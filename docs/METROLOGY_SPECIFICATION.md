# CEPA Optical Metrology Specification & Uncertainty Budget

> **Metrology Framework**: ISO/IEC Guide 98-3 (GUM: Evaluation of Measurement Data) Analytical Uncertainty Model  
> **Target Commodity**: *Allium cepa* L. (Rabi / Kharif Commercial Onion Cultivars)  
> **Regulatory Reference**: Bureau of Indian Standards (BIS) **IS 17912:2022**

---

## 1. Mathematical Formulation of Optical Measurement

### 1.1 Pinhole Camera Geometry & Perspective Homography
A physical world point on the inspection tray $\mathbf{P}_w = [X_w, Y_w, Z_w, 1]^T$ in homogenous coordinates projects onto the camera sensor image plane $\mathbf{p} = [u, v, 1]^T$ via the camera projection matrix $\mathbf{M}$:

$$\mathbf{p} \sim \mathbf{K} [\mathbf{R} \mid \mathbf{t}] \mathbf{P}_w$$

Where $\mathbf{K}$ is the intrinsic camera calibration matrix:

$$\mathbf{K} = \begin{bmatrix} f_x & 0 & c_x \\ 0 & f_y & c_y \\ 0 & 0 & 1 \end{bmatrix}$$

For planar inspection trays ($Z_w = 0$), the transformation reduces to a $3 \times 3$ projective homography matrix $\mathbf{H}$:

$$\begin{bmatrix} u \\ v \\ 1 \end{bmatrix} = \mathbf{H} \begin{bmatrix} X_w \\ Y_w \\ 1 \end{bmatrix} = \begin{bmatrix} h_{11} & h_{12} & h_{13} \\ h_{21} & h_{22} & h_{23} \\ h_{31} & h_{32} & h_{33} \end{bmatrix} \begin{bmatrix} X_w \\ Y_w \\ 1 \end{bmatrix}$$

### 1.2 Lens Distortion Modeling (Brown-Conrady Formulation)
Radial and tangential distortions are modeled to eliminate optical barrel and pincushion aberrations common in mobile camera wide-angle lenses:

$$x_{\text{distorted}} = x (1 + k_1 r^2 + k_2 r^4 + k_3 r^6) + [2 p_1 x y + p_2 (r^2 + 2 x^2)]$$
$$y_{\text{distorted}} = y (1 + k_1 r^2 + k_2 r^4 + k_3 r^6) + [p_1 (r^2 + 2 y^2) + 2 p_2 x y]$$

Where $r^2 = x^2 + y^2$, $k_1, k_2, k_3$ are radial distortion coefficients, and $p_1, p_2$ are tangential distortion coefficients.

### 1.3 ChArUco 7×5 Sub-Pixel Corner Refinement
The system employs a standardized ChArUco board ($7 \times 5$ grid, $20\text{ mm}$ square length, $15\text{ mm}$ marker length, `DICT_5X5_100`). Detected corner coordinates $\mathbf{c}_i$ are iteratively refined to sub-pixel accuracy using the orthogonal gradient dot-product constraint:

$$\sum_{p \in \mathcal{N}} \nabla I(p) \cdot (p - \mathbf{c}_i) = 0$$

Refinement operates with stopping criteria of $\epsilon = 0.001\text{ px}$ or maximum 30 iterations, providing sub-pixel corner repeatability $\sigma_{\text{corner}} \le 0.08\text{ px}$.

---

## 2. ISO/IEC Guide 98-3 (GUM) Measurement Uncertainty Budget

The measurement of bulb equatorial diameter $d_{\text{eq}}$ (in millimeters) is expressed as:

$$d_{\text{eq}} = s_{\text{optical}} \cdot d_{\text{px}} + \delta_{\text{parallax}} + \delta_{\text{segmentation}} + \delta_{\text{printing}}$$

Where:
- $s_{\text{optical}}$: Derived scale factor ($\text{mm/pixel}$) from the homography $\mathbf{H}$.
- $d_{\text{px}}$: Major axis length of the fitted bounding ellipse or minimum enclosing circle (pixels).
- $\delta_{\text{parallax}}$: Parallax error arising from 3D bulb curvature relative to the planar board ($Z \approx 25\text{–}40\text{ mm}$ above tray plane).
- $\delta_{\text{segmentation}}$: Instance boundary uncertainty along the outer dry tunic scales.
- $\delta_{\text{printing}}$: Physical manufacturing tolerance of the ChArUco card.

### 2.1 Uncertainty Budget Table (Certified ChArUco Locked Mode)

| Uncertainty Component $x_i$ | Source of Evaluation | Standard Uncertainty $u(x_i)$ | Sensitivity Coeff. $c_i$ | Contribution $u_i(y)$ |
| :--- | :--- | :--- | :--- | :--- |
| **Sub-pixel Corner Repeatability** | Type A ($n=30$ frames) | $0.08\text{ px}$ | $s \approx 0.18\text{ mm/px}$ | $0.014\text{ mm}$ |
| **Board Printing Tolerance** | Type B (laser calibration) | $0.05\text{ mm} / \sqrt{3}$ | $1.0$ | $0.029\text{ mm}$ |
| **Lens Distortion Residual** | Type B (uncalibrated fringe) | $0.12\text{ mm} / \sqrt{3}$ | $1.0$ | $0.069\text{ mm}$ |
| **Instance Boundary Jitter** | Type A ($5\times$ IoU runs) | $0.85\text{ px}$ | $s \approx 0.18\text{ mm/px}$ | $0.153\text{ mm}$ |
| **3D Bulb Parallax ($< 25^\circ$ tilt)** | Type B (triangulation) | $0.32\text{ mm} / \sqrt{3}$ | $1.0$ | $0.185\text{ mm}$ |

### 2.2 Combined & Expanded Uncertainty
The combined standard uncertainty $u_c(d_{\text{eq}})$ is computed via root sum-of-squares:

$$u_c = \sqrt{\sum_{i=1}^N u_i^2(y)} = \sqrt{0.014^2 + 0.029^2 + 0.069^2 + 0.153^2 + 0.185^2} \approx 0.251\text{ mm}$$

Applying a coverage factor $k = 2$ (representing a **95.45% confidence interval** under a Gaussian error distribution):

$$U = k \cdot u_c = 2 \times 0.251\text{ mm} \approx \pm 0.50\text{ mm}$$

$$\mathbf{U_{\text{certified}} = \pm 0.5\text{ mm} \quad (\text{ChArUco Locked Mode})}$$

---

## 3. Autonomous Heuristic Uncertainty (No Board Mode)

When no ChArUco board is present, working distance $D$ is inferred from optical field-of-view physics with estimated variance $\sigma_D \approx \pm 45\text{ mm}$.

Propagating distance uncertainty:

$$u(s) = \frac{\partial s}{\partial D} u(D) \approx \frac{s}{D} u(D)$$

This yields a combined uncertainty $u_c \approx 2.45\text{ mm}$. With coverage factor $k = 2$:

$$\mathbf{U_{\text{heuristic}} = \pm 5.0\text{ mm} \quad (\text{Flagged: NEEDS\_REVIEW})}$$

The system mathematically forbids reporting sub-millimeter precision under uncalibrated conditions, preserving metrological integrity.
