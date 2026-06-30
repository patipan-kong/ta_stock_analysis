"""Portfolio Reconstruction Engine.

The Transaction table is the single Source of Truth.
Everything else is derived from it.

Reconstruction pipeline
-----------------------
  Stage 1 — Transaction replay
              → Portfolio.cash_balance
              → PortfolioItem (shares, avg_cost)
              → Cost basis
              → Cumulative realized P&L

  Stage 2 — Historical snapshot generation
              → Portfolio state replayed as-of each snapshot date
              → Historical closing prices fetched per symbol
              → holdings_json, equity_value, total_value, sector allocation

  Stage 3 — Return metric recalculation
              → investment_return_pct, daily_return_pct
              → net_external_cash_flow, imported_asset_value
              → period_realized_pnl, period_dividend_income, period_fees_paid

  Stage 4 — Validation / reconciliation report
              → MATCH / DIFFERENT / MISSING / EXTRA per field

  Stage 5 — Ledger validation gate
              → CRITICAL finding → abort; commit is blocked
              → Multi-dimensional confidence report computed (ConfidenceReport)

  Stage 6 — Execution plan generation (read-only)
              → Lists every intended DB change before any write occurs
              → Deterministic: same replay → same plan

  Stage 7 — Pre-commit backup (optional)
              → Existing rows exported to JSON before any writes
              → Backup failure aborts the commit

  Stage 8 — Atomic commit (single DB transaction; rollback on any failure)

  Stage 9 — Idempotency (upsert pattern; running twice = same state)

Key design decisions
---------------------
* transaction_date is used for portfolio-state ordering (what was held on a
  given day). created_at is intentionally NOT used here — it is the live
  engine's workaround for backdated imports and does not apply to a full
  rebuild from the ledger.

* Price coverage < 90% → snapshot is generated but flagged; it is written
  with price_missing=True for affected holdings and is not blocked (the
  build still proceeds; the caller may choose to skip writing it).

* allow_swap is user-configurable metadata, not derivable from transactions.
  It is preserved from the existing PortfolioItem when rebuilding.

* QUANTITY_CORRECTION stores abs(delta) in tx.shares; the signed delta is
  recovered from tx.notes ("Quantity correction: +5.0 shares").

Public API
----------
  rebuild_portfolio(db, portfolio_id, workspace_id, ...) -> RebuildResult
  rebuild_all_portfolios(db, workspace_id, ...) -> list[RebuildResult]
  ConfidenceReport         — multi-dimensional quality assessment (0-100 per dimension)
  ReconstructionPlan       — immutable execution plan with all intended DB changes
  PlanOperation            — one intended DB change (table/operation/field/values/reason)
  PlanSummary              — aggregate counts from a ReconstructionPlan
"""
from __future__ import annotations

import asyncio
import bisect
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Any, Callable, Optional

import pandas as pd
from sqlalchemy.orm import Session

from models.database import LedgerRepair, Portfolio, PortfolioItem, PortfolioSnapshot, Transaction
from services.data_fetcher import fetch_history
from services.ledger_repair import apply_repair_overlay, load_active_repairs
from services.ledger_validator import FindingSeverity, LedgerValidationReport, validate_portfolio_ledger
from services.symbol_normalization import get_yfinance_symbol
from services.symbol_resolver import is_dr
from services.transaction_canonicalizer import CanonicalTransaction, canonicalize_transactions

_log = logging.getLogger(__name__)

# Shared quantization used by the live transaction engine
_QUANT = Decimal("0.000001")

# Snapshot is skipped (for write) if fewer than this fraction of holdings
# have a retrievable historical price.
_COVERAGE_THRESHOLD = 0.90

_CASH_INFLOW_TYPES  = frozenset({"DEPOSIT", "INITIAL_CASH"})
_CASH_OUTFLOW_TYPES = frozenset({"WITHDRAW"})


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

def _d(v: Any) -> Decimal:
    return Decimal(str(v))


def _f(v: Decimal) -> float:
    return float(v.quantize(_QUANT, rounding=ROUND_HALF_UP))


# ──────────────────────────────────────────────────────────────────────────────
# In-memory state objects (private to this module)
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class _HoldingState:
    symbol:   str
    shares:   Decimal
    avg_cost: Decimal       # fee-inclusive per share
    sector:   str | None = None


@dataclass
class _PortfolioState:
    """Mutable portfolio state accumulated during transaction replay."""
    cash_balance:              Decimal
    holdings:                  dict[str, _HoldingState]
    cumulative_realized_pnl:   Decimal

    def copy(self) -> "_PortfolioState":
        return _PortfolioState(
            cash_balance            = self.cash_balance,
            holdings                = {
                sym: _HoldingState(
                    symbol   = h.symbol,
                    shares   = h.shares,
                    avg_cost = h.avg_cost,
                    sector   = h.sector,
                )
                for sym, h in self.holdings.items()
            },
            cumulative_realized_pnl = self.cumulative_realized_pnl,
        )


@dataclass
class _SnapshotDay:
    """All fields for one reconstructed snapshot date."""
    snapshot_date:            str
    # NAV fields (Stage 2)
    total_value:              float = 0.0
    cash_balance:             float = 0.0
    equity_value:             float = 0.0     # not stored in DB; used internally
    total_invested:           float = 0.0
    unrealized_pnl:           float = 0.0
    unrealized_pnl_pct:       float = 0.0
    realized_pnl:             float = 0.0
    holdings_json:            str   = "[]"
    holdings_count:           int   = 0
    sector_breakdown_json:    str   = "{}"
    price_coverage:           float = 1.0
    # Return fields (Stage 3)
    daily_return_pct:         float | None = None
    investment_return_pct:    float | None = None
    investment_return_amount: float | None = None
    net_external_cash_flow:   float | None = None
    imported_asset_value:     float | None = None
    manual_adjustment_value:  float | None = None
    period_realized_pnl:      float | None = None
    period_dividend_income:   float | None = None
    period_fees_paid:         float | None = None


# ──────────────────────────────────────────────────────────────────────────────
# Public result types
# ──────────────────────────────────────────────────────────────────────────────

class ReconciliationStatus(str, Enum):
    MATCH     = "MATCH"
    DIFFERENT = "DIFFERENT"
    MISSING   = "MISSING"
    EXTRA     = "EXTRA"


@dataclass
class ReconciliationRow:
    entity_type:         str                 # "portfolio_item" | "snapshot"
    identifier:          str                 # symbol  OR  "YYYY-MM-DD"
    field:               str                 # column name being compared
    current_value:       Any
    reconstructed_value: Any
    status:              ReconciliationStatus


# ── Confidence report ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ConfidenceReport:
    """Multi-dimensional confidence assessment for one reconstruction run.

    Dimensions (each 0–100):
      replay_confidence    Stage 1 found transactions to replay.
      ledger_integrity     Deduction per CRITICAL/ERROR/WARNING validator finding.
      historical_coverage  Proportion of snapshots with full price coverage.
      snapshot_consistency Proportion of reconciliation rows that match (items + snaps).
      validator_confidence Binary gate: 0 if any CRITICAL finding, 100 otherwise.

    overall = weighted sum using _CONF_W_* constants (must sum to 1.0).
    """
    replay_confidence:    float
    ledger_integrity:     float
    historical_coverage:  float
    snapshot_consistency: float
    validator_confidence: float
    overall:              float


# ── Execution plan ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PlanOperation:
    """One intended database change in the reconstruction plan."""
    table:         str        # "Portfolio" | "PortfolioItem" | "PortfolioSnapshot"
    operation:     str        # "INSERT" | "UPDATE" | "DELETE" | "UPSERT"
    object_id:     str        # primary identifier: symbol, date, or str(portfolio_id)
    field:         str | None # column name; None for whole-row operations
    current_value: Any
    new_value:     Any
    reason:        str


@dataclass(frozen=True)
class PlanSummary:
    """Aggregate counts from a ReconstructionPlan."""
    portfolio_updated_fields: tuple[str, ...]
    item_inserts:             int
    item_updates:             int    # objects with ≥1 changed field (not field count)
    item_deletes:             int
    snapshot_inserts:         int
    snapshot_updates:         int
    snapshot_deletes:         int    # always 0; engine never deletes snapshots
    total_write_operations:   int    # object-level count
    validator_critical:       int
    validator_errors:         int
    validator_warnings:       int
    confidence_score:         float


