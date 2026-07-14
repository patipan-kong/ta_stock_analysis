"""Registry-backed execution instrument facts (M31.1 foundation).

This module adapts the Asset Registry's existing read contracts into the
small, immutable vocabulary the Execution Domain needs.  It is deliberately
descriptive only: it does not block execution, alter optimizer scores, quote
fees, size trades, or persist execution state.

Authoritative sources
---------------------
* Identity comes from ``services.registry_lookup.resolve_asset`` and therefore
  from the Registry identity resolver.  This module never matches symbols.
* EQUITY and ETF come from ``models.asset.Asset.asset_type``, projected as
  ``registry_lookup.AssetView.asset_type``.
* DEPOSITARY_RECEIPT comes only from an outgoing
  ``models.asset.AssetRelationship.relationship_type`` equal to
  ``DEPOSITARY_RECEIPT_OF``.  Symbol spelling is never evidence of DR status.
* Tradability comes from ``models.asset.Asset.tradable``.
* A market-index reference is a Registry ``OTHER`` asset with a current
  classification whose dimension is ``ASSET_CLASS`` and value is ``INDEX``.
  INDEX is an execution role distinction, never an instrument form.

Missing, conflicting, or incomplete Registry evidence produces an explicit
UNKNOWN or AMBIGUOUS result.  There is no fallback instrument form.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Sequence, Tuple, Union

from sqlalchemy.orm import Session

from services import registry_lookup, registry_service
from services.asset_domain import (
    AssetId,
    AssetType,
    ClassificationDimension,
    RelationshipType,
)
from services.resolver_domain import ResolutionVerdict

__all__ = [
    "ExecutionResolutionOutcome",
    "ExecutionInstrumentForm",
    "ExecutionRole",
    "ExecutionFactProvenance",
    "ExecutionInstrumentFacts",
    "resolve_execution_instrument",
    "resolve_execution_instruments",
]


class ExecutionResolutionOutcome(str, Enum):
    RESOLVED = "RESOLVED"
    UNKNOWN = "UNKNOWN"
    AMBIGUOUS = "AMBIGUOUS"
    NOT_TRADABLE = "NOT_TRADABLE"


class ExecutionInstrumentForm(str, Enum):
    EQUITY = "EQUITY"
    ETF = "ETF"
    DEPOSITARY_RECEIPT = "DEPOSITARY_RECEIPT"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class ExecutionRole(str, Enum):
    TRADABLE = "TRADABLE"
    REFERENCE = "REFERENCE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ExecutionFactProvenance:
    """One Registry fact used to produce the execution projection."""

    fact: str
    source_field: str
    source_value: str
    evidence_source: Optional[str] = None


@dataclass(frozen=True)
class ExecutionInstrumentFacts:
    """Immutable execution-facing projection of one Registry resolution."""

    query: str
    resolution_status: ExecutionResolutionOutcome
    instrument_form: ExecutionInstrumentForm
    execution_role: ExecutionRole
    asset_id: Optional[AssetId] = None
    canonical_symbol: Optional[str] = None
    display_symbol: Optional[str] = None
    market: Optional[str] = None
    exchange: Optional[str] = None
    currency: Optional[str] = None
    registry_asset_type: Optional[AssetType] = None
    tradable: Optional[bool] = None
    fractional_support: Optional[bool] = None
    lot_size: Optional[int] = None
    settlement_cycle: Optional[str] = None
    underlying_asset_id: Optional[AssetId] = None
    provenance: Tuple[ExecutionFactProvenance, ...] = ()
    reason: Optional[str] = None
    resolution_error: Optional[str] = None


_IDENTITY_SOURCE = "services.registry_lookup.resolve_asset"
_ASSET_TYPE_SOURCE = "models.asset.Asset.asset_type"
_TRADABLE_SOURCE = "models.asset.Asset.tradable"
_DR_RELATIONSHIP_SOURCE = "models.asset.AssetRelationship.relationship_type"
_INDEX_CLASSIFICATION_SOURCE = "models.asset.AssetClassification.value"
_INDEX_ASSET_CLASS = "INDEX"


def resolve_execution_instrument(
    db: Session,
    query: Union[str, AssetId, int],
) -> ExecutionInstrumentFacts:
    """Resolve Registry identity and adapt it to execution instrument facts.

    The function is read-only with respect to execution state.  It delegates
    identity matching to ``registry_lookup`` and relationship reads to
    ``registry_service``; it contains no symbol classification logic.
    """

    rendered_query = str(query)
    try:
        resolved = registry_lookup.resolve_asset(db, query)
    except (TypeError, ValueError) as exc:
        return _unresolved(
            rendered_query,
            ExecutionResolutionOutcome.UNKNOWN,
            f"incomplete Registry metadata: {exc}",
            ResolutionVerdict.UNKNOWN,
        )

    return _adapt_registry_resolution(db, rendered_query, resolved)


def resolve_execution_instruments(
    db: Session,
    queries: Sequence[Union[str, AssetId, int]],
) -> Dict[Union[str, int], ExecutionInstrumentFacts]:
    """Batch-adapt Registry resolutions for one execution orchestration run.

    Callers provide the complete symbol set once.  The function delegates to
    the Registry's existing ``resolve_many`` read API rather than performing
    per-symbol lookups at the optimizer boundary.  A Registry/read failure is
    represented as UNKNOWN facts for every affected query; it never escapes
    into the optimizer path.
    """

    unique_queries = tuple(dict.fromkeys(queries))
    if not unique_queries:
        return {}

    try:
        resolved_many = registry_lookup.resolve_many(db, unique_queries)
    except Exception as exc:  # optimizer boundary must degrade, never abort
        error = f"{type(exc).__name__}: {exc}"
        reason = f"Registry facts batch resolution failed: {type(exc).__name__}"
        return {
            query: _unresolved(
                str(query),
                ExecutionResolutionOutcome.UNKNOWN,
                reason,
                ResolutionVerdict.UNKNOWN,
                resolution_error=error,
            )
            for query in unique_queries
        }

    facts_by_query: Dict[Union[str, int], ExecutionInstrumentFacts] = {}
    for query in unique_queries:
        try:
            facts_by_query[query] = _adapt_registry_resolution(
                db,
                str(query),
                resolved_many[query],
            )
        except Exception as exc:  # isolate malformed/missing evidence per asset
            facts_by_query[query] = _unresolved(
                str(query),
                ExecutionResolutionOutcome.UNKNOWN,
                f"Registry facts adaptation failed: {type(exc).__name__}",
                ResolutionVerdict.UNKNOWN,
                resolution_error=f"{type(exc).__name__}: {exc}",
            )
    return facts_by_query


def _adapt_registry_resolution(
    db: Session,
    rendered_query: str,
    resolved: Union[registry_lookup.AssetView, registry_lookup.Unresolved],
) -> ExecutionInstrumentFacts:
    if isinstance(resolved, registry_lookup.Unresolved):
        outcome = (
            ExecutionResolutionOutcome.AMBIGUOUS
            if resolved.verdict in (ResolutionVerdict.AMBIGUOUS, ResolutionVerdict.CONFLICT)
            else ExecutionResolutionOutcome.UNKNOWN
        )
        return _unresolved(rendered_query, outcome, resolved.reason, resolved.verdict)

    missing_fields = _missing_required_fields(resolved)
    if missing_fields:
        return _unresolved(
            rendered_query,
            ExecutionResolutionOutcome.UNKNOWN,
            "incomplete Registry metadata: " + ", ".join(missing_fields),
            ResolutionVerdict.RESOLVED,
        )

    relationships = registry_service.get_relationships(db, resolved.asset_id)
    dr_relationships = tuple(
        relationship
        for relationship in relationships
        if relationship.from_asset_id == int(resolved.asset_id)
        and relationship.relationship_type == RelationshipType.DEPOSITARY_RECEIPT_OF.value
    )

    if len(dr_relationships) > 1:
        return ExecutionInstrumentFacts(
            query=rendered_query,
            resolution_status=ExecutionResolutionOutcome.AMBIGUOUS,
            instrument_form=ExecutionInstrumentForm.UNKNOWN,
            execution_role=ExecutionRole.UNKNOWN,
            asset_id=resolved.asset_id,
            canonical_symbol=resolved.canonical_symbol,
            display_symbol=resolved.display_symbol,
            market=resolved.market,
            exchange=resolved.exchange,
            currency=resolved.currency,
            registry_asset_type=resolved.asset_type,
            tradable=resolved.tradable,
            fractional_support=resolved.fractional_support,
            lot_size=resolved.lot_size,
            settlement_cycle=resolved.settlement_cycle,
            provenance=(_identity_provenance(resolved.asset_id),),
            reason="multiple DEPOSITARY_RECEIPT_OF relationships in Registry",
        )

    if dr_relationships:
        instrument_form = ExecutionInstrumentForm.DEPOSITARY_RECEIPT
        underlying_asset_id = AssetId(dr_relationships[0].to_asset_id)
        form_provenance = ExecutionFactProvenance(
            fact="instrument_form",
            source_field=_DR_RELATIONSHIP_SOURCE,
            source_value=RelationshipType.DEPOSITARY_RECEIPT_OF.value,
        )
    else:
        instrument_form = _form_from_registry_asset_type(resolved.asset_type)
        underlying_asset_id = None
        form_provenance = ExecutionFactProvenance(
            fact="instrument_form",
            source_field=_ASSET_TYPE_SOURCE,
            source_value=resolved.asset_type.value,
        )

    asset_class = resolved.classification.get(ClassificationDimension.ASSET_CLASS.value)
    is_market_index = (
        resolved.asset_type == AssetType.OTHER
        and asset_class == _INDEX_ASSET_CLASS
    )

    if is_market_index:
        resolution_status = ExecutionResolutionOutcome.NOT_TRADABLE
        execution_role = ExecutionRole.REFERENCE
        role_provenance = ExecutionFactProvenance(
            fact="execution_role",
            source_field=_INDEX_CLASSIFICATION_SOURCE,
            source_value=asset_class,
            evidence_source=resolved.classification_provenance.get(
                ClassificationDimension.ASSET_CLASS.value,
            ),
        )
        reason = "Registry classifies the asset as a non-tradable market index reference"
    elif not resolved.tradable:
        resolution_status = ExecutionResolutionOutcome.NOT_TRADABLE
        execution_role = ExecutionRole.UNKNOWN
        role_provenance = ExecutionFactProvenance(
            fact="execution_role",
            source_field=_TRADABLE_SOURCE,
            source_value=str(resolved.tradable),
        )
        reason = "Registry marks the asset as non-tradable"
    else:
        resolution_status = ExecutionResolutionOutcome.RESOLVED
        execution_role = ExecutionRole.TRADABLE
        role_provenance = ExecutionFactProvenance(
            fact="execution_role",
            source_field=_TRADABLE_SOURCE,
            source_value=str(resolved.tradable),
        )
        reason = None

    return ExecutionInstrumentFacts(
        query=rendered_query,
        resolution_status=resolution_status,
        instrument_form=instrument_form,
        execution_role=execution_role,
        asset_id=resolved.asset_id,
        canonical_symbol=resolved.canonical_symbol,
        display_symbol=resolved.display_symbol,
        market=resolved.market,
        exchange=resolved.exchange,
        currency=resolved.currency,
        registry_asset_type=resolved.asset_type,
        tradable=resolved.tradable,
        fractional_support=resolved.fractional_support,
        lot_size=resolved.lot_size,
        settlement_cycle=resolved.settlement_cycle,
        underlying_asset_id=underlying_asset_id,
        provenance=(
            _identity_provenance(resolved.asset_id),
            form_provenance,
            role_provenance,
        ),
        reason=reason,
    )


def _form_from_registry_asset_type(asset_type: AssetType) -> ExecutionInstrumentForm:
    if asset_type == AssetType.EQUITY:
        return ExecutionInstrumentForm.EQUITY
    if asset_type == AssetType.ETF:
        return ExecutionInstrumentForm.ETF
    return ExecutionInstrumentForm.OTHER


def _missing_required_fields(view: registry_lookup.AssetView) -> Tuple[str, ...]:
    required_strings = {
        "canonical_symbol": view.canonical_symbol,
        "display_symbol": view.display_symbol,
        "market": view.market,
        "exchange": view.exchange,
        "currency": view.currency,
    }
    missing = [
        name for name, value in required_strings.items()
        if not isinstance(value, str) or not value.strip()
    ]
    if not isinstance(view.asset_type, AssetType):
        missing.append("asset_type")
    if not isinstance(view.tradable, bool):
        missing.append("tradable")
    return tuple(missing)


def _identity_provenance(asset_id: AssetId) -> ExecutionFactProvenance:
    return ExecutionFactProvenance(
        fact="identity",
        source_field=_IDENTITY_SOURCE,
        source_value=str(int(asset_id)),
    )


def _unresolved(
    query: str,
    outcome: ExecutionResolutionOutcome,
    reason: str,
    registry_verdict: ResolutionVerdict,
    *,
    resolution_error: Optional[str] = None,
) -> ExecutionInstrumentFacts:
    return ExecutionInstrumentFacts(
        query=query,
        resolution_status=outcome,
        instrument_form=ExecutionInstrumentForm.UNKNOWN,
        execution_role=ExecutionRole.UNKNOWN,
        provenance=(
            ExecutionFactProvenance(
                fact="identity",
                source_field=_IDENTITY_SOURCE,
                source_value=registry_verdict.value,
            ),
        ),
        reason=reason,
        resolution_error=resolution_error,
    )
