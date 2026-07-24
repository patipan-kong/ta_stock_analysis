# M41-WP2 Stage B — Independent Review

**Document role:** Independent Architecture Review Board

**Review target:** [M41-WP2 Stage B Subject and Manifest Contract Specification](M41_WP2_STAGE_B_SUBJECT_AND_MANIFEST_CONTRACT_SPECIFICATION.md) (`COMPLETE_FOR_INDEPENDENT_REVIEW`, 2026-07-24)

**Authoritative references:** [M41 Architecture](M41_ARCHITECTURE_PROPOSAL.md) (frozen), [M41-WP1 Stage 1](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md) (frozen), [M41-WP1 Stage 2](M41_WP1_DEFINITION_METHOD_VERSION_APPLICABILITY_CONTRACT_SPECIFICATION.md) (frozen), [M41-WP2 Architecture](M41_WP2_ARCHITECTURE_PROPOSAL.md) (confirmed, [Final Architecture Confirmation](M41_WP2_FINAL_ARCHITECTURE_CONFIRMATION.md)), [M41-WP2 Stage A](M41_WP2_STAGE_A_CANDIDATE_VOCABULARY_REGISTER.md) (confirmed, [Stage A Independent Confirmation](M41_WP2_STAGE_A_INDEPENDENT_CONFIRMATION.md))

**Implementation authority:** `NONE`

**Runtime authority:** `NONE`

**Provider authority:** `NONE`

**Persistence authority:** `NONE`

**API authority:** `NONE`

**Review date:** 2026-07-24

---

## Executive Summary

The Stage B specification correctly builds only inside the two boxes WP2's confirmed
Architecture assigned it (Measure Subject, Observation Input Manifest) and correctly
carries forward Stage A's confirmed dispositions: it never reintroduces a capitalized
"Subject Reference" or "Subject Ordering Key" noun, it uses `asset_id` and ordinary
ordering language exactly as Stage A's Required Corrections Response mandated, and it
preserves Manifest Entry's confirmed `ADMIT` disposition and Market Intelligence
ownership without alteration. It explicitly reconciles Subject ordering and Manifest
ordering as one discipline over different key components, discharging the Architecture
Proposal's own §9 risk item. The two required ordering-permutation golden vectors (§7.4.2
Subject, §7.4.5 Manifest) are present and distinct, satisfying `M41-WP2-AC-2`. Ownership
remains singular throughout, and no implementation, runtime, provider, persistence, or
API authority is granted.

One finding is recorded. It concerns §5.4(7)'s treatment of the frozen M41-WP1
`ObservationEvidenceCount` operand: the specification asserts, rather than demonstrates,
that counting *distinct referenced Observation identities* (rather than *Manifest Entry
records*) "exactly preserv[es] the frozen M41-WP1 operand meaning," for a case WP1 could
not have disambiguated because Manifest Entry did not exist when WP1 froze that operand.
Because this choice changes `MET`/`UNMET` evaluation outcomes whenever one Observation
is validly cited by more than one requirement role, it needs an explicit chain of
justification back to WP1's own text before Stage B can rely on it as settled, rather
than as Stage B's own new interpretive act layered on a frozen field it is not permitted
to edit.

Determination: **APPROVED WITH REQUIRED CORRECTIONS**.

---

## Review Scope

This review evaluates only `M41_WP2_STAGE_B_SUBJECT_AND_MANIFEST_CONTRACT_SPECIFICATION.md`
against the frozen and confirmed authorities listed above, per the eleven scope items the
task specified: Measure Subject contract, Observation Input Manifest, Manifest Entry,
binding rules, canonical ordering, canonical serialization, validation requirements,
error conditions, validation vectors, ownership boundaries, and M34/M39/M40/M41
compatibility. It does not redesign the architecture, does not revisit Stage A admission
decisions, and does not perform WP3 or Stage C work.

---

## Findings

### M41-WP2-SB-IR-1 — `ObservationEvidenceCount` operand meaning asserted, not demonstrated, against frozen M41-WP1 text

**Issue:** §5.4(7) states: "Repetition across requirement roles does not create
additional M39 Observation evidence records. `ObservationEvidenceCount` remains the
count of distinct referenced M39 Observation identities in the entire manifest, exactly
preserving the frozen M41-WP1 operand meaning." §5.4(5) permits one referenced
Observation to support more than one applicable Method Requirement, with each distinct
(`requirement_key`, `observation_identity`) pair forming its own Manifest Entry — meaning
one Observation identity can back two or more Manifest Entries in the same manifest.

The frozen M41-WP1 Stage 2 contract (§7.4b) defines the operand's value as "the exact
count of M39 Observation evidence records in the invocation's Observation Input
Manifest." WP1 was frozen before Manifest Entry existed as a governed noun (Manifest
Entry is a Stage A, not WP1, admission), so WP1's text never had occasion to state
whether "evidence records" means distinct Observation identities or manifest line items
— the two readings coincide only when no Observation is ever cited by more than one
requirement role, a case WP1's own text does not exclude and Stage B's own §5.4(5)
explicitly permits.

