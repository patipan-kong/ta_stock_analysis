"""Tests for services/evaluation/opportunity_cost.py — AI Evaluation M5.

Coverage
--------
1. Cold start (no decisions in window) -> status="cold_start", empty rows,
   net_opportunity_cost_pct is None (never 0).
2. APPROVED decision -> not a divergence, excluded from rows entirely.
3. REJECTED decision with a graded H7 row + portfolio snapshots ->
   counterfactual_delta_pct = actual_return_pct - recommendation_return_pct,
   contributes to net_opportunity_cost_pct.
4. Divergence with no matured grade row -> status="maturing", excluded from
   the net total, counted in maturing_count.
5. A deferred REDUCE candidate (no funding need) appears in system_deferrals
   with counterfactual_pricing="unavailable" -- never a fabricated return.
"""
from __future__ import annotations

import json
import sys
import os
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.evaluation.opportunity_cost import compute_opportunity_cost  # noqa: E402


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


def _seed_decision(db, ws, portfolio, snap, decision_type, days_ago=10):
    from models.database import UserExecutionDecision

    dec = UserExecutionDecision(
        workspace_id=ws.id, recommendation_snapshot_id=snap.id, portfolio_id=portfolio.id,
        decision=decision_type,
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


_ALLOCS_BUY_ONLY = [
    {"symbol": "CENTEL", "action": "BUY", "allocation_change_percent": 3.0,
     "current_weight": 0.0, "estimated_amount": 30_000, "sector": "Consumer"},
]

# No BUY need -> funding gap is 0 -> this REDUCE has no job to do today -> deferred.
_ALLOCS_DEFERRED_REDUCE = [
    {"symbol": "BH", "action": "REDUCE", "allocation_change_percent": -3.0,
     "current_weight": 10.0, "estimated_amount": 30_000, "sector": "Consumer"},
]


def test_cold_start_no_decisions(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    result = compute_opportunity_cost(db, portfolio.id, period_days=90)

    assert result["status"] == "cold_start"
    assert result["rows"] == []
    assert result["net_opportunity_cost_pct"] is None
    assert result["graded_count"] == 0
    assert result["system_deferrals"] == []


def test_approved_decision_is_not_a_divergence(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    snap = _seed_snapshot(db, ws, portfolio, _ALLOCS_BUY_ONLY)
    _seed_decision(db, ws, portfolio, snap, "APPROVED")

    result = compute_opportunity_cost(db, portfolio.id, period_days=90)

    assert result["rows"] == []
    assert result["status"] == "cold_start"


def test_rejected_decision_with_graded_horizon_is_priced(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    snap = _seed_snapshot(db, ws, portfolio, _ALLOCS_BUY_ONLY)
    _seed_decision(db, ws, portfolio, snap, "REJECTED")
    _seed_grade(db, ws, portfolio, snap, "H7", return_pct=2.0)
    _seed_portfolio_snapshots(db, ws, portfolio, 1_000_000.0, 1_030_000.0)  # actual +3%

    result = compute_opportunity_cost(db, portfolio.id, period_days=90)

    assert result["status"] == "ok"
    assert result["graded_count"] == 1
    row = result["rows"][0]
    assert row["divergence_type"] == "REJECTED"
    assert row["status"] == "graded"
    # actual (+3%) - recommendation (+2%) = +1% -> ignoring the recommendation helped
    assert row["counterfactual_delta_pct"] == pytest.approx(1.0, abs=0.01)
    assert result["net_opportunity_cost_pct"] == pytest.approx(1.0, abs=0.01)


def test_divergence_without_graded_horizon_is_maturing(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    snap = _seed_snapshot(db, ws, portfolio, _ALLOCS_BUY_ONLY)
    _seed_decision(db, ws, portfolio, snap, "MANUAL_OVERRIDE")
    _seed_portfolio_snapshots(db, ws, portfolio)

    result = compute_opportunity_cost(db, portfolio.id, period_days=90)

    assert result["maturing_count"] == 1
    assert result["graded_count"] == 0
    assert result["net_opportunity_cost_pct"] is None
    assert result["rows"][0]["status"] == "maturing"


def test_system_deferral_reported_without_fabricated_price(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    _seed_snapshot(db, ws, portfolio, _ALLOCS_DEFERRED_REDUCE, days_ago=1)

    result = compute_opportunity_cost(db, portfolio.id, period_days=90)

    assert len(result["system_deferrals"]) == 1
    deferral = result["system_deferrals"][0]
    assert deferral["symbol"] == "BH"
    assert deferral["counterfactual_pricing"] == "unavailable"
    assert "counterfactual_reason" in deferral
