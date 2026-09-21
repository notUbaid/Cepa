"""
Unit and Integration Tests for Advanced Mandi Morphometry, Volumetric Mass,
Multi-Spectral Defect Analysis, and NAFED Commercial FAQ Pricing.
"""
from __future__ import annotations

import math
import numpy as np
import cv2
import pytest
from fastapi.testclient import TestClient

from cv.size_estimator import estimate_size, SizeEstimate, ONION_BULK_DENSITY_G_PER_MM3
from cv.advanced_features import analyze_bulb_morphology
from grading.statistics import (
    compute_apmc_size_distribution,
    compute_lot_weight_statistics,
    compute_commercial_pricing,
    evaluate_lot_statistics,
)
from main import app


class TestMandiMorphometryAndSizing:
    """Test geometric caliper axes, shape classification, and volumetric mass."""

    def test_circular_bulb_equatorial_and_polar_axes(self):
        """A near-circular contour should yield roughly equal equatorial and polar dimensions."""
        mask = np.zeros((300, 300), dtype=np.uint8)
        # Radius 50px circle -> Diameter = 100px. Scale = 0.5 mm/px -> ~50mm diameter
        cv2.circle(mask, (150, 150), 50, 255, -1)
        scale = 0.5

        size = estimate_size(mask, scale_mm_per_px=scale)
        assert size is not None
        assert abs(size.equivalent_diameter_mm - 50.0) < 2.0
        assert size.equatorial_diameter_mm is not None
        assert size.polar_length_mm is not None
        assert size.shape_class in ("GLOBULAR", "OBLATE")
        assert size.mandi_size_grade == "SUPER"  # 50mm is in 45-65mm NAFED Grade A range

        # Check volumetric weight
        expected_vol = (math.pi / 6.0) * (size.equatorial_diameter_mm ** 2) * size.polar_length_mm
        expected_weight = expected_vol * ONION_BULK_DENSITY_G_PER_MM3
        assert size.estimated_weight_grams is not None
        assert abs(size.estimated_weight_grams - expected_weight) < 1.0

    def test_oblate_bulb_shape_classification(self):
        """Flatter onion (Nashik Red style) where polar axis < equatorial diameter."""
        mask = np.zeros((300, 300), dtype=np.uint8)
        # Ellipse with axes 60px wide, 35px high
        cv2.ellipse(mask, (150, 150), (60, 35), 0, 0, 360, 255, -1)
        scale = 0.5  # Equatorial ~ 60mm, Polar ~ 35mm -> shape_index ~ 0.58 (<0.82 -> OBLATE)

        size = estimate_size(mask, scale_mm_per_px=scale)
        assert size is not None
        assert size.shape_class == "OBLATE"
        assert size.shape_index < 0.82
        assert size.mandi_size_grade == "SUPER"  # ~60mm is Super

    def test_goli_baby_onion_mandi_grade(self):
        """Small bulb with diameter < 35mm should be classified as GOLI."""
        mask = np.zeros((200, 200), dtype=np.uint8)
        # Radius 25px -> diam 50px. Scale = 0.5 mm/px -> ~25mm diameter (< 35mm)
        cv2.circle(mask, (100, 100), 25, 255, -1)
        size = estimate_size(mask, scale_mm_per_px=0.5)
        assert size is not None
        assert size.mandi_size_grade == "GOLI"

    def test_jumbo_oversized_onion_mandi_grade(self):
        """Large bulb with diameter > 65mm should be classified as JUMBO."""
        mask = np.zeros((400, 400), dtype=np.uint8)
        # Radius 75px -> diam 150px. Scale = 0.5 mm/px -> ~75mm diameter (> 65mm)
        cv2.circle(mask, (200, 200), 75, 255, -1)
        size = estimate_size(mask, scale_mm_per_px=0.5)
        assert size is not None
        assert size.mandi_size_grade == "JUMBO"


