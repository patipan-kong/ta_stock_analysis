"""Focused M32.3E2 live-evidence shadow tests (no provider/network I/O)."""
from __future__ import annotations

import inspect
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base, Portfolio, Workspace
from services import execution_plan
from services.execution_eligibility import evaluate_execution_eligibility
from services.execution_instrument_facts import (
    ExecutionFactProvenance,
    ExecutionInstrumentFacts,
    ExecutionInstrumentForm,
    ExecutionResolutionOutcome,
    ExecutionRole,
)
from services.execution_live_evidence_config import live_evidence_shadow_enabled
from services.execution_live_evidence_shadow import (
    ShadowDiagnosticOutcome,
    adapt_execution_plan_funding_intent,
    adapt_holding_quantity_snapshot,
    adapt_execution_quote_envelope_to_observation,
    assess_registry_capability_readiness,
    collect_live_execution_quote_evidence,
    project_live_execution_plan_shadow,
)
from services.execution_price_observation import MarketSession, PriceKind
from services.market_data.execution_quote import (
    ExecutionQuoteEvidence,
    adapt_cached_execution_quote,
    adapt_yahoo_chart_execution_quote,
    adapt_yahoo_finance_execution_quote,
    build_execution_quote_envelope,
)


_AT = datetime(2026, 7, 15, 3, 0, tzinfo=timezone.utc)


def _facts(**overrides):
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


def _chart_envelope(symbol="KBANK.BK"):
    return adapt_yahoo_chart_execution_quote(
        {
            "meta": {
                "symbol": symbol,
                "regularMarketPrice": 10,
                "regularMarketTime": int(_AT.timestamp()),
                "marketState": "REGULAR",
                "currency": "THB",
                "exchangeTimezoneName": "Asia/Bangkok",
                "exchangeDataDelayedBy": 15,
            }
        },
        requested_symbol=symbol,
        received_at=_AT + timedelta(seconds=2),
    )


class _BatchProvider:
    def __init__(self, envelopes):
        self.envelopes = envelopes
        self.calls = []

    def get_execution_quote_envelopes(self, symbols):
        self.calls.append(tuple(symbols))
        return {symbol: self.envelopes.get(symbol) for symbol in symbols}


class _FailingProvider:
    def get_execution_quote_envelopes(self, _symbols):
        raise RuntimeError("provider unavailable")


def test_quote_envelope_is_frozen_deterministic_and_preserves_chart_evidence():
    first = _chart_envelope()
    second = _chart_envelope()
    assert first == second
    assert first.price == Decimal("10")
    assert first.price_kind == PriceKind.MARKET_LAST
    assert first.observed_at == _AT
    assert first.received_at == _AT + timedelta(seconds=2)
    assert first.market_session == MarketSession.REGULAR
    with pytest.raises(Exception):
        first.price = Decimal("11")  # type: ignore[misc]


def test_cache_timestamp_is_provenance_only_and_registry_currency_is_not_substituted():
    cached = adapt_cached_execution_quote(_chart_envelope(), fetched_at=_AT + timedelta(minutes=1))
    facts = _facts(currency="THB")
    observation = adapt_execution_quote_envelope_to_observation(
        cached, requested_symbol="KBANK.BK", facts=facts,
    )
    assert observation.cached_at == _AT + timedelta(minutes=1)
    assert observation.observed_at == _AT

    no_currency = build_execution_quote_envelope(
        requested_symbol="KBANK.BK", provider_symbol="KBANK.BK", provider_id="fixture",
        provider_version=None, price=Decimal("10"), price_kind=PriceKind.MARKET_LAST,
        currency=None, observed_at=_AT, received_at=_AT, market_session=MarketSession.REGULAR,
    )
    assert adapt_execution_quote_envelope_to_observation(
        no_currency, requested_symbol="KBANK.BK", facts=facts,
    ).currency is None


