"""Tests for services/transaction_canonicalizer.py — Phase 1.

All tests are pure-Python and require no database or network.
ORM rows are simulated with SimpleNamespace objects that carry the same
attribute names as the Transaction SQLAlchemy model.

Coverage
--------
Field mapping
  1.  All scalar fields preserved correctly
  2.  transaction_date DateTime → date
  3.  created_at DateTime → datetime (preserved as-is)
  4.  sector empty-string normalised to None
  5.  notes empty-string normalised to None

Symbol handling
  6.  Thai symbol without suffix → canonical gets .BK; raw preserved
  7.  Thai symbol already with .BK → canonical unchanged; raw preserved
  8.  None symbol → raw_symbol=None, canonical_symbol=None
  9.  Whitespace-only symbol → treated as None

Decimal conversion
 10.  Float fields converted to Decimal
 11.  None shares → Decimal('0')
 12.  None price_per_share → Decimal('0')
 13.  None fees / taxes → Decimal('0')

QUANTITY_CORRECTION parsing
 14.  Positive delta parsed from notes
 15.  Negative delta parsed from notes
 16.  Missing notes → falls back to tx.shares
 17.  Notes present but pattern absent → falls back to tx.shares
 18.  Non-QUANTITY_CORRECTION type → qty_correction_delta is None

SELL realized P&L parsing
 19.  Positive P&L parsed from notes
 20.  Negative P&L parsed from notes
 21.  Zero P&L parsed from notes
 22.  SELL with notes but no P&L pattern → None
 23.  SELL with notes=None → None
 24.  Non-SELL type → realized_pnl is None

Sorting
 25.  Multiple transactions sorted by (transaction_date, id)
 26.  Same-date transactions sorted by id

Immutability
 27.  CanonicalTransaction is frozen; attribute assignment raises TypeError

Edge cases
 28.  Empty input → empty tuple
 29.  Single transaction
 30.  Output is a tuple, not a list
"""
from __future__ import annotations

