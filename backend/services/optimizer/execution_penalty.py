"""Execution-risk judgment layer (Phase 3B.10, migrated by M31.2).

Consumes Registry-backed ExecutionInstrumentFacts and derives execution-quality
metadata from those facts plus available volume and price estimates. This
module does not resolve Registry identity and contains no symbol taxonomy.

Returns per-symbol ExecutionMetadata that is used to:
  1. Apply soft combined_score penalties for illiquid/DR assets
  2. Enforce reduced max-position caps for DRs (hard-capped at DR_MAX_POSITION_PCT)
  3. Generate execution warning labels injected into L1/L2 AI prompts
  4. Surface execution risk badges in the optimizer UI

Design contract:
  - NO live yfinance calls — data sourced from existing scores_map dicts
  - Graceful degradation — unresolved facts use an explicit, deletable legacy
    compatibility projection; compatibility output is never authoritative
  - Soft-only — never hard-bans assets; only reduces target weights and flags risk
  - Backward compatible — execution_context=None leaves all existing behavior unchanged
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from services.execution_instrument_facts import (
    ExecutionInstrumentFacts,
    ExecutionInstrumentForm,
    ExecutionResolutionOutcome,
    ExecutionRole,
)
from services.optimizer.execution_penalty_compat import (
    LEGACY_COMPATIBILITY_FALLBACK,
    classify_legacy_compatibility,
)

# ── Asset type constants ───────────────────────────────────────────────────────
ASSET_EQUITY = "EQUITY"
ASSET_DR     = "DR"
ASSET_ETF    = "ETF"
ASSET_INDEX  = "INDEX"
ASSET_OTHER  = "OTHER"

# ── Execution risk levels ──────────────────────────────────────────────────────
RISK_LOW      = "LOW"
RISK_MEDIUM   = "MEDIUM"
RISK_HIGH     = "HIGH"
RISK_CRITICAL = "CRITICAL"

REGISTRY_FACTS_CLASSIFICATION = "REGISTRY_EXECUTION_INSTRUMENT_FACTS"

# ── DR-specific allocation constraints ────────────────────────────────────────
# DRs have structurally lower liquidity than their underlying equities.
DR_MAX_POSITION_PCT        = 15.0    # hard cap per DR asset (vs normal 20-30%)
DR_MAX_PORTFOLIO_PCT       = 40.0    # total DR basket capped at 40% of portfolio
ILLIQUID_POSITION_CAP_PCT  = 10.0    # extra cap for critically illiquid assets

# ── Soft combined_score penalties ─────────────────────────────────────────────
# Applied additively: a DR with HIGH execution risk gets 4 + (8-4) = 8 pts penalty.
_PENALTY_DR              = 4.0   # base penalty for any DR asset
_PENALTY_HIGH_RISK       = 8.0   # penalty for HIGH execution risk (replaces DR base if higher)
_PENALTY_CRITICAL_RISK   = 14.0  # penalty for CRITICAL execution risk

# ── Liquidity scoring baselines by asset type ─────────────────────────────────
_LIQUIDITY_BASELINES: dict[str, float] = {
    ASSET_DR:     55.0,   # structurally less liquid than underlying
    ASSET_ETF:    75.0,   # typically highly liquid
    ASSET_INDEX:  90.0,   # legacy compatibility profile only
    ASSET_EQUITY: 68.0,   # regular SET/US equity baseline
    ASSET_OTHER:  68.0,   # neutral descriptive profile; never equity identity
}

_SPREAD_BASELINES: dict[str, float] = {
    ASSET_DR:     48.0,   # wider spreads than underlying
    ASSET_ETF:    72.0,
    ASSET_INDEX:  88.0,
    ASSET_EQUITY: 65.0,
    ASSET_OTHER:  65.0,
}

# Estimated round-trip slippage by risk level
_SLIPPAGE_ESTIMATES: dict[str, float] = {
    RISK_LOW:      0.15,
    RISK_MEDIUM:   0.30,
    RISK_HIGH:     0.65,
    RISK_CRITICAL: 1.50,
}

# DR assets get a slight slippage premium over the base risk estimate
_DR_SLIPPAGE_PREMIUM = 0.20


@dataclass
class ExecutionMetadata:
    symbol:                  str
    asset_type:              str            # risk profile; Registry OTHER stays OTHER
    liquidity_score:         float          # 0–100 (higher = more liquid)
    spread_score:            float          # 0–100 (higher = tighter spread)
    execution_quality_score: float          # 0–100 composite
    execution_risk:          str            # LOW | MEDIUM | HIGH | CRITICAL
    execution_warnings:      list[str]      # short warning labels for UI
    position_cap_pct:        float | None   # reduced position cap; None = use standard
    slippage_cost_est_pct:   float          # estimated round-trip slippage %
    combined_score_penalty:  float          # soft score reduction to apply
    resolution_status:       str            # RESOLVED | UNKNOWN | AMBIGUOUS | NOT_TRADABLE
    instrument_form:         str            # authoritative Registry facts form
    execution_role:          str            # TRADABLE | REFERENCE | UNKNOWN
    classification_source:   str            # Registry facts or named compatibility path
    classification_warning:  str | None     # diagnostic; separate from risk warnings
    legacy_asset_type:       str            # shadow-only pre-M31.2 projection
    classification_agrees:   bool | None    # Registry/legacy shadow comparison


@dataclass(frozen=True)
class _ClassificationDecision:
    asset_type: str
    resolution_status: str
    instrument_form: str
    execution_role: str
    classification_source: str
    classification_warning: str | None
    legacy_asset_type: str
    classification_agrees: bool | None


_FORM_TO_RISK_PROFILE = {
    ExecutionInstrumentForm.EQUITY: ASSET_EQUITY,
    ExecutionInstrumentForm.ETF: ASSET_ETF,
    ExecutionInstrumentForm.DEPOSITARY_RECEIPT: ASSET_DR,
    ExecutionInstrumentForm.OTHER: ASSET_OTHER,
}


def _classification_for_risk_judgment(
    symbol: str,
    is_dr: bool,
    facts: ExecutionInstrumentFacts | None,
) -> _ClassificationDecision:
    """Select a scoring profile without resolving identity or mutating facts."""

    legacy = classify_legacy_compatibility(symbol, is_dr)
    if facts is None:
        return _ClassificationDecision(
            asset_type=legacy.asset_type,
            resolution_status=ExecutionResolutionOutcome.UNKNOWN.value,
            instrument_form=ExecutionInstrumentForm.UNKNOWN.value,
            execution_role=ExecutionRole.UNKNOWN.value,
            classification_source=LEGACY_COMPATIBILITY_FALLBACK,
            classification_warning=(
                "UNKNOWN: no ExecutionInstrumentFacts supplied; execution-risk "
                "assumptions use the deletable legacy compatibility fallback"
            ),
            legacy_asset_type=legacy.asset_type,
            classification_agrees=None,
        )

    if facts.resolution_status in (
        ExecutionResolutionOutcome.UNKNOWN,
        ExecutionResolutionOutcome.AMBIGUOUS,
    ):
        reason = f" ({facts.reason})" if facts.reason else ""
        return _ClassificationDecision(
            asset_type=legacy.asset_type,
            resolution_status=facts.resolution_status.value,
            instrument_form=facts.instrument_form.value,
            execution_role=facts.execution_role.value,
            classification_source=LEGACY_COMPATIBILITY_FALLBACK,
            classification_warning=(
                f"{facts.resolution_status.value}: Registry execution facts are "
                f"unresolved{reason}; execution-risk assumptions use the deletable "
                "legacy compatibility fallback"
            ),
            legacy_asset_type=legacy.asset_type,
            classification_agrees=None,
        )

    asset_type = _FORM_TO_RISK_PROFILE.get(facts.instrument_form, ASSET_OTHER)
    agrees = asset_type == legacy.asset_type
    warning: str | None = None
    if facts.resolution_status == ExecutionResolutionOutcome.NOT_TRADABLE:
        reason = f" ({facts.reason})" if facts.reason else ""
        warning = (
            f"NOT_TRADABLE: Registry facts identify a non-executable "
            f"{facts.execution_role.value} asset{reason}; M31.2 scoring is "
            "descriptive only and adds no blocking enforcement"
        )
    elif not agrees:
        warning = (
            "SHADOW_MISMATCH: Registry instrument form "
            f"{facts.instrument_form.value} overrides legacy projection "
            f"{legacy.asset_type}"
        )

    return _ClassificationDecision(
        asset_type=asset_type,
        resolution_status=facts.resolution_status.value,
        instrument_form=facts.instrument_form.value,
        execution_role=facts.execution_role.value,
        classification_source=REGISTRY_FACTS_CLASSIFICATION,
        classification_warning=warning,
        legacy_asset_type=legacy.asset_type,
        classification_agrees=agrees,
    )


def classify_execution(
    symbol: str,
    is_dr: bool,
    volume: int | None = None,
    avg_volume: int | None = None,
    current_price: float | None = None,
    *,
    facts: ExecutionInstrumentFacts | None = None,
) -> ExecutionMetadata:
    """Classify execution quality for a single symbol using available metadata.

    Derives liquidity/spread scores from facts-selected assumptions plus volume.
    Missing Registry facts remain explicit and use the named compatibility path.
    """
    classification = _classification_for_risk_judgment(symbol, is_dr, facts)
    asset_type = classification.asset_type

    liquidity_score = float(_LIQUIDITY_BASELINES[asset_type])
    spread_score    = float(_SPREAD_BASELINES[asset_type])

    # ── Volume-based liquidity adjustment (when data available) ───────────────
    # Estimate avg daily traded value; normalize against Thai SET thresholds.
    if avg_volume is not None and current_price is not None and current_price > 0:
        est_adtv = avg_volume * current_price
    elif volume is not None and current_price is not None and current_price > 0:
        est_adtv = volume * current_price
    else:
        est_adtv = None

    if est_adtv is not None:
        if est_adtv > 100_000_000:       # >100M THB/day — very liquid
            liquidity_score = min(92.0, liquidity_score + 15.0)
        elif est_adtv > 20_000_000:      # >20M — liquid
            liquidity_score = min(85.0, liquidity_score + 8.0)
        elif est_adtv < 1_000_000:       # <1M — thin
            liquidity_score = max(15.0, liquidity_score - 20.0)
            spread_score    = max(20.0, spread_score - 15.0)
        elif est_adtv < 5_000_000:       # <5M — low
            liquidity_score = max(30.0, liquidity_score - 10.0)
            spread_score    = max(35.0, spread_score - 8.0)

    # ── Composite execution quality ────────────────────────────────────────────
    execution_quality_score = round(0.60 * liquidity_score + 0.40 * spread_score, 1)

    # ── Risk classification ────────────────────────────────────────────────────
    if execution_quality_score >= 70:
        risk = RISK_LOW
    elif execution_quality_score >= 52:
        risk = RISK_MEDIUM
    elif execution_quality_score >= 35:
        risk = RISK_HIGH
    else:
        risk = RISK_CRITICAL

    # ── Warning labels ─────────────────────────────────────────────────────────
    warnings: list[str] = []
    if asset_type == ASSET_DR:
        warnings.append("DR - Execution Sensitive")
    if liquidity_score < 45:
        warnings.append("Thin Liquidity")
    elif liquidity_score < 58:
        warnings.append("Low Liquidity")
    if spread_score < 45:
        warnings.append("High Spread")
    if risk == RISK_HIGH:
        warnings.append("High Slippage Risk")
    elif risk == RISK_CRITICAL:
        warnings.append("Critical Execution Risk")

    # ── Position cap (only set when tighter than standard) ────────────────────
    if asset_type == ASSET_DR:
        position_cap: float | None = (
            ILLIQUID_POSITION_CAP_PCT if risk in (RISK_HIGH, RISK_CRITICAL)
            else DR_MAX_POSITION_PCT
        )
    elif risk == RISK_CRITICAL:
        position_cap = ILLIQUID_POSITION_CAP_PCT
    else:
        position_cap = None   # defer to standard constraint resolver

    # ── Slippage estimate ──────────────────────────────────────────────────────
    base_slip = _SLIPPAGE_ESTIMATES[risk]
    slippage  = round(base_slip + (_DR_SLIPPAGE_PREMIUM if asset_type == ASSET_DR else 0.0), 2)

    # ── Soft score penalty ─────────────────────────────────────────────────────
    if asset_type == ASSET_DR:
        penalty = max(_PENALTY_DR, _PENALTY_HIGH_RISK if risk == RISK_HIGH
                      else _PENALTY_CRITICAL_RISK if risk == RISK_CRITICAL else _PENALTY_DR)
    elif risk == RISK_HIGH:
        penalty = _PENALTY_HIGH_RISK
    elif risk == RISK_CRITICAL:
        penalty = _PENALTY_CRITICAL_RISK
    else:
        penalty = 0.0

    return ExecutionMetadata(
        symbol=symbol,
        asset_type=asset_type,
        liquidity_score=round(liquidity_score, 1),
        spread_score=round(spread_score, 1),
        execution_quality_score=execution_quality_score,
        execution_risk=risk,
        execution_warnings=warnings,
        position_cap_pct=position_cap,
        slippage_cost_est_pct=slippage,
        combined_score_penalty=penalty,
        resolution_status=classification.resolution_status,
        instrument_form=classification.instrument_form,
        execution_role=classification.execution_role,
        classification_source=classification.classification_source,
        classification_warning=classification.classification_warning,
        legacy_asset_type=classification.legacy_asset_type,
        classification_agrees=classification.classification_agrees,
    )


def compute_portfolio_execution_context(
    scores_map: dict[str, dict],
    facts_by_symbol: Mapping[str, ExecutionInstrumentFacts] | None = None,
) -> dict:
    """Compute execution metadata for the full portfolio + watchlist scores_map.

    Returns a context dict consumed by:
      - run_layered_optimizer (prompt injection + post-AI cap enforcement)
      - analyze_optimizer (surfaced in API result as execution_context)
      - Frontend AllocationTable (badge rendering)
    """
    per_symbol: dict[str, dict] = {}
    dr_syms:    list[str] = []
    high_risk:  list[str] = []

    supplied_facts = facts_by_symbol or {}
    for sym, data in scores_map.items():
        is_dr = bool(data.get("is_dr", False))
        meta  = classify_execution(
            symbol=sym,
            is_dr=is_dr,
            volume=data.get("volume"),
            avg_volume=data.get("avg_volume"),
            current_price=data.get("current_price"),
            facts=supplied_facts.get(sym),
        )
        per_symbol[sym] = {
            "asset_type":              meta.asset_type,
            "liquidity_score":         meta.liquidity_score,
            "spread_score":            meta.spread_score,
            "execution_quality_score": meta.execution_quality_score,
            "execution_risk":          meta.execution_risk,
            "execution_warnings":      meta.execution_warnings,
            "position_cap_pct":        meta.position_cap_pct,
            "slippage_cost_est_pct":   meta.slippage_cost_est_pct,
            "combined_score_penalty":  meta.combined_score_penalty,
            "resolution_status":       meta.resolution_status,
            "instrument_form":         meta.instrument_form,
            "execution_role":          meta.execution_role,
            "classification_source":   meta.classification_source,
            "classification_warning":  meta.classification_warning,
            "legacy_asset_type":       meta.legacy_asset_type,
            "classification_agrees":   meta.classification_agrees,
        }
        if meta.asset_type == ASSET_DR:
            dr_syms.append(sym)
        if meta.execution_risk in (RISK_HIGH, RISK_CRITICAL):
            high_risk.append(sym)

    # Human-readable summary for the prompt block
    parts: list[str] = []
    if dr_syms:
        parts.append(f"{len(dr_syms)} DR asset(s): {', '.join(dr_syms[:6])}")
    non_dr_high = [s for s in high_risk if s not in dr_syms]
    if non_dr_high:
        parts.append(f"{len(non_dr_high)} illiquid non-DR asset(s): {', '.join(non_dr_high[:4])}")
    summary = (
        f"Execution-sensitive assets: {'; '.join(parts)}."
        if parts else
        "No significant execution constraints identified."
    )

    return {
        "per_symbol":        per_symbol,
        "has_dr_assets":     len(dr_syms) > 0,
        "dr_symbols":        dr_syms,
        "high_risk_symbols": high_risk,
        "dr_position_cap":   DR_MAX_POSITION_PCT,
        "dr_portfolio_cap":  DR_MAX_PORTFOLIO_PCT,
        "execution_summary": summary,
    }


def apply_execution_score_penalties(
    scores_map: dict[str, dict],
    execution_ctx: dict,
) -> None:
    """Mutate scores_map in-place: reduce combined_score by execution penalty.

    Only affects combined_score when penalty > 0 (DRs / illiquid assets).
    The penalty is capped so combined_score never goes below 5.
    """
    per_sym = execution_ctx.get("per_symbol", {})
    for sym, meta in per_sym.items():
        penalty = float(meta.get("combined_score_penalty", 0.0))
        if penalty > 0 and sym in scores_map:
            original = float(scores_map[sym].get("combined_score", 0))
            scores_map[sym]["combined_score"] = round(max(5.0, original - penalty), 1)
            scores_map[sym]["execution_penalized"] = True


def build_execution_prompt_block(execution_ctx: dict) -> str:
    """Return the [EXECUTION QUALITY] governance block for L1/L2 prompts.

    Returns empty string when there are no execution-sensitive assets,
    keeping prompts unchanged for pure-equity portfolios.
    """
    if not execution_ctx:
        return ""

    dr_syms   = execution_ctx.get("dr_symbols", [])
    high_risk = execution_ctx.get("high_risk_symbols", [])
    dr_cap    = execution_ctx.get("dr_position_cap", DR_MAX_POSITION_PCT)
    port_cap  = execution_ctx.get("dr_portfolio_cap", DR_MAX_PORTFOLIO_PCT)
    per_sym   = execution_ctx.get("per_symbol", {})

    # Skip block entirely if no DR assets and no high-risk equities
    if not dr_syms and not high_risk:
        return ""

    lines = ["[EXECUTION QUALITY — MANDATORY CONSTRAINTS]"]

    if dr_syms:
        lines.append(
            f"DR assets (Thai Depository Receipts): {', '.join(dr_syms)}"
        )
        lines.append(
            f"  -> MAX {dr_cap:.0f}% per DR asset (hard allocation cap — do NOT exceed)"
        )
        lines.append(
            f"  -> Total DR basket: max {port_cap:.0f}% of portfolio combined"
        )
        lines.append(
            "  -> DRs trade with wider bid/ask spreads and lower depth than underlying equities"
        )
        lines.append(
            "  -> Prefer GRADUAL accumulation for DRs; avoid large single-step DR allocation jumps"
        )

    non_dr_high = [s for s in high_risk if s not in dr_syms]
    if non_dr_high:
        lines.append(f"High execution risk (non-DR): {', '.join(non_dr_high)}")
        lines.append(
            "  -> Large trades into thin-liquidity positions increase slippage significantly"
        )

    # Per-asset slippage notes — only for MEDIUM/HIGH/CRITICAL assets; limit to 6
    relevant = [
        (sym, d)
        for sym, d in per_sym.items()
        if d.get("execution_risk") in (RISK_MEDIUM, RISK_HIGH, RISK_CRITICAL)
        and d.get("execution_warnings")
    ]
    if relevant:
        lines.append("Execution notes per asset:")
        for sym, d in relevant[:6]:
            warns = ", ".join(d["execution_warnings"])
            slip  = d.get("slippage_cost_est_pct", 0.3)
            lines.append(f"  {sym}: {warns} (est. ~{slip:.1f}% slippage)")

    lines.append("")   # blank line to separate from next block
    return "\n".join(lines) + "\n"
