"""3-Layer Optimizer — L1 Strategist, L2 Challenger, L3 Risk Auditor.

See OPTIMIZER_PHILOSOPHY.md §5 (pipeline stages) and §6 (Belief Engine
boundary) — these layers answer belief questions only; trade selection and
funding arithmetic happen downstream, deterministically.
"""
import json
import logging
from typing import Callable
from services.ai_client import call_ai
from services.json_utils import safe_parse_json
from services.optimizer.strategy_profiles import build_persona_context, get_profile  # noqa: F401
from services.optimizer.policy_engine import (  # noqa: F401
    compute_policy_alignment_score,
    compute_concentration_breach_severity,
    get_relaxed_turnover_cap,
    envelope_to_dict as _envelope_to_dict,
    HardConstraints as _HardConstraints,
    PolicyEnvelope as _PolicyEnvelope,
)
from services.optimizer.constraint_resolver import (  # noqa: F401
    EffectiveEnvelope as _EffectiveEnvelope,
    effective_sector_cap as _effective_sector_cap,
    envelope_to_dict as _eff_env_to_dict,
)

logger = logging.getLogger(__name__)


def _emit_stage(on_stage: Callable[[str], None] | None, stage: str) -> None:
    """Fire the optional progress callback; never let it break the run."""
    if on_stage is None:
        return
    try:
        on_stage(stage)
    except Exception:  # pragma: no cover — presentation-only plumbing
        pass


def _make_envelope_from_dict(d: dict) -> _PolicyEnvelope:
    """Reconstruct a PolicyEnvelope from its serialized dict form (for scoring)."""
    hc = d.get("hard_constraints", {})
    return _PolicyEnvelope(
        hard_constraints=_HardConstraints(
            min_cash_pct            = float(hc.get("min_cash_pct", 5.0)),
            max_single_position_pct = float(hc.get("max_single_position_pct", 22.0)),
            max_sector_pct          = float(hc.get("max_sector_pct", 40.0)),
            max_turnover_pct        = float(hc.get("max_turnover_pct", 40.0)),
            suppress_speculative    = bool(hc.get("suppress_speculative", False)),
            beta_ceiling            = hc.get("beta_ceiling"),
            max_new_positions       = int(hc.get("max_new_positions", 3)),
        ),
        soft_factor_tilts       = d.get("soft_factor_tilts", {}),
        deployment_bias         = d.get("deployment_bias", "SELECTIVE"),
        risk_budget             = float(d.get("risk_budget", 55.0)),
        rebalance_aggressiveness= float(d.get("rebalance_aggressiveness", 0.5)),
        strictness_level        = d.get("strictness_level", "NORMAL"),
        emergency_override      = bool(d.get("emergency_override", False)),
        emergency_reason        = d.get("emergency_reason"),
        policy_narrative        = d.get("policy_narrative", ""),
        confidence_discount     = float(d.get("confidence_discount", 0.0)),
        violations              = list(d.get("violations", [])),
    )


_DEFAULT_LAYERS: dict = {
    "layer1": {
        "name": "Strategist",
        "role": "Capital allocation strategist",
        "provider": "anthropic",
        "model": "claude-sonnet-4-6",
    },
    "layer2": {
        "name": "Challenger",
        "role": "Independent risk-aware reviewer",
        "provider": "anthropic",
        "model": "claude-sonnet-4-6",
    },
    "layer3": {
        "name": "Risk Auditor",
        "role": "Concentration risk and assumption validator",
        "provider": "anthropic",
        "model": "claude-sonnet-4-6",
    },
}


# ─── Data helpers ─────────────────────────────────────────────────────────────

def _compute_portfolio_weights(portfolio_items: list[dict]) -> list[dict]:
    """Add market_value and weight_pct (equity-only) to each portfolio item."""
    total_mv = sum(
        (i.get("shares") or 0) * (i.get("current_price") or i.get("avg_cost") or 0)
        for i in portfolio_items
    )
    result = []
    for item in portfolio_items:
        price = item.get("current_price") or item.get("avg_cost") or 0
        mv = (item.get("shares") or 0) * price
        result.append({
            **item,
            "market_value": round(mv, 2),
            "weight_pct": round(mv / total_mv * 100, 1) if total_mv > 0 else 0.0,
        })
    return result


def _compact_p(items: list[dict]) -> list[dict]:
    return [
        {
            "symbol": i["symbol"],
            "sector": i.get("sector") or "Other",
            "signal": i.get("signal", "HOLD"),
            "combined_score": i.get("combined_score", 0),
            "ta_score": i.get("ta_score", 0),
            "fa_score": i.get("fa_score", 0),
            "trend": i.get("trend", "sideways"),
            "pe_ratio": i.get("pe_ratio"),
            "roe": round(i["roe"] * 100, 1) if i.get("roe") else None,
            "allow_swap": i.get("allow_swap", True),
            "weight_pct": i.get("weight_pct", 0.0),
            "market_value": i.get("market_value", 0.0),
            "current_price": i.get("current_price"),
            # Phase 4C.6H.3 — timing fields
            "timing_score": i.get("timing_score"),
            "execution_priority": i.get("execution_priority"),
            "momentum": i.get("momentum"),
        }
        for i in items
    ]


def _compact_w(items: list[dict]) -> list[dict]:
    return [
        {
            "symbol": i["symbol"],
            "sector": i.get("sector") or "Other",
            "signal": i.get("signal", "HOLD"),
            "combined_score": i.get("combined_score", 0),
            "ta_score": i.get("ta_score", 0),
            "fa_score": i.get("fa_score", 0),
            "trend": i.get("trend", "sideways"),
            "pe_ratio": i.get("pe_ratio"),
            "roe": round(i["roe"] * 100, 1) if i.get("roe") else None,
            # Phase 4C.6H.3 — timing fields
            "timing_score": i.get("timing_score"),
            "execution_priority": i.get("execution_priority"),
            "momentum": i.get("momentum"),
        }
        for i in items
    ]


def _build_score_context_map(pc: list[dict], wc: list[dict]) -> dict[str, dict]:
    """symbol -> compact score dict, for attaching deterministic context to AI rows.

    Portfolio holdings take priority over watchlist entries for symbols present in both
    (fresher weight/price data). No new calculations — pc/wc are already computed by
    _compact_p/_compact_w before this is called.
    """
    score_map: dict[str, dict] = {w["symbol"]: w for w in wc}
    score_map.update({p["symbol"]: p for p in pc})
    return score_map


# Reason UX (progressive disclosure) — deterministic fields attached to swap/allocation
# rows by symbol lookup, mirroring the existing per_sym_exec execution-metadata join.
_SCORE_CONTEXT_FIELDS = ("ta_score", "fa_score", "pe_ratio", "roe", "sector", "combined_score", "timing_score")


def _apply_score_context(row: dict, score_map: dict[str, dict] | None, symbol: str | None) -> None:
    if not score_map or not symbol:
        return
    ctx = score_map.get(symbol)
    if not ctx:
        return
    for field in _SCORE_CONTEXT_FIELDS:
        if field in row:
            continue
        value = ctx.get(field)
        if value is not None:
            row[field] = value


_L1_BUY_SIGNALS = {"BUY", "ACCUMULATE", "WATCH"}


def _compress_for_layer1(pc: list[dict], wc: list[dict]) -> tuple[list[dict], list[dict]]:
    """Strip data to minimum Layer 1 needs — shortened keys reduce prompt tokens."""
    c_pc = [
        {
            "s": i["symbol"],
            "sec": i.get("sector", "Other"),
            "w": round(i.get("weight_pct", 0), 1),
            "mv": round(i.get("market_value", 0)),
            "fa": i.get("fa_score", 0),
            "ta": i.get("ta_score", 0),
            "sig": i.get("signal", "HOLD"),
            "swap": i.get("allow_swap", True),
            "ts": i.get("timing_score"),        # Phase 4C.6H.3 — timing score
            "pr": i.get("execution_priority"),  # Phase 4C.6H.3 — execution priority
        }
        for i in pc
    ]
    actionable = [w for w in wc if w.get("signal", "HOLD") in _L1_BUY_SIGNALS]
    actionable.sort(key=lambda x: -(x.get("fa_score", 0) + x.get("ta_score", 0)))
    c_wc = [
        {
            "s": w["symbol"],
            "sec": w.get("sector", "Other"),
            "fa": w.get("fa_score", 0),
            "ta": w.get("ta_score", 0),
            "sig": w.get("signal", "WATCH"),
            "ts": w.get("timing_score"),        # Phase 4C.6H.3 — timing score
            "pr": w.get("execution_priority"),  # Phase 4C.6H.3 — execution priority
        }
        for w in actionable[:10]
    ]
    return c_pc, c_wc


def _postprocess_swaps(swaps: list[dict], sell_forced: list[str], locked: list[str]) -> list[dict]:
    """Ensure forced SELLs appear in swap list and remove locked symbols."""
    locked_set = set(locked)
    result = [s for s in swaps if s.get("sell_symbol") not in locked_set and s.get("buy_symbol") not in locked_set]
    covered = {s["sell_symbol"] for s in result if s.get("type") == "SELL"}
    for sym in sell_forced:
        if sym not in covered:
            result.insert(0, {"sell_symbol": sym, "buy_symbol": None, "reason": "Forced exit: SELL signal.", "score_improvement": 0, "sector": "Other", "type": "SELL"})
    return result


def _normalize_l1_swaps(swaps: list, score_map: dict[str, dict] | None = None) -> list[dict]:
    """Normalise L1 compact swap objects into the full swap format used downstream."""
    result = []
    for s in (swaps or []):
        sell = s.get("sell") or s.get("sell_symbol")
        buy = s.get("buy") or s.get("buy_symbol")
        row = {
            "sell_symbol": sell,
            "buy_symbol":  buy,
            "reason": str(s.get("reason") or s.get("r") or ""),
            "score_improvement": float(
                s.get("score_delta") or s.get("delta") or s.get("score_improvement") or 0
            ),
            "sector": s.get("sector", "Other"),
            "type": s.get("type", "SWAP"),
        }
        # Reason UX — deterministic context for the expanded detail panel (subject = buy
        # side when present, since that's the opportunity being evaluated; else sell side).
        _apply_score_context(row, score_map, buy or sell)
        result.append(row)
    return result


def _normalize_allocations(
    allocs: list,
    pc_map: dict[str, float] | None = None,
    score_map: dict[str, dict] | None = None,
) -> list[dict]:
    """Normalise L2 allocation objects to the internal TargetAllocation schema.

    pc_map: symbol → actual weight_pct from portfolio data (authoritative source for current_weight).
    allocation_change_percent and estimated_amount are computed in Python — never trusted from AI.
    score_map: symbol → compact score dict (see _build_score_context_map), attached for Reason UX.
    """
    result = []
    for a in (allocs or []):
        sym = str(a.get("symbol") or a.get("s") or "")
        target_w = float(a.get("target_weight") or a.get("tw") or 0)
        # Use real portfolio weight if available; AI's reported current_weight is a fallback only
        current_w = (pc_map or {}).get(sym, float(a.get("current_weight") or a.get("w") or 0))
        change_pct = round(target_w - current_w, 2)
        row = {
            "symbol": sym,
            "current_weight": round(current_w, 2),
            "target_weight": round(target_w, 2),
            "action": str(a.get("action") or a.get("sig") or "HOLD").upper(),
            "allocation_change_percent": change_pct,
            "estimated_amount": 0,  # filled in by caller once total_value is known
            "reason": str(a.get("reason") or a.get("r") or ""),
        }
        _apply_score_context(row, score_map, sym)
        result.append(row)
    return [a for a in result if a["symbol"]]


def _snap_neutral_actions(allocations: list[dict]) -> None:
    """HOLD/WATCH are investment-conviction signals, not capital-movement instructions.
    Pin target_weight back to current_weight so no downstream consumer (Cash Impact
    column, action_summary, sector-weight projection) can show a nonzero trade for a
    row the AI didn't intend as an execution instruction. Mutates in place.
    """
    for a in allocations:
        if (a.get("action") or "").upper() in ("HOLD", "WATCH"):
            a["target_weight"] = a.get("current_weight", 0.0)
            a["allocation_change_percent"] = 0.0
            a["estimated_amount"] = 0


