"""Asset Registry — Bootstrap Symbol/Market Convention (Milestone M5.3).

Answers exactly one question, and only when the symbol's own shape is
itself unambiguous evidence of venue: "what market/exchange should a
bootstrap-minted Asset carry?" AssetClaim requires market/exchange/currency
to be non-empty (services/asset_registry.py core.mint()); Transaction and
ClaimShape carry no market/exchange column at all, so something has to
supply this to mint from ledger evidence alone. This module is that
something — deliberately narrow, never a population-level default.

Reuses, never reinvents
------------------------
services.symbol_resolver.is_dr() (unmodified, already decision-logged) is
the one existing, exact-pattern signal this module trusts: a DR-pattern
symbol (NVDA01, NVDA01.BK, CATL01, ...) is SET-listed by construction — the
DR certificate itself trades on SET regardless of where its foreign
underlying trades, and is_dr() already encodes the exact regex the platform
uses everywhere else for this determination (ADR-004 — one implementation
per rule; this module does not carry its own copy of that pattern).

Deliberately narrower than symbol_normalization.get_yfinance_symbol()
------------------------------------------------------------------------
That function's pure-alphabetic-with-no-suffix -> ".BK" rule (rule 5 in its
own docstring) is a *query-convenience default* for routing a symbol to a
market-data provider: worst case it asks yfinance for the wrong ticker
temporarily, which is cheap to notice and cheap to fix, and the function
itself never raises. Minting a canonical Asset is a different risk tier —
a durable identity claim, not a disposable lookup. Reusing that fallback
here would treat "we don't actually know" as if it were positive evidence,
violating ASSET_REGISTRY.md Section 4's "resolve decisively or ask — never
guess" at the exact point guessing would be most expensive. So this module
answers only two shapes, both unambiguous on their own:

  - a DR-pattern symbol (is_dr() true, with or without ".BK")   -> SET
  - a symbol carrying the literal ".BK" suffix, non-DR          -> SET

Everything else — including a pure-alphabetic symbol with no suffix at
all — returns None. That is intentional, not a gap: it is the caller's
(services/bootstrap_planner.py's) job to quarantine that case and report it
for a human to extend this table deliberately (mirroring how DR handling
itself became a logged platform convention rather than an assumption), not
for this module to guess on the caller's behalf.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from services.symbol_resolver import is_dr

__all__ = ["MarketExchangeHint", "infer_market_exchange"]

_BK_SUFFIX = ".BK"
_THAILAND = "Thailand"
_SET = "SET"


@dataclass(frozen=True)
class MarketExchangeHint:
    """A market/exchange pair inferred with certainty from a symbol's own
    shape — never a guess, never a population-level default."""

    market: str
    exchange: str


def infer_market_exchange(raw_symbol: str) -> Optional[MarketExchangeHint]:
    """Returns a MarketExchangeHint only when `raw_symbol`'s own shape
    unambiguously identifies a venue. Returns None otherwise — callers
    must treat None as "quarantine, do not mint," never as "assume
    Thailand/SET," per this module's docstring.
    """
    symbol = (raw_symbol or "").strip().upper()
    if not symbol:
        return None

    if is_dr(symbol):
        return MarketExchangeHint(market=_THAILAND, exchange=_SET)

    if symbol.endswith(_BK_SUFFIX):
        return MarketExchangeHint(market=_THAILAND, exchange=_SET)

    return None
