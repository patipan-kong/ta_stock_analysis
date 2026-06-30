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

• Formulas are delegated to services.portfolio_metrics.compute_period_metrics()
  (ADR-004 — exactly one implementation of portfolio return calculations,
  shared across every snapshot-producing engine):

  - net_external_cash_flow is ledger-derived (sum of DEPOSIT/INITIAL_CASH minus
    WITHDRAW — Implementation A, ADR-002), NOT the cash-balance-delta formula
    this engine previously used. See docs/PORTFOLIO_CALCULATION_RULES.md
    Section 4 for the architecture review that settled this: a cash-balance-
    delta formula treats Portfolio.cash_balance as authoritative, but
    Principle 1 (Transaction ledger is the single source of truth) requires
    the ledger to win, with cash_balance as a checked/derived artifact
    (ledger_validator.py CHECK 8 already operates on this premise).

  - imported_asset_value has no duplicate-import dedup heuristic. Detecting
    and correcting duplicate INITIAL_POSITION rows is a ledger-quality
    concern, owned by ledger_validator.py / ledger_repair_plan.py (Section 6
    of the frozen rules doc), not snapshot math.

• For imported_asset_value / manual_adjustment_value, tx.price_per_share is
  used (no live price fetch) — this engine never passes a price_lookup to
  compute_period_metrics(), so every valuation falls back to the
  transaction's own recorded price. In the live pipeline (portfolio_snapshots.py),
  the live market price is preferred.

• All writes for a portfolio (or all portfolios in --all mode) are accumulated
  inside the caller's session.  The caller commits or rolls back.
• Baseline snapshot (first in the series) always gets None for every field —
  there is no previous NAV to compute a return against.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from models.database import Portfolio, PortfolioSnapshot, Transaction
from services.portfolio_metrics import compute_period_metrics
from services.transaction_canonicalizer import canonicalize_transactions

_log = logging.getLogger(__name__)

# ── Transaction type sets (mirror portfolio_snapshots.py exactly) ──────────────
_CASH_INFLOW_TYPES  = {"DEPOSIT", "INITIAL_CASH"}
_CASH_OUTFLOW_TYPES = {"WITHDRAW"}
_ASSET_IMPORT_TYPES = {"INITIAL_POSITION"}
_MANUAL_ADJ_TYPES   = {"QUANTITY_CORRECTION"}

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

    Formulas are delegated to services.portfolio_metrics.compute_period_metrics()
    (ADR-004). net_external_cash_flow is ledger-derived, not a cash-balance-delta
    reconciliation (ADR-002 — see module docstring). imported_asset_value has no
    duplicate-import dedup heuristic (Section 6 of the frozen rules doc).
    """
    if prev_snap is None or not prev_snap.total_value or prev_snap.total_value <= 0:
        return {f: None for f in _RETURN_FIELDS}

    today_end    = datetime.strptime(curr_snap.snapshot_date, "%Y-%m-%d") + timedelta(days=1)
    prev_day_end = datetime.strptime(prev_snap.snapshot_date, "%Y-%m-%d") + timedelta(days=1)

    window_txs = canonicalize_transactions(
        db.query(Transaction).filter(
            Transaction.portfolio_id == portfolio_id,
            Transaction.transaction_type.in_(list(
                _CASH_INFLOW_TYPES | _CASH_OUTFLOW_TYPES | _ASSET_IMPORT_TYPES
                | _MANUAL_ADJ_TYPES | {"SELL", "BUY", "DIVIDEND"}
            )),
            Transaction.created_at >= prev_day_end,
            Transaction.created_at <  today_end,
        ).all()
    )

    metrics = compute_period_metrics(
        curr_nav=curr_snap.total_value,
        prev_nav=prev_snap.total_value,
        period_transactions=window_txs,
    )

    return {
        "net_external_cash_flow":   metrics.net_external_cash_flow,
        "imported_asset_value":     metrics.imported_asset_value,
        "manual_adjustment_value":  metrics.manual_adjustment_value,
        "investment_return_pct":    metrics.investment_return_pct,
        "investment_return_amount": metrics.investment_return_amount,
        "daily_return_pct":         metrics.daily_return_pct,
        "period_realized_pnl":      metrics.period_realized_pnl,
        "period_dividend_income":   metrics.period_dividend_income,
        "period_fees_paid":         metrics.period_fees_paid,
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
