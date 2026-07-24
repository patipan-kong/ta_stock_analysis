# M41-WP2 Stage C — Architecture Proposal

**Document role:** Architecture and Specification Author

**Document status:** Proposed boundary determination

**Proposal date:** 2026-07-24

**M41 Architecture authority:** Frozen (cited, not modified)

**M41-WP1 authority:** Frozen (cited, not modified)

**M41-WP2 Architecture authority:** Confirmed and frozen (cited, not modified)

**M41-WP2 Stage A authority:** Confirmed and frozen (cited, not modified)

**M41-WP2 Stage B authority:** Confirmed and frozen (cited, not modified)

**Implementation authority:** `NONE`

**Runtime authority:** `NONE`

**Provider authority:** `NONE`

**Persistence authority:** `NONE`

**API authority:** `NONE`

---

## Executive Summary

The confirmed [M41-WP2 Architecture Proposal](M41_WP2_ARCHITECTURE_PROPOSAL.md)
allocates M41-WP2 to exactly two internal stages:

1. Stage A — Candidate Vocabulary Supplement; and
2. Stage B — Subject and Manifest Contract Specification.

It allocates no Stage C concept, semantic responsibility, contract,
deliverable, validation vector, or authority. Its normative sequence directs
the repository from confirmed Stage B to M41-WP3, and its bottom-line scope
statement says that WP2's entire job is the concrete Measure Subject contract
and the concrete Observation Input Manifest contract tying the Manifest to
that Subject. Confirmed Stage B completes that allocation.

Accordingly, the exact semantic scope available to a putative M41-WP2 Stage C
is the empty set. Assigning Stage C any new vocabulary, field, record,
identity rule, ordering rule, serialization rule, binding rule, compatibility
rule, validation vector, or operational behavior would redesign the confirmed
M41-WP2 Architecture and would exceed this proposal's authority.

This proposal therefore records a boundary result, not a new semantic design:
no substantive M41-WP2 Stage C may begin under the current authorities. The
next architecture-allocated work is M41-WP3. A future governance action may
create a substantive Stage C only by explicitly amending and reconfirming the
frozen M41-WP2 Architecture before any Stage C contract work begins.

---

## Scope

### Included

This proposal includes only:

- determination of whether the confirmed M41-WP2 Architecture allocates any
  semantic work to Stage C;
- identification of the already-confirmed WP2 completion boundary;
- preservation of every frozen Stage A and Stage B result;
- preservation of the transition from confirmed WP2 to M41-WP3; and
- definition of the governance condition required before any future
  substantive Stage C could be designed.

The determination is:

```text
Stage C allocated concepts        = ∅
Stage C allocated contract fields = ∅
Stage C allocated semantics       = ∅
Stage C allocated deliverables    = ∅
Stage C operational authority     = NONE
```

### Explicitly excluded

Stage C does not:

- revisit Stage A vocabulary or dispositions;
- revisit, clarify, extend, consolidate, restate, or reinterpret Stage B
  contracts;
- modify Measure Subject, its three closed shapes, its ownership, its
  identity, its canonical ordering, or its canonical serialization;
- modify Observation Input Manifest, Manifest Entry, manifest membership,
  binding, identity, canonical ordering, canonical serialization, evidence
  equivalence, or evidence-conflict handling;
- add another Subject or Manifest coordinate;
- alter any Market Measure Definition, Method Version, or Method Requirement
  field or ownership relationship;
- define Measurement Window, timezone/calendar, unit/currency, adjustment,
  missing-data, arithmetic, decimal, or rounding semantics allocated to
  M41-WP3;
- define Measure Value, Result composition, Computation Outcome, the
  outcome/degraded-state interaction matrix, or Provenance semantics allocated
  to M41-WP4;
- admit a production Definition, Method Version, formula, reference method,
  or production method;
- specify a Registry, Applicability Resolver, computation kernel, provider,
  retrieval mechanism, persistence model, API, or runtime lifecycle; or
- perform WP2 closeout under a new stage label. The confirmed WP2 Architecture
  names its own review/correction/confirmation artifacts and does not allocate
  a third internal semantic stage.

### Governing scope proof

The boundary follows from the confirmed authorities:

- M41 Architecture assigns WP2 only the Subject and Observation Input
  Manifest contracts, canonical serialization, evidence equivalence/conflict,
  and manifest identity.
- M41-WP2 Architecture section 11 exhaustively decomposes WP2 into Stage A and
  Stage B.
