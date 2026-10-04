"""
Test Suite: Onion Authenticity Verification & Non-Onion Rejection
=================================================================
Verifies that:
1. Genuine onion bulbs (Nashik Red, Garwa, Rangada, yellow/brown, white, sprouted)
   are authenticated with 100% stability and reliability (zero false negatives).
2. Non-onion produce (apples, oranges, tomatoes, lemons, bananas, cucumbers)
   and non-produce items (tennis balls, mugs, pens) are strictly rejected.
3. The end-to-end pipeline returns quality_passed=False and 'Onion not detected'
   when no authentic onions are visible in the capture.
"""
from __future__ import annotations

import cv2
import numpy as np
import pytest
from pathlib import Path

from cv.onion_validator import OnionAuthenticityValidator
from cv.pipeline import run_pipeline
from cv.providers.watershed_provider import WatershedSegmentationProvider
from cv.defect_classifier import MockDefectClassifier
from grading.policy_loader import load_policy


class TestOnionAuthenticityValidatorUnit:
    """Unit tests for OnionAuthenticityValidator on diverse produce and object crops."""

    def test_synthetic_nashik_red_onion_accepted(self):
        """Authentic red onion with characteristic anthocyanin/quercetin spectrum."""
        # Nashik red / Garwa: burgundy/copper tone (H ~ 167 in OpenCV HSV)
        crop = np.full((120, 130, 3), (65, 30, 110), dtype=np.uint8)
        # Add natural botanical variation (tunic layers)
        crop[30:90, 30:100] = (50, 40, 130)
        res = OnionAuthenticityValidator.validate_candidate(crop)
        assert res.is_onion is True, f"Expected red onion to be accepted, got: {res.rejection_reason}"

    def test_synthetic_yellow_brown_onion_accepted(self):
        """Authentic golden straw / brown storage onion."""
        # Yellow onion: golden ochre (H ~ 18 in OpenCV HSV)
        crop = np.full((120, 125, 3), (60, 120, 160), dtype=np.uint8)
        crop[40:80, 40:80] = (50, 110, 150)
        res = OnionAuthenticityValidator.validate_candidate(crop)
        assert res.is_onion is True, f"Expected yellow onion to be accepted, got: {res.rejection_reason}"

    def test_synthetic_white_onion_accepted(self):
        """Authentic white / parchment onion."""
        # White onion: high lightness, low saturation, warm ivory tint
        crop = np.full((120, 120, 3), (180, 195, 205), dtype=np.uint8)
        res = OnionAuthenticityValidator.validate_candidate(crop)
        assert res.is_onion is True, f"Expected white onion to be accepted, got: {res.rejection_reason}"

    def test_sprouted_onion_accepted(self):
        """Authentic onion with small localized green sprout at apex."""
        crop = np.full((140, 130, 3), (65, 30, 110), dtype=np.uint8)
        # Small green sprout (< 20% of area)
        crop[0:25, 55:75] = (25, 180, 50)
        res = OnionAuthenticityValidator.validate_candidate(crop)
        assert res.is_onion is True, f"Expected sprouted onion to be accepted, got: {res.rejection_reason}"

    def test_red_apple_rejected(self):
        """Glossy scarlet red apple is rejected."""
        crop = np.full((120, 120, 3), (20, 20, 225), dtype=np.uint8)
        res = OnionAuthenticityValidator.validate_candidate(crop)
        assert res.is_onion is False
        assert "scarlet_tomato_or_red_apple" in res.rejection_reason

    def test_green_apple_rejected(self):
        """Green apple is rejected."""
        crop = np.full((120, 120, 3), (25, 210, 30), dtype=np.uint8)
        res = OnionAuthenticityValidator.validate_candidate(crop)
        assert res.is_onion is False
        assert "green_produce_not_onion" in res.rejection_reason

    def test_citrus_orange_rejected(self):
        """Citrus orange is rejected."""
        crop = np.full((120, 120, 3), (0, 140, 255), dtype=np.uint8)
        res = OnionAuthenticityValidator.validate_candidate(crop)
        assert res.is_onion is False
        assert "citrus_orange_not_onion" in res.rejection_reason

    def test_yellow_lemon_rejected(self):
        """Yellow lemon is rejected."""
        crop = np.full((120, 120, 3), (30, 230, 240), dtype=np.uint8)
        res = OnionAuthenticityValidator.validate_candidate(crop)
        assert res.is_onion is False
        assert "lemon_or_yellow_produce" in res.rejection_reason

    def test_banana_rejected_by_aspect_ratio(self):
        """Banana is rejected due to elongated aspect ratio."""
        crop = np.full((60, 210, 3), (20, 215, 235), dtype=np.uint8)
        res = OnionAuthenticityValidator.validate_candidate(crop)
        assert res.is_onion is False
        assert "invalid_aspect_ratio" in res.rejection_reason

    def test_cucumber_rejected_by_aspect_ratio_and_green(self):
        """Cucumber is rejected."""
        crop = np.full((50, 200, 3), (30, 120, 40), dtype=np.uint8)
        res = OnionAuthenticityValidator.validate_candidate(crop)
        assert res.is_onion is False

    def test_red_tomato_rejected(self):
        """Scarlet red tomato is rejected."""
        crop = np.full((120, 120, 3), (15, 10, 230), dtype=np.uint8)
        res = OnionAuthenticityValidator.validate_candidate(crop)
        assert res.is_onion is False
        assert "scarlet_tomato_or_red_apple" in res.rejection_reason or "synthetic_neon_object" in res.rejection_reason

    def test_tennis_ball_rejected(self):
        """Neon chartreuse tennis ball is rejected."""
        crop = np.full((120, 120, 3), (40, 245, 230), dtype=np.uint8)
        res = OnionAuthenticityValidator.validate_candidate(crop)
        assert res.is_onion is False
        assert "lemon_or_yellow_produce" in res.rejection_reason or "synthetic_neon_object" in res.rejection_reason

    def test_blue_mug_rejected(self):
        """Blue artificial object is rejected."""
        crop = np.full((120, 120, 3), (220, 100, 20), dtype=np.uint8)
        res = OnionAuthenticityValidator.validate_candidate(crop)
        assert res.is_onion is False
        assert "artificial_blue_cyan_object" in res.rejection_reason


