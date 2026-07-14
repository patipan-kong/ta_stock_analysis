"""Focused M31.6 Registry remediation Wave 1 tests."""
from __future__ import annotations

import os
import sys
from datetime import datetime

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models.asset  # noqa: F401
import models.registry_finding  # noqa: F401
from models.asset import Asset, AssetIdentifier
from models.database import Base, Portfolio, Transaction, Workspace
from models.registry_finding import RegistryFinding
from services import execution_plan, portfolio_transactions, registry_lookup
from services import registry_service as registry
from services.asset_domain import (
    AssetClaim,
    AssetType,
    IdentifierRecord,
    IdentifierType,
)
from services.execution_cutover_config import (
    EXECUTION_ELIGIBILITY_CUTOVER_MODE_ENV,
    reset_execution_eligibility_cutover_mode_cache,
)
from services.execution_registry_remediation import (
    apply_registry_remediation,
    parse_registry_remediation_manifest,
)
from services.execution_registry_wave1 import (
    M31_6_WAVE1_SYMBOLS,
    Wave1Disposition,
    build_execution_registry_wave1_manifest,
)


def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


@pytest.fixture(autouse=True)
def _reset_state(monkeypatch):
    registry_lookup.invalidate_cache()
    reset_execution_eligibility_cutover_mode_cache()
    monkeypatch.delenv(EXECUTION_ELIGIBILITY_CUTOVER_MODE_ENV, raising=False)
    yield
    registry_lookup.invalidate_cache()
    reset_execution_eligibility_cutover_mode_cache()


def _identifier(symbol: str, source: str = "m31.6-test") -> IdentifierRecord:
    return IdentifierRecord(
        identifier_type=IdentifierType.PROVIDER_SYMBOL,
        value=symbol,
        source=source,
    )


def _mint(db, symbol: str, *, identifier: str | None = None):
    return registry.mint_asset(
        db,
        AssetClaim(
            canonical_symbol=symbol,
            display_symbol=symbol,
            asset_type=AssetType.EQUITY,
            market="TEST",
            exchange="TESTX",
            currency="THB",
            tradable=True,
            lot_size=1,
            settlement_cycle="T+2",
        ),
        identifiers=[_identifier(identifier or symbol)],
    )


def _mint_instruction(symbol: str, *, approved: bool) -> dict:
    return {
        "instruction_id": f"mint-{symbol}",
        "approved": approved,
        "operation": "MINT_ASSET",
        "evidence_source": "reviewed instrument master fixture",
        "evidence_note": "complete explicit identity reviewed by Registry steward",
        "canonical_symbol": symbol,
        "display_symbol": symbol,
        "asset_type": "EQUITY",
        "market": "TEST",
        "exchange": "TESTX",
        "currency": "THB",
        "tradable": True,
        "lot_size": 1,
        "settlement_cycle": "T+2",
        "identifiers": [
            {
                "identifier_type": "PROVIDER_SYMBOL",
                "value": symbol,
                "source": "reviewed instrument master fixture",
            }
        ],
    }


def _attach_instruction(asset_id: int, symbol: str, *, approved: bool) -> dict:
    return {
        "instruction_id": f"attach-{symbol}",
        "requested_symbol": symbol,
        "candidate_asset_ids": [asset_id],
        "approved": approved,
        "operation": "ATTACH_IDENTIFIER",
        "evidence_source": "exact Registry candidate fixture",
        "evidence_note": "one exact candidate reviewed by Registry steward",
        "asset_id": asset_id,
        "identifiers": [
            {
                "identifier_type": "PROVIDER_SYMBOL",
                "value": symbol,
                "source": "exact Registry candidate fixture",
            }
        ],
    }


def _parse(*instructions):
    return parse_registry_remediation_manifest(
        {"version": 1, "instructions": list(instructions)}
    )


