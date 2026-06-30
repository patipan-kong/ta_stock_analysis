"""Shared Portfolio Metrics Engine.

The single, canonical implementation of the nine period-return fields that
`portfolio_rebuilder.py`, `portfolio_snapshots.py`, and
`snapshot_return_recovery.py` each used to compute independently. ADR-004
(2026-06-30) mandates exactly one implementation; this module is it.

Pure by construction: no ORM, no database session, no network access, no
logging, no global state. Every caller is responsible for its own window
membership (which transactions belong in "this period") and for fetching
prices — those decisions are engine-specific and stay with the caller (see
`docs/PORTFOLIO_CALCULATION_RULES.md` Section 2 for why `portfolio_snapshots.py`
and `snapshot_return_recovery.py` window on `created_at` while
`portfolio_rebuilder.py` windows on `transaction_date`). This module never
reads either timestamp field.

Canonical formulas
-------------------
  net_external_cash_flow  = sum(DEPOSIT + INITIAL_CASH .total_amount)
                             − sum(WITHDRAW.total_amount)
                             (ledger-derived; ADR-002 — never cash-balance delta)
  imported_asset_value    = sum(shares × price for INITIAL_POSITION)
                             (no duplicate-import dedup — that is a ledger-repair
                             concern, not a snapshot-math concern)
  manual_adjustment_value = sum(signed qty_correction_delta × price
                             for QUANTITY_CORRECTION)
                             (frozen doc Section 7 — fixes the documented
                             downward-correction bug present in 2 of the 3
                             original engines)
  investment_return_pct   = (curr_nav − prev_nav − net_ecf − imported
                             − manual_adj) / prev_nav × 100
  investment_return_amount = the numerator above
  daily_return_pct        = investment_return_pct (kept as a duplicate column;
                             see frozen-doc Open Question #4 — unchanged here)
  period_realized_pnl     = sum(realized_pnl for SELL)
  period_dividend_income  = sum(total_amount for DIVIDEND)
  period_fees_paid        = sum(fees + taxes for BUY, SELL)
  cumulative_realized_pnl = prev_cumulative_realized_pnl + period_realized_pnl

Scope note on cumulative_realized_pnl
--------------------------------------
This field is computed here because it shares the same realized-P&L formula
as `period_realized_pnl`. It is intentionally NOT wired into
`portfolio_snapshots.py`, which still computes `PortfolioSnapshot.realized_pnl`
by summing every SELL transaction ever (unconditionally, even for the baseline
snapshot with no `prev`). Switching that call site to the incremental
`prev + period` formula would silently drop any SELL transactions that
predate the portfolio's tracking history (e.g. backfilled trade history on a
baseline snapshot) — a real correctness risk, not just a refactor. Until that
case is handled deliberately, only `portfolio_rebuilder.py` (replay-state
accumulation, already incremental and already out of this refactor's scope)
and any future caller that can guarantee no pre-tracking SELLs exist should
rely on this field.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from services.transaction_canonicalizer import CanonicalTransaction

_CASH_INFLOW_TYPES  = frozenset({"DEPOSIT", "INITIAL_CASH"})
_CASH_OUTFLOW_TYPES = frozenset({"WITHDRAW"})


@dataclass(frozen=True)
class PeriodMetrics:
    """Result of `compute_period_metrics()` for a single prev → curr period."""

    net_external_cash_flow:    float | None
    imported_asset_value:      float | None
    manual_adjustment_value:   float | None
    investment_return_pct:     float | None
    investment_return_amount:  float | None
    daily_return_pct:          float | None
    period_realized_pnl:       float | None
    period_dividend_income:    float | None
    period_fees_paid:          float | None
    cumulative_realized_pnl:   float


def _round_or_none(value: float, decimals: int = 4) -> float | None:
    """Round a float; return None when the value is zero-ish.

    Matches the pre-existing convention in all three snapshot engines, where
    a zero-valued period field is stored as NULL rather than 0.0.
    """
    return round(value, decimals) if value else None


def compute_period_metrics(
    *,
    curr_nav: float,
    prev_nav: float | None,
    period_transactions: Sequence[CanonicalTransaction],
    price_lookup: Mapping[str, float] | None = None,
    prev_cumulative_realized_pnl: float = 0.0,
) -> PeriodMetrics:
    """Compute all period return-attribution fields.

    Args:
        curr_nav: This period's ending NAV (total_value).
        prev_nav: The prior period's NAV. When None or <= 0,
            investment_return_pct/investment_return_amount/daily_return_pct
            are None — there is no valid prior reference to compute a return
            against. All other fields are still computed from
            `period_transactions` regardless (they do not depend on prev_nav).
        period_transactions: Transactions already filtered to this period's
            window by the caller — this function makes no window-membership
            decision and never reads transaction_date or created_at.
        price_lookup: symbol (raw_symbol) -> price, used to value
            INITIAL_POSITION / QUANTITY_CORRECTION transactions. Falls back
            to the transaction's own price_per_share when a symbol is absent,
            matching every existing engine's fallback behaviour.
        prev_cumulative_realized_pnl: All-time realized P&L as of prev_nav's
            snapshot. Used only to compute `cumulative_realized_pnl` (see the
            module-level scope note before wiring this into a new caller).

    Returns:
        PeriodMetrics with every field computed deterministically from the
        inputs — calling this twice with identical inputs always produces
        identical output.
    """
    price_lookup = price_lookup or {}

    # ── Cash flows (ledger-derived — ADR-002, never cash-balance delta) ───────
    deposits = sum(
        float(ctx.total_amount) for ctx in period_transactions
        if ctx.transaction_type in _CASH_INFLOW_TYPES
    )
    withdrawals = sum(
        float(ctx.total_amount) for ctx in period_transactions
        if ctx.transaction_type in _CASH_OUTFLOW_TYPES
    )
    net_ecf = deposits - withdrawals

    # ── Asset imports (INITIAL_POSITION) — no dedup ───────────────────────────
    imported_asset_value = sum(
        float(ctx.shares) * price_lookup.get(ctx.raw_symbol or "", float(ctx.price_per_share))
        for ctx in period_transactions
        if ctx.transaction_type == "INITIAL_POSITION" and ctx.raw_symbol and ctx.shares > 0
    )

    # ── Quantity corrections (QUANTITY_CORRECTION) — signed ───────────────────
    # A downward correction must strip a NEGATIVE amount (equity left the
    # books without a trade), not abs(delta). Using abs() here previously
    # caused a downward correction to double-subtract: once for the real NAV
    # drop, once again for the (wrongly positive) strip — see
    # docs/PORTFOLIO_CALCULATION_RULES.md Section 7 and
    # docs/DECISION_LOG.md "Signed Manual Adjustment Value Fix".
    manual_adjustment_value = sum(
        float(ctx.qty_correction_delta)
        * price_lookup.get(ctx.raw_symbol or "", float(ctx.price_per_share))
        for ctx in period_transactions
        if ctx.transaction_type == "QUANTITY_CORRECTION" and ctx.raw_symbol
    )

    # ── Period decomposition (transparency only — never stripped from return) ─
    period_realized_pnl    = 0.0
    period_fees_paid       = 0.0
    period_dividend_income = 0.0
    for ctx in period_transactions:
        if ctx.transaction_type == "SELL":
            period_realized_pnl += ctx.realized_pnl if ctx.realized_pnl is not None else 0.0
            period_fees_paid    += float(ctx.fees) + float(ctx.taxes)
        elif ctx.transaction_type == "BUY":
            period_fees_paid += float(ctx.fees) + float(ctx.taxes)
        elif ctx.transaction_type == "DIVIDEND":
            period_dividend_income += float(ctx.total_amount)

    # ── Cash-flow-adjusted return (Modified Dietz, simplified for periods) ────
    investment_return_pct:    float | None = None
    investment_return_amount: float | None = None
    daily_return_pct:         float | None = None
    if prev_nav is not None and prev_nav > 0:
        pure_gain = curr_nav - prev_nav - net_ecf - imported_asset_value - manual_adjustment_value
        investment_return_pct    = round(pure_gain / prev_nav * 100, 4)
        investment_return_amount = round(pure_gain, 4)
        daily_return_pct         = investment_return_pct

    return PeriodMetrics(
        net_external_cash_flow    = _round_or_none(net_ecf),
        imported_asset_value      = _round_or_none(imported_asset_value),
        manual_adjustment_value   = _round_or_none(manual_adjustment_value),
        investment_return_pct     = investment_return_pct,
        investment_return_amount  = investment_return_amount,
        daily_return_pct          = daily_return_pct,
        period_realized_pnl       = _round_or_none(period_realized_pnl),
        period_dividend_income    = _round_or_none(period_dividend_income),
        period_fees_paid          = _round_or_none(period_fees_paid),
        cumulative_realized_pnl   = round(prev_cumulative_realized_pnl + period_realized_pnl, 4),
    )
