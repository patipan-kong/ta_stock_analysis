"""Contract and resolver tests for M31.1 Execution Instrument Facts."""
import ast
import inspect
import os
import sys
from dataclasses import FrozenInstanceError

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base
import models.asset  # noqa: F401 - registers Asset Registry tables
import models.registry_finding  # noqa: F401 - identity ambiguity records findings
from services import execution_instrument_facts as execution_facts
from services import registry_lookup
from services import registry_service as registry
from services.asset_domain import (
    AssetClaim,
    AssetId,
    AssetType,
    ClassificationDimension,
    IdentifierRecord,
    IdentifierType,
    RelationshipType,
)
from services.execution_instrument_facts import (
    ExecutionInstrumentFacts,
    ExecutionInstrumentForm,
    ExecutionResolutionOutcome,
    ExecutionRole,
    resolve_execution_instrument,
)


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


@pytest.fixture(autouse=True)
def _reset_registry_lookup_cache():
    registry_lookup.invalidate_cache()
    yield
    registry_lookup.invalidate_cache()


def _provider_symbol(value: str) -> IdentifierRecord:
    return IdentifierRecord(
        identifier_type=IdentifierType.PROVIDER_SYMBOL,
        value=value,
        source="m31-test",
    )


def _mint(
    db,
    symbol: str,
    *,
    asset_type: AssetType = AssetType.EQUITY,
    tradable: bool = True,
    fractional_support: bool = False,
    lot_size=None,
    settlement_cycle=None,
):
    return registry.mint_asset(
        db,
        AssetClaim(
            canonical_symbol=symbol,
            asset_type=asset_type,
            market="TEST_MARKET",
            exchange="TEST_EXCHANGE",
            currency="USD",
            tradable=tradable,
            fractional_support=fractional_support,
            lot_size=lot_size,
            settlement_cycle=settlement_cycle,
        ),
        identifiers=[_provider_symbol(symbol)],
    )


def test_contract_has_exact_resolution_outcomes_and_instrument_forms():
    assert {item.value for item in ExecutionResolutionOutcome} == {
        "RESOLVED",
        "UNKNOWN",
        "AMBIGUOUS",
        "NOT_TRADABLE",
    }
    assert {item.value for item in ExecutionInstrumentForm} == {
        "EQUITY",
        "ETF",
        "DEPOSITARY_RECEIPT",
        "OTHER",
        "UNKNOWN",
    }
    assert "INDEX" not in {item.value for item in ExecutionInstrumentForm}


def test_contract_is_immutable():
    facts = ExecutionInstrumentFacts(
        query="UNKNOWN",
        resolution_status=ExecutionResolutionOutcome.UNKNOWN,
        instrument_form=ExecutionInstrumentForm.UNKNOWN,
        execution_role=ExecutionRole.UNKNOWN,
    )

    with pytest.raises(FrozenInstanceError):
        facts.query = "MUTATED"


def test_registry_backed_equity_uses_asset_type_and_preserves_capabilities():
    db = make_session()
    asset = _mint(
        db,
        "ORDINARY-SHARE",
        fractional_support=True,
        lot_size=100,
        settlement_cycle="T+2",
    )

    facts = resolve_execution_instrument(db, "ORDINARY-SHARE")

    assert facts.resolution_status == ExecutionResolutionOutcome.RESOLVED
    assert facts.instrument_form == ExecutionInstrumentForm.EQUITY
    assert facts.execution_role == ExecutionRole.TRADABLE
    assert facts.asset_id == AssetId(asset.id)
    assert facts.registry_asset_type == AssetType.EQUITY
    assert facts.tradable is True
    assert facts.fractional_support is True
    assert facts.lot_size == 100
    assert facts.settlement_cycle == "T+2"
    form_source = next(item for item in facts.provenance if item.fact == "instrument_form")
    assert form_source.source_field == "models.asset.Asset.asset_type"
    assert form_source.source_value == AssetType.EQUITY.value


def test_registry_backed_etf_uses_asset_type_without_ticker_allow_list():
    db = make_session()
    _mint(db, "CUSTOM-FUND-SYMBOL", asset_type=AssetType.ETF)

    facts = resolve_execution_instrument(db, "CUSTOM-FUND-SYMBOL")

    assert facts.resolution_status == ExecutionResolutionOutcome.RESOLVED
    assert facts.instrument_form == ExecutionInstrumentForm.ETF
    form_source = next(item for item in facts.provenance if item.fact == "instrument_form")
    assert form_source.source_field == "models.asset.Asset.asset_type"
    assert form_source.source_value == AssetType.ETF.value


def test_etf_asset_type_is_not_mistaken_for_index_reference():
    db = make_session()
    asset = _mint(db, "INDEX-TRACKER", asset_type=AssetType.ETF)
    registry.record_classification(
        db,
        AssetId(asset.id),
        ClassificationDimension.ASSET_CLASS,
        "INDEX",
        source="fund-classification",
    )

    facts = resolve_execution_instrument(db, "INDEX-TRACKER")

    assert facts.resolution_status == ExecutionResolutionOutcome.RESOLVED
    assert facts.instrument_form == ExecutionInstrumentForm.ETF
    assert facts.execution_role == ExecutionRole.TRADABLE


