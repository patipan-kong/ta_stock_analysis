"""Goal Profile service layer (Phase 4C.3 Goal Discovery Wizard).

Single access point for the user's investment goal profile so future phases
(4A Net Worth, 4B Goal-Based Planning, Policy Engine personalization, MUJI
mode) can read goal_type / goal_priority / risk_personality WITHOUT touching
the Portfolio schema again.

Discovery + personalization data only — NO projections, NO forecasts, NO
optimizer behavior changes live here.

Public API:
    valid_goal_type(raw)         -> str | None
    valid_goal_priority(raw)     -> str | None
    valid_risk_personality(raw)  -> str | None
    valid_goal_date(raw)         -> str | None   (normalized YYYY-MM-DD)
    build_goal_profile(portfolio) -> dict        (None-safe, always a dict)
    get_goal_profile(db, ws_id, portfolio_id) -> dict | None
    update_goal_profile(db, portfolio, fields) -> dict
"""
from datetime import date

from sqlalchemy.orm import Session

from models.database import Portfolio

# ── Vocabulary (codes are the stored values; labels are display-only) ─────────

GOAL_TYPES: dict[str, dict[str, str]] = {
    "WEDDING":           {"emoji": "💍", "label_th": "งานแต่งงาน"},
    "HOUSE":             {"emoji": "🏠", "label_th": "ซื้อบ้าน"},
    "EDUCATION":         {"emoji": "👶", "label_th": "การศึกษา"},
    "RETIREMENT":        {"emoji": "🌴", "label_th": "เกษียณ"},
    "FINANCIAL_FREEDOM": {"emoji": "💰", "label_th": "อิสรภาพทางการเงิน"},
    "WEALTH_GROWTH":     {"emoji": "🚀", "label_th": "สร้างความมั่งคั่งระยะยาว"},
    "OTHER":             {"emoji": "✨", "label_th": "เป้าหมายอื่น"},
}

GOAL_PRIORITIES: dict[str, dict[str, str]] = {
    "ESSENTIAL":    {"label_th": "จำเป็นต้องสำเร็จตามกำหนด"},
    "IMPORTANT":    {"label_th": "สำคัญมาก แต่ยืดหยุ่นได้บ้าง"},
    "ASPIRATIONAL": {"label_th": "ความฝันหรือเป้าหมายระยะยาว"},
}

RISK_PERSONALITIES: dict[str, dict[str, str]] = {
    "AGGRESSIVE":   {"label_th": "เชิงรุก"},
    "MODERATE":     {"label_th": "ปานกลาง"},
    "CONSERVATIVE": {"label_th": "ระมัดระวัง"},
}


# ── Validators (normalize input; None for missing/invalid) ───────────────────

def _valid_code(raw: str | None, vocab: dict[str, dict[str, str]]) -> str | None:
    if not raw or not isinstance(raw, str):
        return None
    code = raw.strip().upper()
    return code if code in vocab else None


def valid_goal_type(raw: str | None) -> str | None:
    return _valid_code(raw, GOAL_TYPES)


def valid_goal_priority(raw: str | None) -> str | None:
    return _valid_code(raw, GOAL_PRIORITIES)


def valid_risk_personality(raw: str | None) -> str | None:
    return _valid_code(raw, RISK_PERSONALITIES)


def valid_goal_date(raw: str | None) -> str | None:
    """Normalize to YYYY-MM-DD; None for missing/unparseable input."""
    if not raw or not isinstance(raw, str):
        return None
    try:
        return date.fromisoformat(raw.strip()[:10]).isoformat()
    except ValueError:
        return None


# ── Profile assembly ──────────────────────────────────────────────────────────

def build_goal_profile(portfolio: Portfolio | None) -> dict:
    """Display-ready goal profile dict. None-safe — always returns a dict.

    `configured` is True once the wizard stored a goal_type; all other fields
    stay independently nullable for backward compatibility.
    """
    if portfolio is None:
        return {
            "portfolio_id": None,
            "configured": False,
            "goal_type": None, "goal_emoji": None, "goal_label_th": None,
            "goal_target_value": None,
            "goal_target_date": None,
            "goal_priority": None, "goal_priority_label_th": None,
            "risk_personality": None, "risk_personality_label_th": None,
        }
    goal_type = valid_goal_type(portfolio.goal_type)
    priority = valid_goal_priority(portfolio.goal_priority)
    risk = valid_risk_personality(portfolio.risk_personality)
    return {
        "portfolio_id": portfolio.id,
        "configured": goal_type is not None,
        "goal_type": goal_type,
        "goal_emoji": GOAL_TYPES[goal_type]["emoji"] if goal_type else None,
        "goal_label_th": GOAL_TYPES[goal_type]["label_th"] if goal_type else None,
        "goal_target_value": portfolio.goal_target_value,
        "goal_target_date": valid_goal_date(portfolio.goal_target_date),
        "goal_priority": priority,
        "goal_priority_label_th": GOAL_PRIORITIES[priority]["label_th"] if priority else None,
        "risk_personality": risk,
        "risk_personality_label_th": RISK_PERSONALITIES[risk]["label_th"] if risk else None,
    }


def get_goal_profile(db: Session, ws_id: int, portfolio_id: int) -> dict | None:
    """Goal profile for one portfolio. None if the portfolio doesn't exist."""
    portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.id == portfolio_id, Portfolio.workspace_id == ws_id)
        .first()
    )
    if portfolio is None:
        return None
    return build_goal_profile(portfolio)


def update_goal_profile(db: Session, portfolio: Portfolio, fields: dict) -> dict:
    """Apply validated goal fields (already normalized by the caller) and
    return the fresh profile.  Only keys present in `fields` are written, so
    partial updates never clobber the rest of the profile.
    """
    for key in ("goal_type", "goal_priority", "goal_target_date",
                "risk_personality", "goal_target_value"):
        if key in fields:
            setattr(portfolio, key, fields[key])
    db.commit()
    db.refresh(portfolio)
    return build_goal_profile(portfolio)
