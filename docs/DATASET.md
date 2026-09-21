# Onion Quality Inspection Dataset & Retraining Guide

This guide details the end-to-end process for creating a production-grade Indian onion dataset and training custom YOLO11-seg and multi-label defect classification models.

---

## 1. Field Data Collection Protocol

### Target Varieties
- **Rabi Onions** (March–May harvest, Maharashtra/MP/Gujarat): High dry-matter, red/pink, stored for buffer stock.
- **Kharif & Late Kharif** (Oct–Jan harvest): High moisture, prone to quick decay and transit damage.

### Capture Environment Setup
1. **Background Surface**: Uniform matte background (light blue or beige inspection cloth/tarp). Avoid shiny, reflective tabletops.
2. **Illumination**: Diffused natural daylight or dual-source LED ring lighting ($5000\text{K} - 6500\text{K}$). Avoid direct midday solar glare.
3. **Board Placement**: Place the ChArUco 7x5 calibration board completely within the camera frame, coplanar with the spread.
4. **Arrangement Diversity**:
   - Spread 15–30 bulbs per photograph.
   - Intentionally include touching bulbs (30% of frames) and partial occlusions (15% of frames).
   - Capture a representative spread of sizes: $<35\text{mm}$, $35-45\text{mm}$, $45-65\text{mm}$, $>70\text{mm}$.
   - Ensure samples contain genuine agricultural defects: dry neck rot, basal plate rot, mechanical shovel cuts, green sprouted shoots, and sunburn discoloration.

---

## 2. Annotation Guidelines & Formats

### Tool Recommendation
- **Label Studio** (Self-hosted open source) or **Roboflow** (Team collaboration).
- Export Format: **YOLOv11 Instance Segmentation** (`*.txt` polygon format).

### Boundary Labeling Rules
1. **Bulb Outline**: Annotate tightly along the bulb outer tunic. Exclude loose papery dry scales peeling off by $>5\text{ mm}$.
2. **Neck & Stem**: Include the stem neck up to $15\text{ mm}$ from bulb shoulder. Exclude elongated dry stalks.
3. **Roots**: Exclude the dry fibrous root tuft from the circular bulb mask.
4. **Touching Bulbs**: Never merge two touching bulbs into a single mask. Cut strictly along the visible contact seam.
5. **Defect Multi-Label Tags**: For every annotated bulb polygon, assign independent binary attributes:
   - `damaged`: $[0, 1]$
   - `rotten`: $[0, 1]$
   - `sprouted`: $[0, 1]$

### YOLO Polygon Format Example (`labels/train/img_001.txt`)
Each line represents an instance:
```
<class_id> <x1> <y1> <x2> <y2> ... <xn> <yn>
```
Normalized coordinates $[0.0, 1.0]$. `class_id = 0` corresponds to `onion`.

---

## 3. Training Custom YOLO11-seg Models

A turnkey training script is provided below for fine-tuning YOLO11s-seg:

```python
# cv_tools/train_yolo11_seg.py
from ultralytics import YOLO

def train():
    # Load pretrained YOLO11 small segmentation weights
    model = YOLO("yolo11s-seg.pt")

    results = model.train(
        data="dataset.yaml",      # dataset configuration
        epochs=100,               # 100 epochs with early stopping
        imgsz=1024,               # 1024px preserves small defect details
        batch=8,                  # Adjust according to available VRAM
        workers=4,
        device="0",               # "0" for GPU or "cpu"
        optimizer="AdamW",
        lr0=0.001,
        augment=True,             # Mosaic, random rotation, color jitter
        degrees=180.0,            # Rotation invariance is crucial for onions
        hsv_h=0.015,
        hsv_s=0.4,
        hsv_v=0.4,
        project="cepa_training",
        name="yolo11s_onion_run1",
        patience=20,
    )

    # Export to optimized formats
    model.export(format="onnx", dynamic=True)

if __name__ == "__main__":
    train()
```

### `dataset.yaml` Schema
```yaml
path: ../datasets/onion_seg
train: images/train
val: images/val
test: images/test

names:
  0: onion
```

---

## 4. Multi-Label Defect Classifier Training

To train the crop classifier on extracted `storage/crops/`:
- **Architecture**: MobileNetV3-Large or EfficientNet-B0 pretrained on ImageNet.
- **Head**: Linear projection with 3 independent outputs followed by `nn.BCEWithLogitsLoss()`.
- **Target Metrics**: Macro F1-score $\ge 0.88$ on surface rot and sprouting.
