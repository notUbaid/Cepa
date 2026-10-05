# Cepa Computer Vision Pipeline (8-Stage Specification)

This document provides a technical walkthrough of the 8-stage image processing and computer vision pipeline implemented in `backend/cv/`.

---

## Stage 1: Image Quality Gate (`quality_gate.py`)

Every image must pass automated quality gates before entering ML inference. If any gate fails, processing stops and returns an actionable instruction to the officer.

| Metric | Target / Normal | Failure Code | Remedy Instruction |
|---|---|---|---|
| **Resolution** | Min dimension $\ge 300\text{ px}$ | `insufficient_resolution` | Retake photo with camera setting at 50–80 cm height. |
| **Blur** | Laplacian variance $\ge 35.0$ | `image_too_blurry` | Hold phone steady, allow autofocus to lock before snapping. |
| **Underexposure** | Grayscale mean lum $\ge 25$ | `too_dark` | Move to better lighting or activate camera flash. |
| **Overexposure** | Grayscale mean lum $\le 245$ | `too_bright` | Shield spread from harsh direct sunlight. |
| **Specular Glare** | Fraction of $(R,G,B > 250) \le 45\%$ | `excessive_glare` | Reposition light source or change camera angle slightly. |

---

## Stage 2: Marker Detection (`marker_detector.py`)

- **Board Standard**: ChArUco 7x5 board, $40\text{ mm}$ square length, $20\text{ mm}$ marker length, `DICT_4X4_250`.
- **Detection Method**: OpenCV 4.7+ class-based API:
  ```python
  detector = cv2.aruco.CharucoDetector(board)
  charuco_corners, charuco_ids, marker_corners, marker_ids = detector.detectBoard(gray)
  ```
- **Requirements**: At least 6 detected corners are required for reliable homography matrix calculation. If $<6$ corners are found, `marker_partially_occluded` is returned.

---

## Stage 3: Perspective & Scale Calibration (`calibration.py`)

1. **3D World Coordinates**: Board corners mapped to physical mm space:
   $$P_{\text{board}} = (x_i \cdot 40.0, y_i \cdot 40.0, 0)$$
2. **Homography Estimation**:
   $$H = \text{findHomography}(P_{\text{image}}, P_{\text{board\_mm}}, \text{RANSAC}, 5.0)$$
3. **Perspective Rectification**:
   $$\text{rectified} = \text{warpPerspective}(\text{image}, H_{\text{shifted}}, (\text{width}, \text{height}))$$
4. **Scale Derivation**:
   $$\text{scale} = \frac{\text{physical board mm}}{\text{measured pixels in rectified space}} \quad [\text{mm/px}]$$
5. **Resolution-Invariant Parallax Calibration**:
   Instead of pixel-density dependent heuristic thresholds, CEPA evaluates board coverage fraction:
   $$\text{board\_frame\_fraction} = \frac{\text{board\_span\_px}}{\max(W, H)}$$
   - Close proximity ($\text{fraction} \ge 0.35$): $\pm 2.0\text{ mm}$ 3D parallax uncertainty.
   - Mid proximity ($0.20 \le \text{fraction} < 0.35$): $\pm 2.8\text{ mm}$ uncertainty.
   - Far proximity ($\text{fraction} < 0.20$): $\pm 3.5\text{ mm}$ uncertainty.
   - No board detected: Fallback scale ($0.6836\text{ mm/px}$), $\pm 5.0\text{ mm}$ uncertainty, force `NEEDS_REVIEW`.

---

## Stage 4: Instance Segmentation & Botanical Authenticity Gate

- **Model**: YOLO11n-seg with C2PSA attention blocks for dense clusters, backed by industrial Watershed fallback.

### 4.1 Segmentation Model Benchmarks (Held-Out Evaluation Set)

Empirically evaluated on 20 held-out mandi scene images comprising 181 annotated ground-truth onion instances at IoU threshold 0.5:

| Provider | Precision | Recall | F1 Score | Measured Details |
|:---|:---:|:---:|:---:|:---|
| **YOLO11n-seg (Fine-Tuned)** | **0.916 (91.6%)** | **0.901 (90.1%)** | **0.908 (90.8%)** | Primary provider. 106.7 ms inference on CPU. TP=163, FP=15, FN=18. |
| **Watershed (Industrial Fallback)** | **0.848 (84.8%)** | **0.464 (46.4%)** | **0.600 (60.0%)** | Zero-weight fallback. Meyer distance transform with chromatic gating. TP=84, FP=15, FN=97. |