def _rebuild_watchlist_ranking(buy_symbols: list, wc: list[dict]) -> list[dict]:
    """Rebuild watchlist_ranking from BUY/ACCUMULATE targets + watchlist data."""
    wc_map = {w["symbol"]: w for w in wc}
    seen: set[str] = set()
    ranked: list[str] = []
    for sym in (buy_symbols or []):
        if sym in wc_map and sym not in seen:
            ranked.append(sym)
            seen.add(sym)
    for w in sorted(wc, key=lambda x: -(x.get("fa_score", 0) + x.get("ta_score", 0))):
        if w["symbol"] not in seen:
            ranked.append(w["symbol"])
            seen.add(w["symbol"])
    return [
        {
            "symbol": sym,
            "rank": i + 1,
            "signal": wc_map.get(sym, {}).get("signal", "WATCH"),
            "combined_score": wc_map.get(sym, {}).get("combined_score", 0),
            "sector": wc_map.get(sym, {}).get("sector", "Other"),
            "suggested_allocation_pct": 0.0,
            "reasoning": "",
        }
        for i, sym in enumerate(ranked)
    ]


# ─── Sector normalization ─────────────────────────────────────────────────────

_CANONICAL_SECTORS = frozenset({
    "Technology", "Financial", "Energy", "Healthcare",
    "Consumer", "Industrial", "Real Estate", "Utilities", "Other",
})


def normalize_sector(raw: str | None) -> str:
    """Map raw yfinance/FA sector strings to canonical frontend sector keys."""
    s = (raw or "").strip()
    if s in _CANONICAL_SECTORS:
        return s
    if "Financial" in s:
        return "Financial"
    if "Consumer" in s:
        return "Consumer"
    if "Industrial" in s:
        return "Industrial"
    return "Other"


# ─── Sector weight helpers ────────────────────────────────────────────────────

def calculate_current_sector_weights(portfolio_items: list[dict]) -> dict:
    """Actual sector weights by market value (shares × current_price)."""
    sector_values: dict[str, float] = {}
    for item in portfolio_items:
        sector = normalize_sector(item.get("sector"))
        price = item.get("current_price") or item.get("avg_cost") or 0
        mv = (item.get("shares") or 0) * price
        sector_values[sector] = sector_values.get(sector, 0.0) + mv
    total = sum(sector_values.values())
    if total == 0:
        return {}
    return {
        s: {"value": round(v, 2), "weight_pct": round(v / total * 100, 1)}
        for s, v in sorted(sector_values.items(), key=lambda x: -x[1])
    }


def calculate_projected_sector_weights(portfolio_items: list[dict], swaps: list[dict]) -> dict:
    """Simulate portfolio after swaps and recompute sector weights (legacy path)."""
    holdings: dict[str, dict] = {}
    for item in portfolio_items:
        sector = normalize_sector(item.get("sector"))
        price = item.get("current_price") or item.get("avg_cost") or 0
        mv = (item.get("shares") or 0) * price
        holdings[item["symbol"]] = {"sector": sector, "value": mv}

    for swap in swaps:
        sell_sym = swap.get("sell_symbol")
        buy_sym = swap.get("buy_symbol")
        sector = normalize_sector(swap.get("sector"))
        sell_val = holdings.pop(sell_sym, {"value": 0})["value"] if sell_sym else 0
        if buy_sym and sell_val > 0:
            holdings[buy_sym] = {"sector": sector, "value": sell_val}

    sector_values: dict[str, float] = {}
    for h in holdings.values():
        sector_values[h["sector"]] = sector_values.get(h["sector"], 0.0) + h["value"]
    total = sum(sector_values.values())
    if total == 0:
        return {}
    return {
        s: {"value": round(v, 2), "weight_pct": round(v / total * 100, 1)}
        for s, v in sorted(sector_values.items(), key=lambda x: -x[1])
    }


def calculate_projected_sector_weights_from_allocations(
    portfolio_items: list[dict],
    allocations: list[dict],
    total_value: float,
) -> dict:
    """Compute projected sector weights from target_allocations."""
    holdings: dict[str, dict] = {}
    for item in portfolio_items:
        sector = normalize_sector(item.get("sector"))
        price = item.get("current_price") or item.get("avg_cost") or 0
        mv = (item.get("shares") or 0) * price
        holdings[item["symbol"]] = {"sector": sector, "value": mv}

    for alloc in allocations:
        sym = alloc.get("symbol", "")
        action = alloc.get("action", "HOLD")
        target_weight = float(alloc.get("target_weight") or 0)
        if action == "SELL":
            holdings.pop(sym, None)
        elif action not in ("WATCH", "HOLD") and total_value > 0:
            sector = normalize_sector(holdings.get(sym, {}).get("sector"))
            new_mv = total_value * target_weight / 100.0
            if sym in holdings:
                holdings[sym]["value"] = new_mv
            else:
                holdings[sym] = {"sector": sector, "value": new_mv}

    sector_values: dict[str, float] = {}
    for h in holdings.values():
        sector_values[h["sector"]] = sector_values.get(h["sector"], 0.0) + h["value"]
    total = sum(sector_values.values())
    if total == 0:
        return {}
    return {
        s: {"value": round(v, 2), "weight_pct": round(v / total * 100, 1)}
        for s, v in sorted(sector_values.items(), key=lambda x: -x[1])
    }


def _compute_sector_warnings(
    current: dict,
    projected: dict,
    sector_limits: dict | None,
    max_sector_pct: int,
) -> list[dict]:
    """Return per-sector status vs allocation limits for current and projected weights."""
    all_sectors = set(current) | set(projected)
    result = []
    for sector in sorted(all_sectors):
        cur_pct = current.get(sector, {}).get("weight_pct", 0.0)
        proj_pct = projected.get(sector, {}).get("weight_pct", 0.0)
        if cur_pct == 0 and proj_pct == 0:
            continue
        limits = sector_limits or {}
        limit = limits.get(sector) or limits.get("default") or max_sector_pct
        if proj_pct > limit:
            status = "EXCEEDS"
        elif proj_pct > limit * 0.8:
            status = "WARNING"
        else:
            status = "OK"
        result.append({
            "sector": sector,
            "current_pct": cur_pct,
            "projected_pct": proj_pct,
            "limit_pct": int(limit),
            "status": status,
        })
    return result


# ─── Derived swap suggestions (backward compat) ───────────────────────────────

def _derive_swap_suggestions(
    allocations: list[dict],
    sell_forced: list[str],
    locked: list[str],
) -> list[dict]:
    """Derive legacy swap_suggestions format from target_allocations."""
    suggestions: list[dict] = []
    locked_set = set(locked)

    covered_forced = {a["symbol"] for a in allocations if a.get("action") == "SELL"}
    for sym in sell_forced:
        if sym not in covered_forced:
            suggestions.append({
                "sell_symbol": sym, "buy_symbol": None,
                "reason": "Forced exit: SELL signal.", "score_improvement": 0,
                "sector": "Other", "type": "SELL",
            })

    reduces = [a for a in allocations if a.get("action") in ("SELL", "REDUCE") and a.get("allocation_change_percent", 0) < -1]
    buys    = [a for a in allocations if a.get("action") in ("BUY", "ACCUMULATE") and a.get("allocation_change_percent", 0) > 1]

    for a in allocations:
        if a.get("action") == "SELL":
            suggestions.append({
                "sell_symbol": a["symbol"], "buy_symbol": None,
                "reason": a.get("reason", ""), "score_improvement": 0,
                "sector": "Other", "type": "SELL",
            })

    buy_idx = 0
    for red in reduces:
        if red.get("action") == "SELL":
            continue
        buy = buys[buy_idx] if buy_idx < len(buys) else None
        if buy_idx < len(buys):
            buy_idx += 1
        suggestions.append({
            "sell_symbol": red["symbol"],
            "buy_symbol": buy["symbol"] if buy else None,
            "reason": red.get("reason", "") + (" → " + buy.get("reason", "") if buy else ""),
            "score_improvement": round(abs(red.get("allocation_change_percent", 0)), 1),
            "sector": "Other",
            "type": "SWAP" if buy else "REDUCE",
        })

    for i, buy in enumerate(buys):
        if i >= buy_idx:
            suggestions.append({
                "sell_symbol": None,
                "buy_symbol": buy["symbol"],
                "reason": buy.get("reason", ""),
                "score_improvement": round(buy.get("allocation_change_percent", 0), 1),
                "sector": "Other",
                "type": "SWAP",
            })

    return [s for s in suggestions if not (s.get("sell_symbol") in locked_set and s.get("type") == "SWAP")]


# ─── Consensus Engine ─────────────────────────────────────────────────────────

_CONSENSUS_LEGACY_AGREES: dict[str, bool] = {
    "STRONG_CONSENSUS":        True,
    "REFINED_CONSENSUS":       True,
    "PARTIAL_CONSENSUS":       True,
    "WEAK_CONSENSUS":          False,
    "RISK_CONFLICT":           True,
    "STRATEGIC_CONFLICT":      False,
    "NO_ACTION_CONSENSUS":     True,
    "NO_REBALANCE_CONSENSUS":  True,  # stabilization-layer injected state
}


