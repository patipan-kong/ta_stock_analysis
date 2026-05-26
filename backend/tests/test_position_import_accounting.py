"""Tests for position-import accounting correctness.

Verifies that manually imported positions, position corrections, and
onboarding events are NEVER counted as investment performance.

All tests use an in-memory SQLite database so no external services are needed.
The snapshot engine is called directly — no HTTP layer involved.

Key invariant: the portfolio's actual cash + equity must equal prev_nav
before the event under test fires, otherwise the formula baseline is wrong.

Event classification under test:
  INITIAL_POSITION  → imported_asset_value  (must not increase investment_return_pct)
  INITIAL_CASH      → net_external_cash_flow (must not increase investment_return_pct)
  DEPOSIT           → net_external_cash_flow (regression guard)
  BUY / SELL        → performance events (must affect return normally)
"""
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base, Portfolio, PortfolioItem, PortfolioSnapshot, Transaction, Workspace
from services.portfolio_transactions import (
    execute_initial_position,
    execute_initial_cash,
    execute_deposit,
    execute_buy,
    execute_quantity_correction,
)

# ── Test DB setup ──────────────────────────────────────────────────────────────

def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _seed(db, cash=0.0):
    ws = Workspace(name="Test")
    db.add(ws)
    db.flush()
    p = Portfolio(workspace_id=ws.id, name="Test", cash_balance=cash)
    db.add(p)
    db.commit()
    return ws, p


def _prev_snapshot(db, portfolio_id, workspace_id, date_str, total_value):
    """Insert a previous snapshot row directly (no price fetch)."""
    snap = PortfolioSnapshot(
        workspace_id=workspace_id,
        portfolio_id=portfolio_id,
        snapshot_date=date_str,
        total_value=total_value,
        cash_balance=0.0,
        total_invested=total_value,
    )
    db.add(snap)
    db.commit()
    return snap


