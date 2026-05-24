"""verify_adaptive_optimizer.py — Phase 3B.4 Policy Engine Scenario Simulations.

Usage (from backend/):
    python scripts/verify_adaptive_optimizer.py [--scenario SCENARIO] [--verbose]

Scenarios:
    growth_risk_on        Growth persona + RISK_ON regime
    growth_risk_off       Growth persona + RISK_OFF regime
    dividend_high_vol     Dividend persona + HIGH_VOLATILITY regime (emergency)
    momentum_transition   Momentum persona + TRANSITION_RISK_OFF regime

All 4 scenarios run by default.

Verifies:
    - Correct deployment_bias for persona × regime combination
    - Hard constraints (cash floor, position cap, speculative suppression)
    - Emergency override detection
    - Factor tilt composition
    - Policy alignment scoring against mock allocations
    - Consensus governance scoring
"""
import sys
import os

# Allow running from the scripts/ directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import argparse
import json
from dataclasses import asdict

from services.optimizer.policy_engine import (
    compute_policy,
    build_policy_prompt_block,
    compute_policy_alignment_score,
    envelope_to_dict,
    DEPLOY_AGGRESSIVE,
    DEPLOY_SELECTIVE,
    DEPLOY_DEFENSIVE,
    DEPLOY_PRESERVATION,
    STRICTNESS_EMERGENCY,
    STRICTNESS_STRICT,
)

# ─── Mock data builders ───────────────────────────────────────────────────────

def _make_persona_ctx(persona_key: str) -> dict:
    """Return a minimal persona_ctx matching the real strategy profile shapes."""
    profiles = {
        "GROWTH": {
            "persona_label": "Growth",
            "factor_weights": {"growth": 0.40, "momentum": 0.30, "quality": 0.20, "value": 0.05, "dividend": 0.05},
            "max_cash_preference": 0.03,
            "rebalance_aggressiveness": 0.75,
            "turnover_tolerance": 0.70,
            "volatility_tolerance": 0.75,
        },
        "VALUE": {
            "persona_label": "Value Investing",
            "factor_weights": {"value": 0.40, "quality": 0.30, "growth": 0.15, "dividend": 0.10, "momentum": 0.05},
            "max_cash_preference": 0.10,
            "rebalance_aggressiveness": 0.25,
            "turnover_tolerance": 0.20,
            "volatility_tolerance": 0.35,
        },
        "DIVIDEND": {
            "persona_label": "Dividend Income",
            "factor_weights": {"dividend": 0.45, "quality": 0.30, "value": 0.15, "growth": 0.05, "momentum": 0.05},
            "max_cash_preference": 0.05,
            "rebalance_aggressiveness": 0.20,
            "turnover_tolerance": 0.15,
            "volatility_tolerance": 0.25,
        },
        "MOMENTUM": {
            "persona_label": "Momentum",
            "factor_weights": {"momentum": 0.50, "growth": 0.25, "quality": 0.15, "value": 0.05, "dividend": 0.05},
            "max_cash_preference": 0.02,
            "rebalance_aggressiveness": 0.90,
            "turnover_tolerance": 0.90,
            "volatility_tolerance": 0.85,
        },
    }
    return profiles.get(persona_key, profiles["GROWTH"])


