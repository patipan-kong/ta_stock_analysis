"""Phase 4C.6G.1 — Timing Gate.

Classifies each symbol's timing status as ELIGIBLE / WATCHLIST / EXCLUDED
based on its timing score and execution priority.

Rules (applied in order):
    execution_priority == DEFER  → EXCLUDED  (overrides score)
    timing_score < 40            → EXCLUDED
    timing_score 40-59           → WATCHLIST (reduced allocation weight)
    timing_score >= 60           → ELIGIBLE

Public API
----------
apply_timing_gate(symbol, timing_score, execution_priority) -> TimingGateResult
apply_timing_gate_batch(timing_results)                     -> list[TimingGateResult]
"""
from __future__ import annotations

from pydantic import BaseModel


class TimingGateResult(BaseModel):
    symbol: str
    timing_score: int
    execution_priority: str
    status: str   # ELIGIBLE | WATCHLIST | EXCLUDED
    reason: str


def apply_timing_gate(
    symbol: str,
    timing_score: int,
    execution_priority: str,
) -> TimingGateResult:
    """Classify a single symbol into ELIGIBLE / WATCHLIST / EXCLUDED."""
    if execution_priority == "DEFER":
        return TimingGateResult(
            symbol=symbol,
            timing_score=timing_score,
            execution_priority=execution_priority,
            status="EXCLUDED",
            reason=f"Execution priority DEFER (score {timing_score})",
        )
    if timing_score < 40:
        return TimingGateResult(
            symbol=symbol,
            timing_score=timing_score,
            execution_priority=execution_priority,
            status="EXCLUDED",
            reason=f"Timing score {timing_score} below minimum threshold (40)",
        )
    if timing_score < 60:
        return TimingGateResult(
            symbol=symbol,
            timing_score=timing_score,
            execution_priority=execution_priority,
            status="WATCHLIST",
            reason=f"Timing score {timing_score} — monitoring, reduced weighting",
        )
    return TimingGateResult(
        symbol=symbol,
        timing_score=timing_score,
        execution_priority=execution_priority,
        status="ELIGIBLE",
        reason=f"Timing score {timing_score} — entry conditions met",
    )


def apply_timing_gate_batch(timing_results: list) -> list[TimingGateResult]:
    """Classify a list of StockTimingResult objects (avoids circular import)."""
    return [
        apply_timing_gate(r.symbol, r.timing_score, r.execution_priority)
        for r in timing_results
    ]
