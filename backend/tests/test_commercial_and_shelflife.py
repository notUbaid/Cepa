"""
Tests for Cold Storage Shelf-Life Predictor and Mandi Commercial Settlement Engine.
"""
from cv.shelf_life import assess_bulb_storageability, compute_lot_storage_advisory
from grading.commercial import calculate_mandi_settlement, DEFAULT_BASE_MSP_INR_PER_QTL


def test_bulb_storageability_healthy():
    profile = assess_bulb_storageability(
        bulb_index=0,
        diameter_mm=52.0,
        black_mold_pct=0.0,
        skin_baldness_pct=2.0,
        circularity=0.92,
        is_double_bulb=False,
        rotten_prob=0.02,
        sprouted_prob=0.01,
        damaged_prob=0.05,
    )
    assert profile.storageability_score >= 85.0
    assert profile.storage_tier == "PREMIUM"
    assert profile.shelf_life_days_est >= 90
    assert len(profile.decay_risk_factors) == 0


def test_bulb_storageability_severe_mold():
    profile = assess_bulb_storageability(
        bulb_index=1,
        diameter_mm=50.0,
        black_mold_pct=22.0,
        skin_baldness_pct=5.0,
        circularity=0.88,
        is_double_bulb=False,
        rotten_prob=0.85,
        sprouted_prob=0.02,
        damaged_prob=0.10,
    )
    assert profile.storageability_score < 40.0
    assert profile.storage_tier in ("RAPID_DISPATCH", "CRITICAL")
    assert profile.shelf_life_days_est <= 20
    assert any("Aspergillus" in r for r in profile.decay_risk_factors)


def test_lot_storage_advisory_premium_batch():
    profiles = [
        assess_bulb_storageability(
            bulb_index=i,
            diameter_mm=50.0 + i,
            black_mold_pct=0.0,
            skin_baldness_pct=3.0,
            circularity=0.90,
            is_double_bulb=False,
            rotten_prob=0.02,
            sprouted_prob=0.01,
            damaged_prob=0.03,
        )
        for i in range(10)
    ]
    advisory = compute_lot_storage_advisory(profiles)
    assert advisory.storage_recommendation == "BUFFER_STOCK_PREMIUM"
    assert advisory.recommended_max_storage_days >= 90
    assert advisory.respiration_risk_level == "LOW"


def test_commercial_settlement_full_payout():
    # 20 bulbs, all Grade A, no defects
    slip = calculate_mandi_settlement(
        total_bulbs=20,
        grade_a_count=20,
        urs_count=0,
        rejected_count=0,
        rotten_count=0,
        sprouted_count=0,
        undersized_count=0,
        oversized_count=0,
        storageability_score=90.0,
    )
    assert slip.settlement_tier == "FULL_MSP_PAYOUT"
    assert slip.procurement_decision == "APPROVED_FOR_PROCUREMENT"
    assert slip.net_payout_rate_inr_per_qtl == DEFAULT_BASE_MSP_INR_PER_QTL
    assert slip.total_dockage_inr_per_qtl == 0.0
    assert len(slip.dockage_items) == 0


def test_commercial_settlement_dockage_proportional():
    # 20 bulbs, 3 undersized (15% vs 5% tolerance = 10% excess)
    slip = calculate_mandi_settlement(
        total_bulbs=20,
        grade_a_count=15,
        urs_count=4,
        rejected_count=1,
        rotten_count=0,
        sprouted_count=0,
        undersized_count=3,
        oversized_count=0,
        storageability_score=75.0,
    )
    assert slip.settlement_tier == "PROPORTIONAL_DOCKAGE"
    assert slip.net_payout_rate_inr_per_qtl < DEFAULT_BASE_MSP_INR_PER_QTL
    assert slip.total_dockage_inr_per_qtl > 0.0
    assert any(item.category == "SIZE_VARIANCE" for item in slip.dockage_items)


def test_commercial_settlement_hard_rejection():
    # 20 bulbs, 4 rotten (20% > 5% tolerance)
    slip = calculate_mandi_settlement(
        total_bulbs=20,
        grade_a_count=10,
        urs_count=4,
        rejected_count=6,
        rotten_count=4,
        sprouted_count=0,
        undersized_count=2,
        oversized_count=0,
        storageability_score=35.0,
    )
    assert slip.settlement_tier == "REJECTED_NO_PAYOUT"
    assert slip.procurement_decision == "CONSIGNMENT_REJECTED"
    assert slip.net_payout_rate_inr_per_qtl == 0.0
