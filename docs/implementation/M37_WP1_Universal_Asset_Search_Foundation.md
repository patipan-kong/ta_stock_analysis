# M37 — WP1: Universal Asset Search Foundation

**Date:** 2026-07-21

**Document class:** Architecture Design Document (architecture milestone)

**Status:** `PROPOSED_FOR_INDEPENDENT_REVIEW`

**Implementation authority:** `NONE` (architecture only; no implementation authorized by this document)

**Runtime authority:** `NONE`

**Governing architecture (frozen, not amended by this document):**
[Platform Architecture](../architecture/platform_architecture.md) (the constitution),
[UNIVERSAL_ASSET_ARCHITECTURE.md](../architecture/UNIVERSAL_ASSET_ARCHITECTURE.md),
[ASSET_REGISTRY.md](../architecture/ASSET_REGISTRY.md),
[MARKET_DATA_PLATFORM.md](../architecture/MARKET_DATA_PLATFORM.md),
[PROVIDER_INTERFACE.md](../architecture/PROVIDER_INTERFACE.md),
[M35-WP1](M35_WP1_Product_Workspace_Foundation.md),
[M36-WP1](M36_WP1_Multiple_Portfolio_Foundation.md),
[M36.1](M36_1_Runtime_Foundation.md).

---

## 1. Executive Summary

Universal Asset Search is the platform's single, canonical way for a human to go
from *a partial description of an asset* to *a canonical reference to an asset*
— across every supported asset class, through every naming system the outside
world uses, without the searcher ever needing to know which provider, market, or
identifier scheme is involved.

The central architectural finding of this milestone is that **the platform's
frozen corpus already owns every concept search needs**:

- The **Asset Foundation domain** already owns "making the catalog of
  everything ownable searchable and discoverable" (Platform Architecture §6.1).
- The **Discovery Layer** already owns the "User Search" door for encountering
  instruments the platform does not yet track (MARKET_DATA_PLATFORM.md §4).
- The **Resolver and Registry** already own the adjudication that turns
  external evidence into permanent identity (ASSET_REGISTRY.md §4,
  MARKET_DATA_PLATFORM.md §5).
- The **Experience Platform** already owns rendering and human intent capture
  (Platform Architecture §6.9).

M37 therefore mints **no new authority and no new domain**. It defines one new
architectural element — the **Universal Asset Search Boundary** — which is a
*composition seam*: a read-only, side-effect-free, provider-independent facade
through which a query fans out to the already-owned candidate sources (the
Registry's catalog; optionally, the Discovery Layer's external universes) and
returns a unified, honestly-labeled candidate list. Selecting a candidate exits
search entirely: a registered candidate becomes an ordinary identity reference;
an unregistered candidate becomes an ordinary discovery claim entering the
existing claim → resolve → register pipeline. Search itself never resolves,
never mints, never ranks by opinion, and never writes anything permanent.

This is deliberately a small architecture. Its value is not invention; it is
the guarantee that when search is implemented, it will have exactly one home,
one contract, and no second copy of anything the platform already owns.

---

## 2. Problem Statement

The platform is becoming multi-asset (Platform Architecture §9, current era).
Every asset class the platform supports — Thai equities, US equities, ETFs,
funds, bonds, cash, property, and classes not yet defined — must be findable by
a human before it can be watched, analyzed, held, or recommended. Today, the
runtime's finding-things surface is fragmentary and equity-shaped:

- Symbol entry points assume the user already knows an exact provider-flavored
  symbol (a `.BK`-suffixed string, a US ticker), which is precisely the
  provider-symbol exposure the frozen identity architecture exists to eliminate
  (ASSET_REGISTRY.md §10: symbols exist only at the resolution boundary and the
  presentation surface).
- There is no single defined answer to "how does a user find a mutual fund, a
  bond, or an asset with no ticker at all?" — even though the asset model,
  registry, and discovery pipeline that could serve those classes are all
  designed and frozen.
- Nothing architecturally prevents each new surface (watchlist, idea intake,
  holdings entry, future dashboards) from growing its *own* asset-finding
  logic, its own provider calls, and its own partial identity opinions — the
  exact multiplication of implementations Law 9 forbids and the exact boundary
  leak Law 10 forbids.

The problem M37 solves is not "the platform lacks a search engine." It is:
**the platform lacks a defined architectural seat for search**, and without
one, search capability will accrete as duplicated, provider-coupled,
identity-opining fragments at every surface that needs it.

---

## 3. Architectural Objectives

1. **One seat.** Define exactly one architectural home for asset search, such
   that every present and future surface that needs to find assets consumes the
   same boundary (Law 9 applied to discovery).
