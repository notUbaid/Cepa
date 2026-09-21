"""
Unit tests for the Grading Engine and Policy Loader.

These tests run without any CV model or camera image — proving that the
domain rules engine is completely decoupled from the computer vision layer.
"""
from pathlib import Path
import pytest

from cv.confidence import ConfidenceAssessment, assess_confidence
from cv.defect_classifier import DefectPrediction
from cv.size_estimator import SizeEstimate
from grading.aggregator import _BulbSummary, aggregate_lot
from grading.engine import GradingEngine
from grading.policy_loader import GradingPolicy, SizeThresholds, DefectThresholds, ReviewThresholds, load_policy


@pytest.fixture
def demo_policy() -> GradingPolicy:
    policies_dir = Path(__file__).parent.parent / "grading" / "policies"
    return load_policy("DEMO_ASSUMPTION_v1", policies_dir)


@pytest.fixture
def grading_engine(demo_policy: GradingPolicy) -> GradingEngine:
    return GradingEngine(demo_policy)


def _make_bulb(
    size_mm: float | None = 52.0,
    damaged_p: float = 0.05,
    rotten_p: float = 0.02,
    sprouted_p: float = 0.01,
    seg_conf: float = 0.90,
    touches_border: bool = False,
    uncertainty_flag: bool = False,
):
    size_est = None
    if size_mm is not None:
        size_est = SizeEstimate(
            equivalent_diameter_mm=size_mm,
            major_axis_mm=size_mm * 1.05,
            minor_axis_mm=size_mm * 0.95,
            mask_area_px=1000,
            scale_mm_per_px=0.5,
            uncertainty_flag=uncertainty_flag,
        )

    defect_pred = DefectPrediction(
        damaged_prob=damaged_p,
        rotten_prob=rotten_p,
        sprouted_prob=sprouted_p,
        model_version="test-model",
        is_mock=True,
    )

    confidence = assess_confidence(
        segmentation_conf=seg_conf,
        touches_border=touches_border,
        size_estimate=size_est,
        defect_prediction=defect_pred,
    )

    return size_est, defect_pred, confidence


class TestGradingPolicyLoader:
    def test_load_demo_policy_success(self, demo_policy: GradingPolicy):
        assert demo_policy.version == "DEMO_ASSUMPTION_v1"
        assert demo_policy.verified is False
        assert demo_policy.urs_active is True
        assert demo_policy.size.grade_a_min_mm == 45.0
        assert demo_policy.size.grade_a_max_mm == 65.0
        assert demo_policy.size.urs_min_mm == 35.0
        assert demo_policy.size.urs_max_mm == 70.0

    def test_policy_not_found_raises_error(self):
        policies_dir = Path(__file__).parent.parent / "grading" / "policies"
        with pytest.raises(FileNotFoundError):
            load_policy("NON_EXISTENT_POLICY_v999", policies_dir)


