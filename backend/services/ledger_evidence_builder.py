"""Asset Registry — Ledger Replay Evidence Builder (Milestone M5.0).

Translates one historical ledger symbol pair
(services/transaction_canonicalizer.py's CanonicalTransaction.raw_symbol,
.canonical_symbol) into a ResolutionClaim — the M5 backfill's answer to
the one source ADR-005 named as a hard prerequisite: the platform's own
historical raw_symbol/canonical_symbol alias-splitting (KBANK vs
KBANK.BK).

Like services/provider_adapter.py (M4), this module's entire job is
translation, never judgment:

  - It never asserts identity. It produces a claim; only
    identity_resolver.resolve() (M3, unmodified) ever produces a
    verdict.
  - It never touches the database or the Registry. Every function here
    is a pure transformation of its input strings.
  - It bundles raw_symbol and canonical_symbol into one claim's
    identifiers only when services/listing_equivalence.py's
    same_listing() confirms they are a representation difference, not
    an economic relationship (DR/underlying, dual listing, etc. —
    ASSET_REGISTRY.md Section 5). When same_listing() cannot confirm
    equivalence, canonical_symbol is left out of the claim entirely —
    the ledger recorded a transaction in raw_symbol, never in whatever
    canonical_symbol's market-data routing happens to point at, so
    treating canonical_symbol as a second, independent piece of
    identity evidence would misrepresent what actually happened.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from services.asset_domain import IdentifierRecord, IdentifierType
from services.listing_equivalence import same_listing
from services.resolver_domain import ResolutionClaim

if TYPE_CHECKING:
    from services.transaction_canonicalizer import CanonicalTransaction

__all__ = ["build_claim", "build_claim_from_transaction"]

_SOURCE = "ledger:historical"


def _identifier(value: str, as_of: Optional[datetime]) -> IdentifierRecord:
    return IdentifierRecord(
        identifier_type=IdentifierType.PROVIDER_SYMBOL,
        value=value,
        source=_SOURCE,
        as_of=as_of,
    )


def build_claim(
    raw_symbol: Optional[str],
    canonical_symbol: Optional[str],
    *,
    market: Optional[str] = None,
    exchange: Optional[str] = None,
    currency: Optional[str] = None,
    as_of: Optional[datetime] = None,
    requested_by: Optional[str] = None,
    note: Optional[str] = None,
) -> ResolutionClaim:
    """One historical symbol pair -> one ResolutionClaim.

    Always returns a claim (never None), mirroring
    provider_adapter.build_claim()'s contract — a transaction with no
    symbol (a cash-only row: DEPOSIT/WITHDRAW/INITIAL_CASH/DIVIDEND)
    simply produces a claim with zero identifiers.

    canonical_symbol is bundled in as a second PROVIDER_SYMBOL
    identifier only when listing_equivalence.same_listing() confirms
    the pair denotes the same listing (e.g. KBANK / KBANK.BK).
    Otherwise the claim carries raw_symbol alone.
    """
    observed_at = as_of or datetime.now(timezone.utc)
    identifiers: List[IdentifierRecord] = []

    if raw_symbol:
        identifiers.append(_identifier(raw_symbol, observed_at))
        if (
            canonical_symbol
            and canonical_symbol != raw_symbol
            and same_listing(raw_symbol, canonical_symbol)
        ):
            identifiers.append(_identifier(canonical_symbol, observed_at))

    return ResolutionClaim(
        identifiers=tuple(identifiers),
        market=market,
        exchange=exchange,
        currency=currency,
        requested_by=requested_by,
        note=note,
    )


def build_claim_from_transaction(
    transaction: "CanonicalTransaction",
    *,
    market: Optional[str] = None,
    exchange: Optional[str] = None,
    currency: Optional[str] = None,
    requested_by: Optional[str] = None,
    note: Optional[str] = None,
) -> ResolutionClaim:
    """Convenience wrapper over build_claim() for the shape M5's backfill
    actually holds: a CanonicalTransaction. market/exchange/currency are
    not fields of CanonicalTransaction (they belong to the portfolio,
    not the transaction) and must still be supplied by the caller as
    corroboration hints, exactly as provider_adapter callers do.

    as_of is taken from the transaction's own created_at — when the
    platform recorded this evidence, not when the trade economically
    occurred (ADR-003's two-timeline rule applied to evidence
    provenance rather than ledger events).
    """
    return build_claim(
        transaction.raw_symbol,
        transaction.canonical_symbol,
        market=market,
        exchange=exchange,
        currency=currency,
        as_of=transaction.created_at,
        requested_by=requested_by,
        note=note,
    )
