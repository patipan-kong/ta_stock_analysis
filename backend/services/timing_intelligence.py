"""Phase 4C.6F — Timing Intelligence Layer.

Deterministic entry quality scoring for a basket of symbols.
No AI calls. No database writes. Pure measurable market signals.

Components
----------
  trend           (40%) — price vs SMA20 / SMA50
  momentum        (30%) — RSI(14)
  relative_strength (20%) — 20-day return vs SPY benchmark
  volume          (10%) — current day vs 20-day average volume

Public API
----------
compute_timing_score(symbol, price, sma20, sma50, sma200,
                     rsi, current_volume, avg_volume_20d,
                     stock_return_20d, benchmark_return_20d) -> StockTimingResult

score_timing_batch(symbols) -> list[StockTimingResult]
"""
from __future__ import annotations

import logging
from typing import Optional

import pandas as pd
import pandas_ta as ta
from pydantic import BaseModel

from services.data_fetcher import fetch_history
from services.symbol_normalization import get_yfinance_symbol

log = logging.getLogger(__name__)

_BENCHMARK_SYMBOL = "SPY"


# ── Response model ─────────────────────────────────────────────────────────────

class StockTimingResult(BaseModel):
    symbol: str
    timing_score: int
    timing_category: str        # STRONG | GOOD | NEUTRAL | WEAK | POOR
    trend_score: int            # 10 | 25 | 40
    momentum_score: int         # 5 | 10 | 20 | 30
    relative_strength_score: int  # 0 | 10 | 20
    volume_score: int           # 0 | 10
    momentum: str               # STRONG_UPTREND | UPTREND | SIDEWAYS | DOWNTREND | STRONG_DOWNTREND
    execution_priority: str     # HIGH | MEDIUM | LOW | DEFER
    reasons: list[str]          # max 3, deterministic
    data_available: bool


# ── Pure scoring functions (no I/O — fully testable) ──────────────────────────

def _trend_score(price: float, sma20: float | None, sma50: float | None) -> int:
    """40% component. Price position relative to SMA50 (and SMA20 as fallback)."""
    if sma50 is None:
        return 10
    if price > sma50:
        return 40
    if sma20 is not None and price > sma20:
        return 25  # between SMA20 and SMA50 (SMA20 < price < SMA50)
    return 10


def _momentum_score(rsi: float | None) -> int:
    """30% component. RSI(14) zones."""
    if rsi is None:
        return 20  # neutral default
    if 55 <= rsi <= 70:
        return 30
    if 45 <= rsi < 55:
        return 20
    if 35 <= rsi < 45:
        return 10
    return 5  # <35 (oversold) or >70 (overbought) both signal poor timing


def _relative_strength_score(
    stock_return: float | None, benchmark_return: float | None
) -> int:
    """20% component. 20-day excess return vs benchmark."""
    if stock_return is None or benchmark_return is None:
        return 10  # neutral
    diff = stock_return - benchmark_return
    if diff > 2.0:
        return 20  # outperforming by >2%
    if diff < -2.0:
        return 0   # underperforming by >2%
    return 10      # within ±2% = neutral


def _volume_score(current_volume: float | None, avg_volume_20d: float | None) -> int:
    """10% component. Volume expansion vs 20-day average."""
    if current_volume is None or avg_volume_20d is None or avg_volume_20d <= 0:
        return 0
    return 10 if current_volume > 1.2 * avg_volume_20d else 0


def _classify_momentum(
    sma20: float | None, sma50: float | None, sma200: float | None
) -> str:
    """SMA alignment → trend label."""
    if sma20 is None or sma50 is None:
        return "SIDEWAYS"
    # Strong trends require all three SMAs
    if sma200 is not None:
        if sma20 > sma50 > sma200:
            return "STRONG_UPTREND"
        if sma20 < sma50 < sma200:
            return "STRONG_DOWNTREND"
    # Sideways: within 1% band
    if abs(sma20 - sma50) <= sma50 * 0.01:
        return "SIDEWAYS"
    return "UPTREND" if sma20 > sma50 else "DOWNTREND"


def _timing_category(score: int) -> str:
    if score >= 80:
        return "STRONG"
    if score >= 60:
        return "GOOD"
    if score >= 40:
        return "NEUTRAL"
    if score >= 20:
        return "WEAK"
    return "POOR"


def _execution_priority(score: int) -> str:
    if score >= 80:
        return "HIGH"
    if score >= 60:
        return "MEDIUM"
    if score >= 40:
        return "LOW"
    return "DEFER"


def _generate_reasons(
    trend: int,
    rsi: float | None,
    volume: int,
    rel_strength: int,
) -> list[str]:
    """Build up to 3 deterministic plain-English reasons."""
    reasons: list[str] = []

    if trend == 40:
        reasons.append("Price above SMA50")
    elif trend == 25:
        reasons.append("Price between SMA20 and SMA50")
    else:
        reasons.append("Price below SMA50")

    if rsi is not None:
        if 55 <= rsi <= 70:
            reasons.append(f"RSI improving ({rsi:.0f})")
        elif rsi > 70:
            reasons.append(f"RSI overbought ({rsi:.0f})")
        elif rsi < 35:
            reasons.append(f"RSI oversold ({rsi:.0f})")

    if volume == 10:
        reasons.append("Volume expanding")

    if rel_strength == 20:
        reasons.append("Relative strength outperforming sector")
    elif rel_strength == 0:
        reasons.append("Relative strength underperforming sector")

    return reasons[:3]


# ── Public pure function ───────────────────────────────────────────────────────

