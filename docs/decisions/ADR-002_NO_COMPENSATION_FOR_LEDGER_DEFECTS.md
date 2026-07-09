# ADR-002: No Compensation for Ledger or Data Defects

**Status:** Accepted
**Date:** 2026-06-30 (Portfolio Metrics Engine Consolidation)
**Origin:** [DECISION_LOG.md](../engineering/DECISION_LOG.md) — "External Cash Flow Formula Confirmed Canonical (Implementation A)" and "INITIAL_POSITION Dedup Removed from Snapshot Engines"; cited in [PORTFOLIO_CALCULATION_RULES.md](../investment/PORTFOLIO_CALCULATION_RULES.md), [ARCHITECTURE.md](../architecture/ARCHITECTURE.md), [PLATFORM_EVOLUTION.md](../architecture/PLATFORM_EVOLUTION.md), [MARKET_DATA_PLATFORM.md](../architecture/MARKET_DATA_PLATFORM.md).

---

## Context

`portfolio_rebuilder.py` and `portfolio_snapshots.py` computed external cash flow by summing ledger `DEPOSIT`/`WITHDRAW`/`INITIAL_CASH` events directly ("Implementation A"). `snapshot_return_recovery.py` instead derived the same figure from the change in `Portfolio.cash_balance` minus BUY/SELL cash movement ("Implementation B") — a formula `PORTFOLIO_CALCULATION_RULES.md` §4 had originally recommended as canonical, on the reasoning that it was "self-validating against the authority column."

A real production case exposed the problem with that reasoning: a portfolio carried a phantom `DEPOSIT` alongside a duplicate `INITIAL_POSITION`. Implementation A produced an obviously anomalous return number — easy to notice and investigate. Implementation B silently absorbed the drift between the ledger and `cash_balance` into a plausible-looking "clean" return, hiding the underlying bug entirely. A parallel pattern existed in `snapshot_return_recovery.py`'s duplicate-`INITIAL_POSITION` dedup heuristic, which skipped counting a symbol's imported value when it appeared to already exist in the prior snapshot — a defensive guess, made inside the metrics layer, at what the ledger "really meant."

## Problem

When ledger data disagrees with a derived, frequently-read column (like `cash_balance`), or when the ledger itself looks anomalous (a possible duplicate import), a metrics or analytics engine has to decide whether to trust the ledger as-is or to quietly work around the discrepancy to produce a "reasonable" number. Any engine that compensates internally for a data-quality problem makes correctness indistinguishable from luck: a genuinely correct calculation and a calculation masking a hidden defect look identical from the outside, because the defect never surfaces.

## Decision

**Portfolio Metrics — and by extension any analytics or market-data consumer — never compensates for ledger corruption or data-quality defects.** Metrics assumes a valid replay and derives every figure strictly from the ledger (or from already-validated derived data), never from a second, independently-mutable column treated as self-validating. Validation of data integrity belongs exclusively to the Ledger Validator (`ledger_validator.py`); repair of any defect it detects belongs exclusively to Ledger Repair (`ledger_repair.py`, `ledger_repair_plan.py`). If the ledger is wrong, the metrics layer must **fail loud** — produce a visibly anomalous result — rather than silently absorb the discrepancy into an unremarkable-looking number.

Concretely:
- `net_external_cash_flow` is always ledger-derived (`sum(DEPOSIT + INITIAL_CASH) − sum(WITHDRAW)`), never a `Portfolio.cash_balance` delta.
- Duplicate-import detection and correction lives exclusively in `ledger_validator.py` (detection) and `ledger_repair_plan.py` (repair) — no snapshot-generation engine may carry its own defensive dedup heuristic.
- The same prohibition extends beyond the ledger to market data: duplicate price observations are deduplicated at the Market Data Platform boundary, with provenance, never downstream as a compensating heuristic inside metrics or replay.

## Rationale

- **Fail loud beats fail quiet.** The worked production example is decisive: Implementation A's obviously-wrong return number is a cheap, fast signal that something needs investigation. Implementation B's plausible-but-wrong number could have persisted indefinitely, because nothing about it looked broken.
- **Compensation inverts the source-of-truth principle.** Per [ADR-001](ADR-001_TRANSACTION_LEDGER_SINGLE_SOURCE_OF_TRUTH.md), the ledger is the only source of truth; treating `cash_balance` (a derived, disposable column) as authoritative input to a calculation — rather than as something checked *against* the ledger — inverts that hierarchy.
- **Defect ownership must stay singular.** A dedup heuristic living inside a snapshot engine duplicates a responsibility `ledger_validator.py`/`ledger_repair_plan.py` already owns, which is itself the kind of parallel-implementation risk [ADR-004](ADR-004_ONE_IMPLEMENTATION_PER_RULE.md) forbids — and it masked the very defect the dedicated repair pipeline exists to fix upstream.

## Consequences

- A portfolio with an un-repaired duplicate `INITIAL_POSITION` shows an inflated `imported_asset_value` and a distorted `investment_return_pct` — deliberately, as a visible signal — until `validate_ledger`/`generate_repair_plan` is run against it.
- Every engine reading portfolio return figures can trust that a "clean" number was never quietly massaged to look clean; an anomaly in the ledger will surface as an anomaly in the output.
- The rule generalizes beyond accounting: `MARKET_DATA_PLATFORM.md` extends the same prohibition to price-data deduplication, and `PLATFORM_EVOLUTION.md` frames "duplicates and conflicts are boundary problems" as a platform-wide stance, not an accounting-specific one.
- New engines integrating with the ledger or market data must go through Ledger Validator / Ledger Repair (or the equivalent Market Data Platform boundary) for anything resembling defect handling — they may not invent their own local workaround.

## Alternatives Considered

1. **Implementation B — derive cash flow from the change in `cash_balance`, treating it as self-validating.**
   Rejected. This is the compensation anti-pattern by definition: it strips whatever actually happened to `cash_balance`, ledger-explained or not, and was the direct cause of the phantom-deposit case going undetected.

2. **Keep a defensive dedup heuristic inside each snapshot engine, in addition to `ledger_validator`'s detection.**
   Rejected. Produces a three-way inconsistency (the heuristic existed in only one of three engines), duplicates ownership of a concern `ledger_repair_plan.py` already handles, and masks the underlying defect rather than surfacing it for repair.

3. **Best-effort reconciliation — average or blend the ledger-derived and column-derived figures when they disagree.**
   Rejected. Blending two figures when they disagree hides the disagreement itself, which is the one piece of information the platform most needs to see when the ledger and a derived column diverge.

---

## Related Documents

- [ADR-001 — Transaction Ledger as Single Source of Truth](ADR-001_TRANSACTION_LEDGER_SINGLE_SOURCE_OF_TRUTH.md) — the principle this ADR protects: metrics never substitutes a second source for the ledger
- [ADR-004 — One Implementation Per Rule](ADR-004_ONE_IMPLEMENTATION_PER_RULE.md) — why defect-handling logic may not be duplicated across engines
- [PORTFOLIO_CALCULATION_RULES.md](../investment/PORTFOLIO_CALCULATION_RULES.md) §4, §6 — the cash-flow formula and imported-asset resolutions this ADR governs
- [MARKET_DATA_PLATFORM.md](../architecture/MARKET_DATA_PLATFORM.md) — the same prohibition extended from ledger to market data
- [ADR-005 — Replay Correctness Baseline](ADR-005_REPLAY_CORRECTNESS_BASELINE.md) — applies this same no-compensation stance to what a golden replay baseline is allowed to represent
