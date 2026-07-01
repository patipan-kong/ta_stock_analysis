#!/usr/bin/env python3
"""
Seed script for Phase 3B.1 — Factor Exposure Analysis development.

Populates MarketDataCache with realistic fundamental and price-history data
so GET /analytics/factor-exposure returns meaningful numbers without live
yfinance calls.  Covers both Thai SET (`.BK`) and US DR assets, intentionally
designed to test cross-market normalization:

  Thai equities — lower P/E ratios, local-currency yield, conservative growth
  US / DR stocks — higher P/E, lower dividend yield, stronger EPS growth

Holdings in the seed portfolio:
  SCB.BK    Financial  — Thai bank, high dividend, moderate growth
  PTT.BK    Energy     — Thai energy, high yield, cyclical
  KBANK.BK  Financial  — Thai bank, solid ROE
  CPALL.BK  Consumer   — Thai retail, moderate growth
  AOT.BK    Industrial — Thai airport, recovery growth
  ADVANC.BK Technology — Thai telco, consistent dividend
  AAPL      Technology — US tech (also used as DR base)
  NVDA      Technology — US mega-cap growth

Usage (run from the backend/ directory):
    python scripts/seed_factor_data.py
    python scripts/seed_factor_data.py --clear          # wipe then reseed
    python scripts/seed_factor_data.py --dry-run        # print plan, no writes
    python scripts/seed_factor_data.py --symbols AAPL NVDA   # specific symbols only
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import SessionLocal, MarketDataCache

# ── Seed configuration ────────────────────────────────────────────────────────

_TTL_FUND_H = 24   # hours; match data_fetcher._TTL_FUND

# yfinance info payload shape for each stock.
# Fields used by factor_engine:
#   Growth:   revenueGrowth, earningsGrowth
#   Value:    trailingPE, forwardPE, priceToBook, enterpriseToEbitda
#   Dividend: dividendYield, payoutRatio
#   Quality:  returnOnEquity, profitMargins, debtToEquity
# Additional fields kept for compatibility with fundamental agent:
#   marketCap, targetMeanPrice, sector, numberOfAnalystOpinions, currentPrice
STOCK_INFO: dict[str, dict] = {
    # ── Thai banks (high div, moderate growth, low PE) ────────────────────────
    "SCB.BK": {
        "symbol": "SCB.BK",
        "sector": "Financial",
        "industry": "Banks",
        "longName": "SCB X PCL",
        "currentPrice": 95.0,
        "regularMarketPrice": 95.0,
        "marketCap": 97_000_000_000,
        "trailingPE": 7.8,
        "forwardPE": 7.2,
        "priceToBook": 0.72,
        "enterpriseToEbitda": 5.1,
        "revenueGrowth": 0.06,        # 6% — stable Thai bank
        "earningsGrowth": 0.07,
        "earningsQuarterlyGrowth": 0.08,
        "returnOnEquity": 0.105,      # 10.5% ROE — solid
        "profitMargins": 0.32,        # 32% net margin — banks are high-margin
        "debtToEquity": 115.0,        # banks have high D/E by nature
        "dividendYield": 0.058,       # 5.8% — high-yield Thai bank
        "payoutRatio": 0.44,
        "targetMeanPrice": 108.0,
        "numberOfAnalystOpinions": 18,
        "trailingEps": 12.2,
        "beta": 0.85,
        "currency": "THB",
    },
    "KBANK.BK": {
        "symbol": "KBANK.BK",
        "sector": "Financial",
        "industry": "Banks",
        "longName": "Kasikorn Bank PCL",
        "currentPrice": 140.0,
        "regularMarketPrice": 140.0,
        "marketCap": 133_000_000_000,
        "trailingPE": 8.4,
        "forwardPE": 7.9,
        "priceToBook": 0.68,
        "enterpriseToEbitda": 5.8,
        "revenueGrowth": 0.05,
        "earningsGrowth": 0.09,
        "earningsQuarterlyGrowth": 0.10,
        "returnOnEquity": 0.115,
        "profitMargins": 0.34,
        "debtToEquity": 125.0,
        "dividendYield": 0.048,       # 4.8%
        "payoutRatio": 0.40,
        "targetMeanPrice": 158.0,
        "numberOfAnalystOpinions": 20,
        "trailingEps": 16.7,
        "beta": 0.88,
        "currency": "THB",
    },
    # ── Thai energy (high yield, cyclical, PE compression) ────────────────────
    "PTT.BK": {
        "symbol": "PTT.BK",
        "sector": "Energy",
        "industry": "Oil & Gas Integrated",
        "longName": "PTT PCL",
        "currentPrice": 32.5,
        "regularMarketPrice": 32.5,
        "marketCap": 580_000_000_000,
        "trailingPE": 9.2,
        "forwardPE": 8.8,
        "priceToBook": 0.92,
        "enterpriseToEbitda": 6.3,
        "revenueGrowth": -0.04,       # slight revenue decline — post-commodity cycle
        "earningsGrowth": -0.06,
        "earningsQuarterlyGrowth": -0.03,
        "returnOnEquity": 0.088,
        "profitMargins": 0.04,        # thin margin on integrated energy
        "debtToEquity": 88.0,
        "dividendYield": 0.062,       # 6.2% — high yield
        "payoutRatio": 0.57,
        "targetMeanPrice": 36.0,
        "numberOfAnalystOpinions": 22,
        "trailingEps": 3.5,
        "beta": 1.05,
        "currency": "THB",
    },
    # ── Thai consumer (moderate growth, low yield) ────────────────────────────
    "CPALL.BK": {
        "symbol": "CPALL.BK",
        "sector": "Consumer Defensive",
        "industry": "Grocery Stores",
        "longName": "CP ALL PCL",
        "currentPrice": 58.0,
        "regularMarketPrice": 58.0,
        "marketCap": 257_000_000_000,
        "trailingPE": 22.5,
        "forwardPE": 19.8,
        "priceToBook": 3.2,
        "enterpriseToEbitda": 12.4,
        "revenueGrowth": 0.08,        # solid consumer growth
        "earningsGrowth": 0.10,
        "earningsQuarterlyGrowth": 0.11,
        "returnOnEquity": 0.145,
        "profitMargins": 0.035,       # thin retail margins
        "debtToEquity": 195.0,        # leveraged from Makro acquisition
        "dividendYield": 0.015,       # 1.5% — growth company, low yield
        "payoutRatio": 0.34,
        "targetMeanPrice": 64.0,
        "numberOfAnalystOpinions": 16,
        "trailingEps": 2.58,
        "beta": 0.72,
        "currency": "THB",
    },
    # ── Thai airport (recovery growth story, low div while reinvesting) ───────
    "AOT.BK": {
        "symbol": "AOT.BK",
        "sector": "Industrials",
        "industry": "Airport Services",
        "longName": "Airports of Thailand PCL",
        "currentPrice": 65.0,
        "regularMarketPrice": 65.0,
        "marketCap": 885_000_000_000,
        "trailingPE": 35.2,           # premium for recovery play
        "forwardPE": 28.5,
        "priceToBook": 5.8,
        "enterpriseToEbitda": 22.1,
        "revenueGrowth": 0.22,        # strong recovery growth (travel rebound)
        "earningsGrowth": 0.45,
        "earningsQuarterlyGrowth": 0.48,
        "returnOnEquity": 0.168,
        "profitMargins": 0.28,        # high-margin airport monopoly
        "debtToEquity": 52.0,
        "dividendYield": 0.008,       # 0.8% — reinvesting for expansion
        "payoutRatio": 0.28,
        "targetMeanPrice": 72.0,
        "numberOfAnalystOpinions": 24,
        "trailingEps": 1.85,
        "beta": 1.15,
        "currency": "THB",
    },
    # ── Thai telco (stable div, low growth) ───────────────────────────────────
    "ADVANC.BK": {
        "symbol": "ADVANC.BK",
        "sector": "Communication Services",
        "industry": "Telecom Services",
        "longName": "Advanced Info Service PCL",
        "currentPrice": 200.0,
        "regularMarketPrice": 200.0,
        "marketCap": 236_000_000_000,
        "trailingPE": 18.5,
        "forwardPE": 17.8,
        "priceToBook": 6.2,
        "enterpriseToEbitda": 8.9,
        "revenueGrowth": 0.04,        # slow steady growth — mature telco
        "earningsGrowth": 0.03,
        "earningsQuarterlyGrowth": 0.04,
        "returnOnEquity": 0.335,      # very high ROE — asset-light
        "profitMargins": 0.195,
        "debtToEquity": 42.0,
        "dividendYield": 0.042,       # 4.2% — consistent telco yield
        "payoutRatio": 0.78,          # high but sustainable for telco
        "targetMeanPrice": 218.0,
        "numberOfAnalystOpinions": 20,
        "trailingEps": 10.8,
        "beta": 0.55,
        "currency": "THB",
    },
    # ── US tech — Apple (quality growth, low yield, premium valuation) ────────
    "AAPL": {
        "symbol": "AAPL",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "longName": "Apple Inc.",
        "currentPrice": 195.0,
        "regularMarketPrice": 195.0,
        "marketCap": 3_000_000_000_000,
        "trailingPE": 30.5,
        "forwardPE": 27.2,
        "priceToBook": 48.5,          # negative book value → high P/B
        "enterpriseToEbitda": 22.8,
        "revenueGrowth": 0.04,        # mature mega-cap
        "earningsGrowth": 0.08,
        "earningsQuarterlyGrowth": 0.06,
        "returnOnEquity": 1.60,       # capped at 5.0 in engine; shows buyback power
        "profitMargins": 0.254,
        "debtToEquity": 180.0,        # capital structure optimization
        "dividendYield": 0.005,       # 0.5% — token yield
        "payoutRatio": 0.15,
        "targetMeanPrice": 215.0,
        "numberOfAnalystOpinions": 42,
        "trailingEps": 6.40,
        "beta": 1.18,
        "currency": "USD",
    },
    # ── US semi — NVIDIA (hyper-growth, no div, sky-high valuation) ───────────
    "NVDA": {
        "symbol": "NVDA",
        "sector": "Technology",
        "industry": "Semiconductors",
        "longName": "NVIDIA Corporation",
        "currentPrice": 875.0,
        "regularMarketPrice": 875.0,
        "marketCap": 2_150_000_000_000,
        "trailingPE": 62.0,
        "forwardPE": 38.5,
        "priceToBook": 35.2,
        "enterpriseToEbitda": 48.5,
        "revenueGrowth": 1.22,        # 122% YoY — AI super-cycle
        "earningsGrowth": 3.48,
        "earningsQuarterlyGrowth": 2.61,
        "returnOnEquity": 1.23,       # capped at 5.0 in engine
        "profitMargins": 0.556,       # 55.6% net margin
        "debtToEquity": 44.0,
        "dividendYield": 0.0002,      # negligible
        "payoutRatio": 0.01,
        "targetMeanPrice": 1050.0,
        "numberOfAnalystOpinions": 55,
        "trailingEps": 14.10,
        "beta": 1.65,
        "currency": "USD",
    },
}

# Momentum: synthetic 90-day daily closes (generates a realistic price series)
# Format: {"symbol": {"base": start_price, "trend": daily_drift, "noise": stddev}}
MOMENTUM_CONFIG: dict[str, dict] = {
    "SCB.BK":   {"base": 90.0,   "trend":  0.0003, "noise": 0.012},
    "KBANK.BK": {"base": 136.0,  "trend":  0.0001, "noise": 0.013},
    "PTT.BK":   {"base": 33.5,   "trend": -0.0004, "noise": 0.015},  # slight downtrend
    "CPALL.BK": {"base": 54.0,   "trend":  0.0005, "noise": 0.010},
    "AOT.BK":   {"base": 59.0,   "trend":  0.0012, "noise": 0.014},  # strong uptrend
    "ADVANC.BK":{"base": 192.0,  "trend":  0.0002, "noise": 0.009},
    "AAPL":     {"base": 182.0,  "trend":  0.0008, "noise": 0.011},
    "NVDA":     {"base": 620.0,  "trend":  0.0025, "noise": 0.022},  # strong uptrend
}

# ── Synthetic price-history builder ──────────────────────────────────────────

def _build_price_history(symbol: str, days: int = 90) -> list[dict]:
    """Generate synthetic daily OHLCV rows for the momentum calculation."""
    import random
    cfg   = MOMENTUM_CONFIG.get(symbol, {"base": 100.0, "trend": 0.0, "noise": 0.01})
    base  = cfg["base"]
    drift = cfg["trend"]
    noise = cfg["noise"]

    rng   = random.Random(hash(symbol) % 2**31)
    price = base
    today = datetime.utcnow().date()
    rows  = []

    for i in range(days - 1, -1, -1):
        day  = today - timedelta(days=i)
        # Skip weekends
        if day.weekday() >= 5:
            continue
        change = drift + rng.gauss(0, noise)
        price  = max(price * (1 + change), 0.01)
        high   = price * (1 + abs(rng.gauss(0, noise / 2)))
        low    = price * (1 - abs(rng.gauss(0, noise / 2)))
        rows.append({
            "Date":   day.isoformat(),
            "Open":   round(price * (1 + rng.gauss(0, noise / 4)), 4),
            "High":   round(high, 4),
            "Low":    round(low, 4),
            "Close":  round(price, 4),
            "Volume": int(rng.uniform(500_000, 5_000_000)),
        })

    return rows


# ── DB write helpers ──────────────────────────────────────────────────────────

def _upsert_cache(db, symbol: str, cache_type: str, payload: dict, ttl_h: int) -> None:
    now     = datetime.utcnow()
    expires = now + timedelta(hours=ttl_h)
    payload_str = json.dumps(payload, default=str)

    entry = (
        db.query(MarketDataCache)
        .filter_by(symbol=symbol, cache_type=cache_type)
        .first()
    )
    if entry:
        entry.payload_json = payload_str
        entry.fetched_at   = now
        entry.expires_at   = expires
        entry.hit_count    = 0
    else:
        db.add(MarketDataCache(
            symbol=symbol,
            cache_type=cache_type,
            payload_json=payload_str,
            fetched_at=now,
            expires_at=expires,
            hit_count=0,
        ))


def _delete_cache(db, symbol: str, cache_type: str) -> bool:
    entry = (
        db.query(MarketDataCache)
        .filter_by(symbol=symbol, cache_type=cache_type)
        .first()
    )
    if entry:
        db.delete(entry)
        return True
    return False


# ── Main seeding logic ────────────────────────────────────────────────────────

def seed(
    symbols:  list[str] | None = None,
    clear:    bool = False,
    dry_run:  bool = False,
) -> None:
    """Run the seed operation."""
    target_symbols = symbols or list(STOCK_INFO.keys())
    unknown = [s for s in target_symbols if s not in STOCK_INFO]
    if unknown:
        print(f"[warn] Unknown symbols (no mock data): {unknown}")
        target_symbols = [s for s in target_symbols if s in STOCK_INFO]

    if not target_symbols:
        print("[error] No valid symbols to seed.")
        return

    print(f"Seed plan: {len(target_symbols)} symbol(s) — {', '.join(target_symbols)}")
    print(f"  clear={clear}  dry_run={dry_run}")

    if dry_run:
        for sym in target_symbols:
            info = STOCK_INFO[sym]
            mom  = MOMENTUM_CONFIG.get(sym)
            print(f"\n  {sym}  ({info['sector']})")
            print(f"    PE={info.get('trailingPE')}  ROE={info.get('returnOnEquity')}  "
                  f"DivYield={info.get('dividendYield')}  RevGrowth={info.get('revenueGrowth')}")
            if mom:
                hist = _build_price_history(sym)
                if len(hist) >= 30:
                    p0 = hist[-30]["Close"]
                    p_end = hist[-1]["Close"]
                    r30 = (p_end - p0) / p0
                    print(f"    30d return (simulated): {r30:+.2%}")
        print("\n[dry-run] No changes written.")
        return

    db = SessionLocal()
    written = 0
    try:
        for sym in target_symbols:
            info = STOCK_INFO[sym]
            hist_rows = _build_price_history(sym)

            if clear:
                _delete_cache(db, sym, "fundamental")
                _delete_cache(db, sym, "history:3mo:1d")
                _delete_cache(db, sym, "quote")
                print(f"  [clear] {sym}")

            # Fundamental info (24h TTL)
            _upsert_cache(db, sym, "fundamental", info, _TTL_FUND_H)

            # Price history: 3mo daily (15min TTL in live, 24h for seed stability)
            hist_payload = {
                "columns": ["Date", "Open", "High", "Low", "Close", "Volume"],
                "data": [[r["Date"], r["Open"], r["High"], r["Low"], r["Close"], r["Volume"]]
                         for r in hist_rows],
            }
            _upsert_cache(db, sym, "history:3mo:1d", hist_payload, _TTL_FUND_H)

            # Quote cache
            last_price = hist_rows[-1]["Close"] if hist_rows else info.get("currentPrice", 0)
            prev_price = hist_rows[-2]["Close"] if len(hist_rows) >= 2 else last_price
            quote = {
                "current_price":   last_price,
                "previous_close":  prev_price,
                "last_updated":    datetime.utcnow().isoformat() + "Z",
            }
            _upsert_cache(db, sym, "quote", quote, 1)  # 1h TTL

            written += 1
            print(f"  [seed] {sym}  PE={info.get('trailingPE')}  "
                  f"DivYield={info.get('dividendYield', 0):.1%}  "
                  f"RevGrowth={info.get('revenueGrowth', 0):+.0%}  "
                  f"Bars={len(hist_rows)}")

        db.commit()
        print(f"\nDone. {written} symbol(s) seeded into MarketDataCache.")
        print("GET /analytics/factor-exposure?portfolio_id=<id>  will now use seeded data.")

    except Exception as exc:
        db.rollback()
        print(f"[error] {exc}")
        raise
    finally:
        db.close()


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed MarketDataCache with mock factor data for Phase 3B.1 dev.",
    )
    parser.add_argument(
        "--symbols", nargs="+", metavar="SYM",
        help="Seed only these symbols (default: all 8 mock holdings).",
    )
    parser.add_argument(
        "--clear", action="store_true",
        help="Delete existing cache entries for target symbols before writing.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print the seed plan without writing to the DB.",
    )
    args = parser.parse_args()
    seed(
        symbols=args.symbols,
        clear=args.clear,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
