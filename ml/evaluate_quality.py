import os
import json
import logging
import torch
from pathlib import Path
from PIL import Image
from torchvision import transforms, models
import torch.nn as nn
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("eval_quality")

def evaluate_model():
    model_dir = Path("ml/models/onion_quality")
    reports_dir = Path("ml/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    test_data_path = model_dir / "test_data.json"
    if not test_data_path.exists():
        logger.error("No test_data.json found. Run train_quality.py first.")
        return
        
    with open(test_data_path, "r") as f:
        test_data = json.load(f)
        
    with open(model_dir / "class_names.json", "r") as f:
        classes = json.load(f)
        
    if len(test_data) < 5:
        logger.warning(f"Only {len(test_data)} test images available. INSUFFICIENT DATA FOR RELIABLE GENERALIZATION.")
        
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    import sys
    backend_path = os.path.abspath("backend")
    if backend_path not in sys.path:
        sys.path.append(backend_path)
    from cv.defect_classifier import OnionDefectClassifierNet
    
    model = OnionDefectClassifierNet().to(device)
    model.load_state_dict(torch.load(model_dir / "best.pt", map_location=device))
    model.eval()
    
    val_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    
    y_true_binary = []  # Is it BAD (1) or GOOD (0)
    y_pred_binary = []  # Is it predicted BAD (1) or GOOD (0)
    
    bad_total = 0
    bad_to_good_errors = 0
    
    with torch.no_grad():
        for item in test_data:
            img_path = item["path"]
            label = item["label"]  # list of 3 floats: [damaged, rotten, sprouted]
            
            if not os.path.exists(img_path): continue
            
            image = Image.open(img_path).convert("RGB")
            tensor = val_transform(image).unsqueeze(0).to(device)
            
            out = model(tensor)
            probs = torch.sigmoid(out).squeeze(0).cpu().tolist()
            
            is_bad_true = sum(label) > 0  # If any defect is 1.0, it's BAD
            is_bad_pred = any(p >= 0.5 for p in probs)  # If any prob >= 0.5, predict BAD
            
            y_true_binary.append(1 if is_bad_true else 0)
            y_pred_binary.append(1 if is_bad_pred else 0)
            
            if is_bad_true:
                bad_total += 1
                if not is_bad_pred:
                    bad_to_good_errors += 1
            
    if len(y_true_binary) == 0:
        logger.error("No valid test images found.")
        return
        
    acc = accuracy_score(y_true_binary, y_pred_binary)
    prec = precision_score(y_true_binary, y_pred_binary, zero_division=0)
    rec = recall_score(y_true_binary, y_pred_binary, zero_division=0)
    f1 = f1_score(y_true_binary, y_pred_binary, zero_division=0)
    
    bad_to_good_rate = (bad_to_good_errors / bad_total) if bad_total > 0 else 0
    
    metrics = {
        "status": "INSUFFICIENT DATA FOR RELIABLE GENERALIZATION" if len(test_data) < 20 else "VALIDATED",
        "total_test_images": len(test_data),
        "overall_accuracy": float(acc),
        "precision_bad": float(prec),
        "recall_bad": float(rec),
        "f1_bad": float(f1),
        "bad_to_good_fn_rate": float(bad_to_good_rate),
        "bad_to_good_fn_count": bad_to_good_errors,
        "total_bad_test_images": bad_total
    }
    
    with open(reports_dir / "quality_metrics.json", "w") as f:
        json.dump(metrics, f, indent=4)
        
    # Confusion Matrix (GOOD vs BAD)
    cm = confusion_matrix(y_true_binary, y_pred_binary, labels=[0, 1])
    plt.figure(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=["GOOD", "BAD"], yticklabels=["GOOD", "BAD"])
    plt.xlabel('Predicted')
    plt.ylabel('Actual')
    plt.title('Quality Classifier Confusion Matrix (GOOD vs BAD)')
    plt.savefig(reports_dir / "confusion_matrix.png")
    
    logger.info(f"Evaluation complete. Status: {metrics['status']}")
    logger.info(f"BAD->GOOD False Negative Rate: {bad_to_good_rate:.2%}")

if __name__ == "__main__":
    evaluate_model()
