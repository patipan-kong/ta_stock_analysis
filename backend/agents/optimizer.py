import json
from services.ai_client import call_ai
from services.json_utils import safe_parse_json


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
    pc: list[dict], wc: list[dict], portfolio_name: str,
    portfolio_count: int, max_reached: bool, room: int,
    sell_forced: list[str], swap_eligible: list[str], locked: list[str],
    role: str = "",
    max_stocks: int = 12,
    max_sector_pct: int = 40,
    sector_limits: dict | None = None,
    current_sector_weights: dict | None = None,
) -> str:
    role_line = f"Your focus: {role}\n\n" if role else ""
    if sector_limits:
        sector_block = (
            f"SECTOR ALLOCATION LIMITS (from user settings):\n{json.dumps(sector_limits, indent=2)}\n"
            "sector_limits apply to CURRENT portfolio holdings. "
            "Flag only if current weight already exceeds limit. "
            "Show projected weight after each swap suggestion. "
            "\"default\" applies to sectors not listed above."
        )
    else:
        sector_block = f"Max sector allocation: {max_sector_pct}% per sector. sector_limits apply to CURRENT holdings only."

    sector_weights_block = ""
    if current_sector_weights:
        sector_weights_block = (
            f"\nCURRENT PORTFOLIO SECTOR WEIGHTS (by market value):\n"
            f"{json.dumps(current_sector_weights, indent=2)}\n"
        )
    return f"""Portfolio optimization expert for Thai (SET) and US stocks.
{role_line}PORTFOLIO: "{portfolio_name}"
{json.dumps(pc, indent=2)}

WATCHLIST:
{json.dumps(wc, indent=2)}

SCORING: combined_score = 0.4×ta_score + 0.6×fa_score (range ~−8 to +8). Thai stocks end in .BK.
{sector_weights_block}
CONSTRAINT GROUPS:
- Portfolio size: {portfolio_count}/{max_stocks}. Room for {room} more. {"AT LIMIT — no net additions allowed." if max_reached else ""}
- SELL/REDUCE-signal stocks (ALWAYS include as type=SELL, regardless of allow_swap): {sell_forced or "none"}
- Swap-eligible: {swap_eligible or "none"}
- Locked (exclude from SWAP, still SELL if signalled): {locked or "none"}

RULES:
1. type="SELL": one entry per forced-exit symbol. buy_symbol=null, score_improvement=0.
2. type="SWAP": only swap_eligible, only if watchlist score >= portfolio score + 2. Max 4 SWAPs. {"No net additions." if max_reached else f"Up to {room} pure additions (sell_symbol=null, type=SWAP) if score is strong."}
3. watchlist_ranking: ALL watchlist stocks by combined_score desc. Top {room} may have non-zero suggested_allocation_pct, rest=0. Non-zero must sum to 100, cap 25%/stock.
   {sector_block}
4. Use 6-level signals for watchlist_ranking: ACCUMULATE | BUY | WATCH | HOLD | REDUCE | SELL.
5. reasoning: 1-2 sentences on overall strategy. priority: "growth"|"balanced"|"defensive".

CRITICAL: Return JSON only. No markdown fences.

{{
  "portfolio_count": {portfolio_count},
  "max_reached": {"true" if max_reached else "false"},
  "portfolio_assessment": "One sentence.",
  "optimization_notes": "1-2 recommendations.",
  "reasoning": "1-2 sentence strategy rationale.",
  "priority": "growth|balanced|defensive",
  "swap_suggestions": [
    {{"sell_symbol": "symbol or null", "buy_symbol": "symbol or null", "reason": "One sentence.",
      "score_improvement": 0.0, "sector": "Banking|Energy|Retail|Healthcare|Tech|Utilities|Other", "type": "SELL|SWAP"}}
  ],
  "watchlist_ranking": [
    {{"symbol": "...", "rank": 1, "signal": "ACCUMULATE|BUY|WATCH|HOLD|REDUCE|SELL", "combined_score": 0.0,
      "sector": "...", "suggested_allocation_pct": 0.0, "reasoning": "One sentence."}}
  ]
}}"""


