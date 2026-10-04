# ADR-0002: Sovereign HMAC-SHA256 Cryptographic Seal Binding

## Status
Accepted

## Date
2026-10-01 (Updated 2026-10-04)

## Context
In government buffer stock procurement under the NAFED Price Stabilisation Fund (PSF), quality assaying certificates determine whether a 50-quintal consignment receives full Minimum Support Price (MSP) payout (e.g. ₹2,410/qtl) or suffers FAQ dockage deductions (up to -₹480/qtl) or total rejection.

Vulnerabilities in previous manual or non-cryptographic digital systems:
1. **Post-Issuance Tampering**: An adversary modifies database rows or PDF values after grading to inflate grade percentages.
2. **Photo Substitution**: An officer captures a clean reference tray, gets certified Grade A, and substitutes photos of a rotted lot.
3. **Truncated Hash Invalidation**: Truncating 64-character hashes to 32 characters prevents public independent SHA-256 validation.
4. **Credential Collision**: Using the same secret key for API authentication and HMAC signing enables any client with an API token to forge cryptographic seals.

## Decision
We implement a **FIPS 198-1 Compliant Sovereign Cryptographic Seal Chain**:

1. **Independent Key Architecture**:
   - `HMAC_SEAL_SECRET_KEY` is decoupled from `OFFICER_API_KEY`.
   - The seal key is generated as a high-entropy 256-bit secret stored securely in environment variables and never leaked to mobile client bundles.

2. **Seal Payload Composition**:
   The seal is computed across a canonical pipe-delimited digest:
   $$\text{CanonicalString} = H(\text{ImageFile}) \parallel \text{LotID} \parallel \text{GradeA\%} \parallel \text{URS\%} \parallel \text{Reject\%} \parallel \text{NetPayoutRate} \parallel \text{OfficerID} \parallel \text{FinalizedAt}$$
   $$\text{Seal} = \text{HMAC-SHA256}(K_{\text{seal}}, \; \text{CanonicalString})$$

3. **Disk Photo Hash Binding**:
   - $H(\text{ImageFile})$ is the real cryptographic SHA-256 digest of the raw optical tray image on physical storage (`storage/images/<filename>`).
   - If the image file has been evicted on ephemeral container restarts, the seal computation flags `PHOTO_RECORDED_FILE_EVICTED` rather than fabricating synthetic hashes. If missing entirely, status becomes `INVALID_MISSING_PHOTO`.

4. **Persistence & Verification Endpoint**:
   - The computed 64-character hex signature is stored in the database column `reports.cryptographic_seal` at finalize time.
   - A public tamper-audit endpoint (`GET /api/v1/reports/{id}/verify`) recomputes the signature from canonical fields and returns both structured JSON and a responsive HTML verification view.

## Consequences

### Positive
- Tamper-evident integrity: Neither farmers, officers, nor traders can alter certificates undetected (asymmetric Ed25519 signatures planned for legal non-repudiation).
- Direct QR code verification by gate personnel without requiring database write credentials.
- Works offline on field tablets using stored HMAC verification tokens.

### Negative / Trade-offs
- If an optical photo is deleted from disk without a persistent volume mount, re-verifying the photo digest will flag the file as evicted.
