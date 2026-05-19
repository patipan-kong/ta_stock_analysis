"""
Pure-math scoring layer — no AI calls.
All functions take pre-computed agent result dicts (already cached/fetched)
and return an integer in the 0-100 range.

Scale semantics:
  technical_score:   50=neutral, >65=bullish, <35=bearish
  fundamental_score: 50=fairly valued, >70=undervalued, <30=overvalued
  news_sentiment:    50=neutral, >65=positive, <35=negative
  risk_score:        higher = more volatile / uncertain
"""


def calculate_technical_score(tech: dict | None) -> int:
    if not tech or "error" in tech:
        return 50

    score = 50.0
    st = tech.get("short_term") or {}
    lt = tech.get("long_term")  or {}

    def _from_frame(frame: dict, weight: float) -> float:
        delta = 0.0
        rsi = frame.get("rsi")
        if rsi is not None:
            if   rsi < 25: delta += 15
            elif rsi < 35: delta += 8
            elif rsi < 45: delta += 4
            elif rsi > 75: delta -= 15
            elif rsi > 65: delta -= 8
            elif rsi > 55: delta -= 4

        macd = frame.get("macd_signal", "")
        if   "bullish" in macd: delta += 12
        elif "bearish" in macd: delta -= 12

        bb = frame.get("bb_position", "")
        if   "lower" in bb: delta += 8
        elif "upper" in bb: delta -= 8

        trend = frame.get("trend", "")
        if   "up"   in trend: delta += 10
        elif "down" in trend: delta -= 10

        return delta * weight

    # Short-term weight 40%, long-term 60% (mirrors existing ta weighting)
    score += _from_frame(st, 0.4)
    score += _from_frame(lt, 0.6)

    # Alignment bonus/penalty: both frames agree → stronger signal
    st_up = "up" in st.get("trend", "")
    lt_up = "up" in lt.get("trend", "")
    if st_up == lt_up:
        score += 5 if lt_up else -5

    return max(0, min(100, round(score)))


def calculate_fundamental_score(fund: dict | None) -> int:
    if not fund or "error" in fund:
        return 50

    score = 50.0

    pe = fund.get("pe_ratio")
    if pe is not None and pe > 0:
        if   pe < 12: score += 15
        elif pe < 20: score += 8
        elif pe < 30: score += 2
        elif pe < 45: score -= 8
        else:         score -= 15

    roe = fund.get("roe")
    if roe is not None:
        if   roe > 0.25: score += 15
        elif roe > 0.15: score += 8
        elif roe > 0.05: score += 3
        elif roe < 0:    score -= 15
        else:            score -= 5

    rev = fund.get("revenue_growth")
    if rev is not None:
        if   rev > 0.25: score += 12
        elif rev > 0.10: score += 6
        elif rev > 0:    score += 2
        elif rev > -0.10: score -= 6
        else:            score -= 12

    de = fund.get("debt_equity")
    if de is not None:
        if   de < 0.3:  score += 8
        elif de < 1.0:  score += 2
        elif de < 2.0:  score -= 6
        else:           score -= 12

    return max(0, min(100, round(score)))


_POS_WORDS = {
    "buy", "growth", "profit", "upgrade", "beat", "surge", "rally", "bullish",
    "strong", "record", "gain", "rise", "outperform", "expand", "positive",
    "increase", "recovery", "boost", "dividend", "earnings",
}
_NEG_WORDS = {
    "sell", "loss", "downgrade", "miss", "drop", "crash", "decline", "bearish",
    "weak", "cut", "fall", "underperform", "contract", "lawsuit", "fraud",
    "investigation", "warning", "default", "debt", "layoff", "recall",
}


def calculate_news_sentiment(news_list: list | None) -> int:
    if not news_list:
        return 50

    pos = neg = 0
    for item in (news_list or [])[:10]:
        text = (item.get("title", "") + " " + item.get("summary", "")).lower()
        words = set(text.split())
        pos += len(words & _POS_WORDS)
        neg += len(words & _NEG_WORDS)

    net = pos - neg
    # Each net point shifts sentiment by ±4, capped at ±25 from neutral
    score = 50 + max(-25, min(25, net * 4))
    return max(0, min(100, round(score)))


def calculate_risk_score(tech: dict | None, fund: dict | None) -> int:
    """
    Higher = more volatile / uncertain risk.
    Derived from: TA/FA divergence, RSI extremes, debt level, revenue trend.
    """
    score = 40.0  # base: moderate-low risk

    if tech and "error" not in tech:
        st = tech.get("short_term") or {}
        lt = tech.get("long_term")  or {}

        # Trend disagreement between timeframes = higher uncertainty
        if st.get("trend") != lt.get("trend") and st.get("trend") and lt.get("trend"):
            score += 15

        # Extreme RSI = momentum overshoot risk
        rsi = tech.get("rsi")
        if rsi is not None:
            if rsi > 78 or rsi < 22:
                score += 12
            elif rsi > 70 or rsi < 30:
                score += 6

        # BB upper band = overbought risk
        bb = (lt.get("bb_position") or "").lower()
        if "upper" in bb:
            score += 8
        elif "lower" in bb:
            score += 5  # oversold — still volatile

    if fund and "error" not in fund:
        de = fund.get("debt_equity")
        if de is not None:
            if   de > 2.0: score += 18
            elif de > 1.0: score += 8
            elif de < 0.2: score -= 5

        rev = fund.get("revenue_growth")
        if rev is not None and rev < -0.05:
            score += 10

        pe = fund.get("pe_ratio")
        if pe is not None and pe > 50:
            score += 8  # high valuation = downside risk

    return max(0, min(100, round(score)))


def compute_scores(
    tech: dict | None,
    fund: dict | None,
    news: dict | None,
    valuation_percentile: int | None = None,
) -> dict:
    """Convenience wrapper — returns all four scores as a single dict.
    valuation_percentile: optional batch-computed PE rank (0-100). If >= 92, applies
    an overvaluation penalty to fundamental_score."""
    news_list = (news.get("news") if news and "error" not in news else None) or []
    fund_score = calculate_fundamental_score(fund)

    # Apply valuation percentile penalty when PE is in the most expensive tier of peers
    if valuation_percentile is not None and valuation_percentile >= 92:
        fund_score = max(0, fund_score - 12)
    elif valuation_percentile is not None and valuation_percentile >= 80:
        fund_score = max(0, fund_score - 6)

    return {
        "technical_score":      calculate_technical_score(tech),
        "fundamental_score":    fund_score,
        "news_sentiment":       calculate_news_sentiment(news_list),
        "risk_score":           calculate_risk_score(tech, fund),
        "valuation_percentile": valuation_percentile,
    }
