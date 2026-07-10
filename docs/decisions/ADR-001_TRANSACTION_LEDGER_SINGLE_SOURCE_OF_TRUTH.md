# ADR-001: Transaction Ledger as Single Source of Truth

**Status:** Accepted
**Date:** Ratified and numbered 2026-06-30 (alongside ADR-002–004, during the Portfolio Metrics Engine Consolidation); in force as foundational platform design since the ledger-based architecture was first built — this ADR formalizes and names a principle the platform already depended on, rather than introducing a new one.
**Origin:** Referenced throughout the Architecture Handbook as settled law; no single incident produced it, but its consequences are enforced everywhere portfolio state is derived. Formalized here from [TRANSACTION_DOMAIN_MODEL.md](../architecture/TRANSACTION_DOMAIN_MODEL.md), [PLATFORM_EVOLUTION.md](../architecture/PLATFORM_EVOLUTION.md), [ASSET_REGISTRY.md](../architecture/ASSET_REGISTRY.md), and [ASSET_REGISTRY_IMPLEMENTATION_PLAN.md](../implementation/ASSET_REGISTRY_IMPLEMENTATION_PLAN.md).

---

## Context

The platform holds portfolio state in several places at once: the `Transaction` ledger, `PortfolioItem` holdings rows, `PortfolioSnapshot` history, and assorted caches (`AgentCache`, `AnalysisCache`, `MarketDataCache`). Every one of these could, in principle, be edited or treated as authoritative independently of the others. As the platform expanded — more asset classes, more engines, more consumers reading "what does this portfolio hold" — the number of places that could each claim to be correct grew with it.

`TRANSACTION_DOMAIN_MODEL.md` states the consequence directly: "the bridge between facts and everything else is deterministic replay: the same ledger under the same rules produces the same state, every time, on any machine, in any year." `PLATFORM_EVOLUTION.md` §2 extends this to every future asset class the platform will ever hold — stock, fund, gold, crypto, property — each existing "because a ledger event says so."

## Problem

If more than one representation of portfolio state can be treated as authoritative, an inconsistency between them has no way to be resolved — nothing determines which one is "right." A snapshot row, a holdings row, and the transactions that supposedly produced them can silently drift apart, and without a designated source of truth, repair and audit tooling has no fixed point to reconcile against. This is not hypothetical: the platform's own history includes exactly this failure mode elsewhere (see [ADR-002](ADR-002_NO_COMPENSATION_FOR_LEDGER_DEFECTS.md), where a formula that trusted a derived column instead of the ledger masked a real production bug).

## Decision

**The transaction ledger — the `Transaction` table — is the platform's single source of truth for portfolio state, and is immutable.** Corrections are appended as new events; existing rows are never edited to "fix" history. Every other representation of portfolio state — `PortfolioItem` holdings, `PortfolioSnapshot` rows, caches — is a **disposable derivation**: it must be fully reproducible solely by replaying canonical transactions, from any point in history, on any machine, at any time. A state that cannot be reproduced this way is a state the platform is merely asserting, not one it has verified.

This principle extends to every future asset class the platform will hold (`PLATFORM_EVOLUTION.md` §2) and underwrites the Asset Registry's own ledger rule that migration re-keys the ledger additively rather than rewriting it (`ASSET_REGISTRY_IMPLEMENTATION_PLAN.md` Principle 1: "This is ADR-001 applied to the migration itself").

## Rationale

- **Determinism requires one fixed input.** Replay can only guarantee "the same ledger under the same rules produces the same state, every time" if there is exactly one ledger being replayed — not a ledger plus a second, independently-mutable account of the truth.
- **Repair and audit need an anchor.** `verify_snapshots`, `validate_ledger`, and the `rebuild_portfolio` engine all work by comparing derived state against what the ledger says should exist. Without the ledger as the fixed reference, "repair" would have no target to repair *toward*.
- **It generalizes cleanly as the platform grows.** Naming this once, as a numbered principle, means every new asset class, every new engine, and every new cache inherits the same rule automatically instead of re-deriving it under deadline pressure.

## Consequences

- Any bug in derived state (a wrong snapshot, a stale cache, an incorrect holding) is fixed by correcting the ledger and replaying — never by hand-patching the derived row directly.
- Migrations that touch identity or schema (e.g., the Asset Registry epic) must be additive to the ledger, never rewrites of it — the ledger's existing columns are read, never written, by migration steps (`ASSET_REGISTRY_IMPLEMENTATION_PLAN.md` Principle 1).
- Repair and validation tooling (`ledger_validator.py`, `ledger_repair.py`, `portfolio_rebuilder.py`) is built around replay-from-ledger as its only legitimate mechanism for producing corrected state.
- Any column, cache, or snapshot introduced in the future is disposable by design — it can be dropped and regenerated from the ledger at any time without data loss.

## Alternatives Considered

1. **Treat a derived, frequently-read column (e.g. `Portfolio.cash_balance`) as authoritative, with the ledger as a secondary audit trail.**
   Rejected. This is precisely the mistake later found and reversed in the cash-flow formula incident behind ADR-002: treating a derived column as self-validating input allowed real drift between the ledger and that column to be silently absorbed into a plausible-looking result instead of being caught.

2. **Allow multiple authoritative sources, reconciled by periodic sync jobs.**
   Rejected. Reconciliation implies two things can disagree and be independently "right" until synced — which reintroduces the exact ambiguity a single source of truth exists to eliminate, and adds a new class of bug (sync-job failures) on top.

3. **Event sourcing with snapshots as authoritative checkpoints (rather than fully disposable derivations).**
   Rejected. Making a snapshot authoritative, even as a checkpoint, would let audit and repair depend on which checkpoint happens to be trusted rather than on the underlying facts — reintroducing state-dependence into what should be a purely fact-dependent system.

---

## Related Documents

- [TRANSACTION_DOMAIN_MODEL.md](../architecture/TRANSACTION_DOMAIN_MODEL.md) — replay reconstructs history; the ledger as canonical stream
- [PLATFORM_EVOLUTION.md](../architecture/PLATFORM_EVOLUTION.md) §2 — extension to all future asset classes
- [ASSET_REGISTRY.md](../architecture/ASSET_REGISTRY.md) §10 — the ledger's immutability as the load-bearing joint for asset identity
- [ASSET_REGISTRY_IMPLEMENTATION_PLAN.md](../implementation/ASSET_REGISTRY_IMPLEMENTATION_PLAN.md) Principle 1 — ADR-001 applied to migration
- [ADR-002 — No Compensation for Ledger Defects](ADR-002_NO_COMPENSATION_FOR_LEDGER_DEFECTS.md) — the direct corollary: since the ledger is the only source of truth, nothing downstream may substitute a different one when the ledger looks wrong
