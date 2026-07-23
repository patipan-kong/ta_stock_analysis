# M41-WP1 Stage 2 — Definition / Method Version / Applicability Contract Specification Independent Review

**Date:** 2026-07-23

**Review role:** Independent Review Board

**Artifact reviewed:** [M41-WP1 Stage 2 — Definition, Method Version, and
Applicability Contract Specification](M41_WP1_DEFINITION_METHOD_VERSION_APPLICABILITY_CONTRACT_SPECIFICATION.md)

**Review scope:** Stage 2 contract specification only

**Architecture status:** Closed and frozen

**M41-WP1 Stage 1 status:** Confirmed and frozen

**Implementation authority:** `NONE`

**Runtime authority:** `NONE`

**Production method authority:** `NONE`

**Provider authority:** `NONE`

**Persistence authority:** `NONE`

**API authority:** `NONE`

**Decision Log:** Not updated

**Graphify:** Queried for read-only review context; not refreshed

---

## Executive Summary

The Stage 2 specification preserves the approved specification-only milestone
boundary, relies on the three confirmed Stage 1 terms assigned to WP1, retains
Market Intelligence as their sole owner, and does not create a registry,
runtime surface, production catalog entry, concrete method, formula, provider
integration, persistence mechanism, or implementation authority. Its future
method-admission gate and registry are expressly described rather than
exercised, and all worked records are labeled non-admitted.

The specification is not yet ready for unconditional approval. Four
substantive groups of Stage 2 defects remain:

1. Stage 1's mandatory future-contract evidence is not fully supplied. The
   Definition contract defers rather than closes the exact subject-shape
   vocabulary and leaves output-coordinate meaning open-ended; the Method
   Version contract supplies neither the exact version-identifier format nor
   the exact dependency-declaration format. The text also uses bare
   “Definition” as shorthand despite Stage 1's explicit full-name rule.
2. The frozen witnessed-versus-computed and Event Type distinction is not
   explicit in the operative contracts or gate. A Method Version is
   computational, but a Market Measure Definition may bind the umbrella
   `Market Measure`; the document does not mechanically prevent that binding
   or its example from recasting source-reported Observation meaning as a
   platform calculation.
3. Some field and evolution rules are not closed enough to be mechanically
   testable. Free-form output and evaluation text can carry prohibited
   semantics, Definition revision treatment omits subject-shape changes, and
   Method Version dependencies are described inconsistently as both an
   ordered set and a set.
4. The future admission gate is stated only “at minimum” and does not
   exhaustively enforce the contracts' own invariants. The future registry
   invariants likewise omit identity uniqueness and referential closure.
   Those omissions defer constitutional choices to the future mechanism the
   document is supposed to specify.

These defects are local to Stage 2. They can be corrected without reopening
the architecture, reopening Stage 1, introducing vocabulary, expanding M41,
or beginning implementation.

---

## Findings

### 1. Stage 1 reliance and vocabulary discipline

The document correctly relies on only the three confirmed Stage 1 terms that
WP1 owns:

- Market Measure Definition;
- Method Version; and
- Method Requirement, realizing the Applicability contract type.

Their exact definitions in sections 5.1, 6.1, and 7.2 reproduce the confirmed
Stage 1 definitions without semantic amendment. Market Intelligence remains
the single owner. Measure Subject, Measurement Window, and Measure Value are
not redefined, and Observation Input Manifest and the existing M40 vocabulary
are reused by reference. No rejected Calculation Temporal Claim or Producing
Domain specialization reappears.

There is, however, a direct Stage 1 naming violation. The confirmed register
section 6.1 requires future contract text to use the full compound name
`Market Measure Definition` and to never abbreviate it to bare `Definition`.
Stage 2 repeatedly uses governed shorthand such as “Definition identifier,”
“Bound Definition reference,” “the Definition's revision,” “specified
Definition,” and “production Definition.” These uses weaken the
non-conflation boundary with Asset Foundation's Definition Version and Asset
Definition.

**Severity:** Medium.

### 2. Contract completeness

#### 2.1 Market Measure Definition

The contract supplies an identity, owner, required fields, relationships,
revision rules, prohibited interpretations, and an illustrative example.
Its subject, input, and output fields correspond to the confirmed Stage 1
meaning.

It does not supply all evidence Stage 1 made mandatory for this contract:

- Stage 1 section 6.1 requires the exact subject-shape vocabulary. Stage 2
  instead says the field references a closure that WP2 “will specify” and
  permits “which shape(s)” without enumerating the exact allowed field
  representation.
- Stage 1 requires the exact output-coordinate-meaning vocabulary. Stage 2
  permits an “explicit statement,” gives open-ended examples, and refers to
  an “equivalent declared meaning.” This is not a closed vocabulary or exact
  representation.
- Stage 1 requires a worked example distinguishing a Market Measure
  Definition from an Asset Definition Version. The example cites a
  Valuation Semantics value but does not explicitly demonstrate the two
  identities, owners, version axes, and non-substitutability.

The revision rules also leave a material case undecided. They state the
treatment of umbrella-concept changes, fundamental output-question changes,
and removal of an input category, but do not state whether changing the
declared subject shape requires a new Market Measure Definition identifier.
That omission permits two implementations to classify the same semantic
change differently.

