"""Focused M32.3E3S2 session-evidence tests; all provider payloads are sanitized."""
from __future__ import annotations

import inspect
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from services.execution_live_evidence_shadow import adapt_execution_quote_envelope_to_observation
from services.execution_price_observation import (
    MarketSession,
    PriceFreshnessPolicy,
    PriceKind,
    PriceSource,
    assess_price_freshness,
    build_price_observation,
)
from services.market_data.execution_quote import (
    adapt_yahoo_chart_execution_quote,
    build_execution_quote_envelope,
)
from services.market_data.session_evidence import (
    MarketSessionConfidence,
    ObservationSessionBasis,
    build_market_session_evidence,
)


_AT = datetime(2026, 7, 15, 5, 0, tzinfo=timezone.utc)
_RECEIVED = _AT + timedelta(seconds=2)
_MISSING = object()


def _result(*, state=_MISSING, price=10, timestamp=None, timezone_name="Asia/Bangkok", delay=15,
            period=True, instrument_type="EQUITY"):
    meta = {
        "symbol": "KBANK.BK",
        "currency": "THB",
        "instrumentType": instrument_type,
    }
    if price is not None:
        meta["regularMarketPrice"] = price
    if timestamp is not None or price is not None:
        meta["regularMarketTime"] = int((timestamp or _AT).timestamp())
    if state is not _MISSING:
        meta["marketState"] = state
    if timezone_name is not None:
        meta["exchangeTimezoneName"] = timezone_name
        meta["gmtoffset"] = 25200
    if delay is not _MISSING:
        meta["exchangeDataDelayedBy"] = delay
    if period:
        meta["currentTradingPeriod"] = {
            "pre": {"start": int((_AT - timedelta(hours=1)).timestamp()), "end": int(_AT.timestamp())},
            "regular": {"start": int(_AT.timestamp()), "end": int((_AT + timedelta(hours=6)).timestamp())},
            "post": {"start": int((_AT + timedelta(hours=6)).timestamp()), "end": int((_AT + timedelta(hours=7)).timestamp())},
        }
    return {"meta": meta}


def _live_shape(**overrides):
    values = {"state": _MISSING, "delay": _MISSING}
    values.update(overrides)
    return _result(**values)


def _envelope(result=None):
    return adapt_yahoo_chart_execution_quote(
        result or _live_shape(), requested_symbol="KBANK.BK", received_at=_RECEIVED,
    )


def test_live_shape_regular_pair_creates_frozen_deterministic_session_evidence():
    first = _envelope()
    second = _envelope()
    evidence = first.session_evidence
    assert evidence is not None and evidence == second.session_evidence
    assert first.market_session == MarketSession.REGULAR
    assert evidence.envelope_ref == first.envelope_ref
    assert evidence.observation_session_claim == MarketSession.REGULAR
    assert evidence.observation_session_basis == ObservationSessionBasis.PROVIDER_REGULAR_MARKET_FIELDS
    assert evidence.confidence == MarketSessionConfidence.PROVIDER_SEMANTIC_PAIR
    assert evidence.provider_reported_state_normalized == MarketSession.UNKNOWN
    assert evidence.provider_reported_state_raw is None
    assert evidence.provider_delay is None
    assert evidence.current_trading_period is not None
    assert evidence.current_trading_period.regular is not None
    with pytest.raises(Exception):
        evidence.provider_id = "other"  # type: ignore[misc]


def test_timezone_aware_times_are_required_and_receipt_never_becomes_observation_or_state_time():
    with pytest.raises(ValueError, match="envelope_ref"):
        build_market_session_evidence(
            envelope_ref="", requested_symbol="X", provider_symbol="X", provider_id="fixture",
            provider_version=None,
        )
    with pytest.raises(ValueError, match="timezone-aware"):
        build_market_session_evidence(
            envelope_ref="eqe", requested_symbol="X", provider_symbol="X", provider_id="fixture",
            provider_version=None, observation_at=datetime(2026, 1, 1),
        )
    evidence = _envelope().session_evidence
    assert evidence is not None
    assert evidence.observation_at == _AT
    assert evidence.provider_state_received_at is None
    assert evidence.provider_state_at is None
    assert evidence.observation_at != _RECEIVED


def test_closed_response_and_regular_observation_are_separate_non_conflicting_facts():
    envelope = _envelope(_result(state="CLOSED"))
    evidence = envelope.session_evidence
    assert evidence is not None
    assert envelope.market_session == MarketSession.REGULAR
    assert evidence.observation_session_claim == MarketSession.REGULAR
    assert evidence.provider_reported_state_raw == "CLOSED"
    assert evidence.provider_reported_state_normalized == MarketSession.CLOSED
    assert evidence.provider_state_received_at == _RECEIVED
    assert evidence.provider_state_at is None


