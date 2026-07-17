"""M32.3E3R2 lot-capability evidence and read-only preflight tests."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import models.asset  # noqa: F401
import models.registry_finding  # noqa: F401
from models.asset import Asset
from models.database import Base, Portfolio, PortfolioItem, Transaction, Workspace
from models.registry_finding import RegistryFinding
from services import registry_service as registry
from services.asset_domain import AssetClaim, AssetType, IdentifierRecord, IdentifierType
from services.execution_lot_capability import (
    ApprovedLotCapabilityAuthority,
    LotCapabilityApprovalState,
    LotCapabilityAuthorityTrust,
    LotCapabilityConfidence,
    LotCapabilityManifestError,
    LotCapabilityPreflightOutcome,
    LotCapabilityScope,
    LotCapabilitySemantics,
    LotCapabilitySourceType,
    LotCapabilityUnit,
    RegistryIdentitySnapshot,
    build_lot_capability_evidence,
    build_lot_capability_preflight,
    parse_lot_capability_manifest,
)


NOW = datetime(2026, 7, 15, 9, 0, tzinfo=timezone.utc)


def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _identifier(symbol: str) -> IdentifierRecord:
    return IdentifierRecord(IdentifierType.PROVIDER_SYMBOL, symbol, "lot-capability-test")


def _mint(db, symbol: str = "KBANK.BK", *, lot_size=None, fractional_support=False):
    asset = registry.mint_asset(
        db,
        AssetClaim(
            canonical_symbol=symbol,
            display_symbol=symbol,
            asset_type=AssetType.EQUITY,
            market="Thailand",
            exchange="SET",
            currency="THB",
            tradable=True,
            lot_size=lot_size,
            fractional_support=fractional_support,
        ),
        identifiers=[_identifier(symbol)],
    )
    db.commit()
    return asset


def _evidence(asset_id: int = 1, symbol: str = "KBANK.BK", **changes):
    values = {
        "contract_version": "1",
        "asset_id": asset_id,
        "registry_identity_snapshot": RegistryIdentitySnapshot(symbol, (("PROVIDER_SYMBOL", symbol),)),
        "unit": LotCapabilityUnit.SHARE,
        "scope": LotCapabilityScope.STANDARD_BOARD_EXECUTION,
        "lot_semantics": LotCapabilitySemantics.QUANTITY_INCREMENT,
        "lot_size": 100,
        "fractional_support": False,
        "source_id": "set-master-v1",
        "source_type": LotCapabilitySourceType.EXCHANGE_MASTER,
        "source_locator": "sha256:fixture",
        "source_record_key": symbol,
        "source_version": "2026-07-15",
        "source_published_at": NOW - timedelta(days=1),
        "source_retrieved_at": NOW,
        "authority": "Fixture SET Authority",
        "confidence": LotCapabilityConfidence.VERIFIED,
        "effective_from": NOW - timedelta(days=1),
        "effective_to": None,
        "provenance": ("sha256:fixture", "reviewed extraction"),
        "reviewed_by": "registry-steward",
        "reviewed_at": NOW,
        "approval_state": LotCapabilityApprovalState.APPROVED,
        "approval_note": "fixture reviewed",
    }
    values.update(changes)
    return build_lot_capability_evidence(**values)


def _trust():
    return LotCapabilityAuthorityTrust((ApprovedLotCapabilityAuthority(
        source_id="set-master-v1",
        authority="Fixture SET Authority",
        source_types=(LotCapabilitySourceType.EXCHANGE_MASTER,),
    ),))


def _instruction(asset, evidence=None):
    evidence = evidence or _evidence(asset.id, asset.canonical_symbol)
    updated = asset.updated_at.replace(tzinfo=timezone.utc)
    return {
        "instruction_id": f"lot-{asset.id}",
        "operation": "UPDATE_LOT_CAPABILITY",
        "asset_id": asset.id,
        "expected_current": {
            "canonical_symbol": asset.canonical_symbol,
            "lot_size": asset.lot_size,
            "fractional_support": asset.fractional_support,
            "asset_updated_at": updated.isoformat(),
        },
        "proposed": {
            "unit": evidence.unit.value,
            "scope": evidence.scope.value,
            "lot_semantics": evidence.lot_semantics.value,
            "lot_size": evidence.lot_size,
            "fractional_support": evidence.fractional_support,
            "effective_from": evidence.effective_from.isoformat(),
        },
        "evidence": evidence.to_dict(),
        "rollback": {
            "prior_lot_size": asset.lot_size,
            "prior_fractional_support": asset.fractional_support,
            "implication": "returns M32 readiness to incomplete",
        },
    }


def _manifest(asset, evidence=None):
    return {"manifest_version": 1, "manifest_id": "review-wave-1", "instructions": [_instruction(asset, evidence)]}


def test_evidence_is_frozen_deterministic_and_requires_explicit_capabilities():
    first = _evidence()
    second = _evidence()
    assert first == second
    assert first.evidence_ref == second.evidence_ref
    with pytest.raises((AttributeError, TypeError)):
        first.lot_size = 1  # type: ignore[misc]
    with pytest.raises(LotCapabilityManifestError, match="positive integer"):
        _evidence(lot_size=True)
    with pytest.raises(LotCapabilityManifestError, match="explicit boolean"):
        _evidence(fractional_support="false")
    with pytest.raises(LotCapabilityManifestError, match="timezone-aware"):
        _evidence(reviewed_at=datetime(2026, 7, 15))


@pytest.mark.parametrize("value", [0, -1, 1.0, "100", True])
def test_manifest_rejects_non_explicit_lot_values(value):
    db = make_session()
    asset = _mint(db)
    raw = _manifest(asset)
    raw["instructions"][0]["proposed"]["lot_size"] = value
    with pytest.raises(LotCapabilityManifestError):
        parse_lot_capability_manifest(raw)


def test_manifest_rejects_approval_without_verified_and_duplicates():
    db = make_session()
    asset = _mint(db)
    # A forged raw form proves the parser refuses APPROVED non-VERIFIED evidence.
    raw = _manifest(asset)
    raw_evidence = raw["instructions"][0]["evidence"]
    raw_evidence["confidence"] = "INSUFFICIENT"
    with pytest.raises(LotCapabilityManifestError):
        parse_lot_capability_manifest(raw)
    duplicate = _manifest(asset)
    second = dict(duplicate["instructions"][0])
    second["instruction_id"] = duplicate["instructions"][0]["instruction_id"]
    duplicate["instructions"].append(second)
    with pytest.raises(LotCapabilityManifestError, match="duplicate instruction_id"):
        parse_lot_capability_manifest(duplicate)


def test_preflight_separates_raw_from_governed_and_does_not_mutate():
    db = make_session()
    asset = _mint(db)
    workspace = Workspace(name="lot")
    db.add(workspace)
    db.flush()
    portfolio = Portfolio(workspace_id=workspace.id, name="lot", cash_balance=1000)
    db.add(portfolio)
    db.flush()
    db.add(PortfolioItem(workspace_id=workspace.id, portfolio_id=portfolio.id, symbol=asset.canonical_symbol, shares=100, avg_cost=10))
    db.add(Transaction(workspace_id=workspace.id, portfolio_id=portfolio.id, symbol=asset.canonical_symbol, transaction_type="BUY", shares=100, price_per_share=10, total_amount=1000, fees=0, transaction_date=NOW.replace(tzinfo=None)))
    db.commit()
    before = (asset.lot_size, asset.fractional_support, db.query(RegistryFinding).count())
    report = build_lot_capability_preflight(db, generated_at=NOW, environment_reference="test")
    row = report.assets[0]
    assert report.raw_capability_coverage["positive_lot_size"] == 0
    assert report.governed_evidence_coverage["accepted_capability_evidence"] == 0
    assert row.outcome == LotCapabilityPreflightOutcome.UNVERIFIED_DEFAULT
    assert row.candidate_operational_evidence.label == "NON_AUTHORITATIVE_CANDIDATE_EVIDENCE"
    assert row.candidate_operational_evidence.holding_quantities == ("100",)
    assert db.query(Asset).one().lot_size == before[0]
    assert db.query(Asset).one().fractional_support == before[1]
    assert db.query(RegistryFinding).count() == before[2]
    assert report.to_dict()["no_writes_performed"] is True


def test_valid_trusted_evidence_is_only_ready_for_review_and_expected_current_is_checked():
    db = make_session()
    asset = _mint(db)
    manifest = parse_lot_capability_manifest(_manifest(asset))
    report = build_lot_capability_preflight(db, generated_at=NOW, manifest=manifest, authority_trust=_trust())
    assert report.assets[0].outcome == LotCapabilityPreflightOutcome.READY_FOR_REVIEW
    assert report.manifest_validation["instructions"][0]["status"] == "WOULD_REVIEW"
    changed = _manifest(asset)
    changed["instructions"][0]["expected_current"]["lot_size"] = 1
    mismatched = parse_lot_capability_manifest(changed)
    mismatch_report = build_lot_capability_preflight(db, generated_at=NOW, manifest=mismatched, authority_trust=_trust())
    assert mismatch_report.manifest_validation["instructions"][0]["status"] == "EXPECTED_CURRENT_MISMATCH"
    assert db.query(Asset).one().lot_size is None


def test_identity_conflict_future_and_untrusted_evidence_are_explicit():
    db = make_session()
    asset = _mint(db)
    identity_bad = _evidence(asset.id, "OTHER.BK")
    report = build_lot_capability_preflight(db, generated_at=NOW, manifest=parse_lot_capability_manifest(_manifest(asset, identity_bad)), authority_trust=_trust())
    assert report.assets[0].outcome == LotCapabilityPreflightOutcome.IDENTITY_MISMATCH
    future = _evidence(asset.id, asset.canonical_symbol, effective_from=NOW + timedelta(days=1))
    report = build_lot_capability_preflight(db, generated_at=NOW, manifest=parse_lot_capability_manifest(_manifest(asset, future)), authority_trust=_trust())
    assert report.assets[0].outcome == LotCapabilityPreflightOutcome.FUTURE_EFFECTIVE
    untrusted = build_lot_capability_preflight(db, generated_at=NOW, manifest=parse_lot_capability_manifest(_manifest(asset)))
    assert untrusted.assets[0].outcome == LotCapabilityPreflightOutcome.APPROVAL_REQUIRED


def test_conflicting_external_evidence_is_quarantined_without_selection():
    db = make_session()
    asset = _mint(db)
    first = _evidence(asset.id, asset.canonical_symbol, lot_size=100)
    second = _evidence(asset.id, asset.canonical_symbol, lot_size=50, source_record_key="KBANK.BK/alternate")
    report = build_lot_capability_preflight(
        db,
        generated_at=NOW,
        authority_trust=_trust(),
        evidence_records={asset.id: (first, second)},
    )
    row = report.assets[0]
    assert row.outcome == LotCapabilityPreflightOutcome.CONFLICT
    assert row.conflict is True
    assert row.governed_evidence_present is False
    assert "highest-confidence" in " ".join(row.details)
    assert db.query(Asset).one().lot_size is None


def test_expired_evidence_and_manifest_shape_failures_are_explicit():
    db = make_session()
    asset = _mint(db)
    expired = _evidence(
        asset.id,
        asset.canonical_symbol,
        effective_from=NOW - timedelta(days=3),
        effective_to=NOW - timedelta(days=1),
    )
    report = build_lot_capability_preflight(
        db, generated_at=NOW, manifest=parse_lot_capability_manifest(_manifest(asset, expired)), authority_trust=_trust()
    )
    assert report.assets[0].outcome == LotCapabilityPreflightOutcome.EXPIRED_EVIDENCE
    incomplete = _manifest(asset)
    del incomplete["instructions"][0]["evidence"]["source_version"]
    with pytest.raises(LotCapabilityManifestError, match="missing required fields"):
        parse_lot_capability_manifest(incomplete)
    multiple = _manifest(asset)
    second_evidence = _evidence(
        asset.id,
        asset.canonical_symbol,
        lot_size=50,
        source_record_key="KBANK.BK/second",
    )
    second = _instruction(asset, second_evidence)
    second["instruction_id"] = "lot-another"
    multiple["instructions"].append(second)
    with pytest.raises(LotCapabilityManifestError, match="overlapping effective periods"):
        parse_lot_capability_manifest(multiple)


def test_json_is_deterministic_and_cli_has_no_commit_mode(tmp_path):
    db = make_session()
    _mint(db)
    first = build_lot_capability_preflight(db, generated_at=NOW, environment_reference="fixture").to_dict()
    second = build_lot_capability_preflight(db, generated_at=NOW, environment_reference="fixture").to_dict()
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    script = os.path.join(os.path.dirname(__file__), "..", "scripts", "execution_lot_capability_preflight.py")
    completed = subprocess.run([sys.executable, script, "--commit"], capture_output=True, text=True)
    assert completed.returncode != 0
    assert "unsupported" in (completed.stderr + completed.stdout)
