"""Disposable in-process cache for external asset-search observations.

The cache is Market Intelligence convenience state only.  It stores immutable
``ProviderObservation`` values for a short TTL and is never consulted for
Registry resolution, canonical identity, or ranking.
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Callable, Mapping, Optional, Sequence, Tuple

from services.provider_domain import ProviderObservation

__all__ = [
    "DEFAULT_MAX_ENTRIES",
    "DEFAULT_TTL_SECONDS",
    "SearchCache",
    "search_cache_key",
]

DEFAULT_TTL_SECONDS = 60.0
DEFAULT_MAX_ENTRIES = 256


def search_cache_key(
    normalized_query: str,
    filters: Mapping[str, str],
    provider_name: str,
) -> str:
    """Return a provider-scoped key without retaining raw query text."""
    query_hash = hashlib.sha256(normalized_query.encode("utf-8")).hexdigest()
    filters_payload = json.dumps(
        sorted(filters.items()), ensure_ascii=False, separators=(",", ":")
    )
    filters_hash = hashlib.sha256(filters_payload.encode("utf-8")).hexdigest()
    return f"{provider_name}:{query_hash}:{filters_hash}"


@dataclass(frozen=True)
class _CacheEntry:
    observations: Tuple[ProviderObservation, ...]
    cached_at: float


class SearchCache:
    """Small thread-safe TTL cache; deletion loses no authoritative data."""

    def __init__(
        self,
        *,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
        max_entries: int = DEFAULT_MAX_ENTRIES,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        if max_entries <= 0:
            raise ValueError("max_entries must be positive")
        self._ttl_seconds = ttl_seconds
        self._max_entries = max_entries
        self._clock = clock
        # Insertion order is the eviction order. Replacing a key makes it the
        # newest entry, yielding deterministic FIFO-by-last-write behavior.
        self._entries: OrderedDict[str, _CacheEntry] = OrderedDict()
        self._lock = threading.Lock()

    def _remove_expired(self, now: float) -> None:
        expired = [
            key
            for key, entry in self._entries.items()
            if now - entry.cached_at >= self._ttl_seconds
        ]
        for key in expired:
            self._entries.pop(key, None)

    def get(self, key: str) -> Optional[Tuple[ProviderObservation, ...]]:
        now = self._clock()
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if now - entry.cached_at >= self._ttl_seconds:
                self._entries.pop(key, None)
                return None
            return entry.observations

    def put(self, key: str, observations: Sequence[ProviderObservation]) -> None:
        values = tuple(observations)
        if not all(isinstance(value, ProviderObservation) for value in values):
            raise TypeError("SearchCache stores ProviderObservation values only")
        now = self._clock()
        with self._lock:
            self._remove_expired(now)
            self._entries.pop(key, None)
            while len(self._entries) >= self._max_entries:
                self._entries.popitem(last=False)
            self._entries[key] = _CacheEntry(values, now)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
