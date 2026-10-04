# CEPA End-to-End System Architecture & Metrology Pipeline

This document provides the canonical architectural specification for **CEPA (Certified and Evidenced Produce Assessment)**, a high-throughput, autonomous computer vision and digital assaying platform engineered for APMC mandi intake gates, cold storages, and national strategic onion buffer procurement operations.

---

## 1. High-Level Component Topology

CEPA decouples sensor telemetry, optical computer vision, statutory grading policies, cryptographic audit chains, and farmer settlement into a modular, production-hardened topology:

```
+--------------------------------------------------------------------------------------------------------+
|                                  FIELD OPERATIONAL TIER (EDGE CLIENTS)                                  |
|                                                                                                        |
|   +------------------------------------+             +---------------------------------------------+   |
|   |    React Native / Expo Mobile      |             |    Forensic Mandi Inspector Web Console     |   |
|   |    - Offline HUD & Guidance Box    |             |    - High-Resolution Staging Canvas         |   |
|   |    - Real-Time Camera Telemetry    |             |    - Sub-Pixel Mask Inspection & Polygons   |   |
|   |    - Instant Bluetooth/LAN Sync    |             |    - One-Click APMC eNAM Clearance Export   |   |
|   +-----------------+------------------+             +----------------------+----------------------+   |
+---------------------|-------------------------------------------------------|--------------------------+
                      |                                                       |
                      | HTTP/REST + TLS 1.3 (Scoped Officer API Key)          |
                      v                                                       v
+--------------------------------------------------------------------------------------------------------+
|                                    APPLICATION ENGINE (FASTAPI ASYNC)                                   |
|                                                                                                        |
|   +------------------------------------------------------------------------------------------------+   |
|   |                                     FastAPI Router Gateway                                     |   |
|   |      /inspections      /reports      /enam      /calibration      /acoustic      /health       |   |
|   +-------------------+--------------------+--------------------+--------------------+-------------+   |
|                       |                    |                    |                    |                 |
|                       v                    v                    v                    v                 |
|   +------------------------------------+  +------------------------------------+  +----------------+   |
|   |      8-Stage CV & ML Pipeline      |  |     Grading & Policy Engine        |  | FIPS 198-1     |   |
|   |   - Quality Gate & Blur Reject     |  |  - BIS IS 17912:2022 Grades        |  | Sovereign Seal |   |
|   |   - Planar Homography (ChArUco)    |  |  - NAFED PSF Fair Average Quality  |  | - HMAC-SHA256  |   |
|   |   - CIELAB Anthocyanin Filter      |  |  - Decoupled YAML Rule Engine      |  | - Raw Hash Bind|   |
|   |   - Prolate Spheroid Metrology     |  |  - Dynamic Dockage Deduction       |  | - Tamper Guard |   |
|   +-------------------+----------------+  +-----------------+------------------+  +--------+-------+   |
|                       |                                     |                              |           |
|                       +------------------+   +--------------+                              |           |
|                                          |   |                                             |           |
|                                          v   v                                             v           |
|   +------------------------------------------------------------------------------------------------+   |
|   |                       Embedded Persistence & Forensic Asset Storage Layer                      |   |
|   |   - SQLite 3.45+ with Write-Ahead Logging (WAL) & 5000ms Busy Timeout                          |   |
|   |   - Content-Addressed Local Filesystem Storage (/storage/images, /crops, /masks, /reports)     |   |
|   +------------------------------------------------------------------------------------------------+   |
+--------------------------------------------------------------------------------------------------------+
                                                    |
                                                    v
+--------------------------------------------------------------------------------------------------------+
|                               DIGITAL PUBLIC INFRASTRUCTURE (DPI) EGRESS                               |
|                                                                                                        |
|   +----------------------------------------+         +---------------------------------------------+   |
|   |          eNAM XML Gateway v2.1         |         |             AgriStack Farmer Registry       |   |
|   |   - Standardized Lot Assaying Payload  |         |   - 12-Digit Farmer ID Verification (FID)   |   |
|   |   - Electronic Warehouse Receipt (eNWR)|         |   - Geo-Referenced Land Record Binding      |   |
|   +----------------------------------------+         +---------------------------------------------+   |
+--------------------------------------------------------------------------------------------------------+
```

---

## 2. The 8-Stage Computer Vision & Metrology Pipeline

Every photographic frame captured at the intake station passes through a strictly validated sequence of algorithmic gates:

