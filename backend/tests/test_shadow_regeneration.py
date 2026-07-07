"""Tests for Accounting Correctness Milestone 2 — historical regeneration and
replay validation (docs/DECISION_LOG.md, "Historical Regeneration + Replay
Validation Engine").

Milestone 1 fixed the shared replay functions (_resolve_shares_from_weights,
assert_nav_conserved) so *future* rebalances stop leaking cash, but left
already-persisted ShadowPortfolio.paper_cash_balance values and
ShadowPortfolioSnapshot rows untouched. This file covers the regeneration
engine that re-derives those rows through the corrected engine, plus the
reusable replay-determinism helper.

Coverage
--------
verify_deterministic_replay (unit, no DB)
  1. A pure, stable function passes and returns its result.
  2. A function whose output changes between calls raises
     ReplayNonDeterministicError.

regenerate_static_shadow (DB-backed)
  3. Restores the correct paper_cash_balance for a shadow whose cash was
     never computed (simulates a pre-Milestone-1 row: paper_cash_balance=0.0
     despite partial-weight holdings) and rewrites its snapshot history so
     every day conserves NAV.
  4. dry_run=True computes the correct value but leaves the database
     unchanged (rollback, not commit).
  5. Regeneration is idempotent — running it twice produces identical cash
     and an unchanged ShadowPortfolioSnapshot row count (no duplicates).

regenerate_active_model_shadow / _replay_active_model_series (DB-backed)
  6. Replays a full multi-day, multi-rebalance history (95% -> 97% -> full
     liquidation, mirroring Milestone 1's own regression fixture) from a
     shadow whose paper_cash_balance was never tracked, and conserves NAV
     on every regenerated day.
  7. The pure replay component is deterministic under verify_deterministic_replay.
  8. Regeneration is idempotent — a second run produces identical snapshot
     values and does not duplicate rows.
  8b. holdings_json is refreshed on an already-existing row, not left
      stale — Accounting Correctness C5, Issue A regression.

regenerate_portfolio_paper_history (DB-backed, orchestration)
  9. Regenerates both a recommendation-keyed STATIC_FROZEN shadow and the
     ACTIVE_MODEL shadow for the same portfolio, with zero errors and no
     shadow rows created or deleted (identity preserved).

compute_ideal_series (DB-backed) — Ideal Portfolio replay determinism
  10. Two independent calls with identical inputs produce identical series,
      verified via verify_deterministic_replay (this is the "Ideal Portfolio"
      half of Milestone 2's determinism requirement; ACTIVE_MODEL's half is
      covered by test 7 above).
"""
from __future__ import annotations

import json
import sys
import os
from datetime import date, datetime, timedelta

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.decision_memory.shadow_tracker import (  # noqa: E402
    verify_deterministic_replay,
    ReplayNonDeterministicError,
    regenerate_static_shadow,
    regenerate_active_model_shadow,
    regenerate_portfolio_paper_history,
    _replay_active_model_series,
    _resolve_shares_from_weights,
)


# ─── verify_deterministic_replay (unit, no DB) ─────────────────────────────

def test_verify_deterministic_replay_passes_for_stable_function():
    def stable(x):
        return {"a": x * 2, "b": [1.0, 2.0, {"c": x}]}

    result = verify_deterministic_replay(stable, 5)
    assert result["deterministic"] is True
    assert result["result"] == {"a": 10, "b": [1.0, 2.0, {"c": 5}]}


def test_verify_deterministic_replay_raises_on_divergence():
    calls = {"n": 0}

    def unstable():
        calls["n"] += 1
        return {"value": calls["n"]}  # different every call

    with pytest.raises(ReplayNonDeterministicError):
        verify_deterministic_replay(unstable)


def test_verify_deterministic_replay_tolerates_floating_point_noise():
    def almost_stable():
        return {"value": 100.0 + 1e-9}

    result = verify_deterministic_replay(almost_stable, tolerance=1e-6)
    assert result["deterministic"] is True


# ─── DB-backed fixtures (mirrors test_shadow_tracker_cash_accounting.py) ───

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


def _seed_recommendation(db, ws, portfolio, allocations, total_portfolio_value=1_000_000.0, days_ago=0):
    from models.database import OptimizerHistory, RecommendationSnapshot

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
        total_portfolio_value=total_portfolio_value,
        projected_allocations_json=json.dumps(allocations),
        created_at=datetime.utcnow() - timedelta(days=days_ago),
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return snap


