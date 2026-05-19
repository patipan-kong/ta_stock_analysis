import math
import pandas as pd
import pandas_ta as ta
from services.data_fetcher import fetch_history


def _f(val) -> float | None:
    try:
        v = float(val)
        return None if (math.isnan(v) or math.isinf(v)) else round(v, 4)
    except (TypeError, ValueError):
        return None


def _i(val) -> int | None:
    try:
        v = float(val)
        return None if math.isnan(v) else int(v)
    except (TypeError, ValueError):
        return None


def _col(df: pd.DataFrame, prefix: str) -> str | None:
    matches = [c for c in df.columns if c.startswith(prefix)]
    return matches[0] if matches else None


def _compute_zigzag(highs: list, lows: list, deviation: float = 5.0, min_bars: int = 10) -> list:
    """
    ZigZag indicator. Returns interpolated price values between pivot points.
    deviation: minimum % reversal to confirm a new pivot (default 5%)
    min_bars:  minimum bars each leg must span (default 10)
    """
    n = len(highs)
    if n < 4:
        return [None] * n

    # Find initial direction: which deviates >= threshold first
    direction = None
    pivots: list[tuple[int, float]] = []

    for i in range(1, n):
        up_pct = (highs[i] - lows[0]) / lows[0] * 100 if lows[0] > 0 else 0
        dn_pct = (highs[0] - lows[i]) / highs[0] * 100 if highs[0] > 0 else 0
        if up_pct >= deviation:
            direction = 1          # uptrend → first pivot is a LOW
            pivots.append((0, lows[0]))
            break
        if dn_pct >= deviation:
            direction = -1         # downtrend → first pivot is a HIGH
            pivots.append((0, highs[0]))
            break

    if direction is None or not pivots:
        return [None] * n

    running_idx = pivots[0][0]
    running_price = pivots[0][1]

    for i in range(running_idx + 1, n):
        if direction == 1:         # tracking highs
            if highs[i] > running_price:
                running_price = highs[i]
                running_idx = i
            rev_pct = (running_price - lows[i]) / running_price * 100 if running_price > 0 else 0
            if rev_pct >= deviation and running_idx - pivots[-1][0] >= min_bars:
                pivots.append((running_idx, running_price))
                running_price = lows[i]
                running_idx = i
                direction = -1
        else:                      # tracking lows
            if lows[i] < running_price:
                running_price = lows[i]
                running_idx = i
            rev_pct = (highs[i] - running_price) / running_price * 100 if running_price > 0 else 0
            if rev_pct >= deviation and running_idx - pivots[-1][0] >= min_bars:
                pivots.append((running_idx, running_price))
                running_price = highs[i]
                running_idx = i
                direction = 1

    # Append final extreme if meaningfully past last confirmed pivot
    if running_idx != pivots[-1][0] and (running_idx - pivots[-1][0]) >= max(1, min_bars // 2):
        pivots.append((running_idx, running_price))

    if len(pivots) < 2:
        return [None] * n

    # Linear interpolation between consecutive pivots
    result: list = [None] * n
    for k in range(len(pivots) - 1):
        i1, p1 = pivots[k]
        i2, p2 = pivots[k + 1]
        if i2 <= i1:
            continue
        for j in range(i1, i2 + 1):
            t = (j - i1) / (i2 - i1)
            result[j] = round(p1 + t * (p2 - p1), 4)

    return result


def fetch_chart_data(symbol: str, period: str = "1d", interval: str = "5m") -> dict:
    df = fetch_history(symbol, period=period, interval=interval)
    if df is None or df.empty:
        return {"error": "No chart data available", "candles": []}

    df.ta.ema(length=20, append=True)
    df.ta.tema(length=9, append=True)
    df.ta.bbands(length=20, std=2.0, append=True)
    df.ta.rsi(length=14, append=True)
    # MACD 12 26 close 9 — EMA of close for fast/slow, EMA of MACD line for signal
    df.ta.macd(fast=12, slow=26, signal=9, append=True)

    ema20_col    = _col(df, "EMA_20")
    tema9_col    = _col(df, "TEMA_9")
    bbu_col      = _col(df, "BBU_")
    bbm_col      = _col(df, "BBM_")
    bbl_col      = _col(df, "BBL_")
    rsi_col      = _col(df, "RSI_")
    macd_col     = _col(df, "MACD_")
    macd_sig_col = _col(df, "MACDs_")
    macd_h_col   = _col(df, "MACDh_")

    highs = df["High"].tolist()
    lows  = df["Low"].tolist()
    zigzag_vals = _compute_zigzag(highs, lows, deviation=5.0, min_bars=10)

    candles = []
    for idx, (ts, row) in enumerate(df.iterrows()):
        candles.append({
            "time":        ts.isoformat(),
            "open":        _f(row.get("Open")),
            "high":        _f(row.get("High")),
            "low":         _f(row.get("Low")),
            "close":       _f(row.get("Close")),
            "volume":      _i(row.get("Volume")),
            "ema20":       _f(row[ema20_col])    if ema20_col    else None,
            "tema9":       _f(row[tema9_col])    if tema9_col    else None,
            "bb_upper":    _f(row[bbu_col])      if bbu_col      else None,
            "bb_middle":   _f(row[bbm_col])      if bbm_col      else None,
            "bb_lower":    _f(row[bbl_col])      if bbl_col      else None,
            "rsi":         _f(row[rsi_col])      if rsi_col      else None,
            "macd_line":   _f(row[macd_col])     if macd_col     else None,
            "macd_signal": _f(row[macd_sig_col]) if macd_sig_col else None,
            "macd_hist":   _f(row[macd_h_col])   if macd_h_col   else None,
            "zigzag":      zigzag_vals[idx],
        })

    return {
        "symbol":   symbol,
        "period":   period,
        "interval": interval,
        "candles":  candles,
    }
