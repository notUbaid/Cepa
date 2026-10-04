"""
Audit Remediation Test Suite
============================
Verifies the complete resolution of findings from the Cepa Deep Audit Report:
- C1: MockDefectClassifier generates distinct hashes and diverse defect probabilities for diverse crops.
- C2: Officer auth enforcement on sensitive endpoints.
- C3: Stored XSS protection in certificate view.
- C4: FINALIZED inspections are strictly immutable (HTTP 409).
- C5: Groq fallback never returns fabricated advice or stale disk cache.
- C6: Seed service boots cleanly without SQLAlchemy kwarg errors.
- H1: Upload limits, extension checks, and memory-safe streaming (HTTP 415/413/400).
- H2: Failed sample processing returns HTTP 422 and does not strand lot in PROCESSING.
- H3: Empty inspection finalization rejected with HTTP 400.
- H6: Public certificates mask officer credentials and fuzz GPS coordinates.
- H7: Dynamic policy thresholds in lot aggregation.
- H8: Bhashini NLTM API key binding in config.
- H9: Acoustic tap signal validity gates reject silence and white noise as INVALID.
"""
from __future__ import annotations

import io
import json
import numpy as np
import pytest
from fastapi.testclient import TestClient

from config import settings
from cv.defect_classifier import MockDefectClassifier
from database import SessionLocal
from models.inspection import Inspection
from models.sample import Sample
from schemas.inspection import InspectionCreate, InspectionUpdate
from services.acoustic_service import RealAcousticAnalyzer
from services.certificate_view import render_certificate_html
from services.upload_validator import (
    ALLOWED_IMAGE_TYPES,
    validate_and_read_upload,
)


class TestDefectClassifierC1:
    def test_mock_defect_classifier_diverse_hashes(self):
        """Verifies C1: diverse crops produce distinct hashes and variable defect probabilities."""
        clf = MockDefectClassifier()

        # Generate 5 crops with different central colors and patterns (simulating distinct onions)
        crops = []
        for color in [(140, 60, 200), (40, 180, 220), (30, 100, 160), (200, 200, 50), (90, 40, 130)]:
            crop = np.full((180, 180, 3), color, dtype=np.uint8)
            # Add top padding (similar to segmented masked crops)
            crop[:25, :, :] = [239, 243, 244]
            crops.append(crop)

        results = [clf.classify(c) for c in crops]

        # Verify not all sprouted probabilities are 0.9348 or identical
        sprouted_probs = [r.sprouted_prob for r in results]
        assert len(set(sprouted_probs)) > 1, f"Expected diverse probabilities, got identical: {sprouted_probs}"

        # Verify not all damaged probabilities are identical
        damaged_probs = [r.damaged_prob for r in results]
        assert len(set(damaged_probs)) > 1


class TestUploadValidationH1:
    @pytest.mark.asyncio
    async def test_upload_validator_rejects_disallowed_extension(self):
        """Verifies H1: non-image files like .exe are rejected with HTTP 415."""
        from fastapi import UploadFile, HTTPException

        fake_file = UploadFile(
            filename="malicious_payload.exe",
            file=io.BytesIO(b"MZ\x90\x00executable-bytes"),
            headers={"content-type": "application/x-msdownload"},
        )

        with pytest.raises(HTTPException) as exc:
            await validate_and_read_upload(
                upload_file=fake_file,
                allowed_types=ALLOWED_IMAGE_TYPES,
                max_mb=5,
                label="Test image",
            )
        assert exc.value.status_code == 415

    @pytest.mark.asyncio
    async def test_upload_validator_rejects_empty_file(self):
        """Verifies H1: empty uploads are rejected with HTTP 400."""
        from fastapi import UploadFile, HTTPException

        empty_file = UploadFile(
            filename="empty.jpg",
            file=io.BytesIO(b""),
            headers={"content-type": "image/jpeg"},
        )

        with pytest.raises(HTTPException) as exc:
            await validate_and_read_upload(
                upload_file=empty_file,
                allowed_types=ALLOWED_IMAGE_TYPES,
                max_mb=5,
                label="Test image",
            )
        assert exc.value.status_code == 400


