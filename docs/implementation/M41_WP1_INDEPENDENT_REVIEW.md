# M41-WP1 — Candidate Vocabulary and Ownership Register Independent Review

**Review date:** 2026-07-23

**Reviewer role:** Independent Review Board. The reviewer is not the
implementation author.

**Artifact reviewed:** [M41-WP1 — Candidate Vocabulary and Ownership
Register](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md)
(`COMPLETE_FOR_INDEPENDENT_REVIEW`, stage 1 only).

**Governing authority:**

- [M41 Architecture Proposal](M41_ARCHITECTURE_PROPOSAL.md);
- [M41 Independent Architecture Review](M41_ARCHITECTURE_INDEPENDENT_REVIEW.md);
- [M41 Required Corrections Response](M41_ARCHITECTURE_REQUIRED_CORRECTIONS_RESPONSE.md);
- [M41 Independent Confirmation](M41_ARCHITECTURE_INDEPENDENT_CONFIRMATION.md);
- [Platform Architecture](../architecture/platform_architecture.md);
- [Canonical Glossary](../GLOSSARY.md);
- [M34 Decision Register](m34/audit/registers/decision_register.md);
- the frozen M39 corpus; and
- the frozen M40 corpus, especially
  [M40-WP1](M40_WP1_Canonical_Market_Measure_Vocabulary_and_Ownership_Specification.md)
  and
  [M40-WP2](M40_WP2_Canonical_Market_Measure_Vocabulary_Admission_Review.md).

**Scope discipline:** This review evaluates only the WP1 Candidate Vocabulary
and Ownership Register against the closed architecture. It does not reopen
the M41 architecture, its architecture-review corrections, or any M29–M40
decision. It does not review or begin WP1 contract specification or WP2.

---

## Executive Summary

The register preserves the most important constitutional boundaries. It
states that drafting creates no canonical vocabulary, keeps all operational
authority at `NONE`, reuses Observation Input Manifest and Provenance rather
than re-admitting them, carries forward the rejection of Calculation Temporal
Claim, preserves the witnessed-versus-computed distinction, and excludes
production Definitions, Method Versions, formulas, methods, catalogs,
providers, persistence, APIs, and runtime behavior.

The six requested `ADMIT` dispositions are directionally compatible with the
M40 Market Measure boundary, the two `REUSE` directions are correct, and the
carried-forward `REJECT` direction is correct. No candidate requires
architectural redesign.

Stage 1 is not yet complete enough for those dispositions to advance,
however. Five bounded defects remain in the register:

1. it treats the six examples in M41 Architecture Proposal §8 as an exact,
   exhaustive set even though the proposal says “terms such as” and names
   other M41 concepts whose vocabulary status is not accounted for;
2. it defers the evidence it says is required for candidate approval to
   downstream contract text that cannot begin or rely on the candidates
   before independent confirmation;
3. it does not record a candidate-by-candidate result for the mandatory
   five-part M40 ownership-boundary gate;
4. its three `REUSE`/`REJECT` records do not contain all mandatory record
   fields, and Provenance is not assigned or traced to an exact single
   canonical owner; and
5. its overlap analysis and confirmation wording are incomplete in specific,
   mechanically correctable places.

These are Stage 1 completeness and governance defects, not architecture
defects. They can be corrected entirely within the reviewed register without
changing the milestone boundary, candidate meanings, work-package structure,
or closed architectural decisions.

## Findings

### 1. Candidate completeness

**Finding 1.1 — Required correction; high severity.**

Section 6 says the six open candidates “match exactly the set” named by M41
Architecture Proposal §8. The governing text does not say that. It says
“Terms such as” Market Measure Definition, Method Version, Measure Subject,
Method Requirement, Measurement Window, and Measure Value remain open
candidates.

The same approved proposal also names concepts including Applicability,
manifest identity, Result identity, State, canonical serialization,
equivalence/conflict disposition, adjustment semantics, and governed
calculation dependencies. The frozen M40 planning corpus additionally makes
the vocabulary risk concrete by naming Measure Invocation, Dependency
Manifest, and a narrower Measure Provenance concept as proposed,
non-canonical concepts. Some of these may be ordinary contract language,
some may be fully covered by existing canonical vocabulary, and some may be
unneeded after the approved M41 boundary reduction. The register does not
show which is true.

This is not a demand to admit additional vocabulary. It is a failure of the
architecture-required completeness proof. Every known M41 noun must be
accounted for as:

- one of the registered candidates;
- exact reuse of an existing canonical term;
- a rejected or unnecessary specialization;
- ordinary non-canonical contract language that no downstream artifact will
  use as a governed noun; or
- explicitly outside M41.

Until that inventory exists, the assertion that the register is complete
cannot be independently reproduced, and later discovery would defeat the
approved “assembled up front” boundary.

**Finding 1.2 — Pass.**

The six candidates that are present are the six expressly illustrated by the
approved architecture. No present candidate creates provider, portfolio,
ledger, judgment, evaluation, wealth, execution, persistence, API, or
runtime authority.

### 2. Ownership and ownership singularity

**Finding 2.1 — Pass for the six `ADMIT` requests and Observation Input
Manifest.**

Market Intelligence is the sole proposed semantic owner of Market Measure
Definition, Method Version, Method Requirement, Measure Subject,
Measurement Window, and Measure Value. Measure Subject correctly leaves
referenced Asset identity, definition, classification, and Definition
Version ownership with Asset Foundation. This is reference across a boundary,
not shared ownership. Observation Input Manifest correctly retains its
frozen Market Intelligence ownership.

**Finding 2.2 — Required correction; moderate severity.**

Provenance is recorded with owner “Pre-existing foundational ownership
(unchanged),” and §10 calls its sole owner “Pre-existing (frozen).” Neither
phrase identifies an exact owning domain or constituted governance owner.
The Platform Architecture reserves Provenance as load-bearing constitutional
vocabulary and assigns provenance-at-capture responsibility at a specific
boundary, but the register does not trace its ownership claim to that
authority or explain how the governing single-owner field is satisfied.

The `REUSE` direction is correct; the ownership evidence is not complete.
The correction must identify the exact existing canonical ownership rule
without creating a new owner, transferring ownership, or redefining
Provenance.

Calculation Temporal Claim correctly has no owner because it remains
rejected.

### 3. Definitions and constitutional compatibility

**Finding 3.1 — Pass with the admission-evidence reservation below.**

The proposed definitions are bounded semantic definitions rather than
implementation designs. They preserve:

- Market Intelligence ownership of calculated descriptive facts;
- Asset Foundation ownership of referenced Asset identity and Definition
  Version;
- the separation of Method Requirement from invocation-time Input
  Sufficiency;
- the separation of Measurement Window from Canonical Temporal Claim;
- the separation of Measure Value from Computation Outcome and Degraded
  State;
- the no-value-on-non-success rule; and
- the prohibition on correctness, trust, suitability, recommendation, and
  action meaning.

The definitions are compatible in direction with V1 and V3, `M34-D-0005`,
`M34-D-0010`, frozen M39 Observation meaning, and frozen M40 vocabulary.
V2 is correctly deferred until a confirmed `ADMIT` or `RENAME` disposition
is synchronized.

**Finding 3.2 — Required correction; moderate severity.**

Measure Subject is defined as Asset identities “and/or” market-context
parameters, while the same register and the governing architecture enumerate
single-Asset, multi-Asset, or market-context subject shapes. “And/or” leaves
a hybrid Asset-plus-market-context subject shape possible without saying
whether it is one of the closed permitted shapes.

The correction must make the proposed exact definition agree with the
register's own declared subject-shape closure. This is a precision correction,
not a request to choose a new architecture.

### 4. Overlap, canonical reuse, and naming collisions

**Finding 4.1 — Pass in material direction.**

The register correctly identifies the most consequential collisions:

- Method Requirement versus Input Sufficiency;
- Measurement Window versus Canonical Temporal Claim;
- Measure Value versus Market Measure Result and Computation Outcome;
- Observation Input Manifest and Provenance as full-overlap `REUSE`;
- Calculation Temporal Claim as a duplicate specialization that remains
  `REJECT`; and
- Method Version versus Asset Foundation's Definition Version axis.

The negative corpus is preserved. No generic Analysis domain, Instrument
Analysis authority, portfolio-measurement owner, judgment/strategy layer,
execution authority, Calculation Temporal Claim, or Producing Domain
specialization is reintroduced.

**Finding 4.2 — Required correction; moderate severity.**

The overlap analysis is not complete against every plausibly colliding
Glossary entry as §5 and acceptance criterion 4 require:

- Market Measure Definition discusses Definition Version but not the
  existing Asset Definition entry, despite both being declarative
  “Definition” contracts owned by different domains.
