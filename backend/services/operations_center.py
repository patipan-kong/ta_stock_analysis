"""Operations Center status aggregation (Phase 4C.1).

Read-only aggregation layer over existing services — NO business logic is
duplicated or modified here.  Pulls together:

  - regime_detector.detect_regime()      (60s TTL cache, local to this module)
  - latest OptimizerHistory + RecommendationSnapshot (consensus / policy)
  - latest PortfolioSnapshot              (NAV, daily return)
  - latest APPROVED UserExecutionDecision (days since rebalance)
  - BenchmarkPrice recency                (market data freshness)

and derives 6 station health statuses (GREEN | YELLOW | RED) plus the
MUJI-mode Thai translation block.

Public API:
    build_operations_status(db, ws_id, portfolio_id) -> dict
"""
import json
import logging
import threading
import time
from datetime import datetime, date, timedelta

from sqlalchemy.orm import Session

from models.database import (
    BenchmarkPrice,
    OptimizerHistory,
    Portfolio,
    PortfolioSnapshot,
    RecommendationSnapshot,
    UserExecutionDecision,
)
from services.goal_profile import build_goal_profile
from services.translations.muji_translator import (
    build_muji_translation,
    station_label_th,
    translate_consensus,
    translate_regime,
)

log = logging.getLogger(__name__)

# ── Regime cache (60s TTL — keeps the 60s frontend poll cheap) ───────────────
# Lives ONLY here; regime_detector logic is untouched.

_REGIME_TTL_SECONDS = 60.0
_regime_cache: dict[str, tuple[float, dict | None]] = {}
_regime_lock = threading.Lock()


def _get_regime_cached(db: Session) -> dict | None:
    """detect_regime() with a 60s in-process TTL cache. None on failure."""
    now = time.monotonic()
    with _regime_lock:
        cached = _regime_cache.get("regime")
        if cached and now - cached[0] < _REGIME_TTL_SECONDS:
            return cached[1]
    try:
        from services.analytics.regime_detector import detect_regime
        result: dict | None = detect_regime(db)
    except Exception as exc:
        log.error("[OPS-CENTER] regime detection failed: %s", exc)
        result = None
    with _regime_lock:
        _regime_cache["regime"] = (now, result)
    return result


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_json(raw: str | None) -> dict | None:
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else None
    except (ValueError, TypeError):
        return None


def _age_in_days(date_str: str | None) -> int | None:
    """Calendar days between a YYYY-MM-DD string and today (UTC). None if missing."""
    if not date_str:
        return None
    try:
        d = date.fromisoformat(date_str[:10])
    except ValueError:
        return None
    return (datetime.utcnow().date() - d).days


def _business_age(days: int | None) -> int | None:
    """Weekend-tolerant age: a Monday reading of Friday data counts as 1 day."""
    if days is None:
        return None
    weekday = datetime.utcnow().date().weekday()  # Mon=0 … Sun=6
    if weekday == 0 and days <= 3:  # Monday: Fri/Sat/Sun gap is normal
        return 1
    if weekday == 6 and days <= 2:  # Sunday: Fri data is fresh
        return 1
    if weekday == 5 and days <= 1:  # Saturday: Fri data is fresh
        return 1
    return days


def _portfolio_summary(
    db: Session, ws_id: int, portfolio_id: int, goal_target_value: float | None
) -> tuple[dict, PortfolioSnapshot | None, int | None]:
    snap = (
        db.query(PortfolioSnapshot)
        .filter(
            PortfolioSnapshot.portfolio_id == portfolio_id,
            PortfolioSnapshot.workspace_id == ws_id,
        )
        .order_by(PortfolioSnapshot.snapshot_date.desc())
        .first()
    )

    last_approved = (
        db.query(UserExecutionDecision)
        .filter(
            UserExecutionDecision.portfolio_id == portfolio_id,
            UserExecutionDecision.workspace_id == ws_id,
            UserExecutionDecision.decision == "APPROVED",
        )
        .order_by(UserExecutionDecision.executed_at.desc())
        .first()
    )
    days_since_rebalance: int | None = None
    if last_approved and last_approved.executed_at:
        days_since_rebalance = max(0, (datetime.utcnow() - last_approved.executed_at).days)

    total_value = snap.total_value if snap else None
    goal_progress_pct: float | None = None
    if total_value is not None and goal_target_value and goal_target_value > 0:
        goal_progress_pct = round(total_value / goal_target_value * 100, 1)

    summary = {
        "portfolio_value": total_value,
        "daily_return_pct": snap.daily_return_pct if snap else None,
        "goal_target_value": goal_target_value,
        "goal_progress_pct": goal_progress_pct,
        "days_since_last_rebalance": days_since_rebalance,
        "snapshot_date": snap.snapshot_date if snap else None,
    }
    return summary, snap, days_since_rebalance


