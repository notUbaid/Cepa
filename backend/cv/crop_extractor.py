"""
Stage 5: Per-Onion Crop Extraction

For each detected onion instance, extracts:
1. A binary segmentation mask (PNG) — white=onion, black=background
2. A masked crop image (JPEG) — the onion isolated from background, with padding

These artifacts are stored to disk and serve as the primary evidence trail.
Every result in the system can be traced back to the source crop image.

Storage paths are relative to settings.storage_dir, using:
  crops/{inspection_id}/{sample_id}/{idx:04d}.jpg
  masks/{inspection_id}/{sample_id}/{idx:04d}.png
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from config import settings

logger = logging.getLogger(__name__)

# Padding around the bounding box when extracting the crop (pixels)
_CROP_PADDING = 20


@dataclass
class ExtractedCrop:
    """Paths and metadata for one extracted onion crop."""
    instance_index: int
    mask_path: str        # relative to storage_dir
    crop_path: str        # relative to storage_dir
    mask_area_px: int


def extract_crops(
    rectified_image: np.ndarray,
    detections: list,            # List[OnionDetection]
    inspection_id: str,
    sample_id: str,
) -> list[ExtractedCrop]:
    """
    Extract and save crops and masks for all detected onion instances.

    Args:
        rectified_image: Perspective-corrected BGR image.
        detections: List of OnionDetection from segmentation provider.
        inspection_id: Used to construct the storage path.
        sample_id: Used to construct the storage path.

    Returns:
        List of ExtractedCrop, one per detection. Failed extractions are
        included with empty paths (will be flagged later).
    """
    h, w = rectified_image.shape[:2]
    results: list[ExtractedCrop] = []

    # Ensure storage directories exist
    crops_dir = settings.storage_dir / "crops" / inspection_id / sample_id
    masks_dir = settings.storage_dir / "masks" / inspection_id / sample_id
    crops_dir.mkdir(parents=True, exist_ok=True)
    masks_dir.mkdir(parents=True, exist_ok=True)

    for det in detections:
        idx = det.instance_index
        mask = det.mask  # uint8, 0 or 255, same HxW as rectified image

        # ── Save binary mask ───────────────────────────────────────────────────
        mask_filename = f"{idx:04d}.png"
        mask_abs_path = masks_dir / mask_filename
        mask_rel_path = f"masks/{inspection_id}/{sample_id}/{mask_filename}"

        try:
            cv2.imwrite(str(mask_abs_path), mask)
        except Exception:
            logger.exception("Failed to save mask for instance %d", idx)
            results.append(ExtractedCrop(
                instance_index=idx, mask_path="", crop_path="", mask_area_px=0
            ))
            continue

        # ── Extract masked crop ────────────────────────────────────────────────
        # Apply the mask to zero out background pixels
        masked_img = rectified_image.copy()
        masked_img[mask == 0] = 0  # background → black

        # Compute padded bounding box, clamped to image bounds
        x = max(0, det.bbox_x - _CROP_PADDING)
        y = max(0, det.bbox_y - _CROP_PADDING)
        x2 = min(w, det.bbox_x + det.bbox_w + _CROP_PADDING)
        y2 = min(h, det.bbox_y + det.bbox_h + _CROP_PADDING)

        crop = masked_img[y:y2, x:x2]

        # ── Save crop ──────────────────────────────────────────────────────────
        crop_filename = f"{idx:04d}.jpg"
        crop_abs_path = crops_dir / crop_filename
        crop_rel_path = f"crops/{inspection_id}/{sample_id}/{crop_filename}"

        try:
            cv2.imwrite(str(crop_abs_path), crop, [cv2.IMWRITE_JPEG_QUALITY, 90])
        except Exception:
            logger.exception("Failed to save crop for instance %d", idx)
            results.append(ExtractedCrop(
                instance_index=idx,
                mask_path=mask_rel_path,
                crop_path="",
                mask_area_px=int(np.count_nonzero(mask)),
            ))
            continue

        mask_area_px = int(np.count_nonzero(mask))
        logger.debug(
            "Extracted instance %d: mask_area=%dpx, crop=%s",
            idx, mask_area_px, crop_rel_path,
        )

        results.append(ExtractedCrop(
            instance_index=idx,
            mask_path=mask_rel_path,
            crop_path=crop_rel_path,
            mask_area_px=mask_area_px,
        ))

    return results
