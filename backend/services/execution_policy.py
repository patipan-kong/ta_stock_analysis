"""Pure M32.3E1 execution-policy contracts and constrained-sizing shadow.

This module is deliberately a policy/evidence boundary.  It accepts immutable
objects assembled by an orchestration caller and neither loads nor authors
facts, prices, quotes, time, configuration, or portfolio state.  Its results
are suitable only for the M32 shadow path until a later milestone explicitly
adopts a canonical plan.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_FLOOR
from enum import Enum
from typing import Sequence

from services.broker_fees import FeeQuote, FeeQuoteStatus, TradeSide
from services.execution_eligibility import ExecutionEligibility
from services.execution_instrument_facts import ExecutionInstrumentFacts
from services.execution_price_observation import (
    ExecutionPriceObservation,
    MarketSession,
    PriceFreshnessAssessment,
    PriceFreshnessStatus,
    PriceKind,
)
from services.normalized_trade_input import (
    HoldingQuantitySnapshot,
    NormalizationResult,
    QuantityAdjustmentSummary,
    QuantityConfidence,
    QuantityIntentSource,
    TradeInputNormalizationRequest,
    normalize_trade_input,
)

__all__ = [
    "ExecutionPricingPolicy",
    "ExecutionFreshnessPolicy",
    "ExecutionSizingPolicy",
    "ExecutionQuantityPolicy",
    "ExecutionResidualPolicy",
    "ExecutionQuoteLifecycle",
    "ExecutionPolicyBundle",
    "PlanningCurrencyContext",
    "ExecutionPolicyOutcome",
    "ExecutionPolicyReason",
    "PolicyEvaluation",
    "PriceSelectionResult",
    "QuantityDerivationResult",
    "QuantityConstraintResult",
    "ResidualResult",
    "FeeQuoteLifecycleResult",
    "PolicyProducedNormalizedInput",
    "select_execution_price",
    "accept_freshness_and_session",
    "derive_requested_quantity",
    "constrain_executable_quantity",
    "calculate_execution_residual",
    "validate_fee_quote_lifecycle",
    "normalize_policy_trade_input",
]


_CONTRACT_VERSION = "1"


class ExecutionPolicyOutcome(str, Enum):
    READY = "READY"
    DEFERRED = "DEFERRED"
    DEFERRED_BELOW_EXECUTABLE_LOT = "DEFERRED_BELOW_EXECUTABLE_LOT"
    INCOMPLETE = "INCOMPLETE"
    EXCLUDED = "EXCLUDED"
    ERROR = "ERROR"


class ExecutionPolicyReason(str, Enum):
    UNSUPPORTED_PRICE_KIND = "UNSUPPORTED_PRICE_KIND"
    MULTIPLE_PRICE_OBSERVATIONS = "MULTIPLE_PRICE_OBSERVATIONS"
    PRICE_MISSING = "PRICE_MISSING"
    PRICE_NON_POSITIVE = "PRICE_NON_POSITIVE"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    CURRENCY_MISMATCH = "CURRENCY_MISMATCH"
    NON_CURRENT_FRESHNESS = "NON_CURRENT_FRESHNESS"
    FRESHNESS_POLICY_MISMATCH = "FRESHNESS_POLICY_MISMATCH"
    FRESHNESS_EXPIRED = "FRESHNESS_EXPIRED"
    UNSUPPORTED_SESSION = "UNSUPPORTED_SESSION"
    SESSION_UNKNOWN = "SESSION_UNKNOWN"
    INELIGIBLE_INSTRUMENT = "INELIGIBLE_INSTRUMENT"
    MISSING_HOLDING_SNAPSHOT = "MISSING_HOLDING_SNAPSHOT"
    INVALID_HOLDING_QUANTITY = "INVALID_HOLDING_QUANTITY"
    INVALID_REQUESTED_VALUE = "INVALID_REQUESTED_VALUE"
    INVALID_SOURCE_SIDE = "INVALID_SOURCE_SIDE"
    CONFLICTING_QUANTITY_INTENT = "CONFLICTING_QUANTITY_INTENT"
    MANUAL_INTENT_NOT_CANONICAL = "MANUAL_INTENT_NOT_CANONICAL"
    MISSING_LOT_SIZE = "MISSING_LOT_SIZE"
    INVALID_LOT_SIZE = "INVALID_LOT_SIZE"
    FRACTIONAL_CAPABILITY_UNSUPPORTED = "FRACTIONAL_CAPABILITY_UNSUPPORTED"
    FULL_SELL_ODD_LOT = "FULL_SELL_ODD_LOT"
    OVERSELL = "OVERSELL"
    ZERO_CONSTRAINED_QUANTITY = "ZERO_CONSTRAINED_QUANTITY"
    FEE_QUOTE_UNAVAILABLE = "FEE_QUOTE_UNAVAILABLE"
    FEE_QUOTE_INVALIDATED = "FEE_QUOTE_INVALIDATED"
    FEE_QUOTE_EXPIRED = "FEE_QUOTE_EXPIRED"


@dataclass(frozen=True)
class ExecutionPricingPolicy:
    policy_version: str
    accepted_price_kind: PriceKind = PriceKind.MARKET_LAST
    required_currency: str = "THB"
    require_identity_match: bool = True


@dataclass(frozen=True)
class ExecutionFreshnessPolicy:
    policy_version: str
    current_for: timedelta
    accepted_freshness: PriceFreshnessStatus = PriceFreshnessStatus.CURRENT
    accepted_session: MarketSession = MarketSession.REGULAR
    assessment_policy_version: str | None = None


@dataclass(frozen=True)
class ExecutionSizingPolicy:
    policy_version: str
    planning_currency: str = "THB"
    allow_manual_quantity_as_canonical: bool = False
    allow_reduce_value_fraction_fallback: bool = False


@dataclass(frozen=True)
class ExecutionQuantityPolicy:
    policy_version: str
    require_non_fractional: bool = True
    value_derived_rounding: str = "FLOOR_TO_LOT"
    full_sell_requires_lot_alignment: bool = True
    allow_partial_scaling: bool = False


@dataclass(frozen=True)
class ExecutionResidualPolicy:
    policy_version: str
    redistribute_residual: bool = False
    rounding_mode: str = "FLOOR_TO_LOT"


@dataclass(frozen=True)
class ExecutionQuoteLifecycle:
    policy_version: str
    require_requote_at_transaction_admission: bool = True
    independent_quote_ttl: timedelta | None = None


@dataclass(frozen=True)
class ExecutionPolicyBundle:
    """The complete frozen policy supplied to one pure sizing evaluation."""

    contract_version: str
    bundle_ref: str
    pricing: ExecutionPricingPolicy
    freshness: ExecutionFreshnessPolicy
    sizing: ExecutionSizingPolicy
    quantity: ExecutionQuantityPolicy
    residual: ExecutionResidualPolicy
    quote_lifecycle: ExecutionQuoteLifecycle

    @classmethod
    def create(
        cls,
        *,
        pricing: ExecutionPricingPolicy,
        freshness: ExecutionFreshnessPolicy,
        sizing: ExecutionSizingPolicy,
        quantity: ExecutionQuantityPolicy,
        residual: ExecutionResidualPolicy,
        quote_lifecycle: ExecutionQuoteLifecycle,
    ) -> "ExecutionPolicyBundle":
        parts = (
            _CONTRACT_VERSION,
            pricing.policy_version,
            pricing.accepted_price_kind.value,
            pricing.required_currency,
            freshness.policy_version,
            _timedelta_text(freshness.current_for),
            freshness.accepted_freshness.value,
            freshness.accepted_session.value,
            freshness.assessment_policy_version or "",
            sizing.policy_version,
            sizing.planning_currency,
            str(sizing.allow_manual_quantity_as_canonical),
            str(sizing.allow_reduce_value_fraction_fallback),
            quantity.policy_version,
            quantity.value_derived_rounding,
            str(quantity.require_non_fractional),
            str(quantity.full_sell_requires_lot_alignment),
            str(quantity.allow_partial_scaling),
            residual.policy_version,
            str(residual.redistribute_residual),
            residual.rounding_mode,
            quote_lifecycle.policy_version,
            str(quote_lifecycle.require_requote_at_transaction_admission),
            _timedelta_text(quote_lifecycle.independent_quote_ttl),
        )
        return cls(
            contract_version=_CONTRACT_VERSION,
            bundle_ref=_ref("epb", parts),
            pricing=pricing,
            freshness=freshness,
            sizing=sizing,
            quantity=quantity,
            residual=residual,
            quote_lifecycle=quote_lifecycle,
        )


@dataclass(frozen=True)
class PlanningCurrencyContext:
    contract_version: str
    context_ref: str
    currency: str
    source: str

    @classmethod
    def thb_transitional(cls, *, source: str = "M32.3E1 transitional THB-only planning") -> "PlanningCurrencyContext":
        return cls.create(currency="THB", source=source)

    @classmethod
    def create(cls, *, currency: str, source: str) -> "PlanningCurrencyContext":
        return cls(
            contract_version=_CONTRACT_VERSION,
            context_ref=_ref("epc", (_CONTRACT_VERSION, currency, source)),
            currency=currency,
            source=source,
        )


@dataclass(frozen=True)
class PolicyEvaluation:
    outcome: ExecutionPolicyOutcome
    reason: ExecutionPolicyReason | None
    detail: str
    result_ref: str

    @property
    def ready(self) -> bool:
        return self.outcome == ExecutionPolicyOutcome.READY


@dataclass(frozen=True)
class PriceSelectionResult:
    evaluation: PolicyEvaluation
    observation: ExecutionPriceObservation | None


@dataclass(frozen=True)
class QuantityDerivationResult:
    evaluation: PolicyEvaluation
    requested_quantity: Decimal | None
    confidence: QuantityConfidence | None


@dataclass(frozen=True)
class QuantityConstraintResult:
    evaluation: PolicyEvaluation
    requested_quantity: Decimal | None
    executable_quantity: Decimal | None
    lot_adjustment: QuantityAdjustmentSummary | None
    fractional_adjustment: QuantityAdjustmentSummary | None


@dataclass(frozen=True)
class ResidualResult:
    evaluation: PolicyEvaluation
    quantity_residual: Decimal | None
    gross_value_residual: Decimal | None
    policy_version: str


@dataclass(frozen=True)
class FeeQuoteLifecycleResult:
    evaluation: PolicyEvaluation
    fee_quote: FeeQuote | None
    expires_at: datetime | None
    bound_asset_id: int | None
    bound_schedule_id: str | None
    bound_schedule_version: str | None


@dataclass(frozen=True)
class PolicyProducedNormalizedInput:
    """Private result joining policy decisions to the existing normalizer."""

    evaluation: PolicyEvaluation
    normalization: NormalizationResult | None
    price_selection: PriceSelectionResult
    quantity_derivation: QuantityDerivationResult
    quantity_constraint: QuantityConstraintResult
    residual: ResidualResult | None
    quote_lifecycle: FeeQuoteLifecycleResult | None
    policy_bundle: ExecutionPolicyBundle

    @property
    def normalized_input(self):
        return self.normalization.normalized_input if self.normalization else None


def select_execution_price(
    observations: Sequence[ExecutionPriceObservation],
    *,
    facts: ExecutionInstrumentFacts,
    planning_currency: PlanningCurrencyContext,
    policy: ExecutionPricingPolicy,
) -> PriceSelectionResult:
    """Accept one exact, Registry-identity-matching MARKET_LAST observation."""

    if len(observations) != 1:
        return PriceSelectionResult(
            _evaluation(
                ExecutionPolicyOutcome.INCOMPLETE,
                ExecutionPolicyReason.MULTIPLE_PRICE_OBSERVATIONS,
                "execution pricing requires exactly one supplied observation",
                "price", policy.policy_version, str(len(observations)),
            ),
            None,
        )
    observation = observations[0]
    if observation.price_type != policy.accepted_price_kind:
        return PriceSelectionResult(_evaluation(
            ExecutionPolicyOutcome.INCOMPLETE, ExecutionPolicyReason.UNSUPPORTED_PRICE_KIND,
            f"{observation.price_type.value} is not accepted by {policy.policy_version}",
            "price", policy.policy_version, observation.observation_ref,
        ), None)
    if observation.observed_price is None:
        return PriceSelectionResult(_evaluation(
            ExecutionPolicyOutcome.INCOMPLETE, ExecutionPolicyReason.PRICE_MISSING,
            "selected observation has no price", "price", policy.policy_version, observation.observation_ref,
        ), None)
    if observation.observed_price <= 0:
        return PriceSelectionResult(_evaluation(
            ExecutionPolicyOutcome.INCOMPLETE, ExecutionPolicyReason.PRICE_NON_POSITIVE,
            "selected observation price must be positive", "price", policy.policy_version, observation.observation_ref,
        ), None)
    if observation.currency != policy.required_currency or observation.currency != planning_currency.currency:
        return PriceSelectionResult(_evaluation(
            ExecutionPolicyOutcome.INCOMPLETE, ExecutionPolicyReason.CURRENCY_MISMATCH,
            "observation currency must equal the explicit pricing and planning currencies",
            "price", policy.policy_version, observation.observation_ref, observation.currency or "",
        ), None)
    if policy.require_identity_match and not _identity_matches(observation, facts):
        return PriceSelectionResult(_evaluation(
            ExecutionPolicyOutcome.INCOMPLETE, ExecutionPolicyReason.IDENTITY_MISMATCH,
            "price observation identity does not exactly match Registry facts",
            "price", policy.policy_version, observation.observation_ref,
        ), None)
    return PriceSelectionResult(_evaluation(
        ExecutionPolicyOutcome.READY, None, "one exact MARKET_LAST observation is selected",
        "price", policy.policy_version, observation.observation_ref,
    ), observation)


def accept_freshness_and_session(
    observation: ExecutionPriceObservation,
    assessment: PriceFreshnessAssessment,
    *,
    policy: ExecutionFreshnessPolicy,
) -> PolicyEvaluation:
    """Validate caller-assessed freshness without reading a clock or cache TTL."""

    if assessment.observation_ref != observation.observation_ref:
        return _evaluation(ExecutionPolicyOutcome.INCOMPLETE, ExecutionPolicyReason.IDENTITY_MISMATCH,
            "freshness assessment belongs to a different observation", "freshness", policy.policy_version,
            observation.observation_ref, assessment.assessment_ref)
    if policy.assessment_policy_version and assessment.policy_version != policy.assessment_policy_version:
        return _evaluation(ExecutionPolicyOutcome.INCOMPLETE, ExecutionPolicyReason.FRESHNESS_POLICY_MISMATCH,
            "freshness assessment policy version does not match the execution policy", "freshness",
            policy.policy_version, assessment.policy_version)
    if observation.market_session == MarketSession.UNKNOWN:
        return _evaluation(ExecutionPolicyOutcome.INCOMPLETE, ExecutionPolicyReason.SESSION_UNKNOWN,
            "market session is unknown", "freshness", policy.policy_version, observation.observation_ref)
    if observation.market_session != policy.accepted_session:
        return _evaluation(ExecutionPolicyOutcome.DEFERRED, ExecutionPolicyReason.UNSUPPORTED_SESSION,
            f"{observation.market_session.value} is not an accepted execution session", "freshness",
            policy.policy_version, observation.observation_ref)
    if assessment.status == PriceFreshnessStatus.EXPIRED:
        return _evaluation(ExecutionPolicyOutcome.DEFERRED, ExecutionPolicyReason.FRESHNESS_EXPIRED,
            assessment.reason, "freshness", policy.policy_version, assessment.assessment_ref)
    if assessment.status != policy.accepted_freshness:
        return _evaluation(ExecutionPolicyOutcome.DEFERRED, ExecutionPolicyReason.NON_CURRENT_FRESHNESS,
            assessment.reason, "freshness", policy.policy_version, assessment.assessment_ref)
    if observation.observed_at is None or assessment.age is None or assessment.age > policy.current_for:
        return _evaluation(ExecutionPolicyOutcome.DEFERRED, ExecutionPolicyReason.NON_CURRENT_FRESHNESS,
            "caller-supplied assessment is not within the execution current_for threshold", "freshness",
            policy.policy_version, observation.observation_ref)
    return _evaluation(ExecutionPolicyOutcome.READY, None, "price freshness and session are accepted",
        "freshness", policy.policy_version, observation.observation_ref, assessment.assessment_ref)


def derive_requested_quantity(
    *,
    side: TradeSide,
    quantity_source: QuantityIntentSource,
    requested_value: Decimal | None,
    selected_price: Decimal | None,
    holding_snapshot: HoldingQuantitySnapshot | None = None,
    holding_fraction: Decimal | None = None,
    competing_quantity_source: QuantityIntentSource | None = None,
    primary_quantity_source: QuantityIntentSource | None = None,
    policy: ExecutionSizingPolicy,
) -> QuantityDerivationResult:
    """Derive a requested quantity from supplied intent only; never constrain it."""

    if competing_quantity_source is not None and primary_quantity_source is None:
        return QuantityDerivationResult(_evaluation(
            ExecutionPolicyOutcome.ERROR, ExecutionPolicyReason.CONFLICTING_QUANTITY_INTENT,
            "conflicting quantity intent has no explicitly designated primary source", "sizing",
            policy.policy_version, quantity_source.value, competing_quantity_source.value,
        ), None, None)
    if primary_quantity_source is not None and primary_quantity_source != quantity_source:
        return QuantityDerivationResult(_evaluation(
            ExecutionPolicyOutcome.ERROR, ExecutionPolicyReason.CONFLICTING_QUANTITY_INTENT,
            "this quantity source is not the explicit primary source", "sizing", policy.policy_version,
            quantity_source.value, primary_quantity_source.value,
        ), None, None)
    if quantity_source == QuantityIntentSource.EXPLICIT_USER_QUANTITY:
        return QuantityDerivationResult(_evaluation(
            ExecutionPolicyOutcome.INCOMPLETE, ExecutionPolicyReason.MANUAL_INTENT_NOT_CANONICAL,
            "manual quantity intent is retained but not canonical recommendation sizing", "sizing",
            policy.policy_version,
        ), None, None)
    if quantity_source == QuantityIntentSource.ALLOCATION_VALUE_AT_PRICE:
        if side != TradeSide.BUY:
            return _invalid_source_side(quantity_source, side, policy)
        return _derive_value_quantity(requested_value, selected_price, policy, cap=None)
    if quantity_source == QuantityIntentSource.REDUCTION_VALUE_AT_PRICE:
        if side != TradeSide.SELL:
            return _invalid_source_side(quantity_source, side, policy)
        if holding_snapshot is None or holding_snapshot.quantity <= 0:
            return _missing_or_invalid_holding(holding_snapshot, policy)
        return _derive_value_quantity(requested_value, selected_price, policy, cap=holding_snapshot.quantity)
    if quantity_source == QuantityIntentSource.FULL_HOLDING_QUANTITY:
        if side != TradeSide.SELL:
            return _invalid_source_side(quantity_source, side, policy)
        if holding_snapshot is None or holding_snapshot.quantity <= 0:
            return _missing_or_invalid_holding(holding_snapshot, policy)
        return QuantityDerivationResult(_evaluation(
            ExecutionPolicyOutcome.READY, None, "full holding quantity is retained exactly", "sizing",
            policy.policy_version, _decimal_text(holding_snapshot.quantity),
        ), holding_snapshot.quantity, QuantityConfidence.EXACT)
    if quantity_source == QuantityIntentSource.HOLDING_FRACTION:
        if side != TradeSide.SELL:
            return _invalid_source_side(quantity_source, side, policy)
        if holding_snapshot is None or holding_snapshot.quantity <= 0:
            return _missing_or_invalid_holding(holding_snapshot, policy)
        if holding_fraction is None or holding_fraction <= 0 or holding_fraction > 1:
            return QuantityDerivationResult(_evaluation(
                ExecutionPolicyOutcome.INCOMPLETE, ExecutionPolicyReason.INVALID_REQUESTED_VALUE,
                "holding fraction must be in (0, 1]", "sizing", policy.policy_version,
            ), None, None)
        return QuantityDerivationResult(_evaluation(
            ExecutionPolicyOutcome.READY, None, "holding fraction quantity is derived from supplied snapshot",
            "sizing", policy.policy_version, _decimal_text(holding_fraction),
        ), holding_snapshot.quantity * holding_fraction, QuantityConfidence.DERIVED)
    return QuantityDerivationResult(_evaluation(
        ExecutionPolicyOutcome.INCOMPLETE, ExecutionPolicyReason.INVALID_SOURCE_SIDE,
        "quantity source is not supported by canonical recommendation sizing", "sizing", policy.policy_version,
        quantity_source.value,
    ), None, None)


def constrain_executable_quantity(
    *,
    requested_quantity: Decimal | None,
    quantity_source: QuantityIntentSource,
    facts: ExecutionInstrumentFacts,
    holding_snapshot: HoldingQuantitySnapshot | None,
    policy: ExecutionQuantityPolicy,
) -> QuantityConstraintResult:
    """Apply the approved lot policy without rounding up, scaling, or overselling."""

    if requested_quantity is None or requested_quantity <= 0:
        return _constraint_failure(ExecutionPolicyOutcome.INCOMPLETE, ExecutionPolicyReason.INVALID_REQUESTED_VALUE,
            "requested quantity must be positive", requested_quantity, facts, policy)
    if policy.require_non_fractional and facts.fractional_support is not False:
        return _constraint_failure(ExecutionPolicyOutcome.INCOMPLETE, ExecutionPolicyReason.FRACTIONAL_CAPABILITY_UNSUPPORTED,
            "fractional capability must be explicitly False in M32.3E1", requested_quantity, facts, policy)
    lot_size = facts.lot_size
    if lot_size is None:
        return _constraint_failure(ExecutionPolicyOutcome.INCOMPLETE, ExecutionPolicyReason.MISSING_LOT_SIZE,
            "Registry lot_size is absent and never defaults to one", requested_quantity, facts, policy)
    if not isinstance(lot_size, int) or isinstance(lot_size, bool) or lot_size <= 0:
        return _constraint_failure(ExecutionPolicyOutcome.INCOMPLETE, ExecutionPolicyReason.INVALID_LOT_SIZE,
            "Registry lot_size must be a positive integer", requested_quantity, facts, policy)
    if holding_snapshot is not None and requested_quantity > holding_snapshot.quantity:
        return _constraint_failure(ExecutionPolicyOutcome.ERROR, ExecutionPolicyReason.OVERSELL,
            "requested sell quantity exceeds supplied holding snapshot", requested_quantity, facts, policy)

    full_sell = quantity_source == QuantityIntentSource.FULL_HOLDING_QUANTITY
    if full_sell and policy.full_sell_requires_lot_alignment and requested_quantity % Decimal(lot_size) != 0:
        return _constraint_failure(ExecutionPolicyOutcome.INCOMPLETE, ExecutionPolicyReason.FULL_SELL_ODD_LOT,
            "full sell quantity is not lot-aligned", requested_quantity, facts, policy)
    value_or_fraction = quantity_source in {
        QuantityIntentSource.ALLOCATION_VALUE_AT_PRICE,
        QuantityIntentSource.REDUCTION_VALUE_AT_PRICE,
        QuantityIntentSource.HOLDING_FRACTION,
    }
    executable = (
        (requested_quantity / Decimal(lot_size)).to_integral_value(rounding=ROUND_FLOOR) * Decimal(lot_size)
        if value_or_fraction else requested_quantity
    )
    if executable <= 0:
        return _constraint_failure(ExecutionPolicyOutcome.DEFERRED_BELOW_EXECUTABLE_LOT,
            ExecutionPolicyReason.ZERO_CONSTRAINED_QUANTITY,
            "requested quantity is below one executable lot", requested_quantity, facts, policy,
            executable_quantity=Decimal("0"))
    lot_adjustment = QuantityAdjustmentSummary(
        requested_quantity=requested_quantity,
        executable_quantity=executable,
        residual_quantity=requested_quantity - executable,
        policy_reference=policy.policy_version,
        adjusted=executable != requested_quantity,
        reason="FLOOR_TO_LOT" if executable != requested_quantity else "LOT_ALIGNED",
    )
    fractional_adjustment = QuantityAdjustmentSummary(
        requested_quantity=requested_quantity,
        executable_quantity=executable,
        residual_quantity=requested_quantity - executable,
        policy_reference=policy.policy_version,
        adjusted=False,
        reason="NON_FRACTIONAL_REQUIRED",
    )
    return QuantityConstraintResult(_evaluation(
        ExecutionPolicyOutcome.READY, None, "quantity is executable under the supplied lot policy", "quantity",
        policy.policy_version, _decimal_text(requested_quantity), _decimal_text(executable), str(lot_size),
    ), requested_quantity, executable, lot_adjustment, fractional_adjustment)


def calculate_execution_residual(
    *,
    requested_quantity: Decimal | None,
    executable_quantity: Decimal | None,
    requested_value: Decimal | None,
    selected_price: Decimal | None,
    policy: ExecutionResidualPolicy,
) -> ResidualResult:
    """Return exact per-leg residual evidence; it never redistributes value."""

    if requested_quantity is None or executable_quantity is None:
        return ResidualResult(_evaluation(ExecutionPolicyOutcome.INCOMPLETE, ExecutionPolicyReason.INVALID_REQUESTED_VALUE,
            "residual requires requested and executable quantities", "residual", policy.policy_version),
            None, None, policy.policy_version)
    quantity_residual = requested_quantity - executable_quantity
    gross_value_residual = None
    if requested_value is not None:
        if selected_price is None or selected_price <= 0:
            return ResidualResult(_evaluation(ExecutionPolicyOutcome.INCOMPLETE, ExecutionPolicyReason.PRICE_MISSING,
                "gross value residual requires selected positive price", "residual", policy.policy_version),
                quantity_residual, None, policy.policy_version)
        gross_value_residual = requested_value - (executable_quantity * selected_price)
    return ResidualResult(_evaluation(ExecutionPolicyOutcome.READY, None,
        "per-leg residual retained without redistribution", "residual", policy.policy_version,
        _decimal_text(quantity_residual), _decimal_text(gross_value_residual)),
        quantity_residual, gross_value_residual, policy.policy_version)


def validate_fee_quote_lifecycle(
    quote: FeeQuote | None,
    *,
    facts: ExecutionInstrumentFacts,
    side: TradeSide,
    quantity: Decimal | None,
    observation: ExecutionPriceObservation,
    assessment: PriceFreshnessAssessment,
    planning_currency: PlanningCurrencyContext,
    pricing_policy: ExecutionPricingPolicy,
    freshness_policy: ExecutionFreshnessPolicy,
    lifecycle: ExecutionQuoteLifecycle,
) -> FeeQuoteLifecycleResult:
    """Bind a supplied quote to final constrained evidence; never re-quote."""

    if quote is None or quote.status != FeeQuoteStatus.QUOTED:
        return FeeQuoteLifecycleResult(_evaluation(ExecutionPolicyOutcome.INCOMPLETE,
            ExecutionPolicyReason.FEE_QUOTE_UNAVAILABLE, "no successful FeeQuote is supplied", "quote",
            lifecycle.policy_version), quote, None, None, None, None)
    mismatch = (
        quote.side != side
        or quote.quantity != quantity
        or quote.unit_price != observation.observed_price
        or quote.currency != observation.currency
        or quote.currency != planning_currency.currency
        or quote.schedule_version is None
        or facts.asset_id is None
        or observation.asset_id != facts.asset_id
        or observation.price_type != pricing_policy.accepted_price_kind
        or observation.currency != pricing_policy.required_currency
    )
    if mismatch:
        return FeeQuoteLifecycleResult(_evaluation(ExecutionPolicyOutcome.INCOMPLETE,
            ExecutionPolicyReason.FEE_QUOTE_INVALIDATED,
            "FeeQuote does not bind the exact side, quantity, price, currency, identity, and schedule version",
            "quote", lifecycle.policy_version, quote.quote_ref), quote, None,
            int(facts.asset_id) if facts.asset_id is not None else None,
            quote.schedule_id, quote.schedule_version)
    if observation.observed_at is None:
        return FeeQuoteLifecycleResult(_evaluation(ExecutionPolicyOutcome.INCOMPLETE,
            ExecutionPolicyReason.FEE_QUOTE_INVALIDATED, "quote has no bound price observation timestamp", "quote",
            lifecycle.policy_version, quote.quote_ref), quote, None,
            int(facts.asset_id) if facts.asset_id is not None else None,
            quote.schedule_id, quote.schedule_version)
    expires_at = observation.observed_at + freshness_policy.current_for
    if assessment.assessed_at > expires_at or assessment.status == PriceFreshnessStatus.EXPIRED:
        return FeeQuoteLifecycleResult(_evaluation(ExecutionPolicyOutcome.DEFERRED,
            ExecutionPolicyReason.FEE_QUOTE_EXPIRED, "price freshness window has expired", "quote",
            lifecycle.policy_version, quote.quote_ref), quote, expires_at,
            int(facts.asset_id) if facts.asset_id is not None else None,
            quote.schedule_id, quote.schedule_version)
    if quote.quoted_at > expires_at or quote.effective_at > expires_at:
        return FeeQuoteLifecycleResult(_evaluation(ExecutionPolicyOutcome.DEFERRED,
            ExecutionPolicyReason.FEE_QUOTE_EXPIRED, "FeeQuote time exceeds the price freshness window", "quote",
            lifecycle.policy_version, quote.quote_ref), quote, expires_at,
            int(facts.asset_id) if facts.asset_id is not None else None,
            quote.schedule_id, quote.schedule_version)
    return FeeQuoteLifecycleResult(_evaluation(ExecutionPolicyOutcome.READY, None,
        "FeeQuote is bound to final constrained trade evidence", "quote", lifecycle.policy_version,
        quote.quote_ref, facts.canonical_symbol or ""), quote, expires_at,
        int(facts.asset_id) if facts.asset_id is not None else None,
        quote.schedule_id, quote.schedule_version)


def normalize_policy_trade_input(
    *,
    recommendation_reference: str | None,
    requested_symbol: str,
    side: TradeSide,
    quantity_source: QuantityIntentSource,
    facts: ExecutionInstrumentFacts,
    eligibility: ExecutionEligibility,
    observations: Sequence[ExecutionPriceObservation],
    freshness_assessment: PriceFreshnessAssessment,
    planning_currency: PlanningCurrencyContext,
    policy_bundle: ExecutionPolicyBundle,
    fee_quote: FeeQuote | None,
    requested_value: Decimal | None = None,
    holding_snapshot: HoldingQuantitySnapshot | None = None,
    holding_fraction: Decimal | None = None,
    competing_quantity_source: QuantityIntentSource | None = None,
    primary_quantity_source: QuantityIntentSource | None = None,
    provenance: tuple[str, ...] = (),
) -> PolicyProducedNormalizedInput:
    """Create private policy-produced normalized evidence after all constraints.

    The exact FeeQuote is accepted only after the final constrained quantity is
    known.  This function does not select a schedule or calculate a quote.
    """

    price = select_execution_price(observations, facts=facts, planning_currency=planning_currency,
        policy=policy_bundle.pricing)
    if not price.evaluation.ready or price.observation is None:
        return _policy_input_failure(price.evaluation, price, policy_bundle)
    freshness = accept_freshness_and_session(price.observation, freshness_assessment,
        policy=policy_bundle.freshness)
    if not freshness.ready:
        return _policy_input_failure(freshness, price, policy_bundle)
    if not eligibility.eligible:
        return _policy_input_failure(_evaluation(ExecutionPolicyOutcome.EXCLUDED,
            ExecutionPolicyReason.INELIGIBLE_INSTRUMENT, eligibility.reason, "eligibility",
            policy_bundle.bundle_ref), price, policy_bundle)
    if facts.currency != planning_currency.currency:
        return _policy_input_failure(_evaluation(ExecutionPolicyOutcome.INCOMPLETE,
            ExecutionPolicyReason.CURRENCY_MISMATCH, "Registry listing currency differs from planning currency",
            "currency", policy_bundle.bundle_ref), price, policy_bundle)
    derivation = derive_requested_quantity(side=side, quantity_source=quantity_source,
        requested_value=requested_value, selected_price=price.observation.observed_price,
        holding_snapshot=holding_snapshot, holding_fraction=holding_fraction,
        competing_quantity_source=competing_quantity_source, primary_quantity_source=primary_quantity_source,
        policy=policy_bundle.sizing)
    if not derivation.evaluation.ready:
        return _policy_input_failure(derivation.evaluation, price, policy_bundle, derivation=derivation)
    constraint = constrain_executable_quantity(requested_quantity=derivation.requested_quantity,
        quantity_source=quantity_source, facts=facts, holding_snapshot=holding_snapshot,
        policy=policy_bundle.quantity)
    if not constraint.evaluation.ready:
        return _policy_input_failure(constraint.evaluation, price, policy_bundle, derivation=derivation,
            constraint=constraint)
    residual = calculate_execution_residual(requested_quantity=derivation.requested_quantity,
        executable_quantity=constraint.executable_quantity, requested_value=requested_value,
        selected_price=price.observation.observed_price, policy=policy_bundle.residual)
    lifecycle = validate_fee_quote_lifecycle(fee_quote, facts=facts, side=side,
        quantity=constraint.executable_quantity, observation=price.observation,
        assessment=freshness_assessment, planning_currency=planning_currency,
        pricing_policy=policy_bundle.pricing, freshness_policy=policy_bundle.freshness,
        lifecycle=policy_bundle.quote_lifecycle)
    if not lifecycle.evaluation.ready:
        return _policy_input_failure(lifecycle.evaluation, price, policy_bundle, derivation=derivation,
            constraint=constraint, residual=residual, lifecycle=lifecycle)
    assert constraint.lot_adjustment is not None
    assert constraint.fractional_adjustment is not None
    request = TradeInputNormalizationRequest(
        recommendation_reference=recommendation_reference,
        requested_symbol=requested_symbol,
        side=side,
        requested_quantity=derivation.requested_quantity,
        executable_quantity=constraint.executable_quantity,
        requested_value=requested_value,
        quantity_source=quantity_source,
        quantity_confidence=derivation.confidence or QuantityConfidence.DERIVED,
        lot_adjustment=constraint.lot_adjustment,
        fractional_adjustment=constraint.fractional_adjustment,
        unit_price=price.observation.observed_price,
        price_kind=price.observation.price_type,
        price_source=price.observation.source,
        observed_at=price.observation.observed_at,
        received_at=price.observation.received_at,
        market_session=price.observation.market_session,
        freshness_assessed_at=freshness_assessment.assessed_at,
        freshness_policy_reference=freshness_assessment.policy_version,
        stale=False,
        currency=planning_currency.currency,
        execution_instrument_facts=facts,
        execution_eligibility=eligibility,
        fee_quote=fee_quote,
        holding_quantity_snapshot=holding_snapshot,
        portfolio_currency=planning_currency.currency,
        valuation_currency=planning_currency.currency,
        provenance=("M32.3E1 policy-produced normalized input", policy_bundle.bundle_ref) + provenance,
        price_observation=price.observation,
        price_freshness_assessment=freshness_assessment,
        execution_policy_bundle_ref=policy_bundle.bundle_ref,
        execution_policy_result_ref=_ref("epi", (policy_bundle.bundle_ref, price.observation.observation_ref,
            lifecycle.evaluation.result_ref, _decimal_text(constraint.executable_quantity))),
    )
    normalization = normalize_trade_input(request)
    if not normalization.complete:
        evaluation = _evaluation(ExecutionPolicyOutcome.ERROR, ExecutionPolicyReason.FEE_QUOTE_INVALIDATED,
            "policy-produced normalized input failed existing evidence validation", "normalize",
            policy_bundle.bundle_ref, normalization.normalized_input.normalization_ref)
        return PolicyProducedNormalizedInput(evaluation, normalization, price, derivation, constraint,
            residual, lifecycle, policy_bundle)
    evaluation = _evaluation(ExecutionPolicyOutcome.READY, None, "policy-produced normalized input is complete",
        "normalize", policy_bundle.bundle_ref, normalization.normalized_input.normalization_ref)
    return PolicyProducedNormalizedInput(evaluation, normalization, price, derivation, constraint,
        residual, lifecycle, policy_bundle)


def _policy_input_failure(evaluation: PolicyEvaluation, price: PriceSelectionResult,
    bundle: ExecutionPolicyBundle, derivation: QuantityDerivationResult | None = None,
    constraint: QuantityConstraintResult | None = None, residual: ResidualResult | None = None,
    lifecycle: FeeQuoteLifecycleResult | None = None) -> PolicyProducedNormalizedInput:
    empty_derivation = derivation or QuantityDerivationResult(evaluation, None, None)
    return PolicyProducedNormalizedInput(evaluation, None, price, empty_derivation, constraint or
        QuantityConstraintResult(evaluation, None, None, None, None), residual, lifecycle, bundle)


def _derive_value_quantity(requested_value: Decimal | None, selected_price: Decimal | None,
    policy: ExecutionSizingPolicy, cap: Decimal | None) -> QuantityDerivationResult:
    if requested_value is None or requested_value <= 0:
        return QuantityDerivationResult(_evaluation(ExecutionPolicyOutcome.INCOMPLETE,
            ExecutionPolicyReason.INVALID_REQUESTED_VALUE, "requested value must be positive", "sizing",
            policy.policy_version), None, None)
    if selected_price is None or selected_price <= 0:
        return QuantityDerivationResult(_evaluation(ExecutionPolicyOutcome.INCOMPLETE,
            ExecutionPolicyReason.PRICE_MISSING, "selected positive price is required for value sizing", "sizing",
            policy.policy_version), None, None)
    quantity = requested_value / selected_price
    if cap is not None:
        quantity = min(quantity, cap)
    return QuantityDerivationResult(_evaluation(ExecutionPolicyOutcome.READY, None,
        "value amount is converted to requested quantity before lot constraint", "sizing", policy.policy_version,
        _decimal_text(quantity)), quantity, QuantityConfidence.DERIVED)


def _invalid_source_side(source: QuantityIntentSource, side: TradeSide,
    policy: ExecutionSizingPolicy) -> QuantityDerivationResult:
    return QuantityDerivationResult(_evaluation(ExecutionPolicyOutcome.INCOMPLETE,
        ExecutionPolicyReason.INVALID_SOURCE_SIDE, f"{source.value} is not valid for {side.value}", "sizing",
        policy.policy_version), None, None)


def _missing_or_invalid_holding(snapshot: HoldingQuantitySnapshot | None,
    policy: ExecutionSizingPolicy) -> QuantityDerivationResult:
    reason = ExecutionPolicyReason.MISSING_HOLDING_SNAPSHOT if snapshot is None else ExecutionPolicyReason.INVALID_HOLDING_QUANTITY
    return QuantityDerivationResult(_evaluation(ExecutionPolicyOutcome.INCOMPLETE, reason,
        "a positive immutable holding snapshot is required", "sizing", policy.policy_version), None, None)


def _constraint_failure(outcome: ExecutionPolicyOutcome, reason: ExecutionPolicyReason, detail: str,
    requested_quantity: Decimal | None, facts: ExecutionInstrumentFacts, policy: ExecutionQuantityPolicy,
    *, executable_quantity: Decimal | None = None) -> QuantityConstraintResult:
    return QuantityConstraintResult(_evaluation(outcome, reason, detail, "quantity", policy.policy_version,
        _decimal_text(requested_quantity), str(facts.lot_size)), requested_quantity, executable_quantity, None, None)


def _identity_matches(observation: ExecutionPriceObservation, facts: ExecutionInstrumentFacts) -> bool:
    return bool(
        observation.requested_symbol == facts.query
        and observation.asset_id is not None
        and facts.asset_id is not None
        and observation.asset_id == facts.asset_id
        and observation.canonical_symbol is not None
        and facts.canonical_symbol is not None
        and observation.canonical_symbol == facts.canonical_symbol
    )


def _evaluation(outcome: ExecutionPolicyOutcome, reason: ExecutionPolicyReason | None, detail: str,
    stage: str, policy_version: str, *parts: str) -> PolicyEvaluation:
    return PolicyEvaluation(outcome, reason, detail, _ref("epr", (
        _CONTRACT_VERSION, stage, policy_version, outcome.value, reason.value if reason else "", detail, *parts,
    )))


def _ref(prefix: str, parts: Sequence[str]) -> str:
    return prefix + "_" + hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:24]


def _decimal_text(value: Decimal | None) -> str:
    return "" if value is None else format(value, "f")


def _timedelta_text(value: timedelta | None) -> str:
    return "" if value is None else str(value.total_seconds())
