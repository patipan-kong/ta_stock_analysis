"""Phase 4C.6C — Timing Score Engine.

Computes a deterministic 0-100 score for each AllocationPeriod based on
three measurable components from PeriodPerformance.

No AI calls.  No database access.  Pure function.

Components
----------
  excess_return_component   Primary timing measure (excess return × 4, capped ±30)
  drawdown_component        Reward for avoiding deep losses
  duration_component        Stability bonus for sufficient observation window

Public API
----------
calculate_timing_score(period: PeriodPerformance) -> TimingScore
"""

from __future__ import annotations

from pydantic import BaseModel

from services.timing_performance import PeriodPerformance


# ── Response model ────────────────────────────────────────────────────────────

class TimingScore(BaseModel):
    recommendation_snapshot_id: int
    timing_score: int
    timing_grade: str
    excess_return_component: float
    drawdown_component: float
    duration_component: float
    confidence_level: str


# ── Pure scoring function ─────────────────────────────────────────────────────

def calculate_timing_score(period: PeriodPerformance) -> TimingScore:
    """Return a deterministic 0-100 timing quality score for one period."""
    excess_component = _excess_return_component(period.excess_return_pct)
    drawdown_component = _drawdown_component(period.max_drawdown_pct)
    duration_component = _duration_component(period.days_active)

    raw = 50.0 + excess_component + drawdown_component + duration_component
    score = max(0, min(100, round(raw)))

    return TimingScore(
        recommendation_snapshot_id=period.recommendation_snapshot_id,
        timing_score=score,
        timing_grade=_grade(score),
        excess_return_component=excess_component,
        drawdown_component=drawdown_component,
        duration_component=duration_component,
        confidence_level=_confidence(period.snapshot_count),
    )


# ── Component calculators ─────────────────────────────────────────────────────

def _excess_return_component(excess_return_pct: float | None) -> float:
    """Excess return × 4, capped to [-30, +30].  None → 0 (neutral)."""
    if excess_return_pct is None:
        return 0.0
    raw = excess_return_pct * 4.0
    return max(-30.0, min(30.0, raw))


def _drawdown_component(max_drawdown_pct: float | None) -> float:
    """Tiered bonus/penalty based on peak-to-trough drawdown magnitude.

    None means the NAV never fell during the period → treat as ≤ 2% → +15.
    """
    if max_drawdown_pct is None:
        return 15.0
    dd = abs(max_drawdown_pct)
    if dd <= 2.0:
        return 15.0
    if dd <= 5.0:
        return 10.0
    if dd <= 8.0:
        return 5.0
    if dd <= 12.0:
        return 0.0
    return -10.0


def _duration_component(days_active: int) -> float:
    """Bonus for longer, more reliable observation windows."""
    if days_active >= 30:
        return 10.0
    if days_active >= 14:
        return 5.0
    if days_active >= 7:
        return 0.0
    return -5.0


# ── Grade and confidence helpers ──────────────────────────────────────────────

def _grade(score: int) -> str:
    if score >= 90:
        return "EXCELLENT"
    if score >= 75:
        return "GOOD"
    if score >= 60:
        return "NEUTRAL"
    if score >= 40:
        return "WEAK"
    return "POOR"


def _confidence(snapshot_count: int) -> str:
    if snapshot_count >= 30:
        return "HIGH"
    if snapshot_count >= 15:
        return "MEDIUM"
    return "LOW"
