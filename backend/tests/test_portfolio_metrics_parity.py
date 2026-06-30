"""Cross-engine regression tests: portfolio_rebuilder.py vs
snapshot_return_recovery.py must produce identical PeriodMetrics for an
identical ledger, now that both delegate to
services.portfolio_metrics.compute_period_metrics() (ADR-004).

No real "Portfolio 4 / 2026-05-27" fixture exists in this codebase — that
date is a debugging artifact (a stray print() removed from
portfolio_rebuilder.py earlier in this refactor), not seeded test data.
These scenarios are built from scratch instead, covering the same event
types: buy, sell, deposit, withdrawal, fees, taxes, INITIAL_POSITION,
QUANTITY_CORRECTION (including a downward delta), a transaction_date !=
created_at (backdated) case, and window self-containment (the invariant
that makes --from-date partial rebuilds safe).

Coverage
--------
  1. Full transaction mix: rebuilder (_populate_return_fields, pure,
     transaction_date-windowed) and recovery (recover_portfolio_snapshot_returns,
     DB-backed, created_at-windowed) produce identical PeriodMetrics for an
     equivalent ledger where transaction_date == created_at for every row.
  2. Backdated transaction (transaction_date far in the past, created_at
     today): rebuilder attributes it to ITS OWN historical window via
     transaction_date; recovery attributes it to TODAY's window via
     created_at. Both are correct per their own engine's contract — this is
     the ADR-003 resolution (docs/PORTFOLIO_CALCULATION_RULES.md Section 2),
     not a parity violation.
  3. Window self-containment: _populate_return_fields's output for a given
     (prev_date, curr_date) pair is unaffected by extra, out-of-window
     transactions present in the full all_txs list — the function always
     re-filters by date range itself. This is the invariant that makes a
     partial rebuild (--from-date) safe: resuming from a later prev_date
     does not change any individual day's computed metrics.
"""
from __future__ import annotations

import os
import sys
from datetime import date, datetime
from decimal import Decimal

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base, Portfolio, PortfolioSnapshot, Transaction, Workspace
from services.portfolio_rebuilder import _SnapshotDay, _populate_return_fields
from services.snapshot_return_recovery import recover_portfolio_snapshot_returns
from services.transaction_canonicalizer import CanonicalTransaction


# ── Rebuilder-side (pure) helpers ────────────────────────────────────────────

def _ctx(
    id: int,
    transaction_type: str,
    total_amount: float = 0.0,
    raw_symbol: str | None = None,
    shares: float = 0.0,
    price_per_share: float = 0.0,
    fees: float = 0.0,
    taxes: float = 0.0,
    qty_correction_delta: Decimal | None = None,
    realized_pnl: float | None = None,
    transaction_date: date = date(2026, 6, 1),
) -> CanonicalTransaction:
    return CanonicalTransaction(
        id                   = id,
        transaction_type     = transaction_type,
        raw_symbol           = raw_symbol,
        canonical_symbol      = raw_symbol,
        shares               = Decimal(str(shares)),
        price_per_share      = Decimal(str(price_per_share)),
        total_amount         = Decimal(str(total_amount)),
        fees                 = Decimal(str(fees)),
        taxes                = Decimal(str(taxes)),
        transaction_date     = transaction_date,
        created_at           = None,
        sector               = None,
        notes                = None,
        qty_correction_delta = qty_correction_delta,
        realized_pnl         = realized_pnl,
    )


def _day(total_value: float, snapshot_date: str = "2026-06-01") -> _SnapshotDay:
    return _SnapshotDay(snapshot_date=snapshot_date, total_value=total_value, holdings_json="[]")


# ── Recovery-side (DB-backed) helpers ────────────────────────────────────────

def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _seed(db):
    ws = Workspace(name="ParityWS")
    db.add(ws)
    db.flush()
    p = Portfolio(workspace_id=ws.id, name="Parity", cash_balance=0.0)
    db.add(p)
    db.commit()
    return ws, p


def _snap(db, portfolio_id, workspace_id, snapshot_date: str, total_value: float) -> PortfolioSnapshot:
    s = PortfolioSnapshot(
        workspace_id=workspace_id, portfolio_id=portfolio_id,
        snapshot_date=snapshot_date, total_value=total_value, cash_balance=0.0,
    )
    db.add(s)
    db.commit()
    return s


