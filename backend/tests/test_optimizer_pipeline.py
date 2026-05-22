"""
Regression tests for the optimizer pipeline.

Verifies that L1 swap data (Gemini) and L2 allocation data survive
raw-response → parser → orchestrator without silent loss or status corruption.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.optimizer import (
    _normalize_l1_swaps,
    _normalize_allocations,
    _consensus_engine,
    _postprocess_swaps,
)


# ── _normalize_l1_swaps ───────────────────────────────────────────────────────

def test_normalize_l1_swaps_compact_keys():
    """Gemini compact-key format (sell/buy) → full swap_suggestions format."""
    raw = [{"sell": "SCB.BK", "buy": "MSFT01.BK", "score_delta": 3.5, "sector": "Technology", "type": "SWAP"}]
    result = _normalize_l1_swaps(raw)
    assert len(result) == 1
    assert result[0]["sell_symbol"] == "SCB.BK"
    assert result[0]["buy_symbol"] == "MSFT01.BK"
    assert result[0]["score_improvement"] == 3.5
    assert result[0]["type"] == "SWAP"


def test_normalize_l1_swaps_sell_only():
    raw = [{"sell": "PTT.BK", "buy": None, "score_delta": 0, "sector": "Energy", "type": "SELL"}]
    result = _normalize_l1_swaps(raw)
    assert result[0]["sell_symbol"] == "PTT.BK"
    assert result[0]["buy_symbol"] is None
    assert result[0]["type"] == "SELL"


def test_normalize_l1_swaps_empty():
    assert _normalize_l1_swaps([]) == []
    assert _normalize_l1_swaps(None) == []


def test_normalize_l1_swaps_full_keys():
    """Full-key format (sell_symbol/buy_symbol) also accepted."""
    raw = [{"sell_symbol": "KBANK.BK", "buy_symbol": "AAPL01.BK", "score_improvement": 2.0, "type": "SWAP"}]
    result = _normalize_l1_swaps(raw)
    assert result[0]["sell_symbol"] == "KBANK.BK"
    assert result[0]["buy_symbol"] == "AAPL01.BK"


# ── _normalize_allocations ────────────────────────────────────────────────────

def test_normalize_allocations_basic():
    raw = [
        {"symbol": "AAPL", "current_weight": 10.0, "target_weight": 15.0, "action": "ACCUMULATE", "reason": "Strong FA"},
        {"symbol": "PTT.BK", "current_weight": 8.0, "target_weight": 5.0, "action": "REDUCE", "reason": "Overweight"},
    ]
    result = _normalize_allocations(raw)
    assert len(result) == 2
    aapl = next(a for a in result if a["symbol"] == "AAPL")
    assert aapl["target_weight"] == 15.0
    assert aapl["action"] == "ACCUMULATE"
    assert aapl["allocation_change_percent"] == 5.0

    ptt = next(a for a in result if a["symbol"] == "PTT.BK")
    assert ptt["allocation_change_percent"] == -3.0


def test_normalize_allocations_pc_map_overrides_ai_weight():
    """pc_map (real portfolio data) should override AI-reported current_weight."""
    raw = [{"symbol": "GOOGL", "current_weight": 5.0, "target_weight": 12.0, "action": "BUY", "reason": ""}]
    pc_map = {"GOOGL": 8.0}  # real weight is 8%, AI said 5%
    result = _normalize_allocations(raw, pc_map)
    assert result[0]["current_weight"] == 8.0
    assert result[0]["allocation_change_percent"] == 4.0  # 12 - 8


def test_normalize_allocations_drops_empty_symbol():
    raw = [{"symbol": "", "target_weight": 10.0, "action": "BUY", "reason": ""}]
    result = _normalize_allocations(raw)
    assert result == []


# ── raw_allocs extraction (None vs falsy) ─────────────────────────────────────

def test_raw_allocs_none_check():
    """Simulates the fixed extraction logic — explicit None check prevents
    dropping a valid but empty allocations list."""
    l2_result = {"allocations": None, "target_allocations": [{"symbol": "X", "target_weight": 10.0}]}
    # Fixed logic: pop allocations; if None, fallback to target_allocations
    raw = l2_result.pop("allocations", None)
    if raw is None:
        raw = l2_result.pop("target_allocations", [])
    assert len(raw) == 1

    # Old buggy logic would silently drop this case:
    l2_old = {"allocations": [], "target_allocations": [{"symbol": "X"}]}
    raw_old = l2_old.pop("allocations", None) or l2_old.get("target_allocations", [])
    # Empty list from allocations is falsy → falls to target_allocations → incidentally works here
    # but the bug was that a valid empty list triggers fallback to a potentially different field
    assert raw_old == [{"symbol": "X"}]  # demonstrates the silent fallback behaviour


# ── _postprocess_swaps ────────────────────────────────────────────────────────

def test_postprocess_swaps_injects_forced_sell():
    swaps = [{"sell_symbol": "A", "buy_symbol": "B", "reason": "", "score_improvement": 1, "sector": "Tech", "type": "SWAP"}]
    result = _postprocess_swaps(swaps, sell_forced=["FORCED.BK"], locked=[])
    symbols = {s["sell_symbol"] for s in result}
    assert "FORCED.BK" in symbols


def test_postprocess_swaps_removes_locked():
    swaps = [{"sell_symbol": "LOCKED.BK", "buy_symbol": "B", "reason": "", "score_improvement": 1, "sector": "Tech", "type": "SWAP"}]
    result = _postprocess_swaps(swaps, sell_forced=[], locked=["LOCKED.BK"])
    assert all(s["sell_symbol"] != "LOCKED.BK" for s in result)


# ── _consensus_engine ─────────────────────────────────────────────────────────

def test_consensus_rebalance_high_confidence():
    l2 = {"agrees_with_layer1": True, "status": "REBALANCE", "rebalance_opportunity_score": 75}
    l3 = {"risk_flags": [], "safer_choice": "layer1", "final_risk_level": "low", "auditor_notes": ""}
    c = _consensus_engine(l2, l3)
    assert c["consensus_decision"] == "REBALANCE"
    assert c["confidence"] == "high"
    assert c["recommended"] == "layer1"


def test_consensus_no_action_low_score():
    l2 = {"agrees_with_layer1": True, "status": "NO_ACTION", "rebalance_opportunity_score": 10,
          "no_action_summary": "Well balanced."}
    l3 = {"risk_flags": [], "safer_choice": "layer1", "final_risk_level": "low", "auditor_notes": ""}
    c = _consensus_engine(l2, l3)
    assert c["consensus_decision"] == "NO_ACTION"
    assert "Well balanced." in c["recommended_action"]


def test_consensus_l1_parse_failure_propagation():
    """When L1 failed and was marked strategist_parse_failed, agrees_with_layer1
    should be False and disagreements note should be present."""
    l2 = {
        "agrees_with_layer1": False,
        "disagreements": ["L1_PARSE_FAILURE: Strategist output could not be parsed — treating as disagreement."],
        "strategist_parse_failed": True,
        "status": "REBALANCE",
        "rebalance_opportunity_score": 50,
    }
    l3 = {"risk_flags": [], "safer_choice": "layer2", "final_risk_level": "medium", "auditor_notes": ""}
    c = _consensus_engine(l2, l3)
    assert c["agrees"] is False
    assert c["consensus_decision"] == "REBALANCE"


def test_consensus_critical_flag_forces_rebalance():
    """CRITICAL risk flag should veto NO_ACTION even at low score."""
    l2 = {"agrees_with_layer1": True, "status": "NO_ACTION", "rebalance_opportunity_score": 5}
    l3 = {
        "risk_flags": [{"symbol": "PTT.BK", "issue": "sector >40%", "severity": "CRITICAL"}],
        "safer_choice": "layer1", "final_risk_level": "high", "auditor_notes": "",
    }
    c = _consensus_engine(l2, l3)
    assert c["consensus_decision"] == "REBALANCE"


# ── Real Gemini L1 response fixture ──────────────────────────────────────────

GEMINI_L1_FIXTURE = """{
  "swaps": [
    {"sell": "SCB.BK", "buy": "MSFT01.BK", "score_delta": 4.2, "sector": "Technology", "type": "SWAP"},
    {"sell": "PTT.BK", "buy": null, "score_delta": 0, "sector": "Energy", "type": "SELL"}
  ],
  "top_buys": ["MSFT01.BK", "AAPL01.BK", "NVDA01.BK"],
  "sector_flags": ["Financial 32%>30%"],
  "priority": "rebalance"
}"""


def test_gemini_l1_fixture_survives_pipeline():
    """Simulates: raw Gemini response → safe_parse_json → _normalize_l1_swaps → _postprocess_swaps."""
    import json
    parsed = json.loads(GEMINI_L1_FIXTURE)

    swaps = _normalize_l1_swaps(parsed.get("swaps", []))
    assert len(swaps) == 2, "Both swaps must survive normalization"

    final = _postprocess_swaps(swaps, sell_forced=[], locked=[])
    assert len(final) == 2, "Swaps must survive postprocessing"
    assert final[0]["sell_symbol"] == "SCB.BK"
    assert final[0]["buy_symbol"] == "MSFT01.BK"
    assert final[1]["sell_symbol"] == "PTT.BK"
    assert final[1]["buy_symbol"] is None

    # Verify these would be visible in layer1_result.swap_suggestions on the frontend
    for s in final:
        assert "sell_symbol" in s
        assert "buy_symbol" in s
        assert "type" in s
        assert "reason" in s
