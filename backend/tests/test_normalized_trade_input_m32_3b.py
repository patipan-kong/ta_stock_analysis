"""Focused M32.3B normalized trade-input contracts and shadow-boundary tests."""
from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError, replace
from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models.asset  # noqa: F401 - include Registry tables in focused plan DB
import models.registry_finding  # noqa: F401 - include resolver finding table
from models.database import Base, Portfolio, Workspace
from services import execution_plan
from services.broker_fees import FeeQuoteStatus, TradeSide, quote_fee_for_instrument
from services.execution_eligibility import evaluate_execution_eligibility
from services.execution_instrument_facts import (
    ExecutionFactProvenance,
    ExecutionInstrumentFacts,
    ExecutionInstrumentForm,
    ExecutionResolutionOutcome,
    ExecutionRole,
)
from services.execution_trade_leg import (
    ExecutionFundingRole,
    ExecutionTradeLegBuilder,
    LegacyExecutionTradeRequest,
)
from services.normalized_trade_input import (
    AllocationSource,
    HoldingQuantitySnapshot,
    MarketSession,
    NormalizationFailureReason,
    NormalizationStatus,
    PriceKind,
    PriceSource,
    QuantityAdjustmentSummary,
    QuantityConfidence,
    QuantityIntentSource,
    TradeInputNormalizationRequest,
    adapt_decision_workspace_amount_intent,
    adapt_explicit_manual_quantity_intent,
    adapt_full_holding_sell_intent,
    adapt_holding_fraction_intent,
    adapt_optimizer_amount_intent,
    normalize_trade_input,
)


_AT = datetime(2026, 7, 14, 10, 0, 0)


def _facts(
    *,
    query: str = "KBANK.BK",
    status: ExecutionResolutionOutcome = ExecutionResolutionOutcome.RESOLVED,
    form: ExecutionInstrumentForm = ExecutionInstrumentForm.EQUITY,
    role: ExecutionRole = ExecutionRole.TRADABLE,
    tradable: bool | None = True,
) -> ExecutionInstrumentFacts:
    return ExecutionInstrumentFacts(
        query=query,
        resolution_status=status,
        instrument_form=form,
        execution_role=role,
        asset_id=42 if status == ExecutionResolutionOutcome.RESOLVED else None,
        canonical_symbol=query if status == ExecutionResolutionOutcome.RESOLVED else None,
        exchange="SET" if status == ExecutionResolutionOutcome.RESOLVED else None,
        currency="THB" if status == ExecutionResolutionOutcome.RESOLVED else None,
        tradable=tradable,
        lot_size=100,
        fractional_support=False,
        provenance=(ExecutionFactProvenance("identity", "Registry", query),),
    )


def _quote(facts: ExecutionInstrumentFacts, *, quantity: Decimal = Decimal("25"), price: Decimal = Decimal("100")):
    return quote_fee_for_instrument(
        facts,
        side=TradeSide.BUY,
        quantity=quantity,
        unit_price=price,
        quoted_at=_AT,
        effective_at=_AT,
    )


def _complete_request(
    *,
    facts: ExecutionInstrumentFacts | None = None,
    quote=None,
    quantity: Decimal = Decimal("25"),
    price: Decimal = Decimal("100"),
) -> TradeInputNormalizationRequest:
    facts = facts or _facts()
    quote = quote if quote is not None else _quote(facts, quantity=quantity, price=price)
    return TradeInputNormalizationRequest(
        recommendation_reference="optimizer:allocation:123",
        requested_symbol="KBANK.BK",
        side=TradeSide.BUY,
        requested_quantity=quantity,
        executable_quantity=quantity,
        requested_value=None,
        quantity_source=QuantityIntentSource.EXPLICIT_USER_QUANTITY,
        quantity_confidence=QuantityConfidence.EXACT,
        lot_adjustment=QuantityAdjustmentSummary.no_op(quantity, policy_reference="test"),
        fractional_adjustment=QuantityAdjustmentSummary.no_op(quantity, policy_reference="test"),
        unit_price=price,
        price_kind=PriceKind.MARKET_REFERENCE,
        price_source=PriceSource.CALLER_SUPPLIED,
        observed_at=_AT,
        received_at=_AT,
        market_session=MarketSession.REGULAR,
        freshness_assessed_at=_AT,
        freshness_policy_reference="test-freshness-v1",
        stale=False,
        currency="THB",
        execution_instrument_facts=facts,
        execution_eligibility=evaluate_execution_eligibility(facts),
        fee_quote=quote,
        provenance=("focused M32.3B complete input",),
    )