def test_absent_chart_fields_and_yfinance_close_remain_explicit():
    incomplete = adapt_yahoo_chart_execution_quote(
        {"meta": {"regularMarketPrice": 10}}, requested_symbol="KBANK.BK", received_at=_AT,
    )
    assert incomplete.observed_at is None
    assert incomplete.market_session == MarketSession.UNKNOWN
    assert incomplete.currency is None
    finance = adapt_yahoo_finance_execution_quote(
        {"current_price": 10}, requested_symbol="KBANK.BK", received_at=_AT,
    )
    assert finance.price_kind == PriceKind.MARKET_CLOSE
    assert finance.observed_at is None


def test_pure_quote_adapters_do_not_read_clock_or_io():
    module = __import__("services.market_data.execution_quote", fromlist=["*"])
    source = inspect.getsource(module)
    for forbidden in ("datetime.now", "datetime.utcnow", "requests", "SessionLocal", ".query("):
        assert forbidden not in source


def test_bounded_batch_collection_deduplicates_and_isolates_failure():
    provider = _BatchProvider({"KBANK.BK": _chart_envelope()})
    evidence = collect_live_execution_quote_evidence(
        ["KBANK.BK", "KBANK.BK", "MISSING.BK"], provider=provider, received_at=_AT,
    )
    assert provider.calls == [("KBANK.BK", "MISSING.BK")]
    assert evidence["KBANK.BK"].envelope is not None
    assert evidence["MISSING.BK"].envelope is None
    assert evidence["MISSING.BK"].error is not None

    failed = collect_live_execution_quote_evidence(
        ["FAILED.BK"], provider=_FailingProvider(), received_at=_AT,
    )
    assert failed["FAILED.BK"].envelope is None
    assert "provider batch failure" in (failed["FAILED.BK"].error or "")

    cache_failed = collect_live_execution_quote_evidence(
        ["CACHE.BK"],
        provider=_BatchProvider({"CACHE.BK": _chart_envelope("CACHE.BK")}),
        received_at=_AT,
        cache_evidence_by_symbol={
            "CACHE.BK": ExecutionQuoteEvidence("CACHE.BK", None, "cache read failed", "CACHE")
        },
    )
    assert cache_failed["CACHE.BK"].envelope is None
    assert cache_failed["CACHE.BK"].source == "CACHE"


def test_complete_buy_builds_policy_normalized_input_quote_and_leg_after_lot_constraint():
    facts = _facts()
    provider = _BatchProvider({"KBANK.BK": _chart_envelope()})
    buy = SimpleNamespace(symbol="KBANK.BK", estimated_amount=1050.0)
    diagnostic = project_live_execution_plan_shadow(
        plan_reference="plan-1",
        buy_actions=[buy],
        funding_actions=[],
        holdings_by_symbol={},
        facts_by_symbol={"KBANK.BK": facts},
        eligibility_by_symbol={"KBANK.BK": evaluate_execution_eligibility(facts)},
        provider=provider,
        assessed_at=_AT + timedelta(minutes=1),
    )
    item = diagnostic.symbols[0]
    assert item.outcome == ShadowDiagnosticOutcome.COMPLETE
    assert item.trade_leg_ref is not None
    assert item.fee_quote_status == "QUOTED"
    assert item.residual_quantity == Decimal("5.0")
    assert provider.calls == [("KBANK.BK",)]
    assert diagnostic.low_cardinality_labels() == {"COMPLETE": 1}


def test_missing_capability_and_registry_failure_remain_incomplete():
    for facts in (_facts(lot_size=None), _facts(fractional_support=True), _facts(resolution_error="offline")):
        provider = _BatchProvider({"KBANK.BK": _chart_envelope()})
        diagnostic = project_live_execution_plan_shadow(
            plan_reference="plan-2", buy_actions=[SimpleNamespace(symbol="KBANK.BK", estimated_amount=1000)],
            funding_actions=[], holdings_by_symbol={}, facts_by_symbol={"KBANK.BK": facts},
            eligibility_by_symbol={"KBANK.BK": evaluate_execution_eligibility(facts)}, provider=provider,
            assessed_at=_AT + timedelta(minutes=1),
        )
        assert diagnostic.symbols[0].outcome == ShadowDiagnosticOutcome.INCOMPLETE
        assert diagnostic.symbols[0].trade_leg_ref is None
    assert assess_registry_capability_readiness(_facts(lot_size=None), evaluate_execution_eligibility(_facts(lot_size=None))).lot_ready is False