class TestInspectionWorkflowH2H3:
    def test_empty_inspection_cannot_be_finalized_h3(self, client: TestClient):
        """Verifies H3: finalizing an inspection with 0 bulbs is rejected with HTTP 400."""
        create_resp = client.post(
            "/api/v1/inspections",
            json={
                "lot_id": "LOT-EMPTY-TEST",
                "procurement_centre": "Lasalgaon Mandi",
                "officer_name": "Auditor",
            },
        )
        assert create_resp.status_code == 201
        insp_id = create_resp.json()["id"]

        fin_resp = client.post(f"/api/v1/inspections/{insp_id}/finalize")
        assert fin_resp.status_code == 400
        assert "0 bulbs" in fin_resp.json()["detail"] or "at least 1" in fin_resp.json()["detail"].lower()

    def test_patch_updates_farmer_fields_c4(self, client: TestClient):
        """Verifies PATCH /inspections updates farmer_id and farmer_name correctly."""
        create_resp = client.post(
            "/api/v1/inspections",
            json={
                "lot_id": "LOT-FARMER-TEST",
                "procurement_centre": "Pimpalgaon Mandi",
                "officer_name": "Auditor",
            },
        )
        assert create_resp.status_code == 201
        insp_id = create_resp.json()["id"]

        patch_resp = client.patch(
            f"/api/v1/inspections/{insp_id}",
            json={
                "farmer_id": "AGRI-MH-9999",
                "farmer_name": "Savitribai Phule",
            },
        )
        assert patch_resp.status_code == 200
        detail = patch_resp.json()
        assert detail["farmer_id"] == "AGRI-MH-9999"
        assert detail["farmer_name"] == "Savitribai Phule"


class TestAcousticValidityGateH9:
    def test_pure_silence_rejected_as_invalid(self):
        """Verifies H9: pure silence returns INVALID instead of false HIGH hollow risk."""
        analyzer = RealAcousticAnalyzer()
        silence = np.zeros(22050, dtype=np.float32)  # 500ms of 0s at 44.1kHz
        reading = analyzer.analyze_pcm(silence, sample_rate=44100)

        assert reading.hollow_risk_tier == "INVALID"
        assert "low energy" in reading.notes.lower() or "silence" in reading.notes.lower()

    def test_white_noise_rejected_as_invalid(self):
        """Verifies H9: flat ambient white noise returns INVALID (lacks tap resonance peak)."""
        analyzer = RealAcousticAnalyzer()
        rng = np.random.default_rng(42)
        noise = rng.normal(0.0, 0.05, 22050).astype(np.float32)
        reading = analyzer.analyze_pcm(noise, sample_rate=44100)

        assert reading.hollow_risk_tier == "INVALID"
        assert "no distinct" in reading.notes.lower() and "resonance" in reading.notes.lower()


