"""Tests for the Asset Registry service boundary (Milestone M2).

Validates the M2-specific capabilities layered on top of M1's frozen
asset_registry.py:
  1. find_by_identifier resolves across current AND historical mappings
  2. mint_asset blocks on a current-identifier duplicate and records a
     first-class OPEN finding (never silently merges/rejects-and-forgets)
  3. mint_asset allows historical-only reuse but still surfaces a finding
  4. attach_identifier conflicts are recorded as IDENTIFIER_CONFLICT findings
  5. record_merge composes status transition + relationship + a RESOLVED,
     durable finding — never a silent identity mutation
  6. Findings are evidence: resolving one appends resolution fields, never
     deletes or overwrites the original observation
  7. supersede_identifier / lifecycle / classification / relationship calls
     delegate correctly to M1 with identical behavior
  8. Absence is data — get_asset_detail and find_by_identifier handle the
     zero-identifier / zero-match case without error

All tests use an in-memory SQLite database; no network calls.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base
import models.asset  # noqa: F401 — registers Asset* tables on Base.metadata
import models.registry_finding  # noqa: F401 — registers RegistryFinding table
from services import registry_service as svc
from services.asset_domain import (
    AssetClaim,
    AssetStatus,
    AssetType,
    ClassificationDimension,
    IdentifierRecord,
    IdentifierType,
    RelationshipType,
)
from services.registry_domain import FindingResolution, FindingStatus, FindingType
from services.registry_service import AssetRegistryError


def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _claim(**overrides):
    defaults = dict(
        canonical_symbol="KBANK",
        asset_type=AssetType.EQUITY,
        market="TH",
        exchange="SET",
        currency="THB",
    )
    defaults.update(overrides)
    return AssetClaim(**defaults)


# ── find_by_identifier: current + historical ────────────────────────────────

def test_find_by_identifier_matches_current_mapping():
    db = make_session()
    asset = svc.mint_asset(db, _claim())
    svc.attach_identifier(db, asset.id, IdentifierRecord(IdentifierType.ISIN, "TH0001010006", source="manual"))

    matches = svc.find_by_identifier(db, IdentifierType.ISIN, "TH0001010006")
    assert [a.id for a in matches] == [asset.id]


def test_find_by_identifier_matches_historical_mapping():
    db = make_session()
    asset = svc.mint_asset(db, _claim())
    svc.attach_identifier(
        db, asset.id, IdentifierRecord(IdentifierType.PROVIDER_SYMBOL, "KBANK.BK", source="yfinance"),
    )
    # supersede it — old value becomes historical, not current
    svc.attach_identifier(
        db, asset.id, IdentifierRecord(IdentifierType.PROVIDER_SYMBOL, "KBANK2.BK", source="yfinance"),
    )

    matches = svc.find_by_identifier(db, IdentifierType.PROVIDER_SYMBOL, "KBANK.BK")
    assert [a.id for a in matches] == [asset.id]  # still resolves, historically


def test_find_by_identifier_no_match_returns_empty_list():
    db = make_session()
    assert svc.find_by_identifier(db, IdentifierType.ISIN, "NOPE") == []


# ── mint_asset: duplicate detection ─────────────────────────────────────────

def test_mint_asset_blocks_on_current_identifier_duplicate():
    db = make_session()
    first = svc.mint_asset(
        db, _claim(canonical_symbol="KBANK"),
        identifiers=[IdentifierRecord(IdentifierType.ISIN, "TH0001010006", source="manual")],
    )

    with pytest.raises(AssetRegistryError):
        svc.mint_asset(
            db, _claim(canonical_symbol="KBANK_DUP"),
            identifiers=[IdentifierRecord(IdentifierType.ISIN, "TH0001010006", source="manual")],
        )

    findings = svc.list_open_findings(db, subject_asset_id=first.id)
    assert len(findings) == 1
    assert findings[0].finding_type == FindingType.DUPLICATE_CLAIM.value
    assert findings[0].status == FindingStatus.OPEN.value


def test_mint_asset_allows_and_flags_historical_only_reuse():
    db = make_session()
    old = svc.mint_asset(
        db, _claim(canonical_symbol="OLD"),
        identifiers=[IdentifierRecord(IdentifierType.PROVIDER_SYMBOL, "ABC.BK", source="yfinance")],
    )
    svc.attach_identifier(
        db, old.id, IdentifierRecord(IdentifierType.PROVIDER_SYMBOL, "ABC2.BK", source="yfinance"),
    )  # ABC.BK is now historical only

    new = svc.mint_asset(
        db, _claim(canonical_symbol="NEW"),
        identifiers=[IdentifierRecord(IdentifierType.PROVIDER_SYMBOL, "ABC.BK", source="yfinance")],
    )
    assert new.id != old.id  # mint succeeded, not blocked

    findings = svc.list_open_findings(db, subject_asset_id=new.id)
    assert len(findings) == 1
    assert findings[0].finding_type == FindingType.DUPLICATE_CLAIM.value
    assert findings[0].related_asset_id == old.id


def test_mint_asset_with_no_prior_history_records_no_finding():
    db = make_session()
    asset = svc.mint_asset(
        db, _claim(),
        identifiers=[IdentifierRecord(IdentifierType.ISIN, "TH0001010006", source="manual")],
    )
    assert svc.list_open_findings(db, subject_asset_id=asset.id) == []


# ── attach_identifier: conflict findings ────────────────────────────────────

def test_attach_identifier_conflict_recorded_as_finding():
    db = make_session()
    a1 = svc.mint_asset(db, _claim(canonical_symbol="KBANK"))
    a2 = svc.mint_asset(db, _claim(canonical_symbol="PTT"))
    svc.attach_identifier(db, a1.id, IdentifierRecord(IdentifierType.ISIN, "TH0001010006", source="manual"))

    with pytest.raises(AssetRegistryError):
        svc.attach_identifier(db, a2.id, IdentifierRecord(IdentifierType.ISIN, "TH0001010006", source="manual"))

    findings = svc.list_open_findings(db, subject_asset_id=a2.id)
    assert len(findings) == 1
    assert findings[0].finding_type == FindingType.IDENTIFIER_CONFLICT.value
    assert findings[0].related_asset_id == a1.id


def test_attach_identifier_delegates_cleanly_when_no_conflict():
    db = make_session()
    asset = svc.mint_asset(db, _claim())
    row = svc.attach_identifier(db, asset.id, IdentifierRecord(IdentifierType.ISIN, "TH0001010006", source="manual"))
    assert row.value == "TH0001010006"
    assert svc.list_open_findings(db) == []


def test_supersede_identifier_is_rename_semantics():
    db = make_session()
    asset = svc.mint_asset(db, _claim())
    svc.supersede_identifier(
        db, asset.id, IdentifierRecord(IdentifierType.PROVIDER_SYMBOL, "KBANK.BK", source="yfinance"),
    )
    svc.supersede_identifier(
        db, asset.id, IdentifierRecord(IdentifierType.PROVIDER_SYMBOL, "KBANK2.BK", source="yfinance"),
    )

    refreshed = svc.get_asset(db, asset.id)
    assert refreshed.canonical_symbol == "KBANK"  # untouched
    assert refreshed.display_symbol == "KBANK2.BK"

    current = svc.get_identifiers(db, asset.id, current_only=True)
    assert len(current) == 1 and current[0].value == "KBANK2.BK"


# ── record_merge ─────────────────────────────────────────────────────────────

def test_record_merge_composes_status_relationship_and_finding():
    db = make_session()
    old = svc.mint_asset(db, _claim(canonical_symbol="OLDTICKER"))
    new = svc.mint_asset(db, _claim(canonical_symbol="NEWTICKER"))

    finding = svc.record_merge(db, old.id, new.id, reason="Corporate action: OLDTICKER absorbed into NEWTICKER")

    assert svc.get_asset(db, old.id).status == AssetStatus.MERGED.value
    rels = svc.get_relationships(db, old.id)
    assert any(
        r.from_asset_id == old.id and r.to_asset_id == new.id and r.relationship_type == RelationshipType.MERGED_INTO.value
        for r in rels
    )

    assert finding.finding_type == FindingType.MERGE_RECORDED.value
    assert finding.status == FindingStatus.RESOLVED.value
    assert finding.resolution == FindingResolution.MERGED.value
    assert finding.subject_asset_id == old.id
    assert finding.related_asset_id == new.id
    # the finding is retained, queryable evidence — not just a return value
    all_findings = svc.list_open_findings(db, subject_asset_id=old.id)
    assert all_findings == []  # it's RESOLVED, so not "open" — but still exists:
    from services import registry_findings_repository as findings_repo
    persisted = findings_repo.list_findings(db, subject_asset_id=old.id)
    assert len(persisted) == 1
    assert persisted[0].id == finding.id


# ── Findings adjudication: evidence, not deletion ───────────────────────────

def test_resolve_finding_appends_without_erasing_original_observation():
    db = make_session()
    a1 = svc.mint_asset(db, _claim(canonical_symbol="KBANK"))
    a2 = svc.mint_asset(db, _claim(canonical_symbol="PTT"))
    svc.attach_identifier(db, a1.id, IdentifierRecord(IdentifierType.ISIN, "TH0001010006", source="manual"))
    with pytest.raises(AssetRegistryError):
        svc.attach_identifier(db, a2.id, IdentifierRecord(IdentifierType.ISIN, "TH0001010006", source="manual"))

    finding = svc.list_open_findings(db, subject_asset_id=a2.id)[0]
    original_detail = finding.detail
    original_created_at = finding.created_at

    resolved = svc.resolve_finding(
        db, finding.id,
        resolution=FindingResolution.CONFIRMED_DISTINCT,
        resolution_note="Verified with registrar: data entry error, corrected upstream",
        resolved_by="ops@example.com",
    )

    assert resolved.detail == original_detail  # original observation untouched
    assert resolved.created_at == original_created_at
    assert resolved.status == FindingStatus.RESOLVED.value
    assert resolved.resolution == FindingResolution.CONFIRMED_DISTINCT.value
    assert resolved.resolved_by == "ops@example.com"
    assert resolved.resolved_at is not None

    # no longer "open" ...
    assert svc.list_open_findings(db, subject_asset_id=a2.id) == []
    # ... but still exists, permanently
    from services import registry_findings_repository as findings_repo
    assert findings_repo.get_finding(db, finding.id) is not None


def test_resolve_finding_with_dismissed_resolution_sets_dismissed_status():
    db = make_session()
    a1 = svc.mint_asset(db, _claim(canonical_symbol="KBANK"))
    a2 = svc.mint_asset(db, _claim(canonical_symbol="PTT"))
    svc.attach_identifier(db, a1.id, IdentifierRecord(IdentifierType.ISIN, "TH0001010006", source="manual"))
    with pytest.raises(AssetRegistryError):
        svc.attach_identifier(db, a2.id, IdentifierRecord(IdentifierType.ISIN, "TH0001010006", source="manual"))
    finding = svc.list_open_findings(db, subject_asset_id=a2.id)[0]

    resolved = svc.resolve_finding(
        db, finding.id, resolution=FindingResolution.DISMISSED, resolution_note="False positive",
    )
    assert resolved.status == FindingStatus.DISMISSED.value


def test_resolve_finding_rejects_unknown_id():
    db = make_session()
    with pytest.raises(AssetRegistryError):
        svc.resolve_finding(db, 999, resolution=FindingResolution.DISMISSED, resolution_note="n/a")


# ── Delegation correctness: lifecycle / classification / relationships ─────

def test_transition_status_delegates_to_core():
    db = make_session()
    asset = svc.mint_asset(db, _claim())
    svc.transition_status(db, asset.id, AssetStatus.SUSPENDED)
    assert svc.get_asset(db, asset.id).status == AssetStatus.SUSPENDED.value


def test_record_classification_delegates_to_core():
    db = make_session()
    asset = svc.mint_asset(db, _claim())
    svc.record_classification(db, asset.id, ClassificationDimension.SECTOR, "Banking", source="THAI_SECTOR_MAP")
    current = svc.get_classifications(db, asset.id, dimension=ClassificationDimension.SECTOR, current_only=True)
    assert len(current) == 1 and current[0].value == "Banking"


def test_link_relationship_delegates_to_core():
    db = make_session()
    thai = svc.mint_asset(db, _claim(canonical_symbol="KBANK"))
    dr = svc.mint_asset(db, _claim(canonical_symbol="KBANK_DR", market="US", exchange="OTC", currency="USD"))
    rel = svc.link_relationship(db, dr.id, thai.id, RelationshipType.DEPOSITARY_RECEIPT_OF)
    assert rel.from_asset_id == dr.id and rel.to_asset_id == thai.id


# ── get_asset_detail: bundled read, absence is data ─────────────────────────

def test_get_asset_detail_bundles_evidence():
    db = make_session()
    asset = svc.mint_asset(db, _claim())
    svc.attach_identifier(db, asset.id, IdentifierRecord(IdentifierType.ISIN, "TH0001010006", source="manual"))
    svc.record_classification(db, asset.id, ClassificationDimension.SECTOR, "Banking", source="THAI_SECTOR_MAP")

    detail = svc.get_asset_detail(db, asset.id)
    assert detail.asset.id == asset.id
    assert len(detail.current_identifiers) == 1
    assert len(detail.current_classifications) == 1
    assert detail.relationships == []


def test_get_asset_detail_handles_absent_asset():
    db = make_session()
    assert svc.get_asset_detail(db, 999) is None


def test_get_asset_detail_absence_is_data_for_bare_asset():
    db = make_session()
    asset = svc.mint_asset(db, _claim())
    detail = svc.get_asset_detail(db, asset.id)
    assert detail.current_identifiers == []
    assert detail.current_classifications == []
