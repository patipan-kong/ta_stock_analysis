"""Executable evidence for WP6 provider discovery and projection."""
import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.asset_domain import IdentifierType
from services.asset_search.cache import SearchCache
from services.asset_search.discovery_search import (
    MAX_CONCURRENT_PROVIDERS,
    PROVIDER_INVENTORY,
    discover,
)
from services.provider_adapter import ProviderAdapter, YahooFinanceAdapter
from services.provider_domain import ProviderCapabilities, ProviderObservation


class FakeAdapter(ProviderAdapter):
    def __init__(
        self,
        name,
        observations=(),
        *,
        supports_search=True,
        delay=0.0,
        error=None,
    ):
        self.provider_name = name
        self.capabilities = ProviderCapabilities(
            identifier_types=frozenset({IdentifierType.PROVIDER_SYMBOL}),
            supports_search=supports_search,
        )
        self.observations = tuple(observations)
        self.delay = delay
        self.error = error
        self.calls = 0

    def normalize(self, raw):
        return raw

    async def search(self, query, *, limit):
        self.calls += 1
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.error is not None:
            raise self.error
        return self.observations


def _run(*providers, query="AAPL", filters=None, timeout_ms=2000, cache=None):
    return asyncio.run(
        discover(
            query,
            filters=filters or {},
            timeout_ms=timeout_ms,
            providers=providers,
            cache=cache or SearchCache(),
        )
    )


def test_inventory_is_deterministic_and_contains_the_search_capable_yahoo_adapter():
    assert len(PROVIDER_INVENTORY) == 1
    assert isinstance(PROVIDER_INVENTORY[0], YahooFinanceAdapter)
    assert PROVIDER_INVENTORY[0].capabilities.supports_search is True


def test_capability_gate_excludes_unsupported_provider_before_call():
    provider = FakeAdapter("unsupported", supports_search=False)

    result = _run(provider)

    assert provider.calls == 0
    assert result.eligible_provider_count == 0
    assert result.candidates == ()


def test_observation_projects_to_noncanonical_discovery_candidate():
    provider = FakeAdapter(
        "provider-a",
        (
            ProviderObservation(
                provider_symbol="AAPL",
                name="Apple Inc.",
                market="US",
                exchange="NMS",
                currency="USD",
                isin="US0378331005",
            ),
        ),
    )

    result = _run(provider, filters={"market": "US"})

    candidate = result.candidates[0]
    assert candidate.kind == "DISCOVERY"
    assert not hasattr(candidate, "asset_id")
    assert candidate.reported_symbol == "AAPL"
    assert candidate.reported_identifiers == {
        "PROVIDER_SYMBOL": "AAPL",
        "ISIN": "US0378331005",
    }
    assert candidate.match_field == "identifier:PROVIDER_SYMBOL"


def test_name_matching_uses_canonical_tiers_not_provider_relevance():
    provider = FakeAdapter(
        "provider-a",
        (ProviderObservation(provider_symbol="AAPL", name="Apple Inc."),),
    )

    prefix = _run(provider, query="App")

    assert prefix.candidates[0].match_field == "name_prefix"


def test_registry_only_classification_filter_does_not_exclude_discovery():
    provider = FakeAdapter(
        "provider-a",
        (ProviderObservation(provider_symbol="AAPL", name="Apple Inc."),),
    )

    result = _run(provider, filters={"asset_class": "EQUITY"})

    assert result.successful_provider_count == 1
    assert len(result.candidates) == 1
    assert result.candidates[0].reported_symbol == "AAPL"


def test_provider_observed_filter_still_excludes_nonmatching_discovery():
    provider = FakeAdapter(
        "provider-a",
        (
            ProviderObservation(
                provider_symbol="AAPL",
                market="US",
                exchange="NMS",
                currency="USD",
            ),
        ),
    )

    result = _run(provider, filters={"currency": "THB"})

    assert result.successful_provider_count == 1
    assert result.candidates == ()


def test_provider_timeout_is_isolated_and_disclosed():
    slow = FakeAdapter("slow", delay=0.05)
    fast = FakeAdapter("fast", (ProviderObservation(provider_symbol="AAPL"),))

    result = _run(slow, fast, timeout_ms=10)

    assert result.successful_provider_count == 1
    assert result.failures[0].source == "slow"
    assert result.failures[0].reason == "TIMEOUT"
    assert [candidate.provider_name for candidate in result.candidates] == ["fast"]


def test_provider_error_does_not_cancel_sibling():
    failing = FakeAdapter("failing", error=RuntimeError("secret provider detail"))
    healthy = FakeAdapter("healthy", (ProviderObservation(provider_symbol="AAPL"),))

    result = _run(failing, healthy)

    assert result.successful_provider_count == 1
    assert result.failures[0].message == "Discovery provider failed."
    assert "secret" not in result.failures[0].message


def test_successful_provider_observations_are_cached_per_provider():
    provider = FakeAdapter("provider-a", (ProviderObservation(provider_symbol="AAPL"),))
    cache = SearchCache()

    first = _run(provider, cache=cache)
    second = _run(provider, cache=cache)

    assert first.candidates == second.candidates
    assert provider.calls == 1


def test_provider_and_cache_outcomes_use_existing_structured_log_path(caplog):
    provider = FakeAdapter("provider-a", (ProviderObservation(provider_symbol="AAPL"),))
    cache = SearchCache()

    with caplog.at_level(logging.INFO, logger="services.asset_search.discovery_search"):
        _run(provider, cache=cache)
        _run(provider, cache=cache)

    messages = [record.getMessage() for record in caplog.records]
    assert any("provider=provider-a outcome=success cache=miss latency_ms=" in message for message in messages)
    assert any("provider=provider-a outcome=success cache=hit latency_ms=" in message for message in messages)


def test_timed_out_provider_does_not_write_cache_after_cancellation():
    provider = FakeAdapter(
        "provider-a",
        (ProviderObservation(provider_symbol="AAPL"),),
        delay=0.05,
    )
    cache = SearchCache()

    first = _run(provider, timeout_ms=5, cache=cache)
    provider.delay = 0
    second = _run(provider, timeout_ms=100, cache=cache)

    assert first.successful_provider_count == 0
    assert second.successful_provider_count == 1
    assert provider.calls == 2


def test_fanout_constant_is_bounded():
    assert MAX_CONCURRENT_PROVIDERS == 8
