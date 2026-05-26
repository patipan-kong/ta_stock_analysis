"""shadow_tracker.py — Phase 3B.7 (stabilized, Phase 3B.9S)

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

Fallback chain (per holding):
  1. AgentCache current_price / price / close   (live)
  2. inception_price stored at shadow creation   (frozen)
  3. Skip holding entirely (warn + exclude)      (never zero)

NAV floor guard
---------------
If the total paper NAV collapses to < 1.0 despite inception_value > 0
(all prices temporarily missing), the engine falls back to:
  - Last non-zero ShadowPortfolioSnapshot.total_value
  - Otherwise inception_value itself

This prevents fake -100% inception returns while prices are unavailable.

Price-frozen holdings
---------------------
When a shadow is created and no AgentCache price is available for a symbol,
_resolve_shares_from_weights stores:
    shares = market_value_dollars, inception_price = 1.0, price_frozen = True

In _compute_paper_value, price_frozen=True holdings ALWAYS use inception_price
(1.0), regardless of what AgentCache later contains.  Without this guard,
market_value_dollars × real_price inflates NAV by 100-300×.

Backward-compat: for DB rows written before this patch, holdings with
inception_price == 1.0 and shares > 1000 are inferred as price_frozen.

Public API
----------
value_shadow_portfolio(db, shadow_id) → dict
create_static_frozen_shadow(db, execution_decision_id, workspace_id) → dict
create_active_model_shadow(db, portfolio_id, snapshot_id, workspace_id) → dict
value_all_active_shadows(db, workspace_id) → list[dict]
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, date, timedelta
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_BENCHMARK_SYMBOL = "^GSPC"


# ─── DB-only price helpers ────────────────────────────────────────────────────

def _fetch_cached_prices(db: Session, symbols: list[str]) -> dict[str, float]:
    """Return {symbol: latest_price} using AgentCache.technical — no yfinance calls."""
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


def _get_last_valid_nav(db: Session, shadow_id: int) -> float | None:
    """Return the most recent positive total_value from ShadowPortfolioSnapshot."""
    from models.database import ShadowPortfolioSnapshot

    row = (
        db.query(ShadowPortfolioSnapshot)
        .filter(
            ShadowPortfolioSnapshot.shadow_portfolio_id == shadow_id,
            ShadowPortfolioSnapshot.total_value > 0,
        )
        .order_by(ShadowPortfolioSnapshot.snapshot_date.desc())
        .first()
    )
    return float(row.total_value) if row else None


def _resolve_shares_from_weights(
    allocations: list[dict],
    total_portfolio_value: float,
    prices: dict[str, float],
) -> list[dict]:
    """Convert target_weight_pct allocations into share counts.

    For each allocation:
      market_value = target_weight / 100 * total_portfolio_value
      shares = market_value / inception_price   (if price available)

      If no price is available, stores:
        shares = market_value, inception_price = 1.0, price_frozen = True

      price_frozen=True marks the holding as a "dollar-value" entry whose
      contribution must NOT be re-multiplied by a future live price.
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
            price_frozen = False
        else:
            # No price: freeze market_value as "shares at price 1"
            shares = round(market_value, 6)
            inception_price = 1.0
            price_frozen = True

        holdings.append({
            "symbol": sym,
            "target_weight_pct": target_weight,
            "action": a.get("action"),
            "shares": shares,
            "inception_price": inception_price,
            "price_frozen": price_frozen,
        })
    return holdings


# ─── Paper valuation ──────────────────────────────────────────────────────────

