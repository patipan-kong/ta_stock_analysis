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


def _belief_clause(period_days: int, belief_status: str, belief_avg_alpha: float | None) -> tuple[str, str]:
    """AI-vs-benchmark clause shared by compose_scorecard_verdict and
    compose_trust_report (MUJI) — one branch table, two registers reading
    the same underlying number (ENGINEERING_PRINCIPLES Single Source of
    Truth: the branch logic is never re-derived per caller).
    """
    if belief_status == "ok" and belief_avg_alpha is not None:
        if belief_avg_alpha > 0:
            return (
                f"Over the last {period_days} days, AI recommendations beat the benchmark",
                f"ในช่วง {period_days} วันที่ผ่านมา คำแนะนำของ AI ให้ผลดีกว่าตลาด",
            )
        if belief_avg_alpha < 0:
            return (
                f"Over the last {period_days} days, AI recommendations trailed the benchmark",
                f"ในช่วง {period_days} วันที่ผ่านมา คำแนะนำของ AI ให้ผลด้อยกว่าตลาด",
            )
        return (
            f"Over the last {period_days} days, AI recommendations matched the benchmark",
            f"ในช่วง {period_days} วันที่ผ่านมา คำแนะนำของ AI ให้ผลใกล้เคียงตลาด",
        )
    return (
        f"Over the last {period_days} days, there is not yet enough graded history to judge AI recommendations",
        f"ในช่วง {period_days} วันที่ผ่านมา ยังมีข้อมูลไม่พอที่จะประเมินคำแนะนำของ AI",
    )


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
    belief_en, belief_th = _belief_clause(period_days, belief_status, belief_avg_alpha)

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


def compose_gap_interpretation(
    *,
    gap_kind: str,
    value: float | None,
    tie_band_pct: float,
) -> dict[str, str]:
    """One-line reading of Gap A (Ideal−AI) or Gap B (AI−You), AI Evaluation
    M6 (UX S7). Sign meaning differs between the two gaps
    (OPTIMIZER_PHILOSOPHY.md §12's three-way Implementation Shortfall
    reading vs. the plain human-vs-AI comparison) so the templates are
    written separately rather than shared. gap_kind is "gap_a" or "gap_b".
    """
    if value is None:
        return {
            "en": "Not enough history yet to interpret this gap.",
            "th": "ยังมีข้อมูลไม่พอที่จะตีความช่องว่างนี้",
        }

    if gap_kind == "gap_a":
        if abs(value) <= tie_band_pct:
            return {
                "en": "Near zero — the execution layer is tracking the ideal closely; it may not be earning its keep as a distinct layer.",
                "th": "ใกล้ศูนย์ — ชั้นการดำเนินการติดตามพอร์ตในอุดมคติได้ใกล้เคียง อาจไม่ได้สร้างคุณค่าเพิ่มในฐานะชั้นแยกต่างหาก",
            }
        if value > 0:
            return {
                "en": f"+{value:.1f}% — the price of practical execution; a persistently large gap suggests execution is being too conservative.",
                "th": f"+{value:.1f}% — ต้นทุนของการดำเนินการจริง หากช่องว่างนี้ยังคงมากต่อเนื่อง แสดงว่าการดำเนินการอาจระมัดระวังเกินไป",
            }
        return {
            "en": f"{value:.1f}% — execution outperformed the frictionless ideal; if this persists, check the belief engine, not the execution layer.",
            "th": f"{value:.1f}% — การดำเนินการให้ผลดีกว่าพอร์ตในอุดมคติที่ไร้แรงเสียดทาน หากเกิดขึ้นต่อเนื่อง ควรตรวจสอบที่ชั้นความเชื่อ ไม่ใช่ชั้นการดำเนินการ",
        }

    # gap_b: AI − You
    if abs(value) <= tie_band_pct:
        return {
            "en": "Near zero — your decisions performed about the same as full compliance with the AI Portfolio.",
            "th": "ใกล้ศูนย์ — การตัดสินใจของคุณให้ผลใกล้เคียงกับการทำตามพอร์ต AI ทั้งหมด",
        }
    if value > 0:
        return {
            "en": f"+{value:.1f}% — full compliance with the AI Portfolio would have outperformed your own decisions.",
            "th": f"+{value:.1f}% — การทำตามพอร์ต AI ทั้งหมดจะให้ผลดีกว่าการตัดสินใจของคุณ",
        }
    return {
        "en": f"{abs(value):.1f}% — your own decisions added value over full compliance with the AI Portfolio.",
        "th": f"{abs(value):.1f}% — การตัดสินใจของคุณเองเพิ่มมูลค่าเหนือกว่าการทำตามพอร์ต AI ทั้งหมด",
    }


