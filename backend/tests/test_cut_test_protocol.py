"""
Unit and integration tests for Assayer Destructive Cut-Test Protocol.

Verifies:
1. Inspection CRUD models and schemas support cut_test_* fields.
2. Report generation mirrors cut-test protocol records onto Report entities.
3. Certificate HTML rendering accurately represents cut-test status (both verified cut-test and non-destructive optical mode).
4. eNAM XML & JSON exports include CutTestRecord and cut_test_protocol.
5. PDF report builds successfully with cut-test story flowable.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from schemas.inspection import InspectionCreate, InspectionDetail, InspectionUpdate
from schemas.report import ReportDetail
from services.certificate_view import render_certificate_html
from services.enam_export_service import build_enam_assaying_payload, build_enam_assaying_xml


class MockInspectionObj:
    def __init__(
        self,
        id="insp-cut-001",
        lot_id="LOT-CUT-2026-01",
        officer_name="Shri R. Patil",
        officer_id="NSK-OFF-882",
        cut_test_performed=True,
        cut_test_bulbs_count=2,
        cut_test_internal_defects_found=0,
        cut_test_notes="Equatorial cross-section: sound flesh, zero internal neck rot.",
        samples=None,
        geo_lat=20.005,
        geo_lon=74.120,
    ):
        self.id = id
        self.lot_id = lot_id
        self.officer_name = officer_name
        self.officer_id = officer_id
        self.cut_test_performed = cut_test_performed
        self.cut_test_bulbs_count = cut_test_bulbs_count
        self.cut_test_internal_defects_found = cut_test_internal_defects_found
        self.cut_test_notes = cut_test_notes
        self.samples = samples or []
        self.geo_lat = geo_lat
        self.geo_lon = geo_lon


class MockReportObj:
    def __init__(
        self,
        report_id="rep-cut-999",
        share_token="token-cut-abc",
        cut_test_performed=True,
        cut_test_bulbs_count=2,
        cut_test_internal_defects_found=0,
        cut_test_notes="Equatorial cross-section: sound flesh, zero internal neck rot.",
        total_bulbs=20,
        grade_a_count=18,
        urs_count=2,
        rejected_count=0,
    ):
        self.report_id = report_id
        self.share_token = share_token
        self.cut_test_performed = cut_test_performed
        self.cut_test_bulbs_count = cut_test_bulbs_count
        self.cut_test_internal_defects_found = cut_test_internal_defects_found
        self.cut_test_notes = cut_test_notes
        self.total_bulbs = total_bulbs
        self.grade_a_count = grade_a_count
        self.urs_count = urs_count
        self.rejected_count = rejected_count
        self.review_count = 0
        self.ruleset_version = "NAFED_2026_v1"
        self.lot_id = "LOT-CUT-2026-01"
        self.procurement_centre = "Lasalgaon Mandi Yard"
        self.officer_name = "Shri R. Patil"
        self.officer_id = "NSK-OFF-882"
        self.officer_notes = "Standard procurement lot"
        self.sample_count = 1
        self.sampling_note = "Sample of 20 bulbs"
        self.grade_a_pct = 90.0
        self.urs_pct = 10.0
        self.rejected_pct = 0.0


def test_inspection_schemas_cut_test_fields():
    create_schema = InspectionCreate(
        lot_id="LOT-001",
        cut_test_performed=True,
        cut_test_bulbs_count=3,
        cut_test_internal_defects_found=1,
        cut_test_notes="1 bulb with internal center rot.",
    )
    assert create_schema.cut_test_performed is True
    assert create_schema.cut_test_bulbs_count == 3
    assert create_schema.cut_test_internal_defects_found == 1
    assert "center rot" in create_schema.cut_test_notes

    update_schema = InspectionUpdate(
        cut_test_performed=False,
        cut_test_bulbs_count=0,
    )
    assert update_schema.cut_test_performed is False
    assert update_schema.cut_test_bulbs_count == 0


def test_certificate_html_renders_cut_test_performed():
    insp = MockInspectionObj(
        cut_test_performed=True,
        cut_test_bulbs_count=2,
        cut_test_internal_defects_found=0,
        cut_test_notes="Slicing showed 100% sound tissue, zero soft rot.",
    )
    rep = MockReportObj(
        cut_test_performed=True,
        cut_test_bulbs_count=2,
        cut_test_internal_defects_found=0,
        cut_test_notes="Slicing showed 100% sound tissue, zero soft rot.",
    )
    html = render_certificate_html(rep, insp)
    assert "Assayer Internal Cut-Test Record" in html
    assert "[VERIFIED] Destructive Sampling Completed" in html
    assert "2 Bulbs Sliced" in html
    assert "Zero Internal Decay" in html
    assert "Slicing showed 100% sound tissue" in html


def test_certificate_html_renders_cut_test_not_performed():
    insp = MockInspectionObj(
        cut_test_performed=False,
        cut_test_bulbs_count=0,
        cut_test_internal_defects_found=0,
        cut_test_notes=None,
    )
    rep = MockReportObj(
        cut_test_performed=False,
        cut_test_bulbs_count=0,
        cut_test_internal_defects_found=0,
        cut_test_notes=None,
    )
    html = render_certificate_html(rep, insp)
    assert "Assayer Internal Cut-Test Record" in html
    assert "[OPTIONAL] Non-Destructive Optical Assaying Mode" in html
    assert "0 Bulbs Cut" in html
    assert "Non-destructive optical grading active" in html


def test_enam_export_includes_cut_test_record():
    insp_detail = InspectionDetail(
        id="insp-enam-cut-01",
        lot_id="LOT-ENAM-01",
        farmer_id="MH-NSK-123456",
        farmer_name="Kisan Ramesh",
        procurement_centre="Pimpalgaon Baswant APMC",
        officer_name="D. More",
        officer_id="OFF-99",
        notes="Buffer intake lot",
        status="FINALIZED",
        geo_lat=20.17,
        geo_lon=73.98,
        location_accuracy=5.0,
        location_note="Mandi gate 2",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        finalized_at=datetime.now(timezone.utc),
        cut_test_performed=True,
        cut_test_bulbs_count=3,
        cut_test_internal_defects_found=0,
        cut_test_notes="3 bulbs cut equatorially: clean flesh",
        total_bulbs=25,
        grade_a_count=22,
        urs_count=3,
        rejected_count=0,
        review_count=0,
        grade_a_pct=88.0,
        urs_pct=12.0,
        rejected_pct=0.0,
        sample_ids=["sample-1"],
    )

    payload = build_enam_assaying_payload(insp_detail)
    cut_dict = payload["assaying_parameters"]["cut_test_protocol"]
    assert cut_dict["performed"] is True
    assert cut_dict["bulbs_sliced"] == 3
    assert cut_dict["internal_defects_found"] == 0
    assert "clean flesh" in cut_dict["officer_notes"]

    xml_str = build_enam_assaying_xml(insp_detail)
    assert "CutTestRecord" in xml_str
    assert 'performed="true"' in xml_str
    assert 'bulbsSliced="3"' in xml_str
    assert 'defectsFound="0"' in xml_str
    assert "clean flesh" in xml_str
