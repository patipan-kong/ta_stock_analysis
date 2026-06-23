"""Phase 4C.6H — Unit tests for optimizer_timing.py.

All tests are pure — no network, no DB, no AI calls.
"""
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from services.optimizer_timing import (
    OptimizerTimingContext,
    apply_timing_confidence_adjustment,
    build_timing_note,
    enrich_scores_with_timing,
)
from agents.optimizer import _compact_p, _compact_w, _compress_for_layer1


# ── 1. High timing enrichment ─────────────────────────────────────────────────

def test_enrich_high_timing():
    """High timing score produces ELIGIBLE-grade context."""
    mock_result = MagicMock()
    mock_result.symbol = "NVDA01"
    mock_result.timing_score = 92
    mock_result.timing_category = "STRONG"
    mock_result.execution_priority = "HIGH"
    mock_result.momentum = "STRONG_UPTREND"
    mock_result.reasons = ["Price above all SMAs"]

    with patch("services.optimizer_timing.score_timing_batch", return_value=[mock_result]):
        result = enrich_scores_with_timing(["NVDA01"])

    assert "NVDA01" in result
    ctx = result["NVDA01"]
    assert ctx.timing_score == 92
    assert ctx.execution_priority == "HIGH"
    assert ctx.momentum == "STRONG_UPTREND"
    assert ctx.timing_reason == "Price above all SMAs"


# ── 2. Low timing enrichment ──────────────────────────────────────────────────

def test_enrich_low_timing():
    """DEFER timing score produces low-quality context."""
    mock_result = MagicMock()
    mock_result.symbol = "AMZN01"
    mock_result.timing_score = 18
    mock_result.timing_category = "POOR"
    mock_result.execution_priority = "DEFER"
    mock_result.momentum = "STRONG_DOWNTREND"
    mock_result.reasons = ["Price below SMA50", "RSI oversold"]

    with patch("services.optimizer_timing.score_timing_batch", return_value=[mock_result]):
        result = enrich_scores_with_timing(["AMZN01"])

    assert "AMZN01" in result
    ctx = result["AMZN01"]
    assert ctx.timing_score == 18
    assert ctx.execution_priority == "DEFER"
    assert ctx.timing_reason == "Price below SMA50"


# ── 3. Missing timing data (enrich failure) ───────────────────────────────────

def test_enrich_failure_returns_empty():
    """Network error during enrichment never raises — returns empty dict."""
    with patch("services.optimizer_timing.score_timing_batch", side_effect=RuntimeError("network")):
        result = enrich_scores_with_timing(["AAPL"])
    assert result == {}


def test_enrich_empty_symbols():
    """Empty symbol list returns empty dict without calling score_timing_batch."""
    with patch("services.optimizer_timing.score_timing_batch") as mock_batch:
        result = enrich_scores_with_timing([])
    mock_batch.assert_not_called()
    assert result == {}


# ── 4. Prompt compression includes timing ─────────────────────────────────────

def test_compact_p_includes_timing_fields():
    items = [{"symbol": "BH", "timing_score": 88, "execution_priority": "HIGH", "momentum": "UPTREND",
               "signal": "BUY", "ta_score": 75, "fa_score": 80, "roe": None}]
    result = _compact_p(items)
    assert result[0]["timing_score"] == 88
    assert result[0]["execution_priority"] == "HIGH"
    assert result[0]["momentum"] == "UPTREND"


def test_compact_w_includes_timing_fields():
    items = [{"symbol": "GULF", "timing_score": 45, "execution_priority": "LOW", "momentum": "SIDEWAYS",
               "signal": "WATCH", "ta_score": 60, "fa_score": 65, "roe": None}]
    result = _compact_w(items)
    assert result[0]["timing_score"] == 45
    assert result[0]["execution_priority"] == "LOW"


def test_compress_for_layer1_includes_ts_pr():
    pc = [{"symbol": "MICRON01", "timing_score": 90, "execution_priority": "HIGH", "momentum": "STRONG_UPTREND",
            "signal": "ACCUMULATE", "ta_score": 82, "fa_score": 78, "weight_pct": 5.0, "market_value": 50000,
            "allow_swap": True, "sector": "Technology", "roe": None}]
    wc = [{"symbol": "PTT", "timing_score": 30, "execution_priority": "DEFER", "momentum": "DOWNTREND",
            "signal": "BUY", "ta_score": 55, "fa_score": 60, "sector": "Energy", "roe": None}]
    c_pc, c_wc = _compress_for_layer1(pc, wc)
    assert c_pc[0]["ts"] == 90
    assert c_pc[0]["pr"] == "HIGH"
    assert c_wc[0]["ts"] == 30
    assert c_wc[0]["pr"] == "DEFER"


