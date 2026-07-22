"""Executable evidence for WP6's disposable external Search Cache."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.asset_search.cache import SearchCache, search_cache_key
from services.provider_domain import ProviderObservation


def test_cache_hit_and_ttl_expiry():
    now = [100.0]
    cache = SearchCache(ttl_seconds=60, clock=lambda: now[0])
    key = search_cache_key("AAPL", {"market": "US"}, "provider-a")
    observations = (ProviderObservation(provider_symbol="AAPL"),)

    cache.put(key, observations)
    assert cache.get(key) == observations

    now[0] += 60
    assert cache.get(key) is None


def test_cache_key_is_provider_and_filter_scoped_and_hides_raw_query():
    first = search_cache_key("sensitive query", {"market": "US"}, "provider-a")
    other_provider = search_cache_key("sensitive query", {"market": "US"}, "provider-b")
    other_filter = search_cache_key("sensitive query", {"market": "TH"}, "provider-a")

    assert first != other_provider
    assert first != other_filter
    assert "sensitive query" not in first


def test_clear_is_disposable_and_complete():
    cache = SearchCache()
    key = search_cache_key("AAPL", {}, "provider-a")
    cache.put(key, (ProviderObservation(provider_symbol="AAPL"),))

    cache.clear()

    assert cache.get(key) is None
