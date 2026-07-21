"""Tests for the Universal Asset Search orchestration + HTTP layer
(Milestone M37.2, WP5).

Validates docs/implementation/M37_1_Universal_Asset_Search_Technical_Design.md
Section 8 (query processing lifecycle) and Section 15 (API design) against
`services/asset_search/search_service.py` and `routers/asset_search.py`:

  1.  Successful CATALOG search
  2.  Empty query -> 400 EMPTY_QUERY
  3.  Query >200 code points -> 400 QUERY_TOO_LONG
  4.  Invalid filter -> 400 UNKNOWN_FILTER_DIMENSION
  5.  Conflicting filters -> ConflictingFiltersError (search_service level;
      the HTTP dict shape cannot itself carry a duplicate key, see below)
  6.  Unsupported search mode -> 400 INVALID_SCOPE
  7.  Invalid limit -> 400 MALFORMED_REQUEST (bad type) and clamped-with-
      warning (out of [1,50] but well-typed)
  8.  HTTP serialization / response contains only approved fields
  11. WP2 (`catalog_search.search`) invoked exactly once per request
  13. WP4 (`ranking.rank`) invoked exactly once per request
  14. Pipeline ordering: catalog search happens before ranking
  15. No bypass of completed work packages (tiering + ranking both visibly
      applied to a mixed-tier result)
  17. Read-only: zero permanent writes across successful and failing calls
  21. Deterministic repeated requests
  22. Dependency injection: `db` is threaded through via FastAPI `Depends`
  23. Endpoint registration: `POST /asset-search` is a real route
  24. OpenAPI generation includes the route

Item 9 (RegistryConsistencyError mapping) and item 12 (WP3 invoked exactly
once) are addressed in test_asset_search_conformance.py instead of here:
the frozen design's own WP5 dependency row states "F12 - WP3/merge
removed: this package's CATALOG-only delivery never invokes `merge.py`"
(docs, Section 20, WP5). Since `merge.py` is never called, WP3 is invoked
*zero* times by design (not once), and `RegistryConsistencyError` can never
be raised on this pipeline - there is nothing to map. Both facts are
proven structurally (no `merge` import anywhere in `search_service.py` /
`routers/asset_search.py`) rather than exercised behaviorally, since
exercising an intentionally-unreachable path would require importing a
module F12 explicitly forecloses.

Repo convention: no FastAPI TestClient/HTTP harness exists in this codebase
(see test_watchlist_registry.py) - the router's async endpoint function is
called directly via asyncio.run(), matching test_main_get_sector_registry.py
and friends.
"""
import asyncio
import base64
import json
import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base
import models.asset  # noqa: F401 - registers Asset* tables on Base.metadata
import models.registry_finding  # noqa: F401 - registers RegistryFinding table
from models.asset import Asset, AssetClassification, AssetIdentifier
from models.registry_finding import RegistryFinding
from services import registry_service as svc
from services.asset_domain import AssetClaim, AssetType

from services.asset_search import catalog_search, search_service
from services.asset_search.search_service import InvalidCursorError
from routers.asset_search import router as asset_search_router, asset_search


def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _claim(**overrides):
    defaults = dict(
        canonical_symbol="KBANK", asset_type=AssetType.EQUITY,
        market="TH", exchange="SET", currency="THB",
    )
    defaults.update(overrides)
    return AssetClaim(**defaults)


def _mint(db, **overrides):
    return svc.mint_asset(db, _claim(**overrides))


def _all_row_counts(db) -> dict:
    return {
        "Asset": db.query(Asset).count(),
        "AssetIdentifier": db.query(AssetIdentifier).count(),
        "AssetClassification": db.query(AssetClassification).count(),
        "RegistryFinding": db.query(RegistryFinding).count(),
    }


def _call(payload: dict, db):
    return asyncio.run(asset_search(payload, db))


# ── 1. Successful CATALOG search ────────────────────────────────────────────

def test_successful_catalog_search():
    db = make_session()
    asset = _mint(db)

    body = _call({"query": "KBANK", "scope": "CATALOG"}, db)

    assert body["scope_used"] == "CATALOG"
    assert body["degraded"] is False
    assert body["degradation"] == []
    assert [c["asset_id"] for c in body["candidates"]] == [asset.id]
    assert body["query_echo"] == "KBANK"


# ── 2. Empty query ───────────────────────────────────────────────────────────

