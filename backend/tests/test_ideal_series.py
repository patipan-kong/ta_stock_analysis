"""Tests for services/evaluation/ideal_series.py — AI Evaluation M6.

Coverage
--------
compute_ideal_series
  1. No RecommendationSnapshot at all -> status="insufficient_data".
  2. Snapshot exists but no PortfolioSnapshot price history -> "no_price_history".
  3. Flat price across the window -> return_pct ~= 0, series indexed to 100 throughout.
  4. Price appreciation -> return_pct matches the price change exactly (single holding).
  5. A later recommendation snapshot inside the window is treated as a
     rebalance point (snapshots_used == 2, rebalance_dates has one entry).

compute_three_portfolios
  6. No data anywhere -> status="insufficient_data", empty chart.
  7. With ideal + actual + AI(ACTIVE_MODEL) data -> status="ok", gap_a/gap_b
     populated, chart rows share one date axis.
  8. Accounting Correctness C5, Issue B regression: the chart's "actual"
     line must be the same cash-flow-adjusted TWR series the summary
     card's actual.return_pct uses, not a raw total_value ratio — a mid-
     window deposit must not appear as investment return in the chart.
"""
from __future__ import annotations

import json
import sys
import os
from datetime import date, datetime, timedelta

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.evaluation.ideal_series import (  # noqa: E402
    compute_ideal_series,
    compute_three_portfolios,
)


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


def _d(days_ago: int) -> str:
    return (date.today() - timedelta(days=days_ago)).isoformat()


def _seed_recommendation(db, ws, portfolio, allocations, days_ago):
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
        total_portfolio_value=1_000_000.0,
        projected_allocations_json=json.dumps(allocations),
        created_at=datetime.utcnow() - timedelta(days=days_ago),
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return snap


def _seed_price_day(db, ws, portfolio, days_ago, prices: dict):
    """One PortfolioSnapshot row carrying holdings_json prices for a given day."""
    from models.database import PortfolioSnapshot

    holdings = [{"symbol": sym, "current_price": p} for sym, p in prices.items()]
    db.add(PortfolioSnapshot(
        workspace_id=ws.id, portfolio_id=portfolio.id,
        snapshot_date=_d(days_ago), total_value=1_000_000.0, cash_balance=0.0,
        holdings_json=json.dumps(holdings),
    ))
    db.commit()


_SEED_100_AAA = [{"symbol": "AAA", "target_weight": 100.0, "action": "BUY"}]
_REBALANCE_100_BBB = [{"symbol": "BBB", "target_weight": 100.0, "action": "BUY"}]


