# M41-WP3 — Architecture Proposal

**Document role:** Architecture and Specification Author

**Document status:** `READY FOR INDEPENDENT ARCHITECTURE REVIEW`

**Proposal date:** 2026-07-24

**Milestone:** M41 — Governed Market Measure Semantics

**Work package:** M41-WP3 — Temporal, Unit, Adjustment, and Arithmetic
Semantics

**M41 Architecture authority:** `COMPLETE`, `CONFIRMED`, `FROZEN` (cited,
not modified)

**M41-WP1 authority:** `COMPLETE`, `CONFIRMED`, `FROZEN` (cited, not
modified)

**M41-WP2 authority:** `COMPLETE`, `CONFIRMED`, `FROZEN` (cited, not
modified)

**Implementation authority:** `NONE`

**Runtime authority:** `NONE`

**Provider authority:** `NONE`

**Persistence authority:** `NONE`

**API authority:** `NONE`

**Production-method authority:** `NONE`

---

## 0. Authority, Precedence, and Non-Reopening Rule

This proposal determines the architecture and internal implementation
sequence for M41-WP3 exactly within the allocation made by the frozen
[M41 Architecture](M41_ARCHITECTURE_PROPOSAL.md). It is subordinate, in
order, to:

1. the frozen platform and Asset Foundation architecture;
2. frozen M34 decisions and the frozen M39 and M40 corpora;
3. the frozen M41 Architecture;
4. frozen M41-WP1, including its candidate register, contract
   specification, confirmation chain, and closeout; and
5. frozen M41-WP2, including its confirmed architecture, confirmed Stage A,
   and confirmed Stage B contract specification.

If this proposal conflicts with a higher authority, the higher authority
governs and the conflicting clause is invalid.

M41-WP2 is complete. WP3 does not reopen, reinterpret, extend, correct, or
replace any WP2 decision. In particular, WP3 accepts as fixed:

- Measure Subject's three closed shapes, ownership, identity, ordering,
  canonical serialization, and immutability;
- Observation Input Manifest's exact M39-evidence-only membership, binding,
  identity, ordering, canonical serialization, and immutability;
- Manifest Entry's exact two-field structure and requirement-role meaning;
- M39 identity equivalence and identity distinctness;
- the fail-closed evidence-conflict consequence already fixed by WP2; and
- the separation of Asset Foundation reference data, invocation parameters,
  and governed calculation dependencies from Manifest membership.

WP3 consumes these contracts by exact reference. It does not insert an
intermediate WP2 stage or create a replacement WP2 summary authority.

---

## 1. Executive Determination

The complete architectural allocation of M41-WP3 is:

> Specify every temporal-selection, missing-data, unit/currency, adjustment,
> decimal/arithmetic, and governed-dependency semantic choice required to
> make a future Market Measure calculation deterministic, explicit,
> version-bound, and independently reproducible, and prove each choice with
> specification-only golden vectors until no ambient semantic default
> remains.

WP3 owns specification of:

1. the concrete Measurement Window contract;
2. cutoff, interval, timezone, calendar, alignment, qualified-time, and
   semantic input-order rules;
3. missing-data, density, omission, and explicit interpolation rules;
4. unit compatibility, unit normalization, currency compatibility, and the
   prohibition of implicit currency conversion;
5. raw, adjusted, and economically continuous input-basis distinctions and
   the prohibition of inferred adjustment;
6. canonical decimal/rational representation, scale, precision, rounding,
   exceptional-number, and intermediate-rounding rules;
7. the exact use and version closure of governed calculation dependencies;
8. deterministic classification of WP3-detected insufficiency, unresolved
   dependency, and arithmetic failure using only the already-frozen
   Computation Outcome meanings; and
9. byte-level canonicalization and golden-vector evidence for all WP3-owned
   semantic coordinates.

WP3 does not own:

- the meaning or fields of Market Measure Definition, Method Version, or
  Method Requirement (WP1);
- Subject or Manifest construction, identity, ordering, or serialization
  (WP2);
- M39 Observation meaning, identity, temporal precision, units, currency,
  absence, or source qualification (M39);
- Asset identity, Asset Definition, Definition Version, Unit Semantics, or
  Structural Event meaning (their existing owners);
- Measure Value, Market Measure Result, Result identity, Provenance
  composition, Canonical Temporal Claim construction, or the
  outcome/degraded-state interaction matrix (WP4);
- any formula, concrete production method, registry, resolver, computation
  kernel, runtime, provider, persistence, API, or consumer behavior.

The work package remains specification-only. Its exit condition is the
frozen M41 condition: **no ambient semantic default remains**.

---

## 2. Frozen Inputs WP3 Must Cite Exactly

