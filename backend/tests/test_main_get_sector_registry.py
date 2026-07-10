"""main.py's _get_sector() / _fetch_sector() — Registry-priority regression
tests (docs/implementation/CLASSIFICATION_CONSOLIDATION.md).

Proves the read-path priority order end to end:
  0. Registry SECTOR classification (when the Registry resolved the symbol
     AND has a current SECTOR fact for it)
  1. DR / Thai static maps (services/sector_taxonomy.py)
  2. FA cache raw sector string, normalized
  3. "Other"

And that every fallback tier still behaves exactly as it did before the
Registry was consulted, for:
  - Thai equities (static map hit)
  - US equities (FA cache only, no static map hit)
  - a historical-only alias (Registry says "unresolved", never guesses —
    falls through to the static map exactly like an unknown symbol would)
  - an unresolved symbol with no static data and no FA cache ("Other")
  - a mixed batch of the above
  - a total Registry failure degrading gracefully instead of raising

Uses main._get_sector/_fetch_sector directly (this codebase has no FastAPI
TestClient harness — see test_watchlist_registry.py for the same
"import main.py directly" convention).
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base
import models.asset  # noqa: F401 — registers Asset* tables on Base.metadata
import models.registry_finding  # noqa: F401 — registers RegistryFinding table

import main
from services import registry_lookup as lookup
from services import registry_service as svc
from services.asset_domain import AssetClaim, AssetId, AssetType, ClassificationDimension, IdentifierRecord, IdentifierType


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


# ── Priority 0: Registry classification wins ────────────────────────────

def test_registry_classification_takes_priority_over_static_map():
    db = make_session()
    asset = _mint(db, "KBANK.BK")
    # Deliberately different from THAI_SECTOR_MAP's "Financial", to prove
    # the Registry value — not the static map — is what's returned.
    svc.record_classification(db, asset.id, ClassificationDimension.SECTOR, "Banking (Registry)", source="human:corrected")

    assert main._get_sector("KBANK.BK", None, db) == "Banking (Registry)"


def test_registry_resolved_but_unclassified_falls_back_to_static_map():
    db = make_session()
    _mint(db, "KBANK.BK")  # no classification recorded

    assert main._get_sector("KBANK.BK", None, db) == "Financial"


# ── Thai equities (static map, Registry unresolved) ─────────────────────

def test_thai_equity_unresolved_in_registry_falls_back_to_static_map():
    db = make_session()
    assert main._get_sector("PTT.BK", None, db) == "Energy"


# ── US equities (FA cache only) ──────────────────────────────────────────

def test_us_equity_uses_fa_cache_when_no_registry_and_no_static_entry():
    db = make_session()
    fa_cache = {"sector": "Technology"}
    assert main._get_sector("AAPL", fa_cache, db) == "Technology"


def test_us_equity_normalizes_raw_fa_sector_string():
    db = make_session()
    fa_cache = {"sector": "Consumer Cyclical"}
    assert main._get_sector("TSLA", fa_cache, db) == "Consumer"


# ── ETFs (no static/FA sector data) ──────────────────────────────────────

def test_etf_with_no_data_anywhere_returns_other():
    db = make_session()
    _mint(db, "SPY", asset_type=AssetType.ETF, market="United States", exchange="NYSEARCA", currency="USD")
    assert main._get_sector("SPY", None, db) == "Other"


# ── Historical aliases: Registry never guesses ───────────────────────────

def test_historical_only_alias_falls_back_to_static_map_not_guessed():
    """A superseded identifier (historical-only, no current claimant) must
    resolve as Unresolved from the Registry's own "resolve decisively or
    ask — never guess" rule (ASSET_REGISTRY.md Section 4) — exactly like
    test_watchlist_registry.py's identical-premise test. _get_sector must
    fall through to the static map/FA-cache/Other chain, not silently
    accept a stale mapping."""
    db = make_session()
    asset = _mint(db, "KBANK.BK")
    svc.attach_identifier(db, AssetId(asset.id), _provider_symbol("KBANK_NEW"))
    # "KBANK.BK" is now historical-only on `asset` — Unresolved from the
    # Registry's perspective, even though the asset still exists.

    assert main._get_sector("KBANK.BK", None, db) == "Financial"  # static map, not Registry-guessed


# ── Fully unresolved / no data anywhere ──────────────────────────────────

def test_unresolved_symbol_no_static_no_fa_cache_returns_other():
    db = make_session()
    assert main._get_sector("ZZZZ.BK", None, db) == "Other"


# ── db=None preserves pre-Registry behavior exactly ──────────────────────

def test_db_none_skips_registry_entirely_identical_to_pre_registry_behavior():
    assert main._get_sector("KBANK.BK", None, None) == "Financial"
    assert main._get_sector("ZZZZ.BK", {"sector": "Technology"}, None) == "Technology"


# ── Registry failure degrades gracefully ─────────────────────────────────

def test_registry_failure_degrades_to_static_fallback_without_raising(monkeypatch):
    db = make_session()

    def _boom(db, query):
        raise RuntimeError("registry unavailable")

    # main.py does `from services import registry_lookup` (module import),
    # so patching the module's attribute is visible from both names.
    monkeypatch.setattr(lookup, "resolve_asset", _boom)

    assert main._get_sector("KBANK.BK", None, db) == "Financial"


# ── Mixed batch ───────────────────────────────────────────────────────────

def test_mixed_batch_each_symbol_resolves_independently():
    db = make_session()
    asset = _mint(db, "KBANK.BK")
    svc.record_classification(db, asset.id, ClassificationDimension.SECTOR, "Banking (Registry)", source="human:corrected")
    _mint(db, "SPY", asset_type=AssetType.ETF, market="United States", exchange="NYSEARCA", currency="USD")

    assert main._get_sector("KBANK.BK", None, db) == "Banking (Registry)"          # Registry-classified
    assert main._get_sector("PTT.BK", None, db) == "Energy"                        # static map
    assert main._get_sector("AAPL", {"sector": "Technology"}, db) == "Technology"  # FA cache
    assert main._get_sector("SPY", None, db) == "Other"                            # resolved, no data
    assert main._get_sector("ZZZZ.BK", None, db) == "Other"                        # fully unresolved


# ── _fetch_sector: async wrapper, network fallback path ──────────────────

def test_fetch_sector_returns_static_map_value_without_calling_yfinance(monkeypatch):
    db = make_session()

    def _boom(*args, **kwargs):
        raise AssertionError("fetch_info should not be called when the static map already resolves")

    monkeypatch.setattr(main, "fetch_info", _boom)

    result = asyncio.run(main._fetch_sector("KBANK.BK", db))
    assert result == "Financial"


def test_fetch_sector_falls_back_to_yfinance_when_registry_and_static_map_miss(monkeypatch):
    db = make_session()

    def _fake_fetch_info(symbol):
        return {"sector": "Healthcare"}

    monkeypatch.setattr(main, "fetch_info", _fake_fetch_info)

    result = asyncio.run(main._fetch_sector("ZZZZ.BK", db))
    assert result == "Healthcare"
