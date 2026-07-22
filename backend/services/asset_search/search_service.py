"""Market Intelligence search orchestration (Milestone M37.3, WP6).

Implements the complete CATALOG/UNIVERSE lifecycle from the frozen M37.1
technical design.  It composes the existing owners rather than duplicating
them: Asset Foundation catalog search (WP2), external discovery fan-out
(WP6), Registry-authoritative merge (WP3), and canonical ranking (WP4).

Read-only: this module never writes Registry state, imports a concrete
provider, or calls the identity resolver directly.  External observations
reach the resolver only through merge.py's non-recording F3-safe boundary.

Pagination limitation (disclosed, not silently absent): `catalog_search.py`
(WP2) has no offset/skip parameter — `search()` always returns the top
`limit` candidates from position zero, clamped to `MAX_LIMIT` (50). To
support cursor continuation at all without modifying WP2 (out of this
package's ownership), this module always requests WP2's maximum window
(50) internally, ranks that whole window once, and paginates *within it*
in memory. A query matching more than 50 registered assets cannot be paged
past position 50 in v1 — an inherited ceiling of the already-frozen WP2
module, not a gap this package can close without reopening WP2.

Cursor honesty within that bounded window: every emitted `cursor_next`
points strictly forward (`start_index` only ever increases), so following
cursors terminates, never repeats a candidate, and the final reachable
page always has `cursor_next=None` — all provable from `ranked` being a
fixed-length list per request and `start_index` advancing by at least one
page's worth each hop.

What this module cannot tell the caller (disclosed limitation, not
silently overclaimed): `catalog_search.search()` returns only the
already-truncated top-50 window, with no total-match count alongside it.
When the window is exactly full (50 candidates), this module cannot
distinguish "the catalog genuinely has exactly 50 matches" from "the
catalog has more than 50 matches and WP2 silently dropped the rest" —
both look identical from here. Rather than inventing a new response field
to carry a count WP2 does not expose, this module reuses the already
-approved `warnings` list (§5) to disclose the *possibility* of
truncation whenever the window is full, so `cursor_next=None` on the
final page never gets over-read as "the catalog has no more matches" when
that cannot actually be verified. This is an explicit reopen trigger: if
WP2 ever exposes a true total-match count, this heuristic should be
replaced with an exact one.
"""
from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from services.asset_search import catalog_search, discovery_search
from services.asset_search.merge import merge as merge_candidates
from services.asset_search.ranking import rank

__all__ = [
    "SearchServiceError",
    "InvalidCursorError",
    "CatalogUnavailableError",
    "DegradationEntry",
    "SearchResult",
    "CATALOG_SCOPE",
    "UNIVERSE_SCOPE",
    "VALID_SCOPES",
    "search",
]

log = logging.getLogger(__name__)

CATALOG_SCOPE = "CATALOG"
UNIVERSE_SCOPE = "UNIVERSE"
VALID_SCOPES = frozenset({CATALOG_SCOPE, UNIVERSE_SCOPE})

# WP2's own hard ceiling (catalog_search.MAX_LIMIT) — the largest window
# this module can ever ask WP2 for, regardless of the caller's requested
# page size. See module docstring's "Pagination limitation" note.
_CATALOG_WINDOW_LIMIT = catalog_search.MAX_LIMIT


class SearchServiceError(Exception):
    """Base class for search_service-owned failures (stages 2/9 of §8).
    Mapping these to HTTP status/error codes is `routers/asset_search.py`'s
    job (§8 stage 1/11) — this module raises typed Python exceptions only."""


class InvalidCursorError(SearchServiceError):
    """§15 F9: the cursor is malformed, or was issued for a different
    query/scope/classification_filters, or no longer corresponds to a
    position in the current deterministic ordering."""


class CatalogUnavailableError(SearchServiceError):
    """§8 stage 4 failure row: the catalog (WP2) could not be queried due
    to a database error. CATALOG-scope requests fail entirely on this —
    catalog is their only source."""


