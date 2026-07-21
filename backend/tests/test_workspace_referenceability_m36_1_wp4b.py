"""M36.1 WP4B F05 — backend referenceability centralization tests.

Covers the read-side services that used to duplicate the inline
Portfolio.id + Portfolio.workspace_id lookup (now delegate to
services.portfolio_reference.resolve_portfolio_reference), and the
write-side services (execute_buy/execute_sell/execute_initial_position/
execute_quantity_correction) that used to look up Portfolio by id alone
with no workspace validation at all.

Coverage
--------
  1.  Valid workspace + portfolio resolves for a representative read service
      (goal_profile.get_goal_profile)
  2.  Absent portfolio returns the documented "not found" shape
  3.  Mismatched workspace + portfolio is rejected, not silently resolved
  4.  No fallback to another portfolio in the same workspace
  5.  Representative write-service rejection: execute_buy/execute_sell
      raise instead of writing under a mismatched workspace/portfolio pair
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base, Portfolio, PortfolioItem, Transaction, Workspace
import models.asset  # noqa: F401 — registers Asset* tables (portfolio_items.asset_id FK target)
import models.registry_finding  # noqa: F401 — registers RegistryFinding table

from services.goal_profile import get_goal_profile
from services.portfolio_transactions import execute_buy, execute_sell


def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _seed_workspace(db, name: str = "Test") -> Workspace:
    ws = Workspace(name=name)
    db.add(ws)
    db.flush()
    return ws


def _seed_portfolio(db, ws: Workspace, name: str = "P", cash: float = 1000.0) -> Portfolio:
    p = Portfolio(workspace_id=ws.id, name=name, cash_balance=cash)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


# ── Read-side centralization (goal_profile representative) ───────────────

def test_valid_workspace_and_portfolio_resolves():
    db = make_session()
    ws = _seed_workspace(db)
    p = _seed_portfolio(db, ws)

    profile = get_goal_profile(db, ws.id, p.id)
    assert profile is not None
    assert profile["portfolio_id"] == p.id


def test_absent_portfolio_returns_none():
    db = make_session()
    ws = _seed_workspace(db)

    assert get_goal_profile(db, ws.id, 99999) is None


def test_mismatched_workspace_and_portfolio_returns_none_not_the_portfolio():
    db = make_session()
    ws_a = _seed_workspace(db, "A")
    ws_b = _seed_workspace(db, "B")
    p = _seed_portfolio(db, ws_a)

    assert get_goal_profile(db, ws_b.id, p.id) is None


def test_no_fallback_to_sibling_portfolio_in_same_workspace():
    db = make_session()
    ws = _seed_workspace(db)
    _seed_portfolio(db, ws, "sibling")
    target = _seed_portfolio(db, ws, "target")

    profile = get_goal_profile(db, ws.id, target.id)
    assert profile["portfolio_id"] == target.id  # never the sibling


# ── Write-side rejection (execute_buy / execute_sell) ─────────────────────

def test_execute_buy_rejects_mismatched_workspace_portfolio_pair():
    db = make_session()
    ws_a = _seed_workspace(db, "A")
    ws_b = _seed_workspace(db, "B")
    p = _seed_portfolio(db, ws_a, cash=1000.0)

    with pytest.raises(ValueError, match="not found"):
        execute_buy(db, ws_b.id, p.id, "PTT", shares=10.0, price_per_share=5.0)

    # Nothing was written for the mismatched pair.
    assert db.query(PortfolioItem).filter_by(portfolio_id=p.id).count() == 0
    assert db.query(Transaction).filter_by(portfolio_id=p.id).count() == 0
    db.refresh(p)
    assert p.cash_balance == 1000.0


def test_execute_buy_succeeds_for_matching_workspace_portfolio_pair():
    db = make_session()
    ws = _seed_workspace(db)
    p = _seed_portfolio(db, ws, cash=1000.0)

    result = execute_buy(db, ws.id, p.id, "PTT", shares=10.0, price_per_share=5.0)
    assert result["shares"] == 10.0
    db.refresh(p)
    assert p.cash_balance < 1000.0


def test_execute_sell_rejects_mismatched_workspace_portfolio_pair():
    db = make_session()
    ws_a = _seed_workspace(db, "A")
    ws_b = _seed_workspace(db, "B")
    p = _seed_portfolio(db, ws_a, cash=1000.0)
    execute_buy(db, ws_a.id, p.id, "PTT", shares=10.0, price_per_share=5.0)

    with pytest.raises(ValueError, match="not found"):
        execute_sell(db, ws_b.id, p.id, "PTT", shares=5.0, price_per_share=6.0)

    item = db.query(PortfolioItem).filter_by(portfolio_id=p.id, symbol="PTT").first()
    assert item is not None
    assert item.shares == 10.0  # untouched by the rejected cross-workspace sell
