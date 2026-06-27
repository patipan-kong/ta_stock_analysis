"""Tests for the snapshot return recovery engine.

Scenarios covered
-----------------
 1. Baseline snapshot  → all return fields are None (no previous NAV)
 2. Single DEPOSIT     → net_external_cash_flow stripped; investment_return_pct correct
 3. WITHDRAW           → reduces net_external_cash_flow
 4. INITIAL_CASH       → treated as inflow (same as DEPOSIT)
 5. INITIAL_POSITION   → creates imported_asset_value; return stripped accordingly
 6. QUANTITY_CORRECTION → creates manual_adjustment_value
 7. SELL transaction   → period_realized_pnl from notes; SELL fees in period_fees_paid
 8. DIVIDEND           → period_dividend_income
 9. BUY fees           → period_fees_paid
10. Bookkeeping on baseline day excluded from next window (Portfolio-2 scenario)
11. Portfolio-4 repaired baseline: first snapshot has None, second computes correctly
12. Dry run            → values computed, DB untouched
13. No-op              → already-correct fields produce unchanged=True
14. Idempotency        → running twice yields identical results
15. Rollback           → caller controls commit; partial writes safe
16. Multi-portfolio    → recover_all handles each portfolio independently
17. Unknown portfolio  → returns error result
18. Empty portfolio    → 0 snapshots scanned, no error
"""
from __future__ import annotations

import json
import sys
import os
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import (
    Base, Portfolio, PortfolioItem, PortfolioSnapshot, Transaction, Workspace,
)
from services.snapshot_return_recovery import (
    PortfolioReturnRecoveryResult,
    SnapshotReturnDiff,
    _RETURN_FIELDS,
    recover_all_snapshot_returns,
    recover_portfolio_snapshot_returns,
)


# ── DB helpers ─────────────────────────────────────────────────────────────────

def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _seed(db, cash: float = 0.0, name: str = "Test") -> tuple:
    ws = Workspace(name="TestWS")
    db.add(ws)
    db.flush()
    p = Portfolio(workspace_id=ws.id, name=name, cash_balance=cash)
    db.add(p)
    db.commit()
    return ws, p


def _snap(
    db,
    portfolio_id: int,
    workspace_id: int,
    date: str,
    total_value: float,
    cash_balance: float = 0.0,
    *,
    investment_return_pct: float | None = None,
    daily_return_pct: float | None = None,
    investment_return_amount: float | None = None,
    net_external_cash_flow: float | None = None,
    imported_asset_value: float | None = None,
    manual_adjustment_value: float | None = None,
    period_realized_pnl: float | None = None,
    period_dividend_income: float | None = None,
    period_fees_paid: float | None = None,
) -> PortfolioSnapshot:
    s = PortfolioSnapshot(
        workspace_id           = workspace_id,
        portfolio_id           = portfolio_id,
        snapshot_date          = date,
        total_value            = total_value,
        cash_balance           = cash_balance,
        total_invested         = total_value - cash_balance,
        investment_return_pct  = investment_return_pct,
        daily_return_pct       = daily_return_pct,
        investment_return_amount = investment_return_amount,
        net_external_cash_flow = net_external_cash_flow,
        imported_asset_value   = imported_asset_value,
        manual_adjustment_value = manual_adjustment_value,
        period_realized_pnl    = period_realized_pnl,
        period_dividend_income = period_dividend_income,
        period_fees_paid       = period_fees_paid,
    )
    db.add(s)
    db.commit()
    return s


def _tx(
    db,
    portfolio_id: int,
    workspace_id: int,
    tx_type: str,
    total_amount: float,
    created_at: datetime,
    *,
    symbol: str | None = None,
    shares: float | None = None,
    price_per_share: float | None = None,
    fees: float = 0.0,
    taxes: float = 0.0,
    notes: str | None = None,
) -> Transaction:
    t = Transaction(
        workspace_id      = workspace_id,
        portfolio_id      = portfolio_id,
        transaction_type  = tx_type,
        total_amount      = total_amount,
        symbol            = symbol,
        shares            = shares,
        price_per_share   = price_per_share,
        fees              = fees,
        taxes             = taxes,
        transaction_date  = created_at,
        created_at        = created_at,
        notes             = notes,
    )
    db.add(t)
    db.commit()
    return t


