"""Market Intelligence — Registry Merge (Milestone M37.2, WP3).

Implements docs/implementation/M37_1_Universal_Asset_Search_Technical_Design.md
Section 3's `merge.py` row (De-dup: consults
`identity_resolver.resolve(db, claim, record_finding=False)` per discovery
result; folds recognized matches into registered candidates) and §8 stage 7
(Registry-authoritative deduplication).

This module reconciles discovery-shaped candidates against the Registry
using the *existing* canonical identity resolver in non-recording (preview)
mode. It never becomes a second identity resolver: no matching, scoring, or
classification logic is reimplemented here — every identity question is
answered by calling `identity_resolver.resolve()` and reading its typed
`ResolutionResult`, never by inspecting raw Registry rows itself.

Read-only, permanently: every `resolve()` call is made with
`record_finding=False` (never the default `True`), so an AMBIGUOUS/CONFLICT
discovery candidate previewed here creates zero `RegistryFinding` rows —
finding creation stays exclusively `identity_resolver.resolve()`'s own
concern when called by its *other* (recording) callers, never something
this module orchestrates. This module never calls `adjudicate()`, never
mints an asset, never attaches an identifier, never records a
classification. It never imports a provider adapter and never imports
`ranking.py` — per §8's stage table, ranking (stage 8) is a separate stage
from merge (stage 7), owned by `ranking.py` and invoked by
`search_service.py` (WP5, not yet built), not by this module. `merge()`
returns its reconciled list unranked, exactly as §8 specifies.

Discovery-shaped input is consumed structurally (duck-typed): this module
does not define, import, or require a `DiscoveryCandidate` base class.
WP6 remains the future canonical producer and owner of that concrete type
(§3); until it exists, callers (today, tests) supply any object exposing
the §6 field shape (`reported_identifiers`, `provider_name`, `market`,
`currency`, `match_field`, ...).
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence

from sqlalchemy.orm import Session

from services import registry_service
from services.asset_domain import AssetId, IdentifierRecord, IdentifierType
from services.asset_search.catalog_search import RegisteredCandidate
from services.identity_resolver import resolve
from services.resolver_domain import ResolutionClaim, ResolutionResult, ResolutionVerdict

__all__ = [
    "RegistryConsistencyError",
    "merge",
]

# Duck-typed, same rationale as ranking.py's `Candidate = Any`: this module
# ranks nothing and defines no producer contract, so it type-hints its
# discovery-shaped input as `Any` rather than importing/requiring a
# concrete `DiscoveryCandidate` class that belongs to WP6.
DiscoveryLike = Any


class RegistryConsistencyError(Exception):
    """Raised when `identity_resolver.resolve()` reports RESOLVED against
    an `asset_id` that no longer projects to a real `Asset` row. This is an
    internal Registry-consistency failure — not "unresolved identity"
    (that is UNKNOWN/AMBIGUOUS/CONFLICT) and not "malformed candidate"
    (that is insufficient-evidence, handled by preserving as discovery,
    never by raising). It must never be silently downgraded to a discovery
    result: doing so would hide a real data-integrity problem behind an
    ordinary "no match" outcome. This is an internal exception, not a
    public API error shape — mapping it to an HTTP response is WP5's
    concern, not this module's."""


def _build_claim(discovery: DiscoveryLike) -> Optional[ResolutionClaim]:
    """Builds a `ResolutionClaim` using only fields §6 authorizes on
    `DiscoveryCandidate` (`reported_identifiers`, `market`, `currency`).
    Any `reported_identifiers` key that is not one of the closed
    `IdentifierType` values, or whose value is blank, is dropped rather
    than fabricated into a claim the resolver was never given real
    evidence for. Returns `None` — never a claim built from partial/guessed
    evidence — when zero usable identifiers survive that filtering."""
    identifiers = []
    for raw_type, value in (discovery.reported_identifiers or {}).items():
        if not value:
            continue
        try:
            identifier_type = IdentifierType(raw_type)
        except ValueError:
            continue  # not one of the closed, approved identifier schemes
        identifiers.append(
            IdentifierRecord(
                identifier_type=identifier_type,
                value=value,
                source=f"discovery:{discovery.provider_name or 'unknown'}",
            )
        )

    if not identifiers:
        return None

    return ResolutionClaim(
        identifiers=tuple(identifiers),
        market=getattr(discovery, "market", None),
        exchange=None,  # §6: DiscoveryCandidate carries no exchange field
        currency=getattr(discovery, "currency", None),
    )


def _primary_match_field(result: ResolutionResult) -> str:
    """Labels a merge-projected `RegisteredCandidate` with the identifier
    type that actually carried the winning evidence — read straight from
    the resolver's own structured `ResolutionCandidate.contributions`
    (never re-derived by re-inspecting raw rows), mirroring
    `catalog_search.py`'s existing "identifier:<TYPE>" vocabulary (§6) so
    WP4's ranking tiers recognize it without new tier logic. Falls back to
    a generic label if the winning candidate is not present in
    `result.candidates` — an internal-consistency edge case the caller
    (`merge()`) has already turned into a `RegistryConsistencyError` before
    this function is ever reached for that case; this fallback only
    protects against a *malformed but non-empty* result shape."""
    winner = next((c for c in result.candidates if c.asset_id == result.resolved_asset_id), None)
    if winner is None or not winner.contributions:
        return "identifier"
    best_contribution = max(winner.contributions, key=lambda c: c.applied_weight)
    return f"identifier:{best_contribution.identifier_type.value}"


