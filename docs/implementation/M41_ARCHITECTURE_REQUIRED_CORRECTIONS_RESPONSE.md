# M41 Architecture Proposal — Required Corrections Response

**Date:** 2026-07-23

**Document class:** Response to independent architectural review required
corrections

**Reviewed document:** [M41_ARCHITECTURE_PROPOSAL.md](M41_ARCHITECTURE_PROPOSAL.md)

**Governing review:** [M41_ARCHITECTURE_INDEPENDENT_REVIEW.md](M41_ARCHITECTURE_INDEPENDENT_REVIEW.md)
— Independent Architecture Review Board, outcome
`APPROVED WITH REQUIRED CORRECTIONS`

**Independent confirmation:** [M41_ARCHITECTURE_INDEPENDENT_CONFIRMATION.md](M41_ARCHITECTURE_INDEPENDENT_CONFIRMATION.md)
— outcome `NOT CONFIRMED`, RC-2 partially unresolved; the two governance
wording corrections it required are addressed in this revision (see
"RC-2 Follow-Up — Independent Confirmation Corrections" below).

**Author role:** Same author as the proposal and self-review, responding to
an independent review it did not write. This response resolves the five
required corrections (RC-1 through RC-5) without redesigning the milestone,
changing the approved architectural boundary, expanding scope, or beginning
WP1.

**Implementation authority:** `NONE`

**Decision Log:** Not updated.

**Graphify:** Not refreshed.

**Milestone boundary:** Unchanged. The specification-only WP1–WP4 boundary,
confirmed sound by the independent review (§3.1 of the review), is preserved
exactly as proposed.

---

## Executive Summary

The Independent Architecture Review Board approved the M41 specification-
only boundary and found the WP1→WP2→WP3→WP4 dependency order coherent, but
required five corrections before WP1 may begin. All five are resolved in
this revision of `M41_ARCHITECTURE_PROPOSAL.md`:

- **RC-1** — the one place the proposal contradicted frozen M40 vocabulary
  (reusing the rejected "Calculation Temporal Claim" name, and listing the
  already-canonical Observation Input Manifest and Provenance as candidate
  new terms) is corrected to explicit reuse.
- **RC-2** — a four-stage candidate-vocabulary admission workflow (Candidate
  → Admission Review → Disposition [`ADMIT`/`REUSE`/`RENAME`/`REJECT`] →
  Synchronization) is now specified in §8, so canonical terminology cannot
  be created merely by drafting text.
- **RC-3** — the frozen M40 five-part ownership boundary (permitted subject,
  permitted inputs, output meaning, prohibited portfolio/ledger/life inputs,
  prohibited judgment semantics) and the witnessed-versus-computed
  distinction are now an explicit, mechanically applied validation gate on
  every WP1–WP4 artifact, and an acceptance-criterion admission blocker
  rather than descriptive guidance.
- **RC-4** — the proposal now states explicitly that M41 specifies but does
  not exercise the future method-admission mechanism, and that the
  production Definition/Method/Formula/catalog remains empty throughout
  M41.
- **RC-5** — golden vectors, canonical serialization, hash stability, and
  round-trip validation are now defined precisely as documentation/data
  fixtures; non-committed helper scripts are scoped as out-of-repository
  scratch work with no bearing on approval, and durable validation tooling
  is confirmed out of scope; the Graphify refresh is now explicitly gated on
  independent review and confirmation of the closeout document itself, not
  on its drafting.

No correction required moving the milestone boundary, pulling Registry/
Kernel/Integration work into M41, or changing the WP1–WP4 structure. All
five are additive precision and gating corrections to a boundary the review
already found sound.

---

## RC-1 — Frozen Vocabulary Contradicted Inside the Proposal

**Decision:** Accepted

**Changes made:**

- §6 (Scope), M41-WP4 bullet: removed "Calculation Temporal Claim usage" and
  replaced it with explicit reuse of the existing Canonical Temporal Claim,
  qualified by Event Type `Calculation` and Producing Domain `Market
  Intelligence` — the same construction M40 itself used when it rejected
  Calculation Temporal Claim as a duplicate specialization.
