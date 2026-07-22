"""FastAPI router — Universal Asset Search (Milestone M37.3, WP6).

Implements docs/implementation/M37_1_Universal_Asset_Search_Technical_Design.md
Section 15's API design and Section 8 stage 1 (request validation) / stage
11 (response creation). This module is transport only: it parses the
request, calls `search_service.search()` (stages 2-10), maps exceptions to
the approved HTTP error codes (§13), and serializes the approved response
shape (§5). It never touches the database directly, never imports
`catalog_search`/`ranking`/provider internals beyond what `search_service`
already returns, and never imports `merge.py` directly.

Endpoint: `POST /asset-search`, `SearchRequest` JSON body (§4), mounted in
`main.py` via `app.include_router(asset_search_router)` alongside the
existing `scheduler_router`/`auth_router` pattern (§15). Authentication is
the existing global `auth_middleware` — no per-route dependency is added,
matching this repo's one actual auth mechanism (§15, F8).

Request/response schemas are plain dicts, validated by hand rather than by
a Pydantic model whose automatic `422` FastAPI validation-error response
this design explicitly does not want (§15: "FastAPI's automatic 422 is
intentionally overridden to the more specific 400 codes in §4/§13"). Manual
validation over a raw JSON body is the most direct way to guarantee every
rejection carries one of the exact §4/§13 error codes instead of generic
Pydantic validation noise, without adding a new global exception handler
that would also change every *other* existing endpoint's 422 behavior —
scope this package's frozen boundary does not authorize.
"""
from __future__ import annotations

import dataclasses
import logging
import math
import threading
import time

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from models.database import get_db
from services.asset_search.catalog_search import (
    ConflictingFiltersError,
    EmptyQueryError,
    InvalidFilterValueError,
    QueryTooLongError,
    UnknownFilterDimensionError,
)
from services.asset_search.search_service import (
    CatalogUnavailableError,
    InvalidCursorError,
    VALID_SCOPES,
    UNIVERSE_SCOPE,
    search as run_search,
)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/asset-search", tags=["asset-search"])

_MIN_TIMEOUT_MS = 200
_MAX_TIMEOUT_MS = 5000
_DEFAULT_TIMEOUT_MS = 2000
_UNIVERSE_RATE_LIMIT_PER_MINUTE = 30


class _TokenBucket:
    """Per-process token bucket for the repository's single shared caller."""

    def __init__(self, capacity: int, refill_per_second: float) -> None:
        self._capacity = float(capacity)
        self._refill_per_second = refill_per_second
        self._tokens = float(capacity)
        self._updated_at = time.monotonic()
        self._lock = threading.Lock()

    def consume(self) -> int | None:
        """Consume one token, or return the retry delay in whole seconds."""
        now = time.monotonic()
        with self._lock:
            elapsed = max(0.0, now - self._updated_at)
            self._tokens = min(
                self._capacity,
                self._tokens + elapsed * self._refill_per_second,
            )
            self._updated_at = now
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return None
            return max(1, math.ceil((1.0 - self._tokens) / self._refill_per_second))

    def reset(self) -> None:
        with self._lock:
            self._tokens = self._capacity
            self._updated_at = time.monotonic()


_universe_rate_limiter = _TokenBucket(
    _UNIVERSE_RATE_LIMIT_PER_MINUTE,
    _UNIVERSE_RATE_LIMIT_PER_MINUTE / 60.0,
)


def _bad_request(code: str) -> HTTPException:
    return HTTPException(status_code=400, detail=code)


def _validate_request(payload: dict) -> tuple[str, str, dict, int, str | None, int]:
    """§4/§8 stage 1: structural request validation, owned by the router.
    Returns (query, scope, classification_filters, limit, cursor, timeout_ms). Raises
    `HTTPException(400, ...)` with the exact §4/§13 error code on any
    violation — never coerces `scope`, never silently drops a bad field."""
    if not isinstance(payload, dict):
        raise _bad_request("MALFORMED_REQUEST")

    scope = payload.get("scope")
    if scope not in VALID_SCOPES:
        raise _bad_request("INVALID_SCOPE")

    query = payload.get("query")
    if not isinstance(query, str):
        raise _bad_request("MALFORMED_REQUEST")

    filters = payload.get("classification_filters", {})
    if filters is None:
        filters = {}
    if not isinstance(filters, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in filters.items()):
        raise _bad_request("MALFORMED_REQUEST")

    limit = payload.get("limit", 20)
    if not isinstance(limit, int) or isinstance(limit, bool):
        raise _bad_request("MALFORMED_REQUEST")

    cursor = payload.get("cursor")
    if cursor is not None and not isinstance(cursor, str):
        raise _bad_request("MALFORMED_REQUEST")
    if cursor is not None and scope == UNIVERSE_SCOPE:
        raise _bad_request("CURSOR_NOT_SUPPORTED_FOR_SCOPE")

    timeout_ms = payload.get("timeout_ms")
    if timeout_ms is None:
        timeout_ms = _DEFAULT_TIMEOUT_MS
    else:
        if not isinstance(timeout_ms, int) or isinstance(timeout_ms, bool):
            raise _bad_request("MALFORMED_REQUEST")
        timeout_ms = max(_MIN_TIMEOUT_MS, min(timeout_ms, _MAX_TIMEOUT_MS))

    return query, scope, filters, limit, cursor, timeout_ms


def _serialize_candidate(candidate) -> dict:
    """Expose only approved registered/discovery candidate projections."""
    return dataclasses.asdict(candidate)


@router.post("")
async def asset_search(payload: dict = Body(...), db: Session = Depends(get_db)) -> dict:
    """`POST /asset-search` — §15. Read-only and naturally idempotent."""
    query, scope, filters, limit, cursor, timeout_ms = _validate_request(payload)

    if scope == UNIVERSE_SCOPE:
        retry_after = _universe_rate_limiter.consume()
        if retry_after is not None:
            raise HTTPException(
                status_code=429,
                detail="RATE_LIMITED",
                headers={"Retry-After": str(retry_after)},
            )

    try:
        result = await run_search(
            db,
            query=query,
            scope=scope,
            filters=tuple(filters.items()),
            limit=limit,
            cursor=cursor,
            timeout_ms=timeout_ms,
        )
    except EmptyQueryError:
        raise _bad_request("EMPTY_QUERY")
    except QueryTooLongError:
        raise _bad_request("QUERY_TOO_LONG")
    except UnknownFilterDimensionError:
        raise _bad_request("UNKNOWN_FILTER_DIMENSION")
    except ConflictingFiltersError:
        raise _bad_request("CONFLICTING_FILTERS")
    except InvalidFilterValueError:
        raise _bad_request("INVALID_FILTER_VALUE")
    except InvalidCursorError:
        raise _bad_request("INVALID_CURSOR")
    except CatalogUnavailableError as exc:
        log.error("asset_search: catalog unavailable — %s", exc)
        raise HTTPException(status_code=503, detail="CATALOG_UNAVAILABLE")
    except HTTPException:
        raise
    except Exception:
        log.exception("asset_search: internal failure")
        raise HTTPException(status_code=500, detail="INTERNAL")

    return {
        "candidates": [_serialize_candidate(c) for c in result.candidates],
        "scope_used": result.scope_used,
        "degraded": result.degraded,
        "degradation": [dataclasses.asdict(entry) for entry in result.degradation],
        "cursor_next": result.cursor_next,
        "warnings": list(result.warnings),
        "query_echo": result.query_echo,
    }