def _seed_price_snapshot(db, ws, portfolio, prices: dict, days_ago=0):
    from models.database import PortfolioSnapshot

    holdings = [{"symbol": sym, "current_price": p} for sym, p in prices.items()]
    db.add(PortfolioSnapshot(
        workspace_id=ws.id, portfolio_id=portfolio.id,
        snapshot_date=(date.today() - timedelta(days=days_ago)).isoformat(),
        total_value=1_000_000.0, cash_balance=0.0,
        holdings_json=json.dumps(holdings),
    ))
    db.commit()


_ALLOCS_95PCT = [
    {"symbol": "AAA", "target_weight": 50.0, "action": "BUY"},
    {"symbol": "BBB", "target_weight": 45.0, "action": "BUY"},
]
_ALLOCS_97PCT = [
    {"symbol": "AAA", "target_weight": 50.0, "action": "HOLD"},
    {"symbol": "BBB", "target_weight": 47.0, "action": "BUY"},
]
_ALLOCS_93PCT = [
    {"symbol": "AAA", "target_weight": 50.0, "action": "HOLD"},
    {"symbol": "BBB", "target_weight": 43.0, "action": "SELL"},
]
_ALLOCS_FULL_LIQUIDATION: list[dict] = []


# ─── regenerate_static_shadow ──────────────────────────────────────────────

def _make_pre_fix_static_shadow(db, ws, portfolio, snap):
    """Directly construct a ShadowPortfolio row simulating pre-Milestone-1
    data: real holdings at partial weights, but paper_cash_balance hardcoded
    to 0.0 (the historical bug) instead of the correct residual.
    """
    from models.database import ShadowPortfolio

    prices = {"AAA": 100.0, "BBB": 100.0}
    holdings, _dropped_cash = _resolve_shares_from_weights(_ALLOCS_95PCT, 1_000_000.0, prices)

    shadow = ShadowPortfolio(
        workspace_id=ws.id, portfolio_id=portfolio.id, shadow_type="STATIC_FROZEN",
        name="Pre-fix recommendation shadow",
        inception_date=date.today().isoformat(), inception_value=1_000_000.0,
        recommendation_snapshot_id=snap.id, execution_decision_id=None,
        inception_holdings_json=json.dumps(holdings),
        paper_cash_balance=0.0,  # the bug: never computed
        is_active=True, created_at=datetime.utcnow(),
    )
    db.add(shadow)
    db.commit()
    db.refresh(shadow)
    return shadow


def test_regenerate_static_shadow_restores_correct_cash(db, ws_portfolio):
    from models.database import ShadowPortfolio, ShadowPortfolioSnapshot

    ws, portfolio = ws_portfolio
    _seed_price_snapshot(db, ws, portfolio, {"AAA": 100.0, "BBB": 100.0})
    snap = _seed_recommendation(db, ws, portfolio, _ALLOCS_95PCT)
    shadow = _make_pre_fix_static_shadow(db, ws, portfolio, snap)

    assert shadow.paper_cash_balance == 0.0  # pre-fix state confirmed

    result = regenerate_static_shadow(db, shadow.id)
    assert result["status"] == "regenerated"
    assert result["new_cash"] == pytest.approx(50_000.0)

    db.refresh(shadow)
    assert shadow.paper_cash_balance == pytest.approx(50_000.0)

    snaps = db.query(ShadowPortfolioSnapshot).filter_by(shadow_portfolio_id=shadow.id).all()
    assert len(snaps) >= 1
    for s in snaps:
        assert s.total_value == pytest.approx(1_000_000.0, abs=1.0)


