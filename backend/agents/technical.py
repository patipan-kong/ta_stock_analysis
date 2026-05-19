import pandas as pd
import pandas_ta as ta
from services.data_fetcher import fetch_history


def _score_timeframe(df: pd.DataFrame, use_macd: bool = True) -> dict:
    """Score one timeframe's OHLCV DataFrame; return indicators + score."""
    score = 0
    notes: list[str] = []
    rsi: float | None = None
    macd_signal = "neutral"
    bb_position = "middle"
    trend = "sideways"

    # ── RSI ──────────────────────────────────────────────────────────────────
    rsi_s = ta.rsi(df["Close"], length=14)
    if rsi_s is not None and not rsi_s.empty:
        rsi = float(rsi_s.iloc[-1])
        if rsi < 30:
            score += 2; notes.append(f"RSI oversold ({rsi:.1f})")
        elif rsi < 45:
            score += 1; notes.append(f"RSI mild oversold ({rsi:.1f})")
        elif rsi > 70:
            score -= 2; notes.append(f"RSI overbought ({rsi:.1f})")
        elif rsi > 55:
            score -= 1; notes.append(f"RSI mild overbought ({rsi:.1f})")
        else:
            notes.append(f"RSI neutral ({rsi:.1f})")

    # ── MACD (skip if < 27 bars or disabled) ─────────────────────────────────
    if use_macd and len(df) >= 27:
        macd_df = ta.macd(df["Close"], fast=12, slow=26, signal=9)
        if macd_df is not None and not macd_df.empty:
            macd_col = [c for c in macd_df.columns if c.startswith("MACD_") and "signal" not in c.lower() and "h" not in c.lower()]
            sig_col  = [c for c in macd_df.columns if "MACDs" in c]
            if macd_col and sig_col:
                mv, sv = macd_df[macd_col[0]].iloc[-1], macd_df[sig_col[0]].iloc[-1]
                pv, ps = macd_df[macd_col[0]].iloc[-2], macd_df[sig_col[0]].iloc[-2]
                if mv > sv and pv <= ps:
                    macd_signal = "bullish"; score += 2; notes.append("MACD bullish crossover")
                elif mv < sv and pv >= ps:
                    macd_signal = "bearish"; score -= 2; notes.append("MACD bearish crossover")
                elif mv > sv:
                    macd_signal = "bullish"; score += 1; notes.append("MACD above signal")
                else:
                    macd_signal = "bearish"; score -= 1; notes.append("MACD below signal")

    # ── Bollinger Bands ───────────────────────────────────────────────────────
    bb_len = min(20, max(10, len(df) // 3))
    bb_df = ta.bbands(df["Close"], length=bb_len)
    if bb_df is not None and not bb_df.empty:
        upper_col = [c for c in bb_df.columns if "BBU" in c]
        lower_col = [c for c in bb_df.columns if "BBL" in c]
        if upper_col and lower_col:
            close = df["Close"].iloc[-1]
            if close <= bb_df[lower_col[0]].iloc[-1]:
                bb_position = "lower"; score += 1; notes.append("Price at lower BB")
            elif close >= bb_df[upper_col[0]].iloc[-1]:
                bb_position = "upper"; score -= 1; notes.append("Price at upper BB")
            else:
                notes.append("Price in BB middle zone")

    # ── EMA trend ────────────────────────────────────────────────────────────
    lengths = [20, 50, 200] if len(df) >= 200 else ([20, 50] if len(df) >= 50 else [])
    if lengths:
        ema_vals = [ta.ema(df["Close"], length=l).iloc[-1] for l in lengths]
        close = df["Close"].iloc[-1]
        if all(ema_vals[i] > ema_vals[i + 1] for i in range(len(ema_vals) - 1)) and close > ema_vals[0]:
            trend = "uptrend"; score += 2; notes.append(f"Strong uptrend (EMA{lengths} aligned ↑)")
        elif all(ema_vals[i] < ema_vals[i + 1] for i in range(len(ema_vals) - 1)) and close < ema_vals[0]:
            trend = "downtrend"; score -= 2; notes.append(f"Strong downtrend (EMA{lengths} aligned ↓)")
        elif close > ema_vals[1]:
            trend = "uptrend"; score += 1; notes.append(f"Price above EMA{lengths[1]}")
        else:
            notes.append("Mixed EMA signals")

    return {
        "rsi": round(rsi, 2) if rsi is not None else None,
        "macd_signal": macd_signal,
        "bb_position": bb_position,
        "trend": trend,
        "score": score,
        "summary": ", ".join(notes) if notes else "no signals",
    }


def analyze_technical(symbol: str) -> dict:
    """
    Dual-timeframe analysis:
      Short-term — 1-month daily  (momentum / entry timing, weight 40% of TA)
      Long-term  — 1-year weekly  (primary trend / structure, weight 60% of TA)
    Composite TA score = round(0.4 × ST_score + 0.6 × LT_score)
    Backward-compatible fields are drawn from the long-term frame (primary).
    """
    st_df = fetch_history(symbol, "1mo", "1d")
    lt_df = fetch_history(symbol, "1y",  "1wk")

    st: dict | None = _score_timeframe(st_df, use_macd=False) if st_df is not None and len(st_df) >= 14 else None
    lt: dict | None = _score_timeframe(lt_df, use_macd=True)  if lt_df is not None and len(lt_df) >= 27 else None

    if st is None and lt is None:
        return {"error": "data unavailable"}

    st_score = st["score"] if st else 0
    lt_score = lt["score"] if lt else 0
    composite = round(0.4 * st_score + 0.6 * lt_score)

    primary = lt or st  # long-term is primary; fall back to short-term

    return {
        "symbol": symbol,
        # ── backward-compatible flat fields (from long-term / primary) ──
        "rsi":          primary["rsi"],
        "macd_signal":  primary["macd_signal"],
        "bb_position":  primary["bb_position"],
        "trend":        primary["trend"],
        "ta_score":     composite,
        "ta_summary": (
            f"ST 1mo: {st['summary'] if st else 'N/A'} "
            f"| LT 1y-wk: {lt['summary'] if lt else 'N/A'}"
        ),
        # ── dual-timeframe detail ──
        "short_term": {
            "period": "1mo daily",
            "score":  st_score,
            **(st if st else {"error": "insufficient data"}),
        },
        "long_term": {
            "period": "1y weekly",
            "score":  lt_score,
            **(lt if lt else {"error": "insufficient data"}),
        },
    }
