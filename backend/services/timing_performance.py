"""Phase 4C.6B — Period Performance Engine.

For each AllocationPeriod produced by timing_periods.py, computes four
deterministic performance metrics using existing PortfolioSnapshot and
BenchmarkPrice tables.  No AI calls.  No new tables.  No migrations.

Public API
----------
build_period_performances(portfolio_id, workspace_id, db, benchmark) -> list[PeriodPerformance]
evaluate_period_performance(period, snap_rows, bench_map)           -> PeriodPerformance
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

from pydantic import BaseModel
from sqlalchemy.orm import Session

from services.timing_periods import AllocationPeriod, build_allocation_periods


# ── Response model ────────────────────────────────────────────────────────────

class PeriodPerformance(BaseModel):
    recommendation_snapshot_id: int
    start_date: datetime
    end_date: Optional[datetime]
    days_active: int
    is_current: bool

    period_return_pct: Optional[float]       # portfolio TWR over the period
    benchmark_return_pct: Optional[float]    # benchmark price return over same window
    excess_return_pct: Optional[float]       # period_return_pct − benchmark_return_pct
    max_drawdown_pct: Optional[float]        # peak-to-trough decline in total_value

    snapshot_count: int                      # portfolio snapshots found in window


# ── Top-level builder (loads DB data then delegates to pure evaluator) ────────

def build_period_performances(
    portfolio_id: int,
    workspace_id: int,
    db: Session,
    benchmark: str = "^SET.BK",
) -> list[PeriodPerformance]:
    """Load all allocation periods + snapshots + benchmark prices, then evaluate."""
    from models.database import BenchmarkPrice, PortfolioSnapshot

    periods = build_allocation_periods(portfolio_id, workspace_id, db)
    if not periods:
        return []

    first_start = _date_str(periods[0].start_date)
    today_str = date.today().isoformat()

    snap_rows = (
        db.query(PortfolioSnapshot)
        .filter(
            PortfolioSnapshot.portfolio_id == portfolio_id,
            PortfolioSnapshot.workspace_id == workspace_id,
            PortfolioSnapshot.snapshot_date >= first_start,
            PortfolioSnapshot.snapshot_date <= today_str,
        )
        .order_by(PortfolioSnapshot.snapshot_date.asc())
        .all()
    )

    bench_rows = (
        db.query(BenchmarkPrice)
        .filter(
            BenchmarkPrice.symbol == benchmark,
            BenchmarkPrice.price_date >= first_start,
            BenchmarkPrice.price_date <= today_str,
        )
        .order_by(BenchmarkPrice.price_date.asc())
        .all()
    )

    # date-string → close_price
    bench_map: dict[str, float] = {r.price_date: r.close_price for r in bench_rows}

    return [evaluate_period_performance(p, snap_rows, bench_map) for p in periods]


# ── Pure evaluator (testable without DB) ─────────────────────────────────────

def evaluate_period_performance(
    period: AllocationPeriod,
    snap_rows: list,         # PortfolioSnapshot ORM rows (or duck-typed dicts)
    bench_map: dict[str, float],
) -> PeriodPerformance:
    """Compute the four timing metrics for a single AllocationPeriod.

    Args:
        period:    AllocationPeriod from build_allocation_periods()
        snap_rows: All PortfolioSnapshot rows for the portfolio, sorted by date.
                   Only rows that fall within [start, end) are used.
        bench_map: date-string → close_price for the chosen benchmark.

    Metrics:
        period_return_pct    TWR chain of investment_return_pct (or daily_return_pct)
        benchmark_return_pct (end_price - start_price) / start_price * 100
        excess_return_pct    period_return_pct - benchmark_return_pct
        max_drawdown_pct     largest peak-to-trough drawdown in total_value
    """
    start_str = _date_str(period.start_date)
    end_str = _date_str(period.end_date) if period.end_date is not None else date.today().isoformat()

    # Snapshots strictly within the period window
    window = [
        s for s in snap_rows
        if start_str <= _snap_date(s) <= end_str
    ]

    period_return = _twr(window)
    benchmark_return = _benchmark_return(bench_map, start_str, end_str)
    excess = _subtract(period_return, benchmark_return)
    drawdown = _max_drawdown(window)

    return PeriodPerformance(
        recommendation_snapshot_id=period.recommendation_snapshot_id,
        start_date=period.start_date,
        end_date=period.end_date,
        days_active=period.days_active,
        is_current=period.is_current,
        period_return_pct=period_return,
        benchmark_return_pct=benchmark_return,
        excess_return_pct=excess,
        max_drawdown_pct=drawdown,
        snapshot_count=len(window),
    )


# ── Metric helpers ────────────────────────────────────────────────────────────

def _twr(snaps: list) -> float | None:
    """Chain investment_return_pct (cash-flow-adjusted) across snapshots."""
    returns: list[float] = []
    for s in snaps:
        r = _attr(s, "investment_return_pct") or _attr(s, "daily_return_pct")
        if r is not None:
            returns.append(float(r))

    if not returns:
        return None

    product = 1.0
    for r in returns:
        product *= (1.0 + r / 100.0)
    return round((product - 1.0) * 100.0, 4)


def _benchmark_return(
    bench_map: dict[str, float],
    start_str: str,
    end_str: str,
) -> float | None:
    """Simple price return for benchmark over [start_str, end_str].

    Finds the earliest price on or after start_str and the latest price on or
    before end_str so that missing trading-day data doesn't return None
    unnecessarily.
    """
    dates_in_range = sorted(d for d in bench_map if start_str <= d <= end_str)
    if len(dates_in_range) < 2:
        return None

    start_price = bench_map[dates_in_range[0]]
    end_price = bench_map[dates_in_range[-1]]

    if not start_price:
        return None
    return round((end_price - start_price) / start_price * 100.0, 4)


def _max_drawdown(snaps: list) -> float | None:
    """Maximum peak-to-trough decline in total_value within a period."""
    values = [float(v) for s in snaps if (v := _attr(s, "total_value")) is not None and v > 0]
    if len(values) < 2:
        return None

    peak = values[0]
    max_dd = 0.0
    for v in values[1:]:
        if v > peak:
            peak = v
        else:
            dd = (peak - v) / peak * 100.0
            if dd > max_dd:
                max_dd = dd

    return round(max_dd, 4) if max_dd > 0 else None


def _subtract(a: float | None, b: float | None) -> float | None:
    if a is None or b is None:
        return None
    return round(a - b, 4)


# ── Date helpers ──────────────────────────────────────────────────────────────

def _date_str(dt: datetime) -> str:
    """Convert aware or naive UTC datetime → 'YYYY-MM-DD' string."""
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.strftime("%Y-%m-%d")


def _snap_date(snap) -> str:
    """Get snapshot_date from an ORM row or a plain dict."""
    v = snap.snapshot_date if hasattr(snap, "snapshot_date") else snap["snapshot_date"]
    return str(v)[:10]  # handle both "YYYY-MM-DD" strings and date objects


def _attr(obj, name: str):
    """Read an attribute from an ORM row or a plain dict."""
    if hasattr(obj, name):
        return getattr(obj, name)
    return obj.get(name)
