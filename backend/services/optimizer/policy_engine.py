"""Adaptive Policy Engine — Phase 3B.4.

Synthesizes Strategy Persona, Market Regime, Portfolio Risk, and Confidence State
into a unified, deterministic Policy Envelope that governs all 3 AI optimizer layers.

The Policy Engine is the structural risk-governance layer above all AI agents.
AI recommendations operate INSIDE these deterministic constraints; they cannot
override hard limits regardless of what they propose.

Public API:
    compute_policy(persona_ctx, regime_ctx, portfolio_data, consensus, max_sector_pct)
        → PolicyEnvelope

    build_policy_prompt_block(envelope) → str
        → [ACTIVE OPTIMIZATION POLICY] block injected into L1/L2/L3 prompts

    compute_policy_alignment_score(final_allocations, envelope, total_value)
        → (policy_alignment_score, regime_compliance_score, risk_governance_score, flags)

    envelope_to_dict(envelope) → dict
        → JSON-serializable representation (includes prompt_block)
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)

# ─── Deployment bias labels ───────────────────────────────────────────────────

DEPLOY_AGGRESSIVE   = "AGGRESSIVE"
DEPLOY_SELECTIVE    = "SELECTIVE"
DEPLOY_DEFENSIVE    = "DEFENSIVE"
DEPLOY_PRESERVATION = "PRESERVATION"

_DEPLOY_ORDER = [DEPLOY_AGGRESSIVE, DEPLOY_SELECTIVE, DEPLOY_DEFENSIVE, DEPLOY_PRESERVATION]

# ─── Strictness level labels ──────────────────────────────────────────────────

STRICTNESS_RELAXED   = "RELAXED"
STRICTNESS_NORMAL    = "NORMAL"
STRICTNESS_STRICT    = "STRICT"
STRICTNESS_EMERGENCY = "EMERGENCY"

# ─── Emergency thresholds ─────────────────────────────────────────────────────

_EMERGENCY_VOL_Z            = 2.5    # vol z-score ≥ this → emergency
_EMERGENCY_DRAWDOWN         = 15.0   # drawdown_score ≤ this → emergency
_EMERGENCY_HIGH_VOL_CONF    = 0.65   # HIGH_VOLATILITY regime + conf ≥ this → emergency
_EMERGENCY_VOLATILE_CONF    = 0.40   # VOLATILE stability + conf < this → emergency

# ─── Regime factor tilt deltas ────────────────────────────────────────────────
# Applied on top of persona factor weights when a regime bias is active.

_REGIME_FACTOR_TILTS: dict[str, dict[str, float]] = {
    "quality_bias": {
        "quality": +0.15, "momentum": -0.05, "growth": -0.05, "value": -0.025, "dividend": -0.025,
    },
    "dividend_bias": {
        "dividend": +0.15, "momentum": -0.08, "growth": -0.07,
    },
    "momentum_bias": {
        "momentum": +0.15, "quality": -0.05, "value": -0.05, "dividend": -0.025, "growth": -0.025,
    },
    "suppress_speculative": {
        "quality": +0.10, "dividend": +0.05, "momentum": -0.10, "growth": -0.05,
    },
}

_FACTORS = ("growth", "value", "momentum", "quality", "dividend")


# ─── Dataclasses ──────────────────────────────────────────────────────────────

@dataclass
class HardConstraints:
    min_cash_pct: float            # minimum % of portfolio held undeployed
    max_single_position_pct: float # max single-stock weight
    max_sector_pct: float          # max sector concentration (from portfolio settings)
    max_turnover_pct: float        # max portfolio turnover as % of NAV per rebalance
    suppress_speculative: bool     # block low-quality / high-beta allocations
    beta_ceiling: float | None     # max implied portfolio beta (None = unconstrained)
    max_new_positions: int         # max new stocks added in one rebalance


@dataclass
class PolicyEnvelope:
    hard_constraints: HardConstraints
    soft_factor_tilts: dict[str, float]   # blended persona × regime factor weights (≈ sum 1.0)
    deployment_bias: str                   # AGGRESSIVE | SELECTIVE | DEFENSIVE | PRESERVATION
    risk_budget: float                     # 0-100 composite risk allowance
    rebalance_aggressiveness: float        # 0-1 composite drive to rebalance
    strictness_level: str                  # RELAXED | NORMAL | STRICT | EMERGENCY
    emergency_override: bool               # True when extreme market stress detected
    emergency_reason: str | None           # plain-English explanation when emergency
    policy_narrative: str                  # one-sentence human-readable summary
    confidence_discount: float             # 0-1: how much constraints were tightened for uncertainty
    violations: list[str]                  # existing policy violations in current portfolio


# ─── Emergency detection ──────────────────────────────────────────────────────

def _detect_emergency(
    regime: str,
    regime_confidence: float,
    vol_z: float,
    drawdown_score: float,
    stability: str,
) -> tuple[bool, str | None]:
    """Return (is_emergency, reason).  Checked top-to-bottom; first match wins."""
    if vol_z >= _EMERGENCY_VOL_Z:
        return True, (
            f"Extreme volatility (vol z-score {vol_z:.1f}σ ≥ {_EMERGENCY_VOL_Z}σ) — "
            "capital preservation mode activated"
        )
    if drawdown_score <= _EMERGENCY_DRAWDOWN:
        return True, (
            f"Severe drawdown across benchmarks (score {drawdown_score:.0f}/100 ≤ "
            f"{_EMERGENCY_DRAWDOWN:.0f} threshold)"
        )
    if regime == "HIGH_VOLATILITY" and regime_confidence >= _EMERGENCY_HIGH_VOL_CONF:
        return True, (
            f"HIGH_VOLATILITY regime confirmed at {regime_confidence:.0%} confidence — "
            "preservation mode enforced"
        )
    if stability == "VOLATILE" and regime_confidence < _EMERGENCY_VOLATILE_CONF:
        return True, (
            f"Regime is VOLATILE with low confidence ({regime_confidence:.0%}) — "
            "unstable transition, aggressive deployment frozen"
        )
    return False, None


# ─── Portfolio risk scoring ───────────────────────────────────────────────────

def _compute_portfolio_risk(portfolio_data: list[dict]) -> tuple[float, float]:
    """Return (portfolio_risk_score, concentration_score), both 0-100."""
    if not portfolio_data:
        return 50.0, 0.0
    total_mv = sum(d.get("market_value") or 0 for d in portfolio_data)
    if total_mv <= 0:
        return 50.0, 0.0

    weights = [(d.get("market_value") or 0) / total_mv for d in portfolio_data]

    # Herfindahl-Hirschman Index → concentration score
    n = len(portfolio_data)
    hhi = sum(w ** 2 for w in weights)
    min_hhi = 1.0 / n if n > 0 else 1.0
    conc = min(100.0, max(0.0, (hhi - min_hhi) / max(1e-6, 1.0 - min_hhi) * 100))

    # Signal-weighted risk: SELL/REDUCE = risky, BUY/ACCUMULATE = less risky
    _SIG_RISK = {
        "SELL": 90, "REDUCE": 70, "HOLD": 45, "WATCH": 38, "ACCUMULATE": 22, "BUY": 15,
    }
    sig_risk = sum(
        _SIG_RISK.get((d.get("signal") or "HOLD").upper(), 45) * w
        for d, w in zip(portfolio_data, weights)
    )

    risk = round(min(100.0, conc * 0.50 + sig_risk * 0.50), 1)
    return risk, round(conc, 1)


# ─── Confidence discount ──────────────────────────────────────────────────────

def _confidence_discount(
    regime_confidence: float,
    stability: str,
    consensus_strength: float,
) -> float:
    """0-1 discount that tightens constraints under uncertainty.

    Higher discount = more uncertain = tighter limits applied downstream.
    """
    # Low regime confidence is the dominant driver (0.70 = "full confidence" baseline)
    regime_disc = max(0.0, (0.70 - regime_confidence) / 0.70)
    # Regime stability adds a flat penalty
    stab_disc = {"STABLE": 0.0, "TRANSITIONING": 0.12, "VOLATILE": 0.30}.get(stability, 0.12)
    # Weak consensus is a small additional modifier
    cons_disc = max(0.0, (50.0 - consensus_strength) / 50.0) * 0.12
    return round(min(1.0, regime_disc * 0.50 + stab_disc * 0.35 + cons_disc * 0.15), 3)


# ─── Factor tilt blending ─────────────────────────────────────────────────────

def _blend_factor_tilts(
    persona_weights: dict[str, float],
    regime_biases: dict[str, bool],
    emergency_override: bool,
) -> dict[str, float]:
    """Blend persona factor weights with regime biases into unified soft tilts.

    Returns values summing to approximately 1.0, each clamped ≥ 0.02.
    """
    blended: dict[str, float] = {f: float(persona_weights.get(f, 0.20)) for f in _FACTORS}

    if emergency_override:
        # Emergency: heavy tilt toward capital-preservation factors
        blended["quality"]  = min(0.60, blended["quality"]  + 0.20)
        blended["dividend"] = min(0.50, blended["dividend"] + 0.15)
        blended["value"]    = min(0.45, blended["value"]    + 0.05)
        blended["growth"]   = max(0.02, blended["growth"]   - 0.20)
        blended["momentum"] = max(0.02, blended["momentum"] - 0.20)
    else:
        for bias_key, tilt_map in _REGIME_FACTOR_TILTS.items():
            if regime_biases.get(bias_key, False):
                for f, delta in tilt_map.items():
                    blended[f] = blended.get(f, 0.20) + delta

    # Clamp and renormalize
    clamped = {f: max(0.02, blended.get(f, 0.20)) for f in _FACTORS}
    total = sum(clamped.values())
    return {f: round(v / total, 3) for f, v in clamped.items()}


# ─── Deployment bias ──────────────────────────────────────────────────────────

def _deployment_bias(
    deployment_stance: str,
    emergency_override: bool,
    disc: float,
    persona_aggressiveness: float,
) -> str:
    if emergency_override:
        return DEPLOY_PRESERVATION

    # Discount reduces effective aggressiveness
    eff_aggr = persona_aggressiveness * (1 - disc * 0.50)

    _STANCE_MAP = {
        "aggressive":           DEPLOY_AGGRESSIVE,
        "cautiously_bullish":   DEPLOY_SELECTIVE,
        "selective":            DEPLOY_SELECTIVE,
        "defensive":            DEPLOY_DEFENSIVE,
        "cautiously_defensive": DEPLOY_DEFENSIVE,
        "preservation":         DEPLOY_PRESERVATION,
    }
    bias = _STANCE_MAP.get(deployment_stance, DEPLOY_SELECTIVE)

    # Downgrade if persona is too conservative for the stance
    if bias == DEPLOY_AGGRESSIVE and eff_aggr < 0.50:
        bias = DEPLOY_SELECTIVE
    if bias == DEPLOY_SELECTIVE and eff_aggr < 0.22:
        bias = DEPLOY_DEFENSIVE

    return bias


# ─── Strictness ───────────────────────────────────────────────────────────────

def _strictness(
    emergency: bool,
    disc: float,
    risk: float,
    bias: str,
) -> str:
    if emergency:
        return STRICTNESS_EMERGENCY
    if bias == DEPLOY_PRESERVATION or disc > 0.55:
        return STRICTNESS_STRICT
    if bias == DEPLOY_DEFENSIVE or disc > 0.28 or risk > 68:
        return STRICTNESS_STRICT
    if bias == DEPLOY_SELECTIVE or disc > 0.12:
        return STRICTNESS_NORMAL
    return STRICTNESS_RELAXED


# ─── Risk budget ──────────────────────────────────────────────────────────────

def _risk_budget(portfolio_risk: float, disc: float, bias: str, emergency: bool) -> float:
    if emergency:
        return max(5.0, 22.0 - portfolio_risk * 0.25)
    _BIAS_BASE = {
        DEPLOY_AGGRESSIVE:   78.0,
        DEPLOY_SELECTIVE:    55.0,
        DEPLOY_DEFENSIVE:    32.0,
        DEPLOY_PRESERVATION: 12.0,
    }
    base = _BIAS_BASE.get(bias, 55.0)
    return max(5.0, min(95.0, base - portfolio_risk * 0.20 - disc * 22.0))


# ─── Violation detection ──────────────────────────────────────────────────────

def _detect_violations(portfolio_data: list[dict], hard: HardConstraints) -> list[str]:
    """Check current portfolio holdings for existing policy violations."""
    violations: list[str] = []
    for item in portfolio_data:
        w = item.get("weight_pct") or 0
        sym = item.get("symbol", "?")
        if w > hard.max_single_position_pct:
            violations.append(
                f"CONCENTRATION_BREACH: {sym} at {w:.1f}% exceeds "
                f"{hard.max_single_position_pct:.0f}% single-position policy limit"
            )
        if hard.suppress_speculative:
            fa = item.get("fa_score") or 0
            ta = item.get("ta_score") or 0
            sig = (item.get("signal") or "HOLD").upper()
            if fa < 35 and ta < 35 and sig not in ("SELL", "REDUCE") and w > 4:
                violations.append(
                    f"POLICY_VIOLATION: {sym} is low-quality (FA={fa}, TA={ta}) and should be "
                    "suppressed per current policy"
                )
        if (item.get("signal") or "HOLD").upper() == "SELL" and w > 0:
            violations.append(
                f"POLICY_VIOLATION: {sym} has a SELL signal but remains held at {w:.1f}%"
            )
    return violations


# ─── Narrative ────────────────────────────────────────────────────────────────

def _narrative(
    bias: str,
    strictness: str,
    hard: HardConstraints,
    tilts: dict[str, float],
    emergency: bool,
    emergency_reason: str | None,
    disc: float,
    persona_label: str,
    regime: str,
) -> str:
    if emergency:
        return (
            f"EMERGENCY POLICY — {emergency_reason}. "
            f"Min cash {hard.min_cash_pct:.0f}%, max position {hard.max_single_position_pct:.0f}%, "
            "speculative assets suppressed."
        )
    dominant = max(tilts, key=lambda f: tilts[f])
    disc_note = (
        f" Constraints tightened {disc:.0%} for regime uncertainty."
        if disc > 0.30 else ""
    )
    return (
        f"{persona_label} persona under {regime} → {bias} deployment. "
        f"Cash ≥{hard.min_cash_pct:.0f}%, position cap {hard.max_single_position_pct:.0f}%, "
        f"dominant tilt {dominant.upper()} ({tilts[dominant]:.0%}). "
        f"Strictness: {strictness}.{disc_note}"
    )


# ─── Public API ───────────────────────────────────────────────────────────────

def compute_policy(
    persona_ctx: dict | None,
    regime_ctx: dict | None,
    portfolio_data: list[dict],
    consensus: dict | None = None,
    max_sector_pct: int = 40,
) -> PolicyEnvelope:
    """Build a PolicyEnvelope from persona + regime + portfolio risk + confidence state.

    This is the single authoritative source of truth for optimizer constraints.
    All hard limits come from here — not from AI output.

    Args:
        persona_ctx    : from build_persona_context()
        regime_ctx     : from detect_regime()
        portfolio_data : current holdings enriched with weight_pct, signal, fa_score, ta_score
        consensus      : optional output of _consensus_engine() — used for confidence modulation
        max_sector_pct : portfolio setting for sector concentration cap
    """
    # ── 1. Persona parameters ─────────────────────────────────────────────────
    pc = persona_ctx or {}
    persona_label   = pc.get("persona_label", "Balanced")
    persona_weights = pc.get("factor_weights", {f: 0.20 for f in _FACTORS})
    persona_cash_pct     = float(pc.get("max_cash_preference", 0.05)) * 100  # fraction → pct
    persona_aggr         = float(pc.get("rebalance_aggressiveness", 0.50))
    persona_turnover     = float(pc.get("turnover_tolerance", 0.40))
    persona_vol_tol      = float(pc.get("volatility_tolerance", 0.50))
    # Persona max-position: 20% base, ±10% scaled by volatility tolerance
    persona_max_pos = 20.0 + persona_vol_tol * 10.0  # 20–30% range

    # ── 2. Regime parameters ──────────────────────────────────────────────────
    rc = regime_ctx or {}
    regime            = rc.get("regime", "SIDEWAYS")
    regime_conf       = float(rc.get("confidence", 0.50))
    stability         = rc.get("transition_stability", "STABLE")
    vol_z             = float(rc.get("vol_z_score", 0.0))
    drawdown_score_val = float(rc.get("drawdown_score", 50.0))

    rcon = rc.get("constraints", {})
    regime_min_cash  = float(rcon.get("min_cash_pct", 5.0))
    regime_max_pos   = float(rcon.get("max_single_position_pct", 22.0))
    regime_turn_mult = float(rcon.get("turnover_multiplier", 1.0))
    suppress_spec    = bool(rcon.get("suppress_speculative", False))
    stance           = str(rcon.get("deployment_stance", "selective"))

    regime_biases = {
        "quality_bias":        bool(rcon.get("quality_bias", False)),
        "dividend_bias":       bool(rcon.get("dividend_bias", False)),
        "momentum_bias":       bool(rcon.get("momentum_bias", False)),
        "suppress_speculative": suppress_spec,
    }

    # ── 3. Consensus confidence ───────────────────────────────────────────────
    cons_strength = float((consensus or {}).get("consensus_strength_score", 50))

    # ── 4. Emergency detection ────────────────────────────────────────────────
    emergency, emergency_reason = _detect_emergency(
        regime, regime_conf, vol_z, drawdown_score_val, stability
    )

    # ── 5. Confidence discount ────────────────────────────────────────────────
    disc = _confidence_discount(regime_conf, stability, cons_strength)

    # ── 6. Hard constraints ───────────────────────────────────────────────────
    cash_boost  = disc * 8.0                          # up to +8% for uncertainty
    min_cash    = max(persona_cash_pct, regime_min_cash) + cash_boost
    if emergency:
        min_cash = max(min_cash, 20.0)

    max_pos = min(persona_max_pos, regime_max_pos)
    if disc > 0.38:
        max_pos = max_pos * 0.85                      # tighten by 15% when uncertain
    if emergency:
        max_pos = min(max_pos, 15.0)

    # Turnover ceiling: persona tolerance × regime multiplier × confidence adjustment
    turn_ceil = persona_turnover * 100 * regime_turn_mult * (1 - disc * 0.40)
    if emergency:
        turn_ceil = min(turn_ceil, 15.0)

    if emergency:
        max_new = 0
    elif stance in ("aggressive", "cautiously_bullish"):
        max_new = 3
    else:
        max_new = max(0, min(3, int(persona_aggr * 4)))

    hard = HardConstraints(
        min_cash_pct              = round(min(35.0, max(2.0, min_cash)), 1),
        max_single_position_pct   = round(max(8.0, max_pos), 1),
        max_sector_pct            = float(max_sector_pct),
        max_turnover_pct          = round(max(5.0, min(100.0, turn_ceil)), 1),
        suppress_speculative      = suppress_spec or emergency,
        beta_ceiling              = None,
        max_new_positions         = max_new,
    )

    # ── 7. Soft factor tilts ──────────────────────────────────────────────────
    tilts = _blend_factor_tilts(persona_weights, regime_biases, emergency)

    # ── 8. Deployment bias ────────────────────────────────────────────────────
    bias = _deployment_bias(stance, emergency, disc, persona_aggr)

    # ── 9. Portfolio risk ─────────────────────────────────────────────────────
    portfolio_risk, _ = _compute_portfolio_risk(portfolio_data)

    # ── 10. Derived outputs ───────────────────────────────────────────────────
    strictness = _strictness(emergency, disc, portfolio_risk, bias)
    budget     = _risk_budget(portfolio_risk, disc, bias, emergency)
    rebal_aggr = min(1.0, max(0.0, persona_aggr * regime_turn_mult * (1 - disc * 0.45)))
    if emergency:
        rebal_aggr = min(rebal_aggr, 0.12)

    violations = _detect_violations(portfolio_data, hard)
    narrative  = _narrative(bias, strictness, hard, tilts, emergency, emergency_reason,
                            disc, persona_label, regime)

    log.info(
        "policy_engine: persona=%s regime=%s bias=%s strict=%s "
        "cash=%.1f%% max_pos=%.1f%% budget=%.0f emergency=%s violations=%d",
        persona_label, regime, bias, strictness,
        hard.min_cash_pct, hard.max_single_position_pct,
        budget, emergency, len(violations),
    )

    return PolicyEnvelope(
        hard_constraints       = hard,
        soft_factor_tilts      = tilts,
        deployment_bias        = bias,
        risk_budget            = round(budget, 1),
        rebalance_aggressiveness = round(rebal_aggr, 3),
        strictness_level       = strictness,
        emergency_override     = emergency,
        emergency_reason       = emergency_reason,
        policy_narrative       = narrative,
        confidence_discount    = disc,
        violations             = violations,
    )


# ─── Prompt block builder ─────────────────────────────────────────────────────

def build_policy_prompt_block(envelope: PolicyEnvelope) -> str:
    """Generate [ACTIVE OPTIMIZATION POLICY] block injected into L1/L2/L3 prompts."""
    hard = envelope.hard_constraints

    top_tilts = sorted(envelope.soft_factor_tilts.items(), key=lambda x: -x[1])[:3]
    tilt_str  = " > ".join(f"{f.upper()} ({v:.0%})" for f, v in top_tilts)

    emergency_block = ""
    if envelope.emergency_override:
        emergency_block = (
            f"\n⚠ EMERGENCY OVERRIDE ACTIVE — {envelope.emergency_reason}\n"
            "ALL new aggressive allocations are FROZEN. Capital preservation is the ONLY objective.\n"
        )

    violation_block = ""
    if envelope.violations:
        violation_block = "\nExisting violations to resolve:\n" + "\n".join(
            f"  • {v}" for v in envelope.violations[:5]
        )

    suppress_note = "YES — avoid low-quality or high-beta positions" if hard.suppress_speculative else "NO"

    return f"""[ACTIVE OPTIMIZATION POLICY — MANDATORY GOVERNANCE]{emergency_block}
