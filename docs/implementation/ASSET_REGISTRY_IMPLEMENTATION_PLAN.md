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
2. **Replay parity is the gate for everything.** Before any consumer switches keys, replay over the full history of every portfolio must produce results identical to a pre-migration golden baseline. Not approximately identical — identical. The existing `verify_snapshots` and `validate_ledger` audit tooling is the enforcement mechanism, extended where needed. Per [ADR-005 — Replay Correctness Baseline](../decisions/ADR-005_REPLAY_CORRECTNESS_BASELINE.md), "identical" means identical to *correct* accounting, not to the current implementation's defects: known correctness defects (e.g. the raw_symbol/canonical_symbol alias-splitting behavior found in M0) must be repaired before golden baselines are captured. **ADR-005 must be accepted before M0's golden baselines are captured, and before M5 — Portfolio Migration begins.**
3. **No flag days.** Old world and new world coexist for the entire epic. Every switchover is per-consumer, feature-flagged, reversible, and independently verifiable. There is no moment when the platform is broken-unless-everything-lands.
4. **Backward compatibility at every seam.** Existing imports, screens, and workflows keep working throughout. Users should be unable to tell the migration is happening except where the product deliberately improves (e.g., ambiguity surfacing on import).
5. **Backfill is adjudication, not string mapping.** The one-time resolution of historical symbols into minted identities goes through the same evidence-and-verdict discipline as live resolution (ASSET_REGISTRY.md §4). Decisive cases resolve in bulk; every ambiguity is surfaced to a human and the confirmation recorded. **No silent guessing during backfill** — a wrong historical mapping is exactly the multiplicative poison §7 warns about.
6. **Expand → verify → cut over → contract.** Every schema-touching step follows the parallel-change pattern: add alongside, backfill under audit, switch reads behind flags, remove only in M7.
7. **Instrumentation before migration.** Every milestone that moves data also ships the verification that proves it moved correctly. Verification is a deliverable, not an afterthought.
8. **One implementation per rule** (ADR-004). The resolver built for backfill is the same resolver used live afterward — no throwaway migration-only logic that then diverges from production behavior.

---

## 5. Milestone Breakdown

Suggested order: **M0 → M1 → M2 → M3 → M4 → M5 → M6 → M7**, with M3/M4 partially parallelizable after M2, and M5 as the hard gate before M6. Dependencies are noted per milestone. Per Migration Principle 2 (§4) and [ADR-005](../decisions/ADR-005_REPLAY_CORRECTNESS_BASELINE.md), M0's golden baselines may not be captured, and M5 may not begin, until ADR-005 is accepted.

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

---

### M5 — Portfolio Migration (the ledger gets its identity)

**Goal.** Every transaction, holding, and snapshot references an `asset_id` — additively, under audit, with replay parity as the gate. This is the epic's center of gravity and its highest-risk milestone.

**Scope.**
- **Adjudicated backfill**: run the M3 bulk resolution over the full ledger. Decisive cases map automatically; every ambiguous case is human-adjudicated through the M2 surface; nothing is committed until its verdict is recorded. The Transaction table's existing content is never modified — asset references are added alongside (the parallel-change expand step).
- **Full-coverage check**: zero ledger rows without an `asset_id` reference at the end of backfill. Unknowns are not skipped — they are minted as honestly-thin identities (absence is data, §7) or escalated.
- **Replay parity verification**: full-history replay for every portfolio, computed via the id-keyed path, compared against the M0 golden baselines. Identical or the milestone stops.
- **Engine cutover behind flags**: Portfolio Engine, Replay Engine, and the rebuild/validation tooling (`rebuild_portfolio`, `verify_snapshots`, `validate_ledger`) switch to `asset_id` as the operative key, per-portfolio or per-engine flagged, with instant reversion available.

**Deliverables.** Fully backfilled ledger references; adjudication log of every human decision made during backfill (these are permanent Registry mappings, not migration scratch); parity report per portfolio; flagged cutover complete for accounting engines; audit tooling running natively on `asset_id`.

**Risks.** This milestone concentrates the epic's three worst risks — wrong mapping, duplicate identity, replay divergence — and they are addressed in §9. The specific mitigations here: parity is checked per portfolio *before* that portfolio's cutover; the symbol column remains authoritative until parity passes; rollback is a flag flip for as long as M5 is in flight.

**Definition of Done.** 100% ledger coverage; replay parity **bit-identical** for every portfolio against golden baselines; `verify_snapshots` and `validate_ledger` clean on the id-keyed path; accounting engines running id-keyed in production for a probation period (suggested: two weekly cycles) with zero drift.

