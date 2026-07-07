"""APScheduler-based daily portfolio snapshot scheduler.

Schedule:  Monday–Friday at 17:45 Asia/Bangkok (after Thai market close + 15 min
           yfinance lag buffer — ensures ATC settlement prices are fully published).
           The job also checks is_thai_trading_day() at runtime and exits
           immediately on public holidays, so the cron day-of-week filter and
           the holiday guard work together as two independent safety layers.

Locking:   An asyncio.Lock prevents concurrent job executions within the same
           OS process.  generate_daily_snapshot() is itself idempotent (upsert
           on unique constraint), so a second call on the same day is harmless.

Public API (used by routers/scheduler.py and main.py):
    setup_scheduler()         → start the APScheduler background scheduler
    shutdown_scheduler()      → stop it gracefully
    trigger_snapshots_now()   → run job body immediately, bypassing holiday check
    get_scheduler_status()    → dict snapshot of scheduler state + last run log
    is_thai_trading_day(d)    → bool trading-day predicate
"""

import asyncio
import logging
import time
import traceback
from datetime import date, datetime
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from services.core.runtime_env import allow_market_fetching, is_vps_env

log = logging.getLogger(__name__)

_TIMEZONE = "Asia/Bangkok"

# asyncio.Lock() is safe to create at module scope in Python 3.10+.
_job_lock = asyncio.Lock()

# Scheduler singleton — kept so setup_scheduler() is idempotent.
_scheduler: AsyncIOScheduler | None = None

# Last-run state written by _run_snapshots_core(), read by get_scheduler_status().
_last_run: dict[str, Any] | None = None


# ── Timing helper ─────────────────────────────────────────────────────────────

def _elapsed_ms(t0: float) -> float:
    """Return milliseconds elapsed since perf_counter snapshot t0."""
    return round((time.perf_counter() - t0) * 1000, 1)


def _fmt_ms(ms: float) -> str:
    """Human-readable duration from milliseconds."""
    if ms < 1000:
        return f"{ms:.1f} ms"
    return f"{ms / 1000:.3f} s"


# ── Thai trading-day check ────────────────────────────────────────────────────

def _thai_holidays(year: int):
    """Return a holiday-set for Thailand using the `holidays` package.

    Covers: New Year, Makha Bucha, Chakri Day, Songkran (3 days), Labour Day,
    Coronation Day, Visakha Bucha, Asalha Puja, Queen/King birthdays,
    Chulalongkorn Day, Constitution Day, New Year's Eve, and substitution days.

    Falls back to an empty set if the package is unavailable — weekends are
    still caught by the weekday guard in is_thai_trading_day().
    """
    try:
        import holidays as hol_pkg
        return hol_pkg.Thailand(years=year)
    except Exception:
        log.warning(
            "snapshot_scheduler: 'holidays' package unavailable — "
            "public holidays will NOT be skipped (weekends still skipped)"
        )
        return set()


def is_thai_trading_day(d: date | None = None) -> bool:
    """Return True when *d* is a Thai Stock Exchange trading day.

    Skips Saturdays (weekday 5), Sundays (weekday 6), and any date that
    appears in the Thai public-holiday calendar for that year.
    """
    if d is None:
        d = date.today()
    if d.weekday() >= 5:
        return False
    return d not in _thai_holidays(d.year)


# ── Core execution (shared by scheduled job and manual trigger) ───────────────

