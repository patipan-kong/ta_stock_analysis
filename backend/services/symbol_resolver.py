"""Centralized symbol resolver for all market data providers.

Resolution order for yfinance:
  1. Explicit YFINANCE_SYMBOL_MAP lookup — highest priority
     (handles company-name DRs and non-US exchange DRs)
  2. Generic DR suffix removal — strips trailing 2+ digits and optional .BK
     (NVDA01 → NVDA, AAPL80.BK → AAPL)
  3. Return original symbol — never raises, never returns None

Platform storage conventions (DB):
  DR certificates   — stored WITHOUT .BK   (NVDA01, CATL01, MICRON01)
  Thai SET equities — stored WITH .BK      (PTT.BK, KBANK.BK, BH.BK)
  International     — stored as-is         (AAPL, 300750.SZ, 0981.HK)

All resolve_* functions accept symbols in any of the above forms, with or
without the .BK suffix, and in any case — they normalise to uppercase before
lookup.
"""
from __future__ import annotations

import re
from typing import Literal

# ── Explicit mapping table ─────────────────────────────────────────────────────
# Add entries here when either:
#   • The DR prefix is a company name, not the stock ticker (MICRON → MU)
#   • The underlying trades on a non-US exchange          (CATL01 → 300750.SZ)
#
# Keys   = SET DR symbol WITHOUT the .BK suffix (e.g. "CATL01", "MICRON01").
# Values = yfinance-compatible ticker.
#
# For company-name aliases that cover multiple issuer suffixes (01, 80, …),
# list each variant explicitly so the resolution order is unambiguous.
YFINANCE_SYMBOL_MAP: dict[str, str] = {
    # ── US tickers — DR prefix is a company name, not the ticker ──────────────
    "MICRON01":   "MU",       # Micron Technology
    "MICRON80":   "MU",
    "INTEL01":    "INTC",     # Intel Corporation
    "INTEL80":    "INTC",
    "QUALCOMM01": "QCOM",     # Qualcomm
    "QUALCOMM80": "QCOM",
    # ── Chinese A-share — Shenzhen Stock Exchange ──────────────────────────────
    "CATL01":     "300750.SZ",  # Contemporary Amperex Technology
    # ── Hong Kong Stock Exchange ───────────────────────────────────────────────
    "SMIC01":     "0981.HK",    # Semiconductor Manufacturing International Corp
    # ── Add future non-US exchange DRs here ───────────────────────────────────
    "GOLDM01": "GLDM",
}

# ── Regex helpers ──────────────────────────────────────────────────────────────
# DR certificate pattern: uppercase letters + 2+ trailing digits, optional .BK.
# The 2-digit minimum prevents single-digit Thai tickers (COM7, PR9) from
# being misidentified as DR certificates.
_DR_RE = re.compile(r"^([A-Z]+)\d{2,}(\.BK)?$")

Provider = Literal["yfinance"]   # extend as new providers are added


# ── Public API ─────────────────────────────────────────────────────────────────

def resolve_symbol(symbol: str, provider: Provider = "yfinance") -> str:
    """Resolve *symbol* to the canonical ticker accepted by *provider*.

    Args:
        symbol:   Any platform symbol (NVDA01, NVDA01.BK, PTT.BK, AAPL,
                  300750.SZ).  Case-insensitive; leading/trailing whitespace
                  is stripped.
        provider: Target data provider.  Currently only "yfinance" is
                  implemented; unknown providers receive the symbol unchanged.

    Returns:
        The ticker string accepted by *provider*.  Never raises; falls back to
        the (uppercased, stripped) original if no mapping is found.

    Examples:
        >>> resolve_symbol("NVDA01")
        'NVDA'
        >>> resolve_symbol("CATL01")
        '300750.SZ'
        >>> resolve_symbol("PTT.BK")
        'PTT.BK'
        >>> resolve_symbol("CATL01", provider="alpha_vantage")  # future
        'CATL01'
    """
    if provider == "yfinance":
        return resolve_yfinance_symbol(symbol)
    # Unknown provider — return normalised symbol unchanged so callers never
    # receive None or an exception.
    return (symbol or "").strip().upper()


def resolve_yfinance_symbol(symbol: str) -> str:
    """Return the yfinance-compatible ticker for *symbol*.

    Resolution order:
      1. Explicit YFINANCE_SYMBOL_MAP lookup (keyed by base without .BK).
      2. Generic DR suffix removal (strips trailing 2+ digits + optional .BK).
      3. Return the original symbol unchanged.

    Handles both DB-stored form (NVDA01 without .BK) and .BK-suffixed form
    (NVDA01.BK) transparently.
    """
    if not symbol:
        return symbol

    norm = symbol.strip().upper()

    # Derive the base key used for map lookup (drop .BK if present).
    base = norm[:-3] if norm.endswith(".BK") else norm

    # Step 1 — explicit map.
    if base in YFINANCE_SYMBOL_MAP:
        return YFINANCE_SYMBOL_MAP[base]

    # Step 2 — generic DR suffix stripping.
    m = _DR_RE.match(norm)
    if m:
        return m.group(1)   # letters-only prefix, e.g. "NVDA"

    # Step 3 — return original (Thai .BK stocks, US tickers, other exchanges).
    return norm


def resolve_display_symbol(symbol: str) -> str:
    """Return a human-readable symbol suitable for UI display.

    Strips the .BK exchange suffix from Thai SET symbols; leaves everything
    else unchanged.

    Examples:
        PTT.BK   → PTT
        NVDA01   → NVDA01
        AAPL     → AAPL
        0981.HK  → 0981.HK
    """
    norm = (symbol or "").strip().upper()
    if norm.endswith(".BK"):
        return norm[:-3]
    return norm


def is_dr(symbol: str) -> bool:
    """Return True if *symbol* is a SET DR certificate.

    Accepts symbols with or without the .BK suffix.  Requires at least 2
    trailing digits so Thai tickers that end in a single digit (COM7.BK,
    PR9.BK) are never misidentified.

    Examples:
        is_dr("NVDA01")     → True
        is_dr("NVDA01.BK")  → True
        is_dr("CATL01")     → True
        is_dr("COM7.BK")    → False   (only 1 trailing digit)
        is_dr("PTT.BK")     → False
        is_dr("AAPL")       → False
    """
    return bool(_DR_RE.match((symbol or "").strip().upper()))
