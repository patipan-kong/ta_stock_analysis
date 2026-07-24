# M41-WP3 Stage A — Vocabulary Sufficiency and Semantic Surface Register

**Document role:** Architecture and Specification Author

**Document class:** Specification-only governance artifact

**Milestone:** M41 — Governed Market Measure Semantics

**Work package:** M41-WP3 — Temporal, Unit, Adjustment, and Arithmetic
Semantics

**Internal stage:** Stage A — Vocabulary Sufficiency and Semantic Surface
Register

**M41 Architecture authority:** `COMPLETE`, `CONFIRMED`, `FROZEN` (cited,
not modified)

**M41-WP1 authority:** `COMPLETE`, `CONFIRMED`, `FROZEN` (cited, not
modified)

**M41-WP2 authority:** `COMPLETE`, `CONFIRMED`, `FROZEN` (cited, not
modified)

**M41-WP3 Architecture authority:** `APPROVED` (cited, not modified)

**Canonical vocabulary admission:** `NONE`

**Glossary synchronization required:** `NO`

**Implementation authority:** `NONE`

**Runtime authority:** `NONE`

**Provider authority:** `NONE`

**Persistence authority:** `NONE`

**API authority:** `NONE`

**Production-method authority:** `NONE`

**Date:** 2026-07-24

---

## 0. Executive Determination

The frozen vocabulary is sufficient for every semantic surface allocated to
M41-WP3.

1. **Measurement Window** is the sole WP3-governed noun needed by Stage B. It
   is reused exactly as confirmed by M41-WP1; Stage B will make its promised
   concrete contract mechanically complete without renaming or redefining
   it.
2. **Method Version** already supplies the single version-bound home for all
   method-governed WP3 semantic rules and the exact declared
   dependency-version list. No policy record and no Dependency Manifest is
   needed.
3. **Unit Semantics**, **Structural Event**, the frozen M39 Observation
   semantics, **Computation Outcome**, **Measure Subject**, **Observation
   Input Manifest**, and **Manifest Entry** are sufficient upstream or
   classification authorities and are cited without redefinition.
4. Temporal selection, timezone/calendar resolution, missing-data handling,
   density, interpolation, unit compatibility, currency compatibility,
   adjustment basis, arithmetic, canonical numeric encoding, dependency
   closure, semantic ordering, and processing order are ordinary normative
   rules or coordinates of the already-governed contracts. None establishes
   a distinct business identity, owner, lifecycle, or cross-contract object.
5. **Measure Value**, **Market Measure Result**, Provenance composition,
   Canonical Temporal Claim construction, reason representation, and the
   outcome/degraded-state matrix remain wholly deferred to M41-WP4.

Accordingly, Stage A discovers no `ADMIT` or `RENAME` candidate, makes no
Glossary change, and authorizes Stage B to use only the frozen vocabulary
and the ordinary-language classifications recorded here after this Stage A
artifact completes independent review and unconditional confirmation.

