"""
Pydantic schemas for Inspection API endpoints.

Input schemas validate incoming requests.
Output schemas define the response structure.
All schemas use Pydantic v2 model_config with from_attributes=True
to enable ORM model serialization.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ── Input schemas ─────────────────────────────────────────────────────────────

class InspectionCreate(BaseModel):
    """Request body for creating a new inspection."""
    lot_id: str | None = Field(None, max_length=100, description="Farmer's lot identifier")
    procurement_centre: str | None = Field(None, max_length=200)
    officer_name: str | None = Field(None, max_length=100)
    officer_id: str | None = Field(None, max_length=50)
    notes: str | None = None

    # Geolocation from the mobile device at inspection start
    geo_lat: float | None = Field(None, ge=-90.0, le=90.0)
    geo_lon: float | None = Field(None, ge=-180.0, le=180.0)
    location_accuracy: float | None = Field(None, ge=0.0, description="Accuracy in metres")
    location_note: str | None = Field(None, max_length=200)


class InspectionUpdate(BaseModel):
    """Partial update — all fields optional."""
    lot_id: str | None = Field(None, max_length=100)
    procurement_centre: str | None = Field(None, max_length=200)
    officer_name: str | None = Field(None, max_length=100)
    officer_id: str | None = Field(None, max_length=50)
    notes: str | None = None


# ── Output schemas ────────────────────────────────────────────────────────────

class InspectionSummary(BaseModel):
    """Lightweight inspection summary for list responses."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    lot_id: str | None
    procurement_centre: str | None
    officer_name: str | None
    status: str
    created_at: datetime
    finalized_at: datetime | None
    sample_count: int = Field(0, description="Number of captured samples")


class InspectionDetail(BaseModel):
    """Full inspection detail including aggregated stats."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    lot_id: str | None
    procurement_centre: str | None
    officer_name: str | None
    officer_id: str | None
    notes: str | None
    status: str
    geo_lat: float | None
    geo_lon: float | None
    location_accuracy: float | None
    location_note: str | None
    created_at: datetime
    updated_at: datetime
    finalized_at: datetime | None

    # Aggregated stats — computed from samples (populated by service layer)
    total_bulbs: int = 0
    grade_a_count: int = 0
    urs_count: int = 0
    rejected_count: int = 0
    review_count: int = 0
    grade_a_pct: float = 0.0
    urs_pct: float = 0.0
    rejected_pct: float = 0.0

    sample_ids: list[str] = Field(default_factory=list)
    has_report: bool = False
    report_id: str | None = None
