# M41-WP3 Stage B — Independent Review

**Document role:** Independent Review Board (fresh session)

**Review class:** Specification-only constitutional and architectural review

**Milestone:** M41 — Governed Market Measure Semantics

**Work package:** M41-WP3 — Temporal, Unit, Adjustment, and Arithmetic
Semantics

**Internal stage:** Stage B — Deterministic Semantics Contract Specification

**Primary review target:**
[`M41_WP3_STAGE_B_TEMPORAL_UNIT_ADJUSTMENT_ARITHMETIC_CONTRACT_SPECIFICATION.md`](M41_WP3_STAGE_B_TEMPORAL_UNIT_ADJUSTMENT_ARITHMETIC_CONTRACT_SPECIFICATION.md)

**Reference authorities (treated as immutable):** M41 Architecture; M41-WP1
(Candidate Register, Stage 2 Contract, closeout); M41-WP2 (Architecture,
Stage A, Stage B Contract); approved M41-WP3 Architecture; approved M41-WP3
Stage A Register; frozen M34/M39/M40 corpora and the Canonical Glossary.

**Implementation authority:** `NONE` (unchanged by this review)

**Date:** 2026-07-24

**Determination:** **APPROVED WITH REQUIRED CORRECTIONS**

---

## 1. Executive Summary

Stage B is a substantially complete, high-quality normative specification
that closes the determinism surface allocated to M41-WP3 by the approved WP3
Architecture and the confirmed Stage A Register. It specifies the concrete
Measurement Window record, canonical encoding, temporal selection and
inclusive cutoff, timezone/calendar/DST semantics, missing-data/density/
interpolation rules, unit and currency compatibility, adjustment and basis
transformation, exact rational arithmetic and canonical numeric bytes, the
governed-dependency closure through the existing Method Version list, one
non-commutative cross-dimension processing order, a total failure
classification onto the frozen Computation Outcome values, a field-level
five-part ownership gate, and thirty normative golden vectors `GV-01`
through `GV-30`.

Independent verification confirms:

- **No frozen authority is modified.** Stage B cites WP1, WP2, WP3
  Architecture, Stage A, M34/M39/M40, and the Glossary by reference only.
- **No new governed vocabulary and no Glossary change.** All semantic-choice
  tokens are ordinary lowercase rule values consistent with the Stage A
  ordinary-language classification; the sole WP3-governed noun remains the
  reused Measurement Window.
- **Ownership and downstream deferral are preserved.** WP4 Result
  composition, Measure Value, Provenance, Canonical Temporal Claim, reason
  codes, and the degraded-state matrix remain deferred.
- **Implementation, runtime, provider, persistence, API, production-method,
  and executable-validation authority remain `NONE`.**
- **The golden-vector arithmetic is independently reproducible.** Every
  numeric vector recomputes to the stated canonical bytes, and the fixture
  Manifest bytes decode consistently against the frozen WP2 §4.7/§5.8
  serialization.

One **internal contradiction** was found that must be corrected before
unconditional confirmation: the explanatory note in §3.1 asserts that
`count:"I:0"` is *invalid* for an `elapsed` window, which directly
contradicts the §3.1 field table, the §3.2 permitted-forms table, the §3.3
rejection rules, and normative vector `GV-01`. This is a localized
normative-text defect, not an architectural or scope defect, and is
correctable without redesign.

Accordingly the determination is **APPROVED WITH REQUIRED CORRECTIONS**
(one required correction, enumerated in §6).

---

## 2. Scope of Review

This review verifies Stage B against, and only against, the frozen and
approved authorities. It does not redesign the M41 Architecture, WP1, WP2,
the approved WP3 Architecture, or Stage A, and it introduces no
implementation guidance.

The review covered the entire Stage B artifact: §§0–2 (authority, encoding,
numeric forms), §3 (Measurement Window), §4 (temporal selection/cutoff/
ordering), §5 (timezone/calendar/DST), §6 (missing data/density/
interpolation), §7 (units/currency), §8 (adjustment/basis), §9 (arithmetic),
§10 (dependency closure), §11 (processing order), §12 (failure
classification), §13 (field-level gate), §14 (compatibility), §§15–17
(golden vectors and coverage), and §§18–19 (determinism requirements,
acceptance).

