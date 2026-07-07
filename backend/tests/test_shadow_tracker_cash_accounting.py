"""Tests for the paper-portfolio cash-accounting fix in shadow_tracker.py
(Accounting Correctness Milestone 1 — docs/DECISION_LOG.md, "Paper Portfolio
Cash-Leak Fix").

Root cause under test: target_weight allocations intentionally sum to less
than 100% (the optimizer's own cash floor, OPTIMIZER_PHILOSOPHY.md §2
Priority 7). Before this fix, _resolve_shares_from_weights silently dropped
the unallocated residual instead of tracking it as cash, so NAV shrank at
every rebalance with zero price movement and zero real friction. This file
proves the residual is now tracked, carried forward, and NAV-conserving.

Coverage
--------
_resolve_shares_from_weights (unit, no DB)
  1. Weights summing to 95% -> explicit cash residual, NAV conserved.
  2. Weights summing to 97% -> explicit cash residual, NAV conserved.
  3. Weights summing to 100% -> cash == 0 (no behavior change for full
     allocation, the pre-fix common case).
  4. Zero-weight liquidation for one symbol -> that holding gets 0 shares,
     not folded into a cash leak.
  5. Full liquidation (empty allocation list) -> 100% cash.
  6. Weights summing fractionally over 100% (rounding) -> cash clamped to 0,
     never negative.

assert_nav_conserved / NavInvariantError (unit, no DB)
  7. Consistent equity+cash -> no exception.
  8. Inconsistent equity+cash -> raises NavInvariantError with diagnostics.

create_active_model_shadow (DB-backed, mirrors test_ideal_series.py fixtures)
  9. First creation persists paper_cash_balance for partial weights.
  10. Multiple consecutive rebalances with NO price movement conserve NAV
      exactly across weight-sum changes (95% -> 97% -> full liquidation) —
      the direct regression test for the compounding leak this milestone
      fixes. Pre-fix, this sequence would have shrunk NAV to ~92% of
      inception; post-fix it stays exactly flat.

create_static_frozen_shadow / create_recommendation_shadow (DB-backed)
  11. Both persist a non-zero paper_cash_balance for partial-weight
      allocations instead of the previous hardcoded 0.0.
"""
from __future__ import annotations

import json
import sys
import os
from datetime import date, datetime, timedelta

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.decision_memory.shadow_tracker import (  # noqa: E402
    _resolve_shares_from_weights,
    _compute_paper_value,
    assert_nav_conserved,
    NavInvariantError,
    create_active_model_shadow,
    create_static_frozen_shadow,
    create_recommendation_shadow,
)


# ─── _resolve_shares_from_weights (unit, no DB) ────────────────────────────

def test_weights_summing_to_95_pct_produce_explicit_cash():
    allocs = [
        {"symbol": "AAA", "target_weight": 50.0, "action": "BUY"},
        {"symbol": "BBB", "target_weight": 45.0, "action": "BUY"},
    ]
    prices = {"AAA": 100.0, "BBB": 100.0}
    holdings, cash = _resolve_shares_from_weights(allocs, 1_000_000.0, prices)

    assert cash == pytest.approx(50_000.0)
    equity, _ = _compute_paper_value(holdings, prices)
    assert equity == pytest.approx(950_000.0)
    assert equity + cash == pytest.approx(1_000_000.0)


def test_weights_summing_to_97_pct_produce_explicit_cash():
    allocs = [
        {"symbol": "AAA", "target_weight": 60.0, "action": "BUY"},
        {"symbol": "BBB", "target_weight": 37.0, "action": "BUY"},
    ]
    prices = {"AAA": 50.0, "BBB": 20.0}
    holdings, cash = _resolve_shares_from_weights(allocs, 2_000_000.0, prices)

    assert cash == pytest.approx(0.03 * 2_000_000.0)
    equity, _ = _compute_paper_value(holdings, prices)
    assert equity + cash == pytest.approx(2_000_000.0)


def test_weights_summing_to_100_pct_yield_zero_cash():
    """Backward-compatibility: the pre-fix common case (full allocation)
    must be unaffected — cash is exactly 0, not a rounding artifact."""
    allocs = [
        {"symbol": "AAA", "target_weight": 60.0, "action": "BUY"},
        {"symbol": "BBB", "target_weight": 40.0, "action": "BUY"},
    ]
    prices = {"AAA": 100.0, "BBB": 100.0}
    holdings, cash = _resolve_shares_from_weights(allocs, 1_000_000.0, prices)

    assert cash == pytest.approx(0.0)
    equity, _ = _compute_paper_value(holdings, prices)
    assert equity == pytest.approx(1_000_000.0)