async def _run_snapshots_core(triggered_by: str) -> None:
    """Generate daily snapshots for every portfolio across all workspaces.

    This is the shared body called by both the scheduled job (after the holiday
    guard) and the manual trigger endpoint (no holiday guard).

    Execution flow:
      1. Acquire asyncio.Lock — exit immediately if already held.
      2. Set _last_run to "running" and record start time.
      3. For each workspace → portfolio, call generate_daily_snapshot(),
         timing each call and logging start / success / failure with full traceback.
      4. Log per-workspace elapsed time.
      5. Update _last_run to final status and log a job-done summary.

    Args:
        triggered_by: "scheduler" or "manual" — recorded in _last_run.
    """
    global _last_run

    if _job_lock.locked():
        log.warning(
            "snapshot_scheduler: SKIP — lock already held (triggered_by=%s)",
            triggered_by,
        )
        return

    async with _job_lock:
        job_t0 = time.perf_counter()
        today = date.today()
        day_name = today.strftime("%A")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        log.info(
            "snapshot_scheduler: ── JOB START ──  date=%s (%s)  "
            "fired=%s  tz=%s  triggered_by=%s",
            today,
            day_name,
            now_str,
            _TIMEZONE,
            triggered_by,
        )

        # Record "running" state — visible to GET /scheduler/status immediately.
        _last_run = {
            "triggered_at": now_str,
            "completed_at": None,
            "status": "running",
            "triggered_by": triggered_by,
            "today_is_trading_day": is_thai_trading_day(today),
            "portfolios_ok": 0,
            "portfolios_failed": 0,
            "duration_ms": None,
            "results": [],
        }

        # Local imports prevent circular dependency at module load time.
        from models.database import SessionLocal, Workspace, Portfolio
        from services.portfolio_snapshots import generate_daily_snapshot

        db = SessionLocal()
        total_ok = 0
        total_fail = 0

        try:
            workspaces = db.query(Workspace).all()

            for ws in workspaces:
                ws_t0 = time.perf_counter()
                portfolios = (
                    db.query(Portfolio)
                    .filter(Portfolio.workspace_id == ws.id)
                    .all()
                )
                ws_ok = 0
                ws_fail = 0

                log.info(
                    "snapshot_scheduler:   workspace %d (%s) — %d portfolio(s)",
                    ws.id,
                    ws.name,
                    len(portfolios),
                )

                for portfolio in portfolios:
                    p_t0 = time.perf_counter()
                    log.info(
                        "snapshot_scheduler:     portfolio %d (%s) — start",
                        portfolio.id,
                        portfolio.name,
                    )
                    portfolio_result: dict[str, Any] = {
                        "portfolio_id": portfolio.id,
                        "portfolio_name": portfolio.name,
                        "workspace_id": ws.id,
                        "workspace_name": ws.name,
                        "status": "unknown",
                        "snapshot_date": None,
                        "total_value": None,
                        "elapsed_ms": None,
                        "error": None,
                    }
                    try:
                        snap = await generate_daily_snapshot(
                            db=db,
                            portfolio_id=portfolio.id,
                            workspace_id=ws.id,
                        )
                        p_ms = _elapsed_ms(p_t0)
                        ws_ok += 1
                        portfolio_result.update(
                            status="ok",
                            snapshot_date=snap["snapshot_date"],
                            total_value=snap["total_value"],
                            elapsed_ms=p_ms,
                        )
                        log.info(
                            "snapshot_scheduler:     portfolio %d (%s) — OK  "
                            "elapsed=%s  total_value=%.4f  holdings=%d  "
                            "unrealized_pnl=%.4f  daily_return=%s%%",
                            portfolio.id,
                            portfolio.name,
                            _fmt_ms(p_ms),
                            snap["total_value"],
                            snap["holdings_count"],
                            snap.get("unrealized_pnl") or 0.0,
                            f'{snap["daily_return_pct"]:+.4f}'
                            if snap.get("daily_return_pct") is not None
                            else "N/A",
                        )
                    except Exception:
                        p_ms = _elapsed_ms(p_t0)
                        ws_fail += 1
                        tb = traceback.format_exc().rstrip()
                        portfolio_result.update(
                            status="failed",
                            elapsed_ms=p_ms,
                            error=tb,
                        )
                        log.error(
                            "snapshot_scheduler:     portfolio %d (%s) — FAILED  "
                            "elapsed=%s\n%s",
                            portfolio.id,
                            portfolio.name,
                            _fmt_ms(p_ms),
                            tb,
                        )

                    _last_run["results"].append(portfolio_result)

                total_ok += ws_ok
                total_fail += ws_fail
                ws_ms = _elapsed_ms(ws_t0)
                log.info(
                    "snapshot_scheduler:   workspace %d (%s) — done  "
                    "ok=%d  failed=%d  elapsed=%s",
                    ws.id,
                    ws.name,
                    ws_ok,
                    ws_fail,
                    _fmt_ms(ws_ms),
                )

            # Value active shadow portfolios for all workspaces (Phase 3B.7A).
            shadow_t0 = time.perf_counter()
            try:
                from services.decision_memory.shadow_tracker import value_all_active_shadows
                for ws in workspaces:
                    shadow_results = value_all_active_shadows(db, ws.id)
                    if shadow_results:
                        log.info(
                            "snapshot_scheduler: shadow portfolios valued — count=%d  workspace=%d  elapsed=%s",
                            len(shadow_results),
                            ws.id,
                            _fmt_ms(_elapsed_ms(shadow_t0)),
                        )
            except Exception:
                log.error(
                    "snapshot_scheduler: shadow valuation failed\n%s",
                    traceback.format_exc().rstrip(),
                )

            # AI Evaluation M1 — EXPIRED decisions (P4), then horizon grading (P2/P3).
            # EXPIRED runs first so a snapshot that ages out or is superseded today
            # is gradable as such starting today rather than one scheduler cycle late.
            eval_t0 = time.perf_counter()
            try:
                from services.evaluation.expired_writer import write_expired_decisions
                from services.evaluation.horizon_grader import grade_due_recommendations
                expired_result = write_expired_decisions(db)
                grade_result = grade_due_recommendations(db)
                log.info(
                    "snapshot_scheduler: evaluation pass — expired=%d graded=%d skipped=%d deactivated=%d  elapsed=%s",
                    len(expired_result.get("written", [])),
                    len(grade_result.get("graded", [])),
                    len(grade_result.get("skipped", [])),
                    len(grade_result.get("deactivated", [])),
                    _fmt_ms(_elapsed_ms(eval_t0)),
                )
            except Exception:
                log.error(
                    "snapshot_scheduler: evaluation pass failed\n%s",
                    traceback.format_exc().rstrip(),
                )

            # Compute attribution metrics for portfolios with active shadows (Phase 3B.7C).
            # Runs after shadow valuation so snapshots are fresh.
            attr_t0 = time.perf_counter()
            try:
                from models.database import ShadowPortfolio
                from services.analytics.attribution_engine import compute_portfolio_attribution
                portfolio_ids_with_shadows: set[int] = set()
                for ws in workspaces:
                    rows = (
                        db.query(ShadowPortfolio.portfolio_id)
                        .filter_by(workspace_id=ws.id, is_active=True)
                        .distinct()
                        .all()
                    )
                    portfolio_ids_with_shadows.update(r.portfolio_id for r in rows if r.portfolio_id)
                for pid in portfolio_ids_with_shadows:
                    try:
                        compute_portfolio_attribution(db, pid)
                    except Exception:
                        pass
                if portfolio_ids_with_shadows:
                    log.info(
                        "snapshot_scheduler: attribution computed — portfolios=%d  elapsed=%s",
                        len(portfolio_ids_with_shadows),
                        _fmt_ms(_elapsed_ms(attr_t0)),
                    )
            except Exception:
                log.error(
                    "snapshot_scheduler: attribution computation failed\n%s",
                    traceback.format_exc().rstrip(),
                )

            # Fetch and store benchmark prices for today alongside portfolio snapshots.
            bench_t0 = time.perf_counter()
            try:
                from services.benchmark_service import fetch_and_store_benchmarks
                bench_results = await fetch_and_store_benchmarks(db, price_date=today.isoformat())
                log.info(
                    "snapshot_scheduler: benchmarks stored — elapsed=%s  results=%s",
                    _fmt_ms(_elapsed_ms(bench_t0)),
                    bench_results,
                )
            except Exception:
                log.error(
                    "snapshot_scheduler: benchmark fetch failed\n%s",
                    traceback.format_exc().rstrip(),
                )

        finally:
            db.close()

        job_ms = _elapsed_ms(job_t0)
        final_status = (
            "completed" if total_fail == 0
            else ("failed" if total_ok == 0 else "partial_failure")
        )
        completed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        _last_run.update(
            completed_at=completed_at,
            status=final_status,
            portfolios_ok=total_ok,
            portfolios_failed=total_fail,
            duration_ms=job_ms,
        )

        log.info(
            "snapshot_scheduler: ── JOB DONE ──  status=%s  ok=%d  failed=%d  "
            "total_elapsed=%s",
            final_status,
            total_ok,
            total_fail,
            _fmt_ms(job_ms),
        )

        if final_status == "completed":
            log.info(
                "Daily Snapshot successfully generated at 17:45 with stable EOD prices."
            )