class TestGradingEngineBulbEvaluation:
    def test_grade_a_healthy_bulb(self, grading_engine: GradingEngine):
        size, defect, conf = _make_bulb(size_mm=55.0, damaged_p=0.02, rotten_p=0.01, sprouted_p=0.01)
        res = grading_engine.evaluate_bulb(size, defect, conf)

        assert res.grade == "GRADE_A"
        assert res.confidence_tier == "HIGH"
        assert len(res.rejection_reasons) == 0
        assert "All Grade A criteria met" in res.explanation.get("grade_decision", "")

    def test_urs_minor_damaged_bulb(self, grading_engine: GradingEngine):
        # Damaged bulb in Grade A size range falls back to URS (since Grade A rejects damage, but URS allows it)
        size, defect, conf = _make_bulb(size_mm=55.0, damaged_p=0.85, rotten_p=0.01, sprouted_p=0.01)
        res = grading_engine.evaluate_bulb(size, defect, conf)

        assert res.grade == "URS"
        assert res.confidence_tier == "HIGH"
        assert len(res.rejection_reasons) == 0
        assert "URS criteria met" in res.explanation.get("grade_decision", "")

    def test_urs_small_bulb(self, grading_engine: GradingEngine):
        # Size 40.0mm is between URS min (35) and Grade A min (45)
        size, defect, conf = _make_bulb(size_mm=40.0, damaged_p=0.05, rotten_p=0.01, sprouted_p=0.01)
        res = grading_engine.evaluate_bulb(size, defect, conf)

        assert res.grade == "URS"
        assert "URS criteria met" in res.explanation.get("grade_decision", "")

    def test_rotten_bulb_always_rejected(self, grading_engine: GradingEngine):
        # Even with perfect size 50mm, rot triggers hard rejection
        size, defect, conf = _make_bulb(size_mm=50.0, rotten_p=0.75)
        res = grading_engine.evaluate_bulb(size, defect, conf)

        assert res.grade == "REJECTED"
        assert "ROTTEN" in res.rejection_reasons

    def test_sprouted_bulb_always_rejected(self, grading_engine: GradingEngine):
        # Sprouted triggers hard rejection
        size, defect, conf = _make_bulb(size_mm=50.0, sprouted_p=0.80)
        res = grading_engine.evaluate_bulb(size, defect, conf)

        assert res.grade == "REJECTED"
        assert "SPROUTED" in res.rejection_reasons

    def test_undersized_bulb_rejected(self, grading_engine: GradingEngine):
        # Size 28mm is < URS min 35mm
        size, defect, conf = _make_bulb(size_mm=28.0)
        res = grading_engine.evaluate_bulb(size, defect, conf)

        assert res.grade == "REJECTED"
        assert "UNDERSIZED" in res.rejection_reasons

    def test_oversized_bulb_rejected(self, grading_engine: GradingEngine):
        # Size 78mm is > URS max 70mm
        size, defect, conf = _make_bulb(size_mm=78.0)
        res = grading_engine.evaluate_bulb(size, defect, conf)

        assert res.grade == "REJECTED"
        assert "OVERSIZED" in res.rejection_reasons

    def test_touches_border_marks_unusable(self, grading_engine: GradingEngine):
        size, defect, conf = _make_bulb(size_mm=50.0, touches_border=True)
        res = grading_engine.evaluate_bulb(size, defect, conf)

        assert res.confidence_tier == "UNUSABLE"
        assert res.grade == "NEEDS_REVIEW"
        assert "CONFIDENCE_UNUSABLE" in res.rejection_reasons

    def test_missing_size_calibration(self, grading_engine: GradingEngine):
        size, defect, conf = _make_bulb(size_mm=None)
        res = grading_engine.evaluate_bulb(size, defect, conf)

        assert res.grade == "NEEDS_REVIEW"
        assert "SIZE_UNKNOWN" in res.rejection_reasons

    def test_urs_inactive_rejection(self, demo_policy: GradingPolicy):
        # When policy has urs_active=False, small bulb 40mm cannot be URS
        inactive_policy = GradingPolicy(
            version="TEST_NO_URS",
            label="Test No URS",
            source_note="Test",
            verified=False,
            urs_active=False,
            size=demo_policy.size,
            defect=demo_policy.defect,
            review=demo_policy.review,
            grade_a_rules=demo_policy.grade_a_rules,
            urs_rules=demo_policy.urs_rules,
            hard_rejection=demo_policy.hard_rejection,
            rejection_reason_codes=demo_policy.rejection_reason_codes,
        )
        engine = GradingEngine(inactive_policy)
        size, defect, conf = _make_bulb(size_mm=40.0)
        res = engine.evaluate_bulb(size, defect, conf)

        assert res.grade == "REJECTED"
        assert "URS_INACTIVE" in res.rejection_reasons


class TestLotAggregator:
    def test_lot_aggregation_statistics(self):
        bulbs = [
            _BulbSummary("GRADE_A", "HIGH", False, [], False, False, False),
            _BulbSummary("GRADE_A", "HIGH", False, [], False, False, False),
            _BulbSummary("URS", "HIGH", False, [], False, True, False),
            _BulbSummary("REJECTED", "HIGH", False, ["ROTTEN"], True, False, False),
            _BulbSummary("NEEDS_REVIEW", "NEEDS_REVIEW", True, [], False, False, False),
        ]
        agg = aggregate_lot(bulbs, "DEMO_ASSUMPTION_v1", "test-model", 1)

        assert agg.total_bulbs == 5
        assert agg.grade_a_count == 2
        assert agg.urs_count == 1
        assert agg.rejected_count == 1
        assert agg.review_count == 1
        assert agg.edge_cutoff_count == 1

        assert agg.grade_a_pct == 40.0
        assert agg.urs_pct == 20.0
        assert agg.rejected_pct == 20.0
        assert agg.rotten_count == 1
        assert agg.damaged_count == 1
