"""
CV Pipeline Orchestrator

The main entry point for processing a captured onion inspection image.
Runs all 8 pipeline stages in sequence, collecting results at each stage.

Pipeline stages:
  1. Image Quality Gate      — reject unusable images early
  2. Marker Detection        — find ChArUco calibration board
  3. Scale Calibration       — compute mm/px ratio, rectify image
  4. Instance Segmentation   — detect individual onion bulbs
  5. Crop Extraction         — save masks and crops to disk
  6. Defect Classification   — multi-label defect probs per onion
  7. Size Estimation         — geometric mm measurements per onion
  8. Confidence Assessment   — tier assignment (HIGH/NEEDS_REVIEW/UNUSABLE)

After the pipeline, the grading engine evaluates each instance.

This module is the ONLY place that knows the full pipeline order.
Individual stages do not know about each other and have no imports
of other pipeline stages.

Threading: This function is CPU-bound (due to model inference).
Run it in a thread pool, never in the async event loop directly.
See services/inspection_service.py for the async wrapper.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from config import settings
from cv.calibration import CalibrationResult, compute_calibration
from cv.confidence import assess_confidence
from cv.crop_extractor import extract_crops
from cv.defect_classifier import DefectClassifier, DefectPrediction
from cv.marker_detector import detect_marker
from cv.providers.base import OnionDetection, SegmentationProvider
from cv.quality_gate import QualityGateResult, check_image_quality
from cv.size_estimator import SizeEstimate, estimate_size
from grading.aggregator import aggregate_from_db_instances
from grading.engine import BulbGradingResult, GradingEngine
from grading.policy_loader import GradingPolicy

logger = logging.getLogger(__name__)


@dataclass
class InstancePipelineResult:
    """Per-onion result from the full pipeline."""
    detection: OnionDetection
    crop_path: str | None
    mask_path: str | None
    defect_prediction: DefectPrediction | None
    size_estimate: SizeEstimate | None
    grading_result: BulbGradingResult


@dataclass
class PipelineResult:
    """
    Full result of processing one sample image through the CV pipeline.

    Successful results have quality_passed=True and populated instances.
    Failed results (quality gate, marker not found, etc.) have quality_passed=False
    and a non-empty failure_message.
    """
    # ── Stage results ──────────────────────────────────────────────────────────
    quality_gate: QualityGateResult | None = None
    calibration: CalibrationResult | None = None

    # ── Aggregate flags ────────────────────────────────────────────────────────
    quality_passed: bool = False
    marker_detected: bool = False
    scale_mm_per_px: float | None = None
    perspective_valid: bool = False

    # ── Quality failures (codes + human message) ───────────────────────────────
    quality_flags: list[str] = field(default_factory=list)
    failure_message: str = ""

    # ── Per-instance results ───────────────────────────────────────────────────
    instances: list[InstancePipelineResult] = field(default_factory=list)

    # ── Timing ────────────────────────────────────────────────────────────────
    total_elapsed_ms: float = 0.0
    segmentation_elapsed_ms: float = 0.0

    # ── Model versions ─────────────────────────────────────────────────────────
    seg_model_version: str = ""
    defect_model_version: str = ""
    processed_image_path: str | None = None


def run_pipeline(
    image_bytes: bytes,
    inspection_id: str,
    sample_id: str,
    seg_provider: SegmentationProvider,
    defect_classifier: DefectClassifier,
    policy: GradingPolicy,
) -> PipelineResult:
    """
    Run the full 8-stage CV pipeline on one captured image.

    This is a synchronous, CPU-bound function.
    Call it from a thread pool (asyncio.get_event_loop().run_in_executor).

    Args:
        image_bytes: Raw image file bytes (JPEG/PNG from device camera).
        inspection_id: For storage path construction.
        sample_id: For storage path construction.
        seg_provider: Loaded segmentation model provider.
        defect_classifier: Loaded defect classifier.
        policy: Active grading policy.

    Returns:
        PipelineResult — always returns, never raises.
    """
    pipeline_start = time.perf_counter()
    result = PipelineResult(
        seg_model_version=seg_provider.model_version,
        defect_model_version=defect_classifier.model_version,
    )

    # ── Decode image ───────────────────────────────────────────────────────────
    nparr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if image is None:
        result.failure_message = "Could not decode image. Please recapture."
        result.quality_flags = ["corrupt_image"]
        logger.error("Could not decode image for sample %s", sample_id)
        return result

    logger.info(
        "Pipeline start: sample=%s image=%dx%d",
        sample_id, image.shape[1], image.shape[0],
    )

    # ── STAGE 1: Image Quality Gate ────────────────────────────────────────────
    qg = check_image_quality(image)
    result.quality_gate = qg
    result.quality_flags = list(qg.failures)

    if not qg.passed:
        result.quality_passed = False
        result.failure_message = qg.message
        logger.warning("Quality gate failed for sample %s: %s", sample_id, qg.failures)
        return result

    result.quality_passed = True

    # ── STAGE 2: ChArUco Marker Detection ─────────────────────────────────────
    marker_result = detect_marker(image)
    result.marker_detected = marker_result.detected

    if not marker_result.detected:
        result.quality_flags.append(marker_result.failure_code or "marker_not_detected")
        # Not fatal — continue with uncalibrated image, measurements will be None
        logger.warning(
            "Marker not detected for sample %s: %s",
            sample_id, marker_result.failure_code,
        )

    # ── STAGE 3: Scale Calibration ─────────────────────────────────────────────
    calibration = compute_calibration(image, marker_result)
    result.calibration = calibration
    result.scale_mm_per_px = calibration.scale_mm_per_px
    result.perspective_valid = calibration.perspective_valid

    if not calibration.perspective_valid and calibration.failure_code:
        if calibration.failure_code not in result.quality_flags:
            result.quality_flags.append(calibration.failure_code)

    # Use rectified image from here on (may be same as original if calibration failed)
    working_image = calibration.rectified_image

    # ── STAGE 4: Instance Segmentation ────────────────────────────────────────
    seg_start = time.perf_counter()
    seg_result = seg_provider.detect(working_image)
    if seg_result.count == 0:
        logger.info("Primary segmentation returned 0 detections — engaging industrial Watershed segmenter")
        from cv.providers.watershed_provider import WatershedSegmentationProvider
        ws_provider = WatershedSegmentationProvider()
        seg_result = ws_provider.detect(working_image)

    result.segmentation_elapsed_ms = (time.perf_counter() - seg_start) * 1000
    result.seg_model_version = seg_result.model_version

    logger.info(
        "Segmentation: %d instances detected in %.1fms (model=%s)",
        seg_result.count,
        result.segmentation_elapsed_ms,
        seg_result.model_version,
    )

    if seg_result.count == 0:
        result.failure_message = (
            "No onion bulbs detected in the image. "
            "Ensure onions are spread out and clearly visible, then recapture."
        )
        result.quality_flags.append("no_detections")
        return result

    # Post-processing quality checks
    detections = seg_result.detections
    n_border = sum(1 for d in detections if d.touches_border)
    if n_border > len(detections) * 0.3:
        result.quality_flags.append("many_edge_cutoffs")

    # ── STAGE 5: Crop Extraction ───────────────────────────────────────────────
    extracted_crops = extract_crops(working_image, detections, inspection_id, sample_id)
    crop_map = {c.instance_index: c for c in extracted_crops}

    # ── STAGES 6-8: Per-instance defect classification, size, confidence ──────
    # Build the grading engine once for all instances
    grading_engine = GradingEngine(policy)
    size_thresholds = policy.size.all_thresholds

    instance_results: list[InstancePipelineResult] = []

    for det in detections:
        idx = det.instance_index
        crop_info = crop_map.get(idx)

        # Load the crop image for defect classification
        crop_image: np.ndarray | None = None
        if crop_info and crop_info.crop_path:
            crop_abs_path = settings.storage_dir / crop_info.crop_path
            if crop_abs_path.exists():
                crop_image = cv2.imread(str(crop_abs_path))

        # ── Stage 6: Defect Classification ──────────────────────────────────
        defect_pred: DefectPrediction | None = None
        if crop_image is not None:
            try:
                defect_pred = defect_classifier.classify(crop_image)
            except Exception:
                logger.exception("Defect classification failed for instance %d", idx)

        # ── Stage 7: Size Estimation ─────────────────────────────────────────
        size_est: SizeEstimate | None = None
        try:
            size_est = estimate_size(
                mask=det.mask,
                scale_mm_per_px=calibration.scale_mm_per_px,
                thresholds_mm=size_thresholds,
            )
        except Exception:
            logger.exception("Size estimation failed for instance %d", idx)

        # ── Stage 8: Confidence Assessment ──────────────────────────────────
        confidence = assess_confidence(
            segmentation_conf=det.confidence,
            touches_border=det.touches_border,
            size_estimate=size_est,
            defect_prediction=defect_pred,
        )

        # ── Grading Engine ───────────────────────────────────────────────────
        grading = grading_engine.evaluate_bulb(
            size_estimate=size_est,
            defect_prediction=defect_pred,
            confidence=confidence,
        )

        # ── Advanced Morphology & Double Bulb Check ───────────────────────────
        if crop_image is not None:
            try:
                from cv.advanced_features import analyze_bulb_morphology
                morph = analyze_bulb_morphology(crop_image, det.mask)
                if morph.is_double_bulb:
                    if "DOUBLE_BULB" not in grading.rejection_reasons:
                        grading.rejection_reasons.append("DOUBLE_BULB")
                    if grading.grade == "GRADE_A":
                        grading.grade = "REJECTED"
                        grading.explanation["double_bulb"] = (
                            f"Twin/double bulb detected (concavity depth {morph.max_concavity_depth_px:.1f}px). Disqualified from Grade A."
                        )
                # Attach morphology telemetry to explanation
                grading.explanation["circularity"] = f"{morph.circularity:.3f}"
                grading.explanation["surface_stain_pct"] = f"{morph.surface_stain_pct:.1f}%"
                grading.explanation["sunburn_pct"] = f"{morph.sunburn_pct:.1f}%"
            except Exception:
                logger.debug("Morphology analysis skipped for instance %d", idx)

        instance_results.append(InstancePipelineResult(
            detection=det,
            crop_path=crop_info.crop_path if crop_info else None,
            mask_path=crop_info.mask_path if crop_info else None,
            defect_prediction=defect_pred,
            size_estimate=size_est,
            grading_result=grading,
        ))

    result.instances = instance_results

    # ── Render Annotated Visual Overlay Image ─────────────────────────────────
    try:
        from cv.annotator import render_annotated_inspection_image
        annotated_rel_path = render_annotated_inspection_image(
            rectified_image=working_image,
            instances=instance_results,
            scale_mm_per_px=calibration.scale_mm_per_px,
            inspection_id=inspection_id,
            sample_id=sample_id,
        )
        result.processed_image_path = annotated_rel_path
    except Exception:
        logger.exception("Failed to render visual annotated overlay for sample %s", sample_id)

    result.total_elapsed_ms = (time.perf_counter() - pipeline_start) * 1000

    logger.info(
        "Pipeline complete: sample=%s instances=%d total=%.0fms",
        sample_id, len(instance_results), result.total_elapsed_ms,
    )

    return result
