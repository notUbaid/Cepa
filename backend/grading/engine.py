"""
Grading Rules Engine

The central policy decision-making component. Evaluates each onion bulb's
observations (size + defect probabilities) against the active procurement
policy and produces a final classification.

DESIGN PRINCIPLE: The CV system detects observations. The policy engine decides grade.
These are separate concerns. The grading engine NEVER touches image data.
It operates entirely on structured measurement and probability data.

This makes the grading engine:
  - Testable without any CV model or image
  - Swappable when procurement rules change
  - Auditable (all decisions include an explanation)

The grading engine can be run in isolation with pure Python:
  from grading.engine import GradingEngine
  engine = GradingEngine(policy)
  result = engine.evaluate_bulb(size_mm=52.0, damaged_p=0.1, rotten_p=0.05, sprouted_p=0.02)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from cv.confidence import ConfidenceAssessment
from cv.defect_classifier import DefectPrediction
from cv.size_estimator import SizeEstimate
from grading.policy_loader import GradingPolicy

logger = logging.getLogger(__name__)


@dataclass
class BulbGradingResult:
    """
    Per-bulb grading decision from the rules engine.

    All fields are populated regardless of grade — the explanation JSON
    always records which rules were applied and what values were used.
    """
    grade: str          # "GRADE_A" | "URS" | "REJECTED" | "NEEDS_REVIEW"
    confidence_tier: str  # from ConfidenceAssessment
    rejection_reasons: list[str] = field(default_factory=list)
    # explanation: traceable record of which rule produced this result
    # Format: {rule_name: "description of threshold and outcome"}
    explanation: dict = field(default_factory=dict)


class GradingEngine:
    """
    Stateless procurement rule engine.

    Instantiate once with a loaded policy.
    Call evaluate_bulb() for each onion instance.
    Call aggregate_lot() for lot-level statistics.
    """

    def __init__(self, policy: GradingPolicy) -> None:
        self.policy = policy

    def evaluate_bulb(
        self,
        size_estimate: SizeEstimate | None,
        defect_prediction: DefectPrediction | None,
        confidence: ConfidenceAssessment,
    ) -> BulbGradingResult:
        """
        Evaluate a single onion bulb against the loaded policy.

        Args:
            size_estimate: Geometric measurement from size_estimator.
                           None if calibration marker was not detected.
            defect_prediction: Defect probabilities from defect_classifier.
                               None if classification could not run.
            confidence: Confidence tier from confidence.py.

        Returns:
            BulbGradingResult with grade, tier, reasons, and explanation.
        """
        p = self.policy
        reasons: list[str] = []
        explanation: dict[str, str] = {
            "policy_version": p.version,
            "policy_verified": str(p.verified),
            "urs_active": str(p.urs_active),
        }

        # ── UNUSABLE: cannot grade reliably ───────────────────────────────────
        if confidence.tier == "UNUSABLE":
            return BulbGradingResult(
                grade="NEEDS_REVIEW",
                confidence_tier="UNUSABLE",
                rejection_reasons=["CONFIDENCE_UNUSABLE"],
                explanation={
                    **explanation,
                    "reason": "Confidence tier is UNUSABLE — reliable grading not possible.",
                    "confidence_reasons": "; ".join(confidence.reasons),
                },
            )

        # ── Extract booleans from defect predictions ───────────────────────────
        is_rotten = False
        is_damaged = False
        is_sprouted = False

        if defect_prediction is not None:
            is_rotten = defect_prediction.rotten_prob >= p.defect.rotten_threshold
            is_damaged = defect_prediction.damaged_prob >= p.defect.damaged_threshold
            is_sprouted = defect_prediction.sprouted_prob >= p.defect.sprouted_threshold
            explanation["rotten"] = (
                f"rotten_prob={defect_prediction.rotten_prob:.3f} "
                f">= threshold {p.defect.rotten_threshold:.2f} → {'ROTTEN' if is_rotten else 'PASS'}"
            )
            explanation["damaged"] = (
                f"damaged_prob={defect_prediction.damaged_prob:.3f} "
                f">= threshold {p.defect.damaged_threshold:.2f} → {'DAMAGED' if is_damaged else 'PASS'}"
            )
            explanation["sprouted"] = (
                f"sprouted_prob={defect_prediction.sprouted_prob:.3f} "
                f">= threshold {p.defect.sprouted_threshold:.2f} → {'SPROUTED' if is_sprouted else 'PASS'}"
            )
        else:
            explanation["defects"] = "Defect classification not available"

        # ── Hard rejection checks (apply before any size checks) ───────────────
        # These are absolute — no exceptions in any grade category.
        if p.hard_rejection.get("rotten_always_rejected", True) and is_rotten:
            reasons.append("ROTTEN")
        if p.hard_rejection.get("sprouted_always_rejected", True) and is_sprouted:
            reasons.append("SPROUTED")

        # ── Size checks ────────────────────────────────────────────────────────
        size_mm = size_estimate.equivalent_diameter_mm if size_estimate is not None else None
        size_note = "No size measurement available — calibration marker not detected."

        if size_mm is not None:
            urs_min = p.size.urs_min_mm
            urs_max = p.size.urs_max_mm
            ga_min = p.size.grade_a_min_mm
            ga_max = p.size.grade_a_max_mm

            if p.hard_rejection.get("below_urs_min_always_rejected", True) and size_mm < urs_min:
                reasons.append("UNDERSIZED")
                size_note = f"size={size_mm:.1f}mm < urs_min={urs_min:.1f}mm → UNDERSIZED"
            elif p.hard_rejection.get("above_urs_max_always_rejected", True) and size_mm > urs_max:
                reasons.append("OVERSIZED")
                size_note = f"size={size_mm:.1f}mm > urs_max={urs_max:.1f}mm → OVERSIZED"
            else:
                in_grade_a_range = ga_min <= size_mm <= ga_max
                in_urs_range = urs_min <= size_mm <= urs_max
                size_note = (
                    f"size={size_mm:.1f}mm | "
                    f"Grade A range [{ga_min},{ga_max}]: {'IN' if in_grade_a_range else 'OUT'} | "
                    f"URS range [{urs_min},{urs_max}]: {'IN' if in_urs_range else 'OUT'}"
                )

        explanation["size"] = size_note

        # ── If any hard rejection reason was triggered → REJECTED ──────────────
        if reasons:
            return BulbGradingResult(
                grade="REJECTED",
                confidence_tier=confidence.tier,
                rejection_reasons=reasons,
                explanation=explanation,
            )

        # ── No hard rejections — try for Grade A ───────────────────────────────
        if size_mm is not None:
            ga_min, ga_max = p.size.grade_a_min_mm, p.size.grade_a_max_mm
            in_grade_a_range = ga_min <= size_mm <= ga_max

            grade_a_size_ok = in_grade_a_range
            grade_a_rotten_ok = not is_rotten  # always required
            grade_a_sprouted_ok = not is_sprouted  # always required
            # Damaged: Grade A rules may or may not permit damage
            grade_a_damaged_ok = not is_damaged  # strict by default

            if grade_a_size_ok and grade_a_rotten_ok and grade_a_sprouted_ok and grade_a_damaged_ok:
                explanation["grade_decision"] = (
                    f"All Grade A criteria met: size_in_range={grade_a_size_ok}, "
                    f"not_rotten={grade_a_rotten_ok}, not_sprouted={grade_a_sprouted_ok}, "
                    f"not_damaged={grade_a_damaged_ok}"
                )
                return BulbGradingResult(
                    grade="GRADE_A",
                    confidence_tier=confidence.tier,
                    rejection_reasons=[],
                    explanation=explanation,
                )

            # ── Try for URS ─────────────────────────────────────────────────────
            if p.urs_active:
                urs_min, urs_max = p.size.urs_min_mm, p.size.urs_max_mm
                in_urs_range = urs_min <= size_mm <= urs_max

                # URS: size in range, not rotten, not sprouted (damaged allowed)
                urs_size_ok = in_urs_range
                urs_rotten_ok = not is_rotten
                urs_sprouted_ok = not is_sprouted

                if urs_size_ok and urs_rotten_ok and urs_sprouted_ok:
                    explanation["grade_decision"] = (
                        f"URS criteria met: size_in_urs_range={urs_size_ok}, "
                        f"not_rotten={urs_rotten_ok}, not_sprouted={urs_sprouted_ok}. "
                        f"Note: Grade A failed — "
                        f"size_in_grade_a={in_grade_a_range}, "
                        f"damaged={is_damaged}"
                    )
                    return BulbGradingResult(
                        grade="URS",
                        confidence_tier=confidence.tier,
                        rejection_reasons=[],
                        explanation=explanation,
                    )
                else:
                    # Failed URS too
                    urs_fail_reasons = []
                    if not urs_size_ok:
                        urs_fail_reasons.append(f"Size {size_mm:.1f}mm outside URS range")
                    if not urs_rotten_ok:
                        urs_fail_reasons.append("Rotten")
                    if not urs_sprouted_ok:
                        urs_fail_reasons.append("Sprouted")
                    explanation["grade_decision"] = (
                        f"Failed Grade A and URS: {'; '.join(urs_fail_reasons)}"
                    )
                    return BulbGradingResult(
                        grade="REJECTED",
                        confidence_tier=confidence.tier,
                        rejection_reasons=["FAILED_ALL_GRADES"],
                        explanation=explanation,
                    )
            else:
                # URS not active — size outside Grade A = REJECTED
                explanation["grade_decision"] = (
                    f"URS category not active (policy.urs_active=False). "
                    f"Size {size_mm:.1f}mm outside Grade A range. → REJECTED"
                )
                return BulbGradingResult(
                    grade="REJECTED",
                    confidence_tier=confidence.tier,
                    rejection_reasons=["URS_INACTIVE"],
                    explanation=explanation,
                )

        # ── No size measurement → cannot determine Grade A ──────────────────────
        explanation["grade_decision"] = (
            "Size measurement unavailable. Cannot determine Grade A or URS eligibility."
        )
        return BulbGradingResult(
            grade="NEEDS_REVIEW",
            confidence_tier="NEEDS_REVIEW",
            rejection_reasons=["SIZE_UNKNOWN"],
            explanation=explanation,
        )
