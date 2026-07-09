"""Tests for services/registry_recommendation_context.py — the M6
Compatibility-Layer Integration Phase 3 recommendation write-path
integration (docs/architecture/REGISTRY_INTEGRATION_GUIDE.md,
docs/implementation/M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md Section 5,
Phase 3).

Coverage (mapped to the Phase 3 brief's required scenarios):
  1. Resolved recommendation — a symbol with a single, unambiguous minted
     identifier resolves to full AssetView metadata.
  2. Unresolved recommendation — a symbol with no minted asset falls back
     to resolved=False with a reason, never guessed.
  3. Historical/alias recommendation — a symbol that is a non-canonical
     alias of a minted asset (canonical_symbol differs from the submitted
     query) still resolves, and the submitted symbol is preserved as the
     dict key untouched.
  4. Duplicate alias recommendation — two different submitted spellings
     that the Registry says are the same instrument both carry the same
     asset_id in the batch result. Uses a mocked resolve_asset(), for the
     same reason documented in test_registry_symbol_matching.py: this
     codebase's identity_resolver treats two live PROVIDER_SYMBOL
     identifiers on one asset as ambiguous rather than both resolving
     cleanly when queried independently — a pre-existing M3 quirk, out of
     scope here, confirmed in the Phase 2 session.
  5. Mixed resolved/unresolved batch — one real minted asset alongside one
     genuinely unknown symbol in the same call.
  6. Graceful failure — an unexpected exception resolving one symbol (not
     an ordinary Unresolved) is caught per-symbol and never propagates.
  7. Additive-only, non-mutating enrichment — enrich_scores_map_for_
     snapshot() never mutates its input and only adds a "registry" key.
  8. Fallback on total Registry failure — if building the batch context
     itself raises, the original scores_map is returned unchanged rather
     than blocking Recommendation generation.
  9. End-to-end persistence — write_recommendation_snapshot() (unmodified
     by this phase) round-trips the enriched scores_map into
     RecommendationSnapshot.scores_map_json with no other field affected,
     proving the "outputs remain identical except for additive Registry
     metadata" regression requirement.

All tests use an in-memory SQLite database; no network calls.
"""
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base, OptimizerHistory, Portfolio, RecommendationSnapshot, Workspace
import models.asset  # noqa: F401 — registers Asset* tables on Base.metadata
import models.registry_finding  # noqa: F401 — registers RegistryFinding table

from services import registry_lookup as lookup
from services import registry_service as svc
from services.asset_domain import AssetClaim, AssetId, AssetType, IdentifierRecord, IdentifierType
from services.decision_memory.snapshot_writer import write_recommendation_snapshot
from services.registry_recommendation_context import (
    build_registry_context,
    enrich_scores_map_for_snapshot,
)


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


# ── Resolved recommendation ─────────────────────────────────────────────────

def test_resolved_symbol_gets_asset_metadata():
    db = make_session()
    svc.mint_asset(db, _claim(canonical_symbol="AOT"), identifiers=[_provider_symbol("AOT")])

    context = build_registry_context(db, ["AOT"])

    assert context["AOT"]["resolved"] is True
    assert context["AOT"]["canonical_symbol"] == "AOT"
    assert context["AOT"]["market"] == "Thailand"
    assert context["AOT"]["exchange"] == "SET"
    assert isinstance(context["AOT"]["asset_id"], int)


# ── Unresolved recommendation ───────────────────────────────────────────────

def test_unresolved_symbol_gets_resolved_false_with_reason():
    db = make_session()

    context = build_registry_context(db, ["ZZZ"])

    assert context["ZZZ"]["resolved"] is False
    assert context["ZZZ"]["reason"]


# ── Historical / alias recommendation ───────────────────────────────────────

def test_alias_symbol_resolves_to_canonical_symbol_different_from_submitted():
    db = make_session()
    svc.mint_asset(db, _claim(canonical_symbol="AOT.BK"), identifiers=[_provider_symbol("AOT")])

    context = build_registry_context(db, ["AOT"])

    # The submitted symbol ("AOT") is preserved as the dict key untouched,
    # even though the Registry's canonical spelling ("AOT.BK") differs.
    assert "AOT" in context
    assert context["AOT"]["resolved"] is True
    assert context["AOT"]["canonical_symbol"] == "AOT.BK"


# ── Duplicate alias recommendation ──────────────────────────────────────────

def test_duplicate_alias_symbols_in_one_batch_resolve_to_same_asset_id():
    db = make_session()
    view_a = lookup.AssetView(
        asset_id=AssetId(99), canonical_symbol="NEWNAME", display_symbol="NEWNAME",
        market="Thailand", exchange="SET", currency="THB", asset_type=AssetType.EQUITY,
    )
    view_b = lookup.AssetView(
        asset_id=AssetId(99), canonical_symbol="NEWNAME", display_symbol="OLDNAME",
        market="Thailand", exchange="SET", currency="THB", asset_type=AssetType.EQUITY,
    )

    def fake_resolve(db, query):
        return {"NEWNAME": view_a, "OLDNAME": view_b}.get(
            query, lookup.Unresolved(query=str(query), reason="no matching asset"),
        )

    with patch.object(lookup, "resolve_asset", side_effect=fake_resolve):
        context = build_registry_context(db, ["NEWNAME", "OLDNAME"])

    assert context["NEWNAME"]["asset_id"] == context["OLDNAME"]["asset_id"] == 99
    assert context["NEWNAME"]["canonical_symbol"] == context["OLDNAME"]["canonical_symbol"] == "NEWNAME"


