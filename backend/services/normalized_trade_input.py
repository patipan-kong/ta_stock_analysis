"""Pure, shadow-only normalized pre-execution trade inputs (M32.3B).

This module records the handoff between a recommendation (or an explicit
manual request) and a future constrained execution trade leg.  It is not an
order builder: it has no ORM, Registry, market-data, clock, environment, or
fee-calculation dependency.  Callers must provide already-resolved facts,
eligibility, price evidence, and (when available) a FeeQuote.

Incomplete inputs are first-class results.  In particular, amount-only
recommendations retain their requested value without being converted to a
fictional quantity or price.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Mapping, Sequence

from services.broker_fees import FeeQuote, FeeQuoteStatus, TradeSide
from services.execution_eligibility import (
    ExecutionEligibility,
    evaluate_execution_eligibility,
)
from services.execution_instrument_facts import (
    ExecutionInstrumentFacts,
    ExecutionResolutionOutcome,
)

__all__ = [
    "QuantityIntentSource",
    "QuantityConfidence",
    "PriceKind",
    "PriceSource",
    "MarketSession",
    "AllocationSource",
    "NormalizationStatus",
    "NormalizationFailureReason",
    "NormalizationFailure",
    "QuantityAdjustmentSummary",
    "HoldingQuantitySnapshot",
    "TradeInputNormalizationRequest",
    "NormalizedTradeInput",
    "NormalizationResult",
    "NormalizedTradeInputShadowProjection",
    "normalize_trade_input",
    "adapt_explicit_manual_quantity_intent",
    "adapt_full_holding_sell_intent",
    "adapt_optimizer_amount_intent",
    "adapt_decision_workspace_amount_intent",
    "adapt_holding_fraction_intent",
    "project_execution_plan_normalized_inputs_shadow",
]


_CONTRACT_VERSION = "1"


class QuantityIntentSource(str, Enum):
    """Where a requested quantity or requested value originated."""

    EXPLICIT_USER_QUANTITY = "EXPLICIT_USER_QUANTITY"
    FULL_HOLDING_QUANTITY = "FULL_HOLDING_QUANTITY"
    ALLOCATION_VALUE_AT_PRICE = "ALLOCATION_VALUE_AT_PRICE"
    REDUCTION_VALUE_AT_PRICE = "REDUCTION_VALUE_AT_PRICE"
    HOLDING_FRACTION = "HOLDING_FRACTION"
    BROKER_ORDER_QUANTITY = "BROKER_ORDER_QUANTITY"
    UNSPECIFIED = "UNSPECIFIED"


class QuantityConfidence(str, Enum):
    EXACT = "EXACT"
    DERIVED = "DERIVED"
    ESTIMATED = "ESTIMATED"


class PriceKind(str, Enum):
    """The semantic kind of price evidence, not a market-data policy."""

    USER_EXECUTION_TERM = "USER_EXECUTION_TERM"
    MARKET_REFERENCE = "MARKET_REFERENCE"
    UNKNOWN = "UNKNOWN"


class PriceSource(str, Enum):
    USER_ENTERED = "USER_ENTERED"
    CALLER_SUPPLIED = "CALLER_SUPPLIED"
    UNKNOWN = "UNKNOWN"


class MarketSession(str, Enum):
    REGULAR = "REGULAR"
    PRE_MARKET = "PRE_MARKET"
    AFTER_HOURS = "AFTER_HOURS"
    CLOSED = "CLOSED"
    UNKNOWN = "UNKNOWN"


class AllocationSource(str, Enum):
    OPTIMIZER_TARGET_ALLOCATION = "OPTIMIZER_TARGET_ALLOCATION"
    DECISION_WORKSPACE_POSITION_SIZING = "DECISION_WORKSPACE_POSITION_SIZING"


class NormalizationStatus(str, Enum):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"


class NormalizationFailureReason(str, Enum):
    MISSING_QUANTITY = "MISSING_QUANTITY"
    MISSING_REQUESTED_VALUE = "MISSING_REQUESTED_VALUE"
    MISSING_PRICE = "MISSING_PRICE"
    PRICE_PROVENANCE_MISSING = "PRICE_PROVENANCE_MISSING"
    PRICE_TIMESTAMP_MISSING = "PRICE_TIMESTAMP_MISSING"
    PRICE_SESSION_UNKNOWN = "PRICE_SESSION_UNKNOWN"
    PRICE_STALE = "PRICE_STALE"
    FRESHNESS_UNASSESSED = "FRESHNESS_UNASSESSED"
    CURRENCY_UNKNOWN = "CURRENCY_UNKNOWN"
    FACTS_UNRESOLVED = "FACTS_UNRESOLVED"
    FACTS_IDENTITY_MISMATCH = "FACTS_IDENTITY_MISMATCH"
    ELIGIBILITY_MISMATCH = "ELIGIBILITY_MISMATCH"
    INELIGIBLE_INSTRUMENT = "INELIGIBLE_INSTRUMENT"
    FEE_QUOTE_UNAVAILABLE = "FEE_QUOTE_UNAVAILABLE"
    QUANTITY_QUOTE_MISMATCH = "QUANTITY_QUOTE_MISMATCH"
    PRICE_QUOTE_MISMATCH = "PRICE_QUOTE_MISMATCH"
    CURRENCY_QUOTE_MISMATCH = "CURRENCY_QUOTE_MISMATCH"
    SIDE_QUOTE_MISMATCH = "SIDE_QUOTE_MISMATCH"
    SIDE_SOURCE_MISMATCH = "SIDE_SOURCE_MISMATCH"
    QUANTITY_ADJUSTMENT_UNEXPLAINED = "QUANTITY_ADJUSTMENT_UNEXPLAINED"
    INVALID_QUANTITY = "INVALID_QUANTITY"
    INVALID_REQUESTED_VALUE = "INVALID_REQUESTED_VALUE"
    INVALID_PRICE = "INVALID_PRICE"
    UNSUPPORTED_SOURCE = "UNSUPPORTED_SOURCE"


@dataclass(frozen=True)
class NormalizationFailure:
    reason: NormalizationFailureReason
    detail: str


@dataclass(frozen=True)
class QuantityAdjustmentSummary:
    """Evidence for a quantity change; M32.3B adapters use only no-op values."""

    requested_quantity: Decimal | None
    executable_quantity: Decimal | None
    residual_quantity: Decimal | None = None
    policy_reference: str | None = None
    adjusted: bool = False
    reason: str | None = None

    @classmethod
    def no_op(cls, quantity: Decimal | None, *, policy_reference: str) -> "QuantityAdjustmentSummary":
        return cls(
            requested_quantity=quantity,
            executable_quantity=quantity,
            policy_reference=policy_reference,
        )


@dataclass(frozen=True)
class HoldingQuantitySnapshot:
    """Caller-supplied Portfolio Runtime evidence; never loaded by an adapter."""

    quantity: Decimal
    observed_at: datetime | None
    source: str
    provenance: tuple[str, ...] = ()


@dataclass(frozen=True)
class TradeInputNormalizationRequest:
    """All preloaded evidence accepted by the one pure normalization boundary."""

    recommendation_reference: str | None
    requested_symbol: str
    side: TradeSide
    requested_quantity: Decimal | None
    executable_quantity: Decimal | None
    requested_value: Decimal | None
    quantity_source: QuantityIntentSource
    quantity_confidence: QuantityConfidence
    lot_adjustment: QuantityAdjustmentSummary
    fractional_adjustment: QuantityAdjustmentSummary
    unit_price: Decimal | None
    price_kind: PriceKind
    price_source: PriceSource
    observed_at: datetime | None
    received_at: datetime | None
    market_session: MarketSession
    freshness_assessed_at: datetime | None
    freshness_policy_reference: str | None
    stale: bool | None
    currency: str | None
    execution_instrument_facts: ExecutionInstrumentFacts
    execution_eligibility: ExecutionEligibility
    fee_quote: FeeQuote | None = None
    allocation_source: AllocationSource | None = None
    holding_quantity_snapshot: HoldingQuantitySnapshot | None = None
    portfolio_currency: str | None = None
    valuation_currency: str | None = None
    assumptions: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    provenance: tuple[str, ...] = ()


@dataclass(frozen=True)
class NormalizedTradeInput:
    """Immutable normalized pre-execution evidence, complete or explicitly incomplete.

    The retained objects are intentionally not copied.  Facts own identity,
    eligibility owns admissibility, and FeeQuote owns fee arithmetic.
    """

    contract_version: str
    normalization_ref: str
    recommendation_reference: str | None
    requested_symbol: str
    side: TradeSide
    requested_quantity: Decimal | None
    executable_quantity: Decimal | None
    requested_value: Decimal | None
    quantity_source: QuantityIntentSource
    quantity_confidence: QuantityConfidence
    lot_adjustment: QuantityAdjustmentSummary
    fractional_adjustment: QuantityAdjustmentSummary
    unit_price: Decimal | None
    price_kind: PriceKind
    price_source: PriceSource
    observed_at: datetime | None
    received_at: datetime | None
    market_session: MarketSession
    freshness_assessed_at: datetime | None
    freshness_policy_reference: str | None
    stale: bool | None
    currency: str | None
    execution_instrument_facts: ExecutionInstrumentFacts
    execution_eligibility: ExecutionEligibility
    fee_quote: FeeQuote | None
    allocation_source: AllocationSource | None
    holding_quantity_snapshot: HoldingQuantitySnapshot | None
    portfolio_currency: str | None
    valuation_currency: str | None
    assumptions: tuple[str, ...]
    warnings: tuple[str, ...]
    provenance: tuple[str, ...]
    status: NormalizationStatus

    @property
    def complete(self) -> bool:
        return self.status == NormalizationStatus.COMPLETE

    @property
    def asset_id(self) -> int | None:
        facts = self.execution_instrument_facts
        return int(facts.asset_id) if facts.asset_id is not None else None

    @property
    def canonical_symbol(self) -> str | None:
        return self.execution_instrument_facts.canonical_symbol


@dataclass(frozen=True)
class NormalizationResult:
    normalized_input: NormalizedTradeInput
    failures: tuple[NormalizationFailure, ...]

    @property
    def complete(self) -> bool:
        return self.normalized_input.complete


@dataclass(frozen=True)
class NormalizedTradeInputShadowProjection:
    """Private execution-plan diagnostic; never returned or persisted."""

    results: tuple[NormalizationResult, ...]
    unavailable_symbols: tuple[str, ...]

    @property
    def complete_count(self) -> int:
        return sum(result.complete for result in self.results)

    def failure_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for result in self.results:
            for failure in result.failures:
                counts[failure.reason.value] = counts.get(failure.reason.value, 0) + 1
        return counts


def normalize_trade_input(request: TradeInputNormalizationRequest) -> NormalizationResult:
    """Validate only supplied evidence and return a complete or typed-incomplete input.

    There is deliberately no lookup, calculation, clock read, or fallback in
    this boundary.  In particular, a requested value is not divided by a
    price, and an unavailable FeeQuote is never treated as free.
    """

    failures: list[NormalizationFailure] = []
    _validate_source_and_side(request, failures)
    _validate_quantities(request, failures)
    _validate_facts_and_eligibility(request, failures)
    _validate_price(request, failures)
    _validate_fee_quote(request, failures)
    failures = _deduplicate_failures(failures)
    status = NormalizationStatus.COMPLETE if not failures else NormalizationStatus.INCOMPLETE
    normalized = NormalizedTradeInput(
        contract_version=_CONTRACT_VERSION,
        normalization_ref=_normalization_ref(request),
        recommendation_reference=request.recommendation_reference,
        requested_symbol=request.requested_symbol,
        side=request.side,
        requested_quantity=request.requested_quantity,
        executable_quantity=request.executable_quantity,
        requested_value=request.requested_value,
        quantity_source=request.quantity_source,
        quantity_confidence=request.quantity_confidence,
        lot_adjustment=request.lot_adjustment,
        fractional_adjustment=request.fractional_adjustment,
        unit_price=request.unit_price,
        price_kind=request.price_kind,
        price_source=request.price_source,
        observed_at=request.observed_at,
        received_at=request.received_at,
        market_session=request.market_session,
        freshness_assessed_at=request.freshness_assessed_at,
        freshness_policy_reference=request.freshness_policy_reference,
        stale=request.stale,
        currency=request.currency,
        execution_instrument_facts=request.execution_instrument_facts,
        execution_eligibility=request.execution_eligibility,
        fee_quote=request.fee_quote,
        allocation_source=request.allocation_source,
        holding_quantity_snapshot=request.holding_quantity_snapshot,
        portfolio_currency=request.portfolio_currency,
        valuation_currency=request.valuation_currency,
        assumptions=request.assumptions,
        warnings=request.warnings,
        provenance=request.provenance,
        status=status,
    )
    return NormalizationResult(normalized, tuple(failures))


def adapt_explicit_manual_quantity_intent(
    *,
    recommendation_reference: str | None,
    requested_symbol: str,
    side: TradeSide,
    requested_quantity: Decimal,
    entered_price: Decimal | None,
    currency: str | None,
    facts: ExecutionInstrumentFacts,
    eligibility: ExecutionEligibility,
    fee_quote: FeeQuote | None = None,
    provenance: tuple[str, ...] = (),
) -> NormalizationResult:
    """Preserve a user term without presenting it as a market observation/fill."""

    return normalize_trade_input(
        _request(
            recommendation_reference=recommendation_reference,
            requested_symbol=requested_symbol,
            side=side,
            requested_quantity=requested_quantity,
            executable_quantity=requested_quantity,
            requested_value=None,
            quantity_source=QuantityIntentSource.EXPLICIT_USER_QUANTITY,
            quantity_confidence=QuantityConfidence.EXACT,
            unit_price=entered_price,
            price_kind=(PriceKind.USER_EXECUTION_TERM if entered_price is not None else PriceKind.UNKNOWN),
            price_source=(PriceSource.USER_ENTERED if entered_price is not None else PriceSource.UNKNOWN),
            currency=currency,
            facts=facts,
            eligibility=eligibility,
            fee_quote=fee_quote,
            provenance=("M32.3B explicit manual quantity intent",) + provenance,
        )
    )


def adapt_full_holding_sell_intent(
    *,
    recommendation_reference: str | None,
    requested_symbol: str,
    holding_snapshot: HoldingQuantitySnapshot,
    facts: ExecutionInstrumentFacts,
    eligibility: ExecutionEligibility,
    fee_quote: FeeQuote | None = None,
    provenance: tuple[str, ...] = (),
) -> NormalizationResult:
    """Preserve a supplied held-quantity snapshot; never query PortfolioItem."""

    quantity = holding_snapshot.quantity
    return normalize_trade_input(
        _request(
            recommendation_reference=recommendation_reference,
            requested_symbol=requested_symbol,
            side=TradeSide.SELL,
            requested_quantity=quantity,
            executable_quantity=quantity,
            requested_value=None,
            quantity_source=QuantityIntentSource.FULL_HOLDING_QUANTITY,
            quantity_confidence=QuantityConfidence.EXACT,
            facts=facts,
            eligibility=eligibility,
            fee_quote=fee_quote,
            holding_snapshot=holding_snapshot,
            provenance=("M32.3B full-holding SELL intent",) + holding_snapshot.provenance + provenance,
        )
    )


def adapt_optimizer_amount_intent(
    *,
    recommendation_reference: str | None,
    requested_symbol: str,
    requested_value: Decimal,
    facts: ExecutionInstrumentFacts,
    eligibility: ExecutionEligibility,
    valuation_currency: str | None = None,
    provenance: tuple[str, ...] = (),
) -> NormalizationResult:
    """Keep an optimizer allocation amount as an incomplete non-quantity intent."""

    return _amount_only_intent(
        recommendation_reference=recommendation_reference,
        requested_symbol=requested_symbol,
        requested_value=requested_value,
        facts=facts,
        eligibility=eligibility,
        allocation_source=AllocationSource.OPTIMIZER_TARGET_ALLOCATION,
        valuation_currency=valuation_currency,
        provenance=("M32.3B optimizer amount-only recommendation",) + provenance,
    )


def adapt_decision_workspace_amount_intent(
    *,
    recommendation_reference: str | None,
    requested_symbol: str,
    requested_value: Decimal,
    facts: ExecutionInstrumentFacts,
    eligibility: ExecutionEligibility,
    valuation_currency: str | None = None,
    provenance: tuple[str, ...] = (),
) -> NormalizationResult:
    """Keep Decision Workspace sizing as incomplete amount-only evidence."""

    return _amount_only_intent(
        recommendation_reference=recommendation_reference,
        requested_symbol=requested_symbol,
        requested_value=requested_value,
        facts=facts,
        eligibility=eligibility,
        allocation_source=AllocationSource.DECISION_WORKSPACE_POSITION_SIZING,
        valuation_currency=valuation_currency,
        provenance=("M32.3B Decision Workspace amount-only sizing",) + provenance,
    )


def adapt_holding_fraction_intent(
    *,
    recommendation_reference: str | None,
    requested_symbol: str,
    holding_snapshot: HoldingQuantitySnapshot,
    holding_fraction: Decimal,
    facts: ExecutionInstrumentFacts,
    eligibility: ExecutionEligibility,
    fee_quote: FeeQuote | None = None,
    provenance: tuple[str, ...] = (),
) -> NormalizationResult:
    """Derive a SELL quantity only from explicit holding evidence and fraction."""

    quantity = holding_snapshot.quantity * holding_fraction
    return normalize_trade_input(
        _request(
            recommendation_reference=recommendation_reference,
            requested_symbol=requested_symbol,
            side=TradeSide.SELL,
            requested_quantity=quantity,
            executable_quantity=quantity,
            requested_value=None,
            quantity_source=QuantityIntentSource.HOLDING_FRACTION,
            quantity_confidence=QuantityConfidence.DERIVED,
            facts=facts,
            eligibility=eligibility,
            fee_quote=fee_quote,
            holding_snapshot=holding_snapshot,
            provenance=(
                "M32.3B explicit holding-fraction intent",
                f"upstream holding_fraction={_decimal_text(holding_fraction)}",
            ) + holding_snapshot.provenance + provenance,
        )
    )


def project_execution_plan_normalized_inputs_shadow(
    buy_actions: Sequence[Any],
    funding_actions: Sequence[Any],
    facts_by_symbol: Mapping[str, ExecutionInstrumentFacts],
    eligibility_by_symbol: Mapping[str, ExecutionEligibility],
) -> NormalizedTradeInputShadowProjection:
    """Project the unchanged legacy plan into private M32.3B intent evidence.

    BUY actions retain their amount and remain incomplete.  Funding actions
    retain explicit legacy share/fraction inputs and also remain incomplete
    without price evidence.  This orchestration helper does no lookup, quote,
    price derivation, or time generation.
    """

    results: list[NormalizationResult] = []
    unavailable: list[str] = []
    for action in buy_actions:
        symbol = str(action.symbol)
        facts, eligibility = _shadow_contracts(symbol, facts_by_symbol, eligibility_by_symbol)
        if facts is None or eligibility is None:
            unavailable.append(symbol)
            continue
        results.append(
            adapt_decision_workspace_amount_intent(
                recommendation_reference=f"execution-plan:{action.signal}:{symbol}",
                requested_symbol=symbol,
                requested_value=Decimal(str(action.estimated_amount)),
                facts=facts,
                eligibility=eligibility,
                provenance=("legacy ExecutionPlanResult BuyAction estimated_amount",),
            )
        )
    for action in funding_actions:
        symbol = str(action.symbol)
        facts, eligibility = _shadow_contracts(symbol, facts_by_symbol, eligibility_by_symbol)
        if facts is None or eligibility is None:
            unavailable.append(symbol)
            continue
        snapshot = HoldingQuantitySnapshot(
            quantity=Decimal(str(action.current_shares)),
            observed_at=None,
            source="legacy ExecutionPlanResult FundingAction.current_shares",
            provenance=("legacy plan does not supply holding snapshot timestamp",),
        )
        results.append(
            adapt_holding_fraction_intent(
                recommendation_reference=f"execution-plan:{action.action}:{symbol}",
                requested_symbol=symbol,
                holding_snapshot=snapshot,
                holding_fraction=Decimal(str(action.release_pct)),
                facts=facts,
                eligibility=eligibility,
                provenance=("legacy ExecutionPlanResult FundingAction.release_pct",),
            )
        )
    return NormalizedTradeInputShadowProjection(tuple(results), tuple(unavailable))


def _amount_only_intent(
    *,
    recommendation_reference: str | None,
    requested_symbol: str,
    requested_value: Decimal,
    facts: ExecutionInstrumentFacts,
    eligibility: ExecutionEligibility,
    allocation_source: AllocationSource,
    valuation_currency: str | None,
    provenance: tuple[str, ...],
) -> NormalizationResult:
    return normalize_trade_input(
        _request(
            recommendation_reference=recommendation_reference,
            requested_symbol=requested_symbol,
            side=TradeSide.BUY,
            requested_quantity=None,
            executable_quantity=None,
            requested_value=requested_value,
            quantity_source=QuantityIntentSource.ALLOCATION_VALUE_AT_PRICE,
            quantity_confidence=QuantityConfidence.ESTIMATED,
            facts=facts,
            eligibility=eligibility,
            allocation_source=allocation_source,
            valuation_currency=valuation_currency,
            provenance=provenance,
        )
    )


def _request(
    *,
    recommendation_reference: str | None,
    requested_symbol: str,
    side: TradeSide,
    requested_quantity: Decimal | None,
    executable_quantity: Decimal | None,
    requested_value: Decimal | None,
    quantity_source: QuantityIntentSource,
    quantity_confidence: QuantityConfidence,
    facts: ExecutionInstrumentFacts,
    eligibility: ExecutionEligibility,
    lot_adjustment: QuantityAdjustmentSummary | None = None,
    fractional_adjustment: QuantityAdjustmentSummary | None = None,
    unit_price: Decimal | None = None,
    price_kind: PriceKind = PriceKind.UNKNOWN,
    price_source: PriceSource = PriceSource.UNKNOWN,
    observed_at: datetime | None = None,
    received_at: datetime | None = None,
    market_session: MarketSession = MarketSession.UNKNOWN,
    freshness_assessed_at: datetime | None = None,
    freshness_policy_reference: str | None = None,
    stale: bool | None = None,
    currency: str | None = None,
    fee_quote: FeeQuote | None = None,
    allocation_source: AllocationSource | None = None,
    holding_snapshot: HoldingQuantitySnapshot | None = None,
    portfolio_currency: str | None = None,
    valuation_currency: str | None = None,
    assumptions: tuple[str, ...] = (),
    warnings: tuple[str, ...] = (),
    provenance: tuple[str, ...] = (),
) -> TradeInputNormalizationRequest:
    return TradeInputNormalizationRequest(
        recommendation_reference=recommendation_reference,
        requested_symbol=requested_symbol,
        side=side,
        requested_quantity=requested_quantity,
        executable_quantity=executable_quantity,
        requested_value=requested_value,
        quantity_source=quantity_source,
        quantity_confidence=quantity_confidence,
        lot_adjustment=lot_adjustment or QuantityAdjustmentSummary.no_op(
            requested_quantity,
            policy_reference="M32.3B no lot policy applied",
        ),
        fractional_adjustment=fractional_adjustment or QuantityAdjustmentSummary.no_op(
            requested_quantity,
            policy_reference="M32.3B no fractional policy applied",
        ),
        unit_price=unit_price,
        price_kind=price_kind,
        price_source=price_source,
        observed_at=observed_at,
        received_at=received_at,
        market_session=market_session,
        freshness_assessed_at=freshness_assessed_at,
        freshness_policy_reference=freshness_policy_reference,
        stale=stale,
        currency=currency,
        execution_instrument_facts=facts,
        execution_eligibility=eligibility,
        fee_quote=fee_quote,
        allocation_source=allocation_source,
        holding_quantity_snapshot=holding_snapshot,
        portfolio_currency=portfolio_currency,
        valuation_currency=valuation_currency,
        assumptions=assumptions,
        warnings=warnings,
        provenance=provenance,
    )


def _validate_source_and_side(
    request: TradeInputNormalizationRequest,
    failures: list[NormalizationFailure],
) -> None:
    sell_only = {
        QuantityIntentSource.FULL_HOLDING_QUANTITY,
        QuantityIntentSource.REDUCTION_VALUE_AT_PRICE,
        QuantityIntentSource.HOLDING_FRACTION,
    }
    buy_only = {QuantityIntentSource.ALLOCATION_VALUE_AT_PRICE}
    if request.quantity_source == QuantityIntentSource.UNSPECIFIED:
        failures.append(_failure(NormalizationFailureReason.UNSUPPORTED_SOURCE, "quantity source is unspecified"))
    elif request.quantity_source in sell_only and request.side != TradeSide.SELL:
        failures.append(_failure(NormalizationFailureReason.SIDE_SOURCE_MISMATCH, "quantity source is SELL-only"))
    elif request.quantity_source in buy_only and request.side != TradeSide.BUY:
        failures.append(_failure(NormalizationFailureReason.SIDE_SOURCE_MISMATCH, "quantity source is BUY-only"))

    value_sources = {
        QuantityIntentSource.ALLOCATION_VALUE_AT_PRICE,
        QuantityIntentSource.REDUCTION_VALUE_AT_PRICE,
    }
    if request.quantity_source in value_sources:
        if request.requested_value is None:
            failures.append(_failure(NormalizationFailureReason.MISSING_REQUESTED_VALUE, "value source has no requested value"))
        elif not _positive(request.requested_value):
            failures.append(_failure(NormalizationFailureReason.INVALID_REQUESTED_VALUE, "requested value must be a positive Decimal"))
    elif request.requested_value is not None and not _positive(request.requested_value):
        failures.append(_failure(NormalizationFailureReason.INVALID_REQUESTED_VALUE, "requested value must be a positive Decimal"))


def _validate_quantities(
    request: TradeInputNormalizationRequest,
    failures: list[NormalizationFailure],
) -> None:
    if request.requested_quantity is None:
        failures.append(_failure(NormalizationFailureReason.MISSING_QUANTITY, "requested quantity is absent"))
    elif not _positive(request.requested_quantity):
        failures.append(_failure(NormalizationFailureReason.INVALID_QUANTITY, "requested quantity must be a positive Decimal"))
    if request.executable_quantity is None:
        failures.append(_failure(NormalizationFailureReason.MISSING_QUANTITY, "executable quantity is absent"))
    elif not _positive(request.executable_quantity):
        failures.append(_failure(NormalizationFailureReason.INVALID_QUANTITY, "executable quantity must be a positive Decimal"))

    if (
        isinstance(request.requested_quantity, Decimal)
        and isinstance(request.executable_quantity, Decimal)
        and request.requested_quantity != request.executable_quantity
        and not _adjustments_explain_difference(request)
    ):
        failures.append(_failure(
            NormalizationFailureReason.QUANTITY_ADJUSTMENT_UNEXPLAINED,
            "requested and executable quantity differ without adjustment evidence",
        ))


def _validate_facts_and_eligibility(
    request: TradeInputNormalizationRequest,
    failures: list[NormalizationFailure],
) -> None:
    facts = request.execution_instrument_facts
    if facts.query != request.requested_symbol:
        failures.append(_failure(
            NormalizationFailureReason.FACTS_IDENTITY_MISMATCH,
            "ExecutionInstrumentFacts.query does not match requested symbol",
        ))
    if facts.resolution_status != ExecutionResolutionOutcome.RESOLVED:
        failures.append(_failure(
            NormalizationFailureReason.FACTS_UNRESOLVED,
            facts.reason or "Registry facts are not resolved",
        ))
    if request.execution_eligibility != evaluate_execution_eligibility(facts):
        failures.append(_failure(
            NormalizationFailureReason.ELIGIBILITY_MISMATCH,
            "ExecutionEligibility does not match the supplied ExecutionInstrumentFacts",
        ))
    if not request.execution_eligibility.eligible:
        failures.append(_failure(
            NormalizationFailureReason.INELIGIBLE_INSTRUMENT,
            request.execution_eligibility.reason,
        ))


def _validate_price(
    request: TradeInputNormalizationRequest,
    failures: list[NormalizationFailure],
) -> None:
    if request.unit_price is None:
        failures.append(_failure(NormalizationFailureReason.MISSING_PRICE, "unit price is absent"))
    elif not _positive(request.unit_price):
        failures.append(_failure(NormalizationFailureReason.INVALID_PRICE, "unit price must be a positive Decimal"))
    if request.price_kind == PriceKind.UNKNOWN or request.price_source == PriceSource.UNKNOWN:
        failures.append(_failure(NormalizationFailureReason.PRICE_PROVENANCE_MISSING, "price kind or source is unknown"))
    if request.observed_at is None or request.received_at is None:
        failures.append(_failure(NormalizationFailureReason.PRICE_TIMESTAMP_MISSING, "observed_at and received_at are both required"))
    if request.market_session == MarketSession.UNKNOWN:
        failures.append(_failure(NormalizationFailureReason.PRICE_SESSION_UNKNOWN, "market session is unknown"))
    if request.freshness_assessed_at is None or not request.freshness_policy_reference:
        failures.append(_failure(NormalizationFailureReason.FRESHNESS_UNASSESSED, "freshness policy or assessment time is absent"))
    if request.stale is True:
        failures.append(_failure(NormalizationFailureReason.PRICE_STALE, "price evidence is marked stale"))
    if not request.currency:
        failures.append(_failure(NormalizationFailureReason.CURRENCY_UNKNOWN, "price currency is absent"))


def _validate_fee_quote(
    request: TradeInputNormalizationRequest,
    failures: list[NormalizationFailure],
) -> None:
    quote = request.fee_quote
    if quote is None or quote.status != FeeQuoteStatus.QUOTED:
        failures.append(_failure(NormalizationFailureReason.FEE_QUOTE_UNAVAILABLE, "no successful FeeQuote is supplied"))
        return
    if quote.side != request.side:
        failures.append(_failure(NormalizationFailureReason.SIDE_QUOTE_MISMATCH, "FeeQuote side differs from normalized input"))
    if request.executable_quantity is None or quote.quantity != request.executable_quantity:
        failures.append(_failure(NormalizationFailureReason.QUANTITY_QUOTE_MISMATCH, "FeeQuote quantity differs from executable quantity"))
    if request.unit_price is None or quote.unit_price != request.unit_price:
        failures.append(_failure(NormalizationFailureReason.PRICE_QUOTE_MISMATCH, "FeeQuote price differs from normalized input"))
    if not request.currency or quote.currency != request.currency:
        failures.append(_failure(NormalizationFailureReason.CURRENCY_QUOTE_MISMATCH, "FeeQuote currency differs from normalized input"))


def _adjustments_explain_difference(request: TradeInputNormalizationRequest) -> bool:
    return any(
        summary.adjusted
        and summary.requested_quantity == request.requested_quantity
        and summary.executable_quantity == request.executable_quantity
        for summary in (request.lot_adjustment, request.fractional_adjustment)
    )


def _normalization_ref(request: TradeInputNormalizationRequest) -> str:
    facts = request.execution_instrument_facts
    quote = request.fee_quote
    parts = (
        _CONTRACT_VERSION,
        request.recommendation_reference or "",
        request.requested_symbol,
        request.side.value,
        _decimal_text(request.requested_quantity),
        _decimal_text(request.executable_quantity),
        _decimal_text(request.requested_value),
        request.quantity_source.value,
        request.quantity_confidence.value,
        _decimal_text(request.unit_price),
        request.price_kind.value,
        request.price_source.value,
        _datetime_text(request.observed_at),
        _datetime_text(request.received_at),
        request.market_session.value,
        _datetime_text(request.freshness_assessed_at),
        request.freshness_policy_reference or "",
        "" if request.stale is None else str(request.stale),
        request.currency or "",
        str(facts.asset_id or ""),
        facts.canonical_symbol or "",
        quote.quote_ref if quote is not None else "",
    )
    return "nti_" + hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:24]


def _shadow_contracts(
    symbol: str,
    facts_by_symbol: Mapping[str, ExecutionInstrumentFacts],
    eligibility_by_symbol: Mapping[str, ExecutionEligibility],
) -> tuple[ExecutionInstrumentFacts | None, ExecutionEligibility | None]:
    return facts_by_symbol.get(symbol), eligibility_by_symbol.get(symbol)


def _positive(value: Decimal) -> bool:
    return isinstance(value, Decimal) and value > Decimal("0")


def _failure(reason: NormalizationFailureReason, detail: str) -> NormalizationFailure:
    return NormalizationFailure(reason, detail)


def _deduplicate_failures(failures: Sequence[NormalizationFailure]) -> list[NormalizationFailure]:
    seen: set[tuple[NormalizationFailureReason, str]] = set()
    result: list[NormalizationFailure] = []
    for failure in failures:
        key = (failure.reason, failure.detail)
        if key not in seen:
            seen.add(key)
            result.append(failure)
    return result


def _decimal_text(value: Decimal | None) -> str:
    return format(value, "f") if isinstance(value, Decimal) else ""


def _datetime_text(value: datetime | None) -> str:
    return value.isoformat() if value is not None else ""
