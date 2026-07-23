# M40 — Canonical Asset Market Measure Foundation

**Date:** 2026-07-23

**Document class:** Proposed architecture and implementation plan

**Status:** `PROPOSED_FOR_ARCHITECTURAL_REVIEW`

**Approval state:** `NOT_APPROVED`

**Canonical authority:** `NONE`

**Implementation authority:** `NONE`

**Runtime authority:** `NONE`

**Production method authority:** `NONE`

**Provider authority:** `NONE`

**Persistence authority:** `NONE`

**Public exposure authority:** `NONE`

**Decision Log status:** `NOT_SUBMITTED`

**Supersedes:** `NONE`

**Closeout:** `NONE`

**Independent review:** [APPROVED WITH REQUIRED CORRECTIONS](M40_INDEPENDENT_CONSTITUTIONAL_ARCHITECTURE_REVIEW.md)

**Review response:** [M40 Review Response](M40_REVIEW_RESPONSE.md)

**Normative status:** This document is a non-canonical proposal. Its use of
`MUST`, `MUST NOT`, `SHALL`, `SHALL NOT`, `MAY`, and `SHOULD` describes
requirements proposed for review. Those terms acquire no repository authority
unless and until the plan is independently reviewed and explicitly approved.

**Governing architecture and frozen authority (not amended by this
proposal):**

- [Platform Architecture](../architecture/platform_architecture.md);
- [Canonical Glossary](../GLOSSARY.md);
- [Asset Foundation Constitution](../architecture/asset_foundation.md);
- [Asset Definitions Constitution](../architecture/asset_definitions.md);
- [Universal Asset Architecture](../architecture/UNIVERSAL_ASSET_ARCHITECTURE.md);
- [M34 Decision Register](m34/audit/registers/decision_register.md), especially
  `M34-D-0004`, `M34-D-0005`, and `M34-D-0010`;
- [M35 Product Workspace Foundation](M35_WP1_Product_Workspace_Foundation.md);
- [M36 Multiple Portfolio Foundation](M36_WP1_Multiple_Portfolio_Foundation.md);
- [M37 Universal Asset Search Foundation](M37_WP1_Universal_Asset_Search_Foundation.md);
- [M38 Product Workspace Foundation closeout](M38_EPIC_CLOSEOUT.md); and
- the complete frozen M39 corpus:
  [WP1](M39_WP1_Canonical_Boundary_Specification.md),
  [WP2](M39_WP2_market_observation_source_boundary_specification.md),
  [WP3](M39_WP3_market_observation_classification_specification.md),
  [WP4](M39_WP4_market_observation_payload_specification.md),
  [WP5](M39_WP5_market_observation_relationship_specification.md),
  [WP6](M39_WP6_market_observation_identity_specification.md), and
  [M39 Epic Closeout](M39_EPIC_CLOSEOUT.md).

---

## 1. Executive Assessment

M40 should establish an asset-agnostic deterministic analytical foundation,
but the repository supports a narrower and more precise milestone than
`Universal Asset Analysis Foundation`.

The recommended successor is:

> **M40 — Canonical Asset Market Measure Foundation**

M40 should define, and only after separate approval implement, a pure,
fixture-backed foundation for producing deterministic, provider-neutral
**Calculated Market Measures** from canonical M39 Observation semantics.

M40 must not become:

- a generic Analysis domain;
- a composite Instrument Analysis authority;
- a production analytics platform;
- an Observation implementation or persistence milestone;
- a portfolio-measurement owner;
- an Investment Judgment, recommendation, or strategy layer;
- a provider, scheduler, or public API integration; or
- an execution, transaction, or trading authority.

This proposal creates no authority to implement any work package. Approval of
the architecture would establish the milestone boundary only. Each
implementation-bearing work package remains subject to the explicit admission
and review gates in this plan.

### 1.1 Corrected architectural flow

The tentative milestone flow is constitutionally incorrect if it implies that
Provider Evidence creates or governs a Canonical Asset Definition. Asset
Foundation owns Asset identity and definitions independently. Providers remain
witnesses.

The proposed flow is:

```text
Canonical Asset Identity + Definition Version
                         │
                         ├──────────────┐
                         │              │
                         ▼              ▼
              Method Requirements   Canonical M39
                                    Observation Evidence
                                           │
                                           ▼
                               Observation Input Manifest
                                           │
                                           ▼
                                Versioned Pure Calculation
                                           │
                                           ▼
                               Calculated Market Measure
                                           │
                                           ▼
                            Read-only projection, if separately
                            authorized in a later adoption step
```

Provider evidence may inform Asset Foundation or Market Intelligence only
through their existing witness-and-adjudication boundaries. It never defines
an Asset, grants an Asset capability, selects an analytical method, or becomes
platform judgment.

---

## 2. Repository-Grounded Findings

### 2.1 Exact capability completed by M39

M39 is complete and frozen as the constitutional specification corpus for
Canonical Asset Market Observation. It established:

- one frozen current-price read contract,
  `GET /assets/{assetId}/market-observation`;
- Market Intelligence as sole semantic owner of Observation Source, Event,
  Timestamp, Origin, Classification, Payload, Relationship, and Identity;
- one immutable, source-reported Observation Event with exactly one Canonical
  Observation Class;
- provider-neutral payload meaning, temporal fidelity, provenance, identity,
  inter-event relationships, and correction semantics; and
- strict separation from Asset identity, ledger truth, portfolio meaning,
  Investment Judgment, execution, and presentation.

M39 did not authorize or implement:

- its frozen public boundary;
- historical observations or observation series;
- Observation storage, retention, replay, or snapshots;
- provider integration for the M39 boundary;
- a runtime consumer of WP2 through WP6 semantics; or
- any calculation, analytics, prediction, or recommendation.

### 2.2 Architectural gap after M39

M39 deliberately excludes platform calculation. An M39 Observation Event
represents an external, source-reported claim. A platform-computed statistic is
therefore not an M39 Observation Event and must not be assigned Event Type
`Observation`.

