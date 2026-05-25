"""regime_attribution.py — Phase 3B.7B

Observational analysis of portfolio performance grouped by market regime.

Joins PortfolioSnapshot daily returns with RegimeSnapshot regime labels to
measure which market conditions the optimizer performs best/worst in.
All arithmetic is deterministic — no yfinance calls.

Public API:
    compute_regime_attribution(db, portfolio_id, lookback_days=90) → dict
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Human-readable regime labels for display
_REGIME_LABELS: dict[str, str] = {
    "RISK_ON":              "Risk-On Bull",
    "RISK_OFF":             "Risk-Off Bear",
    "SIDEWAYS":             "Sideways / Neutral",
    "HIGH_VOLATILITY":      "High Volatility",
    "DEFENSIVE_REGIME":     "Defensive",
    "TRANSITION_RISK_ON":   "Transitioning → Risk-On",
    "TRANSITION_RISK_OFF":  "Transitioning → Risk-Off",
}

_REGIME_COLORS: dict[str, str] = {
    "RISK_ON":              "green",
    "RISK_OFF":             "red",
    "SIDEWAYS":             "gray",
    "HIGH_VOLATILITY":      "orange",
    "DEFENSIVE_REGIME":     "blue",
    "TRANSITION_RISK_ON":   "teal",
    "TRANSITION_RISK_OFF":  "amber",
}


def compute_regime_attribution(
    db: Session,
    portfolio_id: int,
    lookback_days: int = 90,
) -> dict[str, Any]:
    """Group portfolio daily returns by market regime.

    For each RegimeSnapshot date that overlaps with a PortfolioSnapshot,
    records the daily return. Then aggregates per-regime statistics:
      - avg_daily_return_pct
      - total_return_pct (compounded)
      - trading_days
      - volatility
      - min / max daily return

    Returns:
        regimes          : per-regime breakdown dict
        best_regime      : regime with highest avg_daily_return
        worst_regime     : regime with lowest avg_daily_return
        total_days       : total portfolio snapshot days in window
        coverage_pct     : % of days with a matching regime snapshot
    """
    from models.database import PortfolioSnapshot, RegimeSnapshot

    cutoff = (date.today() - timedelta(days=lookback_days)).isoformat()

    portfolio_snaps = (
        db.query(PortfolioSnapshot)
        .filter(
            PortfolioSnapshot.portfolio_id == portfolio_id,
            PortfolioSnapshot.snapshot_date >= cutoff,
        )
        .order_by(PortfolioSnapshot.snapshot_date)
        .all()
    )

    if not portfolio_snaps:
        return {
            "portfolio_id": portfolio_id,
            "lookback_days": lookback_days,
            "regimes": {},
            "best_regime": None,
            "worst_regime": None,
            "total_days": 0,
            "coverage_pct": 0.0,
            "status": "no_snapshot_data",
        }

    # Build regime lookup: date_str → regime
    regime_dates = {s.snapshot_date for s in portfolio_snaps}
    regime_rows = (
        db.query(RegimeSnapshot)
        .filter(RegimeSnapshot.snapshot_date.in_(regime_dates))
        .all()
    )
    regime_map: dict[str, str] = {r.snapshot_date: r.regime for r in regime_rows}
    regime_confidence: dict[str, float] = {r.snapshot_date: r.confidence for r in regime_rows}

    # Group daily returns by regime
    buckets: dict[str, list[float]] = {}
    matched = 0

    for snap in portfolio_snaps:
        if snap.daily_return_pct is None:
            continue
        regime = regime_map.get(snap.snapshot_date)
        if regime is None:
            continue
        matched += 1
        if regime not in buckets:
            buckets[regime] = []
        buckets[regime].append(snap.daily_return_pct)

    total_days = len([s for s in portfolio_snaps if s.daily_return_pct is not None])
    coverage_pct = round(matched / total_days * 100, 1) if total_days > 0 else 0.0

    # Build per-regime statistics
    regime_stats: dict[str, dict[str, Any]] = {}
    for regime, returns in buckets.items():
        n = len(returns)
        avg = sum(returns) / n
        # Compound total return from daily returns
        compound = 1.0
        for r in returns:
            compound *= (1 + r / 100)
        total_ret = round((compound - 1) * 100, 4)

        # Variance / std dev
        if n > 1:
            mean = avg
            variance = sum((r - mean) ** 2 for r in returns) / (n - 1)
            vol = round((variance ** 0.5) * (252 ** 0.5), 4)
        else:
            vol = None

        regime_stats[regime] = {
            "regime": regime,
            "label": _REGIME_LABELS.get(regime, regime),
            "color": _REGIME_COLORS.get(regime, "gray"),
            "trading_days": n,
            "avg_daily_return_pct": round(avg, 4),
            "total_return_pct": total_ret,
            "annualized_volatility": vol,
            "min_daily_return_pct": round(min(returns), 4),
            "max_daily_return_pct": round(max(returns), 4),
        }

    # Best / worst by avg daily return
    best_regime: str | None = None
    worst_regime: str | None = None
    if regime_stats:
        best_regime = max(regime_stats, key=lambda r: regime_stats[r]["avg_daily_return_pct"])
        worst_regime = min(regime_stats, key=lambda r: regime_stats[r]["avg_daily_return_pct"])

    # Optimizer run performance per regime (from OptimizerHistory)
    optimizer_by_regime = _optimizer_performance_by_regime(db, portfolio_id, cutoff, regime_map)

    return {
        "portfolio_id": portfolio_id,
        "lookback_days": lookback_days,
        "period_start": cutoff,
        "period_end": date.today().isoformat(),
        "regimes": regime_stats,
        "best_regime": best_regime,
        "worst_regime": worst_regime,
        "total_days": total_days,
        "matched_days": matched,
        "coverage_pct": coverage_pct,
        "optimizer_by_regime": optimizer_by_regime,
        "status": "ok" if regime_stats else "no_regime_overlap",
    }


def _optimizer_performance_by_regime(
    db: Session,
    portfolio_id: int,
    cutoff: str,
    regime_map: dict[str, str],
) -> dict[str, Any]:
    """Count optimizer runs and avg rebalance_opportunity_score per regime."""
    from models.database import OptimizerHistory

    runs = (
        db.query(OptimizerHistory)
        .filter(
            OptimizerHistory.portfolio_id == portfolio_id,
            OptimizerHistory.analyzed_at >= cutoff,
        )
        .all()
    )

    by_regime: dict[str, dict[str, Any]] = {}
    for run in runs:
        run_date = run.analyzed_at.strftime("%Y-%m-%d") if run.analyzed_at else None
        if not run_date:
            continue
        regime = regime_map.get(run_date)
        if not regime:
            # Try nearest available date in regime_map
            continue
        if regime not in by_regime:
            by_regime[regime] = {"runs": 0, "rebalance_count": 0, "scores": [], "label": _REGIME_LABELS.get(regime, regime)}
        by_regime[regime]["runs"] += 1
        if run.optimizer_status == "REBALANCE":
            by_regime[regime]["rebalance_count"] += 1
        if run.rebalance_opportunity_score is not None:
            by_regime[regime]["scores"].append(run.rebalance_opportunity_score)

    # Finalize averages
    for regime, data in by_regime.items():
        scores = data.pop("scores", [])
        data["avg_opportunity_score"] = round(sum(scores) / len(scores), 1) if scores else None
        data["rebalance_rate_pct"] = (
            round(data["rebalance_count"] / data["runs"] * 100, 1) if data["runs"] > 0 else None
        )

    return by_regime