def _latest_optimizer_context(
    db: Session, ws_id: int, portfolio_id: int
) -> tuple[OptimizerHistory | None, RecommendationSnapshot | None, dict | None, dict | None]:
    history = (
        db.query(OptimizerHistory)
        .filter(
            OptimizerHistory.portfolio_id == portfolio_id,
            OptimizerHistory.workspace_id == ws_id,
        )
        .order_by(OptimizerHistory.analyzed_at.desc())
        .first()
    )
    rec_snap: RecommendationSnapshot | None = None
    if history:
        rec_snap = (
            db.query(RecommendationSnapshot)
            .filter(RecommendationSnapshot.optimizer_history_id == history.id)
            .first()
        )
    consensus = _safe_json(rec_snap.consensus_json) if rec_snap else None
    policy = _safe_json(rec_snap.active_policy_json) if rec_snap else None
    return history, rec_snap, consensus, policy


def _derive_risk_level(consensus: dict | None, regime_ctx: dict | None) -> str | None:
    if consensus and consensus.get("final_risk_level"):
        return str(consensus["final_risk_level"]).lower()
    if regime_ctx and regime_ctx.get("regime"):
        regime = str(regime_ctx["regime"]).upper()
        if regime == "RISK_ON":
            return "low"
        if regime in ("SIDEWAYS", "TRANSITION_RISK_ON", "TRANSITION_RISK_OFF"):
            return "medium"
        if regime in ("RISK_OFF", "HIGH_VOLATILITY", "DEFENSIVE_REGIME"):
            return "high"
    return None


# ── Station health ────────────────────────────────────────────────────────────

def _station(key: str, status: str, detail: str, detail_th: str) -> dict:
    return {"status": status, "label_th": station_label_th(key), "detail": detail, "detail_th": detail_th}


