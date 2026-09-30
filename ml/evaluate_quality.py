import os
import json
import logging
import torch
from pathlib import Path
from PIL import Image
from torchvision import transforms
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix, classification_report
import matplotlib
matplotlib.use('Agg')
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
        classes = json.load(f)  # ["GOOD", "DAMAGED", "ROTTEN", "SPROUTED"]
        
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
    
    y_true = []
    y_pred = []
    
    with torch.no_grad():
        for item in test_data:
            img_path = item["path"]
            label_idx = item["label"]  # int: 0, 1, 2, or 3
            
            if not os.path.exists(img_path):
                continue
            
            image = Image.open(img_path).convert("RGB")
            tensor = val_transform(image).unsqueeze(0).to(device)
            
            out = model(tensor)
            pred_idx = int(torch.argmax(out, dim=1).item())
            
            y_true.append(label_idx)
            y_pred.append(pred_idx)
            
    if len(y_true) == 0:
        logger.error("No valid test images found.")
        return
        
    acc = accuracy_score(y_true, y_pred)
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=[0, 1, 2, 3], zero_division=0
    )
    
    per_class_metrics = {}
    for i, cls_name in enumerate(classes):
        per_class_metrics[cls_name] = {
            "precision": float(precision[i]),
            "recall": float(recall[i]),
            "f1": float(f1[i]),
            "support": int(support[i]),
        }
        
    metrics = {
        "status": "VALIDATED",
        "total_test_images": len(y_true),
        "overall_accuracy": float(acc),
        "classes": classes,
        "per_class": per_class_metrics,
        "classification_report": classification_report(y_true, y_pred, target_names=classes, zero_division=0, output_dict=True)
    }
    
    with open(reports_dir / "quality_metrics.json", "w") as f:
        json.dump(metrics, f, indent=4)
        
    # 4-class Confusion Matrix
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1, 2, 3])
    plt.figure(figsize=(7, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=classes, yticklabels=classes)
    plt.xlabel('Predicted')
    plt.ylabel('Actual')
    plt.title('4-Class Onion Quality Confusion Matrix')
    plt.tight_layout()
    plt.savefig(reports_dir / "confusion_matrix.png")
    plt.close()
    
    logger.info("=" * 60)
    logger.info(f"Evaluation Complete! Total Test Samples: {len(y_true)}")
    logger.info(f"Overall Accuracy: {acc:.2%}")
    for cls_name, vals in per_class_metrics.items():
        logger.info(f"  {cls_name:10s} | Prec: {vals['precision']:.2%} | Rec: {vals['recall']:.2%} | F1: {vals['f1']:.2%} | N={vals['support']}")
    logger.info("=" * 60)

if __name__ == "__main__":
    evaluate_model()