DEPLOYMENT_MODE:        {envelope.deployment_bias}
STRICTNESS_LEVEL:       {envelope.strictness_level}
RISK_BUDGET:            {envelope.risk_budget:.0f}/100

CURRENT_CASH_MANDATE:   minimum {hard.min_cash_pct:.0f}% must remain undeployed
MAX_SINGLE_STOCK_LIMIT: {hard.max_single_position_pct:.0f}% of portfolio per stock
MAX_SECTOR_LIMIT:       {hard.max_sector_pct:.0f}% per sector
TURNOVER_CEILING:       {hard.max_turnover_pct:.0f}% of portfolio value this rebalance
MAX_NEW_POSITIONS:      {hard.max_new_positions} new stock(s) maximum
SUPPRESS_SPECULATIVE:   {suppress_note}

ACTIVE_FACTOR_TILT:     {tilt_str}
{violation_block}
Policy summary: {envelope.policy_narrative}

All allocation proposals MUST comply with these constraints.
Hard limits are enforced deterministically in Python after AI output — violating proposals will be corrected automatically.
"""


# ─── Policy alignment scoring ─────────────────────────────────────────────────

def compute_policy_alignment_score(
    final_allocations: list[dict],
    envelope: PolicyEnvelope,
    total_value: float,
) -> tuple[float, float, float, list[str]]:
    """Score how well the final allocation plan complies with the policy envelope.

    Returns:
        policy_alignment_score  : 0-100 (constraint compliance)
        regime_compliance_score : 0-100 (regime/bias alignment)
        risk_governance_score   : 0-100 (composite)
        governance_flags        : list of flag strings (POLICY_VIOLATION etc.)
    """
    flags: list[str] = []
    hard = envelope.hard_constraints

    # Cash compliance
    total_deployed = sum(
        a.get("target_weight", 0) for a in final_allocations
        if a.get("action") not in ("SELL",)
    )
    implied_cash = max(0.0, 100.0 - total_deployed)
    cash_ok = implied_cash >= hard.min_cash_pct
    if not cash_ok:
        flags.append(
            f"POLICY_VIOLATION: implied cash {implied_cash:.1f}% < required {hard.min_cash_pct:.1f}%"
        )
    cash_score = min(100.0, implied_cash / max(hard.min_cash_pct, 0.1) * 100) if hard.min_cash_pct > 0 else 100.0

    # Position concentration
    conc_violations = 0
    for a in final_allocations:
        tw = float(a.get("target_weight") or 0)
        if tw > hard.max_single_position_pct and a.get("action") not in ("SELL",):
            conc_violations += 1
            flags.append(
                f"CONCENTRATION_BREACH: {a.get('symbol','?')} target {tw:.1f}% > "
                f"{hard.max_single_position_pct:.0f}% limit"
            )
    conc_score = max(0.0, 100.0 - conc_violations * 25)

    # Over-aggression in defensive modes
    buy_count = sum(1 for a in final_allocations if a.get("action") in ("BUY", "ACCUMULATE"))
    if envelope.deployment_bias in (DEPLOY_DEFENSIVE, DEPLOY_PRESERVATION) and buy_count > 1:
        flags.append(
            f"OVER_AGGRESSION: {buy_count} BUY/ACCUMULATE allocation(s) in "
            f"{envelope.deployment_bias} mode"
        )
    aggr_score = 100.0 if envelope.deployment_bias not in (DEPLOY_DEFENSIVE, DEPLOY_PRESERVATION) \
        else max(0.0, 100.0 - buy_count * 15)

    # Emergency compliance
    if envelope.emergency_override and buy_count > 0:
        flags.append(
            f"REGIME_MISMATCH: {buy_count} new allocation(s) proposed during EMERGENCY override"
        )
    regime_mismatch_ok = not (envelope.emergency_override and buy_count > 0)
    regime_mismatch_score = 0.0 if not regime_mismatch_ok else 100.0

    # Turnover compliance
    total_change = sum(abs(a.get("allocation_change_percent") or 0) for a in final_allocations)
    if total_change > hard.max_turnover_pct:
        flags.append(
            f"POLICY_VIOLATION: total turnover {total_change:.1f}% exceeds ceiling {hard.max_turnover_pct:.0f}%"
        )

    # Aggregate scores
    policy_alignment   = cash_score * 0.40 + conc_score * 0.35 + aggr_score * 0.25
    regime_compliance  = regime_mismatch_score * 0.60 + conc_score * 0.40
    risk_governance    = policy_alignment * 0.60 + regime_compliance * 0.40

    return (
        round(min(100.0, policy_alignment), 1),
        round(min(100.0, regime_compliance), 1),
        round(min(100.0, risk_governance), 1),
        flags,
    )


# ─── Serialization ───────────────────────────────────────────────────────────

def envelope_to_dict(env: PolicyEnvelope) -> dict:
    """Convert PolicyEnvelope to a JSON-serializable dict (includes pre-built prompt_block)."""
    h = env.hard_constraints
    return {
        "hard_constraints": {
            "min_cash_pct":            h.min_cash_pct,
            "max_single_position_pct": h.max_single_position_pct,
            "max_sector_pct":          h.max_sector_pct,
            "max_turnover_pct":        h.max_turnover_pct,
            "suppress_speculative":    h.suppress_speculative,
            "beta_ceiling":            h.beta_ceiling,
            "max_new_positions":       h.max_new_positions,
        },
        "soft_factor_tilts":       env.soft_factor_tilts,
        "deployment_bias":         env.deployment_bias,
        "risk_budget":             env.risk_budget,
        "rebalance_aggressiveness": env.rebalance_aggressiveness,
        "strictness_level":        env.strictness_level,
        "emergency_override":      env.emergency_override,
        "emergency_reason":        env.emergency_reason,
        "policy_narrative":        env.policy_narrative,
        "confidence_discount":     env.confidence_discount,
        "violations":              env.violations,
        "prompt_block":            build_policy_prompt_block(env),
    }
