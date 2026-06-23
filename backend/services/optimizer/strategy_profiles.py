"""Strategy persona profiles for policy-driven portfolio optimization.

Each profile defines factor preference weights, turnover tolerance, and
rebalancing aggressiveness that directly drive AI prompt framing and
persona-adjusted scoring in the 3-layer optimizer.

Factors (Growth / Value / Momentum / Quality / Dividend) are lightweight
proxies computed from ta_score, fa_score, pe_ratio, roe, revenue_growth
already available at optimizer run-time — no extra API calls required.
"""
from __future__ import annotations

import math
from typing import Any

# ─── Profile registry ─────────────────────────────────────────────────────────

STRATEGY_PROFILES: dict[str, dict[str, Any]] = {
    "BALANCED": {
        "label": "Balanced",
        "description": "Equal weight across all factors; diversified and suitable for most investors.",
        "factor_weights": {
            "growth": 0.20, "momentum": 0.20, "quality": 0.20,
            "value": 0.20, "dividend": 0.20,
        },
        "turnover_tolerance": 0.40,
        "max_cash_preference": 0.05,
        "volatility_tolerance": 0.50,
        "sector_concentration_tolerance": 0.35,
        "rebalance_aggressiveness": 0.50,
    },
    "GROWTH": {
        "label": "Growth",
        "description": "Prioritizes revenue growth and price momentum; accepts higher volatility.",
        "factor_weights": {
            "growth": 0.40, "momentum": 0.30, "quality": 0.20,
            "value": 0.05, "dividend": 0.05,
        },
        "turnover_tolerance": 0.70,
        "max_cash_preference": 0.03,
        "volatility_tolerance": 0.75,
        "sector_concentration_tolerance": 0.45,
        "rebalance_aggressiveness": 0.75,
    },
    "VALUE": {
        "label": "Value Investing",
        "description": "Seeks undervalued stocks with strong fundamentals; patience and low turnover.",
        "factor_weights": {
            "value": 0.40, "quality": 0.30, "growth": 0.15,
            "dividend": 0.10, "momentum": 0.05,
        },
        "turnover_tolerance": 0.20,
        "max_cash_preference": 0.10,
        "volatility_tolerance": 0.35,
        "sector_concentration_tolerance": 0.30,
        "rebalance_aggressiveness": 0.25,
    },
    "DIVIDEND": {
        "label": "Dividend Income",
        "description": "Maximizes dividend yield and income stability; conservative and defensive.",
        "factor_weights": {
            "dividend": 0.45, "quality": 0.30, "value": 0.15,
            "growth": 0.05, "momentum": 0.05,
        },
        "turnover_tolerance": 0.15,
        "max_cash_preference": 0.05,
        "volatility_tolerance": 0.25,
        "sector_concentration_tolerance": 0.40,
        "rebalance_aggressiveness": 0.20,
    },
    "MOMENTUM": {
        "label": "Momentum",
        "description": "Follows price and earnings trends; high turnover, tactical execution.",
        "factor_weights": {
            "momentum": 0.50, "growth": 0.25, "quality": 0.15,
            "value": 0.05, "dividend": 0.05,
        },
        "turnover_tolerance": 0.90,
        "max_cash_preference": 0.02,
        "volatility_tolerance": 0.85,
        "sector_concentration_tolerance": 0.50,
        "rebalance_aggressiveness": 0.90,
    },
    "PASSIVE": {
        "label": "Passive / Index-Like",
        "description": "Minimal trading, broad diversification, buy-and-hold orientation.",
        "factor_weights": {
            "quality": 0.30, "value": 0.25, "growth": 0.20,
            "dividend": 0.15, "momentum": 0.10,
        },
        "turnover_tolerance": 0.10,
        "max_cash_preference": 0.02,
        "volatility_tolerance": 0.40,
        "sector_concentration_tolerance": 0.35,
        "rebalance_aggressiveness": 0.10,
    },
}

_VALID_PERSONAS = frozenset(STRATEGY_PROFILES)
_FACTORS = ("growth", "value", "momentum", "quality", "dividend")


def get_profile(persona: str) -> dict[str, Any]:
    return STRATEGY_PROFILES.get((persona or "BALANCED").upper(), STRATEGY_PROFILES["BALANCED"])


def valid_persona(persona: str) -> str:
    """Normalise + validate; returns 'BALANCED' for unknown values."""
    p = (persona or "BALANCED").upper()
    return p if p in _VALID_PERSONAS else "BALANCED"


# ─── Style Drift ──────────────────────────────────────────────────────────────

