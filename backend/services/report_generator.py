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
  - Limitations section is mandatory — never omitted
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
    story.append(Paragraph("Cepa Inspection System — SIH26031 Proof of Concept", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#ccc")))
    story.append(Spacer(1, 0.3 * cm))

    # Policy/model version in header (always visible)
    policy_note = (
        f"Policy: {report.ruleset_version}  |  "
        f"Model: {report.model_version}  |  "
        f"Policy Verified: {'YES' if _get_policy_verified(report.ruleset_version) else 'NO — DEMO ASSUMPTIONS'}"
    )
    story.append(Paragraph(policy_note, ParagraphStyle(
        "PolicyNote", parent=styles["Normal"], fontSize=8,
        textColor=colors.HexColor("#c0392b"),
    )))
    story.append(Spacer(1, 0.5 * cm))

    # ── Report metadata table ─────────────────────────────────────────────────
    meta_data = [
        ["Report ID", str(report.report_id)],
        ["Inspection ID", str(inspection.id)],
        ["Date / Time", report.created_at.strftime("%d %B %Y, %H:%M:%S UTC")],
        ["Officer", inspection.officer_name or "Not specified"],
        ["Officer ID", inspection.officer_id or "Not specified"],
        ["Procurement Centre", inspection.procurement_centre or "Not specified"],
        ["Lot ID", inspection.lot_id or "Not specified"],
        ["Location", _format_location(inspection)],
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
        ["Edge Cutoff (partial)", str(report.edge_cutoff_count), "—"],
        ["Total Detected", str(report.total_bulbs), "100%"],
    ]

    grade_colors = [
        colors.white,
        colors.HexColor("#27ae60"),  # Grade A — green
        colors.HexColor("#f39c12"),  # URS — amber
        colors.HexColor("#e74c3c"),  # Rejected — red
        colors.HexColor("#3498db"),  # Review — blue
        colors.HexColor("#95a5a6"),  # Edge cutoff — grey
        colors.HexColor("#ecf0f1"),  # Total — light
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
        ["Damaged (visible damage)", str(defect_counts.get("damaged", "—"))],
        ["Rotten (visible rot/decay)", str(defect_counts.get("rotten", "—"))],
        ["Sprouted (visible sprouting)", str(defect_counts.get("sprouted", "—"))],
        ["Undersized (< 35mm)", str(defect_counts.get("undersize", "—"))],
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
        ["Madhyam (Medium)", "35 – 45 mm", str(apmc.madhyam_count), f"{apmc.madhyam_pct:.1f}%"],
        ["Super (Grade A Target)", "45 – 65 mm", str(apmc.super_count), f"{apmc.super_pct:.1f}%"],
        ["Jumbo (Oversized)", "> 65 mm", str(apmc.jumbo_count), f"{apmc.jumbo_pct:.1f}%"],
        ["Estimated Sample Weight", f"{weights.total_sample_weight_kg:.2f} kg",
         f"Mean: {weights.mean_bulb_weight_g:.0f}g / bulb", f"Range: {weights.min_bulb_weight_g:.0f}–{weights.max_bulb_weight_g:.0f}g"],
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
        ["Benchmark Mandi MSP Base Rate", f"Rs. {pricing.benchmark_mandi_rate_inr_per_qtl:.0f} / quintal"],
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

    # ── Limitations (mandatory — never omitted) ────────────────────────────────
    story.append(Paragraph("System Limitations and Notes", styles["Heading2"]))
    limitations = (
        "1. EXTERNAL SURFACE ONLY: This inspection detects only VISIBLE surface defects. "
        "Internal rot and hidden defects not visible from the exterior cannot be detected by camera.\n\n"
        "2. PROJECTED MEASUREMENT: Onion size is measured as the projected equivalent diameter "
        "from a top-view image. This is NOT equivalent to a laboratory caliper measurement across "
        "the equator. Error range is typically ±5–15mm compared to caliper.\n\n"
        "3. AI-ASSISTED: Defect classification uses AI computer vision. Borderline cases are "
        "flagged for human review. Mock predictions are labelled [MOCK] and should not be used "
        "for actual procurement decisions.\n\n"
        "4. SAMPLING: Lot statistics are based on the inspected sample only. A single photograph "
        "of the top surface does not represent the full consignment.\n\n"
        "5. GRADING POLICY: "
        f"Active policy '{report.ruleset_version}' — "
        f"{'VERIFIED against official specification' if _get_policy_verified(report.ruleset_version) else 'DEMO ASSUMPTIONS — NOT official NAFED/NCCF specification'}."
    )
    story.append(Paragraph(limitations, ParagraphStyle(
        "Limitations", parent=styles["Normal"], fontSize=8,
        textColor=colors.HexColor("#555"),
        leading=14,
    )))
    story.append(Spacer(1, 0.5 * cm))

    # ── Share link ─────────────────────────────────────────────────────────────
    share_url = f"{settings.share_link_base_url}/{report.share_token}"
    story.append(Paragraph("Share This Report", styles["Heading2"]))
    story.append(Paragraph(
        f"Report link: {share_url}",
        ParagraphStyle("ShareLink", parent=styles["Normal"], fontSize=9,
                       textColor=colors.HexColor("#2980b9")),
    ))

    # ── Footer note ────────────────────────────────────────────────────────────
    story.append(Spacer(1, 1 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#ccc")))
    story.append(Paragraph(
        "Generated by Cepa Inspection System (SIH26031 Proof of Concept). "
        "This report is an AI-assisted inspection record. "
        "It does not constitute official government certification or procurement approval.",
        ParagraphStyle("Footer", parent=styles["Normal"], fontSize=7,
                       textColor=colors.HexColor("#999"), alignment=TA_CENTER),
    ))

    doc.build(story)
    logger.info("PDF report generated: %s", pdf_path)
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
