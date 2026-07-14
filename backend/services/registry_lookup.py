"""Asset Registry — Read-Time Compatibility Layer (M6 Compatibility-Layer
Integration, Phase 1: Registry Lookup Foundation).

The one public entry point for runtime Registry lookups, per
docs/implementation/M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md Section 4.
Every non-ledger read path that today re-derives identity from a raw symbol
string (optimizer internals, execution sizing, analytics, evaluation,
watchlist, idea intake) is meant to eventually call through here instead —
but this milestone only builds the module itself. No existing call site is
touched (see the read-path plan's Section 5, Phase 1, item 2: wiring into a
real consumer is a later phase).

Reuses, never reimplements (ADR-004 — one implementation per rule):
  - services.identity_resolver.resolve() for symbol -> Asset resolution.
    In particular, this module does NOT reimplement identity_resolver's
    "a current identifier mapping preempts stale historical ones" rule
    (services/identity_resolver.py _match_candidates) — every symbol
    lookup here goes through the same scoring/precedence engine every
    other Registry caller uses.
  - services.registry_service.get_asset() / get_classifications() for the
    asset_id -> AssetView projection.
  - services.asset_domain for the AssetId/AssetType/AssetStatus/
    IdentifierType vocabulary.

Nothing here is a new identity rule. This module's only original
contribution is (a) the read-only AssetView projection, (b) the Unresolved
first-class value, and (c) the in-process TTL cache in front of both.

API shape — one deviation from the suggested two-signature sketch
--------------------------------------------------------------------
The requesting brief sketched two overloaded signatures,
`resolve_asset(symbol: str)` and `resolve_asset(asset_id: AssetId)`, with
no `db` parameter. Every existing Registry-facing function in this
codebase — registry_service, identity_resolver, registry_query — takes
`db: Session` as its explicit first parameter; there is no ambient
session anywhere in this platform (see e.g. registry_service.get_asset,
identity_resolver.resolve). Introducing a db-less entry point here would
make this the one inconsistent function in the whole Registry surface, and
would also make the TTL cache silently span whatever session happens to be
active when a key is first populated — a correctness hazard, not just a
style one. So `db` is kept as an explicit first parameter, matching every
other module in this layer, and the two suggested signatures are collapsed
into one function that dispatches on the type of `query` (`str` vs
`AssetId`/`int`) rather than on argument position — Python has no
positional-only overloading, and a dispatch-by-type single function is the
smaller surface for callers to learn.

Where NOT to call this from
------------------------------
Per the read-path plan Section 4.3: never from
services/portfolio_rebuilder.py's replay loop or services/ledger_validator.py's
CHECK functions. Those are the accounting-critical, deterministic-replay
paths M5 owns; this module is for analytics, optimizer internals,
evaluation, and CRUD/display paths only.
"""
from __future__ import annotations

import logging
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Dict, Hashable, Mapping, Optional, Sequence, Tuple, Union

from sqlalchemy.orm import Session

from services import identity_resolver
from services import registry_service
from services.asset_domain import AssetId, AssetType, IdentifierRecord, IdentifierType
from services.resolver_domain import ResolutionClaim, ResolutionVerdict

__all__ = [
    "AssetView",
    "Unresolved",
    "resolve_asset",
    "resolve_many",
    "configure_cache",
    "invalidate_cache",
]

_log = logging.getLogger(__name__)

_LOOKUP_SOURCE = "registry_lookup"


# ── Read model ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class AssetView:
    """Immutable, read-only projection of a Registry Asset. Never the ORM
    model itself (models.asset.Asset) — every field below is a plain
    value copied out at resolution time, so holding an AssetView carries
    no session/identity-map lifetime coupling and cannot be used to mutate
    the underlying row."""

    asset_id: AssetId
    canonical_symbol: str
    display_symbol: str
    market: str
    exchange: str
    currency: str
    asset_type: AssetType
    classification: Mapping[str, str] = field(default_factory=dict)
    classification_provenance: Mapping[str, str] = field(default_factory=dict)
    tradable: bool = True
    fractional_support: bool = False
    lot_size: Optional[int] = None
    settlement_cycle: Optional[str] = None


@dataclass(frozen=True)
class Unresolved:
    """The decisive, non-exceptional answer to "no asset for this query
    (yet)". Per ASSET_REGISTRY.md Section 4 ("resolve decisively or ask —
    never guess") and the read-path plan Section 4.1, this is a first-class
    return value: callers distinguish AssetView vs Unresolved with a type
    check, never a try/except."""

    query: str
    reason: str
    verdict: ResolutionVerdict = ResolutionVerdict.UNKNOWN


