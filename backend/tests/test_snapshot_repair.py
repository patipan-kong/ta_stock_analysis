"""Regression tests for the snapshot repair service.

Tests cover:
  1.  Successful repair — corrupted snapshot replaced with correct values
  2.  Repair aborted   — coverage < 90%, original preserved
  3.  Dry run          — no DB writes despite valid prices
  4.  Corruption detection — price==cost indicator
  5.  Corruption detection — zero unrealized P&L indicator
  6.  Corruption detection — NAV discontinuity indicator
  7.  Snapshot replacement — repaired value persisted in database
  8.  Audit log            — RepairResult fields populated correctly
  9.  repair_snapshot() by ID
  10. repair_snapshots() date-range batch
  11. Clean snapshot is idempotent (repair produces the same value)
  12. detect returns empty list for clean portfolio

Refactor-specific tests (snapshot-only approach):
  13. Sold position included from holdings_json — NOT from PortfolioItem
  14. investment_return_pct / daily_return_pct left unchanged after repair
  15. DR symbol NOT normalized — NVDA01.BK passed to yfinance unchanged
  16. snapshot.cash_balance used instead of portfolio.cash_balance
  17. before_after comparison populated in RepairResult

Timezone regression tests:
  18-22. _closing_price_on_or_before handles UTC-aware / tz-naive indexes
"""
import sys
import os
import json
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import (
    Base, Portfolio, PortfolioItem, PortfolioSnapshot, Workspace,
)
from services.snapshot_repair import (
    CorruptionConfidence,
    CorruptionReason,
    RepairStatus,
    _closing_price_on_or_before,
    detect_corrupted_snapshots,
    repair_snapshot,
    repair_snapshot_by_date,
    repair_snapshots,
)


# ── DB / seed helpers ──────────────────────────────────────────────────────────

def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _seed(db, cash: float = 0.0):
    ws = Workspace(name="Test")
    db.add(ws)
    db.flush()
    p = Portfolio(workspace_id=ws.id, name="Test", cash_balance=cash)
    db.add(p)
    db.commit()
    return ws, p


def _add_item(db, portfolio_id: int, workspace_id: int, symbol: str,
              shares: float, avg_cost: float):
    item = PortfolioItem(
        workspace_id=workspace_id,
        portfolio_id=portfolio_id,
        symbol=symbol,
        shares=shares,
        avg_cost=avg_cost,
        sector="Test",
    )
    db.add(item)
    db.commit()
    return item


def _corrupted_holdings_json(items: list[dict]) -> str:
    """Build a holdings_json where current_price == avg_cost (the corruption pattern)."""
    return json.dumps([
        {
            "symbol": it["symbol"],
            "shares": it["shares"],
            "avg_cost": it["avg_cost"],
            "current_price": it["avg_cost"],          # corrupted — equals cost
            "market_value": it["shares"] * it["avg_cost"],
            "unrealized_pnl": 0.0,                   # corrupted — always 0
            "unrealized_pnl_pct": 0.0,
            "sector": it.get("sector", "Test"),
        }
        for it in items
    ])


def _make_snap(
    db,
    portfolio_id: int,
    workspace_id: int,
    snapshot_date: str,
    total_value: float,
    holdings: list[dict] | None = None,
    corrupt: bool = False,
    cash_balance: float = 0.0,
) -> PortfolioSnapshot:
    h_json = None
    if holdings:
        h_json = (
            _corrupted_holdings_json(holdings)
            if corrupt
            else json.dumps([
                {
                    **h,
                    "current_price": h.get("market_price", h["avg_cost"]),
                    "market_value": h["shares"] * h.get("market_price", h["avg_cost"]),
                    "unrealized_pnl": h["shares"] * (h.get("market_price", h["avg_cost"]) - h["avg_cost"]),
                    "unrealized_pnl_pct": 0.0,
                    "sector": h.get("sector", "Test"),
                }
                for h in holdings
            ])
        )
    snap = PortfolioSnapshot(
        workspace_id=workspace_id,
        portfolio_id=portfolio_id,
        snapshot_date=snapshot_date,
        total_value=total_value,
        cash_balance=cash_balance,
        total_invested=total_value - cash_balance,
        holdings_json=h_json,
        holdings_count=len(holdings) if holdings else 0,
    )
    db.add(snap)
    db.commit()
    return snap


def _today() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d")


def _date(offset_days: int) -> str:
    return (datetime.utcnow() - timedelta(days=offset_days)).strftime("%Y-%m-%d")


# ── Mock helpers ───────────────────────────────────────────────────────────────

