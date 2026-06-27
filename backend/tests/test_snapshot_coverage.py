"""Tests for snapshot market-price coverage validation.

Verifies that:
  - snapshots are aborted (SnapshotCoverageError) when fewer than 90% of
    holdings have a live market price
  - avg_cost is NEVER silently substituted for a missing price
  - holdings JSON reflects missing prices explicitly (current_price=None)
  - equity_value excludes positions with no live price (no avg_cost inflation)
  - partial coverage (≥90% but not 100%) is accepted and logged, not aborted
"""
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base, Portfolio, PortfolioItem, PortfolioSnapshot, Workspace
from services.portfolio_snapshots import SnapshotCoverageError


# ── Helpers ────────────────────────────────────────────────────────────────────

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


def _add_item(db, portfolio_id: int, workspace_id: int, symbol: str, shares: float, avg_cost: float):
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


def _prev_snapshot(db, portfolio_id: int, workspace_id: int, date_str: str, total_value: float):
    snap = PortfolioSnapshot(
        workspace_id=workspace_id,
        portfolio_id=portfolio_id,
        snapshot_date=date_str,
        total_value=total_value,
        cash_balance=0.0,
        total_invested=total_value,
    )
    db.add(snap)
    db.commit()


def _prev_date() -> str:
    return (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")


def _today() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d")


def run_snapshot(db, portfolio_id: int, workspace_id: int, today_str: str, price_map: dict):
    """Run generate_daily_snapshot synchronously with a mocked price fetch."""
    import asyncio
    from services.portfolio_snapshots import generate_daily_snapshot

    async def _go():
        with patch(
            "services.portfolio_snapshots.fetch_price_info",
            side_effect=lambda sym: {"current_price": price_map.get(sym)},
        ):
            return await generate_daily_snapshot(db, portfolio_id, workspace_id, today_str)

    return asyncio.get_event_loop().run_until_complete(_go())


# ── Tests: abort cases ─────────────────────────────────────────────────────────

def test_all_prices_missing_raises_coverage_error():
    """0/3 prices → coverage 0% → SnapshotCoverageError."""
    db = make_session()
    ws, p = _seed(db, cash=10_000.0)
    _add_item(db, p.id, ws.id, "BANPU.BK", 1000, 15.0)
    _add_item(db, p.id, ws.id, "AOT.BK",   500,  70.0)
    _add_item(db, p.id, ws.id, "CPALL.BK", 200, 60.0)

    with pytest.raises(SnapshotCoverageError) as exc_info:
        run_snapshot(db, p.id, ws.id, _today(), {})

    err = exc_info.value
    assert err.portfolio_id == p.id
    assert err.total == 3
    assert err.successful == 0
    assert set(err.missing) == {"BANPU.BK", "AOT.BK", "CPALL.BK"}


def test_below_90_coverage_raises_coverage_error():
    """4/7 prices (57%) → below 90% threshold → SnapshotCoverageError."""
    db = make_session()
    ws, p = _seed(db, cash=0.0)
    symbols = [f"SYM{i}.BK" for i in range(7)]
    for sym in symbols:
        _add_item(db, p.id, ws.id, sym, 100, 50.0)

    # Only 4 of 7 symbols have a live price
    partial_prices = {sym: 55.0 for sym in symbols[:4]}

    with pytest.raises(SnapshotCoverageError) as exc_info:
        run_snapshot(db, p.id, ws.id, _today(), partial_prices)

    err = exc_info.value
    assert err.total == 7
    assert err.successful == 4
    assert len(err.missing) == 3


def test_coverage_error_attributes_match_portfolio():
    """SnapshotCoverageError carries the correct portfolio_id and date."""
    db = make_session()
    ws, p = _seed(db, cash=0.0)
    _add_item(db, p.id, ws.id, "MISSING.BK", 100, 10.0)
    today = _today()

    with pytest.raises(SnapshotCoverageError) as exc_info:
        run_snapshot(db, p.id, ws.id, today, {})

    err = exc_info.value
    assert err.portfolio_id == p.id
    assert err.date == today
    assert "MISSING.BK" in err.missing


def test_snapshot_not_saved_when_coverage_too_low():
    """Aborted snapshot must not write a row to the database."""
    db = make_session()
    ws, p = _seed(db, cash=5_000.0)
    _add_item(db, p.id, ws.id, "A.BK", 100, 20.0)
    _add_item(db, p.id, ws.id, "B.BK", 100, 30.0)
    today = _today()

    with pytest.raises(SnapshotCoverageError):
        # 0/2 prices available
        run_snapshot(db, p.id, ws.id, today, {})

    from models.database import PortfolioSnapshot as PS
    saved = db.query(PS).filter_by(portfolio_id=p.id, snapshot_date=today).first()
    assert saved is None, "Snapshot row must not be written when coverage is insufficient"


# ── Tests: pass cases ──────────────────────────────────────────────────────────

def test_full_coverage_succeeds():
    """7/7 prices (100%) → snapshot saves successfully."""
    db = make_session()
    ws, p = _seed(db, cash=50_000.0)
    symbols = [f"STOCK{i}.BK" for i in range(7)]
    for sym in symbols:
        _add_item(db, p.id, ws.id, sym, 100, 50.0)

    prices = {sym: 55.0 for sym in symbols}
    result = run_snapshot(db, p.id, ws.id, _today(), prices)

    assert result["holdings_count"] == 7
    # equity_value = 7 × 100 × 55 = 38,500; cash = 50,000
    assert result["total_value"] == pytest.approx(50_000.0 + 38_500.0, abs=1)


def test_exactly_90_percent_coverage_succeeds():
    """9/10 prices (90%) is at the threshold → snapshot proceeds."""
    db = make_session()
    ws, p = _seed(db, cash=0.0)
    symbols = [f"T{i}.BK" for i in range(10)]
    for sym in symbols:
        _add_item(db, p.id, ws.id, sym, 100, 10.0)

    prices = {sym: 12.0 for sym in symbols[:9]}  # 9/10 = 90%
    result = run_snapshot(db, p.id, ws.id, _today(), prices)

    assert result["holdings_count"] == 10
    # 9 positions with live price: 9 × 100 × 12 = 10,800
    assert result["total_value"] == pytest.approx(10_800.0, abs=1)


# ── Tests: price integrity ─────────────────────────────────────────────────────

def test_missing_price_does_not_use_avg_cost():
    """A single missing price (≥90% coverage) must NOT fall back to avg_cost.

    If avg_cost fallback were active, equity_value would include the missing
    position at cost.  With the fix, the missing position is excluded entirely.
    """
    db = make_session()
    ws, p = _seed(db, cash=0.0)
    # 10 holdings; only 9 have live prices (90% threshold, exactly)
    for i in range(9):
        _add_item(db, p.id, ws.id, f"OK{i}.BK", 100, 50.0)
    _add_item(db, p.id, ws.id, "MISSING.BK", 100, 999.0)  # avg_cost=999, no live price

    prices = {f"OK{i}.BK": 55.0 for i in range(9)}
    result = run_snapshot(db, p.id, ws.id, _today(), prices)

    # If avg_cost fallback were used: equity_value = 9×100×55 + 100×999 = 149,400
    # Correct (no fallback):          equity_value = 9×100×55             = 49,500
    expected_equity = 9 * 100 * 55.0
    wrong_equity_with_fallback = expected_equity + 100 * 999.0
    assert result["total_value"] != pytest.approx(wrong_equity_with_fallback, abs=1), (
        "avg_cost fallback must not be used — equity is inflated"
    )
    assert result["total_value"] == pytest.approx(expected_equity, abs=1)


def test_missing_price_reflected_in_holdings_json():
    """Holdings JSON must show current_price=None for positions with no live price."""
    db = make_session()
    ws, p = _seed(db, cash=0.0)
    for i in range(9):
        _add_item(db, p.id, ws.id, f"OK{i}.BK", 100, 50.0)
    _add_item(db, p.id, ws.id, "DARK.BK", 100, 80.0)

    prices = {f"OK{i}.BK": 55.0 for i in range(9)}
    result = run_snapshot(db, p.id, ws.id, _today(), prices)

    dark_holding = next(h for h in result["holdings"] if h["symbol"] == "DARK.BK")
    assert dark_holding["current_price"] is None
    assert dark_holding["market_value"] is None
    assert dark_holding["unrealized_pnl"] is None
    assert dark_holding["price_missing"] is True


def test_available_prices_are_not_affected_by_missing_peers():
    """Holdings with live prices must have correct market values regardless of peers."""
    db = make_session()
    ws, p = _seed(db, cash=0.0)
    for i in range(9):
        _add_item(db, p.id, ws.id, f"OK{i}.BK", 100, 50.0)
    _add_item(db, p.id, ws.id, "MISSING.BK", 50, 30.0)

    prices = {f"OK{i}.BK": 60.0 for i in range(9)}
    result = run_snapshot(db, p.id, ws.id, _today(), prices)

    ok_holdings = [h for h in result["holdings"] if h["symbol"] != "MISSING.BK"]
    for h in ok_holdings:
        assert h["current_price"] == pytest.approx(60.0)
        assert h["market_value"] == pytest.approx(100 * 60.0)
        assert h["unrealized_pnl"] == pytest.approx(100 * (60.0 - 50.0))


def test_cash_only_portfolio_succeeds():
    """Portfolio with no holdings (cash only) always has 100% coverage."""
    db = make_session()
    ws, p = _seed(db, cash=100_000.0)
    result = run_snapshot(db, p.id, ws.id, _today(), {})

    assert result["total_value"] == pytest.approx(100_000.0, abs=1)
    assert result["holdings_count"] == 0
