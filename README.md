# Cepa (SIH26031): Computer Vision Onion Quality Inspection and Automated Grading System

Cepa is an edge-capable computer vision system and mobile inspection instrument engineered for agricultural procurement officers operating under government buffer schemes, including the National Agricultural Cooperative Marketing Federation of India (NAFED), the National Cooperative Consumers' Federation of India (NCCF), and Agricultural Produce Market Committee (APMC) mandis.

The system automates the inspection, sizing, defect classification, and commercial grading of onion (*Allium cepa*) lots directly at the farm-gate and procurement center. By coupling sub-pixel planar scale calibration with marker-controlled distance-transform watershed instance segmentation and multi-spectral chromatic analysis, Cepa replaces subjective, error-prone visual inspection with verifiable, evidence-backed quality certification.

---

## 1. Executive Summary and Operational Context

### 1.1 The Procurement Problem
India is the world's second-largest onion producer, with annual output exceeding 30 million metric tonnes concentrated across Maharashtra (Nashik, Ahmednagar, Pune), Madhya Pradesh, and Gujarat. To stabilize seasonal price volatility, the Government of India procures an annual buffer stock of 500,000 to 700,000 metric tonnes through the Price Stabilisation Fund (PSF), executed via NAFED and NCCF.

Current procurement operations rely on manual visual sampling:
- **High Error Variance**: Procurement officers visually estimate bulb diameter using manual ring gauges on an arbitrary sample of 10 to 20 onions per truckload (10 to 25 metric tonnes).
- **Subjective Defect Scoring**: Rejection of lots due to minor cuts, neck rot, or sprouting leads to severe farmer-trader disputes, arbitrary dockage penalties, and operational delays at mandi gates.
- **Post-Harvest Deterioration**: Storing uncurated lots with high moisture, fungal rot (*Aspergillus niger*), or sprouting accelerates storage loss, leading to 25% to 40% post-harvest wastage in ventilated godowns (*chawls*).

### 1.2 The Cepa Objective
Cepa provides an objective, tamper-evident digital inspection tool:
1. An officer spreads a representative lot sample (20 to 50 bulbs) on an inspection mat with a known-size reference target.
2. A single overhead smartphone capture is processed through a deterministic 8-stage computer vision pipeline in under 2 seconds.
3. Every individual bulb is isolated, measured with sub-millimetre caliper precision, classified for visible defects, and assigned an APMC size tier and NAFED commercial grade.
4. An immutable inspection certificate with lot-level dockage calculations, photographic evidence crops, and verification QR codes is generated and synchronized with central procurement ledgers.

---

## 2. System Architecture

Cepa is architected as a local-first, privacy-preserving client-server system designed to operate reliably in bandwidth-constrained rural mandis.

```
+-----------------------------------------------------------------------------------+
|                               Mobile Edge Client                                  |
|                         (React Native 0.76 / Expo SDK 52)                         |
|                                                                                   |
|  +---------------------+  +---------------------+  +---------------------------+  |
|  |   Capture Module    |  |  Interactive UI/UX  |  |   Evidence Drilldown      |  |
|  | Viewfinder Guidance |  | Mandi Theme Engine  |  |  Sub-pixel Morphometry   |  |
|  | Real-time Exposure  |  | Off-White Aesthetic |  |  Manual Officer Override  |  |
|  +----------+----------+  +----------+----------+  +-------------+-------------+  |
|             |                        |                           |                |
|             +------------------------+---------------------------+                |
|                                      |                                            |
|                           HTTP / REST + JSON / Blob                               |
+--------------------------------------v--------------------------------------------+
                                       |
+--------------------------------------v--------------------------------------------+
|                             Cepa Core Backend                                     |
|                        (FastAPI / Python 3.12 / ASGI)                             |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  |                        8-Stage CV Pipeline Coordinator                      |  |
|  |                                                                             |  |
|  |  [S1: Quality Gate] -----> [S2: ChArUco Marker] ----> [S3: Rectification]   |  |
|  |          |                                                    |             |  |
|  |  [S6: Defect Engine] <--- [S5: Crop Extraction] <--- [S4: Watershed Seg]   |  |
|  |          |                                                                  |  |
|  |  [S7: Morphometry] ------> [S8: Confidence Tier] --> [Lot Aggregation]      |  |
|  +-----------------------------------+-----------------------------------------+  |
|                                      |                                            |
|  +-----------------------------------+-----------------------------------------+  |
|  |                         Domain Services Layer                               |  |
|  |  - InspectionService (Lifecycle FSM)       - ReportService (ReportLab PDF)  |  |
|  |  - GradingEngine (Rule-based Evaluator)   - PayoutEngine (Dockage Formula)  |  |
|  +-----------------------------------+-----------------------------------------+  |
|                                      |                                            |
|  +-----------------------------------+-----------------------------------------+  |
|  |                       Storage and Persistence Layer                         |  |
|  |  - SQLite (WAL Mode, Foreign Key Pragmas) via SQLAlchemy ORM                |  |
|  |  - Local Content-Addressable Storage (Originals, Crops, Binary Masks)      |  |
|  +-----------------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------+
```

### 2.1 Architectural Decision Records (ADRs)

#### ADR-001: Deterministic Marker-Controlled Watershed vs. Pure Deep Learning
- **Context**: Deep learning instance segmentation models (YOLOv8-seg, YOLO11-seg) require pre-trained weights, GPU acceleration, and substantial inference memory. In packhouse environments without internet or GPU access, downloading 50MB+ weights is impractical.
- **Decision**: Implement an industrial-grade, marker-controlled Euclidean distance-transform watershed segmentation provider as the core zero-cold-start engine. YOLO11-seg remains an optional, pluggable provider when GPU acceleration and trained weights are present.
- **Rationale**: Watershed executes in under 25ms on a single CPU core, has zero external model dependencies, and guarantees deterministic boundaries when seed markers are guided by regional peak local maxima.

