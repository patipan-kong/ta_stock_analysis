"""Snapshot return recovery engine.

Recalculates return-related snapshot fields from stored NAV values and the
Transaction table, without fetching live market prices or rebuilding holdings.

Fields recalculated
-------------------
  net_external_cash_flow   — actual cash flow from external sources this period
  imported_asset_value     — net-new INITIAL_POSITION equity injected this period
  manual_adjustment_value  — QUANTITY_CORRECTION × price_per_share this period
  investment_return_pct    — pure market gain / prev_nav × 100
  investment_return_amount — absolute pure market gain
  daily_return_pct         — always equal to investment_return_pct
  period_realized_pnl      — P&L from SELL notes this period
  period_dividend_income   — DIVIDEND total_amount this period
  period_fees_paid         — BUY + SELL fees/taxes this period

Fields NOT touched
------------------
  total_value, cash_balance, total_invested, unrealized_pnl, unrealized_pnl_pct,
  realized_pnl, holdings_json, sector_breakdown_json, holdings_count

Design notes
------------
• Window detection uses Transaction.created_at (physical insert time), NOT
  transaction_date — matching portfolio_snapshots.py exactly.

• net_external_cash_flow is derived from ACTUAL cash balance change, not from
  summing DEPOSIT/WITHDRAW transaction records:
    net_ecf = (curr_cash − prev_cash) + BUY_cash_out − SELL_cash_in
  This formula is algebraically equivalent to (DEPOSIT − WITHDRAW) when the
  portfolio's cash_balance is correctly updated by every transaction.  When a
  DEPOSIT or INITIAL_CASH was recorded in the Transaction table as a retroactive
  bookkeeping entry but the underlying cash_balance was never actually changed,
  the formula correctly returns zero for that period instead of producing a
  phantom non-performance adjustment.

• INITIAL_POSITION imported_asset_value is excluded when the symbol was already
  present in prev_snap.holdings_json with equal or more shares.  Such imports are
  retroactive documentation entries for positions already embedded in the previous
  NAV; including them would double-subtract the equity from the return calculation.

• For imported_asset_value of genuinely new imports, tx.price_per_share is used
  (no live price fetch).  In the live pipeline, the live market price is preferred.

• All writes for a portfolio (or all portfolios in --all mode) are accumulated
  inside the caller's session.  The caller commits or rolls back.
• Baseline snapshot (first in the series) always gets None for every field —
  there is no previous NAV to compute a return against.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from models.database import Portfolio, PortfolioSnapshot, Transaction

_log = logging.getLogger(__name__)

# ── Transaction type sets (mirror portfolio_snapshots.py exactly) ──────────────
_CASH_INFLOW_TYPES  = {"DEPOSIT", "INITIAL_CASH"}
_CASH_OUTFLOW_TYPES = {"WITHDRAW"}
_ASSET_IMPORT_TYPES = {"INITIAL_POSITION"}
_MANUAL_ADJ_TYPES   = {"QUANTITY_CORRECTION"}

_REALIZED_RE = re.compile(r"Realized P&L:\s*([-+]?\d+\.?\d*)")

# Ordered tuple keeps field order consistent in dry-run output.
_RETURN_FIELDS: tuple[str, ...] = (
    "net_external_cash_flow",
    "imported_asset_value",
    "manual_adjustment_value",
    "investment_return_pct",
    "investment_return_amount",
    "daily_return_pct",
    "period_realized_pnl",
    "period_dividend_income",
    "period_fees_paid",
)

_TOLERANCE = 1e-6  # numeric equality tolerance


# ── Result types ──────────────────────────────────────────────────────────────

@dataclass
class SnapshotReturnDiff:
    """Per-snapshot diff produced by the recovery engine."""
    snapshot_id:   int
    snapshot_date: str
    changed:       bool
    old_values:    dict
    new_values:    dict


@dataclass
class PortfolioReturnRecoveryResult:
    """Summary produced for a single portfolio."""
    portfolio_id:        int
    portfolio_name:      str
    snapshots_scanned:   int
    snapshots_changed:   int
    snapshots_unchanged: int
    diffs:               list[SnapshotReturnDiff] = field(default_factory=list)
    error:               str | None = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _values_equal(a, b) -> bool:
    """Return True when a and b are numerically identical (or both None)."""
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return abs(float(a) - float(b)) <= _TOLERANCE


def _round_or_none(value: float, decimals: int = 4) -> float | None:
    """Round a float; return None when value is zero-ish to match snapshot behaviour."""
    return round(value, decimals) if value else None


# ── Core computation ──────────────────────────────────────────────────────────

def _compute_return_fields(
    db: Session,
    portfolio_id: int,
    prev_snap: PortfolioSnapshot | None,
    curr_snap: PortfolioSnapshot,
) -> dict:
    """Compute all return-attribution fields for the period prev → curr.

    When prev_snap is None (baseline) or its NAV is zero/None, every field
    is set to None because there is no prior reference to compute a return
    against.

    Window detection mirrors generate_daily_snapshot() in portfolio_snapshots.py:
      created_at  ∈  [ end_of_prev_date ,  end_of_curr_date )

    This correctly excludes any bookkeeping transactions (INITIAL_POSITION,
    INITIAL_CASH, …) that were inserted on the same calendar day as the
    baseline snapshot, since those transactions are already captured inside
    the baseline NAV and must not be double-counted.

    net_ecf attribution rule
    ────────────────────────
    net_ecf is derived from the portfolio's ACTUAL cash balance change rather
    than by summing DEPOSIT/WITHDRAW records:

        net_ecf = (curr_cash − prev_cash) + BUY_cash_out − SELL_cash_in

    Algebraically this equals (DEPOSIT − WITHDRAW) when every transaction is
    correctly reflected in portfolio.cash_balance.  When a DEPOSIT or
    INITIAL_CASH exists in the Transaction table as a retroactive bookkeeping
    entry (the cash_balance was never actually updated), cash_delta = 0 and
    the formula correctly returns zero — preventing a phantom non-performance
    adjustment that would distort the period return.

    INITIAL_POSITION attribution rule
    ──────────────────────────────────
    An INITIAL_POSITION is excluded from imported_asset_value when the symbol
    was already present in prev_snap.holdings_json with equal or more shares.
    Such a transaction is a retroactive documentation entry for equity already
    embedded in the previous NAV; including it would double-subtract the
    position's value from the period return.
    """
    if prev_snap is None or not prev_snap.total_value or prev_snap.total_value <= 0:
        return {f: None for f in _RETURN_FIELDS}

    today_end    = datetime.strptime(curr_snap.snapshot_date, "%Y-%m-%d") + timedelta(days=1)
    prev_day_end = datetime.strptime(prev_snap.snapshot_date, "%Y-%m-%d") + timedelta(days=1)

    # ── BUY / SELL transactions (needed for net_ecf and period decomposition) ──
    sell_txs = db.query(Transaction).filter(
        Transaction.portfolio_id == portfolio_id,
        Transaction.transaction_type == "SELL",
        Transaction.created_at >= prev_day_end,
        Transaction.created_at <  today_end,
    ).all()

    buy_txs = db.query(Transaction).filter(
        Transaction.portfolio_id == portfolio_id,
        Transaction.transaction_type == "BUY",
        Transaction.created_at >= prev_day_end,
        Transaction.created_at <  today_end,
    ).all()

    # ── Net external cash flow from actual cash balance change ────────────────
    # Formula: net_ecf = (curr_cash − prev_cash) + BUY_cash_out − SELL_cash_in
    # BUY reduces cash by total_amount; SELL increases cash by total_amount.
    # Subtracting these offsets isolates the external cash contribution:
    #   cash_delta = DEPOSIT − WITHDRAW − BUY_cash_out + SELL_cash_in
    #   → DEPOSIT − WITHDRAW = cash_delta + BUY_cash_out − SELL_cash_in
    # If a DEPOSIT/INITIAL_CASH was recorded but the cash_balance was never
    # actually updated (retroactive bookkeeping), the formula returns zero.
    curr_cash = curr_snap.cash_balance or 0.0
    prev_cash = prev_snap.cash_balance or 0.0
    buy_cash_out  = sum(tx.total_amount for tx in buy_txs)
    sell_cash_in  = sum(tx.total_amount for tx in sell_txs)
    net_ecf = (curr_cash - prev_cash) + buy_cash_out - sell_cash_in

    # ── Symbols already tracked in the previous snapshot ─────────────────────
    # Used to detect INITIAL_POSITION transactions that are retroactive entries.
    prev_holdings: dict[str, float] = {}
    if prev_snap.holdings_json:
        try:
            for h in json.loads(prev_snap.holdings_json):
                sym = h.get("symbol")
                if sym:
                    prev_holdings[sym] = float(h.get("shares") or 0.0)
        except (ValueError, TypeError):
            pass

    # ── Asset imports (INITIAL_POSITION) ──────────────────────────────────────
    # Use tx.price_per_share as the best-available approximation for the
    # market value at import time.  The live pipeline uses the current day's
    # price; here we cannot fetch it without a network call.
    # Skip any import for a symbol that already appears in prev_snap with
    # equal or more shares — those are retroactive entries, not new capital.
    import_txs = db.query(Transaction).filter(
        Transaction.portfolio_id == portfolio_id,
        Transaction.transaction_type.in_(list(_ASSET_IMPORT_TYPES)),
        Transaction.created_at >= prev_day_end,
        Transaction.created_at <  today_end,
    ).all()

    imported_asset_value = 0.0
    for tx in import_txs:
        tx_shares   = tx.shares or 0.0
        prev_shares = prev_holdings.get(tx.symbol or "", 0.0)
        if tx_shares <= prev_shares:
            _log.debug(
                "[IMPORT SKIP] portfolio=%d %s %.4f shares already in prev snapshot (had %.4f)",
                portfolio_id, tx.symbol, tx_shares, prev_shares,
            )
            continue
        imported_asset_value += tx_shares * (tx.price_per_share or 0.0)

    # ── Manual quantity corrections (QUANTITY_CORRECTION) ─────────────────────
    adj_txs = db.query(Transaction).filter(
        Transaction.portfolio_id == portfolio_id,
        Transaction.transaction_type.in_(list(_MANUAL_ADJ_TYPES)),
        Transaction.created_at >= prev_day_end,
        Transaction.created_at <  today_end,
    ).all()

    manual_adj_value = sum(
        (tx.shares or 0.0) * (tx.price_per_share or 0.0)
        for tx in adj_txs
    )

    # ── Return calculation ─────────────────────────────────────────────────────
    prev_nav = prev_snap.total_value
    curr_nav = curr_snap.total_value

    pure_market_gain = (
        curr_nav
        - prev_nav
        - net_ecf
        - imported_asset_value
        - manual_adj_value
    )
    investment_return_pct    = round(pure_market_gain / prev_nav * 100, 4)
    investment_return_amount = round(pure_market_gain, 4)
    daily_return_pct         = investment_return_pct

    # ── Period realized P/L + SELL fees ───────────────────────────────────────
    period_realized_pnl = 0.0
    period_fees_paid    = 0.0
    for tx in sell_txs:
        if tx.notes:
            m = _REALIZED_RE.search(tx.notes)
            if m:
                period_realized_pnl += float(m.group(1))
        period_fees_paid += (tx.fees or 0.0) + (tx.taxes or 0.0)

    # ── Dividend income ────────────────────────────────────────────────────────
    div_txs = db.query(Transaction).filter(
        Transaction.portfolio_id == portfolio_id,
        Transaction.transaction_type == "DIVIDEND",
        Transaction.created_at >= prev_day_end,
        Transaction.created_at <  today_end,
    ).all()
    period_dividend_income = sum(tx.total_amount for tx in div_txs)

    # ── BUY fees ──────────────────────────────────────────────────────────────
    for tx in buy_txs:
        period_fees_paid += (tx.fees or 0.0) + (tx.taxes or 0.0)

    return {
        "net_external_cash_flow":   _round_or_none(net_ecf),
        "imported_asset_value":     _round_or_none(imported_asset_value),
        "manual_adjustment_value":  _round_or_none(manual_adj_value),
        "investment_return_pct":    investment_return_pct,
        "investment_return_amount": investment_return_amount,
        "daily_return_pct":         daily_return_pct,
        "period_realized_pnl":      _round_or_none(period_realized_pnl),
        "period_dividend_income":   _round_or_none(period_dividend_income),
        "period_fees_paid":         _round_or_none(period_fees_paid),
    }


# ── Portfolio-level recovery ───────────────────────────────────────────────────

def _recover_one_portfolio(
    db: Session,
    portfolio: Portfolio,
    workspace_id: int,
    dry_run: bool,
) -> PortfolioReturnRecoveryResult:
    """Recalculate return fields for every snapshot in a single portfolio.

    Snapshots are processed oldest-first so that the prev_snap reference is
    always the immediately preceding row in chronological order.

    No commit is issued here; the caller owns the transaction.
    """
    snaps: list[PortfolioSnapshot] = (
        db.query(PortfolioSnapshot)
        .filter_by(portfolio_id=portfolio.id, workspace_id=workspace_id)
        .order_by(PortfolioSnapshot.snapshot_date)
        .all()
    )

    result = PortfolioReturnRecoveryResult(
        portfolio_id        = portfolio.id,
        portfolio_name      = portfolio.name,
        snapshots_scanned   = len(snaps),
        snapshots_changed   = 0,
        snapshots_unchanged = 0,
    )

    prev: PortfolioSnapshot | None = None

    for snap in snaps:
        new_vals = _compute_return_fields(db, portfolio.id, prev, snap)
        old_vals = {f: getattr(snap, f, None) for f in _RETURN_FIELDS}

        changed = any(
            not _values_equal(old_vals[f], new_vals[f])
            for f in _RETURN_FIELDS
        )

        result.diffs.append(SnapshotReturnDiff(
            snapshot_id   = snap.id,
            snapshot_date = snap.snapshot_date,
            changed       = changed,
            old_values    = old_vals,
            new_values    = new_vals,
        ))

        if changed:
            result.snapshots_changed += 1
            if not dry_run:
                for f, v in new_vals.items():
                    setattr(snap, f, v)
                _log.debug(
                    "[RETURN RECOVERY] portfolio=%d date=%s updated return fields",
                    portfolio.id, snap.snapshot_date,
                )
        else:
            result.snapshots_unchanged += 1

        prev = snap

    return result


# ── Public API ─────────────────────────────────────────────────────────────────

def recover_portfolio_snapshot_returns(
    db: Session,
    portfolio_id: int,
    workspace_id: int,
    dry_run: bool = False,
) -> PortfolioReturnRecoveryResult:
    """Recalculate return fields for all snapshots of one portfolio.

    All writes are accumulated in *db* but not committed.  The caller must
    call db.commit() on success or db.rollback() on failure.

    Args:
        db:           SQLAlchemy session.
        portfolio_id: Target portfolio.
        workspace_id: Owning workspace (for security scoping).
        dry_run:      When True, compute new values but do not write.

    Returns:
        PortfolioReturnRecoveryResult with per-snapshot diffs.
    """
    portfolio = (
        db.query(Portfolio)
        .filter_by(id=portfolio_id, workspace_id=workspace_id)
        .first()
    )
    if portfolio is None:
        return PortfolioReturnRecoveryResult(
            portfolio_id        = portfolio_id,
            portfolio_name      = "?",
            snapshots_scanned   = 0,
            snapshots_changed   = 0,
            snapshots_unchanged = 0,
            error = f"Portfolio {portfolio_id} not found in workspace {workspace_id}",
        )

    return _recover_one_portfolio(db, portfolio, workspace_id, dry_run)


def recover_all_snapshot_returns(
    db: Session,
    workspace_id: int,
    dry_run: bool = False,
) -> list[PortfolioReturnRecoveryResult]:
    """Recalculate return fields for every portfolio in a workspace.

    All writes are accumulated in *db* but not committed.  The caller must
    call db.commit() on success or db.rollback() on failure.

    Args:
        db:           SQLAlchemy session.
        workspace_id: Owning workspace.
        dry_run:      When True, compute new values but do not write.

    Returns:
        One PortfolioReturnRecoveryResult per portfolio, ordered by portfolio.id.
    """
    portfolios = (
        db.query(Portfolio)
        .filter_by(workspace_id=workspace_id)
        .order_by(Portfolio.id)
        .all()
    )
    return [
        _recover_one_portfolio(db, p, workspace_id, dry_run)
        for p in portfolios
    ]