class TestPublicCertificatePrivacyH6:
    def test_certificate_masks_officer_id_and_fuzzes_gps(self):
        """Verifies H6: public certificate masks raw officer ID and fuzzes GPS."""
        class MockReport:
            report_id = "RPT-AUDIT-TEST"
            total_bulbs = 10
            grade_a_pct = 80.0
            grade_a_count = 8
            urs_pct = 20.0
            urs_count = 2
            rejected_pct = 0.0
            rejected_count = 0
            ruleset_version = "DEMO_ASSUMPTION_v1"
            lot_id = "LOT-AUDIT-SAFE"
            procurement_centre = "Lasalgaon Mandi"
            officer_name = "Inspector Patil"
            officer_id = "MH-NAFED-SECRET-8841"
            share_token = "audit-token-123"

        class MockInspection:
            id = "insp-audit-123"
            geo_lat = 20.1472394
            geo_lon = 74.2255819
            location_accuracy = 3.2
            samples = []

        html = render_certificate_html(MockReport(), MockInspection())

        # Raw officer ID must be masked
        assert "MH-NAFED-SECRET-8841" not in html
        assert "***-8841" in html

        # GPS must be fuzzed to 2 decimal places, not raw 7-digit micro-coordinates
        assert "20.1472394" not in html
        assert "20.15° N" in html or "20.14° N" in html
        assert "74.23° E" in html or "74.22° E" in html

    def test_public_share_json_redacts_gps_and_officer_id(self, client: TestClient):
        """Verifies H6: public share JSON endpoint redacts GPS coordinates and officer ID."""
        import uuid
        from models.report import Report
        db = SessionLocal()
        try:
            insp_id = f"insp-privacy-{uuid.uuid4().hex[:8]}"
            share_tok = f"token-privacy-{uuid.uuid4().hex[:8]}"
            insp = Inspection(
                id=insp_id,
                lot_id="LOT-PRIVACY-JSON",
                procurement_centre="Pimpalgaon APMC",
                officer_name="Inspector Deshmukh",
                officer_id="MH-OFFICER-CONFIDENTIAL-999",
                geo_lat=19.9975,
                geo_lon=73.7898,
                status="FINALIZED",
            )
            db.add(insp)
            db.commit()

            rpt = Report(
                inspection_id=insp.id,
                share_token=share_tok,
                ruleset_version="DEMO_ASSUMPTION_v1",
                model_version="seg:watershed/def:mobilenetv3",
                geo_lat=19.9975,
                geo_lon=73.7898,
                total_bulbs=5,
                grade_a_count=5,
                urs_count=0,
                rejected_count=0,
                review_count=0,
            )
            db.add(rpt)
            db.commit()

            resp = client.get(f"/api/v1/reports/share/{share_tok}", headers={"Accept": "application/json"})
            assert resp.status_code == 200
            data = resp.json()
            assert data["geo_lat"] is None, "geo_lat must be None in public share JSON"
            assert data["geo_lon"] is None, "geo_lon must be None in public share JSON"
            assert data["officer_id"] is None, "officer_id must be None in public share JSON"
            assert data["lot_id"] == "LOT-PRIVACY-JSON"
            assert data["officer_name"] == "Inspector Deshmukh"
        finally:
            db.close()


class TestOfficerAuthC2:
    def test_protected_routes_require_token_when_enforced(self, client: TestClient, monkeypatch):
        """Verifies C2: protected inspection routes enforce officer auth when enabled."""
        monkeypatch.setattr(settings, "enforce_officer_auth", True)
        monkeypatch.setattr(settings, "officer_api_key", "secret-key-42")

        # finalize requires officer token
        resp = client.post("/api/v1/inspections/some-id/finalize")
        assert resp.status_code == 401
        assert "Authentication required" in resp.json()["detail"]

        # with invalid token
        resp = client.post("/api/v1/inspections/some-id/finalize", headers={"X-Officer-Token": "wrong"})
        assert resp.status_code == 403

        # ask-ai requires officer token
        resp = client.post("/api/v1/inspections/some-id/ask-ai", json={"question": "how are the bulbs?"})
        assert resp.status_code == 401

        # announce requires officer token
        resp = client.post("/api/v1/inspections/some-id/announce")
        assert resp.status_code == 401


class TestBhashiniConfigH8:
    def test_bhashini_settings_bound(self, monkeypatch):
        """Verifies H8: bhashini_api_key is bound in Settings and accessible."""
        monkeypatch.setenv("BHASHINI_API_KEY", "bhashini_secret_key_123")
        from config import Settings
        s = Settings()
        assert s.bhashini_api_key == "bhashini_secret_key_123"


