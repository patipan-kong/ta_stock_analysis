"""Stage R1 (M12 brief): Asset Registry's shadow consultation of the Asset
Definition Runtime via _consult_runtime_for_mint(), plus the wiring into
mint() itself.

Coverage
--------
  1. EQUITY / CASH agree with the runtime (both have a canonical definition)
  2. Every other AssetType member disagrees -> UnknownCapability finding,
     never raised, mint() still succeeds
  3. Registry boot failure -> single MissingBinding finding, never raises,
     mint() still succeeds
  4. mint()'s observable behavior (return value, DB row, exceptions raised
     for real validation failures) is byte-identical whether or not the
     runtime consultation agrees, disagrees, or fails to boot
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base
import models.asset  # noqa: F401 — registers Asset* tables on Base.metadata
from services import asset_registry as registry
from services.asset_domain import AssetClaim, AssetType
from services.runtime_consultation import RuntimeConsultationLog, RuntimeFindingCategory


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


# ── 1. Defined types agree with the runtime ─────────────────────────────────

@pytest.mark.parametrize(
    "asset_type",
    [AssetType.EQUITY, AssetType.CASH, AssetType.ETF, AssetType.FUND, AssetType.BOND, AssetType.PROPERTY],
)
def test_defined_asset_types_agree_with_runtime(asset_type):
    log = registry._consult_runtime_for_mint(asset_type)
    assert log.consulted == 1
    assert log.agreements == 1
    assert log.findings == ()


# ── 2. Undefined types disagree -> UnknownCapability, never raised ─────────

@pytest.mark.parametrize(
    "asset_type",
    [AssetType.CRYPTO,
     AssetType.COMMODITY, AssetType.OTHER],
)
def test_undefined_asset_types_recorded_as_unknown_capability(asset_type):
    log = registry._consult_runtime_for_mint(asset_type)
    assert log.consulted == 1
    assert log.agreements == 0
    assert len(log.findings) == 1
    finding = log.findings[0]
    assert finding.category == RuntimeFindingCategory.UNKNOWN_CAPABILITY.value
    assert finding.check_id == "RUNTIME_MINT_ASSET_TYPE_DEFINITION"
    assert finding.binding == asset_type.value
    assert finding.legacy_result is True
    assert finding.runtime_result is False


def test_undefined_asset_type_still_mints_successfully():
    # M27: PROPERTY is now defined; CRYPTO is the still-undefined example now.
    db = make_session()
    asset = registry.mint(db, _claim(canonical_symbol="XYZ_CRYPTO", asset_type=AssetType.CRYPTO))

    assert asset.id is not None
    assert asset.asset_type == AssetType.CRYPTO.value


# ── 3. Registry boot failure -> one finding, never raises, mint unaffected ──

def test_registry_boot_failure_yields_single_finding_never_raises(monkeypatch):
    import services.asset_definitions.library as library

    original = dict(library.PINNED_FINGERPRINTS)
    try:
        library.PINNED_FINGERPRINTS[(AssetType.CASH.value, "v1")] = "0" * 64
        log = registry._consult_runtime_for_mint(AssetType.EQUITY)
    finally:
        library.PINNED_FINGERPRINTS.clear()
        library.PINNED_FINGERPRINTS.update(original)

    assert log.consulted == 0
    assert log.agreements == 0
    assert len(log.findings) == 1
    assert log.findings[0].check_id == "RUNTIME_REGISTRY_BOOT_FAILED"
    assert log.findings[0].category == RuntimeFindingCategory.MISSING_BINDING.value


def test_mint_succeeds_even_when_runtime_registry_is_broken(monkeypatch):
    import services.asset_definitions.library as library

    original = dict(library.PINNED_FINGERPRINTS)
    try:
        library.PINNED_FINGERPRINTS[(AssetType.CASH.value, "v1")] = "0" * 64
        db = make_session()
        asset = registry.mint(db, _claim())
        assert asset.id is not None
        assert asset.canonical_symbol == "KBANK"
    finally:
        library.PINNED_FINGERPRINTS.clear()
        library.PINNED_FINGERPRINTS.update(original)


# ── 4. mint()'s own behavior is unaffected by the consultation outcome ─────

def test_mint_behavior_identical_regardless_of_runtime_agreement():
    """Real validation failures (duplicate canonical_symbol, missing
    market/exchange/currency) still raise AssetRegistryError exactly as
    before, for both a runtime-agreeing (EQUITY) and a runtime-disagreeing
    (CRYPTO; FUND became runtime-agreeing as of M22, BOND as of M24, and
    PROPERTY as of M27, so none of the three serves as this test's
    disagreeing example any longer) asset_type — the consultation never
    changes which exceptions are raised or which assets are created."""
    for asset_type in (AssetType.EQUITY, AssetType.CRYPTO):
        db = make_session()
        symbol = f"DUP_{asset_type.value}"

        first = registry.mint(db, _claim(canonical_symbol=symbol, asset_type=asset_type))
        assert first.id is not None

        with pytest.raises(registry.AssetRegistryError):
            registry.mint(db, _claim(canonical_symbol=symbol, asset_type=asset_type))

        with pytest.raises(registry.AssetRegistryError):
            registry.mint(db, _claim(canonical_symbol=f"{symbol}_2", asset_type=asset_type, currency=""))


def test_runtime_consultation_never_raises_out_of_mint(monkeypatch):
    """Even if _consult_runtime_for_mint() itself raised an unexpected
    exception, mint() must swallow it and still complete successfully —
    mirroring the ledger validator's own call-site safety net (M11)."""
    def _boom(asset_type):
        raise RuntimeError("simulated unexpected failure")

    monkeypatch.setattr(registry, "_consult_runtime_for_mint", _boom)

    db = make_session()
    asset = registry.mint(db, _claim())
    assert asset.id is not None
    assert asset.canonical_symbol == "KBANK"
