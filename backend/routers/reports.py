"""
Reports router — generate, retrieve, and share inspection reports.
"""
from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.orm import Session

from services.certificate_view import render_certificate_html

from auth import verify_officer_token
from config import settings
from database import get_db
from models.inspection import Inspection
from models.report import Report
from schemas.report import ReportDetail, ReportSummary
from services.report_generator import generate_pdf_report
from services.image_storage import path_to_url
from grading.aggregator import aggregate_from_db_instances

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["reports"])


def _report_to_detail(report: Report, inspection: Inspection) -> ReportDetail:
    try:
        defect_counts = json.loads(report.defect_counts or "{}")
    except Exception:
        defect_counts = {}

    pdf_url = (
        path_to_url(f"reports/{report.report_id}.pdf")
        if report.pdf_path else None
    )
    share_url = f"{settings.share_link_base_url}/{report.share_token}"

    from routers.inspections import _get_bulb_storage_profile, _extract_defect_probs
    from cv.shelf_life import compute_lot_storage_advisory
    from grading.commercial import calculate_mandi_settlement
    from grading.statistics import compute_apmc_size_distribution, compute_lot_weight_statistics

    storage_profiles = []
    sizes_mm: list[float] = []
    weights_g: list[float] = []
    rot_cnt = 0
    sprout_cnt = 0
    under_cnt = 0
    over_cnt = 0

    for sample in inspection.samples:
        for inst in sample.onion_instances:
            storage_profiles.append(_get_bulb_storage_profile(inst))
            d, r, s = _extract_defect_probs(inst.defect_observation)
            if (r or 0) >= 0.50:
                rot_cnt += 1
            if (s or 0) >= 0.50:
                sprout_cnt += 1
            if inst.measurement:
                sz = inst.measurement.equatorial_diameter_mm or inst.measurement.equivalent_diameter_mm
                if sz:
                    sizes_mm.append(sz)
                    if sz < 45.0:
                        under_cnt += 1
                    elif sz > 65.0:
                        over_cnt += 1
                if inst.measurement.estimated_weight_grams:
                    weights_g.append(inst.measurement.estimated_weight_grams)

    storage_adv = compute_lot_storage_advisory(storage_profiles)
    settlement = calculate_mandi_settlement(
        total_bulbs=report.total_bulbs,
        grade_a_count=report.grade_a_count,
        urs_count=report.urs_count,
        rejected_count=report.rejected_count,
        rotten_count=rot_cnt,
        sprouted_count=sprout_cnt,
        undersized_count=under_cnt,
        oversized_count=over_cnt,
        storageability_score=storage_adv.mean_storageability_score,
    )
    apmc = compute_apmc_size_distribution(sizes_mm)
    weights = compute_lot_weight_statistics(weights_g)

    return ReportDetail(
        id=report.id,
        report_id=report.report_id,
        share_token=report.share_token,
        inspection_id=report.inspection_id,
        lot_id=inspection.lot_id,
        procurement_centre=inspection.procurement_centre,
        officer_name=inspection.officer_name,
        officer_id=inspection.officer_id,
        officer_notes=report.officer_notes,
        cut_test_performed=getattr(report, "cut_test_performed", False),
        cut_test_bulbs_count=getattr(report, "cut_test_bulbs_count", 0),
        cut_test_internal_defects_found=getattr(report, "cut_test_internal_defects_found", 0),
        cut_test_notes=getattr(report, "cut_test_notes", None),
        sample_count=report.sample_count,
        sampling_note=report.sampling_note,
        total_bulbs=report.total_bulbs,
        grade_a_count=report.grade_a_count,
        urs_count=report.urs_count,
        rejected_count=report.rejected_count,
        review_count=report.review_count,
        edge_cutoff_count=report.edge_cutoff_count,
        grade_a_pct=report.grade_a_pct,
        urs_pct=report.urs_pct,
        rejected_pct=report.rejected_pct,
        defect_counts=defect_counts,
        ruleset_version=report.ruleset_version,
        model_version=report.model_version,
        geo_lat=report.geo_lat,
        geo_lon=report.geo_lon,
        location_note=report.location_note,
        created_at=report.created_at,
        finalized_at=report.finalized_at,
        pdf_url=pdf_url,
        share_url=share_url,
        storage_advisory=storage_adv.as_dict(),
        commercial_settlement=settlement.as_dict(),
        apmc_size_distribution={
            "goli_count": apmc.goli_count, "goli_pct": apmc.goli_pct,
            "madhyam_count": apmc.madhyam_count, "madhyam_pct": apmc.madhyam_pct,
            "super_count": apmc.super_count, "super_pct": apmc.super_pct,
            "jumbo_count": apmc.jumbo_count, "jumbo_pct": apmc.jumbo_pct,
        },
        lot_weight_statistics={
            "total_sample_weight_kg": weights.total_sample_weight_kg,
            "mean_bulb_weight_g": weights.mean_bulb_weight_g,
            "min_bulb_weight_g": weights.min_bulb_weight_g,
            "max_bulb_weight_g": weights.max_bulb_weight_g,
        },
        verify_url=f"{settings.report_base_url}/api/v1/reports/{report.report_id}/verify",
        cryptographic_seal=report.cryptographic_seal,
        image_sha256=report.image_sha256,
        seal_status=report.seal_status,
    )