**Severity:** High.

#### 2.2 Method Version

The contract supplies an owner, a binding to exactly one Market Measure
Definition revision, a semantic-version field, dependency declarations,
Method Requirement relationships, immutability rules, a Deterministic
Calculation constraint, non-conflation with Asset Foundation's Definition
Version, and a non-admitted example.

Stage 1 section 6.2 nevertheless requires the exact version-identifier format
and exact dependency-declaration format. “Explicit, platform-assigned
identifier” and “exact, version-bound set” do not define either format. The
document also calls dependencies an “exact, ordered set” in identity, an
“exact, version-bound set” in the field table, and renders them with unordered
set braces in the example. Ordering is therefore both identity-bearing and
undefined.

**Severity:** High.

#### 2.3 Method Requirement / Applicability

The contract correctly carries forward Method Requirement as the sole record
realizing Applicability. It supplies a local identity, owner, closed
prerequisite-category list, deterministic evaluation, fail-closed
applicability, binary `MET`/`UNMET` results, orthogonality to Input
Sufficiency, prohibited interpretations, and a non-admitted example.

The category closure satisfies Stage 1's specific evidence obligation.
However, the evaluation rule remains unrestricted prose except for listed
judgment exclusions. It does not mechanically exclude Ledger events,
transactions, holdings, balances, Portfolio or Workspace state, or Wealth
and life-context data from the predicate itself. Section 7.7 prohibits those
interpretations, but the permitted-values definition must carry the same
fail-closed restriction for the field-level gate to be mechanically
testable.

The Method Version example also points to “section 7.6 worked example”; the
worked example is section 7.8.

**Severity:** Medium.

### 3. Five-part ownership boundary and frozen M40 distinction

Section 11 includes five rows for each contract and correctly recognizes the
required categories. The document also excludes Ledger, Portfolio, Wealth,
judgment, evaluation, provider, runtime, and storage authority in its
prohibited-interpretation and non-leakage sections.

The recorded passes are not yet fully supported by mechanically closed field
contracts:

- the Market Measure Definition output field accepts an open-ended statement
  or “equivalent declared meaning” rather than exact output vocabulary;
- the Method Requirement evaluation-rule field does not itself exclude every
  prohibited input category; and
- the Method Version gate reasons about the record's own fields without
  expressly carrying through the exact subject and output constraints of its
  bound Market Measure Definition.

More importantly, the approved architecture requires every M41 contract to
keep the witnessed-versus-computed/Event Type distinction explicit. Stage 2
mentions a “witnessed-versus-computed ownership discipline” only while
describing which record states what and how. It does not state the frozen
rule that a source-reported claim remains an M39 Observation with Event Type
`Observation`, while a platform-computed output is a Calculated Market
Measure with Event Type `Calculation` and Producing Domain `Market
Intelligence`.

This omission is material because the Definition contract permits either
`Market Measure` or `Calculated Market Measure` as its bound umbrella
concept, while the Method Version contract necessarily describes a
calculation. The worked example binds `Market Measure` and is then used by a
Method Version example without an explicit rule preventing a
source-reported claim from being represented as platform-computed. The
frozen distinction must be made operative without changing the confirmed
Stage 1 field.

**Severity:** High.

### 4. Cross-contract consistency and dependency correctness

The dependency direction is generally coherent:

```text
Market Measure Definition revision
        ↓
Method Version
        ↓
Method Requirement set
```

References point from Method Version to one exact Market Measure Definition
revision and from each Method Requirement to one declaring Method Version.
The prerequisite categories trace to subject shape, declared dependencies,
or M39 Observation availability. Input Sufficiency remains invocation-time
and is not redefined.

The following local inconsistencies prevent a complete pass:

- dependency ordering is identity-bearing in section 6.3 but undefined or
  apparently unordered in section 6.4 and the example;
- the effect of a subject-shape change on Market Measure Definition identity
  is unspecified;
- the worked-example cross-reference is incorrect.

These are specification defects, not architectural dependency reversals.

**Severity:** Medium.

### 5. Future method-admission gate and registry invariants

Sections 8 and 9 maintain correct stage separation:

- no gate is implemented or run;
- no Market Measure Definition, Method Version, Method Requirement, Formula,
  Method, or production catalog entry is admitted;
- no registry is created, persisted, or operated; and
- future implementation requires a separately chartered milestone.

The gate specification is incomplete. Section 8.2 says a future gate checks
the listed predicates “at minimum,” leaving the actual closed admission
predicate to future design. The list does not expressly gate:

- every invariant in sections 5.5–5.7, 6.5–6.8, and 7.5–7.7;
- the witnessed-versus-computed/Event Type rule;
- resolution and uniqueness of every declared dependency version;
- compatibility between the bound Market Measure Definition's declared
  subject/input/output constraints and the Method Version's concrete
  requirements and dependencies; or
- the requirement that a framework record's admission cannot by itself
  admit a Formula, Method, or other production calculation.