#### ADR-002: Planar Homography Rectification via ChArUco Calibration
- **Context**: Smartphone captures at mandi yards are subject to perspective tilt (camera angle deviation from the optical normal) and varying capture heights (60cm to 120cm), rendering uncalibrated pixel-to-millimetre ratios mathematically invalid.
- **Decision**: Standardize on an A4-sized 7x5 ChArUco board with 40mm checker squares and ArUco Dictionary `DICT_5X5_100`.
- **Rationale**: ChArUco combines the unambiguous ID recovery of ArUco markers with the sub-pixel corner precision of checkerboard vertices. Even under partial occlusion (up to 40% of the board covered by onions or dirt), the system derives a perspective homography matrix:

$$H \in \mathbb{R}^{3 \times 3} \quad \text{such that} \quad \mathbf{x}' \sim H \mathbf{x}$$

This rectifies the capture surface into an orthographic projection with a metric scale factor $\sigma \text{ (mm/pixel)}$.

#### ADR-003: Decoupled, Versioned Grading Policies in YAML
- **Context**: NAFED, NCCF, APMC, and export buyers (APEDA) enforce differing size boundaries and defect tolerances. Hardcoding size thresholds inside SQL tables or Python code creates vendor lock-in and prevents policy audits.
- **Decision**: Externalize all grading parameters into declarative, versioned YAML policies stored in `backend/grading/policies/`.
- **Rationale**: Policies specify strict parameter schemas (`SizeThresholds`, `DefectThresholds`, `DockageMultipliers`). A change in government procurement parameters (for example, relaxing the Grade A lower limit from 45mm to 40mm during drought years) requires updating a single versioned YAML file with zero codebase modifications.

#### ADR-004: Dual-Engine Cross-Platform Upload Architecture
- **Context**: React Native mobile applications run on iOS/Android native engines, whereas web demonstration portals execute inside browser JavaScript engines (React Native Web). Standard browser `FormData.append()` converts `{ uri, name, type }` objects into `[object Object]` strings, causing HTTP 422 validation rejections in ASGI frameworks.
- **Decision**: Implement a platform-branching binary transport layer in `mobile/src/api/client.ts`. On native platforms, pass standard URI dictionaries. On web platforms, resolve local object URIs into binary `Blob` instances via the Fetch API prior to multipart assembly.

---

## 3. The 8-Stage Computer Vision Pipeline

```
  Input Image (Raw JPEG / PNG)
               |
               v
  [Stage 1: Image Quality Gate]
  Check Laplacian blur variance, luminance histogram, glare ratio, and resolution
               | (Must Pass)
               v
  [Stage 2: Marker Detection]
  Detect ChArUco / ArUco markers; compute sub-pixel checkerboard corners
               | (Detected / Uncalibrated Fallback)
               v
  [Stage 3: Perspective Rectification & Scale Calibration]
  Compute 3x3 Homography Matrix; warp image to orthogonal plane; derive mm/px ratio
               |
               v
  [Stage 4: Instance Segmentation]
  CIELAB chromatic thresholding; Euclidean distance transform; Meyer watershed
               |
               v
  [Stage 5: Crop Extraction & Matting]
  Fill internal contour holes; 1.5px Gaussian edge feathering; blend off-white background
               |
               v
  [Stage 6: Multi-Spectral Defect Analysis]
  Detect soft rot, sprouting, mechanical cuts, black mold (Aspergillus), sunburn
               |
               v
  [Stage 7: Morphometry & Sizing]
  Calculate minimum area bounding box, equatorial/polar axes, oblate mass estimate
               |
               v
  [Stage 8: Confidence Tiering & Quality Gating]
  Assess edge proximity, geometric eccentricity, calibration presence; assign High/Med/Low
               |
               v
  Output: Verified Inspection Lot Result
```

### Stage 1: Image Quality Gating
Before computational resources are expended on segmentation, the raw frame is checked against 5 physical capture constraints:
1. **Resolution Gate**: Minimum dimension $\min(W, H) \ge 1200\text{ px}$.
2. **Focus / Blur Gate**: Evaluated using the variance of the discrete Laplacian operator:

$$\text{Var}(\nabla^2 I) = \frac{1}{N} \sum_{x, y} \left( \nabla^2 I(x, y) - \overline{\nabla^2 I} \right)^2 \ge 85.0$$

3. **Under-exposure Gate**: Mean luminance in the greyscale plane $\mu_{\text{gray}} \ge 40.0$.
4. **Over-exposure Gate**: Fraction of saturated pixels ($I(x, y) \ge 250$) must not exceed $15.0\%$.
5. **Specular Glare Gate**: High-luminance clusters with low local saturation must not exceed $8.0\%$ of the surface area.

### Stage 2: Sub-Pixel Reference Marker Detection
The image is interrogated for the presence of the calibration board:
- **Detector**: `cv2.aruco.ArucoDetector` configured with sub-pixel corner refinement (`CORNER_REFINE_SUBPIX`).
- **Board Configuration**: 7 squares horizontally, 5 squares vertically; square size $40.0\text{ mm}$, marker size $25.0\text{ mm}$.
- **Corner Interpolation**: `cv2.aruco.interpolateCornersCharuco` fits sub-pixel coordinates for all internal checkerboard vertices, returning corner IDs and pixel coordinates.

### Stage 3: Scale Calibration and Homography Rectification
Using the detected ChArUco corners, the system computes the planar homography matrix $H$:
- **Source Points**: Sub-pixel image coordinates $(u_i, v_i)$.
- **Destination Points**: Metric Euclidean plane coordinates $(X_i, Y_i)$ defined by the known physical geometry of the board.
- **Warping**: `cv2.warpPerspective` projects the entire image onto a flat, top-down plane.
- **Metric Resolution**:

$$\sigma = \frac{\Delta \text{distance}_{\text{metric}}}{\Delta \text{distance}_{\text{pixel}}} \quad (\text{mm/pixel})$$

If the board is absent or obscured, the pipeline flags the sample as `marker_not_detected`, skips metric warping, sets $\sigma = \text{None}$, and continues processing in uncalibrated mode.

### Stage 4: Industrial Watershed Instance Segmentation
For clustered, touching, or partially overlapping onion bulbs, standard global thresholding fails. The industrial watershed engine operates through a 5-step sequence:
1. **Perimeter-Normalized Color Segmentation**:
   - The background luminance and chromaticity are sampled from a 15-pixel border strip along the image perimeter in both greyscale and CIELAB space:

$$\mathbf{c}_{\text{bg}} = \left( L_{\text{bg}}, a_{\text{bg}}, b_{\text{bg}} \right)$$

   - The Euclidean chromatic distance isolates onion skins (red/purple anthocyanins and yellow/brown flavonoids) while rejecting neutral linen and wooden table backgrounds:

$$\Delta E_{\text{ab}} = \sqrt{(a - a_{\text{bg}})^2 + (b - b_{\text{bg}})^2}$$

   - The preliminary binary foreground mask is obtained via:

$$M_{\text{fg}} = \left( \Delta E_{\text{ab}} \ge 16.0 \right) \lor \left( S_{\text{HSV}} \ge 45 \right) \lor \left( |L - L_{\text{bg}}| \ge 22 \right)$$

2. **Internal Hole Filling**:
   - Dry papery skins, specular glints, and tan root plates exhibit low saturation that can cause internal voids.
   - A two-level contour analysis (`cv2.RETR_CCOMP`) identifies all internal holes with area under 30,000 pixels and fills them with solid foreground:

$$\forall C_k \in \text{Holes}(M_{\text{fg}}), \quad M_{\text{fg}}(x, y) \leftarrow 1$$

3. **Euclidean Distance Transform**:
   - Computes the L2 distance from every foreground pixel to the nearest background pixel:

$$D(p) = \min_{q \in M_{\text{bg}}} \|p - q\|_2$$

4. **Regional Peak Local Maxima**:
   - Distance maps are smoothed using a Gaussian kernel ($\sigma = 1.5$) to remove surface texture noise.
   - An adaptive morphological dilation window is constructed based on the maximum distance:

$$k_{\text{size}} = \max\left(21, \min\left(45, \lfloor 0.35 \cdot D_{\max} \rfloor \lor 1\right)\right)$$

   - Regional peaks are identified where the smoothed distance equals the dilated distance:

$$\text{Peaks} = \left( D_{\text{smooth}} = \text{Dilate}(D_{\text{smooth}}, k_{\text{size}}) \right) \land \left( D_{\text{smooth}} \ge \max(15.0, 0.22 \cdot D_{\max}) \right)$$

   - Non-Maximum Suppression (NMS) with an exclusion radius of 38 pixels merges duplicate peaks, producing one seed centroid per bulb.
5. **Meyer Watershed Flooding**:
   - Background markers are placed outside a 15-pixel dilated foreground boundary.
   - Flooding proceeds on a Gaussian-filtered image, partitioning touching bulbs along their contact saddles. Detections touching the outer image boundary with an area under 3,500 pixels are discarded as edge noise.

### Stage 5: Crop Extraction and Edge Matting
For each segmented instance:
- The binary mask is filled to ensure solid coverage.
- To eliminate harsh staircase pixel artifacts, the binary mask boundary is smoothed with a Gaussian filter ($\sigma = 1.5$):

$$\alpha(x, y) = \frac{1}{255} \cdot \text{GaussianBlur}(M_{\text{filled}}, 5 \times 5, 1.5)$$

- The isolated crop is blended against an off-white stone background ($[239, 243, 244]$ BGR, corresponding to `#f4f3ef`):

$$I_{\text{crop}}(x, y) = \alpha(x, y) \cdot I_{\text{rectified}}(x, y) + (1 - \alpha(x, y)) \cdot \begin{bmatrix} 239 \\ 243 \\ 244 \end{bmatrix}$$

This produces clean, professional evidence cutouts with zero pitch-black voids.

### Stage 6: Multi-Spectral Defect Analysis
Each extracted crop undergoes specialized defect classification:
- **Sprouting**: Detection of green vegetative shoots emerging from the neck plate via the Normalized Green-Red Difference Index (NGRDI):

$$\text{NGRDI} = \frac{G - R}{G + R + \epsilon}$$

  Pixels with $\text{NGRDI} \ge 0.12$ clustered within the upper 30% of the bulb bounding box indicate sprouting.
- **Black Mold (*Aspergillus niger*)**: High-frequency, low-luminance soot patches identified via adaptive thresholding on the luminance plane combined with spatial clustering.
- **Mechanical Damage & Cuts**: Surface skin ruptures exposing fleshy scale leaves, characterized by sharp edge discontinuities within the interior contour.
- **Sunburn**: Superficial greening of outer fleshy scales due to solar radiation exposure in field windrows.

### Stage 7: Physical Morphometry and Sizing
When scale calibration is active ($\sigma \text{ mm/pixel}$), the system measures bulb geometry:
1. **Equatorial Diameter ($D_{\text{eq}}$)**: Computed by finding the minimum-area enclosing rectangle (`cv2.minAreaRect`) around the instance contour:

$$D_{\text{eq}} = \max(w_{\text{rect}}, h_{\text{rect}}) \cdot \sigma$$

