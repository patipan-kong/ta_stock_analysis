# M41-WP2 — Required Corrections Response

**Response role:** Implementation Author

**Reviewed artifact:** [M41-WP2 Independent Architecture Review](M41_WP2_ARCHITECTURE_INDEPENDENT_REVIEW.md) (`APPROVED WITH REQUIRED CORRECTIONS`, 2026-07-23)

**Corrected artifact:** [M41-WP2 Architecture Proposal](M41_WP2_ARCHITECTURE_PROPOSAL.md)

**Architecture authority:** Frozen (cited, not modified)

**M41-WP1 authority:** Frozen (cited, not modified)

**Implementation authority:** `NONE`

**Runtime authority:** `NONE`

**Provider authority:** `NONE`

**Persistence authority:** `NONE`

**API authority:** `NONE`

**Response date:** 2026-07-23

---

## Scope of this response

This response resolves the seven findings recorded in the Independent
Architecture Review. All corrections are local to
`M41_WP2_ARCHITECTURE_PROPOSAL.md`. No other repository file was modified.
Neither WP2-Stage A nor WP2-Stage B has begun. This response does not open a
new Independent Review and does not perform Architecture Confirmation.

---

## M41-WP2-AR-1 — Frozen permitted-input field is assigned to the wrong contract

**Resolution:** Fixed.

Every statement that had attributed the four-category permitted-input
declaration, or a "declared input categories" / "permitted-input-category
closure," to Method Requirement was rewritten to attribute it to **Market
Measure Definition** (Stage 2 §5.4), narrowed for a given calculation by
**Method Requirement**'s own closed fields — a declaring Method Version
reference, a prerequisite category (subject shape, dependency presence, or
Observation category availability), and an evaluation rule (§7.4/§7.4a) — per
§10's fixed field-to-contract relationships.

Sections corrected: §0 (inheritance table), §1 (Objectives), §2 (Included
scope, Manifest binding rule bullet), §5 (Component 5, Manifest Binding
Rule), §6 (Lateral boundary bullet), §9 (Risks table, new row naming this
exact failure mode explicitly).

No field was added, renamed, or reinterpreted on either WP1 contract.

---

## M41-WP2-AR-2 — Proposed binding rule widens Observation Input Manifest

**Resolution:** Fixed.

Every Observation Input Manifest description was constrained to exact frozen
M39 Observation evidence membership only. Asset Foundation reference data,
explicit invocation parameters, and explicit governed calculation
dependencies are now described exclusively as **separately owned binding
coordinates**, verified by WP2's overall binding rule but never represented
as manifest entries.

