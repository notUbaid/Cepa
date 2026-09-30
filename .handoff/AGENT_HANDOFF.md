# CEPA Agent Handoff Document

> **For AI agents resuming this session:** Read this entire file before touching any code.
> Then run `git status` and `pytest backend/tests/ -v --tb=short` to verify current state.
> Do NOT start from scratch — the system is substantially built and verified (152/152 tests passing).

---

## Goal of Next Session

Pick up from the verified, working prototype and advance toward:

1. **Train the real defect classifier** (`cv_tools/train_defect_classifier.py`) on actual onion images collected from APMC mandis to replace the optical ensemble with a fine-tuned MobileNetV3 / EfficientNet model.
2. **Develop AS7341 I2C spectral dongle firmware** (ESP32-based) for the Phase 2 hardware upgrade described in Appendix D of `CEPA_ONION_GRADER_MASTER.md`.
3. **Federated learning client-edge aggregation** (`services/federated_service.py`) for privacy-preserving cross-mandi model updates using Flower / FedProx.

---

## State of Play

### What Is DONE and VERIFIED (152/152 tests passing)

| Component | Status | Evidence |
|-----------|--------|---------|
| FastAPI backend (8-stage CV pipeline) | ✅ Production | `pytest backend/tests/: 152/152 passing` |
| YOLO11s-seg instance segmentation | ✅ Production | `cv/providers/yolo11_provider.py` |
| Watershed fallback segmentation | ✅ Production | `cv/providers/watershed_provider.py` |
| Groq Vision AI fallback + Q&A | ✅ Production | `services/groq_ai_service.py`, `/ask-ai` endpoint |
| ChArUco + ArUco calibration | ✅ Production | `cv/calibration.py`, `cv/marker_detector.py` |
| Defect classifier (optical ensemble) | ✅ Production | `cv/defect_classifier.py` (no mock, real pixel analysis) |
| Anthocyanin CIELAB barrier | ✅ Verified | `single_red_onion.jpg` → rot=0.03, not false-positive |
| Aspergillus niger black mold override | ✅ Production | `cv/advanced_features.py:black_mold_pct` |
| Fitzgibbon ellipse + polar/equatorial sizing | ✅ Production | `cv/size_estimator.py` |
| BIS IS 17912:2022 mandi grade (GOLI/MADHYAM/SUPER/JUMBO) | ✅ Production | `cv/size_estimator.py:mandi_size_grade` |
| Grading engine (NAFED policy) | ✅ Production | `grading/engine.py`, `NAFED_2026_v1.yaml` (verified: true) |
| Acoustic tap hollow-body analysis | ✅ Production | `services/acoustic_service.py`, pipeline integration, `/acoustic` endpoint |
| Bhashini multilingual TTS | ✅ Production | `services/bhashini_service.py`, `/announce` endpoint (7 Indian languages, geofenced) |
| eNAM Assaying Export Service | ✅ Production | `services/enam_export_service.py`, `/enam` endpoint (v2.1 XML & JSON) |
| AgriStack 12-Digit Indian Farmer ID | ✅ Production | Database migrations in `database.py`, models, schemas, and UI strip |
| Flash Proxy Index (FPI) Spectroscopy | ✅ Production | `cv/flash_proxy.py`, `/fpi` endpoint (dual-exposure differential reflectance) |
| Double bulb detection | ✅ Production | `cv/advanced_features.py:is_double_bulb` |
| PDF certificate (ReportLab, QR code) | ✅ Production | `services/report_generator.py` |
| Video sweep inspection | ✅ Production | `services/video_service.py` |
| Web Inspector Studio | ✅ Served | `http://localhost:8000/inspector` (with eNAM, Acoustic Tap, Bhashini, AgriStack) |
| SIH 2026 Presentation Deck | ✅ Served | `http://localhost:8000/deck` (with live engineering metrics) |
| React Native mobile app | ✅ Compiles | `npx tsc --noEmit` → 0 errors |
| E2E live verification | ✅ Passed | `tests/live_e2e_verify.py` |

