"""Unit tests for Phase 4C.6D — Regime Attribution Engine.

All tests use aggregate_by_regime() (pure function) or build_summary()
so no DB is required.

Coverage:
  1.  Empty periods → empty list
  2.  Single regime — all periods assigned to same regime
  3.  Multiple regimes — periods split across regimes
  4.  Correct averaging — average_score = sum / count
  5.  Best score detection within a regime group
  6.  Worst score detection within a regime group
  7.  Duration averaging — average_duration_days
  8.  Regime lookup finds latest snapshot ≤ start date (not strictly equal)
  9.  Unknown regime when no regime data precedes period start
 10.  Missing excess return — average_excess_return_pct is None when all None
 11.  Missing drawdown — average_drawdown_pct is None when all None
 12.  Summary generation — best/worst regime by average_score
"""

import sys
import os
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.timing_performance import PeriodPerformance
from services.timing_score import TimingScore, calculate_timing_score
from services.regime_attribution import (
    RegimeTimingResult,
    aggregate_by_regime,
    build_summary,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _dt(days_ago: int = 0) -> datetime:
    return (datetime.utcnow() - timedelta(days=days_ago)).replace(
        microsecond=0, tzinfo=timezone.utc
    )


def _perf(
    rs_id: int,
    days_active: int = 20,
    snapshot_count: int = 10,
    excess_return_pct: float | None = 2.0,
    max_drawdown_pct: float | None = 4.0,
    period_return_pct: float | None = 3.0,
    benchmark_return_pct: float | None = 1.0,
    start_days_ago: int = 30,
    is_current: bool = False,
) -> PeriodPerformance:
    start = _dt(start_days_ago)
    end = _dt(0) if not is_current else None
    return PeriodPerformance(
        recommendation_snapshot_id=rs_id,
        start_date=start,
        end_date=end,
        days_active=days_active,
        is_current=is_current,
        period_return_pct=period_return_pct,
        benchmark_return_pct=benchmark_return_pct,
        excess_return_pct=excess_return_pct,
        max_drawdown_pct=max_drawdown_pct,
        snapshot_count=snapshot_count,
    )


def _score(perf: PeriodPerformance) -> TimingScore:
    return calculate_timing_score(perf)


def _regime_map(entries: list[tuple[int, str]]) -> dict[str, str]:
    """Build a date→regime map from (days_ago, regime) pairs."""
    return {
        (datetime.utcnow() - timedelta(days=d)).strftime("%Y-%m-%d"): r
        for d, r in entries
    }


# ── Test 1: Empty periods ──────────────────────────────────────────────────────

def test_empty_periods_returns_empty_list():
    result = aggregate_by_regime([], [], {})
    assert result == []


# ── Test 2: Single regime ─────────────────────────────────────────────────────

def test_single_regime_groups_all_periods():
    p1 = _perf(rs_id=1, start_days_ago=50)
    p2 = _perf(rs_id=2, start_days_ago=30)
    perfs = [p1, p2]
    scores = [_score(p) for p in perfs]

    # Both periods start after the single regime entry at 60 days ago
    regime_map = _regime_map([(60, "RISK_ON")])

    results = aggregate_by_regime(perfs, scores, regime_map)

    assert len(results) == 1
    assert results[0].regime == "RISK_ON"
    assert results[0].periods == 2


# ── Test 3: Multiple regimes ──────────────────────────────────────────────────

def test_multiple_regimes_split_periods_correctly():
    p_on = _perf(rs_id=1, start_days_ago=40)   # starts 40d ago → RISK_ON (set 50d ago)
    p_off = _perf(rs_id=2, start_days_ago=10)  # starts 10d ago → RISK_OFF (set 20d ago)
    perfs = [p_on, p_off]
    scores = [_score(p) for p in perfs]

    regime_map = _regime_map([
        (50, "RISK_ON"),
        (20, "RISK_OFF"),
    ])

    results = aggregate_by_regime(perfs, scores, regime_map)
    regimes = {r.regime for r in results}

    assert "RISK_ON" in regimes
    assert "RISK_OFF" in regimes
    for r in results:
        assert r.periods == 1


# ── Test 4: Correct averaging ─────────────────────────────────────────────────

def test_average_score_is_computed_correctly():
    # Two periods in same regime; scores must match calculate_timing_score output
    p1 = _perf(rs_id=1, start_days_ago=50, excess_return_pct=0.0, max_drawdown_pct=5.0, days_active=14, snapshot_count=5)
    p2 = _perf(rs_id=2, start_days_ago=30, excess_return_pct=4.0, max_drawdown_pct=5.0, days_active=14, snapshot_count=5)
    perfs = [p1, p2]
    scores = [_score(p) for p in perfs]
    regime_map = _regime_map([(60, "RISK_ON")])

    results = aggregate_by_regime(perfs, scores, regime_map)

    expected_avg = round((scores[0].timing_score + scores[1].timing_score) / 2, 1)
    assert results[0].average_score == expected_avg


# ── Test 5: Best score detection ──────────────────────────────────────────────

def test_best_score_is_maximum_within_regime():
    p1 = _perf(rs_id=1, start_days_ago=50, excess_return_pct=7.0, max_drawdown_pct=None, days_active=30, snapshot_count=5)
    p2 = _perf(rs_id=2, start_days_ago=30, excess_return_pct=0.0, max_drawdown_pct=10.0, days_active=7, snapshot_count=5)
    perfs = [p1, p2]
    scores = [_score(p) for p in perfs]
    regime_map = _regime_map([(60, "RISK_ON")])

    results = aggregate_by_regime(perfs, scores, regime_map)

    assert results[0].best_score == max(s.timing_score for s in scores)


# ── Test 6: Worst score detection ─────────────────────────────────────────────

def test_worst_score_is_minimum_within_regime():
    p1 = _perf(rs_id=1, start_days_ago=50, excess_return_pct=7.0, max_drawdown_pct=None, days_active=30, snapshot_count=5)
    p2 = _perf(rs_id=2, start_days_ago=30, excess_return_pct=0.0, max_drawdown_pct=10.0, days_active=7, snapshot_count=5)
    perfs = [p1, p2]
    scores = [_score(p) for p in perfs]
    regime_map = _regime_map([(60, "RISK_ON")])

    results = aggregate_by_regime(perfs, scores, regime_map)

    assert results[0].worst_score == min(s.timing_score for s in scores)


# ── Test 7: Duration averaging ────────────────────────────────────────────────

def test_average_duration_days_is_mean_of_days_active():
    p1 = _perf(rs_id=1, start_days_ago=50, days_active=10)
    p2 = _perf(rs_id=2, start_days_ago=30, days_active=20)
    p3 = _perf(rs_id=3, start_days_ago=10, days_active=30)
    perfs = [p1, p2, p3]
    scores = [_score(p) for p in perfs]
    regime_map = _regime_map([(60, "RISK_ON")])

    results = aggregate_by_regime(perfs, scores, regime_map)

    assert results[0].average_duration_days == 20.0


# ── Test 8: Regime lookup finds latest snapshot ≤ start date ─────────────────

def test_regime_lookup_uses_most_recent_snapshot_before_start():
    # Two regime transitions; period starts between them
    # 60d ago: RISK_ON; 25d ago: RISK_OFF; period starts 30d ago (→ RISK_ON)
    # period starts 15d ago (→ RISK_OFF)
    p_on = _perf(rs_id=1, start_days_ago=30)
    p_off = _perf(rs_id=2, start_days_ago=15)
    perfs = [p_on, p_off]
    scores = [_score(p) for p in perfs]

    regime_map = _regime_map([(60, "RISK_ON"), (25, "RISK_OFF")])

    results = aggregate_by_regime(perfs, scores, regime_map)
    regime_for = {r.regime: r.periods for r in results}

    assert regime_for.get("RISK_ON") == 1   # p_on starts before RISK_OFF transition
    assert regime_for.get("RISK_OFF") == 1  # p_off starts after transition


# ── Test 9: Unknown regime when no data precedes period ──────────────────────

def test_unknown_regime_when_no_snapshot_before_start():
    p = _perf(rs_id=1, start_days_ago=10)
    perfs = [p]
    scores = [_score(p)]

    # Regime entry is AFTER the period start
    regime_map = _regime_map([(5, "RISK_ON")])

    results = aggregate_by_regime(perfs, scores, regime_map)

    assert results[0].regime == "UNKNOWN"


# ── Test 10: Missing excess return ────────────────────────────────────────────

def test_average_excess_return_none_when_all_missing():
    p1 = _perf(rs_id=1, start_days_ago=50, excess_return_pct=None, benchmark_return_pct=None)
    p2 = _perf(rs_id=2, start_days_ago=30, excess_return_pct=None, benchmark_return_pct=None)
    perfs = [p1, p2]
    scores = [_score(p) for p in perfs]
    regime_map = _regime_map([(60, "RISK_ON")])

    results = aggregate_by_regime(perfs, scores, regime_map)

    assert results[0].average_excess_return_pct is None


# ── Test 11: Missing drawdown ─────────────────────────────────────────────────

def test_average_drawdown_none_when_all_missing():
    p1 = _perf(rs_id=1, start_days_ago=50, max_drawdown_pct=None)
    p2 = _perf(rs_id=2, start_days_ago=30, max_drawdown_pct=None)
    perfs = [p1, p2]
    scores = [_score(p) for p in perfs]
    regime_map = _regime_map([(60, "RISK_ON")])

    results = aggregate_by_regime(perfs, scores, regime_map)

    assert results[0].average_drawdown_pct is None


# ── Test 12: Summary generation ───────────────────────────────────────────────

def test_build_summary_identifies_best_and_worst_regime():
    results = [
        RegimeTimingResult(
            regime="RISK_ON", periods=3, average_score=78.0, best_score=90,
            worst_score=60, average_excess_return_pct=3.0,
            average_drawdown_pct=-2.0, average_duration_days=15.0,
        ),
        RegimeTimingResult(
            regime="RISK_OFF", periods=2, average_score=41.0, best_score=55,
            worst_score=30, average_excess_return_pct=-2.0,
            average_drawdown_pct=-7.0, average_duration_days=10.0,
        ),
        RegimeTimingResult(
            regime="TRANSITION_RISK_ON", periods=1, average_score=62.0, best_score=62,
            worst_score=62, average_excess_return_pct=1.0,
            average_drawdown_pct=None, average_duration_days=8.0,
        ),
    ]

    summary = build_summary(results)

    assert summary["best_regime"] == "RISK_ON"
    assert summary["best_regime_score"] == 78.0
    assert summary["worst_regime"] == "RISK_OFF"
    assert summary["worst_regime_score"] == 41.0


def test_build_summary_empty_returns_none_values():
    summary = build_summary([])
    assert summary["best_regime"] is None
    assert summary["worst_regime"] is None
