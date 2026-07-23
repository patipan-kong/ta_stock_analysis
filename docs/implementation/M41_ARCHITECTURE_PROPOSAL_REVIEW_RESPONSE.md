# M41 Architecture Proposal — Self-Review Response

**Date:** 2026-07-23

**Document class:** Self-review response to the M41 architecture proposal

**Reviewed document:** [M41_ARCHITECTURE_PROPOSAL.md](M41_ARCHITECTURE_PROPOSAL.md)

**Reviewer role:** Same author, performing a self-review pass against five
stated observations. Not an independent constitutional review.

**Scope of this response:** Wording, naming, and structural consistency of
the M41 architecture proposal only. No architectural decision recorded in
the proposal was reopened; no milestone was redesigned; no scope was
expanded; no implementation was begun.

**Implementation authority:** `NONE`

**Decision Log:** Not updated (see Observation 3).

**Graphify:** Not refreshed (see Observation 3).

---

## 1. Summary of Review

Five observations were reviewed against the M41 architecture proposal and
against actual repository convention in the M39 and M40 corpora (not
against invented convention). Two observations (naming, WP structure)
identified a genuine inconsistency with established repository pattern and
were corrected. One observation (future-milestone wording) found the
proposal was already largely compliant and applied a smaller harmonization
pass. One observation (scope boundary) confirmed the existing boundary was
already correctly placed and made a small trim rather than a structural
change. One observation (overall consistency) was addressed as a
byproduct of the other four rather than as a separate pass.

No observation required reopening §2's core reasoning (why M41 adopts the
deferred M40-plan WP3–WP9 content) or changing which work is in versus out
of scope. The milestone boundary proposed in the original proposal is
unchanged.

**Post-independent-review note:** the Independent Architecture Review
Board's assessment (`M41_ARCHITECTURE_INDEPENDENT_REVIEW.md` §8) correctly
flagged that "approved in the original proposal" overstated this document's
authority — the proposal's own headers record `Approval state: NOT_APPROVED`,
and an author self-review cannot grant approval. The wording above has been
corrected to "proposed." This does not change the milestone boundary itself,
which the independent review separately confirmed is architecturally sound
(see `M41_ARCHITECTURE_REQUIRED_CORRECTIONS_RESPONSE.md`).

---

## 2. Observation 1 — Milestone Naming

**Finding:** The original title, "M41 — Canonical Market Measure Contract
Specification," dropped "Asset" relative to the established naming pattern.
Both M39 (`Canonical Asset Market Observation`) and M40 (`Canonical Asset
Market Measure Foundation`) use the form `Canonical Asset Market <domain
noun> <optional stage descriptor>`. The original M41 title broke that
pattern at the one word that signals the milestone is still inside the
Asset Foundation lineage, not a new top-level concern.

**Decision:** `Accepted`

**Technical rationale:** Consistency of milestone titles is not cosmetic in
this repository — `platform_architecture.md` §12 (V1: one term, one
meaning, one home) treats naming precision as a constitutional concern, and
the Implementation Index (`INDEX.md`) uses milestone titles as navigation
keys. Restoring "Asset" removes a title that would have read as a
namespace shift when none occurred. The word "Foundation" in M40's title
was not reused, because M41 is explicitly *not* a foundation-laying
milestone in M40's sense (vocabulary admission) — it is the contract stage
that follows a foundation. "Contract Specification" was kept as the
accurate stage descriptor.

**New title:** `M41 — Canonical Asset Market Measure Contract Specification`

---

## 3. Observation 2 — Future Milestone References