2. **Universal by construction.** The search contract must be expressed in the
   universal asset vocabulary (identity, classification, capabilities —
   UNIVERSAL_ASSET_ARCHITECTURE.md §2, §5, ASSET_REGISTRY.md §8) so that a new
   asset class becomes searchable by *description*, never by extending search
   itself.
3. **Provider independence.** No consumer of search may learn which provider,
   if any, contributed a candidate; provider knowledge stays below the existing
   Provider Interface waterline (Law 10, PROVIDER_INTERFACE.md).
4. **Authority preservation.** Search adds zero authority: identity remains the
   Registry's alone; observation remains Market Intelligence's alone; judgment
   remains Decision Intelligence's alone. Search only *presents* what owners
   already assert.
5. **Read-only, side-effect free.** A search — however many times it is run,
   whatever it returns — changes no recorded state. All permanence is
   downstream, through the existing three gates.
6. **Honest candidates.** A search result never overstates what is known: a
   registered asset and an unregistered external claim are structurally
   distinct kinds of candidate, never blurred into one.
7. **Runtime independence.** The architecture assumes nothing about API style,
   storage, indexing, caching, or frontend framework; it must survive every
   implementation beneath it being replaced.

---

## 4. Scope

In scope for M37 (architecture only):

- The definition, boundaries, responsibilities, and dependencies of the
  **Universal Asset Search Boundary**.
- The canonical distinction between **search, lookup, registry, identity,
  intelligence, and analytics** (§10.1).
- The **search candidate** concept and its two honest kinds (§10.3).
- The **search scope** concept: which universes a search consults (§10.2).
- The **search lifecycle**: what happens from query to candidate to handoff
  (§14), and the identity flow through it (§15).
- The extension mechanisms by which new asset classes, classification
  dimensions, and discovery sources become searchable without modifying search
  (§16).
- Risks, deferred decisions, and dependencies for the future implementation
  milestone(s) (§17–19).

---

## 5. Explicit Non-Goals

M37 does **not** design any of the following. Each is listed with where it
belongs instead, because "not now" must never be read as "nowhere."

| Not designed here | Why, and where it belongs |
| --- | --- |
| Ranking algorithms | Ordering candidates is an implementation concern *bounded* by this document (§10.4: deterministic, explainable, opinion-free). The specific algorithm is an implementation-milestone decision. |
| Recommendation / scoring / "assets you might like" | That is judgment — Decision Intelligence's domain, behind its own constitution. Search presents facts; it never advises (§10.1). |
| Search optimization, full-text indexing, caching strategy | Pure implementation and infrastructure. The architecture requires only that no cache or index ever becomes a second identity mapping (§17, R1). |
| Provider-specific implementations | Owned by adapters under PROVIDER_INTERFACE.md, unchanged. |
| Portfolio Dashboard / Multi-Asset Dashboard | Experience-layer consumers of search, designed in their own milestones; search must not be shaped around any single consumer. |
| AI Evaluation / Intelligence Engine | Trust & Evaluation and Decision Intelligence remain untouched; search is invisible to both. |
| Portfolio analysis / analytics | Knowledge-layer concerns; search returns identity-level facts only (§10.1). |
| UI design | Experience Platform implementation work. |
| REST endpoints / GraphQL / database schema / infrastructure | Level-4/5/6 artifacts (Platform Architecture §11); this is a level-4 architecture document that deliberately does not descend to them. |

---

## 6. Architectural Principles

The constitution's laws apply in full. The following are their specific
projections onto search — restatements, not new law:

- **S1 — Search is presentation of owned facts, never a source of facts.**
  Every field in every candidate is traceable to an owner: identity facts to
  the Registry, descriptive facts to the Registry's classification stewardship,
  external claims to their witnessing adapter with provenance. Search asserts
  nothing of its own.
- **S2 — Search never resolves identity.** Resolution is adjudication and
  belongs to the Resolver/Registry alone (ASSET_REGISTRY.md §4). Search may
  *carry* a claim toward resolution; it never performs it, caches its own
  verdicts, or narrows candidates by guessing.
- **S3 — Search never mints.** No search, and no volume of searches, creates
  an `asset_id`. Minting happens only at the Registry's Verified moment
  (ASSET_REGISTRY.md §6), downstream of an explicit selection and adjudication.
- **S4 — Search is read-only and replayable-in-spirit.** It writes nothing
  permanent. (It is *not* part of any accounting path, so Law 4 determinism
  does not bind it; §10.4 states the weaker, appropriate obligation:
  explainable, deterministic *given the same catalog state and witness
  responses*.)
- **S5 — Candidates are honest about their standing.** Registered vs.
  unregistered is a structural distinction in the candidate model, not a
  display hint. A consumer can never mistake an external claim for a platform
  identity.
- **S6 — Provider independence is inherited, not re-implemented.** Search
  reaches external universes only *through* the existing Discovery Layer and
  Provider Interface. It contains no provider names, no symbol-convention
  logic, no vendor field mappings.
