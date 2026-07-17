"""Focused M32.1 FeeQuote, selector, and posting-parity tests."""
from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base, Portfolio, PortfolioItem, Transaction, Workspace
from services.broker_fees import (
    DR_STANDARD,
    FREE,
    SET_STANDARD,
    FeeProfile,
    FeeQuoteStatus,
    FeeQuoteUnavailableReason,
    FeeSchedule,
    PercentageFeeRule,
    TradeSide,
    calc_fees,
    calculate_fee_components,
    calculate_fee_quote,
    get_fee_schedule,
    get_profile,
    quote_fee_for_instrument,
    register_profile,
    resolve_fee_profile,
    select_fee_schedule,
)
from services.broker_fees_compat import quote_transaction_fee_compat
from services.execution_instrument_facts import (
    ExecutionInstrumentFacts,
    ExecutionInstrumentForm,
    ExecutionResolutionOutcome,
    ExecutionRole,
)
from services.portfolio_transactions import execute_buy, execute_sell

_AT = datetime(2026, 7, 14, 9, 30, 0)


def _facts(
    *,
    query: str = "KBANK.BK",
    form: ExecutionInstrumentForm = ExecutionInstrumentForm.EQUITY,
    status: ExecutionResolutionOutcome = ExecutionResolutionOutcome.RESOLVED,
    role: ExecutionRole = ExecutionRole.TRADABLE,
    tradable: bool | None = True,
    exchange: str | None = "SET",
    currency: str | None = "THB",
    reason: str | None = None,
    resolution_error: str | None = None,
) -> ExecutionInstrumentFacts:
    return ExecutionInstrumentFacts(
        query=query,
        resolution_status=status,
        instrument_form=form,
        execution_role=role,
        canonical_symbol=query,
        market="TH",
        exchange=exchange,
        currency=currency,
        tradable=tradable,
        reason=reason,
        resolution_error=resolution_error,
    )


def _quote(profile_name: str, side: TradeSide):
    return calculate_fee_quote(
        get_fee_schedule(profile_name),
        side=side,
        quantity=Decimal("100"),
        unit_price=Decimal("100"),
        currency="THB",
        quoted_at=_AT,
        effective_at=_AT,
    )


def _session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _portfolio(db, *, cash: float = 100_000.0):
    workspace = Workspace(name="M32.1")
    db.add(workspace)
    db.flush()
    portfolio = Portfolio(
        workspace_id=workspace.id,
        name="M32.1",
        cash_balance=cash,
    )
    db.add(portfolio)
    db.commit()
    return workspace, portfolio


def test_set_buy_quote_matches_existing_formula():
    quote = _quote("SET_STANDARD", TradeSide.BUY)
    legacy = calc_fees(Decimal("10000"), SET_STANDARD)

    assert quote.status == FeeQuoteStatus.QUOTED
    assert quote.to_fee_breakdown() == legacy
    assert quote.net_cash_effect == -legacy.net_buy_amount()


def test_set_sell_quote_matches_existing_formula():
    quote = _quote("SET_STANDARD", TradeSide.SELL)
    legacy = calc_fees(Decimal("10000"), SET_STANDARD)

    assert quote.to_fee_breakdown() == legacy
    assert quote.net_cash_effect == legacy.net_sell_proceeds()


def test_dr_compatibility_quote_preserves_current_rates_and_profile():
    quote = quote_transaction_fee_compat(
        "NVDA01.BK",
        side=TradeSide.BUY,
        quantity=Decimal("100"),
        unit_price=Decimal("100"),
        currency="THB",
        quoted_at=_AT,
        effective_at=_AT,
    )

    assert quote.schedule_id == "DR_STANDARD"
    assert quote.to_fee_breakdown() == calc_fees(Decimal("10000"), DR_STANDARD)
    assert any("Legacy raw-symbol" in warning for warning in quote.warnings)


def test_free_schedule_quote_has_zero_cost_and_gross_cash_effect():
    buy = _quote("FREE", TradeSide.BUY)
    sell = _quote("FREE", TradeSide.SELL)

    assert buy.total_cost == Decimal("0.0000")
    assert buy.net_cash_effect == Decimal("-10000.0000")
    assert sell.net_cash_effect == Decimal("10000.0000")
    assert buy.to_fee_breakdown() == calc_fees(Decimal("10000"), FREE)


