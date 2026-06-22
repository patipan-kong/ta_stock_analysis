"""Phase 4C.5A — Basket Simulation Engine.

Deterministic, read-only simulation of purchasing a basket of symbols
against the active portfolio's constraints.

No AI calls.  No new tables.  No mutations.

Public API
----------
simulate_basket(portfolio_id, symbols, allocation_pct, workspace_id, db)
    -> BasketSimulationResult

compute_basket_simulation(portfolio_id, symbols, symbol_sectors, allocation_pct,
                          cash_pct, sector_weights, sector_limits, cash_min_pct)
    -> BasketSimulationResult            (pure, testable without DB)
"""
from __future__ import annotations

import json
import logging

from pydantic import BaseModel
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)

_CANONICAL_SECTORS = frozenset({
    "Technology", "Financial", "Energy", "Healthcare",
    "Consumer", "Industrial", "Real Estate", "Utilities", "Other",
})


# ── Response models ───────────────────────────────────────────────────────────

class BasketImpact(BaseModel):
    sector: str
    before_pct: float
    after_pct: float
    delta_pct: float
    sector_limit_pct: float
    status: str   # PASS / WARNING / FAIL


class BasketSimulationResult(BaseModel):
    portfolio_id: int
    symbols: list[str]
    allocation_pct: float
    total_capital_required_pct: float
    cash_before_pct: float
    cash_after_pct: float
    impacts: list[BasketImpact]
    warnings: list[str]
    overall_status: str   # PASS / WARNING / FAIL


# ── Pure evaluator (no DB) ────────────────────────────────────────────────────

def compute_basket_simulation(
    portfolio_id: int,
    symbols: list[str],
    symbol_sectors: dict[str, str],
    allocation_pct: float,
    cash_pct: float,
    sector_weights: dict[str, float],
    sector_limits: dict[str, float],
    cash_min_pct: float,
) -> BasketSimulationResult:
    """Compute basket impact deterministically.

    Args:
        portfolio_id:   Portfolio ID (threaded through to result)
        symbols:        List of symbols to simulate (duplicates are deduplicated)
        symbol_sectors: Map symbol → sector name
        allocation_pct: Per-symbol allocation as % of total portfolio
        cash_pct:       Current cash as % of total portfolio
        sector_weights: Current sector allocations as % of total portfolio
        sector_limits:  Max allowed % per sector (from resolved constraints)
        cash_min_pct:   Minimum required cash by policy
    """
    unique_symbols = list(dict.fromkeys(symbols))  # deduplicate, preserve order

    # ── Sector deltas: stack per-symbol allocations by sector ─────────────────
    sector_delta: dict[str, float] = {}
    for sym in unique_symbols:
        sector = symbol_sectors.get(sym, "Other")
        sector_delta[sector] = sector_delta.get(sector, 0.0) + allocation_pct

    # ── Cash ──────────────────────────────────────────────────────────────────
    total_capital_required_pct = round(len(unique_symbols) * allocation_pct, 4)
    cash_after_pct = round(cash_pct - total_capital_required_pct, 4)

    # ── Per-sector impact (only sectors touched by the basket) ────────────────
    impacts: list[BasketImpact] = []
    for sector in sorted(sector_delta):
        before = round(sector_weights.get(sector, 0.0), 2)
        delta  = round(sector_delta[sector], 2)
        after  = round(before + delta, 2)
        limit  = round(_sector_limit(sector, sector_limits), 2)
        status = _sector_status(after, limit)
        impacts.append(BasketImpact(
            sector=sector,
            before_pct=before,
            after_pct=after,
            delta_pct=delta,
            sector_limit_pct=limit,
            status=status,
        ))

    # ── Warnings ──────────────────────────────────────────────────────────────
    warnings: list[str] = []
    for imp in impacts:
        if imp.status == "FAIL":
            warnings.append(
                f"{imp.sector} sector exceeds limit "
                f"({imp.after_pct:.1f}% vs {imp.sector_limit_pct:.0f}% limit)"
            )
        elif imp.status == "WARNING":
            warnings.append(
                f"{imp.sector} sector exceeds 80% of limit "
                f"({imp.after_pct:.1f}% of {imp.sector_limit_pct:.0f}%)"
            )

    if cash_after_pct < 0:
        warnings.append("Insufficient cash to execute basket")
    elif cash_after_pct < cash_min_pct:
        warnings.append("Cash reserve falls below minimum threshold")

    # ── Overall status (FAIL > WARNING > PASS) ────────────────────────────────
    statuses = {imp.status for imp in impacts}
    if cash_after_pct < 0 or "FAIL" in statuses:
        overall_status = "FAIL"
    elif cash_after_pct < cash_min_pct or "WARNING" in statuses:
        overall_status = "WARNING"
    else:
        overall_status = "PASS"

    return BasketSimulationResult(
        portfolio_id=portfolio_id,
        symbols=unique_symbols,
        allocation_pct=allocation_pct,
        total_capital_required_pct=total_capital_required_pct,
        cash_before_pct=round(cash_pct, 2),
        cash_after_pct=cash_after_pct,
        impacts=impacts,
        warnings=warnings,
        overall_status=overall_status,
    )


