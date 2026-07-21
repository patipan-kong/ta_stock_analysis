"""Failure/degradation-mode tests for the Universal Asset Search HTTP layer
(Milestone M37.2, WP5) — catalog-relevant rows only (per WP5's acceptance
criteria; UNIVERSE-scope provider-failure rows do not apply until WP6).

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

`RegistryConsistencyError` mapping is intentionally not exercised here.
The frozen design's WP5 dependency row states F12 removed `merge.py` from
this package's CATALOG-only pipeline entirely - `search_service.py` never
calls `merge()`, so `RegistryConsistencyError` cannot be raised on this
code path. See test_asset_search_conformance.py for the structural proof
that `merge` is not imported.
"""
import asyncio
import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from models.database import Base
import models.asset  # noqa: F401
import models.registry_finding  # noqa: F401

from routers.asset_search import asset_search
from services.asset_search import catalog_search


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
