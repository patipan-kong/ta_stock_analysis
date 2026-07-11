"""Management CLI for the Portfolio Intelligence Platform.

Usage examples
--------------
Rebuild a portfolio from scratch (transaction ledger is the source of truth):
    python manage.py rebuild_portfolio --portfolio 4
    python manage.py rebuild_portfolio --portfolio 4 --dry-run
    python manage.py rebuild_portfolio --portfolio 4 --from-date 2026-01-01
    python manage.py rebuild_portfolio --portfolio 4 --skip-snapshots
    python manage.py rebuild_portfolio --all
    python manage.py rebuild_portfolio --all --yes

Repair a specific date:
    python manage.py repair_snapshots --portfolio 2 --date 2026-06-24

Repair a date range:
    python manage.py repair_snapshots --portfolio 2 \\
        --from-date 2026-06-01 --to-date 2026-06-24

Dry-run (no database writes):
    python manage.py repair_snapshots --portfolio 2 --date 2026-06-24 --dry-run

Scan all portfolios for corruption and repair:
    python manage.py repair_snapshots --all --scan-corrupted

Scan only (print report without repairing):
    python manage.py repair_snapshots --all --scan-corrupted --dry-run

Audit snapshot integrity (read-only):
    python manage.py verify_snapshots --portfolio 2
    python manage.py verify_snapshots --all
    python manage.py verify_snapshots --all --nav-threshold 20

Audit the transaction ledger (read-only):
    python manage.py validate_ledger --portfolio 4
    python manage.py validate_ledger --all
    python manage.py validate_ledger --portfolio 4 --price-check
    python manage.py validate_ledger --portfolio 4 --price-check --price-threshold 50

Simulate an Asset Registry migration (read-only — never writes):
    python manage.py plan_migration --portfolio 4
    python manage.py plan_migration --all

Execute an approved Asset Registry migration plan (defaults to dry run):
    python manage.py execute_migration --portfolio 4
    python manage.py execute_migration --portfolio 4 --commit
    python manage.py execute_migration --portfolio 4 --commit --run-id <uuid>   # resume

Bootstrap the empty Asset Registry from UNKNOWN ledger claims (defaults to dry run):
    python manage.py bootstrap_registry --portfolio 4
    python manage.py bootstrap_registry --portfolio 4 --commit
    python manage.py bootstrap_registry --portfolio 4 --commit --run-id <uuid>   # resume

Generate a deterministic repair plan (read-only — writes a JSON file only):
    python manage.py generate_repair_plan --portfolio 4
    python manage.py generate_repair_plan --portfolio 4 --output repair_plan.json
    python manage.py generate_repair_plan --portfolio 4 --effective

Apply a repair plan, then re-validate and rebuild:
    python manage.py apply_repair --portfolio 4 --plan repair_plan_4.json
    python manage.py validate_ledger --portfolio 4 --effective
    python manage.py rebuild_portfolio --portfolio 4

Backfill recommendation-quality grades for existing snapshots (AI Evaluation M1):
    python manage.py backfill_recommendation_grades --all
    python manage.py backfill_recommendation_grades --portfolio 4

Seed Registry SECTOR classification from the static taxonomy (Classification
Consolidation; defaults to dry run, never overwrites an existing fact):
    python manage.py seed_registry_classification
    python manage.py seed_registry_classification --commit
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import os
import time
import textwrap
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

# Ensure the backend directory is on sys.path when run directly.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.database import (
    AttributionMetric,
    OptimizerHistory,
    Portfolio,
    PortfolioItem,
    PortfolioSnapshot,
    RecommendationSnapshot,
    SessionLocal,
    ShadowPortfolio,
    ShadowPortfolioSnapshot,
    Transaction,
    UserExecutionDecision,
    Workspace,
)
from services.snapshot_repair import (
    CorruptionConfidence,
    CorruptionReport,
    RepairResult,
    RepairStatus,
    detect_corrupted_snapshots,
    repair_snapshot,
    repair_snapshot_by_date,
    repair_snapshots,
)
from services.snapshot_return_recovery import (
    PortfolioReturnRecoveryResult,
    SnapshotReturnDiff,
    _compute_return_fields,
    _RETURN_FIELDS,
    recover_all_snapshot_returns,
    recover_portfolio_snapshot_returns,
)
from services.portfolio_rebuilder import (
    ConfidenceReport,
    PlanOperation,
    PlanSummary,
    RebuildResult,
    ReconstructionPlan,
    ReconciliationStatus,
    rebuild_all_portfolios,
    rebuild_portfolio,
)
from services.ledger_validator import (
    FindingSeverity,
    LedgerFinding,
    LedgerValidationComparison,
    LedgerValidationReport,
    compare_ledger_validation,
    validate_all_ledgers,
    validate_portfolio_ledger,
    _ledger_confidence,
)
from services.ledger_repair import load_active_repairs
from services.repair_plan_executor import (
    RepairApplyResult,
    RepairPlan,
    RepairPlanError,
    apply_repair_plan,
    load_repair_plan,
)
from services.ledger_repair_plan import (
    GenerationSummary,
    generate_repair_plan,
    write_repair_plan,
)
from services.migration_planner import plan_migration
from services.migration_report import MigrationSummary, build_migration_report
from services.migration_executor import ExecutionOutcome, ExecutionReport, execute_migration
from services.bootstrap_planner import BootstrapPlan, build_bootstrap_plan
from services.registry_bootstrap import BootstrapOutcome, BootstrapReport, bootstrap_registry
from services.registry_classification_seed import SeedReport, seed_sector_classification
from services.registry_replay_parity import (
    GoldenBaseline,
    ParityReport,
    RegressionReport,
    capture_golden_baseline,
    compare_against_baseline,
    generate_regression_report,
    load_baseline,
    save_baseline,
)
from services.ledger_asset_backfill import (
    BackfillOutcome,
    BackfillReport,
    RollbackReport,
    backfill_ledger_asset_ids,
    rollback_backfill,
    unresolved_steps,
)


# ── Output helpers ────────────────────────────────────────────────────────────

_W = 60  # ruler width


def _hr() -> str:
    return "─" * _W


def _confirm() -> bool:
    """Prompt for confirmation. Returns True only for 'y'/'Y'."""
    try:
        return input("Proceed? [y/N] ").strip().lower() == "y"
    except (EOFError, KeyboardInterrupt):
        return False


_STATUS_ICON: dict[RepairStatus, str] = {
    RepairStatus.REPAIRED:    "✓",
    RepairStatus.SKIPPED:     "⚠",
    RepairStatus.DRY_RUN:     "~",
    RepairStatus.FAILED:      "✗",
    RepairStatus.NOT_CORRUPT: "○",
}


def _result_suffix(r: RepairResult) -> str:
    """One-line annotation appended after the status label."""
    if r.status == RepairStatus.REPAIRED and r.old_total_value and r.new_total_value:
        delta = r.new_total_value - r.old_total_value
        pct   = delta / r.old_total_value * 100
        return f"  (Δ {delta:+,.2f} / {pct:+.1f}%)"
    if r.status in (RepairStatus.SKIPPED, RepairStatus.DRY_RUN) and r.coverage:
        c = r.coverage
        miss = c.get("missing", [])
        tail = f" — missing: {miss}" if miss else ""
        return f"  (coverage {c['successful']}/{c['total']}{tail})"
    if r.status == RepairStatus.FAILED:
        msg = r.reason or r.error or ""
        return f"  {msg}" if msg else ""
    return ""


def _print_progress(index: int, total: int, r: RepairResult) -> None:
    icon   = _STATUS_ICON.get(r.status, "?")
    suffix = _result_suffix(r)
    print(f"    {icon} {r.status.value}{suffix}")


def _print_corruption_report(cr: CorruptionReport) -> None:
    reasons_str = ", ".join(r.value for r in cr.reasons)
    print(
        f"\n  Snapshot ID:  {cr.snapshot_id}\n"
        f"  Portfolio:    {cr.portfolio_id}\n"
        f"  Date:         {cr.snapshot_date}\n"
        f"  Confidence:   {cr.confidence.value}\n"
        f"  Reasons:      {reasons_str}"
    )
    for key, val in cr.details.items():
        print(f"  {key}: {val}")


def _print_confirmation_block(
    n: int,
    reports: list[CorruptionReport] | None = None,
    portfolio_id: int | None = None,
    date_range: tuple[str, str] | None = None,
    n_portfolios: int | None = None,
) -> None:
    """Print the pre-repair summary and ask for confirmation (prints only; caller reads answer)."""
    print(f"\n{_hr()}")
    if reports is not None:
        high   = sum(1 for r in reports if r.confidence == CorruptionConfidence.HIGH)
        medium = sum(1 for r in reports if r.confidence == CorruptionConfidence.MEDIUM)
        low    = sum(1 for r in reports if r.confidence == CorruptionConfidence.LOW)
        print(f"Found {n} corrupted snapshot(s)")
        if high:
            print(f"  HIGH confidence   : {high}")
        if medium:
            print(f"  MEDIUM confidence : {medium}")
        if low:
            print(f"  LOW confidence    : {low}")
    elif date_range:
        lo, hi = date_range
        label = f"portfolio {portfolio_id}" if portfolio_id else f"{n_portfolios} portfolio(s)"
        print(f"Found {n} snapshot(s)  [{lo} → {hi}]  ({label})")
    else:
        label = f"portfolio {portfolio_id}" if portfolio_id else f"{n_portfolios or '?'} portfolio(s)"
        print(f"Found {n} snapshot(s)  ({label})")
    print("\nThe following operation will modify historical snapshot data.")


def _print_summary(results: list[RepairResult], elapsed: float, dry_run: bool) -> None:
    repaired = sum(1 for r in results if r.status == RepairStatus.REPAIRED)
    skipped  = sum(1 for r in results if r.status == RepairStatus.SKIPPED)
    failed   = sum(1 for r in results if r.status == RepairStatus.FAILED)
    dry      = sum(1 for r in results if r.status == RepairStatus.DRY_RUN)
    total    = len(results)

    print(f"\n{_hr()}")
    if dry_run:
        print("Dry Run Summary")
        print(_hr())
        print(f"  Snapshots Found   : {total}")
        print(f"  Repairable        : {dry}")
        print(f"  Would Skip        : {skipped}")
        print(f"  Would Fail        : {failed}")
        print(f"\n  No database changes were made.")
    else:
        repair_errors = sum(1 for r in results if r.status == RepairStatus.FAILED and r.error)
        print("Repair Summary")
        print(_hr())
        print(f"  Snapshots Found   : {total}")
        print(f"  Repaired          : {repaired}")
        print(f"  Skipped           : {skipped}")
        print(f"  Failed            : {failed}")
        print(f"  Coverage Abort    : {skipped}")
        print(f"  Repair Errors     : {repair_errors}")

    print(_hr())
    print(f"\nCompleted in {elapsed:.2f} seconds.")

    # Failure details
    failures = [r for r in results if r.status == RepairStatus.FAILED]
    if failures and not dry_run:
        print(f"\nFailures")
        print(_hr())
        for r in failures:
            print(f"  Snapshot {r.snapshot_id}")
            msg = r.reason or r.error or "Unknown error"
            print(f"    {msg}")

    print()


# ── Repair loop helper ────────────────────────────────────────────────────────

async def _repair_list(
    db,
    snap_list: list[PortfolioSnapshot],
    ws_id: int,
    dry_run: bool,
) -> list[RepairResult]:
    """Repair each snapshot in snap_list, printing per-item progress."""
    total   = len(snap_list)
    results = []
    for i, snap in enumerate(snap_list, 1):
        print(f"\n[{i}/{total}] Portfolio {snap.portfolio_id}  {snap.snapshot_date}")
        print("    Repairing...")
        r = await repair_snapshot(db=db, snapshot_id=snap.id, workspace_id=ws_id, dry_run=dry_run)
        results.append(r)
        _print_progress(i, total, r)
    return results


# ── Debug: return-recovery inspection ────────────────────────────────────────

def _debug_print_return_recovery(
    db,
    portfolio_id: int,
    ws_id: int,
    snapshot_date: str,
) -> None:
    """Temporary debug helper — prints detailed _compute_return_fields() trace.

    Reads snapshot, previous snapshot, and all transactions in the attribution
    window.  Calls _compute_return_fields() directly and shows the computation
    alongside a stored-vs-recalculated comparison.  Never writes to the DB.
    """
    from datetime import datetime, timedelta

    hr = "-" * _W

    # ── Fetch snapshots ───────────────────────────────────────────────────────
    curr_snap = (
        db.query(PortfolioSnapshot)
        .filter_by(portfolio_id=portfolio_id, workspace_id=ws_id,
                   snapshot_date=snapshot_date)
        .first()
    )
    if curr_snap is None:
        print(f"\n  [DEBUG] Snapshot not found: portfolio={portfolio_id} date={snapshot_date}")
        return

    prev_snap = (
        db.query(PortfolioSnapshot)
        .filter(
            PortfolioSnapshot.portfolio_id == portfolio_id,
            PortfolioSnapshot.workspace_id == ws_id,
            PortfolioSnapshot.snapshot_date < snapshot_date,
        )
        .order_by(PortfolioSnapshot.snapshot_date.desc())
        .first()
    )

    # ── Section: Snapshot ─────────────────────────────────────────────────────
    print(f"\n{hr}")
    print("Snapshot")
    print(hr)
    if prev_snap:
        print(f"  Previous Snapshot ID  : {prev_snap.id}")
        print(f"  Previous Date         : {prev_snap.snapshot_date}")
        print(f"  Previous NAV          : {(prev_snap.total_value or 0):,.2f}")
        print(f"  Previous cash         : {(prev_snap.cash_balance or 0):,.2f}")
    else:
        print("  Previous Snapshot ID  : None  (this is the baseline)")
    print(f"  Current Snapshot ID   : {curr_snap.id}")
    print(f"  Current Date          : {curr_snap.snapshot_date}")
    print(f"  Current NAV           : {(curr_snap.total_value or 0):,.2f}")
    print(f"  Current cash          : {(curr_snap.cash_balance or 0):,.2f}")

    if prev_snap is None:
        print(f"\n  [BASELINE] No previous snapshot — all return fields will be None.")
        return

    # ── Attribution window ────────────────────────────────────────────────────
    today_end    = datetime.strptime(snapshot_date, "%Y-%m-%d") + timedelta(days=1)
    prev_day_end = datetime.strptime(prev_snap.snapshot_date, "%Y-%m-%d") + timedelta(days=1)

    # ── Fetch all transactions in window ──────────────────────────────────────
    all_txs = (
        db.query(Transaction)
        .filter(
            Transaction.portfolio_id == portfolio_id,
            Transaction.created_at >= prev_day_end,
            Transaction.created_at <  today_end,
        )
        .order_by(Transaction.created_at)
        .all()
    )

    # Parse prev_snap holdings to classify INITIAL_POSITION retroactive entries.
    prev_holdings: dict[str, float] = {}
    if prev_snap.holdings_json:
        try:
            for h in json.loads(prev_snap.holdings_json):
                sym = h.get("symbol")
                if sym:
                    prev_holdings[sym] = float(h.get("shares") or 0.0)
        except (ValueError, TypeError):
            pass

    curr_cash  = float(curr_snap.cash_balance or 0.0)
    prev_cash  = float(prev_snap.cash_balance or 0.0)
    cash_delta = curr_cash - prev_cash

    # ── Section: Return Recovery ──────────────────────────────────────────────
    print(f"\n{hr}")
    print("Return Recovery")
    print(hr)
    print(f"  Attribution window  : [{prev_snap.snapshot_date} end-of-day -> {snapshot_date} end-of-day)")
    print(f"    created_at in [ {prev_day_end} , {today_end} )")
    print(f"  Transactions found  : {len(all_txs)}")

    buy_cash_out = 0.0
    sell_cash_in = 0.0

    if all_txs:
        col_w = {"id": 6, "type": 22, "sym": 12, "created": 22, "txdate": 12,
                 "shares": 10, "amount": 14, "inc": 8}
        hdr = (
            f"\n  {'ID':>{col_w['id']}}  {'Type':<{col_w['type']}}  "
            f"{'Symbol':<{col_w['sym']}}  {'created_at':<{col_w['created']}}  "
            f"{'tx_date':<{col_w['txdate']}}  {'Shares':>{col_w['shares']}}  "
            f"{'Amount':>{col_w['amount']}}  {'Included':<{col_w['inc']}}  Reason"
        )
        sep = (
            f"  {'-'*col_w['id']}  {'-'*col_w['type']}  {'-'*col_w['sym']}  "
            f"{'-'*col_w['created']}  {'-'*col_w['txdate']}  {'-'*col_w['shares']}  "
            f"{'-'*col_w['amount']}  {'-'*col_w['inc']}  {'-'*38}"
        )
        print(hdr)
        print(sep)

        for tx in all_txs:
            tx_type  = tx.transaction_type or ""
            symbol   = tx.symbol or ""
            shares   = float(tx.shares or 0.0)
            amount   = float(tx.total_amount or 0.0)
            created  = str(tx.created_at)[:19] if tx.created_at else "?"
            tx_date  = str(tx.transaction_date)[:10] if tx.transaction_date else "?"

            if tx_type == "BUY":
                included = "YES"
                reason   = "buy_cash_out component of net_ecf; fees counted"
                buy_cash_out += amount
            elif tx_type == "SELL":
                included = "YES"
                reason   = "sell_cash_in component of net_ecf; realized P/L + fees counted"
                sell_cash_in += amount
            elif tx_type in ("DEPOSIT", "INITIAL_CASH", "WITHDRAW"):
                included = "INDIRECT"
                reason   = "captured by cash-delta formula -- NOT summed directly"
            elif tx_type == "INITIAL_POSITION":
                prev_sh = prev_holdings.get(symbol, 0.0)
                if shares <= prev_sh:
                    included = "NO"
                    reason   = (
                        f"retroactive: {symbol} already in prev_snap "
                        f"({prev_sh:.0f} sh >= this tx {shares:.0f} sh)"
                    )
                else:
                    included = "YES"
                    reason   = (
                        f"new import: {symbol} not in prev_snap "
                        f"(had {prev_sh:.0f} sh < this tx {shares:.0f} sh)"
                    )
            elif tx_type == "QUANTITY_CORRECTION":
                included = "YES"
                reason   = "manual_adjustment_value"
            elif tx_type == "DIVIDEND":
                included = "YES"
                reason   = "period_dividend_income"
            else:
                included = "YES"
                reason   = f"type {tx_type}"

            print(
                f"  {tx.id:>{col_w['id']}}  {tx_type:<{col_w['type']}}  "
                f"{symbol:<{col_w['sym']}}  {created:<{col_w['created']}}  "
                f"{tx_date:<{col_w['txdate']}}  {shares:>{col_w['shares']}.2f}  "
                f"{amount:>{col_w['amount']},.2f}  {included:<{col_w['inc']}}  {reason}"
            )

    # ── net_ecf breakdown ─────────────────────────────────────────────────────
    net_ecf_raw = cash_delta + buy_cash_out - sell_cash_in
    print(f"\n  net_ecf formula  =  (curr_cash - prev_cash) + buy_cash_out - sell_cash_in")
    print(f"    curr_cash            {curr_cash:>14,.2f}")
    print(f"    prev_cash            {prev_cash:>14,.2f}")
    print(f"    cash_delta           {cash_delta:>+14,.2f}")
    print(f"    buy_cash_out         {buy_cash_out:>+14,.2f}")
    print(f"    sell_cash_in (-)     {sell_cash_in:>+14,.2f}")
    print(f"    ---------------------------------")
    print(f"    net_ecf              {net_ecf_raw:>+14,.2f}")

    # ── Call _compute_return_fields() ─────────────────────────────────────────
    print(f"\n  Calling _compute_return_fields() ...")
    computed = _compute_return_fields(db, portfolio_id, prev_snap, curr_snap)

    prev_nav     = float(prev_snap.total_value or 0.0)
    curr_nav     = float(curr_snap.total_value or 0.0)
    net_ecf_v    = float(computed.get("net_external_cash_flow") or 0.0)
    imp_v        = float(computed.get("imported_asset_value") or 0.0)
    man_v        = float(computed.get("manual_adjustment_value") or 0.0)
    pure_gain    = float(computed.get("investment_return_amount") or 0.0)

    print(f"\n  Pure market gain  =  curr_nav - prev_nav - net_ecf - imported - manual_adj")
    print(f"    curr_nav             {curr_nav:>14,.2f}")
    print(f"    prev_nav (-)         {prev_nav:>+14,.2f}")
    print(f"    net_ecf (-)          {net_ecf_v:>+14,.2f}")
    print(f"    imported_asset (-)   {imp_v:>+14,.2f}")
    print(f"    manual_adj (-)       {man_v:>+14,.2f}")
    print(f"    ---------------------------------")
    print(f"    pure_market_gain     {pure_gain:>+14,.2f}")

    print(f"\n  Computed return fields:")
    for f in _RETURN_FIELDS:
        val = computed.get(f)
        val_str = f"{val:+.4f}" if isinstance(val, float) else ("None" if val is None else str(val))
        print(f"    {f:<32}  {val_str}")

    # ── Section: Comparison ───────────────────────────────────────────────────
    print(f"\n{hr}")
    print("Comparison  (Stored -> Recalculated)")
    print(hr)

    any_changed = False
    for f in _RETURN_FIELDS:
        stored = getattr(curr_snap, f, None)
        new    = computed.get(f)

        stored_str = f"{stored:+.4f}" if isinstance(stored, float) else ("None" if stored is None else str(stored))
        new_str    = f"{new:+.4f}"    if isinstance(new, float)    else ("None" if new    is None else str(new))

        if stored_str != new_str:
            print(f"\n  {f}")
            print(f"    {stored_str}")
            print(f"    v")
            print(f"    {new_str}")
            any_changed = True

    if not any_changed:
        print("\n  No changes — all return fields already match computed values.")

    print()


# ── Command: repair_snapshots ─────────────────────────────────────────────────

async def _cmd_repair_snapshots(args: argparse.Namespace) -> int:
    dry_run: bool = args.dry_run
    db       = SessionLocal()
    results: list[RepairResult] = []
    t_start  = time.monotonic()

    try:
        ws = db.query(Workspace).first()
        if ws is None:
            print("ERROR: No workspace found in database.", file=sys.stderr)
            return 1
        ws_id = ws.id

        # ── Scan-corrupted mode ───────────────────────────────────────────
        if args.scan_corrupted:
            portfolios = (
                db.query(Portfolio).filter_by(workspace_id=ws_id).all()
                if args.all
                else (
                    [db.query(Portfolio).filter_by(id=args.portfolio, workspace_id=ws_id).first()]
                    if args.portfolio
                    else []
                )
            )
            portfolios = [p for p in portfolios if p is not None]

            if not portfolios:
                print("ERROR: No portfolios found.", file=sys.stderr)
                return 1

            all_reports: list[CorruptionReport] = []
            for portfolio in portfolios:
                reports = detect_corrupted_snapshots(db, portfolio.id, ws_id)
                all_reports.extend(reports)

            if not all_reports:
                print("\nNo corrupted snapshots detected.")
                return 2

            # Print scan report
            print(f"\n{_hr()}")
            print(f"Corruption Scan  —  {len(all_reports)} snapshot(s) flagged")
            print(_hr())
            for cr in all_reports:
                _print_corruption_report(cr)

            if dry_run:
                print(f"\n{_hr()}")
                print("DRY RUN — no database changes will be made")
                print(_hr())
            else:
                _print_confirmation_block(len(all_reports), reports=all_reports)
                if not _confirm():
                    print("\nRepair cancelled.")
                    return 3

            total = len(all_reports)
            print(f"\n{_hr()}")
            print(f"Repairing {total} snapshot(s)...")
            print(_hr())
            for i, cr in enumerate(all_reports, 1):
                print(f"\n[{i}/{total}] Portfolio {cr.portfolio_id}  {cr.snapshot_date}")
                print("    Repairing...")
                r = await repair_snapshot_by_date(
                    db=db,
                    portfolio_id=cr.portfolio_id,
                    workspace_id=ws_id,
                    snapshot_date=cr.snapshot_date,
                    dry_run=dry_run,
                )
                results.append(r)
                _print_progress(i, total, r)

        # ── Single-date repair ────────────────────────────────────────────
        elif args.portfolio and args.date:
            if not dry_run:
                _print_confirmation_block(1, portfolio_id=args.portfolio)
                if not _confirm():
                    print("\nRepair cancelled.")
                    return 3

            print(f"\n[1/1] Portfolio {args.portfolio}  {args.date}")
            print("    Repairing...")
            r = await repair_snapshot_by_date(
                db=db,
                portfolio_id=args.portfolio,
                workspace_id=ws_id,
                snapshot_date=args.date,
                dry_run=dry_run,
            )
            results.append(r)
            _print_progress(1, 1, r)

            if getattr(args, "debug", False):
                _debug_print_return_recovery(db, args.portfolio, ws_id, args.date)

        # ── Date-range repair ─────────────────────────────────────────────
        elif args.portfolio and args.from_date and args.to_date:
            snaps = (
                db.query(PortfolioSnapshot)
                .filter(
                    PortfolioSnapshot.portfolio_id == args.portfolio,
                    PortfolioSnapshot.workspace_id == ws_id,
                    PortfolioSnapshot.snapshot_date >= args.from_date,
                    PortfolioSnapshot.snapshot_date <= args.to_date,
                )
                .order_by(PortfolioSnapshot.snapshot_date)
                .all()
            )
            if not snaps:
                print(
                    f"\nNo snapshots found for portfolio {args.portfolio} "
                    f"in [{args.from_date} → {args.to_date}]."
                )
                return 2

            if not dry_run:
                _print_confirmation_block(
                    len(snaps),
                    portfolio_id=args.portfolio,
                    date_range=(args.from_date, args.to_date),
                )
                if not _confirm():
                    print("\nRepair cancelled.")
                    return 3
            else:
                print(f"\n{_hr()}")
                print(
                    f"DRY RUN — {len(snaps)} snapshot(s)  "
                    f"[{args.from_date} → {args.to_date}]"
                )
                print(_hr())

            print(f"\n{_hr()}")
            print(f"Repairing {len(snaps)} snapshot(s)...")
            print(_hr())
            results = await _repair_list(db, snaps, ws_id, dry_run)

        # ── All portfolios, all dates ─────────────────────────────────────
        elif args.all and not args.scan_corrupted:
            portfolios = db.query(Portfolio).filter_by(workspace_id=ws_id).all()
            if not portfolios:
                print("ERROR: No portfolios found.", file=sys.stderr)
                return 1

            all_snaps: list[PortfolioSnapshot] = []
            for portfolio in portfolios:
                all_snaps.extend(
                    db.query(PortfolioSnapshot)
                    .filter_by(portfolio_id=portfolio.id, workspace_id=ws_id)
                    .order_by(PortfolioSnapshot.snapshot_date)
                    .all()
                )

            if not all_snaps:
                print("\nNo snapshots found.")
                return 2

            if not dry_run:
                _print_confirmation_block(
                    len(all_snaps),
                    n_portfolios=len(portfolios),
                )
                if not _confirm():
                    print("\nRepair cancelled.")
                    return 3
            else:
                print(f"\n{_hr()}")
                print(f"DRY RUN — {len(all_snaps)} snapshot(s) across {len(portfolios)} portfolio(s)")
                print(_hr())

            print(f"\n{_hr()}")
            print(f"Repairing {len(all_snaps)} snapshot(s) across {len(portfolios)} portfolio(s)...")
            print(_hr())
            results = await _repair_list(db, all_snaps, ws_id, dry_run)

        else:
            print(
                "ERROR: Specify one of:\n"
                "  --portfolio P --date D\n"
                "  --portfolio P --from-date D --to-date D\n"
                "  --all --scan-corrupted\n"
                "  --all",
                file=sys.stderr,
            )
            return 1

    except Exception as exc:
        print(f"\nERROR: Unexpected failure — {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    elapsed = time.monotonic() - t_start

    if results:
        _print_summary(results, elapsed, dry_run)
    else:
        print(f"\nCompleted in {elapsed:.2f} seconds.")

    if any(r.status == RepairStatus.FAILED for r in results):
        return 1
    return 0


# ══════════════════════════════════════════════════════════════════════════════
# Audit: verify_snapshots
# ══════════════════════════════════════════════════════════════════════════════

# ── Audit data structures ─────────────────────────────────────────────────────

class AuditSeverity(Enum):
    WARNING  = "WARNING"
    CRITICAL = "CRITICAL"


class AuditCheck(Enum):
    NAV_CONTINUITY     = "nav_continuity"
    PNL_CONTINUITY     = "pnl_continuity"
    HOLDINGS_INTEGRITY = "holdings_integrity"
    PRICE_INTEGRITY    = "price_integrity"
    RETURN_SANITY      = "return_sanity"


@dataclass
class AuditAnomaly:
    snapshot_id   : int
    snapshot_date : str
    check         : AuditCheck
    severity      : AuditSeverity
    description   : str
    details       : dict = field(default_factory=dict)


@dataclass
class PortfolioAuditResult:
    portfolio_id      : int
    portfolio_name    : str
    snapshots_checked : int
    anomalies         : list[AuditAnomaly] = field(default_factory=list)

    @property
    def warnings(self) -> list[AuditAnomaly]:
        return [a for a in self.anomalies if a.severity == AuditSeverity.WARNING]

    @property
    def criticals(self) -> list[AuditAnomaly]:
        return [a for a in self.anomalies if a.severity == AuditSeverity.CRITICAL]

    @property
    def status(self) -> str:
        if self.criticals:
            return "FAIL"
        if self.warnings:
            return "WARNING"
        return "PASS"


# ── Audit tolerance ───────────────────────────────────────────────────────────

_INTEGRITY_TOLERANCE = 1.0   # absolute THB tolerance for sum-vs-column checks
_PNL_JUMP_FACTOR     = 0.20  # flag unrealized P/L swing > 20% of NAV
_RETURN_HARD_LIMIT   = 50.0  # impossible daily return threshold (±%)


# ── Per-check audit functions ─────────────────────────────────────────────────

def _audit_nav_continuity(
    snap: PortfolioSnapshot,
    prev: PortfolioSnapshot | None,
    threshold_pct: float,
) -> list[AuditAnomaly]:
    if prev is None or prev.total_value is None or snap.total_value is None:
        return []
    if prev.total_value == 0:
        return []
    change_pct = (snap.total_value - prev.total_value) / abs(prev.total_value) * 100
    if abs(change_pct) <= threshold_pct:
        return []
    return [AuditAnomaly(
        snapshot_id   = snap.id,
        snapshot_date = snap.snapshot_date,
        check         = AuditCheck.NAV_CONTINUITY,
        severity      = AuditSeverity.WARNING,
        description   = f"Large NAV discontinuity ({change_pct:+.1f}%)",
        details       = {
            "previous_date" : prev.snapshot_date,
            "previous_nav"  : round(prev.total_value, 2),
            "current_nav"   : round(snap.total_value, 2),
            "change_pct"    : round(change_pct, 2),
        },
    )]


def _audit_pnl_continuity(
    snap: PortfolioSnapshot,
    prev: PortfolioSnapshot | None,
) -> list[AuditAnomaly]:
    if prev is None:
        return []
    if snap.unrealized_pnl is None or prev.unrealized_pnl is None:
        return []
    delta = snap.unrealized_pnl - prev.unrealized_pnl
    nav   = abs(snap.total_value or 1.0)
    if abs(delta) <= _PNL_JUMP_FACTOR * nav:
        return []
    return [AuditAnomaly(
        snapshot_id   = snap.id,
        snapshot_date = snap.snapshot_date,
        check         = AuditCheck.PNL_CONTINUITY,
        severity      = AuditSeverity.WARNING,
        description   = f"Large unrealized P/L discontinuity (Δ {delta:+,.2f})",
        details       = {
            "previous_date" : prev.snapshot_date,
            "previous_pnl"  : round(prev.unrealized_pnl, 2),
            "current_pnl"   : round(snap.unrealized_pnl, 2),
            "delta"         : round(delta, 2),
        },
    )]


def _audit_holdings_integrity(snap: PortfolioSnapshot) -> list[AuditAnomaly]:
    if not snap.holdings_json:
        return []

    try:
        holdings = json.loads(snap.holdings_json)
    except (ValueError, TypeError):
        return [AuditAnomaly(
            snapshot_id   = snap.id,
            snapshot_date = snap.snapshot_date,
            check         = AuditCheck.HOLDINGS_INTEGRITY,
            severity      = AuditSeverity.CRITICAL,
            description   = "holdings_json is not valid JSON",
            details       = {},
        )]

    if not isinstance(holdings, list):
        return []

    anomalies: list[AuditAnomaly] = []
    n = len(holdings)

    # holdings_count column vs actual array length
    if snap.holdings_count is not None and snap.holdings_count != n:
        anomalies.append(AuditAnomaly(
            snapshot_id   = snap.id,
            snapshot_date = snap.snapshot_date,
            check         = AuditCheck.HOLDINGS_INTEGRITY,
            severity      = AuditSeverity.WARNING,
            description   = (
                f"holdings_count column={snap.holdings_count} "
                f"but holdings_json has {n} entries"
            ),
            details       = {
                "holdings_count_col" : snap.holdings_count,
                "holdings_json_len"  : n,
            },
        ))

    # total_invested ≈ Σ(shares × avg_cost)
    computed_invested = sum(
        float(h.get("shares") or 0) * float(h.get("avg_cost") or 0)
        for h in holdings
    )
    if snap.total_invested is not None and abs(computed_invested - snap.total_invested) > _INTEGRITY_TOLERANCE:
        diff = snap.total_invested - computed_invested
        anomalies.append(AuditAnomaly(
            snapshot_id   = snap.id,
            snapshot_date = snap.snapshot_date,
            check         = AuditCheck.HOLDINGS_INTEGRITY,
            severity      = AuditSeverity.WARNING,
            description   = (
                f"total_invested mismatch: "
                f"stored={snap.total_invested:,.2f}  "
                f"computed={computed_invested:,.2f}  "
                f"diff={diff:+,.2f}"
            ),
            details       = {
                "stored_total_invested"   : round(snap.total_invested, 2),
                "computed_total_invested" : round(computed_invested, 2),
                "diff"                    : round(diff, 2),
            },
        ))

    # total_value ≈ cash_balance + Σ(market_value)
    computed_equity = sum(float(h.get("market_value") or 0) for h in holdings)
    cash            = float(snap.cash_balance or 0)
    computed_total  = cash + computed_equity
    stored_total    = float(snap.total_value or 0)
    if abs(computed_total - stored_total) > _INTEGRITY_TOLERANCE:
        diff = stored_total - computed_total
        anomalies.append(AuditAnomaly(
            snapshot_id   = snap.id,
            snapshot_date = snap.snapshot_date,
            check         = AuditCheck.HOLDINGS_INTEGRITY,
            severity      = AuditSeverity.WARNING,
            description   = (
                f"total_value mismatch: "
                f"stored={stored_total:,.2f}  "
                f"cash+equity={computed_total:,.2f}  "
                f"diff={diff:+,.2f}"
            ),
            details       = {
                "stored_total_value" : round(stored_total, 2),
                "cash_balance"       : round(cash, 2),
                "computed_equity"    : round(computed_equity, 2),
                "computed_total"     : round(computed_total, 2),
                "diff"               : round(diff, 2),
            },
        ))

    # unrealized_pnl ≈ Σ(holding unrealized_pnl)
    computed_upnl = sum(float(h.get("unrealized_pnl") or 0) for h in holdings)
    if snap.unrealized_pnl is not None and abs(computed_upnl - snap.unrealized_pnl) > _INTEGRITY_TOLERANCE:
        diff = snap.unrealized_pnl - computed_upnl
        anomalies.append(AuditAnomaly(
            snapshot_id   = snap.id,
            snapshot_date = snap.snapshot_date,
            check         = AuditCheck.HOLDINGS_INTEGRITY,
            severity      = AuditSeverity.WARNING,
            description   = (
                f"unrealized_pnl mismatch: "
                f"stored={snap.unrealized_pnl:,.2f}  "
                f"computed={computed_upnl:,.2f}  "
                f"diff={diff:+,.2f}"
            ),
            details       = {
                "stored_unrealized_pnl"   : round(snap.unrealized_pnl, 2),
                "computed_unrealized_pnl" : round(computed_upnl, 2),
                "diff"                    : round(diff, 2),
            },
        ))

    # Duplicate symbols
    seen: set[str] = set()
    dupes: list[str] = []
    for h in holdings:
        sym = h.get("symbol", "")
        if sym in seen:
            dupes.append(sym)
        seen.add(sym)
    if dupes:
        anomalies.append(AuditAnomaly(
            snapshot_id   = snap.id,
            snapshot_date = snap.snapshot_date,
            check         = AuditCheck.HOLDINGS_INTEGRITY,
            severity      = AuditSeverity.CRITICAL,
            description   = f"Duplicate symbols in holdings_json: {dupes}",
            details       = {"duplicates": dupes},
        ))

    return anomalies


def _audit_price_integrity(snap: PortfolioSnapshot) -> list[AuditAnomaly]:
    if not snap.holdings_json:
        return []

    try:
        holdings = json.loads(snap.holdings_json)
    except (ValueError, TypeError):
        return []

    if not isinstance(holdings, list):
        return []

    anomalies: list[AuditAnomaly] = []
    for h in holdings:
        symbol        = h.get("symbol", "?")
        shares        = float(h.get("shares") or 0)
        price         = h.get("current_price")
        mv            = h.get("market_value")
        price_missing = h.get("price_missing", False)

        if price_missing:
            anomalies.append(AuditAnomaly(
                snapshot_id   = snap.id,
                snapshot_date = snap.snapshot_date,
                check         = AuditCheck.PRICE_INTEGRITY,
                severity      = AuditSeverity.WARNING,
                description   = f"{symbol}: price_missing=True (avg_cost fallback used)",
                details       = {"symbol": symbol, "shares": shares},
            ))
            continue  # price value is known-invalid; skip further checks for this holding

        if price is None:
            anomalies.append(AuditAnomaly(
                snapshot_id   = snap.id,
                snapshot_date = snap.snapshot_date,
                check         = AuditCheck.PRICE_INTEGRITY,
                severity      = AuditSeverity.WARNING,
                description   = f"{symbol}: current_price is null",
                details       = {"symbol": symbol},
            ))
        elif float(price) <= 0:
            anomalies.append(AuditAnomaly(
                snapshot_id   = snap.id,
                snapshot_date = snap.snapshot_date,
                check         = AuditCheck.PRICE_INTEGRITY,
                severity      = AuditSeverity.WARNING,
                description   = f"{symbol}: current_price <= 0 ({price})",
                details       = {"symbol": symbol, "current_price": price},
            ))

        if mv is not None and float(mv) <= 0 and shares > 0:
            anomalies.append(AuditAnomaly(
                snapshot_id   = snap.id,
                snapshot_date = snap.snapshot_date,
                check         = AuditCheck.PRICE_INTEGRITY,
                severity      = AuditSeverity.WARNING,
                description   = f"{symbol}: market_value={mv} <= 0 while shares={shares}",
                details       = {"symbol": symbol, "market_value": mv, "shares": shares},
            ))

    return anomalies


def _audit_return_sanity(snap: PortfolioSnapshot) -> list[AuditAnomaly]:
    anomalies: list[AuditAnomaly] = []
    for col in ("daily_return_pct", "investment_return_pct"):
        val = getattr(snap, col, None)
        if val is not None and (val < -_RETURN_HARD_LIMIT or val > _RETURN_HARD_LIMIT):
            anomalies.append(AuditAnomaly(
                snapshot_id   = snap.id,
                snapshot_date = snap.snapshot_date,
                check         = AuditCheck.RETURN_SANITY,
                severity      = AuditSeverity.CRITICAL,
                description   = (
                    f"Impossible {col}={val:.2f}% "
                    f"(threshold ±{_RETURN_HARD_LIMIT:.0f}%)"
                ),
                details       = {"field": col, "value": round(val, 4)},
            ))
    return anomalies


# ── Portfolio-level audit ─────────────────────────────────────────────────────

def _audit_portfolio(
    db,
    portfolio: Portfolio,
    ws_id: int,
    nav_threshold_pct: float,
) -> PortfolioAuditResult:
    snaps: list[PortfolioSnapshot] = (
        db.query(PortfolioSnapshot)
        .filter_by(portfolio_id=portfolio.id, workspace_id=ws_id)
        .order_by(PortfolioSnapshot.snapshot_date)
        .all()
    )

    result = PortfolioAuditResult(
        portfolio_id      = portfolio.id,
        portfolio_name    = portfolio.name,
        snapshots_checked = len(snaps),
    )

    prev: PortfolioSnapshot | None = None
    for snap in snaps:
        result.anomalies.extend(_audit_nav_continuity(snap, prev, nav_threshold_pct))
        result.anomalies.extend(_audit_pnl_continuity(snap, prev))
        result.anomalies.extend(_audit_holdings_integrity(snap))
        result.anomalies.extend(_audit_price_integrity(snap))
        result.anomalies.extend(_audit_return_sanity(snap))
        prev = snap

    return result


# ── Audit output helpers ──────────────────────────────────────────────────────

_SEV_ICON = {
    AuditSeverity.WARNING  : "⚠",
    AuditSeverity.CRITICAL : "✗",
}

_NUMERIC_DETAIL_KEYS = {
    "previous_nav", "current_nav", "stored_total_invested",
    "computed_total_invested", "stored_total_value", "computed_equity",
    "computed_total", "stored_unrealized_pnl", "computed_unrealized_pnl",
    "cash_balance", "previous_pnl", "current_pnl",
}

_PCT_DETAIL_KEYS = {"change_pct"}
_SIGNED_DETAIL_KEYS = {"delta", "diff"}


def _print_audit_anomaly(a: AuditAnomaly) -> None:
    icon = _SEV_ICON.get(a.severity, "?")
    print(f"\n  {icon} {a.severity.value}  Snapshot {a.snapshot_id}  ({a.snapshot_date})")
    print(f"      [{a.check.value}] {a.description}")
    for k, v in a.details.items():
        if isinstance(v, (int, float)):
            if k in _PCT_DETAIL_KEYS:
                print(f"      {k:<28} {v:+.2f}%")
            elif k in _SIGNED_DETAIL_KEYS:
                print(f"      {k:<28} {v:+,.2f}")
            elif k in _NUMERIC_DETAIL_KEYS:
                print(f"      {k:<28} {v:,.2f}")
            else:
                print(f"      {k:<28} {v}")
        else:
            print(f"      {k:<28} {v}")


def _print_portfolio_audit_result(r: PortfolioAuditResult) -> None:
    print(f"\n{_hr()}")
    print(f"Portfolio {r.portfolio_id}  \"{r.portfolio_name}\"")
    print(_hr())
    print(f"Snapshots Checked: {r.snapshots_checked}")

    if not r.anomalies:
        print("\n  PASS — No anomalies detected")
        return

    for a in r.anomalies:
        _print_audit_anomaly(a)

    print()
    print(_hr())
    status_line = f"  {r.status}"
    print(status_line)
    if r.warnings:
        print(f"  Warnings  : {len(r.warnings)}")
    if r.criticals:
        print(f"  Criticals : {len(r.criticals)}")


def _print_overall_audit_summary(
    results: list[PortfolioAuditResult],
    elapsed: float,
) -> None:
    total_snaps = sum(r.snapshots_checked for r in results)
    total_warn  = sum(len(r.warnings)  for r in results)
    total_crit  = sum(len(r.criticals) for r in results)
    failing     = [r for r in results if r.status == "FAIL"]
    warning_only = [r for r in results if r.status == "WARNING"]

    print(f"\n{_hr()}")
    print("Overall")
    print(_hr())
    print(f"  Portfolios Checked : {len(results)}")
    print(f"  Snapshots Checked  : {total_snaps}")
    print(f"  Warnings           : {total_warn}")
    print(f"  Criticals          : {total_crit}")
    print()

    if not total_warn and not total_crit:
        print("  PASS — All snapshots pass integrity checks")
    else:
        for r in warning_only:
            w = len(r.warnings)
            print(
                f"  WARNING  Portfolio {r.portfolio_id}  {r.portfolio_name}"
                f"  ({w} warning{'s' if w != 1 else ''})"
            )
        for r in failing:
            c = len(r.criticals)
            print(
                f"  FAIL     Portfolio {r.portfolio_id}  {r.portfolio_name}"
                f"  ({c} critical{'s' if c != 1 else ''})"
            )

    print(_hr())
    print(f"\nCompleted in {elapsed:.2f} seconds.")
    print()


# ── Command: verify_snapshots ─────────────────────────────────────────────────

def _cmd_verify_snapshots(args: argparse.Namespace) -> int:
    """Read-only snapshot integrity audit. Never modifies the database."""
    db      = SessionLocal()
    t_start = time.monotonic()
    results: list[PortfolioAuditResult] = []

    try:
        ws = db.query(Workspace).first()
        if ws is None:
            print("ERROR: No workspace found in database.", file=sys.stderr)
            return 1
        ws_id = ws.id

        if args.all:
            portfolios = db.query(Portfolio).filter_by(workspace_id=ws_id).all()
        elif args.portfolio:
            p = db.query(Portfolio).filter_by(id=args.portfolio, workspace_id=ws_id).first()
            if p is None:
                print(f"ERROR: Portfolio {args.portfolio} not found.", file=sys.stderr)
                return 1
            portfolios = [p]
        else:
            print("ERROR: Specify --portfolio ID or --all", file=sys.stderr)
            return 1

        if not portfolios:
            print("ERROR: No portfolios found in workspace.", file=sys.stderr)
            return 1

        print(f"\n{_hr()}")
        print(f"Snapshot Integrity Audit")
        print(f"NAV continuity threshold : ±{args.nav_threshold:.1f}%")
        print(_hr())

        for portfolio in portfolios:
            r = _audit_portfolio(db, portfolio, ws_id, args.nav_threshold)
            results.append(r)
            _print_portfolio_audit_result(r)

    except Exception as exc:
        print(f"\nERROR: Unexpected failure — {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    elapsed = time.monotonic() - t_start
    _print_overall_audit_summary(results, elapsed)

    # Exit codes: 0 = clean, 1 = warnings, 2 = critical failures
    total_crit = sum(len(r.criticals) for r in results)
    total_warn = sum(len(r.warnings)  for r in results)
    if total_crit:
        return 2
    if total_warn:
        return 1
    return 0


# ══════════════════════════════════════════════════════════════════════════════
# AI Evaluation M1: backfill_recommendation_grades
# ══════════════════════════════════════════════════════════════════════════════

def _cmd_backfill_recommendation_grades(args: argparse.Namespace) -> int:
    """One-shot backfill: recommendation shadows (P2) + mature horizon grades
    (P3, M1) + day-0 PLAN grades (M2).

    For every existing RecommendationSnapshot lacking a recommendation-keyed
    shadow, creates one (create_recommendation_shadow() replays the shadow's
    full historical daily valuation from PortfolioSnapshot prices when the
    snapshot predates today — same routine repair_shadow_portfolios() already
    uses). Then runs the EXPIRED writer, the horizon grader (mature H7-H180
    grades), and the plan grader (PLAN grade — no maturity wait, needs only
    the snapshot itself) so every existing snapshot is gradable immediately.

    Idempotent: shadows and grades are both create-if-missing, so re-running
    this command is always safe and a no-op for anything already backfilled.
    """
    from models.database import RecommendationSnapshot, Workspace
    from services.decision_memory.shadow_tracker import create_recommendation_shadow
    from services.evaluation.expired_writer import write_expired_decisions
    from services.evaluation.horizon_grader import grade_due_recommendations
    from services.evaluation.plan_grader import grade_pending_plans

    db = SessionLocal()
    t_start = time.monotonic()
    errors = 0
    try:
        ws = db.query(Workspace).first()
        if ws is None:
            print("ERROR: No workspace found in database.", file=sys.stderr)
            return 1
        ws_id = ws.id

        if not args.portfolio and not args.all:
            print("ERROR: Specify --portfolio ID or --all", file=sys.stderr)
            return 1

        q = db.query(RecommendationSnapshot).filter(RecommendationSnapshot.workspace_id == ws_id)
        if args.portfolio:
            q = q.filter(RecommendationSnapshot.portfolio_id == args.portfolio)
        snapshots = q.order_by(RecommendationSnapshot.id).all()

        print(f"\n{_hr()}")
        print("Recommendation Grade Backfill")
        print(f"Snapshots in scope : {len(snapshots)}")
        print(_hr())

        created = 0
        existing = 0
        for snap in snapshots:
            try:
                r = create_recommendation_shadow(db, snap.id, ws_id)
            except Exception as exc:
                print(f"  ERROR snapshot {snap.id}: {exc}", file=sys.stderr)
                errors += 1
                continue
            if r.get("action") == "created":
                created += 1
                print(
                    f"  snapshot {snap.id}: shadow created "
                    f"({r.get('holdings_count')} holdings, "
                    f"{r.get('backfilled_snapshots')} SPS backfilled)"
                )
            elif r.get("action") == "exists":
                existing += 1
            else:
                errors += 1
                print(f"  snapshot {snap.id}: {r.get('error')}", file=sys.stderr)

        print(f"\nShadows created  : {created}")
        print(f"Shadows existing : {existing}")

        print(f"\n{_hr()}")
        print("Grading mature horizons...")
        expired_result = write_expired_decisions(db)
        grade_result = grade_due_recommendations(db, portfolio_id=args.portfolio)

        print(f"EXPIRED decisions written : {len(expired_result['written'])}")
        print(f"Grades written            : {len(grade_result['graded'])}")
        for g in grade_result["graded"]:
            print(f"  snapshot {g['snapshot_id']}: {g['grade_kind']}  score={g['score']}")

        skip_reasons: dict[str, int] = {}
        for s in grade_result["skipped"]:
            skip_reasons[s["reason"]] = skip_reasons.get(s["reason"], 0) + 1
        print(f"Grades skipped            : {len(grade_result['skipped'])}")
        for reason, count in skip_reasons.items():
            print(f"  {reason}: {count}")
        print(f"Shadows deactivated (final horizon reached) : {len(grade_result['deactivated'])}")

        print(f"\n{_hr()}")
        print("Grading day-0 plans...")
        plan_result = grade_pending_plans(db, portfolio_id=args.portfolio)
        print(f"PLAN grades written : {len(plan_result['graded'])}")
        for g in plan_result["graded"]:
            print(f"  snapshot {g['snapshot_id']}: score={g['score']}")
        plan_skip_reasons: dict[str, int] = {}
        for s in plan_result["skipped"]:
            plan_skip_reasons[s["reason"]] = plan_skip_reasons.get(s["reason"], 0) + 1
        print(f"PLAN grades skipped : {len(plan_result['skipped'])}")
        for reason, count in plan_skip_reasons.items():
            print(f"  {reason}: {count}")

    except Exception as exc:
        print(f"\nERROR: Unexpected failure — {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    elapsed = time.monotonic() - t_start
    print(f"\n{_hr()}")
    print(f"Done in {elapsed:.2f}s")
    return 1 if errors else 0


# ══════════════════════════════════════════════════════════════════════════════
# Classification Consolidation: seed_registry_classification
# ══════════════════════════════════════════════════════════════════════════════

def _print_seed_report(report: SeedReport) -> None:
    print(f"\n{_hr()}")
    print(f"Registry SECTOR Classification Seed  —  {'DRY RUN' if report.dry_run else 'LIVE'}")
    print(_hr())
    print(f"  Symbols considered    : {len(report.outcomes)}")
    print(f"  Seeded                : {report.seeded}")
    print(f"  Already classified    : {report.already_classified}")
    print(f"  Unresolved (Registry) : {report.unresolved}")
    print(f"  No seed data          : {report.no_seed_data}")

    seeded = [o for o in report.outcomes if o.outcome == "seeded"]
    if seeded:
        print(f"\n{_hr()}")
        print(f"Seeded  ({len(seeded)})")
        print(_hr())
        for o in seeded:
            print(f"  {o.symbol:<16} -> {o.sector}")

    print(_hr())


def _cmd_seed_registry_classification(args: argparse.Namespace) -> int:
    """One-time (re-runnable) seed: copies services/sector_taxonomy.py's
    static sector maps into the Registry as SECTOR AssetClassification
    facts, for every Watchlist/PortfolioItem symbol the Registry can
    already resolve to a minted Asset (docs/implementation/
    CLASSIFICATION_CONSOLIDATION.md).

    Never overwrites an existing classification fact — only fills gaps.
    Safe to re-run after new assets are minted (e.g. by a future M5 Track B
    backfill); already-seeded and already-classified symbols are no-ops.

    Defaults to a dry run (--commit is required to persist changes).
    """
    from models.database import Watchlist

    db = SessionLocal()
    t_start = time.monotonic()
    try:
        ws = db.query(Workspace).first()
        if ws is None:
            print("ERROR: No workspace found in database.", file=sys.stderr)
            return 1

        wl_symbols = {s for (s,) in db.query(Watchlist.symbol).filter(Watchlist.workspace_id == ws.id).all()}
        pi_symbols = {s for (s,) in db.query(PortfolioItem.symbol).filter(PortfolioItem.workspace_id == ws.id).all()}
        symbols = sorted(wl_symbols | pi_symbols)

        dry_run = not getattr(args, "commit", False)

        if not dry_run and not getattr(args, "yes", False):
            print(f"\nThis will write SECTOR classification facts to the Asset Registry for up to {len(symbols)} symbol(s).")
            confirm = input("Proceed? [y/N] ").strip().lower()
            if confirm != "y":
                print("Aborted.")
                return 1

        print(f"\n{_hr()}")
        print(f"Registry SECTOR Classification Seed  —  {len(symbols)} symbol(s) in scope  {'(DRY RUN)' if dry_run else '(LIVE)'}")
        print(_hr())

        report = seed_sector_classification(db, symbols, dry_run=dry_run)
        _print_seed_report(report)

        if not dry_run and report.seeded:
            db.commit()

    except Exception as exc:
        print(f"\nERROR: Unexpected failure — {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    elapsed = time.monotonic() - t_start
    print(f"\n  Completed in {elapsed:.2f}s.")
    return 0


# ══════════════════════════════════════════════════════════════════════════════
# Regenerate: regenerate_paper_portfolios (Accounting Correctness Milestone 2)
# ══════════════════════════════════════════════════════════════════════════════

def _shadow_state_counts(db, portfolio_ids: list[int]) -> dict[str, int]:
    """Identity/count snapshot used for before/after regeneration validation."""
    shadow_q = db.query(ShadowPortfolio).filter(ShadowPortfolio.portfolio_id.in_(portfolio_ids))
    static_shadows = shadow_q.filter(ShadowPortfolio.shadow_type == "STATIC_FROZEN").all()
    active_shadows = shadow_q.filter(ShadowPortfolio.shadow_type == "ACTIVE_MODEL").count()
    recommendation_shadows = len([s for s in static_shadows if s.execution_decision_id is None])
    decision_shadows = len(static_shadows) - recommendation_shadows
    shadow_ids = [s.id for s in shadow_q.all()]
    snapshot_count = (
        db.query(ShadowPortfolioSnapshot)
        .filter(ShadowPortfolioSnapshot.shadow_portfolio_id.in_(shadow_ids))
        .count()
        if shadow_ids else 0
    )
    attribution_count = (
        db.query(AttributionMetric)
        .filter(AttributionMetric.portfolio_id.in_(portfolio_ids))
        .count()
    )
    return {
        "shadows_total": len(static_shadows) + active_shadows,
        "shadows_static_decision": decision_shadows,
        "shadows_static_recommendation": recommendation_shadows,
        "shadows_active_model": active_shadows,
        "snapshots": snapshot_count,
        "attribution_rows": attribution_count,
    }


def _export_shadow_regeneration_backup(db, portfolio_ids: list[int], backup_dir: str = "backups") -> str:
    """Dump ShadowPortfolio + ShadowPortfolioSnapshot + AttributionMetric rows
    for *portfolio_ids* to JSON before regeneration mutates them — mirrors
    portfolio_rebuilder.py's _export_backup convention (pre-commit backup,
    backup failure aborts the commit).
    """
    os.makedirs(backup_dir, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    ids_label = "_".join(str(i) for i in portfolio_ids) if len(portfolio_ids) <= 5 else f"{len(portfolio_ids)}portfolios"
    path = os.path.join(backup_dir, f"regenerate_shadows_{ids_label}_{ts}.json")

    shadows = db.query(ShadowPortfolio).filter(ShadowPortfolio.portfolio_id.in_(portfolio_ids)).all()
    shadow_ids = [s.id for s in shadows]
    snaps = (
        db.query(ShadowPortfolioSnapshot)
        .filter(ShadowPortfolioSnapshot.shadow_portfolio_id.in_(shadow_ids))
        .all()
        if shadow_ids else []
    )
    attributions = (
        db.query(AttributionMetric)
        .filter(AttributionMetric.portfolio_id.in_(portfolio_ids))
        .all()
    )

    data = {
        "portfolio_ids": portfolio_ids,
        "backup_timestamp": datetime.utcnow().isoformat() + "Z",
        "shadow_portfolios": [
            {
                "id": s.id, "portfolio_id": s.portfolio_id, "shadow_type": s.shadow_type,
                "inception_date": s.inception_date, "inception_value": s.inception_value,
                "recommendation_snapshot_id": s.recommendation_snapshot_id,
                "execution_decision_id": s.execution_decision_id,
                "inception_holdings_json": s.inception_holdings_json,
                "paper_cash_balance": s.paper_cash_balance,
                "current_value": s.current_value,
                "inception_return_pct": s.inception_return_pct,
            }
            for s in shadows
        ],
        "shadow_portfolio_snapshots": [
            {
                "shadow_portfolio_id": sn.shadow_portfolio_id, "snapshot_date": sn.snapshot_date,
                "total_value": sn.total_value, "return_pct_since_inception": sn.return_pct_since_inception,
                "daily_return_pct": sn.daily_return_pct, "holdings_json": sn.holdings_json,
                "benchmark_return_pct": sn.benchmark_return_pct, "alpha": sn.alpha,
            }
            for sn in snaps
        ],
        "attribution_metrics": [
            {
                "id": a.id, "shadow_portfolio_id": a.shadow_portfolio_id, "portfolio_id": a.portfolio_id,
                "evaluation_period_start": a.evaluation_period_start, "evaluation_period_end": a.evaluation_period_end,
                "actual_return_pct": a.actual_return_pct, "static_shadow_return_pct": a.static_shadow_return_pct,
                "ai_model_return_pct": a.ai_model_return_pct, "regret_score": a.regret_score,
            }
            for a in attributions
        ],
    }

    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, default=str)
    return os.path.abspath(path)


def _print_shadow_state_counts(label: str, counts: dict[str, int]) -> None:
    print(f"{label}:")
    print(f"  ShadowPortfolio (ACTIVE_MODEL)          : {counts['shadows_active_model']}")
    print(f"  ShadowPortfolio (STATIC_FROZEN, decision): {counts['shadows_static_decision']}")
    print(f"  ShadowPortfolio (STATIC_FROZEN, recomm.) : {counts['shadows_static_recommendation']}")
    print(f"  ShadowPortfolio total                    : {counts['shadows_total']}")
    print(f"  ShadowPortfolioSnapshot rows              : {counts['snapshots']}")
    print(f"  AttributionMetric rows                    : {counts['attribution_rows']}")


async def _cmd_regenerate_paper_portfolios(args: argparse.Namespace) -> int:
    """Historical regeneration for Accounting Correctness Milestone 2.

    Re-derives ShadowPortfolio.paper_cash_balance/inception_holdings_json and
    ShadowPortfolioSnapshot rows for every existing shadow through the
    Milestone 1-corrected engine (services.decision_memory.shadow_tracker's
    regenerate_static_shadow / regenerate_active_model_shadow), then refreshes
    each portfolio's AttributionMetric row (compute_portfolio_attribution is
    an idempotent per-day upsert, so this never creates a duplicate).

    Defaults to a dry run (--commit is required to persist changes) and
    supports --backup to export affected rows to JSON first (mirrors
    portfolio_rebuilder.py's pre-commit backup convention; backup failure
    aborts the commit). Never touches RecommendationSnapshot, PortfolioSnapshot,
    PortfolioItem, Transaction, or UserExecutionDecision.
    """
    from services.decision_memory.shadow_tracker import regenerate_portfolio_paper_history
    from services.analytics.attribution_engine import compute_portfolio_attribution

    db = SessionLocal()
    t_start = time.monotonic()
    try:
        ws = db.query(Workspace).first()
        if ws is None:
            print("ERROR: No workspace found in database.", file=sys.stderr)
            return 1
        ws_id = ws.id

        if not args.portfolio and not args.all:
            print("ERROR: Specify --portfolio ID or --all", file=sys.stderr)
            return 1

        pq = db.query(Portfolio.id).filter(Portfolio.workspace_id == ws_id)
        if args.portfolio:
            pq = pq.filter(Portfolio.id == args.portfolio)
        portfolio_ids = [row[0] for row in pq.all()]
        if not portfolio_ids:
            print("ERROR: No matching portfolios found.", file=sys.stderr)
            return 1

        print(f"\n{_hr()}")
        print("Paper Portfolio Regeneration (Accounting Correctness Milestone 2)")
        print(f"Portfolios in scope : {len(portfolio_ids)} {portfolio_ids}")
        print(f"Mode                : {'COMMIT' if args.commit else 'DRY RUN (no changes will be persisted)'}")
        print(_hr())

        before = _shadow_state_counts(db, portfolio_ids)
        _print_shadow_state_counts("Before regeneration", before)

        if args.commit and args.backup:
            try:
                backup_path = _export_shadow_regeneration_backup(db, portfolio_ids)
                print(f"\nBackup written: {backup_path}")
            except Exception as exc:
                print(f"\nERROR: backup failed, aborting commit — {exc}", file=sys.stderr)
                return 1

        if args.commit and not args.yes:
            print(
                f"\nAbout to regenerate paper-portfolio history for {len(portfolio_ids)} "
                "portfolio(s) and persist the changes."
            )
            if not _confirm():
                print("Aborted.")
                return 1

        print(f"\n{_hr()}")
        print("Regenerating...")
        dry_run = not args.commit
        violations: list[str] = []
        errors: list[dict] = []
        skipped: list[dict] = []
        shadows_regenerated = 0
        snapshots_written = 0

        for pid in portfolio_ids:
            result = regenerate_portfolio_paper_history(db, pid, ws_id, dry_run=dry_run)
            for r in result["static_shadows"]:
                if r.get("status") == "regenerated":
                    shadows_regenerated += 1
                    snapshots_written += r.get("snapshots_rewritten", 0)
                    print(
                        f"  portfolio {pid}: static shadow {r['shadow_id']} regenerated "
                        f"(cash {r['prev_cash']:.2f} -> {r['new_cash']:.2f}, "
                        f"{r['snapshots_rewritten']} snapshots)"
                    )
                elif r.get("status") == "error":
                    errors.append(r)
                    violations.append(f"portfolio {pid} shadow {r['shadow_id']}: {r['error']}")
                    print(f"  portfolio {pid}: static shadow {r['shadow_id']} FAILED — {r['error']}", file=sys.stderr)
                else:
                    skipped.append({"portfolio_id": pid, **r})
                    print(f"  portfolio {pid}: static shadow {r.get('shadow_id')} skipped ({r.get('status')})")
            am = result["active_model"]
            if am and am.get("status") == "regenerated":
                shadows_regenerated += 1
                snapshots_written += am.get("snapshots_written", 0)
                print(
                    f"  portfolio {pid}: ACTIVE_MODEL shadow {am['shadow_id']} regenerated "
                    f"({am['rebalances_replayed']} rebalances replayed, "
                    f"{am['snapshots_written']} snapshots, final cash {am['final_cash']:.2f})"
                )
            elif am and am.get("status") == "error":
                errors.append(am)
                violations.append(f"portfolio {pid} active model: {am['error']}")
                print(f"  portfolio {pid}: ACTIVE_MODEL FAILED — {am['error']}", file=sys.stderr)
            elif am and am.get("status") != "no_active_model_shadow":
                print(f"  portfolio {pid}: ACTIVE_MODEL skipped ({am.get('status')})")

            if args.commit and result["errors"] == [] and (result["static_shadows"] or (am and am.get("status") == "regenerated")):
                try:
                    compute_portfolio_attribution(db, pid)
                except Exception as exc:
                    print(f"  portfolio {pid}: attribution refresh failed — {exc}", file=sys.stderr)
                    violations.append(f"portfolio {pid} attribution refresh: {exc}")

        print(f"\n{_hr()}")
        print("Regeneration validation")
        print(_hr())
        after = _shadow_state_counts(db, portfolio_ids)
        _print_shadow_state_counts("After regeneration" if args.commit else "After regeneration (dry run — DB unchanged)", after)

        identity_ok = (
            before["shadows_total"] == after["shadows_total"]
            and before["shadows_static_decision"] == after["shadows_static_decision"]
            and before["shadows_static_recommendation"] == after["shadows_static_recommendation"]
            and before["shadows_active_model"] == after["shadows_active_model"]
        )
        no_snapshot_loss = after["snapshots"] >= before["snapshots"]

        accounted_for = shadows_regenerated + len(errors) + len(skipped)
        fully_accounted = accounted_for == before["shadows_total"]

        print(f"\nIdentity preserved (no shadow rows created/deleted): {'PASS' if identity_ok else 'FAIL'}")
        print(f"No historical snapshot rows lost                    : {'PASS' if no_snapshot_loss else 'FAIL'}")
        print(f"Every shadow accounted for (regenerated+errors+skipped == before total): "
              f"{'PASS' if fully_accounted else 'FAIL'} ({accounted_for}/{before['shadows_total']})")
        print(f"NAV invariant violations                            : {len(violations)}")
        for v in violations[:20]:
            print(f"  - {v}")
        if skipped:
            print(f"\nSkipped (no stored holdings to regenerate — not a violation): {len(skipped)}")
            for s in skipped:
                print(f"  - portfolio {s['portfolio_id']} shadow {s.get('shadow_id')}: {s.get('status')}")

        print(f"\nShadows regenerated : {shadows_regenerated}")
        print(f"Snapshots written   : {snapshots_written}")
        print(f"Errors (NAV invariant, excluded)     : {len(errors)}")
        print(f"Skipped (no holdings, excluded)      : {len(skipped)}")

        ok = identity_ok and no_snapshot_loss and fully_accounted and not errors

    except Exception as exc:
        print(f"\nERROR: Unexpected failure — {exc}", file=sys.stderr)
        db.rollback()
        return 1
    finally:
        db.close()

    elapsed = time.monotonic() - t_start
    print(f"\n{_hr()}")
    print(f"Done in {elapsed:.2f}s")
    return 0 if ok else 1


# ══════════════════════════════════════════════════════════════════════════════
# Recalculate: recalculate_snapshot_returns
# ══════════════════════════════════════════════════════════════════════════════

def _format_field_value(v) -> str:
    """Human-readable representation of a return field value."""
    if v is None:
        return "None"
    return f"{v:+.4f}" if isinstance(v, float) else str(v)


def _print_recovery_diff(diff: SnapshotReturnDiff) -> None:
    """Print old → new values for a snapshot that would change."""
    print(f"\n  Snapshot {diff.snapshot_id}  ({diff.snapshot_date})")
    from services.snapshot_return_recovery import _RETURN_FIELDS
    for f in _RETURN_FIELDS:
        old = _format_field_value(diff.old_values.get(f))
        new = _format_field_value(diff.new_values.get(f))
        if old != new:
            print(f"    {f:<30}  {old}  →  {new}")


def _print_portfolio_recovery_result(r: PortfolioReturnRecoveryResult, dry_run: bool) -> None:
    print(f"\n{_hr()}")
    print(f"Portfolio {r.portfolio_id}  \"{r.portfolio_name}\"")
    print(_hr())

    if r.error:
        print(f"  ERROR: {r.error}")
        return

    print(f"  Snapshots scanned   : {r.snapshots_scanned}")
    changed_count = r.snapshots_changed
    if changed_count == 0:
        print("  No changes — all return fields already correct")
        return

    label = "Would change" if dry_run else "Changed"
    print(f"  {label}             : {changed_count}")
    print(f"  Unchanged           : {r.snapshots_unchanged}")

    if dry_run:
        for diff in r.diffs:
            if diff.changed:
                _print_recovery_diff(diff)


def _print_recovery_summary(
    results: list[PortfolioReturnRecoveryResult],
    elapsed: float,
    dry_run: bool,
) -> None:
    total_scanned = sum(r.snapshots_scanned for r in results)
    total_changed = sum(r.snapshots_changed for r in results)
    total_unchanged = sum(r.snapshots_unchanged for r in results)
    error_count = sum(1 for r in results if r.error)

    print(f"\n{_hr()}")
    if dry_run:
        print("Dry Run Summary")
    else:
        print("Summary")
    print(_hr())
    print(f"  Portfolios processed  : {len(results)}")
    print(f"  Snapshots scanned     : {total_scanned}")
    if dry_run:
        print(f"  Would change          : {total_changed}")
        print(f"  Would leave unchanged : {total_unchanged}")
        print(f"\n  No database changes were made.")
    else:
        print(f"  Snapshots changed     : {total_changed}")
        print(f"  Snapshots unchanged   : {total_unchanged}")
    if error_count:
        print(f"  Errors                : {error_count}")
    print(_hr())
    print(f"\nElapsed: {elapsed:.2f} seconds.")
    print()


def _cmd_recalculate_snapshot_returns(args: argparse.Namespace) -> int:
    """Recalculate return-related snapshot fields from stored NAV + transactions."""
    dry_run: bool = args.dry_run
    db      = SessionLocal()
    t_start = time.monotonic()

    try:
        ws = db.query(Workspace).first()
        if ws is None:
            print("ERROR: No workspace found in database.", file=sys.stderr)
            return 1
        ws_id = ws.id

        # ── Resolve which portfolios to process ───────────────────────────────
        if args.portfolio:
            p = db.query(Portfolio).filter_by(id=args.portfolio, workspace_id=ws_id).first()
            if p is None:
                print(f"ERROR: Portfolio {args.portfolio} not found.", file=sys.stderr)
                return 1
            portfolios = [p]
        elif args.all:
            portfolios = db.query(Portfolio).filter_by(workspace_id=ws_id).all()
            if not portfolios:
                print("ERROR: No portfolios found in workspace.", file=sys.stderr)
                return 1
        else:
            print("ERROR: Specify --portfolio ID or --all", file=sys.stderr)
            return 1

        # ── Preview / header ──────────────────────────────────────────────────
        print(f"\n{_hr()}")
        mode = "DRY RUN — " if dry_run else ""
        print(f"{mode}Recalculate Snapshot Returns")
        print(f"Portfolios: {', '.join(str(p.id) for p in portfolios)}")
        print(_hr())

        # ── Run recovery inside one transaction ───────────────────────────────
        results: list[PortfolioReturnRecoveryResult] = []
        try:
            if args.portfolio:
                r = recover_portfolio_snapshot_returns(
                    db, args.portfolio, ws_id, dry_run=dry_run
                )
                results.append(r)
            else:
                results = recover_all_snapshot_returns(db, ws_id, dry_run=dry_run)

            if not dry_run:
                db.commit()

        except Exception as exc:
            db.rollback()
            print(f"\nERROR: Recovery failed — rolled back. {exc}", file=sys.stderr)
            return 1

        # ── Per-portfolio output ──────────────────────────────────────────────
        for r in results:
            _print_portfolio_recovery_result(r, dry_run)

    except Exception as exc:
        print(f"\nERROR: Unexpected failure — {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    elapsed = time.monotonic() - t_start
    _print_recovery_summary(results, elapsed, dry_run)

    return 1 if any(r.error for r in results) else 0


# ══════════════════════════════════════════════════════════════════════════════
# Delete: delete_portfolio
# ══════════════════════════════════════════════════════════════════════════════

# Ordered list used for both the pre-deletion summary and the post-deletion report.
# Each entry: (display_label, count_key).
_RELATION_LABELS: list[tuple[str, str]] = [
    ("Portfolio Items",           "portfolio_items"),
    ("Transactions",              "transactions"),
    ("Snapshots",                 "snapshots"),
    ("Optimizer History",         "optimizer_history"),
    ("Recommendation Snapshots",  "recommendation_snapshots"),
    ("Execution Decisions",       "execution_decisions"),
    ("Shadow Portfolios",         "shadow_portfolios"),
    ("Shadow Snapshots",          "shadow_snapshots"),
    ("Attribution Metrics",       "attribution_metrics"),
]


def _count_portfolio_relations(db, portfolio_id: int) -> dict[str, int]:
    """Read-only: count every record that would be removed by a portfolio deletion."""
    shadow_ids = [
        r[0] for r in
        db.query(ShadowPortfolio.id)
        .filter(ShadowPortfolio.portfolio_id == portfolio_id)
        .all()
    ]

    return {
        "portfolio_items": (
            db.query(PortfolioItem)
            .filter(PortfolioItem.portfolio_id == portfolio_id)
            .count()
        ),
        "transactions": (
            db.query(Transaction)
            .filter(Transaction.portfolio_id == portfolio_id)
            .count()
        ),
        "snapshots": (
            db.query(PortfolioSnapshot)
            .filter(PortfolioSnapshot.portfolio_id == portfolio_id)
            .count()
        ),
        "optimizer_history": (
            db.query(OptimizerHistory)
            .filter(OptimizerHistory.portfolio_id == portfolio_id)
            .count()
        ),
        "recommendation_snapshots": (
            db.query(RecommendationSnapshot)
            .filter(RecommendationSnapshot.portfolio_id == portfolio_id)
            .count()
        ),
        "execution_decisions": (
            db.query(UserExecutionDecision)
            .filter(UserExecutionDecision.portfolio_id == portfolio_id)
            .count()
        ),
        "shadow_portfolios": len(shadow_ids),
        "shadow_snapshots": (
            db.query(ShadowPortfolioSnapshot)
            .filter(ShadowPortfolioSnapshot.shadow_portfolio_id.in_(shadow_ids))
            .count()
            if shadow_ids else 0
        ),
        "attribution_metrics": (
            db.query(AttributionMetric)
            .filter(AttributionMetric.portfolio_id == portfolio_id)
            .count()
        ),
    }


def _delete_portfolio_cascade(db, portfolio_id: int) -> dict[str, int]:
    """Delete all portfolio records in safe dependency order.

    Always deletes children before parents so no DB-level cascade fires
    unexpectedly and counts remain accurate.  Everything runs inside the
    caller's transaction — do NOT commit here.
    """
    # Collect shadow portfolio IDs before any deletes.
    shadow_ids = [
        r[0] for r in
        db.query(ShadowPortfolio.id)
        .filter(ShadowPortfolio.portfolio_id == portfolio_id)
        .all()
    ]

    counts: dict[str, int] = {}

    # 1. ShadowPortfolioSnapshot (deepest leaf under ShadowPortfolio)
    counts["shadow_snapshots"] = (
        db.query(ShadowPortfolioSnapshot)
        .filter(ShadowPortfolioSnapshot.shadow_portfolio_id.in_(shadow_ids))
        .delete(synchronize_session=False)
        if shadow_ids else 0
    )

    # 2. AttributionMetric — linked to ShadowPortfolio (CASCADE) and Portfolio (SET NULL)
    #    Delete here so we control the count; also catches any rows with
    #    shadow_portfolio_id outside the current portfolio (shouldn't exist, but safe).
    counts["attribution_metrics"] = (
        db.query(AttributionMetric)
        .filter(AttributionMetric.portfolio_id == portfolio_id)
        .delete(synchronize_session=False)
    )
    if shadow_ids:
        db.query(AttributionMetric)\
          .filter(AttributionMetric.shadow_portfolio_id.in_(shadow_ids))\
          .delete(synchronize_session=False)

    # 3. ShadowPortfolio
    counts["shadow_portfolios"] = (
        db.query(ShadowPortfolio)
        .filter(ShadowPortfolio.portfolio_id == portfolio_id)
        .delete(synchronize_session=False)
    )

    # 4. UserExecutionDecision (references RecommendationSnapshot with CASCADE)
    counts["execution_decisions"] = (
        db.query(UserExecutionDecision)
        .filter(UserExecutionDecision.portfolio_id == portfolio_id)
        .delete(synchronize_session=False)
    )

    # 5. RecommendationSnapshot (references OptimizerHistory with CASCADE)
    counts["recommendation_snapshots"] = (
        db.query(RecommendationSnapshot)
        .filter(RecommendationSnapshot.portfolio_id == portfolio_id)
        .delete(synchronize_session=False)
    )

    # 6. OptimizerHistory
    counts["optimizer_history"] = (
        db.query(OptimizerHistory)
        .filter(OptimizerHistory.portfolio_id == portfolio_id)
        .delete(synchronize_session=False)
    )

    # 7. PortfolioSnapshot
    counts["snapshots"] = (
        db.query(PortfolioSnapshot)
        .filter(PortfolioSnapshot.portfolio_id == portfolio_id)
        .delete(synchronize_session=False)
    )

    # 8. Transaction
    counts["transactions"] = (
        db.query(Transaction)
        .filter(Transaction.portfolio_id == portfolio_id)
        .delete(synchronize_session=False)
    )

    # 9. PortfolioItem
    counts["portfolio_items"] = (
        db.query(PortfolioItem)
        .filter(PortfolioItem.portfolio_id == portfolio_id)
        .delete(synchronize_session=False)
    )

    # 10. Portfolio itself
    db.query(Portfolio)\
      .filter(Portfolio.id == portfolio_id)\
      .delete(synchronize_session=False)

    return counts


def _print_delete_preview(portfolio: Portfolio, counts: dict[str, int]) -> None:
    total = sum(counts.values())
    print(f"\n{_hr()}")
    print("Portfolio to delete")
    print(_hr())
    print(f"  Name         : {portfolio.name}")
    print(f"  ID           : {portfolio.id}")
    print(f"  Cash Balance : {portfolio.cash_balance:,.2f} THB")
    print(f"\nWill permanently delete:")
    for label, key in _RELATION_LABELS:
        n = counts.get(key, 0)
        if n:
            print(f"  {label:<28} : {n:>6,}")
    print(f"  {'─' * 36}")
    print(f"  {'Total records':<28} : {total:>6,}")
    print(_hr())
    print("  WARNING: This action cannot be undone.")


def _print_delete_result(portfolio_id: int, portfolio_name: str, counts: dict[str, int]) -> None:
    print(f"\n{_hr()}")
    print(f"Deleted Portfolio {portfolio_id}  \"{portfolio_name}\"")
    print(_hr())
    for label, key in _RELATION_LABELS:
        n = counts.get(key, 0)
        if n:
            print(f"  {label:<28} : {n:>6,}")
    print(_hr())
    print("  Done.")
    print()


# ── Command: delete_portfolio ─────────────────────────────────────────────────

def _cmd_delete_portfolio(args: argparse.Namespace) -> int:
    db      = SessionLocal()
    t_start = time.monotonic()

    try:
        ws = db.query(Workspace).first()
        if ws is None:
            print("ERROR: No workspace found in database.", file=sys.stderr)
            return 1
        ws_id = ws.id

        portfolio = (
            db.query(Portfolio)
            .filter(Portfolio.id == args.id, Portfolio.workspace_id == ws_id)
            .first()
        )
        if portfolio is None:
            print(f"ERROR: Portfolio {args.id} not found.", file=sys.stderr)
            return 1

        # Stash name before deletion
        portfolio_name = portfolio.name
        portfolio_id   = portfolio.id

        # Count related records (read-only — before any deletes)
        counts = _count_portfolio_relations(db, portfolio_id)

        _print_delete_preview(portfolio, counts)

        if not args.yes:
            print()
            if not _confirm():
                print("\nDeletion cancelled.")
                return 3

        # Delete inside a single transaction
        try:
            deleted = _delete_portfolio_cascade(db, portfolio_id)
            db.commit()
        except Exception as exc:
            db.rollback()
            print(f"\nERROR: Deletion failed — rolled back. {exc}", file=sys.stderr)
            return 1

    except Exception as exc:
        print(f"\nERROR: Unexpected failure — {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    elapsed = time.monotonic() - t_start
    _print_delete_result(portfolio_id, portfolio_name, deleted)
    print(f"  Completed in {elapsed:.2f} seconds.")
    print()
    return 0


# ══════════════════════════════════════════════════════════════════════════════
# Rebuild: rebuild_portfolio / rebuild_all
# ══════════════════════════════════════════════════════════════════════════════

_STATUS_ICON_RECON = {
    ReconciliationStatus.MATCH:     "✓",
    ReconciliationStatus.DIFFERENT: "≠",
    ReconciliationStatus.MISSING:   "+",
    ReconciliationStatus.EXTRA:     "−",
}


def _print_confidence_report(r: ConfidenceReport) -> None:
    """Print the multi-dimensional confidence report."""
    print()
    print("  Confidence Report")
    print(f"    Replay confidence    : {r.replay_confidence:.0f}%")
    print(f"    Ledger integrity     : {r.ledger_integrity:.0f}%")
    print(f"    Historical coverage  : {r.historical_coverage:.0f}%")
    print(f"    Snapshot consistency : {r.snapshot_consistency:.0f}%")
    print(f"    Validator confidence : {r.validator_confidence:.0f}%")
    print(f"    {'─' * 32}")
    print(f"    Overall              : {r.overall:.1f}%")


def _plan_to_dict(plan: ReconstructionPlan) -> dict:
    """Serialize a ReconstructionPlan to a JSON-safe dict."""
    s = plan.summary
    return {
        "portfolio_id":      plan.portfolio_id,
        "generated_at":      plan.generated_at,
        "confidence_score":  plan.confidence_score,
        "validator_passed":  plan.validator_passed,
        "critical_findings": plan.critical_findings,
        "summary": {
            "portfolio_updated_fields": list(s.portfolio_updated_fields),
            "item_inserts":             s.item_inserts,
            "item_updates":             s.item_updates,
            "item_deletes":             s.item_deletes,
            "snapshot_inserts":         s.snapshot_inserts,
            "snapshot_updates":         s.snapshot_updates,
            "snapshot_deletes":         s.snapshot_deletes,
            "total_write_operations":   s.total_write_operations,
            "validator_critical":       s.validator_critical,
            "validator_errors":         s.validator_errors,
            "validator_warnings":       s.validator_warnings,
            "confidence_score":         s.confidence_score,
        },
        "operations": [
            {
                "table":         op.table,
                "operation":     op.operation,
                "object_id":     op.object_id,
                "field":         op.field,
                "current_value": op.current_value,
                "new_value":     op.new_value,
                "reason":        op.reason,
            }
            for op in plan.operations
        ],
    }


def _print_execution_plan(plan: ReconstructionPlan) -> None:
    """Print a formatted execution plan."""
    s = plan.summary
    print(f"\n{_hr()}")
    print(f"Execution Plan  —  Portfolio {plan.portfolio_id}")
    print(_hr())
    print(f"  Generated at              : {plan.generated_at}")
    print()
    print("  PortfolioItem")
    print(f"    INSERT  : {s.item_inserts}")
    print(f"    UPDATE  : {s.item_updates}")
    print(f"    DELETE  : {s.item_deletes}")
    print()
    print("  PortfolioSnapshot")
    print(f"    INSERT  : {s.snapshot_inserts}")
    print(f"    UPSERT  : {s.snapshot_updates}")
    if s.snapshot_deletes:
        print(f"    DELETE  : {s.snapshot_deletes}")
    if s.portfolio_updated_fields:
        print()
        print("  Portfolio")
        print(f"    UPDATE  : {', '.join(s.portfolio_updated_fields)}")
    print()
    print("  Validator")
    print(f"    CRITICAL : {s.validator_critical}")
    print(f"    ERROR    : {s.validator_errors}")
    print(f"    WARNING  : {s.validator_warnings}")
    print()
    print(f"  Confidence                : {plan.confidence_score:.1f}%")
    print()
    print(f"  Estimated write operations: {s.total_write_operations}")

    if plan.operations:
        print()
        print("  Operations")
        hdr_table = "Table"
        hdr_op    = "Op"
        hdr_id    = "ID"
        hdr_field = "Field"
        print(f"  {hdr_table:<20}  {hdr_op:<7}  {hdr_id:<24}  {hdr_field:<18}  Reason")
        print(f"  {'-'*20}  {'-'*7}  {'-'*24}  {'-'*18}  {'-'*38}")
        display_ops = plan.operations[:60]
        for op in display_ops:
            fld    = op.field or "*"
            reason = (op.reason[:38] + "…") if len(op.reason) > 39 else op.reason
            print(f"  {op.table:<20}  {op.operation:<7}  {op.object_id:<24}  {fld:<18}  {reason}")
        if len(plan.operations) > 60:
            remaining = len(plan.operations) - 60
            print(
                f"\n  ({remaining} more operation(s) not shown — "
                "use --plan-json for the complete list)"
            )
    print(_hr())


def _print_rebuild_result(r: RebuildResult, verbose: bool = False) -> None:
    """Print a formatted reconciliation report for one portfolio."""
    print(f"\n{_hr()}")
    print(f"Portfolio {r.portfolio_id}  \"{r.portfolio_name}\"")
    print(_hr())

    if not r.success and r.error:
        print(f"  ERROR: {r.error}")
        return

    # Stage 1 summary
    print(f"  Transactions replayed   : {r.transactions_replayed}")
    print(f"  Reconstructed cash      : {(r.reconstructed_cash or 0):>14,.2f}")
    print(f"  Reconstructed holdings  : {r.reconstructed_holdings_count}")

    # Stage 2/3 summary
    if not r.skip_snapshots:
        print(f"  Snapshots processed     : {r.snapshots_processed}")
        if r.snapshots_skipped_low_coverage:
            print(f"  Low-coverage snapshots  : {r.snapshots_skipped_low_coverage}  (written with price_missing=True)")

    # Stage 4 reconciliation summary
    print()
    print("  Holdings reconciliation")
    print(f"    Match     : {r.items_matched}")
    if r.items_different:
        print(f"    Different : {r.items_different}  ← DRIFT DETECTED")
    if r.items_missing:
        print(f"    Missing   : {r.items_missing}  (in transactions, not in DB)")
    if r.items_extra:
        print(f"    Extra     : {r.items_extra}  (in DB, not in transactions)")

    if not r.skip_snapshots:
        print()
        print("  Snapshot reconciliation")
        print(f"    Match     : {r.snapshots_matched}")
        if r.snapshots_different:
            print(f"    Different : {r.snapshots_different}  ← NAV DRIFT DETECTED")
        if r.snapshots_missing:
            print(f"    Missing   : {r.snapshots_missing}")
        if r.snapshots_extra:
            print(f"    Extra     : {r.snapshots_extra}")

    # Stage 5 — Ledger validation
    print()
    if r.ledger_criticals or r.ledger_errors or r.ledger_warnings:
        print("  Ledger validation")
        if r.ledger_criticals:
            print(f"    Critical : {r.ledger_criticals}  ← COMMIT BLOCKED")
        if r.ledger_errors:
            print(f"    Error    : {r.ledger_errors}")
        if r.ledger_warnings:
            print(f"    Warning  : {r.ledger_warnings}")
    elif r.validator_report is not None:
        print("  Ledger validation       : CLEAN")

    # Stage 6 — Confidence report
    if r.confidence_report is not None:
        _print_confidence_report(r.confidence_report)
    else:
        print(f"\n  Confidence              : {r.confidence_score:.1f}%")

    # Stage 7 — Execution plan summary (brief)
    if r.execution_plan is not None:
        s = r.execution_plan.summary
        print()
        print(f"  Execution plan          : {s.total_write_operations} write operation(s)")
        if s.item_inserts or s.item_updates or s.item_deletes:
            print(f"    PortfolioItem         : +{s.item_inserts} ~{s.item_updates} -{s.item_deletes}")
        if s.snapshot_inserts or s.snapshot_updates:
            print(f"    PortfolioSnapshot     : +{s.snapshot_inserts} ~{s.snapshot_updates}")

    # Commit status
    print()
    if r.aborted:
        print("  ABORTED — CRITICAL ledger findings blocked the commit")
        print("  Run:  python manage.py validate_ledger --portfolio", r.portfolio_id)
    elif r.dry_run:
        print("  DRY RUN — no database changes were made")
    elif r.committed:
        print("  COMMITTED — database updated successfully")
        if r.backup_path:
            print(f"  Backup                  : {r.backup_path}")
    else:
        print("  NOT COMMITTED — see error above")

    # Verbose: per-row reconciliation detail
    if verbose and r.reconciliation_report:
        different = [
            row for row in r.reconciliation_report
            if row.status != ReconciliationStatus.MATCH
        ]
        if different:
            print()
            print("  Differences")
            print(f"  {'Type':<16}  {'ID':<18}  {'Field':<24}  {'Current':>14}  {'Reconstructed':>14}  Status")
            print(f"  {'-'*16}  {'-'*18}  {'-'*24}  {'-'*14}  {'-'*14}  {'-'*9}")
            for row in different:
                icon = _STATUS_ICON_RECON.get(row.status, "?")
                curr_s  = str(row.current_value)[:14]  if row.current_value  is not None else "—"
                recon_s = str(row.reconstructed_value)[:14] if row.reconstructed_value is not None else "—"
                print(
                    f"  {row.entity_type:<16}  {row.identifier:<18}  {row.field:<24}  "
                    f"{curr_s:>14}  {recon_s:>14}  {icon} {row.status.value}"
                )


def _print_rebuild_summary(
    results:  list[RebuildResult],
    elapsed:  float,
    dry_run:  bool,
) -> None:
    total        = len(results)
    succeeded    = sum(1 for r in results if r.success)
    failed       = total - succeeded
    aborted      = sum(1 for r in results if r.aborted)
    committed    = sum(1 for r in results if r.committed)
    diff_items   = sum(r.items_different for r in results)
    diff_snaps   = sum(r.snapshots_different for r in results)
    crit_total   = sum(r.ledger_criticals for r in results)
    err_total    = sum(r.ledger_errors    for r in results)
    avg_conf     = (
        sum(r.confidence_score for r in results) / total if total else 100.0
    )

    print(f"\n{_hr()}")
    if dry_run:
        print("Dry Run Summary")
    else:
        print("Rebuild Summary")
    print(_hr())
    print(f"  Portfolios processed    : {total}")
    print(f"  Succeeded               : {succeeded}")
    if failed:
        print(f"  Failed                  : {failed}")
    if aborted:
        print(f"  Aborted (CRITICAL)      : {aborted}  ← fix ledger before committing")
    if diff_items:
        print(f"  Holdings with drift     : {diff_items}")
    if diff_snaps:
        print(f"  Snapshots with NAV diff : {diff_snaps}")
    if crit_total:
        print(f"  Ledger CRITICAL findings: {crit_total}")
    if err_total:
        print(f"  Ledger ERROR findings   : {err_total}")
    print(f"  Avg confidence score    : {avg_conf:.1f}%")
    if dry_run:
        print(f"\n  No database changes were made.")
    else:
        print(f"  Committed               : {committed}")
    print(_hr())
    print(f"\nCompleted in {elapsed:.2f} seconds.")
    print()


async def _cmd_rebuild_portfolio(args: argparse.Namespace) -> int:
    """Deterministic portfolio rebuild from the transaction ledger."""
    # --plan and --plan-json imply dry_run; --commit is the explicit write opt-in
    dry_run:   bool     = getattr(args, "dry_run", False)
    show_plan: bool     = getattr(args, "plan", False)
    plan_json: str|None = getattr(args, "plan_json", None)

    if show_plan or plan_json:
        dry_run = True   # plan-only mode never writes
    elif getattr(args, "commit", False):
        dry_run = False  # explicit --commit overrides default dry-run

    verbose: bool = getattr(args, "verbose", False)
    yes:     bool = getattr(args, "yes", False)
    t_start  = time.monotonic()

    db = SessionLocal()
    try:
        ws = db.query(Workspace).first()
        if ws is None:
            print("ERROR: No workspace found in database.", file=sys.stderr)
            return 1
        ws_id = ws.id

        # Resolve portfolio(s) to rebuild
        rebuild_ids: list[int] = []

        if getattr(args, "all", False):
            portfolios = db.query(Portfolio).filter_by(workspace_id=ws_id).all()
            if not portfolios:
                print("ERROR: No portfolios found.", file=sys.stderr)
                return 1
            rebuild_ids = [p.id for p in portfolios]
        elif getattr(args, "portfolio", None):
            p = db.query(Portfolio).filter_by(
                id=args.portfolio, workspace_id=ws_id
            ).first()
            if p is None:
                print(f"ERROR: Portfolio {args.portfolio} not found.", file=sys.stderr)
                return 1
            rebuild_ids = [p.id]
        else:
            print(
                "ERROR: Specify --portfolio ID  or  --all",
                file=sys.stderr,
            )
            return 1

        from_date      = getattr(args, "from_date", None)
        skip_snapshots = getattr(args, "skip_snapshots", False)
        skip_benchmark = getattr(args, "skip_benchmark", False)
        do_backup      = getattr(args, "backup", False)

        # ── Confirmation prompt ───────────────────────────────────────────────
        print(f"\n{_hr()}")
        if show_plan or plan_json:
            action = "PLAN ONLY — "
        elif dry_run:
            action = "DRY RUN — "
        else:
            action = ""
        print(f"{action}Portfolio Reconstruction Engine")
        print(_hr())
        print(f"  Portfolios       : {rebuild_ids}")
        if from_date:
            print(f"  From date        : {from_date}")
        if skip_snapshots:
            print(f"  Skip snapshots   : yes")
        stage_list = "1 (replay)"
        if not skip_snapshots:
            stage_list += " + 2-3 (snapshots)"
        stage_list += " + 4 (reconcile) + 5 (validate) + 6 (plan)"
        if not dry_run:
            stage_list += " + 7 (backup) + 8 (commit)"
        print(f"  Stages           : {stage_list}")
        if show_plan or plan_json:
            print("  Mode             : PLAN — no database writes")
        print()

        if not dry_run and not yes:
            print("This will overwrite Portfolio.cash_balance and all PortfolioItem rows.")
            if not skip_snapshots:
                print("Existing snapshots in the rebuild window will be overwritten.")
            if not _confirm():
                print("\nRebuild cancelled.")
                return 3

        # ── Run rebuild ───────────────────────────────────────────────────────
        results: list[RebuildResult] = []
        progress_lines: list[str] = []

        def _cb(msg: str) -> None:
            progress_lines.append(msg)
            print(f"  {msg}")

        for pid in rebuild_ids:
            r = await rebuild_portfolio(
                db             = db,
                portfolio_id   = pid,
                workspace_id   = ws_id,
                from_date      = from_date,
                skip_snapshots = skip_snapshots,
                skip_benchmark = skip_benchmark,
                dry_run        = dry_run,
                backup         = do_backup,
                progress_cb    = _cb,
            )
            results.append(r)
            _print_rebuild_result(r, verbose=verbose)

            # Explicit plan display (--plan or --plan-json)
            if (show_plan or plan_json) and r.execution_plan:
                _print_execution_plan(r.execution_plan)

            # Export plan to JSON (--plan-json)
            if plan_json and r.execution_plan:
                plan_path = plan_json
                if len(rebuild_ids) > 1:
                    base, ext = os.path.splitext(plan_json)
                    plan_path = f"{base}_{pid}{ext or '.json'}"
                try:
                    with open(plan_path, "w", encoding="utf-8") as fh:
                        json.dump(_plan_to_dict(r.execution_plan), fh, indent=2, default=str)
                    print(f"\n  Execution plan JSON: {plan_path}")
                except Exception as exc:
                    print(f"\n  WARNING: Could not write plan JSON: {exc}", file=sys.stderr)

    except Exception as exc:
        print(f"\nERROR: Unexpected failure — {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    elapsed = time.monotonic() - t_start
    _print_rebuild_summary(results, elapsed, dry_run)

    if any(not r.success for r in results):
        return 1
    return 0


# ══════════════════════════════════════════════════════════════════════════════
# Validate: validate_ledger
# ══════════════════════════════════════════════════════════════════════════════

_SEV_ICON_LEDGER: dict[FindingSeverity, str] = {
    FindingSeverity.CRITICAL: "✗",
    FindingSeverity.ERROR:    "!",
    FindingSeverity.WARNING:  "⚠",
}

_LEDGER_SEV_ORDER = {
    FindingSeverity.CRITICAL: 0,
    FindingSeverity.ERROR:    1,
    FindingSeverity.WARNING:  2,
}


def _print_ledger_finding(f: LedgerFinding, index: int | None = None) -> None:
    """Print one LedgerFinding in the user-specified verbose format."""
    icon  = _SEV_ICON_LEDGER.get(f.severity, "?")
    sep   = "─" * _W
    label = f"[{index}] " if index is not None else ""

    print(f"\n{sep}")
    print(f"{label}{icon} {f.severity.value}")
    print(f"Portfolio {f.portfolio_id}")
    if f.symbol:
        sym_line = f.symbol
        if f.normalized_symbol and f.normalized_symbol != f.symbol:
            sym_line += f"  (→ {f.normalized_symbol})"
        print(sym_line)
    print()
    print(f.title)
    print()

    # Transaction IDs with brief details from finding.details
    if f.transaction_ids:
        for tx_id in f.transaction_ids:
            print(f"tx{tx_id}")

    print()
    print(f.explanation)
    print()
    print("Recommendation:")
    # Word-wrap recommendation at ~_W chars
    import textwrap as _tw
    for line in _tw.wrap(f.recommendation, width=_W):
        print(f"  {line}")


def _print_ledger_report(r: LedgerValidationReport) -> None:
    """Print a full validation report for one portfolio."""
    print(f"\n{_hr()}")
    print(f"Portfolio {r.portfolio_id}  \"{r.portfolio_name}\"")
    print(_hr())
    print(f"Transactions inspected : {r.transactions_inspected}")
    if r.price_check_performed:
        print("Price check           : performed")

    if not r.findings:
        print(f"\n  PASS — Ledger is clean. No anomalies detected.")
        return

    counts = {
        FindingSeverity.CRITICAL: len(r.criticals),
        FindingSeverity.ERROR:    len(r.errors),
        FindingSeverity.WARNING:  len(r.warnings),
    }
    print()
    for sev in (FindingSeverity.CRITICAL, FindingSeverity.ERROR, FindingSeverity.WARNING):
        n = counts[sev]
        if n:
            icon = _SEV_ICON_LEDGER[sev]
            print(f"  {icon} {sev.value:<10} : {n}")

    for i, finding in enumerate(r.findings, 1):
        _print_ledger_finding(finding, index=i)

    print(f"\n{_hr()}")
    print(f"  {r.overall_severity}")


def _print_ledger_overall_summary(
    results:  list[LedgerValidationReport],
    elapsed:  float,
) -> None:
    total_crit = sum(len(r.criticals) for r in results)
    total_err  = sum(len(r.errors)    for r in results)
    total_warn = sum(len(r.warnings)  for r in results)

    failing  = [r for r in results if r.overall_severity == "CRITICAL"]
    errored  = [r for r in results if r.overall_severity == "ERROR"]
    warning  = [r for r in results if r.overall_severity == "WARNING"]

    print(f"\n{_hr()}")
    print("Overall Ledger Validation")
    print(_hr())
    print(f"  Portfolios checked : {len(results)}")
    print(f"  Critical           : {total_crit}")
    print(f"  Error              : {total_err}")
    print(f"  Warning            : {total_warn}")
    print()

    if not total_crit and not total_err and not total_warn:
        print("  PASS — All ledgers are clean.")
    else:
        for r in failing:
            print(f"  ✗ CRITICAL  Portfolio {r.portfolio_id}  {r.portfolio_name}"
                  f"  ({len(r.criticals)} critical)")
        for r in errored:
            print(f"  ! ERROR     Portfolio {r.portfolio_id}  {r.portfolio_name}"
                  f"  ({len(r.errors)} error{'s' if len(r.errors) != 1 else ''})")
        for r in warning:
            print(f"  ⚠ WARNING   Portfolio {r.portfolio_id}  {r.portfolio_name}"
                  f"  ({len(r.warnings)} warning{'s' if len(r.warnings) != 1 else ''})")

    print(_hr())
    print(f"\nCompleted in {elapsed:.2f} seconds.")
    print()


def _print_ledger_confidence(report: LedgerValidationReport, label: str = "") -> None:
    """Print a single-line confidence score for a validation report."""
    score = _ledger_confidence(report)
    tag   = f"  ({label})" if label else ""
    print(f"\n  Ledger confidence{tag}: {score:.1f}%")


def _print_ledger_comparison(c: LedgerValidationComparison) -> None:
    """Print a structured raw → effective comparison for one portfolio."""
    r = c.raw_report
    e = c.effective_report

    print(f"\n{_hr()}")
    print(f"Portfolio {r.portfolio_id}  \"{r.portfolio_name}\"")
    print(_hr())

    raw_conf = _ledger_confidence(r)
    eff_conf = _ledger_confidence(e)

    print(f"Raw ledger findings   : {len(r.findings)}   (confidence {raw_conf:.1f}%)")
    print(f"Effective findings    : {len(e.findings)}   (confidence {eff_conf:.1f}%)")
    print()

    print(f"Resolved  (raw only)  : {len(c.resolved_findings)}")
    for key in c.resolved_findings:
        print(f"  - {key}")

    print(f"Remaining (both)      : {len(c.remaining_findings)}")
    for key in c.remaining_findings:
        print(f"  = {key}")

    if c.newly_introduced_findings:
        print(f"New       (eff only)  : {len(c.newly_introduced_findings)}")
        for key in c.newly_introduced_findings:
            print(f"  + {key}")
    else:
        print("New       (eff only)  : 0  [invariant holds]")


async def _cmd_validate_ledger(args: argparse.Namespace) -> int:
    """Read-only transaction ledger audit. Never modifies the database."""
    db      = SessionLocal()
    t_start = time.monotonic()
    results: list[LedgerValidationReport] = []

    fetch_prices        = getattr(args, "price_check", False)
    price_deviation_pct = getattr(args, "price_threshold", 100.0)
    do_effective        = getattr(args, "effective", False)
    do_compare          = getattr(args, "compare", False)

    try:
        ws = db.query(Workspace).first()
        if ws is None:
            print("ERROR: No workspace found in database.", file=sys.stderr)
            return 1
        ws_id = ws.id

        if getattr(args, "all", False):
            portfolios = db.query(Portfolio).filter_by(workspace_id=ws_id).all()
            if not portfolios:
                print("ERROR: No portfolios found in workspace.", file=sys.stderr)
                return 1
        elif getattr(args, "portfolio", None):
            p = db.query(Portfolio).filter_by(id=args.portfolio, workspace_id=ws_id).first()
            if p is None:
                print(f"ERROR: Portfolio {args.portfolio} not found.", file=sys.stderr)
                return 1
            portfolios = [p]
        else:
            print("ERROR: Specify --portfolio ID  or  --all", file=sys.stderr)
            return 1

        # ── Header ────────────────────────────────────────────────────────────
        print(f"\n{_hr()}")
        if do_compare:
            print("Ledger Validator  —  Raw vs Effective Comparison")
            print("(read-only — never modifies the database)")
        elif do_effective:
            print("Ledger Validator  —  Effective Ledger Mode")
            print("(read-only — repair overlay applied before validation)")
        else:
            print("Ledger Validator  (read-only — never modifies the database)")
        if fetch_prices:
            print(f"Price check enabled  threshold={price_deviation_pct:.0f}%")
        print(_hr())

        # ── Per-portfolio validation ──────────────────────────────────────────
        for p in portfolios:
            print(f"  Validating portfolio {p.id} \"{p.name}\"...")

            if do_compare:
                repairs = load_active_repairs(db, p.id)
                c = await compare_ledger_validation(
                    db                  = db,
                    portfolio_id        = p.id,
                    workspace_id        = ws_id,
                    repairs             = repairs,
                    fetch_prices        = fetch_prices,
                    price_deviation_pct = price_deviation_pct,
                )
                _print_ledger_comparison(c)
                results.append(c.effective_report)

            elif do_effective:
                repairs = load_active_repairs(db, p.id)
                r = await validate_portfolio_ledger(
                    db                  = db,
                    portfolio_id        = p.id,
                    workspace_id        = ws_id,
                    fetch_prices        = fetch_prices,
                    price_deviation_pct = price_deviation_pct,
                    repairs             = repairs,
                    mode                = "effective",
                )
                results.append(r)
                _print_ledger_report(r)
                _print_ledger_confidence(r, label="effective")

            else:
                r = await validate_portfolio_ledger(
                    db                  = db,
                    portfolio_id        = p.id,
                    workspace_id        = ws_id,
                    fetch_prices        = fetch_prices,
                    price_deviation_pct = price_deviation_pct,
                )
                results.append(r)
                _print_ledger_report(r)

    except Exception as exc:
        print(f"\nERROR: Unexpected failure — {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    elapsed = time.monotonic() - t_start
    _print_ledger_overall_summary(results, elapsed)

    # Exit codes: 0 = clean, 1 = warnings/errors, 2 = criticals
    total_crit   = sum(len(r.criticals) for r in results)
    total_issues = sum(len(r.findings)  for r in results)
    if total_crit:
        return 2
    if total_issues:
        return 1
    return 0


# ══════════════════════════════════════════════════════════════════════════════
# Golden Baseline: golden_baseline  (M5 Track B Stage 1)
# ══════════════════════════════════════════════════════════════════════════════

def _print_baseline_summary(baseline: GoldenBaseline) -> None:
    print(f"  Portfolio {baseline.portfolio_id} \"{baseline.portfolio_name}\"")
    print(f"    transactions replayed : {baseline.transactions_replayed}")
    print(f"    holdings              : {baseline.reconstructed_holdings_count}")
    print(f"    cash                  : {baseline.reconstructed_cash}")
    print(f"    snapshots processed   : {baseline.snapshots_processed}")
    print(f"    validator severity    : {baseline.validator_overall_severity}")
    print(f"    content hash          : {baseline.content_hash}")


def _print_parity_report(report: ParityReport, baseline_hash: str) -> None:
    status = "IDENTICAL" if report.is_bit_identical else "DIFFERS"
    print(f"  [{status}] portfolio {report.portfolio_id}  baseline_hash={baseline_hash[:12]}")
    for d in report.holding_diffs:
        print(f"    HOLDING  {d.symbol}.{d.field}: {d.baseline_value!r} -> {d.rebuilt_value!r}  [{d.status.value}]")
    for d in report.snapshot_diffs:
        print(f"    SNAPSHOT {d.date}.{d.field}: {d.baseline_value!r} -> {d.rebuilt_value!r}  [{d.status.value}]")
    for d in report.validator_diffs:
        print(f"    VALIDATOR {d.finding_key}: {d.baseline_severity} -> {d.rebuilt_severity}  [{d.status.value}]")


def _print_regression_report(report: RegressionReport) -> None:
    print(f"\n{_hr()}")
    print("Golden Baseline — Regression Report (Stage 1)")
    print(_hr())
    print(f"  generated_at              : {report.generated_at}")
    print(f"  portfolio_count           : {report.portfolio_count}")
    print(f"  portfolios_bit_identical  : {report.portfolios_bit_identical}")
    print(f"  portfolios_with_diffs     : {report.portfolios_with_diffs}")
    print()
    for e in report.entries:
        status = "IDENTICAL" if e.is_bit_identical else "DIFFERS"
        print(
            f"  [{status:9}] portfolio {e.portfolio_id} \"{e.portfolio_name}\"  "
            f"hash={e.baseline_hash[:12]}  "
            f"holding_diffs={e.holding_diff_count} "
            f"snapshot_diffs={e.snapshot_diff_count} "
            f"validator_diffs={e.validator_diff_count}"
        )


async def _cmd_golden_baseline(args: argparse.Namespace) -> int:
    """Golden Baseline capture / determinism verification (read-only).

    Never writes to the database — every replay is dry_run=True. Baseline
    storage (--capture) is a plain JSON file per portfolio under
    --baseline-dir, outside the operational DB (Migration Principle 7).
    """
    db      = SessionLocal()
    t_start = time.monotonic()
    baseline_dir    = getattr(args, "baseline_dir", "golden_baselines")
    skip_snapshots  = getattr(args, "skip_snapshots", False)

    try:
        ws = db.query(Workspace).first()
        if ws is None:
            print("ERROR: No workspace found in database.", file=sys.stderr)
            return 1
        ws_id = ws.id

        if getattr(args, "all", False):
            portfolios = db.query(Portfolio).filter_by(workspace_id=ws_id).all()
            if not portfolios:
                print("ERROR: No portfolios found in workspace.", file=sys.stderr)
                return 1
            portfolio_ids = [p.id for p in portfolios]
        elif getattr(args, "portfolio", None):
            p = db.query(Portfolio).filter_by(id=args.portfolio, workspace_id=ws_id).first()
            if p is None:
                print(f"ERROR: Portfolio {args.portfolio} not found.", file=sys.stderr)
                return 1
            portfolio_ids = [p.id]
        else:
            print("ERROR: Specify --portfolio ID  or  --all", file=sys.stderr)
            return 1

        print(f"\n{_hr()}")
        print("Golden Baseline  (read-only — every replay is dry_run=True)")
        print(_hr())

        if getattr(args, "capture", False):
            for pid in portfolio_ids:
                print(f"  Capturing portfolio {pid}...")
                baseline = await capture_golden_baseline(
                    db, portfolio_id=pid, workspace_id=ws_id, skip_snapshots=skip_snapshots,
                )
                path = save_baseline(baseline, baseline_dir=baseline_dir)
                _print_baseline_summary(baseline)
                print(f"    saved -> {path}")
            return 0

        if getattr(args, "compare_stored", False):
            any_diff = False
            for pid in portfolio_ids:
                stored = load_baseline(pid, baseline_dir=baseline_dir)
                if stored is None:
                    print(f"  ERROR: no stored baseline for portfolio {pid} in {baseline_dir} "
                          f"— run --capture first.", file=sys.stderr)
                    any_diff = True
                    continue
                rebuilt = await rebuild_portfolio(
                    db, portfolio_id=pid, workspace_id=ws_id,
                    dry_run=True, skip_snapshots=skip_snapshots, backup=False,
                )
                parity = compare_against_baseline(stored, rebuilt)
                _print_parity_report(parity, stored.content_hash)
                any_diff = any_diff or not parity.is_bit_identical
            return 1 if any_diff else 0

        # Default action: verify determinism and print a regression report.
        report = await generate_regression_report(
            db, workspace_id=ws_id, portfolio_ids=portfolio_ids, skip_snapshots=skip_snapshots,
        )
        _print_regression_report(report)
        elapsed = time.monotonic() - t_start
        print(f"\n  elapsed: {elapsed:.2f}s")
        return 0 if report.portfolios_with_diffs == 0 else 1

    except Exception as exc:
        print(f"\nERROR: Unexpected failure — {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════════
# Migration planner: plan_migration
# ══════════════════════════════════════════════════════════════════════════════

def _print_claim_shape_entry(entry) -> None:
    shape, result = entry.shape, entry.result
    print(f"\n  {shape.raw_symbol} / {shape.canonical_symbol or '—'}   currency={shape.currency or '—'}")
    print(f"    transactions : {list(entry.transaction_ids)}")
    print(f"    portfolios   : {list(entry.portfolio_ids)}")
    print(f"    verdict      : {result.verdict.value}")
    for candidate in result.candidates:
        print(f"    candidate asset_id={candidate.asset_id}  score={candidate.score:.1f}")
        for contribution in candidate.contributions:
            print(
                f"        + {contribution.identifier_type.value}:{contribution.identifier_value} "
                f"({'current' if contribution.is_current else 'historical'}) weight={contribution.applied_weight:.1f}"
            )


def _print_migration_summary(summary: MigrationSummary) -> None:
    s = summary.statistics
    tv, cv = s.transaction_verdicts, s.claim_shape_verdicts

    print(f"\n{_hr()}")
    print("Migration Summary")
    print(_hr())
    print(f"  Portfolios scanned            : {list(summary.portfolios_scanned)}")
    print(f"  Total transactions            : {s.total_transactions}")
    print(f"  Cash-only (no identity claim) : {s.cash_only_transactions}")
    print(f"  Identity-bearing              : {s.identity_bearing_transactions}")
    print()
    print("  Transaction-level verdicts")
    print(f"    Resolved  : {tv.resolved:<6}  Candidate : {tv.candidate:<6}")
    print(f"    Ambiguous : {tv.ambiguous:<6}  Conflict  : {tv.conflict:<6}  Unknown : {tv.unknown}")
    print()
    print(f"  Resolution %                  : {s.resolution_pct:.1f}%")
    print(f"  Decisive %                    : {s.decisive_pct:.1f}%")
    print()
    print("  Claim-shape-level verdicts (distinct identity questions)")
    print(f"    Resolved  : {cv.resolved:<6}  Candidate : {cv.candidate:<6}")
    print(f"    Ambiguous : {cv.ambiguous:<6}  Conflict  : {cv.conflict:<6}  Unknown : {cv.unknown}")
    print()
    print(f"  Assets created (expected)     : {s.assets_created_expected}  (estimate — see Caveats)")
    print(f"  Assets reused                 : {s.assets_reused}")
    print(f"  Manual adjudications required : {s.manual_adjudications_required}")
    print(f"  Potential duplicates          : {s.potential_duplicates}")
    print(f"  Potential merge candidates    : {s.potential_merge_candidates}")

    if summary.ambiguity_report.entries:
        print(f"\n{_hr()}")
        print(f"Ambiguity Report  ({len(summary.ambiguity_report.entries)} claim shape(s))")
        print(_hr())
        for entry in summary.ambiguity_report.entries:
            _print_claim_shape_entry(entry)

    if summary.conflict_report.entries:
        print(f"\n{_hr()}")
        print(f"Conflict Report  ({len(summary.conflict_report.entries)} claim shape(s))")
        print(_hr())
        for entry in summary.conflict_report.entries:
            _print_claim_shape_entry(entry)
        if summary.conflict_report.potential_merge_candidates:
            print("\n  Potential merge candidates:")
            for pmc in summary.conflict_report.potential_merge_candidates:
                print(
                    f"    asset_id={pmc.asset_ids[0]} <-> asset_id={pmc.asset_ids[1]}  "
                    f"({len(pmc.transaction_ids)} transaction(s))"
                )

    if summary.potential_duplicate_clusters:
        print(f"\n{_hr()}")
        print(f"Potential Duplicates  ({len(summary.potential_duplicate_clusters)} cluster(s))")
        print(_hr())
        for cluster in summary.potential_duplicate_clusters:
            print(
                f"  canonical_symbol={cluster.canonical_symbol}  raw_symbols={list(cluster.raw_symbols)}  "
                f"({len(cluster.transaction_ids)} transaction(s))"
            )

    print(f"\n{_hr()}")
    print(f"Coverage Report  ({len(summary.coverage_report.rows)} claim shape(s))")
    print(_hr())
    print(f"  {'Symbol':<16}{'Canonical':<16}{'Currency':<10}{'Verdict':<12}{'Txns':<6}Portfolios")
    for row in sorted(summary.coverage_report.rows, key=lambda r: r.shape.raw_symbol):
        print(
            f"  {row.shape.raw_symbol:<16}{(row.shape.canonical_symbol or '—'):<16}"
            f"{(row.shape.currency or '—'):<10}{row.verdict.value:<12}{row.transaction_count:<6}"
            f"{list(row.portfolio_ids)}"
        )
    print("\n  By currency:")
    for currency, breakdown in summary.coverage_report.by_currency:
        print(
            f"    {currency:<10} resolved={breakdown.resolved} candidate={breakdown.candidate} "
            f"ambiguous={breakdown.ambiguous} conflict={breakdown.conflict} unknown={breakdown.unknown}"
        )
    print("\n  By provider:")
    for provider, breakdown in summary.coverage_report.by_provider:
        print(
            f"    {provider:<20} resolved={breakdown.resolved} candidate={breakdown.candidate} "
            f"ambiguous={breakdown.ambiguous} conflict={breakdown.conflict} unknown={breakdown.unknown}"
        )

    print(f"\n{_hr()}")
    print("Caveats")
    print(_hr())
    for caveat in s.caveats:
        print(f"  - {caveat}")
    print(_hr())


def _cmd_plan_migration(args: argparse.Namespace) -> int:
    """Read-only Asset Registry migration dry run. Never modifies the
    database. identity_resolver.resolve() does write RegistryFinding rows
    internally for AMBIGUOUS/CONFLICT verdicts (see services/migration_
    planner.py's module docstring) — the "no writes" guarantee here is
    structural: plan_migration() never commits its session and always
    rolls it back before returning, regardless of outcome."""
    db = SessionLocal()
    t_start = time.monotonic()
    try:
        ws = db.query(Workspace).first()
        if ws is None:
            print("ERROR: No workspace found in database.", file=sys.stderr)
            return 1
        ws_id = ws.id

        portfolio_ids: list[int] | None
        if getattr(args, "all", False):
            portfolios = db.query(Portfolio).filter_by(workspace_id=ws_id).all()
            if not portfolios:
                print("ERROR: No portfolios found in workspace.", file=sys.stderr)
                return 1
            portfolio_ids = [p.id for p in portfolios]
        elif getattr(args, "portfolio", None):
            p = db.query(Portfolio).filter_by(id=args.portfolio, workspace_id=ws_id).first()
            if p is None:
                print(f"ERROR: Portfolio {args.portfolio} not found.", file=sys.stderr)
                return 1
            portfolio_ids = [p.id]
        else:
            print("ERROR: Specify --portfolio ID  or  --all", file=sys.stderr)
            return 1

        print(f"\n{_hr()}")
        print("Migration Planner  —  Dry Run")
        print("(read-only — no database mutation; session is rolled back, never committed)")
        print(_hr())

        plan = plan_migration(db, portfolio_ids=portfolio_ids)
        summary = build_migration_report(plan)
        _print_migration_summary(summary)

    except Exception as exc:
        print(f"\nERROR: Unexpected failure — {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    elapsed = time.monotonic() - t_start
    print(f"\n  Completed in {elapsed:.2f}s — DRY RUN, no rows written.")
    return 0


# ══════════════════════════════════════════════════════════════════════════════
# Migration executor: execute_migration
# ══════════════════════════════════════════════════════════════════════════════

def _print_execution_report(report: ExecutionReport) -> None:
    s = report.summary
    print(f"\n{_hr()}")
    print("Execution Report")
    print(_hr())
    print(f"  Run ID                 : {report.run_id}")
    print(f"  Mode                   : {'DRY RUN' if report.dry_run else 'LIVE'}")
    print(f"  Completed              : {s.completed}")
    print(f"  Blocked                : {s.blocked}")
    print(f"  Skipped (not resolved) : {s.skipped_not_resolved}")
    print(f"  Skipped (already done) : {s.skipped_already_done}")
    print(f"  Identifiers attached   : {s.total_identifiers_attached}")

    blocked_steps = [st for st in report.steps if st.outcome == ExecutionOutcome.BLOCKED]
    if blocked_steps:
        print(f"\n{_hr()}")
        print(f"Blocked  ({len(blocked_steps)} claim shape(s))")
        print(_hr())
        for st in blocked_steps:
            print(f"\n  {st.shape.raw_symbol} / {st.shape.canonical_symbol or '—'}   currency={st.shape.currency or '—'}")
            print(f"    resolved_asset_id             : {st.resolved_asset_id}")
            print(f"    identifiers attached (partial): {st.identifiers_attached}")
            print(f"    detail                        : {st.detail}")
    print(_hr())


def _cmd_execute_migration(args: argparse.Namespace) -> int:
    """Executes an approved Asset Registry migration plan (Milestone M5.2).

    Re-computes the MigrationPlan fresh on every invocation (the same
    read-only plan_migration() used by `plan_migration`) so a resumed run
    always sees current Registry/ledger state rather than a stale plan.
    Only RESOLVED claim shapes are ever acted on; AMBIGUOUS/CONFLICT/UNKNOWN
    shapes are always skipped and reported, never auto-resolved.

    Defaults to a dry run (--commit is required to persist changes).
    """
    db = SessionLocal()
    t_start = time.monotonic()
    report: ExecutionReport | None = None
    try:
        ws = db.query(Workspace).first()
        if ws is None:
            print("ERROR: No workspace found in database.", file=sys.stderr)
            return 1
        ws_id = ws.id

        portfolio_ids: list[int] | None
        if getattr(args, "all", False):
            portfolios = db.query(Portfolio).filter_by(workspace_id=ws_id).all()
            if not portfolios:
                print("ERROR: No portfolios found in workspace.", file=sys.stderr)
                return 1
            portfolio_ids = [p.id for p in portfolios]
        elif getattr(args, "portfolio", None):
            p = db.query(Portfolio).filter_by(id=args.portfolio, workspace_id=ws_id).first()
            if p is None:
                print(f"ERROR: Portfolio {args.portfolio} not found.", file=sys.stderr)
                return 1
            portfolio_ids = [p.id]
        else:
            print("ERROR: Specify --portfolio ID  or  --all", file=sys.stderr)
            return 1

        run_id = args.run_id or str(uuid.uuid4())
        dry_run = not getattr(args, "commit", False)
        resuming = bool(args.run_id)

        if not dry_run and not getattr(args, "yes", False):
            action = "Resuming" if resuming else "Starting"
            print(f"\n{action} a LIVE migration execution — run_id={run_id}")
            print("This will attach identifier evidence to the Registry (asset_identifiers).")
            confirm = input("Proceed? [y/N] ").strip().lower()
            if confirm != "y":
                print("Aborted.")
                return 1

        print(f"\n{_hr()}")
        print(f"Migration Executor  —  run_id={run_id}  {'(RESUME)' if resuming else '(NEW RUN)'}  {'(DRY RUN)' if dry_run else '(LIVE)'}")
        print(_hr())

        plan = plan_migration(db, portfolio_ids=portfolio_ids)
        report = execute_migration(db, plan, run_id=run_id, dry_run=dry_run)
        _print_execution_report(report)

    except Exception as exc:
        print(f"\nERROR: Unexpected failure — {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    elapsed = time.monotonic() - t_start
    print(f"\n  Completed in {elapsed:.2f}s.")
    return 1 if report.summary.blocked > 0 else 0


# ══════════════════════════════════════════════════════════════════════════════
# Registry bootstrap: bootstrap_registry
# ══════════════════════════════════════════════════════════════════════════════

def _print_bootstrap_report(report: BootstrapReport) -> None:
    s = report.summary
    print(f"\n{_hr()}")
    print("Bootstrap Report")
    print(_hr())
    print(f"  Run ID                       : {report.run_id}")
    print(f"  Mode                         : {'DRY RUN' if report.dry_run else 'LIVE'}")
    print(f"  Minted                       : {s.minted}")
    print(f"  Blocked                      : {s.blocked}")
    print(f"  Skipped (already done)       : {s.skipped_already_done}")
    print(f"  Identifiers attached         : {s.total_identifiers_attached}")
    print(f"  Duplicate clusters (blocked) : {s.duplicate_blocked_clusters}")
    print(f"  Quarantined (no convention)  : {s.quarantined}")

    blocked_steps = [st for st in report.steps if st.outcome == BootstrapOutcome.BLOCKED]
    if blocked_steps:
        print(f"\n{_hr()}")
        print(f"Blocked  ({len(blocked_steps)} claim shape(s))")
        print(_hr())
        for st in blocked_steps:
            print(f"\n  {st.shape.raw_symbol} / {st.shape.canonical_symbol or '—'}   currency={st.shape.currency or '—'}")
            print(f"    detail : {st.detail}")

    if report.duplicate_blocked:
        print(f"\n{_hr()}")
        print(f"Duplicate Clusters — Manual Resolution Required  ({len(report.duplicate_blocked)} cluster(s))")
        print(_hr())
        for cluster in report.duplicate_blocked:
            print(
                f"  canonical_symbol={cluster.canonical_symbol}  raw_symbols={list(cluster.raw_symbols)}  "
                f"({len(cluster.transaction_ids)} transaction(s))"
            )
        print("\n  Resolve by hand via registry_service.mint_asset()/attach_identifier() — never auto-resolved.")

    if report.quarantined:
        print(f"\n{_hr()}")
        print(f"Quarantined — No Market/Exchange Convention  ({len(report.quarantined)} shape(s))")
        print(_hr())
        for q in report.quarantined:
            print(f"  {q.shape.raw_symbol:<16} currency={q.shape.currency or '—':<6} reason={q.reason}")

    print(_hr())


def _cmd_bootstrap_registry(args: argparse.Namespace) -> int:
    """Populates the empty Asset Registry from UNKNOWN ledger claims
    (Milestone M5.3). Consumes a freshly-computed BootstrapPlan (services.
    bootstrap_planner, unmodified) and mints exactly its `mintable`
    candidates via registry_service.mint_asset(). Duplicate-cluster and
    quarantined shapes are never auto-resolved — they are reported for
    manual review.

    Re-computes the MigrationPlan and BootstrapPlan fresh on every
    invocation, so a resumed run always sees current Registry/ledger state.

    Defaults to a dry run (--commit is required to persist changes).
    """
    db = SessionLocal()
    t_start = time.monotonic()
    report: BootstrapReport | None = None
    try:
        ws = db.query(Workspace).first()
        if ws is None:
            print("ERROR: No workspace found in database.", file=sys.stderr)
            return 1
        ws_id = ws.id

        portfolio_ids: list[int] | None
        if getattr(args, "all", False):
            portfolios = db.query(Portfolio).filter_by(workspace_id=ws_id).all()
            if not portfolios:
                print("ERROR: No portfolios found in workspace.", file=sys.stderr)
                return 1
            portfolio_ids = [p.id for p in portfolios]
        elif getattr(args, "portfolio", None):
            p = db.query(Portfolio).filter_by(id=args.portfolio, workspace_id=ws_id).first()
            if p is None:
                print(f"ERROR: Portfolio {args.portfolio} not found.", file=sys.stderr)
                return 1
            portfolio_ids = [p.id]
        else:
            print("ERROR: Specify --portfolio ID  or  --all", file=sys.stderr)
            return 1

        run_id = args.run_id or str(uuid.uuid4())
        dry_run = not getattr(args, "commit", False)
        resuming = bool(args.run_id)

        if not dry_run and not getattr(args, "yes", False):
            action = "Resuming" if resuming else "Starting"
            print(f"\n{action} a LIVE registry bootstrap — run_id={run_id}")
            print("This will mint new Assets and attach identifier evidence to the Registry.")
            confirm = input("Proceed? [y/N] ").strip().lower()
            if confirm != "y":
                print("Aborted.")
                return 1

        print(f"\n{_hr()}")
        print(f"Registry Bootstrap  —  run_id={run_id}  {'(RESUME)' if resuming else '(NEW RUN)'}  {'(DRY RUN)' if dry_run else '(LIVE)'}")
        print(_hr())

        plan = plan_migration(db, portfolio_ids=portfolio_ids)
        bootstrap_plan = build_bootstrap_plan(plan)
        report = bootstrap_registry(db, bootstrap_plan, run_id=run_id, dry_run=dry_run)
        _print_bootstrap_report(report)

    except Exception as exc:
        print(f"\nERROR: Unexpected failure — {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    elapsed = time.monotonic() - t_start
    print(f"\n  Completed in {elapsed:.2f}s.")
    return 1 if report.summary.blocked > 0 else 0


# ══════════════════════════════════════════════════════════════════════════════
# Ledger asset backfill: backfill_asset_ids  (M5 Track B, Stage 2)
# ══════════════════════════════════════════════════════════════════════════════

def _print_backfill_report(report: BackfillReport) -> None:
    print(f"\n{_hr()}")
    print("Backfill Report")
    print(_hr())
    print(f"  Run ID                    : {report.run_id}")
    print(f"  Mode                      : {'DRY RUN' if report.dry_run else 'LIVE'}")
    print(f"  Portfolios scanned        : {list(report.portfolios_scanned)}")
    print(f"  Transactions updated      : {report.transactions_updated}")
    print(f"  Portfolio items updated   : {report.portfolio_items_updated}")
    print(f"  Watchlist rows updated    : {report.watchlist_rows_updated}")
    print(f"  Still unresolved (txns)   : {report.still_unresolved_transaction_count}")

    completed = [s for s in report.steps if s.outcome == BackfillOutcome.COMPLETED]
    if completed:
        print(f"\n{_hr()}")
        print(f"Completed  ({len(completed)} claim shape(s))")
        print(_hr())
        for st in completed:
            print(
                f"  {st.shape.raw_symbol:<16}{(st.shape.canonical_symbol or '—'):<16}"
                f"asset_id={st.resolved_asset_id:<6} "
                f"tx={st.transactions_updated} item={st.portfolio_items_updated} wl={st.watchlist_rows_updated}"
            )

    already_done = [s for s in report.steps if s.outcome == BackfillOutcome.SKIPPED_ALREADY_DONE]
    if already_done:
        print(f"\n{_hr()}")
        print(f"Already done  ({len(already_done)} claim shape(s))")
        print(_hr())
        for st in already_done:
            print(f"  {st.shape.raw_symbol:<16}{(st.shape.canonical_symbol or '—'):<16}asset_id={st.resolved_asset_id}")

    _print_unresolved_section(report)
    print(_hr())


def _print_unresolved_section(report: BackfillReport) -> None:
    """Every unresolved record, reported — never silently dropped."""
    unresolved = unresolved_steps(report)
    if not unresolved:
        return
    print(f"\n{_hr()}")
    print(f"Unresolved — Adjudication Required  ({len(unresolved)} claim shape(s), "
          f"{sum(s.transaction_count for s in unresolved)} transaction(s))")
    print(_hr())
    for st in unresolved:
        print(
            f"  {st.shape.raw_symbol:<16}{(st.shape.canonical_symbol or '—'):<16}"
            f"currency={st.shape.currency or '—':<6} transactions={st.transaction_count:<6} {st.detail}"
        )
    print("\n  Resolve via plan_migration/execute_migration/bootstrap_registry, then re-run backfill_asset_ids.")


def _print_rollback_report(report: RollbackReport) -> None:
    print(f"\n{_hr()}")
    print("Rollback Report")
    print(_hr())
    print(f"  Run ID                    : {report.run_id}")
    print(f"  Mode                      : {'DRY RUN' if report.dry_run else 'LIVE'}")
    print(f"  Claim shapes rolled back  : {report.shapes_rolled_back}")
    print(f"  Transactions reset        : {report.transactions_reset}")
    print(f"  Portfolio items reset     : {report.portfolio_items_reset}")
    print(f"  Watchlist rows reset      : {report.watchlist_rows_reset}")
    print(_hr())


def _cmd_backfill_asset_ids(args: argparse.Namespace) -> int:
    """Writes RESOLVED Asset Registry verdicts onto Transaction/PortfolioItem/
    Watchlist.asset_id (M5 Track B, Stage 2). Never resolves anything itself —
    consumes a freshly-computed MigrationPlan (services.migration_planner,
    unmodified) exactly like execute_migration/bootstrap_registry do.

    Nothing reads asset_id yet (Stage 5 native cutover); this command is
    inert with respect to replay, analytics, and every other consumer.

    Defaults to a dry run (--commit is required to persist changes).
    --unresolved-report prints only the adjudication backlog (always
    read-only, regardless of --commit). --rollback RUN_ID reverses a prior
    live run's writes precisely (only rows that run actually changed).
    """
    db = SessionLocal()
    t_start = time.monotonic()
    try:
        ws = db.query(Workspace).first()
        if ws is None:
            print("ERROR: No workspace found in database.", file=sys.stderr)
            return 1
        ws_id = ws.id

        if getattr(args, "rollback", None):
            dry_run = not getattr(args, "commit", False)
            if not dry_run and not getattr(args, "yes", False):
                print(f"\nRolling back backfill run_id={args.rollback} — this resets asset_id "
                      f"back to NULL for exactly the rows that run wrote.")
                confirm = input("Proceed? [y/N] ").strip().lower()
                if confirm != "y":
                    print("Aborted.")
                    return 1
            print(f"\n{_hr()}")
            print(f"Backfill Rollback  —  run_id={args.rollback}  {'(DRY RUN)' if dry_run else '(LIVE)'}")
            print(_hr())
            rb_report = rollback_backfill(db, args.rollback, dry_run=dry_run)
            _print_rollback_report(rb_report)
            elapsed = time.monotonic() - t_start
            print(f"\n  Completed in {elapsed:.2f}s.")
            return 0

        portfolio_ids: list[int] | None
        if getattr(args, "all", False):
            portfolios = db.query(Portfolio).filter_by(workspace_id=ws_id).all()
            if not portfolios:
                print("ERROR: No portfolios found in workspace.", file=sys.stderr)
                return 1
            portfolio_ids = [p.id for p in portfolios]
        elif getattr(args, "portfolio", None):
            p = db.query(Portfolio).filter_by(id=args.portfolio, workspace_id=ws_id).first()
            if p is None:
                print(f"ERROR: Portfolio {args.portfolio} not found.", file=sys.stderr)
                return 1
            portfolio_ids = [p.id]
        else:
            print("ERROR: Specify --portfolio ID  or  --all", file=sys.stderr)
            return 1

        unresolved_only = getattr(args, "unresolved_report", False)
        dry_run = True if unresolved_only else not getattr(args, "commit", False)
        run_id = args.run_id or str(uuid.uuid4())
        resuming = bool(args.run_id)

        if not dry_run and not getattr(args, "yes", False):
            action = "Resuming" if resuming else "Starting"
            print(f"\n{action} a LIVE ledger asset backfill — run_id={run_id}")
            print("This will write asset_id onto Transaction/PortfolioItem/Watchlist rows.")
            print("Nothing reads this column yet (Stage 5 native cutover) — this write is inert.")
            confirm = input("Proceed? [y/N] ").strip().lower()
            if confirm != "y":
                print("Aborted.")
                return 1

        label = "Unresolved Assets Report" if unresolved_only else "Ledger Asset Backfill"
        print(f"\n{_hr()}")
        print(f"{label}  —  run_id={run_id}  {'(RESUME)' if resuming else '(NEW RUN)'}  "
              f"{'(DRY RUN)' if dry_run else '(LIVE)'}")
        print(_hr())

        plan = plan_migration(db, portfolio_ids=portfolio_ids)
        report = backfill_ledger_asset_ids(db, plan, portfolio_ids=portfolio_ids, run_id=run_id, dry_run=dry_run)

        if unresolved_only:
            _print_unresolved_section(report)
            print(_hr())
        else:
            _print_backfill_report(report)

    except Exception as exc:
        print(f"\nERROR: Unexpected failure — {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    elapsed = time.monotonic() - t_start
    print(f"\n  Completed in {elapsed:.2f}s.")
    return 1 if unresolved_steps(report) else 0


# ══════════════════════════════════════════════════════════════════════════════
# Apply repairs: apply_repair
# ══════════════════════════════════════════════════════════════════════════════

def _print_apply_repair_preview(plan: RepairPlan, portfolio_id: int) -> None:
    """Print plan details before any write."""
    print(f"\n{_hr()}")
    print(f"Repair Plan Preview  —  Portfolio {portfolio_id}")
    print(_hr())
    print(f"  Plan ID           : {plan.repair_plan_id}")
    print(f"  Generated at      : {plan.generated_at or 'n/a'}")
    print(f"  Portfolio ID      : {plan.portfolio_id}")
    print(f"  Operations        : {len(plan.operations)}")
    if plan.operations:
        print()
        print(f"  {'#':<4}  {'Type':<18}  {'TX ID':<8}  Reason")
        print(f"  {'-'*4}  {'-'*18}  {'-'*8}  {'-'*38}")
        for i, op in enumerate(plan.operations, 1):
            tx_str = str(op.transaction_id) if op.transaction_id is not None else "—"
            reason = (op.reason[:38] + "…") if len(op.reason) > 39 else op.reason
            print(f"  {i:<4}  {op.repair_type:<18}  {tx_str:<8}  {reason}")
    print(_hr())


def _print_apply_repair_result(r: RepairApplyResult) -> None:
    """Print the outcome of apply_repair_plan()."""
    print(f"\n{_hr()}")
    print(f"Apply Repair Result  —  Portfolio {r.portfolio_id}")
    print(_hr())

    if r.error:
        print(f"  ERROR: {r.error}")
        return

    print(f"  Plan ID                : {r.repair_plan_id}")
    print()
    print("  Operations")
    print(f"    Requested            : {r.operations_requested}")
    print(f"    Inserted             : {r.operations_inserted}")
    print(f"    Already active       : {r.already_active}")
    if r.skipped:
        print(f"    Skipped              : {r.skipped}")
    if r.rollback:
        print(f"    Rollback             : YES — {r.rollback_reason}")

    if r.backup_path:
        print()
        print(f"  Backup               : {r.backup_path}")

    if r.effective_before is not None:
        print()
        print("  Effective Validator")
        n_before = len(r.effective_before.findings)
        n_after  = len(r.effective_after.findings) if r.effective_after else n_before
        crit_b   = len(r.effective_before.criticals)
        crit_a   = len(r.effective_after.criticals) if r.effective_after else crit_b
        print(f"    Findings before      : {n_before}  (critical={crit_b})")
        print(f"    Findings after       : {n_after}  (critical={crit_a})")
        print()
        print(f"  Confidence before    : {r.confidence_before:.1f}%")
        print(f"  Confidence after     : {r.confidence_after:.1f}%")
        if r.dry_run and not r.rollback:
            print()
            print(
                "  NOTE: 'after' is a preview computed from an uncommitted overlay "
                "and was rolled back. validate_ledger --effective will still show "
                "the pre-repair findings until you re-run apply_repair without "
                "--dry-run."
            )

    print()
    if r.rollback:
        print("  ROLLED BACK — no database changes written")
    elif r.dry_run:
        print("  DRY RUN — no database changes written")
    elif r.operations_inserted == 0 and r.already_active == r.operations_requested:
        print("  NO-OP — all operations were already active (plan already applied)")
    else:
        print(f"  COMMITTED — {r.operations_inserted} repair(s) written")
        if r.inserted_repair_ids:
            ids_str = ", ".join(str(i) for i in r.inserted_repair_ids)
            print(f"  Repair IDs           : {ids_str}")

    print(_hr())


async def _cmd_apply_repair(args: argparse.Namespace) -> int:
    """Write LedgerRepair rows from a validated repair plan JSON.

    Transaction rows are never modified.
    """
    dry_run: bool = getattr(args, "dry_run", False)
    yes:     bool = getattr(args, "yes", False)
    force:   bool = getattr(args, "force", False)

    # ── Load and validate plan ────────────────────────────────────────────────
    plan_path: str = args.plan
    try:
        plan = load_repair_plan(plan_path)
    except RepairPlanError as exc:
        print(f"\nERROR: Invalid repair plan — {exc}", file=sys.stderr)
        return 1

    portfolio_id: int = args.portfolio

    # ── Preview ───────────────────────────────────────────────────────────────
    _print_apply_repair_preview(plan, portfolio_id)

    # ── Confirmation ──────────────────────────────────────────────────────────
    if not dry_run:
        if not yes:
            print("\nThis will insert LedgerRepair rows.  Transaction rows are NOT modified.")
            if not _confirm():
                print("\nApply cancelled.")
                return 3
    else:
        print(f"\n{_hr()}")
        print("DRY RUN — no database changes will be written")
        print(_hr())

    # ── Run ───────────────────────────────────────────────────────────────────
    db = SessionLocal()
    try:
        ws = db.query(Workspace).first()
        if ws is None:
            print("ERROR: No workspace found in database.", file=sys.stderr)
            return 1
        ws_id = ws.id

        result = await apply_repair_plan(
            db           = db,
            plan         = plan,
            portfolio_id = portfolio_id,
            workspace_id = ws_id,
            dry_run      = dry_run,
            force        = force,
        )
    except Exception as exc:
        print(f"\nERROR: Unexpected failure — {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    _print_apply_repair_result(result)

    if result.error:
        return 1
    if result.rollback:
        return 2
    return 0


# ══════════════════════════════════════════════════════════════════════════════
# Generate repair plans: generate_repair_plan
# ══════════════════════════════════════════════════════════════════════════════

def _print_generation_summary(summary: GenerationSummary) -> None:
    """Print the console report described in the Phase 6.7E spec."""
    print(f"\n{_hr()}")
    print(f"Portfolio: {summary.portfolio_id}")
    print(_hr())

    print("\nFindings:")
    if summary.findings_by_severity:
        for sev in ("CRITICAL", "ERROR", "WARNING"):
            n = summary.findings_by_severity.get(sev, 0)
            if n:
                print(f"    {sev:<9}: {n}")
    else:
        print("    (none)")

    print("\nGenerated repairs:")
    if summary.generated_by_type:
        for repair_type, n in sorted(summary.generated_by_type.items()):
            print(f"    {repair_type:<9}: {n}")
    else:
        print("    (none)")

    if summary.already_active:
        print(f"\nAlready active (skipped): {summary.already_active}")

    print("\nSkipped:")
    if summary.skipped_by_check_id:
        for check_id, n in sorted(summary.skipped_by_check_id.items()):
            print(f"    {check_id:<22}: {n}")
    else:
        print("    (none)")


async def _cmd_generate_repair_plan(args: argparse.Namespace) -> int:
    """Generate a deterministic repair plan JSON from validator findings.

    Read-only — never modifies the database. Only writes the output JSON file.
    """
    portfolio_id: int = args.portfolio
    output_path:  str = args.output or f"repair_plan_{portfolio_id}.json"
    do_effective: bool = getattr(args, "effective", False)

    db = SessionLocal()
    try:
        ws = db.query(Workspace).first()
        if ws is None:
            print("ERROR: No workspace found in database.", file=sys.stderr)
            return 1
        ws_id = ws.id

        p = db.query(Portfolio).filter_by(id=portfolio_id, workspace_id=ws_id).first()
        if p is None:
            print(f"ERROR: Portfolio {portfolio_id} not found.", file=sys.stderr)
            return 1

        active_repairs = load_active_repairs(db, portfolio_id)

        if do_effective:
            report = await validate_portfolio_ledger(
                db           = db,
                portfolio_id = portfolio_id,
                workspace_id = ws_id,
                repairs      = active_repairs,
                mode         = "effective",
            )
        else:
            report = await validate_portfolio_ledger(
                db           = db,
                portfolio_id = portfolio_id,
                workspace_id = ws_id,
            )

        plan, summary = generate_repair_plan(
            report         = report,
            portfolio_id   = portfolio_id,
            active_repairs = active_repairs,
        )
    except Exception as exc:
        print(f"\nERROR: Unexpected failure — {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    _print_generation_summary(summary)

    if plan is None:
        print("\nNo repairable findings — nothing to write.")
        return 2

    write_repair_plan(plan, output_path)
    print(f"\nOutput: {output_path}")
    return 0


# ── Argument parser ────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Portfolio Intelligence Platform — management commands",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── repair_snapshots ──────────────────────────────────────────────────────
    repair = sub.add_parser(
        "repair_snapshots",
        help="Repair corrupted portfolio snapshots",
        description=textwrap.dedent("""\
            Identifies and repairs snapshots corrupted by the avg_cost price
            fallback bug (pre-Phase-1 fix).

            Repair always goes through the production generate_daily_snapshot()
            pipeline with historical closing prices injected via yfinance.
            Original snapshots are preserved if coverage < 90%%.
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    repair.add_argument(
        "--portfolio", "-p",
        type=int,
        metavar="ID",
        help="Portfolio ID to repair",
    )
    repair.add_argument(
        "--date", "-d",
        metavar="YYYY-MM-DD",
        help="Repair a single snapshot date",
    )
    repair.add_argument(
        "--from-date",
        metavar="YYYY-MM-DD",
        help="Start of date range to repair (inclusive)",
    )
    repair.add_argument(
        "--to-date",
        metavar="YYYY-MM-DD",
        help="End of date range to repair (inclusive)",
    )
    repair.add_argument(
        "--all",
        action="store_true",
        help="Process all portfolios in the workspace",
    )
    repair.add_argument(
        "--scan-corrupted",
        action="store_true",
        help="Auto-detect corrupted snapshots before repairing",
    )
    repair.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate without writing to the database",
    )
    repair.add_argument(
        "--debug",
        action="store_true",
        help=(
            "Print detailed return-recovery trace for single-date repair "
            "(shows attribution window, per-transaction inclusion, and "
            "stored vs recalculated return fields). "
            "Only active with --portfolio + --date."
        ),
    )

    # ── verify_snapshots ──────────────────────────────────────────────────────
    verify = sub.add_parser(
        "verify_snapshots",
        help="Audit snapshot integrity (read-only — never modifies the database)",
        description=textwrap.dedent("""\
            Read-only integrity audit for historical portfolio snapshots.

            Checks performed:
              1. NAV continuity      — flags large day-over-day NAV jumps
              2. Unrealized P/L      — flags large P/L discontinuities
              3. Holdings integrity  — verifies holdings_count, total_invested,
                                       total_value, unrealized_pnl against
                                       computed values from holdings_json
              4. Price integrity     — detects null/zero prices, missing prices,
                                       negative market_value, duplicate symbols
              5. Return sanity       — flags impossible daily return values

            Exit codes:
              0  No anomalies detected
              1  Warnings detected
              2  Critical integrity failures detected
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    verify.add_argument(
        "--portfolio", "-p",
        type=int,
        metavar="ID",
        help="Portfolio ID to audit",
    )
    verify.add_argument(
        "--all",
        action="store_true",
        help="Audit all portfolios in the workspace",
    )
    verify.add_argument(
        "--nav-threshold",
        type=float,
        default=15.0,
        metavar="PCT",
        help=(
            "Flag daily NAV changes larger than this percentage "
            "(default: 15.0)"
        ),
    )

    # ── recalculate_snapshot_returns ──────────────────────────────────────────
    recalc = sub.add_parser(
        "recalculate_snapshot_returns",
        help="Recalculate return fields for historical snapshots from stored NAV + transactions",
        description=textwrap.dedent("""\
            Recomputes return-attribution fields for every snapshot in a portfolio
            without fetching live market prices or rebuilding holdings.

            NAV data (total_value, holdings_json, unrealized_pnl, etc.) is treated
            as authoritative and is never modified.

            Fields recalculated:
              investment_return_pct    daily_return_pct
              investment_return_amount net_external_cash_flow
              imported_asset_value     manual_adjustment_value
              period_realized_pnl      period_dividend_income
              period_fees_paid

            Window detection uses Transaction.created_at (physical insert time),
            NOT transaction_date -- matching the live snapshot pipeline exactly.
            Bookkeeping transactions (INITIAL_CASH, INITIAL_POSITION) created on
            the same day as the baseline snapshot are automatically excluded from
            subsequent periods because they fall before the window boundary.

            All writes run inside a single database transaction; rolled back on
            any failure.
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    recalc.add_argument(
        "--portfolio", "-p",
        type=int,
        metavar="ID",
        help="Portfolio ID to process",
    )
    recalc.add_argument(
        "--all",
        action="store_true",
        help="Process all portfolios in the workspace",
    )
    recalc.add_argument(
        "--dry-run",
        action="store_true",
        help="Print old -> new values without writing to the database",
    )

    # ── backfill_recommendation_grades ────────────────────────────────────────
    backfill_grades = sub.add_parser(
        "backfill_recommendation_grades",
        help="Backfill recommendation shadows + mature horizon grades (AI Evaluation M1)",
        description=textwrap.dedent("""\
            One-shot backfill so the AI Evaluation phase does not launch empty
            for existing users.

            For every existing RecommendationSnapshot lacking a
            recommendation-keyed shadow (P2), creates one and replays its full
            historical daily valuation from stored portfolio snapshot prices.
            Then writes any due EXPIRED decisions (P4), grades every horizon
            (7/30/90/180 days by default) that has matured (P3), and grades
            the day-0 PLAN composite (M2 — no maturity wait required).

            Idempotent -- safe to re-run; already-backfilled snapshots and
            already-graded horizons/plans are skipped.
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    backfill_grades.add_argument(
        "--portfolio", "-p",
        type=int,
        metavar="ID",
        help="Portfolio ID to backfill",
    )
    backfill_grades.add_argument(
        "--all",
        action="store_true",
        help="Backfill all portfolios in the workspace",
    )

    # ── regenerate_paper_portfolios ───────────────────────────────────────────
    regen = sub.add_parser(
        "regenerate_paper_portfolios",
        help="Regenerate paper-portfolio history through the corrected accounting engine (Accounting Correctness Milestone 2)",
        description=textwrap.dedent("""\
            Re-derives ShadowPortfolio.paper_cash_balance/inception_holdings_json
            and ShadowPortfolioSnapshot rows for every existing shadow through
            the Milestone 1 cash-leak fix, then refreshes each portfolio's
            AttributionMetric row (idempotent per-day upsert).

            Only derived tables are touched: ShadowPortfolio,
            ShadowPortfolioSnapshot, AttributionMetric. RecommendationSnapshot,
            PortfolioSnapshot, PortfolioItem, Transaction, and
            UserExecutionDecision are never written.

            Defaults to a dry run (computes and validates everything, including
            per-day NAV invariant checks, then rolls back). Pass --commit to
            persist. Pass --backup with --commit to export affected rows to
            JSON first (backup failure aborts the commit).
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    regen.add_argument("--portfolio", "-p", type=int, metavar="ID", help="Portfolio ID to regenerate")
    regen.add_argument("--all", action="store_true", help="Regenerate all portfolios in the workspace")
    regen.add_argument("--commit", action="store_true", help="Persist changes (default is dry run)")
    regen.add_argument("--backup", action="store_true", help="Export affected rows to JSON before committing")
    regen.add_argument("--yes", action="store_true", help="Skip the confirmation prompt before committing")

    # ── rebuild_portfolio ─────────────────────────────────────────────────────
    rebuild = sub.add_parser(
        "rebuild_portfolio",
        help="Deterministic portfolio reconstruction from the transaction ledger",
        description=textwrap.dedent("""\
            Rebuilds a portfolio from scratch using only the Transaction table
            as the Source of Truth.

            Pipeline
            --------
              Stage 1  Replay every transaction chronologically
                       → Portfolio.cash_balance
                       → PortfolioItem (shares, avg_cost, sector)
                       → Cumulative realized P&L

              Stage 2  Reconstruct historical portfolio state at each
                       existing snapshot date using replayed transactions
                       → Historical prices fetched from yfinance
                       → holdings_json, equity_value, sector_breakdown

              Stage 3  Recalculate all derived return fields
                       → investment_return_pct, daily_return_pct
                       → net_external_cash_flow, period_realized_pnl, …

              Stage 4  Reconciliation report (MATCH / DIFFERENT / MISSING / EXTRA)
                       → Never writes automatically if validation shows drift

              Stage 5  Ledger validation gate (runs validate_ledger rules)
                       → CRITICAL finding → abort; commit is blocked
                       → Multi-dimensional ConfidenceReport computed

              Stage 6  Execution plan (deterministic, read-only)
                       → Lists every intended DB change before any write
                       → Use --plan to display; --plan-json to export as JSON

              Stage 7  Pre-commit backup (--backup only)
                       → Existing rows exported to JSON before any writes
                       → Backup failure aborts the commit

              Stage 8  Atomic commit (single DB transaction; rollback on failure)

            Use --all to process every portfolio in the workspace.
            Use --dry-run to preview without writing.
            Use --from-date to rebuild only snapshots on/after a given date
            (Stage 1 always replays ALL transactions regardless of this flag).
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    rebuild.add_argument(
        "--portfolio", "-p",
        type=int,
        metavar="ID",
        help="Portfolio ID to rebuild",
    )
    rebuild.add_argument(
        "--all",
        action="store_true",
        help="Rebuild all portfolios in the workspace",
    )
    rebuild.add_argument(
        "--from-date",
        metavar="YYYY-MM-DD",
        help=(
            "Rebuild snapshots on/after this date only.  "
            "Stage 1 (transaction replay → current holdings) always uses the full ledger."
        ),
    )
    rebuild.add_argument(
        "--skip-snapshots",
        action="store_true",
        help="Skip Stages 2-3 (only rebuild portfolio items and cash balance)",
    )
    rebuild.add_argument(
        "--skip-benchmark",
        action="store_true",
        help="(reserved) Skip benchmark series regeneration",
    )
    rebuild.add_argument(
        "--dry-run",
        action="store_true",
        help="Run all stages but do not write to the database",
    )
    rebuild.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip confirmation prompt (for automation / scripting)",
    )
    rebuild.add_argument(
        "--backup",
        action="store_true",
        help=(
            "Export existing PortfolioItem and PortfolioSnapshot rows to a JSON "
            "backup file before committing (Stage 6).  No-op with --dry-run."
        ),
    )
    rebuild.add_argument(
        "--commit",
        action="store_true",
        help="Explicit opt-in to write to the database (equivalent to omitting --dry-run).",
    )
    rebuild.add_argument(
        "--plan",
        action="store_true",
        help=(
            "Generate and print the execution plan without writing to the database. "
            "Equivalent to --dry-run with explicit plan display. "
            "Shows every intended DB change: table, operation, field, current→new value."
        ),
    )
    rebuild.add_argument(
        "--plan-json",
        metavar="PATH",
        default=None,
        help=(
            "Generate the execution plan and write it as JSON to PATH. "
            "No database writes. Useful for CI, auditing, and approval workflows. "
            "With --all, appends _{portfolio_id} before the extension for each portfolio."
        ),
    )
    rebuild.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print per-field reconciliation detail",
    )

    # ── delete_portfolio ──────────────────────────────────────────────────────
    delete = sub.add_parser(
        "delete_portfolio",
        help="Permanently delete a portfolio and all its related records",
        description=textwrap.dedent("""\
            Deletes a portfolio and every record associated with it:

              Portfolio Items, Transactions, Snapshots, Optimizer History,
              Recommendation Snapshots, Execution Decisions, Shadow Portfolios,
              Shadow Snapshots, Attribution Metrics.

            All deletes run inside a single database transaction.
            If any step fails, everything is rolled back automatically.
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    delete.add_argument(
        "--id",
        type=int,
        required=True,
        metavar="ID",
        help="Portfolio ID to delete",
    )
    delete.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip confirmation prompt (for automation / scripting)",
    )

    # ── validate_ledger ───────────────────────────────────────────────────────
    validate = sub.add_parser(
        "validate_ledger",
        help="Read-only audit of a portfolio's transaction ledger",
        description=textwrap.dedent("""\
            Inspects the transaction ledger and reports anomalies.

            NEVER modifies the database.
            NEVER influences replay behaviour.
            Replay trusts the ledger completely — validation is a separate concern.

            Checks performed
            ----------------
              Structural (no replay needed):
                DUP_INITIAL_POSITION  — same symbol + date imported more than once
                SYMBOL_ALIAS          — multiple raw symbols resolve to same ticker
                NULL_SYMBOL           — equity transaction with no symbol
                ZERO_SHARES           — equity transaction with zero/null shares
                ZERO_PRICE            — BUY/IMPORT with zero/null price (corrupts avg_cost)
                PRE_PORTFOLIO_TX      — transaction_date before portfolio creation
                LARGE_DATE_SKEW       — large gap between created_at and transaction_date
                DUP_TX_FINGERPRINT    — duplicate (type, symbol, shares, price, date)

              Replay-based:
                SELL_WITHOUT_HOLDING  — SELL on symbol not yet held
                NEG_SHARE_BALANCE     — SELL/QCORR drives shares negative
                NEG_CASH_BALANCE      — BUY drives cash negative
                QCORR_WITHOUT_HOLDING — QUANTITY_CORRECTION on absent symbol

              DB consistency:
                CASH_MISMATCH         — replayed cash ≠ Portfolio.cash_balance
                HOLDINGS_MISMATCH     — replayed holdings ≠ PortfolioItem rows
                SNAPSHOT_CASH_MISMATCH— replayed cash at snapshot date ≠ stored

              Price-gated (--price-check only):
                IMPOSSIBLE_PRICE      — recorded price deviates > threshold from market

            Severity levels
            ---------------
              WARNING   suspicious; may or may not be a real problem
              ERROR     likely corruption; incorrect replay results expected
              CRITICAL  definite corruption; action required

            Exit codes
            ----------
              0  clean — no findings
              1  findings present (warnings or errors)
              2  at least one CRITICAL finding
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    validate.add_argument(
        "--portfolio", "-p",
        type=int,
        metavar="ID",
        help="Portfolio ID to validate",
    )
    validate.add_argument(
        "--all",
        action="store_true",
        help="Validate all portfolios in the workspace",
    )
    validate.add_argument(
        "--price-check",
        action="store_true",
        help=(
            "Enable the IMPOSSIBLE_PRICE check (contacts yfinance — may be slow). "
            "Skipped by default."
        ),
    )
    validate.add_argument(
        "--price-threshold",
        type=float,
        default=100.0,
        metavar="PCT",
        help=(
            "Flag recorded prices that deviate more than this %% from the "
            "yfinance market price (default: 100.0)"
        ),
    )
    validate.add_argument(
        "--effective",
        action="store_true",
        help=(
            "Load active LedgerRepair rows and validate the effective ledger "
            "(repair overlay applied before running all checks). "
            "EXCLUDE repairs remove transactions; SUPPRESS_FINDING repairs "
            "suppress matching findings.  Read-only — no DB writes."
        ),
    )
    validate.add_argument(
        "--compare",
        action="store_true",
        help=(
            "Show a side-by-side comparison of raw vs effective validation: "
            "resolved findings (fixed by repairs), remaining findings (still "
            "present), and newly-introduced findings (should be zero). "
            "Read-only — no rebuild, no replay changes, no DB writes."
        ),
    )

    # ── golden_baseline ─────────────────────────────────────────────────────────
    baseline = sub.add_parser(
        "golden_baseline",
        help="Golden Baseline capture and replay-determinism verification (M5 Track B Stage 1)",
        description=textwrap.dedent("""\
            Golden Baseline Capture — M5 Track B Stage 1.

            Read-only. Every replay is dry_run=True; nothing is ever written
            to the database. Reference:
            docs/implementation/M5_TRACK_B_NATIVE_INTEGRATION_TDD.md §7 Stage 1.

            Actions
            -------
              (default)         Replay each portfolio twice and prove the two
                                 replays are bit-identical (holdings, cash, NAV,
                                 and validator findings). Prints a regression
                                 report: portfolio count, replay parity,
                                 validator parity, baseline hash.

              --capture          Capture a golden baseline for each portfolio
                                 and save it to --baseline-dir as JSON
                                 (portfolio_<id>.json). This becomes the fixed
                                 parity reference for later migration stages.

              --compare-stored    Load a previously captured baseline and
                                 compare it against a fresh replay right now.
                                 Requires --capture to have been run first.

            Exit codes
            ----------
              0  no diffs found (deterministic replay, matches stored baseline)
              1  a diff was found, or a requested stored baseline is missing
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    baseline.add_argument("--portfolio", "-p", type=int, metavar="ID", help="Portfolio ID")
    baseline.add_argument("--all", action="store_true", help="All portfolios in the workspace")
    baseline.add_argument(
        "--capture", action="store_true",
        help="Capture and save a golden baseline for each selected portfolio.",
    )
    baseline.add_argument(
        "--compare-stored", action="store_true",
        help="Compare a freshly-run replay against the previously saved baseline.",
    )
    baseline.add_argument(
        "--baseline-dir", default="golden_baselines", metavar="DIR",
        help="Directory for baseline JSON storage (default: golden_baselines)",
    )
    baseline.add_argument(
        "--skip-snapshots", action="store_true",
        help="Skip NAV/snapshot replay (faster; omits snapshot truth from the baseline).",
    )

    # ── apply_repair ──────────────────────────────────────────────────────────
    apply = sub.add_parser(
        "apply_repair",
        help="Apply a repair plan — writes LedgerRepair rows only",
        description=textwrap.dedent("""\
            Apply a validated repair plan JSON to the portfolio.

            Writes LedgerRepair rows only.  The Transaction table is never
            modified.  All inserts run in a single database transaction;
            rolled back automatically if new CRITICAL validator findings appear
            after insertion (unless --force is given).

            Supported repair types (Phase 6.7D)
            ------------------------------------
              EXCLUDE           — remove transaction from effective canonical list
              SUPPRESS_FINDING  — suppress a specific validator finding

            Rejected repair types (deferred to Phase 6.8)
            -----------------------------------------------
              SYMBOL_RENAME / IMPORT_CORRECTION / LEDGER_EXCEPTION

            Idempotency
            -----------
            Applying the same plan twice is safe.  Operations that already have
            an active row with the same (portfolio_id, repair_plan_id,
            transaction_id, repair_type) are counted as "already active" and
            skipped without error.

            Backup
            ------
            The current PortfolioItem + PortfolioSnapshot + LedgerRepair rows
            are exported to a JSON backup file before any insert.

            Exit codes
            ----------
              0  Success (committed or no-op)
              1  Fatal error (invalid plan, backup failure, unexpected exception)
              2  Rolled back (new CRITICAL findings introduced)
              3  Cancelled by user
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    apply.add_argument(
        "--portfolio", "-p",
        type=int,
        required=True,
        metavar="ID",
        help="Portfolio ID to apply the repair plan to",
    )
    apply.add_argument(
        "--plan",
        required=True,
        metavar="PATH",
        help="Path to the repair plan JSON file",
    )
    apply.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Run all stages (backup, idempotency check, validator) but do not "
            "commit any changes to the database"
        ),
    )
    apply.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip the confirmation prompt (for automation / scripting)",
    )
    apply.add_argument(
        "--force",
        action="store_true",
        help=(
            "Commit even when new CRITICAL validator findings appear after "
            "insertion.  USE WITH CAUTION: intended only when you have "
            "verified that the new findings are expected or benign."
        ),
    )

    # ── generate_repair_plan ──────────────────────────────────────────────────
    generate = sub.add_parser(
        "generate_repair_plan",
        help="Generate a deterministic repair plan JSON from validator findings",
        description=textwrap.dedent("""\
            Runs validate_ledger and turns the 100%%-deterministic findings into
            a repair plan JSON suitable for apply_repair.

            Read-only with respect to the database.  Only writes the output
            JSON file — never inserts LedgerRepair rows itself.

            Auto-repaired checks
            ---------------------
              DUP_INITIAL_POSITION  — EXCLUDE every duplicate, keep the earliest
              DUP_TX_FINGERPRINT    — EXCLUDE every duplicate, keep the first

            All other findings (SYMBOL_ALIAS, IMPOSSIBLE_PRICE,
            SELL_WITHOUT_HOLDING, NEG_SHARE_BALANCE, NEG_CASH_BALANCE,
            QCORR_WITHOUT_HOLDING, HOLDINGS_MISMATCH, CASH_MISMATCH,
            SNAPSHOT_CASH_MISMATCH, …) are reported but never auto-repaired —
            they require human review.

            Transactions already covered by an active EXCLUDE repair are
            skipped, so re-running this command is idempotent.

            Workflow
            --------
              validate_ledger -> generate_repair_plan -> human review ->
              apply_repair -> validate_ledger --effective -> rebuild_portfolio

            Exit codes
            ----------
              0  Success — plan written
              1  Unexpected error
              2  No repairable findings — nothing written
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    generate.add_argument(
        "--portfolio", "-p",
        type=int,
        required=True,
        metavar="ID",
        help="Portfolio ID to generate a repair plan for",
    )
    generate.add_argument(
        "--output", "-o",
        metavar="PATH",
        help="Output path for the repair plan JSON (default: repair_plan_<portfolio>.json)",
    )
    generate.add_argument(
        "--effective",
        action="store_true",
        help=(
            "Generate against the effective ledger (active repairs applied "
            "before scanning for findings) instead of the raw ledger."
        ),
    )

    # ── plan_migration ────────────────────────────────────────────────────────
    plan = sub.add_parser(
        "plan_migration",
        help="Read-only Asset Registry migration dry run (Milestone M5.1)",
        description=textwrap.dedent("""\
            Simulates the complete Asset Registry migration for the given
            portfolios without writing a single row.

            NEVER mutates the database. NEVER writes to the Registry. NEVER
            touches the Ledger, Replay, or Snapshots. The session is always
            rolled back, never committed — even though identity_resolver.
            resolve() itself durably records RegistryFinding rows for
            AMBIGUOUS/CONFLICT verdicts, that write never survives this
            command (see services/migration_planner.py).

            Classifies every transaction as RESOLVED / CANDIDATE / AMBIGUOUS /
            CONFLICT / UNKNOWN (or cash-only, reported separately), and
            reports Statistics, an Ambiguity Report, a Conflict Report, a
            Coverage Report, and potential duplicate/merge candidates.

            Answers: "if we migrate today, what exactly would happen?"
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    plan.add_argument(
        "--portfolio", "-p",
        type=int,
        metavar="ID",
        help="Portfolio ID to plan the migration for",
    )
    plan.add_argument(
        "--all",
        action="store_true",
        help="Plan the migration across every portfolio in the workspace",
    )

    # ── execute_migration ────────────────────────────────────────────────────
    execute = sub.add_parser(
        "execute_migration",
        help="Execute an approved Asset Registry migration plan (Milestone M5.2)",
        description=textwrap.dedent("""\
            Consumes a freshly-computed MigrationPlan (services.migration_planner,
            unmodified) and durably attaches identifier evidence to the Registry
            for every RESOLVED claim shape. Never resolves identities, never
            merges assets, never invents mappings — AMBIGUOUS / CONFLICT / UNKNOWN
            claim shapes are always skipped and reported, never auto-resolved.

            Defaults to a dry run (--commit is required to persist changes).
            Every claim shape is checkpointed (MigrationExecutionCheckpoint) as
            it completes or blocks, keyed by --run-id — re-running with the same
            --run-id resumes: already-COMPLETED shapes are skipped, BLOCKED
            shapes are retried, and any newly-RESOLVED shapes (e.g. from
            transactions added since the last run) are picked up. Omit --run-id
            to start a new run; the generated run_id is printed so it can be
            passed to a later --run-id to resume.

            No replay changes. No analytics changes. No optimizer changes.
            Transaction / PortfolioItem / PortfolioSnapshot are never touched —
            only asset_identifiers and migration_execution_checkpoints gain rows.
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    execute.add_argument(
        "--portfolio", "-p",
        type=int,
        metavar="ID",
        help="Portfolio ID to execute the migration for",
    )
    execute.add_argument(
        "--all",
        action="store_true",
        help="Execute the migration across every portfolio in the workspace",
    )
    execute.add_argument(
        "--run-id",
        metavar="UUID",
        help="Resume a specific prior run; omit to start a new run",
    )
    execute.add_argument(
        "--commit",
        action="store_true",
        help="Persist changes to the database (default is a dry run)",
    )
    execute.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip the confirmation prompt when --commit is used",
    )

    # ── bootstrap_registry ───────────────────────────────────────────────────
    bootstrap = sub.add_parser(
        "bootstrap_registry",
        help="Populate the empty Asset Registry from UNKNOWN ledger claims (Milestone M5.3)",
        description=textwrap.dedent("""\
            Consumes a freshly-computed BootstrapPlan (services.bootstrap_planner,
            unmodified over services.migration_planner's MigrationPlan) and mints
            exactly its `mintable` UNKNOWN claim shapes into new canonical Assets
            via registry_service.mint_asset(). This is a one-time bootstrap
            process: it creates canonical Assets, it does not migrate ledger data.

            Duplicate-cluster shapes (two UNKNOWN shapes sharing a canonical_symbol)
            and quarantined shapes (no known market/exchange convention, or no
            currency recorded) are NEVER auto-minted or auto-resolved — both are
            reported for manual review via registry_service.mint_asset()/
            attach_identifier() directly.

            Defaults to a dry run (--commit is required to persist changes).
            Every mint attempt is checkpointed (RegistryBootstrapCheckpoint) as it
            completes or blocks, keyed by --run-id — re-running with the same
            --run-id resumes: already-MINTED shapes are skipped, BLOCKED shapes
            are retried. Omit --run-id to start a new run; the generated run_id is
            printed so it can be passed to a later --run-id to resume.

            No replay changes. No transaction/portfolio changes. No analytics
            changes. Only assets, asset_identifiers, registry_findings, and
            registry_bootstrap_checkpoints gain rows.

            After bootstrapping, re-run `plan_migration` to confirm Resolved
            increased and Unknown decreased for the minted symbols.
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    bootstrap.add_argument(
        "--portfolio", "-p",
        type=int,
        metavar="ID",
        help="Portfolio ID to bootstrap the registry for",
    )
    bootstrap.add_argument(
        "--all",
        action="store_true",
        help="Bootstrap the registry across every portfolio in the workspace",
    )
    bootstrap.add_argument(
        "--run-id",
        metavar="UUID",
        help="Resume a specific prior run; omit to start a new run",
    )
    bootstrap.add_argument(
        "--commit",
        action="store_true",
        help="Persist changes to the database (default is a dry run)",
    )
    bootstrap.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip the confirmation prompt when --commit is used",
    )

    # ── backfill_asset_ids ───────────────────────────────────────────────────
    backfill = sub.add_parser(
        "backfill_asset_ids",
        help="Backfill ledger asset_id columns from resolved Registry identity (M5 Track B Stage 2)",
        description=textwrap.dedent("""\
            Ledger Asset ID Backfill — M5 Track B Stage 2.
            Reference: docs/implementation/M5_TRACK_B_NATIVE_INTEGRATION_TDD.md §7 Stage 2.

            Consumes a freshly-computed MigrationPlan (services.migration_planner,
            unmodified) and writes every RESOLVED claim shape's asset_id onto
            matching Transaction / PortfolioItem / Watchlist rows. Never resolves
            anything itself — AMBIGUOUS/CANDIDATE/CONFLICT/UNKNOWN claim shapes
            are always skipped and reported, never guessed.

            Nothing reads asset_id yet (native cutover is Stage 5) — this
            command's writes are inert with respect to replay, analytics, and
            every other consumer. No production cutover happens here.

            Defaults to a dry run (--commit is required to persist changes).
            Idempotent: re-running (with or without the same --run-id) reports
            zero additional writes once every resolvable row already carries
            the correct asset_id. Resumable via --run-id, exactly like
            execute_migration/bootstrap_registry.

            Actions
            -------
              (default)            Backfill (dry-run unless --commit). Prints
                                     a full progress report: per-shape outcome,
                                     row counts updated, and the unresolved
                                     backlog.

              --unresolved-report   Read-only regardless of --commit. Prints
                                     only the adjudication backlog — every
                                     unresolved claim shape and its exact
                                     transaction scope.

              --rollback RUN_ID     Reverse a prior LIVE run precisely: resets
                                     asset_id back to NULL for exactly the rows
                                     that run wrote (never a later run's rows).
                                     Dry-run unless --commit is also given.

            Exit codes
            ----------
              0  no unresolved claim shapes remain in scope
              1  unresolved claim shapes remain (adjudication required), or
                 an unexpected failure occurred
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    backfill.add_argument(
        "--portfolio", "-p",
        type=int,
        metavar="ID",
        help="Portfolio ID to backfill",
    )
    backfill.add_argument(
        "--all",
        action="store_true",
        help="Backfill across every portfolio in the workspace",
    )
    backfill.add_argument(
        "--run-id",
        metavar="UUID",
        help="Resume a specific prior run; omit to start a new run",
    )
    backfill.add_argument(
        "--commit",
        action="store_true",
        help="Persist changes to the database (default is a dry run)",
    )
    backfill.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip the confirmation prompt when --commit is used",
    )
    backfill.add_argument(
        "--unresolved-report",
        action="store_true",
        help="Print only the unresolved-assets adjudication backlog (always read-only).",
    )
    backfill.add_argument(
        "--rollback",
        metavar="RUN_ID",
        help="Reverse a prior live run's writes precisely (dry-run unless --commit is also given).",
    )

    # ── seed_registry_classification ─────────────────────────────────────────
    seed_classification = sub.add_parser(
        "seed_registry_classification",
        help="Seed Registry SECTOR classification from the static sector taxonomy (Classification Consolidation)",
        description=textwrap.dedent("""\
            Copies services/sector_taxonomy.py's static THAI_SECTOR_MAP /
            _DR_SECTOR_MAP values into the Asset Registry as SECTOR
            AssetClassification facts, for every Watchlist/PortfolioItem
            symbol the Registry can already resolve to a minted Asset.

            Never overwrites an existing classification fact — only fills
            gaps. Safe to re-run at any time, including after new assets
            are minted by a future M5 Track B backfill.

            Defaults to a dry run (--commit is required to persist changes).
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    seed_classification.add_argument(
        "--commit",
        action="store_true",
        help="Persist changes to the database (default is a dry run)",
    )
    seed_classification.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip the confirmation prompt when --commit is used",
    )

    return parser


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    # Force UTF-8 on Windows so box-drawing characters in _hr() don't crash.
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    parser = _build_parser()
    args   = parser.parse_args()

    if args.command == "repair_snapshots":
        exit_code = asyncio.run(_cmd_repair_snapshots(args))
        sys.exit(exit_code)
    elif args.command == "verify_snapshots":
        exit_code = _cmd_verify_snapshots(args)
        sys.exit(exit_code)
    elif args.command == "recalculate_snapshot_returns":
        exit_code = _cmd_recalculate_snapshot_returns(args)
        sys.exit(exit_code)
    elif args.command == "delete_portfolio":
        exit_code = _cmd_delete_portfolio(args)
        sys.exit(exit_code)
    elif args.command == "rebuild_portfolio":
        exit_code = asyncio.run(_cmd_rebuild_portfolio(args))
        sys.exit(exit_code)
    elif args.command == "validate_ledger":
        exit_code = asyncio.run(_cmd_validate_ledger(args))
        sys.exit(exit_code)
    elif args.command == "golden_baseline":
        exit_code = asyncio.run(_cmd_golden_baseline(args))
        sys.exit(exit_code)
    elif args.command == "plan_migration":
        exit_code = _cmd_plan_migration(args)
        sys.exit(exit_code)
    elif args.command == "execute_migration":
        exit_code = _cmd_execute_migration(args)
        sys.exit(exit_code)
    elif args.command == "bootstrap_registry":
        exit_code = _cmd_bootstrap_registry(args)
        sys.exit(exit_code)
    elif args.command == "backfill_asset_ids":
        exit_code = _cmd_backfill_asset_ids(args)
        sys.exit(exit_code)
    elif args.command == "apply_repair":
        exit_code = asyncio.run(_cmd_apply_repair(args))
        sys.exit(exit_code)
    elif args.command == "generate_repair_plan":
        exit_code = asyncio.run(_cmd_generate_repair_plan(args))
        sys.exit(exit_code)
    elif args.command == "backfill_recommendation_grades":
        exit_code = _cmd_backfill_recommendation_grades(args)
        sys.exit(exit_code)
    elif args.command == "regenerate_paper_portfolios":
        exit_code = asyncio.run(_cmd_regenerate_paper_portfolios(args))
        sys.exit(exit_code)
    elif args.command == "seed_registry_classification":
        exit_code = _cmd_seed_registry_classification(args)
        sys.exit(exit_code)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
