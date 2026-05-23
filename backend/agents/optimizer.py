import json
import logging
from services.ai_client import call_ai
from services.json_utils import safe_parse_json
from services.optimizer.strategy_profiles import build_persona_context, get_profile  # noqa: F401

logger = logging.getLogger(__name__)

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
        }
        for i in items
    ]


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


def _normalize_l1_swaps(swaps: list) -> list[dict]:
    """Normalise L1 compact swap objects into the full swap format used downstream."""
    result = []
    for s in (swaps or []):
        result.append({
            "sell_symbol": s.get("sell") or s.get("sell_symbol"),
            "buy_symbol":  s.get("buy")  or s.get("buy_symbol"),
            "reason": s.get("reason", ""),
            "score_improvement": float(
                s.get("score_delta") or s.get("delta") or s.get("score_improvement") or 0
            ),
            "sector": s.get("sector", "Other"),
            "type": s.get("type", "SWAP"),
        })
    return result


def _normalize_allocations(allocs: list, pc_map: dict[str, float] | None = None) -> list[dict]:
    """Normalise L2 allocation objects to the internal TargetAllocation schema.

    pc_map: symbol → actual weight_pct from portfolio data (authoritative source for current_weight).
    allocation_change_percent and estimated_amount are computed in Python — never trusted from AI.
    """
    result = []
    for a in (allocs or []):
        sym = str(a.get("symbol") or a.get("s") or "")
        target_w = float(a.get("target_weight") or a.get("tw") or 0)
        # Use real portfolio weight if available; AI's reported current_weight is a fallback only
        current_w = (pc_map or {}).get(sym, float(a.get("current_weight") or a.get("w") or 0))
        change_pct = round(target_w - current_w, 2)
        result.append({
            "symbol": sym,
            "current_weight": round(current_w, 2),
            "target_weight": round(target_w, 2),
            "action": str(a.get("action") or a.get("sig") or "HOLD").upper(),
            "allocation_change_percent": change_pct,
            "estimated_amount": 0,  # filled in by caller once total_value is known
            "reason": str(a.get("reason") or ""),
        })
    return [a for a in result if a["symbol"]]


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
    "STRONG_CONSENSUS":    True,
    "REFINED_CONSENSUS":   True,
    "PARTIAL_CONSENSUS":   True,
    "WEAK_CONSENSUS":      False,
    "RISK_CONFLICT":       True,
    "STRATEGIC_CONFLICT":  False,
    "NO_ACTION_CONSENSUS": True,
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
    if consensus_type == "NO_ACTION_CONSENSUS":
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
    if consensus_type == "NO_ACTION_CONSENSUS":
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
) -> str:
    sl = sector_limits or {"default": max_sector_pct}

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

    return f"""{strategy_block}You are a STRATEGIST. Output swap targets in JSON only.
No explanation. No prose. Only valid JSON output.

Portfolio: {json.dumps(c_pc)}
Watchlist: {json.dumps(c_wc)}
Sector limits: {json.dumps(sl)}
Swap eligible: {swap_eligible or "none"}
Forced sells: {sell_forced or "none"}

STOCK COUNT: {current_count}/{max_stocks} max unique stocks after rebalancing.
SIGNALS: BUY=add aggressively, ACCUMULATE=add gradually, HOLD=keep, WATCH=monitor, REDUCE=trim, SELL=exit

MANDATE — evaluate ALL five before deciding:
1. Sector concentration: any sector near or above its limit? → propose rebalancing swap
2. Watchlist opportunities: any BUY/ACCUMULATE candidate available? → rank in top_buys
3. Overweight positions: any swap-eligible stock >25% weight? → consider REDUCE (sell=SYM, buy=null)
4. Low-score holdings: swap-eligible stocks with weak fa+ta vs higher-scored watchlist? → consider swap
5. Incremental improvement: would a 2–5% shift improve diversification or expected return?

PREFER incremental REDUCE/ACCUMULATE over full SELL/BUY replacements.
Small allocation shifts (2–5%) are meaningful — propose them when they improve the portfolio.
Behave like a disciplined active portfolio manager, not a frozen allocator.

priority="no_action" ONLY when all 5 checks above show no meaningful improvement opportunity.

Output schema — nothing else. Max 400 tokens.
swaps: max 3 (sell or buy may be null for one-sided REDUCE or ACCUMULATE from cash)
top_buys: max 5 watchlist symbols ranked by signal quality
sector_flags: max 3 short strings
priority: one word only

{{"swaps":[{{"sell":"SYM|null","buy":"SYM|null","score_delta":0.0,"sector":"S","type":"SELL|SWAP|REDUCE"}}],"top_buys":["S"],"sector_flags":["S 45%>30%"],"priority":"growth"}}"""


