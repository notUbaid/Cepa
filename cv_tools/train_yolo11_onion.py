"""
Onion Instance Segmentation Dataset Generator & YOLO11 Fine-Tuning Pipeline

1. Generates authentic synthetic onion spread images with ground-truth polygon masks
2. Writes dataset in official YOLOv11 segmentation format
3. Fine-tunes YOLO11n-seg on onion instance segmentation
4. Overwrites backend/weights/yolo11n-seg.pt with the fine-tuned onion model
"""
from pathlib import Path
import random
import shutil
import cv2
import numpy as np
from ultralytics import YOLO

ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = Path(__file__).parent / "dataset" / "onion_seg"
WEIGHTS_DEST = ROOT_DIR / "backend" / "weights" / "yolo11n-seg.pt"


def generate_dataset(num_train: int = 35, num_val: int = 8, img_size: int = 640):
    # Setup directory tree
    for split in ["train", "val"]:
        (DATA_DIR / "images" / split).mkdir(parents=True, exist_ok=True)
        (DATA_DIR / "labels" / split).mkdir(parents=True, exist_ok=True)

    total_images = num_train + num_val
    print(f"Synthesizing {total_images} onion spread images with polygon masks...")

    for i in range(total_images):
        split = "train" if i < num_train else "val"
        filename = f"onion_spread_{i:04d}"

        # Canvas: light neutral background table
        img = np.full((img_size, img_size, 3), random.randint(190, 210), dtype=np.uint8)
        # Subtle texture noise
        noise = np.random.normal(0, 3, img.shape).astype(np.int16)
        img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        labels_lines = []
        n_bulbs = random.randint(8, 18)

        # Keep track of placed bulbs to allow touching/clustering
        placed = []

        for _ in range(n_bulbs):
            r_x = random.randint(22, 45)
            r_y = int(r_x * random.uniform(0.85, 1.15))
            cx = random.randint(r_x + 10, img_size - r_x - 10)
            cy = random.randint(r_y + 10, img_size - r_y - 10)
            angle = random.randint(0, 180)

            # Base onion skin color (Red / Pink / Yellow)
            variety = random.choice(["red", "pink", "yellow"])
            if variety == "red":
                color = [random.randint(35, 55), random.randint(60, 85), random.randint(145, 185)]
            elif variety == "pink":
                color = [random.randint(70, 95), random.randint(90, 120), random.randint(180, 215)]
            else:
                color = [random.randint(50, 80), random.randint(150, 190), random.randint(200, 230)]

            # Drop shadow
            cv2.ellipse(img, (cx + 3, cy + 3), (r_x, r_y), angle, 0, 360, (140, 150, 155), -1)

            # Onion body
            cv2.ellipse(img, (cx, cy), (r_x, r_y), angle, 0, 360, tuple(color), -1)

            # Concentric tunic rings
            for scale in [0.75, 0.5, 0.25]:
                sub_axes = (int(r_x * scale), int(r_y * scale))
                sub_color = tuple(min(255, int(c * 1.15)) for c in color)
                cv2.ellipse(img, (cx, cy), sub_axes, angle, 0, 360, sub_color, 1)

            # Generate polygon boundary points (e.g. 24 points around ellipse)
            pts = []
            for theta in np.linspace(0, 2 * np.pi, 24, endpoint=False):
                # Ellipse point before rotation
                px = r_x * np.cos(theta)
                py = r_y * np.sin(theta)
                # Rotate by angle
                rad = np.radians(angle)
                rot_x = cx + px * np.cos(rad) - py * np.sin(rad)
                rot_y = cy + px * np.sin(rad) + py * np.cos(rad)
                # Normalize [0, 1]
                pts.extend([round(rot_x / img_size, 4), round(rot_y / img_size, 4)])

            # Class 0: onion
            line = "0 " + " ".join(str(p) for p in pts)
            labels_lines.append(line)

        # Save image and label
        img_path = DATA_DIR / "images" / split / f"{filename}.jpg"
        lbl_path = DATA_DIR / "labels" / split / f"{filename}.txt"

        cv2.imwrite(str(img_path), img, [cv2.IMWRITE_JPEG_QUALITY, 92])
        with open(lbl_path, "w") as f:
            f.write("\n".join(labels_lines) + "\n")

    # Write data.yaml
    yaml_content = f"""path: {DATA_DIR.resolve().as_posix()}
train: images/train
val: images/val

names:
  0: onion
"""
    yaml_path = DATA_DIR / "data.yaml"
    with open(yaml_path, "w") as f:
        f.write(yaml_content)

    print(f"Dataset generated at {DATA_DIR} with data.yaml")
    return yaml_path


def train_yolo(data_yaml: Path, epochs: int = 5):
    print("Loading YOLO11n-seg for onion fine-tuning...")
    model = YOLO("backend/weights/yolo11n-seg.pt")

    print(f"Training for {epochs} epochs on onion instance segmentation...")
    results = model.train(
        data=str(data_yaml),
        epochs=epochs,
        imgsz=640,
        batch=4,
        workers=2,
        device="cpu",
        project=str(DATA_DIR / "runs"),
        name="onion_seg_run",
        verbose=False,
    )

    # Find the best.pt or last.pt
    best_pt = Path(results.save_dir) / "weights" / "best.pt"
    if not best_pt.exists():
        best_pt = Path(results.save_dir) / "weights" / "last.pt"

    if best_pt.exists():
        shutil.copy(best_pt, WEIGHTS_DEST)
        print(f"✓ Fine-tuned YOLO11 onion model saved to: {WEIGHTS_DEST}")
    else:
        print("Warning: Trained weights not found in save_dir.")


if __name__ == "__main__":
    yaml_file = generate_dataset(num_train=30, num_val=8)
    train_yolo(yaml_file, epochs=4)
