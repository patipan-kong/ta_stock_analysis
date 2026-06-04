"""attribution_engine.py — Phase 3B.7B (stabilized, Phase 3B.9S)

Portfolio attribution analytics: actual vs shadow portfolio comparison.

Computes deterministically from stored PortfolioSnapshot and
ShadowPortfolioSnapshot rows — no yfinance calls.

Sanity filters (Phase 3B.9S)
-----------------------------
All snapshot series are pre-filtered to remove zero/negative NAV values
before any arithmetic.  This prevents:
  - Fake -100% returns from shadows with missing price data
  - Zero-divide in drawdown calculation
  - Infinite or NaN returns from corrupted inception baselines

_safe_return() clips results to [-99.9%, +1000%] — values outside this
range are treated as corrupted data (returned as None with a warning log).

Cash-flow-adjusted return accounting
-------------------------------------
PortfolioSnapshot.investment_return_pct stores the cash-flow-adjusted daily
return (deposits / withdrawals stripped out).  Actual portfolio total return
uses TWR chaining over investment_return_pct when available.

Shadow portfolio snapshots have no external cash flows (paper portfolios),
so their daily_return_pct is clean and used for TWR chaining directly.

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

# Plausibility bounds for return percentages.
# Values outside these are almost certainly data corruption, not real returns.
_MIN_PLAUSIBLE_RETURN = -99.9
_MAX_PLAUSIBLE_RETURN = 1000.0


# ── Math utilities ─────────────────────────────────────────────────────────────

def compute_max_drawdown(values: list[float]) -> float:
    """Return the maximum peak-to-trough drawdown as a positive percentage.

    Filters out zero and negative values before computation — they indicate
    missing or corrupted NAV data and must not create artificial drawdowns.
    Returns 0.0 when fewer than 2 valid values remain.
    """
    valid = [v for v in values if v and v > 0]
    if len(valid) < 2:
        return 0.0
    peak = valid[0]
    max_dd = 0.0
    for v in valid:
        if v > peak:
            peak = v
        if peak > 0:
            dd = (peak - v) / peak
            if dd > max_dd:
                max_dd = dd
    return round(max_dd * 100, 4)


def _safe_return(ret: float | None) -> float | None:
    """Clamp a return percentage to plausible bounds.

    Returns None for values clearly outside plausible range, which prevents
    corrupted baselines (e.g. zero NAV from missing prices) from displaying
    fake -100% or +10000% returns in the UI.
    """
    if ret is None:
        return None
    if ret < _MIN_PLAUSIBLE_RETURN or ret > _MAX_PLAUSIBLE_RETURN:
        logger.warning(
            "[ATTRIBUTION] Return %.2f%% outside plausible bounds [%.1f%%, %.1f%%] — suppressed",
            ret, _MIN_PLAUSIBLE_RETURN, _MAX_PLAUSIBLE_RETURN,
        )
        return None
    return ret


def _compute_return_pct(values: list[float]) -> float | None:
    """Compute total return % from first to last NAV value.

    Filters invalid (zero/negative) values. Returns None if fewer than
    2 valid values remain or if the baseline is 0.

    NOTE: This is contaminated by external cash flows when PortfolioSnapshot
    rows do not have investment_return_pct populated (pre-Phase-3B.8 history).
    Prefer _compute_twr() for actual portfolios.
    """
    valid = [v for v in values if v and v > 0]
    if len(valid) < 2 or valid[0] == 0:
        return None
    return _safe_return(round((valid[-1] - valid[0]) / valid[0] * 100, 4))


def _compute_twr(adjusted_returns: list[float]) -> float | None:
    """Time-Weighted Return from cash-flow-adjusted daily return percentages.

    Chains sub-period returns multiplicatively — correct even when external
    cash flows (deposits / withdrawals) occurred during the window.

        TWR = ∏(1 + r_i / 100) - 1  (expressed as %)

    Returns None when the list is empty.
    """
    if not adjusted_returns:
        return None
    result = 1.0
    for r in adjusted_returns:
        result *= (1.0 + r / 100.0)
    return _safe_return(round((result - 1.0) * 100.0, 4))


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


def _actual_portfolio_metrics(
    snaps: list[Any],
) -> tuple[float | None, float, float | None]:
    """Compute (total_return_pct, max_drawdown_pct, annualized_vol) for actual portfolio.

    Filters snapshots with zero/negative total_value before any arithmetic.
    Uses cash-flow-adjusted investment_return_pct for TWR when available.
    Falls back to raw daily_return_pct for volatility (historical rows).
    Falls back to first/last NAV for total return when no adjusted returns exist.
    """
    # Filter out corrupted / missing NAV rows
    valid_snaps = [s for s in snaps if s.total_value and s.total_value > 0]
    if not valid_snaps:
        return None, 0.0, None

    values = [s.total_value for s in valid_snaps]

    # Cash-flow-adjusted daily returns (populated since Phase 3B.8)
    adjusted = [
        s.investment_return_pct
        for s in valid_snaps
        if s.investment_return_pct is not None
    ]
    # Raw daily returns (always present after first snapshot)
    raw_daily = [
        s.daily_return_pct
        for s in valid_snaps
        if s.daily_return_pct is not None
    ]

    total_return = _compute_twr(adjusted) if adjusted else _compute_return_pct(values)
    volatility = _compute_daily_volatility(adjusted if adjusted else raw_daily)
    max_dd = compute_max_drawdown(values)

    return total_return, max_dd, volatility


def _shadow_portfolio_metrics(
    snaps: list[Any],
) -> tuple[float | None, float, float | None]:
    """Compute (total_return_pct, max_drawdown_pct, annualized_vol) for a shadow portfolio.

    Filters snapshots with zero/negative total_value before any arithmetic.
    Shadow portfolios have no external cash flows (paper-only portfolios), so
    daily_return_pct is already cash-flow-clean and used for TWR chaining.
    """
    # Filter out corrupted / missing NAV rows
    valid_snaps = [s for s in snaps if s.total_value and s.total_value > 0]
    if not valid_snaps:
        return None, 0.0, None

    values = [s.total_value for s in valid_snaps]
    daily = [s.daily_return_pct for s in valid_snaps if s.daily_return_pct is not None]

    total_return = _compute_twr(daily) if daily else _compute_return_pct(values)
    volatility = _compute_daily_volatility(daily)
    max_dd = compute_max_drawdown(values)

    return total_return, max_dd, volatility


# ── Core attribution computation ───────────────────────────────────────────────

def compute_portfolio_attribution(
    db: Session,
    portfolio_id: int,
    evaluation_window_days: int = 30,
) -> dict[str, Any]:
    """Compute human-vs-AI attribution for a portfolio over the evaluation window.

    All return values pass through _safe_return() before use.  Zero-NAV and
    negative-NAV snapshot rows are excluded from metric computation.  This
    prevents corrupted shadow baselines from generating -100% returns or
    infinite drawdowns in the attribution output.

    Cash-flow correctness:
        Actual portfolio uses TWR from investment_return_pct (adjusted).
        Shadow portfolios use TWR from daily_return_pct (already clean).
    """
    from models.database import AttributionMetric, Workspace

    ws_row = db.query(Workspace).order_by(Workspace.id).first()
    ws_id = ws_row.id if ws_row else 1

    cutoff = (date.today() - timedelta(days=evaluation_window_days)).isoformat()
    today = date.today().isoformat()

    # ── Actual portfolio ───────────────────────────────────────────────────────
    actual_snaps = _get_actual_snapshots(db, portfolio_id, cutoff)
    actual_return_raw, actual_drawdown, actual_volatility = _actual_portfolio_metrics(actual_snaps)
    actual_return = _safe_return(actual_return_raw)

    # ── STATIC_FROZEN shadow ───────────────────────────────────────────────────
    static_shadow = _find_shadow(db, portfolio_id, "STATIC_FROZEN")
    static_return: float | None = None
    static_drawdown: float | None = None
    static_volatility: float | None = None
    static_shadow_id: int | None = None
    static_snaps: list[Any] = []

    if static_shadow:
        static_shadow_id = static_shadow.id
        static_snaps = _get_shadow_snapshots(db, static_shadow.id, cutoff)
        sr_raw, sd, sv = _shadow_portfolio_metrics(static_snaps)
        static_return = _safe_return(sr_raw)
        static_drawdown = sd
        static_volatility = sv

    # ── ACTIVE_MODEL shadow ────────────────────────────────────────────────────
    ai_shadow = _find_shadow(db, portfolio_id, "ACTIVE_MODEL")
    ai_model_return: float | None = None
    ai_model_drawdown: float | None = None
    ai_model_volatility: float | None = None
    shadow_id_for_record: int | None = None
    ai_snaps: list[Any] = []

    if ai_shadow:
        shadow_id_for_record = ai_shadow.id
        ai_snaps = _get_shadow_snapshots(db, ai_shadow.id, cutoff)
        air_raw, aid, aiv = _shadow_portfolio_metrics(ai_snaps)
        ai_model_return = _safe_return(air_raw)
        ai_model_drawdown = aid
        ai_model_volatility = aiv

    shadow_id_for_record = shadow_id_for_record or static_shadow_id

    # ── Derived metrics ────────────────────────────────────────────────────────
    avoided_drawdown: float | None = None
    if actual_drawdown is not None and static_drawdown is not None:
        avoided_drawdown = round(static_drawdown - actual_drawdown, 4)

    regret_score: float | None = None
    ai_outperformed: bool | None = None
    if ai_model_return is not None and actual_return is not None:
        regret_score = round(ai_model_return - actual_return, 4)
        ai_outperformed = regret_score > 0

    # Determine data quality for frontend display guidance
    valid_actual_count = len([s for s in actual_snaps if s.total_value and s.total_value > 0])
    has_sufficient_history = valid_actual_count >= 2

    # ── Structured data-readiness status ──────────────────────────────────────
    # Lets the frontend and diagnostic endpoint differentiate between:
    #   no_portfolio_snapshots   — scheduler hasn't run yet
    #   insufficient_portfolio_history — < 2 valid NAV points
    #   no_shadows               — optimizer never ran or no decisions recorded
    #   shadows_pending_valuation — shadows exist but today's snapshot not yet written
    #   ok                       — full comparison data available
    shadow_snap_count = len(
        [s for s in static_snaps + ai_snaps if s.total_value and s.total_value > 0]
    )
    if not actual_snaps:
        data_status = "no_portfolio_snapshots"
        data_points_available = 0
        required_days_remaining = 2
    elif not has_sufficient_history:
        data_status = "insufficient_portfolio_history"
        data_points_available = valid_actual_count
        required_days_remaining = max(0, 2 - valid_actual_count)
    elif static_shadow is None and ai_shadow is None:
        data_status = "no_shadows"
        data_points_available = valid_actual_count
        required_days_remaining = 0
    elif shadow_snap_count == 0:
        data_status = "shadows_pending_valuation"
        data_points_available = valid_actual_count
        required_days_remaining = 1
    else:
        data_status = "ok"
        data_points_available = valid_actual_count
        required_days_remaining = 0

    logger.info(
        "[ATTRIBUTION] portfolio_id=%s status=%s actual_snaps=%d shadow_snaps=%d "
        "actual_return=%s static_return=%s ai_return=%s",
        portfolio_id, data_status, valid_actual_count, shadow_snap_count,
        actual_return, static_return, ai_model_return,
    )

    result: dict[str, Any] = {
        "portfolio_id": portfolio_id,
        "evaluation_window_days": evaluation_window_days,
        "period_start": cutoff,
        "period_end": today,
        "status": data_status,
        "data_points_available": data_points_available,
        "required_days_remaining": required_days_remaining,
        "has_sufficient_history": has_sufficient_history,
        "actual": {
            "return_pct": actual_return,
            "max_drawdown_pct": actual_drawdown,
            "annualized_volatility": actual_volatility,
            "snapshot_count": valid_actual_count,
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
        "interpretation": _interpret(regret_score, avoided_drawdown, actual_return, has_sufficient_history),
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
    has_sufficient_history: bool = True,
) -> str:
    """One-sentence plain-English summary of the attribution result."""
    if not has_sufficient_history:
        return "Tracking started — insufficient history for comparison (need ≥2 snapshots)."
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
            "actual_return_pct": _safe_return(r.actual_return_pct),
            "static_shadow_return_pct": _safe_return(r.static_shadow_return_pct),
            "ai_model_return_pct": _safe_return(r.ai_model_return_pct),
            "avoided_drawdown_pct": r.avoided_drawdown_pct,
            "regret_score": r.regret_score,
            "ai_outperformed": r.ai_outperformed,
            "total_alpha": r.total_alpha,
            "computed_at": r.computed_at.isoformat() + "Z" if r.computed_at else None,
        }
        for r in rows
    ]
