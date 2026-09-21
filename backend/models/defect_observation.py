"""
DefectObservation ORM model.

Records the per-onion defect probabilities from the CV defect classifier.
Defects are treated as independent binary attributes (multi-label), not as
mutually exclusive classes. A single onion can be simultaneously damaged
AND sprouted AND rotten.

Preserves both the original model output and any human corrections separately.
The final_decision field records what was actually used for grading.
This separation is critical for audit and model evaluation.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from models.onion_instance import OnionInstance


class DefectObservation(Base):
    __tablename__ = "defect_observations"

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

    # ── Model predictions (sigmoid probabilities, 0.0–1.0 each) ──────────────
    # These are INDEPENDENT probabilities, not a softmax distribution.
    # Each value answers: "How likely is this specific defect visible?"
    damaged_prob: Mapped[float] = mapped_column(Float, nullable=False)
    rotten_prob: Mapped[float] = mapped_column(Float, nullable=False)
    sprouted_prob: Mapped[float] = mapped_column(Float, nullable=False)

    # ── Model provenance ──────────────────────────────────────────────────────
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    # is_mock: True when MockDefectClassifier was used (clearly labelled in reports)
    is_mock: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # raw_model_output: verbatim model output preserved for audit and reanalysis.
    # Stored as JSON string. Never overwritten after initial write.
    raw_model_output: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON

    # ── Human correction ──────────────────────────────────────────────────────
    # human_correction: JSON string with corrected probabilities/flags.
    # NULL means no correction was made.
    # Example: {"damaged_prob": 0.9, "rotten_prob": 0.1, "sprouted_prob": 0.0}
    human_correction: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    corrected_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    corrected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # ── Final decision ────────────────────────────────────────────────────────
    # final_decision: the values actually used by the grading engine.
    # Equals raw model output when human_correction is NULL.
    # Equals human correction when an officer has overridden.
    # JSON string: {"damaged_prob": ..., "rotten_prob": ..., "sprouted_prob": ...}
    final_decision: Mapped[str] = mapped_column(Text, nullable=False)

    # ── Relationship ──────────────────────────────────────────────────────────
    onion_instance: Mapped[OnionInstance] = relationship(
        "OnionInstance", back_populates="defect_observation"
    )

    def __repr__(self) -> str:
        return (
            f"<DefectObservation onion={self.onion_instance_id!r} "
            f"D={self.damaged_prob:.2f} R={self.rotten_prob:.2f} S={self.sprouted_prob:.2f} "
            f"mock={self.is_mock}>"
        )