# ── Mixed resolved/unresolved batch ─────────────────────────────────────────

def test_mixed_resolved_and_unresolved_batch():
    db = make_session()
    svc.mint_asset(db, _claim(canonical_symbol="AOT"), identifiers=[_provider_symbol("AOT")])

    context = build_registry_context(db, ["AOT", "NOPE"])

    assert context["AOT"]["resolved"] is True
    assert context["NOPE"]["resolved"] is False


# ── Graceful failure ─────────────────────────────────────────────────────────

def test_resolve_asset_exception_is_caught_and_recorded_as_unresolved():
    db = make_session()
    svc.mint_asset(db, _claim(canonical_symbol="AOT"), identifiers=[_provider_symbol("AOT")])

    def flaky_resolve(db, query):
        if query == "BOOM":
            raise RuntimeError("simulated registry outage")
        return lookup.Unresolved(query=str(query), reason="no matching asset")

    with patch.object(lookup, "resolve_asset", side_effect=flaky_resolve):
        context = build_registry_context(db, ["BOOM", "AOT"])

    assert context["BOOM"]["resolved"] is False
    assert "resolution error" in context["BOOM"]["reason"]
    # The exception on one symbol never aborts the rest of the batch.
    assert context["AOT"]["resolved"] is False  # mocked resolver always returns Unresolved here


# ── Additive-only, non-mutating enrichment ──────────────────────────────────

def test_enrich_scores_map_for_snapshot_is_additive_and_does_not_mutate_input():
    db = make_session()
    svc.mint_asset(db, _claim(canonical_symbol="AOT"), identifiers=[_provider_symbol("AOT")])

    original_entry = {"symbol": "AOT", "signal": "BUY", "current_price": 32.5}
    scores_map = {"AOT": original_entry, "ZZZ": {"symbol": "ZZZ", "signal": "HOLD"}}

    enriched = enrich_scores_map_for_snapshot(db, scores_map)

    # Original dict and its entries are untouched.
    assert "registry" not in scores_map["AOT"]
    assert scores_map["AOT"] is original_entry
    assert scores_map["AOT"] == {"symbol": "AOT", "signal": "BUY", "current_price": 32.5}

    # Enriched copy carries every original field plus the additive key.
    assert enriched["AOT"]["symbol"] == "AOT"
    assert enriched["AOT"]["signal"] == "BUY"
    assert enriched["AOT"]["current_price"] == 32.5
    assert enriched["AOT"]["registry"]["resolved"] is True
    assert enriched["ZZZ"]["registry"]["resolved"] is False


def test_enrich_scores_map_for_snapshot_falls_back_to_original_on_registry_failure():
    db = make_session()
    scores_map = {"AOT": {"symbol": "AOT", "signal": "BUY"}}

    with patch(
        "services.registry_recommendation_context.build_registry_context",
        side_effect=RuntimeError("registry down"),
    ):
        result = enrich_scores_map_for_snapshot(db, scores_map)

    assert result is scores_map


# ── End-to-end persistence ──────────────────────────────────────────────────

def test_write_recommendation_snapshot_persists_enriched_scores_map_unchanged_otherwise():
    db = make_session()
    svc.mint_asset(db, _claim(canonical_symbol="AOT"), identifiers=[_provider_symbol("AOT")])

    db.add(Workspace(id=1, name="Default"))
    db.add(Portfolio(id=1, workspace_id=1, name="Main", cash_balance=10_000.0))
    import datetime as _dt

    oh = OptimizerHistory(
        id=1, workspace_id=1, portfolio_id=1, portfolio_name="Main",
        analyzed_at=_dt.datetime.utcnow(), swap_count=0, result_json="{}",
    )
    db.add(oh)
    db.commit()

    scores_map = {
        "AOT": {"symbol": "AOT", "signal": "BUY", "current_price": 32.5},
        "ZZZ": {"symbol": "ZZZ", "signal": "HOLD", "current_price": 10.0},
    }
    enriched = enrich_scores_map_for_snapshot(db, scores_map)

    snap_id = write_recommendation_snapshot(
        db,
        workspace_id=1,
        portfolio_id=1,
        optimizer_history_id=oh.id,
        optimizer_result={"target_allocations": []},
        scores_map=enriched,
    )

    assert snap_id is not None
    snap = db.query(RecommendationSnapshot).filter_by(id=snap_id).first()
    persisted = json.loads(snap.scores_map_json)

    # Original fields survive untouched; only the additive "registry" key
    # is new.
    assert persisted["AOT"]["symbol"] == "AOT"
    assert persisted["AOT"]["signal"] == "BUY"
    assert persisted["AOT"]["current_price"] == 32.5
    assert persisted["AOT"]["registry"]["resolved"] is True
    assert persisted["ZZZ"]["registry"]["resolved"] is False
