"""AI Evaluation & Execution Intelligence — services package (M0 skeleton).

Design baseline: docs/EXECUTION_INTELLIGENCE_UX.md
Build order:     docs/AI_EVALUATION_IMPLEMENTATION_PLAN.md

Every module added under this package (horizon_grader, plan_grader,
execution_analyzer, verdict_composer, opportunity_cost, ideal_series, ...)
must hold to the invariants in the implementation plan §4:

1. Read-only upstream — never mutate RecommendationSnapshot, OptimizerHistory,
   UserExecutionDecision (except the scheduler's EXPIRED writer), Transaction,
   or shadow inception data.
2. Grades are append-only (recommendation_grades) — no UPDATE, ever.
3. Zero AI calls anywhere in this package. Grading/scoring/opportunity-cost/
   verdicts are arithmetic and templates (OPTIMIZER_PHILOSOPHY.md §6 boundary).
4. The optimizer pipeline is untouched.
5. Single source of truth per metric — computed once here, formatted by the
   frontend, never recomputed client-side.
6. Existing formulas are not re-derived (portfolio_metrics.py, shadow_tracker.py,
   broker_fees.py stay authoritative for what they already own).
7. Degraded modes are observable — every job logs skips with reasons; every
   API response carries as_of + per-section status (ok|stale|unavailable).
8. Hypothetical figures are always named counterfactual_* in payloads — never
   conflated with realized figures.
9. Storage uses datetime.utcnow(); horizon maturity is evaluated in UTC.

Pure-function bias: grading/scoring services take plain data in, return plain
data out (mirror services/portfolio_metrics.py's contract) — ORM only at thin
call boundaries.
"""