def _reasons(result) -> set[NormalizationFailureReason]:
    return {failure.reason for failure in result.failures}


def test_normalized_trade_input_is_immutable_and_ref_is_deterministic():
    first = normalize_trade_input(_complete_request())
    second = normalize_trade_input(_complete_request())

    assert first.complete is True
    assert first.normalized_input.status == NormalizationStatus.COMPLETE
    assert first.normalized_input.normalization_ref == second.normalized_input.normalization_ref
    with pytest.raises(FrozenInstanceError):
        first.normalized_input.requested_quantity = Decimal("1")


def test_explicit_user_quantity_and_user_execution_term_are_preserved_without_market_claim():
    facts = _facts()
    result = adapt_explicit_manual_quantity_intent(
        recommendation_reference="manual:1",
        requested_symbol="KBANK.BK",
        side=TradeSide.BUY,
        requested_quantity=Decimal("12.5"),
        entered_price=Decimal("101.25"),
        currency="THB",
        facts=facts,
        eligibility=evaluate_execution_eligibility(facts),
    )

    normalized = result.normalized_input
    assert normalized.requested_quantity == normalized.executable_quantity == Decimal("12.5")
    assert normalized.quantity_source == QuantityIntentSource.EXPLICIT_USER_QUANTITY
    assert normalized.price_kind == PriceKind.USER_EXECUTION_TERM
    assert normalized.price_kind != PriceKind.MARKET_REFERENCE
    assert normalized.observed_at is None
    assert normalized.received_at is None
    assert NormalizationFailureReason.PRICE_TIMESTAMP_MISSING in _reasons(result)


def test_full_holding_sell_retains_exact_caller_supplied_snapshot():
    facts = _facts()
    snapshot = HoldingQuantitySnapshot(
        quantity=Decimal("125.75"),
        observed_at=_AT,
        source="Portfolio Runtime replay snapshot",
        provenance=("snapshot:77",),
    )

    result = adapt_full_holding_sell_intent(
        recommendation_reference="sell-all:1",
        requested_symbol="KBANK.BK",
        holding_snapshot=snapshot,
        facts=facts,
        eligibility=evaluate_execution_eligibility(facts),
    )

    assert result.normalized_input.requested_quantity == Decimal("125.75")
    assert result.normalized_input.executable_quantity == Decimal("125.75")
    assert result.normalized_input.holding_quantity_snapshot is snapshot
    assert result.normalized_input.quantity_source == QuantityIntentSource.FULL_HOLDING_QUANTITY


def test_holding_fraction_derives_only_from_explicit_snapshot_and_fraction():
    facts = _facts()
    snapshot = HoldingQuantitySnapshot(Decimal("100"), _AT, "explicit holding snapshot")

    result = adapt_holding_fraction_intent(
        recommendation_reference="reduce:1",
        requested_symbol="KBANK.BK",
        holding_snapshot=snapshot,
        holding_fraction=Decimal("0.25"),
        facts=facts,
        eligibility=evaluate_execution_eligibility(facts),
    )

    assert result.normalized_input.requested_quantity == Decimal("25.00")
    assert result.normalized_input.executable_quantity == Decimal("25.00")
    assert result.normalized_input.quantity_confidence == QuantityConfidence.DERIVED
    assert "upstream holding_fraction=0.25" in result.normalized_input.provenance