- M41-WP2 Architecture section 12 directs work to WP3 after Stage B is
  confirmed.
- Confirmed Stage A closes its three candidate dispositions without leaving an
  undecided Stage C vocabulary obligation.
- Confirmed Stage B states that Measure Subject, Observation Input Manifest,
  and Manifest Entry are the only WP2-governed nouns it specifies and closes
  the complete WP2 contract allocation.

References in Stage B review artifacts saying that “Stage C” had not begun do
not allocate Stage C authority. They are repository-state observations, not
an amendment to the confirmed architecture.

---

## Architectural Responsibilities

Because Stage C has no allocated semantic scope, it has no affirmative
contract-design responsibility. The only responsibilities established by
this proposal are boundary-preservation responsibilities:

1. **Do not invent scope.** Absence of a Stage C allocation is not an
   invitation to infer one.
2. **Treat Stage A and Stage B as complete authorities.** No Stage C artifact
   may correct, normalize, summarize into replacement authority, or otherwise
   alter their confirmed content.
3. **Preserve the downstream handoff.** WP3 may cite the confirmed Measure
   Subject and resolved Observation Input Manifest primitives without Stage C
   mediation.
4. **Require explicit governance for change.** Any proposed substantive Stage
   C requires an explicit amendment to the frozen M41-WP2 Architecture,
   independent architecture review, resolution of required corrections, and
   independent confirmation before Stage C design begins.
5. **Preserve specification-only posture.** This proposal grants no
   implementation or operational authority.

These responsibilities are constraints on future action. They do not create a
Stage C domain model, contract, lifecycle, or deliverable.

---

## Ownership Boundaries

No ownership is created, transferred, shared, or reinterpreted.

| Boundary | Preserved authority | Stage C constraint |
|---|---|---|
| Measure Subject | Market Intelligence | No change to noun, three closed shapes, fields, identity, ordering, serialization, or five-part gate result |
| Asset identity (`asset_id`) | Asset Foundation | Citation only; no alias, wrapper identity, reinterpretation, or ownership transfer |
| Observation Input Manifest | Market Intelligence | No change to exact M39-evidence membership, binding, identity, ordering, serialization, or immutability |
| Manifest Entry | Market Intelligence | No change to admitted definition, fields, role closure, ordering, or ownership |
| M39 Observation evidence | Frozen M39 authority | Exact immutable identity citation only; no correction, merge, supersession, provider substitution, or content-based identity |
| Market Measure Definition | Frozen M41-WP1 | No field addition, renaming, reattribution, or permitted-input change |
| Method Version / Method Requirement | Frozen M41-WP1 | No field addition, renaming, reattribution, grammar change, or applicability change |
| WP3 semantics | M41-WP3 | No temporal, window, unit, currency, adjustment, missing-data, decimal, rounding, dependency, or arithmetic authority |
| WP4 semantics | M41-WP4 | No Result, Measure Value, Computation Outcome definition, state interaction, or Provenance authority |
| Ledger / Portfolio / Wealth / Judgment / Execution | Their existing frozen owners | No input, output, recommendation, strategy, transaction, or execution authority |

The five operational authorities remain:

| Authority | Value |
|---|---|
| Implementation | `NONE` |
| Runtime | `NONE` |
| Provider | `NONE` |
| Persistence | `NONE` |
| API | `NONE` |

---

## Compatibility Analysis

### Frozen M34

Compatible. The empty Stage C semantic scope creates no new ownership,
identity, domain, or authority surface and therefore cannot weaken M34
constitutional boundaries.

### Frozen M39

Compatible. No Observation meaning, identity, payload, relationship, evidence
membership, or witnessed-versus-computed distinction changes. Exact frozen
M39 Observation identities remain the only evidence eligible for Manifest
membership.

### Frozen M40

Compatible. Observation Input Manifest retains its frozen meaning as an
immutable, complete, deterministically ordered binding of exact evidence.
No provider-shaped input, dynamic `latest` reference, or negative-corpus
concept is introduced.

### Frozen M41 Architecture

Compatible. M41-WP2 remains limited to Subject and Manifest; M41-WP3 retains
temporal/unit/adjustment/arithmetic semantics; M41-WP4 retains Result/state/
Provenance semantics; implementation remains deferred; and Epic Closeout
remains a milestone-level activity after WP4 rather than a WP2 internal stage.

### Frozen M41-WP1

Compatible. No Market Measure Definition, Method Version, Method Requirement,
Measure Subject disposition, field-to-contract relationship, applicability
rule, ownership decision, or production-catalog guarantee changes.

