"""
Unit tests for Stage 7 Size Estimator.
"""
import math
import cv2
import numpy as np
import pytest

from cv.size_estimator import estimate_size


class TestSizeEstimator:
    def test_circular_mask_equivalent_diameter(self):
        # Create a 2000x2000 mask with a perfect circle of radius R=100 pixels
        mask = np.zeros((1000, 1000), dtype=np.uint8)
        radius_px = 100
        center = (500, 500)
        cv2.circle(mask, center, radius_px, 255, -1)

        scale_mm_per_px = 0.5  # 1 pixel = 0.5 mm -> expected diameter = 200 * 0.5 = 100.0 mm
        result = estimate_size(mask, scale_mm_per_px)

        assert result is not None
        # Theoretical area = pi * R^2 ≈ 31415.9
        # Theoretical equiv diameter = 2 * sqrt(area / pi) * 0.5 ≈ 200 * 0.5 = 100.0 mm
        assert pytest.approx(result.equivalent_diameter_mm, rel=1e-2) == 100.0
        assert result.scale_mm_per_px == 0.5
        assert result.mask_area_px > 30000

    def test_missing_scale_returns_none(self):
        mask = np.zeros((200, 200), dtype=np.uint8)
        cv2.circle(mask, (100, 100), 50, 255, -1)
        assert estimate_size(mask, scale_mm_per_px=None) is None

    def test_empty_mask_returns_none(self):
        mask = np.zeros((200, 200), dtype=np.uint8)
        assert estimate_size(mask, scale_mm_per_px=0.5) is None

    def test_uncertainty_flag_near_threshold(self):
        # Target diameter ≈ 45.0 mm (Grade A min threshold)
        # 45 mm / 0.5 mm_per_px = 90 px diameter -> radius = 45 px
        mask = np.zeros((500, 500), dtype=np.uint8)
        cv2.circle(mask, (250, 250), 45, 255, -1)

        thresholds = [35.0, 45.0, 65.0, 70.0]
        result = estimate_size(mask, scale_mm_per_px=0.5, thresholds_mm=thresholds)

        assert result is not None
        # Since measured diameter is ~45mm, it is within 3mm of threshold 45.0
        assert result.uncertainty_flag is True

    def test_uncertainty_flag_far_from_threshold(self):
        # Target diameter ≈ 55.0 mm (right in middle of 45-65, >3mm away from all thresholds)
        # 55 mm / 0.5 mm_per_px = 110 px diameter -> radius = 55 px
        mask = np.zeros((500, 500), dtype=np.uint8)
        cv2.circle(mask, (250, 250), 55, 255, -1)

        thresholds = [35.0, 45.0, 65.0, 70.0]
        result = estimate_size(mask, scale_mm_per_px=0.5, thresholds_mm=thresholds)

        assert result is not None
        assert abs(result.equivalent_diameter_mm - 55.0) < 1.0
        assert result.uncertainty_flag is False
