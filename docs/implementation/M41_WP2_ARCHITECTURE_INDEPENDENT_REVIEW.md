# M41-WP2 — Independent Architecture Review

**Review role:** Independent Architecture Review Board

**Artifact reviewed:** [M41-WP2 Architecture Proposal](M41_WP2_ARCHITECTURE_PROPOSAL.md)

**Architecture authority:** Frozen

**M41-WP1 authority:** Frozen

**Implementation authority:** `NONE`

**Runtime authority:** `NONE`

**Provider authority:** `NONE`

**Persistence authority:** `NONE`

**API authority:** `NONE`

**Review date:** 2026-07-23

---

## Executive Summary

The proposed M41-WP2 boundary is directionally consistent with the confirmed
M41 architecture. It keeps WP2 specification-only, preserves the separation
from WP3, WP4, the future Registry, Resolver, Kernel, and integration work,
and uses an appropriate two-stage sequence in which candidate vocabulary is
confirmed before contract text relies on it. The proposal also correctly
retains an empty production Definition/Method catalog and grants no
implementation, runtime, provider, persistence, or API authority.

The proposal is not yet architecturally ready. Seven required corrections are
local to the WP2 proposal. The most important are frozen-contract defects:
the proposal repeatedly assigns the four-category permitted-input declaration
to Method Requirement even though the frozen WP1 contract assigns it to
Market Measure Definition; it then risks widening Observation Input Manifest
membership beyond M39 Observation evidence; and it places Definition Version
inside Measure Subject despite the confirmed three-shape definition containing
only canonical Asset identity references or a no-Asset market-context
parameter set.

The proposal also reopens Stage 1 classifications that already made manifest
identity and equivalence/conflict disposition ordinary non-canonical contract
language, omits Measure Subject canonical serialization from its normative
deliverable decomposition, leaves conflict-to-outcome ownership ambiguous,
and incompletely states the Stage A admission and evidence gates. None of
these findings requires changing the M41 architecture, reopening WP1, adding
vocabulary, or expanding WP2. They require the WP2 proposal to bind precisely
to the authority it already cites.

---

## Strengths

1. **Correct milestone placement.** The proposal keeps WP2 strictly between
   the confirmed WP1 contracts and the future WP3/WP4 contracts. Registry,
   Resolver, Kernel, and integration remain deferred to separately governed
   work.
2. **Correct specification-only posture.** The proposal excludes executable
   modules, provider access, persistence, APIs, Registry mutation, and
   production method admission. Its authority statement assigns all
   operational authorities `NONE`.
3. **Correct high-level WP2 subject matter.** Measure Subject construction,
   identity, ordering, and binding, together with Observation Input Manifest
   binding, serialization, equivalence/conflict treatment, and identity, are
   the content allocated to WP2 by the confirmed M41 architecture.
4. **Sound stage ordering in principle.** Stage A precedes Stage B, and the
   proposal states that Stage B may use only confirmed vocabulary. Stage B
   must complete independent review, correction, and confirmation before WP3
   begins.
5. **Good boundary awareness.** The proposal explicitly preserves frozen M39
   Observation meaning, Asset Foundation identity authority, the M40
   ownership boundary, the empty production catalog, and the prohibition on
   Ledger, Portfolio, Wealth, judgment, and provider-shaped semantics.
6. **Useful specification evidence.** Documentation-only golden vectors,
   canonical-byte examples, round-trip reconstruction, field-level five-part
   gate tables, and negative-corpus checks are appropriate evidence forms for
   M41.

---

## Findings

### M41-WP2-AR-1 — Frozen permitted-input field is assigned to the wrong contract

**Severity:** Major

**Issue**

Sections 0, 1, 2, and 5 state that a Method Requirement has “declared input
categories” or a “permitted-input-category closure” that WP2 maps to manifest
entries. The frozen WP1 Stage 2 contract declares no such Method Requirement
field. The four-category permitted-input declaration belongs to Market Measure
Definition. Method Requirement instead owns a prerequisite category and a
closed evaluation rule; its permitted prerequisite categories are subject
shape, dependency presence, and Observation category availability.

**Rationale**

Using a non-existent Method Requirement field would either reinterpret that
contract or silently add a field to it. Both outcomes violate the proposal's
own lateral boundary and make the planned binding algorithm impossible to
trace mechanically to the confirmed WP1 fields.

