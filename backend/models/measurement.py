"""
Measurement ORM model.

Records the geometric size measurement of an onion bulb, derived from
its segmentation mask and the calibrated mm/pixel scale.

Primary metric: equivalent_diameter_mm — computed as the diameter of a circle
with the same area as the segmentation mask. This is more stable than major-axis
length for near-circular objects and less sensitive to orientation.

IMPORTANT CAVEAT (stored in projection_note and shown in every report):
  A phone camera captures a 2D projection of a 3D spheroid.
  equivalent_diameter_mm is a projected measurement, NOT equivalent to
  a laboratory caliper measurement. The actual 3D diameter may differ
  depending on how the onion was oriented when photographed.
"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from models.onion_instance import OnionInstance

# Standard projection caveat — stored verbatim in DB so reports always carry it
PROJECTION_NOTE = (
    "Projected equivalent diameter from top-view image. "
    "Not equivalent to laboratory caliper measurement. "
    "Actual 3D size may differ based on onion orientation."
)


class Measurement(Base):
    __tablename__ = "measurements"

    # ── Identity ──────────────────────────────────────────────────────────────
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    onion_instance_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("onion_instances.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # 1:1 with OnionInstance
    )

    # ── Primary size metric ───────────────────────────────────────────────────
    # equivalent_diameter_mm: 2 * sqrt(mask_area_px / pi) * mm_per_px
    # This is the value used by the grading engine for size classification.
    equivalent_diameter_mm: Mapped[float] = mapped_column(Float, nullable=False)

    # ── Supplementary ellipse metrics ─────────────────────────────────────────
    # Computed via cv2.fitEllipse on the mask contour.
    # NULL if the contour has < 5 points (OpenCV requirement for ellipse fitting).
    major_axis_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    minor_axis_mm: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Raw pixel data (for reproducibility) ──────────────────────────────────
    mask_area_px: Mapped[int] = mapped_column(Integer, nullable=False)
    # scale_mm_per_px: the calibration value used for THIS measurement.
    # Stored here (not just on the Sample) so measurements are self-contained.
    scale_mm_per_px: Mapped[float] = mapped_column(Float, nullable=False)

    # ── Caveats and flags ─────────────────────────────────────────────────────
    projection_note: Mapped[str] = mapped_column(
        Text, nullable=False, default=PROJECTION_NOTE
    )
    # uncertainty_flag: True when equivalent_diameter_mm is within 3mm of any
    # grading threshold. Triggers NEEDS_REVIEW confidence tier regardless of
    # defect probabilities.
    uncertainty_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── Relationship ──────────────────────────────────────────────────────────
    onion_instance: Mapped[OnionInstance] = relationship(
        "OnionInstance", back_populates="measurement"
    )

    def __repr__(self) -> str:
        return (
            f"<Measurement onion={self.onion_instance_id!r} "
            f"eq_diam={self.equivalent_diameter_mm:.1f}mm "
            f"uncertain={self.uncertainty_flag}>"
        )
