"""horizon_grader.py — AI Evaluation M1: Horizon Grading Engine.

Grades recommendation quality at configured maturity horizons (default
7/30/90/180 days) by reading the recommendation-keyed STATIC_FROZEN shadow's
already-persisted daily valuation series (services/decision_memory/shadow_tracker.py,
P2) — this module performs zero independent price fetching and re-derives no
return/alpha/drawdown formula (PLAN §4.6): return_pct, benchmark_return_pct
and alpha come directly from the ShadowPortfolioSnapshot row nearest the
horizon date, and max_drawdown_pct reuses
services.analytics.attribution_engine.compute_max_drawdown.

Constraints (PLAN §4 — see services/evaluation/__init__.py for the full list):
  - Read-only upstream. Writes only new RecommendationGrade rows and, on the
    final configured horizon, flips ShadowPortfolio.is_active to False.
  - Append-only grades (P3): a (recommendation_snapshot_id, grade_kind) pair
    is graded at most once; re-running is always a no-op for that pair.
  - Zero AI calls (P6): every field here is arithmetic over persisted data.
  - Missing data => skip with a logged reason (§4.7); never raise, never guess.

Public API
----------
grade_due_recommendations(db, portfolio_id=None) -> dict
    {"graded": [...], "skipped": [...], "deactivated": [...]}
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_HORIZON_PREFIX = "H"
# Horizon dates rarely land exactly on a trading day (weekends/holidays); the
# nearest prior valuation is used instead. A gap wider than this is treated as
# "the shadow has fallen behind" rather than "this is the horizon value" —
# skip and let the next scheduler run catch up once valuation resumes.
_MAX_VALUATION_GAP_DAYS = 5


def _horizon_grade_kind(days: int) -> str:
    return f"{_HORIZON_PREFIX}{days}"


def _sps_at_or_before(db: Session, shadow_id: int, target_date: str):
    """Nearest ShadowPortfolioSnapshot row on/before target_date, or None."""
    from models.database import ShadowPortfolioSnapshot

    return (
        db.query(ShadowPortfolioSnapshot)
        .filter(
            ShadowPortfolioSnapshot.shadow_portfolio_id == shadow_id,
            ShadowPortfolioSnapshot.snapshot_date <= target_date,
        )
        .order_by(ShadowPortfolioSnapshot.snapshot_date.desc())
        .first()
    )


def score_directional_calls(
    inception_holdings: list[dict],
    horizon_holdings_json: str | None,
) -> tuple[float | None, bool | None, dict]:
    """Directional correctness of each BUY/ACCUMULATE/SELL/REDUCE call at horizon.

    Pure function — no DB access — so it is unit-testable with synthetic
    holdings lists.

    Compares each holding's inception_price (frozen at recommendation time)
    to the price the shadow itself persisted in the horizon-date SPS row's
    holdings_json (never a fresh price lookup — the same number
    shadow_tracker already computed and stored). HOLD calls and holdings with
    no resolvable horizon price are excluded from the count.

    Directional convention mirrors services/decision_memory/calibration.py:
    BUY/ACCUMULATE expects price up, SELL/REDUCE expects price down.

    Returns (score_pct 0-100 | None, directional_correct bool | None, detail dict).
    directional_correct is None when there are zero evaluable calls (e.g. an
    all-HOLD recommendation), never guessed as True/False.
    """
    if not horizon_holdings_json:
        return None, None, {"note": "no_horizon_holdings_snapshot"}
    try:
        horizon_holdings = {
            h["symbol"]: h for h in json.loads(horizon_holdings_json) if h.get("symbol")
        }
    except Exception:
        return None, None, {"note": "unparseable_horizon_holdings"}

    correct = 0
    total = 0
    per_symbol: list[dict] = []
    for h in inception_holdings:
        sym = h.get("symbol")
        action = (h.get("action") or "").upper()
        if not sym or action not in ("BUY", "ACCUMULATE", "SELL", "REDUCE"):
            continue
        entry_price = h.get("inception_price")
        horizon = horizon_holdings.get(sym)
        horizon_price = horizon.get("current_price") if horizon else None
        if not entry_price or not horizon_price or entry_price <= 0 or horizon_price <= 0:
            continue

        bullish = action in ("BUY", "ACCUMULATE")
        went_up = horizon_price > entry_price
        is_correct = bullish == went_up

        correct += int(is_correct)
        total += 1
        per_symbol.append({
            "symbol": sym,
            "action": action,
            "entry_price": entry_price,
            "horizon_price": horizon_price,
            "correct": is_correct,
        })

    if total == 0:
        return None, None, {"note": "no_directional_calls_evaluable", "per_symbol": per_symbol}

    score = round(correct / total * 100, 2)
    return score, score >= 50.0, {"correct": correct, "total": total, "per_symbol": per_symbol}


def grade_due_recommendations(db: Session, portfolio_id: int | None = None) -> dict[str, Any]:
    """Grade every recommendation snapshot that has reached a configured horizon.

    For each RecommendationSnapshot whose age (today - created_at date) has
    reached a configured horizon and lacks that horizon's RecommendationGrade
    row: reads the recommendation shadow's persisted valuation nearest the
    horizon date, computes max drawdown over the window and directional
    correctness, and writes one append-only grade row. Once the largest
    configured horizon is graded, deactivates the shadow (P2) so the daily
    valuation job stops carrying it forever.

    Missing shadow, stale valuation, or a write failure are all skipped with
    a logged reason and retried on the next call — this function never
    raises for per-snapshot problems.

    Returns {"graded": [...], "skipped": [...], "deactivated": [shadow_id, ...]}.
    """
    from main import _get_evaluation_settings  # existing Settings accessor (P7)
    from models.database import (
        RecommendationSnapshot, ShadowPortfolio, ShadowPortfolioSnapshot,
        RecommendationGrade, Workspace,
    )
    from services.analytics.attribution_engine import compute_max_drawdown

    graded: list[dict] = []
    skipped: list[dict] = []
    deactivated: list[int] = []

    today = date.today()
    today_str = today.isoformat()

    for ws in db.query(Workspace).all():
        settings = _get_evaluation_settings(db, ws.id)
        horizons = sorted(settings.get("horizons_days") or [7, 30, 90, 180])
        if not horizons:
            continue
        final_grade_kind = _horizon_grade_kind(max(horizons))

        q = db.query(RecommendationSnapshot).filter(RecommendationSnapshot.workspace_id == ws.id)
        if portfolio_id is not None:
            q = q.filter(RecommendationSnapshot.portfolio_id == portfolio_id)

        for snap in q.all():
            if not snap.created_at:
                continue
            snap_date = snap.created_at.date()
            age_days = (today - snap_date).days

            shadow = (
                db.query(ShadowPortfolio)
                .filter_by(
                    recommendation_snapshot_id=snap.id,
                    shadow_type="STATIC_FROZEN",
                    execution_decision_id=None,
                )
                .first()
            )

            for horizon_days in horizons:
                if age_days < horizon_days:
                    continue
                grade_kind = _horizon_grade_kind(horizon_days)

                already = (
                    db.query(RecommendationGrade)
                    .filter_by(recommendation_snapshot_id=snap.id, grade_kind=grade_kind)
                    .first()
                )
                if already:
                    continue

                if not shadow:
                    skipped.append({
                        "snapshot_id": snap.id, "grade_kind": grade_kind,
                        "reason": "no_recommendation_shadow",
                    })
                    continue

                target_date = min(
                    (snap_date + timedelta(days=horizon_days)).isoformat(), today_str
                )
                sps = _sps_at_or_before(db, shadow.id, target_date)
                if not sps:
                    skipped.append({
                        "snapshot_id": snap.id, "grade_kind": grade_kind,
                        "reason": "shadow_not_yet_valued",
                    })
                    continue

                gap_days = (
                    date.fromisoformat(target_date) - date.fromisoformat(sps.snapshot_date)
                ).days
                if gap_days > _MAX_VALUATION_GAP_DAYS:
                    skipped.append({
                        "snapshot_id": snap.id, "grade_kind": grade_kind,
                        "reason": "valuation_gap_too_large", "gap_days": gap_days,
                    })
                    continue

                window_values = [
                    r[0] for r in (
                        db.query(ShadowPortfolioSnapshot.total_value)
                        .filter(
                            ShadowPortfolioSnapshot.shadow_portfolio_id == shadow.id,
                            ShadowPortfolioSnapshot.snapshot_date <= sps.snapshot_date,
                        )
                        .order_by(ShadowPortfolioSnapshot.snapshot_date.asc())
                        .all()
                    )
                ]
                max_dd = compute_max_drawdown(window_values)

                inception_holdings: list[dict] = []
                try:
                    if shadow.inception_holdings_json:
                        inception_holdings = json.loads(shadow.inception_holdings_json)
                except Exception:
                    pass
                score, directional_correct, detail = score_directional_calls(
                    inception_holdings, sps.holdings_json
                )

                grade = RecommendationGrade(
                    workspace_id=ws.id,
                    recommendation_snapshot_id=snap.id,
                    portfolio_id=snap.portfolio_id,
                    grade_kind=grade_kind,
                    graded_at=datetime.utcnow(),
                    window_start=shadow.inception_date,
                    window_end=sps.snapshot_date,
                    return_pct=sps.return_pct_since_inception,
                    benchmark_return_pct=sps.benchmark_return_pct,
                    alpha=sps.alpha,
                    max_drawdown_pct=max_dd,
                    directional_correct=directional_correct,
                    score=score,
                    detail_json=json.dumps(detail, default=str),
                    created_at=datetime.utcnow(),
                )
                try:
                    db.add(grade)
                    db.commit()
                except Exception as exc:
                    db.rollback()
                    logger.warning(
                        "[EVAL] grade write failed snapshot_id=%s grade_kind=%s: %s",
                        snap.id, grade_kind, exc,
                    )
                    skipped.append({
                        "snapshot_id": snap.id, "grade_kind": grade_kind, "reason": "write_failed",
                    })
                    continue

                graded.append({"snapshot_id": snap.id, "grade_kind": grade_kind, "score": score})
                logger.info(
                    "[EVAL] Graded snapshot_id=%s grade_kind=%s return=%s alpha=%s score=%s",
                    snap.id, grade_kind, sps.return_pct_since_inception, sps.alpha, score,
                )

                if grade_kind == final_grade_kind and shadow.is_active:
                    shadow.is_active = False
                    db.commit()
                    deactivated.append(shadow.id)
                    logger.info(
                        "[EVAL] Deactivated recommendation shadow id=%s after final horizon grade %s",
                        shadow.id, final_grade_kind,
                    )

    return {"graded": graded, "skipped": skipped, "deactivated": deactivated}
