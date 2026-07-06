"""Tests for services/analytics/human_vs_ai.py::compute_scoreboard — AI Evaluation M5.

Coverage
--------
1. Cold start (no decisions) -> status="cold_start".
2. is_system_generated (EXPIRED) decisions are excluded -- S5 is deliberate
   human judgment vs AI, not inaction (that's opportunity_cost's job).
3. A REJECTED decision with a graded horizon and a real return delta lands
   in the correct outcome bucket (human_better / ai_better) and contributes
   to trade-class segmentation.
4. Tie band: a delta within evaluation_settings.tie_band_pct is a tie, not
   a win for either side.
5. MANUAL_OVERRIDE with a structured override_type segments by that type.
6. A decision with no matured grade row is "maturing", never estimated.
"""
from __future__ import annotations

import json
import sys
import os
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.analytics.human_vs_ai import compute_scoreboard  # noqa: E402


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


_ALLOCS_WITH_FUNDING = [
    {"symbol": "CENTEL", "action": "BUY", "allocation_change_percent": 3.0,
     "current_weight": 0.0, "estimated_amount": 30_000, "sector": "Consumer"},
    {"symbol": "XYZ", "action": "REDUCE", "allocation_change_percent": -3.0,
     "current_weight": 10.0, "estimated_amount": 30_000, "sector": "Healthcare"},
]


