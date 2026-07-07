"""Tests for compute_attribution_waterfall in services/analytics/attribution_engine.py
— AI Evaluation M6 (S8 Attribution effect waterfall).

Coverage
--------
1. No actual portfolio history / no AI shadow -> status="insufficient_data".
2. Full data (actual + ACTIVE_MODEL shadow, no decisions) -> reconciliation
   identity holds: benchmark + sum(measured effects) + residual == actual,
   and the unmeasurable effects (timing, funding) are honestly "unavailable"/
   "no_overrides" rather than fabricated zeros or Nones silently dropped.
3. Residual row is always present (never silently absorbed).
"""
from __future__ import annotations

import sys
import os
from datetime import date, datetime, timedelta

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.analytics.attribution_engine import compute_attribution_waterfall  # noqa: E402


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


def _d(days_ago: int) -> str:
    return (date.today() - timedelta(days=days_ago)).isoformat()


def test_insufficient_data_no_history(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    result = compute_attribution_waterfall(db, portfolio.id, period_days=10)
    assert result["status"] == "insufficient_data"
    assert result["effects"] == []


def test_reconciliation_holds_with_full_data(db, ws_portfolio):
    from models.database import PortfolioSnapshot, ShadowPortfolio, ShadowPortfolioSnapshot

    ws, portfolio = ws_portfolio

    db.add(PortfolioSnapshot(
        workspace_id=ws.id, portfolio_id=portfolio.id, snapshot_date=_d(10),
        total_value=1_000_000.0, cash_balance=0.0,
    ))
    db.add(PortfolioSnapshot(
        workspace_id=ws.id, portfolio_id=portfolio.id, snapshot_date=_d(0),
        total_value=1_030_000.0, cash_balance=0.0,
    ))
    db.commit()

    shadow = ShadowPortfolio(
        workspace_id=ws.id, portfolio_id=portfolio.id, shadow_type="ACTIVE_MODEL",
        name="AI", inception_date=_d(10), inception_value=1_000_000.0,
        inception_holdings_json="[]", is_active=True, created_at=datetime.utcnow(),
    )
    db.add(shadow)
    db.commit()
    db.refresh(shadow)

    db.add(ShadowPortfolioSnapshot(
        shadow_portfolio_id=shadow.id, snapshot_date=_d(10), total_value=1_000_000.0,
        created_at=datetime.utcnow(),
    ))
    db.add(ShadowPortfolioSnapshot(
        shadow_portfolio_id=shadow.id, snapshot_date=_d(0), total_value=1_020_000.0,
        benchmark_return_pct=1.0, created_at=datetime.utcnow(),
    ))
    db.commit()

    result = compute_attribution_waterfall(db, portfolio.id, period_days=10)

    assert result["status"] == "ok"
    assert result["actual_return_pct"] == pytest.approx(3.0, abs=0.01)
    assert result["benchmark_return_pct"] == pytest.approx(1.0, abs=0.01)

    by_key = {e["key"]: e for e in result["effects"]}
    assert by_key["selection_allocation"]["value"] == pytest.approx(1.0, abs=0.01)
    assert by_key["selection_allocation"]["status"] == "approx"
    assert by_key["timing"]["status"] == "unavailable"
    assert by_key["funding"]["status"] == "unavailable"
    assert by_key["overrides"]["status"] == "no_overrides"
    assert by_key["overrides"]["value"] == 0.0

    measured_sum = sum(e["value"] for e in result["effects"] if e["value"] is not None)
    reconciled = result["benchmark_return_pct"] + measured_sum + result["residual_pct"]
    assert reconciled == pytest.approx(result["actual_return_pct"], abs=0.01)

    # Residual is always present as its own labeled row (never silently dropped).
    assert result["residual_pct"] is not None
    assert result["residual_note"]
    assert result["verdict"]["en"]