def _d(offset: int) -> str:
    """Return a date string N days before today."""
    return (datetime.utcnow() - timedelta(days=offset)).strftime("%Y-%m-%d")


def _dt(offset: int) -> datetime:
    """Return midnight UTC N days before today."""
    base = datetime.utcnow() - timedelta(days=offset)
    return base.replace(hour=0, minute=0, second=0, microsecond=0)


# ── Test 1: Baseline snapshot has all-None return fields ──────────────────────

def test_baseline_snapshot_returns_none():
    """The first snapshot (no prev) must always produce None for every return field."""
    db = make_session()
    ws, p = _seed(db)
    _snap(db, p.id, ws.id, _d(5), 100_000.0, cash_balance=100_000.0,
          investment_return_pct=99.0)  # wrong value that should become None

    result = recover_portfolio_snapshot_returns(db, p.id, ws.id, dry_run=True)

    assert result.snapshots_scanned == 1
    assert len(result.diffs) == 1
    diff = result.diffs[0]
    for f in _RETURN_FIELDS:
        assert diff.new_values[f] is None, f"{f} should be None for baseline"


# ── Test 2: DEPOSIT is stripped from returns ──────────────────────────────────

def test_deposit_stripped_from_investment_return():
    """A DEPOSIT in the period increases NAV but must not inflate investment_return_pct."""
    db = make_session()
    ws, p = _seed(db)

    d0, d1 = _d(3), _d(2)
    _snap(db, p.id, ws.id, d0, 100_000.0, cash_balance=100_000.0)
    _snap(db, p.id, ws.id, d1, 122_000.0, cash_balance=122_000.0)  # +22k NAV

    # DEPOSIT of 22,000 happens between d0 and d1
    _tx(db, p.id, ws.id, "DEPOSIT", 22_000.0, _dt(2) + timedelta(hours=10))

    result = recover_portfolio_snapshot_returns(db, p.id, ws.id, dry_run=True)
    d1_diff = result.diffs[1]

    # pure_market_gain = 122,000 − 100,000 − 22,000 = 0
    assert d1_diff.new_values["investment_return_pct"]    == pytest.approx(0.0, abs=1e-4)
    assert d1_diff.new_values["investment_return_amount"] == pytest.approx(0.0, abs=0.01)
    assert d1_diff.new_values["net_external_cash_flow"]   == pytest.approx(22_000.0, abs=0.01)
    assert d1_diff.new_values["daily_return_pct"]         == pytest.approx(0.0, abs=1e-4)


# ── Test 3: WITHDRAW reduces net_external_cash_flow ──────────────────────────

def test_withdraw_reduces_net_external_cash_flow():
    """A WITHDRAW subtracts from net_external_cash_flow."""
    db = make_session()
    ws, p = _seed(db)

    d0, d1 = _d(3), _d(2)
    _snap(db, p.id, ws.id, d0, 100_000.0, cash_balance=100_000.0)
    _snap(db, p.id, ws.id, d1,  95_000.0, cash_balance=95_000.0)

    _tx(db, p.id, ws.id, "WITHDRAW", 5_000.0, _dt(2) + timedelta(hours=10))

    result = recover_portfolio_snapshot_returns(db, p.id, ws.id, dry_run=True)
    d1_diff = result.diffs[1]

    # pure_market_gain = 95,000 − 100,000 − (0 − 5,000) = 0
    assert d1_diff.new_values["net_external_cash_flow"] == pytest.approx(-5_000.0, abs=0.01)
    assert d1_diff.new_values["investment_return_pct"]  == pytest.approx(0.0, abs=1e-4)


# ── Test 4: INITIAL_CASH treated as inflow ────────────────────────────────────

