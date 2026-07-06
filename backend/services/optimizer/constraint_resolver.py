"""Constraint Resolution Layer — Phase 3B.5.

Merges constraints from four authoritative sources into a single EffectiveEnvelope:
  A. User Portfolio Preferences  (max_sector_pct, per-sector limits, persona-derived caps)
  B. Dynamic Regime Policy       (min_cash_pct, max_single_position_pct, sector multipliers)
  C. Emergency Risk Overrides    (crisis thresholds — activated by extreme market signals)
  D. Absolute System Safety      (hard ceilings that can never be exceeded by any config)

Resolution rule for upper-bound constraints (position cap, sector cap, turnover):
    effective = min(user_pref, regime_policy, emergency_limit, system_safety)

Resolution rule for lower-bound constraints (cash floor):
    effective = max(user_pref, regime_policy, emergency_limit, system_safety)

See OPTIMIZER_PHILOSOPHY.md §2 — constraints are enforced deterministically
and never negotiate with a belief, however confident.

The resolved EffectiveEnvelope is the ONLY policy object injected into:
  - L1/L2/L3 AI prompt governance blocks
  - Post-AI constraint enforcement in run_layered_optimizer
  - Compliance scoring in compute_policy_alignment_score
  - Frontend transparency display (constraint comparison table)

Public API:
    resolve_constraints(user_portfolio_settings, user_sector_limits, regime_ctx, persona_ctx)
        → EffectiveEnvelope

    effective_sector_cap(envelope, sector) → float
    envelope_to_dict(envelope) → dict
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

log = logging.getLogger(__name__)

# ─── Absolute system safety ceilings ─────────────────────────────────────────
# Final backstop limits — only activate when every other source is too permissive.
# These represent absolute hard boundaries, not business logic.

ABSOLUTE_SYSTEM_MAX_SECTOR           = 70.0    # no sector may exceed 70% portfolio weight
ABSOLUTE_SYSTEM_MAX_SINGLE_POSITION  = 40.0    # no single stock may exceed 40%
ABSOLUTE_SYSTEM_MAX_TURNOVER         = 100.0   # turnover cap ceiling (100% = full portfolio)
ABSOLUTE_SYSTEM_MIN_CASH             = 0.0     # cash floor cannot go below 0%
ABSOLUTE_SYSTEM_MAX_BETA             = 1.8     # reserved for future beta-weighted enforcement

# ─── Emergency override thresholds ───────────────────────────────────────────
# Applied only when extreme market stress is confirmed via regime signals.

EMERGENCY_MAX_SECTOR          = 25.0    # tightest sector cap in a crisis
EMERGENCY_MAX_SINGLE_POSITION = 15.0    # tightest position cap in a crisis
EMERGENCY_MIN_CASH            = 20.0    # minimum cash floor during crisis
EMERGENCY_MAX_TURNOVER        = 15.0    # minimal churn allowed during crisis

# ─── Regime-based sector tightening multipliers ───────────────────────────────
# Applied multiplicatively to user-defined per-sector limits.
# multiplier < 1.0 = regime tightens user preferences.

_REGIME_SECTOR_MULTIPLIERS: dict[str, float] = {
    "RISK_ON":              1.00,   # full user limits preserved (risk-on = permissive)
    "RISK_OFF":             0.85,   # tighten all sectors 15%
    "SIDEWAYS":             0.95,   # mild 5% tightening
    "HIGH_VOLATILITY":      0.70,   # strong 30% tightening across all sectors
    "DEFENSIVE_REGIME":     0.85,   # tighten 15%
    "TRANSITION_RISK_ON":   0.90,   # cautious, +10% tightening
    "TRANSITION_RISK_OFF":  0.85,   # tightening as transition deteriorates
}

# Canonical sectors that receive individual resolution breakdowns
_KNOWN_SECTORS = (
    "Technology", "Financial", "Energy", "Healthcare",
    "Consumer", "Industrial", "Real Estate", "Utilities", "Other",
)

# ─── Constraint source labels ─────────────────────────────────────────────────

SOURCE_USER      = "USER_PREFERENCE"
SOURCE_REGIME    = "REGIME_POLICY"
SOURCE_EMERGENCY = "EMERGENCY_OVERRIDE"
SOURCE_SYSTEM    = "SYSTEM_SAFETY"

# ─── Emergency signal thresholds (mirrors policy_engine to stay in sync) ─────

_EMERGENCY_VOL_Z         = 2.5
_EMERGENCY_DRAWDOWN      = 15.0
_EMERGENCY_HIGH_VOL_CONF = 0.65
_EMERGENCY_VOLATILE_CONF = 0.40


# ─── Dataclasses ──────────────────────────────────────────────────────────────

@dataclass
class ConstraintBreakdown:
    """Full audit trail for how a single constraint was resolved."""
    user_pref:        float         # raw user-configured value
    regime_policy:    float         # what the active regime mandates
    emergency_limit:  float | None  # crisis override limit (None when not active)
    system_safety:    float         # absolute system ceiling / floor
    effective:        float         # final resolved value
    binding_source:   str           # which source produced the effective value
    tightened_reason: str | None    # human-readable note when a non-user source binds


@dataclass
class EffectiveEnvelope:
    """Fully resolved constraint set — the single authoritative governance layer.

    All downstream optimizer components (prompts, enforcement, scoring, UI) must
    read constraints from this object and this object only.
    """
    # Scalar constraints with full audit trails
    single_position:  ConstraintBreakdown    # upper bound — max single-stock weight
    cash_min:         ConstraintBreakdown    # lower bound — minimum undeployed cash
    turnover_max:     ConstraintBreakdown    # upper bound — max portfolio churn per run
    beta_ceiling:     float | None           # reserved for future beta enforcement

    # Per-sector resolved limits (each sector tracked individually)
    sector_limits:    dict[str, ConstraintBreakdown]  # sector → breakdown
    global_sector_cap: ConstraintBreakdown            # fallback for unlisted sectors

    # Flat values for easy downstream consumption (no unpacking needed)
    effective_single_position_pct: float
    effective_cash_min_pct:        float
    effective_turnover_max_pct:    float
    effective_sector_limits:       dict[str, float]   # sector → effective %

    # Context
    emergency_active: bool
    regime_name:      str
    resolver_notes:   list[str]    # human-readable constraint adjustment notes


# ─── Resolution primitives ────────────────────────────────────────────────────

def _resolve_upper(
    user_pref: float,
    regime_value: float,
    emergency_limit: float,
    system_safety: float,
    emergency_active: bool,
    regime_name: str,
) -> ConstraintBreakdown:
    """Resolve an upper-bound constraint (smaller value = tighter restriction).

    Used for: position cap, sector cap, turnover ceiling.
    """
    candidates: dict[str, float] = {
        SOURCE_USER:   user_pref,
        SOURCE_REGIME: regime_value,
        SOURCE_SYSTEM: system_safety,
    }
    if emergency_active:
        candidates[SOURCE_EMERGENCY] = emergency_limit

    binding  = min(candidates, key=lambda k: candidates[k])
    effective = candidates[binding]

    tightened: str | None = None
    if binding == SOURCE_REGIME and effective < user_pref:
        tightened = (
            f"Tightened {user_pref:.0f}% → {effective:.0f}% "
            f"by {regime_name} regime policy"
        )
    elif binding == SOURCE_EMERGENCY:
        tightened = f"Emergency override: capped at {effective:.0f}% (crisis protection)"
    elif binding == SOURCE_SYSTEM:
        tightened = f"Absolute system ceiling: capped at {effective:.0f}%"

    return ConstraintBreakdown(
        user_pref=round(user_pref, 1),
        regime_policy=round(regime_value, 1),
        emergency_limit=round(emergency_limit, 1) if emergency_active else None,
        system_safety=round(system_safety, 1),
        effective=round(effective, 1),
        binding_source=binding,
        tightened_reason=tightened,
    )


def _resolve_lower(
    user_pref: float,
    regime_value: float,
    emergency_limit: float,
    system_safety: float,
    emergency_active: bool,
    regime_name: str,
) -> ConstraintBreakdown:
    """Resolve a lower-bound constraint (larger value = tighter restriction).

    Used for: cash floor (larger required cash = more conservative).
    """
    candidates: dict[str, float] = {
        SOURCE_USER:   user_pref,
        SOURCE_REGIME: regime_value,
        SOURCE_SYSTEM: system_safety,
    }
    if emergency_active:
        candidates[SOURCE_EMERGENCY] = emergency_limit

    binding  = max(candidates, key=lambda k: candidates[k])
    effective = candidates[binding]

    tightened: str | None = None
    if binding == SOURCE_REGIME and effective > user_pref:
        tightened = (
            f"Raised {user_pref:.0f}% → {effective:.0f}% "
            f"by {regime_name} regime policy"
        )
    elif binding == SOURCE_EMERGENCY:
        tightened = f"Emergency override: floor raised to {effective:.0f}% (crisis protection)"
    elif binding == SOURCE_SYSTEM:
        tightened = f"Absolute system floor: minimum {effective:.0f}%"

    return ConstraintBreakdown(
        user_pref=round(user_pref, 1),
        regime_policy=round(regime_value, 1),
        emergency_limit=round(emergency_limit, 1) if emergency_active else None,
        system_safety=round(system_safety, 1),
        effective=round(effective, 1),
        binding_source=binding,
        tightened_reason=tightened,
    )


# ─── Emergency detection ──────────────────────────────────────────────────────

def _is_emergency(regime_ctx: dict) -> bool:
    """Detect crisis-level market conditions from regime context signals."""
    regime    = str(regime_ctx.get("regime", "SIDEWAYS"))
    conf      = float(regime_ctx.get("confidence", 0.50))
    vol_z     = float(regime_ctx.get("vol_z_score", 0.0))
    drawdown  = float(regime_ctx.get("drawdown_score", 50.0))
    stability = str(regime_ctx.get("transition_stability", "STABLE"))
    return (
        vol_z    >= _EMERGENCY_VOL_Z
        or drawdown   <= _EMERGENCY_DRAWDOWN
        or (regime == "HIGH_VOLATILITY" and conf >= _EMERGENCY_HIGH_VOL_CONF)
        or (stability == "VOLATILE"     and conf <  _EMERGENCY_VOLATILE_CONF)
    )


# ─── Public API ───────────────────────────────────────────────────────────────

def resolve_constraints(
    user_portfolio_settings: dict,
    user_sector_limits: dict,
    regime_ctx: dict | None,
    persona_ctx: dict | None,
) -> EffectiveEnvelope:
    """Resolve all optimizer constraints into a single deterministic EffectiveEnvelope.

    This is the authoritative pre-AI governance step. Every limit produced here
    is enforced deterministically — AI output cannot override these values.

    Args:
        user_portfolio_settings : {max_stocks: int, max_sector_pct: int}
        user_sector_limits      : per-sector % limits from Settings DB (may include "default" key)
        regime_ctx              : from detect_regime() — provides min_cash, max_position, sector mult
        persona_ctx             : from build_persona_context() — provides vol/turnover tolerance
    """
    notes: list[str] = []

    # ── A: User Portfolio Preferences ─────────────────────────────────────────
    user_max_sector_global = float(user_portfolio_settings.get("max_sector_pct", 40))
    pc                     = persona_ctx or {}
    vol_tol                = float(pc.get("volatility_tolerance", 0.50))
    # Persona position cap: 20% base ± 10% scaled by volatility tolerance (range: 20–30%)
    user_max_pos      = 20.0 + vol_tol * 10.0
    user_min_cash     = float(pc.get("max_cash_preference", 0.05)) * 100   # fraction → pct
    user_max_turnover = float(pc.get("turnover_tolerance", 0.40)) * 100    # fraction → pct

    # ── B: Dynamic Regime Policy ──────────────────────────────────────────────
    rc              = regime_ctx or {}
    regime_name     = str(rc.get("regime", "SIDEWAYS"))
    rcon            = rc.get("constraints", {})
    regime_min_cash = float(rcon.get("min_cash_pct", 5.0))
    regime_max_pos  = float(rcon.get("max_single_position_pct", 22.0))
    regime_turn_mult = float(rcon.get("turnover_multiplier", 1.0))
    regime_max_turn  = user_max_turnover * regime_turn_mult
    sector_mult      = _REGIME_SECTOR_MULTIPLIERS.get(regime_name, 1.0)

    # ── C: Emergency Override Detection ───────────────────────────────────────
    emergency = _is_emergency(rc) if rc else False

    # ── Scalar constraint resolution ──────────────────────────────────────────

    pos_bd = _resolve_upper(
        user_pref=user_max_pos,
        regime_value=regime_max_pos,
        emergency_limit=EMERGENCY_MAX_SINGLE_POSITION,
        system_safety=ABSOLUTE_SYSTEM_MAX_SINGLE_POSITION,
        emergency_active=emergency,
        regime_name=regime_name,
    )
    if pos_bd.tightened_reason:
        notes.append(f"Position cap: {pos_bd.tightened_reason}")

    cash_bd = _resolve_lower(
        user_pref=user_min_cash,
        regime_value=regime_min_cash,
        emergency_limit=EMERGENCY_MIN_CASH,
        system_safety=ABSOLUTE_SYSTEM_MIN_CASH,
        emergency_active=emergency,
        regime_name=regime_name,
    )
    if cash_bd.tightened_reason:
        notes.append(f"Cash floor: {cash_bd.tightened_reason}")

    turn_bd = _resolve_upper(
        user_pref=user_max_turnover,
        regime_value=regime_max_turn,
        emergency_limit=EMERGENCY_MAX_TURNOVER,
        system_safety=ABSOLUTE_SYSTEM_MAX_TURNOVER,
        emergency_active=emergency,
        regime_name=regime_name,
    )
    if turn_bd.tightened_reason:
        notes.append(f"Turnover cap: {turn_bd.tightened_reason}")

    # ── Per-sector limit resolution ───────────────────────────────────────────
    sector_breakdowns: dict[str, ConstraintBreakdown] = {}
    user_default_sector = float(user_sector_limits.get("default", user_max_sector_global))

    for sector in _KNOWN_SECTORS:
        user_limit   = float(user_sector_limits.get(sector, user_default_sector))
        regime_limit = round(user_limit * sector_mult, 1)

        bd = _resolve_upper(
            user_pref=user_limit,
            regime_value=regime_limit,
            emergency_limit=EMERGENCY_MAX_SECTOR,
            system_safety=ABSOLUTE_SYSTEM_MAX_SECTOR,
            emergency_active=emergency,
            regime_name=regime_name,
        )
        sector_breakdowns[sector] = bd
        if bd.tightened_reason:
            notes.append(f"{sector}: {bd.tightened_reason}")

    # Global fallback cap for sectors not in the known list
    global_regime_limit = round(user_max_sector_global * sector_mult, 1)
    global_bd = _resolve_upper(
        user_pref=user_max_sector_global,
        regime_value=global_regime_limit,
        emergency_limit=EMERGENCY_MAX_SECTOR,
        system_safety=ABSOLUTE_SYSTEM_MAX_SECTOR,
        emergency_active=emergency,
        regime_name=regime_name,
    )

    effective_sector_limits = {s: bd.effective for s, bd in sector_breakdowns.items()}

    if notes:
        log.info(
            "constraint_resolver: %d adjustment(s). regime=%s emergency=%s",
            len(notes), regime_name, emergency,
        )

    return EffectiveEnvelope(
        single_position=pos_bd,
        cash_min=cash_bd,
        turnover_max=turn_bd,
        beta_ceiling=ABSOLUTE_SYSTEM_MAX_BETA,
        sector_limits=sector_breakdowns,
        global_sector_cap=global_bd,
        effective_single_position_pct=pos_bd.effective,
        effective_cash_min_pct=cash_bd.effective,
        effective_turnover_max_pct=turn_bd.effective,
        effective_sector_limits=effective_sector_limits,
        emergency_active=emergency,
        regime_name=regime_name,
        resolver_notes=notes,
    )


def effective_sector_cap(envelope: EffectiveEnvelope, sector: str) -> float:
    """Return the resolved effective sector cap for a given sector name."""
    bd = envelope.sector_limits.get(sector)
    return bd.effective if bd is not None else envelope.global_sector_cap.effective


def _bd_to_dict(bd: ConstraintBreakdown) -> dict:
    return {
        "user_pref":        bd.user_pref,
        "regime_policy":    bd.regime_policy,
        "emergency_limit":  bd.emergency_limit,
        "system_safety":    bd.system_safety,
        "effective":        bd.effective,
        "binding_source":   bd.binding_source,
        "tightened_reason": bd.tightened_reason,
    }


def envelope_to_dict(envelope: EffectiveEnvelope) -> dict:
    """Convert EffectiveEnvelope to a JSON-serializable dict for API responses."""
    return {
        "single_position":   _bd_to_dict(envelope.single_position),
        "cash_min":          _bd_to_dict(envelope.cash_min),
        "turnover_max":      _bd_to_dict(envelope.turnover_max),
        "beta_ceiling":      envelope.beta_ceiling,
        "sector_limits":     {s: _bd_to_dict(bd) for s, bd in envelope.sector_limits.items()},
        "global_sector_cap": _bd_to_dict(envelope.global_sector_cap),
        "effective_single_position_pct": envelope.effective_single_position_pct,
        "effective_cash_min_pct":        envelope.effective_cash_min_pct,
        "effective_turnover_max_pct":    envelope.effective_turnover_max_pct,
        "effective_sector_limits":       envelope.effective_sector_limits,
        "emergency_active":  envelope.emergency_active,
        "regime_name":       envelope.regime_name,
        "resolver_notes":    envelope.resolver_notes,
    }