def test_zero_weight_liquidation_produces_zero_shares_not_a_leak():
    allocs = [
        {"symbol": "AAA", "target_weight": 0.0, "action": "SELL"},
        {"symbol": "BBB", "target_weight": 100.0, "action": "BUY"},
    ]
    prices = {"AAA": 100.0, "BBB": 50.0}
    holdings, cash = _resolve_shares_from_weights(allocs, 1_000_000.0, prices)

    aaa = next(h for h in holdings if h["symbol"] == "AAA")
    assert aaa["shares"] == 0.0
    assert cash == pytest.approx(0.0)
    equity, _ = _compute_paper_value(holdings, prices)
    assert equity + cash == pytest.approx(1_000_000.0)


def test_full_liquidation_is_all_cash():
    holdings, cash = _resolve_shares_from_weights([], 1_000_000.0, {})
    assert holdings == []
    assert cash == pytest.approx(1_000_000.0)


def test_over_allocated_weights_clamp_cash_to_zero_never_negative():
    """Weights summing fractionally over 100% (rounding upstream) must not
    produce negative cash — clamp to 0 rather than fabricate a short cash
    position."""
    allocs = [
        {"symbol": "AAA", "target_weight": 60.03, "action": "BUY"},
        {"symbol": "BBB", "target_weight": 40.02, "action": "BUY"},
    ]
    prices = {"AAA": 100.0, "BBB": 100.0}
    holdings, cash = _resolve_shares_from_weights(allocs, 1_000_000.0, prices)
    assert cash == 0.0


# ─── assert_nav_conserved / NavInvariantError (unit, no DB) ────────────────

def test_assert_nav_conserved_passes_when_consistent():
    assert_nav_conserved(label="unit-test", expected_nav=1_000_000.0, equity=950_000.0, cash=50_000.0)


def test_assert_nav_conserved_raises_on_violation():
    with pytest.raises(NavInvariantError):
        assert_nav_conserved(label="unit-test", expected_nav=1_000_000.0, equity=900_000.0, cash=50_000.0)


def test_assert_nav_conserved_tolerates_floating_point_rounding():
    # 1e-9-scale floating point noise must not trip the invariant.
    assert_nav_conserved(label="unit-test", expected_nav=1_000_000.0, equity=949_999.9999999, cash=50_000.0000001)


# ─── DB-backed fixtures (mirrors test_ideal_series.py conventions) ─────────

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