# ── DB loader ─────────────────────────────────────────────────────────────────

def simulate_basket(
    portfolio_id: int,
    symbols: list[str],
    allocation_pct: float,
    workspace_id: int,
    db: Session,
) -> BasketSimulationResult:
    """Load current portfolio state, resolve constraints, run simulation."""
    from models.database import Portfolio, PortfolioItem, Settings, Watchlist
    from services.optimizer.constraint_resolver import (
        effective_sector_cap,
        resolve_constraints,
    )

    symbols = [s.strip().upper() for s in symbols if s.strip()]
    if not symbols:
        return compute_basket_simulation(
            portfolio_id, [], {}, allocation_pct, 100.0, {}, {}, 0.0
        )

    # ── Load portfolio ────────────────────────────────────────────────────────
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

    # ── Market values (avg_cost × shares — no live yfinance to stay fast) ─────
    cash = float(portfolio.cash_balance or 0.0)
    item_mvs: dict[str, float] = {
        item.symbol: float(item.avg_cost) * float(item.shares)
        for item in portfolio_items
    }
    total_value = cash + sum(item_mvs.values())
    cash_pct = round(cash / total_value * 100.0, 2) if total_value > 0 else 100.0

    # ── Sector weights ────────────────────────────────────────────────────────
    sector_values: dict[str, float] = {}
    for item in portfolio_items:
        sec = item.sector or "Other"
        sector_values[sec] = sector_values.get(sec, 0.0) + item_mvs.get(item.symbol, 0.0)

    sector_weights: dict[str, float] = {
        sec: round(val / total_value * 100.0, 2)
        for sec, val in sector_values.items()
        if total_value > 0
    }

    # ── Constraints ───────────────────────────────────────────────────────────
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
        log.warning("basket_simulation: constraint resolver failed: %s", exc)

    cash_min_pct = envelope.effective_cash_min_pct if envelope else 0.0

    if envelope:
        sector_limits_resolved: dict[str, float] = {
            sec: effective_sector_cap(envelope, sec) for sec in _CANONICAL_SECTORS
        }
    else:
        default_cap = float(ps.get("max_sector_pct", 40))
        sector_limits_resolved = {sec: default_cap for sec in _CANONICAL_SECTORS}

    # ── Symbol → sector from DB only (no network) ────────────────────────────
    watchlist_items = (
        db.query(Watchlist).filter(Watchlist.workspace_id == workspace_id).all()
    )
    symbol_sectors = _resolve_symbol_sectors(symbols, portfolio_items, watchlist_items)

    return compute_basket_simulation(
        portfolio_id=portfolio_id,
        symbols=symbols,
        symbol_sectors=symbol_sectors,
        allocation_pct=allocation_pct,
        cash_pct=cash_pct,
        sector_weights=sector_weights,
        sector_limits=sector_limits_resolved,
        cash_min_pct=cash_min_pct,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_settings(db: Session, ws: int) -> tuple[dict, dict]:
    from models.database import Settings
    _DEFAULT_PS: dict = {"max_stocks": 12, "max_sector_pct": 40}
    rows = (
        db.query(Settings)
        .filter(
            Settings.workspace_id == ws,
            Settings.key.in_(["portfolio_settings", "sector_limits"]),
        )
        .all()
    )
    ps: dict = dict(_DEFAULT_PS)
    sector_limits: dict = {}
    for row in rows:
        try:
            parsed = json.loads(row.value)
            if row.key == "portfolio_settings":
                ps = {k: int(v) for k, v in parsed.items() if k in _DEFAULT_PS}
            elif row.key == "sector_limits":
                sector_limits = parsed
        except Exception:
            pass
    return ps, sector_limits


def _resolve_symbol_sectors(
    symbols: list[str],
    portfolio_items: list,
    watchlist_items: list,
) -> dict[str, str]:
    """Map each basket symbol to its sector using DB only (no network calls).

    Priority: portfolio holding → watchlist → "Other"
    Handles .BK suffix mismatch so "BH" matches a holding stored as "BH.BK".
    """
    holdings_sector: dict[str, str] = {}
    for item in portfolio_items:
        if item.sector:
            holdings_sector[item.symbol] = item.sector
            if item.symbol.endswith(".BK"):
                holdings_sector.setdefault(item.symbol[:-3], item.sector)
            else:
                holdings_sector.setdefault(item.symbol + ".BK", item.sector)

    watchlist_sector: dict[str, str] = {}
    for item in watchlist_items:
        if item.sector:
            watchlist_sector[item.symbol] = item.sector
            if item.symbol.endswith(".BK"):
                watchlist_sector.setdefault(item.symbol[:-3], item.sector)

    return {
        sym: (holdings_sector.get(sym) or watchlist_sector.get(sym) or "Other")
        for sym in symbols
    }


def _sector_limit(sector: str, sector_limits: dict[str, float]) -> float:
    return sector_limits.get(sector, sector_limits.get("Other", 40.0))


def _sector_status(after_pct: float, limit: float) -> str:
    if limit <= 0:
        return "PASS"
    if after_pct >= limit:
        return "FAIL"
    if after_pct >= limit * 0.8:
        return "WARNING"
    return "PASS"