def test_regenerate_static_shadow_dry_run_leaves_db_unchanged(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    _seed_price_snapshot(db, ws, portfolio, {"AAA": 100.0, "BBB": 100.0})
    snap = _seed_recommendation(db, ws, portfolio, _ALLOCS_95PCT)
    shadow = _make_pre_fix_static_shadow(db, ws, portfolio, snap)

    result = regenerate_static_shadow(db, shadow.id, dry_run=True)
    assert result["dry_run"] is True
    assert result["new_cash"] == pytest.approx(50_000.0)  # computed correctly...

    db.refresh(shadow)
    assert shadow.paper_cash_balance == 0.0  # ...but never committed


def test_regenerate_static_shadow_is_idempotent(db, ws_portfolio):
    from models.database import ShadowPortfolioSnapshot

    ws, portfolio = ws_portfolio
    _seed_price_snapshot(db, ws, portfolio, {"AAA": 100.0, "BBB": 100.0})
    snap = _seed_recommendation(db, ws, portfolio, _ALLOCS_95PCT)
    shadow = _make_pre_fix_static_shadow(db, ws, portfolio, snap)

    r1 = regenerate_static_shadow(db, shadow.id)
    count1 = db.query(ShadowPortfolioSnapshot).filter_by(shadow_portfolio_id=shadow.id).count()

    r2 = regenerate_static_shadow(db, shadow.id)
    count2 = db.query(ShadowPortfolioSnapshot).filter_by(shadow_portfolio_id=shadow.id).count()

    assert r1["new_cash"] == pytest.approx(r2["new_cash"])
    assert count1 == count2  # no duplicate snapshot rows


# ─── regenerate_active_model_shadow / _replay_active_model_series ─────────

def _make_pre_fix_active_model_shadow(db, ws, portfolio, seed_snap, inception_date):
    """Directly construct an ACTIVE_MODEL ShadowPortfolio row with
    inception_date backdated (simulating a shadow created days ago) and
    paper_cash_balance never tracked (the pre-Milestone-1 bug).
    """
    from models.database import ShadowPortfolio

    shadow = ShadowPortfolio(
        workspace_id=ws.id, portfolio_id=portfolio.id, shadow_type="ACTIVE_MODEL",
        name="Pre-fix active model shadow",
        inception_date=inception_date, inception_value=1_000_000.0,
        recommendation_snapshot_id=seed_snap.id,
        inception_holdings_json=json.dumps([]),
        paper_cash_balance=0.0,  # the bug: never computed
        is_active=True, created_at=datetime.utcnow(),
    )
    db.add(shadow)
    db.commit()
    db.refresh(shadow)
    return shadow


def _seed_three_day_rebalance_history(db, ws, portfolio):
    """Seed 3 days of flat prices + 3 RecommendationSnapshots (95% -> 97% ->
    93%), a multi-rebalance history over consecutive calendar days.

    Uses non-empty allocations at every rebalance point. Full liquidation
    (an empty target_allocations list) is deliberately NOT used here: the
    history-scanning replay this function feeds (_replay_active_model_series,
    mirroring ideal_series.py's pre-existing _snapshots_for_window pattern)
    filters out snapshots with `if not allocs: continue` — an empty list is
    indistinguishable from "no usable data" under that filter, so a literal
    liquidation event is currently unrepresentable via history scanning (see
    test_liquidation_snapshot_is_skipped_not_misapplied below, and the
    Milestone 2 carried-forward design note in docs/DECISION_LOG.md). This
    is a pre-existing characteristic shared with the already-shipped Ideal
    Portfolio replay, not something Milestone 2 introduces or is scoped to
    fix (methodology changes are explicitly out of scope).
    """
    for days_ago in (2, 1, 0):
        _seed_price_snapshot(db, ws, portfolio, {"AAA": 100.0, "BBB": 100.0}, days_ago=days_ago)

    snap1 = _seed_recommendation(db, ws, portfolio, _ALLOCS_95PCT, days_ago=2)
    _seed_recommendation(db, ws, portfolio, _ALLOCS_97PCT, days_ago=1)
    _seed_recommendation(db, ws, portfolio, _ALLOCS_93PCT, days_ago=0)

    inception_date = (date.today() - timedelta(days=2)).isoformat()
    return snap1, inception_date


def test_regenerate_active_model_shadow_replays_multi_day_rebalance_history(db, ws_portfolio):
    from models.database import ShadowPortfolioSnapshot

    ws, portfolio = ws_portfolio
    seed_snap, inception_date = _seed_three_day_rebalance_history(db, ws, portfolio)
    shadow = _make_pre_fix_active_model_shadow(db, ws, portfolio, seed_snap, inception_date)

    result = regenerate_active_model_shadow(db, portfolio.id)
    assert result["status"] == "regenerated"
    assert result["rebalances_replayed"] == 2  # snap2 (97%), snap3 (93%)
    assert result["snapshots_written"] == 3    # one row per day: -2, -1, today
    # 93% deployed at the end -> 7% of NAV is cash.
    assert result["final_cash"] == pytest.approx(70_000.0, abs=1.0)

    db.refresh(shadow)
    assert len(json.loads(shadow.inception_holdings_json)) == 2
    assert shadow.paper_cash_balance == pytest.approx(70_000.0, abs=1.0)

    snaps = (
        db.query(ShadowPortfolioSnapshot)
        .filter_by(shadow_portfolio_id=shadow.id)
        .order_by(ShadowPortfolioSnapshot.snapshot_date)
        .all()
    )
    assert len(snaps) == 3
    # NAV conserved on every single regenerated day, across every rebalance —
    # the direct Milestone 2 regression test (no price movement, so every
    # day must equal the original inception NAV exactly).
    for s in snaps:
        assert s.total_value == pytest.approx(1_000_000.0, abs=1.0)


def test_liquidation_snapshot_is_skipped_not_misapplied(db, ws_portfolio):
    """Documents a discovered, pre-existing edge case shared with
    ideal_series.py's identical _snapshots_for_window filter: a literal full
    liquidation (empty target_allocations) is indistinguishable from "no
    usable data" under `if not allocs: continue`, so history-scanning replay
    treats it as though the recommendation never existed rather than as a
    liquidation event. This asserts the SAFE side of that gap — the
    snapshot is silently skipped, not misapplied as a phantom rebalance —
    and is not a Milestone 2 regression (methodology changes are out of
    scope; see docs/DECISION_LOG.md for the carried-forward design note).
    """
    ws, portfolio = ws_portfolio
    for days_ago in (1, 0):
        _seed_price_snapshot(db, ws, portfolio, {"AAA": 100.0, "BBB": 100.0}, days_ago=days_ago)
    seed_snap = _seed_recommendation(db, ws, portfolio, _ALLOCS_95PCT, days_ago=1)
    _seed_recommendation(db, ws, portfolio, _ALLOCS_FULL_LIQUIDATION, days_ago=0)

    inception_date = (date.today() - timedelta(days=1)).isoformat()
    shadow = _make_pre_fix_active_model_shadow(db, ws, portfolio, seed_snap, inception_date)

    result = regenerate_active_model_shadow(db, portfolio.id)
    assert result["status"] == "regenerated"
    assert result["rebalances_replayed"] == 0  # the liquidation row was skipped, not applied
    assert result["final_cash"] == pytest.approx(50_000.0, abs=1.0)  # still the 95% seed state


def test_replay_active_model_series_is_deterministic(db, ws_portfolio):
    from models.database import ShadowPortfolio

    ws, portfolio = ws_portfolio
    seed_snap, inception_date = _seed_three_day_rebalance_history(db, ws, portfolio)
    shadow = _make_pre_fix_active_model_shadow(db, ws, portfolio, seed_snap, inception_date)

    # Re-fetch fresh so the pure function reads consistent, committed state.
    shadow = db.query(ShadowPortfolio).filter_by(id=shadow.id).first()

    result = verify_deterministic_replay(_replay_active_model_series, db, portfolio.id, shadow)
    assert result["deterministic"] is True
    assert result["result"]["status"] == "ok"
    assert result["result"]["final_cash"] == pytest.approx(70_000.0, abs=1.0)


def test_regenerate_active_model_shadow_is_idempotent(db, ws_portfolio):
    from models.database import ShadowPortfolioSnapshot

    ws, portfolio = ws_portfolio
    seed_snap, inception_date = _seed_three_day_rebalance_history(db, ws, portfolio)
    shadow = _make_pre_fix_active_model_shadow(db, ws, portfolio, seed_snap, inception_date)

    r1 = regenerate_active_model_shadow(db, portfolio.id)
    rows1 = {
        s.snapshot_date: s.total_value
        for s in db.query(ShadowPortfolioSnapshot).filter_by(shadow_portfolio_id=shadow.id).all()
    }

    r2 = regenerate_active_model_shadow(db, portfolio.id)
    rows2 = {
        s.snapshot_date: s.total_value
        for s in db.query(ShadowPortfolioSnapshot).filter_by(shadow_portfolio_id=shadow.id).all()
    }

    assert r1["snapshots_written"] == r2["snapshots_written"]
    assert set(rows1.keys()) == set(rows2.keys())  # no duplicate/dropped dates
    for d in rows1:
        assert rows1[d] == pytest.approx(rows2[d], abs=1e-6)


def test_regenerate_active_model_shadow_dry_run_leaves_db_unchanged(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    seed_snap, inception_date = _seed_three_day_rebalance_history(db, ws, portfolio)
    shadow = _make_pre_fix_active_model_shadow(db, ws, portfolio, seed_snap, inception_date)

    result = regenerate_active_model_shadow(db, portfolio.id, dry_run=True)
    assert result["dry_run"] is True
    assert result["final_cash"] == pytest.approx(70_000.0, abs=1.0)

    db.refresh(shadow)
    assert shadow.paper_cash_balance == 0.0  # never committed
    assert json.loads(shadow.inception_holdings_json) == []  # still the placeholder seeded above


# ─── regenerate_portfolio_paper_history (orchestration) ────────────────────

def test_regenerate_active_model_shadow_refreshes_holdings_json_on_existing_row(db, ws_portfolio):
    """Issue A regression (Accounting Correctness C5): regenerate_active_model_shadow
    previously updated total_value/return_pct_since_inception/daily_return_pct
    on an already-existing ShadowPortfolioSnapshot row but left holdings_json
    untouched — e.g. whatever the live daily-valuation scheduler had written
    before regeneration ran. This simulates exactly that pre-existing row
    (stale holdings, stale total_value) and asserts regeneration overwrites
    holdings_json too, so it describes the same state as the corrected
    total_value rather than a leftover composition from before the fix.
    """
    from models.database import ShadowPortfolioSnapshot

    ws, portfolio = ws_portfolio
    seed_snap, inception_date = _seed_three_day_rebalance_history(db, ws, portfolio)
    shadow = _make_pre_fix_active_model_shadow(db, ws, portfolio, seed_snap, inception_date)

    # A pre-existing row at the seed date, as the live scheduler would have
    # written before regeneration — one stale leftover holding, wrong total_value.
    stale_holdings = [{
        "symbol": "AAA", "shares": 1.0, "inception_price": 100.0,
        "price_frozen": False, "current_price": 100.0, "market_value": 100.0,
    }]
    db.add(ShadowPortfolioSnapshot(
        shadow_portfolio_id=shadow.id,
        snapshot_date=inception_date,
        total_value=999.0,
        holdings_json=json.dumps(stale_holdings),
        benchmark_symbol="^GSPC",
        created_at=datetime.utcnow(),
    ))
    db.commit()

    result = regenerate_active_model_shadow(db, portfolio.id)
    assert result["status"] == "regenerated"

    refreshed = (
        db.query(ShadowPortfolioSnapshot)
        .filter_by(shadow_portfolio_id=shadow.id, snapshot_date=inception_date)
        .one()
    )
    assert refreshed.total_value == pytest.approx(1_000_000.0, abs=1.0)

    refreshed_holdings = json.loads(refreshed.holdings_json)
    # No longer the stale single-holding placeholder — matches the 95% seed
    # allocation (AAA + BBB), the same state total_value now reflects.
    assert {h["symbol"] for h in refreshed_holdings} == {"AAA", "BBB"}

    # holdings_json and total_value must describe one consistent state: the
    # equity recorded in holdings_json plus the 5%-cash residual for a
    # 95%-deployed seed reconstructs total_value exactly.
    equity_from_holdings_json = sum(h["market_value"] for h in refreshed_holdings)
    assert equity_from_holdings_json + 50_000.0 == pytest.approx(1_000_000.0, abs=1.0)


def test_regenerate_portfolio_paper_history_regenerates_both_shadow_types(db, ws_portfolio):
    from models.database import ShadowPortfolio

    ws, portfolio = ws_portfolio
    seed_snap, inception_date = _seed_three_day_rebalance_history(db, ws, portfolio)
    _make_pre_fix_active_model_shadow(db, ws, portfolio, seed_snap, inception_date)
    _make_pre_fix_static_shadow(db, ws, portfolio, seed_snap)

    before_count = db.query(ShadowPortfolio).filter_by(portfolio_id=portfolio.id).count()

    result = regenerate_portfolio_paper_history(db, portfolio.id, ws.id)

    assert result["errors"] == []
    assert len(result["static_shadows"]) == 1
    assert result["static_shadows"][0]["status"] == "regenerated"
    assert result["active_model"]["status"] == "regenerated"

    after_count = db.query(ShadowPortfolio).filter_by(portfolio_id=portfolio.id).count()
    assert after_count == before_count  # identity preserved — no rows created/deleted


# ─── compute_ideal_series replay determinism (Milestone 2 acceptance) ─────

def test_compute_ideal_series_replay_is_deterministic(db, ws_portfolio):
    from services.evaluation.ideal_series import compute_ideal_series

    ws, portfolio = ws_portfolio
    for days_ago in (2, 1, 0):
        _seed_price_snapshot(db, ws, portfolio, {"AAA": 100.0, "BBB": 100.0}, days_ago=days_ago)
    _seed_recommendation(db, ws, portfolio, _ALLOCS_95PCT, days_ago=2)
    _seed_recommendation(db, ws, portfolio, _ALLOCS_97PCT, days_ago=1)

    result = verify_deterministic_replay(compute_ideal_series, db, portfolio.id, 5)
    assert result["deterministic"] is True
    assert result["result"]["status"] == "ok"
