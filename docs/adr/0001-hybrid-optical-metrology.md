# ADR-0001: Hybrid Optical Metrology & Autonomous Heuristic Fallback

## Status
Accepted

## Date
2026-09-28 (Updated 2026-10-04)

## Context
In APMC mandi environments across India, onion lot intake occurs under highly variable physical conditions:
1. **Target Metrology Accuracy**: Bureau of Indian Standards (BIS) IS 17912:2022 defines size classes in increments as narrow as 10 mm (e.g., Small: 35–45 mm, Medium: 45–55 mm, Large: 55–65 mm). Planar measurement error must remain $\le 1.0\text{ mm}$ to prevent misclassification at class boundaries.
2. **Operational Realities**: While agricultural gate officers are equipped with standardized ChArUco 7x5 metric calibration cards ($140 \times 100\text{ mm}$), real-world field situations involve lost calibration cards, obscured markers, uneven lighting, or farmers uploading photos taken on village farms without fiducials.
3. **Problem**: Hard-failing when no calibration board is detected blocks mandi intake queues. Conversely, assuming an arbitrary millimeter-per-pixel scale without quantifying uncertainty constitutes metrological fabrication and creates financial dispute risks.

## Decision
We implement a **Dual-Mode Hybrid Metrological Architecture**:

1. **Certified Mode (ChArUco 7x5 Locked)**:
   - When OpenCV detects the $7 \times 5$ ChArUco board ($20\text{ mm}$ checker squares, $15\text{ mm}$ ArUco markers, `DICT_5X5_100` dictionary) with sub-pixel corner refinement (`cv2.cornerSubPix`), perspective homography is estimated:
     $$H = \arg\min_H \sum_i \| x_i' - H x_i \|^2$$
   - Pixel-to-millimeter scale is locked with **Expanded Uncertainty $U \le \pm 0.5\text{ mm}$** ($k=2$, $95\%$ confidence interval).
   - Certificate status is marked `CERTIFIED_CALIBRATED`.

2. **Autonomous Heuristic Fallback Mode (No Board Detected)**:
   - When no calibration board is detected, the engine executes perspective estimation using optical sensor field-of-view physics ($f_{\text{eq}} \approx 26\text{ mm}$, working distance $D \approx 450\text{ mm}$, standard mandi tray span $W \approx 260\text{ mm}$).
   - **Crucial Invariant**: The system **strictly forbids reporting fictitious $\pm 0.5\text{ mm}$ precision**. It enforces an expanded uncertainty of **$\pm 5.0\text{ mm}$** and programmatically tags the inspection status as:
     `NO BOARD DETECTED [NEEDS REVIEW]`
   - The UI displays an amber warning badge requiring officer manual verification before financial payout authorization.

## Consequences

### Positive
- Zero intake queue blockage on field mandi tablets even when calibration cards are misplaced.
- ISO/IEC 17025 metrology compliance: uncertainty bounds are mathematically sound and truthful.
- Transparent audit trail for APMC and NAFED grievance tribunals.

### Negative / Trade-offs
- Lots graded under heuristic fallback require physical manual spot-checks prior to buffer stock procurement payout.