- §8 (Architectural Approach): removed "Input Manifest" and "Provenance"
  from the list of example new registrable nouns. §8 now states explicitly
  that Observation Input Manifest (one of M40's eight admissions) and
  Provenance (pre-existing, foundational Glossary vocabulary — confirmed
  present at `GLOSSARY.md` §"Provenance") are `REUSE` dispositions from the
  outset, not `ADMIT` candidates, and that M41 binds to their frozen meaning
  without re-registering either.

**Architectural rationale:** Platform Architecture §12 V1 (one term, one
meaning, one home) and V3 (constitutional terms are reserved) make this a
constitutional defect, not a wording slip. Reusing the name of a term M40
explicitly rejected — even informally, in a scope bullet — risks a future
work package treating that name as available. Listing an already-effective
Glossary entry as a candidate for new registration risks a redundant or
conflicting Glossary edit landing during WP1–WP4. Both risks are closed by
stating the correct disposition (reuse of Canonical Temporal Claim; reuse of
Observation Input Manifest and Provenance) directly in the sections that
will be read first by whoever drafts WP1–WP4, rather than relying on a
reviewer to catch the contradiction later. This directly satisfies the
review's instruction to run the negative-corpus check against the proposal
itself, not only against future work-package artifacts (§2.2, RC-1 of the
independent review).

---

## RC-2 — Candidate-Vocabulary Admission Workflow

**Decision:** Accepted

**Changes made:**

§8 (Architectural Approach) originally specified a four-stage workflow that
every candidate noun must pass through before a work package may rely on it
as canonical: Candidate → Admission review → Disposition
(`ADMIT`/`REUSE`/`RENAME`/`REJECT`) → Synchronization. §8 pre-applied this
workflow to M41's own known vocabulary: Observation Input Manifest and
Provenance as `REUSE`; Calculation Temporal Claim carrying forward M40's
`REJECT`; Market Measure Definition, Method Version, Measure Subject, Method
Requirement, Measurement Window, and Measure Value as open candidates.

The subsequent independent confirmation ([M41_ARCHITECTURE_INDEPENDENT_CONFIRMATION.md](M41_ARCHITECTURE_INDEPENDENT_CONFIRMATION.md))
found this workflow only partially resolved RC-2 and required two further
governance wording corrections, addressed below in
"RC-2 Follow-Up — Independent Confirmation Corrections."

**Architectural rationale:** The review's finding was precise: same-change
Glossary synchronization satisfies only the timing half of V2, not the
admission half. M40's own frozen history (WP1 candidate specification →
WP2 admission review, with ownership, overlap, negative-corpus, and temporal-
grammar proofs required before any term counted as canonical) is the
existing convention this workflow reproduces — it does not invent a new
governance track, it makes explicit and repeatable the review structure M40
already used, folded into each work package's own independent review rather
than added as a separate cycle. This avoids doubling M41's review overhead
(a risk §10 already flags) while still closing the gap the review identified.

---

## RC-2 Follow-Up — Independent Confirmation Corrections

**Decision:** Accepted

**Changes made:**

The independent confirmation found RC-2 only partially resolved and required
exactly two governance wording corrections, both applied to
`M41_ARCHITECTURE_PROPOSAL.md`, with no redesign, no change to any
architectural decision, no change to milestone scope, and no change to work
package boundaries:

1. **WP1 begins with the complete register.** §6 (Scope), M41-WP1 bullet and
   §11 (Proposed Work Package Structure), M41-WP1 row now state explicitly
   that WP1 SHALL begin by creating the complete Candidate Vocabulary and
   Ownership Register — every noun M41 is known to require, with its
   proposed exact definition, single owning domain, and disposition request
   — before any Definition or Method Version contract specification begins.
2. **Independent Confirmation is an explicit stage.** §8's workflow is now
   five stages, not four: **Candidate Vocabulary Register → Independent
   Review → Required Corrections (if any) → Independent Confirmation → only
   then may downstream artifacts rely on that disposition.** A disposition
   that required corrections is not final until independently confirmed;
   only a confirmed disposition may synchronize the Glossary or be relied
   upon by a later work package, a later section of the same work package,
   or a fixture. §12 (Acceptance Criteria) restates this as an admission
   blocker: independent review alone is not sufficient reliance evidence.

