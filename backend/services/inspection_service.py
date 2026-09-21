"""
Inspection Service

Handles the business logic for creating inspections, processing samples,
persisting pipeline results to the database, and aggregating lot stats.

This service is the single source of truth for inspection state transitions.
It coordinates between: CV pipeline, grading engine, DB models, and storage.

Threading: CV pipeline runs in a thread pool executor to avoid blocking
the FastAPI async event loop during model inference.
"""
from __future__ import annotations

import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from sqlalchemy.orm import Session

from config import settings
from cv.defect_classifier import DefectPrediction, get_classifier
from cv.pipeline import PipelineResult, run_pipeline
from cv.providers.yolo11_provider import YOLO11SegmentationProvider
from cv.providers.mock_provider import MockSegmentationProvider
from cv.providers.base import SegmentationProvider
from grading.aggregator import aggregate_from_db_instances
from grading.policy_loader import GradingPolicy, load_policy
from models.classification_result import ClassificationResult
from models.defect_observation import DefectObservation
from models.inspection import Inspection
from models.measurement import Measurement
from models.onion_instance import OnionInstance
from models.report import Report
from models.sample import Sample
from schemas.inspection import InspectionCreate

logger = logging.getLogger(__name__)

# ── Module-level singletons (loaded once at startup) ──────────────────────────
_seg_provider: SegmentationProvider | None = None
_defect_classifier = None
_active_policy: GradingPolicy | None = None
_executor = ThreadPoolExecutor(max_workers=settings.cv_inference_workers)


def initialize_cv_components() -> None:
    """
    Load CV models and grading policy at application startup.
    Called from main.py lifespan.
    """
    global _seg_provider, _defect_classifier, _active_policy

    # Load segmentation model
    if settings.seg_model_path.exists():
        logger.info("Loading YOLO11 segmentation model from %s", settings.seg_model_path)
        _seg_provider = YOLO11SegmentationProvider(
            model_path=settings.seg_model_path,
            conf_threshold=settings.seg_confidence_threshold,
            iou_threshold=settings.seg_iou_threshold,
            device="cuda" if settings.cv_use_gpu else "cpu",
        )
        if not _seg_provider.is_ready:
            logger.warning("YOLO11 provider not ready — falling back to mock")
            _seg_provider = MockSegmentationProvider()
    else:
        logger.warning(
            "Segmentation model not found at %s — using MockSegmentationProvider",
            settings.seg_model_path,
        )
        _seg_provider = MockSegmentationProvider()

    # Load defect classifier
    _defect_classifier = get_classifier(
        use_mock=settings.def_use_mock,
        model_path=str(settings.def_model_path) if settings.def_model_path.exists() else None,
    )

    # Load grading policy
    try:
        _active_policy = load_policy(
            version=settings.active_grading_policy,
            policies_dir=settings.policies_dir,
        )
    except Exception as e:
        logger.error("Failed to load grading policy '%s': %s", settings.active_grading_policy, e)
        raise

    logger.info(
        "CV components initialized: seg=%s defect=%s policy=%s",
        _seg_provider.model_version,
        _defect_classifier.model_version,
        _active_policy.version,
    )


def get_cv_status() -> dict:
    """Health status of all CV components."""
    return {
        "seg_provider": _seg_provider.model_version if _seg_provider else "not_loaded",
        "seg_ready": _seg_provider.is_ready if _seg_provider else False,
        "seg_is_mock": isinstance(_seg_provider, MockSegmentationProvider),
        "defect_classifier": _defect_classifier.model_version if _defect_classifier else "not_loaded",
        "defect_is_mock": _defect_classifier.is_mock if _defect_classifier else True,
        "active_policy": _active_policy.version if _active_policy else "not_loaded",
        "policy_verified": _active_policy.verified if _active_policy else False,
        "warning": (
            "MOCK mode active: Segmentation and/or defect classification using "
            "deterministic mock predictions. Results are NOT real AI output."
            if (isinstance(_seg_provider, MockSegmentationProvider) or
                (_defect_classifier and _defect_classifier.is_mock))
            else None
        ),
    }


