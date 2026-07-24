# M41-WP4 — Architecture Proposal

**Document role:** Architecture Review Board (fresh session)

**Document status:** `READY FOR INDEPENDENT ARCHITECTURE REVIEW`

**Proposal date:** 2026-07-24

**Milestone:** M41 — Governed Market Measure Semantics

**Work package:** M41-WP4 — Result, State, and Provenance Model

**M41 Architecture authority:** `COMPLETE`, `CONFIRMED`, `FROZEN` (cited,
not modified)

**M41-WP1 authority:** `COMPLETE`, `CONFIRMED`, `CLOSED`, `FROZEN` (cited,
not modified)

**M41-WP2 authority:** `COMPLETE`, `CONFIRMED`, `CLOSED`, `FROZEN` (cited,
not modified)

**M41-WP3 authority:** `COMPLETE`, `CONFIRMED`, `CLOSED`, `FROZEN` (cited,
not modified)

**Implementation authority:** `NONE`

**Runtime authority:** `NONE`

**Provider authority:** `NONE`

**Persistence authority:** `NONE`

**API authority:** `NONE`

**Production-method authority:** `NONE`

**Executable-validation authority:** `NONE`

**Normative status:** This document is a non-canonical architecture proposal.
Its use of `MUST`, `MUST NOT`, `SHALL`, `SHALL NOT`, `MAY`, and `SHOULD`
describes requirements proposed for review. Those terms acquire no repository
authority unless and until this proposal is independently reviewed and
explicitly approved.

---

## 0. Authority, Precedence, and Non-Reopening Rule

This proposal determines the architecture and internal governance sequence for
M41-WP4 exactly within the allocation made by the frozen
[M41 Architecture](M41_ARCHITECTURE_PROPOSAL.md). It is subordinate, in order,
to:

1. the frozen platform and Asset Foundation architecture;
2. frozen M34 decisions and the frozen M39 and M40 corpora;
3. the frozen M41 Architecture;
4. frozen M41-WP1, including its Candidate Vocabulary and Ownership Register,
   contract specification, confirmation chain, and closeout;
5. frozen M41-WP2, including its confirmed architecture, Stage A, and Stage B
   Subject and Manifest contract specification; and
6. frozen M41-WP3, including its confirmed architecture, Stage A, and Stage B
   deterministic-semantics contract specification, and its closeout.

If this proposal conflicts with a higher authority, the higher authority
governs and the conflicting clause is invalid.

M41-WP1, WP2, and WP3 are complete and frozen. WP4 does not reopen,
reinterpret, extend, correct, or replace any of their decisions. In
particular, WP4 accepts as fixed and consumes by exact reference:

- **WP1** — Market Measure Definition, Method Version (its identity, semantic
  version, and declared dependency-version list), Method Requirement, and the
  Applicability contract, each with its closed field set;
- **WP2** — Measure Subject's three closed shapes and identity; the
  Observation Input Manifest's exact M39-evidence-only membership, ordering,
  canonical serialization (`MSB1` Subject bytes, `OIM1` Manifest bytes),
  identity, and `ObservationEvidenceCount`; and Manifest Entry's two-field
  structure; and
- **WP3** — the Measurement Window concrete record, identity, and bytes; the
  temporal-selection, cutoff, timezone/calendar/DST, missing-data/density/
  interpolation, unit/currency, adjustment/basis, decimal/rational/arithmetic,
  governed-dependency-closure, and cross-dimension processing-order semantics;
  the mandatory 12-step processing order; the total failure classification
  onto the frozen Computation Outcome values; and Golden Vectors `GV-01`
  through `GV-30`.

WP4 changes none of these. It inserts no intermediate WP1/WP2/WP3 stage and
creates no replacement summary authority over them.

---

## 1. Architectural Objective (Deliverable 1)

The complete architectural allocation of M41-WP4 is:

> Specify the immutable **Market Measure Result** — its composition, its
> **Measure Value** coordinate, its **Computation Outcome** success/failure
> closure, its **Result identity** and canonical serialization, its reuse of
> the existing **Canonical Temporal Claim** and **Provenance** terms, and the
> deterministic **outcome/degraded-state interaction matrix** — such that the
> semantic coordinates handed off by frozen WP1–WP3 compose into exactly one
> canonically serializable, byte-identity-stable, lineage-complete Result per
> calculation, with no ambient default and no value on any non-success
> outcome, thereby closing the last semantic responsibility M41 allocates
> before Epic Closeout.

WP4 is the terminal specification work package of M41. Its exit condition
inherits and completes the M41 determinism condition — **no ambient semantic
default remains** — for the Result surface, and adds the WP4-specific
completion tests fixed by the M41 Architecture: **hash stability**,
**no-value-on-failure**, **complete lineage**, and **canonical serialization
round-trips** (M41 Architecture §12).

WP4 owns specification of:

1. the concrete **Market Measure Result** composition (fields, cardinalities,
   ordering, and the coordinates it binds from WP1–WP3);
2. the **Measure Value** coordinate — typed, unit-qualified, present **iff**
   the Computation Outcome is `SUCCEEDED`, and never a new classification axis;
3. **success/failure semantic closure** over the frozen four-value Computation
   Outcome, including the total mapping of WP3's classifications into the
   Result and the no-value-on-non-success rule;
4. the deterministic **outcome/degraded-state interaction matrix** over the
   already-admitted Computation Outcome and Degraded State terms;
5. the **Canonical Temporal Claim** binding for a Result — Event Type
   `Calculation`, Producing Domain `Market Intelligence` — and the reserved
   `Snapshot Creation` exclusion boundary;