### What is IN PROGRESS / Next

| Task | Priority | File to Create/Edit |
|------|----------|---------------------|
| Real defect classifier training | HIGH | `cv_tools/train_defect_classifier.py` (exists, needs dataset) |
| AS7341 I2C dongle ESP32 firmware | MEDIUM | `firmware/as7341_dongle/` (spec in master doc Appendix D) |
| Federated learning gradient upload | LOW | `services/federated_service.py` (does not exist) |

### What is Blocked

| Blocker | What It Blocks | Resolution |
|---------|---------------|------------|
| Physical onion dataset (2,000+ images) | Real defect classifier training | Collect 500 bulbs × 4 lighting conditions at APMC centre |
| Groq API key in `.env` | AI Q&A and video synthesis | Add `GROQ_API_KEY=gsk_...` to `backend/.env` |
| YOLO11 weights file | YOLO11 segmentation | Set `YOLO_MODEL_PATH=` in `.env` (auto-downloads if empty) |

---

## Open Decisions

The next agent must resolve these before proceeding:

1. **Training data collection:** Where and when will 500 onion bulbs be photographed? What procurement centre will allow access?
2. **YOLO11 vs YOLOv8:** The codebase references `yolo11_provider.py`. If Ultralytics YOLO11 is not available in the environment, fall back to YOLOv8-seg (`yolov8n-seg.pt`). Check with `python -c "from ultralytics import YOLO"`.
3. **Acoustic module hardware:** Is an external MEMS mic being used, or just the phone's built-in microphone? The built-in mic is sufficient for demo with fingernail tap, but a directional MEMS improves isolation.
4. **Mobile app backend URL:** `CaptureScreen.tsx` has a hardcoded `localhost:8000` URL. For a real device demo, this must be the machine's LAN IP (e.g., `192.168.1.100:8000`).

---

## Skills to Use in Next Session

1. **`exhaustive-implementation`** — Complete implementations only. Never write dummy stubs or `// TODO`.
2. **`systematic-debugging`** — When YOLO11 segmentation returns 0 detections on new image types. Use the 4-phase scientific debugging approach.
3. **`tdd-workflow`** — Write tests before implementing new modules.
4. **`verification-loop`** — Run full verification passes (`pytest backend/tests/`, `npx tsc --noEmit`).
5. **`context7`** — For external APIs, libraries, and frameworks.

---

## Quick Verification Commands

```bash
# 1. Verify backend tests (must show 152 passed)
cd D:\Projects\Cepa\backend
python -m pytest tests/ -v --tb=short

# 2. Verify mobile TypeScript compilation (must show 0 errors)
cd D:\Projects\Cepa\mobile
npx tsc --noEmit

# 3. Check health of live CV components
python -c "from cv.pipeline import run_pipeline; from cv.flash_proxy import compute_flash_proxy_map; from services.acoustic_service import get_analyzer; from services.enam_export_service import COMMODITY_CODE; print('All core modules healthy')"
```

---

## Critical Invariants

1. **No mock shortcuts in production paths** (`DEF_USE_MOCK=false`, `USE_MOCK_CV=false`).
2. **CIELAB Anthocyanin Barrier**: `(a_channel < 136)` in `cv/defect_classifier.py` must stay. Removing it will cause false rot classifications on Nashik Red onions.
3. **Grading Engine Purity**: `grading/engine.py` must NEVER import OpenCV or touch image data directly.
4. **Pipeline Fault Tolerance**: `run_pipeline()` must never raise an unhandled exception — always return a populated `PipelineResult`.
5. **Acoustic & Optical Limitation Statements**: `ACOUSTIC_LIMITATION_STATEMENT` and `FLASH_PROXY_LIMITATION_STATEMENT` must always remain transparent and honest in API responses and UI displays.
