"""
OnionInstance ORM model.

Represents a single detected onion bulb within a Sample image.
This is the central entity — all evidence (defect observations,
measurements, classification results) traces back to a specific
detected bulb in a specific image.

Coordinates are in the RECTIFIED image space (after homography).
"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from models.classification_result import ClassificationResult
    from models.defect_observation import DefectObservation
    from models.measurement import Measurement
    from models.sample import Sample


class OnionInstance(Base):
    __tablename__ = "onion_instances"

    # ── Identity ──────────────────────────────────────────────────────────────
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    sample_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("samples.id", ondelete="CASCADE"), nullable=False
    )
    # Zero-based index within the image (for display: instance_index + 1 = "Onion #N")
    instance_index: Mapped[int] = mapped_column(Integer, nullable=False)

    # ── Bounding box (in rectified image pixel coordinates) ───────────────────
    bbox_x: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox_y: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox_w: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox_h: Mapped[int] = mapped_column(Integer, nullable=False)

    # ── Stored file paths (relative to storage_dir) ───────────────────────────
    # mask_path: binary segmentation mask (PNG, 0/255)
    mask_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # crop_path: masked and cropped JPEG of the bulb
    crop_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # ── Segmentation confidence from the detection model ──────────────────────
    segmentation_conf: Mapped[float] = mapped_column(Float, nullable=False)

    # ── Quality flags ─────────────────────────────────────────────────────────
    # touches_border: True if the segmentation mask touches the image edge,
    # indicating the bulb is partially cut off — measurement is unreliable.
    touches_border: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────────
    sample: Mapped[Sample] = relationship("Sample", back_populates="onion_instances")
    defect_observation: Mapped[DefectObservation | None] = relationship(
        "DefectObservation",
        back_populates="onion_instance",
        uselist=False,
        cascade="all, delete-orphan",
    )
    measurement: Mapped[Measurement | None] = relationship(
        "Measurement",
        back_populates="onion_instance",
        uselist=False,
        cascade="all, delete-orphan",
    )
    classification_result: Mapped[ClassificationResult | None] = relationship(
        "ClassificationResult",
        back_populates="onion_instance",
        uselist=False,
        cascade="all, delete-orphan",
    )

    @property
    def display_number(self) -> int:
        """Human-facing number: "Onion #N" where N = instance_index + 1."""
        return self.instance_index + 1

    def __repr__(self) -> str:
        return (
            f"<OnionInstance id={self.id!r} sample={self.sample_id!r} "
            f"idx={self.instance_index} conf={self.segmentation_conf:.2f}>"
        )
