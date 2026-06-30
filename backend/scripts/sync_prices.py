#!/usr/bin/env python3
"""Market data price sync script — Phase S.3.

Fetches daily closing prices for all active symbols (portfolio items +
watchlist + fixed benchmarks) via the configured market data provider
(PRICE_PROVIDER env var — see services/market_data/provider.py) and
upserts them into the benchmark_prices table.

Designed to run as a GitHub Actions job so the VPS application never needs
to make live yfinance calls.  Can also be run locally for backfills.

Usage
-----
    # Normal run (last 5 trading days, all active symbols)
    python backend/scripts/sync_prices.py

    # Backfill 2 years
    python backend/scripts/sync_prices.py --period 2y

    # Preview without writing to DB
    python backend/scripts/sync_prices.py --dry-run

    # Specific symbols (fixed benchmarks are always added to the list)
    python backend/scripts/sync_prices.py --symbols AAPL NVDA

Exit codes
----------
    0  — all symbols synced successfully (or dry-run)
    1  — at least one symbol failed
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime

# ── sys.path: add backend/ so "models", "services" resolve correctly ──────────
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(_BACKEND_DIR, ".env"))

from models.database import BenchmarkPrice, PortfolioItem, SessionLocal, Watchlist
from services.data_fetcher import normalize_dr_symbol
from services.market_data.provider import get_provider

_log = logging.getLogger(__name__)

# ── DR symbol normalisation (AAPL01.BK → AAPL, MICRON01.BK → MU) ──────────────
# Canonical implementation lives in services.data_fetcher so name-based DR
# aliases (e.g. MICRON → MU) stay in one place.
_normalize = normalize_dr_symbol


# ── Benchmark symbols always included in every sync run ───────────────────────
_FIXED_BENCHMARKS: list[str] = [
    "^SET.BK",   # SET Composite Index
    "^GSPC",     # S&P 500
    "QQQ",       # NASDAQ-100 ETF
    "GLD",       # Gold ETF (SPDR)
    "SPY",       # S&P 500 ETF
]

# Source tag written to benchmark_prices.data_source
_DATA_SOURCE = os.environ.get("SYNC_DATA_SOURCE", "yfinance_github_actions")


# ── Symbol collection ─────────────────────────────────────────────────────────

def _active_symbols(db) -> list[str]:
    """Return sorted union of all portfolio + watchlist + benchmark symbols."""
    portfolio = {row.symbol for row in db.query(PortfolioItem.symbol).all()}
    watchlist = {row.symbol for row in db.query(Watchlist.symbol).all()}
    combined = portfolio | watchlist | set(_FIXED_BENCHMARKS)
    return sorted(combined)


# ── DB upsert ─────────────────────────────────────────────────────────────────

def _upsert(
    db,
    symbol: str,
    price_date: str,
    close_price: float,
    dry_run: bool,
) -> None:
    now = datetime.utcnow()
    if dry_run:
        existing = db.query(BenchmarkPrice).filter_by(symbol=symbol, price_date=price_date).first()
        tag = "UPDATE" if existing else "INSERT"
        print(f"  [DRY RUN] {tag} {symbol} {price_date} close={close_price:.4f}")
        return

    entry = db.query(BenchmarkPrice).filter_by(symbol=symbol, price_date=price_date).first()
    if entry:
        entry.close_price = close_price
        entry.updated_at = now
        entry.data_source = _DATA_SOURCE
        entry.sync_status = "ok"
    else:
        db.add(BenchmarkPrice(
            symbol=symbol,
            price_date=price_date,
            close_price=close_price,
            updated_at=now,
            data_source=_DATA_SOURCE,
            sync_status="ok",
        ))


def _mark_error(db, symbol: str, error_msg: str) -> None:
    """Record a sync failure WITHOUT fabricating synthetic prices.

    Data-integrity rules:
      - Never overwrite a valid close_price with 0.0.
      - Never insert a fabricated 0.0 price row (close_price is NOT NULL, so a
        placeholder row cannot carry a NULL price — we simply don't insert one).
      - If today's row already holds a valid price (from an earlier successful
        run), mark it "stale" so freshness checks see the failed re-fetch while
        the price stays usable by analytics.
      - Absence of today's row + the error log IS the failure signal for
        freshness checks.
    """
    today = datetime.utcnow().strftime("%Y-%m-%d")
    now = datetime.utcnow()
    entry = db.query(BenchmarkPrice).filter_by(symbol=symbol, price_date=today).first()
    if entry:
        # Preserve the existing close_price; only update status metadata.
        entry.sync_status = "stale" if entry.close_price and entry.close_price > 0 else "error"
        entry.updated_at = now
        entry.data_source = _DATA_SOURCE
    else:
        _log.warning(
            "sync_failed symbol=%s date=%s error=%s — no row written (no synthetic prices)",
            symbol, today, error_msg,
        )


# ── Per-symbol sync ───────────────────────────────────────────────────────────

def _sync_symbol(
    db,
    provider: YahooFinanceProvider,
    symbol: str,
    period: str,
    dry_run: bool,
) -> dict:
    """Fetch history for one symbol and upsert each day's close. Returns status dict."""
    yf_symbol = _normalize(symbol)
    try:
        df = provider.get_history(yf_symbol, period=period, interval="1d")
        if df is None or df.empty:
            _log.warning("no_data symbol=%s yf_symbol=%s", symbol, yf_symbol)
            if not dry_run:
                _mark_error(db, symbol, "no_data_returned")
                db.commit()
            return {"symbol": symbol, "status": "no_data", "rows": 0}

        rows = 0
        for ts, row in df.iterrows():
            price_date = ts.strftime("%Y-%m-%d")
            close = float(row["Close"])
            if close > 0:
                _upsert(db, symbol, price_date, close, dry_run)
                rows += 1

        if not dry_run:
            db.commit()

        _log.info("synced symbol=%s yf_symbol=%s rows=%d", symbol, yf_symbol, rows)
        return {"symbol": symbol, "status": "ok", "rows": rows}

    except Exception as exc:
        _log.error("sync_error symbol=%s error=%s", symbol, exc, exc_info=True)
        if not dry_run:
            try:
                _mark_error(db, symbol, str(exc)[:200])
                db.commit()
            except Exception:
                db.rollback()
        return {"symbol": symbol, "status": "error", "error": str(exc)}


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Sync market price data to database")
    parser.add_argument(
        "--period", default="5d",
        help="yfinance history period (e.g. 5d, 30d, 1mo, 6mo, 1y, 2y). Default: 5d",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print planned writes without touching the database",
    )
    parser.add_argument(
        "--symbols", nargs="*",
        help=(
            "Extra symbols to sync; fixed benchmarks are always included "
            "(default: all active portfolio + watchlist + benchmarks)"
        ),
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )

    if not os.environ.get("DATABASE_URL"):
        _log.error("DATABASE_URL is not set — aborting")
        return 1

    db = SessionLocal()
    provider = get_provider()
    counts: dict[str, int] = {"ok": 0, "error": 0, "no_data": 0}

    try:
        if args.symbols:
            # Fixed benchmarks are ALWAYS synced — a manual --symbols override
            # must never silently drop QQQ/SPY/^SET.BK/^GSPC/GLD from the run.
            symbols = sorted(set(args.symbols) | set(_FIXED_BENCHMARKS))
            _log.info("explicit symbol list (+ fixed benchmarks): %s", symbols)
        else:
            symbols = _active_symbols(db)
            _log.info("collected %d symbols from DB", len(symbols))

        if args.dry_run:
            print(f"[DRY RUN] period={args.period}  symbols={len(symbols)}")
            print("-" * 60)

        for symbol in symbols:
            result = _sync_symbol(db, provider, symbol, args.period, args.dry_run)
            status = result["status"]
            counts[status] = counts.get(status, 0) + 1
            if status == "error":
                _log.error("  FAILED %s: %s", symbol, result.get("error", ""))

    finally:
        db.close()

    ok, err, nd = counts.get("ok", 0), counts.get("error", 0), counts.get("no_data", 0)
    print(f"\nSync complete: ok={ok}  error={err}  no_data={nd}  total={ok + err + nd}")

    if args.dry_run:
        print("[DRY RUN] No database writes performed.")
    return 1 if err > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