def test_empty_query_after_normalization_maps_to_400():
    db = make_session()
    with pytest.raises(HTTPException) as exc_info:
        _call({"query": "   ", "scope": "CATALOG"}, db)
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "EMPTY_QUERY"


# ── 3. Query too long ────────────────────────────────────────────────────────

def test_query_too_long_maps_to_400():
    db = make_session()
    with pytest.raises(HTTPException) as exc_info:
        _call({"query": "A" * 201, "scope": "CATALOG"}, db)
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "QUERY_TOO_LONG"


# ── 4. Invalid filter ────────────────────────────────────────────────────────

def test_unknown_filter_dimension_maps_to_400():
    db = make_session()
    with pytest.raises(HTTPException) as exc_info:
        _call(
            {"query": "KBANK", "scope": "CATALOG", "classification_filters": {"sector": "BANK"}},
            db,
        )
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "UNKNOWN_FILTER_DIMENSION"


# ── 5. Conflicting filters (search_service level - see module docstring) ───

def test_conflicting_filters_raises_at_service_level():
    db = make_session()
    _mint(db)
    with pytest.raises(catalog_search.ConflictingFiltersError):
        search_service.search(
            db, query="KBANK", scope="CATALOG",
            filters=(("market", "TH"), ("market", "US")),
        )


# ── 6. Unsupported search mode ───────────────────────────────────────────────

def test_invalid_scope_maps_to_400():
    db = make_session()
    with pytest.raises(HTTPException) as exc_info:
        _call({"query": "KBANK", "scope": "BOGUS"}, db)
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "INVALID_SCOPE"


def test_missing_scope_maps_to_400():
    db = make_session()
    with pytest.raises(HTTPException) as exc_info:
        _call({"query": "KBANK"}, db)
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "INVALID_SCOPE"


# ── 7. Invalid limit ──────────────────────────────────────────────────────────

def test_malformed_limit_type_maps_to_400():
    db = make_session()
    with pytest.raises(HTTPException) as exc_info:
        _call({"query": "KBANK", "scope": "CATALOG", "limit": "ten"}, db)
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "MALFORMED_REQUEST"


def test_out_of_range_limit_is_clamped_with_warning_not_rejected():
    db = make_session()
    _mint(db)

    body = _call({"query": "KBANK", "scope": "CATALOG", "limit": 500}, db)

    assert body["candidates"]  # still succeeds
    assert any("clamped" in w for w in body["warnings"])


# ── 8/16. Response shape ─────────────────────────────────────────────────────

def test_response_contains_only_approved_fields():
    db = make_session()
    _mint(db)

    body = _call({"query": "KBANK", "scope": "CATALOG"}, db)

    assert set(body.keys()) == {
        "candidates", "scope_used", "degraded", "degradation",
        "cursor_next", "warnings", "query_echo",
    }
    candidate = body["candidates"][0]
    assert set(candidate.keys()) == {
        "kind", "asset_id", "canonical_symbol", "display_symbol", "asset_type",
        "market", "exchange", "currency", "classifications", "status", "match_field",
    }
    # Never expose internal Registry/resolver/finding shapes.
    assert "ResolutionResult" not in json.dumps(body)
    assert "RegistryFinding" not in json.dumps(body)


# ── 11. WP2 invoked exactly once ─────────────────────────────────────────────

def test_catalog_search_invoked_exactly_once():
    db = make_session()
    _mint(db)

    with patch(
        "services.asset_search.search_service.catalog_search.search",
        wraps=catalog_search.search,
    ) as mock_search:
        _call({"query": "KBANK", "scope": "CATALOG"}, db)

    assert mock_search.call_count == 1


# ── 13. WP4 invoked exactly once ─────────────────────────────────────────────

def test_ranking_invoked_exactly_once():
    db = make_session()
    _mint(db)

    with patch(
        "services.asset_search.search_service.rank",
        wraps=search_service.rank,
    ) as mock_rank:
        _call({"query": "KBANK", "scope": "CATALOG"}, db)

    assert mock_rank.call_count == 1


# ── 14. Pipeline ordering ────────────────────────────────────────────────────