def _make_regime_ctx(
    regime: str,
    confidence: float = 0.75,
    stability: str = "STABLE",
    vol_z: float = 0.5,
    drawdown_score: float = 70.0,
) -> dict:
    """Return a minimal regime_ctx matching the real detect_regime() output shape."""
    constraints_map = {
        "RISK_ON": {
            "min_cash_pct": 2.0, "max_single_position_pct": 25.0, "turnover_multiplier": 1.2,
            "momentum_bias": True, "quality_bias": False, "dividend_bias": False,
            "suppress_speculative": False, "deployment_stance": "aggressive",
        },
        "RISK_OFF": {
            "min_cash_pct": 10.0, "max_single_position_pct": 20.0, "turnover_multiplier": 0.7,
            "momentum_bias": False, "quality_bias": True, "dividend_bias": True,
            "suppress_speculative": True, "deployment_stance": "defensive",
        },
        "HIGH_VOLATILITY": {
            "min_cash_pct": 15.0, "max_single_position_pct": 18.0, "turnover_multiplier": 0.5,
            "momentum_bias": False, "quality_bias": True, "dividend_bias": False,
            "suppress_speculative": True, "deployment_stance": "preservation",
        },
        "TRANSITION_RISK_OFF": {
            "min_cash_pct": 8.0, "max_single_position_pct": 20.0, "turnover_multiplier": 0.8,
            "momentum_bias": False, "quality_bias": True, "dividend_bias": True,
            "suppress_speculative": True, "deployment_stance": "cautiously_defensive",
        },
        "SIDEWAYS": {
            "min_cash_pct": 5.0, "max_single_position_pct": 22.0, "turnover_multiplier": 0.8,
            "momentum_bias": False, "quality_bias": False, "dividend_bias": True,
            "suppress_speculative": False, "deployment_stance": "selective",
        },
    }
    return {
        "regime": regime,
        "confidence": confidence,
        "confidence_pct": confidence * 100,
        "transition_stability": stability,
        "vol_z_score": vol_z,
        "drawdown_score": drawdown_score,
        "trend_score": 65.0,
        "volatility_score": 60.0,
        "momentum_score": 55.0,
        "constraints": constraints_map.get(regime, constraints_map["SIDEWAYS"]),
    }


def _make_portfolio(
    n: int = 6,
    max_weight: float = 18.0,
    include_low_quality: bool = False,
) -> list[dict]:
    """Generate a simple mock portfolio."""
    entries = [
        {"symbol": "AAPL", "signal": "HOLD",       "fa_score": 72, "ta_score": 65, "weight_pct": max_weight,         "market_value": 1800_000},
        {"symbol": "MSFT", "signal": "BUY",         "fa_score": 80, "ta_score": 75, "weight_pct": max_weight - 2,     "market_value": 1600_000},
        {"symbol": "GOOGL","signal": "ACCUMULATE",  "fa_score": 68, "ta_score": 60, "weight_pct": max_weight - 4,     "market_value": 1400_000},
        {"symbol": "NVDA", "signal": "WATCH",       "fa_score": 60, "ta_score": 55, "weight_pct": max_weight - 6,     "market_value": 1200_000},
        {"symbol": "META", "signal": "HOLD",        "fa_score": 65, "ta_score": 50, "weight_pct": max_weight - 8,     "market_value": 1000_000},
        {"symbol": "AMZN", "signal": "HOLD",        "fa_score": 70, "ta_score": 58, "weight_pct": max_weight - 10,    "market_value": 800_000},
    ]
    result = entries[:n]
    # Always append SPEC1 at the end (outside the n-slice) so it's always present
    if include_low_quality:
        result.append({
            "symbol": "SPEC1", "signal": "WATCH", "fa_score": 28, "ta_score": 30,
            "weight_pct": 8.0, "market_value": 800_000,
        })
    return result


