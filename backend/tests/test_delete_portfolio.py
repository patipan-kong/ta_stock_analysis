"""Tests for the delete_portfolio CLI command.

Tests verify:
  1.  Basic deletion — portfolio with no related records is removed
  2.  Transaction deletion
  3.  Snapshot deletion
  4.  Portfolio item deletion
  5.  Optimizer history deletion
  6.  Recommendation snapshot + execution decision deletion
  7.  Shadow portfolio + shadow snapshot + attribution metric deletion
  8.  Isolation — another portfolio's records are untouched
  9.  Non-existent portfolio → returns exit code 1
  10. --yes flag skips confirmation (no stdin required)
  11. All deletes run in a single transaction (rollback on failure)
  12. Returned counts match what was seeded
  13. Multi-level cascade: shadow snapshot deleted with shadow portfolio
  14. Count function returns zero for empty portfolio
"""
from __future__ import annotations

import sys
import os
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import (
    AttributionMetric,
    Base,
    OptimizerHistory,
    Portfolio,
    PortfolioItem,
    PortfolioSnapshot,
    RecommendationSnapshot,
    ShadowPortfolio,
    ShadowPortfolioSnapshot,
    Transaction,
    UserExecutionDecision,
    Workspace,
)
from manage import (
    _count_portfolio_relations,
    _delete_portfolio_cascade,
    _cmd_delete_portfolio,
)


# ── DB helpers ─────────────────────────────────────────────────────────────────

def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _seed_workspace(db) -> Workspace:
    ws = Workspace(name="Test")
    db.add(ws)
    db.flush()
    return ws


def _seed_portfolio(db, ws: Workspace, name: str = "Test", cash: float = 0.0) -> Portfolio:
    p = Portfolio(workspace_id=ws.id, name=name, cash_balance=cash)
    db.add(p)
    db.flush()
    return p


def _seed_transaction(db, portfolio: Portfolio, ws: Workspace) -> Transaction:
    tx = Transaction(
        workspace_id=ws.id,
        portfolio_id=portfolio.id,
        transaction_type="BUY",
        symbol="AOT.BK",
        shares=100,
        price_per_share=70.0,
        total_amount=7_000.0,
        fees=0.0,
        transaction_date=datetime.utcnow(),
    )
    db.add(tx)
    db.flush()
    return tx


def _seed_snapshot(db, portfolio: Portfolio, ws: Workspace, date: str = "2026-06-01") -> PortfolioSnapshot:
    snap = PortfolioSnapshot(
        workspace_id=ws.id,
        portfolio_id=portfolio.id,
        snapshot_date=date,
        total_value=100_000.0,
        cash_balance=10_000.0,
        total_invested=90_000.0,
    )
    db.add(snap)
    db.flush()
    return snap


def _seed_item(db, portfolio: Portfolio, ws: Workspace, symbol: str = "PTT.BK") -> PortfolioItem:
    item = PortfolioItem(
        workspace_id=ws.id,
        portfolio_id=portfolio.id,
        symbol=symbol,
        shares=100,
        avg_cost=40.0,
        sector="Energy",
    )
    db.add(item)
    db.flush()
    return item


def _seed_optimizer_history(db, portfolio: Portfolio, ws: Workspace) -> OptimizerHistory:
    oh = OptimizerHistory(
        workspace_id=ws.id,
        portfolio_id=portfolio.id,
        portfolio_name=portfolio.name,
        analyzed_at=datetime.utcnow(),
        result_json="{}",
    )
    db.add(oh)
    db.flush()
    return oh


def _seed_recommendation_snapshot(
    db, portfolio: Portfolio, ws: Workspace, oh: OptimizerHistory
) -> RecommendationSnapshot:
    rs = RecommendationSnapshot(
        workspace_id=ws.id,
        portfolio_id=portfolio.id,
        optimizer_history_id=oh.id,
    )
    db.add(rs)
    db.flush()
    return rs


def _seed_execution_decision(
    db, portfolio: Portfolio, ws: Workspace, rs: RecommendationSnapshot
) -> UserExecutionDecision:
    ued = UserExecutionDecision(
        workspace_id=ws.id,
        portfolio_id=portfolio.id,
        recommendation_snapshot_id=rs.id,
        decision="APPROVED",
        executed_at=datetime.utcnow(),
    )
    db.add(ued)
    db.flush()
    return ued


