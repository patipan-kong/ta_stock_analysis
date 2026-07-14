"""M31.5 execution Registry cutover preparation tests."""
from __future__ import annotations

import ast
import inspect
import json
import logging
import os
import sys
from dataclasses import asdict
from datetime import datetime

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models.asset  # noqa: F401
import models.registry_finding  # noqa: F401
from models.asset import Asset, AssetRelationship
from models.database import (
    Base,
    OptimizerHistory,
    Portfolio,
    PortfolioItem,
    Transaction,
    Watchlist,
    Workspace,
)
from models.registry_finding import RegistryFinding
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
from services.execution_cutover_config import (
    EXECUTION_ELIGIBILITY_CUTOVER_MODE_ENV,
    ExecutionCutoverConfigurationError,
    ExecutionEligibilityCutoverMode,
    get_execution_eligibility_cutover_mode,
    load_execution_eligibility_cutover_mode,
    reset_execution_eligibility_cutover_mode_cache,
)
from services.execution_eligibility import (
    ExecutionEligibilityOutcome,
    ShadowExecutionAction,
    consult_execution_eligibility_shadow,
    evaluate_execution_eligibility,
)
from services.execution_eligibility_observability import (
    execution_eligibility_counter_snapshot,
    reset_execution_eligibility_observability,
)
from services.execution_instrument_facts import (
    ExecutionInstrumentFacts,
    ExecutionInstrumentForm,
    ExecutionResolutionOutcome,
    ExecutionRole,
    resolve_execution_instrument,
)
from services.execution_registry_preflight import (
    ExecutionPreflightOutcome,
    build_execution_registry_preflight,
)
from services.execution_registry_remediation import (
    apply_registry_remediation,
    parse_registry_remediation_manifest,
)
from services.optimizer.execution_penalty import classify_execution
from services.optimizer.execution_penalty_compat import LEGACY_COMPATIBILITY_FALLBACK
from services import execution_plan, portfolio_transactions


def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


@pytest.fixture(autouse=True)
def _reset_process_state(monkeypatch):
    registry_lookup.invalidate_cache()
    reset_execution_eligibility_observability()
    reset_execution_eligibility_cutover_mode_cache()
    monkeypatch.delenv(EXECUTION_ELIGIBILITY_CUTOVER_MODE_ENV, raising=False)
    yield
    registry_lookup.invalidate_cache()
    reset_execution_eligibility_observability()
    reset_execution_eligibility_cutover_mode_cache()


def _identifier(symbol: str, source: str = "m31.5-test") -> IdentifierRecord:
    return IdentifierRecord(
        identifier_type=IdentifierType.PROVIDER_SYMBOL,
        value=symbol,
        source=source,
    )


def _mint(db, symbol: str, *, asset_type=AssetType.EQUITY, tradable=True):
    return registry.mint_asset(
        db,
        AssetClaim(
            canonical_symbol=symbol,
            display_symbol=symbol,
            asset_type=asset_type,
            market="TEST",
            exchange="TESTX",
            currency="USD",
            tradable=tradable,
            lot_size=1,
            settlement_cycle="T+2",
        ),
        identifiers=[_identifier(symbol)],
    )


def _workspace_portfolio(db):
    workspace = Workspace(name="M31.5")
    db.add(workspace)
    db.flush()
    portfolio = Portfolio(workspace_id=workspace.id, name="Preparation", cash_balance=100_000)
    db.add(portfolio)
    db.flush()
    return workspace, portfolio


def _manifest(*instructions):
    return parse_registry_remediation_manifest({"version": 1, "instructions": list(instructions)})


def _mint_instruction(
    instruction_id: str,
    symbol: str,
    *,
    approved: bool,
    operation: str = "MINT_ASSET",
    asset_type: str = "EQUITY",
    tradable: bool = True,
    underlying_asset_id: int | None = None,
):
    row = {
        "instruction_id": instruction_id,
        "approved": approved,
        "operation": operation,
        "evidence_source": "approved exchange instrument master",
        "evidence_note": "reviewed by Registry steward",
        "canonical_symbol": symbol,
        "display_symbol": symbol,
        "asset_type": asset_type,
        "market": "TEST",
        "exchange": "TESTX",
        "currency": "USD",
        "tradable": tradable,
        "lot_size": 1,
        "settlement_cycle": "T+2",
        "identifiers": [
            {
                "identifier_type": "PROVIDER_SYMBOL",
                "value": symbol,
                "source": "approved exchange instrument master",
            }
        ],
    }
    if underlying_asset_id is not None:
        row["underlying_asset_id"] = underlying_asset_id
    return row