The Semantic Surface Register in §4 accounts for all nine components in
[the approved WP3 Architecture §4](M41_WP3_ARCHITECTURE_PROPOSAL.md#4-component-responsibilities).
The vector allocation in §5 accounts for every row in its minimum
golden-vector matrix. No ambient semantic default is accepted or supplied by
this Stage A determination.

---

## 1. Authority, Scope, and Non-Reopening Rule

### 1.1 Authority order

This register is subordinate, in order, to:

1. repository constitution, approved Decision Register decisions, and the
   Canonical Glossary;
2. frozen platform and Asset Foundation architecture;
3. frozen M34 decisions and the frozen M39 and M40 corpora;
4. the frozen M41 Architecture;
5. frozen M41-WP1;
6. frozen M41-WP2;
7. the approved M41-WP3 Architecture; and
8. this Stage A register.

Any conflict is resolved in favor of the higher authority. This register
does not reinterpret, correct, extend, or replace a frozen authority.

### 1.2 Exact Stage A allocation

Under
[M41-WP3 Architecture §9, Stage A](M41_WP3_ARCHITECTURE_PROPOSAL.md#wp3-stage-a--vocabulary-sufficiency-and-semantic-surface-register),
this document has exactly two purposes:

- prove before Stage B relies on a label that frozen vocabulary is
  sufficient; and
- inventory every determinism choice Stage B must close.

It therefore records:

- one row for each Component A–I;
- the governing frozen noun or ordinary-language classification;
- the exact owner and non-owner boundary;
- method-governed versus invocation-bound placement;
- exact upstream and downstream contract references;
- governed-dependency exposure;
- required golden-vector rows; and
- a candidate-vocabulary determination.

### 1.3 Explicit non-authority

This document does not:

- supply the normative Stage B contract;
- select concrete Measurement Window fields or canonical bytes;
- choose a missing-data, unit, adjustment, arithmetic, or processing-order
  rule for a production method;
- define a formula, indicator, Method Version, registry entry, or production
  method;
- change a WP1 or WP2 field, grammar, identity, ordering, serialization, or
  invariant;
- change an M39 Observation or its identity, payload, qualification, or
  provenance;
- define any WP4 Result, value, reason, lineage, temporal-claim, or state
  field;
- implement a service, resolver, calculation kernel, schema, test runner, or
  executable fixture; or
- authorize runtime, provider, persistence, API, catalog, or consumer
  behavior.

The production Definition/Method catalog remains empty.

### 1.4 Admission boundary

The vocabulary determination in this register is submitted for review; it
does not become a new vocabulary authority by self-assertion. If independent
review identifies a genuine governed noun, that noun cannot be used by
Stage B until it completes the frozen five-stage workflow: candidate record,
Independent Review, Required Corrections if any, unconditional Independent
Confirmation, and same-change synchronization.

No such candidate is found here. Therefore no candidate definition, owner
assignment, disposition request, or Glossary edit is emitted.

---

## 2. Evaluation Method

### 2.1 Governed-noun test

A label requires candidate treatment only if Stage B cannot be complete
without using it as a stable governed business concept that:

1. has semantic identity distinct from every existing canonical term;
2. needs a single owner not already supplied by an existing term;
3. is referenced across contracts as a thing rather than describing a
   field, value, rule, qualification, transformation, or validation
   condition; and
4. cannot be expressed without ambiguity through existing vocabulary plus
   ordinary normative contract language.

A label is not a candidate merely because Stage B must capitalize a heading,
encode a field, specify a closed value set, define exact arithmetic, or
version a rule. Mechanical precision does not create a separately governed
noun.

### 2.2 Placement test

Every semantic surface is assigned to one or both of these already-approved
layers:

- **Method-governed:** an immutable rule in the semantic specification
  denoted by the exact Method Version semantic version, with exact governed
  dependency identifiers and versions recorded through the existing Method
  Version dependency list where required.
- **Invocation-bound:** an explicit value supplied for one invocation,
  limited here to the concrete Measurement Window boundaries and applicable
  timezone/calendar reference, explicit parameters, and the already-resolved
  Subject and Manifest.

An invocation-bound value cannot override a Method Version rule. A
Method Version rule cannot synthesize an omitted invocation value from
ambient time, locale, configuration, provider convention, or `latest`.
“Invocation-bound” is an ordinary relationship classification; it does not
revive or admit a **Measure Invocation** noun.

### 2.3 Dependency test

A governed dependency may be required only when a calendar, named-zone rule
source, normalization facility, adjustment facility, interpolation facility,
or arithmetic facility can change semantic output. The existing Method
Version declared dependency-version list is the sole inventory for every
such dependency. “Calendar dependency,” “normalization dependency,” and
similar phrases describe entries in that existing inventory; they do not
name new M41 objects.

### 2.4 Ownership test

Every surface is checked against the frozen five-part boundary:

1. permitted subject;
2. permitted inputs;
3. descriptive output meaning only;
4. no Ledger, Portfolio, Workspace, or Wealth inputs; and
5. no judgment, recommendation, trust, evaluation, or suitability
   semantics.

The per-component result is recorded in §4. A failed part would block the
surface and could not be repaired by vocabulary admission.

---

## 3. Vocabulary Sufficiency Register

### 3.1 Reused governed vocabulary

| Governed term | Frozen home and owner | Exact WP3 use | Non-reopening constraint | Determination |
|---|---|---|---|---|
| Measurement Window | [WP1 Register §6.5](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md#65-measurement-window); Market Intelligence | Names the explicit invocation-bound input-selection boundary whose concrete record, identity, and bytes Stage B must specify | Not a Canonical Temporal Claim; not a Subject or Manifest field; does not redefine Observation time | `REUSE`; sufficient |
| Method Version | [WP1 Stage 2 §6](M41_WP1_DEFINITION_METHOD_VERSION_APPLICABILITY_CONTRACT_SPECIFICATION.md#6-method-version-contract); Market Intelligence | Existing semantic version denotes all method-governed WP3 rules; existing declared dependency-version list closes every output-affecting dependency | No new field, operand, policy record, or admitted production Method Version | `REUSE`; sufficient |
| Market Measure Definition | [WP1 Stage 2 §5](M41_WP1_DEFINITION_METHOD_VERSION_APPLICABILITY_CONTRACT_SPECIFICATION.md#5-market-measure-definition-contract); Market Intelligence | Supplies frozen subject-shape, permitted-input-category, and output-coordinate declarations | No WP3 field or meaning change | `REUSE`; sufficient |
| Method Requirement | [WP1 Stage 2 §7](M41_WP1_DEFINITION_METHOD_VERSION_APPLICABILITY_CONTRACT_SPECIFICATION.md#7-method-requirement-contract); Market Intelligence | Supplies frozen prerequisite categories, operands, grammar, and binary applicability result | WP3 conformance rules do not become new prerequisite categories or hidden operands | `REUSE`; sufficient |
| Measure Subject | [WP2 Stage B §4](M41_WP2_STAGE_B_SUBJECT_AND_MANIFEST_CONTRACT_SPECIFICATION.md#4-measure-subject-contract-specification); Market Intelligence | Supplies the already-valid subject bound to the calculation | No field, identity, shape, order, serialization, or ownership change | `REUSE`; sufficient |
| Observation Input Manifest | [WP2 Stage B §5](M41_WP2_STAGE_B_SUBJECT_AND_MANIFEST_CONTRACT_SPECIFICATION.md#5-observation-input-manifest-contract-specification); Market Intelligence | Supplies the immutable, resolved set of exact M39 evidence tested for WP3 conformance and semantically ordered without changing its bytes | No membership, identity, order, serialization, construction, or conflict repair | `REUSE`; sufficient |
| Manifest Entry | [WP2 Stage B §5.3](M41_WP2_STAGE_B_SUBJECT_AND_MANIFEST_CONTRACT_SPECIFICATION.md#53-manifest-entry-canonical-structure); Market Intelligence | Supplies one exact requirement-role/Observation-reference pair | No extra temporal, parameter, dependency, normalized, interpolated, or adjustment field | `REUSE`; sufficient |
| M39 Observation semantics and identity | Frozen M39 WP4/WP6; frozen M39 authority | Supplies source-established time, interval, precision, unit, currency, scale, basis, absence, qualification, and identity | No filling, correction, strengthening, merging, conversion, mutation, or reclassification | `REUSE`; sufficient |
| Unit Semantics | Asset Foundation; [Canonical Glossary](../GLOSSARY.md#unit-semantics) | Supplies declarative meaning of how an Asset kind is counted | WP3 specifies only calculation-side compatibility, rejection, or explicit normalization | `REUSE`; sufficient |
| Structural Event and Definition Version | Existing Asset Foundation/Lifecycle authorities | Bound adjustment rules and evidence without interpreting corporate actions or changing Asset definition meaning | No event inference, adjudication, creation, or Definition Version reclassification | `REUSE`; sufficient |
| Deterministic Calculation | Frozen M40; [Canonical Glossary](../GLOSSARY.md#deterministic-calculation) | Supplies the byte-identical determinism property Stage B must make satisfiable | No weakened or platform-specific meaning | `REUSE`; sufficient |
| Computation Outcome | Frozen M40; [Canonical Glossary](../GLOSSARY.md#computation-outcome) | Supplies `INSUFFICIENT_INPUT`, `DEPENDENCY_UNRESOLVED`, and `FAILED` classifications for WP3-detected conditions | No new outcome, reason model, Result envelope, or degraded-state rule | `REUSE`; sufficient |
| Measure Value and Market Measure Result | Frozen WP1/M40, allocated concretely to WP4 | Establish the downstream owner of successful value and Result composition | WP3 emits only canonical arithmetic output bytes for handoff; no Result/value field is defined here | `REUSE` by boundary reference; sufficient |
| Canonical Temporal Claim and Degraded State | M34-D-0005 and frozen Glossary | Establish the downstream temporal/state boundary | Measurement Window cannot substitute for either; WP3 constructs neither | `REUSE` by boundary reference; sufficient |

### 3.2 Ordinary-language semantic surface

| Surface language | Classification | Existing governed home or boundary | Why no candidate is required |
|---|---|---|---|
| cutoff, start/end edge, window kind, semantic time role, temporal selection, interval overlap, alignment, qualified time, semantic input ordering | Ordinary rules of Measurement Window use and Method Version semantics | Measurement Window + exact M39 temporal evidence | These choose how an existing window admits and orders existing evidence; they have no independent identity or owner |
| timezone identifier, fixed offset, timezone-free rule, named-zone rules, civil calendar, session calendar, DST gap/fold, holiday, early close, leap day | Ordinary temporal rule values; output-affecting facilities may be governed dependencies | Measurement Window + Method Version dependency list | Exact identifiers/versions are fields or dependency references, not new business objects |
| missing data, expected position, gap, duplicate, density, omission, interpolation, boundary/interior gap, maximum gap | Ordinary method-governed rules | Method Version semantics over immutable Manifest evidence | They describe conformance or mathematical treatment; derived working material is not an Observation |
| input type, unit compatibility/equality, scale/basis, currency compatibility, dimensionless ratio, percentage, rate, compound unit, normalization | Ordinary calculation-side rules reusing Unit Semantics | Unit Semantics + M39 qualifications + Method Version dependency list | They neither redefine Unit Semantics nor create a conversion object; implicit FX remains prohibited |
| raw, source-adjusted, economically continuous, calculation-normalized, adjustment factor, accepted input basis | Ordinary basis qualifications and transform rules bounded by Structural Event | M39 source basis + existing Structural Event authority + Method Version semantics | These distinguish existing/derived value states; no corporate-action or event authority is created |
| integer, decimal, exact rational, scale, precision, rounding mode, tie behavior, intermediate rounding, operation order, negative zero, exceptional number | Ordinary normative arithmetic and encoding rules | Method Version semantics; WP3-owned canonical numeric bytes | Exact numeric models and lexical forms are properties of the calculation contract, not governed business nouns |
| governed dependency, dependency identifier/version, dependency resolution, version mismatch | Ordinary reference and conformance language | Existing Method Version declared dependency-version list | The inventory and identity home already exist; a Dependency Manifest would duplicate them |
| processing order, non-commutative pipeline, failure classification | Ordinary orchestration and classification rules | Method Version semantics + frozen Computation Outcome | They relate existing semantic dimensions and outcomes; they do not create a Result or reason object |
| canonical serialization, canonical bytes, schema-version tag, identity, immutability, injectivity, round trip | Ordinary mechanical contract properties | Measurement Window and WP3-owned semantic coordinates | Mechanical precision of an existing noun does not create another noun |
| Semantic Surface Register, component, vector, fixture, acceptance gate | Ordinary governance/documentation language | This approved WP3 staging process | These are artifact and review labels, not domain vocabulary |
| invocation-bound value, explicit parameter | Ordinary placement language | Approved WP3 two-layer model and frozen four-category input closure | No runtime request object, service, or Measure Invocation noun is admitted |

### 3.3 Prohibited or deferred labels

| Label or semantic direction | Treatment | Reason |
|---|---|---|
| Dependency Manifest | Prohibited as a new noun | Fully covered by Method Version's existing dependency-version list |
| temporal policy, unit policy, rounding policy, adjustment policy | Prohibited as added Method Version fields or separately governed records | WP1 field set is frozen; the rules belong to the semantic specification denoted by its existing semantic version |
| Calculation Temporal Claim or renamed equivalent | Rejected/deferred boundary preserved | Measurement Window is an input-selection boundary; WP4 owns Result temporal composition under Canonical Temporal Claim |
| Producing Domain specialization | Prohibited | WP3 creates no temporal-claim or Result owner |
| FX rate, base currency, conversion policy | Not authorized | WP3 expressly prohibits implicit currency conversion and does not admit an FX facility |
| inferred adjustment, inferred Structural Event | Prohibited | Existing Structural Event authority is cited, never inferred or re-owned |
| reason code, partial result, Provenance composition, Result identity, outcome/degraded-state matrix | Deferred to WP4 | These are downstream Result concerns outside WP3 |
| formula, indicator, production method, registry, resolver, loader, kernel | Outside M41-WP3 authority | WP3 is specification-only and the production catalog remains empty |

### 3.4 Sufficiency proof

The inventory is sufficient because each Stage B semantic statement has an
unambiguous grammatical subject:

- if it specifies the concrete input-selection boundary, its subject is
  **Measurement Window**;
- if it specifies a calculation rule or output-affecting version choice, its
  subject is the exact **Method Version** semantic specification;
- if it examines evidence, its subject is an immutable M39 Observation
  referenced by a frozen **Manifest Entry** in an **Observation Input
  Manifest**;
- if it examines counting meaning, event meaning, or asset reference data,
  it cites **Unit Semantics**, **Structural Event**, or the applicable Asset
  Foundation authority;
- if it classifies non-success, it uses **Computation Outcome**; and
- if it would define a successful value, Result, temporal claim, reason,
  lineage, or degraded-state interaction, it stops at the WP4 boundary.

No residual semantic surface lacks a noun, no existing noun is forced to
carry a second meaning, and no surface needs independent ownership or
lifecycle. This is a tested sufficiency conclusion, not a predetermined
assumption.

---

## 4. Semantic Surface Register

The following is the authoritative Stage A inventory. “MG” means
method-governed; “IB” means invocation-bound. Vector identifiers refer to §5.

| Component | Determinism choices Stage B must close | Governing vocabulary / classification | Exact owner and non-owner boundary | Placement | Exact upstream contract | Exact downstream handoff | Governed dependency exposure | Required vectors | Candidate determination |
|---|---|---|---|---|---|---|---|---|---|
| **A — Measurement Window record and identity** | Exact field/cardinality model for start, end/cutoff, timezone/calendar reference, permitted absent start, boundary kinds/combinations, edge inclusion, schema version, field order, encoding, normalization, canonical bytes, identity, immutability, and rejection conditions | **Measurement Window** (`REUSE`); schema/identity/serialization language is ordinary contract language | Market Intelligence owns Measurement Window. M39 owns Observation time; WP2 owns Subject/Manifest; WP4 owns Result temporal claim. Host, provider, storage, cache, and presentation are non-owners | **MG:** permitted window kinds, edge/validation/serialization rules. **IB:** one concrete window and applicable explicit timezone/calendar reference | [WP1 Register §6.5](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md#65-measurement-window); [WP2 Manifest §5](M41_WP2_STAGE_B_SUBJECT_AND_MANIFEST_CONTRACT_SPECIFICATION.md#5-observation-input-manifest-contract-specification) | Exact Measurement Window identity and canonical bytes citable by WP4; no Canonical Temporal Claim construction | Conditional: named-zone/calendar source only when its version affects meaning; never ambient | `GV-01`, `GV-30`; canonical round-trip obligations shared with `GV-04` | `REUSE`; no candidate |
| **B — Cutoff, temporal selection, and ordering** | Inclusive Observation cutoff, role-specific M39 time meaning, observation/occurrence/effective/publication/reference-period distinction, interval inclusion/overlap, multi-role alignment, qualified-time compatibility, stable semantic order/tie-break, and fail-closed absence/ambiguity | Measurement Window + M39 Observation semantics; selection/order terms are ordinary Method Version rules | Market Intelligence owns calculation selection/order rules. M39 owns temporal evidence/identity. WP2 owns Manifest order and bytes. Providers and operational mechanisms are non-owners | **MG:** time role, cutoff treatment, overlap, alignment, order/tie-break, rejection. **IB:** concrete window and immutable Manifest supplied | Frozen M39 WP4/WP6; [WP2 Manifest §§5.3, 5.7](M41_WP2_STAGE_B_SUBJECT_AND_MANIFEST_CONTRACT_SPECIFICATION.md#53-manifest-entry-canonical-structure); [WP3 Architecture §4.2](M41_WP3_ARCHITECTURE_PROPOSAL.md#42-component-b--cutoff-temporal-selection-and-ordering) | Deterministically selected/ordered existing evidence and exact insufficiency classification; Manifest identity/order remain unchanged | Conditional only where alignment uses an exact calendar/zone dependency; M39 identity itself is not a WP3 dependency | `GV-02`, `GV-09`, `GV-10`; shares `GV-01` | Ordinary rules; no candidate |
| **C — Timezone, calendar, alignment, and DST** | Elapsed/civil/session/count basis, exact zone or fixed-offset/timezone-free rule, exact calendar or calendar-free rule, weekends/holidays/early closes/irregular sessions/leap days/boundaries, DST gaps/folds, alignment origin, truncation/extension | Measurement Window + Method Version dependency list; temporal facility labels are ordinary language | Market Intelligence owns calculation rules. Each governed dependency authority owns its semantic identity/version. Machine locale/timezone, exchange convention, provider, and runtime custody are non-owners | **MG:** basis, resolution, disambiguation, calendar/alignment rules and required versions. **IB:** explicit zone/calendar reference where applicable | [WP1 Method Version §6](M41_WP1_DEFINITION_METHOD_VERSION_APPLICABILITY_CONTRACT_SPECIFICATION.md#6-method-version-contract); [WP1 Measurement Window §6.5](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md#65-measurement-window) | Exact resolved temporal semantics and dependency versions; WP4 may cite but not infer them | **Yes** for named-zone databases/calendars when output-affecting; exact identifier/version mandatory. None for an explicitly fixed-offset or calendar-free rule | `GV-03`–`GV-08` | Existing nouns plus ordinary rules; no candidate |
| **D — Missing data and density** | Per-role reject/omit/exact-density/interpolate/independently-complete-coordinate choice; expected positions, gaps, duplicates, density basis, boundary/interior treatment, maximum gap, interpolation formula/endpoints/precision/rounding, omission denominator effect, outcome classification | Method Version semantics over Observation Input Manifest; missing-data/density/interpolation labels are ordinary rules | Market Intelligence owns calculation conformance/treatment. M39 owns evidence and absence. WP2 owns Manifest membership. WP4 owns partial-output/Result composition. Derived working material has no Observation ownership | **MG:** every treatment and formula. **IB:** supplied evidence and explicit parameters only; no override or invented evidence | [WP2 Manifest §§5.3–5.9](M41_WP2_STAGE_B_SUBJECT_AND_MANIFEST_CONTRACT_SPECIFICATION.md#53-manifest-entry-canonical-structure); frozen M39 absence/identity semantics; frozen WP1 Definition output-coordinate declaration | Canonical derived working values or existing `INSUFFICIENT_INPUT`; independently complete coordinate use only if frozen Definition and WP4 allow it | Conditional: interpolation facility only if version affects output; otherwise formula must be fully fixed in Method Version semantics | `GV-11`–`GV-14` | Ordinary rules; no candidate |
| **E — Units and currency** | Explicit numeric type/unit/scale/basis/currency, compatibility, equality versus normalization, dimensionless/percentage/rate/compound-unit rules, absent/incompatible/unresolved consequence, and multi-currency fail-closed rule | **Unit Semantics** (`REUSE`) plus M39 qualification and ordinary calculation-side rules | Asset Foundation owns Unit Semantics and Asset reference data. M39 owns source qualifications. Market Intelligence owns calculation compatibility/normalization acceptance. No owner is granted for implicit FX; Registry/provider/runtime cannot fill absence | **MG:** compatibility and any allowed normalization. **IB:** exact qualified evidence/parameters. No invocation override or inferred currency | Asset Foundation Unit Semantics; frozen M39 payload meaning; frozen four-category input closure; [WP1 Method Version §6](M41_WP1_DEFINITION_METHOD_VERSION_APPLICABILITY_CONTRACT_SPECIFICATION.md#6-method-version-contract) | Explicitly qualified canonical arithmetic inputs/output preparation or existing `INSUFFICIENT_INPUT` / `DEPENDENCY_UNRESOLVED`; no currency conversion | **Yes** when a normalization table/taxonomy/factor/algorithm affects output; exact version required. No implicit FX dependency permitted | `GV-15`–`GV-19` | `REUSE` Unit Semantics + ordinary rules; no candidate |
| **F — Adjustment and basis** | Raw/source-adjusted/economically-continuous distinction, accepted basis per role, basis incompatibility, exact evidence/dependencies, transform ordering, factor representation/decimal rules, and missing/ambiguous/conflicting/unresolved consequence | Existing **Structural Event** boundary + M39 basis qualifications; adjustment language is ordinary Method Version semantics | M39 owns source-reported basis. Existing Lifecycle/Structural Event authority owns event meaning. Market Intelligence owns calculation acceptance/transformation. Asset Foundation, provider convention, Registry, and price discontinuity cannot infer events or adjustment | **MG:** accepted basis, allowed transform, ordering, factor arithmetic, dependency/evidence requirements. **IB:** supplied exact evidence/parameters only | Frozen M39 basis/provenance; existing Structural Event and Definition Version authorities; [WP2 Manifest §5](M41_WP2_STAGE_B_SUBJECT_AND_MANIFEST_CONTRACT_SPECIFICATION.md#5-observation-input-manifest-contract-specification) | Attributable basis-qualified working values/canonical bytes or frozen non-success; no Observation/Event mutation and no WP4 Provenance composition | **Yes** when adjustment rules/factors/facilities are external output-affecting authorities; exact versions required | `GV-20`, `GV-21`; ordering also proven by `GV-29` | Existing boundary vocabulary + ordinary rules; no candidate |
| **G — Decimal, rational, and arithmetic semantics** | Canonical lexical forms/domains, negative zero, input/intermediate/output scale, precision, rounding/ties, intermediate-round locations, operation order, overflow/underflow/division-by-zero/invalid/domain behavior, zero/reduced rational encoding, NaN/infinity prohibition, canonical numeric bytes | Method Version + Deterministic Calculation; numeric/encoding language is ordinary normative contract language | Market Intelligence owns normative calculation arithmetic. WP4 owns Measure Value/Result serialization. Future implementation technology, language, platform, and math library custody are non-owners | **MG:** entire normative arithmetic model. **IB:** canonical numeric inputs/explicit parameters only | Frozen Deterministic Calculation; [WP1 Method Version §6](M41_WP1_DEFINITION_METHOD_VERSION_APPLICABILITY_CONTRACT_SPECIFICATION.md#6-method-version-contract); M39 numeric qualification | Exact canonical arithmetic output bytes or existing `FAILED`; no Measure Value or Result envelope | Conditional: arithmetic facility only if its version affects output; full rules must still be explicit. Binary floating point is never a semantic default | `GV-22`–`GV-26`, `GV-30`; shares `GV-14`, `GV-21`, `GV-29` | Ordinary normative rules; no candidate |
| **H — Governed dependency closure** | Facility exposure, exact identifier/version resolution, frozen ordering, absent/ambiguous/mismatched/unresolved behavior, prohibition of `latest`/environment/network/mutable configuration, identity effect of version change, custody/ownership distinction | **Method Version** declared dependency-version list (`REUSE`); dependency language is ordinary reference language | Method Version owns the exact reference list; each dependency authority owns its semantic identity/version; Market Intelligence owns fail-closed use rules. Registry, plugin, resolver, loader, package manager, network, and runtime custody are non-owners and unauthorized | **MG:** required dependency set, exact use, and failure rule. **IB:** none beyond already-explicit parameters; invocation cannot substitute a version | [WP1 Method Version §6](M41_WP1_DEFINITION_METHOD_VERSION_APPLICABILITY_CONTRACT_SPECIFICATION.md#6-method-version-contract); [WP3 Architecture §4.8](M41_WP3_ARCHITECTURE_PROPOSAL.md#48-component-h--governed-dependency-closure) | Exact dependency versions citable by WP4 and existing `DEPENDENCY_UNRESOLVED` when resolution fails | **Intrinsic:** this component closes every conditional exposure from C–G through the one existing list; it creates no dependency mechanism | `GV-17`, `GV-27`, `GV-28`; dependency bytes participate in `GV-30` | `REUSE` Method Version; Dependency Manifest remains rejected; no candidate |
| **I — Cross-dimension order and failure classification** | One exact order across temporal selection, adjustment, unit normalization, missing-data treatment, arithmetic; non-commutative proof; total mapping of WP3 conditions to existing outcomes | Method Version rules + **Computation Outcome** (`REUSE`); pipeline/order language is ordinary | Market Intelligence owns calculation order and exact reuse of frozen outcomes. WP4 owns Result/reasons/value/temporal claim/state matrix. No runtime orchestrator, provider, or implementation gains semantic ownership | **MG:** processing order and classification. **IB:** only values already admitted by A–H | All upstream rows A–H; frozen Computation Outcome; [WP3 Architecture §4.9](M41_WP3_ARCHITECTURE_PROPOSAL.md#49-component-i--cross-dimension-order-and-failure-classification) | Canonical arithmetic bytes where semantically successful, or exactly `INSUFFICIENT_INPUT`, `DEPENDENCY_UNRESOLVED`, or `FAILED`; WP4 constructs the Result | No new kind; uses only exact dependencies already declared and resolved under H | `GV-25`, `GV-27`, `GV-29`, `GV-30`; classification also asserted in applicable negative vectors | `REUSE` Computation Outcome + ordinary rules; no candidate |

### 4.1 Five-part ownership-boundary gate

| Component | Permitted subject | Permitted inputs | Descriptive output meaning | Prohibited Ledger/Portfolio/Workspace/Wealth inputs | Prohibited judgment/evaluation semantics | Result |
|---|---|---|---|---|---|---|
| A | Exact WP2-valid Measure Subject via its bound Manifest | Explicit window values and frozen Manifest reference | Deterministic input-selection boundary | Excluded | Excluded | **Pass** |
| B | Same | Exact M39 temporal evidence and explicit window/rules | Deterministic evidence selection/order | Excluded | No provider priority or preferred source | **Pass** |
| C | Same | Explicit temporal parameters and governed dependencies | Deterministic civil/session/alignment meaning | Excluded | No convention or suitability judgment | **Pass** |
| D | Same | Exact M39 evidence, parameters, governed dependencies | Deterministic gap treatment/working material | Excluded | No quality ranking or best-effort judgment | **Pass** |
| E | Same | Exact M39 qualifications, Asset reference data, parameters, governed dependencies | Deterministic compatibility/normalization | Excluded | No preferred unit/currency/source judgment | **Pass** |
| F | Same | Exact M39 basis/evidence, Asset references, parameters, governed dependencies | Deterministic basis acceptance/transformation | Excluded | No event inference, recommendation, or source preference | **Pass** |
| G | Same | Canonical numeric evidence, parameters, governed dependencies | Deterministic arithmetic bytes/failure | Excluded | No correctness confidence or quality verdict | **Pass** |
| H | Same | Exact governed dependency identifiers/versions | Deterministic dependency closure | Excluded | No package/source preference or trust score | **Pass** |
| I | Same | Outputs of conforming A–H stages only | Deterministic processing/classification | Excluded | No new verdict beyond frozen outcome meaning | **Pass** |

All nine components pass. This gate verifies allocation eligibility only.
Stage B must still provide its architecture-required field-by-field gate
table; this Stage A result does not pre-approve unwritten fields.

---

## 5. Required Golden-Vector Allocation

Stage A allocates the complete minimum vector matrix; it does not supply
normative vector bytes. Stage B may use more than one fixture for a row and
may reuse a fixture across rows, but it may not omit a row or collapse
materially different risks into a vague example.

Each Stage B vector must record exact canonical input bytes, exact expected
canonical output bytes or exact rejection/outcome classification, the rule
under test, every semantic and dependency version, a short independently
reproducible derivation, and an explicit non-production/no-admission
statement.

| ID | Required vector row | Primary component(s) | Required Stage B proof |
|---|---|---|---|
| `GV-01` | Window start edge | A, B | Exact lower-bound inclusion/exclusion |
| `GV-02` | Inclusive cutoff | B | Evidence at cutoff follows the declared rule; later evidence cannot participate |
| `GV-03` | Elapsed-duration vs civil-calendar window | C | Same apparent dates intentionally resolve differently |
| `GV-04` | Timezone independence | A, C | Different host timezones produce identical canonical semantics |
| `GV-05` | DST gap | C | Nonexistent local time is rejected or resolved by the sole explicit rule |
| `GV-06` | DST fold | C | Repeated local time is explicitly disambiguated |
| `GV-07` | Calendar holiday / early close | C | Exact named calendar version, not weekday/exchange default, controls behavior |
| `GV-08` | Leap day / period alignment | C | Exact boundary, origin, and alignment behavior |
| `GV-09` | Date-only or approximate M39 time | B | No stronger precision or instant is fabricated |
| `GV-10` | Semantic ordering permutation | B | Presentation/Manifest order cannot alter semantic input order or Manifest bytes |
| `GV-11` | Boundary missing data | D | Exact reject/omit/interpolate consequence |
| `GV-12` | Interior missing data / density | D | Exact expected-position and gap rule |
| `GV-13` | Prohibited fill | D | Undeclared forward/zero/nearest fill is rejected |
| `GV-14` | Interpolation | D, G | Formula, endpoints, precision, rounding, and exact bytes; no Observation invented |
| `GV-15` | Compatible unit | E | Exact comparison/combination succeeds |
| `GV-16` | Incompatible unit | E, I | Deterministic non-success classification |
| `GV-17` | Unit normalization dependency | E, H | Exact dependency version controls normalization |
| `GV-18` | Missing currency | E | No Registry/provider/default currency is inferred |
| `GV-19` | Multi-currency | E | Failure unless currency-invariant or separately normalized evidence is explicit |
| `GV-20` | Raw vs adjusted | F | Basis mismatch cannot silently normalize |
| `GV-21` | Explicit adjustment | F, G | Exact evidence, factor, transform order, precision, and dependency versions reproduce bytes |
| `GV-22` | Decimal tie | G | Exact rounding mode and tie behavior |
| `GV-23` | Intermediate rounding | G | Rounding is prohibited or occurs only at each exact declared location |
| `GV-24` | Negative zero | G | Canonical normalization or rejection |
| `GV-25` | NaN/infinity | G, I | Exceptional numbers cannot become successful semantic output |
| `GV-26` | Divide by zero / domain error | G, I | Exact `FAILED` classification |
| `GV-27` | Dependency unresolved | H, I | Exact `DEPENDENCY_UNRESOLVED` classification |
| `GV-28` | Dependency version change | H | Version change alters Method Version identity and, where applicable, expected bytes |
| `GV-29` | Non-commutative pipeline | F, G, I | The exact transform order is proven with values for which reordering changes output |
| `GV-30` | Cross-platform canonical bytes | A, G, H, I | Independent reconstruction and recomputation produce byte-identical output |

### 5.1 Coverage determination

- Components A–I each own at least one primary vector obligation.
- Every required architecture vector row appears exactly once in the matrix
  above.
- Dependency versioning is exercised both within a semantic dimension
  (`GV-17`, `GV-21`) and at dependency-closure level (`GV-27`, `GV-28`).
- Cross-dimension ordering is not left to the single abstract assertion in
  Component I: `GV-14`, `GV-17`, `GV-21`, `GV-23`, and `GV-29` collectively
  expose interpolation, normalization, adjustment, rounding, and pipeline
  interactions. This implements the Architecture Review's non-blocking
  advisory without changing the approved minimum.
- Frozen outcome meanings are tested through dimension-specific rejection
  vectors and explicitly through `GV-26` and `GV-27`; no Result or reason
  envelope is implied.

---

## 6. Upstream and Downstream Contract Trace

| Contract boundary | Stage A finding | Stage B constraint |
|---|---|---|
| WP1 Market Measure Definition | Closed and sufficient | Cite declared subject subset, output-coordinate meaning, and permitted input categories; add no field |
| WP1 Method Version | Closed and sufficient | Bind all method-governed rules to its existing semantic version and all exact dependencies to its existing dependency-version list |
| WP1 Method Requirement | Closed and sufficient | Add no prerequisite category, operand, temporal/unit/density/currency/adjustment grammar, or non-binary result |
| WP2 Measure Subject | Closed and sufficient | Receive one valid Subject; Measurement Window remains external and adds no Asset Definition Version |
| WP2 Observation Input Manifest / Manifest Entry | Closed and sufficient | Receive one resolved immutable Manifest; do not change membership, identity, canonical order/bytes, fields, or conflict result |
| Frozen M39 Observation | Closed and sufficient | Select/reject use only under explicit semantics; never strengthen, repair, merge, mutate, or fill source meaning |
| Asset Foundation / Lifecycle | Closed and sufficient | Cite Unit Semantics, Asset references, Definition Version, and Structural Event without ownership transfer or inference |
| Frozen M40 Deterministic Calculation | Closed and sufficient | Specify enough exact rules and bytes for independent byte-identical reproduction |
| Frozen M40 Computation Outcome | Closed and sufficient | Use only existing `INSUFFICIENT_INPUT`, `DEPENDENCY_UNRESOLVED`, and `FAILED` meanings for WP3-detected non-success |
| WP4 allocation | Deliberately not pulled forward | Hand off exact window, exact semantic/dependency versions, failure classification, and canonical arithmetic bytes only |

---

## 7. Compatibility and Negative-Corpus Determination

### 7.1 M34

- `M34-D-0004` is preserved: temporal, unit, and adjustment rules do not
  infer Asset identity or classification from provider-reported evidence.
- `M34-D-0005` is preserved: Measurement Window remains distinct from
  Canonical Temporal Claim; no Producing Domain specialization, temporal
  claim specialization, degraded-state token, or ambient clock is created.
- `M34-D-0010` is preserved: all surfaces remain descriptive calculation
  semantics, separate from portfolio meaning, judgment, evaluation,
  execution, and presentation.

### 7.2 M39

The register creates no competing Observation noun or derived-evidence
specialization. Observation identity, temporal qualification, unit,
currency, scale, basis, absence, uncertainty, and provenance remain
source-faithful. Value/timestamp/unit equality and arithmetic transforms
cannot merge identity-distinct Observations. Derived interpolation,
normalization, adjustment, and arithmetic material cannot enter the Manifest
or masquerade as witnessed evidence.

### 7.3 M40

The register preserves the four-category input closure, Deterministic
Calculation, explicit Measurement Window/cutoff, no host clock or locale,
explicit units and no implicit FX, basis distinctions and no inferred
adjustment, explicit arithmetic semantics, exact version-bound dependencies,
the four-value Computation Outcome closure, and the empty production
Definition/Method catalog.

### 7.4 WP1 and WP2

No WP1 field, identity coordinate, grammar, or disposition is reopened. No
WP2 Subject/Manifest field, identity, order, serialization, membership,
evidence count, or conflict consequence is reopened. Calculation semantic
ordering is a separate view over immutable entries and never reserializes
the Manifest.

### 7.5 Negative corpus

This register contains none of the following as an admitted or proposed
concept:

- Calculation Temporal Claim or a renamed equivalent;
- a specialized Producing Domain;
- Dependency Manifest;
- implicit FX, base currency, inferred unit, inferred adjustment, default
  timezone/calendar, weekday calendar, 252-session assumption, or dynamic
  `latest`;
- provider priority, provider-shaped payload fields, preferred evidence, or
  source-quality ranking;
- Ledger, Portfolio, Workspace, Wealth, judgment, recommendation, execution,
  evaluation, or presentation semantics;
- production formula, method, registry, resolver, kernel, endpoint, schema,
  persistence, provider, or runtime design; or
- an executable validation artifact.

---

## 8. Candidate-Vocabulary Determination

### 8.1 Determination

**No genuine governed vocabulary candidate is discovered.**

| Candidate question | Finding |
|---|---|
| Does any surface lack an existing governed noun? | No; §3.4 gives a complete subject for every Stage B statement |
| Does any ordinary label possess independent identity or lifecycle? | No; all are fields, rule choices, qualifications, transforms, encodings, validation conditions, or review labels |
| Does any surface require a new single owner? | No; ownership is singular under Measurement Window/Method Version, upstream frozen authorities, Computation Outcome, or deferred WP4 authority |
| Would a new policy/dependency noun improve semantic singularity? | No; it would split Method Version semantics or duplicate its dependency list |
| Is Measurement Window insufficient? | No; WP1 intentionally admitted it with the promise that WP3 would supply its exact timezone/calendar resolution and vectors |
| Must downstream Result language be pulled forward? | No; the WP4 handoff is complete without defining Result internals |

### 8.2 V1–V3 analysis

- **V1 — one term, one meaning, one home:** satisfied. Measurement Window,
  Method Version, Unit Semantics, Structural Event, Observation Input
  Manifest, Computation Outcome, and downstream WP4 terms retain distinct
  meanings and singular homes. No alias is proposed.
- **V2 — same-change synchronization:** not triggered. There is no
  `ADMIT`/`RENAME` disposition and therefore no Glossary synchronization.
- **V3 — constitutional terms reserved:** satisfied. Canonical Temporal
  Claim, Producing Domain, Observation Input Manifest, Unit Semantics,
  Computation Outcome, and other reserved terms are cited without
  redefinition or shadow specialization.

### 8.3 Overlap determination

The only close overlaps are deliberately resolved:

- Measurement Window versus Canonical Temporal Claim: input-selection
  boundary versus Result temporal claim;
- calculation-side unit rules versus Unit Semantics: compatibility and
  explicit normalization versus declarative counting meaning;
- calculation adjustment versus Structural Event: accepted/transformed
  basis versus event meaning and adjudication;
- semantic input ordering versus Manifest ordering: calculation view versus
  canonical identity/serialization order;
- governed dependency closure versus Dependency Manifest: existing Method
  Version list versus a prohibited duplicate noun; and
- canonical numeric bytes versus Measure Value/Result serialization:
  arithmetic handoff versus WP4-owned record composition.

None is a naming collision requiring `ADMIT`, `RENAME`, or `MERGE`.

### 8.4 Disposition and synchronization

| Item | Result |
|---|---|
| Candidate records required | `0` |
| `ADMIT` dispositions | `0` |
| `RENAME` dispositions | `0` |
| `MERGE` dispositions | `0` |
| `REJECT` dispositions newly issued | `0` |
| Existing vocabulary reused | Yes, exactly as recorded in §3.1 |
| Ordinary-language classifications retained | Yes, exactly as recorded in §3.2 |
| Glossary change | `NONE` |
| Candidate five-part gate | Not applicable; no candidate exists |
| Component five-part gate | All pass, §4.1 |

Because no candidate exists, the architecture's conditional candidate record
requirements—proposed definition, new owner, disposition request, full
Glossary overlap, and candidate-level five-part gate—are not activated.
Their absence is the consequence of the sufficiency proof, not an omitted
analysis.

---

## 9. Stage B Drafting Gate

After this Stage A artifact receives unconditional Independent Confirmation,
Stage B may proceed only under these controls:

1. use only vocabulary in §3.1 and ordinary language in §3.2;
2. do not capitalize ordinary surface labels in a way that implies a new
   governed noun;
3. do not add a field to any WP1 or WP2 record;
4. place every rule/value according to the MG/IB allocation in §4;
5. declare every output-affecting dependency through the existing Method
   Version dependency-version list;
6. satisfy every determinism choice in every Component A–I row;
7. supply every vector row in §5 with exact bytes and independent
   derivation;
8. include Stage B's own field-by-field five-part gate;
9. stop and route any unexpectedly necessary noun through the full frozen
   vocabulary workflow before relying on it; and
10. preserve implementation, runtime, provider, persistence, API, and
    production-method authority as `NONE`.

Stage A does not itself start Stage B. Stage B remains gated on independent
review, resolution of any required corrections, and unconditional
confirmation of this register.

---

## 10. Acceptance Checklist

| Requirement from approved WP3 Architecture Stage A | Evidence | Result |
|---|---|---|
| One row for every §4 component | §4, Components A–I | **Pass** |
| Governing frozen noun or ordinary-language classification | §3 and §4 column 3 | **Pass** |
| Exact owner/non-owner boundary traced to frozen authority | §3.1, §4 column 4, §4.1 | **Pass** |
| Method-governed versus invocation-bound placement | §2.2 and §4 column 5 | **Pass** |
| Exact upstream/downstream contract references | §4 columns 6–7 and §6 | **Pass** |
| Governed-dependency exposure | §2.3 and §4 column 8 | **Pass** |
| Required golden-vector rows | Complete 30-row allocation in §5 | **Pass** |
| Candidate-vocabulary determination | §8: no candidate, with V1–V3 and overlap analysis | **Pass** |
| No candidate relied upon before confirmation | No candidate exists; §1.4 and §9 preserve the stop gate | **Pass** |
| No frozen authority modified | This document only cites frozen authorities | **Pass** |
| No implementation or production authority introduced | Header, §1.3, §7.5, §9 | **Pass** |

---

## 11. Final Determination

Vocabulary sufficiency is proven for the complete M41-WP3 semantic surface.
All nine Stage B components have a singular governed home, explicit
owner/non-owner boundary, approved placement, exact contract trace,
dependency determination, and mandatory vector allocation.

No new governed noun is necessary. Measurement Window is reused as
confirmed; all other known WP3 phrases retain the frozen WP1 §6.0
classifications or cite existing upstream/downstream vocabulary. No Glossary
change is required.

This register is ready for independent review. It does not claim
unconditional confirmation and does not authorize Stage B to begin before
the approved gate is satisfied.

---

## Final Status

**READY FOR INDEPENDENT REVIEW**
