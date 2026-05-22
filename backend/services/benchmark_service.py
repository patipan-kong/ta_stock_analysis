"""Benchmark price fetching and storage.

Fetches daily closing prices for index/ETF benchmarks via yfinance and
persists them in the benchmark_prices table for use in the
performance-comparison analytics endpoint.

Default benchmarks:
  ^SET.BK  — Thai SET Composite Index (Yahoo Finance ticker)
  QQQ   — Invesco QQQ Trust (NASDAQ-100 ETF)
"""
import asyncio
import logging
from datetime import date, datetime, timedelta

import yfinance as yf
from sqlalchemy.orm import Session

from models.database import BenchmarkPrice

log = logging.getLogger(__name__)

DEFAULT_BENCHMARKS = ["^SET.BK", "QQQ"]

# Human-readable labels for known benchmark symbols.
_BENCHMARK_LABELS: dict[str, str] = {
    "^SET.BK": "SET Index",
    "^SET": "SET TRI",  # Total Return Index — different from the price index
    "QQQ": "QQQ (NASDAQ-100)",
    "SPY": "S&P 500 (SPY)",
    "^GSPC": "S&P 500",
    "^DJI": "Dow Jones",
}


def benchmark_label(symbol: str) -> str:
    return _BENCHMARK_LABELS.get(symbol, symbol)


def bench_key(symbol: str) -> str:
    """Sanitize a yfinance symbol into a safe JSON key for recharts data rows.

    Examples: "^SET" → "bm_SET",  "QQQ" → "bm_QQQ",  "^GSPC" → "bm_GSPC"
    """
    return "bm_" + symbol.lstrip("^").replace(".", "_")


# ── Single-date fetch (used by the daily snapshot job) ───────────────────────

def _fetch_close_on_date(symbol: str, price_date: str) -> float | None:
    """Return the closing price for *symbol* on or before *price_date*.

    Requests a 6-day window ending on the day after *price_date* so that the
    last available trading-day close is returned even when *price_date* falls
    on a weekend or holiday.
    """
    d = date.fromisoformat(price_date)
    start = (d - timedelta(days=6)).isoformat()
    end = (d + timedelta(days=1)).isoformat()  # yfinance end is exclusive
    try:
        hist = yf.Ticker(symbol).history(start=start, end=end, interval="1d")
        if hist.empty:
            log.warning("benchmark_service: no data for %s on %s", symbol, price_date)
            return None
        return float(hist["Close"].iloc[-1])
    except Exception as exc:
        log.error("benchmark_service: fetch failed %s %s — %s", symbol, price_date, exc)
        return None


# ── Upsert helper (sync) ──────────────────────────────────────────────────────

def _upsert(db: Session, symbol: str, price_date: str, close_price: float) -> None:
    existing = db.query(BenchmarkPrice).filter_by(
        symbol=symbol, price_date=price_date
    ).first()
    if existing:
        existing.close_price = close_price
    else:
        db.add(BenchmarkPrice(symbol=symbol, price_date=price_date, close_price=close_price))


# ── Daily fetch (called from snapshot_scheduler after portfolio snapshots) ────

async def fetch_and_store_benchmarks(
    db: Session,
    symbols: list[str] | None = None,
    price_date: str | None = None,
) -> dict[str, float | None]:
    """Fetch today's close for each benchmark symbol and upsert into the DB.

    Args:
        db: Active SQLAlchemy session.
        symbols: yfinance ticker symbols. Defaults to DEFAULT_BENCHMARKS.
        price_date: "YYYY-MM-DD". Defaults to today UTC.

    Returns:
        {symbol: close_price_or_None}
    """
    if symbols is None:
        symbols = DEFAULT_BENCHMARKS
    if price_date is None:
        price_date = datetime.utcnow().strftime("%Y-%m-%d")

    prices: list[float | None | BaseException] = await asyncio.gather(
        *[asyncio.to_thread(_fetch_close_on_date, sym, price_date) for sym in symbols],
        return_exceptions=True,
    )

    results: dict[str, float | None] = {}
    for sym, price in zip(symbols, prices):
        if isinstance(price, BaseException):
            log.error("benchmark_service: gather exception for %s: %s", sym, price)
            results[sym] = None
        elif price is not None:
            _upsert(db, sym, price_date, price)
            results[sym] = price
            log.info("benchmark_service: stored %s @ %s = %.4f", sym, price_date, price)
        else:
            results[sym] = None

    db.commit()
    return results


# ── Historical backfill (admin endpoint) ─────────────────────────────────────

async def backfill_benchmarks(
    db: Session,
    symbols: list[str] | None = None,
    from_date: str = "2026-05-21",
    to_date: str | None = None,
) -> list[dict]:
    """Bulk-fetch and store benchmark prices for a date range.

    Uses a single yfinance history() call per symbol to retrieve all trading
    days in the range at once, then upserts each row into benchmark_prices.
    Existing rows are overwritten to correct any previously stored stale prices.

    Returns a list of per-symbol result dicts.
    """
    if symbols is None:
        symbols = DEFAULT_BENCHMARKS
    if to_date is None:
        to_date = datetime.utcnow().strftime("%Y-%m-%d")

    end_exclusive = (date.fromisoformat(to_date) + timedelta(days=1)).isoformat()
    results: list[dict] = []

    for sym in symbols:
        try:
            hist = await asyncio.to_thread(
                yf.Ticker(sym).history,
                start=from_date,
                end=end_exclusive,
                interval="1d",
            )
            if hist.empty:
                results.append({"symbol": sym, "status": "no_data", "rows": 0})
                log.warning("benchmark_service: backfill — no data for %s", sym)
                continue

            rows_written = 0
            for idx, row in hist.iterrows():
                pd_str = idx.strftime("%Y-%m-%d")
                _upsert(db, sym, pd_str, float(row["Close"]))
                rows_written += 1

            db.commit()
            results.append({"symbol": sym, "status": "ok", "rows": rows_written})
            log.info("benchmark_service: backfill %s — %d rows", sym, rows_written)

        except Exception as exc:
            db.rollback()
            log.error("benchmark_service: backfill failed %s — %s", sym, exc)
            results.append({"symbol": sym, "status": "error", "error": str(exc), "rows": 0})

        await asyncio.sleep(0.3)

    return results