def test_initial_cash_treated_as_inflow():
    """INITIAL_CASH is in _CASH_INFLOW_TYPES and must be stripped the same as DEPOSIT."""
    db = make_session()
    ws, p = _seed(db)

    d0, d1 = _d(3), _d(2)
    _snap(db, p.id, ws.id, d0, 50_000.0, cash_balance=50_000.0)
    _snap(db, p.id, ws.id, d1, 60_000.0, cash_balance=60_000.0)

    _tx(db, p.id, ws.id, "INITIAL_CASH", 10_000.0, _dt(2) + timedelta(hours=6))

    result = recover_portfolio_snapshot_returns(db, p.id, ws.id, dry_run=True)
    d1_diff = result.diffs[1]

    assert d1_diff.new_values["net_external_cash_flow"] == pytest.approx(10_000.0, abs=0.01)
    assert d1_diff.new_values["investment_return_pct"]  == pytest.approx(0.0, abs=1e-4)


# ── Test 5: INITIAL_POSITION creates imported_asset_value ─────────────────────

def test_initial_position_stripped_as_imported_asset_value():
    """An INITIAL_POSITION import must create imported_asset_value so the equity
    injection does not inflate investment_return_pct."""
    db = make_session()
    ws, p = _seed(db)

    d0, d1 = _d(4), _d(3)
    prev_nav  = 100_000.0
    import_mv = 200 * 50.0  # 10,000

    _snap(db, p.id, ws.id, d0, prev_nav, cash_balance=prev_nav)
    _snap(db, p.id, ws.id, d1, prev_nav + import_mv, cash_balance=prev_nav)

    _tx(
        db, p.id, ws.id, "INITIAL_POSITION", import_mv,
        _dt(3) + timedelta(hours=8),
        symbol="SCB.BK", shares=200.0, price_per_share=50.0,
    )

    result = recover_portfolio_snapshot_returns(db, p.id, ws.id, dry_run=True)
    d1_diff = result.diffs[1]

    assert d1_diff.new_values["imported_asset_value"]     == pytest.approx(import_mv, abs=0.01)
    assert d1_diff.new_values["investment_return_pct"]    == pytest.approx(0.0, abs=1e-4)
    assert d1_diff.new_values["net_external_cash_flow"]   is None


# ── Test 6: QUANTITY_CORRECTION creates manual_adjustment_value ───────────────

def test_quantity_correction_creates_manual_adjustment_value():
    """A share-count correction must create manual_adjustment_value and not
    inflate investment_return_pct."""
    db = make_session()
    ws, p = _seed(db)

    d0, d1 = _d(3), _d(2)
    adj_mv = 50 * 100.0  # 5,000
    _snap(db, p.id, ws.id, d0, 200_000.0)
    _snap(db, p.id, ws.id, d1, 205_000.0)

    _tx(
        db, p.id, ws.id, "QUANTITY_CORRECTION", adj_mv,
        _dt(2) + timedelta(hours=9),
        symbol="AOT.BK", shares=50.0, price_per_share=100.0,
    )

    result = recover_portfolio_snapshot_returns(db, p.id, ws.id, dry_run=True)
    d1_diff = result.diffs[1]

    assert d1_diff.new_values["manual_adjustment_value"] == pytest.approx(adj_mv, abs=0.01)
    assert d1_diff.new_values["investment_return_pct"]   == pytest.approx(0.0, abs=1e-4)


# ── Test 7: SELL transaction produces period_realized_pnl and fees ────────────

def test_sell_transaction_period_realized_pnl_and_fees():
    """A SELL with notes containing 'Realized P&L: +1500' must be reflected
    in period_realized_pnl; fees+taxes in period_fees_paid."""
    db = make_session()
    ws, p = _seed(db)

    d0, d1 = _d(3), _d(2)
    _snap(db, p.id, ws.id, d0, 100_000.0)
    _snap(db, p.id, ws.id, d1, 101_200.0)  # small NAV rise

    _tx(
        db, p.id, ws.id, "SELL", 15_000.0,
        _dt(2) + timedelta(hours=11),
        symbol="PTT.BK", shares=100.0, price_per_share=150.0,
        fees=100.0, taxes=7.0,
        notes="Sell 100 PTT.BK @ 150. Realized P&L: +1500.00",
    )

    result = recover_portfolio_snapshot_returns(db, p.id, ws.id, dry_run=True)
    d1_diff = result.diffs[1]

    assert d1_diff.new_values["period_realized_pnl"] == pytest.approx(1500.0, abs=0.01)
    assert d1_diff.new_values["period_fees_paid"]    == pytest.approx(107.0,  abs=0.01)