@dataclass(frozen=True)
class DegradationEntry:
    """Wire-shaped per §5's `DegradationEntry`."""

    source: str
    reason: str
    message: str
    candidate_kind_uncertain: bool = False


@dataclass(frozen=True)
class SearchResult:
    """Wire-shaped per §5's `SearchResponse` (minus HTTP-layer concerns —
    building the actual HTTP response body is `routers/asset_search.py`'s
    job)."""

    candidates: Tuple[Any, ...]
    scope_used: str
    degraded: bool
    degradation: Tuple[DegradationEntry, ...]
    cursor_next: Optional[str]
    warnings: Tuple[str, ...]
    query_echo: str


def _tier_for_cursor(candidate: Any) -> int:
    """Reads the tier `ranking.py` already assigned this candidate (via its
    `match_field`) to build an opaque resume position. This does not
    decide ranking order — `rank()` already did that — it only labels an
    already-produced position for the cursor, the same closed vocabulary
    `ranking.py` itself uses (symbol match, then identifier match; name
    tiers are not reachable in v1, §9/F4)."""
    match_field = candidate.match_field
    if match_field in ("canonical_symbol", "display_symbol"):
        return 0
    if match_field.startswith("identifier:"):
        return 1
    return 2


def _encode_cursor(*, query: str, scope: str, filters: Mapping[str, str], tier: int, symbol: str) -> str:
    payload = {
        "q": query,
        "s": scope,
        "f": sorted(filters.items()),
        "t": tier,
        "sym": symbol,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def _decode_cursor(cursor: str, *, query: str, scope: str, filters: Mapping[str, str]) -> Tuple[int, str]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii"))
        payload = json.loads(raw)
        expected = {"q": query, "s": scope, "f": sorted(filters.items())}
        if payload.get("q") != expected["q"] or payload.get("s") != expected["s"] or payload.get("f") != expected["f"]:
            raise InvalidCursorError("cursor was issued for a different query/scope/classification_filters")
        return int(payload["t"]), str(payload["sym"])
    except InvalidCursorError:
        raise
    except Exception as exc:
        raise InvalidCursorError("cursor is malformed") from exc


async def search(
    db: Session,
    *,
    query: str,
    scope: str,
    filters: Sequence[Tuple[str, str]] = (),
    limit: int = catalog_search.DEFAULT_LIMIT,
    cursor: Optional[str] = None,
    timeout_ms: int = discovery_search.DEFAULT_PROVIDER_TIMEOUT_MS,
) -> SearchResult:
    """Orchestrate the approved CATALOG or UNIVERSE search lifecycle.

    Provider fan-out remains inside ``discovery_search``; Registry identity
    checks remain inside ``merge``; deterministic order remains exclusively
    owned by ``ranking.rank``.  This function assembles those results and
    their degradation disclosures without writing permanent state.
    """
    normalized_query = catalog_search.normalize_query(query)
    filters_map = catalog_search.validate_filters(filters)
    clamped_limit = max(catalog_search.MIN_LIMIT, min(limit, catalog_search.MAX_LIMIT))
    warnings: List[str] = []
    if limit > catalog_search.MAX_LIMIT:
        warnings.append(f"limit clamped to {catalog_search.MAX_LIMIT}")
    elif limit < catalog_search.MIN_LIMIT:
        warnings.append(f"limit clamped to {catalog_search.MIN_LIMIT}")

    degradation: List[DegradationEntry] = []
    catalog_candidates: List[Any] = []
    catalog_unavailable = False
    try:
        catalog_result = catalog_search.search(
            db, normalized_query, filters=filters, limit=_CATALOG_WINDOW_LIMIT
        )
        catalog_candidates = list(catalog_result.candidates)
    except SQLAlchemyError as exc:
        if scope == CATALOG_SCOPE:
            raise CatalogUnavailableError("catalog search unavailable") from exc
        catalog_unavailable = True
        log.error("asset_search: catalog unavailable during UNIVERSE search", exc_info=True)
        degradation.append(
            DegradationEntry(
                source="catalog",
                reason="UNAVAILABLE",
                message="Catalog search is unavailable.",
            )
        )

    candidates: List[Any] = catalog_candidates
    if scope == UNIVERSE_SCOPE:
        discovery_result = await discovery_search.discover(
            normalized_query,
            filters=filters_map,
            timeout_ms=timeout_ms,
        )

        if discovery_result.eligible_provider_count == 0:
            degradation.append(
                DegradationEntry(
                    source="universe",
                    reason="UNSUPPORTED",
                    message="No discovery providers are capability-eligible yet.",
                )
            )
        elif discovery_result.successful_provider_count == 0:
            degradation.append(
                DegradationEntry(
                    source="universe",
                    reason="UNAVAILABLE",
                    message="All discovery providers are unavailable.",
                )
            )
        else:
            degradation.extend(
                DegradationEntry(
                    source=failure.source,
                    reason=failure.reason,
                    message=failure.message,
                )
                for failure in discovery_result.failures
            )

        merge_failures: List[Exception] = []
        if catalog_unavailable:
            candidates = catalog_candidates + list(discovery_result.candidates)
            if discovery_result.candidates:
                merge_failures.append(
                    CatalogUnavailableError("Registry merge check unavailable")
                )
        else:
            candidates = merge_candidates(
                db,
                catalog_candidates,
                discovery_result.candidates,
                on_resolve_error=lambda _candidate, exc: merge_failures.append(exc),
            )

        if merge_failures:
            log.error(
                "asset_search: Registry merge check unavailable for %d candidate(s)",
                len(merge_failures),
            )
            degradation.append(
                DegradationEntry(
                    source="registry-merge",
                    reason="ERROR",
                    message="Registry standing could not be verified for some discovery candidates.",
                    candidate_kind_uncertain=True,
                )
            )

    ranked = rank(candidates)

    if len(catalog_candidates) >= _CATALOG_WINDOW_LIMIT:
        # Window is full — WP2 exposes no total-match count, so a genuine
        # 50-match catalog and a truncated >50-match catalog are
        # indistinguishable from here (see module docstring). Disclose the
        # possibility honestly rather than let an eventual cursor_next=None
        # be misread as "no more matches exist in the catalog."
        warnings.append(
            f"results may be limited to the first {_CATALOG_WINDOW_LIMIT} "
            "catalog matches; additional matches beyond this window, if "
            "any, are not reachable in v1"
        )

    start_index = 0
    if cursor is not None:
        if scope == UNIVERSE_SCOPE:
            raise InvalidCursorError("cursor is not supported for scope=UNIVERSE")
        decoded_tier, decoded_symbol = _decode_cursor(
            cursor, query=normalized_query, scope=scope, filters=filters_map
        )
        for index, candidate in enumerate(ranked):
            if _tier_for_cursor(candidate) == decoded_tier and candidate.canonical_symbol == decoded_symbol:
                start_index = index + 1
                break
        else:
            raise InvalidCursorError("cursor position no longer corresponds to a defined ordering")

    page = ranked[start_index : start_index + clamped_limit]
    end_index = start_index + len(page)

    cursor_next: Optional[str] = None
    if scope == CATALOG_SCOPE and end_index < len(ranked) and page:
        last = page[-1]
        cursor_next = _encode_cursor(
            query=normalized_query,
            scope=scope,
            filters=filters_map,
            tier=_tier_for_cursor(last),
            symbol=last.canonical_symbol,
        )

    return SearchResult(
        candidates=tuple(page),
        scope_used=scope,
        degraded=bool(degradation),
        degradation=tuple(degradation),
        cursor_next=cursor_next,
        warnings=tuple(warnings),
        query_echo=normalized_query,
    )
