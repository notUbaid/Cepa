"""
Inspection ORM model.

An Inspection represents one complete lot inspection session.
It may contain multiple Samples (one per photograph of the spread).
The final grade aggregates across all samples.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from models.report import Report
    from models.sample import Sample


class InspectionStatus(str):
    DRAFT = "DRAFT"
    CAPTURE = "CAPTURE"
    PROCESSING = "PROCESSING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    REVIEW = "REVIEW"  # legacy alias
    READY_TO_CERTIFY = "READY_TO_CERTIFY"
    FINALIZED = "FINALIZED"


class Inspection(Base):
    __tablename__ = "inspections"

    # ── Identity ──────────────────────────────────────────────────────────────
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # ── Lot / officer metadata (all optional — filled by officer in app) ──────
    lot_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    farmer_id: Mapped[str | None] = mapped_column(String(50), nullable=True)     # AgriStack Farmer ID / State Mandi ID
    farmer_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    procurement_centre: Mapped[str | None] = mapped_column(String(200), nullable=True)
    officer_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    officer_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Assayer Manual Destructive Cut-Test Protocol ──────────────────────────
    cut_test_performed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cut_test_bulbs_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cut_test_internal_defects_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cut_test_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Workflow state machine ────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(30),
        default="DRAFT",
        nullable=False,
    )

    # ── Canonical Provenance Snapshot (frozen at processing time) ────────────
    provenance_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Geolocation (from device GPS — may be null if permission denied) ──────
    # Location is captured at the time of inspection start (not photo capture)
    # to avoid requiring multiple permission prompts. The sample records
    # may store their own location if captured at different times/places.
    geo_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    geo_lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Human-readable location note (e.g., "Location unavailable — permission denied")
    location_note: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # ── Timestamps ─────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    samples: Mapped[list[Sample]] = relationship(
        "Sample",
        back_populates="inspection",
        cascade="all, delete-orphan",
        order_by="Sample.sample_index",
    )
    report: Mapped[Report | None] = relationship(
        "Report",
        back_populates="inspection",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Inspection id={self.id!r} lot={self.lot_id!r} status={self.status!r}>"
