# M40-WP2 — Independent Constitutional Review

**Review date:** 2026-07-23

**Reviewer role:** Independent constitutional reviewer, fresh session. Not the
author of M40-WP1 or M40-WP2.

**Nature of this document:** An independent determination of whether each
M40-WP2 admission decision (`ADMIT` / `REJECT`) is constitutionally correct.
This is **not** a redesign of M40, **not** a redesign of WP1, and **not** an
implementation proposal.

**Artifact reviewed:** [M40-WP2 — Canonical Market Measure Vocabulary
Admission Review](M40_WP2_Canonical_Market_Measure_Vocabulary_Admission_Review.md).

**Judged against:**

- [Platform Architecture](../architecture/platform_architecture.md), §§5, 6,
  6.1–6.9, 7.1–7.4, 11, 12;
- [Canonical Glossary](../GLOSSARY.md);
- [M34 Decision Register](m34/audit/registers/decision_register.md)
  `M34-D-0004`, `M34-D-0005`, `M34-D-0006`, `M34-D-0010`;
- the frozen [M40-WP1 specification](M40_WP1_Canonical_Market_Measure_Vocabulary_and_Ownership_Specification.md)
  (read directly, not taken on WP2's description of it); and
- [M39-WP4](M39_WP4_market_observation_payload_specification.md) §4.6
  (Semantic Sufficiency), relevant to the Input Sufficiency candidate.

**Verdict:** **APPROVED WITH REQUIRED CORRECTIONS.**

**Scope discipline:** This review is the only file created. It modifies no
WP1 or WP2 artifact, the Canonical Glossary, the Decision Log, or any frozen
milestone, and it triggers no Graphify refresh and no closeout.

---

## 1. Executive Assessment

WP2's ten admission decisions were independently re-derived from the frozen
WP1 term records and the governing repository authority, rather than accepted
on WP2's own narrative. All ten decisions are **substantively correct**:

- The eight `ADMIT` candidates each supply genuinely new, singly-owned
  constitutional meaning that cannot be represented by an existing canonical
  term without loss.
- The two `REJECT` candidates (Calculation Temporal Claim; Producing Domain
  M40 specialization) are correctly rejected — both are complete value
  assignments to already-canonical fields, not new nouns — and rejecting them
  creates no gap, because the admitted composition uses the existing
  Canonical Temporal Claim grammar directly.

One defect survives independent review and is **not** cosmetic: the sole
non-domain owner assigned to Mechanical Boundary Rules — "Repository
Architecture Governance" — is asserted without being tied to any specific
provision of Platform Architecture. Section 6 of that document states that
"nine domains partition the platform," full stop; introducing a tenth,
unenumerated ownership category by label alone, even a governance-only one,
is exactly the kind of unanchored assertion the WP1 predicate itself forbids
("approval inferred from silence, precedent, convenience"). The governance
apparatus WP2 is almost certainly pointing at already exists — Platform
Architecture §11 ("Architecture Governance") and the ARB mechanism visible
throughout the M34 Decision Register — but WP2 never cites it. This is
required correction RC-WP2-1 below. It is narrow and does not disturb any of
the ten admission decisions themselves.

---

## 2. Whole-Set Constitutional Findings

Re-derived independently, not copied from WP2 §3:

| Concern | Governing owner | Independent finding |
| --- | --- | --- |
| Asset identity, definition, classification, capability | Asset Foundation (§6.1) | Referenced only by every admitted term; never mutated |
| Source-reported market fact | Market Intelligence, frozen M39 | Preserved exactly; Event Type `Observation` untouched |
| Platform-computed market fact | Market Intelligence (§6.2) | Distinguished by Event Type `Calculation`; correctly not recast as Observation |
| Ledger/accounting truth | Ledger & Accounting (§6.3) | Excluded from every admitted term's permitted inputs |
| Portfolio-derived meaning | Portfolio Intelligence (§6.5) | Excluded from subject, input, and output of every admitted term |
| Life-level meaning | Wealth Intelligence (§6.8) | Excluded from subject, input, and output — now present as an explicit predicate row in WP1 §7.1 (a prior WP1 gap, since closed) |
| Judgment/action meaning | Decision Intelligence (§6.6) | Excluded; evidence does not become recommendation |
| Correctness/trust meaning | Trust & Evaluation (§6.7) | Excluded; determinism and completion are not correctness |
| Presentation | Experience Platform (§6.9) | May render, never defines |

This matches WP2's own §3.1 table. Independent verification found no
domain this table omits and no domain it wrongly excludes.

The M34 record was checked directly, not assumed from WP2's citations:

- `M34-D-0004` (asset classification vs. evidence): preserved — no admitted
  term converts Market Intelligence evidence into Asset Foundation
  classification authority.
- `M34-D-0005` (temporal/degraded-state grammar): preserved — the admitted
  set reuses Event Type, Producing Domain, timestamp, and Degraded State
  exactly as that decision defines them, and the two rejections exist
  precisely because this decision already supplies their complete meaning.
- `M34-D-0006` (bounded vocabulary admission): preserved — WP2 states
  admission is not effectiveness, and none of the eight admitted terms is
  treated as available for downstream reliance.
- `M34-D-0010` (instrument-analysis decomposition): preserved — Market
  Observation, Investment Judgment, Instrument-Level Risk, Consensus, and
  Evaluation retain their `M34-D-0010` owners; nothing in the admitted set
  re-homes any of them.

---

## 3. Candidate Findings

Each of the ten candidates was checked against its own WP1 term record (not
WP2's summary of it) for necessity, uniqueness, sole ownership, and the six
leakage categories.

| Candidate | WP2 decision | Independent finding |
| --- | --- | --- |
| Market Measure | `ADMIT` | Correct. Functions as the boundary's own name (used throughout WP1 as "the M40 Market Measure boundary"); no existing term names the Observation/Calculation parent category |
| Calculated Market Measure | `ADMIT` | Correct. Necessary to keep a platform-computed fact off the frozen Observation Event type without narrowing Market Observation |
| Computation Outcome | `ADMIT` | Correct. Distinct axis from Degraded State (WP1 §8.2 orthogonality, `UNAVAILABLE` reserved) and from Trust & Evaluation's correctness axis |
| Calculation Temporal Claim | `REJECT` | Correct — see §4 |
| Producing Domain (M40 specialization) | `REJECT` | Correct — see §4 |
| Observation Input Manifest | `ADMIT` | Correct. M39 Observation Identity names one Observation; nothing in frozen M39 names a calculation-owned, ordered, multi-Observation evidence set |
| Market Measure Result | `ADMIT` | Correct, and not a duplicate of Calculated Market Measure: the Result is the complete invocation record (including non-success), while Calculated Market Measure is the computed fact itself, produced only when the outcome permits a value |
| Input Sufficiency | `ADMIT` | Correct — see §5 |
| Deterministic Calculation | `ADMIT` | Correct. Distinct from the Glossary's `Derivation` (ledger-computed state); WP1 §6.9 explicitly forbids ledger, portfolio, and user-state lookups as inputs, which is what keeps this term from colliding with Derivation |
| Mechanical Boundary Rules | `ADMIT`, with a correction | See §7 (Authority Assessment) |

---

## 4. REJECT Decision Assessment

**Calculation Temporal Claim.** Attempted to find genuinely new meaning: none
exists. Every constraint WP1 §6.4 lists (Event Type fixed to `Calculation`,
Producing Domain fixed to `Market Intelligence`, an explicit non-ambient
timestamp, a canonical Degraded State) is a value assignment onto the four
fields the Canonical Glossary already defines for Canonical Temporal Claim,
governed by `M34-D-0005`. No new field, no new axis, no new relationship is
introduced. **Rejection confirmed.**

**Producing Domain (M40 specialization).** Attempted to find genuinely new
meaning: none exists. `Producing Domain` is already canonical; WP1 §6.5 adds
only the fixed value `Market Intelligence` for the calculation event. Fixing
a value is not registering a term. **Rejection confirmed.**

**Semantic-gap check.** Both rejections were checked against WP1's own
required composition diagram (§8.1), which names "Calculation Temporal
Claim" as a sub-node. If WP2 rejected the term without correcting the
diagram's dependency, the admitted vocabulary would silently depend on an
inadmissible term. WP2's own coherence diagram (§5) resolves this correctly:
it replaces the node with "Canonical Temporal Claim" carrying the same four
children (Event Type: Calculation; Producing Domain: Market Intelligence;
authoritative timestamp; Degraded State). This is the right substitution and
closes the gap. **No semantic hole found.**

---

## 5. Input Sufficiency — Independent Verification

This candidate carries the specific history of RC-2 from the WP1 review
cycle (lexical collision with the frozen M39-WP4 term `Semantic
Sufficiency`), so it received separate, direct verification against the
M39-WP4 text rather than WP1's or WP2's description of it.

M39-WP4 §4.6 defines Semantic Sufficiency as: "the condition in which the
canonical fact content preserves enough source-established meaning for an
independent reader to understand the represented claim using governed
platform vocabulary... without consulting provider-private semantics or
inventing missing evidence." Its subject is one Observation Payload at
ingestion time, and its question is whether that payload's content is rich
enough to be understood at all.

WP1 §6.8's Input Sufficiency subject is a calculation invocation, and its
question is whether the exact canonical inputs supplied to that
calculation's declared prerequisites are present — a question that can only
be asked of inputs that have already separately cleared Semantic Sufficiency
as Observations. WP1 §6.8 states this ordering explicitly and states that
Input Sufficiency "does not admit, amend, recompute, or reinterpret Semantic
Sufficiency."

Independent conclusion: the two terms differ in subject (payload vs.
invocation), in temporal position (ingestion-time vs. calculation-time), and
in authority sequence (Semantic Sufficiency is always prior when an
Observation is involved). **`ADMIT` is correct**, and it does not create a
second definition of "sufficiency" for the same question.

---

## 6. ADMIT Decision Assessment (Summary)

For the remaining seven `ADMIT` candidates not given dedicated sections
above (Market Measure, Calculated Market Measure, Computation Outcome,
Observation Input Manifest, Market Measure Result, Deterministic
Calculation), independent review confirms each:

- states a claim no existing Glossary entry states;
- has exactly one named owner, and that owner is consistent with Platform
  Architecture §6.2 (Market Intelligence: valuation, market-state
  understanding, absorbing provider data behind adapters);
- excludes, by explicit forbidden-input list, every adjacent domain's
  vocabulary (Asset Foundation, Ledger & Accounting, Portfolio Intelligence,
  Decision Intelligence, Trust & Evaluation, Wealth Intelligence, Experience
  Platform); and
- creates no authority, implementation, runtime, provider, persistence, or
  API leakage — each WP1 term record's "Future admission requirements"
  clause explicitly defers those questions to later, still-ungranted work.

No additional necessity, uniqueness, or ownership defect was found beyond
the one raised in §7.

---

## 7. Authority Assessment (Mechanical Boundary Rules)

WP1 §6.10 and WP2 §4.10 both assign Mechanical Boundary Rules to
"Repository architecture governance" / "Repository Architecture Governance."
This is not one of the nine domains enumerated in Platform Architecture §6,
and Platform Architecture is explicit that a domain-boundary change is "a
major event" requiring the same amendment process as a constitutional law
change (§10).

Independent reading of Platform Architecture finds a plausible anchor for
this ownership: §11 ("Architecture Governance") establishes a precedence
hierarchy and an amendment discipline that sits above and outside the nine
domains, and the M34 Decision Register shows an active Architecture Review
Board (ARB) exercising exactly this kind of cross-domain, predicate-setting
authority (e.g., `M34-D-0004` through `M34-D-0010`, all decided by `ARB`).
"Repository Architecture Governance" is very likely intended to name this
existing apparatus, not a new business domain.

The defect is that neither WP1 nor WP2 says so. As written, the ownership
label is asserted by itself, which is precisely the failure mode WP1's own
Mechanical Boundary Rules forbid for every other candidate: "approval
inferred from silence, precedent, convenience." An ownership claim for a
constitutional predicate needs the same citation discipline WP1 applies
everywhere else.

This does not change the `ADMIT` decision — Mechanical Boundary Rules is
still necessary and still has a coherent, non-domain, governance-level
owner. It requires the citation to be made explicit. See RC-WP2-1.

---

## 8. Coherence Assessment

Verified directly against WP1 §8.1 and WP2 §5:

- The eight admitted terms plus the existing Canonical Temporal Claim
  (Event Type `Calculation`, Producing Domain `Market Intelligence`) fully
  reconstruct every constraint the two rejected candidates would have
  carried. Nothing rejected removes an invariant; both rejections only
  remove a redundant name.
- The composition diagram is semantic only — it defines no schema, control
  flow, module, or persistence, matching WP1 §8.1's own disclaimer.
- Determinism, temporal grammar, outcome/degraded-state orthogonality
  (§8.2), and terminology reservations (§8.3) all carry through the
  admitted set without a rejected term being a load-bearing dependency
  anywhere.

**Coherence confirmed.** No semantic hole exists after the two rejections.

---

## 9. Risks

| Risk | Severity | Disposition |
| --- | --- | --- |
| "Repository Architecture Governance" ownership unanchored to a specific Platform Architecture provision, inviting a future reader to treat it as a de facto tenth domain | Moderate | Required correction (RC-WP2-1) |
| "Market Measure" (new umbrella) lexically close to Portfolio Intelligence's existing "measure" vocabulary | Low | Already tracked as a non-blocking recommendation from the prior WP1 review; not reopened here |
| Reason-code sets for Input Sufficiency (`INSUFFICIENT`) and Computation Outcome remain open-ended ("future-governed reason") | Low | Correctly deferred to a future work package; not a WP2 admission defect |
| Eight admitted terms are not yet effective vocabulary; a downstream author could mistakenly cite them as canonical before Glossary synchronization | Low | WP2 §1 and §6 already state this explicitly ("Effective now: No" for every row); risk is adequately mitigated in the document as written |

---

## 10. Required Corrections

**RC-WP2-1 — Anchor the Mechanical Boundary Rules ownership citation.**

WP2 (and, by inheritance, any future Glossary entry for Mechanical Boundary
Rules) must state which specific Platform Architecture provision
"Repository Architecture Governance" refers to — most directly, Platform
Architecture §11 ("Architecture Governance") and the ARB mechanism already
exercising this authority in the M34 Decision Register. Without this
citation, the ownership label reads as an ownership category outside the
nine domains enumerated in §6, which Platform Architecture treats as a major
event rather than an ordinary admission. This correction does not change the
`ADMIT` decision for Mechanical Boundary Rules; it requires the existing
decision to be grounded the same way every other admitted term in this
document is grounded.

---

## 11. Recommended Improvements

Non-blocking; do not condition the verdict.

1. When Input Sufficiency and Computation Outcome reach a future work
   package, close their reason-code vocabularies explicitly (WP1 already
   flags these as "future-governed"; this simply notes the item is still
   open).
2. Carry forward the prior WP1 review's non-blocking recommendation to
   disambiguate "Market Measure" from Portfolio Intelligence's "measure"
   vocabulary at the point the Glossary entry is actually drafted.
3. When Glossary synchronization eventually occurs, reproduce WP2's
   "Effective now: No" qualification verbatim in the Glossary entries
   themselves (or in the synchronizing change's description) so the
   ineffectiveness travels with the term, not only with this review.

---

## 12. Final Recommendation

**APPROVED WITH REQUIRED CORRECTIONS.**

All ten WP2 admission decisions are constitutionally correct on independent
re-derivation from the frozen WP1 term records and governing repository
authority: the eight `ADMIT` candidates each supply necessary, unique,
singly-owned meaning free of authority/implementation/runtime/provider/
persistence/API leakage, and the two `REJECT` candidates are correctly
rejected as complete value assignments to already-canonical fields, with no
resulting semantic gap in the admitted set.

One correction is required before this review's approval can be treated as
final: RC-WP2-1, anchoring "Repository Architecture Governance" to Platform
Architecture §11 and the ARB mechanism, so that Mechanical Boundary Rules'
ownership is cited rather than asserted. This is a citation-level correction,
not a re-decision — it does not change any `ADMIT`/`REJECT` outcome, does not
add a domain, and does not reopen WP1.

This review creates no vocabulary admission of its own, no implementation,
runtime, provider, persistence, or API authority, and no amendment to any
frozen milestone or the Decision Log. WP2 remains `COMPLETE`, `NOT YET
APPROVED` until RC-WP2-1 is resolved and, per WP2's own stated gate, until
the required Canonical Glossary synchronization occurs.

---

## 13. Validation

- **Markdown validation:** standard heading levels (`#`/`##`/`###`), tables,
  and fenced code blocks; well-formed.
- **Heading validation:** headings are sequential, non-duplicated, and match
  the required section list (Executive Assessment, Whole-set Constitutional
  Findings, Candidate Findings, REJECT Decision Assessment, ADMIT Decision
  Assessment, Coherence Assessment, Authority Assessment, Risks, Required
  Corrections, Recommended Improvements, Final Recommendation, Validation).
- **Link validation:** all internal links
  (`M40_WP2_Canonical_Market_Measure_Vocabulary_Admission_Review.md`,
  `../architecture/platform_architecture.md`, `../GLOSSARY.md`,
  `m34/audit/registers/decision_register.md`,
  `M40_WP1_Canonical_Market_Measure_Vocabulary_and_Ownership_Specification.md`,
  `M39_WP4_market_observation_payload_specification.md`) were confirmed to
  resolve to existing files.
- **`git diff --check`:** clean.
- **Scope confirmation:** only this review document was created. WP2 and WP1
  are unmodified. No Canonical Glossary modification. No Decision Log entry.
  No Graphify refresh. No closeout. No production code. Nothing committed or
  pushed.