def compute_style_drift(portfolio_dna: dict[str, float], persona: str) -> dict[str, Any]:
    """Compute the distance between the current portfolio DNA and the target persona.

    Returns:
        drift_score        : 0–100 (Euclidean distance, normalised)
        drift_severity     : LOW / MEDIUM / HIGH / CRITICAL
        factor_drift       : {factor: signed_delta} (positive = over-weight vs target)
        dominant_factor    : factor with highest current exposure
        factor_alignment_score : 0–100 (100 = perfect alignment)
        rebalance_urgency  : LOW / MODERATE / HIGH / CRITICAL
        misaligned_factors : top-3 most misaligned factor names
    """
    profile = get_profile(persona)
    target_weights = profile["factor_weights"]

    # Normalise DNA 0-1 for comparison with target weights (also 0-1 fractions)
    dna_norm = {k: portfolio_dna.get(k, 50.0) / 100.0 for k in _FACTORS}

    factor_drift: dict[str, float] = {
        f: round(dna_norm.get(f, 0.0) - target_weights.get(f, 0.0), 3)
        for f in _FACTORS
    }

    # Euclidean distance normalised to 0-100
    magnitude = math.sqrt(sum(d ** 2 for d in factor_drift.values()))
    max_possible = math.sqrt(len(_FACTORS))  # each factor can be ±1
    drift_score = round(min(100.0, magnitude / max_possible * 100.0), 1)

    if drift_score < 15:
        severity = "LOW"
    elif drift_score < 35:
        severity = "MEDIUM"
    elif drift_score < 55:
        severity = "HIGH"
    else:
        severity = "CRITICAL"

    dominant_factor = max(_FACTORS, key=lambda k: portfolio_dna.get(k, 0.0))
    factor_alignment_score = round(max(0.0, 100.0 - drift_score), 1)

    # Top-3 most misaligned factors
    misaligned = sorted(
        ((f, abs(d)) for f, d in factor_drift.items()),
        key=lambda x: -x[1],
    )[:3]

    # Urgency: blend of drift magnitude and persona aggressiveness
    aggr = profile["rebalance_aggressiveness"]
    combined = (drift_score / 100.0) * 0.6 + aggr * 0.4
    if combined < 0.30:
        urgency = "LOW"
    elif combined < 0.55:
        urgency = "MODERATE"
    elif combined < 0.75:
        urgency = "HIGH"
    else:
        urgency = "CRITICAL"

    return {
        "drift_score": drift_score,
        "drift_severity": severity,
        "factor_drift": factor_drift,
        "dominant_factor": dominant_factor,
        "factor_alignment_score": factor_alignment_score,
        "rebalance_urgency": urgency,
        "misaligned_factors": [f for f, _ in misaligned],
    }


# ─── Persona context builder ──────────────────────────────────────────────────

def build_persona_context(
    persona: str,
    portfolio_dna: dict[str, float],
    drift_data: dict[str, Any],
) -> dict[str, Any]:
    """Assemble the full persona context dict injected into optimizer prompts."""
    profile = get_profile(persona)
    fw = profile["factor_weights"]

    # Sorted factor priority string: "VALUE > QUALITY > GROWTH > DIVIDEND > MOMENTUM"
    priority_order = " > ".join(
        f.upper() for f, _ in sorted(fw.items(), key=lambda x: -x[1])
    )
    top_factor = priority_order.split(" > ")[0]

    # DNA display string sorted by current exposure descending
    dna_display = " / ".join(
        f"{f.title()} {int(v)}"
        for f, v in sorted(portfolio_dna.items(), key=lambda x: -x[1])
    )

    turnover = profile["turnover_tolerance"]
    aggr = profile["rebalance_aggressiveness"]
    turnover_label = "LOW" if turnover < 0.30 else "HIGH" if turnover > 0.70 else "MODERATE"
    aggr_label = "LOW" if aggr < 0.30 else "HIGH" if aggr > 0.70 else "MODERATE"

    drift_severity = drift_data.get("drift_severity", "LOW")
    dominant = drift_data.get("dominant_factor", "quality").title()
    misaligned = [f.title() for f in drift_data.get("misaligned_factors", [])]

    return {
        "persona": valid_persona(persona),
        "persona_label": profile["label"],
        "persona_description": profile["description"],
        "factor_weights": fw,
        "portfolio_dna": portfolio_dna,
        "dna_display": dna_display,
        "dominant_factor": drift_data.get("dominant_factor", "quality"),
        "dominant_factor_label": dominant,
        "top_target_factor": top_factor,
        "priority_order": priority_order,
        "drift_score": drift_data.get("drift_score", 0.0),
        "drift_severity": drift_severity,
        "factor_drift": drift_data.get("factor_drift", {}),
        "factor_alignment_score": drift_data.get("factor_alignment_score", 100.0),
        "rebalance_urgency": drift_data.get("rebalance_urgency", "LOW"),
        "misaligned_factors": drift_data.get("misaligned_factors", []),
        "misaligned_display": ", ".join(misaligned) if misaligned else "none",
        "turnover_tolerance": turnover,
        "turnover_label": turnover_label,
        "rebalance_aggressiveness": aggr,
        "aggressiveness_label": aggr_label,
        "volatility_tolerance": profile["volatility_tolerance"],
        "max_cash_preference": profile["max_cash_preference"],
    }