def _compute_paper_value(
    holdings: list[dict],
    prices: dict[str, float],
) -> tuple[float, list[dict]]:
    """Compute total paper value from inception holdings + cached prices.

    Valuation priority per holding:
      1. shares × cached_current_price   (price_frozen=False, cache hit)
      2. shares × inception_price        (price_frozen=True OR cache miss)
      Skip                               (shares ≤ 0, and no valid price at all)

    NEVER multiplies dollar-value "shares" (price_frozen=True) by a live price.
    This prevents 100-300× NAV inflation when prices become cached after creation.

    Backward-compat rule: holdings with inception_price == 1.0 and shares > 1000
    are treated as price_frozen even if the flag is absent (old DB rows).
    """
    total = 0.0
    enriched: list[dict] = []

    for h in holdings:
        sym = h.get("symbol", "")
        shares = float(h.get("shares") or 0)
        inception_price = float(h.get("inception_price") or 0)
        price_frozen = h.get("price_frozen", False)

        # Backward-compat: infer price_frozen for old DB rows
        if not price_frozen and inception_price == 1.0 and shares > 1000:
            price_frozen = True

        if shares <= 0:
            enriched.append({**h, "current_price": inception_price, "market_value": 0.0, "price_source": "zero_shares"})
            continue

        if price_frozen:
            # Dollar-value holding: always frozen at inception_price (1.0)
            current_price = inception_price if inception_price > 0 else 1.0
            price_source = "inception_frozen"
        else:
            cached = prices.get(sym)
            if cached and cached > 0:
                current_price = cached
                price_source = "cached"
            elif inception_price > 0:
                current_price = inception_price
                price_source = "inception_fallback"
            else:
                # No valid price — exclude holding, log warning
                logger.warning(
                    "[SHADOW] No price for %s (shares=%.4f) — excluded from valuation",
                    sym, shares,
                )
                enriched.append({**h, "current_price": None, "market_value": None, "price_source": "missing"})
                continue

        mv = shares * current_price
        total += mv
        enriched.append({
            **h,
            "current_price": current_price,
            "inception_price": inception_price,
            "market_value": round(mv, 2),
            "price_source": price_source,
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
    """Price a shadow portfolio at cached market prices and write a snapshot row.

    NAV floor guard: if computed total_value < 1.0 and inception_value > 0,
    falls back to last valid snapshot NAV or inception_value to prevent
    fake -100% inception returns when prices are temporarily unavailable.

    Return sanity: inception_return_pct is set to None (not shown) when the
    raw computed value exceeds plausible bounds (< -99% or > +1000%).
    """
    from models.database import ShadowPortfolio, ShadowPortfolioSnapshot

    shadow = db.query(ShadowPortfolio).filter_by(id=shadow_id).first()
    if not shadow:
        return {"error": "shadow_portfolio_not_found", "id": shadow_id}

    today_str = date.today().isoformat()

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

    # ── NAV floor guard ────────────────────────────────────────────────────────
    # If total_value collapsed to near zero but we have an inception baseline,
    # use the last known valid NAV rather than reporting -100%.
    inception_value: float | None = shadow.inception_value
    if total_value < 1.0 and (inception_value or 0) > 0:
        last_nav = _get_last_valid_nav(db, shadow_id)
        if last_nav and last_nav > 0:
            total_value = last_nav
            logger.info(
                "[SHADOW] NAV fallback: shadow_id=%s using last valid snapshot %.2f",
                shadow_id, total_value,
            )
        else:
            total_value = inception_value  # type: ignore[assignment]
            logger.info(
                "[SHADOW] NAV fallback: shadow_id=%s using inception_value %.2f",
                shadow_id, total_value,
            )

    # ── Inception value backfill ───────────────────────────────────────────────
    # If inception_value was never set (e.g. total_portfolio_value was 0 at creation),
    # use the first valid total_value we compute.
    if (not inception_value or inception_value <= 0) and total_value > 0:
        inception_value = total_value
        shadow.inception_value = total_value
        logger.info(
            "[SHADOW] Backfilled inception_value=%.2f for shadow_id=%s",
            total_value, shadow_id,
        )

    # ── Inception return ───────────────────────────────────────────────────────
    inception_return_pct: float | None = None
    if inception_value and inception_value > 0 and total_value > 0:
        raw_return = (total_value - inception_value) / inception_value * 100
        # Sanity bounds: suppress clearly corrupted values rather than display -100%
        if -99.9 <= raw_return <= 1000.0:
            inception_return_pct = round(raw_return, 4)
        else:
            logger.warning(
                "[SHADOW] shadow_id=%s inception_return=%.2f%% out of plausible range — suppressed",
                shadow_id, raw_return,
            )

    benchmark_symbol = _BENCHMARK_SYMBOL
    benchmark_ret = _benchmark_return_pct(db, benchmark_symbol, shadow.inception_date, today_str)
    alpha = None
    if inception_return_pct is not None and benchmark_ret is not None:
        alpha = round(inception_return_pct - benchmark_ret, 4)

    # ── Daily return ───────────────────────────────────────────────────────────
    daily_return_pct: float | None = None
    prev = (
        db.query(ShadowPortfolioSnapshot)
        .filter(
            ShadowPortfolioSnapshot.shadow_portfolio_id == shadow_id,
            ShadowPortfolioSnapshot.snapshot_date < today_str,
            ShadowPortfolioSnapshot.total_value > 0,
        )
        .order_by(ShadowPortfolioSnapshot.snapshot_date.desc())
        .first()
    )
    if prev and prev.total_value and prev.total_value > 0 and total_value > 0:
        raw_daily = (total_value - prev.total_value) / prev.total_value * 100
        if -50.0 <= raw_daily <= 50.0:
            daily_return_pct = round(raw_daily, 4)

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

    holdings_priced = len([h for h in enriched if h.get("price_source") in ("cached", "inception_fallback")])
    holdings_frozen = len([h for h in enriched if h.get("price_source") == "inception_frozen"])
    holdings_missing = len([h for h in enriched if h.get("price_source") == "missing"])

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
        "holdings_priced": holdings_priced,
        "holdings_frozen": holdings_frozen,
        "holdings_missing": holdings_missing,
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

    Holdings are resolved in this priority order:
      1. approved_allocations_json from the decision (APPROVED path)
      2. projected_allocations_json from the linked RecommendationSnapshot
      3. Actual PortfolioItem holdings (fallback when optimizer returned NO_ACTION)

    If total_portfolio_value is 0, falls back to actual portfolio market value
    computed from AgentCache prices × PortfolioItem.shares.

    Shares are computed from target_weight_pct × total_value ÷ price.
    When no price is cached, price_frozen=True marks the holding to prevent
    future price-scale corruption.
    """
    from models.database import (
        ShadowPortfolio, UserExecutionDecision, RecommendationSnapshot,
        PortfolioItem,
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

    total_portfolio_value: float = (snap.total_portfolio_value if snap else None) or 0.0

    # Resolve prices early (shared by both allocation path and fallback path)
    alloc_symbols = [a.get("symbol") for a in allocs if a.get("symbol")]
    prices = _fetch_cached_prices(db, alloc_symbols) if alloc_symbols else {}

    # ── Fallback: use actual portfolio holdings when allocations are empty ─────
    if not allocs:
        portfolio_items = (
            db.query(PortfolioItem)
            .filter_by(portfolio_id=decision.portfolio_id)
            .all()
        )
        if portfolio_items:
            item_symbols = [i.symbol for i in portfolio_items]
            item_prices = _fetch_cached_prices(db, item_symbols)

            # Compute total market value for weight calculation
            items_mv: dict[str, float] = {}
            for item in portfolio_items:
                price = item_prices.get(item.symbol) or item.avg_cost or 0.0
                if price > 0 and item.shares and item.shares > 0:
                    items_mv[item.symbol] = price * item.shares

            total_items_value = sum(items_mv.values())

            if total_items_value > 0:
                if total_portfolio_value <= 0:
                    total_portfolio_value = total_items_value
                for item in portfolio_items:
                    mv = items_mv.get(item.symbol, 0)
                    weight = mv / total_portfolio_value * 100 if total_portfolio_value > 0 else 0
                    if weight > 0:
                        allocs.append({
                            "symbol": item.symbol,
                            "target_weight": weight,
                            "action": "HOLD",
                        })
                prices.update(item_prices)
                logger.info(
                    "[SHADOW] create_static_frozen: no optimizer allocations, "
                    "using %d actual portfolio items as baseline (total=%.2f)",
                    len(allocs), total_portfolio_value,
                )

    holdings = _resolve_shares_from_weights(allocs, total_portfolio_value, prices)

    inception_date = date.today().isoformat()

    shadow = ShadowPortfolio(
        workspace_id=workspace_id,
        portfolio_id=decision.portfolio_id,
        shadow_type="STATIC_FROZEN",
        name=f"Frozen @ {inception_date} ({decision.decision})",
        inception_date=inception_date,
        inception_value=total_portfolio_value if total_portfolio_value > 0 else None,
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

    holdings_priced = len([h for h in holdings if not h.get("price_frozen")])
    logger.info(
        "[SHADOW] Created STATIC_FROZEN id=%s for decision_id=%s "
        "(%d holdings, %d priced, %d frozen)",
        shadow.id, execution_decision_id, len(holdings),
        holdings_priced, len(holdings) - holdings_priced,
    )
    return {
        "shadow_id": shadow.id,
        "shadow_type": "STATIC_FROZEN",
        "inception_date": inception_date,
        "holdings_count": len(holdings),
        "holdings_priced": holdings_priced,
        "holdings_frozen": len(holdings) - holdings_priced,
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

    Holdings with no cached price are marked price_frozen=True to prevent
    future NAV inflation when prices become available.
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

    holdings_priced = len([h for h in holdings if not h.get("price_frozen")])

    if existing:
        existing.recommendation_snapshot_id = snapshot_id
        existing.inception_holdings_json = holdings_json
        existing.inception_value = total_portfolio_value if total_portfolio_value > 0 else existing.inception_value
        existing.inception_date = today_str
        db.commit()
        logger.info(
            "[SHADOW] Refreshed ACTIVE_MODEL id=%s for portfolio_id=%s "
            "(%d holdings, %d priced, %d frozen)",
            existing.id, portfolio_id, len(holdings),
            holdings_priced, len(holdings) - holdings_priced,
        )
        return {
            "shadow_id": existing.id,
            "shadow_type": "ACTIVE_MODEL",
            "action": "refreshed",
            "holdings_count": len(holdings),
            "holdings_priced": holdings_priced,
            "holdings_frozen": len(holdings) - holdings_priced,
        }

    shadow = ShadowPortfolio(
        workspace_id=workspace_id,
        portfolio_id=portfolio_id,
        shadow_type="ACTIVE_MODEL",
        name=f"Active Model Portfolio ({today_str})",
        inception_date=today_str,
        inception_value=total_portfolio_value if total_portfolio_value > 0 else None,
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
        "[SHADOW] Created ACTIVE_MODEL id=%s for portfolio_id=%s "
        "(%d holdings, %d priced, %d frozen)",
        shadow.id, portfolio_id, len(holdings),
        holdings_priced, len(holdings) - holdings_priced,
    )
    return {
        "shadow_id": shadow.id,
        "shadow_type": "ACTIVE_MODEL",
        "action": "created",
        "holdings_count": len(holdings),
        "holdings_priced": holdings_priced,
        "holdings_frozen": len(holdings) - holdings_priced,
    }