class TestMultiSpectralDefectAnalysis:
    """Test pathological defect extraction (Black mold, Sunburn NGRDI, Double bulb)."""

    def test_double_bulb_concavity_detection(self):
        """Fused twin bulb with deep waist indentation triggers double bulb."""
        mask = np.zeros((300, 300), dtype=np.uint8)
        # Draw two intersecting circles forming twin bulb
        cv2.circle(mask, (115, 150), 45, 255, -1)
        cv2.circle(mask, (185, 150), 45, 255, -1)
        crop = np.zeros((300, 300, 3), dtype=np.uint8)
        crop[mask > 0] = [50, 70, 180]  # red onion color

        morph = analyze_bulb_morphology(crop, mask)
        assert morph.is_double_bulb is True
        assert morph.max_concavity_depth_px > 5.0

    def test_black_mold_aspergillus_detection(self):
        """Dark black fungal spore patches should trigger black_mold_pct."""
        mask = np.zeros((200, 200), dtype=np.uint8)
        cv2.circle(mask, (100, 100), 60, 255, -1)
        crop = np.zeros((200, 200, 3), dtype=np.uint8)
        crop[mask > 0] = [40, 60, 170]  # base red onion
        # Add black mold patch
        cv2.circle(crop, (100, 100), 30, (15, 15, 20), -1)

        morph = analyze_bulb_morphology(crop, mask)
        assert morph.black_mold_pct > 10.0
        assert morph.defect_area_pct > 10.0

    def test_sunburn_chlorophyll_ngrdi_index(self):
        """Green shoulder exposure should produce positive NGRDI and sunburn percentage."""
        mask = np.zeros((200, 200), dtype=np.uint8)
        cv2.circle(mask, (100, 100), 60, 255, -1)
        crop = np.zeros((200, 200, 3), dtype=np.uint8)
        # Strong green chlorophyll shoulder
        crop[mask > 0] = [30, 190, 70]  # BGR with dominant Green

        morph = analyze_bulb_morphology(crop, mask)
        assert morph.sunburn_pct > 50.0
        assert morph.ngrdi_mean > 0.0  # (G - R) / (G + R) > 0


class TestCommercialPricingAndDockage:
    """Test Fair Average Quality (FAQ) MSP rate deduction and APMC statistics."""

    def test_full_payout_for_clean_grade_a_lot(self):
        """Lots with <= 5% off-grade should receive full procurement payout."""
        pricing = compute_commercial_pricing(
            grade_a_pct=96.0,
            urs_pct=4.0,
            rejected_pct=0.0,
            critical_defect_pct=0.0,
            base_rate_inr_per_qtl=1800.0,
        )
        assert pricing.payment_tier == "FULL_PRICE"
        assert pricing.dockage_rate_inr_per_qtl == 0.0
        assert pricing.net_procurement_rate_inr_per_qtl == 1800.0

    def test_proportional_dockage_for_moderate_defects(self):
        """Lots with excess off-grade variance above 5% should receive proportional dockage."""
        pricing = compute_commercial_pricing(
            grade_a_pct=75.0,  # 25% off-grade -> 20% excess over 5%
            urs_pct=20.0,
            rejected_pct=5.0,
            critical_defect_pct=2.0,
            base_rate_inr_per_qtl=1800.0,
        )
        assert pricing.payment_tier == "PROPORTIONAL_DOCKAGE"
        assert pricing.excess_defects_pct == 20.0
        # Dockage = 1800 * (20/100) * 0.75 = 270 INR/qtl
        assert abs(pricing.dockage_rate_inr_per_qtl - 270.0) < 1.0
        assert abs(pricing.net_procurement_rate_inr_per_qtl - 1530.0) < 1.0

    def test_rejection_and_zero_payout_for_high_rot(self):
        """Lots with critical rot > 5% must be rejected with zero payout."""
        pricing = compute_commercial_pricing(
            grade_a_pct=60.0,
            urs_pct=20.0,
            rejected_pct=20.0,
            critical_defect_pct=8.0,  # Critical decay > 5%
            base_rate_inr_per_qtl=1800.0,
        )
        assert pricing.payment_tier == "REJECT_NO_PAYOUT"
        assert pricing.net_procurement_rate_inr_per_qtl == 0.0

    def test_apmc_size_distribution_breakdown(self):
        """Sizes should be properly binned into Goli, Madhyam, Super, Jumbo."""
        sizes = [28.0, 32.0, 40.0, 52.0, 58.0, 62.0, 72.0]  # 2 Goli, 1 Madhyam, 3 Super, 1 Jumbo
        apmc = compute_apmc_size_distribution(sizes)
        assert apmc.goli_count == 2
        assert apmc.madhyam_count == 1
        assert apmc.super_count == 3
        assert apmc.jumbo_count == 1
        assert abs(apmc.super_pct - (3 / 7 * 100.0)) < 0.2


class TestInteractiveInspectorEndpoint:
    """Test that the live Mandi Inspector studio is served at /inspector."""

    def test_inspector_endpoint_returns_html(self):
        client = TestClient(app)
        response = client.get("/inspector")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "CEPA — SIH26031 Mandi Inspection Studio" in response.text
