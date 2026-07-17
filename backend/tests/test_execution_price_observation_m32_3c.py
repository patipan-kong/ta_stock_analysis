"""Focused M32.3C canonical price-observation and freshness tests."""
from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models.asset  # noqa: F401 - register Registry tables in focused plan DB
import models.registry_finding  # noqa: F401
from agents import optimizer
from models.database import Base, Portfolio, Workspace
from services import execution_plan
from services.broker_fees import TradeSide, quote_fee_for_instrument
from services.execution_eligibility import evaluate_execution_eligibility
from services.execution_instrument_facts import (
    ExecutionFactProvenance,
    ExecutionInstrumentFacts,
    ExecutionInstrumentForm,
    ExecutionResolutionOutcome,
    ExecutionRole,
)
from services.execution_price_observation import (
    ExecutionPriceObservation,
    MarketSession,
    PriceFreshnessPolicy,
    PriceFreshnessStatus,
    PriceKind,
    PriceObservationQuality,
    PriceSource,
    PriceTimestampQuality,
    adapt_avg_cost_reference,
    adapt_yahoo_chart_quote,
    adapt_yahoo_finance_quote,
    adapt_yahoo_history_bar,
    assess_price_freshness,
    build_price_observation,
)
from services.execution_trade_leg import (
    ExecutionFundingRole,
    ExecutionTradeLegBuilder,
    LegacyExecutionTradeRequest,
)
from services.normalized_trade_input import (
    MarketSession as NormalizedMarketSession,
    NormalizationFailureReason,
    PriceKind as NormalizedPriceKind,
    PriceSource as NormalizedPriceSource,
    QuantityAdjustmentSummary,
    QuantityConfidence,
    QuantityIntentSource,
    TradeInputNormalizationRequest,
    normalize_trade_input,
)


_OBSERVED = datetime(2026, 7, 15, 3, 0, tzinfo=timezone.utc)
_RECEIVED = _OBSERVED + timedelta(seconds=2)
_POLICY = PriceFreshnessPolicy(
    policy_version="test-v1",
    current_for=timedelta(minutes=5),
    stale_for=timedelta(minutes=15),
)


def _facts() -> ExecutionInstrumentFacts:
    return ExecutionInstrumentFacts(
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
        provenance=(ExecutionFactProvenance("identity", "Registry", "KBANK.BK"),),
    )


def _observation(**overrides) -> ExecutionPriceObservation:
    values = {
        "requested_symbol": "KBANK.BK",
        "asset_id": 42,
        "canonical_symbol": "KBANK.BK",
        "observed_price": Decimal("150.25"),
        "price_type": PriceKind.MARKET_LAST,
        "source": PriceSource.CALLER_SUPPLIED,
        "currency": "THB",
        "provider": "focused-test",
        "observed_at": _OBSERVED,
        "received_at": _RECEIVED,
        "market_session": MarketSession.REGULAR,
        "timestamp_quality": PriceTimestampQuality.EXCHANGE_OBSERVED,
    }
    values.update(overrides)
    return build_price_observation(**values)


def _assessment(
    observation: ExecutionPriceObservation,
    *,
    assessed_at: datetime | None = None,
):
    return assess_price_freshness(
        observation,
        assessed_at=assessed_at or (_OBSERVED + timedelta(minutes=1)),
        policy=_POLICY,
    )


def _normalized_request(observation: ExecutionPriceObservation):
    facts = _facts()
    freshness = _assessment(observation)
    quantity = Decimal("10")
    quote = quote_fee_for_instrument(
        facts,
        side=TradeSide.BUY,
        quantity=quantity,
        unit_price=observation.observed_price or Decimal("1"),
        quoted_at=_RECEIVED,
        effective_at=_RECEIVED,
    )
    return TradeInputNormalizationRequest(
        recommendation_reference="m32.3c:test",
        requested_symbol="KBANK.BK",
        side=TradeSide.BUY,
        requested_quantity=quantity,
        executable_quantity=quantity,
        requested_value=None,
        quantity_source=QuantityIntentSource.EXPLICIT_USER_QUANTITY,
        quantity_confidence=QuantityConfidence.EXACT,
        lot_adjustment=QuantityAdjustmentSummary.no_op(quantity, policy_reference="test"),
        fractional_adjustment=QuantityAdjustmentSummary.no_op(quantity, policy_reference="test"),
        # Raw values deliberately disagree: retained M32.3C contracts own price.
        unit_price=Decimal("999"),
        price_kind=NormalizedPriceKind.UNKNOWN,
        price_source=NormalizedPriceSource.UNKNOWN,
        observed_at=None,
        received_at=None,
        market_session=NormalizedMarketSession.UNKNOWN,
        freshness_assessed_at=None,
        freshness_policy_reference=None,
        stale=None,
        currency=None,
        execution_instrument_facts=facts,
        execution_eligibility=evaluate_execution_eligibility(facts),
        fee_quote=quote,
        price_observation=observation,
        price_freshness_assessment=freshness,
    )


