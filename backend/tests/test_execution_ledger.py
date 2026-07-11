"""Tests for services/evaluation/execution_ledger.py — AI Evaluation M3.

Coverage
--------
list_execution_ledger
  1. Cold start (no decisions in window) -> status="cold_start", zero rows
  2. APPROVED decision with a linked transaction -> row present, class-
     segmented acceptance counts the plan's Reason(s)
  3. REJECTED decision -> counted in decision_counts, excluded from
     acceptance numerator but included in the class denominator
  4. Acceptance note always present (documents the snapshot-level
     approximation, never silently precise)

get_execution_detail
  5. Unknown decision_id -> None (caller 404s)
  6. Decision with no linked transactions -> analysis.status="unavailable",
     partial_warning is None (unavailable is not the same as partial)
  7. Decision with a linked transaction covering only some of the plan ->
     partial_warning is a non-empty string

Registry-aware symbol matching (M6 Phase 4 — plan-vs-live-Transaction join)
  8. A linked Transaction recorded under a .BK-variant spelling of the plan
     symbol (no Registry data minted at all) now links via the legacy
     bare/.BK fallback inside match_known_symbols() instead of reading as
     unmatched.
  9. A genuine Registry conflict (two distinct minted assets, one per
     spelling) must never be silently unified — the transaction stays
     unmatched, exactly as before this change.
  10. Two symbols with no relationship at all (not a .BK variant, not a
      Registry match) remain unmatched — regression safety for the
      unresolved-symbol population.
"""
from __future__ import annotations

import json
import sys
import os
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import models.asset  # noqa: F401 — registers Asset* tables on Base.metadata
import models.registry_finding  # noqa: F401 — registers RegistryFinding table

from services.evaluation.execution_ledger import (  # noqa: E402
    get_execution_detail,
    list_execution_ledger,
)
from services import registry_lookup as lookup  # noqa: E402


@pytest.fixture()
def db():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models.database import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(autouse=True)
def _reset_registry_cache():
    lookup.invalidate_cache()
    yield
    lookup.invalidate_cache()


@pytest.fixture()
def ws_portfolio(db):
    from models.database import Workspace, Portfolio

    ws = Workspace(name="Test")
    db.add(ws)
    db.commit()
    db.refresh(ws)

    portfolio = Portfolio(workspace_id=ws.id, name="P1", cash_balance=100_000.0)
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    return ws, portfolio


def _mint_asset(db, canonical_symbol: str, provider_symbol: str | None = None):
    from services import registry_service as svc
    from services.asset_domain import AssetClaim, AssetType, IdentifierRecord, IdentifierType

    claim = AssetClaim(
        canonical_symbol=canonical_symbol, asset_type=AssetType.EQUITY,
        market="Thailand", exchange="SET", currency="THB",
    )
    identifier = IdentifierRecord(
        identifier_type=IdentifierType.PROVIDER_SYMBOL,
        value=provider_symbol or canonical_symbol, source="test",
    )
    return svc.mint_asset(db, claim, identifiers=[identifier])


def _seed_snapshot_and_decision(
    db, ws, portfolio, decision_type, allocations, with_transaction=False, tx_symbol=None,
):
    from models.database import OptimizerHistory, RecommendationSnapshot, Transaction, UserExecutionDecision

    oh = OptimizerHistory(
        workspace_id=ws.id, portfolio_id=portfolio.id, portfolio_name=portfolio.name,
        analyzed_at=datetime.utcnow(), swap_count=0,
        result_json=json.dumps({"target_allocations": allocations, "cash_balance": 0.0}),
    )
    db.add(oh)
    db.commit()
    db.refresh(oh)

    snap = RecommendationSnapshot(
        workspace_id=ws.id, optimizer_history_id=oh.id, portfolio_id=portfolio.id,
        total_portfolio_value=1_000_000.0,
        projected_allocations_json=json.dumps(allocations),
        active_policy_json=json.dumps({"violations": []}),
        scores_map_json=json.dumps({"CENTEL": {"current_price": 100.0}}),
        created_at=datetime.utcnow(),
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)

    dec = UserExecutionDecision(
        workspace_id=ws.id, recommendation_snapshot_id=snap.id, portfolio_id=portfolio.id,
        decision=decision_type, executed_at=datetime.utcnow(), created_at=datetime.utcnow(),
    )
    db.add(dec)
    db.commit()
    db.refresh(dec)

    if with_transaction:
        db.add(Transaction(
            workspace_id=ws.id, portfolio_id=portfolio.id,
            symbol=tx_symbol or allocations[0]["symbol"],
            transaction_type="BUY", shares=300, price_per_share=100.0, total_amount=30_000,
            transaction_date=datetime.utcnow(), execution_decision_id=dec.id,
        ))
        db.commit()

    return snap, dec