def _consensus_engine(l1: dict, l2: dict, l3: dict) -> dict:
    """Classify optimizer output into one of 7 consensus types with alignment scoring."""

    # ── L2 inputs ─────────────────────────────────────────────────────────────
    agrees            = bool(l2.get("agrees_with_layer1", True))
    disagreements     = list(l2.get("disagreements", []) or [])
    xai_status        = l2.get("status", "REBALANCE")
    xai_score         = int(l2.get("rebalance_opportunity_score") or 50)
    no_action_reason  = l2.get("no_action_reason")
    no_action_summary = l2.get("no_action_summary")
    l2_allocs         = list(l2.get("target_allocations", []) or [])

    # ── L3 inputs ─────────────────────────────────────────────────────────────
    risk_flags   = list(l3.get("risk_flags", []) or [])
    safer_choice = l3.get("safer_choice", "layer1")
    final_risk   = l3.get("final_risk_level", "medium")
    if final_risk not in ("low", "medium", "high"):
        final_risk = "high"
    critical_flags = [f for f in risk_flags if f.get("severity", "").upper() == "CRITICAL"]
    high_flags     = [f for f in risk_flags if f.get("severity", "").upper() in ("HIGH", "CRITICAL")]

    # ── Buy / sell overlap (L1 vs L2) ────────────────────────────────────────
    l1_buys  = set(l1.get("top_buys", []) or [])
    l1_swaps = list(l1.get("swap_suggestions", []) or [])
    l1_sells = {s["sell_symbol"] for s in l1_swaps if s.get("sell_symbol")}

    l2_buy_syms  = {a["symbol"] for a in l2_allocs if a.get("action") in ("BUY", "ACCUMULATE")}
    l2_sell_syms = {a["symbol"] for a in l2_allocs if a.get("action") in ("SELL", "REDUCE")}

    buy_union    = l1_buys | l2_buy_syms
    sell_union   = l1_sells | l2_sell_syms
    buy_overlap  = len(l1_buys & l2_buy_syms)  / len(buy_union)  if buy_union  else 1.0
    sell_overlap = len(l1_sells & l2_sell_syms) / len(sell_union) if sell_union else 1.0

    # ── Alignment scores (0–100) ──────────────────────────────────────────────
    base             = 80 if agrees else 30
    disagree_penalty = min(35, len(disagreements) * 12)
    overlap_bonus    = round((buy_overlap * 0.6 + sell_overlap * 0.4) * 20 - 10)  # –10 … +10
    strategist_alignment_score = int(max(5, min(95, base - disagree_penalty + overlap_bonus)))

    # When L1 parsing failed entirely, strategist alignment is unknowable — hard-cap
    # it so the consensus type reflects the degraded signal quality.
    l1_parse_failure = any("L1_PARSE_FAILURE" in (d or "") for d in disagreements)
    if l1_parse_failure or l1.get("error"):
        strategist_alignment_score = min(strategist_alignment_score, 28)

    if not risk_flags:
        risk_alignment_score = 92
    elif critical_flags:
        risk_alignment_score = 12
    elif high_flags:
        risk_alignment_score = max(30, 55 - len(high_flags) * 8)
    else:
        medium_flags = [f for f in risk_flags if f.get("severity", "").upper() == "MEDIUM"]
        risk_alignment_score = max(50, 80 - len(medium_flags) * 8)

    consensus_strength_score = round(strategist_alignment_score * 0.65 + risk_alignment_score * 0.35)

    # ── Consensus type classification ─────────────────────────────────────────
    is_no_action = (
        xai_status == "NO_ACTION"
        and xai_score < 40
        and not critical_flags
        and not (final_risk == "high" and high_flags)
    )

    if is_no_action:
        consensus_type     = "NO_ACTION_CONSENSUS"
        confidence         = "high" if xai_score < 20 else "medium"
        recommended        = "no_action"
        consensus_decision = "NO_ACTION"

    elif critical_flags or (final_risk == "high" and len(high_flags) >= 2):
        consensus_type     = "RISK_CONFLICT"
        confidence         = "low"
        recommended        = "neither"
        consensus_decision = "REVIEW"

    elif not agrees and strategist_alignment_score < 40:
        consensus_type     = "STRATEGIC_CONFLICT"
        confidence         = "low"
        recommended        = "layer2" if safer_choice == "layer2" else "neither"
        consensus_decision = "REBALANCE"

    elif final_risk == "high" and high_flags:
        consensus_type     = "RISK_CONFLICT"
        confidence         = "medium" if agrees else "low"
        recommended        = "layer1" if agrees and safer_choice != "layer2" else "layer2"
        consensus_decision = "REBALANCE"

    elif strategist_alignment_score >= 70 and risk_alignment_score >= 65:
        consensus_type     = "STRONG_CONSENSUS"
        confidence         = "high"
        recommended        = "layer1"
        consensus_decision = "REBALANCE"

    elif agrees and strategist_alignment_score >= 50:
        consensus_type     = "REFINED_CONSENSUS"
        confidence         = "medium"
        recommended        = "layer2"
        consensus_decision = "REBALANCE"

    elif strategist_alignment_score >= 35:
        consensus_type     = "PARTIAL_CONSENSUS"
        confidence         = "medium"
        recommended        = "layer2" if safer_choice == "layer2" else "layer1"
        consensus_decision = "REBALANCE"

    else:
        consensus_type     = "WEAK_CONSENSUS"
        confidence         = "low"
        recommended        = safer_choice if safer_choice in ("layer1", "layer2") else "neither"
        consensus_decision = "REBALANCE"

    # ── Refinement summary (explainability) ───────────────────────────────────
    if consensus_type in ("NO_ACTION_CONSENSUS", "NO_REBALANCE_CONSENSUS"):
        refinement_summary = (
            no_action_summary
            or "All layers independently concluded the portfolio is well-balanced with insufficient edge for rebalancing."
        )
    elif consensus_type == "STRONG_CONSENSUS":
        refinement_summary = "All layers agree on a clear rebalancing path with strong conviction and acceptable risk."
    elif consensus_type == "REFINED_CONSENSUS":
        if disagreements:
            d_text = "; ".join(disagreements[:2])
            refinement_summary = f"Challenger agrees with the Strategist's core thesis but refines: {d_text}"
        else:
            refinement_summary = "Challenger confirms the Strategist's allocation direction with expanded positioning detail."
    elif consensus_type == "PARTIAL_CONSENSUS":
        n = len(disagreements)
        refinement_summary = (
            f"Challenger partially validates the Strategist's proposal "
            f"with {n} material difference{'s' if n != 1 else ''}."
        )
    elif consensus_type == "RISK_CONFLICT":
        if critical_flags:
            syms = ", ".join(f.get("symbol", "?") for f in critical_flags[:3])
            refinement_summary = (
                f"Risk Auditor identified CRITICAL concentration risk in {syms} — "
                "execution blocked pending manual review."
            )
        else:
            syms = ", ".join(f.get("symbol", "?") for f in high_flags[:3])
            refinement_summary = (
                f"Risk Auditor flagged high-severity risks in {syms} "
                "despite strategic alignment between layers."
            )
    elif consensus_type == "STRATEGIC_CONFLICT":
        refinement_summary = (
            "Challenger fundamentally rejects the Strategist's proposed allocation direction — "
            "review both plans manually before acting."
        )
    else:  # WEAK_CONSENSUS
        refinement_summary = (
            "Low confidence across layers — recommendations are inconsistent. "
            "Consider re-running after refreshing analysis data."
        )

    # ── Recommended action text ───────────────────────────────────────────────
    parts: list[str] = []
    if consensus_type in ("NO_ACTION_CONSENSUS", "NO_REBALANCE_CONSENSUS"):
        parts.append("No rebalancing action recommended at this time.")
        if no_action_summary:
            parts.append(no_action_summary)
        elif no_action_reason:
            parts.append(f"Reason: {no_action_reason.replace('_', ' ').lower()}.")
        if high_flags:
            syms = ", ".join(f.get("symbol", "?") for f in high_flags[:3])
            parts.append(f"Continue monitoring: {syms}.")
    elif consensus_type == "STRONG_CONSENSUS":
        parts.append("Follow Strategist allocation plan — high conviction across all layers.")
    elif consensus_type == "REFINED_CONSENSUS":
        parts.append("Follow Challenger's refined allocation plan — improves on Strategist's core direction.")
    elif consensus_type == "PARTIAL_CONSENSUS":
        if recommended == "layer2":
            parts.append("Consider Challenger's allocation — it addresses key gaps in the Strategist's plan.")
        else:
            parts.append("Follow Strategist plan with caution — Challenger has material reservations.")
    elif consensus_type == "RISK_CONFLICT":
        parts.append("Address Risk Auditor's flags before executing any rebalancing.")
        if high_flags:
            syms = ", ".join(f.get("symbol", "?") for f in high_flags[:3])
            parts.append(f"High-risk positions: {syms}.")
    elif consensus_type == "STRATEGIC_CONFLICT":
        parts.append("Significant strategic disagreement — review both Strategist and Challenger plans manually.")
        if disagreements:
            parts.append(f"Key conflict: {disagreements[0]}")
    else:  # WEAK_CONSENSUS
        parts.append("Low conviction — neither proposal is strongly supported. Review manually.")

    if l3.get("auditor_notes"):
        parts.append(l3["auditor_notes"])

    return {
        # New fields
        "consensus_type":             consensus_type,
        "consensus_strength_score":   consensus_strength_score,
        "strategist_alignment_score": strategist_alignment_score,
        "risk_alignment_score":       risk_alignment_score,
        "disagreement_reasons":       disagreements,
        "refinement_summary":         refinement_summary,
        # Legacy fields (backward compat)
        "agrees":             _CONSENSUS_LEGACY_AGREES.get(consensus_type, agrees),
        "consensus_decision": consensus_decision,
        "confidence":         confidence,
        "recommended":        recommended,
        "final_risk_level":   final_risk,
        "risk_flag_count":    len(risk_flags),
        "recommended_action": " ".join(parts),
    }


# ─── Prompt builders ──────────────────────────────────────────────────────────

def _layer1_prompt(
    c_pc: list[dict],
    c_wc: list[dict],
    sell_forced: list[str],
    swap_eligible: list[str],
    max_sector_pct: int = 40,
    sector_limits: dict | None = None,
    max_stocks: int = 12,
    current_count: int = 0,
    persona_context: dict | None = None,
    regime_context: dict | None = None,
    policy_context: dict | None = None,
    effective_envelope: "_EffectiveEnvelope | None" = None,
    t1_breach_note: str = "",
    execution_context: dict | None = None,
) -> str:
    # Phase 3B.5: use resolved per-sector limits when available; fall back to raw sector_limits
    if effective_envelope is not None:
        sl = {s: int(v) for s, v in effective_envelope.effective_sector_limits.items()}
        sl.setdefault("default", int(effective_envelope.global_sector_cap.effective))
    else:
        sl = sector_limits or {"default": max_sector_pct}

    # Policy block (3B.4) — overrides / supplements regime + strategy blocks
    policy_block = ""
    if policy_context and policy_context.get("prompt_block"):
        policy_block = policy_context["prompt_block"] + "\n"

    regime_block = ""
    if regime_context and not policy_context:
        # Only inject standalone regime block when no unified policy block is present
        from services.analytics.regime_detector import build_regime_prompt_block
        regime_block = build_regime_prompt_block(regime_context) + "\n"

    strategy_block = ""
    if persona_context:
        p_label      = persona_context.get("persona_label", "Balanced").upper()
        p_dna        = persona_context.get("dna_display", "")
        p_drift_sev  = persona_context.get("drift_severity", "LOW")
        p_drift_sc   = persona_context.get("drift_score", 0)
        p_dominant   = persona_context.get("dominant_factor_label", "")
        p_top        = persona_context.get("top_target_factor", "")
        p_priority   = persona_context.get("priority_order", "")
        p_turn_lbl   = persona_context.get("turnover_label", "MODERATE")
        p_urgency    = persona_context.get("rebalance_urgency", "MODERATE")
        p_misaligned = persona_context.get("misaligned_display", "none")
        p_turn       = persona_context.get("turnover_tolerance", 0.5)

        low_turn_note  = "PREFER incremental DCA; avoid large single-step replacements." if p_turn < 0.30 else ""
        high_turn_note = "High turnover is ACCEPTABLE — act decisively on factor misalignment." if p_turn > 0.70 else ""

        strategy_block = f"""[STRATEGY CONTEXT — MANDATORY]
Target Persona: {p_label}
Current Portfolio DNA: {p_dna}
Dominant Style: {p_dominant} → target dominant is {p_top}
Style Drift: {p_drift_sev} ({p_drift_sc}/100) | Rebalance Urgency: {p_urgency}
Factor Priority: {p_priority}
Most Misaligned: {p_misaligned}
Turnover Tolerance: {p_turn_lbl} ({int(p_turn * 100)}%)

[STRATEGY MANDATE]
All swap proposals MUST increase {p_top} factor alignment.
{low_turn_note}{high_turn_note}
Stocks selected for BUY/ACCUMULATE must support the {p_label} factor profile.
Stocks proposed for REDUCE/SELL must be misaligned with {p_label} or overweight.

"""

    # Build a note when the policy envelope already shows hard-constraint violations.
    # This prevents L1 from freezing when historical positions breach the limits —
    # it must actively propose REDUCE actions to resolve the breach step-by-step.
    violation_note = ""
    if policy_context:
        hc = policy_context.get("hard_constraints", {})
        max_pos = float(hc.get("max_single_position_pct", 22.0))
        policy_violations = policy_context.get("violations", [])
        if policy_violations:
            violation_note = (
                f"\nPOLICY VIOLATIONS ACTIVE: {', '.join(policy_violations)}\n"
                f"Max single position is {max_pos:.0f}%. Every position currently over this limit "
                "MUST be targeted for REDUCE in your swaps (sell=SYM, buy=null). "
                "Step-by-step trimming is preferred over full exits. "
                "Do NOT output no_action — a REDUCE is always the right response to a breach.\n"
            )
        else:
            # Even without flagged violations, remind about the position cap
            violation_note = (
                f"\nPolicy max single position: {max_pos:.0f}%. "
                "If any holding currently exceeds this, propose an incremental REDUCE swap.\n"
            )

    execution_block = ""
    if execution_context:
        from services.optimizer.execution_penalty import build_execution_prompt_block
        execution_block = build_execution_prompt_block(execution_context)

    timing_block = """[TIMING INTELLIGENCE — Phase 4C.6H]
Each symbol carries ts= (timing score 0-100) and pr= (execution priority: HIGH/MEDIUM/LOW/DEFER).
Timing Score = entry quality: trend + momentum + relative strength + volume.
  ts≥80 / HIGH  : strong entry → increase conviction for BUY/ACCUMULATE ranking
  ts 60-79 / MED: acceptable  → proceed normally
  ts 40-59 / LOW : weak entry → reduce urgency; rank watchlist candidates lower
  ts<40 / DEFER  : poor entry → note in sector_flags; still eligible as lower-ranked top_buy
Timing informs urgency — it does not block. A DEFER symbol with strong fundamentals is still top_buys material at lower rank.

"""

    return f"""{policy_block}{regime_block}{strategy_block}{t1_breach_note}{execution_block}{timing_block}You are a STRATEGIST. Output swap targets in JSON only.
No explanation. No prose. Only valid JSON output.
{violation_note}
Portfolio: {json.dumps(c_pc)}
Watchlist: {json.dumps(c_wc)}
Sector limits: {json.dumps(sl)}
Swap eligible: {swap_eligible or "none"}
Forced sells: {sell_forced or "none"}

STOCK COUNT: {current_count}/{max_stocks} max unique stocks after rebalancing.
SIGNALS: BUY=add aggressively, ACCUMULATE=add gradually, HOLD=keep, WATCH=monitor, REDUCE=trim, SELL=exit

STABILIZATION MANDATE — quality over quantity. Every proposed change must clear a high bar:
- MINIMUM DRIFT: only propose allocation changes ≥ 3%. Smaller shifts create noise with no economic value.
- HIGH CONVICTION: only propose swaps with strong, defensible signal quality improvement.
- TURNOVER PENALTY: fewer trades are better. Each trade incurs real friction cost (~0.15% per 1% NAV).
- PREFER holding well-positioned assets over constant micro-rotation.

EVALUATE ALL FIVE — but only act if improvement is material:
1. Sector concentration: any sector at or above its limit? → propose meaningful rebalancing swap (≥5% shift)
2. Watchlist opportunities: BUY/ACCUMULATE candidate with clear edge over current holdings? → rank in top_buys
3. Overweight positions: swap-eligible stock >25%? → consider REDUCE, but only if drift ≥ 3%
4. Low-score holdings: weak fa+ta vs watchlist with 10+ score advantage? → consider swap
5. Policy violations: active CONCENTRATION_BREACH or SECTOR_BREACH? → propose remediation (mandatory)

priority="no_action" when ALL of the following are true:
- No sector breach or position limit breach
- No watchlist candidate has a clearly superior score (10+ advantage) over current holdings
- All current positions are within 3% of their ideal weight
- No urgent regime or policy signal

Output schema — nothing else. Max 400 tokens.
swaps: max 3 (sell or buy may be null for one-sided REDUCE or ACCUMULATE from cash)
top_buys: max 5 watchlist symbols ranked by signal quality
sector_flags: max 3 short strings
priority: one word only
"r" = one reason for the swap, under 12 words (e.g. "Technology at 45% > 30% limit").

{{"swaps":[{{"sell":"SYM|null","buy":"SYM|null","score_delta":0.0,"sector":"S","type":"SELL|SWAP|REDUCE","r":"<12 words"}}],"top_buys":["S"],"sector_flags":["S 45%>30%"],"priority":"growth"}}"""


