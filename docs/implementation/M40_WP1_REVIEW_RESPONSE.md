# M40-WP1 — Response to Independent Specification Review

**Date:** 2026-07-23

**Document class:** Work-package specification review response

**Status:** `CORRECTIONS_RECONCILED_PENDING_INDEPENDENT_CONFIRMATION`

**WP1 approval state:** `NOT_YET_CONFIRMED`

**Canonical vocabulary admission:** `NONE`

**Implementation authority:** `NONE`

**Runtime authority:** `NONE`

**Production method authority:** `NONE`

**Provider authority:** `NONE`

**Persistence authority:** `NONE`

**API and public-exposure authority:** `NONE`

**Decision Log status:** `NOT_SUBMITTED`

**Closeout:** `NONE`

**Responding author role:** M40 implementation architect and original WP1
specification author

**Specification:** [M40-WP1 — Canonical Market Measure Vocabulary and
Ownership Specification](M40_WP1_Canonical_Market_Measure_Vocabulary_and_Ownership_Specification.md)

**Independent review:** [M40-WP1 — Independent Specification
Review](M40_WP1_INDEPENDENT_REVIEW.md)

**Normative status:** This response records how the M40-WP1 candidate
specification was reconciled with repository-governing independent review
feedback. It does not confirm approval, admit vocabulary, authorize
implementation or runtime use, amend frozen M39 meaning, or create provider,
persistence, API, public-exposure, production-method, or closeout authority.

---

## 1. Response Summary

Both required corrections are accepted. The approved architecture, ten-term
set, ownership direction, work-package scope, and authority boundaries remain
unchanged.

| Required correction | Disposition | Prior specification authority | Result |
| --- | --- | --- | --- |
| RC-1 — Complete the §7.1 admission predicate | `ACCEPTED` | Wealth routing existed in §7.2, but the operative predicate was incomplete | Explicit Wealth Intelligence exclusion added to §7.1 |
| RC-2 — Reconcile Input Sufficiency with M39 Semantic Sufficiency | `ACCEPTED WITH CLARIFICATION` | Input Sufficiency was bounded from evaluation but not distinguished from the frozen M39 term | Same owner, different subject, purpose, and authority sequence stated in §6.8 and reserved in §8.3 |

No correction redesigns WP1, adds a domain or term, expands milestone scope,
or creates implementation authority.

---

## 2. RC-1 — Complete the §7.1 Admission Predicate

**Disposition:** `ACCEPTED`

### Reviewer concern

Section 7.1 excluded Portfolio Intelligence, Decision Intelligence, Trust &
Evaluation, and authority meaning, but did not explicitly test for Wealth
Intelligence leakage. Section 7.2 routed household, person, goal, net-worth,
and life-plan meaning correctly, yet that routing did not make the operative
all-rows-must-pass admission predicate complete.

### Constitutional analysis

The concern is valid. The prior specification contained sufficient routing
authority to show the intended ownership boundary, but insufficient predicate
authority to enforce that boundary mechanically.

Platform Architecture section 6.8 assigns household, goal, obligation,
protection, liquidity, and life-plan meaning to Wealth Intelligence. Section
7.1 declares itself the pass/fail gate for M40 eligibility. Therefore the
Wealth Intelligence exclusion must be an explicit predicate row, not merely a
later routing outcome. Adding that row reconciles the gate with existing
section 7.2 without changing either domain's ownership.

### Repository authority cited