@dataclass(frozen=True)
class ReconstructionPlan:
    """Immutable, deterministic execution plan for a single portfolio rebuild.

    Describes every intended database change before any write occurs.
    Running the same replay twice on unchanged data produces an identical plan.
    Plan generation never modifies the database.
    """
    portfolio_id:      int
    confidence_score:  float
    validator_passed:  bool
    critical_findings: int
    operations:        tuple[PlanOperation, ...]
    summary:           PlanSummary
    generated_at:      str    # UTC ISO-8601 timestamp


@dataclass
class RebuildResult:
    portfolio_id:   int
    portfolio_name: str
    success:        bool
    error:          str | None = None
    dry_run:        bool = False
    from_date:      str | None = None
    skip_snapshots: bool = False
    # Stage 1
    transactions_replayed:          int   = 0
    reconstructed_holdings_count:   int   = 0
    reconstructed_cash:             float | None = None
    # Stage 1 (cont.) — effective ledger overlay (Phase 6.7C)
    effective_transaction_count: int       = 0
    excluded_transaction_count:  int       = 0
    repairs_applied:             int       = 0
    repair_ids:                  list[int] = field(default_factory=list)
    # Stage 2
    snapshots_processed:            int = 0
    snapshots_skipped_low_coverage: int = 0
    # Stage 4 tallies
    items_matched:      int = 0
    items_different:    int = 0
    items_missing:      int = 0
    items_extra:        int = 0
    snapshots_matched:  int = 0
    snapshots_different:int = 0
    snapshots_missing:  int = 0
    snapshots_extra:    int = 0
    reconciliation_report: list[ReconciliationRow] = field(default_factory=list)
    # Stage 5 — Ledger validation gate
    aborted:          bool                   = False
    ledger_criticals: int                    = 0
    ledger_errors:    int                    = 0
    ledger_warnings:  int                    = 0
    validator_report: LedgerValidationReport | None = field(default=None)
    # Stage 6 — Confidence report (multi-dimensional)
    confidence_report: ConfidenceReport | None = field(default=None)
    confidence_score:  float                   = 100.0   # = confidence_report.overall
    # Stage 7 — Execution plan
    execution_plan:   ReconstructionPlan | None = field(default=None)
    # Stage 8 — Pre-commit backup
    committed:        bool                   = False
    backup_path:      str | None             = None
    elapsed_seconds:  float                  = 0.0


# ──────────────────────────────────────────────────────────────────────────────
# Stage 1 — Transaction replay
# ──────────────────────────────────────────────────────────────────────────────

def _apply_transaction(state: _PortfolioState, ctx: CanonicalTransaction) -> None:
    """Apply one canonical transaction to the mutable portfolio state in-place."""
    tx_type = ctx.transaction_type
    amount  = ctx.total_amount  # already Decimal

    if tx_type in _CASH_INFLOW_TYPES or tx_type == "DIVIDEND":
        state.cash_balance += amount

    elif tx_type == "WITHDRAW":
        state.cash_balance -= amount

    elif tx_type == "BUY":
        shares = ctx.shares
        if shares <= 0:
            return
        # total_amount = net_buy_amount (gross + all fees) — same as live engine
        eff_price = amount / shares
        state.cash_balance -= amount

        sym = ctx.raw_symbol
        if sym in state.holdings:
            h = state.holdings[sym]
            new_shares = h.shares + shares
            new_avg    = (h.shares * h.avg_cost + amount) / new_shares
            h.shares   = new_shares
            h.avg_cost = new_avg
            if ctx.sector and not h.sector:
                h.sector = ctx.sector
        else:
            state.holdings[sym] = _HoldingState(
                symbol   = sym,
                shares   = shares,
                avg_cost = eff_price,
                sector   = ctx.sector,
            )

    elif tx_type == "SELL":
        shares = ctx.shares
        if shares <= 0:
            return
        # total_amount = net_sell_proceeds (cash received after fees)
        state.cash_balance += amount
        pnl = ctx.realized_pnl if ctx.realized_pnl is not None else 0.0
        state.cumulative_realized_pnl += _d(pnl)

        sym = ctx.raw_symbol
        if sym in state.holdings:
            h          = state.holdings[sym]
            new_shares = h.shares - shares
            if _f(new_shares) <= 0:
                del state.holdings[sym]
            else:
                h.shares = new_shares

    elif tx_type == "INITIAL_POSITION":
        sym    = ctx.raw_symbol
        shares = ctx.shares
        avg    = ctx.price_per_share
        if not sym or shares <= 0:
            return
        if sym in state.holdings:
            h          = state.holdings[sym]
            new_shares = h.shares + shares
            new_avg    = (h.shares * h.avg_cost + shares * avg) / new_shares if new_shares else avg
            h.shares   = new_shares
            h.avg_cost = new_avg
            if ctx.sector and not h.sector:
                h.sector = ctx.sector
        else:
            state.holdings[sym] = _HoldingState(
                symbol   = sym,
                shares   = shares,
                avg_cost = avg,
                sector   = ctx.sector,
            )
        # INITIAL_POSITION does NOT affect cash balance

    elif tx_type == "QUANTITY_CORRECTION":
        sym = ctx.raw_symbol
        if not sym or sym not in state.holdings:
            return
        delta = ctx.qty_correction_delta  # pre-parsed Decimal with sign
        h     = state.holdings[sym]
        new_shares = h.shares + delta
        if delta > 0:
            price  = ctx.price_per_share
            if new_shares > 0:
                h.avg_cost = (h.shares * h.avg_cost + delta * price) / new_shares
        if _f(new_shares) <= 0:
            del state.holdings[sym]
        else:
            h.shares = new_shares
        # QUANTITY_CORRECTION does NOT affect cash balance


def _replay_with_date_snapshots(
    txs:   list[CanonicalTransaction],
    dates: list[str],           # snapshot dates, sorted ascending
) -> dict[str, _PortfolioState]:
    """Single-pass replay that captures state at the end of each requested date.

    Returns {date: _PortfolioState} for every date in `dates`.
    Complexity: O(N + D) where N = transactions, D = distinct dates.
    """
    state = _PortfolioState(
        cash_balance            = Decimal("0"),
        holdings                = {},
        cumulative_realized_pnl = Decimal("0"),
    )
    result: dict[str, _PortfolioState] = {}
    tx_idx = 0
    n_txs  = len(txs)

    for snap_date in dates:
        # Advance: apply every transaction with tx_date <= snap_date
        while tx_idx < n_txs:
            ctx     = txs[tx_idx]
            tx_date = ctx.transaction_date.strftime("%Y-%m-%d")
            if tx_date <= snap_date:
                _apply_transaction(state, ctx)
                tx_idx += 1
            else:
                break
        result[snap_date] = state.copy()

    return result


# ──────────────────────────────────────────────────────────────────────────────
# Stage 2 — Historical price matrix
# ──────────────────────────────────────────────────────────────────────────────

async def _build_price_matrix(
    symbols:     list[str],
    dates:       list[str],       # "YYYY-MM-DD", sorted
    progress_cb: Callable[[str], None] | None = None,
) -> dict[str, dict[str, float | None]]:
    """Batch-fetch historical closing prices for all symbols × all dates.

    For weekend / holiday dates the last available trading-day close is used
    (backward-fill).

    Returns: {symbol: {date_str: price | None}}
    """
    if not symbols or not dates:
        return {}

    # Always use "5y" so the fetch key matches the pre-warmed cache.
    # DR certificates (e.g. AAPL01.BK) have SET listing history since ~2020;
    # requesting "10y" or "max" on a .BK ticker that lacks the full period
    # causes yfinance to silently fall back to the underlying US ticker and
    # return USD prices instead of THB DR prices.
    period = "5y"

    result: dict[str, dict[str, float | None]] = {}

    for i, sym in enumerate(symbols):
        # DR certificates trade on SET at ~1/10 the US underlying price in THB.
        # get_yfinance_symbol() resolves them to the US ticker (AAPL01.BK → AAPL),
        # which returns USD prices and inflates NAV by ~10×.  Use the .BK form
        # directly so yfinance returns the actual SET DR market price.
        # print(f"{i+1}/{len(symbols)}  {sym}")
        # print(f"\n========== START {sym} ==========")
        if is_dr(sym):
            yf_sym = sym if sym.endswith(".BK") else sym + ".BK"
        else:
            yf_sym = get_yfinance_symbol(sym)

        try:
            df: Optional[pd.DataFrame] = await asyncio.to_thread(
                fetch_history, yf_sym, period, "1d"
            )
            
            # print("=" * 80)
            # print("period :", period)
            # print("ORIGINAL SYMBOL :", sym)
            # print("YFINANCE SYMBOL :", yf_sym)
            # print("cache key :", f"history:{period}:1d")
            # print(f"========== END {sym} ==========")
            if df is not None and not df.empty:
                print(df["Close"].head())
                tail = df["Close"].tail()
        except Exception as exc:
            print(f"========== EXCEPTION {sym}: {exc}")
            _log.warning("price_matrix fetch failed symbol=%s yf=%s: %s", sym, yf_sym, exc)
            df = None        

        if df is None:
            print("DATAFRAME : None")
        else:
           x = df.head()
           print(x.shape)
           print(df.tail())
           print(df["Close"].iloc[0])
           print(df["Close"].iloc[-1])

        date_price: dict[str, float | None] = {}
        if df is not None and not df.empty:
            df_sorted   = df.sort_index()
            df_dates    = df_sorted.index.strftime("%Y-%m-%d").tolist()
            df_closes   = [
                float(v) if pd.notna(v) and float(v) > 0 else None
                for v in df_sorted["Close"]
            ]

            for snap_date in dates:
                # Binary search: last trading day on or before snap_date
                idx = bisect.bisect_right(df_dates, snap_date) - 1
                date_price[snap_date] = df_closes[idx] if idx >= 0 else None
        else:
            date_price = {d: None for d in dates}
        
        result[sym] = date_price
        
        if progress_cb:
            progress_cb(sym)

    # print("RETURNING PRICE MATRIX")
    # print(result.keys())
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Stage 2+3 — Snapshot day construction + return fields
# ──────────────────────────────────────────────────────────────────────────────

