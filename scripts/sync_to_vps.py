#!/usr/bin/env python3
"""Local → VPS incremental database sync pipeline.

Hybrid Research Architecture: Local Research Node pushes computed data to
the VPS Dashboard Layer so the VPS never needs to call yfinance directly.

Usage
─────
    # Dry-run (show what would be synced, no writes):
    python scripts/sync_to_vps.py --dry-run

    # Full incremental sync using SSH tunnel / direct Postgres URL:
    python scripts/sync_to_vps.py --vps-url postgresql://user:pass@vps-host/dbname

    # SQLite → SQLite (for local testing):
    python scripts/sync_to_vps.py --vps-url sqlite:///./vps_replica.db

    # Sync only specific table groups:
    python scripts/sync_to_vps.py --tables market_data,snapshots,analytics

    # With explicit lookback window (default 48 h):
    python scripts/sync_to_vps.py --since-hours 72

Environment variables (alternative to CLI flags):
    VPS_DATABASE_URL   — VPS target DB URL
    LOCAL_DATABASE_URL — Local source DB URL (defaults to backend/.env DATABASE_URL)

Tables synced
─────────────
  market_data   : market_data_cache, agent_cache, analysis_cache
  snapshots     : portfolio_snapshots, benchmark_prices, regime_snapshots
  analytics     : optimizer_history, recommendation_snapshots,
                  attribution_metrics, signal_history, user_usage
  calibration   : confidence_calibration_records
  shadow         : shadow_portfolio_snapshots (daily valuations only)

Tables NEVER synced (VPS-private, user-specific):
    workspaces, users, portfolios, portfolio_items, watchlist,
    transactions, settings, user_execution_decisions

Sync strategy
─────────────
  1. Timestamp-based incremental: only rows with updated_at / created_at
     newer than the last successful sync watermark are transferred.
  2. UPSERT semantics: existing rows are updated; new rows are inserted.
  3. VPS auth/user tables are never touched.
  4. On conflict: LOCAL wins for all synced tables (local is authoritative
     for computed data).
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# ── Path setup ─────────────────────────────────────────────────────────────────
_REPO_ROOT  = Path(__file__).resolve().parent.parent
_BACKEND    = _REPO_ROOT / "backend"
sys.path.insert(0, str(_BACKEND))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("sync_to_vps")

# ── Table definitions ──────────────────────────────────────────────────────────

# (table_name, timestamp_column, pk_columns)
_SYNC_TABLES: dict[str, list[tuple[str, str, list[str]]]] = {
    "market_data": [
        ("market_data_cache",   "fetched_at",   ["symbol", "cache_type"]),
        ("agent_cache",         "updated_at",   ["symbol", "cache_type"]),
        ("analysis_cache",      "updated_at",   ["symbol"]),
    ],
    "snapshots": [
        ("portfolio_snapshots", "snapshot_date", ["portfolio_id", "snapshot_date"]),
        ("benchmark_prices",    "created_at",    ["symbol", "price_date"]),
        ("regime_snapshots",    "snapshot_date", ["snapshot_date"]),
    ],
    "analytics": [
        ("optimizer_history",           "created_at",  ["id"]),
        ("recommendation_snapshots",    "created_at",  ["id"]),
        ("attribution_metrics",         "created_at",  ["id"]),
        ("signal_history",              "recorded_at", ["id"]),
        ("user_usage",                  "created_at",  ["id"]),
        ("analysis_history",            "created_at",  ["id"]),
    ],
    "calibration": [
        ("confidence_calibration_records", "created_at", ["id"]),
    ],
    "shadow": [
        ("shadow_portfolio_snapshots", "snapshot_date", ["shadow_portfolio_id", "snapshot_date"]),
    ],
}

# Tables that must NEVER be synced (VPS-private user data).
_BLOCKED_TABLES = frozenset({
    "workspaces", "users",
    "portfolios", "portfolio_items", "watchlist",
    "transactions", "settings",
    "user_execution_decisions",
    "shadow_portfolios",  # metadata only — snapshots (valuations) are safe to sync
})


# ── SQLAlchemy helpers ─────────────────────────────────────────────────────────

def _make_engine(url: str):
    from sqlalchemy import create_engine
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True)


def _table_exists(conn, table_name: str) -> bool:
    from sqlalchemy import text, inspect
    insp = inspect(conn.engine)
    return table_name in insp.get_table_names()


def _get_columns(conn, table_name: str) -> list[str]:
    from sqlalchemy import inspect
    insp = inspect(conn.engine)
    return [c["name"] for c in insp.get_columns(table_name)]


def _fetch_rows(
    conn,
    table_name: str,
    ts_col: str,
    since: datetime,
    limit: int = 10_000,
) -> list[dict]:
    from sqlalchemy import text
    try:
        result = conn.execute(
            text(
                f"SELECT * FROM {table_name} "
                f"WHERE {ts_col} >= :since "
                f"ORDER BY {ts_col} ASC "
                f"LIMIT :limit"
            ),
            {"since": since, "limit": limit},
        )
        cols = list(result.keys())
        return [dict(zip(cols, row)) for row in result.fetchall()]
    except Exception as exc:
        log.warning("fetch_rows failed table=%s: %s", table_name, exc)
        return []


def _upsert_rows(
    conn,
    table_name: str,
    pk_cols: list[str],
    rows: list[dict],
    dry_run: bool = False,
) -> int:
    """Upsert rows into target table.  Returns number of rows written."""
    if not rows:
        return 0

    if dry_run:
        log.info("  [dry-run] would upsert %d rows into %s", len(rows), table_name)
        return len(rows)

    from sqlalchemy import text

    # Build column list from first row
    cols = list(rows[0].keys())
    col_list = ", ".join(cols)
    placeholder_list = ", ".join(f":{c}" for c in cols)

    # Build conflict update clause
    update_clause = ", ".join(
        f"{c} = EXCLUDED.{c}" for c in cols if c not in pk_cols
    ) or f"{pk_cols[0]} = EXCLUDED.{pk_cols[0]}"

    pk_list = ", ".join(pk_cols)

    # Detect dialect
    is_pg = "postgresql" in str(conn.engine.url)
    is_sq = "sqlite" in str(conn.engine.url)

    written = 0
    for row in rows:
        try:
            if is_pg:
                stmt = text(
                    f"INSERT INTO {table_name} ({col_list}) VALUES ({placeholder_list}) "
                    f"ON CONFLICT ({pk_list}) DO UPDATE SET {update_clause}"
                )
            elif is_sq:
                # SQLite: INSERT OR REPLACE (replaces full row on PK conflict)
                stmt = text(
                    f"INSERT OR REPLACE INTO {table_name} ({col_list}) VALUES ({placeholder_list})"
                )
            else:
                raise ValueError(f"Unsupported dialect: {conn.engine.url}")

            conn.execute(stmt, row)
            written += 1
        except Exception as exc:
            log.warning("upsert_row failed table=%s pk=%s: %s", table_name, pk_cols, exc)

    try:
        conn.commit()
    except Exception:
        pass  # auto-commit engines skip this

    return written


# ── Watermark helpers ──────────────────────────────────────────────────────────

_WATERMARK_FILE = _REPO_ROOT / ".sync_watermark"


def _load_watermark() -> datetime:
    try:
        ts = float(_WATERMARK_FILE.read_text().strip())
        return datetime.utcfromtimestamp(ts)
    except Exception:
        return datetime.utcnow() - timedelta(hours=48)


def _save_watermark(dt: datetime) -> None:
    try:
        _WATERMARK_FILE.write_text(str(dt.timestamp()))
    except Exception as exc:
        log.warning("watermark save failed: %s", exc)


# ── Core sync logic ────────────────────────────────────────────────────────────

def sync(
    local_url: str,
    vps_url: str,
    table_groups: list[str],
    since: datetime,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run incremental sync from local to VPS.

    Returns a summary dict: {tables_synced, rows_synced, errors, duration_s}.
    """
    t_start = time.monotonic()
    log.info(
        "[SYNC PIPELINE] Starting incremental sync"
        " | since=%s | groups=%s | dry_run=%s",
        since.strftime("%Y-%m-%d %H:%M:%S"),
        ",".join(table_groups),
        dry_run,
    )

    local_engine = _make_engine(local_url)
    vps_engine   = _make_engine(vps_url)

    tables_synced = 0
    rows_synced   = 0
    errors: list[str] = []

    with local_engine.connect() as local_conn, vps_engine.connect() as vps_conn:
        for group in table_groups:
            if group not in _SYNC_TABLES:
                log.warning("Unknown table group: %s — skipping", group)
                continue

            for table_name, ts_col, pk_cols in _SYNC_TABLES[group]:
                if table_name in _BLOCKED_TABLES:
                    log.warning("  BLOCKED — %s is a protected VPS-private table", table_name)
                    continue

                if not _table_exists(local_conn, table_name):
                    log.debug("  SKIP — %s not found in local DB", table_name)
                    continue

                if not _table_exists(vps_conn, table_name):
                    log.warning("  SKIP — %s not found in VPS DB (run migrations first)", table_name)
                    errors.append(f"missing_table:{table_name}")
                    continue

                rows = _fetch_rows(local_conn, table_name, ts_col, since)
                if not rows:
                    log.debug("  %s — 0 new rows", table_name)
                    continue

                # Filter to columns that exist in the VPS table (schema may differ)
                vps_cols = set(_get_columns(vps_conn, table_name))
                rows = [{k: v for k, v in r.items() if k in vps_cols} for r in rows]

                written = _upsert_rows(vps_conn, table_name, pk_cols, rows, dry_run=dry_run)
                rows_synced   += written
                tables_synced += 1
                log.info("  %-45s  %4d rows synced", table_name, written)

    duration = round(time.monotonic() - t_start, 2)
    summary = {
        "tables_synced": tables_synced,
        "rows_synced":   rows_synced,
        "errors":        errors,
        "duration_s":    duration,
        "since":         since.isoformat() + "Z",
        "dry_run":       dry_run,
    }

    if dry_run:
        log.info("[SYNC PIPELINE] Dry-run complete in %.1fs — no data written", duration)
    else:
        log.info(
            "[SYNC PIPELINE] Incremental sync completed: "
            "%d tables | %d rows | %.1fs | errors=%d",
            tables_synced, rows_synced, duration, len(errors),
        )
    return summary