def compute_timing_score(
    symbol: str,
    price: float | None,
    sma20: float | None,
    sma50: float | None,
    sma200: float | None,
    rsi: float | None,
    current_volume: float | None,
    avg_volume_20d: float | None,
    stock_return_20d: float | None,
    benchmark_return_20d: float | None,
) -> StockTimingResult:
    """Compute a deterministic 0-100 timing score from market indicators.

    All inputs are optional; missing values fall back to neutral or minimum scores.
    This function is pure and has no I/O — safe to call from unit tests.
    """
    if price is None:
        return StockTimingResult(
            symbol=symbol,
            timing_score=0,
            timing_category="POOR",
            trend_score=0,
            momentum_score=0,
            relative_strength_score=0,
            volume_score=0,
            momentum="SIDEWAYS",
            execution_priority="DEFER",
            reasons=["No price data available"],
            data_available=False,
        )

    trend = _trend_score(price, sma20, sma50)
    momentum = _momentum_score(rsi)
    rel_strength = _relative_strength_score(stock_return_20d, benchmark_return_20d)
    volume = _volume_score(current_volume, avg_volume_20d)

    total = max(0, min(100, trend + momentum + rel_strength + volume))

    return StockTimingResult(
        symbol=symbol,
        timing_score=total,
        timing_category=_timing_category(total),
        trend_score=trend,
        momentum_score=momentum,
        relative_strength_score=rel_strength,
        volume_score=volume,
        momentum=_classify_momentum(sma20, sma50, sma200),
        execution_priority=_execution_priority(total),
        reasons=_generate_reasons(trend, rsi, volume, rel_strength),
        data_available=True,
    )


# ── Market data helpers ────────────────────────────────────────────────────────

def _extract_indicators(df: pd.DataFrame) -> dict:
    """Derive all required indicators from a price history DataFrame."""
    if df is None or df.empty or len(df) < 5:
        return {}

    close = df["Close"].dropna()
    volume_col = df["Volume"].dropna() if "Volume" in df.columns else pd.Series(dtype=float)

    if len(close) < 5:
        return {}

    price = float(close.iloc[-1])

    sma20 = float(close.rolling(20).mean().iloc[-1]) if len(close) >= 20 else None
    sma50 = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else None
    sma200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else None

    rsi_s = ta.rsi(close, length=14)
    rsi: float | None = None
    if rsi_s is not None and not rsi_s.empty:
        val = rsi_s.iloc[-1]
        if pd.notna(val):
            rsi = float(val)

    current_volume: float | None = None
    avg_volume_20d: float | None = None
    if not volume_col.empty:
        current_volume = float(volume_col.iloc[-1])
        if len(volume_col) >= 20:
            avg_volume_20d = float(volume_col.rolling(20).mean().iloc[-1])

    stock_return_20d: float | None = None
    if len(close) >= 21:
        stock_return_20d = float((close.iloc[-1] / close.iloc[-21] - 1) * 100)

    return {
        "price": price,
        "sma20": sma20,
        "sma50": sma50,
        "sma200": sma200,
        "rsi": rsi,
        "current_volume": current_volume,
        "avg_volume_20d": avg_volume_20d,
        "stock_return_20d": stock_return_20d,
    }


def _fetch_benchmark_return(benchmark: str = _BENCHMARK_SYMBOL) -> float | None:
    try:
        df = fetch_history(benchmark, period="3mo", interval="1d")
        if df is None or df.empty:
            return None
        close = df["Close"].dropna()
        if len(close) < 21:
            return None
        return float((close.iloc[-1] / close.iloc[-21] - 1) * 100)
    except Exception as exc:
        log.warning("timing_intelligence: benchmark fetch failed: %s", exc)
        return None


# ── Public batch scorer ────────────────────────────────────────────────────────

def score_timing_batch(symbols: list[str]) -> list[StockTimingResult]:
    """Score entry timing for a list of symbols by fetching live market data.

    DR symbols (e.g. NVDA01) are normalized before fetching but the original
    symbol name is preserved in the result.
    """
    unique = list(dict.fromkeys(s.strip().upper() for s in symbols if s.strip()))
    if not unique:
        return []

    benchmark_return = _fetch_benchmark_return()

    results: list[StockTimingResult] = []
    for symbol in unique:
        try:
            fetch_sym = get_yfinance_symbol(symbol)
            df = fetch_history(fetch_sym, period="1y", interval="1d")
            log.info(
                "TIMING symbol=%s fetch=%s rows=%s",
                symbol, fetch_sym, len(df) if df is not None else 0,
            )
            indicators = _extract_indicators(df) if df is not None else {}

            result = compute_timing_score(
                symbol=symbol,
                price=indicators.get("price"),
                sma20=indicators.get("sma20"),
                sma50=indicators.get("sma50"),
                sma200=indicators.get("sma200"),
                rsi=indicators.get("rsi"),
                current_volume=indicators.get("current_volume"),
                avg_volume_20d=indicators.get("avg_volume_20d"),
                stock_return_20d=indicators.get("stock_return_20d"),
                benchmark_return_20d=benchmark_return,
            )
        except Exception as exc:
            log.warning("timing_intelligence: %s scoring failed: %s", symbol, exc)
            result = StockTimingResult(
                symbol=symbol,
                timing_score=0,
                timing_category="POOR",
                trend_score=0,
                momentum_score=0,
                relative_strength_score=0,
                volume_score=0,
                momentum="SIDEWAYS",
                execution_priority="DEFER",
                reasons=["Data unavailable"],
                data_available=False,
            )
        results.append(result)

    return results
