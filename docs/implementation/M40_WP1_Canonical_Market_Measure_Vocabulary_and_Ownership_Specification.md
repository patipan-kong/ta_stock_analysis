# M40-WP1 — Canonical Market Measure Vocabulary and Ownership Specification

**Date:** 2026-07-23

**Milestone:** M40 — Canonical Asset Market Measure Foundation

**Document class:** Constitutional vocabulary and ownership specification

**Status:** `COMPLETE_FOR_WP2_CONSTITUTIONAL_ADMISSION_REVIEW`

**Canonical vocabulary admission:** `NONE`

**Implementation authority:** `NONE`

**Runtime authority:** `NONE`

**Production method authority:** `NONE`

**Provider authority:** `NONE`

**Persistence authority:** `NONE`

**API and public-exposure authority:** `NONE`

**Decision Log status:** `NOT_SUBMITTED`

**Supersedes:** `NONE`

**Closeout:** `NONE`

**Architecture phase:** Complete under the
[M40 architecture proposal](M40_Canonical_Asset_Market_Measure_Foundation_Plan.md),
[independent constitutional review](M40_INDEPENDENT_CONSTITUTIONAL_ARCHITECTURE_REVIEW.md),
[review response](M40_REVIEW_RESPONSE.md), and
[independent confirmation](M40_INDEPENDENT_CONFIRMATION.md).

**Document role:** Candidate constitutional vocabulary and mechanically
testable ownership contract submitted to M40-WP2 for admission review.

**Normative language:** `MUST`, `MUST NOT`, `SHALL`, `SHALL NOT`, `MAY`, and
`SHOULD` are normative within this specification. They constrain what WP2 may
consider for admission; they do not themselves admit vocabulary or authorize
implementation, runtime use, persistence, provider integration, an API, or a
production method.

---

## 1. Purpose

M40-WP1 specifies the candidate vocabulary and ownership boundary for Market
Measures. It establishes the constitutional foundation that every later M40
work package must preserve if, and only if, M40-WP2 independently admits the
candidate terms.

This specification defines:

- Market Measure;
- Calculated Market Measure;
- Computation Outcome;
- Calculation Temporal Claim;
- Producing Domain as specialized for M40 calculations;
- Observation Input Manifest;
- Market Measure Result;
- Input Sufficiency;
- Deterministic Calculation; and
- Mechanical Boundary Rules.

For every term, this specification records purpose, one semantic owner,
non-owners, permitted inputs, forbidden inputs, semantic meaning,
constitutional constraints, and future admission requirements.

M40-WP1 does not admit these candidate terms to the
[Canonical Glossary](../GLOSSARY.md), authorize their implementation, or
assert that any production method, runtime, provider, persistence mechanism,
or public interface exists.

## 2. Governing Authority

This specification is subordinate to repository authority. Where this
document conflicts with an approved or frozen authority, that authority
governs and the conflicting M40 candidate is inadmissible.

The governing corpus is:

- [Platform Architecture](../architecture/platform_architecture.md),
  especially sections 5, 6, 6.2, 6.5, 6.6, 6.7, 6.9, 11, and 12;
- [Canonical Glossary](../GLOSSARY.md), especially Canonical Temporal Claim,
  Event Type, Producing Domain, Degraded State, Market Observation,
  Investment Judgment, and Evaluation;
- [M34 Decision Register](m34/audit/registers/decision_register.md):
  `M34-D-0004`, `M34-D-0005`, and `M34-D-0010`;
- the complete, frozen M39 constitutional corpus:
  [WP1](M39_WP1_Canonical_Boundary_Specification.md),
  [WP2](M39_WP2_market_observation_source_boundary_specification.md),
  [WP3](M39_WP3_market_observation_classification_specification.md),
  [WP4](M39_WP4_market_observation_payload_specification.md),
  [WP5](M39_WP5_market_observation_relationship_specification.md),
  [WP6](M39_WP6_market_observation_identity_specification.md), and
  [Epic Closeout](M39_EPIC_CLOSEOUT.md);
- the approved M40 architecture-phase corpus linked in the status header.

### 2.1 Authority order

The following order SHALL resolve any apparent conflict:

1. repository constitution, approved Decision Register decisions, and
   Canonical Glossary;
2. frozen milestone specifications and closeouts;
3. independently approved M40 architecture direction;
4. this WP1 admission candidate; and
5. future M40 work-package proposals.

No lower item MAY reinterpret, weaken, or silently narrow a higher item.

### 2.2 Admission boundary

This document is complete as a WP1 deliverable, but its candidate vocabulary
is not canonical. M40-WP2 SHALL independently evaluate the complete term set
and its boundary proofs. Until WP2 expressly admits the set:

- no candidate term SHALL be added to the Canonical Glossary;
- no downstream artifact SHALL claim a candidate term is canonical;
- no schema, module, service, registry, adapter, endpoint, persistence model,
  or production method SHALL be justified by this document; and
