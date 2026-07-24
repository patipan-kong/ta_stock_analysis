# M41-WP2 Stage A — Candidate Vocabulary Supplement

**Document role:** Architecture and Specification Author

**Document class:** Specification-only governance artifact (candidate vocabulary supplement)

**Milestone:** M41 — Canonical Asset Market Measure Contract Specification

**Work package:** M41-WP2, internal Stage A (per
[Architecture Proposal §11](M41_WP2_ARCHITECTURE_PROPOSAL.md#11-recommended-internal-decomposition-of-wp2))

**Architecture authority:** Frozen (cited, not modified)

**M41-WP1 authority:** Frozen (cited, not modified)

**M41-WP2 Architecture authority:** Frozen (cited, not modified) — confirmed
`CONFIRMED` by
[M41-WP2 Final Architecture Confirmation](M41_WP2_FINAL_ARCHITECTURE_CONFIRMATION.md)

**Canonical vocabulary admission:** `NONE`

**Implementation authority:** `NONE`

**Runtime authority:** `NONE`

**Provider authority:** `NONE`

**Persistence authority:** `NONE`

**API authority:** `NONE`

**Decision Log status:** `NOT_SUBMITTED`

**Graphify status:** Not refreshed by this document

**Status:** `SUBMITTED_PENDING_INDEPENDENT_REVIEW`

**Date:** 2026-07-23

---

## 0. Inherited authority

This document treats the following as frozen and does not reopen, redesign,
or reinterpret any of them:

| Frozen artifact | What is inherited |
|---|---|
| [M41 Architecture](M41_ARCHITECTURE_PROPOSAL.md) | Overall milestone architecture, candidate-admission workflow (§8), five-part ownership-boundary gate |
| M41-WP1 Stage 1 / Stage 2 (Register, Contract Specification, Closeout) | Market Measure Definition, Method Version, Method Requirement, Measure Subject, Measurement Window, Measure Value — all confirmed `ADMIT`; Observation Input Manifest and Provenance confirmed `REUSE`; Calculation Temporal Claim confirmed `REJECT` |
| [M41-WP2 Architecture Proposal](M41_WP2_ARCHITECTURE_PROPOSAL.md), confirmed `CONFIRMED` by [Final Architecture Confirmation](M41_WP2_FINAL_ARCHITECTURE_CONFIRMATION.md) | WP2 scope, boundary, and its own internal Stage A/Stage B decomposition |
| `GLOSSARY.md` complete current state | Every effective term cited below |
| [M34 Decision Register](m34/audit/registers/decision_register.md) | `M34-D-0004`, `M34-D-0005`, `M34-D-0010` |

This document does not modify Architecture, WP1, the Glossary, the Decision
Log, or the Implementation Index. It does not refresh Graphify. It does not
begin WP2-Stage B. It performs candidate vocabulary evaluation only.

### 0.1 Authority order

Unchanged from
[WP1 register §2.1](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md#21-authority-order):
repository constitution / Decision Register / Glossary, then frozen milestone
specifications (M29–M40), then the confirmed M41 Architecture (including the
now-confirmed WP2 Architecture), then WP1's frozen register/contracts, then
this Stage A supplement, then any future WP2-Stage B text. No lower item may
reinterpret, weaken, or narrow a higher item.

### 0.2 Admission boundary

No entry in this document is canonical. Per the confirmed WP2 Architecture
§11 (Stage A), every candidate below must pass Independent Review, any
Required Correction, and its own unconditional Independent Confirmation
before synchronization and downstream reliance. Until that confirmation:

- no candidate term below is added to `GLOSSARY.md`;
- no WP2-Stage B contract text may claim a candidate term is canonical or
  rely on it;
- no schema, module, service, or runtime behavior is justified by this
  document; and
- examples, names, and constraints below are not runtime behavior.

---

## 1. Purpose

Per [M41-WP2 Architecture Proposal §11](M41_WP2_ARCHITECTURE_PROPOSAL.md#wp2-stage-a--candidate-vocabulary-supplement),
this Stage A supplement identifies every genuinely new governed noun WP2's
Stage B contract text will rely on, after showing existing canonical
vocabulary and ordinary contract language are insufficient. It reuses
existing canonical vocabulary wherever possible and creates no new vocabulary
beyond what is shown to be necessary. It begins evaluation with the three
candidates the Architecture Proposal named — **Subject Reference**, **Subject
Ordering Key**, **Manifest Entry** — and then states whether any further
candidate is required.

**Frozen and not reopened** (per Architecture Proposal §4, §11, confirmed by
the Independent Architecture Review's M41-WP2-AR-4 finding and its
resolution): **Manifest Identity**, **Canonical Serialization**, **Evidence
Equivalence**, and **Evidence Conflict Determination** remain confirmed
ordinary non-canonical contract language ([WP1 register §6.0](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md#60-complete-noun-inventory)).
They are not evaluated as candidates anywhere in this document.

---

## 2. Governing authority for this evaluation

Each candidate below is evaluated against:

- the frozen ownership baseline at
  [WP1 register §4](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md#4-frozen-ownership-baseline);
- the confirmed Measure Subject disposition at
  [WP1 register §6.4](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md#64-measure-subject);
- the effective `GLOSSARY.md` entries for
  [Asset](../GLOSSARY.md#asset),
  [Observation Input Manifest](../GLOSSARY.md#observation-input-manifest),
  [Market Measure Result](../GLOSSARY.md#market-measure-result),
  [Computation Outcome](../GLOSSARY.md#computation-outcome), and
  [Provenance](../GLOSSARY.md#provenance);
- the M39/M40 negative corpus (Calculation Temporal Claim; M40's Producing
  Domain specialization; a generic Analysis domain; a composite Instrument
  Analysis authority; a portfolio-measurement owner; an Investment
  Judgment/recommendation/strategy layer; an execution/transaction/trading
  authority); and
- Platform Architecture §12 (V1 one term/one meaning/one home, V2 same-change
  synchronization, V3 constitutional-term reservation).

**Record fields used below** (per the confirmed WP2 Architecture §11
requirement): candidate name, proposed definition, proposed owner, ownership
rationale, canonical overlap analysis, existing glossary overlap analysis,
M39/M40 overlap analysis, negative corpus analysis, V1/V2/V3 compatibility
analysis, M34/M39/M40 compatibility analysis, five-part ownership-boundary
gate, recommended disposition. Disposition is exactly one of `ADMIT`,
`RENAME`, `MERGE`, `REJECT`.

---

## 3. Candidate Evaluations

### 3.1 Subject Reference

**Candidate name:** Subject Reference

**Proposed definition (as entering Stage A):** "The exact immutable pointer
form a Measure Subject uses to name one Asset" (Architecture Proposal §4).

**Proposed owner:** Asset Foundation — the existing canonical owner into
which this candidate's meaning merges. No new ownership is created and no
ownership transfer occurs.

**Ownership rationale:** Asset Foundation already and exclusively owns
`asset_id` ([`GLOSSARY.md#asset`](../GLOSSARY.md#asset),
[`GLOSSARY.md#asset-registry`](../GLOSSARY.md#asset-registry)), the exact
reference Measure Subject cites. Because Subject Reference's proposed
meaning collapses entirely into that already-owned reference, Stage A's
ownership disposition for this candidate is: **MERGE into Asset Foundation's
existing `asset_id`.** No governed noun is admitted, so no new owner is
determined; the determined owner is the existing owner of the concept the
candidate merges into.

**Canonical overlap analysis:** Confirmed [Measure Subject](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md#64-measure-subject)
already closes this exact question at the candidate-admission level. Its
proposed exact definition names shape (1) as "a single canonical Asset
identity reference" and shape (2) as "an ordered, canonical reference set of
two or more Asset identities." Its constitutional constraints already state:
"It MUST reference canonical Asset identity by exact, immutable reference; it
MUST NOT recreate or shadow Asset identity." A "Subject Reference" noun would
either (a) restate this existing constraint under a new capitalized name, in
which case it adds no semantic content Measure Subject does not already own,
or (b) introduce a second pointer form distinct from Asset Foundation's own
identity, in which case it is exactly the shadow-identity risk the
Architecture Proposal's own §9 risk table names ("Asset Foundation reference
in a Subject record leaks a provider-shaped identifier"). Neither outcome
supports a new governed noun.

**Existing glossary overlap analysis:** [`GLOSSARY.md#asset`](../GLOSSARY.md#asset)
already states: "Every asset receives a permanent internal `asset_id`,"
owned by Asset Foundation via the Asset Registry
([`GLOSSARY.md#asset-registry`](../GLOSSARY.md#asset-registry), "the single
source of truth for asset identity"). The pointer a Measure Subject cites is
exactly this `asset_id` — not a new coordinate type. Naming a second term for
"the pointer form" would create two names for one already-owned reference
mechanic, a direct V1 defect (one term, one meaning, one home).

**M39/M40 overlap analysis:** Not applicable — Subject Reference concerns
Asset Foundation identity, not M39 Observation evidence or an M40 term. No
overlap with Observation Input Manifest or any M40-admitted noun.

**Negative corpus analysis:** No overlap with Calculation Temporal Claim, a
Producing Domain specialization, a generic Analysis domain, a composite
Instrument Analysis authority, a portfolio-measurement owner, an Investment
Judgment/recommendation/strategy layer, or an execution/transaction/trading
authority.

**V1/V2/V3 compatibility analysis:** V1 fails as a standalone admission — the
proposed meaning is not a new term with its own home; it is `asset_id`
(Asset Foundation) cited by Measure Subject (Market Intelligence) exactly as
register §6.4 already specifies. Admitting a second name for the same
reference would violate V1's "one term, one meaning, one home." V2
(same-change synchronization) does not apply because no `GLOSSARY.md` entry
is proposed. V3 is not implicated — no reserved term is touched, but for the
same reason no new reservation is created.

**M34/M39/M40 compatibility analysis:** Compatible with `M34-D-0010`
(descriptive market facts separate from judgment). Fully consistent with the
frozen Asset Foundation ownership baseline (WP1 register §4) — this
evaluation preserves, and does not transfer, Asset Foundation's sole
ownership of `asset_id`.

**Five-part ownership-boundary gate:**

| Part | Result | Reasoning |
|---|---|---|
| Permitted subject | N/A | No candidate concept survives evaluation as a distinct subject |
| Permitted inputs | N/A | Inputs collapse entirely into Asset Foundation's existing `asset_id` |
| Output meaning | N/A | No output meaning distinct from Measure Subject's own confirmed shape (1)/(2) reference |
| Prohibited Ledger/Portfolio/Wealth inputs | Pass (vacuously) | Nothing proposed carries any such input |
| Prohibited judgment semantics | Pass (vacuously) | Nothing proposed carries judgment, forecast, or evaluation meaning |

**Recommended disposition:** `MERGE`

**Disposition rationale:** Subject Reference merges fully into the existing,
already-admitted vocabulary owned by Asset Foundation: `asset_id`
([`GLOSSARY.md#asset`](../GLOSSARY.md#asset)), cited by the confirmed Measure
Subject shape (1)/(2) definition exactly as
[WP1 register §6.4](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md#64-measure-subject)
already states. WP2-Stage B contract text MUST refer to this reference as
"the Asset's `asset_id`, cited by exact immutable reference," using ordinary
descriptive language, and MUST NOT introduce a capitalized "Subject
Reference" noun or a second pointer type. This disposition directly
implements the Independent Architecture Review's provider-leak/shadow-identity
concern (§9 risk table) by removing the vocabulary surface that concern would
otherwise attach to.

---

### 3.2 Subject Ordering Key

**Candidate name:** Subject Ordering Key

**Proposed definition (as entering Stage A):** "The deterministic key the
shape-(b) ordered set sorts by" (Architecture Proposal §4).

**Proposed owner:** Market Intelligence — the existing canonical owner into
which this candidate's meaning merges. No new ownership is created and no
ownership transfer occurs.

**Ownership rationale:** Market Intelligence already owns the confirmed
Measure Subject term in full
([WP1 register §6.4](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md#64-measure-subject)),
including its constitutional ordering obligation for shape-(b) subjects.
Because Subject Ordering Key's proposed meaning is exactly that already-owned
ordering obligation, Stage A's ownership disposition for this candidate is:
**MERGE into the confirmed Measure Subject ordering obligation, owned by
Market Intelligence.** No governed noun is admitted, so no new owner is
determined; the determined owner is the existing owner of the concept the
candidate merges into.

**Canonical overlap analysis:** Confirmed Measure Subject's constitutional
constraints ([WP1 register §6.4](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md#64-measure-subject))
already require: "It MUST be enumerable and canonically orderable for
multi-Asset subjects, consistent with the Observation Input Manifest's
existing ordering requirement." The confirmed WP2 Architecture Proposal §5
already names the deliverable that discharges this obligation: Component 3,
"Subject Ordering Rule — for shape (b) only: deterministic ordering key and
tie-break, consistent with the manifest's existing ordering requirement."
The "ordering key" is therefore already scoped as a field of an
already-planned Stage B component of the already-admitted Measure Subject
term, not an independent concept requiring its own ownership record.

**Existing glossary overlap analysis:** No `GLOSSARY.md` entry with this name
exists. The nearest entries are
[Observation Input Manifest](../GLOSSARY.md#observation-input-manifest)
("deterministically ordered evidence binding... enumerable and canonically
orderable") and Measure Subject's own ordering constraint above. Both already
establish that determinism and canonical orderability are properties a
governed record's ordering rule must have; neither treats "the sort key" as
a separately named noun distinct from the ordered record itself. The
Architecture Proposal's own risk table (§9) additionally requires that
"Subject ordering and Manifest entry ordering are the same deterministic
discipline (or explain precisely why they differ)" — a requirement to
reconcile two rules under one Measure Subject / Manifest Entry vocabulary
pair, not evidence that a third, separately owned noun is needed.

**M39/M40 overlap analysis:** The ordering discipline must be reconciled with
Observation Input Manifest's own frozen ordering requirement (M40, effective)
per the Architecture Proposal's own risk table, but reconciliation is a
Stage B drafting obligation, not a vocabulary-admission question. No M40 term
is widened, narrowed, or duplicated by treating the ordering key as part of
Measure Subject's own specification.

**Negative corpus analysis:** No overlap with Calculation Temporal Claim, a
Producing Domain specialization, a generic Analysis domain, a composite
Instrument Analysis authority, a portfolio-measurement owner, an Investment
Judgment/recommendation/strategy layer, or an execution/transaction/trading
authority.

**V1/V2/V3 compatibility analysis:** V1 fails as a standalone admission — a
second, independently owned noun for "the sort key" would split one ordering
obligation (already assigned to Measure Subject, Market Intelligence) across
two homes, the opposite of "one term, one meaning, one home." V2 does not
apply — no `GLOSSARY.md` entry is proposed. V3 is not implicated.

**M34/M39/M40 compatibility analysis:** Compatible with `M34-D-0010`.
Preserves the frozen Observation Input Manifest ordering requirement
(M40-WP1) without redefinition — the ordering key concept is bounded to
Measure Subject's own shape-(b) obligation and does not restate or widen the
manifest's own ordering rule.

**Five-part ownership-boundary gate:**

| Part | Result | Reasoning |
|---|---|---|
| Permitted subject | N/A | No candidate concept survives evaluation as a distinct subject |
| Permitted inputs | N/A | The ordering obligation is already an input-shape constraint owned by Measure Subject |
| Output meaning | N/A | No output meaning distinct from Measure Subject's own canonical ordering |
| Prohibited Ledger/Portfolio/Wealth inputs | Pass (vacuously) | Nothing proposed carries any such input |
| Prohibited judgment semantics | Pass (vacuously) | Nothing proposed carries judgment, forecast, or evaluation meaning |

**Recommended disposition:** `MERGE`

**Disposition rationale:** Subject Ordering Key merges into the
already-admitted Measure Subject term
([WP1 register §6.4](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md#64-measure-subject)),
as the deterministic sort key and tie-break specified by WP2-Stage B's
already-named "Subject Ordering Rule" component
([Architecture Proposal §5](M41_WP2_ARCHITECTURE_PROPOSAL.md#5-component-decomposition), Component 3).
It is ordinary contract language describing a field of an already-owned
concept, not a standalone governed noun, and receives no independent
`GLOSSARY.md` entry. Stage B MUST state explicitly whether the Subject
ordering discipline and the Observation Input Manifest's own ordering
discipline are the same rule or, if not, exactly how and why they differ, per
the Architecture Proposal's own risk mitigation (§9) — this is a drafting
obligation for Stage B, not a reason to admit a fourth candidate.

---

### 3.3 Manifest Entry

**Candidate name:** Manifest Entry

**Proposed definition (as entering Stage A):** "One line item in a resolved
manifest — an M39 Observation reference plus its role in the requirement"
(Architecture Proposal §4).

**Proposed owner:** Market Intelligence.

**Ownership rationale:** Market Intelligence already owns Observation Input
Manifest in full ([`GLOSSARY.md#observation-input-manifest`](../GLOSSARY.md#observation-input-manifest))
and already owns every WP1 `ADMIT` candidate that binds M39 evidence to a
calculation (Market Measure Definition, Method Version, Method Requirement —
[WP1 register §4](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md#4-frozen-ownership-baseline)).
A named constituent element of an already-Market-Intelligence-owned manifest
carries no plausible alternative owner: it is not Asset Foundation (it names
M39 evidence, not Asset identity), not Ledger & Accounting, Portfolio
Intelligence, Decision Intelligence, Trust & Evaluation, Wealth Intelligence,
or Experience Platform (all forbidden per the frozen ownership baseline), and
it makes no provider, storage, or runtime claim.

**Canonical overlap analysis:** [Observation Input Manifest](../GLOSSARY.md#observation-input-manifest)
states the manifest "enumerates the exact frozen M39 Observation semantics
selected as calculation inputs" and "is enumerable and canonically
orderable," but — like Market Measure Result before Measure Value was
admitted at [WP1 register §6.6](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md#66-measure-value) —
it does not itself name the one-line-item coordinate that composition is
built from. WP2's own confirmed Architecture Proposal requires a "Manifest
Binding Rule" that "maps... onto concrete manifest entries for a bound
Subject" (§5, Component 5), a "Manifest Canonical Serialization" that
specifies "entry order, field order" (§5, Component 6), and golden vectors
for "an Observation Input Manifest entry-ordering-permutation case" (§2, §8,
§11) — all of which presuppose a defined, citable unit of manifest
composition. This is a genuine gap the same way Measure Value closed a gap
in Market Measure Result's composition: reusing "Measure Value" precedent,
Manifest Entry is proposed as a named coordinate within Observation Input
Manifest's already-admitted composition, not a new axis or a redefinition of
the manifest itself.

**Existing glossary overlap analysis:** No `GLOSSARY.md` entry with this name
exists. [Provenance](../GLOSSARY.md#provenance) ("where a fact came from...
every ingested event records its source, time, and adapter") is a plausible
adjacent term but describes lineage of a fact generally, not the specific
bound-evidence-plus-role coordinate a resolved manifest requires; Manifest
Entry reuses Provenance only where it must say an entry traces to a source,
exactly as the Architecture Proposal §4 already scopes it ("Reuse only where
WP2 must say a manifest entry traces to a source — no redefinition"), and
does not redefine or duplicate Provenance's own meaning. No collision.

**M39/M40 overlap analysis:** Manifest Entry's membership is exactly one
frozen M39 Observation reference plus its declared role in the binding
Method Requirement — never a second evidence category. It does not widen
Observation Input Manifest's frozen M40 membership (M41-WP2-AR-2's exact
concern): Asset Foundation reference data, explicit invocation parameters,
and explicit governed calculation dependencies remain separately owned
binding coordinates and are expressly excluded from Manifest Entry's own
proposed definition below. It does not correct, merge, or supersede the
referenced M39 Observation, consistent with the frozen M39 corpus and
Observation Input Manifest's own frozen non-mutation rule.

**Negative corpus analysis:** No overlap with Calculation Temporal Claim, a
Producing Domain specialization, a generic Analysis domain, a composite
Instrument Analysis authority, a portfolio-measurement owner, an Investment
Judgment/recommendation/strategy layer, or an execution/transaction/trading
authority.

**V1/V2/V3 compatibility analysis:** V1 satisfied — one term ("Manifest
Entry"), one meaning (a bound M39 Observation reference plus its role within
one resolved Observation Input Manifest), one home (Market Intelligence),
explicitly scoped as a coordinate within Observation Input Manifest's
already-admitted composition, not a new manifest-level axis or a competing
manifest concept. V2 (same-change synchronization) is deferred to Stage A's
own stage 5 (post-confirmation synchronization) and is not performed by this
document. V3 satisfied — the name does not collide with a reserved term, and
Observation Input Manifest's own frozen M40 meaning is not reopened,
narrowed, or widened (the exact discipline M41-WP2-AR-2's required correction
established).

**M34/M39/M40 compatibility analysis:** Compatible with `M34-D-0010`
(descriptive market facts separate from judgment/evaluation/presentation).
Does not touch `M34-D-0004` or `M34-D-0005` (no temporal-claim field of its
own). Preserves the frozen M40 Observation Input Manifest composition and
the frozen M39 Observation corpus without amendment, mutation, correction, or
supersession.

**Five-part ownership-boundary gate:**

| Part | Result | Reasoning |
|---|---|---|
| Permitted subject | Pass | Subject is one constituent line item of an already-owned Observation Input Manifest binding; no Ledger, Portfolio, or Wealth subject |
| Permitted inputs | Pass | Inputs limited to exactly one frozen M39 Observation reference and its declared role within the binding Method Requirement — never Asset Foundation reference data, invocation parameters, or governed calculation dependencies |
| Output meaning | Pass | Output meaning limited to identifying which frozen M39 Observation is bound and its role — no correctness, quality, trust, or recommendation meaning |
| Prohibited Ledger/Portfolio/Wealth inputs | Pass | Proposed definition expressly excludes any Ledger, Portfolio, or Wealth meaning |
| Prohibited judgment semantics | Pass | No forecast, recommendation, signal, consensus, action intent, evaluator verdict, trust score, correctness confidence, or quality ranking appears in the proposed definition |

**Recommended disposition:** `ADMIT`

**Proposed exact definition (for Independent Review):** A Manifest Entry is
one immutable, named constituent element of a resolved Observation Input
Manifest, consisting of exactly one reference to a frozen M39 Observation and
that Observation's declared role within the binding Method Requirement's
prerequisite evaluation. It is a coordinate within Observation Input
Manifest's already-admitted composition, not a new manifest-level concept,
axis, or evidence category. It carries no Asset Foundation reference,
invocation parameter, or governed calculation dependency — those remain
separately owned binding coordinates outside Manifest Entry's own closure. It
creates, corrects, merges, or supersedes no Observation; the referenced M39
Observation retains its frozen identity and meaning without exception.

**Constitutional constraints (for Independent Review):**

- It MUST reference exactly one frozen M39 Observation by exact, immutable
  reference; it MUST NOT recreate, correct, or reinterpret that Observation.
- It MUST carry its declared role within the binding Method Requirement's
  prerequisite evaluation; it MUST NOT carry a correctness, quality, or
  judgment meaning.
- It MUST NOT admit Asset Foundation reference data, invocation parameters,
  or governed calculation dependencies as its own membership (the exact
  M41-WP2-AR-2 boundary).
- Its canonical ordering and serialization within a Manifest are governed by
  Observation Input Manifest's existing frozen ordering/serialization
  requirement, not by a competing rule of its own.

**Glossary synchronization requirement (if confirmed):** Add a `GLOSSARY.md`
entry titled "Manifest Entry," cross-linking Observation Input Manifest and
Provenance with an explicit no-new-manifest-axis note and an explicit
exclusion of Asset Foundation reference data, invocation parameters, and
governed calculation dependencies from its membership, in the same change the
confirmation is recorded. Performed only after Independent Confirmation, not
by this document.

**Future contract acceptance evidence:** Once independently confirmed,
WP2-Stage B's contract text must supply the exact role-vocabulary closure
(the finite set of roles a Manifest Entry may declare), the exact canonical
serialization field order for one entry, and the golden vector demonstrating
the Observation Input Manifest entry-ordering-permutation case required by
the confirmed WP2 Architecture (§2, §8, §11). This is Stage B's own future
contract-review obligation, not a precondition for this candidate's present
disposition.

---

## 4. Further-candidate determination

No additional governed noun is genuinely required beyond the three
candidates evaluated above.

Every other term WP2-Stage B's contract text will need is already accounted
for by one of: an already-confirmed WP1 `ADMIT`/`REUSE` term (Measure
Subject, Observation Input Manifest, Provenance, Computation Outcome, Input
Sufficiency), a term this document merges into one of those (Subject
Reference into `asset_id`; Subject Ordering Key into Measure Subject), the
one new term this document admits (Manifest Entry), or language the
confirmed WP2 Architecture Proposal (§4, §11) and the frozen WP1 register
(§6.0) already fix as ordinary non-canonical contract language and forbid
re-candidating: Manifest Identity, Canonical Serialization, Evidence
Equivalence, and Evidence Conflict Determination. "Binding Rule" and
"Manifest Binding Rule" (Architecture Proposal §5, Component 5) are
documentary component titles for Stage B contract text, not governed nouns,
and are not evaluated as candidates for the same reason canonical
serialization is not: they name a rule Stage B will write, not a new
semantic concept requiring independent ownership.

This satisfies the confirmed WP2 Architecture §11 instruction that Stage A
propose "only genuinely new nouns WP2's contract text will rely on... after
showing existing canonical vocabulary and ordinary contract language are
insufficient." Existing vocabulary and the ordinary-language classifications
already fixed at Stage 1 are sufficient for every remaining WP2 drafting need
except the one gap Manifest Entry closes.

---

## 5. Disposition summary

| Candidate | Determined owner | Disposition | Governed noun / GLOSSARY entry created? |
|---|---|---|---|
| Subject Reference | Asset Foundation (existing owner; no transfer) | `MERGE` | No — merges into Asset Foundation's existing `asset_id` (`GLOSSARY.md#asset`), cited by the already-confirmed Measure Subject (WP1 register §6.4) |
| Subject Ordering Key | Market Intelligence (existing owner; no transfer) | `MERGE` | No — merges into the already-confirmed Measure Subject (WP1 register §6.4), owned by Market Intelligence, as a field of WP2-Stage B's "Subject Ordering Rule" component |
| Manifest Entry | Market Intelligence (new admission) | `ADMIT` | Yes — pending Independent Confirmation, one new `GLOSSARY.md` entry as a coordinate within Observation Input Manifest's already-admitted composition |

Every candidate records exactly one determined owner. For the two `MERGE`
candidates, the determined owner is the existing canonical owner of the
concept the candidate merges into — Asset Foundation for Subject Reference,
Market Intelligence for Subject Ordering Key — and no ownership transfer
occurs. No candidate is left undecided. No candidate's ownership is
predetermined beyond the disposition recorded above, and Manifest Entry's
`ADMIT` disposition — including its owner — does not become canonical,
reusable, or citable by WP2-Stage B until it receives its own unconditional
Independent Confirmation, per the confirmed WP2 Architecture §11 completion
criteria.

---

## 6. Validation

- **Exactly one determined owner per candidate:** Satisfied — Subject
  Reference records Asset Foundation and Subject Ordering Key records Market
  Intelligence as the determined existing owner each merges into (both
  `MERGE`, no ownership transfer); Manifest Entry records exactly one
  determined owner, Market Intelligence (`ADMIT`).
- **No ownership conflicts:** Satisfied — no two entries claim the same
  concept under different owners; the merged concepts (Subject Reference,
  Subject Ordering Key) are folded into owners (Asset Foundation, Market
  Intelligence respectively) that already and exclusively hold that meaning,
  with no transfer of that ownership implied or recorded.
- **No overlap with existing governed vocabulary:** Satisfied — each
  candidate's canonical overlap analysis (§3) traces its meaning to an
  already-admitted or already-effective term and shows the merge or admission
  does not duplicate, widen, or narrow that term.
- **No glossary duplication:** Satisfied — Manifest Entry is the only
  proposed `GLOSSARY.md` addition, and its overlap analysis shows no existing
  entry names this coordinate.
- **No provider terminology:** Satisfied — no candidate or disposition
  references a ticker, display symbol, provider identifier, or provider
  payload shape; Subject Reference's `MERGE` disposition exists specifically
  to foreclose a provider-shaped shadow-identity risk.
- **No runtime semantics:** Satisfied — no candidate authorizes invocation,
  retrieval, persistence, or execution; all three remain specification-only.
- **No implementation semantics:** Satisfied — no executable module, class,
  schema, or code path is named or implied.
- **No persistence semantics:** Satisfied — no storage model, table, or
  index is named or implied.
- **No API semantics:** Satisfied — no endpoint, request, or response shape
  is named or implied.
- **No portfolio semantics:** Satisfied — no candidate's permitted inputs or
  output meaning references portfolio membership, performance, attribution,
  exposure, allocation, or risk.
- **No ledger semantics:** Satisfied — no candidate's permitted inputs or
  output meaning references Ledger events, holdings, transactions, lots, or
  accounting truth.
- **No execution semantics:** Satisfied — no candidate authorizes or implies
  trading, order placement, or execution-intent behavior.

---

## 7. Constraints observed

This document does not modify M41 Architecture, WP1, `GLOSSARY.md`, the
Decision Log, or the Implementation Index. It does not refresh Graphify. It
does not begin WP2-Stage B. It writes no contract specification text — the
"Proposed exact definition" and "Constitutional constraints" recorded for
Manifest Entry in §3.3 are Independent-Review-facing candidate-admission
content, per the same form WP1's register used for its own `ADMIT`
candidates (e.g. [WP1 register §6.6](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md#66-measure-value)),
not WP2-Stage B's binding-rule or serialization-rule contract text itself. It
introduces no implementation, runtime, or provider logic.

---

## Repository Validation

- Git reports branch `feature/m41`.
- Before this document was created, Git reported six untracked M41-WP2
  architecture-governance artifacts: Architecture Proposal, Independent
  Architecture Review, Required Corrections Response, Architecture
  Confirmation, Architecture Confirmation Corrections Response, and Final
  Architecture Confirmation. No tracked modification was present.
- No M41 Architecture or M41-WP1 artifact is modified in the reported
  repository state.
- `docs/GLOSSARY.md`, `docs/engineering/DECISION_LOG.md`, and
  `docs/implementation/INDEX.md` have no reported modification.
- Graphify was not queried or refreshed by this document.
- No `M41_WP2_STAGE_A_INDEPENDENT_REVIEW.md`,
  `M41_WP2_STAGE_A_REQUIRED_CORRECTIONS_RESPONSE.md`,
  `M41_WP2_STAGE_A_INDEPENDENT_CONFIRMATION.md`, or any `M41_WP2_STAGE_B_*`
  artifact exists. Stage A independent review has not begun and Stage B has
  not begun.
- This document grants implementation, runtime, provider, persistence, and
  API authority `NONE`; no executable or runtime artifact was introduced.
- The only repository file created by this document is this Candidate
  Vocabulary Register.
- Markdown structure (heading sequence, table formatting, code-fence
  balance — none used) was checked by inspection; no unclosed fence or
  malformed table is present.

---

## Next step

This document is submitted for Independent Review
(`M41_WP2_STAGE_A_INDEPENDENT_REVIEW.md`, not yet created). No candidate
disposition recorded here is confirmed, canonical, or reliable until that
review, any required correction, and this candidate set's own unconditional
Independent Confirmation are complete, per the confirmed WP2 Architecture
§11 completion criteria. WP2-Stage B does not begin before that completion.

**Stage A Candidate Vocabulary Register — COMPLETE.**