**Architectural rationale:** The independent confirmation's own two findings
were precise and narrow. First, per-work-package candidate discovery
satisfies the four-stage workflow's mechanics but not the governing review's
explicit requirement that WP1 begin with a complete upfront register —
without it, a later work package could still discover and rely on a term
mid-stream without the register-level overlap analysis the review required.
Second, requiring a correction to be "resolved" before the next work package
opens is not the same as requiring the correction itself to be independently
confirmed before a *disposition it affects* is relied upon downstream —
closing this gap makes independent confirmation, not independent review, the
event that licenses reliance, consistent with how this same remediation
cycle (self-review → independent review → corrections → independent
confirmation) is itself being applied to the M41 proposal as a whole.

---

## RC-3 — Frozen M40 Ownership Boundary as an M41 Validation Gate

**Decision:** Accepted

**Changes made:**

- §8 (Architectural Approach): added the "Frozen M40 ownership-boundary
  validation gate" — the exact five-part boundary from `M40-WP1` §6.1–6.2
  (permitted subject, permitted inputs, output meaning, prohibited
  portfolio/ledger/life-context inputs, prohibited judgment semantics),
  stated as a gate every Definition, Method Requirement, Subject, Manifest
  entry, and Result coordinate in WP1–WP4 must pass before independent
  review may approve it. Also carries forward the witnessed-versus-computed/
  Event Type distinction from M40-WP1 §4.1, and requires every input class a
  work package specifies to trace to one of the four permitted-input
  categories M40-WP1 §6.1–6.2 enumerated.
- §11 (Work Package Structure): each WP row's "Independent review" column
  now explicitly names the ownership-boundary gate and the candidate-
  vocabulary admission review as part of that work package's required
  review, not a separate activity.
- §12 (Acceptance Criteria): added an explicit criterion stating the gate is
  "an independent-review admission blocker, not a recommendation" — a work
  package that has not passed it does not return `APPROVED`.
- §15 (Closeout Requirements): whole-corpus reconciliation at closeout now
  explicitly re-checks that the gate held across every WP1–WP4 artifact.

**Architectural rationale:** The review's point was exact: M40's corrections
were approved because they supplied a *mechanically testable* boundary, and
general "no reinterpretation" language is weaker than the admission-blocking
mechanism whose approval made the M40 boundary sound. Restating the same
five-part structure M40-WP1 already used — rather than inventing a new
boundary test — keeps M41 inside the existing, already-approved convention
and gives every future WP1–WP4 independent reviewer the same checklist M40's
reviewers used, cited to its exact source section.

---

## RC-4 — Specifying the Method-Admission Mechanism vs. Exercising It

**Decision:** Accepted

**Changes made:**

- §6 (Scope), M41-WP1 bullet: reworded to state that WP1 specifies how a
  Definition or Method Version would be admitted and does not itself admit
  one; the production catalog remains empty throughout M41.
- §7 (Explicit Out-of-Scope): added an explicit bullet excluding the act of
  exercising the method-admission mechanism WP1 specifies — no concrete
  production Definition, Method Version, formula, reference method, or
  production method is admitted anywhere in M41; formulas and worked
  examples in specification text or golden vectors are labeled non-admitted
  illustrative examples or normative framework vectors; future Registry/
  Kernel implementation authority does not itself admit a production method
  either.
- §10 (Risks and Mitigations): added a row for the specific risk the review
  named — a golden vector or worked example being read as an implicit
  production admission — with the §7/§12 empty-catalog requirement as
  mitigation.
- §12 (Acceptance Criteria): added an explicit criterion that the admitted
  production Definition/Method catalog remains empty throughout M41.
- §15 (Freeze Boundaries): added a boundary bullet stating that readiness of
  the method-admission mechanism's specification is never itself
  authorization to admit a concrete production method.

