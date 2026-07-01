import random
import threading
import time
import logging
from datetime import date, datetime, timezone
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

# curl_cffi on Windows + Python 3.13 crashes (0xC0000005) on large HTTP responses.
# Anything beyond ~3 months of daily data can trigger it for some markets (.BK especially).
# We split long-period requests into 1-year date-range slices to keep each response small.
_PERIOD_YEARS: dict[str, int] = {
    "6mo": 0,   # not chunked — under threshold
    "1y":  1,
    "2y":  2,
    "5y":  5,
    "10y": 10,
    "max": 30,
}


def _date_chunks(period: str) -> list[tuple[str, str]]:
    """Return (start, end) string pairs that together cover *period*, each ≤ 1 year."""
    years = _PERIOD_YEARS.get(period, 0)
    if years <= 1:
        return []  # caller should use the period string directly
    end = date.today()
    start = date(end.year - years, end.month, end.day)
    chunks: list[tuple[str, str]] = []
    cur = start
    while cur < end:
        nxt = date(cur.year + 1, cur.month, cur.day)
        if nxt > end:
            nxt = end
        chunks.append((cur.isoformat(), nxt.isoformat()))
        cur = nxt
    return chunks


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
                prev: float | None = None
                if df is not None and not df.empty:
                    current_price = float(df["Close"].iloc[-1])
                    if len(df) >= 2:
                        prev = float(df["Close"].iloc[-2])
                last_updated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                return {
                    "current_price": round(current_price, 4) if current_price is not None else None,
                    "previous_close": prev,
                    "last_updated": last_updated,
                }
            except Exception as e:
                _log.error("YahooProvider.get_quote(%s): %s", symbol, e)
                return {"current_price": None, "previous_close": None, "last_updated": None}

    def get_history(
        self, symbol: str, period: str = "6mo", interval: str = "1d"
    ) -> Optional[pd.DataFrame]:
        chunks = _date_chunks(period)
        with _YF_SEMAPHORE:
            try:
                ticker = yf.Ticker(symbol)
                if not chunks:
                    df = _yf_retry(ticker.history, period=period, interval=interval)
                else:
                    # Fetch in 1-year slices to avoid large-response crash in curl_cffi
                    # on Windows / Python 3.13 (access violation 0xC0000005).
                    frames: list[pd.DataFrame] = []
                    for start_s, end_s in chunks:
                        chunk_df = _yf_retry(
                            ticker.history, start=start_s, end=end_s, interval=interval
                        )
                        if chunk_df is not None and not chunk_df.empty:
                            frames.append(chunk_df)
                    if not frames:
                        return None
                    df = pd.concat(frames).sort_index()
                    df = df[~df.index.duplicated(keep="last")]
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

        date_chunks = _date_chunks(period)

        for idx, chunk in enumerate(chunks):
            if idx > 0:
                time.sleep(random.uniform(*_CHUNK_DELAY))

            with _YF_SEMAPHORE:
                try:
                    if not date_chunks:
                        data = yf.download(
                            " ".join(chunk),
                            period=period,
                            interval=interval,
                            group_by="ticker",
                            auto_adjust=True,
                            progress=False,
                            threads=False,
                        )
                    else:
                        # Build per-year slices then concatenate, same crash-avoidance
                        # strategy as get_history() — keeps each response small.
                        slice_frames: list[pd.DataFrame] = []
                        for start_s, end_s in date_chunks:
                            slc = yf.download(
                                " ".join(chunk),
                                start=start_s,
                                end=end_s,
                                interval=interval,
                                group_by="ticker",
                                auto_adjust=True,
                                progress=False,
                                threads=False,
                            )
                            if slc is not None and not slc.empty:
                                slice_frames.append(slc)
                        if not slice_frames:
                            continue
                        data = pd.concat(slice_frames).sort_index()
                        data = data[~data.index.duplicated(keep="last")]
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
