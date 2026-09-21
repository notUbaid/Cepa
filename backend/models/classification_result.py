"""
ClassificationResult ORM model.

Records the final per-bulb procurement classification determined by the
grading rules engine. The grade is derived from the Measurement and
DefectObservation — the rules engine is the only thing that maps
observations → procurement categories.

Key design principle: CV detects observations; the policy engine decides grade.
The ruleset_version field ensures every result is traceable to the exact
set of thresholds that produced it.
"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from models.onion_instance import OnionInstance


class ClassificationResult(Base):
    __tablename__ = "classification_results"

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

    # ── Policy traceability ───────────────────────────────────────────────────
    # ruleset_version: the YAML policy file version that produced this result.
    # Changing the policy does NOT automatically reclassify existing results —
    # a new pipeline run is required.
    ruleset_version: Mapped[str] = mapped_column(String(50), nullable=False)

    # ── Final procurement grade ───────────────────────────────────────────────
    grade: Mapped[str] = mapped_column(
        Enum(
            "GRADE_A",
            "URS",
            "REJECTED",
            "NEEDS_REVIEW",
            name="classification_grade",
        ),
        nullable=False,
    )

    # ── Rejection reason codes (JSON list) ────────────────────────────────────
    # e.g. ["ROTTEN", "UNDERSIZED"] or [] for passing grades
    # These are rule-defined codes from the YAML policy, not free text.
    rejection_reasons: Mapped[str] = mapped_column(Text, nullable=False, default="[]")

    # ── Confidence tier ───────────────────────────────────────────────────────
    # Separate from the grade — tells the officer how much to trust this result.
    confidence_tier: Mapped[str] = mapped_column(
        Enum("HIGH", "NEEDS_REVIEW", "UNUSABLE", name="confidence_tier"),
        nullable=False,
    )

    # ── Explanation ───────────────────────────────────────────────────────────
    # JSON string: which rules triggered, what threshold values were used.
    # Example: {"size_rule": "45.0 ≤ 52.3mm ≤ 65.0 → GRADE_A",
    #            "rotten_rule": "rotten_prob=0.03 < 0.50 → PASS"}
    # This powers the "why was it classified this way?" drilldown in the UI.
    explanation: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    # ── Relationship ──────────────────────────────────────────────────────────
    onion_instance: Mapped[OnionInstance] = relationship(
        "OnionInstance", back_populates="classification_result"
    )

    def __repr__(self) -> str:
        return (
            f"<ClassificationResult onion={self.onion_instance_id!r} "
            f"grade={self.grade!r} tier={self.confidence_tier!r}>"
        )