- **S7 — Ranking is arithmetic, never judgment.** Candidate ordering may use
  match quality, identifier strength (the Resolver's existing evidence
  hierarchy is the precedent vocabulary), and classification fit to the query —
  never expected return, model opinion, popularity-as-advice, or any output of
  Decision Intelligence. The judgment/arithmetic boundary applies to ordering.
- **S8 — Failure is loud and partial results are labeled.** If an external
  universe is unreachable, search returns what the catalog knows and says the
  external universe was unavailable (Law 13). It never silently narrows.

---

## 7. Relationship to M29–M36

| Frozen milestone | What it fixed in place | How M37 relates |
| --- | --- | --- |
| M29–M31 (runtime adoption, capability safety, registry cutover) | Asset definitions as code; capability lookups consulted read-only by runtime services; registry read-path | M37 consumes the same capability/classification vocabulary as *searchable description*. No capability semantics change. |
| M32 (cost-aware execution evidence) | Execution evidence foundations | Untouched. Search is upstream of any execution concern and shares no boundary with it. |
| M33 (execution intent, identity, authority) | Governed actions, human authority contracts | Untouched. Searching is not a governed action: it changes no recorded state and grants no authority (the same reasoning M36-WP1 applied to Current Selection). Selecting a search candidate *may lead to* a governed or gated action (registration, transaction), and that action's existing gate governs it — search adds no bypass. |
| M34 (audit protocol) | Audit and decision registers | Untouched; this document is itself subject to that protocol at review time. |
| M35 (Product Workspace) | Workspace Context; context resolvers | Search is **workspace-independent at the identity level**: the asset catalog is platform-global (identity is not workspace-scoped — ASSET_REGISTRY.md; only *portfolio* references are workspace-bound per M36). A workspace provides *where the user came from and what they may do next*, never *what exists*. See §11. |
| M36 / M36.1 (Multiple Portfolio, Current Selection) | Zero-or-one Current Selection, Experience-owned; canonical portfolio referenceability | Search neither reads nor requires Current Selection. Portfolio-aware decoration of results ("already held in Portfolio X") is an Experience-layer join against Portfolio Intelligence, outside the search boundary (§11). Search must function identically with Current Selection = NONE. |

No frozen milestone is redesigned, amended, or reinterpreted by M37.

---

## 8. Dependency Mapping

Per the constitution's dependency law (§7.1: dependencies point downward only):

```
                Experience Platform  (consumer: renders results, captures selection)
                        │  query in / candidates out
                        ▼
        ┌── Universal Asset Search Boundary ──┐
        │   (composition seam — owns nothing) │
        └──────┬──────────────────────┬───────┘
               │ catalog candidates   │ external candidates (optional scope)
               ▼                      ▼
        Asset Foundation        Discovery Layer / User Search door
        (Registry catalog:      (Market Intelligence + Provider
         identity, symbols,      Interface: witnesses queried through
         classification,         existing adapters; claims returned,
         capabilities,           nothing asserted)
         lifecycle status)
```

- **Depends on (downward):** Asset Foundation (the catalog and its taxonomy);
  the Discovery Layer's User Search door (which itself sits on the Provider
  Interface). Nothing else.
- **Explicitly does NOT depend on:** Ledger & Accounting, Portfolio
  Intelligence, Wealth Intelligence, Decision Intelligence, Trust & Evaluation,
  Connectivity & Ingestion's other doors, or any Experience state (workspace,
  Current Selection).
- **Is depended on by (upward, future):** any Experience surface that finds
  assets — watchlist entry, idea intake, holdings/transaction entry, future
  dashboards — and, potentially, Connectivity & Ingestion flows that want a
  human-assisted candidate picker during import reconciliation. All are
  consumers; none may reach past the boundary to its sources.

This placement follows the constitution exactly: search *is* the "searchable
and discoverable" responsibility Asset Foundation already carries, extended
outward through the discovery door Market Intelligence already owns. The
Search Boundary is the seam where those two frozen responsibilities meet one
consumer contract.

---

## 9. Canonical Responsibilities

What the Universal Asset Search Boundary **owns**:

- The **consumer contract**: one query shape in, one candidate-list shape out,
  for every asset class and every consumer (§12).
- The **fan-out and merge discipline**: consulting the catalog always, external
  universes only when scope says so; merging into one honestly-labeled list;
  de-duplicating a registered asset against its own external echo (a candidate
  the catalog already knows must appear once, as registered — recognized via
  the Registry's existing provider mappings, never by search's own matching
  opinion).
- The **candidate vocabulary** (§10.3) and the **scope vocabulary** (§10.2).
- The **ordering bound**: candidate order is deterministic and explainable per
  S7; the boundary owns the *constraint*, implementation owns the algorithm.
