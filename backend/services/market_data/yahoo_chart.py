"""Pure-Python Yahoo Finance Chart API provider.

Replaces yfinance's ``Ticker.history()`` for the historical-price pipeline.

Background
----------
yfinance >= 0.2.37 uses curl_cffi (a compiled native DLL) for browser
impersonation. On Windows + Python 3.13 that DLL crashes the whole
interpreter with an access violation (exit code 0xC0000005 /
-1073741819) when fetching large responses — observed for ``period="5y"``
on SET (.BK) symbols. This is a native crash, not a Python exception, so
it cannot be caught with try/except and previously took down the entire
process.

This provider talks directly to the same Yahoo Finance Chart endpoint
yfinance uses internally:

    https://query1.finance.yahoo.com/v8/finance/chart/{symbol}

via plain ``requests``. Every failure mode (network error, HTTP error,
malformed JSON, Yahoo-side error, empty result) is caught in Python and
degrades to ``None`` — it can never crash the interpreter.

``get_fundamentals()`` and ``get_news()`` have no equivalent on the chart
endpoint; those are delegated to the legacy yfinance-backed YahooProvider,
since the user-reported crash is specific to ``.history()`` on large date
ranges, not ``.info`` / ``.news``.
"""
from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
import requests

from .base import MarketDataProvider

_log = logging.getLogger(__name__)

_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
_TIMEOUT_S = 10
_MAX_ATTEMPTS = 3
_MAX_WORKERS = 5

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

_session = requests.Session()
_session.headers.update(_HEADERS)

# Bounds concurrent outbound requests across all threads (mirrors yahoo.py's
# _YF_SEMAPHORE) to stay well under Yahoo's undocumented per-IP rate limit.
_SEMAPHORE = threading.Semaphore(_MAX_WORKERS)


def _fetch_chart_result(symbol: str, range_: str, interval: str) -> Optional[dict]:
    """GET the raw ``chart.result[0]`` payload for *symbol*, or None on any failure.

    Never raises. Every failure mode is caught and logged here so callers can
    treat None uniformly as "no data available right now".
    """
    url = _CHART_URL.format(symbol=symbol)
    params = {
        "range": range_,
        "interval": interval,
        "includeAdjustedClose": "true",
        "events": "div,splits",
    }

    for attempt in range(_MAX_ATTEMPTS):
        try:
            resp = _session.get(url, params=params, timeout=_TIMEOUT_S)
        except requests.exceptions.RequestException as e:
            _log.warning("YahooChartProvider network error symbol=%s: %s", symbol, e)
            return None

        if resp.status_code == 429 and attempt < _MAX_ATTEMPTS - 1:
            wait = (2 ** attempt) + 1.0
            _log.warning("YahooChartProvider 429 symbol=%s – retry in %.1fs", symbol, wait)
            time.sleep(wait)
            continue

        if resp.status_code != 200:
            _log.warning("YahooChartProvider HTTP %d symbol=%s", resp.status_code, symbol)
            return None

        try:
            payload = resp.json()
        except ValueError as e:
            _log.warning("YahooChartProvider invalid JSON symbol=%s: %s", symbol, e)
            return None

        chart = payload.get("chart") or {}
        if chart.get("error"):
            _log.info("YahooChartProvider chart error symbol=%s: %s", symbol, chart["error"])
            return None

        results = chart.get("result")
        if not results:
            return None
        return results[0]

    return None


