"""
Train YOLO11n-seg on Photorealistic Real-World Mandi Onion Dataset
"""
import shutil
import time
from pathlib import Path
from ultralytics import YOLO

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_YAML = ROOT_DIR / "cv_tools" / "dataset" / "onion_seg_real" / "data.yaml"
BASE_WEIGHTS = ROOT_DIR / "backend" / "weights" / "yolo11n-seg.pt"
DEST_WEIGHTS = ROOT_DIR / "backend" / "weights" / "yolo11n-seg.pt"
BACKUP_WEIGHTS = ROOT_DIR / "backend" / "weights" / "yolo11n-seg-coco.pt"

def train():
    if not DATA_YAML.exists():
        raise FileNotFoundError(f"data.yaml not found at {DATA_YAML}")

    # Backup original COCO weights if not already backed up
    if BASE_WEIGHTS.exists() and not BACKUP_WEIGHTS.exists():
        shutil.copy(BASE_WEIGHTS, BACKUP_WEIGHTS)
        print(f"Backed up COCO weights to {BACKUP_WEIGHTS}")

    print("Loading pre-trained YOLO11n-seg weights...")
    start_weights = BACKUP_WEIGHTS if BACKUP_WEIGHTS.exists() else "yolo11n-seg.pt"
    model = YOLO(str(start_weights))

    print(f"Beginning fine-tuning on photorealistic onion dataset: {DATA_YAML}")
    t0 = time.time()
    results = model.train(
        data=str(DATA_YAML),
        epochs=15,
        imgsz=640,
        batch=8,
        workers=2,
        device="cpu",
        project=str(ROOT_DIR / "cv_tools" / "dataset" / "onion_seg_real" / "runs"),
        name="onion_real_run",
        exist_ok=True,
        lr0=0.01,
        lrf=0.01,
        cos_lr=True,
        mosaic=0.8,
        mixup=0.1,
        verbose=True,
    )
    elapsed = time.time() - t0
    print(f"Training completed in {elapsed:.1f} seconds.")

    best_pt = Path(results.save_dir) / "weights" / "best.pt"
    if not best_pt.exists():
        best_pt = Path(results.save_dir) / "weights" / "last.pt"

    if best_pt.exists():
        shutil.copy(best_pt, DEST_WEIGHTS)
        print(f"SUCCESS: Fine-tuned onion model saved to {DEST_WEIGHTS} ({best_pt.stat().st_size} bytes)")
    else:
        print("Warning: Trained weights not found in save_dir!")

if __name__ == "__main__":
    train()
