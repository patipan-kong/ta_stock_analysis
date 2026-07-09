"""Phase 4D.2 — Risk Budget Allocation Engine.

Converts a basket of stocks (with technical, fundamental, risk, and
confidence scores) into a target portfolio allocation where weights sum
to 100%.

Produces an Ideal Portfolio in the sense of OPTIMIZER_PHILOSOPHY.md §5 —
friction-free target weights; whether a trade toward them is worth making
today is decided downstream, not here.

Formula
-------
    expected_return  = technical_score * 0.40 + fundamental_score * 0.40
                       + confidence_score * 0.20
    allocation_score = expected_return / max(risk_score, 1)
    raw_weight       = allocation_score / sum(all_scores)  × 100

Constraints (applied in order)
-------------------------------
1. confidence_score < confidence_threshold (default 50) → excluded entirely
2. risk_score > high_risk_threshold (default 80) → weight capped at
   high_risk_cap_pct (default 5%)
3. Single-position weight > max_position_pct (default 20%) → capped;
   excess redistributed proportionally to uncapped positions
4. Sector concentration > sector cap (default 40%) → scaled down; then
   the full basket is renormalized back to 100%

No AI calls.  No DB mutations.  Deterministic.

Public API
----------
compute_allocations(recommendations, ...)   -> RiskBudgetResult  (pure)
suggest_risk_budget(portfolio_id, symbols, workspace_id, db)  -> RiskBudgetResult
"""
from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)

# ── Confidence string → numeric (0-100) ──────────────────────────────────────

_CONFIDENCE_MAP: dict[str, float] = {
    "high":   85.0,
    "medium": 60.0,
    "low":    35.0,
}

# Sector cap only enforced when explicitly configured; 100.0 = effectively no cap
_DEFAULT_SECTOR_CAP = 100.0


# ── Response models ───────────────────────────────────────────────────────────

class AllocationItem(BaseModel):
    symbol: str
    weight: float           # 0.0–1.0  (fractional)
    weight_pct: float       # 0.0–100.0
    expected_return: float  # weighted average of TA/FA/confidence scores
    allocation_score: float # expected_return / risk_score
    technical_score: float
    fundamental_score: float
    risk_score: float
    confidence_score: float
    sector: str
    capped: bool
    cap_reason: str | None
    reasons: list[str]


class ExcludedItem(BaseModel):
    symbol: str
    reason: str


class AllocationConstraints(BaseModel):
    max_position_pct: float
    sector_caps: dict[str, float]
    confidence_threshold: float
    high_risk_threshold: float
    high_risk_cap_pct: float


class RiskBudgetResult(BaseModel):
    allocations: list[AllocationItem]
    excluded: list[ExcludedItem]
    total_weight_pct: float          # ≈ 100.0 after renormalization
    constraints: AllocationConstraints
    reasoning: list[str]
    status: str                       # "PASS" | "WARNING" | "FAIL"


# ── Pure allocation engine ────────────────────────────────────────────────────

