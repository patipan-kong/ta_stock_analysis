"""Phase 4C.6D — Regime Attribution Engine.

Attributes timing quality (from 4C.6C TimingScore) to market regimes
stored in RegimeSnapshot.  Answers: which environment produces the best
AI timing outcomes?

No AI calls.  No DB writes.  No new tables.  Attribution analytics only.

Public API
----------
build_regime_attribution(portfolio_id, workspace_id, db, benchmark)
    -> list[RegimeTimingResult]

aggregate_by_regime(performances, scores, regime_map)
    -> list[RegimeTimingResult]       # pure, testable without DB

build_summary(results)
    -> dict                           # best/worst regime summary
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel
from sqlalchemy.orm import Session

from services.timing_performance import PeriodPerformance
from services.timing_score import TimingScore


# ── Response model ────────────────────────────────────────────────────────────

class RegimeTimingResult(BaseModel):
    regime: str
    periods: int
    average_score: float
    best_score: int
    worst_score: int
    average_excess_return_pct: Optional[float]
    average_drawdown_pct: Optional[float]
    average_duration_days: float


# ── Top-level builder (loads DB data then delegates to pure aggregator) ───────

def build_regime_attribution(
    portfolio_id: int,
    workspace_id: int,
    db: Session,
    benchmark: str = "^SET.BK",
) -> list[RegimeTimingResult]:
    """Load periods + scores + regime history, then aggregate."""
    from models.database import RegimeSnapshot
    from services.timing_performance import build_period_performances
    from services.timing_score import calculate_timing_score

    performances = build_period_performances(portfolio_id, workspace_id, db, benchmark)
    if not performances:
        return []

    scored = [calculate_timing_score(p) for p in performances]

    regime_rows = (
        db.query(RegimeSnapshot)
        .order_by(RegimeSnapshot.snapshot_date.asc())
        .all()
    )
    regime_map: dict[str, str] = {r.snapshot_date: r.regime for r in regime_rows}

    return aggregate_by_regime(performances, scored, regime_map)


# ── Pure aggregator (testable without DB) ─────────────────────────────────────

def aggregate_by_regime(
    performances: list[PeriodPerformance],
    scores: list[TimingScore],
    regime_map: dict[str, str],
) -> list[RegimeTimingResult]:
    """Group periods by their start-date regime and compute per-regime statistics."""
    grouped: dict[str, list[tuple[PeriodPerformance, TimingScore]]] = {}

    for perf, score in zip(performances, scores):
        regime = _lookup_regime(perf.start_date, regime_map)
        if regime not in grouped:
            grouped[regime] = []
        grouped[regime].append((perf, score))

    results: list[RegimeTimingResult] = []
    for regime in sorted(grouped):
        pairs = grouped[regime]
        ts = [s.timing_score for _, s in pairs]
        excess = [p.excess_return_pct for p, _ in pairs if p.excess_return_pct is not None]
        drawdown = [p.max_drawdown_pct for p, _ in pairs if p.max_drawdown_pct is not None]
        durations = [p.days_active for p, _ in pairs]

        results.append(RegimeTimingResult(
            regime=regime,
            periods=len(pairs),
            average_score=round(sum(ts) / len(ts), 1),
            best_score=max(ts),
            worst_score=min(ts),
            average_excess_return_pct=(
                round(sum(excess) / len(excess), 4) if excess else None
            ),
            average_drawdown_pct=(
                round(sum(drawdown) / len(drawdown), 4) if drawdown else None
            ),
            average_duration_days=round(sum(durations) / len(durations), 1),
        ))

    return results


def build_summary(results: list[RegimeTimingResult]) -> dict:
    """Return best/worst regime by average_score for inclusion in API response."""
    if not results:
        return {
            "best_regime": None,
            "best_regime_score": None,
            "worst_regime": None,
            "worst_regime_score": None,
        }
    best = max(results, key=lambda r: r.average_score)
    worst = min(results, key=lambda r: r.average_score)
    return {
        "best_regime": best.regime,
        "best_regime_score": best.average_score,
        "worst_regime": worst.regime,
        "worst_regime_score": worst.average_score,
    }


# ── Regime lookup ─────────────────────────────────────────────────────────────

def _lookup_regime(start_date: datetime, regime_map: dict[str, str]) -> str:
    """Find the most recent regime snapshot on or before the period start date.

    Falls back to "UNKNOWN" when no historical regime data precedes the period.
    """
    target = _date_str(start_date)
    candidates = [d for d in regime_map if d <= target]
    if not candidates:
        return "UNKNOWN"
    return regime_map[max(candidates)]


def _date_str(dt: datetime) -> str:
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.strftime("%Y-%m-%d")
