"""human_vs_ai.py — Phase 3B.7B

Observational comparison of human execution decisions vs AI model portfolios.

Measures, per execution decision and in aggregate:
  - return_delta          : shadow_return − actual_portfolio_return since decision
  - ai_better             : shadow outperformed actual → bool
  - hit_rate              : % of decisions where AI was better
  - cumulative_return_delta: aggregate outperformance across all decisions
  - volatility_delta      : shadow_vol − actual_vol (negative = AI less volatile)
  - drawdown_delta        : shadow_max_dd − actual_max_dd

No yfinance calls. All data from PortfolioSnapshot + ShadowPortfolioSnapshot.

Public API:
    compare_human_vs_ai(db, portfolio_id, evaluation_days=90) → dict
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from sqlalchemy.orm import Session

from services.analytics.attribution_engine import (
    compute_max_drawdown,
    _compute_return_pct,
    _compute_twr,
    _compute_daily_volatility,
    _safe_return,
)

logger = logging.getLogger(__name__)


def _portfolio_return_since(
    db: Session,
    portfolio_id: int,
    since_date: str,
) -> tuple[float | None, float, float | None]:
    """Return (return_pct, max_drawdown_pct, annualized_vol) for actual portfolio since since_date.

    Uses investment_return_pct (cash-flow-adjusted) for TWR when available,
    falling back to raw daily_return_pct for historical rows.
    """
    from models.database import PortfolioSnapshot

    snaps = (
        db.query(PortfolioSnapshot)
        .filter(
            PortfolioSnapshot.portfolio_id == portfolio_id,
            PortfolioSnapshot.snapshot_date >= since_date,
        )
        .order_by(PortfolioSnapshot.snapshot_date)
        .all()
    )
    # Filter out zero/negative NAV rows (price outage / corruption guard)
    valid_snaps = [s for s in snaps if s.total_value and s.total_value > 0]
    values = [s.total_value for s in valid_snaps]
    adjusted = [s.investment_return_pct for s in valid_snaps if s.investment_return_pct is not None]
    raw_daily = [s.daily_return_pct for s in valid_snaps if s.daily_return_pct is not None]

    total_return = _safe_return(_compute_twr(adjusted) if adjusted else _compute_return_pct(values))
    volatility = _compute_daily_volatility(adjusted if adjusted else raw_daily)
    return total_return, compute_max_drawdown(values), volatility


def _shadow_return_since(
    db: Session,
    shadow_id: int,
    since_date: str,
) -> tuple[float | None, float, float | None]:
    """Return (return_pct, max_drawdown_pct, annualized_vol) for a shadow since since_date.

    Shadow portfolios have no external cash flows, so daily_return_pct is clean.
    Zero/negative NAV rows are filtered out to prevent fake -100% returns from
    price-outage days.
    """
    from models.database import ShadowPortfolioSnapshot

    snaps = (
        db.query(ShadowPortfolioSnapshot)
        .filter(
            ShadowPortfolioSnapshot.shadow_portfolio_id == shadow_id,
            ShadowPortfolioSnapshot.snapshot_date >= since_date,
        )
        .order_by(ShadowPortfolioSnapshot.snapshot_date)
        .all()
    )
    # Filter out zero/negative NAV rows
    valid_snaps = [s for s in snaps if s.total_value and s.total_value > 0]
    values = [s.total_value for s in valid_snaps]
    daily = [s.daily_return_pct for s in valid_snaps if s.daily_return_pct is not None]
    total_return = _safe_return(_compute_twr(daily) if daily else _compute_return_pct(values))
    return total_return, compute_max_drawdown(values), _compute_daily_volatility(daily)


def compare_human_vs_ai(
    db: Session,
    portfolio_id: int,
    evaluation_days: int = 90,
) -> dict[str, Any]:
    """Compare human execution decisions vs AI model recommendations.

    For each UserExecutionDecision linked to a shadow portfolio:
      - APPROVED decisions: compare actual portfolio vs STATIC_FROZEN shadow
        (how did following the recommendation do vs staying put?)
      - REJECTED decisions: compare actual portfolio vs STATIC_FROZEN shadow
        (what return would the AI recommendation have produced?)
      - Any decision with ACTIVE_MODEL shadow: compare actual vs AI model

    Returns:
        decisions    : per-decision breakdown (shadow_return, actual_return, ai_better, …)
        summary      : aggregate hit_rate, mean_return_delta, cumulative data,
                       volatility_delta, drawdown_delta
        data_quality : how many decisions had enough snapshot data
    """
    from models.database import UserExecutionDecision, ShadowPortfolio

    cutoff = (date.today() - timedelta(days=evaluation_days)).isoformat()

    decisions_q = (
        db.query(UserExecutionDecision)
        .filter(
            UserExecutionDecision.portfolio_id == portfolio_id,
            UserExecutionDecision.executed_at >= cutoff,
        )
        .order_by(UserExecutionDecision.executed_at.desc())
        .all()
    )

    if not decisions_q:
        return {
            "portfolio_id": portfolio_id,
            "evaluation_days": evaluation_days,
            "decisions": [],
            "summary": _empty_summary(),
            "status": "no_decisions",
        }

    decision_details: list[dict[str, Any]] = []
    return_deltas: list[float] = []
    volatility_deltas: list[float] = []
    drawdown_deltas: list[float] = []
    ai_better_flags: list[bool] = []
    data_points_with_data = 0

    for dec in decisions_q:
        since = dec.executed_at.strftime("%Y-%m-%d") if dec.executed_at else cutoff

        # Actual portfolio performance since this decision
        actual_ret, actual_dd, actual_vol = _portfolio_return_since(db, portfolio_id, since)

        # Find the best available shadow for this decision
        shadow: Any | None = None

        # Priority 1: shadow directly linked to this decision
        if dec.id:
            shadow = (
                db.query(ShadowPortfolio)
                .filter(
                    ShadowPortfolio.execution_decision_id == dec.id,
                    ShadowPortfolio.is_active == True,  # noqa: E712
                )
                .first()
            )

        # Priority 2: ACTIVE_MODEL shadow for this portfolio
        if shadow is None:
            shadow = (
                db.query(ShadowPortfolio)
                .filter(
                    ShadowPortfolio.portfolio_id == portfolio_id,
                    ShadowPortfolio.shadow_type == "ACTIVE_MODEL",
                    ShadowPortfolio.is_active == True,  # noqa: E712
                )
                .first()
            )

        shadow_ret: float | None = None
        shadow_dd: float = 0.0
        shadow_vol: float | None = None
        shadow_id: int | None = None

        if shadow:
            shadow_id = shadow.id
            shadow_ret, shadow_dd, shadow_vol = _shadow_return_since(db, shadow.id, since)

        # Compute deltas
        return_delta: float | None = None
        ai_better: bool | None = None
        vol_delta: float | None = None
        dd_delta: float | None = None

        if shadow_ret is not None and actual_ret is not None:
            return_delta = round(shadow_ret - actual_ret, 4)
            ai_better = return_delta > 0
            data_points_with_data += 1
            return_deltas.append(return_delta)
            ai_better_flags.append(ai_better)

        if shadow_vol is not None and actual_vol is not None:
            vol_delta = round(shadow_vol - actual_vol, 4)
            volatility_deltas.append(vol_delta)

        if actual_dd is not None and shadow_dd is not None:
            dd_delta = round(shadow_dd - actual_dd, 4)
            drawdown_deltas.append(dd_delta)

        decision_details.append({
            "decision_id": dec.id,
            "decision_type": dec.decision,
            "executed_at": dec.executed_at.isoformat() + "Z" if dec.executed_at else None,
            "shadow_id": shadow_id,
            "shadow_type": shadow.shadow_type if shadow else None,
            "since_date": since,
            "actual_return_pct": actual_ret,
            "shadow_return_pct": shadow_ret,
            "actual_max_drawdown_pct": actual_dd,
            "shadow_max_drawdown_pct": shadow_dd,
            "return_delta": return_delta,
            "ai_better": ai_better,
            "vol_delta": vol_delta,
            "drawdown_delta": dd_delta,
        })

    # ── Aggregate summary ──────────────────────────────────────────────────────
    total = len(decisions_q)
    n = len(ai_better_flags)
    hit_rate = round(sum(ai_better_flags) / n * 100, 2) if n > 0 else None
    mean_return_delta = round(sum(return_deltas) / len(return_deltas), 4) if return_deltas else None
    mean_vol_delta = round(sum(volatility_deltas) / len(volatility_deltas), 4) if volatility_deltas else None
    mean_dd_delta = round(sum(drawdown_deltas) / len(drawdown_deltas), 4) if drawdown_deltas else None

    # Narrative
    verdict = _verdict(hit_rate, mean_return_delta)

    return {
        "portfolio_id": portfolio_id,
        "evaluation_days": evaluation_days,
        "decisions": decision_details,
        "summary": {
            "total_decisions": total,
            "decisions_with_data": data_points_with_data,
            "hit_rate_pct": hit_rate,                        # % of decisions AI did better
            "mean_return_delta": mean_return_delta,          # avg (shadow − actual)
            "mean_volatility_delta": mean_vol_delta,         # avg (shadow_vol − actual_vol)
            "mean_drawdown_delta": mean_dd_delta,            # avg (shadow_dd − actual_dd)
            "ai_wins": sum(ai_better_flags) if ai_better_flags else 0,
            "human_wins": sum(1 for b in ai_better_flags if not b),
            "verdict": verdict,
        },
        "status": "ok",
    }


def _empty_summary() -> dict[str, Any]:
    return {
        "total_decisions": 0,
        "decisions_with_data": 0,
        "hit_rate_pct": None,
        "mean_return_delta": None,
        "mean_volatility_delta": None,
        "mean_drawdown_delta": None,
        "ai_wins": 0,
        "human_wins": 0,
        "verdict": "No execution decisions recorded yet.",
    }


def _verdict(hit_rate: float | None, mean_delta: float | None) -> str:
    if hit_rate is None:
        return "Insufficient data to compare AI vs human performance."
    if hit_rate >= 70:
        return (
            f"AI recommendations outperformed human execution {hit_rate:.0f}% of the time "
            f"(avg +{mean_delta:+.2f}% per decision). Strong signal quality."
        )
    if hit_rate >= 50:
        return (
            f"AI recommendations were better than human execution {hit_rate:.0f}% of the time "
            f"(avg {mean_delta:+.2f}% per decision). Mixed signal — review rejected recommendations."
        )
    return (
        f"Human execution outperformed AI recommendations {100 - hit_rate:.0f}% of the time "
        f"(avg {mean_delta:+.2f}% per decision). Human judgment added value."
    )
