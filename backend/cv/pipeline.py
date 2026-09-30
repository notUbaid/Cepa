"""
CV Pipeline Orchestrator

The main entry point for processing a captured onion inspection image.
Runs all 8 pipeline stages in sequence, collecting results at each stage.

Pipeline stages:
  1. Image Quality Gate      - reject unusable images early
  2. Marker Detection        - find ChArUco calibration board
  3. Scale Calibration       - compute mm/px ratio, rectify image
  4. Instance Segmentation   - detect individual onion bulbs
  5. Crop Extraction         - save masks and crops to disk
  6. Defect Classification   - multi-label defect probs per onion
  7. Size Estimation         - geometric mm measurements per onion
  8. Confidence Assessment   - tier assignment (HIGH/NEEDS_REVIEW/UNUSABLE)

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
    is_estimated_scale: bool = False
    calibration_method: str = "CHARUCO_BOARD"
    scale_uncertainty_mm: float = 0.5

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
        PipelineResult - always returns, never raises.
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
        # Not fatal - continue with uncalibrated image, measurements will be None
        logger.warning(
            "Marker not detected for sample %s: %s",
            sample_id, marker_result.failure_code,
        )

    # ── STAGE 3: Scale Calibration ─────────────────────────────────────────────
    calibration = compute_calibration(image, marker_result)
    result.calibration = calibration
    result.scale_mm_per_px = calibration.scale_mm_per_px
    result.perspective_valid = calibration.perspective_valid
    result.is_estimated_scale = calibration.is_estimated
    result.calibration_method = calibration.calibration_method
    result.scale_uncertainty_mm = calibration.uncertainty_mm

    if not calibration.perspective_valid and calibration.failure_code:
        if calibration.failure_code not in result.quality_flags:
            result.quality_flags.append(calibration.failure_code)

    # Use rectified image from here on (may be same as original if calibration failed)
    working_image = calibration.rectified_image

    # ── STAGE 4: Instance Segmentation ────────────────────────────────────────
    seg_start = time.perf_counter()
    seg_result = seg_provider.detect(working_image)

    # Hybrid High-Recall Resilient Ensemble:
    # If primary segmenter returns 0 detections, engage industrial Watershed immediately.
    if seg_result.count == 0:
        logger.info("Primary segmentation returned 0 detections. Engaging industrial Watershed segmenter.")
        from cv.providers.watershed_provider import WatershedSegmentationProvider
        ws_provider = WatershedSegmentationProvider()
        seg_result = ws_provider.detect(working_image)
    elif seg_result.count < 4:
        # Complementary ensemble: check for non-overlapping bulbs missed by primary detector
        try:
            from cv.providers.watershed_provider import WatershedSegmentationProvider
            ws_provider = WatershedSegmentationProvider()
            ws_result = ws_provider.detect(working_image)
            if ws_result.count > 0:
                merged_detections = list(seg_result.detections)
                for ws_det in ws_result.detections:
                    ws_area = int(np.count_nonzero(ws_det.mask))
                    overlaps = False
                    for ex_det in merged_detections:
                        ex_area = int(np.count_nonzero(ex_det.mask))
                        inter = int(np.count_nonzero(cv2.bitwise_and(ws_det.mask, ex_det.mask)))
                        if inter > 0.20 * min(ws_area, ex_area):
                            overlaps = True
                            break
                    if not overlaps:
                        ws_det.instance_index = len(merged_detections)
                        merged_detections.append(ws_det)
                if len(merged_detections) > seg_result.count:
                    logger.info(
                        "Ensemble merged %d additional high-confidence bulbs from Watershed",
                        len(merged_detections) - seg_result.count,
                    )
                    seg_result.detections = merged_detections
        except Exception:
            logger.debug("Watershed ensemble merge skipped due to exception")

    result.segmentation_elapsed_ms = (time.perf_counter() - seg_start) * 1000
    result.seg_model_version = seg_result.model_version

    logger.info(
        "Segmentation: %d raw instances detected in %.1fms (model=%s)",
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

    # Debris & Peel filtering: exclude papery skin slivers, peel cutoffs, and foreign material
    raw_detections = seg_result.detections
    img_h, img_w = working_image.shape[:2]
    min_bulb_area = max(600, int(img_h * img_w * 0.0015))
    valid_detections: list[OnionDetection] = []
    for d in raw_detections:
        cnts, _ = cv2.findContours(d.mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts:
            continue
        c = max(cnts, key=cv2.contourArea)
        c_area = cv2.contourArea(c)
        if c_area < min_bulb_area:
            continue

        # ── Pile/background blob guard ─────────────────────────────────────────
        # A single onion bulb cannot span more than 88% of the image dimension.
        # This rejects entire-background pile floods while preserving genuine close-up shots.
        bbox_w_frac = d.bbox_w / max(1, img_w)
        bbox_h_frac = d.bbox_h / max(1, img_h)
        if bbox_w_frac > 0.88 or bbox_h_frac > 0.88:
            logger.info(
                "Pipeline: rejected over-sized detection (bbox %.0fx%.0f = %.0f%%x%.0f%% of image) - likely pile/background blob.",
                d.bbox_w, d.bbox_h, bbox_w_frac * 100, bbox_h_frac * 100,
            )
            continue

        # ── Mask area guard ────────────────────────────────────────────────────
        # No single onion can occupy more than 65% of the image pixel area.
        mask_frac = float(np.count_nonzero(d.mask)) / max(1, img_w * img_h)
        if mask_frac > 0.65:
            logger.info(
                "Pipeline: rejected detection with mask coverage %.1f%% - likely pile/background blob.",
                mask_frac * 100,
            )
            continue

        hull = cv2.convexHull(c)
        hull_area = max(1.0, float(cv2.contourArea(hull)))
        solidity = float(c_area) / hull_area
        peri = cv2.arcLength(c, True)
        circ = (4.0 * np.pi * c_area) / max(1.0, peri * peri)

        # Whole onion bulbs have convex, globular/oblate profiles (solidity >= 0.68)
        # Loose papery skins and debris flakes have notches, folds, or ragged fringes (solidity < 0.68)
        if solidity < 0.68:
            logger.debug("Pipeline: filtered out peel/skin debris (solidity=%.2f)", solidity)
            continue
        if circ < 0.30 and solidity < 0.78:
            logger.debug("Pipeline: filtered out non-bulb strip (circ=%.2f, sol=%.2f)", circ, solidity)
            continue
        valid_detections.append(d)

    # If all detections were filtered out as debris, keep the largest raw detection rather than failing
    if not valid_detections and raw_detections:
        logger.warning("All detections filtered by morphology; retaining largest detection as fallback.")
        valid_detections = [max(raw_detections, key=lambda d: cv2.countNonZero(d.mask))]

    # Re-index valid detections
    detections = [
        OnionDetection(
            bbox_x=vd.bbox_x,
            bbox_y=vd.bbox_y,
            bbox_w=vd.bbox_w,
            bbox_h=vd.bbox_h,
            mask=vd.mask,
            confidence=vd.confidence,
            touches_border=vd.touches_border,
            instance_index=i,
        )
        for i, vd in enumerate(valid_detections)
    ]

    # Refine autonomous scale with empirical bulb population prior.
    # Pile/background blobs have already been filtered above, so the remaining
    # detections are valid candidate bulbs.  We estimate the physical mm/px scale
    # by assuming the median detected bulb diameter in pixels corresponds to the
    # Indian APMC typical adult onion median diameter of 52.5mm.
    #
    # Weight: 75% empirical bulb-size prior + 25% FOV geometric prior.
    # The 700mm FOV geometric prior is calibrated for a ~65cm overhead bench shot
    # and is wildly wrong for close-up phone photos.  The empirical prior dominates.
    if calibration.is_estimated and len(detections) >= 1:
        bulb_diameters_px = []
        for d in detections:
            area_px = float(np.count_nonzero(d.mask))
            if area_px > 0:
                diam_px = 2.0 * np.sqrt(area_px / np.pi)
                # Only include plausible single-bulb pixel diameters (20px-2000px)
                if 20.0 < diam_px < 2000.0:
                    bulb_diameters_px.append(diam_px)

        if bulb_diameters_px:
            med_diam_px = float(np.median(bulb_diameters_px))
            # Indian APMC typical adult onion median equatorial diameter is 52.5mm
            if med_diam_px > 25.0:
                empirical_scale = 52.5 / med_diam_px
                # 75% bulb prior + 25% FOV geometric prior
                blended_scale = 0.25 * (calibration.scale_mm_per_px or 0.36) + 0.75 * empirical_scale
                blended_scale = float(np.clip(
                    blended_scale,
                    settings.scale_min_mm_per_px,
                    settings.scale_max_mm_per_px,
                ))
                calibration.scale_mm_per_px = blended_scale
                result.scale_mm_per_px = blended_scale
                logger.info(
                    "Refined autonomous scale with bulb prior (75%%/25%%): med_px=%.1f -> scale=%.4f mm/px",
                    med_diam_px, blended_scale,
                )

    # Post-processing quality checks
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

        # ── Physical Size Sanity Gate ─────────────────────────────────────────
        # No real Indian onion bulb has an equatorial diameter > 200mm or
        # estimated weight > 5000g (the world record is ~4.9kg at ~175mm).
        # If these limits are exceeded the detection is a background pile segment
        # that slipped through the bbox guard (e.g. an irregular shape).
        # Null out size_est so grading assigns NEEDS_REVIEW rather than REJECTED.
        if size_est is not None:
            eq_diam = size_est.equatorial_diameter_mm or size_est.equivalent_diameter_mm
            wt = size_est.estimated_weight_grams or 0.0
            if eq_diam > 200.0 or wt > 5000.0:
                logger.warning(
                    "Instance %d: physically impossible size (D=%.1fmm, W=%.0fg) - "
                    "likely background pile segment.  Nulling size_est.",
                    idx, eq_diam, wt,
                )
                size_est = None

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
                crop_mask = det.mask[det.bbox_y : det.bbox_y + det.bbox_h, det.bbox_x : det.bbox_x + det.bbox_w]
                morph = analyze_bulb_morphology(crop_image, crop_mask)
                if morph.is_double_bulb:
                    if "DOUBLE_BULB" not in grading.rejection_reasons:
                        grading.rejection_reasons.append("DOUBLE_BULB")
                    if grading.grade == "GRADE_A":
                        grading.grade = "REJECTED"
                        grading.explanation["double_bulb"] = (
                            f"Twin/double bulb detected (concavity depth {morph.max_concavity_depth_px:.1f}px). Disqualified from Grade A."
                        )

                # ── Chromatic Black Mold (Aspergillus niger) Override ────────
                # When significant black mold soot is verified (>15% surface area with L*<32, V<38, A<134),
                # we elevate rotten_prob to 0.90, triggering ROTTEN hard rejection.
                if morph.black_mold_pct >= 15.0 and defect_pred is not None:
                    boosted_rotten = max(defect_pred.rotten_prob, 0.90)
                    from cv.defect_classifier import DefectPrediction as _DP
                    defect_pred = _DP(
                        damaged_prob=defect_pred.damaged_prob,
                        rotten_prob=boosted_rotten,
                        sprouted_prob=defect_pred.sprouted_prob,
                        model_version=defect_pred.model_version + "+chromatic-mold",
                        is_mock=defect_pred.is_mock,
                    )
                    # Re-evaluate grading with boosted rotten_prob
                    grading = grading_engine.evaluate_bulb(
                        size_estimate=size_est,
                        defect_prediction=defect_pred,
                        confidence=confidence,
                    )
                    grading.explanation["black_mold_override"] = (
                        f"Aspergillus niger soot: {morph.black_mold_pct:.1f}% surface area "
                        f"(L*<42 & V<45 CIELAB/HSV). rotten_prob elevated to {boosted_rotten:.2f} → ROTTEN."
                    )
                    logger.info(
                        "Instance %d: black mold chromatic override %.1f%% → rotten_prob=%.2f",
                        idx, morph.black_mold_pct, boosted_rotten,
                    )

                # Attach morphology telemetry to explanation
                grading.explanation["circularity"] = f"{morph.circularity:.3f}"
                grading.explanation["surface_stain_pct"] = f"{morph.surface_stain_pct:.1f}%"
                grading.explanation["sunburn_pct"] = f"{morph.sunburn_pct:.1f}%"
                grading.explanation["black_mold_pct"] = f"{morph.black_mold_pct:.1f}%"
                grading.explanation["skin_baldness_pct"] = f"{morph.skin_baldness_pct:.1f}%"
                grading.explanation["ngrdi_mean"] = f"{morph.ngrdi_mean:.3f}"

                if size_est:
                    if size_est.equatorial_diameter_mm:
                        grading.explanation["equatorial_diameter_mm"] = f"{size_est.equatorial_diameter_mm:.1f}mm"
                    if size_est.polar_length_mm:
                        grading.explanation["polar_length_mm"] = f"{size_est.polar_length_mm:.1f}mm"
                    if size_est.shape_class:
                        grading.explanation["shape_class"] = size_est.shape_class
                    if size_est.estimated_weight_grams:
                        grading.explanation["estimated_weight_grams"] = f"{size_est.estimated_weight_grams:.0f}g"
                    if size_est.mandi_size_grade:
                        grading.explanation["mandi_size_grade"] = size_est.mandi_size_grade
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
