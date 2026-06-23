"""Human Idea Intake — AI Committee Review (Phase 4C.4).

Stateless, read-only evaluation of user-supplied stock symbols against the
active portfolio's constraints, persona, regime, and latest optimizer output.

No new AI calls. No new DB tables. All data sourced from existing services:
  - AnalysisCache        (existing signal + ta/fa scores)
  - PortfolioItem        (existing positions + sector)
  - Watchlist            (watchlist sector)
  - RecommendationSnapshot (latest optimizer allocations for E1 + E2)
  - detect_regime()      (regime context)
  - resolve_constraints() (EffectiveEnvelope — policy limits)
  - build_persona_context() (strategy persona + DNA)

Public API:
    review_ideas(symbols, portfolio_id, db, workspace_id) -> dict
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any

# DR symbols stored without .BK suffix (e.g. NVDA01, MICRON01).
# Matches letters followed by digits — used to detect Thai DRs that need .BK appended
# before fetching Thai market prices or sector info.
_DR_DIGIT_PATTERN = re.compile(r"^[A-Z]+\d+$")

from sqlalchemy.orm import Session

from models.database import (
    AnalysisCache, Portfolio, PortfolioItem,
    RecommendationSnapshot, Settings, Watchlist,
)
from services.data_fetcher import fetch_info, fetch_price_info
from services.symbol_normalization import get_yfinance_symbol
from services.optimizer.strategy_profiles import (
    STRATEGY_PROFILES, valid_persona,
    compute_style_drift, build_persona_context,
)
from services.analytics.factor_engine import compute_portfolio_factor_exposure
from services.optimizer.constraint_resolver import resolve_constraints, effective_sector_cap

log = logging.getLogger(__name__)

_MAX_SYMBOLS = 10

# ─── Direction maps for optimizer alignment ───────────────────────────────────

_OPTIMIZER_DIRECTION: dict[str, str] = {
    "BUY":        "positive",
    "ACCUMULATE": "positive",
    "SWAP":       "positive",
    "SELL":       "negative",
    "REDUCE":     "negative",
    "HOLD":       "neutral",
    "WATCH":      "neutral",
}
_COMMITTEE_DIRECTION: dict[str, str] = {
    "APPROVE": "positive",
    "WATCH":   "positive",
    "DECLINE": "negative",
    "REVIEW":  "neutral",
}

# ─── Canonical sectors (mirrors main.py) ─────────────────────────────────────

_CANONICAL_SECTORS = frozenset({
    "Technology", "Financial", "Energy", "Healthcare",
    "Consumer", "Industrial", "Real Estate", "Utilities", "Other",
})


def _normalize_sector(raw: str | None) -> str:
    s = (raw or "").strip()
    if s in _CANONICAL_SECTORS:
        return s
    if "Financial" in s:
        return "Financial"
    if "Consumer" in s:
        return "Consumer"
    if "Industrial" in s:
        return "Industrial"
    if "Health" in s:
        return "Healthcare"
    if "Technology" in s or "Tech" in s or "Communication" in s:
        return "Technology"
    if "Energy" in s:
        return "Energy"
    if "Real Estate" in s or "REIT" in s:
        return "Real Estate"
    if "Utilities" in s or "Utility" in s:
        return "Utilities"
    return "Other"


# ─── Scoring helpers ──────────────────────────────────────────────────────────

def _compute_strategic_fit(
    ta_score: int | None,
    fa_score: int | None,
    existing_signal: str | None,
    sector_headroom_ratio: float,
    persona: str,
) -> int:
    """Strategic fit score 0–10 from signal alignment and persona factor weights."""
    profile = STRATEGY_PROFILES.get(persona, STRATEGY_PROFILES["BALANCED"])
    weights = profile["factor_weights"]

    score = 5  # neutral baseline

    # Signal alignment
    if existing_signal in ("BUY", "ACCUMULATE"):
        score += 2
    elif existing_signal == "WATCH":
        score += 1
    elif existing_signal == "REDUCE":
        score -= 1
    elif existing_signal == "SELL":
        score -= 2

    # Factor alignment: ta_score → momentum proxy, fa_score → quality/value proxy
    if ta_score is not None and fa_score is not None:
        momentum_w = weights.get("momentum", 0.20)
        quality_w = weights.get("quality", 0.20) + weights.get("value", 0.20) * 0.5
        total_w = momentum_w + quality_w
        if total_w > 0:
            alignment = (
                (ta_score / 100.0) * momentum_w + (fa_score / 100.0) * quality_w
            ) / total_w
            if alignment >= 0.65:
                score += 2
            elif alignment >= 0.50:
                score += 1
            elif alignment < 0.35:
                score -= 1

    # Sector headroom bonus/penalty
    if sector_headroom_ratio >= 0.50:
        score += 1
    elif sector_headroom_ratio < 0.20:
        score -= 1

    return max(0, min(10, score))


def _fit_label(score: int) -> str:
    if score >= 7:
        return "STRONG"
    if score >= 5:
        return "MODERATE"
    return "WEAK"


def _risk_impact(
    sector_current: float, sector_limit: float,
    current_alloc: float, position_limit: float,
) -> str:
    su = sector_current / sector_limit if sector_limit > 0 else 0.0
    pu = current_alloc / position_limit if position_limit > 0 else 0.0
    max_usage = max(su, pu)
    if max_usage < 0.50:
        return "LOW"
    if max_usage < 0.80:
        return "MEDIUM"
    return "HIGH"


def _policy_check(
    sector_current: float, sector_limit: float,
    current_alloc: float, position_limit: float,
) -> str:
    if sector_current >= sector_limit or current_alloc >= position_limit:
        return "FAIL"
    if sector_current > sector_limit * 0.80 or current_alloc > position_limit * 0.80:
        return "WARNING"
    return "PASS"


def _committee_decision(
    fit_score: int, risk: str, policy: str, signal: str | None,
) -> str:
    if policy == "FAIL" or fit_score < 4:
        return "DECLINE"
    if risk == "HIGH" or policy == "WARNING":
        return "REVIEW"
    if fit_score >= 7 and policy == "PASS" and risk == "LOW":
        return "APPROVE"
    return "WATCH"


def _optimizer_alignment(decision: str, optimizer_action: str | None) -> str:
    opt_dir = _OPTIMIZER_DIRECTION.get(optimizer_action or "", "neutral")
    com_dir = _COMMITTEE_DIRECTION.get(decision, "neutral")
    if opt_dir == "neutral" or com_dir == "neutral":
        return "NEUTRAL"
    return "ALIGNED" if opt_dir == com_dir else "CONTRADICTING"


def _portfolio_priority(
    fit_score: int, current_pct: float,
    position_limit: float, policy: str, risk: str,
) -> str:
    if policy == "FAIL":
        return "LOW"
    headroom = (position_limit - current_pct) / position_limit if position_limit > 0 else 0.0
    if fit_score >= 8 and risk == "LOW" and headroom >= 0.50:
        return "HIGH"
    if fit_score >= 5 and risk != "HIGH" and headroom >= 0.20:
        return "MEDIUM"
    return "LOW"


def _build_reason(
    decision: str,
    fit_score: int,
    risk: str,
    policy: str,
    sector: str | None,
    sector_current_pct: float,
    sector_limit_pct: float,
    existing_signal: str | None,
    alignment: str,
    current_alloc_pct: float,
    position_limit_pct: float,
) -> str:
    parts: list[str] = []
    sec = sector or "Sector"

    if decision == "APPROVE":
        parts.append(f"Strategic fit {fit_score}/10 — aligns with portfolio strategy")
        parts.append("Well within position and sector limits")
        if existing_signal in ("BUY", "ACCUMULATE"):
            parts.append(f"{existing_signal} signal active")

    elif decision == "WATCH":
        parts.append(f"Strategic fit {fit_score}/10")
        if risk == "MEDIUM":
            parts.append(
                f"{sec} at {sector_current_pct:.1f}% vs {sector_limit_pct:.0f}% limit — "
                "monitor before adding"
            )
        elif existing_signal in ("WATCH", "HOLD", None):
            parts.append("Signal not yet strong enough for full commitment")

    elif decision == "REVIEW":
        if policy == "WARNING":
            parts.append(
                f"{sec} approaching limit ({sector_current_pct:.1f}% of {sector_limit_pct:.0f}%)"
            )
        if risk == "HIGH":
            parts.append(
                f"Concentration risk elevated — "
                f"{current_alloc_pct:.1f}% vs {position_limit_pct:.0f}% position limit"
            )

    elif decision == "DECLINE":
        if policy == "FAIL":
            parts.append(
                f"Policy violation: {sec} {sector_current_pct:.1f}% "
                f"exceeds {sector_limit_pct:.0f}% limit"
            )
        if fit_score < 4:
            parts.append("Poor strategic alignment with current persona")

    if alignment == "CONTRADICTING":
        parts.append("Note: contradicts latest optimizer recommendation")
    elif alignment == "ALIGNED":
        parts.append("Aligned with latest optimizer recommendation")

    return " — ".join(parts) if parts else "Evaluated against current portfolio context"


# ─── Sector resolution ────────────────────────────────────────────────────────

def _get_sector(
    symbol: str,
    portfolio_items: list[PortfolioItem],
    watchlist_items: list[Watchlist],
    yf_info_cache: dict[str, dict],
) -> str | None:
    """Tiered sector lookup: portfolio DB → watchlist DB → yfinance info.

    Handles .BK suffix mismatch: 'BH' matches item stored as 'BH.BK'.
    """
    for item in portfolio_items:
        match = item.symbol == symbol or (
            item.symbol.endswith(".BK") and item.symbol[:-3] == symbol
        )
        if match and item.sector:
            return item.sector
    for item in watchlist_items:
        match = item.symbol == symbol or (
            item.symbol.endswith(".BK") and item.symbol[:-3] == symbol
        )
        if match and item.sector:
            return item.sector
    raw = yf_info_cache.get(symbol, {}).get("sector")
    return _normalize_sector(raw) if raw else None


# ─── Settings loaders ─────────────────────────────────────────────────────────

_DEFAULT_PS: dict[str, Any] = {"max_stocks": 12, "max_sector_pct": 40}


def _load_settings(db: Session, ws: int) -> tuple[dict, dict]:
    """Return (portfolio_settings, sector_limits) dicts from DB."""
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


# ─── Main entry point ─────────────────────────────────────────────────────────

def review_ideas(
    symbols: list[str],
    portfolio_id: int,
    db: Session,
    workspace_id: int,
) -> dict:
    """Evaluate user-supplied ideas against the active portfolio intelligence stack.

    Synchronous — wrap in asyncio.to_thread() from async FastAPI handlers.
    Returns a dict ready for direct JSON serialisation.
    """
    symbols = [s.strip().upper() for s in symbols if s.strip()][:_MAX_SYMBOLS]
    if not symbols:
        return {"portfolio_context": {}, "reviews": []}

    # ── Load portfolio ─────────────────────────────────────────────────────────
    portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.id == portfolio_id, Portfolio.workspace_id == workspace_id)
        .first()
    )
    if not portfolio:
        return {"error": "portfolio_not_found", "reviews": []}

    portfolio_items: list[PortfolioItem] = (
        db.query(PortfolioItem)
        .filter(
            PortfolioItem.portfolio_id == portfolio_id,
            PortfolioItem.workspace_id == workspace_id,
        )
        .all()
    )
    watchlist_items: list[Watchlist] = (
        db.query(Watchlist).filter(Watchlist.workspace_id == workspace_id).all()
    )

    # ── Portfolio market values + weights ──────────────────────────────────────
    total_value = float(portfolio.cash_balance or 0.0)
    item_mvs: dict[str, float] = {}
    for item in portfolio_items:
        try:
            # DR symbols stored without .BK (e.g. NVDA01, MICRON01) must be fetched as
            # "NVDA01.BK" / "MICRON01.BK" to get the Thai market price in THB.
            # Without .BK, yfinance cannot find the ticker and falls back to avg_cost
            # (stale purchase price), producing wildly wrong current-allocation percentages.
            fetch_sym = item.symbol
            if not item.symbol.endswith(".BK") and _DR_DIGIT_PATTERN.match(item.symbol):
                fetch_sym = item.symbol + ".BK"
            price_data = fetch_price_info(fetch_sym)
            price = float(price_data.get("current_price") or 0.0)
            if price <= 0:
                price = float(item.avg_cost)
        except Exception:
            price = float(item.avg_cost)
        mv = price * float(item.shares)
        item_mvs[item.symbol] = mv
        total_value += mv

    # Sector weights across existing portfolio
    sector_values: dict[str, float] = {}
    for item in portfolio_items:
        sec = item.sector or "Other"
        sector_values[sec] = sector_values.get(sec, 0.0) + item_mvs.get(item.symbol, 0.0)
    sector_weights: dict[str, float] = {
        sec: round(val / total_value * 100, 2)
        for sec, val in sector_values.items()
        if total_value > 0
    }

    # ── AnalysisCache: fetch for both portfolio holdings AND idea symbols ───────
    # Also include .BK variants of bare idea symbols: analysis may have been stored
    # as "BH.BK" (via portfolio analyze) while the user submits "BH" as an idea.
    bk_variants = {f"{s}.BK" for s in symbols if "." not in s}
    all_query_symbols = list(
        {item.symbol for item in portfolio_items} | set(symbols) | bk_variants
    )
    cache_rows = (
        db.query(AnalysisCache)
        .filter(
            AnalysisCache.workspace_id == workspace_id,
            AnalysisCache.symbol.in_(all_query_symbols),
        )
        .all()
    )
    # Dual-index: allows cache_map.get("BH") to find a row stored as "BH.BK"
    cache_map: dict[str, AnalysisCache] = {}
    for r in cache_rows:
        cache_map[r.symbol] = r
        if r.symbol.endswith(".BK"):
            cache_map.setdefault(r.symbol[:-3], r)

    # Normalize portfolio-item lookup so "BH" finds the item stored as "BH.BK"
    holdings_by_sym: dict[str, PortfolioItem] = {}
    for h in portfolio_items:
        holdings_by_sym[h.symbol] = h
        if h.symbol.endswith(".BK"):
            holdings_by_sym.setdefault(h.symbol[:-3], h)

    # ── Portfolio DNA + Persona context ───────────────────────────────────────
    # Use factor_engine as single source of truth (same engine as DNA page).
    persona = valid_persona(portfolio.strategy_persona or "BALANCED")
    try:
        fe_result = compute_portfolio_factor_exposure(db, portfolio_id, workspace_id)
        portfolio_dna = {
            factor: (
                fe_result.get("factor_exposures", {}).get(factor, {}).get("score") or 50.0
            )
            for factor in ("growth", "value", "momentum", "quality", "dividend")
        }
        drift_data = compute_style_drift(portfolio_dna, persona)
        persona_ctx = build_persona_context(persona, portfolio_dna, drift_data)
    except Exception as exc:
        log.warning("idea_review: persona context failed: %s", exc)
        persona_ctx = {}

    # ── Regime context ─────────────────────────────────────────────────────────
    regime_ctx: dict | None = None
    try:
        from services.analytics.regime_detector import detect_regime
        regime_ctx = detect_regime(db)
    except Exception as exc:
        log.warning("idea_review: regime detection failed: %s", exc)

    # ── Constraint envelope ────────────────────────────────────────────────────
    ps, sector_limits = _load_settings(db, workspace_id)
    envelope = None
    try:
        envelope = resolve_constraints(ps, sector_limits, regime_ctx, persona_ctx)
    except Exception as exc:
        log.warning("idea_review: constraint resolver failed: %s", exc)

    # ── Latest optimizer output (shared query for E1 + E2) ────────────────────
    latest_snap = (
        db.query(RecommendationSnapshot)
        .filter_by(portfolio_id=portfolio_id, workspace_id=workspace_id)
        .order_by(RecommendationSnapshot.created_at.desc())
        .limit(1)
        .first()
    )
    last_optimizer_run_at: str | None = None
    optimizer_alloc_map: dict[str, dict] = {}
    if latest_snap:
        last_optimizer_run_at = (
            latest_snap.created_at.isoformat() + "Z" if latest_snap.created_at else None
        )
        try:
            allocs = json.loads(latest_snap.projected_allocations_json or "[]")
            for a in (allocs if isinstance(allocs, list) else []):
                sym = a.get("symbol")
                if sym:
                    optimizer_alloc_map[sym] = {
                        "action":        a.get("action"),
                        "target_weight": a.get("target_weight"),
                    }
        except Exception:
            pass

    # ── yfinance info for symbols not in portfolio / watchlist ─────────────────
    # Expand known_symbols with bare forms so "BH" is not treated as unknown when "BH.BK" is held
    known_symbols: set[str] = set()
    for item in portfolio_items:
        known_symbols.add(item.symbol)
        if item.symbol.endswith(".BK"):
            known_symbols.add(item.symbol[:-3])
    for item in watchlist_items:
        known_symbols.add(item.symbol)
        if item.symbol.endswith(".BK"):
            known_symbols.add(item.symbol[:-3])
    # Symbols whose sector is already set in the DB — yfinance not needed for sector
    symbols_with_db_sector: set[str] = set()
    for item in portfolio_items:
        if item.sector:
            symbols_with_db_sector.add(item.symbol)
            if item.symbol.endswith(".BK"):
                symbols_with_db_sector.add(item.symbol[:-3])
    for item in watchlist_items:
        if item.sector:
            symbols_with_db_sector.add(item.symbol)
            if item.symbol.endswith(".BK"):
                symbols_with_db_sector.add(item.symbol[:-3])

    yf_info_cache: dict[str, dict] = {}
    for sym in symbols:
        # Skip yfinance only when sector is already known from DB.
        # If the symbol is in the portfolio but item.sector is null (e.g. DR added without
        # sector), we must still fetch from yfinance for accurate sector classification.
        if sym in known_symbols and sym in symbols_with_db_sector:
            continue
        try:
            fetch_target = get_yfinance_symbol(sym)
            yf_info_cache[sym] = fetch_info(fetch_target)
        except Exception:
            yf_info_cache[sym] = {}

    # ── Per-symbol evaluation ─────────────────────────────────────────────────
    reviews: list[dict] = []
    for sym in symbols:
        # Existing position — use normalized lookup so "BH" matches item stored as "BH.BK"
        holding = holdings_by_sym.get(sym)
        existing_position = holding is not None
        # item_mvs is keyed by item.symbol (canonical stored form); use holding.symbol to look up
        current_mv = item_mvs.get(holding.symbol, 0.0) if holding else 0.0
        current_alloc_pct = (
            round(current_mv / total_value * 100, 2) if total_value > 0 else 0.0
        )

        # Cached signal
        cached = cache_map.get(sym)
        data_available = cached is not None
        existing_signal: str | None = cached.signal.upper() if cached and cached.signal else None
        ta_score: int | None = int(cached.ta_score) if cached and cached.ta_score is not None else None
        fa_score: int | None = int(cached.fa_score) if cached and cached.fa_score is not None else None
        signal_confidence: float | None = None
        if cached and cached.confidence:
            signal_confidence = {"high": 0.85, "medium": 0.60, "low": 0.35}.get(
                cached.confidence.lower()
            )

        # Sector
        sector = _get_sector(sym, portfolio_items, watchlist_items, yf_info_cache)

        # Constraint limits
        if envelope is not None:
            position_limit = envelope.effective_single_position_pct
            sector_limit = effective_sector_cap(envelope, sector or "Other")
        else:
            position_limit = 22.0
            sector_limit = float(ps.get("max_sector_pct", 40))

        sector_current_pct = sector_weights.get(sector or "Other", 0.0)
        headroom_ratio = (
            (sector_limit - sector_current_pct) / sector_limit if sector_limit > 0 else 0.0
        )

        # Scoring
        fit_score = _compute_strategic_fit(
            ta_score, fa_score, existing_signal, headroom_ratio, persona
        )
        fit_label = _fit_label(fit_score)
        risk = _risk_impact(sector_current_pct, sector_limit, current_alloc_pct, position_limit)
        policy = _policy_check(sector_current_pct, sector_limit, current_alloc_pct, position_limit)
        decision = _committee_decision(fit_score, risk, policy, existing_signal)

        # Enhancement 1 — Optimizer alignment
        opt_data = optimizer_alloc_map.get(sym, {})
        optimizer_action: str | None = opt_data.get("action")
        alignment = _optimizer_alignment(decision, optimizer_action)

        # Enhancement 2 — Target allocation
        raw_target = opt_data.get("target_weight")
        target_alloc_pct: float | None = round(float(raw_target), 2) if raw_target is not None else None

        # Enhancement 3 — Portfolio priority
        priority = _portfolio_priority(fit_score, current_alloc_pct, position_limit, policy, risk)

        # Warnings
        warnings: list[str] = []
        if not data_available:
            warnings.append("No cached analysis — run /analyze first for richer evaluation")
        if alignment == "CONTRADICTING":
            warnings.append(
                f"Contradicts optimizer: last action was {optimizer_action}"
            )
        if risk == "HIGH":
            sec_label = sector or "Sector"
            warnings.append(
                f"Concentration risk elevated — {sec_label} "
                f"at {sector_current_pct:.1f}% of {sector_limit:.0f}% limit"
            )

        reason = _build_reason(
            decision, fit_score, risk, policy,
            sector, sector_current_pct, sector_limit,
            existing_signal, alignment,
            current_alloc_pct, position_limit,
        )

        log.info(
            "idea_review [%s]: holding=%s current_mv=%.2f total_value=%.2f "
            "current_alloc_pct=%.2f position_limit=%.1f "
            "sector=%s sector_current_pct=%.2f sector_limit=%.1f "
            "risk=%s policy=%s decision=%s",
            sym,
            holding.symbol if holding else None,
            current_mv,
            total_value,
            current_alloc_pct,
            position_limit,
            sector,
            sector_current_pct,
            sector_limit,
            risk,
            policy,
            decision,
        )

        reviews.append({
            "symbol":                 sym,
            "sector":                 sector,
            "data_available":         data_available,
            "existing_signal":        existing_signal,
            "signal_confidence":      signal_confidence,
            "existing_position":      existing_position,
            "current_allocation_pct": current_alloc_pct,
            "position_limit_pct":     round(position_limit, 1),
            "sector_current_pct":     round(sector_current_pct, 2),
            "sector_limit_pct":       round(sector_limit, 1),
            "strategic_fit_score":    fit_score,
            "strategic_fit_label":    fit_label,
            "risk_impact":            risk,
            "policy_check":           policy,
            "committee_decision":     decision,
            "reason":                 reason,
            "optimizer_alignment":    alignment,
            "optimizer_action":       optimizer_action,
            "target_allocation_pct":  target_alloc_pct,
            "portfolio_priority":     priority,
            "warnings":               warnings,
        })

    return {
        "portfolio_context": {
            "portfolio_id":          portfolio_id,
            "portfolio_name":        portfolio.name,
            "persona":               persona,
            "regime":                regime_ctx.get("regime") if regime_ctx else None,
            "emergency_active":      envelope.emergency_active if envelope else False,
            "total_value":           round(total_value, 2),
            "last_optimizer_run_at": last_optimizer_run_at,
            "generated_at":          datetime.utcnow().isoformat() + "Z",
        },
        "reviews": reviews,
    }
