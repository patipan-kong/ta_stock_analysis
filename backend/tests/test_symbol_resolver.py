"""Unit tests for services.symbol_resolver.

All tests are pure — no network calls, no DB access.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from services.symbol_resolver import (
    YFINANCE_SYMBOL_MAP,
    is_dr,
    resolve_display_symbol,
    resolve_symbol,
    resolve_yfinance_symbol,
)


# ── resolve_yfinance_symbol — explicit map takes priority ─────────────────────

def test_catl01_maps_to_shenzhen():
    """CATL DR → Shenzhen-listed ticker (not a US stock)."""
    assert resolve_yfinance_symbol("CATL01") == "300750.SZ"


def test_catl01_bk_maps_to_shenzhen():
    """CATL01.BK (stored form in some legacy rows) → 300750.SZ."""
    assert resolve_yfinance_symbol("CATL01.BK") == "300750.SZ"


def test_smic01_maps_to_hk():
    """SMIC DR → Hong Kong-listed ticker."""
    assert resolve_yfinance_symbol("SMIC01") == "0981.HK"


def test_smic01_bk_maps_to_hk():
    assert resolve_yfinance_symbol("SMIC01.BK") == "0981.HK"


def test_micron01_maps_to_mu():
    """Company-name DR prefix: MICRON → MU."""
    assert resolve_yfinance_symbol("MICRON01") == "MU"


def test_micron80_maps_to_mu():
    """Same alias applies regardless of issuer digit-suffix."""
    assert resolve_yfinance_symbol("MICRON80") == "MU"


def test_micron01_bk_maps_to_mu():
    assert resolve_yfinance_symbol("MICRON01.BK") == "MU"


def test_intel01_maps_to_intc():
    assert resolve_yfinance_symbol("INTEL01") == "INTC"


def test_qualcomm01_maps_to_qcom():
    assert resolve_yfinance_symbol("QUALCOMM01") == "QCOM"


def test_explicit_map_overrides_suffix_stripping():
    """Explicit map must win even when generic stripping would give a result."""
    # Without explicit map, MICRON01 → suffix strip → MICRON (wrong).
    # With explicit map, MICRON01 → MU (correct).
    assert resolve_yfinance_symbol("MICRON01") == "MU"
    assert resolve_yfinance_symbol("MICRON01") != "MICRON"


# ── resolve_yfinance_symbol — generic suffix stripping ────────────────────────

def test_aapl80_strips_to_aapl():
    assert resolve_yfinance_symbol("AAPL80") == "AAPL"


def test_nvda01_strips_to_nvda():
    assert resolve_yfinance_symbol("NVDA01") == "NVDA"


def test_amzn01_strips_to_amzn():
    assert resolve_yfinance_symbol("AMZN01") == "AMZN"


def test_aapl80_bk_strips_to_aapl():
    assert resolve_yfinance_symbol("AAPL80.BK") == "AAPL"


def test_nvda01_bk_strips_to_nvda():
    assert resolve_yfinance_symbol("NVDA01.BK") == "NVDA"


def test_meta01_strips_to_meta():
    assert resolve_yfinance_symbol("META01") == "META"


def test_amd80_strips_to_amd():
    assert resolve_yfinance_symbol("AMD80") == "AMD"


# ── resolve_yfinance_symbol — non-DR symbols pass through unchanged ───────────

def test_thai_stock_unchanged():
    assert resolve_yfinance_symbol("PTT.BK") == "PTT.BK"


def test_thai_stock_kbank_unchanged():
    assert resolve_yfinance_symbol("KBANK.BK") == "KBANK.BK"


def test_us_ticker_unchanged():
    assert resolve_yfinance_symbol("AAPL") == "AAPL"


def test_us_ticker_spy_unchanged():
    assert resolve_yfinance_symbol("SPY") == "SPY"


def test_unknown_symbol_unchanged():
    """Symbols with no mapping and no DR pattern are returned as-is."""
    assert resolve_yfinance_symbol("UNKNOWNSYMBOL") == "UNKNOWNSYMBOL"


def test_shenzhen_ticker_unchanged():
    """Raw Shenzhen ticker passed directly is returned unchanged."""
    assert resolve_yfinance_symbol("300750.SZ") == "300750.SZ"


def test_hk_ticker_unchanged():
    assert resolve_yfinance_symbol("0981.HK") == "0981.HK"


# ── Single-digit Thai tickers are NOT treated as DRs ─────────────────────────

def test_com7_bk_unchanged():
    """COM7 has only 1 trailing digit — must not be stripped."""
    assert resolve_yfinance_symbol("COM7.BK") == "COM7.BK"


def test_pr9_bk_unchanged():
    assert resolve_yfinance_symbol("PR9.BK") == "PR9.BK"


# ── resolve_yfinance_symbol — case normalisation ──────────────────────────────

def test_lowercase_input_normalised():
    assert resolve_yfinance_symbol("nvda01") == "NVDA"


def test_mixed_case_input_normalised():
    assert resolve_yfinance_symbol("Catl01") == "300750.SZ"


def test_whitespace_stripped():
    assert resolve_yfinance_symbol("  NVDA01  ") == "NVDA"


# ── resolve_symbol — provider dispatch ───────────────────────────────────────

def test_resolve_symbol_default_provider():
    assert resolve_symbol("CATL01") == "300750.SZ"


def test_resolve_symbol_yfinance_explicit():
    assert resolve_symbol("NVDA01", provider="yfinance") == "NVDA"


def test_resolve_symbol_unknown_provider_passthrough():
    """Unknown providers receive the symbol unchanged (uppercased)."""
    assert resolve_symbol("CATL01", provider="alpha_vantage") == "CATL01"  # type: ignore[arg-type]


# ── resolve_display_symbol ────────────────────────────────────────────────────

def test_display_thai_strips_bk():
    assert resolve_display_symbol("PTT.BK") == "PTT"


def test_display_dr_no_bk_unchanged():
    assert resolve_display_symbol("NVDA01") == "NVDA01"


def test_display_us_ticker_unchanged():
    assert resolve_display_symbol("AAPL") == "AAPL"


def test_display_hk_ticker_unchanged():
    assert resolve_display_symbol("0981.HK") == "0981.HK"


def test_display_case_normalised():
    assert resolve_display_symbol("ptt.bk") == "PTT"


# ── is_dr ─────────────────────────────────────────────────────────────────────

def test_is_dr_nvda01():
    assert is_dr("NVDA01") is True


def test_is_dr_aapl80():
    assert is_dr("AAPL80") is True


def test_is_dr_catl01():
    assert is_dr("CATL01") is True


def test_is_dr_smic01():
    assert is_dr("SMIC01") is True


def test_is_dr_with_bk_suffix():
    assert is_dr("NVDA01.BK") is True


def test_is_dr_regular_thai():
    assert is_dr("PTT.BK") is False


def test_is_dr_us_ticker():
    assert is_dr("AAPL") is False


def test_is_dr_single_digit_thai():
    """Single trailing digit must not be treated as a DR."""
    assert is_dr("COM7.BK") is False


def test_is_dr_single_digit_no_suffix():
    assert is_dr("PR9") is False


def test_is_dr_lowercase_accepted():
    """is_dr normalises to uppercase internally."""
    assert is_dr("nvda01") is True


# ── YFINANCE_SYMBOL_MAP integrity ─────────────────────────────────────────────

def test_map_keys_have_no_bk_suffix():
    """All map keys must be stored without .BK."""
    for key in YFINANCE_SYMBOL_MAP:
        assert not key.endswith(".BK"), f"Key {key!r} should not end with .BK"


def test_map_keys_are_uppercase():
    for key in YFINANCE_SYMBOL_MAP:
        assert key == key.upper(), f"Key {key!r} should be uppercase"


def test_map_values_are_nonempty():
    for key, val in YFINANCE_SYMBOL_MAP.items():
        assert val, f"Map entry {key!r} has empty value"