def test_response_state_without_regular_pair_never_creates_observation_claim():
    envelope = _envelope(_result(state="REGULAR", price=None))
    evidence = envelope.session_evidence
    assert evidence is not None
    assert envelope.market_session == MarketSession.UNKNOWN
    assert evidence.observation_session_claim == MarketSession.UNKNOWN
    assert evidence.provider_reported_state_normalized == MarketSession.REGULAR


@pytest.mark.parametrize(
    ("raw", "normalized"),
    [
        ("PRE", MarketSession.PRE_MARKET),
        ("PREPRE", MarketSession.PRE_MARKET),
        ("POST", MarketSession.AFTER_HOURS),
        ("POSTPOST", MarketSession.AFTER_HOURS),
        ("unexpected-state", MarketSession.UNKNOWN),
    ],
)
def test_raw_provider_response_state_is_preserved_and_known_spellings_are_normalized(raw, normalized):
    evidence = _envelope(_result(state=raw)).session_evidence
    assert evidence is not None
    assert evidence.provider_reported_state_raw == raw
    assert evidence.provider_reported_state_normalized == normalized
    assert evidence.observation_session_claim == MarketSession.REGULAR


def test_schedule_timezone_and_delay_are_preserved_without_session_inference():
    envelope = _envelope(_result(state=_MISSING, price=None, delay=_MISSING))
    evidence = envelope.session_evidence
    assert evidence is not None
    assert evidence.current_trading_period is not None
    assert evidence.exchange_timezone == "Asia/Bangkok"
    assert evidence.provider_delay is None
    assert evidence.observation_session_claim == MarketSession.UNKNOWN

    no_timezone = _envelope(_result(state=_MISSING, timezone_name=None))
    assert no_timezone.session_evidence is not None
    assert no_timezone.session_evidence.exchange_timezone is None


def test_quote_envelope_and_price_observation_retain_exact_session_evidence_identity():
    envelope = _envelope()
    observation = adapt_execution_quote_envelope_to_observation(
        envelope, requested_symbol="KBANK.BK", facts=None,
    )
    assert observation.session_evidence is envelope.session_evidence
    assert observation.market_session == MarketSession.REGULAR
    assert observation.session_evidence is not None
    assert observation.session_evidence.provider_reported_state_normalized == MarketSession.UNKNOWN


def test_provider_state_never_supplies_price_session_or_policy_acceptance():
    evidence = _envelope(_result(state="REGULAR", price=None)).session_evidence
    assert evidence is not None
    observation = build_price_observation(
        requested_symbol="KBANK.BK", asset_id=1, canonical_symbol="KBANK.BK", observed_price=Decimal("10"),
        price_type=PriceKind.MARKET_LAST, source=PriceSource.YAHOO_CHART, currency="THB",
        observed_at=_AT, received_at=_RECEIVED, market_session=MarketSession.REGULAR,
        session_evidence=evidence,
    )
    assert observation.market_session == MarketSession.UNKNOWN
    assessment = assess_price_freshness(
        observation, assessed_at=_RECEIVED,
        policy=PriceFreshnessPolicy("fixture", timedelta(minutes=5), timedelta(minutes=15)),
    )
    assert assessment.status.value == "SESSION_UNKNOWN"


def test_pure_adapter_has_no_clock_registry_network_or_symbol_session_inference():
    module = __import__("services.market_data.session_evidence", fromlist=["*"])
    source = inspect.getsource(module)
    for forbidden in ("datetime.now", "requests", "SessionLocal", ".query(", "get_provider", "endswith(", "startswith("):
        assert forbidden not in source


def test_index_metadata_receives_evidence_without_becoming_identity_or_execution_authority():
    envelope = adapt_yahoo_chart_execution_quote(
        _live_shape(instrument_type="INDEX"), requested_symbol="^SET.BK", received_at=_RECEIVED,
    )
    assert envelope.session_evidence is not None
    assert envelope.session_evidence.observation_session_claim == MarketSession.REGULAR
    assert envelope.requested_symbol == "^SET.BK"
    assert "INDEX" not in envelope.session_evidence.provenance


def test_existing_generic_envelope_can_remain_without_session_evidence():
    envelope = build_execution_quote_envelope(
        requested_symbol="X", provider_symbol="X", provider_id="fixture", provider_version=None,
        price=Decimal("1"), price_kind=PriceKind.MARKET_LAST, currency="THB",
        observed_at=_AT, received_at=_RECEIVED, market_session=MarketSession.UNKNOWN,
    )
    assert envelope.session_evidence is None