def test_insufficient_data_no_snapshot(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    result = compute_ideal_series(db, portfolio.id, period_days=90)
    assert result["status"] == "insufficient_data"
    assert result["series"] == []


def test_no_price_history(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    _seed_recommendation(db, ws, portfolio, _SEED_100_AAA, days_ago=15)
    result = compute_ideal_series(db, portfolio.id, period_days=10)
    assert result["status"] == "no_price_history"


def test_flat_price_yields_zero_return(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    _seed_recommendation(db, ws, portfolio, _SEED_100_AAA, days_ago=15)
    for d in range(10, -1, -1):
        _seed_price_day(db, ws, portfolio, d, {"AAA": 100.0})

    result = compute_ideal_series(db, portfolio.id, period_days=10)

    assert result["status"] == "ok"
    assert result["return_pct"] == pytest.approx(0.0, abs=0.01)
    assert all(row["index"] == pytest.approx(100.0, abs=0.01) for row in result["series"])


def test_price_appreciation_matches_return(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    _seed_recommendation(db, ws, portfolio, _SEED_100_AAA, days_ago=15)
    _seed_price_day(db, ws, portfolio, 10, {"AAA": 100.0})
    _seed_price_day(db, ws, portfolio, 0, {"AAA": 110.0})

    result = compute_ideal_series(db, portfolio.id, period_days=10)

    assert result["status"] == "ok"
    assert result["return_pct"] == pytest.approx(10.0, abs=0.01)
    assert result["series"][-1]["index"] == pytest.approx(110.0, abs=0.01)


def test_later_snapshot_is_a_rebalance_point(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    _seed_recommendation(db, ws, portfolio, _SEED_100_AAA, days_ago=15)
    _seed_recommendation(db, ws, portfolio, _REBALANCE_100_BBB, days_ago=5)
    for d in range(10, -1, -1):
        _seed_price_day(db, ws, portfolio, d, {"AAA": 100.0, "BBB": 50.0})

    result = compute_ideal_series(db, portfolio.id, period_days=10)

    assert result["status"] == "ok"
    assert result["snapshots_used"] == 2
    assert result["rebalance_dates"] == [_d(5)]


_SEED_95_AAA = [{"symbol": "AAA", "target_weight": 95.0, "action": "BUY"}]
_REBALANCE_90_AAA = [{"symbol": "AAA", "target_weight": 90.0, "action": "HOLD"}]
_REBALANCE_97_AAA = [{"symbol": "AAA", "target_weight": 97.0, "action": "BUY"}]


def test_partial_weight_seed_no_leak_at_flat_price(db, ws_portfolio):
    """Accounting Correctness Milestone 1 regression: a 95%-deployed seed
    allocation at a flat price must return exactly 0%, not -5%. Pre-fix, the
    unallocated 5% (the optimizer's own cash floor, OPTIMIZER_PHILOSOPHY.md
    §2 Priority 7) was silently dropped from NAV at the seed rebalance,
    fabricating a loss with zero price movement."""
    ws, portfolio = ws_portfolio
    _seed_recommendation(db, ws, portfolio, _SEED_95_AAA, days_ago=15)
    for d in range(10, -1, -1):
        _seed_price_day(db, ws, portfolio, d, {"AAA": 100.0})

    result = compute_ideal_series(db, portfolio.id, period_days=10)

    assert result["status"] == "ok"
    assert result["return_pct"] == pytest.approx(0.0, abs=0.01)
    assert result["series"][-1]["index"] == pytest.approx(100.0, abs=0.01)


def test_partial_weight_multiple_rebalances_no_leak_at_flat_price(db, ws_portfolio):
    """The direct regression test for the compounding cash-leak defect on
    the Ideal Portfolio side: three different weight sums (95% -> 90% ->
    97%) at a flat price must still return exactly 0%. Pre-fix, this exact
    sequence would compound to roughly 0.95 * 0.90 * 0.97 - 1 = -17% with
    zero market movement — the mechanism behind the -24.5%/-51.7% real
    example this milestone was authorized to fix."""
    ws, portfolio = ws_portfolio
    _seed_recommendation(db, ws, portfolio, _SEED_95_AAA, days_ago=15)
    _seed_recommendation(db, ws, portfolio, _REBALANCE_90_AAA, days_ago=6)
    _seed_recommendation(db, ws, portfolio, _REBALANCE_97_AAA, days_ago=3)
    for d in range(10, -1, -1):
        _seed_price_day(db, ws, portfolio, d, {"AAA": 100.0})

    result = compute_ideal_series(db, portfolio.id, period_days=10)

    assert result["status"] == "ok"
    assert result["snapshots_used"] == 3
    assert result["return_pct"] == pytest.approx(0.0, abs=0.01)
    assert all(row["index"] == pytest.approx(100.0, abs=0.01) for row in result["series"])


def test_partial_weight_with_price_appreciation_scales_by_invested_fraction(db, ws_portfolio):
    """Cash earns zero return: a 95%-deployed portfolio whose sole holding
    rises 10% must return 9.5% overall (95% x +10%), not the full +10% a
    100%-deployed portfolio would show — proving the 5% cash residual sits
    flat rather than participating in (or leaking from) the price move."""
    ws, portfolio = ws_portfolio
    _seed_recommendation(db, ws, portfolio, _SEED_95_AAA, days_ago=15)
    _seed_price_day(db, ws, portfolio, 10, {"AAA": 100.0})
    _seed_price_day(db, ws, portfolio, 0, {"AAA": 110.0})

    result = compute_ideal_series(db, portfolio.id, period_days=10)

    assert result["status"] == "ok"
    assert result["return_pct"] == pytest.approx(9.5, abs=0.01)


def test_three_portfolios_insufficient_data(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    result = compute_three_portfolios(db, portfolio.id, period_days=90)
    assert result["status"] == "insufficient_data"
    assert result["chart"] == []
    assert result["gap_a"]["value"] is None
    assert result["gap_b"]["value"] is None


def test_three_portfolios_global_benchmark_data_alone_is_not_ok(db, ws_portfolio):
    """BenchmarkPrice is a global table, not scoped to this portfolio — its
    mere presence must never flip a data-less portfolio's status to "ok"
    (regression for a bug caught via live verification: a cold portfolio
    was reporting status="ok" purely because ^GSPC benchmark rows existed
    from an unrelated portfolio's sync)."""
    from models.database import BenchmarkPrice

    ws, portfolio = ws_portfolio
    db.add(BenchmarkPrice(symbol="^GSPC", price_date=_d(5), close_price=4000.0))
    db.add(BenchmarkPrice(symbol="^GSPC", price_date=_d(0), close_price=4100.0))
    db.commit()

    result = compute_three_portfolios(db, portfolio.id, period_days=90)
    assert result["status"] == "insufficient_data"


def _seed_ai_shadow(db, ws, portfolio, *, inception_days_ago, holdings, snapshot_rows):
    """holdings: list of {symbol, shares} for inception_holdings_json.
    snapshot_rows: list of (days_ago, holdings_json_or_None, stored_total_value,
    stored_return_pct_since_inception) — the STORED fields simulate whatever
    shadow_tracker.value_shadow_portfolio wrote from its own (live-cache)
    price source; compute_three_portfolios must ignore them post-fix and
    revalue holdings_json from the canonical price archive instead.
    """
    from models.database import ShadowPortfolio, ShadowPortfolioSnapshot

    shadow = ShadowPortfolio(
        workspace_id=ws.id, portfolio_id=portfolio.id, shadow_type="ACTIVE_MODEL",
        name="AI", inception_date=_d(inception_days_ago), inception_value=1_000_000.0,
        inception_holdings_json=json.dumps(holdings), paper_cash_balance=0.0,
        is_active=True, created_at=datetime.utcnow(),
    )
    db.add(shadow)
    db.commit()
    db.refresh(shadow)

    for days_ago, holdings_json, stored_total_value, stored_return_pct in snapshot_rows:
        db.add(ShadowPortfolioSnapshot(
            shadow_portfolio_id=shadow.id, snapshot_date=_d(days_ago),
            total_value=stored_total_value, return_pct_since_inception=stored_return_pct,
            daily_return_pct=None,
            holdings_json=json.dumps(holdings_json) if holdings_json is not None else None,
            created_at=datetime.utcnow(),
        ))
    db.commit()
    return shadow


_AAA_10000_SHARES = [{"symbol": "AAA", "shares": 10000, "inception_price": 100.0, "price_frozen": False}]


def test_three_portfolios_ok_with_full_data(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    _seed_recommendation(db, ws, portfolio, _SEED_100_AAA, days_ago=15)
    for d in range(10, -1, -1):
        _seed_price_day(db, ws, portfolio, d, {"AAA": 100.0})

    _seed_ai_shadow(
        db, ws, portfolio, inception_days_ago=10, holdings=_AAA_10000_SHARES,
        snapshot_rows=[
            (10, _AAA_10000_SHARES, 1_000_000.0, 0.0),
            (0, _AAA_10000_SHARES, 1_000_000.0, 0.0),
        ],
    )

    result = compute_three_portfolios(db, portfolio.id, period_days=10)

    assert result["status"] == "ok"
    assert len(result["chart"]) > 0
    assert all(set(row.keys()) == {"date", "ideal", "ai", "actual", "benchmark"} for row in result["chart"])
    assert result["ideal"]["return_pct"] == pytest.approx(0.0, abs=0.01)
    assert result["ai_portfolio"]["return_pct"] == pytest.approx(0.0, abs=0.01)
    assert result["gap_a"]["value"] == pytest.approx(0.0, abs=0.01)


def test_gap_a_uses_canonical_prices_not_stored_shadow_total_value(db, ws_portfolio):
    """Regression for the Gap A price-source-unification fix: the shadow's
    STORED total_value/return_pct_since_inception (simulating a stale/
    divergent AgentCache-sourced live valuation) claims +5%, but the
    canonical price archive (same one Ideal reads) shows AAA flat at 100
    the whole window. ai_portfolio.return_pct must reflect the canonical
    revaluation of the shadow's actual holdings (0%), not the stored,
    independently-sourced number (5%) — proving Gap A no longer inherits
    price-source noise between the two hypothetical portfolios.
    """
    ws, portfolio = ws_portfolio
    _seed_recommendation(db, ws, portfolio, _SEED_100_AAA, days_ago=15)
    for d in range(10, -1, -1):
        _seed_price_day(db, ws, portfolio, d, {"AAA": 100.0})

    _seed_ai_shadow(
        db, ws, portfolio, inception_days_ago=10, holdings=_AAA_10000_SHARES,
        snapshot_rows=[
            (10, _AAA_10000_SHARES, 1_000_000.0, 0.0),
            # Stored total_value/return_pct claims +5% — a stale/divergent
            # live-cache price the canonical archive does not corroborate.
            (0, _AAA_10000_SHARES, 1_050_000.0, 5.0),
        ],
    )

    result = compute_three_portfolios(db, portfolio.id, period_days=10)

    assert result["ai_portfolio"]["return_pct"] == pytest.approx(0.0, abs=0.01)
    assert result["gap_a"]["value"] == pytest.approx(0.0, abs=0.01)


def test_ai_portfolio_revalues_from_canonical_price_appreciation(db, ws_portfolio):
    """Mirror of test_price_appreciation_matches_return but for the AI
    Portfolio side: canonical AAA price rises 100 -> 110 (+10%); the shadow's
    stored fields deliberately disagree (0%). ai_portfolio.return_pct must
    track the canonical +10%, confirming the revaluation — not the stored
    figure — drives the number in both directions, not just toward zero.
    """
    ws, portfolio = ws_portfolio
    _seed_recommendation(db, ws, portfolio, _SEED_100_AAA, days_ago=15)
    _seed_price_day(db, ws, portfolio, 10, {"AAA": 100.0})
    _seed_price_day(db, ws, portfolio, 0, {"AAA": 110.0})

    _seed_ai_shadow(
        db, ws, portfolio, inception_days_ago=10, holdings=_AAA_10000_SHARES,
        snapshot_rows=[
            (10, _AAA_10000_SHARES, 1_000_000.0, 0.0),
            (0, _AAA_10000_SHARES, 1_000_000.0, 0.0),  # stored: claims flat
        ],
    )

    result = compute_three_portfolios(db, portfolio.id, period_days=10)

    assert result["ai_portfolio"]["return_pct"] == pytest.approx(10.0, abs=0.01)


def test_actual_chart_uses_cash_flow_adjusted_twr_matching_summary_card(db, ws_portfolio):
    """Issue B regression (Accounting Correctness C5): the chart's 'actual'
    line and the summary card's actual.return_pct must agree, even when a
    deposit inflates raw total_value mid-window. Previously the chart
    reindexed raw PortfolioSnapshot.total_value (double-counting the
    deposit as investment return); the card already used TWR-chained
    investment_return_pct. Both must report the same cumulative return.
    """
    from models.database import PortfolioSnapshot

    ws, portfolio = ws_portfolio
    # Day 2 (oldest): baseline, no prior snapshot to compute a return from.
    # Day 1: +1% genuine investment return.
    # Day 0: a $200k deposit inflates total_value by ~17%, but
    # investment_return_pct correctly reports 0% real investment return
    # for the day (the deposit itself is not a gain).
    db.add(PortfolioSnapshot(
        workspace_id=ws.id, portfolio_id=portfolio.id, snapshot_date=_d(2),
        total_value=1_000_000.0, cash_balance=100_000.0,
    ))
    db.add(PortfolioSnapshot(
        workspace_id=ws.id, portfolio_id=portfolio.id, snapshot_date=_d(1),
        total_value=1_010_000.0, cash_balance=100_000.0,
        investment_return_pct=1.0,
    ))
    db.add(PortfolioSnapshot(
        workspace_id=ws.id, portfolio_id=portfolio.id, snapshot_date=_d(0),
        total_value=1_210_000.0, cash_balance=300_000.0,
        investment_return_pct=0.0,
    ))
    db.commit()

    result = compute_three_portfolios(db, portfolio.id, period_days=10)

    card_return = result["actual"]["return_pct"]
    chart_actual = [row["actual"] for row in result["chart"] if row["actual"] is not None]
    chart_return = chart_actual[-1] - 100.0

    assert card_return == pytest.approx(1.0, abs=0.01)
    assert chart_return == pytest.approx(card_return, abs=0.01)

    # Must NOT match the naive raw NAV ratio the old (buggy) chart code
    # would have shown: (1,210,000 - 1,000,000) / 1,000,000 * 100 ~= +21%.
    naive_raw_ratio = (1_210_000.0 - 1_000_000.0) / 1_000_000.0 * 100
    assert chart_return != pytest.approx(naive_raw_ratio, abs=1.0)


def test_ai_portfolio_legacy_row_without_holdings_json_is_no_price_history(db, ws_portfolio):
    """Pre-fix ShadowPortfolioSnapshot rows (or any row with holdings_json
    unset) cannot be canonically revalued — must report a status distinct
    from "ok" rather than silently fabricating a 0%/None-shares return.
    """
    ws, portfolio = ws_portfolio
    _seed_recommendation(db, ws, portfolio, _SEED_100_AAA, days_ago=15)
    for d in range(10, -1, -1):
        _seed_price_day(db, ws, portfolio, d, {"AAA": 100.0})

    _seed_ai_shadow(
        db, ws, portfolio, inception_days_ago=10, holdings=_AAA_10000_SHARES,
        snapshot_rows=[
            (10, None, 1_000_000.0, 0.0),
            (0, None, 1_050_000.0, 5.0),
        ],
    )

    result = compute_three_portfolios(db, portfolio.id, period_days=10)

    assert result["ai_portfolio"]["status"] == "no_price_history"
    assert result["ai_portfolio"]["return_pct"] is None
    assert result["gap_a"]["value"] is None


def test_gap_a_aligns_to_overlapping_window_when_ai_inception_is_later(db, ws_portfolio):
    """Regression for the event-sequence-alignment fix: Ideal replays the
    full 20-day window (including an early -90% crash entirely before the
    AI shadow's own inception), while the AI shadow's inception (simulating
    a Phase 4C.6 admin reset) starts only 5 days ago and never saw that
    crash. Comparing Ideal's full-window return (-90%) against AI's
    inception-to-date return (0%) would produce a Gap A of -90 that is
    really a time-horizon mismatch, not friction. After alignment to the
    overlapping [day-5, day-0] sub-window — where price is flat for both —
    Gap A must collapse to ~0.
    """
    ws, portfolio = ws_portfolio
    _seed_recommendation(db, ws, portfolio, _SEED_100_AAA, days_ago=25)
    _seed_price_day(db, ws, portfolio, 20, {"AAA": 100.0})
    for d in range(19, -1, -1):
        _seed_price_day(db, ws, portfolio, d, {"AAA": 10.0})

    _seed_ai_shadow(
        db, ws, portfolio, inception_days_ago=5, holdings=_AAA_10000_SHARES,
        snapshot_rows=[
            (5, _AAA_10000_SHARES, 100_000.0, 0.0),
            (0, _AAA_10000_SHARES, 100_000.0, 0.0),
        ],
    )

    result = compute_three_portfolios(db, portfolio.id, period_days=20)

    # Sanity: Ideal's own unaligned full-window figure really is the crash.
    assert result is not None
    assert result["ai_portfolio"]["return_pct"] == pytest.approx(0.0, abs=0.01)
    # The aligned Ideal figure (used for both display and Gap A) must reflect
    # only the flat post-crash sub-window it shares with the AI shadow, not
    # the full-window -90% figure compute_ideal_series would report alone.
    assert result["ideal"]["return_pct"] == pytest.approx(0.0, abs=0.5)
    assert result["gap_a"]["value"] == pytest.approx(0.0, abs=0.5)


def test_ai_portfolio_no_snapshots_in_window_status(db, ws_portfolio):
    """Shadow exists but has no ShadowPortfolioSnapshot rows inside the
    requested window — status must say so explicitly rather than "ok"."""
    from models.database import ShadowPortfolio

    ws, portfolio = ws_portfolio
    _seed_recommendation(db, ws, portfolio, _SEED_100_AAA, days_ago=15)
    for d in range(10, -1, -1):
        _seed_price_day(db, ws, portfolio, d, {"AAA": 100.0})

    shadow = ShadowPortfolio(
        workspace_id=ws.id, portfolio_id=portfolio.id, shadow_type="ACTIVE_MODEL",
        name="AI", inception_date=_d(10), inception_value=1_000_000.0,
        inception_holdings_json=json.dumps(_AAA_10000_SHARES), is_active=True,
        created_at=datetime.utcnow(),
    )
    db.add(shadow)
    db.commit()

    result = compute_three_portfolios(db, portfolio.id, period_days=10)

    assert result["ai_portfolio"]["status"] == "no_snapshots_in_window"
    assert result["ai_portfolio"]["return_pct"] is None