def _tx(
    db, portfolio_id, workspace_id, tx_type: str, total_amount: float,
    created_at: datetime, transaction_date: datetime | None = None, *,
    symbol: str | None = None, shares: float | None = None,
    price_per_share: float | None = None, fees: float = 0.0, taxes: float = 0.0,
    notes: str | None = None,
) -> Transaction:
    t = Transaction(
        workspace_id=workspace_id, portfolio_id=portfolio_id,
        transaction_type=tx_type, total_amount=total_amount,
        symbol=symbol, shares=shares, price_per_share=price_per_share,
        fees=fees, taxes=taxes,
        transaction_date=transaction_date or created_at,
        created_at=created_at, notes=notes,
    )
    db.add(t)
    db.commit()
    return t


# ── 1. Full transaction mix parity ───────────────────────────────────────────

def test_parity_full_transaction_mix():
    """Identical ledger, identical NAVs -> rebuilder and recovery must agree
    on every PeriodMetrics field, including the signed downward
    QUANTITY_CORRECTION (frozen doc Section 7) and ledger-derived
    net_external_cash_flow (ADR-002)."""
    prev_nav = 100_000.0
    curr_nav = 115_000.0

    # ── Rebuilder side: pure CanonicalTransaction list ───────────────────────
    rebuilder_txs = [
        _ctx(1, "DEPOSIT", total_amount=10_000.0),
        _ctx(2, "WITHDRAW", total_amount=2_000.0),
        _ctx(3, "BUY", total_amount=8_000.0, fees=50.0, taxes=3.5),
        _ctx(4, "SELL", total_amount=9_000.0, fees=60.0, taxes=4.2, realized_pnl=750.0),
        _ctx(5, "DIVIDEND", total_amount=500.0),
        _ctx(6, "INITIAL_POSITION", raw_symbol="SCB.BK", shares=100.0, price_per_share=100.0),
        _ctx(7, "QUANTITY_CORRECTION", raw_symbol="PTT.BK", price_per_share=30.0,
             qty_correction_delta=Decimal("-5")),
    ]
    day = _day(curr_nav)
    _populate_return_fields(day, "2026-05-31", "2026-06-01", prev_nav, rebuilder_txs)

    # ── Recovery side: equivalent ledger seeded into a real DB ───────────────
    db = make_session()
    ws, p = _seed(db)
    _snap(db, p.id, ws.id, "2026-05-31", prev_nav)
    _snap(db, p.id, ws.id, "2026-06-01", curr_nav)

    ts = datetime(2026, 6, 1, 12, 0, 0)
    _tx(db, p.id, ws.id, "DEPOSIT", 10_000.0, ts)
    _tx(db, p.id, ws.id, "WITHDRAW", 2_000.0, ts)
    _tx(db, p.id, ws.id, "BUY", 8_000.0, ts, fees=50.0, taxes=3.5)
    _tx(db, p.id, ws.id, "SELL", 9_000.0, ts, fees=60.0, taxes=4.2,
        notes="Realized P&L: 750.00")
    _tx(db, p.id, ws.id, "DIVIDEND", 500.0, ts)
    _tx(db, p.id, ws.id, "INITIAL_POSITION", 10_000.0, ts,
        symbol="SCB.BK", shares=100.0, price_per_share=100.0)
    _tx(db, p.id, ws.id, "QUANTITY_CORRECTION", 150.0, ts,
        symbol="PTT.BK", shares=5.0, price_per_share=30.0,
        notes="Quantity correction: -5.0 shares")

    result = recover_portfolio_snapshot_returns(db, p.id, ws.id, dry_run=True)
    recovery_vals = result.diffs[1].new_values  # diffs[0] is the baseline snapshot

    # ── Parity assertions ─────────────────────────────────────────────────────
    assert day.net_external_cash_flow == pytest.approx(recovery_vals["net_external_cash_flow"])
    assert day.imported_asset_value == pytest.approx(recovery_vals["imported_asset_value"])
    assert day.manual_adjustment_value == pytest.approx(recovery_vals["manual_adjustment_value"])
    assert day.manual_adjustment_value == pytest.approx(-150.0)  # signed: downward correction
    assert day.period_realized_pnl == pytest.approx(recovery_vals["period_realized_pnl"])
    assert day.period_dividend_income == pytest.approx(recovery_vals["period_dividend_income"])
    assert day.period_fees_paid == pytest.approx(recovery_vals["period_fees_paid"])
    assert day.investment_return_pct == pytest.approx(recovery_vals["investment_return_pct"])
    assert day.investment_return_amount == pytest.approx(recovery_vals["investment_return_amount"])
    assert day.daily_return_pct == pytest.approx(recovery_vals["daily_return_pct"])