2. **Polar Diameter ($D_{\text{pol}}$)**:

$$D_{\text{pol}} = \min(w_{\text{rect}}, h_{\text{rect}}) \cdot \sigma$$

3. **Equivalent Spherical Diameter ($D_{\text{equiv}}$)**: Derived from the projected 2D surface area $A_{\text{px}}$:

$$D_{\text{equiv}} = 2 \cdot \sqrt{\frac{A_{\text{px}}}{\pi}} \cdot \sigma$$

4. **Shape Classification & Sphericity**:

$$\psi = \frac{D_{\text{pol}}}{D_{\text{eq}}}$$

  - $\psi < 0.85$: Oblate (flat globe, common in Indian Kharif crops).
  - $0.85 \le \psi \le 1.15$: Spherical (globe, ideal Rabi storage crop).
  - $\psi > 1.15$: Torpedo / Oblong.
5. **Estimated Fresh Weight ($W_{\text{est}}$)**: Modeled as an oblate spheroid with fresh onion density $\rho \approx 0.985 \times 10^{-3} \text{ g/mm}^3$:

$$V = \frac{4}{3}\pi \left(\frac{D_{\text{eq}}}{2}\right)^2 \left(\frac{D_{\text{pol}}}{2}\right) = \frac{\pi}{6} D_{\text{eq}}^2 D_{\text{pol}}$$

$$W_{\text{est}} = V \cdot \rho \quad (\text{grams})$$

### Stage 8: Multi-Factor Confidence Tiering
Every bulb receives a verifiable confidence classification:
- **HIGH**: $\sigma$ is calibrated, instance does not touch the frame boundary, solidity $\ge 0.88$, and defect prediction entropy is low.
- **MEDIUM**: Calibrated, but slight border proximity ($< 10\text{ px}$) or minor contour irregularity ($0.75 \le \text{solidity} < 0.88$).
- **LOW / UNUSABLE**: Uncalibrated reference scale, severe frame cutoff ($> 15\%$ of perimeter), or extreme occlusion. Low-confidence bulbs are flagged for mandatory officer manual verification.

---

## 4. Mandi Standards, Grading Logic, and Commercial Payout

### 4.1 APMC Sizing Standards (Bureau of Indian Standards IS 17912:2022)
Cepa classifies all measured bulbs into standardized mandi commercial size tiers:

| Size Grade | Equatorial Diameter Range | Mandi Trade Nomenclature | Commercial Utilization |
|---|---|---|---|
| **Goli / Small** | $< 35.0\text{ mm}$ | Goli / Chhata | Processing, dehydrated flakes, domestic culinary |
| **Madhyam / Medium** | $35.0\text{ mm} \le D < 45.0\text{ mm}$ | Medium | Standard domestic retail market |
| **Super / Large** | $45.0\text{ mm} \le D \le 65.0\text{ mm}$ | Super / Bilti | Premium retail, government buffer reserve |
| **Jumbo / Oversized** | $> 65.0\text{ mm}$ | Jumbo / Ex-Large | Institutional catering, hotels, fast food processing |

### 4.2 NAFED Buffer Procurement Specifications (DEMO_ASSUMPTION_v1)
Under NAFED/NCCF Price Stabilisation Fund operations, lots must meet strict defect limits:

| Parameter | Grade A Specification | URS (Under Relaxed Specification) | Rejection Threshold |
|---|---|---|---|
| **Equatorial Size** | $45.0\text{ mm} \le D \le 65.0\text{ mm}$ | $35.0\text{ mm} \le D \le 70.0\text{ mm}$ | $< 35.0\text{ mm}$ or $> 70.0\text{ mm}$ |
| **Tolerance for Other Sizes** | Max $10.0\%$ by weight | Max $15.0\%$ by weight | $> 15.0\%$ out-of-spec |
| **Sprouting Tolerance** | $0.0\%$ (Strict zero-tolerance) | Max $2.0\%$ | $> 2.0\%$ sprouted |
| **Rotten / Decayed Bulbs** | $0.0\%$ (Strict zero-tolerance) | Max $1.5\%$ | $> 1.5\%$ rot |
| **Mechanical Damage / Cuts** | Max $2.0\%$ | Max $5.0\%$ | $> 5.0\%$ damage |
| **Foreign Matter / Dirt** | Max $1.0\%$ | Max $2.0\%$ | $> 2.0\%$ dirt |

### 4.3 Payout and Commercial Dockage Mechanics
When an inspected lot meets the URS criteria rather than Grade A, commercial dockage is computed deterministically:

$$\text{Dockage Rate } (\delta) = \sum_{k} w_k \cdot \max\left(0, P_k - P_{k, \text{allowed}}\right)$$

Where:
- $P_{\text{rot}}$: Measured rot percentage (Penalty weight $w_{\text{rot}} = 2.5$).
- $P_{\text{sprout}}$: Measured sprout percentage (Penalty weight $w_{\text{sprout}} = 2.0$).
- $P_{\text{damage}}$: Measured cut/damage percentage (Penalty weight $w_{\text{damage}} = 1.0$).
- $P_{\text{undersize}}$: Measured sub-35mm percentage (Penalty weight $w_{\text{size}} = 0.8$).

The final procurement payout to the farmer is calculated as:

$$\text{Final Rate} = \text{Base MSP} \times \left(1 - \frac{\delta}{100}\right) \quad (\text{INR / Quintal})$$

$$\text{Total Payout} = \text{Net Lot Weight (Quintals)} \times \text{Final Rate}$$

---

## 5. Repository Structure and Codebase Index