- The **partial-failure contract**: what a degraded result set looks like and
  how degradation is disclosed (S8).

What it **must never own** (each already has a home):

| Never owned by search | Owner |
| --- | --- |
| Identity, minting, resolution verdicts, mappings | Asset Registry / Resolver |
| Provider communication, symbol dialects, vendor quirks | Provider adapters (PROVIDER_INTERFACE.md) |
| Prices, quotes, observations of worth | Market Intelligence |
| "Is this held / can I afford it / does it fit policy" | Portfolio Intelligence / Decision Intelligence |
| Whether an asset is a *good* result | Decision Intelligence (and never as ordering — S7) |
| The rendered experience, saved searches, recents | Experience Platform |
| Classification taxonomy content | Registry classification stewardship |

---

## 10. Core Concepts

### 10.1 Search, lookup, registry, identity, intelligence, analytics — the six-way distinction

These words are not interchangeable, and the architecture depends on keeping
them apart:

- **Identity** — *what a thing permanently is*: an `asset_id` and its
  guarantees. Owned by Asset Foundation. Identity is a **fact**; it is never
  produced by searching, only referenced by it.
- **Registry** — *the institution that keeps identity*: mints, adjudicates,
  relates, and defends `asset_id`s. The Registry is an **authority**. Search
  is one of its *readers*, never its peer and never its writer.
