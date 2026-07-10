"""Tests for the Registry Lookup Foundation (M6 Compatibility-Layer
Integration, Phase 1).

Validates services/registry_lookup.py in isolation:
  1. A symbol with a current PROVIDER_SYMBOL mapping resolves to an
     AssetView (case-insensitive).
  2. A symbol with no matching evidence returns Unresolved, never raises.
  3. Historical-identifier lookups reuse identity_resolver's own
     current-preempts-historical precedence rather than reimplementing it:
     a symbol reused by a second asset resolves decisively to the current
     holder; a symbol that is only ever historical (no current claimant)
     is honestly reported Unresolved (AMBIGUOUS under DEFAULT_POLICY's
     PROVIDER_SYMBOL weight), never guessed.
  4. Cache hit / cache expiry / unresolved-is-cached-too, verified by
     counting identity_resolver.resolve() invocations.
  5. resolve_asset(asset_id=...) and resolve_many().
  6. Thread safety of the underlying TTL cache.
  7. No ORM object leakage — AssetView is a frozen dataclass of plain
     values, never models.asset.Asset itself.

All tests use an in-memory SQLite database; no network calls.
"""
import os
import sys
import threading
import time
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base
import models.asset  # noqa: F401 — registers Asset* tables on Base.metadata
import models.registry_finding  # noqa: F401 — registers RegistryFinding table
from models.asset import Asset

from services import identity_resolver
from services import registry_lookup as lookup
from services import registry_service as svc
from services.asset_domain import AssetClaim, AssetId, AssetType, IdentifierRecord, IdentifierType


def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _claim(**overrides):
    defaults = dict(
        canonical_symbol="AOT.BK",
        asset_type=AssetType.EQUITY,
        market="Thailand",
        exchange="SET",
        currency="THB",
    )
    defaults.update(overrides)
    return AssetClaim(**defaults)


def _provider_symbol(value: str) -> IdentifierRecord:
    return IdentifierRecord(identifier_type=IdentifierType.PROVIDER_SYMBOL, value=value, source="test")


@pytest.fixture(autouse=True)
def _reset_cache():
    """Every test gets an empty cache at default settings — the module-
    level cache is process-global, so tests must not leak state into
    each other."""
    lookup.invalidate_cache()
    lookup.configure_cache(ttl_seconds=lookup._DEFAULT_TTL_SECONDS, max_size=lookup._DEFAULT_MAX_SIZE)
    yield
    lookup.invalidate_cache()
    lookup.configure_cache(ttl_seconds=lookup._DEFAULT_TTL_SECONDS, max_size=lookup._DEFAULT_MAX_SIZE)


# ── Resolved lookup ──────────────────────────────────────────────────────

def test_resolved_symbol_returns_asset_view():
    db = make_session()
    asset = svc.mint_asset(db, _claim(), identifiers=[_provider_symbol("AOT.BK")])

    result = lookup.resolve_asset(db, "AOT.BK")

    assert isinstance(result, lookup.AssetView)
    assert result.asset_id == asset.id
    assert result.canonical_symbol == "AOT.BK"
    assert result.display_symbol == "AOT.BK"
    assert result.market == "Thailand"
    assert result.exchange == "SET"
    assert result.currency == "THB"
    assert result.asset_type == AssetType.EQUITY


def test_resolved_symbol_lookup_is_case_insensitive():
    db = make_session()
    svc.mint_asset(db, _claim(), identifiers=[_provider_symbol("AOT.BK")])

    result = lookup.resolve_asset(db, "aot.bk")

    assert isinstance(result, lookup.AssetView)
    assert result.canonical_symbol == "AOT.BK"


def test_asset_view_includes_current_classification():
    db = make_session()
    asset = svc.mint_asset(db, _claim(), identifiers=[_provider_symbol("AOT.BK")])
    from services.asset_domain import ClassificationDimension
    svc.record_classification(db, AssetId(asset.id), ClassificationDimension.SECTOR, "Transportation", source="test")

    result = lookup.resolve_asset(db, "AOT.BK")

    assert result.classification == {"SECTOR": "Transportation"}


# ── Unknown lookup ───────────────────────────────────────────────────────

def test_unknown_symbol_returns_unresolved_never_raises():
    db = make_session()

    result = lookup.resolve_asset(db, "NOPE")

    assert isinstance(result, lookup.Unresolved)
    assert result.query == "NOPE"
    assert "no matching asset" in result.reason


def test_empty_symbol_returns_unresolved_without_calling_resolver():
    db = make_session()

    with patch.object(identity_resolver, "resolve", wraps=identity_resolver.resolve) as spy:
        result = lookup.resolve_asset(db, "")
        assert isinstance(result, lookup.Unresolved)
        assert spy.call_count == 0


# ── Historical identifier lookup ────────────────────────────────────────

def test_symbol_reused_by_newer_asset_resolves_to_current_holder():
    db = make_session()
    asset_a = svc.mint_asset(db, _claim(canonical_symbol="OLD_A"), identifiers=[_provider_symbol("SHARED")])
    # Asset A moves on to a new identifier, superseding SHARED on A —
    # SHARED becomes historical-only on A, freeing it for reuse.
    svc.attach_identifier(db, AssetId(asset_a.id), _provider_symbol("NEWCODE_A"))

    asset_b = svc.mint_asset(db, _claim(canonical_symbol="NEW_B"), identifiers=[_provider_symbol("SHARED")])

    result = lookup.resolve_asset(db, "SHARED")

    assert isinstance(result, lookup.AssetView)
    assert result.asset_id == asset_b.id


