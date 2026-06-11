"""In-memory optimizer run-progress registry (Phase 4C.1 Processing Experience).

Tracks which pipeline stage an /analyze-optimizer run is currently in so the
frontend can render a real Operations Timeline instead of a generic spinner.
Stage markers are written by the optimizer pipeline (handler + optional
on_stage callback inside run_layered_optimizer) and read by
GET /operations-center/optimizer-progress.

Thread-safety: writes come from `asyncio.to_thread` worker threads while reads
happen on the event loop, so a `threading.Lock` (not asyncio.Lock) guards the
registry.

Scope note: in-memory and per-process — correct for the current single-worker
uvicorn deployment.  A multi-worker deployment would need an external store
(e.g. Redis); out of scope for this phase.
"""
import threading
from datetime import datetime

# Ordered pipeline stages with plain-Thai labels for the timeline UI.
_STAGES: list[tuple[str, str]] = [
    ("PREPARING_DATA", "เตรียมข้อมูลหุ้นและคะแนน"),
    ("ANALYZING_CONTEXT", "วิเคราะห์ภาวะตลาดและนโยบาย"),
    ("LAYER1_PROPOSAL", "AI ชั้นที่ 1 ร่างข้อเสนอ"),
    ("LAYER2_CHALLENGE", "AI ชั้นที่ 2 ตรวจสอบและโต้แย้ง"),
    ("LAYER3_ARBITRATION", "AI ชั้นที่ 3 ตรวจสอบความเสี่ยงขั้นสุดท้าย"),
    ("STABILIZING", "ตรวจสอบความเสถียรของคำแนะนำ"),
    ("SAVING", "บันทึกผลการวิเคราะห์"),
]
_STAGE_KEYS = [k for k, _ in _STAGES]

_RETENTION_SECONDS = 600   # purge finished runs after 10 minutes
_STALE_RUN_SECONDS = 900   # a "running" entry idle this long is presumed crashed

_runs: dict[int, dict] = {}  # keyed by portfolio_id
_lock = threading.Lock()


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def start_run(portfolio_id: int) -> None:
    """Register a new optimizer run for a portfolio (resets any previous entry)."""
    with _lock:
        _runs[portfolio_id] = {
            "running": True,
            "stage": _STAGE_KEYS[0],
            "ok": None,
            "started_at": _now(),
            "updated_at": _now(),
            "finished_at": None,
            "stage_history": [{"key": _STAGE_KEYS[0], "started_at": _now()}],
        }


def mark_stage(portfolio_id: int, stage: str) -> None:
    """Advance the run to *stage*. No-op for unknown portfolios or stages."""
    if stage not in _STAGE_KEYS:
        return
    with _lock:
        run = _runs.get(portfolio_id)
        if run is None or not run["running"]:
            return
        if run["stage"] != stage:
            run["stage"] = stage
            run["stage_history"].append({"key": stage, "started_at": _now()})
        run["updated_at"] = _now()


def finish_run(portfolio_id: int, ok: bool) -> None:
    """Mark the run finished (success or failure)."""
    with _lock:
        run = _runs.get(portfolio_id)
        if run is None:
            return
        run["running"] = False
        run["ok"] = ok
        run["stage"] = "DONE" if ok else "FAILED"
        run["updated_at"] = _now()
        run["finished_at"] = _now()


def _purge_stale() -> None:
    """Drop finished entries older than the retention window. Caller holds _lock."""
    cutoff = datetime.utcnow().timestamp() - _RETENTION_SECONDS
    stale = [
        pid for pid, run in _runs.items()
        if not run["running"] and run["finished_at"]
        and datetime.fromisoformat(run["finished_at"].rstrip("Z")).timestamp() < cutoff
    ]
    for pid in stale:
        del _runs[pid]


def get_progress(portfolio_id: int) -> dict:
    """Current progress for a portfolio's optimizer run (poll-friendly shape)."""
    with _lock:
        _purge_stale()
        run = _runs.get(portfolio_id)
        # Crash guard: the handler can fail without reaching finish_run() —
        # treat a long-idle "running" entry as a failed run.
        if run is not None and run["running"]:
            idle = datetime.utcnow().timestamp() - datetime.fromisoformat(
                run["updated_at"].rstrip("Z")).timestamp()
            if idle > _STALE_RUN_SECONDS:
                run["running"] = False
                run["ok"] = False
                run["stage"] = "FAILED"
                run["finished_at"] = _now()
        if run is None:
            return {
                "running": False,
                "stage": None,
                "ok": None,
                "stages": [],
                "started_at": None,
                "updated_at": None,
            }

        seen = {h["key"]: h["started_at"] for h in run["stage_history"]}
        current = run["stage"]
        current_idx = _STAGE_KEYS.index(current) if current in _STAGE_KEYS else len(_STAGE_KEYS)
        stages: list[dict] = []
        for idx, (key, label_th) in enumerate(_STAGES):
            if not run["running"]:
                status = "done" if run["ok"] else ("done" if key in seen else "pending")
            elif idx < current_idx:
                status = "done"
            elif idx == current_idx:
                status = "active"
            else:
                status = "pending"
            stages.append({
                "key": key,
                "label_th": label_th,
                "status": status,
                "started_at": seen.get(key),
            })

        return {
            "running": run["running"],
            "stage": run["stage"],
            "ok": run["ok"],
            "stages": stages,
            "started_at": run["started_at"],
            "updated_at": run["updated_at"],
        }
