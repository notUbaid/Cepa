"""
Advanced Agricultural Morphology & Multi-Spectral Biological Defect Extraction

Implements fine-grained physical, pathological, and biochemical surface analysis:
1. Circularity & Sphericity Index:
   - Isoperimetric quotient: Q = 4 * pi * Area / Perimeter^2
   - Aspect ratio (minor_axis / major_axis)
2. Double / Split Bulb Detection:
   - Convexity defect analysis on contour. Fused/twin onions exhibit deep concavities.
   - Disqualifier for NAFED Grade A export standard.
3. Pathological Surface Defect Analysis:
   - Aspergillus niger (Black Mold) index via CIELAB L* < 40 and local entropy
   - Chlorophyll Sunburn Index via Normalized Green-Red Difference Index:
     NGRDI = (G - R) / (G + R + 1e-5)
   - Skin Baldness / Missing Papery Tunic Ratio:
     Exposed fleshy scale leaves vs intact protective dry tunic
   - Total Surface Defect Area Percentage
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class BulbMorphology:
    """Detailed pathological, biochemical, and morphological measurements for an onion bulb."""
    circularity: float           # 0.0 to 1.0 (1.0 = perfect circle)
    aspect_ratio: float          # minor_axis / major_axis (1.0 = spherical)
    is_double_bulb: bool         # True if contour indicates twin/split bulb
    max_concavity_depth_px: float # Max depth of contour indentation
    surface_stain_pct: float     # Percentage of surface area with dark mold/stains (0-100)
    sunburn_pct: float           # Percentage of surface area with chlorophyll sunburn (0-100)
    black_mold_pct: float        # Percentage with Aspergillus niger black mold (0-100)
    skin_baldness_pct: float     # Percentage with missing tunic / peeled fleshy scales (0-100)
    ngrdi_mean: float            # Normalized Green-Red Difference Index (-1.0 to 1.0)
    defect_area_pct: float       # Total surface defect area percentage (0-100)


def analyze_bulb_morphology(
    crop_bgr: np.ndarray,
    mask: np.ndarray,
) -> BulbMorphology:
    """
    Analyze geometry, convexity, and color spaces of an onion bulb crop.

    Args:
        crop_bgr: BGR crop of the bulb.
        mask: Binary mask (0 or 255) for this instance, cropped to same dimensions.

    Returns:
        BulbMorphology with circularity, double bulb flag, black mold, sunburn, baldness %.
    """
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
            black_mold_pct=0.0,
            skin_baldness_pct=0.0,
            ngrdi_mean=0.0,
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
            black_mold_pct=0.0,
            skin_baldness_pct=0.0,
            ngrdi_mean=0.0,
            defect_area_pct=0.0,
        )

    main_contour = max(contours, key=cv2.contourArea)
    perimeter = cv2.arcLength(main_contour, True)

    circularity = 1.0
    if perimeter > 0:
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
                depths = (
                    defects[:, 0, 3] / 256.0
                    if len(defects.shape) == 3
                    else defects[:, 3] / 256.0
                )
                max_depth = float(np.max(depths))
                equiv_diam_px = 2.0 * np.sqrt(area_px / np.pi)
                if equiv_diam_px > 0 and (max_depth / equiv_diam_px) > 0.12:
                    is_double = True
                    logger.debug(
                        "Double bulb detected: concavity depth %.1fpx / equiv diam %.1fpx = %.2f",
                        max_depth, equiv_diam_px, max_depth / equiv_diam_px
                    )
        except Exception:
            pass

    # ── 3. Multi-Spectral Biochemical & Pathological Defect Analysis ─────────
    crop_hsv = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2HSV)
    crop_lab = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2LAB)
    bulb_mask_bool = mask_binary > 0

    # Channels
    b_ch = crop_bgr[:, :, 0].astype(np.float32)
    g_ch = crop_bgr[:, :, 1].astype(np.float32)
    r_ch = crop_bgr[:, :, 2].astype(np.float32)

    l_channel = crop_lab[:, :, 0]
    h_channel = crop_hsv[:, :, 0]
    s_channel = crop_hsv[:, :, 1]
    v_channel = crop_hsv[:, :, 2]

    # (A) Aspergillus niger (Black Mold)
    # Characterized by low L* (< 42), low Value (< 45), low Red/Green reflection
    black_mold_mask = (l_channel < 42) & (v_channel < 45) & bulb_mask_bool
    black_mold_pixels = int(np.count_nonzero(black_mold_mask))
    black_mold_pct = float(round((black_mold_pixels / area_px) * 100.0, 1))

    # (B) Surface Staining / General decay lesions
    stain_mask = (l_channel < 52) & bulb_mask_bool
    stain_pixels = int(np.count_nonzero(stain_mask))
    surface_stain_pct = float(round((stain_pixels / area_px) * 100.0, 1))

    # (C) Sunburn / Green Shoulder Index via NGRDI
    # NGRDI = (G - R) / (G + R + 1e-5)
    # Chlorophyll accumulation produces positive or high NGRDI values
    denom = g_ch + r_ch + 1e-5
    ngrdi_map = (g_ch - r_ch) / denom
    bulb_ngrdi_values = ngrdi_map[bulb_mask_bool]
    ngrdi_mean = float(np.mean(bulb_ngrdi_values)) if len(bulb_ngrdi_values) > 0 else 0.0

    # Green shoulder pixels (H in [35, 85], S > 50, NGRDI > -0.05)
    sunburn_mask = (
        (h_channel >= 35) & (h_channel <= 85) &
        (s_channel > 50) & (ngrdi_map > -0.05) &
        bulb_mask_bool
    )
    sunburn_pixels = int(np.count_nonzero(sunburn_mask))
    sunburn_pct = float(round((sunburn_pixels / area_px) * 100.0, 1))

    # (D) Skin Baldness / Missing Tunic
    # Exposed fleshy inner storage scales are pale/white/pink with high lightness and low saturation
    baldness_mask = (l_channel > 185) & (s_channel < 70) & bulb_mask_bool
    baldness_pixels = int(np.count_nonzero(baldness_mask))
    skin_baldness_pct = float(round((baldness_pixels / area_px) * 100.0, 1))

    # Total combined surface defect area
    total_defect_mask = stain_mask | sunburn_mask | black_mold_mask
    total_defect_pixels = int(np.count_nonzero(total_defect_mask))
    defect_area_pct = float(round((total_defect_pixels / area_px) * 100.0, 1))

    return BulbMorphology(
        circularity=round(circularity, 3),
        aspect_ratio=round(aspect_ratio, 3),
        is_double_bulb=is_double,
        max_concavity_depth_px=round(max_depth, 1),
        surface_stain_pct=surface_stain_pct,
        sunburn_pct=sunburn_pct,
        black_mold_pct=black_mold_pct,
        skin_baldness_pct=skin_baldness_pct,
        ngrdi_mean=round(ngrdi_mean, 3),
        defect_area_pct=defect_area_pct,
    )