def test_preflight_covers_operational_populations_and_is_read_only():
    db = make_session()
    workspace, portfolio = _workspace_portfolio(db)
    _mint(db, "KNOWN")
    db.add_all(
        [
            PortfolioItem(
                workspace_id=workspace.id,
                portfolio_id=portfolio.id,
                symbol="KNOWN",
                shares=1,
                avg_cost=10,
            ),
            PortfolioItem(
                workspace_id=workspace.id,
                portfolio_id=portfolio.id,
                symbol="UNKNOWN-HOLDING",
                shares=1,
                avg_cost=10,
            ),
            Watchlist(workspace_id=workspace.id, symbol="UNKNOWN-WATCH"),
            Transaction(
                workspace_id=workspace.id,
                portfolio_id=portfolio.id,
                symbol="UNKNOWN-TX",
                transaction_type="BUY",
                shares=1,
                price_per_share=1,
                total_amount=1,
                fees=0,
                transaction_date=datetime(2026, 7, 14),
            ),
            OptimizerHistory(
                workspace_id=workspace.id,
                portfolio_id=portfolio.id,
                portfolio_name=portfolio.name,
                analyzed_at=datetime(2026, 7, 14),
                swap_count=1,
                result_json=json.dumps(
                    {
                        "target_allocations": [
                            {"symbol": "UNKNOWN-ACTION", "action": "BUY"},
                            {"symbol": "KNOWN", "action": "HOLD"},
                        ]
                    }
                ),
            ),
        ]
    )
    db.commit()

    before_findings = db.query(RegistryFinding).count()
    report = build_execution_registry_preflight(db, workspace_id=workspace.id)

    populations = {row.population for row in report.rows}
    assert "current_holdings" in populations
    assert "workspace_watchlist" in populations
    assert f"optimizer_reachable:portfolio_id={portfolio.id}" in populations
    assert "latest_actionable_optimizer_allocations" in populations
    assert "historical_executable_transactions" in populations
    assert "configured_etf_review" in populations
    assert "configured_dr_alias_review" in populations
    assert "configured_reference_review" in populations
    by_key = {(row.population, row.requested_symbol): row for row in report.rows}
    assert by_key[("current_holdings", "KNOWN")].outcome == ExecutionPreflightOutcome.ELIGIBLE
    assert by_key[("current_holdings", "UNKNOWN-HOLDING")].outcome == ExecutionPreflightOutcome.UNKNOWN_IDENTITY
    assert by_key[("latest_actionable_optimizer_allocations", "UNKNOWN-ACTION")].outcome == ExecutionPreflightOutcome.UNKNOWN_IDENTITY
    assert by_key[("historical_executable_transactions", "UNKNOWN-TX")].outcome == ExecutionPreflightOutcome.UNKNOWN_IDENTITY
    assert report.read_only is True
    assert db.query(RegistryFinding).count() == before_findings

    holding_readiness = next(
        item for item in report.native_asset_id_readiness if item.table == "portfolio_items"
    )
    assert holding_readiness.total_rows == 2
    assert holding_readiness.missing_but_resolvable == 1
    assert holding_readiness.unresolved_rows == 1
    assert holding_readiness.dry_run_proposals[0].proposed_asset_id > 0
    assert db.query(PortfolioItem).filter(PortfolioItem.asset_id.isnot(None)).count() == 0