def _build_snapshot_day(
    snapshot_date: str,
    state:         _PortfolioState,
    price_row:     dict[str, float | None],   # {symbol: price} for this date
    all_txs:       list[CanonicalTransaction],
    prev_date:     str | None,
    prev_nav:      float | None,
) -> _SnapshotDay:
    """Build a _SnapshotDay from portfolio state + historical prices.

    Also computes Stage 3 return fields when prev_date / prev_nav are provided.
    """
    cash = float(state.cash_balance)

    holdings_list: list[dict] = []
    equity_value  = 0.0
    total_cost    = 0.0
    sector_agg:  dict[str, float] = {}
    n_priced      = 0
    n_holdings    = len(state.holdings)

    for sym, h in state.holdings.items():
        shares   = float(h.shares)
        avg_cost = float(h.avg_cost)
        # print("SNAPSHOT PRICE", snapshot_date, sym, price_row.get(sym))

        price    = price_row.get(sym)

        if sym in ("AAPL01.BK", "AMZN01.BK", "BH.BK") and snapshot_date == "2026-05-26":
            print(
            "[SNAPSHOT]",
            snapshot_date,
            sym,
            "price=", price,
            "shares=", shares,
            "avg_cost=", avg_cost,
            )

        mv       = shares * price if price is not None else None
        cost     = shares * avg_cost
        upnl     = (mv - cost) if mv is not None else None
        sector   = h.sector or "Other"

        if mv is not None:
            equity_value             += mv
            sector_agg[sector]        = sector_agg.get(sector, 0.0) + mv
            n_priced                 += 1
        total_cost += cost

        holdings_list.append({
            "symbol":            sym,
            "shares":            round(shares, 6),
            "avg_cost":          round(avg_cost, 4),
            "current_price":     round(price, 4) if price is not None else None,
            "market_value":      round(mv, 4) if mv is not None else None,
            "unrealized_pnl":    round(upnl, 4) if upnl is not None else None,
            "unrealized_pnl_pct":
                round(upnl / cost * 100, 2) if (upnl is not None and cost > 0) else None,
            "sector":            sector,
            "price_missing":     price is None,
        })

    total_value        = equity_value + cash
    unrealized_pnl     = equity_value - total_cost
    unrealized_pnl_pct = (unrealized_pnl / total_cost * 100) if total_cost > 0 else 0.0
    coverage           = n_priced / n_holdings if n_holdings > 0 else 1.0

    sector_breakdown: dict[str, float] = {
        sec: round(val / total_value * 100, 2) if total_value > 0 else 0.0
        for sec, val in sector_agg.items()
    }

    day = _SnapshotDay(
        snapshot_date          = snapshot_date,
        total_value            = round(total_value, 4),
        cash_balance           = round(cash, 4),
        equity_value           = round(equity_value, 4),
        total_invested         = round(total_cost, 4),
        unrealized_pnl         = round(unrealized_pnl, 4),
        unrealized_pnl_pct     = round(unrealized_pnl_pct, 4),
        realized_pnl           = round(float(state.cumulative_realized_pnl), 4),
        holdings_json          = json.dumps(holdings_list),
        holdings_count         = n_holdings,
        sector_breakdown_json  = json.dumps(sector_breakdown),
        price_coverage         = round(coverage, 4),
    )

    # Stage 3: populate return fields when we have a previous snapshot
    if prev_date and prev_nav and prev_nav > 0:
        _populate_return_fields(day, prev_date, snapshot_date, prev_nav, all_txs)

    return day


def _populate_return_fields(
    day:       _SnapshotDay,
    prev_date: str,
    curr_date: str,
    prev_nav:  float,
    all_txs:   list[CanonicalTransaction],
) -> None:
    """Compute and set return-related fields on the SnapshotDay.

    Window: prev_date < tx.transaction_date <= curr_date.
    Uses transaction_date (not created_at) — correct for historical reconstruction.
    """
    window_txs = [
        ctx for ctx in all_txs
        if prev_date < ctx.transaction_date.strftime("%Y-%m-%d") <= curr_date
    ]

    # ── Cash flows ────────────────────────────────────────────────────────────
    deposits    = sum(float(ctx.total_amount) for ctx in window_txs if ctx.transaction_type in _CASH_INFLOW_TYPES)
    withdrawals = sum(float(ctx.total_amount) for ctx in window_txs if ctx.transaction_type == "WITHDRAW")
    net_ecf     = deposits - withdrawals

    # Current prices from holdings_json for valuing asset imports
    price_map: dict[str, float] = {}
    try:
        for h in json.loads(day.holdings_json):
            sym = h.get("symbol")
            cp  = h.get("current_price")
            if sym and cp is not None:
                price_map[sym] = float(cp)
    except (ValueError, TypeError):
        pass

    # ── Asset imports (INITIAL_POSITION) ─────────────────────────────────────
    imported_asset_value = sum(
        float(ctx.shares) * price_map.get(ctx.raw_symbol or "", float(ctx.price_per_share))
        for ctx in window_txs
        if ctx.transaction_type == "INITIAL_POSITION" and ctx.raw_symbol and ctx.shares > 0
    )

    # ── Quantity corrections (QUANTITY_CORRECTION) ────────────────────────────
    manual_adj_value = sum(
        abs(float(ctx.qty_correction_delta))
        * price_map.get(ctx.raw_symbol or "", float(ctx.price_per_share))
        for ctx in window_txs
        if ctx.transaction_type == "QUANTITY_CORRECTION" and ctx.raw_symbol
    )

    # ── Period decomposition ──────────────────────────────────────────────────
    period_realized_pnl    = 0.0
    period_fees_paid       = 0.0
    period_dividend_income = 0.0

    for ctx in window_txs:
        if ctx.transaction_type == "SELL":
            period_realized_pnl += ctx.realized_pnl if ctx.realized_pnl is not None else 0.0
            period_fees_paid    += float(ctx.fees) + float(ctx.taxes)
        elif ctx.transaction_type == "BUY":
            period_fees_paid += float(ctx.fees) + float(ctx.taxes)
        elif ctx.transaction_type == "DIVIDEND":
            period_dividend_income += float(ctx.total_amount)

    # ── Cash-flow-adjusted return (Modified Dietz, daily) ─────────────────────
    curr_nav    = day.total_value
    pure_gain   = curr_nav - prev_nav - net_ecf - imported_asset_value - manual_adj_value
    inv_ret_pct = round(pure_gain / prev_nav * 100, 4)
    inv_ret_amt = round(pure_gain, 4)

    day.net_external_cash_flow   = round(net_ecf, 4)            if net_ecf            else None
    day.imported_asset_value     = round(imported_asset_value, 4) if imported_asset_value else None
    day.manual_adjustment_value  = round(manual_adj_value, 4)   if manual_adj_value    else None
    day.period_realized_pnl      = round(period_realized_pnl, 4) if period_realized_pnl  else None
    day.period_dividend_income   = round(period_dividend_income, 4) if period_dividend_income else None
    day.period_fees_paid         = round(period_fees_paid, 4)   if period_fees_paid    else None
    day.investment_return_pct    = inv_ret_pct
    day.investment_return_amount = inv_ret_amt
    day.daily_return_pct         = inv_ret_pct


