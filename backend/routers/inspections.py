"""
Inspections router — all inspection and sample endpoints.
"""
from __future__ import annotations

import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from database import get_db
from schemas.inspection import InspectionCreate, InspectionDetail, InspectionSummary, InspectionUpdate
from schemas.sample import OnionCorrectionRequest, OnionInstanceDetail, OnionInstanceSummary, SampleDetail
from services import inspection_service
from services.image_storage import path_to_url

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["inspections"])

# ── Helpers ───────────────────────────────────────────────────────────────────

def _inspection_to_detail(inspection, db: Session) -> InspectionDetail:
    """Build InspectionDetail with aggregated stats."""
    from models.classification_result import ClassificationResult
    from models.onion_instance import OnionInstance
    from models.sample import Sample

    sample_ids = [s.id for s in inspection.samples]
    total = grade_a = urs = rejected = review = 0

    for sample in inspection.samples:
        for inst in sample.onion_instances:
            clf = inst.classification_result
            if clf is None:
                continue
            total += 1
            match clf.grade:
                case "GRADE_A":
                    grade_a += 1
                case "URS":
                    urs += 1
                case "REJECTED":
                    rejected += 1
                case "NEEDS_REVIEW":
                    review += 1

    has_report = inspection.report is not None
    report_id = inspection.report.report_id if has_report else None

    return InspectionDetail(
        id=inspection.id,
        lot_id=inspection.lot_id,
        procurement_centre=inspection.procurement_centre,
        officer_name=inspection.officer_name,
        officer_id=inspection.officer_id,
        notes=inspection.notes,
        status=inspection.status,
        geo_lat=inspection.geo_lat,
        geo_lon=inspection.geo_lon,
        location_accuracy=inspection.location_accuracy,
        location_note=inspection.location_note,
        created_at=inspection.created_at,
        updated_at=inspection.updated_at,
        finalized_at=inspection.finalized_at,
        total_bulbs=total,
        grade_a_count=grade_a,
        urs_count=urs,
        rejected_count=rejected,
        review_count=review,
        grade_a_pct=round(100.0 * grade_a / total, 1) if total else 0.0,
        urs_pct=round(100.0 * urs / total, 1) if total else 0.0,
        rejected_pct=round(100.0 * rejected / total, 1) if total else 0.0,
        sample_ids=sample_ids,
        has_report=has_report,
        report_id=report_id,
    )


def _extract_defect_probs(defect):
    if defect is None:
        return None, None, None
    if defect.final_decision:
        try:
            fd = json.loads(defect.final_decision)
            return (
                float(fd.get("damaged_prob", defect.damaged_prob)),
                float(fd.get("rotten_prob", defect.rotten_prob)),
                float(fd.get("sprouted_prob", defect.sprouted_prob)),
            )
        except Exception:
            pass
    return defect.damaged_prob, defect.rotten_prob, defect.sprouted_prob


def _onion_to_summary(inst) -> OnionInstanceSummary:
    meas = inst.measurement
    defect = inst.defect_observation
    clf = inst.classification_result
    damaged_p, rotten_p, sprouted_p = _extract_defect_probs(defect)
    return OnionInstanceSummary(
        id=inst.id,
        instance_index=inst.instance_index,
        display_number=inst.instance_index + 1,
        bbox_x=inst.bbox_x,
        bbox_y=inst.bbox_y,
        bbox_w=inst.bbox_w,
        bbox_h=inst.bbox_h,
        segmentation_conf=inst.segmentation_conf,
        touches_border=inst.touches_border,
        equivalent_diameter_mm=meas.equivalent_diameter_mm if meas else None,
        equatorial_diameter_mm=meas.equatorial_diameter_mm if meas else None,
        polar_length_mm=meas.polar_length_mm if meas else None,
        shape_class=meas.shape_class if meas else None,
        estimated_weight_grams=meas.estimated_weight_grams if meas else None,
        mandi_size_grade=meas.mandi_size_grade if meas else None,
        damaged_prob=damaged_p,
        rotten_prob=rotten_p,
        sprouted_prob=sprouted_p,
        is_mock_defect=defect.is_mock if defect else True,
        grade=clf.grade if clf else None,
        confidence_tier=clf.confidence_tier if clf else None,
        crop_url=path_to_url(inst.crop_path),
        mask_url=path_to_url(inst.mask_path),
    )


