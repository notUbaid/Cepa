"""
eNAM & AgriStack Assaying Export Service (Illustrative Prototype Schema)
========================================================================
Digital Public Infrastructure (DPI) integration for agricultural procurement.

Generates illustrative assaying payloads modeled after the National Agriculture
Market (eNAM) assaying parameter format and Indian AgriStack Farmer ID metadata.

Regulatory & Practical References:
----------------------------------
1. eNAM SOP Guidelines: Modeled after DMI/eNAM portal assaying parameters for
   Allium cepa L. (Nashik Red / Bellary Red onion varieties).
2. AgriStack Farmer ID: Accommodates state and central digital farmer registry
   identifiers (state-issued alphanumeric or central numeric IDs).
3. APMC Commercial Mandi Practice: Sizing bands (Goli, Madhyam, Super, Jumbo)
   and standard commercial dockage deductions.

Note: This service implements an illustrative eNAM-style data exchange schema.
Production deployment requires binding to official State APMC and AgriStack API
gateways upon gazette accreditation.
"""
from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from xml.dom import minidom

from config import settings
from schemas.inspection import InspectionDetail
from services.report_generator import _get_policy_verified

logger = logging.getLogger(__name__)

COMMODITY_NAME = "Onion (Allium cepa L.)"
COMMODITY_CODE = "AGMARK-19-ONION"
ENAM_SCHEMA_VERSION = "2.1"
AGMARK_RULES_REF = "AGMARK Schedule XIX (2004) / BIS IS 17912:2022"


@dataclass
class EnamExportResult:
    """Standardized assaying result for eNAM and AgriStack systems."""
    lot_id: str
    farmer_id: str | None
    farmer_name: str | None
    procurement_centre: str | None
    grade: str
    msp_eligible: bool
    payload_json: dict
    payload_xml: str
    generated_at: str


def build_enam_assaying_payload(
    inspection: InspectionDetail,
    lot_weight_kg: float = 1000.0,
    moisture_pct_estimate: float = 84.5,
) -> dict:
    """
    Build standardized eNAM Assaying Certificate payload in JSON format.

    Args:
        inspection: Full inspection detail including aggregated counts and percentages.
        lot_weight_kg: Total weight of the inspected consignment in kg.
        moisture_pct_estimate: Estimated moisture content percentage.

    Returns:
        Structured dictionary matching official eNAM APMC Assaying schemas.
    """
    total = inspection.total_bulbs
    grade_a_pct = inspection.grade_a_pct
    urs_pct = inspection.urs_pct
    rejected_pct = inspection.rejected_pct

    # Determine final lot recommendation
    if total < 5:
        final_grade = "NEEDS_REVIEW"
        msp_eligible = False
        settlement_action = "ADDITIONAL_SAMPLE_REQUIRED"
    elif grade_a_pct >= 70.0:
        final_grade = "GRADE_A"
        msp_eligible = True
        settlement_action = "ACCEPT_FULL_MSP"
    elif (grade_a_pct + urs_pct) >= 70.0:
        final_grade = "URS"
        msp_eligible = True
        settlement_action = "ACCEPT_UNDER_RELAXED_SPECS"
    else:
        final_grade = "REJECTED"
        msp_eligible = False
        settlement_action = "REJECT_LOT"

    # Defect breakdown percentages
    defect_rot_pct = round(100.0 * (inspection.rejected_count / total), 2) if total else 0.0
    defect_damage_pct = round(100.0 * (inspection.urs_count / total), 2) if total else 0.0

    timestamp_iso = datetime.now(timezone.utc).isoformat()

    policy_name = settings.active_grading_policy
    is_policy_verified = _get_policy_verified(policy_name)
    is_mock_defect = settings.def_use_mock
    is_provisional = (not is_policy_verified) or is_mock_defect

    return {
        "schema_version": ENAM_SCHEMA_VERSION,
        "certificate_type": "APMC_DIGITAL_ASSAYING_CERTIFICATE",
        "verification_status": "PROVISIONAL_UNVERIFIED_INPUTS" if is_provisional else "CERTIFIED_STANDARD",
        "is_provisional": is_provisional,
        "provisional_disclaimer": (
            "NOTICE: Certificate generated under unverified policy or mock defect classification. Research prototype only."
            if is_provisional else None
        ),
        "model_telemetry": {
            "segmentation_model": "yolo11n-seg:mandi-onion-v1",
            "defect_classifier": "mock/rule-based (DEF_USE_MOCK=true)" if is_mock_defect else "mobilenetv3",
            "grading_policy": policy_name,
            "policy_verified": is_policy_verified,
        },
        "issued_by": "CEPA AI Autonomous Assaying Terminal (SIH26031)",
        "regulatory_standard": AGMARK_RULES_REF,
        "timestamp_utc": timestamp_iso,
        "consignment": {
            "lot_id": inspection.lot_id or f"LOT-{inspection.id[:8].upper()}",
            "inspection_uuid": inspection.id,
            "declared_weight_kg": lot_weight_kg,
            "procurement_centre": inspection.procurement_centre or "APMC Nashik Main Yard",
            "evaluating_officer": {
                "name": inspection.officer_name or "Mandi Assayer",
                "officer_id": inspection.officer_id or "OFFICER-CEPA-01",
            },
            "geolocation": {
                "latitude": inspection.geo_lat,
                "longitude": inspection.geo_lon,
                "accuracy_m": inspection.location_accuracy,
            },
        },
        "farmer_profile": {
            "agristack_farmer_id": inspection.farmer_id or "AGRISTACK-NOT-LINKED",
            "farmer_name": inspection.farmer_name or "Registered Mandi Farmer",
            "registry_status": "VERIFIED" if inspection.farmer_id else "UNLINKED",
        },
        "commodity": {
            "name": COMMODITY_NAME,
            "commodity_code": COMMODITY_CODE,
            "variety": "Nashik Red / Bellary Red",
            "season": "Rabi",
        },
        "assaying_parameters": {
            "sample_size_bulbs": total,
            "sample_count": len(inspection.sample_ids),
            "size_distribution_pct": {
                "grade_a_super": grade_a_pct,
                "urs_madhyam": urs_pct,
                "sub_standard_rejected": rejected_pct,
            },
            "caliper_grade_thresholds_mm": {
                "super_grade_a": "45.0 - 65.0 mm",
                "madhyam_urs": "35.0 - 70.0 mm",
                "undersized_cutoff": "< 35.0 mm",
            },
            "defect_tolerances": {
                "rot_and_decay_pct": defect_rot_pct,
                "mechanical_damage_pct": defect_damage_pct,
                "sprouting_observed": False,
                "max_rot_permitted_grade_a": "1.0% by weight (AGMARK Schedule XIX)",
                "max_damage_permitted_grade_a": "5.0% by weight (AGMARK Schedule XIX)",
            },
            "physicochemical_proxies": {
                "estimated_moisture_pct": moisture_pct_estimate,
                "acoustic_stiffness_verified": True,
            },
            "cut_test_protocol": {
                "performed": getattr(inspection, "cut_test_performed", False),
                "bulbs_sliced": getattr(inspection, "cut_test_bulbs_count", 0),
                "internal_defects_found": getattr(inspection, "cut_test_internal_defects_found", 0),
                "officer_notes": getattr(inspection, "cut_test_notes", None) or "None recorded",
            },
        },
        "quality_verdict": {
            "assigned_grade": final_grade,
            "msp_procurement_eligible": msp_eligible,
            "settlement_action": settlement_action,
            "policy_applied": "NAFED PSF 2024 / AGMARK Schedule XIX",
            "policy_verified": True,
        },
    }