def test_dr_form_comes_only_from_outgoing_registry_relationship():
    db = make_session()
    underlying = _mint(db, "UNDERLYING")
    receipt = _mint(db, "LOCAL-RECEIPT")
    registry.link_relationship(
        db,
        AssetId(receipt.id),
        AssetId(underlying.id),
        RelationshipType.DEPOSITARY_RECEIPT_OF,
    )

    receipt_facts = resolve_execution_instrument(db, "LOCAL-RECEIPT")
    underlying_facts = resolve_execution_instrument(db, "UNDERLYING")

    assert receipt_facts.resolution_status == ExecutionResolutionOutcome.RESOLVED
    assert receipt_facts.instrument_form == ExecutionInstrumentForm.DEPOSITARY_RECEIPT
    assert receipt_facts.underlying_asset_id == AssetId(underlying.id)
    form_source = next(
        item for item in receipt_facts.provenance if item.fact == "instrument_form"
    )
    assert form_source.source_field == "models.asset.AssetRelationship.relationship_type"
    assert form_source.source_value == RelationshipType.DEPOSITARY_RECEIPT_OF.value
    assert underlying_facts.instrument_form == ExecutionInstrumentForm.EQUITY
    assert underlying_facts.underlying_asset_id is None


def test_unknown_symbol_is_explicit_unknown():
    db = make_session()

    facts = resolve_execution_instrument(db, "NOT-IN-REGISTRY")

    assert facts.resolution_status == ExecutionResolutionOutcome.UNKNOWN
    assert facts.instrument_form == ExecutionInstrumentForm.UNKNOWN
    assert facts.execution_role == ExecutionRole.UNKNOWN
    assert facts.asset_id is None
    assert facts.reason


def test_historical_weak_identity_is_explicit_ambiguous():
    db = make_session()
    asset = _mint(db, "RECYCLED")
    registry.attach_identifier(db, AssetId(asset.id), _provider_symbol("REPLACEMENT"))
    registry_lookup.invalidate_cache("RECYCLED")

    facts = resolve_execution_instrument(db, "RECYCLED")

    assert facts.resolution_status == ExecutionResolutionOutcome.AMBIGUOUS
    assert facts.instrument_form == ExecutionInstrumentForm.UNKNOWN
    assert facts.execution_role == ExecutionRole.UNKNOWN
    assert facts.asset_id is None
    assert facts.provenance[0].source_value == "AMBIGUOUS"


def test_non_tradable_index_is_reference_and_not_an_instrument_form():
    db = make_session()
    asset = _mint(
        db,
        "SET-COMPOSITE-REFERENCE",
        asset_type=AssetType.OTHER,
        tradable=False,
    )
    registry.record_classification(
        db,
        AssetId(asset.id),
        ClassificationDimension.ASSET_CLASS,
        "INDEX",
        source="official-index-catalogue",
    )

    facts = resolve_execution_instrument(db, "SET-COMPOSITE-REFERENCE")

    assert facts.resolution_status == ExecutionResolutionOutcome.NOT_TRADABLE
    assert facts.instrument_form == ExecutionInstrumentForm.OTHER
    assert facts.execution_role == ExecutionRole.REFERENCE
    role_source = next(item for item in facts.provenance if item.fact == "execution_role")
    assert role_source.source_field == "models.asset.AssetClassification.value"
    assert role_source.source_value == "INDEX"
    assert role_source.evidence_source == "official-index-catalogue"


def test_incomplete_registry_metadata_returns_unknown_instead_of_fallback():
    db = make_session()
    asset = _mint(db, "INCOMPLETE")
    asset.currency = ""
    db.flush()

    facts = resolve_execution_instrument(db, "INCOMPLETE")

    assert facts.resolution_status == ExecutionResolutionOutcome.UNKNOWN
    assert facts.instrument_form == ExecutionInstrumentForm.UNKNOWN
    assert facts.asset_id is None
    assert "currency" in facts.reason


@pytest.mark.parametrize(
    "heuristic_looking_symbol",
    [
        "SPY",          # formerly present in the execution ETF allow-list
        "FAKE19.BK",    # matches the former DR symbol shape
        "^SET",         # matches the former caret-prefix index rule
        "PLAIN-EQUITY", # formerly reached fallback-to-EQUITY
    ],
)
def test_symbol_shape_never_produces_execution_classification(heuristic_looking_symbol):
    db = make_session()

    facts = resolve_execution_instrument(db, heuristic_looking_symbol)

    assert facts.resolution_status == ExecutionResolutionOutcome.UNKNOWN
    assert facts.instrument_form == ExecutionInstrumentForm.UNKNOWN
    assert facts.asset_id is None


def test_resolver_source_contains_no_symbol_heuristic_implementation():
    source = inspect.getsource(execution_facts)
    tree = ast.parse(source)
    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    referenced_names = {
        node.id for node in ast.walk(tree) if isinstance(node, ast.Name)
    }

    assert "re" not in imported_modules
    assert "frozenset" not in source
    assert ".startswith(" not in source
    assert "_DR_RE" not in referenced_names
