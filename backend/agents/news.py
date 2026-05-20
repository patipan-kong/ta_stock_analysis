from services.data_fetcher import fetch_news, normalize_dr_symbol
from typing import TypedDict


class NewsItem(TypedDict):
    title: str
    publisher: str
    link: str
    published: str


class NewsResult(TypedDict):
    symbol: str
    news: list[NewsItem]
    news_count: int


def analyze_news(symbol: str) -> NewsResult | dict:
    yf_symbol = normalize_dr_symbol(symbol)  # DR: AAPL01.BK → AAPL; others unchanged
    news = fetch_news(yf_symbol)
    return NewsResult(
        symbol=symbol,
        news=news,
        news_count=len(news),
    )
