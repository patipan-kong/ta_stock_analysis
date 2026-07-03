"""Pure deterministic helper — derives an action summary from target_allocations.

No AI calls, no DB access, no side effects.
"""
from __future__ import annotations

from typing import Any


def build_action_summary(target_allocations: list[dict[str, Any]]) -> dict:
    """Classify each allocation into sell / reduce / accumulate / new_position / hold.

    Classification rules
    --------------------
    SELL        action == "SELL"
    REDUCE      action == "REDUCE"
    ACCUMULATE  action in ("BUY", "ACCUMULATE") and current_weight > 0
    NEW_POSITION action in ("BUY", "ACCUMULATE") and current_weight == 0
    HOLD        action == "HOLD"

    Noise-suppressed entries, drift-tolerant entries (deferred by the
    stabilization layer), and blank symbols are silently skipped.
    Pure HOLD rows with negligible change (< 0.5 pp) are also skipped to keep
    the output clean.

    Returns
    -------
    {
      "sell":         [{"symbol": ..., "allocation_change_percent": ..., "timing_score": ...}, ...],
      "reduce":       [...],
      "accumulate":   [...],
      "new_position": [...],
      "hold":         [...],
    }
    Each entry always has "symbol" and "allocation_change_percent".
    "timing_score" is included only when present on the source allocation.
    """
    sell: list[dict] = []
    reduce_: list[dict] = []
    accumulate: list[dict] = []
    new_position: list[dict] = []
    hold: list[dict] = []

    for a in (target_allocations or []):
        symbol = (a.get("symbol") or "").strip()
        if not symbol:
            continue
        if a.get("noise_suppressed") or a.get("within_drift_tolerance"):
            continue

        action = (a.get("action") or "").upper()
        change = float(a.get("allocation_change_percent") or 0.0)
        current_weight = float(a.get("current_weight") or 0.0)

        entry: dict[str, Any] = {
            "symbol": symbol,
            "allocation_change_percent": round(change, 1),
        }
        timing_score = a.get("timing_score")
        if timing_score is not None:
            entry["timing_score"] = timing_score

        if action == "SELL":
            sell.append(entry)
        elif action == "REDUCE":
            reduce_.append(entry)
        elif action in ("BUY", "ACCUMULATE"):
            if current_weight > 0:
                accumulate.append(entry)
            else:
                new_position.append(entry)
        elif action == "HOLD":
            if abs(change) >= 0.5:
                hold.append(entry)
        # WATCH / unknown — ignored in summary

    # Sort each bucket by absolute change descending (most impactful first)
    for bucket in (sell, reduce_, accumulate, new_position):
        bucket.sort(key=lambda x: abs(x["allocation_change_percent"]), reverse=True)

    return {
        "sell": sell,
        "reduce": reduce_,
        "accumulate": accumulate,
        "new_position": new_position,
        "hold": hold,
    }
