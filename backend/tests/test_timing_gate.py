"""Phase 4C.6G.1 — Unit tests for timing_gate.py.

All tests are pure — no network, no DB.
"""
import pytest

from services.timing_gate import apply_timing_gate, apply_timing_gate_batch


# ── 1. Eligible: score >= 80 ──────────────────────────────────────────────────

def test_eligible_high_score():
    r = apply_timing_gate("NVDA", 85, "HIGH")
    assert r.status == "ELIGIBLE"
    assert r.symbol == "NVDA"
    assert "85" in r.reason


def test_eligible_score_at_60():
    r = apply_timing_gate("AAPL", 60, "MEDIUM")
    assert r.status == "ELIGIBLE"


def test_eligible_score_at_79():
    r = apply_timing_gate("MSFT", 79, "MEDIUM")
    assert r.status == "ELIGIBLE"


# ── 2. Watchlist: score 40-59 ─────────────────────────────────────────────────

def test_watchlist_score_at_55():
    r = apply_timing_gate("BH", 55, "LOW")
    assert r.status == "WATCHLIST"
    assert "55" in r.reason


def test_watchlist_score_at_40():
    r = apply_timing_gate("GULF", 40, "LOW")
    assert r.status == "WATCHLIST"


def test_watchlist_score_at_59():
    r = apply_timing_gate("SCCC", 59, "LOW")
    assert r.status == "WATCHLIST"


# ── 3. Excluded: score < 40 ───────────────────────────────────────────────────

def test_excluded_score_below_40():
    r = apply_timing_gate("AMZN01", 20, "DEFER")
    assert r.status == "EXCLUDED"


def test_excluded_score_at_39():
    r = apply_timing_gate("SYM", 39, "LOW")
    assert r.status == "EXCLUDED"
    assert "39" in r.reason


def test_excluded_score_zero():
    r = apply_timing_gate("NOSIG", 0, "DEFER")
    assert r.status == "EXCLUDED"


# ── 4. DEFER overrides score ──────────────────────────────────────────────────

def test_defer_overrides_high_score():
    """Priority DEFER should exclude even if timing_score >= 60."""
    r = apply_timing_gate("WEIRD", 75, "DEFER")
    assert r.status == "EXCLUDED"
    assert "DEFER" in r.reason


def test_defer_overrides_watchlist_score():
    r = apply_timing_gate("SYM2", 50, "DEFER")
    assert r.status == "EXCLUDED"
    assert "DEFER" in r.reason


# ── 5. TimingGateResult fields ────────────────────────────────────────────────

def test_result_preserves_inputs():
    r = apply_timing_gate("NVDA01", 90, "HIGH")
    assert r.symbol == "NVDA01"
    assert r.timing_score == 90
    assert r.execution_priority == "HIGH"
    assert isinstance(r.reason, str)
    assert len(r.reason) > 0


# ── 6. Batch function ─────────────────────────────────────────────────────────

def test_batch_mixed_basket():
    """Mixed basket: eligible, watchlist, excluded."""
    class _FakeTimingResult:
        def __init__(self, symbol, score, priority):
            self.symbol = symbol
            self.timing_score = score
            self.execution_priority = priority

    inputs = [
        _FakeTimingResult("MICRON01", 90, "HIGH"),
        _FakeTimingResult("BH",       90, "HIGH"),
        _FakeTimingResult("GULF",     70, "MEDIUM"),
        _FakeTimingResult("AMZN01",   20, "DEFER"),
    ]
    results = apply_timing_gate_batch(inputs)
    assert len(results) == 4

    statuses = {r.symbol: r.status for r in results}
    assert statuses["MICRON01"] == "ELIGIBLE"
    assert statuses["BH"]       == "ELIGIBLE"
    assert statuses["GULF"]     == "ELIGIBLE"
    assert statuses["AMZN01"]   == "EXCLUDED"


def test_batch_empty():
    results = apply_timing_gate_batch([])
    assert results == []


# ── 7. Watchlist timing multiplier boundary ───────────────────────────────────

def test_watchlist_boundary_at_40():
    r = apply_timing_gate("X", 40, "LOW")
    assert r.status == "WATCHLIST"


def test_excluded_boundary_at_39():
    r = apply_timing_gate("X", 39, "LOW")
    assert r.status == "EXCLUDED"