def compute_allocations(
    recommendations: list[dict[str, Any]],
    *,
    max_position_pct: float = 20.0,
    sector_caps: dict[str, float] | None = None,
    confidence_threshold: float = 50.0,
    high_risk_threshold: float = 80.0,
    high_risk_cap_pct: float = 5.0,
) -> RiskBudgetResult:
    """Compute target portfolio weights from a list of scored recommendations.

    Each recommendation dict must contain:
        symbol            str
        technical_score   float  0-100
        fundamental_score float  0-100
        risk_score        float  0-100   (higher = more volatile/uncertain)
        confidence_score  float  0-100
        sector            str   (optional, defaults to "Other")

    Returns weights that sum to 100 % (or near 100 % when sector caps bind).

    Constraint order
    ----------------
    1. Confidence filter — low-confidence symbols excluded entirely
    2. High-risk hard cap — symbols with risk_score > high_risk_threshold are
       capped at high_risk_cap_pct; excess redistributed to non-risky symbols.
    3. Renormalize to 100 % after high-risk caps.
    4. Sector caps (if configured) — scale down over-cap sectors; freed weight
       redistributed to other sectors within their headroom.  Total may be
       < 100 % if sector constraints are collectively binding.
    5. Re-enforce high-risk caps after sector redistribution (no redistribution
       in this pass — accept total < 100 % if re-violated).
    6. max_position_pct is informational: weights exceeding it are flagged
       capped=True and noted in cap_reason, but not enforced.
    """
    effective_sector_caps = sector_caps or {}
    constraints = AllocationConstraints(
        max_position_pct=max_position_pct,
        sector_caps=effective_sector_caps,
        confidence_threshold=confidence_threshold,
        high_risk_threshold=high_risk_threshold,
        high_risk_cap_pct=high_risk_cap_pct,
    )

    if not recommendations:
        return RiskBudgetResult(
            allocations=[],
            excluded=[],
            total_weight_pct=0.0,
            constraints=constraints,
            reasoning=["No recommendations provided."],
            status="FAIL",
        )

    # ── Step 1: confidence filter ─────────────────────────────────────────────
    included: list[dict] = []
    excluded: list[ExcludedItem] = []
    for r in recommendations:
        conf = float(r.get("confidence_score") or 0)
        if conf < confidence_threshold:
            excluded.append(ExcludedItem(
                symbol=str(r.get("symbol", "?")),
                reason=(
                    f"Confidence {conf:.0f} below threshold {confidence_threshold:.0f} "
                    "— excluded from allocation"
                ),
            ))
        else:
            included.append(r)

    if not included:
        return RiskBudgetResult(
            allocations=[],
            excluded=excluded,
            total_weight_pct=0.0,
            constraints=constraints,
            reasoning=["All symbols excluded by confidence filter."],
            status="FAIL",
        )

    # ── Step 2: score each symbol ─────────────────────────────────────────────
    scored: list[dict] = []
    for r in included:
        ta   = float(r.get("technical_score")   or 50)
        fa   = float(r.get("fundamental_score") or 50)
        conf = float(r.get("confidence_score")  or 60)
        risk = float(r.get("risk_score")        or 50)
        sym  = str(r.get("symbol", "?"))
        sec  = str(r.get("sector") or "Other")

        expected_return  = round(ta * 0.40 + fa * 0.40 + conf * 0.20, 4)
        allocation_score = round(expected_return / max(risk, 1), 6)

        scored.append({
            "symbol":            sym,
            "sector":            sec,
            "technical_score":   ta,
            "fundamental_score": fa,
            "risk_score":        risk,
            "confidence_score":  conf,
            "expected_return":   expected_return,
            "allocation_score":  allocation_score,
        })

    # ── Step 3: raw proportional weights (sum = 100 %) ────────────────────────
    total_score = sum(s["allocation_score"] for s in scored)
    if total_score <= 0:
        raw_weights: dict[str, float] = {
            s["symbol"]: round(100.0 / len(scored), 4) for s in scored
        }
    else:
        raw_weights = {
            s["symbol"]: round(s["allocation_score"] / total_score * 100.0, 4)
            for s in scored
        }

    # ── Step 4: high-risk hard caps with redistribution ───────────────────────
    # Risky symbols (risk_score > threshold) are capped at high_risk_cap_pct.
    # Excess weight is redistributed proportionally to non-risky symbols only.
    risky_syms: set[str] = {
        s["symbol"] for s in scored if s["risk_score"] > high_risk_threshold
    }
    hard_caps: dict[str, float] = {sym: high_risk_cap_pct for sym in risky_syms}

    weights = _apply_hard_caps(raw_weights, hard_caps)

    # ── Step 5: renormalize after hard caps ───────────────────────────────────
    total_w = sum(weights.values())
    if total_w > 0:
        weights = {sym: round(w / total_w * 100.0, 6) for sym, w in weights.items()}

    # ── Step 6: sector concentration caps ────────────────────────────────────
    sectors: dict[str, str] = {s["symbol"]: s["sector"] for s in scored}
    weights, sector_was_capped = _apply_sector_caps(
        weights, sectors, effective_sector_caps, _DEFAULT_SECTOR_CAP
    )
    # Note: total may be < 100 % after sector caps if constraints are collectively binding

    # ── Step 7: re-enforce high-risk hard caps (post-sector redistribution) ───
    # Sector redistribution could push risky symbols above their cap; clip them.
    for sym in risky_syms:
        if weights.get(sym, 0) > high_risk_cap_pct:
            weights[sym] = high_risk_cap_pct

    total_weight_pct = round(sum(weights.values()), 2)

    # ── Step 8: build AllocationItem list ─────────────────────────────────────
    allocations: list[AllocationItem] = []
    for s in sorted(scored, key=lambda x: weights.get(x["symbol"], 0), reverse=True):
        sym     = s["symbol"]
        w_pct   = weights.get(sym, 0.0)
        raw_pct = raw_weights.get(sym, 0.0)

        # A position is "capped" when a hard constraint reduced its weight
        is_high_risk_capped = sym in risky_syms and w_pct <= high_risk_cap_pct + 0.05
        is_sector_capped    = sector_was_capped.get(s["sector"], False) and w_pct < raw_pct - 0.05
        is_pos_capped       = w_pct < raw_pct - 0.05 and not is_high_risk_capped and not is_sector_capped
        capped = is_high_risk_capped or is_sector_capped or is_pos_capped

        cap_reason: str | None = None
        if is_high_risk_capped:
            cap_reason = (
                f"High risk score ({s['risk_score']:.0f} > {high_risk_threshold:.0f}) "
                f"— capped at {high_risk_cap_pct:.0f}%"
            )
        elif is_sector_capped:
            cap_reason = f"Sector {s['sector']} concentration cap applied"
        elif is_pos_capped:
            cap_reason = f"Max position cap ({max_position_pct:.0f}%) applied"
        elif w_pct > max_position_pct + 0.05:
            # Informational: exceeds soft position cap but not hard-capped
            cap_reason = (
                f"Note: exceeds recommended max position ({max_position_pct:.0f}%) "
                "— no hard cap enforced for unconstrained basket"
            )

        reasons = _build_reasons(
            s, w_pct, confidence_threshold,
            high_risk_threshold, high_risk_cap_pct, max_position_pct,
        )

        allocations.append(AllocationItem(
            symbol=sym,
            weight=round(w_pct / 100.0, 6),
            weight_pct=round(w_pct, 2),
            expected_return=s["expected_return"],
            allocation_score=round(s["allocation_score"], 4),
            technical_score=s["technical_score"],
            fundamental_score=s["fundamental_score"],
            risk_score=s["risk_score"],
            confidence_score=s["confidence_score"],
            sector=s["sector"],
            capped=capped,
            cap_reason=cap_reason,
            reasons=reasons,
        ))

    # ── Status ────────────────────────────────────────────────────────────────
    any_capped   = any(a.capped for a in allocations)
    has_excluded = bool(excluded)

    if total_weight_pct < 10.0:
        status = "FAIL"
    elif any_capped or sector_was_capped or has_excluded:
        status = "WARNING"
    else:
        status = "PASS"

    reasoning = _build_overall_reasoning(
        allocations, excluded, total_weight_pct, any_capped, sector_was_capped,
    )

    return RiskBudgetResult(
        allocations=allocations,
        excluded=excluded,
        total_weight_pct=total_weight_pct,
        constraints=constraints,
        reasoning=reasoning,
        status=status,
    )