@pytest.mark.parametrize(
    ("adapter", "allocation_source"),
    [
        (adapt_optimizer_amount_intent, AllocationSource.OPTIMIZER_TARGET_ALLOCATION),
        (adapt_decision_workspace_amount_intent, AllocationSource.DECISION_WORKSPACE_POSITION_SIZING),
    ],
)
def test_amount_only_sources_preserve_value_and_remain_incomplete(adapter, allocation_source):
    facts = _facts()
    result = adapter(
        recommendation_reference="amount:1",
        requested_symbol="KBANK.BK",
        requested_value=Decimal("1234.56"),
        facts=facts,
        eligibility=evaluate_execution_eligibility(facts),
    )

    assert result.complete is False
    assert result.normalized_input.requested_value == Decimal("1234.56")
    assert result.normalized_input.requested_quantity is None
    assert result.normalized_input.executable_quantity is None
    assert result.normalized_input.unit_price is None
    assert result.normalized_input.allocation_source == allocation_source
    assert NormalizationFailureReason.MISSING_QUANTITY in _reasons(result)
    assert NormalizationFailureReason.MISSING_PRICE in _reasons(result)


def test_missing_quantity_price_time_and_currency_are_explicit_not_manufactured():
    request = replace(
        _complete_request(),
        requested_quantity=None,
        executable_quantity=None,
        unit_price=None,
        observed_at=None,
        received_at=None,
        currency=None,
        fee_quote=None,
    )

    result = normalize_trade_input(request)

    assert result.complete is False
    assert result.normalized_input.requested_quantity is None
    assert result.normalized_input.executable_quantity is None
    assert result.normalized_input.unit_price is None
    assert result.normalized_input.observed_at is None
    assert result.normalized_input.received_at is None
    assert result.normalized_input.currency is None
    assert {
        NormalizationFailureReason.MISSING_QUANTITY,
        NormalizationFailureReason.MISSING_PRICE,
        NormalizationFailureReason.PRICE_TIMESTAMP_MISSING,
        NormalizationFailureReason.CURRENCY_UNKNOWN,
    } <= _reasons(result)


def test_no_avg_cost_or_current_time_fallback_exists_for_amount_only_intent():
    result = adapt_optimizer_amount_intent(
        recommendation_reference="optimizer:1",
        requested_symbol="KBANK.BK",
        requested_value=Decimal("1000"),
        facts=_facts(),
        eligibility=evaluate_execution_eligibility(_facts()),
    )

    assert result.normalized_input.unit_price is None
    assert result.normalized_input.observed_at is None
    assert result.normalized_input.received_at is None
    source = inspect.getsource(__import__("services.normalized_trade_input", fromlist=["*"]))
    assert "avg_cost" not in source
    assert "datetime.now" not in source


def test_unresolved_and_ineligible_facts_cannot_produce_complete_input():
    unresolved = _facts(
        query="UNKNOWN",
        status=ExecutionResolutionOutcome.UNKNOWN,
        form=ExecutionInstrumentForm.UNKNOWN,
        role=ExecutionRole.UNKNOWN,
        tradable=None,
    )
    request = replace(
        _complete_request(facts=unresolved, quote=_quote(_facts())),
        requested_symbol="UNKNOWN",
    )

    result = normalize_trade_input(request)

    assert result.complete is False
    assert NormalizationFailureReason.FACTS_UNRESOLVED in _reasons(result)
    assert NormalizationFailureReason.INELIGIBLE_INSTRUMENT in _reasons(result)


def test_eligibility_must_match_the_retained_facts():
    facts = _facts()
    inconsistent_eligibility = replace(evaluate_execution_eligibility(facts), eligible=False)

    result = normalize_trade_input(
        replace(_complete_request(facts=facts), execution_eligibility=inconsistent_eligibility)
    )

    assert result.complete is False
    assert NormalizationFailureReason.ELIGIBILITY_MISMATCH in _reasons(result)