- **Lookup** — *dereferencing a known identity*: given an `asset_id` (or the
  platform's own `canonical_symbol`), return the asset record — exact,
  unranked, boolean in success, no candidates, no ambiguity tolerated. Lookup
  is a Registry read operation that already exists conceptually and is **not
  part of the Search Boundary**. The distinction is load-bearing: engines and
  services *look up*; humans *search*. A service that "searches" for what it
  should look up has smuggled ambiguity into a deterministic path.
- **Search** — *going from partial, human-shaped description to a ranked set
  of candidate references*: fuzzy in input, plural in output, honest about
  uncertainty, read-only, human-facing. Search ends where a candidate is
  selected; everything after selection is lookup (registered) or discovery
  resolution (unregistered).
- **Intelligence** — *judgment about assets*: beliefs, fit, recommendations.
  Lives in Decision Intelligence, downstream of Knowledge, behind its own
  constitution. Search results carry **zero** intelligence: no scores, no
  fit-signals, no opinions. A surface wanting "search results annotated with
  AI views" composes search output with Decision Intelligence output *in the
  Experience layer* — the annotation never enters the search contract.
- **Analytics** — *derived measures about assets and portfolios*: performance,
  exposure, risk. Lives in Portfolio Intelligence. Same rule as intelligence:
  composable above the boundary by consumers, never inside it.

### 10.2 Search Scope

A search always declares, explicitly, which universes it consults:

- **Catalog scope** — the Registry's own catalog: every registered asset, all
  classes, searchable by canonical symbol, display symbol, name, recorded
  external identifiers, and classification dimensions. Always available,
  provider-independent by construction, and sufficient for every consumer whose
  purpose is "reference something the platform knows."
- **Universe scope** — catalog **plus** external universes, reached solely
  through the Discovery Layer's User Search door. This is the scope for
  consumers whose purpose includes "encounter something new." External
  consultation is an explicit widening, never a silent fallback: a catalog-
  scoped search that finds nothing returns nothing, loudly, rather than
  quietly asking the world.

Scope is part of the consumer contract, not a runtime guess. Which scope each
Experience surface uses is a product decision made per consumer, later; the
architecture only requires that it be declared.

### 10.3 Search Candidate

The single output concept. A candidate is a read-only projection with exactly
two structural kinds:

- **Registered candidate** — carries the `asset_id`, canonical symbol, display
  symbol, classification facts, lifecycle status, and (where relevant to the
  consumer contract) capability facts — all as the Registry currently asserts
  them. Selecting one yields an ordinary canonical asset reference. No
  resolution occurs, because none is needed: identity already exists.
- **Discovery candidate** — carries **no** `asset_id`. It is a presentation of
  a **discovery claim** (MARKET_DATA_PLATFORM.md §4): the evidence bundle a
  witness reported (names, external identifiers, venue, currency), tagged with
  provenance, asserting nothing. Selecting one hands the claim to the existing
  claim → resolve → register pipeline, where the Resolver and Registry — not
  search — determine whether it is something already known, something new, or
  something ambiguous requiring the human's word.

The kinds never blur. There is no "probably registered" candidate: if the
Registry's existing mappings recognize an external result as an asset it
already has, the boundary presents it as *registered* (the Registry's mapping
made that determination, not search); otherwise it is a discovery candidate,
whatever it superficially resembles. Uncertainty belongs to the resolution
pipeline, after selection — never to the candidate list's structure.

### 10.4 Candidate ordering (the bound, not the algorithm)

Ordering exists because humans read lists top-down; it is bounded so it can
never become opinion:

- Deterministic given identical inputs (same query, same catalog state, same
  witness responses) — so an ordering is always explainable after the fact.
- Computable only from: match quality between query and candidate fields,
  identifier-strength vocabulary the Resolver already defines
  (MARKET_DATA_PLATFORM.md §5's evidence hierarchy), registered-before-
  unregistered precedence, and declared classification filters.
- Never computable from: judgments, analytics, popularity-as-recommendation,
  provider commercial preference, or anything produced above the Knowledge
  layer.

The algorithm itself — tokenization, fuzziness, weights — is deferred (§18).

---

## 11. Runtime Boundaries

- **Workspace boundary.** Asset identity is platform-global; the catalog is
  therefore searched globally, and search takes no `workspace_id`. What is
  workspace-bound is what a user *does after* selecting a candidate (add to a
  workspace's watchlist, transact in a workspace's portfolio) — and those
  actions already have workspace-scoped owners and resolvers (M35/M36.1).
  Search neither weakens nor re-implements that scoping; it simply ends before
  it begins.
- **Current Selection boundary.** Search never reads Current Selection and is
  fully functional at Current Selection = NONE (M36-WP1 invariants are
  untouched). Any "in the context of your selected portfolio" decoration of
  results is an Experience-layer composition, subject to M36.1's established
  request-identity discipline like every other portfolio-bound view — outside
  this architecture.
- **Truth boundary.** Search sits entirely in the read path of the Identity
  layer plus the witness edge of the Observation layer. It touches no ledger,
  proposes no events, and is invisible to replay. Nothing in the accounting
  path may call search (engines look up; they never search — §10.1).
- **Provider waterline.** External universes are reached only through the
  existing Discovery Layer / Provider Interface. Provider identity surfaces to
  consumers only as *provenance on discovery candidates* — an audit fact,
  never a branching input.
- **Authority boundary.** A search result is never citable as an identity
  determination. The only identity determinations remain the Registry's
  recorded mappings and verdicts.

---

## 12. Public Architectural Interfaces

Public = what consumers (Experience surfaces, and any future gated flow
wanting a human-assisted picker) may depend on. Described as contracts, not
signatures:

- **Search** — *query + declared scope + optional classification filters →
  ordered candidate list + degradation disclosure.* The query is human-shaped
  (partial names, partial symbols, identifiers of any supported kind, in any
  supported language). Filters are expressed exclusively in the Registry's
  classification vocabulary (asset class, market, region, currency, exchange —
  ASSET_REGISTRY.md §8), so the filter surface grows when the taxonomy grows,
  automatically, and never grows anywhere else.
- **Candidate handoff** — *selected registered candidate → canonical asset
  reference* (a lookup, performed by the consumer against the Registry — the
  boundary's obligation is only that a registered candidate carries everything
  needed to perform it); *selected discovery candidate → discovery claim
  submission* into the existing resolution pipeline, whose own contract
  (silent resolution / ranked confirmation / quarantine) then governs.

That is the entire public surface: one read operation, two exits. Anything a
consumer wants beyond it (recents, saved searches, held-asset badges,
AI annotations) is composition above the boundary.

## 13. Internal Architectural Interfaces

Internal = the seams inside the boundary, invisible to consumers:

- **Catalog candidate source** — a read of the Registry's catalog (identity,
  symbols, recorded external identifiers, classifications, lifecycle,
  capabilities). Constraint: this read consumes the Registry's existing read
  path; it never maintains a parallel copy of identity data that could drift
  into a shadow registry (§17, R1 — an *index* over Registry data is an
  implementation detail permitted by the deferred-decisions section only so
  long as it is a disposable derivation, rebuildable and never authoritative,
  in exactly the sense of Law 3).
- **External candidate source** — an invocation of the User Search discovery
  door. Constraint: search passes the human's query through and receives
  claims back; all provider routing, adapter fluency, and quality weighing stay
  inside the Market Data Platform where they already live.
- **Merge & de-duplication** — the recognition of "this external result *is*
  registered asset X" happens by consulting the Registry's recorded provider
  mappings — never by search-side string heuristics, because recognizing
  sameness *is* an identity question and identity questions have one owner.
  Where no recorded mapping exists, no sameness is asserted: the external
  result stands as a discovery candidate even if it "obviously" matches — the
  resolution pipeline, post-selection, is where obviousness is adjudicated.

---

## 14. Search Lifecycle

The complete life of one search, in owner-annotated stages:

1. **Query formation** *(Experience)* — a human expresses intent: text,
   optional filters, and the consumer's declared scope.
2. **Catalog consultation** *(Search Boundary → Asset Foundation)* — always.
   Matching against canonical symbols, display symbols, names, recorded
   external identifiers, and classifications. Produces registered candidates.
3. **Universe consultation** *(Search Boundary → Discovery Layer)* — only in
   universe scope. The User Search door queries external witnesses through
   existing adapters; claims come back provenance-tagged. Unavailability of
   any witness is recorded for the degradation disclosure, never papered over.
4. **Recognition & merge** *(Search Boundary, consulting Registry mappings)* —
   external claims that the Registry's recorded mappings already resolve are
   folded into their registered candidates; everything else becomes a
   discovery candidate. One list, two honest kinds, no duplicates of a known
   asset.
5. **Ordering** *(Search Boundary)* — per §10.4's bound.
6. **Presentation** *(Experience)* — rendering, including the degradation
   disclosure when a consulted universe was unavailable.
7. **Selection or abandonment** *(human)* — abandonment is a complete,
   side-effect-free end: nothing was created, nothing must be cleaned up.
8. **Handoff** *(exits the search architecture)* —
   a registered candidate becomes a canonical reference via Registry lookup;
   a discovery candidate becomes a claim entering the existing
   claim → resolve → register pipeline (ASSET_REGISTRY.md §4, §6). Whatever
   the human then does with the reference (watch, analyze, transact) proceeds
   under that action's own existing gates and scoping.

Stages 2–5 are the entire Search Boundary. Everything before is Experience;
everything after step 7 belongs to owners that predate this milestone.

## 15. Identity Flow

The one-way arrow, end to end:

```
human description ──▶ query ──▶ candidates ──▶ selection ──┬─▶ (registered)  asset_id via Registry lookup
        (no identity)   (no identity)  (identity only        │
                                        where Registry       └─▶ (discovery)  claim ──▶ Resolver/Registry
                                        already minted it)                     adjudication ──▶ asset_id
                                                                               (or ambiguity surfaced,
                                                                                or discarded — no scar)
```

Properties the flow guarantees:

- `asset_id` appears in the flow **only** where the Registry already minted it.
  Search transports identity; it never creates, infers, or approximates it.
- The arrow never reverses: no candidate, claim, or search-side artifact ever
  feeds back into the Registry except through the front door of adjudication.
- A repeated search for a since-registered asset naturally migrates the result
  from discovery candidate to registered candidate — with no search-side
  memory involved, because the Registry's mappings are the only memory.
- Nothing in the flow writes anything a ledger, replay, or audit will ever
  re-encounter, except the claims explicitly submitted at handoff — which are
  the Discovery Layer's existing, already-governed artifact.

---

## 16. Extension Mechanisms

How the foundation grows without being modified — each extension point is an
existing frozen mechanism that search inherits by construction:

- **New asset class** → described in Asset Foundation (definition,
  classification, capabilities per UNIVERSAL_ASSET_ARCHITECTURE.md §11).
  Registered instances become searchable because the catalog source reads the
  catalog. Zero search changes. *This is the "universal" in Universal Asset
  Search: universality is inherited from the asset model, not engineered into
  search.*
- **New classification dimension** → added to the Registry's stewarded
  taxonomy (ASSET_REGISTRY.md §8); becomes a filter automatically because the
  filter vocabulary *is* the taxonomy.
- **New external universe / provider** → a new adapter behind
  PROVIDER_INTERFACE.md, routed by the Market Data Platform. Search sees more
  candidates through the same door. Zero search changes.
- **New discovery door** (imports, feeds) → orthogonal by design: other doors
  produce claims without any search involvement, exactly as today. If a future
  import flow wants a human-assisted candidate picker, it becomes one more
  *consumer* of the public search contract.
- **New consumer surface** → consumes the public contract (§12). The contract
  is consumer-count-invariant; a tenth consumer changes nothing for the first
  nine.
- **Identifier kinds not yet supported as query input** (e.g., FIGI entry) →
  an extension of query interpretation *bounded by* the Resolver's evidence
  vocabulary — added once, at the boundary, for all consumers.

## 17. Risks

| ID | Risk | Severity | Mitigation (architectural) |
| --- | --- | --- | --- |
| R1 | **Shadow registry.** A search index/cache accretes identity data and drifts into a second authority — the exact historical failure class (private mappings) the Registry exists to end. | High | Constitutional framing: any index is a Law-3-style disposable derivation of Registry data — rebuildable, never written to by anything but Registry state, never consulted for identity determinations. Stated here as a binding constraint on the future implementation. |
| R2 | **Ranking drift into judgment.** "Better results" pressure gradually adds popularity, held-by-you, or model-opinion signals into ordering, silently crossing the judgment/arithmetic boundary. | High | S7 makes the input set for ordering *closed* (enumerated, opinion-free). Widening it is an architecture change requiring this document's amendment, not a tuning decision. |
| R3 | **Search used as lookup.** Services or engines call search where they hold an exact identity, importing ambiguity into deterministic paths. | Medium | §10.1's search/lookup distinction is normative: nothing below the Experience layer consumes the search contract. Review gate at implementation time. |
| R4 | **Silent identity guessing at merge.** De-duplication "improves" by string-matching external claims to registered assets without a recorded mapping. | High | §13's merge rule: sameness is asserted only from Registry-recorded mappings; everything else stays a discovery candidate and is adjudicated post-selection by the owner of that question. |
| R5 | **Provider leakage through candidates.** Vendor symbols/quirks in discovery candidates get consumed by surfaces as if canonical. | Medium | Discovery candidates carry evidence *as provenance-tagged claim content*, structurally separate from the canonical fields registered candidates carry; consumers render claims as claims. Inherited from the witness/authority contract. |
| R6 | **Scope creep toward intelligence.** Consumers push annotations (fit, scores, AI views) into the candidate model "for convenience." | Medium | §10.1 and §12: annotations are Experience-layer composition; the candidate model is closed to judgment and analytics fields. |
| R7 | **Duplicate finding surfaces persist.** Existing ad-hoc symbol-entry paths remain alongside the new boundary, violating one-seat. | Medium | An adoption/conformance obligation for the implementation milestone (§19), following the M36.1 precedent of consolidation-by-audit rather than big-bang replacement. |
| R8 | **External search unavailability treated as emptiness.** A witness outage makes the world look smaller with no disclosure. | Low | S8's degradation disclosure is part of the public contract, not a UX nicety. |

## 18. Deferred Decisions

Deliberately not decided here; each is recorded with its future owner:

1. **Ranking algorithm** (tokenization, fuzziness, weights, per-language
   analyzers — including Thai-language matching) — implementation milestone,
   inside §10.4's bound.
2. **Indexing and caching** (whether a catalog index exists at all, its
   technology, its rebuild cadence) — implementation milestone, inside R1's
   constraint.
3. **Per-consumer scope assignments** (which surfaces get universe scope) —
   product decision at each consumer's milestone.
4. **Query interpretation depth** (identifier auto-detection, multi-token
   semantics, typo tolerance) — implementation milestone.
5. **Pagination/limit semantics and API shape** — implementation milestone
   (level 4→5 descent this document deliberately does not make).
6. **Rate/abuse posture toward external witnesses** — Market Data Platform
   operational concern (its existing provider-quality machinery).
7. **Whether discovery-candidate selection requires an M33-governed action**
   for *auto-registration* paths (bulk import contexts) — deferred to the
   Connectivity & Ingestion milestone that would create such a path; the
   human-initiated single-selection path uses the existing resolution
   contract's human-confirmation discipline and needs no new governance.
8. **Search telemetry** (what, if anything, about search activity is worth
   recording operationally) — implementation milestone, bounded by "nothing
   telemetric becomes identity evidence."

## 19. Future Milestone Dependencies

- **M37.x implementation milestone(s)** — realize the boundary: catalog
  search first (catalog scope is fully useful alone and touches no provider),
  then universe scope through the existing discovery door; then the R7
  conformance sweep consolidating existing ad-hoc asset-finding paths onto the
  boundary. The M36 → M36.1 pattern (frozen foundation → conformance-driven
  runtime milestone with its own review) is the intended template.
- **Watchlist / idea-intake adoption** — these surfaces become consumers of
  the public contract; their milestones depend on M37.x.
- **Multi-Asset Dashboard and future Experience milestones** — consumers;
  depend on M37.x, not on this document alone.
- **Connectivity & Ingestion growth** (statement/broker imports) — may adopt
  the search contract for human-assisted reconciliation; that milestone owns
  deferred decision 7.
- **New asset-class milestones** (funds, bonds, and beyond) — no dependency
  in either direction beyond the automatic inheritance of §16; this is the
  design's central payoff and should be asserted as a conformance check in
  each such milestone's review.

## 20. Recommended Repository Structure

Architecture-level recommendation only (no files are created by this
milestone). Stated so the implementation milestone starts with placement
already settled:

- `docs/implementation/M37_WP1_Universal_Asset_Search_Foundation.md` — this
  document.
- A future `backend/services/asset_search/` (or a single
  `asset_search_boundary` service module, at implementation's discretion) —
  the Search Boundary's one home, depending on the existing registry read
  path and the existing discovery/market-data services, and on nothing else.
  It must not live inside the registry package (it is a reader, not part of
  the authority) nor inside any provider/adapter package (it sits above the
  waterline).
- Frontend consumption through one shared client boundary (the existing
  `frontend/lib` convention), so that no page grows a private search client —
  the M36.1 one-mechanism precedent applied to search.
- No new documentation tree: this document slots into the existing
  `docs/implementation/` milestone sequence, under the existing governance
  levels (Platform Architecture §11), as a level-4 artifact.

---

## 21. Architectural Self-Review

Performed against the frozen corpus before submission. Verification checklist:

- **No redesign of previous milestones** — confirmed. Every M29–M36 artifact
  is consumed as-is; §7 enumerates the relationships and each row is
  "untouched" or "consumed."
- **No duplicate ownership** — confirmed by construction: the boundary owns
  only the consumer contract, fan-out/merge discipline, and vocabulary (§9);
  every fact and every verdict retains its pre-existing owner. The one
  delicate point (merge/de-duplication) is explicitly resolved by delegating
  sameness to Registry-recorded mappings (§13, R4).
- **No hidden implementation decisions** — checked. The nearest misses are
  named and pushed out explicitly: ranking (deferred 1), indexing (deferred 2),
  scope-per-consumer (deferred 3), API shape (deferred 5).
- **No provider coupling** — confirmed: external reach is exclusively through
  the existing Discovery Layer / Provider Interface; provider identity appears
  only as provenance (§11, S6).
- **No runtime coupling** — confirmed: no workspace, Current Selection,
  session, or frontend-framework assumptions (§11); search functions at
  Current Selection = NONE.
- **No database assumptions** — confirmed: no schema, no index technology, no
  storage shape anywhere; the only storage-adjacent statement is the R1
  constraint that any future index be a disposable derivation.
- **No API assumptions** — confirmed: §12 is expressed as contracts
  (query→candidates; two handoffs), not endpoints or signatures.
- **No unnecessary abstractions** — the milestone introduces exactly three
  concepts: Search Boundary, Search Scope, Search Candidate (with its two
  kinds). Each is justified: the boundary by Law 9/one-seat (§2's problem),
  scope by the silent-fallback prohibition (§10.2), the candidate kinds by
  the identity-honesty requirement (S5). Search *ordering* was deliberately
  not made a named concept — it is a bound on the boundary, not an object.
- **Consistency with the frozen corpus** — the document reuses the corpus's
  own vocabulary (claim, door, witness, adjudication, mapping, canonical
  symbol, capability, classification) rather than coining synonyms, per the
  constitution's V1/V2 vocabulary rules.

**Potential architectural weaknesses found (disclosed, not hidden):**

1. **The boundary is thin, and thinness invites bypass.** Because the Search
   Boundary owns so little, an implementer may judge it ceremonial and let a
   consumer call the registry read path or a provider adapter directly. The
   architecture's answer is R3/R7's conformance obligations, but enforcement
   is procedural (review), not structural. This is the design's largest
   practical risk.
2. **De-duplication strictness has a UX cost.** §13's rule (no sameness
   without a recorded mapping) means a user can see a discovery candidate for
   something that is "obviously" an already-registered asset whose mapping for
   that particular provider spelling hasn't been recorded yet. The
   architecture accepts this cost deliberately (a wrong silent merge is
   worse), and the cost self-heals (each adjudication records the mapping) —
   but reviewers should confirm they accept the trade-off explicitly.
3. **Universe-scope liveness tension.** External consultation makes search
   latency and completeness hostage to witness responsiveness. S8 makes
   degradation honest but cannot make it pleasant; the deferred caching
   decision (2) will carry real pressure against R1, and that pressure point
   is where a shadow registry would most plausibly emerge. Flagged so the
   implementation review looks there first.
4. **Vocabulary registration is pending.** "Search Candidate," "Search Scope,"
   and "Universal Asset Search Boundary" are new terms of art that, per
   constitution V2, must be registered in GLOSSARY.md when this document is
   accepted. This document does not modify the glossary (frozen-corpus
   discipline during review); registration is an acceptance-time obligation
   and is recorded here so it cannot be forgotten.
5. **Deferred decision 7 leaves a governance edge open.** Bulk/auto
   registration paths are explicitly unowned until a Connectivity & Ingestion
   milestone claims them. The single-selection human path is fully governed by
   existing contracts, so no gap exists *today* — but the deferral should be
   tracked so it is not rediscovered as a surprise.
6. **Thai-language and multi-script matching is entirely deferred.** For this
   platform's home market this is not a minor tuning detail; a search that
   cannot match Thai fund names will fail its purpose in practice. It is
   correctly an implementation concern, but reviewers should treat deferred
   decision 1 as high-priority, not residual.

**Suitability verdict:** the architecture introduces minimal new surface,
assigns no new authority, preserves every frozen boundary, and states its own
weaknesses honestly. In this architect's judgment it is **suitable to proceed
to independent architectural review**, with reviewer attention directed
specifically at weaknesses 1–3 above.