6. **Provenance carriage** — reuse of the existing Provenance term as a
   carried, lineage-complete record, never redefined;
7. **Result identity, canonical serialization, hash stability, and
   round-trip** rules, including a byte-level encoding, a schema-version tag,
   and identity independence from every operational coordinate;
8. **partial-output / partial-result composition** where the frozen Definition
   and Computation Outcome permit independently complete output coordinates;
   and
9. the exact, citation-only **consumption of the WP3 handoff** (Measurement
   Window bytes/identity, semantic and dependency versions, qualified
   canonical arithmetic bytes on success, or one frozen Computation Outcome
   classification).

WP4 does **not** own:

- Market Measure Definition, Method Version, or Method Requirement meaning or
  fields (WP1);
- Measure Subject or Observation Input Manifest construction, identity,
  ordering, membership, or serialization (WP2);
- Measurement Window semantics, temporal/unit/adjustment/arithmetic rules,
  dependency closure, processing order, or the Computation Outcome
  *classification* logic (WP3 — WP4 consumes the classification result, it does
  not re-derive it);
- M39 Observation meaning, identity, or payload (M39);
- Asset identity, Asset Definition, Definition Version, Unit Semantics, or
  Valuation Semantics (their existing Asset Foundation owners);
- the *meaning* or capture of Provenance (Connectivity & Ingestion) or the
  grammar of Canonical Temporal Claim / Producing Domain / Event Type / Degraded
  State (M34-D-0005 and the frozen Glossary); or
- any formula, concrete production method, registry, resolver, computation
  kernel, runtime, provider, persistence, API, or consumer behavior.

The work package is specification-only. It authorizes no code and no
operation.

---

## 2. Constitutional Authority and Frozen Inputs WP4 Must Cite Exactly (Deliverable 2)

WP4 is authorized only by the frozen M41 Architecture §6 allocation of
"M41-WP4 — Result, State, and Provenance Model" and §4/§12 objectives and
acceptance criteria. It must cite, and may not amend, the following.

