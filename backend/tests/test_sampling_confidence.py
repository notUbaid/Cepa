"""
Unit tests for Clopper-Pearson exact confidence intervals and sample size sufficiency.
Validates statistical guarantees under ISO 2859-1 lot appraisal.
"""
import pytest
from grading.statistics import (
    compute_clopper_pearson_interval,
    calculate_sample_size_needed,
    evaluate_lot_statistics,
)


def test_clopper_pearson_zero_defects():
    # 0 defects in 10 bulbs: exact upper bound 1 - 0.025^(1/10) = ~30.8%
    lower, upper = compute_clopper_pearson_interval(0, 10, confidence=0.95)
    assert lower == 0.0
    assert 30.5 <= upper <= 31.0


def test_clopper_pearson_all_defects():
    # 10 defects in 10 bulbs: exact lower bound 0.025^(1/10) = ~69.1% or 69.2%
    lower, upper = compute_clopper_pearson_interval(10, 10, confidence=0.95)
    assert 69.0 <= lower <= 69.5
    assert upper == 100.0


def test_clopper_pearson_two_in_twenty():
    # 2 defects in 20 bulbs: textbook beta interval ~ [1.2%, 31.7%]
    lower, upper = compute_clopper_pearson_interval(2, 20, confidence=0.95)
    assert 1.0 <= lower <= 1.5
    assert 31.0 <= upper <= 32.0


def test_clopper_pearson_empty():
    lower, upper = compute_clopper_pearson_interval(0, 0)
    assert lower == 0.0
    assert upper == 0.0


def test_sample_size_needed_under_sampled():
    # 2 defects out of 20 bulbs (10% defect rate), target error 5%
    # N* = ceil(1.96^2 * 0.1 * 0.9 / 0.05^2) = 139 bulbs
    res = calculate_sample_size_needed(2, 20, target_moe_pct=5.0)
    assert res["target_margin_of_error_pct"] == 5.0
    assert res["recommended_total_sample"] == 139
    assert res["current_sample_size"] == 20
    assert res["additional_bulbs_needed"] == 119
    assert res["is_sample_sufficient"] is False
    assert res["current_margin_of_error_pct"] > 5.0


def test_sample_size_needed_sufficient():
    # 15 defects out of 150 bulbs (10% defect rate), target error 5%
    # N* = 139 bulbs <= 150 current bulbs
    res = calculate_sample_size_needed(15, 150, target_moe_pct=5.0)
    assert res["recommended_total_sample"] == 139
    assert res["current_sample_size"] == 150
    assert res["additional_bulbs_needed"] == 0
    assert res["is_sample_sufficient"] is True


def test_evaluate_lot_statistics_integration():
    stats = evaluate_lot_statistics(
        total_bulbs=25,
        grade_a_count=18,
        urs_count=4,
        rejected_count=3,
        rotten_count=1,
        sprouted_count=1,
    )
    assert hasattr(stats, "clopper_pearson_defect_ci")
    assert hasattr(stats, "sampling_sufficiency")
    assert isinstance(stats.clopper_pearson_defect_ci, tuple)
    assert len(stats.clopper_pearson_defect_ci) == 2
    assert stats.clopper_pearson_defect_ci[0] <= stats.clopper_pearson_defect_ci[1]
    assert stats.sampling_sufficiency["current_sample_size"] == 25
    assert "additional_bulbs_needed" in stats.sampling_sufficiency
