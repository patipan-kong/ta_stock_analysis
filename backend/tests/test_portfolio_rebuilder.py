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

import asyncio
import json
import sys
import os
import tempfile
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.transaction_canonicalizer import CanonicalTransaction
from services.ledger_validator import LedgerFinding, LedgerValidationReport
from services.portfolio_rebuilder import (
    _apply_transaction,
    _replay_with_date_snapshots,
    _populate_return_fields,
    _compute_confidence_score,
    _compute_confidence_report,
    _generate_execution_plan,
    _export_backup,
    _values_differ,
    _COVERAGE_THRESHOLD,
    _CONF_W_REPLAY,
    _CONF_W_LEDGER,
    _CONF_W_COVERAGE,
    _CONF_W_CONSISTENCY,
    _CONF_W_VALIDATOR,
    _CONF_LEDGER_PER_CRITICAL,
    _CONF_LEDGER_PER_ERROR,
    _CONF_LEDGER_PER_WARNING,
    _PortfolioState,
    _HoldingState,
    _SnapshotDay,
    ConfidenceReport,
    ReconstructionPlan,
    PlanOperation,
    RebuildResult,
    rebuild_all_portfolios,
    rebuild_portfolio,
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
# 23. ReplayKey used as holdings key (Stage 0 / ADR-005) — DR price_symbol preserved
# ══════════════════════════════════════════════════════════════════════════════

def test_replay_key_used_as_holdings_key():
    """Holdings keys use replay_key(ctx) (canonical_symbol at Stage 0), not
    raw_symbol — the ADR-005 fix. See test_kbank_and_kbank_bk_merge_into_one_holding
    for the alias-merge case this exists to enable.
    """
    s = _state(100_000.0)
    tx = _ctx(
        transaction_type = "BUY",
        raw_symbol       = "KBANK",
        canonical_symbol = "KBANK.BK",
        shares           = 10.0,
        total_amount     = 5_000.0,
    )
    _apply_transaction(s, tx)
    assert "KBANK.BK" in s.holdings     # canonical_symbol (ReplayKey) used as key
    assert "KBANK" not in s.holdings    # raw_symbol NOT used as key


def test_kbank_and_kbank_bk_merge_into_one_holding():
    """The ADR-005 regression case: two raw spellings of the same instrument
    must merge into a single holding once replay keys by ReplayKey.
    """
    s = _state(100_000.0)
    _apply_transaction(s, _ctx(
        id=1, transaction_type="BUY", raw_symbol="KBANK", canonical_symbol="KBANK.BK",
        shares=100.0, total_amount=14_000.0,
    ))
    _apply_transaction(s, _ctx(
        id=2, transaction_type="BUY", raw_symbol="KBANK.BK", canonical_symbol="KBANK.BK",
        shares=50.0, total_amount=7_100.0,
    ))
    assert list(s.holdings.keys()) == ["KBANK.BK"]
    h = s.holdings["KBANK.BK"]
    assert h.shares == Decimal("150.0")
    assert h.avg_cost == (Decimal("14000.0") + Decimal("7100.0")) / Decimal("150.0")


def test_dr_holding_keyed_by_canonical_but_price_symbol_preserves_raw_form():
    """DR certificates (NVDA01.BK) resolve via canonical_symbol to the US
    underlying ticker (NVDA) — correct for replay identity, but yfinance must
    still be asked for the DR's own THB price, not the US ticker's USD price.
    _HoldingState.price_symbol carries the raw, DR-detectable form so
    _build_price_matrix's is_dr() branch keeps firing correctly post Stage 0.
    """
    s = _state(100_000.0)
    tx = _ctx(
        transaction_type = "BUY",
        raw_symbol       = "NVDA01.BK",
        canonical_symbol = "NVDA",
        shares           = 10.0,
        total_amount     = 5_000.0,
    )
    _apply_transaction(s, tx)
    assert "NVDA" in s.holdings              # ReplayKey (canonical_symbol) is the key
    assert "NVDA01.BK" not in s.holdings     # raw_symbol is NOT the key
    assert s.holdings["NVDA"].price_symbol == "NVDA01.BK"   # but preserved for price fetch


def test_price_symbol_falls_back_to_holdings_key_when_not_dr():
    """Non-DR holdings: price_symbol is simply the raw_symbol seen at creation,
    which for ordinary Thai equities is either identical to the ReplayKey or
    an equally valid yfinance ticker (KBANK vs KBANK.BK — both resolve fine).
    """
    s = _state(100_000.0)
    tx = _ctx(
        transaction_type = "BUY",
        raw_symbol       = "AOT.BK",
        canonical_symbol = "AOT.BK",
        shares           = 100.0,
        total_amount     = 7_500.0,
    )
    _apply_transaction(s, tx)
    assert s.holdings["AOT.BK"].price_symbol == "AOT.BK"


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


# ══════════════════════════════════════════════════════════════════════════════
# Phase 6 — Confidence score + backup export
# ══════════════════════════════════════════════════════════════════════════════

def _result(**kwargs) -> RebuildResult:
    """Minimal RebuildResult factory for confidence tests.

    Defaults transactions_replayed=1 so replay_confidence=100 for 'no issues' tests.
    """
    return RebuildResult(
        portfolio_id          = kwargs.pop("portfolio_id", 1),
        portfolio_name        = kwargs.pop("portfolio_name", "Test"),
        success               = kwargs.pop("success", True),
        transactions_replayed = kwargs.pop("transactions_replayed", 1),
        **kwargs,
    )


# ──────────────────────────────────────────────────────────────────────────────
# 34-40. _compute_confidence_score (delegates to _compute_confidence_report)
# These verify the scalar value returned by the backward-compat wrapper.
# ──────────────────────────────────────────────────────────────────────────────

def test_confidence_score_100_when_no_issues():
    r = _result()
    # All dimensions perfect → overall = 100.0
    assert _compute_confidence_score(r, []) == pytest.approx(100.0)


def test_confidence_score_penalises_critical_finding():
    r = _result(ledger_criticals=1)
    # ledger_integrity = 100-10 = 90; validator_confidence = 0
    # overall = 100×0.20 + 90×0.25 + 100×0.20 + 100×0.20 + 0×0.15 = 82.5
    assert _compute_confidence_score(r, []) == pytest.approx(82.5)


def test_confidence_score_penalises_error_finding():
    r = _result(ledger_errors=1)
    # ledger_integrity = 100-5 = 95; validator_confidence = 100
    # overall = 100×0.20 + 95×0.25 + 100×0.20 + 100×0.20 + 100×0.15 = 98.75 → 98.8
    assert _compute_confidence_score(r, []) == pytest.approx(98.75, abs=0.1)


def test_confidence_score_penalises_warning_finding():
    r = _result(ledger_warnings=1)
    # ledger_integrity = 100-2 = 98; validator_confidence = 100
    # overall = 100×0.20 + 98×0.25 + 100×0.20 + 100×0.20 + 100×0.15 = 99.5
    assert _compute_confidence_score(r, []) == pytest.approx(99.5)


def test_confidence_score_penalises_different_items():
    r = _result(items_different=2)
    # total_recon = 2; different_recon = 2 → snapshot_consistency = 0.0
    # overall = 100×0.20 + 100×0.25 + 100×0.20 + 0×0.20 + 100×0.15 = 80.0
    assert _compute_confidence_score(r, []) == pytest.approx(80.0)


def test_confidence_score_penalises_low_coverage_snapshots():
    low = _day()
    low.holdings_count = 1
    low.price_coverage = _COVERAGE_THRESHOLD - 0.01   # just below threshold
    r = _result()
    # 1/1 low-coverage → historical_coverage = 0.0
    # overall = 100×0.20 + 100×0.25 + 0×0.20 + 100×0.20 + 100×0.15 = 80.0
    assert _compute_confidence_score(r, [low]) == pytest.approx(80.0)


def test_full_coverage_snapshot_not_penalised():
    ok = _day()
    ok.holdings_count = 1
    ok.price_coverage = _COVERAGE_THRESHOLD   # exactly at threshold → not penalised
    r = _result()
    assert _compute_confidence_score(r, [ok]) == pytest.approx(100.0)


def test_confidence_score_many_criticals_reduces_ledger_and_validator():
    r = _result(ledger_criticals=10)
    # ledger_integrity = max(0, 100-100) = 0; validator_confidence = 0
    # replay=100, coverage=100, consistency=100 still contribute
    # overall = 100×0.20 + 0×0.25 + 100×0.20 + 100×0.20 + 0×0.15 = 60.0
    assert _compute_confidence_score(r, []) == pytest.approx(60.0)


def test_export_backup_creates_valid_json_file():
    mock_portfolio = MagicMock()
    mock_portfolio.name = "Test Portfolio"
    mock_portfolio.cash_balance = 100_000.0

    mock_db = MagicMock()
    # filter_by(...).first() → portfolio
    mock_db.query.return_value.filter_by.return_value.first.return_value = mock_portfolio
    # filter_by(...).all() → empty lists (items + snapshots)
    mock_db.query.return_value.filter_by.return_value.all.return_value = []

    with tempfile.TemporaryDirectory() as tmpdir:
        path = _export_backup(mock_db, portfolio_id=7, backup_dir=tmpdir)

        assert path.endswith(".json")
        assert os.path.isfile(path)

        with open(path) as fh:
            data = json.load(fh)

        assert data["portfolio_id"] == 7
        assert "backup_timestamp" in data
        assert data["portfolio"]["name"] == "Test Portfolio"
        assert data["portfolio"]["cash_balance"] == pytest.approx(100_000.0)
        assert data["portfolio_items"] == []
        assert data["snapshots"] == []


# ══════════════════════════════════════════════════════════════════════════════
# Phase 6.5 — ConfidenceReport, _values_differ, _generate_execution_plan
# ══════════════════════════════════════════════════════════════════════════════

# ── _compute_confidence_report (multi-dimensional) ────────────────────────────

def test_confidence_report_all_dimensions_perfect():
    r = _result()
    report = _compute_confidence_report(r, [])
    assert report.replay_confidence    == 100.0
    assert report.ledger_integrity     == 100.0
    assert report.historical_coverage  == 100.0
    assert report.snapshot_consistency == 100.0
    assert report.validator_confidence == 100.0
    assert report.overall              == 100.0


def test_confidence_report_replay_zero_transactions():
    r = _result(transactions_replayed=0)
    report = _compute_confidence_report(r, [])
    assert report.replay_confidence == 0.0
    # overall = 0×0.20 + 100×0.25 + 100×0.20 + 100×0.20 + 100×0.15 = 80.0
    assert report.overall == pytest.approx(80.0)


def test_confidence_report_ledger_integrity_deductions():
    # CRITICAL deduction: 10 per finding; ERROR: 5; WARNING: 2
    r = _result(ledger_criticals=1, ledger_errors=2, ledger_warnings=3)
    report = _compute_confidence_report(r, [])
    expected_ledger = max(0.0, 100.0 - 1 * _CONF_LEDGER_PER_CRITICAL
                                     - 2 * _CONF_LEDGER_PER_ERROR
                                     - 3 * _CONF_LEDGER_PER_WARNING)
    assert report.ledger_integrity == pytest.approx(expected_ledger, abs=0.1)


def test_confidence_report_validator_confidence_zero_on_critical():
    r = _result(ledger_criticals=1)
    report = _compute_confidence_report(r, [])
    assert report.validator_confidence == 0.0


def test_confidence_report_validator_confidence_full_when_no_critical():
    r = _result(ledger_errors=3, ledger_warnings=5)
    report = _compute_confidence_report(r, [])
    assert report.validator_confidence == 100.0


def test_confidence_report_historical_coverage_proportional():
    snap_low  = _day(); snap_low.holdings_count  = 1; snap_low.price_coverage  = 0.50
    snap_high = _day(); snap_high.holdings_count = 1; snap_high.price_coverage = 1.00
    r = _result()
    report = _compute_confidence_report(r, [snap_low, snap_high])
    # 1 out of 2 snaps below threshold → historical_coverage = 100 × (1 - 1/2) = 50.0
    assert report.historical_coverage == pytest.approx(50.0)


def test_confidence_report_snapshot_consistency_includes_items():
    # items_different counts toward snapshot_consistency dimension
    r = _result(items_matched=8, items_different=2)
    report = _compute_confidence_report(r, [])
    # total_recon=10, different=2 → consistency = 80.0
    assert report.snapshot_consistency == pytest.approx(80.0)


def test_confidence_report_overall_equals_weighted_sum():
    """Overall must exactly match the documented weighted formula."""
    r = _result(ledger_errors=1, ledger_warnings=2, snapshots_different=1, snapshots_matched=4)
    snaps = []
    report = _compute_confidence_report(r, snaps)
    expected = round(
        report.replay_confidence    * _CONF_W_REPLAY
        + report.ledger_integrity   * _CONF_W_LEDGER
        + report.historical_coverage * _CONF_W_COVERAGE
        + report.snapshot_consistency * _CONF_W_CONSISTENCY
        + report.validator_confidence * _CONF_W_VALIDATOR,
        1,
    )
    assert report.overall == pytest.approx(expected, abs=0.01)


# ── _values_differ ────────────────────────────────────────────────────────────

def test_values_differ_both_none():
    assert _values_differ(None, None) is False


def test_values_differ_one_none():
    assert _values_differ(None, 1.0) is True
    assert _values_differ(1.0, None) is True


def test_values_differ_within_tolerance():
    assert _values_differ(100.0, 100.005, tol=0.01) is False


def test_values_differ_exceeds_tolerance():
    assert _values_differ(100.0, 100.02, tol=0.01) is True


def test_values_differ_strings():
    assert _values_differ("AOT.BK", "AOT.BK") is False
    assert _values_differ("AOT.BK", "PTT.BK") is True


# ── _generate_execution_plan ──────────────────────────────────────────────────

def _mock_portfolio_obj(cash: float) -> MagicMock:
    p = MagicMock()
    p.cash_balance = cash
    p.id = 1
    return p


def _mock_item(symbol: str, shares: float, avg_cost: float) -> MagicMock:
    m = MagicMock()
    m.symbol   = symbol
    m.shares   = shares
    m.avg_cost = avg_cost
    return m


def _make_mock_db(items: list[MagicMock]) -> MagicMock:
    """Mock DB session that returns given items for PortfolioItem queries
    and empty list for PortfolioSnapshot queries."""
    db = MagicMock()

    from models.database import PortfolioItem, PortfolioSnapshot

    def _query(model):
        m = MagicMock()
        if model is PortfolioItem:
            m.filter_by.return_value.all.return_value = items
        else:
            # PortfolioSnapshot
            fby = MagicMock()
            fby.filter.return_value.all.return_value = []
            fby.all.return_value = []
            m.filter_by.return_value = fby
        return m

    db.query.side_effect = _query
    return db


def _make_final_state(holdings: dict[str, tuple[float, float]]) -> _PortfolioState:
    """Create a _PortfolioState with given {symbol: (shares, avg_cost)} holdings."""
    state = _PortfolioState(
        cash_balance            = Decimal("0"),
        holdings                = {},
        cumulative_realized_pnl = Decimal("0"),
    )
    for sym, (sh, ac) in holdings.items():
        state.holdings[sym] = _HoldingState(
            symbol   = sym,
            shares   = Decimal(str(sh)),
            avg_cost = Decimal(str(ac)),
        )
    return state


def _make_confidence() -> ConfidenceReport:
    return ConfidenceReport(
        replay_confidence=100.0, ledger_integrity=100.0,
        historical_coverage=100.0, snapshot_consistency=100.0,
        validator_confidence=100.0, overall=100.0,
    )


def test_execution_plan_no_changes_when_state_matches():
    """When DB matches replay, plan has no PortfolioItem operations."""
    items    = [_mock_item("AOT.BK", 100.0, 75.5)]
    db       = _make_mock_db(items)
    final    = _make_final_state({"AOT.BK": (100.0, 75.5)})
    portfolio = _mock_portfolio_obj(cash=0.0)
    final.cash_balance = Decimal("0.0")

    plan = _generate_execution_plan(
        db=db, portfolio_id=1, portfolio=portfolio,
        final_state=final, snapshot_days=[],
        from_date=None, confidence=_make_confidence(),
        validator=None, skip_snapshots=True,
    )

    item_ops = [o for o in plan.operations if o.table == "PortfolioItem"]
    assert item_ops == []
    assert plan.summary.item_updates == 0
    assert plan.summary.item_inserts == 0
    assert plan.summary.item_deletes == 0


def test_execution_plan_update_when_avg_cost_differs():
    """Changed avg_cost generates an UPDATE PlanOperation."""
    items    = [_mock_item("KBANK.BK", 200.0, 140.0)]   # current DB value
    db       = _make_mock_db(items)
    final    = _make_final_state({"KBANK.BK": (200.0, 142.5)})  # reconstructed
    portfolio = _mock_portfolio_obj(cash=0.0)
    final.cash_balance = Decimal("0.0")

    plan = _generate_execution_plan(
        db=db, portfolio_id=1, portfolio=portfolio,
        final_state=final, snapshot_days=[],
        from_date=None, confidence=_make_confidence(),
        validator=None, skip_snapshots=True,
    )

    update_ops = [o for o in plan.operations
                  if o.table == "PortfolioItem" and o.operation == "UPDATE"]
    assert any(o.field == "avg_cost" for o in update_ops)
    assert plan.summary.item_updates == 1


def test_execution_plan_insert_for_new_symbol():
    """Symbol in final_state but not in DB generates INSERT."""
    db       = _make_mock_db([])   # no existing items
    final    = _make_final_state({"PTT.BK": (300.0, 35.0)})
    portfolio = _mock_portfolio_obj(cash=0.0)
    final.cash_balance = Decimal("0.0")

    plan = _generate_execution_plan(
        db=db, portfolio_id=1, portfolio=portfolio,
        final_state=final, snapshot_days=[],
        from_date=None, confidence=_make_confidence(),
        validator=None, skip_snapshots=True,
    )

    insert_ops = [o for o in plan.operations
                  if o.table == "PortfolioItem" and o.operation == "INSERT"]
    assert len(insert_ops) == 1
    assert insert_ops[0].object_id == "PTT.BK"
    assert plan.summary.item_inserts == 1


def test_execution_plan_delete_for_closed_position():
    """Symbol in DB but absent from final_state generates DELETE."""
    items    = [_mock_item("CPALL.BK", 50.0, 60.0)]
    db       = _make_mock_db(items)
    final    = _make_final_state({})   # no holdings — position closed
    portfolio = _mock_portfolio_obj(cash=0.0)
    final.cash_balance = Decimal("0.0")

    plan = _generate_execution_plan(
        db=db, portfolio_id=1, portfolio=portfolio,
        final_state=final, snapshot_days=[],
        from_date=None, confidence=_make_confidence(),
        validator=None, skip_snapshots=True,
    )

    delete_ops = [o for o in plan.operations
                  if o.table == "PortfolioItem" and o.operation == "DELETE"]
    assert len(delete_ops) == 1
    assert delete_ops[0].object_id == "CPALL.BK"
    assert plan.summary.item_deletes == 1


def test_execution_plan_portfolio_cash_update():
    """Changed cash balance generates Portfolio UPDATE operation."""
    db        = _make_mock_db([])
    final     = _make_final_state({})
    portfolio = _mock_portfolio_obj(cash=50_000.0)
    final.cash_balance = Decimal("75000.0")   # different from current

    plan = _generate_execution_plan(
        db=db, portfolio_id=1, portfolio=portfolio,
        final_state=final, snapshot_days=[],
        from_date=None, confidence=_make_confidence(),
        validator=None, skip_snapshots=True,
    )

    port_ops = [o for o in plan.operations if o.table == "Portfolio"]
    assert len(port_ops) == 1
    assert port_ops[0].operation == "UPDATE"
    assert port_ops[0].field == "cash_balance"
    assert "cash_balance" in plan.summary.portfolio_updated_fields


def test_execution_plan_total_write_operations_count():
    """total_write_operations is object-level (not field-level)."""
    items    = [_mock_item("AOT.BK", 100.0, 75.5)]   # will have 2 field diffs
    db       = _make_mock_db(items)
    # Both shares and avg_cost differ → 2 UPDATE ops, but 1 object
    final    = _make_final_state({"AOT.BK": (110.0, 78.0)})
    portfolio = _mock_portfolio_obj(cash=0.0)
    final.cash_balance = Decimal("0.0")

    plan = _generate_execution_plan(
        db=db, portfolio_id=1, portfolio=portfolio,
        final_state=final, snapshot_days=[],
        from_date=None, confidence=_make_confidence(),
        validator=None, skip_snapshots=True,
    )

    assert plan.summary.item_updates == 1              # 1 object updated
    assert plan.summary.total_write_operations == 1    # object-level count
    # But two PlanOperation records generated (one per field)
    update_ops = [o for o in plan.operations
                  if o.table == "PortfolioItem" and o.operation == "UPDATE"]
    assert len(update_ops) == 2


# ══════════════════════════════════════════════════════════════════════════════
# Phase 6.7C — Effective Ledger Replay Integration
# ══════════════════════════════════════════════════════════════════════════════

# ── Integration helpers ────────────────────────────────────────────────────────

def _make_portfolio_obj(id: int = 1, name: str = "Test", cash: float = 0.0) -> MagicMock:
    p = MagicMock()
    p.id = id
    p.name = name
    p.cash_balance = cash
    return p


def _make_raw_tx_mock(tx_id: int) -> MagicMock:
    t = MagicMock()
    t.id = tx_id
    return t


def _make_repair_ns(
    repair_id: int,
    tx_id: int | None,
    repair_type: str = "EXCLUDE",
) -> SimpleNamespace:
    return SimpleNamespace(
        id             = repair_id,
        transaction_id = tx_id,
        repair_type    = repair_type,
        reason         = "test",
        reason_code    = None,
        is_active      = True,
    )


def _clean_report(portfolio_id: int = 1) -> LedgerValidationReport:
    return LedgerValidationReport(
        portfolio_id           = portfolio_id,
        portfolio_name         = "Test",
        transactions_inspected = 0,
    )


def _make_rebuild_mock_db(
    portfolio: MagicMock,
    raw_txs:   list,
    items:     list | None = None,
) -> MagicMock:
    """Mock DB session sufficient for rebuild_portfolio(skip_snapshots=True, dry_run=True)."""
    from models.database import Portfolio, Transaction, PortfolioItem, PortfolioSnapshot

    items = items or []
    db    = MagicMock()

    def _query(model):
        m = MagicMock()
        if model is Portfolio:
            m.filter_by.return_value.first.return_value = portfolio
        elif model is Transaction:
            m.filter_by.return_value.order_by.return_value.all.return_value = raw_txs
        elif model is PortfolioItem:
            m.filter_by.return_value.all.return_value = items
            m.filter_by.return_value.delete.return_value = None
        elif model is PortfolioSnapshot:
            snap_m = MagicMock()
            snap_m.all.return_value                   = []
            snap_m.order_by.return_value.all.return_value = []
            snap_m.filter.return_value.all.return_value   = []
            m.filter_by.return_value = snap_m
        return m

    db.query.side_effect = _query
    return db


def _run(
    db,
    portfolio_id:   int  = 1,
    workspace_id:   int  = 1,
    apply_repairs:  bool = True,
    skip_snapshots: bool = True,
    dry_run:        bool = True,
) -> RebuildResult:
    return asyncio.run(rebuild_portfolio(
        db             = db,
        portfolio_id   = portfolio_id,
        workspace_id   = workspace_id,
        skip_snapshots = skip_snapshots,
        dry_run        = dry_run,
        apply_repairs  = apply_repairs,
    ))


# ── 34. RebuildResult new fields default to zero / empty ──────────────────────

def test_rebuild_result_new_fields_default_to_zero():
    r = RebuildResult(portfolio_id=1, portfolio_name="P", success=True)
    assert r.effective_transaction_count == 0
    assert r.excluded_transaction_count  == 0
    assert r.repairs_applied             == 0
    assert r.repair_ids                  == []


# ── 35. apply_repairs=True with a single EXCLUDE repair ───────────────────────

def test_rebuild_apply_repairs_excludes_buy_transaction():
    """Excluded BUY must not appear in final holdings; counts are correct."""
    portfolio = _make_portfolio_obj(cash=100_000.0)
    db        = _make_rebuild_mock_db(portfolio, [_make_raw_tx_mock(1), _make_raw_tx_mock(2)])

    ctxs = [
        _ctx(id=1, transaction_type="DEPOSIT", raw_symbol=None, canonical_symbol=None,
             shares=0.0, total_amount=100_000.0),
        _ctx(id=2, transaction_type="BUY", shares=100.0, total_amount=7_550.0,
             canonical_symbol="AOT.BK"),
    ]
    repair = _make_repair_ns(repair_id=10, tx_id=2)

    with patch("services.portfolio_rebuilder.canonicalize_transactions", return_value=ctxs), \
         patch("services.portfolio_rebuilder.load_active_repairs", return_value=[repair]), \
         patch("services.portfolio_rebuilder.validate_portfolio_ledger",
               new=AsyncMock(return_value=_clean_report())):
        r = _run(db, apply_repairs=True)

    assert r.success
    assert r.repairs_applied             == 1
    assert r.excluded_transaction_count  == 1
    assert r.effective_transaction_count == 1   # only DEPOSIT
    assert r.transactions_replayed       == 1
    assert r.repair_ids                  == [10]
    assert r.reconstructed_holdings_count == 0
    assert r.reconstructed_cash == pytest.approx(100_000.0)


# ── 36. apply_repairs=False — overlay never called, all txs replayed ──────────

def test_rebuild_apply_repairs_false_skips_overlay():
    """apply_repairs=False must not call load_active_repairs and replays every tx."""
    portfolio = _make_portfolio_obj(cash=100_000.0)
    db        = _make_rebuild_mock_db(portfolio, [_make_raw_tx_mock(1), _make_raw_tx_mock(2)])

    ctxs = [
        _ctx(id=1, transaction_type="DEPOSIT", raw_symbol=None, canonical_symbol=None,
             shares=0.0, total_amount=100_000.0),
        _ctx(id=2, transaction_type="BUY", shares=100.0, total_amount=7_550.0,
             canonical_symbol="AOT.BK"),
    ]
    repair = _make_repair_ns(repair_id=10, tx_id=2)

    with patch("services.portfolio_rebuilder.canonicalize_transactions", return_value=ctxs), \
         patch("services.portfolio_rebuilder.load_active_repairs", return_value=[repair]) as mock_load, \
         patch("services.portfolio_rebuilder.validate_portfolio_ledger",
               new=AsyncMock(return_value=_clean_report())):
        r = _run(db, apply_repairs=False)

    mock_load.assert_not_called()
    assert r.success
    assert r.repairs_applied             == 0
    assert r.excluded_transaction_count  == 0
    assert r.effective_transaction_count == 2
    assert r.transactions_replayed       == 2
    assert r.repair_ids                  == []
    assert r.reconstructed_holdings_count == 1   # BUY replayed normally


# ── 37. Empty repair list — no exclusions, counts stay zero ───────────────────

def test_rebuild_empty_repair_list_is_no_op():
    portfolio = _make_portfolio_obj(cash=50_000.0)
    db        = _make_rebuild_mock_db(portfolio, [_make_raw_tx_mock(1)])

    ctxs = [_ctx(id=1, transaction_type="DEPOSIT", raw_symbol=None, canonical_symbol=None,
                 shares=0.0, total_amount=50_000.0)]

    with patch("services.portfolio_rebuilder.canonicalize_transactions", return_value=ctxs), \
         patch("services.portfolio_rebuilder.load_active_repairs", return_value=[]), \
         patch("services.portfolio_rebuilder.validate_portfolio_ledger",
               new=AsyncMock(return_value=_clean_report())):
        r = _run(db, apply_repairs=True)

    assert r.success
    assert r.repairs_applied             == 0
    assert r.excluded_transaction_count  == 0
    assert r.effective_transaction_count == 1
    assert r.transactions_replayed       == 1
    assert r.repair_ids                  == []


# ── 38. Multiple EXCLUDE repairs — counts correct, only survivors replayed ─────

def test_rebuild_multiple_exclusions_counts_and_effective_replay():
    portfolio = _make_portfolio_obj(cash=300_000.0)
    db        = _make_rebuild_mock_db(portfolio, [_make_raw_tx_mock(i) for i in range(1, 6)])

    ctxs = [
        _ctx(id=1, transaction_type="DEPOSIT", raw_symbol=None, canonical_symbol=None,
             shares=0.0, total_amount=300_000.0),
        _ctx(id=2, transaction_type="BUY", shares=100.0, total_amount=7_500.0,
             canonical_symbol="AOT.BK"),
        _ctx(id=3, transaction_type="BUY", shares=200.0, total_amount=8_000.0,
             canonical_symbol="PTT.BK"),
        _ctx(id=4, transaction_type="BUY", shares=50.0,  total_amount=3_000.0,
             canonical_symbol="KBANK.BK"),
        _ctx(id=5, transaction_type="DIVIDEND", raw_symbol=None, canonical_symbol=None,
             shares=0.0, total_amount=500.0),
    ]
    repairs = [
        _make_repair_ns(repair_id=20, tx_id=2),   # exclude AOT.BK BUY
        _make_repair_ns(repair_id=21, tx_id=4),   # exclude KBANK.BK BUY
    ]

    with patch("services.portfolio_rebuilder.canonicalize_transactions", return_value=ctxs), \
         patch("services.portfolio_rebuilder.load_active_repairs", return_value=repairs), \
         patch("services.portfolio_rebuilder.validate_portfolio_ledger",
               new=AsyncMock(return_value=_clean_report())):
        r = _run(db, apply_repairs=True)

    assert r.success
    assert r.repairs_applied             == 2
    assert r.excluded_transaction_count  == 2
    assert r.effective_transaction_count == 3    # DEPOSIT, PTT.BK BUY, DIVIDEND
    assert r.transactions_replayed       == 3
    assert r.repair_ids                  == [20, 21]
    assert r.reconstructed_holdings_count == 1   # only PTT.BK
    assert r.reconstructed_cash == pytest.approx(300_000.0 - 8_000.0 + 500.0)


# ── 39. Execution plan transaction counts match overlay results ────────────────

def test_rebuild_execution_plan_reflects_effective_count():
    """transactions_replayed must equal effective_transaction_count."""
    portfolio = _make_portfolio_obj(cash=200_000.0)
    db        = _make_rebuild_mock_db(portfolio, [_make_raw_tx_mock(i) for i in range(1, 4)])

    ctxs = [
        _ctx(id=1, transaction_type="DEPOSIT", raw_symbol=None, canonical_symbol=None,
             shares=0.0, total_amount=200_000.0),
        _ctx(id=2, transaction_type="BUY", shares=100.0, total_amount=7_550.0,
             canonical_symbol="AOT.BK"),
        _ctx(id=3, transaction_type="BUY", shares=200.0, total_amount=8_000.0,
             canonical_symbol="PTT.BK"),
    ]
    repair = _make_repair_ns(repair_id=30, tx_id=2)

    with patch("services.portfolio_rebuilder.canonicalize_transactions", return_value=ctxs), \
         patch("services.portfolio_rebuilder.load_active_repairs", return_value=[repair]), \
         patch("services.portfolio_rebuilder.validate_portfolio_ledger",
               new=AsyncMock(return_value=_clean_report())):
        r = _run(db, apply_repairs=True)

    assert r.transactions_replayed == r.effective_transaction_count == 2
    assert r.excluded_transaction_count == 1


# ── 40. validate_portfolio_ledger called with mode="effective" ─────────────────

def test_rebuild_validator_called_with_effective_mode():
    portfolio = _make_portfolio_obj(cash=0.0)
    db        = _make_rebuild_mock_db(portfolio, [_make_raw_tx_mock(1)])

    ctxs   = [_ctx(id=1, transaction_type="DEPOSIT", raw_symbol=None, canonical_symbol=None,
                   shares=0.0, total_amount=50_000.0)]
    repair = _make_repair_ns(repair_id=40, tx_id=99)   # orphan — no match

    with patch("services.portfolio_rebuilder.canonicalize_transactions", return_value=ctxs), \
         patch("services.portfolio_rebuilder.load_active_repairs", return_value=[repair]), \
         patch("services.portfolio_rebuilder.validate_portfolio_ledger",
               new=AsyncMock(return_value=_clean_report())) as mock_val:
        _run(db, apply_repairs=True)

    mock_val.assert_awaited_once()
    kw = mock_val.call_args.kwargs
    assert kw.get("mode")    == "effective"
    assert kw.get("repairs") == [repair]


# ── 41. apply_repairs=False — validator NOT called with mode/repairs ───────────

def test_rebuild_validator_no_mode_when_apply_repairs_false():
    portfolio = _make_portfolio_obj(cash=0.0)
    db        = _make_rebuild_mock_db(portfolio, [_make_raw_tx_mock(1)])

    ctxs = [_ctx(id=1, transaction_type="DEPOSIT", raw_symbol=None, canonical_symbol=None,
                 shares=0.0, total_amount=50_000.0)]

    with patch("services.portfolio_rebuilder.canonicalize_transactions", return_value=ctxs), \
         patch("services.portfolio_rebuilder.load_active_repairs", return_value=[]) as mock_load, \
         patch("services.portfolio_rebuilder.validate_portfolio_ledger",
               new=AsyncMock(return_value=_clean_report())) as mock_val:
        _run(db, apply_repairs=False)

    mock_load.assert_not_called()
    kw = mock_val.call_args.kwargs
    assert "mode"    not in kw
    assert "repairs" not in kw


# ── 42. Confidence uses effective validator finding counts ─────────────────────

def test_rebuild_confidence_derived_from_effective_validator_report():
    from services.ledger_validator import FindingSeverity
    portfolio = _make_portfolio_obj(cash=0.0)
    db        = _make_rebuild_mock_db(portfolio, [_make_raw_tx_mock(1)])

    ctxs = [_ctx(id=1, transaction_type="DEPOSIT", raw_symbol=None, canonical_symbol=None,
                 shares=0.0, total_amount=50_000.0)]

    err_finding = LedgerFinding(
        check_id="CASH_MISMATCH", severity=FindingSeverity.ERROR,
        portfolio_id=1, transaction_ids=[], symbol=None, normalized_symbol=None,
        title="test", explanation="", recommendation="",
    )
    report_with_error = LedgerValidationReport(
        portfolio_id=1, portfolio_name="Test",
        transactions_inspected=1, findings=[err_finding],
    )

    with patch("services.portfolio_rebuilder.canonicalize_transactions", return_value=ctxs), \
         patch("services.portfolio_rebuilder.load_active_repairs", return_value=[]), \
         patch("services.portfolio_rebuilder.validate_portfolio_ledger",
               new=AsyncMock(return_value=report_with_error)):
        r = _run(db, apply_repairs=True)

    assert r.ledger_errors    == 1
    assert r.ledger_criticals == 0
    assert r.confidence_report is not None
    assert r.confidence_report.ledger_integrity < 100.0


# ── 43. SUPPRESS_FINDING repair — tx stays in effective list ──────────────────

def test_rebuild_suppress_finding_does_not_exclude_transaction():
    """SUPPRESS_FINDING repairs pass through apply_repair_overlay unchanged."""
    portfolio = _make_portfolio_obj(cash=100_000.0)
    db        = _make_rebuild_mock_db(portfolio, [_make_raw_tx_mock(1), _make_raw_tx_mock(2)])

    ctxs = [
        _ctx(id=1, transaction_type="DEPOSIT", raw_symbol=None, canonical_symbol=None,
             shares=0.0, total_amount=100_000.0),
        _ctx(id=2, transaction_type="BUY", shares=100.0, total_amount=7_550.0,
             canonical_symbol="AOT.BK"),
    ]
    repair = _make_repair_ns(repair_id=50, tx_id=2, repair_type="SUPPRESS_FINDING")

    with patch("services.portfolio_rebuilder.canonicalize_transactions", return_value=ctxs), \
         patch("services.portfolio_rebuilder.load_active_repairs", return_value=[repair]), \
         patch("services.portfolio_rebuilder.validate_portfolio_ledger",
               new=AsyncMock(return_value=_clean_report())):
        r = _run(db, apply_repairs=True)

    assert r.repairs_applied             == 0    # no exclusions
    assert r.excluded_transaction_count  == 0
    assert r.effective_transaction_count == 2    # both transactions in effective list
    assert r.transactions_replayed       == 2
    assert r.repair_ids                  == [50]  # repair was loaded
    assert r.reconstructed_holdings_count == 1   # BUY was replayed


# ── 44. repair_ids lists all loaded repairs regardless of type ─────────────────

def test_rebuild_repair_ids_contains_all_loaded_repairs():
    portfolio = _make_portfolio_obj(cash=100_000.0)
    db        = _make_rebuild_mock_db(portfolio, [_make_raw_tx_mock(1)])

    ctxs = [_ctx(id=1, transaction_type="DEPOSIT", raw_symbol=None, canonical_symbol=None,
                 shares=0.0, total_amount=100_000.0)]
    repairs = [
        _make_repair_ns(repair_id=60, tx_id=99,  repair_type="EXCLUDE"),         # orphan
        _make_repair_ns(repair_id=61, tx_id=1,   repair_type="SUPPRESS_FINDING"),
    ]

    with patch("services.portfolio_rebuilder.canonicalize_transactions", return_value=ctxs), \
         patch("services.portfolio_rebuilder.load_active_repairs", return_value=repairs), \
         patch("services.portfolio_rebuilder.validate_portfolio_ledger",
               new=AsyncMock(return_value=_clean_report())):
        r = _run(db, apply_repairs=True)

    assert sorted(r.repair_ids)         == [60, 61]
    assert r.repairs_applied            == 0   # orphan EXCLUDE → no match; SUPPRESS → no exclude
    assert r.excluded_transaction_count == 0


# ── 45. Backward compatibility — apply_repairs=True is the safe default ────────

def test_rebuild_default_apply_repairs_true():
    """Default apply_repairs=True means load_active_repairs IS called."""
    portfolio = _make_portfolio_obj(cash=0.0)
    db        = _make_rebuild_mock_db(portfolio, [_make_raw_tx_mock(1)])

    ctxs = [_ctx(id=1, transaction_type="DEPOSIT", raw_symbol=None, canonical_symbol=None,
                 shares=0.0, total_amount=10_000.0)]

    with patch("services.portfolio_rebuilder.canonicalize_transactions", return_value=ctxs), \
         patch("services.portfolio_rebuilder.load_active_repairs", return_value=[]) as mock_load, \
         patch("services.portfolio_rebuilder.validate_portfolio_ledger",
               new=AsyncMock(return_value=_clean_report())):
        asyncio.run(rebuild_portfolio(
            db=db, portfolio_id=1, workspace_id=1,
            skip_snapshots=True, dry_run=True,
            # apply_repairs not passed → defaults to True
        ))

    mock_load.assert_called_once()


# ── 46. rebuild_all_portfolios passes apply_repairs to rebuild_portfolio ────────

def test_rebuild_all_passes_apply_repairs():
    """rebuild_all_portfolios propagates apply_repairs=False to each portfolio."""
    p = MagicMock()
    p.id   = 1
    p.name = "Test"

    db = MagicMock()
    db.query.return_value.filter_by.return_value.order_by.return_value.all.return_value = [p]

    mock_result = RebuildResult(portfolio_id=1, portfolio_name="Test", success=True)

    with patch("services.portfolio_rebuilder.rebuild_portfolio",
               new=AsyncMock(return_value=mock_result)) as mock_rebuild:
        asyncio.run(rebuild_all_portfolios(
            db=db, workspace_id=1, apply_repairs=False
        ))

    mock_rebuild.assert_awaited_once()
    kw = mock_rebuild.call_args.kwargs
    assert kw.get("apply_repairs") is False