```
Cepa/
├── .env.example                       # Environment configuration template
├── .gitignore                         # Strict exclusion for weights, databases, caches
├── .session-checkpoint.md             # Long-session state ledger for autonomous development
├── README.md                          # Comprehensive technical documentation
├── start.bat                          # Turnkey dual-stack launcher (Backend + Expo Web)
├── pyproject.toml                     # Python package build definition and tool configuration
├── docs/                              # Detailed architectural design records
│   ├── ARCHITECTURE.md                # System topology and domain boundaries
│   ├── CV_PIPELINE.md                 # Mathematical specification of the 8-stage pipeline
│   ├── DATASET.md                     # Data collection, annotation, and retraining protocols
│   ├── GRADING_ENGINE.md              # Mandi standards, BIS IS 17912, NAFED guidelines
│   └── LIMITATIONS.md                 # Physical, optical, and hardware boundaries
├── backend/                           # Core FastAPI application
│   ├── main.py                        # Application entry point, lifespan, CORS, error handling
│   ├── config.py                      # Pydantic BaseSettings management and path resolvers
│   ├── database.py                    # SQLAlchemy session engine, SQLite WAL pragmas
│   ├── pyproject.toml                 # Backend dependencies and pytest metadata
│   ├── alembic.ini                    # Database schema migration configuration
│   ├── alembic/                       # Schema version migration scripts
│   ├── models/                        # SQLAlchemy database models
│   │   ├── __init__.py                # Model registry
│   │   ├── inspection.py              # Inspection lot entity (mandi, officer, GPS, status)
│   │   ├── sample.py                  # Sample capture entity (quality flags, scale, timing)
│   │   ├── onion_instance.py          # Bulb entity (bounding box, mask path, grade, tier)
│   │   ├── measurement.py             # Sub-pixel morphometric records (axes, area, solidity)
│   │   ├── defect_observation.py      # Defect probabilities (rot, sprout, damage, mold)
│   │   ├── classification_result.py   # Classification audit ledger
│   │   └── report.py                  # Report metadata, share tokens, PDF paths
│   ├── schemas/                       # Pydantic v2 serialization schemas
│   │   ├── __init__.py                # Schema exports
│   │   ├── inspection.py              # Inspection creation, response, and patch schemas
│   │   ├── grading.py                 # Threshold definitions and grading output schemas
│   │   └── report.py                  # Report summary, histogram, and audit schemas
│   ├── routers/                       # FastAPI REST route handlers
│   │   ├── __init__.py                # Router exports
│   │   ├── health.py                  # Health check, CV status, and demo image provider
│   │   ├── inspections.py             # Lot initialization, sample upload, finalization
│   │   ├── onions.py                  # Single-bulb drilldown and officer manual corrections
│   │   └── reports.py                 # JSON compilation, public share links, PDF delivery
│   ├── services/                      # Domain business logic
│   │   ├── __init__.py                # Service exports
│   │   └── inspection_service.py      # Core state machine, CV execution, DB persistence
│   ├── cv/                            # Computer Vision module
│   │   ├── __init__.py                # CV exports
│   │   ├── pipeline.py                # 8-stage synchronous CV pipeline coordinator
│   │   ├── quality_gate.py            # Laplacian blur, brightness, glare validation
│   │   ├── marker_detector.py         # Sub-pixel ChArUco / ArUco detection engine
│   │   ├── calibration.py             # Homography matrix calculation and metric scaling
│   │   ├── crop_extractor.py          # Contour hole filling, alpha feathering, off-white matting
│   │   ├── defect_classifier.py       # Multi-label defect inference engine
│   │   ├── size_estimator.py          # Minimum bounding box, equatorial/polar axes
│   │   ├── confidence.py              # Multi-factor confidence tier assessment
│   │   ├── inspector.py               # Visual diagnostic overlay renderer
│   │   └── providers/                 # Instance segmentation model providers
│   │       ├── __init__.py            # Provider exports
│   │       ├── base.py                # Abstract Base Class: SegmentationProvider
│   │       ├── watershed_provider.py  # Production industrial distance-transform watershed
│   │       ├── yolo11_provider.py     # Ultralytics YOLO11-seg inference wrapper
│   │       └── mock_provider.py       # Deterministic fallback provider for testing
│   ├── grading/                       # Agricultural grading policy engine
│   │   ├── __init__.py                # Grading exports
│   │   ├── policy_loader.py           # YAML policy parser and schema validator
│   │   ├── engine.py                  # Per-bulb grading evaluation logic
│   │   ├── aggregator.py              # Lot statistical aggregation and dockage engine
│   │   └── policies/                  # Declarative versioned policy files
│   │       └── DEMO_ASSUMPTION_v1.yaml# NAFED / PSF buffer procurement specification
│   └── tests/                         # Comprehensive automated test suite (40 specs)
│       ├── __init__.py                # Test package
│       ├── conftest.py                # Pytest fixtures, test database, mock client
│       ├── test_api.py                # End-to-end API inspection workflow tests
│       ├── test_quality_gate.py       # Synthetic blur, darkness, and glare tests
│       ├── test_size_estimator.py     # Sub-pixel geometric measurement tests
│       ├── test_grading_engine.py     # Grade A, URS, and rejection policy tests
│       └── test_advanced_morphometry.py # Oblate spheroid, dockage, and NGRDI defect tests
├── mobile/                            # React Native mobile application
│   ├── App.tsx                        # Root application, navigation stack, state engine
│   ├── index.ts                       # Expo root registration
│   ├── package.json                   # Dependencies (Expo SDK 52, React Native 0.76)
│   ├── tsconfig.json                  # TypeScript compiler settings
│   ├── app.json                       # Expo configuration
│   └── src/                           # Mobile application source code
│       ├── config.ts                  # Network configuration and API URL resolvers
│       ├── types.ts                   # Complete TypeScript data model contracts
│       ├── api/                       # Network client
│       │   └── client.ts              # Platform-adaptive HTTP / multipart upload engine
│       ├── components/                # Reusable UI widgets
│       │   ├── Header.tsx             # Contextual header with lot badge and back action
│       │   └── EvidenceDrilldownModal.tsx # Single-bulb inspection and manual override modal
│       ├── screens/                   # Application screens
│       │   ├── HomeScreen.tsx         # Lot ledger, procurement statistics, resume drafts
│       │   ├── NewInspectionScreen.tsx# Lot metadata entry (mandi, officer, GPS coordinates)
│       │   ├── CaptureScreen.tsx      # Viewfinder, ChArUco alignment frame, spread guide
│       │   ├── QualityCheckScreen.tsx # Pre-flight validation results and retake guidance
│       │   ├── ResultsScreen.tsx      # Lot KPIs, bulb grid, annotated overlay, scale alert
│       │   └── FinalReportScreen.tsx  # Final certification, dockage payout, PDF download
│       └── ui/                        # Off-White Editorial Mandi Design System
│           ├── Theme.ts               # Color tokens (Linen, Card, Obsidian, Stone)
│           ├── AnimatedPressable.tsx  # 60fps spring interaction wrapper with web flex support
│           ├── Badge.tsx              # Grade badges (Grade A, URS, Reject) and size tiers
│           ├── FadeInView.tsx         # Micro-stagger entrance animation wrapper
│           ├── Haptics.ts             # Cross-platform tactile feedback handler
│           ├── LazyImage.tsx          # Smooth image component with skeleton loaders
│           ├── RadarPulse.tsx         # Circular radar animation for calibration status
│           ├── Skeleton.tsx           # Anti-layout-shift placeholder elements
│           └── index.ts               # UI component barrel export
└── cv_tools/                          # Diagnostic, calibration, and synthetic data utilities
    ├── generate_charuco_board.py      # Printable A4 ChArUco calibration board generator
    ├── generate_synthetic_sample.py   # Ground-truth synthetic onion spread generator
    └── test_data/                     # Calibration boards and test spreads
```

