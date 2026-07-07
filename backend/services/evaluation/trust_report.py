"""trust_report.py — AI Evaluation M7: MUJI Trust Report (UX S9).

Read-only aggregation over already-computed M3/M5 data — computes zero new
grades, zero new return math (PLAN §4.6). It exists only to select which
already-computed numbers belong on a three-sentence MUJI card and hand them
to verdict_composer.compose_trust_report for phrasing:

    Belief clause    — same AI-vs-benchmark branch services.evaluation
                       .scorecard.compute_scorecard already computes
                       (belief.avg_alpha_pct / belief.status).
    Compliance count — "followed N of M recommendations", read from
                       services.evaluation.execution_ledger
                       .list_execution_ledger's summary.decision_counts (the
                       same APPROVED/PARTIAL_EXECUTION acceptance definition
                       the Execution ledger (S4) already uses — never a
                       second definition of "followed").
    Gap B clause     — outcome.regret_score / win_rate.n from the same
                       scorecard call (identical figure the Scorecard (S1)
                       verdict strip reads).
    One insight      — the strongest sample-backed trade-class observation
                       from services.analytics.human_vs_ai.compute_scoreboard
                       's by_trade_class breakdown (Human vs AI, S5) — a
                       trade class where the human's own deviations beat the
                       AI more often than not, on at least 2 graded
                       decisions. Below that bar, no insight sentence is
                       shown (never a padded or fabricated one).

Public API
----------
compute_trust_report(db, portfolio_id, period_days=90) -> dict
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

_MIN_INSIGHT_N = 2


def _pick_insight(by_trade_class: dict[str, dict[str, int]]) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    best_ratio = 0.5  # strictly more often right than wrong, and better than nothing found yet
    for label, v in (by_trade_class or {}).items():
        total = v.get("total", 0)
        if total < _MIN_INSIGHT_N:
            continue
        ratio = v.get("human_better", 0) / total
        if ratio > best_ratio:
            best_ratio = ratio
            best = {"label": label, "human_better": v.get("human_better", 0), "total": total}
    return best


def compute_trust_report(db: Session, portfolio_id: int, period_days: int = 90) -> dict[str, Any]:
    """MUJI Trust Report aggregate for one portfolio (UX S9).

    Cold start (no RecommendationSnapshot ever) returns status="cold_start"
    with a single first-run sentence — never zeros, never an error, matching
    the Scorecard's own Rung 0 convention.
    """
    from main import _get_evaluation_settings
    from models.database import RecommendationSnapshot, Workspace
    from services.evaluation.scorecard import compute_scorecard
    from services.evaluation.execution_ledger import list_execution_ledger
    from services.evaluation.verdict_composer import compose_trust_report
    from services.analytics.human_vs_ai import compute_scoreboard

    ws_row = db.query(Workspace).order_by(Workspace.id).first()
    ws = ws_row.id if ws_row else 1
    settings = _get_evaluation_settings(db, ws)
    min_n_win_rate = int(settings.get("min_n_win_rate") or 5)
    tie_band_pct = float(settings.get("tie_band_pct") or 0.3)

    as_of = datetime.utcnow().isoformat() + "Z"

    has_any_snapshot = (
        db.query(RecommendationSnapshot.id)
        .filter_by(workspace_id=ws, portfolio_id=portfolio_id)
        .first()
        is not None
    )
    if not has_any_snapshot:
        return {
            "portfolio_id": portfolio_id,
            "period_days": period_days,
            "status": "cold_start",
            "as_of": as_of,
            "sentences": [{
                "en": "No recommendations yet — the trust report will start after the first optimizer run.",
                "th": "ยังไม่มีคำแนะนำ — รายงานความน่าเชื่อถือจะเริ่มแสดงหลังจากมีคำแนะนำครั้งแรก",
            }],
            "link": "/ai-analytics",
        }

    scorecard = compute_scorecard(db, portfolio_id, period_days)
    ledger = list_execution_ledger(db, portfolio_id, period_days)
    scoreboard = compute_scoreboard(db, portfolio_id, period_days)

    ledger_summary = ledger.get("summary") or {}
    decision_counts: dict[str, int] = ledger_summary.get("decision_counts") or {}
    followed = decision_counts.get("APPROVED", 0) + decision_counts.get("PARTIAL_EXECUTION", 0)
    total_decisions = ledger_summary.get("total_decisions", sum(decision_counts.values()))

    belief = scorecard.get("belief") or {}
    outcome = scorecard.get("outcome") or {}
    win_rate = outcome.get("win_rate") or {}
    insight = _pick_insight(scoreboard.get("by_trade_class") or {})

    composed = compose_trust_report(
        period_days=period_days,
        belief_avg_alpha=belief.get("avg_alpha_pct"),
        belief_status=belief.get("status", "cold_start"),
        gap_b=outcome.get("regret_score"),
        gap_b_n=win_rate.get("n", 0),
        min_n_win_rate=min_n_win_rate,
        tie_band_pct=tie_band_pct,
        followed_count=followed,
        total_decisions=total_decisions,
        insight=insight,
    )

    top_status = "ok" if scorecard.get("status") == "ok" else "partial"

    return {
        "portfolio_id": portfolio_id,
        "period_days": period_days,
        "status": top_status,
        "as_of": as_of,
        "sentences": composed["sentences"],
        "link": "/ai-analytics",
    }
