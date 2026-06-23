"""Phase 4C.6F — Unit tests for timing_intelligence.py.

Pure scoring tests use compute_timing_score() directly (no network).
Regression tests mock fetch_history to verify DR + Thai symbol resolution.
"""
import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch

from services.timing_intelligence import (
    StockTimingResult,
    _classify_momentum,
    _execution_priority,
    _generate_reasons,
    _momentum_score,
    _relative_strength_score,
    _timing_category,
    _trend_score,
    _volume_score,
    compute_timing_score,
)


# ── 1. Strong trend ───────────────────────────────────────────────────────────

def test_strong_trend_above_sma50():
    """Price above SMA50 → trend_score=40."""
    result = compute_timing_score(
        symbol="TEST",
        price=110.0,
        sma20=105.0,
        sma50=100.0,
        sma200=90.0,
        rsi=60.0,
        current_volume=None,
        avg_volume_20d=None,
        stock_return_20d=None,
        benchmark_return_20d=None,
    )
    assert result.trend_score == 40
    assert result.data_available is True
    assert result.momentum == "STRONG_UPTREND"
    assert result.execution_priority in ("HIGH", "MEDIUM")


# ── 2. Weak trend ─────────────────────────────────────────────────────────────

def test_weak_trend_below_sma20_and_sma50():
    """Price below both SMA20 and SMA50 → trend_score=10."""
    assert _trend_score(price=80.0, sma20=90.0, sma50=100.0) == 10


def test_trend_between_sma20_and_sma50():
    """Price between SMA20 (85) and SMA50 (100) → trend_score=25."""
    assert _trend_score(price=90.0, sma20=85.0, sma50=100.0) == 25


# ── 3. RSI scenarios ──────────────────────────────────────────────────────────

def test_rsi_scenarios():
    """All four RSI bands produce the correct momentum scores."""
    assert _momentum_score(62.0) == 30   # 55-70
    assert _momentum_score(50.0) == 20   # 45-55
    assert _momentum_score(40.0) == 10   # 35-45
    assert _momentum_score(28.0) == 5    # <35
    assert _momentum_score(75.0) == 5    # >70
    assert _momentum_score(None) == 20   # missing → neutral


# ── 4. Volume boost ───────────────────────────────────────────────────────────

def test_volume_boost():
    """Current volume > 1.2× average → volume_score=10."""
    assert _volume_score(current_volume=1300.0, avg_volume_20d=1000.0) == 10
    assert _volume_score(current_volume=1199.0, avg_volume_20d=1000.0) == 0
    assert _volume_score(current_volume=None, avg_volume_20d=1000.0) == 0
    assert _volume_score(current_volume=1300.0, avg_volume_20d=0.0) == 0


# ── 5. Relative strength boost ────────────────────────────────────────────────

def test_relative_strength():
    """Excess return >2% = +20, <-2% = 0, else = 10."""
    assert _relative_strength_score(10.0, 5.0) == 20    # outperform by 5%
    assert _relative_strength_score(5.0, 5.0) == 10     # neutral
    assert _relative_strength_score(2.0, 7.0) == 0      # underperform by 5%
    assert _relative_strength_score(None, 5.0) == 10    # missing → neutral


# ── 6. Timing category mapping ────────────────────────────────────────────────

def test_timing_category_mapping():
    """Score bands map to the correct category labels."""
    assert _timing_category(85) == "STRONG"
    assert _timing_category(80) == "STRONG"
    assert _timing_category(79) == "GOOD"
    assert _timing_category(60) == "GOOD"
    assert _timing_category(59) == "NEUTRAL"
    assert _timing_category(40) == "NEUTRAL"
    assert _timing_category(39) == "WEAK"
    assert _timing_category(20) == "WEAK"
    assert _timing_category(19) == "POOR"
    assert _timing_category(0)  == "POOR"


# ── 7. Execution priority mapping ─────────────────────────────────────────────

def test_execution_priority_mapping():
    """Score bands map to the correct priority labels."""
    assert _execution_priority(80) == "HIGH"
    assert _execution_priority(90) == "HIGH"
    assert _execution_priority(60) == "MEDIUM"
    assert _execution_priority(79) == "MEDIUM"
    assert _execution_priority(40) == "LOW"
    assert _execution_priority(59) == "LOW"
    assert _execution_priority(39) == "DEFER"
    assert _execution_priority(0)  == "DEFER"


# ── 8. Reason generation ──────────────────────────────────────────────────────

def test_reason_generation_max_three():
    """Reasons list is capped at 3 and reflects the correct signals."""
    reasons = _generate_reasons(
        trend=40,        # "Price above SMA50"
        rsi=62.0,        # "RSI improving (62)"
        volume=10,       # "Volume expanding"
        rel_strength=20, # "Relative strength outperforming sector"
    )
    assert len(reasons) <= 3
    assert "Price above SMA50" in reasons
    assert "RSI improving (62)" in reasons or any("RSI" in r for r in reasons)


def test_reason_generation_weak_trend():
    """Price below SMA50 and no volume → reason explains the weak signal."""
    reasons = _generate_reasons(trend=10, rsi=30.0, volume=0, rel_strength=10)
    assert "Price below SMA50" in reasons
    assert any("oversold" in r for r in reasons)


# ── 9. Missing data ───────────────────────────────────────────────────────────