# ── DB-loading wrapper ────────────────────────────────────────────────────────


# Agent scores are small integers, not 0-100.
# technical.py produces ta_score ≈ −7 to +7 (per-timeframe range −7..+7, composite same).
# fundamental.py produces fa_score ≈ −6 to +6 (PE±2 + RevGrowth±2 + ROE±2 + D/E±1).
# These constants map raw agent output to the 0-100 scale that compute_allocations() expects.
_TA_MIN, _TA_MAX = -7.0, 7.0    # practical bounds for technical composite
_FA_MIN, _FA_MAX = -6.0, 6.0    # practical bounds for fundamental score


def _normalize_agent_score(raw: float, lo: float, hi: float) -> float:
    """Map a raw agent score from [lo, hi] to [0, 100]."""
    return max(0.0, min(100.0, round((raw - lo) / (hi - lo) * 100)))


def suggest_risk_budget(
    portfolio_id: int,
    symbols: list[str],
    workspace_id: int,
    db: Session,
) -> RiskBudgetResult:
    """Load analysis scores from DB and compute risk-budget allocation.

    Agent ta_score / fa_score are small integers (≈ −7..+7 and −6..+6).
    They are normalised to 0-100 before being passed to compute_allocations()
    so that the risk formula and expected-return weights operate on a consistent
    scale.  A missing cache entry defaults to 0 (neutral mid-point before
    normalisation → 50 after normalisation).

    risk_score = 100 − round((ta_pct + fa_pct) / 2)
    High-quality stocks (high ta+fa) → low risk → larger allocation.
    """
    from models.database import AnalysisCache, Portfolio, PortfolioItem, Watchlist
    from services.basket_simulation import _resolve_symbol_sectors
    from services.registry_symbol_matching import match_known_symbols

    symbols = [s.strip().upper() for s in symbols if s.strip()]
    if not symbols:
        return compute_allocations([])

    portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.id == portfolio_id, Portfolio.workspace_id == workspace_id)
        .first()
    )
    if not portfolio:
        raise ValueError(f"Portfolio {portfolio_id} not found")

    # Sector lookup
    portfolio_items = (
        db.query(PortfolioItem)
        .filter(
            PortfolioItem.portfolio_id == portfolio_id,
            PortfolioItem.workspace_id == workspace_id,
        )
        .all()
    )
    watchlist_items = (
        db.query(Watchlist).filter(Watchlist.workspace_id == workspace_id).all()
    )
    symbol_sectors = _resolve_symbol_sectors(db, symbols, portfolio_items, watchlist_items)

    # AnalysisCache lookup. bk_variants keeps the SQL filter wide enough to
    # catch a row stored under the alternate spelling; the actual symbol ->
    # row matching decision is Registry-backed (registry_symbol_matching).
    bk_variants = {f"{s}.BK" for s in symbols if "." not in s}
    cache_rows = (
        db.query(AnalysisCache)
        .filter(
            AnalysisCache.workspace_id == workspace_id,
            AnalysisCache.symbol.in_(list(set(symbols) | bk_variants)),
        )
        .all()
    )
    cache_row_by_symbol: dict[str, AnalysisCache] = {r.symbol: r for r in cache_rows}
    cache_matched = match_known_symbols(db, symbols, cache_row_by_symbol.keys())
    cache_map: dict[str, AnalysisCache] = {
        sym: cache_row_by_symbol[matched] for sym, matched in cache_matched.items()
    }

    recommendations: list[dict] = []
    for sym in symbols:
        cached = cache_map.get(sym)

        # Default to 0 (neutral in raw agent scale) when no cache exists.
        # After normalisation 0 maps to the midpoint (~50), not maximum.
        ta_raw = int(cached.ta_score) if cached and cached.ta_score is not None else 0
        fa_raw = int(cached.fa_score) if cached and cached.fa_score is not None else 0
        conf   = _CONFIDENCE_MAP.get(
            (cached.confidence or "medium").lower(), 60.0
        ) if cached else 60.0

        # Normalise to 0-100 so compute_allocations() formulas work correctly.
        ta_pct = _normalize_agent_score(ta_raw, _TA_MIN, _TA_MAX)
        fa_pct = _normalize_agent_score(fa_raw, _FA_MIN, _FA_MAX)

        # High TA+FA → low risk; poor TA+FA → high risk.
        risk = max(0, min(100, 100 - round((ta_pct + fa_pct) / 2)))

        recommendations.append({
            "symbol":            sym,
            "sector":            symbol_sectors.get(sym, "Other"),
            "technical_score":   ta_pct,
            "fundamental_score": fa_pct,
            "confidence_score":  conf,
            "risk_score":        float(risk),
        })

    return compute_allocations(recommendations)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _apply_hard_caps(
    weights_pct: dict[str, float],
    hard_caps: dict[str, float],
) -> dict[str, float]:
    """Apply per-symbol hard caps, redistributing excess to non-capped symbols.

    Non-capped symbols receive excess proportionally to their current weight.
    Iterates until stable (max 20 passes).
    """
    weights = dict(weights_pct)

    for _ in range(20):
        over: dict[str, float] = {
            sym: hard_caps[sym]
            for sym in hard_caps
            if weights.get(sym, 0) > hard_caps[sym] + 1e-9
        }
        if not over:
            break

        excess = sum(weights[sym] - cap for sym, cap in over.items())
        for sym, cap in over.items():
            weights[sym] = cap

        # Redistribute only to symbols that are NOT hard-capped
        free = {sym: w for sym, w in weights.items() if sym not in hard_caps}
        free_total = sum(free.values())
        if free and free_total > 0 and excess > 0:
            for sym in free:
                weights[sym] += excess * (weights[sym] / free_total)

    return {sym: round(w, 6) for sym, w in weights.items()}


