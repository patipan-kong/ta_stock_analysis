"""Tests for services/registry_symbol_matching.py — the M6 Compatibility-
Layer Integration Phase 2 replacement for the five independently hand-rolled
`.BK`-suffix variant matchers (basket_simulation, execution_plan,
position_sizing, allocation_engine, idea_review).

Coverage:
  1. Exact match — trivial, no Registry/heuristic involvement needed.
  2. Registry match wins outright when both sides independently resolve to
     the same asset_id — verified with resolve_asset() mocked to a
     controlled two-sided result, since this codebase's identity_resolver
     treats two live PROVIDER_SYMBOL identifiers on one asset as ambiguous
     rather than both resolving cleanly (confirmed empirically against the
     real Registry — see the docstring note on that below), so a live,
     un-mocked fixture cannot exercise this branch today. The branch still
     matters: it is what activates automatically, with no code change here,
     once Registry data quality (or identity_resolver's own scoring)
     improves enough for both spellings of one asset to resolve at once.
  3. Legacy heuristic fallback — nothing minted at all; behavior is
     byte-for-byte what basket_simulation/idea_review/etc. did before.
  4. No match at all — neither Registry nor heuristic can relate the symbols.
  5. Registry CONFLICT is never overridden by the heuristic — two distinct
     minted assets, one per spelling, must never be silently unified just
     because their spellings differ by `.BK` (ASSET_REGISTRY.md §5). This
     one runs against the real Registry: each spelling is the sole
     identifier of its own asset, so no ambiguity is involved.
  6. Registry decisive-but-unrelated symbol still falls back to the
     heuristic for `known` entries the Registry itself never resolved —
     also against the real Registry, single-identifier-per-asset.
  7. No ORM/DB leakage — the function is DB-only, returns plain str->str.

All tests use an in-memory SQLite database; no network calls except where
noted above.

Note on the identity_resolver quirk: minting one asset with two current
PROVIDER_SYMBOL identifiers (e.g. "AOT" and "AOT.BK", whether attached
together at mint time or sequentially via attach_identifier) makes the
*first*-attached value resolve AMBIGUOUS when queried on its own, while only
the most-recently-attached value resolves cleanly — confirmed by direct
experimentation against services/identity_resolver.py in this session. That
is pre-existing behavior of the M3 resolver, unrelated to and unmodified by
this module; it is out of scope for the M6 Phase 2 compatibility-layer work
this file tests (see docs/implementation/M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md
§4.3 — this module reuses resolve_asset() as-is and adds no identity rules).
"""
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base
import models.asset  # noqa: F401 — registers Asset* tables on Base.metadata
import models.registry_finding  # noqa: F401 — registers RegistryFinding table

from services import registry_lookup as lookup
from services import registry_service as svc
from services.asset_domain import AssetClaim, AssetId, AssetType, IdentifierRecord, IdentifierType
from services.registry_symbol_matching import match_known_symbols


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
    lookup.invalidate_cache()
    yield
    lookup.invalidate_cache()


# ── Exact match ──────────────────────────────────────────────────────────────

def test_exact_match_needs_no_registry_or_heuristic():
    db = make_session()
    result = match_known_symbols(db, ["AAPL"], ["AAPL", "MSFT"])
    assert result == {"AAPL": "AAPL"}


# ── Registry match wins outright when both sides independently resolve ─────

def test_registry_match_wins_even_when_spellings_are_not_bk_related():
    """Two query/known strings that share no `.BK` relationship at all —
    the legacy heuristic could never match these — but resolve_asset()
    returns the same asset_id for both, so the Registry path must be what
    produces the match."""
    db = make_session()
    view_a = lookup.AssetView(
        asset_id=AssetId(42), canonical_symbol="NEWNAME", display_symbol="NEWNAME",
        market="Thailand", exchange="SET", currency="THB", asset_type=AssetType.EQUITY,
    )
    view_b = lookup.AssetView(
        asset_id=AssetId(42), canonical_symbol="NEWNAME", display_symbol="OLDNAME",
        market="Thailand", exchange="SET", currency="THB", asset_type=AssetType.EQUITY,
    )

    def fake_resolve(db, query):
        return {"NEWNAME": view_a, "OLDNAME": view_b}.get(query, lookup.Unresolved(query=str(query), reason="no matching asset"))

    with patch.object(lookup, "resolve_asset", side_effect=fake_resolve):
        result = match_known_symbols(db, ["NEWNAME"], ["OLDNAME"])

    assert result == {"NEWNAME": "OLDNAME"}


# ── Legacy heuristic fallback ────────────────────────────────────────────────

def test_falls_back_to_bare_bk_heuristic_when_nothing_is_registered():
    db = make_session()
    result = match_known_symbols(db, ["BH"], ["BH.BK"])
    assert result == {"BH": "BH.BK"}


def test_falls_back_to_bk_stripped_heuristic_when_nothing_is_registered():
    db = make_session()
    result = match_known_symbols(db, ["BH.BK"], ["BH"])
    assert result == {"BH.BK": "BH"}


# ── No match ──────────────────────────────────────────────────────────────────

def test_unrelated_symbols_produce_no_match():
    db = make_session()
    result = match_known_symbols(db, ["ZZZ"], ["AAA"])
    assert result == {}


def test_symbol_with_no_known_entries_produces_no_match():
    db = make_session()
    result = match_known_symbols(db, ["AAPL"], [])
    assert result == {}


# ── Registry conflict must never be overridden by the heuristic ─────────────

def test_registry_conflict_is_not_silently_unified_by_bk_heuristic():
    """Two genuinely distinct minted assets, one claiming 'BH' and the other
    claiming 'BH.BK'. The Registry has decisively said these are different
    instruments (e.g. a DR vs. its underlying, ASSET_REGISTRY.md §5) — the
    `.BK` string heuristic must not paper over that with a false match."""
    db = make_session()
    svc.mint_asset(db, _claim(canonical_symbol="BH"), identifiers=[_provider_symbol("BH")])
    svc.mint_asset(db, _claim(canonical_symbol="BH.BK"), identifiers=[_provider_symbol("BH.BK")])

    result = match_known_symbols(db, ["BH"], ["BH.BK"])

    assert result == {}


def test_registry_decisive_symbol_still_falls_back_for_unresolved_knowns():
    """`sym` resolves decisively to an asset with no counterpart among
    `known`, but an *unrelated*, Registry-unresolved known entry still
    matches it via the legacy .BK heuristic — the Registry's decisive
    "no" about the *other* known asset must not block this one."""
    db = make_session()
    svc.mint_asset(db, _claim(canonical_symbol="AOT"), identifiers=[_provider_symbol("AOT")])

    result = match_known_symbols(db, ["AOT"], ["AOT.BK"])

    # "AOT.BK" was never minted/claimed, so the Registry has no opinion on
    # it — the bare/.BK heuristic is free to match it against "AOT".
    assert result == {"AOT": "AOT.BK"}


# ── No ORM/DB leakage — pure str -> str ──────────────────────────────────────

def test_return_shape_is_plain_str_to_str():
    db = make_session()
    svc.mint_asset(
        db, _claim(canonical_symbol="AOT.BK"),
        identifiers=[_provider_symbol("AOT.BK"), _provider_symbol("AOT")],
    )
    result = match_known_symbols(db, ["AOT", "ZZZ"], ["AOT.BK"])
    for k, v in result.items():
        assert isinstance(k, str)
        assert isinstance(v, str)
