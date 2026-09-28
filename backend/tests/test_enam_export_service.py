"""
Tests for eNAM & AgriStack Assaying Export Service and REST Endpoint.
=====================================================================
Covers:
- build_enam_assaying_payload (Grade A, URS, Rejected, Needs Review)
- build_enam_assaying_xml (Schema compliance, XML namespaces, XML parsing)
- export_enam_certificate (Dataclass container integrity)
- GET /api/v1/inspections/{id}/enam (JSON and XML response modes)
"""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from main import app
from schemas.inspection import InspectionDetail
from services.enam_export_service import (
    COMMODITY_CODE,
    COMMODITY_NAME,
    ENAM_SCHEMA_VERSION,
    build_enam_assaying_payload,
    build_enam_assaying_xml,
    export_enam_certificate,
)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


from datetime import datetime, timezone

def _make_dummy_inspection(
    total_bulbs: int = 50,
    grade_a_pct: float = 75.0,
    urs_pct: float = 20.0,
    rejected_pct: float = 5.0,
    farmer_id: str | None = "1234-5678-9012",
    farmer_name: str | None = "Ramesh Patil",
    lot_id: str | None = "LOT-NSK-2026-001",
    procurement_centre: str | None = "Lasalgaon APMC",
) -> InspectionDetail:
    """Helper to generate an InspectionDetail instance for unit tests."""
    rejected_count = int(total_bulbs * (rejected_pct / 100.0))
    urs_count = int(total_bulbs * (urs_pct / 100.0))
    grade_a_count = total_bulbs - rejected_count - urs_count

    now = datetime.now(timezone.utc)
    return InspectionDetail(
        id="insp-test-uuid-001",
        lot_id=lot_id,
        farmer_id=farmer_id,
        farmer_name=farmer_name,
        procurement_centre=procurement_centre,
        officer_name="QC Inspector Sharma",
        officer_id="OFF-99",
        geo_lat=20.148,
        geo_lon=74.225,
        location_accuracy=4.5,
        location_note="Mandi Shed 4",
        status="completed",
        notes="High quality Nashik red batch",
        total_bulbs=total_bulbs,
        grade_a_pct=grade_a_pct,
        urs_pct=urs_pct,
        rejected_pct=rejected_pct,
        grade_a_count=grade_a_count,
        urs_count=urs_count,
        rejected_count=rejected_count,
        sample_ids=["sample-1", "sample-2"],
        created_at=now,
        updated_at=now,
        finalized_at=now,
    )


class TestEnamPayloadBuilder:
    """Unit tests for eNAM JSON payload generation."""

    def test_grade_a_qualification(self):
        insp = _make_dummy_inspection(grade_a_pct=82.0, urs_pct=15.0, rejected_pct=3.0)
        payload = build_enam_assaying_payload(insp, lot_weight_kg=1500.0)

        assert payload["schema_version"] == ENAM_SCHEMA_VERSION
        assert payload["certificate_type"] == "APMC_DIGITAL_ASSAYING_CERTIFICATE"
        assert payload["commodity"]["commodity_code"] == COMMODITY_CODE
        assert payload["consignment"]["declared_weight_kg"] == 1500.0
        assert payload["farmer_profile"]["agristack_farmer_id"] == "1234-5678-9012"
        assert payload["farmer_profile"]["registry_status"] == "VERIFIED"

        verdict = payload["quality_verdict"]
        assert verdict["assigned_grade"] == "GRADE_A"
        assert verdict["msp_procurement_eligible"] is True
        assert verdict["settlement_action"] == "ACCEPT_FULL_MSP"

    def test_urs_qualification(self):
        # Grade A < 70%, but Grade A + URS >= 70%
        insp = _make_dummy_inspection(grade_a_pct=55.0, urs_pct=25.0, rejected_pct=20.0)
        payload = build_enam_assaying_payload(insp)

        verdict = payload["quality_verdict"]
        assert verdict["assigned_grade"] == "URS"
        assert verdict["msp_procurement_eligible"] is True
        assert verdict["settlement_action"] == "ACCEPT_UNDER_RELAXED_SPECS"

    def test_rejected_qualification(self):
        # Grade A + URS < 70%
        insp = _make_dummy_inspection(grade_a_pct=40.0, urs_pct=20.0, rejected_pct=40.0)
        payload = build_enam_assaying_payload(insp)

        verdict = payload["quality_verdict"]
        assert verdict["assigned_grade"] == "REJECTED"
        assert verdict["msp_procurement_eligible"] is False
        assert verdict["settlement_action"] == "REJECT_LOT"

    def test_insufficient_sample_size(self):
        # Total bulbs < 5 triggers NEEDS_REVIEW
        insp = _make_dummy_inspection(total_bulbs=4, grade_a_pct=100.0, urs_pct=0.0, rejected_pct=0.0)
        payload = build_enam_assaying_payload(insp)

        verdict = payload["quality_verdict"]
        assert verdict["assigned_grade"] == "NEEDS_REVIEW"
        assert verdict["msp_procurement_eligible"] is False
        assert verdict["settlement_action"] == "ADDITIONAL_SAMPLE_REQUIRED"

    def test_unlinked_farmer_profile(self):
        insp = _make_dummy_inspection(farmer_id=None, farmer_name=None)
        payload = build_enam_assaying_payload(insp)

        assert payload["farmer_profile"]["agristack_farmer_id"] == "AGRISTACK-NOT-LINKED"
        assert payload["farmer_profile"]["registry_status"] == "UNLINKED"


