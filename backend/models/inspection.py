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

from sqlalchemy import DateTime, Enum, Float, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from models.report import Report
    from models.sample import Sample


class InspectionStatus(str):
    DRAFT = "DRAFT"
    PROCESSING = "PROCESSING"
    REVIEW = "REVIEW"
    FINALIZED = "FINALIZED"


class Inspection(Base):
    __tablename__ = "inspections"

    # ── Identity ──────────────────────────────────────────────────────────────
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # ── Lot / officer metadata (all optional — filled by officer in app) ──────
    lot_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    procurement_centre: Mapped[str | None] = mapped_column(String(200), nullable=True)
    officer_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    officer_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Workflow state ────────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        Enum("DRAFT", "PROCESSING", "REVIEW", "FINALIZED", name="inspection_status"),
        default="DRAFT",
        nullable=False,
    )

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
