"""
Inspections router — all inspection and sample endpoints.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
import cv2
import numpy as np
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from schemas.inspection import InspectionCreate, InspectionDetail, InspectionSummary, InspectionUpdate
from schemas.sample import (
    AskAiRequest,
    OnionCorrectionRequest,
    OnionInstanceDetail,
    OnionInstanceSummary,
    SampleDetail,
)
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
        farmer_id=getattr(inspection, "farmer_id", None),
        farmer_name=getattr(inspection, "farmer_name", None),
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


def _get_bulb_storage_profile(inst):
    from cv.shelf_life import assess_bulb_storageability
    meas = inst.measurement
    defect = inst.defect_observation
    clf = inst.classification_result
    damaged_p, rotten_p, sprouted_p = _extract_defect_probs(defect)

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

    def _parse_pct(val):
        if not val:
            return 0.0
        try:
            return float(str(val).replace("%", "").strip())
        except Exception:
            return 0.0

    def _parse_flt(val, default=1.0):
        if not val:
            return default
        try:
            return float(val)
        except Exception:
            return default

    black_mold_pct = _parse_pct(explanation.get("black_mold_pct"))
    skin_baldness_pct = _parse_pct(explanation.get("skin_baldness_pct"))
    circularity = _parse_flt(explanation.get("circularity"), default=0.90)
    is_double = "DOUBLE_BULB" in rejection_reasons

    diam = None
    if meas:
        diam = meas.equatorial_diameter_mm or meas.equivalent_diameter_mm

    return assess_bulb_storageability(
        bulb_index=inst.instance_index,
        diameter_mm=diam,
        black_mold_pct=black_mold_pct,
        skin_baldness_pct=skin_baldness_pct,
        circularity=circularity,
        is_double_bulb=is_double,
        rotten_prob=rotten_p or 0.0,
        sprouted_prob=sprouted_p or 0.0,
        damaged_prob=damaged_p or 0.0,
    )


def _onion_to_summary(inst) -> OnionInstanceSummary:
    meas = inst.measurement
    defect = inst.defect_observation
    clf = inst.classification_result
    damaged_p, rotten_p, sprouted_p = _extract_defect_probs(defect)
    storage_prof = _get_bulb_storage_profile(inst)
    rejection_reasons = []
    if clf and clf.rejection_reasons:
        try:
            rejection_reasons = json.loads(clf.rejection_reasons)
        except Exception:
            pass

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
        rejection_reasons=rejection_reasons,
        storageability_score=storage_prof.storageability_score,
        storage_tier=storage_prof.storage_tier,
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

    storage_prof = _get_bulb_storage_profile(inst)

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
        storageability_score=storage_prof.storageability_score,
        shelf_life_days_est=storage_prof.shelf_life_days_est,
        storage_tier=storage_prof.storage_tier,
        decay_risk_factors=storage_prof.decay_risk_factors,
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
            farmer_id=getattr(i, "farmer_id", None),
            farmer_name=getattr(i, "farmer_name", None),
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
    acoustic_file: UploadFile | None = File(None, description="Optional acoustic tap WAV recording"),
    bulb_mass_g: float | None = Form(None, description="Optional bulb mass in grams for Elasticity Index"),
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

    # Read optional acoustic audio bytes
    acoustic_bytes: bytes | None = None
    if acoustic_file is not None:
        raw_audio = await acoustic_file.read()
        if len(raw_audio) > 0:
            acoustic_bytes = raw_audio

    # Run pipeline (async — blocks in thread pool internally)
    sample = await inspection_service.process_sample_image(
        db=db,
        inspection_id=inspection_id,
        image_bytes=image_bytes,
        geo_lat=geo_lat,
        geo_lon=geo_lon,
        location_accuracy=location_accuracy,
        acoustic_bytes=acoustic_bytes,
        bulb_mass_g=bulb_mass_g,
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

    # Post-harvest storage advisory
    storage_profiles = [_get_bulb_storage_profile(i) for i in sample.onion_instances]
    from cv.shelf_life import compute_lot_storage_advisory
    storage_adv = compute_lot_storage_advisory(storage_profiles)

    # Counts for commercial settlement
    total_b = len(sample.onion_instances)
    grade_a_cnt = sum(1 for i in sample.onion_instances if i.classification_result and i.classification_result.grade == "GRADE_A")
    urs_cnt = sum(1 for i in sample.onion_instances if i.classification_result and i.classification_result.grade == "URS")
    rej_cnt = sum(1 for i in sample.onion_instances if i.classification_result and i.classification_result.grade == "REJECTED")

    rot_cnt = 0
    sprout_cnt = 0
    under_cnt = 0
    over_cnt = 0
    for i in sample.onion_instances:
        d, r, s = _extract_defect_probs(i.defect_observation)
        if (r or 0) >= 0.50:
            rot_cnt += 1
        if (s or 0) >= 0.50:
            sprout_cnt += 1
        if i.measurement:
            diam = i.measurement.equatorial_diameter_mm or i.measurement.equivalent_diameter_mm
            if diam and diam < 45.0:
                under_cnt += 1
            elif diam and diam > 65.0:
                over_cnt += 1

    from grading.commercial import calculate_mandi_settlement
    settlement = calculate_mandi_settlement(
        total_bulbs=total_b,
        grade_a_count=grade_a_cnt,
        urs_count=urs_cnt,
        rejected_count=rej_cnt,
        rotten_count=rot_cnt,
        sprouted_count=sprout_cnt,
        undersized_count=under_cnt,
        oversized_count=over_cnt,
        storageability_score=storage_adv.mean_storageability_score,
    )

    ai_verdict = None
    if sample.image_path:
        cache_path = settings.storage_dir / f"{sample.image_path}.ai.json"
        if cache_path.exists():
            try:
                ai_verdict = json.loads(cache_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        if not ai_verdict:
            full_img_path = settings.storage_dir / sample.image_path
            if full_img_path.exists():
                try:
                    import cv2
                    img = cv2.imread(str(full_img_path))
                    if img is not None:
                        from services.groq_ai_service import analyze_inspection_with_ai
                        ai_verdict = analyze_inspection_with_ai(img)
                        cache_path.parent.mkdir(parents=True, exist_ok=True)
                        cache_path.write_text(json.dumps(ai_verdict), encoding="utf-8")
                except Exception as e:
                    logger.warning("Error generating AI verdict: %s", e)

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
        is_estimated_scale=getattr(sample, "is_estimated_scale", False) or not sample.marker_detected,
        calibration_method=getattr(sample, "calibration_method", "AUTONOMOUS_OVERHEAD_HEURISTIC" if not sample.marker_detected else "CHARUCO_BOARD") or "AUTONOMOUS_OVERHEAD_HEURISTIC",
        scale_uncertainty_mm=3.5 if (getattr(sample, "is_estimated_scale", False) or not sample.marker_detected) else 0.5,
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
        storage_advisory=storage_adv.as_dict(),
        commercial_settlement=settlement.as_dict(),
        ai_agronomist_verdict=ai_verdict,
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
    # Auto-generate the official report and PDF so certificates and downloads are immediately available
    from routers.reports import create_or_update_report
    try:
        create_or_update_report(updated, db)
    except Exception as exc:
        logger.exception("Failed to auto-generate report during finalize: %s", exc)
    return _inspection_to_detail(updated, db)


# ── Video Inspection Sweep ───────────────────────────────────────────────────

@router.post("/inspections/{inspection_id}/video", status_code=status.HTTP_201_CREATED)
async def process_video_endpoint(
    inspection_id: str,
    file: UploadFile = File(..., description="Recorded video sweep of onion lot (MP4/MOV/WebM)"),
    db: Session = Depends(get_db),
):
    """
    Process continuous video inspection sweep of an onion lot.
    Segments keyframes, tracks defects across time, and runs Groq Multimodal Vision AI.
    """
    inspection = inspection_service.get_inspection(db, inspection_id)
    if inspection is None:
        raise HTTPException(status_code=404, detail="Inspection not found")
    if inspection.status == "FINALIZED":
        raise HTTPException(status_code=400, detail="Cannot add video to a finalized inspection")

    video_bytes = await file.read()
    if len(video_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded video file is empty")

    from services.video_service import process_video_scan
    try:
        result = process_video_scan(
            db=db,
            inspection_id=inspection_id,
            video_bytes=video_bytes,
            original_filename=file.filename or "sweep.mp4",
        )
        return result
    except Exception as e:
        logger.exception("Failed to process video scan: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to process video: {str(e)}")


# ── Acoustic Tap Impulse Analysis ─────────────────────────────────────────────

@router.post("/inspections/{inspection_id}/acoustic", status_code=status.HTTP_200_OK)
async def analyze_acoustic_endpoint(
    inspection_id: str,
    file: UploadFile = File(..., description="Acoustic tap audio recording (WAV format)"),
    bulb_mass_g: float | None = Form(None, description="Optional bulb mass in grams for Elasticity Index"),
    db: Session = Depends(get_db),
):
    """
    Analyze acoustic tap impulse response of an onion bulb for hollow-body/internal decay detection.

    Computes:
    - Dominant resonant frequency f0 (Hz)
    - Quality factor Q (-3dB bandwidth)
    - Elasticity Index EI = f0^2 * m^(2/3) (if mass provided)
    - Hollow-body risk score (0.0=healthy to 1.0=hollow/suspect)
    - Risk tier (LOW / MEDIUM / HIGH / INVALID)
    - Honest limitation statement ([Taniwaki-2023], [Kim-2024])
    """
    inspection = inspection_service.get_inspection(db, inspection_id)
    if inspection is None:
        raise HTTPException(status_code=404, detail="Inspection not found")

    wav_bytes = await file.read()
    if len(wav_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded audio file is empty")

    from services.acoustic_service import get_analyzer, ACOUSTIC_LIMITATION_STATEMENT
    try:
        analyzer = get_analyzer(use_mock=False)
        reading = analyzer.analyze_wav_bytes(wav_bytes, mass_g=bulb_mass_g)

        timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        f0_val = f"{reading.dominant_freq_hz:.1f}Hz" if reading.dominant_freq_hz is not None else "N/A"
        q_val = f"{reading.quality_factor_q:.1f}" if reading.quality_factor_q is not None else "N/A"
        acoustic_note = (
            f"\n[Acoustic Tap {timestamp_str}] f0={f0_val}, "
            f"Q={q_val}, risk={reading.hollow_risk_tier} ({reading.hollow_risk_score:.2f})"
        )
        inspection.notes = (inspection.notes or "") + acoustic_note
        db.commit()

        recommendation = (
            "High hollow-body risk detected — perform destructive cross-section check on 2 sample bulbs."
            if reading.hollow_risk_tier == "HIGH"
            else "Intermediate acoustic resonance — monitor lot during storage."
            if reading.hollow_risk_tier == "MEDIUM"
            else "Acoustic resonance normal — turgid sound flesh structure."
            if reading.hollow_risk_tier == "LOW"
            else "Invalid acoustic recording — please recapture tap audio in quiet environment."
        )

        return {
            "inspection_id": inspection_id,
            "reading": reading.as_dict(),
            "recommendation": recommendation,
            "limitation_statement": ACOUSTIC_LIMITATION_STATEMENT,
        }
    except Exception as e:
        logger.exception("Acoustic analysis failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Acoustic analysis failed: {str(e)}")


# ── Groq AI Agronomist Interactive Q&A ────────────────────────────────────────

@router.post("/inspections/{inspection_id}/ask-ai")
async def ask_ai_endpoint(
    inspection_id: str,
    body: AskAiRequest,
    db: Session = Depends(get_db),
):
    """
    Ask the Multimodal Groq AI Agronomist an interactive question about the inspected onion lot.
    """
    inspection = inspection_service.get_inspection(db, inspection_id)
    if inspection is None:
        raise HTTPException(status_code=404, detail="Inspection not found")

    detail = _inspection_to_detail(inspection, db)
    context = {
        "total_bulbs": detail.total_bulbs,
        "grade_a_count": detail.grade_a_count,
        "urs_count": detail.urs_count,
        "rejected_count": detail.rejected_count,
        "grade_a_pct": detail.grade_a_pct,
        "urs_pct": detail.urs_pct,
        "rejected_pct": detail.rejected_pct,
    }
    if inspection.samples:
        last_sample = inspection.samples[-1]
        sample_detail = _sample_to_detail(last_sample)
        if sample_detail.storage_advisory:
            context["storage_days"] = sample_detail.storage_advisory.get("recommended_storage_days", 90)
        if sample_detail.commercial_settlement:
            context["net_rate_inr"] = sample_detail.commercial_settlement.get("net_rate_inr", 2410)
            context["avg_diameter_mm"] = sample_detail.commercial_settlement.get("mean_equatorial_diameter_mm", 52.0)

    from services.groq_ai_service import ask_ai_agronomist
    answer = ask_ai_agronomist(body.question, context)
    return {
        "answer": answer,
        "inspection_id": inspection_id,
        "powered_by": "Groq AI (qwen/qwen3.8-27b)",
    }


# ── Bhashini Multilingual Grade Announcement ──────────────────────────────────

@router.post("/inspections/{inspection_id}/announce")
async def announce_grade_endpoint(
    inspection_id: str,
    language: str | None = None,
    state_or_city: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Generate a multilingual spoken grade announcement via Bhashini TTS.

    Produces a complete grade announcement in the officer's regional language
    (automatically inferred from state_or_city, or explicitly set with language).

    Supports: hi (Hindi), mr (Marathi), kn (Kannada), te (Telugu), ta (Tamil),
              gu (Gujarati), en (English).

    Returns:
        JSON with announcement_text always populated.
        If Bhashini API key is configured: also includes base64-encoded WAV audio.
        Falls back gracefully when BHASHINI_API_KEY is absent.
    """
    inspection = inspection_service.get_inspection(db, inspection_id)
    if inspection is None:
        raise HTTPException(status_code=404, detail="Inspection not found")

    detail = _inspection_to_detail(inspection, db)

    # Determine lot recommendation from grade distribution
    grade_a_pct = detail.grade_a_pct
    urs_pct = detail.urs_pct
    rejected_pct = detail.rejected_pct
    total = detail.total_bulbs

    if total < 5:
        lot_recommendation = "ADDITIONAL_SAMPLE_REQUIRED"
    elif grade_a_pct >= 70.0:
        lot_recommendation = "ACCEPT_GRADE_A"
    elif (grade_a_pct + urs_pct) >= 70.0:
        lot_recommendation = "ACCEPT_URS"
    else:
        lot_recommendation = "REJECT_LOT"

    from services.bhashini_service import (
        SupportedLanguage,
        build_announcement_from_inspection,
        synthesize_grade_announcement,
        get_language_from_state,
    )

    # Resolve language
    resolved_language: SupportedLanguage | None = None
    if language:
        try:
            resolved_language = SupportedLanguage(language.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported language '{language}'. Use: hi, mr, kn, te, ta, gu, en",
            )
    elif state_or_city:
        resolved_language = get_language_from_state(state_or_city)
    else:
        # Infer from procurement_centre name
        resolved_language = get_language_from_state(inspection.procurement_centre or "")

    announcement = build_announcement_from_inspection(
        grade_a_pct=grade_a_pct,
        urs_pct=urs_pct,
        rejected_pct=rejected_pct,
        lot_recommendation=lot_recommendation,
        suspect_count=detail.rejected_count,
        centre_name=inspection.procurement_centre or "",
        lot_id=inspection.lot_id or inspection_id[:8].upper(),
        total_bulbs=total,
        language=resolved_language,
    )

    # Get Bhashini API key from settings
    bhashini_key = getattr(settings, "bhashini_api_key", "") or ""

    result = synthesize_grade_announcement(announcement, bhashini_api_key=bhashini_key)

    import base64 as _b64
    response: dict = {
        "inspection_id": inspection_id,
        "language": result.language.value,
        "announcement_text": result.announcement_text,
        "lot_recommendation": lot_recommendation,
        "grade_a_pct": grade_a_pct,
        "urs_pct": urs_pct,
        "rejected_pct": rejected_pct,
        "audio_available": result.success and result.audio_bytes is not None,
        "is_mock": result.is_mock,
        "latency_ms": result.latency_ms,
    }
    if result.success and result.audio_bytes:
        response["audio_base64"] = _b64.b64encode(result.audio_bytes).decode("ascii")
        response["audio_content_type"] = result.content_type
    elif result.error_message:
        response["tts_status"] = result.error_message

    return response