def _chart_result_to_df(result: dict) -> Optional[pd.DataFrame]:
    """Convert a raw ``chart.result[0]`` dict into an OHLCV DataFrame, or None if empty."""
    timestamps = result.get("timestamp")
    if not timestamps:
        return None

    indicators = result.get("indicators") or {}
    quote_list = indicators.get("quote") or [{}]
    quote = quote_list[0] if quote_list else {}
    adjclose_list = indicators.get("adjclose") or []
    adjclose = adjclose_list[0].get("adjclose") if adjclose_list else None

    index = pd.to_datetime(timestamps, unit="s", utc=True)
    df = pd.DataFrame(
        {
            "Open":   quote.get("open"),
            "High":   quote.get("high"),
            "Low":    quote.get("low"),
            "Close":  quote.get("close"),
            "Volume": quote.get("volume"),
        },
        index=index,
    )
    df["Adj Close"] = adjclose if adjclose is not None else df["Close"]

    # Sort + dedupe before mapping events onto bars — asof() requires a
    # monotonic, unique index.
    df = df.sort_index()
    df = df[~df.index.duplicated(keep="last")]

    df["Dividends"] = 0.0
    df["Stock Splits"] = 0.0

    events = result.get("events") or {}
    for ts_str, ev in (events.get("dividends") or {}).items():
        ts = pd.to_datetime(int(ts_str), unit="s", utc=True)
        nearest = df.index.asof(ts)
        if pd.notna(nearest):
            df.loc[nearest, "Dividends"] = ev.get("amount", 0.0)
    for ts_str, ev in (events.get("splits") or {}).items():
        ts = pd.to_datetime(int(ts_str), unit="s", utc=True)
        nearest = df.index.asof(ts)
        denom = ev.get("denominator")
        if pd.notna(nearest) and denom:
            df.loc[nearest, "Stock Splits"] = ev.get("numerator", 1) / denom

    df = df.dropna(how="all", subset=["Open", "High", "Low", "Close"])
    return df if not df.empty else None


class YahooChartProvider(MarketDataProvider):
    """MarketDataProvider backed directly by the Yahoo Finance Chart API.

    Pure-Python HTTP (requests) — no curl_cffi, no native dependency in the
    historical-price path. Cannot crash the interpreter; every failure mode
    degrades to None / {} / [].
    """

    def __init__(self) -> None:
        self._legacy: Optional[MarketDataProvider] = None

    def _legacy_provider(self) -> MarketDataProvider:
        """Lazily-built yfinance-backed provider, used only for .info / .news."""
        if self._legacy is None:
            from .yahoo import YahooProvider
            self._legacy = YahooProvider()
        return self._legacy

    def get_quote(self, symbol: str) -> dict:
        with _SEMAPHORE:
            result = _fetch_chart_result(symbol, range_="5d", interval="1d")
            print("===== RAW YAHOO =====")
            print(symbol)
            print(result)
        if result is None:
            return {"current_price": None, "previous_close": None, "last_updated": None}

        meta = result.get("meta") or {}
        current_price = meta.get("regularMarketPrice")
        closes = result["indicators"]["quote"][0]["close"]
        prev_close = closes[-2] if len(closes) >= 2 else None
        
        return {
            "current_price": round(current_price, 4) if current_price is not None else None,
            "previous_close": prev_close,
            "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

    def get_history(
        self, symbol: str, period: str = "6mo", interval: str = "1d"
    ) -> Optional[pd.DataFrame]:
        with _SEMAPHORE:
            result = _fetch_chart_result(symbol, range_=period, interval=interval)
        if result is None:
            return None
        try:
            return _chart_result_to_df(result)
        except Exception as e:
            _log.error("YahooChartProvider parse error symbol=%s period=%s: %s", symbol, period, e)
            return None

    def get_fundamentals(self, symbol: str) -> dict:
        return self._legacy_provider().get_fundamentals(symbol)

    def get_news(self, symbol: str) -> list[dict]:
        return self._legacy_provider().get_news(symbol)

    def get_history_batch(
        self, symbols: list[str], period: str = "6mo", interval: str = "1d"
    ) -> dict[str, pd.DataFrame]:
        """Concurrent per-symbol fetch — the chart endpoint has no native multi-symbol batch call."""
        result: dict[str, pd.DataFrame] = {}
        if not symbols:
            return result
        with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as ex:
            futures = {ex.submit(self.get_history, sym, period, interval): sym for sym in symbols}
            for fut in as_completed(futures):
                sym = futures[fut]
                try:
                    df = fut.result()
                except Exception as e:
                    _log.warning("YahooChartProvider batch fetch failed symbol=%s: %s", sym, e)
                    df = None
                if df is not None and not df.empty:
                    result[sym] = df
        return result
