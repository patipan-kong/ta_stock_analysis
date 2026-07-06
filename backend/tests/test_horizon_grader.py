"""Tests for services/evaluation/horizon_grader.py + expired_writer.py — AI Evaluation M1.

Uses an in-memory SQLite database seeded directly through the real
SQLAlchemy ORM models (models/database.py) so grading/EXPIRED logic runs
through real session queries without touching the live Postgres dev DB.
SQLite is sufficient here: every column touched by this module is a plain
Integer/String/Float/Boolean/Text/DateTime, no Postgres-only types.

Coverage
--------
Maturity boundaries
  1. Day 29 not mature for H30 — no grade, no skip entry (simply not due yet)
  2. Day 30 exactly mature for H30 — grade written
Append-only
  3. Grading twice writes each (snapshot, grade_kind) pair only once
Skip-with-reason
  4. No recommendation shadow -> skipped "no_recommendation_shadow"
  5. Shadow exists but never valued -> skipped "shadow_not_yet_valued"
Deactivation
  6. Shadow deactivated once the largest configured horizon is graded
  7. Shadow stays active before the largest horizon is reached
Directional scoring (pure function, no DB)
  8. All BUY calls correct when price rose
  9. All SELL calls correct when price fell
  10. Mixed calls -> score is exactly correct/total
  11. HOLD calls excluded from scoring
  12. No evaluable calls -> (None, None, ...)
EXPIRED writer (P4)
  13. Aged-out snapshot (>= expiry_days, no decision, no sibling) gets EXPIRED
  14. Not-yet-aged snapshot with no newer sibling decision stays undecided
  15. Superseded snapshot (older sibling, newer sibling decided) gets EXPIRED
  16. Snapshot with an existing real decision is never touched
Backfill idempotency
  17. create_recommendation_shadow called twice returns the same shadow id,
      second call is a no-op ("exists")
"""
from __future__ import annotations

import itertools
import json
import sys
import os
from datetime import datetime, date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# optimizer_history_id is NOT NULL + unique on RecommendationSnapshot; these
# tests don't exercise OptimizerHistory at all, so a monotonic counter gives
# every synthetic snapshot a distinct placeholder value.
_oh_id_counter = itertools.count(1)

from models.database import (
    Base, Workspace, Portfolio, RecommendationSnapshot, ShadowPortfolio,
    ShadowPortfolioSnapshot, UserExecutionDecision, RecommendationGrade,
)
from services.evaluation.horizon_grader import (
    grade_due_recommendations, score_directional_calls,
)
from services.evaluation.expired_writer import write_expired_decisions
from services.decision_memory.shadow_tracker import create_recommendation_shadow


# ── DB fixture ─────────────────────────────────────────────────────────────────

@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture()
def ws_portfolio(db):
    ws = Workspace(name="Test")
    db.add(ws)
    db.commit()
    db.refresh(ws)

    portfolio = Portfolio(workspace_id=ws.id, name="P1", cash_balance=0.0)
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    return ws, portfolio


# ── Seeding helper ─────────────────────────────────────────────────────────────

def _seed_recommendation(
    db, ws, portfolio, age_days: int, sps_through_day: int | None = None,
    action: str = "BUY", daily_step: float = 1.0,
) -> tuple[RecommendationSnapshot, ShadowPortfolio]:
    """Create a graded-recommendation fixture: snapshot + its recommendation shadow.

    Writes one ShadowPortfolioSnapshot per day from 0..sps_through_day (default:
    age_days), with total_value walking up by daily_step per day so return_pct
    and max-drawdown math has real signal to compute over.
    """
    created_at = datetime.utcnow() - timedelta(days=age_days)
    snap_date = created_at.date()

    snap = RecommendationSnapshot(
        workspace_id=ws.id,
        optimizer_history_id=next(_oh_id_counter),
        portfolio_id=portfolio.id,
        total_portfolio_value=1000.0,
        projected_allocations_json=json.dumps([
            {"symbol": "AAA", "action": action, "target_weight": 100.0},
        ]),
        created_at=created_at,
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)

    entry_price = 100.0
    shadow = ShadowPortfolio(
        workspace_id=ws.id,
        portfolio_id=portfolio.id,
        shadow_type="STATIC_FROZEN",
        name=f"Recommendation @ {snap_date.isoformat()}",
        inception_date=snap_date.isoformat(),
        inception_value=1000.0,
        recommendation_snapshot_id=snap.id,
        execution_decision_id=None,
        inception_holdings_json=json.dumps([
            {"symbol": "AAA", "action": action, "shares": 10.0,
             "inception_price": entry_price, "price_frozen": False},
        ]),
        paper_cash_balance=0.0,
        is_active=True,
        created_at=created_at,
    )
    db.add(shadow)
    db.commit()
    db.refresh(shadow)

    through = age_days if sps_through_day is None else sps_through_day
    for d in range(0, through + 1):
        sd = (snap_date + timedelta(days=d)).isoformat()
        price = entry_price + daily_step * d
        total_value = 10.0 * price
        db.add(ShadowPortfolioSnapshot(
            shadow_portfolio_id=shadow.id,
            snapshot_date=sd,
            total_value=total_value,
            return_pct_since_inception=round((total_value - 1000.0) / 1000.0 * 100, 4),
            daily_return_pct=None,
            holdings_json=json.dumps([
                {"symbol": "AAA", "action": action, "current_price": price,
                 "inception_price": entry_price, "market_value": total_value},
            ]),
            benchmark_symbol="^GSPC",
            benchmark_return_pct=0.0,
            alpha=round((total_value - 1000.0) / 1000.0 * 100, 4),
            created_at=created_at,
        ))
    db.commit()

    return snap, shadow