def test_wave1_candidate_manifest_is_deterministic_and_fixed_scope():
    db = make_session()
    first = build_execution_registry_wave1_manifest(db).to_dict()
    second = build_execution_registry_wave1_manifest(db).to_dict()

    assert first == second
    assert first["scope_symbols"] == list(M31_6_WAVE1_SYMBOLS)
    assert [item["requested_symbol"] for item in first["symbol_reviews"]] == list(
        M31_6_WAVE1_SYMBOLS
    )
    assert "generated_at" not in first


def test_no_candidate_or_operation_is_derived_from_symbol_shape():
    db = make_session()
    _mint(db, "GOOGL01")
    db.commit()

    manifest = build_execution_registry_wave1_manifest(db).to_dict()
    review = next(
        item for item in manifest["symbol_reviews"] if item["requested_symbol"] == "GOOGL01.BK"
    )

    assert review["existing_candidates"] == ()
    assert review["disposition"] == "QUARANTINE_PENDING_HUMAN_ADJUDICATION"
    assert not any(item.get("requested_symbol") == "GOOGL01.BK" for item in manifest["instructions"])


def test_attach_generation_requires_exactly_one_existing_candidate():
    db = make_session()
    asset = _mint(db, "GULF.BK", identifier="OLD-EXACT-ALIAS")
    db.commit()

    manifest = build_execution_registry_wave1_manifest(db).to_dict()
    instruction = next(
        item for item in manifest["instructions"] if item["requested_symbol"] == "GULF.BK"
    )

    assert instruction["candidate_asset_ids"] == [asset.id]
    assert instruction["asset_id"] == asset.id
    assert instruction["approved"] is False

    bad = dict(instruction)
    bad["approved"] = True
    bad["candidate_asset_ids"] = []
    with pytest.raises(ValueError, match="exactly one existing candidate"):
        apply_registry_remediation(db, _parse(bad), commit=True)


def test_mint_requires_complete_explicit_identity_and_classification_evidence():
    db = make_session()
    incomplete = _mint_instruction("COMPLETE-ME", approved=True)
    del incomplete["exchange"]

    with pytest.raises(ValueError, match="requires exchange"):
        apply_registry_remediation(db, _parse(incomplete), commit=True)
    assert db.query(Asset).count() == 0


def test_ambiguous_exact_candidates_are_quarantined_without_persisting_finding():
    db = make_session()
    first = _mint(db, "FIRST")
    second = _mint(db, "SECOND")
    db.flush()
    for asset in (first, second):
        db.add(
            AssetIdentifier(
                asset_id=asset.id,
                identifier_type=IdentifierType.PROVIDER_SYMBOL.value,
                value="ASML01.BK",
                source="historical fixture",
                is_current=False,
            )
        )
    db.commit()

    before = db.query(RegistryFinding).count()
    manifest = build_execution_registry_wave1_manifest(db).to_dict()
    review = next(
        item for item in manifest["symbol_reviews"] if item["requested_symbol"] == "ASML01.BK"
    )

    assert len(review["existing_candidates"]) == 2
    assert review["disposition"] == "QUARANTINE_PENDING_HUMAN_ADJUDICATION"
    assert not any(item.get("requested_symbol") == "ASML01.BK" for item in manifest["instructions"])
    assert db.query(RegistryFinding).count() == before


def test_dry_run_causes_no_persistent_registry_change():
    db = make_session()
    asset = _mint(db, "GULF.BK", identifier="OLD-ALIAS")
    db.commit()
    instruction = _attach_instruction(asset.id, "GULF.BK", approved=True)

    report = apply_registry_remediation(db, _parse(instruction))

    assert report.steps[0].status == "WOULD_APPLY"
    current = registry.get_identifiers(db, asset.id, current_only=True)
    assert [(row.value, row.is_current) for row in current] == [("OLD-ALIAS", True)]


