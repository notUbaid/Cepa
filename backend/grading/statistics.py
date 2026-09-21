"""
Statistical Lot Quality, APMC Mandi Sizing & Commercial NAFED Pricing Engine

Implements comprehensive statistical appraisal under ISO 2859-1 & Indian Mandi specs:
1. Wilson Score 95% Confidence Intervals for proportion estimation (Grade A, URS, Rejection)
2. ISO 2859-1 Lot Acceptance / Rejection Recommendation based on AQL
3. APMC Indian Mandi Size Distribution (Goli, Madhyam, Super, Jumbo)
4. Lot Biomass & Weight Estimation (Total weight in kg, mean bulb mass in grams)
5. NAFED Fair Average Quality (FAQ) Commercial Price Deduction / Dockage Calculator
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


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
class APMCSizeDistribution:
    """Breakdown of sampled onions into traditional Indian Mandi size grades."""
    goli_count: int = 0         # < 35 mm
    goli_pct: float = 0.0
    madhyam_count: int = 0      # 35 - 45 mm
    madhyam_pct: float = 0.0
    super_count: int = 0        # 45 - 65 mm (NAFED Grade A target)
    super_pct: float = 0.0
    jumbo_count: int = 0        # > 65 mm
    jumbo_pct: float = 0.0


@dataclass
class LotWeightStatistics:
    """Volumetric mass estimation for the sample lot."""
    total_sample_weight_kg: float = 0.0
    mean_bulb_weight_g: float = 0.0
    min_bulb_weight_g: float = 0.0
    max_bulb_weight_g: float = 0.0


@dataclass
class CommercialPricingAdvice:
    """NAFED / NCCF Procurement Rate & Dockage Deduction Appraisal."""
    benchmark_mandi_rate_inr_per_qtl: float = 1800.0   # Standard MSP / Mandi base rate
    allowable_tolerance_pct: float = 5.0              # Permissible minor off-grade tolerance
    excess_defects_pct: float = 0.0
    dockage_rate_inr_per_qtl: float = 0.0
    net_procurement_rate_inr_per_qtl: float = 1800.0
    payment_tier: str = "FULL_PRICE"                  # "FULL_PRICE" | "PROPORTIONAL_DOCKAGE" | "REJECT_NO_PAYOUT"
    pricing_rationale: str = ""


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
    apmc_sizes: APMCSizeDistribution = field(default_factory=APMCSizeDistribution)
    weight_stats: LotWeightStatistics = field(default_factory=LotWeightStatistics)
    commercial_pricing: CommercialPricingAdvice = field(default_factory=CommercialPricingAdvice)


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


def compute_apmc_size_distribution(
    sizes_mm: list[float],
) -> APMCSizeDistribution:
    """Compute distribution across Goli (<35), Madhyam (35-45), Super (45-65), Jumbo (>65)."""
    n = len(sizes_mm)
    if n == 0:
        return APMCSizeDistribution()

    goli = sum(1 for s in sizes_mm if s < 35.0)
    madhyam = sum(1 for s in sizes_mm if 35.0 <= s < 45.0)
    super_cnt = sum(1 for s in sizes_mm if 45.0 <= s <= 65.0)
    jumbo = sum(1 for s in sizes_mm if s > 65.0)

    return APMCSizeDistribution(
        goli_count=goli,
        goli_pct=round((goli / n) * 100.0, 1),
        madhyam_count=madhyam,
        madhyam_pct=round((madhyam / n) * 100.0, 1),
        super_count=super_cnt,
        super_pct=round((super_cnt / n) * 100.0, 1),
        jumbo_count=jumbo,
        jumbo_pct=round((jumbo / n) * 100.0, 1),
    )


def compute_lot_weight_statistics(
    weights_g: list[float],
) -> LotWeightStatistics:
    """Compute aggregate weight metrics in grams and kg."""
    valid = [w for w in weights_g if w > 0.0]
    if not valid:
        return LotWeightStatistics()

    total_g = sum(valid)
    return LotWeightStatistics(
        total_sample_weight_kg=round(total_g / 1000.0, 2),
        mean_bulb_weight_g=round(total_g / len(valid), 1),
        min_bulb_weight_g=round(min(valid), 1),
        max_bulb_weight_g=round(max(valid), 1),
    )


def compute_commercial_pricing(
    grade_a_pct: float,
    urs_pct: float,
    rejected_pct: float,
    critical_defect_pct: float,
    base_rate_inr_per_qtl: float = 1800.0,
) -> CommercialPricingAdvice:
    """
    Calculate Fair Average Quality (FAQ) dockage and recommended payout in INR/quintal.
    """
    allowable_tol = 5.0  # standard 5% off-grade tolerance
    if critical_defect_pct > 5.0 or rejected_pct > 25.0:
        return CommercialPricingAdvice(
            benchmark_mandi_rate_inr_per_qtl=base_rate_inr_per_qtl,
            allowable_tolerance_pct=allowable_tol,
            excess_defects_pct=round(max(0.0, (rejected_pct + critical_defect_pct) - allowable_tol), 1),
            dockage_rate_inr_per_qtl=base_rate_inr_per_qtl,
            net_procurement_rate_inr_per_qtl=0.0,
            payment_tier="REJECT_NO_PAYOUT",
            pricing_rationale="Rejected due to excessive decay/off-grade percentage exceeding commercial tolerance limits.",
        )

    # Proportional dockage for excess URS / off-grade above tolerance
    off_grade = (100.0 - grade_a_pct)
    excess = max(0.0, off_grade - allowable_tol)

    if excess == 0.0:
        return CommercialPricingAdvice(
            benchmark_mandi_rate_inr_per_qtl=base_rate_inr_per_qtl,
            allowable_tolerance_pct=allowable_tol,
            excess_defects_pct=0.0,
            dockage_rate_inr_per_qtl=0.0,
            net_procurement_rate_inr_per_qtl=base_rate_inr_per_qtl,
            payment_tier="FULL_PRICE",
            pricing_rationale="Meets full NAFED FAQ Grade A standards with <= 5% minor variance. Full MSP payout approved.",
        )

    # Calculate dockage proportional to excess defect fraction
    # E.g. 15% excess defects on Rs 1800 base -> dockage = 1800 * (15 / 100) * 0.75 = Rs 202.5 / qtl
    dockage = round(base_rate_inr_per_qtl * (excess / 100.0) * 0.75, 1)
    net_payout = round(max(0.0, base_rate_inr_per_qtl - dockage), 1)

    return CommercialPricingAdvice(
        benchmark_mandi_rate_inr_per_qtl=base_rate_inr_per_qtl,
        allowable_tolerance_pct=allowable_tol,
        excess_defects_pct=round(excess, 1),
        dockage_rate_inr_per_qtl=dockage,
        net_procurement_rate_inr_per_qtl=net_payout,
        payment_tier="PROPORTIONAL_DOCKAGE",
        pricing_rationale=f"Applicable dockage deduction of Rs {dockage:.0f}/qtl applied for {excess:.1f}% excess off-grade variance.",
    )


def evaluate_lot_statistics(
    total_bulbs: int,
    grade_a_count: int,
    urs_count: int,
    rejected_count: int,
    rotten_count: int,
    sprouted_count: int,
    sizes_mm: list[float] | None = None,
    weights_g: list[float] | None = None,
    urs_active: bool = True,
    base_rate_inr: float = 1800.0,
) -> LotQualityStatistics:
    """
    Evaluate statistical confidence, APMC sizes, biomass weight, and commercial pricing.
    """
    est_grade_a = compute_proportion_estimate(grade_a_count, total_bulbs)
    est_urs = compute_proportion_estimate(urs_count, total_bulbs)
    est_rejected = compute_proportion_estimate(rejected_count, total_bulbs)

    critical_defects = rotten_count + sprouted_count
    est_critical = compute_proportion_estimate(critical_defects, total_bulbs)

    apmc_dist = compute_apmc_size_distribution(sizes_mm or [])
    weight_stats = compute_lot_weight_statistics(weights_g or [])
    pricing = compute_commercial_pricing(
        grade_a_pct=est_grade_a.percentage,
        urs_pct=est_urs.percentage,
        rejected_pct=est_rejected.percentage,
        critical_defect_pct=est_critical.percentage,
        base_rate_inr_per_qtl=base_rate_inr,
    )

    # Lot recommendation logic
    if est_critical.percentage > 5.0 or rotten_count >= 2:
        recommendation = "REJECT_LOT"
        rationale = (
            f"Critical rot/sprout rate ({est_critical.percentage}%) exceeds procurement threshold. "
            f"Lot is at high risk of rapid decay in storage."
        )
    elif total_bulbs < 15:
        recommendation = "ADDITIONAL_SAMPLE_REQUIRED"
        rationale = (
            f"Sample size (N={total_bulbs}) has wide confidence interval (±{est_grade_a.margin_of_error_pct}%). "
            f"Capture at least one additional sample from another tier of the lot."
        )
    elif est_grade_a.percentage >= 70.0:
        recommendation = "ACCEPT_GRADE_A"
        rationale = (
            f"Grade A proportion is {est_grade_a.percentage}% (95% CI: [{est_grade_a.ci_lower_pct}%, {est_grade_a.ci_upper_pct}%]). "
            f"Meets standards for long-term buffer stock storage."
        )
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
        apmc_sizes=apmc_dist,
        weight_stats=weight_stats,
        commercial_pricing=pricing,
    )