# ── Test 8: DIVIDEND creates period_dividend_income ──────────────────────────

def test_dividend_creates_period_dividend_income():
    """A DIVIDEND transaction must set period_dividend_income."""
    db = make_session()
    ws, p = _seed(db)

    d0, d1 = _d(3), _d(2)
    _snap(db, p.id, ws.id, d0, 100_000.0)
    _snap(db, p.id, ws.id, d1, 100_500.0)

    _tx(db, p.id, ws.id, "DIVIDEND", 500.0, _dt(2) + timedelta(hours=14))

    result = recover_portfolio_snapshot_returns(db, p.id, ws.id, dry_run=True)
    d1_diff = result.diffs[1]

    assert d1_diff.new_values["period_dividend_income"] == pytest.approx(500.0, abs=0.01)
    # Dividend is market income — NOT stripped from returns
    assert d1_diff.new_values["investment_return_pct"] == pytest.approx(0.5, abs=1e-3)


# ── Test 9: BUY fees accumulate in period_fees_paid ──────────────────────────

def test_buy_fees_accumulate_in_period_fees_paid():
    """BUY transaction fees + taxes must be included in period_fees_paid."""
    db = make_session()
    ws, p = _seed(db)

    d0, d1 = _d(3), _d(2)
    _snap(db, p.id, ws.id, d0, 100_000.0)
    _snap(db, p.id, ws.id, d1,  99_800.0)

    _tx(
        db, p.id, ws.id, "BUY", 10_000.0,
        _dt(2) + timedelta(hours=10),
        symbol="KBANK.BK", shares=100.0, price_per_share=100.0,
        fees=150.0, taxes=10.5,
    )

    result = recover_portfolio_snapshot_returns(db, p.id, ws.id, dry_run=True)
    d1_diff = result.diffs[1]

    assert d1_diff.new_values["period_fees_paid"] == pytest.approx(160.5, abs=0.01)


# ── Test 10: Portfolio-2 scenario — bookkeeping on baseline day excluded ───────

def test_bookkeeping_transactions_on_baseline_day_excluded_from_next_window():
    """INITIAL_CASH and INITIAL_POSITION created on Day-0 (baseline day) must NOT
    appear in the return computation for Day-1 because:
      - window is  created_at >= end_of_Day-0
      - Day-0 transactions have created_at  < end_of_Day-0  → excluded

    This matches the Portfolio-2 forensic finding: setup transactions were
    created at the same time as the baseline snapshot, so they should already
    be captured in the baseline NAV and must not distort the next period's
    return.
    """
    db = make_session()
    ws, p = _seed(db)

    baseline_date = _d(3)
    next_date     = _d(2)

    # Baseline NAV includes INITIAL_CASH + INITIAL_POSITION injected on Day-0
    baseline_nav = 100_000.0 + 20_000.0  # 120,000

    _snap(db, p.id, ws.id, baseline_date, baseline_nav, cash_balance=100_000.0)

    # Pure market gain the next day: NAV rises by 1,200 (1 %).
    # Cash is unchanged (no cash transactions on next_date) → realistic cash_balance.
    _snap(db, p.id, ws.id, next_date, baseline_nav + 1_200.0, cash_balance=100_000.0)

    # Bookkeeping transactions created on Day-0 (baseline day)
    _tx(db, p.id, ws.id, "INITIAL_CASH",     100_000.0, _dt(3) + timedelta(hours=9))
    _tx(
        db, p.id, ws.id, "INITIAL_POSITION",  20_000.0, _dt(3) + timedelta(hours=9),
        symbol="AOT.BK", shares=200.0, price_per_share=100.0,
    )

    result = recover_portfolio_snapshot_returns(db, p.id, ws.id, dry_run=True)
    baseline_diff = result.diffs[0]
    next_diff     = result.diffs[1]

    # Baseline: all None
    for f in _RETURN_FIELDS:
        assert baseline_diff.new_values[f] is None, f"baseline {f} should be None"

    # Next day: bookkeeping transactions are NOT in the window → not stripped
    # Return = 1,200 / 121,200 ≈ 0.9901 %
    expected_return = round(1_200.0 / baseline_nav * 100, 4)
    assert next_diff.new_values["investment_return_pct"]  == pytest.approx(expected_return, abs=1e-3)
    assert next_diff.new_values["net_external_cash_flow"] is None
    assert next_diff.new_values["imported_asset_value"]   is None