def test_unavailable_fee_quote_and_quote_mismatches_are_typed_incomplete():
    facts = _facts()
    unavailable = quote_fee_for_instrument(
        _facts(query="UNKNOWN", status=ExecutionResolutionOutcome.UNKNOWN, form=ExecutionInstrumentForm.UNKNOWN, role=ExecutionRole.UNKNOWN, tradable=None),
        side=TradeSide.BUY,
        quantity=Decimal("25"),
        unit_price=Decimal("100"),
        quoted_at=_AT,
        effective_at=_AT,
    )
    unavailable_result = normalize_trade_input(replace(_complete_request(), fee_quote=unavailable))
    assert unavailable.status == FeeQuoteStatus.UNAVAILABLE
    assert NormalizationFailureReason.FEE_QUOTE_UNAVAILABLE in _reasons(unavailable_result)

    quote = _quote(facts)
    mismatch = replace(quote, quantity=Decimal("26"), unit_price=Decimal("101"), currency="USD")
    mismatch_result = normalize_trade_input(replace(_complete_request(facts=facts), fee_quote=mismatch))
    assert {
        NormalizationFailureReason.QUANTITY_QUOTE_MISMATCH,
        NormalizationFailureReason.PRICE_QUOTE_MISMATCH,
        NormalizationFailureReason.CURRENCY_QUOTE_MISMATCH,
    } <= _reasons(mismatch_result)


def test_retained_facts_eligibility_and_quote_objects_keep_identity():
    facts = _facts()
    eligibility = evaluate_execution_eligibility(facts)
    quote = _quote(facts)
    result = normalize_trade_input(replace(_complete_request(facts=facts, quote=quote), execution_eligibility=eligibility))

    normalized = result.normalized_input
    assert normalized.execution_instrument_facts is facts
    assert normalized.execution_eligibility is eligibility
    assert normalized.fee_quote is quote


def test_pure_normalizer_has_no_orm_registry_market_network_or_fee_calculation_dependency():
    source = inspect.getsource(__import__("services.normalized_trade_input", fromlist=["*"]))

    for forbidden in ("from sqlalchemy", ".query(", "resolve_execution", "requests", "yfinance", "quote_fee", "calculate_fee", "datetime.now", "os.environ"):
        assert forbidden not in source


def test_m32_2_legacy_trade_leg_builder_still_accepts_its_legacy_request_unchanged():
    facts = _facts()
    quote = _quote(facts)
    request = LegacyExecutionTradeRequest(
        recommendation_reference="legacy:1",
        requested_symbol="KBANK.BK",
        side=TradeSide.BUY,
        requested_quantity=Decimal("25"),
        unit_price=Decimal("100"),
        price_timestamp=_AT,
        funding_role=ExecutionFundingRole.DEPLOYMENT,
    )

    leg = ExecutionTradeLegBuilder().build(request, facts, evaluate_execution_eligibility(facts), quote)

    assert leg.requested_quantity == leg.executable_quantity == Decimal("25")
    assert leg.fee_quote is quote


def _session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _plan_args(db):
    workspace = Workspace(name="M32.3B")
    db.add(workspace)
    db.flush()
    portfolio = Portfolio(workspace_id=workspace.id, name="M32.3B", cash_balance=100_000.0)
    db.add(portfolio)
    db.commit()
    return {
        "portfolio_id": portfolio.id,
        "workspace_id": workspace.id,
        "buy_symbols": ["BUY-WITHOUT-PRICE"],
        "sizing_suggestions": [{"symbol": "BUY-WITHOUT-PRICE", "suggested_pct": 10}],
        "timing_scores": {"BUY-WITHOUT-PRICE": 70},
        "db": db,
    }


def test_execution_plan_output_is_identical_when_m32_3b_shadow_fails(monkeypatch):
    db = _session()
    args = _plan_args(db)
    baseline = execution_plan.build_execution_plan(**args).model_dump_json()
    monkeypatch.setattr(
        execution_plan,
        "project_execution_plan_normalized_inputs_shadow",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("shadow offline")),
    )

    failed_shadow = execution_plan.build_execution_plan(**args).model_dump_json()

    assert failed_shadow == baseline
    assert "normalized_trade_input" not in execution_plan.ExecutionPlanResult.model_fields


def test_no_optimizer_transaction_replay_frontend_or_cutover_dependency_was_added():
    module_source = inspect.getsource(__import__("services.normalized_trade_input", fromlist=["*"]))
    optimizer_source = inspect.getsource(__import__("agents.optimizer", fromlist=["*"]))

    for forbidden in ("portfolio_transactions", "portfolio_rebuilder", "replay", "frontend", "execution_cutover_config"):
        assert forbidden not in module_source
    assert "normalized_trade_input" not in optimizer_source
