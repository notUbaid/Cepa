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


def compute_image_sha256(
    inspection: Any, storage_dir: Path | None = None
) -> tuple[str | None, str]:
    """
    Compute the SHA-256 hash of the primary sample image from disk.

    Returns:
        tuple[sha256_hex | None, status_code]
        If file exists and is read successfully: (64-char HEX digest, "VERIFIED_ON_DISK")
        If file is missing or unreadable: (None, "PHOTO_FILE_MISSING")
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
                    digest = hashlib.sha256(f.read()).hexdigest().upper()
                    return digest, "VERIFIED_ON_DISK"
        except Exception as e:
            logger.warning("Could not read image file %s for cryptographic hashing: %s", p, e)

    # Photo missing or inaccessible — never fabricate a dummy valid hash
    return None, "PHOTO_FILE_MISSING"


class SealResult(tuple):
    """
    Two-tuple (seal_hex, image_sha256) for complete backwards compatibility
    with unpacking, while carrying detailed verification metadata.
    """
    seal_hex: str
    image_sha256: str | None
    seal_status: str
    is_photo_verified: bool

    def __new__(
        cls,
        seal_hex: str,
        image_sha256: str | None,
        seal_status: str = "VALID",
        is_photo_verified: bool = True,
    ):
        img_repr = image_sha256 or "PHOTO_MISSING"
        return super().__new__(cls, (seal_hex, img_repr))

    def __init__(
        self,
        seal_hex: str,
        image_sha256: str | None,
        seal_status: str = "VALID",
        is_photo_verified: bool = True,
    ):
        self.seal_hex = seal_hex
        self.image_sha256 = image_sha256
        self.seal_status = seal_status
        self.is_photo_verified = is_photo_verified


def _get_seal_secret_key(secret_key: str | None = None) -> bytes:
    """Obtain the sovereign HMAC seal secret key, distinct from officer authentication token."""
    key_str = (
        secret_key
        or getattr(settings, "hmac_seal_secret_key", None)
        or "cepa-sovereign-seal-secret-2026-v2"
    )
    return key_str.encode("utf-8")


def compute_inspection_seal(
    report: Any,
    inspection: Any,
    storage_dir: Path | None = None,
    secret_key: str | None = None,
) -> SealResult:
    """
    Compute cryptographic HMAC-SHA256 seal and image digest.

    If sample photo is missing from storage, the report is marked INVALID_MISSING_PHOTO
    to prevent false authenticity claims on ephemeral storage.

    Returns:
        SealResult (unpacks as (seal_hex, image_sha256))
    """
    image_sha256, photo_status = compute_image_sha256(inspection, storage_dir)

    # If photo on disk is missing, check if report or sample already has a recorded image digest
    recorded_image_sha256 = getattr(report, "image_sha256", None)
    if not recorded_image_sha256:
        for s in getattr(inspection, "samples", []) or []:
            s_hash = getattr(s, "image_sha256", None)
            if s_hash and len(s_hash) == 64:
                recorded_image_sha256 = s_hash
                break

    if image_sha256 is None and recorded_image_sha256 and len(recorded_image_sha256) == 64:
        # DB preserved the image hash from capture time, but physical photo is gone on disk
        img_payload = recorded_image_sha256
        seal_status = "PHOTO_RECORDED_FILE_EVICTED"
        is_photo_verified = False
    elif image_sha256 is not None:
        img_payload = image_sha256
        seal_status = "VALID"
        is_photo_verified = True
    else:
        img_payload = "PHOTO_MISSING"
        seal_status = "INVALID_MISSING_PHOTO"
        is_photo_verified = False

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
        f"IMG_SHA256:{img_payload}"
    )

    key = _get_seal_secret_key(secret_key)
    seal_hex = hmac.new(key, canonical_payload.encode("utf-8"), hashlib.sha256).hexdigest().upper()

    return SealResult(
        seal_hex=seal_hex,
        image_sha256=image_sha256 or recorded_image_sha256,
        seal_status=seal_status,
        is_photo_verified=is_photo_verified,
    )


def verify_inspection_seal(
    seal_hex: str,
    report: Any,
    inspection: Any,
    storage_dir: Path | None = None,
    secret_key: str | None = None,
    require_photo_on_disk: bool = False,
) -> bool:
    """
    Verify if a given seal matches the recomputed HMAC-SHA256 signature.
    Fails if the seal signature mismatches or if require_photo_on_disk is True and the file is missing.
    """
    res = compute_inspection_seal(report, inspection, storage_dir, secret_key)
    if require_photo_on_disk and not res.is_photo_verified:
        return False
    return hmac.compare_digest(seal_hex.strip().upper(), res.seal_hex)


def audit_inspection_seal(
    report: Any,
    inspection: Any,
    storage_dir: Path | None = None,
    secret_key: str | None = None,
) -> dict[str, Any]:
    """
    Full audit inspection verification returning structured diagnostics.
    """
    computed = compute_inspection_seal(report, inspection, storage_dir, secret_key)
    stored_seal = getattr(report, "cryptographic_seal", None)

    seal_matches = bool(stored_seal and hmac.compare_digest(stored_seal.strip().upper(), computed.seal_hex))
    is_valid = seal_matches and computed.is_photo_verified

    status = "VALID" if is_valid else ("INVALID_MISSING_PHOTO" if not computed.is_photo_verified else "TAMPERED")

    return {
        "is_valid": is_valid,
        "seal_status": status,
        "stored_seal": stored_seal,
        "computed_seal": computed.seal_hex,
        "image_sha256": computed.image_sha256,
        "is_photo_verified_on_disk": computed.is_photo_verified,
        "report_id": getattr(report, "report_id", None),
        "inspection_id": getattr(inspection, "id", None),
        "officer_id": getattr(inspection, "officer_id", None),
        "total_bulbs": getattr(report, "total_bulbs", 0),
        "grade_a_pct": getattr(report, "grade_a_pct", 0.0),
    }
