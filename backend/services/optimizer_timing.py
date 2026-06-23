"""Phase 4C.6H.1 — Timing Enrichment Layer.

Adds timing metadata to optimizer symbol data. No AI calls. No DB writes.
Reuses score_timing_batch() from timing_intelligence.py.
"""
from __future__ import annotations

import logging

from pydantic import BaseModel

from services.timing_intelligence import score_timing_batch

log = logging.getLogger(__name__)


class OptimizerTimingContext(BaseModel):
    symbol: str
    timing_score: int
    timing_category: str
    execution_priority: str
    momentum: str
    timing_reason: str


# Phase 4C.6H.6 — confidence multipliers by timing score threshold
_CONFIDENCE_THRESHOLDS: list[tuple[int, float]] = [
    (90, 1.10),
    (80, 1.05),
    (60, 1.00),
    (40, 0.90),
    (0,  0.80),
]


def enrich_scores_with_timing(symbols: list[str]) -> dict[str, OptimizerTimingContext]:
    """Fetch timing data for all symbols; return dict keyed by symbol.

    Never raises — returns {} on any failure so the optimizer continues unaffected.
    """
    if not symbols:
        return {}
    try:
        results = score_timing_batch(symbols)
        return {
            r.symbol: OptimizerTimingContext(
                symbol=r.symbol,
                timing_score=r.timing_score,
                timing_category=r.timing_category,
                execution_priority=r.execution_priority,
                momentum=r.momentum,
                timing_reason=r.reasons[0] if r.reasons else "",
            )
            for r in results
        }
    except Exception as exc:
        log.warning("optimizer_timing: enrich failed — continuing without timing: %s", exc)
        return {}


def apply_timing_confidence_adjustment(
    base_confidence: float,
    timing_score: int | None,
) -> float:
    """Scale recommendation confidence by timing quality.

    Does not alter recommendation type — only the confidence level.
    Caps result at 100.0. Returns base_confidence unchanged when timing_score is None.
    """
    if timing_score is None:
        return base_confidence
    for threshold, factor in _CONFIDENCE_THRESHOLDS:
        if timing_score >= threshold:
            return round(min(100.0, base_confidence * factor), 1)
    return base_confidence


def build_timing_note(action: str, timing_score: int, execution_priority: str) -> str | None:
    """Generate a human-readable timing annotation for an optimizer allocation."""
    if action not in ("BUY", "ACCUMULATE"):
        return None
    if execution_priority == "DEFER" or timing_score < 40:
        return (
            f"Strong long-term thesis. Poor current entry timing "
            f"(score {timing_score}, priority DEFER)."
        )
    if timing_score >= 80:
        return f"Strong momentum and favorable timing (score {timing_score})."
    return None