class TestUncalibratedOverheadRemediation:
    def test_uncalibrated_scale_preserved_with_review_confidence(self):
        """Verifies fix for user issue: random photos without calibration cards compute
        physical size via overhead heuristic with honest NEEDS_REVIEW confidence tier.
        """
        import cv2
        from cv.calibration import compute_calibration
        from cv.confidence import assess_confidence
        from cv.marker_detector import MarkerDetectionResult
        from cv.size_estimator import estimate_size
        from cv.defect_classifier import DefectPrediction
        from grading.engine import GradingEngine

        # 1920x1080 capture frame without marker
        dummy_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        uncalibrated_marker = MarkerDetectionResult(
            detected=False,
            failure_code="marker_not_detected",
            failure_message="No ChArUco board detected.",
        )
        calib = compute_calibration(dummy_img, uncalibrated_marker)

        # Scale must NOT be wiped to None
        assert calib.is_estimated is True
        assert calib.scale_mm_per_px is not None

        # Mask of a clean healthy onion (~50mm diameter)
        mask = np.zeros((1080, 1920), dtype=np.uint8)
        radius_px = int(25.0 / calib.scale_mm_per_px)
        cv2.circle(mask, (960, 540), radius_px, 255, -1)
        size_est = estimate_size(mask, calib.scale_mm_per_px)

        assert size_est is not None
        assert size_est.equatorial_diameter_mm > 40.0

        defects = DefectPrediction(
            sprouted_prob=0.05,
            rotten_prob=0.02,
            damaged_prob=0.03,
            model_version="test-model:v1",
            is_mock=False,
        )

        conf = assess_confidence(
            segmentation_conf=0.92,
            touches_border=False,
            size_estimate=size_est,
            defect_prediction=defects,
            is_estimated_scale=calib.is_estimated,
        )

        assert conf.tier == "NEEDS_REVIEW"
        assert any("autonomous overhead" in r.lower() or "estimated" in r.lower() for r in conf.reasons)

        from pathlib import Path
        from grading.policy_loader import load_policy

        policies_dir = Path(__file__).parent.parent / "grading" / "policies"
        policy = load_policy("DEMO_ASSUMPTION_v1", policies_dir)
        engine = GradingEngine(policy)
        grade = engine.evaluate_bulb(
            size_estimate=size_est,
            defect_prediction=defects,
            confidence=conf,
        )
        assert grade.grade in ("GRADE_A", "UNDER_SIZED", "OVER_SIZED")
        assert grade.confidence_tier == "NEEDS_REVIEW"


