"""Asset Foundation — Catalog Search (Milestone M37.2, WP2).

Implements docs/implementation/M37_1_Universal_Asset_Search_Technical_Design.md
Section 9's catalog-search design: text/identifier matching against
`assets` + `asset_identifiers` + `asset_classifications`, classification
filters, and deterministic catalog-stage ordering. Per Section 3's module
placement table, this is the one place Asset Foundation projects
registered candidates for search — it is permanently read-only (no
`db.add`/`flush`/`commit` anywhere in this module) and never imports a
provider adapter, `identity_resolver.resolve`/`adjudicate`, or any other
Registry-mutating path; ranking across sources (Section 12), external
discovery (Section 10), merge (Section 11), and the HTTP layer
(Section 15) are later, separately-approved work packages
(WP3/WP4/WP5/WP6) this module does not anticipate.

Name matching (Section 9's `AssetDescriptiveName`/`Asset.name`) is out of
scope until WP1 ships that schema — deliberately absent here, not silently
approximated with a column that does not exist yet (F4). NAME_SEARCH_
AVAILABLE reflects this honestly so a later caller (search_service.py,
WP5) can disclose it rather than the gap being invisible.

Case-insensitive comparison is done in Python (NFC-normalize, then
`str.casefold()`), not pushed into the SQL layer. The technical design
suggested `ILIKE`/`COLLATE NOCASE`; direct testing during implementation
showed SQLite's built-in `LOWER()`/`COLLATE NOCASE` are ASCII-only, so an
accented symbol (e.g. stored as precomposed "E" + acute) would silently
fail to case-fold and under-match on SQLite while working correctly on
Postgres — exactly the kind of cross-engine correctness gap Section 9
says v1 must not have ("must not assume Postgres-only operators... only
for a v2 performance enhancement"). Matching the entire catalog in Python
per search is an explicitly acceptable v1 trade given Section 9's own
characterization of the catalog as "a platform's own instrument list, not
an internet-scale corpus," and its own deferral of index/performance
questions to a later, separate decision.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Mapping, Optional, Sequence, Tuple

from sqlalchemy.orm import Session

from models.asset import Asset, AssetClassification, AssetIdentifier
from services.asset_domain import ClassificationDimension

__all__ = [
    "CatalogSearchError",
    "QueryTooLongError",
    "EmptyQueryError",
    "UnknownFilterDimensionError",
    "InvalidFilterValueError",
    "ConflictingFiltersError",
    "ALLOWED_FILTER_KEYS",
    "NAME_SEARCH_AVAILABLE",
    "RegisteredCandidate",
    "CatalogSearchResult",
    "normalize_query",
    "validate_filters",
    "search",
]

MAX_RAW_QUERY_CODEPOINTS = 200
DEFAULT_LIMIT = 20
MIN_LIMIT = 1
MAX_LIMIT = 50

# Native Asset columns a filter key may target directly (§4's classification_filters).
_NATIVE_COLUMN_FILTERS: Dict[str, Any] = {
    "market": Asset.market,
    "exchange": Asset.exchange,
    "currency": Asset.currency,
}

# Filter keys that resolve to a current AssetClassification row instead of a
# native Asset column — the two governed dimensions among §4's five filter
# keys that ASSET_REGISTRY.md §8 actually stewards as an AssetClassification
# dimension (SECTOR is a real dimension too, but not one of the contract's
# five filter keys — adding it here would be inventing filter vocabulary
# the approved design does not authorize).
_CLASSIFICATION_FILTERS: Dict[str, ClassificationDimension] = {
    "asset_class": ClassificationDimension.ASSET_CLASS,
    "region": ClassificationDimension.REGION,
}

ALLOWED_FILTER_KEYS: FrozenSet[str] = frozenset(_NATIVE_COLUMN_FILTERS) | frozenset(_CLASSIFICATION_FILTERS)

# Whether the schema carries the WP1 descriptive-name evidence tier yet.
# Computed once at import time from the live Asset model — not a config
# flag someone can forget to flip, and automatically becomes True the
# moment WP1's migration lands, with no change needed here.
NAME_SEARCH_AVAILABLE: bool = hasattr(Asset, "name")


class CatalogSearchError(Exception):
    """Base class for catalog-search input-validation failures. Mapping to
    the §4/§13 HTTP error codes (400 QUERY_TOO_LONG, 400 EMPTY_QUERY, 400
    UNKNOWN_FILTER_DIMENSION, ...) is WP5/routers/asset_search.py's job —
    this module raises typed Python exceptions only, no HTTP layer here."""


class QueryTooLongError(CatalogSearchError):
    """Raw query exceeded 200 Unicode code points before normalization."""


class EmptyQueryError(CatalogSearchError):
    """Query normalized to the empty string."""


class UnknownFilterDimensionError(CatalogSearchError):
    """A filter key is outside the five stewarded contract dimensions."""


class InvalidFilterValueError(CatalogSearchError):
    """A filter value is missing, blank, or otherwise unusable."""


class ConflictingFiltersError(CatalogSearchError):
    """The same filter key was supplied twice with two different values."""


@dataclass(frozen=True)
class RegisteredCandidate:
    """Wire-shaped per §6's RegisteredCandidate — projects Registry-owned
    facts only; this module never sees, and cannot construct, a provider
    claim or a DiscoveryCandidate."""

    kind: str = field(default="REGISTERED", init=False)
    asset_id: int = 0
    canonical_symbol: str = ""
    display_symbol: Optional[str] = None
    asset_type: str = ""
    market: str = ""
    exchange: str = ""
    currency: str = ""
    classifications: Dict[str, str] = field(default_factory=dict)
    status: str = ""
    match_field: str = ""


@dataclass(frozen=True)
class CatalogSearchResult:
    """catalog_search.py's own return shape — §8 stage 4's
    `List[RegisteredCandidate]`, plus the one piece of staged-conformance
    metadata (§9, F4) a future caller (search_service.py, WP5) needs to
    build the "name search unavailable" warning. Never itself the public
    SearchResponse — that assembly belongs to WP5, not this module."""

    candidates: Tuple[RegisteredCandidate, ...]
    name_search_available: bool = NAME_SEARCH_AVAILABLE


def normalize_query(raw_query: str) -> str:
    """The exact five-step sequence from §4 (F11), applied nowhere else:
    1) reject raw input over 200 Unicode code points, 2) NFC-normalize,
    3) trim + collapse internal whitespace, 4) reject if now empty,
    5) the result is what every match function below is given."""
    if len(raw_query) > MAX_RAW_QUERY_CODEPOINTS:
        raise QueryTooLongError(f"query exceeds {MAX_RAW_QUERY_CODEPOINTS} code points")

    normalized = unicodedata.normalize("NFC", raw_query)
    normalized = re.sub(r"\s+", " ", normalized.strip())

    if not normalized:
        raise EmptyQueryError("query is empty after normalization")

    return normalized


def _fold(text: str) -> str:
    """NFC-normalize then casefold for comparison — correct for non-ASCII
    case differences on both SQLite and Postgres alike (see module
    docstring for why this is done in Python, not pushed into SQL)."""
    return unicodedata.normalize("NFC", text).casefold()


def validate_filters(filters: Sequence[Tuple[str, str]]) -> Dict[str, str]:
    """Validates classification_filters entries against the five keys §4
    authorizes. Accepts (key, value) pairs rather than a plain dict because
    a plain dict cannot represent the same key supplied twice with two
    different values — the concrete shape "conflicting filters" (a caller
    error, not a data question) actually takes at this layer, before it
    ever reaches a plain Dict[str, str]."""
    validated: Dict[str, str] = {}
    for key, value in filters:
        if key not in ALLOWED_FILTER_KEYS:
            raise UnknownFilterDimensionError(key)
        if value is None or not value.strip():
            raise InvalidFilterValueError(f"{key}={value!r}")
        if key in validated and validated[key] != value:
            raise ConflictingFiltersError(
                f"{key} supplied with conflicting values {validated[key]!r} and {value!r}"
            )
        validated[key] = value
    return validated


def _filtered_asset_ids(db: Session, filters: Mapping[str, str]) -> Optional[set]:
    """The set of asset_ids satisfying every supplied filter (AND
    semantics), or None if no filters were supplied — None means "no
    filter-based restriction," never "matches nothing." Every key here is
    already validated against ALLOWED_FILTER_KEYS by validate_filters —
    never a caller-supplied arbitrary dimension (§9)."""
    if not filters:
        return None

    filtered = db.query(Asset.id)
    for key, value in filters.items():
        if key in _NATIVE_COLUMN_FILTERS:
            filtered = filtered.filter(_NATIVE_COLUMN_FILTERS[key] == value)
        else:
            dimension = _CLASSIFICATION_FILTERS[key]
            filtered = filtered.filter(
                Asset.id.in_(
                    db.query(AssetClassification.asset_id).filter(
                        AssetClassification.dimension == dimension.value,
                        AssetClassification.value == value,
                        AssetClassification.is_current.is_(True),
                    )
                )
            )
    return {row[0] for row in filtered.all()}


def _exact_symbol_matches(assets: Sequence[Asset], folded_query: str) -> Dict[int, str]:
    """asset_id -> match_field for every asset whose canonical_symbol or
    display_symbol equals the query, case-insensitively (literal equality,
    not a pattern — no wildcard interpretation is possible here)."""
    matches: Dict[int, str] = {}
    for asset in assets:
        if asset.canonical_symbol is not None and _fold(asset.canonical_symbol) == folded_query:
            matches[asset.id] = "canonical_symbol"
        elif asset.display_symbol is not None and _fold(asset.display_symbol) == folded_query:
            matches[asset.id] = "display_symbol"
    return matches


def _exact_identifier_matches(db: Session, folded_query: str) -> Dict[int, str]:
    """asset_id -> "identifier:<TYPE>" for exact (case-insensitive)
    identifier-value matches. Current rows take precedence over historical
    ones for the same value, mirroring identity_resolver.resolve()'s own
    current-preempts-historical rule (§9) — a mental-model consistency,
    not a shared code path (search matching and identity adjudication are
    different operations run for different reasons)."""
    rows = db.query(AssetIdentifier.asset_id, AssetIdentifier.identifier_type, AssetIdentifier.value, AssetIdentifier.is_current).all()

    current = [row for row in rows if _fold(row[2]) == folded_query and row[3]]
    if current:
        return {asset_id: f"identifier:{identifier_type}" for asset_id, identifier_type, _, _ in current}

    historical = [row for row in rows if _fold(row[2]) == folded_query]
    return {asset_id: f"identifier:{identifier_type}" for asset_id, identifier_type, _, _ in historical}


def _project(asset: Asset, classifications: Sequence[AssetClassification], match_field: str) -> RegisteredCandidate:
    return RegisteredCandidate(
        asset_id=asset.id,
        canonical_symbol=asset.canonical_symbol,
        display_symbol=asset.display_symbol,
        asset_type=asset.asset_type,
        market=asset.market,
        exchange=asset.exchange,
        currency=asset.currency,
        classifications={row.dimension: row.value for row in classifications if row.asset_id == asset.id},
        status=asset.status,
        match_field=match_field,
    )


def search(
    db: Session,
    raw_query: str,
    *,
    filters: Sequence[Tuple[str, str]] = (),
    limit: int = DEFAULT_LIMIT,
) -> CatalogSearchResult:
    """Asset-Foundation-owned catalog search over `assets` +
    `asset_identifiers` + `asset_classifications` (§9). Symbol/identifier
    matching only — name matching stays absent until WP1 ships
    `AssetDescriptiveName` + `Asset.name` (F4); this is disclosed via
    `NAME_SEARCH_AVAILABLE`/`CatalogSearchResult.name_search_available`
    rather than silently approximated against a column that does not
    exist.

    Read-only: no `db.add`/`flush`/`commit` anywhere in this module. Never
    calls a provider adapter, `identity_resolver.resolve()`/`adjudicate()`,
    or any other Registry-mutating path."""
    normalized_query = normalize_query(raw_query)
    folded_query = _fold(normalized_query)
    validated_filters = validate_filters(filters)
    clamped_limit = max(MIN_LIMIT, min(limit, MAX_LIMIT))

    allowed_asset_ids = _filtered_asset_ids(db, validated_filters)
    all_assets = db.query(Asset).all()

    # Tier order, most-preferred first — the approved §12 tier set's
    # symbol/identifier subset only. Name prefix/substring are §12 tiers
    # 3/4, absent until WP1 ships and NAME_SEARCH_AVAILABLE becomes True.
    # No symbol-prefix tier exists here: §12's tier enumeration is closed
    # and does not authorize canonical/display-symbol prefix matching, so
    # a query that is only a prefix of a symbol matches nothing unless it
    # is also an exact current identifier value.
    tiers: List[Dict[int, str]] = [
        _exact_symbol_matches(all_assets, folded_query),
        _exact_identifier_matches(db, folded_query),
    ]

    assigned: Dict[int, Tuple[int, str]] = {}
    for tier_index, tier_matches in enumerate(tiers):
        for asset_id, match_field in tier_matches.items():
            if asset_id in assigned:
                continue  # already claimed by a stronger, earlier tier
            if allowed_asset_ids is not None and asset_id not in allowed_asset_ids:
                continue  # filters never surface a non-matching, unrelated asset
            assigned[asset_id] = (tier_index, match_field)

    assets_by_id = {asset.id: asset for asset in all_assets}
    current_classifications = (
        db.query(AssetClassification)
        .filter(AssetClassification.asset_id.in_(assigned.keys()), AssetClassification.is_current.is_(True))
        .all()
        if assigned
        else []
    )

    candidates = [
        _project(assets_by_id[asset_id], current_classifications, match_field)
        for asset_id, (_, match_field) in assigned.items()
    ]
    candidates.sort(key=lambda c: (assigned[c.asset_id][0], c.canonical_symbol, c.asset_id))

    return CatalogSearchResult(candidates=tuple(candidates[:clamped_limit]))
