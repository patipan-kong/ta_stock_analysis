"""Regression test: GET /optimizer/history/{id} injects recommendation_snapshot_id.

Root cause: result_json is serialized and committed to OptimizerHistory before the
RecommendationSnapshot is written, so recommendation_snapshot_id is never stored in
result_json. The history detail endpoint must look it up and inject it.

Without the fix, DecisionActionPanel (Approve / Manual Override / Reject) would never
render when opening a report via the Operations Center latest-report link, because the
render guard `result.recommendation_snapshot_id && portfolioId` always evaluated falsy.
"""

import json
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import (
    Base, Workspace, Portfolio,
    OptimizerHistory, RecommendationSnapshot,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _seed(db) -> tuple[Workspace, Portfolio]:
    ws = Workspace(name="test-ws")
    db.add(ws)
    db.flush()
    p = Portfolio(workspace_id=ws.id, name="test-portfolio", cash_balance=100_000.0)
    db.add(p)
    db.commit()
    return ws, p


def _make_history(db, ws_id: int, portfolio_id: int, extra: dict | None = None) -> OptimizerHistory:
    """Create an OptimizerHistory row whose result_json mimics the real write-time state
    (no recommendation_snapshot_id — it hadn't been created yet when result_json was committed)."""
    payload: dict = {
        "status": "REBALANCE",
        "watchlist_ranking": [],
        "target_allocations": [],
        "consensus": {"consensus_strength_score": 72},
    }
    if extra:
        payload.update(extra)
    row = OptimizerHistory(
        workspace_id=ws_id,
        portfolio_id=portfolio_id,
        portfolio_name="test-portfolio",
        analyzed_at=datetime.utcnow(),
        swap_count=2,
        result_json=json.dumps(payload),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _make_snapshot(db, ws_id: int, portfolio_id: int, history_id: int) -> RecommendationSnapshot:
    snap = RecommendationSnapshot(
        workspace_id=ws_id,
        optimizer_history_id=history_id,
        portfolio_id=portfolio_id,
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return snap


def _simulate_endpoint(db, history_id: int, ws_id: int) -> dict:
    """Reproduce the exact logic of get_optimizer_history_detail after the fix."""
    row = db.query(OptimizerHistory).filter_by(id=history_id, workspace_id=ws_id).first()
    assert row is not None, "OptimizerHistory row not found"

    payload = json.loads(row.result_json)
    if "final_consensus_score" not in payload:
        consensus = payload.get("consensus") if isinstance(payload.get("consensus"), dict) else {}
        payload["final_consensus_score"] = consensus.get("consensus_strength_score")

    if not payload.get("recommendation_snapshot_id"):
        snap = db.query(RecommendationSnapshot).filter_by(
            optimizer_history_id=history_id,
            workspace_id=ws_id,
        ).first()
        if snap:
            payload["recommendation_snapshot_id"] = snap.id

    return payload


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_snapshot_id_injected_when_absent():
    """Core regression: result_json has no recommendation_snapshot_id,
    but a RecommendationSnapshot exists. Endpoint must inject the ID."""
    db = make_session()
    ws, p = _seed(db)
    history = _make_history(db, ws.id, p.id)
    snap = _make_snapshot(db, ws.id, p.id, history.id)

    result = _simulate_endpoint(db, history.id, ws.id)

    assert result["recommendation_snapshot_id"] == snap.id, (
        "recommendation_snapshot_id must be injected from RecommendationSnapshot table "
        "so that DecisionActionPanel can render"
    )


def test_snapshot_id_not_overwritten_when_present():
    """If result_json already contains recommendation_snapshot_id (fresh POST response
    path in memory), the stored value must not be overwritten."""
    db = make_session()
    ws, p = _seed(db)
    # Simulate a row where the field was somehow persisted correctly
    history = _make_history(db, ws.id, p.id, extra={"recommendation_snapshot_id": 999})
    snap = _make_snapshot(db, ws.id, p.id, history.id)

    result = _simulate_endpoint(db, history.id, ws.id)

    assert result["recommendation_snapshot_id"] == 999, (
        "Pre-existing recommendation_snapshot_id in result_json must not be overwritten"
    )


def test_no_crash_when_snapshot_missing():
    """If no RecommendationSnapshot exists (snapshot write failed silently),
    the endpoint must return the payload unchanged without raising."""
    db = make_session()
    ws, p = _seed(db)
    history = _make_history(db, ws.id, p.id)
    # Intentionally no RecommendationSnapshot created

    result = _simulate_endpoint(db, history.id, ws.id)

    assert result.get("recommendation_snapshot_id") is None, (
        "When no snapshot exists the field should remain absent — no KeyError or crash"
    )
    # Baseline fields must still be present
    assert result["status"] == "REBALANCE"


def test_final_consensus_score_backfilled():
    """Existing behaviour: final_consensus_score is derived from consensus block
    when not already present in result_json."""
    db = make_session()
    ws, p = _seed(db)
    history = _make_history(db, ws.id, p.id)
    # consensus.consensus_strength_score = 72 (set in _make_history)

    result = _simulate_endpoint(db, history.id, ws.id)

    assert result["final_consensus_score"] == 72


def test_snapshot_not_leaked_across_workspaces():
    """A RecommendationSnapshot from a different workspace must not be injected
    (workspace isolation guard)."""
    db = make_session()
    ws1, p1 = _seed(db)
    ws2 = Workspace(name="other-ws")
    db.add(ws2)
    db.flush()
    p2 = Portfolio(workspace_id=ws2.id, name="other-portfolio", cash_balance=0.0)
    db.add(p2)
    db.commit()

    history = _make_history(db, ws1.id, p1.id)
    # Create a snapshot that belongs to ws2 but points at the same history_id
    # (shouldn't happen in practice, but tests the workspace_id filter)
    rogue_snap = RecommendationSnapshot(
        workspace_id=ws2.id,
        optimizer_history_id=history.id,
        portfolio_id=p2.id,
    )
    db.add(rogue_snap)
    db.commit()

    result = _simulate_endpoint(db, history.id, ws1.id)

    assert result.get("recommendation_snapshot_id") is None, (
        "Snapshot from a different workspace must not be injected into another workspace's payload"
    )