def _mock_hist_prices(price_map: dict):
    """Return an async mock for fetch_historical_prices.

    price_map keys must be yfinance tickers (the normalized form), not
    platform symbols.  For Thai stocks (AOT.BK) these are identical; for
    DR certificates (NVDA01) the key should be the resolved ticker (NVDA).
    """
    async def _fake(symbols, date_str):
        return {sym: price_map.get(sym) for sym in symbols}
    return _fake


def run_async(coro):
    import asyncio
    return asyncio.get_event_loop().run_until_complete(coro)


# ── Test 1: Successful repair ─────────────────────────────────────────────────

def test_successful_repair_replaces_snapshot_value():
    """Corrupted snapshot (avg_cost prices) is replaced with correct market values."""
    db = make_session()
    ws, p = _seed(db, cash=0.0)

    # One holding: avg_cost = 50, true market price = 80
    _add_item(db, p.id, ws.id, "AOT.BK", 1000, 50.0)

    corrupted_nav = 1000 * 50.0  # 50,000 — wrong (uses avg_cost as price)
    snap = _make_snap(
        db, p.id, ws.id, _date(3), corrupted_nav,
        holdings=[{"symbol": "AOT.BK", "shares": 1000, "avg_cost": 50.0}],
        corrupt=True,
    )

    with patch(
        "services.snapshot_repair.fetch_historical_prices",
        side_effect=_mock_hist_prices({"AOT.BK": 80.0}),
    ):
        result = run_async(repair_snapshot_by_date(
            db, p.id, ws.id, snap.snapshot_date,
        ))

    assert result.status == RepairStatus.REPAIRED
    assert result.old_total_value == pytest.approx(50_000.0, abs=1)
    assert result.new_total_value == pytest.approx(80_000.0, abs=1)

    # Verify DB was actually updated
    updated = db.query(PortfolioSnapshot).filter_by(id=snap.id).first()
    assert updated.total_value == pytest.approx(80_000.0, abs=1)


# ── Test 2: Repair aborted when coverage too low ──────────────────────────────

def test_repair_aborted_when_coverage_too_low():
    """When <90% of historical prices are available, original snapshot is preserved."""
    db = make_session()
    ws, p = _seed(db, cash=0.0)

    _add_item(db, p.id, ws.id, "BANPU.BK", 500, 10.0)
    _add_item(db, p.id, ws.id, "AOT.BK",   200, 70.0)

    original_nav = 500 * 10.0 + 200 * 70.0  # 19,000 (wrong but preserved)
    snap = _make_snap(
        db, p.id, ws.id, _date(5), original_nav,
        holdings=[
            {"symbol": "BANPU.BK", "shares": 500, "avg_cost": 10.0},
            {"symbol": "AOT.BK",   "shares": 200, "avg_cost": 70.0},
        ],
        corrupt=True,
    )

    with patch(
        "services.snapshot_repair.fetch_historical_prices",
        side_effect=_mock_hist_prices({}),  # no prices available
    ):
        result = run_async(repair_snapshot_by_date(
            db, p.id, ws.id, snap.snapshot_date,
        ))

    assert result.status == RepairStatus.SKIPPED
    assert result.new_total_value is None

    # Original snapshot must be unchanged
    unchanged = db.query(PortfolioSnapshot).filter_by(id=snap.id).first()
    assert unchanged.total_value == pytest.approx(original_nav, abs=1)


# ── Test 3: Dry run does not modify the database ──────────────────────────────

def test_dry_run_does_not_modify_database():
    """dry_run=True must validate prices but leave the database unchanged."""
    db = make_session()
    ws, p = _seed(db, cash=0.0)
    _add_item(db, p.id, ws.id, "SCB.BK", 500, 100.0)

    original_nav = 500 * 100.0
    snap = _make_snap(
        db, p.id, ws.id, _date(2), original_nav,
        holdings=[{"symbol": "SCB.BK", "shares": 500, "avg_cost": 100.0}],
        corrupt=True,
    )

    with patch(
        "services.snapshot_repair.fetch_historical_prices",
        side_effect=_mock_hist_prices({"SCB.BK": 130.0}),
    ):
        result = run_async(repair_snapshot_by_date(
            db, p.id, ws.id, snap.snapshot_date, dry_run=True,
        ))

    assert result.status == RepairStatus.DRY_RUN
    assert result.new_total_value is None  # not computed in dry-run

    # DB must be unchanged
    db_snap = db.query(PortfolioSnapshot).filter_by(id=snap.id).first()
    assert db_snap.total_value == pytest.approx(original_nav, abs=1)


# ── Test 4: Corruption detection — price == avg_cost ─────────────────────────

