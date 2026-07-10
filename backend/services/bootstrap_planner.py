"""Asset Registry — Registry Bootstrap Planner (Milestone M5.3).

Pure aggregation over an already-computed migration_planner.MigrationPlan
(M5.1, unmodified): no database access, no I/O, no resolver calls, no new
identity logic. Mirrors migration_report.py's compute-only pattern one
layer further — where MigrationSummary answers "what does the resolver
say," BootstrapPlan answers a different question layered on top of it:
"which of the resolver's UNKNOWN verdicts can be safely minted, and with
what proposed Asset fields?"

Only UNKNOWN claim shapes are ever bootstrap's concern
----------------------------------------------------------
RESOLVED shapes already have an asset. AMBIGUOUS and CONFLICT shapes
already carry a durable RegistryFinding recorded by identity_resolver.
resolve() itself, awaiting the pre-existing M2/M3 adjudication surface
(registry_service.resolve_finding) — Bootstrap adds no second workflow for
those. CANDIDATE is structurally unreachable from ledger evidence (see
migration_report.py's own module docstring: PROVIDER_SYMBOL is not a
"strong" identifier type) and is handled here only for completeness. Only
UNKNOWN — "nothing matches and nothing corroborates" — is what this
milestone was charged with turning into canonical Assets.

Every UNKNOWN shape lands in exactly one of three buckets:

  mintable            Has a currency and an unambiguous market/exchange
                       hint (symbol_market_convention.infer_market_exchange,
                       unmodified) and is not part of a duplicate cluster.
  duplicate_blocked    Belongs to a migration_report.PotentialDuplicateCluster
                       — reused verbatim from build_migration_report(plan),
                       not recomputed (ADR-004). Never auto-minted; see
                       services/registry_bootstrap.py's module docstring for
                       why this is a manual-review case, not a tie-break.
  quarantined          Has no currency, or no market/exchange convention
                       matches its raw_symbol. Never guessed (ASSET_REGISTRY.
                       md Section 4) — reported so an operator can extend the
                       convention deliberately or mint by hand.

canonical_symbol = shape.raw_symbol, never shape.canonical_symbol
----------------------------------------------------------------------
These are two different concepts that happen to share a name. shape.
canonical_symbol is inherited from CanonicalTransaction.canonical_symbol
(services/transaction_canonicalizer.py) — a ledger-layer, market-data-
routing alias: per ledger_evidence_builder.py's own docstring, it is "the
ledger recorded a transaction in raw_symbol, never in whatever canonical_
symbol's market-data routing happens to point at" — safe to bundle as a
*second* identifier only when listing_equivalence.same_listing() confirms
it is a pure spelling variant, and deliberately dropped when it denotes an
economic relationship instead (a DR pointing at its foreign underlying's
own ticker, ASSET_REGISTRY.md Section 5's non-substitution rule).
Asset.canonical_symbol is a Registry-layer identity decision: the one
symbol a minted Asset is permanently, irreversibly known by. Treating the
ledger-layer field's name as a hint for the Registry-layer field of the
same name would be a category error, not a values choice — matching two
concepts because they are spelled alike rather than because they mean the
same thing. shape.raw_symbol is the only field that answers the Registry's
actual question ("what was this Asset actually transacted as, verbatim"),
and is correct in both the spelling-variant and the DR case alike, since it
is always literally what the ledger recorded.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import FrozenSet, List, Tuple

from services import migration_report
from services.asset_domain import AssetClaim, AssetType
from services.migration_planner import ClaimShape, MigrationPlan
from services.migration_report import PotentialDuplicateCluster
from services.resolver_domain import ResolutionVerdict
from services.symbol_market_convention import infer_market_exchange

__all__ = [
    "MintCandidate",
    "QuarantinedShape",
    "BootstrapPlan",
    "build_bootstrap_plan",
]


@dataclass(frozen=True)
class MintCandidate:
    """One UNKNOWN claim shape judged safe to mint. proposed_claim carries
    the Asset fields Bootstrap can determine with certainty; identifiers
    are deliberately not precomputed here — services/registry_bootstrap.py
    rebuilds them via ledger_evidence_builder.build_claim() at execution
    time, the same pure re-derivation discipline services/migration_
    executor.py already established (ADR-004)."""

    shape: ClaimShape
    proposed_claim: AssetClaim
    transaction_ids: Tuple[int, ...]


@dataclass(frozen=True)
class QuarantinedShape:
    """An UNKNOWN claim shape Bootstrap declines to mint automatically,
    with the specific reason a human needs to resolve it."""

    shape: ClaimShape
    reason: str
    transaction_ids: Tuple[int, ...]


@dataclass(frozen=True)
class BootstrapPlan:
    """The planner's complete, immutable output. Pure: no database access,
    no side effects — calling build_bootstrap_plan() twice on the same
    MigrationPlan produces identical output."""

    mintable: Tuple[MintCandidate, ...]
    duplicate_blocked: Tuple[PotentialDuplicateCluster, ...]
    quarantined: Tuple[QuarantinedShape, ...]
    generated_at: datetime


def _shape_sort_key(shape: ClaimShape) -> Tuple[str, str, str]:
    return (shape.raw_symbol, shape.canonical_symbol or "", shape.currency or "")


def _duplicate_blocked_shapes(clusters: Tuple[PotentialDuplicateCluster, ...]) -> FrozenSet[ClaimShape]:
    blocked: set = set()
    for cluster in clusters:
        blocked.update(cluster.claim_shapes)
    return frozenset(blocked)


def build_bootstrap_plan(plan: MigrationPlan) -> BootstrapPlan:
    """Classifies every UNKNOWN claim shape in `plan` into mintable /
    duplicate_blocked / quarantined. Duplicate detection reuses
    migration_report.build_migration_report(plan).potential_duplicate_
    clusters verbatim — the exact mechanism M5.1 already built for this
    exact purpose (ADR-004: reuse before create).
    """
    report = migration_report.build_migration_report(plan)
    clusters = report.potential_duplicate_clusters
    blocked_shapes = _duplicate_blocked_shapes(clusters)

    mintable: List[MintCandidate] = []
    quarantined: List[QuarantinedShape] = []

    for resolution in plan.resolutions:
        if resolution.result.verdict != ResolutionVerdict.UNKNOWN:
            continue

        shape = resolution.shape
        if shape in blocked_shapes:
            continue  # reported via duplicate_blocked, never mintable/quarantined

        if not shape.currency:
            quarantined.append(
                QuarantinedShape(
                    shape=shape,
                    reason="no currency recorded for this claim shape; cannot mint without a known currency",
                    transaction_ids=resolution.transaction_ids,
                )
            )
            continue

        hint = infer_market_exchange(shape.raw_symbol)
        if hint is None:
            quarantined.append(
                QuarantinedShape(
                    shape=shape,
                    reason=f"no known market/exchange convention for raw_symbol={shape.raw_symbol!r}",
                    transaction_ids=resolution.transaction_ids,
                )
            )
            continue

        proposed_claim = AssetClaim(
            canonical_symbol=shape.raw_symbol,
            asset_type=AssetType.EQUITY,
            market=hint.market,
            exchange=hint.exchange,
            currency=shape.currency,
        )
        mintable.append(
            MintCandidate(shape=shape, proposed_claim=proposed_claim, transaction_ids=resolution.transaction_ids)
        )

    return BootstrapPlan(
        mintable=tuple(sorted(mintable, key=lambda c: _shape_sort_key(c.shape))),
        duplicate_blocked=clusters,
        quarantined=tuple(sorted(quarantined, key=lambda q: _shape_sort_key(q.shape))),
        generated_at=datetime.now(timezone.utc),
    )