| Frozen input | Controlling authority | Consequence for WP3 |
|---|---|---|
| Measurement Window | [M41-WP1 Candidate Register §6.5](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md#65-measurement-window), confirmed | WP3 supplies the concrete contract promised by the confirmed definition: explicit start, end/cutoff, timezone/calendar reference, resolution rules, serialization, and golden vectors. It does not rename or redefine the noun. |
| Market Measure Definition | [M41-WP1 Stage 2 §5](M41_WP1_DEFINITION_METHOD_VERSION_APPLICABILITY_CONTRACT_SPECIFICATION.md#5-market-measure-definition-contract) | Its declared subject-shape subset, output-coordinate meaning, and permitted input-category declaration remain exactly where WP1 placed them. WP3 adds no field. |
| Method Version | [M41-WP1 Stage 2 §6](M41_WP1_DEFINITION_METHOD_VERSION_APPLICABILITY_CONTRACT_SPECIFICATION.md#6-method-version-contract) | WP3 semantics are governed by the exact Method Version semantic specification. WP3 adds no Method Version field or identity coordinate. A semantic-rule change requires a new semantic version; a dependency change requires a new declared dependency-version list and therefore a new Method Version identity. |
| Method Requirement | [M41-WP1 Stage 2 §7](M41_WP1_DEFINITION_METHOD_VERSION_APPLICABILITY_CONTRACT_SPECIFICATION.md#7-method-requirement-contract) | Its prerequisite categories, operands, grammar, and binary `MET`/`UNMET` result remain closed. WP3 may not add a temporal, unit, density, currency, or adjustment prerequisite category or operand. |
| Measure Subject | [M41-WP2 Stage B §4](M41_WP2_STAGE_B_SUBJECT_AND_MANIFEST_CONTRACT_SPECIFICATION.md#4-measure-subject-contract-specification) | WP3 receives one already-valid Subject. A Measurement Window does not change Subject shape or identity and does not absorb an Asset Definition Version. |
| Observation Input Manifest and Manifest Entry | [M41-WP2 Stage B §5](M41_WP2_STAGE_B_SUBJECT_AND_MANIFEST_CONTRACT_SPECIFICATION.md#5-observation-input-manifest-contract-specification) | WP3 receives one resolved, immutable Manifest containing only exact M39 evidence. It validates temporal/unit/adjustment suitability without changing membership, identity, canonical order, or M39 meaning. |
| M39 Observation Payload and Identity | Frozen M39 WP4 and WP6 | Source-established time, interval, precision, unit, currency, scale, basis, absence, and qualification remain exact evidence. WP3 may select or reject their use under explicit calculation semantics but may not strengthen, repair, or rewrite them. |
| Deterministic Calculation | Frozen M40 Glossary meaning | Identical canonical inputs, explicit parameters, semantic versions, and dependency versions must produce byte-identical canonical results. WP3 closes the semantic choices needed to make that property implementable later. |
| Computation Outcome | Frozen M40 Glossary meaning | WP3 may classify its conditions only as `INSUFFICIENT_INPUT`, `DEPENDENCY_UNRESOLVED`, or `FAILED` under their existing meanings. It creates no outcome and does not define the Result envelope. |
| Canonical Temporal Claim and Degraded State | M34-D-0005 and frozen Glossary | Measurement Window is an input-selection boundary, not a temporal claim about the Result. WP3 creates neither a Calculation Temporal Claim specialization nor an outcome/degraded-state matrix. |
| Unit Semantics | Asset Foundation | WP3 cites the existing declarative meaning and governs calculation-side compatibility and normalization. It does not redefine how an Asset kind is counted. |
| Structural Event and Definition Version | Existing Asset Foundation / Lifecycle authorities | WP3 may require explicit adjustment basis and evidence but may not infer a structural event, alter an Asset Definition, or treat an adjustment rule as an Asset Definition Version. |

### 2.1 Frozen vocabulary classification

M41-WP1 already classified all currently known WP3 language:

- **Measurement Window** — confirmed `ADMIT`;
- **cutoff/window and timezone/calendar** — fully covered by Measurement
  Window;
- **missing-data specification** — ordinary non-canonical contract language;
- **unit/currency specification** — reuse of existing Unit Semantics, with
  calculation-side rules expressed as ordinary contract language;
- **adjustment specification** — ordinary non-canonical contract language,
  bounded by existing Structural Event vocabulary;
- **decimal/rounding specification** — ordinary non-canonical contract
  language;
- **dependency specifications** — fully covered by Method Version's declared
  dependency versions; and
- **Dependency Manifest** — not a new M41 noun; fully covered by Method
  Version.

WP3 must preserve these classifications. It must not re-candidate ordinary
language merely because Stage B will make it mechanically precise.

If drafting proves that a genuinely new governed noun is unavoidable, that
noun must complete the frozen five-stage workflow — candidate record,
Independent Review, Required Corrections if any, unconditional Independent
Confirmation, then synchronization — before any later section or fixture
relies on it. This proposal pre-owns and pre-admits no future candidate.

---

## 3. Architectural Model

WP3 occupies the semantic layer between a resolved WP2 binding and the WP4
Result envelope:

```text
Frozen WP1 specification coordinates
  Market Measure Definition
  Method Version + exact dependency versions
  Method Requirements
                  |
                  v
Frozen WP2 binding
  exact Measure Subject
  exact Observation Input Manifest
                  |
                  v
WP3 deterministic semantic closure
  Measurement Window and temporal selection
  missing-data policy
  unit/currency and adjustment compatibility
  decimal/arithmetic and dependency semantics
                  |
                  v
WP4-owned immutable Result envelope
  Measure Value / Computation Outcome
  Canonical Temporal Claim / Provenance
```

The arrows indicate normative dependency, not runtime construction or
custody. WP3 specifies no service that resolves, retrieves, selects,
calculates, or stores anything.

### 3.1 Method-governed rules versus invocation-bound values

WP3 must distinguish two layers without adding a new governed noun:

1. **Method-governed semantic rules.** The exact window kind, interval-edge
   treatment, semantic time role, timezone/calendar resolution rule,
   alignment rule, missing-data treatment, unit/currency compatibility,
   adjustment basis, arithmetic precision, rounding, and required
   dependency use are immutable semantics of the exact Method Version.
2. **Invocation-bound explicit values.** One invocation supplies the
   concrete Measurement Window boundaries, its explicit timezone/calendar
   reference where applicable, explicit parameters, and the already-resolved
   Subject and Manifest.

An invocation value cannot override the Method Version's rule. A Method
Version rule cannot supply an omitted invocation boundary through ambient
time, locale, configuration, or “latest.”

### 3.2 Frozen WP1 field reconciliation

The WP1 Method Version field set is closed and remains unchanged. WP3
therefore:

- does not add a “temporal policy,” “unit policy,” “rounding policy,”
  “adjustment policy,” or similar field to the Method Version record;
- specifies conformance obligations belonging to the semantic specification
  denoted by the existing Method Version identity and semantic version;
- requires every changed semantic rule to use a new semantic version
  identifier;
- requires every changed governed dependency identifier or version to
  change the existing declared dependency-version list, producing a new
  Method Version identity; and
- does not exercise admission of any such Method Version in M41.

This is specification closure, not a WP1 schema amendment.

---

## 4. Component Responsibilities

### 4.1 Component A — Measurement Window record and identity

Stage B must make the confirmed Measurement Window definition mechanically
complete. It must specify:

- exact record fields and cardinalities for start, end/cutoff, and
  timezone/calendar reference;
- the representation of an intentionally absent start only if an explicitly
  bounded window kind permits it; an omitted field may never mean an ambient
  default;
- whether start and end are instants, date-level references, intervals, or
  Observation-count bounds, and which combinations are valid;
- exact boundary inclusion/exclusion;
- a schema-version tag;
- field order, encoding, normalization, and byte-level canonical
  serialization;
- canonical identity and immutability; and
- validation/error conditions for missing, contradictory, unresolved,
  ambiguous, or non-canonical fields.

The concrete Measurement Window is invocation-bound. Its identity must not
include host time, request time, retrieval time, computation time, provider
order, cache state, or presentation labels.

### 4.2 Component B — Cutoff, temporal selection, and ordering

Stage B must close:

- an explicit inclusive Observation cutoff, preserving the inherited rule
  that evidence admitted after the cutoff cannot enter the calculation;
- the exact M39 source-established temporal meaning used for selection and
  ordering for each applicable input role;
- the distinction among observation, occurrence, effective, publication,
  and reference-period meanings;
- exact interval inclusion and overlap behavior;
- alignment of multiple input series or roles;
- treatment of date-only, interval, approximate, and otherwise qualified
  source time without fabricating precision;
- stable semantic input ordering, including an exact tie-break rule based
  only on governed semantic coordinates and M39 Observation Identity; and
- rejection when the required temporal meaning is absent or cannot be
  resolved without inference.

WP3 semantic ordering is calculation-input ordering. It is not WP2 Manifest
canonical ordering. The WP2 Manifest remains ordered by requirement key and
Observation Identity for identity/serialization. WP3 must not change those
bytes to obtain chronological order.

No provider order, retrieval order, row order, storage order, map iteration
order, or operational timestamp may influence selection or result.

### 4.3 Component C — Timezone, calendar, alignment, and DST

Every rule requiring civil time or sessions must identify its basis
explicitly. Stage B must specify:

- whether a window is elapsed-duration, civil-calendar, governed-session
  calendar, or Observation-count based;
- an explicit timezone identifier plus a version-bound resolution source
  when named-zone rules affect meaning, or an explicit fixed-offset /
  timezone-free rule;
- a named, exact calendar dependency and version when calendar behavior is
  required, or an explicit calendar-free policy;
- the treatment of weekends, holidays, early closes, irregular sessions,
  leap days, and calendar boundaries when applicable;
- exact DST gap and fold behavior, including rejection or explicit
  disambiguation of nonexistent and repeated local times; and
- exact alignment origin and period truncation/extension behavior.

Machine locale, machine timezone, current timezone database, exchange
convention, weekday logic, a 252-session year, or “standard market calendar”
may not fill an absent rule.

### 4.4 Component D — Missing data and density

For every required input role or series, Stage B must require the exact
Method Version semantics to choose an explicit behavior from the inherited
closed policy space:

- reject as insufficient;
- omit an interval under an exact omission rule;
- require exact density;
- apply an explicit mathematical interpolation; or
- return only independently complete output coordinates where the frozen
  Definition and future WP4 Result contract permit them.

The contract must define:

- what constitutes an expected position, gap, duplicate, or density failure;
- whether density is elapsed-time, calendar/session, or Observation-count
  based;
- boundary-gap and interior-gap treatment;
- maximum permitted gap, if any, in explicit units;
- the exact interpolation formula, endpoint requirements, precision, and
  rounding when interpolation is allowed;
- whether omission changes the effective arithmetic denominator or other
  calculation coordinate; and
- deterministic failure classification using only frozen outcome meanings.

Forward fill, backward fill, zero fill, weekend fill, nearest-value
selection, silent row omission, and best-effort continuation are prohibited
unless the exact Method Version semantics state and version the mathematical
rule. An interpolated value is calculation-derived working material; it does
not become or mutate an M39 Observation and must not be inserted into the
WP2 Manifest as invented evidence.

### 4.5 Component E — Units and currency

Stage B must specify calculation-side rules that:

- require every numeric input and output coordinate to carry an explicit
  type, unit, scale/basis, and currency where currency is meaningful;
- compare or combine only demonstrably compatible units;
- distinguish unit equality from allowed unit normalization;
- require any normalization table, taxonomy, factor, or algorithm that can
  affect output to be an exact governed dependency declared by identifier
  and version in the Method Version;
- preserve M39 source-established unit/currency/scale/basis without filling
  an absence from Asset Registry, Asset Definition, provider convention, or
  another Observation;
- define deterministic treatment of dimensionless ratios, percentages,
  rates, and compound units; and
- define the exact non-success consequence of missing, incompatible, or
  unresolved qualification.

WP3 does not authorize currency conversion. Multi-currency input must fail
unless the exact Method Version is currency-invariant or consumes separately
authorized, already-normalized evidence under the frozen four-category input
closure. No implicit FX rate, “base currency,” spot lookup, Registry
currency, provider fallback, or current market rate is permitted.

The existing Asset Foundation **Unit Semantics** term remains declarative
authority over how an Asset kind is counted. WP3 owns only the
Market-Intelligence calculation rule for accepting, rejecting, or explicitly
normalizing qualified inputs and producing a qualified calculation output.

### 4.6 Component F — Adjustment and basis

Stage B must keep at least these meanings distinct:

- raw source-reported series;
- explicitly source-adjusted series, preserving the source-established
  adjustment qualification; and
- economically continuous or otherwise calculation-normalized series
  produced under an exact, version-bound rule.

The contract must specify:

- the exact accepted input basis per role;
- whether differently based inputs are incompatible;
- the exact governed evidence and dependency versions needed by an allowed
  transformation;
- transformation ordering relative to unit normalization, interpolation,
  and arithmetic;
- the exact adjustment-factor representation and decimal rules; and
- deterministic treatment when the required basis or adjustment evidence is
  missing, ambiguous, conflicting, or unresolved.

WP3 must not infer an adjustment from a price discontinuity, ticker change,
provider convention, Asset Registry field, or Structural Event. It must not
interpret corporate actions, create Structural Events, mutate M39 evidence,
or reclassify an Asset Definition Version. Provider-adjusted and
platform-calculated values must remain attributable and semantically
distinct.

### 4.7 Component G — Decimal, rational, and arithmetic semantics

Stage B must state an exact normative arithmetic model, including:

- accepted canonical numeric lexical forms;
- integer, decimal, or exact-rational domains allowed at each boundary;
- prohibition or explicit normalization of negative zero;
- input scale;
- intermediate precision;
- output scale;
- exact rounding mode and tie behavior;
- whether and exactly where intermediate rounding occurs;
- operation ordering where algebraically equivalent rearrangements could
  round differently;
- overflow, underflow, division-by-zero, invalid-operation, and domain-error
  treatment;
- canonical representation of zero and reduced rationals where used; and
- prohibition of NaN and positive/negative infinity as successful semantic
  values.

Binary floating point may be an internal choice of a future implementation
only if that implementation proves byte-identical conformance to the
normative canonical output. WP3 does not authorize floating point as a
semantic default.

Stage B must provide a byte-level canonical serialization rule for WP3-owned
numeric values and semantic-choice encodings. It must not define the WP4
Market Measure Result envelope or Measure Value record serialization.

### 4.8 Component H — Governed dependency closure

The existing Method Version declared dependency-version field is the sole
WP3 dependency inventory. Stage B must specify:

- which semantic facilities require a governed dependency, including
  calendar, named-zone rule source, unit normalization, adjustment,
  interpolation, or arithmetic facilities where their version affects
  output;
- exact resolution by declared dependency identifier and exact version;
- canonical ordering by the already-frozen ascending code-point rule;
- fail-closed behavior for absent, ambiguous, mismatched, or unresolved
  versions;
- prohibition of dynamic `latest`, environment discovery, package-manager
  state, network resolution, or mutable global configuration;
- dependency-change golden vectors demonstrating that an exact version
  change changes the Method Version identity and may change semantic output;
  and
- the rule that runtime custody never becomes semantic ownership.

WP3 creates no Dependency Manifest, registry, plugin mechanism, resolver, or
loader.

### 4.9 Component I — Cross-dimension order and failure classification

Temporal selection, adjustment, unit normalization, missing-data treatment,
and arithmetic can produce different answers when applied in different
orders. Stage B must therefore specify one exact processing order and prove
it with at least one non-commutative golden vector.

Every WP3 rejection or failure condition must map deterministically to an
existing Computation Outcome meaning:

- canonical supplied inputs do not satisfy declared prerequisites or
  required semantic qualification → existing `INSUFFICIENT_INPUT`;
- an exact declared governed dependency cannot be resolved → existing
  `DEPENDENCY_UNRESOLVED`; and
- a semantically valid, sufficiently supplied calculation reaches an
  arithmetic/domain failure and does not complete → existing `FAILED`.

This mapping is a semantic classification obligation, not a Result contract.
WP4 remains solely responsible for the immutable Result record, required
reason representation, required-value rule, Canonical Temporal Claim, and
the deterministic outcome/degraded-state interaction matrix.

---

## 5. Ownership Boundaries

### 5.1 Singular ownership matrix

| Concern | Sole semantic owner | WP3 relationship |
|---|---|---|
| Measurement Window and calculation semantic rules | Market Intelligence | WP3 specifies |
| Market Measure Definition, Method Version, Method Requirement | Market Intelligence under frozen WP1 | Exact citation only; no field or grammar change |
| Measure Subject, Observation Input Manifest, Manifest Entry | Market Intelligence under frozen WP2 | Exact citation only; no construction, identity, order, or serialization change |
| Canonical Asset identity, Asset Definition, Definition Version, Unit Semantics | Asset Foundation | Reference only; no mutation or reinterpretation |
| Structural Event meaning | Existing Lifecycle / Structural Event authority | Reference only; no event inference or adjudication |
| M39 Observation identity and source-established payload meaning | Frozen M39 authority | Preserve exactly; no correction, strengthening, filling, conversion, or reclassification |
| Calculation-side unit compatibility, adjustment acceptance, and arithmetic | Market Intelligence | WP3 specifies without taking upstream ownership |
| Governed dependency semantic identity/version | Its governing authority; Method Version records the exact reference | WP3 requires explicit version closure; custody grants no ownership |
| Computation Outcome | Market Intelligence under frozen M40 | Reuse exact values/meanings; no extension |
| Canonical Temporal Claim and Degraded State | Producing Domain grammar under M34-D-0005 | WP3 does not construct or reinterpret |
| Measure Value, Market Measure Result, Result identity and lineage | M41-WP4 allocation | Explicitly deferred |
| Provider retrieval, storage, API, runtime execution | No WP3 authority | Explicitly excluded |

### 5.2 Five-part ownership-boundary gate

Every WP3 concrete field and rule must pass the frozen five-part gate:

1. **Permitted subject:** only an exact Measure Subject or explicit
   market-context subject already valid under WP2.
2. **Permitted inputs:** only exact M39 Observation evidence, Asset
   Foundation references, explicit invocation parameters, and explicit
   governed calculation dependencies.
3. **Output meaning:** only deterministic descriptive calculation semantics
   and qualified numeric/structured output preparation.
4. **Prohibited inputs:** no Ledger events, transactions, holdings, balances,
   accounting state, Portfolio/Workspace membership, allocation, exposure,
   performance, cash flow, person, household, goal, plan, preference, or
   life context.
5. **Prohibited judgment semantics:** no forecast, recommendation, signal,
   consensus, action intent, evaluator verdict, trust score, correctness
   confidence, quality ranking, preferred source, or suitability.

Stage B must contain a field-by-field gate table. A single failure blocks
approval.

### 5.3 Witnessed-versus-computed boundary

WP3 must preserve the frozen distinction:

- a provider/source-reported statistic remains an M39 Observation with Event
  Type `Observation`; and
- a platform-derived statistic remains a Calculated Market Measure with Event
  Type `Calculation`.

Normalization, interpolation, adjustment, or arithmetic does not retroactively
change the input Observation's identity or meaning. Derived working values
must never masquerade as witnessed evidence.

---

## 6. Compatibility Requirements

### 6.1 M34 compatibility

WP3 must remain compatible with:

- `M34-D-0004`: Asset classification and provider-reported evidence remain
  separately owned; temporal/unit rules do not infer Asset identity or
  classification;
- `M34-D-0005`: Measurement Window remains distinct from Canonical Temporal
  Claim; no new temporal-claim specialization, Producing Domain
  specialization, degraded-state token, or ambient-clock meaning is created;
  and
- `M34-D-0010`: descriptive calculation semantics remain separate from
  portfolio meaning, judgment, evaluation, execution, and presentation.

### 6.2 M39 compatibility

WP3 must:

- preserve every Observation's exact identity, source-established payload
  meaning, temporal precision/qualification, unit, currency, basis, absence,
  uncertainty, and provenance;
- never use value equality, timestamp equality, unit equality, or arithmetic
  transform to merge identity-distinct Observations;
- never manufacture an instant from date-only evidence or fill missing
  source meaning;
- never rewrite an Observation when interpolation, normalization, adjustment,
  or arithmetic derives working material;
- never select by provider identity, provider priority, retrieval order, or
  source reputation; and
- keep operational timestamps out of semantic selection.

### 6.3 M40 compatibility

WP3 must preserve:

- the four-category input closure;
- Deterministic Calculation's byte-identical-output requirement;
- exact Measurement Window/cutoff, no host clock, and no ambient locale;
- explicit units and prohibition of implicit FX;
- raw/adjusted/economically-continuous distinctions and prohibition of
  inferred adjustment;
- explicit input scale, intermediate precision, output scale, and rounding;
- prohibition of unversioned or dynamic dependencies;
- the four-value Computation Outcome closure; and
- the empty production Definition/Method catalog.

### 6.4 M41-WP1 compatibility

WP3 must not:

- add, remove, rename, reattribute, or reinterpret a Market Measure
  Definition, Method Version, or Method Requirement field;
- widen Method Requirement's three prerequisite categories or closed grammar;
- turn temporal, unit, density, currency, or adjustment conformance into a
  new hidden Method Requirement operand;
- conflate Method Version semantic version with Asset Definition Version;
  or
- admit a concrete Method Version, formula, named indicator, or production
  method.

WP3 may require a future Method Version semantic specification to make all
WP3 choices explicit because WP1 already requires the Deterministic
Calculation property. It does so without changing the WP1 record shape.

### 6.5 M41-WP2 compatibility

WP3 must not:

- change Measure Subject or Manifest bytes, identity, ordering, or
  membership;
- add a Measurement Window field to Measure Subject or Observation Input
  Manifest;
- put invocation parameters, dependencies, normalized values, interpolated
  values, or adjustment factors into Manifest Entry;
- alter the frozen distinct-identity count used by
  `ObservationEvidenceCount`;
- silently remove a WP2 Manifest Entry because it lies outside a window;
  instead, the supplied binding is non-conforming for that exact invocation;
  or
- repair WP2 evidence conflicts by recency, arithmetic, averaging, or source
  preference.

WP3 operates on a complete, resolved Manifest. It specifies conformance and
calculation semantics, not retrieval or manifest construction.

### 6.6 WP4 handoff compatibility

WP3 must expose a citable, closed semantic contract that lets WP4 identify:

- the exact Measurement Window;
- the exact temporal/unit/adjustment/arithmetic rule set denoted by the
  Method Version semantic version;
- exact dependency versions;
- deterministic failure classification; and
- exact canonical arithmetic output bytes where success is semantically
  possible.

WP3 must not predefine WP4 fields, Result serialization, Result identity,
reason-code vocabulary, partial-result envelope, Provenance composition,
Canonical Temporal Claim contents, or outcome/degraded-state combinations.

---

## 7. Validation and Required Evidence

All validation evidence is documentation or data fixture material. No
committed test runner, reference implementation, conformance harness, or
calculation code is authorized.

Each golden vector must record:

- exact canonical input bytes;
- exact expected canonical output bytes or exact rejection/outcome
  classification;
- the semantic rule under test;
- every exact semantic and dependency version used;
- a short independently reproducible derivation; and
- an explicit statement that the example is non-production and admits no
  Definition, Method Version, formula, or method.

### 7.1 Minimum golden-vector matrix

| Vector | Required proof |
|---|---|
| Window start edge | Exact inclusion/exclusion at the lower boundary |
| Inclusive cutoff | Evidence exactly at cutoff is treated by the declared rule; evidence after cutoff cannot participate |
| Elapsed-duration vs civil-calendar window | Same apparent dates yield intentionally distinct windows |
| Timezone independence | Two host timezones produce the same canonical semantics |
| DST gap | Nonexistent local time is rejected or resolved by the one explicit rule |
| DST fold | Repeated local time is explicitly disambiguated |
| Calendar holiday / early close | Named calendar version, not weekday or exchange default, determines behavior |
| Leap day / period alignment | Exact calendar boundary and alignment behavior |
| Date-only or approximate M39 time | No instant or stronger precision is fabricated |
| Semantic ordering permutation | Different presentation/manifest order yields the same calculation input order without changing Manifest bytes |
| Boundary missing data | Exact reject/omit/interpolate consequence |
| Interior missing data / density | Exact expected-position and gap rule |
| Prohibited fill | Forward/zero/nearest fill is rejected when not explicitly declared |
| Interpolation | Formula, endpoints, precision, and rounding reproduce exact bytes; no M39 Observation is invented |
| Compatible unit | Exact comparison/combination succeeds |
| Incompatible unit | Deterministic non-success classification |
| Unit normalization dependency | Exact dependency version controls normalization |
| Missing currency | No Registry/default currency is inferred |
| Multi-currency | Failure unless currency-invariant or separately normalized evidence is explicit |
| Raw vs adjusted | Basis mismatch does not silently normalize |
| Explicit adjustment | Exact evidence, factor, ordering, precision, and dependency versions reproduce bytes |
| Decimal tie | Exact rounding-mode tie behavior |
| Intermediate rounding | Prohibited or exact declared location demonstrated |
| Negative zero | Canonical normalization/rejection demonstrated |
| NaN/infinity | Cannot become successful semantic output |
| Divide by zero / domain error | Exact `FAILED` classification under the frozen meaning |
| Dependency unresolved | Exact `DEPENDENCY_UNRESOLVED` classification |
| Dependency version change | Version change alters Method Version identity and, where applicable, expected bytes |
| Non-commutative pipeline | Exact transform order is proven where reordering would change output |
| Cross-platform canonical bytes | Independent manual recomputation yields byte-identical output |

Stage B may split these into multiple fixture files, but it may not omit a
row or merge materially distinct risks into one vague example.

### 7.2 Negative-corpus validation

Independent review must confirm that WP3 contains none of:

- Calculation Temporal Claim or a renamed equivalent;
- a specialized Producing Domain;
- a new Dependency Manifest noun;
- implicit FX, base currency, default timezone, default calendar, weekday
  calendar, 252-session assumption, inferred adjustment, or inferred unit;
- provider priority, provider-specific payload fields, or source-quality
  ranking;
- Ledger, Portfolio, Workspace, Wealth, judgment, recommendation, execution,
  or presentation semantics;
- production method, formula, registry, resolver, kernel, endpoint, schema,
  persistence, provider, or runtime design; or
- an executable validation artifact.

### 7.3 Round-trip and determinism proof

The Measurement Window and every WP3-owned serialized semantic coordinate
must be injective and round-trippable:

- given only canonical bytes and the Stage B specification, an independent
  reviewer can reconstruct the exact logical value; and
- given that logical value and the specification, the reviewer produces
  byte-identical canonical bytes without ambient configuration.

Arithmetic vectors must be recomputable by hand or by an independent
reviewer's private scratch work. Scratch scripts are not repository
artifacts and are neither required nor authoritative.

---

## 8. Explicit Exclusions and Deferrals

WP3 does not:

- implement `temporal.py`, `units.py`, `decimal_math.py`, or any equivalent;
- define or admit a concrete calculation formula, indicator, reference
  method, Method Version, or production catalog record;
- build the future method-admission gate or registry;
- resolve applicability or execute a calculation;
- retrieve Observations or construct/modify a Manifest;
- query a clock, timezone service, calendar service, provider, database, or
  network;
- define provider fallback or evidence ranking;
- perform or authorize currency conversion;
- interpret corporate actions or create adjustment evidence;
- define Measure Value or Market Measure Result fields;
- define partial-result composition;
- define reason-code vocabulary;
- define Provenance composition;
- construct a Canonical Temporal Claim;
- define the outcome/degraded-state interaction matrix;
- authorize persistence, cache, replay, history, message, API, SDK, UI, or
  consumer integration; or
- update the Decision Log or refresh Graphify at this proposal stage.

The future Frozen Registry, Applicability Resolver, Pure Computation Kernel,
and Read-Only Integration/Adoption Design remain deferred to a separately
chartered milestone after M41.

---

## 9. Internal Work-Package Decomposition

WP3 remains one M41 work package. The following are internal governance
stages, not new milestone work packages.

### WP3 Stage A — Vocabulary Sufficiency and Semantic Surface Register

**Purpose:** Prove, before normative contract text relies on any new label,
that the frozen vocabulary is sufficient and inventory every determinism
choice Stage B must close.

**Required contents:**

- one row for every component in §4;
- the governing frozen noun or ordinary-language classification;
- the exact owner and non-owner boundary traced to frozen authority;
- the Method-governed versus invocation-bound placement;
- the exact upstream and downstream contract references;
- whether a governed dependency may be required;
- the required golden-vector rows; and
- a candidate-vocabulary determination.

**Expected vocabulary result:** no new governed noun. Measurement Window is
reused as confirmed; other known WP3 phrases retain WP1 §6.0 classifications.

If a genuine candidate is discovered, Stage A must supply its exact proposed
definition, determined single owner justified through the governed workflow,
disposition request, full Glossary/negative-corpus overlap analysis, V1–V3
analysis, M34/M39/M40/WP1/WP2 compatibility analysis, and candidate-level
five-part gate. This architecture proposal assigns no owner in advance.

**Deliverable:**
`M41_WP3_STAGE_A_VOCABULARY_AND_SEMANTIC_SURFACE_REGISTER.md`

**Review artifacts:**

- `M41_WP3_STAGE_A_INDEPENDENT_REVIEW.md`
- `M41_WP3_STAGE_A_REQUIRED_CORRECTIONS_RESPONSE.md` if required
- `M41_WP3_STAGE_A_INDEPENDENT_CONFIRMATION.md`

**Completion criterion:** unconditional `CONFIRMED`, with no open finding
and no candidate relied upon before its confirmed disposition. Any confirmed
`ADMIT`/`RENAME` Glossary synchronization must be recorded in the same change
as that confirmation, as required by the frozen M41 workflow.

### WP3 Stage B — Deterministic Semantics Contract Specification

**Purpose:** Write the complete normative contract described in §§3–7,
using only frozen or Stage A-confirmed vocabulary.

**Required contents:**

- Measurement Window concrete record, identity, serialization, validation,
  and errors;
- temporal selection/order, cutoff, interval, timezone/calendar, alignment,
  and DST rules;
- missing-data/density/interpolation rules;
- unit/currency compatibility and normalization rules;
- adjustment/basis rules;
- decimal/arithmetic rules and canonical numeric encoding;
- dependency resolution/version-closure rules;
- cross-dimension processing order;
- frozen-outcome classification;
- field-level five-part gate;
- compatibility analysis against every authority in §6;
- complete golden-vector matrix and round-trip evidence; and
- explicit non-production/non-operational authority statements.

**Deliverable:**
`M41_WP3_STAGE_B_TEMPORAL_UNIT_ADJUSTMENT_ARITHMETIC_CONTRACT_SPECIFICATION.md`

**Review artifacts:**

- `M41_WP3_STAGE_B_INDEPENDENT_REVIEW.md`
- `M41_WP3_STAGE_B_REQUIRED_CORRECTIONS_RESPONSE.md` if required
- `M41_WP3_STAGE_B_INDEPENDENT_CONFIRMATION.md`

**Review requirement:** independent numerical and architectural review.

**Completion criterion:** `APPROVED`, or `APPROVED WITH REQUIRED
CORRECTIONS` followed by full resolution and unconditional `CONFIRMED`, with
zero open findings and affirmative proof that no ambient semantic default
remains.

### WP3 closeout

After Stage B confirmation, a WP3 closeout may record only the already-proven
status, authorities, deliverables, and readiness for WP4. It must not add
semantics or serve as a correction vehicle.

Suggested deliverable: `M41_WP3_CLOSEOUT.md`.

---

## 10. Dependency-Safe Implementation Sequence

1. Independently review this WP3 Architecture Proposal.
2. Resolve every required architecture correction individually.
3. Obtain unconditional Independent Architecture Confirmation.
4. Freeze the confirmed WP3 Architecture.
5. Draft Stage A's vocabulary/semantic-surface register.
6. Independently review Stage A, resolve required corrections, and obtain
   unconditional confirmation.
7. If Stage A unexpectedly finds an `ADMIT`/`RENAME` candidate, record its
   unconditional confirmation and required Glossary synchronization in the
   same change; otherwise make no Glossary change.
8. Draft Stage B in dependency order:
   1. Measurement Window bytes and identity;
   2. cutoff and semantic-time selection;
   3. timezone/calendar/alignment/DST;
   4. missing-data and density;
   5. unit/currency compatibility;
   6. adjustment/basis;
   7. decimal/arithmetic;
   8. dependency closure;
   9. cross-dimension ordering and frozen-outcome classification; and
   10. integrated vectors, gates, and compatibility proof.
9. Perform independent numerical and architectural review of Stage B.
10. Resolve all findings and repeat confirmation as necessary until
    unconditional `CONFIRMED` with zero open findings.
11. Record WP3 closeout without adding semantics.
12. Only then may M41-WP4 architecture/specification work begin.

No stage begins before the preceding gate is confirmed. WP4 cannot infer or
repair a WP3 ambiguity; an unresolved semantic default blocks WP3 closeout.

---

## 11. Architecture Acceptance Criteria

This proposal is architecturally acceptable only if Independent Review
confirms all of the following:

1. Scope exactly matches frozen M41-WP3 and does not reopen WP1 or WP2.
2. Measurement Window is concretized without becoming a Canonical Temporal
   Claim or a field of Subject/Manifest.
3. WP1's Method Version and Method Requirement field sets remain unchanged.
4. Method-governed rules and invocation-bound values are unambiguously
   separated.
5. Every temporal default is explicit, including time role, cutoff, interval
   edges, timezone, calendar, alignment, qualified time, DST, and ordering.
6. Every missing-data and density choice is explicit and version-bound.
7. Unit Semantics is cited, not redefined; unit compatibility and
   normalization ownership is clear.
8. Currency conversion remains unauthorized and implicit FX is impossible.
9. Raw, adjusted, and economically continuous bases remain distinct; no
   Structural Event or adjustment is inferred.
10. Decimal/rational representation, precision, scale, rounding, operation
    order, and exceptional-number behavior have no ambient default.
11. Every semantic dependency is exact, governed, version-bound, and listed
    through the frozen Method Version field; no Dependency Manifest is
    created.
12. Cross-dimension processing order is explicit.
13. WP3 conditions use only existing Computation Outcome meanings and do not
    invade WP4's Result/state matrix.
14. M39 evidence remains immutable and source-faithful.
15. WP2 Manifest bytes, membership, identity, and ordering remain untouched.
16. The complete golden-vector matrix is mandatory and specification-only.
17. Every concrete Stage B field must pass the five-part ownership gate.
18. No new noun is used before unconditional confirmation and
    synchronization.
19. The production Definition/Method catalog remains empty.
20. Implementation, runtime, provider, persistence, API, and production
    authority remain `NONE`.
21. Stage B's exit test is objectively reviewable: no ambient semantic
    default remains.
22. WP4 begins only after WP3 Stage B is unconditionally confirmed and WP3
    is closed.

---

## 12. Risks and Mitigations

| Risk | Required mitigation |
|---|---|
| WP3 adds policy fields to the frozen Method Version | Bind semantics to the existing semantic version and dependency list; add no field |
| Measurement Window becomes a Result temporal claim | Keep it strictly as Manifest input-selection boundary; WP4 owns Canonical Temporal Claim |
| WP3 reorders or edits the WP2 Manifest | Define separate semantic calculation ordering over immutable entries; preserve WP2 bytes |
| M39 date-only/qualified time is silently strengthened | Require explicit role/precision compatibility and fail closed |
| Host timezone, locale, or current timezone database leaks in | Require explicit fixed basis or exact versioned dependency and DST vectors |
| “Business day” hides an equity calendar | Require named calendar/version or explicit calendar-free policy |
| Missing rows are silently filled or dropped | Require one exact versioned policy and dedicated negative vectors |
| Interpolation fabricates Observation evidence | Treat interpolation only as calculation-derived working material; never add a Manifest Entry |
| Unit normalization takes Asset Foundation ownership | Cite Unit Semantics; WP3 owns only calculation compatibility/transform rules |
| Currency conversion enters through a helper or Registry field | Explicitly prohibit FX and inferred currency; require failure or separately authorized normalized evidence |
| Adjustments infer corporate actions | Require explicit evidence and dependency; preserve Structural Event ownership |
| Equivalent arithmetic expressions round differently | Fix operation order, precision, scale, and rounding; prove non-commutative cases |
| NaN/infinity becomes a value | Prohibit as successful output and require deterministic failure |
| A library/calendar/timezone upgrade changes output silently | Treat every output-affecting facility as a declared exact dependency |
| WP3 creates a fifth outcome or reason model | Reuse only frozen outcomes; defer Result/reasons/state matrix to WP4 |
| Golden vectors accidentally admit a production formula | Label every vector illustrative/non-production; keep catalog empty |
| Durable validation code slips into the repository | Documentation/data fixtures only; committed executable tooling requires future authority |

---

## 13. Repository and Governance Effects

This proposal creates only:

- `docs/implementation/M41_WP3_ARCHITECTURE_PROPOSAL.md`

It does not modify:

- frozen M41, WP1, or WP2 artifacts;
- `docs/GLOSSARY.md`;
- the Decision Log;
- the Implementation Index;
- Graphify output;
- architecture constitutions;
- source code, tests, fixtures, schemas, or configuration.

Per the frozen M41 repository convention, Decision Log reconciliation and
Graphify refresh remain Epic Closeout work after WP4 and independent closeout
confirmation. Creating this proposal is not authority to perform either.

---

## 14. Final Architectural Boundary

M41-WP3 starts with an exact WP1 semantic specification coordinate and an
exact WP2 Subject/Manifest binding. It ends with a fully explicit,
version-bound, canonically serializable set of temporal, missing-data,
unit/currency, adjustment, arithmetic, and dependency semantics that WP4 can
cite without inference.

It changes no upstream contract and creates no downstream Result contract.
It authorizes no code or operation. Its decisive completion test is that two
independent readers, given the same frozen inputs, exact versions, and WP3
specification, can derive the same semantic selection, the same arithmetic
bytes or the same frozen non-success classification, without consulting a
clock, locale, provider, registry default, mutable dependency, or unstated
market convention.

---

## Final Status

**READY FOR INDEPENDENT ARCHITECTURE REVIEW**