This distinction refines artifact and event type; it does not narrow or
reinterpret the frozen [Market Observation](../GLOSSARY.md#market-observation)
ownership boundary. The Glossary and `M34-D-0010` use Market Observation
broadly enough to include technical observations and market statistics, all
owned by Market Intelligence. A witnessed or provider-reported market
statistic remains a Market Observation represented through the M39 Observation
semantics. A statistic computed by the platform remains Market
Intelligence-owned market evidence, but is represented as a Calculated Market
Measure with Canonical Temporal Claim Event Type `Calculation`. Neither form is
Investment Judgment.

The unresolved boundary is:

> How may the platform produce a reproducible calculated market fact from
> immutable canonical observations without reclassifying the calculation as
> an Observation or promoting it into Investment Judgment?

That is the proposed M40 boundary.

### 2.3 Existing analytical implementations

The repository contains useful historical implementations but no canonical,
asset-agnostic Market Measure foundation:

- `backend/agents/technical.py` accepts a symbol, fetches provider-shaped OHLCV
  history, assumes daily and weekly bars, and produces bullish/bearish,
  trend, and score semantics.
- `backend/services/analytics/quant_engine.py` is portfolio-oriented, accepts
  ORM rows, uses Pandas/NumPy and floating-point behavior, contains calendar
  assumptions, emits JSON-ready dictionaries, and maintains process-local
  caches.
- `AnalysisCache` is keyed by Workspace and symbol and stores signals,
  confidence, reasoning, AI summaries, models, and providers.
- `RegimeSnapshot` and `SignalHistory` combine calculated statistics with
  classification, confidence, decision, or optimizer semantics.
- `backend/services/portfolio_metrics.py` is a sound example of a pure,
  single-implementation calculation boundary, but its inputs and semantics are
  Ledger and Portfolio-owned and must not be generalized into Market
  Intelligence.

These artifacts are implementation evidence and possible future migration
subjects only. This proposal does not declare them canonical, migrate them,
change their owners, or authorize their reuse.

### 2.4 Frozen ownership boundaries

| Meaning | Frozen owner | M40 treatment |
| --- | --- | --- |
| Asset identity, definition, classification, and definition capabilities | Asset Foundation | Referenced only |
| Source-reported market observations and market context | Market Intelligence | Consumed without mutation |
| Financial truth and ledger-derived state | Ledger & Accounting | Out of scope |
| Portfolio performance, exposure, attribution, and portfolio risk | Portfolio Intelligence | Out of scope |
| Investment conclusions, instrument risk assessments, recommendations, and plans | Decision Intelligence | Out of scope |
| Correctness, quality, and trust assessment | Trust & Evaluation | Out of scope |
| Projection, interaction, and composition | Experience Platform | Future read-only seam only |
| Authentication, authorization, approval, and actor authority | Existing non-domain boundaries | Unchanged |

M34-D-0010 rejects a composite Instrument Analysis authority. Market
Observations remain Market Intelligence-owned. Investment Judgment,
Instrument-Level Risk, Consensus, and Analysis History remain Decision
Intelligence-owned. Evaluation remains Trust & Evaluation-owned.

The Platform Architecture layer table does not transfer every computed object
to Portfolio Intelligence. Sections 5 and 6 map portfolio and life meaning
derived from truth and observation to the Knowledge layer, while section 6.2
expressly assigns asset valuation over time, regime, volatility, breadth,
histories, and market context to Market Intelligence. `M34-D-0010` likewise
assigns technical observations and market statistics to Market Intelligence.
A Calculated Market Measure stays within that narrower Market Intelligence
responsibility when it describes an identified Asset or market context from
market evidence and contains no portfolio, household, goal, ledger, or
investment-judgment meaning.

### 2.5 Terminology corrections

| Informal term | Proposed repository-aligned treatment |
| --- | --- |
| Universal Asset Analysis | Too broad; implies supported Assets and one Analysis authority |
| Analysis Result | `Calculated Market Measure` within this bounded milestone |
| Analytical Derivation | Avoid as a canonical name because the Glossary defines Derivation as ledger-computed state |
| Analysis History | Already Decision Intelligence-owned |
| Analysis Quality State | `Computation Outcome` and `Input Sufficiency`; quality assessment remains Trust & Evaluation-owned |
| Capability Declaration | Asset Definition capabilities remain Asset Foundation-owned; use `Method Requirement` |
| Analysis Snapshot | Use `Market Measure Snapshot` only if persistence is separately authorized |
| Trend | A numeric statistic may be a measure; bullish, bearish, or expected direction is Investment Judgment |
| Return | M40 may govern a price-series measure; portfolio return remains Portfolio Intelligence-owned |
| Risk | Dispersion or drawdown may be descriptive values; an instrument risk assessment remains Decision Intelligence-owned |

### 2.6 Layer and domain reconciliation

A Calculated Market Measure is constitutionally homed in Market Intelligence
only under the following mechanically testable boundary:

1. every subject is a canonical Asset identity or explicitly defined market
   context, never a Portfolio, Workspace, household, person, goal, or plan;
2. every semantic input is M39 Observation evidence, Asset Foundation
   reference data, an explicit invocation parameter, or a governed
   calculation dependency;
3. the output describes an Asset or market condition and does not interpret
   holdings, cash flows, performance, attribution, exposure, allocation,
   portfolio risk, net worth, or progress;
4. the calculation consumes no Ledger event, holding, tax lot, transaction,
   Portfolio membership, user preference, or life context; and
5. the output contains no outlook, expected direction, recommendation,
   consensus, confidence-as-judgment, or action semantics.

Failure of items 1 through 4 places the concept outside this M40 boundary and
requires classification under Portfolio Intelligence, Wealth Intelligence, or
another existing owner before admission. Failure of item 5 places the concept
in Decision Intelligence. Label similarity is never sufficient to establish
ownership: an asset price-series return, volatility, or drawdown statistic may
be a Market Measure, while portfolio return, portfolio volatility, portfolio
drawdown, and their interpretations remain Portfolio Intelligence meanings.

This is a lower-level refinement under Governance G2, not an exception to the
six-layer model. It relies on the explicit Market Intelligence responsibilities
in Platform Architecture section 6.2, the Knowledge responsibilities in
sections 5 and 6.5, Law 9's single-owner rule, and the decomposition frozen by
`M34-D-0010`.

---

## 3. Recommended Title and Objective

### 3.1 Title

**M40 — Canonical Asset Market Measure Foundation**

`Canonical Asset` preserves `asset_id` and Asset Definition authority.
`Market Measure` denotes a platform calculation over market evidence without
calling it an external Observation. The title neither creates a new domain nor
claims that every Asset type or method is supported.

`Universal Asset Analysis Foundation` may remain an informal direction label
but should not be the canonical milestone title.

### 3.2 Objective

> Establish the canonical vocabulary, owner-explicit contracts,
> deterministic computation rules, provenance model, definition registry,
> and pure fixture-backed calculation boundary through which Market
> Intelligence may produce a Calculated Market Measure from explicitly
> selected M39 Observation evidence for one or more canonical Assets, while
> preserving Asset Foundation identity and definition authority and creating
> no Investment Judgment, portfolio meaning, provider, persistence,
> Workspace, recommendation, or execution authority.

Any approved pure implementation must be callable only with already-canonical
inputs. It must contain no provider access, Registry mutation, current-time
lookup, database access, scheduling, HTTP handling, Asset-type branch, or
production caller.

---

## 4. Scope

### 4.1 In-scope architecture

The minimum coherent architecture includes:

- Calculated Market Measure vocabulary and ownership;
- Market Measure Definition and immutable Method Version;
- one-Asset and explicitly ordered multi-Asset subjects;
- Method Requirements and applicability resolution;
- an Observation Input Manifest;
- explicit Measurement Window and cutoff;
- deterministic ordering, calculation, and result identity;
- typed Measure Values;
- Computation Outcome, Input Sufficiency, and reason codes;
- provenance and dependency manifests;
- a frozen Market Measure Registry;
- pure calculation dispatch;
- fixture-backed conformance;
- an inert future read-only projection contract; and
- explicit method-admission, implementation-admission, and runtime-adoption
  gates.

### 4.2 Subject identity

A Measure Subject must contain:

- exactly one canonical `asset_id`, or an explicitly ordered set of canonical
  `asset_id` values for a multi-subject method;
- subject-role labels defined by the Method Version; and
- exact Asset Definition and Definition Version evidence used to assess
  applicability.

A Measure Subject must not use a ticker, provider symbol, display symbol,
exchange string, provider identity, Workspace state, portfolio membership, or
watchlist membership as identity.

### 4.3 Input contract

An Observation Input Manifest must preserve:

- immutable M39 Observation Identity references;
- canonical subject references;
- Canonical Observation Class;
- canonical payload meaning and a stable content digest;
- explicit semantic timestamps and cutoff;
- required origin and provenance references;
- identity-equivalence, duplicate, selection, and conflict dispositions; and
- deterministic ordering.

No raw provider payload, SDK object, provider field name, provider cache row,
or transport object may enter the core.

### 4.4 Method contract

Each Method Version must declare:

- semantic owner;
- output meaning and unit;
- required Observation Classes and payload meanings;
- required subject cardinality and roles;
- minimum input count and history span;
- temporal-density requirements, if any;
- exact window inclusion and alignment semantics;
- applicable existing Asset Definition declarations;
- unit and currency requirements;
- adjustment expectations;
- calendar dependency, if any;
- missing, duplicate, and conflicting Observation rules;
- decimal precision and rounding;
- dependency versions;
- permitted parameters and their canonical serialization; and
- deterministic failure and partial-result behavior.

### 4.5 Pure implementation boundary

After separate work-package authorization, M40 may implement:

- immutable domain values;
- a frozen definition and method registry;
- exact input validation;
- deterministic ordering and hashing;
- pure calculation dispatch;
- structured success, insufficiency, unavailability, and failure outcomes; and
- test-only reference methods and golden vectors.

The initial production registry must remain empty unless a production method
receives separate, explicit admission authority.

### 4.6 Capability discovery

A caller may discover:

- which admitted Method Versions exist;
- which subjects, observations, units, history, calendars, and existing Asset
  capabilities they require;
- whether a supplied manifest satisfies one exact Method Version; and
- which exact requirement failed.

This is method discovery. It does not admit an Asset type, prove provider
coverage, select a provider, or promise future support.

### 4.7 Read-only exposure design

M40 may specify an inert future projection contract preserving:

- Market Intelligence semantic ownership;
- exact result identity;
- subject references;
- Method Version;
- as-of and cutoff semantics;
- Computation Outcome and provenance; and
- complete Calculation Temporal Claim and explicit Degraded State.

M40 must not bind that proposal to an endpoint, Workspace contribution,
frontend route, database, scheduler, or production caller.

### 4.8 Production method admission

Examples in this document are illustrative only. M40 does not admit moving
average, volatility, drawdown, correlation, return, relative distance, or any
other production method merely by naming it.

A production method requires:

1. one exact semantic owner;
2. one exact formula and output meaning;
3. explicit unit, temporal, adjustment, missing-data, and conflict semantics;
4. independent conformance evidence;
5. version and dependency fingerprints; and
6. explicit method-admission authority.

Test-only reference methods must be structurally incapable of entering the
production registry.

---

## 5. Explicit Non-Goals

| Capability | M40 classification | Reason |
| --- | --- | --- |
| Buy/sell signals | Explicitly excluded | Investment Judgment |
| Recommendations | Explicitly excluded | Decision Intelligence |
| AI-generated analysis | Deferred; governance required | Probabilistic judgment, model governance, and evaluation |
| Strategy execution | Explicitly excluded | Decision and action boundary |
| Portfolio optimization | Already owned elsewhere; unchanged | Decision Intelligence |
| Position sizing | Already owned elsewhere; unchanged | Decision and execution planning |
| Rebalancing | Explicitly excluded | Portfolio decision and action |
| Order creation | Explicitly excluded | Execution |
| Broker integration | Explicitly excluded | Connectivity and execution |
| Live trading | Explicitly excluded | Execution authority |
| Backtesting | Deferred | Requires historical custody and point-in-time method/configuration binding |
| Paper trading | Deferred and separately governed | Simulated execution lifecycle |
| Provider qualification | Already owned elsewhere | M40 consumes canonical evidence |
| Provider selection, routing, or failover | Explicitly excluded | Provider boundary |
| M39 endpoint implementation | Deferred prerequisite for live use | M39 authorizes a contract, not runtime |
| Historical Observation persistence | Deferred | M39 creates no storage or replay authority |
| Admission of Asset types | Blocked pending Asset Foundation governance and evidence | Names in a plan grant nothing |
| Asset-specific implementation bundles | Deferred | Require approved definitions and method evidence |
| Portfolio-level analytics | Already Portfolio Intelligence-owned | Not an Asset market-measure concern |
| Instrument risk assessment | Already Decision Intelligence-owned | M34-D-0010 |
| Quality or correctness scoring | Already Trust & Evaluation-owned | M40 reports sufficiency, not trust |
| UI redesign | Explicitly excluded | Experience Platform concern |
| Workspace runtime binding | Deferred | No runtime authority |
| Schema or database migration | Explicitly excluded | Persistence not authorized |
| Frozen M31–M39 changes | Prohibited | Frozen corpus |
| Migration of legacy analysis tables | Deferred | They mix incompatible identity and judgment semantics |

---

## 6. Proposed Domain Model

Every concept in this section is proposed and non-canonical.

| Concept | Definition and owner | Identity and lifecycle | Version, persistence, and layer |
| --- | --- | --- | --- |
| Calculated Market Measure | Deterministic descriptive market fact calculated from an exact manifest under one Method Version; Market Intelligence-owned | Content-derived `result_id`; immutable | Bound to exact method and dependencies; no M40 persistence; domain result |
| Market Measure Definition | Governed statement of one measure's meaning, requirements, subject roles, parameters, and outputs; Market Intelligence-owned | Stable `measure_definition_id`; proposed, reviewed, admitted, prospectively deprecated; never rewritten | Immutable revisions; domain and constitutional contract |
| Market Measure Method Version | Exact executable specification implementing one Definition; Market Intelligence owns semantics and runtime has custody only | `(method_id, version, definition_digest, implementation_digest)`; immutable after admission | Every semantic or dependency change creates a version; domain plus implementation contract |
| Measure Subject | Role in which canonical Assets participate; Market Intelligence owns the role and Asset Foundation owns referenced identity/definition | Ordered role, `asset_id`, and Definition Version references; invocation-bound | Method-versioned domain value; no persistence |
| Method Requirement | Explicit condition a subject or manifest must satisfy; Market Intelligence-owned | Stable key inside one Method Version; immutable | Domain contract; not an Asset capability |
| Observation Input Manifest | Ordered evidence binding a calculation to exact M39 Observation meaning; Market Intelligence-owned | Content-derived `manifest_id`; changed input creates another manifest | Domain evidence; no persistence authorized |
| Measurement Window | Explicit interval, cutoff, timezone, inclusion, and alignment rule; Market Intelligence-owned | Canonically serialized, invocation-bound | Semantics belong to Method Version; domain value |
| Measure Invocation | Request to apply an exact method to an exact manifest; Market Intelligence semantics with runtime custody | Deterministic digest excluding operational timestamps | Runtime value; no persistence |
| Measure Value | Typed numeric or structured descriptive output; Market Intelligence-owned | Named coordinate within a result; immutable | Method-defined unit and scale; domain value |
| Computation Outcome | `SUCCEEDED`, `INSUFFICIENT_INPUT`, `DEPENDENCY_UNRESOLVED`, or `FAILED`; Market Intelligence-owned method-execution outcome, orthogonal to Degraded State | Outcome and reason in immutable result | Domain/runtime boundary; not quality, trust, or temporal availability |
| Calculation Temporal Claim | Canonical Temporal Claim with Event Type `Calculation`, Producing Domain `Market Intelligence`, an explicit authoritative timestamp, and Degraded State | Immutable part of every result; timestamp meaning is method-defined and invocation-bound | Canonical temporal grammar governed by `M34-D-0005`; no ambient clock |
| Market Measure Result | Complete immutable invocation outcome; Market Intelligence-owned | Content-derived `result_id` | Bound to all input/dependency versions; no persistence |
| Measure Provenance | Trace to subjects, definitions, observations, method, dependencies, and runtime; Market Intelligence owns result lineage while references retain owners | Immutable part of result evidence | Domain evidence; no persistence |
| Dependency Manifest | Exact arithmetic, calendar, unit, or normalization dependencies | Canonical digest; invocation-bound | Implementation evidence |
| Market Measure Registry | Frozen library of admitted Definitions and Method Versions; Market Intelligence-owned | Atomically built and fail-closed | Code-shipped proposal; no provider, Asset Registry, or plugin authority |
| Market Measure Snapshot | Possible durable representation of a complete result | Reserved only | Persistence explicitly deferred |

Rejected overlapping concepts:

- no generic Analysis Domain;
- no generic Analysis Quality State;
- no M40 Analysis History;
- no executable Asset Definition plugin;
- no new Asset Capability Declaration; and
- no provider-specific Analysis Input.

---

## 7. Asset-Agnostic Boundary

### 7.1 Core input rule

The calculation kernel must never receive:

- Asset type;
- ticker or symbol;
- exchange or venue;
- provider identity or payload;
- Workspace or portfolio identity;
- watchlist state; or
- presentation labels.

It may receive only canonical Measure Subjects, exact Asset Definition Version
evidence, existing capability answers, an Observation Input Manifest, an
immutable Method Version, explicit parameters, and an exact Dependency
Manifest.

### 7.2 Applicability

A method applies because all Method Requirements are satisfied, not because a
subject appears in a supported-Asset-type list.

Illustrative requirements include:

- one `Market Price` Observation carrying an exact price meaning;
- a stable declared unit throughout the window;
- a minimum Observation count and semantic span;
- no unresolved currency mismatch;
- a named calendar version or explicit calendar-free policy;
- an existing valuation-question capability;
- an explicit raw or adjusted input expectation; and
- an exact number and ordering of subjects.

These examples admit no method and create no Asset capability.

### 7.3 Asset Definition vocabulary boundary

M40 must not add analytics-only words to Asset Definition vocabulary.
Existing definitions and Capability Views remain unchanged. A method may
require an existing capability, but Method Requirements remain Market
Intelligence-owned and are not projected back into Asset Foundation.

### 7.4 Prohibited hidden assumptions

The core must not assume ticker or exchange identity, universal OHLCV, daily
bars, a 252-session year, universal adjustment, universal calendars, universal
quantity or price semantics, universal liquidity, continuous history, one
currency, binary floating-point semantics, `shares × price`, or equity terms
unless one separately admitted Method Version declares the exact requirement.

---

## 8. Determinism and Reproducibility

### 8.1 Cutoff and ordering

- Every invocation carries an explicit inclusive Observation cutoff.
- No Observation admitted after the cutoff may enter the manifest.
- Host-clock, cache, database, and retrieval times may not select inputs.
- Computation time is provenance only.
- Inputs order by semantic Observation time, Method-defined role/series key,
  and Observation Identity as a stable tie-breaker.

Provider order, row order, retrieval order, and map iteration order must not
affect output.

### 8.2 Window semantics

Each Method Version defines exact interval inclusion, whether the window is
elapsed-duration, calendar, or Observation-count based, timezone/calendar
basis, alignment, and qualified-time treatment.

No machine locale, machine timezone, exchange convention, weekend rule, or
business-day default may fill an absent rule.

### 8.3 Duplicates and conflicts

- M39 Identity-Equivalent representations denote one semantic event.
- Identity-distinct Observations remain distinct even when values match.
- Conflicting Observations may not be averaged or resolved by hidden provider
  precedence.
- A Method Version must require a governed selection policy or return explicit
  insufficiency/conflict.
- Provider identity may remain provenance but may not drive a core branch.

### 8.4 Missing data

For every required input, a Method Version must select exactly one policy:
reject as insufficient, omit the interval, require exact density, apply an
explicit mathematical interpolation, or return independently complete
partial outputs where the Definition permits.

Forward fill, zero fill, weekend fill, and nearest-value selection are
prohibited unless they are exact versioned method semantics.

### 8.5 Units, currency, and adjustments

- Every value carries an explicit unit.
- Incompatible units may not be compared.
- Unit normalization requires a named, versioned dependency.
- Currency conversion is outside initial M40 scope.
- Multi-currency input fails unless the method is currency-invariant or
  consumes separately authorized normalized evidence.
- Asset or Registry metadata may not fill absent Observation currency.
- Raw, adjusted, and economically continuous series are distinct.
- M40 may not infer adjustments, call providers for them, or interpret
  corporate actions.

### 8.6 Arithmetic

- Canonical outputs use decimal or exact rational semantics where required.
- Binary floating point is permitted internally only if conformance proves
  identical canonical output.
- Input scale, intermediate precision, output scale, and rounding mode belong
  to the Method Version.
- Intermediate rounding is prohibited unless explicit.
- NaN and infinity are never successful Measure Values.

### 8.7 Version closure

Result identity binds Definition identity/revision, Method Version and
fingerprints, ordered subjects, exact Asset Definition Versions, manifest
digest, canonical parameters, dependency versions, and engine compatibility
version where relevant.

No reproduction path may dynamically resolve `latest`.

### 8.8 Failure and partial results

| Computation Outcome | Meaning | Required-value rule |
| --- | --- | --- |
| `SUCCEEDED` | Every required output is complete | Present |
| `INSUFFICIENT_INPUT` | Canonical inputs do not satisfy the method | Absent |
| `DEPENDENCY_UNRESOLVED` | A required governed dependency or facility cannot be resolved | Absent |
| `FAILED` | Valid invocation reached computation but did not complete | Absent |

Partial values are permitted only for independently valid output coordinates
declared by the Definition. A partial result may not claim complete success.

### 8.9 Canonical temporal and degraded-state grammar

Every Market Measure Result must carry the complete
[Canonical Temporal Claim](../GLOSSARY.md#canonical-temporal-claim) required by
`M34-D-0005`:

- Event Type is `Calculation`;
- Producing Domain is `Market Intelligence`;
- the authoritative timestamp is an explicit, method-defined invocation input,
  never a system-clock lookup; and
- Degraded State is one of the states admitted by the canonical Glossary and is
  owned by Market Intelligence for this calculation.

Computation Outcome and Degraded State are orthogonal axes. Computation Outcome
reports whether the specified method completed and produced its required value.
Degraded State qualifies the authoritative temporal availability of the result
and its evidence. The token `UNAVAILABLE` is reserved here for Degraded State;
it is not a Computation Outcome. WP5 and WP6 must define a deterministic,
method-versioned interaction matrix for every admitted outcome and Degraded
State, including successful results based on `DELAYED`, `STALE`, `PARTIAL`, or
`CONFLICTING` evidence. No adapter, client, or presentation label may infer,
replace, or reinterpret either axis.

An operational execution timestamp, if retained by a future runtime envelope,
is not the authoritative timestamp and is excluded from the semantic result and
its identity. This preserves deterministic replay while satisfying the
canonical temporal grammar.

---

## 9. Provenance and Evidence

Every result must be traceable to:

- Measure Subjects and canonical `asset_id` values;
- exact Asset Definition Versions;
- Observation Input Manifest and exact Observation Identities;
- canonical Observation content digests;
- Observation Origin and provider evidence references where applicable;
- Market Measure Definition and Method Version;
- invocation parameters;
- Measurement Window and cutoff;
- Dependency Manifest and engine compatibility version;
- complete Calculation Temporal Claim, including the explicit authoritative
  timestamp and Degraded State;
- Computation Outcome; and
- exact insufficiency, unavailability, or failure reasons.

The proposed canonical analytical evidence structure is an Observation Input
Manifest, not an unstructured repeated list. A result references the manifest
while retaining enumerability of every exact Observation.

This proposal does not add fields to M39, define M39 persistence, or claim that
an Observation snapshot already exists. Provenance carries references and
acquires no ownership of the referenced concepts.

---

## 10. Work-Package Plan

The work packages form a dependency-safe sequence. Their inclusion creates no
authority to execute them.

### M40-WP1 — Corpus and Successor Boundary Audit

**Objective:** Confirm M31–M39 constraints, inventory legacy analytics, and
freeze the candidate ownership matrix.

**Dependencies:** Frozen corpus only.

**Deliverables:** Corpus register, authority/terminology map, legacy inventory,
conflict/reuse register, and successor assessment.

**Likely files:** `docs/implementation/M40_WP1_...md` only.

**Validation:** Every authority resolves; every concept has one proposed
owner; legacy artifacts are classified without migration authority.

**Exclusions:** Code, glossary mutation, runtime, formulas.

**Exit criteria:** No unresolved ownership collision remains.

**Independent review:** Recommended.

### M40-WP2 — Vocabulary and Ownership Specification

**Objective:** Ratify or reject Calculated Market Measure and close the
Observation/Measure/Judgment/Evaluation boundary.

**Dependencies:** WP1.

**Deliverables:** Boundary specification, minimum coherent glossary proposal,
six-layer and layer-to-domain reconciliation, M34-D-0004/M34-D-0005/
M34-D-0010 compatibility proof, witnessed-observation versus
platform-calculation refinement, output-classification decision tree, owner
matrix, and asset-measure versus portfolio-measure negative corpus.

**Likely files:** `docs/implementation/M40_WP2_...md`; `docs/GLOSSARY.md` only
in the same change as approval.

**Validation:** No Analysis domain, duplicate owner, M39 reinterpretation, or
movement of Instrument-Level Risk/Analysis History. Mechanically test the
section 2.6 boundary and prove that a platform-computed statistic uses Event
Type `Calculation` without weakening the frozen Market Observation meaning.
Verify that `UNAVAILABLE` is used only as a Degraded State and that every
proposed result preserves the complete `M34-D-0005` grammar.

**Exclusions:** Formula, schema, runtime, provider, API.

**Exit criteria:** Independent constitutional approval expressly accepts:

1. the RC-1 six-layer and asset-measure/portfolio-measure ownership proof;
2. the RC-2 Market Observation/Calculated Market Measure refinement;
3. the RC-3 `M34-D-0005` temporal, producing-domain, and state integration; and
4. the minimum vocabulary set admitted under V1 through V3.

No vocabulary is admitted and no downstream work package begins while any item
remains unresolved.

**Independent review:** Required.

### M40-WP3 — Definition, Method, and Applicability Contracts

**Objective:** Specify Definitions, immutable Method Versions, requirements,
admission, and registry behavior.

**Dependencies:** WP2 approved.

**Deliverables:** Definition/Method contracts, requirement vocabulary,
method-admission gate, registry invariants, production-empty default.

**Likely files:** `M40_WP3_...md`; future `contracts.py` and `requirements.py`.

**Validation:** Immutability/fingerprint vectors; duplicate/moved-version
rejection; no Asset-type/provider fields.

**Exclusions:** Production method admission and runtime.

**Exit criteria:** Contracts independently conform to WP2.

**Independent review:** Required.

### M40-WP4 — Subject and Observation Input Manifest

**Objective:** Bind calculation to exact Assets, Definition Versions, and M39
Observation evidence.

**Dependencies:** WP2 and WP3 approved.

**Deliverables:** Subject/manifest contracts, canonical serialization,
equivalence/conflict dispositions, manifest identity.

**Likely files:** `M40_WP4_...md`; future `subjects.py` and
`input_manifest.py`.

**Validation:** One/multi-subject fixtures, ordering permutations,
equivalent duplicates, distinct conflicts, provider-leak checks.

**Exclusions:** Observation storage, providers, Registry mutation.

**Exit criteria:** Exact evidence reproduction from canonical fixtures.

**Independent review:** Required.

### M40-WP5 — Temporal, Unit, Adjustment, and Arithmetic Semantics

**Objective:** Close every determinism choice before executable methods exist.

**Dependencies:** WP3 and WP4 approved.

**Deliverables:** Cutoff/window, timezone/calendar, missing-data, unit/currency,
adjustment, decimal/rounding, and dependency specifications.

**Likely files:** `M40_WP5_...md`; future `temporal.py`, `units.py`, and
`decimal_math.py`.

**Validation:** Golden vectors for timezones, DST, interval edges, missing
data, units, precision, rounding, and dependency changes.

**Exclusions:** Implicit FX, default calendars, inferred adjustment.

**Exit criteria:** No ambient semantic default remains.

**Independent review:** Required numerical and architectural review.

### M40-WP6 — Result, State, and Provenance Model

**Objective:** Specify immutable results, state, reasons, and complete lineage.

**Dependencies:** WP3 through WP5 approved.

**Deliverables:** Measure Value, Computation Outcome, Calculation Temporal
Claim, Result, Provenance, result identity, deterministic outcome/degraded-state
interaction matrix, and reserved Snapshot boundary.

**Likely files:** `M40_WP6_...md`; future `results.py` and `provenance.py`.

**Validation:** Hash stability, no-value-on-failure, complete lineage,
canonical serialization round trips, `M34-D-0005` grammar completeness,
`UNAVAILABLE` reservation, and no presentation reinterpretation of either
outcome or Degraded State.

**Exclusions:** Persistence, Evaluation, confidence scoring.

**Exit criteria:** Every result is reproducible without a live provider or
current method lookup.

**Independent review:** Required.

### M40-WP7 — Frozen Registry and Applicability Resolver

**Objective:** Implement fail-closed discovery and exact-version resolution.

**Dependencies:** WP3 through WP6 approved and implementation-authorized.

**Deliverables:** Frozen registry, boot validation, applicability resolver,
test/production isolation, production-empty default.

**Likely files:** Future `registry.py` and `applicability.py`.

**Validation:** Duplicate/fingerprint/unknown-requirement rejection,
capability mismatch, forbidden Asset-type branches.

**Exclusions:** Asset Registry writes, providers, dynamic plugins.

**Exit criteria:** Invalid content cannot partially boot.

**Independent review:** Required.

### M40-WP8 — Pure Computation Kernel

**Objective:** Implement deterministic dispatch over supplied canonical values.

**Dependencies:** WP3 through WP7 approved and implementation-authorized.

**Deliverables:** Pure engine, deterministic dispatch, failure containment,
fixture-only methods, conformance corpus.

**Likely files:** Future `engine.py` and `backend/tests/market_measures/`.

**Validation:** Repeated invocation, permutations, cross-platform vectors,
dependency locks, missing/conflicting input, forbidden imports, no mutable
global state.

**Exclusions:** Network, ORM, current clock, providers, AI, Workspace,
Portfolio, recommendation, optimizer, execution, global cache.

**Exit criteria:** Identical canonical input bytes and versions produce
identical canonical result bytes.

**Independent review:** Required numerical and implementation review.

### M40-WP9 — Read-Only Integration and Adoption Design

**Objective:** Define, but do not bind, future service and Experience
projection contracts.

**Dependencies:** WP6 through WP8 approved.

**Deliverables:** Proposed service port, projection contract, availability and
degradation mapping, adoption gates, default-off plan, migration inventory.

**Likely files:** `docs/implementation/M40_WP9_...md` only.

**Validation:** Dependency direction, M38 compatibility, forbidden imports,
disable/rollback proof by design.

**Exclusions:** Endpoint, frontend, schema, scheduler, database, provider,
production caller.

**Exit criteria:** Future adoption can be reviewed without changing the core.

**Independent review:** Required.

### M40-WP10 — Conformance, Reconciliation, and Epic Closeout

**Objective:** Verify the approved corpus and authorized pure implementation.

**Dependencies:** Every admitted prior M40 work package.

**Deliverables:** Conformance/test reports, independent reviews, Index
reconciliation, Decision Log update only after approval, Graphify refresh at
the required point, and closeout only after every gate passes.

**Validation:** Focused/regression tests, forbidden imports, glossary/owner
consistency, no production binding, Markdown links, `git diff --check`.

**Exclusions:** Premature closeout or runtime adoption by implication.

**Exit criteria:** Independent constitutional and implementation approval with
no blocking finding.

**Independent review:** Mandatory.

---

## 11. Proposed Implementation Architecture

Every path in this section is illustrative and non-canonical.

### 11.1 Module layout

```text
backend/services/market_measures/
    __init__.py
    contracts.py
    subjects.py
    requirements.py
    input_manifest.py
    temporal.py
    units.py
    provenance.py
    results.py
    registry.py
    applicability.py
    engine.py
```

```text
backend/tests/market_measures/
    test_contracts.py
    test_manifest_identity.py
    test_applicability.py
    test_temporal_semantics.py
    test_decimal_conformance.py
    test_provenance.py
    test_registry.py
    test_engine_determinism.py
    test_dependency_boundaries.py
    fixtures/
```

### 11.2 Dependency direction

```text
Asset Foundation projection ─┐
                             ├─> manifest/applicability assembly
M39 Observation semantics ───┘              │
                                            ▼
                                    pure Market Measure core
                                            │
                                            ▼
                                  immutable Market Measure Result
                                            │
                              future read-only service adapter
                                            │
                              future Experience projection
```

The pure core must not import Registry repositories, ORM models, providers,
data fetchers, M39 HTTP handlers, Workspace/Portfolio services, AI agents,
scorers, optimizers, execution modules, database sessions, system time,
environment configuration, or mutable process-global caches.

### 11.3 Registry and runtime placement

The Market Measure Registry belongs under Market Intelligence, not Asset
Foundation's Definition Registry. It may consume an existing capability
projection but must not register Assets, alter Asset Definitions, create
analysis-specific grants, expose Asset types to the core, or dynamically load
code.

Domain contracts own meaning and identity. Runtime components only validate
supplied values, resolve an exact admitted version, evaluate requirements,
execute a pure method, and construct an immutable result. Custody transfers no
semantic ownership.

### 11.4 Persistence, API, and Workspace

M40 authorizes no persistence, API, or Workspace binding. A future store must
preserve complete immutable result identity and manifest reference. A cache is
disposable and never authoritative.

`AnalysisCache`, `AgentCache`, `RegimeSnapshot`, and `SignalHistory` are not
M40 migration targets.

A later adoption milestone requires realized canonical Observation inputs, an
admitted production method, a custody decision if history is needed,
authorization review, M38 projection conformance, default-off rollout and
rollback, and independent runtime review.

### 11.5 Version and rollout strategy

- stable Definition identity;
- immutable Definition revisions and Method Versions;
- pinned content fingerprints;
- new version for every semantic or dependency change;
- historical results bound to original versions;
- no dynamic `latest` during reproduction;
- production registry initially empty; and
- future production binding default-off and fail-closed.

Disabling a later binding must leave every M31–M39 behavior and stored record
unchanged.

---

## 12. Risks and Controls

| Risk | Required control |
| --- | --- |
| Equity assumptions enter core | No Asset type/symbol input; forbidden-token/import tests |
| Calculation becomes Judgment | Prohibit outlook, attractiveness, direction, signal, and action semantics |
| Provider payload enters core | Manifest accepts canonical M39 semantics only |
| Observation is mutated/reclassified | Measures are sibling objects referencing immutable identities |
| Reproducibility is lost | Content-addressed manifests and method/dependency digests |
| Version drift | Immutable versions, fingerprints, no mutable current formula |
| Provider preference is hidden | Explicit governed selection or conflict failure |
| Unit/currency mismatch | Typed units; no implicit FX |
| Time is misaligned | Explicit semantic time, cutoff, interval, timezone, calendar |
| Equity calendar is assumed | No default 252-session or weekday behavior |
| Adjustment is guessed | Explicit requirement; absent evidence fails |
| Missing data is silently filled | Versioned policy and golden vectors |
| Duplicates double-count | M39 Identity Equivalence-aware manifests |
| Conflicts are averaged | Conflict remains explicit absent governed selection |
| Float behavior changes output | Canonical decimal semantics and cross-platform vectors |
| Persistence becomes owner | No M40 storage; future stores have custody only |
| Workspace becomes owner | M38 read-only projection preserves source owner |
| Result appears actionable | Non-actionability invariant and judgment-vocabulary exclusion |
| Plugin behavior is unbounded | Declarative definitions; no dynamic code |
| Analytics words enter Asset definitions | Method Requirements remain separate |
| Plan implies Asset support | Applicability is per method, subject, definition, and evidence |
| Legacy analysis is promoted | Non-canonical inventory and no migration |
| Runtime authority appears implicitly | Empty production registry and no production caller |
| Composite Instrument Analysis returns | Market Intelligence owns only Calculated Market Measures |

---

## 13. Definition of Done

M40 may close only when:

1. Calculated Market Measure and adjacent terms are approved and registered.
2. M34-D-0004, M34-D-0005, and M34-D-0010 remain preserved and no Analysis
   domain exists.
3. Observation, Market Measure, portfolio measure, Investment Judgment, and
   Evaluation have mechanically testable boundaries.
4. Independent constitutional review expressly approves the RC-1 six-layer
   ownership proof and RC-2 Observation/Measure refinement before WP2 admits
   vocabulary.
5. Every concept has exactly one owner.
6. Definitions and Method Versions are immutable and fingerprinted.
7. Subjects use `asset_id`; no ticker/provider identity reaches the core.
8. Exact Asset Definition Versions and capabilities are in provenance.
9. Manifests reference exact M39 identities and meaning.
10. Every result carries Event Type `Calculation`, Producing Domain `Market
    Intelligence`, an explicit authoritative timestamp, and Degraded State
    under `M34-D-0005`.
11. Computation Outcome and Degraded State remain distinct, `UNAVAILABLE` is
    reserved for Degraded State, and their interaction is deterministic.
12. Temporal, unit, currency, adjustment, missing-data, conflict, precision,
   and rounding rules have no ambient defaults.
13. Non-success outcomes fabricate no required value.
14. Identical canonical inputs and versions produce byte-identical outputs.
15. The pure core has no network, database, provider, ORM, Workspace,
    Portfolio, AI, recommendation, optimizer, execution, environment,
    system-clock, or mutable-global dependency.
16. No production method is admitted accidentally.
17. No endpoint, schema, persistence, scheduler, UI, provider integration, or
    production consumer exists.
18. Legacy analysis objects remain explicitly non-canonical.
19. Conformance, golden-vector, boundary, negative, and determinism tests pass.
20. Independent constitutional review approves ownership and separation.
21. Independent implementation/numerical review approves reproducibility.
22. Decision Log and Index reconciliation occurs only at the approved point.
23. Graphify is refreshed at the required approved change/closeout point.
24. Closeout explicitly records the production-runtime authority state.

---

## 14. Provisional Successor View

This section is non-canonical and exists only to explain dependency order.

At most two successor families are presently justified:

1. **Canonical Observation Runtime and Historical Custody** — realization of
   the frozen M39 boundary, Observation history/manifests, retention, and
   replay under separate provider and storage authority.
2. **Market Measure Controlled Runtime Adoption** — admission of specific
   Method Versions and read-only exposure after canonical input availability,
   conformance evidence, and runtime authorization.

No successor is authorized by this proposal.

---

## 15. Recommended Review Sequence

1. Submit the corrected proposal and review response for independent
   architectural confirmation.
2. Resolve title, vocabulary, ownership, layer placement, Observation/Measure
   refinement, and temporal grammar before downstream specifications.
3. If explicitly approved, execute WP1 as a read-only corpus audit.
4. Submit WP2 for independent constitutional approval against all four
   correction exit criteria.
5. Do not begin implementation-bearing work until its explicit dependencies
   and authorities exist.
6. Keep the production registry empty and every integration seam inert through
   M40.

---

## 16. Current Disposition

```text
M39:                          COMPLETE AND FROZEN
M40 proposal:                 PROPOSED_FOR_ARCHITECTURAL_REVIEW
Independent review:           APPROVED_WITH_REQUIRED_CORRECTIONS
Required corrections:         RECONCILED_IN_PROPOSAL_PENDING_CONFIRMATION
M40 canonical authority:      NONE
M40 implementation authority: NONE
M40 runtime authority:        NONE
Production method authority:  NONE
Provider authority:           NONE
Persistence authority:        NONE
Public exposure authority:    NONE
Decision Log entry:           NONE
Epic closeout:                NONE
```

This document records an architectural assessment and milestone plan only. It
does not begin implementation, amend the Glossary, admit a production method,
modify a frozen milestone, or create authority by implication.