- examples, names, states, and constraints in this document SHALL NOT be
  treated as runtime behavior.

## 3. Scope

M40-WP1 governs candidate semantic meaning, ownership, allowed source
categories, prohibited semantic dependencies, boundary predicates, and future
admission gates.

It does not govern:

- formulas, indicators, calculation methods, or method parameters;
- moving averages, RSI, MACD, or any named analytical technique;
- portfolio analytics or portfolio measurement;
- trading signals, forecasts, recommendations, or plans;
- software design or implementation;
- runtime evaluation, dispatch, scheduling, or orchestration;
- persistence, snapshots, retention, replay, or caching;
- provider adapters, provider selection, provider routing, or data retrieval;
- API, transport, endpoint, Workspace, or Experience composition;
- production registration, production callers, or method admission.

Mention of an input, output, state, or invariant specifies meaning only. It
does not prescribe a representation or executable process.

## 4. Frozen Ownership Baseline

| Semantic concern | Sole owner | M40-WP1 preservation rule |
| --- | --- | --- |
| Canonical Asset identity, definition, classification, and definition capability | Asset Foundation | Referenced without mutation or reinterpretation |
| External or source-reported Market Observation meaning | Market Intelligence under frozen M39 | Consumed only as exact frozen evidence; never recreated or reclassified |
| Market Measure and platform calculation meaning proposed by this specification | Market Intelligence | Candidate ownership only, subject to WP2 admission |
| Ledger events, holdings, transactions, lots, and accounting truth | Ledger & Accounting | Forbidden as Market Measure semantic inputs |
| Portfolio membership, performance, attribution, exposure, allocation, and portfolio risk | Portfolio Intelligence | Forbidden as Market Measure subjects, inputs, and output meaning |
| Outlook, expected direction, instrument risk judgment, consensus, recommendation, signal, and plan | Decision Intelligence | Forbidden as Market Measure output meaning |
| Correctness, reliability, quality, confidence-in-correctness, benchmark, and evaluator verdict | Trust & Evaluation | Never inferred from a result or computation outcome |
| Projection, interaction, composition, and presentation label | Experience Platform | No truth or ownership transfer; outside WP1 |
| Authentication, authorization, approval, and actor authority | Existing authority boundaries | Unchanged; never created by a result or specification |

Every semantic concept SHALL have exactly one owner. Custody, reference,
transport, display, storage, execution, or evaluation SHALL NOT create shared
ownership.

### 4.1 M39 preservation rule

A witnessed or provider-reported market statistic remains a Market
Observation represented under frozen M39 semantics with Canonical Temporal
Claim Event Type `Observation`. A statistic calculated by the platform is not
an M39 Observation Event; if admitted, it is a Calculated Market Measure with
Event Type `Calculation`.

Both forms remain Market Intelligence-owned market evidence. Neither form is
Investment Judgment. This distinction refines artifact provenance and Event
Type only. It SHALL NOT narrow, reopen, amend, or reinterpret the frozen
Market Observation meaning.

## 5. Uniform Term Record

Each candidate term in §6 uses the following fields:

| Field | Required interpretation |
| --- | --- |
| Purpose | The constitutional reason the concept exists |
| Owner | The sole semantic owner |
| Non-owner | Domains or mechanisms that may reference or carry the concept but cannot define or reinterpret it |
| Permitted inputs | Categories that may contribute to the concept's semantic claim |
| Forbidden inputs | Categories whose presence makes the candidate inadmissible to the M40 boundary |
| Semantic meaning | The exact claim made by the term |
| Constitutional constraints | Mechanically reviewable invariants that preserve repository authority |
| Future admission requirements | Evidence WP2 must accept before the term may become canonical |

“Permitted” means constitutionally eligible for future specification. It does
not mean available, implemented, supported, or authorized for runtime use.

## 6. Candidate Vocabulary

### 6.1 Market Measure

**Purpose:** Provide a bounded name for descriptive, non-judgmental market
meaning about one or more canonical Assets or an explicitly defined market
context.

**Owner:** Market Intelligence.

**Non-owner:** Asset Foundation, Ledger & Accounting, Portfolio Intelligence,
Decision Intelligence, Trust & Evaluation, Experience Platform, providers,
storage mechanisms, and runtime mechanisms.

**Permitted inputs:**

- exact frozen M39 Market Observation evidence;
- canonical Asset identity and exact Asset Definition references owned by
  Asset Foundation;
- explicit, measure-declared subject roles and invocation parameters; and
- explicit governed calculation dependencies when the measure is calculated.

**Forbidden inputs:**

- provider-shaped payloads or provider identity as semantic branches;
- ticker, display symbol, or provider symbol as canonical identity;
- Ledger events, transactions, holdings, tax lots, balances, or accounting
  state;
- Portfolio or Workspace membership, allocation, exposure, cash flow, or
  performance state;
- person, household, goal, plan, preference, or life context;
- judgment, forecast, recommendation, signal, consensus, or action intent; and
- evaluator verdicts, trust scores, correctness confidence, or quality
  rankings.

