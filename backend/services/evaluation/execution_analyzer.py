"""execution_analyzer.py — AI Evaluation M2: Plan-vs-Actual Execution Analysis.

Compares the day-0 plan (services/evaluation/plan_grader.derive_full_plan)
against what a human actually did, per `UserExecutionDecision`, once trades
are linked via `Transaction.execution_decision_id` (P5). Fixes half of G5.

Four deltas, documented weights (composite sums to 100 when all are
measurable; unmeasurable components are excluded and the remaining weights
renormalized — never padded with a fabricated value, PLAN §4.7):

    timing        (weight 25) — recommendation-date price
                  (RecommendationSnapshot.scores_map_json[symbol]
                  ["current_price"], frozen at analysis time) vs the
                  share-weighted average fill price of linked transactions
                  for that symbol. Reported per-symbol as a signed % delta;
                  the composite component is 100 minus 5x the average
                  absolute delta (documented curve, floors at 0 past a 20%
                  average miss).
    size          (weight 25) — planned amount (the OPTIMIZED plan's own
                  executed_amount for SELL/REDUCE, or the buy-side
                  estimated_amount) vs the sum of linked transactions'
                  total_amount for that symbol. Component is 100 minus the
                  average absolute % delta.
    funding_fidelity (weight 25) — of the symbols the plan assigned
                  execution_role=FUNDING_SOURCE, what fraction have a linked
                  SELL/REDUCE transaction? Not applicable (excluded, not
                  zeroed) when the plan proposed no funding-source trades.
    completeness  (weight 25) — fraction of all planned trades (buy + sell/
                  reduce, excluding DEFERRED — those were never meant to
                  execute) that have at least one linked transaction. Also
                  carried as `completeness_pct` for the UX S4b PARTIAL
                  warning payload.

A decision with zero linked transactions returns status="unavailable" and
score=None — never a fabricated 0 or 100 (PLAN §4.7, §4.8). A decision with
some but not all deltas measurable returns status="partial" with a composite
computed only over what could be measured, and every unmeasured symbol/delta
carries an explicit reason string.

Zero AI calls. Zero writes — this module only reads (PLAN §4.1); the
Transaction.execution_decision_id column it depends on is populated by the
buy/sell endpoints (services/portfolio_transactions.py), which is decision-
recording, not evaluation.

Public API
----------
compute_execution_analysis(target_allocations, cash_available, violations,
                            recommendation_prices, linked_transactions) -> dict
    Pure function — no DB access, fully unit-testable with synthetic data.
"""
from __future__ import annotations

from typing import Any

# Curve constants for the timing/size sub-scores — documented here rather
# than left as bare numbers in the function body.
_TIMING_PENALTY_PER_PCT = 5.0   # 100 - (avg |timing delta %|) * this, floored at 0
_SIZE_PENALTY_PER_PCT = 1.0     # 100 - (avg |size delta %|) * this, floored at 0

_COMPONENT_WEIGHT = 25.0        # all four components weigh equally