**Filename note (non-defect):** the review request names the target with an
additional token (`..._ADJUSTMENT_AND_ARITHMETIC_...`). The actual repository
artifact is `..._ADJUSTMENT_ARITHMETIC_...`, which matches verbatim the
deliverable name specified by the approved WP3 Architecture §9 ("WP3 Stage
B") and Stage A. The reviewed file is therefore correctly named; the request
token is a transcription variance only.

---

## 3. Verification Findings

### 3.1 Scope fidelity to the approved WP3 Architecture (Objective 1)

Stage B's normative surface is exactly Components A–I of the approved WP3
Architecture §4:

| Component (Architecture §4 / Stage A §4) | Stage B section(s) | Verdict |
|---|---|---|
| A — Measurement Window record and identity | §§2–3 | Complete |
| B — cutoff, temporal selection, ordering | §4 | Complete |
| C — timezone, calendar, alignment, DST | §5 | Complete |
| D — missing data and density | §6 | Complete |
| E — units and currency | §7 | Complete |
| F — adjustment and basis | §8 | Complete |
| G — decimal/rational/arithmetic | §§2, 9 | Complete |
| H — governed dependency closure | §10 | Complete |
| I — cross-dimension order and classification | §§11–12 | Complete |

No surface outside the A–I allocation is specified. WP3 adds no formula,
method, registry, resolver, kernel, provider, persistence, API, or UI (§1.3,
confirmed throughout).

### 3.2 Preservation of frozen authorities (Objectives 2, 30–32)

- **M39 (Objective 30):** §§4.1–4.4, §6.4, and §14.2 preserve Observation
  identity, temporal precision, unit, currency, scale, basis, absence, and
  uncertainty. Derived interpolation/normalization/adjustment values are
  explicitly working material that receives no Observation Identity and MUST
  NOT enter the Manifest (§6.4, §8.2). Numeric equality never collapses
  identity-distinct evidence (§14.2). **Verified.**
- **M40 (Objective 31):** the four-category input closure, byte-identical
  determinism, explicit cutoff/window, prohibition of ambient defaults,
  explicit units, prohibition of implicit FX and inferred adjustment, exact
  dependency versioning, and the four-value Computation Outcome closure are
  all preserved (§14.3, §§9–12). **Verified.**
- **WP1/WP2 identity and bytes (Objective 32):** §14.4 adds no WP1 field or
  identity coordinate; §14.5 adds no WP2 field and makes semantic ordering a
  calculation-only view that never alters Manifest membership, order, or
  bytes (§4.4). The fixture Manifest bytes in §15 decode consistently
  against WP2 §4.7 (`MSB1` + `0x01` shape tag + `lp(asset_id)` + `lp(role)`)
  and §5.8 (`OIM1` + `lp(subject)` + `u32(entry_count)` + entries), using a
  u32 length prefix. **Verified.**

### 3.3 No new governed vocabulary; no Glossary change (Objectives 3–4)

All Stage B semantic-choice tokens (`elapsed`, `civil`, `session`,
`observation_count`, `inclusive`, `exclusive`, `contained`, `overlap`,
`reject`, `omit`, `exact_density`, `interpolate`, `earlier_offset`,
`later_offset`, `raw`, `source_adjusted`, `calculation_normalized`, the
rounding modes, etc.) are §2.4 lowercase ordinary rule values. They match
the Stage A §3.2 ordinary-language classification and establish no
independent identity, owner, or lifecycle. The schema-version tags
(`m41-wp3.measurement-window/1`, `OIM1`, `MSB1`) are mechanical
contract-version tags, consistent with Stage A §3.2. No `ADMIT`/`RENAME`/
`MERGE` disposition and no Glossary edit appears. **Verified — Objectives 3
and 4 satisfied.**

### 3.4 Ownership boundaries and authority ceilings (Objectives 5–12)

- The §13 field-level five-part gate covers every rule group and records
  "Pass" for each, with Ledger/Portfolio/Workspace/Wealth and
  judgment/evaluation semantics excluded per row. This satisfies the
  Architecture §5.2 requirement for a field-by-field gate that Stage A §4.1
  explicitly deferred to Stage B. **Verified (Objective 5).**
- The header and §§1.3, 15 preserve Implementation, Runtime, Provider,
  Persistence, API, Production-method, and executable-validation authority
  as `NONE`. Golden vectors are documentary data fixtures with an explicit
  per-vector non-production statement. **Verified (Objectives 6–12).**

### 3.5 Semantic completeness of each dimension (Objectives 13–28)

- **Measurement Window (13):** §3 fully closes fields, order, cardinality,
  boundary-object grammar, timezone/calendar reference objects, four
  permitted forms (§3.2), byte identity and immutability (§3.3), and the
  rejection set. **Complete.**
- **Temporal / cutoff (14–15):** §4 closes role temporal-meaning
  declaration, inclusive/exclusive lower edge, always-inclusive cutoff,
  interval `contained`/`overlap`, qualified/approximate time, and the stable
  §4.4 tri-key ordering (role bytes → normalized temporal coordinate → M39
  Observation Identity). **Complete.**
- **Timezone / calendar / DST (16–18):** §5 closes fixed-offset vs
  named-zone resolution, the exact-calendar mandate, DST gap (`reject`
  only) and fold (`earlier_offset`/`later_offset`/`reject`), leap-day
  `reject`/`last_day`, and alignment origin. **Complete.**
- **Missing data / density / interpolation (19–21):** §6 closes the closed
  treatment set, expected-position generation, gap/duplicate definitions,
  density as an exact reduced rational, and §6.4 exact linear interpolation
  as working material. Boundary interpolation and undeclared fills are
  prohibited. **Complete.**
- **Unit / currency (22–23):** §7 closes canonical unit expressions, equality
  vs normalization, dimensionless/percentage/rate/compound handling, the
  currency-compatibility triad, and the prohibition of implicit FX.
  **Complete.**
- **Adjustment (24):** §8 closes the three bases, the seven-part
  allowed-transformation declaration, and exact factor arithmetic; no event
  inference is permitted. **Complete.**
- **Arithmetic (25):** §§2.2–2.3, 9 close the three exact numeric domains,
  quantization modes, single-quantization discipline, exceptional-value
  handling, and negative-zero closure. **Complete.**
- **Dependency closure (26):** §10 makes the existing Method Version
  dependency-version list the sole inventory and forbids `latest`,
  environment discovery, and network lookup. **Complete.**
- **Processing order (27):** §11 fixes a mandatory 12-step non-commutative
  order; `GV-29` proves order-sensitivity. **Complete.**
- **Failure classification (28):** §12 gives a total mapping onto the frozen
  `INSUFFICIENT_INPUT` / `DEPENDENCY_UNRESOLVED` / `FAILED` / `SUCCEEDED`
  values with a precedence rule tied to §11. The value names match the
  Canonical Glossary (`SUCCEEDED`, GLOSSARY.md line 1204) and M40 exactly.
  **Complete.**

### 3.6 WP4 deferral (Objective 29)

§§1.3, 12, and 14.6 confine WP3's handoff to the exact Measurement Window
bytes/identity, exact semantic/dependency versions, canonical arithmetic
bytes on success, or one frozen outcome classification. No Result envelope,
Measure Value, Provenance, Canonical Temporal Claim, reason code, or
partial-value structure is defined. **Verified.**

### 3.7 Golden-vector coverage and internal consistency (Objectives 33–34)

- **Coverage (33):** the §17 coverage table maps `GV-01`–`GV-30` onto
  Components A–I; each of the 30 architecture-required rows (Architecture
  §7.1 / Stage A §5) appears exactly once. **Complete.**
- **Numeric reproducibility (34):** independent recomputation confirms the
  stated canonical bytes, including `GV-03` (elapsed 86,400 s vs civil
  82,800 s across the 23-hour civil day), `GV-08` (`last_day` →
  2025-02-28/2026-02-28), `GV-14` (`R:4/3` → `D:133E-2`), `GV-22`
  (half-even ties → `D:1E0`, `D:102E-2`), `GV-23` (exact `R:2/3` →
  `D:67E-2`), `GV-21` (×`R:1/2` before boundary → `D:5E1`/`D:6E1`),
  `GV-28` (version sensitivity → `D:1E0`/`D:1E1`), `GV-29` (ordered pipeline
  → `D:225E-2`), and `GV-30` (`R:1/3` scale-six → `D:333333E-6`, UTF-8
  `44 3a 33 33 33 33 33 33 45 2d 36`). The `GV-01`/`GV-30` window-fixture
  Manifest bytes decode to the declared single-asset subject and entry.
  **Reproduced.**

  One consistency defect exists at the boundary between §3.1 prose and
  `GV-01`; it is recorded as Required Correction RC-1 (§6) and cross-listed
  under Objectives 34–36.

### 3.8 Absence of leakage (Objectives 37–38)

No implementation authority, runtime behavior, or governance surface outside
the WP3 allocation was found to have leaked into the specification. The
negative corpus (Architecture §7.2, Stage A §7.5) — Calculation Temporal
Claim, Producing Domain specialization, Dependency Manifest, implicit FX /
base currency, default timezone/calendar, weekday/252-session assumptions,
provider priority, and executable validators — is absent. **Verified.**

---

## 4. Repository Validation

Working-tree inspection (`git status`) confirms Stage B is additive only.
The following frozen or shared artifacts are **not** modified:

| Artifact | Status |
|---|---|
| M41 Architecture (proposal/confirmation chain) | Unmodified |
| M41-WP1 (register, Stage 2 contract, closeout) | Unmodified |
| M41-WP2 (architecture, Stage A, Stage B contract) | Unmodified |
| Approved M41-WP3 Architecture | Unmodified |
| Approved M41-WP3 Stage A Register | Unmodified |
| `docs/GLOSSARY.md` | Unmodified |
| `docs/engineering/DECISION_LOG.md` | Unmodified |
| Implementation INDEX | Unmodified |
| Graphify outputs (`graphify-out/`) | Unmodified |
| Source, tests, fixtures, schemas, configuration | Unmodified |

The only new/added files are Stage B and its sibling WP3 register/review
artifacts under `docs/implementation/`. **Repository validation passes.**

---

## 5. Advisory Observations

These are non-blocking and require no action for approval.

- **AO-1 (illustrative-example clarity).** The §3.1 example uses
  `manifest_identity":"hex:4f494d31"` — four bytes (`OIM1` tag only) — which
  is not a complete WP2 §5.8 Manifest and would independently fail §3.3
  decoding. When RC-1 is applied, stating the correct reason the example is
  non-conforming (its truncated `manifest_identity`, not its `count`) would
  make the example unambiguously self-consistent. This is folded into RC-1
  below and noted here only to record the underlying cause.

- **AO-2 (request/deliverable filename variance).** As noted in §2, the
  review request's target token differs from the actual (architecture-
  specified) deliverable name. No change to Stage B is warranted; recording
  for traceability only.

