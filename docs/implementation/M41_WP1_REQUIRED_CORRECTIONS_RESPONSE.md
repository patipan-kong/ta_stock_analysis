# M41-WP1 — Candidate Vocabulary and Ownership Register
# Required Corrections Response

**Date:** 2026-07-23

**Document class:** Response to independent review required corrections

**Reviewed document:** [M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md)

**Governing review:** [M41_WP1_INDEPENDENT_REVIEW.md](M41_WP1_INDEPENDENT_REVIEW.md)
— Independent Review Board, outcome `APPROVED WITH REQUIRED CORRECTIONS`

**Independent confirmation:** Not yet performed. This response resolves
stage 3 (Required Corrections) only. A separate Independent Confirmation
document is required before stage 5 (synchronization and downstream
reliance).

**Author role:** Implementation author, responding to an independent review
it did not write. This response resolves the five required corrections
(WP1-IR-1 through WP1-IR-5) without reopening the M41 architecture,
redesigning the milestone, introducing new architectural recommendations,
modifying work-package boundaries, expanding scope, or beginning WP1's own
Definition, Method Version, or Applicability contract specification, Stage 2
(Independent Review, already complete), or WP2.

**Implementation authority:** `NONE`

**Decision Log:** Not updated.

**Graphify:** Not refreshed.

**Milestone boundary:** Unchanged. The M41 Architecture remains `APPROVED`,
independently reviewed, and `CONFIRMED`/`FROZEN`. This response changes only
the reviewed register's own completeness, evidence sequencing, record
completeness, overlap analysis, and confirmation wording.

---

## Executive Summary

The Independent Review Board approved the register's ownership boundaries,
its six `ADMIT` candidates, its two `REUSE` directions, and its
carried-forward `REJECT`, finding no candidate required architectural
redesign. It required five corrections before the register may advance to
Independent Confirmation. All five are resolved in this revision of
`M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md`:

- **WP1-IR-1** — the register's overstated claim that six candidates
  "match exactly" the architecture's illustrative set is replaced by a
  complete noun inventory (new §6.0) that accounts for every noun currently
  known across M41 WP1–WP4, classifying each as an `ADMIT` candidate, a
  `REUSE`, a `REJECT`, ordinary non-canonical contract language, or
  explicitly outside M41. No additional vocabulary is admitted.
- **WP1-IR-2** — candidate-admission evidence is now separated from
  downstream contract-acceptance evidence. Each `ADMIT` candidate (§6.1–§6.6)
  now carries an explicit, current five-part ownership-boundary gate result
  (permitted subject, permitted inputs, output meaning, prohibited
  Ledger/Portfolio/Wealth inputs, prohibited judgment semantics), decided
  from the candidate's own fields. The former "Admission evidence required"
  field is split into "Five-part ownership-boundary gate (current)" and
  "Future contract acceptance evidence" (§5, §6.1–§6.9, §13), and future
  contract evidence is no longer framed as blocking the present disposition.
- **WP1-IR-3** — the two `REUSE` entries (Observation Input Manifest,
  Provenance, §6.7–§6.8) and the carried-forward `REJECT` (Calculation
  Temporal Claim, §6.9) now carry every §5 field, with an explicit
  not-applicable reason where a field does not apply to a reuse or
  rejection. Provenance's ownership is now traced to its exact existing
  canonical authority: Connectivity & Ingestion owns "Provenance at the
  moment of capture" (Platform Architecture §6.4) — cited, not created,
  transferred, or redefined.
- **WP1-IR-4** — the overlap analysis now explicitly compares Market Measure
  Definition against the existing Asset Definition entry (§6.1, §7) and
  Measure Value against the existing Unit Semantics and Valuation Semantics
  entries (§6.6, §7). Measure Subject's proposed exact definition is
  rewritten as a closed, mutually exclusive set of three subject shapes
  (single-Asset, multi-Asset, market-context), removing the ambiguous
  "and/or" hybrid-shape reading (§6.4).
- **WP1-IR-5** — the three conditional-confirmation passages (Document role,
  acceptance criterion, Final Disposition) now state that independent
  confirmation is always required before downstream reliance; required
  corrections remains the only conditional stage.

No correction reopened the M41 architecture, redesigned the milestone,
changed a candidate's proposed meaning or owner, or altered the WP1–WP4
work-package structure. All five are additive completeness, sequencing,
and precision corrections to a register the review already found
directionally sound.

---

## WP1-IR-1 — Candidate Coverage Completeness

**Decision:** Accepted.

**Finding:** Section 6's claim that six candidates "match exactly" the
architecture's illustrative set overstated what M41 Architecture Proposal
§8 actually says ("Terms such as..."), leaving other named M41 concepts
(Applicability, canonical serialization, equivalence vs. conflict
disposition, manifest identity, Result identity, the deterministic
outcome/degraded-state interaction matrix, the reserved Snapshot boundary,
and the M40 planning corpus's Measure Invocation, Dependency Manifest, and
narrower Measure Provenance) unaccounted for.