def _layer2_prompt(
    pc: list[dict],
    wc: list[dict],
    l1: dict,
    role: str = "",
    cash_balance: float = 0.0,
    total_value: float = 0.0,
    persona_context: dict | None = None,
    regime_context: dict | None = None,
    policy_context: dict | None = None,
    t1_breach_note: str = "",
    execution_context: dict | None = None,
) -> str:
    role_line = f"Your role: {role}\n\n" if role else ""

    policy_block = ""
    if policy_context and policy_context.get("prompt_block"):
        policy_block = policy_context["prompt_block"] + "\n"

    regime_block = ""
    if regime_context and not policy_context:
        from services.analytics.regime_detector import build_regime_prompt_block
        regime_block = build_regime_prompt_block(regime_context) + "\n"
    l1_swaps    = l1.get("swap_suggestions", l1.get("swaps", []))
    l1_top_buys = l1.get("top_buys", [])
    l1_flags    = l1.get("sector_flags", [])
    l1_priority = l1.get("priority", "balanced")

    strategy_block = ""
    if persona_context:
        p_label     = persona_context.get("persona_label", "Balanced")
        p_dna       = persona_context.get("dna_display", "")
        p_drift_sev = persona_context.get("drift_severity", "LOW")
        p_drift_sc  = persona_context.get("drift_score", 0)
        p_priority  = persona_context.get("priority_order", "")
        p_turn_lbl  = persona_context.get("turnover_label", "MODERATE")
        p_urgency   = persona_context.get("rebalance_urgency", "MODERATE")
        p_desc      = persona_context.get("persona_description", "")
        p_turn      = persona_context.get("turnover_tolerance", 0.5)
        p_max_cash  = persona_context.get("max_cash_preference", 0.05)
        p_vol       = persona_context.get("volatility_tolerance", 0.5)

        strategy_block = f"""[STRATEGY CONTEXT — MANDATORY INVESTMENT POLICY]
Target Persona: {p_label.upper()} — {p_desc}
Current Portfolio DNA: {p_dna}
Style Drift: {p_drift_sev} ({p_drift_sc}/100) | Urgency: {p_urgency}
Factor Priority: {p_priority}
Turnover Tolerance: {p_turn_lbl} ({int(p_turn * 100)}%)
Max Cash Preference: {int(p_max_cash * 100)}% of portfolio
Volatility Tolerance: {int(p_vol * 100)}% (0%=very defensive, 100%=aggressive)

[ALLOCATION POLICY]
Your allocation plan MUST align with the {p_label.upper()} investment philosophy.
Factor weighting, position sizing, and stock selection must all reflect this persona.
{"Prefer gradual position changes; high turnover is discouraged for this persona." if p_turn < 0.30 else ""}
{"Active rebalancing is consistent with this persona; larger position changes are appropriate." if p_turn > 0.70 else ""}

"""

    execution_block = ""
    if execution_context:
        from services.optimizer.execution_penalty import build_execution_prompt_block
        execution_block = build_execution_prompt_block(execution_context)

    timing_challenge_block = """[TIMING AWARENESS — CHALLENGER]
Each symbol carries timing_score and execution_priority.
Challenge BUY/ACCUMULATE recommendations where execution_priority=DEFER or timing_score<40.
Add to disagreements[]: "TIMING_CONCERN: [SYM] poor entry timing (ts=[N], priority=DEFER) — waiting 2-4 weeks may improve entry."
Timing does not invalidate a fundamentally attractive stock — document the concern, do not block.

"""

    # TEMP DEBUG — cash data-flow trace (2026-07-03), remove after cash_pct bug confirmed
    _invested_value = sum(i.get("market_value", 0) for i in pc)
    logger.info(
        "[CASH_TRACE stage=3_L2_PROMPT] portfolio_value=%.2f invested_value=%.2f "
        "available_cash=%.2f cash_pct=%.4f%% policy_context_present=%s",
        total_value, _invested_value, cash_balance,
        (cash_balance / total_value * 100) if total_value else 0.0,
        bool(policy_context),
    )

    return f"""You are an independent portfolio reviewer.
{policy_block}{regime_block}{strategy_block}{t1_breach_note}{execution_block}{timing_challenge_block}{role_line}The Strategist (Layer 1) proposed:
- Priority: {l1_priority}
- Swaps: {json.dumps(l1_swaps, indent=2)}
- Top watchlist picks: {l1_top_buys}
- Sector flags: {l1_flags}

Full portfolio data for your analysis:
{json.dumps(pc, indent=2)}

Full watchlist for your analysis:
{json.dumps(wc, indent=2)}

Total portfolio value: {total_value:.0f}, Cash balance: {cash_balance:.0f}
Thai stocks end in .BK.

STABILIZATION PHILOSOPHY:
Unnecessary portfolio churn destroys value through transaction costs, tax drag, and operational complexity.

BEFORE proposing any rebalancing, apply this 3-step discipline:
1. DRIFT TEST: Is any allocation change < 3%? If yes, suppress it — noise, not signal.
2. CONVICTION TEST: Does the proposed change have a clear, measurable benefit (10+ score advantage or breach repair)?
3. COST TEST: Will the expected portfolio improvement exceed the ~0.15% trading cost per 1% NAV traded?

status="NO_ACTION" with rebalance_opportunity_score below 25 is STRONGLY ENCOURAGED when:
- All positions are within 3% of their natural weight (drift tolerance band)
- No watchlist candidate has a compelling 10+ score advantage over existing holdings
- No policy violations or sector concentration breaches exist
- Market conditions are uncertain or data is insufficient to justify rebalancing

PREFER large, high-conviction changes over many small adjustments.
A portfolio with 2 targeted swaps beats one with 6 micro-adjustments.

score guide: 0-25=no action needed, 26-45=minor optimization, 46-70=moderate opportunity, 71-100=strong opportunity.
no_action_reason enum (use null if status=REBALANCE):
  WELL_BALANCED | LOW_CONFIDENCE | HIGH_DISAGREEMENT | CONSTRAINT_BLOCKED | MARKET_UNCERTAINTY | INSUFFICIENT_EDGE

Build a complete capital allocation plan. Challenge or confirm the Strategist's swaps.

OUTPUT CONTRACT — this JSON is read by software, not a person; a separate step writes the human-readable
report later. Do not spend output tokens on prose. Follow this priority order if you are running low on
output budget: (1) allocations for existing holdings and BUY/ACCUMULATE/REDUCE/SELL decisions, (2) risk/
constraint-violation notes, (3) portfolio_assessment, (4) blocked_opportunities, (5) watchlist WATCH rows,
(6) any optional explanation. Never drop an allocation row to make room for longer text.

ALLOCATIONS ARRAY:
- Include every existing portfolio holding exactly once, with its action (ACCUMULATE|BUY|HOLD|REDUCE|SELL|WATCH).
- Include a watchlist symbol only if you assign it BUY or ACCUMULATE, OR it is one of your top few WATCH-worthy
  candidates with a specific reason (max 5 WATCH rows total). Do not add a row for every watchlist symbol —
  omit ones with no actionable signal completely.
- Weights are FLAT PERCENTAGES (10.0 = 10% of portfolio), not monetary amounts.
- Omit current weight — the backend already has it; send only the target.
- "r" = one reason, under 20 words. State each idea once — do not repeat it in "r", disagreements, and
  portfolio_assessment.

If a watchlist symbol with BUY/ACCUMULATE signal was evaluated but rejected (sector limit, cash constraint,
portfolio count cap), list it in blocked_opportunities — but only the highest-priority rejections, max 5.
Keep each "reason" under 10 words (e.g. "sector_limit_exceeded").

disagreements[]: only material disagreements with Layer 1 (wrong signal, missed breach, constraint conflict).
Skip informational observations. Max 5 entries, each under 20 words.

portfolio_assessment: 2-3 sentences max — a decision summary, not an essay.

Return JSON only. No markdown fences, no prose outside the JSON.

{{
  "status": "REBALANCE|NO_ACTION",
  "rebalance_opportunity_score": 50,
  "no_action_reason": "WELL_BALANCED|LOW_CONFIDENCE|HIGH_DISAGREEMENT|CONSTRAINT_BLOCKED|MARKET_UNCERTAINTY|INSUFFICIENT_EDGE|null",
  "no_action_summary": "<20 words, null if REBALANCE",
  "blocked_opportunities": [{{"symbol":"X","signal":"BUY","reason":"sector_limit_exceeded|insufficient_cash|portfolio_count_cap"}}],
  "agrees_with_layer1": true,
  "disagreements": ["<20 words each"],
  "portfolio_assessment": "2-3 sentences",
  "cash_balance_target": 0.0,
  "allocations": [
    {{"s":"X","tw":0.0,"sig":"BUY|ACCUMULATE|HOLD|REDUCE|SELL|WATCH","r":"<20 words"}}
  ]
}}"""


