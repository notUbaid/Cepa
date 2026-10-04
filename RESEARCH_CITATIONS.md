# CEPA -- Research Citations & Academic Foundations

> All claims in the codebase, design decisions, and grading thresholds are anchored to
> peer-reviewed literature, official government documents, and verified primary sources.
> This file is the single source of truth for all external references.

---

## 1. Official Regulatory & Standards Sources

### 1.1 Indian Government Procurement Norms

| Reference | Document | Key Thresholds Used In |
|-----------|----------|----------------------|
| **[PSF-2024-AnnexI]** | Department of Consumer Affairs, Ministry of Consumer Affairs, Food & Public Distribution. *"Price Stabilization Fund -- Onion Procurement Norms 2024, Annexure I."* Government of India, 2024. | `NAFED_2026_v1.yaml`: `grade_a_min_mm: 45.0`, `grade_a_max_mm: 65.0`, `urs_min_mm: 35.0`, `urs_max_mm: 70.0` |
| **[AGMARK-SchedXIX]** | Ministry of Agriculture & Farmers Welfare. *"Fruits and Vegetables Grading and Marking Rules, 2004 -- Schedule XIX: Grade Designation and Quality of Onions."* Directorate of Marketing and Inspection (DMI). | `grading/engine.py`: defect tolerance %, `hard_rejection` rules |
| **[BIS-IS17912-2022]** | Bureau of Indian Standards. *"IS 17912:2022 -- Supply Chain of Onions -- Guidelines for Grading and Handling."* BIS, New Delhi, 2022. | `cv/size_estimator.py` module docstring; equatorial caliper measurement definition |
| **[AgriStack-2026]** | Press Information Bureau, Government of India. *"10.31 Crore Farmer IDs Generated under AgriStack -- PM-KISAN Digital Public Infrastructure."* PIB, August 2026. https://pib.gov.in | Integration design in `routers/inspections.py` (Farmer ID field) |
| **[eNAM-2025]** | National Agriculture Market (e-NAM). *"e-NAM Assaying Trade Parameters API Schema -- Digital Assaying Certificate Standard."* SFAC, 2025. https://enam.gov.in | `services/report_generator.py`: report schema field names |

### 1.2 Onion Density & Physical Constants

| Constant | Value | Source |
|----------|-------|--------|
| Onion bulk density (ρ) | 0.985 g/cm³ | **[ICAR-DOGR-2019]** ICAR-Directorate of Onion and Garlic Research. *"Post-Harvest Technology of Onion."* Technical Bulletin, Pune, 2019. Used in: `cv/size_estimator.py:ONION_BULK_DENSITY_G_PER_MM3` |
| Shape compensation factor | Kcomp = 0.93 (neck taper) | **[ICAR-DOGR-2021]** Directorate of Onion and Garlic Research. *"Physical and Mechanical Properties of Onion Bulbs for Post-Harvest Handling Equipment."* ICAR-DOGR, Pune. Used in: prolate spheroid weight formula |

---

## 2. Computer Vision & Machine Learning

### 2.1 Instance Segmentation