def test_commit_changes_only_approved_instructions():
    db = make_session()
    report = apply_registry_remediation(
        db,
        _parse(
            _mint_instruction("APPROVED-WAVE1", approved=True),
            _mint_instruction("DEFERRED-WAVE1", approved=False),
        ),
        commit=True,
    )

    assert {step.status for step in report.steps} == {"APPLIED", "SKIPPED_NOT_APPROVED"}
    assert [row.canonical_symbol for row in db.query(Asset).all()] == ["APPROVED-WAVE1"]


def test_reapplying_approved_manifest_reports_already_applied_without_finding():
    db = make_session()
    instructions = _parse(_mint_instruction("IDEMPOTENT", approved=True))
    first = apply_registry_remediation(db, instructions, commit=True)
    findings_after_first = db.query(RegistryFinding).count()
    second = apply_registry_remediation(db, instructions, commit=True)

    assert first.steps[0].status == "APPLIED"
    assert second.steps[0].status == "ALREADY_APPLIED"
    assert db.query(Asset).filter_by(canonical_symbol="IDEMPOTENT").count() == 1
    assert db.query(RegistryFinding).count() == findings_after_first


def test_conflicting_repeat_is_not_treated_as_already_applied():
    db = make_session()
    original = _mint_instruction("CONFLICTING", approved=True)
    apply_registry_remediation(db, _parse(original), commit=True)
    changed = dict(original)
    changed["currency"] = "USD"

    with pytest.raises(ValueError, match="conflicting currency"):
        apply_registry_remediation(db, _parse(changed), commit=True)
    assert db.query(Asset).filter_by(canonical_symbol="CONFLICTING").count() == 1


def test_wave1_scope_rejects_broader_etf_dr_or_reference_population():
    db = make_session()
    with pytest.raises(ValueError, match="scope is fixed"):
        build_execution_registry_wave1_manifest(
            db, symbols=(*M31_6_WAVE1_SYMBOLS, "QQQ")
        )

    payload = build_execution_registry_wave1_manifest(db).to_dict()
    assert not {
        "MINT_ETF",
        "MINT_DR",
        "MINT_INDEX_REFERENCE",
        "LINK_DR_RELATIONSHIP",
        "REGISTER_INDEX_REFERENCE",
    } & {item["operation"] for item in payload["instructions"]}


def test_enforce_mode_remains_inert_for_transaction_and_plan(monkeypatch):
    monkeypatch.setenv(EXECUTION_ELIGIBILITY_CUTOVER_MODE_ENV, "ENFORCE")
    reset_execution_eligibility_cutover_mode_cache()
    db = make_session()
    workspace = Workspace(name="M31.6")
    db.add(workspace)
    db.flush()
    portfolio = Portfolio(workspace_id=workspace.id, name="Wave 1", cash_balance=1000)
    db.add(portfolio)
    db.commit()

    transaction = portfolio_transactions.execute_initial_position(
        db,
        workspace.id,
        portfolio.id,
        "UNREGISTERED-WAVE1",
        shares=2,
        avg_cost=5,
        transaction_date=datetime(2026, 7, 14),
    )
    plan = execution_plan.build_execution_plan(
        portfolio_id=portfolio.id,
        workspace_id=workspace.id,
        buy_symbols=["UNREGISTERED-WAVE1"],
        sizing_suggestions=[
            {"symbol": "UNREGISTERED-WAVE1", "suggested_pct": 10, "signal": "BUY"}
        ],
        timing_scores=None,
        db=db,
    )

    assert transaction["type"] == "INITIAL_POSITION"
    assert db.query(Transaction).filter_by(symbol="UNREGISTERED-WAVE1").count() == 1
    assert [action.symbol for action in plan.buy_actions] == ["UNREGISTERED-WAVE1"]


def test_wave1_tooling_is_not_imported_by_execution_runtime_boundaries():
    import inspect
    import services.execution_plan as plan_module
    import services.portfolio_transactions as transaction_module

    runtime_source = inspect.getsource(plan_module) + inspect.getsource(transaction_module)
    assert "execution_registry_wave1" not in runtime_source
    assert "build_execution_registry_wave1_manifest" not in runtime_source