**Resolution:** A new §6.0 "Complete Noun Inventory" enumerates every known
noun and classifies each:

- **Applicability** is fully covered by Method Requirement (§6.3), which is
  explicitly named as the "Applicability" contract in the M41 proposal §4
  and §6 — not a separate noun.
- **Canonical serialization, equivalence vs. conflict disposition, manifest
  identity** are ordinary non-canonical contract language: rules and fields
  future WP2/WP4 contract text will specify for the already-reused
  Observation Input Manifest and the admitted Measure Value, not new
  governed nouns.
- **Cutoff/window, timezone/calendar** are fully covered by Measurement
  Window (§6.5). **Dependency specifications** are fully covered by Method
  Version's declared dependency versions field (§6.2).
- **Missing-data, decimal/rounding, and adjustment specifications** are
  ordinary non-canonical contract rule language, the last bounded by
  existing Asset Foundation Structural Event vocabulary that WP3 must not
  reinterpret.
- **Unit/currency specification** is reuse of the existing Unit Semantics
  entry (Asset Foundation) — WP3 must cite, not redefine, it.
- **Result identity** is fully covered by the already-admitted Market
  Measure Result composition — WP4 specifies the field, not a new term.
  **The interaction matrix** is ordinary contract language built from two
  already-admitted terms (Computation Outcome, Degraded State).
- **The reserved Snapshot boundary** is a reference to the existing Event
  Type value `Snapshot Creation` — an exclusion rule, not a new noun.
- **Measure Invocation** (M40 planning corpus) is explicitly outside M41: a
  runtime construct M41's specification-only scope admits no authority
  over, deferred to the future Registry/Kernel milestone.
- **Dependency Manifest** (M40 planning corpus) is fully covered by Method
  Version's dependency-declaration field.
- **Measure Provenance**, a narrower lineage concept (M40 planning corpus),
  is not currently required; §6.8 already reserves the path for a future
  specialization to be registered on its own, with its own overlap and V3
  proof, if a future WP4 contract needs it. None is proposed here.

No additional candidate is admitted by this inventory. The six `ADMIT`
candidates, two `REUSE` entries, and one carried-forward `REJECT` remain
the complete set of full-record entries in §6.1–§6.9.

---

## WP1-IR-2 — Candidate-Admission Evidence Separated From Future Contract Evidence; Five-Part Gate Applied Now

**Decision:** Accepted.

**Finding:** Each `ADMIT` candidate's "Admission evidence required" field
deferred proof to future WP1–WP4 contract text and stated independent
review could not approve the candidate until that future text existed —
incompatible with the architecture's closed sequencing, under which WP1's
own contract text cannot begin or rely on a candidate until the register
itself is independently confirmed. The register also did not record a
candidate-level five-part ownership-boundary gate result; it deferred the
aggregate proof to future contract text.

**Resolution:**

- §5's field list now defines two distinct fields in place of the single
  "Admission evidence required" field: **Five-part ownership-boundary gate
  (current)** — the candidate-level pass/fail result decided from the
  candidate's own Purpose, Owner, Permitted/Forbidden inputs, and Proposed
  exact definition fields, recorded now — and **Future contract acceptance
  evidence** — what a future, already-confirmed candidate's owning work
  package must additionally supply, explicitly stated as a downstream
  work-package obligation that does not gate the present disposition.
- Each of the six `ADMIT` candidates (§6.1–§6.6) now carries an explicit
  five-part gate table with a Pass result and reasoning for permitted
  subject, permitted inputs, output meaning, prohibited Ledger/Portfolio/
  Wealth inputs, and prohibited judgment semantics.
- Each candidate's former "Admission evidence required" text is preserved,
  reworded as "Future contract acceptance evidence" and reframed as the
  owning work package's future obligation rather than a precondition for
  this register's own disposition.
- §13 is rewritten to state the two evidence categories explicitly and
  confirm the register's own disposition depends only on the current,
  candidate-level gate result.
- §11's "Next stage" column is corrected from "Independent Review (stage 2)"
  — already complete — to "Independent Confirmation (stage 4)."

---

## WP1-IR-3 — Uniform Term Record Completeness and Provenance Ownership Tracing

**Decision:** Accepted.

**Finding:** Sections 6.7 (Observation Input Manifest), 6.8 (Provenance),
and 6.9 (Calculation Temporal Claim) omitted the Non-owner, Permitted
inputs, Forbidden inputs, and Constitutional constraints fields §5 requires
of every entry. Provenance's owner was recorded as "Pre-existing
foundational ownership (unchanged)" — not an exact owning domain traceable
to governing authority.

**Resolution:**

- §6.7, §6.8, and §6.9 each now carry all §5 fields, with an explicit
  "Not applicable — reuse" or "Not applicable — rejected candidate" reason
  and a brief justification wherever a field does not apply to a reuse or
  rejection, rather than omitting the field.
- Provenance's owner is now traced to Platform Architecture §6.4: "Owns...
  Provenance at the moment of capture," assigned to Connectivity &
  Ingestion. §6.8, §9, and §10 are updated to cite this exact authority. No
  ownership is created, transferred, or redefined — Market Intelligence and
  every other domain remain non-owning carriers of a record's Provenance
  field, consistent with Law 2 (recorded history is immutable; corrections
  are new records with their own provenance).

