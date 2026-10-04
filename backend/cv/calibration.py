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
                     the original image (uncorrected), and scale_mm_per_px is
                     calibrated via autonomous packhouse overhead heuristic.
    scale_mm_per_px: mm per pixel in the rectified image.
    perspective_valid: True if homography was computed and applied successfully.
    is_estimated: True if scale was derived via autonomous packhouse overhead heuristic.
    calibration_method: "CHARUCO_BOARD" or "AUTONOMOUS_OVERHEAD_HEURISTIC"
    uncertainty_mm: estimated error margin for diameter measurements.
                   ChArUco board path: ~2.0mm (board-plane parallax at 65cm height
                   introduces ~1.5-2.5mm error for bulbs sitting 20-40mm above the board).
                   Heuristic path: ~5.0mm (scale from FOV prior only, no perspective correction).
    failure_code: set if perspective_valid is False.
    failure_message: human readable explanation.
    measured_square_px: measured square size in rectified image pixels
    """
    rectified_image: np.ndarray
    scale_mm_per_px: float | None
    perspective_valid: bool
    is_estimated: bool = False
    calibration_method: str = "CHARUCO_BOARD"
    uncertainty_mm: float = 2.0  # see docstring above; ChArUco path default
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

    If ChArUco is detected, computes exact homography and sub-millimeter scale.
    If ChArUco is not detected (or fails), activates the Autonomous Packhouse
    Overhead Benchmark Model (65cm bench height, 700mm FOV prior) so downstream
    stages, grading, and Mandi settlement compute realistic physical metrics.
    """
    h_img, w_img = image.shape[:2]
    # Autonomous Produce Benchmark Model:
    # Standard APMC mobile handheld capture distance is ~25-30cm (+-5cm) over a plate/tray.
    # Standard smartphone primary lens (26mm equiv, ~62 deg horizontal FOV)
    # covers approximately 260mm horizontal width at this close-up distance.
    estimated_scale = float(np.clip(
        260.0 / max(1.0, float(w_img)),
        settings.scale_min_mm_per_px,
        settings.scale_max_mm_per_px,
    ))

    if not marker_result.detected:
        logger.info(
            "ChArUco card not detected. Engaging Autonomous Benchmark Caliper: %.4f mm/px for %dx%d image.",
            estimated_scale, w_img, h_img,
        )
        return CalibrationResult(
            rectified_image=image,
            scale_mm_per_px=estimated_scale,
            perspective_valid=False,
            is_estimated=True,
            calibration_method="AUTONOMOUS_OVERHEAD_HEURISTIC",
            uncertainty_mm=5.0,
            failure_code=marker_result.failure_code,
            failure_message=marker_result.failure_message,
        )

    corners = marker_result.charuco_corners  # (N, 1, 2) float32 in image space
    ids = marker_result.charuco_ids          # (N, 1) int32

    if corners is None or ids is None or len(corners) < 4:
        logger.warning("Fewer than 4 corners for homography. Falling back to autonomous benchmark scale.")
        return CalibrationResult(
            rectified_image=image,
            scale_mm_per_px=estimated_scale,
            perspective_valid=False,
            is_estimated=True,
            calibration_method="AUTONOMOUS_OVERHEAD_HEURISTIC",
            uncertainty_mm=5.0,
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
        logger.warning("findHomography returned None — too few inliers. Falling back to autonomous benchmark scale.")
        return CalibrationResult(
            rectified_image=image,
            scale_mm_per_px=estimated_scale,
            perspective_valid=False,
            is_estimated=True,
            calibration_method="AUTONOMOUS_OVERHEAD_HEURISTIC",
            uncertainty_mm=5.0,
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

    extent_w_mm = float(x_max - x_min)
    extent_h_mm = float(y_max - y_min)

    # Output dimensions: maintain sensor optical density rather than downsampling to 1 px/mm.
    # Standard phone captures (1080p-4K) have 2-8 px/mm.
    target_scale = 1.0
    if extent_w_mm > 0:
        target_scale = float(w_img) / extent_w_mm
        target_scale = max(1.0, min(8.0, target_scale))

    out_w = min(8000, max(100, int(np.round(extent_w_mm * target_scale))))
    out_h = min(8000, max(100, int(np.round(extent_h_mm * target_scale))))

    actual_scale_x = out_w / max(extent_w_mm, 1e-6)
    actual_scale_y = out_h / max(extent_h_mm, 1e-6)

    # Shift and scale homography so rectified image aligns to [0, out_w] x [0, out_h]
    T = np.array([
        [actual_scale_x, 0.0, -x_min * actual_scale_x],
        [0.0, actual_scale_y, -y_min * actual_scale_y],
        [0.0, 0.0, 1.0],
    ], dtype=np.float64)
    H_shifted = T @ H

    rectified = cv2.warpPerspective(image, H_shifted, (out_w, out_h))

    # In rectified space, px_per_mm is the true optical density:
    if out_w > 0 and extent_w_mm > 0:
        px_per_mm = actual_scale_x
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
            rectified_image=image,  # use original
            scale_mm_per_px=estimated_scale,
            perspective_valid=False,
            is_estimated=True,
            calibration_method="AUTONOMOUS_OVERHEAD_HEURISTIC",
            uncertainty_mm=5.0,
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

    # Dynamic Parallax & Standoff Uncertainty (Resolution-Invariant):
    # An onion's equator sits ~20-35mm above the planar board surface.
    # We estimate camera distance from the physical board's apparent span across the frame:
    board_min = img_pts.min(axis=0)
    board_max = img_pts.max(axis=0)
    board_span_px = max(float(board_max[0] - board_min[0]), float(board_max[1] - board_min[1]))
    frame_dim = max(float(w_img), float(h_img))
    board_frame_fraction = board_span_px / max(1.0, frame_dim)

    # Resolution-invariant standoff brackets:
    # 1. Close handheld distance (f > 0.50, camera ~25-35cm over tray): parallax ~10% (Δ ~ 3.5mm)
    # 2. Standard calibrated bench / tripod standoff (0.25 <= f <= 0.50, camera ~45-70cm): parallax ~4% (Δ ~ 2.0mm)
    # 3. Packhouse overhead mount (f < 0.25, camera > 75cm): parallax ~2% (Δ ~ 1.5mm)
    if board_frame_fraction > 0.50:
        parallax_uncertainty_mm = 3.5
    elif board_frame_fraction >= 0.25:
        parallax_uncertainty_mm = 2.0
    else:
        parallax_uncertainty_mm = 1.5

    return CalibrationResult(
        rectified_image=rectified,
        scale_mm_per_px=mm_per_px,
        perspective_valid=True,
        is_estimated=False,
        calibration_method="CHARUCO_BOARD",
        uncertainty_mm=parallax_uncertainty_mm,
        measured_square_px=px_per_mm * (settings.charuco_square_length_mm),
    )


def generate_charuco_board(width_px: int = 1400, height_px: int = 1000) -> np.ndarray:
    """
    Generate high-resolution printable ChArUco 7x5 metric calibration board image.
    Uses DICT_4X4_250 matching system configuration.
    """
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_250)
    board = cv2.aruco.CharucoBoard(
        size=(settings.charuco_board_squares_x, settings.charuco_board_squares_y),
        squareLength=settings.charuco_square_length_mm / 1000.0,
        markerLength=settings.charuco_marker_length_mm / 1000.0,
        dictionary=aruco_dict,
    )
    return board.generateImage((width_px, height_px), marginSize=20, borderBits=1)

