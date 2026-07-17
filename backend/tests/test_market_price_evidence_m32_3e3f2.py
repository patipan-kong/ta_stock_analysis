"""Focused M32.3E3F2 evidence-only contracts; no provider/network access."""
from __future__ import annotations

import inspect
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from services.execution_instrument_facts import (
    ExecutionFactProvenance,
    ExecutionInstrumentFacts,
    ExecutionInstrumentForm,
    ExecutionResolutionOutcome,
    ExecutionRole,
)
from services.market_data.execution_quote import adapt_yahoo_chart_execution_quote
from services.market_data.provider_price_capability import (
    ProviderMarketPriceReadiness,
    audit_provider_market_price_capability,
    current_yahoo_chart_set_capability,
)
from services.market_price_evidence import (
    DelayApprovalState,
    DelayConfidence,
    EvidenceAgePolicy,
    LastPriceSemanticKind,
    TopOfBookPairQuality,
    adapt_execution_quote_envelope_to_last_price_evidence,
    adapt_quote_fixture_to_top_of_book_evidence,
    assess_cache_age,
    assess_last_price_age,
    assess_provider_receipt_age,
    assess_top_of_book_age,
    build_declared_provider_delay_evidence,
    build_market_price_evidence_set,
    declared_delay_status,
)


_AT = datetime(2026, 7, 15, 5, 0, tzinfo=timezone.utc)
_RECEIVED = _AT + timedelta(seconds=2)
_POLICY = EvidenceAgePolicy("m32.3e3f2-fixture", timedelta(minutes=5), timedelta(minutes=15))


def _envelope(symbol="KBANK.BK"):
    return adapt_yahoo_chart_execution_quote({"meta": {
        "symbol": symbol, "regularMarketPrice": 10, "regularMarketTime": int(_AT.timestamp()),
        "currency": "THB", "exchangeTimezoneName": "Asia/Bangkok",
    }}, requested_symbol=symbol, received_at=_RECEIVED)


def _facts(*, form=ExecutionInstrumentForm.EQUITY, role=ExecutionRole.TRADABLE):
    return ExecutionInstrumentFacts(
        query="KBANK.BK", resolution_status=ExecutionResolutionOutcome.RESOLVED, instrument_form=form,
        execution_role=role, asset_id=42, canonical_symbol="KBANK.BK", currency="THB",
        tradable=True, lot_size=100, fractional_support=False,
        provenance=(ExecutionFactProvenance("identity", "Registry", "42"),),
    )


def test_yahoo_regular_pair_is_frozen_provider_regular_last_not_last_trade():
    first = adapt_execution_quote_envelope_to_last_price_evidence(_envelope(), facts=_facts())
    second = adapt_execution_quote_envelope_to_last_price_evidence(_envelope(), facts=_facts())
    assert first == second
    assert first.semantic_kind == LastPriceSemanticKind.PROVIDER_REGULAR_LAST
    assert first.observed_at == _AT and first.provider_received_at == _RECEIVED
    with pytest.raises(Exception):
        first.price = Decimal("12")  # type: ignore[misc]


def test_index_evidence_is_labelled_index_value_without_creating_execution_authority():
    item = adapt_execution_quote_envelope_to_last_price_evidence(
        _envelope("^SET.BK"), facts=_facts(form=ExecutionInstrumentForm.OTHER, role=ExecutionRole.REFERENCE),
    )
    assert item.semantic_kind == LastPriceSemanticKind.INDEX_VALUE
    assert item.requested_symbol == "^SET.BK"


def test_missing_observation_and_registry_currency_stay_missing():
    envelope = adapt_yahoo_chart_execution_quote({"meta": {"regularMarketPrice": 10}}, requested_symbol="X", received_at=_RECEIVED)
    item = adapt_execution_quote_envelope_to_last_price_evidence(envelope, facts=_facts())
    assert item.observed_at is None
    assert item.currency is None
    assert assess_last_price_age(item, assessed_at=_RECEIVED, policy=_POLICY).status.value == "PRICE_TIMESTAMP_MISSING"