---

## WP1-IR-4 — Overlap Completeness and Measure Subject Precision

**Decision:** Accepted.

**Finding:** Market Measure Definition's overlap analysis compared only
Definition Version, omitting the existing Asset Definition entry, despite
both being declarative "Definition" contracts owned by different domains.
Measure Value's overlap analysis omitted the existing Unit Semantics and
Valuation Semantics entries, despite its proposed meaning being explicitly
typed and unit-qualified. Measure Subject's proposed exact definition used
"and/or," leaving an unclosed hybrid Asset-plus-market-context subject shape
possible.

**Resolution:**

- §6.1's overlap analysis now explicitly compares Market Measure Definition
  against Asset Definition (`GLOSSARY.md#asset-definition`), establishing
  that an Asset Definition states what an asset class is and supports,
  while a Market Measure Definition states what a family of calculations
  claims to compute — different subjects, different owners, no collision.
  §7's summary table is updated to list both comparisons.
- §6.6's overlap analysis now explicitly compares Measure Value against Unit
  Semantics and Valuation Semantics (both Asset Foundation, both
  declarative axes an Asset Definition states exist without computing a
  value), establishing that Measure Value is the calculated output a Method
  Version produces when it answers the question those axes declare exists —
  reused by reference, never redefined. §7's summary table is updated.
- §6.4's proposed exact definition is rewritten from an "and/or" phrasing to
  three closed, mutually exclusive subject shapes — single-Asset,
  multi-Asset, market-context — with an explicit statement that a hybrid
  Asset-plus-market-context instance is not a permitted shape.

---

## WP1-IR-5 — Unconditional Independent Confirmation Wording

**Decision:** Accepted.

**Finding:** Three passages (the Document role, an acceptance criterion,
and the Final Disposition) used a conditional construction ("if any
correction is required," "if required") that could be read as allowing an
`APPROVED` review with no required corrections to bypass mandatory stage 4.

**Resolution:** All three passages, and the corresponding header fields, now
state that independent confirmation is always required before downstream
reliance, and that required corrections is the only conditional stage. The
header adds an "Independent review" field mirroring the pattern the M41
architecture proposal uses, pointing to
[M41_WP1_INDEPENDENT_REVIEW.md](M41_WP1_INDEPENDENT_REVIEW.md) and this
response, and states plainly that the register is not independently
confirmed until a separate Independent Confirmation document records that
stage 4 has passed. The Workflow stage line is updated from "Stage 1 of 5"
to reflect that stages 1–3 are complete and stage 4 is outstanding.

---

## Repository Validation

- **Scope discipline:** No change was made to the M41 architecture, its
  independent review, its required-corrections response, its independent
  confirmation, `GLOSSARY.md`, the Decision Log, or Graphify. No M41-WP1
  Definition, Method Version, or Applicability contract text was written.
  Stage 2 (Independent Review) was not re-performed by this response. WP2
  was not begun.
- **No new vocabulary admitted:** §6.0's complete noun inventory classifies
  every known noun without proposing new candidacy; the six `ADMIT`
  candidates, two `REUSE` entries, and one carried-forward `REJECT` are
  unchanged from the reviewed register.
- **No ownership transferred:** Provenance's traced ownership (Connectivity
  & Ingestion, capture-time) is cited from existing Platform Architecture
  text, not created or reassigned. No other ownership changed.
- **Markdown validation:** Heading hierarchy in the updated register remains
  sequential (H1, then H2 `## 1.` through `## 17.`, with H3 `### 6.0`–
  `### 6.9` nested only under `## 6.`).
- **Link validation:** Every relative Markdown link added or referenced by
  this response and the updated register resolves to an existing repository
  file, including the new mutual references between this response and
  [M41_WP1_INDEPENDENT_REVIEW.md](M41_WP1_INDEPENDENT_REVIEW.md).
- **Git validation:** `git diff --check` was run against both the updated
  register and this new response file; no whitespace errors were found.
- **Files touched:** Exactly two repository files were created or modified
  by this response —
  `docs/implementation/M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md`
  (updated) and this file (new). No other repository file was modified.

## Final Disposition

All five required corrections (WP1-IR-1 through WP1-IR-5) identified by the
Independent Review are resolved. The M41 Architecture remains `APPROVED`,
independently reviewed, and `CONFIRMED`/`FROZEN`, unchanged by this
response. The updated register has completed stage 1 (Candidate Vocabulary
Register), stage 2 (Independent Review, `APPROVED WITH REQUIRED
CORRECTIONS`), and stage 3 (Required Corrections, this response), and is
submitted for stage 4, Independent Confirmation. No candidate disposition in
the register is canonical, confirmed, or reliable until a separate
Independent Confirmation document records that stage 4 has passed. M41-WP1's
own Definition, Method Version, and Applicability contract specification
does not begin here. M41-WP2 is not begun.