# ──────────────────────────────────────────────────────────────────────────────
# Stage 4 — Reconciliation
# ──────────────────────────────────────────────────────────────────────────────

def _reconcile_portfolio_items(
    db:           Session,
    portfolio_id: int,
    final_state:  _PortfolioState,
) -> list[ReconciliationRow]:
    """Compare existing PortfolioItem rows against the reconstructed final state."""
    current = {
        item.symbol: item
        for item in db.query(PortfolioItem).filter_by(portfolio_id=portfolio_id).all()
    }
    recon = final_state.holdings

    rows: list[ReconciliationRow] = []

    for sym in sorted(set(current) | set(recon)):
        curr_item  = current.get(sym)
        recon_item = recon.get(sym)

        if curr_item is None:
            rows.append(ReconciliationRow(
                entity_type         = "portfolio_item",
                identifier          = sym,
                field               = "*",
                current_value       = None,
                reconstructed_value = {
                    "shares":   _f(recon_item.shares),
                    "avg_cost": _f(recon_item.avg_cost),
                },
                status = ReconciliationStatus.MISSING,
            ))
            continue

        if recon_item is None:
            rows.append(ReconciliationRow(
                entity_type         = "portfolio_item",
                identifier          = sym,
                field               = "*",
                current_value       = {"shares": curr_item.shares, "avg_cost": curr_item.avg_cost},
                reconstructed_value = None,
                status              = ReconciliationStatus.EXTRA,
            ))
            continue

        # Both exist — compare field by field
        for col, tol in [("shares", 0.0001), ("avg_cost", 0.01)]:
            curr_val  = getattr(curr_item, col)
            recon_val = _f(getattr(recon_item, col))
            diff      = abs((curr_val or 0.0) - (recon_val or 0.0))
            rows.append(ReconciliationRow(
                entity_type         = "portfolio_item",
                identifier          = sym,
                field               = col,
                current_value       = round(curr_val, 6),
                reconstructed_value = round(recon_val, 6),
                status              = ReconciliationStatus.MATCH if diff <= tol
                                      else ReconciliationStatus.DIFFERENT,
            ))

    return rows


def _reconcile_snapshots(
    db:            Session,
    portfolio_id:  int,
    snapshot_days: list[_SnapshotDay],
    from_date:     str | None,
) -> list[ReconciliationRow]:
    """Compare existing PortfolioSnapshot rows against the reconstructed days."""
    recon_map = {day.snapshot_date: day for day in snapshot_days}

    # Only compare snapshots in the rebuild window
    query = db.query(PortfolioSnapshot).filter_by(portfolio_id=portfolio_id)
    if from_date:
        query = query.filter(PortfolioSnapshot.snapshot_date >= from_date)
    current_map = {s.snapshot_date: s for s in query.all()}

    rows: list[ReconciliationRow] = []
    all_dates = sorted(set(current_map) | set(recon_map))

    _NAV_FIELDS = [
        ("total_value",     1.0),
        ("cash_balance",    1.0),
        ("total_invested",  1.0),
        ("unrealized_pnl",  1.0),
        ("realized_pnl",    1.0),
    ]

    for date in all_dates:
        curr  = current_map.get(date)
        recon = recon_map.get(date)

        if curr is None:
            rows.append(ReconciliationRow(
                entity_type         = "snapshot",
                identifier          = date,
                field               = "*",
                current_value       = None,
                reconstructed_value = {"total_value": recon.total_value if recon else None},
                status              = ReconciliationStatus.MISSING,
            ))
            continue

        if recon is None:
            rows.append(ReconciliationRow(
                entity_type         = "snapshot",
                identifier          = date,
                field               = "*",
                current_value       = {"total_value": curr.total_value},
                reconstructed_value = None,
                status              = ReconciliationStatus.EXTRA,
            ))
            continue

        for col, tol in _NAV_FIELDS:
            curr_val  = getattr(curr, col, None)
            recon_val = getattr(recon, col, None)
            if curr_val is None and recon_val is None:
                continue
            diff = abs((curr_val or 0.0) - (recon_val or 0.0))
            rows.append(ReconciliationRow(
                entity_type         = "snapshot",
                identifier          = date,
                field               = col,
                current_value       = round(curr_val, 2) if curr_val is not None else None,
                reconstructed_value = round(recon_val, 2) if recon_val is not None else None,
                status              = ReconciliationStatus.MATCH if diff <= tol
                                      else ReconciliationStatus.DIFFERENT,
            ))

    return rows


# ──────────────────────────────────────────────────────────────────────────────
# Stage 5 — Ledger validation gate + confidence report
# ──────────────────────────────────────────────────────────────────────────────

# Deduction constants for the ledger_integrity dimension (applied within 0-100 scale)
_CONF_LEDGER_PER_CRITICAL = 10.0
_CONF_LEDGER_PER_ERROR    =  5.0
_CONF_LEDGER_PER_WARNING  =  2.0

# Documented weights for ConfidenceReport.overall — must sum exactly to 1.0
_CONF_W_REPLAY      = 0.20   # Stage 1 success
_CONF_W_LEDGER      = 0.25   # ledger validator integrity
_CONF_W_COVERAGE    = 0.20   # historical price coverage
_CONF_W_CONSISTENCY = 0.20   # item + snapshot field reconciliation
_CONF_W_VALIDATOR   = 0.15   # binary gate (0 if any CRITICAL)


def _compute_confidence_report(
    result:        RebuildResult,
    snapshot_days: list[_SnapshotDay],
) -> ConfidenceReport:
    """Compute the multi-dimensional ConfidenceReport for a rebuild run.

    Dimensions
    ----------
    replay_confidence     0 if no transactions were replayed; 100 otherwise.
    ledger_integrity      100 minus per-finding deductions (CRITICAL/ERROR/WARNING).
    historical_coverage   100 × (1 − low_coverage_snaps / total_snaps).
    snapshot_consistency  100 × (1 − different_recon_rows / total_recon_rows).
                          Covers both PortfolioItem and PortfolioSnapshot rows.
    validator_confidence  0 if any CRITICAL finding; 100 otherwise.

    overall = weighted sum using _CONF_W_* constants.
    """
    # Replay confidence
    replay = 100.0 if result.transactions_replayed > 0 else 0.0

    # Ledger integrity
    ledger = max(0.0, min(100.0,
        100.0
        - result.ledger_criticals * _CONF_LEDGER_PER_CRITICAL
        - result.ledger_errors    * _CONF_LEDGER_PER_ERROR
        - result.ledger_warnings  * _CONF_LEDGER_PER_WARNING
    ))

    # Historical coverage
    total_snaps = len(snapshot_days)
    low_cov = sum(
        1 for d in snapshot_days
        if d.holdings_count > 0 and d.price_coverage < _COVERAGE_THRESHOLD
    )
    coverage = max(0.0, min(100.0,
        100.0 * (1.0 - low_cov / total_snaps) if total_snaps > 0 else 100.0
    ))

    # Snapshot + item reconciliation consistency
    total_recon = (
        result.items_matched    + result.items_different
        + result.items_missing  + result.items_extra
        + result.snapshots_matched  + result.snapshots_different
        + result.snapshots_missing  + result.snapshots_extra
    )
    different_recon = result.items_different + result.snapshots_different
    consistency = max(0.0, min(100.0,
        100.0 * (1.0 - different_recon / total_recon)
        if total_recon > 0 else 100.0
    ))

    # Validator confidence (binary gate)
    validator_conf = 0.0 if result.ledger_criticals > 0 else 100.0

    # Weighted overall
    overall = round(
        replay         * _CONF_W_REPLAY
        + ledger       * _CONF_W_LEDGER
        + coverage     * _CONF_W_COVERAGE
        + consistency  * _CONF_W_CONSISTENCY
        + validator_conf * _CONF_W_VALIDATOR,
        1,
    )

    return ConfidenceReport(
        replay_confidence    = round(replay, 1),
        ledger_integrity     = round(ledger, 1),
        historical_coverage  = round(coverage, 1),
        snapshot_consistency = round(consistency, 1),
        validator_confidence = round(validator_conf, 1),
        overall              = overall,
    )


