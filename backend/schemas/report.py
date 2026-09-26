"""Pydantic schemas for Report API responses."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReportSummary(BaseModel):
    """Summary view used in inspection detail response."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    report_id: str
    share_token: str
    total_bulbs: int
    grade_a_count: int
    urs_count: int
    rejected_count: int
    review_count: int
    grade_a_pct: float
    urs_pct: float
    rejected_pct: float
    ruleset_version: str
    model_version: str
    created_at: datetime
    has_pdf: bool = False


class ReportDetail(BaseModel):
    """Full report with all statistics for display and PDF generation."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    report_id: str
    share_token: str
    inspection_id: str

    # Officer / lot info
    lot_id: str | None
    procurement_centre: str | None
    officer_name: str | None
    officer_id: str | None
    officer_notes: str | None

    # Sample info
    sample_count: int
    sampling_note: str

    # Lot statistics
    total_bulbs: int
    grade_a_count: int
    urs_count: int
    rejected_count: int
    review_count: int
    edge_cutoff_count: int
    grade_a_pct: float
    urs_pct: float
    rejected_pct: float

    # Defect breakdown
    defect_counts: dict = Field(default_factory=dict)

    # Post-harvest storage advisory & Mandi settlement
    storage_advisory: dict | None = None
    commercial_settlement: dict | None = None
    apmc_size_distribution: dict | None = None
    lot_weight_statistics: dict | None = None

    # Provenance (for transparency)
    ruleset_version: str
    model_version: str

    # Geolocation
    geo_lat: float | None
    geo_lon: float | None
    location_note: str | None

    # Timestamps
    created_at: datetime
    finalized_at: datetime | None

    # Links
    pdf_url: str | None = None
    share_url: str | None = None

    # Limitations notice (always included in reports)
    limitations_note: str = (
        "This inspection is based on visual surface examination only. "
        "Internal rot and defects not visible from the exterior cannot be detected. "
        "Size measurements are projected equivalent diameters from a top-view image, "
        "not laboratory caliper measurements. "
        "Defect classification uses AI-assisted computer vision; "
        "borderline cases are flagged for human review. "
        "Lot statistics are based on the inspected sample only and "
        "may not represent the full consignment."
    )
