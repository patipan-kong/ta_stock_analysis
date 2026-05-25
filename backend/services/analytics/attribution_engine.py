"""attribution_engine.py — Phase 3B.7B

Portfolio attribution analytics: actual vs shadow portfolio comparison.

Computes deterministically from stored PortfolioSnapshot and
ShadowPortfolioSnapshot rows — no yfinance calls.

Public API:
    compute_max_drawdown(values)           → float (% as positive number)
    compute_portfolio_attribution(db, portfolio_id, evaluation_window_days)
    get_attribution_summary(db, portfolio_id)
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# ── Math utilities ─────────────────────────────────────────────────────────────

def compute_max_drawdown(values: list[float]) -> float:
    """Return the maximum peak-to-trough drawdown as a positive percentage.

    Returns 0.0 when fewer than 2 values or all values are zero.
    """
    if len(values) < 2:
        return 0.0
    peak = values[0]
    max_dd = 0.0
    for v in values:
        if v > peak:
            peak = v
        if peak > 0:
            dd = (peak - v) / peak
            if dd > max_dd:
                max_dd = dd
    return round(max_dd * 100, 4)


def _compute_return_pct(values: list[float]) -> float | None:
    """Compute total return % from first to last value in the series."""
    if len(values) < 2 or values[0] == 0:
        return None
    return round((values[-1] - values[0]) / values[0] * 100, 4)


def _compute_daily_volatility(daily_returns: list[float]) -> float | None:
    """Annualized volatility from daily return percentages (stdev * sqrt(252))."""
    if len(daily_returns) < 5:
        return None
    n = len(daily_returns)
    mean = sum(daily_returns) / n
    variance = sum((r - mean) ** 2 for r in daily_returns) / (n - 1)
    std_dev = variance ** 0.5
    return round(std_dev * (252 ** 0.5), 4)


# ── Portfolio snapshot helpers ─────────────────────────────────────────────────

def _get_actual_snapshots(db: Session, portfolio_id: int, cutoff: str) -> list[Any]:
    from models.database import PortfolioSnapshot
    return (
        db.query(PortfolioSnapshot)
        .filter(
            PortfolioSnapshot.portfolio_id == portfolio_id,
            PortfolioSnapshot.snapshot_date >= cutoff,
        )
        .order_by(PortfolioSnapshot.snapshot_date)
        .all()
    )


def _get_shadow_snapshots(db: Session, shadow_id: int, cutoff: str) -> list[Any]:
    from models.database import ShadowPortfolioSnapshot
    return (
        db.query(ShadowPortfolioSnapshot)
        .filter(
            ShadowPortfolioSnapshot.shadow_portfolio_id == shadow_id,
            ShadowPortfolioSnapshot.snapshot_date >= cutoff,
        )
        .order_by(ShadowPortfolioSnapshot.snapshot_date)
        .all()
    )


def _find_shadow(db: Session, portfolio_id: int, shadow_type: str) -> Any | None:
    from models.database import ShadowPortfolio
    return (
        db.query(ShadowPortfolio)
        .filter(
            ShadowPortfolio.portfolio_id == portfolio_id,
            ShadowPortfolio.shadow_type == shadow_type,
            ShadowPortfolio.is_active == True,  # noqa: E712
        )
        .order_by(ShadowPortfolio.created_at.desc())
        .first()
    )


# ── Core attribution computation ───────────────────────────────────────────────

def compute_portfolio_attribution(
    db: Session,
    portfolio_id: int,
    evaluation_window_days: int = 30,
) -> dict[str, Any]:
    """Compute human-vs-AI attribution for a portfolio over the evaluation window.

    Fetches actual PortfolioSnapshot rows and any active shadow portfolios,
    then computes returns, drawdowns, regret score, and avoided drawdown.

    All arithmetic is deterministic: no yfinance calls, no AI inference.
    Persists the result to AttributionMetric (idempotent on portfolio_id +
    period_start + period_end).

    Returns a fully-typed dict suitable for the API response.
    """
    from models.database import AttributionMetric, Workspace

    ws_row = db.query(Workspace).order_by(Workspace.id).first()
    ws_id = ws_row.id if ws_row else 1

    cutoff = (date.today() - timedelta(days=evaluation_window_days)).isoformat()
    today = date.today().isoformat()

    # ── Actual portfolio ───────────────────────────────────────────────────────
    actual_snaps = _get_actual_snapshots(db, portfolio_id, cutoff)
    actual_values = [s.total_value for s in actual_snaps]
    actual_daily = [
        s.daily_return_pct for s in actual_snaps if s.daily_return_pct is not None
    ]
    actual_return = _compute_return_pct(actual_values)
    actual_drawdown = compute_max_drawdown(actual_values)
    actual_volatility = _compute_daily_volatility(actual_daily)

    # ── STATIC_FROZEN shadow ───────────────────────────────────────────────────
    static_shadow = _find_shadow(db, portfolio_id, "STATIC_FROZEN")
    static_return = None
    static_drawdown = None
    static_volatility = None
    static_shadow_id = None

    if static_shadow:
        static_shadow_id = static_shadow.id
        static_snaps = _get_shadow_snapshots(db, static_shadow.id, cutoff)
        static_values = [s.total_value for s in static_snaps]
        static_daily = [
            s.daily_return_pct for s in static_snaps if s.daily_return_pct is not None
        ]
        static_return = _compute_return_pct(static_values)
        static_drawdown = compute_max_drawdown(static_values)
        static_volatility = _compute_daily_volatility(static_daily)

    # ── ACTIVE_MODEL shadow ────────────────────────────────────────────────────
    ai_shadow = _find_shadow(db, portfolio_id, "ACTIVE_MODEL")
    ai_model_return = None
    ai_model_drawdown = None
    ai_model_volatility = None
    shadow_id_for_record = None

    if ai_shadow:
        shadow_id_for_record = ai_shadow.id
        ai_snaps = _get_shadow_snapshots(db, ai_shadow.id, cutoff)
        ai_values = [s.total_value for s in ai_snaps]
        ai_daily = [
            s.daily_return_pct for s in ai_snaps if s.daily_return_pct is not None
        ]
        ai_model_return = _compute_return_pct(ai_values)
        ai_model_drawdown = compute_max_drawdown(ai_values)
        ai_model_volatility = _compute_daily_volatility(ai_daily)

    shadow_id_for_record = shadow_id_for_record or static_shadow_id

    # ── Derived metrics ────────────────────────────────────────────────────────
    # avoided_drawdown: static_drawdown - actual_drawdown
    #   positive → the AI recommendation had more drawdown (human held steadier)
    #   negative → AI recommendation would have reduced drawdown
    avoided_drawdown: float | None = None
    if actual_drawdown is not None and static_drawdown is not None:
        avoided_drawdown = round(static_drawdown - actual_drawdown, 4)

    # regret_score: ai_model_return - actual_return
    #   positive → AI model portfolio would have done better (human left gains on table)
    #   negative → human execution outperformed AI recommendation
    regret_score: float | None = None
    ai_outperformed: bool | None = None
    if ai_model_return is not None and actual_return is not None:
        regret_score = round(ai_model_return - actual_return, 4)
        ai_outperformed = regret_score > 0

    result: dict[str, Any] = {
        "portfolio_id": portfolio_id,
        "evaluation_window_days": evaluation_window_days,
        "period_start": cutoff,
        "period_end": today,
        "actual": {
            "return_pct": actual_return,
            "max_drawdown_pct": actual_drawdown,
            "annualized_volatility": actual_volatility,
            "snapshot_count": len(actual_values),
        },
        "static_shadow": {
            "shadow_id": static_shadow_id,
            "return_pct": static_return,
            "max_drawdown_pct": static_drawdown,
            "annualized_volatility": static_volatility,
        } if static_shadow else None,
        "ai_model_shadow": {
            "shadow_id": ai_shadow.id if ai_shadow else None,
            "return_pct": ai_model_return,
            "max_drawdown_pct": ai_model_drawdown,
            "annualized_volatility": ai_model_volatility,
        } if ai_shadow else None,
        "avoided_drawdown_pct": avoided_drawdown,
        "regret_score": regret_score,
        "ai_outperformed": ai_outperformed,
        "interpretation": _interpret(regret_score, avoided_drawdown, actual_return),
        "computed_at": datetime.utcnow().isoformat() + "Z",
    }

    # ── Persist ────────────────────────────────────────────────────────────────
    if shadow_id_for_record:
        try:
            existing = (
                db.query(AttributionMetric)
                .filter_by(
                    shadow_portfolio_id=shadow_id_for_record,
                    evaluation_period_start=cutoff,
                    evaluation_period_end=today,
                )
                .first()
            )
            if existing:
                existing.portfolio_id = portfolio_id
                existing.evaluation_window_days = evaluation_window_days
                existing.actual_return_pct = actual_return
                existing.static_shadow_return_pct = static_return
                existing.ai_model_return_pct = ai_model_return
                existing.avoided_drawdown_pct = avoided_drawdown
                existing.regret_score = regret_score
                existing.ai_outperformed = ai_outperformed
                existing.computed_at = datetime.utcnow()
            else:
                db.add(AttributionMetric(
                    workspace_id=ws_id,
                    shadow_portfolio_id=shadow_id_for_record,
                    portfolio_id=portfolio_id,
                    evaluation_period_start=cutoff,
                    evaluation_period_end=today,
                    evaluation_window_days=evaluation_window_days,
                    actual_return_pct=actual_return,
                    static_shadow_return_pct=static_return,
                    ai_model_return_pct=ai_model_return,
                    avoided_drawdown_pct=avoided_drawdown,
                    regret_score=regret_score,
                    ai_outperformed=ai_outperformed,
                    computed_at=datetime.utcnow(),
                ))
            db.commit()
        except Exception as exc:
            logger.warning("[ATTRIBUTION] DB write failed: %s", exc)
            db.rollback()

    return result


def _interpret(
    regret_score: float | None,
    avoided_drawdown: float | None,
    actual_return: float | None,
) -> str:
    """One-sentence plain-English summary of the attribution result."""
    if regret_score is None:
        return "Insufficient shadow portfolio data to compare AI vs actual performance."
    if regret_score > 2:
        return (
            f"AI model portfolio would have outperformed by {regret_score:+.2f}% — "
            "consider following recommendations more closely."
        )
    if regret_score < -2:
        return (
            f"Human execution outperformed AI model by {abs(regret_score):.2f}% — "
            "your adjustments added value over the recommendation."
        )
    return (
        f"AI model and actual portfolio returned within {abs(regret_score):.2f}% of each other "
        "— execution was broadly aligned with recommendations."
    )


def get_attribution_summary(
    db: Session,
    portfolio_id: int,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Return recent AttributionMetric rows for a portfolio, newest first."""
    from models.database import AttributionMetric

    rows = (
        db.query(AttributionMetric)
        .filter(AttributionMetric.portfolio_id == portfolio_id)
        .order_by(AttributionMetric.computed_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "evaluation_window_days": r.evaluation_window_days,
            "period_start": r.evaluation_period_start,
            "period_end": r.evaluation_period_end,
            "actual_return_pct": r.actual_return_pct,
            "static_shadow_return_pct": r.static_shadow_return_pct,
            "ai_model_return_pct": r.ai_model_return_pct,
            "avoided_drawdown_pct": r.avoided_drawdown_pct,
            "regret_score": r.regret_score,
            "ai_outperformed": r.ai_outperformed,
            "total_alpha": r.total_alpha,
            "computed_at": r.computed_at.isoformat() + "Z" if r.computed_at else None,
        }
        for r in rows
    ]