- Measure Value discusses Market Measure Result and Computation Outcome but
  not the existing Unit Semantics and Valuation Semantics entries, even
  though its proposed meaning is explicitly typed and unit-qualified and may
  represent a valuation measure.

The missing comparisons do not prove collision or require renaming. They
must be analyzed explicitly so V1/V3 compatibility is evidenced rather than
asserted.

### 5. Disposition verification

| Entry | Requested disposition | Independent finding |
| --- | --- | --- |
| Market Measure Definition | `ADMIT` | Constitutionally supportable, pending the completeness, gate, evidence, definition-precision, and overlap corrections |
| Method Version | `ADMIT` | Constitutionally supportable, pending the completeness, gate, and evidence corrections |
| Method Requirement | `ADMIT` | Constitutionally supportable, pending the completeness, gate, and evidence corrections |
| Measure Subject | `ADMIT` | Constitutionally supportable, pending the completeness, gate, evidence, and exact-definition corrections |
| Measurement Window | `ADMIT` | Constitutionally supportable, pending the completeness, gate, and evidence corrections |
| Measure Value | `ADMIT` | Constitutionally supportable, pending the completeness, gate, evidence, and overlap corrections |
| Observation Input Manifest | `REUSE` | Correct; the frozen M40 term is reused without redefinition |
| Provenance | `REUSE` | Correct in meaning; single-owner evidence and uniform-record completeness remain unresolved |
| Calculation Temporal Claim | `REJECT` | Correct; the frozen M40 rejection is preserved and not re-decided |

No `RENAME` disposition is presently required by the evidence reviewed. None
of these dispositions is final before the architecture-mandated independent
confirmation stage.

### 6. Admission evidence and the M40 ownership gate

**Finding 6.1 — Required correction; high severity.**

Each `ADMIT` entry states that future WP1–WP4 contract text must provide
additional exact vocabulary, formats, rules, worked examples, or golden
vectors “before independent review may approve” the candidate. Section 13
repeats that no `ADMIT` candidate may be approved until that future contract
text exists.

That sequencing is incompatible with the closed M41 gate. WP1's Definition,
Method Version, and Applicability contract text cannot begin or rely on these
candidate dispositions until the register is independently reviewed,
corrected if necessary, and independently confirmed. WP2–WP4 are later still.
Evidence that can exist only in those downstream contracts therefore cannot
be a prerequisite for this Stage 2 candidate disposition.

The register must distinguish:

1. evidence required now to decide whether the candidate noun and meaning
   are admissible; and
2. downstream contract acceptance evidence that will later prove the
   confirmed term was used correctly.

The present register must contain the first category. The second category
may remain as a future work-package obligation, but it cannot be stated as
missing evidence that blocks the review which must occur before that work
may begin.

**Finding 6.2 — Required correction; high severity.**

The approved architecture makes the frozen M40 five-part boundary a
mechanically testable admission gate:

1. permitted subject;
2. permitted inputs;
3. exact output meaning;
4. prohibited Ledger/Portfolio/Wealth inputs; and
5. prohibited judgment semantics.

The register supplies related prose fields, but it does not apply and record
all five pass/fail results for each open candidate. Instead, Market Measure
Definition says it must pass the gate when future contract text is specified,
and §13 defers the aggregate proof to future WP1–WP4 contract text. That is
not the candidate-level gate required at this independent review stage.

Every open candidate must receive an explicit, mechanically reviewable
five-part result now. Any future contract will have to pass the gate again
for its concrete fields, but that later proof does not replace the present
candidate-admission proof.

### 7. Uniform record completeness

**Finding 7.1 — Required correction; moderate severity.**

Section 5 says each §6 entry uses all required fields, and acceptance
criterion 2 requires every entry to contain every §5 field. Sections
6.7–6.9 do not:

- Observation Input Manifest omits Non-owner, Permitted inputs, Forbidden
  inputs, and Constitutional constraints.
- Provenance omits Non-owner, Permitted inputs, Forbidden inputs, and
  Constitutional constraints.
- Calculation Temporal Claim omits Non-owner, Permitted inputs, Forbidden
  inputs, and Constitutional constraints.

A carried-forward `REUSE` or `REJECT` may legitimately mark a field “not
applicable,” but the field must still be present with a reason if the
register claims a uniform, complete record. This correction also provides
the proper place to make the reserved-term and no-redefinition boundaries
mechanically visible.

### 8. Scope and authority

**Finding 8.1 — Pass.**

The register:

- admits no vocabulary;
- does not modify the Glossary;
- does not modify the Decision Log;
- does not refresh Graphify;
- does not create implementation, runtime, production-method, provider,
  persistence, API, or public-exposure authority;
- does not admit a production Definition, Method Version, Formula, Method,
  or catalog entry; and
- does not begin WP1 contract specification or WP2.

No scope leakage or operational authority leakage was found.

**Finding 8.2 — Required correction; moderate severity.**

The governing architecture requires independent confirmation of every
candidate disposition before downstream reliance, whether or not the Stage 2
review required corrections. Most of the register states this correctly,
including §§2.2, 11, and 12. Three passages narrow it incorrectly:

- the Document role says contract specification waits for review and, “if
  any correction is required,” confirmation;
- acceptance criterion 8 repeats “if required”; and
- the final disposition repeats the same conditional sequence.

Those passages could allow an `APPROVED` review to bypass mandatory Stage 4.
They must state that independent confirmation is always required; required
corrections are the only conditional stage.

## Required Corrections

The following corrections apply only to the WP1 register. They do not reopen
or amend the M41 architecture or its prior RC-1 through RC-5.

1. **WP1-IR-1 — Complete the candidate-coverage proof.** Replace the
   unsupported assertion that the architecture's six examples are the exact
   complete set with an exhaustive inventory of all governed nouns already
   known across M41 WP1–WP4. Account for each noun without presuming that it
   must be admitted. At minimum, resolve the vocabulary status of the named
   concepts identified in Finding 1.1.
2. **WP1-IR-2 — Supply current admission evidence and apply the five-part
   gate now.** Separate candidate-admission evidence from future contract
   acceptance evidence. For every open candidate, record a current pass/fail
   result for permitted subject, permitted inputs, output meaning,
   prohibited Ledger/Portfolio/Wealth inputs, and prohibited judgment
   semantics. Do not use forbidden downstream contract text as evidence for
   the present review.
3. **WP1-IR-3 — Complete every uniform record and resolve Provenance
   ownership evidence.** Add every §5 field to the two `REUSE` entries and
   the carried-forward `REJECT`, using reasoned “not applicable” values where
   appropriate. Trace Provenance to an exact existing canonical ownership
   rule without creating, transferring, or redefining ownership.
4. **WP1-IR-4 — Complete the overlap proof and exact subject definition.**
   Add the missing plausible Glossary comparisons identified in Finding 4.2
   and make Measure Subject's proposed exact definition unambiguous with
   respect to the register's declared subject-shape closure.
5. **WP1-IR-5 — Restore unconditional independent confirmation wording.**
   Correct the three conditional-confirmation passages identified in Finding
   8.2 so all dispositions require Stage 4 confirmation before Stage 5
   synchronization or downstream reliance.

No other architectural or implementation correction is required by this
review.

## Repository Validation

- **Authority inspection:** The reviewed register was compared directly with
  all four governing M41 architecture artifacts, Platform Architecture §§11
  and 12, the current Canonical Glossary, the cited M34 decisions, frozen M39,
  and frozen M40-WP1/WP2.
- **Candidate-set cross-check:** The six open names, two `REUSE` names, and
  carried-forward `REJECT` were reconciled against M41 Architecture Proposal
  §8 and the frozen M40 planning vocabulary.
- **Glossary cross-check:** Current entries for Asset Definition, Definition
  Version, Unit Semantics, Valuation Semantics, Provenance, Canonical
  Temporal Claim, Event Type, Producing Domain, Degraded State, Market
  Measure, Calculated Market Measure, Computation Outcome, Observation Input
  Manifest, Market Measure Result, Input Sufficiency, Deterministic
  Calculation, and Mechanical Boundary Rules were inspected directly.
- **Link validation:** Every relative Markdown link in the reviewed register
  resolves to an existing repository file.
- **Markdown validation:** The reviewed register's heading structure is
  ordered and no trailing-whitespace line was found.
- **Git validation:** Before this review document was created, both
  `git diff --check` and `git diff --cached --check` completed without a
  whitespace error. Repository status showed only the staged M41
  architecture and WP1 documentation artifacts; no production-code change
  was present.
- **Review scope:** This independent review document is the only repository
  file created by this review. The register and governing artifacts were not
  modified. The Decision Log and Graphify were not changed, and WP1 contract
  specification and WP2 were not begun.

## Final Determination

APPROVED WITH REQUIRED CORRECTIONS
