"""
Report ORM model.

The finalized inspection report. Generated after the officer reviews
all onion instances and clicks "Finalize". Contains all lot-level
aggregated statistics, references the policy/model versions used,
and stores the PDF path + a shareable token.

A Report can only be generated from a FINALIZED Inspection.
The share_token creates a read-only public link for farmers/centres.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from models.inspection import Inspection


class Report(Base):
    __tablename__ = "reports"

    # ── Identity ──────────────────────────────────────────────────────────────
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    inspection_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("inspections.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # 1:1 with Inspection
    )

    # ── Public-facing report identifier ──────────────────────────────────────
    # report_id is the human-visible ID shown on the printed report / QR code.
    # Uses a separate UUID so the internal DB id is not exposed.
    report_id: Mapped[str] = mapped_column(
        String(36), nullable=False, unique=True, default=lambda: str(uuid.uuid4())
    )

    # ── Shareable token ───────────────────────────────────────────────────────
    # Used to construct the public share link: /api/v1/reports/share/{share_token}
    # Allows farmer and centre to view a read-only report summary without login.
    share_token: Mapped[str] = mapped_column(
        String(36), nullable=False, unique=True, default=lambda: str(uuid.uuid4())
    )

    # ── Generated files ───────────────────────────────────────────────────────
    pdf_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # ── Lot-level statistics ──────────────────────────────────────────────────
    total_bulbs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    grade_a_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    urs_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rejected_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    review_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # edge_cutoff_count: bulbs touching image border — measurement unreliable
    edge_cutoff_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ── Defect counts (JSON) ──────────────────────────────────────────────────
    # e.g. {"damaged": 3, "rotten": 1, "sprouted": 2, "undersize": 4}
    defect_counts: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    # ── Provenance ────────────────────────────────────────────────────────────
    # These fields ensure the result is reproducible and traceable.
    ruleset_version: Mapped[str] = mapped_column(String(50), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # sampling_note: honest statement about sampling coverage
    # e.g. "Lot result based on 1 sample(s). Does not represent the full lot."
    sampling_note: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # ── Geolocation (from Inspection record) ─────────────────────────────────
    geo_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    geo_lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_note: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # ── Officer notes ─────────────────────────────────────────────────────────
    officer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Timestamps ─────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # ── Relationship ──────────────────────────────────────────────────────────
    inspection: Mapped[Inspection] = relationship("Inspection", back_populates="report")

    @property
    def grade_a_pct(self) -> float:
        """Grade A percentage of confidently classified bulbs."""
        if self.total_bulbs == 0:
            return 0.0
        return round(100.0 * self.grade_a_count / self.total_bulbs, 1)

    @property
    def urs_pct(self) -> float:
        if self.total_bulbs == 0:
            return 0.0
        return round(100.0 * self.urs_count / self.total_bulbs, 1)

    @property
    def rejected_pct(self) -> float:
        if self.total_bulbs == 0:
            return 0.0
        return round(100.0 * self.rejected_count / self.total_bulbs, 1)

    def __repr__(self) -> str:
        return (
            f"<Report id={self.report_id!r} inspection={self.inspection_id!r} "
            f"total_bulbs={self.total_bulbs} grade_a={self.grade_a_pct}%>"
        )
