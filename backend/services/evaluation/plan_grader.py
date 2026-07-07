"""plan_grader.py — AI Evaluation M2: Day-0 Plan Grade.

Scores the *execution plan* the moment it exists — before any human decides
anything, before any trade fills — so a bad plan can be told apart from a
bad outcome (PLAN §4.6, OPTIMIZER_PHILOSOPHY.md §12). This is a Belief-free,
deterministic composite over data the pipeline already produced:

    necessity                 (weight 30) — share of candidate SELL/REDUCE
                               trades that are either Required-tier (Reason
                               = Mandatory Risk Reduction / Policy
                               Enforcement) or actively serving as a funding
                               source today. A plan padded with discretionary
                               trades that end up deferred scores lower here
                               — every trade on the plan should be doing a
                               job, per OPTIMIZER_PHILOSOPHY.md §8.
    funding_efficiency         (weight 30) — THE BH-INCIDENT METRIC. Of the
                               total amount discretionary (Portfolio
                               Improvement) candidates proposed to release,
                               what fraction was actually needed to close the
                               funding gap? A REDUCE proposing far more than
                               the gap requires scores near the floor even
                               though services/optimizer/execution_optimizer.py
                               already defers the unneeded portion — this
                               sub-score grades the RECOMMENDATION's own
                               proportionality, not just whether the
                               execution-optimization stage caught it.
    turnover_proportionality   (weight 20) — reads the already-computed
                               TURNOVER_BREACH violation_detail (if any) from
                               policy_engine.compute_policy_alignment_score;
                               100 when absent, decaying with the recorded
                               overshoot ratio when present. No turnover
                               math is re-derived here (PLAN §4.6).
    explanation_completeness   (weight 20) — every SELL/REDUCE candidate
                               execution_optimizer produced must carry a
                               non-empty reason/necessity/execution_role/
                               execution_state/note; a no-trade plan must
                               carry a portfolio_assessment or
                               no_action_summary. This is an invariant check
                               on an already-guaranteed property, not new
                               judgment.

This module re-derives the execution plan via `optimize_execution` on
STORED inputs (target_allocations, cash_balance, active_policy.violations —
all frozen at analysis time) rather than re-running any AI layer or
re-deriving execution_optimizer's own arithmetic — same inputs always
produce the same PLAN grade (PLAN §4.1, §4.6; Invariant 3).

Zero AI calls, zero DB writes to anything but `recommendation_grades`
(append-only, P3), zero mutation of `RecommendationSnapshot`/
`OptimizerHistory` (PLAN §4.1). See services/evaluation/__init__.py for the
full constraint list.

Public API
----------
read_snapshot_plan_inputs(db, snap) -> dict | None
    Thin ORM-boundary reader: reconstructs (target_allocations,
    violations, violation_details, cash_available, portfolio_assessment,
    no_action_summary) from a RecommendationSnapshot + its linked
    OptimizerHistory.result_json. Single place this reconstruction is
    written (ENGINEERING_PRINCIPLES Single Source of Truth) — reused by
    grade_pending_plans below and by services/evaluation/
    recommendation_ledger.py + execution_ledger.py (M3) so the Report
    Card / execution ledger never re-derive "what does this snapshot's
    plan look like" a second way. Returns None when
    projected_allocations_json is missing/unparseable (caller decides
    how to report the skip).
derive_full_plan(target_allocations, cash_available, violations=None) -> dict
    Shared "what does the day-0 plan actually say" derivation — buy-side
    trades plus the resolved SELL/REDUCE ExecutionOptimizationResult. Reused
    by services/evaluation/execution_analyzer.py so the notion of "the plan"
    is computed in exactly one place (PLAN §4.5).
compute_plan_grade(target_allocations, cash_available, violations, ...) -> dict
    Pure function: the 0-100 composite + documented sub-scores + weights.
grade_pending_plans(db, portfolio_id=None) -> dict
    {"graded": [...], "skipped": [...]} — writes grade_kind="PLAN" rows for
    every RecommendationSnapshot lacking one.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Composite weights (documented, sum to 100). See module docstring for what
# each sub-score measures and why it is weighted this way.
_WEIGHT_NECESSITY = 30.0
_WEIGHT_FUNDING_EFFICIENCY = 30.0
_WEIGHT_TURNOVER = 20.0
_WEIGHT_EXPLANATION = 20.0


def _derive_action_summary_and_buys(
    target_allocations: list[dict],
) -> tuple[dict, list[dict], float]:
    """BUY-side trades never pass through execution_optimizer (it only ever
    classifies SELL/REDUCE candidates — PLAN §5/§7) so the buy side of the
    plan is read directly off the already-computed action_summary buckets.
    """
    from services.optimizer_action_summary import build_action_summary

    action_summary = build_action_summary(target_allocations or [])
    by_symbol = {a.get("symbol"): a for a in (target_allocations or []) if a.get("symbol")}

    buy_trades: list[dict] = []
    total_buy_deployment = 0.0
    for group in ("accumulate", "new_position"):
        for entry in action_summary.get(group, []):
            alloc = by_symbol.get(entry.get("symbol"))
            if not alloc:
                continue
            amount = abs(float(alloc.get("estimated_amount") or 0.0))
            total_buy_deployment += amount
            buy_trades.append({
                "symbol": entry["symbol"],
                "action": alloc.get("action", "BUY"),
                "planned_amount": amount,
            })

    return action_summary, buy_trades, total_buy_deployment


def read_snapshot_plan_inputs(db: Session, snap: Any) -> dict[str, Any] | None:
    """Reconstruct the stored plan inputs for one RecommendationSnapshot.

    Reads target_allocations/active_policy directly off the snapshot
    (stored verbatim by snapshot_writer.py) and cash_balance/
    portfolio_assessment/no_action_summary off the linked
    OptimizerHistory.result_json (the snapshot itself has no cash_balance
    column). result_json is committed before main.py appends the
    action_summary/execution_optimization response-time views to the
    in-memory result dict (main.py:~2409 precedes :~2599/:2610) — so this
    read is stable and reproducible (PLAN §4.1).

    Returns None (never raises) when projected_allocations_json is
    missing or unparseable.
    """
    from models.database import OptimizerHistory

    if not snap.projected_allocations_json:
        return None
    try:
        target_allocations = json.loads(snap.projected_allocations_json)
    except Exception:
        return None

    active_policy: dict = {}
    if snap.active_policy_json:
        try:
            active_policy = json.loads(snap.active_policy_json)
        except Exception:
            active_policy = {}

    oh = (
        db.query(OptimizerHistory).filter_by(id=snap.optimizer_history_id).first()
        if snap.optimizer_history_id else None
    )
    cash_available = 0.0
    portfolio_assessment = None
    no_action_summary = None
    if oh and oh.result_json:
        try:
            stored = json.loads(oh.result_json)
            cash_available = float(stored.get("cash_balance") or 0.0)
            portfolio_assessment = stored.get("portfolio_assessment")
            no_action_summary = stored.get("no_action_summary")
        except Exception:
            pass

    return {
        "target_allocations": target_allocations,
        "violations": active_policy.get("violations") or [],
        "violation_details": active_policy.get("violation_details") or [],
        "cash_available": cash_available,
        "portfolio_assessment": portfolio_assessment,
        "no_action_summary": no_action_summary,
    }


def derive_full_plan(
    target_allocations: list[dict],
    cash_available: float,
    violations: list[str] | None = None,
) -> dict[str, Any]:
    """Re-derive the complete day-0 plan: buy-side trades + the resolved
    SELL/REDUCE ExecutionOptimizationResult. Single source of truth for
    "what the plan says," shared by compute_plan_grade (below) and
    services/evaluation/execution_analyzer.py's plan-vs-actual comparison.

    Delegates entirely to already-existing, already-tested pure functions
    (build_action_summary, optimize_execution) — adds zero new trade-
    selection or funding logic (Working Agreement #5: execution_optimizer.py
    is read-only this phase).
    """
    from services.optimizer.execution_optimizer import optimize_execution

    action_summary, buy_trades, total_buy_deployment = _derive_action_summary_and_buys(
        target_allocations
    )
    eo = optimize_execution(
        action_summary, target_allocations or [], cash_available, violations=violations
    )
    return {
        "buy_trades": buy_trades,
        "total_buy_deployment": total_buy_deployment,
        "execution_optimization": eo,
    }


def compute_plan_grade(
    target_allocations: list[dict],
    cash_available: float,
    violations: list[str] | None = None,
    violation_details: list[dict] | None = None,
    portfolio_assessment: str | None = None,
    no_action_summary: str | None = None,
) -> dict[str, Any]:
    """Pure function: the day-0 plan composite. No DB, no AI — fully
    reproducible from the four stored arguments (asserted in tests)."""
    from services.optimizer.execution_optimizer import (
        NECESSITY_DISCRETIONARY,
        ROLE_FUNDING_SOURCE,
        STATE_DEFERRED,
    )

    plan = derive_full_plan(target_allocations, cash_available, violations)
    eo = plan["execution_optimization"]
    trades = eo.trades

    # ── Necessity: share of candidates that are Required-tier or actively funding today ──
    if trades:
        necessary_or_funding = sum(
            1 for t in trades
            if t.necessity != NECESSITY_DISCRETIONARY or t.execution_role == ROLE_FUNDING_SOURCE
        )
        necessity_score = round(100.0 * necessary_or_funding / len(trades), 2)
    else:
        necessity_score = 100.0

    # ── Funding efficiency: the BH-incident metric ──
    discretionary = [t for t in trades if t.necessity == NECESSITY_DISCRETIONARY]
    total_discretionary_recommended = sum(t.full_recommended_amount for t in discretionary)
    if total_discretionary_recommended <= 0:
        funding_efficiency_score = 100.0
    else:
        excess = max(0.0, total_discretionary_recommended - eo.funding_gap)
        funding_efficiency_score = round(
            100.0 * (1 - excess / total_discretionary_recommended), 2
        )

    # ── Turnover proportionality: reuses the already-computed TURNOVER_BREACH detail ──
    turnover_viol = next(
        (v for v in (violation_details or []) if v.get("violation_type") == "TURNOVER_BREACH"),
        None,
    )
    if not turnover_viol:
        turnover_score = 100.0
    else:
        proposed = float(turnover_viol.get("proposed_pct") or 0.0)
        allowed = float(turnover_viol.get("allowed_pct") or 1.0) or 1.0
        overshoot_ratio = max(0.0, (proposed - allowed) / allowed)
        turnover_score = max(0.0, round(100.0 - overshoot_ratio * 100, 2))

    # ── Explanation completeness ──
    if trades:
        complete = sum(
            1 for t in trades
            if t.reason and t.necessity and t.execution_role and t.execution_state and t.note
        )
        explanation_score = round(100.0 * complete / len(trades), 2)
    else:
        explanation_score = 100.0 if (portfolio_assessment or no_action_summary) else 60.0

    composite = round(
        (
            necessity_score * _WEIGHT_NECESSITY
            + funding_efficiency_score * _WEIGHT_FUNDING_EFFICIENCY
            + turnover_score * _WEIGHT_TURNOVER
            + explanation_score * _WEIGHT_EXPLANATION
        )
        / 100.0,
        2,
    )

    deferred_count = sum(1 for t in trades if t.execution_state == STATE_DEFERRED)

    return {
        "score": composite,
        "necessity_score": necessity_score,
        "funding_efficiency_score": funding_efficiency_score,
        "turnover_proportionality_score": turnover_score,
        "explanation_completeness_score": explanation_score,
        "weights": {
            "necessity": _WEIGHT_NECESSITY,
            "funding_efficiency": _WEIGHT_FUNDING_EFFICIENCY,
            "turnover_proportionality": _WEIGHT_TURNOVER,
            "explanation_completeness": _WEIGHT_EXPLANATION,
        },
        "trade_count": len(trades),
        "deferred_count": deferred_count,
        "funding_gap": eo.funding_gap,
        "cash_available": eo.cash_available,
    }


def grade_pending_plans(db: Session, portfolio_id: int | None = None) -> dict[str, Any]:
    """Write grade_kind="PLAN" rows for every RecommendationSnapshot lacking one.

    Reads target_allocations/active_policy directly off RecommendationSnapshot
    (already stored there verbatim by snapshot_writer.py) and cash_balance /
    portfolio_assessment / no_action_summary from the linked OptimizerHistory
    .result_json (RecommendationSnapshot has no cash_balance column of its
    own). result_json is committed before main.py appends the action_summary
    /execution_optimization response-time views to the in-memory result dict
    (verified main.py:2409 precedes :2599/:2610) — so this read is stable and
    reproducible, never racing a later mutation (PLAN §4.1).

    Missing data => skip with a logged reason, same convention as
    horizon_grader.grade_due_recommendations; never raises per-snapshot.
    """
    from models.database import RecommendationGrade, RecommendationSnapshot, Workspace

    graded: list[dict] = []
    skipped: list[dict] = []

    for ws in db.query(Workspace).all():
        q = db.query(RecommendationSnapshot).filter(RecommendationSnapshot.workspace_id == ws.id)
        if portfolio_id is not None:
            q = q.filter(RecommendationSnapshot.portfolio_id == portfolio_id)

        for snap in q.all():
            already = (
                db.query(RecommendationGrade)
                .filter_by(recommendation_snapshot_id=snap.id, grade_kind="PLAN")
                .first()
            )
            if already:
                continue

            inputs = read_snapshot_plan_inputs(db, snap)
            if inputs is None:
                reason = "no_target_allocations" if not snap.projected_allocations_json else "unparseable_allocations"
                skipped.append({"snapshot_id": snap.id, "reason": reason})
                continue

            result = compute_plan_grade(
                inputs["target_allocations"], inputs["cash_available"],
                inputs["violations"], inputs["violation_details"],
                portfolio_assessment=inputs["portfolio_assessment"],
                no_action_summary=inputs["no_action_summary"],
            )

            grade = RecommendationGrade(
                workspace_id=ws.id,
                recommendation_snapshot_id=snap.id,
                portfolio_id=snap.portfolio_id,
                grade_kind="PLAN",
                graded_at=datetime.utcnow(),
                window_start=None,
                window_end=None,
                score=result["score"],
                detail_json=json.dumps(result, default=str),
                created_at=datetime.utcnow(),
            )
            try:
                db.add(grade)
                db.commit()
            except Exception as exc:
                db.rollback()
                logger.warning("[EVAL] PLAN grade write failed snapshot_id=%s: %s", snap.id, exc)
                skipped.append({"snapshot_id": snap.id, "reason": "write_failed"})
                continue

            graded.append({"snapshot_id": snap.id, "score": result["score"]})
            logger.info("[EVAL] Graded PLAN snapshot_id=%s score=%s", snap.id, result["score"])

    return {"graded": graded, "skipped": skipped}
