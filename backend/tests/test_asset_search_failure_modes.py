"""Failure/degradation-mode tests for the Universal Asset Search HTTP layer
(Milestone M37.3, WP6), including catalog, provider, and merge degradation.

Validates docs/implementation/M37_1_Universal_Asset_Search_Technical_Design.md
Section 13's failure table against `routers/asset_search.py` /
`services/asset_search/search_service.py`:

  - Invalid request (bad scope/empty query/unknown filter) -> 400, no
    candidates returned (covered in depth by test_asset_search_service.py;
    one representative case is kept here for the §13-table cross-check).
  - Catalog unavailable (DB error), CATALOG scope -> 503 CATALOG_UNAVAILABLE,
    no candidates returned, whole request fails.
  - Internal failure (unhandled exception, serialization error) -> 500
    INTERNAL, generic message, no stack trace in the response body.

The suite verifies that UNIVERSE failures remain partial and explicit while
CATALOG-only failure behavior stays unchanged.
"""
import asyncio
import os
import sys
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from models.database import Base
import models.asset  # noqa: F401
import models.registry_finding  # noqa: F401

from routers.asset_search import asset_search, _universe_rate_limiter
from services.asset_search import catalog_search, search_service
from services.asset_search.discovery_search import (
    DiscoveryCandidate,
    DiscoverySearchResult,
    ProviderFailure,
)


def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _call(payload: dict, db):
    return asyncio.run(asset_search(payload, db))


def test_invalid_request_returns_400_and_no_candidates():
    db = make_session()
    with pytest.raises(HTTPException) as exc_info:
        _call({"query": "", "scope": "CATALOG"}, db)
    assert exc_info.value.status_code == 400


def test_catalog_unavailable_maps_to_503():
    db = make_session()

    with patch(
        "services.asset_search.search_service.catalog_search.search",
        side_effect=OperationalError("SELECT 1", {}, Exception("db is down")),
    ):
        with pytest.raises(HTTPException) as exc_info:
            _call({"query": "KBANK", "scope": "CATALOG"}, db)

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "CATALOG_UNAVAILABLE"


def test_internal_failure_maps_to_500_with_generic_message():
    db = make_session()

    with patch(
        "services.asset_search.search_service.catalog_search.search",
        side_effect=ValueError("boom - unexpected internal state"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            _call({"query": "KBANK", "scope": "CATALOG"}, db)

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "INTERNAL"
    assert "boom" not in str(exc_info.value.detail)


def _candidate():
    return DiscoveryCandidate(
        claim_id="discovery:test:1",
        provider_name="provider-a",
        reported_symbol="AAPL",
        reported_name="Apple Inc.",
        reported_identifiers={"PROVIDER_SYMBOL": "AAPL"},
        market="US",
        currency="USD",
        match_field="identifier:PROVIDER_SYMBOL",
    )


def test_partial_provider_timeout_returns_results_and_per_provider_degradation():
    db = make_session()
    result = DiscoverySearchResult(
        candidates=(_candidate(),),
        failures=(
            ProviderFailure("slow-provider", "TIMEOUT", "Discovery provider timed out."),
        ),
        eligible_provider_count=2,
        successful_provider_count=1,
    )
    with patch(
        "services.asset_search.search_service.discovery_search.discover",
        new_callable=AsyncMock,
        return_value=result,
    ):
        body = _call({"query": "AAPL", "scope": "UNIVERSE"}, db)

    assert body["candidates"][0]["kind"] == "DISCOVERY"
    assert body["degradation"] == [
        {
            "source": "slow-provider",
            "reason": "TIMEOUT",
            "message": "Discovery provider timed out.",
            "candidate_kind_uncertain": False,
        }
    ]


def test_total_provider_failure_collapses_to_universe_unavailable():
    db = make_session()
    result = DiscoverySearchResult(
        candidates=(),
        failures=(ProviderFailure("provider-a", "ERROR", "Discovery provider failed."),),
        eligible_provider_count=1,
        successful_provider_count=0,
    )
    with patch(
        "services.asset_search.search_service.discovery_search.discover",
        new_callable=AsyncMock,
        return_value=result,
    ):
        body = _call({"query": "AAPL", "scope": "UNIVERSE"}, db)

    assert body["degradation"] == [
        {
            "source": "universe",
            "reason": "UNAVAILABLE",
            "message": "All discovery providers are unavailable.",
            "candidate_kind_uncertain": False,
        }
    ]


def test_registry_merge_failure_keeps_candidate_and_marks_kind_uncertain():
    db = make_session()
    result = DiscoverySearchResult((_candidate(),), (), 1, 1)
    with patch(
        "services.asset_search.search_service.discovery_search.discover",
        new_callable=AsyncMock,
        return_value=result,
    ), patch(
        "services.asset_search.merge.resolve",
        side_effect=OperationalError("SELECT 1", {}, Exception("db is down")),
    ):
        body = _call({"query": "AAPL", "scope": "UNIVERSE"}, db)

    assert body["candidates"][0]["kind"] == "DISCOVERY"
    assert body["degradation"] == [
        {
            "source": "registry-merge",
            "reason": "ERROR",
            "message": "Registry standing could not be verified for some discovery candidates.",
            "candidate_kind_uncertain": True,
        }
    ]


def test_catalog_unavailable_in_universe_returns_discovery_with_paired_disclosure():
    db = make_session()
    result = DiscoverySearchResult((_candidate(),), (), 1, 1)
    with patch(
        "services.asset_search.search_service.catalog_search.search",
        side_effect=OperationalError("SELECT 1", {}, Exception("db is down")),
    ), patch(
        "services.asset_search.search_service.discovery_search.discover",
        new_callable=AsyncMock,
        return_value=result,
    ):
        body = _call({"query": "AAPL", "scope": "UNIVERSE"}, db)

    assert body["candidates"][0]["kind"] == "DISCOVERY"
    assert [(entry["source"], entry["reason"]) for entry in body["degradation"]] == [
        ("catalog", "UNAVAILABLE"),
        ("registry-merge", "ERROR"),
    ]
    assert body["degradation"][1]["candidate_kind_uncertain"] is True


def test_universe_rate_limit_returns_429_with_retry_after():
    db = make_session()
    result = DiscoverySearchResult((), (), 1, 1)
    _universe_rate_limiter.reset()
    try:
        with patch(
            "services.asset_search.search_service.discovery_search.discover",
            new_callable=AsyncMock,
            return_value=result,
        ):
            for _ in range(30):
                _call({"query": "AAPL", "scope": "UNIVERSE"}, db)
            with pytest.raises(HTTPException) as exc_info:
                _call({"query": "AAPL", "scope": "UNIVERSE"}, db)

        assert exc_info.value.status_code == 429
        assert exc_info.value.detail == "RATE_LIMITED"
        assert int(exc_info.value.headers["Retry-After"]) >= 1
    finally:
        _universe_rate_limiter.reset()
