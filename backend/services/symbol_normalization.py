"""Shared symbol normalization — one place for all yfinance ticker resolution.

Platform conventions (invariants):
  DR stocks       stored without .BK  (NVDA01, MICRON01, CATL01)
  Thai SET stocks stored with .BK     (GLIF.BK, BH.BK, AOT.BK)
  US tickers      as-is               (AAPL, SPY)

User-entered symbols (Decision Workspace textarea) follow the same
convention but may omit .BK for Thai stocks or still have .BK.

get_yfinance_symbol() resolves all platform forms to the ticker that
yfinance's get_history / get_fundamentals accepts without error.

DR resolution (explicit mapping + suffix stripping) is handled by
services.symbol_resolver — this module adds the Thai .BK inference rule
for pure-alpha symbols entered without a suffix.
"""
from __future__ import annotations

import re

from services.symbol_resolver import resolve_yfinance_symbol, is_dr

# Matches DR certificates: one or more uppercase letters followed by one or
# more digits, no suffix.  E.g. NVDA01, MICRON01, GOOGL01, AMD80.
_DR_PATTERN = re.compile(r"^[A-Z]+\d+$")


def get_yfinance_symbol(symbol: str) -> str:
    """Resolve any platform symbol to a yfinance-compatible ticker.

    Resolution rules (in order):
      1. Ends with .BK and base is a DR  → resolve via symbol_resolver
         NVDA01.BK  → NVDA,  CATL01.BK → 300750.SZ,  MICRON01.BK → MU
      2. Ends with .BK and base is not DR → return unchanged
         BH.BK → BH.BK,  AOT.BK → AOT.BK
      3. Other exchange suffix present    → return unchanged
         RELIANCE.NS → RELIANCE.NS
      4. DR pattern without .BK           → resolve via symbol_resolver
         NVDA01 → NVDA,  CATL01 → 300750.SZ,  MICRON01 → MU
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
            return resolve_yfinance_symbol(symbol)
        return symbol

    if "." in symbol:
        return symbol

    if _DR_PATTERN.match(symbol):
        return resolve_yfinance_symbol(symbol)

    if symbol.isalpha():
        return symbol + ".BK"

    return symbol
