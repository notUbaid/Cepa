"""
Stage 7: Geometric Size, Polar/Equatorial Morphometry & Volumetric Mass Estimation

Estimates physical size, equatorial caliper diameter, polar axis length,
bulb shape index, and volumetric weight from segmentation masks and mm/pixel scale.

Conforms to:
- BIS IS 17912:2022 (Supply Chain of Onions — Guidelines for Grading and Handling)
- NAFED & APMC Mandi Sizing Specs (Goli, Madhyam, Super, Jumbo)
- ICAR-DOGR (Directorate of Onion and Garlic Research) onion density standards

Primary metrics:
1. equivalent_diameter_mm: 2 × √(mask_area_px / π) × mm_per_px
2. equatorial_diameter_mm: Maximum cross-section perpendicular to polar axis
3. polar_length_mm: Distance from stem apex to root basal plate
4. shape_index: polar_length_mm / equatorial_diameter_mm
   - OBLATE (< 0.82)
   - GLOBULAR (0.82 to 1.15)
   - TORPEDO (> 1.15)
5. estimated_weight_grams: Volumetric mass estimation using prolate/oblate spheroid
   formula: V = (π / 6) × D_eq² × L_polar, mass = V × ρ (ρ ≈ 0.985 g/cm³)
6. mandi_size_grade:
   - GOLI (< 35 mm)
   - MADHYAM (35 - 45 mm)
   - SUPER (45 - 65 mm — NAFED Grade A)
   - JUMBO (> 65 mm)
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass

import cv2
import numpy as np

from models.measurement import PROJECTION_NOTE

logger = logging.getLogger(__name__)

# Specific bulk density of fresh Allium cepa bulbs (g/cm³ -> g/mm³)
# 0.985 g/cm³ = 0.000985 g/mm³
ONION_BULK_DENSITY_G_PER_MM3 = 0.000985


@dataclass
class SizeEstimate:
    """Complete geometric and physical mass measurements for one onion bulb."""
    equivalent_diameter_mm: float
    major_axis_mm: float | None = None
    minor_axis_mm: float | None = None
    equatorial_diameter_mm: float | None = None
    polar_length_mm: float | None = None
    shape_index: float | None = None
    shape_class: str | None = None              # "OBLATE", "GLOBULAR", "TORPEDO"
    estimated_weight_grams: float | None = None  # in grams
    mandi_size_grade: str | None = None         # "GOLI", "MADHYAM", "SUPER", "JUMBO"
    polar_endpoints: tuple[tuple[int, int], tuple[int, int]] | None = None
    equatorial_endpoints: tuple[tuple[int, int], tuple[int, int]] | None = None
    mask_area_px: int = 0
    scale_mm_per_px: float = 0.0
    projection_note: str = PROJECTION_NOTE
    uncertainty_flag: bool = False              # Set if near policy boundary


def _detect_stem_and_root_poles(
    contour: np.ndarray,
) -> tuple[tuple[int, int], tuple[int, int], float, float]:
    """
    Detect the stem apex and root basal plate on the contour.
    Returns:
        (pole_apex, pole_base, polar_len_px, equatorial_diam_px)
    """
    if len(contour) < 5:
        x, y, w, h = cv2.boundingRect(contour)
        p1 = (x + w // 2, y)
        p2 = (x + w // 2, y + h)
        return p1, p2, float(h), float(w)

    # Fit rotated bounding box for principal orientations
    rect = cv2.minAreaRect(contour)
    (cx, cy), (dim1, dim2), angle = rect

    # Ellipse fit
    try:
        (_, _), (dim_minor, dim_major), el_angle = cv2.fitEllipse(contour)
        ax_minor = min(dim_minor, dim_major)
        ax_major = max(dim_minor, dim_major)
    except Exception:
        ax_minor, ax_major = min(dim1, dim2), max(dim1, dim2)
        el_angle = angle

    aspect = ax_minor / max(1.0, ax_major)

    # Unit vectors for major and minor axes
    rad_maj = np.radians(el_angle)
    u_maj = np.array([np.sin(rad_maj), -np.cos(rad_maj)], dtype=np.float32)
    u_min = np.array([np.cos(rad_maj), np.sin(rad_maj)], dtype=np.float32)

    # Check for sharp local curvature spike (vegetative sprout or pointed neck)
    pts = contour[:, 0, :]
    n_pts = len(pts)
    step = max(2, n_pts // 30)

    curvatures = np.zeros(n_pts, dtype=np.float32)
    for i in range(n_pts):
        p_prev = pts[(i - step) % n_pts]
        p_curr = pts[i]
        p_next = pts[(i + step) % n_pts]
        v1 = p_curr - p_prev
        v2 = p_next - p_curr
        n1 = np.linalg.norm(v1)
        n2 = np.linalg.norm(v2)
        if n1 > 0 and n2 > 0:
            cos_t = np.dot(v1, v2) / (n1 * n2)
            curvatures[i] = 1.0 - np.clip(cos_t, -1.0, 1.0)

    max_k = float(np.max(curvatures))
    med_k = float(np.median(curvatures)) + 1e-5
    has_curvature_spike = (max_k / med_k) > 4.0

    # Decision: Oblate vs Torpedo/Globular
    # In Indian onions (Nashik Red, Bellary), flat/oblate varieties have the stem and root
    # along the MINOR axis and the equatorial caliper along the MAJOR axis (S < 0.82).
    if aspect < 0.82:
        # Oblate bulb: Polar axis is along minor axis, Equator is along major axis
        p1 = (int(cx + (ax_minor / 2.0) * u_min[0]), int(cy + (ax_minor / 2.0) * u_min[1]))
        p2 = (int(cx - (ax_minor / 2.0) * u_min[0]), int(cy - (ax_minor / 2.0) * u_min[1]))
        polar_len_px = float(ax_minor)
        eq_diam_px = float(ax_major)
        return p1, p2, max(1.0, polar_len_px), max(1.0, eq_diam_px)

    # For elongated or spurred bulbs, polar axis is along major axis
    p1 = (int(cx + (ax_major / 2.0) * u_maj[0]), int(cy + (ax_major / 2.0) * u_maj[1]))
    p2 = (int(cx - (ax_major / 2.0) * u_maj[0]), int(cy - (ax_major / 2.0) * u_maj[1]))
    polar_len_px = float(ax_major)
    eq_diam_px = float(ax_minor)

    return p1, p2, max(1.0, polar_len_px), max(1.0, eq_diam_px)


def estimate_size(
    mask: np.ndarray,
    scale_mm_per_px: float | None,
    thresholds_mm: list[float] | None = None,
) -> SizeEstimate | None:
    """
    Compute comprehensive geometric, polar/equatorial, and volumetric mass metrics.

    Args:
        mask: Binary mask, uint8, 0/255.
        scale_mm_per_px: mm per pixel ratio from calibration.
        thresholds_mm: Optional list of grading thresholds to flag uncertainty.

    Returns:
        SizeEstimate with equatorial diameter, polar length, weight (g), and mandi grade.
    """
    if scale_mm_per_px is None:
        logger.debug("Cannot estimate size: no scale calibration available")
        return None

    if len(mask.shape) == 3:
        mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)

    mask_area_px = int(np.count_nonzero(mask))
    if mask_area_px == 0:
        logger.warning("Cannot estimate size: mask is empty")
        return None

    # 1. Equivalent circular diameter
    equiv_diameter_mm = 2.0 * math.sqrt(mask_area_px / math.pi) * scale_mm_per_px

    # 2. Contour extraction
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return SizeEstimate(
            equivalent_diameter_mm=round(equiv_diameter_mm, 2),
            mask_area_px=mask_area_px,
            scale_mm_per_px=scale_mm_per_px,
        )

    main_contour = max(contours, key=cv2.contourArea)

    # 3. Ellipse fit
    major_axis_mm: float | None = None
    minor_axis_mm: float | None = None
    if len(main_contour) >= 5:
        try:
            (_, _), (minor_px, major_px), _ = cv2.fitEllipse(main_contour)
            major_axis_mm = round(float(major_px) * scale_mm_per_px, 2)
            minor_axis_mm = round(float(minor_px) * scale_mm_per_px, 2)
        except Exception:
            pass

    # 4. Polar vs Equatorial Axis Morphometry
    apex_pt, base_pt, polar_px, eq_px = _detect_stem_and_root_poles(main_contour)
    polar_length_mm = round(polar_px * scale_mm_per_px, 2)
    equatorial_diameter_mm = round(eq_px * scale_mm_per_px, 2)

    # If equatorial diameter is too small due to mask contour noise, bound by equivalent diameter
    if equatorial_diameter_mm < equiv_diameter_mm * 0.75:
        equatorial_diameter_mm = round(equiv_diameter_mm, 2)

    # Compute equatorial caliper endpoints
    cx = (apex_pt[0] + base_pt[0]) // 2
    cy = (apex_pt[1] + base_pt[1]) // 2
    p_vec = np.array(base_pt) - np.array(apex_pt)
    p_norm = np.linalg.norm(p_vec)
    if p_norm > 0:
        perp = np.array([-p_vec[1], p_vec[0]], dtype=np.float32) / p_norm
        half_eq = eq_px / 2.0
        eq_pt1 = (int(cx + perp[0] * half_eq), int(cy + perp[1] * half_eq))
        eq_pt2 = (int(cx - perp[0] * half_eq), int(cy - perp[1] * half_eq))
    else:
        eq_pt1 = (cx - int(eq_px // 2), cy)
        eq_pt2 = (cx + int(eq_px // 2), cy)

    # 5. Shape Index & Classification
    shape_index = round(polar_length_mm / max(1.0, equatorial_diameter_mm), 2)
    if shape_index < 0.82:
        shape_class = "OBLATE"
    elif shape_index <= 1.15:
        shape_class = "GLOBULAR"
    else:
        shape_class = "TORPEDO"

    # 6. Volumetric Weight Estimation (g)
    # Prolate/oblate spheroid: V = (π / 6) * D_eq² * L_polar (in mm³)
    volume_mm3 = (math.pi / 6.0) * (equatorial_diameter_mm ** 2) * polar_length_mm
    estimated_weight_g = round(volume_mm3 * ONION_BULK_DENSITY_G_PER_MM3, 1)

    # 7. Mandi Size Grade (APMC Indian Standard)
    caliper_size = equatorial_diameter_mm or equiv_diameter_mm
    if caliper_size < 35.0:
        mandi_grade = "GOLI"
    elif caliper_size < 45.0:
        mandi_grade = "MADHYAM"
    elif caliper_size <= 65.0:
        mandi_grade = "SUPER"
    else:
        mandi_grade = "JUMBO"

    # 8. Uncertainty Flag
    uncertainty_flag = False
    if thresholds_mm:
        tolerance_mm = 3.0
        for threshold in thresholds_mm:
            if abs(equiv_diameter_mm - threshold) <= tolerance_mm:
                uncertainty_flag = True
                break

    return SizeEstimate(
        equivalent_diameter_mm=round(equiv_diameter_mm, 2),
        major_axis_mm=major_axis_mm,
        minor_axis_mm=minor_axis_mm,
        equatorial_diameter_mm=equatorial_diameter_mm,
        polar_length_mm=polar_length_mm,
        shape_index=shape_index,
        shape_class=shape_class,
        estimated_weight_grams=estimated_weight_g,
        mandi_size_grade=mandi_grade,
        polar_endpoints=(apex_pt, base_pt),
        equatorial_endpoints=(eq_pt1, eq_pt2),
        mask_area_px=mask_area_px,
        scale_mm_per_px=scale_mm_per_px,
        uncertainty_flag=uncertainty_flag,
    )