---

## 6. Technology Stack and Engineering Rationale

### 6.1 Backend
- **FastAPI 0.115+ / Starlette**: Provides high-throughput asynchronous execution. CPU-bound computer vision stages run in a dedicated `ThreadPoolExecutor` to ensure the ASGI event loop is never blocked during image processing.
- **Python 3.12**: Selected for improved runtime performance, enhanced typing generics, and native performance optimizations.
- **OpenCV 4.10 (headless)**: Core image processing, morphological filtering, Euclidean distance transforms, sub-pixel corner interpolation, and perspective warping.
- **NumPy 2.1+**: Vectorized matrix calculations, distance map operations, and histogram analysis.
- **SQLAlchemy 2.0+ with SQLite (WAL Mode)**: Lightweight, zero-configuration local database. SQLite runs with `journal_mode=WAL` (Write-Ahead Logging) and `busy_timeout=5000` to support concurrent reads while inspection results are committed.
- **ReportLab 4.2+**: Programmatic generation of vector-quality, printable A4 PDF inspection certificates with embedded tabular summaries and verification QR codes.
- **Pytest & AnyIO**: Comprehensive test runner supporting async integration testing and parameterized fixture matrices.

### 6.2 Frontend / Mobile Client
- **React Native 0.76 & Expo SDK 52**: Cross-platform mobile development targeting Android, iOS, and Web from a single codebase.
- **TypeScript 5.3 (Strict Mode)**: Comprehensive type safety across all network payloads, UI states, and domain models.
- **React Native Reanimated & Animated**: 60fps spring-physics animations and micro-interactions.
- **Expo Haptics**: Tactile feedback on critical officer interactions (defect tagging, lot certification, shutter trigger).
- **Lucide Icons & Monospace Telemetry**: Utilitarian, high-legibility typography designed for outdoor visibility under direct sunlight in dusty mandi yards.

---

## 7. Mobile UI/UX Design System: The Off-White Editorial Mandi Aesthetic

Cepa deliberately eliminates generic artificial intelligence design tropes (glowing neon gradients, pitch-black dark modes, random emojis, and low-effort pill overlays). Instead, it adopts a print-inspired, editorial aesthetic designed for field credibility:

### 7.1 Design Tokens (`mobile/src/ui/Theme.ts`)
- **Surfaces**:
  - `Colors.bg = '#f9f8f6'`: Warm linen off-white representing natural unbleached paper.
  - `Colors.cardBg = '#ffffff'`: Crisp white card surface providing high-contrast separation.
  - `Colors.cardBgElevated = '#f4f3ef'`: Subtle warm stone surface for secondary modules, crop backdrops, and telemetry bars.
- **Borders & Dividers**:
  - `Colors.border = '#e7e5e4'`: 1px stone divider defining modular boundaries without heavy drop shadows.
  - `Colors.borderActive = '#18181b'`: Charcoal focus border for active selections and certified lots.
- **Primary Typography & Accents**:
  - `Colors.text = '#18181b'`: High-density charcoal replacing pure `#000000` to reduce eye strain.
  - `Colors.textSecondary = '#52525b'`: Mid-tone charcoal for secondary metadata and technical units.
  - `Colors.accent = '#18181b'`: Obsidian accent for primary actions.
  - `Colors.accentTeal = '#0f766e'`: Calm agricultural teal used exclusively for calibration indicators.
- **Mandi Quality Status Tones**:
  - **Grade A**: Obsidian `#18181b` on `#f4f3ef` (Restrained, certified quality).
  - **URS**: Ochre/Amber `#9a3412` on `#fffbeb` (Borderline, relaxed specification).
  - **Rejected**: Deep Brick Crimson `#991b1b` on `#fef2f2` (Defective lot).

