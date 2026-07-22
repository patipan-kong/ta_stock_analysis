# M37.1 — Universal Asset Search Technical Design

**Date:** 2026-07-21

**Document class:** Technical Design Document (level-5 artifact, per Platform Architecture §11)

**Design status:** `APPROVED_AND_FROZEN`

**Lifecycle:** Technical Design Complete

**Implementation:** Implemented by M37.3

**Independent Review:** Approved

**Closeout:** M37_EPIC_CLOSEOUT.md

**Remediation record:** this document has been amended in response to the
Independent Technical Design Review (verdict: `PASS WITH REQUIRED
REMEDIATION`, findings F1-F15). Every change below is traceable to a
specific finding; see the accompanying Remediation Report for the full
disposition matrix. Sections not mentioned there were reviewed and found
sound, and are unchanged.

**Governing architecture (frozen, authoritative, not amended by this document):**
[M37-WP1](M37_WP1_Universal_Asset_Search_Foundation.md) — status `APPROVED_AND_FROZEN` after
Independent Architecture Review → Architect Remediation → Final Approval
(`APPROVED WITH MINOR NOTES`). This document also inherits the remediation's
placement decision (the Search door is hosted in Market Intelligence's
Discovery Layer, not a free-standing "boundary" service) as binding.

---

## 1. Technical Design Status and Authority

- **Milestone:** M37.1 — Universal Asset Search Technical Design.
- **Design status:** design only. No production code, no migrations, no
  runtime behavior change is introduced by this document.
- **Governing architecture:** M37-WP1 as approved and frozen. This document
  may not reopen any of its decisions.
- **Authority level:** this document has *technical design authority* only —
  it may decide module boundaries, contracts, data shapes, algorithms bounded
  by M37-WP1 §10.4, error taxonomies, and rollout sequencing. It has **no
  architectural authority**: it cannot create a domain, move an owned
  responsibility, or change what M37-WP1 assigned to Asset Foundation,
  Market Intelligence, or the Registry.
- **What this document may decide:** module placement inside the already-approved
  hosting (Market Intelligence's Discovery Layer / Asset Foundation's catalog
  read path); the public request/response contract's concrete shape; the
  ranking algorithm within §10.4's closed input set; the failure taxonomy;
  cache key/value shapes within the frozen cache doctrine; API routes; test
  strategy; rollout stages.
- **What this document may not decide:** whether search is a domain (settled:
  no); who owns identity, minting, or adjudication (settled: Registry); what
  ranking inputs are legal (settled, closed set, M37-WP1 §10.4); whether a
  new column may carry meaning the Registry doesn't already assert as fact
  (a descriptive name is metadata under Registry stewardship, not a new
  identity fact — consistent with §10.3's "identity vs. descriptive facts"
  split). **Correction (F4):** this document's original text proposed
  writing a provider-reported name directly into a bare `Asset.name` scalar
  with no selection rule, provenance, or update policy — a lesser but real
  version of the exact witness-becomes-authority failure the Registry's
  evidence-tier/identity-tier split (ASSET_REGISTRY.md §2, §6) exists to
  prevent. §9 now specifies a governed model, consistent with the same
  evidence doctrine `AssetIdentifier`/`AssetClassification` already follow,
  and still within this document's own level-5 authority (a descriptive
  fact's *governance*, not a new identity fact — the classification itself
  is unchanged, only its rigor).
- **Escalation condition:** if repository inspection had produced a direct,
  unresolvable contradiction with the frozen corpus, this document would stop
  and report it instead of designing around it. No such contradiction was
  found (see §25).

---

## 2. Current-State Assessment

Evidence gathered by direct repository inspection (paths and behavior as of
this commit), not by assuming architecture-named concepts already exist in code.

### 2.1 Registry read capabilities

- `backend/services/registry_query.py` — **exists, reusable, but narrow.**
  `find_identifier_rows(db, identifier_type, value)` returns exact-match
  `AssetIdentifier` rows, current and historical. This is an *exact
  identifier* lookup, not a text/name search. It is the correct building
  block for exact-symbol catalog matching; it is **not** sufficient alone for
  fuzzy/partial catalog search.
- `backend/services/identity_resolver.py` — **exists, reusable, load-bearing
  for merge/dedup, with one caveat corrected in this remediation (Finding
  F1).** `resolve(db, claim, policy=DEFAULT_POLICY) -> ResolutionResult`
  performs weighted, current-vs-historical evidence matching and returns a
  verdict (`RESOLVED` / `CANDIDATE` / `AMBIGUOUS` / `CONFLICT` / `UNKNOWN`,
  per `resolver_domain.py`). This is precisely the "Registry-recorded
  mappings" authority M37-WP1 §13 requires the merge stage to consult — it
  already exists and already forbids string-only guessing (`_score_candidates`
  works from identifier evidence, never name strings). **Correction:**
  `resolve()` is *not* unconditionally read-only as originally stated here —
  its existing behavior (`identity_resolver.py:83-85`) writes a durable
  `RegistryFinding` row (via `registry_findings_repository.create_finding`,
  which performs `db.add`/`db.flush`) whenever the verdict is `AMBIGUOUS` or
  `CONFLICT`. Calling `resolve()` from search's merge stage as originally
  designed would therefore write permanent Registry state on every
  ambiguous/conflicting discovery candidate — a real side effect, not a
  theoretical one. §3/§11 now specify a non-recording evaluation mode added
  to `resolve()` itself (never a second implementation) so search can
  consult the same matching/scoring logic without ever calling
  `_record_finding`. `adjudicate(...)` exists for human-confirmed resolution
  of ambiguity — out of scope for search itself (search never adjudicates,
  confirmed unchanged by this remediation), but it *is* the correct
  destination for a selected Discovery Candidate per M37-WP1 §14 stage 8.
- **Missing:** no text/name search over `assets` exists anywhere in the
  codebase today. This must be built (§9).

### 2.2 Asset schema — a concrete blocking gap

`backend/models/asset.py`'s `Asset` table has exactly these fields:
`canonical_symbol`, `asset_type`, `market`, `exchange`, `currency`, `status`,
`display_symbol`, `tradable`, `fractional_support`, `lot_size`,
`settlement_cycle`. **There is no `name` column, and no free-text descriptive
field of any kind.**

Meanwhile `backend/services/provider_domain.py`'s `ProviderObservation`
already carries `name: Optional[str]` — providers already report a name today
— but nothing in the ingestion or registry path persists it. This is not a
hypothetical gap; it is a concrete missing capability: **catalog search "by
name" (which M37-WP1 §14 stage 2 explicitly requires) has no column to read
from.** This is flagged as *missing and required*, not deferred — the
architecture already promised name-matching as part of catalog consultation,
and the design cannot honor that promise without it.

**Governance correction (F4):** the schema addition needed to close this gap
is not merely "add a nullable string column." Every other evidence-derived
fact already in this schema (`AssetIdentifier`, `AssetClassification`)
carries `source`, `is_current`, and retained superseded rows — a descriptive
name reported by a provider is exactly this kind of evidence, and deserves
the same governance, not a bare scalar with no selection rule for
conflicting provider names and no update policy for renames. §9 specifies
the governed model.

### 2.3 Provider / Discovery Layer capabilities

- `backend/services/provider_adapter.py`'s `ProviderAdapter` abstract class
  has exactly one method contract, `normalize()`, for translating a vendor
  payload into a `ProviderObservation` — a valuation/identity-evidence
  shape, not a search-results shape. **No adapter method for "search this
  provider's universe by free text" exists.**
- `ProviderCapabilities.supports_search: bool = False` **exists as a
  declared field**, but its own docstring states plainly: *"No behavior is
  implemented against this today — no router, no confidence policy consumes
  it... a label, not a callable capability."* `YahooFinanceAdapter` sets it
  to `False`. This confirms MARKET_DATA_PLATFORM.md §4's "User Search door"
  is a documented architectural concept with **zero runtime implementation**
  — existing but unsuitable is the wrong characterization; the honest one is
  **missing and required**, with one field usefully pre-declared.
- `backend/services/symbol_resolver.py` — **exists, but must not be reused
  inside the canonical boundary.** It is an explicit, hardcoded,
  yfinance-specific dialect table (`YFINANCE_SYMBOL_MAP`, DR-suffix
  stripping rules) — exactly the kind of provider-symbol-convention logic
  PROVIDER_INTERFACE.md's waterline exists to keep below the line. It is
  correctly placed today (used only inside the yfinance adapter path) and
  must stay there; the search design must not call it directly or duplicate
  its pattern for a new provider.

### 2.4 Search-related caches