def _mock_allocations(bias: str) -> list[dict]:
    """Generate mock final_allocations that match a deployment bias."""
    if bias in (DEPLOY_AGGRESSIVE,):
        return [
            {"symbol": "AAPL",  "action": "BUY",       "target_weight": 20.0, "current_weight": 15.0, "allocation_change_percent": 5.0},
            {"symbol": "MSFT",  "action": "BUY",        "target_weight": 18.0, "current_weight": 14.0, "allocation_change_percent": 4.0},
            {"symbol": "GOOGL", "action": "ACCUMULATE", "target_weight": 15.0, "current_weight": 12.0, "allocation_change_percent": 3.0},
            {"symbol": "NVDA",  "action": "HOLD",       "target_weight": 12.0, "current_weight": 12.0, "allocation_change_percent": 0.0},
            {"symbol": "META",  "action": "HOLD",       "target_weight": 10.0, "current_weight": 10.0, "allocation_change_percent": 0.0},
        ]
    elif bias in (DEPLOY_DEFENSIVE, DEPLOY_PRESERVATION):
        return [
            {"symbol": "AAPL",  "action": "HOLD",   "target_weight": 15.0, "current_weight": 15.0, "allocation_change_percent": 0.0},
            {"symbol": "MSFT",  "action": "REDUCE",  "target_weight": 10.0, "current_weight": 14.0, "allocation_change_percent": -4.0},
            {"symbol": "GOOGL", "action": "REDUCE",  "target_weight": 8.0,  "current_weight": 12.0, "allocation_change_percent": -4.0},
            {"symbol": "NVDA",  "action": "SELL",    "target_weight": 0.0,  "current_weight": 12.0, "allocation_change_percent": -12.0},
            {"symbol": "META",  "action": "HOLD",    "target_weight": 10.0, "current_weight": 10.0, "allocation_change_percent": 0.0},
        ]
    else:  # SELECTIVE
        return [
            {"symbol": "AAPL",  "action": "ACCUMULATE","target_weight": 16.0, "current_weight": 15.0, "allocation_change_percent": 1.0},
            {"symbol": "MSFT",  "action": "HOLD",       "target_weight": 14.0, "current_weight": 14.0, "allocation_change_percent": 0.0},
            {"symbol": "GOOGL", "action": "HOLD",       "target_weight": 12.0, "current_weight": 12.0, "allocation_change_percent": 0.0},
            {"symbol": "NVDA",  "action": "WATCH",      "target_weight": 12.0, "current_weight": 12.0, "allocation_change_percent": 0.0},
            {"symbol": "META",  "action": "HOLD",       "target_weight": 10.0, "current_weight": 10.0, "allocation_change_percent": 0.0},
        ]


# ─── Assertions ───────────────────────────────────────────────────────────────

class AssertionError_(Exception):
    pass


def _assert(condition: bool, msg: str):
    if not condition:
        raise AssertionError_(f"FAIL: {msg}")


def _check(label: str, condition: bool, msg: str, results: list[tuple[bool, str]]):
    results.append((condition, f"  {'PASS' if condition else 'FAIL'} [{label}] {msg}"))


# ─── Scenario runners ─────────────────────────────────────────────────────────

def _run_growth_risk_on(verbose: bool) -> bool:
    """Growth persona + RISK_ON regime → AGGRESSIVE deployment, low cash floor, growth/momentum tilt."""
    print("\n" + "─" * 60)
    print("Scenario 1: Growth + RISK_ON")
    print("─" * 60)

    persona = _make_persona_ctx("GROWTH")
    regime  = _make_regime_ctx("RISK_ON", confidence=0.80, vol_z=0.3)
    port    = _make_portfolio(n=5)
    env     = compute_policy(persona, regime, port, max_sector_pct=40)

    results: list[tuple[bool, str]] = []
    _check("bias",        env.deployment_bias in (DEPLOY_AGGRESSIVE, DEPLOY_SELECTIVE),
           f"Expected AGGRESSIVE or SELECTIVE, got {env.deployment_bias}", results)
    _check("cash_floor",  env.hard_constraints.min_cash_pct <= 6.0,
           f"Expected ≤6% cash floor (Growth+RISK_ON), got {env.hard_constraints.min_cash_pct}%", results)
    _check("emergency",   not env.emergency_override,
           "Should NOT be emergency in RISK_ON + stable", results)
    _check("suppress",    not env.hard_constraints.suppress_speculative,
           "RISK_ON should not suppress speculative for Growth", results)

    # Factor tilts: growth + momentum should be in top 3
    top2 = sorted(env.soft_factor_tilts, key=lambda f: -env.soft_factor_tilts[f])[:2]
    _check("factor_tilt", "growth" in top2 or "momentum" in top2,
           f"Expected growth/momentum in top tilts, got {top2}", results)

    # Policy alignment against aggressive allocations
    allocs = _mock_allocations(env.deployment_bias)
    pa, rc, rg, flags = compute_policy_alignment_score(allocs, env, total_value=10_000_000)
    _check("pa_score",    pa >= 60,
           f"Policy alignment {pa:.0f} should be ≥60 for aligned allocations", results)

    if verbose:
        _print_envelope(env, pa, rc, rg, flags)

    return _print_results(results)