def test_detect_corruption_price_equals_cost():
    """Detector flags snapshots where current_price == avg_cost for most holdings."""
    db = make_session()
    ws, p = _seed(db, cash=0.0)
    snap = _make_snap(
        db, p.id, ws.id, _date(10), 100_000.0,
        holdings=[
            {"symbol": f"STOCK{i}.BK", "shares": 100, "avg_cost": 50.0}
            for i in range(5)
        ],
        corrupt=True,
    )

    reports = detect_corrupted_snapshots(db, p.id, ws.id)

    assert len(reports) == 1
    assert reports[0].snapshot_id == snap.id
    assert CorruptionReason.PRICE_EQUALS_COST in reports[0].reasons
    assert CorruptionReason.ZERO_UNREALIZED_PNL in reports[0].reasons
    assert reports[0].confidence == CorruptionConfidence.HIGH


# ── Test 5: Corruption detection — zero unrealized P&L ───────────────────────

def test_detect_corruption_zero_unrealized_pnl():
    """Detector flags snapshots where all holdings have zero unrealized P&L."""
    db = make_session()
    ws, p = _seed(db, cash=0.0)

    holdings_json = json.dumps([
        {
            "symbol": f"S{i}.BK",
            "shares": 100,
            "avg_cost": 50.0,
            "current_price": 50.01,  # slightly above cost — not the price==cost signal
            "market_value": 5001.0,
            "unrealized_pnl": 0.0,   # explicitly zero
            "unrealized_pnl_pct": 0.0,
            "sector": "Test",
        }
        for i in range(4)
    ])
    snap = PortfolioSnapshot(
        workspace_id=ws.id,
        portfolio_id=p.id,
        snapshot_date=_date(15),
        total_value=20_000.0,
        cash_balance=0.0,
        total_invested=20_000.0,
        holdings_json=holdings_json,
        holdings_count=4,
    )
    db.add(snap)
    db.commit()

    reports = detect_corrupted_snapshots(db, p.id, ws.id)

    assert len(reports) >= 1
    flagged = next((r for r in reports if r.snapshot_id == snap.id), None)
    assert flagged is not None
    assert CorruptionReason.ZERO_UNREALIZED_PNL in flagged.reasons


# ── Test 6: Corruption detection — NAV discontinuity ─────────────────────────

def test_detect_corruption_nav_discontinuity():
    """Detector flags a snapshot whose value deviates >15% from its neighbours."""
    db = make_session()
    ws, p = _seed(db, cash=0.0)

    prev_date    = _date(5)
    corrupt_date = _date(4)
    next_date    = _date(3)

    _make_snap(db, p.id, ws.id, prev_date,    100_000.0)
    corrupt_snap = _make_snap(
        db, p.id, ws.id, corrupt_date, 150_000.0,  # 50% above interpolation
    )
    _make_snap(db, p.id, ws.id, next_date,    102_000.0)

    reports = detect_corrupted_snapshots(db, p.id, ws.id)

    flagged = next((r for r in reports if r.snapshot_id == corrupt_snap.id), None)
    assert flagged is not None
    assert CorruptionReason.NAV_DISCONTINUITY in flagged.reasons


# ── Test 7: Snapshot replacement persisted in DB ──────────────────────────────

def test_snapshot_replacement_persisted():
    """Repaired total_value must be committed and readable after repair."""
    db = make_session()
    ws, p = _seed(db, cash=0.0)
    _add_item(db, p.id, ws.id, "CPALL.BK", 200, 60.0)

    # Snapshot records cash_balance=10_000 at snapshot time — must be read
    # from the snapshot, not from portfolio.cash_balance.
    snap = _make_snap(
        db, p.id, ws.id, _date(1),
        total_value=200 * 60.0 + 10_000.0,
        holdings=[{"symbol": "CPALL.BK", "shares": 200, "avg_cost": 60.0}],
        corrupt=True,
        cash_balance=10_000.0,
    )

    with patch(
        "services.snapshot_repair.fetch_historical_prices",
        side_effect=_mock_hist_prices({"CPALL.BK": 75.0}),
    ):
        result = run_async(repair_snapshot_by_date(
            db, p.id, ws.id, snap.snapshot_date,
        ))

    assert result.status == RepairStatus.REPAIRED

    db_snap = db.query(PortfolioSnapshot).filter_by(
        portfolio_id=p.id, snapshot_date=snap.snapshot_date
    ).first()
    expected_nav = 200 * 75.0 + 10_000.0  # 15,000 + 10,000 = 25,000
    assert db_snap.total_value == pytest.approx(expected_nav, abs=1)


