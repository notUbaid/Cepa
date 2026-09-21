"""
Advanced Agricultural Morphology & Surface Defect Extraction

Implements fine-grained physical analysis of segmented onion bulbs:
1. Circularity & Sphericity Index:
   - Isoperimetric quotient: Q = 4 * pi * Area / Perimeter^2
   - Aspect ratio (minor_axis / major_axis)
2. Double / Split Bulb Detection:
   - Convexity defect analysis on contour. Fused/twin onions exhibit deep concavities.
   - Disqualifier for NAFED Grade A.
3. Color Space Surface Defect Analysis:
   - HSV & CIELAB analysis for:
     * Surface Staining % (Aspergillus niger, dirty scales)
     * Sunburn / Green Shoulder % (chlorophyll exposure in Kharif/Rabi)
     * Surface defect area fraction (% of total bulb area)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class BulbMorphology:
    """Detailed morphological measurements for an onion bulb."""
    circularity: float           # 0.0 to 1.0 (1.0 = perfect circle)
    aspect_ratio: float          # minor_axis / major_axis (1.0 = spherical)
    is_double_bulb: bool         # True if contour indicates twin/split bulb
    max_concavity_depth_px: float # Max depth of contour indentation
    surface_stain_pct: float     # Percentage of surface area with dark mold/stains (0-100)
    sunburn_pct: float           # Percentage of surface area with chlorophyll sunburn (0-100)
    defect_area_pct: float       # Total surface defect area percentage (0-100)


def analyze_bulb_morphology(
    crop_bgr: np.ndarray,
    mask: np.ndarray,
) -> BulbMorphology:
    """
    Analyze geometry, convexity, and color space of an onion bulb crop.

    Args:
        crop_bgr: BGR crop of the bulb (background is black).
        mask: Binary mask (0 or 255) for this instance, cropped to same dimensions.

    Returns:
        BulbMorphology with circularity, double bulb flag, stain %, sunburn %.
    """
    # Ensure mask is uint8 single channel
    if len(mask.shape) == 3:
        mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
    mask_binary = (mask > 127).astype(np.uint8) * 255

    area_px = int(np.count_nonzero(mask_binary))
    if area_px == 0:
        return BulbMorphology(
            circularity=1.0,
            aspect_ratio=1.0,
            is_double_bulb=False,
            max_concavity_depth_px=0.0,
            surface_stain_pct=0.0,
            sunburn_pct=0.0,
            defect_area_pct=0.0,
        )

    # ── 1. Circularity & Contour Analysis ─────────────────────────────────────
    contours, _ = cv2.findContours(mask_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return BulbMorphology(
            circularity=1.0,
            aspect_ratio=1.0,
            is_double_bulb=False,
            max_concavity_depth_px=0.0,
            surface_stain_pct=0.0,
            sunburn_pct=0.0,
            defect_area_pct=0.0,
        )

    main_contour = max(contours, key=cv2.contourArea)
    perimeter = cv2.arcLength(main_contour, True)

    circularity = 1.0
    if perimeter > 0:
        # Isoperimetric quotient: 4 * pi * Area / Perimeter^2
        circularity = float(min(1.0, (4.0 * np.pi * area_px) / (perimeter * perimeter)))

    # Aspect ratio from fitted ellipse or minAreaRect
    aspect_ratio = 1.0
    if len(main_contour) >= 5:
        try:
            (_, _), (axis1, axis2), _ = cv2.fitEllipse(main_contour)
            minor_ax = min(axis1, axis2)
            major_ax = max(axis1, axis2)
            if major_ax > 0:
                aspect_ratio = float(min(1.0, minor_ax / major_ax))
        except Exception:
            pass

    # ── 2. Double / Split Bulb Detection via Convexity Defects ────────────────
    is_double = False
    max_depth = 0.0

    hull_indices = cv2.convexHull(main_contour, returnPoints=False)
    if hull_indices is not None and len(hull_indices) > 3:
        try:
            defects = cv2.convexityDefects(main_contour, hull_indices)
            if defects is not None:
                # defects array: [start_idx, end_idx, farthest_idx, distance_fixed_point]
                # distance is fixed point with 8 fractional bits (divide by 256.0 for pixels)
                depths = defects[:, 0, 3] / 256.0
                max_depth = float(np.max(depths))

                # If the deepest concavity indentation is > 18% of the equivalent diameter,
                # the bulb is fused/split (double bulb)
                equiv_diam_px = 2.0 * np.sqrt(area_px / np.pi)
                if equiv_diam_px > 0 and (max_depth / equiv_diam_px) > 0.18:
                    is_double = True
                    logger.debug(
                        "Double bulb detected: concavity depth %.1fpx / equiv diam %.1fpx = %.2f",
                        max_depth, equiv_diam_px, max_depth / equiv_diam_px
                    )
        except Exception:
            pass

    # ── 3. Color Space Surface Analysis (Stain & Sunburn) ──────────────────────
    # Convert crop from BGR to HSV and LAB
    crop_hsv = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2HSV)
    crop_lab = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2LAB)

    bulb_mask_bool = mask_binary > 0

    # Staining detection (fungal rot / Aspergillus niger / deep dark lesions)
    # Characterized by very low lightness L in LAB, or low V and low S in HSV
    l_channel = crop_lab[:, :, 0]
    stain_mask = (l_channel < 50) & bulb_mask_bool
    stain_pixels = int(np.count_nonzero(stain_mask))
    stain_pct = float(round((stain_pixels / area_px) * 100.0, 1))

    # Sunburn detection (chlorophyll green shoulder)
    # In HSV: Green hue H is roughly [35, 85], with moderate-to-high saturation
    h_channel = crop_hsv[:, :, 0]
    s_channel = crop_hsv[:, :, 1]
    sunburn_mask = (h_channel >= 35) & (h_channel <= 85) & (s_channel > 60) & bulb_mask_bool
    sunburn_pixels = int(np.count_nonzero(sunburn_mask))
    sunburn_pct = float(round((sunburn_pixels / area_px) * 100.0, 1))

    # Total surface defect area (union of stain, sunburn, and severe discoloration)
    defect_mask = stain_mask | sunburn_mask
    defect_pixels = int(np.count_nonzero(defect_mask))
    defect_area_pct = float(round((defect_pixels / area_px) * 100.0, 1))

    return BulbMorphology(
        circularity=round(circularity, 3),
        aspect_ratio=round(aspect_ratio, 3),
        is_double_bulb=is_double,
        max_concavity_depth_px=round(max_depth, 1),
        surface_stain_pct=stain_pct,
        sunburn_pct=sunburn_pct,
        defect_area_pct=defect_area_pct,
    )