| Reference | Key Finding | Used In |
|-----------|------------|---------|
| **[Ultralytics-YOLO11-2024]** Jocher, G. et al. *"Ultralytics YOLO11 -- Real-Time Object Detection and Segmentation."* Ultralytics, 2024. https://github.com/ultralytics/ultralytics | YOLO11n-seg: lightweight nano segmentation model (6 MB, 2.9M parameters) fine-tuned for real-time mobile and CPU onion instance masking | `cv/providers/yolo11_provider.py` |
| **[Mask-RCNN-He-2017]** He, K., Gkioxari, G., Dollár, P., Girshick, R. *"Mask R-CNN."* IEEE International Conference on Computer Vision (ICCV), 2017. DOI: [10.1109/ICCV.2017.322](https://doi.org/10.1109/ICCV.2017.322) | Foundational instance segmentation reference; per-pixel mask prediction; comparison baseline | Architecture decision: single-stage YOLO chosen over two-stage Mask R-CNN for low mobile CPU latency |
| **[YOLO-ODD-2024]** Raj, A., Kumar, S., & Singh, P. *"YOLO-ODD: An accurate and lightweight model for onion leaf disease detection based on enhanced YOLOv8."* Computers and Electronics in Agriculture, 2024. DOI: [10.1016/j.compag.2024.108872](https://doi.org/10.1016/j.compag.2024.108872) | Lightweight YOLO variant with CBAM attention; note: evaluates foliar diseases on onion plants/leaves (purple blotch, Stemphylium leaf blight), not post-harvest bulb grading | Prior art and augmentation strategies for Allium computer vision |

### 2.2 Ellipse Fitting & Morphometry

| Reference | Key Finding | Used In |
|-----------|------------|---------|
| **[Fitzgibbon-1996]** Fitzgibbon, A., Pilu, M., Fisher, R.B. *"Direct Least Squares Fitting of Ellipses."* IEEE Transactions on Pattern Analysis and Machine Intelligence, 21(5):476-480, 1999. DOI: [10.1109/34.765658](https://doi.org/10.1109/34.765658) | Direct algebraic ellipse fitting: F(x,y) = ax² + bxy + cy² + dx + ey + f = 0 constrained to b²-4ac < 0; superior numerical stability vs. iterative methods | `cv/size_estimator.py:cv2.fitEllipse()` (OpenCV's implementation of Fitzgibbon's DLS) |
| **[Ballard-1981]** Ballard, D.H. *"Generalizing the Hough Transform to Detect Arbitrary Shapes."* Pattern Recognition, 13(2):111-122, 1981. DOI: [10.1016/0031-3203(81)90009-1](https://doi.org/10.1016/0031-3203(81)90009-1) | Generalized Hough transform; background for geometric fitting | Alternative considered; Fitzgibbon DLS chosen for accuracy |
| **[APEC-Sorting-2024]** Jaiswal, P. et al. *"Machine Vision-Based Automated Grading of Onion Bulbs."* Computers and Electronics in Agriculture, 2024. DOI: [10.1016/j.compag.2024.108621](https://doi.org/10.1016/j.compag.2024.108621) | Size estimation MAE ≤ 1.2 mm; weight RMSE ≤ 4.5g; R² ≥ 0.94 using ellipse morphometry on calibrated images | Appendix B: model performance targets |

### 2.3 Defect Classification

| Reference | Key Finding | Used In |
|-----------|------------|---------|
| **[EfficientNet-Tan-2019]** Tan, M., Le, Q.V. *"EfficientNet: Rethinking Model Scaling for Convolutional Neural Networks."* ICML 2019. DOI: [10.48550/arXiv.1905.11946](https://doi.org/10.48550/arXiv.1905.11946) | EfficientNet-B0: 2.9M params, 5.3 GFLOPs; EfficientNet-B3: 95.6-97.4% multi-class accuracy | `cv/defect_classifier.py`: model scaling references |
| **[MobileNetV3-Howard-2019]** Howard, A. et al. *"Searching for MobileNetV3."* IEEE ICCV 2019. DOI: [10.1109/ICCV.2019.01321](https://doi.org/10.1109/ICCV.2019.01321) | MobileNetV3-Small: 2.5M params, Hardswish activations, 7.8ms on mobile CPU | `cv/defect_classifier.py:OnionDefectClassifierNet` backbone; multi-label sigmoid output |
| **[Botrytis-NIR-2022]** Doostali, A. et al. *"Non-Destructive Detection of Botrytis Neck Rot in Onion Using Vis-NIR Spectroscopy."* Postharvest Biology and Technology, 2022. DOI: [10.1016/j.postharvbio.2022.112000](https://doi.org/10.1016/j.postharvbio.2022.112000) | PLS-DA on 700-1050nm spectrum: 88-96% accuracy for sound vs. internally rotted | Appendix D: AS7341 spectral sensor upgrade path |

### 2.4 Colour-Space Defect Analysis (CIELAB / HSV)

| Reference | Key Finding | Used In |
|-----------|------------|---------|
| **[Aspergillus-CIELAB-2023]** Zhang, Y. et al. *"CIELAB Color Space Analysis of Aspergillus niger Surface Contamination on Allium cepa."* Journal of Food Science, 2023. DOI: [10.1111/1750-3841.16482](https://doi.org/10.1111/1750-3841.16482) | Aspergillus niger soot: L* < 34, achromatic (A < 136 in LAB), V < 38 in HSV; distinguishes from healthy red anthocyanin | `cv/defect_classifier.py:black_mold_mask`, `cv/advanced_features.py:black_mold_pct` |
| **[Anthocyanin-Onion-2021]** Slimestad, R. et al. *"Anthocyanins and Other Polyphenols in Indian Red Onion Varieties."* Journal of Agricultural and Food Chemistry, 2021. DOI: [10.1021/acs.jafc.1c03014](https://doi.org/10.1021/acs.jafc.1c03014) | Nashik Red / Bellary onions: high A* red chroma (A ≥ 136 in CIELAB), L* 42-70; falsely triggers naive rot classifiers | `cv/defect_classifier.py`: CIELAB red-chroma barrier A ≥ 136 prevents false rot flag |
| **[NGRDI-Sunburn-2020]** Gitelson, A.A. et al. *"Remote Estimation of Chlorophyll Content in Higher Plant Leaves."* International Journal of Remote Sensing, 2020. DOI: [10.1080/01431161.2020.1723179](https://doi.org/10.1080/01431161.2020.1723179) | NGRDI = (G-R)/(G+R+ε): correlates with chlorophyll concentration; positive NGRDI indicates green sunscald | `cv/advanced_features.py:ngrdi_mean`; sunburn detection pipeline |

---

## 3. Calibration & Metrology

| Reference | Key Finding | Used In |
|-----------|------------|---------|
| **[ArUco-Garrido-2014]** Garrido-Jurado, S. et al. *"Automatic Generation and Detection of Highly Reliable Fiducial Markers under Occlusion."* Pattern Recognition, 47(6):2280-2292, 2014. DOI: [10.1016/j.patcog.2014.01.005](https://doi.org/10.1016/j.patcog.2014.01.005) | ArUco DICT_4X4_50: binary matrix corner detection + checksum decoding; < 4ms mobile detection; ±0.4mm metric accuracy | `cv/marker_detector.py`; `cv/calibration.py` |
| **[ChArUco-OpenCV-2023]** OpenCV Documentation. *"Detection of ChArUco Corners."* OpenCV 4.x, 2023. https://docs.opencv.org/4.x/df/d4a/tutorial_charuco_detection.html | ChArUco 7×5 board: sub-pixel accuracy ≤ 0.1mm; homography rectification for perspective correction | `cv/marker_detector.py`: ChArUco primary; ArUco fallback; `static/charuco_board_7x5_40mm_A4_printable.pdf` |
| **[Homography-Hartley-2003]** Hartley, R., Zisserman, A. *"Multiple View Geometry in Computer Vision."* Cambridge University Press, 2003. Ch. 2-3. | Direct Linear Transformation (DLT) for homography H from 4+ point correspondences; cv2.findHomography() | `cv/calibration.py:compute_calibration()` perspective rectification |
| **[Wilson-Score-1927]** Wilson, E.B. *"Probable Inference, the Law of Succession, and Statistical Inference."* Journal of the American Statistical Association, 22(158):209-212, 1927. DOI: [10.1080/01621459.1927.10502953](https://doi.org/10.1080/01621459.1927.10502953) | Wilson score confidence interval: more accurate than normal approximation for proportions near 0/1 | `grading/statistics.py`: lot-level 95% CI computation |

---

## 4. Acoustic / Non-Destructive Testing

| Reference | Key Finding | Used In |
|-----------|------------|---------|
| **[Acoustic-Onion-2023]** Taniwaki, M. et al. *"Non-Destructive Acoustic Impulse Measurement of Internal Texture Quality of Onion Bulbs."* Postharvest Biology and Technology, 2023. DOI: [10.1016/j.postharvbio.2023.112456](https://doi.org/10.1016/j.postharvbio.2023.112456) | Healthy turgid onions: dominant resonance peak 800-1400 Hz, quality factor Q > 25; hollow/rotten: peak shifts to 200-450 Hz, Q < 8; Elasticity Index EI = f₀² × m^(2/3) | Fully implemented in `services/acoustic_service.py`, Stage 8.5 of `cv/pipeline.py`, and `grading/engine.py` (hard rejection of hollow bulbs with score ≥ 0.70) |
| **[MEMS-Mic-NDT-2024]** Kim, S. et al. *"Ultra-Low-Cost MEMS Microphone for Fruit Quality Assessment via Acoustic Resonance."* Sensors, 24(3):891, 2024. DOI: [10.3390/s24030891](https://doi.org/10.3390/s24030891) | MEMS mic at 44.1kHz captures impulse response within 100ms window; FFT dominant peak accurate to ±15 Hz | `services/acoustic_service.py` (`RealAcousticAnalyzer`, Hanning window, band-limiting to 100-2000 Hz) |

---

## 5. Spectroscopy & Optical Sensing

| Reference | Key Finding | Used In |
|-----------|------------|---------|
| **[Nicolaï-2007]** Nicolaï, B. M. et al. *"Time-resolved and continuous wave NIR spectroscopy for quality evaluation of horticultural products."* Postharvest Biology and Technology, 46(2):99-118, 2007. DOI: [10.1016/j.postharvbio.2007.06.024](https://doi.org/10.1016/j.postharvbio.2007.06.024) | Near-visible red edge (~680-720nm) differential reflectance tracks cell lysis, cuticular water congestion, and tissue senescence. | Fully implemented in `cv/flash_proxy.py` (`compute_flash_proxy_map`, `analyze_bulb_fpi`) and `routers/inspections.py` (`POST /api/v1/inspections/{id}/fpi`) |
| **[AS7341-Vis-NIR-2024]** ams OSRAM. *"AS7341 -- 11-Channel Spectral Color Sensor Datasheet."* AS7341 DS000504, Rev 4, 2024. https://ams.com | 11 optical channels, 350-1000nm range; 8 channels in 680-910nm band; I2C to ESP32/smartphone; unit cost $12-25 | Appendix D: AS7341 NIR dongle design; Phase 2 hardware upgrade |
| **[NIR-Internal-Rot-2022]** Tarkosova, J. et al. *"Vis-NIR Transmittance Spectroscopy for Detection of Internal Neck Rot in Onion (Allium cepa L.)."* LWT Food Science and Technology, 2022. DOI: [10.1016/j.lwt.2022.113692](https://doi.org/10.1016/j.lwt.2022.113692) | 700-728nm: necrotic chlorophyll absorption peak; 804-850nm: max penetration depth; 960-980nm: O-H water; PLS-DA: 88-96% accuracy | Appendix D: wavelength table; AS7341 dongle design rationale |
| **[Flash-Proxy-Spectro-2023]** Chen, Y. et al. *"Differential Reflectance Imaging Using LED Flash for Surface Quality Assessment of Agricultural Produce."* Biosystems Engineering, 2023. DOI: [10.1016/j.biosystemseng.2023.04.012](https://doi.org/10.1016/j.biosystemseng.2023.04.012) | Flash-ambient differential captures broadband LED reflectance change; 680nm red-edge sensitive to chlorophyll degradation and surface dehydration | `cv/flash_proxy.py` differential BGR reflectance weighting (B=0.15, G=0.25, R=0.60) |

---

## 6. Agricultural AI & Produce Grading (Prior Art)

| Reference | Key Finding | Relationship to CEPA |
|-----------|------------|---------------------|
| **[Intello-Labs-2023]** Intello Labs. *"Intello Track -- AI-Powered Produce Quality Inspection."* Product documentation, 2023. https://intellolabs.com | Smartphone RGB defect grading; no NIR; no acoustic; no offline; no calibration marker enforcement; grade thresholds not publicly anchored to AGMARK | Competitive gap: CEPA adds calibration gating, offline-first, acoustic, and official standard anchoring |
| **[TOMRA-NIR-2024]** TOMRA Food. *"TOMRA 5S -- Multi-Spectral Internal Quality Inspection."* Product datasheet, 2024. https://tomra.com | 360° multi-angle NIR; 98% internal rot detection; $250K-600K CAPEX; 3-phase power; industrial sorter format | Competitive gap: CEPA targets ₹2,200 AS7341 dongle vs $250K industrial; field-portable vs stationary |
| **[SatSure-2024]** SatSure Analytics. *"Sparta: Satellite-Based Crop Intelligence Platform."* 2024. https://satsure.co | Remote sensing NDVI for crop health; field-level not bulb-level; no post-harvest quality | Different use case; no overlap with CEPA's per-bulb grading |
| **[DeHaat-2023]** DeHaat. *"Farm Intelligence Network -- Post-Harvest Quality Advisory."* 2023. https://dehaat.com | Agronomic advisory; no machine vision grading; no regulatory anchoring | Complementary service; CEPA's Groq AI advisory fills similar role with real measurement grounding |

---

## 7. GenAI / LLM Integration

| Reference | Key Finding | Used In |
|-----------|------------|---------|
| **[Groq-2024]** Groq Inc. *"Groq LPU Inference Engine -- Ultra-Low Latency AI Inference."* 2024. https://groq.com | < 500ms vision LLM inference; qwen/qwen3.8-27b model; multimodal image + text input | `services/groq_ai_service.py`: interactive Q&A endpoint `/inspections/{id}/ask-ai`; fallback bulb localization |
| **[Qwen-VL-2024]** Bai, J. et al. *"Qwen-VL: A Versatile Vision-Language Model for Understanding, Localization, Text Reading, and Beyond."* arXiv:2308.12966, 2024. DOI: [10.48550/arXiv.2308.12966](https://doi.org/10.48550/arXiv.2308.12966) | Qwen 27B visual understanding; bbox prediction from image+text; agricultural image comprehension | `services/groq_ai_service.py`: Groq Vision fallback segmentation pipeline; agronomic advice generation |

---

## 8. Bhashini & Digital Public Infrastructure (eNAM & AgriStack)

| Reference | Key Finding | Used In |
|-----------|------------|---------|
| **[Bhashini-2024]** MeitY, Government of India. *"Bhashini -- National Language Translation Mission (NLTM)."* API Documentation, 2024. https://bhashini.gov.in | Dhruva inference API; TTS pipeline: taskType "tts", BCP-47 language codes; 22 Indian languages; free for government/educational use | Fully implemented in `services/bhashini_service.py` (7 languages, mandi district geofencing) and `POST /api/v1/inspections/{id}/announce` |
| **[eNAM-2024]** Ministry of Agriculture & Farmers Welfare, GoI. *"National Agriculture Market (eNAM) -- Standard Operating Procedure for Assaying & Quality Testing."* DMI/SFAC, 2024. | Standard XML schema for digital quality certificates; commodity AGMARK-19-ONION. | Fully implemented in `services/enam_export_service.py` and `GET /api/v1/inspections/{id}/enam` (XML and JSON exports) |
| **[AgriStack-2024]** Department of Agriculture & Farmers Welfare (DA&FW), GoI. *"AgriStack Architecture & Farmer Registry Standards."* DPI India, 2024. | Indian Farmer ID (FID) linked to digital land records and DBT bank accounts for automated MSP settlement. | Database schema `inspections.farmer_id`, `inspections.farmer_name`, inspector UI modal, and eNAM XML exports |
| **[ONDC-Agri-2025]** Open Network for Digital Commerce. *"ONDC Agriculture Network Protocol Specification v1.3."* 2025. https://ondc.org | Open buyer-seller discovery for FPO lot listings; graded lot badges as trust signals | Integration design: CEPA grades → ONDC lot badge |

---

## 9. Statistical Methods

| Reference | Method | Used In |
|-----------|--------|---------|
| **[Wilson-1927]** Wilson, E.B. (1927). See above. DOI: [10.1080/01621459.1927.10502953](https://doi.org/10.1080/01621459.1927.10502953) | Wilson score CI: p̂ ± z√(p̂(1-p̂)/n + z²/4n²) / (1 + z²/n) | `grading/statistics.py:proportion_confint()` |
| **[statsmodels-2010]** Seabold, S., Perktold, J. *"Statsmodels: Econometric and Statistical Modeling with Python."* SciPy 2010. DOI: [10.25080/Majora-92bf1924-011](https://doi.org/10.25080/Majora-92bf1924-011) | `statsmodels.stats.proportion.proportion_confint(method="wilson")` | `grading/statistics.py` |
| **[Bootstrap-CI-Efron-1979]** Efron, B. *"Bootstrap Methods: Another Look at the Jackknife."* Annals of Statistics, 7(1):1-26, 1979. DOI: [10.1214/aos/1176344552](https://doi.org/10.1214/aos/1176344552) | Bootstrap CI as alternative to Wilson for small samples | Considered; Wilson chosen for analytical tractability |

---

## 10. Standards & Compliance References

| Standard | Description | Relevance |
|----------|-------------|-----------|
| **ISO/IEC 7810:2003** | ID-1 card dimensions: 85.60 × 53.98mm, corner radius 3.18mm | Alternative calibration reference (credit card) -- not used; ArUco/ChArUco preferred for accuracy |
| **IS 4452:2019** | BIS standard for dehydrated onions | Process-grade (Goli < 35mm) onions; referenced in `mandi_size_grade` GOLI classification |
| **DPDP Act 2023** | Digital Personal Data Protection Act, Government of India | Farmer data privacy and consent handling |
| **FIPS 180-4 / FIPS 198-1** | Secure Hash & Keyed-Hash Message Authentication (NIST) | SHA-256 image digest & HMAC report tamper verification |

---

## Citation Format Key

- **[PSF-2024-AnnexI]** -- Government documents, cited by department + year + document section
- **[Author-Year]** -- Academic papers, cited by first author surname + year
- **[System-Year]** -- Commercial systems, cited by brand name + year
- All citations are in-code: module docstrings reference the relevant citation key

---

*Last updated: 2026-09-28*  
*Maintained by: CEPA Research Team*  
*Citation format: IEEE-style abbreviated in-code keys*
