# ADR-0003: Dual-Stage Botanical Morphology & Pigment Validation Gate

## Status
Accepted

## Date
2026-09-30 (Updated 2026-10-04)

## Context
Computer vision models trained on bounded datasets can hallucinate when presented with out-of-distribution inputs. In agricultural intake, adversarial or erroneous inputs include:
- Stones, clods of dirt, tennis balls, potatoes, or garlic presented as onions.
- Synthetically generated AI images designed to game mandi procurement payouts.
- Debris, leaves, or hands entering the camera frame during sorting sweeps.

If standard YOLO segmentation masks treat these non-allium items as Grade A onions, farmers and procurement agencies suffer catastrophic economic damage.

## Decision
We enforce a **Dual-Stage Botanical Validation Gate** (`backend/cv/onion_validator.py`):

1. **Stage 1: Deep Feature Rejection (MobileNetV3-Small / Torchvision Classifier)**:
   - Evaluates whether the bounding region belongs to non-food or non-vegetable categories.
   - If the top ImageNet predicted class indicates an inanimate object (e.g. tennis ball, stone, ceramic) with probability $> 0.30$, the instance is immediately rejected.
   - If offline or weights unavailable, Stage 1 gracefully yields to Stage 2 without failing open.

2. **Stage 2: Strict Botanical Morphology & Quercetin/Anthocyanin Pigment Analysis**:
   - **Solidity Check**: Real *Allium cepa* cross-sections exhibit high convexity. The contour must satisfy:
     $$\text{Solidity} = \frac{\text{Contour Area}}{\text{Convex Hull Area}} \ge 0.72$$
   - **Aspect Ratio Bounds**: Equatorial-to-polar axis ratio must satisfy:
     $$0.58 \le \frac{W_{\text{bbox}}}{H_{\text{bbox}}} \le 1.70$$
   - **Colorimetric Spectrometry (HSV/CIE-LAB)**: Indian commercial onion cultivars (Nashik Red, Garwa, Rabi) have distinct tunic pigmentation characterized by quercetin (yellow-brown flavonol) and cyanidin (red anthocyanin). The crop patch must contain $\ge 65\%$ pigment within valid botanical hue/saturation gates ($H \in [0, 42] \cup [160, 180]$, $S \ge 38$).
   - **Scale Validity**: Apparent diameter must lie within physiological bounds ($20\text{ mm} \le D_{\text{eq}} \le 125\text{ mm}$).

## Consequences

### Positive
- Prevents non-onion debris, stones, or synthetic AI prints from receiving valid NAFED grading certificates.
- Resilient offline fallback: Stage 2 executes purely in NumPy/OpenCV without neural network runtime overhead.

### Negative / Trade-offs
- Heavily caked mud on uncleaned onions can occasionally fail the tunic pigment gate until the outer dried scale is brushed.
