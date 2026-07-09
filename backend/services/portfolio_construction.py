"""Phase 4C.5B — Portfolio Construction Assistant.

Determines the largest equal-weight per-symbol allocation that satisfies all
portfolio constraints (sector caps + cash floor).  Reduces step-by-step from
5% down to 1% until a PASS is found.

No AI calls.  No new tables.  No mutations.

Public API
----------
suggest_basket_allocation(portfolio_id, symbols, workspace_id, db)
    -> PortfolioConstructionResult

compute_portfolio_construction(portfolio_id, symbols, symbol_sectors,
                               cash_pct, sector_weights, sector_limits,
                               cash_min_pct, *, start_pct, min_pct, step_pct)
    -> PortfolioConstructionResult       (pure, testable without DB)
"""
from __future__ import annotations

import logging

from pydantic import BaseModel
from sqlalchemy.orm import Session

from services.basket_simulation import (
    BasketSimulationResult,
    _CANONICAL_SECTORS,
    _load_settings,
    _resolve_symbol_sectors,
    compute_basket_simulation,
)

log = logging.getLogger(__name__)

_START_PCT: float = 5.0
_MIN_PCT: float   = 1.0
_STEP_PCT: float  = 1.0


# ── Response models ───────────────────────────────────────────────────────────

class SuggestedBasketAllocation(BaseModel):
    symbol: str
    suggested_pct: float


class PortfolioConstructionResult(BaseModel):
    overall_status: str                   # PASS / WARNING / FAIL
    recommended_allocation_pct: float
    total_deployment_pct: float
    cash_after_pct: float
    allocations: list[SuggestedBasketAllocation]
    reasoning: list[str]
    simulation: BasketSimulationResult    # sector impacts at recommended allocation


# ── Pure evaluator (no DB) ────────────────────────────────────────────────────

def compute_portfolio_construction(
    portfolio_id: int,
    symbols: list[str],
    symbol_sectors: dict[str, str],
    cash_pct: float,
    sector_weights: dict[str, float],
    sector_limits: dict[str, float],
    cash_min_pct: float,
    *,
    start_pct: float = _START_PCT,
    min_pct: float   = _MIN_PCT,
    step_pct: float  = _STEP_PCT,
) -> PortfolioConstructionResult:
    """Determine the largest equal-weight allocation satisfying all constraints.

    Tries start_pct, then decrements by step_pct until a PASS is found or
    allocation_pct falls below min_pct.
    """
    unique_symbols = list(dict.fromkeys(symbols))

    if not unique_symbols:
        empty_sim = compute_basket_simulation(
            portfolio_id, [], {}, 0.0, cash_pct, sector_weights, sector_limits, cash_min_pct,
        )
        return PortfolioConstructionResult(
            overall_status="PASS",
            recommended_allocation_pct=0.0,
            total_deployment_pct=0.0,
            cash_after_pct=round(cash_pct, 2),
            allocations=[],
            reasoning=["No symbols provided."],
            simulation=empty_sim,
        )

    allocation_pct = start_pct
    first_failing_sim: BasketSimulationResult | None = None
    last_sim: BasketSimulationResult | None = None

    while allocation_pct >= min_pct - 1e-9:
        pct = round(allocation_pct, 1)
        sim = compute_basket_simulation(
            portfolio_id=portfolio_id,
            symbols=unique_symbols,
            symbol_sectors=symbol_sectors,
            allocation_pct=pct,
            cash_pct=cash_pct,
            sector_weights=sector_weights,
            sector_limits=sector_limits,
            cash_min_pct=cash_min_pct,
        )
        last_sim = sim

        if sim.overall_status == "PASS":
            reasoning = _build_reasoning_pass(sim, first_failing_sim, start_pct)
            return _build_result(sim, pct, reasoning)

        if first_failing_sim is None:
            first_failing_sim = sim

        allocation_pct = round(allocation_pct - step_pct, 1)

    # No PASS found at any allocation down to min_pct
    assert last_sim is not None
    reasoning: list[str] = [
        f"No viable allocation found — constraints cannot be satisfied "
        f"even at minimum {min_pct:.0f}% per position.",
    ]
    reasoning.extend(last_sim.warnings)
    return _build_result(last_sim, min_pct, reasoning)


# ── DB loader ─────────────────────────────────────────────────────────────────

