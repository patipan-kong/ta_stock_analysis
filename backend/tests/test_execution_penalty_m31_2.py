"""M31.2 Execution Risk Consumer Migration tests."""
from __future__ import annotations

import ast
import inspect
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import main
import models.asset  # noqa: F401 - registers Asset Registry tables
import models.registry_finding  # noqa: F401 - identity ambiguity findings
from models.database import Base
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
    resolve_execution_instruments,
)
from services.optimizer import execution_penalty
from services.optimizer.execution_penalty import (
    ASSET_DR,
    ASSET_EQUITY,
    ASSET_ETF,
    ASSET_OTHER,
    REGISTRY_FACTS_CLASSIFICATION,
    classify_execution,
    compute_portfolio_execution_context,
)
from services.optimizer.execution_penalty_compat import LEGACY_COMPATIBILITY_FALLBACK


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
        source="m31.2-test",
    )


def _mint(
    db,
    symbol: str,
    *,
    asset_type: AssetType = AssetType.EQUITY,
    tradable: bool = True,
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
        ),
        identifiers=[_provider_symbol(symbol)],
    )


def _risk_projection(meta):
    return {
        "asset_type": meta.asset_type,
        "liquidity_score": meta.liquidity_score,
        "spread_score": meta.spread_score,
        "execution_quality_score": meta.execution_quality_score,
        "execution_risk": meta.execution_risk,
        "execution_warnings": meta.execution_warnings,
        "position_cap_pct": meta.position_cap_pct,
        "slippage_cost_est_pct": meta.slippage_cost_est_pct,
        "combined_score_penalty": meta.combined_score_penalty,
    }


def _unknown_facts(
    symbol: str,
    outcome: ExecutionResolutionOutcome = ExecutionResolutionOutcome.UNKNOWN,
) -> ExecutionInstrumentFacts:
    return ExecutionInstrumentFacts(
        query=symbol,
        resolution_status=outcome,
        instrument_form=ExecutionInstrumentForm.UNKNOWN,
        execution_role=ExecutionRole.UNKNOWN,
        reason="test unresolved Registry identity",
    )


def test_registry_equity_preserves_agreed_execution_risk_output():
    db = make_session()
    _mint(db, "ORDINARY")
    facts = resolve_execution_instrument(db, "ORDINARY")

    legacy = classify_execution("ORDINARY", False, avg_volume=10_000, current_price=100)
    migrated = classify_execution(
        "ORDINARY", False, avg_volume=10_000, current_price=100, facts=facts
    )

    assert _risk_projection(migrated) == _risk_projection(legacy)
    assert migrated.asset_type == ASSET_EQUITY
    assert migrated.classification_source == REGISTRY_FACTS_CLASSIFICATION
    assert migrated.classification_agrees is True
    assert migrated.classification_warning is None


def test_registry_etf_uses_asset_type_without_legacy_ticker_allow_list():
    db = make_session()
    _mint(db, "CUSTOM-FUND", asset_type=AssetType.ETF)
    facts = resolve_execution_instrument(db, "CUSTOM-FUND")

    migrated = classify_execution("CUSTOM-FUND", False, facts=facts)

    assert migrated.asset_type == ASSET_ETF
    assert migrated.liquidity_score == 75.0
    assert migrated.spread_score == 72.0
    assert migrated.execution_quality_score == 73.8
    assert migrated.execution_warnings == []
    assert migrated.position_cap_pct is None
    assert migrated.slippage_cost_est_pct == 0.15
    assert migrated.classification_source == REGISTRY_FACTS_CLASSIFICATION
    assert migrated.classification_agrees is False
    assert "SHADOW_MISMATCH" in migrated.classification_warning


def test_registry_dr_relationship_preserves_dr_execution_risk_behavior():
    db = make_session()
    underlying = _mint(db, "UNDERLYING")
    receipt = _mint(db, "LOCAL-RECEIPT")
    registry.link_relationship(
        db,
        AssetId(receipt.id),
        AssetId(underlying.id),
        RelationshipType.DEPOSITARY_RECEIPT_OF,
    )
    facts = resolve_execution_instrument(db, "LOCAL-RECEIPT")

    migrated = classify_execution("LOCAL-RECEIPT", False, facts=facts)

    assert facts.instrument_form == ExecutionInstrumentForm.DEPOSITARY_RECEIPT
    assert migrated.asset_type == ASSET_DR
    assert migrated.execution_quality_score == 52.2
    assert migrated.execution_risk == "MEDIUM"
    assert migrated.execution_warnings == ["DR - Execution Sensitive", "Low Liquidity"]
    assert migrated.position_cap_pct == 15.0
    assert migrated.slippage_cost_est_pct == 0.5
    assert migrated.combined_score_penalty == 4.0
    assert migrated.classification_source == REGISTRY_FACTS_CLASSIFICATION


