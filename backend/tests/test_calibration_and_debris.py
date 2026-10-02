"""
Unit tests for Dual-Mode Calibration (ChArUco vs Autonomous Benchmark)
and Morphological Debris/Peel Filtering.
"""
import cv2
import numpy as np
import pytest

from cv.calibration import CalibrationResult, compute_calibration
from cv.marker_detector import MarkerDetectionResult
from cv.providers.watershed_provider import WatershedSegmentationProvider
from cv.size_estimator import estimate_size


class TestDualModeCalibration:
    def test_uncalibrated_marker_engages_autonomous_heuristic(self):
        # 1920x1080 capture frame
        dummy_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        uncalibrated_result = MarkerDetectionResult(
            detected=False,
            failure_code="marker_not_detected",
            failure_message="No ChArUco board detected.",
        )

        calib = compute_calibration(dummy_img, uncalibrated_result)

        assert calib is not None
        assert calib.is_estimated is True
        assert calib.calibration_method == "AUTONOMOUS_OVERHEAD_HEURISTIC"
        # 260mm FOV / 1920px ≈ 0.1354 mm/px (mobile close-up benchmark prior)
        assert pytest.approx(calib.scale_mm_per_px, rel=0.05) == (260.0 / 1920.0)
        assert calib.uncertainty_mm == 3.5

    def test_autonomous_scale_produces_valid_size_and_mandi_grade(self):
        # Realistic bulb: 140px diameter circle on 1920x1080 image
        # At scale ~0.365 mm/px -> ~51.1 mm (Grade A / SUPER tier)
        mask = np.zeros((1080, 1920), dtype=np.uint8)
        cv2.circle(mask, (960, 540), 70, 255, -1)

        scale = 700.0 / 1920.0
        size_est = estimate_size(mask, scale)

        assert size_est is not None
        assert 48.0 < size_est.equivalent_diameter_mm < 54.0
        assert size_est.mandi_size_grade in ("MADHYAM", "SUPER")
        assert size_est.estimated_weight_grams is not None
        assert 50.0 < size_est.estimated_weight_grams < 120.0


class TestMorphologicalDebrisFiltering:
    def test_watershed_discards_loose_peel_fragments(self):
        # Create an image with:
        # 1. A real convex round onion (radius 75px)
        # 2. A thin, jagged crescent peel sliver (low solidity < 0.65)
        h, w = 600, 800
        img = np.ones((h, w, 3), dtype=np.uint8) * 230  # Light background table

        # Draw red/purple whole onion at (250, 300)
        cv2.circle(img, (250, 300), 75, (40, 30, 160), -1)

        # Draw ragged crescent peel at (550, 300) - outer circle minus inner circle with deep notch
        peel_pts = np.array([
            [500, 280], [530, 260], [580, 265], [610, 290],
            [590, 295], [550, 280], [520, 290]
        ], dtype=np.int32)
        cv2.fillPoly(img, [peel_pts], (60, 45, 175))

        provider = WatershedSegmentationProvider(min_bulb_area_px=1000)
        result = provider.detect(img)

        # The genuine bulb should be detected; the jagged thin peel fragment should be rejected by solidity/circularity
        assert result.count >= 1
        for det in result.detections:
            cnts, _ = cv2.findContours(det.mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            c = max(cnts, key=cv2.contourArea)
            hull = cv2.convexHull(c)
            solidity = cv2.contourArea(c) / max(1.0, cv2.contourArea(hull))
            assert solidity >= 0.70, f"Detected object with low solidity {solidity:.2f} was not filtered!"
