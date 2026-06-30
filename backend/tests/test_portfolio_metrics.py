"""Pure unit tests for services/portfolio_metrics.py.

No database, no mocks, no network — compute_period_metrics() is a pure
function, so every test calls it directly with hand-built CanonicalTransaction
inputs and asserts on the returned PeriodMetrics.

Coverage
--------
  1.  No prior NAV (prev_nav=None) -> return fields are None, others still computed
  2.  prev_nav <= 0 -> same as above
  3.  DEPOSIT counted in net_external_cash_flow
  4.  WITHDRAW counted in net_external_cash_flow (negative)
  5.  INITIAL_CASH counted alongside DEPOSIT
  6.  net_external_cash_flow is None when zero (rounding convention)
  7.  INITIAL_POSITION valued at price_lookup price
  8.  INITIAL_POSITION falls back to price_per_share when symbol absent from price_lookup
  9.  QUANTITY_CORRECTION upward delta produces a positive strip
  10. QUANTITY_CORRECTION downward delta produces a negative strip (signed-delta fix)
  11. SELL contributes realized_pnl and fees to period decomposition
  12. BUY contributes fees only (no realized_pnl)
  13. DIVIDEND counted in period_dividend_income
  14. investment_return_pct / investment_return_amount / daily_return_pct formula
  15. cumulative_realized_pnl = prev_cumulative + period_realized_pnl
  16. Empty period_transactions -> all period fields None, cumulative unchanged
  17. Mixed window: multiple transaction types combine correctly
"""
from __future__ import annotations

import os
import sys
from datetime import date
from decimal import Decimal

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.transaction_canonicalizer import CanonicalTransaction
from services.portfolio_metrics import PeriodMetrics, compute_period_metrics


def _ctx(
    id: int = 1,
    transaction_type: str = "BUY",
    raw_symbol: str | None = "AOT.BK",
    shares: float = 0.0,
    price_per_share: float = 0.0,
    total_amount: float = 0.0,
    fees: float = 0.0,
    taxes: float = 0.0,
    qty_correction_delta: Decimal | None = None,
    realized_pnl: float | None = None,
) -> CanonicalTransaction:
    return CanonicalTransaction(
        id                   = id,
        transaction_type     = transaction_type,
        raw_symbol           = raw_symbol,
        canonical_symbol     = raw_symbol,
        shares               = Decimal(str(shares)),
        price_per_share      = Decimal(str(price_per_share)),
        total_amount         = Decimal(str(total_amount)),
        fees                 = Decimal(str(fees)),
        taxes                = Decimal(str(taxes)),
        transaction_date     = date(2026, 6, 1),
        created_at           = None,
        sector               = None,
        notes                = None,
        qty_correction_delta = qty_correction_delta,
        realized_pnl         = realized_pnl,
    )


def _compute(txs, curr_nav=100_000.0, prev_nav=100_000.0, price_lookup=None,
             prev_cumulative_realized_pnl=0.0) -> PeriodMetrics:
    return compute_period_metrics(
        curr_nav=curr_nav,
        prev_nav=prev_nav,
        period_transactions=txs,
        price_lookup=price_lookup,
        prev_cumulative_realized_pnl=prev_cumulative_realized_pnl,
    )


# ── 1-2. No valid prior NAV ──────────────────────────────────────────────────

def test_prev_nav_none_yields_none_return_fields_but_still_computes_others():
    txs = [_ctx(1, "DEPOSIT", total_amount=10_000.0)]
    m = _compute(txs, curr_nav=110_000.0, prev_nav=None)
    assert m.investment_return_pct is None
    assert m.investment_return_amount is None
    assert m.daily_return_pct is None
    assert m.net_external_cash_flow == pytest.approx(10_000.0)


def test_prev_nav_zero_yields_none_return_fields():
    txs = [_ctx(1, "DEPOSIT", total_amount=10_000.0)]
    m = _compute(txs, curr_nav=110_000.0, prev_nav=0.0)
    assert m.investment_return_pct is None
    assert m.net_external_cash_flow == pytest.approx(10_000.0)


# ── 3-6. Cash flows ──────────────────────────────────────────────────────────

def test_deposit_counted_in_net_ecf():
    m = _compute([_ctx(1, "DEPOSIT", total_amount=10_000.0)])
    assert m.net_external_cash_flow == pytest.approx(10_000.0)


def test_withdraw_counted_negative_in_net_ecf():
    m = _compute([_ctx(1, "WITHDRAW", total_amount=4_000.0)])
    assert m.net_external_cash_flow == pytest.approx(-4_000.0)


def test_initial_cash_counted_alongside_deposit():
    txs = [_ctx(1, "DEPOSIT", total_amount=5_000.0), _ctx(2, "INITIAL_CASH", total_amount=2_000.0)]
    m = _compute(txs)
    assert m.net_external_cash_flow == pytest.approx(7_000.0)


def test_net_ecf_none_when_zero():
    txs = [_ctx(1, "DEPOSIT", total_amount=1_000.0), _ctx(2, "WITHDRAW", total_amount=1_000.0)]
    m = _compute(txs)
    assert m.net_external_cash_flow is None


# ── 7-8. INITIAL_POSITION valuation ──────────────────────────────────────────