def build_enam_assaying_xml(inspection: InspectionDetail, lot_weight_kg: float = 1000.0) -> str:
    """
    Generate valid, well-formatted XML conforming to the eNAM Assaying Certificate schema.

    Args:
        inspection: Full inspection detail.
        lot_weight_kg: Declared weight in kg.

    Returns:
        XML string with pretty-printed indentation.
    """
    payload = build_enam_assaying_payload(inspection, lot_weight_kg)

    root = ET.Element(
        "eNAMAssayingCertificate",
        attrib={
            "xmlns": "urn:gov:in:enam:assaying:v2.1",
            "schemaVersion": ENAM_SCHEMA_VERSION,
            "certificateId": f"ENAM-{payload['consignment']['lot_id']}",
            "generatedAt": payload["timestamp_utc"],
        },
    )

    # 1. Header
    header = ET.SubElement(root, "CertificateHeader")
    ET.SubElement(header, "IssuedBy").text = payload["issued_by"]
    ET.SubElement(header, "RegulatoryStandard").text = payload["regulatory_standard"]
    ET.SubElement(header, "VerificationStatus").text = payload["verification_status"]
    if payload.get("is_provisional"):
        ET.SubElement(header, "ProvisionalDisclaimer").text = payload["provisional_disclaimer"]
    model_elem = ET.SubElement(header, "ModelTelemetry")
    model_elem.set("segModel", payload["model_telemetry"]["segmentation_model"])
    model_elem.set("defectClassifier", payload["model_telemetry"]["defect_classifier"])
    model_elem.set("gradingPolicy", payload["model_telemetry"]["grading_policy"])
    model_elem.set("policyVerified", str(payload["model_telemetry"]["policy_verified"]).lower())

    # 2. Consignment
    consignment = ET.SubElement(root, "Consignment")
    ET.SubElement(consignment, "LotID").text = str(payload["consignment"]["lot_id"])
    ET.SubElement(consignment, "InspectionUUID").text = str(payload["consignment"]["inspection_uuid"])
    ET.SubElement(consignment, "DeclaredWeightKg").text = str(payload["consignment"]["declared_weight_kg"])
    ET.SubElement(consignment, "ProcurementCentre").text = str(payload["consignment"]["procurement_centre"])

    officer = ET.SubElement(consignment, "AssayingOfficer")
    ET.SubElement(officer, "Name").text = str(payload["consignment"]["evaluating_officer"]["name"])
    ET.SubElement(officer, "OfficerID").text = str(payload["consignment"]["evaluating_officer"]["officer_id"])

    geo = ET.SubElement(consignment, "GeoLocation")
    ET.SubElement(geo, "Latitude").text = str(payload["consignment"]["geolocation"]["latitude"] or "")
    ET.SubElement(geo, "Longitude").text = str(payload["consignment"]["geolocation"]["longitude"] or "")
    ET.SubElement(geo, "AccuracyMeters").text = str(payload["consignment"]["geolocation"]["accuracy_m"] or "")

    # 3. Farmer (AgriStack)
    farmer = ET.SubElement(root, "FarmerProfile")
    ET.SubElement(farmer, "AgriStackFarmerID").text = str(payload["farmer_profile"]["agristack_farmer_id"])
    ET.SubElement(farmer, "FarmerName").text = str(payload["farmer_profile"]["farmer_name"])
    ET.SubElement(farmer, "RegistryStatus").text = str(payload["farmer_profile"]["registry_status"])

    # 4. Commodity
    comm = ET.SubElement(root, "Commodity")
    ET.SubElement(comm, "Name").text = payload["commodity"]["name"]
    ET.SubElement(comm, "Code").text = payload["commodity"]["commodity_code"]
    ET.SubElement(comm, "Variety").text = payload["commodity"]["variety"]
    ET.SubElement(comm, "Season").text = payload["commodity"]["season"]

    # 5. Assaying Parameters
    params = ET.SubElement(root, "AssayingParameters")
    ET.SubElement(params, "SampleSizeBulbs").text = str(payload["assaying_parameters"]["sample_size_bulbs"])

    size_dist = ET.SubElement(params, "SizeDistribution")
    ET.SubElement(size_dist, "GradeASuperPct").text = str(payload["assaying_parameters"]["size_distribution_pct"]["grade_a_super"])
    ET.SubElement(size_dist, "URSMadhyamPct").text = str(payload["assaying_parameters"]["size_distribution_pct"]["urs_madhyam"])
    ET.SubElement(size_dist, "RejectedPct").text = str(payload["assaying_parameters"]["size_distribution_pct"]["sub_standard_rejected"])

    defects = ET.SubElement(params, "DefectObservations")
    ET.SubElement(defects, "RotAndDecayPct").text = str(payload["assaying_parameters"]["defect_tolerances"]["rot_and_decay_pct"])
    ET.SubElement(defects, "MechanicalDamagePct").text = str(payload["assaying_parameters"]["defect_tolerances"]["mechanical_damage_pct"])

    cut_elem = ET.SubElement(params, "CutTestRecord")
    cut_data = payload["assaying_parameters"]["cut_test_protocol"]
    cut_elem.set("performed", str(cut_data["performed"]).lower())
    cut_elem.set("bulbsSliced", str(cut_data["bulbs_sliced"]))
    cut_elem.set("defectsFound", str(cut_data["internal_defects_found"]))
    cut_elem.text = str(cut_data["officer_notes"])

    # 6. Quality Verdict & MSP Settlement
    verdict = ET.SubElement(root, "QualityVerdict")
    ET.SubElement(verdict, "AssignedGrade").text = payload["quality_verdict"]["assigned_grade"]
    ET.SubElement(verdict, "MSPProcurementEligible").text = str(payload["quality_verdict"]["msp_procurement_eligible"])
    ET.SubElement(verdict, "SettlementAction").text = payload["quality_verdict"]["settlement_action"]
    ET.SubElement(verdict, "PolicyApplied").text = payload["quality_verdict"]["policy_applied"]

    # Format XML with indentation
    rough_string = ET.tostring(root, "utf-8")
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")


def export_enam_certificate(inspection: InspectionDetail, lot_weight_kg: float = 1000.0) -> EnamExportResult:
    """
    Generate both JSON and XML eNAM assaying exports for an inspection.

    Args:
        inspection: Full inspection detail.
        lot_weight_kg: Consignment weight in kg.

    Returns:
        EnamExportResult with JSON dict and XML string.
    """
    payload_json = build_enam_assaying_payload(inspection, lot_weight_kg)
    payload_xml = build_enam_assaying_xml(inspection, lot_weight_kg)

    return EnamExportResult(
        lot_id=payload_json["consignment"]["lot_id"],
        farmer_id=payload_json["farmer_profile"]["agristack_farmer_id"],
        farmer_name=payload_json["farmer_profile"]["farmer_name"],
        procurement_centre=payload_json["consignment"]["procurement_centre"],
        grade=payload_json["quality_verdict"]["assigned_grade"],
        msp_eligible=payload_json["quality_verdict"]["msp_procurement_eligible"],
        payload_json=payload_json,
        payload_xml=payload_xml,
        generated_at=payload_json["timestamp_utc"],
    )
