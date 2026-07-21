"""Market Intelligence — Search Orchestration (Milestone M37.2, WP5).

Implements docs/implementation/M37_1_Universal_Asset_Search_Technical_Design.md
Section 8's query-processing lifecycle for the CATALOG-only delivery this
work package ships (§3, §15). This module owns stages 2/3/9/10 of that
lifecycle (query normalization delegation, scope echoing, pagination,
degradation assembly) and composes — never reimplements — the stages owned
by earlier work packages:

- Stage 4 (catalog search): `catalog_search.search()` (WP2).
- Stage 8 (ranking): `ranking.rank()` (WP4).

**F12 — `merge.py` (WP3) is deliberately never imported or called here.**
The frozen design's own WP5 dependency row (§20, "WP5 — Orchestration +
CATALOG-only API") states this explicitly: "Dependencies: WP2, WP4 (F12 —
WP3/merge removed: this package's CATALOG-only delivery never invokes
`merge.py`, since UNIVERSE-scope dedup is not part of its exclusions; the
original dependency was incorrect)." Registry-authoritative deduplication
(§8 stage 7) only has work to do when discovery candidates exist to
reconcile against the Registry — and discovery candidates do not exist
until WP6 ships `discovery_search.py`. Wiring `merge.py` into a pipeline
that will only ever hand it registered candidates (nothing to merge) would
be dead code, not conformance. When WP6 ships and this module gains a real
UNIVERSE-scope discovery stage, `merge.py` becomes a genuine dependency of
*that* future stage — not of this one.

`scope=UNIVERSE` is accepted (§4: "scope absent or invalid -> 400
INVALID_SCOPE, never defaulted" implies UNIVERSE is a valid contract value,
not one to reject) but is never given a discovery fan-out — v1's
permanent, honest state is "zero capability-eligible providers" (§13's own
documented row, true today independent of WP6), so a UNIVERSE-scope
request runs the exact same catalog-only pipeline as CATALOG scope and
returns `degraded=true` with a single `reason=UNSUPPORTED, source=universe`
DegradationEntry (§13). This is not "implementing UNIVERSE search" — no
provider is contacted, no fan-out logic exists — it is honestly disclosing
that UNIVERSE search does not exist yet, exactly as §13/§17 already require
independent of WP6's timeline.

Read-only: this module never calls `db.add`/`flush`/`commit`, never
imports a provider adapter, and never imports `identity_resolver`.

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

What this module *cannot* tell the caller (disclosed limitation, not
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

from services.asset_search import catalog_search
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


def search(
    db: Session,
    *,
    query: str,
    scope: str,
    filters: Sequence[Tuple[str, str]] = (),
    limit: int = catalog_search.DEFAULT_LIMIT,
    cursor: Optional[str] = None,
) -> SearchResult:
    """Orchestrates the approved CATALOG-only lifecycle (§8): normalizes
    and searches the catalog (WP2, stage 4), ranks the result (WP4, stage
    8), paginates it (stage 9), and assembles degradation disclosure
    (stage 10). Never calls `merge.py` (F12, see module docstring). Never
    writes anything; never imports a provider adapter or
    `identity_resolver`.

    `scope` must already be validated by the caller (router stage 1) to be
    one of `VALID_SCOPES` — this function trusts that and only branches on
    it to decide whether to add the UNIVERSE "zero capability-eligible
    providers" degradation entry (§13)."""
    filters_map: Dict[str, str] = dict(filters)
    clamped_limit = max(catalog_search.MIN_LIMIT, min(limit, catalog_search.MAX_LIMIT))
    warnings: List[str] = []
    if limit > catalog_search.MAX_LIMIT:
        warnings.append(f"limit clamped to {catalog_search.MAX_LIMIT}")
    elif limit < catalog_search.MIN_LIMIT:
        warnings.append(f"limit clamped to {catalog_search.MIN_LIMIT}")

    try:
        catalog_result = catalog_search.search(
            db, query, filters=filters, limit=_CATALOG_WINDOW_LIMIT
        )
    except SQLAlchemyError as exc:
        raise CatalogUnavailableError("catalog search unavailable") from exc

    normalized_query = catalog_search.normalize_query(query)
    ranked = rank(list(catalog_result.candidates))

    if len(ranked) >= _CATALOG_WINDOW_LIMIT:
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

    degradation: List[DegradationEntry] = []
    if scope == UNIVERSE_SCOPE:
        degradation.append(
            DegradationEntry(
                source="universe",
                reason="UNSUPPORTED",
                message="No discovery providers are capability-eligible yet.",
            )
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
