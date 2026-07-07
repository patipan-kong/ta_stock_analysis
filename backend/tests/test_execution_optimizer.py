"""Unit tests for services/optimizer/execution_optimizer.py.

Pure module — no DB, no AI. Covers the founding BH/CENTEL example from
OPTIMIZER_PHILOSOPHY.md and the conceptual points clarified during design
review: Reason/Necessity/Execution Role/Execution State as independent
axes, least-distortion funding-candidate ordering, and deterministic
tie-breaking.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.optimizer.execution_optimizer import (  # noqa: E402
    FundingCandidate,
    classify_reason,
    necessity_for,
    resolve_funding_gap,
    REASON_MANDATORY_RISK_REDUCTION,
    REASON_POLICY_ENFORCEMENT,
    REASON_PORTFOLIO_IMPROVEMENT,
    NECESSITY_NECESSARY,
    NECESSITY_DISCRETIONARY,
    ROLE_STANDALONE,
    ROLE_FUNDING_SOURCE,
    ROLE_NOT_NEEDED_TODAY,
    STATE_FULL,
    STATE_SCALED,
    STATE_DEFERRED,
)


# ── classify_reason / necessity_for ─────────────────────────────────────────

def test_sell_is_always_mandatory_risk_reduction():
    assert classify_reason("BH", "SELL", "Consumer", []) == REASON_MANDATORY_RISK_REDUCTION


def test_reduce_is_portfolio_improvement_by_default():
    assert classify_reason("BH", "REDUCE", "Consumer", []) == REASON_PORTFOLIO_IMPROVEMENT


def test_reduce_in_breached_sector_is_policy_enforcement():
    violations = ["SECTOR_BREACH: Consumer at 45.2% exceeds 40% resolved sector limit"]
    assert classify_reason("BH", "REDUCE", "Consumer", violations) == REASON_POLICY_ENFORCEMENT


def test_reduce_in_unrelated_sector_is_not_policy_enforcement():
    violations = ["SECTOR_BREACH: Financial at 45.2% exceeds 40% resolved sector limit"]
    assert classify_reason("BH", "REDUCE", "Consumer", violations) == REASON_PORTFOLIO_IMPROVEMENT


def test_reduce_with_live_position_breach_is_policy_enforcement():
    """CONCENTRATION_BREACH names the symbol, not the sector — classify_reason
    must catch this shape too, not just SECTOR_BREACH. This is the gap found
    during design review: a live single-position breach was silently
    downgraded to discretionary Portfolio Improvement and could be deferred
    whenever funding happened to be sufficient."""
    violations = ["CONCENTRATION_BREACH: KBANK at 12.5% exceeds 10% single-position policy limit"]
    assert classify_reason("KBANK", "REDUCE", "Financial", violations) == REASON_POLICY_ENFORCEMENT


def test_reduce_with_unrelated_position_breach_is_not_policy_enforcement():
    violations = ["CONCENTRATION_BREACH: PTT at 12.5% exceeds 10% single-position policy limit"]
    assert classify_reason("KBANK", "REDUCE", "Financial", violations) == REASON_PORTFOLIO_IMPROVEMENT


def test_necessity_mapping():
    assert necessity_for(REASON_MANDATORY_RISK_REDUCTION) == NECESSITY_NECESSARY
    assert necessity_for(REASON_POLICY_ENFORCEMENT) == NECESSITY_NECESSARY
    assert necessity_for(REASON_PORTFOLIO_IMPROVEMENT) == NECESSITY_DISCRETIONARY


# ── The founding example: cash already covers the buy, funding not needed ──

def test_founding_example_bh_centel_defers_unnecessary_reduce():
    """Cash 120k, need 30k (CENTEL) — REDUCE BH 95k must NOT ship."""
    candidates = [FundingCandidate(symbol="BH", action="REDUCE", sector="Consumer", full_amount=95_000)]
    result = resolve_funding_gap(candidates, cash_available=120_000, total_buy_deployment=30_000)

    assert result.funding_gap == 0
    assert len(result.trades) == 1
    bh = result.trades[0]
    assert bh.necessity == NECESSITY_DISCRETIONARY
    assert bh.execution_role == ROLE_NOT_NEEDED_TODAY
    assert bh.execution_state == STATE_DEFERRED
    assert bh.executed_amount == 0
    assert "no funding need" in bh.note.lower()
    # Idle cash after: 120k cash - 30k deployed, nothing released
    assert result.idle_cash_after == 90_000


# ── Live position breach ships regardless of cash (the design-review fix) ──

def test_position_breach_reduce_ships_despite_sufficient_cash():
    """KBANK is over its single-position limit. Cash already covers today's
    buys (no funding gap) — before the fix, KBANK's REDUCE would have been
    misclassified as discretionary Portfolio Improvement and deferred to
    'Not Executing Today' simply because no funding was needed. A live
    policy breach must ship regardless of cash position (§9)."""
    violations = ["CONCENTRATION_BREACH: KBANK at 12.5% exceeds 10% single-position policy limit"]
    candidates = [FundingCandidate(symbol="KBANK", action="REDUCE", sector="Financial", full_amount=40_000)]
    result = resolve_funding_gap(
        candidates, cash_available=120_000, total_buy_deployment=30_000, violations=violations,
    )

    assert result.funding_gap == 0
    kbank = result.trades[0]
    assert kbank.reason == REASON_POLICY_ENFORCEMENT
    assert kbank.necessity == NECESSITY_NECESSARY
    assert kbank.execution_role == ROLE_STANDALONE
    assert kbank.execution_state == STATE_FULL
    assert kbank.executed_amount == 40_000


# ── Necessary trades always ship in full, never scaled ─────────────────────

def test_necessary_sell_ships_in_full_even_when_far_exceeding_gap():
    candidates = [FundingCandidate(symbol="XYZ", action="SELL", sector="Energy", full_amount=300_000)]
    result = resolve_funding_gap(candidates, cash_available=0, total_buy_deployment=30_000)

    xyz = result.trades[0]
    assert xyz.necessity == NECESSITY_NECESSARY
    assert xyz.execution_role == ROLE_STANDALONE
    assert xyz.execution_state == STATE_FULL
    assert xyz.executed_amount == 300_000
    # Surplus becomes idle cash, tolerated per Priority 7 — never scaled down.
    assert result.idle_cash_after == 270_000


# ── Least-distortion ordering: small, well-fitting REDUCE beats a huge one ─

def test_prefers_smallest_sufficient_discretionary_candidate():
    """gap=30k. A REDUCE=300k (would be 90% distorted if cut to 30k) vs.
    B REDUCE=35k (only ~14% distorted). B should be the one scaled; A stays
    untouched — matches the design conversation's worked example exactly.
    """
    candidates = [
        FundingCandidate(symbol="A", action="REDUCE", sector="Energy", full_amount=300_000),
        FundingCandidate(symbol="B", action="REDUCE", sector="Consumer", full_amount=35_000),
    ]
    result = resolve_funding_gap(candidates, cash_available=0, total_buy_deployment=30_000)

    by_symbol = {t.symbol: t for t in result.trades}
    assert by_symbol["B"].execution_state == STATE_SCALED
    assert by_symbol["B"].execution_role == ROLE_FUNDING_SOURCE
    assert by_symbol["B"].executed_amount == 30_000
    assert by_symbol["A"].execution_state == STATE_DEFERRED
    assert by_symbol["A"].executed_amount == 0


def test_ascending_walk_uses_multiple_small_candidates_before_cutting_one():
    """gap=30k. C1=5k, C2=28k, C3=300k. Ascending walk: C1 full (5k),
    then C2 alone would total 33k > 30k gap, so C2 becomes the scaled one
    (25k of its own 28k) — C3 is never touched.
    """
    candidates = [
        FundingCandidate(symbol="C1", action="REDUCE", full_amount=5_000),
        FundingCandidate(symbol="C2", action="REDUCE", full_amount=28_000),
        FundingCandidate(symbol="C3", action="REDUCE", full_amount=300_000),
    ]
    result = resolve_funding_gap(candidates, cash_available=0, total_buy_deployment=30_000)
    by_symbol = {t.symbol: t for t in result.trades}

    assert by_symbol["C1"].execution_state == STATE_FULL
    assert by_symbol["C1"].executed_amount == 5_000
    assert by_symbol["C2"].execution_state == STATE_SCALED
    assert by_symbol["C2"].executed_amount == 25_000
    assert by_symbol["C3"].execution_state == STATE_DEFERRED
    assert by_symbol["C3"].executed_amount == 0


# ── Deterministic tie-break: exact ties resolved by symbol ──────────────────

def test_tie_break_is_deterministic_across_runs():
    candidates = [
        FundingCandidate(symbol="ZZZ", action="REDUCE", full_amount=50_000),
        FundingCandidate(symbol="AAA", action="REDUCE", full_amount=50_000),
    ]
    r1 = resolve_funding_gap(candidates, cash_available=0, total_buy_deployment=20_000)
    r2 = resolve_funding_gap(list(reversed(candidates)), cash_available=0, total_buy_deployment=20_000)

    # Same result regardless of input order (Invariant 3).
    state1 = {t.symbol: (t.execution_state, t.executed_amount) for t in r1.trades}
    state2 = {t.symbol: (t.execution_state, t.executed_amount) for t in r2.trades}
    assert state1 == state2
    # AAA sorts first alphabetically at an exact tie — it's the one scaled.
    assert state1["AAA"][0] == STATE_SCALED
    assert state1["ZZZ"][0] == STATE_DEFERRED


# ── No candidates / no gap edge cases ───────────────────────────────────────

def test_no_candidates_no_buys():
    result = resolve_funding_gap([], cash_available=50_000, total_buy_deployment=0)
    assert result.funding_gap == 0
    assert result.trades == []
    assert result.idle_cash_after == 50_000


def test_insufficient_funding_reports_negative_idle_cash():
    """Even every discretionary candidate executed in full can't close the
    gap — the shortfall surfaces as negative idle cash (existing INSUFFICIENT
    handling upstream), not as an inflated/fabricated release."""
    candidates = [FundingCandidate(symbol="A", action="REDUCE", full_amount=10_000)]
    result = resolve_funding_gap(candidates, cash_available=0, total_buy_deployment=50_000)
    a = result.trades[0]
    assert a.execution_state == STATE_FULL
    assert a.executed_amount == 10_000
    assert result.idle_cash_after == -40_000