# ── Test 11: Portfolio-4 repaired baseline scenario ───────────────────────────

def test_portfolio4_repaired_baseline_two_snapshot_chain():
    """After snapshot_repair.py has fixed the NAV values, the return engine
    correctly computes performance from the repaired chain.

    Scenario:
      Snap-0 (baseline): NAV = 200,000  → all return fields = None
      Snap-1 (day+1):    NAV = 202,000  → return = +1.0%, no cash events
    """
    db = make_session()
    ws, p = _seed(db)

    d0, d1 = _d(5), _d(4)
    _snap(db, p.id, ws.id, d0, 200_000.0)
    _snap(db, p.id, ws.id, d1, 202_000.0)

    result = recover_portfolio_snapshot_returns(db, p.id, ws.id, dry_run=True)

    assert result.diffs[0].new_values["investment_return_pct"] is None
    assert result.diffs[1].new_values["investment_return_pct"] == pytest.approx(1.0, abs=1e-4)
    assert result.diffs[1].new_values["net_external_cash_flow"] is None
    assert result.diffs[1].new_values["investment_return_amount"] == pytest.approx(2_000.0, abs=0.01)


# ── Test 12: Dry run does not write to DB ─────────────────────────────────────

def test_dry_run_does_not_write():
    """dry_run=True must leave every snapshot column unchanged."""
    db = make_session()
    ws, p = _seed(db)

    d0, d1 = _d(3), _d(2)
    _snap(db, p.id, ws.id, d0, 100_000.0)
    s1 = _snap(db, p.id, ws.id, d1, 110_000.0, investment_return_pct=99.0)

    result = recover_portfolio_snapshot_returns(db, p.id, ws.id, dry_run=True)
    assert result.snapshots_changed == 1

    # DB must not have been touched
    db.expire_all()
    unchanged = db.query(PortfolioSnapshot).filter_by(id=s1.id).first()
    assert unchanged.investment_return_pct == pytest.approx(99.0, abs=0.001)


# ── Test 13: No-op when fields are already correct ────────────────────────────

def test_noop_when_fields_already_correct():
    """A snapshot with the correct values already stored should be unchanged=True."""
    db = make_session()
    ws, p = _seed(db)

    d0, d1 = _d(3), _d(2)
    _snap(db, p.id, ws.id, d0, 100_000.0)

    # Pre-seed correct values
    expected_return_pct = round(5_000.0 / 100_000.0 * 100, 4)
    _snap(
        db, p.id, ws.id, d1, 105_000.0,
        investment_return_pct    = expected_return_pct,
        daily_return_pct         = expected_return_pct,
        investment_return_amount = 5_000.0,
        # All other fields None (no transactions)
    )

    result = recover_portfolio_snapshot_returns(db, p.id, ws.id)
    # baseline (d0) and d1 are both unchanged — 2 total
    assert result.snapshots_unchanged == 2
    assert result.snapshots_changed   == 0


# ── Test 14: Idempotency — running twice is identical ────────────────────────

def test_idempotency():
    """Running the recovery twice produces the same result as running it once."""
    db = make_session()
    ws, p = _seed(db)

    d0, d1, d2 = _d(5), _d(4), _d(3)
    _snap(db, p.id, ws.id, d0, 100_000.0, cash_balance=100_000.0)
    _snap(db, p.id, ws.id, d1, 122_000.0, cash_balance=122_000.0)
    # d2: no cash transactions → cash unchanged from d1
    _snap(db, p.id, ws.id, d2, 124_000.0, cash_balance=122_000.0)

    _tx(db, p.id, ws.id, "DEPOSIT", 22_000.0, _dt(4) + timedelta(hours=10))

    # First run — writes values
    r1 = recover_portfolio_snapshot_returns(db, p.id, ws.id, dry_run=False)
    db.commit()

    # Second run — should find everything already correct
    r2 = recover_portfolio_snapshot_returns(db, p.id, ws.id, dry_run=False)
    db.commit()

    assert r2.snapshots_changed   == 0
    assert r2.snapshots_unchanged == r1.snapshots_scanned