def _layer2_prompt(
    pc: list[dict],
    wc: list[dict],
    l1: dict,
    role: str = "",
    cash_balance: float = 0.0,
    total_value: float = 0.0,
    persona_context: dict | None = None,
) -> str:
    role_line = f"Your role: {role}\n\n" if role else ""
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

    return f"""You are an independent portfolio reviewer.
{strategy_block}{role_line}The Strategist (Layer 1) proposed:
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

PHILOSOPHY: Unnecessary portfolio turnover destroys value through transaction costs and tax drag.
Setting status="NO_ACTION" with rebalance_opportunity_score below 20 is HIGHLY ENCOURAGED when:
- The portfolio is already well-balanced across sectors and signal quality
- No watchlist candidate has a compelling BUY/ACCUMULATE signal with clear edge over existing holdings
- Market conditions are uncertain or data quality is insufficient to justify rebalancing
Only recommend changes with a clear, measurable, defensible improvement.

score guide: 0-20=no action needed, 21-40=minor optimization, 41-70=moderate opportunity, 71-100=strong opportunity.
no_action_reason enum (use null if status=REBALANCE):
  WELL_BALANCED | LOW_CONFIDENCE | HIGH_DISAGREEMENT | CONSTRAINT_BLOCKED | MARKET_UNCERTAINTY | INSUFFICIENT_EDGE

If any watchlist symbol with BUY/ACCUMULATE signal was evaluated but rejected due to sector limits,
cash constraints, or portfolio count cap — list it in blocked_opportunities with the specific reason.

Build a complete capital allocation plan. Challenge or confirm the Strategist's swaps.
Use all 6 signals (ACCUMULATE|BUY|WATCH|HOLD|REDUCE|SELL) for every position.

Weights are FLAT PERCENTAGES (e.g. 10.0 means 10% of portfolio). Do NOT output monetary amounts.
The backend will compute change amounts from target_weight minus current_weight automatically.

Return JSON only. No markdown fences.

{{
  "status": "REBALANCE|NO_ACTION",
  "rebalance_opportunity_score": 50,
  "no_action_reason": "WELL_BALANCED|LOW_CONFIDENCE|HIGH_DISAGREEMENT|CONSTRAINT_BLOCKED|MARKET_UNCERTAINTY|INSUFFICIENT_EDGE|null",
  "no_action_summary": "short human-readable explanation when NO_ACTION, null otherwise",
  "blocked_opportunities": [{{"symbol":"X","signal":"BUY","reason":"sector_limit_exceeded|insufficient_cash|portfolio_count_cap"}}],
  "agrees_with_layer1": true,
  "disagreements": ["detailed reason if any"],
  "portfolio_assessment": "1-2 sentences",
  "cash_balance_target": 0.0,
  "allocations": [
    {{"symbol":"X","current_weight":0.0,"target_weight":0.0,"action":"BUY|ACCUMULATE|HOLD|REDUCE|SELL|WATCH","reason":"concise"}}
  ]
}}"""


