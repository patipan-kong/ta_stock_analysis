"""Asset Registry — Listing Equivalence Rule (Milestone M5.0).

The one, shared, independently-tested answer to a single question: "may
these two symbol spellings be bundled as evidence for the same asset
inside one ResolutionClaim?" Every Evidence Builder (services/
ledger_evidence_builder.py today; any future broker-import or
manual-entry builder) must call this module rather than deriving its own
alias heuristic. M0_CURRENT_STATE_ANALYSIS.md already found three
independently-maintained DR-detection regexes drifting apart
(symbol_resolver.py, symbol_normalization.py, broker_fees.py) — a
fourth, reinvented inside an Evidence Builder, would be the same mistake
one layer up.

The rule (ASSET_REGISTRY.md Section 5, restated as a bundling test):

    Two identifiers may share one ResolutionClaim only when every
    accounting fact the Portfolio/Replay Engine computes with —
    currency, exchange, settlement cycle, corporate-action timing — is
    identical between them. If any of those facts could plausibly
    differ, the identifiers describe a relationship between two
    listings, not two spellings of one listing, and must never share a
    claim; the Registry expresses the connection through its
    relationship graph instead (RelationshipType.DEPOSITARY_RECEIPT_OF,
    DUAL_LISTED, CROSS_LISTED — services/asset_domain.py, M1).

Concretely, for the platform's own historical symbol pair
(services/transaction_canonicalizer.py's CanonicalTransaction.raw_symbol,
.canonical_symbol, itself produced by services/symbol_normalization.py's
get_yfinance_symbol()):

  - Identical strings -> nothing to decide; one identifier, no bundling
    question.
  - canonical_symbol == raw_symbol + ".BK", and neither symbol is a DR
    certificate -> a venue-suffix convention only (the KBANK / KBANK.BK
    case ADR-005 named as a hard prerequisite for M5). Same listing,
    same currency, same settlement. SAFE to bundle.
  - Either symbol is a DR certificate (services.symbol_resolver.is_dr)
    -> canonical_symbol was produced by DR-to-underlying mapping
    (YFINANCE_SYMBOL_MAP / the DR-suffix regex), not suffix
    normalization. A DR is a distinct instrument that wraps another
    (ASSET_REGISTRY.md Section 5) — never a representation difference.
    is_dr() is reused here only as an exclusion check (a veto): this
    module never consults YFINANCE_SYMBOL_MAP and never treats a DR
    mapping's *output* as bundling evidence.
  - Anything else -> unclassified divergence. Defaults to NOT bundling
    (ASSET_REGISTRY.md Section 4: "never a silent guess") — the caller
    is expected to build identity evidence from raw_symbol alone and
    leave canonical_symbol out of the claim entirely.
"""
from __future__ import annotations

from services.symbol_resolver import is_dr

__all__ = ["same_listing"]


def same_listing(raw_symbol: str | None, canonical_symbol: str | None) -> bool:
    """True only when raw_symbol and canonical_symbol are safe to bundle
    as evidence for one asset inside a single ResolutionClaim.

    Pure function: no I/O, no database, no provider calls, no dependence
    on YFINANCE_SYMBOL_MAP's mapped values. See module docstring for the
    rule and its rationale.
    """
    if not raw_symbol or not canonical_symbol:
        return False
    if raw_symbol == canonical_symbol:
        return False
    if is_dr(raw_symbol) or is_dr(canonical_symbol):
        return False
    return canonical_symbol == f"{raw_symbol}.BK"
