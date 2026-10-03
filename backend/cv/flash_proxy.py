"""
Flash Proxy Index (FPI) Differential Reflectance Spectroscopy Proxy
====================================================================
Estimates cuticular wax degradation, surface water pooling, and early soft rot
by measuring differential optical reflectance between ambient and flash illuminations.

Theoretical grounding:
- Nicolaï et al. (2007): Non-destructive NIR spectroscopy and visible reflectance
- Taniwaki & Sakurai (2023): Vis-NIR optical reflectance characteristics of Allium cepa L.
- APMC Mandi Commercial Practice & BIS IS 17912:2022 (Supply Chain Guidelines)
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
import cv2
import numpy as np

FLASH_PROXY_LIMITATION_STATEMENT: str = (
    "This module analyzes differential optical reflectance under flash illumination as a "
    "non-destructive optical proxy for surface moisture and early cuticular breakdown. "
    "It does NOT replace laboratory NIR/SWIR spectroscopy or destructive cut assays ([Nicolaï-2007])."
)


@dataclass
class FpiAnalysisResult:
    """Quantitative differential reflectance appraisal for an individual bulb crop."""
    surface_state: str  # 'NORMAL' | 'SUSPECT' | 'INVALID'
    mean_fpi: float  # [0.0, 1.0]
    spatial_heterogeneity: float  # Standard deviation of FPI across mask
    lesion_area_ratio: float  # Fraction of bulb area exhibiting localized hyper-reflectance
    confidence: float  # [0.0, 1.0]
    notes: str


def compute_flash_proxy_map(ambient_bgr: np.ndarray, flash_bgr: np.ndarray) -> np.ndarray:
    """
    Compute 2D normalized differential reflectance map between ambient and flash frames.

    Args:
        ambient_bgr: BGR uint8 image under standard ambient light.
        flash_bgr: BGR uint8 image with active flash/strobe.

    Returns:
        float32 2D array normalized to [0.0, 1.0].
    """
    if ambient_bgr is None or flash_bgr is None:
        raise ValueError("Both ambient and flash images must be non-None valid numpy arrays.")

    # Align spatial dimensions if needed
    h_a, w_a = ambient_bgr.shape[:2]
    h_f, w_f = flash_bgr.shape[:2]
    if (h_a, w_a) != (h_f, w_f):
        flash_bgr = cv2.resize(flash_bgr, (w_a, h_a), interpolation=cv2.INTER_LINEAR)

    # Convert to float32
    amb_f = ambient_bgr.astype(np.float32) / 255.0
    fls_f = flash_bgr.astype(np.float32) / 255.0

    # Differential reflectance (flash response over ambient)
    diff = np.maximum(0.0, fls_f - amb_f)

    # Standard perceptual luminance weights (Rec. 601: B:0.114, G:0.587, R:0.299)
    fpi_map = diff[:, :, 0] * 0.114 + diff[:, :, 1] * 0.587 + diff[:, :, 2] * 0.299

    return np.clip(fpi_map, 0.0, 1.0).astype(np.float32)


def analyze_bulb_fpi(fpi_map: np.ndarray, mask: np.ndarray) -> FpiAnalysisResult:
    """
    Appraise surface condition of a segmented bulb instance using FPI.

    Args:
        fpi_map: 2D float32 array of differential reflectance values.
        mask: 2D uint8 binary mask of the bulb (255 inside bulb, 0 outside).

    Returns:
        FpiAnalysisResult with surface_state ('NORMAL' | 'SUSPECT' | 'INVALID').
    """
    valid_pixels = fpi_map[mask > 0]
    total_px = len(valid_pixels)

    if total_px < 25:
        return FpiAnalysisResult(
            surface_state="INVALID",
            mean_fpi=0.0,
            spatial_heterogeneity=0.0,
            lesion_area_ratio=0.0,
            confidence=0.0,
            notes="Insufficient segmented bulb pixels to compute reliable FPI surface proxy.",
        )

    mean_fpi = float(np.mean(valid_pixels))
    spatial_heterogeneity = float(np.std(valid_pixels))

    # Lesions or water-soaked soft rot patches typically have FPI > 0.45
    lesion_pixels = np.count_nonzero(valid_pixels > 0.45)
    lesion_area_ratio = float(lesion_pixels / total_px)

    # Classification thresholds
    if mean_fpi > 0.42 or lesion_area_ratio > 0.12:
        surface_state = "SUSPECT"
        confidence = 0.85
        notes = (
            f"Elevated differential reflectance (FPI={mean_fpi:.3f}, lesion={lesion_area_ratio:.1%}). "
            "Suspected cuticular degradation or early bacterial soft rot."
        )
    else:
        surface_state = "NORMAL"
        confidence = 0.88
        notes = f"Sound cuticular integrity (FPI={mean_fpi:.3f}, lesion={lesion_area_ratio:.1%})."

    return FpiAnalysisResult(
        surface_state=surface_state,
        mean_fpi=mean_fpi,
        spatial_heterogeneity=spatial_heterogeneity,
        lesion_area_ratio=lesion_area_ratio,
        confidence=confidence,
        notes=notes,
    )


def generate_fpi_heatmap(fpi_map: np.ndarray, bulb_mask: np.ndarray | None = None) -> np.ndarray:
    """
    Generate an RGB false-color JET heatmap from the FPI differential reflectance map.

    Args:
        fpi_map: 2D float32 array with values in [0.0, 1.0].
        bulb_mask: Optional binary mask. If provided, background pixels are zeroed.

    Returns:
        3-channel BGR uint8 heatmap image suitable for OpenCV display or export.
    """
    scaled = np.clip(fpi_map * 255.0, 0, 255).astype(np.uint8)
    heatmap_bgr = cv2.applyColorMap(scaled, cv2.COLORMAP_JET)

    if bulb_mask is not None:
        heatmap_bgr = cv2.bitwise_and(heatmap_bgr, heatmap_bgr, mask=bulb_mask)

    return heatmap_bgr


def encode_heatmap_to_base64(heatmap_bgr: np.ndarray) -> str:
    """Encode BGR heatmap image into a standard JPEG base64 string for API consumption."""
    success, buffer = cv2.imencode(".jpg", heatmap_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    if not success:
        raise ValueError("Failed to encode heatmap to JPEG.")
    return base64.b64encode(buffer).decode("ascii")