# ── CRUD operations ───────────────────────────────────────────────────────────

def create_inspection(db: Session, data: InspectionCreate) -> Inspection:
    """Create a new inspection record."""
    inspection = Inspection(
        lot_id=data.lot_id,
        procurement_centre=data.procurement_centre,
        officer_name=data.officer_name,
        officer_id=data.officer_id,
        notes=data.notes,
        geo_lat=data.geo_lat,
        geo_lon=data.geo_lon,
        location_accuracy=data.location_accuracy,
        location_note=data.location_note or (
            "Location unavailable — permission denied" if data.geo_lat is None else None
        ),
        status="DRAFT",
    )
    db.add(inspection)
    db.commit()
    db.refresh(inspection)
    logger.info("Created inspection %s", inspection.id)
    return inspection


def get_inspection(db: Session, inspection_id: str) -> Inspection | None:
    return db.query(Inspection).filter(Inspection.id == inspection_id).first()


def get_all_inspections(db: Session, skip: int = 0, limit: int = 20) -> list[Inspection]:
    return (
        db.query(Inspection)
        .order_by(Inspection.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_sample(db: Session, sample_id: str) -> Sample | None:
    return db.query(Sample).filter(Sample.id == sample_id).first()


def get_onion_instance(db: Session, instance_id: str) -> OnionInstance | None:
    return (
        db.query(OnionInstance)
        .filter(OnionInstance.id == instance_id)
        .first()
    )


async def process_sample_image(
    db: Session,
    inspection_id: str,
    image_bytes: bytes,
    geo_lat: float | None,
    geo_lon: float | None,
    location_accuracy: float | None,
) -> Sample:
    """
    Async entry point: creates a Sample record, runs the CV pipeline in
    a thread pool, and persists all results to the database.

    Args:
        db: Database session.
        inspection_id: Parent inspection UUID.
        image_bytes: Raw image file bytes from the mobile upload.
        geo_lat/lon/location_accuracy: GPS from the device at capture time.

    Returns:
        Sample record (with processing_status='DONE' or 'FAILED').
    """
    inspection = get_inspection(db, inspection_id)
    if inspection is None:
        raise ValueError(f"Inspection {inspection_id} not found")

    # Count existing samples to determine sample_index
    existing_count = (
        db.query(Sample).filter(Sample.inspection_id == inspection_id).count()
    )
    sample_index = existing_count + 1

    # Save the original image to storage
    from services.image_storage import save_image
    image_path = save_image(image_bytes, inspection_id)

    # Create the Sample record
    sample = Sample(
        inspection_id=inspection_id,
        sample_index=sample_index,
        image_path=image_path,
        processing_status="RUNNING",
        processing_started_at=datetime.utcnow(),
        geo_lat=geo_lat,
        geo_lon=geo_lon,
        location_accuracy_m=location_accuracy,
        model_version=(
            f"seg:{_seg_provider.model_version if _seg_provider else 'mock'}/"
            f"def:{_defect_classifier.model_version if _defect_classifier else 'mock'}"
        ),
    )
    db.add(sample)
    inspection.status = "PROCESSING"
    db.commit()
    db.refresh(sample)

    sample_id = sample.id

    # Run CV pipeline in thread pool (blocking CPU work)
    loop = asyncio.get_event_loop()
    try:
        pipeline_result: PipelineResult = await loop.run_in_executor(
            _executor,
            _run_pipeline_sync,
            image_bytes,
            inspection_id,
            sample_id,
        )
    except Exception as e:
        logger.exception("Pipeline execution failed for sample %s", sample_id)
        _mark_sample_failed(db, sample_id, str(e))
        return db.query(Sample).filter(Sample.id == sample_id).first()

    # Persist results to database
    _persist_pipeline_results(db, sample_id, pipeline_result)
    return db.query(Sample).filter(Sample.id == sample_id).first()


def _run_pipeline_sync(
    image_bytes: bytes,
    inspection_id: str,
    sample_id: str,
) -> PipelineResult:
    """Synchronous wrapper called from thread pool."""
    return run_pipeline(
        image_bytes=image_bytes,
        inspection_id=inspection_id,
        sample_id=sample_id,
        seg_provider=_seg_provider,
        defect_classifier=_defect_classifier,
        policy=_active_policy,
    )


def _mark_sample_failed(db: Session, sample_id: str, error: str) -> None:
    sample = db.query(Sample).filter(Sample.id == sample_id).first()
    if sample:
        sample.processing_status = "FAILED"
        sample.processing_error = error
        sample.processing_finished_at = datetime.utcnow()
        db.commit()


def _persist_pipeline_results(
    db: Session, sample_id: str, result: PipelineResult
) -> None:
    """Write all pipeline results to the database."""
    sample = db.query(Sample).filter(Sample.id == sample_id).first()
    if sample is None:
        logger.error("Sample %s not found for result persistence", sample_id)
        return

    sample.quality_passed = result.quality_passed
    sample.quality_flags = json.dumps(result.quality_flags)
    sample.marker_detected = result.marker_detected
    sample.scale_mm_per_px = result.scale_mm_per_px
    sample.perspective_valid = result.perspective_valid
    sample.processing_finished_at = datetime.utcnow()
    if result.processed_image_path:
        sample.processed_image_path = result.processed_image_path

    if result.quality_gate and result.quality_gate.metrics:
        # Store image dimensions if we have them from the decoded image
        pass  # Will get dimensions from quality gate metrics if needed

    if not result.quality_passed or not result.instances:
        sample.processing_status = "DONE" if result.quality_passed else "FAILED"
        sample.processing_error = result.failure_message or None
        db.commit()
        logger.info(
            "Sample %s persisted: quality_passed=%s error=%s",
            sample_id, result.quality_passed, result.failure_message,
        )
        return

    # Persist each onion instance
    for inst_result in result.instances:
        det = inst_result.detection
        defect = inst_result.defect_prediction
        size = inst_result.size_estimate
        grading = inst_result.grading_result

        onion = OnionInstance(
            sample_id=sample_id,
            instance_index=det.instance_index,
            bbox_x=det.bbox_x,
            bbox_y=det.bbox_y,
            bbox_w=det.bbox_w,
            bbox_h=det.bbox_h,
            mask_path=inst_result.mask_path,
            crop_path=inst_result.crop_path,
            segmentation_conf=det.confidence,
            touches_border=det.touches_border,
        )
        db.add(onion)
        db.flush()  # get onion.id before adding children

        # DefectObservation
        if defect is not None:
            raw_output = json.dumps(defect.as_dict())
            final_decision = raw_output  # no human correction yet
            db.add(DefectObservation(
                onion_instance_id=onion.id,
                damaged_prob=defect.damaged_prob,
                rotten_prob=defect.rotten_prob,
                sprouted_prob=defect.sprouted_prob,
                model_version=defect.model_version,
                is_mock=defect.is_mock,
                raw_model_output=raw_output,
                final_decision=final_decision,
            ))

        # Measurement
        if size is not None:
            from models.measurement import PROJECTION_NOTE
            db.add(Measurement(
                onion_instance_id=onion.id,
                equivalent_diameter_mm=size.equivalent_diameter_mm,
                major_axis_mm=size.major_axis_mm,
                minor_axis_mm=size.minor_axis_mm,
                mask_area_px=size.mask_area_px,
                scale_mm_per_px=size.scale_mm_per_px,
                projection_note=PROJECTION_NOTE,
                uncertainty_flag=size.uncertainty_flag,
            ))

        # ClassificationResult
        db.add(ClassificationResult(
            onion_instance_id=onion.id,
            ruleset_version=_active_policy.version,
            grade=grading.grade,
            rejection_reasons=json.dumps(grading.rejection_reasons),
            confidence_tier=grading.confidence_tier,
            explanation=json.dumps(grading.explanation),
        ))

    sample.processing_status = "DONE"
    db.commit()
    logger.info(
        "Persisted %d instances for sample %s",
        len(result.instances), sample_id,
    )

    # Update inspection status to REVIEW
    inspection = db.query(Inspection).filter(Inspection.id == sample.inspection_id).first()
    if inspection:
        inspection.status = "REVIEW"
        db.commit()


def apply_officer_correction(
    db: Session,
    instance_id: str,
    damaged_prob: float,
    rotten_prob: float,
    sprouted_prob: float,
    corrected_by: str,
) -> OnionInstance | None:
    """
    Apply an officer's manual correction to a defect observation.

    The original model output is NEVER overwritten.
    The correction is stored separately and used as final_decision.
    The classification_result is recomputed from the corrected values.
    """
    instance = get_onion_instance(db, instance_id)
    if instance is None:
        return None

    defect_obs = instance.defect_observation
    if defect_obs is None:
        logger.warning("No DefectObservation found for instance %s", instance_id)
        return instance

    # Build correction
    correction = {
        "damaged_prob": damaged_prob,
        "rotten_prob": rotten_prob,
        "sprouted_prob": sprouted_prob,
    }
    defect_obs.human_correction = json.dumps(correction)
    defect_obs.final_decision = json.dumps(correction)
    defect_obs.corrected_by = corrected_by
    defect_obs.corrected_at = datetime.utcnow()

    # Recompute classification from corrected values
    if _active_policy and instance.measurement:
        from cv.confidence import assess_confidence
        from cv.defect_classifier import DefectPrediction
        from cv.size_estimator import SizeEstimate
        from models.measurement import PROJECTION_NOTE

        size = SizeEstimate(
            equivalent_diameter_mm=instance.measurement.equivalent_diameter_mm,
            major_axis_mm=instance.measurement.major_axis_mm,
            minor_axis_mm=instance.measurement.minor_axis_mm,
            mask_area_px=instance.measurement.mask_area_px,
            scale_mm_per_px=instance.measurement.scale_mm_per_px,
            uncertainty_flag=instance.measurement.uncertainty_flag,
        )
        corrected_defect = DefectPrediction(
            damaged_prob=damaged_prob,
            rotten_prob=rotten_prob,
            sprouted_prob=sprouted_prob,
            model_version=defect_obs.model_version,
            is_mock=defect_obs.is_mock,
        )
        confidence = assess_confidence(
            segmentation_conf=instance.segmentation_conf,
            touches_border=instance.touches_border,
            size_estimate=size,
            defect_prediction=corrected_defect,
        )
        engine = GradingEngine(_active_policy)
        new_grading = engine.evaluate_bulb(size, corrected_defect, confidence)

        clf = instance.classification_result
        if clf:
            clf.grade = new_grading.grade
            clf.confidence_tier = new_grading.confidence_tier
            clf.rejection_reasons = json.dumps(new_grading.rejection_reasons)
            explanation = new_grading.explanation.copy()
            explanation["human_correction_by"] = corrected_by
            clf.explanation = json.dumps(explanation)

    db.commit()
    db.refresh(instance)
    logger.info(
        "Officer correction applied to instance %s by %s", instance_id, corrected_by
    )
    return instance


def finalize_inspection(db: Session, inspection_id: str) -> Inspection | None:
    """Mark an inspection as FINALIZED."""
    inspection = get_inspection(db, inspection_id)
    if inspection is None:
        return None
    inspection.status = "FINALIZED"
    inspection.finalized_at = datetime.utcnow()
    db.commit()
    db.refresh(inspection)
    return inspection


# Import at bottom to avoid circular deps
from grading.engine import GradingEngine