def _compute_agent_health(
    db: Session,
    regime_ctx: dict | None,
    history: OptimizerHistory | None,
    consensus: dict | None,
    policy: dict | None,
    snap: PortfolioSnapshot | None,
    rec_snap: RecommendationSnapshot | None,
) -> dict[str, dict]:
    health: dict[str, dict] = {}

    # market_data_station — freshness of benchmark prices and/or NAV snapshots
    latest_bench = db.query(BenchmarkPrice.price_date).order_by(BenchmarkPrice.price_date.desc()).first()
    bench_age = _business_age(_age_in_days(latest_bench[0] if latest_bench else None))
    snap_age = _business_age(_age_in_days(snap.snapshot_date if snap else None))
    data_age = min(a for a in (bench_age, snap_age) if a is not None) if (bench_age is not None or snap_age is not None) else None
    if data_age is None:
        health["market_data_station"] = _station(
            "market_data_station", "RED", "No market data recorded yet", "ยังไม่มีข้อมูลตลาดในระบบ")
    elif data_age <= 1:
        health["market_data_station"] = _station(
            "market_data_station", "GREEN", f"Prices current (age {data_age}d)", "ข้อมูลราคาอัปเดตล่าสุด")
    elif data_age <= 3:
        health["market_data_station"] = _station(
            "market_data_station", "YELLOW", f"Prices {data_age} days old", f"ข้อมูลราคาเก่ากว่าปกติ ({data_age} วัน)")
    else:
        health["market_data_station"] = _station(
            "market_data_station", "RED", f"Prices stale ({data_age} days old)", f"ข้อมูลราคาไม่อัปเดตมา {data_age} วัน")

    # macro_station — regime detector health
    if regime_ctx is None:
        health["macro_station"] = _station(
            "macro_station", "RED", "Regime detection unavailable", "ระบบวิเคราะห์ภาวะตลาดขัดข้อง")
    else:
        stability = str(regime_ctx.get("transition_stability") or "STABLE").upper()
        if stability == "STABLE":
            health["macro_station"] = _station(
                "macro_station", "GREEN", f"Regime {regime_ctx.get('regime')} (stable)", "ภาวะตลาดมีเสถียรภาพ")
        elif stability == "TRANSITIONING":
            health["macro_station"] = _station(
                "macro_station", "YELLOW", f"Regime {regime_ctx.get('regime')} (transitioning)", "ภาวะตลาดกำลังเปลี่ยนผ่าน")
        else:  # VOLATILE
            health["macro_station"] = _station(
                "macro_station", "RED", f"Regime {regime_ctx.get('regime')} (volatile)", "ภาวะตลาดแกว่งตัวรุนแรง")

    # risk_desk — active policy warnings
    if policy is None:
        health["risk_desk"] = _station(
            "risk_desk", "YELLOW", "No active policy yet (run optimizer)", "ยังไม่มีนโยบายความเสี่ยง — รัน Optimizer ก่อน")
    elif policy.get("emergency_override"):
        health["risk_desk"] = _station(
            "risk_desk", "RED", f"Emergency override active: {policy.get('emergency_reason') or 'unspecified'}",
            "ระบบเข้าสู่โหมดป้องกันพิเศษ")
    elif policy.get("violations"):
        v = policy["violations"]
        health["risk_desk"] = _station(
            "risk_desk", "YELLOW", f"{len(v)} policy violation(s): {', '.join(map(str, v[:3]))}",
            f"พบประเด็นความเสี่ยง {len(v)} รายการ")
    else:
        health["risk_desk"] = _station(
            "risk_desk", "GREEN", "No policy violations", "ไม่พบประเด็นความเสี่ยง")

    # quant_corner — factor/DNA analytics freshness
    run_age = None
    if history and history.analyzed_at:
        run_age = (datetime.utcnow() - history.analyzed_at).days
    has_quant = bool(rec_snap and (rec_snap.portfolio_dna_json or rec_snap.style_drift_json))
    if not has_quant:
        health["quant_corner"] = _station(
            "quant_corner", "RED", "No factor analytics yet", "ยังไม่มีข้อมูลวิเคราะห์เชิงปริมาณ")
    elif run_age is not None and run_age <= 7:
        health["quant_corner"] = _station(
            "quant_corner", "GREEN", f"Factor analytics current ({run_age}d)", "ข้อมูลวิเคราะห์เชิงปริมาณเป็นปัจจุบัน")
    else:
        health["quant_corner"] = _station(
            "quant_corner", "YELLOW", f"Factor analytics {run_age} days old", "ข้อมูลวิเคราะห์เชิงปริมาณเริ่มเก่า")

    # portfolio_lab — NAV snapshot engine
    if snap is None:
        health["portfolio_lab"] = _station(
            "portfolio_lab", "RED", "No portfolio snapshot yet", "ยังไม่มีบันทึกมูลค่าพอร์ต")
    elif snap_age is not None and snap_age <= 1:
        health["portfolio_lab"] = _station(
            "portfolio_lab", "GREEN", f"Snapshot current ({snap.snapshot_date})", "บันทึกมูลค่าพอร์ตเป็นปัจจุบัน")
    elif snap_age is not None and snap_age <= 7:
        health["portfolio_lab"] = _station(
            "portfolio_lab", "YELLOW", f"Snapshot {snap_age} days old", f"บันทึกมูลค่าพอร์ตเก่า {snap_age} วัน")
    else:
        health["portfolio_lab"] = _station(
            "portfolio_lab", "RED", f"Snapshot stale ({snap.snapshot_date})", "บันทึกมูลค่าพอร์ตไม่อัปเดตนาน")

    # consensus_room — optimizer agreement state
    if history is None:
        health["consensus_room"] = _station(
            "consensus_room", "YELLOW", "Optimizer never run", "ยังไม่เคยรันการวิเคราะห์")
    else:
        ctype = str((consensus or {}).get("consensus_type") or "").upper()
        decision = str((consensus or {}).get("consensus_decision") or "").upper()
        if ctype in ("RISK_CONFLICT", "STRATEGIC_CONFLICT"):
            health["consensus_room"] = _station(
                "consensus_room", "RED", f"AI conflict: {ctype}", "AI เห็นต่างกัน ต้องการการตัดสินใจ")
        elif ctype in ("PARTIAL_CONSENSUS", "WEAK_CONSENSUS") or decision == "REVIEW":
            health["consensus_room"] = _station(
                "consensus_room", "YELLOW", f"Partial agreement: {ctype or decision}", "AI เห็นตรงกันบางส่วน")
        elif ctype:
            health["consensus_room"] = _station(
                "consensus_room", "GREEN", f"Consensus: {ctype}", "AI เห็นพ้องต้องกัน")
        else:
            health["consensus_room"] = _station(
                "consensus_room", "YELLOW", "Last run has no consensus record", "ผลการวิเคราะห์ล่าสุดไม่มีบันทึกฉันทามติ")

    return health


