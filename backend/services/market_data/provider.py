"""Public interface for market data providers.

Canonical import path for new code (sync scripts, ETL jobs, admin tools).
The abstract class lives in base.py; the concrete Yahoo Finance implementation
lives in yahoo.py.

    from services.market_data.provider import MarketDataProvider, YahooFinanceProvider

Provider contract (all methods):
    get_quote(symbol)              -> {current_price, change_percent, last_updated}
    get_quotes(symbols)            -> {symbol: {current_price, change_percent, last_updated}}
    get_history(symbol, period, interval) -> pd.DataFrame | None
    get_history_batch(symbols, period, interval) -> {symbol: pd.DataFrame}
    get_fundamentals(symbol)       -> dict
    get_news(symbol)               -> list[dict]
"""
from .base import MarketDataProvider
from .yahoo import YahooProvider as YahooFinanceProvider

__all__ = ["MarketDataProvider", "YahooFinanceProvider"]
