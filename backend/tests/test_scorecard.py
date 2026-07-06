"""Tests for services/evaluation/scorecard.py — AI Evaluation M3.

Coverage
--------
1. Cold start: no RecommendationSnapshot ever -> status="cold_start",
   structured empty lenses (never zeros/errors).
2. Partial history: a PLAN grade exists (execution lens populated) but no
   horizon grade yet (belief lens cold) -> top-level status="partial".
3. Min-n gating: horizon grades exist but fewer than min_n_letter_grade ->
   belief.grade.status == "insufficient_evidence" even though hit_rate_pct
   is a real number (not hidden, just ungraded per UX D10).
4. Sufficient evidence (settings overridden to a low min_n): belief.grade
   reaches status="ok" with a letter.
5. Verdict payload always present with en/th/branch.
"""
from __future__ import annotations

import json
import sys
import os
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.evaluation.scorecard import compute_scorecard  # noqa: E402


@pytest.fixture()
def db():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models.database import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture()
def ws_portfolio(db):
    from models.database import Workspace, Portfolio

    ws = Workspace(name="Test")
    db.add(ws)
    db.commit()
    db.refresh(ws)

    portfolio = Portfolio(workspace_id=ws.id, name="P1", cash_balance=100_000.0)
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    return ws, portfolio


def _seed_snapshot(db, ws, portfolio, days_ago: int = 40):
    from models.database import OptimizerHistory, RecommendationSnapshot

    oh = OptimizerHistory(
        workspace_id=ws.id, portfolio_id=portfolio.id, portfolio_name=portfolio.name,
        analyzed_at=datetime.utcnow(), swap_count=0,
        result_json=json.dumps({"target_allocations": [], "cash_balance": 50_000.0}),
    )
    db.add(oh)
    db.commit()
    db.refresh(oh)

    snap = RecommendationSnapshot(
        workspace_id=ws.id, optimizer_history_id=oh.id, portfolio_id=portfolio.id,
        total_portfolio_value=1_000_000.0,
        projected_allocations_json="[]",
        created_at=datetime.utcnow() - timedelta(days=days_ago),
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return snap


def test_cold_start_portfolio_returns_cold_start_status(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    result = compute_scorecard(db, portfolio.id, period_days=90)

    assert result["status"] == "cold_start"
    assert result["belief"]["status"] == "cold_start"
    assert result["execution"]["status"] == "cold_start"
    assert result["verdict"]["en"]
    assert result["recent_grades"] == []


def test_partial_history_execution_graded_belief_cold(db, ws_portfolio):
    from models.database import RecommendationGrade

    ws, portfolio = ws_portfolio
    snap = _seed_snapshot(db, ws, portfolio)

    db.add(RecommendationGrade(
        workspace_id=ws.id, recommendation_snapshot_id=snap.id, portfolio_id=portfolio.id,
        grade_kind="PLAN", graded_at=datetime.utcnow(), score=88.0,
        detail_json=json.dumps({"necessity_score": 90.0, "funding_efficiency_score": 95.0}),
        created_at=datetime.utcnow(),
    ))
    db.commit()

    result = compute_scorecard(db, portfolio.id, period_days=90)

    assert result["execution"]["status"] == "ok"
    assert result["execution"]["avg_plan_score"] == 88.0
    assert result["execution"]["avg_necessity_pct"] == 90.0
    assert result["belief"]["status"] == "cold_start"
    assert result["status"] == "partial"


def test_min_n_gating_hides_letter_but_keeps_hit_rate(db, ws_portfolio):
    from models.database import RecommendationGrade

    ws, portfolio = ws_portfolio
    snap = _seed_snapshot(db, ws, portfolio)

    # Only 2 horizon grades -- default min_n_letter_grade is 8.
    for i, correct in enumerate([True, True]):
        db.add(RecommendationGrade(
            workspace_id=ws.id, recommendation_snapshot_id=snap.id, portfolio_id=portfolio.id,
            grade_kind=f"H{7 + i}", graded_at=datetime.utcnow(),
            window_start="2026-01-01", window_end=datetime.utcnow().date().isoformat(),
            return_pct=2.0, alpha=1.0, directional_correct=correct,
            created_at=datetime.utcnow(),
        ))
    db.commit()

    result = compute_scorecard(db, portfolio.id, period_days=90)

    assert result["belief"]["hit_rate_pct"] == 100.0
    assert result["belief"]["grade"]["status"] == "insufficient_evidence"
    assert result["belief"]["grade"]["letter"] is None


def test_sufficient_evidence_with_lowered_settings_yields_letter(db, ws_portfolio):
    from models.database import RecommendationGrade, Settings

    ws, portfolio = ws_portfolio
    snap = _seed_snapshot(db, ws, portfolio)

    db.add(Settings(
        workspace_id=ws.id, key="evaluation_settings",
        value=json.dumps({"min_n_letter_grade": 1, "min_n_win_rate": 1}),
    ))
    db.add(RecommendationGrade(
        workspace_id=ws.id, recommendation_snapshot_id=snap.id, portfolio_id=portfolio.id,
        grade_kind="H30", graded_at=datetime.utcnow(),
        window_start="2026-01-01", window_end=datetime.utcnow().date().isoformat(),
        return_pct=4.2, alpha=3.1, directional_correct=True,
        created_at=datetime.utcnow(),
    ))
    db.commit()

    result = compute_scorecard(db, portfolio.id, period_days=90)

    assert result["belief"]["grade"]["status"] == "ok"
    assert result["belief"]["grade"]["letter"] == "A+"
    assert result["verdict"]["branch"] in ("ai_ahead", "human_ahead", "tie", "insufficient_evidence")