# ── Test 8: Audit log fields ──────────────────────────────────────────────────

def test_repair_result_audit_fields_populated():
    """RepairResult must carry all fields needed for audit logging."""
    db = make_session()
    ws, p = _seed(db, cash=0.0)
    _add_item(db, p.id, ws.id, "PTT.BK", 100, 40.0)

    snap = _make_snap(
        db, p.id, ws.id, _date(2), 100 * 40.0,
        holdings=[{"symbol": "PTT.BK", "shares": 100, "avg_cost": 40.0}],
        corrupt=True,
    )

    with patch(
        "services.snapshot_repair.fetch_historical_prices",
        side_effect=_mock_hist_prices({"PTT.BK": 48.0}),
    ):
        result = run_async(repair_snapshot_by_date(
            db, p.id, ws.id, snap.snapshot_date,
        ))

    assert result.snapshot_id == snap.id
    assert result.portfolio_id == p.id
    assert result.snapshot_date == snap.snapshot_date
    assert result.status == RepairStatus.REPAIRED
    assert result.old_total_value is not None
    assert result.new_total_value is not None
    assert result.reason != ""
    assert result.repaired_at != ""
    assert result.coverage is not None
    assert result.coverage["total"] >= 1
    assert result.coverage["successful"] >= 1


# ── Test 9: repair_snapshot() by ID ──────────────────────────────────────────

def test_repair_by_snapshot_id():
    """repair_snapshot(snapshot_id) correctly locates and repairs the row."""
    db = make_session()
    ws, p = _seed(db, cash=0.0)
    _add_item(db, p.id, ws.id, "KTB.BK", 300, 20.0)

    snap = _make_snap(
        db, p.id, ws.id, _date(6), 300 * 20.0,
        holdings=[{"symbol": "KTB.BK", "shares": 300, "avg_cost": 20.0}],
        corrupt=True,
    )

    with patch(
        "services.snapshot_repair.fetch_historical_prices",
        side_effect=_mock_hist_prices({"KTB.BK": 25.0}),
    ):
        result = run_async(repair_snapshot(db, snap.id, ws.id))

    assert result.status == RepairStatus.REPAIRED
    assert result.snapshot_id == snap.id
    assert result.new_total_value == pytest.approx(300 * 25.0, abs=1)


def test_repair_by_unknown_snapshot_id_returns_failed():
    """repair_snapshot() with a non-existent ID returns FAILED status."""
    db = make_session()
    ws, _ = _seed(db)
    result = run_async(repair_snapshot(db, snapshot_id=99999, workspace_id=ws.id))
    assert result.status == RepairStatus.FAILED


# ── Test 10: repair_snapshots() batch ────────────────────────────────────────

def test_repair_snapshots_date_range_batch():
    """repair_snapshots() processes all snapshots in the date range."""
    db = make_session()
    ws, p = _seed(db, cash=0.0)
    _add_item(db, p.id, ws.id, "SCC.BK", 100, 200.0)

    dates = [_date(d) for d in range(5, 0, -1)]  # 5 days, oldest first
    snaps = [
        _make_snap(
            db, p.id, ws.id, d, 100 * 200.0,
            holdings=[{"symbol": "SCC.BK", "shares": 100, "avg_cost": 200.0}],
            corrupt=True,
        )
        for d in dates
    ]

    with patch(
        "services.snapshot_repair.fetch_historical_prices",
        side_effect=_mock_hist_prices({"SCC.BK": 220.0}),
    ):
        results = run_async(repair_snapshots(
            db, p.id, ws.id,
            from_date=min(dates),
            to_date=max(dates),
        ))

    assert len(results) == 5
    assert all(r.status == RepairStatus.REPAIRED for r in results)
    assert all(r.new_total_value == pytest.approx(100 * 220.0, abs=1) for r in results)


def test_repair_snapshots_dry_run_batch_no_db_changes():
    """Batch dry run must not modify any snapshot rows."""
    db = make_session()
    ws, p = _seed(db, cash=0.0)
    _add_item(db, p.id, ws.id, "MINT.BK", 50, 30.0)

    dates = [_date(d) for d in range(3, 0, -1)]
    for d in dates:
        _make_snap(
            db, p.id, ws.id, d, 50 * 30.0,
            holdings=[{"symbol": "MINT.BK", "shares": 50, "avg_cost": 30.0}],
            corrupt=True,
        )

    original_values = {
        s.snapshot_date: s.total_value
        for s in db.query(PortfolioSnapshot).filter_by(portfolio_id=p.id).all()
    }

    with patch(
        "services.snapshot_repair.fetch_historical_prices",
        side_effect=_mock_hist_prices({"MINT.BK": 45.0}),
    ):
        results = run_async(repair_snapshots(
            db, p.id, ws.id,
            from_date=min(dates),
            to_date=max(dates),
            dry_run=True,
        ))

    assert all(r.status == RepairStatus.DRY_RUN for r in results)

    for snap in db.query(PortfolioSnapshot).filter_by(portfolio_id=p.id).all():
        assert snap.total_value == pytest.approx(
            original_values[snap.snapshot_date], abs=0.01
        ), f"DB was modified for {snap.snapshot_date} in dry-run mode"