def _onion_to_detail(inst) -> OnionInstanceDetail:
    meas = inst.measurement
    defect = inst.defect_observation
    clf = inst.classification_result

    explanation = {}
    rejection_reasons = []
    if clf:
        try:
            explanation = json.loads(clf.explanation or "{}")
        except Exception:
            pass
        try:
            rejection_reasons = json.loads(clf.rejection_reasons or "[]")
        except Exception:
            pass

    damaged_p, rotten_p, sprouted_p = _extract_defect_probs(defect)

    morph_dict = {
        "circularity": explanation.get("circularity"),
        "surface_stain_pct": explanation.get("surface_stain_pct"),
        "sunburn_pct": explanation.get("sunburn_pct"),
        "black_mold_pct": explanation.get("black_mold_pct"),
        "skin_baldness_pct": explanation.get("skin_baldness_pct"),
        "ngrdi_mean": explanation.get("ngrdi_mean"),
        "double_bulb": "DOUBLE_BULB" in rejection_reasons,
    }

    return OnionInstanceDetail(
        id=inst.id,
        instance_index=inst.instance_index,
        display_number=inst.instance_index + 1,
        bbox_x=inst.bbox_x,
        bbox_y=inst.bbox_y,
        bbox_w=inst.bbox_w,
        bbox_h=inst.bbox_h,
        segmentation_conf=inst.segmentation_conf,
        touches_border=inst.touches_border,
        crop_url=path_to_url(inst.crop_path),
        mask_url=path_to_url(inst.mask_path),
        damaged_prob=damaged_p,
        rotten_prob=rotten_p,
        sprouted_prob=sprouted_p,
        defect_model_version=defect.model_version if defect else None,
        is_mock_defect=defect.is_mock if defect else True,
        has_human_correction=defect.human_correction is not None if defect else False,
        corrected_by=defect.corrected_by if defect else None,
        morphology=morph_dict,
        equivalent_diameter_mm=meas.equivalent_diameter_mm if meas else None,
        major_axis_mm=meas.major_axis_mm if meas else None,
        minor_axis_mm=meas.minor_axis_mm if meas else None,
        equatorial_diameter_mm=meas.equatorial_diameter_mm if meas else None,
        polar_length_mm=meas.polar_length_mm if meas else None,
        shape_index=meas.shape_index if meas else None,
        shape_class=meas.shape_class if meas else None,
        estimated_weight_grams=meas.estimated_weight_grams if meas else None,
        mandi_size_grade=meas.mandi_size_grade if meas else None,
        mask_area_px=meas.mask_area_px if meas else None,
        scale_mm_per_px=meas.scale_mm_per_px if meas else None,
        projection_note=meas.projection_note if meas else None,
        uncertainty_flag=meas.uncertainty_flag if meas else False,
        grade=clf.grade if clf else None,
        rejection_reasons=rejection_reasons,
        confidence_tier=clf.confidence_tier if clf else None,
        ruleset_version=clf.ruleset_version if clf else None,
        explanation=explanation,
    )


# ── Inspection endpoints ───────────────────────────────────────────────────────

@router.post("/inspections", status_code=status.HTTP_201_CREATED)
async def create_inspection(
    body: InspectionCreate,
    db: Session = Depends(get_db),
) -> InspectionDetail:
    inspection = inspection_service.create_inspection(db, body)
    return _inspection_to_detail(inspection, db)


@router.get("/inspections")
async def list_inspections(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
) -> list[InspectionSummary]:
    inspections = inspection_service.get_all_inspections(db, skip=skip, limit=limit)
    return [
        InspectionSummary(
            id=i.id,
            lot_id=i.lot_id,
            procurement_centre=i.procurement_centre,
            officer_name=i.officer_name,
            status=i.status,
            created_at=i.created_at,
            finalized_at=i.finalized_at,
            sample_count=len(i.samples),
        )
        for i in inspections
    ]


@router.get("/inspections/{inspection_id}")
async def get_inspection(
    inspection_id: str,
    db: Session = Depends(get_db),
) -> InspectionDetail:
    inspection = inspection_service.get_inspection(db, inspection_id)
    if inspection is None:
        raise HTTPException(status_code=404, detail=f"Inspection {inspection_id} not found")
    return _inspection_to_detail(inspection, db)


@router.patch("/inspections/{inspection_id}")
async def update_inspection(
    inspection_id: str,
    body: InspectionUpdate,
    db: Session = Depends(get_db),
) -> InspectionDetail:
    inspection = inspection_service.get_inspection(db, inspection_id)
    if inspection is None:
        raise HTTPException(status_code=404, detail="Inspection not found")
    if body.lot_id is not None:
        inspection.lot_id = body.lot_id
    if body.procurement_centre is not None:
        inspection.procurement_centre = body.procurement_centre
    if body.officer_name is not None:
        inspection.officer_name = body.officer_name
    if body.officer_id is not None:
        inspection.officer_id = body.officer_id
    if body.notes is not None:
        inspection.notes = body.notes
    db.commit()
    db.refresh(inspection)
    return _inspection_to_detail(inspection, db)


# ── Sample endpoints ───────────────────────────────────────────────────────────

