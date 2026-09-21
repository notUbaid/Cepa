"""
Stage 1: Image Quality Gate

Checks whether a captured image is suitable for reliable onion inspection.
Uses only deterministic classical CV — no ML model involved.

This gate is a FIRST-CLASS RELIABILITY MECHANISM.
If an image fails, the pipeline stops and returns an actionable error.
Low-quality input must NEVER silently produce a confident grade.

Checks performed:
  1. Resolution (minimum dimension)
  2. Blur (Laplacian variance)
  3. Darkness (mean luminance)
  4. Overexposure (mean luminance)
  5. Glare (fraction of saturated pixels)

All thresholds are configurable via settings.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

import cv2
import numpy as np

from config import settings

logger = logging.getLogger(__name__)

# ── Failure codes (machine-readable, also displayed to officer) ───────────────
FAIL_INSUFFICIENT_RESOLUTION = "insufficient_resolution"
FAIL_IMAGE_TOO_BLURRY = "image_too_blurry"
FAIL_TOO_DARK = "too_dark"
FAIL_TOO_BRIGHT = "too_bright"
FAIL_EXCESSIVE_GLARE = "excessive_glare"

# Human-readable messages for each failure code
FAILURE_MESSAGES: dict[str, str] = {
    FAIL_INSUFFICIENT_RESOLUTION: (
        "Image resolution is too low. Please use your device's highest camera "
        "resolution and capture from approximately 50-80 cm above the spread."
    ),
    FAIL_IMAGE_TOO_BLURRY: (
        "Image is too blurry. Hold the phone steady, ensure autofocus has locked, "
        "and retake the photo."
    ),
    FAIL_TOO_DARK: (
        "Image is too dark. Move to better lighting or use the flash, then recapture."
    ),
    FAIL_TOO_BRIGHT: (
        "Image is overexposed. Avoid direct sunlight on the onion spread "
        "or shade the area and recapture."
    ),
    FAIL_EXCESSIVE_GLARE: (
        "Excessive glare detected. Move the spread to reduce reflections, "
        "or capture at a slight angle to avoid direct light reflection."
    ),
}


@dataclass
class QualityGateResult:
    """
    Result of the image quality gate check.

    passed: True only when ALL checks pass.
    failures: List of failure codes (empty if passed).
    message: Human-readable summary for display to the officer.
    metrics: Diagnostic values for each check (useful for debugging).
    """
    passed: bool
    failures: list[str] = field(default_factory=list)
    message: str = ""
    metrics: dict[str, float] = field(default_factory=dict)

    @property
    def failure_messages(self) -> list[str]:
        return [FAILURE_MESSAGES.get(f, f) for f in self.failures]


def check_image_quality(image: np.ndarray) -> QualityGateResult:
    """
    Run all quality checks on the input BGR image.

    Args:
        image: BGR uint8 numpy array (as loaded by OpenCV).

    Returns:
        QualityGateResult — check passed field before proceeding.
    """
    failures: list[str] = []
    metrics: dict[str, float] = {}

    h, w = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # ── Check 1: Resolution ────────────────────────────────────────────────────
    min_dim = min(h, w)
    metrics["min_dimension_px"] = float(min_dim)
    if min_dim < settings.qg_min_resolution_px:
        failures.append(FAIL_INSUFFICIENT_RESOLUTION)
        logger.debug("Quality gate: resolution %dpx < threshold %dpx", min_dim, settings.qg_min_resolution_px)

    # ── Check 2: Blur (Laplacian variance) ────────────────────────────────────
    # High variance = sharp image; low variance = blurry.
    # We compute on the grayscale image.
    laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    metrics["laplacian_variance"] = laplacian_var
    if laplacian_var < settings.qg_blur_threshold:
        failures.append(FAIL_IMAGE_TOO_BLURRY)
        logger.debug("Quality gate: blur var %.2f < threshold %.2f", laplacian_var, settings.qg_blur_threshold)

    # ── Check 3: Darkness ─────────────────────────────────────────────────────
    mean_lum = float(np.mean(gray))
    metrics["mean_luminance"] = mean_lum
    if mean_lum < settings.qg_dark_threshold:
        failures.append(FAIL_TOO_DARK)
        logger.debug("Quality gate: luminance %.1f < threshold %d", mean_lum, settings.qg_dark_threshold)

    # ── Check 4: Overexposure ─────────────────────────────────────────────────
    if mean_lum > settings.qg_bright_threshold:
        failures.append(FAIL_TOO_BRIGHT)
        logger.debug("Quality gate: luminance %.1f > threshold %d", mean_lum, settings.qg_bright_threshold)

    # ── Check 5: Glare (saturated pixels) ────────────────────────────────────
    # A pixel is considered glare if ALL three channels are > 250.
    # This identifies specular reflections and blown-out regions.
    glare_mask = np.all(image > 250, axis=2)
    glare_fraction = float(np.mean(glare_mask))
    metrics["glare_fraction"] = glare_fraction
    if glare_fraction > settings.qg_glare_fraction:
        failures.append(FAIL_EXCESSIVE_GLARE)
        logger.debug(
            "Quality gate: glare fraction %.3f > threshold %.3f",
            glare_fraction, settings.qg_glare_fraction,
        )

    # ── Assemble result ────────────────────────────────────────────────────────
    passed = len(failures) == 0

    if passed:
        message = "Image quality acceptable. Proceeding with inspection."
    elif len(failures) == 1:
        message = FAILURE_MESSAGES.get(failures[0], failures[0])
    else:
        parts = [FAILURE_MESSAGES.get(f, f) for f in failures]
        message = "Multiple quality issues detected: " + " | ".join(parts)

    logger.info(
        "Quality gate: passed=%s failures=%s lum=%.1f blur=%.1f glare=%.3f",
        passed, failures, mean_lum, laplacian_var, glare_fraction,
    )

    return QualityGateResult(passed=passed, failures=failures, message=message, metrics=metrics)