def _run_growth_risk_off(verbose: bool) -> bool:
    """Growth persona + RISK_OFF → DEFENSIVE deployment, high cash floor, quality/dividend tilt."""
    print("\n" + "─" * 60)
    print("Scenario 2: Growth + RISK_OFF")
    print("─" * 60)

    persona = _make_persona_ctx("GROWTH")
    regime  = _make_regime_ctx("RISK_OFF", confidence=0.78, vol_z=1.1, drawdown_score=40.0)
    port    = _make_portfolio(n=5)
    env     = compute_policy(persona, regime, port, max_sector_pct=40)

    results: list[tuple[bool, str]] = []
    _check("bias",       env.deployment_bias in (DEPLOY_DEFENSIVE, DEPLOY_SELECTIVE),
           f"Expected DEFENSIVE or SELECTIVE for Growth+RISK_OFF, got {env.deployment_bias}", results)
    _check("cash_floor", env.hard_constraints.min_cash_pct >= 8.0,
           f"Cash floor {env.hard_constraints.min_cash_pct}% should be ≥8% in RISK_OFF", results)
    _check("suppress",   env.hard_constraints.suppress_speculative,
           "RISK_OFF should suppress speculative assets", results)

    # Quality and dividend should be amplified vs Growth defaults
    quality_w  = env.soft_factor_tilts.get("quality", 0)
    dividend_w = env.soft_factor_tilts.get("dividend", 0)
    _check("quality_tilt",  quality_w  >= 0.18,
           f"Quality tilt {quality_w:.0%} should be ≥18% in RISK_OFF (regime quality_bias)", results)
    _check("dividend_tilt", dividend_w >= 0.08,
           f"Dividend tilt {dividend_w:.0%} should be ≥8% in RISK_OFF (regime dividend_bias)", results)

    allocs = _mock_allocations(env.deployment_bias)
    pa, rc, rg, flags = compute_policy_alignment_score(allocs, env, total_value=10_000_000)
    _check("pa_score", pa >= 55,
           f"Policy alignment {pa:.0f} should be ≥55 for defensive allocations", results)

    if verbose:
        _print_envelope(env, pa, rc, rg, flags)

    return _print_results(results)


def _run_dividend_high_vol(verbose: bool) -> bool:
    """Dividend persona + HIGH_VOLATILITY + high vol_z → EMERGENCY, PRESERVATION, strict cash floor."""
    print("\n" + "─" * 60)
    print("Scenario 3: Dividend + HIGH_VOLATILITY (Emergency)")
    print("─" * 60)

    persona = _make_persona_ctx("DIVIDEND")
    regime  = _make_regime_ctx(
        "HIGH_VOLATILITY", confidence=0.82,
        vol_z=3.0,          # ≥2.5 → emergency
        drawdown_score=12.0, # ≤15 → emergency (extra trigger)
    )
    port = _make_portfolio(n=5, include_low_quality=True)
    env  = compute_policy(persona, regime, port, max_sector_pct=40)

    results: list[tuple[bool, str]] = []
    _check("emergency",     env.emergency_override,
           "vol_z≥2.5 and drawdown≤15 should trigger emergency override", results)
    _check("bias",          env.deployment_bias == DEPLOY_PRESERVATION,
           f"Emergency must yield PRESERVATION, got {env.deployment_bias}", results)
    _check("strictness",    env.strictness_level == STRICTNESS_EMERGENCY,
           f"Emergency must yield EMERGENCY strictness, got {env.strictness_level}", results)
    _check("cash_floor",    env.hard_constraints.min_cash_pct >= 20.0,
           f"Emergency cash floor {env.hard_constraints.min_cash_pct}% should be ≥20%", results)
    _check("max_pos",       env.hard_constraints.max_single_position_pct <= 15.0,
           f"Emergency max position {env.hard_constraints.max_single_position_pct}% should be ≤15%", results)
    _check("suppress",      env.hard_constraints.suppress_speculative,
           "Emergency must suppress speculative", results)
    _check("max_new",       env.hard_constraints.max_new_positions == 0,
           f"Emergency max_new_positions should be 0, got {env.hard_constraints.max_new_positions}", results)
    _check("low_aggr",      env.rebalance_aggressiveness <= 0.12,
           f"Emergency aggressiveness {env.rebalance_aggressiveness:.2f} should be ≤0.12", results)

    # Violations: low-quality speculative stock should be flagged
    has_spec_violation = any("SPEC1" in v or "low-quality" in v for v in env.violations)
    _check("spec_violation", has_spec_violation,
           "Low-quality speculative holding should be flagged in violations", results)

    # Policy alignment: aggressive BUY allocations in emergency → low score + flag
    aggressive_allocs = _mock_allocations(DEPLOY_AGGRESSIVE)
    pa, rc, rg, flags = compute_policy_alignment_score(aggressive_allocs, env, total_value=10_000_000)
    _check("regime_mismatch_flag",
           any("REGIME_MISMATCH" in f for f in flags),
           f"Aggressive buys during EMERGENCY should raise REGIME_MISMATCH, got flags={flags}", results)
    _check("pa_score_low", pa < 80,
           f"Policy alignment {pa:.0f} should be penalised for emergency violation", results)

    if verbose:
        _print_envelope(env, pa, rc, rg, flags)

    return _print_results(results)


