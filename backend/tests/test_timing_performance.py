"""Unit tests for Phase 4C.6B — Period Performance Engine.

All tests use plain dict rows (no DB) so they exercise the pure
evaluate_period_performance() function in isolation.

Coverage:
  1. Simple period return (TWR chain)
  2. Benchmark return over same window
  3. Excess return = period − benchmark
  4. Max drawdown within a period
  5. Period with no snapshots → all metrics None
  6. Current (open-ended) period still evaluated
  7. TWR falls back to daily_return_pct when investment_return_pct is absent
  8. benchmark_return_pct is None when fewer than 2 prices in window
  9. Max drawdown is None for monotonically rising NAV
 10. Excess return is None when benchmark is unavailable
"""

import sys
import os
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.timing_periods import AllocationPeriod
from services.timing_performance import PeriodPerformance, evaluate_period_performance


# ── Helpers ───────────────────────────────────────────────────────────────────

def _dt(days_ago: int = 0) -> datetime:
    return (datetime.utcnow() - timedelta(days=days_ago)).replace(
        microsecond=0, tzinfo=timezone.utc
    )


def _period(
    rs_id: int = 1,
    days_ago_start: int = 10,
    days_ago_end: int | None = 0,
    is_current: bool = False,
) -> AllocationPeriod:
    start = _dt(days_ago_start)
    end = _dt(days_ago_end) if days_ago_end is not None else None
    days = (days_ago_start - days_ago_end) if days_ago_end is not None else days_ago_start + 1
    return AllocationPeriod(
        recommendation_snapshot_id=rs_id,
        start_date=start,
        end_date=end,
        days_active=max(1, days),
        is_current=is_current,
    )


def _snap(date_str: str, total_value: float, inv_return: float | None = None, daily_return: float | None = None) -> dict:
    return {
        "snapshot_date": date_str,
        "total_value": total_value,
        "investment_return_pct": inv_return,
        "daily_return_pct": daily_return,
    }


def _date(days_ago: int) -> str:
    return (datetime.utcnow() - timedelta(days=days_ago)).strftime("%Y-%m-%d")


# ── Test 1: Simple period return (TWR chain) ──────────────────────────────────

def test_period_return_twr_chain():
    period = _period(rs_id=1, days_ago_start=5, days_ago_end=0)
    snaps = [
        _snap(_date(5), 100_000, inv_return=1.0),
        _snap(_date(4), 101_000, inv_return=1.0),
        _snap(_date(3), 102_010, inv_return=1.0),
    ]
    bench_map = {}

    result = evaluate_period_performance(period, snaps, bench_map)

    # TWR: (1.01)^3 - 1 = 3.0301%
    assert result.period_return_pct is not None
    assert abs(result.period_return_pct - 3.0301) < 0.01
    assert result.snapshot_count == 3


# ── Test 2: Benchmark return ──────────────────────────────────────────────────

def test_benchmark_return_calculation():
    period = _period(rs_id=2, days_ago_start=5, days_ago_end=0)
    snaps = [_snap(_date(5), 100_000, inv_return=0.0)]
    bench_map = {
        _date(5): 1_000.0,
        _date(4): 1_010.0,
        _date(3): 1_020.0,
        _date(2): 980.0,
        _date(1): 1_050.0,
        _date(0): 1_100.0,
    }

    result = evaluate_period_performance(period, snaps, bench_map)

    # (1100 - 1000) / 1000 * 100 = 10.0%
    assert result.benchmark_return_pct is not None
    assert abs(result.benchmark_return_pct - 10.0) < 0.01


# ── Test 3: Excess return ─────────────────────────────────────────────────────

def test_excess_return_is_period_minus_benchmark():
    period = _period(rs_id=3, days_ago_start=3, days_ago_end=0)
    snaps = [
        _snap(_date(3), 100_000, inv_return=2.0),
        _snap(_date(2), 102_000, inv_return=2.0),
    ]
    bench_map = {_date(3): 100.0, _date(0): 103.0}

    result = evaluate_period_performance(period, snaps, bench_map)

    expected_period = round((1.02 * 1.02 - 1) * 100, 4)     # ≈ 4.04%
    expected_bench = round((103 - 100) / 100 * 100, 4)       # 3.0%
    expected_excess = round(expected_period - expected_bench, 4)

    assert result.excess_return_pct is not None
    assert abs(result.excess_return_pct - expected_excess) < 0.01


