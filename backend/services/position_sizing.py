"""Phase 4D.1 — Constraint-Aware Position Sizing.

Sizes a basket of ideas proportionally by signal quality, confidence,
strategic fit, and portfolio priority — then scales down if any sector
cap would be breached.

No AI calls.  No new tables.  No mutations.

Public API
----------
suggest_position_sizes(portfolio_id, symbols, workspace_id, db)
    -> PositionSizingResult

compute_position_sizes(portfolio_id, symbols, symbol_data, symbol_sectors,
                       cash_pct, sector_weights, sector_limits, cash_min_pct)
    -> PositionSizingResult       (pure, testable without DB)

Scoring
-------
    signal_points       = ACCUMULATE 5 / BUY 4 / WATCH 2 / HOLD 1 / REDUCE 0 / SELL 0
    confidence_points   = confidence_float × 5
    fit_points          = strategic_fit_score / 2
    priority_points     = HIGH 3 / MEDIUM 2 / LOW 1
    position_score      = sum of above

Capital allocation: proportional to position_score, capped by deployable cash
(cash_pct − cash_min_pct).  If any sector cap would be exceeded the whole
basket is scaled proportionally downward to fit within the tightest headroom.
"""
from __future__ import annotations

import logging

from pydantic import BaseModel
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)

# ── Scoring tables ────────────────────────────────────────────────────────────

_SIGNAL_POINTS: dict[str, float] = {
    "ACCUMULATE": 5.0,
    "BUY":        4.0,
    "WATCH":      2.0,
    "HOLD":       1.0,
    "REDUCE":     0.0,
    "SELL":       0.0,
}

_PRIORITY_POINTS: dict[str, float] = {
    "HIGH":   3.0,
    "MEDIUM": 2.0,
    "LOW":    1.0,
}

_CONFIDENCE_MAP: dict[str, float] = {
    "high":   0.85,
    "medium": 0.60,
    "low":    0.35,
}


# ── Response models ───────────────────────────────────────────────────────────

class ScoreBreakdown(BaseModel):
    signal_points: float
    confidence_points: float
    fit_points: float
    priority_points: float


class PositionSuggestion(BaseModel):
    symbol: str
    position_score: float
    suggested_pct: float
    signal: str
    confidence: float
    breakdown: ScoreBreakdown


class PositionSizingResult(BaseModel):
    deployable_cash_pct: float
    total_allocated_pct: float
    status: str                         # PASS / WARNING / FAIL
    suggestions: list[PositionSuggestion]
    reasoning: list[str]


# ── Pure evaluator (no DB) ────────────────────────────────────────────────────

