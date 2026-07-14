"""M31.3 non-blocking execution eligibility shadow-adoption tests."""
from __future__ import annotations

import ast
import copy
import inspect
import logging
import os
import sys
from datetime import datetime

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import main
import models.asset  # noqa: F401 - register Registry tables
import models.registry_finding  # noqa: F401 - register identity findings
from models.database import AnalysisCache, Base, Portfolio, PortfolioItem, Transaction, Workspace
from models.registry_finding import RegistryFinding
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
from services.execution_eligibility import (
    ExecutionEligibilityOutcome,
    ShadowExecutionAction,
    consult_execution_eligibility_shadow,
    evaluate_execution_eligibility,
)
from services.execution_instrument_facts import (
    ExecutionFactProvenance,
    ExecutionInstrumentFacts,
    ExecutionInstrumentForm,
    ExecutionResolutionOutcome,
    ExecutionRole,
    resolve_execution_instrument,
    resolve_execution_instruments,
)
from services import execution_eligibility
from services.execution_eligibility_shadow import (
    resolve_execution_eligibility_shadow_facts,
)
from services import execution_plan
from services import portfolio_transactions


def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


@pytest.fixture(autouse=True)
def _reset_registry_cache():
    registry_lookup.invalidate_cache()
    yield
    registry_lookup.invalidate_cache()


def _identifier(symbol: str) -> IdentifierRecord:
    return IdentifierRecord(
        identifier_type=IdentifierType.PROVIDER_SYMBOL,
        value=symbol,
        source="m31.3-test",
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
        identifiers=[_identifier(symbol)],
    )


def _seed_portfolio(db, *, cash: float = 100_000.0):
    ws = Workspace(name="M31.3")
    db.add(ws)
    db.flush()
    portfolio = Portfolio(workspace_id=ws.id, name="Shadow", cash_balance=cash)
    db.add(portfolio)
    db.commit()
    return ws, portfolio


@pytest.mark.parametrize(
    ("symbol", "asset_type", "expected_form"),
    [
        ("ORDINARY", AssetType.EQUITY, ExecutionInstrumentForm.EQUITY),
        ("CUSTOM-ETF", AssetType.ETF, ExecutionInstrumentForm.ETF),
    ],
)
def test_registry_resolved_equity_and_etf_are_shadow_eligible(
    symbol, asset_type, expected_form
):
    db = make_session()
    _mint(db, symbol, asset_type=asset_type)

    facts = resolve_execution_instrument(db, symbol)
    result = evaluate_execution_eligibility(facts)

    assert facts.instrument_form == expected_form
    assert result.outcome == ExecutionEligibilityOutcome.ELIGIBLE
    assert result.eligible is True


def test_registry_relationship_backed_dr_is_shadow_eligible():
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
    result = evaluate_execution_eligibility(facts)

    assert facts.instrument_form == ExecutionInstrumentForm.DEPOSITARY_RECEIPT
    assert result.outcome == ExecutionEligibilityOutcome.ELIGIBLE


def test_non_tradable_registry_index_is_reference_only():
    db = make_session()
    asset = _mint(db, "INDEX-REFERENCE", asset_type=AssetType.OTHER, tradable=False)
    registry.record_classification(
        db,
        AssetId(asset.id),
        ClassificationDimension.ASSET_CLASS,
        "INDEX",
        source="official-index-catalogue",
    )

    facts = resolve_execution_instrument(db, "INDEX-REFERENCE")
    result = evaluate_execution_eligibility(facts)

    assert facts.resolution_status == ExecutionResolutionOutcome.NOT_TRADABLE
    assert facts.execution_role == ExecutionRole.REFERENCE
    assert result.outcome == ExecutionEligibilityOutcome.REFERENCE_ONLY
    assert result.eligible is False


def test_unknown_legacy_action_logs_structured_disagreement_without_equity_relabel(caplog):
    facts = ExecutionInstrumentFacts(
        query="UNKNOWN",
        resolution_status=ExecutionResolutionOutcome.UNKNOWN,
        instrument_form=ExecutionInstrumentForm.UNKNOWN,
        execution_role=ExecutionRole.UNKNOWN,
        reason="no Registry identity",
        provenance=(
            ExecutionFactProvenance(
                fact="identity",
                source_field="services.registry_lookup.resolve_asset",
                source_value="UNKNOWN",
            ),
        ),
    )
    logger = logging.getLogger("m31.3.unknown")

    with caplog.at_level(logging.WARNING, logger=logger.name):
        records = consult_execution_eligibility_shadow(
            [ShadowExecutionAction("UNKNOWN", "BUY")],
            {"UNKNOWN": facts},
            legacy_path="TEST_BOUNDARY",
            logger=logger,
        )

    assert records[0].shadow_eligibility == ExecutionEligibilityOutcome.UNKNOWN_IDENTITY
    assert records[0].disagreement is True
    payload = caplog.records[-1].execution_eligibility
    assert payload["requested_symbol"] == "UNKNOWN"
    assert payload["legacy_action"] == "BUY"
    assert payload["legacy_permitted"] is True
    assert payload["instrument_form"] == "UNKNOWN"
    assert payload["instrument_form"] != "EQUITY"
    assert payload["provenance"][0]["source_value"] == "UNKNOWN"