def test_incomplete_metadata_has_distinct_preflight_outcome():
    db = make_session()
    workspace, portfolio = _workspace_portfolio(db)
    malformed = Asset(
        canonical_symbol="INCOMPLETE",
        display_symbol="INCOMPLETE",
        asset_type=AssetType.EQUITY.value,
        market="TEST",
        exchange="",
        currency="USD",
        status="ACTIVE",
        tradable=True,
        fractional_support=False,
    )
    db.add(malformed)
    db.flush()
    registry.attach_identifier(db, AssetId(malformed.id), _identifier("INCOMPLETE"))
    db.add(
        PortfolioItem(
            workspace_id=workspace.id,
            portfolio_id=portfolio.id,
            symbol="INCOMPLETE",
            shares=1,
            avg_cost=1,
        )
    )
    db.commit()

    report = build_execution_registry_preflight(db, workspace_id=workspace.id)
    row = next(
        row
        for row in report.rows
        if row.population == "current_holdings" and row.requested_symbol == "INCOMPLETE"
    )
    assert row.outcome == ExecutionPreflightOutcome.INCOMPLETE_METADATA
    assert "exchange" in " ".join(row.missing_requirements)


def test_registry_failure_is_explicit_and_distinct_from_unknown_ambiguity_and_incomplete():
    failure = ExecutionInstrumentFacts(
        query="A",
        resolution_status=ExecutionResolutionOutcome.UNKNOWN,
        instrument_form=ExecutionInstrumentForm.UNKNOWN,
        execution_role=ExecutionRole.UNKNOWN,
        reason="Registry facts batch resolution failed: RuntimeError",
        resolution_error="RuntimeError: offline",
    )
    unknown = ExecutionInstrumentFacts(
        query="B",
        resolution_status=ExecutionResolutionOutcome.UNKNOWN,
        instrument_form=ExecutionInstrumentForm.UNKNOWN,
        execution_role=ExecutionRole.UNKNOWN,
        reason="no matching asset",
    )
    ambiguous = ExecutionInstrumentFacts(
        query="C",
        resolution_status=ExecutionResolutionOutcome.AMBIGUOUS,
        instrument_form=ExecutionInstrumentForm.UNKNOWN,
        execution_role=ExecutionRole.UNKNOWN,
        reason="multiple candidates",
    )
    incomplete = ExecutionInstrumentFacts(
        query="D",
        resolution_status=ExecutionResolutionOutcome.UNKNOWN,
        instrument_form=ExecutionInstrumentForm.UNKNOWN,
        execution_role=ExecutionRole.UNKNOWN,
        reason="incomplete Registry metadata: exchange",
    )

    assert evaluate_execution_eligibility(failure).outcome == ExecutionEligibilityOutcome.REGISTRY_FAILURE
    assert evaluate_execution_eligibility(unknown).outcome == ExecutionEligibilityOutcome.UNKNOWN_IDENTITY
    assert evaluate_execution_eligibility(ambiguous).outcome == ExecutionEligibilityOutcome.AMBIGUOUS_IDENTITY
    assert evaluate_execution_eligibility(incomplete).outcome == ExecutionEligibilityOutcome.UNKNOWN_IDENTITY
    assert evaluate_execution_eligibility(failure).registry_failure is True


def test_remediation_dry_run_causes_no_writes():
    db = make_session()
    instructions = _manifest(_mint_instruction("mint-1", "DRYRUN", approved=True))

    report = apply_registry_remediation(db, instructions)

    assert report.dry_run is True
    assert report.committed is False
    assert report.steps[0].status == "WOULD_APPLY"
    assert db.query(Asset).count() == 0


def test_commit_writes_only_explicitly_approved_records():
    db = make_session()
    instructions = _manifest(
        _mint_instruction("approved", "APPROVED", approved=True),
        _mint_instruction("unapproved", "UNAPPROVED", approved=False),
    )

    report = apply_registry_remediation(db, instructions, commit=True)

    assert report.committed is True
    assert {step.status for step in report.steps} == {"APPLIED", "SKIPPED_NOT_APPROVED"}
    assert [row.canonical_symbol for row in db.query(Asset).all()] == ["APPROVED"]


