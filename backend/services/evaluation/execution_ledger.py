"""execution_ledger.py — AI Evaluation M3: Execution ledger (S4) and
execution detail (S4b).

Read-only aggregation over M0/M2 data — reuses
services.evaluation.plan_grader.read_snapshot_plan_inputs / derive_full_plan
(the same reconstruction recommendation_ledger.py uses) and
services.evaluation.execution_analyzer.compute_execution_analysis (M2,
unchanged) for every per-decision score. No new grading arithmetic.

Class-segmented acceptance (UX D5 / S4): execution_optimizer.py only ever
assigns a Reason to SELL/REDUCE candidates (buy-side trades never pass
through it — OPTIMIZER_PHILOSOPHY.md §7/§9 module docstring) so "Optional
Rebalancing" never appears as a produced Reason; this ledger honestly
segments acceptance across the three Reasons execution_optimizer actually
produces (Mandatory Risk Reduction, Policy Enforcement, Portfolio
Improvement) rather than fabricating a fourth bucket the pipeline doesn't
emit. "Accepted" is evaluated at the snapshot/decision level (APPROVED or
PARTIAL_EXECUTION) — the data model does not record which individual trade
within a PARTIAL_EXECUTION decision was kept vs dropped, so per-trade
acceptance within a PARTIAL decision is a documented approximation, not a
precise measurement (PLAN §4.7 — surfaced via the `note` field, never
hidden).

Public API
----------
list_execution_ledger(db, portfolio_id, period_days=90) -> dict
get_execution_detail(db, portfolio_id, decision_id) -> dict | None
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_ACCEPTED_DECISIONS = ("APPROVED", "PARTIAL_EXECUTION")

_REASON_LABELS = {
    "MANDATORY_RISK_REDUCTION": "Mandatory Risk Reduction",
    "POLICY_ENFORCEMENT": "Policy Enforcement",
    "PORTFOLIO_IMPROVEMENT": "Portfolio Improvement",
}


def _recommendation_prices(snap: Any) -> dict[str, float]:
    import json

    prices: dict[str, float] = {}
    if not snap.scores_map_json:
        return prices
    try:
        scores_map = json.loads(snap.scores_map_json)
        for sym, s in scores_map.items():
            if isinstance(s, dict) and s.get("current_price"):
                prices[sym] = float(s["current_price"])
    except Exception:
        pass
    return prices


def _linked_transactions(db: Session, decision_id: int, known_symbols: list[str] | None = None) -> list[dict]:
    """Transactions linked to one decision, symbol-normalized against the
    decision's own plan symbols where possible.

    `Transaction.symbol` is live and mutable; the plan's target_allocation
    symbols are frozen at recommendation time (docs/architecture/
    ASSET_REGISTRY.md §10; M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md §2.3
    item 1 — "the strongest concrete argument... for why asset_id beats
    symbol"). A post-hoc spelling difference (e.g. plan says "BH", the fill
    is recorded as "BH.BK") must not silently read as "no linked
    transaction". When `known_symbols` (the plan's own symbols) is given,
    each transaction symbol that doesn't already match one exactly is
    resolved against them via registry_symbol_matching.match_known_symbols()
    — a genuine Registry match (or its legacy .BK fallback) rewrites the
    transaction's symbol to the plan's spelling; anything the Registry
    can't decide is left untouched, which is identical to today's behavior
    for the population of symbols the Registry hasn't resolved yet.
    """
    from models.database import Transaction

    rows = db.query(Transaction).filter_by(execution_decision_id=decision_id).all()
    txs = [
        {"symbol": t.symbol, "shares": t.shares, "price_per_share": t.price_per_share, "total_amount": t.total_amount}
        for t in rows
    ]

    if not known_symbols:
        return txs

    known_set = set(known_symbols)
    unmatched = [tx["symbol"] for tx in txs if tx["symbol"] and tx["symbol"] not in known_set]
    if not unmatched:
        return txs

    from services.registry_symbol_matching import match_known_symbols

    matches = match_known_symbols(db, symbols=unmatched, known=known_symbols)
    if not matches:
        return txs

    for tx in txs:
        mapped = matches.get(tx["symbol"])
        if mapped is not None:
            tx["symbol"] = mapped
    return txs


def _decision_analysis(db: Session, decision: Any, snap: Any) -> dict[str, Any]:
    from services.evaluation.execution_analyzer import compute_execution_analysis
    from services.evaluation.plan_grader import read_snapshot_plan_inputs

    inputs = read_snapshot_plan_inputs(db, snap)
    if inputs is None:
        return {"status": "unavailable", "reason": "no_target_allocations", "score": None}

    plan_symbols = [a.get("symbol") for a in (inputs["target_allocations"] or []) if a.get("symbol")]

    return compute_execution_analysis(
        inputs["target_allocations"], inputs["cash_available"], inputs["violations"],
        _recommendation_prices(snap), _linked_transactions(db, decision.id, known_symbols=plan_symbols),
    )


def list_execution_ledger(db: Session, portfolio_id: int, period_days: int = 90) -> dict[str, Any]:
    """Decision ledger + class-segmented acceptance summary (UX S4)."""
    from models.database import RecommendationGrade, UserExecutionDecision, Workspace
    from services.evaluation.plan_grader import derive_full_plan, read_snapshot_plan_inputs
    from services.optimizer.execution_optimizer import STATE_DEFERRED

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

    decision_counts: dict[str, int] = {}
    class_totals: dict[str, dict[str, int]] = {
        label: {"accepted": 0, "total": 0} for label in _REASON_LABELS.values()
    }
    scores: list[float] = []
    timing_deltas: list[float] = []
    funding_fidelities: list[float] = []
    rows: list[dict[str, Any]] = []

    for dec in decisions:
        decision_counts[dec.decision] = decision_counts.get(dec.decision, 0) + 1
        snap = dec.snapshot
        if snap is None:
            continue

        inputs = read_snapshot_plan_inputs(db, snap)
        if inputs is not None:
            plan = derive_full_plan(inputs["target_allocations"], inputs["cash_available"], inputs["violations"])
            accepted = dec.decision in _ACCEPTED_DECISIONS
            for t in plan["execution_optimization"].trades:
                if t.execution_state == STATE_DEFERRED:
                    continue  # never offered to the human as something to act on today
                label = _REASON_LABELS.get(t.reason)
                if not label:
                    continue
                class_totals[label]["total"] += 1
                if accepted:
                    class_totals[label]["accepted"] += 1

        analysis = _decision_analysis(db, dec, snap)
        if analysis.get("score") is not None:
            scores.append(analysis["score"])
        for sym_data in (analysis.get("symbols") or {}).values():
            if sym_data.get("timing_delta_pct") is not None:
                timing_deltas.append(sym_data["timing_delta_pct"])
        if analysis.get("funding_fidelity_pct") is not None:
            funding_fidelities.append(analysis["funding_fidelity_pct"])

        # Outcome delta: nearest mature horizon grade, marked counterfactual
        # when the decision wasn't actually followed.
        grade_row = (
            db.query(RecommendationGrade)
            .filter(
                RecommendationGrade.recommendation_snapshot_id == snap.id,
                RecommendationGrade.grade_kind.like("H%"),
            )
            .order_by(RecommendationGrade.window_end.desc())
            .first()
        )

        rows.append({
            "decision_id": dec.id,
            "snapshot_id": snap.id,
            "date": dec.executed_at.isoformat() + "Z" if dec.executed_at else None,
            "decision": dec.decision,
            "execution_status": analysis.get("status"),
            "execution_score": analysis.get("score"),
            "completeness_pct": analysis.get("completeness_pct"),
            "funding_fidelity_pct": analysis.get("funding_fidelity_pct"),
            "outcome_delta": {
                "grade_kind": grade_row.grade_kind,
                "return_pct": grade_row.return_pct,
                "alpha": grade_row.alpha,
                "is_counterfactual": dec.decision not in _ACCEPTED_DECISIONS,
            } if grade_row else None,
        })

    acceptance_by_class = {
        label: {
            "accepted": v["accepted"],
            "total": v["total"],
            "acceptance_pct": round(100.0 * v["accepted"] / v["total"], 2) if v["total"] else None,
        }
        for label, v in class_totals.items()
    }

    return {
        "portfolio_id": portfolio_id,
        "period_days": period_days,
        "as_of": datetime.utcnow().isoformat() + "Z",
        "status": "ok" if decisions else "cold_start",
        "summary": {
            "total_decisions": len(decisions),
            "decision_counts": decision_counts,
            "acceptance_by_class": acceptance_by_class,
            "acceptance_note": (
                "Segmented by the three Reasons execution_optimizer.py assigns to "
                "SELL/REDUCE candidates; acceptance is evaluated at the decision "
                "level (APPROVED/PARTIAL_EXECUTION), not per individual trade."
            ),
            "avg_execution_score": round(sum(scores) / len(scores), 2) if scores else None,
            "avg_timing_delta_pct": round(sum(timing_deltas) / len(timing_deltas), 2) if timing_deltas else None,
            "avg_funding_fidelity_pct": round(sum(funding_fidelities) / len(funding_fidelities), 2) if funding_fidelities else None,
        },
        "rows": rows,
    }


def get_execution_detail(db: Session, portfolio_id: int, decision_id: int) -> dict[str, Any] | None:
    """Plan-vs-actual detail for one decision (UX S4b).

    Returns None when the decision doesn't exist / doesn't belong to this
    portfolio — caller (main.py) turns that into a 404.
    """
    from models.database import UserExecutionDecision, Workspace

    ws_row = db.query(Workspace).order_by(Workspace.id).first()
    ws = ws_row.id if ws_row else 1

    dec = (
        db.query(UserExecutionDecision)
        .filter_by(id=decision_id, workspace_id=ws, portfolio_id=portfolio_id)
        .first()
    )
    if not dec or dec.snapshot is None:
        return None

    analysis = _decision_analysis(db, dec, dec.snapshot)

    partial_warning = None
    if analysis.get("status") == "partial" and (analysis.get("completeness_pct") or 100) < 100:
        n_missing = sum(
            1 for s in (analysis.get("symbols") or {}).values()
            if s.get("note") == "no_linked_transaction"
        )
        partial_warning = (
            f"Partial execution: {n_missing} planned trade(s) have no linked transaction — "
            "the portfolio that resulted was not the one designed."
        )

    return {
        "decision_id": dec.id,
        "snapshot_id": dec.recommendation_snapshot_id,
        "portfolio_id": portfolio_id,
        "decision": dec.decision,
        "executed_at": dec.executed_at.isoformat() + "Z" if dec.executed_at else None,
        "analysis": analysis,
        "partial_warning": partial_warning,
        "as_of": datetime.utcnow().isoformat() + "Z",
    }
