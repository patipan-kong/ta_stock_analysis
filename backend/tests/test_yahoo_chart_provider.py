"""Regression tests for services.market_data.yahoo_chart.YahooChartProvider.

Two layers:
  1. Mocked unit tests (default) — no network, deterministic, run in CI.
     Cover DataFrame shape/columns/sort/dedup and every failure mode
     (invalid symbol, HTTP error, timeout, malformed JSON).
  2. Live smoke tests — actually hit Yahoo Finance for the US/TH symbol
     list across 1mo/3mo/1y/5y. Skipped unless RUN_LIVE_MARKET_TESTS=1,
     since CI shouldn't depend on an external network call succeeding.
     Run manually with:
         RUN_LIVE_MARKET_TESTS=1 python -m pytest backend/tests/test_yahoo_chart_provider.py -v
"""
import os
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import pytest
import requests

from services.market_data.provider import get_provider
from services.market_data.yahoo import YahooProvider
from services.market_data.yahoo_chart import YahooChartProvider, _chart_result_to_df


# ── Fixture payload builder ────────────────────────────────────────────────────

def _make_payload(
    timestamps: list[int],
    opens: list[float | None],
    highs: list[float | None],
    lows: list[float | None],
    closes: list[float | None],
    volumes: list[int | None],
    dividends: dict[str, dict] | None = None,
    splits: dict[str, dict] | None = None,
    meta_overrides: dict | None = None,
) -> dict:
    meta = {
        "regularMarketPrice": closes[-1] if closes else None,
        "previousClose": closes[-2] if len(closes) >= 2 else None,
    }
    if meta_overrides:
        meta.update(meta_overrides)
    return {
        "chart": {
            "result": [
                {
                    "meta": meta,
                    "timestamp": timestamps,
                    "events": {
                        "dividends": dividends or {},
                        "splits": splits or {},
                    },
                    "indicators": {
                        "quote": [{"open": opens, "high": highs, "low": lows, "close": closes, "volume": volumes}],
                        "adjclose": [{"adjclose": closes}],
                    },
                }
            ],
            "error": None,
        }
    }


def _error_payload(code: str = "Not Found", description: str = "No data found, symbol may be delisted") -> dict:
    return {"chart": {"result": None, "error": {"code": code, "description": description}}}


class _MockResponse:
    def __init__(self, status_code: int = 200, json_data: dict | None = None):
        self.status_code = status_code
        self._json_data = json_data

    def json(self):
        if self._json_data is None:
            raise ValueError("no json body")
        return self._json_data


_BASE_TS = [1717113600, 1717200000, 1717286400, 1717372800, 1717459200]  # 5 consecutive days (UTC)
_BASE_CLOSES = [10.0, 10.5, 10.2, 10.8, 11.0]


def _patched_get(provider_module: str = "services.market_data.yahoo_chart"):
    return patch(f"{provider_module}._session.get")


# ── get_history: happy path ────────────────────────────────────────────────────

def test_get_history_returns_required_columns():
    payload = _make_payload(_BASE_TS, _BASE_CLOSES, _BASE_CLOSES, _BASE_CLOSES, _BASE_CLOSES, [1000] * 5)
    with _patched_get() as mock_get:
        mock_get.return_value = _MockResponse(200, payload)
        df = YahooChartProvider().get_history("GULF.BK", period="1mo", interval="1d")

    assert df is not None
    for col in ["Open", "High", "Low", "Close", "Volume", "Adj Close", "Dividends", "Stock Splits"]:
        assert col in df.columns
    assert len(df) == 5


def test_get_history_index_is_utc_datetime_and_sorted_ascending():
    shuffled_ts = [_BASE_TS[2], _BASE_TS[0], _BASE_TS[4], _BASE_TS[1], _BASE_TS[3]]
    shuffled_closes = [10.2, 10.0, 11.0, 10.5, 10.8]
    payload = _make_payload(shuffled_ts, shuffled_closes, shuffled_closes, shuffled_closes, shuffled_closes, [1000] * 5)
    with _patched_get() as mock_get:
        mock_get.return_value = _MockResponse(200, payload)
        df = YahooChartProvider().get_history("AAPL", period="1mo", interval="1d")

    assert df is not None
    assert isinstance(df.index, pd.DatetimeIndex)
    assert str(df.index.tz) == "UTC"
    assert df.index.is_monotonic_increasing
    assert list(df["Close"]) == _BASE_CLOSES  # restored to chronological order


def test_get_history_removes_duplicate_timestamps():
    ts_with_dupe = _BASE_TS + [_BASE_TS[-1]]
    closes_with_dupe = _BASE_CLOSES + [99.0]  # duplicate ts should keep this (last) value
    payload = _make_payload(ts_with_dupe, closes_with_dupe, closes_with_dupe, closes_with_dupe, closes_with_dupe, [1000] * 6)
    with _patched_get() as mock_get:
        mock_get.return_value = _MockResponse(200, payload)
        df = YahooChartProvider().get_history("PTT.BK", period="1mo", interval="1d")

    assert df is not None
    assert len(df) == len(_BASE_TS)  # dedup'd back down
    assert df["Close"].iloc[-1] == 99.0  # kept the later duplicate