**Finding:** The proposal, as delivered, contained no literal reference to
"M42" or any other specific future milestone number — that phrasing
appeared only in this reviewer's own chat-turn summary outside the
document, not in the file. Within the file, forward references already
used non-numeric phrasing ("a subsequent milestone," "the next eligible
milestone number"), but the phrasing was not fully consistent across
sections, and one instance ("next eligible milestone number") risked
implying a specific successor was already anticipated by number.

**Decision:** `Partially Accepted`

**Technical rationale:** No factual correction was needed — the document
never named a future milestone number. What was strengthened is
consistency: every forward reference now uses one of two forms — "a
future, separately governed/chartered/authorized milestone" (§2, §7) or
"the next milestone, identified as eligible for separately governed
definition, without authorizing it" (§12, §13, §15) — the latter matching
the exact phrase already established in `M40_EPIC_CLOSEOUT.md` §9, which
this proposal quotes directly in §1. No explicit milestone number is
asserted anywhere in the document body; the one place a number appears
("M41" in the current milestone's own name, and the quoted "M41" inside the
§1 citation from `M40_EPIC_CLOSEOUT.md`) is the proposal's own identity and
a verbatim quotation, both of which repository convention requires to stay
literal.

**Files modified:** §2, §7, §12, §13, §15 of `M41_ARCHITECTURE_PROPOSAL.md`
(wording only).

---

## 4. Observation 3 — Work Package Structure (Epic Closeout)

**Finding:** The original proposal listed "M41-WP5 — Epic Closeout and
Repository Reconciliation" as a fifth numbered work package. Repository
history does not support this. Both frozen precedents place Epic Closeout
**outside** the numbered work-package sequence, as a standalone,
milestone-level document produced after the last work package:

- M39 closed with WP1–WP6, followed by a separate `M39_EPIC_CLOSEOUT.md`
  (not a "WP7").
- M40 closed with WP1–WP5, followed by a separate `M40_EPIC_CLOSEOUT.md`
  (not a "WP6").

Neither closeout document is numbered as, titled as, or filed as a work
package. Numbering Epic Closeout as "M41-WP5" would have introduced a
structural inconsistency the two prior milestones do not exhibit.

**Decision:** `Accepted`

**Technical rationale:** This is not a matter of preference; it is applying
the existing, already-frozen repository convention rather than inventing a
new one, per the task's explicit instruction to use existing convention as
the deciding authority. Correcting this also has a real governance
consequence: framing closeout as a fifth work package would have implied it
carries the same "independently reviewed before the next work package
opens" gating logic as WP1–WP4, when in both precedents closeout is instead
a *reconciliation* step across an already-completed corpus — a different
kind of activity with a different validation shape (whole-corpus check,
not new-content review).

**Files modified:** §6 (Scope), §11 (Proposed Work Package Structure), §13
(Required Evidence), §14 (Repository Convention Check), §15 (Freeze
Boundaries and Closeout Requirements) of `M41_ARCHITECTURE_PROPOSAL.md`.
The numbered work-package list is now WP1–WP4 only; Epic Closeout is
described as the milestone-level artifact that follows WP4, matching the
M39/M40 pattern explicitly, with citations to both precedents.

**Consequence for §13 (Required Evidence):** Because Decision Log entries
and Graphify refreshes are also closeout-time activities in both
precedents (verified in the original proposal's §14 and re-confirmed here),
this correction is consistent with, not in tension with, the prior finding
that neither action belongs at the proposal stage. No Decision Log entry
was added and no Graphify refresh was performed as part of this review, per
the task's explicit instruction.

---

## 5. Observation 4 — Scope Boundaries

**Finding:** The proposal's placement of the Registry, Applicability
Resolver, Pure Computation Kernel, and Read-Only Integration Design outside
M41 (deferred to a future milestone) was reviewed against §2's own stated
reasoning: WP3–WP6 are specification-only (no code), while WP7–WP8 are the
first code the Market Measure vocabulary cycle would produce. This is the
same category boundary M40 itself drew between vocabulary (WP1–WP2) and
everything after it — the repository's own precedent for where a
specification milestone should stop. The boundary was confirmed correct
and was not moved.

**Decision:** `Partially Accepted`

**Technical rationale:** The boundary itself required no change — moving it
in either direction (pulling WP7–WP8 into M41, or trimming further to
exclude WP5–WP6) would either reintroduce the spec/code bundling risk M40's
history warns against, or would leave the Result/Provenance model
unspecified, which §5 (Capability Gap) shows is necessary before any Kernel
work is even meaningful to scope. What was accepted was the second half of
the observation: the proposal repeated the WP7–WP9 exclusion rationale in
three separate places (§2, §7, §15) with overlapping detail. §15's freeze-
boundary bullet was trimmed to point back to §7 rather than restating the
excluded work item-by-item, since §7 is already the authoritative
out-of-scope list and repeating it verbatim in §15 added length without
adding a distinct constraint.

**Files modified:** §15 (Freeze Boundaries) of
`M41_ARCHITECTURE_PROPOSAL.md` — condensed to reference §7 instead of
restating it.

---

## 6. Observation 5 — Overall Consistency

**Finding:** Addressed as a byproduct of Observations 1–4 rather than as an
independent pass, per the instruction not to make changes beyond what the
other observations justify. The specific repetitions removed were: the
WP7–WP9 exclusion detail duplicated between §7 and §15 (Observation 4), and
inconsistent forward-milestone phrasing across §2/§7/§12/§13/§15
(Observation 2). No wording was changed outside the scope of Observations
1–4, and no additional rewrite was performed.

**Decision:** `Accepted` (as a byproduct; no independent changes made)

**Technical rationale:** The task instruction was to preserve every
architectural decision unless there was a clear constitutional reason to
revise it. None of the four prior observations produced a reason to revise
any decision — only to correct naming, restore convention-consistent
structure, and tighten wording. Treating "overall consistency" as a fifth,
independent editorial pass risked exactly the kind of scope expansion the
task explicitly prohibited, so it was scoped to what the other four
observations already required.

---

## 7. Files Modified

- `docs/implementation/M41_ARCHITECTURE_PROPOSAL.md` — revised in place:
  - H1 title corrected (Observation 1).
  - §2 — forward-reference wording harmonized; no change to the reasoning
    or conclusion (Observation 2).
  - §6 (Scope) — WP5 removed from the numbered list; closeout note added,
    pointing to §11 (Observation 3).
  - §7 (Explicit Out-of-Scope) — WP7/WP8 exclusion consolidated into one
    bullet; wording harmonized (Observations 2, 4).
  - §11 (Proposed Work Package Structure) — table reduced to WP1–WP4;
    explanatory paragraph added citing the M39/M40 Epic Closeout precedent
    (Observation 3).
  - §12 (Acceptance Criteria) — "WP1–WP5" corrected to reflect M40's own
    history accurately; forward-reference wording harmonized (Observations
    2, 3).
  - §13 (Required Evidence) — "M41-WP5" reference corrected to describe
    Epic Closeout as milestone-level; forward-reference wording harmonized
    (Observations 2, 3).
  - §14 (Repository Convention Check) — "M41-WP5" reference corrected
    (Observation 3).
  - §15 (Freeze Boundaries and Closeout Requirements) — "M41-WP5" reference
    corrected; WP7/WP8 detail trimmed to reference §7 instead of repeating
    it; forward-reference wording harmonized (Observations 2, 3, 4).
- `docs/implementation/M41_ARCHITECTURE_PROPOSAL_REVIEW_RESPONSE.md` —
  created (this document).

No other file was read for modification purposes and no other file was
changed. No Decision Log entry was added. No Graphify refresh was
performed. No implementation code was written. No work package was begun.

---

## 8. Validation Performed

- **Markdown structure:** Heading hierarchy in the revised proposal is
  sequential (H1, then H2 `## 1.` through `## 15.`, then a final unnumbered
  `## Related Documents`) with no skipped or duplicated levels.
- **Internal links:** Every relative link target in the revised proposal
  (`M40_Canonical_Asset_Market_Measure_Foundation_Plan.md`,
  `M40_EPIC_CLOSEOUT.md`, `M39_EPIC_CLOSEOUT.md`,
  `M40_INDEPENDENT_CONFIRMATION.md`, `M40_WP5_INDEPENDENT_CONFIRMATION.md`,
  `../architecture/platform_architecture.md`,
  `../architecture/asset_foundation.md`,
  `../architecture/asset_definitions.md`,
  `../architecture/UNIVERSAL_ASSET_ARCHITECTURE.md`,
  `../architecture/MARKET_DATA_PLATFORM.md`,
  `../architecture/PROVIDER_INTERFACE.md`, `../architecture/ROADMAP.md`,
  `../GLOSSARY.md`, `m34/audit/registers/decision_register.md`) was
  confirmed to resolve to an existing file on disk.
- **Repository consistency:** Confirmed against actual file listings and
  document headers that M39 closed with WP1–WP6 plus a standalone
  `M39_EPIC_CLOSEOUT.md`, and M40 closed with WP1–WP5 plus a standalone
  `M40_EPIC_CLOSEOUT.md`, neither treating closeout as a numbered work
  package — the basis for Observation 3's correction. Confirmed no stray
  `M41-WP5` references remain in the revised proposal (only historical
  references to M40's actual WP5 and the original M40-plan WP5, both of
  which are accurate as written).
- **`git diff --check`:** Run against
  `docs/implementation/M41_ARCHITECTURE_PROPOSAL.md`; exit code 0, no
  whitespace errors.