**Governing authority**

- [M41-WP1 Stage 2 §5.4](M41_WP1_DEFINITION_METHOD_VERSION_APPLICABILITY_CONTRACT_SPECIFICATION.md#54-required-fields)
  assigns the four-category declaration to Market Measure Definition.
- [M41-WP1 Stage 2 §7.4](M41_WP1_DEFINITION_METHOD_VERSION_APPLICABILITY_CONTRACT_SPECIFICATION.md#74-required-fields)
  closes Method Requirement to its declaring Method Version reference,
  prerequisite category, and evaluation rule.
- [M41-WP1 Stage 2 §10](M41_WP1_DEFINITION_METHOD_VERSION_APPLICABILITY_CONTRACT_SPECIFICATION.md#10-cross-contract-consistency)
  fixes the field-to-contract relationships.
- [M41-WP1 Closeout §Frozen Deliverables](M41_WP1_CLOSEOUT.md#frozen-deliverables)
  prohibits future work packages from redefining the three WP1 contracts.

**Required correction**

Replace every attribution of a permitted-input-category declaration or
four-category closure to Method Requirement with exact references to the
frozen owning fields. The WP2 binding plan must distinguish:

- Market Measure Definition's permitted input-category declaration;
- Method Version's exact dependencies and declared Method Requirement set;
  and
- each Method Requirement's frozen prerequisite category and evaluation rule.

No WP1 field may be added, renamed, or reinterpreted.

### M41-WP2-AR-2 — Proposed binding rule widens Observation Input Manifest

**Severity:** Major

**Issue**

Sections 2 and 5 say that all four permitted input categories—M39 evidence,
Asset Foundation references, invocation parameters, and governed calculation
dependencies—resolve to Observation Input Manifest entries. The frozen
Observation Input Manifest meaning is narrower: its membership enumerates
exact frozen M39 Observation semantics selected as calculation inputs.

**Rationale**

Putting Asset Foundation references, parameters, or calculation dependencies
inside manifest membership would redefine an effective M40 term. Those inputs
may participate in the wider invocation and contract binding, but they do not
become Observation Input Manifest evidence entries. The current wording also
conflicts internally with the proposal's own proposed Manifest Entry
description, which names an M39 Observation reference.

**Governing authority**

- [Canonical Glossary — Observation Input Manifest](../GLOSSARY.md#observation-input-manifest)
  limits manifest membership to exact frozen M39 Observation semantics.
- [M41 Architecture §8](M41_ARCHITECTURE_PROPOSAL.md#8-architectural-approach)
  requires each input class to trace to one of four categories but does not
  collapse those categories into manifest membership.
- [M41-WP1 Stage 1 §6.7](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md#67-observation-input-manifest--reuse)
  requires WP2 to cite the frozen term without narrowing or widening it.

**Required correction**

Constrain every Observation Input Manifest entry and its serialization,
identity, equivalence, and conflict rules to exact M39 Observation evidence.
Describe Asset Foundation references, explicit invocation parameters, and
governed calculation dependencies only through their separately owned frozen
contract coordinates. The broader binding contract may verify all relevant
coordinates, but it must not represent the other three categories as manifest
membership.

### M41-WP2-AR-3 — Definition Version is placed inside Measure Subject without authority

**Severity:** Major

**Issue**

Section 6 states that Measure Subject references both Asset identity and
Definition Version and calls this an existing constraint from Stage 1
§6.4. Stage 1 §6.4 does not say that. The confirmed Measure Subject shapes
contain canonical Asset identity references for shapes (1) and (2), or an
explicit no-Asset market-context parameter set for shape (3). The proposal's
own Sections 0 and 2 accurately repeat those shapes, so Section 6 is also
internally inconsistent.

**Rationale**

The confirmed M41 architecture requires WP2's overall contract to bind a
calculation to exact Assets, Definition Versions, and M39 Observation
evidence. That does not authorize adding Definition Version to Measure
Subject itself. Doing so would change the content of the closed shapes and
would also risk conflating the independent Asset Definition Version and
Method Version axes that WP1 explicitly separated.

**Governing authority**

- [M41-WP1 Stage 1 §6.4](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md#64-measure-subject)
  supplies the exact, closed three-shape definition.
- [M41-WP1 Stage 2 §5.4](M41_WP1_DEFINITION_METHOD_VERSION_APPLICABILITY_CONTRACT_SPECIFICATION.md#54-required-fields)
  cites exactly those three shapes and adds no Definition Version coordinate.
- [M41-WP1 Stage 2 §6.6](M41_WP1_DEFINITION_METHOD_VERSION_APPLICABILITY_CONTRACT_SPECIFICATION.md#66-non-conflation-with-asset-foundation-definition-version)
  preserves version-axis separation.
- [M41-WP1 Closeout §Remaining Work](M41_WP1_CLOSEOUT.md#remaining-work)
  defers Measure Subject construction, serialization, identity, and binding
  without reopening its confirmed meaning.

**Required correction**

Remove the claim that Definition Version is a field or constituent of Measure
Subject or that Stage 1 requires it there. Keep all three Subject variants
exactly within the confirmed closure. The proposal must still require WP2's
overall binding contract to account for exact Asset Definition Version
references where the governing architecture requires them, while preserving
their own Asset Foundation authority and their separation from Measure
Subject identity.

### M41-WP2-AR-4 — Stage 1 vocabulary classifications are reopened

**Severity:** Major

**Issue**

Sections 4 and 11 propose Manifest Identity, Equivalence Disposition, and
Conflict Disposition as possible or definite new governed candidates. The
confirmed Stage 1 complete noun inventory already classified “manifest
identity” and “equivalence vs. conflict disposition” as ordinary
non-canonical contract language. The proposal also leaves Manifest Identity
simultaneously a possible candidate and possible ordinary language, so its
own vocabulary plan has no single disposition.

**Rationale**

The architecture allows WP2 to propose a genuinely newly discovered noun,
but it does not allow WP2 to re-candidate language whose classification Stage
1 already settled. Doing so reopens the frozen register and creates avoidable
V1 ambiguity. Other proposed labels such as Subject Reference, Subject
Ordering Key, and Manifest Entry must first demonstrate that they are
governed nouns rather than ordinary field labels; their ownership cannot be
treated as predetermined merely because the proposal lists them.

**Governing authority**

- [M41-WP1 Stage 1 §6.0](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md#60-complete-noun-inventory)
  classifies canonical serialization, equivalence vs. conflict disposition,
  and manifest identity as ordinary non-canonical contract language.
- [M41-WP1 Independent Confirmation](M41_WP1_INDEPENDENT_CONFIRMATION.md)
  confirms the corrected noun inventory and disposition records.
- [M41 Architecture §8](M41_ARCHITECTURE_PROPOSAL.md#8-architectural-approach)
  permits a later work package to propose a further noun only through the
  complete candidate-admission workflow.

**Required correction**

Preserve Stage 1's ordinary-language classifications for manifest identity
and equivalence/conflict disposition and remove them from the proposed new
candidate set. For any other genuinely newly discovered candidate, require
Stage A to establish why existing canonical vocabulary and ordinary contract
language are insufficient before requesting a disposition. Do not pre-admit
the term or pre-decide its owner in the architecture proposal.

### M41-WP2-AR-5 — Measure Subject serialization and acceptance evidence are incomplete

**Severity:** Major

**Issue**

The objectives, included scope, component decomposition, and Stage B
deliverable specify Measure Subject record structure, identity, and ordering,
but omit a normative Measure Subject canonical serialization rule. Section 8
later asks for round-trip reconstruction of Subject and Manifest bytes even
though Section 5 defines canonical serialization only for the Manifest. The
fixture set also does not explicitly cover ordering permutations, distinct
identity conflicts, provider-leak rejection, or exact evidence reproduction.

**Rationale**

WP1 Stage 2 and WP1 Closeout explicitly defer Measure Subject construction,
serialization, identity, and binding to WP2. A round-trip assertion cannot be
mechanically reviewed without a closed byte-level Subject encoding. The
confirmed M41 evidence model requires exact canonical input and output bytes,
and the inherited WP2 validation boundary requires more than one positive
example per shape.

**Governing authority**

- [M41-WP1 Stage 2 §12](M41_WP1_DEFINITION_METHOD_VERSION_APPLICABILITY_CONTRACT_SPECIFICATION.md#12-relationship-to-m41-wp2wp4)
  defers Measure Subject construction and serialization to WP2.
- [M41-WP1 Closeout §Remaining Work](M41_WP1_CLOSEOUT.md#remaining-work)
  repeats construction, serialization, identity, and binding as WP2 work.
- [M41 Architecture §13](M41_ARCHITECTURE_PROPOSAL.md#13-required-evidence)
  defines exact byte-level canonical serialization and golden-vector
  evidence.
- The frozen M40 planning boundary for Subject and Observation Input Manifest
  requires ordering permutations, equivalent duplicates, distinct conflicts,
  provider-leak checks, and exact evidence reproduction.

**Required correction**

Add Measure Subject canonical serialization as an explicit objective,
included-scope item, Stage B component, deliverable, and acceptance criterion.
Make the validation matrix explicitly cover all three shapes, subject and
manifest ordering permutations, M39 Identity-Equivalent representations,
identity-distinct conflicts, forbidden provider-shaped inputs, byte-level
round trips, and exact evidence reproduction. All fixtures remain
documentation/data only and non-executable.

### M41-WP2-AR-6 — Conflict handling crosses into WP4 and remains architecturally undecided

**Severity:** Major

**Issue**

Sections 1, 2, and 5 assign each equivalence/conflict disposition a
Computation Outcome mapping. Section 9 then says the likely mapping is
`INSUFFICIENT_INPUT` “or a new outcome,” while also acknowledging that a new
outcome would reopen the frozen four-value enum. The proposal therefore both
crosses into WP4's Result/Outcome allocation and leaves a constitutional
choice unresolved.

**Rationale**

WP2 owns deterministic input equivalence, selection, and conflict rules. WP4
owns the complete Result, Computation Outcome interaction, and
outcome/degraded-state model. The frozen Glossary already states the
Input Sufficiency-to-`INSUFFICIENT_INPUT` relationship; WP2 may cite that
existing rule but may neither introduce a fifth outcome nor pre-specify the
WP4 Result composition. “Likely” is not a closed architectural boundary.

**Governing authority**

- [M41 Architecture §6](M41_ARCHITECTURE_PROPOSAL.md#6-scope) allocates
  equivalence/conflict disposition to WP2 and the Computation Outcome/Result
  model to WP4.
- [Canonical Glossary — Computation Outcome](../GLOSSARY.md#computation-outcome)
  closes the outcome set to four values.
- [Canonical Glossary — Input Sufficiency](../GLOSSARY.md#input-sufficiency)
  defines the existing `INSUFFICIENT` to `INSUFFICIENT_INPUT` mapping.
- [M41-WP1 Stage 2 §3](M41_WP1_DEFINITION_METHOD_VERSION_APPLICABILITY_CONTRACT_SPECIFICATION.md#3-scope)
  defers Result and Computation Outcome interaction text to WP4.

**Required correction**

Close the WP2 boundary unambiguously: Stage B specifies deterministic
evidence-equivalence, duplicate, selection, and conflict dispositions and
their input-sufficiency consequence, while citing existing canonical outcome
semantics where needed. Remove every possibility of a new Computation Outcome
and do not specify WP4 Result composition or the outcome/degraded-state
interaction matrix.

### M41-WP2-AR-7 — Stage A governance and artifact decomposition are incomplete

**Severity:** Moderate

**Issue**

Stage A's deliverable lists only an exact definition, owner, disposition
request, Glossary overlap, and negative-corpus analysis. It omits explicit
V1–V3 analysis, M34/M39/M40 compatibility, the candidate-level five-part
gate, and synchronization evidence required by the confirmed M41 workflow.
Its completion criterion says required corrections are independently
confirmed but does not unconditionally state that every disposition itself
must receive Independent Confirmation. Section 10 also proposes one generic
set of WP2 review filenames despite Stage A and Stage B each requiring
separate review/correction/confirmation artifacts.

The document header describes the reviewed artifact only as a preserved
advisory draft intended to seed a future formal proposal. That status is
inconsistent with this document being the WP2 architecture proposal now
submitted to governance, and its inline authority sentence omits the
repository's complete explicit authority/status header convention.

**Rationale**

These omissions allow candidate dispositions to appear usable after review
without confirmation, make Stage A evidence weaker than the frozen workflow,
and create ambiguous review-artifact ownership between the two internal
stages. The advisory-only status also makes it unclear whether corrections
apply to the reviewed proposal or to a different future document.

**Governing authority**

- [M41 Architecture §8](M41_ARCHITECTURE_PROPOSAL.md#8-architectural-approach)
  requires exact definition, single owner, disposition, complete overlap
  analysis, V1–V3, M34/M39/M40 compatibility, Required Corrections,
  unconditional Independent Confirmation, synchronization, and only then
  downstream reliance.
- [M41 Architecture §11](M41_ARCHITECTURE_PROPOSAL.md#11-proposed-work-package-structure)
  requires independent review for WP2 and prevents the next work package from
  beginning before corrections are resolved.
- [M41 Architecture §13](M41_ARCHITECTURE_PROPOSAL.md#13-required-evidence)
  requires distinct work-package, review-response, and confirmation evidence.
- [M41-WP1 Closeout](M41_WP1_CLOSEOUT.md) demonstrates the repository's
  stage-specific artifact naming and explicit authority posture.

**Required correction**

Make Stage A's record and acceptance criteria include every confirmed
candidate-admission evidence field and require Independent Confirmation for
every disposition, whether or not review required corrections. Define
unambiguous, stage-specific review, correction-response, and confirmation
artifacts for Stage A and Stage B. Update the proposal's own status and header
so this exact artifact is the submitted WP2 architecture proposal, with the
complete authority/status fields explicit and all operational authorities
`NONE`.

---

## Required Corrections

The following corrections are required before M41-WP2 architecture can be
approved:

1. **M41-WP2-AR-1:** Restore exact WP1 field ownership in every binding-rule
   statement.
2. **M41-WP2-AR-2:** Keep Observation Input Manifest membership limited to
   exact frozen M39 Observation evidence.
3. **M41-WP2-AR-3:** Remove Definition Version from Measure Subject's closed
   shape content while retaining its separately owned binding coordinate.
4. **M41-WP2-AR-4:** Preserve the Stage 1 ordinary-language classifications
   and gate only genuinely new vocabulary.
5. **M41-WP2-AR-5:** Add complete Measure Subject serialization and the
   required validation matrix to Stage B.
6. **M41-WP2-AR-6:** Close conflict handling inside the WP2/WP4 boundary and
   prohibit any new Computation Outcome.
7. **M41-WP2-AR-7:** Complete the unconditional Stage A governance,
   evidence, artifact naming, and proposal-status requirements.

All corrections are local to
`M41_WP2_ARCHITECTURE_PROPOSAL.md`. They do not authorize changes to the M41
architecture, WP1 artifacts, the Glossary, the Decision Log, Graphify output,
or implementation artifacts. Stage A and Stage B remain unopened.

---

## Repository Validation

- The existing Graphify knowledge graph was queried read-only for navigation.
  It was not refreshed or updated.
- The branch reported by Git is `feature/m41`.
- Before this review document was created, Git reported only
  `docs/implementation/M41_WP2_ARCHITECTURE_PROPOSAL.md` as untracked. No
  tracked modification was present.
- The WP2 proposal contains no executable implementation artifact and grants
  implementation, runtime, provider, persistence, and API authority `NONE`.
- No production Market Measure Definition, Method Version, Method
  Requirement, formula, method, provider, or production catalog is admitted.
- The proposal does not modify the approved three Measure Subject shapes in
  its stated scope, but finding `M41-WP2-AR-3` identifies one contradictory
  data-boundary sentence that must be corrected before that preservation is
  reliable.
- The proposal states that Market Measure Definition, Method Version, and
  Method Requirement are frozen, but findings `M41-WP2-AR-1` and
  `M41-WP2-AR-2` identify operative binding text that is not yet consistent
  with those frozen contracts.
- No M41-WP2 Stage A or Stage B artifact exists or was begun by this review.
- No Glossary, Decision Log, Implementation Index, Graphify, source-code,
  fixture, WP1, WP3, or WP4 file was modified by this review.
- The only repository file created by this review is this independent review
  document.

---

## Final Determination

APPROVED WITH REQUIRED CORRECTIONS