def _seed_shadow_portfolio(db, portfolio: Portfolio, ws: Workspace) -> ShadowPortfolio:
    sp = ShadowPortfolio(
        workspace_id=ws.id,
        portfolio_id=portfolio.id,
        shadow_type="STATIC_FROZEN",
        name="Shadow Test",
        inception_date="2026-06-01",
    )
    db.add(sp)
    db.flush()
    return sp


def _seed_shadow_snapshot(db, sp: ShadowPortfolio, date: str = "2026-06-01") -> ShadowPortfolioSnapshot:
    sps = ShadowPortfolioSnapshot(
        shadow_portfolio_id=sp.id,
        snapshot_date=date,
        total_value=50_000.0,
    )
    db.add(sps)
    db.flush()
    return sps


def _seed_attribution_metric(
    db, portfolio: Portfolio, ws: Workspace, sp: ShadowPortfolio
) -> AttributionMetric:
    am = AttributionMetric(
        workspace_id=ws.id,
        portfolio_id=portfolio.id,
        shadow_portfolio_id=sp.id,
        evaluation_period_start="2026-05-01",
        evaluation_period_end="2026-06-01",
    )
    db.add(am)
    db.flush()
    return am


# ── Tests: _count_portfolio_relations ─────────────────────────────────────────

def test_count_empty_portfolio():
    db = make_session()
    ws = _seed_workspace(db)
    p  = _seed_portfolio(db, ws)
    db.commit()

    counts = _count_portfolio_relations(db, p.id)

    for key in ("portfolio_items", "transactions", "snapshots", "optimizer_history",
                "recommendation_snapshots", "execution_decisions",
                "shadow_portfolios", "shadow_snapshots", "attribution_metrics"):
        assert counts[key] == 0, f"{key} should be 0 for empty portfolio"


def test_count_with_records():
    db = make_session()
    ws = _seed_workspace(db)
    p  = _seed_portfolio(db, ws)
    _seed_transaction(db, p, ws)
    _seed_snapshot(db, p, ws, "2026-06-01")
    _seed_snapshot(db, p, ws, "2026-06-02")
    _seed_item(db, p, ws)
    sp = _seed_shadow_portfolio(db, p, ws)
    _seed_shadow_snapshot(db, sp, "2026-06-01")
    _seed_shadow_snapshot(db, sp, "2026-06-02")
    db.commit()

    counts = _count_portfolio_relations(db, p.id)

    assert counts["transactions"]    == 1
    assert counts["snapshots"]       == 2
    assert counts["portfolio_items"] == 1
    assert counts["shadow_portfolios"] == 1
    assert counts["shadow_snapshots"]  == 2


# ── Tests: _delete_portfolio_cascade ──────────────────────────────────────────

def test_delete_empty_portfolio():
    db = make_session()
    ws = _seed_workspace(db)
    p  = _seed_portfolio(db, ws)
    db.commit()
    pid = p.id

    _delete_portfolio_cascade(db, pid)
    db.commit()

    assert db.query(Portfolio).filter_by(id=pid).first() is None


def test_delete_removes_transactions():
    db = make_session()
    ws = _seed_workspace(db)
    p  = _seed_portfolio(db, ws)
    _seed_transaction(db, p, ws)
    _seed_transaction(db, p, ws)
    db.commit()
    pid = p.id

    counts = _delete_portfolio_cascade(db, pid)
    db.commit()

    assert db.query(Transaction).filter_by(portfolio_id=pid).count() == 0
    assert counts["transactions"] == 2


def test_delete_removes_snapshots():
    db = make_session()
    ws = _seed_workspace(db)
    p  = _seed_portfolio(db, ws)
    for i in range(5):
        _seed_snapshot(db, p, ws, f"2026-06-0{i+1}")
    db.commit()
    pid = p.id

    counts = _delete_portfolio_cascade(db, pid)
    db.commit()

    assert db.query(PortfolioSnapshot).filter_by(portfolio_id=pid).count() == 0
    assert counts["snapshots"] == 5


def test_delete_removes_portfolio_items():
    db = make_session()
    ws = _seed_workspace(db)
    p  = _seed_portfolio(db, ws)
    _seed_item(db, p, ws, "PTT.BK")
    _seed_item(db, p, ws, "AOT.BK")
    _seed_item(db, p, ws, "KBANK.BK")
    db.commit()
    pid = p.id

    counts = _delete_portfolio_cascade(db, pid)
    db.commit()

    assert db.query(PortfolioItem).filter_by(portfolio_id=pid).count() == 0
    assert counts["portfolio_items"] == 3


