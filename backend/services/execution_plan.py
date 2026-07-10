"""Phase UX.2E — Execution Plan Generator.

Pure service — reads DB, makes no mutations, no AI calls.
Bridges the gap between optimizer analysis and actual trade execution by
identifying funding sources (SELL/REDUCE existing holdings) and sizing
buy targets using the position sizing output already computed.

See OPTIMIZER_PHILOSOPHY.md §9 (Reason vs. Execution Role) and §10 (Funding
Philosophy) — a sale here is never justified "to fund" a purchase.

Public API
----------
build_execution_plan(portfolio_id, workspace_id, buy_symbols,
                     sizing_suggestions, timing_scores, db)
    -> ExecutionPlanResult
"""
from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import Session

from services.funding_source_analysis import (
    FundingSourceResult,
    build_funding_sources,
)

log = logging.getLogger(__name__)


# ── Response models ────────────────────────────────────────────────────────────

class FundingAction(BaseModel):
    action: str                   # "SELL" | "REDUCE"
    symbol: str
    current_shares: float
    current_value: float          # avg_cost × shares (estimated, no live price)
    release_pct: float            # fraction of the position actually released today
    estimated_cash_release: float
    full_recommended_amount: float | None = None   # this trade's own full planned release
    necessity: str | None = None                   # "NECESSARY" | "DISCRETIONARY"
    execution_state: str | None = None             # "FULL" | "SCALED" | "DEFERRED"
    note: str | None = None                        # human explanation


class BuyAction(BaseModel):
    symbol: str
    signal: str
    allocation_pct: float         # % of total portfolio
    estimated_amount: float       # allocation_pct × total_value / 100
    timing_score: int | None


class CashSummary(BaseModel):
    total_value: float
    cash_before: float
    cash_released: float
    total_deployable: float
    total_deployed: float
    cash_remaining: float


class ExecutionPlanResult(BaseModel):
    funding_actions: list[FundingAction]
    deferred_funding_actions: list[FundingAction] = []  # discretionary trades not needed today
    buy_actions: list[BuyAction]
    cash_summary: CashSummary
    status: str                      # "READY" | "INSUFFICIENT" | "NO_SELLS_NEEDED"
    warnings: list[str]
    funding_breakdown: FundingSourceResult | None = None  # UX.2L structured flow


# ── Main entry point ───────────────────────────────────────────────────────────

