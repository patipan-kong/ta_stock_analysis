from services.data_fetcher import fetch_info, normalize_dr_symbol
from typing import TypedDict


class FundamentalResult(TypedDict):
    symbol: str
    sector: str | None
    pe_ratio: float | None
    eps: float | None
    revenue_growth: float | None
    roe: float | None
    debt_equity: float | None
    market_cap: float | None
    target_price: float | None
    analyst_count: int | None
    upside_pct: float | None
    upside_source: str | None
    fa_score: int
    fa_summary: str


def analyze_fundamental(symbol: str) -> FundamentalResult | dict:
    yf_symbol = normalize_dr_symbol(symbol)  # DR: AAPL01.BK → AAPL; others unchanged
    info = fetch_info(yf_symbol)
    if not info:
        return {"error": "data unavailable"}

    score = 0
    notes = []

    sector: str | None = info.get("sector") or None
    pe_ratio: float | None = info.get("trailingPE") or info.get("forwardPE")
    eps: float | None = info.get("trailingEps")
    revenue_growth: float | None = info.get("revenueGrowth")
    roe: float | None = info.get("returnOnEquity")
    debt_equity: float | None = info.get("debtToEquity")
    market_cap: float | None = info.get("marketCap")
    target_price: float | None = info.get("targetMeanPrice")
    analyst_count: int | None = info.get("numberOfAnalystOpinions")
    current_price_info: float | None = info.get("currentPrice") or info.get("regularMarketPrice")
    upside_pct: float | None = (
        round((target_price - current_price_info) / current_price_info * 100, 1)
        if target_price and current_price_info and current_price_info > 0
        else None
    )
    upside_source: str | None = "analyst_consensus" if target_price else None

    # P/E scoring
    if pe_ratio is not None:
        if 0 < pe_ratio < 15:
            score += 2
            notes.append(f"P/E {pe_ratio:.1f} — undervalued")
        elif 15 <= pe_ratio <= 25:
            score += 1
            notes.append(f"P/E {pe_ratio:.1f} — fair value")
        elif pe_ratio > 40:
            score -= 1
            notes.append(f"P/E {pe_ratio:.1f} — expensive")
        elif pe_ratio < 0:
            score -= 1
            notes.append("Negative P/E (loss-making)")
    else:
        notes.append("P/E unavailable")

    # Revenue growth
    if revenue_growth is not None:
        if revenue_growth > 0.15:
            score += 2
            notes.append(f"Revenue growth {revenue_growth:.0%} — strong")
        elif revenue_growth > 0.05:
            score += 1
            notes.append(f"Revenue growth {revenue_growth:.0%} — moderate")
        elif revenue_growth < 0:
            score -= 1
            notes.append(f"Revenue declining {revenue_growth:.0%}")
    else:
        notes.append("Revenue growth unavailable")

    # ROE
    if roe is not None:
        if roe > 0.20:
            score += 2
            notes.append(f"ROE {roe:.0%} — excellent")
        elif roe > 0.10:
            score += 1
            notes.append(f"ROE {roe:.0%} — good")
        elif roe < 0:
            score -= 1
            notes.append(f"ROE {roe:.0%} — negative")
    else:
        notes.append("ROE unavailable")

    # Debt/Equity
    if debt_equity is not None:
        if debt_equity < 50:
            score += 1
            notes.append(f"D/E {debt_equity:.1f} — low leverage")
        elif debt_equity > 200:
            score -= 1
            notes.append(f"D/E {debt_equity:.1f} — high leverage")

    return FundamentalResult(
        symbol=symbol,
        sector=sector,
        pe_ratio=round(pe_ratio, 2) if pe_ratio is not None else None,
        eps=round(eps, 4) if eps is not None else None,
        revenue_growth=round(revenue_growth, 4) if revenue_growth is not None else None,
        roe=round(roe, 4) if roe is not None else None,
        debt_equity=round(debt_equity, 2) if debt_equity is not None else None,
        market_cap=market_cap,
        target_price=round(target_price, 2) if target_price is not None else None,
        analyst_count=analyst_count,
        upside_pct=upside_pct,
        upside_source=upside_source,
        fa_score=score,
        fa_summary=", ".join(notes),
    )