# ── Test 4: Max drawdown ──────────────────────────────────────────────────────

def test_max_drawdown_peak_to_trough():
    period = _period(rs_id=4, days_ago_start=6, days_ago_end=0)
    snaps = [
        _snap(_date(6), 100_000),
        _snap(_date(5), 110_000),   # peak
        _snap(_date(4), 99_000),    # trough: (110k-99k)/110k = 10%
        _snap(_date(3), 105_000),
        _snap(_date(2), 115_000),   # new peak
        _snap(_date(1), 108_000),   # (115k-108k)/115k = 6.08%
    ]

    result = evaluate_period_performance(period, snaps, {})

    assert result.max_drawdown_pct is not None
    assert abs(result.max_drawdown_pct - 10.0) < 0.1


# ── Test 5: No snapshots in period ───────────────────────────────────────────

def test_no_snapshots_returns_none_metrics():
    period = _period(rs_id=5, days_ago_start=5, days_ago_end=3)

    result = evaluate_period_performance(period, [], {})

    assert result.period_return_pct is None
    assert result.benchmark_return_pct is None
    assert result.excess_return_pct is None
    assert result.max_drawdown_pct is None
    assert result.snapshot_count == 0


# ── Test 6: Open-ended current period still evaluated ────────────────────────

def test_current_period_is_evaluated():
    period = _period(rs_id=6, days_ago_start=3, days_ago_end=None, is_current=True)
    snaps = [
        _snap(_date(3), 100_000, inv_return=1.0),
        _snap(_date(2), 101_000, inv_return=1.0),
        _snap(_date(1), 102_010, inv_return=1.0),
    ]

    result = evaluate_period_performance(period, snaps, {})

    assert result.is_current is True
    assert result.end_date is None
    assert result.period_return_pct is not None
    assert result.snapshot_count == 3


# ── Test 7: Falls back to daily_return_pct ───────────────────────────────────

def test_twr_fallback_to_daily_return_pct():
    period = _period(rs_id=7, days_ago_start=2, days_ago_end=0)
    snaps = [
        # investment_return_pct absent; daily_return_pct present
        _snap(_date(2), 100_000, inv_return=None, daily_return=2.0),
        _snap(_date(1), 102_000, inv_return=None, daily_return=2.0),
    ]

    result = evaluate_period_performance(period, snaps, {})

    assert result.period_return_pct is not None
    assert abs(result.period_return_pct - round((1.02 * 1.02 - 1) * 100, 4)) < 0.001


# ── Test 8: Benchmark None when fewer than 2 prices in window ─────────────────

def test_benchmark_none_when_insufficient_prices():
    period = _period(rs_id=8, days_ago_start=5, days_ago_end=0)
    snaps = [_snap(_date(3), 100_000, inv_return=1.0)]
    bench_map = {_date(3): 1_000.0}  # only one price point

    result = evaluate_period_performance(period, snaps, bench_map)

    assert result.benchmark_return_pct is None


# ── Test 9: No drawdown for monotonically rising NAV ─────────────────────────

def test_no_drawdown_when_nav_always_rises():
    period = _period(rs_id=9, days_ago_start=4, days_ago_end=0)
    snaps = [
        _snap(_date(4), 100_000),
        _snap(_date(3), 101_000),
        _snap(_date(2), 102_000),
        _snap(_date(1), 103_000),
    ]

    result = evaluate_period_performance(period, snaps, {})

    assert result.max_drawdown_pct is None


# ── Test 10: Excess return is None when benchmark unavailable ─────────────────

def test_excess_return_none_when_no_benchmark():
    period = _period(rs_id=10, days_ago_start=3, days_ago_end=0)
    snaps = [_snap(_date(3), 100_000, inv_return=2.0)]

    result = evaluate_period_performance(period, snaps, {})

    assert result.period_return_pct is not None
    assert result.benchmark_return_pct is None
    assert result.excess_return_pct is None