def test_get_history_drops_rows_with_no_ohlc_data():
    closes = _BASE_CLOSES + [None]
    ts = _BASE_TS + [1717545600]
    payload = _make_payload(ts, closes, closes, closes, closes, [1000] * 5 + [None])
    with _patched_get() as mock_get:
        mock_get.return_value = _MockResponse(200, payload)
        df = YahooChartProvider().get_history("KBANK.BK", period="1mo", interval="1d")

    assert df is not None
    assert len(df) == 5  # trailing all-NaN bar dropped


# ── Dividends / splits ─────────────────────────────────────────────────────────

def test_dividends_and_splits_populated_on_matching_bar():
    div_ts = str(_BASE_TS[2])
    split_ts = str(_BASE_TS[3])
    payload = _make_payload(
        _BASE_TS, _BASE_CLOSES, _BASE_CLOSES, _BASE_CLOSES, _BASE_CLOSES, [1000] * 5,
        dividends={div_ts: {"amount": 1.25, "date": int(div_ts)}},
        splits={split_ts: {"numerator": 2, "denominator": 1, "date": int(split_ts)}},
    )
    with _patched_get() as mock_get:
        mock_get.return_value = _MockResponse(200, payload)
        df = YahooChartProvider().get_history("ADVANC.BK", period="1mo", interval="1d")

    assert df is not None
    assert df["Dividends"].iloc[2] == 1.25
    assert df["Stock Splits"].iloc[3] == 2.0
    # all other bars stay at the sensible default
    assert df["Dividends"].sum() == 1.25
    assert df["Stock Splits"].replace(0.0, pd.NA).count() == 1


# ── Failure modes — must all return None, never raise ──────────────────────────

def test_invalid_symbol_returns_none():
    with _patched_get() as mock_get:
        mock_get.return_value = _MockResponse(200, _error_payload())
        df = YahooChartProvider().get_history("NOTASYMBOL.XX", period="1mo", interval="1d")
    assert df is None


def test_http_error_status_returns_none():
    with _patched_get() as mock_get:
        mock_get.return_value = _MockResponse(404, None)
        df = YahooChartProvider().get_history("AAPL", period="1mo", interval="1d")
    assert df is None


def test_network_timeout_returns_none():
    with _patched_get() as mock_get:
        mock_get.side_effect = requests.exceptions.Timeout("simulated timeout")
        df = YahooChartProvider().get_history("GULF.BK", period="5y", interval="1d")
    assert df is None


def test_connection_error_returns_none():
    with _patched_get() as mock_get:
        mock_get.side_effect = requests.exceptions.ConnectionError("simulated DNS failure")
        df = YahooChartProvider().get_history("GULF.BK", period="5y", interval="1d")
    assert df is None


def test_malformed_json_returns_none():
    with _patched_get() as mock_get:
        mock_get.return_value = _MockResponse(200, None)  # .json() raises ValueError
        df = YahooChartProvider().get_history("AAPL", period="1mo", interval="1d")
    assert df is None


def test_empty_result_list_returns_none():
    with _patched_get() as mock_get:
        mock_get.return_value = _MockResponse(200, {"chart": {"result": [], "error": None}})
        df = YahooChartProvider().get_history("AAPL", period="1mo", interval="1d")
    assert df is None


def test_no_timestamps_returns_none():
    payload = _make_payload([], [], [], [], [], [])
    with _patched_get() as mock_get:
        mock_get.return_value = _MockResponse(200, payload)
        df = YahooChartProvider().get_history("AAPL", period="1mo", interval="1d")
    assert df is None


def test_chart_result_to_df_handles_garbage_without_raising():
    # Defensive: a structurally-odd-but-truthy result dict shouldn't raise.
    assert _chart_result_to_df({}) is None
    assert _chart_result_to_df({"timestamp": None}) is None


# ── Rate-limit retry ────────────────────────────────────────────────────────────

def test_429_then_200_retries_and_succeeds():
    payload = _make_payload(_BASE_TS, _BASE_CLOSES, _BASE_CLOSES, _BASE_CLOSES, _BASE_CLOSES, [1000] * 5)
    with _patched_get() as mock_get, patch("services.market_data.yahoo_chart.time.sleep"):
        mock_get.side_effect = [_MockResponse(429, None), _MockResponse(200, payload)]
        df = YahooChartProvider().get_history("AAPL", period="1mo", interval="1d")
    assert df is not None
    assert mock_get.call_count == 2


# ── get_quote ────────────────────────────────────────────────────────────────────

