"""
Lot-level Aggregator

After all onion instances in a sample (or inspection) have been graded,
the aggregator computes lot-level statistics.

Design note: aggregation happens server-side, not client-side.
The mobile app receives the aggregated statistics — it never computes
grade percentages itself. This ensures the backend is authoritative
for all procurement decisions.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass
class LotAggregation:
    """Lot-level statistics aggregated from individual bulb results."""
    total_bulbs: int = 0
    grade_a_count: int = 0
    urs_count: int = 0
    rejected_count: int = 0
    review_count: int = 0
    edge_cutoff_count: int = 0     # touches_border=True instances

    # Defect occurrence counts (a bulb can contribute to multiple)
    damaged_count: int = 0
    rotten_count: int = 0
    sprouted_count: int = 0
    undersized_count: int = 0

    # Source tracking
    ruleset_version: str = ""
    model_version: str = ""
    sample_count: int = 0

    @property
    def grade_a_pct(self) -> float:
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

    @property
    def sampling_note(self) -> str:
        return (
            f"Lot result based on {self.sample_count} sample image(s). "
            "This does not represent the full consignment. "
            "Additional samples improve lot coverage."
        )

    def defect_counts_json(self) -> str:
        return json.dumps({
            "damaged": self.damaged_count,
            "rotten": self.rotten_count,
            "sprouted": self.sprouted_count,
            "undersize": self.undersized_count,
            "edge_cutoff": self.edge_cutoff_count,
        })


@dataclass
class _BulbSummary:
    """Minimal per-bulb data needed for aggregation."""
    grade: str                 # GRADE_A | URS | REJECTED | NEEDS_REVIEW
    confidence_tier: str       # HIGH | NEEDS_REVIEW | UNUSABLE
    touches_border: bool
    rejection_reasons: list[str]
    is_rotten: bool
    is_damaged: bool
    is_sprouted: bool


def aggregate_lot(
    bulb_summaries: list[_BulbSummary],
    ruleset_version: str,
    model_version: str,
    sample_count: int,
) -> LotAggregation:
    """
    Compute lot-level statistics from a list of graded bulb summaries.

    Args:
        bulb_summaries: All graded OnionInstance records for the lot.
        ruleset_version: The policy version used.
        model_version: The segmentation model version used.
        sample_count: Number of sample images in this inspection.

    Returns:
        LotAggregation with all lot statistics.
    """
    agg = LotAggregation(
        ruleset_version=ruleset_version,
        model_version=model_version,
        sample_count=sample_count,
    )

    for b in bulb_summaries:
        agg.total_bulbs += 1

        if b.touches_border:
            agg.edge_cutoff_count += 1

        match b.grade:
            case "GRADE_A":
                agg.grade_a_count += 1
            case "URS":
                agg.urs_count += 1
            case "REJECTED":
                agg.rejected_count += 1
            case "NEEDS_REVIEW":
                agg.review_count += 1

        if b.is_rotten:
            agg.rotten_count += 1
        if b.is_damaged:
            agg.damaged_count += 1
        if b.is_sprouted:
            agg.sprouted_count += 1
        if "UNDERSIZED" in b.rejection_reasons:
            agg.undersized_count += 1

    return agg


def aggregate_from_db_instances(
    instances,  # list of OnionInstance ORM objects with relationships loaded
    ruleset_version: str,
    model_version: str,
    sample_count: int,
) -> LotAggregation:
    """
    Convenience function that builds summaries from ORM objects and aggregates.
    """
    import json as _json

    summaries: list[_BulbSummary] = []
    for inst in instances:
        defect = inst.defect_observation
        clf = inst.classification_result

        is_rotten = False
        is_damaged = False
        is_sprouted = False

        if defect and defect.final_decision:
            try:
                fd = _json.loads(defect.final_decision)
                is_rotten = fd.get("rotten_prob", 0) >= 0.5
                is_damaged = fd.get("damaged_prob", 0) >= 0.5
                is_sprouted = fd.get("sprouted_prob", 0) >= 0.5
            except Exception:
                pass

        grade = clf.grade if clf else "NEEDS_REVIEW"
        tier = clf.confidence_tier if clf else "NEEDS_REVIEW"
        reasons = []
        if clf and clf.rejection_reasons:
            try:
                reasons = _json.loads(clf.rejection_reasons)
            except Exception:
                pass

        summaries.append(_BulbSummary(
            grade=grade,
            confidence_tier=tier,
            touches_border=inst.touches_border,
            rejection_reasons=reasons,
            is_rotten=is_rotten,
            is_damaged=is_damaged,
            is_sprouted=is_sprouted,
        ))

    return aggregate_lot(summaries, ruleset_version, model_version, sample_count)
