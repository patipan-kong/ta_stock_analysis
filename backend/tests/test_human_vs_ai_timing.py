"""Unit tests for Phase 4C.6E — Human vs AI Timing Attribution.

All tests use evaluate_override() and build_override_summary() (pure functions).
No DB required.

Coverage:
  1.  No decisions → empty summary
  2.  Single GOOD_OVERRIDE (human return > AI return)
  3.  Single BAD_OVERRIDE (AI return > human return)
  4.  NEUTRAL_OVERRIDE (|delta| < 0.25)
  5.  Win-rate calculation across mixed outcomes
  6.  Added return aggregation (total_added_return_pct)
  7.  Drawdown aggregation (total_saved_drawdown_pct)
  8.  APPROVED decision → override=False, outcome=NOT_OVERRIDE
  9.  Missing AI data (no shadow) → ai_return=None, outcome=UNKNOWN
 10.  Missing human data (no portfolio snaps) → human_return=None, outcome=UNKNOWN
 11.  Mixed override outcomes in one summary
 12.  Summary generation for realistic scenario
"""

import sys
import os
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.human_vs_ai_timing import (
    OverrideAttribution,
    HumanVsAISummary,
    evaluate_override,
    build_override_summary,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _port_snap(date_str: str, total_value: float, inv_return: float | None = None,
               daily_return: float | None = None) -> dict:
    return {
        "snapshot_date": date_str,
        "total_value": total_value,
        "investment_return_pct": inv_return,
        "daily_return_pct": daily_return,
    }


def _shadow_snap(date_str: str, total_value: float, daily_return: float | None = None) -> dict:
    return {
        "snapshot_date": date_str,
        "total_value": total_value,
        "daily_return_pct": daily_return,
    }


def _make_attribution(
    decision_type: str = "REJECTED",
    human_return: float | None = 2.0,
    ai_return: float | None = 1.0,
    human_dd: float | None = 3.0,
    ai_dd: float | None = 5.0,
) -> OverrideAttribution:
    """Build a synthetic attribution directly (bypasses evaluate_override)."""
    is_override = decision_type in {"REJECTED", "MANUAL_OVERRIDE", "PARTIAL_EXECUTION"}
    delta = round(human_return - ai_return, 4) if (human_return is not None and ai_return is not None) else None
    saved_dd = round(ai_dd - human_dd, 4) if (ai_dd is not None and human_dd is not None) else None

    if not is_override:
        outcome = "NOT_OVERRIDE"
    elif delta is None:
        outcome = "UNKNOWN"
    elif abs(delta) < 0.25:
        outcome = "NEUTRAL_OVERRIDE"
    elif delta > 0:
        outcome = "GOOD_OVERRIDE"
    else:
        outcome = "BAD_OVERRIDE"

    return OverrideAttribution(
        recommendation_snapshot_id=1,
        symbol="PORTFOLIO",
        ai_action="REBALANCE",
        human_action=decision_type,
        override=is_override,
        human_return_pct=human_return,
        ai_return_pct=ai_return,
        delta_return_pct=delta,
        human_drawdown_pct=human_dd,
        ai_drawdown_pct=ai_dd,
        saved_drawdown_pct=saved_dd,
        outcome=outcome,
    )


# ── Test 1: No decisions ──────────────────────────────────────────────────────

def test_empty_decisions_returns_zero_summary():
    summary = build_override_summary([])
    assert summary.overrides == 0
    assert summary.good_overrides == 0
    assert summary.bad_overrides == 0
    assert summary.neutral_overrides == 0
    assert summary.override_win_rate == 0.0
    assert summary.total_added_return_pct == 0.0
    assert summary.total_saved_drawdown_pct == 0.0


# ── Test 2: Single GOOD_OVERRIDE ─────────────────────────────────────────────

def test_single_good_override_human_beats_ai():
    # human +3%, AI +1% → delta = +2% → GOOD_OVERRIDE
    port_snaps = [
        _port_snap("2026-06-01", 100_000, inv_return=1.5),
        _port_snap("2026-06-02", 101_500, inv_return=1.5),
    ]
    shadow_snaps = [
        _shadow_snap("2026-06-01", 100_000, daily_return=0.5),
        _shadow_snap("2026-06-02", 100_500, daily_return=0.5),
    ]

    result = evaluate_override(
        decision_type="REJECTED",
        symbol="PTT",
        ai_action="REBALANCE",
        rs_id=1,
        portfolio_snaps=port_snaps,
        shadow_snaps=shadow_snaps,
    )

    assert result.override is True
    assert result.delta_return_pct is not None
    assert result.delta_return_pct > 0
    assert result.outcome == "GOOD_OVERRIDE"


# ── Test 3: Single BAD_OVERRIDE ──────────────────────────────────────────────

def test_single_bad_override_ai_beats_human():
    # human +0.5%, AI +3% → delta = -2.5% → BAD_OVERRIDE
    port_snaps = [_port_snap("2026-06-01", 100_000, inv_return=0.25)]
    shadow_snaps = [_shadow_snap("2026-06-01", 100_000, daily_return=1.5)]

    result = evaluate_override(
        decision_type="REJECTED",
        symbol="PORTFOLIO",
        ai_action="REBALANCE",
        rs_id=2,
        portfolio_snaps=port_snaps,
        shadow_snaps=shadow_snaps,
    )

    assert result.outcome == "BAD_OVERRIDE"
    assert result.delta_return_pct is not None
    assert result.delta_return_pct < 0


# ── Test 4: NEUTRAL_OVERRIDE ──────────────────────────────────────────────────

def test_neutral_override_when_delta_below_threshold():
    # human +1%, AI +1.1% → delta = -0.1% → abs < 0.25 → NEUTRAL
    port_snaps = [_port_snap("2026-06-01", 100_000, inv_return=1.0)]
    shadow_snaps = [_shadow_snap("2026-06-01", 100_000, daily_return=1.1)]

    result = evaluate_override(
        decision_type="MANUAL_OVERRIDE",
        symbol="PORTFOLIO",
        ai_action="REBALANCE",
        rs_id=3,
        portfolio_snaps=port_snaps,
        shadow_snaps=shadow_snaps,
    )

    assert result.outcome == "NEUTRAL_OVERRIDE"
    assert abs(result.delta_return_pct) < 0.25


# ── Test 5: Win-rate calculation ──────────────────────────────────────────────

def test_win_rate_is_good_overrides_over_total():
    attributions = [
        _make_attribution("REJECTED", human_return=3.0, ai_return=1.0),   # GOOD
        _make_attribution("REJECTED", human_return=3.0, ai_return=1.0),   # GOOD
        _make_attribution("REJECTED", human_return=-1.0, ai_return=2.0),  # BAD
    ]
    summary = build_override_summary(attributions)

    assert summary.overrides == 3
    assert summary.good_overrides == 2
    assert summary.bad_overrides == 1
    assert abs(summary.override_win_rate - 66.7) < 0.1


# ── Test 6: Added return aggregation ─────────────────────────────────────────

def test_total_added_return_is_sum_of_deltas():
    # delta: +2, -1, +3 → net = +4
    attributions = [
        _make_attribution("REJECTED", human_return=3.0, ai_return=1.0),   # delta +2
        _make_attribution("REJECTED", human_return=0.0, ai_return=1.0),   # delta -1
        _make_attribution("REJECTED", human_return=4.0, ai_return=1.0),   # delta +3
    ]
    summary = build_override_summary(attributions)

    assert abs(summary.total_added_return_pct - 4.0) < 0.01


# ── Test 7: Drawdown aggregation ──────────────────────────────────────────────

def test_total_saved_drawdown_is_sum_of_saved_drawdowns():
    # saved_dd: +2 (ai_dd=5, human_dd=3), +3 (ai_dd=6, human_dd=3), -1 (ai_dd=2, human_dd=3)
    # net = +4
    attributions = [
        _make_attribution("REJECTED", human_dd=3.0, ai_dd=5.0),   # saved +2
        _make_attribution("REJECTED", human_dd=3.0, ai_dd=6.0),   # saved +3
        _make_attribution("REJECTED", human_dd=3.0, ai_dd=2.0),   # saved -1
    ]
    summary = build_override_summary(attributions)

    assert abs(summary.total_saved_drawdown_pct - 4.0) < 0.01


# ── Test 8: APPROVED decision is not an override ──────────────────────────────

def test_approved_decision_is_not_override():
    port_snaps = [_port_snap("2026-06-01", 100_000, inv_return=2.0)]
    shadow_snaps = [_shadow_snap("2026-06-01", 100_000, daily_return=1.0)]

    result = evaluate_override(
        decision_type="APPROVED",
        symbol="PORTFOLIO",
        ai_action="REBALANCE",
        rs_id=4,
        portfolio_snaps=port_snaps,
        shadow_snaps=shadow_snaps,
    )

    assert result.override is False
    assert result.outcome == "NOT_OVERRIDE"

    # APPROVED decisions should NOT count in override summary
    summary = build_override_summary([result])
    assert summary.overrides == 0
    assert summary.override_win_rate == 0.0


# ── Test 9: Missing AI data (no shadow) ───────────────────────────────────────

def test_missing_ai_data_gives_unknown_outcome():
    port_snaps = [_port_snap("2026-06-01", 100_000, inv_return=2.0)]

    result = evaluate_override(
        decision_type="REJECTED",
        symbol="PORTFOLIO",
        ai_action="UNKNOWN",
        rs_id=5,
        portfolio_snaps=port_snaps,
        shadow_snaps=[],  # no shadow data
    )

    assert result.ai_return_pct is None
    assert result.delta_return_pct is None
    assert result.outcome == "UNKNOWN"


# ── Test 10: Missing human data (no portfolio snaps) ─────────────────────────

def test_missing_human_data_gives_unknown_outcome():
    shadow_snaps = [_shadow_snap("2026-06-01", 100_000, daily_return=1.5)]

    result = evaluate_override(
        decision_type="REJECTED",
        symbol="PORTFOLIO",
        ai_action="REBALANCE",
        rs_id=6,
        portfolio_snaps=[],  # no portfolio data
        shadow_snaps=shadow_snaps,
    )

    assert result.human_return_pct is None
    assert result.delta_return_pct is None
    assert result.outcome == "UNKNOWN"


# ── Test 11: Mixed override outcomes ─────────────────────────────────────────

def test_mixed_outcomes_count_correctly():
    attributions = [
        _make_attribution("APPROVED"),                                # NOT_OVERRIDE
        _make_attribution("REJECTED", human_return=3.0, ai_return=1.0),   # GOOD
        _make_attribution("REJECTED", human_return=-1.0, ai_return=2.0),  # BAD
        _make_attribution("MANUAL_OVERRIDE", human_return=1.05, ai_return=1.0),  # NEUTRAL (delta=0.05)
        _make_attribution("REJECTED", human_return=5.0, ai_return=1.0),   # GOOD
    ]
    summary = build_override_summary(attributions)

    assert summary.overrides == 4          # not counting APPROVED
    assert summary.good_overrides == 2
    assert summary.bad_overrides == 1
    assert summary.neutral_overrides == 1


# ── Test 12: Summary generation ──────────────────────────────────────────────

def test_summary_fields_are_correct_for_realistic_scenario():
    # 3 overrides: 2 good, 1 bad
    # deltas: +5, +3, -2  → total_added = +6
    # saved_dd: +4, +2, -3 → total_saved = +3
    attributions = [
        _make_attribution("REJECTED", human_return=6.0, ai_return=1.0, human_dd=2.0, ai_dd=6.0),
        _make_attribution("REJECTED", human_return=4.0, ai_return=1.0, human_dd=3.0, ai_dd=5.0),
        _make_attribution("REJECTED", human_return=-1.0, ai_return=1.0, human_dd=4.0, ai_dd=1.0),
    ]
    summary = build_override_summary(attributions)

    assert summary.overrides == 3
    assert summary.good_overrides == 2
    assert summary.bad_overrides == 1
    assert summary.neutral_overrides == 0
    assert abs(summary.override_win_rate - 66.7) < 0.1
    assert abs(summary.total_added_return_pct - 6.0) < 0.01
    assert abs(summary.total_saved_drawdown_pct - 3.0) < 0.01