@pytest.mark.parametrize(("payload", "quality", "midpoint"), [
    ({"bid": "10", "ask": "11", "quote_observed_at": _AT, "provider_received_at": _RECEIVED, "currency": "THB"}, TopOfBookPairQuality.TWO_SIDED, Decimal("10.5")),
    ({"bid": "10", "quote_observed_at": _AT, "provider_received_at": _RECEIVED, "currency": "THB"}, TopOfBookPairQuality.BID_ONLY, None),
    ({"ask": "11", "quote_observed_at": _AT, "provider_received_at": _RECEIVED, "currency": "THB"}, TopOfBookPairQuality.ASK_ONLY, None),
    ({"bid": "10", "ask": "10", "quote_observed_at": _AT, "provider_received_at": _RECEIVED, "currency": "THB"}, TopOfBookPairQuality.LOCKED, None),
    ({"bid": "11", "ask": "10", "quote_observed_at": _AT, "provider_received_at": _RECEIVED, "currency": "THB"}, TopOfBookPairQuality.CROSSED, None),
])
def test_book_pair_quality_and_midpoint_are_evidence_only(payload, quality, midpoint):
    book = adapt_quote_fixture_to_top_of_book_evidence(payload, asset_id=42, requested_symbol="KBANK.BK",
        canonical_symbol="KBANK.BK", provider_id="fixture", provider_version=None)
    assert book.pair_quality == quality
    assert book.midpoint == midpoint


def test_book_without_quote_timestamp_is_not_repaired_by_receipt_or_cache_time():
    book = adapt_quote_fixture_to_top_of_book_evidence({"bid": "10", "ask": "11", "currency": "THB",
        "provider_received_at": _RECEIVED, "cached_at": _RECEIVED + timedelta(seconds=1)}, asset_id=42,
        requested_symbol="KBANK.BK", canonical_symbol="KBANK.BK", provider_id="fixture", provider_version=None)
    assert book.quote_observed_at is None
    assert book.midpoint is None
    assert assess_top_of_book_age(book, assessed_at=_RECEIVED, policy=_POLICY).status.value == "PRICE_TIMESTAMP_MISSING"
    assert assess_provider_receipt_age(book, assessed_at=_RECEIVED, policy=_POLICY).status.value == "CURRENT"
    assert assess_cache_age(book, assessed_at=_RECEIVED + timedelta(seconds=2), policy=_POLICY).status.value == "CURRENT"


def test_governed_delay_is_explicit_and_never_changes_last_price_age():
    delay = build_declared_provider_delay_evidence(provider_id="yahoo_chart", provider_version=None,
        market_scope_ref="provider-market:yahoo_chart:set", delay=timedelta(minutes=15),
        source_authority="Yahoo Finance", source_locator="sanitized:official-delay-table", source_version="2026-07-15",
        source_published_at=_AT, source_retrieved_at=_RECEIVED, effective_from=_AT,
        confidence=DelayConfidence.VERIFIED, approval_state=DelayApprovalState.APPROVED)
    last = adapt_execution_quote_envelope_to_last_price_evidence(_envelope(), facts=_facts(), declared_delay_evidence=delay)
    age = assess_last_price_age(last, assessed_at=_AT + timedelta(minutes=16), policy=_POLICY)
    assert last.declared_delay_evidence is delay
    assert declared_delay_status(delay) == "PRESENT"
    assert age.age == timedelta(minutes=16) and age.status.value == "EXPIRED"


def test_evidence_set_retains_exact_objects_and_cannot_select_a_price():
    last = adapt_execution_quote_envelope_to_last_price_evidence(_envelope(), facts=_facts())
    book = adapt_quote_fixture_to_top_of_book_evidence({"bid": "10", "ask": "11", "quote_observed_at": _AT,
        "provider_received_at": _RECEIVED, "currency": "THB"}, asset_id=42, requested_symbol="KBANK.BK",
        canonical_symbol="KBANK.BK", provider_id="fixture", provider_version=None)
    value = build_market_price_evidence_set(facts=_facts(), provider_id="fixture", provider_version=None,
        currency="THB", last_price_evidence=last, top_of_book_evidence=book, declared_delay_evidence=None,
        session_evidence=last.session_evidence, provider_received_at=_RECEIVED, cached_at=None)
    assert value.last_price_evidence is last and value.top_of_book_evidence is book
    assert not hasattr(value, "selected_price")


def test_yahoo_chart_capability_is_last_price_only_and_static_audit_never_fetches_network():
    capability = current_yahoo_chart_set_capability()
    audit = audit_provider_market_price_capability(capability, samples=({"regular_last": True, "currency": True, "session": True},))
    assert audit.readiness == ProviderMarketPriceReadiness.LAST_PRICE_ONLY
    assert audit.quote_timestamp_coverage == 0 and audit.bid_coverage == 0 and audit.ask_coverage == 0
    source = inspect.getsource(__import__("services.market_data.provider_price_capability", fromlist=["*"]))
    for forbidden in ("requests", "http", "get_execution_quote", "datetime.now", "SessionLocal"):
        assert forbidden not in source
