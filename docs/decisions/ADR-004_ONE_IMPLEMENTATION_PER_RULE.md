# ADR-004: One Implementation Per Rule

**Status:** Accepted
**Date:** 2026-06-30 (Portfolio Metrics Engine Consolidation)
**Origin:** [DECISION_LOG.md](../engineering/DECISION_LOG.md) — "Portfolio Metrics Engine Consolidation"; cited in [ARCHITECTURE.md](../architecture/ARCHITECTURE.md), [PLATFORM_EVOLUTION.md](../architecture/PLATFORM_EVOLUTION.md), [PORTFOLIO_DOMAIN_MODEL.md](../architecture/PORTFOLIO_DOMAIN_MODEL.md), [PROVIDER_INTERFACE.md](../architecture/PROVIDER_INTERFACE.md), [UNIVERSAL_ASSET_ARCHITECTURE.md](../architecture/UNIVERSAL_ASSET_ARCHITECTURE.md).

---

## Context

`portfolio_rebuilder.py`, `portfolio_snapshots.py`, and `snapshot_return_recovery.py` each independently implemented the same nine period-return `PortfolioSnapshot` fields. `docs/PORTFOLIO_CALCULATION_RULES.md` documented the result: subtle, undocumented divergences between the three — a different window field, a different cash-flow formula (see [ADR-002](ADR-002_NO_COMPENSATION_FOR_LEDGER_DEFECTS.md)), a signed-vs-absolute quantity correction discrepancy, and inconsistent duplicate-import handling. `PLATFORM_EVOLUTION.md` names this incident directly: "the v2.0 hardening sprint exists in memory precisely because three engines once computed nine return fields three subtly different ways."

## Problem

Any business rule — a return formula, a cash-flow definition, a fee calculation, a caching policy — that is implemented more than once by independent consumers will drift, because each copy gets patched independently as bugs are found in only one of them at a time. This is not a one-time cleanup problem: the platform is expanding (new asset classes, new consumers, new engines), and every new consumer of an existing rule is another opportunity to reimplement it slightly differently rather than reuse what already exists.

## Decision

**Every calculation, business rule, or piece of business law has exactly one authoritative implementation, shared by every consumer.** No engine, cache, or consumer may reimplement, special-case, or maintain a parallel version of a rule another part of the platform already implements. A portfolio, asset, or engine may *parameterize* the rule (its currency, its window, its inputs) — it may never get its own variant of the rule itself.

Concretely: `services/portfolio_metrics.py::compute_period_metrics()` is the sole implementation of the nine period-return `PortfolioSnapshot` fields. `portfolio_rebuilder.py`, `portfolio_snapshots.py`, `snapshot_return_recovery.py`, and `snapshot_repair.py` (via delegation) all call it instead of computing independently.

## Rationale

- **Per-engine duplication was the confirmed root cause.** The architecture review behind the 2026-06-30 consolidation traced every one of the divergences found — the cash-flow formula split, the signed/unsigned quantity-correction bug, the inconsistent dedup heuristic — back to the same structural cause: three implementations of one rule, drifting independently.
- **The risk compounds with platform growth, not just persists.** `PLATFORM_EVOLUTION.md` §10 states this as an ongoing law, not a retrospective lesson: "platform growth multiplies consumers; it must never multiply implementations." Every new epic (Asset Registry, Corporate Actions, Multi-Currency) adds consumers of existing rules, and each one is a fresh opportunity to violate this principle if it isn't a standing rule.
- **It generalizes beyond calculations to caching and identity.** `PROVIDER_INTERFACE.md` names a private engine cache as "a second source of truth with an undocumented refresh policy — the precise duplication ADR-004 forbids, wearing a performance costume." `UNIVERSAL_ASSET_ARCHITECTURE.md` extends the same principle from "how a number is computed" to "what an asset is," applying it to the identity layer.

## Consequences

- New consumers of the period-return formula must call `compute_period_metrics()`; they may not compute their own version, even for a seemingly minor variation.
- `compute_period_metrics()` is deliberately **windowing-agnostic** (see [ADR-003](ADR-003_TWO_TIMELINE_RULE.md)) so that the one implementation can serve every engine's different window-membership need without forking the formula itself — parameterization, not duplication, is how legitimate per-engine differences are accommodated.
- A private, engine-local cache with its own refresh policy is treated as a violation of this principle, not a performance optimization — canonical data has one layer, one policy, deciding how it is kept warm and fresh.
- The Asset Registry epic's Symbol Resolver is built once and reused identically for both bulk backfill and live resolution — "no throwaway migration-only logic that then diverges from production behavior" (`ASSET_REGISTRY_IMPLEMENTATION_PLAN.md` Principle 8).
- Regression coverage (`test_portfolio_metrics.py`, `test_portfolio_metrics_parity.py`) exists specifically to keep the three accounting engines from drifting apart again now that they share one implementation.

## Alternatives Considered

1. **Keep three independent implementations, but add cross-engine parity tests to catch drift.**
   Rejected as insufficient on its own. Parity tests can catch drift after it happens, but the original divergence persisted undetected for a long time before being found — tests alone don't remove the temptation or opportunity for a future patch to touch only one engine.

2. **Allow legitimate per-engine variants where windowing needs genuinely differ.**
   Rejected as a general policy, though the underlying need is real. Instead of forking the formula per engine, `compute_period_metrics()` was made windowing-agnostic — callers pre-filter `period_transactions` to their own window — so one implementation serves every engine's differing need without violating the one-implementation rule.

3. **Centralize only the fields that had already caused production bugs, and leave the rest per-engine.**
   Rejected. ADR-004 is stated as a blanket rule ("every calculation"), not a targeted remediation of the fields already found broken — the risk is structural and recurring, not confined to whichever bugs happened to surface first.

---

## Related Documents

- [PORTFOLIO_CALCULATION_RULES.md](../investment/PORTFOLIO_CALCULATION_RULES.md) — the full specification `compute_period_metrics()` implements; Section 12 records this as one of the three resolved Open Questions from the 2026-06-30 consolidation
- [ADR-002 — No Compensation for Ledger Defects](ADR-002_NO_COMPENSATION_FOR_LEDGER_DEFECTS.md) — one of the divergences ADR-004's consolidation resolved
- [ADR-003 — Two-Timeline Rule](ADR-003_TWO_TIMELINE_RULE.md) — how windowing-agnosticism lets one implementation serve engines with different window-membership rules
- [ASSET_REGISTRY_IMPLEMENTATION_PLAN.md](../implementation/ASSET_REGISTRY_IMPLEMENTATION_PLAN.md) Principle 8 — ADR-004 applied to the Symbol Resolver
- [PROVIDER_INTERFACE.md](../architecture/PROVIDER_INTERFACE.md) — why engines hold no private caches