def _run_momentum_transition(verbose: bool) -> bool:
    """Momentum persona + TRANSITION_RISK_OFF → DEFENSIVE, high discount, quality/dividend tilt."""
    print("\n" + "─" * 60)
    print("Scenario 4: Momentum + TRANSITION_RISK_OFF (low confidence)")
    print("─" * 60)

    persona = _make_persona_ctx("MOMENTUM")
    regime  = _make_regime_ctx(
        "TRANSITION_RISK_OFF",
        confidence=0.42,           # low confidence → big discount
        stability="VOLATILE",      # extra discount
        vol_z=1.4,
        drawdown_score=38.0,
    )
    port = _make_portfolio(n=5)
    env  = compute_policy(persona, regime, port, max_sector_pct=40)

    results: list[tuple[bool, str]] = []
    _check("emergency",     not env.emergency_override,
           f"Should NOT be emergency (vol_z={regime['vol_z_score']}, drawdown={regime['drawdown_score']})", results)
    _check("bias",          env.deployment_bias in (DEPLOY_DEFENSIVE, DEPLOY_SELECTIVE),
           f"TRANSITION_RISK_OFF + low conf should yield DEFENSIVE/SELECTIVE, got {env.deployment_bias}", results)
    _check("strictness",    env.strictness_level in (STRICTNESS_STRICT, "NORMAL"),
           f"Expected STRICT/NORMAL strictness, got {env.strictness_level}", results)
    _check("cash_floor",    env.hard_constraints.min_cash_pct >= 8.0,
           f"Transition+low conf cash {env.hard_constraints.min_cash_pct}% should be ≥8%", results)
    _check("discount",      env.confidence_discount > 0.30,
           f"Low conf + VOLATILE should give discount >30%, got {env.confidence_discount:.0%}", results)
    _check("aggr_reduced",  env.rebalance_aggressiveness < 0.70,
           f"Momentum aggressiveness {env.rebalance_aggressiveness:.2f} should be reduced <0.70 by regime+discount", results)

    # Tilt: quality and dividend should be boosted despite Momentum persona
    quality_w  = env.soft_factor_tilts.get("quality", 0)
    dividend_w = env.soft_factor_tilts.get("dividend", 0)
    _check("quality_amplified",  quality_w  >= 0.15,
           f"Quality tilt {quality_w:.0%} should be ≥15% in TRANSITION_RISK_OFF", results)
    _check("dividend_amplified", dividend_w >= 0.10,
           f"Dividend tilt {dividend_w:.0%} should be ≥10% in TRANSITION_RISK_OFF", results)

    # Max position capped vs pure Momentum default
    _check("pos_cap", env.hard_constraints.max_single_position_pct <= 22.0,
           f"Position cap {env.hard_constraints.max_single_position_pct}% should be ≤22% in TRANSITION_RISK_OFF", results)

    allocs = _mock_allocations(env.deployment_bias)
    pa, rc, rg, flags = compute_policy_alignment_score(allocs, env, total_value=10_000_000)
    _check("pa_score", pa >= 50,
           f"Policy alignment {pa:.0f} should be ≥50 for aligned allocations", results)

    if verbose:
        _print_envelope(env, pa, rc, rg, flags)

    return _print_results(results)


