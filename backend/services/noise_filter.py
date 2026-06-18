"""Presentation-layer noise filter for optimizer recommendations.

Converts micro-rebalance BUY/SELL/ACCUMULATE/REDUCE actions to HOLD when the
recommended change is too small to be meaningful for a real investor.

Applied to the HTTP response only — DB records (history, signal history,
recommendation snapshots) retain the unfiltered optimizer output.
"""
from __future__ import annotations

DRIFT_THRESHOLD_PCT = 1.0   # Rule A: abs(target_weight - current_weight) < 1.0%
MIN_TRADE_VALUE_THB = 5000  # Rule B: abs(estimated_amount) < 5,000 THB

_SUPPRESSIBLE = {"BUY", "SELL", "ACCUMULATE", "REDUCE"}


def apply_noise_filter(result: dict) -> dict:
    """Suppress micro-rebalance actions in target_allocations in-place.

    Rule A — drift < DRIFT_THRESHOLD_PCT: position already close enough to target.
    Rule B — trade value < MIN_TRADE_VALUE_THB: trade too small to execute.
    If either rule fires, action is set to HOLD with a Thai explanation.

    Returns the same dict (mutated) for convenience.
    """
    for alloc in result.get("target_allocations") or []:
        action = (alloc.get("action") or "").upper()
        if action not in _SUPPRESSIBLE:
            continue

        drift = abs(alloc.get("allocation_change_percent") or 0)
        trade_val = abs(alloc.get("estimated_amount") or 0)

        if drift < DRIFT_THRESHOLD_PCT:
            alloc["action"] = "HOLD"
            alloc["noise_suppressed"] = True
            alloc["noise_reason"] = "สัดส่วนปัจจุบันใกล้เคียงเป้าหมายแล้ว"
        elif trade_val < MIN_TRADE_VALUE_THB:
            alloc["action"] = "HOLD"
            alloc["noise_suppressed"] = True
            alloc["noise_reason"] = "มูลค่าที่ต้องปรับมีขนาดเล็กมาก"

    return result
