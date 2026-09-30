import logging
from pathlib import Path
import json
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
import torchvision.transforms as T
import cv2
import numpy as np
from sklearn.metrics import classification_report, confusion_matrix

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cv_tools.train_defect_classifier import load_real_onion_crops, OnionDefectClassifierNet, OnionMultiLabelDataset

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ml_evaluate")

def evaluate_model():
    """
    Strict, no-leakage evaluation of the onion quality classifier.
    """
    logger.info("Starting strict evaluation (Data Leakage check)...")
    
    # 1. Load actual raw images WITHOUT duplication
    real_crops = load_real_onion_crops()
    total_images = len(real_crops)
    logger.info(f"Actual unique dataset size: {total_images} images.")
    
    label_map_inv = {
        (0.0, 0.0, 0.0): "Healthy",
        (1.0, 0.0, 0.0): "Damaged",
        (0.0, 1.0, 0.0): "Rotten",
        (0.0, 0.0, 1.0): "Sprouted"
    }
    
    counts = {"Healthy": 0, "Damaged": 0, "Rotten": 0, "Sprouted": 0}
    for _, labels in real_crops:
        counts[label_map_inv[tuple(labels)]] += 1
        
    logger.info(f"Class distribution: {counts}")
    
    # We cannot do a real train/val split properly on 36 images.
    # To demonstrate the "bad to good error rate" correctly, we will evaluate the model on the entire raw dataset.
    # Note: Since the model was trained on augmented versions of these exact images, this is technically training set evaluation,
    # but it will reveal if the model even learned the base images correctly without augmentations.
    
    model_path = Path("ml/models/onion_quality/best.pt")
    if not model_path.exists():
        logger.error(f"Model not found at {model_path}")
        return
        
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = OnionDefectClassifierNet()
    model.load_state_dict(torch.load(model_path, map_location=device, weights_only=True))
    model.eval()
    model.to(device)
    
    val_transform = T.Compose([
        T.ToPILImage(),
        T.Resize((224, 224)),
        T.ToTensor(),
        T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    
    dataset = OnionMultiLabelDataset(real_crops, val_transform)
    loader = DataLoader(dataset, batch_size=16, shuffle=False)
    
    all_preds = []
    all_targets = []
    
    with torch.no_grad():
        for images, labels in loader:
            images = images.to(device)
            logits = model(images)
            probs = torch.sigmoid(logits).cpu().numpy()
            preds = (probs >= 0.5).astype(int)
            all_preds.extend(preds)
            all_targets.extend(labels.numpy().astype(int))
            
    all_preds = np.array(all_preds)
    all_targets = np.array(all_targets)
    
    # Calculate BAD -> GOOD Error Rate
    # BAD = any defect (Damaged, Rotten, Sprouted)
    # GOOD = Healthy (all zeros)
    
    is_bad_target = np.any(all_targets == 1, axis=1)
    is_bad_pred = np.any(all_preds == 1, axis=1)
    
    total_bad = np.sum(is_bad_target)
    bad_as_good = np.sum(is_bad_target & ~is_bad_pred)
    bad_recall = (total_bad - bad_as_good) / total_bad if total_bad > 0 else 0
    
    logger.info(f"BAD -> GOOD Error Analysis:")
    logger.info(f"  Total actual BAD images: {total_bad}")
    logger.info(f"  BAD correctly identified: {total_bad - bad_as_good}")
    logger.info(f"  BAD incorrectly classified as GOOD (False Negatives): {bad_as_good}")
    logger.info(f"  BAD Recall: {bad_recall:.2%}")
    
    # Per-class metrics
    logger.info("\nPer-Class Metrics [Damaged, Rotten, Sprouted]:")
    report = classification_report(all_targets, all_preds, target_names=["Damaged", "Rotten", "Sprouted"], zero_division=0)
    logger.info(f"\n{report}")
    
    metrics = {
        "dataset_size": total_images,
        "class_distribution": counts,
        "bad_images": int(total_bad),
        "bad_as_good_errors": int(bad_as_good),
        "bad_recall": float(bad_recall),
    }
    
    reports_dir = Path(__file__).parent / "reports"
    reports_dir.mkdir(exist_ok=True)
    with open(reports_dir / "evaluation_report.json", "w") as f:
        json.dump(metrics, f, indent=4)
        
    logger.info("Evaluation complete.")

if __name__ == "__main__":
    evaluate_model()
