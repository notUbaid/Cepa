# ADR-0006: Asymmetric Ed25519 Digital Seals for Legal Non-Repudiation

## Status
Accepted

## Date
2026-10-05

## Context
In CEPA's initial implementation (ADR-0002), inspection certificates and evidence manifests were sealed using server-side HMAC-SHA256 message authentication codes. While HMAC-SHA256 provides strong tamper-evidence against post-issuance database tampering, it is a symmetric primitive:
1. **Lack of Non-Repudiation**: Verification requires knowing the symmetric secret key. Exposing the key to external verifiers (banks, e-NAM mandi operators, interstate buyers) would enable those third parties to forge valid seals.
2. **Centralized Verification Dependency**: External parties who do not hold the secret key must query CEPA's server verification endpoint (`/api/v1/reports/{id}/verify`), making offline or decentralized verification impossible.
3. **Statutory Admissibility**: Under the Indian Information Technology Act (2000, Section 3) and electronic evidence admissibility standards, legal non-repudiation requires asymmetric public-key cryptography where only the certifier possesses the private signing key.

## Decision
We implement **RFC 8032 Ed25519 Asymmetric Digital Seals** over RFC 8785 canonical evidence manifests:

1. **Cryptographic Algorithm**:
   - Signature Scheme: Ed25519 (Edwards-curve Digital Signature Algorithm using SHA-512 and Curve25519).
   - Key Size: 32-byte public key (64 hex characters), 32-byte private key.
   - Signature Size: 64 bytes (128 hex characters), offering constant-time operation and immune resistance to side-channel timing attacks.

2. **Signing Pipeline**:
   $$\text{Manifest} = \text{CanonicalJSON}(\text{Inspection}, \text{Provenance}, \text{Samples}, \text{Bulbs})$$
   $$\text{Digest} = \text{SHA-256}(\text{Manifest})$$
   $$\text{Signature}_{\text{Ed25519}} = \text{Ed25519-Sign}(K_{\text{private}}, \; \text{Digest})$$

3. **Public Key Discovery**:
   - The root public verification key is exposed at `GET /api/v1/.well-known/cepa-public-key` in both raw hex and RFC 5280 SubjectPublicKeyInfo PEM format.
   - Any third-party system (e-NAM gateway, cold storage operator, commercial bank disbursement portal) can fetch or pin this public key and verify certificate signatures completely offline without contacting CEPA's backend.

4. **Backwards Compatibility**:
   - The system maintains backwards-compatible dual verification:
     - Signatures prefixed with `ED25519:` or 128 hex characters are verified via Ed25519 asymmetric public-key validation.
     - 64 hex character signatures are verified via HMAC-SHA256.
     - Historical CEPA-SEAL-V2 pipe-delimited HMAC payloads remain verifiable for archived certificates.

## Consequences

### Positive
- **True Legal Non-Repudiation**: The assaying authority cannot deny having issued the certificate, and no external party with access to verification keys can forge an inspection.
- **Offline Decentralized Verification**: Mandi gates, border checkpoints, and rural warehouses with zero cellular connectivity can verify paper QR codes using pinned public keys.
- **High Performance**: Ed25519 signing and verification execute in sub-millisecond time on low-cost edge CPU hardware without GPU acceleration.

### Negative / Trade-offs
- Private key security requires strict environment isolation (`CEPA_ED25519_PRIVATE_KEY` / HSM integration in production cloud deployments).
