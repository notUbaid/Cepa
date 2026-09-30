import os
import json
import random
import logging
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms, models
from pathlib import Path
from PIL import Image

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("train_quality")

class OnionQualityDataset(Dataset):
    def __init__(self, image_paths, labels, transform=None):
        self.image_paths = image_paths
        self.labels = labels
        self.transform = transform

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        img_path = self.image_paths[idx]
        image = Image.open(img_path).convert('RGB')
        label = self.labels[idx]
        
        if self.transform:
            image = self.transform(image)
            
        return image, torch.tensor(label, dtype=torch.long)

def get_class_weights(labels, num_classes=4):
    import numpy as np
    counts = np.bincount(labels, minlength=num_classes)
    total = len(labels)
    weights = total / (num_classes * (counts + 1e-6))
    return torch.FloatTensor(weights)

def train_model():
    base_dir = Path("ml/datasets/onion_quality")
    out_dir = Path("ml/models/onion_quality")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    classes = ["GOOD", "DAMAGED", "ROTTEN", "SPROUTED"]
    
    # Save class names
    with open(out_dir / "class_names.json", "w") as f:
        json.dump(classes, f)
        
    all_images = []
    all_labels = []
    
    for idx, cls in enumerate(classes):
        cls_dir = base_dir / cls
        if not cls_dir.exists(): continue
        for img_path in cls_dir.glob("*"):
            if img_path.suffix.lower() in [".jpg", ".jpeg", ".png"]:
                all_images.append(str(img_path))
                all_labels.append(idx)
            
    if len(all_images) < 20:
        logger.error(f"Dataset too small ({len(all_images)} images) for training. Please run download and audit first.")
        return
        
    # SPLIT BEFORE AUGMENTATION (Avoid Data Leakage)
    data = list(zip(all_images, all_labels))
    random.shuffle(data)
    
    n = len(data)
    train_size = int(0.7 * n)
    val_size = int(0.15 * n)
    
    train_data = data[:train_size]
    val_data = data[train_size:train_size+val_size]
    test_data = data[train_size+val_size:]
    
    logger.info(f"Unique images split: Train={len(train_data)}, Val={len(val_data)}, Test={len(test_data)}")
    
    # No synthetic data: only deterministic resize + normalize.
    # Real-image geometric transforms (random flip, rotation) are light-weight
    # standard practice and do NOT generate synthetic images; they are omitted
    # here per user instruction for full transparency.
    plain_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    
    train_dataset = OnionQualityDataset([x[0] for x in train_data], [x[1] for x in train_data], plain_transform)
    val_dataset = OnionQualityDataset([x[0] for x in val_data], [x[1] for x in val_data], plain_transform)
    
    # Save test dataset paths for evaluation script
    with open(out_dir / "test_data.json", "w") as f:
        json.dump([{"path": x[0], "label": x[1]} for x in test_data], f)
        
    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False, num_workers=0)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Training on device: {device}")
    
    import sys
    backend_path = os.path.abspath("backend")
    if backend_path not in sys.path:
        sys.path.append(backend_path)
    from cv.defect_classifier import OnionDefectClassifierNet
    
    model = OnionDefectClassifierNet()
    
    # Load pretrained ImageNet backbone (features only, no classifier head)
    pretrained_backbone = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT)
    pretrained_dict = pretrained_backbone.state_dict()
    filtered_dict = {k: v for k, v in pretrained_dict.items() if not k.startswith("classifier.")}
    model.net.load_state_dict(filtered_dict, strict=False)
    model = model.to(device)
    
    # Class-weighted loss to handle severe class imbalance:
    # GOOD: 10329, DAMAGED: 167, ROTTEN: 976, SPROUTED: 73
    train_labels = [x[1] for x in train_data]
    class_weights = get_class_weights(train_labels, num_classes=4).to(device)
    logger.info(f"Class weights: GOOD={class_weights[0]:.3f} DAMAGED={class_weights[1]:.3f} ROTTEN={class_weights[2]:.3f} SPROUTED={class_weights[3]:.3f}")
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=7, gamma=0.5)
    
    epochs = 20
    best_val_loss = float('inf')
    
    for epoch in range(epochs):
        model.train()
        train_loss = 0.0
        for inputs, labels in train_loader:
            inputs, labels = inputs.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
            
        model.eval()
        val_loss = 0.0
        correct = 0
        total = 0
        with torch.no_grad():
            for inputs, labels in val_loader:
                inputs, labels = inputs.to(device), labels.to(device)
                outputs = model(inputs)
                loss = criterion(outputs, labels)
                val_loss += loss.item()
                
                _, predicted = torch.max(outputs.data, 1)
                total += labels.size(0)
                correct += (predicted == labels).sum().item()
                
        val_acc = 100 * correct / max(total, 1)
        logger.info(f"Epoch {epoch+1}/{epochs} | Train Loss: {train_loss/len(train_loader):.4f} | Val Loss: {val_loss/max(len(val_loader),1):.4f} | Val Acc: {val_acc:.2f}%")
        
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save(model.state_dict(), out_dir / "best.pt")
            logger.info("Saved best model.")
        
        scheduler.step()

if __name__ == "__main__":
    train_model()