def _set_horizons(db, ws, horizons: list[int]) -> None:
    from models.database import Settings
    db.add(Settings(
        workspace_id=ws.id, key="evaluation_settings",
        value=json.dumps({"horizons_days": horizons}),
    ))
    db.commit()


# ── Maturity boundaries ────────────────────────────────────────────────────────

def test_day_29_not_mature_for_h30(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    _set_horizons(db, ws, [30])
    _seed_recommendation(db, ws, portfolio, age_days=29)

    result = grade_due_recommendations(db)

    assert result["graded"] == []
    assert result["skipped"] == []
    assert db.query(RecommendationGrade).count() == 0


def test_day_30_exactly_mature_for_h30(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    _set_horizons(db, ws, [30])
    _seed_recommendation(db, ws, portfolio, age_days=30)

    result = grade_due_recommendations(db)

    assert len(result["graded"]) == 1
    assert result["graded"][0]["grade_kind"] == "H30"
    grade = db.query(RecommendationGrade).one()
    assert grade.grade_kind == "H30"
    assert grade.return_pct is not None


# ── Append-only ────────────────────────────────────────────────────────────────

def test_grading_twice_is_append_only(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    _set_horizons(db, ws, [7])
    _seed_recommendation(db, ws, portfolio, age_days=10)

    first = grade_due_recommendations(db)
    assert len(first["graded"]) == 1
    assert db.query(RecommendationGrade).count() == 1

    second = grade_due_recommendations(db)
    assert second["graded"] == []
    assert db.query(RecommendationGrade).count() == 1


# ── Skip-with-reason ───────────────────────────────────────────────────────────

def test_skip_no_recommendation_shadow(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    _set_horizons(db, ws, [7])
    snap = RecommendationSnapshot(
        workspace_id=ws.id,
        optimizer_history_id=next(_oh_id_counter),
        portfolio_id=portfolio.id,
        total_portfolio_value=1000.0,
        projected_allocations_json=json.dumps([{"symbol": "AAA", "action": "BUY", "target_weight": 100.0}]),
        created_at=datetime.utcnow() - timedelta(days=10),
    )
    db.add(snap)
    db.commit()

    result = grade_due_recommendations(db)

    assert result["graded"] == []
    assert len(result["skipped"]) == 1
    assert result["skipped"][0]["reason"] == "no_recommendation_shadow"


def test_skip_shadow_not_yet_valued(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    _set_horizons(db, ws, [7])
    # sps_through_day=-1 writes zero ShadowPortfolioSnapshot rows.
    _seed_recommendation(db, ws, portfolio, age_days=10, sps_through_day=-1)

    result = grade_due_recommendations(db)

    assert result["graded"] == []
    assert len(result["skipped"]) == 1
    assert result["skipped"][0]["reason"] == "shadow_not_yet_valued"


# ── Deactivation ───────────────────────────────────────────────────────────────

def test_shadow_deactivated_after_final_horizon(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    _set_horizons(db, ws, [7, 30])
    snap, shadow = _seed_recommendation(db, ws, portfolio, age_days=30)

    result = grade_due_recommendations(db)

    assert {g["grade_kind"] for g in result["graded"]} == {"H7", "H30"}
    assert result["deactivated"] == [shadow.id]
    db.refresh(shadow)
    assert shadow.is_active is False


def test_shadow_stays_active_before_final_horizon(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    _set_horizons(db, ws, [7, 30])
    snap, shadow = _seed_recommendation(db, ws, portfolio, age_days=7)

    result = grade_due_recommendations(db)

    assert {g["grade_kind"] for g in result["graded"]} == {"H7"}
    assert result["deactivated"] == []
    db.refresh(shadow)
    assert shadow.is_active is True


# ── Directional scoring (pure function) ────────────────────────────────────────

def test_directional_all_buy_correct_when_price_rose():
    inception = [{"symbol": "AAA", "action": "BUY", "inception_price": 100.0}]
    horizon_json = json.dumps([{"symbol": "AAA", "current_price": 120.0}])
    score, correct, detail = score_directional_calls(inception, horizon_json)
    assert score == 100.0
    assert correct is True


def test_directional_all_sell_correct_when_price_fell():
    inception = [{"symbol": "AAA", "action": "SELL", "inception_price": 100.0}]
    horizon_json = json.dumps([{"symbol": "AAA", "current_price": 80.0}])
    score, correct, detail = score_directional_calls(inception, horizon_json)
    assert score == 100.0
    assert correct is True


def test_directional_mixed_calls_score_is_exact_ratio():
    inception = [
        {"symbol": "AAA", "action": "BUY", "inception_price": 100.0},   # rose -> correct
        {"symbol": "BBB", "action": "BUY", "inception_price": 100.0},   # fell -> wrong
        {"symbol": "CCC", "action": "SELL", "inception_price": 100.0},  # fell -> correct
    ]
    horizon_json = json.dumps([
        {"symbol": "AAA", "current_price": 110.0},
        {"symbol": "BBB", "current_price": 90.0},
        {"symbol": "CCC", "current_price": 90.0},
    ])
    score, correct, detail = score_directional_calls(inception, horizon_json)
    assert score == pytest.approx(66.67, abs=0.01)
    assert correct is True
    assert detail["correct"] == 2
    assert detail["total"] == 3


def test_directional_hold_excluded_from_scoring():
    inception = [
        {"symbol": "AAA", "action": "BUY", "inception_price": 100.0},
        {"symbol": "BBB", "action": "HOLD", "inception_price": 100.0},
    ]
    horizon_json = json.dumps([
        {"symbol": "AAA", "current_price": 110.0},
        {"symbol": "BBB", "current_price": 50.0},
    ])
    score, correct, detail = score_directional_calls(inception, horizon_json)
    assert score == 100.0
    assert detail["total"] == 1


def test_directional_no_evaluable_calls_returns_none():
    inception = [{"symbol": "AAA", "action": "HOLD", "inception_price": 100.0}]
    horizon_json = json.dumps([{"symbol": "AAA", "current_price": 110.0}])
    score, correct, detail = score_directional_calls(inception, horizon_json)
    assert score is None
    assert correct is None


# ── EXPIRED writer (P4) ─────────────────────────────────────────────────────────

def _bare_snapshot(db, ws, portfolio, age_days: int) -> RecommendationSnapshot:
    snap = RecommendationSnapshot(
        workspace_id=ws.id,
        optimizer_history_id=next(_oh_id_counter),
        portfolio_id=portfolio.id,
        total_portfolio_value=1000.0,
        created_at=datetime.utcnow() - timedelta(days=age_days),
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return snap


def test_expired_aged_out(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    snap = _bare_snapshot(db, ws, portfolio, age_days=20)  # >= default 14-day expiry

    result = write_expired_decisions(db)

    assert len(result["written"]) == 1
    assert result["written"][0]["reason"] == "aged_out"
    decision = db.query(UserExecutionDecision).filter_by(recommendation_snapshot_id=snap.id).one()
    assert decision.decision == "EXPIRED"
    assert decision.is_system_generated is True


def test_not_yet_aged_stays_undecided(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    _bare_snapshot(db, ws, portfolio, age_days=5)

    result = write_expired_decisions(db)

    assert result["written"] == []
    assert db.query(UserExecutionDecision).count() == 0


def test_superseded_by_newer_decided_sibling(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    older = _bare_snapshot(db, ws, portfolio, age_days=20)
    newer = _bare_snapshot(db, ws, portfolio, age_days=2)
    db.add(UserExecutionDecision(
        workspace_id=ws.id, recommendation_snapshot_id=newer.id, portfolio_id=portfolio.id,
        decision="APPROVED", is_system_generated=False, executed_at=datetime.utcnow(),
    ))
    db.commit()

    result = write_expired_decisions(db)

    written_for_older = [w for w in result["written"] if w["snapshot_id"] == older.id]
    assert len(written_for_older) == 1
    assert written_for_older[0]["reason"] == "superseded"
    written_for_newer = [w for w in result["written"] if w["snapshot_id"] == newer.id]
    assert written_for_newer == []  # already decided, untouched


def test_decided_snapshot_never_touched(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    snap = _bare_snapshot(db, ws, portfolio, age_days=20)
    db.add(UserExecutionDecision(
        workspace_id=ws.id, recommendation_snapshot_id=snap.id, portfolio_id=portfolio.id,
        decision="REJECTED", is_system_generated=False, executed_at=datetime.utcnow(),
    ))
    db.commit()

    result = write_expired_decisions(db)

    assert result["written"] == []
    decisions = db.query(UserExecutionDecision).filter_by(recommendation_snapshot_id=snap.id).all()
    assert len(decisions) == 1
    assert decisions[0].decision == "REJECTED"


# ── Backfill idempotency ────────────────────────────────────────────────────────

def test_create_recommendation_shadow_idempotent(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    snap = RecommendationSnapshot(
        workspace_id=ws.id,
        optimizer_history_id=next(_oh_id_counter),
        portfolio_id=portfolio.id,
        total_portfolio_value=1000.0,
        projected_allocations_json=json.dumps([{"symbol": "AAA", "action": "BUY", "target_weight": 100.0}]),
        created_at=datetime.utcnow(),
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)

    first = create_recommendation_shadow(db, snap.id, ws.id)
    assert first["action"] == "created"
    assert db.query(ShadowPortfolio).count() == 1

    second = create_recommendation_shadow(db, snap.id, ws.id)
    assert second["action"] == "exists"
    assert second["shadow_id"] == first["shadow_id"]
    assert db.query(ShadowPortfolio).count() == 1
