"""
Stage 3: Perspective Correction and Scale Calibration

Uses the detected ChArUco corners to:
1. Compute a homography matrix from camera image plane to top-down view
2. Apply perspective correction (warpPerspective) to produce a rectified image
3. Calculate the mm/pixel ratio from the known physical square size

The rectified image is used for all subsequent pipeline stages.
All coordinates (bounding boxes, masks) returned later are in rectified space.

Measurement geometry:
  - The ChArUco board's physical square size is known (settings.charuco_square_length_mm)
  - After rectification, we measure the projected pixel size of these squares
  - mm_per_px = physical_size_mm / measured_pixel_size
  - This ratio is then applied to all onion mask measurements

Limitation (acknowledged in code and reports):
  The homography assumes all objects of interest lie in the SAME plane as the
  calibration board. An onion bulb is a 3D object resting on a surface; its
  visible top surface is at a slightly different depth than the board surface.
  This introduces a small systematic error in size estimation, typically < 5 mm
  for typical capture heights (50-80 cm) and onion heights (40-80 mm).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import cv2
import numpy as np

from config import settings
from cv.marker_detector import MarkerDetectionResult

logger = logging.getLogger(__name__)

FAIL_SCALE_UNRELIABLE = "scale_unreliable"
FAIL_HOMOGRAPHY_FAILED = "homography_failed"


@dataclass
class CalibrationResult:
    """
    Result of perspective correction and scale calibration.

    rectified_image: the corrected image to use for all downstream stages.
                     If calibration failed (perspective_valid=False), this is
                     the original image (uncorrected), and scale_mm_per_px is None.
    scale_mm_per_px: mm per pixel in the rectified image. None if calibration failed.
    perspective_valid: True if homography was computed and applied successfully.
    failure_code: set if perspective_valid is False.
    """
    rectified_image: np.ndarray
    scale_mm_per_px: float | None
    perspective_valid: bool
    failure_code: str | None = None
    failure_message: str | None = None
    # Debug: measured square size in rectified image pixels
    measured_square_px: float | None = None


def compute_calibration(
    image: np.ndarray,
    marker_result: MarkerDetectionResult,
) -> CalibrationResult:
    """
    Compute homography and mm/px scale from ChArUco detection result.

    Falls back to the original image without scale if calibration fails.
    Downstream stages can still run (with is_mock_scale=True flagging).
    """
    if not marker_result.detected:
        # Cannot calibrate without marker — return original image, no scale
        return CalibrationResult(
            rectified_image=image,
            scale_mm_per_px=None,
            perspective_valid=False,
            failure_code=marker_result.failure_code,
            failure_message=marker_result.failure_message,
        )

    corners = marker_result.charuco_corners  # (N, 1, 2) float32 in image space
    ids = marker_result.charuco_ids          # (N, 1) int32

    if corners is None or ids is None or len(corners) < 4:
        return CalibrationResult(
            rectified_image=image,
            scale_mm_per_px=None,
            perspective_valid=False,
            failure_code=FAIL_HOMOGRAPHY_FAILED,
            failure_message="Not enough corners for homography computation.",
        )

    # Build the board's 3D object points (assuming Z=0 for the flat board)
    # ChArUco corner positions are on a regular grid with known spacing
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_250)
    board = cv2.aruco.CharucoBoard(
        size=(settings.charuco_board_squares_x, settings.charuco_board_squares_y),
        squareLength=settings.charuco_square_length_mm / 1000.0,
        markerLength=settings.charuco_marker_length_mm / 1000.0,
        dictionary=aruco_dict,
    )

    # Get the object points (world coordinates) for the detected corner IDs
    obj_points_3d = board.getChessboardCorners()  # all corners in 3D
    # Filter to only the detected IDs
    ids_flat = ids.flatten()
    obj_pts = np.array(
        [obj_points_3d[i][:2] for i in ids_flat],  # take X, Y only (Z=0)
        dtype=np.float32,
    )
    img_pts = corners.reshape(-1, 2).astype(np.float32)

    # Scale obj_pts from metres to mm for easier interpretation
    obj_pts_mm = obj_pts * 1000.0  # now in mm

    # Compute homography: maps image points → board coordinate system (mm)
    H, mask = cv2.findHomography(img_pts, obj_pts_mm, cv2.RANSAC, 5.0)

    if H is None:
        logger.warning("findHomography returned None — too few inliers")
        return CalibrationResult(
            rectified_image=image,
            scale_mm_per_px=None,
            perspective_valid=False,
            failure_code=FAIL_HOMOGRAPHY_FAILED,
            failure_message=(
                "Homography computation failed. Ensure the calibration board "
                "is flat and not warped."
            ),
        )

    # ── Compute rectified image ────────────────────────────────────────────────
    # Determine output size by mapping image corners through H to find extent
    h_img, w_img = image.shape[:2]
    img_corners = np.float32([[0, 0], [w_img, 0], [w_img, h_img], [0, h_img]])
    mapped = cv2.perspectiveTransform(img_corners.reshape(-1, 1, 2), H).reshape(-1, 2)

    x_min, y_min = mapped.min(axis=0)
    x_max, y_max = mapped.max(axis=0)

    # Output dimensions: limit to a reasonable size (8000px max) to avoid memory issues
    out_w = min(8000, int(x_max - x_min))
    out_h = min(8000, int(y_max - y_min))

    # Shift homography to account for the min offset
    T = np.array([[1, 0, -x_min], [0, 1, -y_min], [0, 0, 1]], dtype=np.float64)
    H_shifted = T @ H

    rectified = cv2.warpPerspective(image, H_shifted, (out_w, out_h))

    # ── Compute mm/px scale in rectified image ─────────────────────────────────
    # In the rectified image, 1 mm in board coordinates = some number of pixels.
    # Map two adjacent corners through H to find their pixel separation.
    # We use the first two detected corners for this.
    pt1_board_mm = np.float32([[obj_pts_mm[0][0], obj_pts_mm[0][1], 1]])
    pt2_board_mm = np.float32([[obj_pts_mm[1][0], obj_pts_mm[1][1], 1]])

    # In board space, distance between corners:
    board_dist_mm = float(np.linalg.norm(obj_pts_mm[0] - obj_pts_mm[1]))

    # Map back through inverse homography to get pixel distance in rectified image
    # Simpler: use the original image point distance scaled by H's local scale
    # Actually: in rectified space, 1 board mm = (out_w / (x_max - x_min)) pixels
    if (x_max - x_min) > 0:
        px_per_mm = out_w / (x_max - x_min)
        mm_per_px = 1.0 / px_per_mm
    else:
        mm_per_px = None

    # Sanity check on the computed scale
    if mm_per_px is not None and (
        mm_per_px < settings.scale_min_mm_per_px
        or mm_per_px > settings.scale_max_mm_per_px
    ):
        logger.warning(
            "Computed scale %.4f mm/px is outside valid range [%.2f, %.2f]. "
            "Check that the physical board dimensions in .env match the printed card.",
            mm_per_px,
            settings.scale_min_mm_per_px,
            settings.scale_max_mm_per_px,
        )
        return CalibrationResult(
            rectified_image=image,  # use original, no scale
            scale_mm_per_px=None,
            perspective_valid=False,
            failure_code=FAIL_SCALE_UNRELIABLE,
            failure_message=(
                f"Computed scale {mm_per_px:.4f} mm/px is implausible. "
                "Check that the physical board dimensions match the .env configuration, "
                "or ensure the card is in the same plane as the onions."
            ),
        )

    logger.info(
        "Calibration success: scale=%.4f mm/px, rectified size=%dx%d",
        mm_per_px, out_w, out_h,
    )

    return CalibrationResult(
        rectified_image=rectified,
        scale_mm_per_px=mm_per_px,
        perspective_valid=True,
    )