def compute_position_sizes(
    portfolio_id: int,
    symbols: list[str],
    symbol_data: dict[str, dict],
    symbol_sectors: dict[str, str],
    cash_pct: float,
    sector_weights: dict[str, float],
    sector_limits: dict[str, float],
    cash_min_pct: float,
) -> PositionSizingResult:
    """Size a basket proportionally by score, then scale to satisfy sector caps.

    Args:
        portfolio_id:   Portfolio ID (used for correlation; not stored in result)
        symbols:        Basket to size (duplicates deduplicated, order preserved)
        symbol_data:    Per-symbol dict with keys signal/confidence/
                        strategic_fit_score/portfolio_priority
        symbol_sectors: symbol → sector name (for constraint checks)
        cash_pct:       Current cash as % of total portfolio
        sector_weights: Current sector allocations as % of total portfolio
        sector_limits:  Max allowed % per sector (from resolved constraints)
        cash_min_pct:   Minimum required cash by policy
    """
    unique_symbols = list(dict.fromkeys(symbols))
    deployable = round(max(0.0, cash_pct - cash_min_pct), 4)

    if not unique_symbols:
        return PositionSizingResult(
            deployable_cash_pct=deployable,
            total_allocated_pct=0.0,
            status="FAIL",
            suggestions=[],
            reasoning=["No symbols provided."],
        )

    if deployable <= 0:
        suggestions = [
            _make_suggestion(sym, symbol_data.get(sym, {}), 0.0)
            for sym in unique_symbols
        ]
        return PositionSizingResult(
            deployable_cash_pct=0.0,
            total_allocated_pct=0.0,
            status="FAIL",
            suggestions=suggestions,
            reasoning=[
                "No deployable cash available after maintaining the minimum cash reserve."
            ],
        )

    # ── Score each symbol ─────────────────────────────────────────────────────
    scored: dict[str, tuple[float, ScoreBreakdown]] = {
        sym: _score_symbol(symbol_data.get(sym, {})) for sym in unique_symbols
    }
    total_score = sum(s[0] for s in scored.values())

    if total_score <= 0:
        # Fallback to equal weighting when all signals are REDUCE/SELL
        per_sym = round(deployable / len(unique_symbols), 4)
        raw_allocs: dict[str, float] = {sym: per_sym for sym in unique_symbols}
    else:
        raw_allocs = {
            sym: round(score / total_score * deployable, 4)
            for sym, (score, _) in scored.items()
        }

    # ── Sector cap check → compute scale factor ───────────────────────────────
    sector_allocs: dict[str, float] = {}
    for sym, pct in raw_allocs.items():
        sec = symbol_sectors.get(sym, "Other")
        sector_allocs[sec] = round(sector_allocs.get(sec, 0.0) + pct, 6)

    scale_factor = 1.0
    for sec, alloc in sector_allocs.items():
        if alloc <= 0:
            continue
        limit = sector_limits.get(sec, sector_limits.get("Other", 40.0))
        current = sector_weights.get(sec, 0.0)
        headroom = limit - current
        if headroom <= 0:
            scale_factor = 0.0
            break
        if alloc > headroom:
            scale_factor = min(scale_factor, headroom / alloc)

    scale_factor = max(0.0, min(1.0, scale_factor))

    final_allocs = {sym: round(pct * scale_factor, 4) for sym, pct in raw_allocs.items()}
    total_allocated = round(sum(final_allocs.values()), 4)

    # ── Status ────────────────────────────────────────────────────────────────
    scaled_down = scale_factor < 0.999
    if total_allocated < 0.01:
        status = "FAIL"
    elif scaled_down:
        status = "WARNING"
    else:
        status = "PASS"

    # ── Build suggestions sorted by score desc ────────────────────────────────
    suggestions = sorted(
        [_make_suggestion(sym, symbol_data.get(sym, {}), final_allocs[sym]) for sym in unique_symbols],
        key=lambda s: s.position_score,
        reverse=True,
    )

    reasoning = _build_reasoning(
        suggestions, deployable, total_allocated, scale_factor,
        sector_allocs, sector_limits, sector_weights,
    )

    return PositionSizingResult(
        deployable_cash_pct=deployable,
        total_allocated_pct=total_allocated,
        status=status,
        suggestions=suggestions,
        reasoning=reasoning,
    )


# ── DB loader ─────────────────────────────────────────────────────────────────

