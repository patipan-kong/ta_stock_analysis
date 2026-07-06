"""verdict_composer.py — AI Evaluation M3: deterministic TH/EN verdict sentences.

Single implementation of "what does this evaluation mean, in one sentence" —
consumed by the scorecard endpoint and the per-recommendation Report Card
endpoint (PLAN §5 M3; UX D9: one verdict, two registers). No AI calls, no DB
access: every function here is a pure template over already-computed numbers
(PLAN §4.3, §4.6). This mirrors services/translations/muji_translator.py's
template pattern (lookup + branch, never free text generation).

Two independent template families:

    letter_grade(score, n, min_n)
        Maps a 0-100 composite to a letter grade, gated by minimum sample
        size (UX D10 — "insufficient evidence" below the threshold, same
        visual weight as a real grade, never a fabricated letter).

    compose_scorecard_verdict(...)
        The Row-1 verdict-strip sentence (UX §3.2): one clause on whether AI
        recommendations beat the benchmark (Belief lens), one clause on
        whether human judgment or full AI compliance did better (Gap B —
        the same quantity services/analytics/human_vs_ai.py already grades
        per-decision; here it is summarized in prose). Four branches, each
        with an EN and TH sentence:
            ai_ahead              — AI Portfolio beat the human's actual result
            human_ahead           — the human's actual result beat the AI Portfolio
            tie                   — within evaluation_settings.tie_band_pct
            insufficient_evidence — gap not measurable yet (no shadow data)

    compose_report_card_verdict(...)
        The Report Card's per-recommendation verdict (UX S3, bottom strip):
        one sentence combining the day-0 plan grade with the most mature
        horizon outcome available. Falls back to a plan-only sentence when
        no horizon has matured yet (UX Rung 1 — "plans are gradeable before
        outcomes").

Letter-grade thresholds and the tie-band source are implementation choices,
not re-derivations of an existing formula (OPTIMIZER_PHILOSOPHY.md §12:
"formulas belong to implementation") — documented here, in one place, so
scorecard.py and recommendation_ledger.py never each invent their own scale.
"""
from __future__ import annotations

from typing import Any

# 0-100 composite -> letter, highest threshold first.
_LETTER_THRESHOLDS: list[tuple[float, str]] = [
    (97.0, "A+"), (93.0, "A"), (90.0, "A-"),
    (87.0, "B+"), (83.0, "B"), (80.0, "B-"),
    (77.0, "C+"), (73.0, "C"), (70.0, "C-"),
    (60.0, "D"), (0.0, "F"),
]


def letter_grade(score: float | None, n: int, min_n: int) -> dict[str, Any]:
    """0-100 composite -> {"status", "letter", "n"}.

    status is one of:
      "unavailable"           — score itself is None (nothing computed yet)
      "insufficient_evidence" — score exists but n < min_n (UX D10)
      "ok"                    — letter is meaningful
    letter is always None unless status == "ok" — never guessed.
    """
    if score is None:
        return {"status": "unavailable", "letter": None, "n": n}
    if n < min_n:
        return {"status": "insufficient_evidence", "letter": None, "n": n}
    for threshold, letter in _LETTER_THRESHOLDS:
        if score >= threshold:
            return {"status": "ok", "letter": letter, "n": n}
    return {"status": "ok", "letter": "F", "n": n}


