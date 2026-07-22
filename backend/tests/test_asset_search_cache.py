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


def test_capacity_evicts_oldest_last_write_deterministically():
    cache = SearchCache(max_entries=2)
    first = search_cache_key("A", {}, "provider-a")
    second = search_cache_key("B", {}, "provider-a")
    third = search_cache_key("C", {}, "provider-a")

    cache.put(first, (ProviderObservation(provider_symbol="A"),))
    cache.put(second, (ProviderObservation(provider_symbol="B"),))
    cache.put(third, (ProviderObservation(provider_symbol="C"),))

    assert cache.get(first) is None
    assert cache.get(second)[0].provider_symbol == "B"
    assert cache.get(third)[0].provider_symbol == "C"


def test_put_removes_all_expired_entries_before_capacity_eviction():
    now = [0.0]
    cache = SearchCache(ttl_seconds=60, max_entries=3, clock=lambda: now[0])
    first = search_cache_key("A", {}, "provider-a")
    second = search_cache_key("B", {}, "provider-a")
    third = search_cache_key("C", {}, "provider-a")

    cache.put(first, (ProviderObservation(provider_symbol="A"),))
    cache.put(second, (ProviderObservation(provider_symbol="B"),))
    now[0] = 60.0
    cache.put(third, (ProviderObservation(provider_symbol="C"),))

    assert list(cache._entries) == [third]


def test_capacity_must_be_positive():
    try:
        SearchCache(max_entries=0)
    except ValueError as exc:
        assert str(exc) == "max_entries must be positive"
    else:
        raise AssertionError("zero cache capacity must be rejected")