def create_or_update_report(inspection: Inspection, db: Session) -> ReportDetail:
    """
    Core service helper to aggregate inspection instances, persist the Report entity,
    and generate the PDF document.
    """
    # Aggregate lot statistics from all onion instances
    all_instances = []
    for sample in inspection.samples:
        all_instances.extend(sample.onion_instances)

    from services.inspection_service import get_cv_status
    cv_status = get_cv_status()
    model_version = f"seg:{cv_status['seg_provider']}/def:{cv_status['defect_classifier']}"
    from config import settings
    ruleset_version = settings.active_grading_policy

    agg = aggregate_from_db_instances(
        instances=all_instances,
        ruleset_version=ruleset_version,
        model_version=model_version,
        sample_count=len(inspection.samples),
    )

    # Create or update the Report record
    report = inspection.report
    if report is None:
        report = Report(
            inspection_id=inspection.id,
            report_id=str(uuid.uuid4()),
            share_token=str(uuid.uuid4()),
            ruleset_version=ruleset_version,
            model_version=model_version,
        )
        db.add(report)

    report.total_bulbs = agg.total_bulbs
    report.grade_a_count = agg.grade_a_count
    report.urs_count = agg.urs_count
    report.rejected_count = agg.rejected_count
    report.review_count = agg.review_count
    report.edge_cutoff_count = agg.edge_cutoff_count
    report.defect_counts = agg.defect_counts_json()
    report.ruleset_version = ruleset_version
    report.model_version = model_version
    report.sample_count = agg.sample_count
    report.sampling_note = agg.sampling_note
    report.geo_lat = inspection.geo_lat
    report.geo_lon = inspection.geo_lon
    report.location_note = inspection.location_note
    report.cut_test_performed = getattr(inspection, "cut_test_performed", False)
    report.cut_test_bulbs_count = getattr(inspection, "cut_test_bulbs_count", 0)
    report.cut_test_internal_defects_found = getattr(inspection, "cut_test_internal_defects_found", 0)
    report.cut_test_notes = getattr(inspection, "cut_test_notes", None)
    report.finalized_at = inspection.finalized_at
    db.flush()

    # Compute and persist tamper-evident sovereign cryptographic seal
    from services.crypto_seal import compute_inspection_seal
    seal_res = compute_inspection_seal(report=report, inspection=inspection)
    report.cryptographic_seal = seal_res.seal_hex
    report.image_sha256 = seal_res.image_sha256
    report.seal_status = seal_res.seal_status

    db.commit()
    db.refresh(report)

    # Generate PDF
    try:
        pdf_path = generate_pdf_report(report=report, inspection=inspection)
        report.pdf_path = f"reports/{report.report_id}.pdf"
        db.commit()
        db.refresh(report)
    except Exception:
        logger.exception("PDF generation failed for report %s", report.report_id)
        # Not fatal — report data is still available, just no PDF yet

    return _report_to_detail(report, inspection)


@router.post("/inspections/{inspection_id}/reports", status_code=201)
async def generate_report(
    inspection_id: str,
    officer: str = Depends(verify_officer_token),
    db: Session = Depends(get_db),
) -> ReportDetail:
    """
    Generate (or regenerate) the inspection report and PDF.
    Only callable on FINALIZED inspections.
    """
    inspection = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if inspection is None:
        raise HTTPException(status_code=404, detail="Inspection not found")
    if inspection.status != "FINALIZED":
        raise HTTPException(
            status_code=400,
            detail=f"Inspection must be FINALIZED before generating report. Current: {inspection.status}"
        )

    return create_or_update_report(inspection, db)


@router.get("/inspections/{inspection_id}/reports")
async def get_report(
    inspection_id: str,
    db: Session = Depends(get_db),
) -> ReportDetail:
    """Get the generated report for an inspection."""
    inspection = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if inspection is None:
        raise HTTPException(status_code=404, detail="Inspection not found")
    if inspection.report is None:
        if inspection.status == "FINALIZED":
            # Auto-generate report on demand if missing on finalized inspection
            return create_or_update_report(inspection, db)
        raise HTTPException(status_code=404, detail="No report generated yet")
    return _report_to_detail(inspection.report, inspection)


