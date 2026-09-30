import os
import glob
import hashlib
import json
import shutil
import logging
from pathlib import Path
from PIL import Image
import imagehash
import yaml
from collections import defaultdict
import random

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def load_sources_config(yaml_path="ml/dataset_sources.yaml"):
    with open(yaml_path, "r") as f:
        return yaml.safe_load(f)["sources"]

def get_image_hash(filepath):
    """Returns SHA256 and Perceptual Hash (PHash)"""
    try:
        with open(filepath, "rb") as f:
            sha256 = hashlib.sha256(f.read()).hexdigest()
        img = Image.open(filepath).convert("RGB")
        phash = str(imagehash.phash(img))
        return sha256, phash, img.size
    except Exception as e:
        logger.warning(f"Error hashing {filepath}: {e}")
        return None, None, None

def audit_datasets():
    raw_dir = Path("ml/datasets/raw")
    if not raw_dir.exists():
        logger.error(f"Directory {raw_dir} does not exist.")
        return
        
    sources = load_sources_config()
    
    # Store images by perceptual hash to find near-duplicates
    hash_map = defaultdict(list)
    sha256_map = defaultdict(list)
    
    total_images_found = 0
    corrupted_images = 0
    valid_images = []
    
    logger.info("Scanning for images...")
    for ext in ["*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG"]:
        for filepath in raw_dir.rglob(ext):
            total_images_found += 1
            sha256, phash, size = get_image_hash(filepath)
            
            if sha256 is None:
                corrupted_images += 1
                continue
                
            hash_map[phash].append(filepath)
            sha256_map[sha256].append(filepath)
            valid_images.append({
                "path": str(filepath),
                "sha256": sha256,
                "phash": phash,
                "size": size,
                "source": filepath.parts[3] if len(filepath.parts) > 3 else "unknown"
            })
            
    logger.info(f"Total files: {total_images_found}")
    logger.info(f"Corrupted: {corrupted_images}")
    logger.info(f"Unique exact images (SHA256): {len(sha256_map)}")
    logger.info(f"Unique perceptual images (PHash): {len(hash_map)}")
    
    duplicates_count = sum(len(paths) - 1 for paths in hash_map.values() if len(paths) > 1)
    logger.info(f"Cross-dataset / internal duplicates to discard: {duplicates_count}")
    
    # Let's save a deduplicated mapping
    dedup_list = []
    for phash, paths in hash_map.items():
        # Just pick the first one as the canonical version
        canonical = paths[0]
        dedup_list.append(str(canonical))
        
    with open("ml/datasets/audit_report.json", "w") as f:
        json.dump({
            "total_files": total_images_found,
            "corrupted": corrupted_images,
            "exact_duplicates": sum(len(paths) - 1 for paths in sha256_map.values()),
            "perceptual_duplicates": duplicates_count,
            "usable_images_after_dedup": len(dedup_list)
        }, f, indent=4)
        
    logger.info(f"Audit complete. Usable images: {len(dedup_list)}")
    
    # --- BUILD FINAL DATASET ---
    final_dir = Path("ml/datasets/onion_quality")
    for cls in ["GOOD", "DAMAGED", "ROTTEN", "SPROUTED", "UNHEALTHY_AUXILIARY"]:
        (final_dir / cls).mkdir(parents=True, exist_ok=True)
        
    copied = 0
    for path_str in dedup_list:
        p = Path(path_str)
        p_str_lower = str(p).lower()
        
        target_class = None
        
        if "mendeley" in p_str_lower:
            if "healthy" in p_str_lower and "unhealthy" not in p_str_lower:
                target_class = "GOOD"
            elif "unhealthy" in p_str_lower:
                target_class = "UNHEALTHY_AUXILIARY"
                
        elif "harvard_dataverse" in p_str_lower:
            target_class = "GOOD"
            
        if target_class:
            dest = final_dir / target_class / f"{copied}_{p.name}"
            shutil.copy2(p, dest)
            copied += 1
            
    logger.info(f"Successfully copied {copied} images to {final_dir}")

if __name__ == "__main__":
    audit_datasets()