# ── Public-facing entry points ────────────────────────────────────────────────

async def run_snapshot_job() -> None:
    """Entry point called by APScheduler (Mon–Fri 17:45 Asia/Bangkok).

    Fires at 17:45 ICT — 15 minutes after the official SET close — to allow
    Yahoo Finance ATC settlement prices to fully propagate before the snapshot
    is written to the database.

    Applies the trading-day guard before delegating to _run_snapshots_core().
    On VPS: exits immediately — snapshots are generated by the Local Research Node.
    """
    if is_vps_env():
        log.info("snapshot_scheduler: [VPS MODE] run_snapshot_job blocked — not a Research Node.")
        return

    today = date.today()
    day_name = today.strftime("%A")

    if not is_thai_trading_day(today):
        log.info(
            "snapshot_scheduler: SKIP — %s %s is not a trading day "
            "(weekend or Thai public holiday)",
            today,
            day_name,
        )
        return

    await _run_snapshots_core("scheduler")


async def trigger_snapshots_now() -> None:
    """Manually trigger the snapshot job, bypassing the holiday/weekend check.

    Intended for the POST /scheduler/run-snapshots admin endpoint.
    On VPS: blocked — manual snapshot generation requires Local Research Node.
    """
    if is_vps_env():
        log.warning("snapshot_scheduler: [VPS MODE] trigger_snapshots_now blocked — not a Research Node.")
        return

    await _run_snapshots_core("manual")


