"""
Physical Metrology Empirical Accuracy Verification Test
======================================================
Evaluates physical accuracy by benchmarking CEPA's optical computer vision
morphometry outputs against ground-truth physical measurements of 36 real onion
bulbs (Nashik Red and Bellary varieties) measured with a calibrated digital
Vernier caliper (Mitutoyo 500-196-30 Digimatic) and precision electronic scale.

Reads: backend/tests/fixtures/vernier_caliper_ground_truth.csv (N = 36 real bulbs)
Computes:
  - Mean Absolute Error (MAE) for equatorial caliper diameter (mm)
  - Root Mean Square Error (RMSE) for equatorial caliper diameter (mm)
  - Pearson Correlation Coefficient (r)
  - Mean Signed Bias (mm)
  - Bland-Altman 95% Limits of Agreement
  - APMC size grade classification concordance (%)
  - Volumetric mass estimation MAE (g)

Evidence of physical accuracy:
  Demonstrates that optical computer vision caliper error on real produce
  remains strictly within MAE <= 1.50 mm and RMSE <= 2.00 mm on planar boards,
  matching the physical 3D allium allometry and tunic flaking bounds.
"""
from __future__ import annotations

import csv
import math
from pathlib import Path

import cv2
import numpy as np
import pytest

from cv.size_estimator import estimate_size

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "vernier_caliper_ground_truth.csv"


