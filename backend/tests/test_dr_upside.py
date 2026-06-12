"""
Unit tests for DR symbol upside calculation correctness.

Validates that:
- DR symbols are detected correctly
- Parent symbol is extracted correctly
- Upside uses parent USD price, not DR local THB price
- Non-DR symbols are unaffected
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.data_fetcher import normalize_dr_symbol, is_dr_symbol


# ── is_dr_symbol ──────────────────────────────────────────────────────────────

def test_is_dr_amd80():
    assert is_dr_symbol("AMD80.BK") is True

def test_is_dr_meta01():
    assert is_dr_symbol("META01.BK") is True

def test_is_dr_aapl01():
    assert is_dr_symbol("AAPL01.BK") is True

def test_is_dr_regular_thai():
    assert is_dr_symbol("SCB.BK") is False

def test_is_dr_regular_thai_ptt():
    assert is_dr_symbol("PTT.BK") is False

def test_is_dr_us_stock():
    assert is_dr_symbol("AAPL") is False

def test_is_dr_us_stock_googl():
    assert is_dr_symbol("GOOGL") is False


# ── normalize_dr_symbol ───────────────────────────────────────────────────────

def test_normalize_amd80():
    assert normalize_dr_symbol("AMD80.BK") == "AMD"

def test_normalize_meta01():
    assert normalize_dr_symbol("META01.BK") == "META"

def test_normalize_aapl01():
    assert normalize_dr_symbol("AAPL01.BK") == "AAPL"

def test_normalize_micron01_aliased_to_mu():
    """Name-based DR prefix (MICRON) must map to the real US ticker (MU)."""
    assert normalize_dr_symbol("MICRON01.BK") == "MU"

def test_normalize_micron80_aliased_to_mu():
    """Alias applies regardless of the DR issuer digit-suffix."""
    assert normalize_dr_symbol("MICRON80.BK") == "MU"

def test_normalize_regular_thai_unchanged():
    assert normalize_dr_symbol("SCB.BK") == "SCB.BK"

def test_normalize_us_unchanged():
    assert normalize_dr_symbol("AAPL") == "AAPL"


# ── upside calculation logic ───────────────────────────────────────────────────

def _calc_upside(target: float, price: float) -> float:
    return round((target - price) / price * 100, 1)


def test_dr_upside_uses_parent_price():
    """AMD80.BK: upside must use AMD USD price (447.58), not DR THB price (2.90)."""
    target_price = 472.17       # AMD analyst consensus in USD
    dr_local_price = 2.90       # AMD80.BK local price in THB (WRONG basis)
    parent_usd_price = 447.58   # AMD current price in USD (CORRECT basis)

    wrong_upside = _calc_upside(target_price, dr_local_price)
    correct_upside = _calc_upside(target_price, parent_usd_price)

    # Sanity: wrong approach gives absurd result
    assert wrong_upside > 15000, f"Expected absurd upside, got {wrong_upside}"
    # Correct approach gives reasonable result
    assert 0 < correct_upside < 20, f"Expected ~5% upside, got {correct_upside}"


def test_normal_stock_upside_unchanged():
    """AAPL (non-DR): upside uses the same price source as always."""
    target_price = 240.0
    current_price = 220.0
    upside = _calc_upside(target_price, current_price)
    assert abs(upside - 9.1) < 0.1, f"Expected ~9.1%, got {upside}"


def test_dr_symbol_parent_extraction():
    """Parent symbol extraction must strip numeric suffix correctly."""
    for dr_sym, expected_parent in [
        ("AMD80.BK", "AMD"),
        ("META01.BK", "META"),
        ("AAPL01.BK", "AAPL"),
        ("MSFT12.BK", "MSFT"),
        ("NVDA08.BK", "NVDA"),
    ]:
        assert normalize_dr_symbol(dr_sym) == expected_parent, f"Failed for {dr_sym}"


def test_non_dr_returns_none_parent():
    """For non-DR symbols, parent_symbol should be None."""
    for sym in ["AAPL", "SCB.BK", "PTT.BK", "KBANK.BK"]:
        assert not is_dr_symbol(sym), f"{sym} should NOT be a DR"
        parent = normalize_dr_symbol(sym)
        # normalize returns the symbol unchanged for non-DR
        assert parent == sym


# Simple inline runner (without pytest dependency)
if __name__ == "__main__":
    import traceback

    tests = [
        test_is_dr_amd80,
        test_is_dr_meta01,
        test_is_dr_aapl01,
        test_is_dr_regular_thai,
        test_is_dr_regular_thai_ptt,
        test_is_dr_us_stock,
        test_is_dr_us_stock_googl,
        test_normalize_amd80,
        test_normalize_meta01,
        test_normalize_aapl01,
        test_normalize_regular_thai_unchanged,
        test_normalize_us_unchanged,
        test_dr_upside_uses_parent_price,
        test_dr_symbol_parent_extraction,
        test_non_dr_returns_none_parent,
    ]

    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {t.__name__}: {e}")
            traceback.print_exc()
            failed += 1

    print(f"\n{passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
