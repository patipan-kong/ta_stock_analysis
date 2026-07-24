# M41-WP2 — Architecture Proposal

**Document status:** Submitted M41-WP2 Architecture Proposal.

**Architecture authority:** Frozen (cited, not modified)

**M41-WP1 authority:** Frozen (cited, not modified)

**Implementation authority:** `NONE`

**Runtime authority:** `NONE`

**Provider authority:** `NONE`

**Persistence authority:** `NONE`

**API authority:** `NONE`

**Review history:** [Independent Architecture Review](M41_WP2_ARCHITECTURE_INDEPENDENT_REVIEW.md) returned `APPROVED WITH REQUIRED CORRECTIONS` (2026-07-23, findings M41-WP2-AR-1 through M41-WP2-AR-7). All seven findings are resolved in this revision; see [Required Corrections Response](M41_WP2_REQUIRED_CORRECTIONS_RESPONSE.md) for the disposition of each.

This document specifies the architecture, scope, and work-package decomposition for M41-WP2. It does not modify the M41 Architecture, any M41-WP1 artifact, `GLOSSARY.md`, the Decision Log, or the Implementation Index. Neither WP2-Stage A nor WP2-Stage B has begun.

---

## 0. What WP2 inherits vs. what it must not touch

Before scoping anything new, three things are already frozen and confirmed, and WP2's whole job is to build *inside* them, not around them:

| Already confirmed | Source | What it means for WP2 |
|---|---|---|
| **Measure Subject** — `ADMIT`, three closed shapes: (a) single canonical Asset identity, (b) ordered canonical reference set of ≥2 Asset identities, (c) explicit market-context parameter set with no Asset identity | [Register §6.4](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md#64-measure-subject), confirmed | WP2 does **not** re-derive or re-litigate this definition. It inherits the *disposition* confirmed. What's still open is the record structure, canonical identity rule, and ordering mechanics — not the meaning. |
| **Observation Input Manifest** — immutable, complete, deterministically ordered evidence binding of exact frozen M39 Observation evidence | `GLOSSARY.md`, effective (M40) | WP2 does **not** redefine this term or widen its membership. It specifies the *binding rule* — how the M39-Observation-evidence share of a Market Measure Definition's permitted input-category declaration, as narrowed by a Method Requirement's prerequisite category and evaluation rule, concretely resolves to actual M39 Observation instances for one Measure Subject. |
| **Market Measure Definition / Method Version / Method Requirement** | M41-WP1 Stage 2, `CONFIRMED`, `FROZEN` | WP2 cites these by exact field reference only (Stage 2 §5.4, §7.4, §10). It never edits their fields, identity rules, or five-part gate results, and never attributes one contract's field to another. |

Stage 2 §5.4 already assigns the four-category permitted-input declaration — a non-empty subset of {M39 Observation evidence; Asset Foundation reference data; explicit invocation parameters; explicit governed calculation dependencies} — to **Market Measure Definition**, not to Method Requirement. Method Requirement's own fields (§7.4) are closed to a declaring Method Version reference, a prerequisite category (subject shape, dependency presence, or Observation category availability), and an evaluation rule over that closed grammar (§7.4a). §10 fixes these field-to-contract relationships and WP2 must not blur them. Stage 2 §5.4 also already closes *which* of the three Measure Subject shapes a Definition requires, by citation. WP2's job is everything Stage 2 explicitly declined to specify (§12 of the Stage 2 spec): Measure Subject's own record construction, identity, canonical ordering, and serialization, plus the manifest's binding, serialization, equivalence/conflict disposition, and identity — all built on exact reference to the fields above, never a restatement of them.

---

## 1. Objectives

- Specify the **canonical record structure, identity rule, ordering mechanics, and canonical serialization** for a Measure Subject in each of its three confirmed shapes.
- Specify the **binding rule** connecting the M39-Observation-evidence share of a Market Measure Definition's permitted input-category declaration, as narrowed by a Method Requirement's prerequisite category and evaluation rule, to concrete Observation Input Manifest entries, for one exact Measure Subject.
- Specify the manifest's **canonical serialization** (byte-level encoding any two independent implementations must agree on) and **manifest identity** (when two manifests denote the same semantic evidence set) as ordinary contract language, consistent with the confirmed Stage 1 noun inventory.
- Specify **evidence equivalence vs. conflict determination** — when two candidate M39 Observation selections for the same Subject are the same evidence (equivalent) versus genuinely competing evidence (conflicting), and the input-sufficiency consequence of a conflict, expressed only through the existing frozen `Computation Outcome` values — never a silent pick, and never a new outcome.
- Produce a reviewed, fixture-referenced spec that M41-WP3 (temporal/unit/arithmetic) and M41-WP4 (Result/Provenance) can cite without re-deriving Subject or Manifest semantics, and without WP2 pre-specifying WP4's Result or Computation Outcome interaction model.

### Relationship to WP1
Strictly downstream. WP2 supplies the two nouns Stage 2 explicitly named as its own deferred obligation (§12) and nothing else. It does not reopen Market Measure Definition, Method Version, or Method Requirement.

### Relationship to WP3/WP4
WP3 (temporal/unit/window semantics) and WP4 (Result/Provenance) will need to cite a *bound* Measure Subject and a *resolved* manifest as inputs to their own contracts (e.g., a Measurement Window is evaluated relative to a Subject; a Market Measure Result names its exact Subject and Manifest in its identity). WP2 must produce those citable primitives before WP3/WP4 can be written without forward references to undefined structure.

---

## 2. Scope

### Included
- Measure Subject canonical record shape for all three closed forms exactly as confirmed at register §6.4: (a) a single canonical Asset identity reference, (b) an ordered canonical reference set of ≥2 Asset identities, (c) an explicit market-context parameter set containing no Asset identity. No shape carries a Definition Version coordinate.
- Measure Subject identity rule (what makes two Subject records the same Subject), canonical ordering rule for the multi-Asset shape, and Measure Subject canonical serialization (byte-level encoding rule).
- Observation Input Manifest binding rule: how the M39-Observation-evidence share of a Market Measure Definition's permitted input-category declaration (§5.4), as narrowed by the bound Method Requirement's prerequisite category and evaluation rule (§7.4/§7.4a), concretely resolves to manifest entries for one Subject. Asset Foundation reference data, explicit invocation parameters, and explicit governed calculation dependencies are separately owned binding coordinates verified by the same overall binding rule; they are never represented as manifest entries.
- Canonical serialization rule for the manifest (field order, entry ordering, no dynamic "latest" reference — already prohibited by the frozen glossary entry), limited to exact M39 Observation evidence membership.
- Evidence equivalence determination (same semantic M39 Observation evidence, different representation) vs. conflict determination (genuinely competing M39 Observation evidence), expressed as ordinary contract language, and the input-sufficiency consequence each maps to under the existing frozen `Computation Outcome` values.
- Manifest identity rule, expressed as ordinary contract language per the confirmed Stage 1 noun inventory.
- Five-part ownership-boundary gate re-application to every new field, exactly as WP1 did.
- Golden vectors for: a shape-(a) Subject, a shape-(b) ordered multi-Asset Subject (including a Subject ordering-permutation pair), a shape-(c) market-context Subject, one M39-Identity-Equivalent representation case, one identity-distinct conflict case, one forbidden provider-shaped-input rejection case, one Observation Input Manifest entry-ordering-permutation case (distinct from the Subject ordering-permutation pair — differently ordered representations of the same valid manifest entry set resolving through the normative ordering rule to the same canonical Manifest serialization and identity), and byte-level round-trip reconstruction for both Subject and Manifest encodings.

### Explicit exclusions
- Redefining Measure Subject's three shapes, ownership, or permitted/forbidden inputs (frozen at WP1).
- Redefining Observation Input Manifest's meaning (frozen at M40).
- Measurement Window, timezone/calendar, unit/currency, rounding (M41-WP3).
- Measure Value, Result composition, `Computation Outcome` definition, degraded-state interaction matrix, Provenance model (M41-WP4). WP2 cites existing frozen `Computation Outcome` values; it never adds, removes, or redefines one.
- Any executable module (`subjects.py`, `input_manifest.py`, or equivalents) — named for future planning only.
- Any Asset Registry, Portfolio Engine, optimizer, or execution-intent behavior change.
- Exercising the method-admission gate or admitting any concrete production Definition/Method/formula — the production catalog stays empty through WP2 as it did through WP1.

### Deferred (explicitly, to name-but-not-do)
- Frozen Registry / Applicability Resolver and Pure Computation Kernel (post-WP4, separately chartered milestone per the M41 architecture proposal §2, §7).
- Read-Only Integration and Adoption Design (same deferral).

---

## 3. Proposed architecture

WP2 sits in the flow the M41 architecture already drew (proposal §8):

```text
Canonical Asset Identity + Definition Version
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
      Method Requirements    Canonical M39
      (WP1, frozen)          Observation Evidence
                                     │
              ┌──────────────────────┘
              ▼
      ┌───────────────────┐
      │  Measure Subject   │  ← WP2: record/identity/ordering
      │  (bound instance)  │
      └─────────┬─────────┘
                │ binds
                ▼
      ┌───────────────────────────┐
      │ Observation Input Manifest │  ← WP2: binding rule, serialization,
      │  (resolved for this        │     equivalence/conflict, identity
      │   Subject + Requirement)   │
      └─────────┬─────────────────┘
                │
                ▼
        Versioned Pure Calculation (WP3 semantics, future Kernel)
                │
                ▼
      Immutable Result + Provenance (WP4)
```

WP2 does not draw a new box — it fills in the internals of the two boxes ("Measure Subject" and "Observation Input Manifest") that WP1 explicitly left as citations, and defines the arrow between them (the binding rule).

---

## 4. Canonical terminology

Every noun below traces to one of: an already-confirmed candidate (reused, not redefined), an existing `GLOSSARY.md` entry (reused by reference), a term the confirmed Stage 1 noun inventory already classified as ordinary non-canonical contract language (reused as ordinary language, not re-candidated), or a genuinely new candidate WP2 must propose through its own Candidate Vocabulary supplement (§8 of the M41 proposal) only after showing existing canonical vocabulary and ordinary contract language are insufficient.

| Term | Status entering WP2 | WP2's obligation |
|---|---|---|
| Measure Subject | Confirmed `ADMIT` (WP1 register §6.4) | Cite verbatim; specify record/identity/ordering/serialization only |
| Observation Input Manifest | Effective `GLOSSARY.md` entry (M40) | Cite verbatim; specify binding rule only; membership stays exact M39 Observation evidence |
| Provenance | Effective `GLOSSARY.md` entry | Reuse only where WP2 must say a manifest entry traces to a source — no redefinition |
| Manifest identity | Confirmed ordinary non-canonical contract language (register §6.0) | Use as ordinary contract language; do not re-candidate |
| Equivalence / conflict disposition | Confirmed ordinary non-canonical contract language (register §6.0) | Use as ordinary contract language; do not re-candidate |
| Canonical serialization | Confirmed ordinary non-canonical contract language (register §6.0) | Use as ordinary contract language for both Subject and Manifest; do not re-candidate |
| **Subject Reference** *(candidate under evaluation)* | Not yet proposed | Stage A must first show this is a governed noun rather than an ordinary field label before requesting a disposition: the exact immutable pointer form a Measure Subject uses to name one Asset (must not shadow Asset Registry's `asset_id`) |
| **Subject Ordering Key** *(candidate under evaluation)* | Not yet proposed | Stage A must first show this is a governed noun rather than an ordinary field label before requesting a disposition: the deterministic key the shape-(b) ordered set sorts by |
| **Manifest Entry** *(candidate under evaluation)* | Not yet proposed | Stage A must first show this is a governed noun rather than an ordinary field label before requesting a disposition: one line item in a resolved manifest — an M39 Observation reference plus its role in the requirement |

No formula, provider name, or production method appears anywhere in this list. No candidate above is pre-admitted or pre-owned by this proposal; disposition is a Stage A/Independent Confirmation outcome, not an architecture-proposal decision.

---

## 5. Component decomposition

Purely documentary "components" (no code implied):

1. **Subject Record Specification** — field list, per-shape variant, immutability statement. No shape carries a Definition Version field.
2. **Subject Identity Rule** — canonical-identity function description (what two records must share to be "the same Subject"), stated the same way WP1 stated Definition identity (§5.3 of Stage 2).
3. **Subject Ordering Rule** — for shape (b) only: deterministic ordering key and tie-break, consistent with the manifest's existing ordering requirement.
4. **Subject Canonical Serialization** — byte-level encoding rule for a Measure Subject record, symmetric in kind to the Manifest's own canonical serialization below.
5. **Manifest Binding Rule** — maps the M39-Observation-evidence share of a Market Measure Definition's permitted input-category declaration (§5.4), as narrowed by the bound Method Requirement's prerequisite category and evaluation rule (§7.4/§7.4a), onto concrete manifest entries for a bound Subject. Asset Foundation reference, invocation-parameter, and governed-calculation-dependency inputs are verified through their own separately owned contract coordinates, never folded into manifest entries.
6. **Manifest Canonical Serialization** — byte-level encoding rule (entry order, field order, no `latest` reference — already prohibited by the frozen term), scoped to exact M39 Observation evidence.
7. **Manifest Identity Rule** — when two manifests are the same semantic evidence binding (ordinary contract language).
8. **Evidence Equivalence/Conflict Determination Rule** — classification logic over M39 Observation evidence candidates (ordinary contract language) and its input-sufficiency mapping to an existing frozen `Computation Outcome` value.
9. **Five-Part Gate Re-application** — same checklist WP1 ran, applied to every field above.

---

## 6. Data / contract boundaries

- **Upstream boundary (Asset Foundation):** Measure Subject references Asset identity *by exact, immutable reference only*, exactly within the three closed shapes of register §6.4 — never mutates, derives, or reinterprets Asset identity, and carries no Definition Version field. Where the governing architecture requires an exact Asset Definition Version reference for a calculation, that reference is its own independently owned binding coordinate, bound alongside the Subject but not a constituent of it.
- **Upstream boundary (M39):** Manifest entries reference frozen M39 Observation identity and meaning *without correcting, merging, or superseding* the Observation — also already frozen. Manifest membership never includes Asset Foundation references, invocation parameters, or governed calculation dependencies.
- **Downstream boundary (WP3/WP4):** WP2 must expose exactly the vocabulary WP3 needs to say "the Measurement Window applies to this Subject" and WP4 needs to say "the Result identifies this exact Subject and Manifest" — no more. WP2 must not pre-specify Measurement Window, Result composition, Computation Outcome definition, or the degraded-state interaction matrix itself (that would be scope leakage into WP3/WP4, the same failure mode the M41 proposal's risk table already flags for WP7-into-WP8 boundary creep).
- **Lateral boundary (WP1):** WP2 cites Market Measure Definition's permitted input-category declaration (§5.4) and Method Requirement's prerequisite category and evaluation rule (§7.4/§7.4a) by exact field reference only, and may not add, rename, or reattribute a field between these contracts or add new fields to either.

---

## 7. Lifecycle

A Measure Subject and its bound Manifest are, like every other M41 artifact, **immutable once constructed**:

```text
Candidate Vocabulary Supplement (new WP2 nouns)
        │
        ▼
Independent Review (incl. five-part gate)
        │
        ▼
Required Corrections (if any)
        │
        ▼
Independent Confirmation
        │
        ▼
Contract text may be relied upon by WP3/WP4
```

There is no runtime lifecycle to specify (no construction-at-invocation-time state machine) — WP2 is a specification of what a valid Subject/Manifest record *must contain*, not a service that produces one. Runtime construction is out of scope until the future Kernel milestone.

---

## 8. Validation strategy

Mirrors WP1's evidence model exactly (per M41 proposal §13 — specification-only validation forms):

- **Golden vectors** (documentation fixtures, not code) for each of the three Subject shapes, a shape-(b) Subject ordering-permutation pair, an Observation Input Manifest entry-ordering-permutation case distinct from the Subject ordering-permutation pair, one M39-Identity-Equivalent representation case, and one identity-distinct conflict case.
- **Canonical serialization proof** — worked examples showing both the Subject's and the Manifest's byte-level rules are unambiguous, checked by hand/independent reviewer recomputation (no hashing program run as part of WP2).
- **Round-trip validation** — an independent reviewer, given only serialized bytes and the WP2 spec, can reconstruct the logical Subject and vice versa, and can reconstruct the logical Manifest and vice versa.
- **Provider-leak rejection check** — a documented example of a forbidden provider-shaped identifier (ticker, display symbol) in place of canonical `asset_id`, and the rule that rejects it.
- **Exact evidence reproduction check** — a documented example confirming a resolved manifest reproduces the exact frozen M39 Observation evidence it cites, with no correction, merge, or supersession.
- **Five-part gate** re-applied field-by-field, exactly as WP1 §11 did, with a pass/fail table per field.
- **Negative-corpus check** — confirm no Subject or Manifest field reintroduces a Ledger, Portfolio, judgment, or evaluation concept (the same check WP1 ran against the M39/M40 negative corpus).

---

## 9. Risks

| Risk | Mitigation |
|---|---|
| WP2 quietly redefines Measure Subject's three shapes, or adds a field (such as Definition Version) that register §6.4 does not contain, while "just adding structure" | Every new field checked verbatim against register §6.4's confirmed exact definition before independent review is requested; Definition Version is bound only as its own separately owned coordinate, never as a Subject field — same discipline WP1 used for its own inherited terms. |
| WP2 attributes the four-category permitted-input declaration to Method Requirement instead of Market Measure Definition, or widens Observation Input Manifest membership beyond exact M39 Observation evidence | Every binding-rule statement checked verbatim against Stage 2 §5.4, §7.4, and §10 before independent review is requested; manifest membership stays limited to M39 Observation evidence, with the other three input categories bound through their own separately owned coordinates. |
| Evidence equivalence/conflict determination invents an implicit fifth Computation Outcome without amending the frozen four-outcome enum | Conflict maps only to an *existing* outcome (`INSUFFICIENT_INPUT` — declared prerequisites not satisfied by a single unambiguous input set); no new outcome value is proposed, and Result composition / degraded-state interaction remain WP4's to specify, not WP2's. |
| Candidate nouns (Subject Reference, Subject Ordering Key, Manifest Entry) get used in WP2's own contract text before their disposition is independently confirmed, or ordinary-language terms already classified at Stage 1 (manifest identity, equivalence/conflict disposition, canonical serialization) get re-candidated | Apply the same five-stage vocabulary workflow WP1 used (Candidate Register → Independent Review → Required Corrections → Confirmation → downstream reliance) only to genuinely new nouns, after showing existing canonical vocabulary and ordinary contract language are insufficient; do not reopen Stage 1's settled ordinary-language classifications. |
| Repeat of WP1 Stage 2's three-round correction cycle (Independent Confirmation returned `NOT CONFIRMED` twice before Final2) | Budget for it up front — treat one pass at "Independent Review → Required Corrections → Independent Confirmation" as the optimistic case, not the plan; the M40/M41 track record so far is that first-pass confirmation on a multi-noun contract is the exception, not the rule. |
| Subject Ordering Key for shape (b) drifts from the manifest's own existing ordering requirement, producing two incompatible "canonical order" rules for what should be one ordering discipline | State explicitly that Subject ordering and Manifest entry ordering are the *same* deterministic discipline (or explain precisely why they differ) — do not let two independently-drafted ordering rules coexist un-reconciled. |
| Asset Foundation reference in a Subject record leaks a provider-shaped identifier (ticker, display symbol) instead of canonical `asset_id` | Explicit forbidden-input already exists in register §6.4; carry it into every field-level example in WP2's contract text. |

---

## 10. Governance boundaries

- WP2 may modify `GLOSSARY.md` only additively, only for confirmed `ADMIT`/`RENAME` new nouns, only in the same change as their independent confirmation.
- WP2 grants zero implementation/runtime/provider/persistence/API authority — identical posture to WP1.
- WP2 may not modify `platform_architecture.md`, `asset_foundation.md`, `UNIVERSAL_ASSET_ARCHITECTURE.md`, the M41 Architecture Proposal, or any frozen WP1 artifact.
- WP2 does not begin WP3 or WP4; it produces citable primitives for them but does not draft their contract text.
- WP2's own closeout artifacts (Independent Review, Required Corrections Response, Independent Confirmation) follow the same naming convention as WP1's (`M41_WP2_INDEPENDENT_REVIEW.md`, etc.) for repository consistency.
- No Decision Log entry or Graphify refresh at WP2's proposal stage — per the repository convention WP1's own §14 documented, both happen only at Epic Closeout (after WP4).

---

## 11. Recommended internal decomposition of WP2

The M41 architecture proposal fixes WP2 as one milestone work package (§11 table) — this decomposition is *internal staging within WP2*, mirroring how WP1 internally ran a "Stage 1" (vocabulary register) and "Stage 2" (contract spec) without becoming two milestone work packages.

### WP2-Stage A — Candidate Vocabulary Supplement
- **Purpose:** Propose only genuinely new nouns WP2's contract text will rely on (Subject Reference, Subject Ordering Key, Manifest Entry, and any others discovered while drafting), after showing existing canonical vocabulary and ordinary contract language are insufficient, before Stage B cites them. Manifest identity, equivalence/conflict disposition, and canonical serialization are NOT re-proposed — Stage 1 already classified them as ordinary non-canonical contract language (register §6.0) and Stage A must preserve that classification.
- **Dependencies:** Confirmed WP1 register (for Measure Subject's already-settled disposition and the §6.0 ordinary-language classifications) and `GLOSSARY.md` current state.
- **Deliverables:** `M41_WP2_STAGE_A_CANDIDATE_VOCABULARY_REGISTER.md`, one entry per candidate, each with: exact proposed definition; a determined single owner, justified through the governed candidate-admission workflow and recorded as a Stage A ownership disposition — this architecture proposal pre-owns and pre-admits no candidate, and does not name a specific owner in advance; disposition request; complete overlap analysis against `GLOSSARY.md` and the M39/M40 negative corpus; V1/V2/V3 analysis; M34/M39/M40 compatibility analysis; and the candidate-level five-part ownership-boundary gate (permitted subject, permitted inputs, output meaning, prohibited Ledger/Portfolio/Wealth inputs, prohibited judgment semantics). Every confirmed governed noun ends Stage A with exactly one determined owner.
- **Review artifacts:** `M41_WP2_STAGE_A_INDEPENDENT_REVIEW.md`, `M41_WP2_STAGE_A_REQUIRED_CORRECTIONS_RESPONSE.md` (if needed), `M41_WP2_STAGE_A_INDEPENDENT_CONFIRMATION.md` — distinct from Stage B's artifacts.
- **Completion criteria:** Independent Review completed; any Required Corrections resolved and independently confirmed; every candidate's disposition — whether or not correction was required — receives its own unconditional Independent Confirmation with no open findings; then Decision Log/Implementation Index synchronization for the confirmed entries. No Stage B text may rely on an entry until this completes.

### WP2-Stage B — Subject and Manifest Contract Specification
- **Purpose:** Write the actual contract text — Subject record/identity/ordering/serialization, Manifest binding/serialization/identity, evidence equivalence vs. conflict determination — using only confirmed vocabulary (WP1's + Stage A's), with Manifest membership held to exact M39 Observation evidence and conflict determination mapped only to existing frozen `Computation Outcome` values.
- **Dependencies:** Stage A confirmed; WP1 Stage 2 (frozen, cited not modified).
- **Deliverables:** `M41_WP2_STAGE_B_SUBJECT_AND_MANIFEST_CONTRACT_SPECIFICATION.md`, including the five-part gate table per field and the complete golden-vector/ordering-permutation/round-trip/provider-leak-rejection/exact-evidence-reproduction validation matrix listed in §8 above, covering both Subject ordering permutations and the distinct Observation Input Manifest entry-ordering-permutation case.
- **Review artifacts:** `M41_WP2_STAGE_B_INDEPENDENT_REVIEW.md`, `M41_WP2_STAGE_B_REQUIRED_CORRECTIONS_RESPONSE.md` (if needed), `M41_WP2_STAGE_B_INDEPENDENT_CONFIRMATION.md` — distinct from Stage A's artifacts.
- **Completion criteria:** Independent Review returns `APPROVED` (or `APPROVED WITH REQUIRED CORRECTIONS`, resolved); Independent Confirmation returns `CONFIRMED` with no open findings, unconditionally — same bar WP1 Stage 2 eventually cleared at Final2.

No stage begins before the prior one is independently confirmed — the same sequencing discipline WP1 and the M41 proposal both hold to.

---

## 12. Recommended implementation sequence

1. Draft WP2-Stage A (Candidate Vocabulary Supplement).
2. Independent Review of Stage A → Required Corrections (if any) → Independent Confirmation.
3. Draft WP2-Stage B (Contract Specification), citing only WP1's frozen fields and Stage A's now-confirmed nouns.
4. Independent Review of Stage B. Budget for at least one correction round given the WP1 Stage 2 precedent (three rounds before `CONFIRMED`).
5. Resolve Required Corrections; resubmit for Independent Confirmation; repeat until `CONFIRMED` with zero open findings.
6. Only then does WP3 (Temporal/Unit/Arithmetic Semantics) begin drafting — it will need to cite a confirmed Subject and Manifest identity rule for its own Measurement Window contract.
7. WP4 begins after WP3, for the same reason (Result identity needs both Subject/Manifest identity and Measurement Window resolution settled).
8. Epic Closeout follows WP4 — not a numbered work package, per existing M39/M40/M41 convention.

---

**Bottom line:** WP2's entire job is two things — give Measure Subject a concrete, citable record/identity/ordering rule, and give the Observation Input Manifest a concrete binding/serialization/identity rule tying it to that Subject. Everything else (Measurement Window, Result composition, Registry, Kernel) stays exactly where the frozen architecture already put it.