def test_catalog_search_happens_before_ranking():
    db = make_session()
    _mint(db)
    call_order = []

    real_search = catalog_search.search
    real_rank = search_service.rank

    def _tracked_search(*args, **kwargs):
        call_order.append("catalog_search")
        return real_search(*args, **kwargs)

    def _tracked_rank(*args, **kwargs):
        call_order.append("rank")
        return real_rank(*args, **kwargs)

    with patch("services.asset_search.search_service.catalog_search.search", side_effect=_tracked_search), \
         patch("services.asset_search.search_service.rank", side_effect=_tracked_rank):
        _call({"query": "KBANK", "scope": "CATALOG"}, db)

    assert call_order == ["catalog_search", "rank"]


# ── 15. No bypass — tiering and ranking are both visibly applied ────────────

def test_no_bypass_symbol_tier_ranks_before_identifier_tier():
    db = make_session()
    symbol_hit = _mint(db, canonical_symbol="AAA")
    identifier_hit = _mint(db, canonical_symbol="ZZZ")
    from services.asset_domain import IdentifierRecord, IdentifierType
    svc.attach_identifier(db, identifier_hit.id, IdentifierRecord(
        identifier_type=IdentifierType.ISIN, value="AAA", source="test",
    ))

    body = _call({"query": "AAA", "scope": "CATALOG"}, db)

    assert [c["asset_id"] for c in body["candidates"]] == [symbol_hit.id, identifier_hit.id]


# ── 17. Read-only ─────────────────────────────────────────────────────────────

def test_zero_permanent_writes_across_successful_and_failing_calls():
    db = make_session()
    _mint(db)
    before = _all_row_counts(db)

    _call({"query": "KBANK", "scope": "CATALOG"}, db)
    try:
        _call({"query": "", "scope": "CATALOG"}, db)
    except HTTPException:
        pass
    try:
        _call({"query": "KBANK", "scope": "NOPE"}, db)
    except HTTPException:
        pass

    assert _all_row_counts(db) == before


# ── 21. Deterministic repeated requests ─────────────────────────────────────

def test_repeated_identical_requests_are_deterministic():
    db = make_session()
    _mint(db, canonical_symbol="AAA")
    _mint(db, canonical_symbol="ZZZ", display_symbol="AAA")

    first = _call({"query": "AAA", "scope": "CATALOG"}, db)
    second = _call({"query": "AAA", "scope": "CATALOG"}, db)

    assert first == second
    assert len(first["candidates"]) == 2


# ── 22. Dependency injection ─────────────────────────────────────────────────

def test_endpoint_declares_db_dependency_injection():
    import inspect
    sig = inspect.signature(asset_search)
    assert "db" in sig.parameters
    default = sig.parameters["db"].default
    assert default is not inspect._empty  # a Depends(...) default is present


# ── 23. Endpoint registration ─────────────────────────────────────────────────

def test_route_is_registered_as_post_asset_search():
    assert asset_search_router.prefix == "/asset-search"
    paths_and_methods = {
        (route.path, tuple(sorted(route.methods)))
        for route in asset_search_router.routes
    }
    assert ("/asset-search", ("POST",)) in paths_and_methods


# ── 24. OpenAPI generation ────────────────────────────────────────────────────

def test_openapi_schema_includes_asset_search_route():
    app = FastAPI()
    app.include_router(asset_search_router)
    schema = app.openapi()
    assert "/asset-search" in schema["paths"]
    assert "post" in schema["paths"]["/asset-search"]


# ── UNIVERSE scope honest degradation (§13, F12 note) ───────────────────────

def test_universe_scope_is_accepted_and_degrades_honestly_without_provider_calls():
    db = make_session()
    _mint(db)

    body = _call({"query": "KBANK", "scope": "UNIVERSE"}, db)

    assert body["scope_used"] == "UNIVERSE"
    assert body["degraded"] is True
    assert body["degradation"] == [
        {"source": "universe", "reason": "UNSUPPORTED",
         "message": "No discovery providers are capability-eligible yet.",
         "candidate_kind_uncertain": False}
    ]
    assert body["cursor_next"] is None


def test_universe_scope_with_cursor_maps_to_400():
    db = make_session()
    with pytest.raises(HTTPException) as exc_info:
        _call({"query": "KBANK", "scope": "UNIVERSE", "cursor": "abc"}, db)
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "CURSOR_NOT_SUPPORTED_FOR_SCOPE"


# ── Pagination / cursor (§15 F9) ─────────────────────────────────────────────