# ── CLI ────────────────────────────────────────────────────────────────────────

def _resolve_local_url() -> str:
    """Load DATABASE_URL from backend/.env or environment."""
    env_url = os.environ.get("LOCAL_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if env_url:
        return env_url

    env_file = _BACKEND / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line.startswith("DATABASE_URL="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")

    # Default SQLite path
    return f"sqlite:///{_BACKEND / 'stocks.db'}"


def main():
    parser = argparse.ArgumentParser(
        description="Sync computed data from Local Research Node to VPS Dashboard."
    )
    parser.add_argument(
        "--vps-url",
        default=os.environ.get("VPS_DATABASE_URL", ""),
        help="VPS database URL (postgresql://... or sqlite:///...)",
    )
    parser.add_argument(
        "--local-url",
        default="",
        help="Local DB URL (defaults to backend/.env DATABASE_URL)",
    )
    parser.add_argument(
        "--tables",
        default="market_data,snapshots,analytics,calibration,shadow",
        help="Comma-separated table groups to sync (default: all)",
    )
    parser.add_argument(
        "--since-hours",
        type=float,
        default=None,
        help="Sync rows newer than N hours ago (default: use watermark file)",
    )
    parser.add_argument(
        "--since",
        default=None,
        help="Explicit ISO timestamp cutoff (overrides --since-hours and watermark)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be synced without writing to VPS",
    )
    parser.add_argument(
        "--reset-watermark",
        action="store_true",
        help="Clear the watermark file before running (forces full re-sync)",
    )
    args = parser.parse_args()

    # Resolve URLs
    local_url = args.local_url or _resolve_local_url()
    vps_url   = args.vps_url
    if not vps_url:
        log.error("--vps-url is required (or set VPS_DATABASE_URL env var)")
        sys.exit(1)

    log.info("local_url=%s", local_url)
    log.info("vps_url=%s",   vps_url.split("@")[0] + "@***")  # hide credentials

    # Resolve since
    if args.reset_watermark and _WATERMARK_FILE.exists():
        _WATERMARK_FILE.unlink()
        log.info("Watermark reset — full re-sync will run")

    if args.since:
        since = datetime.fromisoformat(args.since.rstrip("Z"))
    elif args.since_hours is not None:
        since = datetime.utcnow() - timedelta(hours=args.since_hours)
    else:
        since = _load_watermark()

    table_groups = [g.strip() for g in args.tables.split(",") if g.strip()]

    summary = sync(
        local_url=local_url,
        vps_url=vps_url,
        table_groups=table_groups,
        since=since,
        dry_run=args.dry_run,
    )

    # Save watermark on success
    if not args.dry_run and not summary["errors"]:
        _save_watermark(datetime.utcnow())

    # Exit non-zero if there were errors
    if summary["errors"]:
        log.warning("Sync completed with %d errors: %s", len(summary["errors"]), summary["errors"])
        sys.exit(1)


if __name__ == "__main__":
    main()