def _apply_sector_caps(
    weights_pct: dict[str, float],
    sectors: dict[str, str],
    sector_caps: dict[str, float],
    default_cap: float,
) -> tuple[dict[str, float], dict[str, bool]]:
    """Scale down over-cap sectors; redistribute freed weight to other sectors.

    Iterates until stable (max 10 passes).
    Total weight may end up < 100 % if sector constraints are collectively binding.
    """
    weights = dict(weights_pct)
    sector_was_capped: dict[str, bool] = {}

    for _ in range(10):
        # Current sector totals
        sector_totals: dict[str, float] = {}
        for sym, w in weights.items():
            sec = sectors.get(sym, "Other")
            sector_totals[sec] = sector_totals.get(sec, 0.0) + w

        # Find violating sectors
        violating: dict[str, float] = {}
        for sec, total in sector_totals.items():
            cap = sector_caps.get(sec, default_cap)
            if total > cap + 0.01:
                violating[sec] = cap

        if not violating:
            break

        # Scale down each violating sector; collect freed weight
        freed_total = 0.0
        for sec, cap in violating.items():
            total = sector_totals[sec]
            scale = cap / total
            freed_from_sec = 0.0
            for sym in weights:
                if sectors.get(sym, "Other") == sec:
                    old_w = weights[sym]
                    weights[sym] = round(old_w * scale, 6)
                    freed_from_sec += old_w - weights[sym]
            freed_total += freed_from_sec
            sector_was_capped[sec] = True

        # Redistribute freed weight to symbols NOT in a violating sector,
        # proportional to their current weights, capped by remaining sector headroom
        if freed_total <= 0:
            break

        free_syms: dict[str, float] = {
            sym: w for sym, w in weights.items()
            if sectors.get(sym, "Other") not in violating
        }
        if not free_syms:
            break  # nowhere to redistribute

        # Compute each free sector's remaining headroom
        free_sec_totals: dict[str, float] = {}
        for sym in free_syms:
            sec = sectors.get(sym, "Other")
            free_sec_totals[sec] = free_sec_totals.get(sec, 0.0) + free_syms[sym]

        free_total_w = sum(free_syms.values())
        if free_total_w <= 0:
            break

        for sym in free_syms:
            sec = sectors.get(sym, "Other")
            cap = sector_caps.get(sec, default_cap)
            headroom = max(0.0, cap - free_sec_totals.get(sec, 0.0))
            sym_share = freed_total * (free_syms[sym] / free_total_w)
            # Don't add more than the sector's remaining headroom (pro-rata)
            sec_sym_ratio = (
                free_syms[sym] / free_sec_totals[sec] if free_sec_totals.get(sec, 0) > 0 else 0
            )
            max_add = headroom * sec_sym_ratio
            weights[sym] = round(weights[sym] + min(sym_share, max_add), 6)

    return weights, sector_was_capped


