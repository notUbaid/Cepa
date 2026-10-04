# Contributing to CEPA

Thank you for contributing to CEPA — the Autonomous Mandi Optical & AI Quality Assaying Platform for Smart India Hackathon 2026.

This document outlines our engineering standards, development lifecycle, and quality verification gates.

---

## 1. Code of Conduct & Core Engineering Tenets

We hold this codebase to uncompromising engineering standards:
- **Zero Mock / Placeholder Rule**: No `// TODO: implement later`, no stub functions returning mock hardcoded percentages, and no artificial constants without empirical physical backing.
- **Metrological Truthfulness**: Never present heuristic estimates as certified measurements. Uncertainty bounds must be stated honestly ($\pm 0.5\text{ mm}$ with ChArUco vs $\pm 5.0\text{ mm}$ autonomous heuristic).
- **Cryptographic Immutability**: All commercial assay certificates must be cryptographically sealed and verifiable offline.

---

## 2. Development Environment Setup

### Prerequisites
- Python 3.11 or 3.12
- Node.js 20 LTS & npm 10+
- OpenCV system dependencies (`libgl1-mesa-glx`, `libglib2.0-0` on Linux)
- Git 2.40+

### Backend Setup
```bash
# 1. Create and activate a virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\Activate.ps1
# On macOS/Linux:
source venv/bin/activate

# 2. Install dependencies in editable mode
pip install -e backend/
pip install -r backend/requirements.txt
pip install pytest pytest-asyncio pytest-cov ruff mypy

# 3. Copy environment template
cp .env.example .env

# 4. Verify backend test suite
pytest backend/tests
```

### Mobile Workstation Setup
```bash
cd mobile
npm install --legacy-peer-deps
npx tsc --noEmit
npx expo start
```

---

## 3. Branching & Commit Conventions

### Branch Naming Conventions
- `feature/<ticket>-<short-description>`: New optical pipelines or UI workflows
- `fix/<ticket>-<short-description>`: Bug remediations and edge case patches
- `metrology/<short-description>`: Calibration, lens distortion, or sizing math updates
- `security/<short-description>`: Cryptographic seals, auth, and penetration patches

### Conventional Commits
All commits must adhere to [Conventional Commits v1.0.0](https://www.conventionalcommits.org/):
```text
feat(cv): implement ChArUco 7x5 sub-pixel corner refinement
fix(seal): bind raw tray photo SHA-256 digest into certificate HMAC
docs(adr): add ADR-0002 for sovereign cryptographic seal chain
test(security): add test suite for replay attacks and tampered seals
```

---

## 4. Pre-Commit Quality Gates

Before submitting a Pull Request, run the complete verification suite locally:

```bash
# 1. Python Linting & Formatting Check
ruff check backend/

# 2. Strict Type Check
mypy backend/routers backend/schemas backend/services backend/cv --ignore-missing-imports

# 3. Pytest Regression Test Suite
pytest backend/tests -v

# 4. Mobile TypeScript Compilation
cd mobile && npx tsc --noEmit
```

---

## 5. Architectural Decision Records (ADRs)

If your pull request introduces an architectural shift (e.g. database migration, new computer vision network, cryptographic protocol adjustment), you must include a new ADR in `docs/adr/` following the MADR template.
