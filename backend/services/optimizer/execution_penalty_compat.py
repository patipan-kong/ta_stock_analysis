"""Deletable M31.2 compatibility classifier for execution-risk scoring.

This module preserves the observable Phase 3B.10 behavior only when the
Asset Registry cannot supply decisive ExecutionInstrumentFacts.  Its result
is never authoritative and must always be surfaced with
``LEGACY_COMPATIBILITY_FALLBACK`` provenance by the caller.

Do not use this module to mint, enrich, or backfill Registry facts.  The
symbol rules below intentionally remain isolated here so M31.3 can remove
the whole compatibility path without touching the execution judgment layer.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


LEGACY_COMPATIBILITY_FALLBACK = "LEGACY_COMPATIBILITY_FALLBACK"

_LEGACY_DR_RE = re.compile(r"^([A-Z]+)\d{2}\.BK$")
_LEGACY_ETF_TICKERS = frozenset(
    ["QQQ", "SPY", "VTI", "IVV", "EEM", "GLD", "TLT", "ARKK", "XLF", "XLK"]
)


def legacy_etf_review_symbols() -> tuple[str, ...]:
    """Expose the legacy list to audit tooling as non-authoritative evidence."""

    return tuple(sorted(_LEGACY_ETF_TICKERS))


@dataclass(frozen=True)
class LegacyCompatibilityClassification:
    asset_type: str
    provenance: str = LEGACY_COMPATIBILITY_FALLBACK


def classify_legacy_compatibility(symbol: str, is_dr: bool) -> LegacyCompatibilityClassification:
    """Reproduce the pre-M31.2 taxonomy solely for temporary compatibility."""

    if is_dr or bool(_LEGACY_DR_RE.match(symbol)):
        asset_type = "DR"
    elif symbol.upper() in _LEGACY_ETF_TICKERS:
        asset_type = "ETF"
    elif symbol.startswith("^"):
        asset_type = "INDEX"
    else:
        asset_type = "EQUITY"
    return LegacyCompatibilityClassification(asset_type=asset_type)
