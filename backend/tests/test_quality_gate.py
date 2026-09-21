"""
Unit tests for Stage 1 Image Quality Gate.
"""
import cv2
import numpy as np
import pytest

from cv.quality_gate import (
    FAIL_EXCESSIVE_GLARE,
    FAIL_IMAGE_TOO_BLURRY,
    FAIL_INSUFFICIENT_RESOLUTION,
    FAIL_TOO_BRIGHT,
    FAIL_TOO_DARK,
    check_image_quality,
)


def _create_sharp_image(width: int = 1200, height: int = 1200) -> np.ndarray:
    """Create a sharp test image with rich high-frequency textures and normal lighting."""
    img = np.full((height, width, 3), 128, dtype=np.uint8)
    # Add high-contrast fine checkerboard pattern to produce high Laplacian variance
    grid_size = 10
    for y in range(0, height, grid_size):
        for x in range(0, width, grid_size):
            if (x // grid_size + y // grid_size) % 2 == 0:
                img[y : y + grid_size, x : x + grid_size] = [40, 40, 40]
            else:
                img[y : y + grid_size, x : x + grid_size] = [210, 210, 210]
    # Add high-contrast text and edges
    cv2.putText(img, "TEST QUALITY GATE", (100, 200), cv2.FONT_HERSHEY_SIMPLEX, 3, (255, 255, 255), 6)
    return img


class TestQualityGate:
    def test_sharp_well_lit_image_passes(self):
        img = _create_sharp_image()
        result = check_image_quality(img)
        assert result.passed is True
        assert len(result.failures) == 0

    def test_insufficient_resolution_fails(self):
        # 600x600 < 1000 threshold
        img = np.full((600, 600, 3), 128, dtype=np.uint8)
        result = check_image_quality(img)
        assert result.passed is False
        assert FAIL_INSUFFICIENT_RESOLUTION in result.failures

    def test_blurry_image_fails(self):
        img = _create_sharp_image()
        # Heavy Gaussian blur removes high-frequency content
        blurry = cv2.GaussianBlur(img, (75, 75), 30)
        result = check_image_quality(blurry)
        assert result.passed is False
        assert FAIL_IMAGE_TOO_BLURRY in result.failures

    def test_too_dark_image_fails(self):
        # Mean luminance < 40
        dark_img = np.full((1200, 1200, 3), 20, dtype=np.uint8)
        result = check_image_quality(dark_img)
        assert result.passed is False
        assert FAIL_TOO_DARK in result.failures

    def test_too_bright_image_fails(self):
        # Mean luminance > 215
        bright_img = np.full((1200, 1200, 3), 235, dtype=np.uint8)
        result = check_image_quality(bright_img)
        assert result.passed is False
        assert FAIL_TOO_BRIGHT in result.failures

    def test_excessive_glare_fails(self):
        img = _create_sharp_image()
        # Make > 6% of pixels pure blown-out white (>250 in all channels)
        img[:350, :350] = [255, 255, 255]
        result = check_image_quality(img)
        assert result.passed is False
        assert FAIL_EXCESSIVE_GLARE in result.failures
