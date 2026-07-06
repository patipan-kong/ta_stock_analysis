"""Tests for the Transaction <-> UserExecutionDecision linkage — AI Evaluation
M2 (P5). Metadata-only: services/portfolio_transactions.py::execute_buy /
execute_sell accept an optional execution_decision_id and store it verbatim
on the created Transaction row. Never inferred, never required.

Coverage
--------
1. execute_buy with execution_decision_id sets Transaction.execution_decision_id
2. execute_sell with execution_decision_id sets Transaction.execution_decision_id
3. Omitting it (existing call sites, existing tests) leaves it None —
   fully backward compatible
"""
from __future__ import annotations

import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base, Portfolio, PortfolioItem, Transaction, UserExecutionDecision, Workspace
from services.portfolio_transactions import execute_buy, execute_sell


def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


@pytest.fixture()
def db():
    session = make_session()
    yield session
    session.close()


@pytest.fixture()
def ws_portfolio_decision(db):
    ws = Workspace(name="Test")
    db.add(ws)
    db.commit()
    db.refresh(ws)

    portfolio = Portfolio(workspace_id=ws.id, name="P1", cash_balance=100_000.0)
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)

    decision = UserExecutionDecision(
        workspace_id=ws.id, recommendation_snapshot_id=1, portfolio_id=portfolio.id,
        decision="APPROVED", is_system_generated=False,
    )
    db.add(decision)
    db.commit()
    db.refresh(decision)

    return ws, portfolio, decision


def test_execute_buy_links_execution_decision_id(db, ws_portfolio_decision):
    ws, portfolio, decision = ws_portfolio_decision

    result = execute_buy(
        db, ws.id, portfolio.id, "CENTEL", shares=100, price_per_share=30.0,
        execution_decision_id=decision.id,
    )
    tx = db.query(Transaction).filter_by(id=result["transaction_id"]).one()
    assert tx.execution_decision_id == decision.id


def test_execute_sell_links_execution_decision_id(db, ws_portfolio_decision):
    ws, portfolio, decision = ws_portfolio_decision
    buy_result = execute_buy(db, ws.id, portfolio.id, "CENTEL", shares=100, price_per_share=30.0)

    sell_result = execute_sell(
        db, ws.id, portfolio.id, "CENTEL", shares=50, price_per_share=32.0,
        execution_decision_id=decision.id,
    )
    tx = db.query(Transaction).filter_by(id=sell_result["transaction_id"]).one()
    assert tx.execution_decision_id == decision.id
    # The unrelated earlier BUY was never linked — no retroactive inference.
    buy_tx = db.query(Transaction).filter_by(id=buy_result["transaction_id"]).one()
    assert buy_tx.execution_decision_id is None


def test_omitting_execution_decision_id_leaves_it_none(db, ws_portfolio_decision):
    ws, portfolio, _decision = ws_portfolio_decision

    result = execute_buy(db, ws.id, portfolio.id, "CENTEL", shares=100, price_per_share=30.0)
    tx = db.query(Transaction).filter_by(id=result["transaction_id"]).one()
    assert tx.execution_decision_id is None
