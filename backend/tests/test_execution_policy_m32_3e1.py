"""Focused pure M32.3E1 policy and constrained-sizing shadow tests."""
from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from services.broker_fees import TradeSide, quote_fee_for_instrument
from services.execution_eligibility import evaluate_execution_eligibility
from services.execution_instrument_facts import (
    ExecutionFactProvenance,
    ExecutionInstrumentFacts,
    ExecutionInstrumentForm,
    ExecutionResolutionOutcome,
    ExecutionRole,
)
from services.execution_policy import (
    ExecutionFreshnessPolicy,
    ExecutionPolicyBundle,
    ExecutionPolicyOutcome,
    ExecutionPolicyReason,
    ExecutionPricingPolicy,
    ExecutionQuantityPolicy,
    ExecutionQuoteLifecycle,
    ExecutionResidualPolicy,
    ExecutionSizingPolicy,
    PlanningCurrencyContext,
    accept_freshness_and_session,
    calculate_execution_residual,
    constrain_executable_quantity,
    derive_requested_quantity,
    normalize_policy_trade_input,
    select_execution_price,
    validate_fee_quote_lifecycle,
)
from services.execution_price_observation import (
    MarketSession,
    PriceFreshnessPolicy,
    PriceKind,
    PriceSource,
    assess_price_freshness,
    build_price_observation,
)
from services.execution_trade_leg import (
    ExecutionFundingRole,
    ExecutionTradeLegBuilder,
    LegacyExecutionTradeRequest,
)
from services.normalized_trade_input import (
    HoldingQuantitySnapshot,
    QuantityIntentSource,
)


_OBSERVED = datetime(2026, 7, 15, 3, 0, tzinfo=timezone.utc)
_RECEIVED = _OBSERVED + timedelta(seconds=2)
_ASSESSED = _OBSERVED + timedelta(minutes=1)


def _facts(**overrides) -> ExecutionInstrumentFacts:
    values = dict(
        query="KBANK.BK",
        resolution_status=ExecutionResolutionOutcome.RESOLVED,
        instrument_form=ExecutionInstrumentForm.EQUITY,
        execution_role=ExecutionRole.TRADABLE,
        asset_id=42,
        canonical_symbol="KBANK.BK",
        exchange="SET",
        currency="THB",
        tradable=True,
        lot_size=100,
        fractional_support=False,
        provenance=(ExecutionFactProvenance("identity", "Registry", "42"),),
    )
    values.update(overrides)
    return ExecutionInstrumentFacts(**values)


def _observation(**overrides):
    values = dict(
        requested_symbol="KBANK.BK",
        asset_id=42,
        canonical_symbol="KBANK.BK",
        observed_price=Decimal("10"),
        price_type=PriceKind.MARKET_LAST,
        source=PriceSource.CALLER_SUPPLIED,
        currency="THB",
        provider="fixture",
        observed_at=_OBSERVED,
        received_at=_RECEIVED,
        market_session=MarketSession.REGULAR,
    )
    values.update(overrides)
    return build_price_observation(**values)


def _bundle():
    return ExecutionPolicyBundle.create(
        pricing=ExecutionPricingPolicy(policy_version="pricing-v1"),
        freshness=ExecutionFreshnessPolicy(
            policy_version="freshness-v1",
            current_for=timedelta(minutes=5),
            assessment_policy_version="freshness-v1",
        ),
        sizing=ExecutionSizingPolicy(policy_version="sizing-v1"),
        quantity=ExecutionQuantityPolicy(policy_version="quantity-v1"),
        residual=ExecutionResidualPolicy(policy_version="residual-v1"),
        quote_lifecycle=ExecutionQuoteLifecycle(policy_version="quote-v1"),
    )


def _assessment(observation, *, assessed_at=_ASSESSED):
    return assess_price_freshness(
        observation,
        assessed_at=assessed_at,
        policy=PriceFreshnessPolicy(
            policy_version="freshness-v1",
            current_for=timedelta(minutes=5),
            stale_for=timedelta(minutes=15),
        ),
    )


