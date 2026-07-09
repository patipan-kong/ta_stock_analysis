"""Asset Registry — Migration Report (Milestone M5.1).

Pure aggregation over a migration_planner.MigrationPlan: no database access,
no I/O, no resolver calls. Mirrors the compute/render split
identity_resolver.py already models (resolve() returns structured data;
_format_finding_detail is one rendering of it) — this module produces the
structured report; backend/manage.py owns turning it into printed text, the
same way it already owns _print_ledger_report for validate_ledger.

Two derived statistics deserve a note, since neither is a resolver concept
on its own — both are read directly off ResolutionResult data the resolver
already computed, not new heuristics, and deliberately avoid any string-
similarity/fuzzy matching (ASSET_REGISTRY.md Section 4: never a silent
guess):

  potential duplicates
      Within the UNKNOWN set, claim shapes that share a canonical_symbol
      but differ in raw_symbol. Two raw spellings routing to the same
      yfinance ticker without being bundled by listing_equivalence.same_
      listing() (e.g. because is_dr() vetoed it) are exactly the residue
      that veto produces — worth a human's attention before two separate
      assets get minted for what may be one instrument.

  potential merge candidates
      Every pairwise combination of candidate asset_ids surfaced by a
      CONFLICT verdict. A CONFLICT *is* two-or-more existing assets each
      currently, authoritatively claiming overlapping evidence — the
      candidates the resolver already scored are the merge candidates;
      nothing new is computed to find them.

CANDIDATE is included in the verdict taxonomy for completeness but is
structurally unreachable from ledger-only evidence: ledger_evidence_builder
only ever emits PROVIDER_SYMBOL identifiers, and PROVIDER_SYMBOL is not in
resolver_domain.DEFAULT_POLICY.strong_identifier_types (only ISIN/CUSIP/
SEDOL/FIGI are). A ledger claim matching nothing therefore always lands
UNKNOWN, never CANDIDATE — so "Assets created (expected)" is reported from
the UNKNOWN count, with that limitation stated explicitly in Statistics.
caveats rather than silently producing a number that looks more certain
than the evidence supports.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from itertools import combinations
from typing import Dict, List, Optional, Tuple

from services.asset_domain import AssetId
from services.migration_planner import ClaimShape, ClaimShapeResolution, MigrationPlan
from services.resolver_domain import ResolutionVerdict

__all__ = [
    "VerdictBreakdown",
    "Statistics",
    "AmbiguityReport",
    "ConflictReport",
    "PotentialMergeCandidate",
    "PotentialDuplicateCluster",
    "CoverageRow",
    "CoverageReport",
    "MigrationSummary",
    "build_migration_report",
]

# Mirrors ledger_evidence_builder._SOURCE (private to that module, not
# imported here — this is the one evidence source the planner's claims can
# carry today; the field exists in CoverageReport so a future milestone
# adding Provider Observation evidence has somewhere to report a second
# value without a report-shape change).
_LEDGER_EVIDENCE_SOURCE = "ledger:historical"

_VERDICT_ATTR = {
    ResolutionVerdict.RESOLVED: "resolved",
    ResolutionVerdict.CANDIDATE: "candidate",
    ResolutionVerdict.AMBIGUOUS: "ambiguous",
    ResolutionVerdict.CONFLICT: "conflict",
    ResolutionVerdict.UNKNOWN: "unknown",
}


@dataclass(frozen=True)
class VerdictBreakdown:
    """A count of the resolver's five verdicts, at either transaction or
    claim-shape granularity — Statistics reports both, since the required
    output asks for transaction-level totals but "manual adjudications
    required" and "assets created (expected)" are properties of distinct
    claim shapes, not of transaction counts."""

    resolved: int = 0
    candidate: int = 0
    ambiguous: int = 0
    conflict: int = 0
    unknown: int = 0

    @property
    def total(self) -> int:
        return self.resolved + self.candidate + self.ambiguous + self.conflict + self.unknown


def _tally(resolutions: Tuple[ClaimShapeResolution, ...], *, weight_by_transactions: bool) -> VerdictBreakdown:
    counts: Dict[str, int] = defaultdict(int)
    for res in resolutions:
        attr = _VERDICT_ATTR[res.result.verdict]
        counts[attr] += len(res.transaction_ids) if weight_by_transactions else 1
    return VerdictBreakdown(**counts)


@dataclass(frozen=True)
class Statistics:
    """The required minimum output set (ASSET_REGISTRY_IMPLEMENTATION_PLAN.md
    M5.1), plus the per-claim-shape breakdown the transaction-level counts
    alone can't express."""

    total_transactions: int
    cash_only_transactions: int
    identity_bearing_transactions: int
    transaction_verdicts: VerdictBreakdown
    claim_shape_verdicts: VerdictBreakdown
    resolution_pct: float
    decisive_pct: float
    assets_created_expected: int
    assets_reused: int
    manual_adjudications_required: int
    potential_duplicates: int
    potential_merge_candidates: int
    caveats: Tuple[str, ...]


