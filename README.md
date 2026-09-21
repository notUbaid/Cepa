# Cepa (SIH26031): AI-Powered Onion Quality Inspection & Grading System

Cepa is a realistic proof-of-concept mobile and edge inspection instrument designed for agricultural procurement officers (NAFED, NCCF, APMC mandis). It automates quality grading, defect detection, and millimeter-accurate size estimation using smartphone photography and computer vision.

---

## Key Highlights

- **8-Stage Deterministic Computer Vision Pipeline**: Image quality gating (blur, glare, resolution) $\rightarrow$ Sub-pixel ChArUco scale calibration $\rightarrow$ YOLO11 instance segmentation $\rightarrow$ Crop extraction $\rightarrow$ Multi-label defect classification $\rightarrow$ Equivalent diameter estimation $\rightarrow$ Confidence tiering.
- **Evidence-First Architecture**: Every lot-level grade is traceable to individual bulb crops, binary segmentation masks, and specific rule triggers.
- **Configurable & Versioned Procurement Policies**: Grade A ($45-65\text{ mm}$) and Under Relaxed Specification (URS: $35-70\text{ mm}$) rules reside in versioned YAML files (`backend/grading/policies/`), fully decoupled from the CV models.
- **Transparent Limitations**: Clear notices stating that internal rot is physically undetectable from exterior images and that 2D area-derived diameter is a projected measurement.
- **Turnkey Production PDF Reports**: Comprehensive inspection certificates generated via ReportLab with defect summaries, location metadata, and verification QR/share links.

---

## Quickstart Guide

### 1. Prerequisites
- Python 3.11+
- Node.js 20+ & npm
- Standard printer for A4 ChArUco calibration board

### 2. Backend Setup
```bash
# From repository root
cd backend

# Create .env from template
cp ../.env.example .env

# Install dependencies
pip install -e .

# Run pytest test suite
pytest tests -v

# Start FastAPI server (runs on http://localhost:8000)
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Generate Printable ChArUco Board
```bash
python cv_tools/generate_charuco_board.py
```
This generates:
- `cv_tools/calibration_board/charuco_board_7x5_40mm_A4_printable.pdf`
- Print at 100% scale ("Actual Size", no fit-to-page). Verify that squares measure exactly $40\text{ mm}$ with a physical ruler.

### 4. Run End-to-End Synthetic Demo
```bash
# Generate synthetic test frame
python cv_tools/generate_synthetic_sample.py

# Run API integration test
pytest backend/tests/test_api.py -v
```

---

## System Documentation

- [System Architecture & ADRs](docs/ARCHITECTURE.md)
- [8-Stage CV Pipeline Specification](docs/CV_PIPELINE.md)
- [Grading Engine & NAFED Standards](docs/GRADING_ENGINE.md)
- [Dataset Collection & Retraining Protocol](docs/DATASET.md)
- [Physical & System Limitations](docs/LIMITATIONS.md)

---

## REST API Summary

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/health` | Service liveness & version |
| `GET` | `/api/v1/health/cv` | CV models status & active policy |
| `POST` | `/api/v1/inspections` | Initialize new inspection lot |
| `GET` | `/api/v1/inspections` | List inspection history |
| `POST` | `/api/v1/inspections/{id}/samples` | Upload photo & execute 8-stage CV pipeline |
| `GET` | `/api/v1/inspections/{id}/onions/{onion_id}` | Individual bulb evidence drilldown |
| `POST` | `/api/v1/inspections/{id}/onions/{onion_id}/correct` | Officer manual correction with audit trail |
| `POST` | `/api/v1/inspections/{id}/finalize` | Finalize lot inspection |
| `POST` | `/api/v1/inspections/{id}/reports` | Compile lot statistics & generate PDF |
| `GET` | `/api/v1/reports/share/{token}` | Public read-only report portal |
| `GET` | `/api/v1/inspections/{id}/reports/pdf` | Download official PDF report |

---

## License & Ethics
- **Ultralytics YOLO11**: AGPL-3.0 for open-source academic/hackathon usage.
- **Scientific Integrity**: Cepa explicitly rejects synthetic or falsified AI claims. All mock demo fallbacks are labelled `is_mock=True` throughout the database and user interfaces.