def _quote(facts, observation, *, side=TradeSide.BUY, quantity=Decimal("100")):
    return quote_fee_for_instrument(
        facts,
        side=side,
        quantity=quantity,
        unit_price=observation.observed_price,
        quoted_at=_RECEIVED,
        effective_at=_RECEIVED,
    )


def test_policy_contracts_are_frozen_versioned_and_bundle_ref_is_deterministic():
    bundle = _bundle()
    assert bundle.bundle_ref == _bundle().bundle_ref
    assert bundle.contract_version == "1"
    with pytest.raises(FrozenInstanceError):
        bundle.pricing.policy_version = "changed"  # type: ignore[misc]
    assert PlanningCurrencyContext.thb_transitional().currency == "THB"


def test_market_last_selection_requires_one_matching_thb_observation():
    facts, observation, bundle = _facts(), _observation(), _bundle()
    selected = select_execution_price((observation,), facts=facts,
        planning_currency=PlanningCurrencyContext.thb_transitional(), policy=bundle.pricing)
    assert selected.evaluation.ready and selected.observation is observation
    for changed in (
        replace(observation, price_type=PriceKind.MARKET_CLOSE),
        replace(observation, price_type=PriceKind.USER_EXECUTION_TERM),
        replace(observation, price_type=PriceKind.AVG_COST_REFERENCE),
        replace(observation, asset_id=99),
        replace(observation, currency="USD"),
    ):
        assert not select_execution_price((changed,), facts=facts,
            planning_currency=PlanningCurrencyContext.thb_transitional(), policy=bundle.pricing).evaluation.ready
    assert select_execution_price((observation, observation), facts=facts,
        planning_currency=PlanningCurrencyContext.thb_transitional(), policy=bundle.pricing).evaluation.reason == ExecutionPolicyReason.MULTIPLE_PRICE_OBSERVATIONS


def test_freshness_accepts_only_current_regular_using_caller_assessed_time():
    bundle, observation = _bundle(), _observation()
    assert accept_freshness_and_session(observation, _assessment(observation), policy=bundle.freshness).ready
    stale = _assessment(observation, assessed_at=_OBSERVED + timedelta(minutes=8))
    assert accept_freshness_and_session(observation, stale, policy=bundle.freshness).outcome == ExecutionPolicyOutcome.DEFERRED
    for session in (MarketSession.CLOSED, MarketSession.PRE_MARKET, MarketSession.AFTER_HOURS):
        assert accept_freshness_and_session(replace(observation, market_session=session), _assessment(observation),
            policy=bundle.freshness).outcome == ExecutionPolicyOutcome.DEFERRED
    assert accept_freshness_and_session(replace(observation, market_session=MarketSession.UNKNOWN), _assessment(observation),
        policy=bundle.freshness).outcome == ExecutionPolicyOutcome.INCOMPLETE
    assert "datetime.now" not in inspect.getsource(accept_freshness_and_session)


