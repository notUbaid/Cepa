"""
Stage 2: ChArUco Marker Detection

Detects the printed ChArUco calibration board in the camera image.
The ChArUco board serves as the reference object for:
  - Scale calibration (mm/px ratio)
  - Perspective correction (homography)

ChArUco is preferred over plain ArUco because:
  - Sub-pixel accuracy via saddle-point corner detection
  - Tolerates partial occlusion (individual corner IDs remain valid)
  - Better robustness to illumination variation

Physical board: 7x5 squares, 40mm square size, 20mm marker size, DICT_4X4_250
Print on A4 rigid cardboard. Measure actual squares with calipers and update
charuco_square_length_mm in .env if your print differs from 40.0mm.

Required package: opencv-contrib-python (NOT bare opencv-python)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

import cv2
import numpy as np

from config import settings

logger = logging.getLogger(__name__)

# ── Failure codes ─────────────────────────────────────────────────────────────
FAIL_MARKER_NOT_DETECTED = "marker_not_detected"
FAIL_MARKER_PARTIALLY_OCCLUDED = "marker_partially_occluded"
FAIL_MARKER_LOW_CONFIDENCE = "marker_low_confidence"

MARKER_FAILURE_MESSAGES: dict[str, str] = {
    FAIL_MARKER_NOT_DETECTED: (
        "Calibration board not detected. Place the printed ChArUco card "
        "fully inside the frame alongside the onions and recapture."
    ),
    FAIL_MARKER_PARTIALLY_OCCLUDED: (
        "Calibration board is partially hidden. Ensure the entire board "
        "is visible and not covered by onions."
    ),
    FAIL_MARKER_LOW_CONFIDENCE: (
        "Calibration board detected with low confidence. "
        "Ensure the board is flat, well-lit, and in focus."
    ),
}

# Minimum number of ChArUco corners required for reliable homography
_MIN_CORNERS_FOR_HOMOGRAPHY = 6


@dataclass
class MarkerDetectionResult:
    """Result of ChArUco board detection."""
    detected: bool
    failure_code: str | None = None
    failure_message: str | None = None

    # Detected corner coordinates in pixel space
    charuco_corners: np.ndarray | None = None  # shape (N, 1, 2) float32
    charuco_ids: np.ndarray | None = None       # shape (N, 1) int32

    # Number of valid corners found
    corner_count: int = 0


def detect_marker(image: np.ndarray) -> MarkerDetectionResult:
    """
    Detect ChArUco calibration board in the given BGR image.

    Args:
        image: BGR uint8 numpy array.

    Returns:
        MarkerDetectionResult. Check .detected before proceeding to calibration.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Build the ChArUco board definition matching the printed card
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_250)
    board = cv2.aruco.CharucoBoard(
        size=(settings.charuco_board_squares_x, settings.charuco_board_squares_y),
        squareLength=settings.charuco_square_length_mm / 1000.0,  # convert to metres for OpenCV
        markerLength=settings.charuco_marker_length_mm / 1000.0,
        dictionary=aruco_dict,
    )
    detector = cv2.aruco.CharucoDetector(board)

    try:
        charuco_corners, charuco_ids, marker_corners, marker_ids = detector.detectBoard(gray)
    except Exception:
        logger.exception("ChArUco detection failed unexpectedly")
        return MarkerDetectionResult(
            detected=False,
            failure_code=FAIL_MARKER_NOT_DETECTED,
            failure_message=MARKER_FAILURE_MESSAGES[FAIL_MARKER_NOT_DETECTED],
        )

    # No markers detected at all
    if charuco_ids is None or len(charuco_ids) == 0:
        logger.debug("Marker detection: no ChArUco corners found")
        return MarkerDetectionResult(
            detected=False,
            failure_code=FAIL_MARKER_NOT_DETECTED,
            failure_message=MARKER_FAILURE_MESSAGES[FAIL_MARKER_NOT_DETECTED],
        )

    n_corners = len(charuco_ids)
    logger.debug("Marker detection: found %d ChArUco corners", n_corners)

    # Fewer corners than required for homography = partial occlusion
    if n_corners < _MIN_CORNERS_FOR_HOMOGRAPHY:
        return MarkerDetectionResult(
            detected=False,
            failure_code=FAIL_MARKER_PARTIALLY_OCCLUDED,
            failure_message=MARKER_FAILURE_MESSAGES[FAIL_MARKER_PARTIALLY_OCCLUDED],
            charuco_corners=charuco_corners,
            charuco_ids=charuco_ids,
            corner_count=n_corners,
        )

    return MarkerDetectionResult(
        detected=True,
        charuco_corners=charuco_corners,
        charuco_ids=charuco_ids,
        corner_count=n_corners,
    )
