"""Market Intelligence external discovery for Universal Asset Search.

This module owns the deterministic in-process provider inventory, capability
gating, bounded fan-out, provider-observation filtering, and projection to
non-canonical ``DiscoveryCandidate`` values.  It does not resolve identity,
rank candidates, write Registry state, or inspect provider relevance.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import time
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, Mapping, Optional, Sequence, Tuple

from services.asset_domain import IdentifierType
from services.asset_search.cache import SearchCache, search_cache_key
from services.provider_adapter import ProviderAdapter, YahooFinanceAdapter
from services.provider_domain import ProviderObservation

__all__ = [
    "DEFAULT_PROVIDER_TIMEOUT_MS",
    "MAX_CONCURRENT_PROVIDERS",
    "PROVIDER_INVENTORY",
    "DiscoveryCandidate",
    "ProviderFailure",
    "DiscoverySearchResult",
    "discover",
]

log = logging.getLogger(__name__)

DEFAULT_PROVIDER_TIMEOUT_MS = 2000
MAX_CONCURRENT_PROVIDERS = 8
MAX_PROVIDER_RESULTS = 50

# Canonical WP6 inventory: deterministic, in-process, and deliberately not a
# Registry, Router, priority table, health service, or scheduler.
PROVIDER_INVENTORY: Tuple[ProviderAdapter, ...] = (YahooFinanceAdapter(),)
_SEARCH_CACHE = SearchCache()


@dataclass(frozen=True)
class DiscoveryCandidate:
    kind: str = field(default="DISCOVERY", init=False)
    claim_id: str = ""
    provider_name: str = ""
    reported_symbol: Optional[str] = None
    reported_name: Optional[str] = None
    reported_identifiers: Dict[str, str] = field(default_factory=dict)
    market: Optional[str] = None
    currency: Optional[str] = None
    match_field: str = ""


@dataclass(frozen=True)
class ProviderFailure:
    source: str
    reason: str
    message: str


@dataclass(frozen=True)
class DiscoverySearchResult:
    candidates: Tuple[DiscoveryCandidate, ...]
    failures: Tuple[ProviderFailure, ...]
    eligible_provider_count: int
    successful_provider_count: int


def _fold(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold()


def _reported_identifiers(observation: ProviderObservation) -> Dict[str, str]:
    pairs = (
        (IdentifierType.PROVIDER_SYMBOL, observation.provider_symbol),
        (IdentifierType.ISIN, observation.isin),
        (IdentifierType.CUSIP, observation.cusip),
        (IdentifierType.SEDOL, observation.sedol),
        (IdentifierType.FIGI, observation.figi),
    )
    return {identifier_type.value: value for identifier_type, value in pairs if value}


def _matches_filters(observation: ProviderObservation, filters: Mapping[str, str]) -> bool:
    """Filter only against facts the provider observation actually carries.

    Registry-only classifications such as ``asset_class`` and ``region`` are
    deliberately ignored here. They may constrain registered candidates, but
    cannot exclude an unresolved discovery observation.
    """
    observed = {
        "market": observation.market,
        "exchange": observation.exchange,
        "currency": observation.currency,
    }
    for key, expected in filters.items():
        if key in observed and (observed[key] is None or observed[key] != expected):
            return False
    return True


def _match_field(observation: ProviderObservation, normalized_query: str) -> Optional[str]:
    query = _fold(normalized_query)
    for identifier_type, value in _reported_identifiers(observation).items():
        if _fold(value) == query:
            return f"identifier:{identifier_type}"

    if observation.name:
        name = _fold(observation.name)
        if name.startswith(query):
            return "name_prefix"
        if query in name:
            return "name_substring"
    return None


def _claim_id(provider_name: str, observation: ProviderObservation) -> str:
    evidence = "\x1f".join(
        value or ""
        for value in (
            provider_name,
            observation.provider_symbol,
            observation.name,
            observation.market,
            observation.exchange,
            observation.currency,
            observation.isin,
            observation.cusip,
            observation.sedol,
            observation.figi,
        )
    )
    digest = hashlib.sha256(evidence.encode("utf-8")).hexdigest()[:24]
    return f"discovery:{provider_name}:{digest}"


def _project(
    provider_name: str,
    observation: ProviderObservation,
    normalized_query: str,
    filters: Mapping[str, str],
) -> Optional[DiscoveryCandidate]:
    if not _matches_filters(observation, filters):
        return None
    match_field = _match_field(observation, normalized_query)
    if match_field is None:
        return None
    return DiscoveryCandidate(
        claim_id=_claim_id(provider_name, observation),
        provider_name=provider_name,
        reported_symbol=observation.provider_symbol,
        reported_name=observation.name,
        reported_identifiers=_reported_identifiers(observation),
        market=observation.market,
        currency=observation.currency,
        match_field=match_field,
    )


async def _query_provider(
    provider: ProviderAdapter,
    *,
    normalized_query: str,
    filters: Mapping[str, str],
    timeout_seconds: float,
    semaphore: asyncio.Semaphore,
    cache: SearchCache,
) -> Tuple[DiscoveryCandidate, ...]:
    started_at = time.monotonic()
    key = search_cache_key(normalized_query, filters, provider.provider_name)
    cached = cache.get(key)
    cache_outcome = "hit" if cached is not None else "miss"
    outcome = "success"
    try:
        if cached is None:
            async with semaphore:
                observations = await asyncio.wait_for(
                    provider.search(normalized_query, limit=MAX_PROVIDER_RESULTS),
                    timeout=timeout_seconds,
                )
            if not isinstance(observations, (list, tuple)):
                raise TypeError("provider search must return a sequence of observations")
            valid_observations = tuple(
                observation
                for observation in observations
                if isinstance(observation, ProviderObservation)
            )
            if len(valid_observations) != len(observations):
                log.warning(
                    "asset_search provider=%s dropped malformed observations",
                    provider.provider_name,
                )
            # Cache only after successful, non-cancelled provider completion.
            cache.put(key, valid_observations)
            cached = valid_observations

        projected = []
        for observation in cached:
            candidate = _project(
                provider.provider_name,
                observation,
                normalized_query,
                filters,
            )
            if candidate is not None:
                projected.append(candidate)
        return tuple(projected)
    except asyncio.CancelledError:
        outcome = "cancelled"
        raise
    except asyncio.TimeoutError:
        outcome = "timeout"
        raise
    except BaseException:
        outcome = "error"
        raise
    finally:
        log.info(
            "asset_search provider=%s outcome=%s cache=%s latency_ms=%d",
            provider.provider_name,
            outcome,
            cache_outcome,
            int((time.monotonic() - started_at) * 1000),
        )


async def discover(
    normalized_query: str,
    *,
    filters: Mapping[str, str],
    timeout_ms: int = DEFAULT_PROVIDER_TIMEOUT_MS,
    providers: Sequence[ProviderAdapter] = PROVIDER_INVENTORY,
    cache: SearchCache = _SEARCH_CACHE,
) -> DiscoverySearchResult:
    """Query every capability-eligible provider with bounded isolation."""
    eligible = tuple(
        provider
        for provider in providers
        if provider.capabilities.supports_search is True
    )
    if not eligible:
        return DiscoverySearchResult((), (), 0, 0)

    semaphore = asyncio.Semaphore(min(len(eligible), MAX_CONCURRENT_PROVIDERS))
    timeout_seconds = timeout_ms / 1000.0
    tasks = [
        asyncio.create_task(
            _query_provider(
                provider,
                normalized_query=normalized_query,
                filters=filters,
                timeout_seconds=timeout_seconds,
                semaphore=semaphore,
                cache=cache,
            )
        )
        for provider in eligible
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    candidates = []
    failures = []
    successful = 0
    for provider, result in zip(eligible, results):
        if isinstance(result, asyncio.CancelledError):
            raise result
        if isinstance(result, asyncio.TimeoutError):
            log.warning("asset_search provider=%s timed out", provider.provider_name)
            failures.append(
                ProviderFailure(
                    source=provider.provider_name,
                    reason="TIMEOUT",
                    message="Discovery provider timed out.",
                )
            )
        elif isinstance(result, BaseException):
            log.warning(
                "asset_search provider=%s failed: %s",
                provider.provider_name,
                result,
                exc_info=(type(result), result, result.__traceback__),
            )
            failures.append(
                ProviderFailure(
                    source=provider.provider_name,
                    reason="ERROR",
                    message="Discovery provider failed.",
                )
            )
        else:
            successful += 1
            candidates.extend(result)

    return DiscoverySearchResult(
        candidates=tuple(candidates),
        failures=tuple(failures),
        eligible_provider_count=len(eligible),
        successful_provider_count=successful,
    )