def _compute_confidence_score(
    result:        RebuildResult,
    snapshot_days: list[_SnapshotDay],
) -> float:
    """Return the overall confidence score (0–100).

    Delegates to _compute_confidence_report().overall.
    Kept for backward compatibility with callers that only need the scalar.
    """
    return _compute_confidence_report(result, snapshot_days).overall


# ──────────────────────────────────────────────────────────────────────────────
# Stage 6 — Backup export
# ──────────────────────────────────────────────────────────────────────────────

def _export_backup(
    db:           Session,
    portfolio_id: int,
    backup_dir:   str = "backups",
) -> str:
    """Dump the current PortfolioItem + PortfolioSnapshot + LedgerRepair rows to JSON.

    Called before the atomic commit so the pre-rebuild state is preserved.
    LedgerRepair rows are included so that a restore from backup can
    reconstruct the same effective canonical list that was used for the rebuild.
    Returns the absolute path of the written file.
    """
    os.makedirs(backup_dir, exist_ok=True)
    ts   = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(backup_dir, f"rebuild_{portfolio_id}_{ts}.json")

    portfolio = db.query(Portfolio).filter_by(id=portfolio_id).first()
    items     = db.query(PortfolioItem).filter_by(portfolio_id=portfolio_id).all()
    snaps     = db.query(PortfolioSnapshot).filter_by(portfolio_id=portfolio_id).all()
    repairs   = db.query(LedgerRepair).filter_by(portfolio_id=portfolio_id).all()

    data: dict = {
        "portfolio_id":     portfolio_id,
        "backup_timestamp": datetime.utcnow().isoformat() + "Z",
        "portfolio": {
            "name":         portfolio.name          if portfolio else None,
            "cash_balance": portfolio.cash_balance  if portfolio else None,
        },
        "portfolio_items": [
            {
                "symbol":    item.symbol,
                "shares":    item.shares,
                "avg_cost":  item.avg_cost,
                "sector":    item.sector,
                "allow_swap": item.allow_swap,
            }
            for item in items
        ],
        "snapshots": [
            {
                "snapshot_date": snap.snapshot_date,
                "total_value":   snap.total_value,
                "cash_balance":  snap.cash_balance,
                "equity_value":  getattr(snap, "equity_value", None),
                "holdings_json": snap.holdings_json,
            }
            for snap in snaps
        ],
        "ledger_repairs": [
            {
                "id":             repair.id,
                "transaction_id": repair.transaction_id,
                "repair_plan_id": repair.repair_plan_id,
                "repair_type":    repair.repair_type,
                "reason":         repair.reason,
                "reason_code":    repair.reason_code,
                "payload_json":   repair.payload_json,
                "created_by":     repair.created_by,
                "created_at":     repair.created_at,
                "is_active":      repair.is_active,
            }
            for repair in repairs
        ],
    }

    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, default=str)

    _log.info("backup written: portfolio=%d path=%s", portfolio_id, path)
    return path


# ──────────────────────────────────────────────────────────────────────────────
# Stage 7 — Execution plan
# ──────────────────────────────────────────────────────────────────────────────

def _values_differ(a: Any, b: Any, tol: float = 0.01) -> bool:
    """Return True when a and b are meaningfully different.

    None vs None → no difference.
    Numerics compared with absolute tolerance.
    Everything else compared as strings.
    """
    if a is None and b is None:
        return False
    if a is None or b is None:
        return True
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(float(a) - float(b)) > tol
    return str(a) != str(b)


def _generate_execution_plan(
    db:             Session,
    portfolio_id:   int,
    portfolio:      Portfolio,
    final_state:    _PortfolioState,
    snapshot_days:  list[_SnapshotDay],
    from_date:      str | None,
    confidence:     ConfidenceReport,
    validator:      LedgerValidationReport | None,
    skip_snapshots: bool,
) -> ReconstructionPlan:
    """Generate a deterministic, read-only execution plan.

    Lists every intended DB change without writing anything.
    Running the same replay twice on unchanged data produces an identical plan.
    The plan is the official audit trail for every reconstruction.
    """
    ops: list[PlanOperation] = []

    # ── Portfolio.cash_balance ────────────────────────────────────────────────
    new_cash = _f(final_state.cash_balance)
    port_updated_fields: list[str] = []
    if _values_differ(portfolio.cash_balance, new_cash, tol=0.001):
        port_updated_fields.append("cash_balance")
        ops.append(PlanOperation(
            table         = "Portfolio",
            operation     = "UPDATE",
            object_id     = str(portfolio_id),
            field         = "cash_balance",
            current_value = round(portfolio.cash_balance, 4) if portfolio.cash_balance is not None else None,
            new_value     = round(new_cash, 4),
            reason        = "Cash balance reconstructed from transaction ledger",
        ))

    # ── PortfolioItem rows ────────────────────────────────────────────────────
    current_items = {
        item.symbol: item
        for item in db.query(PortfolioItem).filter_by(portfolio_id=portfolio_id).all()
    }
    final_syms   = set(final_state.holdings)
    current_syms = set(current_items)
    updated_syms: set[str] = set()   # symbols with ≥1 changed field

    for sym in sorted(final_syms & current_syms):
        h          = final_state.holdings[sym]
        curr       = current_items[sym]
        new_shares = _f(h.shares)
        new_avg    = _f(h.avg_cost)

        if _values_differ(curr.shares, new_shares, tol=0.0001):
            updated_syms.add(sym)
            ops.append(PlanOperation(
                table         = "PortfolioItem",
                operation     = "UPDATE",
                object_id     = sym,
                field         = "shares",
                current_value = round(curr.shares, 6) if curr.shares is not None else None,
                new_value     = round(new_shares, 6),
                reason        = "Reconstructed from transaction ledger",
            ))

        if _values_differ(curr.avg_cost, new_avg, tol=0.01):
            updated_syms.add(sym)
            ops.append(PlanOperation(
                table         = "PortfolioItem",
                operation     = "UPDATE",
                object_id     = sym,
                field         = "avg_cost",
                current_value = round(curr.avg_cost, 6) if curr.avg_cost is not None else None,
                new_value     = round(new_avg, 6),
                reason        = "Reconstructed from transaction ledger",
            ))

    for sym in sorted(final_syms - current_syms):
        h = final_state.holdings[sym]
        ops.append(PlanOperation(
            table         = "PortfolioItem",
            operation     = "INSERT",
            object_id     = sym,
            field         = None,
            current_value = None,
            new_value     = {
                "shares":   _f(h.shares),
                "avg_cost": _f(h.avg_cost),
                "sector":   h.sector,
            },
            reason        = "Symbol found in transaction ledger but absent from PortfolioItem",
        ))

    for sym in sorted(current_syms - final_syms):
        curr = current_items[sym]
        ops.append(PlanOperation(
            table         = "PortfolioItem",
            operation     = "DELETE",
            object_id     = sym,
            field         = None,
            current_value = {"shares": curr.shares, "avg_cost": curr.avg_cost},
            new_value     = None,
            reason        = "Symbol absent from replayed final holdings; position fully closed",
        ))

    # ── PortfolioSnapshot rows ─────────────────────────────────────────────────
    snap_inserts = 0
    snap_updates = 0

    if not skip_snapshots:
        snap_q = db.query(PortfolioSnapshot).filter_by(portfolio_id=portfolio_id)
        if from_date:
            snap_q = snap_q.filter(PortfolioSnapshot.snapshot_date >= from_date)
        current_snaps = {s.snapshot_date: s for s in snap_q.all()}

        for day in snapshot_days:
            existing = current_snaps.get(day.snapshot_date)
            if existing:
                ops.append(PlanOperation(
                    table         = "PortfolioSnapshot",
                    operation     = "UPSERT",
                    object_id     = day.snapshot_date,
                    field         = None,
                    current_value = {
                        "total_value":  existing.total_value,
                        "cash_balance": existing.cash_balance,
                    },
                    new_value     = {
                        "total_value":  day.total_value,
                        "cash_balance": day.cash_balance,
                    },
                    reason        = "Historical snapshot reconstructed from transaction replay",
                ))
                snap_updates += 1
            else:
                ops.append(PlanOperation(
                    table         = "PortfolioSnapshot",
                    operation     = "INSERT",
                    object_id     = day.snapshot_date,
                    field         = None,
                    current_value = None,
                    new_value     = {
                        "total_value":  day.total_value,
                        "cash_balance": day.cash_balance,
                    },
                    reason        = "Missing historical snapshot; reconstructed from transaction replay",
                ))
                snap_inserts += 1

    # ── Summary ────────────────────────────────────────────────────────────────
    n_item_inserts = len(final_syms - current_syms)
    n_item_updates = len(updated_syms)
    n_item_deletes = len(current_syms - final_syms)

    summary = PlanSummary(
        portfolio_updated_fields = tuple(port_updated_fields),
        item_inserts             = n_item_inserts,
        item_updates             = n_item_updates,
        item_deletes             = n_item_deletes,
        snapshot_inserts         = snap_inserts,
        snapshot_updates         = snap_updates,
        snapshot_deletes         = 0,
        total_write_operations   = (
            len(port_updated_fields)
            + n_item_inserts + n_item_updates + n_item_deletes
            + snap_inserts + snap_updates
        ),
        validator_critical = len(validator.criticals) if validator else 0,
        validator_errors   = len(validator.errors)    if validator else 0,
        validator_warnings = len(validator.warnings)  if validator else 0,
        confidence_score   = confidence.overall,
    )

    return ReconstructionPlan(
        portfolio_id      = portfolio_id,
        confidence_score  = confidence.overall,
        validator_passed  = (validator is None or len(validator.criticals) == 0),
        critical_findings = len(validator.criticals) if validator else 0,
        operations        = tuple(ops),
        summary           = summary,
        generated_at      = datetime.utcnow().isoformat() + "Z",
    )