def test_ambiguous_identity_remains_explicit():
    facts = ExecutionInstrumentFacts(
        query="RECYCLED",
        resolution_status=ExecutionResolutionOutcome.AMBIGUOUS,
        instrument_form=ExecutionInstrumentForm.UNKNOWN,
        execution_role=ExecutionRole.UNKNOWN,
        reason="multiple Registry candidates",
    )

    result = evaluate_execution_eligibility(facts)

    assert result.outcome == ExecutionEligibilityOutcome.AMBIGUOUS_IDENTITY
    assert result.eligible is False
    assert result.registry_failure is False


def test_registry_infrastructure_failure_is_typed_and_never_escapes(monkeypatch):
    monkeypatch.setattr(
        registry_lookup,
        "resolve_many",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("registry offline")),
    )

    facts = resolve_execution_instruments(object(), ["A", "B"])

    assert set(facts) == {"A", "B"}
    for item in facts.values():
        result = evaluate_execution_eligibility(item)
        assert item.resolution_status == ExecutionResolutionOutcome.UNKNOWN
        assert item.resolution_error == "RuntimeError: registry offline"
        assert result.outcome == ExecutionEligibilityOutcome.REGISTRY_FAILURE
        assert result.registry_failure is True


def test_optimizer_shadow_consultation_cannot_mutate_output_when_enabled_or_failed():
    result = {
        "target_allocations": [
            {"symbol": "A", "action": "BUY", "target_weight": 10.0},
            {"symbol": "B", "action": "HOLD", "target_weight": 20.0},
        ],
        "execution_optimization": {"status": "READY"},
    }
    before = copy.deepcopy(result)
    facts = {
        "A": ExecutionInstrumentFacts(
            query="A",
            resolution_status=ExecutionResolutionOutcome.RESOLVED,
            instrument_form=ExecutionInstrumentForm.EQUITY,
            execution_role=ExecutionRole.TRADABLE,
            tradable=True,
        )
    }
    actions = [ShadowExecutionAction("A", "BUY")]
    logger = logging.getLogger("m31.3.optimizer")

    consult_execution_eligibility_shadow(
        actions,
        facts,
        legacy_path="OPTIMIZER_TARGET_ALLOCATION",
        logger=logger,
    )

    class FailedLogger:
        def debug(self, *_args, **_kwargs):
            raise RuntimeError("telemetry sink failed")

        warning = debug
        exception = debug

    consult_execution_eligibility_shadow(
        actions,
        facts,
        legacy_path="OPTIMIZER_TARGET_ALLOCATION",
        logger=FailedLogger(),
    )
    assert result == before


def test_execution_plan_output_identical_when_shadow_resolution_fails(monkeypatch):
    db = make_session()
    ws, portfolio = _seed_portfolio(db)
    args = dict(
        portfolio_id=portfolio.id,
        workspace_id=ws.id,
        buy_symbols=["NEWCO"],
        sizing_suggestions=[{"symbol": "NEWCO", "suggested_pct": 10, "signal": "BUY"}],
        timing_scores={"NEWCO": 70},
        db=db,
    )

    enabled = execution_plan.build_execution_plan(**args).model_dump()
    monkeypatch.setattr(
        execution_plan,
        "resolve_execution_eligibility_shadow_facts",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("offline")),
    )
    failed = execution_plan.build_execution_plan(**args).model_dump()

    assert failed == enabled


