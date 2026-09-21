"""
Statistical Lot Quality & Sampling Uncertainty Engine

Implements statistical estimation for agricultural sampling under ISO 2859-1:
1. Wilson Score 95% Confidence Intervals for proportion estimation (Grade A, URS, Rejection)
2. Sampling Error Margin (Margin of Error)
3. ISO 2859-1 Lot Acceptance / Rejection Recommendation based on AQL
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class ProportionEstimate:
    """Proportion point estimate with 95% Wilson Score Confidence Interval."""
    count: int
    total: int
    percentage: float
    ci_lower_pct: float
    ci_upper_pct: float
    margin_of_error_pct: float


@dataclass
class LotQualityStatistics:
    """Comprehensive statistical appraisal for an inspected lot."""
    total_sample_size: int
    grade_a: ProportionEstimate
    urs: ProportionEstimate
    rejected: ProportionEstimate
    critical_defect_rate: ProportionEstimate
    lot_recommendation: str  # "ACCEPT_GRADE_A" | "ACCEPT_URS" | "REJECT_LOT" | "ADDITIONAL_SAMPLE_REQUIRED"
    recommendation_rationale: str


def compute_wilson_score_interval(
    count: int,
    total: int,
    confidence_z: float = 1.96,  # 95% confidence
) -> tuple[float, float]:
    """
    Compute the Wilson score confidence interval for a binomial proportion.
    Superior to normal approximation when sample size is small or proportion is near 0 or 1.
    """
    if total <= 0:
        return 0.0, 0.0

    p_hat = count / total
    z = confidence_z
    z2 = z * z

    denominator = 1.0 + z2 / total
    centre = p_hat + z2 / (2.0 * total)
    spread = z * math.sqrt((p_hat * (1.0 - p_hat) / total) + (z2 / (4.0 * total * total)))

    lower = max(0.0, (centre - spread) / denominator)
    upper = min(1.0, (centre + spread) / denominator)

    return round(lower * 100.0, 1), round(upper * 100.0, 1)


def compute_proportion_estimate(count: int, total: int) -> ProportionEstimate:
    if total <= 0:
        return ProportionEstimate(0, 0, 0.0, 0.0, 0.0, 0.0)

    pct = round((count / total) * 100.0, 1)
    lower, upper = compute_wilson_score_interval(count, total)
    moe = round((upper - lower) / 2.0, 1)

    return ProportionEstimate(
        count=count,
        total=total,
        percentage=pct,
        ci_lower_pct=lower,
        ci_upper_pct=upper,
        margin_of_error_pct=moe,
    )


def evaluate_lot_statistics(
    total_bulbs: int,
    grade_a_count: int,
    urs_count: int,
    rejected_count: int,
    rotten_count: int,
    sprouted_count: int,
    urs_active: bool = True,
) -> LotQualityStatistics:
    """
    Evaluate statistical confidence and make lot-level procurement recommendation.
    """
    est_grade_a = compute_proportion_estimate(grade_a_count, total_bulbs)
    est_urs = compute_proportion_estimate(urs_count, total_bulbs)
    est_rejected = compute_proportion_estimate(rejected_count, total_bulbs)

    critical_defects = rotten_count + sprouted_count
    est_critical = compute_proportion_estimate(critical_defects, total_bulbs)

    # Lot recommendation logic:
    # 1. Critical rot/sprout rate > 5% -> Hard REJECT_LOT
    if est_critical.percentage > 5.0 or rotten_count >= 2:
        recommendation = "REJECT_LOT"
        rationale = (
            f"Critical rot/sprout rate ({est_critical.percentage}%) exceeds procurement threshold. "
            f"Lot is at high risk of storage decay."
        )
    # 2. Insufficient sample size for definitive high-value buffer stock
    elif total_bulbs < 15:
        recommendation = "ADDITIONAL_SAMPLE_REQUIRED"
        rationale = (
            f"Sample size (N={total_bulbs}) has wide confidence interval (±{est_grade_a.margin_of_error_pct}%). "
            f"Capture at least one additional sample from another tier of the lot."
        )
    # 3. Grade A >= 70%
    elif est_grade_a.percentage >= 70.0:
        recommendation = "ACCEPT_GRADE_A"
        rationale = (
            f"Grade A proportion is {est_grade_a.percentage}% (95% CI: [{est_grade_a.ci_lower_pct}%, {est_grade_a.ci_upper_pct}%]). "
            f"Meets standards for long-term buffer stock storage."
        )
    # 4. Qualifies for URS
    elif urs_active and (est_grade_a.percentage + est_urs.percentage) >= 70.0:
        recommendation = "ACCEPT_URS"
        rationale = (
            f"Combined Grade A + URS proportion is {(est_grade_a.percentage + est_urs.percentage):.1f}%. "
            f"Meets Under Relaxed Specification standards for immediate distribution."
        )
    else:
        recommendation = "REJECT_LOT"
        rationale = (
            f"Off-grade / rejected bulbs ({est_rejected.percentage}%) exceed maximum permissible lot tolerance."
        )

    return LotQualityStatistics(
        total_sample_size=total_bulbs,
        grade_a=est_grade_a,
        urs=est_urs,
        rejected=est_rejected,
        critical_defect_rate=est_critical,
        lot_recommendation=recommendation,
        recommendation_rationale=rationale,
    )