This is not a hypothetical distinction: for a Method Requirement whose evaluation rule
is, for example, `(>= ObservationEvidenceCount 2)`, a manifest with one Observation
identity cited under two requirement roles evaluates to `MET` under Stage B's
"count of records" reading only if "records" means entries, and to `UNMET` under Stage
B's own chosen "distinct identities" reading. Two independent implementations working
only from the frozen WP1 text, without also being told Stage B's operational choice,
could disagree about a real evaluation outcome — the exact failure mode the "mechanically
checkable from its concrete value" property (WP1 §7.4a) exists to prevent.

**Rationale:** The confirmed WP2 Architecture (§0, §6) permits Stage B to cite WP1's
fields "by exact field reference only" and states WP2 "never edits their fields, identity
rules, or five-part gate results, and never attributes one contract's field to another."
Resolving a genuine ambiguity in a frozen field's operational meaning — even one WP1
could not have anticipated — is an interpretive act on that field, not a citation of it.
Stage B is entitled to make this determination (WP1's own text cannot mechanically
resolve a case it never contemplated, and someone must), but asserting textual identity
("exactly preserving the frozen M41-WP1 operand meaning") without showing the chain of
reasoning that makes "records" necessarily mean "distinct identities" rather than
"entries" overstates what the frozen WP1 text actually settles, and could mislead a
future WP3/WP4 reader into treating this as WP1-frozen rather than Stage-B-determined.

**Governing authority:** [M41-WP2 Architecture Proposal §0, §6](M41_WP2_ARCHITECTURE_PROPOSAL.md#0-what-wp2-inherits-vs-what-it-must-not-touch) (WP1 fields cited by exact reference only, never edited or reattributed); [M41-WP1 Stage 2 §7.4b](M41_WP1_DEFINITION_METHOD_VERSION_APPLICABILITY_CONTRACT_SPECIFICATION.md#74b-operand-value-domains-and-expression-semantics) (frozen `ObservationEvidenceCount` value definition); [M41-WP1 Stage 2 §7.4a](M41_WP1_DEFINITION_METHOD_VERSION_APPLICABILITY_CONTRACT_SPECIFICATION.md#74a-evaluation-rule-closed-grammar-and-canonical-form) (mechanically-checkable-from-concrete-value property).

**Required correction:** In §5.4(7) (and any place §5.7 or §9.9 restates the same claim),
replace the bare assertion of exact preservation with an explicit derivation: state that
WP1's "M39 Observation evidence records" cannot have meant "Manifest Entry" (a term that
did not exist at WP1's freeze), and therefore the only concept WP1's frozen text could
have been referring to is the M39 Observation evidence itself — i.e., distinct Observation
identity — making entry-level repetition definitionally outside what WP1 counted. Add one
worked golden vector (alongside §7.4.4–§7.4.8) showing one Observation identity cited by
two distinct requirement keys in one manifest, with the resulting `ObservationEvidenceCount`
value stated explicitly, so two independent implementations cannot diverge on this case.
No change to Measure Subject, Manifest Entry's own definition, ownership, or any other
Stage B section is required.

---

## Repository Validation

- Git reports branch `feature/m41`. Before this review was created, the only
  `M41_WP2_STAGE_B_*` artifact present was the reviewed specification itself
  (`COMPLETE_FOR_INDEPENDENT_REVIEW`); no `M41_WP2_STAGE_B_INDEPENDENT_REVIEW.md`,
  `M41_WP2_STAGE_B_REQUIRED_CORRECTIONS_RESPONSE.md`, or
  `M41_WP2_STAGE_B_INDEPENDENT_CONFIRMATION.md` existed.
- `M41_ARCHITECTURE_PROPOSAL.md` and its full WP1 authority chain (Stage 1 register,
  Stage 2 contract specification and all correction/confirmation rounds, Closeout) report
  no modification.
- `M41_WP2_ARCHITECTURE_PROPOSAL.md` and its full confirmation chain (Independent
  Architecture Review, Required Corrections Response, Architecture Confirmation,
  Architecture Confirmation Corrections Response, Final Architecture Confirmation) report
  no modification.
- `M41_WP2_STAGE_A_CANDIDATE_VOCABULARY_REGISTER.md` and its full confirmation chain
  (Independent Review, Required Corrections Response, Independent Confirmation) report no
  modification. No Stage A candidate definition, disposition, or ownership determination
  was reopened by this review.
- `docs/GLOSSARY.md`, `docs/engineering/DECISION_LOG.md`, and
  `docs/implementation/INDEX.md` report no modification.
- `graphify-out/` reports no modification; Graphify was not refreshed.
- No `M41_WP2_STAGE_C_*` or `M41_WP3_*` artifact exists. Stage C and WP3 have not begun,
  and this review does not perform either.
- No implementation, runtime, provider, persistence, or API behavior was introduced by
  the reviewed specification; all five operational authority fields remain `NONE`. This
  review introduces none either.
- The only repository file created by this review is this document.

---

## Final Determination

APPROVED WITH REQUIRED CORRECTIONS