# ── Test 11: Clean snapshot is idempotent ─────────────────────────────────────

def test_repair_preserves_correct_values_for_non_corrupt_snapshot():
    """Repairing a non-corrupt snapshot should produce the same values (idempotent)."""
    db = make_session()
    ws, p = _seed(db, cash=0.0)
    _add_item(db, p.id, ws.id, "HMPRO.BK", 100, 15.0)

    # Non-corrupt: current_price == 18, not avg_cost; snapshot has 5,000 cash
    correct_nav = 100 * 18.0 + 5_000.0
    snap = _make_snap(
        db, p.id, ws.id, _date(1), correct_nav,
        holdings=[{"symbol": "HMPRO.BK", "shares": 100, "avg_cost": 15.0, "market_price": 18.0}],
        corrupt=False,
        cash_balance=5_000.0,
    )

    with patch(
        "services.snapshot_repair.fetch_historical_prices",
        side_effect=_mock_hist_prices({"HMPRO.BK": 18.0}),
    ):
        result = run_async(repair_snapshot_by_date(
            db, p.id, ws.id, snap.snapshot_date,
        ))

    assert result.status == RepairStatus.REPAIRED
    assert result.new_total_value == pytest.approx(correct_nav, abs=1)


# ── Test 12: detect returns empty list for clean portfolio ────────────────────

def test_detect_returns_empty_for_clean_portfolio():
    """A portfolio with no suspicious snapshots produces an empty report."""
    db = make_session()
    ws, p = _seed(db, cash=0.0)

    for i, d in enumerate([_date(5), _date(4), _date(3)]):
        nav = 100_000.0 + i * 1_000.0
        holdings = [
            {
                "symbol": "BIG.BK",
                "shares": 1000,
                "avg_cost": 80.0,
                "current_price": 100.0 + i,
                "market_value": 1000 * (100.0 + i),
                "unrealized_pnl": 1000 * (100.0 + i - 80.0),
                "unrealized_pnl_pct": round((100.0 + i - 80.0) / 80.0 * 100, 2),
                "sector": "Test",
            }
        ]
        snap = PortfolioSnapshot(
            workspace_id=ws.id,
            portfolio_id=p.id,
            snapshot_date=d,
            total_value=nav,
            cash_balance=0.0,
            total_invested=80_000.0,
            holdings_json=json.dumps(holdings),
            holdings_count=1,
        )
        db.add(snap)
    db.commit()

    reports = detect_corrupted_snapshots(db, p.id, ws.id)
    assert reports == []


# ── Test 13: Sold position included from holdings_json ────────────────────────

def test_sold_position_included_from_holdings_json():
    """Position present in holdings_json but absent from PortfolioItem is repaired.

    This verifies the key behavioural difference from the old pipeline: the
    repair is driven by holdings_json, not by the current PortfolioItem table.
    A position that has since been sold must still contribute to the historical NAV.
    """
    db = make_session()
    ws, p = _seed(db, cash=0.0)

    # Only AOT.BK remains in the portfolio today — BANPU.BK was sold.
    _add_item(db, p.id, ws.id, "AOT.BK", 100, 70.0)
    # No PortfolioItem for BANPU.BK — it has been sold since the snapshot date.

    # Snapshot at the historical date has BOTH holdings.
    snap = _make_snap(
        db, p.id, ws.id, _date(5),
        total_value=100 * 70.0 + 500 * 10.0,  # corrupted — uses avg_cost as price
        holdings=[
            {"symbol": "AOT.BK",   "shares": 100, "avg_cost": 70.0},
            {"symbol": "BANPU.BK", "shares": 500, "avg_cost": 10.0},
        ],
        corrupt=True,
    )

    with patch(
        "services.snapshot_repair.fetch_historical_prices",
        side_effect=_mock_hist_prices({"AOT.BK": 80.0, "BANPU.BK": 12.0}),
    ):
        result = run_async(repair_snapshot_by_date(
            db, p.id, ws.id, snap.snapshot_date,
        ))

    assert result.status == RepairStatus.REPAIRED
    # Both positions must contribute: 100×80 + 500×12 = 8,000 + 6,000 = 14,000
    expected = 100 * 80.0 + 500 * 12.0
    assert result.new_total_value == pytest.approx(expected, abs=1)

    # The repaired holdings_json must still contain BANPU.BK
    updated = db.query(PortfolioSnapshot).filter_by(id=snap.id).first()
    symbols = {h["symbol"] for h in json.loads(updated.holdings_json)}
    assert "BANPU.BK" in symbols
    assert "AOT.BK" in symbols


