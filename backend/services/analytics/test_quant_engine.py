"""Unit tests for quant_engine benchmark regression functions.

Run from the backend directory:
    python -m pytest services/analytics/test_quant_engine.py -v
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from services.analytics.quant_engine import (
    _assess_data_quality,
    calculate_alpha_beta,
    calculate_information_ratio,
    calculate_tracking_error,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _s(returns: list[float] | np.ndarray) -> pd.Series:
    return pd.Series(returns, dtype=float)


RNG = np.random.default_rng(42)


# ══════════════════════════════════════════════════════════════════════════════
# calculate_alpha_beta
# ══════════════════════════════════════════════════════════════════════════════

class TestAlphaBeta:
    def test_perfectly_correlated_alpha_zero_beta_one(self):
        """portfolio == benchmark → alpha ≈ 0, beta ≈ 1, r² ≈ 1."""
        rb = RNG.normal(0.0008, 0.010, 200)
        rp = rb.copy()
        result = calculate_alpha_beta(_s(rp), _s(rb))
        assert result["beta"] == pytest.approx(1.0, abs=1e-9)
        assert result["r_squared"] == pytest.approx(1.0, abs=1e-9)
        assert result["correlation"] == pytest.approx(1.0, abs=1e-9)
        assert abs(result["alpha"]) < 0.01  # < 0.01% annual

    def test_inverse_correlated_beta_minus_one(self):
        """portfolio == -benchmark → beta ≈ -1, r² ≈ 1, correlation ≈ -1."""
        rb = RNG.normal(0.0008, 0.010, 200)
        rp = -rb
        result = calculate_alpha_beta(_s(rp), _s(rb))
        assert result["beta"] == pytest.approx(-1.0, abs=1e-9)
        assert result["r_squared"] == pytest.approx(1.0, abs=1e-9)
        assert result["correlation"] == pytest.approx(-1.0, abs=1e-9)

    def test_flat_portfolio_beta_zero(self):
        """All portfolio returns == 0 → beta ≈ 0, alpha ≈ 0."""
        rb = RNG.normal(0.0008, 0.010, 200)
        rp = np.zeros(len(rb))
        # corrcoef(constant, x) emits an expected divide-by-zero warning; suppress it.
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            result = calculate_alpha_beta(_s(rp), _s(rb))
        # cov(0, rb) = 0, so beta = 0
        assert result["beta"] == pytest.approx(0.0, abs=1e-9)
        # daily_alpha = mean(0) - 0 * mean(rb) = 0 → annual alpha = 0
        assert abs(result["alpha"]) < 0.01

    def test_beta_scaled_portfolio(self):
        """portfolio == 2 × benchmark → beta ≈ 2, r² ≈ 1, alpha ≈ 0."""
        rb = RNG.normal(0.0008, 0.010, 200)
        rp = 2.0 * rb
        result = calculate_alpha_beta(_s(rp), _s(rb))
        assert result["beta"] == pytest.approx(2.0, abs=1e-9)
        assert result["r_squared"] == pytest.approx(1.0, abs=1e-9)
        assert abs(result["alpha"]) < 0.01

    def test_random_noise_low_r_squared(self):
        """Independent portfolio and benchmark → r² near 0."""
        rng2 = np.random.default_rng(99)
        rb = _s(rng2.normal(0.0005, 0.010, 300))
        rp = _s(rng2.normal(0.0005, 0.010, 300))
        result = calculate_alpha_beta(rp, rb)
        assert (result["r_squared"] or 0.0) < 0.15
        assert abs(result["correlation"] or 0.0) < 0.30

    def test_compound_annualization_formula(self):
        """Constant 0.001 daily excess over benchmark → annual alpha = ((1.001)^252-1)*100.

        A flat (all-zeros) benchmark has var=0 so we use a near-flat one instead
        (tiny gaussian noise) which keeps var > 0 while keeping beta ≈ 0.
        """
        rng2 = np.random.default_rng(7)
        n = 252
        rb = _s(rng2.normal(0.0, 1e-6, n))  # near-flat, var > 0
        rp = _s(rb.values + 0.001)            # constant 0.1%/day excess
        result = calculate_alpha_beta(rp, rb)
        expected = ((1.001) ** 252 - 1.0) * 100.0  # ≈ 28.13%
        assert result["alpha"] == pytest.approx(expected, rel=1e-3)

    def test_negative_daily_alpha_uses_compound(self):
        """Negative constant daily excess → compound annualisation (not linear)."""
        rng2 = np.random.default_rng(7)
        n = 252
        rb = _s(rng2.normal(0.0, 1e-6, n))
        rp = _s(rb.values - 0.001)  # constant -0.1%/day
        result = calculate_alpha_beta(rp, rb)
        expected = ((1.0 - 0.001) ** 252 - 1.0) * 100.0  # ≈ -22.10%
        assert result["alpha"] == pytest.approx(expected, rel=1e-3)

    def test_insufficient_data_returns_none(self):
        """< 10 observations → all None (minimum for stable OLS)."""
        rp = _s([0.01, 0.02, -0.01, 0.005, 0.003])
        rb = _s([0.01, 0.02, -0.01, 0.005, 0.003])
        result = calculate_alpha_beta(rp, rb)
        assert result["alpha"] is None
        assert result["beta"] is None
        assert result["r_squared"] is None
        assert result["correlation"] is None

    def test_zero_benchmark_variance_returns_none(self):
        """Flat benchmark (var=0) → cannot compute beta → all None."""
        rb = _s(np.zeros(50))
        rp = _s(RNG.normal(0.001, 0.01, 50))
        result = calculate_alpha_beta(rp, rb)
        assert result["beta"] is None

    def test_no_linear_scaling_anomaly(self):
        """Verify compound formula, not linear scaling, is used for daily alpha.

        daily_alpha = 0.005 (0.5%/day constant excess):
          Linear formula would give: 0.005 * 252 * 100 = 126%
          Compound formula gives:    ((1.005)^252 - 1)*100 ≈ 251%
        These differ by > 2×, confirming we take the compound path.
        """
        rng2 = np.random.default_rng(7)
        n = 252
        rb = _s(rng2.normal(0.0, 1e-6, n))
        rp = _s(rb.values + 0.005)
        result = calculate_alpha_beta(rp, rb)
        linear_would_give = 0.005 * 252 * 100.0  # 126%
        compound_expected = ((1.005) ** 252 - 1.0) * 100.0  # ≈ 251%
        assert result["alpha"] != pytest.approx(linear_would_give, rel=0.01)
        assert result["alpha"] == pytest.approx(compound_expected, rel=1e-3)


# ══════════════════════════════════════════════════════════════════════════════
# _assess_data_quality
# ══════════════════════════════════════════════════════════════════════════════

class TestAssessDataQuality:
    def test_insufficient_very_short(self):
        q = _assess_data_quality(10, alpha=50.0, beta=0.8, r_squared=0.5, tracking_error_pct=5.0)
        assert q["data_quality"] == "INSUFFICIENT"
        assert q["statistical_confidence"] == "UNRELIABLE"
        assert "LOW_SAMPLE_SIZE" in q["warnings"]
        assert q["sample_size"] == 10

    def test_low_sample_size_between_20_and_59(self):
        q = _assess_data_quality(45, alpha=10.0, beta=0.8, r_squared=0.5, tracking_error_pct=5.0)
        assert q["data_quality"] == "LOW"
        assert q["statistical_confidence"] == "LOW"
        assert "LOW_SAMPLE_SIZE" in q["warnings"]

    def test_exactly_60_is_moderate(self):
        q = _assess_data_quality(60, alpha=10.0, beta=0.8, r_squared=0.5, tracking_error_pct=5.0)
        assert q["data_quality"] == "MODERATE"
        assert q["statistical_confidence"] == "MODERATE"
        assert "LOW_SAMPLE_SIZE" not in q["warnings"]

    def test_good_quality_one_year_plus(self):
        q = _assess_data_quality(300, alpha=5.0, beta=0.8, r_squared=0.65, tracking_error_pct=8.0)
        assert q["data_quality"] == "GOOD"
        assert q["statistical_confidence"] == "HIGH"
        assert q["warnings"] == []

    def test_unreliable_regression_flag(self):
        """High alpha + low r² → UNRELIABLE_REGRESSION, overrides confidence."""
        q = _assess_data_quality(200, alpha=150.0, beta=0.05, r_squared=0.04, tracking_error_pct=5.0)
        assert "UNRELIABLE_REGRESSION" in q["warnings"]
        assert q["statistical_confidence"] == "UNRELIABLE"

    def test_suspect_alpha_flag(self):
        q = _assess_data_quality(200, alpha=60.0, beta=0.3, r_squared=0.03, tracking_error_pct=5.0)
        assert "SUSPECT_ALPHA" in q["warnings"]
        assert "UNRELIABLE_REGRESSION" not in q["warnings"]

    def test_near_zero_te_flag(self):
        q = _assess_data_quality(200, alpha=5.0, beta=1.0, r_squared=0.9, tracking_error_pct=0.05)
        assert "NEAR_ZERO_TE" in q["warnings"]

    def test_none_alpha_does_not_crash(self):
        q = _assess_data_quality(200, alpha=None, beta=None, r_squared=None, tracking_error_pct=None)
        assert q["data_quality"] == "MODERATE"
        assert isinstance(q["warnings"], list)

    def test_low_sample_overrides_unreliable_regression_to_unreliable(self):
        """Short history with bad regression: should include both warnings."""
        q = _assess_data_quality(30, alpha=200.0, beta=0.01, r_squared=0.01, tracking_error_pct=5.0)
        assert "LOW_SAMPLE_SIZE" in q["warnings"]
        assert "UNRELIABLE_REGRESSION" in q["warnings"]
        assert q["statistical_confidence"] == "UNRELIABLE"


# ══════════════════════════════════════════════════════════════════════════════
# calculate_tracking_error
# ══════════════════════════════════════════════════════════════════════════════

class TestTrackingError:
    def test_identical_returns_zero_te(self):
        """portfolio == benchmark → active returns = 0 → TE = 0."""
        rb = _s(RNG.normal(0.001, 0.01, 100))
        te = calculate_tracking_error(rb.copy(), rb)
        assert te == pytest.approx(0.0, abs=0.001)

    def test_positive_te_for_divergent_series(self):
        rng2 = np.random.default_rng(77)
        rb = _s(rng2.normal(0.001, 0.010, 100))
        rp = _s(rng2.normal(0.001, 0.015, 100))
        te = calculate_tracking_error(rp, rb)
        assert te is not None and te > 0.0

    def test_te_annualized_correctly(self):
        """Active returns of constant 1% daily → std=0 → TE=0 (no variation)."""
        rb = _s(np.zeros(100))
        rp = _s(np.full(100, 0.01))  # constant 1%/day excess
        te = calculate_tracking_error(rp, rb)
        assert te == pytest.approx(0.0, abs=0.001)

    def test_known_std_gives_known_te(self):
        """Active returns with known std should annualize to std * sqrt(252) * 100."""
        rng2 = np.random.default_rng(55)
        active = rng2.normal(0.0, 0.01, 500)  # daily std = 1%
        rb = _s(np.zeros(500))
        rp = _s(active)
        te = calculate_tracking_error(rp, rb)
        expected = float(np.std(active, ddof=1)) * math.sqrt(252) * 100
        assert te == pytest.approx(expected, rel=1e-4)

    def test_insufficient_data_returns_none(self):
        rp = _s([0.01, 0.02, 0.01])
        rb = _s([0.01, 0.02, 0.01])
        assert calculate_tracking_error(rp, rb) is None


# ══════════════════════════════════════════════════════════════════════════════
# calculate_information_ratio
# ══════════════════════════════════════════════════════════════════════════════

class TestInformationRatio:
    def test_zero_te_returns_none(self):
        """Identical returns → TE=0 → IR undefined → None."""
        rb = _s(RNG.normal(0.001, 0.01, 50))
        ir = calculate_information_ratio(rb.copy(), rb)
        assert ir is None

    def test_positive_active_return_positive_ir(self):
        rng2 = np.random.default_rng(33)
        rb = _s(rng2.normal(0.0005, 0.010, 200))
        rp = _s(rb.values + rng2.normal(0.001, 0.008, 200))  # positive mean active
        ir = calculate_information_ratio(rp, rb)
        assert ir is not None and ir > 0.0

    def test_ir_formula_correctness(self):
        """Verify IR = mean(active)*252 / (std(active)*sqrt(252)) on synthetic data."""
        rng2 = np.random.default_rng(11)
        active = rng2.normal(0.001, 0.012, 300)
        rb = _s(np.zeros(300))
        rp = _s(active)
        ir = calculate_information_ratio(rp, rb)
        expected = (float(np.mean(active)) * 252) / (float(np.std(active, ddof=1)) * math.sqrt(252))
        assert ir == pytest.approx(expected, rel=1e-4)

    def test_insufficient_data_returns_none(self):
        rp = _s([0.01, 0.02, 0.01, 0.005])
        rb = _s([0.01, 0.02, 0.01, 0.005])
        assert calculate_information_ratio(rp, rb) is None