# ── 2. Backdated transaction: each engine uses its own window field ─────────

def test_backdated_transaction_attributed_per_engine_own_window_field():
    """A transaction backdated to transaction_date=2024-01-10 but inserted
    (created_at) on 2026-06-14 must be picked up by the REBUILDER in its own
    historical window (2024-01-09 -> 2024-01-10) via transaction_date, and by
    RECOVERY in TODAY's window (2026-06-13 -> 2026-06-14) via created_at.
    These are different windows by design (ADR-003 resolution) — this is not
    a parity violation; it is each engine correctly answering a different
    question (portfolio-state-as-of-date vs. window-membership-for-an-
    incrementally-built-series). See PORTFOLIO_CALCULATION_RULES.md Section 2.
    """
    backdated_tx_date = date(2024, 1, 10)

    # ── Rebuilder: process the transaction's OWN historical window ──────────
    historical_txs = [
        _ctx(1, "INITIAL_POSITION", raw_symbol="SCB.BK", shares=1_000.0,
             price_per_share=50.0, transaction_date=backdated_tx_date),
    ]
    historical_day = _day(total_value=50_000.0, snapshot_date="2024-01-10")
    _populate_return_fields(historical_day, "2024-01-09", "2024-01-10", 0.0, historical_txs)
    # prev_nav=0.0 is invalid (<=0), so investment_return_pct stays None, but
    # imported_asset_value is still computed from the window regardless.
    assert historical_day.imported_asset_value == pytest.approx(50_000.0)

    # The SAME transaction is invisible to "today's" rebuilder window, since
    # transaction_date (2024-01-10) does not fall in (2026-06-13, 2026-06-14].
    today_day = _day(total_value=100_000.0, snapshot_date="2026-06-14")
    _populate_return_fields(today_day, "2026-06-13", "2026-06-14", 90_000.0, historical_txs)
    assert today_day.imported_asset_value is None

    # ── Recovery: the same transaction, inserted (created_at) today ─────────
    db = make_session()
    ws, p = _seed(db)
    _snap(db, p.id, ws.id, "2026-06-13", 90_000.0)
    _snap(db, p.id, ws.id, "2026-06-14", 140_000.0)

    _tx(
        db, p.id, ws.id, "INITIAL_POSITION", 50_000.0,
        created_at=datetime(2026, 6, 14, 9, 0, 0),
        transaction_date=datetime(2024, 1, 10),
        symbol="SCB.BK", shares=1_000.0, price_per_share=50.0,
    )

    result = recover_portfolio_snapshot_returns(db, p.id, ws.id, dry_run=True)
    recovery_vals = result.diffs[1].new_values

    # Recovery picks it up in TODAY's window via created_at — the opposite of
    # the rebuilder's "today" window result above, by design.
    assert recovery_vals["imported_asset_value"] == pytest.approx(50_000.0)


# ── 3. Window self-containment (partial-rebuild resumption safety) ──────────

def test_populate_return_fields_window_is_self_contained():
    """A day's computed metrics must not depend on which other, out-of-window
    transactions happen to be present in the full all_txs list — the function
    always re-filters by (prev_date, curr_date) itself. This is the invariant
    that makes a partial rebuild (--from-date) safe: resuming from a later
    prev_date and passing a smaller all_txs slice must reproduce the exact
    same result as passing the full, unfiltered transaction history."""
    in_window_tx  = _ctx(2, "DEPOSIT", total_amount=5_000.0, transaction_date=date(2026, 6, 1))
    earlier_tx    = _ctx(1, "DEPOSIT", total_amount=99_000.0, transaction_date=date(2024, 1, 1))
    later_tx      = _ctx(3, "WITHDRAW", total_amount=1_000.0, transaction_date=date(2026, 12, 31))

    full_day = _day(105_000.0)
    _populate_return_fields(full_day, "2026-05-31", "2026-06-01", 100_000.0,
                             [earlier_tx, in_window_tx, later_tx])

    minimal_day = _day(105_000.0)
    _populate_return_fields(minimal_day, "2026-05-31", "2026-06-01", 100_000.0,
                             [in_window_tx])

    assert full_day.net_external_cash_flow == pytest.approx(minimal_day.net_external_cash_flow)
    assert full_day.net_external_cash_flow == pytest.approx(5_000.0)
    assert full_day.investment_return_pct == pytest.approx(minimal_day.investment_return_pct)
