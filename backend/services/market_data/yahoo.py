import random
import threading
import time
import logging
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
import yfinance as yf

from .base import MarketDataProvider

_log = logging.getLogger(__name__)

try:
    from yfinance.exceptions import YFRateLimitError as _YFRateLimitError
except ImportError:
    _YFRateLimitError = None

# Max concurrent yfinance network calls across all threads.
# Keeps us well under Yahoo's undocumented per-IP rate limit.
_YF_SEMAPHORE = threading.Semaphore(5)

_CHUNK_SIZE = 15          # symbols per yf.download() batch
_CHUNK_DELAY = (0.3, 0.8)  # seconds between consecutive chunks (anti-burst)


def _is_rate_limit(e: Exception) -> bool:
    if _YFRateLimitError and isinstance(e, _YFRateLimitError):
        return True
    msg = str(e).lower()
    return "429" in msg or "rate limit" in msg or "too many requests" in msg


def _yf_retry(fn, *args, max_attempts: int = 3, **kwargs):
    """Exponential-backoff retry on Yahoo rate-limit errors only."""
    for attempt in range(max_attempts):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if _is_rate_limit(e) and attempt < max_attempts - 1:
                wait = (2 ** attempt) + random.uniform(1, 3)
                _log.warning(
                    "yfinance rate limit – retry in %.1fs (attempt %d/%d)",
                    wait, attempt + 1, max_attempts,
                )
                time.sleep(wait)
                continue
            raise


class YahooProvider(MarketDataProvider):
    """Concrete MarketDataProvider backed by yfinance (free, no API key)."""

    def get_quote(self, symbol: str) -> dict:
        with _YF_SEMAPHORE:
            try:
                ticker = yf.Ticker(symbol)
                df = _yf_retry(ticker.history, period="5d")
                current_price: float | None = None
                change_percent: float | None = None
                if df is not None and not df.empty:
                    current_price = float(df["Close"].iloc[-1])
                    if len(df) >= 2:
                        prev = float(df["Close"].iloc[-2])
                        if prev and prev != 0:
                            change_percent = round((current_price - prev) / prev * 100, 2)
                last_updated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                return {
                    "current_price": round(current_price, 4) if current_price is not None else None,
                    "change_percent": change_percent,
                    "last_updated": last_updated,
                }
            except Exception as e:
                _log.error("YahooProvider.get_quote(%s): %s", symbol, e)
                return {"current_price": None, "change_percent": None, "last_updated": None}

    def get_history(
        self, symbol: str, period: str = "6mo", interval: str = "1d"
    ) -> Optional[pd.DataFrame]:
        with _YF_SEMAPHORE:
            try:
                ticker = yf.Ticker(symbol)
                df = _yf_retry(ticker.history, period=period, interval=interval)
                if df is None or df.empty:
                    return None
                return df
            except Exception as e:
                _log.error("YahooProvider.get_history(%s, %s, %s): %s", symbol, period, interval, e)
                return None

    def get_fundamentals(self, symbol: str) -> dict:
        with _YF_SEMAPHORE:
            try:
                ticker = yf.Ticker(symbol)
                return _yf_retry(lambda: ticker.info) or {}
            except Exception as e:
                _log.error("YahooProvider.get_fundamentals(%s): %s", symbol, e)
                return {}

    def get_news(self, symbol: str) -> list[dict]:
        with _YF_SEMAPHORE:
            try:
                ticker = yf.Ticker(symbol)
                raw_news = _yf_retry(lambda: ticker.news) or []
                result = []
                for item in raw_news[:10]:
                    content = item.get("content", {})
                    result.append({
                        "title": content.get("title", ""),
                        "publisher": (
                            content.get("provider", {}).get("displayName", "")
                            if isinstance(content.get("provider"), dict) else ""
                        ),
                        "link": (
                            content.get("canonicalUrl", {}).get("url", "")
                            if isinstance(content.get("canonicalUrl"), dict) else ""
                        ),
                        "published": content.get("pubDate", ""),
                    })
                return result
            except Exception as e:
                _log.error("YahooProvider.get_news(%s): %s", symbol, e)
                return []

    def get_history_batch(
        self, symbols: list[str], period: str = "6mo", interval: str = "1d"
    ) -> dict[str, pd.DataFrame]:
        """Use yf.download() to fetch multiple symbols in one HTTP request per chunk.

        Chunks of up to _CHUNK_SIZE symbols are downloaded together.
        A small random delay between chunks provides anti-burst protection.
        """
        result: dict[str, pd.DataFrame] = {}
        chunks = [symbols[i:i + _CHUNK_SIZE] for i in range(0, len(symbols), _CHUNK_SIZE)]

        for idx, chunk in enumerate(chunks):
            if idx > 0:
                time.sleep(random.uniform(*_CHUNK_DELAY))

            with _YF_SEMAPHORE:
                try:
                    data = yf.download(
                        " ".join(chunk),
                        period=period,
                        interval=interval,
                        group_by="ticker",
                        auto_adjust=True,
                        progress=False,
                        threads=False,  # we manage concurrency ourselves
                    )
                    if data is None or data.empty:
                        continue

                    if len(chunk) == 1:
                        sym = chunk[0]
                        if not data.empty:
                            result[sym] = data
                    else:
                        for sym in chunk:
                            try:
                                sym_data = data[sym].dropna(how="all")
                                if not sym_data.empty:
                                    result[sym] = sym_data
                            except (KeyError, TypeError):
                                pass

                except Exception as e:
                    _log.warning("batch download failed for %s: %s – falling back to per-symbol", chunk, e)
                    for sym in chunk:
                        df = self.get_history(sym, period, interval)
                        if df is not None and not df.empty:
                            result[sym] = df

        return result