- MARKET_DATA_PLATFORM.md §12 already documents a **Search Cache** concept
  (owned by Market Data Platform, "least trusted, most disposable"), but
  **no implementation of it exists in the repository.** Existing caches
  found (`technical`/`news`/`fundamental`, referenced in ARCHITECTURE.md and
  visible in `data_fetcher.py`'s per-kind TTL handling) are valuation/analysis
  caches, unrelated to instrument search. Missing and required.

### 2.5 Frontend asset-entry surfaces (confirms R7 concretely)

- `frontend/components/TransactionModal.tsx` — a raw `<input>` bound to
  `symbolInput`, uppercased on change, with the symbol subsequently *manually
  stripped of a `.BK` suffix for display* (`symbolDisplay.replace(".BK", "")`)
  directly in component code. This is a live, shipped instance of a
  provider/venue-dialect concern leaking into the Experience layer — the
  exact failure class Law 10 and PROVIDER_INTERFACE.md's waterline exist to
  prevent, and precisely what R7 warned would keep happening absent a shared
  seat.
- `frontend/components/operations-center/idea-intake/IdeaIntakeCard.tsx` —
  a free-text textarea parsing comma/newline-separated tickers
  (`parseSymbols(input)`), capped at 10, with no lookup, autocomplete, or
  validation against the catalog at entry time.
- `frontend/lib/api.ts` — **exists, reusable.** This is the established,
  single shared API-client module convention (also used for `goal.ts`,
  `executionPlan.ts`, etc., as sibling client files). The new search client
  belongs here, as a sibling module, per the M36.1 "one mechanism" precedent
  the architecture already cites.

### 2.6 API and router conventions

- `backend/main.py` is a large flat FastAPI app with the overwhelming
  majority of endpoints declared directly as `@app.get/@app.post(...)`
  (e.g. `/portfolios/{portfolio_id}/holdings`, `/watchlist`,
  `/analyze/{symbol}`).
- A `backend/routers/` package exists but is nascent — only
  `scheduler.py` (`APIRouter(prefix="/scheduler", ...)`) and an `auth`
  router are mounted via `app.include_router(...)`. This is the *emerging*,
  not yet dominant, convention.
- **Decision for this design:** use the `routers/` pattern (new
  `backend/routers/asset_search.py`, `APIRouter(prefix="/asset-search",
  tags=["asset-search"])`) rather than adding to the `main.py` monolith —
  consistent with where the codebase is visibly heading, and it keeps the
  new, architecturally sensitive surface in one isolated, reviewable module
  rather than interleaved with 600+ unrelated routes.

### 2.7 Test conventions

- `backend/tests/` is flat, one file per concern, named `test_<concern>.py`
  (`test_identity_resolver.py`, `test_registry_symbol_matching.py`,
  `test_provider_adapter.py`, etc.), using direct pytest functions
  (`def test_...`), not classes. The design's test strategy (§19) follows
  this convention exactly: new files `test_asset_search_*.py`.

### 2.8 Summary table

| Component | Status |
|---|---|
| Exact identifier lookup (`registry_query.py`) | Existing, reusable |
| Claim adjudication (`identity_resolver.resolve`/`adjudicate`) | Existing, reusable — is the merge/dedup authority, but `resolve()` requires a new non-recording mode (WP2a, F1) before search may call it |
| Catalog name/text search | Missing and required |
| `Asset.name` (or equivalent descriptive field) | Missing and required |
| Provider search method on `ProviderAdapter` | Missing and required (`supports_search` flag pre-declared, unused) |
| Search Cache (MDP §12 concept) | Missing and required |
| yfinance dialect normalizer (`symbol_resolver.py`) | Existing, unsuitable for reuse inside the boundary — must stay adapter-internal |
| Shared frontend API client convention (`lib/api.ts`) | Existing, reusable |
| Ad-hoc symbol entry (`TransactionModal`, `IdeaIntakeCard`) | Existing, unsuitable — migration targets (§20) |
| Router convention (`routers/`) | Existing, reusable, nascent |
| Ranking algorithm | Missing, deferred within §10.4's bound (§22) |

---

## 3. Proposed Module Placement

Per the frozen remediation, the door is hosted in Market Intelligence's
Discovery Layer; Asset Foundation hosts catalog searchability and any
catalog index; no free-standing "boundary" package exists.

| Module | Responsibility | Owner (domain) | Allowed deps | Forbidden deps | Source-of-truth? |
|---|---|---|---|---|---|
| `backend/services/asset_search/catalog_search.py` | Text/identifier match against `assets` + `asset_identifiers` + `asset_classifications`; classification filters; deterministic catalog ordering | Asset Foundation | `models.asset`, `models.database` | Provider adapters, Discovery door, HTTP layer | No — projects Registry data |
| `backend/services/asset_search/catalog_index.py` (optional, §9) | Disposable, rebuildable acceleration structure over catalog text fields | Asset Foundation | `catalog_search.py`'s read shapes only | Any provider code | No — explicitly disposable derivation (R1) |
| `backend/services/asset_search/discovery_search.py` | Fan-out to providers via existing `ProviderAdapter`s, `ProviderCapabilities.supports_search` gating, concurrency/timeout bounds, normalization to `DiscoveryCandidate` | Market Intelligence (Discovery Layer) | `provider_adapter.py`, `provider_domain.py` | `models.asset` write path, `identity_resolver.adjudicate` | No — projects provider claims |
| `backend/services/asset_search/merge.py` | De-dup: consults `identity_resolver.resolve(db, claim, record_finding=False)` per discovery result; folds recognized matches into registered candidates | Market Intelligence (Discovery Layer) | `identity_resolver.resolve` (non-recording call only, see below) | `identity_resolver.adjudicate`, any string-similarity "sameness" heuristic, any call to `resolve()` without `record_finding=False` | No |
| `backend/services/asset_search/ranking.py` | Deterministic ordering per §12 | Market Intelligence (Discovery Layer) | pure functions of candidate fields | Any DB/network call | No |
| `backend/services/asset_search/search_service.py` | Orchestrates the lifecycle (§8): validates request, calls catalog/discovery per scope, merges, ranks, assembles degradation, returns envelope | Market Intelligence (Discovery Layer) — this *is* the matured User Search door | all of the above | Nothing above the Experience boundary; no ledger, portfolio, or decision-layer import | No |
| `backend/services/asset_search/cache.py` | Search Cache per MDP §12 (external-result caching only) | Market Intelligence | in-process or Redis-backed KV, TTL only | `models.asset` (must never cache identity) | No — disposable, TTL-bound |
| `backend/routers/asset_search.py` | HTTP transport: request parsing, response serialization, error mapping | Experience-facing transport, calls `search_service.py` only | `search_service.py` | Direct provider or DB access | No |
| `frontend/lib/assetSearch.ts` | The one shared frontend search client | Experience Platform | `lib/api.ts` conventions | Direct `fetch` to provider URLs (none should ever exist client-side) | No |
| `frontend/components/asset-search/AssetSearchInput.tsx` (+ result list) | The one shared search UI primitive | Experience Platform | `lib/assetSearch.ts` | Direct symbol-string manipulation (`.BK` stripping etc. stays a display-layer concern of `display_symbol`, never invented client-side) | No |

**Shadow-registry prevention, made structural, not just documented:**
`catalog_index.py` (if built at all — see §9's staleness discussion) may
**only** be imported by `catalog_search.py`, and its build/read functions
take the same `Session` the Registry's own read path uses — there is no
second connection, second store, or independently-writable table. Any
schema for it (should implementation choose a persisted index over an
in-memory one) is additive only, rebuildable from `assets`/`asset_identifiers`
in one deterministic pass, and carries no column the Registry itself does
not already assert (it is an index *of* Registry fields, never a *cache of
opinions about* them).

**Resolver reuse without a durable write (F1 remediation, load-bearing):**
`identity_resolver.py`'s `resolve()` is the one and only matching/scoring
implementation; this design does not fork it or add a parallel resolver.
Instead, `resolve()` gains one new keyword parameter:

```
def resolve(
    db: Session, claim: ResolutionClaim, *,
    policy: ResolutionPolicy = DEFAULT_POLICY,
    record_finding: bool = True,
) -> ResolutionResult:
```

- **Default (`record_finding=True`):** identical to today's behavior in
  every respect — every existing caller (`adjudicate()`'s callers, any
  ingestion path that resolves a claim) is a no-op change; `AMBIGUOUS`/
  `CONFLICT` verdicts still write a `RegistryFinding` row exactly as before.
  This is what backward-compatibility tests (§19) assert.
- **`record_finding=False` (new, search-only):** `_match_candidates`,
  `_score_candidates`, and `_classify` — the pure evaluation logic — run
  unchanged; the single `if verdict in (AMBIGUOUS, CONFLICT): finding =
  _record_finding(...)` call is skipped entirely. `ResolutionResult.finding`
  is always `None` for a `record_finding=False` call. No transaction is
  opened, no `db.add`/`db.flush` occurs, no row is created — verified by a
  dedicated unit test asserting zero `RegistryFinding` rows exist after any
  number of `resolve(..., record_finding=False)` calls against ambiguous/
  conflicting fixtures (§19).
- **Caller behavior:** `merge.py` is the only caller in this design that
  ever passes `record_finding=False`; it must never call `resolve()` with
  the default. This is enforced by a conformance test grepping
  `services/asset_search/merge.py` for the literal call shape.
- **Why this is the correct option (not a parallel extraction):** `resolve()`
  already structurally isolates recording behind the single `if verdict in
  (...)` guard at line 84 of the existing implementation — no internal
  refactor of `_match_candidates`/`_score_candidates`/`_classify` is needed,
  only a guard on the one branch that writes. This keeps `identity_resolver.py`
  as the sole implementation of matching, scoring, and classification, per
  ADR-004 and the review's explicit "do not create a second resolver"
  constraint.
- **Adjudication is unaffected:** `adjudicate()` is not touched by this
  change and search never calls it, consistent with M37-WP1's no-adjudication
  rule — restated, not reopened.

---

## 4. Public Search Contract

```
SearchRequest:
  query: str                      # required, 1-200 Unicode code points pre-normalization (F11 — see order below)
  scope: "CATALOG" | "UNIVERSE"    # required, no default — no silent widening
  classification_filters: {        # optional, all keys from ASSET_REGISTRY.md §8's
    asset_class?: str              # stewarded taxonomy — never a free-form string
    market?: str
    region?: str
    currency?: str
    exchange?: str
  }
  limit: int = 20                  # optional, clamped [1, 50] server-side
  cursor: str | None = None        # optional, opaque continuation token — CATALOG scope only (§15 pagination policy, F9)
  timeout_ms: int | None = None    # optional, caller-supplied soft deadline, clamped [200, 5000]
```

- **Query text:** UTF-8, human-shaped. No identifier-kind auto-detection in
  v1 (deferred, §22 item 1) — a bare ISIN or FIGI is treated as query text
  and matched against identifier columns like any other token; recognizing
  *which* identifier kind it is remains deferred.
- **Locale/market hints:** *not included* in v1. Justification for omission:
  no current provider or catalog data is locale-tagged beyond `market`
  (already a classification filter); adding a separate hint field before any
  consumer needs it would be speculative surface the architecture's §5 non-goals
  table already forbids designing prematurely (ranking/tokenization
  internals are explicitly deferred, §10.4).
- **Caller context:** *not included.* Search is Current-Selection-independent
  by architecture (M37-WP1 §11); no workspace or portfolio identifier is
  part of the contract. Any "already held" decoration is an Experience-layer
  join performed by the caller *after* receiving candidates, never a
  parameter search consumes.
- **Timeout/deadline:** caller-controlled, optional, bounded server-side —
  justified because UNIVERSE scope's latency is provider-hostage (M37-WP1
  §21 weakness 3) and a caller (e.g., a modal wanting a snappy UX) needs a
  way to ask for a faster, possibly more-degraded answer.
- **Validation rules:** `scope` absent or invalid → `400 INVALID_SCOPE`
  (never defaulted — no silent fallback, M37-WP1 §10.2). `query` empty after
  normalization → `400 EMPTY_QUERY`. `classification_filters` keys outside
  the stewarded taxonomy → `400 UNKNOWN_FILTER_DIMENSION`. `limit` outside
  `[1,50]` → clamped, not rejected (a caller asking for 500 gets 50 plus a
  `warnings` entry, not an error — see §5). `cursor` non-null with
  `scope=UNIVERSE` → `400 CURSOR_NOT_SUPPORTED_FOR_SCOPE` (F9, §15).
- **Query length/normalization order, made precise (F11 — the original text
  stated this inconsistently in two places: "1-200 chars after
  normalization" here vs. "hard cap 200 chars pre-normalization" in §17;
  this is now the single, exact sequence, applied nowhere else):**
  1. Reject if raw input exceeds 200 Unicode code points (pre-normalization
     length cap — bounds worst-case normalization/matching cost before any
     other processing runs) → `400 QUERY_TOO_LONG`.
  2. Unicode NFC-normalize.
  3. Trim leading/trailing whitespace; collapse internal whitespace runs to
     a single space.
  4. Reject if the result is empty → `400 EMPTY_QUERY`.
  5. No further length re-check is needed — NFC normalization and
     whitespace collapse never increase code-point count beyond step 1's
     cap for the scripts this design targets, so a second length
     enforcement after step 3 would be dead code, not a real safeguard.

  Case-folding and script-aware matching remain `catalog_search.py`'s
  internal, deferred tokenization concern (§9, §22 item 1) — no case-folding
  decision is made at this contract layer.

---

## 5. Search Result Contract

```
SearchResponse:
  candidates: List[Candidate]       # ordered per §12
  scope_used: "CATALOG" | "UNIVERSE"  # echoes the request; never silently widened
  degraded: bool
  degradation: List[DegradationEntry]   # empty if degraded == false
  cursor_next: str | None            # opaque continuation, CATALOG scope only; always null when scope_used=UNIVERSE (F9, §15) or when exhausted
  warnings: List[str]                # e.g. "limit clamped to 50"
  query_echo: str                    # the normalized query actually matched against

DegradationEntry:
  source: str                       # "catalog" | "catalog_index" | "registry-merge" | "universe" | "<provider_name>" (provider identity as PROVENANCE, not a branching field consumers key logic on)
  reason: "TIMEOUT" | "UNAVAILABLE" | "UNSUPPORTED" | "ERROR"
  message: str                      # human-safe, no stack traces, no vendor error bodies (§17)
  candidate_kind_uncertain: bool = false  # true only for source="registry-merge": signals that DiscoveryCandidate results in this response may include assets that are actually already registered, because the merge check could not be completed (F3)
```

- **No timing/diagnostic fields** are included in the response body — those
  belong to observability (§18), not the canonical contract, per M37-WP1
  §12's "that is the entire public surface" discipline. A caller wanting
  latency data reads it from response headers or server-side telemetry, not
  the JSON envelope.
- **Canonical vs. presentation-convenience distinction:** `candidates`,
  `scope_used`, `degraded`, `degradation` are canonical (every consumer must
  handle them). `warnings` and `cursor_next` are presentation conveniences —
  a consumer may legally ignore `warnings`; it may not ignore `degraded`.
- **`UNSUPPORTED` vs. `UNAVAILABLE` (F15):** these are distinct facts, not
  interchangeable synonyms for "no discovery results." `UNSUPPORTED` means
  no capability-eligible provider exists at all (today's permanent v1
  state, pre-WP6, per §10 — a configuration fact, not an incident).
  `UNAVAILABLE` means eligible providers exist but could not be reached
  this request (a transient, retryable fact). `TIMEOUT` and `ERROR` remain
  as originally specified, per-provider only. The frontend (§16) renders
  these differently: `UNSUPPORTED` shows no user-facing warning banner at
  all (it is not a fault); `UNAVAILABLE`/`TIMEOUT`/`ERROR` show the
  dismissible degraded-state notice.
- **`registry-merge` source and `candidate_kind_uncertain` (F3, new):**
  when the merge stage's `resolve()` check fails for one or more discovery
  candidates (§8 stage 7, §11), the response includes exactly one
  `DegradationEntry(source="registry-merge", reason=ERROR,
  candidate_kind_uncertain=true)`. This is the only field on
  `DegradationEntry` that is source-specific, because it carries a
  semantically distinct fact: the *classification itself* (registered vs.
  discovery), not merely the presence or freshness of results, may be
  wrong for the affected candidates. Every other `source` value leaves
  `candidate_kind_uncertain` at its default `false`.

---

## 6. Candidate Type Design

```
RegisteredCandidate:
  kind: "REGISTERED"                       # literal discriminant — never inferred client-side
  asset_id: int                            # Registry-owned, stable, safe for persistence and identity decisions
  canonical_symbol: str                    # Registry-owned, stable, safe for persistence
  display_symbol: str | None               # Registry-owned (evidence tier), mutable, safe for display only — never for identity decisions
  asset_type: str                          # Registry-owned, stable
  market: str; exchange: str; currency: str  # Registry-owned, stable
  classifications: Dict[str, str]          # Registry-owned (AssetClassification.dimension -> current value), stable-ish (versioned by is_current), safe for filtering, NOT safe for identity decisions
  status: str                              # Registry-owned (ACTIVE/SUSPENDED/...), stable, informs UI only
  match_field: str                         # ephemeral, this-query-only, describes what matched ("canonical_symbol"|"name"|"identifier:ISIN"...)

DiscoveryCandidate:
  kind: "DISCOVERY"                        # literal discriminant
  claim_id: str                            # ephemeral, this-search-only correlation token — NOT a persistent identifier, NOT an asset_id, must not be stored across requests
  provider_name: str                       # provenance only (M37-WP1 §11: "never a branching input")
  reported_symbol: str | None              # provider's own spelling — evidence, explicitly NOT canonical_symbol-shaped
  reported_name: str | None
  reported_identifiers: Dict[str, str]     # ISIN/CUSIP/etc. as reported — evidence, unverified
  market: str | None; currency: str | None
  match_field: str                         # ephemeral
```

- **A Discovery Candidate cannot masquerade as registered:** the
  discriminant `kind` is a required literal on the wire (not inferred from
  field presence), `asset_id` is physically absent from the type (not
  merely null) on `DiscoveryCandidate`, and `claim_id` is namespaced and
  documented as non-persistent so no caller mistakes it for identity.
  `reported_symbol` is never written to a field named anything resembling
  `canonical_symbol` or `display_symbol` anywhere in the contract, closing
  off the R5 leakage path M37-WP1 flagged.
- **Persistence safety:** only `asset_id` and `canonical_symbol` on
  `RegisteredCandidate` are safe to persist across requests (e.g., a
  watchlist entry). Everything on `DiscoveryCandidate` is safe only to carry
  forward *as the payload of a claim submission* (M37-WP1 §14 stage 8) —
  never as a standalone stored reference.

---

## 7. Search Scope Semantics

**CATALOG scope:**
- Sources consulted: `catalog_search.py` only.
- Sources that must not be consulted: any `ProviderAdapter`, any external
  network call, `discovery_search.py` is never imported by the CATALOG code
  path (enforced at the module-dependency level, verified by an
  architecture-conformance test, §19).
- Fallback: none. A CATALOG search that finds nothing returns an empty
  `candidates` list with `degraded: false` — loudly empty, never quietly
  widened to UNIVERSE (M37-WP1 §10.2).
- Timeout: bounded by the DB query itself; no external-latency exposure.
- Partial results: not applicable — single source.
- Identity guarantees: every candidate is `RegisteredCandidate`; `asset_id`
  is always Registry-verified.
- Disclosure: `degraded` is only ever `true` for CATALOG scope if the
  catalog index (if one exists, §9) is itself unavailable and the design
  falls back to a slower authoritative read — a performance degradation,
  disclosed honestly, never a correctness degradation.

**UNIVERSE scope:**
- Sources consulted: `catalog_search.py` **and** `discovery_search.py`
  (always both — universe scope never skips the catalog).
- Sources that must not be consulted: any provider adapter whose
  `ProviderCapabilities.supports_search` is `False` (checked before fan-out,
  never attempted then caught).
- Fallback: none in the "silently substitute a different provider" sense;
  bounded concurrent fan-out to all eligible providers is not a fallback,
  it is the defined behavior.
- Timeout: per-provider deadline derived from `timeout_ms` (request) or a
  server default (2000ms); a provider that misses its deadline is recorded
  as a `DegradationEntry(reason=TIMEOUT)` and excluded from the result, never
  awaited past the deadline (cancellation, §8 stage 5).
- Partial results: always returned — CATALOG-scope results are never
  withheld because a provider failed; the response is exactly "everything
  the catalog knows, plus everything reachable within the deadline,"
  disclosed honestly (M37-WP1 S8).
- Identity guarantees: none for `DiscoveryCandidate`s — they are explicitly
  unverified claims.
- Disclosure: any unreachable/timed-out/erroring provider produces exactly
  one `DegradationEntry`. Zero *capability-eligible* providers (today's
  permanent v1 state, pre-WP6 — no adapter declares `supports_search=True`)
  produces `degraded: true` with `reason=UNSUPPORTED, source="universe"`
  (F15 — a configuration fact, not an incident). Eligible providers that
  exist but all fail before/during fan-out produce `reason=UNAVAILABLE,
  source="universe"` instead — a distinct, retryable incident. The request
  still returns catalog results in both cases, never an error. Independently,
  if the merge stage's `resolve()` check fails (F3), a
  `source="registry-merge"` entry is added (§5/§11/§13) regardless of
  provider health — a discovery-vs-registered classification degradation,
  orthogonal to provider reachability, and it must never be conflated with
  or suppressed by a `source="universe"` entry.

---

## 8. Query Processing Lifecycle

| # | Stage | Input | Output | Owner | Failure behavior |
|---|---|---|---|---|---|
| 1 | Validation | `SearchRequest` | validated request or `400` | `routers/asset_search.py` | Reject with specific code (§4); never coerce `scope` |
| 2 | Query normalization | raw query string | normalized query string | `search_service.py` | Empty-after-normalization → `400 EMPTY_QUERY` |
| 3 | Scope resolution | validated request | confirmed scope (no widening) | `search_service.py` | N/A — scope is never "resolved" beyond echoing the caller's declared value |
| 4 | Catalog search | normalized query + filters | `List[RegisteredCandidate]` | `catalog_search.py` (Asset Foundation) | DB error → `503 CATALOG_UNAVAILABLE`; the whole request fails only for CATALOG scope — for UNIVERSE scope this becomes a `DegradationEntry` and the request continues with discovery-only results |
| 5 | External discovery fan-out (UNIVERSE only) | normalized query + filters | `List[DiscoveryCandidate]` + per-provider `DegradationEntry`s | `discovery_search.py` (Market Intelligence) | Per-provider timeout/error isolated (§10); never blocks other providers; bounded concurrency (§17) |
| 6 | Candidate projection | raw catalog rows / provider observations | typed `RegisteredCandidate`/`DiscoveryCandidate` | same as producing stage | A malformed provider payload is dropped with a logged (not user-facing) warning, never surfaced as a candidate |
| 7 | Registry-authoritative deduplication | projected candidates | merged candidate list, no duplicate registered assets | `merge.py`, calling `identity_resolver.resolve(db, claim, record_finding=False)` (F1 — never a recording call) | `resolve()` raising is treated as *merge-check unavailable* for that discovery candidate: the candidate is kept as `DISCOVERY` **and** a `DegradationEntry(source="registry-merge", reason=ERROR)` is recorded (F3) — never silently treated as a clean "no match" |
| 8 | Ranking and ordering | merged list | ordered list | `ranking.py` | Never fails — pure function; a candidate missing a rankable field sorts last within its tier, never excluded |
| 9 | Limit/pagination | ordered list | page + `cursor_next` | `search_service.py` | `limit` already clamped at validation; cursor decode failure → `400 INVALID_CURSOR` |
| 10 | Degradation assembly | accumulated `DegradationEntry`s | `degraded` flag + list | `search_service.py` | N/A |
| 11 | Response creation | all of the above | `SearchResponse` | `routers/asset_search.py` | Serialization error → `500 INTERNAL`, logged with full context server-side, generic message client-side |

---

## 9. Catalog Search Design

- **Search fields (v1):** `canonical_symbol`, `display_symbol`, current
  `AssetIdentifier.value` rows (all types), and — **contingent on the schema
  addition below** — a new descriptive name field.
- **Required schema addition, revised for governance (F4; flagged as a work
  package, §21, not silently assumed):** the original proposal — a bare
  `Asset.name: Column(String, nullable=True)` populated directly from
  whatever `ProviderObservation.name` a mint happened to carry — is
  rejected as under-governed. `AssetIdentifier` and `AssetClassification`
  (`backend/models/asset.py`) both model evidence-derived facts with
  `source`, `is_current`, and retained superseded rows; a provider-reported
  name is the same kind of fact and gets the same treatment (**Option B**
  from the review, chosen over a governed-scalar Option A because it
  requires no new selection-policy machinery beyond the pattern already
  proven twice in this schema):

  - **New evidence-tier table `AssetDescriptiveName`** (name mirrors
    `AssetIdentifier`'s shape deliberately): `asset_id` (FK), `value`
    (the reported name text), `source` (e.g. `"provider:yahoo_finance"`,
    `"mint_evidence"`), `is_current` (bool), `observed_at`. Historical rows
    are retained, never deleted, exactly as `AssetIdentifier` already does
    — the same audit/history expectation the review raised is satisfied by
    reusing the existing pattern rather than inventing a new one.
  - **Selection rule (new, closing the gap the original proposal left
    open):** at Verified-minting time, the mint's own evidence source
    provides the first `AssetDescriptiveName` row, marked current. A later
    provider observation reporting a *different* name for the same asset
    does **not** overwrite the current row automatically — it is recorded
    as a new row with `is_current=false` (evidence retained, never
    discarded) and surfaces as a `RegistryFinding`-style review item for a
    human to promote if appropriate, mirroring how `AssetIdentifier`
    conflicts are already handled (never a silent auto-update; renames are
    a deliberate, reviewed action, not an ingestion side effect).
  - **`Asset.name` (retained, redefined):** a derived, denormalized
    convenience column equal to the current `AssetDescriptiveName.value`
    for that asset, kept in sync only when a row is explicitly promoted to
    `is_current=true` (the same synchronous-update discipline already used
    elsewhere in this design, §9's index-rebuild rules) — never written to
    directly by any other code path. This keeps `catalog_search.py`'s query
    simple (matches against the denormalized column) while keeping
    provenance and history in the evidence tier, exactly as
    `AssetClassification`'s current-value/history split already works for
    classification dimensions.
  - **Conflict/localization/backfill:** conflicting provider names are
    retained as competing non-current rows (no forced single truth);
    localization (multiple names in different scripts/languages) is *not*
    solved by this design — `AssetDescriptiveName` supports multiple
    current rows in principle but this milestone only populates and
    searches one, and script-aware matching remains deferred per §22 item 1;
    backfill for existing assets is best-effort from any available
    provider evidence, explicitly non-blocking (an asset with no available
    name evidence simply has no `AssetDescriptiveName` row and a null
    `Asset.name`, degrading gracefully to symbol/identifier matching for
    that asset specifically).
  - **Staged conformance (F4):** WP2 (§21) ships symbol/identifier-only
    catalog search first and is **not** blocked by this model. Name search
    remains blocked until `AssetDescriptiveName` and its selection rule are
    implemented and migrated (new WP1b, §21) — this temporary state is
    disclosed via a `warnings` entry ("name search unavailable") on every
    response until WP1b ships, never silently presented as full name-search
    support.

  This remains additive, non-breaking, and squarely inside Asset
  Foundation's existing §6.1 "classification and descriptive facts"
  stewardship — no architecture amendment, only a migration, now with the
  governance the evidence tier already demands elsewhere in this schema.
- **Normalization:** same NFC + whitespace-collapse as the contract layer
  (§4); additionally case-insensitive comparison via the database's native
  case-insensitive collation/operator (`ILIKE` on Postgres; `LIKE` with
  `COLLATE NOCASE` on SQLite — both engines are live per
  `models/database.py`'s `DATABASE_URL` branching, so the design must not
  assume Postgres-only operators like `pg_trgm` for v1 correctness, only for
  a v2 performance enhancement, see below).
- **Exact vs. fuzzy:** v1 is **prefix/substring, not fuzzy** — deterministic,
  explainable, and portable across both database backends without a new
  extension. Fuzzy/typo-tolerant matching is explicitly deferred (§22 item 1,
  already flagged by M37-WP1 §18 item 1) because it requires a ranking-weight
  decision the architecture correctly withheld.
- **LIKE-metacharacter escaping (F6, new):** query text is escaped for `%`,
  `_`, and the chosen escape character before being interpolated into any
  `LIKE`/`ILIKE` pattern (via SQLAlchemy's `.escape()` argument to
  `.contains()`/`.startswith()` or an equivalent explicit `ESCAPE` clause),
  regardless of parameterization. Parameterized SQL prevents *injection* but
  does not prevent a caller-supplied `%` or `_` from being interpreted as a
  wildcard rather than a literal character — an unescaped `%` alone would
  match every row in the table, a cheap denial-of-service and a correctness
  bug (matching everything instead of nothing). This is verified by
  `test_asset_search_security.py` (§19) with wildcard-only and
  mixed-wildcard query fixtures.
- **Aliases/identifiers:** matched via `AssetIdentifier` current rows first;
  historical rows included only when no current row matches (mirroring
  `identity_resolver.resolve()`'s own current-preempts-historical rule, for
  consistency of mental model — not a shared code path, since search matching
  and identity adjudication are different operations run for different
  reasons).
- **Classification filtering:** `AssetClassification` rows filtered by
  `dimension` + current `value`, restricted to the dimension names
  ASSET_REGISTRY.md §8 stewards — never a caller-supplied arbitrary
  dimension.
- **Deterministic ordering:** within the catalog stage, ordered by match
  strength (exact canonical/display symbol > exact identifier > name
  prefix > name substring), then `canonical_symbol` ascending as a stable
  tie-break — before the cross-source ranking pass (§12) runs.
- **Index ownership:** Asset Foundation, per the Final Approval's binding
  resolution of Finding 3. Whether a persisted index is built at all in v1 is
  a deferred performance decision (§22 item 2) — the `assets` table's
  existing `unique, index=True` on `canonical_symbol` plus a new plain
  B-tree/trigram index on the new `name` column may be entirely sufficient
  at current data volumes (the catalog is a platform's own instrument list,
  not an internet-scale corpus).
- **Index rebuild rules:** if a persisted derived index (e.g., a
  materialized search-vector column) is added later, it is rebuilt
  synchronously in the same transaction that mints or reclassifies an asset
  — never by a background job racing the Registry's writes, and never
  read from a second store.
- **Stale-index behavior:** if a future implementation adds an async-refreshed
  index, a stale read must never be presented as `RegisteredCandidate` fact
  without being consistent with the Registry's current row at read time —
  v1 avoids this entirely by not introducing async staleness at all.
- **Fallback to authoritative reads:** always — the "index," if any, is
  additive to, never a replacement for, `catalog_search.py` querying `assets`
  directly. If the index is unavailable, the design falls back to a direct
  (slower) table scan, disclosed as a degradation (§7), rather than failing
  the request.
- **Consistency:** read-committed, same transaction isolation as every other
  Registry read; no eventual-consistency contract is introduced.

---

## 10. External Discovery Design

- **Capability detection:** `discovery_search.py` filters the set of
  registered `ProviderAdapter` instances to those whose
  `capabilities.supports_search is True`, evaluated **before** any network
  call — an adapter with `supports_search=False` (all adapters today,
  including `YahooFinanceAdapter`) is never attempted and never appears in
  `DegradationEntry`s (excluding it is not a failure, it's a correct
  non-eligibility).
- **Eligible provider selection:** all capability-eligible providers are
  queried, unconditionally — no popularity or commercial-preference
  ordering at the fan-out stage (that would be R2 territory; selection here
  is eligibility, not ranking).
- **Fan-out policy:** bounded concurrent fan-out, one task per eligible
  provider, via `asyncio.gather(..., return_exceptions=True)` or equivalent —
  concurrency bound: `min(eligible_provider_count, MAX_CONCURRENT_PROVIDERS)`
  with `MAX_CONCURRENT_PROVIDERS = 8` as a named constant (bounded, not
  "parallel" left vague).
- **Deadlines and cancellation:** each provider task is wrapped in
  `asyncio.wait_for(task, timeout=effective_timeout)`; on timeout the task is
  cancelled (not abandoned to run to completion in the background — a
  cancelled task must not later write to any cache or store), and a
  `DegradationEntry(reason=TIMEOUT)` is recorded.
- **Provider-specific translation:** delegated entirely to the existing
  `ProviderAdapter.normalize()` contract — a new "search" adapter method
  (`search(query) -> List[ProviderObservation]`, to be added, §21) reuses the
  exact same translation discipline already enforced for price/identity
  observations (no adapter written for this milestone invents a second
  translation pattern).
- **Provider result normalization:** `ProviderObservation` (already exists,
  already has `name`, `provider_symbol`, `isin`/`cusip`/`sedol`/`figi`) is
  reused as-is for search results — no new provider-facing shape is
  invented; `DiscoveryCandidate` projection is a thin, one-directional
  mapping from `ProviderObservation`.
- **Provider confidence limitations:** a provider's own relevance score, if
  it returns one, is **not** part of the canonical contract (it would be a
  provider-commercial-preference input to ranking, forbidden by §10.4/R2) —
  it may be logged for observability only.
- **Unsupported provider behavior:** silently excluded pre-fan-out (see
  capability detection above) — never attempted-then-errored.
- **Partial provider failure:** isolated per-provider by construction
  (`return_exceptions=True` / per-task try/except); one provider's exception
  never propagates to cancel siblings.
- **Zero-provider behavior:** if no adapter is capability-eligible (true for
  every adapter today, since none declares `supports_search=True`),
  UNIVERSE scope degrades to catalog-only results with a single
  `DegradationEntry(source="universe", reason=UNSUPPORTED)` (F15 — distinct
  from `reason=UNAVAILABLE`, which is reserved for eligible-but-unreachable
  providers) — this is the **expected v1 behavior**, not a bug, until a
  provider actually implements search (§21 work packages make this explicit
  so it isn't mistaken for a defect during initial rollout, and the frontend
  does not show a warning banner for `UNSUPPORTED`, §16).
- **Provider evidence never becomes canonical identity merely by appearing:**
  enforced by construction — `DiscoveryCandidate` has no `asset_id` field to
  populate, full stop (§6).

---

## 11. Merge and Deduplication

- **Registered-to-registered duplicates:** cannot occur — `catalog_search.py`
  queries `assets` directly, which has no duplicate rows for one `asset_id`
  by definition (SQL `DISTINCT asset_id` at the query layer as a belt-and-
  suspenders guard, though the schema already prevents it).
- **Discovery-to-registered relationships:** for each `DiscoveryCandidate`,
  `merge.py` builds a `ResolutionClaim` from its `reported_identifiers` (same
  shape `resolver_domain.ResolutionClaim` already expects) and calls
  `identity_resolver.resolve(db, claim, record_finding=False)` (F1 — the
  non-recording mode added to the one existing resolver; never `adjudicate()`,
  never a plain `resolve()` call that would write a `RegistryFinding`). A
  `RESOLVED` verdict with a `resolved_asset_id` means: drop the
  `DiscoveryCandidate`, and if that `asset_id` is not already present from
  the catalog stage (edge case: catalog search missed it because the
  provider's reported name didn't match but its ISIN does), add it as a
  `RegisteredCandidate` fetched fresh from the Registry.
- **Discovery-to-discovery duplicates:** two providers reporting the same
  unregistered instrument are **not** merged into one `DiscoveryCandidate`
  in v1 — each is presented separately with its own `provider_name`
  provenance, because merging them would require a sameness judgment call
  identical in kind to R4 (no recorded mapping exists for two *unregistered*
  claims to be compared against). This is a deliberate, disclosed
  limitation, not an oversight (§22 item 3 records it as a future
  possibility contingent on a policy decision the architecture didn't make).
- **Use of Registry-recorded mappings:** exclusively via
  `identity_resolver.resolve(db, claim, record_finding=False)` — no direct
  SQL, no string comparison, anywhere in `merge.py`.
- **Behavior when sameness is unknown (`AMBIGUOUS`/`CONFLICT`/`UNKNOWN`
  verdicts):** the `DiscoveryCandidate` is kept as-is (not merged, not
  discarded) — ambiguity at search time is not the search boundary's problem
  to resolve; it surfaces at handoff (M37-WP1 §14 stage 8) through the
  existing `adjudicate()` path if the user selects it. Because search calls
  `resolve()` with `record_finding=False` (F1), **no `RegistryFinding` is
  created by this comparison** — the ambiguity is not durably recorded
  until/unless the user actually selects the candidate and the handoff path
  calls `resolve()` (or `adjudicate()`) in its normal, recording mode.
- **Preservation of provenance:** `provider_name` is retained on every
  `DiscoveryCandidate` through to the response; it is never stripped by the
  merge stage even when a claim resolves.
- **Conflict handling:** a `CONFLICT` verdict from `resolve()` does not
  block the search response — the candidate is presented as `DISCOVERY`
  (unknown standing). Because the merge-stage call uses
  `record_finding=False`, this comparison writes nothing; no
  `RegistryFinding` exists for search to leave alone or disturb — search
  neither reads nor writes findings, now true in fact as well as in intent.
- **Merge-check unavailability (F3, new):** if `resolve()` itself raises
  (Registry DB unreachable, unexpected error) while evaluating a discovery
  candidate, the candidate is kept as `DISCOVERY` (never silently dropped)
  **and** the response records `DegradationEntry(source="registry-merge",
  reason=ERROR)` (§13). This is distinct from an `UNKNOWN`/`AMBIGUOUS`
  verdict (a decisive answer that no registered match exists) — it means
  the comparison could not be performed at all, so the candidate's
  `DISCOVERY` classification is *unverified*, not *confirmed unregistered*.
  The response must not let a `DiscoveryCandidate` produced under this
  condition imply "checked, and not in your catalog" — §16 specifies the UI
  consequence.
- **Deterministic output:** for a fixed catalog state, fixed provider
  responses, and fixed Registry mappings, `merge.py`'s output is the same
  set every time — no randomness, no unordered-set iteration exposed to
  output ordering (ranking, §12, is a separate deterministic stage).
- **Explicit prohibition, enforced structurally:** `merge.py` contains no
  import of any string-similarity library (`difflib`, `rapidfuzz`, etc.) —
  absence is verified by an architecture-conformance test (§19).

---

## 12. Ranking and Ordering

Bounded exactly to M37-WP1 §10.4's closed input set. Tiers, most-preferred first:

1. **Exact canonical/display symbol match** (registered only — a
   `DiscoveryCandidate` cannot match a canonical symbol, since it has none).
2. **Exact identifier match** (ISIN/CUSIP/SEDOL/FIGI/current provider symbol),
   registered before discovery within this tier.
3. **Name prefix match** (once §9's `AssetDescriptiveName` model and WP1b
   ship; degrades to skipping this tier gracefully until then, disclosed
   via `warnings` per §9's staged-conformance note).
4. **Name substring match.**

**Tier 5 removed (F5):** the original design included a fifth tier
returning every catalog row satisfying `classification_filters` even when
the query matched nothing — since `query` is never empty at this stage
(empty queries are rejected at validation, §4), this tier could only ever
fire for a genuinely non-matching query (e.g. `"zzzz"` with `market=TH`),
in which case it silently returned the entire filtered catalog. That
contradicts §7's "loudly empty" CATALOG behavior and had no bounded size.
There is no browse-mode contract in this design for "show me everything in
this filter regardless of what I typed"; if one is wanted later, it is a
new, separately-specified endpoint or parameter, not a ranking tier. A
query matching no text or identifier now returns zero candidates,
regardless of whether filters would otherwise match rows.

Within each tier: **registered before discovery** (per M37-WP1 §10.4's
"registered-before-unregistered precedence"), then alphabetical by
`canonical_symbol` (registered) or `reported_symbol` (discovery) as a
**deterministic tie-break** — never insertion order, never a hash-dependent
order.

- **Provider relevance:** excluded (§10, R2) — a provider's own score is
  never consulted.
- **Classification relevance:** only as an eligibility filter (§4, applied
  before ranking, never as a fallback result bucket after F5's removal of
  tier 5), never as a numeric weight blended with text match — keeps the
  ranking function auditable as "which tier, then which tie-break," not an
  opaque weighted sum.
- **Personalization exclusions:** no user ID, no history, no "you searched
  this before" signal enters ranking — enforced by `ranking.py` taking no
  caller-identity parameter at all (there is nothing to accidentally use).
- **Analytics/intelligence exclusions:** no performance, fit, or confidence
  score is a ranking input — enforced the same way (no such parameter
  exists on the function signature).
- **Not investment ranking:** nothing here answers "is this a good asset" —
  only "how well did this candidate match what was typed," exactly per
  M37-WP1 §5's non-goals table.

---

## 13. Failure and Degradation Model

| State | HTTP/API behavior | Candidates returned? | Degradation disclosed? | Retryable? | Observability |
|---|---|---|---|---|---|
| Invalid request (bad scope/empty query/unknown filter) | `400`, specific error code | No | N/A | No (caller must fix request) | Log at INFO, no alert |
| Catalog unavailable (DB error), CATALOG scope | `503 CATALOG_UNAVAILABLE` | No | N/A (whole request fails — catalog is the only source) | Yes | Log at ERROR, alert candidate |
| Catalog unavailable, UNIVERSE scope | `200`, degraded | Discovery-only | Yes, `reason=UNAVAILABLE, source=catalog` **and** `reason=ERROR, source=registry-merge, candidate_kind_uncertain=true` (F3 — the DB outage that took out the catalog also takes out `resolve()`, so no discovery candidate can be checked against Registry mappings; both facts must be disclosed together, never just the first) | Yes (retry may hit a healthy DB) | Log at ERROR, alert candidate |
| Catalog index unavailable (if one exists) | `200`, degraded (perf only) | Yes, via fallback scan (§9) | Yes, `reason=UNAVAILABLE, source=catalog_index` | N/A — self-heals via fallback | Log at WARN |
| Zero capability-eligible providers (F15) | `200`, degraded | Catalog-only | Yes, single `reason=UNSUPPORTED, source=universe` (not a warning banner in the UI, §16 — this is a configuration fact, not an incident) | N/A | Log at INFO, no alert |
| Provider unsupported (not capability-eligible, but ≥1 other provider is) | N/A — never attempted for that provider | N/A | No entry for that provider (not a failure) | N/A | No log needed |
| Provider timeout | `200`, degraded | Yes (partial) | Yes, `reason=TIMEOUT, source=<provider>` | Yes | Log at WARN, metric increment |
| Provider error | `200`, degraded | Yes (partial) | Yes, `reason=ERROR, source=<provider>`, message sanitized (§17) | Yes | Log at WARN with sanitized detail, full detail server-side only |
| Partial provider failure (some succeed) | `200`, degraded (for the failed subset only) | Yes | Per-failed-provider entries only | Yes | Per-provider metrics |
| Total universe-search failure (≥1 eligible provider exists, all fail) | `200`, degraded | Catalog-only | Yes, single `reason=UNAVAILABLE, source=universe` entry | Yes | Metric: universe-search-total-failure |
| Registry merge-check unavailable (`resolve()` raises, F1/F3) | `200`, degraded | Yes (affected candidates kept as DISCOVERY) | **Yes** — `reason=ERROR, source=registry-merge, candidate_kind_uncertain=true` (§5/§11; corrected from the original design, which treated this as an undisclosed internal detail — that violated honest degradation disclosure because a registered asset could be shown as "not in your catalog" with no signal that the check was skipped) | N/A | Log at ERROR — this indicates a Registry problem worth investigating |
| Cancellation (client disconnect / caller timeout) | Connection closed, no body | N/A | N/A | N/A | Log at DEBUG |
| Internal failure (unhandled exception, serialization error) | `500 INTERNAL`, generic message | No | N/A | Yes | Log at ERROR with full stack trace server-side only |

---

## 14. Cache and Index Design

**Asset Foundation catalog index** (if built at all in v1 — see §9's
deferral):
- Owner: Asset Foundation.
- Key shape: none (it is a database index/materialized column on `assets`,
  not a KV cache) — or, if a v2 in-memory acceleration structure is added,
  keyed by normalized query prefix.
- Value shape: `asset_id` references only, never full candidate payloads
  (payloads are always re-projected fresh from `assets`/`asset_identifiers`
  at read time, so a stale index can never serve a stale *name* or *status*).
- TTL/invalidation: none needed for a DB index (transactionally consistent
  by construction); if a v2 in-memory structure exists, invalidate
  synchronously on write, never TTL-based, per §9.
- Rebuild: full rebuild is a single deterministic pass over `assets`; safe
  to run at any time, idempotent.
- Permissible staleness: zero for the DB-index approach; zero is also the
  target for any future in-memory approach (synchronous invalidation, not
  "eventually consistent").
- Prohibited use: never queried for anything resembling an identity
  verdict — it answers "which asset_ids might match this text," full stop;
  the actual candidate is always re-fetched from the authoritative row.
- Source-of-truth relationship: strictly derived; deletable and
  rebuildable with zero data loss, satisfying Law 3's "holdings are
  derived" pattern applied to search.

**Market Intelligence external Search Cache** (per MDP §12, currently
undocumented in code — this design is its first concrete shape):
- Owner: Market Intelligence.
- Key shape: `(normalized_query, classification_filters_hash,
  provider_name)` — scoped per-provider so one slow provider's cache
  entry never gets served under another provider's name.
- Value shape: the raw `List[ProviderObservation]` that provider returned,
  plus `cached_at`.
- TTL: short, per MDP §12's "least trusted, most disposable" — proposed
  default 60 seconds (a human re-searching "AAPL" twice in a minute
  shouldn't re-hit the network; a search cache is not a source of identity
  and does not need price-cache-grade freshness discipline).
- Rebuild: lazy, on next cache-miss request — no background warming (a
  search cache trades a little latency for a lot of avoided provider load;
  warming would defeat that trade).
- Permissible staleness: up to the TTL — acceptable because nothing
  downstream treats a cached discovery result as identity-authoritative.
- Prohibited use: never consulted by `merge.py`'s Registry-mapping check
  (that check always runs fresh against `identity_resolver.resolve()`,
  cache or no cache — mirroring MARKET_DATA_PLATFORM.md §12's explicit
  "resolution always goes through the Resolver and Registry, cached or
  not").
- Source-of-truth: none — explicitly the least-trusted tier of the
  existing cache doctrine (§12's own ranking of its six cache kinds).
- Privacy/security: cache keys are hashed normalized query text, not raw
  user input, to bound key-space growth from adversarial input (§17);
  values contain no caller-identifying information (search is
  caller-anonymous by contract, §4).

**No shared ambiguous cache exists between the two** — they are two
different stores, owned by two different domains, keyed differently, with
different trust levels, exactly per MDP §12's per-cache-kind doctrine.

---

## 15. API Design

```
POST /asset-search
Body: SearchRequest (§4, JSON)
```

- **Method, revised (F7):** the original design specified `GET` with the
  query in the URL, justifying it partly on free HTTP-cacheability — but
  this repo's access logging records full request lines (including query
  strings) at INFO by uvicorn's default, which directly contradicts this
  same document's own rule (§17, §18) that raw query text must not be
  logged above DEBUG. No route-level access-log field-redaction mechanism
  exists anywhere in this repository today (verified: `main.py` configures
  no custom access-log formatter), so "GET with sanitized logging" is not a
  choice this design can verifiably deliver. **Search is now `POST
  /asset-search` with `SearchRequest` as a JSON body** — still read-only,
  still idempotent (idempotency is a property of the operation's effect,
  not the HTTP verb; nothing is created, mutated, or side-effected by
  issuing the same request twice, §8), and it removes raw query text from
  the URL/access-log path entirely. The claimed HTTP-cacheability benefit
  is withdrawn — it was never load-bearing (no cache-control policy was
  actually specified for it) and a `POST` body isn't cached by ordinary
  HTTP infrastructure regardless.
- **Route:** `backend/routers/asset_search.py`, `APIRouter(prefix="/asset-search",
  tags=["asset-search"])`, mounted in `main.py` via
  `app.include_router(asset_search_router)` alongside the existing
  `scheduler_router`/`auth_router` pattern.
- **Request/response schema:** Pydantic models mirroring §4/§5 exactly,
  co-located in `backend/routers/asset_search.py` or a sibling
  `schemas/asset_search.py` if the repo's existing schema-organization
  convention (checked: most routes inline their Pydantic models in
  `main.py` today) is followed — inline in the router module for
  consistency with current practice.
- **Authentication/authorization, corrected (F8):** the original text said
  this route "inherits whatever auth dependency already gates other read
  endpoints... the existing `auth_router` pattern," implying a per-route
  `Depends`. Repository verification shows this is inaccurate: `main.py`
  enforces authentication via a single **global HTTP middleware**
  (`@app.middleware("http") async def auth_middleware`) that calls
  `auth.verify_token(token) -> bool` against one shared/static token — there
  is no per-user identity anywhere in the request context, and no separate
  `auth_router`-style per-route dependency exists. The practical effect the
  original text relied on is still correct (any new route is automatically
  covered by the global middleware, no additional wiring needed) — only the
  described mechanism was wrong, now corrected. Search reveals only
  catalog/discovery facts, no portfolio-scoped data, so no additional
  authorization beyond passing the existing middleware is needed, consistent
  with M37-WP1 §11's workspace-independence.
- **Rate limiting, corrected (F8):** the original "30 UNIVERSE
  requests/minute/**authenticated-user**" bound cannot be built as
  specified — there is no per-user identity to key on (see above), and no
  rate-limiting library or middleware (`slowapi` or equivalent) exists
  anywhere in this repository today. Revised: a **per-process, in-memory
  token-bucket limiter** keyed on the single shared auth token (the only
  caller-distinguishing value the current auth model provides), bound to
  30 UNIVERSE-scope requests/minute globally per application instance, `429`
  on breach with `Retry-After`. **Explicit multi-instance behavior:** this
  bound is per-instance, not global-fleet-wide — if the app is horizontally
  scaled, the effective ceiling is `30 * instance_count`/minute; this is
  disclosed here as a known, accepted v1 limitation (consistent with this
  document's practice of stating bounded, verifiable behavior rather than
  an aspirational one) rather than silently implying a distributed limiter
  exists. A distributed limiter (shared Redis-backed bucket) is a
  reopenable future decision if fleet-wide enforcement becomes necessary,
  not built here since no shared-state infrastructure for it currently
  exists in the repo. CATALOG scope remains unlimited beyond the existing
  global `limit` clamp (§4) — it is a bounded local DB query, not an
  amplification surface.
- **Timeout policy:** server-side hard ceiling of 5000ms regardless of
  caller-supplied `timeout_ms` (§4 already clamps caller input to this
  range) — the server never waits longer than this even if a caller asks.
- **Idempotency:** natural (no side effects anywhere in the lifecycle, §8)
  — no idempotency key needed; `POST` does not change this, since
  idempotency here is a property of the request having no persisted effect,
  not of the HTTP verb.
- **Validation:** delegated to Pydantic + the explicit rules in §4;
  FastAPI's automatic 422 is intentionally overridden to the more specific
  `400` codes in §4/§13 via a custom exception handler, so error codes are
  meaningful rather than generic schema-validation noise.
- **Pagination/cursor policy (F9, new):** cursor semantics differ by scope,
  specified explicitly rather than left for an implementer to infer:
  - **CATALOG scope:** `cursor` is a deterministic, opaque, base64-encoded
    continuation token encoding the last-seen `(rank_tier, canonical_symbol)`
    pair from §12's deterministic ordering — stable because catalog
    ordering is fully deterministic and re-derivable from the same inputs.
    A cursor from one request is valid for a later request only if
    `query`/`scope`/`classification_filters` are identical; otherwise it
    decodes to `400 INVALID_CURSOR` (the position it encodes no longer
    corresponds to a defined ordering).
  - **UNIVERSE scope:** pagination is **not supported in v1**. A request
    with `scope=UNIVERSE` and a non-null `cursor` returns `400
    CURSOR_NOT_SUPPORTED_FOR_SCOPE`. Rationale: discovery results are live,
    non-repeatable provider responses with no snapshot mechanism in this
    design (§14 explicitly does not cache-for-replay); a second "page" would
    either silently re-run the entire fan-out (wasteful, and not actually a
    continuation) or require inventing per-provider continuation tokens
    `ProviderObservation` has no field for. `cursor_next` is always `null`
    for `scope_used=UNIVERSE` responses. This is disclosed as a scoped v1
    limitation, not silently unimplemented.
- **Error mapping:** per the table in §13.
- **Versioning:** none introduced for v1 — the route is new, so there is
  nothing to version yet; if the contract needs a breaking change later, a
  new path segment (`/asset-search/v2`) is the repo-consistent approach
  (no existing versioning scheme was found in `main.py` to conform to
  instead).
- **One public search seat:** this is the only asset-search endpoint;
  §20's migration plan explicitly retires the informal symbol-typing paths
  in `TransactionModal`/`IdeaIntakeCard` rather than leaving a second route.

---

## 16. Frontend Integration Design

- **Shared client:** `frontend/lib/assetSearch.ts`, sibling to `api.ts`,
  exposing one function `searchAssets(request: SearchRequest):
  Promise<SearchResponse>` — the *only* place in the frontend that ever
  calls `/asset-search`.
- **Shared component:** `frontend/components/asset-search/AssetSearchInput.tsx`
  — a single reusable input + result-list component, parameterized by
  `scope` and `classification_filters`, used by every consumer surface.
  This directly satisfies R7/M36.1's "one mechanism" precedent the
  architecture invokes.
- **Debouncing:** 250ms debounce on keystroke before calling
  `searchAssets`, standard for autocomplete-shaped UI, applied inside
  `AssetSearchInput.tsx` so no consumer re-implements it.
- **Cancellation / stale-response prevention:** each keystroke-triggered
  request carries an incrementing local sequence number; a response is
  applied to UI state only if its sequence number is still the latest
  issued (the standard "ignore stale async response" pattern) — combined
  with `AbortController` to actually cancel the in-flight HTTP request,
  which also lets the backend's cancellation handling (§8 stage 5, §13) take
  effect end-to-end.
- **Loading/empty/error/degraded states:** four distinct, explicitly
  designed UI states — `loading` (debounce elapsed, request in flight),
  `empty` (`candidates: []`, not degraded — "nothing matches," stated
  plainly), `error` (request itself failed — `400`/`503`/`500`), `degraded`
  (`200` with `degraded: true` — results shown, plus a visible, dismissible
  "some sources were unavailable" notice built from `degradation` entries,
  never silently hidden).
- **Registered vs. discovery presentation:** visually distinct rendering —
  a registered result shows `display_symbol` + a "tracked" affordance;
  a discovery result shows `reported_symbol` + `provider_name` as a small
  provenance label + a "not yet in your catalog" affordance — so a user
  can never mistake one kind for the other, mirroring §6's wire-level
  discriminant.
- **Selection/handoff behavior:** selecting a `RegisteredCandidate` resolves
  immediately to `{asset_id, canonical_symbol}` for the consumer (a lookup,
  §10.1 of M37-WP1 — no additional network call needed since the candidate
  already carries the reference); selecting a `DiscoveryCandidate` invokes
  the existing claim-submission path (out of scope for this component —
  it hands the claim payload to whatever surface-specific flow already
  exists for resolution/registration, per M37-WP1 §14 stage 8). The
  component itself performs neither a portfolio mutation nor a Current
  Selection change — it only emits `onSelect(candidate)` to its caller.
- **Accessibility:** standard combobox ARIA pattern
  (`role="combobox"`, `aria-expanded`, `aria-activedescendant`,
  keyboard up/down/enter/escape) — called out explicitly rather than left
  implicit, since it's a new shared primitive many surfaces will depend on.
- **Mobile behavior:** debounce increased to 350ms on touch input (network
  variability), result list capped to a scrollable max-height rather than
  full-page takeover, consistent with existing modal patterns in this
  codebase (`TransactionModal` is already a constrained-height modal).
- **Prevention of direct provider calls:** enforced structurally — no
  frontend code imports or constructs a provider URL anywhere; the only
  network call this component ever makes is to `/asset-search`.
- **Migration of `TransactionModal` and `IdeaIntakeCard`:** staged, not
  big-bang (§20). **Scope policy for `TransactionModal` (F2 — this
  document's original text asserted CATALOG and UNIVERSE in the same
  sentence; that contradiction is resolved here as a single staged
  policy):**
  - **Stage 2 (§20):** `TransactionModal`'s free-text `symbolInput` field is
    replaced by `AssetSearchInput` in **CATALOG scope only**. Rationale: at
    this stage no discovery-to-transaction handoff path exists yet (that
    path is M37-WP1 §14 stage 8, out of scope for this component per this
    section's own selection-behavior bullet above), so offering UNIVERSE
    results a user cannot actually act on would be a dead end, not a
    feature.
  - **After Stage 3 ships (external discovery + a working claim
    handoff/registration flow, §20):** `TransactionModal` **may** be
    explicitly upgraded to UNIVERSE scope, because a first-time buy of a
    genuinely new instrument is a real use case *once* selecting a
    `DiscoveryCandidate` has somewhere real to go. This upgrade is a
    deliberate, separately reviewed change to WP8's acceptance criteria
    (§21) — never an automatic or silent widening, consistent with §4's
    "no silent scope broadening" rule applied to product behavior, not just
    the wire contract.
  - **In both stages:** a `DiscoveryCandidate` may never directly create a
    transaction. Selecting one always routes through the existing
    registration/resolution handoff (M37-WP1 §14 stage 8) before a
    transaction can reference the resulting `asset_id` — `TransactionModal`
    itself performs no minting, merging, or direct discovery-to-transaction
    shortcut.

  The `.replace(".BK", "")` display logic is deleted entirely, replaced by
  rendering `display_symbol` as the Registry already provides it.

  **`registry-merge` degradation in the UI (F3):** when a response includes
  a `DegradationEntry(source="registry-merge", candidate_kind_uncertain=true)`,
  the affected `DiscoveryCandidate` results render with a distinct copy
  string — *"standing not yet verified"* — rather than the normal
  *"not yet in your catalog"* affordance, so the UI never implies a
  registered asset was checked and confirmed absent when the check could
  not run at all.

  `IdeaIntakeCard`'s multi-symbol textarea becomes a multi-select built on
  the same `AssetSearchInput` primitive (add up to 10 selected candidates).
  **Paste behavior is preserved, not silently removed (F13):**
  `AssetSearchInput`'s multi-select mode detects a paste event containing
  comma- or newline-separated tokens and splits it into up to 10 individual
  search-and-select operations (one per token, matched against CATALOG
  scope, silently dropping tokens beyond the 10th with a `warnings` entry)
  rather than treating the paste as a single literal query string. This
  keeps `IdeaIntakeCard`'s existing bulk-paste product behavior intact while
  still removing `parseSymbols`'s ad-hoc comma/newline regex parsing itself.

---

## 17. Security and Abuse Resistance

- **Query injection:** all catalog matching goes through SQLAlchemy's
  parameterized query construction (already the codebase's universal
  pattern, e.g. `registry_query.py`'s `db.query(...).filter(...)`) — no
  string-concatenated SQL anywhere in `catalog_search.py`. No shell/OS
  command is ever built from query text (irrelevant here but stated for
  completeness against the review's checklist).
- **Wildcard/pattern injection (F6, corrected):** parameterization alone is
  **not** sufficient — it prevents SQL injection but not `LIKE`-pattern
  injection: an unescaped `%` or `_` in caller-supplied query text becomes
  a wildcard in the constructed pattern, not a literal character, letting a
  short adversarial query (e.g. a bare `%`) force a full-table pattern scan.
  §9 now specifies explicit escaping of `%`, `_`, and the escape character
  before pattern construction; this is the actual, verified defense against
  wildcard-driven broad scans, not an incidental side effect of
  parameterization.
- **Provider abuse amplification:** UNIVERSE-scope rate limiting (§15,
  30/min/application-instance via the per-instance token-bucket limiter,
  F8) exists specifically because one search request can trigger up to
  `MAX_CONCURRENT_PROVIDERS` (8) outbound provider calls — without a cap, a
  scripted burst of searches becomes a provider-hammering amplifier.
- **Denial-of-service / fan-out amplification:** bounded concurrency (§10)
  plus the rate limit together bound worst-case outbound call volume to
  `30 * 8 = 240` provider calls/minute/instance — a concrete, stated number,
  not "parallel calls" left open-ended. Corrected (F8): this bound is
  per-application-instance, not per-authenticated-user (no per-user
  identity exists in the current auth model) and not fleet-wide (a
  horizontally scaled deployment multiplies this ceiling by instance
  count) — both limitations are disclosed in §15 rather than implied away.
- **Excessive result limits:** `limit` clamped server-side to `[1,50]`
  regardless of caller input (§4) — never trusted as a caller-controlled
  unbounded value that could force a large response payload or an
  expensive query.
- **Cache poisoning:** the Search Cache key includes `provider_name` (§14),
  so one provider's response can never be served under another's identity;
  cache values are provider observations only, never merged/adjudicated
  facts, so a poisoned cache entry cannot become a false identity — worst
  case it shows a stale/wrong *discovery* candidate for up to 60 seconds,
  which is exactly the "least trusted, most disposable" tier MDP §12
  already accepts.
- **Sensitive provider errors:** `DegradationEntry.message` is a fixed,
  sanitized string per `reason` code (§5's schema) — raw provider exception
  text/stack traces are logged server-side only (§18), never placed in the
  response body, closing the "sensitive provider errors" and "information
  leakage" checklist items together.
- **Enumeration concerns:** search is intentionally not authorization-scoped
  beyond "authenticated user" (§15) because the catalog is platform-global,
  non-sensitive reference data (M37-WP1 §11) — there is no per-user
  enumeration risk to defend against here that isn't already accepted by
  the architecture itself; this is stated explicitly so a future reviewer
  doesn't flag it as an oversight.
- **Malformed Unicode:** the single, precise length/normalization sequence
  in §4 (F11 — pre-normalization 200-code-point cap, then NFC-normalize,
  then whitespace-collapse, then empty-check) rejects pathological input
  before it reaches any matching logic; the DB layer's native UTF-8
  handling manages the rest.
- **Logging of user-entered search queries:** logged at DEBUG level only,
  with the raw query text — no PII beyond free-text search intent is
  expected in an asset-search query, but query text is still excluded from
  any long-retention analytics store by default (only aggregate metrics —
  §18 — are retained long-term); this is stated as a design constraint on
  whatever logging framework the implementation wires up.
- **Authorization boundaries:** none beyond "authenticated," per the
  enumeration note above — consistent with the architecture's workspace-
  independence.

---

## 18. Observability

- **Metrics, corrected (F14):** `asset_search_requests_total{scope}` (counter);
  `asset_search_latency_ms{scope}` (histogram — p50/p95/p99 are **computed
  from the histogram's buckets by the metrics backend at query time**, not
  emitted as separate label values or separate series, correcting the
  original text's `{scope,p50/p95/p99}` label, which is not how percentile
  metrics work);
  `asset_search_provider_latency_ms{provider}` (histogram);
  `asset_search_provider_failures_total{provider,reason}` (counter);
  `asset_search_degraded_total{scope,reason}` (counter — `reason` label
  added so `UNSUPPORTED`/`UNAVAILABLE`/`TIMEOUT`/`ERROR`/`registry-merge`
  degradations are distinguishable, per F15);
  `asset_search_cache_hit_ratio{provider}` (gauge or computed from hit/miss
  counters);
  `asset_search_catalog_index_fallback_total` (counter, if an index exists).
- **Structured logs:** one log line per request at INFO
  (`{request_id, scope, normalized_query_hash, candidate_count, degraded,
  latency_ms}` — query *hash*, not raw text, at INFO; raw text only at
  DEBUG per §17); one log line per provider failure at WARN/ERROR with
  full (server-side-only) detail.
- **Traces:** one span for the overall request, child spans per stage
  (§8) and per-provider fan-out task, so a slow UNIVERSE search's time
  budget is attributable to a specific stage or provider.
- **Provider-level measurements:** latency and failure-reason breakdown
  per provider (above) — this is the concrete data that would inform the
  deferred provider-quality decisions MARKET_DATA_PLATFORM.md §10 already
  owns; search observability feeds that existing system, it does not
  duplicate it.
- **Cache/index measurements:** hit ratio (Search Cache), fallback-rate
  (catalog index, if built).
- **Degradation measurements:** `asset_search_degraded_total` broken out
  by `reason`, giving a concrete signal for the M37-WP1 §21 weakness-3
  "universe-scope liveness tension" the architecture flagged as worth
  watching.
- **Latency budgets:** CATALOG scope target p95 < 150ms (single DB query);
  UNIVERSE scope target p95 < 2500ms (bounded by the 2000ms per-provider
  default deadline plus merge/rank overhead).
- **Alerting candidates:** `asset_search_degraded_total{scope=UNIVERSE}`
  sustained above a threshold (provider health signal);
  `asset_search_catalog_unavailable` (any occurrence — CATALOG scope
  failing is a Registry-availability incident, not a search incident,
  and should page accordingly).
- **Data that must not be logged:** raw query text above DEBUG level;
  any provider API key/credential (adapters already keep these out of
  `ProviderObservation`, so this is inherited, not newly at risk); full
  provider error bodies at any level below server-side ERROR.
- **No second authority created:** none of the above metrics/logs are ever
  read back by `catalog_search.py`, `merge.py`, or `ranking.py` to influence
  behavior — observability is write-only from the search path's
  perspective, so it can never become a second identity or analytics
  authority (the same discipline Trust & Evaluation's read-only posture
  models, applied here by analogy, not by dependency).

---

## 19. Testing Strategy

Following the existing flat `backend/tests/test_<concern>.py` convention:

- **`test_identity_resolver.py`** (existing file, extended — WP2a, F1) —
  new cases for `resolve(..., record_finding=False)`: zero `RegistryFinding`
  rows created across all five verdicts; full existing suite re-run
  unmodified as a backward-compatibility proof that the default
  (`record_finding=True`) still records findings exactly as before.
- **`test_asset_search_catalog.py`** (unit) — symbol/identifier matching,
  deterministic tier ordering (tier 5 removed, F5), empty-query rejection,
  graceful degrade when `AssetDescriptiveName`/`Asset.name` is not yet
  migrated (pre-WP1 compatibility, F4), name-tier matching once WP1 ships,
  wildcard-only and mixed-wildcard query cases confirming literal (not
  pattern) matching (F6).
- **`test_asset_search_discovery.py`** (unit, provider-adapter-style mocks
  matching `test_provider_adapter.py`'s existing pattern) — capability
  gating, per-provider isolation, timeout/cancellation behavior.
- **`test_asset_search_merge.py`** (unit) — every verdict from
  `identity_resolver.resolve(db, claim, record_finding=False)`
  (`RESOLVED`/`CANDIDATE`/`AMBIGUOUS`/`CONFLICT`/`UNKNOWN`) mapped to the
  correct merge outcome (mirrors `test_identity_resolver.py`'s existing
  verdict-coverage style); **explicit test asserting zero `RegistryFinding`
  rows are created by any `merge.py` call, across all five verdicts (F1 —
  the load-bearing regression this remediation exists to prevent)**; a test
  asserting `resolve()` raising produces a `DegradationEntry(source=
  "registry-merge", reason=ERROR, candidate_kind_uncertain=true)` and keeps
  the candidate as `DISCOVERY` (F3); explicit test asserting no
  string-similarity import exists in `merge.py` (import-inspection test);
  a conformance test grepping `merge.py` for the literal
  `record_finding=False` call shape.
- **`test_asset_search_ranking.py`** (unit, property-style) — for any
  candidate set, output is a total order over the four remaining tiers
  (F5); tier precedence holds under randomized input ordering
  (property/invariant test: shuffling input never changes output); a
  non-matching query with satisfied filters returns zero candidates (F5
  regression test).
- **`test_asset_search_service.py`** (contract) — full `SearchRequest` →
  `SearchResponse` lifecycle against the schemas in §4/§5, including the
  clamping/validation rules and the F11 length/normalization order;
  repeated identical `POST` requests produce unchanged `Asset`/
  `RegistryFinding` row counts (idempotency proof, replacing the
  GET-implies-idempotent assumption, F7); `cursor` + `scope=UNIVERSE` →
  `400 CURSOR_NOT_SUPPORTED_FOR_SCOPE` (F9); CATALOG cursor round-trip and
  cross-request-mismatch → `400 INVALID_CURSOR` (F9).
- **`test_asset_search_failure_modes.py`** — one test per row of §13's
  table (catalog down for CATALOG scope, catalog down for UNIVERSE scope
  including the paired `registry-merge` entry per F3, zero
  capability-eligible providers → `UNSUPPORTED` vs. all-eligible-providers-
  fail → `UNAVAILABLE`, F15, provider timeout, provider error, registry
  merge-check unavailable, cancellation).
- **`test_asset_search_cache.py`** — Search Cache TTL expiry, per-provider
  key isolation, confirms merge stage bypasses cache for Registry-mapping
  checks.
- **`test_asset_search_security.py`** — oversized (>200 code points,
  pre-normalization) and malformed-Unicode query rejection in the exact
  F11 order; wildcard-only (`%`, `_`, `%%%`) and mixed-wildcard query
  fixtures asserting literal, non-scanning matches (F6); `limit` clamping;
  rate-limit breach → `429` against the per-instance token-bucket limiter
  (F8), including a test documenting the accepted per-instance (not
  fleet-wide) limitation.
- **`test_asset_search_frontend.tsx`** (frontend, colocated per existing
  `.test.ts` convention seen in `frontend/lib/*.test.ts`) — debounce,
  stale-response discarding via sequence numbers, degraded-state rendering.
- **`test_asset_search_conformance.py`** (architecture-conformance,
  import-graph inspection) — asserts: `catalog_search.py` never imports
  `discovery_search.py` or any `ProviderAdapter`; `discovery_search.py`
  never imports `models.asset` for writes; no module under
  `services/asset_search/` imports `identity_resolver.adjudicate` (only
  `resolve`); no module imports a string-similarity library; `merge.py`'s
  only call to `resolve()` uses the literal `record_finding=False` keyword
  (F1, grep-verifiable).
- **Explicit invariants asserted across the suite** (each with its own
  test, not just incidental coverage): no asset minting occurs anywhere in
  the search path (assert `Asset` row count unchanged before/after any
  search call in an integration test); **no `RegistryFinding` row is ever
  created by a search request, regardless of verdict or degradation path
  (F1 — the central regression this remediation closes; asserted at both
  the `merge.py` unit level and the full `search_service.py` integration
  level)**; no string-only identity merge (covered by the conformance
  test's import check plus a merge-unit-test fixture where two candidates
  share a name but no identifier — asserted to remain unmerged); CATALOG
  scope never calls a provider (assert zero adapter invocations via a mock
  spy in an integration test); UNIVERSE scope discloses degradation
  whenever any provider fails, and separately whenever the merge check
  fails (parametrized over every `DegradationEntry.reason` × `source`
  combination, F3/F15); discovery candidates remain non-canonical
  (schema-level test: `DiscoveryCandidate` has no `asset_id` attribute at
  all, not just a null one); caches never become identity authorities
  (test that clearing the Search Cache entirely changes zero
  `RegisteredCandidate` output, since catalog reads never consult it).
- **End-to-end:** one Playwright/equivalent flow (matching whatever E2E
  tooling, if any, already exists in `frontend/` — none was found in this
  inspection, so this item is flagged: if no E2E harness exists, this
  becomes a manual verification step in the rollout plan, §20, rather than
  an assumed automated gate).

---

## 20. Migration and Adoption Plan

Staged, matching the M36→M36.1 frozen precedent this document is bound to reuse:

1. **Stage 0 — Schema addition.** Add `AssetDescriptiveName` and the derived
   `Asset.name` column (§9, F4, WP1) as a standalone, reversible migration.
   No behavior changes; existing code paths untouched. Independently, land
   WP2a's `resolve(record_finding=...)` parameter (§3/§11, F1) — also a
   standalone, reversible, backward-compatible change.
2. **Stage 1 — Shared contract + backend door, CATALOG only.** Ship
   `catalog_search.py`, `search_service.py` (CATALOG path only),
   `routers/asset_search.py`, behind a feature flag (repo's existing
   settings/flag mechanism, e.g. alongside `/settings/*` endpoints already
   present in `main.py`). No frontend consumer yet — verified via the test
   suite (§19) and manual API calls only.
3. **Stage 2 — Frontend shared client + component, CATALOG only.** Ship
   `lib/assetSearch.ts` and `AssetSearchInput.tsx`; adopt in **one** low-risk
   surface first (`TransactionModal`'s buy-flow symbol entry, **CATALOG
   scope only** — F2; UNIVERSE scope is explicitly deferred to a
   post-Stage-3 decision, not adopted here) behind the same flag. Verify in
   a real browser session before wider rollout (per this repo's stated
   UI-verification practice).
4. **Stage 3 — External discovery path.** Requires at least one
   `ProviderAdapter` to implement the new `search()` method and flip
   `supports_search=True` — this is new adapter work, scoped as its own
   work package (§21), not bundled into the door's own rollout. UNIVERSE
   scope remains catalog-only-degraded (§10) until this ships, which is
   safe and disclosed by construction.
5. **Stage 3a (new, F2) — `TransactionModal` UNIVERSE upgrade (optional,
   separately reviewed).** Only after Stage 3 ships *and* a working
   discovery-candidate registration/resolution handoff exists (M37-WP1 §14
   stage 8), `TransactionModal` may be explicitly upgraded to UNIVERSE
   scope. This is its own reviewed change (updated WP8 acceptance
   criteria, §21), never an automatic consequence of Stage 3 shipping.
6. **Stage 4 — Second surface migration.** `IdeaIntakeCard`, replacing
   `parseSymbols` with the shared multi-select component (paste-splitting
   behavior preserved, F13, §16).
7. **Stage 5 — Freeze enforcement.** Per the Final Approval's Finding 4
   condition: from this stage on, no new ad-hoc symbol-entry code may be
   added anywhere in the frontend; enforced procedurally via code review
   checklist (an automated lint rule is possible but out of scope for this
   design — flagged as a deferred tooling decision, §22).
8. **Stage 6 — Conformance sweep.** Audit remaining surfaces (any found
   beyond the two identified here) and migrate them onto
   `AssetSearchInput`.
9. **Stage 7 — Removal of obsolete paths.** Delete `TransactionModal`'s
   dead `symbolInput`/`.replace(".BK", "")` code and `IdeaIntakeCard`'s
   `parseSymbols` once their replacements are verified in production for
   an agreed bake period.
10. **Rollback:** each stage is independently revertible via its feature
   flag (backend stages) or a component-level revert (frontend stages) —
   no stage depends on an irreversible migration except Stage 0, which is
   purely additive (`nullable=True` column) and trivially reversible by a
   down-migration that drops the column, with zero data-loss risk since
   nothing reads or writes it before Stage 0 ships.

No stage requires any other stage to be "in flight" simultaneously — the
design can pause safely after any stage.

---

## 21. Implementation Work Packages

**WP1 — Schema: `AssetDescriptiveName` + governed `Asset.name` (F4, revised)**
- Objective: add the evidence-tier `AssetDescriptiveName` table, its
  selection rule, and the derived `Asset.name` convenience column per §9.
- Files: `backend/models/asset.py`, a new Alembic migration.
- Dependencies: none.
- Deliverables: migration (new table + new column), model fields, the
  current-row-promotion logic (mint-time population; later provider
  observations recorded as non-current rows, never auto-overwriting),
  backfill script (best-effort, from any available provider evidence —
  explicitly best-effort, not a blocking guarantee).
- Acceptance criteria: migration applies cleanly on both SQLite and
  Postgres (per `database.py`'s dual-engine reality); existing tests
  (`test_asset_registry.py` etc.) pass unmodified; a test asserting a
  conflicting provider name never overwrites the current row without
  explicit promotion.
- Tests: migration up/down test; backfill idempotency test; current-row
  promotion/conflict test.
- Exclusions: no search logic in this package. Name search itself remains
  blocked until this package ships (§9) — WP2 does not depend on it.

**WP2 — Catalog search service**
- Objective: `catalog_search.py` implementing §9 (symbol/identifier
  matching in full; name matching gracefully absent until WP1 ships,
  disclosed via `warnings` per §9).
- Files: new `backend/services/asset_search/catalog_search.py`.
- Dependencies: none (F4 — decoupled from WP1; name-tier matching is added
  once WP1 ships but does not gate this package's initial delivery).
- Deliverables: the module, matching §9's field/ordering rules.
- Acceptance criteria: `test_asset_search_catalog.py` passes; conformance
  test confirms no provider import.
- Tests: `test_asset_search_catalog.py`.
- Exclusions: no ranking (that's a cross-source concern, §12), no HTTP layer.

**WP2a (new, F1) — `identity_resolver.resolve()` non-recording mode**
- Objective: add the `record_finding: bool = True` keyword parameter to
  `resolve()` per §3/§11, defaulting to today's exact behavior.
- Files: `backend/services/identity_resolver.py` (the one existing
  implementation — no new module).
- Dependencies: none.
- Deliverables: the parameter, guarding the existing `_record_finding` call
  only.
- Acceptance criteria: `test_identity_resolver.py`'s full existing suite
  passes unmodified (backward-compatibility proof — every existing call
  site still records findings by default); new tests prove
  `record_finding=False` creates zero `RegistryFinding` rows across
  `AMBIGUOUS`/`CONFLICT`/`RESOLVED`/`CANDIDATE`/`UNKNOWN` verdicts.
- Tests: additions to `test_identity_resolver.py`.
- Exclusions: no change to `adjudicate()`; no new resolver module.

**WP3 — Merge/dedup stage**
- Objective: `merge.py` wrapping `identity_resolver.resolve(db, claim,
  record_finding=False)` per §11, including F3's merge-unavailability
  degradation disclosure.
- Files: new `backend/services/asset_search/merge.py`.
- Dependencies: WP2 (needs `RegisteredCandidate` shape to compare against),
  WP2a (needs the non-recording mode to exist before it can be called).
- Deliverables: the module.
- Acceptance criteria: `test_asset_search_merge.py` passes, covering all
  five `ResolutionVerdict` values (`RESOLVED`/`CANDIDATE`/`AMBIGUOUS`/
  `CONFLICT`/`UNKNOWN`) plus the `resolve()`-raises path producing a
  `DegradationEntry(source="registry-merge")`; a test asserting zero
  `RegistryFinding` rows are created by any `merge.py` call, across all
  five verdicts.
- Tests: `test_asset_search_merge.py`.
- Exclusions: no adjudication calls (`adjudicate()` is out of scope —
  search never adjudicates).

**WP4 — Ranking stage**
- Objective: `ranking.py` per §12.
- Files: new `backend/services/asset_search/ranking.py`.
- Dependencies: none (pure function of candidate lists).
- Deliverables: the module.
- Acceptance criteria: `test_asset_search_ranking.py` passes, including the
  shuffled-input property test.
- Tests: `test_asset_search_ranking.py`.
- Exclusions: no tokenization/fuzzy-matching algorithm (deferred, §22).

**WP5 — Orchestration + CATALOG-only API**
- Objective: `search_service.py` (CATALOG path), `routers/asset_search.py`,
  mounted behind a feature flag.
- Files: new `backend/services/asset_search/search_service.py`,
  `backend/routers/asset_search.py`, edit to `backend/main.py` (router
  mount only).
- Dependencies: WP2, WP4 (F12 — WP3/merge removed: this package's CATALOG-only
  delivery never invokes `merge.py`, since UNIVERSE-scope dedup is not part
  of its exclusions; the original dependency was incorrect).
- Deliverables: working `/asset-search?scope=CATALOG` endpoint.
- Acceptance criteria: `test_asset_search_service.py` and
  `test_asset_search_failure_modes.py` (catalog-relevant rows) pass;
  manual `curl` verification against a running instance.
- Tests: as above, plus `test_asset_search_conformance.py`.
- Exclusions: UNIVERSE scope returns `degraded: true, discovery-empty`
  honestly (§10's zero-eligible-provider behavior) rather than being
  blocked — this package does not need to wait for WP6.

**WP6 — External discovery + Search Cache**
- Objective: `discovery_search.py`, `cache.py`, at least one adapter's
  `search()` method (proposed: extend `YahooFinanceAdapter` first, since it
  is the only adapter currently in the repository).
- Files: new `backend/services/asset_search/discovery_search.py`,
  `cache.py`; edit `backend/services/provider_adapter.py` (add abstract
  `search()` method — additive, does not change `normalize()`'s contract)
  and `backend/services/provider_domain.py` if a new
  `ProviderSearchResult`-shaped shim is needed beyond reusing
  `ProviderObservation`; flip `YahooFinanceAdapter.capabilities.
  supports_search` to `True` once its `search()` is implemented and tested.
- Dependencies: WP2, WP3 (merge needs discovery candidates to merge against;
  WP3 itself depends on WP2a).
- Deliverables: working UNIVERSE scope.
- Acceptance criteria: `test_asset_search_discovery.py`,
  `test_asset_search_cache.py` pass; full `test_asset_search_failure_modes.py`
  suite passes (all rows now exercisable).
- Tests: as above.
- Exclusions: no second provider's adapter in this package — one adapter
  proves the pattern; more providers are pure repetition of WP6's shape,
  not a new decision.

**WP7 — Frontend shared client + component**
- Objective: `lib/assetSearch.ts`, `AssetSearchInput.tsx`.
- Files: new `frontend/lib/assetSearch.ts`,
  `frontend/components/asset-search/AssetSearchInput.tsx` (+ styles/tests).
- Dependencies: WP5 (needs a live CATALOG-scope endpoint to integrate against).
- Deliverables: the client + component, unadopted by any page yet.
- Acceptance criteria: `test_asset_search_frontend.tsx` passes; manual
  browser verification of debounce/cancel/degraded states against a
  running backend (per this repo's stated UI-testing practice).
- Tests: `test_asset_search_frontend.tsx`.
- Exclusions: no migration of existing components yet.

**WP8 — TransactionModal migration**
- Objective: replace `symbolInput`/`.BK`-stripping logic with
  `AssetSearchInput`, **CATALOG scope only** (F2).
- Files: `frontend/components/TransactionModal.tsx`.
- Dependencies: WP7.
- Deliverables: updated component, feature-flagged, CATALOG scope.
- Acceptance criteria: manual verification of buy/sell/initial-position
  flows in a browser; existing transaction-modal tests (if any) updated;
  confirms no UNIVERSE-scope call is made from this component at this
  stage.
- Exclusions: no changes to transaction submission logic itself; no
  UNIVERSE scope (deferred to WP8a).

**WP8a (new, F2) — TransactionModal UNIVERSE upgrade (optional, gated)**
- Objective: upgrade `TransactionModal` to UNIVERSE scope once a genuine
  discovery-candidate handoff exists.
- Files: `frontend/components/TransactionModal.tsx`.
- Dependencies: WP6 (external discovery), and the discovery-candidate
  registration/resolution handoff (M37-WP1 §14 stage 8 — external to this
  document's work packages, tracked by whichever milestone implements it).
- Deliverables: updated component scope, with a working, tested path from
  selecting a `DiscoveryCandidate` to a resolved `asset_id` before any
  transaction can reference it.
- Acceptance criteria: a `DiscoveryCandidate` selection cannot itself create
  a transaction — verified by a test asserting the handoff path is invoked,
  not bypassed; manual verification of the full new-instrument buy flow.
- Exclusions: none of WP1-WP7's scope is reopened.

**WP9 — IdeaIntakeCard migration**
- Objective: replace `parseSymbols` textarea with multi-select
  `AssetSearchInput`.
- Files: `frontend/components/operations-center/idea-intake/IdeaIntakeCard.tsx`.
- Dependencies: WP7.
- Deliverables: updated component.
- Acceptance criteria: manual verification against `reviewIdeas` API call
  (unchanged downstream contract — only the input mechanism changes).
- Exclusions: no change to `reviewIdeas`/idea-review backend logic.

**WP10 — Conformance sweep and cleanup**
- Objective: audit remaining ad-hoc surfaces; remove dead code from WP8/WP9.
- Files: TBD by audit.
- Dependencies: WP8, WP9 baked for an agreed period.
- Deliverables: sweep report; cleanup PR.
- Acceptance criteria: no remaining free-text ticker input outside
  `AssetSearchInput` in the frontend codebase (grep-verifiable).

**Ordering:** WP1, WP2, WP2a, WP4 have no cross-dependency and can proceed in
parallel; WP3 depends only on WP2a (not WP1). WP5 depends on WP2 and WP4
only (F12) and does not wait for WP1, WP2a, or WP3 — a CATALOG-only endpoint
can ship the moment WP2/WP4 are ready, with name-tier matching and UNIVERSE
scope arriving later without re-opening WP5. WP6 depends on WP2 and WP3
(hence transitively WP2a) and is independent of WP7-10 and can proceed in
parallel with them once WP5 ships. WP8/WP9 both depend only on WP7 and can
proceed in parallel. WP10 is last.

---

## 22. Deferred Decisions

1. **Ranking algorithm internals beyond tier ordering** (exact tokenization
   for name prefix/substring matching, especially Thai-script matching).
   Why deferred: M37-WP1 §18 item 1 already deferred this at the
   architecture level; this design only had to define the *tiers*, not the
   string-matching internals within a tier. Evidence missing: real query
   volume/patterns don't exist yet (no search feature has shipped). Owner:
   implementation team at Stage 2+ of rollout, informed by WP2's initial
   substring-match usage data. Reopen trigger: user complaints about
   Thai-name search quality, or measured low click-through on name-tier
   results.
2. **Whether a persisted catalog index is needed at all** (§9, §14). Why
   deferred: current catalog size is unknown to this design (not measured
   during inspection) and a plain indexed column may be entirely sufficient.
   Evidence missing: query latency measurements from WP2 in production.
   Owner: Asset Foundation implementation, informed by
   `asset_search_catalog_index_fallback_total`-style metrics (§18) once
   real load exists. Reopen trigger: CATALOG-scope p95 latency exceeding
   the 150ms budget (§18) under real usage.
3. **Discovery-to-discovery merging** (§11) — whether two providers'
   unregistered results for "the same" instrument should ever be
   presented as one candidate. Why deferred: doing so requires a policy
   decision the frozen architecture didn't make (R4's mapping-only rule
   covers discovery-to-*registered*, not discovery-to-discovery), and no
   second provider adapter exists yet to even produce the scenario. Owner:
   Market Intelligence, at the point a second search-capable provider
   adapter ships (WP6+1). Reopen trigger: a second adapter's rollout.
4. **Automated lint enforcement of the Stage 5 freeze** (§20) — whether a
   custom ESLint rule should mechanically block new raw ticker `<input>`
   elements outside `AssetSearchInput`. Why deferred: this is tooling
   investment that only pays off once the freeze is actually in force
   (Stage 5); premature before Stages 1-4 land. Owner: whoever executes
   Stage 5. Reopen trigger: a third ad-hoc surface appearing despite the
   procedural freeze (evidence the procedural approach alone is
   insufficient).
5. **A second provider adapter's search implementation.** Why deferred:
   WP6 deliberately proves the pattern with one adapter; a second is
   repetition, not a new design decision, and no second provider is
   currently integrated in this repository at all. Owner: whoever
   integrates the next provider. Reopen trigger: a new provider
   integration milestone.

Not deferred, deliberately: identity/ownership questions (all resolved in
§3), the merge authority (§11, resolved as `identity_resolver.resolve()`),
cache ownership (§14, resolved per-domain), and the public contract shape
(§4/§5, fully specified) — these are foundational and this document commits
to them now, per its own instruction not to defer ownership questions.

---

## 23. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Shadow registry (catalog index accretes independent authority) | Low | High | Index is Asset-Foundation-owned, same-Session reads only, never holds candidate payloads — only `asset_id` references (§14); conformance test (§19) can be extended to check no second table stores name/symbol data outside `assets`/`asset_identifiers` |
| Provider coupling (a provider quirk leaks into the canonical contract) | Low | Medium | `DiscoveryCandidate` is structurally provenance-tagged evidence only; `ProviderObservation` reuse (§10) means no new provider-shaped field is invented |
| Uncontrolled fan-out | Medium (until WP6's bounds are implemented) | Medium | Concrete numeric bounds stated (§10, §15, §17): 8 concurrent providers, 30 UNIVERSE requests/min/application-instance (F8 — corrected from "/user," since no per-user identity exists), 240 provider-calls/min/instance worst case; explicitly disclosed as per-instance, not fleet-wide (§15) |
| Ambiguous candidate identity (a Discovery Candidate treated as registered somewhere downstream) | Low | High | `asset_id` structurally absent (not nullable) from `DiscoveryCandidate` (§6); schema-level test enforces this |
| Duplicate search seats (a second ad-hoc entry point appears) | Medium (two already exist pre-remediation) | Medium | Stage 5 freeze (§20) plus WP10 conformance sweep; flagged as the architecture's own R7, now with a concrete enforcement stage |
| Ranking scope creep (a future PR adds a "relevance score" from an analytics source) | Medium (a natural-feeling feature request over time) | High (crosses judgment/arithmetic boundary) | `ranking.py`'s function signature has no parameter through which such a score could even be threaded (§12) — a future PR would have to visibly change the function signature, making the violation reviewable rather than silent |
| Cache drift (Search Cache serving stale/wrong-provider data) | Low | Low | Per-provider-keyed, 60s TTL, explicitly least-trusted tier (§14), never consulted by merge's identity check |
| Frontend bypass (a page calls `/asset-search` directly instead of through `lib/assetSearch.ts`, or worse, calls a provider directly) | Medium (until Stage 5 freeze is enforced) | Medium | Code-review checklist item at Stage 5; §22 item 4 flags automated lint enforcement as a reopenable future decision if procedural enforcement proves insufficient |
| Provider result instability (a provider changes its response shape) | Medium | Low | Isolated to that provider's `normalize()`-equivalent `search()` method (§10); failure is per-provider-isolated (§10, §13), never cascades |
| Migration incompleteness (WP10's sweep misses a surface) | Medium | Low | Explicitly staged as its own work package (§21) with a grep-verifiable acceptance criterion, not left to informal memory |

---

## 24. Architecture Conformance Matrix

| Governing rule | Technical mechanism | Verification method | Work package |
|---|---|---|---|
| M37-WP1 S1 (search presents owned facts only) | `RegisteredCandidate`/`DiscoveryCandidate` fields sourced only from `assets`/`asset_identifiers`/`ProviderObservation` — no derived/computed fact invented | Schema review; `test_asset_search_catalog.py`, `test_asset_search_discovery.py` | WP2, WP6 |
| M37-WP1 S2 (search never resolves identity) | `merge.py` calls `identity_resolver.resolve(db, claim, record_finding=False)` only (F1), never `adjudicate()`, and creates zero `RegistryFinding` rows | Conformance test asserting no `adjudicate` import in `services/asset_search/`; unit test asserting zero `RegistryFinding` rows created by `merge.py` across all verdicts | WP2a, WP3, WP5 (`test_asset_search_conformance.py`, §19) |
| M37-WP1 S3 (search never mints) | No module under `services/asset_search/` writes to `assets` | Integration test asserting `Asset` row count unchanged across search calls | WP5 (`test_asset_search_conformance.py`, §19) |
| M37-WP1 S4 (read-only, replayable-in-spirit) | `POST /asset-search` (F7) carries no side effects anywhere in the lifecycle (§8) — idempotency is verified by behavior, not inferred from HTTP verb | `test_asset_search_service.py` asserts `Asset`/`RegistryFinding` row counts unchanged across repeated identical requests | WP5 |
| M37-WP1 S5 (candidates honest about standing) | `kind` discriminant + structural field absence (§6); `registry-merge` degradation disclosure when standing cannot be verified (F3, §5/§11/§13) | Schema-level test; `test_asset_search_failure_modes.py` merge-unavailable case | WP3, WP5 (`test_asset_search_conformance.py`, §19) |
| M37-WP1 S6 (provider independence inherited) | All external reach via existing `ProviderAdapter`/`ProviderCapabilities` (§10); no vendor name/field-mapping logic in `discovery_search.py` | Conformance test; code review | WP6 |
| M37-WP1 S7 (ranking is arithmetic) | `ranking.py`'s closed function signature (§12) | Signature inspection; no personalization/analytics parameter | WP4 |
| M37-WP1 S8 (failure is loud) | `DegradationEntry` taxonomy (§13); never a silently-narrowed empty result | `test_asset_search_failure_modes.py` | WP5, WP6 |
| M37-WP1 §10.2 (no silent scope broadening) | `scope_used` echoes request exactly; CATALOG never imports discovery module | Conformance test | WP5 (`test_asset_search_conformance.py`, §19) |
| M37-WP1 §11 (workspace/Current-Selection independence) | No `workspace_id`/selection parameter anywhere in `SearchRequest` (§4) | Contract schema review | WP5 |
| Remediation Finding 1 (no tenth domain; hosted in Market Intelligence) | Module placement table (§3): all "door" logic lives under Market Intelligence's ownership; Asset Foundation owns only catalog search + its own index | Placement/ownership table cross-check against §9 | WP2-WP6 |
| Remediation Finding 2 ("Lookup" grounded, not asserted) | §16's "selection resolves immediately... a lookup" cites the existing candidate fields already carrying `asset_id`/`canonical_symbol` — no new dereference endpoint invented | Design review | WP7 |
| Remediation Finding 3 (index ownership explicit) | §9/§14: catalog index owned by Asset Foundation; Search Cache owned by Market Intelligence; never shared | Module placement table; conformance test | WP2, WP6 |
| Remediation Finding 4 (R7 freeze) | Stage 5 (§20) explicit freeze + WP10 sweep | Code-review checklist; grep-verifiable acceptance criterion | WP10 |
| R4 (no string-only sameness) | `merge.py` uses only `identity_resolver.resolve(db, claim, record_finding=False)`; conformance test bans similarity-library imports | `test_asset_search_conformance.py` | WP2a, WP3 |
| R1 (shadow registry) | Index rebuild/ownership rules (§9/§14); same-Session read discipline | Conformance test; code review | WP2 |
| R2 (ranking drift to judgment) | Closed ranking input set (§12), enforced by function signature | Signature inspection | WP4 |
| Registry evidence-tier governance (F4) | `AssetDescriptiveName` mirrors `AssetIdentifier`'s source/currentness/history pattern; `Asset.name` is a derived, synchronously-updated convenience column, never written directly by any other path (§9) | Model review; migration test; current-row-promotion/conflict test | WP1 |
| No durable write from a read-only search path (F1) | `resolve(..., record_finding=False)` skips `_record_finding` entirely; `merge.py` never calls the recording default | Unit test asserting zero `RegistryFinding` rows across all verdicts; backward-compatibility test on the default path | WP2a, WP3 |
| Honest disclosure when merge standing is unverifiable (F3) | `DegradationEntry(source="registry-merge", candidate_kind_uncertain=true)`; distinct UI copy for uncertain-standing candidates (§16) | `test_asset_search_failure_modes.py`; frontend copy review | WP3, WP7 |

---

## 25. Self-Review

- **Hidden architecture changes:** none found. The one place this design
  comes closest to touching architecture is proposing `Asset.name` — but
  this is a descriptive/classification fact, a category M37-WP1 §10.3 and
  ASSET_REGISTRY.md §8 already assign to Asset Foundation's stewardship; no
  new identity fact is created, no new authority moves. Flagged explicitly
  rather than silently added.
- **Accidental tenth domain:** checked against the Final Approval's own
  test — does anything in this design own exclusive vocabulary? No:
  `SearchRequest`/`SearchResponse`/`Candidate` are contract shapes owned
  jointly by the two hosting domains per §3's table, not a third party;
  "Search Scope" values (`CATALOG`/`UNIVERSE`) are enum literals of a
  contract, not a vocabulary a service asserts facts through.
- **Ownership gaps:** the one gap found during design (index ownership
  ambiguity) is the exact gap Finding 3 already required resolved — closed
  here concretely (§9, §14) rather than re-opened.
- **Duplicate authority:** none — every module in §3's table has exactly
  one listed owner and the merge stage explicitly reuses rather than
  reimplements `identity_resolver.resolve()`.
- **Upward dependency:** checked module-by-module against §7.1's law —
  `catalog_search.py` (Asset Foundation) depends on nothing above it;
  `discovery_search.py`/`merge.py`/`ranking.py`/`search_service.py`
  (Market Intelligence) depend downward on Asset Foundation and on
  provider adapters, never upward on Experience; `routers/asset_search.py`
  and the frontend client depend downward on the service layer. No cycle.
  Confirmed clean.
- **Provider leakage:** checked specifically because `symbol_resolver.py`'s
  existing dialect-normalization pattern was a live temptation to reuse —
  explicitly rejected in §2.3/§10 in favor of the existing
  `ProviderAdapter.normalize()`/`ProviderObservation` contract, which
  already keeps provider dialect below the waterline.
- **Shadow Registry:** addressed structurally (§9, §14, §23) — the design's
  own conformance test suite (§19) is written to catch a future regression
  here, not just assert good intent today.
- **Implementation overreach:** this document specifies module boundaries,
  contracts, and bounded algorithms but does not write the tokenizer, the
  concrete ORM query text, or the exact Pydantic class bodies — those are
  implementation, correctly left to the work packages (§21). One possible
  overreach: §9's proposal of a specific migration (`Asset.name`) is a
  concrete schema decision; it is included because §5's non-goals
  explicitly reserve "REST endpoints/database schema" as *architecture*
  non-goals, not *technical-design* non-goals — schema is exactly this
  document's level (Platform Architecture §11's level-5), so this is in
  scope, not overreach.
- **Under-specification:** the two items most likely to be challenged are
  (a) whether a persisted catalog index is needed at all (§22 item 2) and
  (b) ranking's exact tokenization (§22 item 1) — both are deferred with
  named owners and concrete reopen triggers rather than left silently
  open, per the instruction not to defer foundational questions while
  correctly deferring genuinely evidence-dependent ones.
- **Unnecessary complexity:** the design deliberately does not build a
  second provider adapter, a persisted index, or discovery-to-discovery
  merging in v1 (§21 WP6 exclusions, §11, §22) — each omission is a named,
  justified deferral, not an oversight, keeping the initial implementation
  surface to exactly what M37-WP1's approved contract requires.

**Honest residual weakness:** this design's correctness for CATALOG scope
is independently verifiable today (WP1, WP2, WP4, WP5 touch only code paths
already present in the repository); its correctness for UNIVERSE scope
cannot be fully validated until WP6 gives at least one real provider a
`search()` implementation to test against — until then, §10's fan-out/
timeout/cancellation design is reasoned from the existing `ProviderAdapter`
contract's shape, not from a working example. This is disclosed rather
than hidden, and is exactly why §20 sequences UNIVERSE scope as its own
independently-revertible stage rather than bundling it with the initial
rollout.

**Remediation self-review (F1-F15, this pass):** the Independent Technical
Design Review's central finding (F1) was a genuine, verified defect: this
document's original text asserted `identity_resolver.resolve()` was safely
reusable "read-only" without checking the function's own behavior on
`AMBIGUOUS`/`CONFLICT` verdicts, where it writes a durable `RegistryFinding`
row. That is exactly the failure mode this document's own review-readiness
claims exist to catch, and it was caught by the *next* stage of governance,
not this one — worth stating plainly rather than minimizing. The fix (a
non-recording parameter on the one existing resolver, WP2a) is proportionate:
it does not fork the resolver, does not add a second implementation, and
does not touch `adjudicate()` or any existing caller's behavior. F3's fix
(disclosing merge-check unavailability) and F4's fix (governing
`Asset.name` through an evidence-tier table matching the schema's existing
pattern) are similarly corrections of *rigor*, not reversals of the
underlying design decisions the Final Approval Board already blessed —
hosting, ownership, candidate-kind split, cache doctrine, and the
no-minting/no-adjudication rules are all unchanged. F2's TransactionModal
contradiction was a drafting error (two claims in one sentence), now
resolved as a single staged policy. F5-F12/F14 were contract-precision and
mechanical-reference defects, each closed with a one-rule choice rather
than a redesign. No finding required reopening M37-WP1's architecture, the
remediation's Market-Intelligence-hosting decision, or the Final Approval's
conditions — consistent with this remediation's own scope constraint.

---

## Final Decision

**READY FOR FINAL TECHNICAL APPROVAL**

This document has been remediated in response to the Independent Technical
Design Review's `PASS WITH REQUIRED REMEDIATION` verdict (F1-F15, all
addressed — see the accompanying Remediation Report for the full
disposition matrix). Every section remains grounded in either the frozen,
approved M37-WP1 architecture (including its Final-Approval remediation
conditions) or direct repository evidence (§2, re-verified during this
remediation pass — `identity_resolver.py`, `registry_findings_repository.py`,
`main.py`'s auth middleware, and the absence of rate-limiting infrastructure
were all re-inspected against the review's specific claims). The one
critical defect (F1 — a search-triggered durable Registry write) is closed
by extending the single existing resolver with a non-recording mode, not by
forking it or building a second one. All architecture-level ownership,
dependency-direction, and shadow-registry concerns raised through M37-WP1's
full governance lifecycle remain mapped to concrete technical mechanisms in
§24, now including three additional rows for the F1/F3/F4 mechanisms. No
architectural contradiction was found or introduced by this remediation;
the deferred items in §22 are unchanged and remain genuinely
evidence-dependent rather than foundational questions being avoided.