# ── Test 15: Rollback leaves DB unchanged on error ───────────────────────────

def test_rollback_on_failure():
    """When the caller rolls back after an error, no partial writes persist."""
    db = make_session()
    ws, p = _seed(db)

    d0, d1 = _d(3), _d(2)
    _snap(db, p.id, ws.id, d0, 100_000.0)
    s1 = _snap(db, p.id, ws.id, d1, 108_000.0, investment_return_pct=0.0)

    # Accumulate changes without committing
    recover_portfolio_snapshot_returns(db, p.id, ws.id, dry_run=False)

    # Simulate a failure — roll back instead of commit
    db.rollback()

    db.expire_all()
    unchanged = db.query(PortfolioSnapshot).filter_by(id=s1.id).first()
    # investment_return_pct should still be the original 0.0, not the newly computed 8.0
    assert unchanged.investment_return_pct == pytest.approx(0.0, abs=0.001)


# ── Test 16: recover_all handles multiple portfolios independently ─────────────

def test_recover_all_multiple_portfolios():
    """recover_all_snapshot_returns processes each portfolio separately."""
    db = make_session()
    ws = Workspace(name="WS")
    db.add(ws)
    db.flush()

    pA = Portfolio(workspace_id=ws.id, name="Alpha", cash_balance=0.0)
    pB = Portfolio(workspace_id=ws.id, name="Beta",  cash_balance=0.0)
    db.add_all([pA, pB])
    db.commit()

    d0, d1 = _d(3), _d(2)

    _snap(db, pA.id, ws.id, d0, 100_000.0)
    _snap(db, pA.id, ws.id, d1, 105_000.0)

    _snap(db, pB.id, ws.id, d0, 200_000.0)
    _snap(db, pB.id, ws.id, d1, 190_000.0)

    results = recover_all_snapshot_returns(db, ws.id, dry_run=True)

    assert len(results) == 2
    assert results[0].portfolio_id == pA.id
    assert results[1].portfolio_id == pB.id

    alpha_d1 = results[0].diffs[1]
    beta_d1  = results[1].diffs[1]

    assert alpha_d1.new_values["investment_return_pct"] == pytest.approx(5.0, abs=1e-4)
    assert beta_d1.new_values["investment_return_pct"]  == pytest.approx(-5.0, abs=1e-4)


# ── Test 17: Unknown portfolio returns error result ────────────────────────────

def test_unknown_portfolio_returns_error():
    """A non-existent portfolio_id must return a result with an error message."""
    db = make_session()
    ws, _ = _seed(db)

    result = recover_portfolio_snapshot_returns(db, portfolio_id=99999, workspace_id=ws.id)

    assert result.error is not None
    assert "99999" in result.error
    assert result.snapshots_scanned == 0


# ── Test 18: Empty portfolio scans 0 snapshots without error ─────────────────

def test_empty_portfolio_scans_zero_snapshots():
    """A portfolio with no snapshots must produce a clean result with 0 scanned."""
    db = make_session()
    ws, p = _seed(db)

    result = recover_portfolio_snapshot_returns(db, p.id, ws.id)

    assert result.error is None
    assert result.snapshots_scanned   == 0
    assert result.snapshots_changed   == 0
    assert result.snapshots_unchanged == 0
    assert result.diffs               == []


# ── Test 19: Multi-snapshot chain — each window uses correct boundaries ────────