- [Platform Architecture §6.8 — Wealth
  Intelligence](../architecture/platform_architecture.md#68-wealth-intelligence)
- [Platform Architecture §6.2 — Market
  Intelligence](../architecture/platform_architecture.md#62-market-intelligence)
- [M40-WP1 independent review §4 — Boundary
  Findings](M40_WP1_INDEPENDENT_REVIEW.md#4-boundary-findings)

### Proposal change

Section 7.1 now contains a `Wealth exclusion` row. A candidate passes that row
only when no household, person, goal, net-worth, obligation, protection, or
life-plan meaning exists in its subject, inputs, or output claim. Failure
routes the candidate to Wealth Intelligence.

### Rationale

The change makes the admission predicate consistent with the already-approved
fail-closed routing direction. It introduces no new domain, moves no ownership,
and does not widen the Market Measure boundary.

---

## 3. RC-2 — Input Sufficiency and M39 Semantic Sufficiency

**Disposition:** `ACCEPTED WITH CLARIFICATION`

### Reviewer concern

Section 6.8 defined candidate `Input Sufficiency` without reconciling it with
M39-WP4's frozen `Semantic Sufficiency`. Because both concepts are owned by
Market Intelligence and both concern a form of sufficiency, future reviewers
or implementers could conflate the Observation-payload gate with the
calculation-input gate and silently reinterpret M39 vocabulary.

### Constitutional analysis

The concern is valid, but the concepts do not overlap:

- **Owner:** both concepts are semantically owned by Market Intelligence.
  Different ownership is not required because their subjects and claims are
  distinct.
- **Subject:** frozen Semantic Sufficiency concerns one Observation Payload
  and the source-established meaning it preserves. Candidate Input Sufficiency
  concerns the exact canonical inputs supplied to one specified calculation.
- **Semantic purpose:** Semantic Sufficiency determines whether represented
  source evidence preserves enough governed meaning to be independently
  understood. Input Sufficiency determines whether supplied canonical inputs
  satisfy the calculation's explicit prerequisites.
- **Authority sequence:** M39 admissibility and preserved Observation meaning
  are prior authority when an Observation is referenced as input. The later
  Input Sufficiency classification cannot admit, amend, recompute, or
  reinterpret that frozen meaning.

Consequently, neither sufficiency result establishes the other. An
Observation may satisfy its frozen payload-preservation obligation without
satisfying every prerequisite of a particular calculation. Conversely, a
calculation cannot use Input Sufficiency to cure or bypass an M39
admissibility failure.

### Repository authority cited

- [M39-WP4 §4.6 — Semantic
  Sufficiency](M39_WP4_market_observation_payload_specification.md#46-semantic-sufficiency)
- [M39-WP4 §6.1 — Minimum semantic
  obligations](M39_WP4_market_observation_payload_specification.md#61-minimum-semantic-obligations)
- [M40-WP1 independent review §2 — Vocabulary
  Findings](M40_WP1_INDEPENDENT_REVIEW.md#2-vocabulary-findings)
- [M40-WP1 §4.1 — M39 preservation
  rule](M40_WP1_Canonical_Market_Measure_Vocabulary_and_Ownership_Specification.md#41-m39-preservation-rule)

### Proposal change

Section 6.8 now states the same-owner, different-subject, different-purpose,
and prior-authority relationship explicitly. Section 8.3 now reserves
`Semantic Sufficiency` to its frozen M39-WP4 meaning and prohibits `Input
Sufficiency` from substituting for, inferring, amending, or reinterpreting it.

### Rationale

The clarification prevents a lexical collision from becoming a constitutional
collision while preserving both the frozen M39 meaning and the intended M40
calculation-prerequisite concept. It changes no term owner, classification,
state set, or work-package scope.

---

## 4. Scope and Authority Confirmation

This reconciliation:

- revises only RC-1 and RC-2;
- preserves the approved M40-WP1 architecture and ten-term structure;
- introduces no new domain or vocabulary candidate;
- weakens no M40 or M39 boundary;
- expands no milestone or work-package scope;
- leaves the independent review and every frozen milestone untouched;
- creates no implementation, runtime, provider, persistence, API,
  public-exposure, production-method, authorization, or production-code
  authority;
- modifies neither the Decision Log nor Canonical Glossary;
- triggers no Graphify refresh; and
- creates no closeout.

M40-WP1 remains a candidate specification with no canonical vocabulary
admission. Independent confirmation remains required before the review
corrections may be treated as closed.
