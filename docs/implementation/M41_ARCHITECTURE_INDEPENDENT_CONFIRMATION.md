# M41 — Independent Confirmation of Required Corrections

**Date:** 2026-07-23

**Document class:** Independent confirmation

**Reviewed proposal:** [M41_ARCHITECTURE_PROPOSAL.md](M41_ARCHITECTURE_PROPOSAL.md)

**Corrections response:** [M41_ARCHITECTURE_REQUIRED_CORRECTIONS_RESPONSE.md](M41_ARCHITECTURE_REQUIRED_CORRECTIONS_RESPONSE.md)

**Governing review:** [M41_ARCHITECTURE_INDEPENDENT_REVIEW.md](M41_ARCHITECTURE_INDEPENDENT_REVIEW.md)

**Review scope:** Initial confirmation of RC-1 through RC-5, followed by
verification limited to the two remaining RC-2 governance requirements

**Implementation authority:** `NONE`

**Decision Log:** Not updated

**Graphify:** Existing output queried for navigation; not refreshed

---

## Executive Summary

The initial confirmation fully confirmed RC-1, RC-3, RC-4, and RC-5 and left
only two RC-2 governance requirements unresolved. This follow-up verification
did not reopen those previously confirmed corrections.

Both remaining RC-2 requirements are now explicit in the operative proposal.
WP1 begins by creating the complete Candidate Vocabulary and Ownership
Register before any Definition or Method Version contract specification
begins. The candidate-admission workflow now requires Candidate Vocabulary
Register → Independent Review → Required Corrections → Independent
Confirmation → downstream reliance, and prohibits downstream reliance until
independent confirmation is complete.

This is a confirmation of the governing review's Required Corrections, not a
new architectural review. No new architectural issue or recommendation is
introduced here.

---

## RC-1 Verification

**Status:** Resolved

The revised proposal preserves the frozen M40 vocabulary:

- Section 6 uses the existing Canonical Temporal Claim qualified by Event
  Type `Calculation` and Producing Domain `Market Intelligence`.
- It reuses Provenance with its frozen Glossary meaning.
- Section 8 records Observation Input Manifest and Provenance as `REUSE`
  dispositions rather than new admissions.
- It carries forward M40's `REJECT` disposition for Calculation Temporal
  Claim and does not introduce a replacement specialization.
- Sections 7, 8, 10, and 12 apply the M39/M40 negative corpus to the proposal
  and future work-package artifacts.

The repository Glossary contains the existing Provenance, Canonical Temporal
Claim, Producing Domain, and Observation Input Manifest entries. The revised
proposal no longer contains the rejected phrase “Calculation Temporal Claim
usage” and does not present Observation Input Manifest or Provenance as new
registrable nouns.

---

## RC-2 Verification

**Status:** Resolved

The two requirements left open by the initial confirmation are satisfied:

1. **Complete register before contract specification.** Section 6 states
   that WP1 `SHALL` begin by creating the complete Candidate Vocabulary and
   Ownership Register before any Definition or Method Version contract
   specification begins. It requires every noun M41 is known to need, its
   proposed exact definition, single owning domain, and disposition request
   to be assembled up front. Section 11 repeats the ordering in the WP1 row:
   the register comes before the Definition, Method Version, and
   Applicability contracts, and the register is reviewed and independently
   confirmed before WP1 contract text relies on an entry.
2. **Independent confirmation before reliance.** Section 8 now specifies the
   required five-stage sequence:

   ```text
   Candidate Vocabulary Register
   → Independent Review
   → Required Corrections
   → Independent Confirmation
   → downstream reliance
   ```

   A disposition and any required corrections are not final until
   independently confirmed. Only a confirmed disposition may synchronize
   the Glossary or be relied upon. The prohibition covers a later work
   package, a later section of the same work package, and fixtures. Section
   12 repeats this rule as an acceptance criterion and states expressly that
   independent review alone is insufficient and that a correction affecting
   a disposition must be independently confirmed before downstream reliance.

The complete RC-2 admission workflow is therefore confirmed.

---

## RC-3 Verification

**Status:** Resolved

Section 8 carries forward the complete five-part M40 ownership boundary:

1. permitted subject;
2. permitted inputs;
3. output meaning;
4. prohibited portfolio, ledger, and life-context inputs; and
5. prohibited judgment semantics.

The gate applies mechanically to every Definition, Method Requirement,
Subject, Manifest entry, and Result coordinate in WP1–WP4. Each input class
must trace to exactly one permitted category: M39 Observation evidence, an
Asset Foundation reference, an explicit invocation parameter, or an explicit
governed calculation dependency. Failure makes the candidate inadmissible.

The witnessed-versus-computed distinction is explicit: provider-reported
statistics remain Market Observations with Event Type `Observation`, while
platform-computed statistics are Calculated Market Measures with Event Type
`Calculation`.

The gate appears in every work-package review requirement in section 11 and
as an independent-review admission blocker in section 12 acceptance
criteria. Section 15 requires whole-corpus revalidation at closeout.

---

## RC-4 Verification

**Status:** Resolved

Sections 6 and 7 distinguish specification of the future method-admission
mechanism from exercising it. M41 does not admit a production Market Measure
Definition, Method Version, formula, reference method, Method, or production
catalog entry.

The proposal requires the production Definition/Method catalog to remain
empty throughout M41. Illustrative formulas, named indicators, worked
calculations, and normative framework vectors are expressly non-admitted.
Future Registry or Kernel implementation authority is also stated not to
admit a production method.

This empty-catalog invariant is present in the scope exclusions, risks,
acceptance criteria, and freeze boundaries. No implementation or production
method authority is created.

---

## RC-5 Verification

**Status:** Resolved

Section 13 completely defines the permitted specification-only evidence:

- golden vectors are versioned documentation/data fixtures containing exact
  canonical input bytes, expected output bytes, the rule under test, and a
  derivation rationale;
- canonical serialization includes field order, numeric representation,
  decimal precision and rounding, timestamp format, Unicode normalization,
  and schema version;
- hash stability is established by recorded manual or independent
  recomputation;
- round-trip validation is a reversible specification-completeness proof;
  and
- durable validation scripts, fixture runners, conformance harnesses, and
  reference implementations remain out of scope and require separate
  authority.

Sections 12 through 15 require `M41_EPIC_CLOSEOUT.md` to receive independent
review and require independent confirmation of any closeout correction before
Graphify is refreshed. Drafting WP4 or the closeout document cannot trigger
the refresh. Decision Log reconciliation remains at the stated
reconciliation/closeout point.

---

## Repository Validation

- The milestone boundary remains the same specification-only WP1–WP4
  sequence that the governing review found sound.
- Proposal authority fields remain `NONE`, including canonical,
  implementation, runtime, production method, provider, persistence, and API
  authority.
- Registry, Resolver, Kernel, integration design, providers, persistence,
  APIs, schedulers, and Experience changes remain excluded.
- The correction response adds gates and evidence definitions without
  expanding the milestone into implementation.
- M29–M40 remain declared frozen. No frozen artifact, constitution, Glossary,
  Decision Log, implementation file, or Graphify output was modified during
  this confirmation.
- Existing Graphify output was queried only for navigation. No Graphify
  update or refresh was run.
- The working tree contains only untracked M41 architecture/review documents;
  no tracked repository change or implementation artifact was reported by
  `git status` before this confirmation document was created.
- WP1 was not begun.

---

## Final Determination

The two previously unresolved RC-2 governance requirements are satisfied.
All Required Corrections from the governing independent review are resolved.

CONFIRMED
