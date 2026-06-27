"""Tests for services/portfolio_rebuilder.py — Phase 2 consumer migration.

Verifies that the replay engine operates on CanonicalTransaction objects and
that the removed duplicate parsing helpers are gone.  All tests are pure-Python
(no database or network).

Coverage
--------
Removed helpers
  1.  _REALIZED_RE not importable from portfolio_rebuilder
  2.  _QCORR_RE not importable from portfolio_rebuilder
  3.  _parse_realized_pnl not importable from portfolio_rebuilder
  4.  _parse_qty_correction_delta not importable from portfolio_rebuilder

_apply_transaction with CanonicalTransaction
  5.  DEPOSIT increases cash balance
  6.  INITIAL_CASH increases cash balance
  7.  WITHDRAW decreases cash balance
  8.  DIVIDEND increases cash balance
  9.  BUY decreases cash and adds holding (avg cost = total_amount / shares)
  10. BUY into existing holding merges with weighted-average cost
  11. BUY with zero shares is a no-op
  12. SELL increases cash and removes holding when fully sold
  13. SELL partial reduces shares; holding remains
  14. SELL accumulates realized P&L from ctx.realized_pnl
  15. SELL with None realized_pnl treated as 0.0
  16. INITIAL_POSITION adds holding without affecting cash
  17. INITIAL_POSITION into existing holding merges avg_cost
  18. INITIAL_POSITION with zero shares is a no-op
  19. QUANTITY_CORRECTION positive delta increases shares and adjusts avg_cost
  20. QUANTITY_CORRECTION negative delta decreases shares
  21. QUANTITY_CORRECTION that zeros a holding removes it
  22. QUANTITY_CORRECTION for unknown symbol is a no-op
  23. Uses canonical_symbol (not raw_symbol) as holdings key

_replay_with_date_snapshots
  24. Single date: state reflects transactions up to that date
  25. Transactions after the date are NOT applied
  26. Same date, multiple snapshots: second date builds on first
  27. Empty transaction list returns initial state for every date

_populate_return_fields
  28. DEPOSIT counted in net_ecf (deposits)
  29. WITHDRAW counted in net_ecf (withdrawals)
  30. BUY fees and taxes counted in period_fees_paid
  31. SELL P&L and fees counted in period decomposition
  32. DIVIDEND counted in period_dividend_income
  33. Transactions outside the window are excluded
"""
from __future__ import annotations

