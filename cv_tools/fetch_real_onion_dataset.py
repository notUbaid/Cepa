"""
Fetch Authentic Real-World Onion Dataset from Open Wikimedia Commons API

Searches and downloads authentic high-resolution photographs of real onions:
1. Red onions (Nashik Red, Bellary culinary bulbs)
2. Sprouted onions (apical vegetative shoots)
3. Rotten / diseased onions (Aspergillus niger black mold, soft rot)
4. Mechanically damaged / skinned onions
5. Harvest field spreads

Extracts individual bulb crops using automated morphological foreground isolation,
filters out irrelevant artifacts, and organizes crops into:
  cv_tools/dataset/real_onions/crops/{healthy, sprouted, rotten, damaged}/
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import urllib.parse
import urllib.request
import cv2
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("fetch_real_onions")

BASE_DIR = Path(__file__).parent / "dataset" / "real_onions"
RAW_DIR = BASE_DIR / "raw"
CROPS_DIR = BASE_DIR / "crops"

CATEGORIES = {
    "healthy": [
        "red onion bulb",
        "red onion whole",
        "yellow onion bulb",
        "Allium cepa bulb",
        "onion harvest",
        "fresh onions",
    ],
    "sprouted": [
        "sprouted onion",
        "sprouting onion bulb",
        "onion sprouts",
        "Allium cepa sprouting",
    ],
    "rotten": [
        "rotten onion",
        "bawang merah busuk",
        "decayed onion",
        "onion black mold",
        "onion Aspergillus",
    ],
    "damaged": [
        "peeled onion",
        "cut onion bulb",
        "damaged onion",
        "sliced red onion",
    ],
}

HEADERS = {
    "User-Agent": "CepaInspectionBot/1.0 (Agricultural Quality Assurance Research; contact@cepa-sih.internal)"
}


def search_wikimedia_files(query: str, limit: int = 8) -> list[str]:
    """Search Wikimedia Commons for image files matching query."""
    params = {
        "action": "query",
        "list": "search",
        "srsearch": f"{query} filetype:bitmap",
        "srnamespace": "6",  # File namespace
        "srlimit": str(limit),
        "format": "json",
    }
    url = f"https://commons.wikimedia.org/w/api.php?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers=HEADERS)

    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            results = data.get("query", {}).get("search", [])
            return [r["title"] for r in results if not r["title"].lower().endswith((".svg", ".pdf", ".ogg", ".webm"))]
    except Exception as e:
        logger.warning("Wikimedia search failed for '%s': %s", query, e)
        return []


def get_image_direct_url(file_title: str) -> str | None:
    """Get direct download URL for a Wikimedia file."""
    params = {
        "action": "query",
        "titles": file_title,
        "prop": "imageinfo",
        "iiprop": "url",
        "format": "json",
    }
    url = f"https://commons.wikimedia.org/w/api.php?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers=HEADERS)

    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            pages = data.get("query", {}).get("pages", {})
            for page in pages.values():
                imageinfo = page.get("imageinfo", [])
                if imageinfo:
                    return imageinfo[0].get("url")
    except Exception as e:
        logger.warning("Failed to get direct URL for %s: %s", file_title, e)
    return None


def download_image(url: str, save_path: Path) -> bool:
    """Download image to disk."""
    if save_path.exists() and save_path.stat().st_size > 1000:
        return True
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=20) as resp:
            content = resp.read()
            if len(content) < 5000:  # Skip tiny icons / thumbnails
                return False
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, "wb") as f:
                f.write(content)
        return True
    except Exception as e:
        logger.warning("Download failed for %s: %s", url, e)
        return False


def extract_bulb_crops(
    img_path: Path,
    label: str,
    target_crop_dir: Path,
    min_bulb_size: int = 120,
    crop_output_size: int = 224,
) -> int:
    """
    Extract individual onion bulbs from an image using color saliency and morphology.
    Saves isolated 224x224 crops with square padding.
    """
    img = cv2.imread(str(img_path))
    if img is None:
        return 0

    h, w = img.shape[:2]
    # Resize giant images for consistent processing
    max_dim = 1600
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        h, w = img.shape[:2]

    # Convert to LAB and HSV color spaces
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # Detect onion colors (reddish, brownish, yellow, golden-orange)
    # Mask out uniform white/grey backgrounds or bright edges
    l_chan = lab[:, :, 0]
    a_chan = lab[:, :, 1]
    b_chan = lab[:, :, 2]
    h_chan = hsv[:, :, 0]
    s_chan = hsv[:, :, 1]

    # Red/yellow onion chromaticity mask
    chroma_mask = (a_chan > 130) | ((b_chan > 135) & (s_chan > 40))
    # Filter out extreme glare and dark shadows
    valid_lum = (l_chan > 35) & (l_chan < 240)
    candidate_mask = (chroma_mask & valid_lum).astype(np.uint8) * 255

    # Morphological cleaning
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    closed = cv2.morphologyEx(candidate_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel, iterations=1)

    contours, _ = cv2.findContours(opened, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    extracted = 0

    target_crop_dir.mkdir(parents=True, exist_ok=True)
    stem_name = img_path.stem

    for idx, cnt in enumerate(contours):
        area = cv2.contourArea(cnt)
        if area < (min_bulb_size * min_bulb_size * 0.4):
            continue

        x, y, bw, bh = cv2.boundingRect(cnt)
        # Filter extreme aspect ratios (not bulb-like)
        aspect = bw / float(bh)
        if aspect < 0.45 or aspect > 2.2:
            continue

        # Check contour circularity / fill
        extent = area / (bw * bh)
        if extent < 0.4:
            continue

        # Extract with margin
        pad = int(max(bw, bh) * 0.15)
        x1 = max(0, x - pad)
        y1 = max(0, y - pad)
        x2 = min(w, x + bw + pad)
        y2 = min(h, y + bh + pad)

        crop = img[y1:y2, x1:x2]
        if crop.shape[0] < 50 or crop.shape[1] < 50:
            continue

        # Make square with edge padding
        ch, cw = crop.shape[:2]
        max_c = max(ch, cw)
        square = np.zeros((max_c, max_c, 3), dtype=np.uint8)
        off_y = (max_c - ch) // 2
        off_x = (max_c - cw) // 2
        square[off_y : off_y + ch, off_x : off_x + cw] = crop

        # Resize to standard model input 224x224
        resized = cv2.resize(square, (crop_output_size, crop_output_size), interpolation=cv2.INTER_AREA)

        out_name = f"real_{label}_{stem_name}_{idx:02d}.jpg"
        out_path = target_crop_dir / out_name
        cv2.imwrite(str(out_path), resized)
        extracted += 1

    return extracted


def run_dataset_pipeline(max_per_category: int = 10) -> dict[str, int]:
    """Execute the full real-onion harvesting and cropping pipeline."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    CROPS_DIR.mkdir(parents=True, exist_ok=True)

    summary: dict[str, int] = {}

    for label, queries in CATEGORIES.items():
        label_crops_dir = CROPS_DIR / label
        label_raw_dir = RAW_DIR / label
        label_raw_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Fetching real images for label: %s", label.upper())
        files_to_download: set[str] = set()

        for q in queries:
            matched = search_wikimedia_files(q, limit=5)
            for m in matched:
                files_to_download.add(m)
                if len(files_to_download) >= max_per_category:
                    break
            if len(files_to_download) >= max_per_category:
                break

        logger.info("Found %d real candidate files for %s", len(files_to_download), label)
        downloaded_count = 0
        total_crops = 0

        for file_title in files_to_download:
            direct_url = get_image_direct_url(file_title)
            if not direct_url:
                continue

            # Safe filename
            safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in file_title)
            save_path = label_raw_dir / safe_name
            if download_image(direct_url, save_path):
                downloaded_count += 1
                n_crops = extract_bulb_crops(save_path, label, label_crops_dir)
                total_crops += n_crops

        logger.info(
            "Category %s: Downloaded %d raw images -> Extracted %d authentic bulb crops",
            label, downloaded_count, total_crops
        )
        summary[label] = total_crops

    logger.info("Real onion dataset extraction completed! Total crops: %s", summary)
    return summary


if __name__ == "__main__":
    run_dataset_pipeline(max_per_category=10)