def test_observation_is_immutable_and_ref_is_deterministic():
    first = _observation()
    second = _observation()
    assert first.observation_ref == second.observation_ref
    with pytest.raises(FrozenInstanceError):
        first.observed_price = Decimal("1")  # type: ignore[misc]


def test_yahoo_quote_adapter_preserves_observation_and_fetch_times_separately():
    payload = {
        "current_price": 150.25,
        "regularMarketTime": int(_OBSERVED.timestamp()),
        "last_updated": _RECEIVED.isoformat(),
        "currency": "THB",
        "market_state": "REGULAR",
    }
    observation = adapt_yahoo_chart_quote(payload, requested_symbol="KBANK.BK")
    assert observation.observed_at == _OBSERVED
    assert observation.received_at == _RECEIVED
    assert observation.observed_at != observation.received_at
    assert observation.timestamp_quality == PriceTimestampQuality.EXCHANGE_OBSERVED


@pytest.mark.parametrize("adapter", [adapt_yahoo_chart_quote, adapt_yahoo_finance_quote])
def test_current_provider_adapter_never_promotes_fetch_time_to_observation_time(adapter):
    observation = adapter(
        {"current_price": 150.25, "last_updated": _RECEIVED.isoformat()},
        requested_symbol="KBANK.BK",
    )
    assert observation.observed_at is None
    assert observation.received_at == _RECEIVED
    assert observation.timestamp_quality == PriceTimestampQuality.RECEIPT_ONLY


def test_unknown_provider_timestamps_remain_unknown():
    observation = adapt_yahoo_chart_quote(
        {"current_price": 150.25},
        requested_symbol="KBANK.BK",
    )
    assert observation.observed_at is None
    assert observation.received_at is None
    assert observation.cached_at is None
    assert observation.timestamp_quality == PriceTimestampQuality.MISSING


def test_history_adapter_preserves_provider_bar_time_and_receipt_time():
    observation = adapt_yahoo_history_bar(
        requested_symbol="KBANK.BK",
        price=Decimal("150.25"),
        price_type=PriceKind.MARKET_CLOSE,
        observed_at=_OBSERVED,
        received_at=_RECEIVED,
        currency="THB",
    )
    assert observation.observed_at == _OBSERVED
    assert observation.received_at == _RECEIVED
    assert observation.timestamp_quality == PriceTimestampQuality.PROVIDER_BAR


def test_avg_cost_is_reference_only_and_never_execution_price_evidence():
    observation = adapt_avg_cost_reference(
        requested_symbol="KBANK.BK",
        avg_cost=Decimal("120"),
        asset_id=42,
        canonical_symbol="KBANK.BK",
        currency="THB",
    )
    assert observation.price_type == PriceKind.AVG_COST_REFERENCE
    assert observation.quality == PriceObservationQuality.REFERENCE_ONLY
    assert observation.is_market_observation is False
    assert observation.satisfies_execution_price_evidence is False
    result = normalize_trade_input(_normalized_request(observation))
    assert result.complete is False
    assert NormalizationFailureReason.PRICE_NOT_EXECUTION_EVIDENCE in {
        failure.reason for failure in result.failures
    }


def test_freshness_assessment_is_immutable_deterministic_and_pure():
    observation = _observation()
    first = _assessment(observation)
    second = _assessment(observation)
    assert first == second
    assert first.assessment_ref == second.assessment_ref
    with pytest.raises(FrozenInstanceError):
        first.status = PriceFreshnessStatus.STALE  # type: ignore[misc]


@pytest.mark.parametrize(
    ("age", "status"),
    [
        (timedelta(minutes=1), PriceFreshnessStatus.CURRENT),
        (timedelta(minutes=10), PriceFreshnessStatus.STALE),
        (timedelta(minutes=30), PriceFreshnessStatus.EXPIRED),
    ],
)
def test_age_based_freshness_statuses(age, status):
    assert _assessment(_observation(), assessed_at=_OBSERVED + age).status == status


def test_session_closed_status():
    assert _assessment(_observation(market_session=MarketSession.CLOSED)).status == PriceFreshnessStatus.SESSION_CLOSED


