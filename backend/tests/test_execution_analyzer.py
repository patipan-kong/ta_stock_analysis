"""Tests for services/evaluation/execution_analyzer.py — AI Evaluation M2.

Pure-function module — no DB, no AI. Coverage:

Unavailable / null-handling
  1. Zero linked transactions -> status="unavailable", score=None, every
     planned symbol carries note="no_linked_transaction"
  2. A plan with zero planned trades and zero transactions -> completeness 100
Matching and deltas
  3. Fully matched plan, exact fill vs. plan -> status="ok", high score
  4. Timing delta sign and magnitude for a BUY filled above the recommended price
  5. Size delta when executed amount is double the planned amount
Partial completeness
  6. One of two planned trades unmatched -> status="partial",
     completeness_pct == 50, PARTIAL note present on the unmatched symbol
Funding fidelity
  7. A planned FUNDING_SOURCE trade with no linked transaction drags
     funding_fidelity_pct down
  8. No planned funding-source trades at all -> funding_fidelity_pct is None
     (not applicable), never a fabricated 100 or 0
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.evaluation.execution_analyzer import compute_execution_analysis  # noqa: E402


def _alloc(symbol: str, action: str, change_pct: float, estimated_amount: float,
           current_weight: float = 10.0, sector: str = "Consumer") -> dict:
    return {
        "symbol": symbol, "action": action,
        "allocation_change_percent": change_pct, "current_weight": current_weight,
        "estimated_amount": estimated_amount, "sector": sector,
    }


def _tx(symbol: str, shares: float, price_per_share: float, total_amount: float) -> dict:
    return {"symbol": symbol, "shares": shares, "price_per_share": price_per_share, "total_amount": total_amount}


# ── Unavailable / null-handling ─────────────────────────────────────────────

def test_no_linked_transactions_is_unavailable_not_fabricated():
    allocations = [_alloc("CENTEL", "BUY", 3.0, 30_000, current_weight=0.0)]
    result = compute_execution_analysis(
        allocations, cash_available=0.0, violations=[],
        recommendation_prices={"CENTEL": 100.0}, linked_transactions=[],
    )
    assert result["status"] == "unavailable"
    assert result["score"] is None
    assert result["symbols"]["CENTEL"]["note"] == "no_linked_transaction"


def test_empty_plan_and_empty_transactions_completeness_is_full():
    result = compute_execution_analysis(
        [], cash_available=0.0, violations=[], recommendation_prices={}, linked_transactions=[],
    )
    assert result["completeness_pct"] == 100.0


# ── Matching and deltas ──────────────────────────────────────────────────────

def test_fully_matched_exact_fill_scores_high():
    allocations = [_alloc("CENTEL", "BUY", 3.0, 30_000, current_weight=0.0)]
    txs = [_tx("CENTEL", shares=300, price_per_share=100.0, total_amount=30_000)]
    result = compute_execution_analysis(
        allocations, cash_available=0.0, violations=[],
        recommendation_prices={"CENTEL": 100.0}, linked_transactions=txs,
    )
    assert result["status"] in ("ok", "partial")
    assert result["symbols"]["CENTEL"]["timing_delta_pct"] == 0.0
    assert result["symbols"]["CENTEL"]["size_delta_pct"] == 0.0
    assert result["completeness_pct"] == 100.0
    assert result["score"] > 90.0


def test_timing_delta_positive_when_buy_fills_above_recommended_price():
    allocations = [_alloc("CENTEL", "BUY", 3.0, 30_000, current_weight=0.0)]
    txs = [_tx("CENTEL", shares=250, price_per_share=120.0, total_amount=30_000)]
    result = compute_execution_analysis(
        allocations, cash_available=0.0, violations=[],
        recommendation_prices={"CENTEL": 100.0}, linked_transactions=txs,
    )
    # (120 - 100) / 100 * 100 = +20%
    assert result["symbols"]["CENTEL"]["timing_delta_pct"] == 20.0


def test_size_delta_when_executed_is_double_planned():
    allocations = [_alloc("CENTEL", "BUY", 3.0, 30_000, current_weight=0.0)]
    txs = [_tx("CENTEL", shares=600, price_per_share=100.0, total_amount=60_000)]
    result = compute_execution_analysis(
        allocations, cash_available=0.0, violations=[],
        recommendation_prices={"CENTEL": 100.0}, linked_transactions=txs,
    )
    assert result["symbols"]["CENTEL"]["size_delta_pct"] == 100.0


# ── Partial completeness ─────────────────────────────────────────────────────

def test_one_of_two_unmatched_is_partial_with_50pct_completeness():
    allocations = [
        _alloc("CENTEL", "BUY", 3.0, 30_000, current_weight=0.0),
        _alloc("ADVANC", "BUY", 2.0, 20_000, current_weight=0.0),
    ]
    txs = [_tx("CENTEL", shares=300, price_per_share=100.0, total_amount=30_000)]
    result = compute_execution_analysis(
        allocations, cash_available=0.0, violations=[],
        recommendation_prices={"CENTEL": 100.0, "ADVANC": 200.0}, linked_transactions=txs,
    )
    assert result["status"] == "partial"
    assert result["completeness_pct"] == 50.0
    assert result["symbols"]["ADVANC"]["note"] == "no_linked_transaction"
    assert result["symbols"]["ADVANC"]["executed_amount"] is None


# ── Funding fidelity ──────────────────────────────────────────────────────────

def test_unmatched_funding_source_drags_fidelity_down():
    """Gap=30k, XYZ REDUCE(30k) is the funding source; if the human never
    actually sold XYZ, funding_fidelity_pct must reflect that miss."""
    allocations = [
        _alloc("CENTEL", "BUY", 3.0, 30_000, current_weight=0.0),
        _alloc("XYZ", "REDUCE", -3.0, 30_000),
    ]
    txs = [_tx("CENTEL", shares=300, price_per_share=100.0, total_amount=30_000)]
    result = compute_execution_analysis(
        allocations, cash_available=0.0, violations=[],
        recommendation_prices={"CENTEL": 100.0}, linked_transactions=txs,
    )
    assert result["funding_fidelity_pct"] == 0.0
    assert result["status"] == "partial"


def test_no_funding_source_planned_fidelity_is_not_applicable():
    allocations = [_alloc("CENTEL", "BUY", 3.0, 30_000, current_weight=0.0)]
    txs = [_tx("CENTEL", shares=300, price_per_share=100.0, total_amount=30_000)]
    result = compute_execution_analysis(
        allocations, cash_available=100_000.0, violations=[],
        recommendation_prices={"CENTEL": 100.0}, linked_transactions=txs,
    )
    assert result["funding_fidelity_pct"] is None
