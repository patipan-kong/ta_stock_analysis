# M40-WP1 — Independent Confirmation of Review Corrections

**Confirmation date:** 2026-07-23

**Reviewer role:** Independent specification reviewer (author of the prior
WP1 review; not the WP1 specification author).

**Nature of this document:** Confirmation that the Required Corrections
issued in the prior WP1 review are resolved. It is **not** a new
specification review and introduces no new review criteria.

**Artifacts assessed:**

- Revised specification — [M40-WP1 — Canonical Market Measure Vocabulary and
  Ownership Specification](M40_WP1_Canonical_Market_Measure_Vocabulary_and_Ownership_Specification.md)
- Author response — [M40-WP1 — Response to Independent Specification
  Review](M40_WP1_REVIEW_RESPONSE.md)

**Judged against:** the prior [M40-WP1 Independent Specification
Review](M40_WP1_INDEPENDENT_REVIEW.md) (verdict `APPROVED WITH REQUIRED
CORRECTIONS`) and the governing authority it cited —
[Platform Architecture](../architecture/platform_architecture.md) §6.2 and
§6.8, and
[M39-WP4](M39_WP4_market_observation_payload_specification.md) §4.6.

**Verdict:** **APPROVED.**

**Scope discipline:** This confirmation is the only file created. It
modifies no specification, no prior review, no response document, no frozen
milestone, and no Decision Log entry, and it triggers no Graphify refresh and
no closeout.

---

## 1. Summary

Both Required Corrections are **RESOLVED**. Each claimed change was verified
directly in the **revised specification text**, not only asserted by the
response document. Neither correction added a domain, changed a term owner,
widened the ten-term set, or created implementation, runtime, provider,
persistence, or API authority.

| Required correction | Prior concern | Disposition |
| --- | --- | --- |
| RC-1 — Complete the §7.1 admission predicate | §7.1's operative pass/fail gate had no row testing Wealth Intelligence leakage, even though §7.2's informal routing matrix and Platform Architecture §6.2/§6.8 implied one was needed | **RESOLVED** |
| RC-2 — Reconcile Input Sufficiency with M39 Semantic Sufficiency | `Input Sufficiency` (§6.8) was left undistinguished from the frozen, Market-Intelligence-owned M39-WP4 term `Semantic Sufficiency` | **RESOLVED** |

---

## 2. RC-1 Assessment — Complete the §7.1 Admission Predicate

**Prior requirement:** §7.1 declares itself the predicate that "a candidate
qualifies for the M40 Market Measure boundary only when every row is
`PASS`." That gate omitted any row testing for Wealth Intelligence meaning
(household, person, goal, net worth, obligation, protection, life-plan),
even though Market Intelligence "Provides... Wealth Intelligence (planning
assumptions)" per Platform Architecture §6.2, and §6.8 owns that vocabulary
exclusively. The exclusion existed only informally in §7.2's routing matrix,
which is not the operative admission gate.

**What the revised specification now does (verified directly):**

- §7.1 now contains an explicit **`Wealth exclusion`** row: "No household,
  person, goal, net worth, obligation, protection, or life-plan meaning
  exists in the subject, inputs, or output claim" with failure classification
  routing to Wealth Intelligence (line 747).
- §7.2's routing matrix already carried the corresponding "Household, person,
  goal, net worth, or life-plan meaning → Wealth Intelligence or other
  existing owner" row (line 761), so the gate and the routing matrix are now
  consistent with each other rather than the gate being silently narrower
  than the matrix.
- §4's Frozen Ownership Baseline table does not add a separate Wealth
  Intelligence row, but this is immaterial: §7.1 is the operative admission
  predicate the prior review was concerned with, and it now closes the gap.

**Assessment:** The predicate is complete. A candidate that carries any
Wealth Intelligence meaning now fails §7.1 directly, rather than surviving
the gate and being caught only by an informal routing table. **RESOLVED.**

---

## 3. RC-2 Assessment — Input Sufficiency vs. M39 Semantic Sufficiency

**Prior requirement:** §6.8's candidate `Input Sufficiency` and M39-WP4's
frozen `Semantic Sufficiency` are both Market-Intelligence-owned and both
answer a "is there enough X" question, but WP1 did not distinguish or
reconcile them anywhere, despite performing exactly this kind of
reconciliation correctly elsewhere (Observation vs. Calculation in §4.1).