def compose_attribution_verdict(
    *,
    period_days: int,
    actual_return_pct: float | None,
    benchmark_return_pct: float | None,
    effects: list[dict[str, Any]],
) -> dict[str, str]:
    """The Attribution screen's leading sentence (UX S8): "a user should be
    able to read only the sentence and leave correctly informed." Names the
    single largest-magnitude measured effect — a simplified, single-cause
    version of the UX mock's multi-clause narrative (documented scope
    choice: naming and ranking *multiple* causes in prose is closer to
    generation than templating; one dominant, deterministically-selected
    cause keeps this a template, not a narrative). `effects` is
    [{"label", "value"}, ...] — rows with value=None (unavailable/maturing)
    are excluded from the "dominant effect" selection, never guessed.
    """
    if actual_return_pct is None or benchmark_return_pct is None:
        return {
            "en": f"Not enough graded history yet to explain the last {period_days} days' return.",
            "th": f"ยังมีข้อมูลไม่พอที่จะอธิบายผลตอบแทนในช่วง {period_days} วันที่ผ่านมา",
        }

    diff = round(actual_return_pct - benchmark_return_pct, 2)
    measured = [e for e in effects if e.get("value") is not None]
    if not measured:
        return {
            "en": f"You returned {actual_return_pct:+.1f}% vs the benchmark {benchmark_return_pct:+.1f}%. The breakdown is not yet measurable.",
            "th": f"คุณได้รับผลตอบแทน {actual_return_pct:+.1f}% เทียบกับตลาด {benchmark_return_pct:+.1f}% แต่ยังไม่สามารถแยกสาเหตุได้",
        }

    dominant = max(measured, key=lambda e: abs(e["value"]))
    verb_en = "came from" if dominant["value"] >= 0 else "was cost by"
    verb_th = "มาจาก" if dominant["value"] >= 0 else "ถูกลดทอนจาก"

    return {
        "en": (
            f"You returned {actual_return_pct:+.1f}% vs the benchmark {benchmark_return_pct:+.1f}%. "
            f"Most of the {diff:+.1f}% difference {verb_en} {dominant['label'].lower()}."
        ),
        "th": (
            f"คุณได้รับผลตอบแทน {actual_return_pct:+.1f}% เทียบกับตลาด {benchmark_return_pct:+.1f}% "
            f"ส่วนต่าง {diff:+.1f}% ส่วนใหญ่{verb_th}{dominant['label']}"
        ),
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


def compose_trust_report(
    *,
    period_days: int,
    belief_avg_alpha: float | None,
    belief_status: str,
    gap_b: float | None,
    gap_b_n: int,
    min_n_win_rate: int,
    tie_band_pct: float,
    followed_count: int,
    total_decisions: int,
    insight: dict[str, Any] | None,
) -> dict[str, Any]:
    """MUJI Trust Report (AI Evaluation M7, UX S9): at most three plain
    sentences, no letter grades, no jargon, at most two numbers per sentence
    (UX: "one calm card, not the hub"). Reuses the same verdict data
    compose_scorecard_verdict already reads (_belief_clause, gap_b) rather
    than re-deriving the AI-vs-benchmark or human-vs-AI branch logic a
    second way — MUJI and Quant are two registers over one source of truth.

    `insight` is the strongest sample-backed observation from
    services.analytics.human_vs_ai.compute_scoreboard's by_trade_class
    breakdown (already computed there, read here — never recomputed):
    {"label": str, "human_better": int, "total": int} when the human's
    deviations from a specific trade class beat the AI more often than not
    on a defensible sample, else None. When None, sentence 3 is omitted
    entirely rather than padded with a vague filler — "three sentences
    maximum" does not mean three sentences always.

    Returns {"sentences": [{"en", "th"}, ...], "branch": str}.
    """
    belief_en, belief_th = _belief_clause(period_days, belief_status, belief_avg_alpha)
    sentences = [{"en": f"{belief_en}.", "th": f"{belief_th}"}]

    if total_decisions == 0:
        sentences.append({
            "en": "You have not yet recorded a decision on an AI recommendation.",
            "th": "คุณยังไม่ได้บันทึกการตัดสินใจกับคำแนะนำของ AI",
        })
        branch = "no_decisions"
    else:
        compliance_en = f"You followed {followed_count} of {total_decisions} recommendations."
        compliance_th = f"คุณทำตามคำแนะนำ {followed_count} จาก {total_decisions} ครั้ง"

        if gap_b is None or gap_b_n < min_n_win_rate:
            branch = "insufficient_evidence"
            perf_en = "not enough of your decisions have matured yet to say how your own judgment performed"
            perf_th = "การตัดสินใจของคุณยังครบกำหนดประเมินไม่พอ จึงยังบอกไม่ได้ว่าผลงานเป็นอย่างไร"
        elif abs(gap_b) <= tie_band_pct:
            branch = "tie"
            perf_en = "your own decisions performed about the same as following the AI exactly"
            perf_th = "การตัดสินใจของคุณให้ผลใกล้เคียงกับการทำตาม AI ทั้งหมด"
        elif gap_b > 0:
            branch = "ai_ahead"
            perf_en = "following the AI's recommendations exactly would have done slightly better"
            perf_th = "หากทำตามคำแนะนำของ AI ทั้งหมดจะให้ผลดีกว่าเล็กน้อย"
        else:
            branch = "human_ahead"
            perf_en = f"your own decisions did well ({gap_b * -1:+.1f}%)"
            perf_th = f"การตัดสินใจของคุณเองก็ทำได้ดี ({gap_b * -1:+.1f}%)"

        sentences.append({
            "en": f"{compliance_en} Overall, {perf_en}.",
            "th": f"{compliance_th} {perf_th}",
        })

    if insight is not None:
        label = insight["label"]
        sentences.append({
            "en": f"Worth noting: when you didn't follow \"{label}\" recommendations, it was often the right call.",
            "th": f'สิ่งที่น่าสนใจ: ครั้งที่คุณไม่ทำตามคำแนะนำประเภท "{label}" มักเป็นการตัดสินใจที่ถูก',
        })

    return {"sentences": sentences, "branch": branch}