def _run_transaction_sequence(db):
    ws, portfolio = _seed_portfolio(db)
    initial = portfolio_transactions.execute_initial_position(
        db,
        ws.id,
        portfolio.id,
        "UNKNOWNCO",
        shares=10,
        avg_cost=5,
        transaction_date=datetime(2026, 1, 1),
    )
    buy = portfolio_transactions.execute_buy(
        db,
        ws.id,
        portfolio.id,
        "UNKNOWNCO",
        shares=5,
        price_per_share=6,
        transaction_date=datetime(2026, 1, 2),
    )
    sell = portfolio_transactions.execute_sell(
        db,
        ws.id,
        portfolio.id,
        "UNKNOWNCO",
        shares=3,
        price_per_share=7,
        transaction_date=datetime(2026, 1, 3),
        remove_if_zero=False,
    )
    responses = [initial, buy, sell]
    rows = db.query(Transaction).order_by(Transaction.id).all()
    item = db.query(PortfolioItem).filter_by(portfolio_id=portfolio.id).one()
    db.refresh(portfolio)
    return (
        [{k: v for k, v in response.items() if k != "transaction_id"} for response in responses],
        [
            (
                row.transaction_type,
                row.symbol,
                row.shares,
                row.price_per_share,
                row.total_amount,
                row.fees,
                row.taxes,
                row.asset_id,
            )
            for row in rows
        ],
        (portfolio.cash_balance, item.shares, item.avg_cost),
    )


def test_transaction_results_and_persisted_rows_identical_when_shadow_fails(monkeypatch):
    enabled_db = make_session()
    enabled = _run_transaction_sequence(enabled_db)

    monkeypatch.setattr(
        portfolio_transactions,
        "resolve_execution_eligibility_shadow_facts",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("offline")),
    )
    failed_db = make_session()
    failed = _run_transaction_sequence(failed_db)

    assert failed == enabled
    assert [row[0] for row in failed[1]] == ["INITIAL_POSITION", "BUY", "SELL"]


def test_execution_plan_batch_resolves_all_active_symbols_once(monkeypatch):
    db = make_session()
    ws, portfolio = _seed_portfolio(db)
    calls = []

    def fake_batch(_db, symbols):
        calls.append(tuple(symbols))
        return {
            symbol: ExecutionInstrumentFacts(
                query=symbol,
                resolution_status=ExecutionResolutionOutcome.UNKNOWN,
                instrument_form=ExecutionInstrumentForm.UNKNOWN,
                execution_role=ExecutionRole.UNKNOWN,
                reason="fixture has no Registry identity",
            )
            for symbol in set(symbols)
        }

    monkeypatch.setattr(
        execution_plan,
        "resolve_execution_eligibility_shadow_facts",
        fake_batch,
    )

    execution_plan.build_execution_plan(
        portfolio_id=portfolio.id,
        workspace_id=ws.id,
        buy_symbols=["A", "B"],
        sizing_suggestions=[
            {"symbol": "A", "suggested_pct": 10, "signal": "BUY"},
            {"symbol": "B", "suggested_pct": 5, "signal": "BUY"},
        ],
        timing_scores=None,
        db=db,
    )

    assert calls == [("A", "B")]


def test_shadow_resolution_rolls_back_registry_ambiguity_findings():
    db = make_session()
    asset = _mint(db, "RECYCLED")
    registry.attach_identifier(db, AssetId(asset.id), _identifier("REPLACEMENT"))
    db.commit()
    registry_lookup.invalidate_cache("RECYCLED")

    facts = resolve_execution_eligibility_shadow_facts(db, ["RECYCLED"])

    assert facts["RECYCLED"].resolution_status == ExecutionResolutionOutcome.AMBIGUOUS
    assert db.query(RegistryFinding).count() == 0


def test_eligibility_predicate_has_no_db_or_registry_resolution_access():
    source = inspect.getsource(execution_eligibility)
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
    assert ".query(" not in source
    assert "resolve_execution_instrument" not in called_names
    assert "resolve_execution_instruments" not in called_names


def test_shadow_adoption_sources_add_no_symbol_taxonomy_heuristics():
    sources = [
        inspect.getsource(module)
        for module in (execution_eligibility, execution_plan, portfolio_transactions)
    ]
    imported_modules = {
        alias.name
        for source in sources
        for node in ast.walk(ast.parse(source))
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    combined_source = "\n".join(sources)

    assert "re" not in imported_modules
    assert "_DR_RE" not in combined_source
    assert "_ETF_TICKERS" not in combined_source
    assert 'startswith("^")' not in combined_source
    assert "fallback-to-equity" not in combined_source.lower()


def test_selected_boundary_placement_is_post_legacy_result():
    optimizer_source = inspect.getsource(main.analyze_optimizer)
    plan_source = inspect.getsource(execution_plan.build_execution_plan)
    transaction_source = inspect.getsource(portfolio_transactions.execute_buy)

    assert optimizer_source.index('result["execution_optimization"]') < optimizer_source.index(
        'legacy_path="OPTIMIZER_TARGET_ALLOCATION"'
    )
    assert plan_source.index("result = ExecutionPlanResult(") < plan_source.index(
        'legacy_path="EXECUTION_PLAN"'
    )
    assert transaction_source.index("db.commit()") < transaction_source.index(
        "_observe_transaction_execution_eligibility"
    )
