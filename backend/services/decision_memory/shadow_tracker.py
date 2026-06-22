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
repair_shadow_portfolios(db, workspace_id) → list[dict]
reset_active_model_inception(db, workspace_id) → list[dict]
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

def _fetch_snapshot_prices(
    db: Session,
    symbols: list[str],
    on_or_before: str | None = None,
) -> dict[str, float]:
    """Return {symbol: price} from PortfolioSnapshot.holdings_json valuations.

    Portfolio snapshots store per-holding "current_price" written daily at
    17:45 ICT from live yfinance — the most reliable DB-only price source.
    Scans snapshot rows newest-first and keeps the first price seen per
    symbol, so each symbol resolves to its most recent available valuation.
    """
    from models.database import PortfolioSnapshot

    prices: dict[str, float] = {}
    if not symbols:
        return prices
    wanted = set(symbols)

    q = db.query(PortfolioSnapshot.snapshot_date, PortfolioSnapshot.holdings_json).filter(
        PortfolioSnapshot.holdings_json.isnot(None)
    )
    if on_or_before:
        q = q.filter(PortfolioSnapshot.snapshot_date <= on_or_before)
    rows = q.order_by(PortfolioSnapshot.snapshot_date.desc()).limit(200).all()

    for _, holdings_json in rows:
        if not (wanted - prices.keys()):
            break
        try:
            holdings = json.loads(holdings_json)
        except Exception:
            continue
        for h in holdings:
            sym = h.get("symbol")
            price = h.get("current_price")
            if sym in wanted and sym not in prices and price and float(price) > 0:
                prices[sym] = float(price)

    return prices