def test_missing_price_returns_poor():
    """When price is None, result is POOR with data_available=False."""
    result = compute_timing_score(
        symbol="NODATA",
        price=None,
        sma20=None, sma50=None, sma200=None,
        rsi=None,
        current_volume=None, avg_volume_20d=None,
        stock_return_20d=None, benchmark_return_20d=None,
    )
    assert result.data_available is False
    assert result.timing_score == 0
    assert result.timing_category == "POOR"
    assert result.execution_priority == "DEFER"
    assert len(result.reasons) > 0


def test_partial_missing_data_does_not_crash():
    """Partial data (only price + sma50) should still produce a valid result."""
    result = compute_timing_score(
        symbol="PARTIAL",
        price=150.0,
        sma20=None, sma50=140.0, sma200=None,
        rsi=None,
        current_volume=None, avg_volume_20d=None,
        stock_return_20d=None, benchmark_return_20d=None,
    )
    assert result.data_available is True
    assert result.trend_score == 40   # price > sma50
    assert result.momentum_score == 20  # rsi=None → neutral
    assert isinstance(result.timing_score, int)


# ── 10. Deterministic output ──────────────────────────────────────────────────

def test_deterministic_output():
    """Same inputs always produce identical outputs."""
    kwargs = dict(
        symbol="AAPL",
        price=175.0,
        sma20=170.0,
        sma50=165.0,
        sma200=150.0,
        rsi=58.0,
        current_volume=12_000_000.0,
        avg_volume_20d=10_000_000.0,
        stock_return_20d=4.5,
        benchmark_return_20d=2.0,
    )
    r1 = compute_timing_score(**kwargs)
    r2 = compute_timing_score(**kwargs)

    assert r1.timing_score == r2.timing_score
    assert r1.timing_category == r2.timing_category
    assert r1.momentum == r2.momentum
    assert r1.execution_priority == r2.execution_priority
    assert r1.reasons == r2.reasons
    assert r1.trend_score == r2.trend_score
    assert r1.momentum_score == r2.momentum_score
    assert r1.relative_strength_score == r2.relative_strength_score
    assert r1.volume_score == r2.volume_score


# ── Momentum classification ───────────────────────────────────────────────────

def test_momentum_classification():
    """SMA alignment maps to correct momentum labels."""
    assert _classify_momentum(110.0, 100.0, 90.0) == "STRONG_UPTREND"
    assert _classify_momentum(90.0, 100.0, 110.0) == "STRONG_DOWNTREND"
    assert _classify_momentum(105.0, 100.0, None) == "UPTREND"   # sma20 > sma50 by >1%
    assert _classify_momentum(95.0, 100.0, None) == "DOWNTREND"  # sma20 < sma50 by >1%
    assert _classify_momentum(100.5, 100.0, None) == "SIDEWAYS"  # within 1% band
    assert _classify_momentum(None, None, None) == "SIDEWAYS"    # no data


# ── Symbol normalization regression tests ─────────────────────────────────────
# These tests mock fetch_history so no network is needed, but exercise the full
# score_timing_batch() path including get_yfinance_symbol() resolution.


def _make_price_history(n: int = 252, base_price: float = 100.0) -> pd.DataFrame:
    """Synthetic 1-year daily OHLCV DataFrame with a gentle uptrend."""
    prices = np.linspace(base_price * 0.85, base_price, n)
    idx = pd.date_range(end="2026-06-22", periods=n, freq="B", tz="UTC")
    return pd.DataFrame(
        {
            "Open":   prices * 0.999,
            "High":   prices * 1.010,
            "Low":    prices * 0.990,
            "Close":  prices,
            "Volume": np.full(n, 1_500_000.0),
        },
        index=idx,
    )


@patch("services.timing_intelligence.fetch_history")
def test_regression_nvda01_resolves_and_scores(mock_fetch):
    """NVDA01 → get_yfinance_symbol → NVDA → valid history → data_available=True."""
    mock_fetch.return_value = _make_price_history()
    from services.timing_intelligence import score_timing_batch
    results = score_timing_batch(["NVDA01"])
    assert len(results) == 1
    r = results[0]
    assert r.symbol == "NVDA01"
    assert r.data_available is True
    assert r.timing_score > 0
    assert r.execution_priority != "DEFER"


@patch("services.timing_intelligence.fetch_history")
def test_regression_micron01_resolves_to_mu(mock_fetch):
    """MICRON01 → MU (alias mapping) → valid history → data_available=True."""
    mock_fetch.return_value = _make_price_history()
    from services.timing_intelligence import score_timing_batch
    results = score_timing_batch(["MICRON01"])
    assert len(results) == 1
    r = results[0]
    assert r.symbol == "MICRON01"
    assert r.data_available is True
    assert r.timing_score > 0


@patch("services.timing_intelligence.fetch_history")
def test_regression_glif_appends_bk(mock_fetch):
    """GLIF (Thai SET stock, no .BK) → GLIF.BK → valid history → data_available=True."""
    mock_fetch.return_value = _make_price_history()
    from services.timing_intelligence import score_timing_batch
    results = score_timing_batch(["GLIF"])
    assert len(results) == 1
    r = results[0]
    assert r.symbol == "GLIF"
    assert r.data_available is True
    assert r.timing_score > 0