def suggest_position_sizes(
    portfolio_id: int,
    symbols: list[str],
    workspace_id: int,
    db: Session,
) -> PositionSizingResult:
    """Load portfolio + analysis cache, resolve constraints, size positions."""
    from models.database import AnalysisCache, Portfolio, PortfolioItem, Watchlist
    from services.basket_simulation import (
        _CANONICAL_SECTORS,
        _load_settings,
        _resolve_symbol_sectors,
    )
    from services.idea_review import (
        _compute_strategic_fit,
        _policy_check,
        _portfolio_priority,
        _risk_impact,
    )
    from services.optimizer.constraint_resolver import effective_sector_cap, resolve_constraints
    from services.optimizer.strategy_profiles import valid_persona

    symbols = [s.strip().upper() for s in symbols if s.strip()]
    if not symbols:
        return compute_position_sizes(portfolio_id, [], {}, {}, 100.0, {}, {}, 0.0)

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

    # Market values (avg_cost × shares — no live yfinance for speed)
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

    # Constraints
    ps, sector_limit_settings = _load_settings(db, workspace_id)

    regime_ctx = None
    try:
        from services.analytics.regime_detector import detect_regime
        regime_ctx = detect_regime(db)
    except Exception:
        pass

    envelope = None
    try:
        envelope = resolve_constraints(ps, sector_limit_settings, regime_ctx, None)
    except Exception as exc:
        log.warning("position_sizing: constraint resolver failed: %s", exc)

    cash_min_pct = envelope.effective_cash_min_pct if envelope else 0.0
    position_limit = envelope.effective_single_position_pct if envelope else 22.0

    if envelope:
        sector_limits_resolved: dict[str, float] = {
            sec: effective_sector_cap(envelope, sec) for sec in _CANONICAL_SECTORS
        }
    else:
        default_cap = float(ps.get("max_sector_pct", 40))
        sector_limits_resolved = {sec: default_cap for sec in _CANONICAL_SECTORS}

    # Symbol sectors
    watchlist_items = (
        db.query(Watchlist).filter(Watchlist.workspace_id == workspace_id).all()
    )
    symbol_sectors = _resolve_symbol_sectors(symbols, portfolio_items, watchlist_items)

    # AnalysisCache for signal + scores
    bk_variants = {f"{s}.BK" for s in symbols if "." not in s}
    cache_rows = (
        db.query(AnalysisCache)
        .filter(
            AnalysisCache.workspace_id == workspace_id,
            AnalysisCache.symbol.in_(list(set(symbols) | bk_variants)),
        )
        .all()
    )
    cache_map: dict[str, AnalysisCache] = {}
    for r in cache_rows:
        cache_map[r.symbol] = r
        if r.symbol.endswith(".BK"):
            cache_map.setdefault(r.symbol[:-3], r)

    persona = valid_persona(portfolio.strategy_persona or "BALANCED")

    # Normalize current holdings lookup to handle .BK mismatch
    holdings_mv: dict[str, float] = {}
    for item in portfolio_items:
        holdings_mv[item.symbol] = item_mvs.get(item.symbol, 0.0)
        if item.symbol.endswith(".BK"):
            holdings_mv.setdefault(item.symbol[:-3], holdings_mv[item.symbol])

    symbol_data: dict[str, dict] = {}
    for sym in symbols:
        cached = cache_map.get(sym)
        signal = cached.signal.upper() if cached and cached.signal else "HOLD"
        conf_str = (cached.confidence or "medium").lower() if cached else "medium"
        confidence = _CONFIDENCE_MAP.get(conf_str, 0.50)
        ta_score = int(cached.ta_score) if cached and cached.ta_score is not None else None
        fa_score = int(cached.fa_score) if cached and cached.fa_score is not None else None

        sector = symbol_sectors.get(sym, "Other")
        sector_current = sector_weights.get(sector, 0.0)
        sector_limit = sector_limits_resolved.get(sector, 40.0)
        headroom_ratio = (
            (sector_limit - sector_current) / sector_limit if sector_limit > 0 else 0.0
        )

        fit_score = _compute_strategic_fit(ta_score, fa_score, signal, headroom_ratio, persona)

        current_mv = holdings_mv.get(sym, 0.0)
        current_alloc_pct = round(current_mv / total_value * 100.0, 2) if total_value > 0 else 0.0
        policy = _policy_check(sector_current, sector_limit, current_alloc_pct, position_limit)
        risk = _risk_impact(sector_current, sector_limit, current_alloc_pct, position_limit)
        priority = _portfolio_priority(fit_score, current_alloc_pct, position_limit, policy, risk)

        symbol_data[sym] = {
            "signal":                signal,
            "confidence":            confidence,
            "strategic_fit_score":   float(fit_score),
            "portfolio_priority":    priority,
        }

    return compute_position_sizes(
        portfolio_id=portfolio_id,
        symbols=symbols,
        symbol_data=symbol_data,
        symbol_sectors=symbol_sectors,
        cash_pct=cash_pct,
        sector_weights=sector_weights,
        sector_limits=sector_limits_resolved,
        cash_min_pct=cash_min_pct,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _score_symbol(data: dict) -> tuple[float, ScoreBreakdown]:
    signal = str(data.get("signal") or "HOLD").upper()
    confidence = float(data.get("confidence") or 0.5)
    fit = float(data.get("strategic_fit_score") or 5.0)
    priority = str(data.get("portfolio_priority") or "MEDIUM").upper()

    sig_pts  = _SIGNAL_POINTS.get(signal, 1.0)
    conf_pts = round(confidence * 5.0, 4)
    fit_pts  = round(fit / 2.0, 4)
    pri_pts  = _PRIORITY_POINTS.get(priority, 2.0)

    total = round(sig_pts + conf_pts + fit_pts + pri_pts, 4)
    return total, ScoreBreakdown(
        signal_points=sig_pts,
        confidence_points=conf_pts,
        fit_points=fit_pts,
        priority_points=pri_pts,
    )


def _make_suggestion(
    sym: str,
    data: dict,
    suggested_pct: float,
) -> PositionSuggestion:
    score, breakdown = _score_symbol(data)
    return PositionSuggestion(
        symbol=sym,
        position_score=round(score, 2),
        suggested_pct=suggested_pct,
        signal=str(data.get("signal") or "HOLD").upper(),
        confidence=round(float(data.get("confidence") or 0.5), 3),
        breakdown=breakdown,
    )


def _build_reasoning(
    suggestions: list[PositionSuggestion],
    deployable: float,
    total_allocated: float,
    scale_factor: float,
    sector_allocs: dict[str, float],
    sector_limits: dict[str, float],
    sector_weights: dict[str, float],
) -> list[str]:
    if not suggestions:
        return ["No symbols provided."]

    if total_allocated < 0.01:
        for sec, alloc in sector_allocs.items():
            limit = sector_limits.get(sec, 40.0)
            current = sector_weights.get(sec, 0.0)
            if current >= limit:
                return [
                    f"No deployment possible — {sec} sector is already at or above "
                    f"its {limit:.0f}% limit."
                ]
        return ["No deployment possible — insufficient cash or binding sector constraints."]

    lines: list[str] = []

    if len(suggestions) > 1:
        top = suggestions[0]
        rest = suggestions[1:]
        component = _dominant_component(top, rest[0])
        lines.append(
            f"{top.symbol} received the largest allocation ({top.suggested_pct:.2f}%) "
            f"due to higher {component}."
        )

    if scale_factor < 0.999:
        binding_sector = _binding_sector(sector_allocs, sector_limits, sector_weights)
        if binding_sector:
            sec, alloc, limit, current = binding_sector
            lines.append(
                f"Allocations scaled to {scale_factor * 100:.0f}% of initial sizing "
                f"to stay within the {sec} sector cap "
                f"({current:.1f}% + {alloc:.1f}% → {limit:.0f}% limit)."
            )
    else:
        lines.append(
            f"Proportional sizing applied — {total_allocated:.1f}% of "
            f"{deployable:.1f}% deployable cash allocated."
        )

    return lines


def _dominant_component(top: PositionSuggestion, other: PositionSuggestion) -> str:
    diffs = {
        "signal strength":    top.breakdown.signal_points     - other.breakdown.signal_points,
        "signal confidence":  top.breakdown.confidence_points - other.breakdown.confidence_points,
        "portfolio fit":      top.breakdown.fit_points        - other.breakdown.fit_points,
        "portfolio priority": top.breakdown.priority_points   - other.breakdown.priority_points,
    }
    return max(diffs, key=lambda k: diffs[k])


def _binding_sector(
    sector_allocs: dict[str, float],
    sector_limits: dict[str, float],
    sector_weights: dict[str, float],
) -> tuple[str, float, float, float] | None:
    """Return (sector, alloc, limit, current) for the most constrained sector."""
    tightest: tuple[str, float, float, float] | None = None
    tightest_ratio = 1.0
    for sec, alloc in sector_allocs.items():
        if alloc <= 0:
            continue
        limit = sector_limits.get(sec, 40.0)
        current = sector_weights.get(sec, 0.0)
        headroom = limit - current
        if headroom > 0:
            ratio = alloc / headroom
            if ratio > tightest_ratio:
                tightest_ratio = ratio
                tightest = (sec, alloc, limit, current)
    return tightest
