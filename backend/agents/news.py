from services.data_fetcher import fetch_news
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
    news = fetch_news(symbol)
    return NewsResult(
        symbol=symbol,
        news=news,
        news_count=len(news),
    )