# ──────────────────────────────────────────────────────────────────────────────
# Stage 8 — Atomic commit
# ──────────────────────────────────────────────────────────────────────────────

def _snap_day_to_db_dict(day: _SnapshotDay) -> dict:
    """Convert a _SnapshotDay to a dict of PortfolioSnapshot column values."""
    return {
        "total_value":              day.total_value,
        "cash_balance":             day.cash_balance,
        "total_invested":           day.total_invested,
        "unrealized_pnl":           day.unrealized_pnl,
        "unrealized_pnl_pct":       day.unrealized_pnl_pct,
        "realized_pnl":             day.realized_pnl,
        "daily_return_pct":         day.daily_return_pct,
        "net_external_cash_flow":   day.net_external_cash_flow,
        "investment_return_pct":    day.investment_return_pct,
        "investment_return_amount": day.investment_return_amount,
        "imported_asset_value":     day.imported_asset_value,
        "manual_adjustment_value":  day.manual_adjustment_value,
        "period_realized_pnl":      day.period_realized_pnl,
        "period_dividend_income":   day.period_dividend_income,
        "period_fees_paid":         day.period_fees_paid,
        "sector_breakdown_json":    day.sector_breakdown_json,
        "holdings_json":            day.holdings_json,
        "holdings_count":           day.holdings_count,
    }


def _commit_rebuild(
    db:             Session,
    portfolio_id:   int,
    workspace_id:   int,
    portfolio:      Portfolio,
    final_state:    _PortfolioState,
    snapshot_days:  list[_SnapshotDay],
    skip_snapshots: bool,
) -> None:
    """Write the reconstructed state to the database atomically.

    Caller is responsible for calling db.commit() / db.rollback().
    This function performs NO commit — it only stages ORM changes.
    """
    # ── 1. Update Portfolio.cash_balance ─────────────────────────────────────
    portfolio.cash_balance = _f(final_state.cash_balance)

    # ── 2. Replace PortfolioItem rows ─────────────────────────────────────────
    # Preserve user-configurable allow_swap before deleting
    allow_swap_map: dict[str, bool] = {
        item.symbol: item.allow_swap
        for item in db.query(PortfolioItem).filter_by(portfolio_id=portfolio_id).all()
    }

    db.query(PortfolioItem).filter_by(portfolio_id=portfolio_id).delete(
        synchronize_session=False
    )

    for sym, h in final_state.holdings.items():
        db.add(PortfolioItem(
            workspace_id = workspace_id,
            portfolio_id = portfolio_id,
            symbol       = sym,
            shares       = _f(h.shares),
            avg_cost     = _f(h.avg_cost),
            sector       = h.sector,
            allow_swap   = allow_swap_map.get(sym, True),
        ))

    # ── 3. Upsert snapshot rows ────────────────────────────────────────────────
    if not skip_snapshots:
        for day in snapshot_days:
            if day.holdings_count > 0 and day.price_coverage < _COVERAGE_THRESHOLD:
                _log.warning(
                    "rebuild: snapshot %s coverage=%.0f%% < %.0f%% — writing anyway "
                    "(price_missing=True for affected holdings)",
                    day.snapshot_date,
                    day.price_coverage * 100,
                    _COVERAGE_THRESHOLD * 100,
                )

            # ── FORENSIC COMMIT PRE-WRITE ─────────────────────────────────
            existing  = (
                db.query(PortfolioSnapshot)
                .filter_by(portfolio_id=portfolio_id, snapshot_date=day.snapshot_date)
                .first()
            )
            print(
                f"[FORENSIC COMMIT PRE]  snap_date={day.snapshot_date}"
                f"  {'existing.id=' + str(existing.id) if existing else 'INSERT'}"
                f"  total_value={day.total_value}"
                f"  cash={day.cash_balance}"
                f"  holdings_count={day.holdings_count}"
                f"  holdings_json[:500]={day.holdings_json[:500]}"
            )
            snap_data = _snap_day_to_db_dict(day)
            if existing:
                for k, v in snap_data.items():
                    setattr(existing, k, v)
                # ── FORENSIC COMMIT POST-SETATTR ──────────────────────────
                print(
                    f"[FORENSIC COMMIT POST] snap_date={existing.snapshot_date}"
                    f"  total_value={existing.total_value}"
                    f"  cash={existing.cash_balance}"
                    f"  holdings_json[:500]={str(existing.holdings_json)[:500]}"
                )
            else:
                db.add(PortfolioSnapshot(
                    workspace_id  = workspace_id,
                    portfolio_id  = portfolio_id,
                    snapshot_date = day.snapshot_date,
                    **snap_data,
                ))


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