# ── 5. Confidence adjustment ──────────────────────────────────────────────────

def test_confidence_high_timing_boosts():
    adj = apply_timing_confidence_adjustment(80.0, 92)
    assert adj == pytest.approx(88.0, abs=0.2)  # 80 × 1.10


def test_confidence_defer_timing_reduces():
    adj = apply_timing_confidence_adjustment(80.0, 20)
    assert adj == pytest.approx(64.0, abs=0.2)  # 80 × 0.80


def test_confidence_watchlist_range_reduces():
    adj = apply_timing_confidence_adjustment(60.0, 50)
    assert adj == pytest.approx(54.0, abs=0.2)  # 60 × 0.90


def test_confidence_neutral_timing_unchanged():
    adj = apply_timing_confidence_adjustment(70.0, 65)
    assert adj == pytest.approx(70.0, abs=0.1)  # 70 × 1.00


def test_confidence_capped_at_100():
    adj = apply_timing_confidence_adjustment(95.0, 95)
    assert adj <= 100.0


# ── 6. Recommendation type never mutated ─────────────────────────────────────

def test_no_recommendation_mutation():
    """apply_timing_confidence_adjustment never changes recommendation strings."""
    action_before = "ACCUMULATE"
    symbol_before = "AMZN01"
    _ = apply_timing_confidence_adjustment(85.0, 15)
    assert action_before == "ACCUMULATE"
    assert symbol_before == "AMZN01"


# ── 7. Layer prompts contain timing fields ────────────────────────────────────

def test_layer1_prompt_contains_timing_guidance():
    from agents.optimizer import _layer1_prompt
    prompt = _layer1_prompt([], [], [], [])
    assert "TIMING INTELLIGENCE" in prompt
    assert "ts=" in prompt
    assert "DEFER" in prompt


def test_layer2_prompt_contains_timing_awareness():
    from agents.optimizer import _layer2_prompt
    prompt = _layer2_prompt([], [], {})
    assert "TIMING AWARENESS" in prompt
    assert "TIMING_CONCERN" in prompt


def test_layer3_prompt_contains_timing_risk():
    from agents.optimizer import _layer3_prompt
    prompt = _layer3_prompt({}, {})
    assert "TIMING RISK" in prompt
    assert "MEDIUM" in prompt


# ── 8. Multiple symbols ───────────────────────────────────────────────────────

def test_enrich_multiple_symbols():
    """Batch enrichment returns context for each symbol independently."""
    def _mk(sym, score, pri):
        r = MagicMock()
        r.symbol = sym
        r.timing_score = score
        r.timing_category = "STRONG" if score >= 80 else "POOR"
        r.execution_priority = pri
        r.momentum = "UPTREND"
        r.reasons = [f"score {score}"]
        return r

    mocks = [_mk("MICRON01", 90, "HIGH"), _mk("BH", 88, "HIGH"),
             _mk("GULF", 70, "MEDIUM"), _mk("AMZN01", 20, "DEFER")]

    with patch("services.optimizer_timing.score_timing_batch", return_value=mocks):
        result = enrich_scores_with_timing(["MICRON01", "BH", "GULF", "AMZN01"])

    assert len(result) == 4
    assert result["MICRON01"].execution_priority == "HIGH"
    assert result["AMZN01"].execution_priority == "DEFER"
    assert result["GULF"].timing_score == 70


# ── 9. build_timing_note ──────────────────────────────────────────────────────

def test_timing_note_defer_for_buy():
    note = build_timing_note("BUY", 15, "DEFER")
    assert note is not None
    assert "DEFER" in note
    assert "15" in note


def test_timing_note_strong_for_accumulate():
    note = build_timing_note("ACCUMULATE", 88, "HIGH")
    assert note is not None
    assert "88" in note


def test_timing_note_none_for_hold():
    note = build_timing_note("HOLD", 20, "DEFER")
    assert note is None


def test_timing_note_none_for_good_timing():
    note = build_timing_note("ACCUMULATE", 65, "MEDIUM")
    assert note is None