def _mint_three_way_match(db, query_value: str):
    """catalog_search only matches an *exact* field value (no prefix/
    substring tier is approved yet, §12) - so to get several distinct
    candidates for one query, mint several distinct assets that each
    happen to carry `query_value` on a *different* field (canonical
    symbol, display symbol, an attached identifier)."""
    from services.asset_domain import IdentifierRecord, IdentifierType

    by_symbol = _mint(db, canonical_symbol=query_value)
    by_display = _mint(db, canonical_symbol="ZZZ1", display_symbol=query_value)
    by_identifier = _mint(db, canonical_symbol="ZZZ2")
    svc.attach_identifier(db, by_identifier.id, IdentifierRecord(
        identifier_type=IdentifierType.ISIN, value=query_value, source="test",
    ))
    return by_symbol, by_display, by_identifier


def test_cursor_round_trip_pages_through_results():
    db = make_session()
    by_symbol, by_display, by_identifier = _mint_three_way_match(db, "AAA")

    first_page = _call({"query": "AAA", "scope": "CATALOG", "limit": 2}, db)
    assert [c["asset_id"] for c in first_page["candidates"]] == [by_symbol.id, by_display.id]
    assert first_page["cursor_next"] is not None

    second_page = _call(
        {"query": "AAA", "scope": "CATALOG", "limit": 2, "cursor": first_page["cursor_next"]}, db
    )
    assert [c["asset_id"] for c in second_page["candidates"]] == [by_identifier.id]
    assert second_page["cursor_next"] is None


def test_cursor_for_different_query_is_rejected():
    db = make_session()
    _mint_three_way_match(db, "AAA")

    first_page = _call({"query": "AAA", "scope": "CATALOG", "limit": 1}, db)

    with pytest.raises(HTTPException) as exc_info:
        _call({"query": "ZZZ1", "scope": "CATALOG", "limit": 1, "cursor": first_page["cursor_next"]}, db)
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "INVALID_CURSOR"


def test_malformed_cursor_is_rejected():
    db = make_session()
    _mint(db)
    with pytest.raises(HTTPException) as exc_info:
        _call({"query": "KBANK", "scope": "CATALOG", "cursor": "not-valid-base64!!"}, db)
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "INVALID_CURSOR"


def test_malformed_cursor_type_maps_to_400():
    db = make_session()
    with pytest.raises(HTTPException) as exc_info:
        _call({"query": "KBANK", "scope": "CATALOG", "cursor": 123}, db)
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "MALFORMED_REQUEST"


# ── Pagination ceiling honesty (M37.2 WP5 remediation, Observation 2) ───────
# `catalog_search.search()` (WP2, frozen) truncates to its own MAX_LIMIT=50
# window with no total-match count alongside it. When that window comes
# back full, this module cannot tell "the catalog has exactly 50 matches"
# apart from "the catalog has more than 50 and WP2 silently dropped the
# rest" - both cases must be disclosed via the approved `warnings` field
# (no new response field invented), and cursor traversal within the
# bounded window must still terminate, never repeat, and end with
# cursor_next=None on the final page.

def _mock_full_window_result(total: int):
    return catalog_search.CatalogSearchResult(
        candidates=tuple(
            catalog_search.RegisteredCandidate(
                asset_id=i,
                canonical_symbol=f"SYM{i:04d}",
                asset_type="EQUITY",
                market="TH",
                exchange="SET",
                currency="THB",
                status="ACTIVE",
                match_field="canonical_symbol",
            )
            for i in range(total)
        )
    )


def test_full_window_emits_truncation_possibility_warning():
    db = make_session()
    with patch(
        "services.asset_search.search_service.catalog_search.search",
        return_value=_mock_full_window_result(search_service._CATALOG_WINDOW_LIMIT),
    ):
        body = _call({"query": "SYM", "scope": "CATALOG", "limit": 10}, db)

    assert any("50" in w or str(search_service._CATALOG_WINDOW_LIMIT) in w for w in body["warnings"])


def test_window_below_ceiling_emits_no_truncation_warning():
    db = make_session()
    with patch(
        "services.asset_search.search_service.catalog_search.search",
        return_value=_mock_full_window_result(search_service._CATALOG_WINDOW_LIMIT - 1),
    ):
        body = _call({"query": "SYM", "scope": "CATALOG", "limit": 10}, db)

    assert not any("not reachable" in w for w in body["warnings"])


