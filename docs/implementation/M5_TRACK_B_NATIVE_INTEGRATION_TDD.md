# M5 Track B & M6 Native Integration — Technical Design Document

_The implementation-ready design for making the ledger `asset_id`-native and cutting engines over to it. This is a level-4 Technical Design Document under [platform_architecture.md](../architecture/platform_architecture.md) §11: it refines and is bound by [asset_foundation.md](../architecture/asset_foundation.md) (level-2) and [ASSET_REGISTRY.md](../architecture/ASSET_REGISTRY.md) (level-4, frozen). Where either disagrees with this document, this document is wrong._

_Companion documents: [ASSET_REGISTRY_IMPLEMENTATION_PLAN.md](ASSET_REGISTRY_IMPLEMENTATION_PLAN.md) (the M0–M7 plan this document executes M5 Track B and M6 Native Integration for), [M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md](M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md) (the completed Compatibility-Layer this document supersedes at each cutover point), [ASSET_REGISTRY_RETROSPECTIVE.md](../architecture/ASSET_REGISTRY_RETROSPECTIVE.md) (history and lessons this design applies), [ADR-005](../decisions/ADR-005_REPLAY_CORRECTNESS_BASELINE.md) (the hard gate this document's Stage 0 satisfies), [OPTIMIZER_PHILOSOPHY.md](../investment/OPTIMIZER_PHILOSOPHY.md) and [PORTFOLIO_CALCULATION_RULES.md](../investment/PORTFOLIO_CALCULATION_RULES.md) (the invariants this design must not disturb)._

---

## 0. Scope Note

**What this document is not.** It does not redesign the Registry (frozen — ASSET_REGISTRY.md), the domain constitution (frozen — asset_foundation.md), or the M0–M7 milestone breakdown (frozen — ASSET_REGISTRY_IMPLEMENTATION_PLAN.md §5). It does not touch optimizer decision logic, execution planning philosophy, or AI evaluation grading — those are governed by OPTIMIZER_PHILOSOPHY.md and are read-only consumers of what this document produces.

**What this document is.** The technical design for the two pieces of the epic that remain genuinely unbuilt after M1–M4, M5 Track A, and M6 Compatibility-Layer all shipped (2026-07-09/10):

1. **M5 Track B — Native Ledger Persistence.** Giving `Transaction`, `PortfolioItem`, `PortfolioSnapshot`, and `Watchlist` a native `asset_id`, backfilled under adjudication, gated on bit-identical replay parity.
2. **M6 Native Integration.** Repointing every consumer the Compatibility Layer made Registry-*informed* (via read-time `resolve_asset()` calls) to instead read the now-*materialized* `asset_id` directly — faster, and closing the one correctness risk the Compatibility Layer explicitly could not close (§2.3 item 1 of the read-path plan: the frozen-plan-vs-live-`Transaction` join).

It also designs the **Asset Definition v1** mechanism (§8) — the second Core Foundation item in [asset_foundation.md](../architecture/asset_foundation.md) §8 — since it is a small, low-risk, foundational piece that Native Integration's capability-discovery needs benefit from having in place, and because the milestone brief requested it. It does **not** implement any new asset class.

**Current state, precisely** (verified against live code, not docs, in the grounding pass for this document):

| Table | `asset_id` column today | Notes |
|---|---|---|
| `Transaction` | None | `symbol: String, nullable` (null for cash-only rows) |
| `PortfolioItem` | None | `symbol: String, nullable=False`, unique with `portfolio_id` |
| `PortfolioSnapshot` | None | symbols only inside `holdings_json`/`sector_breakdown_json` text blobs |
| `Watchlist` | None | `symbol: String, nullable=False`, unique with `workspace_id` |

Registry coverage against production-like data (M5 Track A bootstrap, 2026-07-09): 21 assets minted, 41/52 transactions (79%) resolved to a mintable identity, 21/25 claim shapes (84%) resolved, 2 duplicate clusters correctly left unminted, 0 quarantined.

---

## 1. Architecture Overview

### 1.1 What already exists (reuse, do not rebuild)

Per ENGINEERING_PRINCIPLES.md ("Reuse Before Create," "Identify the existing owner of the responsibility"), this design's first and most important decision is what it does **not** build:

| Capability | Owner (existing, unmodified) |
|---|---|
| Minting, identity permanence, lifecycle transitions, relationships, classification | `services/asset_registry.py` (M1) |
| Identity questions/verdicts entry point, findings, merges | `services/registry_service.py` (M2) |
| Claim adjudication — decisive / ambiguous / unknown | `services/identity_resolver.py` (M3) |
| Provider→claim translation | `services/provider_adapter.py` (M4) |
| Ledger symbol → `ResolutionClaim` | `services/ledger_evidence_builder.py` (M5 Track A) |
| Dry-run bulk resolution over the real ledger, grouped by `ClaimShape` | `services/migration_planner.py::plan_migration()` (M5 Track A) |
| Committing already-decisive verdicts (attach identifiers) | `services/migration_executor.py::execute_migration()` (M5 Track A) |
| Minting new assets for unambiguous `UNKNOWN` shapes | `services/registry_bootstrap.py::bootstrap_registry()` + `services/bootstrap_planner.py::build_bootstrap_plan()` (M5 Track A) |
| Read-time symbol→`AssetView` resolution with cache and honest `Unresolved` | `services/registry_lookup.py::resolve_asset()`/`resolve_many()` (M6 Compatibility-Layer) |
| `.BK`-variant / bare-ticker matching | `services/registry_symbol_matching.py::match_known_symbols()` (M6 Compatibility-Layer) |
| Ledger row → value object (the natural resolver insertion point) | `services/transaction_canonicalizer.py::canonicalize_transactions()` |

Nothing in this document duplicates a rule any of these already own (ADR-004). Every new module below is either new *plumbing* connecting these existing authorities to columns that don't yet exist, or a genuinely new small capability (the Asset Definition vocabulary, §8) that no existing module owns.

### 1.2 The two remaining problems, stated precisely

**Problem A (M5 Track B).** The ledger tables are symbol-keyed. Registry identity exists and has real callers everywhere *except* the four tables that are the actual accounting record. Until they carry `asset_id`, the Registry's core promise — "one real-world instrument, one identity, forever" — is not actually protecting the one place an identity error is irreversible (replay reproduces it forever, per ASSET_REGISTRY.md §10).

**Problem B (M6 Native).** Every non-ledger consumer the Compatibility Layer wired up (optimizer internals, execution sizing, evaluation, shadow portfolios, analytics) resolves identity **at read time**, on every call, via `resolve_asset()`. This works and is safe, but it is a shim by design (REGISTRY_INTEGRATION_GUIDE.md, `registry_lookup.py`'s own module docstring) — the architecture's audit goal is that engines carry `asset_id` as a *fact*, not re-derive it as a *query*, every time.

Both problems share one root dependency: **neither can be solved until the ledger tables have the column.** This is why M6 Native Integration is designed here as a direct continuation of M5 Track B, not a parallel track — Migration Principle 2 already ordered them this way (ASSET_REGISTRY_IMPLEMENTATION_PLAN.md §5's dependency graph: `M5 Track B → M6 Native → M7`).

### 1.3 Design posture

Three postures carried over unchanged from the parent plan, because nothing about reaching this milestone changes them:

- **Expand → verify → cut over → contract** (Migration Principle 6). Every schema change in this document is additive; nothing is dropped until M7.
- **No flag days, per-consumer, per-portfolio, reversible** (Migration Principle 3). The dual-identity coexistence period is not a fixed calendar window — it ends independently for each portfolio, gated on that portfolio's own backfill coverage and replay parity.
- **Replay parity against corrected accounting, not against today's bugs** (ADR-005). This document's Stage 0 (§7.1) exists specifically to satisfy ADR-005's precondition, which — per the grounding pass for this document — has **not yet been implemented**: `portfolio_rebuilder.py` still keys all replay state by `raw_symbol`, and `ledger_validator.py` CHECK 2 (`_check_symbol_aliases`) still only warns about it. No golden baseline may be captured before this is fixed.

---

## 2. Registry-Native Integration Strategy

### 2.1 The single new domain concept: `ReplayKey`

The central design decision of this document. Today, `portfolio_rebuilder.py`'s entire replay state (`_PortfolioState.holdings: dict[str, _HoldingState]`, the reconciliation diff, the execution-plan diff, the Stage 8 commit) is keyed by `raw_symbol`. ADR-005 requires this to become identity-based — but Registry coverage is, and will remain for some time, partial (79% today; the residual 21% is Track A's own named adjudication debt, not something this milestone must clear to zero before proceeding).

A key space that is sometimes `asset_id` and sometimes a raw string, chosen per-transaction, would make replay's own key type nondeterministic across ledger states — unacceptable for an engine whose contract is bit-identical reproduction. The resolution is a single, three-tier, **always-computed, always-deterministic** derivation:

```
ReplayKey(ctx: CanonicalTransaction) =
    asset_id            if ctx.asset_id is not None            # Registry-resolved (target state)
    else canonical_symbol  if ctx.canonical_symbol is not None    # legacy yfinance-routing alias (ADR-005's own fix)
    else raw_symbol                                                # should not occur when raw_symbol is set (canonical_symbol is always computed from it)
```

This is not a workaround bolted onto ADR-005 — it **is** ADR-005's fix, generalized. ADR-005 asked for exactly the middle tier (key by `canonical_symbol`, which `transaction_canonicalizer.py` already computes, instead of `raw_symbol`) because at the time it was written (2026-07-08) no Registry existed yet to provide a real identity. Today it does. `ReplayKey` uses the permanent identity where the Registry has adjudicated one, and falls back to exactly the alias-collapsing fix ADR-005 specified where it hasn't — so `KBANK`/`KBANK.BK` merge into one holding under `ReplayKey` **the day this ships**, independent of Registry coverage, and individual instruments silently upgrade to the permanent key as Track A's backlog clears, with no further replay-engine change required. `ReplayKey` is computed once, by `transaction_canonicalizer.py` (§2.2), never independently by any consumer — ADR-004.

### 2.2 Where identity enters the replay path without breaking purity

`transaction_canonicalizer.py` is documented as a pure function (no DB access, no I/O) and is used by three independent engines (`portfolio_rebuilder.py`, `ledger_validator.py`, `snapshot_return_recovery.py`) specifically *because* it is pure. The naive fix — call `registry_lookup.resolve_asset()` inside `_canonicalize_one()` — would break that contract and reintroduce exactly the "silent behavior change during coexistence" risk Migration Principle 3 forbids inside the replay loop (`registry_lookup.py`'s own module docstring already prohibits this call site).

The resolution is the same one that makes `ReplayKey` deterministic: **`Transaction.asset_id` becomes a materialized column, backfilled in Stage 2 (§7.2), and `CanonicalTransaction.asset_id` is populated by simply reading that column** — no resolution call, no DB session inside the pure function, no I/O. `canonicalize_transactions()` gains exactly one new field on its output dataclass and one new line reading `tx.asset_id`, which is a plain ORM attribute access identical in kind to every other field it already reads (`tx.symbol`, `tx.shares`, …). Purity is preserved because identity resolution happens once, upstream, at write time (§2.3) — not on every replay.

### 2.3 Where identity is resolved: write time, not read time

Every `execute_*` function in `services/portfolio_transactions.py` already looks up (or creates) the `PortfolioItem` row by `symbol` before writing the `Transaction` row. This is the natural, and only necessary, resolution point: resolve once, at the moment a symbol enters the ledger, exactly as ASSET_REGISTRY.md §10 describes the two legitimate places a symbol may appear ("the boundary, as resolution inputs... and the presentation surface"). `execute_buy`/`execute_sell`/`execute_initial_position`/`execute_quantity_correction` gain one `registry_lookup.resolve_asset(db, symbol)` call each, writing the resolved `asset_id` (or `None`, honestly, for `Unresolved`) onto both the `Transaction` and `PortfolioItem` rows they already construct. `execute_dividend`, `execute_deposit`, `execute_withdraw`, `execute_initial_cash` are cash-only or symbol-optional and are touched only where a `symbol` is actually present (`execute_dividend`'s optional `symbol` parameter).

This is additive and fails open: `Unresolved` writes `asset_id=None`, identical to today's behavior, for any symbol the Registry hasn't yet adjudicated — never blocks a transaction, never guesses (ASSET_REGISTRY.md §4).

---

## 3. Module Structure

No new package. Five new files, in the flat `backend/services/` layout every prior milestone used (M1–M4, M5 Track A each added 2–4 files this way; no milestone introduced a subpackage). Consistent naming with the existing `registry_*`/`migration_*` families:

```
backend/services/
  ledger_asset_backfill.py      # NEW — Stage 2: writes asset_id onto Transaction/PortfolioItem/Watchlist rows
  replay_key.py                 # NEW — the ReplayKey derivation (§2.1), one pure function, zero DB access
  asset_definition_domain.py    # NEW — §8: the closed vocabulary (Capability enum, AssetDefinition dataclass, EQUITY_V1/CASH_V1)
  asset_definition.py           # NEW — §8: get_definition(), validate_against_definition() — the read/validate surface
  registry_replay_parity.py     # NEW — Stage 1/4: golden-baseline capture + bit-identical comparison harness
```

Modified (all additive — new optional fields, new optional parameters, existing signatures untouched wherever a caller doesn't opt in):

```
backend/models/database.py              # + nullable asset_id columns (§4.1)
backend/services/transaction_canonicalizer.py   # + CanonicalTransaction.asset_id field (§2.2)
backend/services/portfolio_transactions.py      # + resolve-and-write in execute_buy/sell/initial_position/quantity_correction/dividend (§2.3)
backend/services/portfolio_rebuilder.py         # holdings dict rekeyed to ReplayKey (§7.4), behind a per-portfolio flag
backend/services/ledger_validator.py            # CHECK 2 rewritten to assert zero aliasing under ReplayKey (§7.1)
backend/services/registry_lookup.py             # AssetView gains .capabilities (§8.4), additive field
```

Nothing in `agents/`, `main.py`'s route signatures, or any frontend file needs to change for M5 Track B or M6 Native to ship — per the grounding pass, no `/transactions/*`, `/holdings`, or `/watchlist*` route currently accepts or returns `asset_id`, and none of this design proposes adding it to any wire contract. Native Integration is an internal-representation change; API compatibility is automatic, not engineered.

---

## 4. Domain Model

### 4.1 Schema changes (one Alembic migration, chained off the current head)

```python
transactions.asset_id      = Column(Integer, ForeignKey("assets.id"), nullable=True, index=True)
portfolio_items.asset_id   = Column(Integer, ForeignKey("assets.id"), nullable=True, index=True)
watchlist.asset_id         = Column(Integer, ForeignKey("assets.id"), nullable=True, index=True)
```

All three: **nullable, no unique constraint, no FK cascade behavior beyond default RESTRICT** (an `Asset` must never be deletable while a ledger row references it — but per ASSET_REGISTRY.md §6, assets are never deleted anyway, so RESTRICT is a belt-and-braces default, not a load-bearing one). `PortfolioSnapshot` gets no new column — see §4.2.

Why nullable, permanently (not just during migration): the Registry's own architecture requires it. ASSET_REGISTRY.md §7 ("Missing identifiers... Absence is data") and §4 ("resolve decisively or ask — never guess") together mean a symbol the Registry cannot yet adjudicate must still be transactable — the platform doesn't stop accepting a user's trade because identity resolution is pending. `asset_id IS NULL` is not "migration in progress," it is a permanently legitimate state for any symbol Track A's adjudication has not reached, exactly mirroring what `Unresolved` already means everywhere else in this codebase.

### 4.2 `PortfolioSnapshot.holdings_json` — additive shape only

Per `PORTFOLIO_CALCULATION_RULES.md` Design Principle 4 (deterministic replay) and the existing `snapshot_repair.py` docstring (reconstructs *only* from `holdings_json`, no live-DB fallback, by design), historical snapshot rows are frozen exactly like a `RecommendationSnapshot` (OPTIMIZER_PHILOSOPHY.md Design Invariant 1). This document does not propose rewriting them. Going forward, `_build_snapshot_day()`'s per-holding dict gains one additive optional key:

```json
{"symbol": "KBANK.BK", "asset_id": 41, "shares": 100, "market_value": 19700.0, ...}
```

`asset_id` is `null` for any holding not yet backfilled and absent entirely on every snapshot row written before this ships — both are legitimate, distinguishable states (`"asset_id" not in holding` = pre-cutover row; `holding["asset_id"] is None` = post-cutover, unresolved). No consumer of `holdings_json` may treat these as equivalent; `services/snapshot_repair.py` and every reader must default-handle both without erroring, per ENGINEERING_PRINCIPLES.md "Failure Handling."

### 4.3 `CanonicalTransaction` (transaction_canonicalizer.py)

```python
@dataclass(frozen=True)
class CanonicalTransaction:
    # ...existing fields unchanged...
    asset_id: AssetId | None = None    # NEW — read directly from Transaction.asset_id, never resolved here
```

### 4.4 `ReplayKey` (replay_key.py — new)

```python
ReplayKeyT = Union[AssetId, str]   # int-typed AssetId, or a legacy string key — never mixed meaning within one key's lifetime

def replay_key(ctx: CanonicalTransaction) -> ReplayKeyT | None:
    """None only for cash-only transactions (ctx.raw_symbol is None)."""
    if ctx.asset_id is not None:
        return ctx.asset_id
    if ctx.canonical_symbol is not None:
        return ctx.canonical_symbol
    return ctx.raw_symbol
```

Pure, total, deterministic, zero DB access — the same purity class as `transaction_canonicalizer.py` itself, and co-located conceptually with it (kept in a separate file per the existing per-milestone file-splitting convention M2/M3/M4 each used, since `replay_key()` is consumed by three engines — `portfolio_rebuilder.py`, `ledger_validator.py`, `snapshot_return_recovery.py` — none of which should import from each other).

---

## 5. Internal Interfaces

### 5.1 `ledger_asset_backfill.py` (new)

```python
def backfill_ledger_asset_ids(
    db: Session,
    plan: MigrationPlan,             # reused, unmodified, from migration_planner.plan_migration()
    *,
    portfolio_ids: Sequence[int] | None = None,
    run_id: str | None = None,
    dry_run: bool = True,
    requested_by: str = "ledger_asset_backfill",
) -> BackfillReport
```

Mirrors `migration_executor.execute_migration()`'s discipline exactly (same checkpoint-append-only pattern via a new `LedgerAssetBackfillCheckpoint` table, same dry-run-rolls-back-every-stage default, same `requested_by` provenance field) because it performs the same *kind* of operation — committing an already-decided verdict — just against a different set of tables. For each `RESOLVED` `ClaimShape` in `plan.resolutions` with a live `resolved_asset_id`, it writes `asset_id` onto every `Transaction`, `PortfolioItem`, and `Watchlist` row whose `symbol` matches that shape's `raw_symbol`, scoped to `portfolio_ids` if given. **Never resolves anything itself** — like every Track A tool, it only commits verdicts `identity_resolver.resolve()` already reached (ADR-004: zero new identity logic in this module).

```python
@dataclass(frozen=True)
class BackfillReport:
    run_id: str
    portfolios_scanned: Sequence[int]
    transactions_updated: int
    portfolio_items_updated: int
    watchlist_rows_updated: int
    still_unresolved_transaction_count: int   # the Track A adjudication backlog, counted per this run's scope
    dry_run: bool
```

### 5.2 `registry_replay_parity.py` (new)

```python
def capture_golden_baseline(db: Session, portfolio_id: int) -> GoldenBaseline
def compare_against_baseline(baseline: GoldenBaseline, rebuilt: RebuildResult) -> ParityReport

@dataclass(frozen=True)
class ParityReport:
    portfolio_id: int
    is_bit_identical: bool
    snapshot_diffs: Sequence[SnapshotDiff]     # empty iff is_bit_identical
    holding_diffs: Sequence[HoldingDiff]       # empty iff is_bit_identical
```

Thin wrapper, not a new comparison algorithm: `capture_golden_baseline` runs `portfolio_rebuilder.rebuild_portfolio(..., dry_run=True)` once (pre-Stage-4, symbol-keyed) and serializes its `RebuildResult`; `compare_against_baseline` reuses the exact MATCH/DIFFERENT/MISSING/EXTRA diff shape `portfolio_rebuilder.py`'s own Stage 4 reconciliation already produces (§6 of this document reuses, not reinvents, that comparator).

### 5.3 `portfolio_transactions.py` — additive resolve-and-write

```python
def execute_buy(db, ws_id, portfolio_id, symbol, shares, price_per_share, ...) -> dict:
    resolved = registry_lookup.resolve_asset(db, symbol)
    asset_id = resolved.asset_id if isinstance(resolved, registry_lookup.AssetView) else None
    # ...existing PortfolioItem lookup-or-create, now also setting/backfilling .asset_id...
    # ...existing Transaction construction, now also setting asset_id=asset_id...
```

No signature change. `asset_id` is derived internally, exactly the way `sector` already is via `_fetch_sector()` at add-time (ARCHITECTURE.md's existing "Sector stored at add-time" pattern) — this design reuses that established idiom rather than inventing a new one.

### 5.4 `asset_definition.py` (new — see §8 for the full mechanism)

```python
def get_definition(asset_type: AssetType) -> AssetDefinition
def validate_against_definition(claim: AssetClaim, definition: AssetDefinition) -> Sequence[str]   # returns violation messages, empty if valid
```

---

## 6. Reused Comparator: Replay Diffing

No new diff algorithm. `portfolio_rebuilder.py`'s Stage 4 reconciliation (`_reconcile_portfolio_items`, `_reconcile_snapshots`) already computes exactly the MATCH/DIFFERENT/MISSING/EXTRA classification a parity gate needs — the only change Stage 4 requires is that its dict-builders key by `replay_key(ctx)` instead of `.symbol`/`ctx.raw_symbol` (§7.4). `registry_replay_parity.py` (§5.2) calls this existing function twice — once against the pre-cutover baseline, once against the post-cutover rebuild — rather than writing a second comparator, per ADR-004.

---

## 7. Migration Plan

Ordered, gated, per-portfolio wherever the gate allows it (Migration Principle 3). Every stage's regression discipline follows the epic's own established practice: `git stash` isolation, before/after pass-count delta, byte-identical pre-existing-failure set, asserted with numbers — not claimed.

### Stage 0 — ADR-005 Precondition: Fix the Alias-Splitting Defect

**Must complete, platform-wide, before any golden baseline is captured (ADR-005, hard gate).**

- Ship `replay_key.py` (§2.1, §5.2).
- Repoint `portfolio_rebuilder.py`'s `_PortfolioState.holdings` dict, `_reconcile_portfolio_items`'s `current`/`recon` dicts, and `_generate_execution_plan`'s symbol-set diff from `ctx.raw_symbol`/`.symbol` to `replay_key(ctx)`. At this stage `ctx.asset_id` is always `None` (Stage 2 hasn't run yet), so `replay_key()` degrades exactly to ADR-005's originally specified fix: key by `canonical_symbol`. This is intentional — Stage 0 delivers ADR-005's fix on its own merits, independent of Registry backfill, and is safe to ship and verify in isolation.
- `ledger_validator.py` CHECK 2 (`_check_symbol_aliases`) is rewritten to assert **zero** aliasing under `replay_key()` rather than merely flag it at WARNING — it becomes the mechanical proof that Stage 0 is complete, run against every portfolio.
- **Definition of Done:** `ledger_validator.py` CHECK 2 finds zero `SYMBOL_ALIAS` findings across every portfolio in the platform; `portfolio_rebuilder.py`'s full existing test suite passes with only the expected, intentional behavior change (aliased holdings now merge); any portfolio where the merge changes a previously-reported NAV/holding count is individually reviewed and the change documented in DECISION_LOG.md per ADR-005 §"Consequences" ("any correction applied before baseline capture must be documented").

### Stage 1 — Golden Baseline Capture (M0's deliverable, now unblocked)

- Run `registry_replay_parity.capture_golden_baseline()` for every portfolio, post-Stage-0. Store durably (versioned storage, outside the operational DB, per Migration Principle 7 — verification is a deliverable).
- Run `verify_snapshots` and `validate_ledger` on every portfolio; any open finding is dispositioned (fixed or explicitly waived in writing) before its portfolio's baseline is treated as canonical — ADR-005's own "no silent waiving" rule.
- **These baselines are the fixed parity reference for the rest of this document.** No further exception is granted once captured (ADR-005).

### Stage 2 — Ledger Asset ID Backfill

- Alembic migration (§4.1) ships first — additive, zero behavior change on its own (every new column is nullable and unread until Stage 4).
- Run `ledger_asset_backfill.backfill_ledger_asset_ids()` (§5.1) in `dry_run=True` first, review the `BackfillReport`, then commit per-portfolio.
- **The residual 21% (11 unresolved transactions, 2 duplicate clusters) is Track A's own named adjudication debt** (per ASSET_REGISTRY_RETROSPECTIVE.md's own accounting) — it is **not** this stage's job to clear it, and it does not block this stage: those transactions simply keep `asset_id = NULL` and fall through `replay_key()`'s second tier, exactly as designed (§2.1, §4.1). A portfolio is eligible for Stage 4 cutover once **its own** transactions are either resolved or the remainder is explicitly reviewed and accepted at `canonical_symbol`-tier keying (not blocked platform-wide by another portfolio's unresolved backlog).

### Stage 3 — Write-Path Cutover (resolve at write time, §2.3)

- Ship the `execute_*` resolve-and-write changes. New transactions from this point forward carry `asset_id` at write time; no further backfill needed for them.
- Purely additive, zero risk to existing behavior — `Unresolved` writes `NULL`, identical to today.

### Stage 4 — Replay Cutover (the hard gate)

Per portfolio, in this order:
1. Confirm Stage 2 backfill ran for this portfolio (`BackfillReport.still_unresolved_transaction_count` reviewed and accepted).
2. Run `rebuild_portfolio(..., dry_run=True)` with `replay_key()`-based keying (now genuinely `asset_id`-preferring, since Stage 2 populated the column).
3. `registry_replay_parity.compare_against_baseline()` against this portfolio's Stage 1 baseline. **`is_bit_identical` must be `True`.** Because Stage 0 already delivered the only legitimate baseline-vs-post-migration difference (alias merging) *before* the baseline was captured, this comparison should show zero diffs by construction — any diff found here is a **new** defect, not an expected migration effect, and blocks cutover for that portfolio until root-caused (this is precisely the discipline ADR-005 §"Consequences" describes: post-baseline defects follow the ordinary repair path, they do not get grandfathered into "expected migration noise").
4. Flip the portfolio's cutover flag (§9). Live replay for this portfolio now runs `asset_id`-preferring; the flag is reversible.
5. Probation period (§9) elapses; only then is the portfolio considered part of M5 Track B's Definition of Done.

### Stage 5 — M6 Native Integration (per consumer, parallelizable, no further hard gate)

Every module the Compatibility Layer already wired to `resolve_asset()` at read time is repointed to read the now-materialized `asset_id` directly. Ordered by leverage, matching the read-path plan's own phase numbering where a module already has a phase:

| Consumer | Compatibility-Layer state (today) | Native Integration change |
|---|---|---|
| **Recommendation write path** (`registry_recommendation_context.py`) | Resolves live at write time via `resolve_asset()` | Unchanged in mechanism (still write-time), but the *source* symbol's `Transaction`/`PortfolioItem.asset_id` is now available as a faster first-check before falling to live resolution for genuinely new symbols |
| **AI Evaluation plan-vs-live join** (`execution_ledger.py::_linked_transactions`) | `match_known_symbols()` string-matching (§2.3 item 1 of the read-path plan; explicitly documented as "requires M5 Track B to close completely") | **Closes the gap named in the Compatibility Layer's own documentation.** Joins on `Transaction.asset_id == plan_asset_id` directly; `match_known_symbols()` remains only as the fallback for the still-unresolved residual (§2.1's third tier) |
| **`.BK`-variant shim callers** (`basket_simulation.py`, `execution_plan.py`, `position_sizing.py`, `allocation_engine.py`, `idea_review.py`, `portfolio_construction.py`) | Call `registry_symbol_matching.match_known_symbols()` per invocation | Read `PortfolioItem.asset_id` directly where the holding is already a known DB row (the common case); `match_known_symbols()` retained only for symbols not yet in any portfolio (e.g. a freshly-submitted idea) |
| **Watchlist read path** | Read-time `resolve_asset()`/`resolve_many()` per request | `Watchlist.asset_id` read directly; `resolve_asset()` retained as fallback only for unresolved rows |
| **Sector classification** (`main.py::_get_sector`) | Read-time `resolve_asset()` then `classification["SECTOR"]` | Unchanged — classification is a per-asset dated fact looked up by `asset_id`, and `asset_id` is now available on the calling row directly rather than re-derived; the lookup itself (`AssetClassification` by `asset_id`) doesn't change |
| **Optimizer internal dict-keys** (`agents/optimizer.py` `score_map`/`pc_map`/`alloc_map`) | Symbol-keyed throughout | Rekeyed to `asset_id` where resolvable, symbol retained as a **data field**, never a key, on each entry. AI prompt/response JSON contract is explicitly **not** touched (OPTIMIZER_PHILOSOPHY.md §6 — identity resolution is arithmetic, stays outside the probabilistic layer; this is a restatement, not a new decision) |
| **Consensus engine set-overlap** (`_consensus_engine`) | Symbol sets (`l1_sells & l2_buy_syms`) | Same math over `asset_id` sets once the optimizer's internal dicts carry it; numerically re-verified identical on every already-resolved symbol (regression test) |
| **`policy_engine.py` violation strings / `execution_optimizer.classify_reason`** | Symbol interpolated into free text, recovered by substring search | Named as real technical debt by the M6 Compatibility-Layer's own Phase 5 review, explicitly deferred there as "a business-logic redesign, not a read-path fix." This document does not resolve it either — `policy_engine.py`'s `violations` model would need a structured `subject_asset_id` field, which is a change to the optimizer's constraint-resolution output contract and belongs to a future, explicitly-scoped optimizer change, not this migration. Left as documented debt (§10). |
| **Shadow portfolios** (`shadow_tracker.py`) | Symbol-keyed `{"symbol": ..., "shares": ...}` dicts | New shadows gain an additive `asset_id` field in the same dict shape; existing frozen `inception_holdings_json` rows are never touched (immutability) |
| **Factor engine, calibration** | Symbol-keyed dict joins | Switch to `asset_id` joins where resolvable; both already confirmed low-risk by the Compatibility-Layer's own audit |

**Explicitly not in Stage 5:** anything the Compatibility-Layer's Phase 5 completion review already classified as "no identity join to fix," "pure function, deliberately Registry-free," or "genuine join, deliberately deferred" (`horizon_grader.py`) — re-litigating those conclusions is out of this document's scope; they were reached by a full-file audit this document has no new evidence to overturn.

### Stage 6 — Contract (M7)

Named for completeness only; out of this document's scope per the parent plan (ASSET_REGISTRY_IMPLEMENTATION_PLAN.md's own M7 gate: requires Track B *and* Native Integration complete, plus probation periods elapsed, plus one explicit go decision). Retires the Compatibility Layer's fallback paths and the `symbol` columns' status as *keys* — never as evidence, which per ASSET_REGISTRY.md §3 stays in the evidence tier forever.

---

## 8. Asset Definition v1 — Technical Design

Per [asset_foundation.md](../architecture/asset_foundation.md) §6 and §8, a definition is "a declarative behavior contract, written in a closed vocabulary the platform owns" — not metadata, not an executable plugin. This section designs the mechanism for exactly two definitions: **equity** and **cash**. No new asset class is implemented; this is the vocabulary and the reading/validation surface only.

### 8.1 Storage format: code, not data

**Decision: the vocabulary is a versioned Python module, not a database table.** This follows directly from asset_foundation.md §6's own conclusion and §7.6's named risk (definition vocabulary sprawl): "the vocabulary itself is the one thing in this domain that changes by deliberation rather than by data." A DB-editable `asset_definitions` table would let the vocabulary grow by a runtime write instead of a code review — precisely the failure mode §7.6 warns against. This also matches an already-established pattern in this codebase: `AssetType`, `AssetStatus`, `IdentifierType`, and `RelationshipType` (M1) are compile-time enums for exactly this reason ("each is a small, closed, structurally load-bearing set" — M1's own implementation note), and `ResolutionPolicy`/`DEFAULT_POLICY` (M3) is a frozen dataclass instance, not a DB row, for the same reason.

```python
# services/asset_definition_domain.py

class Capability(str, Enum):
    SUPPORTS_OHLC = "SUPPORTS_OHLC"
    SUPPORTS_DIVIDENDS = "SUPPORTS_DIVIDENDS"
    SUPPORTS_FRACTIONAL_TRADING = "SUPPORTS_FRACTIONAL_TRADING"
    SUPPORTS_CORPORATE_ACTIONS = "SUPPORTS_CORPORATE_ACTIONS"
    SUPPORTS_DAILY_PRICING = "SUPPORTS_DAILY_PRICING"
    SUPPORTS_INTRADAY_PRICING = "SUPPORTS_INTRADAY_PRICING"
    SUPPORTS_INTEREST = "SUPPORTS_INTEREST"
    # closed set for v1 — UNIVERSAL_ASSET_ARCHITECTURE.md §5 names the full future vocabulary;
    # only the members equity/cash actually need are declared now (asset_foundation.md §8: "deliberately two, deliberately unglamorous")

@dataclass(frozen=True)
class AssetDefinition:
    asset_type: AssetType
    version: int
    capabilities: FrozenSet[Capability]
    allowed_transaction_types: FrozenSet[str]   # the flow-type vocabulary this class may post
    fractional_default: bool
    lot_size_applicable: bool

EQUITY_V1 = AssetDefinition(
    asset_type=AssetType.EQUITY,
    version=1,
    capabilities=frozenset({
        Capability.SUPPORTS_OHLC, Capability.SUPPORTS_DIVIDENDS,
        Capability.SUPPORTS_CORPORATE_ACTIONS, Capability.SUPPORTS_DAILY_PRICING,
        Capability.SUPPORTS_INTRADAY_PRICING,
    }),
    allowed_transaction_types=frozenset({"BUY", "SELL", "DIVIDEND", "INITIAL_POSITION", "QUANTITY_CORRECTION"}),
    fractional_default=False,
    lot_size_applicable=True,
)

CASH_V1 = AssetDefinition(
    asset_type=AssetType.CASH,
    version=1,
    capabilities=frozenset({Capability.SUPPORTS_INTEREST}),
    allowed_transaction_types=frozenset({"DEPOSIT", "WITHDRAW", "INITIAL_CASH"}),
    fractional_default=True,
    lot_size_applicable=False,
)

_DEFINITIONS: Mapping[AssetType, AssetDefinition] = {
    AssetType.EQUITY: EQUITY_V1,
    AssetType.CASH: CASH_V1,
}
```

### 8.2 Loading

```python
# services/asset_definition.py
def get_definition(asset_type: AssetType) -> AssetDefinition:
    """Raises KeyError for any AssetType not yet defined — fail loud, never guess a definition."""
```

No I/O, no session, no caching layer — the entire vocabulary is a handful of frozen dataclass instances resident in the process, which is both simpler and more honest than adding a cache for data that never has staleness to begin with (contrast with `registry_lookup.py`'s TTL cache, which exists because its underlying data — Registry identity — genuinely changes at runtime; a definition does not, by design).

### 8.3 Versioning and compatibility guarantees

- `AssetDefinition.version` is an explicit field, bumped on any vocabulary change to that asset type. Old versions are **never deleted from the module** — `EQUITY_V1` stays even after a hypothetical `EQUITY_V2` exists, because a definition's version at a point in time is itself a fact a future audit or replay-adjacent question ("what could this asset type do as of 2026-08?") might need, mirroring `AssetClassification`'s dated-fact discipline conceptually (the mechanism differs — git history + an explicit field, not a DB table — because the vocabulary itself, unlike a classification value, is not asset-instance data; see §8.1).
- **Compatibility guarantee 1 — additive-only within a version.** A version's `capabilities` set, once shipped, never shrinks. Removing a capability requires a new version and a DECISION_LOG.md entry (this is a governed vocabulary extension per asset_foundation.md §6, and removal is the sharper case of extension).
- **Compatibility guarantee 2 — unknown capabilities are unsupported, never fatal.** Any consumer testing `Capability.X in definition.capabilities` must treat a missing flag as "does not support," never raise. This is what makes a *future* capability additively introducible without touching every existing consumer (the same principle UNIVERSAL_ASSET_ARCHITECTURE.md §5 states for the full model, scoped here to the two live definitions).
- **Compatibility guarantee 3 — the vocabulary test before any addition.** Per asset_foundation.md §7.6: before any new `Capability` member is added, the test is "does an engine need to *behave differently* because of this?" — if only analytics or presentation cares, it belongs in classification (§8's dimension model, unchanged) or metadata, not here.

### 8.4 Capability discovery

`AssetView` (`registry_lookup.py`) gains one additive field:

```python
@dataclass(frozen=True)
class AssetView:
    # ...existing fields unchanged...
    capabilities: FrozenSet[Capability] = field(default_factory=frozenset)  # NEW
```

Populated inside `resolve_asset()` by one extra line — `get_definition(asset.asset_type).capabilities` — after the existing `AssetType` is already known from the resolved `Asset` row. Zero new DB reads (the `asset_type` column is already fetched), zero new cache entries needed (definitions aren't cached separately; they're computed from data already in the cached `AssetView`). Any engine already calling `resolve_asset()` gets capability discovery for free the moment it upgrades to read the new field; no engine is required to change to keep working (additive field, per ENGINEERING_PRINCIPLES.md and the epic's own "Additive API evolution" practice).

### 8.5 Validation

```python
def validate_against_definition(claim: AssetClaim, definition: AssetDefinition) -> Sequence[str]:
    """Pure. Returns human-readable violation strings; empty sequence means valid."""
```

Called once, optionally, inside `AssetRegistryService.mint_asset()` (M1, unmodified core — this is a new, optional pre-check a caller may run before minting, not a change to `mint_asset()`'s own contract) to catch, for example, an equity claim missing `exchange` — but never blocks a mint on its own; per ASSET_REGISTRY.md §7 ("Missing identifiers... absence is data"), validation *informs*, adjudication (a human or the resolver) still *decides*. This mirrors the platform-wide judgment/arithmetic boundary (OPTIMIZER_PHILOSOPHY.md §6): the definition contract computes facts about conformance; it never itself refuses a mint.

### 8.6 What this explicitly does not do

No new asset class (ETF, fund, gold, crypto, property — all named in asset_foundation.md §8's Future Extensions, all explicitly out of M6). No capability beyond what equity and cash's *already-hardened, already-shipped* behavior needs — every capability listed in §8.1 corresponds to something `services/portfolio_transactions.py` and `services/broker_fees.py` already do today, not a new feature. No engine is changed to *consume* capabilities in this document — §5's table names capability discovery as available; wiring a specific engine to branch on `Capability.X` instead of an `if asset_type ==` check (where any such check exists today) is Stage 5 work, tracked per-consumer, not a blanket requirement of shipping the vocabulary itself.

---

## 9. Rollout Plan

- **Unit of rollout: one portfolio.** Not a global flag day (Migration Principle 3). A boolean, `Portfolio.replay_asset_id_native` (nullable, default `False`, additive column alongside §4.1's migration), gates Stage 4 per portfolio.
- **Canary selection.** First portfolios cut over are chosen by lowest risk: zero unresolved transactions (from `BackfillReport.still_unresolved_transaction_count == 0`) and smallest transaction count — the same "lowest-stakes pilot consumer" logic the Compatibility Layer already used for its own Watchlist pilot (REGISTRY_INTEGRATION_GUIDE.md).
- **Probation period.** Matching the parent plan's own Definition of Done language ("accounting engines running id-keyed in production for a probation period"): **21 days** per portfolio, chosen to span at least three weekly snapshot/attribution cycles and the existing 17:45 ICT daily scheduler's full weekly rhythm, before a portfolio is counted toward M5 Track B's completion. During probation, both keying paths remain live in code (the flag is reversible in either direction) — this is not a monitoring-only period, it is a genuine dual-path window.
- **Rollback.** Flip `replay_asset_id_native` back to `False`. Because `ReplayKey`'s fallback tiers are themselves stable and deterministic (§2.1), reverting a single portfolio never destabilizes any other portfolio's replay, and never requires a data rollback — only a re-run of `rebuild_portfolio()` under the old keying, which is exactly what dry-run parity checking already exercises routinely.
- **M5 Track B Definition of Done** (restated precisely against this document's stages): 100% of portfolios have completed Stage 4 with `is_bit_identical=True` and cleared probation; every portfolio's residual `NULL asset_id` population is reviewed and either resolved or explicitly, individually accepted (ADR-005's "explicitly and individually waived in writing" standard, applied per-portfolio rather than platform-wide).
- **M6 Native Integration rollout** is per-consumer (§7 Stage 5's table), each independently shippable and regression-tested, with no dependency on every portfolio having finished Stage 4 first — a consumer reading `asset_id` correctly handles `NULL` (falls back to symbol-keyed behavior for that one row) exactly as the Compatibility Layer already does today for `Unresolved`.

---

## 10. Testing Strategy

### 10.1 Unit tests (new modules, pure logic)

- `replay_key.py` — every tier of the fallback (`asset_id` present; only `canonical_symbol` present; only `raw_symbol` present; cash-only → `None`), plus the specific regression case ADR-005 names (`KBANK` and `KBANK.BK` produce the same `ReplayKey` once both share a `canonical_symbol`, before either has an `asset_id`).
- `asset_definition_domain.py` / `asset_definition.py` — `get_definition()` raises for an undefined `AssetType`; `EQUITY_V1`/`CASH_V1` capability sets match §8.1 exactly; `validate_against_definition()` returns the expected violation set for known-bad claims and empty for known-good ones.
- `ledger_asset_backfill.py` — mirrors `test_migration_executor.py`'s existing fixture idiom (in-memory SQLite, `_shape`/`_result` helpers): dry-run makes zero writes; commit is idempotent (re-running against already-backfilled rows changes nothing); scoping by `portfolio_ids` never touches another portfolio's rows.

### 10.2 Integration tests

- Full backfill dry-run against a production-like fixture (reusing the same fixture shape M5 Track A's own bootstrap validation used — 52 transactions, 25 claim shapes, 2 duplicate clusters) — assert the `BackfillReport` counts match the already-known 41/52, 21/25 figures exactly, as a regression guard that nothing in this document's plumbing silently changes Track A's own adjudication results.
- `execute_buy`/`execute_sell`/`execute_initial_position`/`execute_quantity_correction` — assert `Transaction.asset_id` and `PortfolioItem.asset_id` are populated for a Registry-known symbol and `NULL` (never an exception, never a blocked write) for an unknown one.

### 10.3 Replay validation (the hard gate, ADR-005)

- **The parity test is the acceptance test for Stage 4, full stop.** Per portfolio: `capture_golden_baseline()` (post-Stage-0) vs. `rebuild_portfolio()` under `ReplayKey` keying (post-Stage-2) via `compare_against_baseline()`, asserting `is_bit_identical=True`. This is not a sampling check — it runs for every portfolio before that portfolio's flag flips (§9).
- `ledger_validator.py` CHECK 2, re-run platform-wide post-Stage-0, asserting zero `SYMBOL_ALIAS` findings — the mechanical proof Stage 0's Definition of Done is met.
- `verify_snapshots` and `validate_ledger`, re-run post-Stage-4 per cut-over portfolio, asserting no new findings relative to the Stage 1 baseline run.

### 10.4 Migration validation

- Idempotency: running `backfill_ledger_asset_ids()` twice against the same portfolio produces an identical `BackfillReport` (zero additional writes) the second time.
- Coverage accounting: `BackfillReport.still_unresolved_transaction_count`, summed across all portfolios, matches the platform-wide unresolved count independently computed by `migration_planner.plan_migration()` run fresh — the same number reported two different ways must agree.

### 10.5 Regression tests

Every existing suite (`test_asset_registry.py`, `test_registry_service.py`, `test_identity_resolver.py`, `test_provider_adapter.py`, `test_registry_lookup.py`, `test_registry_symbol_matching*.py`, `test_registry_recommendation_context.py`, `test_bootstrap_planner.py`, `test_registry_bootstrap.py`, plus the full `portfolio_rebuilder`/`ledger_validator`/`portfolio_transactions` suites) run before and after every stage, via the epic's own established `git stash`-isolation practice — a before/after pass-count delta and a byte-identical pre-existing-failure-set diff, recorded in this document's own changelog (§12) the same way every prior milestone recorded it, not merely claimed.

### 10.6 Invariant tests — constitutional laws as executable tests

Per the milestone brief's explicit request, each named constitutional invariant becomes a concrete, automatable check:

| Constitutional law | Executable test |
|---|---|
| "Registry is the single institutional authority" | Static/CI check: no file outside `services/asset_registry.py`, `services/registry_service.py`, `services/identity_resolver.py` calls `AssetRegistryService.mint()`/`registry_service.mint_asset()`'s underlying core mint path directly (grep-based allowlist check, mirroring the platform's existing "no engine can tell what any asset is called" audit already named in ASSET_REGISTRY.md §10) |
| "Asset identity is permanent" | Existing M1 tests (`test_asset_registry.py`) already assert no reuse/reassignment; unchanged, re-run every stage |
| "Replay never re-resolves identity" | `transaction_canonicalizer.py`'s `asset_id` field is asserted, by a dedicated test, to come from `Transaction.asset_id` only — a test that monkeypatches `registry_lookup.resolve_asset` to raise, then asserts `canonicalize_transactions()` still succeeds unchanged, proving no resolution call occurs in the replay path |
| "Definitions are declarative contracts" | `asset_definition_domain.py`'s `AssetDefinition` fields are typed as immutable value types only (`FrozenSet`, `bool`, `int`, `str` enums) — a test asserts no field is `Callable` (no executable content ever enters the vocabulary) |
| "No executable asset plugins" | Same test as above, restated: `AssetDefinition` cannot hold code, only declarations |
| "No asset-specific logic inside engines" | The existing platform-wide grep audit (already informally practiced per the retrospective's "no engine below the resolution boundary should be able to tell what any asset is called") formalized as a CI check scanning `portfolio_rebuilder.py`, `ledger_validator.py`, and `agents/optimizer.py` for `AssetType.`-branching outside `asset_definition.py`/`registry_lookup.py` themselves |
| "Market providers are witnesses, never authorities" | Existing M4 test (`test_provider_adapter.py::test_adapter_methods_take_no_session_parameter`) already enforces this structurally; unchanged |
| "Structural Events never mutate accounting directly" | Out of this document's scope (Structural Events are a future M6 charter item per asset_foundation.md §8's Future Extensions, not built here) — noted for completeness, no test needed yet |
| "Ledger remains the single source of truth" | `ledger_asset_backfill.py`'s own test suite asserts it never writes to `assets`/`asset_identifiers` (mirrors `migration_executor.py`'s existing `test_execute_migration_never_mints` pattern) — it only ever reads Registry state and writes ledger-table `asset_id` columns, never the reverse |

---

## 11. Risks & Mitigations

1. **Residual unresolved population (21% today) permanently limits some portfolios to `canonical_symbol`-tier keying.** Mitigation: `ReplayKey`'s design makes this safe rather than blocking — a portfolio with unresolved symbols still gets ADR-005's alias-fix benefit and correct, deterministic replay; it simply doesn't yet get permanent-identity-level protection for those specific symbols. Named, not hidden: `BackfillReport` surfaces the count every run, and Stage 4 cutover review explicitly reads it.
2. **`portfolio_snapshots.holdings_json` historical immutability means pre-cutover snapshots can never gain `asset_id`.** Accepted permanently, per §4.2 — matches this codebase's own established precedent for frozen JSON blobs (`RecommendationSnapshot`, `ShadowPortfolio.inception_holdings_json`). Not a defect; a consequence of Design Invariant 1 applied consistently.
3. **`transaction_canonicalizer.py` purity is preserved only because `asset_id` is a materialized column** — if a future change tried to add resolution logic back into this function "for convenience," it would silently reintroduce the exact risk `registry_lookup.py`'s own docstring warns against. Mitigation: the invariant test in §10.6 ("Replay never re-resolves identity") is specifically designed to catch this regression mechanically, not just in code review.
4. **Stage 0's alias-merge changes historical numbers for any portfolio that actually has an aliased pair.** This is a real, disclosed behavior change (ADR-005 anticipates it explicitly). Mitigation: per-portfolio review before baseline capture, documented in DECISION_LOG.md per ADR-005's own requirement — not silently absorbed into "the migration."
5. **`policy_engine.py`/`execution_optimizer.classify_reason`'s string-coupling remains unfixed.** Named debt, not resolved by this document (§7 Stage 5's table) — a business-logic redesign of the violations contract, outside a migration document's authority per the Compatibility-Layer's own Phase 5 review, which reached the same conclusion independently.
6. **Two-hop backfill ordering risk** (Registry bootstrap must mint before ledger backfill can attach, but bootstrap itself depends on a fresh `plan_migration()` pass) — mitigated by §7 Stage 2's explicit ordering, reusing the exact sequence M5 Track A's own implementation notes already recommend (`plan_migration → bootstrap_planner → registry_bootstrap → plan_migration again → migration_executor → ledger_asset_backfill`), not a new sequence invented for this document.
7. **Probation-period portfolios still routing through the old keying path indefinitely if nobody revisits the flag.** Mitigation: `BackfillReport`/parity results are logged per run, making stalled cutovers observable (ENGINEERING_PRINCIPLES.md "Failure Handling" — degraded/incomplete states must be observable, not silent); the M5 Track B Definition of Done (§9) is explicitly "100% of portfolios," not "the ones somebody remembered."

---

## 12. Governance

This document is a level-4 Technical Design Document (platform_architecture.md §11), executing the already-frozen M5 Track B and M6 Native Integration entries of [ASSET_REGISTRY_IMPLEMENTATION_PLAN.md](ASSET_REGISTRY_IMPLEMENTATION_PLAN.md) §5, and the "Registry-native integration" and "The definition contract, v1" items of [asset_foundation.md](../architecture/asset_foundation.md) §8's M6 Core Foundation. It does not amend either. Implementation of any stage in §7 should record its outcome here (changelog, mirroring every sibling document's practice) and, where a stage changes recorded historical numbers (Stage 0's alias merge — risk 4 above), in [DECISION_LOG.md](../engineering/DECISION_LOG.md), per ADR-005's own documentation requirement.

### Changelog

**Stage 5 — M6 Native Integration, partial (2026-07-11).** Per §7 Stage 5's own framing ("per consumer, parallelizable, no further hard gate"), five consumers migrated, several named debt confirmed still deferred. No schema change; every edit additive (new optional parameters/keys, existing signatures and call sites unaffected wherever a caller doesn't opt in). No portfolio flag, no accounting/replay path touched (out of Stage 5's scope — that's Stage 4, already shipped).

Migrated:
- **AI Evaluation plan-vs-live join** (`services/evaluation/execution_ledger.py::_linked_transactions`) — now joins `Transaction.asset_id` against each plan symbol's resolved `asset_id` before falling back to `match_known_symbols()`, exactly as this document's own §7 Stage 5 table specified.
- **`.BK`-variant shim callers** — `services/registry_symbol_matching.py::match_known_symbols()` gained an optional `known_asset_ids` parameter so a caller already holding a loaded `PortfolioItem`/`Watchlist` row can pass its materialized `asset_id` straight through, skipping a `resolve_asset()` call for that entry. Wired into `basket_simulation.py::_resolve_symbol_sectors` (also covers `portfolio_construction.py` and the basket-sector paths of `allocation_engine.py`/`position_sizing.py`, all of which call the same shared helper), `position_sizing.py`'s own holdings match, and all three `idea_review.py` call sites backed by `PortfolioItem`/`Watchlist` rows.
- **Watchlist read path** (`main.py::list_watchlist`) — rows with a materialized `Watchlist.asset_id` resolve by id directly; `resolve_asset()` by symbol remains the fallback for rows Track A hasn't adjudicated.
- **Portfolio snapshots** (`services/portfolio_snapshots.py`) — each `holdings_json` holding gains the additive `asset_id` key specified in §4.2 (`None` when not yet backfilled, absent entirely on any snapshot row predating this change).
- **Factor engine** (`services/analytics/factor_engine.py`) — `per_stock_scores` entries gain an additive `asset_id` data field (never a key), read off the already-loaded `PortfolioItem` row.

Reviewed and intentionally deferred (not migrated this stage):
- **Optimizer internal dict-keys / consensus engine set-overlap** (`agents/optimizer.py`) — the highest-blast-radius consumer in the table; `score_map`/`pc_map`/`alloc_map` are built from plain dicts (`_compact_p`/`_compact_w`) that do not carry `asset_id` without plumbing several upstream call sites first, and a key-type migration here touches the AI-facing allocation pipeline OPTIMIZER_PHILOSOPHY.md gates carefully. Left for a dedicated, explicitly-scoped follow-up rather than a partial patch bundled into a consumer-migration stage.
- **Calibration** (`services/decision_memory/calibration.py::_compute_signal_accuracy`) and **cache keys** (`AgentCache`, `AnalysisCache`) — both join through tables that carry no `asset_id` column; migrating either requires a schema change this stage's TDD scope does not authorize (§3 Module Structure lists no cache-table migration).
- **Benchmarks** (`BenchmarkPrice`) — not applicable. Index/ETF symbols (`^SET`, `QQQ`, …) are not Registry-adjudicated equities; no identity join exists to migrate.
- **Shadow portfolios** (`services/decision_memory/shadow_tracker.py`) — moderate complexity confirmed, plus a discrepancy from this document's own assumption discovered during review: `inception_holdings_json` is not genuinely immutable (`create_active_model_shadow`'s rebalance path rewrites it). Deferred pending a dedicated look rather than patched hastily here.
- **`policy_engine.py` / `execution_optimizer.classify_reason` string-coupling** — already named debt in §7 Stage 5's own table; re-confirmed out of scope (business-logic redesign).

Testing: unit tests for the new `known_asset_ids` parameter (`tests/test_registry_symbol_matching.py`), native asset_id-match regression tests with no `.BK` relationship at all (`tests/test_execution_ledger.py`, `tests/test_registry_symbol_matching_integration.py`, `tests/test_watchlist_registry.py`), additive-field tests (`tests/test_factor_engine_asset_id.py`, `tests/test_snapshot_coverage.py`). Regression: every touched consumer's existing test file re-run before/after, zero new failures; one unrelated pre-existing gap fixed in passing (`tests/test_snapshot_coverage.py` was missing the `models.asset` import needed to resolve `portfolio_items.asset_id`'s foreign key, breaking all 10 of its pre-existing tests independent of this change — confirmed via `git stash` comparison).

## Related Documents

- [ASSET_REGISTRY_IMPLEMENTATION_PLAN.md](ASSET_REGISTRY_IMPLEMENTATION_PLAN.md) — the M0–M7 plan this document is the Track B / Native Integration child of
- [M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md](M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md) — the Compatibility Layer this document's Stage 5 supersedes per consumer
- [ASSET_REGISTRY_RETROSPECTIVE.md](../architecture/ASSET_REGISTRY_RETROSPECTIVE.md) — history, lessons, and the exact coverage numbers this document's tests regress against
- [ADR-005](../decisions/ADR-005_REPLAY_CORRECTNESS_BASELINE.md) — the hard gate Stage 0 satisfies
- [asset_foundation.md](../architecture/asset_foundation.md) — the domain constitution; §8 names this document's two Core Foundation items
- [ASSET_REGISTRY.md](../architecture/ASSET_REGISTRY.md) — the frozen architecture this design implements against
