"""
System Health — read-only aggregation for the AI Analytics "System Health" dashboard.

This module computes NOTHING new: every field is a direct read or a trivial
aggregate (MAX/COUNT/AVG) of state that already exists elsewhere (UserUsage,
OptimizerHistory, BenchmarkPrice, PortfolioSnapshot, the snapshot scheduler,
ai-model.json). No status/health-level thresholds are decided here — those
live once, on the frontend, in lib/ai-analytics-transformers.ts, so every
card in the dashboard shares the same green/amber/red/gray model. Fields that
have no real backing data are returned as null; the frontend renders null as
"Unknown" rather than inventing a value.
"""

from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session

from models.database import UserUsage, OptimizerHistory, BenchmarkPrice, PortfolioSnapshot
from services.ai_client import _load_config
from services.snapshot_scheduler import get_scheduler_status
import json as _json
import os


def _iso(dt: datetime | None) -> str | None:
    return (dt.isoformat() + "Z") if dt else None


# ── Shared reliability aggregate (also used by GET /stats/ai-analytics) ──────

def compute_ai_reliability(db: Session) -> dict:
    """Single source of truth for optimizer fallback-rate and the (currently
    untracked) reliability metrics. UserUsage only records calls that
    completed, so success/error/timeout/parse-failure rates aren't derivable
    yet and stay null rather than being guessed at."""
    optimize_total = db.query(func.count(UserUsage.id)).filter(UserUsage.operation == "optimize").scalar() or 0
    optimize_fallback = (
        db.query(func.count(UserUsage.id))
        .filter(UserUsage.operation == "optimize", UserUsage.layer == "fallback")
        .scalar() or 0
    )
    return {
        "fallback_rate": round(optimize_fallback / optimize_total, 4) if optimize_total else None,
        "success_rate": None,
        "json_parse_success_rate": None,
        "api_error_rate": None,
        "timeout_rate": None,
        "max_token_stop_rate": None,
    }


def _ai_providers(db: Session) -> list[dict]:
    """configured (env key present) + last_success/avg_latency from UserUsage,
    grouped strictly by provider (leaderboard groups by provider+model, a
    different granularity — this is not a duplicate of that computation)."""
    config = _load_config()
    providers_cfg = config.get("providers", {})

    since_24h = datetime.utcnow() - timedelta(hours=24)
    rows = (
        db.query(
            UserUsage.provider,
            func.max(UserUsage.created_at).label("last_success"),
            func.count(UserUsage.id).label("call_count_24h"),
            func.avg(UserUsage.latency_ms).label("avg_latency_ms"),
        )
        .filter(UserUsage.created_at >= since_24h)
        .group_by(UserUsage.provider)
        .all()
    )
    recent_by_provider = {r.provider: r for r in rows}

    last_overall = dict(
        db.query(UserUsage.provider, func.max(UserUsage.created_at))
        .group_by(UserUsage.provider)
        .all()
    )

    out = []
    for provider, cfg in providers_cfg.items():
        env_key = cfg.get("envKey")
        configured = bool(env_key and os.environ.get(env_key))
        recent = recent_by_provider.get(provider)
        out.append({
            "provider": provider,
            "configured": configured,
            "last_success_at": _iso(last_overall.get(provider)),
            "call_count_24h": int(recent.call_count_24h) if recent else 0,
            "avg_latency_ms_24h": round(recent.avg_latency_ms) if recent and recent.avg_latency_ms else None,
            # Reachability requires an active health-check ping, which this
            # backend doesn't perform — never invented, always null/unknown.
            "reachable": None,
        })
    return out


def _optimizer_pipeline(db: Session, ws: int) -> dict:
    latest = (
        db.query(OptimizerHistory)
        .filter(OptimizerHistory.workspace_id == ws)
        .order_by(OptimizerHistory.analyzed_at.desc())
        .first()
    )
    if latest is None:
        return {
            "last_run_at": None,
            "layer1_latency_ms": None, "layer2_latency_ms": None,
            "layer3_latency_ms": None, "total_latency_ms": None,
            "layer1_error": None, "layer2_error": None, "layer3_error": None,
            "fallback_mode": None,
            "policy_engine_status": None,
        }

    try:
        result = _json.loads(latest.result_json or "{}")
    except Exception:
        result = {}

    def _has_error(layer_key: str) -> bool | None:
        layer_result = result.get(layer_key)
        if not isinstance(layer_result, dict):
            return None
        return "error" in layer_result

    return {
        "last_run_at": _iso(latest.analyzed_at),
        "layer1_latency_ms": latest.layer1_latency_ms,
        "layer2_latency_ms": latest.layer2_latency_ms,
        "layer3_latency_ms": latest.layer3_latency_ms,
        "total_latency_ms": latest.total_latency_ms,
        "layer1_error": _has_error("layer1_result"),
        "layer2_error": _has_error("layer2_result"),
        "layer3_error": _has_error("layer3_result"),
        "fallback_mode": bool(result.get("fallback_mode", False)),
        "policy_engine_status": result.get("policy_engine_status"),
    }


