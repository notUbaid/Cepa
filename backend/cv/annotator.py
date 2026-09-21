"""
Visual Annotation & Mask Overlay Generator

Renders publication-grade visual overlays directly onto the inspection image:
  - Translucent alpha-blended instance masks color-coded by procurement grade
  - High-visibility contour outlines
  - Crisp header pill tags: "#N: 54.2mm | GRADE A"
  - Defect tags: "[ROTTEN]", "[DAMAGED]", "[SPROUTED]", "[DOUBLE]"
  - Calibration board bounding indicator with calculated mm/px scale
"""
from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

from config import settings

logger = logging.getLogger(__name__)

# Grade BGR colors
COLOR_GRADE_A = (46, 204, 113)     # Emerald Green
COLOR_URS = (243, 156, 18)         # Amber
COLOR_REJECTED = (231, 76, 60)     # Crimson Red
COLOR_REVIEW = (52, 152, 219)      # Blue


def render_annotated_inspection_image(
    rectified_image: np.ndarray,
    instances: list,  # list of InstancePipelineResult
    scale_mm_per_px: float | None,
    inspection_id: str,
    sample_id: str,
) -> str:
    """
    Generate and save an annotated visualization of the inspection spread.

    Returns:
        Relative path to the saved annotated image.
    """
    annotated = rectified_image.copy()
    overlay = rectified_image.copy()
    h, w = rectified_image.shape[:2]

    # 1. Blend segmentation masks with alpha transparency
    for item in instances:
        det = item.detection
        grading = item.grading_result
        mask = det.mask

        if grading.grade == "GRADE_A":
            color = COLOR_GRADE_A
        elif grading.grade == "URS":
            color = COLOR_URS
        elif grading.grade == "REJECTED":
            color = COLOR_REJECTED
        else:
            color = COLOR_REVIEW

        # Apply color to mask pixels
        overlay[mask > 0] = color

    # Alpha blend: 65% original + 35% colored mask
    cv2.addWeighted(overlay, 0.35, annotated, 0.65, 0, annotated)

    # 2. Draw sharp contour outlines and badges
    for item in instances:
        det = item.detection
        grading = item.grading_result
        size = item.size_estimate
        idx = det.instance_index
        mask = det.mask

        if grading.grade == "GRADE_A":
            color = COLOR_GRADE_A
            grade_str = "GRADE A"
        elif grading.grade == "URS":
            color = COLOR_URS
            grade_str = "URS"
        elif grading.grade == "REJECTED":
            color = COLOR_REJECTED
            grade_str = "REJECT"
        else:
            color = COLOR_REVIEW
            grade_str = "REVIEW"

        # Contour outline
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(annotated, contours, -1, color, 2)

        # Build label text
        size_str = f"{size.equivalent_diameter_mm:.1f}mm" if size else "N/A"
        label = f"#{idx + 1}: {size_str} | {grade_str}"

        # If rejected, append primary reason
        if grading.rejection_reasons:
            label += f" [{grading.rejection_reasons[0]}]"

        # Anchor position for text label
        tx = max(10, det.bbox_x)
        ty = max(25, det.bbox_y - 6)

        # Background pill behind text for high legibility
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.48
        thickness = 1
        (text_w, text_h), baseline = cv2.getTextSize(label, font, font_scale, thickness)

        # Draw dark drop shadow background
        cv2.rectangle(
            annotated,
            (tx - 3, ty - text_h - 4),
            (tx + text_w + 5, ty + baseline + 1),
            (15, 23, 42),  # Dark navy #0f172a
            -1,
        )
        # Draw colored left border tag
        cv2.rectangle(
            annotated,
            (tx - 3, ty - text_h - 4),
            (tx, ty + baseline + 1),
            color,
            -1,
        )
        # Text string
        cv2.putText(
            annotated,
            label,
            (tx + 2, ty - 1),
            font,
            font_scale,
            (248, 250, 252),  # White text
            thickness,
            cv2.LINE_AA,
        )

    # 3. Corner Calibration & System Banner
    banner_text = f"CEPA CALIBRATION: {scale_mm_per_px:.4f} mm/px" if scale_mm_per_px else "CEPA CALIBRATION: UNCALIBRATED"
    cv2.rectangle(annotated, (10, h - 40), (420, h - 10), (15, 23, 42), -1)
    cv2.rectangle(annotated, (10, h - 40), (14, h - 10), (56, 189, 248), -1)
    cv2.putText(
        annotated,
        banner_text,
        (22, h - 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.52,
        (56, 189, 248),
        1,
        cv2.LINE_AA,
    )

    # Save annotated image
    out_dir = settings.storage_dir / "images" / inspection_id
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{sample_id}_annotated.jpg"
    abs_path = out_dir / filename
    cv2.imwrite(str(abs_path), annotated, [cv2.IMWRITE_JPEG_QUALITY, 92])

    rel_path = f"images/{inspection_id}/{filename}"
    logger.info("Saved annotated visual overlay to: %s", rel_path)
    return rel_path