# ── eNAM & AgriStack Digital Assaying Export ─────────────────────────────────

@router.get("/inspections/{inspection_id}/enam")
async def export_enam_endpoint(
    inspection_id: str,
    format: str = Query("json", pattern="^(json|xml)$", description="Export format: json or xml"),
    lot_weight_kg: float = Query(1000.0, ge=1.0, le=100000.0, description="Consignment declared weight in kg"),
    db: Session = Depends(get_db),
):
    """
    Export standardized eNAM (National Agriculture Market) Assaying Certificate
    linked to the farmer's 12-digit AgriStack Farmer ID.

    Conforms to:
    - Ministry of Agriculture eNAM Assaying Specification v2.1
    - AGMARK Schedule XIX (Fruits and Vegetables Grading and Marking Rules)
    - AgriStack Farmer Registry Data Exchange Standard
    """
    inspection = inspection_service.get_inspection(db, inspection_id)
    if inspection is None:
        raise HTTPException(status_code=404, detail="Inspection not found")

    detail = _inspection_to_detail(inspection, db)
    from services.enam_export_service import export_enam_certificate
    try:
        res = export_enam_certificate(detail, lot_weight_kg=lot_weight_kg)
        if format == "xml":
            filename = f"eNAM_Assaying_{res.lot_id}.xml"
            return Response(
                content=res.payload_xml,
                media_type="application/xml",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )
        return {
            "status": "success",
            "inspection_id": inspection_id,
            "lot_id": res.lot_id,
            "farmer_id": res.farmer_id,
            "farmer_name": res.farmer_name,
            "procurement_centre": res.procurement_centre,
            "assigned_grade": res.grade,
            "msp_procurement_eligible": res.msp_eligible,
            "generated_at": res.generated_at,
            "payload_json": res.payload_json,
            "payload_xml": res.payload_xml,
            "download_xml_url": f"/api/v1/inspections/{inspection_id}/enam?format=xml&lot_weight_kg={lot_weight_kg}",
        }
    except Exception as e:
        logger.exception("Failed to export eNAM certificate: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to generate eNAM certificate: {str(e)}")


