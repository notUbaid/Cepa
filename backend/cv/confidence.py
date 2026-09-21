"""
Stage 8: Confidence Tier Assignment

Assigns a confidence tier (HIGH / NEEDS_REVIEW / UNUSABLE) to each
onion instance based on:
  - Segmentation confidence from the detection model
  - Whether size is near any grading threshold (uncertainty_flag)
  - Whether defect probabilities are in the borderline range
  - Whether the instance touches the image border (partial occlusion)

The confidence tier is INDEPENDENT of the grade.
A Grade A onion can be HIGH confidence or NEEDS_REVIEW depending on
how certain the measurements are.

The report must show the confidence tier alongside each grade so that
the procurement officer understands the reliability of each classification.

Never allow a UNUSABLE instance to appear to have a definitive grade.
"""
from __future__ import annotations

from dataclasses import dataclass

from cv.defect_classifier import DefectPrediction
from cv.size_estimator import SizeEstimate

# Thresholds for tier assignment
# These mirror the values in the YAML policy but are enforced by the CV layer,
# not the grading engine — they're about measurement certainty, not procurement rules.
_SEG_CONF_HIGH = 0.70
_SEG_CONF_REVIEW_MIN = 0.40
_DEFECT_PROB_BORDERLINE_LOW = 0.35
_DEFECT_PROB_BORDERLINE_HIGH = 0.65


@dataclass
class ConfidenceAssessment:
    """Confidence tier and explanation for one onion instance."""
    tier: str  # "HIGH" | "NEEDS_REVIEW" | "UNUSABLE"
    reasons: list[str]  # Human-readable reasons for non-HIGH tier


def assess_confidence(
    segmentation_conf: float,
    touches_border: bool,
    size_estimate: SizeEstimate | None,
    defect_prediction: DefectPrediction | None,
) -> ConfidenceAssessment:
    """
    Determine confidence tier for a single onion instance.

    Tier hierarchy (worst wins):
      UNUSABLE > NEEDS_REVIEW > HIGH

    Args:
        segmentation_conf: Detection confidence from segmentation model.
        touches_border: True if mask touches the image edge.
        size_estimate: Geometric measurement result (may be None).
        defect_prediction: Defect classifier output (may be None).
    """
    reasons: list[str] = []
    worst_tier = "HIGH"

    def _downgrade(to: str, reason: str) -> None:
        nonlocal worst_tier
        reasons.append(reason)
        # Tier order: HIGH < NEEDS_REVIEW < UNUSABLE
        tier_order = {"HIGH": 0, "NEEDS_REVIEW": 1, "UNUSABLE": 2}
        if tier_order.get(to, 0) > tier_order.get(worst_tier, 0):
            worst_tier = to

    # ── Border touch → UNUSABLE ────────────────────────────────────────────────
    if touches_border:
        _downgrade("UNUSABLE", "Bulb is partially outside the image frame — measurement unreliable.")

    # ── Low segmentation confidence ────────────────────────────────────────────
    if segmentation_conf < _SEG_CONF_REVIEW_MIN:
        _downgrade("UNUSABLE", f"Very low detection confidence ({segmentation_conf:.0%})")
    elif segmentation_conf < _SEG_CONF_HIGH:
        _downgrade("NEEDS_REVIEW", f"Moderate detection confidence ({segmentation_conf:.0%}) — verify manually.")

    # ── Size near threshold ─────────────────────────────────────────────────────
    if size_estimate is not None and size_estimate.uncertainty_flag:
        _downgrade(
            "NEEDS_REVIEW",
            f"Size ({size_estimate.equivalent_diameter_mm:.1f} mm) is near a grading threshold.",
        )

    # ── Borderline defect probabilities ────────────────────────────────────────
    if defect_prediction is not None:
        for name, prob in [
            ("Damaged", defect_prediction.damaged_prob),
            ("Rotten", defect_prediction.rotten_prob),
            ("Sprouted", defect_prediction.sprouted_prob),
        ]:
            if _DEFECT_PROB_BORDERLINE_LOW <= prob <= _DEFECT_PROB_BORDERLINE_HIGH:
                _downgrade(
                    "NEEDS_REVIEW",
                    f"{name} probability ({prob:.0%}) is borderline — manual inspection recommended.",
                )

    # ── No size estimate ───────────────────────────────────────────────────────
    if size_estimate is None:
        _downgrade(
            "NEEDS_REVIEW",
            "Size could not be measured (calibration marker not detected).",
        )

    return ConfidenceAssessment(tier=worst_tier, reasons=reasons)