_REASON_NOT_FOUND = "no matching asset"
_REASON_AMBIGUOUS = "ambiguous — multiple candidate assets, see RegistryFinding"
_REASON_CONFLICT = "conflicting evidence — see RegistryFinding"
_REASON_NO_ASSET_ID = "no asset with this asset_id"

_VERDICT_REASON = {
    ResolutionVerdict.AMBIGUOUS: _REASON_AMBIGUOUS,
    ResolutionVerdict.CONFLICT: _REASON_CONFLICT,
    ResolutionVerdict.UNKNOWN: _REASON_NOT_FOUND,
    ResolutionVerdict.CANDIDATE: _REASON_NOT_FOUND,
}


def _to_asset_view(asset, db: Session) -> AssetView:
    classifications = registry_service.get_classifications(
        db, AssetId(asset.id), current_only=True,
    )
    return AssetView(
        asset_id=AssetId(asset.id),
        canonical_symbol=asset.canonical_symbol,
        display_symbol=asset.display_symbol or asset.canonical_symbol,
        market=asset.market,
        exchange=asset.exchange,
        currency=asset.currency,
        asset_type=AssetType(asset.asset_type),
        classification={c.dimension: c.value for c in classifications},
        classification_provenance={c.dimension: c.source for c in classifications},
        tradable=asset.tradable,
        fractional_support=asset.fractional_support,
        lot_size=asset.lot_size,
        settlement_cycle=asset.settlement_cycle,
    )


# ── TTL cache ────────────────────────────────────────────────────────────

_DEFAULT_TTL_SECONDS = 300.0
_DEFAULT_MAX_SIZE = 2048

_MISS = object()


class _TTLCache:
    """Thread-safe, in-process LRU+TTL cache. Caches both positive
    (AssetView) and negative (Unresolved) results — a symbol that
    consistently fails to resolve is exactly as expensive to keep
    re-resolving as one that succeeds, and the read-path plan's whole
    premise (§4.1) is that hot read paths must not re-run adjudication on
    every request regardless of outcome."""

    def __init__(self, ttl_seconds: float, max_size: int) -> None:
        self._ttl_seconds = ttl_seconds
        self._max_size = max_size
        self._lock = threading.Lock()
        self._store: "OrderedDict[Hashable, Tuple[float, object]]" = OrderedDict()

    def get(self, key: Hashable):
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return _MISS
            expires_at, value = entry
            if expires_at <= time.monotonic():
                del self._store[key]
                return _MISS
            self._store.move_to_end(key)
            return value

    def set(self, key: Hashable, value: object) -> None:
        with self._lock:
            self._store[key] = (time.monotonic() + self._ttl_seconds, value)
            self._store.move_to_end(key)
            while len(self._store) > self._max_size:
                self._store.popitem(last=False)

    def invalidate(self, key: Optional[Hashable]) -> None:
        with self._lock:
            if key is None:
                self._store.clear()
            else:
                self._store.pop(key, None)

    def reconfigure(self, *, ttl_seconds: Optional[float], max_size: Optional[int]) -> None:
        with self._lock:
            if ttl_seconds is not None:
                self._ttl_seconds = ttl_seconds
            if max_size is not None:
                self._max_size = max_size
                while len(self._store) > self._max_size:
                    self._store.popitem(last=False)


_cache = _TTLCache(_DEFAULT_TTL_SECONDS, _DEFAULT_MAX_SIZE)


def configure_cache(*, ttl_seconds: Optional[float] = None, max_size: Optional[int] = None) -> None:
    """Adjusts the shared cache's TTL and/or max size at runtime. Omitted
    arguments leave that setting unchanged. Does not itself clear existing
    entries (a shrunk max_size evicts the oldest as needed; a changed TTL
    only takes effect for entries written after the call)."""
    _cache.reconfigure(ttl_seconds=ttl_seconds, max_size=max_size)


def invalidate_cache(query: Optional[Union[str, AssetId, int]] = None) -> None:
    """Clears one cached entry, or the whole cache when `query` is omitted.
    Mirrors services.analytics.regime_detector.invalidate_cache()'s
    existing convention in this codebase."""
    if query is None:
        _cache.invalidate(None)
        return
    _cache.invalidate(_cache_key(query))


def _normalize_symbol(symbol: str) -> str:
    return (symbol or "").strip().upper()


