"""M36.1 WP4C F05 — backend referenceability centralization tests, part 2.

WP4B centralized the 8 read-side services + portfolio_transactions.py's
write paths onto services.portfolio_reference.resolve_portfolio_reference().
This WP closes the three remaining duplicated lookups the independent
re-review named: services/analytics/factor_engine.py,
services/portfolio_snapshots.py, services/ledger_validator.py.

Each test proves the pre-existing "mismatched workspace + portfolio is
rejected, not silently resolved" contract still holds exactly as documented
(same exception type / same response shape) after switching to the shared
resolver.
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base, Portfolio, Workspace
import models.asset  # noqa: F401 — registers Asset* tables
import models.registry_finding  # noqa: F401 — registers RegistryFinding table

from services.analytics import factor_engine
from services.analytics.quant_engine import invalidate_all
from services import portfolio_snapshots
from services import ledger_validator


def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _seed_two_workspaces(db):
    ws_a = Workspace(name="A")
    ws_b = Workspace(name="B")
    db.add_all([ws_a, ws_b])
    db.flush()
    p = Portfolio(workspace_id=ws_a.id, name="P", cash_balance=1000.0)
    db.add(p)
    db.commit()
    db.refresh(p)
    return ws_a, ws_b, p


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    monkeypatch.setattr(factor_engine, "fetch_price_info", lambda symbol: {"current_price": 100.0})
    monkeypatch.setattr(factor_engine, "fetch_info", lambda symbol: {})
    monkeypatch.setattr(factor_engine, "fetch_history", lambda symbol, **kw: None)
    invalidate_all()
    yield
    invalidate_all()


def test_factor_engine_mismatched_workspace_returns_not_found():
    db = make_session()
    _, ws_b, p = _seed_two_workspaces(db)

    result = factor_engine.compute_portfolio_factor_exposure(db, portfolio_id=p.id, workspace_id=ws_b.id)
    assert result == {"error": "portfolio_not_found"}


def test_factor_engine_valid_workspace_resolves():
    db = make_session()
    ws_a, _, p = _seed_two_workspaces(db)

    result = factor_engine.compute_portfolio_factor_exposure(db, portfolio_id=p.id, workspace_id=ws_a.id)
    assert result.get("error") != "portfolio_not_found"
    assert result["portfolio_id"] == p.id


def test_portfolio_snapshots_mismatched_workspace_raises_value_error():
    db = make_session()
    _, ws_b, p = _seed_two_workspaces(db)

    with pytest.raises(ValueError, match="not found"):
        asyncio.run(portfolio_snapshots.generate_daily_snapshot(db, portfolio_id=p.id, workspace_id=ws_b.id))


def test_ledger_validator_mismatched_workspace_returns_portfolio_not_found_finding():
    db = make_session()
    _, ws_b, p = _seed_two_workspaces(db)

    report = asyncio.run(ledger_validator.validate_portfolio_ledger(db, portfolio_id=p.id, workspace_id=ws_b.id))
    assert report.portfolio_name == "?"
    assert any(f.check_id == "PORTFOLIO_NOT_FOUND" for f in report.findings)


def test_ledger_validator_valid_workspace_resolves():
    db = make_session()
    ws_a, _, p = _seed_two_workspaces(db)

    report = asyncio.run(ledger_validator.validate_portfolio_ledger(db, portfolio_id=p.id, workspace_id=ws_a.id))
    assert not any(f.check_id == "PORTFOLIO_NOT_FOUND" for f in report.findings)