def _layer3_prompt(l1: dict, l2: dict, role: str = "", max_sector_pct: int = 40, persona_context: dict | None = None) -> str:
    role_line = f"Your role: {role}\n\n" if role else ""
    # L1 (Strategist) now outputs swaps only — no allocation table
    l1_swaps    = l1.get("swap_suggestions", l1.get("swaps", []))[:4]
    l1_priority = l1.get("priority", "balanced")
    l2_allocs   = l2.get("allocations", l2.get("target_allocations", []))

    persona_note = ""
    if persona_context:
        p_label    = persona_context.get("persona_label", "Balanced")
        p_turn     = persona_context.get("turnover_tolerance", 0.5)
        p_vol      = persona_context.get("volatility_tolerance", 0.5)
        persona_note = (
            f"\nPersona Policy: {p_label.upper()} "
            f"(turnover tolerance: {int(p_turn*100)}%, volatility tolerance: {int(p_vol*100)}%)\n"
            "Flag any risk that conflicts with this persona's policy constraints.\n"
        )

    return f"""You are a portfolio risk auditor.
{persona_note}{role_line}Evaluate both allocation proposals for concentration risk and soundness.

Layer 1 (Strategist):
Priority: {l1_priority}
Proposed swaps: {json.dumps(l1_swaps, indent=2)}

Layer 2 (Challenger):
Agrees: {l2.get("agrees_with_layer1", True)}
Disagreements: {json.dumps(l2.get("disagreements", []))}
Allocations: {json.dumps(l2_allocs, indent=2)}

Check for (use exact severity thresholds):
- CRITICAL : sector > {max_sector_pct}% OR single stock > 30% OR SELL signal kept in portfolio
- HIGH     : single stock 25-30% OR weak fundamentals on large position
- MEDIUM   : sector 60-80% of limit OR conflicting allocation math
- LOW      : minor concentration risk, suboptimal but acceptable

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

Return ONLY valid JSON without markdown fences:
{{
  "status": "REBALANCE|NO_ACTION",
  "rebalance_opportunity_score": 50,
  "no_action_reason": "WELL_BALANCED|LOW_CONFIDENCE|HIGH_DISAGREEMENT|CONSTRAINT_BLOCKED|MARKET_UNCERTAINTY|INSUFFICIENT_EDGE|null",
  "no_action_summary": "short explanation if NO_ACTION, null otherwise",
  "blocked_opportunities": [{{"symbol":"X","signal":"BUY","reason":"sector_limit_exceeded|insufficient_cash|portfolio_count_cap"}}],
  "portfolio_assessment": "1-2 sentence summary of the plan",
  "cash_balance_target": 5.0,
  "allocations": [
    {{"symbol":"X","current_weight":0.0,"target_weight":0.0,"action":"BUY|ACCUMULATE|HOLD|REDUCE|SELL|WATCH","reason":"concise"}}
  ],
  "risk_flags": [],
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
    prompt = _fallback_prompt(pc, wc, sell_forced, locked, max_stocks, max_sector_pct, total_value, cash_balance)
    raw = call_ai(
        prompt, fallback_provider, fallback_model, max_tokens=4096,
        usage_operation="optimize", usage_layer="fallback",
    )
    fb_latency_ms = raw["latency_ms"]
    result = safe_parse_json(raw["text"])

    raw_allocs = result.pop("allocations", None) or []
    allocations = _normalize_allocations(raw_allocs, pc_map)
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
    result["swap_suggestions"] = _postprocess_swaps(_normalize_l1_swaps(result.get("swaps", [])), sell_forced, locked)
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
) -> dict:
    """3-layer Dynamic Capital Allocation Engine with global single-shot fallback."""
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

    # Authoritative current weights from real portfolio data (not AI-reported)
    pc_map: dict[str, float] = {p["symbol"]: p.get("weight_pct", 0.0) for p in portfolio_data}

    swap_eligible = [p["symbol"] for p in portfolio_data if p.get("allow_swap", True) and p.get("signal") != "SELL"]
    pc = _compact_p(portfolio_data)
    wc = _compact_w(watchlist_data)
    c_pc, c_wc = _compress_for_layer1(pc, wc)

    current_sector_weights = calculate_current_sector_weights(portfolio_data)

    try:
        # Layer 1 — Strategist
        l1_parse_failed = False
        try:
            l1_prompt = _layer1_prompt(
                c_pc, c_wc, sell_forced, swap_eligible,
                max_sector_pct=max_sector_pct, sector_limits=sector_limits,
                max_stocks=max_stocks, current_count=portfolio_count,
                persona_context=persona_context,
            )
            logger.info(f"L1 prompt chars: {len(l1_prompt)}")
            l1_raw = call_ai(
                l1_prompt, l1_cfg["provider"], l1_cfg["model"], max_tokens=2048,
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
                _normalize_l1_swaps(l1_result.get("swaps", [])), sell_forced, locked
            )
            logger.info(
                "[L1_DEBUG] parsed: swaps_count=%d swap_suggestions_count=%d top_buys=%s priority=%s",
                len(l1_result.get("swaps", [])),
                len(l1_result.get("swap_suggestions", [])),
                l1_result.get("top_buys", []),
                l1_result.get("priority"),
            )
        except Exception as e:
            l1_parse_failed = True
            logger.error("[L1_DEBUG] parse_error=%s", e)
            l1_result = {
                "error": str(e), "swap_suggestions": [],
                "top_buys": [], "sector_flags": [], "priority": "",
            }
            l1_latency_ms = 0

        # Layer 2 — Challenger
        try:
            l2_raw = call_ai(
                _layer2_prompt(pc, wc, l1_result, l2_cfg.get("role", ""),
                               cash_balance=cash_balance, total_value=total_value,
                               persona_context=persona_context),
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
            l2_allocs = _normalize_allocations(raw_allocs, pc_map)
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
        try:
            l3_raw = call_ai(
                _layer3_prompt(l1_result, l2_result, l3_cfg.get("role", ""), max_sector_pct=max_sector_pct,
                               persona_context=persona_context),
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
