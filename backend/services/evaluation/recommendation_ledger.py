"""recommendation_ledger.py — AI Evaluation M3: Recommendations ledger (S2)
and per-recommendation Report Card (S3).

Both read-only aggregations over data M0/M1/M2 already persisted — no new
grading logic. Reuses:
  - services.evaluation.plan_grader.read_snapshot_plan_inputs /
    derive_full_plan for "what does this snapshot's plan say" (single
    reconstruction, shared with execution_ledger.py).
  - services.optimizer_action_summary.build_action_summary for trade counts.
  - RecommendationGrade rows (PLAN + H7/H30/H90/H180, M1/M2) for every
    graded figure — never re-derived.
  - services.evaluation.verdict_composer for the Report Card's verdict
    sentence.

Horizon-strip semantics (UX S2/S3 HorizonStrip component), documented once
here since the UX wireframe's own legend is ambiguous about the maturing/
not-due boundary:
  "graded"          — a RecommendationGrade row exists for that grade_kind.
  "maturing"        — age_days < horizon_days; carries due_date computed
                       from snapshot.created_at + horizon_days.
  "pending_grading" — age_days >= horizon_days but no grade row yet
                       (the scheduler hasn't caught up) — an honest,
                       observable transient state (PLAN §4.7), never
                       collapsed into "maturing".

A ledger row's grades are marked is_counterfactual=True whenever the
recorded decision is anything other than APPROVED/PARTIAL_EXECUTION — the
recommendation-keyed shadow (P2) always exists regardless of what the human
did, so REJECTED/EXPIRED/MANUAL_OVERRIDE rows show a real number that was
never realized money (PLAN §4.8; UX D7).

Public API
----------
list_recommendations_ledger(db, portfolio_id, limit=50, offset=0) -> dict
get_report_card(db, portfolio_id, snapshot_id) -> dict | None
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_ACCEPTED_DECISIONS = ("APPROVED", "PARTIAL_EXECUTION")


def _horizon_days(db: Session, ws: int) -> list[int]:
    from main import _get_evaluation_settings

    settings = _get_evaluation_settings(db, ws)
    return sorted(settings.get("horizons_days") or [7, 30, 90, 180])


def _trade_count(target_allocations: list[dict] | None) -> int:
    from services.optimizer_action_summary import build_action_summary

    summary = build_action_summary(target_allocations or [])
    return sum(len(summary.get(k, [])) for k in ("sell", "reduce", "accumulate", "new_position"))


def _horizon_strip(
    db: Session, snap: Any, horizons: list[int], today: date,
) -> dict[str, dict[str, Any]]:
    from models.database import RecommendationGrade

    grade_rows = {
        r.grade_kind: r
        for r in db.query(RecommendationGrade)
        .filter_by(recommendation_snapshot_id=snap.id)
        .all()
        if r.grade_kind.startswith("H")
    }

    snap_date = snap.created_at.date() if snap.created_at else today
    age_days = (today - snap_date).days

    strip: dict[str, dict[str, Any]] = {}
    for h in horizons:
        kind = f"H{h}"
        row = grade_rows.get(kind)
        if row:
            strip[kind] = {
                "status": "graded",
                "return_pct": row.return_pct,
                "benchmark_return_pct": row.benchmark_return_pct,
                "alpha": row.alpha,
                "directional_correct": row.directional_correct,
                "graded_at": row.graded_at.isoformat() + "Z" if row.graded_at else None,
            }
        elif age_days < h:
            strip[kind] = {
                "status": "maturing",
                "due_date": (snap_date + timedelta(days=h)).isoformat(),
                "days_remaining": h - age_days,
            }
        else:
            strip[kind] = {"status": "pending_grading"}
    return strip


def list_recommendations_ledger(
    db: Session, portfolio_id: int, limit: int = 50, offset: int = 0,
) -> dict[str, Any]:
    """Every recommendation snapshot for a portfolio, newest first (UX S2)."""
    from models.database import RecommendationSnapshot, UserExecutionDecision, Workspace

    ws_row = db.query(Workspace).order_by(Workspace.id).first()
    ws = ws_row.id if ws_row else 1
    horizons = _horizon_days(db, ws)
    today = date.today()

    total = (
        db.query(RecommendationSnapshot.id)
        .filter_by(workspace_id=ws, portfolio_id=portfolio_id)
        .count()
    )
    snaps = (
        db.query(RecommendationSnapshot)
        .filter_by(workspace_id=ws, portfolio_id=portfolio_id)
        .order_by(RecommendationSnapshot.created_at.desc())
        .offset(offset)
        .limit(min(limit, 100))
        .all()
    )

    rows: list[dict[str, Any]] = []
    for snap in snaps:
        decision_row = (
            db.query(UserExecutionDecision)
            .filter_by(recommendation_snapshot_id=snap.id)
            .order_by(UserExecutionDecision.executed_at.desc())
            .first()
        )
        decision_type = decision_row.decision if decision_row else None
        is_counterfactual = decision_type not in _ACCEPTED_DECISIONS

        consensus_type = None
        if snap.consensus_json:
            try:
                consensus_type = json.loads(snap.consensus_json).get("consensus_type")
            except Exception:
                consensus_type = None

        target_allocations = None
        if snap.projected_allocations_json:
            try:
                target_allocations = json.loads(snap.projected_allocations_json)
            except Exception:
                target_allocations = None

        strip = _horizon_strip(db, snap, horizons, today)
        # Headline alpha = the most-mature graded horizon available.
        headline_alpha = None
        for h in sorted(horizons, reverse=True):
            cell = strip.get(f"H{h}", {})
            if cell.get("status") == "graded":
                headline_alpha = cell.get("alpha")
                break

        rows.append({
            "snapshot_id": snap.id,
            "date": snap.created_at.isoformat() + "Z" if snap.created_at else None,
            "consensus_type": consensus_type,
            "trade_count": _trade_count(target_allocations),
            "decision": decision_type,
            "is_system_generated": bool(decision_row.is_system_generated) if decision_row else False,
            "is_counterfactual": is_counterfactual,
            "horizon_strip": strip,
            "headline_alpha": headline_alpha,
        })

    return {
        "portfolio_id": portfolio_id,
        "total": total,
        "limit": limit,
        "offset": offset,
        "as_of": datetime.utcnow().isoformat() + "Z",
        "status": "ok" if rows else "cold_start",
        "rows": rows,
    }


def get_report_card(db: Session, portfolio_id: int, snapshot_id: int) -> dict[str, Any] | None:
    """Single-recommendation Report Card (UX S3): plan -> execution -> outcome.

    Returns None when the snapshot doesn't exist / doesn't belong to this
    portfolio — the caller (main.py) turns that into a 404.
    """
    from models.database import (
        RecommendationGrade, RecommendationSnapshot, UserExecutionDecision, Workspace,
    )
    from services.evaluation.plan_grader import derive_full_plan, read_snapshot_plan_inputs
    from services.evaluation.verdict_composer import compose_report_card_verdict

    ws_row = db.query(Workspace).order_by(Workspace.id).first()
    ws = ws_row.id if ws_row else 1

    snap = (
        db.query(RecommendationSnapshot)
        .filter_by(id=snapshot_id, workspace_id=ws, portfolio_id=portfolio_id)
        .first()
    )
    if not snap:
        return None

    regime = {}
    if snap.regime_snapshot_json:
        try:
            regime = json.loads(snap.regime_snapshot_json)
        except Exception:
            regime = {}
    consensus = {}
    if snap.consensus_json:
        try:
            consensus = json.loads(snap.consensus_json)
        except Exception:
            consensus = {}

    inputs = read_snapshot_plan_inputs(db, snap)

    plan_grade_row = (
        db.query(RecommendationGrade)
        .filter_by(recommendation_snapshot_id=snap.id, grade_kind="PLAN")
        .first()
    )

    plan_section: dict[str, Any]
    if inputs is None:
        plan_section = {"status": "unavailable", "reason": "no_target_allocations"}
    else:
        plan = derive_full_plan(inputs["target_allocations"], inputs["cash_available"], inputs["violations"])
        eo = plan["execution_optimization"]
        plan_section = {
            "status": "ok",
            "buy_trades": plan["buy_trades"],
            "sell_reduce_trades": [t.model_dump() for t in eo.trades],
            "cash_available": eo.cash_available,
            "funding_gap": eo.funding_gap,
            "grade": {
                "score": plan_grade_row.score if plan_grade_row else None,
                "detail": json.loads(plan_grade_row.detail_json) if plan_grade_row and plan_grade_row.detail_json else None,
            },
            "portfolio_assessment": inputs["portfolio_assessment"],
            "no_action_summary": inputs["no_action_summary"],
        }

    decision_row = (
        db.query(UserExecutionDecision)
        .filter_by(recommendation_snapshot_id=snap.id)
        .order_by(UserExecutionDecision.executed_at.desc())
        .first()
    )

    execution_section: dict[str, Any] = {"status": "no_decision_recorded"}
    if decision_row and inputs is not None:
        from models.database import Transaction
        from services.evaluation.execution_analyzer import compute_execution_analysis

        recommendation_prices: dict[str, float] = {}
        if snap.scores_map_json:
            try:
                scores_map = json.loads(snap.scores_map_json)
                for sym, s in scores_map.items():
                    if isinstance(s, dict) and s.get("current_price"):
                        recommendation_prices[sym] = float(s["current_price"])
            except Exception:
                pass

        tx_rows = (
            db.query(Transaction)
            .filter_by(execution_decision_id=decision_row.id)
            .all()
        )
        linked_transactions = [
            {"symbol": t.symbol, "shares": t.shares, "price_per_share": t.price_per_share, "total_amount": t.total_amount}
            for t in tx_rows
        ]

        analysis = compute_execution_analysis(
            inputs["target_allocations"], inputs["cash_available"], inputs["violations"],
            recommendation_prices, linked_transactions,
        )
        execution_section = {
            "status": "ok",
            "decision_id": decision_row.id,
            "decision": decision_row.decision,
            "executed_at": decision_row.executed_at.isoformat() + "Z" if decision_row.executed_at else None,
            "analysis": analysis,
        }

    horizons = _horizon_days(db, ws)
    strip = _horizon_strip(db, snap, horizons, date.today())

    # Most-mature graded horizon drives the verdict sentence.
    mature_kind = None
    mature_cell = None
    for h in sorted(horizons, reverse=True):
        cell = strip.get(f"H{h}", {})
        if cell.get("status") == "graded":
            mature_kind, mature_cell = f"H{h}", cell
            break

    verdict = compose_report_card_verdict(
        plan_score=plan_grade_row.score if plan_grade_row else None,
        horizon_grade_kind=mature_kind,
        return_pct=mature_cell.get("return_pct") if mature_cell else None,
        benchmark_return_pct=mature_cell.get("benchmark_return_pct") if mature_cell else None,
        alpha=mature_cell.get("alpha") if mature_cell else None,
        directional_correct=mature_cell.get("directional_correct") if mature_cell else None,
    )

    return {
        "snapshot_id": snap.id,
        "portfolio_id": portfolio_id,
        "date": snap.created_at.isoformat() + "Z" if snap.created_at else None,
        "persona": snap.persona,
        "regime": regime.get("regime"),
        "consensus_type": consensus.get("consensus_type"),
        "confidence": consensus.get("consensus_strength_score"),
        "plan": plan_section,
        "decision": {
            "decision": decision_row.decision if decision_row else None,
            "is_system_generated": bool(decision_row.is_system_generated) if decision_row else None,
            "executed_at": decision_row.executed_at.isoformat() + "Z" if (decision_row and decision_row.executed_at) else None,
        } if decision_row else None,
        "execution": execution_section,
        "outcomes": strip,
        "verdict": verdict,
        "as_of": datetime.utcnow().isoformat() + "Z",
    }