**Semantic meaning:** A Market Measure is a descriptive market fact whose
subject, inputs, and output meaning remain inside the mechanically testable
Market Intelligence boundary in §7. The term is an umbrella semantic category.
It does not make every externally reported value a platform calculation and
does not make every numerical value a Market Measure.

**Constitutional constraints:**

- It MUST describe an Asset or market condition, not a portfolio, person,
  household, goal, or plan.
- It MUST be evidence, not Investment Judgment.
- It MUST preserve the owner and meaning of every referenced input.
- It MUST NOT claim correctness, reliability, suitability, or actionability.
- If it represents a source-reported claim, frozen M39 Observation semantics
  govern.
- If it represents a platform calculation, §6.2 and Event Type `Calculation`
  govern.

**Future admission requirements:** WP2 MUST approve the umbrella term without
weakening the Canonical Glossary's Market Observation meaning, prove that the
term cannot absorb Portfolio Intelligence, Decision Intelligence, or Trust &
Evaluation meaning, and approve every §7 boundary predicate.

### 6.2 Calculated Market Measure

**Purpose:** Distinguish a platform-computed descriptive market fact from a
source-reported M39 Observation Event.

**Owner:** Market Intelligence.

**Non-owner:** M39 Observation sources, Asset Foundation, Ledger & Accounting,
Portfolio Intelligence, Decision Intelligence, Trust & Evaluation, Experience
Platform, providers, storage, and runtime custody.

**Permitted inputs:**

- an exact Observation Input Manifest;
- canonical Asset identity and exact Asset Definition references;
- explicit invocation parameters;
- an exact, future-governed calculation-definition and version reference; and
- an exact governed dependency declaration.

**Forbidden inputs:**

- any unmanifested or dynamically retrieved market input;
- source claims represented as if the platform had calculated them;
- ambient time, randomness, mutable process state, or an unresolved `latest`;
- all portfolio, ledger, life-context, judgment, evaluation, provider-control,
  and presentation inputs prohibited by §7.

**Semantic meaning:** A Calculated Market Measure is an immutable descriptive
market fact produced by a Deterministic Calculation from an exact Observation
Input Manifest under explicit semantic and dependency versions. It is a
platform calculation and therefore carries Event Type `Calculation`. It is
not an M39 Observation Event, Investment Judgment, Evaluation, or portfolio
measure.

**Constitutional constraints:**

- The result MUST satisfy all Market Measure constraints.
- Exact inputs, versions, dependencies, outcome, and temporal claim MUST be
  attributable.
- A non-success outcome MUST NOT fabricate a required measure value.
- Calculation MUST NOT transfer ownership of input evidence.
- Runtime custody or storage MUST NOT become semantic ownership.
- No named calculation method or production method is admitted by this term.

**Future admission requirements:** WP2 MUST approve the
Observation-versus-Calculation refinement, the Market Intelligence layer
placement, the deterministic identity implications, the non-success value
rule, and the negative boundary corpus before admitting this term.

### 6.3 Computation Outcome

**Purpose:** State whether the specified calculation completed and produced
its required semantic value without using quality, trust, or temporal
availability vocabulary.

**Owner:** Market Intelligence.

**Non-owner:** Trust & Evaluation, Experience Platform, providers, callers,
storage, and transport.

**Permitted inputs:**

- declared Input Sufficiency;
- whether every declared governed dependency is resolved;
- whether the valid calculation completed; and
- whether every required output coordinate is present.

**Forbidden inputs:**

- source popularity, provider ranking, trust score, correctness assessment,
  model confidence, or evaluator verdict;
- presentation labels or HTTP/transport status;
- portfolio suitability, expected direction, recommendation, or actionability;
- retry policy or operational availability; and
- an inferred Degraded State.

**Semantic meaning:** Computation Outcome is exactly one of:

| Candidate outcome | Meaning | Required-value rule |
| --- | --- | --- |
| `SUCCEEDED` | The declared calculation completed and every required output is present | Required value present |
| `INSUFFICIENT_INPUT` | The canonical supplied inputs do not satisfy the declared input prerequisites | Required value absent |
| `DEPENDENCY_UNRESOLVED` | A declared governed dependency needed for the calculation is unresolved | Required value absent |
| `FAILED` | A semantically valid and sufficiently supplied calculation did not complete | Required value absent |

**Constitutional constraints:**

- The outcome axis MUST remain distinct from Degraded State.
- `UNAVAILABLE` is reserved for the canonical Degraded State grammar and MUST
  NOT be a Computation Outcome.
- `SUCCEEDED` MUST NOT mean correct, trusted, current, suitable, recommended,
  or available through a runtime.
- Every non-success outcome MUST carry no required calculated value.
- A reason MAY explain an outcome but MUST NOT introduce judgment or
  evaluation meaning.

**Future admission requirements:** WP2 MUST approve the complete and closed
outcome set, the no-value-on-non-success rule, the separation from Degraded
State, and the separation from Trust & Evaluation before admission.