def test_price_timestamp_missing_status():
    assert _assessment(_observation(observed_at=None)).status == PriceFreshnessStatus.PRICE_TIMESTAMP_MISSING


def test_session_unknown_status():
    assert _assessment(_observation(market_session=MarketSession.UNKNOWN)).status == PriceFreshnessStatus.SESSION_UNKNOWN


def test_unknown_status_for_non_market_or_future_observation():
    term = _observation(price_type=PriceKind.USER_EXECUTION_TERM)
    assert _assessment(term).status == PriceFreshnessStatus.UNKNOWN
    future = _observation(observed_at=_OBSERVED + timedelta(hours=1))
    assert _assessment(future).status == PriceFreshnessStatus.UNKNOWN


def test_missing_currency_remains_explicit():
    observation = _observation(currency=None)
    assessment = _assessment(observation)
    assert observation.currency is None
    assert assessment.status == PriceFreshnessStatus.CURRENCY_UNKNOWN


def test_normalized_input_reuses_observation_and_assessment_objects():
    observation = _observation()
    request = _normalized_request(observation)
    result = normalize_trade_input(request)
    assert result.complete is True
    assert result.normalized_input.price_observation is observation
    assert result.normalized_input.price_freshness_assessment is request.price_freshness_assessment
    assert result.normalized_input.unit_price == Decimal("150.25")


def test_fee_quote_and_trade_leg_contracts_remain_unchanged():
    observation = _observation()
    request = _normalized_request(observation)
    quote = request.fee_quote
    assert quote is not None
    quote_before = quote.to_dict()
    normalize_trade_input(request)
    assert quote.to_dict() == quote_before

    legacy = LegacyExecutionTradeRequest(
        recommendation_reference="legacy",
        requested_symbol="KBANK.BK",
        side=TradeSide.BUY,
        requested_quantity=Decimal("10"),
        unit_price=Decimal("150.25"),
        price_timestamp=_OBSERVED,
        funding_role=ExecutionFundingRole.DEPLOYMENT,
    )
    facts = _facts()
    leg = ExecutionTradeLegBuilder().build(
        legacy,
        facts,
        evaluate_execution_eligibility(facts),
        quote,
    )
    assert leg.unit_price == Decimal("150.25")
    assert leg.fee_quote is quote


def _plan_args():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    workspace = Workspace(name="M32.3C")
    db.add(workspace)
    db.flush()
    portfolio = Portfolio(workspace_id=workspace.id, name="M32.3C", cash_balance=100_000)
    db.add(portfolio)
    db.commit()
    return db, {
        "portfolio_id": portfolio.id,
        "workspace_id": workspace.id,
        "buy_symbols": ["NO-PRICE"],
        "sizing_suggestions": [{"symbol": "NO-PRICE", "suggested_pct": 10}],
        "timing_scores": {"NO-PRICE": 70},
        "db": db,
    }


def test_execution_plan_output_is_unchanged_when_price_shadow_fails(monkeypatch):
    db, args = _plan_args()
    baseline = execution_plan.build_execution_plan(**args).model_dump_json()
    monkeypatch.setattr(
        execution_plan,
        "project_execution_plan_price_observations_shadow",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("price shadow offline")),
    )
    failed = execution_plan.build_execution_plan(**args).model_dump_json()
    db.close()
    assert failed == baseline
    assert "price_observation" not in execution_plan.ExecutionPlanResult.model_fields


def test_foundation_has_no_clock_io_registry_fetch_db_api_persistence_or_frontend_dependency():
    module = __import__("services.execution_price_observation", fromlist=["*"])
    source = inspect.getsource(module)
    for forbidden in (
        "datetime.now",
        "datetime.utcnow",
        "time.time",
        "from sqlalchemy",
        ".query(",
        "SessionLocal",
        "requests",
        "yfinance",
        "fetch_price",
        "registry_lookup",
        "resolve_execution",
        "portfolio_transactions",
        "frontend",
        "BaseModel",
        "Column(",
    ):
        assert forbidden not in source


def test_provider_optimizer_api_and_canonical_planning_surfaces_are_unchanged():
    chart_source = inspect.getsource(
        __import__("services.market_data.yahoo_chart", fromlist=["*"])
    )
    finance_source = inspect.getsource(
        __import__("services.market_data.yahoo", fromlist=["*"])
    )
    assert "execution_price_observation" not in chart_source
    assert "execution_price_observation" not in finance_source
    assert "execution_price_observation" not in inspect.getsource(optimizer)
    assert "price_observation" not in execution_plan.ExecutionPlanResult.model_fields
    assert "CANONICAL" not in inspect.getsource(execution_plan.build_execution_plan)