def test_multi_snapshot_chain_correct_windows():
    """In a 4-snapshot chain, each period's return uses only transactions in
    that specific window, not those from adjacent periods."""
    db = make_session()
    ws, p = _seed(db)

    d0, d1, d2, d3 = _d(6), _d(5), _d(4), _d(3)
    # d0: all equity, no cash
    _snap(db, p.id, ws.id, d0, 100_000.0, cash_balance=0.0)
    # d1: DEPOSIT of 22k raised cash from 0 → 22,000; equity unchanged → total 122,000
    _snap(db, p.id, ws.id, d1, 122_000.0, cash_balance=22_000.0)
    # d2 and d3: no cash transactions → cash stays at 22,000
    _snap(db, p.id, ws.id, d2, 122_500.0, cash_balance=22_000.0)
    _snap(db, p.id, ws.id, d3, 119_500.0, cash_balance=22_000.0)

    # DEPOSIT falls between d0 and d1
    _tx(db, p.id, ws.id, "DEPOSIT", 22_000.0, _dt(5) + timedelta(hours=10))

    result = recover_portfolio_snapshot_returns(db, p.id, ws.id, dry_run=True)

    # d0: baseline → None
    assert result.diffs[0].new_values["investment_return_pct"] is None

    # d1: DEPOSIT stripped → 0% return
    assert result.diffs[1].new_values["investment_return_pct"] == pytest.approx(0.0, abs=1e-4)
    assert result.diffs[1].new_values["net_external_cash_flow"] == pytest.approx(22_000.0, abs=0.01)

    # d2: no events → 500/122,000 ≈ 0.4098%
    assert result.diffs[2].new_values["investment_return_pct"] == pytest.approx(500.0 / 122_000.0 * 100, abs=1e-3)
    assert result.diffs[2].new_values["net_external_cash_flow"] is None

    # d3: no events → -3,000/122,500 ≈ -2.4490%
    assert result.diffs[3].new_values["investment_return_pct"] == pytest.approx(-3_000.0 / 122_500.0 * 100, abs=1e-3)


# ── Test 20: Writes are persisted when not dry_run ────────────────────────────

def test_writes_persisted_to_db_on_commit():
    """After commit, the new return fields must be readable from the database."""
    db = make_session()
    ws, p = _seed(db)

    d0, d1 = _d(3), _d(2)
    _snap(db, p.id, ws.id, d0, 100_000.0)
    s1 = _snap(db, p.id, ws.id, d1, 112_000.0)

    result = recover_portfolio_snapshot_returns(db, p.id, ws.id, dry_run=False)
    db.commit()

    assert result.snapshots_changed == 1

    db.expire_all()
    updated = db.query(PortfolioSnapshot).filter_by(id=s1.id).first()
    expected_pct = round(12_000.0 / 100_000.0 * 100, 4)
    assert updated.investment_return_pct    == pytest.approx(expected_pct, abs=1e-4)
    assert updated.daily_return_pct         == pytest.approx(expected_pct, abs=1e-4)
    assert updated.investment_return_amount == pytest.approx(12_000.0, abs=0.01)


# ── Test 21: NAV fields are never modified ────────────────────────────────────

def test_nav_fields_never_modified():
    """total_value, cash_balance, total_invested, unrealized_pnl, holdings_json
    must be identical before and after recovery."""
    db = make_session()
    ws, p = _seed(db)

    d0, d1 = _d(3), _d(2)
    _snap(db, p.id, ws.id, d0, 100_000.0, cash_balance=10_000.0)

    s1 = PortfolioSnapshot(
        workspace_id      = ws.id,
        portfolio_id      = p.id,
        snapshot_date     = d1,
        total_value       = 105_000.0,
        cash_balance      = 15_000.0,
        total_invested    = 90_000.0,
        unrealized_pnl    = 5_000.0,
        unrealized_pnl_pct = 5.88,
        realized_pnl      = 1_234.5,
        holdings_json     = json.dumps([{"symbol": "AOT.BK", "shares": 100}]),
        holdings_count    = 1,
    )
    db.add(s1)
    db.commit()

    before = {
        "total_value": s1.total_value,
        "cash_balance": s1.cash_balance,
        "total_invested": s1.total_invested,
        "unrealized_pnl": s1.unrealized_pnl,
        "unrealized_pnl_pct": s1.unrealized_pnl_pct,
        "realized_pnl": s1.realized_pnl,
        "holdings_json": s1.holdings_json,
        "holdings_count": s1.holdings_count,
    }

    recover_portfolio_snapshot_returns(db, p.id, ws.id, dry_run=False)
    db.commit()

    db.expire_all()
    after_snap = db.query(PortfolioSnapshot).filter_by(id=s1.id).first()
    for col, val in before.items():
        assert getattr(after_snap, col) == val, f"Column {col} was modified"


