"""Watchlist Registry Pilot — regression tests for GET/POST /watchlist's
additive Asset Registry metadata (docs/implementation/WATCHLIST_REGISTRY_PILOT.md).

Covers, per the pilot brief:
  - a resolved watchlist entry carries additive registry metadata
  - an unresolved entry falls back to today's behavior (never fails the request)
  - a historical-only alias (superseded identifier, no current claimant) is
    honestly reported unresolved, never guessed
  - a recycled ticker ("duplicate aliases": one symbol value claimed by two
    different assets over time) resolves to the current holder, never the
    original, stale asset
  - a mixed watchlist (resolved + unresolved + historical-alias entries in
    one call) is handled entry-by-entry with no cross-contamination
  - existing response fields are unchanged for every entry (API compatibility)
  - a total Registry failure degrades to "not evaluated" instead of failing
    the request (ENGINEERING_PRINCIPLES.md "Failure Handling")

Uses main.list_watchlist / main.add_watchlist directly (this codebase has no
FastAPI TestClient/HTTP-level test harness — see test_transaction_symbol_
normalization.py for the same "import main.py directly" convention). Network
calls (fetch_price_info, sector lookup) are monkeypatched out; only Registry
tables (in-memory SQLite) are exercised for real.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base, Watchlist
import models.asset  # noqa: F401 — registers Asset* tables on Base.metadata
import models.registry_finding  # noqa: F401 — registers RegistryFinding table

import main
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
        canonical_symbol="AOT.BK", asset_type=AssetType.EQUITY,
        market="Thailand", exchange="SET", currency="THB",
    )
    defaults.update(overrides)
    return AssetClaim(**defaults)


def _provider_symbol(value: str) -> IdentifierRecord:
    return IdentifierRecord(identifier_type=IdentifierType.PROVIDER_SYMBOL, value=value, source="test")


@pytest.fixture(autouse=True)
def _reset_cache():
    lookup.invalidate_cache()
    yield
    lookup.invalidate_cache()


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    monkeypatch.setattr(main, "fetch_price_info", lambda symbol: {"current_price": 100.0})

    async def _fake_fetch_sector(symbol: str) -> str:
        return "Other"

    monkeypatch.setattr(main, "_fetch_sector", _fake_fetch_sector)


def _add_watchlist_row(db, symbol: str) -> Watchlist:
    ws_id = main._ws_id(db)
    item = Watchlist(workspace_id=ws_id, symbol=symbol, sector="Other")
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


# ── Resolved entries ─────────────────────────────────────────────────────

def test_resolved_entry_carries_additive_registry_metadata():
    db = make_session()
    asset = svc.mint_asset(db, _claim(canonical_symbol="AOT.BK"), identifiers=[_provider_symbol("AOT.BK")])
    _add_watchlist_row(db, "AOT.BK")

    rows = asyncio.run(main.list_watchlist(db))

    assert len(rows) == 1
    registry = rows[0]["registry"]
    assert registry == {
        "resolved": True,
        "asset_id": asset.id,
        "canonical_symbol": "AOT.BK",
        "market": "Thailand",
        "exchange": "SET",
    }


# ── Unresolved entries ───────────────────────────────────────────────────

def test_unresolved_entry_falls_back_without_failing_request():
    db = make_session()
    _add_watchlist_row(db, "UNKNOWN_CO")

    rows = asyncio.run(main.list_watchlist(db))

    assert len(rows) == 1
    assert rows[0]["registry"] == {"resolved": False, "reason": "no matching asset"}


# ── Historical aliases ───────────────────────────────────────────────────

def test_historical_only_alias_is_honestly_unresolved_not_guessed():
    db = make_session()
    asset = svc.mint_asset(db, _claim(canonical_symbol="RETIRED_CO"), identifiers=[_provider_symbol("RETIRED")])
    # RETIRED is superseded on the same asset -> historical-only, no current claimant.
    svc.attach_identifier(db, AssetId(asset.id), _provider_symbol("REPLACEMENT"))
    _add_watchlist_row(db, "RETIRED")

    rows = asyncio.run(main.list_watchlist(db))

    assert len(rows) == 1
    assert rows[0]["registry"]["resolved"] is False


# ── Duplicate aliases (one symbol value claimed by two assets over time) ─

def test_recycled_symbol_resolves_to_current_holder_not_the_original_asset():
    """A ticker can be recycled: asset A once claimed "SHARED", moved on to
    a new identifier, and asset B later claimed "SHARED" for itself. A
    watchlist row for "SHARED" must resolve to B (the current holder),
    never to A and never ambiguously — the exact identity-resolution
    property Watchlist gains from the Registry that plain string equality
    could not provide (ASSET_REGISTRY.md Section 4)."""
    db = make_session()
    asset_old = svc.mint_asset(db, _claim(canonical_symbol="OLDCO"), identifiers=[_provider_symbol("SHARED")])
    # OLDCO moves on to a new ticker, freeing SHARED for legitimate reuse.
    svc.attach_identifier(db, AssetId(asset_old.id), _provider_symbol("OLDCO_NEW"))
    asset_new = svc.mint_asset(db, _claim(canonical_symbol="NEWCO"), identifiers=[_provider_symbol("SHARED")])

    _add_watchlist_row(db, "SHARED")

    rows = asyncio.run(main.list_watchlist(db))

    assert len(rows) == 1
    assert rows[0]["registry"] == {
        "resolved": True,
        "asset_id": asset_new.id,
        "canonical_symbol": "NEWCO",
        "market": "Thailand",
        "exchange": "SET",
    }


# ── Mixed watchlist ──────────────────────────────────────────────────────

def test_mixed_watchlist_resolves_each_entry_independently():
    db = make_session()
    resolved_asset = svc.mint_asset(db, _claim(canonical_symbol="PTT.BK"), identifiers=[_provider_symbol("PTT.BK")])
    retired_asset = svc.mint_asset(db, _claim(canonical_symbol="RETIRED_CO"), identifiers=[_provider_symbol("RETIRED")])
    svc.attach_identifier(db, AssetId(retired_asset.id), _provider_symbol("REPLACEMENT"))

    _add_watchlist_row(db, "PTT.BK")      # resolved
    _add_watchlist_row(db, "RETIRED")     # historical-only, unresolved
    _add_watchlist_row(db, "NEVER_SEEN")  # never registered, unresolved

    rows = asyncio.run(main.list_watchlist(db))

    assert len(rows) == 3
    by_symbol = {r["symbol"]: r for r in rows}
    assert by_symbol["PTT.BK"]["registry"] == {
        "resolved": True,
        "asset_id": resolved_asset.id,
        "canonical_symbol": "PTT.BK",
        "market": "Thailand",
        "exchange": "SET",
    }
    assert by_symbol["RETIRED"]["registry"]["resolved"] is False
    assert by_symbol["NEVER_SEEN"]["registry"] == {"resolved": False, "reason": "no matching asset"}


# ── API compatibility ────────────────────────────────────────────────────

def test_existing_response_fields_unchanged_regardless_of_registry_status():
    db = make_session()
    svc.mint_asset(db, _claim(canonical_symbol="PTT.BK"), identifiers=[_provider_symbol("PTT.BK")])
    resolved_item = _add_watchlist_row(db, "PTT.BK")
    unresolved_item = _add_watchlist_row(db, "UNKNOWN_CO")

    rows = asyncio.run(main.list_watchlist(db))
    by_symbol = {r["symbol"]: r for r in rows}

    expected_keys = {
        "id", "symbol", "latest_signal", "signal_confidence", "analyzed_at",
        "reasoning", "risks", "ta_score", "fa_score", "target_price",
        "upside_pct", "risk_level", "sector", "is_dr", "parent_symbol",
        "upside_reference_price", "registry",
    }
    for item, row in ((resolved_item, by_symbol["PTT.BK"]), (unresolved_item, by_symbol["UNKNOWN_CO"])):
        assert set(row.keys()) == expected_keys
        assert row["id"] == item.id
        assert row["symbol"] == item.symbol
        assert row["sector"] == "Other"
        assert row["latest_signal"] is None
        assert row["ta_score"] is None


def test_empty_watchlist_returns_empty_list():
    db = make_session()
    assert asyncio.run(main.list_watchlist(db)) == []


# ── Graceful degradation on Registry failure ────────────────────────────

def test_registry_failure_degrades_to_not_evaluated_without_failing_request(monkeypatch):
    db = make_session()
    svc.mint_asset(db, _claim(canonical_symbol="PTT.BK"), identifiers=[_provider_symbol("PTT.BK")])
    _add_watchlist_row(db, "PTT.BK")

    def _boom(db, queries):
        raise RuntimeError("registry unavailable")

    monkeypatch.setattr(main.registry_lookup, "resolve_many", _boom)

    rows = asyncio.run(main.list_watchlist(db))

    assert len(rows) == 1
    assert rows[0]["registry"] == {"resolved": False, "reason": "not evaluated"}
    # Non-registry fields are completely unaffected by the Registry outage.
    assert rows[0]["symbol"] == "PTT.BK"
    assert rows[0]["sector"] == "Other"


# ── POST /watchlist (add) ────────────────────────────────────────────────

def test_add_watchlist_returns_registry_metadata_for_new_entry():
    db = make_session()
    asset = svc.mint_asset(db, _claim(canonical_symbol="SCB.BK"), identifiers=[_provider_symbol("SCB.BK")])

    row = asyncio.run(main.add_watchlist(main.WatchlistCreate(symbol="SCB.BK"), db))

    assert row["registry"] == {
        "resolved": True,
        "asset_id": asset.id,
        "canonical_symbol": "SCB.BK",
        "market": "Thailand",
        "exchange": "SET",
    }


def test_add_watchlist_degrades_gracefully_when_registry_resolution_raises(monkeypatch):
    db = make_session()

    def _boom(db, query):
        raise RuntimeError("registry unavailable")

    monkeypatch.setattr(main.registry_lookup, "resolve_asset", _boom)

    row = asyncio.run(main.add_watchlist(main.WatchlistCreate(symbol="NEWCO"), db))

    assert row["symbol"] == "NEWCO"
    assert row["registry"] == {"resolved": False, "reason": "not evaluated"}
