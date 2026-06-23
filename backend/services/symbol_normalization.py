"""Shared symbol normalization — one place for all yfinance ticker resolution.

Platform conventions (invariants):
  DR stocks       stored without .BK  (NVDA01, MICRON01)
  Thai SET stocks stored with .BK     (GLIF.BK, BH.BK, AOT.BK)
  US tickers      as-is               (AAPL, SPY)

User-entered symbols (Decision Workspace textarea) follow the same
convention but may omit .BK for Thai stocks or still have .BK.

get_yfinance_symbol() resolves all platform forms to the ticker that
yfinance's get_history / get_fundamentals accepts without error.
"""
from __future__ import annotations

import re

from services.data_fetcher import normalize_dr_symbol

# Matches DR certificates: one or more uppercase letters followed by one or
# more digits, no suffix.  E.g. NVDA01, MICRON01, GOOGL01, AMD80.
_DR_PATTERN = re.compile(r"^[A-Z]+\d+$")


def get_yfinance_symbol(symbol: str) -> str:
    """Resolve any platform symbol to a yfinance-compatible ticker.

    Resolution rules (in order):
      1. Ends with .BK and base is a DR  → normalize to underlying US ticker
         NVDA01.BK  → NVDA,  MICRON01.BK → MU
      2. Ends with .BK and base is not DR → return unchanged
         BH.BK → BH.BK,  AOT.BK → AOT.BK
      3. Other exchange suffix present    → return unchanged
         RELIANCE.NS → RELIANCE.NS
      4. DR pattern without .BK           → inject .BK then normalize
         NVDA01 → NVDA,  MICRON01 → MU,  GOOGL01 → GOOGL
      5. Pure alphabetic (no digits)      → Thai SET equity, append .BK
         GLIF → GLIF.BK,  BH → BH.BK,  AOT → AOT.BK
      6. Anything else                    → return unchanged
    """
    symbol = symbol.strip().upper()
    if not symbol:
        return symbol

    if symbol.endswith(".BK"):
        base = symbol[:-3]
        if _DR_PATTERN.match(base):
            return normalize_dr_symbol(symbol)
        return symbol

    if "." in symbol:
        return symbol

    if _DR_PATTERN.match(symbol):
        return normalize_dr_symbol(symbol + ".BK")

    if symbol.isalpha():
        return symbol + ".BK"

    return symbol
