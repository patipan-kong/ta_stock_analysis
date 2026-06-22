"""Unit tests for Phase 4C.6A — Allocation Period Engine.

All tests use an in-memory SQLite database; no network calls.

Coverage:
  1. Single snapshot → one current period
  2. Multiple snapshots → correct period count and ordering
  3. Current active period has end_date=None and is_current=True
  4. days_active calculation is correct
  5. Periods are sorted ascending by start_date
  6. Workspace isolation — other workspace's snapshots are excluded
  7. No overlapping periods
"""

import sys
import os
from datetime import datetime, timezone, timedelta

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base, Workspace, Portfolio, OptimizerHistory, RecommendationSnapshot
from services.timing_periods import build_allocation_periods


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _seed_workspace(db) -> tuple:
    """Create a workspace and portfolio, return (workspace_id, portfolio_id)."""
    ws = Workspace(name="TestWS")
    db.add(ws)
    db.flush()
    p = Portfolio(workspace_id=ws.id, name="TestPortfolio", cash_balance=100_000.0)
    db.add(p)
    db.commit()
    return ws.id, p.id


def _add_snapshot(db, workspace_id: int, portfolio_id: int, created_at: datetime) -> RecommendationSnapshot:
    # RecommendationSnapshot requires a linked OptimizerHistory row (NOT NULL + UNIQUE FK).
    oh = OptimizerHistory(
        workspace_id=workspace_id,
        portfolio_id=portfolio_id,
        portfolio_name="Test",
        analyzed_at=created_at,
        swap_count=0,
        result_json="{}",
    )
    db.add(oh)
    db.flush()
    snap = RecommendationSnapshot(
        workspace_id=workspace_id,
        portfolio_id=portfolio_id,
        optimizer_history_id=oh.id,
        created_at=created_at,
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return snap


def _dt(days_ago: int = 0) -> datetime:
    """Return a naive UTC datetime N days before now."""
    return datetime.utcnow().replace(microsecond=0) - timedelta(days=days_ago)


# ── Test 1: Single snapshot ────────────────────────────────────────────────────

def test_single_snapshot_produces_one_current_period():
    db = make_session()
    ws_id, p_id = _seed_workspace(db)
    _add_snapshot(db, ws_id, p_id, _dt(5))

    periods = build_allocation_periods(p_id, ws_id, db)

    assert len(periods) == 1
    period = periods[0]
    assert period.is_current is True
    assert period.end_date is None
    assert period.days_active >= 1


# ── Test 2: Multiple snapshots → correct count and ascending order ─────────────

def test_multiple_snapshots_correct_count():
    db = make_session()
    ws_id, p_id = _seed_workspace(db)

    _add_snapshot(db, ws_id, p_id, _dt(20))
    _add_snapshot(db, ws_id, p_id, _dt(10))
    _add_snapshot(db, ws_id, p_id, _dt(3))

    periods = build_allocation_periods(p_id, ws_id, db)

    assert len(periods) == 3


# ── Test 3: Current active period semantics ────────────────────────────────────

def test_current_period_is_last_and_open_ended():
    db = make_session()
    ws_id, p_id = _seed_workspace(db)

    _add_snapshot(db, ws_id, p_id, _dt(15))
    _add_snapshot(db, ws_id, p_id, _dt(7))

    periods = build_allocation_periods(p_id, ws_id, db)

    current = periods[-1]
    assert current.is_current is True
    assert current.end_date is None

    for p in periods[:-1]:
        assert p.is_current is False
        assert p.end_date is not None


# ── Test 4: days_active calculation ───────────────────────────────────────────

def test_days_active_calculation():
    db = make_session()
    ws_id, p_id = _seed_workspace(db)

    start_a = _dt(30)
    start_b = _dt(20)   # 10-day gap
    start_c = _dt(5)    # 15-day gap

    _add_snapshot(db, ws_id, p_id, start_a)
    _add_snapshot(db, ws_id, p_id, start_b)
    _add_snapshot(db, ws_id, p_id, start_c)

    periods = build_allocation_periods(p_id, ws_id, db)

    # Period A: 30-day ago → 20-day ago  ≈ 10 days
    assert periods[0].days_active == 10
    # Period B: 20-day ago → 5-day ago   ≈ 15 days
    assert periods[1].days_active == 15
    # Period C: 5-day ago → now           ≈ 5+ days
    assert periods[2].days_active >= 5


# ── Test 5: Sorted ascending ──────────────────────────────────────────────────

def test_periods_sorted_ascending():
    db = make_session()
    ws_id, p_id = _seed_workspace(db)

    # Insert out-of-order to confirm sorting is by created_at, not insert order
    _add_snapshot(db, ws_id, p_id, _dt(5))
    _add_snapshot(db, ws_id, p_id, _dt(30))
    _add_snapshot(db, ws_id, p_id, _dt(15))

    periods = build_allocation_periods(p_id, ws_id, db)

    start_dates = [p.start_date for p in periods]
    assert start_dates == sorted(start_dates)


# ── Test 6: Workspace isolation ───────────────────────────────────────────────

def test_workspace_isolation():
    db = make_session()
    ws_id, p_id = _seed_workspace(db)

    # Second workspace with its own portfolio and snapshots
    ws2 = Workspace(name="OtherWS")
    db.add(ws2)
    db.flush()
    p2 = Portfolio(workspace_id=ws2.id, name="OtherPortfolio", cash_balance=0.0)
    db.add(p2)
    db.commit()
    _add_snapshot(db, ws2.id, p2.id, _dt(10))
    _add_snapshot(db, ws2.id, p2.id, _dt(3))

    # Our workspace has 1 snapshot
    _add_snapshot(db, ws_id, p_id, _dt(7))

    periods = build_allocation_periods(p_id, ws_id, db)

    assert len(periods) == 1
    assert periods[0].recommendation_snapshot_id not in {
        s.id
        for s in db.query(RecommendationSnapshot)
        .filter_by(workspace_id=ws2.id)
        .all()
    }


# ── Test 7: No overlapping periods ───────────────────────────────────────────

def test_no_overlapping_periods():
    db = make_session()
    ws_id, p_id = _seed_workspace(db)

    _add_snapshot(db, ws_id, p_id, _dt(30))
    _add_snapshot(db, ws_id, p_id, _dt(20))
    _add_snapshot(db, ws_id, p_id, _dt(10))
    _add_snapshot(db, ws_id, p_id, _dt(2))

    periods = build_allocation_periods(p_id, ws_id, db)

    for i in range(len(periods) - 1):
        current = periods[i]
        nxt = periods[i + 1]
        # Closed period's end must equal (or not exceed) next period's start
        assert current.end_date is not None
        assert current.end_date <= nxt.start_date, (
            f"Period {i} ends at {current.end_date} which overlaps with "
            f"period {i+1} starting at {nxt.start_date}"
        )


# ── Test: Empty portfolio returns empty list ──────────────────────────────────

def test_empty_portfolio_returns_empty():
    db = make_session()
    ws_id, p_id = _seed_workspace(db)

    periods = build_allocation_periods(p_id, ws_id, db)

    assert periods == []