def _seed_snapshot(db, ws, portfolio, allocations, days_ago=10):
    from models.database import OptimizerHistory, RecommendationSnapshot

    oh = OptimizerHistory(
        workspace_id=ws.id, portfolio_id=portfolio.id, portfolio_name=portfolio.name,
        analyzed_at=datetime.utcnow(), swap_count=0,
        result_json=json.dumps({"target_allocations": allocations, "cash_balance": 50_000.0}),
    )
    db.add(oh)
    db.commit()
    db.refresh(oh)

    snap = RecommendationSnapshot(
        workspace_id=ws.id, optimizer_history_id=oh.id, portfolio_id=portfolio.id,
        total_portfolio_value=1_000_000.0,
        projected_allocations_json=json.dumps(allocations),
        active_policy_json=json.dumps({"violations": []}),
        created_at=datetime.utcnow() - timedelta(days=days_ago),
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return snap


def _seed_decision(db, ws, portfolio, snap, decision_type, days_ago=10, is_system_generated=False,
                    override_type=None):
    from models.database import UserExecutionDecision

    dec = UserExecutionDecision(
        workspace_id=ws.id, recommendation_snapshot_id=snap.id, portfolio_id=portfolio.id,
        decision=decision_type,
        is_system_generated=is_system_generated,
        override_type=override_type,
        executed_at=datetime.utcnow() - timedelta(days=days_ago),
        created_at=datetime.utcnow() - timedelta(days=days_ago),
    )
    db.add(dec)
    db.commit()
    db.refresh(dec)
    return dec


def _seed_grade(db, ws, portfolio, snap, grade_kind="H7", return_pct=2.0):
    from models.database import RecommendationGrade

    db.add(RecommendationGrade(
        workspace_id=ws.id, recommendation_snapshot_id=snap.id, portfolio_id=portfolio.id,
        grade_kind=grade_kind, graded_at=datetime.utcnow(),
        window_start="2026-01-01", window_end=datetime.utcnow().date().isoformat(),
        return_pct=return_pct, alpha=1.0,
        created_at=datetime.utcnow(),
    ))
    db.commit()


def _seed_portfolio_snapshots(db, ws, portfolio, start_value=1_000_000.0, end_value=1_050_000.0, days_ago=10):
    from models.database import PortfolioSnapshot

    db.add(PortfolioSnapshot(
        workspace_id=ws.id, portfolio_id=portfolio.id,
        snapshot_date=(datetime.utcnow() - timedelta(days=days_ago)).date().isoformat(),
        total_value=start_value, cash_balance=0.0,
    ))
    db.add(PortfolioSnapshot(
        workspace_id=ws.id, portfolio_id=portfolio.id,
        snapshot_date=datetime.utcnow().date().isoformat(),
        total_value=end_value, cash_balance=0.0,
    ))
    db.commit()


def test_cold_start_no_decisions(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    result = compute_scoreboard(db, portfolio.id, period_days=90)
    assert result["status"] == "cold_start"
    assert result["summary"]["n_graded"] == 0


def test_system_generated_expired_excluded(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    snap = _seed_snapshot(db, ws, portfolio, _ALLOCS_WITH_FUNDING)
    _seed_decision(db, ws, portfolio, snap, "EXPIRED", is_system_generated=True)
    _seed_grade(db, ws, portfolio, snap, "H7", return_pct=2.0)
    _seed_portfolio_snapshots(db, ws, portfolio)

    result = compute_scoreboard(db, portfolio.id, period_days=90)
    assert result["status"] == "cold_start"
    assert result["decisions"] == []


def test_human_better_bucket_and_class_segmentation(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    snap = _seed_snapshot(db, ws, portfolio, _ALLOCS_WITH_FUNDING)
    _seed_decision(db, ws, portfolio, snap, "REJECTED")
    _seed_grade(db, ws, portfolio, snap, "H7", return_pct=1.0)
    _seed_portfolio_snapshots(db, ws, portfolio, 1_000_000.0, 1_040_000.0)  # actual +4%

    result = compute_scoreboard(db, portfolio.id, period_days=90)

    assert result["status"] == "ok"
    assert result["summary"]["n_graded"] == 1
    # delta = ai(1.0) - actual(4.0) = -3.0 -> human_better
    assert result["summary"]["you_beat_ai"] == 1
    assert result["summary"]["ai_beat_you"] == 0
    assert result["summary"]["net_effect_pct"] == pytest.approx(3.0, abs=0.01)
    assert "Portfolio Improvement" in result["by_trade_class"]
    assert result["by_trade_class"]["Portfolio Improvement"]["human_better"] == 1


def test_tie_band_applies(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    snap = _seed_snapshot(db, ws, portfolio, _ALLOCS_WITH_FUNDING)
    _seed_decision(db, ws, portfolio, snap, "REJECTED")
    _seed_grade(db, ws, portfolio, snap, "H7", return_pct=2.1)
    _seed_portfolio_snapshots(db, ws, portfolio, 1_000_000.0, 1_020_000.0)  # actual +2% -> delta 0.1, within default 0.3 tie band

    result = compute_scoreboard(db, portfolio.id, period_days=90)
    assert result["summary"]["ties"] == 1
    assert result["summary"]["you_beat_ai"] == 0
    assert result["summary"]["ai_beat_you"] == 0


def test_override_type_segmentation(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    snap = _seed_snapshot(db, ws, portfolio, _ALLOCS_WITH_FUNDING)
    _seed_decision(db, ws, portfolio, snap, "MANUAL_OVERRIDE", override_type="REPLACE_SYMBOL")
    _seed_grade(db, ws, portfolio, snap, "H7", return_pct=5.0)
    _seed_portfolio_snapshots(db, ws, portfolio, 1_000_000.0, 1_010_000.0)  # actual +1% -> AI better

    result = compute_scoreboard(db, portfolio.id, period_days=90)
    assert result["summary"]["ai_beat_you"] == 1
    assert result["by_override_type"]["REPLACE_SYMBOL"]["ai_better"] == 1


def test_no_graded_horizon_is_maturing(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    snap = _seed_snapshot(db, ws, portfolio, _ALLOCS_WITH_FUNDING)
    _seed_decision(db, ws, portfolio, snap, "REJECTED")
    _seed_portfolio_snapshots(db, ws, portfolio)

    result = compute_scoreboard(db, portfolio.id, period_days=90)
    assert result["summary"]["maturing"] == 1
    assert result["summary"]["n_graded"] == 0
    assert result["decisions"][0]["status"] == "maturing"
