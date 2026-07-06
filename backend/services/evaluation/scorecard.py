"""scorecard.py — AI Evaluation M3: three-lens aggregation for GET
/analytics/evaluation/scorecard.

Aggregates Belief / Execution / Outcome (OPTIMIZER_PHILOSOPHY.md §12) from
data M1/M2 already persisted, plus two already-existing analytics services —
this module computes zero new grades and re-derives zero return formulas
(PLAN §4.6):

    Belief Quality    — RecommendationGrade rows with grade_kind starting
                        "H" (horizon grades, M1): hit rate (share with
                        directional_correct=True), average alpha, letter
                        grade. Confidence Calibration is read from the
                        latest ConfidenceCalibrationRecord for this
                        portfolio's snapshots (services/decision_memory/
                        calibration.py already owns that computation).
    Execution Quality — RecommendationGrade rows with grade_kind="PLAN"
                        (M2): average plan score, and the necessity/
                        funding_efficiency sub-scores already stored in
                        each row's detail_json. Implementation Shortfall
                        (Gap A, ideal-vs-AI-Portfolio) needs the ideal
                        return series, which is services/evaluation/
                        ideal_series.py — explicitly scoped to M6 by
                        docs/AI_EVALUATION_IMPLEMENTATION_PLAN.md §5. Ships
                        here as an honest "unavailable" field rather than a
                        fabricated number (PLAN §4.7).
    Outcome Quality   — services.analytics.attribution_engine
                        .compute_portfolio_attribution() (existing, already
                        used by /analytics/attribution-summary) for actual
                        vs AI-Portfolio (ACTIVE_MODEL shadow) returns and
                        drawdowns; services.analytics.human_vs_ai
                        .compare_human_vs_ai() (existing) for the win-rate
                        figure. Net Opportunity Cost is explicitly "a
                        placeholder until M5" per the implementation plan's
                        own M3 section — ships unavailable, not zero.
                        The benchmark ("SET") figure is read directly off
                        the most recent ShadowPortfolioSnapshot's own
                        already-computed benchmark_return_pct column
                        (shadow_tracker.py owns that computation) rather
                        than fetching or re-deriving prices here.

Min-n gating (P7, UX D10) is applied server-side via
verdict_composer.letter_grade() for the Belief/Execution letter chips, and
directly against evaluation_settings.min_n_win_rate for the Outcome win
rate — never left to the frontend to hide/show (§4.5 Single Source of
Truth: the frontend never recomputes evidence sufficiency).

Zero writes from this module (compute_portfolio_attribution's own upsert
into AttributionMetric is pre-existing behavior of that already-accepted
analytics function — unchanged, not new, here). Zero AI calls.

Public API
----------
compute_scorecard(db, portfolio_id, period_days=90) -> dict
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from services.evaluation.verdict_composer import compose_scorecard_verdict, letter_grade

logger = logging.getLogger(__name__)


def _belief_lens(db: Session, ws: int, portfolio_id: int, cutoff: str, min_n: int) -> dict[str, Any]:
    from models.database import RecommendationGrade

    rows = (
        db.query(RecommendationGrade)
        .filter(
            RecommendationGrade.workspace_id == ws,
            RecommendationGrade.portfolio_id == portfolio_id,
            RecommendationGrade.grade_kind.like("H%"),
            RecommendationGrade.window_end >= cutoff,
        )
        .all()
    )

    alphas = [r.alpha for r in rows if r.alpha is not None]
    directional = [r.directional_correct for r in rows if r.directional_correct is not None]

    n_graded = len(rows)
    avg_alpha = round(sum(alphas) / len(alphas), 4) if alphas else None
    hit_rate = round(100.0 * sum(1 for d in directional if d) / len(directional), 2) if directional else None

    calibration = _calibration_join(db, ws, portfolio_id)

    status = "ok" if rows else "cold_start"
    # Hit rate is itself a 0-100 scale — used directly as the belief composite
    # for letter-grading purposes (documented implementation choice; no
    # existing "belief score" formula to re-derive).
    grade = letter_grade(hit_rate, len(directional), min_n)

    return {
        "status": status,
        "n_graded": n_graded,
        "hit_rate_pct": hit_rate,
        "avg_alpha_pct": avg_alpha,
        "calibration": calibration,
        "grade": grade,
    }


def _calibration_join(db: Session, ws: int, portfolio_id: int) -> dict[str, Any]:
    """Latest ConfidenceCalibrationRecord for this portfolio's snapshots.

    Read-only join, mirrors the existing GET /analytics/calibration-history
    portfolio filter (main.py) — never recomputes calibration.
    """
    from models.database import ConfidenceCalibrationRecord, RecommendationSnapshot

    snapshot_ids = [
        r[0]
        for r in db.query(RecommendationSnapshot.id)
        .filter_by(workspace_id=ws, portfolio_id=portfolio_id)
        .all()
    ]
    if not snapshot_ids:
        return {"status": "unavailable", "calibration_score": None, "consensus_strength_calibration": None, "computed_at": None}

    row = (
        db.query(ConfidenceCalibrationRecord)
        .filter(
            ConfidenceCalibrationRecord.workspace_id == ws,
            ConfidenceCalibrationRecord.recommendation_snapshot_id.in_(snapshot_ids),
        )
        .order_by(ConfidenceCalibrationRecord.computed_at.desc())
        .first()
    )
    if not row or row.calibration_score is None:
        return {"status": "unavailable", "calibration_score": None, "consensus_strength_calibration": None, "computed_at": None}

    return {
        "status": "ok",
        "calibration_score": row.calibration_score,
        "consensus_strength_calibration": row.consensus_strength_calibration,
        "computed_at": row.computed_at.isoformat() + "Z" if row.computed_at else None,
    }


def _execution_lens(db: Session, ws: int, portfolio_id: int, cutoff_dt: datetime, min_n: int) -> dict[str, Any]:
    from models.database import RecommendationGrade

    rows = (
        db.query(RecommendationGrade)
        .filter(
            RecommendationGrade.workspace_id == ws,
            RecommendationGrade.portfolio_id == portfolio_id,
            RecommendationGrade.grade_kind == "PLAN",
            RecommendationGrade.graded_at >= cutoff_dt,
        )
        .all()
    )

    scores = [r.score for r in rows if r.score is not None]
    necessity: list[float] = []
    funding_eff: list[float] = []
    for r in rows:
        if not r.detail_json:
            continue
        try:
            detail = json.loads(r.detail_json)
        except Exception:
            continue
        if detail.get("necessity_score") is not None:
            necessity.append(detail["necessity_score"])
        if detail.get("funding_efficiency_score") is not None:
            funding_eff.append(detail["funding_efficiency_score"])

    avg_score = round(sum(scores) / len(scores), 2) if scores else None
    avg_necessity = round(sum(necessity) / len(necessity), 2) if necessity else None
    avg_funding_eff = round(sum(funding_eff) / len(funding_eff), 2) if funding_eff else None

    status = "ok" if rows else "cold_start"
    grade = letter_grade(avg_score, len(scores), min_n)

    return {
        "status": status,
        "n_plans": len(rows),
        "avg_plan_score": avg_score,
        "avg_necessity_pct": avg_necessity,
        "avg_funding_efficiency_pct": avg_funding_eff,
        "implementation_shortfall": {
            "status": "unavailable",
            "reason": "ideal_series_not_yet_implemented_pending_M6",
        },
        "grade": grade,
    }


def _outcome_lens(db: Session, ws: int, portfolio_id: int, period_days: int, min_n_win_rate: int) -> dict[str, Any]:
    from services.analytics.attribution_engine import compute_portfolio_attribution
    from services.analytics.human_vs_ai import compare_human_vs_ai
    from models.database import ShadowPortfolio, ShadowPortfolioSnapshot

    attribution = compute_portfolio_attribution(db, portfolio_id, period_days)
    hva = compare_human_vs_ai(db, portfolio_id, period_days)

    benchmark_return_pct = None
    active_shadow = (
        db.query(ShadowPortfolio)
        .filter_by(portfolio_id=portfolio_id, shadow_type="ACTIVE_MODEL", is_active=True)
        .order_by(ShadowPortfolio.created_at.desc())
        .first()
    )
    if active_shadow:
        latest_sps = (
            db.query(ShadowPortfolioSnapshot)
            .filter_by(shadow_portfolio_id=active_shadow.id)
            .order_by(ShadowPortfolioSnapshot.snapshot_date.desc())
            .first()
        )
        if latest_sps:
            benchmark_return_pct = latest_sps.benchmark_return_pct

    win_rate_n = hva.get("summary", {}).get("decisions_with_data", 0)
    win_rate_status = "ok" if win_rate_n >= min_n_win_rate else "insufficient_evidence"

    return {
        "status": attribution.get("status", "unavailable"),
        "actual_return_pct": attribution.get("actual", {}).get("return_pct"),
        "ai_model_return_pct": (attribution.get("ai_model_shadow") or {}).get("return_pct"),
        "ideal_return_pct": {"status": "unavailable", "reason": "ideal_series_not_yet_implemented_pending_M6"},
        "benchmark_return_pct": benchmark_return_pct,
        "win_rate": {
            "status": win_rate_status,
            "n": win_rate_n,
            "hit_rate_pct": hva.get("summary", {}).get("hit_rate_pct"),
            "ai_wins": hva.get("summary", {}).get("ai_wins"),
            "human_wins": hva.get("summary", {}).get("human_wins"),
        },
        "net_opportunity_cost": {"status": "unavailable", "reason": "opportunity_cost_pending_M5"},
        "max_drawdown_pct": {
            "actual": attribution.get("actual", {}).get("max_drawdown_pct"),
            "ai_model": (attribution.get("ai_model_shadow") or {}).get("max_drawdown_pct"),
            "ideal": None,
        },
        "regret_score": attribution.get("regret_score"),
    }


def _recent_grades(db: Session, ws: int, portfolio_id: int, limit: int = 10) -> list[dict[str, Any]]:
    from models.database import RecommendationGrade

    rows = (
        db.query(RecommendationGrade)
        .filter(RecommendationGrade.workspace_id == ws, RecommendationGrade.portfolio_id == portfolio_id)
        .order_by(RecommendationGrade.graded_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "recommendation_snapshot_id": r.recommendation_snapshot_id,
            "grade_kind": r.grade_kind,
            "graded_at": r.graded_at.isoformat() + "Z" if r.graded_at else None,
            "score": r.score,
            "return_pct": r.return_pct,
            "benchmark_return_pct": r.benchmark_return_pct,
            "alpha": r.alpha,
        }
        for r in rows
    ]


def compute_scorecard(db: Session, portfolio_id: int, period_days: int = 90) -> dict[str, Any]:
    """Three-lens scorecard aggregate for one portfolio.

    Cold start (no RecommendationSnapshot ever) returns status="cold_start"
    with structured empty lenses — never zeros, never an error (UX §7 Rung 0).
    """
    from main import _get_evaluation_settings
    from models.database import RecommendationSnapshot, Workspace

    ws_row = db.query(Workspace).order_by(Workspace.id).first()
    ws = ws_row.id if ws_row else 1
    settings = _get_evaluation_settings(db, ws)
    min_n_letter = int(settings.get("min_n_letter_grade") or 8)
    min_n_win_rate = int(settings.get("min_n_win_rate") or 5)
    tie_band_pct = float(settings.get("tie_band_pct") or 0.3)

    has_any_snapshot = (
        db.query(RecommendationSnapshot.id)
        .filter_by(workspace_id=ws, portfolio_id=portfolio_id)
        .first()
        is not None
    )

    as_of = datetime.utcnow().isoformat() + "Z"

    if not has_any_snapshot:
        empty_lens = {"status": "cold_start"}
        return {
            "portfolio_id": portfolio_id,
            "period_days": period_days,
            "status": "cold_start",
            "as_of": as_of,
            "belief": {**empty_lens, "n_graded": 0, "hit_rate_pct": None, "avg_alpha_pct": None,
                       "calibration": {"status": "unavailable", "calibration_score": None, "consensus_strength_calibration": None, "computed_at": None},
                       "grade": {"status": "unavailable", "letter": None, "n": 0}},
            "execution": {**empty_lens, "n_plans": 0, "avg_plan_score": None, "avg_necessity_pct": None,
                          "avg_funding_efficiency_pct": None,
                          "implementation_shortfall": {"status": "unavailable", "reason": "ideal_series_not_yet_implemented_pending_M6"},
                          "grade": {"status": "unavailable", "letter": None, "n": 0}},
            "outcome": {**empty_lens, "actual_return_pct": None, "ai_model_return_pct": None,
                        "ideal_return_pct": {"status": "unavailable", "reason": "ideal_series_not_yet_implemented_pending_M6"},
                        "benchmark_return_pct": None,
                        "win_rate": {"status": "insufficient_evidence", "n": 0, "hit_rate_pct": None, "ai_wins": 0, "human_wins": 0},
                        "net_opportunity_cost": {"status": "unavailable", "reason": "opportunity_cost_pending_M5"},
                        "max_drawdown_pct": {"actual": None, "ai_model": None, "ideal": None},
                        "regret_score": None},
            "verdict": {
                "en": "No optimizer runs yet — the scorecard will populate after the first recommendation.",
                "th": "ยังไม่มีการรันคำแนะนำ — สรุปผลงานจะเริ่มแสดงหลังจากมีคำแนะนำครั้งแรก",
                "branch": "insufficient_evidence",
            },
            "recent_grades": [],
        }

    cutoff_date = (date.today() - timedelta(days=period_days)).isoformat()
    cutoff_dt = datetime.utcnow() - timedelta(days=period_days)

    belief = _belief_lens(db, ws, portfolio_id, cutoff_date, min_n_letter)
    execution = _execution_lens(db, ws, portfolio_id, cutoff_dt, min_n_letter)
    outcome = _outcome_lens(db, ws, portfolio_id, period_days, min_n_win_rate)

    verdict = compose_scorecard_verdict(
        period_days=period_days,
        belief_avg_alpha=belief["avg_alpha_pct"],
        belief_status=belief["status"],
        gap_b=outcome["regret_score"],
        gap_b_n=outcome["win_rate"]["n"],
        min_n_win_rate=min_n_win_rate,
        tie_band_pct=tie_band_pct,
    )

    lens_statuses = {belief["status"], execution["status"], outcome["status"]}
    if lens_statuses <= {"ok"}:
        top_status = "ok"
    elif lens_statuses & {"ok"}:
        top_status = "partial"
    else:
        top_status = "cold_start" if lens_statuses <= {"cold_start"} else "partial"

    return {
        "portfolio_id": portfolio_id,
        "period_days": period_days,
        "status": top_status,
        "as_of": as_of,
        "belief": belief,
        "execution": execution,
        "outcome": outcome,
        "verdict": verdict,
        "recent_grades": _recent_grades(db, ws, portfolio_id),
    }