def build_execution_plan(
    portfolio_id: int,
    workspace_id: int,
    buy_symbols: list[str],
    sizing_suggestions: list[dict[str, Any]],
    timing_scores: dict[str, int] | None,
    db: Session,
) -> ExecutionPlanResult:
    """Build a ready-to-execute trade plan from existing analysis results.

    Args:
        portfolio_id:       Target portfolio.
        workspace_id:       Active workspace.
        buy_symbols:        Symbols that passed the timing gate (to BUY).
        sizing_suggestions: Raw PositionSuggestion dicts from position_sizing output.
        timing_scores:      {symbol: score} used to annotate buy actions.
        db:                 SQLAlchemy session.
    """
    from models.database import AnalysisCache, Portfolio, PortfolioItem
    from services.registry_symbol_matching import match_known_symbols

    portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.id == portfolio_id, Portfolio.workspace_id == workspace_id)
        .first()
    )
    if not portfolio:
        raise ValueError(f"Portfolio {portfolio_id} not found")

    portfolio_items = (
        db.query(PortfolioItem)
        .filter(
            PortfolioItem.portfolio_id == portfolio_id,
            PortfolioItem.workspace_id == workspace_id,
        )
        .all()
    )

    # ── Portfolio value (no live prices — avg_cost × shares) ──────────────────
    cash = float(portfolio.cash_balance or 0.0)
    item_values: dict[str, float] = {
        item.symbol: float(item.avg_cost) * float(item.shares)
        for item in portfolio_items
    }
    total_value = cash + sum(item_values.values())

    # ── Signal lookup for existing holdings ────────────────────────────────────
    # bk_variants keeps the SQL filter wide enough to catch a row stored under
    # the alternate spelling; the actual holding-symbol -> row matching
    # decision is Registry-backed (services/registry_symbol_matching.py).
    holding_symbols = [item.symbol for item in portfolio_items]
    bk_variants = {f"{s}.BK" for s in holding_symbols if "." not in s}
    cache_rows = (
        db.query(AnalysisCache)
        .filter(
            AnalysisCache.workspace_id == workspace_id,
            AnalysisCache.symbol.in_(list(set(holding_symbols) | bk_variants)),
        )
        .all()
    )
    cache_row_by_symbol: dict[str, AnalysisCache] = {r.symbol: r for r in cache_rows}
    signal_matched = match_known_symbols(db, holding_symbols, cache_row_by_symbol.keys())
    signal_map: dict[str, str] = {
        holding_sym: (cache_row_by_symbol[matched].signal or "HOLD").upper()
        for holding_sym, matched in signal_matched.items()
    }

    buy_set = {s.upper() for s in buy_symbols}

    # ── Buy actions from sizing suggestions (computed first — funding needs
    #    to know the total deployment before it can decide what's actually
    #    necessary to release; see OPTIMIZER_PHILOSOPHY.md §10) ────────────────
    sizing_map = {str(s.get("symbol", "")).upper(): s for s in sizing_suggestions}
    _timing = timing_scores or {}
    buy_actions: list[BuyAction] = []

    for sym in buy_symbols:
        sug = sizing_map.get(sym.upper())
        if not sug:
            continue
        alloc_pct = float(sug.get("suggested_pct", 0.0))
        estimated_amount = round(alloc_pct * total_value / 100.0, 2)
        buy_actions.append(BuyAction(
            symbol=sym,
            signal=str(sug.get("signal", "BUY")).upper(),
            allocation_pct=round(alloc_pct, 4),
            estimated_amount=estimated_amount,
            timing_score=_timing.get(sym),
        ))

    buy_actions.sort(key=lambda ba: -ba.allocation_pct)
    total_deployed = sum(ba.estimated_amount for ba in buy_actions)

    # ── Funding: existing holdings flagged SELL or REDUCE ──────────────────────
    # Execution Optimization (services/optimizer/execution_optimizer.py) decides
    # which of these actually execute today, and how much of each — never an
    # unconditional "every flagged holding becomes a funding action" scan.
    funding_breakdown = build_funding_sources(
        item_values=item_values,
        signal_map=signal_map,
        cash_available=cash,
        buy_set=buy_set,
        total_deployment=total_deployed,
    )

    funding_actions: list[FundingAction] = []
    deferred_funding_actions: list[FundingAction] = []
    for src in (funding_breakdown.sell_sources + funding_breakdown.reduce_sources):
        funding_actions.append(FundingAction(
            action=src.action, symbol=src.symbol,
            current_shares=round(float(next(
                (i.shares for i in portfolio_items if i.symbol == src.symbol), 0.0
            )), 4),
            current_value=src.current_value,
            release_pct=src.release_pct,
            estimated_cash_release=src.estimated_release,
            full_recommended_amount=src.current_value,
            necessity=src.necessity,
            execution_state=src.execution_state,
            note=src.note,
        ))
    for src in funding_breakdown.deferred_sources:
        deferred_funding_actions.append(FundingAction(
            action=src.action, symbol=src.symbol,
            current_shares=round(float(next(
                (i.shares for i in portfolio_items if i.symbol == src.symbol), 0.0
            )), 4),
            current_value=src.current_value,
            release_pct=src.release_pct,
            estimated_cash_release=src.estimated_release,
            full_recommended_amount=src.current_value,
            necessity=src.necessity,
            execution_state=src.execution_state,
            note=src.note,
        ))

    # ── Capital available ──────────────────────────────────────────────────────
    cash_released = funding_breakdown.total_released
    total_deployable = cash + cash_released
    cash_remaining = round(total_deployable - total_deployed, 2)

    # ── Warnings ───────────────────────────────────────────────────────────────
    warnings: list[str] = []
    if cash_remaining < 0:
        warnings.append(
            f"Deployment exceeds available capital by "
            f"{abs(cash_remaining):,.0f} — reduce position sizes or add more funding."
        )
    if total_value > 0 and cash / total_value < 0.03 and not funding_actions:
        warnings.append(
            "Cash below 3% of portfolio — no sell candidates found. "
            "Reduce existing positions before deploying."
        )

    # ── Status ─────────────────────────────────────────────────────────────────
    if cash_remaining < 0:
        status = "INSUFFICIENT"
    elif not funding_actions:
        status = "NO_SELLS_NEEDED"
    else:
        status = "READY"

    return ExecutionPlanResult(
        funding_actions=funding_actions,
        deferred_funding_actions=deferred_funding_actions,
        buy_actions=buy_actions,
        cash_summary=CashSummary(
            total_value=round(total_value, 2),
            cash_before=round(cash, 2),
            cash_released=round(cash_released, 2),
            total_deployable=round(total_deployable, 2),
            total_deployed=round(total_deployed, 2),
            cash_remaining=cash_remaining,
        ),
        status=status,
        warnings=warnings,
        funding_breakdown=funding_breakdown,
    )
