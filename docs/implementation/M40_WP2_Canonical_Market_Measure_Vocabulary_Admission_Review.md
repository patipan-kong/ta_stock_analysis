# M40-WP2 — Canonical Market Measure Vocabulary Admission Review

**Date:** 2026-07-23

**Milestone:** M40 — Canonical Asset Market Measure Foundation

**Document class:** Constitutional vocabulary admission review

**Status:** `COMPLETE_FOR_INDEPENDENT_CONSTITUTIONAL_REVIEW`

**WP2 admission review:** `COMPLETE`

**Candidate decisions:** `8_ADMIT_2_REJECT`

**Canonical Glossary effectiveness:** `PENDING_GLOSSARY_SYNCHRONIZATION_AND_INDEPENDENT_APPROVAL`

**Implementation authority:** `NONE`

**Runtime authority:** `NONE`

**Production method authority:** `NONE`

**Provider authority:** `NONE`

**Persistence authority:** `NONE`

**API and public-exposure authority:** `NONE`

**Decision Log status:** `NOT_SUBMITTED`

**Graphify refresh:** `NOT_PERFORMED`

**Supersedes:** `NONE`

**Closeout:** `NONE`

**Reviewed specification:** [M40-WP1 — Canonical Market Measure Vocabulary
and Ownership Specification](M40_WP1_Canonical_Market_Measure_Vocabulary_and_Ownership_Specification.md)

**WP1 governance state:** Complete and frozen following
[independent review](M40_WP1_INDEPENDENT_REVIEW.md),
[review response](M40_WP1_REVIEW_RESPONSE.md), and
[independent confirmation](M40_WP1_INDEPENDENT_CONFIRMATION.md).

**Independent review:** [APPROVED WITH REQUIRED
CORRECTIONS](M40_WP2_INDEPENDENT_CONSTITUTIONAL_REVIEW.md)

**Review response:** [M40-WP2 Review Response](M40_WP2_REVIEW_RESPONSE.md)

**Review reconciliation:**
`CORRECTIONS_RECONCILED_PENDING_INDEPENDENT_CONFIRMATION`

**Document role:** Binary constitutional admissibility determination for
every M40-WP1 candidate term. This document does not redesign WP1.

---

## 1. Purpose and Disposition

M40-WP2 applies the repository's canonical-vocabulary rules to the complete
ten-term candidate set defined by frozen M40-WP1. Every candidate receives
exactly one indivisible decision: `ADMIT` or `REJECT`.

The result is:

| Decision | Count | Candidates |
| --- | ---: | --- |
| `ADMIT` | 8 | Market Measure; Calculated Market Measure; Computation Outcome; Observation Input Manifest; Market Measure Result; Input Sufficiency; Deterministic Calculation; Mechanical Boundary Rules |
| `REJECT` | 2 | Calculation Temporal Claim; Producing Domain (M40 specialization) |