def _prev_date():
    return (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")


def _today():
    return datetime.utcnow().strftime("%Y-%m-%d")


# ── Snapshot runner ────────────────────────────────────────────────────────────

def run_snapshot(db, portfolio_id, workspace_id, today_str, price_map):
    """Run generate_daily_snapshot synchronously with a mocked price fetch."""
    import asyncio
    from services.portfolio_snapshots import generate_daily_snapshot

    async def _go():
        with patch(
            "services.portfolio_snapshots.fetch_price_info",
            side_effect=lambda sym: {"current_price": price_map.get(sym, 0.0)},
        ):
            return await generate_daily_snapshot(db, portfolio_id, workspace_id, today_str)

    return asyncio.get_event_loop().run_until_complete(_go())


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_import_does_not_create_return():
    """INITIAL_POSITION import must not generate investment return.

    Scenario: portfolio holds 100k cash (prev snapshot NAV = 100k).
    User imports 1,000 SCB.BK shares (avg_cost 190, current price 200).
    INITIAL_POSITION does not reduce cash, so:
        today_nav = 100k cash + 200k equity = 300k
        change    = +200k
        imported_asset_value = 1000 × 200 = 200k
        pure_market_gain = 300k - 100k - 200k = 0  →  return = 0%
    """
    db = make_session()
    ws, p = _seed(db, cash=100_000.0)   # actual cash matches prev_nav
    _prev_snapshot(db, p.id, ws.id, _prev_date(), 100_000.0)

    execute_initial_position(db, ws.id, p.id, "SCB.BK", shares=1000, avg_cost=190.0)

    result = run_snapshot(db, p.id, ws.id, _today(), {"SCB.BK": 200.0})

    assert result["imported_asset_value"] == pytest.approx(200_000.0, abs=1)
    assert result["investment_return_pct"] == pytest.approx(0.0, abs=0.01)
    assert result["investment_return_amount"] == pytest.approx(0.0, abs=1)


def test_initial_cash_excluded_from_return():
    """INITIAL_CASH must be treated as an onboarding deposit and excluded from return.

    Scenario: portfolio holds 50k cash (prev snapshot NAV = 50k).
    User runs initial-cash to record another 50k onboarding balance.
        today_nav = 100k cash
        net_external_cash_flow = 50k (INITIAL_CASH treated as inflow)
        pure_market_gain = 100k - 50k - 50k = 0  →  return = 0%
    """
    db = make_session()
    ws, p = _seed(db, cash=50_000.0)
    _prev_snapshot(db, p.id, ws.id, _prev_date(), 50_000.0)

    execute_initial_cash(db, ws.id, p.id, amount=50_000.0)

    result = run_snapshot(db, p.id, ws.id, _today(), {})

    assert result["net_external_cash_flow"] == pytest.approx(50_000.0, abs=1)
    assert result["investment_return_pct"] == pytest.approx(0.0, abs=0.01)


def test_deposit_regression_still_excluded():
    """DEPOSIT exclusion (pre-existing behaviour) must not regress.

    Scenario: portfolio holds 100k cash. User deposits 22k.
        today_nav = 122k
        net_external_cash_flow = 22k
        pure_market_gain = 122k - 100k - 22k = 0  →  return = 0%
    """
    db = make_session()
    ws, p = _seed(db, cash=100_000.0)
    _prev_snapshot(db, p.id, ws.id, _prev_date(), 100_000.0)

    execute_deposit(db, ws.id, p.id, amount=22_000.0)

    result = run_snapshot(db, p.id, ws.id, _today(), {})

    assert result["net_external_cash_flow"] == pytest.approx(22_000.0, abs=1)
    assert result["investment_return_pct"] == pytest.approx(0.0, abs=0.01)


def test_mixed_import_and_market_gain():
    """Only genuine market movement should appear in investment_return_pct.

    Scenario: portfolio holds 500 XYZ.BK @ cost 100 = 50k equity; prev NAV = 50k.
    XYZ.BK rises from 100 to 102 → market gain = 500 × 2 = 1,000.
    User also imports 200 ABC.BK @ avg_cost 50; current price 60.
        today_nav = 500×102 + 200×60 = 51,000 + 12,000 = 63,000
        change = 63,000 - 50,000 = 13,000
        imported_asset_value = 200 × 60 = 12,000
        pure_market_gain = 63,000 - 50,000 - 12,000 = 1,000
        investment_return_pct = 1,000 / 50,000 = 2.0%
    """
    db = make_session()
    ws, p = _seed(db, cash=0.0)

    existing = PortfolioItem(
        workspace_id=ws.id, portfolio_id=p.id,
        symbol="XYZ.BK", shares=500, avg_cost=100.0,
    )
    db.add(existing)
    db.commit()

    # prev snapshot: only XYZ.BK at old price 100 → NAV = 50k
    _prev_snapshot(db, p.id, ws.id, _prev_date(), 50_000.0)

    # Import ABC.BK AFTER prev snapshot
    execute_initial_position(db, ws.id, p.id, "ABC.BK", shares=200, avg_cost=50.0)

    result = run_snapshot(db, p.id, ws.id, _today(), {"XYZ.BK": 102.0, "ABC.BK": 60.0})

    assert result["imported_asset_value"] == pytest.approx(12_000.0, abs=1)
    assert result["investment_return_pct"] == pytest.approx(2.0, abs=0.05)
    assert result["investment_return_amount"] == pytest.approx(1_000.0, abs=5)


def test_quantity_correction_upward_excluded():
    """A follow-up INITIAL_POSITION that increases shares is a correction, not a gain.

    Scenario: portfolio holds 500 SCB.BK @ 190; prev NAV = 500×190 = 95k.
    User forgot to log 500 more shares; imports them (correction).
    Current price stays at 190 (no market movement).
        today_nav = 1000×190 = 190k
        change = 190k - 95k = 95k
        imported_asset_value = 500 × 190 = 95k
        pure_market_gain = 190k - 95k - 95k = 0  →  return = 0%
    """
    db = make_session()
    ws, p = _seed(db, cash=0.0)

    item = PortfolioItem(
        workspace_id=ws.id, portfolio_id=p.id,
        symbol="SCB.BK", shares=500, avg_cost=190.0,
    )
    db.add(item)
    db.commit()

    _prev_snapshot(db, p.id, ws.id, _prev_date(), 95_000.0)

    # Correction: import the missing 500 shares
    execute_initial_position(db, ws.id, p.id, "SCB.BK", shares=500, avg_cost=190.0)

    result = run_snapshot(db, p.id, ws.id, _today(), {"SCB.BK": 190.0})

    assert result["imported_asset_value"] == pytest.approx(95_000.0, abs=100)
    assert result["investment_return_pct"] == pytest.approx(0.0, abs=0.1)


def test_backdated_import_still_excluded():
    """INITIAL_POSITION with a historical transaction_date must still be stripped.

    This is the primary regression this test suite guards against.
    A user can record an import with transaction_date set to the original
    purchase date (e.g. 2024-03-01).  The snapshot engine must use
    Transaction.created_at (the physical insert time) for window detection,
    NOT transaction_date.  Without this fix the import falls outside the
    prev_snapshot → today window and appears as investment gain.

    Scenario: portfolio holds 100k cash; prev snapshot NAV = 100k.
    User imports 1,000 SCB.BK with transaction_date backdated two years.
    Expected: invested_return_pct = 0% (import stripped via created_at).
    """
    db = make_session()
    ws, p = _seed(db, cash=100_000.0)
    _prev_snapshot(db, p.id, ws.id, _prev_date(), 100_000.0)

    # Backdate to two years ago — this would escape the window if the engine
    # incorrectly filtered by transaction_date.
    two_years_ago = datetime.utcnow() - timedelta(days=730)
    execute_initial_position(
        db, ws.id, p.id, "SCB.BK",
        shares=1000, avg_cost=140.0,
        transaction_date=two_years_ago,
    )

    result = run_snapshot(db, p.id, ws.id, _today(), {"SCB.BK": 200.0})

    # imported_asset_value = 1000 × 200 = 200k (detected via created_at, not transaction_date)
    assert result["imported_asset_value"] == pytest.approx(200_000.0, abs=1)
    assert result["investment_return_pct"] == pytest.approx(0.0, abs=0.01)
    assert result["investment_return_amount"] == pytest.approx(0.0, abs=1)


def test_quantity_correction_excluded():
    """QUANTITY_CORRECTION must be excluded from investment_return_pct.

    Scenario: portfolio holds 500 SCB.BK @ 190; prev NAV = 95k.
    User corrects the share count by +200 via QUANTITY_CORRECTION.
    Price is 200 (market moved +10 since last snapshot).
        today_nav    = 700 × 200 = 140k
        market gain  = 500 × (200 - 190) = 5k  (pre-existing 500 shares)
        correction   = 200 × 200 = 40k  (must be stripped)
        pure_gain    = 140k - 95k - 40k = 5k
        return_pct   = 5k / 95k ≈ 5.26%
    """
    db = make_session()
    ws, p = _seed(db, cash=0.0)

    item = PortfolioItem(
        workspace_id=ws.id, portfolio_id=p.id,
        symbol="SCB.BK", shares=500, avg_cost=190.0,
    )
    db.add(item)
    db.commit()

    _prev_snapshot(db, p.id, ws.id, _prev_date(), 95_000.0)

    execute_quantity_correction(
        db, ws.id, p.id, "SCB.BK",
        shares_delta=200, price_per_share=200.0,
    )

    result = run_snapshot(db, p.id, ws.id, _today(), {"SCB.BK": 200.0})

    assert result["manual_adjustment_value"] == pytest.approx(40_000.0, abs=1)
    expected_return = 5_000.0 / 95_000.0 * 100
    assert result["investment_return_pct"] == pytest.approx(expected_return, abs=0.1)
    assert result["investment_return_amount"] == pytest.approx(5_000.0, abs=10)


def test_buy_transaction_is_performance_event():
    """A BUY is a market trade — cash exits, equity enters; net NAV effect ≈ 0.
    Only subsequent price appreciation is performance.

    Scenario: portfolio holds 100k cash; prev NAV = 100k.
    BUY 100 AAPL @ 100 (−10k cash, +10k equity → NAV stays 100k).
    Price rises to 110 by snapshot time.
        today_nav = 90k cash + 11k equity = 101k
        investment_return_pct = 1,000 / 100,000 = 1.0%
        imported_asset_value = None / 0
    """
    db = make_session()
    ws, p = _seed(db, cash=100_000.0)
    _prev_snapshot(db, p.id, ws.id, _prev_date(), 100_000.0)

    execute_buy(db, ws.id, p.id, "AAPL", shares=100, price_per_share=100.0)

    result = run_snapshot(db, p.id, ws.id, _today(), {"AAPL": 110.0})

    assert (result["imported_asset_value"] or 0.0) == pytest.approx(0.0, abs=1)
    # 90,000 cash + 11,000 equity = 101,000; gain = 1,000; return = 1%
    assert result["investment_return_pct"] == pytest.approx(1.0, abs=0.05)