_ALLOCS_BUY_ONLY = [
    {"symbol": "CENTEL", "action": "BUY", "allocation_change_percent": 3.0,
     "current_weight": 0.0, "estimated_amount": 30_000, "sector": "Consumer"},
]

# Gap = 30k funded by a discretionary REDUCE of exactly 30k (Portfolio Improvement).
_ALLOCS_WITH_FUNDING = _ALLOCS_BUY_ONLY + [
    {"symbol": "XYZ", "action": "REDUCE", "allocation_change_percent": -3.0,
     "current_weight": 10.0, "estimated_amount": 30_000, "sector": "Healthcare"},
]


def test_cold_start_execution_ledger(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    result = list_execution_ledger(db, portfolio.id)
    assert result["status"] == "cold_start"
    assert result["rows"] == []
    assert result["summary"]["total_decisions"] == 0


def test_approved_decision_with_transaction_is_scored(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    _seed_snapshot_and_decision(db, ws, portfolio, "APPROVED", _ALLOCS_WITH_FUNDING, with_transaction=True)

    result = list_execution_ledger(db, portfolio.id)
    assert result["status"] == "ok"
    assert result["summary"]["decision_counts"]["APPROVED"] == 1
    row = result["rows"][0]
    assert row["decision"] == "APPROVED"
    # Portfolio Improvement is the Reason for the XYZ REDUCE candidate.
    acc = result["summary"]["acceptance_by_class"]["Portfolio Improvement"]
    assert acc["total"] == 1
    assert acc["accepted"] == 1
    assert "note" not in acc  # note lives at summary level, not per-class
    assert result["summary"]["acceptance_note"]


def test_rejected_decision_counted_but_not_accepted(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    _seed_snapshot_and_decision(db, ws, portfolio, "REJECTED", _ALLOCS_WITH_FUNDING, with_transaction=False)

    result = list_execution_ledger(db, portfolio.id)
    assert result["summary"]["decision_counts"]["REJECTED"] == 1
    acc = result["summary"]["acceptance_by_class"]["Portfolio Improvement"]
    assert acc["total"] == 1
    assert acc["accepted"] == 0
    assert acc["acceptance_pct"] == 0.0


def test_get_execution_detail_unknown_decision_returns_none(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    assert get_execution_detail(db, portfolio.id, decision_id=99999) is None


def test_execution_detail_no_transactions_is_unavailable_not_partial(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    _snap, dec = _seed_snapshot_and_decision(db, ws, portfolio, "APPROVED", _ALLOCS_BUY_ONLY, with_transaction=False)

    detail = get_execution_detail(db, portfolio.id, dec.id)
    assert detail["analysis"]["status"] == "unavailable"
    assert detail["partial_warning"] is None


def test_execution_detail_partial_execution_has_warning(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    allocations = _ALLOCS_BUY_ONLY + [
        {"symbol": "ADVANC", "action": "BUY", "allocation_change_percent": 2.0,
         "current_weight": 0.0, "estimated_amount": 20_000, "sector": "Telecom"},
    ]
    _snap, dec = _seed_snapshot_and_decision(db, ws, portfolio, "PARTIAL_EXECUTION", allocations, with_transaction=True)

    detail = get_execution_detail(db, portfolio.id, dec.id)
    assert detail["analysis"]["status"] == "partial"
    assert detail["partial_warning"]
    assert "Partial execution" in detail["partial_warning"]


# ── Registry-aware symbol matching (M6 Phase 4) ─────────────────────────────

_ALLOCS_BH_PLAN = [
    {"symbol": "BH", "action": "BUY", "allocation_change_percent": 3.0,
     "current_weight": 0.0, "estimated_amount": 30_000, "sector": "Healthcare"},
]


def test_bk_variant_spelling_links_via_legacy_fallback(db, ws_portfolio):
    """No Registry data minted at all: plan says "BH", the fill is recorded
    as "BH.BK". match_known_symbols()'s legacy bare/.BK heuristic must still
    link them — this is the exact correctness gap M6_REGISTRY_READ_PATH_
    INTEGRATION_PLAN.md §2.3 item 1 named, now fixed at the
    _linked_transactions boundary rather than inside the pure
    compute_execution_analysis."""
    ws, portfolio = ws_portfolio
    _snap, dec = _seed_snapshot_and_decision(
        db, ws, portfolio, "APPROVED", _ALLOCS_BH_PLAN, with_transaction=True, tx_symbol="BH.BK",
    )

    detail = get_execution_detail(db, portfolio.id, dec.id)
    # status is "partial" here regardless of the matching fix (no funding-
    # source trade in this plan => funding_fidelity_pct is N/A => is_partial),
    # exactly like test_fully_matched_exact_fill_scores_high in
    # test_execution_analyzer.py. What's under test is that the transaction
    # matched at all.
    assert detail["analysis"]["status"] in ("ok", "partial")
    assert detail["analysis"]["symbols"]["BH"]["executed_amount"] == 30_000.0
    assert detail["analysis"]["symbols"]["BH"]["note"] is None


def test_registry_conflict_never_silently_unified(db, ws_portfolio):
    """Two distinct minted assets, one per spelling ("BH" and "BH.BK") are a
    genuine Registry conflict, per ASSET_REGISTRY.md §5 (a DR/underlying-
    style relationship is never the same identity). match_known_symbols()
    must not paper over that verdict with the .BK heuristic — the linked
    transaction must remain unmatched, exactly as it would have before this
    change."""
    ws, portfolio = ws_portfolio
    _mint_asset(db, "BH", provider_symbol="BH")
    _mint_asset(db, "BH.BK", provider_symbol="BH.BK")

    _snap, dec = _seed_snapshot_and_decision(
        db, ws, portfolio, "APPROVED", _ALLOCS_BH_PLAN, with_transaction=True, tx_symbol="BH.BK",
    )

    detail = get_execution_detail(db, portfolio.id, dec.id)
    # linked_transactions is non-empty (a Transaction row exists) but it must
    # not be matched to the plan's "BH" — the Registry's conflict verdict
    # wins over the .BK heuristic, so this reads as an unmatched trade
    # ("partial", not a false "ok").
    assert detail["analysis"]["status"] == "partial"
    assert detail["analysis"]["symbols"]["BH"]["note"] == "no_linked_transaction"


def test_native_asset_id_links_transaction_with_no_bk_relationship(db, ws_portfolio):
    """M6 Native Integration (M5_TRACK_B_NATIVE_INTEGRATION_TDD.md §7 Stage 5):
    Transaction.asset_id is materialized directly (simulating a Stage 2
    backfill) and links to the plan's "BH" through a fill recorded under a
    spelling ("BHNEWNAME") that has no `.BK` relationship at all — the
    legacy heuristic could never produce this match. A passing result here
    can only come from the native asset_id join."""
    ws, portfolio = ws_portfolio
    asset = _mint_asset(db, "BH", provider_symbol="BH")

    _snap, dec = _seed_snapshot_and_decision(
        db, ws, portfolio, "APPROVED", _ALLOCS_BH_PLAN, with_transaction=True, tx_symbol="BHNEWNAME",
    )
    from models.database import Transaction
    tx = db.query(Transaction).filter_by(execution_decision_id=dec.id).first()
    tx.asset_id = int(asset.id)
    db.commit()

    detail = get_execution_detail(db, portfolio.id, dec.id)
    assert detail["analysis"]["symbols"]["BH"]["executed_amount"] == 30_000.0
    assert detail["analysis"]["symbols"]["BH"]["note"] is None


def test_unrelated_symbols_stay_unmatched(db, ws_portfolio):
    """A transaction recorded under a wholly unrelated symbol (not a .BK
    variant, no Registry data at all) must not be linked — regression
    safety for the unresolved-symbol population this change must leave
    untouched."""
    ws, portfolio = ws_portfolio
    _snap, dec = _seed_snapshot_and_decision(
        db, ws, portfolio, "APPROVED", _ALLOCS_BUY_ONLY, with_transaction=True, tx_symbol="ADVANC",
    )

    detail = get_execution_detail(db, portfolio.id, dec.id)
    assert detail["analysis"]["status"] == "partial"
    assert detail["analysis"]["symbols"]["CENTEL"]["note"] == "no_linked_transaction"