---

## 8. REST API Reference

All API routes are versioned under `/api/v1`.

### 8.1 System and Health
- `GET /api/v1/health`
  - Returns service status, version, and server timestamp.
- `GET /api/v1/health/cv`
  - Returns active segmentation provider (`watershed-industrial:v1` or `yolo11n-seg`), defect classifier status, active grading policy, and GPU availability.
- `GET /api/v1/demo/sample-image`
  - Serves a high-resolution, photorealistic test spread (`synthetic_onion_spread_sample.jpg`) containing 28 bulbs and an A4 ChArUco calibration target for end-to-end demonstrations.

### 8.2 Inspections
- `POST /api/v1/inspections`
  - Initializes a new inspection session.
  - Request Body:
    ```json
    {
      "lot_id": "LOT-2026-NASHIK-001",
      "procurement_centre": "Lasalgaon Mandi, Nashik",
      "officer_name": "Rajesh Sharma",
      "officer_id": "NAFED-OFFICER-4821",
      "notes": "Rabi crop, farmer Ramdas Patil",
      "geo_lat": 20.1472,
      "geo_lon": 74.2255,
      "location_accuracy": 4.5
    }
    ```
  - Response: `201 Created` with initialized `Inspection` entity (`status: "DRAFT"`).

- `GET /api/v1/inspections`
  - Returns a list of past inspections ordered by creation timestamp with pagination.

- `POST /api/v1/inspections/{id}/samples`
  - Accepts a multipart image upload (`file`), captures GPS coordinates, and triggers the 8-stage CV pipeline.
  - Returns sample analysis results: image quality status, marker calibration telemetry, bulb counts, and per-bulb instance summaries.

- `POST /api/v1/inspections/{id}/finalize`
  - Finalizes the inspection lot. Transitions state from `DRAFT` to `FINALIZED`.
  - Executes lot aggregation, assigns final NAFED grade, and computes commercial dockage.

### 8.3 Bulb-Level Evidence and Manual Override
- `GET /api/v1/inspections/{id}/onions/{onion_id}`
  - Returns complete evidence drilldown for a single bulb: high-resolution crop URL, binary segmentation mask URL, equatorial/polar diameters, weight estimate, defect probabilities, and rule evaluation trace.

- `POST /api/v1/inspections/{id}/onions/{onion_id}/correct`
  - Enables the procurement officer to override computer vision defect classifications.
  - Request Body:
    ```json
    {
      "damaged_prob": 0.0,
      "rotten_prob": 0.0,
      "sprouted_prob": 0.0,
      "corrected_by": "Rajesh Sharma",
      "notes": "Verified visually: root plate is dry, no neck rot present."
    }
    ```
  - Creates an audit record in `defect_observations` tracking original machine predictions alongside officer corrections.

### 8.4 Certification and Reporting
- `POST /api/v1/inspections/{id}/reports`
  - Compiles the final inspection report, generates a secure 64-character public share token, and builds the ReportLab PDF certificate.

- `GET /api/v1/inspections/{id}/reports/pdf`
  - Downloads the official printable PDF inspection certificate.

- `GET /api/v1/reports/share/{token}`
  - Public read-only web portal for farmers and mandi managers to inspect the complete lot certificate and photographic evidence trail.

---

## 9. Database Schema and Persistence Architecture

Cepa utilizes a relational schema configured with foreign key cascades and indexed access paths:

```
+-----------------------------------------------------------------------------------+
|                                 inspections                                       |
|  id (UUID, PK) | lot_id | procurement_centre | officer_name | officer_id           |
|  geo_lat | geo_lon | status (DRAFT/FINALIZED) | created_at | finalized_at         |
+------------------------------------------+----------------------------------------+
                                           | 1
                                           |
                                           | N
+------------------------------------------v----------------------------------------+
|                                   samples                                         |
|  id (UUID, PK) | inspection_id (FK) | sample_number | quality_passed (Bool)        |
|  marker_detected (Bool) | scale_mm_per_px (Float) | onion_count (Int)              |
|  raw_image_path | annotated_image_path | processing_time_ms (Float)               |
+------------------------------------------+----------------------------------------+
                                           | 1
                                           |
                                           | N
+------------------------------------------v----------------------------------------+
|                                onion_instances                                    |
|  id (UUID, PK) | sample_id (FK) | display_number (Int) | bbox_x, y, w, h (Int)    |
|  crop_path | mask_path | touches_border (Bool) | confidence_tier (HIGH/MED/LOW)    |
|  grade (GRADE_A/URS/REJECTED) | mandi_size_grade (SUPER/MADHYAM/JUMBO/GOLI)       |
+-------------------+-----------------------------------+---------------------------+
                    | 1                                 | 1
                    |                                   |
                    | 1                                 | 1
+-------------------v---------------+   +---------------v---------------------------+
|            measurements           |   |            defect_observations            |
|  id (UUID, PK)                    |   |  id (UUID, PK)                            |
|  onion_instance_id (FK)           |   |  onion_instance_id (FK)                   |
|  equatorial_diameter_mm (Float)   |   |  rotten_prob (Float)                      |
|  polar_diameter_mm (Float)        |   |  sprouted_prob (Float)                    |
|  equivalent_diameter_mm (Float)   |   |  damaged_prob (Float)                     |
|  estimated_weight_grams (Float)   |   |  sunburn_prob (Float)                     |
|  shape_classification (String)    |   |  is_corrected (Bool)                      |
|  solidity (Float)                 |   |  corrected_by | corrected_at | notes      |
+-----------------------------------+   +-------------------------------------------+
```

---

## 10. Verification and Automated Testing Suite

The repository contains 40 automated tests verifying every aspect of the pipeline:

### 10.1 Running Backend Pytest Suite
```bash
# Execute full test matrix with verbose output
pytest backend/tests -v
```

### 10.2 Test Coverage Matrix
1. **End-to-End API Workflows (`test_api.py`)**:
   - Service health and versioning endpoints.
   - Demonstration sample image generation and delivery.
   - Complete lifecycle: creation, sample upload, watershed segmentation, single-bulb drilldown, manual officer override, and final lot certification.
2. **Quality Gate Validation (`test_quality_gate.py`)**:
   - Laplacian blur variance filtering on defocused inputs.
   - Under-exposure rejection on dark inputs ($\mu < 40$).
   - Over-exposure rejection on saturated inputs.
   - Specular glare detection on reflective white backgrounds.
3. **Sub-Pixel Sizing and Morphometry (`test_size_estimator.py`, `test_advanced_morphometry.py`)**:
   - Equatorial and polar axis measurement on synthetic masks.
   - Shape classification (Oblate vs. Spherical vs. Torpedo).
   - Equivalent spherical diameter calculations.
   - APMC size tier allocation (Super, Madhyam, Jumbo, Goli).
4. **Grading Policy Engine (`test_grading_engine.py`)**:
   - Grade A qualification for healthy, calibrated bulbs.
   - URS classification for minor mechanical cuts.
   - Mandatory rejection for rotten or sprouted bulbs.
   - Border-cutoff handling and uncalibrated fallback behavior.
5. **Commercial Pricing and Dockage (`test_advanced_morphometry.py`)**:
   - Full payout calculations for pristine Grade A lots.
   - Proportional dockage deductions for moderate URS defects.
   - Lot rejection and zero-payout enforcement for rot over 1.5%.

### 10.3 Mobile TypeScript Typecheck
```bash
cd mobile
npx tsc --noEmit
```
Verifies that all 18 TypeScript modules, UI components, and API client interfaces pass type validation with zero compiler errors.

---

## 11. Deployment and Quickstart Guide

### 11.1 Prerequisites
- **Operating System**: Windows 10/11, Ubuntu 22.04 LTS, or macOS 14+
- **Python**: Version 3.11 or 3.12
- **Node.js**: Version 20.x or 22.x LTS with npm
- **Printer**: Standard laser or inkjet printer for printing the A4 ChArUco calibration board

### 11.2 One-Click Startup (Windows)
The repository includes a batch launcher that manages both backend and frontend servers:
```cmd
start.bat
```
`start.bat` automatically:
1. Validates the Python and Node.js environments.
2. Activates or configures the backend virtual environment.
3. Initializes the SQLite database and executes database migrations.
4. Starts the FastAPI server on `http://localhost:8000`.
5. Starts the Expo Metro bundler on `http://localhost:8081`.

### 11.3 Manual CLI Startup

#### Terminal 1: Backend Service
```bash
cd backend
python -m venv .venv

# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -e .
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

#### Terminal 2: Mobile Client (Expo Web / Mobile)
```bash
cd mobile
npm install
npx expo start --web
```
Open `http://localhost:8081` in Google Chrome or Mozilla Firefox to interact with the web studio interface, or scan the Metro QR code using the Expo Go application on an Android or iOS device.

### 11.4 Generating the Printable ChArUco Calibration Target
```bash
python cv_tools/generate_charuco_board.py
```
This writes `cv_tools/calibration_board/charuco_board_7x5_40mm_A4_printable.pdf`.
- **Printing Instruction**: Print at 100% scale ("Actual Size"). Do not select "Fit to Page" or "Shrink oversized pages".
- **Verification**: Measure any checkerboard square with a physical ruler to confirm it measures exactly $40.0\text{ mm} \times 40.0\text{ mm}$.

---

## 12. Physical, Sensor, and Operational Limitations

In the interest of scientific integrity, Cepa explicitly documents its operational boundaries:

1. **Non-Destructive Exterior Optical Limitation**:
   - Visual cameras capture external surface reflectance only. Internal rot, internal bacterial black heart, or inner-scale decay with no external visual manifestation cannot be detected by 2D RGB sensors.
   - Non-destructive internal defect detection requires Near-Infrared (NIR) spectroscopy (750nm to 1100nm) or X-ray transmission imaging, which are beyond the scope of a standard smartphone camera.
2. **2D Projected Silhouette Measurement**:
   - Sizing calculations assume an oblate spheroid resting stably on its flat cheek. If a bulb rests on its neck or root plate, the projected silhouette represents the equatorial plane rather than the polar profile.
3. **Severe Overlap Limitation**:
   - While the watershed engine splits touching and moderately clustered bulbs along contact creases, bulbs that are completely stacked on top of one another will be occluded. Procurement officers must spread lots into a reasonably distributed, single-layer arrangement.
4. **Extreme Soil Encapsulation**:
   - Field-harvested onions heavily coated in wet clay or soil clods will obscure the true skin color, potentially causing false-positive sunburn or damage readings. Bulbs should be lightly shaken to remove loose dirt prior to spreading.

---

## 13. License and Academic Attribution

This project is developed for the Smart India Hackathon (SIH 2026), Problem Statement SIH26031: *AI-Powered Onion Quality Inspection and Grading System*.

- **Software Core**: Distributed under the MIT License.
- **YOLO11 Provider**: When utilizing the optional Ultralytics YOLO11 backend, usage is subject to the AGPL-3.0 License or commercial enterprise licensing terms from Ultralytics Inc.
- **Reference Standards**: Derived from Bureau of Indian Standards IS 17912:2022 (*Supply Chain of Onions - Guidelines*) and the Ministry of Consumer Affairs, Food and Public Distribution Price Stabilisation Fund (PSF) procurement guidelines.
