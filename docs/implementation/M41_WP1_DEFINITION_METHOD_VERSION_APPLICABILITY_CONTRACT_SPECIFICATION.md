# M41-WP1 — Market Measure Definition, Method Version, and Applicability Contract Specification

**Date:** 2026-07-23

**Milestone:** M41 — Canonical Asset Market Measure Contract Specification

**Document class:** Constitutional semantic contract specification

**Workflow stage:** M41-WP1 stage 2 of 2 (Candidate Vocabulary and Ownership
Register → **Market Measure Definition, Method Version, and Applicability Contracts**).
Stage 1 — the
[Candidate Vocabulary and Ownership Register](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md)
— is `CONFIRMED`
([M41_WP1_INDEPENDENT_CONFIRMATION.md](M41_WP1_INDEPENDENT_CONFIRMATION.md))
and frozen. This document is the contract text the M41 architecture proposal
§6 (M41-WP1 bullet) and §11 (M41-WP1 row) requires next: *"Definition and
immutable Method Version contracts, requirement vocabulary, and the
specification of a future method-admission gate and registry invariants
follow from that register."*

**Status:** `FINAL2_REQUIRED_CORRECTIONS_APPLIED_PENDING_INDEPENDENT_CONFIRMATION`
— [M41_WP1_STAGE2_INDEPENDENT_REVIEW.md](M41_WP1_STAGE2_INDEPENDENT_REVIEW.md)
returned `APPROVED WITH REQUIRED CORRECTIONS`, resolved by
[M41_WP1_STAGE2_REQUIRED_CORRECTIONS_RESPONSE.md](M41_WP1_STAGE2_REQUIRED_CORRECTIONS_RESPONSE.md);
the subsequent
[M41_WP1_STAGE2_INDEPENDENT_CONFIRMATION.md](M41_WP1_STAGE2_INDEPENDENT_CONFIRMATION.md)
returned `NOT CONFIRMED`, identifying four still-unresolved portions of
those same corrections (not new findings); a first final revision resolved
`M41-WP1-S2-IR-1` and `M41-WP1-S2-IR-3` in full, per
[M41_WP1_STAGE2_FINAL_REQUIRED_CORRECTIONS_RESPONSE.md](M41_WP1_STAGE2_FINAL_REQUIRED_CORRECTIONS_RESPONSE.md).
The subsequent
[M41_WP1_STAGE2_FINAL_INDEPENDENT_CONFIRMATION.md](M41_WP1_STAGE2_FINAL_INDEPENDENT_CONFIRMATION.md)
confirmed `M41-WP1-S2-IR-1` and `M41-WP1-S2-IR-3` `RESOLVED` and returned
`NOT CONFIRMED` overall, identifying two still-unresolved portions of
`M41-WP1-S2-IR-2` and `M41-WP1-S2-IR-4` (again, not new findings); this
revision resolves those two remaining portions in full, per
[M41_WP1_STAGE2_FINAL2_REQUIRED_CORRECTIONS_RESPONSE.md](M41_WP1_STAGE2_FINAL2_REQUIRED_CORRECTIONS_RESPONSE.md).
This document does not itself begin a further Independent Confirmation.

**Canonical vocabulary admission by this specification:** `NONE` — this
document coins no new noun; it specifies contract text for the three nouns
Stage 1 already confirmed `ADMIT` for M41-WP1's own use (§4).

**Implementation authority:** `NONE`

**Runtime authority:** `NONE`

**Production method authority:** `NONE`

**Provider authority:** `NONE`

**Persistence authority:** `NONE`

**API and public-exposure authority:** `NONE`

**Decision Log status:** `NOT_SUBMITTED`

**Supersedes:** `NONE`

**Closeout:** `NONE`

**Stage 1 authority (frozen, not reopened by this document):**
[M41-WP1 Candidate Vocabulary and Ownership Register](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md),
independently reviewed
([M41_WP1_INDEPENDENT_REVIEW.md](M41_WP1_INDEPENDENT_REVIEW.md)), corrected
([M41_WP1_REQUIRED_CORRECTIONS_RESPONSE.md](M41_WP1_REQUIRED_CORRECTIONS_RESPONSE.md)),
and independently confirmed
([M41_WP1_INDEPENDENT_CONFIRMATION.md](M41_WP1_INDEPENDENT_CONFIRMATION.md)).

