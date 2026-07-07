"""opportunity_cost.py — AI Evaluation M5: Counterfactual Opportunity-Cost Ledger.

Prices what every divergence from the AI's recommendation actually did (UX
S6; OPTIMIZER_PHILOSOPHY.md §12 "a philosophy that cannot measure its own
downside is dogma"). A divergence is any decision that was not full
compliance: REJECTED, PARTIAL_EXECUTION, MANUAL_OVERRIDE, or an
is_system_generated EXPIRED row (P4 — an ignored recommendation nobody
explicitly rejected).

Pricing method — reuses grade rows, never re-derives return math (PLAN
§4.6): for the divergent decision's recommendation snapshot, the nearest
matured RecommendationGrade horizon row (grade_kind H7/H30/H90/H180,
written by M1's horizon_grader) already holds
`return_pct` = the recommendation-keyed shadow's return — i.e. exactly
"what would have happened had this recommendation been followed in full."
`services.analytics.human_vs_ai._portfolio_return_since` (existing, M3's
compare_human_vs_ai already depends on it) gives the actual portfolio's
return over the same window. The difference, sign-flipped so that a
positive number always means "diverging helped you", is the row's
counterfactual_delta_pct:

    counterfactual_delta_pct = actual_return_pct − counterfactual_recommendation_return_pct

This is a **decision-level approximation**, not a per-symbol figure — the
data model does not record which individual trade within a multi-trade
recommendation drove a REJECTED/PARTIAL/OVERRIDE decision, the same
documented limitation execution_ledger.py's acceptance_by_class already
carries (PLAN §4.7, surfaced via the `note` field on every row, never
hidden).

System's-own-deferrals honesty strip: execution_optimizer.py defers
SELL/REDUCE candidates whose funding need disappeared (OPTIMIZER_PHILOSOPHY
§7 STATE_DEFERRED). Per UX S6 this deserves its own accountability ledger —
"the Opportunity Cost metric pointed at the machine" — but pricing one
deferred trade in isolation would need a per-symbol counterfactual price
series this system does not yet track (no such infrastructure exists for
single trades, only for whole recommendations via the recommendation-keyed
shadow). Rather than fabricate a number, each deferral is reported
structurally (symbol, reason, snapshot) with counterfactual_pricing
explicitly "unavailable" — PLAN §4.7/§4.8: never a guessed return.

Zero AI calls. Zero writes — this module only reads RecommendationGrade,
UserExecutionDecision, RecommendationSnapshot (PLAN §4.1).

Public API
----------
compute_opportunity_cost(db, portfolio_id, period_days=90) -> dict
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# APPROVED = full compliance, never a divergence. Every other recorded
# decision type is a divergence worth pricing.
_DIVERGENT_DECISIONS = ("REJECTED", "PARTIAL_EXECUTION", "MANUAL_OVERRIDE", "EXPIRED")


def _divergence_type(dec: Any) -> str | None:
    if dec.decision not in _DIVERGENT_DECISIONS:
        return None
    return dec.decision


def _system_deferrals(db: Session, ws: int, portfolio_id: int, cutoff: datetime) -> list[dict[str, Any]]:
    from models.database import RecommendationSnapshot
    from services.evaluation.plan_grader import derive_full_plan, read_snapshot_plan_inputs
    from services.optimizer.execution_optimizer import STATE_DEFERRED

    snaps = (
        db.query(RecommendationSnapshot)
        .filter(
            RecommendationSnapshot.workspace_id == ws,
            RecommendationSnapshot.portfolio_id == portfolio_id,
            RecommendationSnapshot.created_at >= cutoff,
        )
        .order_by(RecommendationSnapshot.created_at.desc())
        .all()
    )

    deferrals: list[dict[str, Any]] = []
    for snap in snaps:
        inputs = read_snapshot_plan_inputs(db, snap)
        if inputs is None:
            continue
        plan = derive_full_plan(inputs["target_allocations"], inputs["cash_available"], inputs["violations"])
        for t in plan["execution_optimization"].trades:
            if t.execution_state != STATE_DEFERRED:
                continue
            deferrals.append({
                "snapshot_id": snap.id,
                "date": snap.created_at.isoformat() + "Z" if snap.created_at else None,
                "symbol": t.symbol,
                "action": t.action,
                "reason": t.reason,
                "note": t.note,
                "counterfactual_pricing": "unavailable",
                "counterfactual_reason": (
                    "Pricing one deferred trade in isolation requires a per-trade "
                    "counterfactual price series that is not yet tracked; recorded "
                    "structurally (symbol + reason) only — never a fabricated return."
                ),
            })
    return deferrals


def compute_opportunity_cost(db: Session, portfolio_id: int, period_days: int = 90) -> dict[str, Any]:
    """Counterfactual waterfall of every divergence from AI recommendations (UX S6)."""
    from models.database import UserExecutionDecision, Workspace
    from services.analytics.human_vs_ai import _nearest_graded_horizon, _portfolio_return_since

    ws_row = db.query(Workspace).order_by(Workspace.id).first()
    ws = ws_row.id if ws_row else 1
    cutoff = datetime.utcnow() - timedelta(days=period_days)

    decisions = (
        db.query(UserExecutionDecision)
        .filter(
            UserExecutionDecision.workspace_id == ws,
            UserExecutionDecision.portfolio_id == portfolio_id,
            UserExecutionDecision.executed_at >= cutoff,
        )
        .order_by(UserExecutionDecision.executed_at.desc())
        .all()
    )

    rows: list[dict[str, Any]] = []
    maturing_count = 0
    graded_count = 0
    net_total = 0.0

    for dec in decisions:
        dtype = _divergence_type(dec)
        if dtype is None:
            continue
        snap = dec.snapshot
        if snap is None:
            continue

        grade_row = _nearest_graded_horizon(db, snap.id, period_days)
        since = dec.executed_at.strftime("%Y-%m-%d") if dec.executed_at else cutoff.date().isoformat()
        actual_ret, _dd, _vol = _portfolio_return_since(db, portfolio_id, since)

        base = {
            "decision_id": dec.id,
            "snapshot_id": snap.id,
            "date": dec.executed_at.isoformat() + "Z" if dec.executed_at else None,
            "divergence_type": dtype,
            "override_type": dec.override_type,
            "original_symbol": dec.original_symbol,
            "replacement_symbol": dec.replacement_symbol,
        }

        if grade_row is None or grade_row.return_pct is None or actual_ret is None:
            maturing_count += 1
            rows.append({
                **base,
                "status": "maturing",
                "grade_kind": grade_row.grade_kind if grade_row else None,
                "counterfactual_recommendation_return_pct": None,
                "actual_return_pct": actual_ret,
                "counterfactual_delta_pct": None,
                "note": "Recommendation shadow has not matured at any horizon within this window yet.",
            })
            continue

        counterfactual_delta_pct = round(actual_ret - grade_row.return_pct, 4)
        net_total += counterfactual_delta_pct
        graded_count += 1

        rows.append({
            **base,
            "status": "graded",
            "grade_kind": grade_row.grade_kind,
            "counterfactual_recommendation_return_pct": grade_row.return_pct,
            "actual_return_pct": actual_ret,
            "counterfactual_delta_pct": counterfactual_delta_pct,
            "note": (
                "Decision-level approximation: prices the whole recommendation's "
                "counterfactual shadow vs. actual portfolio return since this "
                "decision, not the individual symbol(s) diverged on."
            ),
        })

    rows.sort(key=lambda r: abs(r.get("counterfactual_delta_pct") or 0), reverse=True)

    return {
        "portfolio_id": portfolio_id,
        "period_days": period_days,
        "as_of": datetime.utcnow().isoformat() + "Z",
        "status": "ok" if rows else "cold_start",
        "net_opportunity_cost_pct": round(net_total, 4) if graded_count else None,
        "graded_count": graded_count,
        "maturing_count": maturing_count,
        "rows": rows,
        "system_deferrals": _system_deferrals(db, ws, portfolio_id, cutoff),
    }
