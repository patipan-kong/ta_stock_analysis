"""MUJI-mode translation layer — deterministic Thai phrasing (Phase 4C.1).

Converts quantitative system states (regime, consensus, risk, station health)
into plain Thai sentences for novice investors.  Pure lookup tables and
templates — NO LLM calls, NO database access.  All inputs are None-safe:
unknown or missing values fall back to neutral "no data yet" phrasing.

Public API:
    translate_regime(regime)            -> {"label": ..., "description": ...}
    translate_consensus(consensus_type) -> str
    translate_risk(risk_level)          -> str
    translate_decision(decision)        -> {"action_th": ..., "severity": ...}
    station_label_th(station_key)       -> str
    build_muji_translation(...)         -> {"headline", "summary", "action_required"}
"""

# ── Mapping tables ────────────────────────────────────────────────────────────

REGIME_TH: dict[str, dict[str, str]] = {
    "RISK_ON": {
        "label": "ตลาดอยู่ในช่วงขาขึ้น",
        "description": "ช่วงนี้ภาพรวมตลาดสดใสดีค่ะ ถือสินทรัพย์ตามแผนเดิมได้สบายใจเลยนะ",
    },
    "RISK_OFF": {
        "label": "ตลาดอยู่ในช่วงขาลง",
        "description": "ตลาดมีแรงขาย ควรเน้นความปลอดภัยและถือเงินสดมากขึ้น",
    },
    "SIDEWAYS": {
        "label": "ตลาดทรงตัว",
        "description": "ตลาดยังไม่มีทิศทางชัดเจน ถือตามแผนเดิมได้",
    },
    "HIGH_VOLATILITY": {
        "label": "ตลาดผันผวนสูง",
        "description": "ช่วงนี้ตลาดผันผวนกว่าปกติ ควรใจเย็นก่อนลงทุนเพิ่ม",
    },
    "DEFENSIVE_REGIME": {
        "label": "ช่วงตั้งรับ",
        "description": "ระบบแนะนำให้เน้นสินทรัพย์ปลอดภัยในช่วงนี้",
    },
    "TRANSITION_RISK_ON": {
        "label": "ตลาดกำลังฟื้นตัว",
        "description": "เริ่มเห็นสัญญาณบวก แต่ยังต้องรอการยืนยัน",
    },
    "TRANSITION_RISK_OFF": {
        "label": "ตลาดเริ่มอ่อนแรง",
        "description": "เริ่มเห็นสัญญาณเสี่ยง ควรติดตามใกล้ชิด",
    },
}

_REGIME_FALLBACK: dict[str, str] = {
    "label": "ยังไม่มีข้อมูลตลาด",
    "description": "ระบบยังไม่มีข้อมูลภาวะตลาดล่าสุด",
}

CONSENSUS_TYPE_TH: dict[str, str] = {
    "STRONG_CONSENSUS": "AI ทุกตัวเห็นตรงกัน",
    "REFINED_CONSENSUS": "AI เห็นตรงกันหลังปรับปรุงข้อเสนอ",
    "PARTIAL_CONSENSUS": "AI เห็นตรงกันบางส่วน",
    "WEAK_CONSENSUS": "AI เห็นต่างกันพอสมควร",
    "RISK_CONFLICT": "พี่ๆ AI ในระบบมีมุมมองเรื่องความเสี่ยงไม่ตรงกันนิดหน่อยค่ะ",
    "STRATEGIC_CONFLICT": "AI เห็นต่างกันเชิงกลยุทธ์",
    "NO_ACTION_CONSENSUS": "AI เห็นตรงกันว่ายังไม่ต้องปรับพอร์ต",
    "NO_REBALANCE_CONSENSUS": "AI เห็นตรงกันว่ายังไม่ถึงเวลาปรับพอร์ต",
}

DECISION_TH: dict[str, dict[str, str]] = {
    "NO_ACTION": {
        "action_th": "ไม่ต้องทำอะไรตอนนี้ ถือพอร์ตต่อได้",
        "severity": "INFO",
    },
    "REVIEW": {
        "action_th": "ควรเข้าไปตรวจสอบคำแนะนำล่าสุด",
        "severity": "WARN",
    },
    "REBALANCE": {
        "action_th": "ระบบแนะนำให้ปรับพอร์ต — เปิดหน้า Optimizer เพื่อดูรายละเอียด",
        "severity": "ACTION",
    },
}

_DECISION_FALLBACK: dict[str, str] = {
    "action_th": "ยังไม่มีคำแนะนำ — ลองรันการวิเคราะห์พอร์ตครั้งแรก",
    "severity": "INFO",
}

RISK_TH: dict[str, str] = {
    "low": "ความเสี่ยงอยู่ในระดับต่ำ",
    "medium": "ความเสี่ยงอยู่ในระดับปานกลาง รับได้",
    "high": "ระดับความเสี่ยงรอบนี้ค่อนข้างพอดีๆ อยู่ในเกณฑ์ที่เราควบคุมได้ค่ะ",
}

