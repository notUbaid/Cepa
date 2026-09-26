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

SAMPLE_IMG_PATH = Path(__file__).parent.parent.parent / "cv_tools" / "test_data" / "synthetic_onion_spread_sample.jpg"


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

        # 6. Finalize inspection
        fin_resp = client.post(f"/api/v1/inspections/{inspection_id}/finalize")
        assert fin_resp.status_code == 200
        fin_data = fin_resp.json()
        assert fin_data["status"] == "FINALIZED"
        assert fin_data["finalized_at"] is not None

        # 7. Generate PDF Report
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
