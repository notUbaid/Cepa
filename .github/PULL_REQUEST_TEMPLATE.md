## Description of Changes
<!-- Provide a clear, concise summary of your changes and motivation. -->

## Architectural Invariants & Quality Gates
Please confirm the following quality gates have been satisfied:
- [ ] **Metrological Invariance**: No hardcoded pixel-to-millimeter scales; uncertainty bounds adhere to ISO/IEC 17025 / GUM criteria ($\pm 0.5\text{ mm}$ with ChArUco, $\pm 5.0\text{ mm}$ heuristic flagged as `NEEDS_REVIEW`).
- [ ] **Cryptographic Integrity**: All finalized certificates include 64-character HMAC-SHA256 signature binding optical photo SHA-256 digest, lot grade distribution, and officer credentials.
- [ ] **Regulatory Alignment**: Sizing classifications match BIS **IS 17912:2022** and NAFED Price Stabilisation Fund FAQ procurement parameters.
- [ ] **Botanical Authentication**: Rejection filters prevent non-onion objects or invalid morphology from receiving valid grades.
- [ ] **Offline Edge Portability**: SQLite transactions utilize WAL mode and busy timeout; no unhandled network crashes on offline mandi tablets.

## Verification Executed
- [ ] Backend test suite: `pytest backend/tests` (Passes 100%)
- [ ] Mobile type check: `cd mobile && npx tsc --noEmit` (0 errors)
- [ ] Code formatting & linting: `ruff check backend/`

## Related Issues / ADRs
Closes #
Relates to ADR:
