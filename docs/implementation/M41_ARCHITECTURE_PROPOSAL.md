# M41 — Canonical Asset Market Measure Contract Specification

**Date:** 2026-07-23

**Document class:** Proposed architecture and milestone plan

**Status:** `PROPOSED_FOR_ARCHITECTURAL_REVIEW`

**Approval state:** `NOT_APPROVED`

**Canonical authority:** `NONE`

**Implementation authority:** `NONE`

**Runtime authority:** `NONE`

**Production method authority:** `NONE`

**Provider authority:** `NONE`

**Persistence authority:** `NONE`

**API and public-exposure authority:** `NONE`

**Decision Log status:** `NOT_SUBMITTED`

**Supersedes:** `NONE`

**Closeout:** `NONE`

**Independent review:** [APPROVED WITH REQUIRED CORRECTIONS](M41_ARCHITECTURE_INDEPENDENT_REVIEW.md) — the five required corrections (RC-1 through RC-5) are resolved in this revision; see [M41_ARCHITECTURE_REQUIRED_CORRECTIONS_RESPONSE.md](M41_ARCHITECTURE_REQUIRED_CORRECTIONS_RESPONSE.md)

**Normative status:** This document is a non-canonical proposal. Its use of
`MUST`, `MUST NOT`, `SHALL`, `SHALL NOT`, `MAY`, and `SHOULD` describes
requirements proposed for review. Those terms acquire no repository authority
unless and until this plan is independently reviewed and explicitly approved.

**Governing architecture and frozen authority (not amended by this
proposal):**

- [Platform Architecture](../architecture/platform_architecture.md);
- [Canonical Glossary](../GLOSSARY.md);
- [Asset Foundation Constitution](../architecture/asset_foundation.md);
- [Asset Definitions Constitution](../architecture/asset_definitions.md);
- [Universal Asset Architecture](../architecture/UNIVERSAL_ASSET_ARCHITECTURE.md);
- [M34 Decision Register](m34/audit/registers/decision_register.md), especially
  `M34-D-0004`, `M34-D-0005`, and `M34-D-0010`;
- the complete frozen M39 corpus (Market Observation: source, classification,
  payload, relationship, identity — [M39 Epic Closeout](M39_EPIC_CLOSEOUT.md));
  and
- the complete frozen M40 corpus (Canonical Asset Market Measure vocabulary —
  [M40 Epic Closeout](M40_EPIC_CLOSEOUT.md), independently confirmed via
  [M40 Independent Confirmation](M40_INDEPENDENT_CONFIRMATION.md) and
  [M40-WP5 Independent Confirmation](M40_WP5_INDEPENDENT_CONFIRMATION.md)).

This proposal creates no authority to implement any work package. Approval of
the architecture would establish the milestone boundary only. Each
implementation-bearing work package remains subject to its own explicit
admission and review gate.

---

## 1. Repository Status

As of this proposal:

- M40 — Canonical Asset Market Measure Foundation is `COMPLETE_AND_FROZEN`.
  Its constitutional vocabulary cycle is complete: eight Canonical Glossary
  terms admitted (Market Measure, Calculated Market Measure, Computation
  Outcome, Observation Input Manifest, Market Measure Result, Input
  Sufficiency, Deterministic Calculation, Mechanical Boundary Rules), two
  specializations rejected (Calculation Temporal Claim, and a M40-specific
  specialization of Producing Domain).
- All M40 independent reviews returned `APPROVED`; RC-1 is resolved; the
  epic closeout and independent confirmation are both complete.
- Graphify has been refreshed against the post-M40 repository state.
- The Decision Log records the M40 constitutional vocabulary cycle
  completion.
- The main branch is clean. No implementation, runtime, provider,
  persistence, or API authority exists anywhere in the M39/M40 corpus.
- Per [M40 Epic Closeout §9](M40_EPIC_CLOSEOUT.md#9-next-milestone-readiness):
  *"The repository is constitutionally ready for the next milestone. M41 is
  the next milestone number eligible for separately governed definition, but
  [M40's] closeout does not define, authorize, or begin M41."* This document
  is that separate definition.

M29–M40 are treated as canonical and are not redesigned, reinterpreted, or
reopened by anything in this proposal.

---

## 2. Reasoning: Why This Is the Correct M41 Boundary

Before proposing scope, the repository itself suggests a narrower and more
precise M41 boundary than "pick the next roadmap capability."

M40's own architecture plan
([M40_Canonical_Asset_Market_Measure_Foundation_Plan.md §5](M40_Canonical_Asset_Market_Measure_Foundation_Plan.md))
already laid out a nine-work-package sequence for the full Market Measure
foundation: WP1–WP2 (vocabulary and admission), WP3 (Definition, Method
Version, and Applicability contracts), WP4 (Subject and Observation Input
Manifest), WP5 (Temporal, unit, adjustment, and arithmetic semantics), WP6
(Result, State, and Provenance model), WP7 (Frozen Registry and Applicability
Resolver), WP8 (Pure Computation Kernel), and WP9 (Read-Only Integration and
Adoption Design).

What was actually executed and closed as M40 is narrower than that plan: the
completed M40-WP1 through WP5 delivered vocabulary definition and ownership,
admission review, Canonical Glossary synchronization, Decision Log
reconciliation, and independent confirmation — the naming layer only. The
epic closeout is explicit that this is a boundary, not an oversight:

> *"Any future implementation of calculations, methods, registries, kernels,
> providers, persistence, APIs, or consumers requires separately governed
> authority."*

The original plan's WP3–WP9 content — Definition/Method contracts, Input
Manifest, determinism semantics, Result model, Registry, Kernel, and
Integration Design — was written and carried through the same architecture
review that produced M40, but was never itself separately chartered,
admitted, or approved as executable work. It is not stale: it is
already-reviewed material sitting one governance step short of being
actionable.

Two consequences follow:

1. **M41 should adopt that deferred content as its scope, under fresh
   milestone authority — not re-derive a new scope from the roadmap.**
   Treating the existing WP3–WP9 material as a starting draft, re-chartered
   under M41's own authority, is the evolutionary continuation; inventing an
   unrelated M41 scope while this material sits unused would be scope
   drift away from what the repository has already reasoned through.
2. **The deferred material itself splits into two different kinds of work,
   and they should not share a milestone.** WP3–WP6 (Definition/Method
   contracts, Input Manifest, determinism semantics, Result model) are pure
   specification — no code, same governance shape M40 used throughout.
   WP7–WP8 (Frozen Registry, Pure Computation Kernel) are the first
   **code** this entire vocabulary cycle would produce. M40's own history is
   the caution here: vocabulary alone required five work packages and
   multiple independent constitutional reviews to close correctly. Bundling
   spec-only work with first-code work in one milestone reintroduces exactly
   the scope pressure M40 was deliberately narrowed to avoid.

M41 is therefore scoped as the **specification-only continuation**: the
original WP3–WP6 content, re-chartered under M41's own authority. The
original WP7–WP9 content (Registry, Kernel, Read-Only Integration Design)
remains explicitly deferred: it requires a future milestone that is
separately chartered, separately reviewed, and separately authorized once
M41's contracts are independently approved. This proposal does not name or
number that milestone.

---

## 3. Position of M41 in the Roadmap

Per [ROADMAP.md](../architecture/ROADMAP.md), Phase 3 — Platform Evolution,
Market Intelligence track: "Multiple Price Providers," "Market Calendar," and
"Historical Services" are all unstarted. M41 implements none of them. It sits
one layer beneath all three, inside the Market Measure vocabulary cycle that
M39 (Observation) and M40 (Measure naming) opened, and produces the contract
specifications a later milestone needs before any provider, calendar, or
historical-service work can consume a Calculated Market Measure
deterministically.

M41 is a **specification milestone**, in the same sense M39 was: it commits
no runtime, endpoint, provider, storage, or public-exposure authority.

---

## 4. Objectives

- Specify, under independent review, the **Definition, Method Version, and
  Applicability contracts** (the M40 plan's original WP3 content).
- Specify the **Subject and Observation Input Manifest** binding a
  calculation to exact Assets, Definition Versions, and M39 Observation
  evidence (original WP4).
- Close every determinism choice — cutoff/window, timezone/calendar,
  missing-data handling, unit/currency, adjustment, decimal/rounding, and
  dependency semantics — before any executable method exists (original WP5).
- Specify the **immutable Result, Computation Outcome, and Provenance
  model**, including the deterministic outcome/degraded-state interaction
  matrix (original WP6).
- Produce a fully reviewed, fixture-referenced specification corpus that a
  later, separately authorized milestone can implement without re-litigating
  semantics.

---

## 5. Capability Gap Being Addressed

M40 gave the platform words for a Calculated Market Measure. It gave no
contract for what a Definition is, how a Method Version is admitted or
fingerprinted, what evidence a calculation may consume, what constitutes a
conflicting or equivalent input, how temporal/unit/rounding ambiguity is
resolved, or what an immutable Result and its provenance must contain.
Without these contracts, no deterministic calculation could be written that
is not ad hoc, and no later Registry or Kernel milestone would have a
specification to implement against. M41 closes the gap between "the platform
can name this" and "the platform knows exactly what must be true before code
may exist."

---

## 6. Scope

- **M41-WP1 — Definition, Method Version, and Applicability Contracts**: WP1
  SHALL begin by creating the complete Candidate Vocabulary and Ownership
  Register (§8) before any Definition or Method Version contract
  specification begins — every noun M41 is known to require, with its
  proposed exact definition, single owning domain, and disposition request,
  assembled up front rather than discovered work package by work package.
  Definition and immutable Method Version contracts, requirement vocabulary,
  and the **specification** of a future method-admission gate and registry
  invariants follow from that register. WP1 specifies how a Definition or
  Method Version would be admitted; it does not itself admit one. The
  production Definition/Method catalog remains empty throughout M41 (§7,
  §12).
- **M41-WP2 — Subject and Observation Input Manifest**: contracts binding a
  calculation to exact Assets, Definition Versions, and M39 Observation
  evidence; canonical serialization; equivalence vs. conflict disposition;
  manifest identity.
- **M41-WP3 — Temporal, Unit, Adjustment, and Arithmetic Semantics**:
  cutoff/window, timezone/calendar, missing-data, unit/currency, adjustment,
  decimal/rounding, and dependency specifications, each closed against
  golden vectors.
- **M41-WP4 — Result, State, and Provenance Model**: Measure Value,
  Computation Outcome, Result identity, the deterministic
  outcome/degraded-state interaction matrix, and the reserved Snapshot
  boundary, all expressed using the existing Canonical Temporal Claim
  (Event Type `Calculation`, Producing Domain `Market Intelligence`) and the
  existing Provenance term — both reused with their frozen Glossary meaning,
  not redefined.

Every work package is specification only: contracts, requirement vocabulary,
serialization rules, and validation vectors — no executable module.

Epic Closeout follows WP4 as a milestone-level artifact, not a numbered work
package — see §11.

---

## 7. Explicit Out-of-Scope

- Any executable code (`contracts.py`, `subjects.py`, `input_manifest.py`,
  `temporal.py`, `units.py`, `decimal_math.py`, `results.py`,
  `provenance.py`, or equivalents) — these remain named for future planning
  only, exactly as they were in the M40 plan.
- The **Frozen Registry and Applicability Resolver** (original WP7) and the
  **Pure Computation Kernel** (original WP8) — the first code this
  vocabulary cycle would produce; deferred to a future, separately
  chartered milestone (§2).
- **Read-Only Integration and Adoption Design** (original WP9) — deferred
  until a Kernel exists to integrate against.
- Any provider, persistence, API, scheduler, or Experience-layer change.
- Any reinterpretation of M39 Observation semantics or the eight M40
  Canonical Glossary admissions.
- Any reintroduction of the M40 negative corpus: a generic Analysis domain,
  a composite Instrument Analysis authority, a portfolio-measurement owner,
  an Investment Judgment/recommendation/strategy layer, or an
  execution/transaction/trading authority.
- Any Asset Registry, Portfolio Engine, optimizer, or execution-intent
  behavior change.
- **Exercising the method-admission mechanism WP1 specifies.** M41
  specifies *how* a future Definition or Method Version would be admitted;
  it does not exercise that mechanism. No WP1–WP4 artifact admits a
  concrete production Market Measure Definition, Method Version, formula,
  reference method, or production method, and the admitted production
  catalog remains empty throughout M41. Formulas, named indicators, and
  worked calculations appearing in specification text or golden vectors
  (§13) are explicitly non-admitted illustrative examples or normative
  framework vectors, never production admissions. Future Registry or Kernel
  implementation authority (deferred above) does not itself admit any
  production method either — admission remains a separate, future,
  explicitly gated act even after a Kernel exists.

---

## 8. Architectural Approach

M41 follows the governance shape M40 used throughout: each work package is a
standalone document under `docs/implementation/M41_WPn_...md`, carrying its
own authority header block (`Implementation authority: NONE`, etc.),
validated against fixtures and golden vectors, and independently reviewed
before the next work package may begin. No work package grants itself
authority beyond specification, consistent with
[constitution §11](../architecture/platform_architecture.md#11-architecture-governance)
(G5: Technical Design Documents are revised freely but carry no operational
authority of their own) and
[§12](../architecture/platform_architecture.md#12-canonical-vocabulary) (V1:
one term, one meaning, one home; V2: new nouns are registered in the Glossary
in the same change that defines them; V3: constitutional terms are reserved).

**Candidate-vocabulary admission workflow.** No work package's own text
admits a canonical noun by drafting it. WP1 SHALL begin by assembling the
complete **Candidate Vocabulary and Ownership Register**: every noun M41 is
known to require, listed up front with its proposed exact definition,
single owning domain, and disposition request, rather than raised
piecemeal as each work package happens to need a term. Every noun in that
register — and any further noun a later work package discovers it needs —
moves through five explicit stages before it may be used as if it were
canonical:

1. **Candidate Vocabulary Register** — the noun is entered in the register
   (WP1) or proposed by the work package that first needs it (WP2–WP4), with
   an exact definition, a single owning domain, an explicit disposition
   request (`ADMIT`, `REUSE`, `RENAME`, or `REJECT`), and an overlap analysis
   against every existing `GLOSSARY.md` entry and the M39/M40 negative corpus
   (§10).
2. **Independent Review** — the independent reviewer for that work package
   evaluates the candidate against V1–V3, ownership singularity, negative-
   corpus reappearance, and M34/M39/M40 compatibility, as part of the same
   independent review the work package itself requires (§11). This is not a
   separate governance track; it is a required subsection of each work
   package's independent review. The reviewer returns exactly one
   disposition:
   - `ADMIT` — a genuinely new noun, registered under a single owner;
   - `REUSE` — the concept is already covered by an existing term, which the
     work package must cite and bind to verbatim rather than re-defining;
   - `RENAME` — the candidate name collides with or shadows an existing
     term; the work package adopts the reviewer's alternative name; or
   - `REJECT` — the candidate duplicates existing canonical meaning without
     adding a distinct, owned concept (the M40 disposition given to
     Calculation Temporal Claim and M40's Producing Domain specialization).
3. **Required Corrections** — if the independent review returns the
   disposition subject to required corrections, the work package resolves
   each one individually, exactly as §11's own work-package review gate
   requires.
4. **Independent Confirmation** — a disposition (and, if applicable, its
   required corrections) is not final until independently confirmed. Only a
   `CONFIRMED` disposition may synchronize the Glossary or be relied upon.
5. **Synchronization and downstream reliance** — only a confirmed `ADMIT` or
   `RENAME` outcome produces a `GLOSSARY.md` change, made in the same change
   that records the independent confirmation. Confirmed `REUSE` and `REJECT`
   outcomes produce no Glossary change; the work package instead cites the
   existing entry. No later work package, later section of the same work
   package, or fixture may rely on a candidate noun until stage 5 is
   reached for that noun.

The flow is therefore:

```text
Candidate Vocabulary Register
        │
        ▼
  Independent Review
        │
        ▼
Required Corrections (if any)
        │
        ▼
Independent Confirmation
        │
        ▼
Only then may downstream artifacts rely on that disposition
```

No work package may rely on a candidate noun — in its own text, in a later
work package, or in a fixture — until its disposition is independently
confirmed, not merely independently reviewed. This closes the gap M40's own
RC-1 correction found (same-change timing alone is necessary but not
sufficient) and the gap M41's own independent confirmation found (review
alone is necessary but not sufficient; a correction affecting a disposition
must itself be independently confirmed before downstream reliance).

Applying this workflow to M41's own known vocabulary in advance: **Observation
Input Manifest** and **Provenance** are already effective Glossary entries
(the former one of M40's eight admissions; the latter pre-existing,
foundational vocabulary) and are therefore `REUSE`, not `ADMIT`, from the
outset — M41 binds to their frozen meaning and registers nothing new for
either. **Calculation Temporal Claim** was rejected by M40 in favor of the
existing Canonical Temporal Claim qualified by Event Type `Calculation`; M41
carries that `REJECT` disposition forward and does not reintroduce the
candidate under any name. Terms such as Market Measure Definition, Method
Version, Measure Subject, Method Requirement, Measurement Window, and Measure
Value remain open candidates: WP1's Candidate Vocabulary and Ownership
Register enters each of them up front, and each runs through the five
stages above — ending in independent confirmation — before any work package
relies on it.

**Frozen M40 ownership-boundary validation gate.** M40-WP1's admitted terms
were reviewed and approved against a mechanically testable five-part
boundary, not a general "no reinterpretation" statement:

1. **permitted subject** — the exact Asset or market-context subject the
   term may describe;
2. **permitted inputs** — the exact evidence categories the term may draw on
   (frozen M39 Observation evidence, canonical Asset identity and Definition
   Version references, explicit invocation parameters, explicit governed
   calculation dependencies);
3. **output meaning** — the exact semantic claim the term makes, and no
   more;
4. **prohibited inputs** — Ledger events, transactions, holdings, balances,
   or accounting state; Portfolio or Workspace membership, allocation,
   exposure, cash flow, or performance state; and person, household, goal,
   plan, preference, or life context; and
5. **prohibited judgment semantics** — forecast, recommendation, signal,
   consensus, action intent, evaluator verdict, trust score, correctness
   confidence, or quality ranking.

Every M41 Definition, Method Requirement, Subject, Manifest entry, and Result
coordinate specified in WP1–WP4 MUST pass all five parts before independent
review may approve it — this is a validation gate each work package's
independent review applies, not descriptive background. A candidate that
fails any part is inadmissible regardless of how well-specified it is
otherwise.

This gate also carries forward the frozen witnessed-versus-computed
distinction ([§4.1 of M40-WP1](M40_WP1_Canonical_Market_Measure_Vocabulary_and_Ownership_Specification.md#41-m39-preservation-rule)):
a witnessed or provider-reported statistic remains a Market Observation under
frozen M39 semantics with Canonical Temporal Claim Event Type `Observation`;
a platform-computed statistic is a Calculated Market Measure with Event Type
`Calculation`. Every M41 contract MUST keep this distinction explicit — no
WP1–WP4 artifact may represent a source-reported claim as if the platform
had calculated it, or vice versa.

Every input class a work package specifies MUST additionally be traceable to
exactly one of: exact M39 Observation evidence, an Asset Foundation
reference (Asset identity or Definition Version), an explicit invocation
parameter, or an explicit governed calculation dependency — the same
permitted-input closure M40-WP1 §6.1–6.2 enumerated. An input class that does
not trace to one of these four categories fails the gate.

The corrected architectural flow M40 established is preserved unchanged:

```text
Canonical Asset Identity + Definition Version
                         │
                         ├──────────────┐
                         │              │
                         ▼              ▼
              Method Requirements   Canonical M39
                                    Observation Evidence
                                           │
                                           ▼
                               Observation Input Manifest
                                           │
                                           ▼
                                Versioned Pure Calculation
                                           │
                                           ▼
                                Immutable Result + Provenance
```

M41 specifies every box below "Method Requirements" and "Canonical M39
Observation Evidence" down to "Immutable Result + Provenance." It does not
draw a new flow and does not move any box M40 already placed.

---

## 9. Dependencies

- **M39 (frozen)** — Observation source/classification/payload/relationship/
  identity specifications: the evidentiary vocabulary M41's Input Manifest
  binds to. M41 may not reinterpret any M39 term.
- **M40 (frozen)** — the eight admitted Canonical Glossary terms and the two
  rejected specializations. M41 must build strictly inside these meanings.
- **M34 Decision Register** (`M34-D-0004`, `M34-D-0005`, `M34-D-0010`) — the
  temporal claim grammar and authority patterns the Result model (WP4) must
  remain compatible with.
- **[MARKET_DATA_PLATFORM.md](../architecture/MARKET_DATA_PLATFORM.md)** and
  **[PROVIDER_INTERFACE.md](../architecture/PROVIDER_INTERFACE.md)** —
  architected but unimplemented. M41 must not encode any provider-shaped
  assumption anywhere in its contracts, consistent with those documents'
  provider-blindness principle.

---

## 10. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Scope creep into code ("just write the dataclass since the contract is already specified") | Every M41 artifact carries `Implementation authority: NONE`; §7 names code exclusion explicitly, as M40 did. |
| Reintroducing rejected M40 concepts (Calculation Temporal Claim, M40's Producing Domain specialization) | Each WP's validation step checks against the M40 negative corpus before independent review is requested. |
| Determinism gaps left implicit (silently assumed calendar, FX convention, rounding mode) | WP3's exit criterion is unchanged from the original plan: "no ambient semantic default remains," proven with golden vectors per choice. |
| Vocabulary drift from M39/M40 meaning | Independent reviewer checks Glossary V1 (one term, one meaning, one home) on every newly introduced noun before admission. |
| Milestone re-inflates to M40's five-work-package review cost, now across four specification work packages | Keep M41 strictly spec-only (no WP7–WP9 equivalent); if review load proves too high, split further rather than compress review rigor. |
| Glossary synchronization lags admission, repeating M40's RC-1 gap | WP1–WP4 each synchronize `GLOSSARY.md` in the same change as admission, not deferred to a later reconciliation step. |
| A candidate noun is relied upon (in later WP text or a fixture) before its admission disposition is independently confirmed | §8's five-stage workflow (Candidate Vocabulary Register → Independent Review → Required Corrections → Independent Confirmation → downstream reliance) is a review-blocking gate, checked explicitly in §12 acceptance criteria. |
| A concrete production Definition, Method Version, or formula is admitted as a documentation-only act (a golden vector or worked example read as a production admission) | §7 and §12 require the production Definition/Method catalog to remain empty throughout M41; every formula or worked example is explicitly labeled non-admitted. |
| Graphify refreshed on the strength of a drafted-but-unreviewed closeout | §13–§15 gate the refresh on independent review and confirmation of `M41_EPIC_CLOSEOUT.md`, not on its drafting. |

---

## 11. Proposed Work Package Structure

| Work package | Content | Independent review |
|---|---|---|
| M41-WP1 | Candidate Vocabulary and Ownership Register, then Definition, Method Version, and Applicability Contracts | Required, including the §8 ownership-boundary gate and candidate-vocabulary admission review; the register itself is reviewed and independently confirmed before WP1's contract text relies on any entry in it |
| M41-WP2 | Subject and Observation Input Manifest | Required, including the §8 ownership-boundary gate and candidate-vocabulary admission review |
| M41-WP3 | Temporal, Unit, Adjustment, and Arithmetic Semantics | Required (numerical and architectural), including the §8 ownership-boundary gate and candidate-vocabulary admission review |
| M41-WP4 | Result, State, and Provenance Model | Required, including the §8 ownership-boundary gate and candidate-vocabulary admission review |

No work package begins before the prior one is independently approved and any
required correction resolved — the same sequencing discipline the M40 plan
specified and M40's actual execution followed.

Epic Closeout is not a numbered work package. Repository convention treats it
as a milestone-level artifact produced after the last work package: M39
closed with WP1–WP6 followed by a standalone `M39_EPIC_CLOSEOUT.md`, and M40
closed with WP1–WP5 followed by a standalone `M40_EPIC_CLOSEOUT.md`. M41
follows the same pattern — a standalone `M41_EPIC_CLOSEOUT.md` performing
whole-corpus reconciliation after WP4, not a fifth work package (§14, §15).

---

## 12. Acceptance Criteria

- Every work package independently reviewed and returns `APPROVED` (or
  `APPROVED WITH REQUIRED CORRECTIONS`, resolved before the next work
  package opens) — the same bar M40 held throughout its work packages.
- **Every Definition, Method Requirement, Subject, Manifest entry, and
  Result coordinate in WP1–WP4 passes the §8 five-part ownership-boundary
  gate (permitted subject, permitted inputs, output meaning, prohibited
  portfolio/ledger/life-context inputs, prohibited judgment semantics) and
  keeps the witnessed-versus-computed/Event Type distinction explicit.**
  This is an independent-review admission blocker, not a recommendation:
  a work package that has not passed the gate does not return `APPROVED`.
- **Every candidate noun a work package relies on has an `ADMIT`, `REUSE`,
  `RENAME`, or `REJECT` disposition that is independently reviewed and, if
  the review required corrections, independently confirmed (§8) — no later
  work package, later section of the same work package, or fixture may
  depend on the noun before that confirmation.** Independent review alone is
  not sufficient; a correction affecting a disposition must itself be
  independently confirmed before downstream reliance. Only `ADMIT`/`RENAME`
  dispositions produce a `GLOSSARY.md` change, made in the same change the
  confirmation is recorded.
- No item from the M39/M40 negative corpus reappears in any M41 artifact,
  including no reuse of Calculation Temporal Claim or any specialization of
  Producing Domain, and no re-admission or redefinition of the already-
  effective Observation Input Manifest or Provenance terms.
- **The admitted production Definition/Method catalog remains empty
  throughout M41.** No concrete production Market Measure Definition, Method
  Version, formula, reference method, or production method is admitted by
  any WP1–WP4 artifact; illustrative formulas and reference calculations
  used in specification text or golden vectors are explicitly labeled
  non-admitted examples, not production admissions (§7).
- WP3's golden-vector validation demonstrates no ambient semantic default
  remains, using the evidence forms defined in §13.
- WP4's Result model demonstrates hash stability, no-value-on-failure,
  complete lineage, and canonical serialization round-trips, using the
  evidence forms defined in §13.
- Decision Log records the complete WP1–WP4 admission/rejection set before
  closeout.
- `M41_EPIC_CLOSEOUT.md` is itself independently reviewed, and any required
  correction on it is independently confirmed, before Graphify is refreshed
  (§13, §15).
- Closeout explicitly states that no production code, runtime, provider,
  persistence, or API surface changed, and identifies the next milestone as
  eligible for separately governed definition without authorizing it —
  preserving the same non-transitive-authority pattern M40 used relative to
  M39.

---

## 13. Required Evidence

- Work package documents under `docs/implementation/M41_WPn_...md`, each
  with its own independent-review and review-response artifacts (mirroring
  `M40_WPn_INDEPENDENT_REVIEW.md` / `_REVIEW_RESPONSE.md` /
  `_INDEPENDENT_CONFIRMATION.md`).
- Updated `GLOSSARY.md` entries for each newly admitted term, synchronized
  in the same change as admission.
- A Decision Log entry recording the M41 admission/rejection set, added at
  reconciliation/closeout — consistent with repository convention (see §14).
- `M41_EPIC_CLOSEOUT.md`, structured like `M40_EPIC_CLOSEOUT.md`: authority
  fields all `NONE`, repository-state section, and a "Next-Milestone
  Readiness" section identifying the next milestone as eligible for
  separately governed definition without authorizing it.
- `M41_EPIC_CLOSEOUT.md` is itself independently reviewed, with any required
  correction independently confirmed, before Graphify is refreshed — a
  distinct step from producing the closeout draft itself (see §14).
- A Graphify refresh performed only after that independent closeout review
  and confirmation, not merely because WP4 or a first closeout draft exists
  — consistent with repository convention (see §14).

**Specification-only validation-evidence definitions.** M41 is a
specification-only milestone: every evidentiary artifact below is a
documentation or data fixture, never an executable contract module,
calculation engine, registry, or reference kernel.

- **Golden vector** — a versioned, human-reviewable fixture file (e.g.
  `docs/implementation/m41/fixtures/wp3_<case>.md` or an equivalent data
  file referenced by path from the WP document) recording: exact canonical
  input bytes, the exact expected canonical output bytes, the semantic rule
  under test, and a short derivation rationale. A golden vector is data plus
  prose; it contains no executable code and invokes no calculation.
- **Canonical serialization** — the exact, work-package-specified byte-level
  encoding rule (field order, numeric representation, decimal precision and
  rounding mode, timestamp format, Unicode normalization form, and explicit
  schema-version tag) that any two independent implementations of the same
  contract MUST produce identical bytes under. WP3 (arithmetic/decimal
  rules) and WP4 (Result serialization) MUST each state this rule
  explicitly as a normative deliverable, not leave it implied by example.
- **Hash stability** — the property, proven by worked example in the WP4
  document, that applying the WP4 canonical-serialization rule to the same
  logical Result twice (by hand or by an independent reviewer's own
  recomputation) yields byte-identical output and therefore an identical
  hash. This is demonstrated by manual/independent recomputation recorded
  in the review, not by running a hashing program as part of M41.
- **Round-trip validation** — the property, proven by worked example, that
  the WP4 canonical serialization rule is unambiguous enough to be
  reversed: an independent reviewer, given only the serialized bytes and
  the WP4 specification, can reconstruct the exact logical Result the
  bytes represent, and vice versa. This is a specification-completeness
  proof, not a round-trip implemented in code.
- **Non-production validation scripts are out of scope for M41 and require
  separate authority.** If a work package's independent review determines
  that a fixture is easier to verify with a short, throwaway, non-committed
  script (e.g. to hand-check a decimal-rounding worked example), that script
  is scratch work used only to help the reviewer verify a golden vector by
  hand; it is not a repository artifact, is not committed, carries no
  `Implementation authority`, and its existence or absence has no bearing on
  whether the work package is `APPROVED`. Any durable, committed validation
  tooling (a fixture-runner, a conformance harness, a reference
  implementation) is executable-contract work and is out of scope for M41
  under §7 — it requires the same future, separately chartered milestone
  authority as the Registry and Kernel.

---

## 14. Repository Convention Check — Decision Log and Graphify

Before this proposal was written, repository history was checked for
convention on when a milestone's initiation is recorded:

- The Decision Log entries for M39 and M40
  (`## M39 — Canonical Asset Market Observation Epic Closeout`,
  `## M40 — Constitutional Vocabulary Cycle Completion`) were both added at
  **closeout/reconciliation**, not when the architecture proposal document
  was first created. M40's own WP2 commit message states explicitly: *"No
  Decision Log update"* at that stage. `M40_EPIC_CLOSEOUT.md §8` confirms the
  Decision Log gained its M40 entry only at the epic closeout.
- Graphify was likewise refreshed only at M40's closeout
  (`M40_EPIC_CLOSEOUT.md`: *"Graphify refresh: NOT_PERFORMED"* is the
  in-flight status; the refresh happens after closeout, per repository
  status above).

Repository convention therefore does **not** call for a Decision Log entry
or a Graphify refresh at the architecture-proposal stage. Both are deferred
to Epic Closeout — the milestone-level artifact that follows WP4 (§11),
consistent with how M39 and M40 were actually handled. No Decision Log or
Graphify action is taken as part of this proposal.

The Graphify refresh specifically is gated on more than the closeout
document's existence: `M40_EPIC_CLOSEOUT.md`'s own header records
`Graphify refresh: NOT_PERFORMED` even though that closeout document was
itself complete — the refresh is a separate, later action, gated on the
closeout being independently reviewed and any required correction on it
independently confirmed, not on the first closeout draft existing. M41
follows the same sequencing: `M41_EPIC_CLOSEOUT.md` is drafted, then
independently reviewed, then (if corrections are required) independently
confirmed, and only then is Graphify refreshed. Producing WP4 or drafting
the closeout document never by itself triggers a refresh.

---

## 15. Freeze Boundaries and Closeout Requirements

**Freeze boundaries:**

- M29–M40 remain frozen and are not reopened by M41 under any work package.
- M41 may not modify `platform_architecture.md`, `asset_foundation.md`,
  `UNIVERSAL_ASSET_ARCHITECTURE.md`, or any Domain Constitution — only
  `GLOSSARY.md` (additive registrations) and the Decision Log (additive
  entries, at closeout).
- M41 grants zero implementation, runtime, provider, persistence, API, or
  production authority — identical posture to every M40 work package header.
- The Registry, Resolver, Kernel, and Integration Design deferred in §7
  remain out of M41's authority regardless of how ready their design text
  is; readiness of a specification is never itself authorization to build.
- The production Definition/Method catalog remains empty throughout M41: M41
  specifies the future method-admission mechanism but does not exercise it
  (§7); readiness of that mechanism's specification is never itself
  authorization to admit a concrete production method.

**Closeout requirements (executed at Epic Closeout, following M41-WP4, per
§11):**

- Whole-corpus reconciliation across M41-WP1–WP4: no unresolved correction,
  no conflicting terminology, no ownership or authority conflict — the same
  check M40-WP4/closeout performed, including a re-check that the §8
  ownership-boundary gate held across every WP1–WP4 artifact and that the
  production Definition/Method catalog is still empty.
- `M41_EPIC_CLOSEOUT.md` is independently reviewed and any required
  correction independently confirmed before the Graphify refresh below
  (§13, §14) — closeout drafting and closeout approval are distinct steps.
- Explicit statement that no production code or operational surface changed.
- An explicit "Next-Milestone Readiness" section identifying the next
  milestone as eligible for separately governed definition, without
  authorizing it — so that no future milestone can claim to inherit M41's
  authority any more than M41 inherited M40's.
- The Graphify refresh, performed only after the independent closeout review
  and confirmation above (§13, §14).

---

## Related Documents

- [M40 Canonical Asset Market Measure Foundation Plan](M40_Canonical_Asset_Market_Measure_Foundation_Plan.md) — source of the deferred WP3–WP9 content this proposal re-charters
- [M40 Epic Closeout](M40_EPIC_CLOSEOUT.md) — the frozen state this proposal builds forward from
- [M39 Epic Closeout](M39_EPIC_CLOSEOUT.md) — the frozen Observation corpus M41's Input Manifest binds to
- [Platform Architecture](../architecture/platform_architecture.md) — governing constitution, §11 (Architecture Governance) and §12 (Canonical Vocabulary)
