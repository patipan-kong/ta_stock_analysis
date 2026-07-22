"""Asset Registry — Provider Adapter Layer (Milestone M4).

Connects external market-data providers to the Identity Resolution Engine
(M3) without the Registry ever learning a provider exists
(PROVIDER_INTERFACE.md Section 1: "the interface is the waterline;
provider knowledge exists only above it, and it must never rise").

An adapter's entire job is provider transport and translation, never judgment:

  - It converts a vendor-shaped payload into ProviderObservation
    (provider_domain.py) — one canonical shape per observation kind,
    exactly as PROVIDER_INTERFACE.md Section 4 requires.
  - It converts that observation into a ResolutionClaim
    (services/resolver_domain.py, M3, unmodified) — the same shape
    identity_resolver.resolve() already consumes from any other caller.

What an adapter must never do (PROVIDER_INTERFACE.md Section 2):
  - Never assert identity. An adapter produces a claim; only
    identity_resolver.resolve() and a human adjudicator (via
    identity_resolver.adjudicate()) ever produce a verdict.
  - Never infer, repair, or reinterpret. A missing field stays missing
    (None) in ProviderObservation and is simply absent from the resulting
    ResolutionClaim's identifiers — it is never guessed, defaulted, or
    filled from another field. This module contains no symbol-cleanup,
    no regex normalization, no DR-suffix handling — that is
    services/symbol_resolver.py's job, and this module does not call it
    (M0/M3 already flagged that module as a separate, untouched concern).
  - Never touch the database or the Registry directly. Translation methods
    are pure; search performs provider I/O only. Nothing in this module
    imports registry_service, identity_resolver, or a Session.

build_claim() is the one shared, non-overridable implementation of
"ProviderObservation -> ResolutionClaim" (ADR-004 — one implementation per
rule): every adapter subclass supplies provider-specific normalize() and
search() methods; adding one never changes shared claim-construction logic.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, ClassVar, List, Mapping, Optional, Sequence, Tuple, final

import httpx

from services.asset_domain import IdentifierRecord, IdentifierType
from services.provider_domain import ProviderCapabilities, ProviderObservation
from services.resolver_domain import ResolutionClaim

__all__ = ["ProviderAdapter", "YahooFinanceAdapter"]

log = logging.getLogger(__name__)

_YAHOO_SEARCH_URL = "https://query1.finance.yahoo.com/v1/finance/search"
_YAHOO_SEARCH_TIMEOUT_SECONDS = 5
_YAHOO_SEARCH_HEADERS = {
    "User-Agent": "stock-analysis/asset-search",
    "Accept": "application/json",
}


async def _fetch_yahoo_search_payload(query: str, limit: int) -> Mapping[str, Any]:
    # The repository already depends on httpx. Keeping the transport async
    # allows cancellation from discovery_search's existing wait_for boundary
    # to reach the in-flight request instead of abandoning a worker thread.
    async with httpx.AsyncClient(
        headers=_YAHOO_SEARCH_HEADERS,
        timeout=_YAHOO_SEARCH_TIMEOUT_SECONDS,
    ) as client:
        response = await client.get(
            _YAHOO_SEARCH_URL,
            params={
                "q": query,
                "quotesCount": limit,
                "newsCount": 0,
                "listsCount": 0,
                "enableFuzzyQuery": "false",
            },
        )
        response.raise_for_status()
        payload = response.json()
    if not isinstance(payload, Mapping):
        raise ValueError("Yahoo Finance search returned a malformed payload")
    return payload


def _clean_str(value: Any) -> Optional[str]:
    """Translates a vendor field's presence/absence honestly: strips
    incidental whitespace, treats an empty string as absent. Never changes
    meaning (no case folding, no substring extraction, no synonym
    mapping) — representation only, per PROVIDER_INTERFACE.md Section 4's
    "translation, not interpretation"."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


