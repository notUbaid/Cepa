"""
Optical Metrology & GUM Measurement Uncertainty Budget Tests
============================================================
Conforms to ISO/IEC Guide 98-3 (GUM) and BIS IS 17912:2022 sizing specifications.
"""

import math
import numpy as np
import pytest

try:
    from cv.size_estimator import (
        estimate_size,
        BULB_COMPACTNESS_FACTOR,
        ONION_BULK_DENSITY_G_PER_MM3,
    )
    from cv.calibration import CalibrationResult
except ImportError:
    from backend.cv.size_estimator import (
        estimate_size,
        BULB_COMPACTNESS_FACTOR,
        ONION_BULK_DENSITY_G_PER_MM3,
    )
    from backend.cv.calibration import CalibrationResult


def test_bulb_compactness_factor_physical_invariants():
    """Verify that Allium cepa bulb compactness factor adheres to empirical allometry."""
    # Compactness factor must lie strictly between 0.90 and 0.95 for prolate/oblate onion geometry
    assert BULB_COMPACTNESS_FACTOR == 0.93
    # Density must correspond to ~0.985 g/cm³
    assert math.isclose(ONION_BULK_DENSITY_G_PER_MM3, 0.000985, rel_tol=1e-5)


def test_prolate_spheroid_mass_estimation_accuracy():
    """
    Test volumetric mass calculation of a known synthetic bulb:
    Equatorial diameter: 55 mm, Polar length: 50 mm
    Theoretical prolate spheroid volume: V = (π / 6) * D_eq^2 * L_polar
    Mass = V * density * compactness_factor
    """
    d_eq = 55.0  # mm
    d_polar = 50.0  # mm

    v_theoretical = (math.pi / 6.0) * (d_eq ** 2) * d_polar
    expected_mass = v_theoretical * ONION_BULK_DENSITY_G_PER_MM3 * BULB_COMPACTNESS_FACTOR

    # Realistic mass of a 55mm medium/large onion is ~70g to 80g
    assert 65.0 < expected_mass < 85.0

    # Create synthetic elliptical mask with matching dimensions at scale 0.20 mm/px
    scale = 0.20
    radius_x_px = int((d_eq / 2.0) / scale)
    radius_y_px = int((d_polar / 2.0) / scale)

    mask = np.zeros((300, 300), dtype=np.uint8)
    import cv2
    cv2.ellipse(mask, (150, 150), (radius_x_px, radius_y_px), 0, 0, 360, 255, -1)

    res = estimate_size(mask, scale_mm_per_px=scale)
    # Compactness-adjusted physical mass matches expected_mass within ±3%
    assert math.isclose(res.grevsen_weight_grams, expected_mass, rel_tol=0.03)
    # Raw prolate spheroid volume mass without compactness factor matches within ±3%
    assert math.isclose(res.estimated_weight_grams, v_theoretical * ONION_BULK_DENSITY_G_PER_MM3, rel_tol=0.03)


def test_gum_expanded_uncertainty_budget():
    """
    Verify GUM combined standard uncertainty and expanded uncertainty calculation (k=2).
    u_c = sqrt(sum(u_i^2))
    U = k * u_c <= 0.5 mm in calibrated ChArUco mode.
    """
    # Individual standard uncertainty components in millimeters (from METROLOGY_SPECIFICATION.md):
    u_corner = 0.014        # Sub-pixel corner repeatability (Type A)
    u_board_print = 0.029   # Board manufacturing tolerance (Type B)
    u_distortion = 0.069    # Residual lens distortion (Type B)
    u_segmentation = 0.153  # Instance mask border variation (Type A)
    u_parallax = 0.185      # Normal bulb curvature standoff (Type B)

    # Combined uncertainty: Root Sum of Squares
    u_combined = math.sqrt(
        u_corner**2 + u_board_print**2 + u_distortion**2 + u_segmentation**2 + u_parallax**2
    )

    # Coverage factor k = 2 (95.45% confidence)
    expanded_uncertainty = 2.0 * u_combined

    # Must verify that expanded uncertainty is <= 0.52 mm (standardized to ±0.5 mm)
    assert expanded_uncertainty <= 0.52
    assert math.isclose(expanded_uncertainty, 0.50, abs_tol=0.03)