def test_unknown_symbol_uses_named_compatibility_fallback_without_authoritative_equity():
    db = make_session()
    facts = resolve_execution_instrument(db, "NOT-IN-REGISTRY")

    meta = classify_execution("NOT-IN-REGISTRY", False, facts=facts)

    assert facts.resolution_status == ExecutionResolutionOutcome.UNKNOWN
    assert facts.instrument_form == ExecutionInstrumentForm.UNKNOWN
    assert meta.resolution_status == "UNKNOWN"
    assert meta.instrument_form == "UNKNOWN"
    assert meta.asset_type == ASSET_EQUITY
    assert meta.classification_source == LEGACY_COMPATIBILITY_FALLBACK
    assert meta.classification_agrees is None
    assert "legacy compatibility fallback" in meta.classification_warning


@pytest.mark.parametrize(
    "outcome",
    [ExecutionResolutionOutcome.AMBIGUOUS, ExecutionResolutionOutcome.NOT_TRADABLE],
)
def test_ambiguous_and_not_tradable_facts_do_not_crash_scoring(outcome):
    if outcome == ExecutionResolutionOutcome.NOT_TRADABLE:
        facts = ExecutionInstrumentFacts(
            query="REFERENCE",
            resolution_status=outcome,
            instrument_form=ExecutionInstrumentForm.OTHER,
            execution_role=ExecutionRole.REFERENCE,
            tradable=False,
            reason="Registry reference",
        )
    else:
        facts = _unknown_facts("AMBIGUOUS", outcome)

    meta = classify_execution(facts.query, False, facts=facts)

    assert meta.resolution_status == outcome.value
    assert meta.execution_risk in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    assert meta.classification_warning


def test_index_reference_is_not_classified_as_executable_index_or_equity():
    db = make_session()
    asset = _mint(db, "^CUSTOM-INDEX", asset_type=AssetType.OTHER, tradable=False)
    registry.record_classification(
        db,
        AssetId(asset.id),
        ClassificationDimension.ASSET_CLASS,
        "INDEX",
        source="official-index-catalogue",
    )
    facts = resolve_execution_instrument(db, "^CUSTOM-INDEX")

    meta = classify_execution("^CUSTOM-INDEX", False, facts=facts)

    assert facts.resolution_status == ExecutionResolutionOutcome.NOT_TRADABLE
    assert meta.asset_type == ASSET_OTHER
    assert meta.asset_type not in {"INDEX", "EQUITY"}
    assert meta.instrument_form == "OTHER"
    assert meta.execution_role == "REFERENCE"
    assert meta.classification_source == REGISTRY_FACTS_CLASSIFICATION
    assert "NOT_TRADABLE" in meta.classification_warning


def test_public_execution_context_retains_legacy_shape_and_adds_typed_diagnostics():
    facts = ExecutionInstrumentFacts(
        query="EQ",
        resolution_status=ExecutionResolutionOutcome.RESOLVED,
        instrument_form=ExecutionInstrumentForm.EQUITY,
        execution_role=ExecutionRole.TRADABLE,
        tradable=True,
    )
    context = compute_portfolio_execution_context(
        {"EQ": {"is_dr": False, "combined_score": 70}},
        {"EQ": facts},
    )

    assert set(
        [
            "per_symbol",
            "has_dr_assets",
            "dr_symbols",
            "high_risk_symbols",
            "dr_position_cap",
            "dr_portfolio_cap",
            "execution_summary",
        ]
    ).issubset(context)
    old_symbol_fields = {
        "asset_type",
        "liquidity_score",
        "spread_score",
        "execution_quality_score",
        "execution_risk",
        "execution_warnings",
        "position_cap_pct",
        "slippage_cost_est_pct",
        "combined_score_penalty",
    }
    assert old_symbol_fields.issubset(context["per_symbol"]["EQ"])
    assert context["per_symbol"]["EQ"]["resolution_status"] == "RESOLVED"
    assert context["per_symbol"]["EQ"]["classification_source"] == REGISTRY_FACTS_CLASSIFICATION


