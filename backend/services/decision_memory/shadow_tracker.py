"""shadow_tracker.py — Phase 3B.7 (revised)

Paper-trading valuation engine for ShadowPortfolio rows.

Two shadow types:
  STATIC_FROZEN — Holdings frozen at the moment a UserExecutionDecision was
                  recorded.  Simulates "what would have happened if the user
                  had followed the recommendation exactly."
  ACTIVE_MODEL  — Hypothetical 100%-compliant portfolio rebuilt each time the
                  optimizer runs for the same source portfolio.  Tracks the
                  live frontier of the AI's best guess.

Price source policy
-------------------
All price lookups use AgentCache (technical agent) — never live yfinance
calls.  This means paper valuations stay within the project's existing cache
TTL (15 min for technical data) and never block the daily scheduler with
network I/O.

If a symbol has no AgentCache entry its most-recent inception_price is used,
keeping that holding's contribution frozen until the cache is refreshed by a
normal analysis run.

Public API
----------
value_shadow_portfolio(db, shadow_id) → dict
    Compute today's paper value for one shadow portfolio and append a
    ShadowPortfolioSnapshot row.  Returns a summary dict.

value_all_active_shadows(db, workspace_id) → list[dict]
    Iterate every is_active shadow for the workspace and call
    value_shadow_portfolio.  Intended to be called from the APScheduler
    daily job alongside generate_daily_snapshot.

create_static_frozen_shadow(db, execution_decision_id, workspace_id) → dict
    Build a STATIC_FROZEN shadow from a UserExecutionDecision row.
    Resolves actual shares using AgentCache prices at creation time.

create_active_model_shadow(db, portfolio_id, snapshot_id, workspace_id) → dict
    Build or refresh an ACTIVE_MODEL shadow from the latest optimizer snapshot.
    Resolves actual shares using AgentCache prices at creation time.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, date, timedelta
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_BENCHMARK_SYMBOL = "^GSPC"  # default benchmark; overridden per portfolio currency


# ─── DB-only price helpers ────────────────────────────────────────────────────

def _fetch_cached_prices(db: Session, symbols: list[str]) -> dict[str, float]:
    """Return {symbol: latest_price} using AgentCache.technical — no yfinance calls.

    Parses result_json for 'current_price', 'price', or 'close' keys.
    Symbols without a cache entry are silently omitted; callers fall back to
    inception_price for those holdings.
    """
    from models.database import AgentCache

    prices: dict[str, float] = {}
    if not symbols:
        return prices

    rows = (
        db.query(AgentCache)
        .filter(AgentCache.symbol.in_(symbols), AgentCache.agent == "technical")
        .all()
    )
    for row in rows:
        if not row.result_json:
            continue
        try:
            data = json.loads(row.result_json)
            price = (
                data.get("current_price")
                or data.get("price")
                or data.get("close")
            )
            if price and isinstance(price, (int, float)) and float(price) > 0:
                prices[row.symbol] = float(price)
        except Exception:
            pass

    return prices


def _resolve_shares_from_weights(
    allocations: list[dict],
    total_portfolio_value: float,
    prices: dict[str, float],
) -> list[dict]:
    """Convert target_weight_pct allocations into share counts.

    For each allocation with 'target_weight' (0-100):
      market_value = target_weight / 100 * total_portfolio_value
      shares = market_value / inception_price   (if price available)
      shares = market_value, inception_price = 1.0  (if no price — value frozen)

    Returns a list of holding dicts ready for inception_holdings_json.
    """
    holdings: list[dict] = []
    for a in allocations:
        sym = a.get("symbol")
        if not sym:
            continue
        target_weight = float(a.get("target_weight") or 0)
        market_value = target_weight / 100.0 * total_portfolio_value
        inception_price = prices.get(sym)

        if inception_price and inception_price > 0:
            shares = round(market_value / inception_price, 6)
        else:
            # No price found: store market_value as "units at price 1"
            # so paper value stays frozen at market_value until cache is refreshed.
            shares = round(market_value, 6)
            inception_price = 1.0

        holdings.append({
            "symbol": sym,
            "target_weight_pct": target_weight,
            "action": a.get("action"),
            "shares": shares,
            "inception_price": inception_price,
        })
    return holdings


# ─── Paper valuation ──────────────────────────────────────────────────────────

def _compute_paper_value(
    holdings: list[dict],
    prices: dict[str, float],
) -> tuple[float, list[dict]]:
    """Compute total paper value from inception holdings + cached prices.

    holdings: [{symbol, shares, inception_price, ...}, ...]
    Returns (total_value, enriched_holdings_with_current_value).

    Valuation priority per holding:
      1. shares * cached_current_price  (if both available)
      2. shares * inception_price       (if no fresh price)
      3. 0                              (if shares/inception_price missing)
    """
    total = 0.0
    enriched: list[dict] = []
    for h in holdings:
        sym = h.get("symbol", "")
        shares = float(h.get("shares") or 0)
        inception_price = float(h.get("inception_price") or 0)
        current_price = prices.get(sym) or inception_price
        mv = shares * current_price
        total += mv
        enriched.append({
            **h,
            "current_price": current_price,
            "inception_price": inception_price,
            "market_value": round(mv, 2),
        })
    return total, enriched


def _benchmark_return_pct(
    db: Session,
    benchmark_symbol: str,
    inception_date: str,
    today_str: str,
) -> float | None:
    """Approximate benchmark return since inception using BenchmarkPrice table."""
    from models.database import BenchmarkPrice

    start = (
        db.query(BenchmarkPrice)
        .filter(BenchmarkPrice.symbol == benchmark_symbol, BenchmarkPrice.price_date >= inception_date)
        .order_by(BenchmarkPrice.price_date)
        .first()
    )
    end = (
        db.query(BenchmarkPrice)
        .filter(BenchmarkPrice.symbol == benchmark_symbol, BenchmarkPrice.price_date <= today_str)
        .order_by(BenchmarkPrice.price_date.desc())
        .first()
    )
    if start and end and start.close_price and end.close_price and start.close_price != 0:
        return round((end.close_price - start.close_price) / start.close_price * 100, 4)
    return None


# ─── Core valuation ──────────────────────────────────────────────────────────

def value_shadow_portfolio(db: Session, shadow_id: int) -> dict[str, Any]:
    """Price a shadow portfolio at cached market prices and write a snapshot row."""
    from models.database import ShadowPortfolio, ShadowPortfolioSnapshot

    shadow = db.query(ShadowPortfolio).filter_by(id=shadow_id).first()
    if not shadow:
        return {"error": "shadow_portfolio_not_found", "id": shadow_id}

    today_str = date.today().isoformat()

    # Check idempotency — update existing snapshot rather than duplicate
    existing = (
        db.query(ShadowPortfolioSnapshot)
        .filter_by(shadow_portfolio_id=shadow_id, snapshot_date=today_str)
        .first()
    )

    holdings: list[dict] = []
    try:
        raw = shadow.inception_holdings_json
        if raw:
            holdings = json.loads(raw)
    except Exception:
        pass

    symbols = [h["symbol"] for h in holdings if h.get("symbol")]
    prices = _fetch_cached_prices(db, symbols)
    total_value, enriched = _compute_paper_value(holdings, prices)
    total_value += shadow.paper_cash_balance

    inception_value = shadow.inception_value or total_value
    inception_return_pct = None
    if inception_value and inception_value != 0:
        inception_return_pct = round((total_value - inception_value) / inception_value * 100, 4)

    benchmark_symbol = _BENCHMARK_SYMBOL
    benchmark_ret = _benchmark_return_pct(db, benchmark_symbol, shadow.inception_date, today_str)
    alpha = None
    if inception_return_pct is not None and benchmark_ret is not None:
        alpha = round(inception_return_pct - benchmark_ret, 4)

    # Daily return vs previous snapshot
    daily_return_pct = None
    prev = (
        db.query(ShadowPortfolioSnapshot)
        .filter(
            ShadowPortfolioSnapshot.shadow_portfolio_id == shadow_id,
            ShadowPortfolioSnapshot.snapshot_date < today_str,
        )
        .order_by(ShadowPortfolioSnapshot.snapshot_date.desc())
        .first()
    )
    if prev and prev.total_value and prev.total_value != 0:
        daily_return_pct = round((total_value - prev.total_value) / prev.total_value * 100, 4)

    try:
        if existing:
            existing.total_value = total_value
            existing.return_pct_since_inception = inception_return_pct
            existing.daily_return_pct = daily_return_pct
            existing.holdings_json = json.dumps(enriched, default=str)
            existing.benchmark_symbol = benchmark_symbol
            existing.benchmark_return_pct = benchmark_ret
            existing.alpha = alpha
        else:
            snap = ShadowPortfolioSnapshot(
                shadow_portfolio_id=shadow_id,
                snapshot_date=today_str,
                total_value=total_value,
                return_pct_since_inception=inception_return_pct,
                daily_return_pct=daily_return_pct,
                holdings_json=json.dumps(enriched, default=str),
                benchmark_symbol=benchmark_symbol,
                benchmark_return_pct=benchmark_ret,
                alpha=alpha,
                created_at=datetime.utcnow(),
            )
            db.add(snap)

        shadow.current_value = total_value
        shadow.inception_return_pct = inception_return_pct
        shadow.last_valued_at = datetime.utcnow()
        db.commit()

    except Exception as exc:
        logger.warning("[SHADOW] snapshot write failed for shadow_id=%s: %s", shadow_id, exc)
        db.rollback()

    return {
        "shadow_id": shadow_id,
        "shadow_type": shadow.shadow_type,
        "snapshot_date": today_str,
        "total_value": total_value,
        "inception_return_pct": inception_return_pct,
        "daily_return_pct": daily_return_pct,
        "alpha": alpha,
        "benchmark_symbol": benchmark_symbol,
        "benchmark_return_pct": benchmark_ret,
        "holdings_priced": len([h for h in holdings if prices.get(h.get("symbol", ""))]),
        "holdings_total": len(holdings),
    }


def value_all_active_shadows(db: Session, workspace_id: int) -> list[dict]:
    """Value every active shadow portfolio for the workspace (for the daily job)."""
    from models.database import ShadowPortfolio

    shadows = (
        db.query(ShadowPortfolio)
        .filter_by(workspace_id=workspace_id, is_active=True)
        .all()
    )
    results = []
    for s in shadows:
        try:
            results.append(value_shadow_portfolio(db, s.id))
        except Exception as exc:
            logger.warning("[SHADOW] value_all_active_shadows: shadow_id=%s failed: %s", s.id, exc)
            results.append({"shadow_id": s.id, "error": str(exc)})
    return results


# ─── Factory helpers ──────────────────────────────────────────────────────────

def create_static_frozen_shadow(
    db: Session,
    execution_decision_id: int,
    workspace_id: int,
) -> dict[str, Any]:
    """Create a STATIC_FROZEN shadow from a UserExecutionDecision row.

    Holdings are taken from approved_allocations_json (if APPROVED) or
    the optimizer snapshot's projected_allocations_json.  Actual shares
    are computed from target_weight_pct × total_portfolio_value ÷ price
    using AgentCache prices at creation time — no live yfinance calls.
    """
    from models.database import (
        ShadowPortfolio, UserExecutionDecision, RecommendationSnapshot,
    )

    decision = db.query(UserExecutionDecision).filter_by(id=execution_decision_id).first()
    if not decision:
        return {"error": "decision_not_found"}

    snap = db.query(RecommendationSnapshot).filter_by(
        id=decision.recommendation_snapshot_id
    ).first()

    # Resolve allocations: prefer approved_allocations for APPROVED decisions
    allocs_raw = decision.approved_allocations_json or (
        snap.projected_allocations_json if snap else None
    )
    allocs: list[dict] = []
    if allocs_raw:
        try:
            allocs = json.loads(allocs_raw)
        except Exception:
            pass

    total_portfolio_value = (snap.total_portfolio_value if snap else None) or 0.0

    # Resolve actual shares using AgentCache prices
    symbols = [a.get("symbol") for a in allocs if a.get("symbol")]
    prices = _fetch_cached_prices(db, symbols)
    holdings = _resolve_shares_from_weights(allocs, total_portfolio_value, prices)

    inception_date = date.today().isoformat()

    shadow = ShadowPortfolio(
        workspace_id=workspace_id,
        portfolio_id=decision.portfolio_id,
        shadow_type="STATIC_FROZEN",
        name=f"Frozen @ {inception_date} ({decision.decision})",
        inception_date=inception_date,
        inception_value=total_portfolio_value or None,
        recommendation_snapshot_id=decision.recommendation_snapshot_id,
        execution_decision_id=execution_decision_id,
        inception_holdings_json=json.dumps(holdings, default=str),
        paper_cash_balance=0.0,
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db.add(shadow)
    db.commit()
    db.refresh(shadow)
    logger.info(
        "[SHADOW] Created STATIC_FROZEN id=%s for decision_id=%s (%d holdings, %d priced)",
        shadow.id, execution_decision_id, len(holdings), len([h for h in holdings if prices.get(h["symbol"])]),
    )
    return {
        "shadow_id": shadow.id,
        "shadow_type": "STATIC_FROZEN",
        "inception_date": inception_date,
        "holdings_count": len(holdings),
        "holdings_priced": len([h for h in holdings if prices.get(h["symbol"])]),
    }


def create_active_model_shadow(
    db: Session,
    portfolio_id: int,
    snapshot_id: int,
    workspace_id: int,
) -> dict[str, Any]:
    """Create or refresh an ACTIVE_MODEL shadow from the latest optimizer snapshot.

    If an existing ACTIVE_MODEL shadow for the same portfolio exists, its
    snapshot link and holdings are updated rather than creating a duplicate.
    Shares are computed from target_weight_pct × total_value ÷ AgentCache price.
    """
    from models.database import ShadowPortfolio, RecommendationSnapshot

    snap = db.query(RecommendationSnapshot).filter_by(id=snapshot_id).first()
    if not snap:
        return {"error": "snapshot_not_found"}

    allocs: list[dict] = []
    if snap.projected_allocations_json:
        try:
            allocs = json.loads(snap.projected_allocations_json)
        except Exception:
            pass

    total_portfolio_value = snap.total_portfolio_value or 0.0
    symbols = [a.get("symbol") for a in allocs if a.get("symbol")]
    prices = _fetch_cached_prices(db, symbols)
    holdings = _resolve_shares_from_weights(allocs, total_portfolio_value, prices)

    today_str = date.today().isoformat()
    holdings_json = json.dumps(holdings, default=str)

    existing = (
        db.query(ShadowPortfolio)
        .filter_by(portfolio_id=portfolio_id, shadow_type="ACTIVE_MODEL", is_active=True)
        .order_by(ShadowPortfolio.created_at.desc())
        .first()
    )

    if existing:
        existing.recommendation_snapshot_id = snapshot_id
        existing.inception_holdings_json = holdings_json
        existing.inception_value = total_portfolio_value or None
        existing.inception_date = today_str
        db.commit()
        logger.info(
            "[SHADOW] Refreshed ACTIVE_MODEL id=%s for portfolio_id=%s (%d holdings, %d priced)",
            existing.id, portfolio_id, len(holdings), len([h for h in holdings if prices.get(h["symbol"])]),
        )
        return {
            "shadow_id": existing.id,
            "shadow_type": "ACTIVE_MODEL",
            "action": "refreshed",
            "holdings_count": len(holdings),
            "holdings_priced": len([h for h in holdings if prices.get(h["symbol"])]),
        }

    shadow = ShadowPortfolio(
        workspace_id=workspace_id,
        portfolio_id=portfolio_id,
        shadow_type="ACTIVE_MODEL",
        name=f"Active Model Portfolio ({today_str})",
        inception_date=today_str,
        inception_value=total_portfolio_value or None,
        recommendation_snapshot_id=snapshot_id,
        inception_holdings_json=holdings_json,
        paper_cash_balance=0.0,
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db.add(shadow)
    db.commit()
    db.refresh(shadow)
    logger.info(
        "[SHADOW] Created ACTIVE_MODEL id=%s for portfolio_id=%s (%d holdings, %d priced)",
        shadow.id, portfolio_id, len(holdings), len([h for h in holdings if prices.get(h["symbol"])]),
    )
    return {
        "shadow_id": shadow.id,
        "shadow_type": "ACTIVE_MODEL",
        "action": "created",
        "holdings_count": len(holdings),
        "holdings_priced": len([h for h in holdings if prices.get(h["symbol"])]),
    }
