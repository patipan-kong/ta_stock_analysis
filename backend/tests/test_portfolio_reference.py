"""Tests for services/portfolio_reference.py (M36.1 Phase 0).

Characterizes the referenceability resolver that replaces ~40 duplicated
inline lookups in main.py. Referenceability must depend only on exact
Portfolio Identity + exact one-workspace match (M36-WP1 §5.2, foundation
invariant 9) — never on any other portfolio, its own availability, or
lifecycle state.

Coverage
--------
  1.  Existing portfolio in the caller's workspace resolves
  2.  Nonexistent portfolio id resolves to None
  3.  Portfolio that exists but belongs to a different workspace resolves to None
      (never crosses workspace boundary — invariant 21)
  4.  resolve_portfolio_or_404 returns the portfolio when referenceable
  5.  resolve_portfolio_or_404 raises 404 with the exact historical message
      when not found
  6.  resolve_portfolio_or_404 raises 404 (not some other status) when the
      portfolio belongs to a different workspace
  7.  Referenceability is independent of sibling portfolios existing in the
      same workspace (no accidental first()-without-filter behavior)
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base, Portfolio, Workspace
import models.asset  # noqa: F401 — registers Asset* tables (portfolio_items.asset_id FK target)
from services.portfolio_reference import resolve_portfolio_or_404, resolve_portfolio_reference


def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _seed_workspace(db, name: str = "Test") -> Workspace:
    ws = Workspace(name=name)
    db.add(ws)
    db.flush()
    return ws


def _seed_portfolio(db, ws: Workspace, name: str = "P") -> Portfolio:
    p = Portfolio(workspace_id=ws.id, name=name)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def test_resolves_portfolio_in_caller_workspace():
    db = make_session()
    ws = _seed_workspace(db)
    p = _seed_portfolio(db, ws)

    assert resolve_portfolio_reference(db, p.id, ws.id) is not None
    assert resolve_portfolio_reference(db, p.id, ws.id).id == p.id


def test_nonexistent_portfolio_id_resolves_to_none():
    db = make_session()
    ws = _seed_workspace(db)

    assert resolve_portfolio_reference(db, 99999, ws.id) is None


def test_portfolio_in_different_workspace_resolves_to_none():
    db = make_session()
    ws_a = _seed_workspace(db, "A")
    ws_b = _seed_workspace(db, "B")
    p = _seed_portfolio(db, ws_a)

    assert resolve_portfolio_reference(db, p.id, ws_b.id) is None


def test_or_404_returns_portfolio_when_referenceable():
    db = make_session()
    ws = _seed_workspace(db)
    p = _seed_portfolio(db, ws)

    result = resolve_portfolio_or_404(db, p.id, ws.id)
    assert result.id == p.id


def test_or_404_raises_with_historical_message_when_missing():
    db = make_session()
    ws = _seed_workspace(db)

    with pytest.raises(HTTPException) as exc_info:
        resolve_portfolio_or_404(db, 99999, ws.id)
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Portfolio not found"


def test_or_404_raises_404_for_cross_workspace_portfolio():
    db = make_session()
    ws_a = _seed_workspace(db, "A")
    ws_b = _seed_workspace(db, "B")
    p = _seed_portfolio(db, ws_a)

    with pytest.raises(HTTPException) as exc_info:
        resolve_portfolio_or_404(db, p.id, ws_b.id)
    assert exc_info.value.status_code == 404


def test_referenceability_independent_of_sibling_portfolios():
    db = make_session()
    ws = _seed_workspace(db)
    _seed_portfolio(db, ws, "sibling-1")
    target = _seed_portfolio(db, ws, "target")
    _seed_portfolio(db, ws, "sibling-2")

    result = resolve_portfolio_or_404(db, target.id, ws.id)
    assert result.id == target.id
    assert result.name == "target"