def test_each_component_uses_four_decimal_round_half_up():
    base = get_fee_schedule("FREE")
    half_up_schedule = FeeSchedule(
        schedule_id="HALF_UP_TEST",
        schedule_version="1",
        effective_from=None,
        commission_rule=PercentageFeeRule(Decimal("0.00005")),
        trading_fee_rule=PercentageFeeRule(Decimal("0")),
        clearing_fee_rule=PercentageFeeRule(Decimal("0")),
        tax_rule=PercentageFeeRule(Decimal("0"), basis="PRE_TAX_FEE_COMPONENTS"),
        rounding_rules=base.rounding_rules,
        currency=None,
        applicability_metadata=(("test", "rounding"),),
        provenance=("focused M32.1 rounding fixture",),
    )

    breakdown = calculate_fee_components(Decimal("1"), half_up_schedule)

    assert breakdown.commission == Decimal("0.0001")
    assert breakdown.trading_fee == Decimal("0.0000")
    assert breakdown.clearing_fee == Decimal("0.0000")
    assert breakdown.vat == Decimal("0.0000")


@pytest.mark.parametrize(
    "gross",
    [
        Decimal("0"),
        Decimal("0.01"),
        Decimal("0.033333333333"),
        Decimal("1"),
        Decimal("123.456789"),
        Decimal("9999.999999"),
        Decimal("1000000.123456"),
    ],
)
def test_calculator_exactly_matches_pre_m32_decimal_contract(gross):
    quantum = Decimal("0.0001")
    commission = (gross * Decimal("0.0015")).quantize(quantum, rounding=ROUND_HALF_UP)
    trading = (gross * Decimal("0.00006")).quantize(quantum, rounding=ROUND_HALF_UP)
    clearing = (gross * Decimal("0.00001")).quantize(quantum, rounding=ROUND_HALF_UP)
    vat = ((commission + trading + clearing) * Decimal("0.07")).quantize(
        quantum,
        rounding=ROUND_HALF_UP,
    )

    assert calculate_fee_components(gross, get_fee_schedule("SET_STANDARD")) == (
        calc_fees(gross, SET_STANDARD)
    )
    result = calculate_fee_components(gross, get_fee_schedule("SET_STANDARD"))
    assert result.commission == commission
    assert result.trading_fee == trading
    assert result.clearing_fee == clearing
    assert result.vat == vat


def test_signed_cash_effect_convention_is_explicit():
    buy = _quote("SET_STANDARD", TradeSide.BUY)
    sell = _quote("SET_STANDARD", TradeSide.SELL)

    assert buy.net_cash_effect < 0
    assert sell.net_cash_effect > 0
    assert -buy.net_cash_effect == buy.gross_amount + buy.total_cost
    assert sell.net_cash_effect == sell.gross_amount - sell.total_cost


def test_quote_ref_is_deterministic_and_excludes_observation_time():
    schedule = get_fee_schedule("SET_STANDARD")
    first = calculate_fee_quote(
        schedule,
        side=TradeSide.BUY,
        quantity=Decimal("100.00"),
        unit_price=Decimal("100.0"),
        currency="THB",
        quoted_at=_AT,
        effective_at=_AT,
    )
    second = calculate_fee_quote(
        schedule,
        side=TradeSide.BUY,
        quantity=Decimal("100"),
        unit_price=Decimal("100"),
        currency="THB",
        quoted_at=datetime(2026, 7, 14, 9, 31),
        effective_at=_AT,
    )

    assert first.quote_ref == second.quote_ref
    assert first.quote_ref.startswith("feeq_")