def compose_scorecard_verdict(
    *,
    period_days: int,
    belief_avg_alpha: float | None,
    belief_status: str,
    gap_b: float | None,
    gap_b_n: int,
    min_n_win_rate: int,
    tie_band_pct: float,
) -> dict[str, Any]:
    """The Row-1 verdict-strip sentence (UX §3.2).

    gap_b is AI Portfolio return minus the human's actual return over the
    window (ShadowPortfolio ACTIVE_MODEL vs actual — the same sign
    convention as attribution_engine.compute_portfolio_attribution's
    regret_score: positive means the AI Portfolio did better).
    gap_b_n is the number of graded/comparable decisions backing that gap
    (services.analytics.human_vs_ai.compare_human_vs_ai's
    decisions_with_data) — below min_n_win_rate the gap clause degrades to
    "insufficient evidence" rather than asserting a side won.

    Returns {"en": str, "th": str, "branch": str}. branch is one of
    "ai_ahead" | "human_ahead" | "tie" | "insufficient_evidence" — asserted
    exhaustively in tests.
    """
    if belief_status == "ok" and belief_avg_alpha is not None:
        if belief_avg_alpha > 0:
            belief_en = f"Over the last {period_days} days, AI recommendations beat the benchmark"
            belief_th = f"ในช่วง {period_days} วันที่ผ่านมา คำแนะนำของ AI ให้ผลดีกว่าตลาด"
        elif belief_avg_alpha < 0:
            belief_en = f"Over the last {period_days} days, AI recommendations trailed the benchmark"
            belief_th = f"ในช่วง {period_days} วันที่ผ่านมา คำแนะนำของ AI ให้ผลด้อยกว่าตลาด"
        else:
            belief_en = f"Over the last {period_days} days, AI recommendations matched the benchmark"
            belief_th = f"ในช่วง {period_days} วันที่ผ่านมา คำแนะนำของ AI ให้ผลใกล้เคียงตลาด"
    else:
        belief_en = f"Over the last {period_days} days, there is not yet enough graded history to judge AI recommendations"
        belief_th = f"ในช่วง {period_days} วันที่ผ่านมา ยังมีข้อมูลไม่พอที่จะประเมินคำแนะนำของ AI"

    if gap_b is None or gap_b_n < min_n_win_rate:
        branch = "insufficient_evidence"
        gap_en = "not enough decisions have matured yet to say whether your judgment or full compliance would have done better"
        gap_th = "ยังมีการตัดสินใจที่ครบกำหนดประเมินไม่พอ จึงยังบอกไม่ได้ว่าการตัดสินใจของคุณหรือการทำตาม AI ทั้งหมดจะดีกว่ากัน"
    elif abs(gap_b) <= tie_band_pct:
        branch = "tie"
        gap_en = "your own decisions performed about the same as following the AI Portfolio exactly"
        gap_th = "การตัดสินใจของคุณให้ผลใกล้เคียงกับการทำตามพอร์ต AI ทั้งหมด"
    elif gap_b > 0:
        branch = "ai_ahead"
        gap_en = f"full compliance with the AI Portfolio would have outperformed your own decisions by {gap_b:+.2f}%"
        gap_th = f"การทำตามพอร์ต AI ทั้งหมดจะให้ผลดีกว่าการตัดสินใจของคุณ {gap_b:+.2f}%"
    else:
        branch = "human_ahead"
        gap_en = f"your own decisions slightly outperformed full compliance by {abs(gap_b):.2f}%"
        gap_th = f"การตัดสินใจของคุณเองให้ผลดีกว่าการทำตาม AI ทั้งหมดเล็กน้อย {abs(gap_b):.2f}%"

    return {
        "en": f"{belief_en}, and {gap_en}.",
        "th": f"{belief_th} และ{gap_th}",
        "branch": branch,
    }


def compose_report_card_verdict(
    *,
    plan_score: float | None,
    horizon_grade_kind: str | None,
    return_pct: float | None,
    benchmark_return_pct: float | None,
    alpha: float | None,
    directional_correct: bool | None,
) -> dict[str, str]:
    """The Report Card's bottom verdict strip (UX S3).

    When no horizon has matured yet (horizon_grade_kind is None), the
    sentence is plan-only — the day-0 grade is the only thing gradeable
    (OPTIMIZER_PHILOSOPHY.md §11; UX Rung 1). Once a horizon has matured,
    the sentence combines plan quality with the realized outcome.
    """
    if plan_score is None:
        plan_en = "This recommendation has not yet been graded."
        plan_th = "คำแนะนำนี้ยังไม่ได้รับการประเมิน"
    elif plan_score >= 80:
        plan_en = "A well-constructed plan"
        plan_th = "แผนการลงทุนที่มีคุณภาพดี"
    elif plan_score >= 60:
        plan_en = "A plan with some rough edges"
        plan_th = "แผนการลงทุนที่ยังมีจุดปรับปรุงได้"
    else:
        plan_en = "A plan with significant proportionality concerns"
        plan_th = "แผนการลงทุนที่มีความกังวลด้านความเหมาะสมของขนาดการซื้อขาย"

    if horizon_grade_kind is None or return_pct is None:
        return {
            "en": f"{plan_en}. Outcome grading has not matured yet.",
            "th": f"{plan_th} ยังไม่ถึงกำหนดประเมินผลลัพธ์",
        }

    beat_benchmark = (
        alpha is not None and alpha > 0
    ) if alpha is not None else (
        benchmark_return_pct is not None and return_pct is not None and return_pct > benchmark_return_pct
    )
    outcome_en = (
        f"and it worked — {return_pct:+.1f}% vs benchmark {benchmark_return_pct:+.1f}%"
        if beat_benchmark and benchmark_return_pct is not None
        else f"but the outcome trailed the benchmark ({return_pct:+.1f}% vs {benchmark_return_pct:+.1f}%)"
        if benchmark_return_pct is not None
        else f"with a {horizon_grade_kind} return of {return_pct:+.1f}%"
    )
    outcome_th = (
        f"และให้ผลลัพธ์ดี {return_pct:+.1f}% เทียบกับตลาด {benchmark_return_pct:+.1f}%"
        if beat_benchmark and benchmark_return_pct is not None
        else f"แต่ผลลัพธ์ด้อยกว่าตลาด ({return_pct:+.1f}% เทียบกับ {benchmark_return_pct:+.1f}%)"
        if benchmark_return_pct is not None
        else f"ให้ผลตอบแทน {horizon_grade_kind} ที่ {return_pct:+.1f}%"
    )

    directional_note_en = ""
    directional_note_th = ""
    if directional_correct is not None:
        directional_note_en = " Directional calls were correct." if directional_correct else " Directional calls were wrong."
        directional_note_th = " การคาดการณ์ทิศทางถูกต้อง" if directional_correct else " การคาดการณ์ทิศทางไม่ถูกต้อง"

    return {
        "en": f"{plan_en}, {outcome_en}.{directional_note_en}",
        "th": f"{plan_th} {outcome_th}{directional_note_th}",
    }