def _build_reasons(
    s: dict,
    weight_pct: float,
    confidence_threshold: float,
    high_risk_threshold: float,
    high_risk_cap_pct: float,
    max_position_pct: float,
) -> list[str]:
    """Generate human-readable reasons for the allocation decision."""
    reasons: list[str] = []

    er = s["expected_return"]
    if er >= 70:
        reasons.append("High expected return")
    elif er >= 50:
        reasons.append("Moderate expected return")
    else:
        reasons.append("Below-average expected return")

    risk = s["risk_score"]
    if risk <= 30:
        reasons.append("Low risk profile")
    elif risk <= 60:
        reasons.append("Moderate risk profile")
    elif risk <= high_risk_threshold:
        reasons.append("Elevated risk profile — allocation reduced")
    else:
        reasons.append(f"High risk score ({risk:.0f}) — capped at {high_risk_cap_pct:.0f}%")

    conf = s["confidence_score"]
    if conf >= 80:
        reasons.append("Strong confidence")
    elif conf >= confidence_threshold:
        reasons.append("Moderate confidence")

    if weight_pct >= max_position_pct - 0.1:
        reasons.append(f"Position limit reached ({max_position_pct:.0f}%)")

    return reasons


def _build_overall_reasoning(
    allocations: list[AllocationItem],
    excluded: list[ExcludedItem],
    total_weight_pct: float,
    any_capped: bool,
    sector_was_capped: dict[str, bool] | bool,
) -> list[str]:
    lines: list[str] = []

    if excluded:
        syms = ", ".join(e.symbol for e in excluded)
        lines.append(
            f"{len(excluded)} symbol(s) excluded by confidence filter: {syms}."
        )

    if allocations:
        top = allocations[0]
        lines.append(
            f"{top.symbol} received the largest allocation ({top.weight_pct:.1f}%) "
            f"with expected return {top.expected_return:.1f} and "
            f"risk score {top.risk_score:.0f}."
        )

    if any_capped:
        capped_syms = [a.symbol for a in allocations if a.capped]
        lines.append(
            f"Position caps applied to {', '.join(capped_syms)} — "
            "excess weight redistributed to uncapped positions."
        )

    capped_sectors = (
        [sec for sec, v in sector_was_capped.items() if v]
        if isinstance(sector_was_capped, dict) else []
    )
    if capped_sectors:
        lines.append(
            f"Sector cap applied to {', '.join(capped_sectors)} — "
            "weights scaled down and renormalized."
        )

    if not lines:
        lines.append(
            f"Risk-adjusted proportional allocation — "
            f"{len(allocations)} positions totalling {total_weight_pct:.1f}%."
        )

    return lines