@router.get("/reports/share/{share_token}")
async def get_shared_report(
    share_token: str,
    request: Request,
    format: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Public share endpoint — readable without authentication.
    Returns responsive HTML certificate for mobile browser QR scans,
    or JSON data for API requests.
    """
    report = db.query(Report).filter(Report.share_token == share_token).first()
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    inspection = report.inspection
    detail = _report_to_detail(report, inspection)

    accept = request.headers.get("accept", "")
    wants_html = format == "html" or ("text/html" in accept and "application/json" not in accept)

    if wants_html:
        html_content = render_certificate_html(detail, inspection)
        return HTMLResponse(content=html_content)

    return detail.model_copy(update={
        "geo_lat": None,
        "geo_lon": None,
        "officer_id": None,
    })


@router.get("/inspections/{inspection_id}/reports/pdf")
async def download_pdf(
    inspection_id: str,
    db: Session = Depends(get_db),
) -> FileResponse:
    """Stream the PDF report for download."""
    inspection = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if inspection is None:
        raise HTTPException(status_code=404, detail="Inspection not found")

    if inspection.report is None:
        if inspection.status == "FINALIZED":
            create_or_update_report(inspection, db)
            db.refresh(inspection)
        else:
            raise HTTPException(status_code=404, detail="Report not found")

    report = inspection.report
    if not report.pdf_path:
        # Attempt generating PDF now
        try:
            generate_pdf_report(report=report, inspection=inspection)
            report.pdf_path = f"reports/{report.report_id}.pdf"
            db.commit()
            db.refresh(report)
        except Exception:
            raise HTTPException(status_code=500, detail="PDF generation failed")

    pdf_abs = settings.storage_dir / report.pdf_path
    if not pdf_abs.exists():
        try:
            generate_pdf_report(report=report, inspection=inspection)
            db.commit()
            db.refresh(report)
        except Exception:
            raise HTTPException(status_code=404, detail="PDF file not found on disk")

    return FileResponse(
        path=str(pdf_abs),
        media_type="application/pdf",
        filename=f"inspection-{report.report_id[:8]}.pdf",
    )


@router.get("/reports/{report_id}/verify")
async def verify_report_seal_endpoint(
    report_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Public verification endpoint to mathematically verify a report's cryptographic HMAC seal.
    Accessible without authentication for APMC gate officers, traders, banks, and farmers.
    """
    report = db.query(Report).filter(
        (Report.report_id == report_id) | (Report.id == report_id) | (Report.share_token == report_id)
    ).first()
    if report is None:
        raise HTTPException(status_code=404, detail="Inspection report not found")

    inspection = report.inspection
    from services.crypto_seal import audit_inspection_seal
    audit = audit_inspection_seal(report, inspection)

    format_param = request.query_params.get("format", "").lower()
    accept = request.headers.get("accept", "").lower()
    if format_param == "html" or ("text/html" in accept and "application/json" not in accept):
        status_color = "#10b981" if audit["is_valid"] else "#ef4444"
        status_text = "VERIFIED AUTHENTIC" if audit["is_valid"] else f"VERIFICATION ISSUE: {audit['seal_status']}"
        html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Cepa Sovereign Verification — {report.report_id}</title>
  <style>
    body {{ font-family: system-ui, -apple-system, sans-serif; background: #0f172a; color: #f8fafc; padding: 24px; display: flex; justify-content: center; }}
    .card {{ background: #1e293b; border-radius: 16px; padding: 28px; max-width: 600px; width: 100%; border: 1px solid #334155; }}
    .badge {{ display: inline-block; padding: 6px 14px; border-radius: 999px; font-weight: 700; font-size: 13px; background: {status_color}22; color: {status_color}; border: 1px solid {status_color}; margin-bottom: 20px; }}
    .row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #334155; font-size: 14px; }}
    .label {{ color: #94a3b8; }}
    .val {{ font-family: monospace; font-weight: 600; word-break: break-all; }}
    a {{ color: #38bdf8; text-decoration: none; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="badge">{status_text}</div>
    <h2 style="margin: 0 0 16px 0;">Cepa Quality Appraisal Seal</h2>
    <div class="row"><span class="label">Report ID</span><span class="val">{report.report_id}</span></div>
    <div class="row"><span class="label">Inspection ID</span><span class="val">{inspection.id}</span></div>
    <div class="row"><span class="label">Assayer Officer</span><span class="val">{inspection.officer_id or 'OFF-DEFAULT'}</span></div>
    <div class="row"><span class="label">Bulbs Evaluated</span><span class="val">{report.total_bulbs}</span></div>
    <div class="row"><span class="label">Grade A %</span><span class="val">{report.grade_a_pct}%</span></div>
    <div class="row"><span class="label">Seal Status</span><span class="val" style="color: {status_color}">{audit['seal_status']}</span></div>
    <div class="row"><span class="label">Cryptographic Seal</span><span class="val">{audit['computed_seal']}</span></div>
    <div class="row"><span class="label">Optical Photo Digest</span><span class="val">{audit['image_sha256'] or 'PHOTO_FILE_MISSING'}</span></div>
    <div class="row"><span class="label">Photo on Storage</span><span class="val">{'PRESENT' if audit['is_photo_verified_on_disk'] else 'MISSING / EPHEMERAL'}</span></div>
    <p style="margin-top: 24px; font-size: 13px; color: #94a3b8;">
      Cryptographically signed by Cepa Sovereign Mandi Assayer Engine using HMAC-SHA256 tamper-evident integrity binding.
      <br/><a href="/api/v1/reports/share/{report.share_token}?format=html">&larr; Back to Quality Certificate</a>
    </p>
  </div>
</body>
</html>"""
        return HTMLResponse(content=html)

    return audit