def test_delete_removes_optimizer_history():
    db = make_session()
    ws = _seed_workspace(db)
    p  = _seed_portfolio(db, ws)
    _seed_optimizer_history(db, p, ws)
    db.commit()
    pid = p.id

    counts = _delete_portfolio_cascade(db, pid)
    db.commit()

    assert db.query(OptimizerHistory).filter_by(portfolio_id=pid).count() == 0
    assert counts["optimizer_history"] == 1


def test_delete_removes_recommendation_snapshots_and_decisions():
    db = make_session()
    ws = _seed_workspace(db)
    p  = _seed_portfolio(db, ws)
    oh = _seed_optimizer_history(db, p, ws)
    rs = _seed_recommendation_snapshot(db, p, ws, oh)
    _seed_execution_decision(db, p, ws, rs)
    db.commit()
    pid = p.id

    counts = _delete_portfolio_cascade(db, pid)
    db.commit()

    assert db.query(RecommendationSnapshot).filter_by(portfolio_id=pid).count() == 0
    assert db.query(UserExecutionDecision).filter_by(portfolio_id=pid).count() == 0
    assert counts["recommendation_snapshots"] == 1
    assert counts["execution_decisions"] == 1


def test_delete_removes_shadow_portfolio_and_snapshots():
    db = make_session()
    ws = _seed_workspace(db)
    p  = _seed_portfolio(db, ws)
    sp = _seed_shadow_portfolio(db, p, ws)
    _seed_shadow_snapshot(db, sp, "2026-06-01")
    _seed_shadow_snapshot(db, sp, "2026-06-02")
    _seed_shadow_snapshot(db, sp, "2026-06-03")
    db.commit()
    pid  = p.id
    spid = sp.id

    counts = _delete_portfolio_cascade(db, pid)
    db.commit()

    assert db.query(ShadowPortfolio).filter_by(portfolio_id=pid).count() == 0
    assert db.query(ShadowPortfolioSnapshot).filter_by(shadow_portfolio_id=spid).count() == 0
    assert counts["shadow_portfolios"] == 1
    assert counts["shadow_snapshots"]  == 3


def test_delete_removes_attribution_metrics():
    db = make_session()
    ws = _seed_workspace(db)
    p  = _seed_portfolio(db, ws)
    sp = _seed_shadow_portfolio(db, p, ws)
    _seed_attribution_metric(db, p, ws, sp)
    db.commit()
    pid = p.id

    counts = _delete_portfolio_cascade(db, pid)
    db.commit()

    assert db.query(AttributionMetric).filter_by(portfolio_id=pid).count() == 0
    assert counts["attribution_metrics"] == 1


def test_delete_does_not_touch_other_portfolio():
    """Records belonging to a different portfolio must be untouched."""
    db = make_session()
    ws  = _seed_workspace(db)
    p1  = _seed_portfolio(db, ws, "Alpha")
    p2  = _seed_portfolio(db, ws, "Beta")
    _seed_transaction(db, p1, ws)
    _seed_transaction(db, p2, ws)
    _seed_snapshot(db, p1, ws, "2026-06-01")
    _seed_snapshot(db, p2, ws, "2026-06-01")
    _seed_item(db, p1, ws, "PTT.BK")
    _seed_item(db, p2, ws, "KBANK.BK")
    db.commit()
    p1_id = p1.id
    p2_id = p2.id

    _delete_portfolio_cascade(db, p1_id)
    db.commit()

    # p1 gone
    assert db.query(Portfolio).filter_by(id=p1_id).first() is None
    # p2 fully intact
    assert db.query(Portfolio).filter_by(id=p2_id).first() is not None
    assert db.query(Transaction).filter_by(portfolio_id=p2_id).count() == 1
    assert db.query(PortfolioSnapshot).filter_by(portfolio_id=p2_id).count() == 1
    assert db.query(PortfolioItem).filter_by(portfolio_id=p2_id).count() == 1


