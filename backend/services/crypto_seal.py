"""
CEPA Sovereign Cryptographic Seal Service.

Computes a tamper-evident HMAC-SHA256 digital seal binding:
1. Primary sample image byte digest (SHA-256 of optical capture)
2. Authorized inspecting officer credential (officer_id)
3. Quantitative metrological and defect distribution metrics (total_bulbs, grade_a_pct, urs_pct, rejected_pct)
4. System inspection and report identifiers

This establishes non-repudiation between the physical photo at the APMC mandi,
the assayer officer, and the grading verdict.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
from pathlib import Path
from typing import Any

from config import settings

logger = logging.getLogger(__name__)


def compute_image_sha256(inspection: Any, storage_dir: Path | None = None) -> str:
    """
    Compute the SHA-256 hash of the primary sample image.
    Falls back to a deterministic sample descriptor if file is absent on disk.
    """
    base_dir = storage_dir or settings.storage_dir
    samples = getattr(inspection, "samples", []) or []

    for s in samples:
        img_path = getattr(s, "image_path", None) or getattr(s, "processed_image_path", None)
        if not img_path:
            continue
        p = Path(img_path)
        if not p.is_absolute():
            p = base_dir / p
        try:
            if p.exists() and p.is_file():
                with open(p, "rb") as f:
                    return hashlib.sha256(f.read()).hexdigest().upper()
        except Exception as e:
            logger.warning("Could not read image file %s for cryptographic hashing: %s", p, e)

    # Deterministic fallback fingerprint if image file is not on local disk
    insp_id = str(getattr(inspection, "id", "") or "sample-unidentified")
    sample_count = len(samples) if samples else 1
    fallback_data = f"cepa:optical-capture:{insp_id}:{sample_count}".encode()
    return hashlib.sha256(fallback_data).hexdigest().upper()


def compute_inspection_seal(
    report: Any,
    inspection: Any,
    storage_dir: Path | None = None,
    secret_key: str | None = None,
) -> tuple[str, str]:
    """
    Compute cryptographic HMAC-SHA256 seal and image digest.

    Returns:
        tuple[seal_hex, image_sha256]
        seal_hex: 64-char uppercase hexadecimal HMAC-SHA256 digest
        image_sha256: 64-char uppercase hexadecimal SHA-256 digest of sample photo
    """
    image_sha256 = compute_image_sha256(inspection, storage_dir)

    report_id = str(getattr(report, "report_id", "") or getattr(inspection, "id", "UNKNOWN-REPORT"))
    inspection_id = str(getattr(inspection, "id", "") or getattr(report, "inspection_id", "UNKNOWN-INSPECTION"))
    officer_id = str(getattr(inspection, "officer_id", "") or getattr(report, "officer_id", "") or "OFFICER-UNKNOWN").strip()
    total_bulbs = int(getattr(report, "total_bulbs", 0))
    grade_a_pct = float(getattr(report, "grade_a_pct", 0.0))
    urs_pct = float(getattr(report, "urs_pct", 0.0))
    rejected_pct = float(getattr(report, "rejected_pct", 0.0))

    # Canonical audit payload binding identity, optics, and grading distribution
    canonical_payload = (
        f"CEPA-SEAL-V2|REPORT:{report_id}|INSP:{inspection_id}|OFFICER:{officer_id}|"
        f"BULBS:{total_bulbs}|A_PCT:{grade_a_pct:.2f}|URS_PCT:{urs_pct:.2f}|REJ_PCT:{rejected_pct:.2f}|"
        f"IMG_SHA256:{image_sha256}"
    )

    key = (secret_key or settings.officer_api_key or "cepa-sovereign-seal-secret-2026").encode("utf-8")
    seal_hex = hmac.new(key, canonical_payload.encode("utf-8"), hashlib.sha256).hexdigest().upper()

    return seal_hex, image_sha256


def verify_inspection_seal(
    seal_hex: str,
    report: Any,
    inspection: Any,
    storage_dir: Path | None = None,
    secret_key: str | None = None,
) -> bool:
    """Verify if a given seal matches the recomputed HMAC-SHA256 signature."""
    expected_seal, _ = compute_inspection_seal(report, inspection, storage_dir, secret_key)
    return hmac.compare_digest(seal_hex.strip().upper(), expected_seal)