import sys
import os
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.transaction_canonicalizer import (
    CanonicalTransaction,
    canonicalize_transactions,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _tx(
    id: int = 1,
    transaction_type: str = "BUY",
    symbol: str | None = "AOT.BK",
    shares: float | None = 100.0,
    price_per_share: float | None = 75.50,
    total_amount: float = 7550.0,
    fees: float = 50.0,
    taxes: float | None = 3.50,
    transaction_date: datetime = datetime(2025, 1, 15, 9, 30),
    created_at: datetime = datetime(2025, 1, 15, 10, 0),
    sector: str | None = "Transport",
    notes: str | None = None,
) -> SimpleNamespace:
    """Factory for mock Transaction ORM objects."""
    return SimpleNamespace(
        id               = id,
        transaction_type = transaction_type,
        symbol           = symbol,
        shares           = shares,
        price_per_share  = price_per_share,
        total_amount     = total_amount,
        fees             = fees,
        taxes            = taxes,
        transaction_date = transaction_date,
        created_at       = created_at,
        sector           = sector,
        notes            = notes,
    )


# ── Field mapping ─────────────────────────────────────────────────────────────

def test_all_scalar_fields_preserved():
    tx = _tx(
        id               = 42,
        transaction_type = "BUY",
        symbol           = "AOT.BK",
        shares           = 200.0,
        price_per_share  = 75.00,
        total_amount     = 15000.0,
        fees             = 100.0,
        taxes            = 7.0,
        sector           = "Transport",
        notes            = None,
    )
    (ctx,) = canonicalize_transactions([tx])

    assert ctx.id               == 42
    assert ctx.transaction_type == "BUY"
    assert ctx.shares           == Decimal("200.0")
    assert ctx.price_per_share  == Decimal("75.0")
    assert ctx.total_amount     == Decimal("15000.0")
    assert ctx.fees             == Decimal("100.0")
    assert ctx.taxes            == Decimal("7.0")
    assert ctx.sector           == "Transport"
    assert ctx.notes            is None


def test_transaction_date_coerced_to_date():
    tx = _tx(transaction_date=datetime(2024, 6, 15, 14, 30, 55))
    (ctx,) = canonicalize_transactions([tx])
    assert ctx.transaction_date == date(2024, 6, 15)
    assert isinstance(ctx.transaction_date, date)
    assert not isinstance(ctx.transaction_date, datetime)


def test_created_at_preserved_as_datetime():
    dt = datetime(2024, 6, 15, 17, 45, 0)
    tx = _tx(created_at=dt)
    (ctx,) = canonicalize_transactions([tx])
    assert ctx.created_at == dt
    assert isinstance(ctx.created_at, datetime)


def test_sector_empty_string_normalised_to_none():
    tx = _tx(sector="")
    (ctx,) = canonicalize_transactions([tx])
    assert ctx.sector is None


def test_notes_empty_string_normalised_to_none():
    tx = _tx(notes="")
    (ctx,) = canonicalize_transactions([tx])
    assert ctx.notes is None


# ── Symbol handling ────────────────────────────────────────────────────────────

def test_thai_symbol_without_suffix_gets_bk():
    tx = _tx(symbol="KBANK")
    (ctx,) = canonicalize_transactions([tx])
    assert ctx.raw_symbol       == "KBANK"
    assert ctx.canonical_symbol == "KBANK.BK"


def test_thai_symbol_already_with_bk_unchanged():
    tx = _tx(symbol="AOT.BK")
    (ctx,) = canonicalize_transactions([tx])
    assert ctx.raw_symbol       == "AOT.BK"
    assert ctx.canonical_symbol == "AOT.BK"


def test_symbol_is_stripped_and_uppercased():
    tx = _tx(symbol="  aot.bk  ")
    (ctx,) = canonicalize_transactions([tx])
    assert ctx.raw_symbol == "AOT.BK"


def test_none_symbol_produces_none_for_both():
    tx = _tx(symbol=None, transaction_type="DEPOSIT")
    (ctx,) = canonicalize_transactions([tx])
    assert ctx.raw_symbol       is None
    assert ctx.canonical_symbol is None


def test_whitespace_only_symbol_treated_as_none():
    tx = _tx(symbol="   ", transaction_type="DEPOSIT")
    (ctx,) = canonicalize_transactions([tx])
    assert ctx.raw_symbol       is None
    assert ctx.canonical_symbol is None


# ── Decimal conversion ─────────────────────────────────────────────────────────

def test_float_fields_converted_to_decimal():
    tx = _tx(shares=123.456, price_per_share=78.9, total_amount=9753.98, fees=5.0, taxes=0.35)
    (ctx,) = canonicalize_transactions([tx])
    assert isinstance(ctx.shares,          Decimal)
    assert isinstance(ctx.price_per_share, Decimal)
    assert isinstance(ctx.total_amount,    Decimal)
    assert isinstance(ctx.fees,            Decimal)
    assert isinstance(ctx.taxes,           Decimal)


def test_none_shares_becomes_zero_decimal():
    tx = _tx(shares=None)
    (ctx,) = canonicalize_transactions([tx])
    assert ctx.shares == Decimal("0")


def test_none_price_per_share_becomes_zero_decimal():
    tx = _tx(price_per_share=None)
    (ctx,) = canonicalize_transactions([tx])
    assert ctx.price_per_share == Decimal("0")


def test_none_fees_becomes_zero_decimal():
    tx = _tx(fees=None)
    (ctx,) = canonicalize_transactions([tx])
    assert ctx.fees == Decimal("0")


def test_none_taxes_becomes_zero_decimal():
    tx = _tx(taxes=None)
    (ctx,) = canonicalize_transactions([tx])
    assert ctx.taxes == Decimal("0")


# ── QUANTITY_CORRECTION parsing ────────────────────────────────────────────────

def test_qcorr_positive_delta_parsed_from_notes():
    tx = _tx(
        transaction_type = "QUANTITY_CORRECTION",
        symbol           = "KBANK.BK",
        shares           = 5.0,
        notes            = "Quantity correction: +5.0 shares (manual adjustment)",
    )
    (ctx,) = canonicalize_transactions([tx])
    assert ctx.qty_correction_delta == Decimal("+5.0")


def test_qcorr_negative_delta_parsed_from_notes():
    tx = _tx(
        transaction_type = "QUANTITY_CORRECTION",
        symbol           = "KBANK.BK",
        shares           = 3.0,
        notes            = "Quantity correction: -3.0 shares",
    )
    (ctx,) = canonicalize_transactions([tx])
    assert ctx.qty_correction_delta == Decimal("-3.0")


def test_qcorr_missing_notes_falls_back_to_shares():
    tx = _tx(
        transaction_type = "QUANTITY_CORRECTION",
        symbol           = "KBANK.BK",
        shares           = 10.0,
        notes            = None,
    )
    (ctx,) = canonicalize_transactions([tx])
    assert ctx.qty_correction_delta == Decimal("10.0")


def test_qcorr_notes_without_pattern_falls_back_to_shares():
    tx = _tx(
        transaction_type = "QUANTITY_CORRECTION",
        symbol           = "KBANK.BK",
        shares           = 7.0,
        notes            = "Admin correction — see ticket #123",
    )
    (ctx,) = canonicalize_transactions([tx])
    assert ctx.qty_correction_delta == Decimal("7.0")


def test_qcorr_pattern_is_case_insensitive():
    tx = _tx(
        transaction_type = "QUANTITY_CORRECTION",
        symbol           = "KBANK.BK",
        shares           = 2.0,
        notes            = "quantity correction: +2.0 shares",
    )
    (ctx,) = canonicalize_transactions([tx])
    assert ctx.qty_correction_delta == Decimal("+2.0")


def test_non_qcorr_has_none_delta():
    for tx_type in ("BUY", "SELL", "DEPOSIT", "WITHDRAW", "INITIAL_POSITION", "DIVIDEND"):
        tx = _tx(transaction_type=tx_type)
        (ctx,) = canonicalize_transactions([tx])
        assert ctx.qty_correction_delta is None, f"Expected None for {tx_type}"


# ── SELL realized P&L parsing ─────────────────────────────────────────────────

def test_sell_positive_pnl_parsed():
    tx = _tx(
        transaction_type = "SELL",
        notes            = "Sell executed. Realized P&L: 1500.75",
    )
    (ctx,) = canonicalize_transactions([tx])
    assert ctx.realized_pnl == pytest.approx(1500.75)


def test_sell_negative_pnl_parsed():
    tx = _tx(
        transaction_type = "SELL",
        notes            = "Realized P&L: -320.50",
    )
    (ctx,) = canonicalize_transactions([tx])
    assert ctx.realized_pnl == pytest.approx(-320.50)


def test_sell_zero_pnl_parsed():
    tx = _tx(
        transaction_type = "SELL",
        notes            = "Realized P&L: 0.0",
    )
    (ctx,) = canonicalize_transactions([tx])
    assert ctx.realized_pnl == pytest.approx(0.0)


def test_sell_notes_without_pnl_pattern_gives_none():
    tx = _tx(
        transaction_type = "SELL",
        notes            = "Normal sell at market price",
    )
    (ctx,) = canonicalize_transactions([tx])
    assert ctx.realized_pnl is None


def test_sell_none_notes_gives_none_pnl():
    tx = _tx(transaction_type="SELL", notes=None)
    (ctx,) = canonicalize_transactions([tx])
    assert ctx.realized_pnl is None


def test_non_sell_has_none_pnl():
    for tx_type in ("BUY", "DEPOSIT", "WITHDRAW", "INITIAL_POSITION", "DIVIDEND",
                    "QUANTITY_CORRECTION"):
        tx = _tx(
            transaction_type = tx_type,
            notes            = "Realized P&L: 999.0",  # pattern present but type is not SELL
        )
        (ctx,) = canonicalize_transactions([tx])
        assert ctx.realized_pnl is None, f"Expected None for {tx_type}"


# ── Sorting ────────────────────────────────────────────────────────────────────

def test_sorted_by_transaction_date_then_id():
    txs = [
        _tx(id=3, transaction_date=datetime(2025, 3, 1)),
        _tx(id=1, transaction_date=datetime(2025, 1, 1)),
        _tx(id=2, transaction_date=datetime(2025, 2, 1)),
    ]
    result = canonicalize_transactions(txs)
    assert [c.id for c in result] == [1, 2, 3]


def test_same_date_sorted_by_id():
    same_date = datetime(2025, 6, 15)
    txs = [
        _tx(id=30, transaction_date=same_date),
        _tx(id=10, transaction_date=same_date),
        _tx(id=20, transaction_date=same_date),
    ]
    result = canonicalize_transactions(txs)
    assert [c.id for c in result] == [10, 20, 30]


def test_sort_does_not_mutate_input():
    txs = [
        _tx(id=2, transaction_date=datetime(2025, 2, 1)),
        _tx(id=1, transaction_date=datetime(2025, 1, 1)),
    ]
    original_ids = [t.id for t in txs]
    canonicalize_transactions(txs)
    assert [t.id for t in txs] == original_ids   # input list unchanged


# ── Immutability ──────────────────────────────────────────────────────────────

def test_canonical_transaction_is_frozen():
    tx = _tx()
    (ctx,) = canonicalize_transactions([tx])
    with pytest.raises((TypeError, AttributeError)):
        ctx.shares = Decimal("999")  # type: ignore[misc]


# ── Edge cases ────────────────────────────────────────────────────────────────

def test_empty_input_returns_empty_tuple():
    result = canonicalize_transactions([])
    assert result == ()
    assert isinstance(result, tuple)


def test_single_transaction():
    tx = _tx(id=99)
    result = canonicalize_transactions([tx])
    assert len(result) == 1
    assert result[0].id == 99


def test_output_is_tuple_not_list():
    result = canonicalize_transactions([_tx()])
    assert isinstance(result, tuple)


def test_created_at_none_gives_none():
    tx = _tx(created_at=None)
    (ctx,) = canonicalize_transactions([tx])
    assert ctx.created_at is None


def test_integer_total_amount_converts_to_decimal():
    tx = _tx(total_amount=10000)
    (ctx,) = canonicalize_transactions([tx])
    assert ctx.total_amount == Decimal("10000")
    assert isinstance(ctx.total_amount, Decimal)
