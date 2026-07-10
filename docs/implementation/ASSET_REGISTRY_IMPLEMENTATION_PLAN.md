# Asset Registry — Implementation Plan

_The engineering execution plan for the Asset Registry Epic: introducing platform-owned asset identity into a live production system without corrupting replay, accounting, or analytics._

_This document is neither architecture nor implementation. The architecture is frozen — [ASSET_REGISTRY.md](../architecture/ASSET_REGISTRY.md) and its handbook siblings define **what** the Registry is; this plan defines **how the platform gets there from here**, in what order, behind what safety mechanisms, and with what evidence of success. Where the two ever appear to disagree, the handbook wins and this plan is wrong._

_Companion documents: [UNIVERSAL_ASSET_ARCHITECTURE.md](../architecture/UNIVERSAL_ASSET_ARCHITECTURE.md) (the Asset model), [MARKET_DATA_PLATFORM.md](../architecture/MARKET_DATA_PLATFORM.md) (the resolution pipeline), [PROVIDER_INTERFACE.md](../architecture/PROVIDER_INTERFACE.md) (the adapter contract), [TRANSACTION_DOMAIN_MODEL.md](../architecture/TRANSACTION_DOMAIN_MODEL.md) (the ledger the migration must never disturb)._

---

## 1. Executive Summary

### Why this is the next milestone

The Architecture Handbook is complete, and nearly every planned domain stands on the same joint: **the ledger references assets by `asset_id`, never by symbols** (ASSET_REGISTRY.md §10). The Transaction Domain assumes it. The Corporate Action Domain adjudicates *into* it. Multi-currency, tax, and every future asset class presuppose it. The Registry is not one epic among peers — it is the load-bearing prerequisite for the rest of the roadmap, and every quarter it does not exist, the symbol-keyed surface area it must eventually replace keeps growing. Building it first is not preference; it is dependency order.

### Current limitations

Today the platform is symbol-keyed end to end. Provider-shaped symbol strings serve simultaneously as ledger keys, price-series keys, analytics dimensions, and display names — four jobs the architecture assigns to four different concepts. The consequences are already in the decision log: a vendor's depositary-receipt symbol convention had to be normalized at every call site; provider naming conventions leak into business logic; and the platform's history is silently exposed to every future decision of every namespace owner — a recycled ticker or a vendor suffix change can, in principle, weld two instruments' histories together or orphan years of records.

### Expected outcomes

At the end of this epic:

- Every asset the platform has ever recorded has exactly one permanent, platform-minted `asset_id`, with the existing symbols preserved as its evidence file.
- The transaction ledger, replay, snapshots, analytics, and AI evaluation reference assets by `asset_id`; symbols survive only at the resolution boundary and the presentation surface.
- Replay produces **bit-identical** results before and after migration — the migration's defining acceptance test.
- Providers are demoted from identity sources to witnesses: a vendor symbol change becomes a one-row mapping update instead of a codebase-wide incident.
- The platform is structurally ready for the next epics (Corporate Actions, Multi Currency, new asset classes) without further identity work.

---

## 2. Current State Analysis

Described conceptually — the platform's actual code is inventoried in M0, not assumed here.

### Current symbol usage

A single symbol string per instrument acts as the universal key. It appears in the transaction ledger, in holdings and snapshots, in price and indicator series, in optimizer inputs and recommendations, in the decision record, in attribution and timing analytics, and on screen. There is no distinction between "what this asset *is*," "what the provider *calls* it," and "what the user should *see*" — one string plays all three roles.

### Current provider assumptions

Symbols largely follow the primary market-data provider's naming conventions, including venue suffixes. The implicit assumptions are: one provider namespace, symbols are stable, one symbol denotes one instrument forever, and the provider's spelling is a safe permanent key. Each assumption is false in general and merely *usually true* for the current single-market, single-provider footprint — which is why the platform has survived so far, and why expansion beyond that footprint is blocked.

### Current coupling

Business logic can see — and therefore can depend on — provider naming. The DR-normalization incident is the canonical example: a vendor spelling convention became a concern of every call site instead of one boundary. Analytics dimensions (the stewarded sector taxonomy) attach to symbol strings. The replay engine's determinism currently rests on an unstated premise: that every symbol in the ledger will always mean what it meant when written.

### Current risks

- **Recycled or reassigned tickers** silently merging unrelated instruments' histories.
- **Vendor convention changes** requiring call-site-wide normalization sweeps (already happened once).
- **The same instrument entering through two doors** (CSV import vs. manual entry vs. feed) under two spellings, creating divergent records with no mechanism to notice.
- **Corporate actions with identity effects** (symbol changes, mergers) having no correct place to land — the platform can only mutate or duplicate a symbol, both wrong.

### Current technical debt

The debt is not messy code; it is a **missing institution**. Every symbol-keyed table, join, and cache is an IOU written against the day identity moves. The debt compounds: each new feature built symbol-keyed (and every epic in the roadmap would be) adds migration surface. This epic is the payoff point.

---

## 3. Target Architecture

The end state is fully specified by the handbook and is **not redesigned here**. In one paragraph, for orientation:

The Asset Registry ([ASSET_REGISTRY.md](../architecture/ASSET_REGISTRY.md)) becomes the one subsystem that answers "what is this?" It mints permanent, opaque `asset_id`s and once-only `canonical_symbol`s (§3); adjudicates every identity claim through candidate-matching, evidence-weighing, and decisive-or-ask verdicts (§4); treats each listing as its own identity with explicit relationships carrying sameness (§5); manages a lifecycle where minting is the only irreversible moment (§6); validates the one-instrument-one-asset guarantee loudly (§7); stewards classification as dated facts on a permanent spine (§8); treats providers as witnesses who may never rename, merge, or delete (§9); and underwrites the ledger rule that business logic uses `asset_id` only, with symbols confined to the resolution boundary and the presentation surface (§10).

The migration target, stated as the handbook's own audit: **no engine should be able to tell what any asset is called** (ASSET_REGISTRY.md §10).

---

## 4. Migration Principles

These principles bind every milestone. A milestone plan that violates one is wrong regardless of schedule pressure.

1. **The ledger is never rewritten — it is re-keyed additively.** Transaction rows gain an `asset_id` reference alongside the existing symbol; the symbol column is not dropped until parity is proven and the contract phase (M7) explicitly retires it. This is ADR-001 applied to the migration itself.
2. **Replay parity is the gate for everything.** Before any consumer switches keys, replay over the full history of every portfolio must produce results identical to a pre-migration golden baseline. Not approximately identical — identical. The existing `verify_snapshots` and `validate_ledger` audit tooling is the enforcement mechanism, extended where needed. Per [ADR-005 — Replay Correctness Baseline](../decisions/ADR-005_REPLAY_CORRECTNESS_BASELINE.md), "identical" means identical to *correct* accounting, not to the current implementation's defects: known correctness defects (e.g. the raw_symbol/canonical_symbol alias-splitting behavior found in M0) must be repaired before golden baselines are captured. **ADR-005 must be accepted before M0's golden baselines are captured, and before M5 Track B — Native Ledger Persistence begins.** (M5 Track A — evidence, planning, and bootstrap tooling — never runs replay and is not subject to this gate; see §5.)
3. **No flag days.** Old world and new world coexist for the entire epic. Every switchover is per-consumer, feature-flagged, reversible, and independently verifiable. There is no moment when the platform is broken-unless-everything-lands.
4. **Backward compatibility at every seam.** Existing imports, screens, and workflows keep working throughout. Users should be unable to tell the migration is happening except where the product deliberately improves (e.g., ambiguity surfacing on import).
5. **Backfill is adjudication, not string mapping.** The one-time resolution of historical symbols into minted identities goes through the same evidence-and-verdict discipline as live resolution (ASSET_REGISTRY.md §4). Decisive cases resolve in bulk; every ambiguity is surfaced to a human and the confirmation recorded. **No silent guessing during backfill** — a wrong historical mapping is exactly the multiplicative poison §7 warns about.
6. **Expand → verify → cut over → contract.** Every schema-touching step follows the parallel-change pattern: add alongside, backfill under audit, switch reads behind flags, remove only in M7.
7. **Instrumentation before migration.** Every milestone that moves data also ships the verification that proves it moved correctly. Verification is a deliverable, not an afterthought.
8. **One implementation per rule** (ADR-004). The resolver built for backfill is the same resolver used live afterward — no throwaway migration-only logic that then diverges from production behavior.

---

## 5. Milestone Breakdown

Suggested order: **M0 → M1 → M2 → M3 → M4 → M5 Track A → {M5 Track B ∥ M6 Compatibility-Layer} → M6 Native → M7**, with M3/M4 partially parallelizable after M2, M5 Track B and M6 Compatibility-Layer mutually independent of each other and safe to run concurrently, and M5 Track B remaining the hard gate before M6 Native Integration. Dependencies are noted per milestone and in the graph below. Per Migration Principle 2 (§4) and [ADR-005](../decisions/ADR-005_REPLAY_CORRECTNESS_BASELINE.md), M0's golden baselines may not be captured, and M5 Track B may not begin, until ADR-005 is accepted.

**Dependency graph (revised 2026-07-09 — see Changelog, §13).** The single chain M0→...→M7 originally suggested above is no longer the actual shape of the remaining work; M5 and M6 each branch into two tracks that proceed on independent schedules:

```
M0 → M1 → M2 → M3 → M4
                 │     │
                 │     └───────────────► M5 Track A  (COMPLETE, 2026-07-09)
                 │                            │
                 │                            ├──────────────► M5 Track B ──► M6 Native ──► M7
                 │                            │                (ledger backfill,    ▲
                 │                            │                 hard-gated on        │
                 │                            │                 Track A + ADR-005)   │
                 └────────────────────────────┴──────────────► M6 Compatibility- ────┘
                                                                 Layer (independent
                                                                 of Track B; a shim,
                                                                 retired at M7 like
                                                                 every other shim)
```

M6 Native Integration depends on **both** M5 Track B (hard gate, accounting correctness) and, in practice, benefits from M6 Compatibility-Layer having already converted most non-ledger call sites — but does not structurally require it. M7 requires M5 Track B and M6 Native complete, with their probation periods elapsed, regardless of whether Compatibility-Layer shipped first.

---

### M0 — Planning, Inventory, and Golden Baselines

**Goal.** Know exactly what exists before touching anything, and freeze the evidence of current correctness that every later milestone will be measured against.

**Scope.**
- A complete **symbol usage census**: every table, engine, cache, and surface that stores or branches on a symbol, classified as *ledger key / data key / analytics dimension / display*. This is the map every later milestone navigates by.
- A **symbol inventory** of the actual data: every distinct symbol in the ledger and price store, with per-symbol transaction counts, date ranges, and known oddities (DR spellings, delisted names, manual entries). This inventory is the raw input to the M5 backfill and the first estimate of how many ambiguities the human will need to adjudicate.
- **Golden baselines**: full-history replay outputs, snapshot series, and key analytics results for every portfolio, captured and stored as the parity reference. Run `verify_snapshots` and `validate_ledger` and record their clean (or explained) state — migrating on top of undiagnosed ledger issues would make parity failures ambiguous.
- Provider symbol convention inventory (suffixes, DR spellings, known quirks) from the decision log and operational experience.

**Deliverables.** Census document; symbol inventory with ambiguity estimate; golden baseline artifacts under version control or durable storage; a go/no-go review of any pre-existing ledger findings.

**Risks.** Undercounting symbol usage sites (mitigate: mechanical search plus per-engine owner review). Pre-existing ledger issues discovered late (mitigate: run the validators *first*; fix or explicitly waive before M1).

**Definition of Done.** Census reviewed; every ledger symbol appears in the inventory; golden baselines reproducible on demand; open ledger findings dispositioned.

**Depends on.** Nothing. **Unknowns resolved here:** true breadth of symbol coupling; true count of ambiguous historical symbols.

---

### M1 — Canonical Asset (identity core)

**Goal.** The permanent tier exists: the platform can mint an `asset_id` and `canonical_symbol`, attach an evidence file, and guarantee uniqueness — as a new subsystem, touching nothing existing.

**Scope.**
- The Asset identity record per ASSET_REGISTRY.md §3: permanent tier (opaque `asset_id`, once-only `canonical_symbol`) plus the evidence tier (external identifiers, per-provider symbol mappings, historical mappings that never expire).
- Lifecycle states per §6, including the claim states (Discovery/Candidate/Verified) and the bright line at minting.
- Relationship links between identities (§5) — the mechanism only; populating DR/wrapper relationships happens as they are encountered.
- Classification as dated, provenance-tagged facts (§8), seeded from the existing stewarded sector taxonomy rather than inventing a parallel one.

**Deliverables.** Identity storage and domain model; minting with uniqueness enforcement; evidence-file custody; lifecycle transitions with the irreversibility rule enforced; unit tests for every §12 principle expressible as a test (no reuse, no reassignment, historical mappings retained, etc.).

**Risks.** Scope creep into resolution logic (that is M3) or provider calls (M4). Modeling classification too rigidly to absorb the existing taxonomy (mitigate: seed from the real taxonomy in this milestone, not later).

**Definition of Done.** An asset can be minted, described, related, transitioned, and never un-minted; nothing in the existing platform references it yet; test suite green.