# ── Test 14: Return fields recalculated atomically after repair ───────────────

def test_investment_return_fields_recalculated_after_repair():
    """Repair atomically recalculates return-series fields via the recovery
    engine after updating NAV fields.  Pre-existing stale values are replaced.

    When no previous snapshot exists (baseline) the recovery engine sets every
    return field to None — this is the correct baseline behaviour.
    """
    db = make_session()
    ws, p = _seed(db, cash=0.0)
    _add_item(db, p.id, ws.id, "PTT.BK", 100, 40.0)

    snap = _make_snap(
        db, p.id, ws.id, _date(2), 100 * 40.0,
        holdings=[{"symbol": "PTT.BK", "shares": 100, "avg_cost": 40.0}],
        corrupt=True,
    )
    # Stamp stale values — repair should overwrite all of them.
    snap.investment_return_pct  = 3.14
    snap.daily_return_pct       = 3.14
    snap.net_external_cash_flow = 1_000.0
    snap.period_fees_paid       = 99.5
    snap.period_realized_pnl    = 500.0
    snap.period_dividend_income = 75.0
    db.commit()

    with patch(
        "services.snapshot_repair.fetch_historical_prices",
        side_effect=_mock_hist_prices({"PTT.BK": 48.0}),
    ):
        result = run_async(repair_snapshot_by_date(
            db, p.id, ws.id, snap.snapshot_date,
        ))

    assert result.status == RepairStatus.REPAIRED

    # NAV must be repaired correctly.
    updated = db.query(PortfolioSnapshot).filter_by(id=snap.id).first()
    assert updated.total_value == pytest.approx(100 * 48.0, abs=1)

    # Return fields must be recalculated — not preserve stale values.
    # This is the baseline snapshot (no prev_snap), so the recovery engine
    # correctly sets all return fields to None.
    assert updated.investment_return_pct  is None
    assert updated.daily_return_pct       is None
    assert updated.net_external_cash_flow is None
    assert updated.period_fees_paid       is None
    assert updated.period_realized_pnl    is None
    assert updated.period_dividend_income is None


# ── Test 15: DR symbols are NOT normalized during snapshot repair ─────────────

def test_dr_symbol_not_normalized_during_snapshot_repair():
    """DR certificate .BK symbols (NVDA01.BK) are passed to yfinance unchanged.

    Before the fix, NVDA01.BK was resolved to NVDA (the underlying US ticker)
    and the USD price was stored as THB, inflating NAV by ~10×.

    After the fix, the exact SET DR ticker is used; yfinance returns the correct
    THB price for NVDA01.BK directly.
    """
    db = make_session()
    ws, p = _seed(db, cash=0.0)

    snap = _make_snap(
        db, p.id, ws.id, _date(3),
        total_value=100 * 20.0,
        holdings=[{"symbol": "NVDA01.BK", "shares": 100, "avg_cost": 20.0}],
        corrupt=True,
    )

    fetched_symbols: list[list[str]] = []

    async def _capture(symbols, date_str):
        fetched_symbols.append(list(symbols))
        return {"NVDA01.BK": 21.5}

    with patch(
        "services.snapshot_repair.fetch_historical_prices",
        side_effect=_capture,
    ):
        result = run_async(repair_snapshot_by_date(
            db, p.id, ws.id, snap.snapshot_date,
        ))

    assert result.status == RepairStatus.REPAIRED
    assert result.new_total_value == pytest.approx(100 * 21.5, abs=1)

    assert fetched_symbols, "fetch_historical_prices was never called"
    called_with = fetched_symbols[0]
    assert "NVDA01.BK" in called_with, f"Expected 'NVDA01.BK' in {called_with}"
    assert "NVDA" not in called_with, f"Underlying 'NVDA' must not appear in {called_with}"

    updated = db.query(PortfolioSnapshot).filter_by(id=snap.id).first()
    holdings = json.loads(updated.holdings_json)
    assert holdings[0]["symbol"] == "NVDA01.BK"
    assert holdings[0]["current_price"] == pytest.approx(21.5, abs=0.01)


