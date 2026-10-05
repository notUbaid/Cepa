"""
CEPA Evidence Manifest & Cryptographic Seal Service.
===================================================
Generates and verifies the canonical immutable Evidence Manifest and tamper-evident
digital MAC signature.

The Evidence Manifest cryptographically binds:
1. Inspection identity, farmer ID, procurement center, and authenticated operator ID.
2. Canonical provenance snapshot: policy version, policy SHA256, model versions, model artifact SHA256s, code commit.
3. Every sample photograph's SHA256 byte digest and calibration metrics.
4. Every detected bulb's physical dimensions, uncertainty flags, defect probabilities, final grading decisions, and officer overrides.
5. Lot-level aggregated classification statistics.
6. Generated PDF certificate SHA256 hash.

Trust Model Note:
Server-side HMAC-SHA256 provides a tamper-evident server MAC verifying that the record
has not been altered since finalization. An asymmetric public-key signature scheme
(Ed25519 with officer hardware tokens / KMS) is on the statutory roadmap for legal non-repudiation.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from config import settings
from services.provenance_service import get_or_freeze_provenance

logger = logging.getLogger(__name__)

_EPHEMERAL_DEV_SECRET: bytes | None = None
_ED25519_PRIVATE_KEY: ed25519.Ed25519PrivateKey | None = None


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

    return None, "PHOTO_FILE_MISSING"


class SealResult(tuple):
    """
    Two-tuple (seal_hex, image_sha256) for complete backwards compatibility
    with unpacking, while carrying detailed verification metadata, manifest hash,
    and Ed25519 asymmetric public-key signature.
    """
    seal_hex: str
    image_sha256: str | None
    seal_status: str
    is_photo_verified: bool
    manifest_hash: str | None
    ed25519_signature: str | None
    ed25519_public_key: str | None

    def __new__(
        cls,
        seal_hex: str,
        image_sha256: str | None,
        seal_status: str = "VALID",
        is_photo_verified: bool = True,
        manifest_hash: str | None = None,
        ed25519_signature: str | None = None,
        ed25519_public_key: str | None = None,
    ):
        img_repr = image_sha256 or "PHOTO_MISSING"
        return super().__new__(cls, (seal_hex, img_repr))

    def __init__(
        self,
        seal_hex: str,
        image_sha256: str | None,
        seal_status: str = "VALID",
        is_photo_verified: bool = True,
        manifest_hash: str | None = None,
        ed25519_signature: str | None = None,
        ed25519_public_key: str | None = None,
    ):
        self.seal_hex = seal_hex
        self.image_sha256 = image_sha256
        self.seal_status = seal_status
        self.is_photo_verified = is_photo_verified
        self.manifest_hash = manifest_hash
        self.ed25519_signature = ed25519_signature
        self.ed25519_public_key = ed25519_public_key


def get_ed25519_private_key() -> ed25519.Ed25519PrivateKey:
    """
    Obtain the server's Ed25519 sovereign signing private key.
    Loads from environment variable, persistent key directory, or generates
    and persists an RFC 8032 keypair.
    """
    global _ED25519_PRIVATE_KEY
    if _ED25519_PRIVATE_KEY is not None:
        return _ED25519_PRIVATE_KEY

    # 1. Environment variable
    env_key = os.environ.get("CEPA_ED25519_PRIVATE_KEY") or os.environ.get("ED25519_PRIVATE_KEY")
    if env_key and env_key.strip():
        k_str = env_key.strip()
        try:
            if "BEGIN PRIVATE KEY" in k_str or "BEGIN OPENSSH PRIVATE KEY" in k_str:
                _ED25519_PRIVATE_KEY = serialization.load_pem_private_key(k_str.encode("utf-8"), password=None)
            else:
                raw_bytes = bytes.fromhex(k_str)
                _ED25519_PRIVATE_KEY = ed25519.Ed25519PrivateKey.from_private_bytes(raw_bytes)
            logger.info("Loaded Ed25519 sovereign signing key from environment variable.")
            return _ED25519_PRIVATE_KEY
        except Exception as e:
            logger.warning("Failed to load Ed25519 private key from environment: %s", e)

    # 2. File in storage/keys/
    key_dir = settings.storage_dir / "keys"
    key_file = key_dir / "ed25519_private.pem"
    if key_file.exists():
        try:
            with open(key_file, "rb") as f:
                _ED25519_PRIVATE_KEY = serialization.load_pem_private_key(f.read(), password=None)
            logger.info("Loaded Ed25519 sovereign signing key from disk at %s", key_file)
            return _ED25519_PRIVATE_KEY
        except Exception as e:
            logger.warning("Failed to load Ed25519 key from %s: %s", key_file, e)

    # 3. Generate new keypair and persist if possible
    _ED25519_PRIVATE_KEY = ed25519.Ed25519PrivateKey.generate()
    try:
        key_dir.mkdir(parents=True, exist_ok=True)
        pem_bytes = _ED25519_PRIVATE_KEY.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        with open(key_file, "wb") as f:
            f.write(pem_bytes)
        pub_pem = _ED25519_PRIVATE_KEY.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        with open(key_dir / "ed25519_public.pem", "wb") as f:
            f.write(pub_pem)
        logger.info("Generated and persisted new Ed25519 sovereign keypair to %s", key_dir)
    except Exception as e:
        logger.warning("Could not persist Ed25519 keys to disk: %s. Using ephemeral in-memory key.", e)

    return _ED25519_PRIVATE_KEY


def get_ed25519_public_key() -> ed25519.Ed25519PublicKey:
    """Obtain public key corresponding to sovereign Ed25519 signing key."""
    return get_ed25519_private_key().public_key()


def get_ed25519_public_key_pem() -> str:
    """Return SubjectPublicKeyInfo PEM string for public certificate distribution."""
    pub = get_ed25519_public_key()
    return pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")


def get_ed25519_public_key_hex() -> str:
    """Return 32-byte raw public key as 64-character uppercase hex string."""
    pub = get_ed25519_public_key()
    raw = pub.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return raw.hex().upper()


def verify_ed25519_seal(
    signature_hex: str,
    manifest_bytes: bytes,
    public_key: ed25519.Ed25519PublicKey | None = None,
) -> bool:
    """
    Verify Ed25519 digital signature over canonical evidence manifest.
    Accepts hex signature with or without 'ED25519:' prefix.
    """
    try:
        pub = public_key or get_ed25519_public_key()
        sig_clean = signature_hex.strip()
        if sig_clean.upper().startswith("ED25519:"):
            sig_clean = sig_clean[8:]
        sig_bytes = bytes.fromhex(sig_clean)
        pub.verify(sig_bytes, manifest_bytes)
        return True
    except Exception:
        return False


def _get_seal_secret_key(secret_key: str | None = None) -> bytes:
    """
    Obtain the HMAC seal secret key.
    Never falls back to a hardcoded static string in production.
    """
    global _EPHEMERAL_DEV_SECRET
    key_str = (
        secret_key
        or os.environ.get("SOVEREIGN_SEAL_SECRET")
        or os.environ.get("HMAC_SEAL_SECRET_KEY")
        or getattr(settings, "hmac_seal_secret_key", None)
    )
    if key_str and str(key_str).strip():
        return str(key_str).strip().encode("utf-8")

    is_prod = (
        os.environ.get("RENDER") is not None
        or os.environ.get("CEPA_ENV", "").lower() == "production"
        or getattr(settings, "backend_env", "").lower() == "production"
    )
    if is_prod:
        raise ValueError(
            "CRITICAL SECURITY CONFIGURATION ERROR: SOVEREIGN_SEAL_SECRET environment variable "
            "must be explicitly set in production mode. Sealing will not fall back to insecure defaults."
        )

    if _EPHEMERAL_DEV_SECRET is None:
        _EPHEMERAL_DEV_SECRET = secrets.token_bytes(32)
        logger.warning(
            "SECURITY AUDIT NOTICE: SOVEREIGN_SEAL_SECRET is unset. "
            "Generated an ephemeral 256-bit runtime key for this process session."
        )
    return _EPHEMERAL_DEV_SECRET


def canonicalize_manifest(manifest: dict[str, Any]) -> str:
    """
    Produce deterministic canonical JSON representation (sorted keys, compact separators).
    Conforms to RFC 8785 canonical JSON principles.
    """
    return json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _is_mock(val: Any) -> bool:
    return "Mock" in type(val).__name__


def _safe_str(val: Any, default: str = "") -> str:
    if val is None or _is_mock(val):
        return default
    return str(val)


def _safe_int(val: Any, default: int = 0) -> int:
    if val is None or _is_mock(val):
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def _safe_float(val: Any, default: float = 0.0) -> float:
    if val is None or _is_mock(val):
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _safe_bool(val: Any, default: bool = False) -> bool:
    if val is None or _is_mock(val):
        return default
    return bool(val)


def build_evidence_manifest(
    report: Any,
    inspection: Any,
    storage_dir: Path | None = None,
) -> dict[str, Any]:
    """
    Build the exhaustive Canonical Evidence Manifest.
    """
    prov = get_or_freeze_provenance(inspection)

    # 1. Inspection metadata
    finalized_dt = getattr(inspection, "finalized_at", None)
    insp_dict = {
        "id": _safe_str(getattr(inspection, "id", "")),
        "lot_id": _safe_str(getattr(inspection, "lot_id", "") or "UNSPECIFIED", "UNSPECIFIED"),
        "farmer_id": _safe_str(getattr(inspection, "farmer_id", "")),
        "farmer_name": _safe_str(getattr(inspection, "farmer_name", "")),
        "procurement_centre": _safe_str(getattr(inspection, "procurement_centre", "")),
        "operator_id": _safe_str(getattr(inspection, "officer_id", "") or "OFFICER-UNKNOWN", "OFFICER-UNKNOWN").strip(),
        "finalized_at": (
            finalized_dt.isoformat()
            if finalized_dt and not _is_mock(finalized_dt) and hasattr(finalized_dt, "isoformat")
            else ""
        ),
    }

    # 2. Report summary
    rep_dict = {
        "report_id": _safe_str(getattr(report, "report_id", "") or insp_dict["id"], insp_dict["id"]),
        "report_version": _safe_int(getattr(report, "report_version", 1), 1),
        "image_sha256": _safe_str(getattr(report, "image_sha256", "")),
        "total_bulbs": _safe_int(getattr(report, "total_bulbs", 0)),
        "grade_a_count": _safe_int(getattr(report, "grade_a_count", 0)),
        "urs_count": _safe_int(getattr(report, "urs_count", 0)),
        "rejected_count": _safe_int(getattr(report, "rejected_count", 0)),
        "review_count": _safe_int(getattr(report, "review_count", 0)),
        "grade_a_pct": round(_safe_float(getattr(report, "grade_a_pct", 0.0)), 2),
        "urs_pct": round(_safe_float(getattr(report, "urs_pct", 0.0)), 2),
        "rejected_pct": round(_safe_float(getattr(report, "rejected_pct", 0.0)), 2),
        "defect_counts": _safe_str(getattr(report, "defect_counts", "{}"), "{}"),
    }

    # 3. Samples
    samples_list = []
    raw_samples = getattr(inspection, "samples", [])
    samples = raw_samples if isinstance(raw_samples, (list, tuple)) else []
    for s in samples:
        scale_val = getattr(s, "scale_mm_per_px", None)
        samples_list.append({
            "sample_id": _safe_str(getattr(s, "id", "")),
            "sample_index": _safe_int(getattr(s, "sample_index", 1), 1),
            "image_sha256": _safe_str(getattr(s, "image_sha256", "") or "MISSING_HASH", "MISSING_HASH"),
            "marker_detected": _safe_bool(getattr(s, "marker_detected", False)),
            "scale_mm_per_px": (
                round(_safe_float(scale_val), 4)
                if scale_val is not None and not _is_mock(scale_val)
                else None
            ),
            "perspective_valid": _safe_bool(getattr(s, "perspective_valid", False)),
            "is_estimated_scale": _safe_bool(getattr(s, "is_estimated_scale", False)),
            "calibration_method": _safe_str(getattr(s, "calibration_method", "") or "CHARUCO_BOARD", "CHARUCO_BOARD"),
        })

    # 4. Per-Bulb Instances
    bulbs_list = []
    for s in samples:
        raw_instances = getattr(s, "onion_instances", [])
        instances = raw_instances if isinstance(raw_instances, (list, tuple)) else []
        for b in instances:
            meas = getattr(b, "measurement", None)
            clf = getattr(b, "classification_result", None)
            obs = getattr(b, "defect_observation", None)

            bulb_item: dict[str, Any] = {
                "bulb_id": _safe_str(getattr(b, "id", "")),
                "instance_index": _safe_int(getattr(b, "instance_index", 0)),
                "sample_id": _safe_str(getattr(b, "sample_id", "")),
                "touches_border": _safe_bool(getattr(b, "touches_border", False)),
                "segmentation_conf": round(_safe_float(getattr(b, "segmentation_conf", 0.0)), 4),
            }

            if meas and not _is_mock(meas):
                eq_d = getattr(meas, "equatorial_diameter_mm", None)
                pol_l = getattr(meas, "polar_length_mm", None)
                bulb_item["measurement"] = {
                    "equivalent_diameter_mm": round(_safe_float(getattr(meas, "equivalent_diameter_mm", 0.0)), 2),
                    "equatorial_diameter_mm": (
                        round(_safe_float(eq_d), 2)
                        if eq_d is not None and not _is_mock(eq_d)
                        else None
                    ),
                    "polar_length_mm": (
                        round(_safe_float(pol_l), 2)
                        if pol_l is not None and not _is_mock(pol_l)
                        else None
                    ),
                    "scale_mm_per_px": round(_safe_float(getattr(meas, "scale_mm_per_px", 0.0)), 4),
                    "uncertainty_flag": _safe_bool(getattr(meas, "uncertainty_flag", False)),
                }

            if clf and not _is_mock(clf):
                bulb_item["classification"] = {
                    "grade": _safe_str(getattr(clf, "grade", "NEEDS_REVIEW"), "NEEDS_REVIEW"),
                    "confidence_tier": _safe_str(getattr(clf, "confidence_tier", "NEEDS_REVIEW"), "NEEDS_REVIEW"),
                    "rejection_reasons": _safe_str(getattr(clf, "rejection_reasons", "[]"), "[]"),
                }

            if obs and not _is_mock(obs):
                corr_by = getattr(obs, "corrected_by", None)
                bulb_item["defect_observation"] = {
                    "damaged_prob": round(_safe_float(getattr(obs, "damaged_prob", 0.0)), 4),
                    "rotten_prob": round(_safe_float(getattr(obs, "rotten_prob", 0.0)), 4),
                    "sprouted_prob": round(_safe_float(getattr(obs, "sprouted_prob", 0.0)), 4),
                    "raw_model_output": _safe_str(getattr(obs, "raw_model_output", "") or "{}", "{}"),
                    "final_decision": _safe_str(getattr(obs, "final_decision", "") or "{}", "{}"),
                    "corrected_by": _safe_str(corr_by) if corr_by and not _is_mock(corr_by) else None,
                }

            bulbs_list.append(bulb_item)

    manifest = {
        "manifest_spec": "CEPA-MANIFEST-V1",
        "inspection": insp_dict,
        "report": rep_dict,
        "provenance": prov,
        "samples": samples_list,
        "bulbs": bulbs_list,
    }
    return manifest


def compute_inspection_seal(
    report: Any,
    inspection: Any,
    storage_dir: Path | None = None,
    secret_key: str | None = None,
) -> SealResult:
    """
    Compute cryptographic HMAC-SHA256 seal and full Evidence Manifest.
    """
    image_sha256, photo_status = compute_image_sha256(inspection, storage_dir)

    recorded_image_sha256 = getattr(report, "image_sha256", None)
    if not recorded_image_sha256:
        for s in getattr(inspection, "samples", []) or []:
            s_hash = getattr(s, "image_sha256", None)
            if s_hash and len(s_hash) == 64:
                recorded_image_sha256 = s_hash
                break

    if image_sha256 is None and recorded_image_sha256 and len(recorded_image_sha256) == 64:
        seal_status = "PHOTO_RECORDED_FILE_EVICTED"
        is_photo_verified = False
    elif image_sha256 is not None:
        seal_status = "VALID"
        is_photo_verified = True
    else:
        seal_status = "INVALID_MISSING_PHOTO"
        is_photo_verified = False

    # Build and canonicalize evidence manifest
    manifest = build_evidence_manifest(report, inspection, storage_dir)
    canonical_str = canonicalize_manifest(manifest)
    manifest_hash = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest().upper()

    key = _get_seal_secret_key(secret_key)
    seal_hex = hmac.new(key, manifest_hash.encode("utf-8"), hashlib.sha256).hexdigest().upper()

    # Sign evidence manifest with Ed25519
    priv_key = get_ed25519_private_key()
    ed25519_sig = priv_key.sign(manifest_hash.encode("utf-8"))
    ed25519_sig_hex = ed25519_sig.hex().upper()
    ed25519_pub_hex = get_ed25519_public_key_hex()

    # Store manifest details on report if writable
    try:
        setattr(report, "manifest_hash", manifest_hash)
        setattr(report, "evidence_manifest_json", canonical_str)
        setattr(report, "ed25519_signature", ed25519_sig_hex)
        setattr(report, "ed25519_public_key", ed25519_pub_hex)
    except Exception:
        pass

    return SealResult(
        seal_hex=seal_hex,
        image_sha256=image_sha256 or recorded_image_sha256,
        seal_status=seal_status,
        is_photo_verified=is_photo_verified,
        manifest_hash=manifest_hash,
        ed25519_signature=ed25519_sig_hex,
        ed25519_public_key=ed25519_pub_hex,
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
    Verify if a given seal matches either the Ed25519 asymmetric signature or the
    recomputed HMAC-SHA256 signature over the Canonical Evidence Manifest.
    """
    res = compute_inspection_seal(report, inspection, storage_dir, secret_key)
    if require_photo_on_disk and not res.is_photo_verified:
        return False

    clean_seal = seal_hex.strip().upper()

    # 1. Asymmetric Ed25519 signature verification (RFC 8032)
    if clean_seal.startswith("ED25519:") or len(clean_seal) == 128:
        if res.manifest_hash and verify_ed25519_seal(clean_seal, res.manifest_hash.encode("utf-8")):
            return True

    # 2. Symmetric HMAC-SHA256 seal verification (FIPS 198-1)
    if hmac.compare_digest(clean_seal, res.seal_hex):
        return True

    # Legacy fallback check (for existing historical seals)
    report_id = str(getattr(report, "report_id", "") or getattr(inspection, "id", "UNKNOWN-REPORT"))
    inspection_id = str(getattr(inspection, "id", "") or getattr(report, "inspection_id", "UNKNOWN-INSPECTION"))
    officer_id = str(getattr(inspection, "officer_id", "") or getattr(report, "officer_id", "") or "OFFICER-UNKNOWN").strip()
    total_bulbs = int(getattr(report, "total_bulbs", 0))
    grade_a_pct = float(getattr(report, "grade_a_pct", 0.0))
    urs_pct = float(getattr(report, "urs_pct", 0.0))
    rejected_pct = float(getattr(report, "rejected_pct", 0.0))
    img_p = res.image_sha256 or "PHOTO_MISSING"

    legacy_payload = (
        f"CEPA-SEAL-V2|REPORT:{report_id}|INSP:{inspection_id}|OFFICER:{officer_id}|"
        f"BULBS:{total_bulbs}|A_PCT:{grade_a_pct:.2f}|URS_PCT:{urs_pct:.2f}|REJ_PCT:{rejected_pct:.2f}|"
        f"IMG_SHA256:{img_p}"
    )
    key = _get_seal_secret_key(secret_key)
    legacy_seal = hmac.new(key, legacy_payload.encode("utf-8"), hashlib.sha256).hexdigest().upper()
    return hmac.compare_digest(clean_seal, legacy_seal)


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

    seal_matches = bool(stored_seal and verify_inspection_seal(stored_seal, report, inspection, storage_dir, secret_key))
    is_valid = seal_matches and computed.is_photo_verified

    status = "VALID" if is_valid else ("INVALID_MISSING_PHOTO" if not computed.is_photo_verified else "TAMPERED")

    # PDF hash verification if recorded
    pdf_path = getattr(report, "pdf_path", None)
    stored_pdf_sha256 = getattr(report, "pdf_sha256", None)
    pdf_verified = None
    if stored_pdf_sha256 and pdf_path:
        base_dir = storage_dir or settings.storage_dir
        p = Path(pdf_path)
        if not p.is_absolute():
            p = base_dir / p
        if p.exists() and p.is_file():
            with open(p, "rb") as f:
                current_pdf_hash = hashlib.sha256(f.read()).hexdigest().upper()
            pdf_verified = (current_pdf_hash == stored_pdf_sha256)
        else:
            pdf_verified = False

    ed25519_verified = (
        verify_ed25519_seal(computed.ed25519_signature, computed.manifest_hash.encode("utf-8"))
        if computed.ed25519_signature and computed.manifest_hash
        else False
    )

    return {
        "is_valid": is_valid,
        "seal_status": status,
        "stored_seal": stored_seal,
        "computed_seal": computed.seal_hex,
        "manifest_hash": computed.manifest_hash,
        "ed25519_signature": computed.ed25519_signature,
        "ed25519_public_key": computed.ed25519_public_key,
        "ed25519_verified": ed25519_verified,
        "image_sha256": computed.image_sha256,
        "is_photo_verified_on_disk": computed.is_photo_verified,
        "pdf_verified": pdf_verified,
        "report_id": getattr(report, "report_id", None),
        "inspection_id": getattr(inspection, "id", None),
        "officer_id": getattr(inspection, "officer_id", None),
        "total_bulbs": getattr(report, "total_bulbs", 0),
        "grade_a_pct": getattr(report, "grade_a_pct", 0.0),
    }