def test_schedule_and_quote_are_immutable_versioned_and_provenanced():
    schedule = get_fee_schedule("SET_STANDARD")
    quote = _quote("SET_STANDARD", TradeSide.BUY)

    assert schedule.schedule_version == "1"
    assert schedule.provenance
    assert quote.contract_version == "1"
    assert quote.schedule_version == schedule.schedule_version
    assert quote.provenance
    assert quote.to_dict()["net_cash_effect"] == "-10016.7990"
    with pytest.raises(FrozenInstanceError):
        quote.schedule_id = "CHANGED"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("facts", "reason"),
    [
        (
            _facts(
                status=ExecutionResolutionOutcome.UNKNOWN,
                form=ExecutionInstrumentForm.UNKNOWN,
                role=ExecutionRole.UNKNOWN,
                tradable=None,
                exchange=None,
                currency=None,
            ),
            FeeQuoteUnavailableReason.IDENTITY_UNKNOWN,
        ),
        (
            _facts(
                status=ExecutionResolutionOutcome.AMBIGUOUS,
                form=ExecutionInstrumentForm.UNKNOWN,
                role=ExecutionRole.UNKNOWN,
                tradable=None,
            ),
            FeeQuoteUnavailableReason.IDENTITY_AMBIGUOUS,
        ),
        (
            _facts(
                status=ExecutionResolutionOutcome.NOT_TRADABLE,
                form=ExecutionInstrumentForm.OTHER,
                role=ExecutionRole.REFERENCE,
                tradable=False,
            ),
            FeeQuoteUnavailableReason.NOT_TRADABLE,
        ),
        (
            _facts(
                status=ExecutionResolutionOutcome.UNKNOWN,
                form=ExecutionInstrumentForm.UNKNOWN,
                role=ExecutionRole.UNKNOWN,
                tradable=None,
                resolution_error="database unavailable",
            ),
            FeeQuoteUnavailableReason.REGISTRY_FAILURE,
        ),
    ],
)
def test_unavailable_quotes_have_typed_reason_and_no_money(facts, reason):
    quote = quote_fee_for_instrument(
        facts,
        side=TradeSide.BUY,
        quantity=Decimal("10"),
        unit_price=Decimal("25"),
        quoted_at=_AT,
        effective_at=_AT,
    )

    assert quote.status == FeeQuoteStatus.UNAVAILABLE
    assert quote.unavailable_reason == reason
    for field in (
        "quantity",
        "unit_price",
        "gross_amount",
        "commission",
        "trading_fee",
        "clearing_fee",
        "taxes",
        "total_cost",
        "net_cash_effect",
    ):
        assert getattr(quote, field) is None


def test_facts_backed_set_equity_selection_uses_listing_metadata():
    selection = select_fee_schedule(
        _facts(form=ExecutionInstrumentForm.EQUITY),
        side=TradeSide.BUY,
        effective_at=_AT,
    )

    assert selection.schedule is get_fee_schedule("SET_STANDARD")
    assert selection.unavailable_reason is None


def test_dr_schedule_comes_only_from_registry_backed_instrument_form():
    dr_shaped_equity = select_fee_schedule(
        _facts(query="NVDA01.BK", form=ExecutionInstrumentForm.EQUITY),
        side=TradeSide.BUY,
        effective_at=_AT,
    )
    non_dr_shaped_receipt = select_fee_schedule(
        _facts(query="RECEIPT", form=ExecutionInstrumentForm.DEPOSITARY_RECEIPT),
        side=TradeSide.BUY,
        effective_at=_AT,
    )

    assert dr_shaped_equity.schedule is get_fee_schedule("SET_STANDARD")
    assert non_dr_shaped_receipt.schedule is get_fee_schedule("DR_STANDARD")


def test_resolved_unsupported_listing_has_no_invented_set_quote():
    quote = quote_fee_for_instrument(
        _facts(exchange="NASDAQ", currency="USD"),
        side=TradeSide.BUY,
        quantity=Decimal("1"),
        unit_price=Decimal("100"),
        quoted_at=_AT,
        effective_at=_AT,
    )

    assert quote.status == FeeQuoteStatus.UNAVAILABLE
    assert quote.unavailable_reason == FeeQuoteUnavailableReason.MISSING_FEE_SCHEDULE


def test_legacy_adapter_preserves_unresolved_transaction_behavior():
    set_quote = quote_transaction_fee_compat(
        "UNKNOWN",
        side=TradeSide.BUY,
        quantity=Decimal("1"),
        unit_price=Decimal("100"),
        currency="USD",
        quoted_at=_AT,
        effective_at=_AT,
    )
    dr_quote = quote_transaction_fee_compat(
        "UNKNOWN01.BK",
        side=TradeSide.BUY,
        quantity=Decimal("1"),
        unit_price=Decimal("100"),
        currency="THB",
        quoted_at=_AT,
        effective_at=_AT,
    )

    assert set_quote.schedule_id == "SET_STANDARD"
    assert dr_quote.schedule_id == "DR_STANDARD"