def test_purely_historical_symbol_with_no_current_claimant_is_unresolved_not_guessed():
    db = make_session()
    asset = svc.mint_asset(db, _claim(canonical_symbol="RETIRED_CO"), identifiers=[_provider_symbol("RETIRED")])
    # Superseded on the same asset — RETIRED is now historical-only,
    # nobody currently claims it.
    svc.attach_identifier(db, AssetId(asset.id), _provider_symbol("REPLACEMENT"))

    result = lookup.resolve_asset(db, "RETIRED")

    # A single historical PROVIDER_SYMBOL match (weight 50 * 0.95 = 47.5)
    # falls under DEFAULT_POLICY.resolved_threshold (50.0) — this module
    # must not treat that as decisive; it must report exactly what
    # identity_resolver decided, not paper over it.
    assert isinstance(result, lookup.Unresolved)


# ── Caching ──────────────────────────────────────────────────────────────

def test_cache_hit_does_not_call_resolver_again():
    db = make_session()
    svc.mint_asset(db, _claim(), identifiers=[_provider_symbol("AOT.BK")])

    with patch.object(identity_resolver, "resolve", wraps=identity_resolver.resolve) as spy:
        first = lookup.resolve_asset(db, "AOT.BK")
        second = lookup.resolve_asset(db, "AOT.BK")

    assert first == second
    assert spy.call_count == 1


def test_unresolved_result_is_cached_too():
    db = make_session()

    with patch.object(identity_resolver, "resolve", wraps=identity_resolver.resolve) as spy:
        lookup.resolve_asset(db, "NOPE")
        lookup.resolve_asset(db, "NOPE")

    assert spy.call_count == 1


def test_cache_expiry_reissues_resolver_call():
    db = make_session()
    svc.mint_asset(db, _claim(), identifiers=[_provider_symbol("AOT.BK")])
    lookup.configure_cache(ttl_seconds=0.05)

    with patch.object(identity_resolver, "resolve", wraps=identity_resolver.resolve) as spy:
        lookup.resolve_asset(db, "AOT.BK")
        time.sleep(0.12)
        lookup.resolve_asset(db, "AOT.BK")

    assert spy.call_count == 2


def test_invalidate_cache_for_one_key_forces_refetch():
    db = make_session()
    svc.mint_asset(db, _claim(), identifiers=[_provider_symbol("AOT.BK")])

    with patch.object(identity_resolver, "resolve", wraps=identity_resolver.resolve) as spy:
        lookup.resolve_asset(db, "AOT.BK")
        lookup.invalidate_cache("AOT.BK")
        lookup.resolve_asset(db, "AOT.BK")

    assert spy.call_count == 2


def test_max_size_evicts_oldest_entry():
    db = make_session()
    svc.mint_asset(db, _claim(canonical_symbol="ONE"), identifiers=[_provider_symbol("ONE")])
    svc.mint_asset(db, _claim(canonical_symbol="TWO"), identifiers=[_provider_symbol("TWO")])
    svc.mint_asset(db, _claim(canonical_symbol="THREE"), identifiers=[_provider_symbol("THREE")])
    lookup.configure_cache(max_size=2)

    with patch.object(identity_resolver, "resolve", wraps=identity_resolver.resolve) as spy:
        lookup.resolve_asset(db, "ONE")     # fills slot 1
        lookup.resolve_asset(db, "TWO")     # fills slot 2
        lookup.resolve_asset(db, "THREE")   # evicts ONE (least recently used)
        lookup.resolve_asset(db, "ONE")     # cache miss again

    assert spy.call_count == 4


# ── asset_id lookup ──────────────────────────────────────────────────────

def test_resolve_by_asset_id():
    db = make_session()
    asset = svc.mint_asset(db, _claim(), identifiers=[_provider_symbol("AOT.BK")])

    result = lookup.resolve_asset(db, AssetId(asset.id))

    assert isinstance(result, lookup.AssetView)
    assert result.asset_id == asset.id


def test_resolve_by_unknown_asset_id_returns_unresolved():
    db = make_session()

    result = lookup.resolve_asset(db, 999999)

    assert isinstance(result, lookup.Unresolved)


def test_resolve_asset_rejects_non_str_non_int_query():
    db = make_session()

    with pytest.raises(TypeError):
        lookup.resolve_asset(db, 3.14)


# ── resolve_many ─────────────────────────────────────────────────────────

def test_resolve_many_keys_results_by_original_query():
    db = make_session()
    asset = svc.mint_asset(db, _claim(), identifiers=[_provider_symbol("AOT.BK")])

    results = lookup.resolve_many(db, ["AOT.BK", "NOPE", AssetId(asset.id)])

    assert isinstance(results["AOT.BK"], lookup.AssetView)
    assert isinstance(results["NOPE"], lookup.Unresolved)
    assert isinstance(results[AssetId(asset.id)], lookup.AssetView)


# ── No ORM leakage ───────────────────────────────────────────────────────

def test_asset_view_never_leaks_the_orm_model():
    db = make_session()
    svc.mint_asset(db, _claim(), identifiers=[_provider_symbol("AOT.BK")])

    result = lookup.resolve_asset(db, "AOT.BK")

    assert not isinstance(result, Asset)
    with pytest.raises((AttributeError, TypeError)):
        result.canonical_symbol = "MUTATED"  # frozen dataclass — must reject mutation


# ── Thread safety (cache-level) ──────────────────────────────────────────

def test_ttl_cache_is_thread_safe_under_concurrent_access():
    cache = lookup._TTLCache(ttl_seconds=5.0, max_size=50)
    errors = []

    def worker(n: int) -> None:
        try:
            for i in range(200):
                key = ("symbol", f"SYM{(n + i) % 20}")
                cache.set(key, i)
                cache.get(key)
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    assert len(cache._store) <= 50