async def rebuild_portfolio(
    db:             Session,
    portfolio_id:   int,
    workspace_id:   int,
    from_date:      str | None = None,
    skip_snapshots: bool       = False,
    skip_benchmark: bool       = False,   # reserved for future benchmark series rebuild
    dry_run:        bool       = False,
    backup:         bool       = False,
    apply_repairs:  bool       = True,
    progress_cb:    Callable[[str], None] | None = None,
) -> RebuildResult:
    """Rebuild a portfolio from its transaction ledger.

    Stages
    ------
    1. Replay all transactions → final cash + holdings + realized P/L
       When apply_repairs=True, loads active LedgerRepair rows and applies
       apply_repair_overlay() before replay so excluded transactions are
       invisible to every downstream stage.
    2. Reconstruct historical portfolio state at each existing snapshot date
    3. Recalculate return metrics for each snapshot
    4. Generate a reconciliation report (current DB vs reconstructed)
    5. Run ledger validator — abort commit if any CRITICAL finding is present
       + compute multi-dimensional ConfidenceReport
       When apply_repairs=True, validates the effective ledger (mode="effective").
    6. Generate the execution plan (deterministic, read-only list of DB changes)
    7. Export pre-rebuild backup (when backup=True and not dry_run)
       — backup failure aborts the commit
    8. Commit (atomically) unless dry_run=True or Stage 5 aborted

    Args:
        db:             SQLAlchemy session (caller manages lifecycle).
        portfolio_id:   ID of the portfolio to rebuild.
        workspace_id:   Owning workspace ID.
        from_date:      "YYYY-MM-DD".  Only rebuild snapshots on/after this date.
                        Stage 1 (final state) always replays all transactions.
        skip_snapshots: Skip Stages 2–3 (only rebuild portfolio items + cash).
        skip_benchmark: (reserved) Skip benchmark series regeneration.
        dry_run:        Run all stages but do not write to the database.
        backup:         Export existing rows to JSON before committing (Stage 7).
                        If the export fails, the commit is aborted.
        apply_repairs:  When True (default), load active LedgerRepair rows and
                        apply the repair overlay before replay.  Excluded
                        transactions are omitted from every downstream stage
                        including validation and confidence scoring.
                        When False, behaviour is identical to Phase 6.7B.
        progress_cb:    Optional callable(message) for progress reporting.

    Returns:
        RebuildResult with per-stage statistics, reconciliation report,
        multi-dimensional ConfidenceReport, and execution plan.
        result.aborted=True means a CRITICAL ledger finding or backup failure
        blocked the commit.
    """
    t_start = time.monotonic()

    def _progress(msg: str) -> None:
        if progress_cb:
            progress_cb(msg)
        _log.info("rebuild portfolio=%d: %s", portfolio_id, msg)

    # ── Load portfolio ────────────────────────────────────────────────────────
    portfolio = (
        db.query(Portfolio)
        .filter_by(id=portfolio_id, workspace_id=workspace_id)
        .first()
    )
    if not portfolio:
        return RebuildResult(
            portfolio_id   = portfolio_id,
            portfolio_name = "?",
            success        = False,
            error          = f"Portfolio {portfolio_id} not found in workspace {workspace_id}",
        )

    result = RebuildResult(
        portfolio_id   = portfolio_id,
        portfolio_name = portfolio.name,
        success        = False,
        dry_run        = dry_run,
        from_date      = from_date,
        skip_snapshots = skip_snapshots,
    )

    try:
        # ── Load all transactions ──────────────────────────────────────────────
        raw_txs: list[Transaction] = (
            db.query(Transaction)
            .filter_by(portfolio_id=portfolio_id)
            .order_by(Transaction.transaction_date, Transaction.id)
            .all()
        )

        if not raw_txs:
            result.error = "No transactions found — nothing to rebuild"
            return result

        canonical_txs: list[CanonicalTransaction] = list(canonicalize_transactions(raw_txs))
        raw_canonical_count = len(canonical_txs)

        # ── Repair overlay (Phase 6.7C) ────────────────────────────────────────
        active_repairs: list = []
        if apply_repairs:
            active_repairs = load_active_repairs(db, portfolio_id)
            if active_repairs:
                effective_tuple, provenance_map = apply_repair_overlay(
                    tuple(canonical_txs), active_repairs
                )
                excluded_count = sum(
                    1 for v in provenance_map.values() if v == "EXCLUDED"
                )
                all_txs = list(effective_tuple)
                result.repairs_applied            = excluded_count
                result.excluded_transaction_count = excluded_count
                result.repair_ids                 = [r.id for r in active_repairs]
                excluded_tx_ids = sorted(
                    tx_id for tx_id, prov in provenance_map.items()
                    if prov == "EXCLUDED"
                )
                # Phase 6.7G diagnostic — printed unconditionally so the
                # effective-ledger state is always visible before replay.
                print(
                    f"[PIPELINE] raw={raw_canonical_count}  "
                    f"repairs(rows)={len(active_repairs)}  "
                    f"excluded={excluded_count}  "
                    f"effective={len(all_txs)}"
                )
                if excluded_tx_ids:
                    print(f"[PIPELINE] excluded tx IDs: {excluded_tx_ids}")
                if excluded_count:
                    _progress(
                        f"Stage 1: overlay applied — "
                        f"raw={raw_canonical_count}  "
                        f"repairs_applied={excluded_count}  "
                        f"effective={len(all_txs)}"
                    )
            else:
                all_txs = canonical_txs
        else:
            all_txs = canonical_txs

        result.effective_transaction_count = len(all_txs)
        result.transactions_replayed = len(all_txs)
        _progress(f"Stage 1: replaying {len(all_txs)} transactions...")

        # ── Stage 1: single-pass replay → final state ─────────────────────────
        final_state = _PortfolioState(Decimal("0"), {}, Decimal("0"))
        for ctx in all_txs:
            _apply_transaction(final_state, ctx)

        result.reconstructed_holdings_count = len(final_state.holdings)
        result.reconstructed_cash           = _f(final_state.cash_balance)
        _progress(
            f"  → cash={result.reconstructed_cash:,.2f}  "
            f"holdings={result.reconstructed_holdings_count}"
        )

        # ── Stages 2–3: historical snapshots ──────────────────────────────────
        snapshot_days: list[_SnapshotDay] = []

        if not skip_snapshots:
            existing_snaps: list[PortfolioSnapshot] = (
                db.query(PortfolioSnapshot)
                .filter_by(portfolio_id=portfolio_id)
                .order_by(PortfolioSnapshot.snapshot_date)
                .all()
            )

            if from_date:
                rebuild_dates  = [s.snapshot_date for s in existing_snaps
                                   if s.snapshot_date >= from_date]
                prev_db_snap   = next(
                    (s for s in reversed(existing_snaps) if s.snapshot_date < from_date),
                    None,
                )
            else:
                rebuild_dates = [s.snapshot_date for s in existing_snaps]
                prev_db_snap  = None

            if not rebuild_dates:
                _progress("  → no snapshot dates in rebuild window; skipping Stages 2–3")
            else:
                _progress(
                    f"Stage 2: rebuilding {len(rebuild_dates)} snapshots "
                    f"({rebuild_dates[0]} → {rebuild_dates[-1]})..."
                )

                # Collect all symbols that appear in the rebuild window
                all_symbols: set[str] = set(final_state.holdings)
                for snap in existing_snaps:
                    if snap.snapshot_date in set(rebuild_dates) and snap.holdings_json:
                        try:
                            for h in json.loads(snap.holdings_json):
                                sym = h.get("symbol")
                                if sym:
                                    all_symbols.add(sym)
                        except (ValueError, TypeError):
                            pass

                _progress(
                    f"  → fetching historical prices for {len(all_symbols)} symbol(s)..."
                )
                print(sorted(all_symbols))
                price_matrix = await _build_price_matrix(
                    symbols     = sorted(all_symbols),
                    dates       = rebuild_dates,
                    progress_cb = lambda sym: _progress(f"    price: {sym}"),
                )
                print(">>> BUILD PRICE MATRIX FINISHED <<<")

                # Replay transactions to get portfolio state at each snapshot date
                _progress("  → replaying transactions for each snapshot date...")
                state_by_date = _replay_with_date_snapshots(all_txs, rebuild_dates)

                # Build _SnapshotDay objects with NAV + return fields
                prev_snap_day: _SnapshotDay | None = None
                print("===== BEFORE LOOP =====")
                for snap_date in rebuild_dates:
                    print("LOOP", snap_date)
                    state_at = state_by_date.get(snap_date)
                    if state_at is None:
                        _log.warning(
                            "rebuild: no state for portfolio=%d date=%s",
                            portfolio_id, snap_date,
                        )
                        continue

                    price_row = {
                        sym: price_matrix.get(sym, {}).get(snap_date)
                        for sym in state_at.holdings
                    }
                    print("=" * 80)
                    print("SNAP DATE:", snap_date)
                    print("PRICE ROW:")
                    for s in ("AAPL01.BK", "AMZN01.BK", "BH.BK"):
                        print(s, "=>", price_row.get(s))

                    # Determine the "previous" for return calculation
                    if prev_snap_day is not None:
                        prev_date = prev_snap_day.snapshot_date
                        prev_nav  = prev_snap_day.total_value
                    elif prev_db_snap is not None:
                        prev_date = prev_db_snap.snapshot_date
                        prev_nav  = prev_db_snap.total_value
                    else:
                        prev_date = None
                        prev_nav  = None

                    # ── FORENSIC PRE-BUILD ────────────────────────────────────
                    print("=" * 80)
                    print("PRICE ROW", snap_date)

                    for s in ("AAPL01.BK", "AMZN01.BK", "BH.BK"):
                        print(
                            s,
                            price_row.get(s),
                        )
                    print(
                        f"[FORENSIC PRE-BUILD]  snap_date={snap_date}"
                        f"  n_holdings={len(state_at.holdings)}"
                        f"  holdings={sorted(state_at.holdings.keys())}"
                        f"  id(state)={id(state_at)}"
                    )
                    print("CALL _build_snapshot_day", snap_date)
                    day = _build_snapshot_day(
                        snapshot_date = snap_date,
                        state         = state_at,
                        price_row     = price_row,
                        all_txs       = all_txs,
                        prev_date     = prev_date,
                        prev_nav      = prev_nav,
                    )
                    if snap_date == "2026-05-26":
                        print("=" * 80)
                        print("PRICE ROW DEBUG")

                        for s in ("AAPL01.BK", "AMZN01.BK", "BH.BK"):
                            print(
                                s,
                                "matrix=",
                                price_matrix.get(s, {}).get(snap_date),
                                "row=",
                                price_row.get(s),
                            )
                    # ── FORENSIC POST-BUILD ───────────────────────────────────
                    print(
                        f"[FORENSIC POST-BUILD] snap_date={day.snapshot_date}"
                        f"  holdings_count={day.holdings_count}"
                        f"  id(day)={id(day)}"
                        f"  holdings_json[:500]={day.holdings_json[:500]}"
                    )

                    snapshot_days.append(day)
                    prev_snap_day = day
                    # Once we have our first reconstructed snapshot, drop the DB baseline
                    if prev_db_snap is not None:
                        prev_db_snap = None

                result.snapshots_processed            = len(snapshot_days)
                result.snapshots_skipped_low_coverage = sum(
                    1 for d in snapshot_days
                    if d.holdings_count > 0 and d.price_coverage < _COVERAGE_THRESHOLD
                )
                _progress(
                    f"  → processed {result.snapshots_processed} snapshot(s), "
                    f"{result.snapshots_skipped_low_coverage} with low coverage"
                )

        # ── Stage 4: reconciliation ───────────────────────────────────────────
        _progress("Stage 4: reconciling...")

        recon_rows: list[ReconciliationRow] = []
        recon_rows.extend(_reconcile_portfolio_items(db, portfolio_id, final_state))
        if not skip_snapshots and snapshot_days:
            recon_rows.extend(
                _reconcile_snapshots(db, portfolio_id, snapshot_days, from_date)
            )

        result.reconciliation_report = recon_rows

        item_rows = [r for r in recon_rows if r.entity_type == "portfolio_item"]
        snap_rows = [r for r in recon_rows if r.entity_type == "snapshot"]

        result.items_matched    = sum(1 for r in item_rows if r.status == ReconciliationStatus.MATCH)
        result.items_different  = sum(1 for r in item_rows if r.status == ReconciliationStatus.DIFFERENT)
        result.items_missing    = sum(1 for r in item_rows if r.status == ReconciliationStatus.MISSING)
        result.items_extra      = sum(1 for r in item_rows if r.status == ReconciliationStatus.EXTRA)

        result.snapshots_matched   = sum(1 for r in snap_rows if r.status == ReconciliationStatus.MATCH)
        result.snapshots_different = sum(1 for r in snap_rows if r.status == ReconciliationStatus.DIFFERENT)
        result.snapshots_missing   = sum(1 for r in snap_rows if r.status == ReconciliationStatus.MISSING)
        result.snapshots_extra     = sum(1 for r in snap_rows if r.status == ReconciliationStatus.EXTRA)

        # ── Stage 5: ledger validation gate ───────────────────────────────────
        _progress("Stage 5: validating ledger...")
        if apply_repairs:
            validation_report = await validate_portfolio_ledger(
                db           = db,
                portfolio_id = portfolio_id,
                workspace_id = workspace_id,
                repairs      = active_repairs,
                mode         = "effective",
            )
        else:
            validation_report = await validate_portfolio_ledger(
                db           = db,
                portfolio_id = portfolio_id,
                workspace_id = workspace_id,
            )
        result.validator_report  = validation_report
        result.ledger_criticals  = len(validation_report.criticals)
        result.ledger_errors     = len(validation_report.errors)
        result.ledger_warnings   = len(validation_report.warnings)

        if result.ledger_criticals > 0:
            result.aborted = True
            _progress(
                f"  → ABORTED: {result.ledger_criticals} CRITICAL finding(s) — "
                "commit blocked until ledger is corrected"
            )
        else:
            _progress(
                f"  → clean  (C={result.ledger_criticals} "
                f"E={result.ledger_errors} "
                f"W={result.ledger_warnings})"
            )

        # ── Stage 5 (cont.): confidence report ────────────────────────────────
        conf_report = _compute_confidence_report(result, snapshot_days)
        result.confidence_report = conf_report
        result.confidence_score  = conf_report.overall
        _progress(
            f"  → confidence {conf_report.overall:.1f}%  "
            f"(replay={conf_report.replay_confidence:.0f}% "
            f"ledger={conf_report.ledger_integrity:.0f}% "
            f"coverage={conf_report.historical_coverage:.0f}% "
            f"consistency={conf_report.snapshot_consistency:.0f}% "
            f"validator={conf_report.validator_confidence:.0f}%)"
        )

        # ── Stage 6: execution plan ────────────────────────────────────────────
        _progress("Stage 6: generating execution plan...")
        if result.excluded_transaction_count > 0:
            _progress(
                f"  → transaction summary  "
                f"raw={raw_canonical_count}  "
                f"repairs_applied={result.repairs_applied}  "
                f"effective={result.effective_transaction_count}"
            )
        exec_plan = _generate_execution_plan(
            db             = db,
            portfolio_id   = portfolio_id,
            portfolio      = portfolio,
            final_state    = final_state,
            snapshot_days  = snapshot_days,
            from_date      = from_date,
            confidence     = conf_report,
            validator      = result.validator_report,
            skip_snapshots = skip_snapshots,
        )
        result.execution_plan = exec_plan
        s = exec_plan.summary
        _progress(
            f"  → {s.total_write_operations} write operation(s) planned  "
            f"(items: +{s.item_inserts} ~{s.item_updates} -{s.item_deletes}  "
            f"snapshots: +{s.snapshot_inserts} ~{s.snapshot_updates})"
        )

        # ── Stage 7: pre-commit backup ─────────────────────────────────────────
        if backup and not dry_run and not result.aborted:
            _progress("Stage 7: exporting backup...")
            try:
                result.backup_path = _export_backup(db, portfolio_id)
                _progress(f"  → backup written: {result.backup_path}")
            except Exception as backup_exc:
                _log.error(
                    "rebuild backup failed portfolio=%d: %s", portfolio_id, backup_exc
                )
                result.aborted = True
                result.error   = f"Backup failed (commit aborted): {backup_exc}"
                _progress(f"  → ABORTED: backup failed: {backup_exc}")

        # ── Stage 8: atomic commit ─────────────────────────────────────────────
        if not dry_run and not result.aborted:
            _progress("Stage 8: committing...")
            try:
                _commit_rebuild(
                    db             = db,
                    portfolio_id   = portfolio_id,
                    workspace_id   = workspace_id,
                    portfolio      = portfolio,
                    final_state    = final_state,
                    snapshot_days  = snapshot_days,
                    skip_snapshots = skip_snapshots,
                )
                db.commit()
                result.committed = True
                _progress("  → committed successfully")
            except Exception as commit_exc:
                db.rollback()
                result.error = f"Commit failed (rolled back): {commit_exc}"
                _log.exception(
                    "rebuild commit failed portfolio=%d", portfolio_id
                )
                return result
        elif result.aborted:
            _progress("  → skipped: CRITICAL validator findings or backup failure blocked commit")
        else:
            _progress("  → dry-run: no database changes written")

        result.success = True

    except Exception as exc:
        _log.exception("rebuild_portfolio failed portfolio=%d", portfolio_id)
        result.error = str(exc)
        if not dry_run:
            try:
                db.rollback()
            except Exception:
                pass

    finally:
        result.elapsed_seconds = time.monotonic() - t_start

    return result