def test_replacing_registered_builtin_updates_automatic_resolution_and_quote():
    replacement = FeeProfile(
        name="SET_STANDARD",
        commission_rate=Decimal("0.0025"),
        trading_fee_rate=SET_STANDARD.trading_fee_rate,
        clearing_fee_rate=SET_STANDARD.clearing_fee_rate,
        vat_rate=SET_STANDARD.vat_rate,
        schedule_version="replacement-test",
        currency="THB",
        provenance=("focused replacement fixture",),
    )
    try:
        register_profile(replacement)
        resolved = resolve_fee_profile("KBANK.BK")
        quote = quote_transaction_fee_compat(
            "KBANK.BK",
            side=TradeSide.BUY,
            quantity=Decimal("1"),
            unit_price=Decimal("10000"),
            currency="THB",
            quoted_at=_AT,
            effective_at=_AT,
        )

        assert resolved is replacement
        assert get_profile("SET_STANDARD") is replacement
        assert quote.schedule_version == "replacement-test"
        assert quote.commission == Decimal("25.0000")
        assert calc_fees(Decimal("10000")).commission == Decimal("25.0000")
    finally:
        register_profile(SET_STANDARD)


def test_buy_posting_and_public_shape_remain_ledger_compatible():
    db = _session()
    workspace, portfolio = _portfolio(db)
    expected = calc_fees(Decimal("10000"), SET_STANDARD)

    result = execute_buy(
        db,
        workspace.id,
        portfolio.id,
        "KBANK.BK",
        shares=100,
        price_per_share=100,
        transaction_date=_AT,
    )
    tx = db.query(Transaction).filter_by(transaction_type="BUY").one()
    holding = db.query(PortfolioItem).filter_by(symbol="KBANK.BK").one()

    assert tx.total_amount == pytest.approx(float(expected.net_buy_amount()))
    assert tx.fees == pytest.approx(float(expected.total_fees_excl_vat))
    assert tx.taxes == pytest.approx(float(expected.vat))
    assert holding.avg_cost == pytest.approx(float(expected.net_buy_amount() / Decimal("100")))
    assert result["fee_profile"] == "SET_STANDARD"
    assert result["fee_breakdown"] == expected.to_dict()
    assert "fee_quote" not in result


def test_sell_posting_and_public_shape_remain_ledger_compatible():
    db = _session()
    workspace, portfolio = _portfolio(db)
    execute_buy(
        db,
        workspace.id,
        portfolio.id,
        "KBANK.BK",
        shares=100,
        price_per_share=100,
        transaction_date=_AT,
        fee_profile=FREE,
    )
    expected = calc_fees(Decimal("11000"), SET_STANDARD)

    result = execute_sell(
        db,
        workspace.id,
        portfolio.id,
        "KBANK.BK",
        shares=100,
        price_per_share=110,
        transaction_date=_AT,
    )
    tx = db.query(Transaction).filter_by(transaction_type="SELL").one()

    assert tx.total_amount == pytest.approx(float(expected.net_sell_proceeds()))
    assert tx.fees == pytest.approx(float(expected.total_fees_excl_vat))
    assert tx.taxes == pytest.approx(float(expected.vat))
    assert result["fee_profile"] == "SET_STANDARD"
    assert result["fee_breakdown"] == expected.to_dict()
    assert "fee_quote" not in result


def test_replay_consumes_persisted_net_total_without_fee_recalculation():
    from services import portfolio_rebuilder

    source = inspect.getsource(portfolio_rebuilder._apply_transaction)
    assert "ctx.total_amount" in source
    assert "calc_fees" not in source
    assert "FeeQuote" not in source


def test_admin_recalculation_still_routes_through_shared_compatibility_adapter():
    main_source = (Path(__file__).parents[1] / "main.py").read_text(encoding="utf-8")
    route_start = main_source.index("async def admin_recalculate_cost_basis")
    route_source = main_source[route_start:]

    assert "calc_fees as _calc_fees" in route_source
    assert "resolve_fee_profile as _resolve_profile" in route_source
    assert "_calc_fees(gross, profile)" in route_source
    assert calculate_fee_components(Decimal("10000"), get_fee_schedule("SET_STANDARD")) == calc_fees(
        Decimal("10000"),
        SET_STANDARD,
    )


def test_pure_calculators_have_no_database_orm_network_or_clock_access():
    source = inspect.getsource(calculate_fee_components) + inspect.getsource(calculate_fee_quote)

    for forbidden in ("Session", "query(", "requests", "http", "datetime.now", "utcnow"):
        assert forbidden not in source


def test_authoritative_module_contains_no_symbol_regex_or_ticker_allow_list():
    source = inspect.getsource(__import__("services.broker_fees", fromlist=["*"]))

    assert "re.compile" not in source
    assert "_DR_RE" not in source
    assert "ETF_TICKERS" not in source
    assert "ticker_allow" not in source.lower()