def _cache_key(query: Union[str, AssetId, int]) -> Tuple[str, Union[str, int]]:
    if isinstance(query, str):
        return ("symbol", _normalize_symbol(query))
    return ("asset_id", int(query))


# ── Resolution ───────────────────────────────────────────────────────────

def resolve_asset(db: Session, query: Union[str, AssetId, int]) -> Union[AssetView, Unresolved]:
    """Resolves `query` — a platform symbol string, or an AssetId/int
    asset_id — to an AssetView, or Unresolved if the Registry has no
    decisive answer. Never raises for an ordinary not-found/ambiguous
    result (ASSET_REGISTRY.md Section 4); a TypeError is raised only if
    `query` is neither a str nor an int, which is a caller programming
    error, not a lookup outcome.

    Results are cached (positive and negative) for a configurable TTL —
    see configure_cache(). A cache hit performs no database work and does
    not re-invoke identity_resolver.resolve().
    """
    if isinstance(query, str):
        return _resolve_symbol(db, query)
    if isinstance(query, int):
        return _resolve_asset_id(db, AssetId(query))
    raise TypeError(f"resolve_asset() query must be str or int/AssetId, got {type(query)!r}")


def _resolve_symbol(db: Session, symbol: str) -> Union[AssetView, Unresolved]:
    normalized = _normalize_symbol(symbol)
    key = ("symbol", normalized)

    cached = _cache.get(key)
    if cached is not _MISS:
        _log.debug("registry_lookup: cache hit symbol=%r", normalized)
        return cached  # type: ignore[return-value]

    _log.debug("registry_lookup: cache miss symbol=%r — calling identity_resolver.resolve", normalized)

    if not normalized:
        result: Union[AssetView, Unresolved] = Unresolved(
            query=normalized,
            reason=_REASON_NOT_FOUND,
            verdict=ResolutionVerdict.UNKNOWN,
        )
        _cache.set(key, result)
        return result

    claim = ResolutionClaim(
        identifiers=(
            IdentifierRecord(
                identifier_type=IdentifierType.PROVIDER_SYMBOL,
                value=normalized,
                source=_LOOKUP_SOURCE,
            ),
        ),
    )
    resolution = identity_resolver.resolve(db, claim)

    if resolution.verdict == ResolutionVerdict.RESOLVED and resolution.resolved_asset_id is not None:
        asset = registry_service.get_asset(db, resolution.resolved_asset_id)
        if asset is None:
            # Should not happen (RESOLVED implies the asset exists), but
            # honesty over a stale cache entry if it ever does.
            result = Unresolved(
                query=normalized,
                reason=_REASON_NOT_FOUND,
                verdict=ResolutionVerdict.UNKNOWN,
            )
        else:
            result = _to_asset_view(asset, db)
    else:
        reason = _VERDICT_REASON.get(resolution.verdict, _REASON_NOT_FOUND)
        _log.debug("registry_lookup: unresolved symbol=%r verdict=%s", normalized, resolution.verdict.value)
        result = Unresolved(query=normalized, reason=reason, verdict=resolution.verdict)

    _cache.set(key, result)
    return result


def _resolve_asset_id(db: Session, asset_id: AssetId) -> Union[AssetView, Unresolved]:
    key = ("asset_id", int(asset_id))

    cached = _cache.get(key)
    if cached is not _MISS:
        _log.debug("registry_lookup: cache hit asset_id=%r", int(asset_id))
        return cached  # type: ignore[return-value]

    _log.debug("registry_lookup: cache miss asset_id=%r — calling registry_service.get_asset", int(asset_id))

    asset = registry_service.get_asset(db, asset_id)
    if asset is None:
        _log.debug("registry_lookup: unresolved asset_id=%r", int(asset_id))
        result: Union[AssetView, Unresolved] = Unresolved(
            query=str(int(asset_id)),
            reason=_REASON_NO_ASSET_ID,
            verdict=ResolutionVerdict.UNKNOWN,
        )
    else:
        result = _to_asset_view(asset, db)

    _cache.set(key, result)
    return result


def resolve_many(
    db: Session, queries: Sequence[Union[str, AssetId, int]],
) -> Dict[Union[str, int], Union[AssetView, Unresolved]]:
    """Resolves several queries in one call, reusing the shared cache so a
    symbol repeated within (or across) calls is never re-resolved. Returns
    a dict keyed by the original query values, in input order (Python
    dicts preserve insertion order) — duplicate queries collapse to a
    single key, exactly as a normal dict would."""
    return {query: resolve_asset(db, query) for query in queries}