def _project_registered(db: Session, asset_id: int, match_field: str) -> RegisteredCandidate:
    """Projects a `RegisteredCandidate` from Registry-owned facts only,
    via the same read helpers `catalog_search.py` (WP2) uses
    (`registry_service.get_asset`/`get_classifications`) — never from the
    resolving `DiscoveryCandidate`'s `reported_*` fields, which are
    unverified provider evidence, not Registry fact (§6). The caller
    (`merge()`) already verified the asset exists before calling this."""
    asset = registry_service.get_asset(db, AssetId(asset_id))
    classifications = registry_service.get_classifications(db, AssetId(asset_id), current_only=True)
    return RegisteredCandidate(
        asset_id=asset.id,
        canonical_symbol=asset.canonical_symbol,
        display_symbol=asset.display_symbol,
        asset_type=asset.asset_type,
        market=asset.market,
        exchange=asset.exchange,
        currency=asset.currency,
        classifications={row.dimension: row.value for row in classifications},
        status=asset.status,
        match_field=match_field,
    )


def merge(
    db: Session,
    registered_candidates: Sequence[RegisteredCandidate],
    discovery_candidates: Sequence[DiscoveryLike],
    *,
    on_resolve_error: Optional[Callable[[DiscoveryLike, Exception], None]] = None,
) -> List[Any]:
    """Reconciles discovery-shaped candidates against the Registry (§8
    stage 7). Every discovery candidate that yields a buildable claim is
    checked via `identity_resolver.resolve(db, claim, record_finding=False)`
    — never a copy of its matching/scoring logic. Verdict handling:

    - RESOLVED: collapsed onto the real registered asset. Reuses an
      existing `RegisteredCandidate` for that `asset_id` already present in
      `registered_candidates` when one exists; otherwise projects one fresh
      from Registry facts. Multiple discovery candidates resolving to the
      same asset still produce exactly one registered result. The original
      discovery candidate is dropped — never kept alongside its now-
      resolved registered counterpart (§8 stage 7: "never surface both").
    - AMBIGUOUS / CONFLICT / CANDIDATE / UNKNOWN: the discovery candidate
      is preserved as-is, unresolved. (`CANDIDATE` is not itself called out
      by §12's four-verdict merge narrative, but it carries
      `resolved_asset_id=None` exactly like AMBIGUOUS/CONFLICT/UNKNOWN, so
      the same "collapse only on RESOLVED" branch already covers it
      correctly without a redundant special case.)
    - No buildable claim (insufficient/malformed identity evidence): the
      resolver is never called; the candidate is preserved as discovery.

    Returns the merged list unranked — `registered_candidates` in their
    given order, then newly-projected registered candidates in resolution
    order, then preserved discovery candidates in their given order. §8
    stage 8 (ranking) is a separate stage owned by `ranking.py`, invoked by
    `search_service.py`; this function never calls `rank()`.

    Never mutates `registered_candidates`, `discovery_candidates`, or any
    candidate object. Deterministic: identical input always produces
    identical output, since no step depends on anything but the input data
    and the Registry's current (already-consistent, resolve()-mediated)
    state."""
    registered_by_asset_id: Dict[int, RegisteredCandidate] = {}
    merged_registered: List[RegisteredCandidate] = []
    for candidate in registered_candidates:
        merged_registered.append(candidate)
        registered_by_asset_id.setdefault(candidate.asset_id, candidate)

    preserved_discovery: List[Any] = []
    for discovery in discovery_candidates:
        claim = _build_claim(discovery)
        if claim is None:
            preserved_discovery.append(discovery)
            continue

        try:
            result = resolve(db, claim, record_finding=False)
        except Exception as exc:
            # F3: a failed Registry check is not proof that the provider
            # observation is unregistered.  Preserve the discovery candidate
            # and let orchestration disclose the unavailable merge check.
            preserved_discovery.append(discovery)
            if on_resolve_error is not None:
                on_resolve_error(discovery, exc)
            continue

        if result.verdict == ResolutionVerdict.RESOLVED and result.resolved_asset_id is not None:
            asset_id = int(result.resolved_asset_id)
            if asset_id not in registered_by_asset_id:
                if registry_service.get_asset(db, AssetId(asset_id)) is None:
                    raise RegistryConsistencyError(
                        f"resolve() reported RESOLVED asset_id={asset_id} but no such Asset row exists"
                    )
                projected = _project_registered(db, asset_id, _primary_match_field(result))
                registered_by_asset_id[asset_id] = projected
                merged_registered.append(projected)
            # else: an existing (or already-projected-this-call) registered
            # candidate already represents this asset — the discovery
            # candidate is dropped, never kept alongside it.
            continue

        preserved_discovery.append(discovery)

    return merged_registered + preserved_discovery
