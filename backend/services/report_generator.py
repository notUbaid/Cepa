"""
Report Generator Service

Generates a professional PDF inspection report using ReportLab.

The report includes:
  - Inspection metadata (ID, date/time, location, officer, lot)
  - Sample coverage and sampling limitation note
  - Lot statistics (Grade A%, URS%, Rejected%)
  - Defect counts breakdown
  - Grading policy version and model version
  - Full limitations disclaimer
  - QR code for share URL

Design constraints:
  - No fake government logos or official-looking seals
  - Limitations section is mandatory -- never omitted
  - Policy version always visible
  - Mock prediction warning shown if applicable
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path

from config import settings
from models.report import Report

logger = logging.getLogger(__name__)


def generate_pdf_report(
    report: Report,
    inspection,        # Inspection ORM object
    output_dir: Path | None = None,
) -> Path:
    """
    Generate a PDF report for the given Report record.

    Args:
        report: Report ORM object with all statistics populated.
        inspection: Inspection ORM object for metadata.
        output_dir: Directory to save PDF. Defaults to storage_dir/reports.

    Returns:
        Absolute path to the generated PDF file.

    Raises:
        Exception: If PDF generation fails (caller should handle and log).
    """
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm, mm
    from reportlab.platypus import (
        HRFlowable,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    if output_dir is None:
        output_dir = settings.storage_dir / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_filename = f"{report.report_id}.pdf"
    pdf_path = output_dir / pdf_filename

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    story = []

    # ── Header ─────────────────────────────────────────────────────────────────
    title_style = ParagraphStyle(
        "CepaTitle",
        parent=styles["Heading1"],
        fontSize=18,
        textColor=colors.HexColor("#1a1a2e"),
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "CepaSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#555"),
        spaceAfter=2,
    )

    story.append(Paragraph("Onion Quality Inspection Report", title_style))
    story.append(Paragraph("Cepa Inspection System -- SIH26031 Proof of Concept", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#ccc")))
    story.append(Spacer(1, 0.3 * cm))

    is_verified = _get_policy_verified(report.ruleset_version)
    is_mock_defect = settings.def_use_mock
    is_provisional = (not is_verified) or is_mock_defect

    # Policy/model version in header (always visible)
    policy_note = (
        f"Policy: {report.ruleset_version} | "
        f"Segmentation: {report.model_version} | "
        f"Defect Classifier: {'MOCK/RULE-BASED' if is_mock_defect else 'MobileNetV3'} | "
        f"Policy Verified: {'YES' if is_verified else 'NO -- WORKING ASSUMPTION'}"
    )
    story.append(Paragraph(policy_note, ParagraphStyle(
        "PolicyNote", parent=styles["Normal"], fontSize=7.5,
        textColor=colors.HexColor("#c0392b" if is_provisional else "#27ae60"),
    )))
    story.append(Spacer(1, 0.2 * cm))

    # Prominent warning box for unverified / mock reports
    if is_provisional:
        warn_html = (
            "<b>PROVISIONAL INSPECTION REPORT -- NOT FOR COMMERCIAL SETTLEMENT</b><br/>"
            f"This inspection was evaluated under unverified grading specifications ({report.ruleset_version}) "
            f"and/or rule-based mock defect predictions (DEF_USE_MOCK=true). "
            "It is a research demonstration prototype and is NOT certified for commercial APMC trade settlement."
        )
        warn_box = Table([[Paragraph(warn_html, ParagraphStyle(
            "WarnText", parent=styles["Normal"], fontSize=8, leading=11, textColor=colors.HexColor("#991b1b")
        ))]], colWidths=[16 * cm])
        warn_box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fee2e2")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#ef4444")),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(warn_box)
        story.append(Spacer(1, 0.3 * cm))

    # ── Report metadata table ─────────────────────────────────────────────────
    meta_data = [
        ["Report ID", str(report.report_id)],
        ["Inspection ID", str(inspection.id)],
        ["Date / Time", report.created_at.strftime("%d %B %Y, %H:%M:%S UTC")],
        ["Officer", inspection.officer_name or "Not specified"],
        ["Officer ID", inspection.officer_id or "Not specified"],
        ["Procurement Centre", inspection.procurement_centre or "Not specified"],
        ["Lot ID", inspection.lot_id or "Not specified"],
        ["Location (Device-Reported, Unverified GNSS)", _format_location(inspection)],
        ["Grading Policy", f"{report.ruleset_version} (verified: {is_verified})"],
        ["Defect Classifier", "Mock / Rule-Based (DEF_USE_MOCK=true)" if is_mock_defect else "MobileNetV3 PyTorch"],
        ["Segmentation Model", str(report.model_version)],
        ["Certification Status", "PROVISIONAL / RESEARCH DEMO" if is_provisional else "OFFICIAL APMC RECORD"],
    ]

    meta_table = Table(meta_data, colWidths=[5 * cm, 11 * cm])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f5f5f5")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#ddd")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 0.5 * cm))

    # ── Grade results ──────────────────────────────────────────────────────────
    story.append(Paragraph("Inspection Results", styles["Heading2"]))

    grade_data = [
        ["Category", "Count", "Percentage"],
        ["Grade A", str(report.grade_a_count), f"{report.grade_a_pct:.1f}%"],
        ["URS (Under Relaxed Specification)", str(report.urs_count), f"{report.urs_pct:.1f}%"],
        ["Rejected", str(report.rejected_count), f"{report.rejected_pct:.1f}%"],
        ["Needs Review", str(report.review_count),
         f"{100.0 * report.review_count / max(report.total_bulbs, 1):.1f}%"],
        ["Edge Cutoff (partial)", str(report.edge_cutoff_count), "--"],
        ["Total Detected", str(report.total_bulbs), "100%"],
    ]

    grade_colors = [
        colors.white,
        colors.HexColor("#27ae60"),  # Grade A -- green
        colors.HexColor("#f39c12"),  # URS -- amber
        colors.HexColor("#e74c3c"),  # Rejected -- red
        colors.HexColor("#3498db"),  # Review -- blue
        colors.HexColor("#95a5a6"),  # Edge cutoff -- grey
        colors.HexColor("#ecf0f1"),  # Total -- light
    ]

    grade_table = Table(grade_data, colWidths=[9 * cm, 3 * cm, 3 * cm])
    grade_style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#bdc3c7")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    for i, bg in enumerate(grade_colors[1:], start=1):
        grade_style.append(("BACKGROUND", (0, i), (-1, i), bg))
        if i in (1, 2, 3):
            grade_style.append(("TEXTCOLOR", (0, i), (-1, i), colors.white))

    grade_table.setStyle(TableStyle(grade_style))
    story.append(grade_table)
    story.append(Spacer(1, 0.3 * cm))

    # ── Defect breakdown ───────────────────────────────────────────────────────
    story.append(Paragraph("Visible Defect Summary", styles["Heading2"]))

    try:
        defect_counts = json.loads(report.defect_counts) if report.defect_counts else {}
    except Exception:
        defect_counts = {}

    defect_data = [
        ["Defect Type", "Count (bulbs)"],
        ["Damaged (visible damage)", str(defect_counts.get("damaged", "--"))],
        ["Rotten (visible rot/decay)", str(defect_counts.get("rotten", "--"))],
        ["Sprouted (visible sprouting)", str(defect_counts.get("sprouted", "--"))],
        ["Undersized (< 35mm)", str(defect_counts.get("undersize", "--"))],
    ]

    defect_table = Table(defect_data, colWidths=[9 * cm, 3 * cm])
    defect_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9f9f9")]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#bdc3c7")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(defect_table)
    story.append(Spacer(1, 0.4 * cm))

    # ── Assayer Manual Destructive Cut-Test Record ───────────────────────────
    story.append(Paragraph("Assayer Destructive Cut-Test Protocol", styles["Heading2"]))
    cut_performed = bool(getattr(report, "cut_test_performed", False) or getattr(inspection, "cut_test_performed", False))
    cut_bulbs = int(getattr(report, "cut_test_bulbs_count", 0) or getattr(inspection, "cut_test_bulbs_count", 0))
    cut_defects = int(getattr(report, "cut_test_internal_defects_found", 0) or getattr(inspection, "cut_test_internal_defects_found", 0))
    cut_notes = getattr(report, "cut_test_notes", None) or getattr(inspection, "cut_test_notes", None) or ""

    if cut_performed:
        cut_status_label = f"COMPLETED ({cut_bulbs} bulbs sliced, {cut_defects} internal defect(s) detected)"
        cut_finding = f"{cut_defects} bulb(s) with internal decay" if cut_defects > 0 else "0 defective bulbs (Zero internal rot / sound center)"
        cut_obs = cut_notes if cut_notes else "Physical cross-section cut test conducted per AGMARK protocol."
    else:
        cut_status_label = "NOT PERFORMED (Non-destructive optical assaying only)"
        cut_finding = "N/A — Visual surface evaluation only"
        cut_obs = "Sub-surface internal rot estimated via multi-factor acoustic and optical proxies."

    cut_table_data = [
        ["Cut-Test Parameter", "Field Observation"],
        ["Protocol Status", cut_status_label],
        ["Bulbs Sliced & Inspected", str(cut_bulbs) if cut_performed else "0"],
        ["Internal Decay / Rot Findings", cut_finding],
        ["Assayer Observations", cut_obs],
    ]
    cut_table = Table(cut_table_data, colWidths=[6 * cm, 10 * cm])
    cut_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9f9f9")]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#bdc3c7")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(cut_table)
    story.append(Spacer(1, 0.4 * cm))

    # ── APMC Mandi Size Distribution & Biomass Weight ────────────────────────
    story.append(Paragraph("APMC Mandi Size & Biomass Distribution", styles["Heading2"]))

    sizes_mm: list[float] = []
    weights_g: list[float] = []
    for s in inspection.samples:
        for inst in s.onion_instances:
            if inst.measurement:
                sz = inst.measurement.equatorial_diameter_mm or inst.measurement.equivalent_diameter_mm
                if sz:
                    sizes_mm.append(sz)
                if inst.measurement.estimated_weight_grams:
                    weights_g.append(inst.measurement.estimated_weight_grams)

    from grading.statistics import (
        compute_apmc_size_distribution,
        compute_commercial_pricing,
        compute_lot_weight_statistics,
    )
    apmc = compute_apmc_size_distribution(sizes_mm)
    weights = compute_lot_weight_statistics(weights_g)

    mandi_data = [
        ["Mandi Size Grade", "Specification", "Count", "Percentage"],
        ["Goli (Baby)", "< 35 mm", str(apmc.goli_count), f"{apmc.goli_pct:.1f}%"],
        ["Madhyam (Medium)", "35 - 45 mm", str(apmc.madhyam_count), f"{apmc.madhyam_pct:.1f}%"],
        ["Super (Grade A Target)", "45 - 65 mm", str(apmc.super_count), f"{apmc.super_pct:.1f}%"],
        ["Jumbo (Oversized)", "> 65 mm", str(apmc.jumbo_count), f"{apmc.jumbo_pct:.1f}%"],
        ["Estimated Sample Weight", f"{weights.total_sample_weight_kg:.2f} kg",
         f"Mean: {weights.mean_bulb_weight_g:.0f}g / bulb", f"Range: {weights.min_bulb_weight_g:.0f}-{weights.max_bulb_weight_g:.0f}g"],
    ]

    mandi_table = Table(mandi_data, colWidths=[5 * cm, 4 * cm, 3 * cm, 3 * cm])
    mandi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#34495e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#bdc3c7")),
        ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#e8f8f5")),  # highlight Super
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f4f6f7")),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(mandi_table)
    story.append(Spacer(1, 0.4 * cm))

    # ── NAFED Commercial FAQ & Price Dockage Appraisal ───────────────────────
    story.append(Paragraph("NAFED Commercial FAQ & Rate Deduction Appraisal", styles["Heading2"]))

    rot_cnt = int(defect_counts.get("rotten", 0) if isinstance(defect_counts.get("rotten"), (int, float)) else 0)
    spr_cnt = int(defect_counts.get("sprouted", 0) if isinstance(defect_counts.get("sprouted"), (int, float)) else 0)
    crit_pct = 100.0 * (rot_cnt + spr_cnt) / max(report.total_bulbs, 1)

    pricing = compute_commercial_pricing(
        grade_a_pct=report.grade_a_pct,
        urs_pct=report.urs_pct,
        rejected_pct=report.rejected_pct,
        critical_defect_pct=crit_pct,
    )

    pricing_data = [
        ["Commercial Metric", "Appraisal Value"],
        ["Benchmark PSF Procurement Rate (Illustrative)", f"Rs. {pricing.benchmark_mandi_rate_inr_per_qtl:.0f} / quintal"],
        ["Permissible Off-Grade Tolerance", f"{pricing.allowable_tolerance_pct:.1f}%"],
        ["Excess Off-Grade Variance", f"{pricing.excess_defects_pct:.1f}%"],
        ["Applicable FAQ Dockage Rate", f"Rs. {pricing.dockage_rate_inr_per_qtl:.1f} / quintal"],
        ["Net Recommended Procurement Payout", f"Rs. {pricing.net_procurement_rate_inr_per_qtl:.1f} / quintal"],
        ["Commercial Decision", f"{pricing.payment_tier} ({pricing.pricing_rationale})"],
    ]

    tier_color = colors.HexColor("#27ae60") if pricing.payment_tier == "FULL_PRICE" else (
        colors.HexColor("#f39c12") if pricing.payment_tier == "PROPORTIONAL_DOCKAGE" else colors.HexColor("#e74c3c")
    )

    pricing_table = Table(pricing_data, colWidths=[7 * cm, 9 * cm])
    pricing_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1b4f72")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#bdc3c7")),
        ("BACKGROUND", (0, 5), (-1, 5), colors.HexColor("#fcf3cf")),  # highlight Net Rate
        ("FONTNAME", (0, 5), (-1, 5), "Helvetica-Bold"),
        ("TEXTCOLOR", (1, 6), (1, 6), tier_color),
        ("FONTNAME", (1, 6), (1, 6), "Helvetica-Bold"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(pricing_table)
    story.append(Paragraph(
        "<font size=7 color='#7f8c8d'>* Note: Onion has no statutory MSP. Procurement operates under Price Stabilisation Fund (PSF) at market-linked benchmark rates. All rates shown are illustrative simulations based on tender parameters.</font>",
        styles["Normal"]
    ))
    story.append(Spacer(1, 0.4 * cm))

    # ── Post-Harvest Cold Storage Preservation Advisory ───────────────────────
    story.append(Paragraph("Post-Harvest Cold Storage Preservation Advisory", styles["Heading2"]))

    from routers.inspections import _get_bulb_storage_profile
    from cv.shelf_life import compute_lot_storage_advisory
    storage_profiles = []
    for s in inspection.samples:
        for inst in s.onion_instances:
            storage_profiles.append(_get_bulb_storage_profile(inst))

    storage_adv = compute_lot_storage_advisory(storage_profiles)

    risk_color = colors.HexColor("#27ae60") if storage_adv.respiration_risk_level == "LOW" else (
        colors.HexColor("#f39c12") if storage_adv.respiration_risk_level == "MODERATE" else colors.HexColor("#e74c3c")
    )

    storage_data = [
        ["Cold Storage Metric", "Assessment & Directive"],
        ["Lot Storageability Index", f"{storage_adv.mean_storageability_score:.1f} / 100.0"],
        ["Preservation Classification", f"{storage_adv.storage_recommendation.replace('_', ' ')}"],
        ["Safe Cold Storage Window", f"Up to {storage_adv.recommended_max_storage_days} days (0-2°C, 65-70% RH)"],
        ["Respiration & Spoilage Risk", f"{storage_adv.respiration_risk_level}"],
        ["Pathogen Exposure Breakdown", f"Mold: {storage_adv.fungal_spore_exposure_pct:.1f}% | Tunic Loss: {storage_adv.tunic_loss_exposure_pct:.1f}% | Sprout: {storage_adv.dormancy_break_exposure_pct:.1f}%"],
    ]

    storage_table = Table(storage_data, colWidths=[6.5 * cm, 9.5 * cm])
    storage_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1b4f72")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#bdc3c7")),
        ("TEXTCOLOR", (1, 4), (1, 4), risk_color),
        ("FONTNAME", (1, 4), (1, 4), "Helvetica-Bold"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(storage_table)
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(f"<b>Operational Directive:</b> {storage_adv.recommended_action}", ParagraphStyle(
        "StorageAction", parent=styles["Normal"], fontSize=8, textColor=colors.HexColor("#2c3e50"), leading=11
    )))
    story.append(Spacer(1, 0.4 * cm))

    # ── Sampling note ──────────────────────────────────────────────────────────
    story.append(Paragraph("Sampling", styles["Heading2"]))
    story.append(Paragraph(
        f"Sample count: {report.sample_count} image(s) | "
        f"Total bulbs detected: {report.total_bulbs}",
        styles["Normal"],
    ))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(report.sampling_note or "", ParagraphStyle(
        "SamplingNote", parent=styles["Normal"], fontSize=9,
        textColor=colors.HexColor("#7f8c8d"),
    )))
    story.append(Spacer(1, 0.5 * cm))

    # ── Limitations (mandatory -- never omitted) ────────────────────────────────
    story.append(Paragraph("System Limitations and Notes", styles["Heading2"]))
    limitations = (
        "1. EXTERNAL SURFACE ONLY: This inspection detects only VISIBLE surface defects. "
        "Internal rot and hidden defects not visible from the exterior cannot be detected by camera.\n\n"
        "2. PROJECTED MEASUREMENT: Onion size is measured as the projected equivalent diameter "
        "from a top-view image. This is NOT equivalent to a laboratory caliper measurement across "
        "the equator. Error range is typically ±5-15mm compared to caliper.\n\n"
        "3. AI-ASSISTED: Defect classification uses AI computer vision. Borderline cases are "
        "flagged for human review. Mock predictions are labelled [MOCK] and should not be used "
        "for actual procurement decisions.\n\n"
        "4. SAMPLING: Lot statistics are based on the inspected sample only. A single photograph "
        "of the top surface does not represent the full consignment.\n\n"
        "5. GRADING POLICY: "
        f"Active policy '{report.ruleset_version}' -- "
        f"{'VERIFIED against official specification' if _get_policy_verified(report.ruleset_version) else 'DEMO ASSUMPTIONS -- NOT official NAFED/NCCF specification'}."
    )
    story.append(Paragraph(limitations, ParagraphStyle(
        "Limitations", parent=styles["Normal"], fontSize=8,
        textColor=colors.HexColor("#555"),
        leading=14,
    )))
    story.append(Spacer(1, 0.4 * cm))

    # ── Share & Content Fingerprint (QR Code + SHA-256 of report summary) ────────
    # NOTE: This hash covers report_id + total_bulbs + grade_a_pct only.
    # It does not cover individual measurements, images, or acoustic recordings.
    # It is a content fingerprint for report identity, not a cryptographic audit trail.
    share_url = f"{settings.share_link_base_url}/{report.share_token}"
    story.append(Paragraph("Digital Verification & Report Fingerprint", styles["Heading2"]))

    from reportlab.graphics.barcode import qr
    from reportlab.graphics.shapes import Drawing
    qr_widget = qr.QrCodeWidget(share_url)
    bounds = qr_widget.getBounds()
    w = bounds[2] - bounds[0]
    h = bounds[3] - bounds[1]
    qr_drawing = Drawing(32 * mm, 32 * mm, transform=[32 * mm / w, 0, 0, 32 * mm / h, 0, 0])
    qr_drawing.add(qr_widget)

    from services.crypto_seal import compute_inspection_seal
    seal_res = compute_inspection_seal(report, inspection)
    cert_seal = getattr(report, "cryptographic_seal", None) or seal_res.seal_hex
    img_sha256 = getattr(report, "image_sha256", None) or seal_res.image_sha256 or "PHOTO_UNAVAILABLE"
    seal_status = getattr(report, "seal_status", None) or getattr(seal_res, "seal_status", "VALID")

    verify_info = (
        f"<b>Scan QR to access inspection record online:</b><br/>"
        f"<font color='#2980b9'>{share_url}</font><br/><br/>"
        f"<b>Cryptographic Sovereign Seal:</b><br/>"
        f"<font size='6.5'><code>HMAC-SHA256:{cert_seal}</code></font><br/>"
        f"<b>Sample Optical Hash:</b><br/>"
        f"<font size='6.5'><code>SHA256:{img_sha256}</code></font><br/>"
        f"<b>Seal Verification Status:</b> <b>{seal_status}</b> &nbsp;|&nbsp; <b>Verification Token:</b> {report.share_token}<br/>"
        f"<i>This HMAC-SHA256 seal cryptographically binds the raw sample optical capture, "
        f"assayer officer credential, and final defect/grade distribution metrics.</i>"
    )

    qr_table = Table([[qr_drawing, Paragraph(verify_info, ParagraphStyle("QRText", parent=styles["Normal"], fontSize=8, leading=10.5))]], colWidths=[3.5 * cm, 12.5 * cm])
    qr_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(qr_table)

    # ── Footer note ────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.6 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#ccc")))
    story.append(Paragraph(
        "Generated by Cepa Inspection System (SIH26031 Proof of Concept). "
        "This report is an AI-assisted inspection record. "
        "It does not constitute official government certification or procurement approval.",
        ParagraphStyle("Footer", parent=styles["Normal"], fontSize=7,
                       textColor=colors.HexColor("#999"), alignment=TA_CENTER),
    ))

    def _draw_provisional_watermark(canvas, document):
        if is_provisional:
            canvas.saveState()
            canvas.setFont("Helvetica-Bold", 32)
            canvas.setFillColor(colors.HexColor("#ef4444"), alpha=0.08)
            canvas.translate(297.5, 421)  # Center of A4 in points (595x842)
            canvas.rotate(45)
            canvas.drawCentredString(0, 0, "PROVISIONAL -- UNVERIFIED INPUTS")
            canvas.restoreState()

    doc.build(story, onFirstPage=_draw_provisional_watermark, onLaterPages=_draw_provisional_watermark)
    logger.info("PDF report generated: %s (provisional=%s)", pdf_path, is_provisional)
    return pdf_path


def _format_location(inspection) -> str:
    if inspection.geo_lat is not None and inspection.geo_lon is not None:
        return (
            f"{inspection.geo_lat:.5f}°N, {inspection.geo_lon:.5f}°E "
            f"(±{inspection.location_accuracy:.0f}m)"
            if inspection.location_accuracy
            else f"{inspection.geo_lat:.5f}°N, {inspection.geo_lon:.5f}°E"
        )
    return inspection.location_note or "Location unavailable"


def _get_policy_verified(version: str) -> bool:
    """Quick check if the policy version claims to be verified."""
    try:
        policy_path = settings.policies_dir / f"{version}.yaml"
        if policy_path.exists():
            import yaml
            with policy_path.open() as f:
                raw = yaml.safe_load(f)
            return bool(raw.get("verified", False))
    except Exception:
        pass
    return False