@dataclass(frozen=True)
class AmbiguityReport:
    """One row per AMBIGUOUS claim shape — every ClaimShapeResolution here
    carries its full ResolutionResult (candidates, contributions,
    corroborations), so nothing further needs to be re-derived to explain
    why a shape landed here."""

    entries: Tuple[ClaimShapeResolution, ...]


@dataclass(frozen=True)
class PotentialMergeCandidate:
    """One pair of existing assets that co-occurred as candidates in a
    CONFLICT verdict — read directly off ResolutionResult.candidates, not a
    new heuristic (see module docstring)."""

    asset_ids: Tuple[AssetId, AssetId]
    claim_shapes: Tuple[ClaimShape, ...]
    transaction_ids: Tuple[int, ...]


@dataclass(frozen=True)
class ConflictReport:
    """One row per CONFLICT claim shape, plus the merge-candidate pairs
    derived from them."""

    entries: Tuple[ClaimShapeResolution, ...]
    potential_merge_candidates: Tuple[PotentialMergeCandidate, ...]


@dataclass(frozen=True)
class PotentialDuplicateCluster:
    """Two or more UNKNOWN claim shapes sharing a canonical_symbol — see
    module docstring for why this, and not string similarity, is the
    detection rule."""

    canonical_symbol: str
    raw_symbols: Tuple[str, ...]
    claim_shapes: Tuple[ClaimShape, ...]
    transaction_ids: Tuple[int, ...]


@dataclass(frozen=True)
class CoverageRow:
    """Per-symbol coverage: one claim shape's verdict, transaction/
    portfolio footprint, and — for RESOLVED shapes only — the resolved
    asset's true market/exchange (never guessed for anything else)."""

    shape: ClaimShape
    verdict: ResolutionVerdict
    transaction_count: int
    portfolio_ids: Tuple[int, ...]
    evidence_source: str
    resolved_market: Optional[str]
    resolved_exchange: Optional[str]


@dataclass(frozen=True)
class CoverageReport:
    """Per-symbol, per-provider, per-market/currency statistics
    (ASSET_REGISTRY_IMPLEMENTATION_PLAN.md M5.1: "to help estimate the
    migration workload"). by_provider is a single bucket today
    ("ledger:historical") — the planner consumes only Ledger Evidence
    Builders, never live Provider Adapters, per the M5.1 Architecture
    Requirement, so a second provider bucket cannot appear until a future
    milestone wires provider evidence into this same report shape."""

    rows: Tuple[CoverageRow, ...]
    by_currency: Tuple[Tuple[str, VerdictBreakdown], ...]
    by_provider: Tuple[Tuple[str, VerdictBreakdown], ...]


@dataclass(frozen=True)
class MigrationSummary:
    """The top-level, umbrella report — everything a human needs to answer
    "if we migrate today, what exactly would happen?" in one object."""

    statistics: Statistics
    ambiguity_report: AmbiguityReport
    conflict_report: ConflictReport
    coverage_report: CoverageReport
    potential_duplicate_clusters: Tuple[PotentialDuplicateCluster, ...]
    portfolios_scanned: Tuple[int, ...]
    generated_at: datetime


_CANDIDATE_UNREACHABLE_CAVEAT = (
    "Ledger evidence carries only PROVIDER_SYMBOL identifiers, which are not a "
    "'strong' identifier type (see resolver_domain.DEFAULT_POLICY). The CANDIDATE "
    "verdict is therefore unreachable from ledger evidence alone — every genuinely "
    "new symbol lands UNKNOWN instead. 'Assets created (expected)' is the UNKNOWN "
    "claim-shape count, reported as an estimate under today's evidence, not a "
    "resolver-guaranteed figure."
)
_PROVIDER_COVERAGE_CAVEAT = (
    "Per-provider statistics have a single bucket today ('ledger:historical'): the "
    "planner consumes only Ledger Evidence Builders, never live Provider Adapters "
    "(M5.1 Architecture Requirement). This is expected, not a bug in this report."
)
_MARKET_COVERAGE_CAVEAT = (
    "Transaction rows carry no market/exchange columns, only currency. Per-market "
    "coverage uses currency as a proxy for unresolved claim shapes; RESOLVED shapes "
    "use the true market/exchange read from the resolved asset instead."
)


def _potential_merge_candidates(
    conflict_resolutions: Tuple[ClaimShapeResolution, ...],
) -> Tuple[PotentialMergeCandidate, ...]:
    grouped: Dict[Tuple[AssetId, AssetId], Dict[str, list]] = {}
    for res in conflict_resolutions:
        asset_ids = [c.asset_id for c in res.result.candidates]
        for a, b in combinations(asset_ids, 2):
            key = tuple(sorted((a, b), key=int))
            bucket = grouped.setdefault(key, {"shapes": [], "tx_ids": []})
            bucket["shapes"].append(res.shape)
            bucket["tx_ids"].extend(res.transaction_ids)

    return tuple(
        PotentialMergeCandidate(
            asset_ids=key,
            claim_shapes=tuple(bucket["shapes"]),
            transaction_ids=tuple(sorted(set(bucket["tx_ids"]))),
        )
        for key, bucket in grouped.items()
    )


