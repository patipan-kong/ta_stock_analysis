"""Regression tests for transaction symbol normalization.

Covers the single transaction entry-point normalizer used by BUY/SELL/
INITIAL_POSITION/QUANTITY_CORRECTION/DIVIDEND transaction routes.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from main import _normalize_transaction_symbol


def test_trims_and_uppercases_symbol() -> None:
    assert _normalize_transaction_symbol("  kbank  ") == "KBANK.BK"
    assert _normalize_transaction_symbol("  qqq  ") == "QQQ"


def test_known_set_symbol_auto_appends_bk_suffix() -> None:
    assert _normalize_transaction_symbol("KBANK") == "KBANK.BK"
    assert _normalize_transaction_symbol("SCB") == "SCB.BK"
    assert _normalize_transaction_symbol("PTT") == "PTT.BK"


def test_does_not_blindly_append_bk_for_us_symbols() -> None:
    assert _normalize_transaction_symbol("QQQ") == "QQQ"
    assert _normalize_transaction_symbol("SPY") == "SPY"
    assert _normalize_transaction_symbol("AAPL") == "AAPL"
    assert _normalize_transaction_symbol("NVDA") == "NVDA"


def test_preserves_symbols_with_existing_suffix() -> None:
    assert _normalize_transaction_symbol("micron01.bk") == "MICRON01.BK"
    assert _normalize_transaction_symbol("kbank.bk") == "KBANK.BK"
    assert _normalize_transaction_symbol("BRK.B") == "BRK.B"


def test_unknown_suffixless_symbol_is_left_as_is() -> None:
    # Unknown suffixless ticker should not be force-converted to .BK.
    assert _normalize_transaction_symbol("XYZ123") == "XYZ123"
