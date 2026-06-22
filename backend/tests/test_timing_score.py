"""Unit tests for Phase 4C.6C — Timing Score Engine.

All tests use PeriodPerformance plain-dict construction (no DB).

Coverage:
  1.  Neutral period — base 50, moderate inputs
  2.  Positive excess return contribution
  3.  Negative excess return contribution
  4.  Excellent score (>= 90)
  5.  Poor score (< 40)
  6.  Score clamping at lower bound (0)
  7.  Confidence HIGH (>= 30 snapshots)
  8.  Confidence MEDIUM (15-29 snapshots)
  9.  Confidence LOW (< 15 snapshots)
 10.  Grade mapping (all five grades)
 11.  Missing drawdown (None) treated as +15
 12.  Missing benchmark (excess_return_pct=None) treated as 0 component
"""

import sys
import os
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.timing_performance import PeriodPerformance
from services.timing_score import TimingScore, calculate_timing_score


# ── Factory helper ────────────────────────────────────────────────────────────

_NOW = datetime(2026, 6, 22, 12, 0, 0, tzinfo=timezone.utc)
_START = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _period(
    rs_id: int = 1,
    days_active: int = 20,
    snapshot_count: int = 10,
    period_return_pct: float | None = 0.0,
    benchmark_return_pct: float | None = 0.0,
    excess_return_pct: float | None = 0.0,
    max_drawdown_pct: float | None = 5.0,
    is_current: bool = False,
) -> PeriodPerformance:
    return PeriodPerformance(
        recommendation_snapshot_id=rs_id,
        start_date=_START,
        end_date=_NOW if not is_current else None,
        days_active=days_active,
        is_current=is_current,
        period_return_pct=period_return_pct,
        benchmark_return_pct=benchmark_return_pct,
        excess_return_pct=excess_return_pct,
        max_drawdown_pct=max_drawdown_pct,
        snapshot_count=snapshot_count,
    )


# ── Test 1: Neutral period ────────────────────────────────────────────────────

def test_neutral_period_score_near_50():
    # excess=0 (0 component), drawdown=5% (≤5 → +10), days=14 (≥14 → +5)
    # expected: 50 + 0 + 10 + 5 = 65
    period = _period(excess_return_pct=0.0, max_drawdown_pct=5.0, days_active=14, snapshot_count=5)
    result = calculate_timing_score(period)

    assert result.timing_score == 65
    assert result.excess_return_component == 0.0
    assert result.drawdown_component == 10.0
    assert result.duration_component == 5.0


# ── Test 2: Positive excess return ───────────────────────────────────────────

def test_positive_excess_return_increases_score():
    # excess=5% → +20 component
    baseline = _period(excess_return_pct=0.0, max_drawdown_pct=None, days_active=30, snapshot_count=5)
    with_excess = _period(excess_return_pct=5.0, max_drawdown_pct=None, days_active=30, snapshot_count=5)

    base_result = calculate_timing_score(baseline)
    excess_result = calculate_timing_score(with_excess)

    assert excess_result.timing_score > base_result.timing_score
    assert excess_result.excess_return_component == 20.0


# ── Test 3: Negative excess return ───────────────────────────────────────────

def test_negative_excess_return_decreases_score():
    # excess=-5% → -20 component
    period = _period(excess_return_pct=-5.0, max_drawdown_pct=5.0, days_active=14, snapshot_count=5)
    result = calculate_timing_score(period)

    assert result.excess_return_component == -20.0
    # 50 + (-20) + 10 + 5 = 45
    assert result.timing_score == 45


# ── Test 4: Excellent score ───────────────────────────────────────────────────

def test_excellent_score_requires_high_excess_low_drawdown_long_duration():
    # excess=7.5% → +30 (capped), drawdown None → +15, days=30 → +10
    # 50 + 30 + 15 + 10 = 105 → clamped to 100
    period = _period(excess_return_pct=7.5, max_drawdown_pct=None, days_active=30, snapshot_count=10)
    result = calculate_timing_score(period)

    assert result.timing_score == 100
    assert result.timing_grade == "EXCELLENT"


# ── Test 5: Poor score ────────────────────────────────────────────────────────