### 6.4 Calculation Temporal Claim

**Purpose:** Specialize the existing Canonical Temporal Claim grammar for a
Market Intelligence calculation without inventing a parallel clock or state
model.

**Owner:** Market Intelligence as the Producing Domain of the calculation.

**Non-owner:** Experience Platform, providers, callers, schedulers, caches,
storage, transport, and Trust & Evaluation.

**Permitted inputs:**

- the fixed Event Type `Calculation`;
- the fixed Producing Domain `Market Intelligence`;
- one explicit, calculation-defined authoritative timestamp whose meaning is
  declared by the future governed calculation specification; and
- one canonical Degraded State owned by Market Intelligence for the result.

**Forbidden inputs:**

- ambient system time;
- request, retrieval, receipt, cache, storage, render, or display time unless
  a higher authority separately defines that exact event as the calculation's
  authoritative timestamp;
- a presentation label such as “current” or “updated” in place of the complete
  temporal claim;
- provider freshness semantics silently reclassified as calculation time; and
- Computation Outcome used as Degraded State or vice versa.

**Semantic meaning:** A Calculation Temporal Claim is the complete
[Canonical Temporal Claim](../GLOSSARY.md#canonical-temporal-claim) for a
Calculated Market Measure. It contains Event Type `Calculation`, Producing
Domain `Market Intelligence`, an explicit authoritative timestamp, and one
canonical Degraded State.

**Constitutional constraints:**

- All four canonical fields MUST be present.
- Timestamp meaning MUST be explicit, deterministic, and version-bound.
- Market Intelligence MUST own the event, timestamp meaning, and Degraded
  State.
- Experience MAY later render the claim but MUST NOT derive or reinterpret it.
- Computation Outcome and Degraded State MUST remain orthogonal.
- Operational execution time, if a future runtime records it, MUST remain
  outside the result's authoritative semantic claim unless separately
  admitted.

**Future admission requirements:** WP2 MUST verify exact conformance to
`M34-D-0005` and the Canonical Glossary, approve the timestamp-meaning rule,
and approve the outcome/degraded-state separation before admission.

### 6.5 Producing Domain

**Purpose:** Identify the one constitutional domain that owns the calculation
event, its authoritative timestamp meaning, and its Degraded State.

**Owner:** Market Intelligence for every candidate M40 Calculation Temporal
Claim.

**Non-owner:** Asset Foundation, Portfolio Intelligence, Decision
Intelligence, Trust & Evaluation, Experience Platform, providers, runtime
custody, storage, and transport.

**Permitted inputs:**

- the semantic classification of the material event as a Market Intelligence
  calculation; and
- the owner decision already established by repository architecture and
  accepted through WP2 admission.

**Forbidden inputs:**

- module path, service name, deployment boundary, database owner, provider,
  caller, UI surface, or transport route;
- the owner of a referenced Asset or Observation;
- the domain that later evaluates or displays the result; and
- any dynamic or per-request owner selection.

**Semantic meaning:** Producing Domain is the existing canonical temporal field
defined by `M34-D-0005`. In the M40 candidate specialization its value is
always `Market Intelligence`, because Market Intelligence owns the calculation
event and its temporal qualification.

**Constitutional constraints:**

- The value MUST be fixed by semantic ownership, not implementation topology.
- It MUST NOT vary by provider, caller, subject type, or presentation.
- It MUST NOT transfer ownership of referenced Asset Foundation or M39
  evidence.
- It MUST NOT imply that Market Intelligence owns portfolio, judgment, or
  evaluation meaning.

**Future admission requirements:** WP2 MUST confirm the fixed value against
Platform Architecture §6.2, `M34-D-0005`, `M34-D-0010`, and the RC-1
layer/domain reconciliation before admitting the specialization.

### 6.6 Observation Input Manifest

**Purpose:** Bind a candidate calculation to the exact frozen M39 evidence it
uses without copying, mutating, fetching, or reclassifying that evidence.

**Owner:** Market Intelligence.

**Non-owner:** Observation sources, providers, Asset Foundation, Portfolio
Intelligence, Decision Intelligence, Trust & Evaluation, Experience Platform,
adapters, and storage.

**Permitted inputs:**

- immutable M39 Observation Identity references;
- canonical Observation Class and payload-meaning references;
- stable content digests;
- exact subject references;
- explicit Observation temporal claims, origins, relationships, and source
  qualifications needed to preserve meaning;
- explicit deterministic ordering; and
- an explicit semantic cutoff or measurement boundary when the future
  calculation specification requires one.

**Forbidden inputs:**

- live provider requests, adapters, SDK objects, provider response envelopes,
  or provider-specific field semantics;
- unversioned, mutable, or dynamically resolved observations;
- symbol lookup, search, resolver output, or provider routing;
- copied observation content that loses frozen identity or provenance;
- portfolio, ledger, judgment, evaluation, presentation, or authorization
  context; and
- an ambient default for ordering, time, timezone, currency, unit, adjustment,
  conflict, or missing-data meaning.

**Semantic meaning:** An Observation Input Manifest is an immutable, complete,
deterministically ordered evidence binding that enumerates the exact M39
Observation semantics selected as calculation inputs. It is evidence lineage,
not an Observation, provider request, persistence model, or permission to
retrieve data.

**Constitutional constraints:**

- Every input observation MUST retain its frozen M39 identity and meaning.
- Manifest membership MUST NOT create, correct, merge, or supersede an
  Observation.
- The manifest MUST be enumerable and canonically orderable.
- The manifest MUST NOT contain a dynamic `latest` reference.
- The manifest MUST NOT imply that referenced evidence exists in production.
- The manifest MUST NOT authorize storage, history, replay, or provider access.

**Future admission requirements:** WP2 MUST confirm preservation of all six
frozen M39 specifications, exact-reference semantics, ordering determinism,
provider neutrality, and the no-retrieval/no-persistence boundary before
admission.

### 6.7 Market Measure Result

**Purpose:** Provide one complete semantic record of a candidate calculation
invocation, including success or non-success, without fabricating values or
creating runtime authority.

**Owner:** Market Intelligence.

**Non-owner:** Asset Foundation, Portfolio Intelligence, Decision
Intelligence, Trust & Evaluation, Experience Platform, providers, callers,
runtime custody, and storage.

**Permitted inputs:**

- canonical subject references;
- an exact Observation Input Manifest reference;
- exact future-governed calculation-definition and version references;
- explicit invocation parameters and dependency references;
- Input Sufficiency;
- Computation Outcome;
- calculated values only when permitted by the outcome;
- complete Calculation Temporal Claim; and
- complete evidence lineage.

**Forbidden inputs:**

- unmanifested evidence or unresolved `latest` references;
- fabricated values for non-success outcomes;
- provider, transport, cache, database, or UI envelopes as semantic meaning;
- portfolio or ledger state;
- judgment, forecast, recommendation, signal, evaluator verdict, or quality
  score; and
- authorization, entitlement, approval, or action instructions.

**Semantic meaning:** A Market Measure Result is one immutable,
owner-explicit semantic outcome of applying one exact future-governed
calculation specification to one exact invocation and Observation Input
Manifest. It represents success and non-success without changing the meaning
of its inputs.

**Constitutional constraints:**

- It MUST have exactly one Market Intelligence semantic owner.
- It MUST identify exact subjects, inputs, semantic versions, dependencies,
  outcome, temporal claim, and lineage.
- It MUST contain required calculated values only for `SUCCEEDED`.
- It MUST NOT assert correctness, suitability, recommendation, or
  actionability.
- It MUST NOT imply persistence, public exposure, runtime availability, or
  production adoption.
- Identical canonical semantic inputs and versions MUST identify the same
  semantic result.

**Future admission requirements:** WP2 MUST approve the result boundary, the
one-owner rule, the complete lineage floor, the no-value-on-non-success rule,
and the separation from portfolio, judgment, evaluation, presentation, and
authority semantics.

### 6.8 Input Sufficiency

**Purpose:** Describe whether the exact supplied canonical inputs satisfy the
declared prerequisites of a future-governed calculation specification.

**Owner:** Market Intelligence.

**Non-owner:** Asset Foundation, providers, Portfolio Intelligence, Decision
Intelligence, Trust & Evaluation, Experience Platform, and runtime mechanisms.

**Permitted inputs:**

- the exact declared input prerequisites of the referenced future-governed
  calculation specification;
- exact subject and Asset Definition references;
- the Observation Input Manifest;
- explicit invocation parameters; and
- explicit dependency availability facts.

**Forbidden inputs:**

- correctness, reliability, reputation, confidence, or evaluator judgment;
- portfolio suitability or user preference;
- provider ranking or fallback policy;
- implicit defaults, heuristics, or best-effort substitution;
- a forecast, recommendation, or action objective; and
- a Degraded State treated as an automatic sufficiency result.

**Semantic meaning:** Input Sufficiency is the deterministic classification of
whether every declared prerequisite for the specified calculation is
satisfied by the exact supplied canonical inputs. It is `SATISFIED` only when
all declared prerequisites are satisfied; otherwise it is `INSUFFICIENT` with
at least one exact, future-governed reason. It does not assess whether an input
is true, high quality, useful, or suitable for action.

Input Sufficiency and M39-WP4 Semantic Sufficiency are distinct
Market Intelligence-owned concepts with different subjects and purposes.
Frozen Semantic Sufficiency governs whether an Observation Payload preserves
enough source-established meaning for the represented claim to be understood
in governed platform vocabulary. Candidate Input Sufficiency governs the
later and separate question of whether the exact canonical inputs supplied to
a specified calculation satisfy that calculation's declared prerequisites.
Input Sufficiency does not admit, amend, recompute, or reinterpret Semantic
Sufficiency. Where an Observation is supplied as a calculation input, its
M39 admissibility and frozen meaning remain prior authority; satisfying that
authority neither establishes nor is established by the calculation's Input
Sufficiency result.

**Constitutional constraints:**

- Sufficiency MUST be evaluated only against explicit declared prerequisites.
- Absence or conflict MUST NOT be repaired through an ambient default,
  provider fallback, input substitution, or fabricated value.
- `SATISFIED` MUST NOT imply `SUCCEEDED`, trusted, current, or correct.
- `INSUFFICIENT` MUST map to Computation Outcome
  `INSUFFICIENT_INPUT` and MUST prohibit required calculated values.
- Degraded State MUST remain a distinct qualification.

**Future admission requirements:** WP2 MUST approve the closed classification,
reason-code governance requirement, deterministic prerequisite rule, and
separation from capability, applicability, evaluation, and degraded state.

### 6.9 Deterministic Calculation

**Purpose:** Establish the reproducibility property required of every future
Calculated Market Measure without specifying a formula or implementation.

**Owner:** Market Intelligence.

**Non-owner:** providers, runtime frameworks, storage, schedulers, callers,
Experience Platform, and Trust & Evaluation.

**Permitted inputs:**

- exact canonical subjects and Asset Definition references;
- one exact Observation Input Manifest;
- explicit invocation parameters;
- one exact future-governed calculation-definition and version reference;
- exact declared dependency versions; and
- explicit semantic rules for time, ordering, units, precision, rounding,
  absence, conflict, and partiality.

**Forbidden inputs:**

- ambient clock, randomness, locale, timezone, environment configuration, or
  mutable process-global state;
- network, provider, database, cache, Workspace, Portfolio, or user-state
  lookups;
- dynamic code loading, provider branching, or an unresolved `latest`;
- implicit ordering, conversion, adjustment, rounding, missing-data, or
  conflict policy; and
- any judgment, evaluation, or action objective.

**Semantic meaning:** A Deterministic Calculation is a semantic transformation
for which identical canonical inputs, explicit parameters, semantic versions,
and dependency versions produce a byte-identical canonical Market Measure
Result, including outcome, reasons, values when permitted, and authoritative
temporal meaning.

**Constitutional constraints:**

- Every semantic dependency MUST be explicit and version-bound.
- No ambient or mutable input MAY influence the semantic result.
- Input order MUST be explicit or canonically determined.
- Failure and insufficiency MUST be deterministic results, not opportunities
  for implicit fallback.
- Reproducibility MUST NOT be represented as proof of correctness or trust.
- This property MUST NOT authorize any formula, library, engine, module, or
  production execution.

**Future admission requirements:** WP2 MUST approve the reproducibility
invariant, the complete forbidden-dependency set, the separation from Trust &
Evaluation, and the no-implementation-authority clause.

### 6.10 Mechanical Boundary Rules

**Purpose:** Supply falsifiable predicates for deciding whether a proposed
concept belongs inside the M40 Market Measure boundary.

**Owner:** Repository architecture governance.

**Non-owner:** Market Intelligence acting alone, every adjacent domain acting
alone, providers, implementations, storage, transport, and presentation.

**Permitted inputs:**

- the proposed concept's subject types;
- complete semantic input categories;
- exact output claim and vocabulary;
- claimed Producing Domain and Event Type;
- provenance and temporal requirements; and
- explicit negative-boundary evidence.

**Forbidden inputs:**

- implementation location, module name, current UI placement, database table,
  provider, caller, or team ownership as proof of semantic ownership;
- label similarity such as the words “measure,” “analysis,” “risk,” “return,”
  or “observation” without subject/input/output analysis;
- current runtime availability or historical implementation behavior; and
- approval inferred from silence, precedent, convenience, or this WP1 file.

**Semantic meaning:** Mechanical Boundary Rules are the complete
subject-input-output-event-owner predicates in §7 used by WP2 to classify each
candidate without discretionary ownership overlap.

**Constitutional constraints:**

- Every classification MUST produce exactly one owner or `INADMISSIBLE`.
- Failure of any required predicate MUST fail closed.
- The rules MUST preserve frozen M39 ownership and all adjacent-domain
  boundaries.
- No domain MAY self-authorize an exception.
- Only repository governance may approve a lower-level refinement.

**Future admission requirements:** WP2 MUST execute the rules against positive
and negative cases, resolve every collision, obtain independent constitutional
approval, and admit the rules together with the vocabulary or admit neither.

## 7. Mechanically Testable Ownership Rules

### 7.1 Market Intelligence admission predicate

A candidate qualifies for the M40 Market Measure boundary only when every row
is `PASS`.

| Predicate | Mechanical pass condition | Failure classification |
| --- | --- | --- |
| Subject | Every subject is a canonical Asset identity or explicitly defined market context | Outside M40; classify under the existing owner |
| Observation provenance | Every external market claim is an exact frozen M39 reference with preserved identity and meaning | `INADMISSIBLE` |
| Input category | Every semantic input is permitted by §6.1 and §6.2 | Route according to §7.2 |
| Output meaning | Output is descriptive Asset or market-condition evidence only | Route according to §7.2 |
| Event Type | Source-reported claim is `Observation`; platform calculation is `Calculation` | `INADMISSIBLE` |
| Producing Domain | Calculated result declares `Market Intelligence` | `INADMISSIBLE` |
| Temporal grammar | Complete canonical four-field claim is present in the specification | `INADMISSIBLE` |
| Determinism | No ambient input or unresolved semantic dependency exists | `INADMISSIBLE` |
| Judgment exclusion | No outlook, expected direction, recommendation, signal, consensus, or action meaning exists | Decision Intelligence |
| Evaluation exclusion | No correctness, reliability, trust, benchmark, or evaluator verdict exists | Trust & Evaluation |
| Portfolio exclusion | No Portfolio subject, membership, holding, transaction, cash flow, attribution, exposure, allocation, or performance meaning exists | Portfolio Intelligence |
| Wealth exclusion | No household, person, goal, net worth, obligation, protection, or life-plan meaning exists in the subject, inputs, or output claim | Wealth Intelligence |
| Authority exclusion | Result grants no authorization, approval, entitlement, execution, or transaction authority | Existing authority owner; `INADMISSIBLE` to M40 |

Passing this predicate means eligible for WP2 review only. It does not mean
admitted, supported, implementable, or authorized.

### 7.2 Fail-closed routing matrix

| Mechanically detected subject, input, or output meaning | Sole semantic owner | M40 disposition |
| --- | --- | --- |
| External witnessed or source-reported market claim | Market Intelligence under frozen M39 | Preserve as Observation input; do not recast as a calculation |
| Canonical Asset identity, classification, definition, or capability | Asset Foundation | Reference only; do not derive or mutate |
| Ledger event, transaction, lot, holding, balance, or accounting truth | Ledger & Accounting | Forbidden input; outside M40 |
| Portfolio membership, return, exposure, attribution, allocation, or portfolio risk | Portfolio Intelligence | Outside M40 |
| Household, person, goal, net worth, or life-plan meaning | Wealth Intelligence or other existing owner | Outside M40 |
| Outlook, expected direction, recommendation, trading signal, consensus, or action plan | Decision Intelligence | Outside M40 |
| Correctness, trust, reliability, quality score, benchmark, or evaluator verdict | Trust & Evaluation | Outside M40 |
| Rendering, interaction, composition, or presentation label | Experience Platform | Outside WP1; no semantic ownership transfer |
| Provider routing, retrieval, adapter behavior, or source selection | Existing provider/runtime boundary | Outside M40-WP1 |
| Authorization, approval, entitlement, execution, or transaction instruction | Existing authority boundary | Outside M40 |

### 7.3 Ownership non-overlap invariants

The following invariants are mandatory:

1. Market Intelligence owns candidate calculation meaning; it does not own
   referenced Asset identity or definition.
2. Market Intelligence preserves frozen M39 Observation meaning; it does not
   convert an Observation Event into a Calculation Event.
3. Portfolio Intelligence owns portfolio-derived meaning even when an output
   label resembles an Asset-level market measure.
4. Decision Intelligence owns interpretation and action-oriented conclusions
   even when they consume a Market Measure.
5. Trust & Evaluation owns evaluation even when it evaluates a Market Measure
   or Deterministic Calculation.
6. Experience Platform may later render an owner-explicit result but owns none
   of its business truth.
7. Runtime, provider, persistence, and transport custody never establish
   semantic ownership.

### 7.4 Boundary decision procedure

WP2 SHALL apply this sequence to every candidate term and every positive or
negative case:

1. identify every subject;
2. enumerate every semantic input category;
3. state the exact output claim without presentation language;
4. classify the event as external `Observation` or platform `Calculation`;
5. apply the fail-closed routing matrix;
6. verify the complete temporal grammar;
7. verify determinism and lineage constraints;
8. verify judgment, evaluation, portfolio, and authority exclusions; and
9. return exactly `ELIGIBLE_FOR_ADMISSION_REVIEW`, an existing sole owner, or
   `INADMISSIBLE`.

The procedure SHALL NOT return shared ownership.

## 8. Cross-Term Consistency

### 8.1 Required composition

If WP2 admits the vocabulary, a Calculated Market Measure SHALL be represented
semantically only through this composition:

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
  ├─ Calculation Temporal Claim
  │    ├─ Event Type: Calculation
  │    ├─ Producing Domain: Market Intelligence
  │    ├─ authoritative timestamp
  │    └─ Degraded State
  └─ complete lineage
```

This diagram is semantic and non-implementing. It defines no schema, control
flow, component, module, runtime, or persistence model.

### 8.2 Orthogonal classifications

| Classification | Question answered | Must not mean |
| --- | --- | --- |
| Input Sufficiency | Were every declared input prerequisite satisfied? | Correctness, quality, freshness, or success |
| Computation Outcome | Did the specified calculation complete with its required output? | Trust, recommendation, or Degraded State |
| Degraded State | How is the producing domain's temporal availability qualified? | Computation failure or evaluator verdict |
| Trust & Evaluation assessment | Is the result correct, reliable, or otherwise evaluated under a separately governed contract? | Market Intelligence-owned result meaning |

No value in one row MAY be inferred solely from a value in another row.

### 8.3 Terminology reservations

- `Observation` SHALL retain its frozen external/source-reported meaning.
- `Calculation` SHALL identify the platform calculation event.
- `UNAVAILABLE` SHALL remain a Degraded State and SHALL NOT become a
  Computation Outcome.
- `Analysis History`, `Investment Judgment`, `Consensus`, and
  `Instrument-Level Risk` SHALL remain Decision Intelligence vocabulary.
- `Evaluation` SHALL remain Trust & Evaluation vocabulary.
- `portfolio measure`, portfolio performance, attribution, exposure, and
  portfolio risk SHALL remain Portfolio Intelligence meaning.
- `Semantic Sufficiency` SHALL retain its frozen M39-WP4 meaning for
  Observation Payload preservation. `Input Sufficiency` SHALL apply only to a
  specified calculation's declared prerequisites and SHALL NOT substitute for,
  infer, amend, or reinterpret Semantic Sufficiency.
- “Canonical,” “result,” “measure,” or “deterministic” SHALL NOT imply
  admission, correctness, implementation, or production availability.

## 9. WP2 Admission Requirements

WP2 SHALL evaluate the ten candidate terms as one coherent boundary. It MUST
NOT admit a term whose omission or alteration would create an ownership gap,
overlap, or authority leak.

Admission requires independent constitutional approval that:

1. the layer/domain reconciliation preserves the Platform Architecture;
2. the Market Observation versus Calculated Market Measure refinement
   preserves frozen M39 and `M34-D-0010`;
3. the Calculation Temporal Claim and Producing Domain specialization conform
   exactly to `M34-D-0005`;
4. Asset Foundation, Portfolio Intelligence, Decision Intelligence, Trust &
   Evaluation, Experience Platform, provider, runtime, and authority boundaries
   remain exclusive;
5. every boundary rule is mechanically testable and fail-closed;
6. every term has exactly one semantic owner;
7. Input Sufficiency, Computation Outcome, Degraded State, and Evaluation are
   non-overlapping;
8. the candidate vocabulary creates no formula, implementation, runtime,
   persistence, provider, API, or production-method authority; and
9. positive and negative review cases produce no shared or ambiguous owner.

Until all nine conditions are expressly accepted, admission SHALL fail closed
and downstream reliance SHALL remain prohibited.

## 10. Authority Non-Leakage

This specification:

- creates no formula or indicator authority;
- admits no calculation method;
- creates no implementation design or production code authority;
- creates no runtime, scheduler, dispatcher, or orchestration authority;
- creates no provider, retrieval, adapter, routing, or fallback authority;
- creates no persistence, history, snapshot, replay, or cache authority;
- creates no API, endpoint, transport, Workspace, or public-exposure authority;
- creates no portfolio, judgment, evaluation, recommendation, execution,
  transaction, authorization, or approval authority; and
- does not amend the Decision Log, Canonical Glossary, frozen M39 corpus, or
  any other frozen milestone.

No statement in this document SHALL be used as authority to create a file
outside documentation or to alter runtime behavior.

## 11. WP1 Completion Criteria

M40-WP1 is complete for WP2 admission review only when:

1. all ten required terms contain every Uniform Term Record field;
2. each term has exactly one owner;
3. the M39 Observation boundary is preserved without amendment;
4. Market Intelligence, Portfolio Intelligence, Decision Intelligence, and
   Trust & Evaluation meanings are mechanically non-overlapping;
5. Producing Domain and Calculation Temporal Claim conform to `M34-D-0005`;
6. every forbidden-input category fails closed;
7. the complete candidate set creates no implementation, runtime, provider,
   persistence, API, or production authority;
8. all internal links and headings validate;
9. terminology and ownership consistency checks pass; and
10. the deliverable is submitted to WP2 without vocabulary admission.

Completion of these criteria means only
`COMPLETE_FOR_WP2_CONSTITUTIONAL_ADMISSION_REVIEW`.

## 12. Final Disposition

M40-WP1 supplies the candidate Canonical Market Measure vocabulary and
ownership specification required for independent WP2 evaluation.

The candidate owner of Market Measure semantics is Market Intelligence.
Frozen M39 Observation ownership, Asset Foundation identity authority,
Portfolio Intelligence meaning, Decision Intelligence judgment, and Trust &
Evaluation assessment remain unchanged and exclusive.

No candidate vocabulary is admitted by this document. No formula,
implementation, runtime behavior, provider integration, persistence, API,
production method, authorization, Decision Log entry, Graphify output, or
closeout is created or authorized.