import sys
import os
from datetime import date, datetime
from decimal import Decimal

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.transaction_canonicalizer import CanonicalTransaction
from services.portfolio_rebuilder import (
    _apply_transaction,
    _replay_with_date_snapshots,
    _populate_return_fields,
    _PortfolioState,
    _HoldingState,
    _SnapshotDay,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _ctx(
    id: int = 1,
    transaction_type: str = "BUY",
    raw_symbol: str | None = "AOT.BK",
    canonical_symbol: str | None = "AOT.BK",
    shares: float = 100.0,
    price_per_share: float = 75.0,
    total_amount: float = 7_550.0,
    fees: float = 50.0,
    taxes: float = 3.50,
    transaction_date: date = date(2026, 1, 15),
    created_at: datetime | None = None,
    sector: str | None = "Transport",
    notes: str | None = None,
    qty_correction_delta: Decimal | None = None,
    realized_pnl: float | None = None,
) -> CanonicalTransaction:
    return CanonicalTransaction(
        id                   = id,
        transaction_type     = transaction_type,
        raw_symbol           = raw_symbol,
        canonical_symbol     = canonical_symbol,
        shares               = Decimal(str(shares)),
        price_per_share      = Decimal(str(price_per_share)),
        total_amount         = Decimal(str(total_amount)),
        fees                 = Decimal(str(fees)),
        taxes                = Decimal(str(taxes)),
        transaction_date     = transaction_date,
        created_at           = created_at,
        sector               = sector,
        notes                = notes,
        qty_correction_delta = qty_correction_delta,
        realized_pnl         = realized_pnl,
    )


def _state(cash: float = 0.0) -> _PortfolioState:
    return _PortfolioState(
        cash_balance            = Decimal(str(cash)),
        holdings                = {},
        cumulative_realized_pnl = Decimal("0"),
    )


def _day(holdings_json: str = "[]", total_value: float = 100_000.0) -> _SnapshotDay:
    return _SnapshotDay(
        snapshot_date = "2026-06-01",
        total_value   = total_value,
        holdings_json = holdings_json,
    )


# ══════════════════════════════════════════════════════════════════════════════
# 1-4. Removed helpers
# ══════════════════════════════════════════════════════════════════════════════

def test_realized_re_not_in_rebuilder():
    import services.portfolio_rebuilder as mod
    assert not hasattr(mod, "_REALIZED_RE")


def test_qcorr_re_not_in_rebuilder():
    import services.portfolio_rebuilder as mod
    assert not hasattr(mod, "_QCORR_RE")


def test_parse_realized_pnl_not_in_rebuilder():
    import services.portfolio_rebuilder as mod
    assert not hasattr(mod, "_parse_realized_pnl")


def test_parse_qty_correction_delta_not_in_rebuilder():
    import services.portfolio_rebuilder as mod
    assert not hasattr(mod, "_parse_qty_correction_delta")


# ══════════════════════════════════════════════════════════════════════════════
# 5-8. Cash-only transaction types
# ══════════════════════════════════════════════════════════════════════════════

def test_deposit_increases_cash():
    s = _state(0.0)
    _apply_transaction(s, _ctx(transaction_type="DEPOSIT", total_amount=50_000.0,
                                raw_symbol=None, canonical_symbol=None, shares=0.0))
    assert s.cash_balance == Decimal("50000.0")


def test_initial_cash_increases_cash():
    s = _state(0.0)
    _apply_transaction(s, _ctx(transaction_type="INITIAL_CASH", total_amount=20_000.0,
                                raw_symbol=None, canonical_symbol=None, shares=0.0))
    assert s.cash_balance == Decimal("20000.0")


def test_withdraw_decreases_cash():
    s = _state(30_000.0)
    _apply_transaction(s, _ctx(transaction_type="WITHDRAW", total_amount=10_000.0,
                                raw_symbol=None, canonical_symbol=None, shares=0.0))
    assert s.cash_balance == Decimal("20000.0")


def test_dividend_increases_cash():
    s = _state(5_000.0)
    _apply_transaction(s, _ctx(transaction_type="DIVIDEND", total_amount=500.0,
                                shares=0.0))
    assert s.cash_balance == Decimal("5500.0")


# ══════════════════════════════════════════════════════════════════════════════
# 9-11. BUY
# ══════════════════════════════════════════════════════════════════════════════

def test_buy_reduces_cash_and_adds_holding():
    s = _state(100_000.0)
    tx = _ctx(transaction_type="BUY", shares=100.0, total_amount=7_550.0,
              canonical_symbol="AOT.BK")
    _apply_transaction(s, tx)
    assert s.cash_balance == Decimal("100000.0") - Decimal("7550.0")
    assert "AOT.BK" in s.holdings
    h = s.holdings["AOT.BK"]
    assert h.shares == Decimal("100.0")
    # avg_cost = total_amount / shares = 7550 / 100 = 75.5
    assert h.avg_cost == Decimal("7550.0") / Decimal("100.0")


def test_buy_into_existing_holding_merges_weighted_avg():
    s = _state(200_000.0)
    # First buy: 100 shares @ effective 75.50 each (total_amount 7550)
    _apply_transaction(s, _ctx(id=1, transaction_type="BUY", shares=100.0,
                                total_amount=7_550.0, canonical_symbol="AOT.BK"))
    # Second buy: 100 shares @ effective 80.00 each (total_amount 8000)
    _apply_transaction(s, _ctx(id=2, transaction_type="BUY", shares=100.0,
                                total_amount=8_000.0, canonical_symbol="AOT.BK"))

    h = s.holdings["AOT.BK"]
    assert h.shares == Decimal("200.0")
    expected_avg = (Decimal("7550.0") + Decimal("8000.0")) / Decimal("200.0")
    assert h.avg_cost == expected_avg


def test_buy_zero_shares_is_no_op():
    s = _state(100_000.0)
    _apply_transaction(s, _ctx(transaction_type="BUY", shares=0.0, total_amount=0.0,
                                canonical_symbol="AOT.BK"))
    assert "AOT.BK" not in s.holdings
    assert s.cash_balance == Decimal("100000.0")


# ══════════════════════════════════════════════════════════════════════════════
# 12-15. SELL
# ══════════════════════════════════════════════════════════════════════════════

def test_sell_full_position_removes_holding():
    s = _state(0.0)
    s.holdings["AOT.BK"] = _HoldingState("AOT.BK", Decimal("100"), Decimal("75"), "Transport")
    _apply_transaction(s, _ctx(transaction_type="SELL", shares=100.0, total_amount=8_000.0,
                                canonical_symbol="AOT.BK", realized_pnl=500.0))
    assert "AOT.BK" not in s.holdings
    assert s.cash_balance == Decimal("8000.0")
    assert s.cumulative_realized_pnl == Decimal("500.0")


def test_sell_partial_reduces_shares():
    s = _state(0.0)
    s.holdings["AOT.BK"] = _HoldingState("AOT.BK", Decimal("200"), Decimal("75"), "Transport")
    _apply_transaction(s, _ctx(transaction_type="SELL", shares=50.0, total_amount=4_000.0,
                                canonical_symbol="AOT.BK", realized_pnl=250.0))
    assert "AOT.BK" in s.holdings
    assert s.holdings["AOT.BK"].shares == Decimal("150")


def test_sell_accumulates_realized_pnl_from_ctx():
    s = _state(0.0)
    s.holdings["AOT.BK"] = _HoldingState("AOT.BK", Decimal("100"), Decimal("75"), None)
    _apply_transaction(s, _ctx(transaction_type="SELL", shares=100.0, total_amount=8_000.0,
                                canonical_symbol="AOT.BK", realized_pnl=1_234.56))
    assert float(s.cumulative_realized_pnl) == pytest.approx(1_234.56)


def test_sell_with_none_realized_pnl_treated_as_zero():
    s = _state(0.0)
    s.holdings["AOT.BK"] = _HoldingState("AOT.BK", Decimal("100"), Decimal("75"), None)
    _apply_transaction(s, _ctx(transaction_type="SELL", shares=100.0, total_amount=8_000.0,
                                canonical_symbol="AOT.BK", realized_pnl=None))
    assert s.cumulative_realized_pnl == Decimal("0")


# ══════════════════════════════════════════════════════════════════════════════
# 16-18. INITIAL_POSITION
# ══════════════════════════════════════════════════════════════════════════════

def test_initial_position_adds_holding_without_affecting_cash():
    s = _state(50_000.0)
    _apply_transaction(s, _ctx(transaction_type="INITIAL_POSITION", shares=200.0,
                                price_per_share=60.0, total_amount=12_000.0,
                                raw_symbol="KBANK.BK", canonical_symbol="KBANK.BK"))
    assert s.cash_balance == Decimal("50000.0")  # unchanged
    assert "KBANK.BK" in s.holdings
    h = s.holdings["KBANK.BK"]
    assert h.shares == Decimal("200.0")
    assert h.avg_cost == Decimal("60.0")


def test_initial_position_merges_into_existing_holding():
    s = _state(0.0)
    s.holdings["KBANK.BK"] = _HoldingState("KBANK.BK", Decimal("100"), Decimal("60"), None)
    _apply_transaction(s, _ctx(transaction_type="INITIAL_POSITION", shares=100.0,
                                price_per_share=70.0, total_amount=7_000.0,
                                raw_symbol="KBANK.BK", canonical_symbol="KBANK.BK"))
    h = s.holdings["KBANK.BK"]
    assert h.shares == Decimal("200")
    expected_avg = (Decimal("100") * Decimal("60") + Decimal("100") * Decimal("70")) / Decimal("200")
    assert h.avg_cost == expected_avg


def test_initial_position_zero_shares_is_no_op():
    s = _state(0.0)
    _apply_transaction(s, _ctx(transaction_type="INITIAL_POSITION", shares=0.0,
                                canonical_symbol="KBANK.BK"))
    assert "KBANK.BK" not in s.holdings


# ══════════════════════════════════════════════════════════════════════════════
# 19-22. QUANTITY_CORRECTION
# ══════════════════════════════════════════════════════════════════════════════

def test_qcorr_positive_delta_increases_shares_and_adjusts_avg():
    s = _state(0.0)
    s.holdings["PTT.BK"] = _HoldingState("PTT.BK", Decimal("100"), Decimal("40"), None)
    _apply_transaction(s, _ctx(
        transaction_type     = "QUANTITY_CORRECTION",
        raw_symbol           = "PTT.BK",
        canonical_symbol     = "PTT.BK",
        shares               = 10.0,
        price_per_share      = 42.0,
        qty_correction_delta = Decimal("+10.0"),
    ))
    h = s.holdings["PTT.BK"]
    assert h.shares == Decimal("110")
    expected_avg = (Decimal("100") * Decimal("40") + Decimal("10") * Decimal("42")) / Decimal("110")
    assert float(h.avg_cost) == pytest.approx(float(expected_avg), rel=1e-6)
    assert s.cash_balance == Decimal("0")  # cash unaffected


def test_qcorr_negative_delta_decreases_shares():
    s = _state(0.0)
    s.holdings["PTT.BK"] = _HoldingState("PTT.BK", Decimal("100"), Decimal("40"), None)
    _apply_transaction(s, _ctx(
        transaction_type     = "QUANTITY_CORRECTION",
        raw_symbol           = "PTT.BK",
        canonical_symbol     = "PTT.BK",
        shares               = 20.0,
        price_per_share      = 42.0,
        qty_correction_delta = Decimal("-20.0"),
    ))
    assert s.holdings["PTT.BK"].shares == Decimal("80")


def test_qcorr_zeros_holding_removes_it():
    s = _state(0.0)
    s.holdings["PTT.BK"] = _HoldingState("PTT.BK", Decimal("50"), Decimal("40"), None)
    _apply_transaction(s, _ctx(
        transaction_type     = "QUANTITY_CORRECTION",
        raw_symbol           = "PTT.BK",
        canonical_symbol     = "PTT.BK",
        shares               = 50.0,
        qty_correction_delta = Decimal("-50.0"),
    ))
    assert "PTT.BK" not in s.holdings


def test_qcorr_unknown_symbol_is_no_op():
    s = _state(10_000.0)
    _apply_transaction(s, _ctx(
        transaction_type     = "QUANTITY_CORRECTION",
        raw_symbol           = "NONEXISTENT.BK",
        canonical_symbol     = "NONEXISTENT.BK",
        shares               = 10.0,
        qty_correction_delta = Decimal("+10.0"),
    ))
    assert "NONEXISTENT.BK" not in s.holdings
    assert s.cash_balance == Decimal("10000.0")


# ══════════════════════════════════════════════════════════════════════════════
# 23. raw_symbol used as holdings key (preserves DB symbol form for reconciliation)
# ══════════════════════════════════════════════════════════════════════════════

def test_raw_symbol_used_as_holdings_key():
    """Holdings keys use raw_symbol so they match PortfolioItem.symbol in the DB.

    canonical_symbol resolves DR tickers (NVDA01.BK → NVDA) in ways that would
    break both reconciliation and price-matrix lookups.  raw_symbol preserves
    the exact form stored at transaction time.
    """
    s = _state(100_000.0)
    # Simulate a DR stock: raw="NVDA01.BK", canonical="NVDA"
    tx = _ctx(
        transaction_type = "BUY",
        raw_symbol       = "NVDA01.BK",
        canonical_symbol = "NVDA",
        shares           = 10.0,
        total_amount     = 5_000.0,
    )
    _apply_transaction(s, tx)
    assert "NVDA01.BK" in s.holdings    # raw_symbol used as key
    assert "NVDA" not in s.holdings     # canonical_symbol NOT used


# ══════════════════════════════════════════════════════════════════════════════
# 24-27. _replay_with_date_snapshots
# ══════════════════════════════════════════════════════════════════════════════

def _buy(id: int, sym: str, shares: float, amount: float, dt: date) -> CanonicalTransaction:
    return _ctx(id=id, transaction_type="BUY", canonical_symbol=sym,
                shares=shares, total_amount=amount, transaction_date=dt)


def test_replay_single_date_captures_correct_state():
    txs = [
        _buy(1, "AOT.BK", 100.0, 7_000.0, date(2026, 1, 10)),
        _buy(2, "AOT.BK", 50.0,  3_500.0, date(2026, 1, 20)),
    ]
    # Snapshot date between the two buys — only first should be applied
    result = _replay_with_date_snapshots(txs, ["2026-01-15"])
    state = result["2026-01-15"]
    assert state.holdings["AOT.BK"].shares == Decimal("100.0")


def test_replay_transactions_after_date_not_applied():
    txs = [
        _buy(1, "AOT.BK", 100.0, 7_000.0, date(2026, 2, 1)),  # after snap date
    ]
    result = _replay_with_date_snapshots(txs, ["2026-01-31"])
    state = result["2026-01-31"]
    assert "AOT.BK" not in state.holdings


def test_replay_second_date_builds_on_first():
    txs = [
        _buy(1, "AOT.BK", 100.0, 7_000.0, date(2026, 1, 10)),
        _buy(2, "AOT.BK", 50.0,  3_500.0, date(2026, 1, 20)),
    ]
    result = _replay_with_date_snapshots(txs, ["2026-01-15", "2026-01-25"])
    state_15 = result["2026-01-15"]
    state_25 = result["2026-01-25"]
    assert state_15.holdings["AOT.BK"].shares == Decimal("100.0")
    assert state_25.holdings["AOT.BK"].shares == Decimal("150.0")


def test_replay_empty_txs_returns_initial_state():
    result = _replay_with_date_snapshots([], ["2026-01-01", "2026-02-01"])
    for date_str in ["2026-01-01", "2026-02-01"]:
        state = result[date_str]
        assert state.cash_balance == Decimal("0")
        assert state.holdings == {}


# ══════════════════════════════════════════════════════════════════════════════
# 28-33. _populate_return_fields
# ══════════════════════════════════════════════════════════════════════════════

def _pop(txs, prev="2026-05-31", curr="2026-06-01", prev_nav=100_000.0,
         total_value=100_000.0) -> _SnapshotDay:
    day = _day(total_value=total_value)
    _populate_return_fields(day, prev, curr, prev_nav, txs)
    return day


def _make_tx(id: int, tx_type: str, amount: float, sym: str | None = None,
             shares: float = 0.0, fees: float = 0.0, taxes: float = 0.0,
             realized_pnl: float | None = None,
             qty_delta: Decimal | None = None,
             dt: date = date(2026, 6, 1)) -> CanonicalTransaction:
    return CanonicalTransaction(
        id                   = id,
        transaction_type     = tx_type,
        raw_symbol           = sym,
        canonical_symbol     = sym,
        shares               = Decimal(str(shares)),
        price_per_share      = Decimal("0"),
        total_amount         = Decimal(str(amount)),
        fees                 = Decimal(str(fees)),
        taxes                = Decimal(str(taxes)),
        transaction_date     = dt,
        created_at           = None,
        sector               = None,
        notes                = None,
        qty_correction_delta = qty_delta,
        realized_pnl         = realized_pnl,
    )


def test_populate_deposit_counted_in_net_ecf():
    txs = [_make_tx(1, "DEPOSIT", 10_000.0)]
    day = _pop(txs, total_value=110_000.0, prev_nav=100_000.0)
    assert day.net_external_cash_flow == pytest.approx(10_000.0)


def test_populate_withdraw_counted_in_net_ecf():
    txs = [_make_tx(1, "WITHDRAW", 5_000.0)]
    day = _pop(txs, total_value=95_000.0, prev_nav=100_000.0)
    assert day.net_external_cash_flow == pytest.approx(-5_000.0)


def test_populate_buy_fees_and_taxes_in_period_fees():
    txs = [_make_tx(1, "BUY", 8_000.0, fees=50.0, taxes=3.50)]
    day = _pop(txs)
    assert day.period_fees_paid == pytest.approx(53.50)


def test_populate_sell_pnl_and_fees_in_period_decomposition():
    txs = [_make_tx(1, "SELL", 9_000.0, fees=60.0, taxes=4.20,
                    realized_pnl=750.0)]
    day = _pop(txs)
    assert day.period_realized_pnl == pytest.approx(750.0)
    assert day.period_fees_paid    == pytest.approx(64.20)


def test_populate_dividend_in_period_income():
    txs = [_make_tx(1, "DIVIDEND", 1_200.0)]
    day = _pop(txs)
    assert day.period_dividend_income == pytest.approx(1_200.0)


def test_populate_transactions_outside_window_excluded():
    txs_in  = [_make_tx(1, "DEPOSIT", 5_000.0, dt=date(2026, 6, 1))]
    txs_out = [_make_tx(2, "DEPOSIT", 99_000.0, dt=date(2026, 5, 31))]  # on prev_date = excluded
    day_in  = _pop(txs_in,  prev="2026-05-31", curr="2026-06-01", total_value=105_000.0)
    day_out = _pop(txs_out, prev="2026-05-31", curr="2026-06-01", total_value=100_000.0)
    assert day_in.net_external_cash_flow  == pytest.approx(5_000.0)
    assert day_out.net_external_cash_flow is None  # excluded → None