STATION_TH: dict[str, str] = {
    "market_data_station": "สถานีข้อมูลตลาด",
    "macro_station": "สถานีภาพรวมเศรษฐกิจ",
    "risk_desk": "โต๊ะดูแลความเสี่ยง",
    "quant_corner": "มุมวิเคราะห์เชิงปริมาณ",
    "portfolio_lab": "ห้องทดลองพอร์ต",
    "consensus_room": "ห้องประชุม AI",
}


# ── Translation functions ─────────────────────────────────────────────────────

def translate_regime(regime: str | None) -> dict[str, str]:
    """Thai label + description for a market regime (fallback if unknown/None)."""
    if not regime:
        return dict(_REGIME_FALLBACK)
    return dict(REGIME_TH.get(regime.upper(), _REGIME_FALLBACK))


def translate_consensus(consensus_type: str | None) -> str:
    if not consensus_type:
        return "ยังไม่มีผลการวิเคราะห์จาก AI"
    return CONSENSUS_TYPE_TH.get(consensus_type.upper(), "ระบบ AI ให้ผลการวิเคราะห์ล่าสุดแล้ว")


def translate_risk(risk_level: str | None) -> str:
    if not risk_level:
        return "ยังไม่มีข้อมูลระดับความเสี่ยง"
    return RISK_TH.get(risk_level.lower(), "ยังไม่มีข้อมูลระดับความเสี่ยง")


def translate_decision(decision: str | None) -> dict[str, str]:
    """Thai action sentence + severity (INFO | WARN | ACTION) for a consensus decision."""
    if not decision:
        return dict(_DECISION_FALLBACK)
    return dict(DECISION_TH.get(decision.upper(), _DECISION_FALLBACK))


def station_label_th(station_key: str) -> str:
    return STATION_TH.get(station_key, station_key)


def build_muji_translation(
    regime: str | None,
    consensus_type: str | None,
    consensus_decision: str | None,
    risk_level: str | None,
    emergency_override: bool,
    station_statuses: dict[str, str],
    goal_progress_pct: float | None,
    days_since_rebalance: int | None,
) -> dict:
    """Assemble the MUJI-mode headline / summary / action block.

    Headline priority (first match wins):
      1. emergency_override          -> protective mode warning
      2. any station RED             -> attention needed
      3. decision REBALANCE          -> rebalance recommended
      4. decision REVIEW             -> something to review
      5. decision NO_ACTION          -> healthy, nothing to do
      6. no optimizer run ever       -> first-run prompt
    """
    decision = (consensus_decision or "").upper() or None
    red_stations = [k for k, v in station_statuses.items() if v == "RED"]

    if emergency_override:
        headline = "ระบบเข้าสู่โหมดป้องกันพิเศษ — โปรดตรวจสอบ"
    elif red_stations:
        headline = "พอร์ตของเรามีจุดที่อยากให้ช่วยตรวจเช็กเล็กน้อยค่ะ"
    elif decision == "REBALANCE":
        headline = "มีคำแนะนำให้ปรับพอร์ต"
    elif decision == "REVIEW":
        headline = "คำแนะนำวันนี้"
    elif decision == "NO_ACTION":
        headline = "พอร์ตของคุณอยู่ในสถานะดี ไม่ต้องทำอะไรเพิ่ม"
    else:
        headline = "ยังไม่มีข้อมูลวิเคราะห์ — ลองรัน Optimizer ครั้งแรก"

    # Summary bullets — skip pieces with no data, never render "None".
    summary: list[str] = []
    if regime:
        summary.append(translate_regime(regime)["description"])
    if risk_level:
        summary.append(translate_risk(risk_level))
    if consensus_type:
        summary.append(translate_consensus(consensus_type))
    if decision:
        summary.append(translate_decision(decision)["action_th"])
    if goal_progress_pct is not None:
        summary.append(f"พอร์ตคืบหน้า {goal_progress_pct:.0f}% สู่เป้าหมายของคุณ")
    if days_since_rebalance is not None:
        summary.append(f"ปรับพอร์ตครั้งล่าสุดเมื่อ {days_since_rebalance} วันก่อน")
    for k in red_stations:
        summary.append(f"{station_label_th(k)}แนะนำให้แวะเข้าไปช่วยดูแนวคิดของระบบสักนิดนะคะ")
    if not summary:
        summary.append("ระบบยังไม่มีข้อมูลเพียงพอ — เริ่มจากการรันการวิเคราะห์พอร์ต")

    action = translate_decision(decision)
    required = emergency_override or decision in ("REVIEW", "REBALANCE")
    link = "/optimizer" if decision in ("REVIEW", "REBALANCE") else None
    if emergency_override:
        action = {
            "action_th": "ระบบจำกัดความเสี่ยงอัตโนมัติ — เปิดหน้า Optimizer เพื่อดูรายละเอียด",
            "severity": "ACTION",
        }
        link = "/optimizer"

    return {
        "headline": headline,
        "summary": summary,
        "action_required": {
            "required": required,
            "action_th": action["action_th"],
            "severity": action["severity"],
            "link": link,
        },
    }