---

## 6. Required Corrections

Exactly one required correction. It is a localized normative-text
contradiction, not a redesign, and does not alter any rule, field, byte,
vector, or classification.

### RC-1 — §3.1 explanatory note contradicts the `count` contract and `GV-01`

**Location:** §3.1, the sentence immediately after the example record:
"The example shows field order only; `count:"I:0"` is invalid for `elapsed`
under §3.3."

**Defect:** This statement is false and internally contradictory. Per the
§3.1 field table (`count` = "positive canonical integer for
`observation_count`; otherwise exact token `I:0`"), the §3.2 permitted-forms
table (only `observation_count` carries a positive count), and the §3.3
rejection rule ("`count` violates §3.1 or §3.2"), an `elapsed` window MUST
carry exactly `count:"I:0"`. Therefore `count:"I:0"` is the **required**
value for `elapsed`, not an invalid one. The contradiction is confirmed by
normative vector **`GV-01`**, whose `elapsed` window sets `count:"I:0"` and
is expected to be valid and to select `["O1","O2"]`; if the §3.1 note were
correct, `GV-01`'s window would be non-conforming and map to
`INSUFFICIENT_INPUT`, contradicting its own expected bytes.

**Required change (author's discretion on exact wording; no rule change):**
Replace the note so it no longer asserts that `count:"I:0"` is invalid for
`elapsed`. The example may be retained as an illustration of field order
only; if the specification wishes to state that the example record is
non-conforming, it must attribute the non-conformance to the correct cause —
the `manifest_identity` value `hex:4f494d31` is a truncated four-byte tag,
not a complete WP2 §5.8 Manifest, and fails §3.3 Manifest-identity decoding —
while affirming that `count:"I:0"` is the correct value for an `elapsed`
window.

**Scope guard:** This correction touches only explanatory prose in §3.1. It
must not modify the §3.1 field table, the §3.2 permitted forms, the §3.3
rejection set, or any golden vector, all of which are already correct and
mutually consistent.

---

## 7. Final Determination

**APPROVED WITH REQUIRED CORRECTIONS.**

Stage B correctly and completely specifies the M41-WP3 determinism surface
within its allocated authority; preserves every frozen M34/M39/M40/WP1/WP2
authority and the approved WP3 Architecture and Stage A Register; introduces
no governed vocabulary and no Glossary change; preserves all ownership
boundaries and the WP4 deferral; keeps implementation, runtime, provider,
persistence, API, production-method, and executable-validation authority at
`NONE`; and supplies thirty internally reproducible golden vectors that
cover every required obligation.

Approval is conditioned on resolution of the single required correction
**RC-1** (§6). RC-1 is a localized normative-text contradiction correctable
without redesign and without touching any rule, field, canonical byte,
vector, or classification. Advisory observations AO-1 and AO-2 require no
action.

Upon submission of `M41_WP3_STAGE_B_REQUIRED_CORRECTIONS_RESPONSE.md`
resolving RC-1, Stage B is eligible for unconditional Independent
Confirmation. No further semantic obligation is outstanding, and — subject to
RC-1 — no ambient semantic default remains.

This review records an independent determination only. It does not itself
confirm Stage B, does not begin implementation, and does not alter the
frozen status of any upstream authority.

---

**Review status:** COMPLETE — one required correction issued.