The future registry rules preserve immutability, exact references, an empty
valid state, and non-authority. They do not explicitly require unique
canonical identities, rejection of conflicting duplicate identities,
referential closure for bound Market Measure Definition revisions,
dependency versions, and Method Requirements, or deterministic
content-equivalence behavior. Those are constitutional invariants, not
implementation choices.

**Severity:** High.

### 6. Authority leakage and stage separation

No present authority leakage was found. The header and sections 3, 8, 9, 13,
and 15 consistently withhold:

- implementation and execution authority;
- runtime and provider authority;
- persistence and API authority;
- production catalog and method authority; and
- concrete admission authority.

The examples are marked illustrative and non-admitted. No formula, named
indicator, provider-shaped payload, runtime interface, persistence schema,
or production record is created. Stage 2 does not begin WP2.

The incomplete future-gate closure identified above must be corrected so
that future framework admission cannot be mistaken for concrete production
method admission, but the document does not exercise that authority now.

---

## Required Corrections

The following corrections are confined to
`M41_WP1_DEFINITION_METHOD_VERSION_APPLICABILITY_CONTRACT_SPECIFICATION.md`.
They do not reopen Architecture or Stage 1, introduce vocabulary, expand
milestone scope, or authorize implementation.

### M41-WP1-S2-IR-1 — Complete the confirmed Stage 1 contract evidence

**Severity:** High

1. Replace governed uses of bare `Definition` with the full canonical name
   `Market Measure Definition`, except where the text is explicitly naming
   the distinct existing terms Asset Definition or Definition Version.
2. Supply the exact field-level subject-shape vocabulary already fixed by
   Stage 1, without defining WP2's subject-binding contract.
3. Supply an exact, closed representation for required output-coordinate
   meaning using only existing canonical vocabulary and ordinary field-value
   syntax; do not leave admission-bearing meaning as arbitrary prose or
   “equivalent” meaning.
4. Make the Market Measure Definition worked example explicitly demonstrate
   its identity, ownership, version-axis, and non-substitutability relative
   to Asset Definition and Definition Version.
5. Supply the exact Method Version semantic-version-identifier format and
   exact dependency-declaration format that Stage 1 requires.

### M41-WP1-S2-IR-2 — Make the frozen M40 boundary mechanically operative

**Severity:** High

1. State explicitly in the operative contracts, five-part re-application,
   and future admission gate that source-reported claims remain M39
   Observations with Event Type `Observation`, while platform-computed
   outputs are Calculated Market Measures with Event Type `Calculation` and
   Producing Domain `Market Intelligence`.
2. Constrain the broad `Market Measure` binding so that no Market Measure
   Definition/Method Version combination or example can recast witnessed
   evidence as a platform calculation.
3. Close the output-coordinate and Method Requirement evaluation-rule
   representations so every permitted subject, input category, output
   meaning, prohibited Ledger/Portfolio/Wealth input, and prohibited
   judgment semantic is mechanically decidable from the concrete field
   values.
4. Re-run section 11's pass results against the corrected concrete fields.

### M41-WP1-S2-IR-3 — Resolve identity, evolution, and reference inconsistencies

**Severity:** Medium

1. Define one unambiguous dependency collection model and ordering rule, then
   use it consistently in Method Version identity, required fields,
   invariants, the admission gate, registry invariants, and examples.
2. State the identity consequence of every Market Measure Definition field
   change, including a declared subject-shape change.
3. Correct the Method Version example's section 7.6 reference to the actual
   Method Requirement worked example.

### M41-WP1-S2-IR-4 — Close the future gate and registry invariant sets

**Severity:** High

1. Replace the open-ended “at minimum” admission predicate with a closed,
   exhaustive set that enforces every applicable invariant in sections 5–7,
   including Deterministic Calculation, exact dependency resolution,
   cross-contract compatibility, and the corrected M40/Event Type boundary.
2. State explicitly that admitting a framework Market Measure Definition or
   Method Version under this future gate is not sufficient to admit a
   Formula, Method, reference calculation, named indicator, or production
   calculation.
3. Complete the future registry invariants with canonical-identity
   uniqueness, conflicting-duplicate rejection, full referential closure,
   and deterministic content-equivalence requirements.

---

## Repository Validation

- The reviewed Stage 2 document exists at the repository-conventional
  `docs/implementation/M41_WP1_...md` location.
- Its heading hierarchy is coherent and its relative governing-document
  references resolve to files present in the repository.
- The architecture, Stage 1 register, Stage 1 review, correction response,
  and confirmation remain separate artifacts and were not modified by this
  review.
- Repository status before this review showed only M41 documentation
  artifacts in scope; no production code, runtime, provider, persistence, API,
  formula, method, catalog, WP2, or closeout artifact was present as an M41
  change.
- `GLOSSARY.md`, the Decision Log, and Graphify output were not modified.
- Graphify was used only for the required read-only context query and was not
  refreshed.
- Git validation used a per-command safe-directory override because the
  workspace owner SID differs from the review process SID; no Git
  configuration was changed.
- This review document is the only repository file created by the Independent
  Review Board. Required Corrections and Independent Confirmation were not
  begun.

---

## Final Determination

APPROVED WITH REQUIRED CORRECTIONS
