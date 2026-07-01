"""Public interface for market data providers.

Canonical import path for new code (sync scripts, ETL jobs, admin tools).
The abstract class lives in base.py; concrete implementations live in
yahoo.py (legacy, yfinance-backed) and yahoo_chart.py (default, pure-Python
Yahoo Chart API client — see yahoo_chart.py docstring for why this exists).

    from services.market_data.provider import MarketDataProvider, get_provider

Provider contract (all methods):
    get_quote(symbol)              -> {current_price, previous_close, last_updated}
    get_quotes(symbols)            -> {symbol: {current_price, previous_close, last_updated}}
    get_history(symbol, period, interval) -> pd.DataFrame | None
    get_history_batch(symbols, period, interval) -> {symbol: pd.DataFrame}
    get_fundamentals(symbol)       -> dict
    get_news(symbol)               -> list[dict]

Provider selection (env var PRICE_PROVIDER, default "yahoo"):
    PRICE_PROVIDER=yahoo     -> YahooChartProvider  (default — crash-safe)
    PRICE_PROVIDER=yfinance  -> YahooFinanceProvider (legacy — rollback / comparison)
"""
import os

from .base import MarketDataProvider
from .yahoo import YahooProvider as YahooFinanceProvider
from .yahoo_chart import YahooChartProvider

__all__ = [
    "MarketDataProvider",
    "YahooFinanceProvider",
    "YahooChartProvider",
    "get_provider",
]

_PROVIDER_ENV = "PRICE_PROVIDER"


def get_provider(name: str | None = None) -> MarketDataProvider:
    """Build the configured MarketDataProvider.

    *name* overrides the PRICE_PROVIDER env var when given (mainly for tests).
    Unrecognised values fall back to the default ("yahoo").
    """
    choice = (name or os.environ.get(_PROVIDER_ENV, "yahoo")).strip().lower()
    if choice == "yfinance":
        return YahooFinanceProvider()
    return YahooChartProvider()