| Frozen input | Controlling authority | Consequence for WP4 |
|---|---|---|
| Market Measure Result | Frozen M40 Glossary (`GLOSSARY.md#market-measure-result`); one immutable, owner-explicit outcome composed of Computation Outcome, Canonical Temporal Claim, and lineage | WP4 specifies the concrete composition, field order, cardinalities, identity, and serialization of this already-admitted term. It adds no meaning the M40 admission did not grant. |
| Computation Outcome | Frozen M40 Glossary; four values `SUCCEEDED` / `INSUFFICIENT_INPUT` / `DEPENDENCY_UNRESOLVED` / `FAILED` | WP4 uses exactly these four values, closes the Result over them, and creates no fifth outcome. |
| Input Sufficiency | Frozen M40 Glossary | Distinct from Computation Outcome and from WP1 Method Requirement; WP4 does not conflate the Result's outcome closure with sufficiency classification. |
| Measure Value | [M41-WP1 Candidate Register §6.6](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md#66-measure-value) — `ADMIT` candidate, reviewed and confirmed in the frozen WP1 register | WP4 is the work package that first *relies* on Measure Value. It uses the confirmed WP1 definition — a typed, unit-qualified value coordinate within Market Measure Result, present iff `SUCCEEDED`, never a new axis — verbatim. It re-defines nothing. |
| Provenance | [M41-WP1 Candidate Register §6.8](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md#68-provenance--reuse) — `REUSE`; owned by Connectivity & Ingestion at capture time (Platform Architecture §6.4) | WP4 is a *carrier* of Provenance on its own Result record, never an owner of what Provenance means or how it is captured. WP4 cites, does not redefine, and does not widen Provenance. |
| Canonical Temporal Claim, Event Type, Producing Domain | `M34-D-0005` and the frozen Glossary; `REUSE` carried by WP1 §6 | A Result's temporal claim reuses the existing grammar qualified by Event Type `Calculation`, Producing Domain `Market Intelligence`. WP4 constructs the binding but neither reinterprets the grammar nor creates a Calculation Temporal Claim specialization. |
| Degraded State | `M34-D-0005` and the frozen Glossary | An already-admitted term. WP4 combines it with Computation Outcome in the interaction matrix without redefining either. |
| Reserved `Snapshot Creation` Event Type | [M41-WP1 Candidate Register §6 note](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md); `GLOSSARY.md#event-type` | An exclusion rule: a Market Measure Result MUST NOT claim the `Snapshot Creation` Event Type, which is reserved for its existing owner. Not a new noun. |
| Calculation Temporal Claim | M40 `REJECT`, carried forward by WP1 | WP4 does not reintroduce this rejected candidate under any name. |
| WP1 Method Version identity + declared dependency-version list | [M41-WP1 Stage 2 §6](M41_WP1_DEFINITION_METHOD_VERSION_APPLICABILITY_CONTRACT_SPECIFICATION.md#6-method-version-contract) | The Result's lineage cites the exact Method Version identity, semantic version, and dependency versions. WP4 adds no Method Version field. |
| WP2 Subject / Manifest bytes and identity | [M41-WP2 Stage B](M41_WP2_STAGE_B_SUBJECT_AND_MANIFEST_CONTRACT_SPECIFICATION.md) | The Result's lineage cites the exact Subject identity, Manifest identity, and `ObservationEvidenceCount`. WP4 changes no Subject/Manifest byte, membership, or order. |
| WP3 Measurement Window bytes/identity, semantic bytes, arithmetic bytes, and Computation Outcome classification | [M41-WP3 Stage B](M41_WP3_STAGE_B_TEMPORAL_UNIT_ADJUSTMENT_ARITHMETIC_CONTRACT_SPECIFICATION.md) and [WP3 Closeout](M41_WP3_CLOSEOUT.md) | WP4 consumes exactly these coordinates by reference. It re-derives no window, no arithmetic, and no classification; it composes them into the Result. |

### 2.1 Frozen vocabulary posture

WP4's expected vocabulary result is **no new governed noun of WP4's own
invention**. Concretely:

- **Market Measure Result**, **Computation Outcome**, **Input Sufficiency** —
  frozen M40 admissions, reused with frozen meaning;
- **Measure Value** — WP1-registered, confirmed `ADMIT`; WP4 is the first
  relying work package and uses the confirmed definition without re-admitting
  or altering it;
- **Provenance**, **Canonical Temporal Claim**, **Event Type**, **Producing
  Domain**, **Degraded State**, **Snapshot Creation** — reused / referenced
  with frozen meaning; and
- **Calculation Temporal Claim** — `REJECT`, carried forward, never
  reintroduced.

If Stage B drafting proves a genuinely new governed noun is unavoidable
(for example, a narrower lineage specialization of Provenance — the path WP1
§6.8 already reserved), that noun MUST complete the frozen five-stage workflow
— candidate record, Independent Review, Required Corrections if any,
unconditional Independent Confirmation, then synchronization — before any
later section or fixture relies on it. This proposal pre-owns and pre-admits
no future candidate.

---

## 3. Scope (Deliverable 3) and Boundary vs. WP1–WP3 (Deliverable 10 boundary)

### 3.1 Architectural model — WP4's position

WP4 occupies the terminal layer that composes the frozen upstream coordinates
into the immutable Result envelope:

```text
Frozen WP1 specification coordinates
  Market Measure Definition
  Method Version identity + semantic version + dependency versions
  Method Requirements
                  |
                  v
Frozen WP2 binding
  exact Measure Subject (identity, bytes)
  exact Observation Input Manifest (identity, bytes, ObservationEvidenceCount)
                  |
                  v
Frozen WP3 deterministic semantic closure
  Measurement Window bytes/identity
  temporal / unit / adjustment / arithmetic semantics
  qualified canonical arithmetic bytes on success
  OR one frozen Computation Outcome classification
                  |
                  v
WP4 immutable Result envelope  ← THIS WORK PACKAGE
  Market Measure Result composition
  Measure Value (iff SUCCEEDED)
  Computation Outcome closure + outcome/degraded-state matrix
  Canonical Temporal Claim (Event Type Calculation) + Provenance carriage
  Result identity, canonical bytes, hash stability, round-trip
```

The arrows indicate normative dependency, not runtime construction or custody.
WP4 specifies no service that resolves, retrieves, calculates, composes at
runtime, or stores anything. It specifies what a valid Result **is**, not a
process that builds one.

### 3.2 Already-completed (WP1–WP3) versus allocated-to-WP4 — no overlap

| Concern | Owner | WP4 relationship |
|---|---|---|
| Definition / Method Version / Method Requirement fields | WP1 (frozen) | Cited in lineage only |
| Subject / Manifest / Manifest Entry bytes, identity, order | WP2 (frozen) | Cited in lineage only |
| Measurement Window bytes/identity | WP3 (frozen) | Cited in lineage / temporal-claim distinction only |
| Temporal / unit / adjustment / arithmetic semantics | WP3 (frozen) | Consumes result bytes; specifies no rule |
| Computation Outcome *classification* logic | WP3 (frozen) | Consumes the classification; does not re-classify |
| Market Measure Result *composition, identity, bytes* | **WP4** | **Specifies** |
| Measure Value coordinate | **WP4** | **Specifies** (on confirmed WP1 `ADMIT`) |
| Success/failure Result closure + no-value-on-failure | **WP4** | **Specifies** |
| Outcome/degraded-state interaction matrix | **WP4** | **Specifies** |
| Result Canonical Temporal Claim binding + Snapshot exclusion | **WP4** | **Specifies binding** (grammar frozen) |
| Provenance carriage / lineage completeness | **WP4** | **Specifies carriage** (meaning frozen) |
| Partial-output / partial-result composition | **WP4** | **Specifies** |

No cell is owned twice. Every WP4-owned cell was explicitly deferred to WP4 by
the WP1–WP3 closeouts and by M41 Architecture §6.

---

## 4. Out-of-Scope (Deliverable 4)

WP4 does not:

- implement `results.py`, `provenance.py`, or any equivalent module;
- define or admit a concrete Market Measure Definition, Method Version,
  formula, indicator, reference method, or production catalog record — the
  production Definition/Method catalog remains **empty** throughout M41;
- build the future method-admission gate, Frozen Registry, Applicability
  Resolver, Pure Computation Kernel, or Read-Only Integration/Adoption Design
  (deferred to a future, separately chartered milestone);
- re-derive, repair, or reinterpret any Measurement Window, arithmetic result,
  or Computation Outcome classification produced under frozen WP3;
- change any Subject, Manifest, or Method Version byte, field, identity, or
  order;
- redefine, widen, or re-capture Provenance, or reinterpret the Canonical
  Temporal Claim / Event Type / Producing Domain / Degraded State grammar;
- reintroduce Calculation Temporal Claim or any specialized Producing Domain;
- permit a Result to claim the reserved `Snapshot Creation` Event Type;
- introduce any judgment, recommendation, signal, consensus, evaluator
  verdict, trust score, correctness confidence, quality ranking, or
  suitability semantics;
- introduce any Ledger, Portfolio, Workspace, Wealth, execution, transaction,
  or presentation semantics;
- define reason-code *taxonomies* as new governed vocabulary (WP4 may specify
  a reason *representation* field on the Result only insofar as it composes
  already-frozen coordinates and adds no new governed noun);
- retrieve, persist, cache, replay, message, expose via API/SDK/UI, or
  integrate with any consumer;
- author any committed executable validation artifact, test runner,
  conformance harness, or reference implementation; or
- update the Decision Log or refresh Graphify at this proposal stage.

---

## 5. Ownership Boundaries (Deliverable 5)

### 5.1 Singular ownership matrix

| Concern | Sole semantic owner | WP4 relationship |
|---|---|---|
| Market Measure Result composition, identity, serialization | Market Intelligence under frozen M40 admission | WP4 specifies the concrete contract |
| Measure Value coordinate | Market Intelligence (WP1 confirmed `ADMIT`) | WP4 specifies the field on the confirmed definition |
| Computation Outcome values and meaning | Market Intelligence under frozen M40 | Reuse of exact four values; no extension |
| Outcome/degraded-state interaction | Market Intelligence (rule built from two frozen terms) | WP4 specifies the matrix; redefines neither term |
| Canonical Temporal Claim / Event Type / Producing Domain grammar | Producing-Domain grammar under `M34-D-0005` | WP4 binds Event Type `Calculation`; constructs no new grammar |
| Provenance meaning and capture | Connectivity & Ingestion (Platform Architecture §6.4) | WP4 carries it on its record; never owns or captures it |
| Degraded State meaning | Existing owner under `M34-D-0005` | Reference only |
| `Snapshot Creation` Event Type | Its existing owner | Exclusion only; WP4 forbids a Result claiming it |
| Definition / Method Version / Method Requirement | Market Intelligence under frozen WP1 | Exact citation only |
| Subject / Manifest / Manifest Entry | Market Intelligence under frozen WP2 | Exact citation only |
| Measurement Window and calculation semantics | Market Intelligence under frozen WP3 | Exact citation only |
| M39 Observation identity and payload | Frozen M39 authority | Preserve exactly via lineage; no mutation |
| Asset identity / Definition / Unit Semantics / Valuation Semantics | Asset Foundation | Reference only |
| Provider retrieval, storage, API, runtime | No WP4 authority | Explicitly excluded |

### 5.2 Five-part ownership-boundary gate

Every WP4 concrete field and rule MUST pass the frozen five-part gate before
independent review may approve it:

1. **Permitted subject:** only an exact Measure Subject already valid under
   WP2, described by a Result that makes a Calculated Market Measure claim.
2. **Permitted inputs:** only the frozen WP1–WP3 coordinates (Definition/Method
   Version identity and versions, Subject/Manifest identity, Measurement Window
   identity, qualified arithmetic bytes, Computation Outcome classification),
   Asset Foundation references, explicit invocation parameters, and explicit
   governed calculation dependencies — the same four-category input closure.
3. **Output meaning:** only an immutable, deterministic descriptive Result —
   a qualified value coordinate on success, or a frozen non-success
   classification with no value — plus its lineage and temporal claim.
4. **Prohibited inputs:** no Ledger events, transactions, holdings, balances,
   accounting state, Portfolio/Workspace membership, allocation, exposure,
   performance, cash flow, person, household, goal, plan, preference, or life
   context.
5. **Prohibited judgment semantics:** no forecast, recommendation, signal,
   consensus, action intent, evaluator verdict, trust score, correctness
   confidence, quality ranking, preferred source, or suitability.

Stage B MUST contain a field-by-field gate table. A single failure blocks
approval.

### 5.3 Witnessed-versus-computed boundary

A Market Measure Result carries Event Type `Calculation`: it is a
platform-computed claim. WP4 MUST preserve the frozen distinction — a
provider/source-reported statistic remains an M39 Observation with Event Type
`Observation`; a platform-derived Result is a Calculated Market Measure with
Event Type `Calculation`. A Result MUST NOT be represented as if a source had
reported it, and the Result's Provenance MUST make the computed lineage
explicit rather than laundering derived values into apparent witnessed
evidence.

---

## 6. Component Decomposition (Deliverable 6) and Semantic Responsibility Allocation (Deliverable 8)

WP4's normative surface is nine components, A–I. Each row is a Stage B
obligation; none is designed here.

### 6.1 Component A — Market Measure Result composition and identity

Stage B must make the already-admitted Market Measure Result mechanically
complete. It must specify:

- the exact composed coordinates: Subject identity, Measurement Window
  identity, Method Version identity + semantic version + dependency-version
  list, Observation Input Manifest identity + `ObservationEvidenceCount`,
  Computation Outcome, Measure Value (conditional per Component B),
  Canonical Temporal Claim (Component E), and Provenance (Component F);
- exact field order, cardinalities, and the required-versus-conditional status
  of each coordinate;
- a schema-version tag;
- immutability; and
- validation/error conditions for a missing, contradictory, or non-canonical
  coordinate.

The Result composition binds already-frozen identities by reference; it
introduces no coordinate that is not traceable to a frozen WP1–WP3 or M39/M40
authority.

### 6.2 Component B — Measure Value coordinate

Stage B must specify, on the confirmed WP1 `ADMIT` definition:

- Measure Value as a typed, unit-qualified (and currency-qualified where
  meaningful) value coordinate, reusing Unit Semantics / Valuation Semantics by
  reference, never redefining them;
- the invariant that Measure Value is present **if and only if** Computation
  Outcome is `SUCCEEDED`;
- the prohibition that Measure Value is never a second/third classification
  axis beside Computation Outcome and Degraded State; and
- that the value bytes on success are exactly the WP3 qualified canonical
  arithmetic bytes, carried without re-derivation or re-rounding.

### 6.3 Component C — Success/failure semantic closure

Stage B must specify total closure of the Result over the frozen four-value
Computation Outcome:

- exactly one Computation Outcome per Result;
- the total mapping of WP3's `INSUFFICIENT_INPUT` / `DEPENDENCY_UNRESOLVED` /
  `FAILED` / `SUCCEEDED` classification onto the Result, consumed by reference
  from WP3 §12 (WP4 does not re-classify);
- the **no-value-on-failure** rule: every non-`SUCCEEDED` outcome carries no
  Measure Value; and
- that WP4 creates no fifth outcome and no partial "success-with-error" hybrid
  outside the outcome/degraded-state matrix (Component D).

### 6.4 Component D — Outcome/degraded-state interaction matrix

Stage B must specify a deterministic, total interaction matrix over the frozen
Computation Outcome values and the frozen Degraded State term:

- every (Computation Outcome × Degraded State) combination is either an
  enumerated valid Result shape or an explicitly prohibited combination;
- the matrix is deterministic — the same coordinates yield the same cell — and
  introduces no new state token; and
- degraded-state carriage never converts a non-success outcome into a value or
  a success outcome into a failure.

### 6.5 Component E — Canonical Temporal Claim binding and Snapshot exclusion

Stage B must specify:

- the Result's Canonical Temporal Claim reusing the existing grammar,
  qualified by Event Type `Calculation` and Producing Domain
  `Market Intelligence`;
- that the Measurement Window (WP3) is an input-selection boundary and is
  distinct from the Result's own temporal claim — the two are not the same
  field and one is never substituted for the other;
- the reserved-boundary rule that a Market Measure Result MUST NOT claim the
  `Snapshot Creation` Event Type; and
- that no Calculation Temporal Claim specialization and no specialized
  Producing Domain is created.

### 6.6 Component F — Provenance carriage and lineage completeness

Stage B must specify:

- Provenance carried on the Result by reuse of the frozen term, with Market
  Intelligence as carrier and Connectivity & Ingestion as owner;
- **complete lineage**: the Result's Provenance/lineage must make the exact
  Subject identity, Manifest identity + `ObservationEvidenceCount`, Method
  Version identity + semantic version + dependency versions, and Measurement
  Window identity recoverable, so that the calculation is fully attributable;
- that lineage cites frozen identities and adds no new witnessed evidence and
  no interpolated/normalized/adjusted working value as if it were an
  Observation; and
- that Provenance is neither widened nor recaptured by WP4.

### 6.7 Component G — Result identity, canonical serialization, hash stability, round-trip

Stage B must state a byte-level canonical serialization rule for the Market
Measure Result. Because the Result both carries a `Calculation` Canonical
Temporal Claim — whose authoritative timestamp is, under the frozen
`M34-D-0005`, the calculation instant — and must have an identity that excludes
computation time, Stage B must specify these two byte views as distinct and
must not conflate them:

- the **canonical Result serialization** (the complete, round-trippable
  encoding): field order, numeric representation (inheriting WP3 canonical
  numeric bytes for Measure Value), the Canonical Temporal Claim encoding
  including its calculation-instant timestamp, Unicode normalization form, and
  an explicit schema-version tag. This is the full record that round-trips and
  carries lineage; it necessarily includes the calculation-instant timestamp;
  and
- the **Result identity basis** (the identity-determining subset of those
  canonical fields): the frozen upstream WP1–WP3 coordinates and the
  outcome/value content, from which **Result identity** is computed. The
  identity basis **excludes** the `Calculation` Canonical Temporal Claim's
  calculation-instant timestamp together with host time, request time,
  retrieval time, provider order, cache state, map-iteration order, and
  presentation labels.

The architectural rule this fixes is: the `Calculation` Canonical Temporal
Claim timestamp is **carried on** the Result — serialized, round-tripped, and
part of its lineage — but **does not participate in** Result identity. Two
Results built from identical frozen WP1–WP3 coordinates and identical
outcome/value content are the same Result — same identity, same hash — even
when their calculation-instant timestamps differ. This clarifies, and does not
redesign, Result identity, the Canonical Temporal Claim, or the Measurement
Window; the Measurement Window remains the distinct input-selection boundary of
Component E, neither substituted for the temporal claim nor part of identity.

Stage B must then specify:

- **hash stability** — applying the identity rule to the same logical Result
  twice yields a byte-identical identity basis and an identical hash, proven by
  manual / independent recomputation; and
- **round-trip** — an independent reviewer, given only the canonical Result
  serialization and the Stage B specification, can reconstruct the exact logical
  Result, and vice versa.

The rule must be consistent with, and must not restate or fork, the frozen WP2
`MSB1`/`OIM1` and WP3 numeric serialization it references.

### 6.8 Component H — WP3→WP4 handoff consumption

Stage B must specify that WP4 consumes exactly, and only, the four handoff
coordinates fixed by the WP3 closeout — Measurement Window bytes/identity,
exact semantic and dependency versions, exact qualified canonical arithmetic
bytes on success, or one frozen Computation Outcome classification — by
citation. It must specify no re-computation, no repair, and no alternate path
that would let WP4 reach a Result the WP3 semantics did not produce.

### 6.9 Component I — Partial-output / partial-result composition

Stage B must specify how, when the frozen Definition and Computation Outcome
permit independently complete output coordinates (the case WP3 §6.1 and its
§12.1 note left to the Result contract), those coordinates compose into a
Result:

- what constitutes an independently complete coordinate;
- how partial composition interacts with the no-value-on-failure rule and the
  outcome/degraded-state matrix so that a partial Result is never an
  undisclosed full success or an undisclosed failure; and
- that partial composition adds no new outcome value and remains within the
  frozen Computation Outcome closure.

---

## 7. Stage Decomposition (Deliverable 7)

WP4 remains one M41 work package. The following are internal governance stages,
not new milestone work packages. **This proposal designs neither stage's
contents** — it fixes each stage's purpose, deliverable, and review artifacts,
exactly as the confirmed WP2 and WP3 architectures did.

### 7.1 WP4 Stage A — Vocabulary Sufficiency and Semantic Surface Register

**Purpose:** Prove, before normative contract text relies on any label, that
the frozen vocabulary is sufficient for WP4 and inventory every Result/state/
provenance coordinate Stage B must close.

**Required contents (to be produced in Stage A, not here):**

- one row per component in §6;
- the governing frozen noun or ordinary-language classification for each;
- the exact owner / non-owner boundary traced to frozen authority;
- the exact upstream (WP1/WP2/WP3/M39/M40) coordinate each Result field cites;
- whether a governed dependency may be required;
- the required golden-vector rows; and
- a candidate-vocabulary determination.

**Expected vocabulary result:** no new governed noun. Market Measure Result,
Computation Outcome, and Input Sufficiency are reused as frozen; Measure Value
relies on WP1's confirmed `ADMIT`; Provenance, Canonical Temporal Claim, Event
Type, Producing Domain, Degraded State, and `Snapshot Creation` are reused /
referenced; Calculation Temporal Claim's `REJECT` is carried forward. If a
genuine candidate is discovered, Stage A must supply its exact definition,
single owner justified through the governed workflow, disposition request, full
Glossary/negative-corpus overlap analysis, V1–V3 analysis, compatibility
analysis, and candidate-level five-part gate. This proposal assigns no owner in
advance.

**Deliverable:**
`M41_WP4_STAGE_A_VOCABULARY_AND_SEMANTIC_SURFACE_REGISTER.md`

**Review artifacts:**
`M41_WP4_STAGE_A_INDEPENDENT_REVIEW.md`,
`M41_WP4_STAGE_A_REQUIRED_CORRECTIONS_RESPONSE.md` (if required),
`M41_WP4_STAGE_A_INDEPENDENT_CONFIRMATION.md`.

**Completion criterion:** unconditional `CONFIRMED`, with no open finding and
no candidate relied upon before its confirmed disposition. Any confirmed
`ADMIT`/`RENAME` Glossary synchronization is recorded in the same change as
that confirmation, per the frozen M41 workflow.

### 7.2 WP4 Stage B — Result, State, and Provenance Contract Specification

**Purpose:** Write the complete normative contract described in §§1, 6,
using only frozen or Stage A-confirmed vocabulary.

**Required contents (to be produced in Stage B, not here):**

- Market Measure Result concrete composition, identity, serialization,
  validation, and errors;
- Measure Value coordinate and the present-iff-`SUCCEEDED` invariant;
- success/failure closure and no-value-on-failure rule;
- outcome/degraded-state interaction matrix;
- Canonical Temporal Claim binding and `Snapshot Creation` exclusion;
- Provenance carriage and complete-lineage rule;
- Result identity, canonical bytes, hash stability, and round-trip evidence;
- partial-output/partial-result composition;
- WP3-handoff consumption rules;
- field-level five-part gate table;
- compatibility analysis against every authority in §9; and
- the complete golden-vector matrix (§8) with explicit non-production/
  non-operational authority statements.

**Deliverable:**
`M41_WP4_STAGE_B_RESULT_STATE_PROVENANCE_CONTRACT_SPECIFICATION.md`

**Review artifacts:**
`M41_WP4_STAGE_B_INDEPENDENT_REVIEW.md`,
`M41_WP4_STAGE_B_REQUIRED_CORRECTIONS_RESPONSE.md` (if required),
`M41_WP4_STAGE_B_INDEPENDENT_CONFIRMATION.md`.

**Review requirement:** independent architectural review, including
serialization/identity verification (hash-stability and round-trip
recomputation).

**Completion criterion:** `APPROVED`, or `APPROVED WITH REQUIRED CORRECTIONS`
followed by full resolution and unconditional `CONFIRMED`, with zero open
findings and affirmative proof of hash stability, no-value-on-failure,
complete lineage, and round-trip serialization with no ambient default.

### 7.3 WP4 closeout

After Stage B confirmation, a WP4 closeout records only the already-proven
status, authorities, deliverables, and readiness for M41 Epic Closeout. It adds
no semantics and serves as no correction vehicle.

**Deliverable:** `M41_WP4_CLOSEOUT.md`.

---

## 8. Deliverables (Deliverable 9) and Required Validation Evidence

### 8.1 Document deliverables

- `docs/implementation/M41_WP4_ARCHITECTURE_PROPOSAL.md` (this document);
- its independent architecture review, corrections response (if required), and
  confirmation;
- the Stage A register and its review chain (§7.1);
- the Stage B contract and its review chain (§7.2); and
- `M41_WP4_CLOSEOUT.md` (§7.3).

### 8.2 Validation evidence — specification-only

All validation evidence is documentation or data-fixture material. No committed
test runner, reference implementation, conformance harness, or Result-building
code is authorized (M41 Architecture §13). Each golden vector records: exact
canonical input coordinates, exact expected canonical Result bytes **or** the
exact non-success classification and its no-value consequence, the semantic
rule under test, every exact semantic and dependency version used, a short
independently reproducible derivation, and an explicit non-production
statement.

### 8.3 Minimum golden-vector matrix

| Vector | Required proof |
|---|---|
| Success Result | `SUCCEEDED` carries exactly the WP3 qualified arithmetic bytes as Measure Value |
| No value on `INSUFFICIENT_INPUT` | Result carries the outcome and **no** Measure Value |
| No value on `DEPENDENCY_UNRESOLVED` | Result carries the outcome and no Measure Value |
| No value on `FAILED` | Result carries the outcome and no Measure Value |
| Measure Value present-iff-`SUCCEEDED` | Presence/absence matches the outcome exactly, both directions |
| Hash stability | Two independent serializations of the same logical Result are byte-identical |
| Round-trip | Bytes → logical Result → bytes reproduces identical bytes |
| Identity independence | Two Results differing only in host/request/computation time — including the `Calculation` Canonical Temporal Claim's calculation-instant timestamp — provider order, or cache state have identical Result identity |
| Dependency-version sensitivity | A changed Method Version dependency version changes Method Version identity and therefore the Result identity |
| Complete lineage | Subject, Manifest identity + `ObservationEvidenceCount`, Method Version identity + versions, and Measurement Window identity are all recoverable from the Result |
| Event Type `Calculation` | The Result's Canonical Temporal Claim carries Event Type `Calculation`, Producing Domain `Market Intelligence` |
| Snapshot exclusion | A Result claiming `Snapshot Creation` is non-conforming |
| Outcome/degraded-state matrix | Each enumerated (outcome × degraded-state) cell yields its exact Result shape; each prohibited cell is rejected |
| Provenance non-laundering | An interpolated/normalized/adjusted working value never appears as witnessed Observation lineage |
| Partial composition | An independently complete coordinate composes without becoming an undisclosed full success or failure |
| Calculation Temporal Claim absence | No rejected specialization appears under any name |

Stage B may split these into multiple fixture files but may not omit a row or
merge materially distinct risks into one vague example.

### 8.4 Negative-corpus validation

Independent review must confirm WP4 contains none of: Calculation Temporal
Claim or a renamed equivalent; a specialized Producing Domain; a fifth
Computation Outcome value or new state token; a Result claiming `Snapshot
Creation`; a redefinition, widening, or recapture of Provenance; Ledger,
Portfolio, Workspace, Wealth, judgment, recommendation, execution, or
presentation semantics; a production method, formula, registry, resolver,
kernel, endpoint, schema, persistence, provider, or runtime design; or any
executable validation artifact.

---

## 9. Compatibility Requirements

### 9.1 M34 compatibility

- `M34-D-0004`: Result composition infers no Asset identity or classification.
- `M34-D-0005`: the Result reuses the existing Canonical Temporal Claim /
  Degraded State grammar; it creates no temporal-claim specialization, no
  Producing Domain specialization, and no ambient-clock meaning.
- `M34-D-0010`: descriptive calculation Results remain separate from portfolio
  meaning, judgment, evaluation, execution, and presentation.

### 9.2 M39 compatibility

WP4 lineage preserves every referenced Observation's exact identity and
source-established meaning; it never merges identity-distinct Observations by
value/timestamp equality, never manufactures precision, and never rewrites an
Observation when a derived value is carried as a Result coordinate.

### 9.3 M40 compatibility

WP4 preserves the four-category input closure, Deterministic Calculation's
byte-identical-output requirement, the four-value Computation Outcome closure,
the frozen Market Measure Result / Input Sufficiency meanings, and the empty
production Definition/Method catalog.

### 9.4 M41-WP1 / WP2 / WP3 compatibility

WP4 adds no Definition/Method Version/Method Requirement field, no Subject/
Manifest field, and no Measurement Window or semantics rule; it changes no
frozen byte, identity, membership, or order; and it consumes the WP3 handoff by
exact reference without re-derivation, per §§2, 6.8.

---

## 10. Review Strategy (Deliverable 10)

The dependency-safe governance sequence is:

1. Independently review this WP4 Architecture Proposal.
2. Resolve every required architecture correction individually.
3. Obtain unconditional Independent Architecture Confirmation; freeze the
   confirmed WP4 Architecture.
4. Draft Stage A's vocabulary/semantic-surface register (§7.1).
5. Independently review Stage A, resolve required corrections, and obtain
   unconditional confirmation. If Stage A unexpectedly finds an `ADMIT`/
   `RENAME` candidate, record its unconditional confirmation and required
   Glossary synchronization in the same change; otherwise make no Glossary
   change.
6. Draft Stage B in dependency order: Result composition/identity → Measure
   Value → success/failure closure → outcome/degraded-state matrix → Canonical
   Temporal Claim binding + Snapshot exclusion → Provenance carriage/lineage →
   Result identity/serialization/hash/round-trip → partial composition →
   handoff-consumption → integrated vectors, gate, and compatibility proof.
7. Perform independent architectural + serialization/identity review of Stage
   B.
8. Resolve all findings and repeat confirmation until unconditional `CONFIRMED`
   with zero open findings.
9. Record the WP4 closeout without adding semantics.
10. Only then is M41 eligible for Epic Closeout (§13).

No stage begins before the preceding gate is confirmed. Epic Closeout cannot
infer or repair a WP4 ambiguity; an unresolved Result-surface default blocks
WP4 closeout.

---

## 11. Acceptance Criteria (Deliverable 11)

This proposal is architecturally acceptable only if Independent Review confirms
all of the following:

1. Scope exactly matches frozen M41-WP4 (M41 Architecture §6) and reopens no
   part of WP1, WP2, or WP3.
2. Market Measure Result, Computation Outcome, and Input Sufficiency are reused
   with frozen M40 meaning; no fifth outcome is created.
3. Measure Value relies on WP1's confirmed `ADMIT` and is present iff
   `SUCCEEDED`, never a new axis.
4. Provenance and Canonical Temporal Claim are reused, not redefined; Event
   Type `Calculation` / Producing Domain `Market Intelligence` is used; no
   Calculation Temporal Claim reappears.
5. A Result may never claim the reserved `Snapshot Creation` Event Type.
6. The outcome/degraded-state interaction matrix is deterministic and total and
   introduces no new state token.
7. Result identity, canonical serialization, hash stability, and round-trip are
   mandatory and specification-only, and identity excludes every operational
   coordinate.
8. No-value-on-failure, complete lineage, and partial-composition rules are
   explicit.
9. The WP3 handoff is consumed by exact citation with no re-derivation.
10. Every concrete Stage B field must pass the five-part ownership gate; the
    witnessed-versus-computed distinction is preserved.
11. No new noun is used before unconditional confirmation and synchronization.
12. The production Definition/Method catalog remains empty.
13. Implementation, runtime, provider, persistence, API, production, and
    executable-validation authority remain `NONE`.
14. The stage decomposition is sufficient for independent review and
    confirmation exactly as WP2 and WP3 were.
15. WP4 completes every remaining M41-allocated semantic responsibility, so
    that M41 Epic Closeout has no outstanding semantic obligation.

---

## 12. Closeout Conditions (Deliverable 12)

WP4 is eligible for its own closeout only when:

- the WP4 Architecture is confirmed and frozen;
- Stage A is confirmed with no candidate relied on before confirmation;
- Stage B is `CONFIRMED` and `FROZEN` with zero open findings and affirmative
  proof of hash stability, no-value-on-failure, complete lineage, and
  round-trip serialization;
- every required correction is resolved and, where it affected a disposition,
  independently confirmed; and
- `M41_WP4_CLOSEOUT.md` records the status without adding semantics.

The WP4 closeout, like the WP3 closeout, performs documentation-only
reconciliation: it adds the closeout record, records the closeout decision in
the Decision Log, and updates the Implementation Index. It refreshes no
Graphify output and modifies no frozen artifact.

---

## 13. Relationship to M41 Epic Closeout (Deliverable 13)

WP4 is the **terminal** M41 work package. Per M41 Architecture §11, Epic
Closeout is not a numbered work package but a milestone-level artifact
(`M41_EPIC_CLOSEOUT.md`) produced after WP4, performing whole-corpus
reconciliation across WP1–WP4.

On WP4 confirmation and closeout:

- every semantic responsibility M41 Architecture §4/§6 allocated —
  Definition/Method/Applicability (WP1), Subject/Manifest (WP2),
  Temporal/Unit/Adjustment/Arithmetic (WP3), and Result/State/Provenance (WP4)
  — is complete, leaving **no outstanding M41 semantic obligation**;
- Epic Closeout may then verify that the §8 five-part ownership gate held across
  all four work packages, that the production Definition/Method catalog is still
  empty, and that no negative-corpus item reappeared;
- the consolidated Decision Log entry recording the full M41 admission/rejection
  set (including Measure Value `ADMIT`, the Provenance/Canonical Temporal Claim
  `REUSE`s, and the Calculation Temporal Claim `REJECT`) is added at Epic
  Closeout, not here; and
- the Graphify refresh is performed only after `M41_EPIC_CLOSEOUT.md` is itself
  independently reviewed and any required correction confirmed (M41 Architecture
  §§13–15).

This proposal authorizes none of those closeout actions. It establishes only
that WP4's architecture is sufficient to permit eventual M41 Epic Closeout once
WP4's own review chain completes.

---

## 14. Repository and Governance Effects

This proposal creates only:

- `docs/implementation/M41_WP4_ARCHITECTURE_PROPOSAL.md`

It does not modify frozen M41, WP1, WP2, or WP3 artifacts; `docs/GLOSSARY.md`;
the Decision Log; the Implementation Index; Graphify output; architecture
constitutions; or source code, tests, fixtures, schemas, or configuration.
Per the frozen M41 convention, Decision Log reconciliation and Graphify refresh
remain Epic Closeout work after WP4 and independent closeout confirmation.
Creating this proposal is authority to perform neither.

---

## 15. Final Architectural Boundary

M41-WP4 begins with the exact frozen coordinates handed off by WP1
(Definition/Method Version identity and versions), WP2 (Subject/Manifest
identity and bytes), and WP3 (Measurement Window bytes, qualified arithmetic
bytes, or one frozen Computation Outcome classification). It ends with a fully
explicit, version-bound, canonically serializable, hash-stable, round-trippable
**Market Measure Result** — one value on success, one frozen non-success
classification otherwise — carrying a complete lineage, a `Calculation`
temporal claim, and reused Provenance, with no ambient default and no value on
any non-success outcome.

It changes no upstream contract and creates no downstream authority. Its
decisive completion test is that two independent readers, given the same frozen
WP1–WP3 coordinates and the WP4 specification, derive the same Result bytes,
the same Result identity, and the same outcome/degraded-state classification,
without consulting a clock, locale, provider, registry default, mutable
dependency, or unstated convention.

---

## Final Status

**READY FOR INDEPENDENT ARCHITECTURE REVIEW**