def _fetch_cached_prices(db: Session, symbols: list[str]) -> dict[str, float]:
    """Return {symbol: latest_price} from DB only — no yfinance calls.

    Source priority per symbol:
      1. AgentCache.technical result_json (current_price / price / close)
      2. PortfolioSnapshot.holdings_json valuation prices (daily close)

    Source 2 matters: the technical agent does not currently store any price
    key in its cache JSON, so without the snapshot fallback every shadow
    holding froze at inception_price and daily_return_pct stayed 0.0 forever.
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

    # Fallback: resolve remaining symbols from daily portfolio snapshot prices
    missing = [s for s in symbols if s not in prices]
    if missing:
        snapshot_prices = _fetch_snapshot_prices(db, missing)
        if snapshot_prices:
            logger.info(
                "[SHADOW] %d/%d prices resolved from portfolio snapshots (AgentCache miss)",
                len(snapshot_prices), len(missing),
            )
        prices.update(snapshot_prices)

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
            existing.recommendation_snapshot_id = shadow.recommendation_snapshot_id
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
                recommendation_snapshot_id=shadow.recommendation_snapshot_id,
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

    On refresh, computes the shadow's own running NAV from current holdings and
    prices before rebalancing — never resets inception_date or inception_value so
    the shadow accumulates a true cumulative track record across optimizer runs.

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

    today_str = date.today().isoformat()
    symbols = [a.get("symbol") for a in allocs if a.get("symbol")]
    prices = _fetch_cached_prices(db, symbols)

    existing = (
        db.query(ShadowPortfolio)
        .filter_by(portfolio_id=portfolio_id, shadow_type="ACTIVE_MODEL", is_active=True)
        .order_by(ShadowPortfolio.created_at.desc())
        .first()
    )

    if existing:
        # Compute shadow's own running NAV from current holdings — never use actual
        # portfolio NAV, which would tether the shadow to deposits/withdrawals.
        old_holdings: list[dict] = []
        try:
            if existing.inception_holdings_json:
                old_holdings = json.loads(existing.inception_holdings_json)
        except Exception:
            pass

        if old_holdings:
            old_syms = [h["symbol"] for h in old_holdings if h.get("symbol")]
            old_prices = _fetch_cached_prices(db, old_syms)
            running_nav, _ = _compute_paper_value(old_holdings, old_prices)
            running_nav += existing.paper_cash_balance or 0.0
            if running_nav < 1.0:
                running_nav = (
                    _get_last_valid_nav(db, existing.id)
                    or existing.inception_value
                    or snap.total_portfolio_value
                    or 0.0
                )
        else:
            running_nav = snap.total_portfolio_value or 0.0

        if running_nav <= 0:
            running_nav = snap.total_portfolio_value or 1.0

        new_holdings = _resolve_shares_from_weights(allocs, running_nav, prices)
        holdings_priced = len([h for h in new_holdings if not h.get("price_frozen")])

        # inception_date and inception_value are NEVER touched after first creation
        existing.recommendation_snapshot_id = snapshot_id
        existing.inception_holdings_json = json.dumps(new_holdings, default=str)
        db.commit()

        logger.info(
            "[SHADOW] Rebalanced ACTIVE_MODEL id=%s portfolio_id=%s "
            "running_nav=%.2f → new weights (%d holdings, %d priced, %d frozen)",
            existing.id, portfolio_id, running_nav,
            len(new_holdings), holdings_priced, len(new_holdings) - holdings_priced,
        )
        return {
            "shadow_id": existing.id,
            "shadow_type": "ACTIVE_MODEL",
            "action": "rebalanced",
            "running_nav": round(running_nav, 2),
            "holdings_count": len(new_holdings),
            "holdings_priced": holdings_priced,
            "holdings_frozen": len(new_holdings) - holdings_priced,
        }

    # First-time creation — use actual portfolio NAV as inception baseline
    total_portfolio_value = snap.total_portfolio_value or 0.0
    holdings = _resolve_shares_from_weights(allocs, total_portfolio_value, prices)
    holdings_priced = len([h for h in holdings if not h.get("price_frozen")])

    shadow = ShadowPortfolio(
        workspace_id=workspace_id,
        portfolio_id=portfolio_id,
        shadow_type="ACTIVE_MODEL",
        name=f"Active Model Portfolio ({today_str})",
        inception_date=today_str,
        inception_value=total_portfolio_value if total_portfolio_value > 0 else None,
        recommendation_snapshot_id=snapshot_id,
        inception_holdings_json=json.dumps(holdings, default=str),
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


# ─── One-time repair (price_frozen holdings + flat snapshot history) ─────────

def _snapshot_price_history(db: Session) -> dict[str, dict[str, float]]:
    """Return {snapshot_date: {symbol: price}} from all PortfolioSnapshot rows."""
    from models.database import PortfolioSnapshot

    history: dict[str, dict[str, float]] = {}
    rows = (
        db.query(PortfolioSnapshot.snapshot_date, PortfolioSnapshot.holdings_json)
        .filter(PortfolioSnapshot.holdings_json.isnot(None))
        .order_by(PortfolioSnapshot.snapshot_date.asc())
        .all()
    )
    for snap_date, holdings_json in rows:
        try:
            holdings = json.loads(holdings_json)
        except Exception:
            continue
        day = history.setdefault(snap_date, {})
        for h in holdings:
            sym = h.get("symbol")
            price = h.get("current_price")
            if sym and price and float(price) > 0:
                day[sym] = float(price)
    return history


def _price_near_date(
    history: dict[str, dict[str, float]],
    date_str: str,
    symbol: str,
) -> float | None:
    """Price for *symbol* on the nearest date ≤ date_str, else first date after."""
    best: float | None = None
    for d in sorted(history):
        p = history[d].get(symbol)
        if p is None:
            continue
        if d <= date_str:
            best = p          # keep walking forward to the latest date ≤ target
        elif best is None:
            return p          # no observation before target — use first after
        else:
            break
    return best


def _rebuild_shadow_snapshots(
    db: Session,
    shadow: Any,
    holdings: list[dict],
    history: dict[str, dict[str, float]],
) -> int:
    """Re-derive every ShadowPortfolioSnapshot from daily snapshot prices (LOCF).

    Walks all price-history dates in order, carrying prices forward, and
    upserts one snapshot per date ≥ inception_date. Returns rows written.
    """
    from models.database import ShadowPortfolioSnapshot

    existing_rows = {
        s.snapshot_date: s
        for s in db.query(ShadowPortfolioSnapshot)
        .filter(ShadowPortfolioSnapshot.shadow_portfolio_id == shadow.id)
        .all()
    }
    # Union of price dates and already-written snapshot dates ≥ inception
    rebuild_dates = sorted(
        {d for d in history if d >= shadow.inception_date}
        | {d for d in existing_rows if d >= shadow.inception_date}
    )

    last_prices: dict[str, float] = {}
    # Seed LOCF with prices observed on/before inception
    for d in sorted(history):
        if d > shadow.inception_date:
            break
        last_prices.update(history[d])

    inception_value: float | None = shadow.inception_value
    prev_total: float | None = None
    written = 0

    for d in rebuild_dates:
        if d in history:
            last_prices.update(history[d])

        total, _ = _compute_paper_value(holdings, last_prices)
        total += shadow.paper_cash_balance or 0.0
        if total <= 0:
            continue

        if not inception_value or inception_value <= 0:
            inception_value = total
            shadow.inception_value = total

        inception_ret: float | None = None
        raw_ret = (total - inception_value) / inception_value * 100
        if -99.9 <= raw_ret <= 1000.0:
            inception_ret = round(raw_ret, 4)

        daily_ret: float | None = None
        if prev_total and prev_total > 0:
            raw_daily = (total - prev_total) / prev_total * 100
            if -50.0 <= raw_daily <= 50.0:
                daily_ret = round(raw_daily, 4)
        prev_total = total

        snap = existing_rows.get(d)
        if snap:
            snap.total_value = total
            snap.return_pct_since_inception = inception_ret
            snap.daily_return_pct = daily_ret
        else:
            db.add(ShadowPortfolioSnapshot(
                shadow_portfolio_id=shadow.id,
                snapshot_date=d,
                total_value=total,
                return_pct_since_inception=inception_ret,
                daily_return_pct=daily_ret,
                holdings_json=None,
                benchmark_symbol=_BENCHMARK_SYMBOL,
                created_at=datetime.utcnow(),
            ))
        written += 1

        shadow.current_value = total
        shadow.inception_return_pct = inception_ret

    return written


def repair_shadow_portfolios(db: Session, workspace_id: int) -> list[dict[str, Any]]:
    """One-time repair for shadows created while no DB price source resolved.

    Fixes two historical defects (root cause: AgentCache.technical rows carry
    no price keys, so _fetch_cached_prices returned {} at creation AND at
    every daily valuation — all holdings froze at inception_price=1.0 and
    daily_return_pct stayed 0.0 forever):

      1. price_frozen dollar-value holdings → converted to real share counts
         using the PortfolioSnapshot price nearest the shadow's inception date.
      2. Empty inception_holdings_json (pre-fallback rows) → rebuilt from the
         linked decision's approved allocations or the recommendation
         snapshot's projected allocations.

    Then re-derives the full ShadowPortfolioSnapshot history from daily
    portfolio snapshot prices so shadow returns reflect real market moves.
    """
    from models.database import (
        ShadowPortfolio, UserExecutionDecision, RecommendationSnapshot,
    )

    history = _snapshot_price_history(db)
    if not history:
        return [{"status": "no_price_history"}]

    shadows = (
        db.query(ShadowPortfolio)
        .filter_by(workspace_id=workspace_id, is_active=True)
        .order_by(ShadowPortfolio.id)
        .all()
    )

    results: list[dict[str, Any]] = []
    for shadow in shadows:
        result: dict[str, Any] = {"shadow_id": shadow.id, "shadow_type": shadow.shadow_type}
        try:
            holdings: list[dict] = []
            if shadow.inception_holdings_json:
                try:
                    holdings = json.loads(shadow.inception_holdings_json)
                except Exception:
                    holdings = []

            # ── Rebuild empty holdings from linked allocations ────────────────
            if not holdings:
                decision = (
                    db.query(UserExecutionDecision).filter_by(id=shadow.execution_decision_id).first()
                    if shadow.execution_decision_id else None
                )
                snap = (
                    db.query(RecommendationSnapshot).filter_by(id=shadow.recommendation_snapshot_id).first()
                    if shadow.recommendation_snapshot_id else None
                )
                allocs_raw = (decision.approved_allocations_json if decision else None) or (
                    snap.projected_allocations_json if snap else None
                )
                allocs: list[dict] = []
                if allocs_raw:
                    try:
                        allocs = json.loads(allocs_raw)
                    except Exception:
                        pass
                total_value = shadow.inception_value or (
                    (snap.total_portfolio_value if snap else None) or 0.0
                )
                if not allocs or total_value <= 0:
                    result.update(status="skipped_no_allocations", holdings=0)
                    results.append(result)
                    continue
                for a in allocs:
                    sym = a.get("symbol")
                    if not sym:
                        continue
                    weight = float(a.get("target_weight") or 0)
                    holdings.append({
                        "symbol": sym,
                        "target_weight_pct": weight,
                        "action": a.get("action"),
                        "shares": round(weight / 100.0 * total_value, 6),
                        "inception_price": 1.0,
                        "price_frozen": True,  # un-frozen below with real prices
                    })
                result["holdings_rebuilt"] = True

            # ── Un-freeze dollar-value holdings with inception-date prices ────
            unfrozen = 0
            still_frozen = 0
            for h in holdings:
                frozen = h.get("price_frozen", False)
                # Backward-compat inference (same rule as _compute_paper_value)
                if not frozen and float(h.get("inception_price") or 0) == 1.0 and float(h.get("shares") or 0) > 1000:
                    frozen = True
                if not frozen:
                    continue
                price = _price_near_date(history, shadow.inception_date, h.get("symbol", ""))
                if price and price > 0:
                    dollars = float(h.get("shares") or 0)
                    h["shares"] = round(dollars / price, 6)
                    h["inception_price"] = price
                    h["price_frozen"] = False
                    unfrozen += 1
                else:
                    still_frozen += 1

            shadow.inception_holdings_json = json.dumps(holdings, default=str)

            # ── Skip full snapshot rebuild for ACTIVE_MODEL ──────────────────
            # ACTIVE_MODEL allocation changes at each optimizer run; replaying its
            # full SPS history from a single static holdings set produces wrong values.
            # Holdings are still un-frozen above to keep running_nav accurate.
            if shadow.shadow_type == "ACTIVE_MODEL":
                db.commit()
                result.update(
                    status="unfrozen_holdings_only",
                    holdings=len(holdings),
                    unfrozen=unfrozen,
                    still_frozen=still_frozen,
                    snapshots_rebuilt=0,
                )
                logger.info(
                    "[SHADOW] Repair skipped snapshot rebuild for ACTIVE_MODEL shadow_id=%s "
                    "(%d holdings, %d unfrozen)",
                    shadow.id, len(holdings), unfrozen,
                )
                results.append(result)
                continue

            # ── Rebuild snapshot history with real daily prices ───────────────
            rows = _rebuild_shadow_snapshots(db, shadow, holdings, history)
            db.commit()

            result.update(
                status="repaired",
                holdings=len(holdings),
                unfrozen=unfrozen,
                still_frozen=still_frozen,
                snapshots_rebuilt=rows,
                inception_return_pct=shadow.inception_return_pct,
            )
            logger.info(
                "[SHADOW] Repaired shadow_id=%s: %d holdings (%d unfrozen), %d snapshots rebuilt",
                shadow.id, len(holdings), unfrozen, rows,
            )
        except Exception as exc:
            db.rollback()
            logger.error("[SHADOW] Repair failed for shadow_id=%s: %s", shadow.id, exc)
            result.update(status="error", error=str(exc))
        results.append(result)

    return results


def reset_active_model_inception(db: Session, workspace_id: int) -> list[dict[str, Any]]:
    """Reset ACTIVE_MODEL shadow inception to today's date and current NAV.

    Clears all ShadowPortfolioSnapshot history for each ACTIVE_MODEL shadow
    and resets inception_date/inception_value so the cumulative track record
    starts fresh from the current point in time.

    Call once after deploying the Option B rebalancing fix to clear previously
    corrupted history before the new compounding logic takes over.
    """
    from models.database import ShadowPortfolio, ShadowPortfolioSnapshot

    today_str = date.today().isoformat()
    shadows = (
        db.query(ShadowPortfolio)
        .filter_by(workspace_id=workspace_id, shadow_type="ACTIVE_MODEL", is_active=True)
        .all()
    )
    results: list[dict[str, Any]] = []
    for shadow in shadows:
        result: dict[str, Any] = {"shadow_id": shadow.id, "portfolio_id": shadow.portfolio_id}
        try:
            db.query(ShadowPortfolioSnapshot).filter_by(shadow_portfolio_id=shadow.id).delete()

            holdings: list[dict] = []
            if shadow.inception_holdings_json:
                try:
                    holdings = json.loads(shadow.inception_holdings_json)
                except Exception:
                    pass

            current_nav = 0.0
            if holdings:
                syms = [h["symbol"] for h in holdings if h.get("symbol")]
                prices = _fetch_cached_prices(db, syms)
                current_nav, _ = _compute_paper_value(holdings, prices)
                current_nav += shadow.paper_cash_balance or 0.0

            if current_nav < 1.0:
                current_nav = shadow.inception_value or 0.0

            shadow.inception_date = today_str
            shadow.inception_value = current_nav if current_nav > 0 else None
            shadow.inception_return_pct = 0.0
            shadow.current_value = current_nav if current_nav > 0 else None
            db.commit()

            if current_nav > 0:
                value_shadow_portfolio(db, shadow.id)

            result.update(
                status="reset",
                new_inception_date=today_str,
                new_inception_value=round(current_nav, 2),
            )
            logger.info(
                "[SHADOW] Reset ACTIVE_MODEL id=%s: new inception %s @ %.2f NAV",
                shadow.id, today_str, current_nav,
            )
        except Exception as exc:
            db.rollback()
            logger.error("[SHADOW] reset failed for shadow_id=%s: %s", shadow.id, exc)
            result.update(status="error", error=str(exc))
        results.append(result)
    return results