def _market_data(db: Session) -> dict:
    latest_update = (
        db.query(func.max(BenchmarkPrice.updated_at))
        .filter(BenchmarkPrice.updated_at.isnot(None))
        .scalar()
    )
    age_minutes = None
    if latest_update:
        age_minutes = round((datetime.utcnow() - latest_update).total_seconds() / 60.0, 1)

    sync_counts = dict(
        db.query(BenchmarkPrice.sync_status, func.count(BenchmarkPrice.id))
        .filter(BenchmarkPrice.sync_status.isnot(None))
        .group_by(BenchmarkPrice.sync_status)
        .all()
    )

    return {
        "latest_update_at": _iso(latest_update),
        "age_minutes": age_minutes,
        "sync_status_counts": {
            "ok": int(sync_counts.get("ok", 0)),
            "error": int(sync_counts.get("error", 0)),
            "stale": int(sync_counts.get("stale", 0)),
        },
    }


def _portfolio_engine(db: Session, ws: int) -> dict:
    scheduler = get_scheduler_status()
    last_snapshot_at = (
        db.query(func.max(PortfolioSnapshot.created_at))
        .filter(PortfolioSnapshot.workspace_id == ws)
        .scalar()
    )
    return {
        "snapshot_scheduler_status": (scheduler.get("last_run") or {}).get("status"),
        "snapshot_scheduler_last_run_at": (scheduler.get("last_run") or {}).get("completed_at")
            or (scheduler.get("last_run") or {}).get("triggered_at"),
        "last_snapshot_at": _iso(last_snapshot_at),
        # No runtime health signal exists for these today — real gap, not invented.
        "replay_engine_status": None,
        "calculation_engine_status": None,
    }


def _background_jobs(db: Session, market_data: dict) -> dict:
    scheduler = get_scheduler_status()
    return {
        "snapshot_scheduler": {
            "status": (scheduler.get("last_run") or {}).get("status"),
            "last_run_at": (scheduler.get("last_run") or {}).get("completed_at")
                or (scheduler.get("last_run") or {}).get("triggered_at"),
            "next_run_time": scheduler["jobs"][0]["next_run_time"] if scheduler.get("jobs") else None,
        },
        # No in-process job for this — prices are synced by an external GitHub
        # Actions workflow (scripts/sync_prices.py). BenchmarkPrice.updated_at
        # is the closest real proxy for "last successful run" of that job.
        "market_update": {
            "last_run_at": market_data["latest_update_at"],
            "note": "Inferred from BenchmarkPrice.updated_at — GitHub Actions job has no in-app run log.",
        },
        # No reminder job exists anywhere in this backend today.
        "reminders": {
            "last_run_at": None,
            "note": "No reminder job is registered in this backend.",
        },
    }


def _optional_metrics(db: Session) -> dict:
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    rows = db.query(UserUsage).filter(UserUsage.created_at >= today_start).all()
    call_count = len(rows)
    latencies = [r.latency_ms for r in rows if r.latency_ms is not None]
    total_cost = sum(r.total_cost_usd for r in rows)
    return {
        "requests_today": call_count,
        "avg_latency_ms_today": round(sum(latencies) / len(latencies)) if latencies else None,
        "avg_cost_usd_today": round(total_cost / call_count, 6) if call_count else None,
        # Not tracked anywhere yet — same gap as the Reliability section.
        "failure_rate": None,
        "retry_count": None,
    }


def compute_system_health(db: Session, ws: int) -> dict:
    market_data = _market_data(db)
    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "ai_providers": _ai_providers(db),
        "optimizer_pipeline": _optimizer_pipeline(db, ws),
        "market_data": market_data,
        "portfolio_engine": _portfolio_engine(db, ws),
        "prompt_pipeline": compute_ai_reliability(db),
        "background_jobs": _background_jobs(db, market_data),
        "optional_metrics": _optional_metrics(db),
    }