- **Dual-Stage Botanical Gate (`cv/onion_validator.py`)**:
  1. **Deep Learning Contaminant Check**: MobileNetV3 ImageNet zero-shot rejection for non-food foreign objects (tennis balls, mugs, stones) with strict offline fallback.
  2. **Botanical Morphology & Chromatic Screening**:
     - Solidity $\ge 0.72$ (ensures convex, compact bulb shape; rejects irregular debris).
     - Aspect ratio $0.58 \le \text{AR} \le 1.70$ (rejects elongated non-bulbs like cucumbers/bananas).
     - Onion pigment fraction $\ge 0.65$ in HSV space ($H \in [0, 28] \cup [165, 180]$ for anthocyanin/quercetin red and golden tunic hues, $S \in [0.15, 0.95]$, $V \in [0.18, 0.95]$).
- **Edge Flagging**: Binary masks intersecting image frame boundaries set `touches_border = True`, classifying the bulb as physically truncated.

---

## Stage 5: Crop & Mask Extraction (`crop_extractor.py`)

For each detected onion instance:
1. **Binary Mask**: Exported as PNG to `storage/masks/{inspection_id}/{sample_id}/{idx:04d}.png`.
2. **Masked Bulb Crop**: Background masked to black, padded with 20px margin, saved as JPEG to `storage/crops/{inspection_id}/{sample_id}/{idx:04d}.jpg`.

---

## Stage 6: 4-Class Defect Classification (`defect_classifier.py`)

Visible defects are categorized using a MobileNetV3-Small neural network trained for 4-class single-label classification with Softmax output:
- $P(\text{GOOD})$: Intact, undamaged healthy onion with uniform papery tunic.
- $P(\text{DAMAGED})$: Mechanical impact damage, cuts, abrasions, bruises ($\ge 0.50$).
- $P(\text{ROTTEN})$: Visible surface decay, black mold spores (*Aspergillus niger*), or bacterial soft rot ($\ge 0.50$).
- $P(\text{SPROUTED})$: Emergent vegetative green shoots protruding from apex ($\ge 0.50$).

The argmax determines the primary prediction. Borderline defect probabilities ($0.35 \le P \le 0.65$) trigger review flags, and secondary color/semantic checks (chlorophyll hue, black mold L-channel, RAM++ produce tags) protect against dry papery neck false-positives.

---

## Stage 7: Geometric Size Estimation & Volumetric Allometry (`size_estimator.py`)

### 1. Caliper Equivalent Equatorial Diameter
$$D_{\text{eq}} = 2 \cdot \sqrt{\frac{\text{Area}_{\text{mask\_px}}}{\pi}} \cdot \text{scale\_mm\_per\_px} \quad [\text{mm}]$$

### 2. Polar Axis Length
Caliper polar dimension derived from the minor or orientation-aligned axis of the fitted bounding ellipse:
$$L_{\text{polar}} = \text{fitted\_ellipse\_minor\_axis} \cdot \text{scale\_mm\_per\_px} \quad [\text{mm}]$$

### 3. Prolate Spheroid Mass Estimation
Applying prolate spheroid solid geometry calibrated to Indian Rabi cultivars (*Allium cepa L.*):
$$V = \frac{4}{3} \pi \left(\frac{D_{\text{eq}}}{2}\right)^2 \left(\frac{L_{\text{polar}}}{2}\right) \cdot \kappa$$
$$M = V \cdot \rho$$
Where:
- $\kappa = 0.93$ (empirical bulb compactness factor accounting for neck taper and basal plate depression).
- $\rho = 0.000985\text{ g/mm}^3 \approx 0.985\text{ g/cm}^3$ (bulk biological density of cured onion tissue).

### 4. Proximity Uncertainty Flagging
If $D_{\text{eq}}$ is within $3\text{ mm}$ of any AGMARK / NAFED grading boundary ($35, 45, 65, 70\text{ mm}$), `uncertainty_flag = True` is assigned, routing the bulb to `NEEDS_REVIEW`.

---

## Stage 8: Confidence Tier Assessment & Cryptographic Sealing

Tiers are assigned independently of the procurement grade:
- **`HIGH`**: High segmentation confidence ($\ge 70\%$), not near size thresholds, non-borderline defect probabilities.
- **`NEEDS_REVIEW`**: Near size thresholds ($\pm 3\text{ mm}$), defect probabilities in borderline range ($[0.35, 0.65]$), or uncalibrated fallback scale.
- **`UNUSABLE`**: Bulb touches image frame boundary (`touches_border = True`) or segmentation confidence $< 40\%$.

### FIPS 198-1 Sovereign Cryptographic Seal
Upon finalization, the entire assaying dataset is bound into an immutable HMAC-SHA256 signature combining:
- `inspection_uuid` & `report_id`
- Physical photograph SHA-256 digest on disk
- Officer ID & timestamp
- Lot grade breakdown percentages ($A$, $URS$, $Rejected$)
Publicly verifiable via `GET /api/v1/reports/{report_id}/verify`.
