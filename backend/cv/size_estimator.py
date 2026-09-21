"""
Stage 7: Geometric Size Estimation

Estimates the physical size of each onion bulb from its segmentation mask
and the calibrated mm/pixel ratio.

Primary metric: equivalent_diameter_mm
  = 2 × √(mask_area_px / π) × mm_per_px

This is the diameter of a circle with the same area as the mask.
Chosen because:
  - More stable than major-axis length for near-circular shapes
  - Less sensitive to mask orientation artifacts
  - Works even when mask is not perfectly elliptical
  - Directly comparable to the "equatorial diameter" used in NAFED specs

Supplementary metrics (from ellipse fitting):
  - major_axis_mm: longest axis (≈ max cross-section)
  - minor_axis_mm: shortest axis

MANDATORY LIMITATION (stored in every Measurement record and shown in reports):
  The equivalent_diameter_mm is a projected measurement from a top-view image.
  It is NOT equivalent to a laboratory caliper measurement across the equator.
  An onion resting on a table may present a different apparent size depending
  on orientation. Measurement error is typically ±5-15mm compared to caliper.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass

import cv2
import numpy as np

from models.measurement import PROJECTION_NOTE

logger = logging.getLogger(__name__)


@dataclass
class SizeEstimate:
    """Geometric size measurements for one onion bulb."""
    equivalent_diameter_mm: float
    major_axis_mm: float | None       # None if ellipse fit failed
    minor_axis_mm: float | None
    mask_area_px: int
    scale_mm_per_px: float
    projection_note: str = PROJECTION_NOTE
    uncertainty_flag: bool = False    # Set by grading engine, not here


def estimate_size(
    mask: np.ndarray,
    scale_mm_per_px: float | None,
    thresholds_mm: list[float] | None = None,
) -> SizeEstimate | None:
    """
    Compute size metrics for an onion mask.

    Args:
        mask: Binary mask, uint8, 0/255. Same size as rectified image.
        scale_mm_per_px: mm per pixel ratio from calibration.
                         If None, size cannot be estimated (returns None).
        thresholds_mm: List of grading threshold values in mm
                       (e.g. [35.0, 45.0, 65.0, 70.0]).
                       Used to set uncertainty_flag if size is near a threshold.

    Returns:
        SizeEstimate or None if scale is not available or mask is empty.
    """
    if scale_mm_per_px is None:
        logger.debug("Cannot estimate size: no scale calibration available")
        return None

    mask_area_px = int(np.count_nonzero(mask))
    if mask_area_px == 0:
        logger.warning("Cannot estimate size: mask is empty")
        return None

    # ── Primary metric: equivalent circle diameter ─────────────────────────────
    equiv_diameter_mm = 2.0 * math.sqrt(mask_area_px / math.pi) * scale_mm_per_px

    # ── Supplementary: ellipse fit ─────────────────────────────────────────────
    major_axis_mm: float | None = None
    minor_axis_mm: float | None = None

    try:
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            # Use the largest contour (main onion body)
            largest = max(contours, key=cv2.contourArea)
            if len(largest) >= 5:  # OpenCV requires ≥5 points for fitEllipse
                (_, _), (minor_px, major_px), _ = cv2.fitEllipse(largest)
                major_axis_mm = float(major_px) * scale_mm_per_px
                minor_axis_mm = float(minor_px) * scale_mm_per_px
    except Exception:
        logger.debug("Ellipse fitting failed for mask — using equiv diameter only")

    # ── Uncertainty flag: near any grading threshold ───────────────────────────
    uncertainty_flag = False
    if thresholds_mm:
        tolerance_mm = 3.0  # within 3mm of any threshold → uncertain
        for threshold in thresholds_mm:
            if abs(equiv_diameter_mm - threshold) <= tolerance_mm:
                uncertainty_flag = True
                logger.debug(
                    "Size %.1fmm within %.1fmm of threshold %.1fmm → NEEDS_REVIEW",
                    equiv_diameter_mm, tolerance_mm, threshold,
                )
                break

    return SizeEstimate(
        equivalent_diameter_mm=round(equiv_diameter_mm, 2),
        major_axis_mm=round(major_axis_mm, 2) if major_axis_mm is not None else None,
        minor_axis_mm=round(minor_axis_mm, 2) if minor_axis_mm is not None else None,
        mask_area_px=mask_area_px,
        scale_mm_per_px=scale_mm_per_px,
        uncertainty_flag=uncertainty_flag,
    )
