"""Focused M32.2 immutable trade-leg and shadow-plan tests."""
from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError, replace
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models.asset  # noqa: F401 - include Registry tables in focused plan DB
import models.registry_finding  # noqa: F401 - include resolver finding table
from models.database import Base, Portfolio, Workspace
from services.broker_fees import (
    FeeQuoteStatus,
    TradeSide,
    quote_fee_for_instrument,
)
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
    project_execution_plan_trade_legs_shadow,
)
from services import execution_plan


_AT = datetime(2026, 7, 14, 10, 0, 0)


def _facts(
    *,
    query: str = "KBANK.BK",
    status: ExecutionResolutionOutcome = ExecutionResolutionOutcome.RESOLVED,
    form: ExecutionInstrumentForm = ExecutionInstrumentForm.EQUITY,
    role: ExecutionRole = ExecutionRole.TRADABLE,
    tradable: bool | None = True,
    reason: str | None = None,
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
        reason=reason,
        provenance=(
            ExecutionFactProvenance(
                fact="identity",
                source_field="Registry",
                source_value=query,
            ),
        ),
    )


def _request(side: TradeSide = TradeSide.BUY) -> LegacyExecutionTradeRequest:
    return LegacyExecutionTradeRequest(
        recommendation_reference="optimizer:allocation:123",
        requested_symbol="KBANK.BK",
        side=side,
        requested_quantity=Decimal("25"),
        unit_price=Decimal("100"),
        price_timestamp=_AT,
        funding_role=(
            ExecutionFundingRole.DEPLOYMENT
            if side == TradeSide.BUY
            else ExecutionFundingRole.FUNDING_SOURCE
        ),
        provenance=("focused M32.2 legacy request",),
    )


def _quote(facts: ExecutionInstrumentFacts, side: TradeSide):
    return quote_fee_for_instrument(
        facts,
        side=side,
        quantity=Decimal("25"),
        unit_price=Decimal("100"),
        quoted_at=_AT,
        effective_at=_AT,
    )


def _leg(
    *,
    facts: ExecutionInstrumentFacts | None = None,
    side: TradeSide = TradeSide.BUY,
):
    facts = facts or _facts()
    quote = _quote(facts, side)
    eligibility = evaluate_execution_eligibility(facts)
    return ExecutionTradeLegBuilder().build(_request(side), facts, eligibility, quote)


def test_buy_trade_leg_preserves_quantity_gross_and_fee_quote_identity():
    facts = _facts()
    quote = _quote(facts, TradeSide.BUY)
    eligibility = evaluate_execution_eligibility(facts)

    leg = ExecutionTradeLegBuilder().build(_request(), facts, eligibility, quote)

    assert leg.requested_quantity == leg.executable_quantity == Decimal("25")
    assert leg.gross_amount == Decimal("2500")
    assert leg.gross_amount == quote.gross_amount
    assert leg.estimated_net_cash_effect == quote.net_cash_effect
    assert leg.fee_quote is quote
    assert leg.execution_instrument_facts is facts
    assert leg.execution_eligibility is eligibility
    assert leg.funding_role == ExecutionFundingRole.DEPLOYMENT
    assert leg.complete is True


def test_sell_trade_leg_preserves_quantity_and_signed_quote_cash_effect():
    leg = _leg(side=TradeSide.SELL)

    assert leg.side == TradeSide.SELL
    assert leg.requested_quantity == leg.executable_quantity == Decimal("25")
    assert leg.estimated_net_cash_effect is not None
    assert leg.estimated_net_cash_effect > 0
    assert leg.funding_role == ExecutionFundingRole.FUNDING_SOURCE


def test_leg_is_immutable_and_m32_2_applies_no_lot_or_fractional_adjustment():
    leg = _leg()

    with pytest.raises(FrozenInstanceError):
        leg.executable_quantity = Decimal("1")

    assert leg.lot_adjustment.adjusted is False
    assert leg.fractional_adjustment.adjusted is False
    assert leg.lot_adjustment.requested_quantity == leg.executable_quantity
    assert leg.fractional_adjustment.requested_quantity == leg.executable_quantity


def test_builder_does_not_lookup_registry_or_recalculate_fee():
    source = inspect.getsource(ExecutionTradeLegBuilder)

    assert "Session" not in source
    assert ".query(" not in source
    assert "resolve_execution" not in source
    assert "quote_fee" not in source
    assert "calculate_fee" not in source