@router.post("/inspections/{inspection_id}/samples", status_code=status.HTTP_201_CREATED)
async def add_sample(
    inspection_id: str,
    file: UploadFile = File(..., description="Captured onion spread image (JPEG/PNG)"),
    geo_lat: float | None = Form(None),
    geo_lon: float | None = Form(None),
    location_accuracy: float | None = Form(None),
    db: Session = Depends(get_db),
) -> SampleDetail:
    inspection = inspection_service.get_inspection(db, inspection_id)
    if inspection is None:
        raise HTTPException(status_code=404, detail="Inspection not found")
    if inspection.status == "FINALIZED":
        raise HTTPException(status_code=400, detail="Cannot add samples to a finalized inspection")

    # Read image bytes
    image_bytes = await file.read()
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    # Run pipeline (async — blocks in thread pool internally)
    sample = await inspection_service.process_sample_image(
        db=db,
        inspection_id=inspection_id,
        image_bytes=image_bytes,
        geo_lat=geo_lat,
        geo_lon=geo_lon,
        location_accuracy=location_accuracy,
    )

    return _sample_to_detail(sample)


@router.get("/inspections/{inspection_id}/samples")
async def list_samples(
    inspection_id: str,
    db: Session = Depends(get_db),
) -> list[SampleDetail]:
    inspection = inspection_service.get_inspection(db, inspection_id)
    if inspection is None:
        raise HTTPException(status_code=404, detail="Inspection not found")
    return [_sample_to_detail(s) for s in inspection.samples]


@router.get("/inspections/{inspection_id}/samples/{sample_id}")
async def get_sample(
    inspection_id: str,
    sample_id: str,
    db: Session = Depends(get_db),
) -> SampleDetail:
    sample = inspection_service.get_sample(db, sample_id)
    if sample is None or sample.inspection_id != inspection_id:
        raise HTTPException(status_code=404, detail="Sample not found")
    return _sample_to_detail(sample)


def _sample_to_detail(sample) -> SampleDetail:
    flags = []
    if sample.quality_flags:
        try:
            flags = json.loads(sample.quality_flags)
        except Exception:
            pass
    return SampleDetail(
        id=sample.id,
        inspection_id=sample.inspection_id,
        sample_index=sample.sample_index,
        image_path=sample.image_path,
        processed_image_path=sample.processed_image_path,
        original_image_url=path_to_url(sample.image_path),
        processed_image_url=path_to_url(sample.processed_image_path),
        image_width_px=sample.image_width_px,
        image_height_px=sample.image_height_px,
        marker_detected=sample.marker_detected,
        scale_mm_per_px=sample.scale_mm_per_px,
        perspective_valid=sample.perspective_valid,
        quality_passed=sample.quality_passed,
        quality_flags=flags,
        processing_status=sample.processing_status,
        processing_error=sample.processing_error,
        processing_started_at=sample.processing_started_at,
        processing_finished_at=sample.processing_finished_at,
        model_version=sample.model_version,
        geo_lat=sample.geo_lat,
        geo_lon=sample.geo_lon,
        location_accuracy_m=sample.location_accuracy_m,
        created_at=sample.created_at,
        onion_count=len(sample.onion_instances),
        onion_instances=[_onion_to_summary(i) for i in sample.onion_instances],
    )


# ── Per-onion drilldown ────────────────────────────────────────────────────────

@router.get("/inspections/{inspection_id}/onions/{instance_id}")
async def get_onion(
    inspection_id: str,
    instance_id: str,
    db: Session = Depends(get_db),
) -> OnionInstanceDetail:
    inst = inspection_service.get_onion_instance(db, instance_id)
    if inst is None or inst.sample.inspection_id != inspection_id:
        raise HTTPException(status_code=404, detail="Onion instance not found")
    return _onion_to_detail(inst)


@router.post("/inspections/{inspection_id}/onions/{instance_id}/correct")
async def correct_onion(
    inspection_id: str,
    instance_id: str,
    body: OnionCorrectionRequest,
    db: Session = Depends(get_db),
) -> OnionInstanceDetail:
    inst = inspection_service.get_onion_instance(db, instance_id)
    if inst is None or inst.sample.inspection_id != inspection_id:
        raise HTTPException(status_code=404, detail="Onion instance not found")

    updated = inspection_service.apply_officer_correction(
        db=db,
        instance_id=instance_id,
        damaged_prob=body.damaged_prob,
        rotten_prob=body.rotten_prob,
        sprouted_prob=body.sprouted_prob,
        corrected_by=body.corrected_by,
    )
    if updated is None:
        raise HTTPException(status_code=500, detail="Failed to apply correction")
    return _onion_to_detail(updated)


# ── Finalize ───────────────────────────────────────────────────────────────────

@router.post("/inspections/{inspection_id}/finalize")
async def finalize_inspection(
    inspection_id: str,
    db: Session = Depends(get_db),
) -> InspectionDetail:
    inspection = inspection_service.get_inspection(db, inspection_id)
    if inspection is None:
        raise HTTPException(status_code=404, detail="Inspection not found")
    if inspection.status not in ("REVIEW", "DRAFT"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot finalize inspection with status '{inspection.status}'"
        )
    updated = inspection_service.finalize_inspection(db, inspection_id)
    return _inspection_to_detail(updated, db)