def test_provider_or_cache_failure_becomes_incomplete_not_a_leg():
    facts = _facts()
    for provider, cache in (
        (_FailingProvider(), None),
        (_BatchProvider({}), {"KBANK.BK": ExecutionQuoteEvidence("KBANK.BK", None, "cache offline", "CACHE")}),
    ):
        diagnostic = project_live_execution_plan_shadow(
            plan_reference="plan-failure", buy_actions=[SimpleNamespace(symbol="KBANK.BK", estimated_amount=1000)],
            funding_actions=[], holdings_by_symbol={}, facts_by_symbol={"KBANK.BK": facts},
            eligibility_by_symbol={"KBANK.BK": evaluate_execution_eligibility(facts)}, provider=provider,
            assessed_at=_AT + timedelta(minutes=1), cache_evidence_by_symbol=cache,
        )
        assert diagnostic.symbols[0].outcome == ShadowDiagnosticOutcome.INCOMPLETE
        assert diagnostic.symbols[0].trade_leg_ref is None


def test_funding_snapshot_preserves_loaded_quantity_and_declared_fraction_only():
    item = SimpleNamespace(symbol="KBANK.BK", shares=250, avg_cost=999)
    snapshot = adapt_holding_quantity_snapshot(item, captured_at=_AT)
    action = SimpleNamespace(action="REDUCE", symbol="KBANK.BK", current_shares=250, release_pct=0.4)
    intent = adapt_execution_plan_funding_intent(action, plan_reference="plan-3")
    assert snapshot.quantity == Decimal("250")
    assert snapshot.observed_at == _AT
    assert intent.holding_fraction == Decimal("0.4")
    assert "avg_cost" not in inspect.getsource(adapt_holding_quantity_snapshot)


def test_enabled_live_shadow_failure_keeps_legacy_plan_byte_identical(monkeypatch):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    workspace = Workspace(name="M32.3E2")
    db.add(workspace)
    db.flush()
    portfolio = Portfolio(workspace_id=workspace.id, name="M32.3E2", cash_balance=100_000)
    db.add(portfolio)
    db.commit()
    args = {
        "portfolio_id": portfolio.id,
        "workspace_id": workspace.id,
        "buy_symbols": ["NO-LIVE-QUOTE"],
        "sizing_suggestions": [{"symbol": "NO-LIVE-QUOTE", "suggested_pct": 10}],
        "timing_scores": {"NO-LIVE-QUOTE": 70},
        "db": db,
    }
    baseline = execution_plan.build_execution_plan(**args).model_dump_json()
    monkeypatch.setattr(execution_plan, "live_evidence_shadow_enabled", lambda: True)
    monkeypatch.setattr(
        execution_plan,
        "project_live_execution_plan_shadow",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("live shadow offline")),
    )
    assert execution_plan.build_execution_plan(**args).model_dump_json() == baseline
    monkeypatch.setattr(
        execution_plan,
        "project_live_execution_plan_shadow",
        lambda **_kwargs: SimpleNamespace(
            plan_reference="private", assessed_at=_AT, policy_bundle_ref="private",
            low_cardinality_labels=lambda: {"COMPLETE": 1},
        ),
    )
    assert execution_plan.build_execution_plan(**args).model_dump_json() == baseline
    db.close()


def test_shadow_configuration_is_default_off_and_invalid_is_safe(monkeypatch):
    monkeypatch.delenv("M32_LIVE_EVIDENCE_SHADOW", raising=False)
    assert live_evidence_shadow_enabled() is False
    monkeypatch.setenv("M32_LIVE_EVIDENCE_SHADOW", "unexpected")
    assert live_evidence_shadow_enabled() is False
    monkeypatch.setenv("M32_LIVE_EVIDENCE_SHADOW", "ON")
    assert live_evidence_shadow_enabled() is True
