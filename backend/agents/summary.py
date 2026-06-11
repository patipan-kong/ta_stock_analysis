import json
from typing import TypedDict
from services.ai_client import call_ai
from services.json_utils import safe_parse_json


class SummaryResult(TypedDict):
    symbol: str
    signal: str
    confidence: str
    reasoning: str
    risks: str
    executive_summary: str
    ai_summary: str


_CONF_ORDER = ["low", "medium", "high"]
_VALID_SIGNALS = {"ACCUMULATE", "BUY", "WATCH", "HOLD", "REDUCE", "SELL"}


def _cap_confidence(conf: str, max_conf: str) -> str:
    idx     = _CONF_ORDER.index(conf)     if conf     in _CONF_ORDER else 0
    max_idx = _CONF_ORDER.index(max_conf) if max_conf in _CONF_ORDER else 2
    return _CONF_ORDER[min(idx, max_idx)]


def determine_signal(
    ta_short: int | None,
    ta_long: int | None,
    fa_score: int | None,
) -> tuple[str, str]:
    """
    6-level preliminary signal. FA weight 60%, TA weight 40% (LT 60%, ST 40% within TA).
    Returns (signal, confidence).
    """
    has_ta = ta_short is not None and ta_long is not None
    has_fa = fa_score is not None

    ta_composite = round(0.4 * (ta_short or 0) + 0.6 * (ta_long or 0)) if has_ta else 0
    fa = fa_score or 0

    if has_ta and has_fa:
        weighted = round(0.4 * ta_composite + 0.6 * fa)
    elif has_fa:
        weighted = fa
    elif has_ta:
        weighted = ta_composite
    else:
        return "HOLD", "low"

    # Strong combined signal → BUY
    if weighted >= 3 or (has_fa and has_ta and fa >= 4 and ta_composite >= 2):
        return "BUY", "high"

    # Strong FA but TA lagging → ACCUMULATE (DCA opportunity)
    if has_fa and fa >= 3 and has_ta and ta_composite < 1:
        return "ACCUMULATE", "medium"

    # Moderate positive combined → WATCH
    if weighted >= 1:
        return "WATCH", "medium"

    # Good fundamentals but TA not confirming → WATCH
    if has_fa and fa >= 2:
        return "WATCH", "low"

    # Neutral zone → HOLD
    if weighted >= -1:
        return "HOLD", "medium" if (has_ta and has_fa) else "low"

    # Mild deterioration → REDUCE
    if weighted >= -3:
        return "REDUCE", "medium" if weighted <= -2 else "low"

    # Strong bearish → SELL
    return "SELL", "high" if (has_fa and fa <= -4) else "medium"