# ── Test 16: snapshot.cash_balance used, not portfolio.cash_balance ───────────

def test_uses_snapshot_cash_balance_not_portfolio_cash_balance():
    """Repair uses snapshot.cash_balance (historical cash) rather than the
    portfolio's current cash_balance.
    """
    db = make_session()
    # Portfolio currently holds 99,000 cash — very different from snapshot time.
    ws, p = _seed(db, cash=99_000.0)
    _add_item(db, p.id, ws.id, "SCB.BK", 100, 100.0)

    # At snapshot time, cash was only 5,000.
    snap = _make_snap(
        db, p.id, ws.id, _date(3),
        total_value=100 * 100.0 + 5_000.0,
        holdings=[{"symbol": "SCB.BK", "shares": 100, "avg_cost": 100.0}],
        corrupt=True,
        cash_balance=5_000.0,
    )

    with patch(
        "services.snapshot_repair.fetch_historical_prices",
        side_effect=_mock_hist_prices({"SCB.BK": 120.0}),
    ):
        result = run_async(repair_snapshot_by_date(
            db, p.id, ws.id, snap.snapshot_date,
        ))

    assert result.status == RepairStatus.REPAIRED
    # Must use snapshot cash (5,000), not portfolio cash (99,000).
    expected = 100 * 120.0 + 5_000.0  # 12,000 + 5,000 = 17,000
    assert result.new_total_value == pytest.approx(expected, abs=1)

    # Sanity: portfolio cash must not appear in the result.
    assert result.new_total_value != pytest.approx(100 * 120.0 + 99_000.0, abs=1)


# ── Test 17: before_after comparison in RepairResult ─────────────────────────

def test_before_after_comparison_populated_in_repair_result():
    """RepairResult.before_after contains per-holding and aggregate comparison."""
    db = make_session()
    ws, p = _seed(db, cash=0.0)
    _add_item(db, p.id, ws.id, "KBANK.BK", 200, 150.0)

    snap = _make_snap(
        db, p.id, ws.id, _date(2),
        total_value=200 * 150.0,  # corrupted — avg_cost used as price
        holdings=[{"symbol": "KBANK.BK", "shares": 200, "avg_cost": 150.0}],
        corrupt=True,
    )

    with patch(
        "services.snapshot_repair.fetch_historical_prices",
        side_effect=_mock_hist_prices({"KBANK.BK": 175.0}),
    ):
        result = run_async(repair_snapshot_by_date(
            db, p.id, ws.id, snap.snapshot_date,
        ))

    assert result.status == RepairStatus.REPAIRED
    assert result.before_after is not None

    ba = result.before_after
    # Old equity = corrupted market_value (200 × 150 = 30,000)
    assert ba["equity_before"] == pytest.approx(200 * 150.0, abs=1)
    # New equity = repaired market_value (200 × 175 = 35,000)
    assert ba["equity_after"]  == pytest.approx(200 * 175.0, abs=1)
    assert ba["cash"]          == pytest.approx(0.0, abs=0.01)
    assert ba["total_before"]  == pytest.approx(200 * 150.0, abs=1)
    assert ba["total_after"]   == pytest.approx(200 * 175.0, abs=1)

    assert len(ba["holdings"]) == 1
    h = ba["holdings"][0]
    assert h["symbol"]    == "KBANK.BK"
    assert h["old_price"] == pytest.approx(150.0, abs=0.01)  # corrupted == avg_cost
    assert h["new_price"] == pytest.approx(175.0, abs=0.01)
    assert h["old_market_value"] == pytest.approx(200 * 150.0, abs=1)
    assert h["new_market_value"] == pytest.approx(200 * 175.0, abs=1)


# ── Timezone regression tests for _closing_price_on_or_before ────────────────

def _make_ohlcv(dates_and_closes: list[tuple[str, float]], tz=None) -> pd.DataFrame:
    idx = pd.to_datetime([d for d, _ in dates_and_closes])
    if tz:
        idx = idx.tz_localize(tz)
    return pd.DataFrame({"Close": [c for _, c in dates_and_closes]}, index=idx)


def test_closing_price_utc_aware_index():
    df = _make_ohlcv([
        ("2024-01-15", 100.0),
        ("2024-01-16", 110.0),
        ("2024-01-17", 120.0),
    ], tz="UTC")
    assert _closing_price_on_or_before(df, "2024-01-16") == pytest.approx(110.0)


