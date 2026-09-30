"""
ml/crop_detections.py

Crops bounding boxes from the chandrajith-j/onions-quality-analysis
YOLO detection dataset and saves them as per-class images.

Class mapping (indices from data.yaml):
  0: Damaged   -> DAMAGED
  1: Healthy   -> GOOD
  2: Onions-Quality-Analysis -> EXCLUDE (ambiguous label)
  3: Rotten    -> ROTTEN
  4: Sprouted  -> SPROUTED
"""

import os
import cv2
import logging
import shutil
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("crop_detections")

# Class index -> final quality label (None = exclude)
CLASS_MAP = {
    0: "DAMAGED",
    1: "GOOD",
    2: None,        # Onions-Quality-Analysis — ambiguous, excluded per user rule
    3: "ROTTEN",
    4: "SPROUTED",
}

SPLITS = ["train", "valid", "test"]
SRC_ROOT = Path("ml/datasets/raw/roboflow/chandrajith_dl")
DST_ROOT = Path("ml/datasets/onion_quality")

# Ensure destination dirs exist
for cls in ["GOOD", "DAMAGED", "ROTTEN", "SPROUTED"]:
    (DST_ROOT / cls).mkdir(parents=True, exist_ok=True)

counts = {cls: 0 for cls in ["GOOD", "DAMAGED", "ROTTEN", "SPROUTED"]}
excluded = 0
crop_id = 0

for split in SPLITS:
    img_dir = SRC_ROOT / split / "images"
    lbl_dir = SRC_ROOT / split / "labels"

    if not img_dir.exists():
        logger.warning(f"Split dir not found: {img_dir}")
        continue

    for lbl_path in sorted(lbl_dir.glob("*.txt")):
        stem = lbl_path.stem
        # Find matching image
        img_path = None
        for ext in [".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG"]:
            candidate = img_dir / (stem + ext)
            if candidate.exists():
                img_path = candidate
                break

        if img_path is None:
            logger.warning(f"No image found for label: {lbl_path}")
            continue

        img = cv2.imread(str(img_path))
        if img is None:
            logger.warning(f"Failed to read image: {img_path}")
            continue

        h, w = img.shape[:2]

        with open(lbl_path, "r") as f:
            lines = f.read().strip().splitlines()

        for i, line in enumerate(lines):
            parts = line.strip().split()
            if len(parts) < 5:
                continue

            cls_idx = int(parts[0])
            cx, cy, bw, bh = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])

            final_label = CLASS_MAP.get(cls_idx)
            if final_label is None:
                excluded += 1
                continue

            # Convert YOLO normalized coords to pixel coords
            x1 = int((cx - bw / 2) * w)
            y1 = int((cy - bh / 2) * h)
            x2 = int((cx + bw / 2) * w)
            y2 = int((cy + bh / 2) * h)

            # Clamp to image bounds
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)

            if x2 <= x1 or y2 <= y1:
                continue  # Invalid crop

            crop = img[y1:y2, x1:x2]
            if crop.size == 0:
                continue

            out_name = f"rf_{split}_{stem}_crop{i}_{crop_id}.jpg"
            out_path = DST_ROOT / final_label / out_name
            cv2.imwrite(str(out_path), crop)
            counts[final_label] += 1
            crop_id += 1

logger.info("=" * 50)
logger.info("Crop extraction complete!")
logger.info(f"  GOOD:     {counts['GOOD']}")
logger.info(f"  DAMAGED:  {counts['DAMAGED']}")
logger.info(f"  ROTTEN:   {counts['ROTTEN']}")
logger.info(f"  SPROUTED: {counts['SPROUTED']}")
logger.info(f"  EXCLUDED (Onions-Quality-Analysis label): {excluded}")
logger.info(f"  TOTAL saved: {sum(counts.values())}")

# Print final dataset distribution
logger.info("")
logger.info("FINAL DATASET DISTRIBUTION (ml/datasets/onion_quality/):")
total = 0
for cls in ["GOOD", "DAMAGED", "ROTTEN", "SPROUTED"]:
    n = sum(1 for f in (DST_ROOT / cls).glob("*") if f.suffix.lower() in [".jpg", ".jpeg", ".png"])
    logger.info(f"  {cls}: {n}")
    total += n
logger.info(f"  TOTAL: {total}")