def test_quantity_derivation_capping_full_and_fraction_and_conflict():
    policy = _bundle().sizing
    holding = HoldingQuantitySnapshot(Decimal("150"), _ASSESSED, "fixture")
    buy = derive_requested_quantity(side=TradeSide.BUY,
        quantity_source=QuantityIntentSource.ALLOCATION_VALUE_AT_PRICE,
        requested_value=Decimal("1050"), selected_price=Decimal("10"), policy=policy)
    assert buy.requested_quantity == Decimal("105")
    reduce = derive_requested_quantity(side=TradeSide.SELL,
        quantity_source=QuantityIntentSource.REDUCTION_VALUE_AT_PRICE,
        requested_value=Decimal("2000"), selected_price=Decimal("10"), holding_snapshot=holding, policy=policy)
    assert reduce.requested_quantity == Decimal("150")
    full = derive_requested_quantity(side=TradeSide.SELL,
        quantity_source=QuantityIntentSource.FULL_HOLDING_QUANTITY,
        requested_value=None, selected_price=None, holding_snapshot=holding, policy=policy)
    assert full.requested_quantity == Decimal("150")
    fraction = derive_requested_quantity(side=TradeSide.SELL,
        quantity_source=QuantityIntentSource.HOLDING_FRACTION,
        requested_value=None, selected_price=None, holding_snapshot=holding, holding_fraction=Decimal("0.5"), policy=policy)
    assert fraction.requested_quantity == Decimal("75")
    conflict = derive_requested_quantity(side=TradeSide.SELL,
        quantity_source=QuantityIntentSource.REDUCTION_VALUE_AT_PRICE, requested_value=Decimal("1"),
        selected_price=Decimal("1"), holding_snapshot=holding,
        competing_quantity_source=QuantityIntentSource.HOLDING_FRACTION, policy=policy)
    assert conflict.evaluation.reason == ExecutionPolicyReason.CONFLICTING_QUANTITY_INTENT


def test_quantity_constraint_requires_explicit_non_fractional_positive_lot_and_floors_only():
    facts, policy = _facts(), _bundle().quantity
    constrained = constrain_executable_quantity(requested_quantity=Decimal("250"),
        quantity_source=QuantityIntentSource.ALLOCATION_VALUE_AT_PRICE, facts=facts, holding_snapshot=None, policy=policy)
    assert constrained.executable_quantity == Decimal("200")
    assert constrained.lot_adjustment and constrained.lot_adjustment.adjusted
    assert constrain_executable_quantity(requested_quantity=Decimal("99"),
        quantity_source=QuantityIntentSource.ALLOCATION_VALUE_AT_PRICE, facts=facts, holding_snapshot=None,
        policy=policy).evaluation.outcome == ExecutionPolicyOutcome.DEFERRED_BELOW_EXECUTABLE_LOT
    assert constrain_executable_quantity(requested_quantity=Decimal("100"),
        quantity_source=QuantityIntentSource.ALLOCATION_VALUE_AT_PRICE, facts=replace(facts, lot_size=None),
        holding_snapshot=None, policy=policy).evaluation.reason == ExecutionPolicyReason.MISSING_LOT_SIZE
    assert constrain_executable_quantity(requested_quantity=Decimal("100"),
        quantity_source=QuantityIntentSource.ALLOCATION_VALUE_AT_PRICE, facts=replace(facts, fractional_support=True),
        holding_snapshot=None, policy=policy).evaluation.reason == ExecutionPolicyReason.FRACTIONAL_CAPABILITY_UNSUPPORTED
    assert constrain_executable_quantity(requested_quantity=Decimal("150"),
        quantity_source=QuantityIntentSource.FULL_HOLDING_QUANTITY, facts=facts,
        holding_snapshot=HoldingQuantitySnapshot(Decimal("150"), _ASSESSED, "fixture"),
        policy=policy).evaluation.reason == ExecutionPolicyReason.FULL_SELL_ODD_LOT


def test_residuals_are_exact_and_never_redistributed():
    result = calculate_execution_residual(requested_quantity=Decimal("250"), executable_quantity=Decimal("200"),
        requested_value=Decimal("2500"), selected_price=Decimal("10"), policy=_bundle().residual)
    assert result.quantity_residual == Decimal("50")
    assert result.gross_value_residual == Decimal("500")
    assert not _bundle().residual.redistribute_residual