def _layer2_prompt(pc: list[dict], wc: list[dict], l1: dict, role: str = "") -> str:
    role_line = f"Your role: {role}\n\n" if role else ""
    return f"""You are an independent portfolio reviewer.
{role_line}A strategist proposed these portfolio changes:
{json.dumps(l1.get("swap_suggestions", []), indent=2)}

Strategist reasoning: {l1.get("reasoning", l1.get("portfolio_assessment", ""))}

Portfolio context:
{json.dumps(pc, indent=2)}

Watchlist alternatives:
{json.dumps(wc, indent=2)}

Challenge or confirm this proposal. Thai stocks end in .BK.

CRITICAL: Return JSON only. No markdown fences.

{{
  "agrees_with_layer1": true,
  "disagreements": ["reason if any"],
  "alternative_suggestions": [
    {{"sell_symbol": "...", "buy_symbol": "...", "reason": "...", "score_improvement": 0.0, "sector": "...", "type": "SELL|SWAP"}}
  ],
  "alternative_allocation": {{"SYMBOL": "20%"}}
}}
Use 6-level signals (ACCUMULATE|BUY|WATCH|HOLD|REDUCE|SELL) in any signal fields."""


def _layer3_prompt(l1: dict, l2: dict, role: str = "", max_sector_pct: int = 40) -> str:
    role_line = f"Your role: {role}\n\n" if role else ""
    return f"""You are a portfolio risk auditor.
{role_line}Evaluate both proposals for concentration risk and allocation issues.

Layer 1 (Strategist) swaps:
{json.dumps(l1.get("swap_suggestions", []), indent=2)}
Notes: {l1.get("optimization_notes", "")}

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
    room = max(0, max_stocks - portfolio_count)
    prompt = _layer1_prompt(
        _compact_p(portfolio_data), _compact_w(watchlist_data),
        portfolio_name, portfolio_count, max_reached, room,
        sell_forced, swap_eligible, locked, role="",
        max_stocks=max_stocks, max_sector_pct=max_sector_pct,
    )
    ai_result = call_ai(
        prompt,
        provider,
        model,
        max_tokens=8192,
        usage_operation="optimize",
        usage_layer="layer1",
    )
    result = safe_parse_json(ai_result["text"])
    result["swap_suggestions"] = _postprocess_swaps(
        result.get("swap_suggestions", []), sell_forced, locked
    )
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
    room = max(0, max_stocks - portfolio_count)
    pc, wc = _compact_p(portfolio_data), _compact_w(watchlist_data)

    current_sector_weights = calculate_current_sector_weights(portfolio_data)

    # Layer 1 — Strategist
    try:
        l1_raw = call_ai(
            _layer1_prompt(pc, wc, portfolio_name, portfolio_count, max_reached, room,
                           sell_forced, swap_eligible, locked, l1_cfg.get("role", ""),
                           max_stocks=max_stocks, max_sector_pct=max_sector_pct,
                           sector_limits=sector_limits,
                           current_sector_weights=current_sector_weights),
            l1_cfg["provider"], l1_cfg["model"], max_tokens=8192,
            usage_operation="optimize",
            usage_layer="layer1",
        )
        l1_latency_ms = l1_raw["latency_ms"]
        l1_result = safe_parse_json(l1_raw["text"])
    except Exception as e:
        l1_result = {"error": str(e), "swap_suggestions": [], "watchlist_ranking": []}
        l1_latency_ms = 0

    # Layer 2 — Challenger
    try:
        l2_raw = call_ai(
            _layer2_prompt(pc, wc, l1_result, l2_cfg.get("role", "")),
            l2_cfg["provider"], l2_cfg["model"], max_tokens=8192,
            usage_operation="optimize",
            usage_layer="layer2",
        )
        l2_latency_ms = l2_raw["latency_ms"]
        l2_result = safe_parse_json(l2_raw["text"])
    except Exception as e:
        l2_result = {"error": str(e), "agrees_with_layer1": True, "disagreements": [], "alternative_suggestions": []}
        l2_latency_ms = 0

    # Layer 3 — Risk Auditor
    try:
        l3_raw = call_ai(
            _layer3_prompt(l1_result, l2_result, l3_cfg.get("role", ""), max_sector_pct=max_sector_pct),
            l3_cfg["provider"], l3_cfg["model"], max_tokens=8192,
            usage_operation="optimize",
            usage_layer="layer3",
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

    return {
        "portfolio_name": portfolio_name,
        "portfolio_assessment": l1_result.get("portfolio_assessment", ""),
        "optimization_notes": consensus["recommended_action"],
        "swap_suggestions": swap_suggestions,
        "watchlist_ranking": l1_result.get("watchlist_ranking", []),
        "portfolio_count": portfolio_count,
        "max_reached": max_reached,
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
