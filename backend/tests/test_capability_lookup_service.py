"""capability_lookup_service.py unit tests (M30.1).

Coverage
--------
  1. successful lookup — a minted, identifier-attached symbol resolves to
     a real CapabilityView.
  2. unknown asset — a symbol with no Registry identifier at all.
  3. missing definition — a minted asset whose asset_type has no canonical
     Asset Definition (CRYPTO, COMMODITY, OTHER today).
  4. registry failure — DefinitionRegistry.build() raising is swallowed,
     never propagates out of this module.
  5. fallback / batch behavior — resolve_capability_views() handles a mix
     of resolved/unresolved symbols in one call without raising, and
     resolve_capability_view() is consistent with the batch form.

Mirrors the sqlite in-memory session setup and never-raises verification
style already used by test_asset_registry_runtime_consultation.py and
test_ledger_validator_runtime_consultation.py.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base
import models.asset  # noqa: F401 — registers Asset* tables on Base.metadata
from services import asset_registry as registry
from services import capability_lookup_service as lookup
from services.asset_definitions.capability_view import CapabilityView
from services.asset_definitions.vocabulary import AcquisitionSemantics
from services.asset_domain import AssetClaim, AssetType, IdentifierRecord, IdentifierType


def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _mint_with_symbol(db, symbol, asset_type, **overrides):
    claim = AssetClaim(
        canonical_symbol=symbol,
        asset_type=asset_type,
        market=overrides.pop("market", "TH"),
        exchange=overrides.pop("exchange", "SET"),
        currency=overrides.pop("currency", "THB"),
        **overrides,
    )
    return registry.mint(
        db, claim,
        identifiers=(IdentifierRecord(identifier_type=IdentifierType.PROVIDER_SYMBOL, value=symbol, source="test"),),
    )


# ── 1. Successful lookup ─────────────────────────────────────────────────

def test_successful_lookup_returns_real_capability_view():
    db = make_session()
    _mint_with_symbol(db, "KBANK", AssetType.EQUITY)

    result = lookup.resolve_capability_view(db, "KBANK")

    assert isinstance(result, CapabilityView)
    assert result.acquisition_semantics() == AcquisitionSemantics.VENUE_TRADED


# ── 2. Unknown asset ─────────────────────────────────────────────────────

def test_unknown_asset_returns_unresolved_capability():
    db = make_session()

    result = lookup.resolve_capability_view(db, "NEVER_MINTED")

    assert isinstance(result, lookup.UnresolvedCapability)
    assert result.symbol == "NEVER_MINTED"
    assert result.reason == lookup._REASON_UNKNOWN_ASSET


# ── 3. Missing definition ────────────────────────────────────────────────

def test_asset_type_without_definition_returns_unresolved_capability():
    db = make_session()
    _mint_with_symbol(db, "XYZ_CRYPTO", AssetType.CRYPTO)

    result = lookup.resolve_capability_view(db, "XYZ_CRYPTO")

    assert isinstance(result, lookup.UnresolvedCapability)
    assert result.reason == lookup._REASON_NO_DEFINITION


# ── 4. Registry failure ──────────────────────────────────────────────────

def test_registry_boot_failure_never_raises_and_marks_every_symbol():
    import services.asset_definitions.library as library

    db = make_session()
    _mint_with_symbol(db, "KBANK", AssetType.EQUITY)

    original = dict(library.PINNED_FINGERPRINTS)
    try:
        library.PINNED_FINGERPRINTS[(AssetType.CASH.value, "v1")] = "0" * 64
        result = lookup.resolve_capability_views(db, ["KBANK", "UNUSED"])
    finally:
        library.PINNED_FINGERPRINTS.clear()
        library.PINNED_FINGERPRINTS.update(original)

    assert set(result) == {"KBANK", "UNUSED"}
    for symbol, answer in result.items():
        assert isinstance(answer, lookup.UnresolvedCapability)
        assert answer.reason == lookup._REASON_REGISTRY_BOOT_FAILED


# ── 5. Fallback / batch behavior ─────────────────────────────────────────

def test_batch_lookup_handles_mixed_resolved_and_unresolved_symbols():
    db = make_session()
    _mint_with_symbol(db, "KBANK", AssetType.EQUITY)
    _mint_with_symbol(db, "XYZ_CRYPTO", AssetType.CRYPTO)

    result = lookup.resolve_capability_views(db, ["KBANK", "XYZ_CRYPTO", "NEVER_MINTED"])

    assert isinstance(result["KBANK"], CapabilityView)
    assert isinstance(result["XYZ_CRYPTO"], lookup.UnresolvedCapability)
    assert result["XYZ_CRYPTO"].reason == lookup._REASON_NO_DEFINITION
    assert isinstance(result["NEVER_MINTED"], lookup.UnresolvedCapability)
    assert result["NEVER_MINTED"].reason == lookup._REASON_UNKNOWN_ASSET


def test_duplicate_symbols_collapse_to_one_key():
    db = make_session()
    _mint_with_symbol(db, "KBANK", AssetType.EQUITY)

    result = lookup.resolve_capability_views(db, ["KBANK", "KBANK"])

    assert set(result) == {"KBANK"}


def test_single_symbol_form_matches_batch_form():
    db = make_session()
    _mint_with_symbol(db, "KBANK", AssetType.EQUITY)

    single = lookup.resolve_capability_view(db, "KBANK")
    batch = lookup.resolve_capability_views(db, ["KBANK"])["KBANK"]

    assert isinstance(single, CapabilityView)
    assert isinstance(batch, CapabilityView)
    assert single.acquisition_semantics() == batch.acquisition_semantics()


def test_lookup_never_raises_for_empty_symbol():
    db = make_session()

    result = lookup.resolve_capability_view(db, "")

    assert isinstance(result, lookup.UnresolvedCapability)