# ── Public entry ──────────────────────────────────────────────────────────────

def build_operations_status(db: Session, ws_id: int, portfolio_id: int) -> dict:
    """Aggregate the full Operations Center status payload for one portfolio."""
    portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.id == portfolio_id, Portfolio.workspace_id == ws_id)
        .first()
    )
    goal_target_value = portfolio.goal_target_value if portfolio else None

    summary, snap, days_since_rebalance = _portfolio_summary(db, ws_id, portfolio_id, goal_target_value)
    history, rec_snap, consensus, policy = _latest_optimizer_context(db, ws_id, portfolio_id)
    regime_ctx = _get_regime_cached(db)

    regime_name = regime_ctx.get("regime") if regime_ctx else None
    risk_level = _derive_risk_level(consensus, regime_ctx)
    regime_th = translate_regime(regime_name)

    health = _compute_agent_health(db, regime_ctx, history, consensus, policy, snap, rec_snap)
    station_statuses = {k: v["status"] for k, v in health.items()}

    consensus_type = (consensus or {}).get("consensus_type")
    consensus_decision = (consensus or {}).get("consensus_decision")
    emergency_override = bool((policy or {}).get("emergency_override"))

    muji = build_muji_translation(
        regime=regime_name,
        consensus_type=consensus_type,
        consensus_decision=consensus_decision,
        risk_level=risk_level,
        emergency_override=emergency_override,
        station_statuses=station_statuses,
        goal_progress_pct=summary["goal_progress_pct"],
        days_since_rebalance=days_since_rebalance,
    )

    policy_block: dict | None = None
    if policy is not None:
        policy_block = {
            "strictness_level": policy.get("strictness_level"),
            "violations": policy.get("violations") or [],
            "emergency_override": emergency_override,
            "emergency_reason": policy.get("emergency_reason"),
            "deployment_bias": policy.get("deployment_bias"),
            "policy_narrative": policy.get("policy_narrative"),
            "hard_constraints": policy.get("hard_constraints") or {},
        }

    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "portfolio_id": portfolio_id,
        "portfolio_name": portfolio.name if portfolio else None,
        "mode_capabilities": {"modes": ["MUJI", "QUANT"], "default_mode": "MUJI"},
        "portfolio_summary": summary,
        "goal_profile": build_goal_profile(portfolio),  # Phase 4C.3 — discovery data, display only
        "market": {
            "regime": regime_name,
            "confidence_pct": regime_ctx.get("confidence_pct") if regime_ctx else None,
            "transition_stability": regime_ctx.get("transition_stability") if regime_ctx else None,
            "vix_level": regime_ctx.get("vix_level") if regime_ctx else None,
            "regime_duration_days": regime_ctx.get("regime_duration_days") if regime_ctx else None,
            "risk_level": risk_level,
            "label_th": regime_th["label"],
            "description_th": regime_th["description"],
            "narrative": regime_ctx.get("narrative") if regime_ctx else None,
        },
        "optimizer": {
            "last_run_at": history.analyzed_at.isoformat() + "Z" if history and history.analyzed_at else None,
            "optimizer_status": history.optimizer_status if history else None,
            "consensus_status": consensus_type,
            "consensus_decision": consensus_decision,
            "consensus_score": (consensus or {}).get("consensus_strength_score"),
            "final_risk_level": (consensus or {}).get("final_risk_level"),
            "recommendation_summary_th": translate_consensus(consensus_type),
            "recommended_action": (consensus or {}).get("recommended_action"),
        },
        "policy": policy_block,
        "agent_health": health,
        "muji_translation": muji,
    }