# ── Test 22: Forensic scenario — phantom DEPOSIT + INITIAL_POSITION ────────────

def test_phantom_deposit_and_initial_position_excluded():
    """Retroactive bookkeeping DEPOSIT and INITIAL_POSITION must not distort return.

    Mirrors the real-data forensic investigation for Snapshot 39 (portfolio 2,
    2026-05-25):
      • prev_snap: SCB.BK already held with 2300 shares, cash=23,071.69
      • curr_snap: same 2300 SCB.BK shares, cash=23,071.69 (unchanged)
      • In-window transactions:
          tx#26 — DEPOSIT 22,071.69: recorded in DB, but cash_balance unchanged
          tx#28 — INITIAL_POSITION SCB.BK 1000 shares: recorded in DB, but
                  SCB.BK was already in prev holdings with 2300 ≥ 1000 shares

    Both are retroactive bookkeeping entries.  Neither changed the portfolio's
    actual state.  The correct period return is the pure market gain:
        6,085 / 836,436.69 × 100 ≈ +0.7275 %
    """
    db = make_session()
    ws, p = _seed(db)

    prev_nav  = 836_436.69
    prev_cash = 23_071.69
    prev_holdings_json = json.dumps([
        {
            "symbol": "SCB.BK", "shares": 2300.0, "avg_cost": 134.2033,
            "current_price": 135.0, "market_value": 310_500.0,
            "unrealized_pnl": 1840.0, "sector": "Finance",
        },
        {
            "symbol": "AOT.BK", "shares": 5000.0, "avg_cost": 56.09,
            "current_price": 52.75, "market_value": 263_750.0,
            "unrealized_pnl": -16_700.0, "sector": "Transport",
        },
    ])
    d_prev = _d(4)
    s0 = PortfolioSnapshot(
        workspace_id=ws.id, portfolio_id=p.id, snapshot_date=d_prev,
        total_value=prev_nav, cash_balance=prev_cash,
        holdings_json=prev_holdings_json, holdings_count=2,
    )
    db.add(s0)
    db.commit()

    # Pure market gain between periods; cash and share counts unchanged.
    market_gain = 6_085.0
    curr_nav    = prev_nav + market_gain
    curr_cash   = prev_cash  # phantom DEPOSIT did not change cash

    d_curr = _d(1)
    s1 = PortfolioSnapshot(
        workspace_id=ws.id, portfolio_id=p.id, snapshot_date=d_curr,
        total_value=curr_nav, cash_balance=curr_cash,
        holdings_count=2,
    )
    db.add(s1)
    db.commit()

    # Phantom DEPOSIT — Transaction record exists but cash_balance never updated.
    _tx(db, p.id, ws.id, "DEPOSIT", 22_071.69,
        _dt(1) + timedelta(hours=5))

    # Phantom INITIAL_POSITION — SCB.BK already held (2300 shares ≥ 1000 in tx).
    _tx(db, p.id, ws.id, "INITIAL_POSITION", 144_646.69,
        _dt(1) + timedelta(hours=5, minutes=5),
        symbol="SCB.BK", shares=1000.0, price_per_share=144.64669)

    result = recover_portfolio_snapshot_returns(db, p.id, ws.id, dry_run=True)

    assert result.snapshots_scanned == 2
    diff = result.diffs[1]  # curr snapshot

    expected_return = round(market_gain / prev_nav * 100, 4)  # ≈ +0.7275 %
    assert diff.new_values["investment_return_pct"] == pytest.approx(expected_return, abs=1e-3), (
        f"Expected +{expected_return}% (forensic result) but got "
        f"{diff.new_values['investment_return_pct']}%"
    )
    assert diff.new_values["net_external_cash_flow"] is None, \
        "Phantom DEPOSIT must not appear in net_external_cash_flow"
    assert diff.new_values["imported_asset_value"] is None, \
        "Phantom INITIAL_POSITION for already-tracked symbol must not appear in imported_asset_value"
    assert diff.new_values["investment_return_amount"] == pytest.approx(market_gain, abs=0.01)
