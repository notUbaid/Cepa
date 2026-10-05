"""
Full end-to-end integration tests for Cepa FastAPI REST endpoints.

Uses FastAPI TestClient to test the complete workflow from creating an inspection
to sample processing, officer review, correction, report generation, and PDF download.
"""
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from main import app
from database import Base, engine

SAMPLE_IMG_PATH = Path(__file__).parent.parent / "static" / "synthetic_demo_spread.jpg"


@pytest.fixture(scope="session")
def client():
    # Use TestClient context manager to trigger lifespan events (DB creation, CV initialization)
    with TestClient(app) as test_client:
        yield test_client


class TestHealthEndpoints:
    def test_health_check(self, client: TestClient):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "cepa-backend"

    def test_health_liveness(self, client: TestClient):
        response = client.get("/api/v1/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_health_readiness(self, client: TestClient):
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "checks" in data
        assert data["checks"]["database"]["status"] == "ok"
        assert data["checks"]["storage"]["status"] == "ok"

    def test_cv_health(self, client: TestClient):
        response = client.get("/api/v1/health/cv")
        assert response.status_code == 200
        data = response.json()
        assert "seg_provider" in data
        assert "defect_classifier" in data
        assert "active_policy" in data
        assert data["active_policy"] == "DEMO_ASSUMPTION_v1"

    def test_demo_sample_image(self, client: TestClient):
        response = client.get("/api/v1/demo/sample-image")
        assert response.status_code == 200
        assert "image/jpeg" in response.headers["content-type"]
        assert len(response.content) > 10000

    def test_root_redirect(self, client: TestClient):
        response = client.get("/", follow_redirects=False)
        assert response.status_code in (302, 307)
        assert response.headers["location"] == "/inspector"

    def test_calibration_board_endpoint(self, client: TestClient):
        response = client.get("/calibration-board")
        assert response.status_code == 200
        assert "application/pdf" in response.headers["content-type"]
        assert len(response.content) > 1000

    def test_deck_endpoint(self, client: TestClient):
        response = client.get("/deck")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Cepa" in response.text
        assert "Smart India Hackathon" in response.text



class TestFullInspectionWorkflow:
    def test_end_to_end_inspection_flow(self, client: TestClient):
        # 1. Create a new inspection
        create_payload = {
            "lot_id": "LOT-2026-NASHIK-001",
            "procurement_centre": "Lasalgaon Mandi, Nashik",
            "officer_name": "Rajesh Sharma",
            "officer_id": "NAFED-OFFICER-4821",
            "notes": "Farmer Ramdas Patil, Rabi onion harvest sample",
            "geo_lat": 20.1472,
            "geo_lon": 74.2255,
            "location_accuracy": 4.5,
        }
        resp = client.post("/api/v1/inspections", json=create_payload)
        assert resp.status_code == 201
        inspection = resp.json()
        inspection_id = inspection["id"]
        assert inspection["lot_id"] == "LOT-2026-NASHIK-001"
        assert inspection["status"] == "DRAFT"

        # 2. Upload a sample image
        assert SAMPLE_IMG_PATH.exists(), f"Missing test image at {SAMPLE_IMG_PATH}"
        with open(SAMPLE_IMG_PATH, "rb") as f:
            files = {"file": ("sample.jpg", f, "image/jpeg")}
            data = {
                "geo_lat": "20.1472",
                "geo_lon": "74.2255",
                "location_accuracy": "4.5",
            }
            upload_resp = client.post(
                f"/api/v1/inspections/{inspection_id}/samples",
                files=files,
                data=data,
            )

        assert upload_resp.status_code == 201
        sample_data = upload_resp.json()
        assert sample_data["quality_passed"] is True
        assert sample_data["processing_status"] == "DONE"
        assert sample_data["onion_count"] > 0
        sample_id = sample_data["id"]

        # Check that individual onions are listed
        onions = sample_data["onion_instances"]
        assert len(onions) > 0
        first_onion = onions[0]
        onion_id = first_onion["id"]
        assert first_onion["display_number"] == 1
        assert "grade" in first_onion
        assert "confidence_tier" in first_onion

        # 3. Retrieve sample details
        sample_get = client.get(f"/api/v1/inspections/{inspection_id}/samples/{sample_id}")
        assert sample_get.status_code == 200
        assert sample_get.json()["id"] == sample_id

        # 4. Evidence drilldown for a single bulb
        drilldown_resp = client.get(f"/api/v1/inspections/{inspection_id}/onions/{onion_id}")
        assert drilldown_resp.status_code == 200
        onion_detail = drilldown_resp.json()
        assert onion_detail["id"] == onion_id
        assert "equivalent_diameter_mm" in onion_detail
        assert "damaged_prob" in onion_detail
        assert "explanation" in onion_detail
        assert isinstance(onion_detail["is_mock_defect"], bool)  # True when mock, False when real model

        # 5. Manual Officer Correction
        correction_payload = {
            "damaged_prob": 0.0,
            "rotten_prob": 0.0,
            "sprouted_prob": 0.0,
            "corrected_by": "Rajesh Sharma",
            "notes": "Verified visually: no rot or cuts present.",
        }
        corr_resp = client.post(
            f"/api/v1/inspections/{inspection_id}/onions/{onion_id}/correct",
            json=correction_payload,
        )
        assert corr_resp.status_code == 200
        corrected_onion = corr_resp.json()
        assert corrected_onion["has_human_correction"] is True
        assert corrected_onion["corrected_by"] == "Rajesh Sharma"
        assert corrected_onion["rotten_prob"] == 0.0

        # 6. Finalize inspection (auto-generates the Report and PDF)
        fin_resp = client.post(f"/api/v1/inspections/{inspection_id}/finalize")
        assert fin_resp.status_code == 200
        fin_data = fin_resp.json()
        assert fin_data["status"] == "FINALIZED"
        assert fin_data["finalized_at"] is not None

        # 6b. Verify report is immediately available via GET without calling POST /reports
        auto_rep = client.get(f"/api/v1/inspections/{inspection_id}/reports")
        assert auto_rep.status_code == 200
        assert auto_rep.json()["inspection_id"] == inspection_id
        assert auto_rep.json()["total_bulbs"] > 0

        # 7. Generate PDF Report (idempotent regeneration)
        report_resp = client.post(f"/api/v1/inspections/{inspection_id}/reports")
        assert report_resp.status_code == 201
        report = report_resp.json()
        assert report["inspection_id"] == inspection_id
        assert report["total_bulbs"] > 0
        assert "share_url" in report
        share_token = report["share_token"]

        # 8. View report details
        get_rep = client.get(f"/api/v1/inspections/{inspection_id}/reports")
        assert get_rep.status_code == 200
        assert get_rep.json()["id"] == report["id"]

        # 9. Public share URL check (JSON for REST clients)
        share_resp = client.get(f"/api/v1/reports/share/{share_token}")
        assert share_resp.status_code == 200
        assert share_resp.json()["lot_id"] == "LOT-2026-NASHIK-001"
        assert "storage_advisory" in share_resp.json()
        assert "commercial_settlement" in share_resp.json()

        # 9b. Public share URL as HTML (for mobile browser QR scans)
        share_html_resp = client.get(
            f"/api/v1/reports/share/{share_token}",
            headers={"Accept": "text/html,application/xhtml+xml"},
        )
        assert share_html_resp.status_code == 200
        assert "text/html" in share_html_resp.headers["content-type"]
        assert "Cepa Mandi Procurement Record" in share_html_resp.text
        assert "SHA256:" in share_html_resp.text
        assert "Net Procurement Rate" in share_html_resp.text

        # 10. Download PDF
        pdf_resp = client.get(f"/api/v1/inspections/{inspection_id}/reports/pdf")
        assert pdf_resp.status_code == 200
        assert pdf_resp.headers["content-type"] == "application/pdf"
        assert len(pdf_resp.content) > 1000  # valid non-empty PDF

        # 11. Interactive AI Agronomist Q&A
        ask_resp = client.post(
            f"/api/v1/inspections/{inspection_id}/ask-ai",
            json={"question": "What is the best storage humidity to prevent neck rot?"},
        )
        assert ask_resp.status_code == 200
        ask_data = ask_resp.json()
        assert "answer" in ask_data
        assert "storage" in ask_data["answer"].lower() or "humidity" in ask_data["answer"].lower() or "rot" in ask_data["answer"].lower()
        assert "powered_by" in ask_data

    def test_demo_sample_video(self, client: TestClient):
        response = client.get("/api/v1/demo/sample-video")
        assert response.status_code == 200
        assert "video/mp4" in response.headers["content-type"]
        assert len(response.content) > 10000

    def test_video_inspection_workflow(self, client: TestClient):
        # Create inspection for video sweep
        resp = client.post(
            "/api/v1/inspections",
            json={
                "lot_id": "LOT-VIDEO-TEST-001",
                "procurement_centre": "Lasalgaon Mandi",
                "officer_name": "Test Officer",
            },
        )
        assert resp.status_code == 201
        inspection_id = resp.json()["id"]

        # Fetch demo video bytes
        demo_vid = client.get("/api/v1/demo/sample-video")
        assert demo_vid.status_code == 200

        # Upload video
        files = {"file": ("demo_sweep.mp4", demo_vid.content, "video/mp4")}
        vid_resp = client.post(
            f"/api/v1/inspections/{inspection_id}/video",
            files=files,
        )
        assert vid_resp.status_code == 201
        data = vid_resp.json()
        assert data["keyframes_sampled"] > 0
        assert data["total_bulbs_spotted"] > 0
        assert "ai_agronomist_verdict" in data
        verdict = data["ai_agronomist_verdict"]
        assert "quality_rating" in verdict or verdict.get("available") is False
        assert len(data["keyframes"]) > 0


class TestStorageSecurity:
    def test_path_traversal_blocked(self, client: TestClient):
        # Attempting path traversal outside storage_dir must be rejected with 403
        resp = client.get("/api/v1/storage/images/%2e%2e/%2e%2e/pyproject.toml")
        assert resp.status_code == 403
        assert "traversal blocked" in resp.json()["detail"].lower()

    def test_nonexistent_file_returns_404(self, client: TestClient):
        resp = client.get("/api/v1/storage/images/nonexistent_batch/missing.jpg")
        assert resp.status_code == 404

    def test_storage_auth_enforcement_when_enabled(self, client: TestClient, monkeypatch):
        from config import settings
        # Create a dummy file in storage_dir
        test_file = settings.storage_dir / "images" / "test_auth" / "sample.jpg"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_bytes(b"dummy-image-bytes")

        try:
            monkeypatch.setattr(settings, "enforce_officer_auth", True)
            monkeypatch.setattr(settings, "officer_api_key", "secret-test-key")

            # 1. Unauthenticated request should be rejected with 401
            resp = client.get("/api/v1/storage/images/test_auth/sample.jpg")
            assert resp.status_code == 401

            # 2. Invalid officer token should be rejected with 401
            resp_bad = client.get(
                "/api/v1/storage/images/test_auth/sample.jpg",
                headers={"X-Officer-Token": "wrong-token"},
            )
            assert resp_bad.status_code == 401

            # 3. Valid officer token should be authorized with 200
            resp_good = client.get(
                "/api/v1/storage/images/test_auth/sample.jpg",
                headers={"X-Officer-Token": "secret-test-key"},
            )
            assert resp_good.status_code == 200
            assert resp_good.content == b"dummy-image-bytes"
        finally:
            if test_file.exists():
                test_file.unlink()