**Document role:** The Market Measure Definition, Method Version, and
Applicability contract specification required by the approved
[M41 Architecture Proposal](M41_ARCHITECTURE_PROPOSAL.md) §6 (M41-WP1
bullet) and §11 (M41-WP1 row), building exclusively on the three `ADMIT`
candidates Stage 1 confirmed for this contract's own use: Market Measure
Definition, Method Version, and Method Requirement (the noun that realizes
the proposal's "Applicability" contract type — Stage 1 register §6.0: *"the
contract type Method Requirement... instantiates; it is not a separate noun
requiring its own entry"*). This document does not reopen Stage 1, does not
admit, rename, or redefine any candidate, and does not itself constitute
independent review, required corrections, or independent confirmation of its
own text — those stages follow this document, per the same five-stage
discipline Stage 1 completed (M41 proposal §8).

**Normative language:** `MUST`, `MUST NOT`, `SHALL`, `SHALL NOT`, `MAY`, and
`SHOULD` are normative within this specification, in the same sense Stage 1
used them: they state the requirements this contract text proposes for
independent review. They acquire no repository authority beyond that until
this document is itself independently reviewed, corrected if required, and
independently confirmed.

---

## 1. Purpose

This document specifies the semantic contracts for **Market Measure
Definition**, **Method Version**, and **Applicability** (realized by
**Method Requirement**) — the three constitutional nouns Stage 1 confirmed
`ADMIT` for M41-WP1's own contract text, per the Stage 1 register's
disposition summary
([§11](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md#11-disposition-summary))
and the Independent Confirmation's unconditional confirmation of that
disposition set.

It supplies exactly the "future contract acceptance evidence" each of these
three candidates' Stage 1 entry named as its own downstream obligation
([register §6.1](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md#61-market-measure-definition),
[§6.2](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md#62-method-version),
[§6.3](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md#63-method-requirement)):
exact vocabulary and format left open at the specification level, at least
one worked example demonstrating each candidate's constitutional constraints
hold, and the frozen M40 five-part ownership-boundary gate applied again to
each contract's concrete fields.

This document does not specify Measure Subject, Measurement Window, Measure
Value, Observation Input Manifest, or Provenance contract text — those
remain M41-WP2 and M41-WP4 obligations (§3, §12).

## 2. Governing Authority

This specification is subordinate to repository authority. Where this
document conflicts with an approved or frozen authority, that authority
governs and the conflicting contract text is inadmissible.

The governing corpus is:

- [Platform Architecture](../architecture/platform_architecture.md),
  especially §11 (Architecture Governance) and §12 (Canonical Vocabulary);
- [Canonical Glossary](../GLOSSARY.md) in its complete current state;
- [M34 Decision Register](m34/audit/registers/decision_register.md):
  `M34-D-0004`, `M34-D-0005`, and `M34-D-0010`;
- the complete frozen M39 corpus
  ([Epic Closeout](M39_EPIC_CLOSEOUT.md));
- the complete frozen M40 corpus
  ([Epic Closeout](M40_EPIC_CLOSEOUT.md),
  [M40-WP1](M40_WP1_Canonical_Market_Measure_Vocabulary_and_Ownership_Specification.md),
  [M40-WP2](M40_WP2_Canonical_Market_Measure_Vocabulary_Admission_Review.md));
- the approved [M41 Architecture Proposal](M41_ARCHITECTURE_PROPOSAL.md) and
  its independent confirmation
  ([M41_ARCHITECTURE_INDEPENDENT_CONFIRMATION.md](M41_ARCHITECTURE_INDEPENDENT_CONFIRMATION.md));
  and
- the confirmed
  [M41-WP1 Candidate Vocabulary and Ownership Register](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md)
  and its
  [Independent Confirmation](M41_WP1_INDEPENDENT_CONFIRMATION.md), which are
  now normative authority for this document and are not reopened by it.

### 2.1 Authority order

1. repository constitution, approved Decision Register decisions, and the
   Canonical Glossary;
2. frozen milestone specifications and closeouts (M29–M40);
3. the independently approved and confirmed M41 architecture;
4. the confirmed M41-WP1 Stage 1 register (candidate meaning, ownership,
   and disposition — frozen, not reinterpreted here);
5. this contract specification; and
6. any future M41-WP2–WP4 contract text.

No lower item MAY reinterpret, weaken, or silently narrow a higher item. In
particular, this document MUST NOT alter the proposed exact definition,
ownership, permitted/forbidden inputs, or five-part gate result any Stage 1
entry already recorded; it may only add the field-level, worked-example, and
gate-reapplication detail Stage 1 itself deferred to this stage.

### 2.2 Reliance boundary

Per M41 proposal §8 stage 5, Market Measure Definition, Method Version, and
Method Requirement may be relied upon by this document because their
disposition is independently confirmed (§4). This document's own contract
text has completed independent review, which returned `APPROVED WITH
REQUIRED CORRECTIONS`
([M41_WP1_STAGE2_INDEPENDENT_REVIEW.md](M41_WP1_STAGE2_INDEPENDENT_REVIEW.md)),
and a first revision applied those required corrections
([M41_WP1_STAGE2_REQUIRED_CORRECTIONS_RESPONSE.md](M41_WP1_STAGE2_REQUIRED_CORRECTIONS_RESPONSE.md)).
An Independent Confirmation of that revision returned `NOT CONFIRMED`
([M41_WP1_STAGE2_INDEPENDENT_CONFIRMATION.md](M41_WP1_STAGE2_INDEPENDENT_CONFIRMATION.md)),
identifying four unresolved portions of the same required corrections
(`M41-WP1-S2-IR-1` through `-IR-4`) — not new findings or architectural
recommendations. A first final revision resolved those portions
([M41_WP1_STAGE2_FINAL_REQUIRED_CORRECTIONS_RESPONSE.md](M41_WP1_STAGE2_FINAL_REQUIRED_CORRECTIONS_RESPONSE.md)).
A subsequent Independent Confirmation of that revision again returned
`NOT CONFIRMED`
([M41_WP1_STAGE2_FINAL_INDEPENDENT_CONFIRMATION.md](M41_WP1_STAGE2_FINAL_INDEPENDENT_CONFIRMATION.md)),
confirming `M41-WP1-S2-IR-1` and `M41-WP1-S2-IR-3` `RESOLVED` and
identifying two still-unresolved portions of `M41-WP1-S2-IR-2` and
`M41-WP1-S2-IR-4` — again not new findings or architectural
recommendations. This revision resolves those two remaining portions
([M41_WP1_STAGE2_FINAL2_REQUIRED_CORRECTIONS_RESPONSE.md](M41_WP1_STAGE2_FINAL2_REQUIRED_CORRECTIONS_RESPONSE.md)).
This document is not yet independently confirmed: no later M41 work
package, later section of this document, or fixture may treat any *contract
detail* introduced here (field names, worked examples, gate re-application
results) as canonical or reliable until this document completes independent
confirmation. Only the underlying candidate *terms* — not this document's
contract text — are already confirmed.

`GLOSSARY.md` synchronization for the confirmed `ADMIT` terms remains a
separate, not-yet-performed action; see §4.4. This document does not perform
that synchronization and does not assert that `GLOSSARY.md` currently
contains these terms.

## 3. Scope

This document specifies, for Market Measure Definition, Method Version, and
Method Requirement (Applicability) only:

- semantic purpose;
- exact meaning and canonical identity;
- ownership (inherited from Stage 1, restated for traceability, not
  re-decided);
- required fields and their exact meaning;
- invariants;
- admissible relationships between the three contracts;
- constitutional constraints, including the frozen M40 five-part
  ownership-boundary gate re-applied at the field level;
- references to existing canonical vocabulary these contracts consume by
  reference;
- prohibited interpretations;
- validation requirements a future independent review can mechanically
  check; and
- a specification-only description of a future method-admission gate and
  future registry invariants — described, not exercised (§8, §9).

It does not govern:

- Measure Subject or Observation Input Manifest binding rules (M41-WP2);
- Measurement Window, unit, adjustment, or arithmetic rule text (M41-WP3);
- Measure Value, Result, Computation Outcome interaction, or Provenance
  model text (M41-WP4);
- software design, implementation, runtime, persistence, provider, or API
  behavior; and
- production registration or method admission — the production Market
  Measure Definition/Method Version catalog remains empty (§8.4, M41
  proposal §7).

Naming a field in this document specifies candidate contract meaning only.
It authorizes no schema, module, service, endpoint, or executable process.

## 4. Vocabulary Provenance

Every noun this document uses traces to exactly one of: a Stage 1 `ADMIT`
candidate confirmed for M41-WP1's own reliance, an existing `GLOSSARY.md`
entry reused by reference, or ordinary non-canonical contract language that
Stage 1's own §6.0 inventory already classified as such. This document
admits no additional candidate.

### 4.1 Confirmed `ADMIT` candidates relied upon (Stage 1, confirmed)

| Term | Stage 1 entry | Owner | Confirmed |
| --- | --- | --- | --- |
| Market Measure Definition | [register §6.1](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md#61-market-measure-definition) | Market Intelligence | Yes — [Independent Confirmation §WP1-IR-5](M41_WP1_INDEPENDENT_CONFIRMATION.md) |
| Method Version | [register §6.2](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md#62-method-version) | Market Intelligence | Yes |
| Method Requirement (realizes "Applicability") | [register §6.3](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md#63-method-requirement) | Market Intelligence | Yes |

Measure Subject, Measurement Window, and Measure Value are also confirmed
`ADMIT` candidates, but their owning work packages are M41-WP2 and M41-WP4,
not M41-WP1; this document references them only where Stage 1 itself already
established a relationship (e.g., Method Requirement's declared prerequisite
categories may name "subject shape" and "Observation category availability"
in the abstract, per register §6.3) and never specifies their own contract
fields.

### 4.2 Existing `GLOSSARY.md` entries reused by reference

Market Measure, Calculated Market Measure, Computation Outcome, Observation
Input Manifest, Input Sufficiency, Deterministic Calculation, Mechanical
Boundary Rules (M40, effective); Definition Version, Asset Definition, Unit
Semantics, Valuation Semantics (Asset Foundation); Canonical Temporal Claim,
Event Type, Producing Domain, Degraded State (`M34-D-0005`). Every reference
below cites these with their frozen meaning; none is redefined, narrowed, or
widened.

### 4.3 Ordinary non-canonical contract language

"Semantic version identifier," "dependency version," "prerequisite
category," "admission gate," "registry," "evaluation rule," "requirement
key," the §7.4a evaluation-rule grammar's own syntax tokens (`AND`, `OR`,
`NOT`, `EXISTS`, the comparators, `SubjectShape`, `Dependency(...)`,
`ObservationEvidenceCount`), and similar phrases used below are descriptive
prose or ordinary predicate-grammar syntax, not proposed candidate nouns — consistent with Stage 1's own treatment of "canonical
serialization," "manifest identity," and "missing-data specification" as
ordinary non-canonical contract language
([register §6.0](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md#60-complete-noun-inventory)).
None of these phrases is admitted, reserved, or given independent ownership
by this document.

### 4.4 `GLOSSARY.md` synchronization status

As of this document, `GLOSSARY.md` does not yet contain entries for Market
Measure Definition, Method Version, or Method Requirement. The Independent
Confirmation recorded canonical vocabulary admission as `NONE`
([M41_WP1_INDEPENDENT_CONFIRMATION.md](M41_WP1_INDEPENDENT_CONFIRMATION.md)).
Per M41 proposal §8 stage 5, synchronization is a distinct action, performed
in the same change as confirmation of the *disposition*, and remains
outstanding as repository state independent of this document. This
specification does not perform that synchronization, does not modify
`GLOSSARY.md`, and does not assert these terms are currently discoverable
there. Whichever future change performs synchronization is expected to cite
this document's exact definitions (§5.1, §6.1, §7.1) as the definition text,
subject to that change's own review.

## 5. Market Measure Definition Contract

### 5.1 Exact meaning (inherited, unmodified)

A Market Measure Definition is an immutable, versioned specification record
identifying which Market Measure or Calculated Market Measure concept a
family of Method Versions realizes, including its declared subject shape,
required output coordinate meaning, and permitted input-category
declaration. It admits no formula, named indicator, reference calculation,
or production method
([register §6.1](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md#61-market-measure-definition)).

### 5.2 Owner

Market Intelligence. Non-owners: Asset Foundation, Ledger & Accounting,
Portfolio Intelligence, Decision Intelligence, Trust & Evaluation, Wealth
Intelligence, Experience Platform, providers, storage, and runtime
mechanisms (unchanged from Stage 1).

### 5.3 Canonical identity

A Market Measure Definition's identity is the exact, immutable combination
of:

1. an explicit, stable Market Measure Definition identifier, assigned once at
   proposal time and never reused for a different semantic meaning;
2. the exact bound Market Measure or Calculated Market Measure concept it
   realizes (§4.2); and
3. an explicit revision indicator, incremented only by an additive or
   narrowing amendment that does not change the meaning of any already-bound
   Method Version (§5.6).

Two Market Measure Definition records with the same Market Measure
Definition identifier and revision indicator MUST denote the exact same
semantic specification.
Identity MUST NOT depend on record order, storage location, or any runtime
or provider-shaped value.

### 5.4 Required fields

A Market Measure Definition record MUST declare, and MUST declare no other
semantic field:

| Field | Meaning | Permitted values |
| --- | --- | --- |
| Market Measure Definition identifier | Stable identity (§5.3) | Explicit, platform-assigned; never a formula name or provider term |
| Bound umbrella concept | Which existing Market Measure / Calculated Market Measure concept this Market Measure Definition realizes | Exactly one of the two already-admitted M40 umbrella terms (§4.2); constrained further by §5.5's witnessed-versus-computed invariant |
| Declared subject shape | Which of the three closed Measure Subject shapes a Method Version realizing this Market Measure Definition must accept | A non-empty subset of exactly the three closed shapes register [§6.4](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md#64-measure-subject) already names: (a) a single canonical Asset identity reference; (b) an ordered, canonical reference set of two or more Asset identities; (c) an explicit market-context parameter set with no Asset identity reference. This Market Measure Definition declares only which of these three named shapes it requires; it does not itself define Measure Subject's own identity, ordering, or binding rules (M41-WP2) |
| Required output coordinate meaning | What question the output answers | An explicit citation to exactly one of the four already-admitted Valuation Semantics questions (§4.2): `Identity`; `Continuous quotation`; `Periodic NAV`; `Appraisal-on-event` — cited by that exact name only, never restated, paraphrased, or extended with additional prose |
| Permitted input-category declaration | Which of the frozen M40 four-category closure this Market Measure Definition's realizing Method Versions may draw upon | A non-empty subset of: M39 Observation evidence; Asset Foundation reference data; explicit invocation parameters; explicit governed calculation dependencies |
| Revision indicator | Version of this Market Measure Definition's own text (§5.3) | Monotonically increasing per Market Measure Definition identifier |

No field MAY carry a concrete formula, named indicator, reference
calculation, provider-shaped value, or ambient default. A field left
unstated is absent, never implicitly filled. The required output coordinate
meaning field's closure to the four named Valuation Semantics questions is a
citation restriction only: it reuses `GLOSSARY.md`'s already-admitted
Valuation Semantics closed set (§4.2) and admits no new output-coordinate
vocabulary of its own.

### 5.5 Relationship to Method Version

Exactly one Market Measure Definition (at exactly one revision) is bound by
any one Method Version (§6.4). A Market Measure Definition MAY be realized
by zero, one, or many Method Versions across its lifetime; it does not
enumerate or own the Method Versions that bind to it, consistent with M40's
witnessed-versus-computed ownership discipline — the Market Measure
Definition states what is claimed; the Method Version states how it is
computed.

**Witnessed-versus-computed invariant (frozen M40 boundary, made operative
here).** A Method Version is, by its own exact meaning (§6.1) and its
Deterministic Calculation constraint (§6.5), inherently computational. It
follows that:

- a source-reported claim remains an M39 Observation, carries Event Type
  `Observation`, and is never produced by, attributed to, or represented as
  the output of a Method Version; and
- every output actually produced by invoking a Method Version bound to a
  Market Measure Definition is a Calculated Market Measure, carries Event
  Type `Calculation`, and carries Producing Domain `Market Intelligence`
  (§4.2) — regardless of which of the two already-admitted M40 umbrella
  terms (`Market Measure` or `Calculated Market Measure`, §4.2) that Market
  Measure Definition's own Bound umbrella concept field (§5.4) names.

The Bound umbrella concept field states only the general semantic category
the Market Measure Definition's declared subject and output fall under in
the abstract, per Stage 1's own inherited meaning (§5.1); it MUST NOT be
read as reclassifying, or as authority to reclassify, what a specific Method
Version's realized output actually is. No Market Measure Definition/Method
Version combination admitted by this contract MAY recast a source-reported,
M39-Observation-carried claim as a platform calculation, or vice versa.

### 5.6 Revision invariants

- A new revision of a Market Measure Definition MUST be additive or
  narrowing only with respect to already-bound Method Versions: it MUST NOT
  retroactively change the meaning any existing Method Version's binding
  already relied upon.
- A revision that would change the bound umbrella concept, the required
  output coordinate meaning's fundamental question, or remove a
  permitted-input category a bound Method Version already relies upon MUST
  instead be a new Market Measure Definition identifier, not a revision.
- A revision that would add, remove, or otherwise change the declared
  subject shape subset (§5.4) MUST likewise instead be a new Market Measure
  Definition identifier, not a revision: a bound Method Version's
  applicability (§7) may depend on the exact subject-shape subset its
  binding was specified against, and a subject-shape change is therefore
  never additive-or-narrowing-only with respect to that binding.
- Market Measure Definitions are never rewritten in place (mirrors the
  Domain Constitution precedent, Platform Architecture §11 G5: a wrong
  ruling is superseded, not edited).

### 5.7 Prohibited interpretations

A Market Measure Definition MUST NOT be interpreted, presented, or consumed
as:

- an executable formula or a promise that any Method Version currently
  realizes it (the production catalog remains empty, §8.4);
- an Asset capability grant (Definition Version and Asset Definition remain
  Asset Foundation's exclusive identity/capability authority, §4.2);
- a correctness, trust, reliability, or recommendation claim; or
- a Ledger, Portfolio, or Wealth Intelligence subject, input, or output
  (Stage 1 five-part gate, re-verified at §11.1).

### 5.8 Worked example (illustrative only — no production admission)

The following is a non-admitted, illustrative worked example proving the
contract's fields are usable, not a production Market Measure Definition:

```
Market Measure Definition identifier: "market-measure-definition:example-price-level"
Bound umbrella concept:               Calculated Market Measure
Declared subject shape:               { single canonical Asset identity reference }
Required output coordinate meaning:   Identity
Permitted input categories:           { M39 Observation evidence }
Revision indicator:                   1
```

This example names no formula, no provider, and no production method. It
demonstrates only that the required-fields table (§5.4) is complete enough
to instantiate a record without an implicit default. It is explicitly
non-admitted (M41 proposal §7).

**Identity, ownership, version-axis, and non-substitutability
demonstration.** This illustrative record shows the four properties Stage 1
required a worked example to demonstrate (register §6.1 future contract
acceptance evidence):

- **Identity.** `market-measure-definition:example-price-level` at revision
  `1` is this record's entire canonical identity (§5.3); it is not, and does
  not reference, any Asset's own identity.
- **Ownership.** This record is Market Intelligence-owned specification text
  about a family of calculations; it grants no Asset capability and is not
  itself an Asset Definition, which Asset Foundation alone owns (§5.7).
- **Version-axis separation.** The `Revision indicator: 1` versions this
  Market Measure Definition's own text (§5.3, §5.6). It is a distinct axis
  from, and is never compared, merged, or substituted with, any Asset
  Definition Version — which versions a wholly different subject, an
  Asset's own definition, under Asset Foundation's exclusive ownership
  (§6.6's non-conflation invariant applies identically here by the same
  reasoning).
- **Non-substitutability.** Citing `Identity` as the required output
  coordinate meaning (§4.2) does not import, alter, or grant standing to
  reinterpret the Valuation Semantics `Identity` question's own Asset
  Foundation-owned meaning; this Market Measure Definition only references
  that already-admitted question by exact name and answers no other
  question in its place.

## 6. Method Version Contract

### 6.1 Exact meaning (inherited, unmodified)

A Method Version is an immutable, version-identified specification record
binding to exactly one Market Measure Definition, declaring its semantic
version, its dependency versions, and its Method Requirement set. It is the
version-controlled unit a future, separately chartered method-admission
mechanism would evaluate for admission. It admits no concrete formula or
production method
([register §6.2](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md#62-method-version)).

### 6.2 Owner

Market Intelligence. Non-owners unchanged from §5.2.

### 6.3 Canonical identity

A Method Version's identity is the exact, immutable combination of:

1. the exact Market Measure Definition identifier and revision it binds to
   (§5.3, §6.4);
2. an explicit semantic version identifier, distinct from the Market Measure
   Definition's own revision indicator (§6.6), in the exact format §6.4
   fixes; and
3. the exact, canonically ordered list of declared dependency versions, in
   the exact ordering model §6.4 fixes (§6.5).

Two Method Version records with an identical combination of these three
elements MUST denote the exact same semantic specification. This identity
axis is independent of, and MUST NOT be conflated with, Asset Foundation's
Definition Version axis (§6.6, mirrors the register's explicit
non-conflation requirement).

### 6.4 Required fields

| Field | Meaning | Permitted values |
| --- | --- | --- |
| Bound Market Measure Definition reference | The exact Market Measure Definition identifier and revision this Method Version realizes | Exactly one; MUST exist as a specified Market Measure Definition (§5.3) |
| Semantic version identifier | This Method Version's own version, distinct from the Market Measure Definition's revision | An explicit triple of non-negative integers `MAJOR.MINOR.PATCH`, each component written with no leading zero other than a standalone `0` (e.g., `1.0.0`, `2.3.1`); no other character, separator, suffix, or format is permitted; MUST NOT reuse a given triple for a semantically different specification bound to the same Market Measure Definition identifier |
| Declared dependency versions | The exact, canonically ordered list of calculation dependencies this Method Version requires | A list of `(dependency identifier, exact dependency version)` pairs, each drawn only from explicit, governed calculation dependencies (the fourth frozen M40 input category, §4.2); no ambient or unversioned dependency; no two pairs may share the same dependency identifier; the list MUST be ordered by dependency identifier in ascending code-point order — this is the one dependency ordering model this document defines, and it applies identically to this field, this Method Version's identity (§6.3), the future admission gate (§8.2), and the future registry invariants (§9.2) |
| Declared Method Requirement set | The exact, canonically ordered list of Method Requirement records (§7) this Method Version's applicability depends on | Zero or more Method Requirement records, each individually specified per §7.4; ordered by requirement key (§7.4) in ascending code-point order, using the same ordering model as declared dependency versions |

No field MAY carry executable code, a formula body, a named indicator
implementation, ambient time, randomness, or mutable process state — the
forbidden-inputs closure Stage 1 already fixed
([register §6.2](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md#62-method-version)).

### 6.5 Relationship to Deterministic Calculation

Every Method Version MUST satisfy the already-admitted Deterministic
Calculation property (§4.2): identical canonical inputs, explicit
parameters, this Method Version's own semantic version, and its declared
dependency versions MUST produce a byte-identical canonical Market Measure
Result. This contract does not restate Deterministic Calculation's meaning;
it cites it as the property every Method Version's declared dependency
versions field exists to make checkable.

### 6.6 Non-conflation invariant

A Method Version's semantic version identifier and an Asset's Definition
Version are two independent version axes governing two different subjects —
a calculation specification and an Asset definition, respectively. A future
consumer MUST reference each by its own exact identifier and MUST NOT
compare, merge, or substitute one for the other. No field in this contract
derives a Method Version's semantic version from, or binds it to, an Asset
Definition Version's own numbering.

### 6.7 Immutability invariants

- Once specified, a Method Version's bound Market Measure Definition
  reference, semantic version identifier, and declared dependency versions
  MUST NOT change. A
  change to any of these three fields is a new Method Version, never an
  edit.
- The declared Method Requirement set MAY only be specified at the same time
  as the Method Version itself; it MUST NOT be appended or amended after
  specification without producing a new Method Version.
- Specifying a Method Version is not a production-method admission (§8.4);
  it is the version-controlled unit a future, separately chartered
  admission mechanism evaluates (§8).

### 6.8 Prohibited interpretations

A Method Version MUST NOT be interpreted, presented, or consumed as:

- a second, competing versioning scheme against Asset Foundation's
  Definition Version (§6.6);
- a production-method admission or an entry in a non-empty production
  catalog (§8.4);
- a correctness, trust, reliability, or recommendation claim; or
- a Ledger, Portfolio, or Wealth Intelligence subject, input, or output
  (Stage 1 five-part gate, re-verified at §11.2).

### 6.9 Worked example (illustrative only — no production admission)

```
Bound Market Measure Definition reference: "market-measure-definition:example-price-level"
                                            revision 1
Semantic version identifier:               1.0.0
Declared dependency versions:              [ ]  (empty list; none required
                                            for this illustrative
                                            identity-question example — an
                                            empty list is trivially in
                                            ascending code-point order)
Declared Method Requirement set:           [ "example-price-level:mr-01" ]
                                            (§7.8 worked example)
```

Non-admitted; illustrates only that the required-fields table (§6.4) is
sufficient to instantiate a record without an implicit default.

## 7. Applicability Contract (Method Requirement)

### 7.1 Applicability as a contract type

The M41 architecture proposal names "Applicability" as one of three
contracts M41-WP1 must specify (§4, §6, WP1 title). Stage 1 established that
Applicability is not itself a separate governed noun: it is the contract
*type* the confirmed noun Method Requirement instantiates
([register §6.0](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md#60-complete-noun-inventory)).
This section is therefore the Applicability contract in full: it specifies
Method Requirement, and no separate "Applicability" record type exists
alongside it.

### 7.2 Exact meaning (inherited, unmodified)

A Method Requirement is an explicit, declared prerequisite condition
specified at Method Version definition time that must hold for that Method
Version to be applicable to a given Measure Subject and Observation Input
Manifest. It is evaluated deterministically against the declared condition
and produces no correctness, quality, or judgment meaning
([register §6.3](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md#63-method-requirement)).

### 7.3 Owner

Market Intelligence. Non-owners unchanged from §5.2.

### 7.4 Canonical identity and required fields

A Method Requirement's identity is a stable requirement key, unique within
the one Method Version that declares it (§6.4). It MUST declare:

| Field | Meaning | Permitted values |
| --- | --- | --- |
| Requirement key | Stable identity within its declaring Method Version | Explicit, platform-assigned; immutable once specified |
| Declaring Method Version reference | Which Method Version this requirement constrains | Exactly one (§6.4) |
| Prerequisite category | What kind of condition this requirement states | One of: subject shape; dependency presence; Observation category availability (the closed set register §6.3 names; no other category is admitted by this document) |
| Evaluation rule | The exact, deterministic condition that must hold | An explicit predicate, serialized in exactly the closed grammar §7.4a fixes, built only from operands (a)–(c) below and no other reference, value, or vocabulary: (a) `SubjectShape`, referencing the declaring Method Version's own bound Market Measure Definition's declared subject shape (§5.4), permitted only if the Prerequisite category is subject shape; (b) `Dependency(<dependency identifier>)`, referencing an identifier present in the declaring Method Version's own declared dependency versions (§6.4), permitted only if the Prerequisite category is dependency presence; (c) `ObservationEvidenceCount`, the count of M39 Observation evidence records in the invocation's Observation Input Manifest (frozen M40 category, §4.2), permitted only if the Prerequisite category is Observation category availability |

No field MAY carry an implicit default, heuristic, or best-effort
substitution — the forbidden-inputs closure Stage 1 already fixed
([register §6.3](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md#63-method-requirement)).
Because the evaluation rule field's permitted operands are restricted to
(a)–(c) above — each already a permitted-input category under the frozen
M40 four-category closure (§4.2) or a field this Market Measure
Definition/Method Version pair already declares — no evaluation rule can
reference a Ledger, Portfolio, Wealth Intelligence, judgment, evaluation,
reputation, confidence, or suitability value: no such value is a
constructible operand under §7.4a's grammar. This makes the exclusion
structural, not merely a prohibited-interpretation statement (§7.7).

### 7.4a Evaluation rule closed grammar and canonical form

The evaluation rule field (§7.4) MUST be an ASCII string conforming exactly
to the following grammar (ordinary, non-governed syntax notation, per
§4.3 — this grammar coins no candidate noun):

```
<predicate>   ::= <atom> | "(" "AND" " " <predicate> " " <predicate> ")"
                 | "(" "OR" " " <predicate> " " <predicate> ")"
                 | "(" "NOT" " " <predicate> ")"
<atom>        ::= "(" "EXISTS" " " <operand> ")"
                 | "(" <comparator> " " <operand> " " <operand> ")"
<comparator>  ::= "=" | "!=" | ">" | "<" | ">=" | "<="
<operand>     ::= "SubjectShape" | "Dependency(" <dependency-identifier> ")"
                 | "ObservationEvidenceCount" | <integer-literal>
```

`<dependency-identifier>` MUST be an identifier already present in the
declaring Method Version's declared dependency versions (§6.4).
`<integer-literal>` MUST be a non-negative integer with no leading zero
other than a standalone `0`. `SubjectShape` and `Dependency(...)` operands
are permitted only for the corresponding Prerequisite category, per §7.4's
table; `ObservationEvidenceCount` is an operand yielding a non-negative
integer and is permitted only for the Observation category availability
Prerequisite category.

**Canonical form.** A conforming evaluation rule string MUST use exactly one
space as every token separator shown above, MUST contain no other
whitespace, comment, or formatting variance, and MUST use no token, operand,
comparator, or connective outside this grammar. Two evaluation rule values
denoting the same semantic condition MUST be byte-identical under this
canonical form; a future admission gate or independent review MAY therefore
decide grammar conformance, and MAY decide byte-identity between two
evaluation rules, from the field's concrete value alone, without evaluating
its truth against any actual invocation. This is the "mechanically
checkable from its concrete value" property Required Correction
`M41-WP1-S2-IR-2` requires.

Every atom's boolean evaluation result and every predicate's overall
evaluation result is exactly one of `TRUE` or `FALSE`, mapped directly to
this Method Requirement's `MET`/`UNMET` result (§7.5): `TRUE` yields `MET`;
`FALSE` yields `UNMET`. No third value is constructible under this grammar,
which is what makes §7.5's binary result and fail-closed unmet consequence
mechanically guaranteed by the field's own closed form, not merely asserted
by prose.

### 7.4b Operand value domains and expression semantics

§7.4a fixes the evaluation rule field's grammar and canonical form; this
subsection closes its evaluation semantics — the exact value each operand
denotes and the exact result of every `EXISTS` and comparator atom — without
adding, removing, or renaming any grammar production in §7.4a. It coins no
candidate noun; every domain and result below is stated using only §7.4's
already-permitted operand meanings, §5.4, §6.4, and §8.2 predicate 8's
already-fixed concepts, or ordinary integer/boolean semantics.

**Operand value domains.** Each operand has exactly one value domain, fixed
for every invocation the evaluation rule is checked against:

- `SubjectShape` — an enumerated domain of exactly the three closed shape
  names §5.4 already fixes: (a) a single canonical Asset identity reference;
  (b) an ordered, canonical reference set of two or more Asset identities;
  (c) an explicit market-context parameter set with no Asset identity
  reference. Its value for a given invocation is the one shape the
  invocation's actual Measure Subject instantiates.
- `Dependency(<dependency-identifier>)` — a presence domain, not a numeric or
  enumerated domain: for a given invocation, this operand is either resolved
  (the named dependency identifier's exact governed dependency version
  already declared for it in the declaring Method Version's declared
  dependency versions, §6.4, is available for that invocation, per §8.2
  predicate 8) or not resolved. It carries no comparable value beyond that
  resolved/not-resolved state.
- `ObservationEvidenceCount` — the non-negative-integer domain: its value is
  the exact count of M39 Observation evidence records in the invocation's
  Observation Input Manifest (§7.4), always defined, never absent.
- `<integer-literal>` — the non-negative-integer domain: its value is
  exactly the integer the literal's own text denotes (§7.4a), fixed by the
  evaluation rule string itself and always defined.

**`EXISTS` semantics.** `(EXISTS <operand>)` evaluates to `TRUE` or `FALSE`
as follows, with no other case possible:

- `(EXISTS SubjectShape)` is `TRUE` iff the invocation's actual Measure
  Subject instantiates a shape that is a member of the declaring Method
  Version's bound Market Measure Definition's declared subject shape subset
  (§5.4); `FALSE` otherwise.
- `(EXISTS Dependency(<dependency-identifier>))` is `TRUE` iff that
  dependency identifier's operand is resolved for the invocation, as defined
  above; `FALSE` otherwise.
- `(EXISTS ObservationEvidenceCount)` is always `TRUE`, because this
  operand's value is always defined (§7.4), including when the count is
  `0`.
- `(EXISTS <integer-literal>)` is always `TRUE`, for the same reason: an
  integer literal's value is always defined.

**Comparator well-formedness and semantics.** A comparator atom
`(<comparator> <operand-1> <operand-2>)` is well-formed only if both
operands are drawn from the non-negative-integer domain — that is, each of
`<operand-1>` and `<operand-2>` is `ObservationEvidenceCount` or an
`<integer-literal>`, in any combination. `SubjectShape` and
`Dependency(...)` operands each have a domain this document defines no
ordering or equality relation over (enumerated and presence-typed,
respectively, not integer-valued); a comparator atom naming either as an
operand is grammar-conformant under §7.4a but is not well-formed, and is
therefore not a legal evaluation rule: predicate 4 (§8.2) rejects it at
admission, on the same "checkable from the field's concrete string value
alone" basis as grammar conformance and canonical form, exactly as it
rejects an ungrammatical string. This is the defined result of every
type-incompatible expression this grammar's syntax otherwise admits — a
fixed rejection at admission, never a runtime evaluation. A well-formed
comparator atom evaluates using ordinary integer comparison
(`=`, `!=`, `>`, `<`, `>=`, `<=`) between its two operands' integer values as
fixed above, yielding exactly `TRUE` or `FALSE`.

**Connective semantics.** `AND`, `OR`, and `NOT` apply ordinary boolean
semantics to their sub-predicates' already-determined `TRUE`/`FALSE`
results: `AND` is `TRUE` iff both sub-predicates are `TRUE`; `OR` is `TRUE`
iff at least one sub-predicate is `TRUE`; `NOT` is `TRUE` iff its
sub-predicate is `FALSE`.

Because every operand's value domain, every `EXISTS` result, every
comparator's well-formedness and result, and every connective's result are
fixed above from concepts this document already defines (§5.4, §6.4, §7.4,
§8.2 predicate 8) or from ordinary integer/boolean semantics, every
grammar-conformant evaluation rule string either (i) is well-formed and
evaluates, for any given concrete invocation state, to exactly one of
`TRUE` or `FALSE` with no third value or invented case, or (ii) is not
well-formed and is rejected at admission with no evaluation ever attempted.
No grammar-conformant string is left with an undefined or
implementation-invented result. This closes the "mechanically checkable
from its concrete value" requirement `M41-WP1-S2-IR-2` first raised to cover
evaluation, not merely parsing.

### 7.5 Evaluation invariants

- Every Method Requirement MUST be declared at Method Version specification
  time (§6.7); it MUST NOT be inferred, added, or altered at invocation
  time.
- Evaluation of a Method Requirement against a given Measure Subject and
  Observation Input Manifest MUST be deterministic: identical subject and
  manifest inputs MUST always yield the same met/unmet result.
- An unmet Method Requirement MUST prevent its declaring Method Version from
  being applicable to that invocation. It MUST NOT trigger a fallback,
  substitution, or partial-applicability outcome.
- A Method Requirement's evaluation result is exactly one of `MET` or
  `UNMET`; no third value, confidence score, or partial-satisfaction value
  is admitted by this contract.

### 7.6 Orthogonality to Input Sufficiency

A Method Requirement (specification-time, "what a Method Version needs in
principle") is orthogonal to the already-admitted Input Sufficiency (§4.2;
invocation-time, "whether one exact invocation's supplied inputs satisfy
it"). This contract's evaluation rule field (§7.4) states the *general*
condition; Input Sufficiency's frozen meaning governs whether one exact
invocation's supplied canonical inputs satisfy the declared prerequisites.
Neither this contract nor Input Sufficiency substitutes for, amends, or
reinterprets the other.

### 7.7 Prohibited interpretations

A Method Requirement MUST NOT be interpreted, presented, or consumed as:

- a substitute for, or redefinition of, Input Sufficiency (§7.6);
- an Asset capability grant (§5.7);
- correctness, reliability, reputation, confidence, or evaluator judgment;
- a portfolio suitability or user preference constraint; or
- a Ledger, Portfolio, or Wealth Intelligence subject, input, or output
  (Stage 1 five-part gate, re-verified at §11.3).

### 7.8 Worked example (illustrative only — no production admission)

```
Requirement key:                  "example-price-level:mr-01"
Declaring Method Version:         bound Market Measure Definition
                                   "market-measure-definition:example-price-level"
                                   rev 1, semantic version 1.0.0
Prerequisite category:            Observation category availability
Evaluation rule:                  (>= ObservationEvidenceCount 1)
```

`(>= ObservationEvidenceCount 1)` conforms exactly to §7.4a's grammar and
canonical form: it is a single atom comparing the `ObservationEvidenceCount`
operand (permitted only for the Observation category availability
Prerequisite category) against the integer literal `1`, with no other
token. Its evaluation yields `TRUE` (hence `MET`) whenever the invocation's
Observation Input Manifest contains at least one M39 Observation evidence
record, and `FALSE` (hence `UNMET`) otherwise.

Non-admitted; illustrates that a declared prerequisite category and a
grammar-conformant evaluation rule are sufficient to instantiate a record
without an implicit default, and shows the orthogonality of §7.6: this
requirement states what must exist in principle, not whether one exact
manifest satisfies it.

## 8. Future Method-Admission Gate — Specification, Not Exercise

### 8.1 Purpose

The M41 architecture proposal §6 requires M41-WP1 to specify "the
specification of a future method-admission gate," distinct from exercising
it. This section describes the mechanically testable structure a future,
separately chartered admission mechanism would apply to a candidate Market
Measure Definition or Method Version before adding it to a production
catalog. It creates no such mechanism and admits no candidate.

### 8.2 Gate predicate structure

A future admission gate evaluating a candidate Market Measure Definition or
Method Version MUST check exactly the following closed, exhaustive set of
structural predicates — no fewer, and a future chartering milestone MAY NOT
substitute a smaller or open-ended set for it — each derived from an
invariant already fixed by §5–§7 of this document:

1. **Field completeness** — every required field in §5.4 (Market Measure
   Definition) or §6.4 (Method Version) is present and non-implicit.
2. **Identity uniqueness** — the candidate's canonical identity (§5.3 or
   §6.3) does not collide with any already-admitted record's identity of the
   same record type, unconditionally — including a collision where the
   colliding records' field content is otherwise identical. No two admitted
   records of the same type may ever share a canonical identity; an
   identical-content duplicate is inadmissible for the same reason a
   conflicting duplicate is (§9.2 predicate 6).
3. **Binding integrity** — a candidate Method Version's bound Market Measure
   Definition reference (§6.4) resolves to exactly one already-admitted
   Market Measure Definition at an exact revision (§5.5).
4. **Requirement well-formedness** — every Method Requirement in a candidate
   Method Version's declared set (§6.4) independently satisfies §7.4's
   required-fields closure, including grammar conformance and canonical
   form of the evaluation rule field under §7.4a and operand-domain
   well-formedness under §7.4b (no comparator atom names `SubjectShape` or
   `Dependency(...)` as an operand) — checkable from the field's concrete
   string value alone, with no reference to any actual invocation.
5. **Ownership-boundary gate** — the candidate passes the frozen M40
   five-part ownership-boundary gate (permitted subject, permitted inputs,
   output meaning, prohibited Ledger/Portfolio/Wealth inputs, prohibited
   judgment semantics), re-applied to the candidate's own concrete field
   values, not merely its abstract Stage 1 disposition (§11).
6. **Non-conflation check** — for a Method Version, the semantic version
   identifier is not derived from or equated with an Asset Definition
   Version (§6.6), and its format matches §6.4's fixed
   `MAJOR.MINOR.PATCH` representation exactly.
7. **Witnessed-versus-computed compliance** — the candidate does not, and
   cannot by its concrete field values, recast a source-reported,
   M39-Observation-carried claim as a platform calculation, or vice versa
   (§5.5's witnessed-versus-computed invariant); every Method Version
   candidate's realized output is confirmed to carry Event Type
   `Calculation` and Producing Domain `Market Intelligence`.
8. **Dependency resolution and uniqueness** — every `(dependency
   identifier, exact dependency version)` pair in a candidate Method
   Version's declared dependency versions (§6.4) resolves to exactly one
   exact, already-governed dependency version; no dependency identifier
   appears more than once in the declared list; the list is in the exact
   canonical order §6.4 fixes.
9. **Cross-contract compatibility** — a candidate Method Version's declared
   dependency versions and declared Method Requirement set are each
   compatible with its bound Market Measure Definition's declared subject
   shape, declared output coordinate meaning, and permitted input-category
   declaration (§5.4): no Method Version dependency, requirement, or
   prerequisite category may draw on an input category or subject shape its
   bound Market Measure Definition does not itself permit or declare.
10. **Deterministic Calculation compliance** — the candidate satisfies the
    already-admitted Deterministic Calculation property (§6.5): identical
    canonical inputs, explicit parameters, semantic version, and dependency
    versions are checkable, by the candidate's own declared fields, as
    sufficient to determine a byte-identical canonical result.
11. **Revision compliance** — if the candidate is a Market Measure
    Definition sharing a Market Measure Definition identifier with an
    already-admitted record at a lower revision indicator, the candidate's
    fields differ from that already-admitted record only by an additive or
    narrowing amendment; in particular, the candidate MUST NOT change the
    bound umbrella concept, the required output coordinate meaning, remove a
    permitted-input category, or add, remove, or otherwise change the
    declared subject shape subset relative to that already-admitted record
    (§5.6). A candidate failing this comparison is inadmissible as a
    revision of that identifier; it MAY still be admissible under a new
    Market Measure Definition identifier.
12. **Requirement evaluation invariant compliance** — every Method
    Requirement in a candidate Method Version's declared set, in addition to
    passing predicate 4's grammar conformance and well-formedness (§7.4b), is
    confirmed against every applicable invariant §7.5 fixes:
    (a) under §7.4a's grammar and §7.4b's operand value domains and
    expression semantics, it evaluates, for any given concrete invocation
    state, to exactly one of `TRUE` or `FALSE`, with no third value
    constructible;
    (b) that `TRUE`/`FALSE` result maps to exactly one of `MET`/`UNMET`, with
    no confidence score or partial-satisfaction value admitted;
    (c) an `UNMET` result for any one Method Requirement in the candidate's
    declared set renders the candidate Method Version inapplicable to that
    invocation in its entirety, and the candidate's fields and declared set
    contain no fallback rule, no substitute Method Version or calculation
    path, and no partial-applicability outcome that would apply instead of
    that consequence; and
    (d) the candidate's declared Method Requirement set is fixed at Method
    Version specification time (§6.7) and contains no field, reference, or
    mechanism by which a requirement could be inferred, added, altered,
    weakened, or bypassed at invocation time.

A candidate that fails any predicate is inadmissible regardless of how
complete its other fields are, mirroring the Stage 1 register's own
fail-closed gate discipline.

### 8.2a Framework admission is not production-method admission

A future gate returning `ADMITTED` for a candidate Market Measure Definition
or Method Version under §8.2 admits only that framework specification
record. It does NOT, by itself or in combination with any other admission
under this gate, admit a Formula, named indicator, reference calculation,
Method, or any other production calculation. Admitting a concrete Formula,
named indicator, reference calculation, or Method requires separate,
additional, future authority this document does not specify, describe, or
authorize (§8.4, §13).

### 8.3 Admission is binary and non-partial

The future gate, once chartered, MUST return exactly one of `ADMITTED` or
`REJECTED` for a candidate as a whole. No predicate failure is admissible as
a partial or provisional admission. This mirrors §7.5's requirement-level
`MET`/`UNMET` binary and the Stage 1 register's own `ADMIT`/`REUSE`/
`RENAME`/`REJECT` closed disposition set.

### 8.4 Non-exercise statement

This section specifies gate structure only. No production Market Measure
Definition, Method Version, or Method Requirement is admitted by this
document, this gate description, or the worked examples in §5.8, §6.9, and
§7.8. The production Market Measure Definition/Method Version catalog
remains empty throughout M41
(M41 proposal §7, §12). Exercising this gate — building it, running it, or
admitting a concrete candidate through it — requires a future, separately
chartered milestone (M41 proposal §2, §7); this document's description of
its structure is never itself that authorization.

## 9. Future Registry Invariants — Specification, Not Exercise

### 9.1 Purpose

The M41 architecture proposal §6 also requires M41-WP1 to specify "registry
invariants" a future frozen library of admitted Market Measure Definitions
and Method Versions would need to satisfy. The Frozen Registry itself (the
M40 plan's
original WP7) is explicitly out of M41's scope, deferred to a future,
separately chartered milestone (M41 proposal §7). This section states
invariants only — it builds, names, or admits no registry as a governed
noun, consistent with §4.3's treatment of "registry" as ordinary
non-canonical descriptive language, not a candidate.

### 9.2 Invariants

A future registry holding admitted Market Measure Definition and Method
Version records, once separately chartered and implemented, MUST:

1. build atomically — either every admitted record is present and
   consistent, or the registry does not come into existence in a usable
   state (fail-closed, mirroring §8.3's binary admission result);
2. be immutable once built — no in-place mutation of an admitted record; a
   changed specification is a new record admitted through the gate (§8),
   never an edit to an existing one (mirrors §5.6, §6.7);
3. never resolve an identity dynamically as "latest" — every reference into
   the registry MUST name an exact Market Measure Definition
   identifier/revision or Method Version identity (§5.3, §6.3), never an
   unresolved or ambient pointer;
4. grant no provider, Asset Registry, or plugin authority — a registry
   holding Market Measure Definition and Method Version records is
   Market-Intelligence-owned specification storage only, and does not
   itself become a provider integration, an Asset admission mechanism, or a
   capability grant (§5.7, §7.7);
5. remain, upon initial construction, structurally capable of holding zero
   admitted production records — an empty registry is a valid registry
   state, consistent with the production catalog remaining empty throughout
   M41 (§8.4);
6. enforce canonical-identity uniqueness unconditionally — no two admitted
   records of the same record type (Market Measure Definition or Method
   Version) may ever share an identical canonical identity (§5.3 or §6.3),
   regardless of whether the colliding records' field content differs or is
   identical; a candidate whose canonical identity collides with an
   already-admitted record MUST be rejected by the gate (§8.2 predicate 2)
   in either case, never merged, overwritten, deduplicated, or silently
   superseded by the registry;
7. maintain full referential closure — every admitted Method Version's
   bound Market Measure Definition reference, every entry in its declared
   dependency versions, and every record in its declared Method Requirement
   set MUST resolve to a record already present in, or admitted atomically
   together with (predicate 1), the registry; no admitted record may
   reference a Market Measure Definition, dependency version, or Method
   Requirement absent from the registry; every admitted record's declared
   dependency versions list and declared Method Requirement set MUST retain,
   unchanged, the exact ascending-code-point ordering model §6.4 fixes — the
   one dependency ordering model this document defines (§6.3, §6.4, §8.2
   predicate 8); the registry MUST NOT reorder, re-sort, or otherwise store
   either list under a different ordering than the admitted record itself
   carried through the gate; and
8. exhibit deterministic content-equivalence — two registry builds from an
   identical exact set of admitted-record inputs MUST produce byte-identical
   registry content; no build order, timing, or process-specific value may
   affect the resulting registry content, mirroring the Deterministic
   Calculation property (§4.2, §6.5) applied to the registry itself.

### 9.3 Non-exercise statement

No registry is built, persisted, or operated by this document. These
invariants are prose requirements for a future milestone's implementation
authority to satisfy; their statement here creates no implementation,
runtime, persistence, or provider authority (Implementation authority:
`NONE`, header).

## 10. Cross-Contract Consistency

- Every field in the Method Version contract (§6.4) that references a
  Market Measure Definition resolves to a field the Market Measure
  Definition contract actually declares (§5.4) — no Method Version field
  assumes an undocumented Market Measure Definition property.
- Every field in the Method Requirement contract (§7.4) that references a
  Method Version resolves to a field the Method Version contract actually
  declares (§6.4) — no Method Requirement assumes an undocumented Method
  Version property.
- The three contracts' prerequisite category closure (§7.4: subject shape,
  dependency presence, Observation category availability) references only
  concepts each of the other two contracts already declares: subject shape
  is the Market Measure Definition's own declared field (§5.4); dependency
  presence references the Method Version's declared dependency versions
  (§6.4); Observation category availability references the frozen M40
  permitted M39 Observation evidence category (§4.2). No prerequisite
  category requires an undeclared field from any contract.
- No contract in this document redefines a field or invariant another
  contract in this document already states; each field is declared exactly
  once, in the contract that owns it.
- Every Method Requirement evaluation rule's permitted reference set (§7.4)
  is drawn only from fields the Market Measure Definition (§5.4) and Method
  Version (§6.4) contracts already declare, or the frozen M40 M39
  Observation evidence category (§4.2); this closure is what makes §8.2
  predicate 9's cross-contract compatibility check mechanically decidable.

## 11. Constitutional Constraints Compliance — Five-Part Gate Re-Application

Per M41 proposal §8 and this document's own §8.2 predicate 5, the frozen M40
five-part ownership-boundary gate is re-applied here to each contract's
concrete, now-closed fields (§5.4, §6.4, §7.4, §7.4a, §7.4b), not merely
restated from Stage 1's candidate-level result. This re-application reflects
the closed representations the first Required Corrections Response, the
[Final Required Corrections Response](M41_WP1_STAGE2_FINAL_REQUIRED_CORRECTIONS_RESPONSE.md),
and the
[Final2 Required Corrections Response](M41_WP1_STAGE2_FINAL2_REQUIRED_CORRECTIONS_RESPONSE.md)
fixed: the three-shape subject-shape closure, the four-question
output-coordinate citation closure, the grammar-closed, canonically formed,
and now semantically closed evaluation-rule representation (§7.4a, §7.4b),
and the witnessed-versus-computed invariant (§5.5).

### 11.1 Market Measure Definition

| Part | Result | Reasoning |
| --- | --- | --- |
| Permitted subject | Pass | §5.4's declared subject shape field is restricted to a non-empty subset of exactly the three closed Measure Subject shapes register §6.4 names; no field names a Ledger, Portfolio, or Wealth subject |
| Permitted inputs | Pass | §5.4's permitted input-category declaration field is a non-empty subset of exactly the frozen M40 four-category closure; no other field admits an input |
| Output meaning | Pass | §5.4's required output coordinate meaning field is restricted to citing exactly one of the four already-admitted Valuation Semantics questions by exact name; no free-form or "equivalent" statement is permitted, and no field asserts correctness or recommendation |
| Prohibited Ledger/Portfolio/Wealth inputs | Pass | No field in §5.4 accepts a Ledger, Portfolio, or Wealth Intelligence value; §5.7 states this explicitly |
| Prohibited judgment semantics | Pass | No field in §5.4 accepts a forecast, recommendation, signal, consensus, action intent, evaluator verdict, trust score, correctness confidence, or quality ranking; §5.7 states this explicitly |

The five-part gate above is unchanged in structure. A separate, sixth check
— not a sixth gate part, but the witnessed-versus-computed boundary §5.5
adds — also passes: §5.5's invariant forecloses any Bound umbrella concept
value from recasting a Method Version's realized output as a source-reported
claim, or vice versa, regardless of which of the two admitted umbrella terms
that field names.

### 11.2 Method Version

| Part | Result | Reasoning |
| --- | --- | --- |
| Permitted subject | Pass | §6.4's fields reference only a Market Measure Definition binding, a version identifier, dependency versions, and a Method Requirement set — no Ledger, Portfolio, or Wealth subject |
| Permitted inputs | Pass | §6.4's declared dependency versions field is restricted to explicit, governed calculation dependencies (the fourth frozen M40 category), in a closed `(identifier, version)` pair format with a fixed ordering rule; no field admits an ungoverned input |
| Output meaning | Pass | §6.4's fields are limited to identity, versioning, and dependency/requirement declaration; no field asserts correctness or recommendation |
| Prohibited Ledger/Portfolio/Wealth inputs | Pass | No field in §6.4 accepts a Ledger, Portfolio, or Wealth Intelligence value; §6.8 states this explicitly |
| Prohibited judgment semantics | Pass | No field in §6.4 accepts judgment, trust, or quality meaning; §6.8 states this explicitly |

Witnessed-versus-computed boundary (supplementary, not a sixth gate part):
Pass — every Method Version is, by §6.1 and §6.5, inherently computational;
§5.5 confirms its realized output always carries Event Type `Calculation`
and Producing Domain `Market Intelligence`.

### 11.3 Method Requirement

| Part | Result | Reasoning |
| --- | --- | --- |
| Permitted subject | Pass | §7.4's fields reference only a declaring Method Version, a prerequisite category, and an evaluation rule — no Ledger, Portfolio, or Wealth subject |
| Permitted inputs | Pass | §7.4's prerequisite category field is restricted to the closed set (subject shape, dependency presence, Observation category availability), each tracing to the frozen four-category closure via §10; the evaluation rule field is restricted to the closed grammar §7.4a fixes, whose only constructible operands are `SubjectShape`, `Dependency(...)`, and `ObservationEvidenceCount` — no other reference is a syntactically valid operand |
| Output meaning | Pass | §7.5 restricts evaluation results to `MET`/`UNMET`; §7.4a's grammar together with §7.4b's operand value domains and expression semantics independently guarantees every well-formed predicate evaluates to exactly `TRUE`/`FALSE`, mapped one-to-one to `MET`/`UNMET`, with no third value constructible, and that a not-well-formed atom is rejected at admission rather than evaluated; no field asserts correctness, quality, or judgment meaning |
| Prohibited Ledger/Portfolio/Wealth inputs | Pass | No field in §7.4 accepts a Ledger, Portfolio, or Wealth Intelligence value — structurally, because §7.4a's grammar admits no operand token for any such value, not merely by the §7.7 prohibited-interpretation statement |
| Prohibited judgment semantics | Pass | §7.4a's grammar restricts the evaluation rule field to existence and comparison atoms combined by `AND`/`OR`/`NOT` over three closed operand kinds only, which excludes correctness, reliability, reputation, confidence, evaluator judgment, portfolio suitability, and user preference by construction — no such concept has a representable operand token; §7.7 restates this |

All three contracts pass the re-applied gate in full. No field introduced
by this document weakens, narrows, or contradicts the candidate-level gate
result Stage 1 already recorded
([register §6.1–§6.3](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md#61-market-measure-definition)).

## 12. Relationship to M41-WP2–WP4

This document explicitly does not specify:

- Measure Subject's own identity, binding, and canonical ordering rule —
  i.e., how an actual Measure Subject record is constructed, serialized, and
  ordered for the shape (b) reference set (deferred to M41-WP2, per register
  §6.4's own future contract acceptance evidence obligation). This is
  distinct from, and narrower than, §5.4's declared subject shape field:
  §5.4 closes which of the three already-named Stage 1 shapes a Market
  Measure Definition requires, by citation only; it does not define, and
  this document does not otherwise define, Measure Subject's own record
  structure, identity, or binding rule — that remains exclusively M41-WP2's
  obligation;
- Observation Input Manifest's binding to this contract's declared
  input-category fields beyond citing the existing frozen M40 term (M41-WP2);
- Measurement Window's cutoff, timezone, and calendar resolution rule
  (M41-WP3);
- Measure Value's canonical serialization rule (M41-WP4); or
- the Market Measure Result's complete composition, the deterministic
  outcome/degraded-state interaction matrix, or the Provenance model's
  narrower lineage structure, if any is later proposed (M41-WP4).

A future M41-WP2, M41-WP3, or M41-WP4 contract text MUST cite this
document's Market Measure Definition, Method Version, and Method Requirement
fields by reference where it needs them, and MUST NOT redefine any field
this document already specifies.

## 13. Authority Non-Leakage

This document:

- creates no formula, indicator, or production-method authority;
- admits no candidate term — the three terms it specifies contract text for
  were already independently confirmed by Stage 1, and this document adds
  no new noun (§4);
- creates no implementation, runtime, provider, persistence, API, or
  public-exposure authority;
- creates no portfolio, judgment, evaluation, recommendation, execution,
  transaction, authorization, or approval authority;
- does not amend `GLOSSARY.md`, the Decision Log, the frozen M39/M40 corpus,
  the M41 architecture, or the Stage 1 register; and
- does not exercise the method-admission gate or build the registry it
  describes (§8, §9) — both remain specification-only descriptions pending
  future, separately chartered milestone authority; and
- does not, through §8.2's closed predicate set or §8.2a's non-implication
  statement, admit any Formula, named indicator, reference calculation, or
  Method — framework-record admission and production-method admission
  remain two distinct, unbridged authorities.

No statement in this document SHALL be used as authority to create a file
outside documentation, to alter `GLOSSARY.md`, or to alter runtime behavior.

## 14. Validation Performed

- **Markdown structure:** Heading hierarchy is sequential (H1, then H2
  `## 1.` through `## 15.`, with H3/H3a nested only under the section they
  belong to, including `### 8.2a`, the first final-round addition
  `### 7.4a`, and the final2-round addition `### 7.4b`), with no skipped or
  duplicated levels.
- **Vocabulary provenance:** Every noun used in §5–§9, including the
  corrections added by this revision, was checked against §4's provenance
  table; no term outside the three confirmed `ADMIT` candidates, the reused
  `GLOSSARY.md` entries (including the closed Valuation Semantics question
  set and the Event Type / Producing Domain terms now cited operatively in
  §5.5), or ordinary non-canonical contract language appears.
- **No Stage 1 reopening:** §5.1, §6.1, and §7.2's exact meanings were
  checked verbatim against the Stage 1 register's own proposed exact
  definition fields and are unmodified restatements, not reinterpretations;
  the closed subject-shape vocabulary added to §5.4 was checked verbatim
  against register §6.4's own three-shape closure and is a citation, not a
  redefinition of Measure Subject.
- **Terminology consistency:** Every governed use of "Definition" was
  checked; bare shorthand for Market Measure Definition was replaced with
  the full canonical name throughout, except where the text names the
  distinct existing Asset Foundation terms Asset Definition or Definition
  Version, which are left unmodified.
- **Semantic and constitutional consistency:** §5.5's witnessed-versus-
  computed invariant, §7.4's structurally closed evaluation-rule
  representation, and §11's revalidated five-part gate results were checked
  against each other for consistency; no contract text asserts a Method
  Version output can carry Event Type `Observation`.
- **Ownership consistency:** §5.2, §6.2, §7.3 (Market Intelligence) and the
  non-owner lists were checked against Stage 1's recorded ownership; no
  correction changed ownership of any candidate.
- **Contract completeness:** §5.4, §6.4, and §7.4 were checked against
  register §6.1–§6.3's "future contract acceptance evidence" obligations;
  the exact subject-shape vocabulary, exact output-coordinate vocabulary,
  exact semantic-version format, and exact dependency-declaration format are
  now all closed, non-open-ended representations.
- **Identity consistency:** §5.6 was checked to confirm every Market Measure
  Definition field categorized in §5.4 (including declared subject shape)
  has an explicit identity-consequence rule on change; §6.3, §6.4, §8.2, and
  §9.2 were checked to confirm they use the same single dependency-ordering
  model (ascending code-point order by dependency identifier) with no
  remaining "set" versus "ordered set" inconsistency.
- **Repository consistency:** Every `GLOSSARY.md` cross-reference in §4.2
  and throughout §5–§9 was checked against the current `GLOSSARY.md` content
  and matches the exact current entry text, including the Valuation
  Semantics closed question set and the Event Type / Producing Domain
  entries newly cited operatively.
- **Internal cross references:** All relative links to
  `M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md`,
  `M41_WP1_INDEPENDENT_REVIEW.md`,
  `M41_WP1_REQUIRED_CORRECTIONS_RESPONSE.md`,
  `M41_WP1_INDEPENDENT_CONFIRMATION.md`, `M41_ARCHITECTURE_PROPOSAL.md`, and
  `M41_ARCHITECTURE_INDEPENDENT_CONFIRMATION.md` resolve to files that exist
  on disk; the §6.9 worked example's cross-reference to §7's worked example
  was corrected from the incorrect `§7.6` to the actual `§7.8`.
- **Five-part gate re-application completeness:** §11 re-applies all five
  gate parts to each of the three contracts' concrete, now-closed fields,
  independent of Stage 1's candidate-level result, per §8.2 predicate 5; the
  witnessed-versus-computed boundary is tracked as a separate, supplementary
  check, not as a sixth gate part, so the frozen gate's five-part structure
  is unchanged.
- **Future gate completeness:** §8.2 was checked to confirm its predicate
  list is now closed and exhaustive (ten predicates, "at minimum" language
  removed) and covers every invariant in §5.5–5.7, §6.5–6.8, and §7.5–7.7,
  dependency resolution and uniqueness, cross-contract compatibility, the
  witnessed-versus-computed boundary, and Deterministic Calculation
  compliance; §8.2a was checked to confirm framework admission is explicitly
  stated as insufficient to admit a Formula, Method, named indicator, or
  reference calculation.
- **Registry invariant completeness:** §9.2 was checked to confirm it now
  includes canonical-identity uniqueness, referential closure, and
  deterministic content-equivalence alongside the four invariants already
  present.
- **No production admission:** §5.8, §6.9, and §7.8 worked examples were
  checked to confirm each is explicitly labeled non-admitted and names no
  formula, provider, or production method.
- **No registry or gate exercise:** §8 and §9 were checked to confirm each
  states structure and invariants only, with an explicit non-exercise
  statement, and creates no implementation or runtime artifact.
- **Subject-shape internal consistency (final round):** §5.4 and §12 were
  checked against each other; §12 no longer describes any subject-shape
  vocabulary as deferred to M41-WP2 — it defers only Measure Subject's own
  record structure, identity, and binding rule, which §5.4 never supplied
  and does not now supply; the specification contains exactly one position.
- **Evaluation-rule mechanical decidability (final round):** §7.4a's grammar
  and canonical form were checked to confirm every legal evaluation rule
  string is parseable, and every parse's grammar-conformance and
  byte-identity-to-canonical-form questions are decidable, from the field's
  concrete value alone, without reference to any actual invocation; the
  §7.8 worked example was checked to conform exactly to this grammar.
- **Final-round dependency ordering consistency:** §9.2 predicate 7 was
  checked to confirm it now explicitly requires every admitted record's
  dependency versions list and Method Requirement set to retain the exact
  §6.4 ascending-code-point ordering, cross-referencing §6.3, §6.4, and §8.2
  predicate 8 — the one ordering model this document defines is now applied
  at every point a dependency or requirement list appears, including the
  registry.
- **Final-round gate and registry exhaustiveness:** §8.2 was checked to
  confirm it now includes explicit predicates (11, 12) enforcing §5.6's
  revision invariants and §7.5's evaluation invariants, and that predicate 2
  and §9.2 predicate 6 now state canonical-identity uniqueness
  unconditionally, rejecting a colliding candidate regardless of whether its
  content matches or conflicts with the already-admitted record; §8.2a was
  re-checked and is unchanged, so the framework/production-admission
  separation is preserved.
- **Evaluation-semantics completeness (final2 round):** §7.4b was checked to
  confirm every operand (`SubjectShape`, `Dependency(...)`,
  `ObservationEvidenceCount`, `<integer-literal>`) has exactly one stated
  value domain, every `EXISTS` atom and every well-formed comparator atom
  has a stated `TRUE`/`FALSE` result rule, and every comparator atom naming
  `SubjectShape` or `Dependency(...)` is stated as not well-formed and
  rejected at admission (predicate 4) rather than left with an undefined
  runtime result; no grammar-conformant evaluation rule string is left
  without a defined outcome, and no grammar production, operand, or
  connective in §7.4a was added, removed, or renamed.
- **Predicate 12 completeness (final2 round):** §8.2 predicate 12 was
  checked to confirm it explicitly states, as separate sub-requirements, the
  binary `TRUE`/`FALSE` evaluation result, the binary `MET`/`UNMET` mapping,
  that an `UNMET` result renders the declaring Method Version inapplicable
  in its entirety, that fallback and substitute-calculation paths are
  prohibited, that partial-applicability outcomes are prohibited, and that
  the declared requirement set is fixed at specification time with no
  invocation-time inference, addition, alteration, or bypass — covering
  every invariant §7.5 states, with none left implicit.
- **`git diff --check`:** Run against this file once staged; see the
  Final2 Required Corrections Response document for the result.

## 15. Completion Criteria and Final Status

This document is complete for its own independent review only when:

1. it specifies contract text for exactly the three Stage-1-confirmed
   `ADMIT` candidates M41-WP1 owns (Market Measure Definition, Method
   Version, Method Requirement realizing Applicability), and no other
   candidate;
2. every field it declares traces to §4's vocabulary provenance without
   coining a new noun;
3. the frozen M40 five-part ownership-boundary gate is re-applied, at the
   field level, to all three contracts (§11);
4. the future method-admission gate and future registry invariants are
   described structurally, with an explicit statement that neither is
   exercised (§8, §9);
5. every worked example is explicitly labeled non-admitted and the
   production Market Measure Definition/Method Version catalog remains
   empty; and
6. no `GLOSSARY.md` edit, Decision Log entry, or Graphify refresh is made by
   this document, and Stage 1's register is not reopened or reinterpreted.

**Final status:**
`FINAL2_REQUIRED_CORRECTIONS_APPLIED_PENDING_INDEPENDENT_CONFIRMATION`. This
document is Implementation Author output only. Independent Review
([M41_WP1_STAGE2_INDEPENDENT_REVIEW.md](M41_WP1_STAGE2_INDEPENDENT_REVIEW.md))
returned `APPROVED WITH REQUIRED CORRECTIONS`; a first revision resolved
M41-WP1-S2-IR-1 through M41-WP1-S2-IR-4
([M41_WP1_STAGE2_REQUIRED_CORRECTIONS_RESPONSE.md](M41_WP1_STAGE2_REQUIRED_CORRECTIONS_RESPONSE.md)).
Independent Confirmation of that revision
([M41_WP1_STAGE2_INDEPENDENT_CONFIRMATION.md](M41_WP1_STAGE2_INDEPENDENT_CONFIRMATION.md))
returned `NOT CONFIRMED`, identifying four unresolved portions of those same
corrections — not new findings or architectural recommendations. A first
final revision resolved those portions
([M41_WP1_STAGE2_FINAL_REQUIRED_CORRECTIONS_RESPONSE.md](M41_WP1_STAGE2_FINAL_REQUIRED_CORRECTIONS_RESPONSE.md)).
A subsequent Independent Confirmation of that revision
([M41_WP1_STAGE2_FINAL_INDEPENDENT_CONFIRMATION.md](M41_WP1_STAGE2_FINAL_INDEPENDENT_CONFIRMATION.md))
again returned `NOT CONFIRMED`, confirming `M41-WP1-S2-IR-1` and
`M41-WP1-S2-IR-3` `RESOLVED` and identifying two still-unresolved portions
of `M41-WP1-S2-IR-2` and `M41-WP1-S2-IR-4` — again not new findings or
architectural recommendations. This revision resolves those two remaining
portions in full
([M41_WP1_STAGE2_FINAL2_REQUIRED_CORRECTIONS_RESPONSE.md](M41_WP1_STAGE2_FINAL2_REQUIRED_CORRECTIONS_RESPONSE.md)).
It does not itself begin, and expressly defers, a further Independent
Confirmation. No candidate, field, worked example, or invariant in this
document is canonical, admitted, or reliable by any downstream artifact
until Independent Confirmation completes. M41-WP2 is not begun.