Sections corrected: §0 (inheritance table), §2 (Included scope, two
bullets), §5 (Components 5 and 6), §6 (Upstream boundary — M39 bullet), §9
(Risks table row, combined with AR-1's row).

---

## M41-WP2-AR-3 — Definition Version is placed inside Measure Subject without authority

**Resolution:** Fixed.

The claim that Measure Subject references both Asset identity and Definition
Version was removed. §2 (Included scope) and §6 (Upstream boundary — Asset
Foundation) now state explicitly that all three Measure Subject shapes stay
exactly within register §6.4's closure and that **no shape carries a
Definition Version field**. §5 (Component 1) states the same constraint.
Where the governing architecture requires an exact Asset Definition Version
reference for a calculation, §6 now describes it as its own independently
owned binding coordinate, bound alongside the Subject but never a
constituent of it. §9's risk table gained a row naming this exact failure
mode (adding a field register §6.4 does not contain) and its mitigation.

---

## M41-WP2-AR-4 — Stage 1 vocabulary classifications are reopened

**Resolution:** Fixed.

§4 (Canonical terminology) now lists manifest identity, equivalence/conflict
disposition, and canonical serialization as **confirmed ordinary
non-canonical contract language (register §6.0)** — reused as ordinary
language, not re-candidated. Only Subject Reference, Subject Ordering Key,
and Manifest Entry remain as candidates, each explicitly marked "candidate
under evaluation" with the obligation that Stage A must first show the term
is a governed noun rather than an ordinary field label before requesting a
disposition. §11 (Stage A purpose) states the same constraint directly and
names the three ordinary-language terms that must not be re-proposed. No
term's ownership is predetermined or pre-admitted anywhere in the document.

---

## M41-WP2-AR-5 — Measure Subject serialization and acceptance evidence are incomplete

**Resolution:** Fixed.

- **Objectives (§1):** now names Measure Subject canonical serialization
  explicitly, alongside record structure, identity, and ordering.
- **Included scope (§2):** now lists Measure Subject canonical serialization
  as an included item, and expands the golden-vector list to cover a
  shape-(b) ordering-permutation pair, an M39-Identity-Equivalent
  representation case, an identity-distinct conflict case, a forbidden
  provider-shaped-input rejection case, and byte-level round-trip
  reconstruction for both Subject and Manifest encodings.
- **Component decomposition (§5):** gained a new Component 4, "Subject
  Canonical Serialization," symmetric to the Manifest's own canonical
  serialization component.
- **Validation strategy (§8):** now requires canonical serialization proofs
  for both Subject and Manifest, round-trip validation for both, a
  provider-leak rejection check, and an exact-evidence-reproduction check.
- **Stage B deliverable (§11):** now names Subject serialization explicitly
  in its purpose statement and references the complete validation matrix.

All fixtures remain documentation/data only and non-executable, consistent
with WP2's specification-only posture.

---

## M41-WP2-AR-6 — Conflict handling crosses into WP4 and remains architecturally undecided

**Resolution:** Fixed.

Every "equivalence/conflict disposition" statement was reframed as "evidence
equivalence vs. conflict determination," scoped to M39 Observation evidence
candidates only, and its outcome was closed to the **existing frozen
`Computation Outcome` values** (`INSUFFICIENT_INPUT` for a conflict) with no
possibility of a new outcome value stated anywhere. §1, §2, §5, §6, and §9
all now state this closure. §2's Explicit exclusions gained an explicit
`Computation Outcome` definition, Result composition, and degraded-state
interaction matrix exclusion, with a direct statement that WP2 cites but
never adds, removes, or redefines a `Computation Outcome` value. §6's
downstream boundary bullet was updated to list `Computation Outcome`
definition among the things WP2 must not pre-specify.

---

## M41-WP2-AR-7 — Stage A governance and artifact decomposition are incomplete

**Resolution:** Fixed.

- **Document header:** replaced the "Advisory Draft" framing with a formal
  submitted-proposal header carrying explicit `Architecture authority`,
  `M41-WP1 authority`, and the five operational authority fields (all
  `NONE`), plus a Review history line citing the Independent Architecture
  Review and this response.
- **Stage A deliverables (§11):** now require, per candidate: exact proposed
  definition, single owner, disposition request, complete overlap analysis,
  V1/V2/V3 analysis, M34/M39/M40 compatibility analysis, and the
  candidate-level five-part ownership-boundary gate.
- **Stage A completion criteria (§11):** now require every candidate's
  disposition to receive its own **unconditional** Independent Confirmation
  — whether or not a correction was required — followed by Decision
  Log/Implementation Index synchronization, before any downstream reliance.
- **Distinct review artifacts (§11):** Stage A and Stage B now each name
  their own review, correction-response, and confirmation artifact filenames
  (`M41_WP2_STAGE_A_*` vs. `M41_WP2_STAGE_B_*`), replacing the prior single
  generic WP2-wide artifact set.
- **Stage B completion criteria (§11):** now states Independent Confirmation
  must return `CONFIRMED` with no open findings **unconditionally**.

---

## Corrections Summary Table

| Finding | Severity | Resolution |
|---|---|---|
| M41-WP2-AR-1 | Major | Fixed — exact WP1 field ownership restored throughout |
| M41-WP2-AR-2 | Major | Fixed — manifest membership limited to exact M39 Observation evidence |
| M41-WP2-AR-3 | Major | Fixed — Definition Version removed from Measure Subject; retained as separate coordinate |
| M41-WP2-AR-4 | Major | Fixed — Stage 1 ordinary-language classifications preserved; only genuine new nouns remain candidates |
| M41-WP2-AR-5 | Major | Fixed — Measure Subject serialization and full acceptance-evidence matrix added |
| M41-WP2-AR-6 | Major | Fixed — conflict handling closed to existing `Computation Outcome` values; WP4 boundary restored |
| M41-WP2-AR-7 | Moderate | Fixed — complete Stage A governance workflow, distinct artifacts, formal proposal header |

---

## Repository Validation

- Only two repository files were modified or created by this response:
  `docs/implementation/M41_WP2_ARCHITECTURE_PROPOSAL.md` (updated) and
  `docs/implementation/M41_WP2_REQUIRED_CORRECTIONS_RESPONSE.md` (created).
- No M41 Architecture, WP1 artifact, `GLOSSARY.md`, Decision Log,
  Implementation Index, or Graphify output was modified.
- Neither WP2-Stage A nor WP2-Stage B has begun; no candidate vocabulary was
  admitted and no contract specification was drafted.
- No implementation, runtime, provider, persistence, or API behavior was
  introduced.
- Markdown structure (code-fence balance, heading sequence) and
  `git diff --check` were validated clean for both files.

---

## Final Status

All seven required corrections are resolved. This response does not
constitute a new Independent Review or an Architecture Confirmation.
