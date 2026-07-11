"""M6 Native Integration (M5_TRACK_B_NATIVE_INTEGRATION_TDD.md §7 Stage 5) —
factor_engine's per_stock_scores gains an additive asset_id field, read
directly off the already-loaded PortfolioItem row (materialized since Stage 2
backfill). No new resolve_asset() call, no key change — still symbol-keyed
output, asset_id is a data field only.

Network calls (fetch_info/fetch_history/fetch_price_info) are monkeypatched
out; only the DB (in-memory SQLite) is exercised for real.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base, Portfolio, PortfolioItem, Workspace
import models.asset  # noqa: F401 — registers Asset* tables on Base.metadata
import models.registry_finding  # noqa: F401 — registers RegistryFinding table

from services.analytics import factor_engine
from services.analytics.quant_engine import invalidate_all


def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    monkeypatch.setattr(factor_engine, "fetch_price_info", lambda symbol: {"current_price": 100.0})
    monkeypatch.setattr(factor_engine, "fetch_info", lambda symbol: {})
    monkeypatch.setattr(factor_engine, "fetch_history", lambda symbol, **kw: None)
    invalidate_all()
    yield
    invalidate_all()


def _seed(db, portfolio_id: int, *, asset_id: int | None):
    db.add(Workspace(id=1, name="Default"))
    db.add(Portfolio(id=portfolio_id, workspace_id=1, name="P", cash_balance=0.0))
    db.add(PortfolioItem(
        workspace_id=1, portfolio_id=portfolio_id, symbol="AOT.BK",
        shares=10.0, avg_cost=50.0, sector="Energy", asset_id=asset_id,
    ))
    db.commit()


def test_per_stock_scores_carries_materialized_asset_id():
    db = make_session()
    _seed(db, portfolio_id=101, asset_id=42)

    result = factor_engine.compute_portfolio_factor_exposure(db, portfolio_id=101, workspace_id=1)

    assert result["per_stock_scores"][0]["symbol"] == "AOT.BK"
    assert result["per_stock_scores"][0]["asset_id"] == 42


def test_per_stock_scores_asset_id_is_none_when_not_backfilled():
    """Not-yet-adjudicated holdings must not error or fabricate an id."""
    db = make_session()
    _seed(db, portfolio_id=102, asset_id=None)

    result = factor_engine.compute_portfolio_factor_exposure(db, portfolio_id=102, workspace_id=1)

    assert result["per_stock_scores"][0]["asset_id"] is None