def _layer3_prompt(
    l1: dict,
    l2: dict,
    role: str = "",
    max_sector_pct: int = 40,
    persona_context: dict | None = None,
    policy_context: dict | None = None,
    effective_envelope: "_EffectiveEnvelope | None" = None,
    t1_breach_note: str = "",
) -> str:
    role_line = f"Your role: {role}\n\n" if role else ""
    l1_swaps    = l1.get("swap_suggestions", l1.get("swaps", []))[:4]
    l1_priority = l1.get("priority", "balanced")
    l2_allocs   = l2.get("allocations", l2.get("target_allocations", []))

    # Use resolved position cap for CRITICAL threshold — eliminates hardcoded 30% magic number
    if effective_envelope is not None:
        resolved_max_pos    = effective_envelope.effective_single_position_pct
        resolved_sector_cap = int(effective_envelope.global_sector_cap.effective)
    elif policy_context:
        hc = policy_context.get("hard_constraints", {})
        resolved_max_pos    = float(hc.get("max_single_position_pct", 22.0))
        resolved_sector_cap = int(hc.get("max_sector_pct", max_sector_pct))
    else:
        resolved_max_pos    = 30.0   # legacy: was hardcoded
        resolved_sector_cap = max_sector_pct

    # CRITICAL threshold: any position > resolved max + 8pp buffer, or resolved position cap + 8pp
    critical_pos_threshold = min(30.0, resolved_max_pos + max(5.0, resolved_max_pos * 0.25))

    persona_note = ""
    if persona_context:
        p_label = persona_context.get("persona_label", "Balanced")
        p_turn  = persona_context.get("turnover_tolerance", 0.5)
        p_vol   = persona_context.get("volatility_tolerance", 0.5)
        persona_note = (
            f"\nPersona Policy: {p_label.upper()} "
            f"(turnover tolerance: {int(p_turn*100)}%, volatility tolerance: {int(p_vol*100)}%)\n"
            "Flag any risk that conflicts with this persona's policy constraints.\n"
        )

    policy_note = ""
    if policy_context:
        hc = policy_context.get("hard_constraints", {})
        bias = policy_context.get("deployment_bias", "SELECTIVE")
        policy_note = (
            f"\nActive Policy Governance ({bias} mode — strictness: {policy_context.get('strictness_level','NORMAL')}):\n"
            f"  Cash mandate: ≥{hc.get('min_cash_pct', 5):.0f}%  "
            f"  Max position: {hc.get('max_single_position_pct', 22):.0f}%  "
            f"  Max sector: {hc.get('max_sector_pct', 40):.0f}%\n"
            "Flag POLICY_VIOLATION for cash < mandate, CONCENTRATION_BREACH for position > cap,\n"
            "OVER_AGGRESSION for excessive buys in defensive mode, REGIME_MISMATCH for emergency violations.\n"
        )

    high_pos_threshold = round(resolved_max_pos * 0.85, 1)  # HIGH = 85–100% of cap

    timing_risk_block = """[TIMING RISK ASSESSMENT — Phase 4C.6H]
Flag MEDIUM severity when a new BUY or ACCUMULATE position has execution_priority=DEFER or timing_score<40.
Use: {"symbol":"X","issue":"Poor entry timing (ts=[N], priority=DEFER) for new position","severity":"MEDIUM"}
Do NOT escalate to HIGH or CRITICAL for timing alone — timing cautions, it does not block.

"""

    return f"""{t1_breach_note}You are a portfolio risk auditor.
{timing_risk_block}{policy_note}{persona_note}{role_line}Evaluate both allocation proposals for concentration risk and soundness.

Layer 1 (Strategist):
Priority: {l1_priority}
Proposed swaps: {json.dumps(l1_swaps, indent=2)}

Layer 2 (Challenger):
Agrees: {l2.get("agrees_with_layer1", True)}
Disagreements: {json.dumps(l2.get("disagreements", []))}
Allocations: {json.dumps(l2_allocs, indent=2)}

Check for (use exact resolved severity thresholds — derived from active policy, not hardcoded):
- CRITICAL : sector > {resolved_sector_cap}% OR single stock > {critical_pos_threshold:.0f}% OR SELL signal kept in portfolio
- HIGH     : single stock {high_pos_threshold:.0f}–{critical_pos_threshold:.0f}% OR weak fundamentals on large position
- MEDIUM   : sector {int(resolved_sector_cap * 0.6)}–{int(resolved_sector_cap * 0.8)}% of limit OR conflicting allocation math
- LOW      : minor concentration risk, suboptimal but acceptable

Only flag positions that actually cross a threshold above — do not add a LOW-severity row for every position that
is merely fine. Max 8 risk_flags, "issue" under 15 words each. "auditor_notes" is a 1-2 sentence verdict — do not
restate the risk_flags issue text there.

Return JSON only. No markdown fences.

{{
  "risk_flags": [{{"symbol":"...","issue":"...","severity":"LOW|MEDIUM|HIGH|CRITICAL"}}],
  "safer_choice": "layer1|layer2|neither",
  "final_risk_level": "low|medium|high",
  "auditor_notes": "1-2 sentences."
}}"""


def _fallback_prompt(
    pc: list[dict],
    wc: list[dict],
    sell_forced: list[str],
    locked: list[str],
    max_stocks: int,
    max_sector_pct: int,
    total_value: float,
    cash_balance: float,
) -> str:
    return f"""You are an emergency portfolio analyst. The multi-layer optimizer pipeline failed.
Produce a complete, compliant capital allocation plan in a single response.

Portfolio holdings (current): {json.dumps(pc, indent=2)}
Watchlist candidates: {json.dumps(wc, indent=2)}
Forced exits (SELL signal): {sell_forced or "none"}
Locked positions (no swap): {locked or "none"}
Max portfolio stocks: {max_stocks}
Max sector weight: {max_sector_pct}%
Total portfolio value: {total_value:.0f}, Cash balance: {cash_balance:.0f}

HARD RULES — you MUST follow all of these:
1. Forced exit symbols MUST appear with action=SELL and target_weight=0.0
2. Locked symbols MUST appear with action=HOLD and unchanged target_weight
3. Total unique stocks after rebalancing (HOLD/BUY/ACCUMULATE/REDUCE combined) MUST NOT exceed {max_stocks}
4. No single sector may exceed {max_sector_pct}% weight
5. target_weight values are FLAT PERCENTAGES (10.0 = 10% of portfolio), NOT monetary amounts
6. Every existing portfolio holding must appear in allocations with an explicit action

OUTPUT CONTRACT — this JSON is read by software; do not spend output tokens on prose. Watchlist symbols you are
not recommending (no BUY/ACCUMULATE) do NOT need an allocations row — omit them, except up to 5 WATCH rows for
your top-ranked candidates. "r"/"reason" is one line, under 20 words. blocked_opportunities and risk_flags: only
the highest-priority items, max 5 each. Never drop an existing-holding allocation row to make room for text.

Return ONLY valid JSON without markdown fences:
{{
  "status": "REBALANCE|NO_ACTION",
  "rebalance_opportunity_score": 50,
  "no_action_reason": "WELL_BALANCED|LOW_CONFIDENCE|HIGH_DISAGREEMENT|CONSTRAINT_BLOCKED|MARKET_UNCERTAINTY|INSUFFICIENT_EDGE|null",
  "no_action_summary": "<20 words, null if REBALANCE",
  "blocked_opportunities": [{{"symbol":"X","signal":"BUY","reason":"sector_limit_exceeded|insufficient_cash|portfolio_count_cap"}}],
  "portfolio_assessment": "1-2 sentence summary of the plan",
  "cash_balance_target": 5.0,
  "allocations": [
    {{"s":"X","tw":0.0,"sig":"BUY|ACCUMULATE|HOLD|REDUCE|SELL|WATCH","r":"<20 words"}}
  ],
  "risk_flags": [{{"symbol":"...","issue":"<15 words","severity":"LOW|MEDIUM|HIGH|CRITICAL"}}],
  "final_risk_level": "low|medium|high|critical",
  "auditor_notes": "brief compliance note"
}}"""


def _run_single_shot_fallback(
    pc: list[dict],
    wc: list[dict],
    sell_forced: list[str],
    locked: list[str],
    portfolio_data: list[dict],
    current_sector_weights: dict,
    pc_map: dict[str, float],
    max_stocks: int,
    max_sector_pct: int,
    sector_limits: dict | None,
    total_value: float,
    cash_balance: float,
    fallback_provider: str,
    fallback_model: str,
    portfolio_name: str,
    portfolio_count: int,
    max_reached: bool,
) -> dict:
    """Single-shot emergency fallback when the 3-layer pipeline fails completely."""
    score_map = _build_score_context_map(pc, wc)
    prompt = _fallback_prompt(pc, wc, sell_forced, locked, max_stocks, max_sector_pct, total_value, cash_balance)
    raw = call_ai(
        prompt, fallback_provider, fallback_model, max_tokens=4096,
        usage_operation="optimize", usage_layer="fallback",
    )
    fb_latency_ms = raw["latency_ms"]
    result = safe_parse_json(raw["text"])

    raw_allocs = result.pop("allocations", None) or []
    allocations = _normalize_allocations(raw_allocs, pc_map, score_map)
    for a in allocations:
        a["estimated_amount"] = round((a["allocation_change_percent"] / 100) * total_value)

    locked_set = set(locked)
    alloc_map: dict[str, dict] = {a["symbol"]: a for a in allocations}
    for sym in sell_forced:
        if sym in alloc_map:
            alloc_map[sym]["action"] = "SELL"
            alloc_map[sym]["target_weight"] = 0.0
        else:
            cur_w = pc_map.get(sym, 0.0)
            alloc_map[sym] = {
                "symbol": sym, "current_weight": cur_w, "target_weight": 0.0,
                "action": "SELL", "allocation_change_percent": round(-cur_w, 2),
                "estimated_amount": 0, "reason": "Forced exit: SELL signal.",
            }
    for sym in locked_set:
        if sym in alloc_map and alloc_map[sym].get("action") not in ("HOLD", "WATCH"):
            alloc_map[sym]["action"] = "HOLD"
            alloc_map[sym]["target_weight"] = alloc_map[sym].get("current_weight", 0.0)
            alloc_map[sym]["allocation_change_percent"] = 0.0

    final_allocations = list(alloc_map.values())
    for a in final_allocations:
        a["allocation_change_percent"] = round(a["target_weight"] - a["current_weight"], 2)
        a["estimated_amount"] = round((a["allocation_change_percent"] / 100) * total_value)
    _snap_neutral_actions(final_allocations)

    swap_suggestions = _derive_swap_suggestions(final_allocations, sell_forced, locked)
    projected_sector_weights = calculate_projected_sector_weights_from_allocations(
        portfolio_data, final_allocations, total_value
    )
    sector_warnings = _compute_sector_warnings(
        current_sector_weights, projected_sector_weights, sector_limits, max_sector_pct
    )

    buy_symbols = [a["symbol"] for a in final_allocations if a.get("action") in ("BUY", "ACCUMULATE")]
    watchlist_ranking = _rebuild_watchlist_ranking(buy_symbols, wc)

    portfolio_assessment = result.get("portfolio_assessment", "Emergency fallback analysis.")
    risk_flags = result.get("risk_flags", [])
    final_risk_level = result.get("final_risk_level", "medium")
    auditor_notes = result.get("auditor_notes", "Fallback mode — single-shot analysis.")
    fb_tag = f"[FALLBACK:{fallback_provider}/{fallback_model}]"

    xai_status            = result.get("status", "REBALANCE")
    xai_score             = int(result.get("rebalance_opportunity_score") or 50)
    xai_no_action_reason  = result.get("no_action_reason")
    xai_no_action_summary = result.get("no_action_summary")
    xai_blocked           = result.get("blocked_opportunities", [])

    consensus = {
        "consensus_type":             "WEAK_CONSENSUS",
        "consensus_strength_score":   20,
        "strategist_alignment_score": 20,
        "risk_alignment_score":       50,
        "disagreement_reasons":       [],
        "refinement_summary":         "Emergency fallback mode — single-shot analysis, review allocations manually.",
        "agrees":             True,
        "consensus_decision": "REBALANCE",
        "confidence":         "low",
        "recommended":        "fallback",
        "final_risk_level":   "medium",
        "risk_flag_count":    len(risk_flags),
        "recommended_action": (
            f"{fb_tag} Pipeline recovered via emergency single-shot analysis. "
            "Review allocations manually before acting."
        ),
    }

    return {
        "portfolio_name": portfolio_name,
        "status": xai_status,
        "rebalance_opportunity_score": xai_score,
        "no_action_reason": xai_no_action_reason,
        "no_action_summary": xai_no_action_summary,
        "blocked_opportunities": xai_blocked,
        "portfolio_assessment": f"{fb_tag} {portfolio_assessment}",
        "optimization_notes": consensus["recommended_action"],
        "target_allocations": final_allocations,
        "target_cash_weight": float(result.get("cash_balance_target", 0.0)),
        "portfolio_turnover_percent": 0.0,
        "swap_suggestions": swap_suggestions,
        "watchlist_ranking": watchlist_ranking,
        "portfolio_count": portfolio_count,
        "max_reached": max_reached,
        "max_stocks": max_stocks,
        "cash_balance": cash_balance,
        "total_value": round(total_value, 2),
        "ai_provider": fallback_provider,
        "ai_model": fallback_model,
        "current_sector_weights": current_sector_weights,
        "projected_sector_weights": projected_sector_weights,
        "sector_warnings": sector_warnings,
        "layer1_latency_ms": 0,
        "layer2_latency_ms": 0,
        "layer3_latency_ms": fb_latency_ms,
        "total_latency_ms": fb_latency_ms,
        "layer1_result": {
            "provider": fallback_provider, "model": fallback_model, "name": "Fallback",
            "error": "Pipeline failed — emergency fallback activated",
            "swap_suggestions": [], "top_buys": [], "sector_flags": [], "priority": "",
        },
        "layer2_result": {
            "provider": fallback_provider, "model": fallback_model, "name": "Fallback",
            "target_allocations": final_allocations, "portfolio_assessment": portfolio_assessment,
            "agrees_with_layer1": True, "disagreements": [],
        },
        "layer3_result": {
            "provider": fallback_provider, "model": fallback_model, "name": "Fallback",
            "risk_flags": risk_flags, "safer_choice": "fallback",
            "final_risk_level": final_risk_level, "auditor_notes": auditor_notes,
        },
        "consensus": consensus,
        "fallback_mode": True,
    }