def test_cursor_traversal_over_full_window_terminates_without_repeats_or_gaps():
    db = make_session()
    total = search_service._CATALOG_WINDOW_LIMIT
    seen_ids = []
    cursor = None
    hops = 0
    with patch(
        "services.asset_search.search_service.catalog_search.search",
        return_value=_mock_full_window_result(total),
    ):
        while True:
            hops += 1
            assert hops <= total + 1, "cursor traversal did not terminate"
            payload = {"query": "SYM", "scope": "CATALOG", "limit": 7}
            if cursor is not None:
                payload["cursor"] = cursor
            page = _call(payload, db)
            page_ids = [c["asset_id"] for c in page["candidates"]]
            seen_ids.extend(page_ids)
            cursor = page["cursor_next"]
            if cursor is None:
                break

    assert seen_ids == list(range(total)), "candidates repeated, skipped, or reordered across pages"


def test_final_page_has_no_next_cursor():
    db = make_session()
    with patch(
        "services.asset_search.search_service.catalog_search.search",
        return_value=_mock_full_window_result(3),
    ):
        body = _call({"query": "SYM", "scope": "CATALOG", "limit": 50}, db)

    assert len(body["candidates"]) == 3
    assert body["cursor_next"] is None


# ── Limit validation matrix (M37.2 WP5 remediation, Observation 3) ──────────
# §4: `limit: int = 20` - a non-nullable, non-boolean int, clamped (not
# rejected) when out of [1,50]. `bool` is a subclass of `int` in Python, so
# True/False must be explicitly rejected, not silently accepted as 1/0.

def test_limit_within_range_is_used_as_is():
    db = make_session()
    _mint(db)
    body = _call({"query": "KBANK", "scope": "CATALOG", "limit": 5}, db)
    assert not body["warnings"]


def test_limit_zero_is_clamped_to_minimum_with_warning():
    db = make_session()
    _mint(db)
    body = _call({"query": "KBANK", "scope": "CATALOG", "limit": 0}, db)
    assert body["candidates"]
    assert any("clamped" in w for w in body["warnings"])


def test_limit_negative_is_clamped_to_minimum_with_warning():
    db = make_session()
    _mint(db)
    body = _call({"query": "KBANK", "scope": "CATALOG", "limit": -5}, db)
    assert body["candidates"]
    assert any("clamped" in w for w in body["warnings"])


def test_limit_above_maximum_is_clamped_with_warning():
    db = make_session()
    _mint(db)
    body = _call({"query": "KBANK", "scope": "CATALOG", "limit": 51}, db)
    assert body["candidates"]
    assert any("clamped" in w for w in body["warnings"])


def test_limit_float_is_rejected_as_malformed():
    db = make_session()
    with pytest.raises(HTTPException) as exc_info:
        _call({"query": "KBANK", "scope": "CATALOG", "limit": 10.5}, db)
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "MALFORMED_REQUEST"


def test_limit_numeric_string_is_rejected_as_malformed():
    db = make_session()
    with pytest.raises(HTTPException) as exc_info:
        _call({"query": "KBANK", "scope": "CATALOG", "limit": "10"}, db)
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "MALFORMED_REQUEST"


def test_limit_null_is_rejected_as_malformed():
    """§4's `limit` is `int = 20` - not `int | None` (unlike `cursor`/
    `timeout_ms`, which are explicitly nullable). An explicit JSON `null`
    is therefore not the "missing" case and must not silently fall back
    to the default."""
    db = make_session()
    with pytest.raises(HTTPException) as exc_info:
        _call({"query": "KBANK", "scope": "CATALOG", "limit": None}, db)
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "MALFORMED_REQUEST"


def test_limit_boolean_true_is_rejected_not_treated_as_one():
    db = make_session()
    with pytest.raises(HTTPException) as exc_info:
        _call({"query": "KBANK", "scope": "CATALOG", "limit": True}, db)
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "MALFORMED_REQUEST"


def test_limit_boolean_false_is_rejected_not_treated_as_zero():
    db = make_session()
    with pytest.raises(HTTPException) as exc_info:
        _call({"query": "KBANK", "scope": "CATALOG", "limit": False}, db)
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "MALFORMED_REQUEST"


def test_limit_missing_uses_approved_default():
    db = make_session()
    _mint(db)
    body = _call({"query": "KBANK", "scope": "CATALOG"}, db)
    assert not body["warnings"]
