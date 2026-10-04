# Architecture Decision Records (ADRs)

This directory contains records of significant technical, mathematical, and architectural decisions made for the **CEPA (Certified and Evidenced Produce Assessment)** platform.

Each record documents the business context, technical trade-offs, decision drivers, and consequences in compliance with modern software engineering best practices.

## Index of Architectural Decisions

| ADR ID | Title | Status | Date | Decision Summary |
|:---|:---|:---:|:---:|:---|
| [**ADR-0001**](0001-hybrid-optical-metrology.md) | Hybrid Optical Metrology & Planar Homography Fallback | **Accepted** | 2026-03-28 | Enforces ChArUco sub-pixel corner refinement for metric millimeter sizing ($U \le \pm 0.5\text{ mm}$); requires explicit fallback state with degradation flag when board is absent. |
| [**ADR-0002**](0002-immutable-hmac-sha256-sovereign-seals.md) | Sovereign HMAC-SHA256 Cryptographic Seal Binding | **Accepted** | 2026-03-29 | Implements FIPS 198-1 HMAC-SHA256 seals binding raw image bytes, metrics, and policy decisions into an unforgeable, verifiable 64-character hex signature. |
| [**ADR-0003**](0003-dual-stage-botanical-segmentation-gate.md) | Dual-Stage Botanical Morphology & Pigment Validation Gate | **Accepted** | 2026-03-30 | Enforces CIELAB anthocyanin pigment barrier and botanical morphology ratio checks to reject non-onion contraband, apples, or foreign objects before classification. |
| [**ADR-0004**](0004-sqlite-wal-concurrency-for-offline-mandi-terminals.md) | SQLite WAL Concurrency & Edge Portability for Mandi Terminals | **Accepted** | 2026-03-30 | Standardizes on SQLite with Write-Ahead Logging (WAL) and synchronous normal mode for zero-overhead local deployment in disconnected rural APMC yards. |
| [**ADR-0005**](0005-prolate-spheroid-allium-cepa-compactness-factor.md) | Prolate Spheroid Model with Empirical 0.93 Compactness Factor | **Accepted** | 2026-04-01 | Replaces naive spherical volume assumption with prolate spheroid geometry ($V = \frac{\pi}{6} L_{\text{polar}} D_{\text{caliper}}^2$) modified by empirical packing compactness $\kappa = 0.93$. |

## Decision Template

ADRs in this repository follow the Michael Nygard format:
1. **Title**: Short noun phrase describing the architectural decision.
2. **Status**: Proposed, Accepted, Superseded, or Deprecated.
3. **Context**: Physical, regulatory, mathematical, and operational constraints motivating the decision.
4. **Decision**: The precise technical choice made, including mathematical invariants and interfaces.
5. **Consequences**: Positive architectural outcomes and acknowledged trade-offs or limitations.