**Architectural rationale:** The review's concern was precise: semantic
admission can leak authority even when no code exists, and the "no re-
litigating semantics" language was valid only for the framework contracts,
not for a future concrete method's own formula/owner/dependency/
conformance/production decision. Stating the empty-catalog invariant in four
places (scope, out-of-scope, acceptance criteria, freeze boundaries) rather
than once ensures no single downstream reader of just one section could
read WP1's admission-gate specification as itself an admission act.

---

## RC-5 — Specification-Only Validation Evidence and Closeout Sequencing

**Decision:** Accepted

**Changes made:**

- §13 (Required Evidence): added precise definitions for golden vector
  (a versioned documentation/data fixture: canonical input bytes, expected
  output bytes, the rule under test, and derivation rationale — never
  executable code), canonical serialization (the exact byte-level encoding
  rule a work package must state as a normative deliverable), hash
  stability and round-trip validation (both demonstrated by worked example
  and independent manual recomputation, not by running production code),
  and an explicit statement that non-committed helper scripts used only to
  hand-check a fixture are scratch work with no bearing on approval, while
  any durable, committed validation tooling (fixture-runner, conformance
  harness, reference implementation) is executable-contract work out of
  scope for M41 under §7.
- §13 and §14 (Repository Convention Check): the Graphify refresh
  requirement is now explicitly gated on `M41_EPIC_CLOSEOUT.md` itself being
  independently reviewed and any required correction independently
  confirmed — not merely on the closeout document existing or on WP4 being
  complete. §14 cites `M40_EPIC_CLOSEOUT.md`'s own header
  (`Graphify refresh: NOT_PERFORMED` even though that closeout document was
  itself complete) as the precedent for this distinction.
- §12 (Acceptance Criteria): added a criterion that `M41_EPIC_CLOSEOUT.md`
  is itself independently reviewed and confirmed before Graphify is
  refreshed.
- §15 (Closeout Requirements): added the same independent-review-before-
  refresh sequencing as an explicit closeout requirement, and listed the
  Graphify refresh as the final step, performed only after it.

**Architectural rationale:** The review identified two distinct gaps: what
counts as valid specification-only evidence was undefined precisely enough
to prevent it from silently authorizing an executable module, and the
closeout/Graphify sequence omitted the independent-review-and-confirmation
step that M40's own closeout required. Both are now closed by definition
(what a golden vector, canonical serialization rule, hash-stability proof,
and round-trip proof each precisely are, as data/documentation artifacts)
and by sequencing (Graphify refresh strictly after independent closeout
review and confirmation, matching M40's actual, not merely stated,
practice).

---

## Files Modified

- `docs/implementation/M41_ARCHITECTURE_PROPOSAL.md` — revised in place:
  - Header: `Independent review` field updated to record the
    `APPROVED WITH REQUIRED CORRECTIONS` outcome and link both the
    independent review and this response.
  - §6 (Scope) — WP1 bullet reworded for RC-4, and further updated for the
    RC-2 follow-up to state WP1 SHALL begin with the complete Candidate
    Vocabulary and Ownership Register; WP4 bullet reworded for RC-1.
  - §7 (Explicit Out-of-Scope) — new bullet added for RC-4.
  - §8 (Architectural Approach) — RC-1 correction to new-noun examples;
    "Candidate-vocabulary admission workflow" subsection added for RC-2 and
    revised for the RC-2 follow-up from a four-stage to a five-stage flow
    (Candidate Vocabulary Register → Independent Review → Required
    Corrections → Independent Confirmation → downstream reliance); new
    "Frozen M40 ownership-boundary validation gate" subsection for RC-3.
  - §10 (Risks and Mitigations) — three new rows added for RC-2, RC-4, RC-5;
    the RC-2 row's workflow description updated for the RC-2 follow-up.
  - §11 (Proposed Work Package Structure) — "Independent review" column
    updated for all four work packages for RC-3; M41-WP1 row further updated
    for the RC-2 follow-up to name the upfront register.
  - §12 (Acceptance Criteria) — new criteria added for RC-2, RC-3, RC-4,
    RC-5; the RC-2 criterion revised for the RC-2 follow-up to require
    independent confirmation, not merely independent review, before
    downstream reliance.
  - §13 (Required Evidence) — new "Specification-only validation-evidence
    definitions" subsection added for RC-5; closeout/Graphify bullets
    updated for RC-5.
  - §14 (Repository Convention Check) — new paragraph added for RC-5.
  - §15 (Freeze Boundaries and Closeout Requirements) — new freeze-boundary
    bullet for RC-4; closeout requirements updated for RC-3 and RC-5.
- `docs/implementation/M41_ARCHITECTURE_PROPOSAL_REVIEW_RESPONSE.md` —
  §1 wording corrected ("approved" → "proposed") per the independent
  review's §8 finding, with a note explaining the correction; no
  architectural content changed.
- `docs/implementation/M41_ARCHITECTURE_REQUIRED_CORRECTIONS_RESPONSE.md` —
  created (this document).

No other file was read for modification purposes and no other file was
changed. No Decision Log entry was added. No Graphify refresh was performed.
No implementation code was written. No work package was begun. No new
milestone was created.

---

## Validation Performed

- **Markdown structure:** Heading hierarchy in the revised proposal remains
  sequential (H1, then H2 `## 1.` through `## 15.`, then a final unnumbered
  `## Related Documents`) with no skipped or duplicated levels; all new
  subsections use H2/bold-label structure consistent with the surrounding
  document, introducing no new heading level.
- **Internal links:** The new link to `M41_ARCHITECTURE_INDEPENDENT_REVIEW.md`
  and the new link to `M41_ARCHITECTURE_REQUIRED_CORRECTIONS_RESPONSE.md`
  (this document) both resolve to files that exist on disk. All
  previously-validated link targets are unchanged.
- **Repository consistency:** Confirmed against `GLOSSARY.md` that
  Observation Input Manifest (§"Observation Input Manifest", one of M40's
  eight admissions) and Provenance (§"Provenance", pre-existing vocabulary)
  are both already-effective entries, supporting the RC-1 correction.
  Confirmed against `M40_WP1_Canonical_Market_Measure_Vocabulary_and_
  Ownership_Specification.md` §4.1 and §6.1–6.2 that the five-part
  boundary and witnessed-versus-computed distinction cited in the RC-3
  correction match the actual frozen M40-WP1 text, not a paraphrase.
- **Glossary consistency:** No `GLOSSARY.md` edit was made by this response;
  the proposal's own admission workflow (RC-2) explicitly defers any
  Glossary change to independently reviewed WP1–WP4 admission, consistent
  with the "no Decision Log update, no Graphify refresh" restriction on this
  task.
- **Frozen-vocabulary consistency:** Verified the revised proposal no longer
  contains the string "Calculation Temporal Claim usage" and no longer lists
  Observation Input Manifest or Provenance as example new registrable nouns.
- **Negative-corpus validation:** Re-confirmed the revised proposal's §7 and
  §10 negative-corpus exclusions (generic Analysis domain, composite
  Instrument Analysis authority, portfolio-measurement owner, Investment
  Judgment/recommendation/strategy layer, execution/transaction/trading
  authority, Calculation Temporal Claim, M40's Producing Domain
  specialization) are unchanged and now additionally covered by the §8
  admission workflow's negative-corpus overlap check for any future
  candidate.
- **`git diff --check`:** Run against `M41_ARCHITECTURE_PROPOSAL.md`,
  `M41_ARCHITECTURE_PROPOSAL_REVIEW_RESPONSE.md`, and this document; no
  whitespace errors.
- **RC-2 follow-up scope check:** Confirmed the two governance wording
  corrections required by `M41_ARCHITECTURE_INDEPENDENT_CONFIRMATION.md`
  touch only §6, §8, §10, §11, and §12 of `M41_ARCHITECTURE_PROPOSAL.md` and
  the RC-2 sections of this document; no architectural decision, milestone
  boundary, or work package boundary was changed. Re-ran `git diff --cached
  --check` against `M41_ARCHITECTURE_PROPOSAL.md` and this document after
  the RC-2 follow-up edits; no whitespace errors.