def test_quote_lifecycle_binds_exact_constrained_inputs_and_expires_with_freshness():
    facts, observation, bundle = _facts(), _observation(), _bundle()
    assessment, quote = _assessment(observation), _quote(facts, observation)
    ready = validate_fee_quote_lifecycle(quote, facts=facts, side=TradeSide.BUY, quantity=Decimal("100"),
        observation=observation, assessment=assessment, planning_currency=PlanningCurrencyContext.thb_transitional(),
        pricing_policy=bundle.pricing, freshness_policy=bundle.freshness, lifecycle=bundle.quote_lifecycle)
    assert ready.evaluation.ready and ready.expires_at == _OBSERVED + timedelta(minutes=5)
    assert validate_fee_quote_lifecycle(replace(quote, quantity=Decimal("200")), facts=facts, side=TradeSide.BUY,
        quantity=Decimal("100"), observation=observation, assessment=assessment,
        planning_currency=PlanningCurrencyContext.thb_transitional(), pricing_policy=bundle.pricing,
        freshness_policy=bundle.freshness, lifecycle=bundle.quote_lifecycle).evaluation.reason == ExecutionPolicyReason.FEE_QUOTE_INVALIDATED
    assert validate_fee_quote_lifecycle(quote, facts=facts, side=TradeSide.BUY, quantity=Decimal("100"),
        observation=observation, assessment=_assessment(observation, assessed_at=_OBSERVED + timedelta(minutes=20)),
        planning_currency=PlanningCurrencyContext.thb_transitional(), pricing_policy=bundle.pricing,
        freshness_policy=bundle.freshness, lifecycle=bundle.quote_lifecycle).evaluation.reason == ExecutionPolicyReason.FEE_QUOTE_EXPIRED


def test_policy_normalized_input_and_policy_trade_leg_retain_object_identity():
    facts, observation, bundle = _facts(), _observation(), _bundle()
    quote = _quote(facts, observation, quantity=Decimal("100"))
    result = normalize_policy_trade_input(recommendation_reference="fixture", requested_symbol="KBANK.BK",
        side=TradeSide.BUY, quantity_source=QuantityIntentSource.ALLOCATION_VALUE_AT_PRICE, facts=facts,
        eligibility=evaluate_execution_eligibility(facts), observations=(observation,), freshness_assessment=_assessment(observation),
        planning_currency=PlanningCurrencyContext.thb_transitional(), policy_bundle=bundle, fee_quote=quote,
        requested_value=Decimal("1050"))
    assert result.evaluation.ready and result.normalization and result.normalization.complete
    normalized = result.normalized_input
    assert normalized is not None and normalized.execution_instrument_facts is facts
    assert normalized.price_observation is observation and normalized.fee_quote is quote
    leg = ExecutionTradeLegBuilder().build_from_policy_input(normalized, funding_role=ExecutionFundingRole.DEPLOYMENT)
    assert leg.execution_instrument_facts is facts and leg.fee_quote is quote
    assert leg.price_observation is observation and leg.complete


def test_policy_path_never_promotes_incomplete_or_changes_legacy_builder_contract():
    facts, observation, bundle = _facts(), _observation(), _bundle()
    incomplete = normalize_policy_trade_input(recommendation_reference=None, requested_symbol="KBANK.BK",
        side=TradeSide.BUY, quantity_source=QuantityIntentSource.ALLOCATION_VALUE_AT_PRICE, facts=facts,
        eligibility=evaluate_execution_eligibility(facts), observations=(observation,), freshness_assessment=_assessment(observation),
        planning_currency=PlanningCurrencyContext.thb_transitional(), policy_bundle=bundle, fee_quote=None,
        requested_value=Decimal("1000"))
    assert incomplete.evaluation.reason == ExecutionPolicyReason.FEE_QUOTE_UNAVAILABLE
    old = ExecutionTradeLegBuilder().build
    assert "LegacyExecutionTradeRequest" in str(inspect.signature(old))
    for source in (select_execution_price, derive_requested_quantity, constrain_executable_quantity,
                   validate_fee_quote_lifecycle, normalize_policy_trade_input):
        body = inspect.getsource(source)
        assert "Session" not in body and "os.environ" not in body and "datetime.now" not in body