def test_initial_position_valued_at_price_lookup():
    txs = [_ctx(1, "INITIAL_POSITION", raw_symbol="SCB.BK", shares=1_000.0, price_per_share=50.0)]
    m = _compute(txs, price_lookup={"SCB.BK": 120.0})
    assert m.imported_asset_value == pytest.approx(120_000.0)


def test_initial_position_falls_back_to_price_per_share():
    txs = [_ctx(1, "INITIAL_POSITION", raw_symbol="SCB.BK", shares=1_000.0, price_per_share=50.0)]
    m = _compute(txs, price_lookup={})
    assert m.imported_asset_value == pytest.approx(50_000.0)


# ── 9-10. QUANTITY_CORRECTION (signed) ───────────────────────────────────────

def test_quantity_correction_upward_strips_positive_amount():
    txs = [_ctx(1, "QUANTITY_CORRECTION", raw_symbol="PTT.BK", price_per_share=30.0,
                qty_correction_delta=Decimal("10"))]
    m = _compute(txs)
    assert m.manual_adjustment_value == pytest.approx(300.0)


def test_quantity_correction_downward_strips_negative_amount():
    """Signed-delta fix (frozen doc Section 7): a downward correction must
    strip a NEGATIVE amount, since equity left the books without a trade.
    Using abs() here would double-subtract a downward correction's NAV drop."""
    txs = [_ctx(1, "QUANTITY_CORRECTION", raw_symbol="PTT.BK", price_per_share=30.0,
                qty_correction_delta=Decimal("-10"))]
    m = _compute(txs)
    assert m.manual_adjustment_value == pytest.approx(-300.0)


# ── 11-13. Period decomposition ──────────────────────────────────────────────

def test_sell_contributes_realized_pnl_and_fees():
    txs = [_ctx(1, "SELL", fees=60.0, taxes=4.2, realized_pnl=750.0)]
    m = _compute(txs)
    assert m.period_realized_pnl == pytest.approx(750.0)
    assert m.period_fees_paid == pytest.approx(64.2)


def test_buy_contributes_fees_only():
    txs = [_ctx(1, "BUY", fees=50.0, taxes=3.5)]
    m = _compute(txs)
    assert m.period_fees_paid == pytest.approx(53.5)
    assert m.period_realized_pnl is None


def test_dividend_counted_in_period_income():
    m = _compute([_ctx(1, "DIVIDEND", total_amount=1_200.0)])
    assert m.period_dividend_income == pytest.approx(1_200.0)


# ── 14. Return formula ────────────────────────────────────────────────────────

def test_investment_return_formula():
    txs = [_ctx(1, "DEPOSIT", total_amount=10_000.0)]
    m = _compute(txs, curr_nav=115_000.0, prev_nav=100_000.0)
    # pure_gain = 115,000 - 100,000 - 10,000(net_ecf) - 0 - 0 = 5,000
    assert m.investment_return_amount == pytest.approx(5_000.0)
    assert m.investment_return_pct == pytest.approx(5.0)
    assert m.daily_return_pct == pytest.approx(m.investment_return_pct)


# ── 15-16. cumulative_realized_pnl ────────────────────────────────────────────

def test_cumulative_realized_pnl_accumulates():
    txs = [_ctx(1, "SELL", realized_pnl=500.0)]
    m = _compute(txs, prev_cumulative_realized_pnl=2_000.0)
    assert m.cumulative_realized_pnl == pytest.approx(2_500.0)


def test_empty_period_transactions():
    m = _compute([], prev_cumulative_realized_pnl=2_000.0)
    assert m.net_external_cash_flow is None
    assert m.imported_asset_value is None
    assert m.manual_adjustment_value is None
    assert m.period_realized_pnl is None
    assert m.period_dividend_income is None
    assert m.period_fees_paid is None
    assert m.cumulative_realized_pnl == pytest.approx(2_000.0)


# ── 17. Mixed window ──────────────────────────────────────────────────────────

def test_mixed_window_combines_correctly():
    txs = [
        _ctx(1, "DEPOSIT", total_amount=10_000.0),
        _ctx(2, "BUY", fees=50.0, taxes=3.5),
        _ctx(3, "SELL", fees=60.0, taxes=4.2, realized_pnl=750.0),
        _ctx(4, "DIVIDEND", total_amount=200.0),
        _ctx(5, "INITIAL_POSITION", raw_symbol="SCB.BK", shares=100.0, price_per_share=100.0),
        _ctx(6, "QUANTITY_CORRECTION", raw_symbol="PTT.BK", price_per_share=30.0,
             qty_correction_delta=Decimal("5")),
    ]
    m = _compute(txs, curr_nav=200_000.0, prev_nav=100_000.0, price_lookup={"SCB.BK": 110.0})
    assert m.net_external_cash_flow == pytest.approx(10_000.0)
    assert m.imported_asset_value == pytest.approx(11_000.0)
    assert m.manual_adjustment_value == pytest.approx(150.0)
    assert m.period_realized_pnl == pytest.approx(750.0)
    assert m.period_dividend_income == pytest.approx(200.0)
    assert m.period_fees_paid == pytest.approx(117.7)
    pure_gain = 200_000.0 - 100_000.0 - 10_000.0 - 11_000.0 - 150.0
    assert m.investment_return_amount == pytest.approx(pure_gain)