```
[Input Camera Capture]
          |
          v
[Stage 1: Pre-Flight Optical Quality Gate]
  - Resolution Check: >= 1280 x 720 px
  - Laplacian Variance: >= 80.0 (Motion blur rejection)
  - Mean Luminance: 40.0 <= Y <= 230.0 (Under/over-exposure protection)
  - Specular Highlight Fraction: <= 12% (Overhead glare rejection)
          | (Passed)
          v
[Stage 2: Metric Ground Plane Calibration]
  - ChArUco 7x5 Board Detection (cv2.aruco.DICT_5X5_100)
  - Sub-pixel corner refinement (5x5 search window, EPS+COUNT)
  - Homography Matrix H solved via RANSAC (reprojection error < 5.0 px)
  - Metric resolution: S_x, S_y (mm/pixel) with uncertainty U <= +/- 0.5 mm
  - Fallback State: Fixed field of view heuristic with mandatory degradation flag
          |
          v
[Stage 3: Botanical Morphology & Pigment Validation Gate]
  - CIELAB Anthocyanin Protection Barrier (A* >= 136 thresholding)
  - Morphological Eccentricity (0.45 <= L/D <= 1.45) & Circularity (>= 0.60)
  - Reject apples, potatoes, stones, and non-allium contaminants
          |
          v
[Stage 4: Instance Segmentation & Geometric Boundary Extraction]
  - YOLO11n-seg deep neural network inference (PyTorch CPU / ONNX runtime)
  - Direct polygon contour extraction from mask manifold
  - Boundary collision filter (discards incomplete edge-clipped bulbs)
          |
          v
[Stage 5: Prolate Spheroid Metrology & Physical Compactness]
  - Equatorial Caliper Diameter: D_caliper (mm)
  - Polar Axis Length: L_polar (mm)
  - Compactness correction: kappa = 0.93 (Allium cepa packing ratio)
  - Volumetric mass prediction: m = kappa * (pi/6) * L_polar * D_caliper^2 * rho
          |
          v
[Stage 6: Multi-Spectral & Surface Defect Classification]
  - CIELAB Necrotic Rot Segmentation (L* < 38, A* < 136)
  - Sprout Apex Vector Analysis (green shoot emergence detection)
  - Mechanical Damage & Surface Bruising Identification
          |
          v
[Stage 7: Procurement Policy Engine & Commercial Dockage Calculation]
  - Dynamic YAML Rule Resolution (BIS IS 17912:2022 vs NAFED FAQ)
  - Sizing Distribution: Small (<45mm), Medium (45-65mm), Large (>65mm)
  - Cumulative dockage calculation and fair payout determination
          |
          v
[Stage 8: Sovereign Cryptographic Sealing & DPI Egress]
  - SHA-256 Hash Computation over pristine raw input JPEG bytes
  - Canonical JSON payload serialization
  - FIPS 198-1 HMAC-SHA256 signature generation with isolated master key
  - Immutable database commit, PDF/A assaying certificate, and eNAM v2.1 XML output
```

---

## 3. Cryptographic Sovereign Seal Protocol

To guarantee that assaying certificates generated at rural mandis cannot be tampered with or modified post-hoc:

### 3.1 Mathematical Formulation
$$\mathcal{S} = \text{HMAC-SHA256}_{K_{\text{seal}}}\left( \mathcal{H}_{\text{photo}} \parallel \text{UUID}_{\text{insp}} \parallel G \parallel D_{\text{pct}} \parallel W_{\text{kg}} \parallel \text{FID} \parallel T \right)$$

Where:
- $K_{\text{seal}}$: High-entropy cryptographic master secret provisioned via secure environment variable.
- $\mathcal{H}_{\text{photo}}$: Full SHA-256 digest of pristine source imagery.
- $\text{UUID}_{\text{insp}}$: Canonical inspection identifier.
- $G$: Certified quality grade (`GRADE_A`, `GRADE_B`, `GRADE_C`, `REJECTED`).
- $D_{\text{pct}}$: Total assessed commercial dockage percentage.
- $W_{\text{kg}}$: Gross weight in kilograms.
- $\text{FID}$: 12-digit farmer identifier.
- $T$: ISO-8601 UTC timestamp of inspection finalization.

### 3.2 Offline Mandi Validation
Any third party (APMC registrar, bank lending against electronic Warehouse Receipts, or farmer) can independently audit certificate authenticity by executing:
```bash
python -m backend.cli verify-seal --report-id <REPORT_UUID>
```
The verification algorithm executes constant-time byte comparison (`hmac.compare_digest`) to prevent timing side-channel attacks.

---

## 4. Concurrency & Offline Mandi Failover

Mandi yards frequently experience intermittent power, zero 4G connectivity, and sudden disconnections:

1. **Embedded SQLite WAL Engine:** SQLite running in Write-Ahead Log mode enables simultaneous read operations during batch writes, avoiding locking contention during rapid sampling.
2. **Deterministic Fallback Degradation:** If the metric ChArUco target is physically obscured by spilled onion skins, the system does not crash or abort; it transitions gracefully to conservative optical heuristics and permanently flags the certificate with `CALIBRATION_UNVERIFIED_DEGRADED` for human review.
3. **Stateless Edge Architecture:** All heavy neural inference runs locally on standard x86 or ARM CPU cores using PyTorch and OpenCV without requiring cloud GPU round-trips.
