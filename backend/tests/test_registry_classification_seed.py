"""services/registry_classification_seed.py — regression tests
(docs/implementation/CLASSIFICATION_CONSOLIDATION.md).

Covers:
  - a resolved, unclassified Thai equity gets seeded from THAI_SECTOR_MAP
  - a resolved, unclassified DR gets seeded from _DR_SECTOR_MAP via its prefix
  - a symbol already carrying a current SECTOR classification is left
    untouched (never overwritten), regardless of source
  - a symbol the Registry cannot resolve is reported unresolved, no write
  - a resolved symbol with no static seed data (e.g. an ETF/US ticker with
    no map entry) is reported no_seed_data, no write
  - dry_run=True performs zero writes for an otherwise-seedable symbol
  - a mixed batch resolves every symbol independently (no cross-contamination)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base
import models.asset  # noqa: F401 — registers Asset* tables on Base.metadata
import models.registry_finding  # noqa: F401 — registers RegistryFinding table

from services import registry_lookup as lookup
from services import registry_service as svc
from services.asset_domain import AssetClaim, AssetType, ClassificationDimension, IdentifierRecord, IdentifierType
from services.registry_classification_seed import seed_sector_classification


def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _claim(**overrides):
    defaults = dict(
        canonical_symbol="AOT.BK", asset_type=AssetType.EQUITY,
        market="Thailand", exchange="SET", currency="THB",
    )
    defaults.update(overrides)
    return AssetClaim(**defaults)


def _provider_symbol(value: str) -> IdentifierRecord:
    return IdentifierRecord(identifier_type=IdentifierType.PROVIDER_SYMBOL, value=value, source="test")


def _mint(db, symbol: str, **overrides):
    return svc.mint_asset(db, _claim(canonical_symbol=symbol, **overrides), identifiers=[_provider_symbol(symbol)])


@pytest.fixture(autouse=True)
def _reset_cache():
    lookup.invalidate_cache()
    yield
    lookup.invalidate_cache()


# ── Thai equities ────────────────────────────────────────────────────────

def test_thai_equity_seeded_from_static_map():
    db = make_session()
    asset = _mint(db, "KBANK.BK")

    report = seed_sector_classification(db, ["KBANK.BK"], dry_run=False)
    db.commit()

    assert report.seeded == 1
    assert report.outcomes[0].outcome == "seeded"
    assert report.outcomes[0].sector == "Financial"

    classifications = svc.get_classifications(db, asset.id, dimension=ClassificationDimension.SECTOR, current_only=True)
    assert len(classifications) == 1
    assert classifications[0].value == "Financial"
    assert classifications[0].source == "seed:sector_taxonomy"


# ── DR equities ──────────────────────────────────────────────────────────

def test_dr_equity_seeded_from_dr_sector_map():
    db = make_session()
    asset = _mint(db, "NVDA01.BK", market="United States", exchange="NASDAQ", currency="USD")

    report = seed_sector_classification(db, ["NVDA01.BK"], dry_run=False)
    db.commit()

    assert report.seeded == 1
    assert report.outcomes[0].sector == "Technology"
    classifications = svc.get_classifications(db, asset.id, dimension=ClassificationDimension.SECTOR, current_only=True)
    assert classifications[0].value == "Technology"


# ── Never overwrites ─────────────────────────────────────────────────────

def test_existing_classification_is_never_overwritten():
    db = make_session()
    asset = _mint(db, "KBANK.BK")
    svc.record_classification(db, asset.id, ClassificationDimension.SECTOR, "Banking", source="human:corrected")
    db.commit()

    report = seed_sector_classification(db, ["KBANK.BK"], dry_run=False)
    db.commit()

    assert report.already_classified == 1
    assert report.outcomes[0].sector == "Banking"
    classifications = svc.get_classifications(db, asset.id, dimension=ClassificationDimension.SECTOR, current_only=True)
    assert len(classifications) == 1
    assert classifications[0].value == "Banking"
    assert classifications[0].source == "human:corrected"


# ── Unresolved assets ────────────────────────────────────────────────────

def test_unresolved_symbol_is_reported_and_no_write_occurs():
    db = make_session()
    report = seed_sector_classification(db, ["NEVERSEEN.BK"], dry_run=False)
    db.commit()

    assert report.unresolved == 1
    assert report.outcomes[0].outcome == "unresolved"


# ── No seed data available ───────────────────────────────────────────────

def test_resolved_symbol_with_no_static_seed_data_is_reported():
    db = make_session()
    _mint(db, "SPY", asset_type=AssetType.ETF, market="United States", exchange="NYSEARCA", currency="USD")

    report = seed_sector_classification(db, ["SPY"], dry_run=False)
    db.commit()

    assert report.no_seed_data == 1
    assert report.outcomes[0].sector is None


# ── Dry run performs zero writes ─────────────────────────────────────────

def test_dry_run_performs_no_writes():
    db = make_session()
    asset = _mint(db, "KBANK.BK")

    report = seed_sector_classification(db, ["KBANK.BK"], dry_run=True)

    assert report.dry_run is True
    assert report.seeded == 1  # reported as would-be-seeded
    assert report.outcomes[0].sector == "Financial"

    classifications = svc.get_classifications(db, asset.id, dimension=ClassificationDimension.SECTOR, current_only=True)
    assert classifications == []  # nothing actually persisted


# ── Mixed batch ───────────────────────────────────────────────────────────

def test_mixed_batch_resolves_each_symbol_independently():
    db = make_session()
    _mint(db, "KBANK.BK")
    _mint(db, "SPY", asset_type=AssetType.ETF, market="United States", exchange="NYSEARCA", currency="USD")
    asset_pre_classified = _mint(db, "PTT.BK")
    svc.record_classification(db, asset_pre_classified.id, ClassificationDimension.SECTOR, "Energy", source="seed:sector_taxonomy")
    db.commit()

    report = seed_sector_classification(
        db, ["KBANK.BK", "SPY", "PTT.BK", "NEVERSEEN.BK"], dry_run=False,
    )
    db.commit()

    by_symbol = {o.symbol: o for o in report.outcomes}
    assert by_symbol["KBANK.BK"].outcome == "seeded"
    assert by_symbol["SPY"].outcome == "no_seed_data"
    assert by_symbol["PTT.BK"].outcome == "already_classified"
    assert by_symbol["NEVERSEEN.BK"].outcome == "unresolved"
    assert report.seeded == 1
    assert report.no_seed_data == 1
    assert report.already_classified == 1
    assert report.unresolved == 1
