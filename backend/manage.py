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
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import os
import time
import textwrap
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
    RebuildResult,
    ReconciliationStatus,
    rebuild_all_portfolios,
    rebuild_portfolio,
)
from services.ledger_validator import (
    FindingSeverity,
    LedgerFinding,
    LedgerValidationReport,
    validate_all_ledgers,
    validate_portfolio_ledger,
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

    # Stage 5
    print()
    if r.dry_run:
        print("  DRY RUN — no database changes were made")
    elif r.committed:
        print("  COMMITTED — database updated successfully")
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
    total      = len(results)
    succeeded  = sum(1 for r in results if r.success)
    failed     = total - succeeded
    committed  = sum(1 for r in results if r.committed)
    diff_items = sum(r.items_different for r in results)
    diff_snaps = sum(r.snapshots_different for r in results)

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
    if diff_items:
        print(f"  Holdings with drift     : {diff_items}")
    if diff_snaps:
        print(f"  Snapshots with NAV diff : {diff_snaps}")
    if dry_run:
        print(f"\n  No database changes were made.")
    else:
        print(f"  Committed               : {committed}")
    print(_hr())
    print(f"\nCompleted in {elapsed:.2f} seconds.")
    print()


async def _cmd_rebuild_portfolio(args: argparse.Namespace) -> int:
    """Deterministic portfolio rebuild from the transaction ledger."""
    dry_run: bool = getattr(args, "dry_run", False)
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

        # ── Confirmation prompt ───────────────────────────────────────────────
        print(f"\n{_hr()}")
        action = "DRY RUN — " if dry_run else ""
        print(f"{action}Portfolio Reconstruction Engine")
        print(_hr())
        print(f"  Portfolios       : {rebuild_ids}")
        if from_date:
            print(f"  From date        : {from_date}")
        if skip_snapshots:
            print(f"  Skip snapshots   : yes")
        print(f"  Stages           : 1-Stage1 (transactions)"
              + ("" if skip_snapshots else " + 2-3 (snapshots)") + " + 4 (reconcile)"
              + (" + 5 (commit)" if not dry_run else ""))
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
                progress_cb    = _cb,
            )
            results.append(r)
            _print_rebuild_result(r, verbose=verbose)

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


async def _cmd_validate_ledger(args: argparse.Namespace) -> int:
    """Read-only transaction ledger audit. Never modifies the database."""
    db      = SessionLocal()
    t_start = time.monotonic()
    results: list[LedgerValidationReport] = []

    fetch_prices        = getattr(args, "price_check", False)
    price_deviation_pct = getattr(args, "price_threshold", 100.0)

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

        print(f"\n{_hr()}")
        print("Ledger Validator  (read-only — never modifies the database)")
        if fetch_prices:
            print(f"Price check enabled  threshold={price_deviation_pct:.0f}%")
        print(_hr())

        for p in portfolios:
            print(f"  Validating portfolio {p.id} \"{p.name}\"...")
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
    total_crit = sum(len(r.criticals) for r in results)
    total_issues = sum(len(r.findings) for r in results)
    if total_crit:
        return 2
    if total_issues:
        return 1
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

              Stage 5  Atomic commit (single DB transaction; rollback on failure)

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
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
