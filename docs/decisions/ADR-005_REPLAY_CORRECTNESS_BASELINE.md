# ADR-005: Replay Correctness Baseline

**Date:** 2026-07-08
**Deciders:** Platform owner, informed by [M0_CURRENT_STATE_ANALYSIS.md](../implementation/M0_CURRENT_STATE_ANALYSIS.md) (Asset Registry epic)
**Resolves:** M0 Open Question 2 — "does the replay-parity gate require matching today's (alias-split) output, or the corrected (merged) output?"

---

## Context

During Asset Registry M0, investigation of the replay engine found that `backend/services/portfolio_rebuilder.py` keys all in-memory holdings state by `raw_symbol` (stripped/uppercased original), never by `canonical_symbol` — even though `backend/services/transaction_canonicalizer.py` already computes the latter (DR/exchange-resolved, e.g. `NVDA01` → `NVDA`) for every transaction. As a result, aliased spellings of the same instrument — the M0 report's example is `KBANK` vs. `KBANK.BK` — are treated as two distinct holdings in replay today, not one. The platform's own ledger validator already detects this condition (`ledger_validator.py`, the `SYMBOL_ALIAS` check) but only at `WARNING` severity, with no automated repair.

The Asset Registry Implementation Plan requires, as Migration Principle 2, that M5's ledger migration achieve **bit-identical** replay parity against golden baselines captured in M0 before any accounting engine cuts over to `asset_id`-keyed replay. Those golden baselines are full-history replay outputs captured from the current, symbol-keyed engine — the same engine that contains the alias-splitting defect.

## Problem

Once the Symbol Resolver (M3) correctly adjudicates `KBANK` and `KBANK.BK` as one asset, replaying the migrated ledger under `asset_id` will merge them into a single holding. Two baseline definitions are possible, and the plan does not say which one governs:

1. If the golden baseline was captured from the pre-migration engine as-is, it still shows two holdings for that instrument. The bit-identical parity gate would then read the *correct*, merged, post-migration output as a parity **failure**.
2. If the migration is instead required to reproduce the split behavior to satisfy "parity," the platform would be permanently locking in a known accounting defect as the definition of correctness — the opposite of what the epic exists to deliver.

Neither reading is acceptable as written, and the ambiguity has to be resolved *before* golden baselines are captured in M0, because the answer determines what those baselines are for.

## Decision

**Replay parity is measured against correct accounting, not against the current implementation's defects.**

Known correctness defects identified before baseline capture — including the raw_symbol/canonical_symbol alias-splitting defect described above — must be repaired first. Golden replay baselines are captured only after such repairs, so that the baseline represents the platform's intended accounting model from the outset, not a snapshot of its current bugs.

Concretely, for the Asset Registry epic:

- The alias-splitting defect is repaired — replay keys holdings state by resolved identity, not the raw symbol string — before M0's golden baselines are captured.
- Any other correctness defect surfaced during M0 investigation, before baseline capture, is either repaired or explicitly and individually waived in writing; silent waiving is not permitted.
- Once golden baselines are captured, they become the fixed parity reference for the rest of the epic. M5's bit-identical gate applies against that corrected baseline, with no further exceptions.
- Defects discovered *after* baseline capture are out of scope for this ADR. They follow the platform's existing repair-tooling path (`ledger_repair.py`, `generate_repair_plan`) and do not retroactively invalidate an already-captured baseline unless the platform owner explicitly chooses to re-cut it.

## Rationale

- **The architecture already forbids compensation for defects.** `docs/engineering/DECISION_LOG.md`'s ADR-002 establishes that engines never compensate for ledger or accounting defects — defects are fixed at the source, not accommodated downstream. Defining "parity" as "faithful to a known bug" would make the replay-parity gate itself a compensation mechanism, directly contradicting settled platform law.
- **A migration is the wrong vehicle to freeze a bug into permanent architecture.** The Asset Registry is meant to be the platform's long-term identity authority. If its first golden baseline enshrines an accounting error as "correct by definition," every future epic inherits it, and undoing it later requires another migration rather than a straightforward repair.
- **The defect is confirmed, not hypothetical.** `ledger_validator.py`'s `SYMBOL_ALIAS` check exists specifically because this condition occurs in practice, and M0 traced the exact code path (`portfolio_rebuilder.py`) that produces it. The codebase itself already carries a forward reference to this exact gap (`ledger_repair.py:32-35`, citing an unlocated "architecture review"), indicating it was previously identified and parked rather than newly discovered.
- **Fixing before baseline-capture, not during migration, keeps the parity gate meaningful.** If defects were repaired *after* baselines were already cut, every subsequent repair would register as a parity failure against the M5 gate, making genuine migration bugs indistinguishable from expected, intentional corrections.

## Consequences

- Replay parity remains a strict, deterministic, bit-identical gate; its meaning is anchored to corrected accounting rather than to whatever the pre-migration code happened to produce.
- The Asset Registry migration does not institutionalize the alias-splitting defect, or any other known correctness defect discovered before baseline capture, as permanent platform behavior.
- M0's "golden baselines" deliverable gains an explicit precondition: known correctness defects are repaired (or explicitly waived in writing) *before* baselines are captured, not after — this precedes and gates M0's Definition of Done for that deliverable.
- Any correction applied before baseline capture must be documented (what changed, why, and its effect on affected portfolios) and verified via `validate_ledger` before the baseline is cut. An undocumented correction at this stage would be indistinguishable from data corruption to a future reader of the baseline.
- Future epics inherit a clean baseline: they compare against corrected truth rather than legacy behavior, closing off this class of "which bug do we preserve" question before it can recur elsewhere in the platform.

## Alternatives Considered

1. **Preserve current (buggy) behavior as the baseline; treat any future fix as a separate, later change.**
   Rejected. This would require the Asset Registry migration to deliberately reproduce a known-incorrect result (splitting `KBANK`/`KBANK.BK` into two holdings) as its definition of success — directly contradicting ADR-002's no-compensation rule and the architecture's own audit goal (`ASSET_REGISTRY.md` §10: "no engine should be able to tell what any asset is called").

2. **Let "parity" mean either the baseline or the corrected output, decided case by case at M5.**
   Rejected. A parity gate whose meaning depends on which finding is under review is not a gate — it converts every parity check into a fresh judgment call at the point of highest migration risk, which is exactly what Migration Principle 2 exists to prevent.

3. **Defer the decision until M5, once the concrete defect count is known.**
   Rejected. M0 already found a confirmed instance of the defect class, and golden baselines are captured *during* M0 — before M5 begins. Deferring the decision would mean capturing baselines without knowing what they represent, risking a costly re-cut later.

## Status

**Accepted.** This ADR resolves M0 Open Question 2 in full (see [M0_CURRENT_STATE_ANALYSIS.md](../implementation/M0_CURRENT_STATE_ANALYSIS.md)). It is a hard prerequisite: no golden replay baseline may be captured, and M5 — Portfolio Migration may not begin, until this ADR is accepted (see [ASSET_REGISTRY_IMPLEMENTATION_PLAN.md](../implementation/ASSET_REGISTRY_IMPLEMENTATION_PLAN.md) §4, Principle 2).