The two rejections do not reject, alter, or weaken the existing
[Canonical Temporal Claim](../GLOSSARY.md#canonical-temporal-claim) or
[Producing Domain](../GLOSSARY.md#producing-domain). They reject only
duplicate M40 names for value assignments already represented completely by
that canonical grammar.

The eight `ADMIT` decisions mean that WP2 finds the complete WP1 meanings
constitutionally necessary, unique, singly owned, and free of hidden
authority. They are admission determinations, not yet effective Glossary
registration. Platform Architecture V2 and `M34-D-0006` require new nouns to
be synchronized into the Canonical Glossary and independently approved before
downstream reliance. The user-directed scope of this work package expressly
excludes a Glossary edit. Therefore:

- the Canonical Glossary remains untouched;
- the eight admitted meanings are not yet effective shared vocabulary;
- no downstream work package may rely on them as effective canonical terms
  until the required synchronization and independent approval occur; and
- this document creates no implementation, runtime, provider, persistence,
  API, production-method, or authorization authority.

This fail-closed effectiveness boundary reconciles the requested admission
review with repository authority without changing WP1 or expanding M40.

## 2. Governing Authority and Review Method

### 2.1 Governing authority

This review is subordinate to:

1. [Platform Architecture](../architecture/platform_architecture.md),
   especially §§5, 6, 6.1, 6.2, 6.5–6.9, 7.1, 7.3, 7.4, 11, and 12;
2. [Canonical Glossary](../GLOSSARY.md), especially Canonical Temporal Claim,
   Event Type, Producing Domain, Degraded State, Market Observation,
   Investment Judgment, and Evaluation;
3. [M34 Decision Register](m34/audit/registers/decision_register.md),
   especially `M34-D-0004`, `M34-D-0005`, `M34-D-0006`, and `M34-D-0010`;
4. the complete frozen M39 corpus:
   [WP1](M39_WP1_Canonical_Boundary_Specification.md),
   [WP2](M39_WP2_market_observation_source_boundary_specification.md),
   [WP3](M39_WP3_market_observation_classification_specification.md),
   [WP4](M39_WP4_market_observation_payload_specification.md),
   [WP5](M39_WP5_market_observation_relationship_specification.md),
   [WP6](M39_WP6_market_observation_identity_specification.md), and
   [Epic Closeout](M39_EPIC_CLOSEOUT.md);
5. the approved M40 architecture corpus:
   [proposal](M40_Canonical_Asset_Market_Measure_Foundation_Plan.md),
   [constitutional review](M40_INDEPENDENT_CONSTITUTIONAL_ARCHITECTURE_REVIEW.md),
   [review response](M40_REVIEW_RESPONSE.md), and
   [independent confirmation](M40_INDEPENDENT_CONFIRMATION.md); and
6. the frozen [M40-WP1 specification](M40_WP1_Canonical_Market_Measure_Vocabulary_and_Ownership_Specification.md)
   and its completed review cycle.

Where a candidate cannot meet a higher authority without changing its WP1
meaning, the only permitted result is `REJECT`.

For Mechanical Boundary Rules, **Repository Architecture Governance** names
the existing non-domain governance apparatus established by:

- [Platform Architecture §11 — Architecture
  Governance](../architecture/platform_architecture.md#11-architecture-governance),
  which places Platform Architecture, domain constitutions, Architecture
  Decision Records, technical designs, implementation documentation, and
  source code in one repository precedence hierarchy and requires conflicts
  to be resolved upward;
- the [M34 Decision Register](m34/audit/registers/decision_register.md),
  whose active status identifies its records as approved post-WP5
  Architecture Review Board governance rulings and whose `M34-D-0004` through
  `M34-D-0010` records identify `ARB` as decision authority;
- the [M34 repository role
  appointments](m34/audit/reports/M34_ROLE_APPOINTMENTS.md), which appoint the
  Architecture Review Board acting as the sole board for this repository and
  separates governance roles by authority and procedure; and
- the frozen [M34 Authorization Gate
  Specification](m34/audit/reports/M34_WP6_authorization_gate_specification.md#3-authority)
  and [operating
  procedure](m34/audit/reports/M34_WP6_authorization_gate_operating_procedure.md#41-architecture-review-board),
  which establish the Architecture Review Board as the decision authority
  and sole gate decision authority for that governed gate.

The gate documents demonstrate the repository's constituted ARB mechanism;
they are not generalized here into authority over unrelated runtime or
production decisions. Repository Architecture Governance is therefore a
governance-level semantic owner under the §11 hierarchy, not a tenth business
domain under §6. It owns the cross-domain admission predicate and its
fail-closed routing rules; it owns no Asset, market, portfolio, wealth,
decision, evaluation, or experience fact.

### 2.2 Meaning of the binary decisions

`ADMIT` means the whole WP1 term record passes this constitutional
admissibility review without semantic alteration. It does not mean the term
is already registered, independently approved, implemented, exposed, or
available at runtime.

`REJECT` means the whole candidate term fails at least one mandatory
admission test. No part of the rejected candidate becomes canonical through
this review. Existing canonical vocabulary cited as the reason for rejection
remains fully effective and unchanged.

There is no conditional, partial, provisional, or semantic-subset admission.
The effectiveness gate that follows `ADMIT` is a repository-governance gate,
not a partial admission decision.

### 2.3 Mandatory admission tests

Each candidate is reviewed for:

- constitutional necessity and genuinely new meaning;
- inability to be represented by an existing canonical term;
- exactly one semantic owner;
- overlap with the Canonical Glossary, frozen M39, Asset Foundation,
  Portfolio Intelligence, Decision Intelligence, Trust & Evaluation,
  Experience Platform, and Wealth Intelligence;
- preservation of Platform Architecture, the M34 Decision Register, and
  frozen milestones; and
- absence of authority, implementation, runtime, provider, persistence, and
  API leakage.

Failure of necessity, uniqueness, or single ownership requires `REJECT`,
even when the candidate's proposed constraints are otherwise sound.

## 3. Whole-Set Constitutional Proof

### 3.1 Layer and domain reconciliation

| Concern | Governing owner or layer | WP2 finding |
| --- | --- | --- |
| Canonical Asset identity, definition, classification, and capability | Asset Foundation / Identity | Referenced only; never computed, mutated, or re-owned |
| Source-reported market fact | Market Intelligence / Observation | Remains a frozen M39 Market Observation with Event Type `Observation` |
| Platform-computed descriptive Asset or market-context fact | Market Intelligence / Observation | Eligible as Calculated Market Measure with Event Type `Calculation` |
| Ledger event, holding, lot, transaction, balance, or accounting truth | Ledger & Accounting / Truth | Excluded from every admitted Market Measure input and output |
| Portfolio return, exposure, attribution, allocation, performance, or portfolio risk | Portfolio Intelligence / Knowledge | Excluded; label similarity cannot transfer ownership |
| Person, household, goal, net worth, obligation, protection, or life plan | Wealth Intelligence / Knowledge widening | Excluded from subject, input, and output meaning |
| Outlook, expected direction, instrument-risk judgment, consensus, recommendation, signal, or plan | Decision Intelligence / Judgment | Excluded; calculated evidence does not become judgment |
| Correctness, reliability, benchmark, quality, calibration, or evaluator verdict | Trust & Evaluation / observer plane | Excluded; reproducibility and completion do not imply trust |
| Rendering, interaction, composition, and presentation labels | Experience Platform / Experience | May later render owner-explicit meaning but owns no result truth |

The admitted set creates no new domain and no ownership overlap. The only
non-domain owner is Repository Architecture Governance for Mechanical
Boundary Rules: the §11 architecture-governance hierarchy exercised through
the repository's constituted ARB mechanism, not a business fact owner or a
tenth §6 domain. This is one exact governance owner and does not give Market
Intelligence, the ARB, or an adjacent business domain semantic ownership of
the business facts routed by the predicate or authority to waive a
higher-level boundary.

### 3.2 Observation versus calculation proof

Frozen M39 governs attributable external or source-reported claims. M40 does
not recast them. A platform calculation instead:

- references exact frozen Observation identities and meanings;
- has Event Type `Calculation`, not `Observation`;
- keeps Market Intelligence as the sole owner of descriptive market meaning;
- preserves each input's source and temporal provenance;
- introduces no provider authority; and
- remains evidence, not Investment Judgment or Evaluation.

Market Measure is necessary as the bounded parent category spanning these two
provenance-distinct forms. Calculated Market Measure is necessary to name the
platform-computed form without broadening or silently reinterpreting Market
Observation.

### 3.3 Temporal and state proof

Every time-bearing calculated result must use the existing four-field
Canonical Temporal Claim from `M34-D-0005`:

| Canonical field | Required M40 value or rule |
| --- | --- |
| Event Type | `Calculation` |
| Producing Domain | `Market Intelligence` |
| authoritative timestamp | Explicit, calculation-defined, deterministic, and version-bound |
| Degraded State | One canonical state owned by Market Intelligence |

Computation Outcome remains orthogonal to Degraded State. In particular,
`UNAVAILABLE` remains a Degraded State and is not a Computation Outcome.

This proof also explains the two rejections. “Calculation Temporal Claim” is
fully expressible as a Canonical Temporal Claim with the values above.
“Producing Domain (M40 specialization)” is fully expressible by assigning
`Market Intelligence` to the existing Producing Domain field. Neither
specialization introduces a new noun or constitutional meaning.

### 3.4 M34 preservation proof

| Decision | Preservation finding |
| --- | --- |
| `M34-D-0004` | Asset classification remains Asset Foundation truth; Market Intelligence may consume exact references but cannot convert evidence into classification authority |
| `M34-D-0005` | The existing temporal grammar is reused exactly; no parallel temporal claim, event type, producing-domain concept, or degraded-state axis is admitted |
| `M34-D-0006` | Admission is term-specific; rejected duplicates remain excluded, and admitted terms remain ineffective until Glossary synchronization and independent approval |
| `M34-D-0010` | Market fact, judgment, instrument risk, evaluation, and presentation remain decomposed under their existing exclusive owners |

No Decision Register record is modified or superseded.

### 3.5 Authority non-leakage proof

The admitted meanings specify semantic classification only:

| Leakage category | Whole-set result |
| --- | --- |
| Authority | No term grants authorization, approval, entitlement, execution, transaction, or governance-waiver authority |
| Implementation | No schema, module, class, formula, library, engine, adapter, or production method is defined |
| Runtime | No dispatcher, scheduling, invocation, retrieval, fallback, retry, orchestration, or availability behavior is authorized |
| Provider | Providers remain witnesses; no provider identity, payload, routing, selection, or adapter becomes semantic authority |
| Persistence | No database, cache, snapshot, retention, history, replay, or serialization authority is created |
| API | No endpoint, transport, request, response, public type, Workspace contract, or exposure authority is created |

## 4. Candidate Admission Decisions

### 4.1 Market Measure — `ADMIT`

**Constitutional necessity:** A provenance-neutral parent category is needed
for descriptive Asset or market-context facts when the corpus must
distinguish source-reported Observations from platform calculations without
moving either outside Market Intelligence.

**Uniqueness:** Market Observation cannot represent the complete meaning
because frozen M39 restricts it to witnessed or source-reported claims.
Investment Judgment, portfolio measure, and Evaluation are deliberately
different substances. No existing Glossary term names the bounded parent
category.

**Sole semantic owner:** Market Intelligence.

| Admission criterion | Finding |
| --- | --- |
| Canonical Glossary overlap | New parent category; does not redefine Market Observation |
| M39 overlap | Includes M39 Observations by reference but preserves their complete frozen meaning |
| Asset Foundation overlap | Subjects use canonical Asset references; identity, definition, classification, and capability remain Asset Foundation-owned |
| Portfolio Intelligence overlap | Portfolio subjects and portfolio-derived meaning are forbidden |
| Decision Intelligence overlap | Outlook, expected direction, risk judgment, recommendation, signal, consensus, and action meaning are forbidden |
| Trust & Evaluation overlap | Correctness, reliability, trust, benchmark, and evaluator verdict are forbidden |
| Experience Platform overlap | Presentation may reference the term but cannot define or compute its meaning |
| Wealth Intelligence overlap | Person, household, goal, net-worth, obligation, protection, and life-plan meaning are forbidden |
| Authority leakage | None; descriptive evidence creates no approval or action authority |
| Implementation leakage | None; the umbrella defines no formula or implementation |
| Runtime leakage | None; it asserts no availability or execution path |
| Provider leakage | None; provider identity cannot branch semantic meaning |
| Persistence leakage | None; custody or storage cannot establish ownership |
| API leakage | None; no public or transport contract is defined |

**Decision rationale:** The whole WP1 term record introduces necessary,
non-overlapping constitutional meaning with one owner and passes every
mechanical exclusion. `ADMIT`.

### 4.2 Calculated Market Measure — `ADMIT`

**Constitutional necessity:** The corpus needs an exact name for a
platform-computed descriptive market fact that is not falsely represented as
a frozen M39 Observation Event.

**Uniqueness:** Market Observation denotes a witnessed or source-reported
claim. Canonical Temporal Claim describes provenance in time but not the
result's market meaning. No existing term expresses the conjunction of
platform calculation, descriptive market evidence, deterministic inputs, and
non-judgmental ownership.

**Sole semantic owner:** Market Intelligence.

| Admission criterion | Finding |
| --- | --- |
| Canonical Glossary overlap | New semantic kind; uses existing Event Type `Calculation` without redefining it |
| M39 overlap | Consumes exact Observation references but is never an Observation Event |
| Asset Foundation overlap | Uses identity and definition references without mutation or ownership transfer |
| Portfolio Intelligence overlap | Portfolio state, return, exposure, attribution, allocation, and risk are excluded |
| Decision Intelligence overlap | Evidence remains non-predictive and non-prescriptive |
| Trust & Evaluation overlap | Determinism and success do not claim correctness or reliability |
| Experience Platform overlap | Rendering and presentation labels remain downstream and non-authoritative |
| Wealth Intelligence overlap | Life-context subjects and inputs are excluded |
| Authority leakage | None; a calculated fact cannot authorize action |
| Implementation leakage | None; no named calculation method or formula is admitted |
| Runtime leakage | None; the term does not establish invocation or availability |
| Provider leakage | None; unmanifested retrieval and provider-shaped meaning are forbidden |
| Persistence leakage | None; immutability is semantic, not a storage mandate |
| API leakage | None; no endpoint or public representation is authorized |

**Decision rationale:** The term is the minimum new distinction required to
preserve the Observation/Calculation boundary established by M39 and
`M34-D-0010`. `ADMIT`.

### 4.3 Computation Outcome — `ADMIT`

**Constitutional necessity:** A closed semantic axis is needed to distinguish
successful completion, insufficient declared input, unresolved governed
dependency, and calculation failure without abusing Degraded State or
evaluation vocabulary.

**Uniqueness:** Degraded State qualifies temporal availability; Evaluation
assesses quality or correctness; transport status describes delivery. None
states whether the specified calculation completed with its required value.

**Sole semantic owner:** Market Intelligence.

| Admission criterion | Finding |
| --- | --- |
| Canonical Glossary overlap | New completion axis; explicitly excludes canonical Degraded State meanings |
| M39 overlap | Does not classify Observation validity, availability, or payload meaning |
| Asset Foundation overlap | Does not assess identity or capability |
| Portfolio Intelligence overlap | Does not assess portfolio calculations or portfolio state |
| Decision Intelligence overlap | Does not state suitability, outlook, recommendation, or actionability |
| Trust & Evaluation overlap | `SUCCEEDED` does not mean correct, trusted, or reliable |
| Experience Platform overlap | HTTP, UI, and presentation statuses cannot define the outcome |
| Wealth Intelligence overlap | Does not assess goals, plans, or life-level sufficiency |
| Authority leakage | None; no outcome value grants approval or permission |
| Implementation leakage | None; the closed meanings define no executable mechanism |
| Runtime leakage | None; retry and operational availability are forbidden meanings |
| Provider leakage | None; provider ranking and popularity cannot affect the axis |
| Persistence leakage | None; no recording mechanism is prescribed |
| API leakage | None; no status code or response mapping is authorized |

**Decision rationale:** The four-value record is admitted as one indivisible
semantic axis. Removing or merging a value would change WP1 and is not
permitted by this review. `ADMIT`.

### 4.4 Calculation Temporal Claim — `REJECT`

**Constitutional necessity:** The constraints are necessary, but a new term is
not. Every calculated result still requires a temporal claim.

**Uniqueness:** The candidate's complete meaning is exactly the existing
Canonical Temporal Claim with Event Type `Calculation`, Producing Domain
`Market Intelligence`, an explicit authoritative timestamp, and a canonical
Degraded State. Existing vocabulary represents it without loss.

**Proposed semantic owner:** Market Intelligence. Ownership is clear but does
not cure the uniqueness failure.

| Admission criterion | Finding |
| --- | --- |
| Canonical Glossary overlap | Complete duplication by value assignment to Canonical Temporal Claim |
| M39 overlap | Correctly differs from Observation temporal provenance, but existing Event Type already expresses that difference |
| Asset Foundation overlap | None; referenced subject ownership remains unchanged |
| Portfolio Intelligence overlap | None when the existing Producing Domain is Market Intelligence |
| Decision Intelligence overlap | None; Event Type `Analysis Generation` remains distinct |
| Trust & Evaluation overlap | None; Degraded State remains distinct from evaluation |
| Experience Platform overlap | Existing grammar already prevents presentation time from becoming authoritative |
| Wealth Intelligence overlap | None |
| Authority leakage | None in WP1, but duplicate vocabulary would weaken V1/V2 |
| Implementation leakage | None |
| Runtime leakage | None |
| Provider leakage | None |
| Persistence leakage | None |
| API leakage | None |

**Decision rationale:** V1 requires one term and one meaning, and V2 forbids a
private duplicate dialect. The candidate fails the mandatory
genuinely-new-meaning and cannot-be-represented tests. The phrase may appear
only as non-normative prose describing a Canonical Temporal Claim for a
calculation; it is not an admitted term of art. `REJECT`.

### 4.5 Producing Domain (M40 Specialization) — `REJECT`

**Constitutional necessity:** Every calculated result must declare its
Producing Domain, and for admitted M40 calculation meaning the required value
is Market Intelligence.

**Uniqueness:** Producing Domain is already canonical under `M34-D-0005`.
Fixing its value to Market Intelligence is an application of the existing
field, not new constitutional vocabulary.

**Proposed semantic owner:** Market Intelligence for the calculation event.
The existing term's meaning remains governed by `M34-D-0005`.

| Admission criterion | Finding |
| --- | --- |
| Canonical Glossary overlap | Exact existing term; M40 supplies only a fixed value |
| M39 overlap | Preserves Market Intelligence ownership for both Observation and Calculation events |
| Asset Foundation overlap | Asset reference ownership does not determine the Producing Domain |
| Portfolio Intelligence overlap | Portfolio calculations remain Portfolio Intelligence-produced and outside M40 |
| Decision Intelligence overlap | Judgment and analysis-generation events retain their existing producer |
| Trust & Evaluation overlap | Evaluation events retain their existing producer |
| Experience Platform overlap | Module, caller, UI, or renderer cannot select the producer |
| Wealth Intelligence overlap | Wealth-owned events remain outside M40 |
| Authority leakage | None in the fixed assignment, but a duplicate specialization would violate V1 |
| Implementation leakage | None; topology is explicitly irrelevant |
| Runtime leakage | None; no per-request owner selection exists |
| Provider leakage | None; provider cannot become Producing Domain |
| Persistence leakage | None; database ownership is irrelevant |
| API leakage | None; transport route is irrelevant |

**Decision rationale:** The required rule remains authoritative as
`Producing Domain = Market Intelligence`; only the proposed duplicate M40
specialization is rejected. No canonical term is changed. `REJECT`.

### 4.6 Observation Input Manifest — `ADMIT`

**Constitutional necessity:** A calculated result needs a provider-neutral,
immutable semantic binding to the exact frozen Observations it used. Mere
provenance on an individual Observation cannot name an invocation's complete,
ordered evidence set.

**Uniqueness:** M39 Observation Identity identifies one Observation and M39
relationships preserve source-established relations. Neither defines the
calculation-owned selection and deterministic ordering of multiple exact
Observation references.

**Sole semantic owner:** Market Intelligence.

| Admission criterion | Finding |
| --- | --- |
| Canonical Glossary overlap | New evidence-lineage composition; not an Observation or generic Provenance redefinition |
| M39 overlap | References all frozen identity, class, payload, source, relationship, and temporal meaning without copying or mutation |
| Asset Foundation overlap | Exact Asset subjects may be referenced but not resolved or adjudicated |
| Portfolio Intelligence overlap | Portfolio, ledger, allocation, and performance context are forbidden |
| Decision Intelligence overlap | Judgment and action context are forbidden |
| Trust & Evaluation overlap | Selection does not assert evidence quality or correctness |
| Experience Platform overlap | Workspace, UI selection, and presentation ordering cannot define membership |
| Wealth Intelligence overlap | Person, goal, plan, and life context are forbidden |
| Authority leakage | None; membership grants no permission to retrieve or act |
| Implementation leakage | None; manifest meaning defines no schema or class |
| Runtime leakage | None; live lookup, dynamic `latest`, and retrieval are forbidden |
| Provider leakage | None; adapters, SDK objects, routing, and provider-private semantics are forbidden |
| Persistence leakage | None; stable identity and digest do not authorize storage, history, or replay |
| API leakage | None; no request or response envelope is defined |

**Decision rationale:** The manifest supplies new invocation-lineage meaning
that existing single-Observation vocabulary cannot represent, while leaving
every referenced Observation frozen. `ADMIT`.

### 4.7 Market Measure Result — `ADMIT`

**Constitutional necessity:** The corpus needs one owner-explicit semantic
record for a calculation invocation that can represent success and
non-success without fabricating a required value.

**Uniqueness:** Market Observation represents a source claim; Canonical
Temporal Claim represents only temporal provenance; Computation Outcome
represents only completion. No existing term composes exact subject, manifest,
versions, dependencies, outcome, permitted value, temporal claim, and lineage.

**Sole semantic owner:** Market Intelligence.

| Admission criterion | Finding |
| --- | --- |
| Canonical Glossary overlap | New result composition; existing constituent terms retain their meanings |
| M39 overlap | Exact Observation inputs remain independently identifiable and unchanged |
| Asset Foundation overlap | Subject references remain Asset Foundation-owned |
| Portfolio Intelligence overlap | Portfolio and ledger state are forbidden |
| Decision Intelligence overlap | No forecast, recommendation, signal, or action meaning is permitted |
| Trust & Evaluation overlap | No correctness, quality, suitability, or evaluator verdict is permitted |
| Experience Platform overlap | Presentation and public exposure are outside the result meaning |
| Wealth Intelligence overlap | Life-context inputs and outputs are excluded |
| Authority leakage | None; a result cannot authorize execution or approval |
| Implementation leakage | None; the semantic composition is not a schema or method |
| Runtime leakage | None; the record does not imply a running producer |
| Provider leakage | None; provider envelopes cannot become result meaning |
| Persistence leakage | None; semantic immutability does not mandate storage |
| API leakage | None; no public type, endpoint, or transport is admitted |

**Decision rationale:** The complete WP1 record is a new constitutional
composition and is admitted without treating the two rejected shorthand terms
as dependencies: its temporal member is the existing Canonical Temporal Claim
with the fixed values in §3.3. `ADMIT`.

### 4.8 Input Sufficiency — `ADMIT`

**Constitutional necessity:** A deterministic calculation needs a
non-evaluative classification of whether its exact supplied inputs meet its
declared prerequisites, separate from completion and degraded state.

**Uniqueness:** Frozen M39 Semantic Sufficiency asks whether one Observation
Payload preserves enough source-established meaning. Input Sufficiency asks
whether the exact inputs supplied to a specified calculation satisfy that
calculation's declared prerequisites. Neither establishes the other.

**Sole semantic owner:** Market Intelligence.

| Admission criterion | Finding |
| --- | --- |
| Canonical Glossary overlap | New prerequisite axis; does not rename completeness, applicability, capability, or evaluation |
| M39 overlap | Semantic Sufficiency remains prior, frozen, payload-focused authority |
| Asset Foundation overlap | Asset references may be prerequisites, but the term does not assess identity or definition capability |
| Portfolio Intelligence overlap | Portfolio suitability and portfolio state are forbidden |
| Decision Intelligence overlap | User preference, forecast, recommendation, and action objectives are forbidden |
| Trust & Evaluation overlap | Truth, quality, reliability, reputation, and confidence are forbidden |
| Experience Platform overlap | UI readiness and presentation state cannot define sufficiency |
| Wealth Intelligence overlap | Goal or life-plan suitability cannot define sufficiency |
| Authority leakage | None; `SATISFIED` grants no permission or approval |
| Implementation leakage | None; prerequisite meaning defines no executable checker |
| Runtime leakage | None; fallback, best effort, and ambient defaults are forbidden |
| Provider leakage | None; provider ranking or substitution cannot repair insufficiency |
| Persistence leakage | None; reason semantics create no storage obligation |
| API leakage | None; no error or response mapping is defined |

**Decision rationale:** The WP1 reconciliation proves a different subject,
purpose, and authority sequence from M39 Semantic Sufficiency. The complete
two-value classification is unique and non-overlapping. `ADMIT`.

### 4.9 Deterministic Calculation — `ADMIT`

**Constitutional necessity:** Market calculations require a named
reproducibility property that excludes ambient state and binds every semantic
dependency without claiming correctness.

**Uniqueness:** The existing Glossary term Derivation applies to state
computed from the ledger. M40's term applies to descriptive market evidence
computed from exact Observation inputs and versioned semantics. General
ordinary-language determinism does not carry WP1's complete dependency and
result-identity contract.

**Sole semantic owner:** Market Intelligence.

| Admission criterion | Finding |
| --- | --- |
| Canonical Glossary overlap | New Market Intelligence calculation property; does not redefine Ledger Derivation |
| M39 overlap | Uses exact frozen Observation meaning and does not normalize or recalculate an Observation |
| Asset Foundation overlap | References exact identity and definition without mutation |
| Portfolio Intelligence overlap | Portfolio and ledger lookups are forbidden |
| Decision Intelligence overlap | Judgment, model opinion, and action objectives are forbidden |
| Trust & Evaluation overlap | Reproducibility does not prove correctness or trust |
| Experience Platform overlap | Locale, display settings, and Workspace state cannot influence the result |
| Wealth Intelligence overlap | Person, goal, and life context cannot influence the calculation |
| Authority leakage | None; reproducibility grants no decision or execution authority |
| Implementation leakage | None; no formula, library, engine, or module is authorized |
| Runtime leakage | None; clock, randomness, mutable global state, and dynamic loading are forbidden semantic inputs |
| Provider leakage | None; network calls and provider branching are forbidden |
| Persistence leakage | None; byte-identical canonical meaning does not prescribe storage or serialization machinery |
| API leakage | None; callers and transport cannot alter or expose the meaning by authority of this term |

**Decision rationale:** The property adds necessary Market
Intelligence-specific constitutional meaning not supplied by Ledger
Derivation or generic prose. `ADMIT`.

### 4.10 Mechanical Boundary Rules — `ADMIT`

**Constitutional necessity:** The Market Measure boundary requires a
falsifiable, fail-closed classification procedure. Without a named governed
rule set, label similarity or implementation placement could silently create
shared ownership.

**Uniqueness:** Platform Architecture supplies general domain laws, but no
existing canonical term names the complete M40 subject-input-output-event-
owner predicate set and its exactly-one-owner-or-inadmissible result.

**Sole semantic owner:** Repository Architecture Governance, meaning the
non-domain governance apparatus established by [Platform Architecture
§11](../architecture/platform_architecture.md#11-architecture-governance)
and exercised through the constituted Architecture Review Board mechanism
recorded in the [M34 Decision
Register](m34/audit/registers/decision_register.md), with the repository-level
appointment recorded in [M34 role
appointments](m34/audit/reports/M34_ROLE_APPOINTMENTS.md). The frozen M34
[gate authority](m34/audit/reports/M34_WP6_authorization_gate_specification.md#3-authority)
and [operating
procedure](m34/audit/reports/M34_WP6_authorization_gate_operating_procedure.md#41-architecture-review-board)
demonstrate that the ARB is the decision authority for its governed gate.
They do not make Repository Architecture Governance a business domain or
extend this admission review into implementation, runtime, or production
authority.

| Admission criterion | Finding |
| --- | --- |
| Canonical Glossary overlap | New bounded governance predicate; does not redefine a business-domain concept |
| M39 overlap | Makes preservation of every frozen Observation semantic a mandatory pass condition |
| Asset Foundation overlap | Routes identity, definition, classification, and capability to Asset Foundation |
| Portfolio Intelligence overlap | Routes portfolio-derived meaning to Portfolio Intelligence |
| Decision Intelligence overlap | Routes judgment and action meaning to Decision Intelligence |
| Trust & Evaluation overlap | Routes correctness and evaluation meaning to Trust & Evaluation |
| Experience Platform overlap | Rejects UI placement and presentation labels as ownership evidence |
| Wealth Intelligence overlap | Routes life-level subjects and meanings to Wealth Intelligence |
| Authority leakage | None; no domain may self-authorize an exception |
| Implementation leakage | None; source location and module names are forbidden ownership evidence |
| Runtime leakage | None; current behavior and availability are forbidden admission evidence |
| Provider leakage | None; provider and adapter placement are forbidden ownership evidence |
| Persistence leakage | None; database custody is forbidden ownership evidence |
| API leakage | None; caller and transport route are forbidden ownership evidence |

**Decision rationale:** This is a §11 governance-owned constitutional
predicate, not a new business domain or shared semantic owner. The ARB
records ground the repository governance mechanism that applies the
predicate; they do not transfer ownership of routed business facts to the
Board. Its complete fail-closed meaning is necessary and unique. `ADMIT`.

## 5. Coherence After the Two Rejections

WP1 required the candidate vocabulary to be evaluated as one coherent
boundary. Rejecting duplicate names must not create a semantic hole.

The coherent admitted composition is:

```text
canonical Asset references
          +
exact Observation Input Manifest
          +
explicit semantic and dependency versions
          ↓
 Deterministic Calculation
          ↓
Market Measure Result
  ├─ Input Sufficiency
  ├─ Computation Outcome
  ├─ value only when outcome permits
  ├─ Canonical Temporal Claim
  │    ├─ Event Type: Calculation
  │    ├─ Producing Domain: Market Intelligence
  │    ├─ authoritative timestamp
  │    └─ Degraded State
  └─ complete lineage
```

This is not a redesign. It preserves every semantic constraint from WP1 while
using the already-canonical names that V1 and V2 require. The candidate
“Calculation Temporal Claim” and the M40 specialization of “Producing Domain”
are omitted as terms because their complete meanings remain present through
the canonical grammar.

The composition is semantic only. It defines no schema, control flow,
formula, module, service, runtime, provider integration, persistence model,
or API.

## 6. Admission Register

| Candidate | Decision | Sole owner | New meaning test | Existing-term representation test | Effective now |
| --- | --- | --- | --- | --- | --- |
| Market Measure | `ADMIT` | Market Intelligence | Pass | Cannot be represented without losing the Observation/Calculation parent boundary | No |
| Calculated Market Measure | `ADMIT` | Market Intelligence | Pass | Cannot be represented by Market Observation without violating frozen M39 provenance | No |
| Computation Outcome | `ADMIT` | Market Intelligence | Pass | Not represented by Degraded State, Evaluation, or transport status | No |
| Calculation Temporal Claim | `REJECT` | Market Intelligence proposed | Fail | Fully represented by Canonical Temporal Claim with fixed values | No |
| Producing Domain (M40 specialization) | `REJECT` | Market Intelligence proposed | Fail | Fully represented by existing Producing Domain set to Market Intelligence | No |
| Observation Input Manifest | `ADMIT` | Market Intelligence | Pass | No existing term binds the complete ordered invocation evidence set | No |
| Market Measure Result | `ADMIT` | Market Intelligence | Pass | No existing term provides the complete result composition | No |
| Input Sufficiency | `ADMIT` | Market Intelligence | Pass | Distinct subject and purpose from M39 Semantic Sufficiency | No |
| Deterministic Calculation | `ADMIT` | Market Intelligence | Pass | Distinct from Ledger Derivation and generic prose | No |
| Mechanical Boundary Rules | `ADMIT` | Repository Architecture Governance | Pass | No existing term names the complete fail-closed M40 predicate | No |

“Effective now” is `No` for admitted terms solely because this scoped work
package does not modify the Canonical Glossary and has not yet received the
required independent approval. It is not a third decision state.

## 7. Frozen-Corpus and Scope Confirmation

This review confirms:

1. all ten WP1 candidates were reviewed exactly once;
2. every candidate has one binary and justified decision;
3. no candidate received partial semantic admission;
4. all admitted terms introduce genuinely new constitutional meaning;
5. no admitted term can be represented by existing canonical vocabulary
   without semantic loss;
6. every admitted term has exactly one owner;
7. existing Canonical Temporal Claim and Producing Domain vocabulary remains
   unchanged and supplies the two rejected specializations' required meaning;
8. Platform Architecture and `M34-D-0004`, `M34-D-0005`,
   `M34-D-0006`, and `M34-D-0010` remain preserved;
9. M39 remains complete, frozen, and unmodified;
10. WP1 remains complete, frozen, and unmodified;
11. no Canonical Glossary, Decision Log, Graphify output, closeout, or frozen
    milestone was modified;
12. no formula, indicator, method, implementation design, production method,
    or production code was created;
13. no runtime, provider, persistence, API, Workspace, public-exposure,
    authorization, approval, entitlement, execution, or transaction authority
    was created; and
14. no downstream reliance is authorized until Glossary synchronization and
    independent constitutional approval make the admitted vocabulary
    effective.

## 8. Final Disposition

M40-WP2 completes the constitutional admissibility review of the full frozen
WP1 candidate set.

Eight candidates are `ADMIT`: Market Measure, Calculated Market Measure,
Computation Outcome, Observation Input Manifest, Market Measure Result, Input
Sufficiency, Deterministic Calculation, and Mechanical Boundary Rules.

Two candidates are `REJECT`: Calculation Temporal Claim and Producing Domain
(M40 specialization). Both fail uniqueness only; their required constraints
remain fully represented by the existing Canonical Temporal Claim and
Producing Domain vocabulary.

This document is ready for independent constitutional review. Because the
Canonical Glossary is outside this task's authorized change set, none of the
eight admitted terms is yet effective shared vocabulary and no implementation
or runtime work is authorized.