def test_warnings_only_propagate_from_facts_eligibility_and_quote():
    facts = _facts(reason="Registry supplied warning")
    eligibility = evaluate_execution_eligibility(facts)
    quote = replace(_quote(facts, TradeSide.BUY), warnings=("FeeQuote warning",))

    leg = ExecutionTradeLegBuilder().build(_request(), facts, eligibility, quote)

    assert leg.warnings == ("Registry supplied warning", "FeeQuote warning")


def test_unavailable_fee_quote_creates_incomplete_leg_without_money_values():
    facts = _facts(
        query="UNKNOWN",
        status=ExecutionResolutionOutcome.UNKNOWN,
        form=ExecutionInstrumentForm.UNKNOWN,
        role=ExecutionRole.UNKNOWN,
        tradable=None,
        reason="no Registry identity",
    )
    quote = _quote(facts, TradeSide.BUY)

    leg = ExecutionTradeLegBuilder().build(_request(), facts, evaluate_execution_eligibility(facts), quote)

    assert quote.status == FeeQuoteStatus.UNAVAILABLE
    assert leg.complete is False
    assert leg.unit_price is None
    assert leg.gross_amount is None
    assert leg.estimated_total_cost is None
    assert leg.estimated_net_cash_effect is None
    assert leg.instrument_form == ExecutionInstrumentForm.UNKNOWN
    assert leg.execution_eligibility.eligible is False


def test_not_tradable_reference_remains_explicit_in_incomplete_leg():
    facts = _facts(
        query="SET-INDEX",
        status=ExecutionResolutionOutcome.NOT_TRADABLE,
        form=ExecutionInstrumentForm.OTHER,
        role=ExecutionRole.REFERENCE,
        tradable=False,
        reason="Registry reference",
    )

    leg = ExecutionTradeLegBuilder().build(
        _request(), facts, evaluate_execution_eligibility(facts), _quote(facts, TradeSide.BUY)
    )

    assert leg.complete is False
    assert leg.execution_role == ExecutionRole.REFERENCE
    assert leg.execution_eligibility.outcome.value == "REFERENCE_ONLY"
    assert leg.estimated_net_cash_effect is None


def test_shadow_projection_compares_legacy_gross_to_facts_backed_net_quote():
    facts = _facts()
    eligibility = evaluate_execution_eligibility(facts)
    funding_action = SimpleNamespace(
        action="REDUCE",
        symbol="KBANK.BK",
        current_shares=100.0,
        release_pct=0.25,
        estimated_cash_release=2500.0,
    )
    buy_action = SimpleNamespace(symbol="BUY-WITHOUT-PRICE")

    projection = project_execution_plan_trade_legs_shadow(
        [funding_action],
        {"KBANK.BK": facts},
        {"KBANK.BK": eligibility},
        quoted_at=_AT,
        effective_at=_AT,
        buy_actions=[buy_action],
    )

    assert len(projection.legs) == len(projection.comparisons) == 1
    assert projection.comparisons[0].legacy_gross_amount == Decimal("2500.0")
    assert projection.legs[0].estimated_total_cost == projection.legs[0].fee_quote.total_cost
    assert projection.legs[0].estimated_net_cash_effect == projection.legs[0].fee_quote.net_cash_effect
    assert projection.unprojectable_symbols == ("BUY-WITHOUT-PRICE",)


def _session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _plan_args(db):
    workspace = Workspace(name="M32.2")
    db.add(workspace)
    db.flush()
    portfolio = Portfolio(workspace_id=workspace.id, name="M32.2", cash_balance=100_000.0)
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


def test_execution_plan_output_is_identical_when_trade_leg_shadow_fails(monkeypatch):
    db = _session()
    args = _plan_args(db)
    baseline = execution_plan.build_execution_plan(**args).model_dump()
    monkeypatch.setattr(
        execution_plan,
        "project_execution_plan_trade_legs_shadow",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("shadow offline")),
    )

    failed_shadow = execution_plan.build_execution_plan(**args).model_dump()

    assert failed_shadow == baseline


def test_trade_leg_has_no_ledger_optimizer_frontend_or_persistence_dependency():
    source = inspect.getsource(__import__("services.execution_trade_leg", fromlist=["*"]))
    plan_fields = execution_plan.ExecutionPlanResult.model_fields

    assert "portfolio_transactions" not in source
    assert "agents.optimizer" not in source
    assert "models.database" not in source
    assert "frontend" not in source
    assert "trade_legs" not in plan_fields
