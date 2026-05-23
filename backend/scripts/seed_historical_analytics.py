#!/usr/bin/env python3
"""
Seed script for Phase 3A analytics development.

Generates realistic mock data so the /analytics/performance-stats endpoint
returns meaningful numbers immediately without running the live scheduler.

What it creates:
  - N trading-day portfolio snapshots with sector breakdowns and holdings
  - Benchmark prices for ^SET.BK and QQQ
  - BUY / SELL / ACCUMULATE / REDUCE signals in signal_history
  - INITIAL_POSITION and INITIAL_CASH transactions

Usage (run from the backend/ directory):
    python scripts/seed_historical_analytics.py
    python scripts/seed_historical_analytics.py --portfolio-id 2 --days 60
    python scripts/seed_historical_analytics.py --clear        # wipe then reseed
    python scripts/seed_historical_analytics.py --dry-run      # print plan, no writes
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
from datetime import datetime, timedelta

# Allow imports from the backend root when executed from anywhere.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from models.database import (
    SessionLocal,
    Portfolio,
    PortfolioSnapshot,
    BenchmarkPrice,
    SignalHistory,
    Transaction,
    get_default_workspace,
)

# ── Seed configuration ────────────────────────────────────────────────────────

RANDOM_SEED = 42

# Mock holdings — symbol, sector, initial shares, cost basis
MOCK_HOLDINGS: list[dict] = [
    {"symbol": "SCB.BK",   "sector": "Financial",   "shares": 2_000, "avg_cost": 95.0},
    {"symbol": "PTT.BK",   "sector": "Energy",      "shares": 5_000, "avg_cost": 32.5},
    {"symbol": "KBANK.BK", "sector": "Financial",   "shares": 1_500, "avg_cost": 140.0},
    {"symbol": "CPALL.BK", "sector": "Consumer",    "shares": 3_000, "avg_cost": 58.0},
    {"symbol": "AOT.BK",   "sector": "Industrial",  "shares": 1_000, "avg_cost": 65.0},
    {"symbol": "ADVANC.BK","sector": "Technology",  "shares": 1_200, "avg_cost": 200.0},
    {"symbol": "AAPL",     "sector": "Technology",  "shares": 10,    "avg_cost": 175.0},
    {"symbol": "NVDA",     "sector": "Technology",  "shares": 5,     "avg_cost": 800.0},
]

STARTING_CASH = 50_000.0

# Benchmark GBM parameters: start price and daily vol
_BENCH_CFG: dict[str, dict] = {
    "^SET.BK": {"start": 1_360.0, "daily_vol": 0.008,  "daily_drift": 0.00015},
    "QQQ":     {"start":   475.0, "daily_vol": 0.012,  "daily_drift": 0.00025},
}

# Signal schedule: (day_offset, symbol, action, signal_level, confidence)
_SIGNAL_SCHEDULE: list[tuple] = [
    (2,  "NVDA",     "BUY",        "BUY",        "high"),
    (5,  "PTT.BK",   "ACCUMULATE", "ACCUMULATE", "medium"),
    (8,  "SCB.BK",   "REDUCE",     "REDUCE",     "medium"),
    (12, "AAPL",     "ACCUMULATE", "ACCUMULATE", "high"),
    (15, "KBANK.BK", "SELL",       "SELL",       "medium"),
    (18, "CPALL.BK", "BUY",        "BUY",        "high"),
    (22, "AOT.BK",   "REDUCE",     "REDUCE",     "low"),
    (25, "ADVANC.BK","BUY",        "BUY",        "high"),
    (27, "PTT.BK",   "SELL",       "SELL",       "medium"),
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _workday_dates(n: int, end: datetime | None = None) -> list[str]:
    """Return n Mon–Fri date strings ending on or before *end* (default: today UTC)."""
    anchor = end or datetime.utcnow()
    dates: list[str] = []
    d = anchor
    while len(dates) < n:
        if d.weekday() < 5:
            dates.append(d.strftime("%Y-%m-%d"))
        d -= timedelta(days=1)
    return list(reversed(dates))


def _gbm_path(
    start: float,
    n: int,
    daily_drift: float,
    daily_vol: float,
    rng: random.Random,
) -> list[float]:
    """Geometric Brownian Motion price path of length n."""
    path = [start]
    for _ in range(1, n):
        ret = daily_drift + daily_vol * rng.gauss(0, 1)
        path.append(path[-1] * (1.0 + ret))
    return path


def _correlated_paths(
    holdings: list[dict],
    n: int,
    market_corr: float,
    rng: random.Random,
) -> dict[str, list[float]]:
    """Simulate correlated stock paths with GBM.

    Each stock has an idiosyncratic and a market component; market_corr controls
    how tightly they co-move.
    """
    paths: dict[str, list[float]] = {}
    market_shocks = [rng.gauss(0, 1) for _ in range(n)]

    for h in holdings:
        p0 = h["avg_cost"] * rng.uniform(0.90, 1.12)
        daily_drift = 0.0003
        daily_vol = 0.015
        path = [p0]
        for i in range(1, n):
            shock = (
                market_corr * market_shocks[i]
                + math.sqrt(max(1.0 - market_corr ** 2, 0)) * rng.gauss(0, 1)
            )
            path.append(path[-1] * (1.0 + daily_drift + daily_vol * shock))
        paths[h["symbol"]] = path

    return paths


# ── Seeder functions ──────────────────────────────────────────────────────────

def seed_snapshots(
    db: Session,
    portfolio_id: int,
    workspace_id: int,
    dates: list[str],
    stock_paths: dict[str, list[float]],
    holdings: list[dict],
    dry_run: bool = False,
) -> int:
    """Upsert PortfolioSnapshot rows.  Returns number of rows written."""
    prev_value: float | None = None
    written = 0

    for day_idx, date_str in enumerate(dates):
        equity_value = sum(
            h["shares"] * stock_paths[h["symbol"]][day_idx]
            for h in holdings
        )
        total_cost = sum(h["shares"] * h["avg_cost"] for h in holdings)
        total_value = equity_value + STARTING_CASH
        unrealized_pnl = equity_value - total_cost

        # Sector market values
        sector_mv: dict[str, float] = {}
        holdings_list: list[dict] = []
        for h in holdings:
            price = stock_paths[h["symbol"]][day_idx]
            mv = h["shares"] * price
            cost = h["shares"] * h["avg_cost"]
            sector_mv[h["sector"]] = sector_mv.get(h["sector"], 0.0) + mv
            holdings_list.append({
                "symbol": h["symbol"],
                "shares": h["shares"],
                "avg_cost": round(h["avg_cost"], 4),
                "current_price": round(price, 4),
                "market_value": round(mv, 4),
                "unrealized_pnl": round(mv - cost, 4),
                "unrealized_pnl_pct": round((price - h["avg_cost"]) / h["avg_cost"] * 100, 2),
                "sector": h["sector"],
            })

        sector_breakdown = {
            s: round(v / total_value * 100, 2)
            for s, v in sector_mv.items()
        }
        daily_return_pct = (
            round((total_value - prev_value) / prev_value * 100, 4)
            if prev_value and prev_value > 0
            else None
        )

        if not dry_run:
            existing = db.query(PortfolioSnapshot).filter_by(
                portfolio_id=portfolio_id, snapshot_date=date_str
            ).first()
            snap_data = dict(
                total_value=round(total_value, 4),
                cash_balance=round(STARTING_CASH, 4),
                total_invested=round(total_cost, 4),
                unrealized_pnl=round(unrealized_pnl, 4),
                unrealized_pnl_pct=round(unrealized_pnl / total_cost * 100, 4) if total_cost > 0 else 0.0,
                realized_pnl=0.0,
                daily_return_pct=daily_return_pct,
                sector_breakdown_json=json.dumps(sector_breakdown),
                holdings_json=json.dumps(holdings_list),
                holdings_count=len(holdings),
            )
            if existing:
                for k, v in snap_data.items():
                    setattr(existing, k, v)
            else:
                db.add(PortfolioSnapshot(
                    workspace_id=workspace_id,
                    portfolio_id=portfolio_id,
                    snapshot_date=date_str,
                    **snap_data,
                ))

        prev_value = round(total_value, 4)
        written += 1

    if not dry_run:
        db.commit()
    return written


def seed_benchmarks(
    db: Session,
    dates: list[str],
    rng: random.Random,
    dry_run: bool = False,
) -> int:
    """Upsert BenchmarkPrice rows.  Returns total rows written."""
    written = 0
    for sym, cfg in _BENCH_CFG.items():
        path = _gbm_path(cfg["start"], len(dates), cfg["daily_drift"], cfg["daily_vol"], rng)
        for date_str, price in zip(dates, path):
            if not dry_run:
                existing = db.query(BenchmarkPrice).filter_by(
                    symbol=sym, price_date=date_str
                ).first()
                if existing:
                    existing.close_price = round(price, 4)
                else:
                    db.add(BenchmarkPrice(
                        symbol=sym,
                        price_date=date_str,
                        close_price=round(price, 4),
                    ))
            written += 1
        if not dry_run:
            db.commit()
    return written


def seed_signals(
    db: Session,
    workspace_id: int,
    dates: list[str],
    holdings: list[dict],
    rng: random.Random,
    dry_run: bool = False,
) -> int:
    """Insert SignalHistory rows based on the schedule.  Returns rows written."""
    sector_map = {h["symbol"]: h["sector"] for h in holdings}
    written = 0

    for day_off, symbol, action, signal, confidence in _SIGNAL_SCHEDULE:
        if day_off >= len(dates):
            continue
        date_str = dates[day_off]
        dt = datetime.fromisoformat(date_str).replace(hour=10, minute=30)
        if not dry_run:
            db.add(SignalHistory(
                workspace_id=workspace_id,
                session_id=f"seed-{day_off}",
                symbol=symbol,
                sector=sector_map.get(symbol, "Other"),
                action=action,
                signal=signal,
                signal_type="L2",
                confidence=confidence,
                ta_score=rng.randint(45, 82),
                fa_score=rng.randint(50, 85),
                score_at_signal=round(rng.uniform(55.0, 82.0), 1),
                price_at_signal=None,
                reasoning_snippet=f"[SEED] {action} signal for {symbol} on {date_str}.",
                recorded_at=dt,
            ))
        written += 1

    if not dry_run:
        db.commit()
    return written


def seed_transactions(
    db: Session,
    workspace_id: int,
    portfolio_id: int,
    dates: list[str],
    holdings: list[dict],
    dry_run: bool = False,
) -> int:
    """Insert INITIAL_POSITION + INITIAL_CASH transactions.  Returns rows written."""
    base_dt = datetime.fromisoformat(dates[0])
    written = 0

    if not dry_run:
        for h in holdings:
            db.add(Transaction(
                workspace_id=workspace_id,
                portfolio_id=portfolio_id,
                symbol=h["symbol"],
                transaction_type="INITIAL_POSITION",
                shares=float(h["shares"]),
                price_per_share=float(h["avg_cost"]),
                total_amount=float(h["shares"] * h["avg_cost"]),
                fees=0.0,
                taxes=0.0,
                currency="THB",
                exchange_rate=1.0,
                transaction_date=base_dt,
                sector=h["sector"],
            ))
            written += 1

        db.add(Transaction(
            workspace_id=workspace_id,
            portfolio_id=portfolio_id,
            symbol=None,
            transaction_type="INITIAL_CASH",
            shares=None,
            price_per_share=None,
            total_amount=STARTING_CASH,
            fees=0.0,
            transaction_date=base_dt,
        ))
        written += 1
        db.commit()
    else:
        written = len(holdings) + 1

    return written


def clear_existing(
    db: Session,
    portfolio_id: int,
    workspace_id: int,
    dates: list[str],
) -> None:
    """Remove seeded rows in the given date range."""
    db.query(PortfolioSnapshot).filter(
        PortfolioSnapshot.portfolio_id == portfolio_id,
        PortfolioSnapshot.snapshot_date >= dates[0],
        PortfolioSnapshot.snapshot_date <= dates[-1],
    ).delete(synchronize_session=False)

    db.query(SignalHistory).filter(
        SignalHistory.workspace_id == workspace_id,
        SignalHistory.session_id.like("seed-%"),
    ).delete(synchronize_session=False)

    db.query(Transaction).filter(
        Transaction.portfolio_id == portfolio_id,
        Transaction.transaction_type.in_(["INITIAL_POSITION", "INITIAL_CASH"]),
    ).delete(synchronize_session=False)

    for sym in _BENCH_CFG:
        db.query(BenchmarkPrice).filter(
            BenchmarkPrice.symbol == sym,
            BenchmarkPrice.price_date >= dates[0],
            BenchmarkPrice.price_date <= dates[-1],
        ).delete(synchronize_session=False)

    db.commit()
    print("  Cleared existing seed data.")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed Phase 3A analytics mock data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--portfolio-id", type=int, default=None,
        help="Target portfolio ID (default: first portfolio in DB)",
    )
    parser.add_argument(
        "--days", type=int, default=30,
        help="Number of trading days to generate (default: 30)",
    )
    parser.add_argument(
        "--clear", action="store_true",
        help="Delete existing seed rows before inserting",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print plan without writing to the database",
    )
    args = parser.parse_args()

    rng = random.Random(RANDOM_SEED)
    db: Session = SessionLocal()
    try:
        ws = get_default_workspace(db)

        # Resolve portfolio
        if args.portfolio_id:
            portfolio = db.query(Portfolio).filter_by(
                id=args.portfolio_id, workspace_id=ws.id
            ).first()
            if not portfolio:
                print(f"ERROR: Portfolio {args.portfolio_id} not found.")
                return
        else:
            portfolio = (
                db.query(Portfolio)
                .filter_by(workspace_id=ws.id)
                .order_by(Portfolio.id)
                .first()
            )
            if not portfolio:
                print("ERROR: No portfolios found. Create a portfolio first via the UI.")
                return

        print(f"Target portfolio: '{portfolio.name}' (ID={portfolio.id})")

        # Generate trading-day dates ending today
        dates = _workday_dates(args.days)
        print(f"Date range     : {dates[0]} → {dates[-1]} ({len(dates)} trading days)")
        print(f"Holdings       : {len(MOCK_HOLDINGS)} symbols")
        print(f"Benchmarks     : {', '.join(_BENCH_CFG)}")
        print(f"Signals        : {len([s for s in _SIGNAL_SCHEDULE if s[0] < len(dates)])} entries")

        if args.dry_run:
            print("\n[DRY RUN] No changes written.")
            return

        if args.clear:
            clear_existing(db, portfolio.id, ws.id, dates)

        # Simulate correlated price paths
        stock_paths = _correlated_paths(MOCK_HOLDINGS, len(dates), market_corr=0.55, rng=rng)

        n_snaps = seed_snapshots(db, portfolio.id, ws.id, dates, stock_paths, MOCK_HOLDINGS)
        print(f"  Snapshots written  : {n_snaps}")

        n_bench = seed_benchmarks(db, dates, rng)
        print(f"  Benchmark rows     : {n_bench}")

        n_sigs = seed_signals(db, ws.id, dates, MOCK_HOLDINGS, rng)
        print(f"  Signal rows        : {n_sigs}")

        n_txs = seed_transactions(db, ws.id, portfolio.id, dates, MOCK_HOLDINGS)
        print(f"  Transaction rows   : {n_txs}")

        print(
            f"\nDone.  "
            f"Visit /analytics/performance-stats?portfolio_id={portfolio.id}"
        )

    finally:
        db.close()


if __name__ == "__main__":
    main()
