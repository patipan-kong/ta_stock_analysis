"""Unit tests for symbol_normalization.get_yfinance_symbol().

All tests are pure — no network calls, no DB access.
"""
import pytest

from services.symbol_normalization import get_yfinance_symbol


# ── DR symbols (with .BK suffix — stored form in DR awareness lookups) ─────────

def test_nvda01_bk_normalizes_to_nvda():
    """NVDA01.BK is a DR certificate → strip .BK and DR suffix → NVDA."""
    assert get_yfinance_symbol("NVDA01.BK") == "NVDA"


def test_micron01_bk_normalizes_to_mu():
    """MICRON01.BK → alias MICRON → MU (company-name DR prefix)."""
    assert get_yfinance_symbol("MICRON01.BK") == "MU"


# ── DR symbols (without .BK — user-entered convention in Decision Workspace) ────

def test_nvda01_normalizes_to_nvda():
    assert get_yfinance_symbol("NVDA01") == "NVDA"


def test_googl01_normalizes_to_googl():
    assert get_yfinance_symbol("GOOGL01") == "GOOGL"


def test_micron01_normalizes_to_mu():
    assert get_yfinance_symbol("MICRON01") == "MU"


def test_amd80_normalizes_to_amd():
    assert get_yfinance_symbol("AMD80") == "AMD"


# ── Thai SET stocks — pure alphabetic → append .BK ─────────────────────────────

def test_bh_appends_bk():
    assert get_yfinance_symbol("BH") == "BH.BK"


def test_glif_appends_bk():
    assert get_yfinance_symbol("GLIF") == "GLIF.BK"


def test_aot_appends_bk():
    assert get_yfinance_symbol("AOT") == "AOT.BK"


# ── Already-normalised symbols — unchanged ────────────────────────────────────

def test_bh_bk_unchanged():
    assert get_yfinance_symbol("BH.BK") == "BH.BK"


def test_aot_bk_unchanged():
    assert get_yfinance_symbol("AOT.BK") == "AOT.BK"


def test_glif_bk_unchanged():
    assert get_yfinance_symbol("GLIF.BK") == "GLIF.BK"


# ── Other exchange suffixes — unchanged ───────────────────────────────────────

def test_other_suffix_unchanged():
    assert get_yfinance_symbol("RELIANCE.NS") == "RELIANCE.NS"


# ── Case insensitivity ────────────────────────────────────────────────────────

def test_lowercase_dr_normalized():
    assert get_yfinance_symbol("nvda01") == "NVDA"


def test_lowercase_thai_appends_bk():
    assert get_yfinance_symbol("glif") == "GLIF.BK"


# ── Edge cases ────────────────────────────────────────────────────────────────

def test_empty_string_returns_empty():
    assert get_yfinance_symbol("") == ""


def test_whitespace_stripped():
    assert get_yfinance_symbol("  NVDA01  ") == "NVDA"
