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
from datetime import date, datetime, timedelta
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


_REASON_LABELS = {
    "MANDATORY_RISK_REDUCTION": "Mandatory Risk Reduction",
    "POLICY_ENFORCEMENT": "Policy Enforcement",
    "PORTFOLIO_IMPROVEMENT": "Portfolio Improvement",
}


def _nearest_graded_horizon(db: Session, snapshot_id: int, period_days: int):
    """Nearest matured RecommendationGrade horizon row for one snapshot.

    Prefers the largest horizon that matured within period_days; falls back
    to whatever horizon is graded if none fit that window (a decision can
    still be scored against, e.g., an H7 grade even inside a 90-day query).
    Returns None when nothing has graded yet — callers must treat that as
    "maturing", never guess a return (PLAN §4.7). Shared by
    services.evaluation.opportunity_cost (M5) and compute_scoreboard below
    so "what would the recommendation have returned" is read the same way
    everywhere (ENGINEERING_PRINCIPLES Single Source of Truth).
    """
    from models.database import RecommendationGrade

    rows = (
        db.query(RecommendationGrade)
        .filter(
            RecommendationGrade.recommendation_snapshot_id == snapshot_id,
            RecommendationGrade.grade_kind.like("H%"),
        )
        .all()
    )
    if not rows:
        return None
    candidates = sorted(rows, key=lambda r: int(r.grade_kind[1:]))
    within = [r for r in candidates if int(r.grade_kind[1:]) <= period_days]
    return within[-1] if within else candidates[0]


def compute_scoreboard(db: Session, portfolio_id: int, period_days: int = 90) -> dict[str, Any]:
    """Grade-sourced Human-vs-AI Scoreboard (AI Evaluation M5, UX S5).

    Additive sibling to compare_human_vs_ai — that function's live ad-hoc
    valuation is unchanged and still backs /analytics/human-vs-ai,
    /analytics/ai-vs-human-timeline, and the optimizer page's existing
    AttributionPanel consumers (zero regression risk, ENGINEERING_PRINCIPLES
    System Integration). This function instead reads the same
    RecommendationGrade horizon rows the Recommendations Ledger (S2) and
    Opportunity Cost (S6) already use — "verdicts sourced from grade rows,"
    per the M5 implementation plan — so every Evaluation-hub screen that
    says "the AI would have returned X%" is reading the identical recorded
    number. Decisions without a matured grade row are reported as maturing,
    never estimated from a live in-flight valuation.

    is_system_generated (EXPIRED) rows are excluded here: S5 is specifically
    about deliberate human judgment vs the AI ("where is each of you
    strong?" — UX tone rule), whereas an EXPIRED row reflects inaction, not
    a decision. Inaction is priced instead in
    services.evaluation.opportunity_cost, which is the honest ledger for
    ignored/expired recommendations.

    Sign convention matches compare_human_vs_ai: delta = ai_recommendation
    return − actual_return (positive = AI would have done better).
    net_effect_pct is the mirror (−mean(delta)): positive means the human's
    own decisions outperformed full compliance.

    Trade-class and override-type segmentation are decision-level
    approximations — the same documented convention as
    execution_ledger.py's acceptance_by_class (a multi-trade recommendation
    contributes its outcome to every Reason class it contains).
    """
    from main import _get_evaluation_settings
    from models.database import UserExecutionDecision, Workspace
    from services.evaluation.plan_grader import derive_full_plan, read_snapshot_plan_inputs

    ws_row = db.query(Workspace).order_by(Workspace.id).first()
    ws = ws_row.id if ws_row else 1
    settings = _get_evaluation_settings(db, ws)
    tie_band_pct = float(settings.get("tie_band_pct") or 0.3)

    cutoff = (date.today() - timedelta(days=period_days)).isoformat()

    decisions = (
        db.query(UserExecutionDecision)
        .filter(
            UserExecutionDecision.workspace_id == ws,
            UserExecutionDecision.portfolio_id == portfolio_id,
            UserExecutionDecision.executed_at >= cutoff,
            UserExecutionDecision.is_system_generated == False,  # noqa: E712
        )
        .order_by(UserExecutionDecision.executed_at.desc())
        .all()
    )

    you_beat_ai = 0
    ai_beat_you = 0
    ties = 0
    maturing = 0
    deltas: list[float] = []
    class_totals: dict[str, dict[str, int]] = {}
    override_totals: dict[str, dict[str, int]] = {}
    decision_rows: list[dict[str, Any]] = []

    for dec in decisions:
        snap = dec.snapshot
        if snap is None:
            continue

        grade_row = _nearest_graded_horizon(db, snap.id, period_days)
        since = dec.executed_at.strftime("%Y-%m-%d") if dec.executed_at else cutoff
        actual_ret, _dd, _vol = _portfolio_return_since(db, portfolio_id, since)

        if grade_row is None or grade_row.return_pct is None or actual_ret is None:
            maturing += 1
            decision_rows.append({
                "decision_id": dec.id, "snapshot_id": snap.id, "status": "maturing",
                "decision": dec.decision, "delta": None, "outcome": None, "grade_kind": None,
            })
            continue

        delta = round(grade_row.return_pct - actual_ret, 4)
        deltas.append(delta)
        if abs(delta) <= tie_band_pct:
            outcome = "tie"
            ties += 1
        elif delta > 0:
            outcome = "ai_better"
            ai_beat_you += 1
        else:
            outcome = "human_better"
            you_beat_ai += 1

        decision_rows.append({
            "decision_id": dec.id, "snapshot_id": snap.id, "status": "graded",
            "decision": dec.decision, "delta": delta, "outcome": outcome,
            "grade_kind": grade_row.grade_kind,
        })

        inputs = read_snapshot_plan_inputs(db, snap)
        if inputs is not None:
            plan = derive_full_plan(inputs["target_allocations"], inputs["cash_available"], inputs["violations"])
            seen_labels: set[str] = set()
            for t in plan["execution_optimization"].trades:
                label = _REASON_LABELS.get(t.reason)
                if not label or label in seen_labels:
                    continue
                seen_labels.add(label)
                bucket = class_totals.setdefault(label, {"human_better": 0, "ai_better": 0, "tie": 0})
                bucket[outcome] += 1

        if dec.decision == "MANUAL_OVERRIDE" and dec.override_type:
            bucket = override_totals.setdefault(dec.override_type, {"human_better": 0, "ai_better": 0, "tie": 0})
            bucket[outcome] += 1

    net_effect_pct = round(-sum(deltas) / len(deltas), 4) if deltas else None

    return {
        "portfolio_id": portfolio_id,
        "period_days": period_days,
        "as_of": datetime.utcnow().isoformat() + "Z",
        "status": "ok" if decisions else "cold_start",
        "tie_band_pct": tie_band_pct,
        "summary": {
            "n_graded": len(deltas),
            "you_beat_ai": you_beat_ai,
            "ai_beat_you": ai_beat_you,
            "ties": ties,
            "maturing": maturing,
            "net_effect_pct": net_effect_pct,
        },
        "by_trade_class": {label: {**v, "total": sum(v.values())} for label, v in class_totals.items()},
        "by_override_type": {label: {**v, "total": sum(v.values())} for label, v in override_totals.items()},
        "decisions": decision_rows,
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