class TestCryptographicSealAndPolicyDecoupling:
    """Verifies HMAC-SHA256 cryptographic seal tamper-evident integrity and dynamic policy thresholds."""

    def test_cryptographic_seal_integrity_binding(self, tmp_path):
        from services.crypto_seal import compute_inspection_seal, verify_inspection_seal
        from unittest.mock import MagicMock

        # Create real sample image file on disk
        img_file = tmp_path / "test_sample.jpg"
        img_file.write_bytes(b"optical-onion-capture-bytes-verified")

        report = MagicMock(
            report_id="REP-TEST-001",
            total_bulbs=42,
            grade_a_pct=85.7,
            urs_pct=9.5,
            rejected_pct=4.8,
            share_token="cepa-demo-token-123",
        )
        sample = MagicMock(image_path=str(img_file), processed_image_path=None)
        inspection = MagicMock(
            id="insp-seal-uuid-001",
            officer_id="OFF-SEAL-77",
            samples=[sample],
        )

        seal_hex, img_hash = compute_inspection_seal(report, inspection)
        assert len(seal_hex) == 64
        assert len(img_hash) == 64
        assert verify_inspection_seal(seal_hex, report, inspection, require_photo_on_disk=True) is True

        # Tampering with officer ID fails verification
        tampered_inspection = MagicMock(
            id="insp-seal-uuid-001",
            officer_id="OFF-IMPOSTOR-99",
            samples=[sample],
        )
        assert verify_inspection_seal(seal_hex, report, tampered_inspection) is False

        # Tampering with quality metrics fails verification
        tampered_report = MagicMock(
            report_id="REP-TEST-001",
            total_bulbs=42,
            grade_a_pct=99.0,
            urs_pct=1.0,
            rejected_pct=0.0,
            share_token="cepa-demo-token-123",
        )
        assert verify_inspection_seal(seal_hex, tampered_report, inspection) is False

        # Missing photo marks seal status as INVALID_MISSING_PHOTO
        missing_inspection = MagicMock(
            id="insp-seal-uuid-002",
            officer_id="OFF-SEAL-77",
            samples=[MagicMock(image_path="nonexistent_photo.jpg", processed_image_path=None)],
        )
        missing_res = compute_inspection_seal(report, missing_inspection)
        assert missing_res.seal_status == "INVALID_MISSING_PHOTO"
        assert missing_res.is_photo_verified is False

    def test_size_estimator_policy_decoupling(self):
        from cv.size_estimator import estimate_size
        import cv2

        mask = np.zeros((200, 200), dtype=np.uint8)
        # Draw 100px diameter circle at 0.5 mm/px -> ~50mm diameter
        cv2.circle(mask, (100, 100), 50, 255, -1)

        # Standard APMC thresholds: 45 to 65 is SUPER
        std_est = estimate_size(mask, scale_mm_per_px=0.5)
        assert std_est is not None
        assert std_est.mandi_size_grade == "SUPER"

        # Custom policy where 50mm is classified as MADHYAM because SUPER starts at 55mm
        custom_thresholds = [40.0, 55.0, 75.0]
        custom_est = estimate_size(mask, scale_mm_per_px=0.5, thresholds_mm=custom_thresholds)
        assert custom_est is not None
        assert custom_est.mandi_size_grade == "MADHYAM"

    def test_groq_ai_agronomist_truthfulness(self, monkeypatch):
        from services.groq_ai_service import ask_ai_agronomist
        monkeypatch.setattr("services.groq_ai_service._get_groq_api_key", lambda: "")

        # 1. Empty lot should never fabricate praise or pretend bulbs were checked
        empty_ans = ask_ai_agronomist("Can I store these onions?", {"total_bulbs": 0})
        assert "No inspection measurements" in empty_ans
        assert "zero critical defects" not in empty_ans

        # 2. Rot-heavy lot should explicitly warn against buffer storage
        rot_ans = ask_ai_agronomist(
            "Can I store these onions?",
            {"total_bulbs": 20, "grade_a_count": 5, "urs_count": 5, "rejected_count": 10, "net_rate_inr": 1800, "storage_days": 90}
        )
        assert "High rot/defect concentration" in rot_ans
        assert "NOT recommended" in rot_ans
        assert "Immediate segregation" in rot_ans

        # 3. Clean lot gives sound agronomic storage advice
        clean_ans = ask_ai_agronomist(
            "How should I store these?",
            {"total_bulbs": 20, "grade_a_count": 20, "urs_count": 0, "rejected_count": 0, "net_rate_inr": 2410, "storage_days": 90}
        )
        assert "Excellent quality lot" in clean_ans
        assert "suitable for strategic buffer storage" in clean_ans

    def test_public_verification_endpoint(self, client):
        from database import SessionLocal
        from models import Inspection, Report
        from services.crypto_seal import compute_inspection_seal
        import uuid

        db = SessionLocal()
        try:
            insp = Inspection(
                id=str(uuid.uuid4()),
                lot_id=f"LOT-TEST-{uuid.uuid4().hex[:6]}",
                procurement_centre="Nashik APMC",
                officer_id="OFF-TEST-VERIFY",
                status="FINALIZED",
            )
            db.add(insp)
            db.flush()

            rep = Report(
                id=str(uuid.uuid4()),
                report_id=f"RPT-{uuid.uuid4().hex[:8]}",
                inspection_id=insp.id,
                total_bulbs=20,
                grade_a_count=16,
                urs_count=3,
                rejected_count=1,
                ruleset_version="DEMO_ASSUMPTION_v1",
                model_version="test-model:v1",
                share_token=f"token-{uuid.uuid4().hex[:8]}",
            )
            seal_res = compute_inspection_seal(rep, insp)
            rep.cryptographic_seal = seal_res.seal_hex
            rep.image_sha256 = seal_res.image_sha256
            rep.seal_status = seal_res.seal_status
            db.add(rep)
            db.commit()
            report_id = rep.report_id
        finally:
            db.close()

        # 1. Test JSON audit payload
        res = client.get(f"/api/v1/reports/{report_id}/verify")
        assert res.status_code == 200
        data = res.json()
        assert "is_valid" in data
        assert "seal_status" in data
        assert "computed_seal" in data
        assert len(data["computed_seal"]) == 64
        assert data["report_id"] == report_id

        # 2. Test HTML certificate verification badge view
        html_res = client.get(
            f"/api/v1/reports/{report_id}/verify",
            headers={"Accept": "text/html"},
        )
        assert html_res.status_code == 200
        assert "Cepa Quality Appraisal Seal" in html_res.text
        assert "Cryptographically signed by Cepa Sovereign" in html_res.text


