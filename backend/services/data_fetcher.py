import re
import time
import random
import traceback
import yfinance as yf
import pandas as pd
from datetime import datetime, timezone
from typing import Optional

try:
    from yfinance.exceptions import YFRateLimitError as _YFRateLimitError
except ImportError:
    _YFRateLimitError = None

# DR (Depository Receipt) symbols traded on the Thai SET: letters + 2 digits + .BK
# e.g. AAPL01.BK, AMD08.BK, MSFT12.BK → base US ticker: AAPL, AMD, MSFT
_DR_RE = re.compile(r'^([A-Z]+)\d{2}\.BK$')

# In-memory price cache: {symbol: {current_price, change_percent, last_updated, cached_at}}
_price_cache: dict = {}
_PRICE_CACHE_TTL = 15 * 60  # 15 minutes


def normalize_dr_symbol(symbol: str) -> str:
    """Strip the DR digit-suffix so yfinance can find the underlying US company.

    AAPL01.BK → 'AAPL'   (DR → base ticker)
    PTT.BK    → 'PTT.BK' (unchanged — regular Thai stock)
    AAPL      → 'AAPL'   (unchanged — already a US ticker)
    """
    m = _DR_RE.match(symbol)
    return m.group(1) if m else symbol


def resolve_symbol(symbol: str) -> str:
    """Append .BK for Thai stocks if not already present and not a US ticker."""
    symbol = symbol.upper()
    if symbol.endswith(".BK"):
        return symbol
    return symbol


def _is_rate_limit(e: Exception) -> bool:
    if _YFRateLimitError and isinstance(e, _YFRateLimitError):
        return True
    msg = str(e).lower()
    return "429" in msg or "rate limit" in msg or "too many requests" in msg


def _yf_retry(fn, *args, max_attempts: int = 3, **kwargs):
    """Call fn(*args, **kwargs) with exponential backoff on rate-limit errors."""
    for attempt in range(max_attempts):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if _is_rate_limit(e) and attempt < max_attempts - 1:
                wait = (2 ** attempt) + random.uniform(1, 3)
                print(f"⚠️ yfinance rate limit, retry in {wait:.1f}s (attempt {attempt + 1}/{max_attempts})")
                time.sleep(wait)
                continue
            raise


def fetch_history(symbol: str, period: str = "6mo", interval: str = "1d") -> Optional[pd.DataFrame]:
    try:
        ticker = yf.Ticker(symbol)
        df = _yf_retry(ticker.history, period=period, interval=interval)
        if df is None or df.empty:
            return None
        return df
    except Exception:
        return None


def fetch_info(symbol: str) -> dict:
    """Fetch yfinance .info for a symbol.
    Callers are responsible for normalising DR symbols via normalize_dr_symbol() first."""
    try:
        ticker = yf.Ticker(symbol)
        return _yf_retry(lambda: ticker.info) or {}
    except Exception:
        return {}


def fetch_price_info(symbol: str) -> dict:
    # Return cached price if still fresh
    cached = _price_cache.get(symbol)
    if cached and (time.time() - cached["cached_at"]) < _PRICE_CACHE_TTL:
        return {
            "current_price": cached["current_price"],
            "change_percent": cached["change_percent"],
            "last_updated": cached["last_updated"],
        }

    # Jitter before hitting yfinance to reduce thundering-herd on bulk calls
    time.sleep(random.uniform(0.5, 1.5))

    try:
        ticker = yf.Ticker(symbol)
        # Use history() — fast_info.last_price triggers a full 1y history fetch internally
        df = _yf_retry(ticker.history, period="5d")

        current_price: float | None = None
        change_percent: float | None = None

        if df is not None and not df.empty:
            current_price = float(df["Close"].iloc[-1])
            if len(df) >= 2:
                prev_close = float(df["Close"].iloc[-2])
                if prev_close and prev_close != 0:
                    change_percent = round((current_price - prev_close) / prev_close * 100, 2)

        last_updated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        result = {
            "current_price": round(current_price, 4) if current_price is not None else None,
            "change_percent": change_percent,
            "last_updated": last_updated,
        }
        _price_cache[symbol] = {**result, "cached_at": time.time()}
        return result

    except Exception as e:
        print(f"❌ Error fetching price for {symbol}: {str(e)}")
        traceback.print_exc()
        return {"current_price": None, "change_percent": None, "last_updated": None}


def fetch_news(symbol: str) -> list[dict]:
    """Callers are responsible for normalising DR symbols via normalize_dr_symbol() first."""
    try:
        ticker = yf.Ticker(symbol)
        news = _yf_retry(lambda: ticker.news) or []
        result = []
        for item in news[:10]:
            content = item.get("content", {})
            result.append({
                "title": content.get("title", ""),
                "publisher": content.get("provider", {}).get("displayName", "") if isinstance(content.get("provider"), dict) else "",
                "link": content.get("canonicalUrl", {}).get("url", "") if isinstance(content.get("canonicalUrl"), dict) else "",
                "published": content.get("pubDate", ""),
            })
        return result
    except Exception:
        return []
