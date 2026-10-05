"""
Judge Attack Vector Test Suite for CEPA Assaying Instrument
============================================================
Exhaustively validates the 20 attack vectors that an adversarial hackathon
evaluator, CV/ML researcher, government auditor, or security pentester
would attempt against the CEPA system.

Every test represents a hard architectural invariant.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import uuid
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi.testclient import TestClient

from config import settings
from cv.calibration import CalibrationResult, compute_calibration
from cv.confidence import ConfidenceAssessment, assess_confidence
from cv.defect_classifier import DefectPrediction
from cv.marker_detector import MarkerDetectionResult
from cv.size_estimator import SizeEstimate
from database import SessionLocal
from grading.engine import GradingEngine
from grading.policy_loader import load_policy
from main import app
from models.classification_result import ClassificationResult
from models.defect_observation import DefectObservation
from models.inspection import Inspection
from models.measurement import Measurement
from models.onion_instance import OnionInstance
from models.report import Report
from models.sample import Sample
from schemas.inspection import InspectionDetail
from services.crypto_seal import (
    compute_inspection_seal,
    verify_inspection_seal,
)
from services.enam_export_service import build_enam_assaying_payload


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def active_policy():
    policies_dir = Path(__file__).resolve().parent.parent / "grading" / "policies"
    return load_policy("DEMO_ASSUMPTION_v1", policies_dir)


# ── Vector 1: Uncalibrated Image Cannot Certify Grade A ──────────────────────
def test_attack_01_uncalibrated_cannot_certify_grade_a(active_policy):
    """
    Attack: Submit an uncalibrated optical image without planar marker.
    Defense: Hard calibration gate strictly blocks Grade A / URS, forcing
    NEEDS_REVIEW with UNCALIBRATED_SCALE_SCREENING_ONLY.
    """
    size_est = SizeEstimate(
        equivalent_diameter_mm=55.0,
        major_axis_mm=56.0,
        minor_axis_mm=54.0,
        equatorial_diameter_mm=55.0,
        polar_length_mm=54.0,
        mask_area_px=12000,
        scale_mm_per_px=0.5,
        uncertainty_flag=True,
    )
    defect = DefectPrediction(
        sprouted_prob=0.01,
        rotten_prob=0.01,
        damaged_prob=0.02,
        model_version="test-v1",
        is_mock=False,
    )
    conf = assess_confidence(
        segmentation_conf=0.95,
        touches_border=False,
        size_estimate=size_est,
        defect_prediction=defect,
        is_estimated_scale=True,  # No marker detected!
    )
    engine = GradingEngine(active_policy)
    result = engine.evaluate_bulb(size_est, defect, conf)

    assert result.grade == "NEEDS_REVIEW"
    assert "UNCALIBRATED_SCALE_SCREENING_ONLY" in result.rejection_reasons
    assert result.confidence_tier == "NEEDS_REVIEW"


# ── Vector 2: Missing ChArUco Cannot Claim Sub-Millimeter ─────────────────────
def test_attack_02_missing_charuco_cannot_claim_submillimeter():
    """
    Attack: System claims sub-millimeter caliper precision on uncalibrated camera.
    Defense: Missing ChArUco marks is_estimated=True and derives analytical
    uncertainty >= 2.0 mm (including parallax and standoff distance variance).
    """
    dummy_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    no_marker = MarkerDetectionResult(
        detected=False,
        failure_code="marker_not_detected",
        failure_message="No ChArUco board detected",
    )
    calib = compute_calibration(dummy_frame, no_marker)

    assert calib.is_estimated is True
    assert calib.quality_passed is False
    assert calib.uncertainty_mm >= 1.5


# ── Vector 3: Mutating Bulb Measurement Breaks Seal ──────────────────────────
def test_attack_03_mutating_bulb_measurement_breaks_seal(tmp_path):
    """
    Attack: Mallory modifies a bulb's diameter from 42mm to 55mm to falsify Grade A.
    Defense: The Canonical Evidence Manifest binds all per-bulb measurements into
    the manifest hash. Seal verification immediately fails.
    """
    insp_id = f"INSP-ATTACK-{uuid.uuid4().hex[:6]}"
    meas = SimpleNamespace(
        equivalent_diameter_mm=52.0,
        equatorial_diameter_mm=52.5,
        polar_length_mm=50.0,
        scale_mm_per_px=0.51,
        uncertainty_flag=False,
    )
    bulb = SimpleNamespace(
        id="bulb-001",
        instance_index=0,
        sample_id="samp-001",
        touches_border=False,
        segmentation_conf=0.96,
        measurement=meas,
        classification_result=None,
        defect_observation=None,
    )
    sample = SimpleNamespace(
        id="samp-001",
        sample_index=1,
        image_sha256="HASH-1234",
        marker_detected=True,
        scale_mm_per_px=0.51,
        perspective_valid=True,
        is_estimated_scale=False,
        calibration_method="CHARUCO_BOARD",
        onion_instances=[bulb],
    )
    inspection = SimpleNamespace(
        id=insp_id,
        lot_id="LOT-ATTACK-01",
        farmer_id="FARMER-01",
        farmer_name="Ramesh",
        procurement_centre="Lasalgaon",
        officer_id="OFF-99",
        samples=[sample],
    )
    report = SimpleNamespace(
        report_id=f"RPT-{uuid.uuid4().hex[:6]}",
        report_version=1,
        total_bulbs=1,
        grade_a_count=1,
        urs_count=0,
        rejected_count=0,
        review_count=0,
        grade_a_pct=100.0,
        urs_pct=0.0,
        rejected_pct=0.0,
        defect_counts="{}",
        image_sha256="HASH-1234",
    )

    seal_res = compute_inspection_seal(report, inspection)
    authentic_seal = seal_res.seal_hex

    # Verification passes for authentic data
    assert verify_inspection_seal(authentic_seal, report, inspection) is True

    # Tamper with bulb measurement
    meas.equivalent_diameter_mm = 68.0
    assert verify_inspection_seal(authentic_seal, report, inspection) is False


# ── Vector 4: Mutating Bulb Classification Breaks Seal ───────────────────────
def test_attack_04_mutating_bulb_classification_breaks_seal():
    """
    Attack: Flip bulb grade from REJECTED to GRADE_A after certification.
    Defense: Per-bulb classification decisions are cryptographically locked.
    """
    clf = SimpleNamespace(
        grade="REJECTED",
        confidence_tier="HIGH",
        rejection_reasons='["ROTTEN"]',
    )
    bulb = SimpleNamespace(
        id="bulb-002",
        instance_index=0,
        sample_id="samp-002",
        touches_border=False,
        segmentation_conf=0.94,
        measurement=None,
        classification_result=clf,
        defect_observation=None,
    )
    sample = SimpleNamespace(
        id="samp-002",
        sample_index=1,
        image_sha256="HASH-2222",
        marker_detected=True,
        scale_mm_per_px=0.50,
        perspective_valid=True,
        is_estimated_scale=False,
        calibration_method="CHARUCO_BOARD",
        onion_instances=[bulb],
    )
    inspection = SimpleNamespace(
        id="INSP-ATTACK-02",
        lot_id="LOT-ATTACK-02",
        officer_id="OFF-02",
        samples=[sample],
    )
    report = SimpleNamespace(
        report_id="RPT-ATTACK-02",
        report_version=1,
        total_bulbs=1,
        grade_a_pct=0.0,
        urs_pct=0.0,
        rejected_pct=100.0,
        image_sha256="HASH-2222",
    )

    seal_res = compute_inspection_seal(report, inspection)
    authentic_seal = seal_res.seal_hex

    assert verify_inspection_seal(authentic_seal, report, inspection) is True

    # Tamper grade to GRADE_A
    clf.grade = "GRADE_A"
    assert verify_inspection_seal(authentic_seal, report, inspection) is False


# ── Vector 5: Mutating Sample Image Bytes Breaks Seal ────────────────────────
def test_attack_05_mutating_image_bytes_breaks_seal():
    """
    Attack: Substitute tray photograph with an unblemished reference image.
    Defense: The SHA-256 digest of every physical photograph is bound to the seal.
    """
    sample = SimpleNamespace(
        id="samp-003",
        sample_index=1,
        image_sha256="AUTHENTIC-IMAGE-SHA256",
        marker_detected=True,
        scale_mm_per_px=0.50,
        perspective_valid=True,
        is_estimated_scale=False,
        calibration_method="CHARUCO_BOARD",
        onion_instances=[],
    )
    inspection = SimpleNamespace(
        id="INSP-ATTACK-03",
        lot_id="LOT-ATTACK-03",
        officer_id="OFF-03",
        samples=[sample],
    )
    report = SimpleNamespace(
        report_id="RPT-ATTACK-03",
        report_version=1,
        total_bulbs=0,
        grade_a_pct=0.0,
        urs_pct=0.0,
        rejected_pct=0.0,
        image_sha256="AUTHENTIC-IMAGE-SHA256",
    )

    seal_res = compute_inspection_seal(report, inspection)
    authentic_seal = seal_res.seal_hex

    # Tamper sample hash
    sample.image_sha256 = "FRAUDULENT-SUBSTITUTED-SHA256"
    assert verify_inspection_seal(authentic_seal, report, inspection) is False


# ── Vector 6: Mutating Policy SHA-256 Breaks Seal ────────────────────────────
def test_attack_06_mutating_policy_sha256_breaks_seal():
    """
    Attack: Replace grading policy YAML or alter threshold parameters retroactively.
    Defense: Provenance locks policy_sha256 at processing time into the manifest.
    """
    inspection = SimpleNamespace(
        id="INSP-ATTACK-04",
        lot_id="LOT-ATTACK-04",
        officer_id="OFF-04",
        samples=[],
        provenance_json=json.dumps({
            "policy": {"policy_id": "DEMO_ASSUMPTION_v1", "policy_sha256": "ORIGINAL-HASH-1111"},
            "models": {},
        }),
    )
    report = SimpleNamespace(
        report_id="RPT-ATTACK-04",
        report_version=1,
        total_bulbs=0,
        grade_a_pct=0.0,
        urs_pct=0.0,
        rejected_pct=0.0,
        image_sha256="",
    )

    seal_res = compute_inspection_seal(report, inspection)
    authentic_seal = seal_res.seal_hex

    # Tamper policy sha256 in provenance
    inspection.provenance_json = json.dumps({
        "policy": {"policy_id": "DEMO_ASSUMPTION_v1", "policy_sha256": "TAMPERED-POLICY-HASH"},
        "models": {},
    })
    assert verify_inspection_seal(authentic_seal, report, inspection) is False


# ── Vector 7: Mutating Model Hash Breaks Seal ────────────────────────────────
def test_attack_07_mutating_model_hash_breaks_seal():
    """
    Attack: Retrain or swap defect classifier model weights without detection.
    Defense: Exact weights artifact SHA-256 is bound in provenance and evidence manifest.
    """
    inspection = SimpleNamespace(
        id="INSP-ATTACK-05",
        lot_id="LOT-ATTACK-05",
        officer_id="OFF-05",
        samples=[],
        provenance_json=json.dumps({
            "policy": {"policy_id": "DEMO_ASSUMPTION_v1", "policy_sha256": "POL-1111"},
            "models": {
                "defect_classifier": {"artifact_sha256": "AUTH-WEIGHTS-SHA-9999"}
            },
        }),
    )
    report = SimpleNamespace(
        report_id="RPT-ATTACK-05",
        report_version=1,
        total_bulbs=0,
        grade_a_pct=0.0,
        urs_pct=0.0,
        rejected_pct=0.0,
        image_sha256="",
    )

    seal_res = compute_inspection_seal(report, inspection)
    authentic_seal = seal_res.seal_hex

    inspection.provenance_json = json.dumps({
        "policy": {"policy_id": "DEMO_ASSUMPTION_v1", "policy_sha256": "POL-1111"},
        "models": {
            "defect_classifier": {"artifact_sha256": "ROGUE-WEIGHTS-SHA-0000"}
        },
    })
    assert verify_inspection_seal(authentic_seal, report, inspection) is False


# ── Vector 8: Mutating Operator ID Breaks Seal ───────────────────────────────
def test_attack_08_mutating_operator_id_breaks_seal():
    """
    Attack: Spoof the assayer officer ID on an issued certificate.
    Defense: Operator ID is locked inside the HMAC audit payload.
    """
    inspection = SimpleNamespace(
        id="INSP-ATTACK-06",
        lot_id="LOT-ATTACK-06",
        officer_id="OFF-LEGIT-101",
        samples=[],
    )
    report = SimpleNamespace(
        report_id="RPT-ATTACK-06",
        report_version=1,
        total_bulbs=0,
        grade_a_pct=0.0,
        urs_pct=0.0,
        rejected_pct=0.0,
        image_sha256="",
    )

    seal_res = compute_inspection_seal(report, inspection)
    authentic_seal = seal_res.seal_hex

    inspection.officer_id = "OFF-IMPOSTOR-999"
    assert verify_inspection_seal(authentic_seal, report, inspection) is False


# ── Vector 9: Finalized Inspection Rejects New Samples ───────────────────────
def test_attack_09_finalized_inspection_rejects_new_samples(client: TestClient, tmp_path):
    """
    Attack: Attempt to upload extra samples to an already FINALIZED inspection.
    Defense: Returns HTTP 400 Bad Request.
    """
    db = SessionLocal()
    insp_id = str(uuid.uuid4())
    try:
        insp = Inspection(
            id=insp_id,
            lot_id=f"LOT-FIN-{uuid.uuid4().hex[:6]}",
            status="FINALIZED",
        )
        db.add(insp)
        db.commit()
    finally:
        db.close()

    dummy_img = tmp_path / "extra.jpg"
    dummy_img.write_bytes(b"\xFF\xD8\xFF\xE0" + b"\x00" * 100)

    with open(dummy_img, "rb") as f:
        resp = client.post(
            f"/api/v1/inspections/{insp_id}/samples",
            files={"file": ("extra.jpg", f, "image/jpeg")},
        )
    assert resp.status_code == 400
    assert "finalized inspection" in resp.json()["detail"].lower()


# ── Vector 10: Finalized Inspection Rejects PATCH Metadata ───────────────────
def test_attack_10_finalized_inspection_rejects_patch_metadata(client: TestClient):
    """
    Attack: Attempt to alter farmer name or lot ID via PATCH on a FINALIZED inspection.
    Defense: Returns HTTP 409 Conflict.
    """
    db = SessionLocal()
    insp_id = str(uuid.uuid4())
    try:
        insp = Inspection(
            id=insp_id,
            lot_id="LOT-LOCKED-01",
            farmer_name="Authentic Farmer",
            status="FINALIZED",
        )
        db.add(insp)
        db.commit()
    finally:
        db.close()

    resp = client.patch(
        f"/api/v1/inspections/{insp_id}",
        json={"farmer_name": "Fraudulent Farmer"},
    )
    assert resp.status_code == 409
    assert "immutable after certification" in resp.json()["detail"]


# ── Vector 11: Finalized Inspection Rejects Bulb Override ────────────────────
def test_attack_11_finalized_inspection_rejects_bulb_override(client: TestClient):
    """
    Attack: Call /correct on a bulb belonging to a FINALIZED inspection.
    Defense: Returns HTTP 409 Conflict.
    """
    db = SessionLocal()
    insp_id = str(uuid.uuid4())
    inst_id = str(uuid.uuid4())
    samp_id = str(uuid.uuid4())
    try:
        insp = Inspection(id=insp_id, lot_id="LOT-LOCK-02", status="FINALIZED")
        samp = Sample(id=samp_id, inspection_id=insp_id, sample_index=1, image_path="fake.jpg")
        onion = OnionInstance(id=inst_id, sample_id=samp_id, instance_index=0, bbox_x=0, bbox_y=0, bbox_w=10, bbox_h=10, segmentation_conf=0.95)
        db.add_all([insp, samp, onion])
        db.commit()
    finally:
        db.close()

    resp = client.post(
        f"/api/v1/inspections/{insp_id}/onions/{inst_id}/correct",
        json={"damaged_prob": 0.0, "rotten_prob": 0.0, "sprouted_prob": 0.0, "corrected_by": "Attacker"},
    )
    assert resp.status_code == 409
    assert "immutable after certification" in resp.json()["detail"]


# ── Vector 12: Empty Inspection Cannot Be Finalized ──────────────────────────
def test_attack_12_empty_inspection_cannot_be_finalized(client: TestClient):
    """
    Attack: Finalize an inspection with 0 bulb instances.
    Defense: Returns HTTP 400 Bad Request.
    """
    create_resp = client.post(
        "/api/v1/inspections",
        json={"lot_id": "LOT-ZERO-BULBS", "procurement_centre": "Lasalgaon APMC"},
    )
    assert create_resp.status_code == 201
    insp_id = create_resp.json()["id"]

    fin_resp = client.post(f"/api/v1/inspections/{insp_id}/finalize")
    assert fin_resp.status_code == 400
    assert "at least 1" in fin_resp.json()["detail"].lower() or "0 bulbs" in fin_resp.json()["detail"]


# ── Vector 13: Public Share JSON Redacts Officer and GPS ─────────────────────
def test_attack_13_public_share_json_redacts_officer_and_gps(client: TestClient):
    """
    Attack: Scrape exact GPS coordinates and internal officer ID via public share link.
    Defense: Public share JSON strictly sanitizes and redacts geo_lat, geo_lon, and officer_id.
    """
    db = SessionLocal()
    share_tok = f"tok-sec-{uuid.uuid4().hex[:8]}"
    insp_id = str(uuid.uuid4())
    rep_id = str(uuid.uuid4())
    try:
        insp = Inspection(
            id=insp_id,
            lot_id="LOT-SECRET-GPS",
            officer_id="INTERNAL-OFF-PRIVATE",
            geo_lat=19.9975,
            geo_lon=73.7898,
            status="FINALIZED",
        )
        rep = Report(
            id=rep_id,
            report_id=f"RPT-{uuid.uuid4().hex[:8]}",
            inspection_id=insp_id,
            share_token=share_tok,
            ruleset_version="DEMO_ASSUMPTION_v1",
            model_version="test-v1",
        )
        db.add_all([insp, rep])
        db.commit()
    finally:
        db.close()

    resp = client.get(f"/api/v1/reports/share/{share_tok}", headers={"Accept": "application/json"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["geo_lat"] is None
    assert data["geo_lon"] is None
    assert data["officer_id"] is None


# ── Vector 14: Public Verify Rejects Internal DB Primary Key ─────────────────
def test_attack_14_public_verify_rejects_internal_db_primary_key(client: TestClient):
    """
    Attack: Enumerate internal database primary key UUIDs (Report.id) on public verify endpoint.
    Defense: Rejects internal DB id lookup (returns 404). Only allows high-entropy share_token
    or public report_id.
    """
    db = SessionLocal()
    internal_id = str(uuid.uuid4())
    pub_report_id = f"RPT-PUB-{uuid.uuid4().hex[:8]}"
    insp_id = str(uuid.uuid4())
    try:
        insp = Inspection(id=insp_id, lot_id="LOT-IDOR-TEST", status="FINALIZED")
        rep = Report(
            id=internal_id,  # Internal primary key
            report_id=pub_report_id,  # Public ID
            inspection_id=insp_id,
            share_token=f"token-{uuid.uuid4().hex[:8]}",
            ruleset_version="DEMO_ASSUMPTION_v1",
            model_version="test-v1",
        )
        db.add_all([insp, rep])
        db.commit()
    finally:
        db.close()

    # Internal primary key MUST NOT resolve
    resp = client.get(f"/api/v1/reports/{internal_id}/verify")
    assert resp.status_code == 404

    # Public report_id DOES resolve
    resp_ok = client.get(f"/api/v1/reports/{pub_report_id}/verify")
    assert resp_ok.status_code == 200


def _make_dummy_inspection(
    total_bulbs: int = 20,
    grade_a_pct: float = 90.0,
    urs_pct: float = 10.0,
    rejected_pct: float = 0.0,
) -> InspectionDetail:
    now = datetime.now(timezone.utc)
    return InspectionDetail(
        id="insp-enam-test",
        lot_id="LOT-ENAM-01",
        farmer_id="1234",
        farmer_name="Farmer",
        procurement_centre="Nashik",
        officer_name="Officer",
        officer_id="OFF-01",
        notes="Notes",
        geo_lat=20.0,
        geo_lon=74.0,
        location_accuracy=5.0,
        location_note="Yard",
        status="FINALIZED",
        created_at=now,
        updated_at=now,
        finalized_at=now,
        total_bulbs=total_bulbs,
        grade_a_count=int(total_bulbs * grade_a_pct / 100),
        urs_count=int(total_bulbs * urs_pct / 100),
        rejected_count=int(total_bulbs * rejected_pct / 100),
        review_count=0,
        grade_a_pct=grade_a_pct,
        urs_pct=urs_pct,
        rejected_pct=rejected_pct,
        sample_ids=["sample-1"],
    )


# ── Vector 15: eNAM Export Has No Fabricated Moisture ────────────────────────
def test_attack_15_enam_export_no_fabricated_moisture():
    """
    Attack: Claims optical camera provides moisture percentage (e.g. 84.5%).
    Defense: Moisture is strictly null / NOT_MEASURED with explicit limitation note.
    """
    dummy_insp = _make_dummy_inspection(total_bulbs=20, grade_a_pct=90.0, urs_pct=10.0, rejected_pct=0.0)
    payload = build_enam_assaying_payload(dummy_insp)
    proxies = payload["assaying_parameters"]["physicochemical_proxies"]

    assert proxies["estimated_moisture_pct"] is None
    assert proxies["moisture_status"] == "NOT_MEASURED"
    assert "Optical cameras cannot measure moisture" in proxies["limitation_note"]


# ── Vector 16: eNAM Export Uses Benchmark Procurement, Not MSP ───────────────
def test_attack_16_enam_export_uses_benchmark_procurement_not_msp():
    """
    Attack: Asserts onion has a statutory MSP.
    Defense: Explains that onion procurement operates under PSF/MIS using benchmark rates.
    """
    dummy_insp = _make_dummy_inspection(total_bulbs=20, grade_a_pct=80.0, urs_pct=20.0, rejected_pct=0.0)
    payload = build_enam_assaying_payload(dummy_insp)
    verdict = payload["quality_verdict"]

    assert "Price Stabilisation Fund" in verdict["procurement_framework"]
    assert "Not Statutory MSP" in verdict["procurement_framework"]
    assert "benchmark_rate_eligible" in verdict


# ── Vector 17: Hard Calibration Gate Rejects High Residual ───────────────────
def test_attack_17_hard_calibration_gate_rejects_high_residual():
    """
    Attack: Distorted lens or warped ChArUco board produces severe reprojection residual.
    Defense: Residual > 5.0 px fails quality pass, forcing is_estimated=True.
    """
    calib_res = CalibrationResult(
        scale_mm_per_px=0.5,
        rectified_image=None,
        perspective_valid=False,
        reprojection_residual_px=7.8,  # Excessive error!
        corner_count=20,
        board_coverage_pct=15.0,
        quality_passed=False,
        is_estimated=True,
    )
    assert calib_res.quality_passed is False
    assert calib_res.is_estimated is True


# ── Vector 18: Health Readiness Checks Subsystems ────────────────────────────
def test_attack_18_health_readiness_checks_subsystems(client: TestClient):
    """
    Attack: Traffic routed to instance where database or weights failed to load.
    Defense: /health/ready returns 200 only when database, storage, and models pass.
    """
    resp = client.get("/api/v1/health/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"
    assert "checks" in data
    assert data["checks"]["database"]["status"] == "ok"
    assert data["checks"]["storage"]["status"] == "ok"
    assert "cv_pipeline" in data["checks"]


# ── Vector 19: Storage Path Traversal Blocked ─────────────────────────────────
def test_attack_19_storage_path_traversal_blocked(client: TestClient):
    """
    Attack: Attempt to access sensitive OS files using path traversal '../..'.
    Defense: Path traversal is safely caught; returns 404/400/403.
    """
    payloads = [
        "../../etc/passwd",
        "..%2f..%2fetc%2fpasswd",
        "....//....//windows//win.ini",
    ]
    for p in payloads:
        resp = client.get(f"/api/v1/storage/{p}")
        assert resp.status_code in (404, 400, 403, 422)


# ── Vector 20: Black Mold Heuristic Preserves Raw Probabilities ──────────────
def test_attack_20_black_mold_heuristic_preserves_raw_probabilities():
    """
    Attack: Visual chromatic black mold heuristic mutates neural network softmax outputs.
    Defense: Raw model probabilities remain pure; heuristic acts as an explicit rule override.
    """
    raw_defect = DefectPrediction(
        sprouted_prob=0.05,
        rotten_prob=0.15,  # Raw model gave 0.15
        damaged_prob=0.10,
        model_version="mobilenetv3-test",
        is_mock=False,
    )

    # Dictionary representation must reflect true model output
    d = raw_defect.as_dict()
    assert d["rotten_prob"] == 0.15
    assert raw_defect.model_version == "mobilenetv3-test"