async def rebuild_all_portfolios(
    db:             Session,
    workspace_id:   int,
    from_date:      str | None = None,
    skip_snapshots: bool       = False,
    skip_benchmark: bool       = False,
    dry_run:        bool       = False,
    backup:         bool       = False,
    apply_repairs:  bool       = True,
    progress_cb:    Callable[[int, str, str], None] | None = None,
) -> list[RebuildResult]:
    """Rebuild every portfolio in a workspace.

    Args:
        apply_repairs:  Passed through to rebuild_portfolio().  When True
                        (default), active LedgerRepair rows are applied as an
                        overlay before each portfolio is replayed.
        progress_cb: Optional callable(portfolio_id, portfolio_name, message).
    """
    portfolios = (
        db.query(Portfolio)
        .filter_by(workspace_id=workspace_id)
        .order_by(Portfolio.id)
        .all()
    )

    if not portfolios:
        _log.warning("rebuild_all: no portfolios found in workspace %d", workspace_id)
        return []

    results: list[RebuildResult] = []

    for p in portfolios:
        _log.info("rebuild_all: starting portfolio=%d name=%s", p.id, p.name)

        def _cb(msg: str) -> None:
            if progress_cb:
                progress_cb(p.id, p.name, msg)

        r = await rebuild_portfolio(
            db             = db,
            portfolio_id   = p.id,
            workspace_id   = workspace_id,
            from_date      = from_date,
            skip_snapshots = skip_snapshots,
            skip_benchmark = skip_benchmark,
            dry_run        = dry_run,
            backup         = backup,
            apply_repairs  = apply_repairs,
            progress_cb    = _cb,
        )
        results.append(r)

    return results