# ─── Display helpers ──────────────────────────────────────────────────────────

def _print_envelope(env, pa: float, rc: float, rg: float, flags: list[str]):
    d = envelope_to_dict(env)
    hc = d["hard_constraints"]
    print(f"\n  Deployment Bias:    {d['deployment_bias']}")
    print(f"  Strictness:         {d['strictness_level']}")
    print(f"  Emergency:          {d['emergency_override']}  {d.get('emergency_reason') or ''}")
    print(f"  Cash Floor:         {hc['min_cash_pct']:.1f}%")
    print(f"  Max Position:       {hc['max_single_position_pct']:.1f}%")
    print(f"  Suppress Spec:      {hc['suppress_speculative']}")
    print(f"  Turnover Cap:       {hc['max_turnover_pct']:.1f}%")
    print(f"  Max New Positions:  {hc['max_new_positions']}")
    print(f"  Risk Budget:        {d['risk_budget']:.1f}/100")
    print(f"  Rebal Aggression:   {d['rebalance_aggressiveness']:.3f}")
    print(f"  Confidence Disc:    {d['confidence_discount']:.0%}")
    tilts = sorted(d["soft_factor_tilts"].items(), key=lambda x: -x[1])
    print(f"  Factor Tilts:       {', '.join(f'{f}={v:.0%}' for f,v in tilts)}")
    if d["violations"]:
        print(f"  Violations:         {d['violations']}")
    print(f"  Policy Alignment:   {pa:.0f}/100")
    print(f"  Regime Compliance:  {rc:.0f}/100")
    print(f"  Risk Governance:    {rg:.0f}/100")
    if flags:
        print(f"  Gov Flags:          {flags}")
    print(f"\n  Prompt Block (truncated):")
    prompt_lines = d["prompt_block"].split("\n")[:12]
    for ln in prompt_lines:
        print(f"    {ln}")


def _print_results(results: list[tuple[bool, str]]) -> bool:
    all_pass = all(ok for ok, _ in results)
    for ok, msg in results:
        print(msg)
    total = len(results)
    passed = sum(1 for ok, _ in results if ok)
    status = "PASSED" if all_pass else "FAILED"
    print(f"\n  Result: {status} ({passed}/{total} checks)")
    return all_pass


# ─── Entry point ──────────────────────────────────────────────────────────────

_SCENARIOS = {
    "growth_risk_on":     _run_growth_risk_on,
    "growth_risk_off":    _run_growth_risk_off,
    "dividend_high_vol":  _run_dividend_high_vol,
    "momentum_transition": _run_momentum_transition,
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify Phase 3B.4 Policy Engine scenarios")
    parser.add_argument("--scenario", choices=list(_SCENARIOS), default=None,
                        help="Run a single named scenario (default: all)")
    parser.add_argument("--verbose", action="store_true",
                        help="Print full policy envelope details for each scenario")
    args = parser.parse_args()

    print("=" * 60)
    print("Phase 3B.4 - Adaptive Optimizer Policy Engine Verification")
    print("=" * 60)

    scenarios_to_run = (
        [(args.scenario, _SCENARIOS[args.scenario])] if args.scenario
        else list(_SCENARIOS.items())
    )

    results = []
    for name, fn in scenarios_to_run:
        try:
            ok = fn(args.verbose)
            results.append((name, ok, None))
        except Exception as exc:
            print(f"\n  ERROR in {name}: {exc}")
            results.append((name, False, str(exc)))

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    all_passed = True
    for name, ok, err in results:
        status = "PASSED" if ok else "FAILED"
        print(f"  {status}  {name}" + (f"  [{err}]" if err else ""))
        if not ok:
            all_passed = False

    total = len(results)
    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\nTotal: {passed}/{total} scenarios passed")
    sys.exit(0 if all_passed else 1)