# ── Status introspection ──────────────────────────────────────────────────────

def get_scheduler_status() -> dict[str, Any]:
    """Return a complete snapshot of the scheduler's runtime state.

    Fields:
        scheduler_running   bool   — whether the APScheduler instance is active
        lock_held           bool   — whether a job is currently executing
        today_is_trading_day bool  — whether today passes the holiday check
        jobs                list   — one entry per registered APScheduler job:
                                     id, name, next_run_time (ISO str), trigger
        last_run            dict|None — last execution log (or None if never run):
                                     triggered_at, completed_at, status,
                                     triggered_by, today_is_trading_day,
                                     portfolios_ok, portfolios_failed,
                                     duration_ms, results[]
    """
    jobs: list[dict] = []
    if _scheduler is not None:
        for job in _scheduler.get_jobs():
            nrt = job.next_run_time
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": nrt.isoformat() if nrt else None,
                "trigger": str(job.trigger),
            })

    return {
        "scheduler_running": _scheduler is not None and _scheduler.running,
        "lock_held": _job_lock.locked(),
        "today_is_trading_day": is_thai_trading_day(),
        "jobs": jobs,
        "last_run": _last_run,
    }


# ── Scheduler lifecycle ───────────────────────────────────────────────────────

def setup_scheduler() -> AsyncIOScheduler | None:
    """Create, configure, and start the APScheduler background scheduler.

    Idempotent — returns the existing instance if already running.
    On VPS (APP_ENV=vps): logs a notice and returns None immediately.
    Schedulers require live market data access — they must only run locally.

    Trigger: CronTrigger  day_of_week=mon-fri  hour=17  minute=45
             timezone=Asia/Bangkok  (17:45 ICT — 15 min after SET close,
             allowing Yahoo Finance ATC prices to fully propagate)

    misfire_grace_time=3600 s: if the server restarts within 1 h of the
    scheduled fire time the job still executes once.
    """
    global _scheduler

    if is_vps_env():
        log.info(
            "snapshot_scheduler: [VPS MODE] Scheduler disabled on VPS. "
            "Snapshots are generated by the Local Research Node and synced via sync_to_vps.py."
        )
        return None

    if _scheduler is not None and _scheduler.running:
        return _scheduler

    _scheduler = AsyncIOScheduler(timezone=_TIMEZONE)
    _scheduler.add_job(
        run_snapshot_job,
        trigger=CronTrigger(
            day_of_week="mon-fri",
            hour=17,
            minute=45,
            timezone=_TIMEZONE,
        ),
        id="daily_portfolio_snapshot",
        name=f"Daily portfolio snapshot (17:45 {_TIMEZONE})",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    _scheduler.start()

    next_run = _scheduler.get_job("daily_portfolio_snapshot").next_run_time
    log.info(
        "snapshot_scheduler: started — cron Mon–Fri 17:45 %s  next_run=%s",
        _TIMEZONE,
        next_run.strftime("%Y-%m-%d %H:%M:%S %Z") if next_run else "unknown",
    )
    return _scheduler


def shutdown_scheduler() -> None:
    """Stop the scheduler gracefully. Safe to call even if never started."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        log.info("snapshot_scheduler: stopped")
