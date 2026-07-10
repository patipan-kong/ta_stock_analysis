# ADR-003: Two-Timeline Rule

**Status:** Accepted (scope clarified 2026-06-30)
**Date:** Settled as platform law prior to 2026-06-30 (the underlying rule predates its formal numbering); scope explicitly clarified 2026-06-30 during the Portfolio Metrics Engine Consolidation, in "Time Attribution Scope (ADR-003 Resolution)."
**Origin:** [DECISION_LOG.md](../engineering/DECISION_LOG.md) — "Backdated Import Detection (Phase 3B.9 Hotfix)" and "Time Attribution Scope (ADR-003 Resolution)"; cited in [TRANSACTION_DOMAIN_MODEL.md](../architecture/TRANSACTION_DOMAIN_MODEL.md), [BROKER_ACCOUNT_DOMAIN.md](../architecture/BROKER_ACCOUNT_DOMAIN.md), [CORPORATE_ACTION_DOMAIN.md](../architecture/CORPORATE_ACTION_DOMAIN.md), [ARCHITECTURE.md](../architecture/ARCHITECTURE.md).

---

## Context

Every transaction carries two dates that answer different questions: `transaction_date` (when the trade economically happened) and `created_at` (when the platform's database physically recorded the row). Phase 3B.9's original import-stripping logic used `transaction_date` to find `INITIAL_POSITION` events inside a snapshot's window — but a backdated import (a user supplying an original purchase date years in the past) then became invisible to that window check under an incrementally-built snapshot series, leaking its value into NAV as an undetected phantom gain. The Phase 3B.9 hotfix fixed this by switching all non-performance transaction queries to filter by `Transaction.created_at` instead.

Later, during the 2026-06-30 Portfolio Metrics Engine Consolidation, this rule was read literally against a different question — portfolio-state and replay-order — and the literal reading would have required switching `portfolio_snapshots.py` and `snapshot_return_recovery.py`'s window-membership logic from `created_at` back to `transaction_date`, which would have reintroduced the exact Phase 3B.9 bug the hotfix existed to fix.

## Problem

A transaction needs its two dates to answer two structurally different questions, and using the wrong date for either one produces a real bug in each direction:

- Using `created_at` for replay-order/portfolio-state questions would misplace history — a 2022 trade imported in 2027 would replay as if it happened in 2027, corrupting every state computed as-of a date in between.
- Using `transaction_date` for window-membership in incrementally-built snapshot engines makes backdated imports invisible to the window check that would otherwise catch them (the Phase 3B.9 bug), letting their value silently leak into NAV as an unaccounted-for gain.

Without a settled, explicit rule for which date governs which class of question, this ambiguity would keep resurfacing as new engines (analytics, corporate actions, broker-account backfills) are added and each has to independently guess the right answer.

## Decision

**Every transaction carries two timestamps with two distinct meanings, and neither substitutes for the other:**

- **`transaction_date`** governs **replay-order and portfolio-state questions** — cost basis, holdings-as-of-a-date, chronological sort. This is "when it happened," and it determines *where an event lands in replay*.
- **`created_at`** governs **audit and window-membership**, but only in **incrementally-built** engines — this is "when the platform learned it," and it determines which reporting period's totals a transaction counts toward when that period's numbers were built up over time rather than recomputed from scratch.

A backfilled trade lands in event time for replay purposes (a 2022 trade replays in 2022) and confesses its late arrival in provenance/audit (the platform can always tell it was imported in 2027).

**Scope clarification (2026-06-30):** ADR-003 governs replay-order/portfolio-state questions only. It does **not** extend to window-membership logic, which remains each engine's own responsibility: `created_at` for the two incrementally-built engines (`portfolio_snapshots.py`, `snapshot_return_recovery.py`), `transaction_date` for the full rebuild (`portfolio_rebuilder.py`, which recomputes everything from scratch on every run and has no "window" to leak into). `services/portfolio_metrics.py::compute_period_metrics()` itself is windowing-agnostic — it reads neither date field; callers pre-filter `period_transactions` to the window using whichever field is correct for that engine.

## Rationale

- **The two questions really are different.** "Where does this event sit in the portfolio's history" and "does today's incrementally-built snapshot need to notice this event" are not the same question, and the Phase 3B.9 incident is direct evidence that conflating them produces a real, user-visible bug (a phantom gain from an invisible backdated import).
- **Backfills must stay honest.** `TRANSACTION_DOMAIN_MODEL.md` and `BROKER_ACCOUNT_DOMAIN.md` both describe this rule as what makes backfills honest — a late-arriving fact still replays at its true economic date, while the fact that it arrived late remains visible rather than erased.
- **A literal, context-free application of the rule is not what was decided.** The 2026-06-30 clarification exists precisely because "apply ADR-003 everywhere a date is used" is not the actual rule; the rule is scoped to the question being asked. This distinction was confirmed explicitly with the task requester before implementation, specifically because a context-free application would have reintroduced a previously-fixed, documented production bug — directly conflicting with that refactor's "business behavior must remain unchanged" constraint.

## Consequences

- `services/portfolio_metrics.py` is deliberately windowing-agnostic: it never reads `transaction_date` or `created_at` itself, only the already-filtered `period_transactions` its caller provides — enforced structurally, not just by convention (`ARCHITECTURE.md` §"Pure").
- A transaction with `transaction_date != created_at` (a backdated entry) is *correctly* attributed to different windows by different engines — this is an expected consequence of the rule, not a parity violation (`PORTFOLIO_CALCULATION_RULES.md` Invariant 3), and is covered by a dedicated regression test (`test_backdated_transaction_attributed_per_engine_own_window_field`).
- Corporate Action and Broker Account domain work (backfilled statements, action effective-dating) both rest on this rule without re-deriving it: an action recorded today with last month's effective date replays last month.
- Any future engine that needs "when did this happen" must ask explicitly which of the two questions it means, rather than defaulting to whichever date field is convenient.

## Alternatives Considered

1. **Use `transaction_date` uniformly, including for window-membership in incrementally-built engines.**
   Rejected. This is the literal, context-free reading the 2026-06-30 consolidation explicitly declined — it reintroduces the Phase 3B.9 bug, making backdated imports invisible to the window check that should catch them.

2. **Use `created_at` uniformly, including for replay-order/portfolio-state questions.**
   Rejected. This would misplace historical state entirely — a trade dated years in the past would replay as if it happened on the day it was entered, corrupting cost basis and every holdings-as-of-date computation for the intervening period.

3. **Let each engine independently decide which date to use, with no platform-wide rule.**
   Rejected. This is effectively the pre-3B.9 state — no settled answer, decided ad hoc per engine, with no protection against a future engine re-choosing incorrectly and reintroducing the exact class of bug ADR-003 exists to prevent.

---

## Related Documents

- [TRANSACTION_DOMAIN_MODEL.md](../architecture/TRANSACTION_DOMAIN_MODEL.md) §"Two timestamps, two meanings" — the canonical statement of the rule
- [BROKER_ACCOUNT_DOMAIN.md](../architecture/BROKER_ACCOUNT_DOMAIN.md) — historical imports as ordinary imports, resting on this rule
- [CORPORATE_ACTION_DOMAIN.md](../architecture/CORPORATE_ACTION_DOMAIN.md) — the two-timeline rule applied to corporate action effective-dating
- [ARCHITECTURE.md](../architecture/ARCHITECTURE.md) §"Windowing-agnostic" — how `compute_period_metrics()` stays neutral between the two fields
- [PORTFOLIO_CALCULATION_RULES.md](../investment/PORTFOLIO_CALCULATION_RULES.md) Section 2, Invariant 3 — the per-engine window-field assignment and its parity implications