def compute_execution_analysis(
    target_allocations: list[dict],
    cash_available: float,
    violations: list[str] | None,
    recommendation_prices: dict[str, float],
    linked_transactions: list[dict],
) -> dict[str, Any]:
    """Plan-vs-actual execution analysis for one decision.

    Args:
        target_allocations, cash_available, violations: the same stored
            snapshot inputs plan_grader.compute_plan_grade takes — the plan
            is re-derived via derive_full_plan, never duplicated by hand.
        recommendation_prices: {symbol: price} — normally
            RecommendationSnapshot.scores_map_json's per-symbol current_price.
        linked_transactions: [{"symbol", "shares", "price_per_share",
            "total_amount"}, ...] already filtered by the caller to rows
            whose execution_decision_id matches this decision.
    """
    from services.evaluation.plan_grader import derive_full_plan
    from services.optimizer.execution_optimizer import ROLE_FUNDING_SOURCE, STATE_DEFERRED

    plan = derive_full_plan(target_allocations, cash_available, violations)
    eo = plan["execution_optimization"]

    planned_by_symbol: dict[str, dict] = {}
    for bt in plan["buy_trades"]:
        planned_by_symbol[bt["symbol"]] = {
            "action": bt["action"],
            "planned_amount": bt["planned_amount"],
            "execution_role": None,
        }
    for t in eo.trades:
        if t.execution_state == STATE_DEFERRED:
            continue  # never meant to execute — not part of "the plan" to compare against
        planned_by_symbol[t.symbol] = {
            "action": t.action,
            "planned_amount": t.executed_amount,
            "execution_role": t.execution_role,
        }

    tx_by_symbol: dict[str, list[dict]] = {}
    for tx in linked_transactions or []:
        sym = tx.get("symbol")
        if sym:
            tx_by_symbol.setdefault(sym, []).append(tx)

    total_planned = len(planned_by_symbol)

    if not linked_transactions:
        return {
            "status": "unavailable",
            "reason": "no_linked_transactions",
            "score": None,
            "symbols": {
                sym: {
                    "action": p["action"],
                    "planned_amount": p["planned_amount"],
                    "executed_amount": None,
                    "timing_delta_pct": None,
                    "size_delta_pct": None,
                    "note": "no_linked_transaction",
                }
                for sym, p in planned_by_symbol.items()
            },
            "completeness_pct": 0.0 if total_planned else 100.0,
            "funding_fidelity_pct": None,
        }

    symbol_results: dict[str, dict] = {}
    matched_count = 0
    for sym, p in planned_by_symbol.items():
        txs = tx_by_symbol.get(sym, [])
        if not txs:
            symbol_results[sym] = {
                "action": p["action"],
                "planned_amount": p["planned_amount"],
                "executed_amount": None,
                "timing_delta_pct": None,
                "size_delta_pct": None,
                "note": "no_linked_transaction",
            }
            continue

        matched_count += 1
        executed_amount = sum(float(t.get("total_amount") or 0.0) for t in txs)
        total_shares = sum(float(t.get("shares") or 0.0) for t in txs)
        fill_price = (
            sum(float(t.get("price_per_share") or 0.0) * float(t.get("shares") or 0.0) for t in txs)
            / total_shares
            if total_shares > 0 else None
        )
        rec_price = recommendation_prices.get(sym)

        timing_delta_pct = (
            round((fill_price - rec_price) / rec_price * 100, 2)
            if rec_price and fill_price else None
        )
        size_delta_pct = (
            round((executed_amount - p["planned_amount"]) / p["planned_amount"] * 100, 2)
            if p["planned_amount"] else None
        )

        symbol_results[sym] = {
            "action": p["action"],
            "planned_amount": p["planned_amount"],
            "executed_amount": round(executed_amount, 2),
            "timing_delta_pct": timing_delta_pct,
            "size_delta_pct": size_delta_pct,
            "note": None,
        }

    completeness_pct = round(100.0 * matched_count / total_planned, 2) if total_planned else 100.0

    funding_planned = {
        sym for sym, p in planned_by_symbol.items() if p.get("execution_role") == ROLE_FUNDING_SOURCE
    }
    if funding_planned:
        funding_matched = sum(1 for sym in funding_planned if tx_by_symbol.get(sym))
        funding_fidelity_pct = round(100.0 * funding_matched / len(funding_planned), 2)
    else:
        funding_fidelity_pct = None  # nothing was planned as a funding source — not applicable

    timing_values = [
        r["timing_delta_pct"] for r in symbol_results.values() if r["timing_delta_pct"] is not None
    ]
    size_values = [
        r["size_delta_pct"] for r in symbol_results.values() if r["size_delta_pct"] is not None
    ]

    components: list[tuple[float, float]] = []
    if timing_values:
        avg_abs_timing = sum(abs(v) for v in timing_values) / len(timing_values)
        components.append((max(0.0, 100.0 - avg_abs_timing * _TIMING_PENALTY_PER_PCT), _COMPONENT_WEIGHT))
    if size_values:
        avg_abs_size = sum(abs(v) for v in size_values) / len(size_values)
        components.append((max(0.0, 100.0 - avg_abs_size * _SIZE_PENALTY_PER_PCT), _COMPONENT_WEIGHT))
    if funding_fidelity_pct is not None:
        components.append((funding_fidelity_pct, _COMPONENT_WEIGHT))
    components.append((completeness_pct, _COMPONENT_WEIGHT))

    total_weight = sum(w for _, w in components)
    composite = round(sum(s * w for s, w in components) / total_weight, 2) if total_weight else None

    is_partial = (
        matched_count < total_planned
        or not timing_values
        or not size_values
        or funding_fidelity_pct is None
    )

    return {
        "status": "partial" if is_partial else "ok",
        "reason": "some_deltas_unmeasurable" if is_partial else None,
        "score": composite,
        "symbols": symbol_results,
        "completeness_pct": completeness_pct,
        "funding_fidelity_pct": funding_fidelity_pct,
    }