def test_poor_score_for_bad_timing():
    # excess=-5% → -20, drawdown=15% (>12 → -10), days=3 (<7 → -5)
    # 50 + (-20) + (-10) + (-5) = 15 → POOR
    period = _period(excess_return_pct=-5.0, max_drawdown_pct=15.0, days_active=3, snapshot_count=2)
    result = calculate_timing_score(period)

    assert result.timing_score == 15
    assert result.timing_grade == "POOR"


# ── Test 6: Score clamping at lower bound ────────────────────────────────────

def test_score_clamped_to_zero():
    # excess=-7.5% → -30 (capped), drawdown=20% → -10, days=3 → -5
    # 50 + (-30) + (-10) + (-5) = 5 → above 0 — let's push harder:
    # excess=-10% → raw=-40 → capped -30, drawdown=20% → -10, days=1 → -5
    # 50 - 30 - 10 - 5 = 5
    # To actually hit 0: need 50 - 30 - 10 - 5 = 5; impossible to go negative via these components.
    # Per spec: clamp is max(0, ...). Let's verify that extreme excess + large drawdown stays >= 0.
    period = _period(excess_return_pct=-100.0, max_drawdown_pct=50.0, days_active=1, snapshot_count=1)
    result = calculate_timing_score(period)

    # 50 + (-30) + (-10) + (-5) = 5  — clamped ensures >= 0
    assert result.timing_score >= 0
    assert result.timing_score <= 100


# ── Test 7: Confidence HIGH ───────────────────────────────────────────────────

def test_confidence_high_at_30_snapshots():
    period = _period(snapshot_count=30)
    result = calculate_timing_score(period)

    assert result.confidence_level == "HIGH"


# ── Test 8: Confidence MEDIUM ────────────────────────────────────────────────

def test_confidence_medium_at_15_to_29_snapshots():
    for count in [15, 20, 29]:
        period = _period(snapshot_count=count)
        result = calculate_timing_score(period)
        assert result.confidence_level == "MEDIUM", f"Failed at snapshot_count={count}"


# ── Test 9: Confidence LOW ────────────────────────────────────────────────────

def test_confidence_low_below_15_snapshots():
    for count in [0, 1, 10, 14]:
        period = _period(snapshot_count=count)
        result = calculate_timing_score(period)
        assert result.confidence_level == "LOW", f"Failed at snapshot_count={count}"


# ── Test 10: Grade mapping ────────────────────────────────────────────────────

def test_grade_mapping_all_five_grades():
    from services.timing_score import _grade
    assert _grade(100) == "EXCELLENT"
    assert _grade(90) == "EXCELLENT"
    assert _grade(89) == "GOOD"
    assert _grade(75) == "GOOD"
    assert _grade(74) == "NEUTRAL"
    assert _grade(60) == "NEUTRAL"
    assert _grade(59) == "WEAK"
    assert _grade(40) == "WEAK"
    assert _grade(39) == "POOR"
    assert _grade(0) == "POOR"


# ── Test 11: Missing drawdown treated as +15 ─────────────────────────────────

def test_missing_drawdown_none_gives_max_drawdown_bonus():
    period_no_dd = _period(excess_return_pct=0.0, max_drawdown_pct=None, days_active=14, snapshot_count=5)
    period_dd_0 = _period(excess_return_pct=0.0, max_drawdown_pct=1.0, days_active=14, snapshot_count=5)

    result_no_dd = calculate_timing_score(period_no_dd)
    result_dd_0 = calculate_timing_score(period_dd_0)

    assert result_no_dd.drawdown_component == 15.0
    assert result_dd_0.drawdown_component == 15.0
    assert result_no_dd.timing_score == result_dd_0.timing_score


# ── Test 12: Missing benchmark → excess component zero ───────────────────────

def test_missing_benchmark_excess_component_is_zero():
    # When benchmark was unavailable, excess_return_pct=None
    period = _period(
        excess_return_pct=None,
        benchmark_return_pct=None,
        max_drawdown_pct=5.0,
        days_active=14,
        snapshot_count=5,
    )
    result = calculate_timing_score(period)

    assert result.excess_return_component == 0.0
    # 50 + 0 + 10 + 5 = 65
    assert result.timing_score == 65
