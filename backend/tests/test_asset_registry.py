"""Tests for the Asset Registry canonical identity core (Milestone M1).

Validates the design principles in docs/architecture/ASSET_REGISTRY.md
Section 12 that are expressible as unit tests:
  1. Minting uniqueness — canonical_symbol can only ever be minted once
  2. canonical_symbol permanence — never reassigned, even across a
     real-world ticker change (display_symbol/AssetIdentifier evolve instead)
  3. asset_id is never reused or un-minted
  4. Historical identifier mappings are retained, not deleted, on supersession
  5. Conflicting identifiers (same value, two live assets) are rejected
  6. Lifecycle transitions are forward-only and illegal transitions are rejected
  7. Classification facts are dated/superseded, never deleted
  8. Relationships link listings without merging their identity
  9. Absence is data — an asset with no identifiers/classification is valid

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
from services import asset_registry as registry
from services.asset_domain import (
    AssetClaim,
    AssetStatus,
    AssetType,
    ClassificationDimension,
    IdentifierRecord,
    IdentifierType,
    RelationshipType,
)
from services.asset_registry import AssetRegistryError


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


# ── Minting ──────────────────────────────────────────────────────────────────

def test_mint_creates_active_asset_with_permanent_id():
    db = make_session()
    asset = registry.mint(db, _claim())

    assert asset.id is not None
    assert asset.canonical_symbol == "KBANK"
    assert asset.status == AssetStatus.ACTIVE.value
    assert asset.display_symbol == "KBANK"  # defaults to canonical_symbol


def test_mint_rejects_duplicate_canonical_symbol():
    db = make_session()
    registry.mint(db, _claim())

    with pytest.raises(AssetRegistryError):
        registry.mint(db, _claim())


def test_mint_requires_market_exchange_currency():
    db = make_session()
    with pytest.raises(AssetRegistryError):
        registry.mint(db, _claim(currency=""))


def test_asset_id_never_reused_across_assets():
    db = make_session()
    a1 = registry.mint(db, _claim(canonical_symbol="KBANK"))
    a2 = registry.mint(db, _claim(canonical_symbol="PTT"))

    assert a1.id != a2.id


# ── canonical_symbol permanence vs. real-world ticker change ────────────────

def test_canonical_symbol_survives_identifier_supersession():
    """A real-world ticker/provider-symbol change must never touch
    canonical_symbol or asset_id — only the evidence tier (identifiers,
    display_symbol) moves."""
    db = make_session()
    asset = registry.mint(db, _claim())
    asset_id = asset.id

    registry.attach_identifier(
        db, asset_id,
        IdentifierRecord(IdentifierType.PROVIDER_SYMBOL, "KBANK.BK", source="yfinance"),
    )
    # Simulate a provider symbol rename (e.g. exchange re-listing)
    registry.attach_identifier(
        db, asset_id,
        IdentifierRecord(IdentifierType.PROVIDER_SYMBOL, "KBANK2.BK", source="yfinance"),
    )

    refreshed = registry.get_asset(db, asset_id)
    assert refreshed.id == asset_id
    assert refreshed.canonical_symbol == "KBANK"  # untouched
    assert refreshed.display_symbol == "KBANK2.BK"  # evidence-tier field moved


def test_superseded_identifier_retained_not_deleted():
    db = make_session()
    asset = registry.mint(db, _claim())
    asset_id = asset.id

    old = registry.attach_identifier(
        db, asset_id,
        IdentifierRecord(IdentifierType.PROVIDER_SYMBOL, "KBANK.BK", source="yfinance"),
    )
    registry.attach_identifier(
        db, asset_id,
        IdentifierRecord(IdentifierType.PROVIDER_SYMBOL, "KBANK2.BK", source="yfinance"),
    )

    all_identifiers = registry.get_identifiers(db, asset_id)
    values = {row.value for row in all_identifiers}
    assert values == {"KBANK.BK", "KBANK2.BK"}  # both retained

    current = registry.get_identifiers(db, asset_id, current_only=True)
    assert len(current) == 1
    assert current[0].value == "KBANK2.BK"

    old_row = [row for row in all_identifiers if row.value == "KBANK.BK"][0]
    assert old_row.is_current is False
    assert old_row.id == old.id  # same row, not deleted+recreated


def test_conflicting_identifier_across_two_assets_rejected():
    db = make_session()
    a1 = registry.mint(db, _claim(canonical_symbol="KBANK"))
    a2 = registry.mint(db, _claim(canonical_symbol="PTT"))

    registry.attach_identifier(
        db, a1.id, IdentifierRecord(IdentifierType.ISIN, "TH0001010006", source="manual"),
    )

    with pytest.raises(AssetRegistryError):
        registry.attach_identifier(
            db, a2.id, IdentifierRecord(IdentifierType.ISIN, "TH0001010006", source="manual"),
        )


def test_attaching_same_identifier_twice_is_idempotent():
    db = make_session()
    asset = registry.mint(db, _claim())
    ident = IdentifierRecord(IdentifierType.ISIN, "TH0001010006", source="manual")

    first = registry.attach_identifier(db, asset.id, ident)
    second = registry.attach_identifier(db, asset.id, ident)

    assert first.id == second.id
    assert len(registry.get_identifiers(db, asset.id)) == 1


# ── Lifecycle transitions ────────────────────────────────────────────────────

def test_legal_lifecycle_transition_sequence():
    db = make_session()
    asset = registry.mint(db, _claim())

    registry.transition_status(db, asset.id, AssetStatus.SUSPENDED)
    assert registry.get_asset(db, asset.id).status == AssetStatus.SUSPENDED.value

    registry.transition_status(db, asset.id, AssetStatus.ACTIVE)
    assert registry.get_asset(db, asset.id).status == AssetStatus.ACTIVE.value

    registry.transition_status(db, asset.id, AssetStatus.DELISTED)
    registry.transition_status(db, asset.id, AssetStatus.ARCHIVED)
    assert registry.get_asset(db, asset.id).status == AssetStatus.ARCHIVED.value


def test_illegal_lifecycle_transition_rejected():
    db = make_session()
    asset = registry.mint(db, _claim())
    registry.transition_status(db, asset.id, AssetStatus.DELISTED)
    registry.transition_status(db, asset.id, AssetStatus.ARCHIVED)

    with pytest.raises(AssetRegistryError):
        registry.transition_status(db, asset.id, AssetStatus.ACTIVE)  # archived is terminal


def test_asset_id_and_canonical_symbol_survive_lifecycle_transitions():
    db = make_session()
    asset = registry.mint(db, _claim())
    asset_id, canonical_symbol = asset.id, asset.canonical_symbol

    registry.transition_status(db, asset.id, AssetStatus.SUSPENDED)
    registry.transition_status(db, asset.id, AssetStatus.DELISTED)
    registry.transition_status(db, asset.id, AssetStatus.ARCHIVED)

    final = registry.get_asset(db, asset_id)
    assert final.id == asset_id
    assert final.canonical_symbol == canonical_symbol  # never un-minted


# ── Classification stewardship ───────────────────────────────────────────────

def test_classification_is_dated_and_superseded_not_deleted():
    db = make_session()
    asset = registry.mint(db, _claim())

    registry.record_classification(
        db, asset.id, ClassificationDimension.SECTOR, "Financials", source="THAI_SECTOR_MAP",
    )
    registry.record_classification(
        db, asset.id, ClassificationDimension.SECTOR, "Banking", source="THAI_SECTOR_MAP",
    )

    all_rows = registry.get_classifications(db, asset.id, dimension=ClassificationDimension.SECTOR)
    assert {row.value for row in all_rows} == {"Financials", "Banking"}  # both retained

    current = registry.get_classifications(
        db, asset.id, dimension=ClassificationDimension.SECTOR, current_only=True,
    )
    assert len(current) == 1
    assert current[0].value == "Banking"


def test_classification_value_is_not_enum_constrained():
    """Classification values are registry-managed vocabulary, not a
    compile-time enum — an arbitrary taxonomy string must be accepted."""
    db = make_session()
    asset = registry.mint(db, _claim())

    row = registry.record_classification(
        db, asset.id, ClassificationDimension.SECTOR, "ธนาคาร", source="THAI_SECTOR_MAP",
    )
    assert row.value == "ธนาคาร"


def test_empty_classification_value_rejected():
    db = make_session()
    asset = registry.mint(db, _claim())

    with pytest.raises(AssetRegistryError):
        registry.record_classification(db, asset.id, ClassificationDimension.SECTOR, "  ", source="manual")


# ── Relationships (multiple listings) ────────────────────────────────────────

def test_relationship_links_listings_without_merging_identity():
    db = make_session()
    thai = registry.mint(db, _claim(canonical_symbol="KBANK", market="TH", exchange="SET", currency="THB"))
    dr = registry.mint(db, _claim(canonical_symbol="KBANK_DR", market="US", exchange="OTC", currency="USD"))

    rel = registry.link_relationship(db, dr.id, thai.id, RelationshipType.DEPOSITARY_RECEIPT_OF)

    assert rel.from_asset_id == dr.id
    assert rel.to_asset_id == thai.id
    # both listings keep their own independent identity
    assert registry.get_asset(db, dr.id).canonical_symbol == "KBANK_DR"
    assert registry.get_asset(db, thai.id).canonical_symbol == "KBANK"


def test_relationship_rejects_self_link():
    db = make_session()
    asset = registry.mint(db, _claim())

    with pytest.raises(AssetRegistryError):
        registry.link_relationship(db, asset.id, asset.id, RelationshipType.DUAL_LISTED)


def test_duplicate_relationship_is_idempotent():
    db = make_session()
    a1 = registry.mint(db, _claim(canonical_symbol="KBANK"))
    a2 = registry.mint(db, _claim(canonical_symbol="KBANK_DR"))

    first = registry.link_relationship(db, a2.id, a1.id, RelationshipType.DEPOSITARY_RECEIPT_OF)
    second = registry.link_relationship(db, a2.id, a1.id, RelationshipType.DEPOSITARY_RECEIPT_OF)

    assert first.id == second.id
    assert len(registry.get_relationships(db, a1.id)) == 1


# ── Absence is data ───────────────────────────────────────────────────────────

def test_asset_with_no_identifiers_or_classification_is_valid():
    db = make_session()
    asset = registry.mint(db, _claim(canonical_symbol="XYZ"))

    assert registry.get_identifiers(db, asset.id) == []
    assert registry.get_classifications(db, asset.id) == []
    assert registry.get_asset(db, asset.id) is not None