### Confirmed M41-WP2 Architecture

Compatible. This proposal applies the architecture's exhaustive Stage A/Stage
B decomposition and its explicit Stage B-to-WP3 sequence. It does not amend
that decomposition by implication.

### Confirmed Stage A

Compatible. `Subject Reference` remains merged into Asset Foundation's
existing `asset_id`; `Subject Ordering Key` remains merged into Measure
Subject; Manifest Entry remains the sole new admitted Stage A noun; and all
recorded owners and dispositions remain unchanged.

### Confirmed Stage B

Compatible. Every normative Subject and Manifest rule remains unchanged,
including the `MSB1` and `OIM1` identity/serialization contracts, canonical
ordering, exact M39 evidence membership, evidence equivalence/conflict rules,
fail-closed behavior, immutability, and the mapping of unresolved evidence
conflict only to the existing `INSUFFICIENT_INPUT` outcome.

---

## Acceptance Criteria

This proposal is acceptable only if independent architecture review confirms
all of the following:

1. The confirmed M41-WP2 Architecture contains no Stage C allocation.
2. Stage C's semantic, vocabulary, field, contract, validation, and
   operational scope is therefore empty.
3. No Stage A vocabulary decision is reopened.
4. No Stage B contract is modified, extended, clarified, consolidated into
   replacement authority, or reinterpreted.
5. Measure Subject, Observation Input Manifest, Manifest Entry, canonical
   ordering, canonical serialization, ownership, and compatibility remain
   exactly as confirmed.
6. Frozen M34, M39, M40, M41 Architecture, M41-WP1, M41-WP2 Architecture,
   Stage A, and Stage B remain compatible and unmodified.
7. No implementation, runtime, provider, persistence, API, production catalog,
   Registry, Resolver, Kernel, or integration authority is introduced.
8. The next architecture-allocated semantic work remains M41-WP3.
9. Any future substantive Stage C is blocked until an explicit M41-WP2
   Architecture amendment is independently reviewed, corrected if required,
   and independently confirmed.
10. Repository changes are confined to this proposal.

Failure of any criterion requires rejection or correction of this proposal;
it does not authorize filling the perceived gap with inferred Stage C scope.

---

## Repository Validation

Validation was performed read-only before this proposal was created and again
afterward.

- **Stage A unchanged:** the Candidate Vocabulary Register and its review,
  correction-response, and independent-confirmation chain were not edited.
- **Stage B unchanged:** the Subject and Manifest Contract Specification and
  its review, correction-response, and independent-confirmation chain were not
  edited.
- **Architecture unchanged:** M41 Architecture and the complete confirmed
  M41-WP2 Architecture chain were not edited.
- **WP1 unchanged:** the Stage 1 register, Stage 2 contract specification,
  their review/confirmation chains, and WP1 Closeout were not edited.
- **Decision Log unchanged:** `docs/engineering/DECISION_LOG.md` was not
  edited.
- **Glossary unchanged:** `docs/GLOSSARY.md` was not edited.
- **Graphify unchanged:** Graphify was queried read-only. No
  `graphify update .` was run because this proposal changes no code and the
  user expressly limited repository modification to this document.
- **Implementation INDEX unchanged:** `docs/implementation/INDEX.md` was not
  edited.
- The pre-existing repository state contains the expected staged M41-WP2
  authority artifacts. No pre-existing staged artifact was altered by this
  proposal.
- The only repository file created or modified for this task is
  `docs/implementation/M41_WP2_STAGE_C_ARCHITECTURE_PROPOSAL.md`.

No implementation, runtime, production, provider, persistence, retrieval, or
API artifact was created or modified.

---

## Final Recommendation

Approve this proposal as the authoritative determination that the confirmed
M41-WP2 Architecture allocates no substantive Stage C.

Do not commence Stage C specification work, do not create Stage C contract
artifacts, and do not use Stage C as an ungoverned WP2 closeout or
consolidation stage. Treat confirmed Stage B as completion of the semantic
work allocated to M41-WP2 and proceed next only through the architecture-
allocated M41-WP3 governance sequence.

If governance intends Stage C to have substantive content, first amend the
frozen M41-WP2 Architecture explicitly. That amendment must name Stage C's
purpose, dependencies, deliverables, review artifacts, completion criteria,
ownership boundaries, and compatibility obligations, and must receive
independent review and confirmation before any Stage C design is drafted.

---

**Final status: READY FOR INDEPENDENT ARCHITECTURE REVIEW**