# ── Flash Proxy Index (FPI) Differential Reflectance Endpoint ───────────────

@router.post("/inspections/{inspection_id}/fpi")
async def analyze_flash_proxy_endpoint(
    inspection_id: str,
    ambient_file: UploadFile = File(..., description="Image captured under ambient mandi illumination"),
    flash_file: UploadFile = File(..., description="Image captured under smartphone LED flash illumination"),
    db: Session = Depends(get_db),
):
    """
    Analyze dual-exposure (ambient vs flash) differential reflectance using
    Flash Proxy Index (FPI) to detect sub-surface cuticular water congestion and early soft rot.

    Theoretical basis: [Nicolaï-2007], [Taniwaki-2023].
    """
    inspection = inspection_service.get_inspection(db, inspection_id)
    if inspection is None:
        raise HTTPException(status_code=404, detail="Inspection not found")

    from cv.flash_proxy import (
        FLASH_PROXY_LIMITATION_STATEMENT,
        analyze_bulb_fpi,
        compute_flash_proxy_map,
        encode_heatmap_to_base64,
        generate_fpi_heatmap,
    )

    try:
        amb_bytes = await ambient_file.read()
        flash_bytes = await flash_file.read()

        amb_np = np.frombuffer(amb_bytes, np.uint8)
        flash_np = np.frombuffer(flash_bytes, np.uint8)

        amb_bgr = cv2.imdecode(amb_np, cv2.IMREAD_COLOR)
        flash_bgr = cv2.imdecode(flash_np, cv2.IMREAD_COLOR)

        if amb_bgr is None or flash_bgr is None:
            raise HTTPException(status_code=400, detail="Invalid image bytes: could not decode JPEG/PNG")

        # Downscale for memory efficiency on constrained cloud containers (512MB RAM)
        max_dim = 800
        h_a, w_a = amb_bgr.shape[:2]
        if max(h_a, w_a) > max_dim:
            scale = max_dim / float(max(h_a, w_a))
            amb_bgr = cv2.resize(amb_bgr, (int(w_a * scale), int(h_a * scale)), interpolation=cv2.INTER_AREA)
            flash_bgr = cv2.resize(flash_bgr, (int(w_a * scale), int(h_a * scale)), interpolation=cv2.INTER_AREA)

        fpi_map = compute_flash_proxy_map(amb_bgr, flash_bgr)

        # Whole field mask
        full_mask = np.full(fpi_map.shape, 255, dtype=np.uint8)
        analysis = analyze_bulb_fpi(fpi_map, full_mask)
        heatmap_bgr = generate_fpi_heatmap(fpi_map)
        heatmap_b64 = encode_heatmap_to_base64(heatmap_bgr)

        import gc
        del amb_bytes, flash_bytes, amb_np, flash_np, amb_bgr, flash_bgr, fpi_map, full_mask, heatmap_bgr
        gc.collect()

        return {
            "status": "success",
            "inspection_id": inspection_id,
            "mean_fpi": analysis.mean_fpi,
            "spatial_heterogeneity": analysis.spatial_heterogeneity,
            "lesion_area_ratio": analysis.lesion_area_ratio,
            "surface_state": analysis.surface_state,
            "confidence": analysis.confidence,
            "notes": analysis.notes,
            "heatmap_base64": heatmap_b64,
            "limitation_statement": FLASH_PROXY_LIMITATION_STATEMENT,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("FPI analysis failed: %s", e)
        raise HTTPException(status_code=500, detail=f"FPI differential reflectance analysis failed: {str(e)}")