def test_delete_counts_match_seeded_records():
    """Returned count dict must exactly match the number of seeded records."""
    db = make_session()
    ws = _seed_workspace(db)
    p  = _seed_portfolio(db, ws, cash=50_000.0)
    _seed_transaction(db, p, ws)
    _seed_transaction(db, p, ws)
    _seed_snapshot(db, p, ws, "2026-06-01")
    _seed_item(db, p, ws, "PTT.BK")
    _seed_item(db, p, ws, "AOT.BK")
    oh = _seed_optimizer_history(db, p, ws)
    rs = _seed_recommendation_snapshot(db, p, ws, oh)
    _seed_execution_decision(db, p, ws, rs)
    sp = _seed_shadow_portfolio(db, p, ws)
    _seed_shadow_snapshot(db, sp)
    _seed_attribution_metric(db, p, ws, sp)
    db.commit()

    counts = _delete_portfolio_cascade(db, p.id)
    db.commit()

    assert counts["transactions"]            == 2
    assert counts["snapshots"]               == 1
    assert counts["portfolio_items"]         == 2
    assert counts["optimizer_history"]       == 1
    assert counts["recommendation_snapshots"] == 1
    assert counts["execution_decisions"]     == 1
    assert counts["shadow_portfolios"]       == 1
    assert counts["shadow_snapshots"]        == 1
    assert counts["attribution_metrics"]     == 1


# ── Tests: _cmd_delete_portfolio ──────────────────────────────────────────────

def _make_args(portfolio_id: int, yes: bool = True) -> object:
    from types import SimpleNamespace
    return SimpleNamespace(id=portfolio_id, yes=yes)


def _patch_session(db_session):
    """Patch SessionLocal to return a pre-built in-memory session."""
    return patch("manage.SessionLocal", return_value=db_session)


def test_cmd_delete_portfolio_not_found():
    db = make_session()
    ws = _seed_workspace(db)
    db.commit()

    with _patch_session(db):
        exit_code = _cmd_delete_portfolio(_make_args(portfolio_id=9999, yes=True))

    assert exit_code == 1


def test_cmd_delete_portfolio_yes_flag_skips_confirm():
    db = make_session()
    ws = _seed_workspace(db)
    p  = _seed_portfolio(db, ws)
    pid = p.id
    db.commit()

    # --yes: should not call input() at all
    with _patch_session(db):
        with patch("builtins.input") as mock_input:
            exit_code = _cmd_delete_portfolio(_make_args(portfolio_id=pid, yes=True))
            mock_input.assert_not_called()

    assert exit_code == 0
    assert db.query(Portfolio).filter_by(id=pid).first() is None


def test_cmd_delete_portfolio_confirm_no_cancels():
    db = make_session()
    ws = _seed_workspace(db)
    p  = _seed_portfolio(db, ws)
    pid = p.id
    db.commit()

    with _patch_session(db):
        with patch("builtins.input", return_value="N"):
            exit_code = _cmd_delete_portfolio(_make_args(portfolio_id=pid, yes=False))

    assert exit_code == 3
    # Portfolio must still exist
    assert db.query(Portfolio).filter_by(id=pid).first() is not None


def test_cmd_delete_portfolio_confirm_yes_deletes():
    db = make_session()
    ws = _seed_workspace(db)
    p  = _seed_portfolio(db, ws)
    _seed_transaction(db, p, ws)
    pid = p.id
    db.commit()

    with _patch_session(db):
        with patch("builtins.input", return_value="y"):
            exit_code = _cmd_delete_portfolio(_make_args(portfolio_id=pid, yes=False))

    assert exit_code == 0
    assert db.query(Portfolio).filter_by(id=pid).first() is None
    assert db.query(Transaction).filter_by(portfolio_id=pid).count() == 0


def test_cmd_delete_rolls_back_on_error():
    """If the cascade delete raises, the transaction must be rolled back."""
    db = make_session()
    ws = _seed_workspace(db)
    p  = _seed_portfolio(db, ws)
    _seed_transaction(db, p, ws)
    pid = p.id
    db.commit()

    def _raise(*args, **kwargs):
        raise RuntimeError("Simulated DB failure")

    with _patch_session(db):
        with patch("manage._delete_portfolio_cascade", side_effect=_raise):
            exit_code = _cmd_delete_portfolio(_make_args(portfolio_id=pid, yes=True))

    # Must return error exit code
    assert exit_code == 1
    # Portfolio and transaction must still exist after rollback
    assert db.query(Portfolio).filter_by(id=pid).first() is not None
    assert db.query(Transaction).filter_by(portfolio_id=pid).count() == 1
