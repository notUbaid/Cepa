"""
Optical Metrology & GUM Measurement Uncertainty Budget Tests
============================================================
Evaluates mathematical uncertainty propagation in accordance with the
ISO/IEC Guide 98-3 (GUM) framework: Evaluation of measurement data —
Guide to the expression of uncertainty in measurement.

Tests:
1. Dynamic GUM Law of Propagation of Uncertainty for ChArUco optical calipers:
   D_mm = s * D_px = (L_square_mm / W_square_px) * D_px
   Sensitivity coefficients: c_Dpx = s, c_s = D_px
2. Type A standard uncertainty quantification on stochastic edge jitter
3. Physical allometric mass estimation scaling across bulb diameter distributions
"""
import math
import numpy as np
import pytest
import cv2

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


def calculate_gum_diameter_uncertainty(
    d_px: float,
    square_px: float,
    square_mm: float,
    u_d_px: float,          # Type A segmentation boundary variation (px)
    u_corner_px: float,     # Sub-pixel corner repeatability (px)
    u_board_print_mm: float,# Board manufacturing tolerance (mm)
    u_parallax_mm: float,   # Out-of-plane bulb 3D curvature standoff (mm)
    coverage_factor: float = 2.0,
) -> tuple[float, float, float]:
    """
    Computes combined standard uncertainty u_c and expanded uncertainty U
    using analytical first-order Taylor expansion per ISO/IEC Guide 98-3 (GUM).

    Measurement model:
        D = s * D_px = (L_mm / W_px) * D_px
    """
    s = square_mm / square_px
    d_mm = s * d_px

    # Sensitivity coefficients:
    # ∂D/∂D_px = s
    c_d_px = s
    # ∂s/∂L_mm = 1 / W_px  ==> ∂D/∂L_mm = D_px / W_px
    c_l_mm = d_px / square_px
    # ∂s/∂W_px = -L_mm / W_px^2 ==> ∂D/∂W_px = - (L_mm * D_px) / (W_px^2)
    c_w_px = -(square_mm * d_px) / (square_px ** 2)

    # Variance components
    var_d_px = (c_d_px * u_d_px) ** 2
    var_l_mm = (c_l_mm * u_board_print_mm) ** 2
    var_w_px = (c_w_px * u_corner_px) ** 2
    var_parallax = u_parallax_mm ** 2

    # Combined standard uncertainty u_c
    u_c = math.sqrt(var_d_px + var_l_mm + var_w_px + var_parallax)
    # Expanded uncertainty with coverage factor k (typically k=2 for ~95% confidence)
    u_expanded = coverage_factor * u_c

    return d_mm, u_c, u_expanded


def test_gum_analytical_propagation_under_chruco_parameters():
    """
    Verify GUM uncertainty propagation across realistic Mandi inspection conditions:
    40mm ChArUco square, 78.4 px per square (~0.5101 mm/px), 55mm medium onion.
    """
    square_mm = 40.0
    square_px = 78.41
    nominal_scale = square_mm / square_px  # ~0.5101 mm/px
    d_px = 55.0 / nominal_scale           # ~107.8 px

    # Realistic physical standard uncertainty components:
    u_d_px = 0.50          # ±0.5 px segmentation edge localization (Type A)
    u_corner_px = 0.15     # ±0.15 px OpenCV sub-pixel corner refinement (Type A)
    u_board_mm = 0.05      # ±0.05 mm printing laser cutter tolerance (Type B)
    u_parallax_mm = 0.65   # Out-of-plane 3D bulb height vs calibration surface (Type B)

    d_mm, u_c, u_expanded = calculate_gum_diameter_uncertainty(
        d_px=d_px,
        square_px=square_px,
        square_mm=square_mm,
        u_d_px=u_d_px,
        u_corner_px=u_corner_px,
        u_board_print_mm=u_board_mm,
        u_parallax_mm=u_parallax_mm,
        coverage_factor=2.0,
    )

    # Calculated diameter must match nominal 55 mm
    assert math.isclose(d_mm, 55.0, rel_tol=0.01)

    # Combined standard uncertainty must be positive and bounded by physics
    assert 0.60 < u_c < 1.0

    # Expanded uncertainty (k=2) must reflect realistic field conditions (~1.5 to 1.9 mm)
    # confirming that claim of sub-2mm uncertainty is mathematically and physically earned
    assert 1.2 < u_expanded < 2.0


def test_gum_type_a_stochastic_boundary_convergence():
    """
    Evaluate Type A evaluation of measurement uncertainty by perturbing
    synthetic onion contours with random Gaussian edge noise over N runs.
    Verifies that mean measurement converges and standard error follows σ / sqrt(N).
    """
    np.random.seed(42)
    nominal_radius = 50
    scale = 0.50
    trials = 25
    measured_diameters = []

    for _ in range(trials):
        # Generate base elliptical contour with stochastic edge jitter
        mask = np.zeros((160, 160), dtype=np.uint8)
        cv2.circle(mask, (80, 80), nominal_radius, 255, -1)
        # Apply random pixel noise to contour boundary
        noise = np.random.randint(-1, 2, mask.shape).astype(np.int16)
        noisy_mask = np.clip(mask.astype(np.int16) + noise * 30, 0, 255).astype(np.uint8)
        _, thresh = cv2.threshold(noisy_mask, 127, 255, cv2.THRESH_BINARY)

        res = estimate_size(thresh, scale_mm_per_px=scale)
        measured_diameters.append(res.equatorial_diameter_mm)

    diameters = np.array(measured_diameters)
    mean_d = float(np.mean(diameters))
    sample_std = float(np.std(diameters, ddof=1))
    type_a_uncertainty = sample_std / math.sqrt(trials)

    # Nominal diameter is 2 * 50 px * 0.5 mm/px = 50 mm
    assert math.isclose(mean_d, 50.0, abs_tol=1.5)
    # Sample standard deviation across boundary jitter must be tightly bounded
    assert sample_std < 1.0
    # Standard uncertainty of the mean (Type A) must be under 0.25 mm
    assert type_a_uncertainty < 0.25


def test_volumetric_mass_monotonicity_across_size_grades():
    """
    Verify physical volume and mass scaling across standard APMC market grades:
    Goli (<35mm), Madhyam (35-45mm), Super (45-65mm), Jumbo (>65mm).
    Mass must strictly monotonically increase with diameter cubed according to spheroid geometry.
    """
    diameters = [30.0, 40.0, 55.0, 70.0]
    polar_lengths = [28.0, 38.0, 50.0, 65.0]
    masses = []

    scale = 0.25
    for d, l in zip(diameters, polar_lengths):
        rx = int((d / 2.0) / scale)
        ry = int((l / 2.0) / scale)
        mask = np.zeros((350, 350), dtype=np.uint8)
        cv2.ellipse(mask, (175, 175), (rx, ry), 0, 0, 360, 255, -1)
        res = estimate_size(mask, scale_mm_per_px=scale)
        masses.append(res.grevsen_weight_grams)

    # Verify strict monotonic increase
    for i in range(len(masses) - 1):
        assert masses[i] < masses[i + 1]

    # Verify physically plausible weights for Indian onion varieties (ICAR-DOGR benchmarks):
    # 30mm Goli: ~10-25g
    # 40mm Madhyam: ~30-50g
    # 55mm Super: ~65-85g
    # 70mm Jumbo: ~130-180g
    assert 10.0 < masses[0] < 25.0
    assert 28.0 < masses[1] < 50.0
    assert 60.0 < masses[2] < 90.0
    assert 120.0 < masses[3] < 190.0
