"""FastAPI router — scheduler control and status.

Endpoints:
    GET  /scheduler/status
        Returns whether the APScheduler is running, all registered jobs with
        their next-fire times, lock state, today's trading-day flag, and the
        full log of the last execution (per-portfolio results, durations, errors).

    POST /scheduler/run-snapshots
        Fires generate_daily_snapshot() for all portfolios immediately as a
        background task, bypassing the holiday/weekend check.  Returns 202
        Accepted straight away; poll GET /scheduler/status to watch progress.
        Returns 409 Conflict if a run is already in progress.
"""

import asyncio
import logging

from fastapi import APIRouter, HTTPException

from services.snapshot_scheduler import (
    get_scheduler_status,
    trigger_snapshots_now,
    _job_lock,
)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


# ── GET /scheduler/status ─────────────────────────────────────────────────────

@router.get("/status")
async def scheduler_status() -> dict:
    """Return runtime state of the background scheduler.

    Response fields:
        scheduler_running     bool    — APScheduler instance is active
        lock_held             bool    — a job execution is currently in progress
        today_is_trading_day  bool    — today passes the Thai holiday check
        jobs                  list    — registered jobs:
            id                str
            name              str
            next_run_time     str|null  ISO-8601 (timezone-aware)
            trigger           str       APScheduler trigger repr
        last_run              object|null
            triggered_at      str       "YYYY-MM-DD HH:MM:SS"
            completed_at      str|null  null while still running
            status            str       running | completed | partial_failure | failed
            triggered_by      str       scheduler | manual
            today_is_trading_day bool
            portfolios_ok     int
            portfolios_failed int
            duration_ms       float|null
            results           list      per-portfolio outcome objects
    """
    return get_scheduler_status()


# ── POST /scheduler/run-snapshots ─────────────────────────────────────────────

@router.post("/run-snapshots", status_code=202)
async def run_snapshots_now() -> dict:
    """Manually trigger the daily snapshot job in the background.

    The holiday / weekend check is bypassed so this works on any day of the
    week and is safe to call during development and testing.

    The asyncio.Lock IS respected: if a job is already running this endpoint
    returns 409 Conflict rather than queuing a second run.

    The task fires asynchronously — this endpoint returns 202 Accepted
    immediately.  Poll GET /scheduler/status to track progress via last_run.
    """
    if _job_lock.locked():
        raise HTTPException(
            status_code=409,
            detail="A snapshot job is already running. Poll GET /scheduler/status for progress.",
        )

    log.info("scheduler router: manual run-snapshots requested — launching background task")
    asyncio.create_task(trigger_snapshots_now())

    return {
        "accepted": True,
        "message": "Snapshot job started in the background. Poll GET /scheduler/status for progress.",
    }