class TestEnamXmlBuilder:
    """Unit tests for XML generation conforming to eNAM schema v2.1."""

    def test_valid_xml_structure(self):
        insp = _make_dummy_inspection()
        xml_str = build_enam_assaying_xml(insp, lot_weight_kg=2000.0)

        assert xml_str.startswith("<?xml")
        root = ET.fromstring(xml_str)
        assert "eNAMAssayingCertificate" in root.tag
        assert root.attrib["schemaVersion"] == "2.1"
        assert "ENAM-LOT-NSK-2026-001" in root.attrib["certificateId"]

        # Check subelements exist
        header = root.find("{urn:gov:in:enam:assaying:v2.1}CertificateHeader")
        assert header is not None
        assert header.find("{urn:gov:in:enam:assaying:v2.1}IssuedBy").text.startswith("CEPA")

        consignment = root.find("{urn:gov:in:enam:assaying:v2.1}Consignment")
        assert consignment is not None
        assert consignment.find("{urn:gov:in:enam:assaying:v2.1}DeclaredWeightKg").text == "2000.0"

        farmer = root.find("{urn:gov:in:enam:assaying:v2.1}FarmerProfile")
        assert farmer is not None
        assert farmer.find("{urn:gov:in:enam:assaying:v2.1}AgriStackFarmerID").text == "1234-5678-9012"

        comm = root.find("{urn:gov:in:enam:assaying:v2.1}Commodity")
        assert comm is not None
        assert comm.find("{urn:gov:in:enam:assaying:v2.1}Code").text == "AGMARK-19-ONION"

        verdict = root.find("{urn:gov:in:enam:assaying:v2.1}QualityVerdict")
        assert verdict is not None
        assert verdict.find("{urn:gov:in:enam:assaying:v2.1}AssignedGrade").text == "GRADE_A"
        assert verdict.find("{urn:gov:in:enam:assaying:v2.1}MSPProcurementEligible").text == "True"


class TestExportCertificateFunction:
    """Tests the dataclass wrapper export_enam_certificate."""

    def test_export_enam_certificate_dataclass(self):
        insp = _make_dummy_inspection()
        res = export_enam_certificate(insp, lot_weight_kg=850.0)

        assert res.lot_id == "LOT-NSK-2026-001"
        assert res.farmer_id == "1234-5678-9012"
        assert res.grade == "GRADE_A"
        assert res.msp_eligible is True
        assert isinstance(res.payload_json, dict)
        assert isinstance(res.payload_xml, str)
        assert "eNAMAssayingCertificate" in res.payload_xml


class TestEnamApiEndpoint:
    """Integration tests for GET /api/v1/inspections/{id}/enam endpoint."""

    def test_enam_endpoint_json_format(self, client: TestClient):
        # 1. Create an inspection with AgriStack metadata
        create_resp = client.post(
            "/api/v1/inspections",
            json={
                "lot_id": "LOT-ENAM-TEST-01",
                "farmer_id": "9876-5432-1098",
                "farmer_name": "Suresh Kale",
                "procurement_centre": "Pimpalgaon Baswant APMC",
                "officer_name": "Inspector Deshmukh",
                "officer_id": "OFF-102",
                "policy_name": "NAFED_2026_v1",
            },
        )
        assert create_resp.status_code == 201
        insp_id = create_resp.json()["id"]

        # 2. Fetch eNAM JSON export
        resp = client.get(f"/api/v1/inspections/{insp_id}/enam?format=json")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["lot_id"] == "LOT-ENAM-TEST-01"
        assert data["farmer_id"] == "9876-5432-1098"
        assert data["farmer_name"] == "Suresh Kale"
        assert data["payload_json"]["schema_version"] == "2.1"
        assert data["payload_json"]["consignment"]["lot_id"] == "LOT-ENAM-TEST-01"
        assert data["payload_json"]["farmer_profile"]["agristack_farmer_id"] == "9876-5432-1098"

    def test_enam_endpoint_xml_format(self, client: TestClient):
        # 1. Create inspection
        create_resp = client.post(
            "/api/v1/inspections",
            json={
                "lot_id": "LOT-ENAM-XML-02",
                "farmer_id": "5555-4444-3333",
                "farmer_name": "Anita Shinde",
                "procurement_centre": "Nashik APMC",
            },
        )
        assert create_resp.status_code == 201
        insp_id = create_resp.json()["id"]

        # 2. Fetch eNAM XML export
        resp = client.get(f"/api/v1/inspections/{insp_id}/enam?format=xml")
        assert resp.status_code == 200
        assert "application/xml" in resp.headers["content-type"]
        assert "attachment" in resp.headers.get("content-disposition", "")
        assert "eNAM_Assaying_LOT-ENAM-XML-02.xml" in resp.headers.get("content-disposition", "")

        # Verify parsed XML
        root = ET.fromstring(resp.text)
        assert "eNAMAssayingCertificate" in root.tag

    def test_enam_endpoint_not_found(self, client: TestClient):
        resp = client.get("/api/v1/inspections/00000000-0000-0000-0000-000000000000/enam")
        assert resp.status_code == 404