class TestOnionAuthenticityRealImages:
    """Verifies that authentic real onions from repository datasets pass with high recall."""

    def test_demo_spread_authenticates_genuine_onions(self):
        img_path = Path(__file__).parent.parent / "static" / "demo_onion_spread.jpg"
        if not img_path.exists():
            pytest.skip("demo_onion_spread.jpg not available")
        img = cv2.imread(str(img_path))
        assert img is not None

        ws = WatershedSegmentationProvider()
        res = ws.detect(img)
        assert res.count > 0

        auth, _ = OnionAuthenticityValidator.filter_detections(img, res.detections)
        assert len(auth) >= 1, "At least one authentic onion must be validated from demo spread"

    def test_real_red_onions_authenticated(self):
        """Authentic red onions from real-world mandi capture must not be rejected by ImageNet sphere-mimic."""
        img_path = Path(__file__).parent.parent / "static" / "test_red_onions.jpg"
        if not img_path.exists():
            pytest.skip("test_red_onions.jpg not available")
        img = cv2.imread(str(img_path))
        assert img is not None

        from cv.providers.yolo11_provider import YOLO11SegmentationProvider
        from config import settings
        yolo = YOLO11SegmentationProvider(model_path=settings.seg_model_path)
        res = yolo.detect(img)
        assert res.count > 0, "YOLO must detect candidate bulbs in real red onion image"

        auth, rejected = OnionAuthenticityValidator.filter_detections(img, res.detections)
        assert len(auth) >= 1, f"Authentic red onions must pass verification (got rejected: {rejected})"



class TestPipelineNonOnionRejection:
    """Verifies end-to-end pipeline failure when non-onion objects are presented."""

    def test_pipeline_rejects_apples_with_onion_not_detected(self):
        # 800x600 table with 3 shiny apples (red, green, and orange)
        img = np.full((600, 800, 3), 215, dtype=np.uint8)
        cv2.circle(img, (200, 300), 75, (20, 20, 220), -1)  # Red apple
        cv2.circle(img, (400, 300), 75, (25, 210, 30), -1)  # Green apple
        cv2.circle(img, (600, 300), 75, (0, 140, 255), -1)  # Orange

        _, enc = cv2.imencode(".jpg", img)
        image_bytes = enc.tobytes()

        policies_dir = Path(__file__).parent.parent / "grading" / "policies"
        policy = load_policy("DEMO_ASSUMPTION_v1", policies_dir)
        ws_provider = WatershedSegmentationProvider()
        mock_defect = MockDefectClassifier()

        res = run_pipeline(
            image_bytes=image_bytes,
            inspection_id="test-insp-non-onion",
            sample_id="test-sample-apple",
            seg_provider=ws_provider,
            defect_classifier=mock_defect,
            policy=policy,
        )

        assert res.quality_passed is False
        assert "no_onions_detected" in res.quality_flags
        assert "Onion not detected" in res.failure_message
        assert res.instances == []
