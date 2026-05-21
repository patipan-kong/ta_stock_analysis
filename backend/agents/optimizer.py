import json
import logging
from services.ai_client import call_ai
from services.json_utils import safe_parse_json

logger = logging.getLogger(__name__)

_DEFAULT_LAYERS: dict = {
    "layer1": {
        "name": "Strategist",
        "role": "Aggressive growth with sector diversification",
        "provider": "anthropic",
        "model": "claude-sonnet-4-6",
    },
    "layer2": {
        "name": "Challenger",
        "role": "Independent reviewer seeking alternative allocations",
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
    """Strip data to the minimum Layer 1 needs — shortened keys reduce prompt tokens."""
    c_pc = [
        {
            "s": i["symbol"],
            "sec": i.get("sector", "Other"),
            "w": round(i.get("weight_pct", 0), 1),
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


def _normalize_l1_swaps(swaps: list) -> list[dict]:
    """Convert L1 minimal swap objects to the full format used by post-processing and Layer 3."""
    result = []
    for s in (swaps or []):
        result.append({
            "sell_symbol": s.get("sell") or s.get("sell_symbol"),
            "buy_symbol": s.get("buy") or s.get("buy_symbol"),
            "reason": s.get("reason", ""),
            "score_improvement": float(s.get("score_delta") or s.get("delta") or s.get("score_improvement") or 0),
            "sector": s.get("sector", "Other"),
            "type": s.get("type", "SWAP"),
        })
    return result


def _rebuild_watchlist_ranking(top_buys: list, wc: list[dict]) -> list[dict]:
    """Rebuild full watchlist_ranking from L1 top_buys + watchlist data."""
    wc_map = {w["symbol"]: w for w in wc}
    seen: set[str] = set()
    ranked: list[str] = []
    for sym in (top_buys or []):
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


# ─── Sector weight helpers ────────────────────────────────────────────────────

def calculate_current_sector_weights(portfolio_items: list[dict]) -> dict:
    """Actual sector weights by market value (shares × current_price)."""
    sector_values: dict[str, float] = {}
    for item in portfolio_items:
        sector = item.get("sector") or "Other"
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
    """Simulate portfolio after applying swap suggestions and recompute sector weights."""
    holdings: dict[str, dict] = {}
    for item in portfolio_items:
        sector = item.get("sector") or "Other"
        price = item.get("current_price") or item.get("avg_cost") or 0
        mv = (item.get("shares") or 0) * price
        holdings[item["symbol"]] = {"sector": sector, "value": mv}

    for swap in swaps:
        sell_sym = swap.get("sell_symbol")
        buy_sym = swap.get("buy_symbol")
        sector = swap.get("sector") or "Other"
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


# ─── Post-processing ──────────────────────────────────────────────────────────

def _postprocess_swaps(
    suggestions: list[dict],
    sell_forced: list[str],
    locked: list[str],
) -> list[dict]:
    """Enforce hard constraints regardless of AI output."""
    for s in suggestions:
        if s.get("type") == "SELL":
            s["buy_symbol"] = None
            s["score_improvement"] = 0

    suggestions = [
        s for s in suggestions
        if not (s.get("type") == "SELL" and not s.get("sell_symbol"))
    ]

    covered = {s["sell_symbol"] for s in suggestions if s.get("type") == "SELL" and s.get("sell_symbol")}
    injected = [
        {"sell_symbol": sym, "buy_symbol": None, "reason": "Forced exit: SELL signal detected.",
         "score_improvement": 0, "sector": "Other", "type": "SELL"}
        for sym in sell_forced if sym not in covered
    ]
    suggestions = injected + suggestions

    locked_set = set(locked)
    return [
        s for s in suggestions
        if not (s.get("type") == "SWAP" and s.get("sell_symbol") in locked_set)
    ]


# ─── Consensus Engine ─────────────────────────────────────────────────────────

def _consensus_engine(l2: dict, l3: dict) -> dict:
    agrees = bool(l2.get("agrees_with_layer1", True))
    risk_flags = l3.get("risk_flags", [])
    safer_choice = l3.get("safer_choice", "layer1")
    final_risk = l3.get("final_risk_level", "medium")

    high_flags = [f for f in risk_flags if f.get("severity") == "high"]

    if agrees and final_risk != "high":
        confidence, recommended = "high", "layer1"
    elif not agrees and safer_choice == "layer2" and final_risk != "high":
        confidence, recommended = "medium", "layer2"
    elif safer_choice == "layer1" or agrees:
        confidence, recommended = "medium", "layer1"
    else:
        confidence, recommended = "low", "neither"

    parts: list[str] = []
    if recommended == "layer1":
        parts.append("Follow Strategist recommendation.")
    elif recommended == "layer2":
        parts.append("Consider Challenger's alternative allocation.")
    else:
        parts.append("Neither proposal is ideal — review manually.")

    if high_flags:
        syms = ", ".join(f["symbol"] for f in high_flags[:3])
        parts.append(f"Address high-risk positions: {syms}.")

    if l3.get("auditor_notes"):
        parts.append(l3["auditor_notes"])

    return {
        "agrees": agrees,
        "confidence": confidence,
        "recommended": recommended,
        "final_risk_level": final_risk,
        "risk_flag_count": len(risk_flags),
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
) -> str:
    sl = sector_limits or {"default": max_sector_pct}
    return f"""You are a DIRECTOR. Output swap targets only.
DO NOT explain. DO NOT describe. DO NOT reason.
Every word not in the JSON structure is a failure.
If you write reasoning, you fail.
If you exceed 200 tokens, you fail.

Portfolio: {json.dumps(c_pc)}
Watchlist: {json.dumps(c_wc)}
Sector limits: {json.dumps(sl)}
Swap eligible: {swap_eligible or "none"}
Forced sells: {sell_forced or "none"}

Output schema (strictly follow):
swaps: max 3 items [sell, buy, delta, sector]
top_buys: max 5 symbols
sector_flags: max 3 short strings
priority: one word only

{{"swaps":[{{"sell":"SYMBOL|null","buy":"SYMBOL|null","score_delta":0.0,"sector":"S","type":"SELL|SWAP"}}],"top_buys":["S"],"sector_flags":["S 45%>30%"],"priority":"growth"}}"""


def _layer2_prompt(pc: list[dict], wc: list[dict], l1: dict, role: str = "") -> str:
    role_line = f"Your role: {role}\n\n" if role else ""
    l1_swaps = l1.get("swap_suggestions", l1.get("swaps", []))
    l1_top_buys = l1.get("top_buys", [])
    l1_sector_flags = l1.get("sector_flags", [])
    l1_priority = l1.get("priority", "balanced")
    return f"""You are an independent portfolio reviewer.
{role_line}The strategist proposed:
- Priority: {l1_priority}
- Swaps: {json.dumps(l1_swaps, indent=2)}
- Top watchlist picks: {l1_top_buys}
- Sector flags: {l1_sector_flags}

Full portfolio data for your analysis:
{json.dumps(pc, indent=2)}

Full watchlist for your analysis:
{json.dumps(wc, indent=2)}

Using the full data above, challenge or confirm the strategist's proposal with detailed reasoning.
Thai stocks end in .BK.

CRITICAL: Return JSON only. No markdown fences.

{{
  "agrees_with_layer1": true,
  "disagreements": ["detailed reason if any"],
  "alternative_suggestions": [
    {{"sell_symbol": "...", "buy_symbol": "...", "reason": "...", "score_improvement": 0.0, "sector": "...", "type": "SELL|SWAP"}}
  ],
  "alternative_allocation": {{"SYMBOL": "20%"}}
}}
Use 6-level signals (ACCUMULATE|BUY|WATCH|HOLD|REDUCE|SELL) in any signal fields."""


def _layer3_prompt(l1: dict, l2: dict, role: str = "", max_sector_pct: int = 40) -> str:
    role_line = f"Your role: {role}\n\n" if role else ""
    l1_swaps = l1.get("swap_suggestions", l1.get("swaps", []))
    l1_sector_flags = l1.get("sector_flags", [])
    return f"""You are a portfolio risk auditor.
{role_line}Evaluate both proposals for concentration risk and allocation issues.

Layer 1 (Strategist) swaps:
{json.dumps(l1_swaps, indent=2)}
Sector flags: {l1_sector_flags}

Layer 2 (Challenger):
Agrees: {l2.get("agrees_with_layer1", True)}
Disagreements: {json.dumps(l2.get("disagreements", []))}
Alternatives: {json.dumps(l2.get("alternative_suggestions", []), indent=2)}

Check for (use exact severity thresholds):
- CRITICAL : sector > {max_sector_pct}% OR single stock > 30% OR SELL signal kept in portfolio
- HIGH     : single stock 25-30% OR weak fundamentals on large position
- MEDIUM   : sector 60-80% of limit OR conflicting allocation math
- LOW      : minor concentration risk, suboptimal but acceptable

CRITICAL: Return JSON only. No markdown fences.

{{
  "risk_flags": [{{"symbol": "...", "issue": "...", "severity": "LOW|MEDIUM|HIGH|CRITICAL"}}],
  "safer_choice": "layer1|layer2|neither",
  "final_risk_level": "low|medium|high",
  "auditor_notes": "1-2 sentences."
}}"""


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
) -> dict:
    """Single-model optimizer (legacy path)."""
    sell_forced   = [p["symbol"] for p in portfolio_data if p.get("signal") == "SELL"]
    swap_eligible = [p["symbol"] for p in portfolio_data if p.get("allow_swap", True) and p.get("signal") != "SELL"]
    locked        = [p["symbol"] for p in portfolio_data if not p.get("allow_swap", True)]
    pc = _compact_p(portfolio_data)
    wc = _compact_w(watchlist_data)
    c_pc, c_wc = _compress_for_layer1(pc, wc)
    prompt = _layer1_prompt(
        c_pc, c_wc, sell_forced, swap_eligible,
        max_sector_pct=max_sector_pct,
    )
    logger.info(f"L1 prompt chars: {len(prompt)}")
    ai_result = call_ai(
        prompt, provider, model, max_tokens=1024,
        use_schema=True,
        usage_operation="optimize", usage_layer="layer1",
    )
    logger.info(f"L1 response chars: {len(ai_result.get('text', ''))}")
    result = safe_parse_json(ai_result["text"])
    result["portfolio_name"] = portfolio_name
    result["portfolio_count"] = portfolio_count
    result["max_reached"] = max_reached
    result["max_stocks"] = max_stocks
    result["swap_suggestions"] = _postprocess_swaps(
        _normalize_l1_swaps(result.get("swaps", [])), sell_forced, locked
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
) -> dict:
    """3-layer optimizer with consensus engine."""
    if layers is None:
        layers = _DEFAULT_LAYERS

    l1_cfg = {**_DEFAULT_LAYERS["layer1"], **layers.get("layer1", {})}
    l2_cfg = {**_DEFAULT_LAYERS["layer2"], **layers.get("layer2", {})}
    l3_cfg = {**_DEFAULT_LAYERS["layer3"], **layers.get("layer3", {})}

    sell_forced   = [p["symbol"] for p in portfolio_data if p.get("signal") == "SELL"]
    swap_eligible = [p["symbol"] for p in portfolio_data if p.get("allow_swap", True) and p.get("signal") != "SELL"]
    locked        = [p["symbol"] for p in portfolio_data if not p.get("allow_swap", True)]
    pc = _compact_p(portfolio_data)
    wc = _compact_w(watchlist_data)
    c_pc, c_wc = _compress_for_layer1(pc, wc)

    current_sector_weights = calculate_current_sector_weights(portfolio_data)

    # Layer 1 — Strategist (compressed data, minimal output schema)
    try:
        l1_prompt = _layer1_prompt(
            c_pc, c_wc, sell_forced, swap_eligible,
            max_sector_pct=max_sector_pct,
            sector_limits=sector_limits,
        )
        logger.info(f"L1 prompt chars: {len(l1_prompt)}")
        l1_raw = call_ai(
            l1_prompt, l1_cfg["provider"], l1_cfg["model"], max_tokens=1024,
            use_schema=True,
            usage_operation="optimize", usage_layer="layer1",
        )
        l1_latency_ms = l1_raw["latency_ms"]
        logger.info(f"L1 response chars: {len(l1_raw.get('text', ''))}")
        l1_result = safe_parse_json(l1_raw["text"])
        # Normalize compact swaps → full format for L3 and post-processing
        l1_result["swap_suggestions"] = _normalize_l1_swaps(l1_result.get("swaps", []))
    except Exception as e:
        l1_result = {
            "error": str(e), "swaps": [], "swap_suggestions": [],
            "top_buys": [], "sector_flags": [], "priority": "balanced",
        }
        l1_latency_ms = 0

    # Layer 2 — Challenger (full pc/wc for reasoning, L1 compact summary as context)
    try:
        l2_raw = call_ai(
            _layer2_prompt(pc, wc, l1_result, l2_cfg.get("role", "")),
            l2_cfg["provider"], l2_cfg["model"], max_tokens=8192,
            usage_operation="optimize", usage_layer="layer2",
        )
        l2_latency_ms = l2_raw["latency_ms"]
        l2_result = safe_parse_json(l2_raw["text"])
    except Exception as e:
        l2_result = {"error": str(e), "agrees_with_layer1": True, "disagreements": [], "alternative_suggestions": []}
        l2_latency_ms = 0

    # Layer 3 — Risk Auditor (works from normalized swap_suggestions)
    try:
        l3_raw = call_ai(
            _layer3_prompt(l1_result, l2_result, l3_cfg.get("role", ""), max_sector_pct=max_sector_pct),
            l3_cfg["provider"], l3_cfg["model"], max_tokens=2048,
            usage_operation="optimize", usage_layer="layer3",
        )
        l3_latency_ms = l3_raw["latency_ms"]
        l3_result = safe_parse_json(l3_raw["text"])
    except Exception as e:
        l3_result = {"error": str(e), "risk_flags": [], "safer_choice": "layer1",
                     "final_risk_level": "medium", "auditor_notes": ""}
        l3_latency_ms = 0

    consensus = _consensus_engine(l2_result, l3_result)
    swap_suggestions = _postprocess_swaps(
        l1_result.get("swap_suggestions", []), sell_forced, locked
    )

    projected_sector_weights = calculate_projected_sector_weights(portfolio_data, swap_suggestions)
    sector_warnings = _compute_sector_warnings(
        current_sector_weights, projected_sector_weights, sector_limits, max_sector_pct
    )

    total_latency_ms = l1_latency_ms + l2_latency_ms + l3_latency_ms
    watchlist_ranking = _rebuild_watchlist_ranking(l1_result.get("top_buys", []), wc)
    portfolio_assessment = (
        "; ".join(l1_result.get("sector_flags", [])) or l1_result.get("priority", "")
    )

    return {
        "portfolio_name": portfolio_name,
        "portfolio_assessment": portfolio_assessment,
        "optimization_notes": consensus["recommended_action"],
        "swap_suggestions": swap_suggestions,
        "watchlist_ranking": watchlist_ranking,
        "portfolio_count": portfolio_count,
        "max_reached": max_reached,
        "max_stocks": max_stocks,
        "ai_provider": l1_cfg["provider"],
        "ai_model": l1_cfg["model"],
        "current_sector_weights": current_sector_weights,
        "projected_sector_weights": projected_sector_weights,
        "sector_warnings": sector_warnings,
        "layer1_latency_ms": l1_latency_ms,
        "layer2_latency_ms": l2_latency_ms,
        "layer3_latency_ms": l3_latency_ms,
        "total_latency_ms": total_latency_ms,
        "layer1_result": {**l1_result, "provider": l1_cfg["provider"], "model": l1_cfg["model"], "name": l1_cfg.get("name", "Strategist")},
        "layer2_result": {**l2_result, "provider": l2_cfg["provider"], "model": l2_cfg["model"], "name": l2_cfg.get("name", "Challenger")},
        "layer3_result": {**l3_result, "provider": l3_cfg["provider"], "model": l3_cfg["model"], "name": l3_cfg.get("name", "Risk Auditor")},
        "consensus": consensus,
    }