# ─── L1 minimal-prompt retry helper ──────────────────────────────────────────

def _retry_l1_with_schema(
    c_pc: list[dict],
    c_wc: list[dict],
    sell_forced: list[str],
    swap_eligible: list[str],
    l1_cfg: dict,
) -> dict:
    """Single-shot L1 retry with a stripped-down prompt after an initial parse failure.

    Called only when the full L1 prompt produced unparseable output.  The goal is
    to get *something* structurally valid so L2/L3 can still run with real signal.
    """
    minimal_prompt = (
        "You are a portfolio strategist. Return ONLY a valid JSON object — "
        "no markdown, no prose, just the JSON.\n\n"
        f"Current holdings: {json.dumps(c_pc)}\n"
        f"Watchlist candidates: {json.dumps(c_wc)}\n"
        f"Swap-eligible: {swap_eligible or 'none'}\n"
        f"Forced exits: {sell_forced or 'none'}\n\n"
        "Propose up to 3 swap / reduce actions and rank the top watchlist buys.\n"
        "Required output (fill in real values, \"r\" = reason under 12 words):\n"
        '{"swaps":[{"sell":"SYM_OR_NULL","buy":"SYM_OR_NULL","score_delta":0.0,'
        '"sector":"Other","type":"SWAP","r":"<12 words"}],"top_buys":["SYM"],'
        '"sector_flags":[],"priority":"balanced"}'
    )
    raw = call_ai(
        minimal_prompt,
        l1_cfg["provider"],
        l1_cfg["model"],
        max_tokens=2048,
        use_schema=True,
        usage_operation="optimize",
        usage_layer="layer1_retry",
    )
    return safe_parse_json(raw["text"])


# ─── Public API ───────────────────────────────────────────────────────────────

def run_optimizer(
    portfolio_data: list[dict],
    watchlist_data: list[dict],
    portfolio_name: str,
    portfolio_count: int = 0,
    max_reached: bool = False,
    provider: str = "anthropic",
    model: str = "claude-sonnet-4-6",
    max_stocks: int = 12,
    max_sector_pct: int = 40,
    cash_balance: float = 0.0,
) -> dict:
    """Single-model optimizer (legacy path)."""
    portfolio_data = _compute_portfolio_weights(portfolio_data)

    sell_forced   = [p["symbol"] for p in portfolio_data if p.get("signal") == "SELL"]
    locked        = [p["symbol"] for p in portfolio_data if not p.get("allow_swap", True)]
    swap_eligible = [p["symbol"] for p in portfolio_data if p.get("allow_swap", True) and p.get("signal") != "SELL"]
    pc = _compact_p(portfolio_data)
    wc = _compact_w(watchlist_data)
    score_map = _build_score_context_map(pc, wc)
    c_pc, c_wc = _compress_for_layer1(pc, wc)
    prompt = _layer1_prompt(
        c_pc, c_wc, sell_forced, swap_eligible,
        max_sector_pct=max_sector_pct, max_stocks=max_stocks, current_count=portfolio_count,
    )
    logger.info(f"L1 prompt chars: {len(prompt)}")
    ai_result = call_ai(
        prompt, provider, model, max_tokens=2048,
        use_schema=True,
        usage_operation="optimize", usage_layer="layer1",
    )
    result = safe_parse_json(ai_result["text"])
    result["portfolio_name"] = portfolio_name
    result["portfolio_count"] = portfolio_count
    result["max_reached"] = max_reached
    result["max_stocks"] = max_stocks
    result["swap_suggestions"] = _postprocess_swaps(
        _normalize_l1_swaps(result.get("swaps", []), score_map), sell_forced, locked
    )
    result["watchlist_ranking"] = _rebuild_watchlist_ranking(result.get("top_buys", []), wc)
    return result