**Depends on.** M3 (resolver), M4 (price joins by `asset_id` — replay needs id-keyed valuation). **Hard gate for:** M6.

---

### M6 — Analytics & Intelligence Integration

**Goal.** Everything downstream of accounting — analytics, attribution, timing intelligence, the optimizer pipeline, the decision record, AI evaluation — reads `asset_id`, with symbols surviving only as render-time display lookups.

**Scope.**
- Analytics dimensions (sector, region, class) re-attached to Registry classification — dated facts, so period analytics can see classification *as it stood then* (§8).
- The recommendation/decision/evaluation chain re-keyed: recommendations, execution decisions, shadow tracking, attribution, and grading reference assets by identity. Frozen historical records are **not** rewritten — they gain resolution through the same additive mapping the ledger got, preserving the AI Evaluation domain's never-retro-edit rule.
- Presentation: `display_symbol` looked up at render time; screens stop passing symbols through business layers.
- Parity verification for headline analytics (returns, attribution, human-vs-AI results) against M0 baselines.

**Deliverables.** Id-keyed analytics and evaluation flows; analytics parity report; display-symbol lookup at the presentation boundary; classification-history support in period analytics.

**Risks.** Long tail of minor consumers discovered late (mitigate: the M0 census is the checklist; anything not on it is a census defect to record). Analytics differences that are *corrections* rather than regressions — e.g., a DR previously conflated with its underlying now correctly distinct (mitigate: parity report distinguishes "identical," "explained improvement," and "unexplained divergence"; only the third blocks).

**Definition of Done.** Census checklist fully dispositioned; analytics parity clean or explained; no business-layer symbol passing in the migrated flows; AI evaluation results stable across the cutover.

**Depends on.** M5 (hard gate).

---

### M7 — Cleanup (contract phase)

**Goal.** The coexistence machinery is removed, the old world is retired, and the end state is audited against the architecture's own test.

**Scope.**
- Remove dual-key reads, compatibility shims, and migration flags; retire symbol columns from ledger-adjacent storage once every consumer is confirmed id-keyed (symbols persist *in the Registry's evidence tier*, where they now belong — retirement means removal as *keys*, never as *evidence*).
- The final audit: **no engine can tell what any asset is called** (ASSET_REGISTRY.md §10) — a mechanical sweep for symbol access below the resolution boundary and presentation surface, plus review sign-off per engine.
- Golden baselines re-cut on the end state, becoming the new reference for future epics.
- Documentation: architecture handbook README coverage note, decision log entries for any judgment calls made during migration, and an operations note for the ongoing adjudication workflow (ambiguity surfacing is now a permanent, low-volume operational activity, not a migration artifact).

**Deliverables.** Contracted schema; audit report; refreshed baselines; documentation set; epic retrospective with the unknowns-vs-actuals comparison (M0's estimates vs. reality — calibration data for the next epic's planning).

**Risks.** Premature contraction (mitigate: contraction requires the M5/M6 probation periods complete plus one explicit go decision; there is no schedule pressure that justifies contracting early, because coexistence is cheap and un-deletion is not).

**Definition of Done.** No symbol-keyed business path remains; audit clean; validators clean; baselines refreshed; retrospective written.

**Depends on.** M5 and M6 complete, probation periods elapsed.

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
- **Ambiguity volume.** The human adjudication workload turning out far larger than estimated. *Mitigations:* the M3 dry-run measures it *before* M5 commits to a schedule; if large, adjudication becomes a scheduled workstream with the decisive majority migrating first.
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

## Related Documents

- [ASSET_REGISTRY.md](../architecture/ASSET_REGISTRY.md) — the frozen architecture this plan implements
- [ADR-005 — Replay Correctness Baseline](../decisions/ADR-005_REPLAY_CORRECTNESS_BASELINE.md) — resolves what "replay parity" means for M0's golden baselines and the M5 gate
- [Architecture Handbook README](../architecture/README.md) — reading order and the document dependency chain
- [ENGINEERING_PRINCIPLES.md](../engineering/ENGINEERING_PRINCIPLES.md) / [DECISION_LOG.md](../engineering/DECISION_LOG.md) — the ADRs (ledger immutability, no compensation, one implementation per rule) this plan's principles instantiate
- [AI_EVALUATION_IMPLEMENTATION_PLAN.md](AI_EVALUATION_IMPLEMENTATION_PLAN.md) — the previous epic's plan; the milestone register and testing discipline here follow its precedent