def test_get_quote_computes_change_percent():
    payload = _make_payload(_BASE_TS, _BASE_CLOSES, _BASE_CLOSES, _BASE_CLOSES, _BASE_CLOSES, [1000] * 5,
                             meta_overrides={"regularMarketPrice": 11.0, "previousClose": 10.8})
    with _patched_get() as mock_get:
        mock_get.return_value = _MockResponse(200, payload)
        quote = YahooChartProvider().get_quote("AAPL")
    assert quote["current_price"] == 11.0
    assert quote["change_percent"] == round((11.0 - 10.8) / 10.8 * 100, 2)
    assert quote["last_updated"] is not None


def test_get_quote_failure_returns_none_fields():
    with _patched_get() as mock_get:
        mock_get.return_value = _MockResponse(404, None)
        quote = YahooChartProvider().get_quote("NOTASYMBOL.XX")
    assert quote == {"current_price": None, "change_percent": None, "last_updated": None}


# ── get_history_batch ────────────────────────────────────────────────────────────

def test_get_history_batch_returns_all_successful_symbols():
    payload = _make_payload(_BASE_TS, _BASE_CLOSES, _BASE_CLOSES, _BASE_CLOSES, _BASE_CLOSES, [1000] * 5)

    def _get(url, params=None, timeout=None):
        if "BADSYM" in url:
            return _MockResponse(200, _error_payload())
        return _MockResponse(200, payload)

    with patch("services.market_data.yahoo_chart._session.get", side_effect=_get):
        result = YahooChartProvider().get_history_batch(
            ["AAPL", "GULF.BK", "BADSYM.BK"], period="1mo", interval="1d"
        )

    assert set(result.keys()) == {"AAPL", "GULF.BK"}
    for df in result.values():
        assert df.index.is_monotonic_increasing


def test_get_history_batch_empty_symbol_list():
    assert YahooChartProvider().get_history_batch([], period="1mo", interval="1d") == {}


# ── get_fundamentals / get_news delegate to legacy provider ─────────────────────

def test_get_fundamentals_delegates_to_legacy_provider():
    with patch.object(YahooProvider, "get_fundamentals", return_value={"sector": "Energy"}) as mock_fund:
        info = YahooChartProvider().get_fundamentals("PTT.BK")
    mock_fund.assert_called_once_with("PTT.BK")
    assert info == {"sector": "Energy"}


def test_get_news_delegates_to_legacy_provider():
    with patch.object(YahooProvider, "get_news", return_value=[{"title": "x"}]) as mock_news:
        news = YahooChartProvider().get_news("PTT.BK")
    mock_news.assert_called_once_with("PTT.BK")
    assert news == [{"title": "x"}]


# ── Provider factory ─────────────────────────────────────────────────────────────

def test_factory_defaults_to_yahoo_chart_provider(monkeypatch):
    monkeypatch.delenv("PRICE_PROVIDER", raising=False)
    assert isinstance(get_provider(), YahooChartProvider)


def test_factory_yahoo_explicit(monkeypatch):
    monkeypatch.setenv("PRICE_PROVIDER", "yahoo")
    assert isinstance(get_provider(), YahooChartProvider)


def test_factory_yfinance_rollback(monkeypatch):
    monkeypatch.setenv("PRICE_PROVIDER", "yfinance")
    assert isinstance(get_provider(), YahooProvider)


def test_factory_explicit_name_overrides_env(monkeypatch):
    monkeypatch.setenv("PRICE_PROVIDER", "yfinance")
    assert isinstance(get_provider("yahoo"), YahooChartProvider)


def test_factory_unknown_value_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("PRICE_PROVIDER", "bogus")
    assert isinstance(get_provider(), YahooChartProvider)


# ── Live smoke tests (network, opt-in only) ──────────────────────────────────────

_RUN_LIVE = os.environ.get("RUN_LIVE_MARKET_TESTS") == "1"

_US_SYMBOLS = ["AAPL", "MSFT", "NVDA"]
_TH_SYMBOLS = ["SCB.BK", "KBANK.BK", "PTT.BK", "ADVANC.BK", "GULF.BK"]
_PERIODS = ["1mo", "3mo", "1y", "5y"]


@pytest.mark.skipif(not _RUN_LIVE, reason="set RUN_LIVE_MARKET_TESTS=1 to hit the real Yahoo Finance API")
@pytest.mark.parametrize("symbol", _US_SYMBOLS + _TH_SYMBOLS)
@pytest.mark.parametrize("period", _PERIODS)
def test_live_get_history(symbol, period):
    df = YahooChartProvider().get_history(symbol, period=period, interval="1d")
    assert df is not None, f"no data returned for {symbol} {period}"
    assert not df.empty
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        assert col in df.columns
    assert df.index.is_monotonic_increasing
    assert not df.index.duplicated().any()
    assert str(df.index.tz) == "UTC"