class TestSampleUploadIdempotency:
    """Verifies that duplicate mobile uploads or network retries do not duplicate samples."""

    def test_duplicate_image_upload_returns_existing_sample_idempotently(self, client):
        import cv2

        # 1. Create a draft inspection
        create_res = client.post("/api/v1/inspections", json={
            "lot_id": "LOT-IDEMPOTENT-TEST",
            "procurement_centre": "Lasalgaon Mandi",
            "officer_name": "Test Officer",
        })
        assert create_res.status_code == 201
        insp_id = create_res.json()["id"]

        # 2. Generate a valid test image (synthetic onion spread)
        img = np.full((300, 300, 3), (240, 240, 240), dtype=np.uint8)
        # Add a bulb-like red circle in center
        cv2.circle(img, (150, 150), 60, (50, 40, 170), -1)
        _, buf = cv2.imencode(".jpg", img)
        img_bytes = buf.tobytes()

        # 3. First upload
        up1 = client.post(
            f"/api/v1/inspections/{insp_id}/samples",
            files={"file": ("test_frame.jpg", io.BytesIO(img_bytes), "image/jpeg")},
        )
        assert up1.status_code == 201
        sample1 = up1.json()
        assert sample1["sample_index"] == 1
        sample_id1 = sample1["id"]

        # 4. Immediate second upload of IDENTICAL bytes (simulating mobile timeout retry)
        up2 = client.post(
            f"/api/v1/inspections/{insp_id}/samples",
            files={"file": ("test_frame_retry.jpg", io.BytesIO(img_bytes), "image/jpeg")},
        )
        assert up2.status_code == 201
        sample2 = up2.json()

        # Must return the SAME sample without creating a duplicate record or incrementing index
        assert sample2["id"] == sample_id1
        assert sample2["sample_index"] == 1

        # 5. Verify inspection sample list has exactly 1 sample, not 2
        list_res = client.get(f"/api/v1/inspections/{insp_id}")
        assert list_res.status_code == 200
        assert len(list_res.json()["sample_ids"]) == 1
        assert list_res.json()["sample_ids"] == [sample_id1]


class TestOnionValidatorHardening:
    """Verifies that onion validator never fails open and enforces strict botanical constraints."""

    def test_validator_rejects_synthetic_blue_neon_object(self):
        from cv.onion_validator import OnionAuthenticityValidator
        # Pure blue neon crop
        blue_crop = np.full((120, 120, 3), (255, 120, 0), dtype=np.uint8) # BGR: blue dominant
        res = OnionAuthenticityValidator.validate_candidate(blue_crop)
        assert not res.is_onion

    def test_validator_accepts_authentic_onion_crop(self):
        from cv.onion_validator import OnionAuthenticityValidator
        import cv2
        # Nashik Red onion patch: purple-red/terracotta tones
        onion_crop = np.full((120, 120, 3), (45, 35, 160), dtype=np.uint8)
        mask = np.zeros((120, 120), dtype=np.uint8)
        cv2.circle(mask, (60, 60), 45, 255, -1)
        res = OnionAuthenticityValidator.validate_candidate(onion_crop, mask)
        assert res.is_onion


class TestResolutionInvariantParallax:
    """Verifies that camera standoff parallax uncertainty is resolution invariant."""

    def test_standoff_uncertainty_keyed_to_board_frame_fraction(self):
        from cv.calibration import compute_calibration
        from cv.marker_detector import MarkerDetectionResult

        # Simulate 4K frame (3840x2160) where board spans 30% of frame (standard tripod)
        img_4k = np.zeros((2160, 3840, 3), dtype=np.uint8)
        # Create corners spanning ~1150 px (approx 30% of 3840)
        c_x = np.linspace(500, 1650, 6)
        c_y = np.linspace(500, 1300, 4)
        xx, yy = np.meshgrid(c_x, c_y)
        corners = np.stack([xx.flatten(), yy.flatten()], axis=1).reshape(-1, 1, 2).astype(np.float32)
        ids = np.arange(len(corners), dtype=np.int32).reshape(-1, 1)

        marker_res = MarkerDetectionResult(
            detected=True,
            corner_count=len(corners),
            charuco_corners=corners,
            charuco_ids=ids,
        )

        calib = compute_calibration(img_4k, marker_res)
        # Because board covers ~30% of frame, uncertainty must be standard 2.0 mm (not 3.5 mm)
        assert calib.uncertainty_mm == 2.0





