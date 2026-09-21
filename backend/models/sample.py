"""
Sample ORM model.

A Sample represents one captured image within an Inspection.
An Inspection should have ≥1 Sample. Multiple samples can be added to
increase lot coverage. The final grade aggregates across all samples.

Design note: The data model supports multi-sample inspections even if the
Phase 1 demo flow only captures one. This is intentional — the sampling
limitation (one photo ≠ entire truck) is architecturally acknowledged.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from models.inspection import Inspection
    from models.onion_instance import OnionInstance


class Sample(Base):
    __tablename__ = "samples"

    # ── Identity ──────────────────────────────────────────────────────────────
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    inspection_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False
    )
    sample_index: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-based

    # ── Image files ───────────────────────────────────────────────────────────
    # Paths are relative to settings.storage_dir.
    # Absolute paths are never stored — allows moving storage without DB migration.
    image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    processed_image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    image_width_px: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_height_px: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Calibration results ────────────────────────────────────────────────────
    # marker_detected: whether the ChArUco calibration board was found
    marker_detected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    scale_mm_per_px: Mapped[float | None] = mapped_column(Float, nullable=True)
    # perspective_valid: whether homography correction was successfully applied
    perspective_valid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── Quality gate ──────────────────────────────────────────────────────────
    quality_passed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # JSON list of failure codes, e.g. ["image_too_blurry", "too_dark"]
    quality_flags: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON str

    # ── Processing state ──────────────────────────────────────────────────────
    processing_status: Mapped[str] = mapped_column(
        Enum("PENDING", "RUNNING", "DONE", "FAILED", name="sample_processing_status"),
        default="PENDING",
        nullable=False,
    )
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    processing_finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # ── Model provenance ──────────────────────────────────────────────────────
    # Stored at the sample level so each sample's results are independently traceable.
    model_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # ── Geolocation at capture time ───────────────────────────────────────────
    geo_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    geo_lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_accuracy_m: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Timestamps ─────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    inspection: Mapped[Inspection] = relationship("Inspection", back_populates="samples")
    onion_instances: Mapped[list[OnionInstance]] = relationship(
        "OnionInstance",
        back_populates="sample",
        cascade="all, delete-orphan",
        order_by="OnionInstance.instance_index",
    )

    def __repr__(self) -> str:
        return (
            f"<Sample id={self.id!r} idx={self.sample_index} "
            f"status={self.processing_status!r}>"
        )