class ProviderAdapter(ABC):
    """One stateless, DB-free adapter per provider.

    Adapters perform provider I/O and pure translation only; they hold no
    Registry state and make no identity or ranking judgment.
    """

    provider_name: ClassVar[str]
    capabilities: ClassVar[ProviderCapabilities]

    @abstractmethod
    def normalize(self, raw: Any) -> ProviderObservation:
        """Vendor payload -> ProviderObservation. The only method a new
        adapter must write. Must not guess, default, or repair a missing
        field — leave it None (PROVIDER_INTERFACE.md Section 2: "never
        fill gaps creatively")."""
        raise NotImplementedError

    @abstractmethod
    async def search(self, query: str, *, limit: int) -> Sequence[ProviderObservation]:
        """Search provider instruments and return provider observations.

        This additive I/O boundary returns evidence only.  It must not rank,
        resolve identity, write Registry state, or return provider relevance.
        """
        raise NotImplementedError

    @final
    def build_claim(
        self,
        raw: Any,
        *,
        requested_by: Optional[str] = None,
        note: Optional[str] = None,
    ) -> ResolutionClaim:
        """normalize() then a fixed, shared mapping into ResolutionClaim.
        Final by design (ADR-004): claim construction is one rule with one
        implementation, regardless of how many adapters exist."""
        observation = self.normalize(raw)
        return ResolutionClaim(
            identifiers=tuple(self._build_identifiers(observation)),
            market=observation.market,
            exchange=observation.exchange,
            currency=observation.currency,
            requested_by=requested_by,
            note=note,
        )

    def _build_identifiers(self, observation: ProviderObservation) -> List[IdentifierRecord]:
        source = f"provider:{self.provider_name}"
        candidates: Tuple[Tuple[IdentifierType, Optional[str]], ...] = (
            (IdentifierType.PROVIDER_SYMBOL, observation.provider_symbol),
            (IdentifierType.ISIN, observation.isin),
            (IdentifierType.CUSIP, observation.cusip),
            (IdentifierType.SEDOL, observation.sedol),
            (IdentifierType.FIGI, observation.figi),
        )
        return [
            IdentifierRecord(
                identifier_type=identifier_type,
                value=value,
                source=source,
                as_of=observation.observed_at,
            )
            for identifier_type, value in candidates
            if value is not None
        ]

    def _now(self) -> datetime:
        """Translation-time provenance: when *this adapter* processed the
        payload. Not a vendor-reported value, so it is generated here
        rather than left for normalize() implementations to duplicate."""
        return datetime.now(timezone.utc)


class YahooFinanceAdapter(ProviderAdapter):
    """Translates a yfinance-shaped payload (the dict a caller assembles
    from Ticker.info, optionally merged with Ticker.isin under an "isin"
    key) into ProviderObservation. Today's yfinance payload carries no
    CUSIP/SEDOL/FIGI, so those fields are always None here — an honest
    reflection of the current data source, not a limitation of this
    adapter's mapping, which is written generically for when a richer
    source exists."""

    provider_name = "yahoo_finance"
    capabilities = ProviderCapabilities(
        identifier_types=frozenset({IdentifierType.PROVIDER_SYMBOL, IdentifierType.ISIN}),
        supports_search=True,
    )

    def normalize(self, raw: Mapping[str, Any]) -> ProviderObservation:
        return ProviderObservation(
            provider_symbol=_clean_str(raw.get("symbol")),
            name=_clean_str(
                raw.get("longName")
                or raw.get("longname")
                or raw.get("shortName")
                or raw.get("shortname")
            ),
            market=_clean_str(raw.get("market")),
            exchange=_clean_str(raw.get("exchange")),
            currency=_clean_str(raw.get("currency")),
            isin=_clean_str(raw.get("isin")),
            cusip=None,
            sedol=None,
            figi=None,
            observed_at=self._now(),
        )

    async def search(self, query: str, *, limit: int) -> Sequence[ProviderObservation]:
        bounded_limit = max(1, min(limit, 50))
        payload = await _fetch_yahoo_search_payload(query, bounded_limit)
        quotes = payload.get("quotes", ())
        if not isinstance(quotes, (list, tuple)):
            raise ValueError("Yahoo Finance search quotes were malformed")
        observations = tuple(
            self.normalize(raw) for raw in quotes if isinstance(raw, Mapping)
        )
        if len(observations) != len(quotes):
            log.warning("Yahoo Finance search dropped malformed quote entries")
        return observations