def _potential_duplicate_clusters(
    unknown_resolutions: Tuple[ClaimShapeResolution, ...],
) -> Tuple[PotentialDuplicateCluster, ...]:
    grouped: Dict[str, List[ClaimShapeResolution]] = defaultdict(list)
    for res in unknown_resolutions:
        if res.shape.canonical_symbol:
            grouped[res.shape.canonical_symbol].append(res)

    clusters = []
    for canonical_symbol, group in grouped.items():
        raw_symbols = sorted({res.shape.raw_symbol for res in group})
        if len(raw_symbols) < 2:
            continue
        tx_ids = sorted({tid for res in group for tid in res.transaction_ids})
        clusters.append(
            PotentialDuplicateCluster(
                canonical_symbol=canonical_symbol,
                raw_symbols=tuple(raw_symbols),
                claim_shapes=tuple(res.shape for res in group),
                transaction_ids=tuple(tx_ids),
            )
        )
    return tuple(clusters)


def _by_key(resolutions: Tuple[ClaimShapeResolution, ...], key_fn) -> Tuple[Tuple[str, VerdictBreakdown], ...]:
    grouped: Dict[str, List[ClaimShapeResolution]] = defaultdict(list)
    for res in resolutions:
        grouped[key_fn(res)].append(res)
    return tuple(
        (key, _tally(tuple(group), weight_by_transactions=True))
        for key, group in sorted(grouped.items())
    )


def build_migration_report(plan: MigrationPlan) -> MigrationSummary:
    """Aggregates a MigrationPlan into the full M5.1 report set. Pure: no
    database access, no side effects — calling this twice on the same plan
    produces identical output."""
    resolutions = plan.resolutions

    ambiguous = tuple(r for r in resolutions if r.result.verdict == ResolutionVerdict.AMBIGUOUS)
    conflicts = tuple(r for r in resolutions if r.result.verdict == ResolutionVerdict.CONFLICT)
    unknowns = tuple(r for r in resolutions if r.result.verdict == ResolutionVerdict.UNKNOWN)
    resolved = tuple(r for r in resolutions if r.result.verdict == ResolutionVerdict.RESOLVED)

    transaction_verdicts = _tally(resolutions, weight_by_transactions=True)
    claim_shape_verdicts = _tally(resolutions, weight_by_transactions=False)

    identity_bearing = transaction_verdicts.total
    resolution_pct = (transaction_verdicts.resolved / identity_bearing * 100.0) if identity_bearing else 0.0
    decisive_pct = (
        (transaction_verdicts.resolved + transaction_verdicts.candidate) / identity_bearing * 100.0
        if identity_bearing
        else 0.0
    )

    merge_candidates = _potential_merge_candidates(conflicts)
    duplicate_clusters = _potential_duplicate_clusters(unknowns)
    assets_reused = len({r.result.resolved_asset_id for r in resolved if r.result.resolved_asset_id is not None})

    statistics = Statistics(
        total_transactions=plan.total_transactions,
        cash_only_transactions=len(plan.cash_only.transaction_ids),
        identity_bearing_transactions=identity_bearing,
        transaction_verdicts=transaction_verdicts,
        claim_shape_verdicts=claim_shape_verdicts,
        resolution_pct=resolution_pct,
        decisive_pct=decisive_pct,
        assets_created_expected=claim_shape_verdicts.unknown,
        assets_reused=assets_reused,
        manual_adjudications_required=claim_shape_verdicts.ambiguous + claim_shape_verdicts.conflict,
        potential_duplicates=len(duplicate_clusters),
        potential_merge_candidates=len(merge_candidates),
        caveats=(_CANDIDATE_UNREACHABLE_CAVEAT, _PROVIDER_COVERAGE_CAVEAT, _MARKET_COVERAGE_CAVEAT),
    )

    coverage_rows = tuple(
        CoverageRow(
            shape=res.shape,
            verdict=res.result.verdict,
            transaction_count=len(res.transaction_ids),
            portfolio_ids=res.portfolio_ids,
            evidence_source=_LEDGER_EVIDENCE_SOURCE,
            resolved_market=res.resolved_market,
            resolved_exchange=res.resolved_exchange,
        )
        for res in resolutions
    )
    coverage_report = CoverageReport(
        rows=coverage_rows,
        by_currency=_by_key(resolutions, lambda r: r.shape.currency or "(unspecified)"),
        by_provider=_by_key(resolutions, lambda r: _LEDGER_EVIDENCE_SOURCE),
    )

    return MigrationSummary(
        statistics=statistics,
        ambiguity_report=AmbiguityReport(entries=ambiguous),
        conflict_report=ConflictReport(entries=conflicts, potential_merge_candidates=merge_candidates),
        coverage_report=coverage_report,
        potential_duplicate_clusters=duplicate_clusters,
        portfolios_scanned=plan.portfolios_scanned,
        generated_at=plan.generated_at,
    )