def analyze_summary(
    symbol: str,
    technical: dict | None,
    fundamental: dict | None,
    news: dict | None,
    provider: str = "anthropic",
    model: str = "claude-sonnet-4-6",
    scores: dict | None = None,
) -> dict:
    has_ta   = technical   is not None and "error" not in technical
    has_fa   = fundamental is not None and "error" not in fundamental
    has_news = news        is not None and "error" not in news

    valid_count = sum([has_ta, has_fa, has_news])
    if valid_count == 0:
        return {"error": "no data available for analysis"}

    max_conf = "high" if valid_count == 3 else "medium" if valid_count == 2 else "low"

    st = technical.get("short_term", {}) if has_ta else {}
    lt = technical.get("long_term",  {}) if has_ta else {}
    ta_short     = st.get("score", 0)       if has_ta and "error" not in st else (None if not has_ta else 0)
    ta_long      = lt.get("score", 0)       if has_ta and "error" not in lt else (None if not has_ta else 0)
    ta_short     = ta_short if has_ta else None
    ta_long      = ta_long  if has_ta else None
    ta_composite = technical.get("ta_score") if has_ta else None
    fa_score     = fundamental.get("fa_score") if has_fa else None

    prelim_signal, prelim_conf = determine_signal(ta_short, ta_long, fa_score)

    if has_ta and has_fa:
        weight_note = "FA 60% | TA 40% (within TA: long-term 60%, short-term 40%)"
        weighted = round(0.4 * (ta_composite or 0) + 0.6 * (fa_score or 0))
    elif has_fa:
        weight_note = "FA only (TA disabled)"
        weighted = fa_score or 0
    else:
        weight_note = "TA only (FA disabled)"
        weighted = ta_composite or 0

    score_lines = [f"Weighting: {weight_note}"]
    if has_ta:
        score_lines += [
            f"TA Short-term ST : {'+' if (ta_short or 0) >= 0 else ''}{ta_short or 0}   (1-month daily)",
            f"TA Long-term  LT : {'+' if (ta_long  or 0) >= 0 else ''}{ta_long  or 0}   (1-year weekly)",
            f"TA Composite     : {'+' if (ta_composite or 0) >= 0 else ''}{ta_composite or 0}",
        ]
    if has_fa:
        score_lines.append(f"FA Score         : {'+' if (fa_score or 0) >= 0 else ''}{fa_score or 0}   (range −6 to +6)")
    score_lines.append(f"Weighted score   : {'+' if weighted >= 0 else ''}{weighted}")
    score_lines.append(f"Preliminary      : {prelim_signal} ({prelim_conf} confidence)")

    limit_notes = []
    if technical is None:
        limit_notes.append("Technical Analysis (TA): disabled by user settings")
    elif not has_ta:
        limit_notes.append("Technical Analysis (TA): data unavailable")
    if fundamental is None:
        limit_notes.append("Fundamental Analysis (FA): disabled by user settings")
    elif not has_fa:
        limit_notes.append("Fundamental Analysis (FA): data unavailable")
    if news is None:
        limit_notes.append("News Sentiment: disabled by user settings")
    elif not has_news:
        limit_notes.append("News Sentiment: data unavailable")

    data_sections: list[str] = []
    if has_ta:
        data_sections.append(
            f"=== SHORT-TERM TECHNICALS (1-month, daily bars) ===\n{json.dumps(st, indent=2)}"
            f"\n\n=== LONG-TERM TECHNICALS (1-year, weekly bars) ===\n{json.dumps(lt, indent=2)}"
        )
    if has_fa:
        fund_display = {k: v for k, v in fundamental.items() if k not in ("fa_score", "symbol", "fa_summary")}
        data_sections.append(
            f"=== FUNDAMENTALS ===\n{json.dumps(fund_display, indent=2)}"
            f"\nFA Summary: {fundamental.get('fa_summary', 'N/A')}"
        )
    if has_news:
        recent_news = news.get("news", [])[:5]
        data_sections.append(
            f"=== RECENT NEWS (latest {len(recent_news)}) ===\n{json.dumps(recent_news, indent=2)}"
        )

    limitations_block = ""
    if limit_notes:
        limitations_block = (
            "\n=== DATA LIMITATIONS ===\n"
            + "\n".join(f"- {n}" for n in limit_notes)
            + f"\nMaximum confidence for this analysis: \"{max_conf}\"\n"
        )

    scores_block = ""
    if scores:
        val_pct = scores.get("valuation_percentile")
        val_line = (
            f"PE valuation percentile vs batch peers: {val_pct}%  (higher = more expensive)\n"
            if val_pct is not None else ""
        )
        scores_block = f"""
=== DETERMINISTIC SCORES (pure math, no AI) ===
Technical Score  : {scores.get('technical_score', '?'):>3} / 100  (>65 bullish · <35 bearish · 50 neutral)
Fundamental Score: {scores.get('fundamental_score', '?'):>3} / 100  (>70 undervalued · <30 overvalued · 50 fair)
News Sentiment   : {scores.get('news_sentiment', '?'):>3} / 100  (>65 positive · <35 negative · 50 neutral)
Risk Score       : {scores.get('risk_score', '?'):>3} / 100  (higher = more volatile / uncertain)
{val_line}
These are computed from raw market data before any AI interpretation.
Use them as an objective anchor — confirm or override based on qualitative context.
"""

    prompt = f"""You are a professional stock analyst specializing in long-term equity positions.

Symbol: {symbol}{scores_block}

=== QUANTITATIVE SCORING ===
{chr(10).join(score_lines)}
{limitations_block}
{chr(10).join(data_sections)}

=== SIGNAL DEFINITIONS (use exactly one) ===
- ACCUMULATE : FA score strong, TA score neutral or negative. Good company — buy gradually via DCA, not all at once.
- BUY        : FA strong AND TA positive AND valuation percentile < 92 AND opportunity in top 20% overall.
               Do NOT assign BUY based on FA alone — TA must not be bearish.
- WATCH      : Good fundamentals, technicals not ready or entry price not ideal. Wait for better setup.
               Use when valuation_percentile < 75 and FA is positive but TA is neutral.
- HOLD       : Mixed or insufficient signals. No strong reason to add or reduce.
- REDUCE     : Position likely overextended. Trim allocation.
               Use when TA strongly bearish on existing holding OR valuation_percentile > 85.
- SELL       : Exit signal. FA deteriorating OR TA score <= −3 OR major negative catalyst.

Only assign BUY to stocks in the top 20% of overall opportunity (strong FA + strong TA).
Stocks in the 21–50% opportunity range should be ACCUMULATE or WATCH.
If data is limited, prefer HOLD or WATCH over BUY — be conservative.

=== PAGE LAYOUT — RESPONSIBILITY SPLIT (do not mix these) ===
The stock page shows three separate sections. Each output field feeds exactly one:
- "executive_summary" → Executive Summary box  = "What the company IS."
- "ai_summary"        → AI Summary box         = "What the AI THINKS about it right now."
- Technical/Fundamental sections (rendered elsewhere) = evidence and metrics.
The user can already see every chart, score, and ratio on the page.

=== EXECUTIVE SUMMARY LAYER (field: "executive_summary") ===
Explain WHAT THE COMPANY IS in plain Thai — its business, how it earns money,
and its place in the industry. Do NOT give opinions, signals, or outlooks here;
that belongs to "ai_summary".

1. LANGUAGE & TONE:
   - Natural, fluent Thai. Professional, calm, beginner-friendly, objective.
   - NO promotional text, NO hype, NO investment advice.
2. CONTENT: business model, revenue sources, market position, industry context.
3. NO numbers/metrics already shown on the page.
4. FORMAT: 80-120 Thai words, 2-4 short paragraphs separated by \\n\\n,
   NO bullet points or numbered lists.

=== AI SUMMARY — INVESTMENT INTERPRETER LAYER (field: "ai_summary") ===
You are an Investment Interpreter, NOT a financial analyst. Translate the
quantitative signals above into short, human-readable investment context.
Answer within a 20-second read: "What should a normal investor understand
about this stock right now based on the AI's current interpretation?"

1. STRICT REPETITION PROHIBITION:
   - DO NOT repeat or restate any number, indicator, ratio, or score shown
     elsewhere on the page (P/E, P/BV, ROE, RSI, MACD, Beta, Alpha,
     Momentum/Technical/Fundamental scores, percentiles). Focus strictly on
     qualitative meaning, not metrics.
2. LANGUAGE:
   - Natural, fluid, elegant Thai ONLY. NO English finance jargon, no robotic
     translations. Do not sound like a broker research report.
   - BANNED boilerplate phrases (never use these or close variants):
     "ข้อมูลพื้นฐานแสดงให้เห็นว่า...", "ด้านเทคนิคบ่งชี้ว่า...",
     "การประเมินมูลค่าน่าสนใจ...", "Momentum remains positive..."
3. FORMAT: strictly 80-120 Thai words, 2-4 short paragraphs separated by \\n\\n,
   NO bullet points, NO dashes, NO numbered lists.
4. REQUIRED PARAGRAPH STRUCTURE:
   - Paragraph 1: the company's current business situation in everyday language.
   - Paragraph 2: what the market appears to be expecting from this company now.
   - Paragraph 3: the single most important opportunity or pressing risk right now.
   - Paragraph 4 (optional): a calm, balanced, non-hyped observation.

GOOD EXAMPLE (style to imitate):
"COM7 ยังคงได้ประโยชน์จากความต้องการสินค้าเทคโนโลยีและอุปกรณ์ไอทีที่มีอยู่ต่อเนื่องในตลาดไทย\\n\\nนักลงทุนยังมองว่าบริษัทมีศักยภาพในการเติบโตจากการขยายสินค้าและบริการใหม่ ๆ แต่ในขณะเดียวกันก็มีความคาดหวังต่อผลประกอบการในระดับค่อนข้างสูง\\n\\nสิ่งที่ควรติดตามคือกำลังซื้อของผู้บริโภคและการแข่งขันในตลาด ซึ่งอาจส่งผลต่อการเติบโตในระยะถัดไป\\n\\nโดยรวมยังเป็นบริษัทที่มีพื้นฐานแข็งแรง แต่ควรติดตามพัฒนาการของธุรกิจอย่างต่อเนื่อง"

BAD EXAMPLE (never write like this):
"ข้อมูลพื้นฐานแสดงถึงความสามารถในการสร้างรายได้ที่ดี และการประเมินมูลค่าอยู่ในระดับที่น่าสนใจ ขณะที่ด้านเทคนิคแสดงถึงแนวโน้มที่แข็งแกร่งในระยะยาว..."

[CRITICAL INSTRUCTION]
Review the preliminary signal and confirm or override with expert judgment.
Respond ONLY with a valid JSON object. No markdown. No text before or after.

{{
  "signal": "ACCUMULATE" | "BUY" | "WATCH" | "HOLD" | "REDUCE" | "SELL",
  "confidence": "high" | "medium" | "low",
  "reasoning": "2-3 concise English sentences covering data quality, trend alignment, and key catalyst (used in compact tables — keep short)",
  "risks": "specific risks that could invalidate this signal (concise English)",
  "executive_summary": "Thai — what the company IS, per EXECUTIVE SUMMARY LAYER rules (80-120 words, 2-4 paragraphs separated by \\n\\n)",
  "ai_summary": "Thai — Investment Interpreter narrative per AI SUMMARY LAYER rules (80-120 words, 2-4 paragraphs separated by \\n\\n)"
}}"""

    try:
        ai_result = call_ai(
            prompt,
            provider,
            model,
            max_tokens=4096,
            usage_operation="analyze",
        )
        parsed = safe_parse_json(ai_result["text"])
        raw_signal = parsed.get("signal", "HOLD")
        signal = raw_signal if raw_signal in _VALID_SIGNALS else "HOLD"
        capped_conf = _cap_confidence(parsed.get("confidence", "low"), max_conf)
        return {
            "symbol": symbol,
            "signal": signal,
            "confidence": capped_conf,
            "reasoning": parsed.get("reasoning", ""),
            "risks": parsed.get("risks", ""),
            "executive_summary": parsed.get("executive_summary", ""),
            "ai_summary": parsed.get("ai_summary", ""),
            "ai_provider": provider,
            "ai_model": model,
            "latency_ms": ai_result["latency_ms"],
        }
    except Exception as e:
        return {"error": f"AI error: {str(e)}"}