def test_dr_remediation_requires_authoritative_underlying_and_never_uses_symbol_shape():
    db = make_session()
    with pytest.raises(ValueError, match="underlying_asset_id"):
        apply_registry_remediation(
            db,
            _manifest(
                _mint_instruction(
                    "dr-missing-underlying",
                    "NAME99.BK",
                    approved=True,
                    operation="MINT_DR",
                )
            ),
            commit=True,
        )

    underlying = _mint(db, "UNDERLYING")
    db.commit()
    instructions = _manifest(
        _mint_instruction(
            "ordinary-shaped-dr",
            "LOCAL-RECEIPT",
            approved=True,
            operation="MINT_DR",
            underlying_asset_id=underlying.id,
        ),
        _mint_instruction(
            "dr-shaped-equity",
            "LOOKS99.BK",
            approved=True,
            operation="MINT_ASSET",
        ),
    )
    apply_registry_remediation(db, instructions, commit=True)

    receipt = resolve_execution_instrument(db, "LOCAL-RECEIPT")
    shaped_equity = resolve_execution_instrument(db, "LOOKS99.BK")
    assert receipt.instrument_form == ExecutionInstrumentForm.DEPOSITARY_RECEIPT
    assert shaped_equity.instrument_form == ExecutionInstrumentForm.EQUITY
    relationships = db.query(AssetRelationship).all()
    assert len(relationships) == 1
    assert relationships[0].to_asset_id == underlying.id
    remediation_source = inspect.getsource(
        sys.modules["services.execution_registry_remediation"]
    )
    imported_names = {
        alias.name
        for node in ast.walk(ast.parse(remediation_source))
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert "re" not in imported_names


def test_etf_remediation_requires_explicit_registry_asset_type():
    db = make_session()
    with pytest.raises(ValueError, match="asset_type=ETF"):
        apply_registry_remediation(
            db,
            _manifest(
                _mint_instruction(
                    "bad-etf",
                    "CUSTOM-FUND",
                    approved=True,
                    operation="MINT_ETF",
                    asset_type="EQUITY",
                )
            ),
            commit=True,
        )

    apply_registry_remediation(
        db,
        _manifest(
            _mint_instruction(
                "good-etf",
                "CUSTOM-FUND",
                approved=True,
                operation="MINT_ETF",
                asset_type="ETF",
            )
        ),
        commit=True,
    )
    assert resolve_execution_instrument(db, "CUSTOM-FUND").instrument_form == ExecutionInstrumentForm.ETF


def test_index_reference_remediation_requires_other_index_and_non_tradable():
    db = make_session()
    with pytest.raises(ValueError, match="asset_type=OTHER and tradable=false"):
        apply_registry_remediation(
            db,
            _manifest(
                _mint_instruction(
                    "bad-index",
                    "MARKET-REFERENCE",
                    approved=True,
                    operation="MINT_INDEX_REFERENCE",
                    asset_type="EQUITY",
                    tradable=True,
                )
            ),
            commit=True,
        )

    apply_registry_remediation(
        db,
        _manifest(
            _mint_instruction(
                "good-index",
                "MARKET-REFERENCE",
                approved=True,
                operation="MINT_INDEX_REFERENCE",
                asset_type="OTHER",
                tradable=False,
            )
        ),
        commit=True,
    )
    facts = resolve_execution_instrument(db, "MARKET-REFERENCE")
    assert facts.registry_asset_type == AssetType.OTHER
    assert facts.execution_role == ExecutionRole.REFERENCE
    assert facts.resolution_status == ExecutionResolutionOutcome.NOT_TRADABLE
    assert evaluate_execution_eligibility(facts).outcome == ExecutionEligibilityOutcome.REFERENCE_ONLY


def test_supported_universe_is_registry_governed_not_legacy_membership():
    db = make_session()
    workspace, _portfolio = _workspace_portfolio(db)
    _mint(db, "NOT-IN-LEGACY-LIST", asset_type=AssetType.ETF)
    db.commit()

    report = build_execution_registry_preflight(db, workspace_id=workspace.id)
    legacy_qqq = next(
        row
        for row in report.rows
        if row.population == "configured_etf_review" and row.requested_symbol == "QQQ"
    )
    assert legacy_qqq.supported_executable is False
    assert legacy_qqq.outcome == ExecutionPreflightOutcome.UNKNOWN_IDENTITY

    facts = resolve_execution_instrument(db, "NOT-IN-LEGACY-LIST")
    assert evaluate_execution_eligibility(facts).outcome == ExecutionEligibilityOutcome.ELIGIBLE


def test_cutover_mode_defaults_and_invalid_configuration_fails_safely(monkeypatch):
    assert load_execution_eligibility_cutover_mode({}) == ExecutionEligibilityCutoverMode.LEGACY_FALLBACK

    with pytest.raises(ExecutionCutoverConfigurationError):
        load_execution_eligibility_cutover_mode(
            {EXECUTION_ELIGIBILITY_CUTOVER_MODE_ENV: "TURN_IT_ON"}
        )

    monkeypatch.setenv(EXECUTION_ELIGIBILITY_CUTOVER_MODE_ENV, "TURN_IT_ON")
    reset_execution_eligibility_cutover_mode_cache()
    assert get_execution_eligibility_cutover_mode() == ExecutionEligibilityCutoverMode.LEGACY_FALLBACK


def test_telemetry_has_required_low_cardinality_labels_and_no_identity_labels():
    facts = ExecutionInstrumentFacts(
        query="SENSITIVE-SYMBOL",
        resolution_status=ExecutionResolutionOutcome.RESOLVED,
        instrument_form=ExecutionInstrumentForm.EQUITY,
        execution_role=ExecutionRole.TRADABLE,
        tradable=True,
    )
    consult_execution_eligibility_shadow(
        [ShadowExecutionAction("SENSITIVE-SYMBOL", "BUY", classification_agreement=True)],
        {"SENSITIVE-SYMBOL": facts},
        legacy_path="TEST_BOUNDARY",
        logger=logging.getLogger("m31.5.telemetry"),
    )

    snapshot = execution_eligibility_counter_snapshot()
    assert len(snapshot) == 1
    labels = asdict(snapshot[0][0])
    assert set(labels) == {
        "boundary",
        "eligibility_outcome",
        "resolution_status",
        "instrument_form",
        "execution_role",
        "cutover_mode",
        "registry_failure",
        "classification_agreement",
    }
    assert "SENSITIVE-SYMBOL" not in json.dumps(labels)
    assert labels["classification_agreement"] == "AGREE"
    assert labels["cutover_mode"] == "LEGACY_FALLBACK"


def test_nonlegacy_modes_are_typed_but_do_not_block_m31_5(monkeypatch):
    monkeypatch.setenv(EXECUTION_ELIGIBILITY_CUTOVER_MODE_ENV, "ENFORCE")
    reset_execution_eligibility_cutover_mode_cache()
    db = make_session()
    workspace, portfolio = _workspace_portfolio(db)
    db.commit()

    transaction = portfolio_transactions.execute_initial_position(
        db,
        workspace.id,
        portfolio.id,
        "UNREGISTERED",
        shares=2,
        avg_cost=5,
        transaction_date=datetime(2026, 7, 14),
    )
    plan = execution_plan.build_execution_plan(
        portfolio_id=portfolio.id,
        workspace_id=workspace.id,
        buy_symbols=["UNREGISTERED"],
        sizing_suggestions=[
            {"symbol": "UNREGISTERED", "suggested_pct": 10, "signal": "BUY"}
        ],
        timing_scores=None,
        db=db,
    )

    assert transaction["type"] == "INITIAL_POSITION"
    assert db.query(Transaction).filter_by(symbol="UNREGISTERED").count() == 1
    assert [action.symbol for action in plan.buy_actions] == ["UNREGISTERED"]


def test_legacy_compatibility_remains_authoritative_for_unresolved_risk_profile():
    facts = ExecutionInstrumentFacts(
        query="UNREGISTERED",
        resolution_status=ExecutionResolutionOutcome.UNKNOWN,
        instrument_form=ExecutionInstrumentForm.UNKNOWN,
        execution_role=ExecutionRole.UNKNOWN,
        reason="no matching asset",
    )

    metadata = classify_execution("UNREGISTERED", False, facts=facts)

    assert metadata.asset_type == "EQUITY"
    assert metadata.classification_source == LEGACY_COMPATIBILITY_FALLBACK


def test_m31_5_introduces_no_blocking_branch():
    boundary_source = "\n".join(
        [
            inspect.getsource(execution_plan.build_execution_plan),
            inspect.getsource(portfolio_transactions.execute_buy),
            inspect.getsource(portfolio_transactions.execute_sell),
            inspect.getsource(portfolio_transactions.execute_initial_position),
        ]
    )
    assert "ExecutionEligibilityCutoverMode.ENFORCE" not in boundary_source
    assert "REGISTRY_FAILURE" not in boundary_source