**What the revised specification now does (verified directly):**

- §6.8 now contains an explicit reconciliation paragraph (lines 603–614):
  same owner, but different **subject** (Observation Payload preservation
  vs. a specified calculation's declared prerequisites), different
  **purpose** (source-meaning preservation vs. prerequisite satisfaction),
  and an explicit **authority sequence** — "Input Sufficiency does not
  admit, amend, recompute, or reinterpret Semantic Sufficiency," and where
  an Observation is a calculation input, "its M39 admissibility and frozen
  meaning remain prior authority."
- §8.3 ("Terminology reservations") now reserves `Semantic Sufficiency` to
  its frozen M39-WP4 meaning and states `Input Sufficiency` "SHALL NOT
  substitute for, infer, amend, or reinterpret Semantic Sufficiency" (lines
  858–861), giving the distinction the same reservation-level protection
  already given to `Observation`, `Calculation`, and other frozen terms in
  that section.
- This mirrors the reconciliation pattern already used for Observation vs.
  Calculation in §4.1, which the prior review used as the standard WP1 was
  falling short of.

**Assessment:** The lexical collision is now a documented, resolved
distinction rather than a silent gap. Neither term's meaning was weakened;
`Semantic Sufficiency` remains untouched and prior in authority. **RESOLVED.**

---

## 4. Remaining Concerns

None that block confirmation.

- The prior review's three Recommended Improvements (reframing §6.4/§6.5 as
  value-assignment rather than new grammar; clarifying that "stable content
  digest" in §6.6 is identity-only; reducing the `SATISFIED`/`INSUFFICIENT`
  vs. `INSUFFICIENT_INPUT` lexical closeness) were non-blocking and were not
  required corrections. They are not addressed in the revision, and nothing
  in this confirmation requires that they be. They remain available for
  WP2 or a future refinement to consider at its discretion.
- The response document at no point claims vocabulary admission, and the
  revised specification's status header remains
  `COMPLETE_FOR_WP2_CONSTITUTIONAL_ADMISSION_REVIEW` with every authority
  field `NONE`. This confirmation does not change that status.

---

## 5. Final Recommendation

**APPROVED.**

RC-1 and RC-2 are each **RESOLVED**. The author accepted both corrections,
applied each at the correct location (§7.1's operative gate; §6.8 and §8.3's
terminology reservations), and grounded each change in the same governing
authority the prior review cited (Platform Architecture §6.2/§6.8; M39-WP4
§4.6). The response document's claims were verified against the revised
specification text itself, not taken on assertion.

This confirmation closes the corrections issued under the prior verdict
`APPROVED WITH REQUIRED CORRECTIONS`. It does not admit any candidate
vocabulary to the Canonical Glossary, authorize implementation, runtime,
provider, persistence, or API behavior, amend the Decision Log or any frozen
milestone, or create closeout authority. M40-WP1 remains a candidate
specification in `COMPLETE_FOR_WP2_CONSTITUTIONAL_ADMISSION_REVIEW` state;
WP2's own independent constitutional admission review is the next
authority-bearing step.

---

## 6. Validation

- **Markdown validation:** document uses standard heading levels (`#`/`##`),
  tables, and fenced code — well-formed.
- **Heading validation:** headings are sequential and non-duplicated within
  the document.
- **Link validation:** all internal links (`M40_WP1_Canonical_Market_Measure_Vocabulary_and_Ownership_Specification.md`,
  `M40_WP1_REVIEW_RESPONSE.md`, `M40_WP1_INDEPENDENT_REVIEW.md`,
  `../architecture/platform_architecture.md`,
  `M39_WP4_market_observation_payload_specification.md`) were confirmed to
  resolve to existing files.
- **`git diff --check`:** clean for the revised specification and the
  response document.
- **Scope confirmation:** only this confirmation file was created by this
  task. The revised WP1 specification and the review response are
  pre-existing untracked files, not modified by this task. No change was
  made to the Decision Log, the Canonical Glossary, any frozen M39 or prior
  M40 artifact, or any production code. No Graphify refresh was run. No
  closeout was created. Nothing was committed or pushed.