def test_agreed_registered_portfolio_outputs_match_legacy_context():
    scores = {
        "ORDINARY": {"is_dr": False, "combined_score": 70, "current_price": 100},
        "SPY": {"is_dr": False, "combined_score": 80, "current_price": 500},
        "NVDA19.BK": {"is_dr": True, "combined_score": 75, "current_price": 20},
    }
    facts = {
        "ORDINARY": ExecutionInstrumentFacts(
            query="ORDINARY",
            resolution_status=ExecutionResolutionOutcome.RESOLVED,
            instrument_form=ExecutionInstrumentForm.EQUITY,
            execution_role=ExecutionRole.TRADABLE,
        ),
        "SPY": ExecutionInstrumentFacts(
            query="SPY",
            resolution_status=ExecutionResolutionOutcome.RESOLVED,
            instrument_form=ExecutionInstrumentForm.ETF,
            execution_role=ExecutionRole.TRADABLE,
        ),
        "NVDA19.BK": ExecutionInstrumentFacts(
            query="NVDA19.BK",
            resolution_status=ExecutionResolutionOutcome.RESOLVED,
            instrument_form=ExecutionInstrumentForm.DEPOSITARY_RECEIPT,
            execution_role=ExecutionRole.TRADABLE,
        ),
    }

    legacy = compute_portfolio_execution_context(scores)
    migrated = compute_portfolio_execution_context(scores, facts)
    old_symbol_fields = {
        "asset_type",
        "liquidity_score",
        "spread_score",
        "execution_quality_score",
        "execution_risk",
        "execution_warnings",
        "position_cap_pct",
        "slippage_cost_est_pct",
        "combined_score_penalty",
    }

    for symbol in scores:
        assert {
            key: migrated["per_symbol"][symbol][key] for key in old_symbol_fields
        } == {
            key: legacy["per_symbol"][symbol][key] for key in old_symbol_fields
        }
    for key in (
        "has_dr_assets",
        "dr_symbols",
        "high_risk_symbols",
        "dr_position_cap",
        "dr_portfolio_cap",
        "execution_summary",
    ):
        assert migrated[key] == legacy[key]


def test_pure_scoring_module_has_no_database_or_registry_resolution_calls():
    source = inspect.getsource(execution_penalty)
    tree = ast.parse(source)
    imported_names = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    called_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }

    assert "sqlalchemy" not in imported_names
    assert "Session" not in imported_names
    assert "resolve_execution_instrument" not in called_names
    assert "resolve_execution_instruments" not in called_names
    assert ".query(" not in source


def test_batch_facts_resolution_uses_registry_batch_api_once(monkeypatch):
    views = {
        "A": registry_lookup.AssetView(
            asset_id=AssetId(1),
            canonical_symbol="A",
            display_symbol="A",
            market="M",
            exchange="X",
            currency="USD",
            asset_type=AssetType.EQUITY,
        ),
        "B": registry_lookup.AssetView(
            asset_id=AssetId(2),
            canonical_symbol="B",
            display_symbol="B",
            market="M",
            exchange="X",
            currency="USD",
            asset_type=AssetType.ETF,
        ),
    }
    calls = []

    def fake_resolve_many(db, queries):
        calls.append(tuple(queries))
        return {query: views[query] for query in queries}

    monkeypatch.setattr(registry_lookup, "resolve_many", fake_resolve_many)
    monkeypatch.setattr(
        registry_lookup,
        "resolve_asset",
        lambda *_args, **_kwargs: pytest.fail("per-symbol resolve_asset N+1 call"),
    )
    monkeypatch.setattr(execution_facts.registry_service, "get_relationships", lambda *_args: [])

    resolved = resolve_execution_instruments(object(), ["A", "B", "A"])

    assert calls == [("A", "B")]
    assert set(resolved) == {"A", "B"}
    assert resolved["A"].instrument_form == ExecutionInstrumentForm.EQUITY
    assert resolved["B"].instrument_form == ExecutionInstrumentForm.ETF


def test_execution_penalty_contains_no_authoritative_symbol_taxonomy():
    source = inspect.getsource(execution_penalty)
    tree = ast.parse(source)
    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }

    assert "re" not in imported_modules
    assert "frozenset" not in source
    assert ".startswith(" not in source
    assert "_DR_RE" not in source
    assert "_ETF_TICKERS" not in source


def test_optimizer_boundary_batch_resolves_complete_symbol_set_once():
    source = inspect.getsource(main.analyze_optimizer)

    assert source.count("resolve_execution_instruments(") == 1
    assert "tuple(scores_map)" in source
    assert "facts_by_symbol=execution_facts" in source


def test_facts_resolution_failure_degrades_to_unknown_and_never_raises(monkeypatch):
    def fail_batch(*_args, **_kwargs):
        raise RuntimeError("Registry unavailable")

    monkeypatch.setattr(registry_lookup, "resolve_many", fail_batch)

    facts = resolve_execution_instruments(object(), ["SPY", "ORDINARY"])
    context = compute_portfolio_execution_context(
        {
            "SPY": {"is_dr": False, "combined_score": 70},
            "ORDINARY": {"is_dr": False, "combined_score": 60},
        },
        facts,
    )

    assert set(facts) == {"SPY", "ORDINARY"}
    assert all(
        fact.resolution_status == ExecutionResolutionOutcome.UNKNOWN
        for fact in facts.values()
    )
    assert context["per_symbol"]["SPY"]["classification_source"] == LEGACY_COMPATIBILITY_FALLBACK
    assert context["per_symbol"]["ORDINARY"]["classification_source"] == LEGACY_COMPATIBILITY_FALLBACK