def suggest_basket_allocation(
    portfolio_id: int,
    symbols: list[str],
    workspace_id: int,
    db: Session,
) -> PortfolioConstructionResult:
    """Load current portfolio state, resolve constraints, find best allocation."""
    from models.database import Portfolio, PortfolioItem, Watchlist
    from services.optimizer.constraint_resolver import effective_sector_cap, resolve_constraints

    symbols = [s.strip().upper() for s in symbols if s.strip()]
    if not symbols:
        return compute_portfolio_construction(
            portfolio_id, [], {}, 100.0, {}, {}, 0.0,
        )

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

    cash = float(portfolio.cash_balance or 0.0)
    item_mvs: dict[str, float] = {
        item.symbol: float(item.avg_cost) * float(item.shares)
        for item in portfolio_items
    }
    total_value = cash + sum(item_mvs.values())
    cash_pct = round(cash / total_value * 100.0, 2) if total_value > 0 else 100.0

    sector_values: dict[str, float] = {}
    for item in portfolio_items:
        sec = item.sector or "Other"
        sector_values[sec] = sector_values.get(sec, 0.0) + item_mvs.get(item.symbol, 0.0)
    sector_weights: dict[str, float] = {
        sec: round(val / total_value * 100.0, 2)
        for sec, val in sector_values.items()
        if total_value > 0
    }

    ps, sector_limit_settings = _load_settings(db, workspace_id)

    regime_ctx: dict | None = None
    try:
        from services.analytics.regime_detector import detect_regime
        regime_ctx = detect_regime(db)
    except Exception:
        pass

    envelope = None
    try:
        envelope = resolve_constraints(ps, sector_limit_settings, regime_ctx, None)
    except Exception as exc:
        log.warning("portfolio_construction: constraint resolver failed: %s", exc)

    cash_min_pct = envelope.effective_cash_min_pct if envelope else 0.0

    if envelope:
        sector_limits_resolved: dict[str, float] = {
            sec: effective_sector_cap(envelope, sec) for sec in _CANONICAL_SECTORS
        }
    else:
        default_cap = float(ps.get("max_sector_pct", 40))
        sector_limits_resolved = {sec: default_cap for sec in _CANONICAL_SECTORS}

    watchlist_items = (
        db.query(Watchlist).filter(Watchlist.workspace_id == workspace_id).all()
    )
    symbol_sectors = _resolve_symbol_sectors(db, symbols, portfolio_items, watchlist_items)

    return compute_portfolio_construction(
        portfolio_id=portfolio_id,
        symbols=symbols,
        symbol_sectors=symbol_sectors,
        cash_pct=cash_pct,
        sector_weights=sector_weights,
        sector_limits=sector_limits_resolved,
        cash_min_pct=cash_min_pct,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_result(
    sim: BasketSimulationResult,
    allocation_pct: float,
    reasoning: list[str],
) -> PortfolioConstructionResult:
    return PortfolioConstructionResult(
        overall_status=sim.overall_status,
        recommended_allocation_pct=allocation_pct,
        total_deployment_pct=round(len(sim.symbols) * allocation_pct, 4),
        cash_after_pct=sim.cash_after_pct,
        allocations=[
            SuggestedBasketAllocation(symbol=sym, suggested_pct=allocation_pct)
            for sym in sim.symbols
        ],
        reasoning=reasoning,
        simulation=sim,
    )


def _build_reasoning_pass(
    sim: BasketSimulationResult,
    first_failing: BasketSimulationResult | None,
    start_pct: float,
) -> list[str]:
    if first_failing is None:
        return [f"{sim.allocation_pct:.0f}% per position satisfies all portfolio constraints."]
    desc = _failure_description(first_failing)
    return [
        f"{start_pct:.0f}% per position {desc}.",
        f"{sim.allocation_pct:.0f}% per position satisfies all portfolio constraints.",
    ]


def _failure_description(sim: BasketSimulationResult) -> str:
    for imp in sim.impacts:
        if imp.status == "FAIL":
            return (
                f"would breach {imp.sector} sector limit "
                f"({imp.after_pct:.1f}% vs {imp.sector_limit_pct:.0f}%)"
            )
    for imp in sim.impacts:
        if imp.status == "WARNING":
            return (
                f"would approach {imp.sector} sector limit "
                f"({imp.after_pct:.1f}% of {imp.sector_limit_pct:.0f}%)"
            )
    if sim.cash_after_pct < 0:
        return "would result in insufficient cash to execute"
    return "would reduce cash below policy minimum"
