"""
Regression test for the Adaptive Policy Engine wiring in analyze_optimizer().

Covers the Jun 23 regression (c45dc8a) where `pd_with_weights` was removed in
favor of factor_engine-based portfolio_dna, but the `compute_policy(...)` call
in main.py still referenced the now-undefined `pd_with_weights`, silently
raising NameError -> policy_ctx = None on every run (regime-only fallback,
persona/confidence/policy-alignment scoring all skipped).

This test exercises the same call sequence main.py uses so a future refactor
that breaks this wiring fails loudly here instead of degrading silently in
production.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.optimizer import _compute_portfolio_weights
from services.optimizer.strategy_profiles import build_persona_context, compute_style_drift
from services.optimizer.policy_engine import (
    compute_policy,
    envelope_to_dict,
    compute_policy_alignment_score,
)


def _sample_portfolio_data():
    return [
        {"symbol": "AAPL", "market_value": 40000, "shares": 100, "avg_cost": 300,
         "ta_score": 70, "fa_score": 65, "signal": "BUY", "allow_swap": True},
        {"symbol": "PTT.BK", "market_value": 30000, "shares": 500, "avg_cost": 40,
         "ta_score": 45, "fa_score": 55, "signal": "HOLD", "allow_swap": True},
        {"symbol": "KBANK.BK", "market_value": 20000, "shares": 200, "avg_cost": 90,
         "ta_score": 30, "fa_score": 50, "signal": "SELL", "allow_swap": True},
    ]


def _sample_regime_ctx():
    return {
        "regime": "SIDEWAYS",
        "confidence": 0.65,
        "transition_stability": "STABLE",
        "vol_z_score": 0.2,
        "drawdown_score": 40.0,
        "constraints": {
            "min_cash_pct": 8.0,
            "max_single_position_pct": 22.0,
            "turnover_multiplier": 1.0,
            "suppress_speculative": False,
            "deployment_stance": "selective",
            "quality_bias": False,
            "dividend_bias": False,
            "momentum_bias": False,
        },
    }


def test_compute_policy_runs_with_weighted_portfolio_data():
    """compute_policy() must succeed given the weighted portfolio representation
    main.py builds via _compute_portfolio_weights (the restored pd_with_weights)."""
    portfolio_data = _sample_portfolio_data()
    pd_with_weights = _compute_portfolio_weights(portfolio_data)

    # The exact contract compute_policy() depends on — reused, not duplicated.
    assert all("weight_pct" in p for p in pd_with_weights)

    portfolio_dna = {"growth": 55.0, "value": 45.0, "momentum": 50.0, "quality": 60.0, "dividend": 40.0}
    drift_data = compute_style_drift(portfolio_dna, "BALANCED")
    persona_ctx = build_persona_context("BALANCED", portfolio_dna, drift_data)

    envelope = compute_policy(
        persona_ctx, _sample_regime_ctx(), pd_with_weights,
        consensus=None, max_sector_pct=40,
        effective_envelope=None,
    )
    assert envelope is not None

    policy_ctx = envelope_to_dict(envelope)
    assert policy_ctx is not None
    assert policy_ctx.get("hard_constraints") is not None


def test_policy_prompt_block_is_active_not_regime_only():
    """The generated prompt block must carry the active-policy governance
    section, not silently degrade to legacy regime-only wording."""
    portfolio_data = _sample_portfolio_data()
    pd_with_weights = _compute_portfolio_weights(portfolio_data)
    portfolio_dna = {"growth": 55.0, "value": 45.0, "momentum": 50.0, "quality": 60.0, "dividend": 40.0}
    drift_data = compute_style_drift(portfolio_dna, "BALANCED")
    persona_ctx = build_persona_context("BALANCED", portfolio_dna, drift_data)

    envelope = compute_policy(
        persona_ctx, _sample_regime_ctx(), pd_with_weights,
        consensus=None, max_sector_pct=40, effective_envelope=None,
    )
    policy_ctx = envelope_to_dict(envelope)

    prompt_block = policy_ctx["prompt_block"]
    assert "ACTIVE OPTIMIZATION POLICY" in prompt_block


def test_policy_alignment_score_executes_against_computed_envelope():
    """compute_policy_alignment_score() must run against a live PolicyEnvelope —
    this is skipped entirely whenever policy_ctx is None."""
    portfolio_data = _sample_portfolio_data()
    pd_with_weights = _compute_portfolio_weights(portfolio_data)
    portfolio_dna = {"growth": 55.0, "value": 45.0, "momentum": 50.0, "quality": 60.0, "dividend": 40.0}
    drift_data = compute_style_drift(portfolio_dna, "BALANCED")
    persona_ctx = build_persona_context("BALANCED", portfolio_dna, drift_data)

    envelope = compute_policy(
        persona_ctx, _sample_regime_ctx(), pd_with_weights,
        consensus=None, max_sector_pct=40, effective_envelope=None,
    )

    final_allocations = [
        {"symbol": "AAPL", "action": "ACCUMULATE", "target_weight": 25.0},
        {"symbol": "PTT.BK", "action": "HOLD", "target_weight": 30.0},
        {"symbol": "KBANK.BK", "action": "SELL", "target_weight": 0.0},
    ]
    pa_score, rc_score, rg_score, gov_flags, violation_details = compute_policy_alignment_score(
        final_allocations, envelope, total_value=90000.0,
    )

    assert isinstance(pa_score, float)
    assert isinstance(rc_score, float)
    assert isinstance(rg_score, float)
    assert isinstance(gov_flags, list)
    assert isinstance(violation_details, list)
