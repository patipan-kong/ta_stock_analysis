"""Read-only M31.5 execution Registry coverage and readiness reporting.

Legacy configuration is admitted here only as *review evidence*.  It never
establishes asset type, DR identity, tradability, or execution eligibility.
All authoritative columns in the report are derived from Registry facts and
Registry rows.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, Iterable, Mapping, Optional, Sequence, Tuple

from sqlalchemy.orm import Session

from models.asset import Asset, AssetIdentifier, AssetRelationship
from models.database import OptimizerHistory, Portfolio, PortfolioItem, Transaction, Watchlist
from services import registry_lookup
from services.asset_domain import AssetStatus, IdentifierType
from services.execution_eligibility import (
    ExecutionEligibilityOutcome,
    evaluate_execution_eligibility,
)
from services.execution_eligibility_shadow import (
    resolve_execution_eligibility_shadow_facts,
)
from services.execution_instrument_facts import (
    ExecutionInstrumentFacts,
    ExecutionInstrumentForm,
    ExecutionResolutionOutcome,
    ExecutionRole,
)

__all__ = [
    "ExecutionPreflightOutcome",
    "ExecutionPreflightRow",
    "ExecutionPreflightCoverage",
    "NativeAssetIdProposal",
    "NativeAssetIdReadiness",
    "ExecutionRegistryPreflightReport",
    "configured_execution_review_populations",
    "build_execution_registry_preflight",
]


_ACTIONABLE = frozenset({"BUY", "SELL", "ACCUMULATE", "REDUCE"})
_EXECUTABLE_TRANSACTIONS = frozenset({"BUY", "SELL", "INITIAL_POSITION"})


class ExecutionPreflightOutcome(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    UNKNOWN_IDENTITY = "UNKNOWN_IDENTITY"
    AMBIGUOUS_IDENTITY = "AMBIGUOUS_IDENTITY"
    NOT_TRADABLE = "NOT_TRADABLE"
    REFERENCE_ONLY = "REFERENCE_ONLY"
    REGISTRY_FAILURE = "REGISTRY_FAILURE"
    INCOMPLETE_METADATA = "INCOMPLETE_METADATA"


@dataclass(frozen=True)
class ExecutionPreflightRow:
    population: str
    requested_symbol: str
    evidence: Tuple[str, ...]
    outcome: ExecutionPreflightOutcome
    supported_executable: bool
    canonical_symbol: Optional[str]
    asset_id: Optional[int]
    asset_type: Optional[str]
    instrument_form: str
    execution_role: str
    relationship_evidence: Tuple[str, ...]
    identifier_evidence: Tuple[str, ...]
    classification_provenance: Tuple[str, ...]
    missing_requirements: Tuple[str, ...]
    recommended_remediation_category: str

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["outcome"] = self.outcome.value
        return payload


@dataclass(frozen=True)
class ExecutionPreflightCoverage:
    population: str
    total: int
    by_outcome: Mapping[str, int]
    supported_executable: int

    @property
    def coverage_pct(self) -> float:
        return round(self.supported_executable / self.total * 100, 1) if self.total else 100.0

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["coverage_pct"] = self.coverage_pct
        return payload


@dataclass(frozen=True)
class NativeAssetIdProposal:
    table: str
    row_id: int
    requested_symbol: str
    proposed_asset_id: int
    canonical_symbol: Optional[str]


@dataclass(frozen=True)
class NativeAssetIdReadiness:
    table: str
    total_rows: int
    materialized_rows: int
    exactly_resolvable_rows: int
    missing_but_resolvable: int
    unresolved_rows: int
    ambiguous_rows: int
    registry_failure_rows: int
    conflicting_existing_rows: int
    dry_run_proposals: Tuple[NativeAssetIdProposal, ...]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ExecutionRegistryPreflightReport:
    generated_at: datetime
    read_only: bool
    rows: Tuple[ExecutionPreflightRow, ...]
    coverage: Tuple[ExecutionPreflightCoverage, ...]
    native_asset_id_readiness: Tuple[NativeAssetIdReadiness, ...]
    limitations: Tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "generated_at": self.generated_at.isoformat(),
            "read_only": self.read_only,
            "coverage": [item.to_dict() for item in self.coverage],
            "rows": [item.to_dict() for item in self.rows],
            "native_asset_id_readiness": [
                item.to_dict() for item in self.native_asset_id_readiness
            ],
            "limitations": list(self.limitations),
        }


def configured_execution_review_populations() -> Mapping[str, Mapping[str, str]]:
    """Return existing legacy/config symbols as non-authoritative review input.

    Imports remain local to keep these compatibility sources out of the
    Registry-backed execution runtime.  The values explain provenance only;
    callers must never convert them into Registry facts automatically.
    """

    from services.benchmark_service import DEFAULT_BENCHMARKS
    from services.optimizer import execution_penalty_compat
    from services.symbol_resolver import YFINANCE_SYMBOL_MAP

    etfs = {
        symbol: "legacy execution ETF allow-list; review evidence only"
        for symbol in execution_penalty_compat.legacy_etf_review_symbols()
    }
    dr_aliases = {
        symbol: (
            "configured yfinance alias to "
            f"{provider_symbol}; underlying/DR authority not established"
        )
        for symbol, provider_symbol in sorted(YFINANCE_SYMBOL_MAP.items())
    }
    references = {
        symbol: "default benchmark configuration; reference role requires explicit review"
        for symbol in DEFAULT_BENCHMARKS
        if symbol not in etfs
    }
    return {
        "configured_etf_review": etfs,
        "configured_dr_alias_review": dr_aliases,
        "configured_reference_review": references,
    }


def _add_population_symbol(
    populations: Dict[str, Dict[str, list[str]]],
    population: str,
    symbol: object,
    evidence: str,
) -> None:
    rendered = str(symbol or "").strip()
    if not rendered:
        return
    populations.setdefault(population, {}).setdefault(rendered, []).append(evidence)


def _collect_operational_populations(
    db: Session,
    workspace_id: Optional[int],
) -> Dict[str, Dict[str, list[str]]]:
    populations: Dict[str, Dict[str, list[str]]] = {}

    holdings_query = db.query(PortfolioItem)
    watchlist_query = db.query(Watchlist)
    histories_query = db.query(OptimizerHistory)
    transaction_query = db.query(Transaction).filter(
        Transaction.transaction_type.in_(_EXECUTABLE_TRANSACTIONS)
    )
    portfolios_query = db.query(Portfolio)
    if workspace_id is not None:
        holdings_query = holdings_query.filter(PortfolioItem.workspace_id == workspace_id)
        watchlist_query = watchlist_query.filter(Watchlist.workspace_id == workspace_id)
        histories_query = histories_query.filter(OptimizerHistory.workspace_id == workspace_id)
        transaction_query = transaction_query.filter(Transaction.workspace_id == workspace_id)
        portfolios_query = portfolios_query.filter(Portfolio.workspace_id == workspace_id)

    holdings = holdings_query.all()
    watchlist = watchlist_query.all()
    for row in holdings:
        _add_population_symbol(populations, "current_holdings", row.symbol, f"portfolio_item_id={row.id}")
    for row in watchlist:
        _add_population_symbol(populations, "workspace_watchlist", row.symbol, f"watchlist_id={row.id}")

    watchlist_by_workspace: Dict[int, set[str]] = {}
    for row in watchlist:
        watchlist_by_workspace.setdefault(row.workspace_id, set()).add(row.symbol)
    holdings_by_portfolio: Dict[int, set[str]] = {}
    for row in holdings:
        holdings_by_portfolio.setdefault(row.portfolio_id, set()).add(row.symbol)
    for portfolio in portfolios_query.all():
        population = f"optimizer_reachable:portfolio_id={portfolio.id}"
        symbols = holdings_by_portfolio.get(portfolio.id, set()) | watchlist_by_workspace.get(
            portfolio.workspace_id, set()
        )
        for symbol in symbols:
            _add_population_symbol(
                populations,
                population,
                symbol,
                "portfolio holdings union workspace watchlist",
            )

    latest_by_portfolio: Dict[int, OptimizerHistory] = {}
    for row in histories_query.order_by(
        OptimizerHistory.portfolio_id.asc(),
        OptimizerHistory.analyzed_at.desc(),
        OptimizerHistory.id.desc(),
    ).all():
        latest_by_portfolio.setdefault(row.portfolio_id, row)
    for portfolio_id, history in latest_by_portfolio.items():
        try:
            payload = json.loads(history.result_json or "{}")
        except (TypeError, ValueError):
            continue
        for allocation in payload.get("target_allocations") or ():
            if str(allocation.get("action", "")).upper() not in _ACTIONABLE:
                continue
            _add_population_symbol(
                populations,
                "latest_actionable_optimizer_allocations",
                allocation.get("symbol"),
                f"optimizer_history_id={history.id};portfolio_id={portfolio_id}",
            )

    for row in transaction_query.all():
        _add_population_symbol(
            populations,
            "historical_executable_transactions",
            row.symbol,
            f"transaction_id={row.id};type={row.transaction_type}",
        )

    for population, symbols in configured_execution_review_populations().items():
        for symbol, evidence in symbols.items():
            _add_population_symbol(populations, population, symbol, evidence)
    return populations


def _registry_evidence(
    db: Session,
    facts: ExecutionInstrumentFacts,
) -> Tuple[Optional[Asset], Tuple[str, ...], Tuple[str, ...]]:
    if facts.asset_id is None:
        return None, (), ()
    asset = db.query(Asset).filter(Asset.id == int(facts.asset_id)).one_or_none()
    identifiers = tuple(
        f"{row.identifier_type}:{row.value} (source={row.source})"
        for row in db.query(AssetIdentifier)
        .filter(
            AssetIdentifier.asset_id == int(facts.asset_id),
            AssetIdentifier.is_current.is_(True),
        )
        .order_by(AssetIdentifier.identifier_type, AssetIdentifier.value)
        .all()
    )
    relationships = tuple(
        f"{row.relationship_type}:{row.from_asset_id}->{row.to_asset_id}"
        for row in db.query(AssetRelationship)
        .filter(
            (AssetRelationship.from_asset_id == int(facts.asset_id))
            | (AssetRelationship.to_asset_id == int(facts.asset_id))
        )
        .order_by(
            AssetRelationship.relationship_type,
            AssetRelationship.from_asset_id,
            AssetRelationship.to_asset_id,
        )
        .all()
    )
    return asset, identifiers, relationships


def _preflight_outcome(
    facts: ExecutionInstrumentFacts,
    *,
    asset: Optional[Asset],
    identifiers: Sequence[str],
) -> ExecutionPreflightOutcome:
    eligibility = evaluate_execution_eligibility(facts)
    if eligibility.outcome == ExecutionEligibilityOutcome.REGISTRY_FAILURE:
        return ExecutionPreflightOutcome.REGISTRY_FAILURE
    if eligibility.outcome == ExecutionEligibilityOutcome.AMBIGUOUS_IDENTITY:
        return ExecutionPreflightOutcome.AMBIGUOUS_IDENTITY
    if eligibility.outcome == ExecutionEligibilityOutcome.REFERENCE_ONLY:
        return ExecutionPreflightOutcome.REFERENCE_ONLY
    if eligibility.outcome == ExecutionEligibilityOutcome.NOT_TRADABLE:
        return ExecutionPreflightOutcome.NOT_TRADABLE
    if facts.reason and facts.reason.startswith("incomplete Registry metadata"):
        return ExecutionPreflightOutcome.INCOMPLETE_METADATA
    if eligibility.outcome == ExecutionEligibilityOutcome.UNKNOWN_IDENTITY:
        return ExecutionPreflightOutcome.UNKNOWN_IDENTITY
    if (
        asset is None
        or asset.status != AssetStatus.ACTIVE.value
        or not identifiers
        or not any(item.startswith(f"{IdentifierType.PROVIDER_SYMBOL.value}:") for item in identifiers)
    ):
        return ExecutionPreflightOutcome.INCOMPLETE_METADATA
    return ExecutionPreflightOutcome.ELIGIBLE


def _expected_requirements(population: str, facts: ExecutionInstrumentFacts) -> list[str]:
    missing: list[str] = []
    if population == "configured_etf_review" and facts.instrument_form != ExecutionInstrumentForm.ETF:
        missing.append("explicit Registry Asset.asset_type=ETF evidence")
    if (
        population == "configured_dr_alias_review"
        and facts.instrument_form != ExecutionInstrumentForm.DEPOSITARY_RECEIPT
    ):
        missing.append("exactly one authoritative DEPOSITARY_RECEIPT_OF relationship")
    if population == "configured_reference_review" and not (
        facts.execution_role == ExecutionRole.REFERENCE
        and facts.resolution_status == ExecutionResolutionOutcome.NOT_TRADABLE
    ):
        missing.append("Registry OTHER + current ASSET_CLASS=INDEX + tradable=false evidence")
    return missing


def _build_row(
    db: Session,
    population: str,
    symbol: str,
    evidence: Sequence[str],
    facts: ExecutionInstrumentFacts,
) -> ExecutionPreflightRow:
    asset, identifiers, relationships = _registry_evidence(db, facts)
    outcome = _preflight_outcome(facts, asset=asset, identifiers=identifiers)
    missing = _expected_requirements(population, facts)
    if facts.reason and outcome != ExecutionPreflightOutcome.ELIGIBLE:
        missing.append(facts.reason)
    if facts.asset_id is not None:
        if asset is None:
            missing.append("Registry asset row")
        elif asset.status != AssetStatus.ACTIVE.value:
            missing.append("active Registry lifecycle status")
        if not identifiers:
            missing.append("current Registry identifier")
        elif not any(
            item.startswith(f"{IdentifierType.PROVIDER_SYMBOL.value}:")
            for item in identifiers
        ):
            missing.append("current PROVIDER_SYMBOL identifier")

    remediation = {
        ExecutionPreflightOutcome.ELIGIBLE: "NONE",
        ExecutionPreflightOutcome.AMBIGUOUS_IDENTITY: "ADJUDICATE_IDENTITY",
        ExecutionPreflightOutcome.NOT_TRADABLE: "REVIEW_TRADABILITY",
        ExecutionPreflightOutcome.REFERENCE_ONLY: "NONE_REFERENCE_EXPECTED",
        ExecutionPreflightOutcome.REGISTRY_FAILURE: "RESTORE_REGISTRY_INFRASTRUCTURE",
        ExecutionPreflightOutcome.INCOMPLETE_METADATA: "COMPLETE_REGISTRY_METADATA",
        ExecutionPreflightOutcome.UNKNOWN_IDENTITY: "REGISTER_OR_ATTACH_IDENTIFIER",
    }[outcome]
    if population == "configured_etf_review" and outcome != ExecutionPreflightOutcome.ELIGIBLE:
        remediation = "REVIEW_AND_REGISTER_ETF"
    elif population == "configured_dr_alias_review" and facts.instrument_form != ExecutionInstrumentForm.DEPOSITARY_RECEIPT:
        remediation = "REVIEW_DR_IDENTITY_AND_UNDERLYING"
    elif population == "configured_reference_review" and outcome != ExecutionPreflightOutcome.REFERENCE_ONLY:
        remediation = "REVIEW_AND_REGISTER_REFERENCE"

    provenance = tuple(
        f"{item.fact}:{item.source_field}={item.source_value}"
        + (f" (source={item.evidence_source})" if item.evidence_source else "")
        for item in facts.provenance
    )
    return ExecutionPreflightRow(
        population=population,
        requested_symbol=symbol,
        evidence=tuple(sorted(set(evidence))),
        outcome=outcome,
        supported_executable=outcome == ExecutionPreflightOutcome.ELIGIBLE,
        canonical_symbol=facts.canonical_symbol,
        asset_id=int(facts.asset_id) if facts.asset_id is not None else None,
        asset_type=(facts.registry_asset_type.value if facts.registry_asset_type else None),
        instrument_form=facts.instrument_form.value,
        execution_role=facts.execution_role.value,
        relationship_evidence=relationships,
        identifier_evidence=identifiers,
        classification_provenance=provenance,
        missing_requirements=tuple(dict.fromkeys(missing)),
        recommended_remediation_category=remediation,
    )


def _coverage(rows: Sequence[ExecutionPreflightRow]) -> Tuple[ExecutionPreflightCoverage, ...]:
    populations = sorted({row.population for row in rows})
    result = []
    for population in populations:
        selected = [row for row in rows if row.population == population]
        counts: Dict[str, int] = {}
        for row in selected:
            counts[row.outcome.value] = counts.get(row.outcome.value, 0) + 1
        result.append(
            ExecutionPreflightCoverage(
                population=population,
                total=len(selected),
                by_outcome=dict(sorted(counts.items())),
                supported_executable=sum(row.supported_executable for row in selected),
            )
        )
    return tuple(result)


def _native_readiness(
    table: str,
    operational_rows: Iterable[object],
    facts_by_symbol: Mapping[str, ExecutionInstrumentFacts],
) -> NativeAssetIdReadiness:
    rows = list(operational_rows)
    materialized = exactly_resolvable = unresolved = ambiguous = failures = conflicts = 0
    proposals: list[NativeAssetIdProposal] = []
    for row in rows:
        native_asset_id = getattr(row, "asset_id", None)
        if native_asset_id is not None:
            materialized += 1
        symbol = str(getattr(row, "symbol", "") or "")
        facts = facts_by_symbol.get(symbol)
        if facts is None or facts.resolution_error:
            failures += 1
            continue
        if facts.resolution_status == ExecutionResolutionOutcome.AMBIGUOUS:
            ambiguous += 1
            continue
        if facts.asset_id is None:
            unresolved += 1
            continue
        exactly_resolvable += 1
        resolved_asset_id = int(facts.asset_id)
        if native_asset_id is not None and int(native_asset_id) != resolved_asset_id:
            conflicts += 1
        elif native_asset_id is None:
            proposals.append(
                NativeAssetIdProposal(
                    table=table,
                    row_id=int(getattr(row, "id")),
                    requested_symbol=symbol,
                    proposed_asset_id=resolved_asset_id,
                    canonical_symbol=facts.canonical_symbol,
                )
            )
    return NativeAssetIdReadiness(
        table=table,
        total_rows=len(rows),
        materialized_rows=materialized,
        exactly_resolvable_rows=exactly_resolvable,
        missing_but_resolvable=len(proposals),
        unresolved_rows=unresolved,
        ambiguous_rows=ambiguous,
        registry_failure_rows=failures,
        conflicting_existing_rows=conflicts,
        dry_run_proposals=tuple(proposals),
    )


def build_execution_registry_preflight(
    db: Session,
    *,
    workspace_id: Optional[int] = None,
) -> ExecutionRegistryPreflightReport:
    """Build the repeatable report without retaining resolver/finding writes."""

    populations = _collect_operational_populations(db, workspace_id)
    symbols = tuple(
        dict.fromkeys(
            symbol
            for population in populations.values()
            for symbol in population
        )
    )
    registry_lookup.invalidate_cache()
    facts_by_symbol = resolve_execution_eligibility_shadow_facts(db, symbols)

    report_rows = tuple(
        _build_row(db, population, symbol, evidence, facts_by_symbol[symbol])
        for population, symbols_and_evidence in sorted(populations.items())
        for symbol, evidence in sorted(symbols_and_evidence.items())
    )

    holdings_query = db.query(PortfolioItem)
    watchlist_query = db.query(Watchlist)
    transactions_query = db.query(Transaction).filter(
        Transaction.transaction_type.in_(_EXECUTABLE_TRANSACTIONS)
    )
    if workspace_id is not None:
        holdings_query = holdings_query.filter(PortfolioItem.workspace_id == workspace_id)
        watchlist_query = watchlist_query.filter(Watchlist.workspace_id == workspace_id)
        transactions_query = transactions_query.filter(Transaction.workspace_id == workspace_id)

    native = (
        _native_readiness("portfolio_items", holdings_query.all(), facts_by_symbol),
        _native_readiness("watchlist", watchlist_query.all(), facts_by_symbol),
        _native_readiness("transactions", transactions_query.all(), facts_by_symbol),
    )
    registry_lookup.invalidate_cache()
    return ExecutionRegistryPreflightReport(
        generated_at=datetime.utcnow(),
        read_only=True,
        rows=report_rows,
        coverage=_coverage(report_rows),
        native_asset_id_readiness=native,
        limitations=(
            "execution plans are not persisted, so arbitrary future plan inputs cannot be measured",
            "manual transaction routes accept an open-ended symbol universe until a later admission milestone",
            "legacy ETF/DR/benchmark configuration is review evidence, never Registry authority",
            "native asset_id proposals are reporting-only and require separate governance approval",
        ),
    )
