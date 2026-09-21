"""
Visual Annotation & Mask Overlay Generator

Renders publication-grade visual overlays directly onto the inspection image:
  - Translucent alpha-blended instance masks color-coded by procurement grade
  - High-visibility contour outlines
  - Equatorial Caliper Line (Cyan, widest cross-section) & Polar Axis Line (Magenta, stem-root)
  - Crisp header pill tags: "#N: SUPER 54mm 82g | GRADE A"
  - Defect tags: "[ROTTEN]", "[DAMAGED]", "[SPROUTED]", "[DOUBLE]", "[MOLD]"
  - Calibration board indicator with calculated mm/px scale and 50mm physical scale bar
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
COLOR_REVIEW = (52, 152, 219)      # Sky Blue

# Morphometry line colors
COLOR_EQUATORIAL = (255, 220, 0)   # Cyan / Light Yellow (Caliper)
COLOR_POLAR = (255, 105, 180)      # Magenta / Pink (Stem-to-Root)


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

        overlay[mask > 0] = color

    # Alpha blend: 68% original + 32% colored mask
    cv2.addWeighted(overlay, 0.32, annotated, 0.68, 0, annotated)

    # 2. Draw axes, contours, and badges
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

        # Draw Polar Axis and Equatorial Caliper Lines if available
        if size and size.polar_endpoints:
            p1, p2 = size.polar_endpoints
            cv2.line(annotated, p1, p2, COLOR_POLAR, 2, cv2.LINE_AA)
            # End ticks
            cv2.circle(annotated, p1, 3, COLOR_POLAR, -1)
            cv2.circle(annotated, p2, 3, COLOR_POLAR, -1)

        if size and size.equatorial_endpoints:
            e1, e2 = size.equatorial_endpoints
            cv2.line(annotated, e1, e2, COLOR_EQUATORIAL, 2, cv2.LINE_AA)
            cv2.circle(annotated, e1, 3, COLOR_EQUATORIAL, -1)
            cv2.circle(annotated, e2, 3, COLOR_EQUATORIAL, -1)

        # Build label text
        size_num = size.equatorial_diameter_mm or size.equivalent_diameter_mm if size else None
        size_str = f"{size_num:.0f}mm" if size_num else "N/A"
        weight_str = f"{size.estimated_weight_grams:.0f}g" if (size and size.estimated_weight_grams) else ""
        mandi_str = f"{size.mandi_size_grade} " if (size and size.mandi_size_grade) else ""

        label_parts = [f"#{idx + 1}: {mandi_str}{size_str}"]
        if weight_str:
            label_parts.append(weight_str)
        label_parts.append(f"| {grade_str}")
        label = " ".join(label_parts)

        # If rejected, append primary reason
        if grading.rejection_reasons:
            label += f" [{grading.rejection_reasons[0]}]"

        # Anchor position for text label
        tx = max(10, det.bbox_x)
        ty = max(25, det.bbox_y - 6)

        # Background pill behind text for high legibility
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.44
        thickness = 1
        (text_w, text_h), baseline = cv2.getTextSize(label, font, font_scale, thickness)

        # Draw dark navy pill background
        cv2.rectangle(
            annotated,
            (tx - 3, ty - text_h - 4),
            (tx + text_w + 5, ty + baseline + 1),
            (15, 23, 42),
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
            (248, 250, 252),
            thickness,
            cv2.LINE_AA,
        )

    # 3. Bottom Calibration & Scale Telemetry Banner
    banner_text = (
        f"CEPA CALIBRATION: {scale_mm_per_px:.4f} mm/px"
        if scale_mm_per_px
        else "CEPA CALIBRATION: UNCALIBRATED"
    )
    cv2.rectangle(annotated, (10, h - 42), (430, h - 10), (15, 23, 42), -1)
    cv2.rectangle(annotated, (10, h - 42), (14, h - 10), (56, 189, 248), -1)
    cv2.putText(
        annotated,
        banner_text,
        (22, h - 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.50,
        (56, 189, 248),
        1,
        cv2.LINE_AA,
    )

    # Physical 50mm Scale Bar (Bottom Right)
    if scale_mm_per_px and scale_mm_per_px > 0:
        bar_len_px = int(50.0 / scale_mm_per_px)
        if 20 < bar_len_px < w // 2:
            bx2 = w - 25
            bx1 = bx2 - bar_len_px
            by = h - 24
            cv2.rectangle(annotated, (bx1 - 15, by - 22), (bx2 + 15, by + 12), (15, 23, 42), -1)
            cv2.line(annotated, (bx1, by), (bx2, by), (255, 255, 255), 2)
            cv2.line(annotated, (bx1, by - 6), (bx1, by + 6), (255, 255, 255), 2)
            cv2.line(annotated, (bx2, by - 6), (bx2, by + 6), (255, 255, 255), 2)
            cv2.putText(
                annotated,
                "50 mm Scale",
                (bx1 + max(0, (bar_len_px - 85) // 2), by - 8),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.40,
                (255, 255, 255),
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
