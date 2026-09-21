# Cepa Computer Vision Pipeline (8-Stage Specification)

This document provides a technical walkthrough of the 8-stage image processing and computer vision pipeline implemented in `backend/cv/`.

---

## Stage 1: Image Quality Gate (`quality_gate.py`)

Every image must pass automated quality gates before entering ML inference. If any gate fails, processing stops and returns an actionable instruction to the officer.

| Metric | Target / Normal | Failure Code | Remedy Instruction |
|---|---|---|---|
| **Resolution** | Min dimension $\ge 1000\text{ px}$ | `insufficient_resolution` | Retake photo with high-res camera setting at 50–80 cm height. |
| **Blur** | Laplacian variance $\ge 80.0$ | `image_too_blurry` | Hold phone steady, allow autofocus to lock before snapping. |
| **Underexposure** | Grayscale mean lum $\ge 40$ | `too_dark` | Move to better lighting or activate camera flash. |
| **Overexposure** | Grayscale mean lum $\le 215$ | `too_bright` | Shield spread from harsh direct midday sunlight. |
| **Specular Glare** | Fraction of $(R,G,B > 250) \le 5\%$ | `excessive_glare` | Reposition light source or change camera angle slightly. |

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
5. **Sanity Validation**:
   $$0.05 \le \text{scale\_mm\_per\_px} \le 5.0$$
   If the scale lies outside this interval, `scale_unreliable` is triggered.

---

## Stage 4: Instance Segmentation (`providers/yolo11_provider.py`)

- **Model**: YOLO11s-seg / YOLO11n-seg.
- **Occlusion Handling**: Cross-Stage Partial with Spatial Attention (C2PSA) blocks distinguish individual bulbs in dense clusters.
- **Edge Flagging**: Any binary mask touching the image boundary sets `touches_border = True`, signifying that the bulb is truncated.

---

## Stage 5: Crop & Mask Extraction (`crop_extractor.py`)

For each detected onion instance:
1. **Binary Mask**: Exported as PNG to `storage/masks/{inspection_id}/{sample_id}/{idx:04d}.png`.
2. **Masked Bulb Crop**: Background masked to black, padded with 20px margin, saved as JPEG to `storage/crops/{inspection_id}/{sample_id}/{idx:04d}.jpg`.

---

## Stage 6: Multi-Label Defect Classification (`defect_classifier.py`)

Defects are treated as independent binary probabilities (Sigmoid activation, not Softmax):
- $P(\text{damaged})$: Visible cuts, abrasions, bruising.
- $P(\text{rotten})$: Visible surface decay, mold, black mold spores.
- $P(\text{sprouted})$: Protruding green shoots or emerged vegetative tips.

---

## Stage 7: Geometric Size Estimation (`size_estimator.py`)

### Primary Size Metric: Equivalent Diameter
$$D_{\text{eq}} = 2 \cdot \sqrt{\frac{\text{Area}_{\text{mask\_px}}}{\pi}} \cdot \text{scale\_mm\_per\_px} \quad [\text{mm}]$$

- **Why Equivalent Diameter?**
  1. Equatorial major-axis length is sensitive to bulb rotation and orientation on the table.
  2. Equivalent circular diameter from the 2D projected mask area is rotation-invariant.
  3. Closely aligns with circular mechanical sizing rings used in mandis.

### Proximity Uncertainty Flagging
If $D_{\text{eq}}$ is within $3\text{ mm}$ of any policy threshold ($35, 45, 65, 70\text{ mm}$), `uncertainty_flag = True` is assigned, routing the bulb to `NEEDS_REVIEW`.

---

## Stage 8: Confidence Tier Assessment (`confidence.py`)

Tiers are assigned independently of the procurement grade:
- **`HIGH`**: High segmentation confidence ($\ge 70\%$), not near size thresholds, non-borderline defect probabilities.
- **`NEEDS_REVIEW`**: Near size thresholds ($\pm 3\text{ mm}$), defect probabilities in borderline range ($[0.35, 0.65]$), or missing scale calibration.
- **`UNUSABLE`**: Bulb touches image frame boundary (`touches_border = True`) or segmentation confidence $< 40\%$.
