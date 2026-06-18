"""Regression tests for the presentation-layer noise filter.

Tests validate that micro-rebalance BUY/SELL recommendations are suppressed
to HOLD while larger, actionable trades remain unchanged.

Test matrix (from spec):
  1. Drift = 0.8%, trade value = 15,000  → Rule A fires → HOLD
  2. Drift = 2.5%, trade value = 2,000   → Rule B fires → HOLD
  3. Drift = 2.5%, trade value = 12,000  → neither rule → BUY unchanged
  4. Non-BUY/SELL actions (HOLD, WATCH)  → never touched
"""
import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.noise_filter import apply_noise_filter, DRIFT_THRESHOLD_PCT, MIN_TRADE_VALUE_THB


def _make_result(allocations: list[dict]) -> dict:
    return {"target_allocations": allocations}


def _alloc(action: str, drift: float, amount: float, symbol: str = "TEST") -> dict:
    return {
        "symbol": symbol,
        "action": action,
        "current_weight": 10.0,
        "target_weight": round(10.0 + drift, 2),
        "allocation_change_percent": drift,
        "estimated_amount": amount,
        "reason": "AI-generated reason",
    }


# ── Rule A — Drift below threshold ────────────────────────────────────────────

def test_rule_a_suppresses_buy_with_small_drift():
    """Drift 0.8% < 1.0% threshold → BUY becomes HOLD (Rule A)."""
    result = _make_result([_alloc("BUY", drift=0.8, amount=15_000)])
    apply_noise_filter(result)
    alloc = result["target_allocations"][0]
    assert alloc["action"] == "HOLD"
    assert alloc["noise_suppressed"] is True
    assert alloc["noise_reason"] == "สัดส่วนปัจจุบันใกล้เคียงเป้าหมายแล้ว"


def test_rule_a_suppresses_sell_with_small_drift():
    """Drift -0.5% → SELL becomes HOLD (Rule A applies to SELL too)."""
    result = _make_result([_alloc("SELL", drift=-0.5, amount=-8_000)])
    apply_noise_filter(result)
    alloc = result["target_allocations"][0]
    assert alloc["action"] == "HOLD"
    assert alloc["noise_suppressed"] is True
    assert "สัดส่วน" in alloc["noise_reason"]


# ── Rule B — Trade value below threshold ──────────────────────────────────────

def test_rule_b_suppresses_buy_with_low_trade_value():
    """Drift 2.5% but trade value 2,000 THB < 5,000 THB → HOLD (Rule B)."""
    result = _make_result([_alloc("BUY", drift=2.5, amount=2_000)])
    apply_noise_filter(result)
    alloc = result["target_allocations"][0]
    assert alloc["action"] == "HOLD"
    assert alloc["noise_suppressed"] is True
    assert alloc["noise_reason"] == "มูลค่าที่ต้องปรับมีขนาดเล็กมาก"


def test_rule_b_suppresses_accumulate_with_low_trade_value():
    """ACCUMULATE with tiny trade value → HOLD (Rule B covers ACCUMULATE)."""
    result = _make_result([_alloc("ACCUMULATE", drift=1.5, amount=1_200)])
    apply_noise_filter(result)
    alloc = result["target_allocations"][0]
    assert alloc["action"] == "HOLD"
    assert alloc["noise_suppressed"] is True


# ── Neither rule — recommendation unchanged ───────────────────────────────────

def test_no_suppression_when_both_thresholds_pass():
    """Drift 2.5%, trade value 12,000 THB → BUY remains unchanged."""
    result = _make_result([_alloc("BUY", drift=2.5, amount=12_000)])
    apply_noise_filter(result)
    alloc = result["target_allocations"][0]
    assert alloc["action"] == "BUY"
    assert alloc.get("noise_suppressed") is None
    assert alloc.get("noise_reason") is None


def test_no_suppression_for_hold_and_watch():
    """HOLD and WATCH are never modified by the noise filter."""
    result = _make_result([
        _alloc("HOLD", drift=0.2, amount=500, symbol="AAA"),
        _alloc("WATCH", drift=0.3, amount=400, symbol="BBB"),
    ])
    apply_noise_filter(result)
    for alloc in result["target_allocations"]:
        original_action = alloc["action"]
        assert alloc["action"] == original_action
        assert alloc.get("noise_suppressed") is None


# ── Boundary values ───────────────────────────────────────────────────────────

def test_drift_exactly_at_threshold_is_not_suppressed():
    """Drift == DRIFT_THRESHOLD_PCT (1.0%) is NOT suppressed (strict less-than)."""
    result = _make_result([_alloc("BUY", drift=DRIFT_THRESHOLD_PCT, amount=10_000)])
    apply_noise_filter(result)
    assert result["target_allocations"][0]["action"] == "BUY"


def test_trade_value_exactly_at_threshold_is_not_suppressed():
    """Trade value == MIN_TRADE_VALUE_THB (5,000) is NOT suppressed (strict less-than)."""
    result = _make_result([_alloc("BUY", drift=2.0, amount=MIN_TRADE_VALUE_THB)])
    apply_noise_filter(result)
    assert result["target_allocations"][0]["action"] == "BUY"


def test_rule_a_takes_priority_over_rule_b():
    """When both rules would fire, Rule A is applied first (drift < 1% reason shown)."""
    result = _make_result([_alloc("BUY", drift=0.3, amount=500)])
    apply_noise_filter(result)
    alloc = result["target_allocations"][0]
    assert alloc["action"] == "HOLD"
    assert alloc["noise_reason"] == "สัดส่วนปัจจุบันใกล้เคียงเป้าหมายแล้ว"


def test_mixed_allocations_only_small_ones_suppressed():
    """Only below-threshold allocations are suppressed; others pass through."""
    result = _make_result([
        _alloc("BUY",  drift=0.8, amount=15_000, symbol="KBANK"),   # Rule A → HOLD
        _alloc("BUY",  drift=2.5, amount=2_000,  symbol="GOOGL"),   # Rule B → HOLD
        _alloc("BUY",  drift=2.5, amount=12_000, symbol="AMZN"),    # pass through
        _alloc("SELL", drift=-3.0, amount=-20_000, symbol="TTB"),   # pass through
    ])
    apply_noise_filter(result)
    allocs = {a["symbol"]: a for a in result["target_allocations"]}

    assert allocs["KBANK"]["action"] == "HOLD"
    assert allocs["KBANK"]["noise_reason"] == "สัดส่วนปัจจุบันใกล้เคียงเป้าหมายแล้ว"

    assert allocs["GOOGL"]["action"] == "HOLD"
    assert allocs["GOOGL"]["noise_reason"] == "มูลค่าที่ต้องปรับมีขนาดเล็กมาก"

    assert allocs["AMZN"]["action"] == "BUY"
    assert allocs["AMZN"].get("noise_suppressed") is None

    assert allocs["TTB"]["action"] == "SELL"
    assert allocs["TTB"].get("noise_suppressed") is None


def test_empty_and_missing_target_allocations():
    """apply_noise_filter handles missing or empty target_allocations gracefully."""
    apply_noise_filter({})
    apply_noise_filter({"target_allocations": []})
    apply_noise_filter({"target_allocations": None})