def run_layered_optimizer(
    portfolio_data: list[dict],
    watchlist_data: list[dict],
    portfolio_name: str,
    portfolio_count: int = 0,
    max_reached: bool = False,
    layers: dict | None = None,
    max_stocks: int = 12,
    max_sector_pct: int = 40,
    sector_limits: dict | None = None,
    cash_balance: float = 0.0,
    fallback_provider: str = "anthropic",
    fallback_model: str = "claude-sonnet-4-6",
    persona_context: dict | None = None,
    regime_context: dict | None = None,
    policy_context: dict | None = None,
    effective_envelope: "_EffectiveEnvelope | None" = None,
    execution_context: dict | None = None,
    on_stage: Callable[[str], None] | None = None,
) -> dict:
    """3-layer Dynamic Capital Allocation Engine with global single-shot fallback.

    on_stage: optional presentation-only progress callback (Phase 4C.1) invoked
    with a stage key before each AI layer call. Failures inside the callback are
    swallowed — it can never affect optimizer behavior.
    """
    if layers is None:
        layers = _DEFAULT_LAYERS

    l1_cfg = {**_DEFAULT_LAYERS["layer1"], **layers.get("layer1", {})}
    l2_cfg = {**_DEFAULT_LAYERS["layer2"], **layers.get("layer2", {})}
    l3_cfg = {**_DEFAULT_LAYERS["layer3"], **layers.get("layer3", {})}

    sell_forced   = [p["symbol"] for p in portfolio_data if p.get("signal") == "SELL"]
    locked        = [p["symbol"] for p in portfolio_data if not p.get("allow_swap", True)]

    portfolio_data = _compute_portfolio_weights(portfolio_data)
    total_equity = sum(i.get("market_value", 0) for i in portfolio_data)
    total_value = total_equity + cash_balance

    # TEMP DEBUG — cash data-flow trace (2026-07-03), remove after cash_pct bug confirmed
    logger.info(
        "[CASH_TRACE stage=2_OPTIMIZER_CONTEXT] portfolio_value=%.2f invested_value=%.2f "
        "available_cash=%.2f cash_pct=%.4f%%",
        total_value, total_equity, cash_balance,
        (cash_balance / total_value * 100) if total_value else 0.0,
    )

    # Authoritative current weights from real portfolio data (not AI-reported)
    pc_map: dict[str, float] = {p["symbol"]: p.get("weight_pct", 0.0) for p in portfolio_data}

    swap_eligible = [p["symbol"] for p in portfolio_data if p.get("allow_swap", True) and p.get("signal") != "SELL"]
    pc = _compact_p(portfolio_data)
    wc = _compact_w(watchlist_data)
    score_map = _build_score_context_map(pc, wc)
    c_pc, c_wc = _compress_for_layer1(pc, wc)

    current_sector_weights = calculate_current_sector_weights(portfolio_data)

    # ── Phase 3B.6 — Tier 1 breach detection for dynamic turnover relaxation ──
    # Detect concentration breaches in the CURRENT portfolio before AI layers run.
    # When breaches exist, Tier 3 turnover constraints are relaxed so they cannot
    # block the remediation that Tier 1 demands.
    _t1_severity: str = "NONE"
    _t1_reason:   str = ""
    _base_turn_cap:    float = 0.0
    _relaxed_turn_cap: float | None = None

    if policy_context:
        _pe_for_t1 = _make_envelope_from_dict(policy_context)
        _base_turn_cap = _pe_for_t1.hard_constraints.max_turnover_pct
        _t1_severity, _t1_reason = compute_concentration_breach_severity(
            portfolio_data,
            _pe_for_t1.hard_constraints.max_single_position_pct,
            _pe_for_t1.hard_constraints.max_sector_pct,
            dict(policy_context.get("resolved_sector_limits") or {}),
        )
        _relaxed_turn_cap = get_relaxed_turnover_cap(_base_turn_cap, _t1_severity)
        if _t1_severity != "NONE":
            logger.info(
                "[TIER1_RELAX] severity=%s base_turn=%.0f%% relaxed=%.0f%% reason=%s",
                _t1_severity, _base_turn_cap, _relaxed_turn_cap, _t1_reason,
            )

    # Prompt note injected into all 3 layers when Tier 1 breaches are present
    _t1_note = ""
    if _t1_severity != "NONE" and _relaxed_turn_cap is not None and _base_turn_cap > 0:
        _mult_pct = round((_relaxed_turn_cap / _base_turn_cap - 1) * 100)
        _t1_note = (
            f"[CONSTRAINT HIERARCHY — CONCENTRATION PRIORITY ACTIVE]\n"
            f"TIER 1 BREACH DETECTED ({_t1_severity}): {_t1_reason}\n"
            f"PRIORITY RULE: Eliminating dangerous concentration risk takes absolute precedence "
            f"over Tier 3 turnover efficiency constraints.\n"
            f"Effective turnover ceiling this run: {_relaxed_turn_cap:.0f}% "
            f"(base {_base_turn_cap:.0f}% + {_mult_pct}% relaxation for Tier 1 remediation).\n"
            f"concentration reduction > turnover efficiency | "
            f"safety remediation > optimization friction\n"
            f"\n"
            f"AUTHORIZED EXCEPTION SEMANTICS — MANDATORY FOR ALL AGENTS:\n"
            f"'Turnover Relaxation Active' is a SAFE AUTHORIZED STATE, NOT a failure condition.\n"
            f"The system has mathematically pre-approved this temporary turnover overshoot to eliminate\n"
            f"a more dangerous Tier 1 concentration risk. This is controlled, policy-compliant behavior.\n"
            f"\n"
            f"SAFE AUTHORIZED STATES (do NOT escalate to REVIEW / flag HIGH or CRITICAL):\n"
            f"  • Turnover Relaxation Active    — controlled Tier 3 flex for Tier 1 remediation\n"
            f"  • Temporary Cash Deployment Override — transient, for forced exits\n"
            f"  • Controlled Sector Rotation    — rebalancing within resolved sector limits\n"
            f"\n"
            f"DANGEROUS FAILURE STATES (flag HIGH/CRITICAL, warrant REVIEW or REJECT):\n"
            f"  • Concentration breach UNRESOLVED after proposed rebalancing\n"
            f"  • Contradictory allocation logic (same stock BUY + SELL simultaneously)\n"
            f"  • Unauthorized leverage or risk escalation beyond policy envelope\n"
            f"  • Policy envelope violations WITHOUT documented system authorization\n"
            f"\n"
            f"MANDATORY DECISION RULE:\n"
            f"  IF (a) concentration violations are materially reduced by the proposed plan, AND\n"
            f"     (b) portfolio diversification improves (fewer or smaller overweight positions), AND\n"
            f"     (c) the ONLY remaining concern is an authorized turnover relaxation buffer:\n"
            f"  THEN → L2 MUST output status=REBALANCE (not NO_ACTION, not REVIEW).\n"
            f"          L3 MUST output final_risk_level=low or medium (not high).\n"
            f"  Authorized operational relaxations confirm the system is working correctly.\n\n"
        )

    try:
        # Layer 1 — Strategist
        _emit_stage(on_stage, "LAYER1_PROPOSAL")
        l1_parse_failed = False
        try:
            l1_prompt = _layer1_prompt(
                c_pc, c_wc, sell_forced, swap_eligible,
                max_sector_pct=max_sector_pct, sector_limits=sector_limits,
                max_stocks=max_stocks, current_count=portfolio_count,
                persona_context=persona_context,
                regime_context=regime_context,
                policy_context=policy_context,
                effective_envelope=effective_envelope,
                t1_breach_note=_t1_note,
                execution_context=execution_context,
            )
            logger.info(f"L1 prompt chars: {len(l1_prompt)}")
            l1_raw = call_ai(
                l1_prompt, l1_cfg["provider"], l1_cfg["model"], max_tokens=4096,
                use_schema=True,
                usage_operation="optimize", usage_layer="layer1",
            )
            l1_latency_ms = l1_raw["latency_ms"]
            raw_l1_text = l1_raw.get("text", "")
            logger.info(
                "[L1_DEBUG] provider=%s model=%s raw_text_len=%d latency_ms=%d",
                l1_cfg["provider"], l1_cfg["model"], len(raw_l1_text), l1_latency_ms,
            )
            l1_result = safe_parse_json(raw_l1_text)
            l1_result["swap_suggestions"] = _postprocess_swaps(
                _normalize_l1_swaps(l1_result.get("swaps", []), score_map), sell_forced, locked
            )
            logger.info(
                "[L1_DEBUG] parsed: swaps_count=%d swap_suggestions_count=%d top_buys=%s priority=%s",
                len(l1_result.get("swaps", [])),
                len(l1_result.get("swap_suggestions", [])),
                l1_result.get("top_buys", []),
                l1_result.get("priority"),
            )
        except Exception as e:
            logger.error("[L1_DEBUG] parse_error=%s", e)
            # Single quiet retry with a minimal stripped-down prompt before giving up
            try:
                l1_result = _retry_l1_with_schema(c_pc, c_wc, sell_forced, swap_eligible, l1_cfg)
                l1_result["swap_suggestions"] = _postprocess_swaps(
                    _normalize_l1_swaps(l1_result.get("swaps", []), score_map), sell_forced, locked
                )
                l1_parse_failed = False
                logger.info("[L1_RETRY] recovered successfully after minimal-prompt retry")
            except Exception as retry_err:
                logger.error("[L1_RETRY] also failed: %s", retry_err)
                l1_parse_failed = True
                l1_result = {
                    "error": str(e), "swap_suggestions": [],
                    "top_buys": [], "sector_flags": [], "priority": "",
                }
                l1_latency_ms = 0

        # Layer 2 — Challenger
        _emit_stage(on_stage, "LAYER2_CHALLENGE")
        try:
            l2_raw = call_ai(
                _layer2_prompt(pc, wc, l1_result, l2_cfg.get("role", ""),
                               cash_balance=cash_balance, total_value=total_value,
                               persona_context=persona_context,
                               regime_context=regime_context,
                               policy_context=policy_context,
                               t1_breach_note=_t1_note,
                               execution_context=execution_context),
                l2_cfg["provider"], l2_cfg["model"], max_tokens=8192,
                usage_operation="optimize", usage_layer="layer2",
            )
            l2_latency_ms = l2_raw["latency_ms"]
            raw_l2_text = l2_raw.get("text", "")
            logger.info(
                "[L2_DEBUG] provider=%s model=%s raw_text_len=%d latency_ms=%d",
                l2_cfg["provider"], l2_cfg["model"], len(raw_l2_text), l2_latency_ms,
            )
            l2_result = safe_parse_json(raw_l2_text)
            # Fix: use None check so an explicitly-empty allocations:[] isn't dropped
            raw_allocs = l2_result.pop("allocations", None)
            if raw_allocs is None:
                raw_allocs = l2_result.pop("target_allocations", [])
            l2_allocs = _normalize_allocations(raw_allocs, pc_map, score_map)
            for a in l2_allocs:
                a["estimated_amount"] = round((a["allocation_change_percent"] / 100) * total_value)
            l2_result["target_allocations"] = l2_allocs
            if "portfolio_assessment" in l2_result and "summary" not in l2_result:
                l2_result["summary"] = l2_result["portfolio_assessment"]
            if "cash_balance_target" in l2_result and "target_cash_weight" not in l2_result:
                l2_result["target_cash_weight"] = l2_result["cash_balance_target"]
            # If L1 failed, L2 cannot meaningfully agree with it — mark disagreement
            if l1_parse_failed:
                l2_result["agrees_with_layer1"] = False
                l2_result.setdefault("disagreements", []).insert(
                    0, "L1_PARSE_FAILURE: Strategist output could not be parsed — treating as disagreement."
                )
                l2_result["strategist_parse_failed"] = True
            logger.info(
                "[L2_DEBUG] status=%s allocs_count=%d agrees_with_layer1=%s strategist_parse_failed=%s",
                l2_result.get("status"),
                len(l2_allocs),
                l2_result.get("agrees_with_layer1"),
                l2_result.get("strategist_parse_failed", False),
            )
        except Exception as e:
            logger.error("[L2_DEBUG] parse_error=%s", e)
            l2_result = {
                "error": str(e), "agrees_with_layer1": False,
                "disagreements": ["L2_PARSE_FAILURE: Challenger output could not be parsed."],
                "target_allocations": [],
            }
            l2_latency_ms = 0

        # Layer 3 — Risk Auditor
        _emit_stage(on_stage, "LAYER3_ARBITRATION")
        try:
            l3_raw = call_ai(
                _layer3_prompt(l1_result, l2_result, l3_cfg.get("role", ""), max_sector_pct=max_sector_pct,
                               persona_context=persona_context,
                               policy_context=policy_context,
                               effective_envelope=effective_envelope,
                               t1_breach_note=_t1_note),
                l3_cfg["provider"], l3_cfg["model"], max_tokens=2048,
                usage_operation="optimize", usage_layer="layer3",
            )
            l3_latency_ms = l3_raw["latency_ms"]
            l3_result = safe_parse_json(l3_raw["text"])
        except Exception as e:
            l3_result = {
                "error": str(e), "risk_flags": [],
                "safer_choice": "layer1", "final_risk_level": "medium", "auditor_notes": "",
            }
            l3_latency_ms = 0

        # If L2 produced no allocations all three layers failed — trigger global fallback
        if "error" in l2_result and not l2_result.get("target_allocations"):
            raise RuntimeError(
                f"L2 allocation plan empty after all layers attempted. L2 error: {l2_result.get('error')}"
            )

        consensus = _consensus_engine(l1_result, l2_result, l3_result)

        # ── Policy governance scoring (3B.4) ───────────────────────────────────
        # Populated after final_allocations are known; policy_context may be None.
        # We store placeholders now and fill them in below after constraint enforcement.
        _policy_scores_pending = bool(policy_context)

        # XAI metadata — extracted from L2 with safe defaults
        xai_status              = l2_result.get("status", "REBALANCE")
        xai_score               = int(l2_result.get("rebalance_opportunity_score") or 50)
        xai_no_action_reason    = l2_result.get("no_action_reason")
        xai_no_action_summary   = l2_result.get("no_action_summary")
        xai_blocked             = l2_result.get("blocked_opportunities", [])

        # Final allocations always come from L2 (L1 only produces swaps)
        final_allocations = l2_result.get("target_allocations", [])
        final_cash_weight = l2_result.get("target_cash_weight", 0.0)
        final_turnover    = l2_result.get("portfolio_turnover_percent", 0.0)
        final_summary     = l2_result.get("summary", l2_result.get("portfolio_assessment", ""))

        # Enforce constraints regardless of AI output
        locked_set = set(locked)
        alloc_map: dict[str, dict] = {a["symbol"]: a for a in final_allocations}
        for sym in sell_forced:
            if sym in alloc_map:
                alloc_map[sym]["action"] = "SELL"
                alloc_map[sym]["target_weight"] = 0.0
            else:
                cur_w = pc_map.get(sym, 0.0)
                alloc_map[sym] = {
                    "symbol": sym, "current_weight": cur_w, "target_weight": 0.0,
                    "action": "SELL", "allocation_change_percent": round(-cur_w, 2),
                    "estimated_amount": 0, "reason": "Forced exit: SELL signal.",
                }
        for sym in locked_set:
            if sym in alloc_map and alloc_map[sym].get("action") not in ("HOLD", "WATCH"):
                alloc_map[sym]["action"] = "HOLD"
                alloc_map[sym]["target_weight"] = alloc_map[sym].get("current_weight", 0.0)
                alloc_map[sym]["allocation_change_percent"] = 0.0

        final_allocations = list(alloc_map.values())

        # Recompute change% and THB amounts in Python — never trust AI-reported monetary values
        for a in final_allocations:
            a["allocation_change_percent"] = round(a["target_weight"] - a["current_weight"], 2)
            a["estimated_amount"] = round((a["allocation_change_percent"] / 100) * total_value)

        # ── Policy / Regime hard constraints (applied after AI output) ────────
        # When policy_context is available it supersedes the raw regime constraints
        # (policy_engine already synthesizes persona + regime into a single envelope).
        if policy_context:
            pc_hard       = policy_context.get("hard_constraints", {})
            min_cash_pct  = float(pc_hard.get("min_cash_pct", 5.0))
            max_pos_pct   = float(pc_hard.get("max_single_position_pct", 22.0))
            suppress_spec = bool(pc_hard.get("suppress_speculative", False))
            emergency     = bool(policy_context.get("emergency_override", False))

            # Emergency: convert all BUY/ACCUMULATE to HOLD
            if emergency:
                for a in final_allocations:
                    if a.get("action") in ("BUY", "ACCUMULATE"):
                        logger.info(
                            "[POLICY_EMERGENCY] freezing %s BUY→HOLD (emergency override)", a["symbol"]
                        )
                        a["action"]                   = "HOLD"
                        a["target_weight"]             = a.get("current_weight", 0.0)
                        a["allocation_change_percent"] = 0.0
                        a["estimated_amount"]          = 0

            # Cap BUY/ACCUMULATE target_weight at policy max position
            for a in final_allocations:
                if a.get("action") in ("BUY", "ACCUMULATE") and a.get("target_weight", 0) > max_pos_pct:
                    logger.info(
                        "[POLICY] capping %s target_weight %.1f→%.1f (bias=%s)",
                        a["symbol"], a["target_weight"], max_pos_pct,
                        policy_context.get("deployment_bias"),
                    )
                    a["target_weight"]             = max_pos_pct
                    a["allocation_change_percent"] = round(a["target_weight"] - a["current_weight"], 2)
                    a["estimated_amount"]          = round((a["allocation_change_percent"] / 100) * total_value)

            # Enforce minimum cash floor
            total_target  = sum(a.get("target_weight", 0) for a in final_allocations
                                if a.get("action") not in ("SELL",))
            cash_headroom = 100.0 - total_target
            if cash_headroom < min_cash_pct:
                deficit = min_cash_pct - cash_headroom
                buy_allocs = sorted(
                    [a for a in final_allocations if a.get("action") in ("BUY", "ACCUMULATE")],
                    key=lambda x: -x.get("target_weight", 0),
                )
                for a in buy_allocs:
                    if deficit <= 0:
                        break
                    trim            = min(a["target_weight"], deficit)
                    a["target_weight"]             = round(a["target_weight"] - trim, 2)
                    a["allocation_change_percent"] = round(a["target_weight"] - a["current_weight"], 2)
                    a["estimated_amount"]          = round((a["allocation_change_percent"] / 100) * total_value)
                    deficit -= trim
                logger.info(
                    "[POLICY] enforced min_cash=%.0f%% deployment=%s",
                    min_cash_pct, policy_context.get("deployment_bias"),
                )

        elif regime_context:
            # Fallback: legacy regime-only enforcement when no policy_context
            from services.analytics.regime_detector import get_regime_constraints
            rc = get_regime_constraints(regime_context.get("regime", "SIDEWAYS"))
            min_cash_pct  = rc["min_cash_pct"]
            max_pos_pct   = rc["max_single_position_pct"]

            for a in final_allocations:
                if a.get("action") in ("BUY", "ACCUMULATE") and a.get("target_weight", 0) > max_pos_pct:
                    a["target_weight"]             = max_pos_pct
                    a["allocation_change_percent"] = round(a["target_weight"] - a["current_weight"], 2)
                    a["estimated_amount"]          = round((a["allocation_change_percent"] / 100) * total_value)

            total_target  = sum(a.get("target_weight", 0) for a in final_allocations
                                if a.get("action") not in ("SELL",))
            cash_headroom = 100.0 - total_target
            if cash_headroom < min_cash_pct:
                deficit = min_cash_pct - cash_headroom
                buy_allocs = sorted(
                    [a for a in final_allocations if a.get("action") in ("BUY", "ACCUMULATE")],
                    key=lambda x: -x.get("target_weight", 0),
                )
                for a in buy_allocs:
                    if deficit <= 0:
                        break
                    trim                           = min(a["target_weight"], deficit)
                    a["target_weight"]             = round(a["target_weight"] - trim, 2)
                    a["allocation_change_percent"] = round(a["target_weight"] - a["current_weight"], 2)
                    a["estimated_amount"]          = round((a["allocation_change_percent"] / 100) * total_value)
                    deficit -= trim
                logger.info("[REGIME] enforced min_cash=%.0f%% regime=%s", min_cash_pct, regime_context.get("regime"))

        # ── Phase 3B.5 — Sector-level enforcement from resolved EffectiveEnvelope ──
        # Runs AFTER position/cash enforcement to ensure no sector exceeds its resolved limit.
        # This is a new enforcement step that operates on projected weights from target allocations.
        if effective_envelope is not None:
            # Build sector lookup from all available data (portfolio + watchlist)
            _all_sector_data = {d["symbol"]: normalize_sector(d.get("sector", "Other"))
                                for d in (portfolio_data + watchlist_data)}

            # Compute projected sector weights from current target allocations
            proj_sector: dict[str, float] = {}
            for a in final_allocations:
                if a.get("action") == "SELL":
                    continue
                sector = _all_sector_data.get(a.get("symbol", ""), "Other")
                proj_sector[sector] = proj_sector.get(sector, 0.0) + float(a.get("target_weight") or 0)

            # Enforce per-sector resolved limits
            for sector, proj_pct in proj_sector.items():
                limit = _effective_sector_cap(effective_envelope, sector)
                if proj_pct <= limit:
                    continue
                # Trim largest BUY/ACCUMULATE allocations in this sector until within limit
                excess = proj_pct - limit
                over_allocs = sorted(
                    [a for a in final_allocations
                     if _all_sector_data.get(a.get("symbol", ""), "Other") == sector
                     and a.get("action") in ("BUY", "ACCUMULATE")],
                    key=lambda x: -x.get("target_weight", 0),
                )
                for a in over_allocs:
                    if excess <= 0:
                        break
                    trim = min(a["target_weight"], excess)
                    a["target_weight"]             = round(a["target_weight"] - trim, 2)
                    a["allocation_change_percent"] = round(a["target_weight"] - a["current_weight"], 2)
                    a["estimated_amount"]          = round((a["allocation_change_percent"] / 100) * total_value)
                    excess -= trim
                logger.info(
                    "[SECTOR_ENFORCE] %s sector %.1f%% > %.1f%% resolved limit — trimmed",
                    sector, proj_pct, limit,
                )

        # ── Phase 3B.10 — Execution quality cap enforcement ──────────────────
        # Applies per-asset position caps for DR and illiquid assets.
        # This is a SOFT enforcement: reduces target_weight to the cap but never
        # hard-rejects the asset. Runs after all other constraint enforcement.
        if execution_context:
            per_sym_exec = execution_context.get("per_symbol", {})
            for a in final_allocations:
                if a.get("action") not in ("BUY", "ACCUMULATE"):
                    continue
                sym = a.get("symbol", "")
                sym_exec = per_sym_exec.get(sym, {})
                cap = sym_exec.get("position_cap_pct")   # None = no reduced cap
                if cap is not None and a.get("target_weight", 0) > cap:
                    logger.info(
                        "[EXEC_CAP] %s target_weight %.1f%% → %.1f%% (DR/illiquid cap)",
                        sym, a["target_weight"], cap,
                    )
                    a["target_weight"]             = round(cap, 2)
                    a["allocation_change_percent"] = round(a["target_weight"] - a["current_weight"], 2)
                    a["estimated_amount"]          = round((a["allocation_change_percent"] / 100) * total_value)
                    a["execution_capped"]          = True

        # Attach per-symbol execution metadata to allocations for frontend badge rendering
        if execution_context:
            per_sym_exec = execution_context.get("per_symbol", {})
            for a in final_allocations:
                sym = a.get("symbol", "")
                if sym in per_sym_exec:
                    a["execution_risk"]     = per_sym_exec[sym].get("execution_risk", "LOW")
                    a["execution_warnings"] = per_sym_exec[sym].get("execution_warnings", [])
                    a["asset_type"]         = per_sym_exec[sym].get("asset_type", "EQUITY")
                    a["slippage_est_pct"]   = per_sym_exec[sym].get("slippage_cost_est_pct")

        # ── Post-enforcement action label reconciliation ──────────────────────
        # Constraint passes (policy cap, cash floor, sector cap, DR exec cap) all
        # update target_weight + allocation_change_percent but never touch action.
        # A BUY/ACCUMULATE whose delta went negative is now a net REDUCE; fix it.
        for a in final_allocations:
            delta  = a.get("allocation_change_percent", 0)
            action = (a.get("action") or "HOLD").upper()
            if action in ("BUY", "ACCUMULATE") and delta < -1.0:
                a["action"] = "REDUCE"
                logger.info(
                    "[ACTION_RECONCILE] %s %s→REDUCE (delta=%.1f%% after constraint enforcement)",
                    a.get("symbol"), action, delta,
                )
            elif action in ("BUY", "ACCUMULATE") and delta <= 0:
                a["action"] = "HOLD"
                logger.info(
                    "[ACTION_RECONCILE] %s %s→HOLD (delta=%.1f%% suppressed to zero by constraints)",
                    a.get("symbol"), action, delta,
                )
            elif action == "REDUCE" and delta > 1.0:
                # Mirror case: REDUCE that became a net increase (rare but possible)
                a["action"] = "ACCUMULATE"
                logger.info(
                    "[ACTION_RECONCILE] %s REDUCE→ACCUMULATE (delta=%.1f%% after constraint enforcement)",
                    a.get("symbol"), delta,
                )

        _snap_neutral_actions(final_allocations)

        # Build sector_map for governance scoring (symbol → sector)
        _sector_map_for_scoring: dict[str, str] = {
            d["symbol"]: normalize_sector(d.get("sector", "Other"))
            for d in (portfolio_data + watchlist_data)
        } if effective_envelope is not None else {}

        # Defensive: auto-correct NO_ACTION when allocations contain real changes
        if xai_status == "NO_ACTION" and any(
            a.get("action") not in ("HOLD", "WATCH") or abs(a.get("allocation_change_percent", 0)) >= 1.0
            for a in final_allocations
        ):
            logger.warning(
                "[DEFENSIVE] status=NO_ACTION but %d allocations with changes — auto-correcting to REBALANCE",
                len(final_allocations),
            )
            xai_status = "REBALANCE"
            xai_no_action_reason = None
            xai_no_action_summary = None

        # ── Policy governance scores (fill in now that allocations are finalized) ─
        if _policy_scores_pending and policy_context:
            from services.optimizer.policy_engine import compute_policy_alignment_score, PolicyEnvelope
            pa_score, rc_score, rg_score, gov_flags, violation_details = compute_policy_alignment_score(
                final_allocations,
                _make_envelope_from_dict(policy_context),
                total_value,
                sector_map=_sector_map_for_scoring or None,
                effective_turnover_cap=_relaxed_turn_cap,
            )
            consensus["policy_alignment_score"]  = pa_score
            consensus["regime_compliance_score"] = rc_score
            consensus["risk_governance_score"]   = rg_score
            consensus["governance_flags"]        = gov_flags
            consensus["violation_details"]       = violation_details
            # Downgrade consensus strength when genuine governance flags are raised.
            # Authorized turnover expansions (Tier 1 relaxation active) are controlled
            # policy-compliant events — exclude them so authorized behavior isn't penalized.
            if gov_flags:
                penalizable = gov_flags if _t1_severity == "NONE" else [
                    f for f in gov_flags
                    if not any(kw in f.lower() for kw in ("turnover", "tier3_efficiency"))
                ]
                penalty = min(20, len(penalizable) * 6)
                if penalty > 0:
                    consensus["consensus_strength_score"] = max(
                        5, consensus.get("consensus_strength_score", 50) - penalty
                    )
                logger.info(
                    "[POLICY_GOV] flags=%d penalizable=%d strength_penalty=-%d t1_severity=%s",
                    len(gov_flags), len(penalizable), penalty, _t1_severity,
                )

        # Auto-generate summary when empty but allocations exist
        if not final_summary and final_allocations:
            action_counts: dict[str, int] = {}
            for a in final_allocations:
                act = a.get("action", "HOLD")
                action_counts[act] = action_counts.get(act, 0) + 1
            summary_parts = [f"{act}×{cnt}" for act, cnt in sorted(action_counts.items()) if act not in ("HOLD", "WATCH")]
            if summary_parts:
                final_summary = f"Proposed changes: {', '.join(summary_parts)} across {len(final_allocations)} positions."

        logger.info(
            "[PIPELINE_FINAL] status=%s allocs_count=%d summary_len=%d swap_suggestions_count_pre=%d",
            xai_status, len(final_allocations), len(final_summary or ""),
            len(l1_result.get("swap_suggestions", [])),
        )

        swap_suggestions = _derive_swap_suggestions(final_allocations, sell_forced, locked)
        projected_sector_weights = calculate_projected_sector_weights_from_allocations(
            portfolio_data, final_allocations, total_value
        )
        sector_warnings = _compute_sector_warnings(
            current_sector_weights, projected_sector_weights, sector_limits, max_sector_pct
        )

        total_latency_ms = l1_latency_ms + l2_latency_ms + l3_latency_ms
        buy_symbols = [a["symbol"] for a in final_allocations if a.get("action") in ("BUY", "ACCUMULATE")]
        watchlist_ranking = _rebuild_watchlist_ranking(buy_symbols, wc)

        persona_fields: dict = {}
        if persona_context:
            persona_fields = {
                "target_persona":         persona_context.get("persona"),
                "persona_label":          persona_context.get("persona_label"),
                "current_portfolio_dna":  persona_context.get("portfolio_dna"),
                "style_drift_score":      persona_context.get("drift_score"),
                "style_drift_severity":   persona_context.get("drift_severity"),
                "factor_alignment_score": persona_context.get("factor_alignment_score"),
                "factor_drift":           persona_context.get("factor_drift"),
                "rebalance_urgency":      persona_context.get("rebalance_urgency"),
            }

        # Strip prompt_block from policy_context before surfacing to API (it's large)
        active_policy_out: dict | None = None
        if policy_context:
            active_policy_out = {k: v for k, v in policy_context.items() if k != "prompt_block"}
            active_policy_out["policy_alignment_score"]  = consensus.get("policy_alignment_score")
            active_policy_out["regime_compliance_score"] = consensus.get("regime_compliance_score")
            active_policy_out["risk_governance_score"]   = consensus.get("risk_governance_score")
            active_policy_out["governance_flags"]        = consensus.get("governance_flags", [])
            active_policy_out["violation_details"]       = consensus.get("violation_details", [])
            # Phase 3B.6 — Tier 1 turnover relaxation metadata
            active_policy_out["turnover_relaxation_active"] = _t1_severity != "NONE"
            active_policy_out["turnover_relaxation_reason"] = _t1_reason if _t1_severity != "NONE" else None
            active_policy_out["relaxed_turnover_cap"]       = _relaxed_turn_cap if _t1_severity != "NONE" else None

        return {
            "portfolio_name": portfolio_name,
            "status": xai_status,
            "rebalance_opportunity_score": xai_score,
            "no_action_reason": xai_no_action_reason,
            "no_action_summary": xai_no_action_summary,
            "blocked_opportunities": xai_blocked,
            "portfolio_assessment": final_summary,
            "optimization_notes": consensus["recommended_action"],
            "target_allocations": final_allocations,
            "target_cash_weight": final_cash_weight,
            "portfolio_turnover_percent": final_turnover,
            "swap_suggestions": swap_suggestions,
            "watchlist_ranking": watchlist_ranking,
            "portfolio_count": portfolio_count,
            "max_reached": max_reached,
            "max_stocks": max_stocks,
            "cash_balance": cash_balance,
            "total_value": round(total_value, 2),
            "ai_provider": l1_cfg["provider"],
            "ai_model": l1_cfg["model"],
            "current_sector_weights": current_sector_weights,
            "projected_sector_weights": projected_sector_weights,
            "sector_warnings": sector_warnings,
            "layer1_latency_ms": l1_latency_ms,
            "layer2_latency_ms": l2_latency_ms,
            "layer3_latency_ms": l3_latency_ms,
            "total_latency_ms": total_latency_ms,
            "layer1_result": {
                **l1_result,
                "provider": l1_cfg["provider"], "model": l1_cfg["model"], "name": l1_cfg.get("name", "Strategist"),
            },
            "layer2_result": {
                **l2_result,
                "provider": l2_cfg["provider"], "model": l2_cfg["model"], "name": l2_cfg.get("name", "Challenger"),
            },
            "layer3_result": {
                **l3_result,
                "provider": l3_cfg["provider"], "model": l3_cfg["model"], "name": l3_cfg.get("name", "Risk Auditor"),
            },
            "consensus": consensus,
            "active_policy": active_policy_out,
            # Phase 3B.5 — resolved constraint breakdown (None when resolver not run)
            "effective_envelope": _eff_env_to_dict(effective_envelope) if effective_envelope else None,
            **persona_fields,
        }

    except Exception as exc:
        logger.critical(
            f"Multi-layer pipeline failed. Initiating Global Fallback Model: "
            f"{fallback_provider}/{fallback_model}. Error: {exc}"
        )
        return _run_single_shot_fallback(
            pc, wc, sell_forced, locked, portfolio_data, current_sector_weights,
            pc_map, max_stocks, max_sector_pct, sector_limits,
            total_value, cash_balance, fallback_provider, fallback_model,
            portfolio_name, portfolio_count, max_reached,
        )