**Depends on.** M0 (the inventory shapes the evidence-tier model's first citizens).

**Status: Complete (2026-07-09).**

**Implementation notes.**
- New, standalone code only — zero existing files modified. `backend/models/asset.py` (`Asset`, `AssetIdentifier`, `AssetRelationship`, `AssetClassification`, sharing the existing `Base`); `backend/services/asset_domain.py` (enums, `AssetId` identity type, unpersisted `AssetClaim`/`IdentifierRecord` value objects); `backend/services/asset_repository.py` (pure persistence, no rules); `backend/services/asset_registry.py` (`AssetRegistryService` — the one authoritative implementation of minting, identifier stewardship, lifecycle legality, relationship linking, and classification stewardship, per ADR-004); Alembic migration `d6f8a0b2c4d6` (4 new tables, no FK from any existing table); `backend/tests/test_asset_registry.py` (18 unit tests, one per §12 principle expressible as a test).
- `asset_id` (the `Asset.id` PK) is exposed to Python callers only through `AssetId = typing.NewType("AssetId", int)`, not a plain `int` alias — static type-checking treats it as distinct from an ordinary integer, while remaining zero-cost at runtime (no wrapper object). This keeps the "opaque, permanent identity" contract of §3 separate from "autoincrement integer," which is a persistence detail that could change (e.g., to a UUID) without it being a domain change.
- **`canonical_symbol` vs. `display_symbol` — resolved explicitly**, since this was flagged during design review as a place the identity model could become ambiguous: `canonical_symbol` is assigned once at minting and is never reassigned, *including when the real-world ticker it was minted from later changes*. A ticker rename (rebrand, exchange-mandated change, DR re-listing) is an evidence-tier event — a new `AssetIdentifier` row is recorded (the superseded one is retained with `is_current=False`, never deleted) and `display_symbol` is updated to the new current-facing symbol. `asset_id` and `canonical_symbol` are untouched. Any future consumer rendering a symbol to a user must read `display_symbol`, never `canonical_symbol`. Documented on `Asset` in `models/asset.py` and in `asset_domain.py`'s module docstring.
- **Vocabulary split — enums vs. registry-managed strings**, also resolved during design review: `AssetType`, `AssetStatus`, `IdentifierType`, `RelationshipType`, and `ClassificationDimension` (the dimension name) are compile-time enums, because each is a small, closed, structurally load-bearing set — `AssetStatus` in particular *is* the lifecycle state machine, and its transition legality is enforced in code (`_ALLOWED_TRANSITIONS` in `asset_registry.py`). Classification *values* (e.g. a sector name) are deliberately plain, service-validated strings, not enum members — per §8 these are dated, provenance-tagged business content that evolves independently of code, matching how the existing `THAI_SECTOR_MAP`/`_DR_SECTOR_MAP` in `main.py` are already data rather than compiled constants.
- **Deviation — claim states are vocabulary-only, not persisted.** §6 asks for "claim states (Discovery/Candidate/Verified)." M1 models `ClaimStatus` (Discovery/Candidate) as an enum carried by the unpersisted `AssetClaim` value object consumed by `mint()`; there is no `asset_claims` table. Rationale: nothing produces a claim until the Symbol Resolver exists (M3), so a persisted pre-mint table would be speculative structure with no writer — contrary to "implement only the minimum foundation." "Verified" is not a distinct claim state in this implementation; minting *is* the verification act and always produces `AssetStatus.ACTIVE` directly. If M3 needs claims to survive across a process boundary (e.g., a review queue), that milestone will need to add persistence for them — noted here so it isn't mistaken for an oversight.
- **Deviation — classification is not pre-seeded from `THAI_SECTOR_MAP`/`_DR_SECTOR_MAP`.** The scope bullet ("seeded from the existing stewarded sector taxonomy rather than inventing a parallel one") is satisfied at the *model* level — `AssetClassification.value` is a free string validated against no compiled enum, so the existing taxonomy can be written through unchanged — but no seed script populated real rows in M1, since M1 mints no real assets (no consumer exists yet; the platform still runs entirely on symbols). Backfilling classification for real assets is M-later work, once something (M3/M4) actually mints them.
- Capability flags (§5 of UNIVERSAL_ASSET_ARCHITECTURE.md) and the open `metadata` bundle (§2) were excluded from the `Asset` table — not called out in this milestone's scope bullets, and nothing consumes them yet.
- No API endpoints were added; the service is in-process only, per M2 owning "the authoritative service boundary."
- Migration `d6f8a0b2c4d6` chains off the actual Alembic head `c5d7e9f1a3b5` (`add_recommendation_grades`), found via `alembic heads` rather than by filename/date sorting — several existing migration files are not date-ordered with the true chain, so this was verified mechanically, not assumed.
- Test suite: 18/18 new tests pass. Full backend suite run before and after this change (`77 failed, 896 passed, 32 skipped` baseline with the M1 files removed; `77 failed, 914 passed, 32 skipped` with them restored) — identical pre-existing failure set, +18 newly passing, zero regressions. The 77 pre-existing failures are environment issues (a pandas/numpy binary incompatibility causing access-violation crashes on this Windows/Python 3.13 setup, plus unrelated fixture problems) confirmed unrelated to this change by removing the new files and reproducing the exact same failure count. Two debug scripts under `tests/investigate/` and `tests/test_pandas.py` crash the interpreter on collection and were excluded from both runs; this is pre-existing and out of scope for M1.

---

### M2 — Registry Service (the authority)

**Goal.** The identity core becomes an *institution*: one internal service boundary through which all identity questions are asked and all identity verdicts are entered, with validation that defends the uniqueness guarantee loudly.

**Scope.**
- The authoritative service boundary: lookup by any known identifier (current or historical), asset detail with evidence and classification, relationship traversal, lifecycle operations.
- Validation per §7: duplicate detection at claim time, identifier-conflict findings as first-class records, explicit merge machinery (never silent cleanup), the absence-is-data stance for identifier-poor assets.
- The stewardship operations a human operator needs: confirm an ambiguous mapping, record a merge, correct a classification as a dated fact — the minimum adjudication surface, not a full admin product.

**Deliverables.** Registry service with its consumer-facing contract (internal); validation findings that surface rather than auto-correct; merge-as-explicit-event; operator adjudication surface (minimal); documentation of the service contract for downstream milestones.

**Risks.** The adjudication surface ballooning into a UI project (mitigate: M2 ships the *capability*; polish is explicitly out of scope). Downstream teams bypassing the service with direct reads (mitigate: contract documented in M2, enforced culturally and by review until M7's audit).

**Definition of Done.** Every identity operation the later milestones need is available through one boundary; a deliberately-injected duplicate claim is detected and surfaced, not silently merged; a human can adjudicate a finding end to end.

**Depends on.** M1.

**Status: Complete (2026-07-09).**

**Implementation notes.**
- New, standalone code only — zero M1 files modified. `backend/models/registry_finding.py` (`RegistryFinding`, sharing the existing `Base`); `backend/services/registry_domain.py` (`FindingType`, `FindingStatus`, `FindingResolution` — kept separate from M1's `asset_domain.py` rather than appended to it); `backend/services/registry_findings_repository.py` (pure persistence, no rules, mirroring `asset_repository.py`'s discipline); `backend/services/registry_query.py` (`find_identifier_rows` — the one genuinely new *read*, since M1's `find_current_identifier` only searches current mappings); `backend/services/registry_service.py` (the public service boundary — delegates every M1-owned rule to `services/asset_registry.py` per ADR-004, adding only `find_by_identifier`, `mint_asset`'s pre-mint duplicate detection, findings-backed conflict recording, `record_merge`, and the findings adjudication surface); Alembic migration `e7a9c1d3f5b7` (1 new table, chains off `d6f8a0b2c4d6`, no FK from any existing table into it); `backend/tests/test_registry_service.py` (19 unit tests).
- **`RegistryFinding` is an evidence record, not an error log.** Rows are never deleted and `resolve_finding()` never overwrites the original observation (`finding_type`, `subject_asset_id`/`related_asset_id`, `identifier_type`/`identifier_value`, `detail`, `created_at`) — it only appends resolution fields (`status`, `resolution`, `resolution_note`, `resolved_by`, `resolved_at`) on top. `test_resolve_finding_appends_without_erasing_original_observation` asserts the pre-resolution `detail`/`created_at` are byte-identical after resolution.
- **Named `record_merge()`, not `merge_assets()`** — deliberately, per design review: the operation's purpose is to durably record a merge decision that has already been made (the status transition to `MERGED` and the `MERGED_INTO` relationship link are consequences of the recording, not the primary act). It returns the `RegistryFinding` — the merge's permanent evidentiary record — not the mutated `Asset`. The finding is created already `RESOLVED`/`MERGED`, since recording a merge is itself the evidence of a decision, not something left open for adjudication.
- **`AssetDetail` (the `get_asset_detail()` return type) is explicitly an internal read model, not a public contract.** It is defined in `registry_service.py` itself (not in `registry_domain.py`, which is reserved for genuine domain vocabulary) with a docstring stating its shape may change without notice — appropriate given M2 has zero consumers yet (Backward Compatibility: "Registry exists in parallel. Nothing consumes it yet").
- **`find_by_identifier()` searches current AND historical `AssetIdentifier` rows** — a genuine capability gap in M1's `asset_repository.find_current_identifier`, which only searches `is_current=True` rows. Implemented as a new read (`registry_query.find_identifier_rows`) rather than a new rule, keeping ADR-004 intact: no business logic was duplicated, only a broader query was added. Can legitimately return more than one `Asset` if an identifier value has been reused over time (ISIN/CUSIP recycling, provider symbol reassignment) — callers must not assume a single answer.
- **`mint_asset()` duplicate detection is two-tier**, per §7: a *current* identifier match on another asset blocks the mint outright (raises `AssetRegistryError` and records an `OPEN` `DUPLICATE_CLAIM` finding against the existing asset — never silently proceeds); a *historical-only* match does not block minting (legitimate long-horizon identifier reuse is explicitly allowed by ASSET_REGISTRY.md §2) but still records an `OPEN` `DUPLICATE_CLAIM` finding on the new asset for human review.
- **No API endpoints.** Interpreted the same way M1's note already framed it — M2 is the in-process service boundary; nothing outside the Registry calls it yet, per the task's own Backward Compatibility statement ("Registry exists in parallel. Nothing consumes it yet").
- Migration `e7a9c1d3f5b7` verified via `alembic heads` to chain cleanly off the actual current head `d6f8a0b2c4d6` before being written (single head, no drift since M1 landed).
- Test suite: 19/19 new tests pass; all 19 M1 `test_asset_registry.py` tests continue to pass unmodified. Full backend suite run before and after this change with the M2 files moved aside and restored (`--ignore=tests/investigate --ignore=tests/test_pandas.py --ignore=tests/test_snapshot_repair.py`, three known pre-existing interpreter-crashing files unrelated to this change): `58 failed, 906 passed, 32 skipped` baseline; `58 failed, 925 passed, 32 skipped` with M2 restored — byte-identical `FAILED` test list in both runs (diffed directly), +19 newly passing, zero regressions.

---

### M3 — Symbol Resolver (adjudication pipeline)

**Goal.** The platform can take any claim — a search string, a CSV row, a manual entry — and adjudicate it to a verdict per ASSET_REGISTRY.md §4: decisive resolution, surfaced ambiguity, or honest unknown. This is the single most correctness-critical component of the epic, because M5's backfill runs through it.

**Scope.**
- The adjudication sequence: candidate matching against current *and historical* mappings first; evidence weighing by the identifier hierarchy; three honest confidence positions; verdicts recorded as durable mappings so the same question is never asked twice.
- Ambiguity surfacing: ranked candidates, human confirmation, recorded settlement — wired into the M2 adjudication surface.
- **Bulk mode** for M5: the same resolver, run over the M0 symbol inventory, partitioning it into decisive / ambiguous / unknown *without committing anything* — a dry-run report that tells us the true size of the human adjudication workload before migration begins.
- **Shadow mode** for live doors: existing import and search flows keep working symbol-keyed while the resolver runs alongside, logging what it *would* have decided. Divergences between shadow verdicts and current behavior are reviewed as findings.

**Deliverables.** Resolver with the full verdict discipline; dry-run bulk report over the entire historical symbol inventory; shadow-mode instrumentation on at least the CSV-import and manual-entry doors; test fixtures covering the known hard cases (DR vs. underlying, venue suffixes, delisted names, recycled-ticker simulation).

**Risks.** Over-eager decisive resolution (a "decisive" threshold that guesses) — the one failure mode the architecture forbids absolutely (mitigate: bias thresholds toward *ambiguous*; a too-large human workload is an inconvenience, a wrong silent mapping is permanent poison). Underestimated ambiguity volume making M5 impractical (mitigate: the dry-run report is exactly the early warning; if the ambiguous set is large, schedule adjudication as a workstream, not an afterthought).

**Definition of Done.** Dry-run report over full history reviewed and its ambiguous set sized and owned; shadow mode running in production with divergences triaged; zero cases where the resolver silently chose under genuine ambiguity in testing.

**Depends on.** M2. **Parallelizable with:** M4, after both have M2.

**Status: Complete (2026-07-09).**

**Implementation notes.**
- **Scope was narrowed at kickoff, deliberately, and is recorded here as a deviation from this section's original text.** The task as assigned named six objectives — Identifier Resolution, Candidate Discovery, Resolution Pipeline, Confidence Classification, Registry Findings integration, Manual Adjudication — and its own Milestone Discipline explicitly said "do not introduce speculative future work." Bulk mode (the M5 dry-run report over the M0 symbol inventory) and shadow mode (instrumentation on live CSV-import/manual-entry doors) are out of scope for this milestone: bulk mode has no M5 to serve yet (Replay/Portfolio Migration have not started), and shadow mode has no live door to instrument yet (M0 confirmed no bulk-import path exists in the current codebase, and this task's own Out of Scope list excludes frontend/HTTP APIs/provider synchronization). Both remain available as-designed extensions of the same resolver — ADR-004 ("one implementation per rule") is satisfied because `identity_resolver.resolve()` takes a plain `ResolutionClaim` value object with no bulk- or shadow-specific code path baked in; a future milestone can call it in a loop over the M0 inventory (bulk) or call it alongside an existing door without acting on the verdict (shadow) without rewriting it.
- New, standalone code only — zero M1 or M2 files modified. `backend/services/resolver_domain.py` (`ResolutionVerdict`, `ResolutionFindingType`, `AdjudicationDecision`, `ResolutionPolicy`/`DEFAULT_POLICY`, and the structured evidence value objects — kept separate from `asset_domain.py` and `registry_domain.py` rather than appended to either, same rationale as M2's own split); `backend/services/identity_resolver.py` (the pipeline: `resolve()` and `adjudicate()`); `backend/tests/test_identity_resolver.py` (17 unit tests). No new tables, no Alembic migration — the resolver is pure in-process logic over M1/M2's existing tables and reads.
- **Named `identity_resolver.py`, not `symbol_resolver.py`**, to avoid collision with the pre-existing `backend/services/symbol_resolver.py` (the ad hoc `YFINANCE_SYMBOL_MAP` + DR-suffix regex module M0 flagged as a future retirement candidate). That module is untouched; nothing wires into the new resolver yet, per this task's Out of Scope list.
- **Confidence is a deterministic classification, not a probability — no ML.** `ResolutionPolicy` holds every weight/threshold as an explicit, inspectable field (identifier-type weights mirroring the MARKET_DATA_PLATFORM.md §5 evidence hierarchy — ISIN 100, FIGI 90, CUSIP/SEDOL 80, PROVIDER_SYMBOL 50, BROKER_CODE 20 — plus a historical-match multiplier, a resolved threshold, and corroboration bonus/penalty), rather than constants embedded in the pipeline, per explicit user direction during plan review. `DEFAULT_POLICY` is the only instance currently used; alternate policies can be passed to `resolve()` without touching the pipeline.
- **Evidence stays structured end-to-end, not collapsed into a prose string** — also per explicit user direction during plan review. `ResolutionResult` carries `candidates` (each with `contributions` and `corroborations`, all structured dataclasses) and `claim_evaluations`; the only place free text is generated is `_format_finding_detail()`, a single rendering function used solely to populate `RegistryFinding.detail` (a pre-existing `Text` column) for the durable audit trail. Any future UI/diagnostic consumer should build its own explanation from the structured `ResolutionResult`, not parse that text.
- **Five outcomes, mapped onto the architecture's three-position model** (ASSET_REGISTRY.md §4: decisive / ambiguous / unknown): RESOLVED and CANDIDATE are both "decisive" (converges on exactly one existing asset, or clearly matches nothing despite strong evidence — never auto-minted); AMBIGUOUS and CONFLICT are both "ambiguous" (insufficient to decide vs. the evidence actively disagreeing with itself); UNKNOWN stands alone. CONFLICT specifically requires two *different* identifiers within one claim each carrying a *current* mapping to two *different* assets — a live contradiction. A single recycled identifier value with multiple *historical*, no-current-claimant owners is AMBIGUOUS, not CONFLICT (`test_recycled_identifier_no_current_claimant_is_ambiguous_not_conflict`).
- **A current mapping preempts an asset's own stale history for the same identifier value** — discovered while writing tests: without this rule, an asset's superseded identifier row would count as a second, competing "candidate" against its own live current mapping for the same value, producing false ambiguity. Fixed in `_match_candidates()`: historical rows for a given (type, value) only contribute when no current row exists for that exact value anywhere (`test_current_mapping_preempts_own_stale_history`).
- **Registry Findings remain the sole adjudication mechanism**, exactly as instructed. `resolve()` persists AMBIGUOUS/CONFLICT verdicts via `registry_findings_repository.create_finding` directly (the same low-level module `registry_service.record_merge` itself calls) using two new `finding_type` string values (`RESOLUTION_AMBIGUOUS`, `RESOLUTION_CONFLICT`) — not added to M2's `FindingType` enum, since `RegistryFinding.finding_type` is a plain string column and M2's enum models a different (mint-time/attach-time) vocabulary. `adjudicate()` closes findings via `registry_findings_repository.resolve_finding` directly rather than `registry_service.resolve_finding()`, whose `FindingResolution` type (`MERGED`/`CONFIRMED_DISTINCT`/`DISMISSED`) does not model "this claim's identity was confirmed" — `AdjudicationDecision` (`CONFIRM_MATCH`/`CONFIRM_NEW`/`NOT_A_MATCH`) is M3's own resolution vocabulary for its own finding types, reusing M2's `FindingStatus` (OPEN/RESOLVED/DISMISSED) unchanged since that lifecycle is generic across all finding types.
- **Never auto-creates, never auto-merges — verified, not just asserted in prose.** `adjudicate(CONFIRM_MATCH)` only attaches an identifier to an asset the human named (via the unmodified `registry_service.attach_identifier`); `CONFIRM_NEW` only closes the finding, leaving minting to a separate, explicit `mint_asset()` call the resolver never makes itself. `test_resolve_never_mutates_assets_table` and `test_adjudicate_confirm_new_closes_finding_without_minting` assert the `assets` table row count is unchanged across every verdict and adjudication path.
- **A pre-existing gap in M1's `attach_identifier` was discovered, not fixed.** Re-attaching an identifier value to an asset that already holds a *historical* (superseded) row for that exact value raises a raw `IntegrityError` (unique constraint on `asset_id`+`identifier_type`+`value`) rather than a clean `AssetRegistryError` or idempotent flip back to current. Left as-is per this milestone's "keep implementation additive" / "do not modify M1" discipline; test fixtures were designed around it (`test_adjudicate_confirm_match_resolves_decisively_next_time` uses a fresh third asset rather than re-confirming onto an asset that already had a historical row for the value) rather than working around it inside M3. Worth a small, isolated fix in a future milestone.
- Test suite: 17/17 new tests pass. Full Asset Registry regression run (`test_asset_registry.py` + `test_registry_service.py` + `test_identity_resolver.py`, M1+M2+M3 together): 54/54 pass, zero regressions. Full backend suite not re-run in full for this milestone — the same three pre-existing interpreter-crashing files noted in M2's regression run (`tests/investigate/`, `tests/test_pandas.py`, `tests/test_snapshot_repair.py`) plus a pre-existing block of unrelated failures remain, none touched by or related to this change (M3 adds only new files; nothing existing was modified).

---

### M4 — Provider Integration (witnesses, not judges)

**Goal.** Market data flows re-keyed: provider symbols become per-provider mappings *into* `asset_id`s, adapters return candidates rather than identities, and price/observation storage is joinable by `asset_id` — while every existing symbol-keyed read keeps working.

**Scope.**
- Per-provider symbol mappings in the Registry's evidence tier for every actively-used provider symbol.
- Adapter conformance to PROVIDER_INTERFACE.md's never-assert-identity rule: search and lookup responses become candidate evidence for the resolver, not direct asset creation.
- Market data association: observations keyed or joinable by `asset_id`, with the existing symbol-keyed access preserved through the compatibility layer (§6 of this plan) for unmigrated consumers.
- Corroboration lookups: the resolver (M3) can request provider evidence through the Market Data Platform when a claim is thin.

**Deliverables.** Complete provider-symbol mapping coverage for live data flows; adapters demoted to witnesses; dual-key data access verified equivalent (same series retrieved by symbol and by `asset_id` are the same series); provider-outage identity non-event confirmed by test (a provider's mappings going quiet changes no identity).

**Risks.** Subtle divergence between symbol-keyed and id-keyed reads during coexistence (mitigate: automated equivalence checks in CI and a production sampling audit). Vendor quirks not in the M0 inventory surfacing mid-milestone (mitigate: quirks become evidence-file entries and resolver fixtures — the architecture's normal absorption path, not an emergency).

**Definition of Done.** Every live provider data flow resolvable to an `asset_id`; equivalence audit clean over a full market cycle (at least one week of live operation); no adapter can create or rename an asset.

**Depends on.** M2 (mappings live in the Registry); M3 for corroboration wiring. **Parallelizable with:** M3 core work.

**Status: Partially complete — Provider Adapter Layer only (2026-07-09).**

**Implementation notes.**
- **Scope was narrowed at kickoff, deliberately, and is recorded here as a deviation from this section's original text** — the same pattern M3's notes already established. The task as assigned retitled this milestone "Provider Adapter Layer" with a single goal: an abstraction converting provider-specific payloads into canonical `ResolutionClaim`s, with the Registry never learning a provider exists. Its own Out of Scope list excludes synchronization jobs, scheduling, HTTP endpoints, and provider recommendation/routing logic. Consequently, this section's original fuller scope — complete per-provider mapping coverage for *live* data flows, dual-key (symbol vs. `asset_id`) equivalence audits, and resolver corroboration wiring into `identity_resolver._corroborate()` — remains undone and is **not** claimed complete here; it has no live door to serve yet (M5 has not started) and depends on wiring decisions ("which existing call sites adopt the adapter") this task's Out of Scope list explicitly excludes. What shipped is the translation abstraction and one concrete adapter; the corroboration-wiring and live-flow-coverage bullets are left for a future milestone to pick up against this section's original text.
- New, standalone code only — zero M1/M2/M3 files modified, and `services/market_data/*` and `services/symbol_resolver.py` are untouched (the adapter neither calls nor is called by either). `backend/services/provider_domain.py` (`ProviderObservation`, `ProviderCapabilities` — vocabulary, kept separate from `resolver_domain.py` per the same per-milestone split M2/M3 already established); `backend/services/provider_adapter.py` (`ProviderAdapter` ABC, `YahooFinanceAdapter`); `backend/tests/test_provider_adapter.py` (13 unit tests). No new tables, no Alembic migration — pure in-process transformation, same as M3.
- **`ProviderObservation` is a frozen dataclass**, per explicit user direction during plan review — it represents a provider's observation, not caller-mutable working state.
- **`ProviderCapabilities` is declared but consumed by nothing yet**, also per explicit user direction during plan review: a `frozen` dataclass listing which `IdentifierType`s an adapter can in principle supply, attached to each adapter as a class attribute, with zero routing/selection/confidence logic reading it. It exists solely so a future provider-selection or confidence-weighting policy has an extension point already in the adapter interface, rather than requiring a breaking change to add one later.
- **`build_claim()` is the one shared, `@final`-marked implementation of `ProviderObservation -> ResolutionClaim`** (ADR-004): every adapter subclass writes only `normalize()`. Proven by `test_second_adapter_requires_only_normalize_override`, which defines a throwaway fake adapter *inside the test file* (not shipped as production code, since no such provider integration exists) to demonstrate the cost of a new provider is exactly one method.
- **Adapters are strictly translational, verified rather than merely asserted.** `normalize()` implementations contain no inference, repair, or reinterpretation — `_clean_str()` only trims incidental whitespace and treats empty strings as absence, matching PROVIDER_INTERFACE.md Section 4's "translation, not interpretation." No adapter calls `symbol_resolver.py`'s DR-suffix/ticker-cleanup logic, which remains a separate, untouched concern. `test_empty_string_fields_become_none_not_fabricated` and `test_build_claim_omits_absent_identifier_types` assert absent vendor fields never become fabricated identifiers. `test_adapter_methods_take_no_session_parameter` asserts the architectural DB-free boundary mechanically, not just in prose.
- **Provenance uses only fields M3 already defined** — no new fields were added to `ResolutionClaim` or `IdentifierRecord` (both frozen, from M3). Every identifier an adapter emits carries `source=f"provider:{provider_name}"` and `as_of=<translation-time UTC timestamp>`, which the Registry stores exactly as it would any other identifier's evidence-tier provenance (`ASSET_REGISTRY.md` Section 3) — nothing provider-specific crosses into the Registry's own vocabulary.
- `YahooFinanceAdapter` maps the actual fields the current codebase's `Ticker.info`-based fetches use (`symbol`, `longName`/`shortName`, `exchange`, `market`, `currency`) plus an optional `isin` key a future caller could merge in from `Ticker.isin` — a separate property yfinance does not include in `.info`. `cusip`/`sedol`/`figi` are always `None` for this adapter today, an honest reflection of what yfinance actually reports, not a limitation of the (generically written) mapping.
- **`test_adapter_built_claim_resolves_like_a_hand_built_one` is the mechanical proof of the milestone's success criterion** — an adapter-built claim, run through M3's real `identity_resolver.resolve()` against an in-memory Registry, resolves identically to a hand-constructed `ResolutionClaim`. `identity_resolver.py` was not modified to make this pass.
- Test suite: 13/13 new tests pass. Full Asset Registry regression run (`test_asset_registry.py` + `test_registry_service.py` + `test_identity_resolver.py` + `test_provider_adapter.py`, M1+M2+M3+M4 together): 67/67 pass, zero regressions.

---

### M5 — Portfolio Migration (the ledger gets its identity)

**Status: Split into two tracks by implementation reality (see Changelog, §13). Track A — Complete (2026-07-09). Track B — Not started.**

This milestone's original text specified one continuous scope: adjudicated ledger backfill, full-coverage check, replay parity verification, and engine cutover. Implementation proceeded as four sub-milestones — tracked internally as M5.0–M5.3 — that built the adjudication and bootstrap tooling this scope depends on, but by explicit, documented design choice at each step, never touched `Transaction`, `PortfolioItem`, `PortfolioSnapshot`, or `Watchlist`. That leaves the schema-changing, replay-parity-gated core of the original Definition of Done entirely undone. Rather than mark M5 "complete" on the strength of adjacent tooling — which the M6 Registry Read Path audit (2026-07-09) flagged as exactly the kind of false signal this plan exists to prevent — the two tracks are named explicitly below so neither is mistaken for the other.

#### M5 Track A — Ledger Evidence, Migration Planning & Registry Bootstrap

**Goal.** Build the adjudication and minting tooling Track B will run on: turn raw ledger symbols into evidence, plan a migration against the Registry's current state, execute that plan's already-decisive cases, and bootstrap the Registry from whatever claim shapes the historical ledger contains — all without writing to the ledger itself.

**Scope (as implemented).**
- **M5.0 — Ledger Evidence Builder.** Turns a raw ledger symbol into a `ResolutionClaim` via the same `build_claim()` M4's provider adapters use (ADR-004 reuse) — the ledger's own evidence-tier citizenship, established once.
- **M5.1 — Migration Planner.** Runs the M3 resolver in bulk over the ledger's actual symbol population (not a synthetic inventory), producing a `MigrationPlan` that partitions every claim shape into RESOLVED / AMBIGUOUS / CONFLICT / CANDIDATE / UNKNOWN — a dry-run report; commits nothing.
- **M5.2 — Migration Executor.** Commits the Planner's already-decisive verdicts (attaches identifiers to already-minted assets) under the same dry-run/rollback discipline as every other Registry writer; never invents a mapping the resolver did not already decide.
- **M5.3 — Registry Bootstrap.** Mints new assets for `UNKNOWN` claim shapes that carry an unambiguous market/exchange signal (`.BK` suffix, DR pattern) per `services/symbol_market_convention.py`'s deliberately conservative rules; quarantines — never guesses — shapes with no such signal or missing currency; leaves duplicate clusters (two `UNKNOWN` shapes sharing a canonical symbol) unminted on both sides pending human adjudication.

**Deliverables (shipped).** `services/symbol_market_convention.py`, `services/bootstrap_planner.py`, `models/registry_bootstrap.py`, Alembic migration `c6e8a0f2d4b6`, `services/registry_bootstrap.py`, `manage.py` CLI wiring; 19 unit tests (`test_bootstrap_planner.py` ×11, `test_registry_bootstrap.py` ×8), all green.

**Bootstrap validation (production-like data, 2026-07-09).** 21 assets minted; 2 duplicate clusters found and correctly left unminted for manual adjudication (not auto-resolved — ASSET_REGISTRY.md §4); 0 shapes quarantined; 21/25 claim shapes resolved (84%); 41/52 transactions resolved to a mintable identity (79%).

**What Track A explicitly does not do.** Per `migration_executor.py`'s own docstring: *"Transaction, PortfolioItem, and PortfolioSnapshot are never imported or touched. Replay, accounting, and the ledger are unreachable from this module."* Confirmed directly against the schema: `PortfolioItem`, `Watchlist`, and `Transaction` retain only a plain `symbol` String column; `PortfolioSnapshot` has no symbol column at all (symbols live inside `holdings_json`/`sector_breakdown_json` text blobs). Track A answers "what asset does this historical symbol refer to?" for the Registry's own benefit; it does not record that answer anywhere the ledger, replay engine, or accounting tooling can see it.

**Risks.** Ambiguity volume turning out larger than the tooling can absorb quietly — see §9's updated "Ambiguity volume" entry for the actual measured result.

**Definition of Done.** Bootstrap run completes against real ledger data; every `UNKNOWN` claim shape is classified as mintable, quarantined, or duplicate-blocked with no silent guessing; test suite green. *(Met, 2026-07-09.)*

**Depends on.** M3 (resolver), M4 (bootstrap reuses `build_claim()`).

**Status: Complete (2026-07-09).**

#### M5 Track B — Native Ledger Persistence (asset_id backfill, replay parity, engine cutover)

**This is the original M5 scope, unchanged, carried forward as this milestone's remaining work:**

**Goal.** Every transaction, holding, and snapshot references an `asset_id` — additively, under audit, with replay parity as the gate. This remains the epic's center of gravity and its highest-risk milestone; nothing in Track A reduces that risk, it only reduces the adjudication backlog Track B must clear before it can start.

**Scope.**
- **Adjudicated backfill**: run the M3 bulk resolution over the full ledger, this time writing the result — a new, additive `asset_id` reference on `Transaction`, `PortfolioItem`, and (in whatever additive form its JSON-blob shape allows) `PortfolioSnapshot`. Decisive cases map automatically; every ambiguous case is human-adjudicated through the M2 surface; nothing is committed until its verdict is recorded. The Transaction table's existing content is never modified — asset references are added alongside (the parallel-change expand step).
- **Full-coverage check**: zero ledger rows without an `asset_id` reference at the end of backfill. Unknowns are not skipped — they are minted as honestly-thin identities (absence is data, §7) or escalated. **Precondition, newly known from Track A's bootstrap run:** Track B cannot reach 100% coverage without first closing Track A's own adjudication backlog — the 2 unresolved duplicate clusters and the 11/52 (21%) transactions with no resolvable claim shape at all. This backlog is Track A/M2 adjudication debt, not Track B's to solve from scratch; it must be cleared, or explicitly and individually waived, before Track B's full-coverage check can pass.
- **Replay parity verification**: full-history replay for every portfolio, computed via the id-keyed path, compared against the M0 golden baselines. Identical or the milestone stops.
- **Engine cutover behind flags**: Portfolio Engine, Replay Engine, and the rebuild/validation tooling (`rebuild_portfolio`, `verify_snapshots`, `validate_ledger`) switch to `asset_id` as the operative key, per-portfolio or per-engine flagged, with instant reversion available.

**Deliverables.** Fully backfilled ledger references; adjudication log of every human decision made during backfill (these are permanent Registry mappings, not migration scratch); parity report per portfolio; flagged cutover complete for accounting engines; audit tooling running natively on `asset_id`.

**Risks.** This milestone concentrates the epic's three worst risks — wrong mapping, duplicate identity, replay divergence — and they are addressed in §9. The specific mitigations here: parity is checked per portfolio *before* that portfolio's cutover; the symbol column remains authoritative until parity passes; rollback is a flag flip for as long as Track B is in flight.

**Definition of Done.** Track A's adjudication backlog (2 duplicate clusters, 11 unresolved transactions as of the 2026-07-09 bootstrap run) cleared or explicitly waived per-row; 100% ledger coverage; replay parity **bit-identical** for every portfolio against golden baselines; `verify_snapshots` and `validate_ledger` clean on the id-keyed path; accounting engines running id-keyed in production for a probation period (suggested: two weekly cycles) with zero drift.

**Depends on.** M5 Track A (adjudication tooling and the Registry population it produced), M3 (resolver), M4 (price joins by `asset_id` — replay needs id-keyed valuation). **Hard gate for:** M6 Native Integration — **not** for M6 Compatibility-Layer Integration, which does not depend on Track B (see below).

**Status: Not started.**

---

### M6 — Analytics & Intelligence Integration

**Status: Split into two tracks (see Changelog, §13) — a read-time Compatibility-Layer track that can proceed now without waiting on M5 Track B, and the original Native Integration track, still hard-gated on M5 Track B.**

The M6 Registry Read Path audit (2026-07-09, see [M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md](M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md)) inventoried every symbol read across Portfolio, Transactions, Snapshots, Watchlist, Optimizer, Execution, Shadow Portfolio, Attribution, and AI Evaluation, and confirmed this milestone's original hard gate (M5, now M5 Track B) is not satisfied. Rather than defer all read-path improvement until Track B lands — a schedule with no fixed date — that audit specified a non-schema-changing track delivering most of this milestone's *practical* value early. Both tracks are named here so this plan matches what the audit found.

#### M6 Compatibility-Layer Integration

**Goal.** Every non-ledger read path — optimizer internals, execution sizing/planning, factor exposure, shadow portfolios, calibration, the recommendation write path, AI evaluation, human idea intake, watchlist — becomes Registry-informed for identity and classification facts, via a new read-time `resolve_asset()` adapter wrapping the already-complete M1–M3 Registry/Resolver (ADR-004 reuse). Symbol-string behavior is preserved unchanged for any symbol the Registry has not yet resolved (`Unresolved` is a first-class, non-guessing return value, per ASSET_REGISTRY.md §4).

**Scope.** Full detail — the per-module Current → Target → Effort → Dependencies table and the 7-phase refactoring order — is specified in [M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md](M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md) §§3–5. Summary:
- New module `services/registry_lookup.py` (`resolve_asset()`, `Unresolved`, TTL cache) — zero existing files touched to introduce it.
- Retirement of 5 independently-duplicated `.BK`-variant matching shims (`basket_simulation.py`, `execution_plan.py`, `position_sizing.py`, `allocation_engine.py`, `idea_review.py`) in favor of the one adapter.
- Additive `asset_id` alongside `symbol` in the recommendation write path (`snapshot_writer.py`, `main.py`'s `POST /analyze/optimizer`) for **new** rows only — existing `RecommendationSnapshot`/`SignalHistory`/`RecommendationGrade` rows are never rewritten (Design Invariant 1, OPTIMIZER_PHILOSOPHY.md §14.1).
- Optimizer internal dict-keys (`score_map`, `pc_map`, `alloc_map` in `agents/optimizer.py`) migrate to `asset_id`-keyed in-memory structures; the AI L1/L2/L3 prompt/response JSON contract stays symbol-shaped (explicit non-goal, judgment/arithmetic boundary per OPTIMIZER_PHILOSOPHY.md §6).
- A structural fix separating `policy_engine.py`'s free-text violation strings from `execution_optimizer.classify_reason`'s substring-search recovery of them.
- Explicitly excluded: `services/portfolio_rebuilder.py`'s replay loop and `services/ledger_validator.py`'s CHECK functions — those remain Track B's territory; the adapter must never be called from either.

**Deliverables.** `services/registry_lookup.py` and its test suite; the 5 shims retired; recommendation write-path carrying `asset_id` for new rows; optimizer internals re-keyed; `policy_engine`/`execution_optimizer` structural fix; unit tests per the read-path plan's §7 (regression, unresolved-symbol fallback behavior, consensus-math parity, immutability audit, no-accounting-drift).

**Risks.** Named directly by the read-path audit as pre-existing correctness bugs this track also happens to fix: (1) `execution_analyzer.py:88-181` joining a frozen recommendation symbol against the live, mutable `Transaction.symbol` — **not fully closed by this track**, since it requires `Transaction` itself to carry `asset_id` (Track B); (2) `execution_optimizer.classify_reason`'s fragile substring coupling; (3) the 5-file `.BK`-shim duplication (ADR-004 violation in the wild). Standard risk: a partial rollout leaving some consumers `asset_id`-aware and others symbol-only simultaneously — mitigated the same way as elsewhere in this plan, per-consumer flags and the `Unresolved`-fallback discipline (Migration Principle 3).

**Definition of Done.** All 7 phases of the read-path plan's refactoring order shipped; regression suite green throughout; consensus-math parity proven byte-identical; zero `UPDATE`s against any FROZEN table verified by mechanical grep audit; `verify_snapshots`/`validate_ledger` clean before and after every phase (this track never touches ledger-adjacent code, so a clean run is the expected, not aspirational, outcome).

**Depends on.** M2, M3 (the Registry/Resolver this track wraps). **Not dependent on M5 Track B.** **Does not, by itself, satisfy M6 Native Integration's Definition of Done** (below) — it is additive and read-time only; the ledger itself remains symbol-keyed until Track B.

**Status: Phase 1 (both steps), Phase 2, and Phase 3 (steps 7 and 8) shipped (2026-07-09 through 2026-07-10).** `services/registry_lookup.py` (`AssetView`, `Unresolved`, `resolve_asset()`, `resolve_many()`, thread-safe TTL cache) landed with 18 unit tests, all green, alongside the full pre-existing Registry test family (133 tests total) — see Changelog §13. Phase 1 step 2 (wiring `resolve_asset()`/`resolve_many()` into `GET /watchlist` as the lowest-stakes pilot consumer, plus `POST /watchlist` for response-shape consistency) shipped 2026-07-10 as the **Watchlist Registry Pilot** — see [WATCHLIST_REGISTRY_PILOT.md](WATCHLIST_REGISTRY_PILOT.md) for the full audit and pilot report. Phase 2 (retiring the 5 duplicated `.BK`-variant shims) shipped next: `basket_simulation.py`, `execution_plan.py`, `position_sizing.py`, `allocation_engine.py`, and `idea_review.py` are now wired through a new shared `services/registry_symbol_matching.py` adapter (`match_known_symbols()`) that tries `resolve_asset()` first and falls back to the original bare/`.BK` heuristic only for symbols the Registry hasn't resolved, per the fallback discipline this section already committed to. `portfolio_construction.py`, a 6th, previously-undocumented consumer of the shared `basket_simulation._resolve_symbol_sectors` helper, was also updated (signature-compatibility only, no shim of its own). Phase 3 step 7 (the Recommendation write-path root fix) shipped 2026-07-09: `services/registry_recommendation_context.py` resolves every symbol in an optimizer run's `scores_map` and additively attaches `asset_id`/`canonical_symbol`/`market`/`exchange` (or an honest `resolved: false` + reason) into `RecommendationSnapshot.scores_map_json` only — the live `scores_map` driving the AI prompt and every other in-run computation is never mutated. `SignalHistory` was audited and found to require a schema change to carry the same metadata, which this phase's own constraints forbid; it remains symbol-only, flagged as technical debt. Phase 3 step 8 was rescoped and reshipped 2026-07-10: a full audit of `plan_grader.py`/`optimizer_action_summary.py` found neither has a genuine cross-source identity join, so the originally-worded "asset_id-aware read path" fix would have been decorative; the real read-path gap in AI Evaluation was the plan-vs-live-`Transaction.symbol` join (M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md §2.3 item 1), fixed instead in `execution_ledger.py`/`recommendation_ledger.py`/`attribution_engine.py` via `match_known_symbols()` — see Changelog §13 for the full accounting. Phase 6 (shadow portfolios, factor engine, calibration) not started. Phase 7 (classification consolidation) shipped 2026-07-10 — see [CLASSIFICATION_CONSOLIDATION.md](CLASSIFICATION_CONSOLIDATION.md) and Changelog §13. `resolve_asset()` now has real callers across symbol matching, recommendation persistence, AI Evaluation's execution analysis, Watchlist, and `main.py`'s sector-classification system.

#### M6 Native Integration

**This is the original M6 scope, unchanged, and remains hard-gated as originally specified:**

**Goal.** Everything downstream of accounting — analytics, attribution, timing intelligence, the optimizer pipeline, the decision record, AI evaluation — reads `asset_id` *natively from the ledger*, with symbols surviving only as render-time display lookups. This supersedes the Compatibility-Layer track once it lands: the same call sites the Compatibility Layer touched are revisited so they read the now-native `asset_id` directly instead of resolving one at read time.

**Scope.**
- Analytics dimensions (sector, region, class) re-attached to Registry classification — dated facts, so period analytics can see classification *as it stood then* (§8).
- The recommendation/decision/evaluation chain re-keyed: recommendations, execution decisions, shadow tracking, attribution, and grading reference assets by identity. Frozen historical records are **not** rewritten — they gain resolution through the same additive mapping the ledger got, preserving the AI Evaluation domain's never-retro-edit rule.
- Presentation: `display_symbol` looked up at render time; screens stop passing symbols through business layers.
- Parity verification for headline analytics (returns, attribution, human-vs-AI results) against M0 baselines.
- Retirement of the M6 Compatibility-Layer adapter's read-time resolution calls in favor of native `asset_id` columns, wherever Track B has made that column available — this does not wait for M7; a consumer converts as soon as its data is native, same as every other per-consumer cutover in this plan.

**Deliverables.** Id-keyed analytics and evaluation flows; analytics parity report; display-symbol lookup at the presentation boundary; classification-history support in period analytics.

**Risks.** Long tail of minor consumers discovered late (mitigate: the M0 census is the checklist; anything not on it is a census defect to record). Analytics differences that are *corrections* rather than regressions — e.g., a DR previously conflated with its underlying now correctly distinct (mitigate: parity report distinguishes "identical," "explained improvement," and "unexplained divergence"; only the third blocks).

**Definition of Done.** Census checklist fully dispositioned; analytics parity clean or explained; no business-layer symbol passing in the migrated flows; AI evaluation results stable across the cutover; every call site the Compatibility-Layer track touched now reads native `asset_id` rather than calling `resolve_asset()` at read time.

**Depends on.** M5 Track B (hard gate, unchanged). M6 Compatibility-Layer Integration is not a structural dependency but is expected to precede it in practice, since it is the lower-risk path most consumers will already be on.

**Status: Blocked on M5 Track B.**

---

### M7 — Cleanup (contract phase)

**Goal.** The coexistence machinery is removed, the old world is retired, and the end state is audited against the architecture's own test.

**Scope.**
- Remove dual-key reads, compatibility shims (including M6 Compatibility-Layer's `resolve_asset()` call sites not already retired during M6 Native Integration), and migration flags; retire symbol columns from ledger-adjacent storage once every consumer is confirmed id-keyed (symbols persist *in the Registry's evidence tier*, where they now belong — retirement means removal as *keys*, never as *evidence*).
- The final audit: **no engine can tell what any asset is called** (ASSET_REGISTRY.md §10) — a mechanical sweep for symbol access below the resolution boundary and presentation surface, plus review sign-off per engine.
- Golden baselines re-cut on the end state, becoming the new reference for future epics.
- Documentation: architecture handbook README coverage note, decision log entries for any judgment calls made during migration, and an operations note for the ongoing adjudication workflow (ambiguity surfacing is now a permanent, low-volume operational activity, not a migration artifact).

**Deliverables.** Contracted schema; audit report; refreshed baselines; documentation set; epic retrospective with the unknowns-vs-actuals comparison (M0's estimates vs. reality, including how M5/M6's track split compared to the single-milestone plan originally written — calibration data for the next epic's planning).

**Risks.** Premature contraction (mitigate: contraction requires the M5 Track B and M6 Native probation periods complete plus one explicit go decision; there is no schedule pressure that justifies contracting early, because coexistence is cheap and un-deletion is not).

**Definition of Done.** No symbol-keyed business path remains, including no remaining `resolve_asset()` call sites from M6 Compatibility-Layer; audit clean; validators clean; baselines refreshed; retrospective written.

**Depends on.** M5 Track B and M6 Native Integration complete, probation periods elapsed. (M5 Track A and M6 Compatibility-Layer are prerequisites of those, not independent gates on M7.)

---

## 6. Compatibility Strategy

The epic lives or dies on coexistence. The strategy is a one-way ratchet with four stations:

```
Old symbol world                 (M0: inventoried, baselined, untouched)
        ↓
Compatibility layer              (M1–M4: Registry + resolver exist;
                                  symbol ↔ asset_id mappings are total for
                                  live flows; every read answerable by
                                  either key; writes recorded both ways)
        ↓
Canonical Asset IDs              (M5–M6: engines cut over one at a time,
                                  behind flags; asset_id is operative;
                                  symbols still present as passive columns
                                  and instant-rollback path)
        ↓
Full migration                   (M7: shims removed, symbol keys retired,
                                  symbols live only in the Registry's
                                  evidence tier and at render time)
```

Coexistence rules during the middle stations:

- **The mapping is total before any cutover.** No consumer switches keys while any symbol it reads lacks a resolved identity. Partial mappings are the source of the worst coexistence bugs (two code paths disagreeing about the same row), so totality-per-consumer is checked mechanically before each flag flips.
- **One direction of authority at a time.** For any given record family, either the symbol or the `asset_id` is operative — never "whichever the code path happens to read." The flag defines which; the other is passively maintained.
- **New identity features wait.** Capabilities the old world cannot express (relationships, multi-listing distinction, classification history) are not *exposed* to users until the flows that would render them are id-keyed — otherwise the two worlds visibly disagree.
- **Coexistence is temporary by declaration.** Every shim ships with its removal milestone named (M7). The compatibility layer is scaffolding, and scaffolding left standing becomes architecture by accident.

**2026-07-09 addendum — two compatibility layers, not one.** The "Compatibility layer" station above was originally scoped as symbol ↔ `asset_id` mapping totality for M1–M4's own live flows (provider data, resolver evidence). The M6 Registry Read Path audit found a second, distinct compatibility need: **non-ledger consumers** (optimizer, execution, analytics, evaluation) that want Registry-informed reads *before* M5 Track B makes the ledger itself id-keyed. `resolve_asset()` (M6 Compatibility-Layer Integration, §5) is that second layer — read-time, additive, `Unresolved`-safe, and, like every other shim in this plan, named for removal at M7 once M6 Native Integration makes it redundant. It does not change the four-station diagram or its order; it is scaffolding *within* stations 2–3, scoped to consumers that do not require ledger-level replay parity to benefit from Registry-informed reads.

---

## 7. Database Migration Strategy

High level only; specific schema work is designed milestone by milestone during implementation.

**Philosophy: expand → backfill → verify → cut over → contract**, the parallel-change pattern, applied without exception:

- **Expand** — every structural change is additive: new tables for the Registry, new nullable references alongside existing symbol columns. Additive changes are deployable with zero downtime and zero risk to running code, because nothing existing reads them yet.
- **Backfill** — population runs online, in batches, resumable, and idempotent (re-running a backfill is always safe — the resolver's recorded-verdict discipline gives idempotency for free). The ledger's existing columns are **read, never written**: backfill adds references beside history, in the same spirit as ADR-002's rule that nothing compensates by touching the ledger.
- **Verify** — every backfill has a completeness check (zero unresolved rows) and a correctness check (parity against baselines) that must pass before the next step. Verification queries are kept and re-runnable, not one-shot.
- **Cut over** — reads switch per consumer behind flags; writes dual-record during the transition so rollback needs no data repair, only a flag flip.
- **Contract** — destructive changes (dropping symbol key columns, removing shims) happen only in M7, only after probation, and only once — the single place in the whole epic where a step is not trivially reversible, which is exactly why it is last and gated.

Zero downtime is achievable throughout because no step requires simultaneous change to schema and code: schema leads (additive), code follows (flagged), cleanup trails (gated). Migrations run through the platform's existing migration tooling and discipline; the dev/production parity rule (real migrations, no ad-hoc patches) applies as always.

---

## 8. Testing Strategy

Six verification tracks, cross-cutting all milestones. The first four share one instrument: the **golden baselines** cut in M0.

- **Regression.** The existing test suite passes unmodified at every milestone boundary — the platform's current behavior is the contract until a flag deliberately changes it. New Registry/resolver logic ships with its own suite (identity permanence, uniqueness, verdict discipline, lifecycle irreversibility as properties under test).
- **Replay verification.** The epic's supreme test: full-history replay per portfolio, id-keyed path vs. golden baseline, **bit-identical**. Run at M5 per-portfolio before each cutover, re-run after, re-run at M7. Any divergence stops the line: there is no such thing as an acceptable replay delta in this migration, because a delta means an identity mapped wrong, and wrong identities are permanent.
- **Accounting verification.** `verify_snapshots` (NAV continuity, P/L swing, holdings integrity, price integrity, return sanity) and `validate_ledger` run clean on the id-keyed path, and their findings are compared with the pre-migration run — the migration may not *introduce* findings, and "explained by pre-existing issue recorded in M0" is the only acceptable non-clean state.
- **Analytics verification.** Headline analytics (returns, attribution, sector exposure, human-vs-AI results) compared against baselines with three-way classification: identical / explained improvement (documented, e.g., DR disambiguation) / unexplained (blocking).
- **Migration verification.** Structural checks on the mapping itself: totality (every ledger symbol resolves), uniqueness (no symbol maps to two assets in the same market context; no two assets carry a decisively-identical evidence set without a recorded relationship or merge), round-trip (every minted asset traces back to the claims that justified it), and adjudication completeness (every ambiguity in the M3 dry-run has a recorded human verdict).
- **Provider verification.** Adapter contract tests (candidates only, never identity assertions); per-provider mapping fixtures for known quirks (DR spellings, venue suffixes); equivalence audits between symbol-keyed and id-keyed data reads during coexistence; and the disappearance test — deactivating a provider's mappings in a test environment must be an identity non-event.

---

## 9. Risks

Ordered by severity × likelihood. The first two are the reason this plan is shaped the way it is.

- **Wrong symbol mapping (severity: maximal).** One historical symbol resolved to the wrong identity mis-books every transaction that flows through it, and replay reproduces the error forever. *Mitigations:* backfill is adjudication (Principle 5); resolver thresholds biased toward surfacing; every ambiguity human-confirmed and recorded; per-portfolio replay parity before cutover — a wrong mapping that changes any accounting result is caught by the bit-identical gate before it becomes operative.
- **Duplicate assets.** Two identities minted for one instrument split its history invisibly. *Mitigations:* candidate matching against current *and historical* mappings before any minting; the M3 dry-run surfacing near-matches for review; M2's continuous duplicate auditing with explicit merge as the only remedy; migration-verification uniqueness checks.
- **Broken replay.** Any divergence between symbol-keyed and id-keyed replay. *Mitigations:* golden baselines cut before anything moves; parity as a hard per-portfolio gate; flags making reversion instant during the entire coexistence period.
- **Historical corruption.** The migration itself damaging ledger data. *Mitigations:* the ledger's existing columns are never written by any migration step; all changes additive until M7; backups per the platform's existing rebuild/backup discipline before each backfill wave; `validate_ledger` bracketing every wave.
- **Provider inconsistencies.** Vendor data contradicting itself or the inventory mid-migration. *Mitigations:* conflicts are first-class Registry findings, not migration blockers; the architecture's quarantine-and-adjudicate path absorbs them as ordinary weather.
- **Ambiguity volume.** The human adjudication workload turning out far larger than estimated. *Mitigations:* the M3 dry-run measures it *before* M5 Track B commits to a schedule; if large, adjudication becomes a scheduled workstream with the decisive majority migrating first. *Status (2026-07-09):* M5 Track A's bootstrap run against production-like data found the workload is small — 2 duplicate clusters and 11 unresolved transactions out of 52 — confirming the dry-run/quarantine discipline correctly separates the decisive majority from genuine ambiguity, rather than volume being a live concern. That backlog is now the named precondition on Track B's Definition of Done (§5).
- **Migration rollback.** Needing to retreat after a cutover. *Mitigations:* until M7, rollback is a flag flip plus dual-write catch-up — no data repair, because the old keys were passively maintained. After M7's contraction, rollback is a restore-from-backup event; this is precisely why M7 is gated on probation periods and an explicit go decision.
- **Scope creep into adjacent epics.** The Registry touching corporate actions, multi-currency, or new asset classes "while we're in here." *Mitigation:* §12 is the contract; anything on that list found mid-epic is written down for its own epic and not built.

---

## 10. Rollout Strategy

```
Development     →  Internal     →  Staging        →  Production     →  Cleanup
(per milestone)    (dogfooding)    (full rehearsal)   (flagged, per     (M7, gated)
                                                      consumer)
```

- **Development.** Each milestone develops against realistic data — a production-shaped copy including the genuinely messy symbols, because a resolver validated only on clean fixtures is unvalidated.
- **Internal.** The platform operator's own portfolios migrate first at every flagged step. This is the platform's established shadow-then-live pattern: the people who can read a parity report absorb the risk before anyone else does.
- **Staging: the full-history rehearsal.** Before M5 touches production, the *entire* migration — backfill, adjudication (with real human verdicts on the real ambiguity set), cutover, parity — is executed end to end against a production snapshot. The rehearsal's parity report is the go/no-go input for production. Rehearsal adjudication verdicts are kept and replayed into production, so the human work is done once.
- **Production.** Per-consumer, per-flag, in dependency order (accounting engines before analytics before presentation), each with its probation period. No two major cutovers in flight simultaneously — when something drifts, the cause must be unambiguous.
- **Cleanup.** M7 executes only after all probation periods pass and an explicit, recorded go decision. Contraction is the one step that is hard to reverse, so it is the one step that is never rushed.

---

## 11. Success Metrics

The epic succeeds when all of the following hold, each mechanically checkable:

- **Replay parity: 100%.** Full-history replay for every portfolio is bit-identical to the pre-migration golden baseline (and the M7 re-cut baselines become the new reference).
- **Zero accounting drift.** `verify_snapshots` and `validate_ledger` clean on the id-keyed path, with no findings introduced relative to the M0 run, through every probation period.
- **Analytics parity.** Headline analytics identical to baseline, or divergent only with a documented identity-correctness explanation reviewed and accepted.
- **Mapping totality and uniqueness.** Zero ledger rows without an `asset_id`; zero unresolved conflicts in the Registry's findings queue at M7; every historical ambiguity carries a recorded human verdict.
- **Stable APIs and workflows.** Existing user-facing behavior unchanged through the migration except deliberate improvements; no consumer-visible flag day occurred.
- **The architecture's own audit passes.** No engine below the resolution boundary reads a symbol; `display_symbol` appears only at render time (ASSET_REGISTRY.md §10's test, verified mechanically in M7).
- **Operational readiness.** The ongoing adjudication workflow (new ambiguities from live doors) is documented, staffed by the operator, and measured — surfaced-ambiguity counts and time-to-verdict are visible, because ambiguity surfacing is now a permanent product behavior, not migration residue.
- **The epic unblocked what it promised.** The Corporate Action and Multi Currency epics can begin against a stable identity layer without further prerequisite identity work — the true test of whether this was the right milestone.

---

## 12. Out of Scope

Explicitly deferred to later epics. Each depends on the Registry and none may sneak in with it:

- **Corporate Action Domain implementation** — the adjudication pipeline, event lifecycle, and dual-authority recording of [CORPORATE_ACTION_DOMAIN.md](../architecture/CORPORATE_ACTION_DOMAIN.md). This epic builds the identity layer corporate actions will *land on* (statuses, successor relationships, evidence updates), not the machinery that processes them.
- **Multi Currency** — the Registry records each asset's native currency as fact; FX conversion, multi-currency valuation, and reporting currency belong to their own epic.
- **Tax Engine** — cost-basis methodology, lot tracking, and jurisdiction rules.
- **Goal Planning** — beyond what already exists; no Registry-driven changes.
- **Wealth Platform / Wealth Domain** — net-worth aggregation across non-portfolio assets, even though the Registry's identifier-free identity support (property, private equity) makes it possible.
- **Risk Engine** — exposure and risk decomposition, even where Registry relationships (DR/underlying, listings) would feed it.
- **New asset classes** — options, futures, bonds, crypto expansion per ASSET_REGISTRY.md §11. The Registry is *built ready* for them (evidence shapes, relationship kinds); onboarding any of them is its own product decision and epic.
- **New providers or broker feed integrations** — the provider interface work here covers existing live flows only.
- **Execution Domain implementation** — the decision-ledger machinery of [EXECUTION_DOMAIN.md](../architecture/EXECUTION_DOMAIN.md); this epic only ensures existing decision records gain identity resolution like every other consumer.
- **Registry admin product** — M2's adjudication surface is deliberately minimal; a polished stewardship UI is future work.

---

## 13. Changelog

Modifications to this plan since its initial authoring, most recent first. Migration Principle 3 (§4 — "no flag days... every switchover is per-consumer, feature-flagged, reversible") applies to this document too: milestone text is revised in place when reality diverges from prediction, with the original scope preserved verbatim inside the revision rather than deleted, so a reader can always see what was originally intended alongside what actually happened. This is the first entry; no changelog existed before this revision.

**2026-07-10 — M6 Compatibility-Layer Integration, Phase 7 shipped: Classification Consolidation.**
- Audited every classification implementation in the codebase (not just `main.py`'s already-named sector system), per this milestone's own "do not assume this list is complete" instruction: three independently-drifted copies of `normalize_sector()` (`agents/optimizer.py`, `services/idea_review.py`, `services/optimizer/policy_engine.py`); `idea_review.py`/`basket_simulation.py`'s sector fallback chains (already Registry-aware for identity via Phase 2's `match_known_symbols`, not yet for classification); `services/symbol_market_convention.py` (confirmed Registry-internal bootstrap logic, not a duplicate); `services/broker_fees.py::resolve_fee_profile` (confirmed a fee-domain decision, not classification); `services/optimizer/execution_penalty.py::classify_execution` (re-confirmed as the existing, already-tracked Technical Debt Register row, not re-implemented). Full audit table with Replace/Keep/Deferred/Technical-debt classification for every finding: [CLASSIFICATION_CONSOLIDATION.md](CLASSIFICATION_CONSOLIDATION.md) §1.
- Extracted `main.py`'s `THAI_SECTOR_MAP`, `_DR_SECTOR_MAP`, `normalize_sector()`, `dr_prefix()` into a new module, `services/sector_taxonomy.py` — a byte-identical move (same map contents, same rules), done so the maps could be imported by both `main.py` and a new seed script without importing the FastAPI app module itself. Added one new pure helper, `static_sector_lookup(symbol, *, is_dr)`, factoring out the static-only lookup chain `main.py`'s `_get_sector()` already had inline.
- `main.py::_get_sector(symbol, fa_cache, db=None)` gained a new priority-0 check: `registry_lookup.resolve_asset(db, symbol)` → `AssetView.classification.get("SECTOR")`, consulted before the DR/Thai static maps and the FA-cache fallback. A Registry failure is caught, logged, and falls through — degraded mode is observable, never silent (ENGINEERING_PRINCIPLES.md "Failure Handling"). `db` is optional and defaults to skipping the Registry entirely, which is also the proof of safety: since the Registry currently holds zero SECTOR facts, `_get_sector()`'s output is byte-identical to its pre-Registry implementation until the new seed script is run. All 8 existing call sites in `main.py` (`add_holding`, `add_watchlist`, `_fetch_agents`, `/admin/backfill-sectors`, `/admin/fix-sectors`, `transaction_buy`, `transaction_initial_position`, plus `_fetch_sector()`'s own two internal calls) were updated to pass their already-in-scope request session.
- Added `services/registry_classification_seed.py::seed_sector_classification(db, symbols, *, dry_run=True)` — resolves each symbol via `registry_lookup.resolve_asset()` (ADR-004 reuse) and, for every symbol resolved to a minted Asset with no current SECTOR fact, writes one via `registry_service.record_classification()` using `sector_taxonomy.static_sector_lookup()` as the value. Never overwrites an existing fact, regardless of source (ADR-002). Exposed as `manage.py seed_registry_classification` (dry-run by default, `--commit` to persist), scoped to the workspace's existing `Watchlist`/`PortfolioItem` symbols — the exact universe `_get_sector()` actually serves, not a blind sweep of the static maps' keys.
- Three divergent `normalize_sector()` copies were found but **not** unified — unifying them would necessarily change behavior for at least two of the three call sites on any input where the rulesets already disagree, which directly conflicts with this adoption milestone's "existing behaviour must remain unchanged" mandate. Recorded as Technical Debt with the blocking dependency named (a product/engineering decision on the canonical ruleset) rather than silently left unmentioned. Same treatment for `idea_review.py`/`basket_simulation.py`'s not-yet-classification-aware fallback chains (deferred, scope-fence reasoning) and `execution_penalty.classify_execution` (unchanged carry-forward from the existing M6 read-path Technical Debt Register).
- Added `backend/tests/test_sector_taxonomy.py` (12 tests, proving the extraction is behavior-preserving), `backend/tests/test_registry_classification_seed.py` (7 tests), and `backend/tests/test_main_get_sector_registry.py` (13 tests, the full priority-order proof including a historical-only-alias-never-guessed case mirroring the Watchlist pilot's identical-premise test). Updated `backend/tests/test_watchlist_registry.py`'s `_fetch_sector` monkeypatch for the new `db` parameter (signature-only change, no behavioral change to that suite).
- Full regression, verified by `git stash`-isolating this milestone's changes and re-running the full backend suite (same `--ignore` exclusions as every prior entry): **byte-identical 58-failure pre-existing set before and after**, passed count up by exactly the 32 new tests (1073 → 1105), 32 skipped unchanged both times.
- Updated `docs/architecture/REGISTRY_INTEGRATION_GUIDE.md` (status banner, new "Phase 7: Classification Consolidation" section, current-status section declaring all 7 of §5's phases shipped) and this plan (M6 Compatibility-Layer status line above). Created `docs/implementation/CLASSIFICATION_CONSOLIDATION.md` (full audit, migration summary, retained fallbacks, technical debt, future work).
- **No database schema was changed. No Portfolio/Ledger/Replay/Optimizer-decision-logic/Recommendation/Analytics-algorithm code was touched — only duplicated sector-classification logic in `main.py` and, additively, a new Registry seed. Native Asset Persistence (M5 Track B) was not started, per this milestone's own "stop after Classification Consolidation" instruction. All 7 phases named in [M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md](M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md) §5 are now shipped.**

**2026-07-10 — M6 Compatibility-Layer Integration, Phase 1 step 2 shipped: Watchlist Registry Pilot.**
- Audited the complete Watchlist read path first, per the requesting brief's own instruction (API entry points, response model, symbol normalization, UI consumer) — see [WATCHLIST_REGISTRY_PILOT.md](WATCHLIST_REGISTRY_PILOT.md) for the full write-up. Found `GET /watchlist` (`main.py::list_watchlist`) has no existing symbol-matching/normalization logic of its own to replace (unlike the five `.BK`-variant shims Phase 2 retired) — it reads `Watchlist.symbol` directly and joins `AnalysisCache`/`AgentCache` by exact string match. This made it the lowest-risk possible pilot: purely additive metadata, zero existing logic to touch.
- Wired `services/registry_lookup.py::resolve_many()` into `list_watchlist` (batch, one call for the whole watchlist, reusing the shared TTL cache — no N+1) and `resolve_asset()` into `add_watchlist` (`POST /watchlist`, a single symbol) for response-shape consistency between the two endpoints, which already share the `_watchlist_row()` helper. Both endpoints add one new, additive `"registry"` key per entry: `{"resolved": true, "asset_id", "canonical_symbol", "market", "exchange"}` or `{"resolved": false, "reason"}` — the identical shape `services/registry_recommendation_context.py` already shipped (Phase 3 step 7), per ENGINEERING_PRINCIPLES.md's "Shared Schemas" principle (no layer-specific field names for the same fact). No existing field was renamed, removed, or changed in meaning; `DELETE /watchlist/{symbol}` was not touched (nothing in its response needs enrichment).
- Failure handling: both endpoints wrap their `registry_lookup` call in `try/except`, log a warning on failure, and degrade to `{"resolved": false, "reason": "not evaluated"}` — a total Registry outage cannot fail a Watchlist request (ENGINEERING_PRINCIPLES.md "Failure Handling": degraded mode is logged and observable, never silent).
- Added `backend/tests/test_watchlist_registry.py` (10 tests): a resolved entry carrying full metadata; an unresolved entry falling back cleanly; a historical-only alias (identifier superseded on its own asset, no current claimant) honestly reported unresolved rather than guessed; a recycled ticker (one symbol value claimed by two different assets over time) resolving to the *current* holder, never the stale original — the concrete identity-correctness property Watchlist gains that plain string equality could not provide; a mixed watchlist (resolved + unresolved + historical-alias entries in one call) resolved entry-by-entry with no cross-contamination; an existing-field-set regression proof (every pre-existing response key present and unchanged in value, for both a resolved and an unresolved entry); an empty-watchlist proof; and two Registry-outage tests (`GET`/`POST`) proving graceful degradation.
- Full regression, verified by `git stash`-isolating this change and re-running the full backend suite (same `--ignore` exclusions as every prior entry): **byte-identical 58-failure set before and after** (none in watchlist/registry modules), passed count up by exactly the 10 new tests (1063 → 1073), 32 skipped unchanged both times.
- Updated `frontend/lib/api.ts`'s `WatchlistItem` interface with an additive, optional `registry?: WatchlistRegistryView` field — no existing field changed; every current frontend consumer (`app/watchlist/page.tsx`) continues to compile and run unchanged, since nothing reads the new field yet.
- Updated `docs/architecture/REGISTRY_INTEGRATION_GUIDE.md` (status banner, new "Watchlist read path (Phase 1 step 2)" section, current-status section) and this plan (Compatibility-Layer status line above). Created `docs/implementation/WATCHLIST_REGISTRY_PILOT.md` (audit, implementation summary, compatibility notes, performance considerations, future adoption opportunities).
- **No database schema was changed. No Portfolio/Optimizer/Recommendation/Analytics/Execution/Ledger/Replay logic was touched — this pilot's scope was `GET /watchlist` and its two directly-related sibling endpoint/helper (`POST /watchlist`, `_watchlist_row()`) only, per the requesting brief's explicit scope fence. Classification Consolidation (Phase 7) and Native Asset Persistence (M5 Track B / M6 Native) were not started, per the brief's explicit "stop after the Watchlist pilot" instruction.**

**2026-07-09 — M5/M6 reconciliation after the M5.3 Registry Bootstrap and the M6 Registry Read Path audit.**
- Split **M5** into **Track A** (Ledger Evidence Builder, Migration Planner, Migration Executor, Registry Bootstrap — built and shipped as "M5.0–M5.3," Status: Complete) and **Track B** (the original M5 scope: adjudicated ledger backfill, full-coverage check, replay parity, engine cutover — Status: Not started). *Reason:* Track A's own implementation docstrings state explicitly that `Transaction`, `PortfolioItem`, and `PortfolioSnapshot` are never touched; treating "M5.0–M5.3 shipped" as "M5 done" would have been a false signal to every milestone depending on M5's hard gate.
- Recorded M5 Track A's bootstrap validation numbers permanently in this plan: 21 assets minted, 2 duplicate clusters correctly left unminted, 0 quarantined, 21/25 claim shapes resolved, 41/52 transactions resolved (2026-07-09 run against production-like data).
- Added an explicit precondition to Track B's Definition of Done: Track A's adjudication backlog (2 duplicate clusters, 11 unresolved transactions as of the above run) must be cleared or explicitly waived before Track B's full-coverage check can pass. This precondition did not previously exist because Track A was not yet a distinct concept when M5's original text was written.
- Split **M6** into **Compatibility-Layer Integration** (new track; a read-time `resolve_asset()` adapter over the existing M1–M3 Registry/Resolver, non-schema-changing, depends only on M2/M3, independent of M5 Track B — full detail in [M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md](M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md)) and **Native Integration** (the original M6 scope, unchanged, still hard-gated on M5 Track B). *Reason:* the read-path audit found the majority of read-path work (optimizer internals, execution sizing, analytics, evaluation, watchlist, idea intake) does not actually require ledger-level `asset_id` to become Registry-informed — only the ledger-adjacent paths (replay, `execution_analyzer.py`'s frozen-vs-live join) do.
- Updated the milestone order (§5) from a single chain to a branching order, and added a dependency graph making the M5/M6 branching explicit.
- Added a 2026-07-09 addendum to §6 (Compatibility Strategy) distinguishing the M1–M4 provider/resolver compatibility layer from the new M6 read-time compatibility layer — both are colloquially "a compatibility layer" but serve different consumers and different gates.
- Updated M6 Native Integration's Definition of Done to include retiring the Compatibility-Layer track's `resolve_asset()` call sites once native `asset_id` columns become available per consumer — previously implicit (M7 retires everything eventually) but now stated at M6, since a consumer can convert as soon as its own data is native without waiting for the full M7 contraction phase.
- Updated §4 Migration Principle 2 and the §9 "Ambiguity volume" risk entry to reference Track A/Track B by name and to record the measured 2026-07-09 backlog numbers.
- Added [M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md](M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md) to Related Documents.
- **No architectural decision was changed. No canonical model was changed. No database schema was changed by this revision.** This is a planning-document update only, per the requesting brief's own constraint; every milestone's original scope text is preserved verbatim within its revised section.

**2026-07-09 — M6 Compatibility-Layer Integration, Phase 1 step 1 shipped: Registry Lookup Foundation.**
- Added `backend/services/registry_lookup.py`: `AssetView` (immutable read projection — `asset_id`, `canonical_symbol`, `display_symbol`, `market`, `exchange`, `currency`, `asset_type`, `classification`), `Unresolved` (first-class non-exceptional not-found/ambiguous/conflict value), `resolve_asset(db, query)` (dispatches on `str` vs `int`/`AssetId` rather than the two separately-named signatures the requesting brief sketched — documented in the module's own docstring, since every other Registry-facing function in this codebase takes `db` as an explicit first argument and this module did not want to be the one exception), `resolve_many(db, queries)`, and a thread-safe, configurable-TTL, configurable-max-size, positive-and-negative-caching in-process cache (`configure_cache()`, `invalidate_cache()`).
- Reuses `identity_resolver.resolve()` for all symbol lookups rather than reimplementing its current-preempts-historical precedence rule (ADR-004) — verified by a dedicated test pair: a `PROVIDER_SYMBOL` value reused by a second, newer asset resolves decisively to the current holder, while a value that is only ever historical (no current claimant) is correctly reported `Unresolved` rather than guessed, since a lone historical `PROVIDER_SYMBOL` match falls under `DEFAULT_POLICY.resolved_threshold` by construction (M3's own weights, unmodified).
- Added `backend/tests/test_registry_lookup.py`: 18 tests covering resolved/unknown/historical lookups, cache hit/expiry/invalidation/max-size eviction, `asset_id`-keyed lookup, `resolve_many()`, no-ORM-leakage, and cache-level thread safety. Full pre-existing Asset Registry test family (`test_registry_service.py`, `test_identity_resolver.py`, `test_bootstrap_planner.py`, `test_registry_bootstrap.py`, `test_migration_executor.py`, `test_migration_planner.py`, `test_asset_registry.py`, `test_provider_adapter.py`, `test_ledger_evidence_builder.py`) re-run together with the new suite: 133 passed, 0 failed.
- Expanded `docs/architecture/REGISTRY_INTEGRATION_GUIDE.md` from its existing DO/DON'T stub into a full usage guide for `resolve_asset()` — the developer-facing companion to this module.
- Updated the M6 Compatibility-Layer Integration section's Status line (above) to distinguish "the module is built and tested" from "a consumer depends on it" — no existing file was modified, so `resolve_asset()` has zero callers as of this entry. Read-path plan Phase 1 step 2 (wiring `GET /watchlist` as the pilot consumer) remains open.
- **No database schema was changed. No existing file was modified. No business logic in Portfolio, Optimizer, Analytics, Execution, or Evaluation was touched.** This shipment is purely additive — one new module, one new test file, and documentation.

**2026-07-09 — M6 Compatibility-Layer Integration, Phase 2 shipped: duplicated `.BK`-variant shims retired.**
- Added `backend/services/registry_symbol_matching.py`: `match_known_symbols(db, symbols, known)`, the single shared adapter that replaces the five independently hand-rolled bare/`.BK`-suffix matchers named in [M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md](M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md) §2.3 item 3. It holds no identity rules of its own (ADR-004): every match is decided by `registry_lookup.resolve_asset()`, called on both the query symbol and every candidate; the legacy string heuristic only ever fires as a fallback for symbols the Registry could not resolve, and — critically — never against a `known` entry the Registry *did* resolve to a different `asset_id` (a genuine Registry conflict is never overridden by string-guessing; see the module's own docstring and `test_registry_conflict_is_not_silently_unified_by_bk_heuristic`).
- Rewired the five target modules to call it: `basket_simulation._resolve_symbol_sectors` (now the canonical, `db`-taking implementation used by every consumer), `execution_plan.py`'s holding-signal lookup, `position_sizing.py`'s `AnalysisCache` lookup and holdings-value lookup, `allocation_engine.py`'s `AnalysisCache` lookup, and `idea_review.py`'s `_get_sector`, `AnalysisCache` lookup, holdings lookup, and the `known_symbols`/`symbols_with_db_sector` yfinance-skip gate. `portfolio_construction.py` — a sixth, previously undocumented consumer of `basket_simulation._resolve_symbol_sectors` found while making this change — was updated for signature compatibility only; it carried no shim of its own and needed no behavioral change.
- One deliberate, documented behavior normalization: several of the retired shims were internally asymmetric (e.g. `basket_simulation`'s watchlist matching only ever stripped a stored `.BK` suffix, never appended one to a bare watchlist symbol, while its portfolio-holding matching did both; `idea_review`'s several independent expansions had similar inconsistencies). The shared fallback in `registry_symbol_matching.py` is symmetric everywhere. This can only ever *add* a match none of the old code found — it cannot remove one — so it is additive-safe, but it is a real, intentional behavior change and is recorded here per the requesting brief's own "if behavior changes, document why" instruction. Nothing in the codebase was found to depend on the old asymmetry.
- Added `backend/tests/test_registry_symbol_matching.py` (9 tests: exact match, a genuine Registry-decided match on a non-`.BK` spelling pair verified with `resolve_asset()` mocked — the identity_resolver's own current-vs-historical scoring makes two live identifiers on one asset resolve as ambiguous rather than both cleanly, so this branch is exercised with a controlled double-sided mock rather than fighting that pre-existing M3 behavior, which is out of this task's scope — legacy heuristic fallback both directions, no-match cases, the Registry-conflict-is-never-overridden property, and no-ORM-leakage) and `backend/tests/test_registry_symbol_matching_integration.py` (6 tests exercising all five DB-loading wrapper functions end-to-end: one `.BK`-variant-still-matches regression test per module, plus a Registry-conflict-is-not-silently-unified test for `basket_simulation.simulate_basket`).
- Full regression: the pre-existing `test_basket_simulation.py` (12 tests, pure-function only — the DB-loading wrappers this change touches had no prior test coverage) and `test_position_sizing.py` (12 tests, same), `test_risk_budget_allocation.py` (covers `allocation_engine.py`), `test_portfolio_construction.py`, and the full pre-existing Asset Registry test family, run together with the new suites: **116 + 91 tests passed, 0 failed** (some files counted in both runs; no unique failures anywhere). `execution_plan.py` and `idea_review.py` had no pre-existing unit test files at all before this change — coverage for their refactored paths comes entirely from the new integration test file.
- Updated the M6 Compatibility-Layer Integration section's Status line (above) and [M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md](M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md) §5 Phase 2's checklist to Shipped.
- **No database schema was changed. No Portfolio/Optimizer/Analytics/Execution/Evaluation business logic outside the five named `.BK`-matching shims (plus the one signature-compatibility fix in `portfolio_construction.py`) was touched. No work began on Phase 3 (recommendation write-path) or any later phase.**

**2026-07-09 — M6 Compatibility-Layer Integration, Phase 3 step 7 shipped: Recommendation write-path root fix.**
- Audited every place a Recommendation is created (per the requesting brief's "do not assume the list is complete — find every write path" instruction). Confirmed exactly one production write path exists: `main.py`'s `POST /analyze/optimizer`, which writes both `SignalHistory` rows and, via `services/decision_memory/snapshot_writer.py::write_recommendation_snapshot()`, the `RecommendationSnapshot` row. Audited and explicitly excluded `services/decision_memory/shadow_tracker.py`'s recommendation-shadow creation (`create_recommendation_shadow`, `create_active_model_shadow`, `create_static_frozen_shadow`) — these consume an already-written, frozen `RecommendationSnapshot` to build a paper-trading mirror; they do not generate a Recommendation, and are the read-path plan's own Phase 6, not Phase 3. Full reasoning and the complete audit trail are recorded in [M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md](M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md)'s new "Phase 3 Migration Report" subsection.
- Added `backend/services/registry_recommendation_context.py`: `build_registry_context(db, symbols)` resolves a batch of symbols via `registry_lookup.resolve_asset()` (zero new identity rules, ADR-004) and returns `{symbol: {resolved, asset_id, canonical_symbol, market, exchange}}` or `{resolved: false, reason}` per symbol, never raising — an unexpected error resolving one symbol is caught and recorded as `resolved: false` rather than aborting the batch. `enrich_scores_map_for_snapshot(db, scores_map)` wraps it into a *new*, additively-enriched copy of a recommendation's `scores_map` dict, deliberately never mutating the input.
- Rewired exactly one call site: `main.py`'s `POST /analyze/optimizer`, immediately before `write_recommendation_snapshot()` — `scores_map=scores_map` became `scores_map=enrich_scores_map_for_snapshot(db, scores_map)`, already inside the pre-existing failure-swallowing `try/except` around the snapshot write. The live `scores_map` that feeds the AI prompt, `portfolio_data`/`watchlist_data` construction, timing enrichment, and `services.optimizer.execution_penalty` is untouched — those all run *before* this call and read the original, unenriched dict, satisfying the requesting brief's "existing business logic must not change" and OPTIMIZER_PHILOSOPHY.md §6's judgment/arithmetic boundary (identity resolution never reaches the AI's input). `snapshot_writer.py` required **zero code changes** — its `scores_map_json=_j(scores_map)` was already a generic passthrough serializer, so the additive `"registry"` key rides through for free. Confirmed both existing read-side consumers of `scores_map_json` (`services/evaluation/execution_ledger.py`, `services/evaluation/recommendation_ledger.py`) index specific known fields (`current_price`) and never validate the full key set, so the new key is fully backward compatible with zero read-side changes required for safety.
- `SignalHistory` (the other per-run recommendation record) was audited and found unable to carry `asset_id` without a schema change — it has fixed typed columns and no free-form JSON field, and this phase's own brief states "No schema migration is permitted." Its rows remain symbol-only; flagged as a new Technical Debt Register row in the read-path plan.
- Added `backend/tests/test_registry_recommendation_context.py` (9 tests): a resolved symbol gaining full asset metadata; an unresolved symbol recorded honestly with a reason; an alias symbol (submitted spelling differs from the Registry's canonical spelling) resolving correctly while the submitted symbol is preserved as the dict key untouched; two differently-spelled symbols in one batch that the Registry says are the same instrument both carrying the same `asset_id` (mocked, for the same pre-existing identity_resolver ambiguity-on-live-data reason documented in the Phase 2 test file); a mixed resolved/unresolved batch; an unexpected exception on one symbol being caught and not propagating; a non-mutation proof (`enrich_scores_map_for_snapshot` never modifies its input dict or entries); a total-failure fallback proof (returns the original `scores_map` object unchanged if context-building itself raises); and an end-to-end persistence round-trip through the real, unmodified `write_recommendation_snapshot()` proving every original field survives in `scores_map_json` with only the additive `"registry"` key new.
- Full regression, verified by `git stash`-isolating the one-line `main.py` change and re-running the full backend suite (`--ignore`-excluding the pre-existing, unrelated `tests/investigate/`, `test_pandas.py`, `test_yf.py` network-dependent scratch scripts and `test_snapshot_repair.py`'s pre-existing native pandas access-violation crash, none of which this change touches): **identical 58 pre-existing failures before and after** (same asyncio-ordering/environment fragility documented since the AI Evaluation M0 changelog entry), passed count up by exactly the 9 new tests (1050 → 1059), 32 skipped unchanged both times.
- Updated `docs/architecture/REGISTRY_INTEGRATION_GUIDE.md` (status banner, new "Recommendation write-path metadata" section, current-status section) and [M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md](M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md) (Phase 3 step 7 marked Shipped with full detail, new "Phase 3 Migration Report" subsection, new Technical Debt Register row for `SignalHistory`).
- **No database schema was changed. No Portfolio migration. No Ledger/Replay changes. No Analytics migration. No Execution changes. No Recommendation model redesign — `RecommendationSnapshot`'s columns are unchanged; only the JSON content of the existing `scores_map_json` column gained an additive nested field. Phase 3 step 8 (read-side `asset_id`-awareness) and Phases 4–7 not started.**

**2026-07-10 — M6 Compatibility-Layer Integration, Phase 3 step 8 rescoped and shipped: AI Evaluation read-path business logic.**
- Audited every file in `backend/services/evaluation/` in full (per the requesting brief's own "audit first, do not assume the named list is exhaustive" instruction), rather than assuming the brief's named targets (`plan_grader.py`, `optimizer_action_summary.py`, `execution_analyzer.py`, `execution_report.py`, "AI evaluation helpers") were the correct or complete set. Found: `execution_report.py` does not exist anywhere in this codebase (the only match, `manage.py`'s `_print_execution_report()`, is unrelated CLI output for the M5 migration executor); `plan_grader.py` and `optimizer_action_summary.py` have no genuine cross-source identity join (both index a dict by symbols drawn from the same source list they were built from) and `build_action_summary` is a documented, enforced pure function that Registry calls do not belong inside; the actual named correctness risk (M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md §2.3 item 1 — the frozen-plan-vs-live-`Transaction.symbol` join) lives in `execution_analyzer.py`'s callers, not `execution_analyzer.py` itself, which is a deliberately pure, unit-tested function; and `services/analytics/attribution_engine.py::_timing_and_fee_effects` is a fourth, previously undocumented consumer of the same join, correcting this document's own prior classification of that file as "confirmed symbol-agnostic."
- Fixed at the DB-aware boundary rather than inside the pure function: `services/evaluation/execution_ledger.py::_linked_transactions(db, decision_id, known_symbols=None)` gained an optional `known_symbols` parameter — when the caller supplies the decision's plan symbols, each transaction symbol not already an exact match is resolved against them via `services/registry_symbol_matching.py::match_known_symbols()` (reused, no new identity rule, ADR-004) before the list reaches `compute_execution_analysis`. `compute_execution_analysis` itself was not modified — its pure-function contract and its existing test suite (`test_execution_analyzer.py`) are untouched.
- Three call sites wired: `execution_ledger.py`'s own `_decision_analysis`; `recommendation_ledger.py::get_report_card`, which previously duplicated the `linked_transactions`/`recommendation_prices` construction inline instead of reusing `execution_ledger.py`'s helpers — the duplication was removed in the same change (ENGINEERING_PRINCIPLES.md Single Source of Truth), so this call site both stopped duplicating logic and gained the Registry-aware fix for free; and `attribution_engine.py::_timing_and_fee_effects`, the newly-found fourth consumer.
- `horizon_grader.py::score_directional_calls` — audited and found to have a genuine cross-source symbol join (a recommendation's frozen inception holdings vs. a shadow's later frozen snapshot), but both sides are the same shadow's own machine-written output, not independently-sourced spellings the way the plan-vs-live-Transaction join is. Lower risk; **intentionally deferred**, not fixed this phase — recorded in the read-path plan's Technical Debt Register rather than silently left unmentioned.
- Added 3 new tests to `backend/tests/test_execution_ledger.py` (legacy `.BK` fallback links a previously-unmatched transaction with no Registry data minted at all; a genuine Registry conflict — two distinct minted assets, one per spelling — is never silently unified, the transaction stays unmatched exactly as before; wholly unrelated symbols stay unmatched, regression safety) and 1 new test to `backend/tests/test_recommendation_ledger.py` proving the same fix reaches `get_report_card`. All existing tests in both files, plus the full `test_execution_analyzer.py` suite, pass unmodified.
- Full regression, verified by `git stash`-isolating this phase's changes and re-running the full backend suite (same `--ignore` exclusions as every prior entry: `tests/investigate/`, `test_pandas.py`, `test_snapshot_repair.py`, all pre-existing native-crash exclusions unrelated to this change): **byte-identical 49-failure set before and after** (none in evaluation, registry, or attribution modules), passed count up by exactly the 4 new tests (1040 → 1044), 32 skipped unchanged both times.
- Updated `docs/architecture/REGISTRY_INTEGRATION_GUIDE.md` (status banner, new "AI Evaluation read-path (Phase 4)" section) and [M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md](M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md) (§1.6/§3.1 correction on `attribution_engine.py`, §2.3 item 1 updated with the partial fix, Phase 3 step 8 marked rescoped-and-shipped, new "Phase 4 Migration Report" subsection, three new Technical Debt Register rows: the residual M5-Track-B-gated risk, the deferred `horizon_grader.py` join, and the `execution_report.py` naming mismatch).
- **No database schema was changed. `execution_analyzer.py`'s pure-function signature was not changed. No Analytics/Portfolio/Replay migration. No changes to the Recommendation write path (Phase 3 step 7, already shipped). Phases 4–7 not started.**

**2026-07-10 — M6 Compatibility-Layer Integration, Phase 5 (Execution & Evaluation Completion Review): audit-only, no migration — Execution & Evaluation domains declared Registry-complete.**
- Requesting brief asked for a fresh audit of `backend/services/evaluation/` and `backend/services/execution/`, explicitly not assuming Phase 4's scoping still held, with two allowed outcomes: implement whatever genuinely qualifies, or declare the domain complete with rationale and a recommended next milestone. `backend/services/execution/` does not exist — the same class of naming mismatch as Phase 4's `execution_report.py` finding; "Execution" was interpreted as the domain the read-path plan's own §1.3 already names "Execution sizing/planning" (`services/execution_plan.py`, `services/funding_source_analysis.py`, `services/optimizer/execution_optimizer.py`, `services/optimizer/execution_penalty.py`, `services/optimizer/stabilization.py`).
- Every file in that set was read in full, alongside a re-check of the `services/evaluation/` files not already fully disposed of in the Phase 4 report (`scorecard.py`, `trust_report.py`, `verdict_composer.py`, `expired_writer.py` re-grepped for `symbol`, zero matches; `execution_analyzer.py`'s pure-function status re-confirmed unchanged). `override_classifier.py` was also read in full for completeness even though it sits outside both literal directories.
- Two new genuine cross-source-adjacent findings, both classified as technical debt rather than implemented, since neither satisfies "no business-logic redesign": `execution_penalty.py::classify_execution` infers `asset_type` from ticker shape (regex + hardcoded ETF list) instead of reading the Registry's own `AssetView.asset_type`, but its only call site (`main.py:2177`, `POST /analyze/optimizer`'s synchronous execution-context step) has no `db` session threaded to it — wiring Registry resolution in would mean changing this `agents/optimizer.py`-adjacent function's signature and control flow, not a caller-boundary fix. `stabilization.py::diagnose_duplicate_tickers` is diagnostic-only (scans one pipeline run's own L1/L2/L3 output dicts for same-symbol duplicates within that single run) — not a cross-source join, and already implicitly covered by this plan's existing note that it becomes unnecessary once `agents/optimizer.py`'s internal dict-keys migrate to `asset_id` (a separate, later, out-of-scope phase).
- `execution_optimizer.py::classify_reason` (already tracked in the Technical Debt Register as the §5 Phase 5 structural fix) was re-audited and reached the identical prior conclusion: blocked on `policy_engine.py` gaining a structured `subject_asset_id` field, a business-logic redesign, not a read-path fix.
- `funding_source_analysis.py::build_funding_sources` was read in full and confirmed to have no identity-join surface at all — its docstring already states "Pure service — no AI calls, no DB mutations, no side effects," and its symbol-keyed inputs (`item_values`, `signal_map`, `buy_set`) are all built by one caller from one holdings loop, with no independently-sourced second symbol collection to join against.
- **Zero source files changed this phase — audit-only.** No new tests were added, since no code changed; the audit table in the read-path plan's new Phase 5 Migration Report section is the "prove no implementation is necessary" deliverable in place of tests.
- Updated `docs/architecture/REGISTRY_INTEGRATION_GUIDE.md` (status banner, new "Execution & Evaluation Completion Review (Phase 5)" section, current-status section) and [M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md](M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md) (new "Phase 5 Migration Report" subsection, three new/refined Technical Debt Register rows: `execution_penalty.classify_execution`'s asset-type inference, `funding_source_analysis.py` confirmed no-op, and a cross-reference on the existing `execution_optimizer.classify_reason` row).
- **Outcome B: Execution & Evaluation integration declared complete.** Recommended next milestones (named, not started): Phase 1 step 2 (pilot `resolve_asset()` on `GET /watchlist`) or Phase 7 (classification consolidation, `THAI_SECTOR_MAP`/`_get_sector` becoming Registry-backed) — both outside this phase's Execution/Evaluation scope. **No database schema was changed. No source files under `backend/` were modified. No tests were added or needed. No Analytics/Portfolio/Replay/optimizer-internals migration.**

---

## Related Documents

- [ASSET_REGISTRY.md](../architecture/ASSET_REGISTRY.md) — the frozen architecture this plan implements
- [M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md](M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md) — the detailed read-path audit and 7-phase refactoring order behind M6 Compatibility-Layer Integration (§5)
- [CLASSIFICATION_CONSOLIDATION.md](CLASSIFICATION_CONSOLIDATION.md) — §5 Phase 7's full audit, migration summary, retained fallbacks, and technical debt for `main.py`'s sector-classification system becoming Registry-backed
- [WATCHLIST_REGISTRY_PILOT.md](WATCHLIST_REGISTRY_PILOT.md) — §5 Phase 1 step 2's audit and pilot report
- [ADR-005 — Replay Correctness Baseline](../decisions/ADR-005_REPLAY_CORRECTNESS_BASELINE.md) — resolves what "replay parity" means for M0's golden baselines and the M5 Track B gate
- [Architecture Handbook README](../architecture/README.md) — reading order and the document dependency chain
- [ENGINEERING_PRINCIPLES.md](../engineering/ENGINEERING_PRINCIPLES.md) / [DECISION_LOG.md](../engineering/DECISION_LOG.md) — the ADRs (ledger immutability, no compensation, one implementation per rule) this plan's principles instantiate
- [AI_EVALUATION_IMPLEMENTATION_PLAN.md](AI_EVALUATION_IMPLEMENTATION_PLAN.md) — the previous epic's plan; the milestone register and testing discipline here follow its precedent