def test_closing_price_tz_naive_index():
    df = _make_ohlcv([
        ("2024-01-15", 100.0),
        ("2024-01-16", 110.0),
        ("2024-01-17", 120.0),
    ])
    assert _closing_price_on_or_before(df, "2024-01-16") == pytest.approx(110.0)


def test_closing_price_exact_date_match():
    df = _make_ohlcv([
        ("2024-03-01", 50.0),
        ("2024-03-04", 55.0),
        ("2024-03-05", 60.0),
    ], tz="UTC")
    assert _closing_price_on_or_before(df, "2024-03-04") == pytest.approx(55.0)


def test_closing_price_uses_previous_trading_day():
    df = _make_ohlcv([
        ("2024-03-01", 100.0),  # Friday
        ("2024-03-04", 105.0),  # Monday — after the Saturday target
    ], tz="UTC")
    assert _closing_price_on_or_before(df, "2024-03-02") == pytest.approx(100.0)


def test_closing_price_returns_none_for_empty_df():
    assert _closing_price_on_or_before(None, "2024-01-01") is None
    assert _closing_price_on_or_before(pd.DataFrame(), "2024-01-01") is None


def test_closing_price_returns_none_when_all_dates_after_target():
    df = _make_ohlcv([
        ("2024-06-01", 200.0),
        ("2024-06-02", 210.0),
    ], tz="UTC")
    assert _closing_price_on_or_before(df, "2024-05-31") is None


# ── DR regression tests: platform symbol must reach yfinance unchanged ────────

def _assert_dr_symbol_passes_through(symbol: str, thb_price: float) -> None:
    """Assert *symbol* is forwarded to fetch_historical_prices without modification."""
    db = make_session()
    ws, p = _seed(db, cash=0.0)
    snap = _make_snap(
        db, p.id, ws.id, _date(5),
        total_value=1000 * 25.0,
        holdings=[{"symbol": symbol, "shares": 1000, "avg_cost": 25.0}],
        corrupt=True,
    )

    fetched: list[str] = []

    async def _capture(symbols, date_str):
        fetched.extend(symbols)
        return {s: thb_price if s == symbol else None for s in symbols}

    with patch("services.snapshot_repair.fetch_historical_prices", side_effect=_capture):
        result = run_async(repair_snapshot_by_date(db, p.id, ws.id, snap.snapshot_date))

    assert fetched, "fetch_historical_prices was never called"
    assert symbol in fetched, f"Expected '{symbol}' in {fetched}"
    assert result.status == RepairStatus.REPAIRED
    assert result.new_total_value == pytest.approx(1000 * thb_price, abs=1)


def test_aapl01_bk_passed_unchanged_to_yfinance():
    """AAPL01.BK must NOT be normalised to AAPL before the historical price fetch."""
    _assert_dr_symbol_passes_through("AAPL01.BK", thb_price=29.5)


def test_nvda01_bk_passed_unchanged_to_yfinance():
    """NVDA01.BK must NOT be normalised to NVDA before the historical price fetch."""
    _assert_dr_symbol_passes_through("NVDA01.BK", thb_price=21.0)


def test_googl01_bk_passed_unchanged_to_yfinance():
    """GOOGL01.BK must NOT be normalised to GOOGL before the historical price fetch."""
    _assert_dr_symbol_passes_through("GOOGL01.BK", thb_price=37.5)


def test_thai_set_symbols_unchanged_during_snapshot_repair():
    """Thai SET symbols (KBANK.BK, AOT.BK) are already yfinance-compatible and
    must pass through the repair fetch without modification."""
    db = make_session()
    ws, p = _seed(db, cash=0.0)
    snap = _make_snap(
        db, p.id, ws.id, _date(4),
        total_value=100 * 190.0 + 200 * 70.0,
        holdings=[
            {"symbol": "KBANK.BK", "shares": 100, "avg_cost": 190.0},
            {"symbol": "AOT.BK",   "shares": 200, "avg_cost": 70.0},
        ],
        corrupt=True,
    )

    fetched: list[str] = []

    async def _capture(symbols, date_str):
        fetched.extend(symbols)
        return {"KBANK.BK": 197.0, "AOT.BK": 72.0}

    with patch("services.snapshot_repair.fetch_historical_prices", side_effect=_capture):
        result = run_async(repair_snapshot_by_date(db, p.id, ws.id, snap.snapshot_date))

    assert result.status == RepairStatus.REPAIRED
    assert "KBANK.BK" in fetched, f"KBANK.BK not in {fetched}"
    assert "AOT.BK" in fetched, f"AOT.BK not in {fetched}"
    expected = 100 * 197.0 + 200 * 72.0
    assert result.new_total_value == pytest.approx(expected, abs=1)