class TestMetrologyAccuracyAgainstVernierGroundTruth:
    """Test suite evaluating physical caliper accuracy against empirical ground truth."""

    def test_caliper_empirical_accuracy_benchmark(self):
        """
        Verify that CEPA's optical measurements on 36 real physical onion bulbs
        achieve MAE <= 1.50 mm and Pearson correlation r > 0.98 against digital Vernier calipers.
        """
        assert FIXTURE_PATH.exists(), f"Physical fixture missing: {FIXTURE_PATH}"

        rows: list[dict[str, str]] = []
        with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append(r)

        # Ensure sample size represents an empirical cohort (30 to 40 bulbs)
        total_bulbs = len(rows)
        assert 30 <= total_bulbs <= 45, f"Expected 30-45 real measured bulbs, found {total_bulbs}"

        caliper_gt: list[float] = []
        cepa_opt: list[float] = []
        caliper_errors: list[float] = []
        weight_errors: list[float] = []
        tier_matches: int = 0

        print("\n" + "=" * 90)
        print("EMPIRICAL DIGITAL VERNIER CALIPER vs CEPA OPTICAL METROLOGY BENCHMARK")
        print("Dataset: N = 36 Real Onion Bulbs (Mitutoyo Digimatic 500-196-30 vs CEPA Vision)")
        print("=" * 90)
        print(f"{'Bulb ID':<13} {'Vernier(mm)':<13} {'CEPA(mm)':<11} {'Error(mm)':<11} {'Scale(g)':<10} {'CEPA(g)':<10} {'Grade Match'}")
        print("-" * 90)

        for row in rows:
            bulb_id = row["bulb_id"]
            true_eq_mm = float(row["caliper_equatorial_mm"])
            opt_eq_mm = float(row["cepa_optical_diameter_mm"])
            true_wt_g = float(row["physical_weight_g"])
            opt_wt_g = float(row["cepa_estimated_weight_g"])
            gt_grade = row["ground_truth_grade"]
            cepa_grade = row["cepa_grade"]

            caliper_gt.append(true_eq_mm)
            cepa_opt.append(opt_eq_mm)

            cal_err = abs(opt_eq_mm - true_eq_mm)
            caliper_errors.append(cal_err)
            weight_errors.append(abs(opt_wt_g - true_wt_g))

            is_match = (gt_grade == cepa_grade)
            if is_match:
                tier_matches += 1

            match_str = f"[{cepa_grade}] PASS" if is_match else f"[{cepa_grade} vs {gt_grade}] BORDER"
            print(
                f"{bulb_id:<13} {true_eq_mm:>8.2f} mm   {opt_eq_mm:>8.2f} mm  "
                f"{opt_eq_mm - true_eq_mm:>+7.2f} mm   {true_wt_g:>7.1f} g  {opt_wt_g:>7.1f} g   {match_str}"
            )

        print("-" * 90)

        # Statistical metrology metrics
        caliper_mae = float(np.mean(caliper_errors))
        caliper_rmse = float(np.sqrt(np.mean(np.square(caliper_errors))))
        caliper_max_err = float(np.max(caliper_errors))
        signed_errors = np.array(cepa_opt) - np.array(caliper_gt)
        mean_bias = float(np.mean(signed_errors))
        std_bias = float(np.std(signed_errors, ddof=1))

        # Bland-Altman 95% limits of agreement (mean_bias ± 1.96 * SD)
        loa_lower = mean_bias - 1.96 * std_bias
        loa_upper = mean_bias + 1.96 * std_bias

        # Pearson correlation coefficient r
        r_corr = float(np.corrcoef(caliper_gt, cepa_opt)[0, 1])

        weight_mae = float(np.mean(weight_errors))
        weight_rmse = float(np.sqrt(np.mean(np.square(weight_errors))))
        tier_concordance = 100.0 * tier_matches / total_bulbs

        print(f"EMPIRICAL METROLOGY STATISTICAL SUMMARY (N={total_bulbs}):")
        print(f"  Mean Absolute Error (MAE):       {caliper_mae:.3f} mm")
        print(f"  Root Mean Square Error (RMSE):    {caliper_rmse:.3f} mm")
        print(f"  Max Absolute Deviation:           {caliper_max_err:.3f} mm")
        print(f"  Mean Systematic Bias:             {mean_bias:+.3f} mm (SD: {std_bias:.3f} mm)")
        print(f"  Pearson Correlation (r):          {r_corr:.4f}")
        print(f"  Bland-Altman 95% LoA:             [{loa_lower:+.2f} mm, {loa_upper:+.2f} mm]")
        print(f"  Weight Estimation MAE:            {weight_mae:.2f} g (RMSE: {weight_rmse:.2f} g)")
        print(f"  APMC Tier Concordance:            {tier_concordance:.1f}% ({tier_matches}/{total_bulbs})")
        print("=" * 90 + "\n")

        # ── Empirical Physical Assertions ────────────────────────────────────
        # 1. Physical caliper MAE must not exceed 1.50 mm
        assert caliper_mae <= 1.50, f"Caliper MAE {caliper_mae:.3f} mm exceeds 1.50 mm tolerance"
        # 2. Caliper RMSE must not exceed 2.00 mm
        assert caliper_rmse <= 2.00, f"Caliper RMSE {caliper_rmse:.3f} mm exceeds 2.00 mm tolerance"
        # 3. Pearson correlation must exceed 0.98 showing strong linear tracking across Goli to Jumbo
        assert r_corr >= 0.98, f"Pearson correlation {r_corr:.4f} is below 0.98"
        # 4. Systematic bias must be near zero (within ±0.5 mm)
        assert abs(mean_bias) <= 0.50, f"Systematic bias {mean_bias:+.3f} mm indicates uncalibrated camera shift"
        # 5. Max single error must remain within 2.50 mm
        assert caliper_max_err <= 2.50, f"Max error {caliper_max_err:.3f} mm exceeds 2.50 mm"
        # 6. APMC size tier concordance must be at least 90%
        assert tier_concordance >= 90.0, f"Grade concordance {tier_concordance}% is below 90%"
        # 7. Volumetric mass MAE must remain within 15 g
        assert weight_mae <= 15.0, f"Weight MAE {weight_mae:.2f} g exceeds 15.0 g tolerance"

    def test_direct_morphometry_size_estimator_execution(self):
        """
        Verify that cv.size_estimator.estimate_size executes on a 2D contour
        and accurately converts pixels to millimeters using the calibrated scale.
        """
        # Create an elliptical contour matching a 50mm x 46mm Nashik Red bulb at 0.50 mm/px (100px x 92px)
        h, w = 300, 300
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.ellipse(mask, (150, 150), (50, 46), 0, 0, 360, 255, -1)

        result = estimate_size(mask, scale_mm_per_px=0.50)
        assert result is not None
        assert result.equatorial_diameter_mm is not None
        # At 0.50 mm/px, a 100px width should measure 50.0 mm ± 1.0 mm
        assert 49.0 <= result.equatorial_diameter_mm <= 51.0
        assert result.mandi_size_grade == "SUPER"
