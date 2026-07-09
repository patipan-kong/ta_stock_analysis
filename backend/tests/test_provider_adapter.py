"""Tests for the Provider Adapter Layer (Milestone M4).

Validates:
  1. YahooFinanceAdapter.normalize() maps vendor fields into
     ProviderObservation faithfully (no interpretation).
  2. build_claim() produces a ResolutionClaim with correctly provenance-
     tagged identifiers.
  3. Absent vendor fields stay absent — never fabricated, never defaulted.
  4. Empty-string vendor fields are treated as absent, not as identity
     evidence.
  5. ProviderCapabilities is declared, inert data (no behavior reads it).
  6. A new provider costs exactly one method (normalize()) to add — proven
     with a throwaway adapter defined only in this test file.
  7. An adapter-built claim is indistinguishable to identity_resolver from
     a hand-built one: resolve() behaves identically either way.
  8. Adapters are architecturally DB-free: no method takes a Session.

All tests are pure/in-memory; no network calls, no real yfinance payloads.
"""
import inspect
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base
import models.asset  # noqa: F401 — registers Asset* tables on Base.metadata
import models.registry_finding  # noqa: F401 — registers RegistryFinding table
from services import identity_resolver as resolver
from services import registry_service as svc
from services.asset_domain import AssetClaim, AssetType, IdentifierRecord, IdentifierType
from services.provider_adapter import ProviderAdapter, YahooFinanceAdapter
from services.provider_domain import ProviderCapabilities, ProviderObservation
from services.resolver_domain import ResolutionVerdict


def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


YFINANCE_INFO = {
    "symbol": "ADVANC.BK",
    "longName": "Advanced Info Service Public Company Limited",
    "shortName": "ADVANC",
    "exchange": "SET",
    "market": "th_market",
    "currency": "THB",
}


# ── normalize() ──────────────────────────────────────────────────────────

def test_normalize_maps_yfinance_fields():
    observation = YahooFinanceAdapter().normalize(YFINANCE_INFO)
    assert observation.provider_symbol == "ADVANC.BK"
    assert observation.name == "Advanced Info Service Public Company Limited"
    assert observation.exchange == "SET"
    assert observation.market == "th_market"
    assert observation.currency == "THB"
    assert observation.isin is None
    assert observation.cusip is None
    assert observation.observed_at is not None


def test_normalize_falls_back_to_short_name():
    raw = dict(YFINANCE_INFO)
    del raw["longName"]
    observation = YahooFinanceAdapter().normalize(raw)
    assert observation.name == "ADVANC"


def test_empty_string_fields_become_none_not_fabricated():
    raw = dict(YFINANCE_INFO, currency="", exchange=None)
    observation = YahooFinanceAdapter().normalize(raw)
    assert observation.currency is None
    assert observation.exchange is None


def test_observation_is_immutable():
    observation = YahooFinanceAdapter().normalize(YFINANCE_INFO)
    with pytest.raises(Exception):
        observation.provider_symbol = "OTHER"  # type: ignore[misc]


# ── build_claim() ────────────────────────────────────────────────────────

def test_build_claim_produces_provider_symbol_identifier_with_provenance():
    claim = YahooFinanceAdapter().build_claim(YFINANCE_INFO)
    assert len(claim.identifiers) == 1
    identifier = claim.identifiers[0]
    assert identifier.identifier_type == IdentifierType.PROVIDER_SYMBOL
    assert identifier.value == "ADVANC.BK"
    assert identifier.source == "provider:yahoo_finance"
    assert identifier.as_of is not None
    assert claim.market == "th_market"
    assert claim.exchange == "SET"
    assert claim.currency == "THB"


def test_build_claim_includes_isin_when_present():
    raw = dict(YFINANCE_INFO, isin="TH0001010006")
    claim = YahooFinanceAdapter().build_claim(raw)
    types = {i.identifier_type for i in claim.identifiers}
    assert types == {IdentifierType.PROVIDER_SYMBOL, IdentifierType.ISIN}
    isin_record = next(i for i in claim.identifiers if i.identifier_type == IdentifierType.ISIN)
    assert isin_record.value == "TH0001010006"
    assert isin_record.source == "provider:yahoo_finance"


def test_build_claim_omits_absent_identifier_types():
    claim = YahooFinanceAdapter().build_claim(YFINANCE_INFO)
    types = {i.identifier_type for i in claim.identifiers}
    assert IdentifierType.CUSIP not in types
    assert IdentifierType.SEDOL not in types
    assert IdentifierType.FIGI not in types


def test_build_claim_passes_through_requested_by_and_note():
    claim = YahooFinanceAdapter().build_claim(
        YFINANCE_INFO, requested_by="tester", note="manual check"
    )
    assert claim.requested_by == "tester"
    assert claim.note == "manual check"


def test_build_claim_with_no_symbol_produces_no_identifiers():
    claim = YahooFinanceAdapter().build_claim({})
    assert claim.identifiers == ()


# ── ProviderCapabilities — declarative only ─────────────────────────────

def test_capabilities_declared_and_inert():
    caps = YahooFinanceAdapter.capabilities
    assert isinstance(caps, ProviderCapabilities)
    assert IdentifierType.PROVIDER_SYMBOL in caps.identifier_types
    assert IdentifierType.ISIN in caps.identifier_types
    assert caps.supports_search is False


# ── Extensibility: a new provider costs one method ──────────────────────

class _FakeBloombergAdapter(ProviderAdapter):
    """Defined only in this test file to prove the abstraction, not shipped
    as production code (no such integration exists yet)."""

    provider_name = "fake_bloomberg"
    capabilities = ProviderCapabilities(identifier_types=frozenset({IdentifierType.FIGI}))

    def normalize(self, raw):
        return ProviderObservation(figi=raw.get("figi"))


def test_second_adapter_requires_only_normalize_override():
    claim = _FakeBloombergAdapter().build_claim({"figi": "BBG000BLNNH6"})
    assert len(claim.identifiers) == 1
    identifier = claim.identifiers[0]
    assert identifier.identifier_type == IdentifierType.FIGI
    assert identifier.source == "provider:fake_bloomberg"


# ── Architecture: adapters are DB-free ──────────────────────────────────

def test_adapter_methods_take_no_session_parameter():
    for method in (ProviderAdapter.normalize, ProviderAdapter.build_claim):
        params = inspect.signature(method).parameters
        assert "db" not in params
        assert "session" not in params


# ── End-to-end: the Registry cannot tell a claim came from an adapter ───

def test_adapter_built_claim_resolves_like_a_hand_built_one():
    db = make_session()
    asset = svc.mint_asset(
        db,
        AssetClaim(
            canonical_symbol="ADVANC",
            asset_type=AssetType.EQUITY,
            market="TH",
            exchange="SET",
            currency="THB",
        ),
    )
    svc.attach_identifier(
        db,
        asset.id,
        IdentifierRecord(
            identifier_type=IdentifierType.PROVIDER_SYMBOL,
            value="ADVANC.BK",
            source="seed",
        ),
    )

    claim = YahooFinanceAdapter().build_claim(YFINANCE_INFO)
    result = resolver.resolve(db, claim)

    assert result.verdict == ResolutionVerdict.RESOLVED
    assert result.resolved_asset_id == asset.id
