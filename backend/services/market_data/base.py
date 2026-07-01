from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd


class MarketDataProvider(ABC):
    """Abstract interface for market data providers.

    Implement this to swap yfinance for a paid provider (EODHD, FMP, etc.)
    without touching any agent or endpoint code.
    """

    @abstractmethod
    def get_quote(self, symbol: str) -> dict:
        """Return current price info dict: {current_price, previous_close, last_updated}."""
        ...

    @abstractmethod
    def get_history(self, symbol: str, period: str = "6mo", interval: str = "1d") -> Optional[pd.DataFrame]:
        """Return OHLCV DataFrame for the given period/interval, or None on failure."""
        ...

    @abstractmethod
    def get_fundamentals(self, symbol: str) -> dict:
        """Return raw info dict (P/E, ROE, sector, marketCap, …), or {} on failure."""
        ...

    @abstractmethod
    def get_news(self, symbol: str) -> list[dict]:
        """Return list of recent news articles (up to 10).
        Each item: {title, publisher, link, published}."""
        ...

    def get_quotes(self, symbols: list[str]) -> dict[str, dict]:
        """Batch-fetch current quotes for multiple symbols.

        Returns {symbol: {current_price, previous_close, last_updated}}.
        Default implementation calls get_quote() sequentially.
        Override for batch efficiency.
        """
        return {sym: self.get_quote(sym) for sym in symbols}

    def get_history_batch(
        self, symbols: list[str], period: str = "6mo", interval: str = "1d"
    ) -> dict[str, pd.DataFrame]:
        """Batch-fetch history for multiple symbols.

        Default implementation calls get_history per-symbol sequentially.
        Override in concrete providers that support native batch endpoints
        (e.g. yf.download for Yahoo, multi-ticker API for EODHD).
        """
        result: dict[str, pd.DataFrame] = {}
        for sym in symbols:
            df = self.get_history(sym, period, interval)
            if df is not None and not df.empty:
                result[sym] = df
        return result
