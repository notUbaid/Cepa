"""
Reports router — generate, retrieve, and share inspection reports.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

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
    )


@router.post("/inspections/{inspection_id}/reports", status_code=201)
async def generate_report(
    inspection_id: str,
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
        report = Report(inspection_id=inspection_id)
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
    report.finalized_at = inspection.finalized_at

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
        raise HTTPException(status_code=404, detail="No report generated yet")
    return _report_to_detail(inspection.report, inspection)


@router.get("/reports/share/{share_token}")
async def get_shared_report(
    share_token: str,
    db: Session = Depends(get_db),
) -> ReportDetail:
    """Public share endpoint — readable without authentication."""
    report = db.query(Report).filter(Report.share_token == share_token).first()
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    inspection = report.inspection
    return _report_to_detail(report, inspection)


@router.get("/inspections/{inspection_id}/reports/pdf")
async def download_pdf(
    inspection_id: str,
    db: Session = Depends(get_db),
) -> FileResponse:
    """Stream the PDF report for download."""
    inspection = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if inspection is None or inspection.report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    report = inspection.report
    if not report.pdf_path:
        raise HTTPException(status_code=404, detail="PDF not yet generated")

    pdf_abs = settings.storage_dir / report.pdf_path
    if not pdf_abs.exists():
        raise HTTPException(status_code=404, detail="PDF file not found on disk")

    return FileResponse(
        path=str(pdf_abs),
        media_type="application/pdf",
        filename=f"inspection-{report.report_id[:8]}.pdf",
    )