def _seed_recommendation(db, ws, portfolio, allocations, total_portfolio_value=1_000_000.0, days_ago=0):
    from models.database import OptimizerHistory, RecommendationSnapshot

    oh = OptimizerHistory(
        workspace_id=ws.id, portfolio_id=portfolio.id, portfolio_name=portfolio.name,
        analyzed_at=datetime.utcnow(), swap_count=0,
        result_json=json.dumps({"target_allocations": allocations, "cash_balance": 0.0}),
    )
    db.add(oh)
    db.commit()
    db.refresh(oh)

    snap = RecommendationSnapshot(
        workspace_id=ws.id, optimizer_history_id=oh.id, portfolio_id=portfolio.id,
        total_portfolio_value=total_portfolio_value,
        projected_allocations_json=json.dumps(allocations),
        created_at=datetime.utcnow() - timedelta(days=days_ago),
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return snap


def _seed_price_snapshot(db, ws, portfolio, prices: dict, days_ago=0):
    from models.database import PortfolioSnapshot

    holdings = [{"symbol": sym, "current_price": p} for sym, p in prices.items()]
    db.add(PortfolioSnapshot(
        workspace_id=ws.id, portfolio_id=portfolio.id,
        snapshot_date=(date.today() - timedelta(days=days_ago)).isoformat(),
        total_value=1_000_000.0, cash_balance=0.0,
        holdings_json=json.dumps(holdings),
    ))
    db.commit()


_ALLOCS_95PCT = [
    {"symbol": "AAA", "target_weight": 50.0, "action": "BUY"},
    {"symbol": "BBB", "target_weight": 45.0, "action": "BUY"},
]
_ALLOCS_97PCT = [
    {"symbol": "AAA", "target_weight": 50.0, "action": "HOLD"},
    {"symbol": "BBB", "target_weight": 47.0, "action": "BUY"},
]
_ALLOCS_FULL_LIQUIDATION: list[dict] = []


def test_create_active_model_shadow_first_creation_persists_cash(db, ws_portfolio):
    from models.database import ShadowPortfolio

    ws, portfolio = ws_portfolio
    _seed_price_snapshot(db, ws, portfolio, {"AAA": 100.0, "BBB": 100.0})
    snap = _seed_recommendation(db, ws, portfolio, _ALLOCS_95PCT)

    result = create_active_model_shadow(db, portfolio.id, snap.id, ws.id)
    assert result["action"] == "created"

    shadow = db.query(ShadowPortfolio).filter_by(id=result["shadow_id"]).first()
    assert shadow.paper_cash_balance == pytest.approx(50_000.0)


def test_create_active_model_shadow_multiple_rebalances_no_price_movement_conserves_nav(db, ws_portfolio):
    """The direct regression test for the compounding cash-leak defect.

    Three consecutive rebalances (95% deployed -> 97% deployed -> full
    liquidation), flat prices throughout (no market movement). Pre-fix, each
    rebalance would have silently discarded its residual, compounding to
    roughly 0.95 * ~0.97 * ... of the true NAV. Post-fix, NAV must be
    IDENTICAL to the inception value after every single rebalance, because
    cash is carried forward exactly rather than dropped.
    """
    from models.database import ShadowPortfolio

    ws, portfolio = ws_portfolio
    _seed_price_snapshot(db, ws, portfolio, {"AAA": 100.0, "BBB": 100.0})

    snap1 = _seed_recommendation(db, ws, portfolio, _ALLOCS_95PCT, total_portfolio_value=1_000_000.0)
    r1 = create_active_model_shadow(db, portfolio.id, snap1.id, ws.id)
    shadow = db.query(ShadowPortfolio).filter_by(id=r1["shadow_id"]).first()
    assert shadow.paper_cash_balance == pytest.approx(50_000.0)

    snap2 = _seed_recommendation(db, ws, portfolio, _ALLOCS_97PCT)
    r2 = create_active_model_shadow(db, portfolio.id, snap2.id, ws.id)
    assert r2["running_nav"] == pytest.approx(1_000_000.0, abs=0.5)
    db.refresh(shadow)
    assert shadow.paper_cash_balance == pytest.approx(30_000.0, abs=0.5)

    snap3 = _seed_recommendation(db, ws, portfolio, _ALLOCS_FULL_LIQUIDATION)
    r3 = create_active_model_shadow(db, portfolio.id, snap3.id, ws.id)
    assert r3["running_nav"] == pytest.approx(1_000_000.0, abs=0.5)
    db.refresh(shadow)
    # Fully liquidated: every dollar is now cash, and it is still the full NAV.
    assert shadow.paper_cash_balance == pytest.approx(1_000_000.0, abs=0.5)
    assert json.loads(shadow.inception_holdings_json) == []


def test_create_static_frozen_shadow_persists_cash_for_partial_weights(db, ws_portfolio):
    from models.database import UserExecutionDecision, ShadowPortfolio

    ws, portfolio = ws_portfolio
    _seed_price_snapshot(db, ws, portfolio, {"AAA": 100.0, "BBB": 100.0})
    snap = _seed_recommendation(db, ws, portfolio, _ALLOCS_95PCT)

    decision = UserExecutionDecision(
        workspace_id=ws.id, portfolio_id=portfolio.id,
        recommendation_snapshot_id=snap.id, decision="APPROVED",
        created_at=datetime.utcnow(),
    )
    db.add(decision)
    db.commit()
    db.refresh(decision)

    result = create_static_frozen_shadow(db, decision.id, ws.id)
    shadow = db.query(ShadowPortfolio).filter_by(id=result["shadow_id"]).first()
    assert shadow.paper_cash_balance == pytest.approx(50_000.0)


def test_create_recommendation_shadow_persists_cash_for_partial_weights(db, ws_portfolio):
    from models.database import ShadowPortfolio

    ws, portfolio = ws_portfolio
    _seed_price_snapshot(db, ws, portfolio, {"AAA": 100.0, "BBB": 100.0})
    snap = _seed_recommendation(db, ws, portfolio, _ALLOCS_95PCT)

    result = create_recommendation_shadow(db, snap.id, ws.id)
    shadow = db.query(ShadowPortfolio).filter_by(id=result["shadow_id"]).first()
    assert shadow.paper_cash_balance == pytest.approx(50_000.0)
