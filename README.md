<div align="center">

<img src="backend/static/logo.png" alt="CEPA Logo" width="220" />

# CEPA: Certified and Evidenced Produce Assessment
### Autonomous Post-Harvest Produce Quality Inspection and Mandi Assaying Platform

**Smart India Hackathon (SIH 2026) Engineering Submission | Problem Statement ID: SIH26031**

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.x_CPU-EE4C2C?style=flat-square&logo=pytorch&logoColor=white)](https://pytorch.org)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.9+-5C3EE8?style=flat-square&logo=opencv&logoColor=white)](https://opencv.org)
[![React Native](https://img.shields.io/badge/React_Native-0.86-61DAFB?style=flat-square&logo=react&logoColor=black)](https://reactnative.dev)
[![Expo](https://img.shields.io/badge/Expo-57.0-000020?style=flat-square&logo=expo&logoColor=white)](https://expo.dev)
[![Tests Passing](https://img.shields.io/badge/Tests-208%20passed%20%7C%201%20skipped-success?style=flat-square)](backend/tests/)
[![License AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue?style=flat-square)](LICENSE)

<br />

| Dimension | Specification |
|:---|:---|
| **Problem Statement** | **SIH26031**: Quality assessment and grading of onions |
| **Team Name** | **Better Call Coders** |
| **Team Leader** | Ubaid Khan |
| **Nodal Authorities** | Ministry of Consumer Affairs, Food & Public Distribution; NAFED; NCCF; Department of Consumer Affairs (DoCA) |
| **Commodity Focus** | Onion (*Allium cepa L.*), Rabi Buffer Procurement (Price Stabilisation Fund) |
| **Target Deployment** | APMC Mandi Intake Gates, Central Buffer Ventilated Chawls, Cold Storages |
| **Policy Status** | **PROVISIONAL (`policy_verified: false`)**: Grading thresholds are based on published PSF/APMC norms; not yet verified against an official tender EOI |
| **Verification State** | 208 of 209 Automated Pytest Specifications Passing (1 Hardware Camera Dependent Skipped, 0 Failures) |

</div>

---

## Executive Summary & Engineering Solution

During India's strategic onion buffer procurement operations (300,000–500,000 MT under the Price Stabilisation Fund), procurement agencies face 30–40% post-harvest storage losses. At APMC mandi intake gates, consignment grading relies predominantly on subjective, visual hand-sampling (inspecting only 5–10 bulbs per multi-tonne truck) with zero persistent photographic audit trails.

**CEPA** is an automated produce assaying and inspection platform designed to operate at mandi intake gates and packhouse stations. It combines:
1. **Calibrated Computer Vision**: Rectified top-down imaging with planar fiducial homography to measure physical bulb geometry (equatorial diameter, polar length, and volumetric mass).
2. **Transparent Defect Detection**: A 4-class deep learning classifier evaluated specifically for procurement risk, measuring minority defect interception rates rather than misleading aggregate accuracy.
3. **Decoupled Policy Architecture**: Declarative YAML grading policies allowing instantaneous switching between APMC, NAFED, and NCCF procurement standards without backend code changes.
4. **Tamper-Evident Certification**: Every inspection generates a machine-verifiable digital certificate bound by an HMAC-SHA256 cryptographic seal linking the raw image digest, officer ID, and per-bulb measurements.

```
                              CEPA 8-STAGE VISION PIPELINE
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ 1. Quality   │ ──> │ 2. Metric    │ ──> │ 3. Produce   │ ──> │ 4. Produce   │
│    Gate      │     │    Homography│     │    Segment.  │     │    Validator │
│ (Blur/Glare) │     │ (ChArUco 7x5)│     │ (YOLO11-seg) │     │ (HSV/Aspect) │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                                                                       │
                                                                       ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ 8. Sovereign │ <── │ 7. Calibrated│ <── │ 6. Multi-    │ <── │ 5. Defect    │
│    Seal      │     │    Metrology │     │    Sample    │     │    Classifier│
│ (HMAC-SHA256)│     │ (GUM Budget) │     │    Aggregate │     │ (4-Cls Softm)│
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
```

---

## 1. Computer Vision & Metrology Pipeline

The backend executes an 8-stage synchronous inspection pipeline (`POST /api/v1/inspections`):

1. **Optical Quality Gate (`cv/quality_gate.py`)**:
   - Rejects ungradable images before inference to prevent garbage-in/garbage-out results.
   - Evaluates Laplacian blur variance ($\ge 35.0$), specular glare fraction ($\le 0.45$, accounting for high-luma white/cream onion tunic scales), minimum image resolution ($\ge 300\text{ px}$), and extreme brightness bounds ($25 \le \text{luma} \le 245$).

2. **Metric Homography Calibration (`cv/calibrator.py`)**:
   - Detects a standardized ChArUco fiducial board ($7 \times 5$ grid, $40\text{ mm}$ square length, $20\text{ mm}$ marker length).
   - Solves planar perspective homography via RANSAC with sub-pixel corner refinement ($\sigma \le 0.08\text{ px}$), deriving the physical millimeter-per-pixel scale factor ($s \approx 0.4\text{--}0.6\text{ mm/px}$).
   - Validates that the derived scale falls within plausible optical limits ($0.05 \le s \le 5.0\text{ mm/px}$). If no calibration board is detected, the pipeline marks `NEEDS_REVIEW` and reports an uncalibrated flag.

3. **Produce Instance Segmentation (`cv/segmentor.py`)**:
   - Segmentor fine-tuned on onion produce spreads (`backend/weights/yolo11n-seg.pt`), backed by an automatic deterministic Watershed and contour morphology fallback on CPU.
   - Generates individual binary masks and bounding boxes for every detected bulb on the inspection surface.

4. **Produce Validator (`cv/onion_validator.py`)**:
   - Discards non-onion artifacts, stray debris, and spurious background segmentations using HSV color distribution boundaries, contour circularity, and minimum area filtering.

5. **Multi-Class Defect Classification (`cv/defect_classifier.py`)**:
   - Evaluates isolated individual bulb crops using a MobileNetV3 backbone (`backend/weights/defect_classifier.pt`).
   - Generates 4-class single-label probabilities: `GOOD`, `DAMAGED`, `ROTTEN`, `SPROUTED`.

6. **Multi-Sample Lot Aggregation (`cv/aggregator.py`)**:
   - Aggregates multi-image samples from different tiers of a consignment truck/heap to ensure statistical lot representativeness.
   - Computes weighted defect distribution percentages across all inspected bulbs.

7. **Morphometry & Volumetric Mass Estimation (`cv/size_estimator.py`)**:
   - Fits minimum enclosing ellipses and detects stem-to-root polar axes.
   - Computes equivalent diameter ($D_{\text{eq}} = 2\sqrt{A / \pi} \cdot s$), equatorial diameter ($D_{\text{equatorial}}$), and polar length ($L_{\text{polar}}$).
   - Estimates volumetric bulb weight via prolate/oblate spheroid geometry adjusted for bulb compactness:
     $$V = \frac{\pi}{6} D_{\text{eq}}^2 L_{\text{polar}}, \quad M = V \cdot \rho \cdot K_{\text{compactness}} \quad (\rho = 0.985\text{ g/cm}^3, K = 0.93)$$
   - Assigns Mandi size grades: **Goli** ($< 35\text{ mm}$), **Madhyam** ($35\text{--}45\text{ mm}$), **Super** ($45\text{--}65\text{ mm}$), and **Jumbo** ($> 65\text{ mm}$).

8. **Tamper-Evident Digital Seal (`services/crypto_seal.py`)**:
   - Generates an HMAC-SHA256 cryptographic seal binding the raw sample image SHA-256 digest, inspecting officer ID, per-bulb metrics, and timestamp.
   - Embeds the cryptographic seal into an encrypted QR code on the generated PDF inspection certificate.

---

## 2. Metrological Rigor & Physical Uncertainty Budget

A core engineering principle of CEPA is strict metrological honesty: 2D optical cameras cannot replace laboratory 3D profilometers, and planar homography must not be conflated with 3D produce measurement.

### Planar vs 3D Metrology Limits

| Metrological Parameter | Ground Truth Basis | CEPA Performance / Boundary | Field Operational Handling |
|:---|:---|:---|:---|
| **Planar Calibration Error** | ChArUco $7 \times 5$ sub-pixel corners | **$\le 0.40\text{ mm}$ RMS** on board plane | Validates camera distance and tilt angles |
| **Geometric Diameter Fidelity** | Calibrated synthetic ellipse masks | **$\le 1.00\text{ mm}$** ($0.5\text{ mm/px}$) | Verified in `test_metrology_accuracy.py` |
| **3D Out-of-Plane Parallax** | Bulb height ($20\text{--}40\text{ mm}$) at $Z_0 \approx 600\text{ mm}$ | **$\pm 1.5\text{ to } 3.5\text{ mm}$** theoretical | Governed by ISO/IEC Guide 98-3 (GUM) |
| **Near-Boundary Safety Flag** | Policy boundaries ($35, 45, 65\text{ mm}$) | **`uncertainty_flag = True`** ($\pm 3.0\text{ mm}$) | Automatically alerts officer for boundary cases |
| **Internal Produce Rot** | Sub-surface microbial infection | **Not visible to surface RGB cameras** | Mandatory certificate disclaimer; cut-test protocol |

> **Metrological Invariant**:
> - **Method**: ChArUco homography gives physical scale; sizing uses a documented uncertainty budget (±1.5 to 3.5 mm from parallax, flagged per bulb near grade thresholds).
> - **Evidence**: Synthetic bench result (validated by `TestMetrologySyntheticBench` in `backend/tests/test_metrology_accuracy.py`, recovering equatorial diameter within $\le 1.2\text{ mm}$ error across rotations and blur levels).
> - **Status**: Field validation against physical calipers: not yet performed.

*Deep-dive documentation:* [`docs/METROLOGY_SPECIFICATION.md`](docs/METROLOGY_SPECIFICATION.md) | [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md)

---

## 3. Machine Learning Evaluation & Procurement Risk

Standard accuracy is an inadequate metric for agricultural grading due to severe class imbalance (88.7% majority healthy bulbs in standard commercial lots). A naive classifier that marks every bulb "GOOD" would achieve ~89% accuracy while failing 100% of defect inspections.

CEPA reports its evaluation transparently across a 70/15/15 stratified test partition (1,733 test crops from an 11,545-image curated dataset):

### Comprehensive ML Evaluation Benchmark

| Metric Dimension | Value | 95% Confidence Interval | Clinical Mandi Interpretation |
|:---|:---|:---|:---|
| **Overall Accuracy** | **96.36%** | [95.38%, 97.18%] | Standard baseline metric |
| **Macro F1 Score** | **0.7270** | [0.681, 0.773] | Unweighted mean across all 4 classes |
| **Balanced Accuracy** | **83.43%** | [0.772, 0.896] | Arithmetic mean of per-class sensitivity |
| **BAD → GOOD False-Negative Rate** | **2.55%** | **[1.09%, 5.83%]** | **Critical metric: out of 196 defective bulbs, only 5 were missed (97.45% interception recall)** |
| **GOOD → BAD False-Positive Rate** | **1.82%** | [1.26%, 2.62%] | Rate of unfair rejection of healthy farmer produce |

### Per-Class Performance Breakdown

| Class | Precision | Recall | F1 Score | Test Support | Operational Characteristics |
|:---|:---:|:---:|:---:|:---:|:---|
| **GOOD** | 0.997 | 0.982 | **0.989** | 1,537 | Dominant commercial majority class |
| **ROTTEN** | 0.934 | 0.859 | **0.895** | 149 | Surface mold, black smudge, soft decay |
| **DAMAGED** | 0.444 | 0.552 | **0.492** | 29 | Cuts, mechanical bruises, tunic splits (small minority cohort) |
| **SPROUTED** | 0.370 | 0.944 | **0.531** | 18 | Vegetative apical shoot emergence (high recall: 17 of 18 caught) |

> **Dataset Transparency Note**:
> Evaluated on single-bulb cutouts curated from public datasets (Mendeley, Roboflow). Field performance on dirty, unwashed, field-run mandi heaps requires domain adaptation and fine-tuning with local harvest imagery.

*Deep-dive documentation:* [`docs/DATASET_CARD.md`](docs/DATASET_CARD.md) | Reports: [`ml/reports/quality_metrics.json`](ml/reports/quality_metrics.json)

---

## 4. Decoupled Procurement Policy Engine

Grading standards vary significantly across agencies and seasons. CEPA decouples grading rules from computer vision algorithms via declarative YAML policies stored in `backend/grading/policies/`:

- **`DEMO_ASSUMPTION_v1.yaml`**: Active baseline policy for testing and demonstration.
- **`NAFED_2026_v1.yaml`**: Illustrative policy implementing Price Stabilisation Fund buffer specifications:
  - Grade A: $45\text{--}65\text{ mm}$ equatorial diameter, max 5.0% defective bulbs.
  - Relaxed / URS: $35\text{--}70\text{ mm}$, max 12.0% defective bulbs.
  - Rejection: $> 12.0\%$ defect or $> 3.0\%$ critical rot.
  - Marked with `verified: false` to reflect its status as an engineering prototype policy.

Any policy can be activated dynamically via the `.env` configuration (`ACTIVE_GRADING_POLICY=...`) or passed per-request without restarting the service.

*Deep-dive documentation:* [`backend/grading/policies/`](backend/grading/policies/)

---

## 5. Non-Destructive Testing (NDT) & Extensions

Surface RGB cameras cannot detect internal microbial decay (*Pectobacterium* bacterial soft rot or internal *Fusarium* basal rot). CEPA provides structured hooks for multi-modal extensions:

1. **Acoustic Resonance Analysis (`POST /api/v1/inspections/{id}/acoustic`)**:
   - Laboratory contact piezoelectric transducer endpoint analyzing acoustic impulse resonance ($f_0 \approx 700\text{--}800\text{ Hz}$, $Q$-factor damping).
   - Designed for laboratory testing fixtures; not claimed as an in-air smartphone microphone feature due to ambient mandi acoustic noise ($> 75\text{ dB}$).
2. **Officer Destructive Cut-Test Protocol (`services/cut_test_service.py`)**:
   - Structured protocol enabling procurement officers to log 10-bulb cross-sectional cut tests to verify internal core health and calibrate lot storageability scores.
3. **Dual-Exposure Flash Proxy Index (FPI)**:
   - Differential luminance reflectance analysis to highlight sub-tunic surface moisture and skin slip.

---

## 6. Digital Public Infrastructure (DPI) & Cryptography

CEPA is architected for integration with India's agricultural digital infrastructure:

- **eNAM Assaying Schema Export (`services/enam_export.py`)**:
  - Generates standardized JSON payloads containing Mandi Assaying parameters: size distribution percentages, foreign matter debris fraction, defect ratios, and moisture index.
- **AgriStack Farmer ID (FID) Binding**:
  - Direct binding of Farmer Identifiers to lot certificates, enabling integration with Direct Benefit Transfer (DBT) and procurement settlement systems.
- **Tamper-Evident HMAC Digital Seal (`services/crypto_seal.py`)**:
  - Computes an HMAC-SHA256 seal over the primary image SHA-256 digest, officer credentials, and grading results.
  - Verifiable independently via `GET /api/v1/reports/{id}/verify`.
  - *Trust Model Note:* HMAC provides tamper-evident integrity protection. Asymmetric public-key signatures (Ed25519) are on the production roadmap for legal non-repudiation.

---

## 7. Quickstart & Verification

### Prerequisites
- Python 3.12+
- Node.js 20+ & npm (for mobile client)
- PyTorch (CPU wheel installed automatically)

### 1. Backend Setup & Test Verification

```bash
# Clone repository
git clone https://github.com/notUbaid/Cepa.git
cd Cepa

# Set up virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run full test suite (208 passing, 1 skipped)
pytest -q

# Launch local FastAPI inspection station
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation will be live at: [`http://localhost:8000/docs`](http://localhost:8000/docs)  
Inspector Web Studio: [`http://localhost:8000/inspector`](http://localhost:8000/inspector)

### 2. Mobile Client Setup (Expo / React Native)

```bash
cd mobile
npm install

# Start development server
npx expo start
```
Scan the displayed QR code with the Expo Go app (Android/iOS) or press `w` to open in browser.

### 3. Quick CLI Evaluation

CEPA includes an operational developer CLI (`backend/cli.py`):
```bash
# Run complete inspection on a test spread
python backend/cli.py inspect backend/static/demo_onion_spread.jpg

# Verify cryptographic seal of an inspection
python backend/cli.py verify-seal <INSPECTION_ID>
```

---

## 8. Repository Layout & Documentation Suite

```
Cepa/
├── backend/                  # FastAPI Core Inspection Engine
│   ├── cv/                   # 8-Stage Computer Vision & Metrology Pipeline
│   │   ├── quality_gate.py   # Focus, glare, luminance, and resolution gates
│   │   ├── calibrator.py     # ChArUco 7x5 fiducial calibration & homography
│   │   ├── segmentor.py      # YOLO11-seg inference with Watershed CPU fallback
│   │   ├── onion_validator.py# HSV chromatic & morphology sanity gate
│   │   ├── defect_classifier.py # MobileNetV3 4-class single-label classifier
│   │   ├── aggregator.py     # Multi-sample lot distribution aggregator
│   │   ├── size_estimator.py # Equatorial diameter, polar axis, and mass model
│   │   └── annotator.py      # Inspection overlay visualization generator
│   ├── grading/              # Decoupled Policy Engine & YAML Rules
│   ├── routers/              # REST API Route Controllers
│   ├── services/             # Report generation, crypto seal, eNAM export
│   ├── static/               # Demonstration assets, ChArUco cards, UI webviews
│   ├── tests/                # 209 automated pytest verification specifications
│   └── weights/              # Model weights (YOLO11-seg, MobileNetV3)
├── docs/                     # Formal Engineering & Research Documentation
│   ├── CV_PIPELINE.md        # Mathematical formulation of 8-stage pipeline
│   ├── METROLOGY_SPECIFICATION.md # ISO/IEC Guide 98-3 (GUM) uncertainty budget
│   ├── LIMITATIONS.md        # Physical boundaries & non-destructive scope
│   ├── ARCHITECTURE_DECISION_RECORDS.md # Key technical decision records
│   ├── API_DOCUMENTATION.md  # Complete REST API reference
│   ├── RESEARCH_CITATIONS.md # Formal agronomic & CV literature citations
│   └── DATASET_CARD.md       # Dataset provenance, split protocol, & metrics
├── ml/                       # Model Training & Evaluation Subsystem
│   ├── evaluate.py           # Stratified evaluation & confusion matrix script
│   └── reports/              # JSON metrics & confusion matrix visualizations
├── mobile/                   # React Native (Expo) Field Officer Client
└── cv_tools/                 # Synthetic spread generator & dataset utilities
```

---

## 9. Team & Hackathon Details

- **Team Name:** Better Call Coders
- **Team Leader:** Ubaid Khan
- **Hackathon:** Smart India Hackathon (SIH 2026)
- **Problem Statement:** SIH26031: Quality assessment and grading of onions
- **License:** GNU Affero General Public License v3.0 ([AGPL-3.0](LICENSE))
