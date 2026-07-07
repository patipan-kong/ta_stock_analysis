"""Tests for services/evaluation/verdict_composer.py — AI Evaluation M3.

Coverage
--------
letter_grade
  1. None score -> unavailable
  2. score present but n < min_n -> insufficient_evidence
  3. score + sufficient n -> correct letter at threshold boundaries

compose_scorecard_verdict — all four branches, EN + TH present
  4. ai_ahead
  5. human_ahead
  6. tie (within tie_band_pct)
  7. insufficient_evidence (gap_b is None)
  8. insufficient_evidence (gap_b_n below min_n_win_rate)

compose_report_card_verdict
  9. plan graded, no horizon matured yet -> plan-only sentence
  10. plan + matured horizon, beat benchmark -> "worked" phrasing
  11. plan + matured horizon, trailed benchmark -> "trailed" phrasing

compose_gap_interpretation — AI Evaluation M6
  12. value None -> "not enough history" branch
  13. gap_a within tie band -> near-zero / "not earning its keep" branch
  14. gap_a positive, outside tie band -> "price of practical execution"
  15. gap_a negative, outside tie band -> "check the belief engine"
  16. gap_b positive/negative/tie branches produce distinct, non-empty text

compose_attribution_verdict — AI Evaluation M6
  17. missing actual/benchmark -> insufficient-evidence sentence
  18. all effects None -> "not yet measurable" sentence
  19. dominant effect (largest |value|) is named in the sentence
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.evaluation.verdict_composer import (  # noqa: E402
    compose_attribution_verdict,
    compose_gap_interpretation,
    compose_report_card_verdict,
    compose_scorecard_verdict,
    letter_grade,
)


def test_letter_grade_none_score_is_unavailable():
    result = letter_grade(None, n=20, min_n=8)
    assert result == {"status": "unavailable", "letter": None, "n": 20}


def test_letter_grade_below_min_n_is_insufficient_evidence():
    result = letter_grade(95.0, n=3, min_n=8)
    assert result["status"] == "insufficient_evidence"
    assert result["letter"] is None
    assert result["n"] == 3


def test_letter_grade_boundaries():
    assert letter_grade(97.0, n=10, min_n=8)["letter"] == "A+"
    assert letter_grade(92.9, n=10, min_n=8)["letter"] == "A-"
    assert letter_grade(89.9, n=10, min_n=8)["letter"] == "B+"
    assert letter_grade(59.9, n=10, min_n=8)["letter"] == "F"


def test_verdict_branch_ai_ahead():
    result = compose_scorecard_verdict(
        period_days=90, belief_avg_alpha=1.5, belief_status="ok",
        gap_b=1.2, gap_b_n=10, min_n_win_rate=5, tie_band_pct=0.3,
    )
    assert result["branch"] == "ai_ahead"
    assert "en" in result and "th" in result
    assert result["en"] and result["th"]


def test_verdict_branch_human_ahead():
    result = compose_scorecard_verdict(
        period_days=90, belief_avg_alpha=1.5, belief_status="ok",
        gap_b=-0.7, gap_b_n=10, min_n_win_rate=5, tie_band_pct=0.3,
    )
    assert result["branch"] == "human_ahead"
    assert result["en"] and result["th"]


def test_verdict_branch_tie():
    result = compose_scorecard_verdict(
        period_days=90, belief_avg_alpha=1.5, belief_status="ok",
        gap_b=0.2, gap_b_n=10, min_n_win_rate=5, tie_band_pct=0.3,
    )
    assert result["branch"] == "tie"


def test_verdict_branch_insufficient_evidence_no_gap():
    result = compose_scorecard_verdict(
        period_days=90, belief_avg_alpha=None, belief_status="cold_start",
        gap_b=None, gap_b_n=0, min_n_win_rate=5, tie_band_pct=0.3,
    )
    assert result["branch"] == "insufficient_evidence"


def test_verdict_branch_insufficient_evidence_low_n():
    result = compose_scorecard_verdict(
        period_days=90, belief_avg_alpha=1.0, belief_status="ok",
        gap_b=2.0, gap_b_n=2, min_n_win_rate=5, tie_band_pct=0.3,
    )
    assert result["branch"] == "insufficient_evidence"


def test_report_card_verdict_plan_only_when_no_horizon_matured():
    result = compose_report_card_verdict(
        plan_score=92.0, horizon_grade_kind=None, return_pct=None,
        benchmark_return_pct=None, alpha=None, directional_correct=None,
    )
    assert "not yet matured" in result["en"] or "has not matured" in result["en"]
    assert result["th"]


def test_report_card_verdict_beat_benchmark():
    result = compose_report_card_verdict(
        plan_score=92.0, horizon_grade_kind="H30", return_pct=4.2,
        benchmark_return_pct=1.1, alpha=3.1, directional_correct=True,
    )
    assert "worked" in result["en"]
    assert "correct" in result["en"].lower()


def test_report_card_verdict_trailed_benchmark():
    result = compose_report_card_verdict(
        plan_score=92.0, horizon_grade_kind="H30", return_pct=-1.0,
        benchmark_return_pct=1.1, alpha=-2.1, directional_correct=False,
    )
    assert "trailed" in result["en"]


def test_gap_interpretation_none_value():
    result = compose_gap_interpretation(gap_kind="gap_a", value=None, tie_band_pct=0.3)
    assert "not enough history" in result["en"].lower()
    assert result["th"]


def test_gap_a_near_zero_is_not_earning_its_keep():
    result = compose_gap_interpretation(gap_kind="gap_a", value=0.1, tie_band_pct=0.3)
    assert "earning its keep" in result["en"]


def test_gap_a_positive_is_price_of_practical_execution():
    result = compose_gap_interpretation(gap_kind="gap_a", value=2.0, tie_band_pct=0.3)
    assert "price of practical execution" in result["en"]


def test_gap_a_negative_flags_belief_engine():
    result = compose_gap_interpretation(gap_kind="gap_a", value=-2.0, tie_band_pct=0.3)
    assert "belief engine" in result["en"]


def test_gap_b_branches_are_distinct():
    tie = compose_gap_interpretation(gap_kind="gap_b", value=0.1, tie_band_pct=0.3)
    ai_ahead = compose_gap_interpretation(gap_kind="gap_b", value=2.0, tie_band_pct=0.3)
    human_ahead = compose_gap_interpretation(gap_kind="gap_b", value=-2.0, tie_band_pct=0.3)

    texts = {tie["en"], ai_ahead["en"], human_ahead["en"]}
    assert len(texts) == 3
    assert "full compliance" in ai_ahead["en"]
    assert "added value" in human_ahead["en"]


def test_attribution_verdict_insufficient_evidence():
    result = compose_attribution_verdict(
        period_days=90, actual_return_pct=None, benchmark_return_pct=3.2, effects=[],
    )
    assert "not enough graded history" in result["en"].lower()


def test_attribution_verdict_no_measured_effects():
    result = compose_attribution_verdict(
        period_days=90, actual_return_pct=6.8, benchmark_return_pct=3.2,
        effects=[{"label": "Timing Effect", "value": None}],
    )
    assert "not yet measurable" in result["en"]


def test_attribution_verdict_names_dominant_effect():
    result = compose_attribution_verdict(
        period_days=90, actual_return_pct=6.8, benchmark_return_pct=3.2,
        effects=[
            {"label": "Stock Selection & Allocation", "value": 2.9},
            {"label": "Timing Effect", "value": -0.4},
            {"label": "Your Overrides", "value": 0.7},
        ],
    )
    assert "stock selection & allocation" in result["en"].lower()
    assert "+6.8%" in result["en"] and "+3.2%" in result["en"]
