# M41-WP1 — Candidate Vocabulary and Ownership Register

**Date:** 2026-07-23

**Milestone:** M41 — Canonical Asset Market Measure Contract Specification

**Document class:** Constitutional candidate-vocabulary and ownership register

**Workflow stage:** Stage 3 of 5 (Required Corrections) complete —
[Candidate Vocabulary Register](M41_ARCHITECTURE_PROPOSAL.md#8-architectural-approach)
(Candidate Vocabulary Register → Independent Review → Required Corrections →
Independent Confirmation → downstream reliance). Stage 1 (this register) and
stage 2 (Independent Review,
[M41_WP1_INDEPENDENT_REVIEW.md](M41_WP1_INDEPENDENT_REVIEW.md), APPROVED WITH
REQUIRED CORRECTIONS) are complete. This revision resolves stage 3
(WP1-IR-1 through WP1-IR-5, see
[M41_WP1_REQUIRED_CORRECTIONS_RESPONSE.md](M41_WP1_REQUIRED_CORRECTIONS_RESPONSE.md))
and is submitted for stage 4, Independent Confirmation. No disposition in
this register is confirmed, canonical, or reliable until a separate
Independent Confirmation document records that stage 4 has passed.

**Status:** `CORRECTIONS_APPLIED_PENDING_INDEPENDENT_CONFIRMATION`

**Independent review:** [APPROVED WITH REQUIRED CORRECTIONS](M41_WP1_INDEPENDENT_REVIEW.md) — the
five required corrections (WP1-IR-1 through WP1-IR-5) are resolved in this
revision; see
[M41_WP1_REQUIRED_CORRECTIONS_RESPONSE.md](M41_WP1_REQUIRED_CORRECTIONS_RESPONSE.md).
This register is not independently confirmed until a separate Independent
Confirmation document records that stage 4 has passed.

**Canonical vocabulary admission:** `NONE`

**Implementation authority:** `NONE`

**Runtime authority:** `NONE`

**Production method authority:** `NONE`

**Provider authority:** `NONE`

**Persistence authority:** `NONE`

**API and public-exposure authority:** `NONE`

**Decision Log status:** `NOT_SUBMITTED`

**Supersedes:** `NONE`

**Closeout:** `NONE`

**Architecture phase:** Produced under the
[M41 Architecture Proposal](M41_ARCHITECTURE_PROPOSAL.md) (`APPROVED`,
independent review
[M41_ARCHITECTURE_INDEPENDENT_REVIEW.md](M41_ARCHITECTURE_INDEPENDENT_REVIEW.md),
required-corrections response
[M41_ARCHITECTURE_REQUIRED_CORRECTIONS_RESPONSE.md](M41_ARCHITECTURE_REQUIRED_CORRECTIONS_RESPONSE.md),
independently confirmed).

**Document role:** The complete candidate-vocabulary and ownership register
required by the approved M41 architecture §6 (M41-WP1 bullet), §8
("Candidate-vocabulary admission workflow," stage 1), and §11 (M41-WP1 row).
Per §6: *"WP1 SHALL begin by creating the complete Candidate Vocabulary and
Ownership Register (§8) before any Definition or Method Version contract
specification begins."* This document is that register. It precedes, and is
a precondition for, WP1's own Definition, Method Version, and Applicability
Contracts, which are not specified here and do not begin until this register
is independently reviewed, corrected if required, and independently
confirmed. Independent confirmation is always required before downstream
reliance; required corrections is the only conditional stage.

**Normative language:** `MUST`, `MUST NOT`, `SHALL`, `SHALL NOT`, `MAY`, and
`SHOULD` are normative within this register. They constrain what the
independent reviewer may consider for disposition; they do not themselves
admit vocabulary, synchronize `GLOSSARY.md`, or authorize implementation,
runtime use, persistence, provider integration, an API, or a production
method.

---

## 1. Purpose

This register assembles, in one place and before any contract specification
text is written, every noun M41 is known to require across its full
WP1–WP4 scope: its proposed exact definition, its single owning domain, an
overlap analysis against every existing `GLOSSARY.md` entry, a negative-
corpus analysis against the frozen M39/M40 negative corpus, a V1–V3
constitutional-compatibility analysis, and an explicit disposition request
(`ADMIT`, `REUSE`, `RENAME`, or `REJECT`).

This satisfies the governing review's RC-2 requirement — restated by the
independent confirmation as: *"WP1 SHALL begin by creating the complete
Candidate Vocabulary and Ownership Register before any Definition or Method
Version contract specification begins"* — and the M41 proposal's own §8
stage 1. No candidate in this register is canonical, admitted, or reusable by
any downstream artifact until it independently completes all five stages of
the workflow in §8 of the proposal.

## 2. Governing Authority

This register is subordinate to repository authority. Where this document
conflicts with an approved or frozen authority, that authority governs and
the conflicting M41 candidate is inadmissible.

The governing corpus is:

- [Platform Architecture](../architecture/platform_architecture.md),
  especially §11 (Architecture Governance) and §12 (Canonical Vocabulary: V1
  one term/one meaning/one home, V2 same-change synchronization, V3
  constitutional terms are reserved);
- [Canonical Glossary](../GLOSSARY.md) in its complete current state;
- [M34 Decision Register](m34/audit/registers/decision_register.md):
  `M34-D-0004`, `M34-D-0005`, and `M34-D-0010`;
- the complete frozen M39 corpus
  ([Epic Closeout](M39_EPIC_CLOSEOUT.md));
- the complete frozen M40 corpus
  ([Epic Closeout](M40_EPIC_CLOSEOUT.md),
  [M40-WP1 Vocabulary and Ownership Specification](M40_WP1_Canonical_Market_Measure_Vocabulary_and_Ownership_Specification.md),
  [M40-WP2 Vocabulary Admission Review](M40_WP2_Canonical_Market_Measure_Vocabulary_Admission_Review.md));
  and
- the approved [M41 Architecture Proposal](M41_ARCHITECTURE_PROPOSAL.md),
  its [independent review](M41_ARCHITECTURE_INDEPENDENT_REVIEW.md), its
  [required-corrections response](M41_ARCHITECTURE_REQUIRED_CORRECTIONS_RESPONSE.md),
  and its
  [independent confirmation](M41_ARCHITECTURE_INDEPENDENT_CONFIRMATION.md).

### 2.1 Authority order

The following order SHALL resolve any apparent conflict:

1. repository constitution, approved Decision Register decisions, and the
   Canonical Glossary;
2. frozen milestone specifications and closeouts (M29–M40);
3. the independently approved and confirmed M41 architecture;
4. this WP1 register; and
5. any future M41 work-package contract text.

No lower item MAY reinterpret, weaken, or silently narrow a higher item.

### 2.2 Admission boundary

This register is complete as a stage-1 deliverable, but no entry in it is
canonical. Per the M41 architecture proposal §8, every candidate MUST pass
independent review (stage 2), any required correction (stage 3), and
independent confirmation (stage 4) before synchronization and downstream
reliance (stage 5). Until a candidate's disposition is independently
confirmed:

- no candidate term SHALL be added to `GLOSSARY.md`;
- no downstream artifact — including M41-WP1's own Definition, Method
  Version, and Applicability Contracts — SHALL claim a candidate term is
  canonical or rely on it;
- no schema, module, service, registry, adapter, endpoint, persistence model,
  or production method SHALL be justified by this register; and
- examples, names, and constraints in this register SHALL NOT be treated as
  runtime behavior.

## 3. Scope

This register governs candidate semantic meaning, ownership, overlap
analysis, negative-corpus analysis, constitutional compatibility, and
disposition requests for every noun M41 is currently known to require. It
does not govern:

- the Definition, Method Version, and Applicability contract text itself
  (deferred until this register is independently confirmed — §6 of the M41
  proposal);
- formulas, indicators, calculation methods, or method parameters;
- Subject and Observation Input Manifest binding rules (M41-WP2 contract
  content — this register only admits the candidate nouns those contracts
  will use);
- temporal, unit, adjustment, or arithmetic rule text (M41-WP3 contract
  content);
- Result, State, and Provenance model text (M41-WP4 contract content);
- software design, implementation, runtime, persistence, provider, or API
  behavior; and
- production registration or method admission.

Naming a noun in this register specifies candidate meaning only. It
authorizes no work-package contract text, schema, or executable process, and
it does not itself begin M41-WP1's contract specification.

## 4. Frozen Ownership Baseline

This register inherits, without amendment, the frozen ownership baseline
established by
[M40-WP1 §4](M40_WP1_Canonical_Market_Measure_Vocabulary_and_Ownership_Specification.md#4-frozen-ownership-baseline)
and preserved through M40 admission and closeout:

| Semantic concern | Sole owner | Register preservation rule |
| --- | --- | --- |
| Canonical Asset identity, definition, classification, and Definition Version | Asset Foundation | Referenced without mutation or reinterpretation; never re-owned by a Market Measure candidate |
| Frozen M39 Market Observation meaning | Market Intelligence under frozen M39 | Consumed only as exact frozen evidence; never recreated or reclassified |
| The eight admitted M40 Canonical Glossary terms (Market Measure, Calculated Market Measure, Computation Outcome, Observation Input Manifest, Market Measure Result, Input Sufficiency, Deterministic Calculation, Mechanical Boundary Rules) | Market Intelligence (business terms) / Repository Architecture Governance (Mechanical Boundary Rules) | Reused with frozen meaning; never re-admitted or redefined |
| M41 candidate Definition, Method Version, Applicability, Subject, Window, and Value vocabulary proposed by this register | Market Intelligence | Candidate ownership only, subject to independent review and confirmation |
| Ledger events, holdings, transactions, lots, and accounting truth | Ledger & Accounting | Forbidden as any M41 candidate's semantic input |
| Portfolio membership, performance, attribution, exposure, allocation, and portfolio risk | Portfolio Intelligence | Forbidden as any M41 candidate's subject, input, or output meaning |
| Outlook, expected direction, instrument risk judgment, consensus, recommendation, signal, and plan | Decision Intelligence | Forbidden as any M41 candidate's output meaning |
| Correctness, reliability, quality, confidence-in-correctness, benchmark, and evaluator verdict | Trust & Evaluation | Never inferred from a candidate term's result or record |
| Household, person, goal, net worth, or life-plan meaning | Wealth Intelligence | Forbidden as any M41 candidate's subject or input |
| Projection, interaction, composition, and presentation label | Experience Platform | No truth or ownership transfer; outside this register |
| Authentication, authorization, approval, and actor authority | Existing authority boundaries | Unchanged; never created by any candidate term |

Every semantic concept in this register SHALL have exactly one owner.
Custody, reference, transport, display, storage, execution, or evaluation
SHALL NOT create shared ownership.

## 5. Register Record Fields

Each candidate entry in §6 uses the following fields, satisfying the
governing review's RC-2 requirement that each candidate carry "exact
definition, single owner, existing-term overlap analysis, V1–V3 disposition,
M34/M39/M40 compatibility, and `ADMIT`, `REUSE`, `RENAME`, or `REJECT`
outcome":

| Field | Required interpretation |
| --- | --- |
| Purpose | The constitutional reason the candidate concept exists |
| Owner | The single proposed semantic owner |
| Non-owner | Domains or mechanisms that may reference or carry the concept but cannot define or reinterpret it |
| Permitted inputs | Categories that may contribute to the concept's semantic claim |
| Forbidden inputs | Categories whose presence makes the candidate inadmissible |
| Proposed exact definition | The exact semantic claim the term would make if admitted |
| Constitutional constraints | Mechanically reviewable invariants the disposition must preserve |
| Overlap analysis | Comparison against every existing `GLOSSARY.md` entry with a plausible naming or meaning collision |
| Canonical reuse analysis | Whether an existing canonical term already covers this meaning, in whole or in part |
| Negative corpus analysis | Comparison against the frozen M39/M40 negative corpus (Calculation Temporal Claim; M40's Producing Domain specialization; a generic Analysis domain; a composite Instrument Analysis authority; a portfolio-measurement owner; an Investment Judgment/recommendation/strategy layer; an execution/transaction/trading authority) |
| V1–V3 disposition | Whether the candidate satisfies Platform Architecture §12 V1 (one term, one meaning, one home), V2 (same-change synchronization, deferred to stage 5), and V3 (constitutional-term reservation) |
| M34/M39/M40 compatibility | Explicit compatibility check against `M34-D-0004`, `M34-D-0005`, `M34-D-0010`, and the frozen M39/M40 corpus |
| Disposition request | Exactly one of `ADMIT`, `REUSE`, `RENAME`, `REJECT` |
| Glossary synchronization requirement | What `GLOSSARY.md` change, if any, this disposition would require — performed only after independent confirmation |
| Five-part ownership-boundary gate (current) | The candidate-level pass/fail result, recorded now, against the frozen M40 five-part gate (permitted subject; permitted inputs; output meaning; prohibited Ledger/Portfolio/Wealth inputs; prohibited judgment semantics) — decided from the candidate's own Purpose, Owner, Permitted/Forbidden inputs, and Proposed exact definition fields above, not from unwritten future contract text |
| Future contract acceptance evidence | What a future WP1–WP4 contract specification, once this candidate is independently confirmed, must additionally supply (exact vocabulary, formats, worked examples, golden vectors) to prove the confirmed term was used correctly. This is a downstream work-package obligation; it is not evidence this register's own candidate-admission review requires, and it does not gate the present disposition |

"Permitted" means constitutionally eligible for future candidacy. It does not
mean available, implemented, supported, or authorized for runtime use.

## 6. Candidate Vocabulary and Ownership Register

### 6.0 Complete Noun Inventory

The M41 architecture proposal §8 introduces its six illustrative candidates
with "Terms such as," not an exhaustive closure. This section corrects that
prior overstatement by inventorying every noun currently known across the
full M41 WP1–WP4 scope (proposal §6, §8; frozen M40 planning corpus) and
classifying each as exactly one of: `ADMIT` candidate, `REUSE` existing
canonical vocabulary, `REJECT` specialization, ordinary non-canonical
contract language, or explicitly outside M41. No additional vocabulary is
admitted by this inventory; it accounts for known nouns without proposing
new candidacy beyond what §6.1–§6.9 already register.

| Noun | Source | Classification | Reasoning |
| --- | --- | --- | --- |
| Market Measure Definition | Proposal §6, §8 | `ADMIT` candidate | Registered at §6.1 |
| Method Version | Proposal §6, §8 | `ADMIT` candidate | Registered at §6.2 |
| Method Requirement | Proposal §8 | `ADMIT` candidate | Registered at §6.3 |
| Measure Subject | Proposal §8 | `ADMIT` candidate | Registered at §6.4 |
| Measurement Window | Proposal §8 | `ADMIT` candidate | Registered at §6.5 |
| Measure Value | Proposal §6, §8 | `ADMIT` candidate | Registered at §6.6 |
| Observation Input Manifest | Proposal §6, §8 | `REUSE` | Registered at §6.7; frozen M40 term |
| Provenance | Proposal §6, §8 | `REUSE` | Registered at §6.8; pre-existing foundational term |
| Calculation Temporal Claim | Proposal §8 | `REJECT` (carried forward) | Registered at §6.9; frozen M40 rejection |
| Applicability | Proposal §6 (WP1 title), §4 | Fully covered by Method Requirement | "Applicability" names the contract *type* Method Requirement (§6.3) instantiates; it is not a separate noun requiring its own entry |
| Canonical serialization | Proposal §6 (WP2), §12 (WP4) | Ordinary non-canonical contract language | A property future WP2/WP4 contract text will specify for Observation Input Manifest and Measure Value respectively; not itself a governed noun with independent ownership |
| Equivalence vs. conflict disposition | Proposal §6 (WP2) | Ordinary non-canonical contract language | A comparison rule for Observation Input Manifest instances; part of WP2's future contract text, not a separate noun |
| Manifest identity | Proposal §6 (WP2) | Ordinary non-canonical contract language | An identity field of the already-reused Observation Input Manifest (§6.7); not a new term |
| Cutoff/window, timezone/calendar | Proposal §6 (WP3) | Fully covered by Measurement Window | Registered at §6.5 |
| Missing-data specification | Proposal §6 (WP3) | Ordinary non-canonical contract language | A rule governing Observation Input Manifest gaps; part of future WP3 contract text, not a new noun |
| Unit/currency specification | Proposal §6 (WP3) | Reuse of existing Unit Semantics (`GLOSSARY.md#unit-semantics`, Asset Foundation) | WP3 must cite, not redefine, Asset Foundation's frozen Unit Semantics; no new M41 noun |
| Adjustment specification | Proposal §6 (WP3) | Ordinary non-canonical contract language, bounded by existing Structural Event vocabulary | WP3 must not reinterpret Asset Foundation's Structural Event or Definition Version meaning; no new M41 noun |
| Decimal/rounding specification | Proposal §6 (WP3) | Ordinary non-canonical contract language | An arithmetic-precision rule; not a governed noun |
| Dependency specifications | Proposal §6 (WP3) | Fully covered by Method Version | Method Version's declared dependency versions field (§6.2) already covers this |
| Result identity | Proposal §6 (WP4) | Fully covered by existing Market Measure Result | An identity field within the already-admitted M40 Market Measure Result composition (`GLOSSARY.md#market-measure-result`); WP4 specifies the field, not a new term |
| Deterministic outcome/degraded-state interaction matrix | Proposal §6 (WP4) | Ordinary non-canonical contract language | A rule built from two already-admitted terms (Computation Outcome, Degraded State); not a new noun |
| Reserved Snapshot boundary | Proposal §6 (WP4) | Reference to existing Event Type value `Snapshot Creation` (`GLOSSARY.md#event-type`) | An exclusion rule — WP4 MUST NOT let a Market Measure Result claim the `Snapshot Creation` Event Type, which is reserved for its existing owner; not a new noun |
| Measure Invocation | M40 planning corpus (not carried into M41 architecture) | Explicitly outside M41 | Runtime request-to-apply-a-method construct; M41 is specification-only and admits no runtime authority (proposal §7); deferred to the future Frozen Registry/Kernel milestone |
| Dependency Manifest | M40 planning corpus (not carried into M41 architecture) | Fully covered by Method Version | Method Version's declared dependency versions field (§6.2) covers this meaning; not entered as a separate M41 noun |
| Measure Provenance (narrower lineage) | M40 planning corpus (not carried into M41 architecture) | Not currently required; potential future specialization of Provenance | §6.8 already reserves the path: if a future WP4 contract needs a narrower lineage structure, it MUST be registered as its own candidate specialization with its own overlap and V3 proof; no such specialization is proposed here |

This inventory satisfies WP1-IR-1: every noun M41 is currently known to
require is accounted for as an `ADMIT` candidate, a `REUSE`, a `REJECT`, or
explicitly non-canonical or out-of-scope language. No additional candidate
is admitted.

Nine entries carry a full disposition record below: the six `ADMIT`
candidates named by the M41 architecture proposal §8's illustrative list —
Market Measure Definition, Method Version, Measure Subject, Method
Requirement, Measurement Window, and Measure Value — and three carried-
forward dispositions: Observation Input Manifest and Provenance (`REUSE`),
and Calculation Temporal Claim (`REJECT`). Recording all nine together — not
only the six new candidates — keeps the register complete rather than
partial, per §6 field "Register preservation rule."

### 6.1 Market Measure Definition

**Purpose:** Name and version-bind the constitutional specification of what a
specific family of calculations claims to compute, independent of any
concrete formula, so a Method Version has exactly one Definition it realizes.

**Owner:** Market Intelligence.

**Non-owner:** Asset Foundation, Ledger & Accounting, Portfolio Intelligence,
Decision Intelligence, Trust & Evaluation, Wealth Intelligence, Experience
Platform, providers, storage, and runtime mechanisms.

**Permitted inputs:**

- the already-admitted Market Measure / Calculated Market Measure umbrella
  meaning (§4);
- an explicit declared subject shape (single-Asset, multi-Asset, or
  market-context);
- an explicit declared required output coordinate meaning; and
- an explicit permitted-input-category declaration drawn only from the
  frozen M40 four-category closure (M39 Observation evidence, Asset
  Foundation reference data, explicit invocation parameters, explicit
  governed calculation dependencies).

**Forbidden inputs:**

- a concrete formula, named indicator, or reference calculation (reserved to
  a future, separately admitted production method — M41 proposal §7);
- provider-shaped payloads or provider identity;
- Ledger, Portfolio, Wealth, judgment, or evaluation meaning (§4); and
- an ambient or ungoverned default for any declared field.

**Proposed exact definition:** A Market Measure Definition is an immutable,
versioned specification record identifying which Market Measure or
Calculated Market Measure concept a family of Method Versions realizes,
including its declared subject shape, required output coordinate meaning,
and permitted input-category declaration. It admits no formula, named
indicator, reference calculation, or production method.

**Constitutional constraints:**

- It MUST bind to exactly one already-admitted Market Measure or Calculated
  Market Measure concept; it MUST NOT create a new umbrella category.
- It MUST NOT itself admit a concrete production method (M41 proposal §7,
  §12 — empty catalog throughout M41).
- It MUST preserve the witnessed-versus-computed / Event Type distinction
  (M41 proposal §8, carried from M40-WP1 §4.1).
- It MUST pass the frozen M40 five-part ownership-boundary gate (M41
  proposal §8) in full at the candidate level now, and its future contract
  text MUST pass the gate again for its concrete fields before that
  contract's own independent review.

**Five-part ownership-boundary gate (current):**

| Part | Result | Reasoning |
| --- | --- | --- |
| Permitted subject | Pass | Subject is a family of calculations bound to the already-admitted Market Measure / Calculated Market Measure umbrella (§4); no Ledger, Portfolio, or Wealth subject |
| Permitted inputs | Pass | Declared input-category closure is limited to M39 Observation evidence, Asset Foundation reference data, invocation parameters, and governed calculation dependencies — the frozen M40 four-category closure |
| Output meaning | Pass | Output meaning is limited to identifying which Market Measure/Calculated Market Measure concept a Method Version realizes, its subject shape, and its output coordinate meaning — no correctness, trust, or recommendation claim |
| Prohibited Ledger/Portfolio/Wealth inputs | Pass | Forbidden-inputs field expressly excludes Ledger, Portfolio, Wealth, judgment, and evaluation meaning |
| Prohibited judgment semantics | Pass | No forecast, recommendation, signal, consensus, action intent, evaluator verdict, trust score, correctness confidence, or quality ranking appears in the proposed exact definition |

**Overlap analysis:** `GLOSSARY.md` contains **Definition Version**
("one immutable published state of an asset definition," owned by Asset
Foundation) at `GLOSSARY.md#definition-version`. This is a structurally
similar but semantically and ownership-distinct concept: Definition Version
versions an *Asset's* definition; Market Measure Definition versions a
*calculation family's* specification. To avoid the exact naming confusion
the independent review's §6.2 hidden-risk table flagged ("Framework
Definition identity is confused with Asset Definition identity"), this
candidate is registered only under the full compound name **Market Measure
Definition**, never bare "Definition," and its future contract text MUST NOT
abbreviate the name. `GLOSSARY.md` also contains **Asset Definition**
(`GLOSSARY.md#asset-definition` — "the declarative behavior contract of an
asset class," Asset Foundation). Both are declarative, closed-vocabulary
"Definition" contracts, but they describe different subjects with different
owners: an Asset Definition states what an *asset class* is and supports
(unit semantics, valuation cadence, flow types, lifecycle) so engines can
branch on capability rather than type; a Market Measure Definition states
what a *family of calculations* claims to compute (subject shape, output
coordinate meaning, permitted inputs) so a Method Version has exactly one
specification it realizes. A Market Measure Definition references an Asset
Definition's declared Valuation Semantics or capabilities only as a
Method Requirement prerequisite (§6.3); it never redeclares or reinterprets
Asset Definition vocabulary. No collision with either existing entry.

**Canonical reuse analysis:** No existing canonical term covers this
meaning. Market Measure and Calculated Market Measure (M40, effective) name
the descriptive-fact category; neither names the versioned specification
record a Method Version implements. This is a genuinely new concept, not a
duplicate.

**Negative corpus analysis:** Does not reintroduce Calculation Temporal
Claim, a generic Analysis domain, a composite Instrument Analysis authority,
a portfolio-measurement owner, an Investment Judgment/recommendation/
strategy layer, or an execution/transaction/trading authority. No overlap
with the negative corpus.

**V1–V3 disposition:** V1 (one term, one meaning, one home) satisfied under
the full compound name with Market Intelligence as sole owner. V2
(same-change synchronization) is deferred to stage 5 and not performed by
this register. V3 (constitutional-term reservation) satisfied — the name is
not currently reserved and does not collide with a reserved term.

**M34/M39/M40 compatibility:** Compatible with `M34-D-0010` (descriptive
market facts separate from judgment/evaluation/presentation). Does not touch
`M34-D-0004` or `M34-D-0005` directly (no temporal-claim field of its own;
temporal claim belongs to the Result, §6.6). Builds strictly inside the M40
Market Measure / Calculated Market Measure umbrella without reinterpreting
either.

**Disposition request:** `ADMIT`.

**Glossary synchronization requirement:** If confirmed `ADMIT`, add a
`GLOSSARY.md` entry titled "Market Measure Definition" (never abbreviated),
cross-linking Market Measure, Calculated Market Measure, and Definition
Version with an explicit non-collision note, in the same change the
confirmation is recorded.

**Future contract acceptance evidence:** Once independently confirmed,
M41-WP1's contract text must supply the exact subject-shape vocabulary, the
exact output-coordinate-meaning vocabulary, and a worked example
distinguishing a Market Measure Definition from an Asset Definition Version.
This is WP1's own future contract-review obligation, not a precondition for
this candidate's present disposition.

---

### 6.2 Method Version

**Purpose:** Identify one immutable, version-controlled computational
specification — semantic rules, not code or a formula — admissible under
exactly one Market Measure Definition, and the unit a future method-admission
gate operates on.

**Owner:** Market Intelligence.

**Non-owner:** Asset Foundation, Ledger & Accounting, Portfolio Intelligence,
Decision Intelligence, Trust & Evaluation, Wealth Intelligence, Experience
Platform, providers, storage, and runtime mechanisms.

**Permitted inputs:**

- exactly one Market Measure Definition reference (§6.1);
- an explicit semantic version identifier;
- explicit declared dependency versions; and
- an explicit declared Method Requirement set (§6.3).

**Forbidden inputs:**

- executable code, a formula body, or a named indicator implementation;
- any production-admission act (M41 proposal §7 — specifying the
  method-admission mechanism is not exercising it);
- ambient time, randomness, or mutable process state; and
- any Ledger, Portfolio, Wealth, judgment, or evaluation meaning.

**Proposed exact definition:** A Method Version is an immutable,
version-identified specification record binding to exactly one Market
Measure Definition, declaring its semantic version, its dependency versions,
and its Method Requirement set. It is the version-controlled unit a future,
separately chartered method-admission mechanism would evaluate for
admission. It admits no concrete formula or production method.

**Constitutional constraints:**

- It MUST bind to exactly one Market Measure Definition; it MUST NOT bind to
  more than one, and it MUST NOT exist without one.
- It MUST NOT itself constitute a production-method admission (M41 proposal
  §7, §12).
- Every declared dependency MUST be explicit and version-bound, consistent
  with the Deterministic Calculation property already admitted by M40
  (`GLOSSARY.md#deterministic-calculation`).
- It MUST NOT introduce a second, competing versioning scheme against the
  existing Asset Foundation Definition Version — the two version axes
  govern different subjects (a calculation specification vs. an Asset
  definition) and MUST remain independently referenced, never conflated.

**Five-part ownership-boundary gate (current):**

| Part | Result | Reasoning |
| --- | --- | --- |
| Permitted subject | Pass | Subject is a version-identified calculation specification bound to exactly one Market Measure Definition; no Ledger, Portfolio, or Wealth subject |
| Permitted inputs | Pass | Inputs are limited to a Market Measure Definition reference, a semantic version identifier, declared dependency versions, and a declared Method Requirement set |
| Output meaning | Pass | Output meaning is limited to identity, versioning, and dependency/requirement declaration of a calculation specification — no correctness, trust, or recommendation claim |
| Prohibited Ledger/Portfolio/Wealth inputs | Pass | Forbidden-inputs field expressly excludes Ledger, Portfolio, Wealth, judgment, and evaluation meaning |
| Prohibited judgment semantics | Pass | No forecast, recommendation, signal, consensus, action intent, evaluator verdict, trust score, correctness confidence, or quality ranking appears in the proposed exact definition |

**Overlap analysis:** Structurally analogous to but ownership-distinct from
`GLOSSARY.md#definition-version` (Asset Foundation, versions an Asset
definition). No name collision — "Method Version" is not "Definition
Version" — but the future contract text MUST state the non-conflation rule
explicitly, per the independent review's §6.2 hidden-risk table. No other
`GLOSSARY.md` entry overlaps.

**Canonical reuse analysis:** No existing canonical term covers this
meaning. Deterministic Calculation (M40, effective) names the reproducibility
property a Method Version must satisfy; it does not name the versioned
specification record itself.

**Negative corpus analysis:** No overlap with the M39/M40 negative corpus.

**V1–V3 disposition:** V1 satisfied — one term, one meaning, one home
(Market Intelligence), disambiguated from Definition Version. V2 deferred to
stage 5. V3 satisfied — no reserved-term collision.

**M34/M39/M40 compatibility:** Compatible with `M34-D-0010`. Preserves the
frozen M40 Deterministic Calculation property (`GLOSSARY.md#deterministic-calculation`)
as a requirement a Method Version must satisfy, without redefining that
term.

**Disposition request:** `ADMIT`.

**Glossary synchronization requirement:** If confirmed `ADMIT`, add a
`GLOSSARY.md` entry titled "Method Version," cross-linking Market Measure
Definition, Deterministic Calculation, and Definition Version with an
explicit non-conflation note, in the same change the confirmation is
recorded.

**Future contract acceptance evidence:** Once independently confirmed,
M41-WP1's contract text must supply the exact version-identifier format,
the exact dependency-declaration format, and a worked example showing a
Method Version bound to a Market Measure Definition. This is WP1's own
future contract-review obligation, not a precondition for this candidate's
present disposition.

---

### 6.3 Method Requirement

**Purpose:** State one declared prerequisite condition a Method Version's
applicability depends on — the "Applicability" contract named in M41
proposal §4 and §6 — distinct from the invocation-time Input Sufficiency
check M40 already admitted.

**Owner:** Market Intelligence.

**Non-owner:** Asset Foundation, Ledger & Accounting, Portfolio Intelligence,
Decision Intelligence, Trust & Evaluation, Wealth Intelligence, Experience
Platform, providers, storage, and runtime mechanisms.

**Permitted inputs:**

- an explicit reference to the Method Version it constrains (§6.2);
- an explicit declared prerequisite category (subject shape, dependency
  presence, Observation category availability); and
- an explicit, deterministic evaluation rule for the prerequisite.

**Forbidden inputs:**

- correctness, reliability, reputation, confidence, or evaluator judgment;
- portfolio suitability or user preference;
- an implicit default, heuristic, or best-effort substitution; and
- any input the frozen M40 four-category permitted-input closure does not
  cover.

**Proposed exact definition:** A Method Requirement is an explicit, declared
prerequisite condition specified at Method Version definition time that must
hold for that Method Version to be applicable to a given Measure Subject and
Observation Input Manifest. It is evaluated deterministically against the
declared condition and produces no correctness, quality, or judgment
meaning.

**Constitutional constraints:**

- It MUST be declared at specification time, not inferred at invocation
  time.
- It MUST NOT be confused with or substitute for Input Sufficiency
  (`GLOSSARY.md`, M40, evaluated at invocation time against exact supplied
  inputs) — the two are orthogonal: Method Requirement states what a
  Method Version needs in principle; Input Sufficiency states whether one
  exact invocation's supplied inputs satisfy it.
- It MUST fail closed: an unmet Method Requirement MUST prevent the Method
  Version from being applicable, never trigger a fallback.

**Five-part ownership-boundary gate (current):**

| Part | Result | Reasoning |
| --- | --- | --- |
| Permitted subject | Pass | Subject is a declared prerequisite condition on a Method Version's applicability; no Ledger, Portfolio, or Wealth subject |
| Permitted inputs | Pass | Inputs are limited to a Method Version reference, a declared prerequisite category, and a deterministic evaluation rule — within the frozen M40 four-category closure |
| Output meaning | Pass | Output meaning is limited to a deterministic met/unmet result — no correctness, quality, or judgment meaning |
| Prohibited Ledger/Portfolio/Wealth inputs | Pass | Forbidden-inputs field expressly excludes any input outside the frozen four-category closure |
| Prohibited judgment semantics | Pass | Forbidden-inputs field expressly excludes correctness, reliability, reputation, confidence, evaluator judgment, portfolio suitability, and user preference |

**Overlap analysis:** No `GLOSSARY.md` entry with this name exists. The
closest existing term is Input Sufficiency (M40, effective,
`GLOSSARY.md#input-sufficiency`), which this candidate's proposed exact
definition explicitly distinguishes itself from, mirroring the same
distinction M40-WP1 §6.8 already drew between Input Sufficiency and frozen
M39 Semantic Sufficiency. No collision.

**Canonical reuse analysis:** No existing canonical term names a
specification-time applicability prerequisite; Input Sufficiency is
invocation-time and does not cover this meaning.

**Negative corpus analysis:** No overlap with the M39/M40 negative corpus.

**V1–V3 disposition:** V1 satisfied — one term, one meaning, one home,
explicitly disambiguated from Input Sufficiency. V2 deferred to stage 5. V3
satisfied.

**M34/M39/M40 compatibility:** Compatible with `M34-D-0010`. Preserves the
frozen M40 Input Sufficiency meaning without amendment (M40-WP1 §6.8 /
`GLOSSARY.md#input-sufficiency`).

**Disposition request:** `ADMIT`.

**Glossary synchronization requirement:** If confirmed `ADMIT`, add a
`GLOSSARY.md` entry titled "Method Requirement," cross-linking Method
Version and Input Sufficiency with an explicit orthogonality note, in the
same change the confirmation is recorded.

**Future contract acceptance evidence:** Once independently confirmed,
M41-WP1's contract text must supply the closed set of permitted
prerequisite categories and a worked example distinguishing a Method
Requirement from Input Sufficiency. This is WP1's own future
contract-review obligation, not a precondition for this candidate's present
disposition.

---

### 6.4 Measure Subject

**Purpose:** Name the exact, canonical binding of one Market Measure
invocation to one or more Assets or an explicitly defined market context —
the "Subject" M41-WP2 (M41 proposal §6) will bind to exact Asset Foundation
identity and M39 evidence.

**Owner:** Market Intelligence for the Subject-binding contract itself. Asset
Foundation retains sole ownership of the referenced Asset identity,
definition, and classification (§4) — this candidate never re-owns that
meaning.

**Non-owner:** Ledger & Accounting, Portfolio Intelligence, Decision
Intelligence, Trust & Evaluation, Wealth Intelligence, Experience Platform,
providers, storage, and runtime mechanisms. Asset Foundation is a referenced
authority, not a non-owner in the sense of a forbidden domain — it is the
sole owner of the identity this candidate references.

**Permitted inputs:**

- canonical Asset identity and exact Asset Definition Version references
  owned by Asset Foundation, referenced without mutation;
- explicit, measure-declared subject role and ordering; and
- an explicit declared market-context parameter set, when the subject is a
  market context rather than one or more Assets.

**Forbidden inputs:**

- provider-shaped payloads, ticker, or display symbol as canonical identity;
- Ledger, Portfolio, Wealth, judgment, or evaluation meaning; and
- an unresolved or dynamically resolved Asset reference.

**Proposed exact definition:** A Measure Subject is exactly one of the
following three closed subject shapes to which one Market Measure Definition
/ Method Version invocation applies: (1) a single canonical Asset identity
reference; (2) an ordered, canonical reference set of two or more Asset
identities; or (3) an explicit market-context parameter set with no Asset
identity reference. A Measure Subject MUST instantiate exactly one of these
three shapes; a hybrid subject combining Asset identity references with
market-context parameters in the same instance is not a permitted shape and
is outside this candidate's closure. It references Asset Foundation identity
without mutating, deriving, or reinterpreting it, and it carries no ledger,
portfolio, or life-context meaning.

**Constitutional constraints:**

- It MUST reference canonical Asset identity by exact, immutable reference;
  it MUST NOT recreate or shadow Asset identity.
- It MUST be enumerable and canonically orderable for multi-Asset subjects,
  consistent with the Observation Input Manifest's existing ordering
  requirement (`GLOSSARY.md#observation-input-manifest`).
- It MUST NOT become an Asset capability grant, per the independent review's
  §6.2 hidden-risk table ("Applicability becomes an Asset capability
  grant").

**Five-part ownership-boundary gate (current):**

| Part | Result | Reasoning |
| --- | --- | --- |
| Permitted subject | Pass | Subject is a canonical reference set of Asset identities and/or an explicit market-context parameter set; no Ledger, Portfolio, or Wealth subject |
| Permitted inputs | Pass | Inputs are limited to canonical Asset identity/Definition Version references (Asset Foundation), declared subject role/ordering, and declared market-context parameters |
| Output meaning | Pass | Output meaning is limited to an ordered, canonical reference set — no correctness, quality, or judgment meaning |
| Prohibited Ledger/Portfolio/Wealth inputs | Pass | Forbidden-inputs field expressly excludes Ledger, Portfolio, Wealth, judgment, and evaluation meaning |
| Prohibited judgment semantics | Pass | No forecast, recommendation, signal, consensus, action intent, evaluator verdict, trust score, correctness confidence, or quality ranking appears in the proposed exact definition |

**Overlap analysis:** No `GLOSSARY.md` entry with this name exists.
M40-WP1's "permitted inputs" fields use the common noun "subject" generically
(e.g. "explicit subject references," §6.7); this is not a registered term
and creates no collision with the capitalized candidate Measure Subject.

**Canonical reuse analysis:** No existing canonical term covers this exact
meaning; Asset (identity) is reused by reference, not redefined.

**Negative corpus analysis:** No overlap with the M39/M40 negative corpus.

**V1–V3 disposition:** V1 satisfied — one term, one meaning, one home
(Market Intelligence for the binding; Asset Foundation retains identity
ownership by reference). V2 deferred to stage 5. V3 satisfied.

**M34/M39/M40 compatibility:** Compatible with `M34-D-0010`. Preserves
Asset Foundation's frozen identity ownership (§4) without transfer or
mutation.

**Disposition request:** `ADMIT`.

**Glossary synchronization requirement:** If confirmed `ADMIT`, add a
`GLOSSARY.md` entry titled "Measure Subject," cross-linking Asset,
Observation Input Manifest, and Market Measure, in the same change the
confirmation is recorded.

**Future contract acceptance evidence:** Once independently confirmed,
M41-WP2's contract text must supply the exact canonical ordering rule for
multi-Asset subjects and the exact market-context parameter closure. This is
WP2's own future contract-review obligation, not a precondition for this
candidate's present disposition.

---

### 6.5 Measurement Window

**Purpose:** Name the explicit, deterministic temporal boundary over which a
calculation's inputs are evaluated — closing the cutoff/window determinism
choice M41-WP3 (M41 proposal §4, §6) must resolve before any executable
method exists.

**Owner:** Market Intelligence.

**Non-owner:** Asset Foundation, Ledger & Accounting, Portfolio Intelligence,
Decision Intelligence, Trust & Evaluation, Wealth Intelligence, Experience
Platform, providers, storage, and runtime mechanisms.

**Permitted inputs:**

- an explicit start reference, end/cutoff reference, and timezone/calendar
  reference; and
- an explicit reference to the Observation Input Manifest entries the window
  bounds (`GLOSSARY.md#observation-input-manifest`).

**Forbidden inputs:**

- ambient system time, request time, or "latest" as an unresolved reference;
- a presentation label such as "current" in place of an explicit boundary;
  and
- any Ledger, Portfolio, Wealth, judgment, or evaluation meaning.

**Proposed exact definition:** A Measurement Window is an explicit,
deterministic temporal boundary specification — start, end/cutoff, and
timezone/calendar reference — that bounds which Observation Input Manifest
entries a Method Version may draw upon for one invocation. It contains no
ambient or implicit default and is not itself a Canonical Temporal Claim
(`GLOSSARY.md#canonical-temporal-claim`), which remains the Result's field,
not the input-selection boundary's.

**Constitutional constraints:**

- Every boundary field MUST be explicit; no field MAY silently default.
- It MUST NOT be confused with or substitute for the Calculation's own
  Canonical Temporal Claim (§6.9 rejection; the existing, reused term).
- It MUST bound only Observation Input Manifest membership, never redefine
  an Observation's own frozen M39 temporal meaning.

**Five-part ownership-boundary gate (current):**

| Part | Result | Reasoning |
| --- | --- | --- |
| Permitted subject | Pass | Subject is an input-selection temporal boundary bounding Observation Input Manifest membership; no Ledger, Portfolio, or Wealth subject |
| Permitted inputs | Pass | Inputs are limited to an explicit start/end/cutoff reference, timezone/calendar reference, and a reference to the Observation Input Manifest entries bounded |
| Output meaning | Pass | Output meaning is limited to a deterministic temporal boundary — no correctness, quality, or judgment meaning |
| Prohibited Ledger/Portfolio/Wealth inputs | Pass | Forbidden-inputs field expressly excludes Ledger, Portfolio, Wealth, judgment, and evaluation meaning |
| Prohibited judgment semantics | Pass | No forecast, recommendation, signal, consensus, action intent, evaluator verdict, trust score, correctness confidence, or quality ranking appears in the proposed exact definition |

**Overlap analysis:** No `GLOSSARY.md` entry with this name exists. Closest
adjacent terms are Canonical Temporal Claim and Event Type
(`GLOSSARY.md#canonical-temporal-claim`, `GLOSSARY.md#event-type`); this
candidate's proposed exact definition explicitly distinguishes an
input-selection boundary from the Result's own temporal claim. No collision.

**Canonical reuse analysis:** No existing canonical term names a
deterministic input-selection temporal boundary; the existing Canonical
Temporal Claim names a different thing (when the Calculation event occurred
and its Degraded State), reused, not redefined, by this candidate.

**Negative corpus analysis:** No overlap with the M39/M40 negative corpus.
Does not reintroduce Calculation Temporal Claim (§6.9) under a new name —
Measurement Window bounds *input selection*, not the Result's temporal
claim.

**V1–V3 disposition:** V1 satisfied — one term, one meaning, one home,
explicitly disambiguated from Canonical Temporal Claim. V2 deferred to
stage 5. V3 satisfied — Canonical Temporal Claim's reserved fields are not
touched or renamed.

**M34/M39/M40 compatibility:** Compatible with `M34-D-0005` — does not
duplicate or reinterpret the Canonical Temporal Claim grammar; adds a
distinct, narrower input-boundary concept the Result's temporal claim does
not cover.

**Disposition request:** `ADMIT`.

**Glossary synchronization requirement:** If confirmed `ADMIT`, add a
`GLOSSARY.md` entry titled "Measurement Window," cross-linking Observation
Input Manifest and Canonical Temporal Claim with an explicit distinction
note, in the same change the confirmation is recorded.

**Future contract acceptance evidence:** Once independently confirmed,
M41-WP3's contract text must supply the exact calendar/timezone resolution
rule and a golden vector proving no ambient default remains. This is WP3's
own future contract-review obligation, not a precondition for this
candidate's present disposition.

---

### 6.6 Measure Value

**Purpose:** Name the calculated, typed output coordinate a Market Measure
Result carries when Computation Outcome permits — the value coordinate
M41-WP4's Result model (M41 proposal §4, §6) must specify without
introducing a competing axis beside the frozen Outcome/Degraded State
composition.

**Owner:** Market Intelligence.

**Non-owner:** Asset Foundation, Ledger & Accounting, Portfolio Intelligence,
Decision Intelligence, Trust & Evaluation, Wealth Intelligence, Experience
Platform, providers, storage, and runtime mechanisms.

**Permitted inputs:**

- the already-admitted Computation Outcome value
  (`GLOSSARY.md#computation-outcome`), governing whether a value may be
  present;
- an explicit declared type and unit qualification; and
- the Deterministic Calculation that produced it
  (`GLOSSARY.md#deterministic-calculation`).

**Forbidden inputs:**

- a value on any non-`SUCCEEDED` Computation Outcome (the existing
  no-value-on-non-success rule, `GLOSSARY.md#market-measure-result`);
- correctness, trust, quality, or recommendation meaning attached to the
  value; and
- an untyped or unit-unqualified numeric literal.

**Proposed exact definition:** A Measure Value is the exact typed,
unit-qualified value or value set produced by a `SUCCEEDED` Deterministic
Calculation and carried by a Market Measure Result. It is a named coordinate
within the Market Measure Result's already-admitted composition
(`GLOSSARY.md#market-measure-result`), not a new axis beside Computation
Outcome or Degraded State, and it is present only under the existing
no-value-on-non-success rule.

**Constitutional constraints:**

- It MUST be present if and only if Computation Outcome is `SUCCEEDED`.
- It MUST carry an explicit type and unit; it MUST NOT be an untyped
  literal.
- It MUST NOT become a third classification axis beside Computation Outcome
  and Degraded State, per the independent review's §6.2 hidden-risk table
  ("`State` becomes a third axis beside Outcome and Degraded State").
- It MUST NOT assert correctness, trust, or recommendation meaning.

**Five-part ownership-boundary gate (current):**

| Part | Result | Reasoning |
| --- | --- | --- |
| Permitted subject | Pass | Subject is the typed, unit-qualified value coordinate of a Market Measure Result; no Ledger, Portfolio, or Wealth subject |
| Permitted inputs | Pass | Inputs are limited to the already-admitted Computation Outcome, an explicit type/unit qualification, and the Deterministic Calculation that produced it |
| Output meaning | Pass | Output meaning is limited to an exact typed, unit-qualified value or value set — no correctness, trust, or recommendation meaning |
| Prohibited Ledger/Portfolio/Wealth inputs | Pass | Forbidden-inputs field expressly excludes any value on non-`SUCCEEDED` Computation Outcome and any Ledger, Portfolio, or Wealth meaning |
| Prohibited judgment semantics | Pass | Forbidden-inputs field expressly excludes correctness, trust, quality, or recommendation meaning attached to the value |

**Overlap analysis:** No `GLOSSARY.md` entry with this name exists. Market
Measure Result (`GLOSSARY.md#market-measure-result`) already states "It
contains required calculated values only for `SUCCEEDED`" without naming the
value coordinate itself; this candidate names that coordinate precisely
without altering Market Measure Result's existing composition. No collision.
`GLOSSARY.md` also contains **Unit Semantics** (`GLOSSARY.md#unit-semantics`
— "how a kind is counted," Asset Foundation) and **Valuation Semantics**
(`GLOSSARY.md#valuation-semantics` — "what question, if any, establishes a
kind's worth," Asset Foundation). Both are declarative axes an Asset
Definition states exist; neither computes or carries a calculated value.
Measure Value is the calculated, typed, unit-qualified output a Method
Version produces when it answers the valuation or other question Asset
Foundation's Definition declares — it reuses Unit Semantics' unit
vocabulary by reference and never restates or reinterprets the arithmetic
Valuation Semantics deliberately withholds. No collision; the future
contract text MUST reference, not redefine, either term.

**Canonical reuse analysis:** Market Measure Result and Computation Outcome
are reused with their frozen meaning; neither names the value coordinate
itself, which is the gap this candidate closes.

**Negative corpus analysis:** No overlap with the M39/M40 negative corpus.

**V1–V3 disposition:** V1 satisfied — one term, one meaning, one home,
explicitly scoped as a coordinate within Market Measure Result, not a new
axis. V2 deferred to stage 5. V3 satisfied — Computation Outcome and
Degraded State's reserved meanings are not altered.

**M34/M39/M40 compatibility:** Compatible with `M34-D-0005` and
`M34-D-0010`. Preserves the frozen Market Measure Result composition
(M40-WP1 §6.7 / `GLOSSARY.md#market-measure-result`) without amendment.

**Disposition request:** `ADMIT`.

**Glossary synchronization requirement:** If confirmed `ADMIT`, add a
`GLOSSARY.md` entry titled "Measure Value," cross-linking Market Measure
Result and Computation Outcome with an explicit no-new-axis note, in the
same change the confirmation is recorded.

**Future contract acceptance evidence:** Once independently confirmed,
M41-WP4's contract text must supply the exact canonical serialization rule
for typed/unit-qualified values and a worked example of the
no-value-on-non-success rule. This is WP4's own future contract-review
obligation, not a precondition for this candidate's present disposition.

---

### 6.7 Observation Input Manifest — `REUSE`

**Purpose (of this register entry):** Record, per M41 proposal §8 stage 1,
that Observation Input Manifest is not a new M41 candidate.

**Owner:** Market Intelligence (unchanged, frozen at M40).

**Non-owner:** Not applicable — reuse of a frozen M40 term; this entry does
not reopen or reassign ownership. The frozen non-owner set from
[M40-WP1 §6.6](M40_WP1_Canonical_Market_Measure_Vocabulary_and_Ownership_Specification.md#66-observation-input-manifest)
remains unchanged.

**Permitted inputs:** Not applicable — reuse; the frozen M40 permitted-input
closure for Observation Input Manifest is unchanged and is not restated or
reinterpreted here.

**Forbidden inputs:** Not applicable — reuse; the frozen M40 forbidden-input
set for Observation Input Manifest is unchanged and is not restated or
reinterpreted here.

**Constitutional constraints:** Not applicable for new constraints — this
entry adds none. The single applicable constraint is that M41-WP2 MUST cite
`GLOSSARY.md#observation-input-manifest` directly and MUST NOT redefine,
narrow, or widen its frozen M40 meaning.

**Proposed exact definition:** Not applicable — this entry proposes no new
definition. Observation Input Manifest is already an effective `GLOSSARY.md`
entry (`GLOSSARY.md#observation-input-manifest`), one of M40's eight
admissions, defined in full at
[M40-WP1 §6.6](M40_WP1_Canonical_Market_Measure_Vocabulary_and_Ownership_Specification.md#66-observation-input-manifest).

**Overlap analysis:** Full overlap — this is the same term, not a candidate
specialization.

**Canonical reuse analysis:** Fully covered by the existing entry. M41-WP2
binds to its frozen meaning without modification (M41 proposal §8, RC-1).

**Negative corpus analysis:** Not applicable — reuse, not a new admission.

**V1–V3 disposition:** V3 requires this: Observation Input Manifest is
constitutional, reserved vocabulary. Re-registering it would itself be a V1/
V3 defect (the exact RC-1 finding).

**M34/M39/M40 compatibility:** Fully compatible — this is the frozen M40
meaning, unmodified.

**Disposition request:** `REUSE`.

**Glossary synchronization requirement:** None. No `GLOSSARY.md` change.
M41-WP2's future contract text cites `GLOSSARY.md#observation-input-manifest`
directly.

**Five-part ownership-boundary gate (current):** Not applicable — reuse of
an already-admitted, already-gated M40 term; this entry re-applies no new
gate.

**Future contract acceptance evidence:** None beyond the existing M40
admission record. M41-WP2 must cite, not redefine, the existing entry.

---

### 6.8 Provenance — `REUSE`

**Purpose (of this register entry):** Record, per M41 proposal §8 stage 1,
that Provenance is not a new M41 candidate.

**Owner:** Connectivity & Ingestion owns "Provenance at the moment of
capture" (Platform Architecture §6.4, "Owns" clause). This is the exact
existing canonical ownership rule this entry traces to; it is cited, not
created, transferred, or redefined by this register. Once captured,
Provenance is carried forward immutably by whichever domain's record holds
it (Law 2, Platform Architecture) — carrying a fact's provenance forward is
custody, not a competing ownership claim over what Provenance means or where
it originates.

**Non-owner:** Market Intelligence, Asset Foundation, Ledger & Accounting,
Portfolio Intelligence, Decision Intelligence, Trust & Evaluation, Wealth
Intelligence, and Experience Platform may carry, cite, or display a record's
Provenance field; none of them may define, capture, or reinterpret it. M41's
Market Intelligence domain is a carrier of Provenance on its own records,
not the term's owner.

**Permitted inputs:** Not applicable — reuse; Provenance's frozen scope
(source, time, adapter, per `GLOSSARY.md#provenance`) is unchanged and is
not restated or reinterpreted here.

**Forbidden inputs:** Not applicable — reuse; this entry does not narrow or
widen what Provenance may carry.

**Constitutional constraints:** Not applicable for new constraints — this
entry adds none. The single applicable constraint is that M41-WP4 MUST cite
`GLOSSARY.md#provenance` directly and MUST NOT redefine it or reassign its
capture-time ownership away from Connectivity & Ingestion.

**Proposed exact definition:** Not applicable — this entry proposes no new
definition. Provenance is already an effective `GLOSSARY.md` entry
(`GLOSSARY.md#provenance`: "Where a fact came from. Every ingested event
records its source, time, and adapter. Preserved forever.").

**Overlap analysis:** Full overlap — this is the same term, not a candidate
specialization. If M41-WP4's future Result model needs a narrower lineage
structure than the existing entry provides, that narrower structure MUST be
registered as its own candidate specialization in a future work-package
register addendum, with its own overlap and V3 proof that it refines rather
than redefines Provenance (M41 proposal §8, RC-1) — no such specialization
is proposed by this register.

**Canonical reuse analysis:** Fully covered by the existing entry. M41-WP4
binds to its frozen meaning without modification.

**Negative corpus analysis:** Not applicable — reuse, not a new admission.

**V1–V3 disposition:** V1 satisfied — one term, one meaning, one home
(Connectivity & Ingestion, at capture time). V3 requires this: Provenance is
pre-existing, foundational, reserved vocabulary under Platform Architecture
V3. Re-registering it would itself be a V1/V3 defect (the exact RC-1
finding).

**M34/M39/M40 compatibility:** Fully compatible — unmodified pre-existing
meaning.

**Disposition request:** `REUSE`.

**Glossary synchronization requirement:** None. No `GLOSSARY.md` change.
M41-WP4's future contract text cites `GLOSSARY.md#provenance` directly.

**Five-part ownership-boundary gate (current):** Not applicable — reuse of
pre-existing, foundational vocabulary; this entry re-applies no new gate.

**Future contract acceptance evidence:** None beyond the existing entry.
M41-WP4 must cite, not redefine, Provenance.

---

### 6.9 Calculation Temporal Claim — `REJECT` (carried forward)

**Purpose (of this register entry):** Record, per M41 proposal §8 stage 1,
that Calculation Temporal Claim remains rejected and is not reintroduced
under any name.

**Owner:** Not applicable — rejected candidate.

**Non-owner:** Not applicable — rejected candidate; no ownership question
arises because no term is admitted.

**Permitted inputs:** Not applicable — rejected candidate.

**Forbidden inputs:** Not applicable — rejected candidate.

**Constitutional constraints:** Not applicable for the rejected candidate
itself. The single applicable constraint is that no future M41 artifact may
reintroduce Calculation Temporal Claim, or an equivalent specialization,
under any name — the meaning remains fully covered by reusing Canonical
Temporal Claim qualified by Event Type `Calculation` and Producing Domain
`Market Intelligence`.

**Proposed exact definition:** Not applicable — no definition is proposed.
Calculation Temporal Claim was proposed as a candidate specialization by
M40-WP1 §6.4 and rejected by M40-WP2
([M40-WP2 Vocabulary Admission Review](M40_WP2_Canonical_Market_Measure_Vocabulary_Admission_Review.md))
in favor of the existing Canonical Temporal Claim
(`GLOSSARY.md#canonical-temporal-claim`) qualified by Event Type
`Calculation` and Producing Domain `Market Intelligence`
(`GLOSSARY.md#producing-domain`).

**Overlap analysis:** Full overlap with the existing, effective Canonical
Temporal Claim and Producing Domain entries — this is precisely why the
candidate was rejected rather than admitted.

**Canonical reuse analysis:** The concept the rejected candidate attempted
to name is fully covered by reusing Canonical Temporal Claim, qualified by
Event Type `Calculation` and Producing Domain `Market Intelligence`. M41's
Result model (WP4, §6.6 of this register) uses exactly this reused
construction and creates no new term for it.

**Negative corpus analysis:** This is the negative corpus entry itself.
Every other candidate in this register was checked against it (§8 below).

**V1–V3 disposition:** V1/V3 required the rejection — admitting a duplicate
specialization would have created two homes for one meaning.

**M34/M39/M40 compatibility:** The rejection preserves, rather than weakens,
`M34-D-0005`'s existing Canonical Temporal Claim grammar.

**Disposition request:** `REJECT` (carried forward, not re-decided; no new
review of this disposition is requested).

**Glossary synchronization requirement:** None. No `GLOSSARY.md` change.

**Five-part ownership-boundary gate (current):** Not applicable — rejected
candidate; no gate is applied to a term that is not being admitted.

**Future contract acceptance evidence:** Not applicable — rejected.

## 7. Overlap Analysis Summary

| Candidate | Nearest existing `GLOSSARY.md` entry | Collision risk | Resolution |
| --- | --- | --- | --- |
| Market Measure Definition | Definition Version (Asset Foundation); Asset Definition (Asset Foundation) | Name-adjacency only; different subject and owner | Full compound name required; never abbreviated to "Definition"; explicit subject/owner distinction from Asset Definition (§6.1) |
| Method Version | Definition Version (Asset Foundation); Deterministic Calculation | Structural analogy only; different subject and owner | Explicit non-conflation statement required in future contract text |
| Method Requirement | Input Sufficiency (M40, effective) | Conceptual adjacency (both gate applicability/sufficiency) | Explicit orthogonality statement in proposed exact definition (§6.3) |
| Measure Subject | none (generic noun "subject" used informally elsewhere) | None | No resolution required beyond capitalization discipline |
| Measurement Window | Canonical Temporal Claim, Event Type | Conceptual adjacency (both temporal) | Explicit distinction: input-selection boundary vs. Result's own temporal claim |
| Measure Value | Market Measure Result, Computation Outcome, Unit Semantics (Asset Foundation), Valuation Semantics (Asset Foundation) | Conceptual adjacency (value is a Result coordinate; declarative axes it reuses by reference) | Explicit no-new-axis statement in proposed exact definition (§6.6); reference-not-redefine statement for Unit/Valuation Semantics |
| Observation Input Manifest | Observation Input Manifest (M40, effective) | Full overlap — same term | `REUSE`, cite directly |
| Provenance | Provenance (pre-existing) | Full overlap — same term | `REUSE`, cite directly |
| Calculation Temporal Claim | Canonical Temporal Claim, Producing Domain | Full overlap — this is the rejected duplicate | `REJECT`, carried forward |

No candidate in this register duplicates an existing `GLOSSARY.md` meaning
without disclosure. Every adjacency identified above is resolved by an
explicit distinguishing statement inside the candidate's own proposed exact
definition, not left implicit.

## 8. Negative Corpus Analysis

The frozen M39/M40 negative corpus consists of: Calculation Temporal Claim
(rejected, §6.9); M40's Producing Domain specialization (rejected); a
generic Analysis domain; a composite Instrument Analysis authority; a
portfolio-measurement owner; an Investment Judgment/recommendation/strategy
layer; and an execution/transaction/trading authority (M41 proposal §7,
§10).

Each of the six new candidates (§6.1–§6.6) was individually checked against
every item in this list in its own "Negative corpus analysis" field above.
None reintroduces any negative-corpus item under any name:

- none names or re-specializes a temporal claim outside the existing
  Canonical Temporal Claim / Producing Domain grammar (Measurement Window is
  explicitly scoped as an input-selection boundary, not a temporal-claim
  specialization);
- none creates a generic Analysis domain, a composite Instrument Analysis
  authority, or a portfolio-measurement owner;
- none carries judgment, recommendation, or strategy meaning; and
- none carries execution, transaction, or trading authority.

This satisfies the M41 proposal §10 mitigation: *"Each WP's validation step
checks against the M40 negative corpus before independent review is
requested."*

## 9. Constitutional Compatibility

| Authority | Compatibility finding |
| --- | --- |
| Platform Architecture §11 (Architecture Governance) | This register grants no operational authority; it is a Technical Design Document input, consistent with G5 |
| Platform Architecture §12 V1 (one term, one meaning, one home) | Satisfied for all nine entries — see §7 |
| Platform Architecture §12 V2 (same-change synchronization) | Not yet applicable — deferred to stage 5 (synchronization) for each `ADMIT`/`RENAME` disposition; no synchronization is performed by this register |
| Platform Architecture §12 V3 (constitutional terms reserved) | Satisfied — no reserved term is redefined; Observation Input Manifest, Provenance, Canonical Temporal Claim, and Producing Domain are reused or left untouched |
| `M34-D-0004` | Not directly engaged by this register; no candidate alters temporal-claim authority patterns |
| `M34-D-0005` | Compatible — Measurement Window is explicitly distinguished from the Canonical Temporal Claim grammar it governs; Calculation Temporal Claim's rejection is preserved |
| `M34-D-0010` | Compatible — every candidate is descriptive market/calculation meaning, excluded from judgment, evaluation, and presentation authority |
| Frozen M39 corpus | Compatible — no candidate reinterprets M39 Observation meaning; Measure Subject and Measurement Window reference M39 evidence only by exact frozen identity |
| Frozen M40 corpus | Compatible — every candidate builds strictly inside the eight admitted M40 terms without reopening any of them; §4's ownership baseline is inherited unchanged |

## 10. Ownership Singularity Verification

| Term | Sole proposed owner | Verified non-overlapping with |
| --- | --- | --- |
| Market Measure Definition | Market Intelligence | Asset Foundation (Definition Version), Ledger & Accounting, Portfolio Intelligence, Decision Intelligence, Trust & Evaluation, Wealth Intelligence, Experience Platform |
| Method Version | Market Intelligence | Same set as above |
| Method Requirement | Market Intelligence | Same set as above; also non-overlapping with Trust & Evaluation's correctness/quality meaning |
| Measure Subject | Market Intelligence (binding); Asset Foundation (referenced identity, unchanged) | Ledger & Accounting, Portfolio Intelligence, Decision Intelligence, Trust & Evaluation, Wealth Intelligence, Experience Platform |
| Measurement Window | Market Intelligence | Same set as above |
| Measure Value | Market Intelligence | Same set as above; also non-overlapping with Trust & Evaluation |
| Observation Input Manifest | Market Intelligence (frozen, M40) | Unchanged; reused |
| Provenance | Connectivity & Ingestion (capture-time; Platform Architecture §6.4) | Unchanged; reused |
| Calculation Temporal Claim | Not applicable — rejected | Not applicable |

No entry in this register produces shared, ambiguous, or dual ownership.
Every candidate resolves to exactly one owner or a `REUSE`/`REJECT`
disposition that creates no new ownership at all.

## 11. Disposition Summary

| Term | Disposition request | Next stage |
| --- | --- | --- |
| Market Measure Definition | `ADMIT` | Independent Confirmation (stage 4) |
| Method Version | `ADMIT` | Independent Confirmation (stage 4) |
| Method Requirement | `ADMIT` | Independent Confirmation (stage 4) |
| Measure Subject | `ADMIT` | Independent Confirmation (stage 4) |
| Measurement Window | `ADMIT` | Independent Confirmation (stage 4) |
| Measure Value | `ADMIT` | Independent Confirmation (stage 4) |
| Observation Input Manifest | `REUSE` | Independent Confirmation (stage 4) confirms no re-admission occurred |
| Provenance | `REUSE` | Independent Confirmation (stage 4) confirms no re-admission occurred |
| Calculation Temporal Claim | `REJECT` (carried forward) | Independent Confirmation (stage 4) confirms the rejection is not reopened |

No disposition in this table is final. Per M41 proposal §8, every
disposition — including the two `REUSE` entries and the carried-forward
`REJECT` — must complete stage 2 (Independent Review, complete —
[M41_WP1_INDEPENDENT_REVIEW.md](M41_WP1_INDEPENDENT_REVIEW.md)), stage 3
(Required Corrections, complete in this revision — see
[M41_WP1_REQUIRED_CORRECTIONS_RESPONSE.md](M41_WP1_REQUIRED_CORRECTIONS_RESPONSE.md)),
and stage 4 (Independent Confirmation, not yet performed) before stage 5
(synchronization and downstream reliance).

## 12. Glossary Synchronization Requirements

No `GLOSSARY.md` edit is made by this register. Per the M41 proposal §8
stage 5 and this register's §2.2 admission boundary, synchronization occurs
only after independent confirmation, in the same change the confirmation is
recorded:

- Six potential new entries are named for future synchronization, contingent
  on confirmed `ADMIT`: Market Measure Definition, Method Version, Method
  Requirement, Measure Subject, Measurement Window, Measure Value — each
  with the exact cross-linking note specified in its §6 entry.
- No entry is created for Observation Input Manifest or Provenance
  (`REUSE`) — future contract text cites the existing entries directly.
- No entry is created for Calculation Temporal Claim (`REJECT`) — the
  rejection remains recorded in the M40 corpus and is not re-decided here.

## 13. Candidate-Admission Evidence and Future Contract Evidence (Summary)

Two distinct evidence categories apply, and this register's own candidate
disposition depends only on the first:

**Candidate-admission evidence (present, this register).** Each `ADMIT`
candidate's five-part ownership-boundary gate result, recorded now in its
§6 entry, is the evidence this register's independent review and
confirmation evaluate. Every `ADMIT` candidate passes all five parts at the
candidate level (§6.1–§6.6).

**Future contract acceptance evidence (later, per work package).** Once a
candidate is independently confirmed, its owning work package's future
contract text must additionally supply the specific evidence named in its
§6 "Future contract acceptance evidence" field:

1. the exact vocabulary or format the candidate's proposed exact definition
   leaves at the specification level (subject-shape vocabulary,
   version-identifier format, prerequisite category closure, ordering rule,
   calendar/timezone resolution rule, or serialization rule, as applicable);
2. at least one worked example or golden vector demonstrating the
   candidate's constitutional constraints hold; and
3. the frozen M40 five-part ownership-boundary gate (M41 proposal §8)
   applied again to the contract's concrete fields.

This future evidence is a work-package obligation for whichever WP later
relies on the confirmed candidate. It does not gate this register's present
disposition, and this register does not defer its own candidate-level gate
result to that future text.

## 14. Acceptance Criteria for This Register

This register is complete for independent confirmation only when:

1. every noun M41 is currently known to require, across the full WP1–WP4
   scope (not only the architecture's illustrative six examples), is
   accounted for in the §6.0 complete noun inventory — as an `ADMIT`
   candidate, a `REUSE`, a `REJECT`, ordinary non-canonical contract
   language, or explicitly outside M41;
2. each of the nine full-record entries (§6.1–§6.9) contains every §5
   Register Record Field, with an explicit reason wherever a `REUSE`/`REJECT`
   entry marks a field not applicable;
3. each entry has exactly one proposed owner, traced to an exact existing
   canonical authority where reused, or an explicit `REUSE`/`REJECT`
   disposition creating no new ownership;
4. each entry's overlap analysis checks every plausibly colliding existing
   `GLOSSARY.md` entry, not only exact-name matches;
5. each entry's negative corpus analysis checks every item in the frozen
   M39/M40 negative corpus;
6. each entry's V1–V3 disposition and M34/M39/M40 compatibility analysis is
   explicit, not assumed;
7. each `ADMIT` candidate's five-part ownership-boundary gate result is
   recorded now, at the candidate level, separate from any future
   work-package contract-acceptance evidence;
8. no `GLOSSARY.md` edit, Decision Log entry, or Graphify refresh is made by
   this register; and
9. no M41-WP1 Definition, Method Version, or Applicability contract text is
   written by this register — that specification begins only after this
   register is independently reviewed, corrected if required, and
   independently confirmed. Independent confirmation is always required
   before downstream reliance; required corrections is the only conditional
   stage.

Completion of these criteria means this register has completed stages 1–3
of the five-stage workflow (Candidate Vocabulary Register, Independent
Review, Required Corrections) and is ready for stage 4 (Independent
Confirmation). It does not mean any candidate is canonical, admitted, or
reliable by any downstream artifact — that requires a separate Independent
Confirmation document.

## 15. Authority Non-Leakage

This register:

- creates no formula, indicator, or production-method authority;
- admits no candidate term — every disposition remains a request pending
  independent review and confirmation;
- creates no implementation, runtime, provider, persistence, API, or
  public-exposure authority;
- creates no portfolio, judgment, evaluation, recommendation, execution,
  transaction, authorization, or approval authority;
- does not amend `GLOSSARY.md`, the Decision Log, the frozen M39/M40 corpus,
  or any other frozen milestone; and
- does not begin M41-WP1's Definition, Method Version, or Applicability
  contract specification, M41-WP2, M41-WP3, or M41-WP4.

No statement in this register SHALL be used as authority to create a file
outside documentation, to alter `GLOSSARY.md`, or to alter runtime behavior.

## 16. Validation Performed

- **Markdown structure:** Heading hierarchy is sequential (H1, then H2
  `## 1.` through `## 17.`, with H3 `### 6.0`–`### 6.9` nested only under
  `## 6.`), with no skipped or duplicated levels.
- **Repository consistency:** Every `GLOSSARY.md` cross-reference in §6–§10
  was checked against the current `GLOSSARY.md` content (Market Measure,
  Calculated Market Measure, Computation Outcome, Observation Input
  Manifest, Market Measure Result, Input Sufficiency, Deterministic
  Calculation, Mechanical Boundary Rules, Provenance, Canonical Temporal
  Claim, Event Type, Producing Domain, Degraded State, Definition Version,
  Asset Definition, Unit Semantics, Valuation Semantics) and matches the
  exact current entry text, not a paraphrase from an intermediate draft.
- **Platform Architecture cross-check:** Provenance's traced ownership
  ("Connectivity & Ingestion... Provenance at the moment of capture") was
  checked against the current text of Platform Architecture §6.4.
- **Candidate coverage completeness:** §6.0's inventory was cross-checked
  against M41 Architecture Proposal §6, §7, and §8, and against the M40
  planning corpus, to confirm every named noun (including Applicability,
  canonical serialization, equivalence/conflict disposition, manifest
  identity, Result identity, the interaction matrix, the reserved Snapshot
  boundary, Measure Invocation, Dependency Manifest, and narrower Measure
  Provenance) is classified.
- **Five-part gate completeness:** Each of the six `ADMIT` candidates
  (§6.1–§6.6) carries an explicit, current pass/fail result for all five
  gate parts, derived only from that candidate's own §6 fields, not from
  unwritten future contract text.
- **Uniform record completeness:** §6.7, §6.8, and §6.9 were checked field
  by field against §5; every field is present, with an explicit
  not-applicable reason where the entry is a reuse or rejection rather than
  a new proposal.
- **Internal cross references:** All relative links to
  `M41_ARCHITECTURE_PROPOSAL.md`,
  `M41_ARCHITECTURE_INDEPENDENT_REVIEW.md`,
  `M41_ARCHITECTURE_REQUIRED_CORRECTIONS_RESPONSE.md`,
  `M41_ARCHITECTURE_INDEPENDENT_CONFIRMATION.md`,
  `M41_WP1_INDEPENDENT_REVIEW.md`,
  `M41_WP1_REQUIRED_CORRECTIONS_RESPONSE.md`,
  `M40_WP1_Canonical_Market_Measure_Vocabulary_and_Ownership_Specification.md`,
  and `M40_WP2_Canonical_Market_Measure_Vocabulary_Admission_Review.md`
  resolve to files that exist on disk.
- **Terminology consistency:** "Market Measure Definition" and "Method
  Version" are never abbreviated to "Definition" or "Version" anywhere in
  this register, preserving the disambiguation from Asset Foundation's
  Definition Version and Asset Definition required by §7.
- **No contradictory ownership:** §10 confirms every entry resolves to
  exactly one owner — traced to an exact existing canonical authority where
  reused (Provenance → Connectivity & Ingestion) — or a `REUSE`/`REJECT`
  disposition with no new ownership.
- **Unconditional confirmation wording:** The Document role, acceptance
  criterion 9, and §17 Final Disposition were checked to confirm none states
  or implies that independent confirmation is conditional; required
  corrections remains the only conditional stage.
- **`git diff --check`:** Run against this file once staged; no whitespace
  errors found.

## 17. Final Disposition

M41-WP1's Candidate Vocabulary and Ownership Register has completed
independent review (`APPROVED WITH REQUIRED CORRECTIONS`,
[M41_WP1_INDEPENDENT_REVIEW.md](M41_WP1_INDEPENDENT_REVIEW.md)) and this
revision resolves the five required corrections
(see
[M41_WP1_REQUIRED_CORRECTIONS_RESPONSE.md](M41_WP1_REQUIRED_CORRECTIONS_RESPONSE.md)).
It proposes `ADMIT` for six candidates (Market Measure Definition, Method
Version, Method Requirement, Measure Subject, Measurement Window, Measure
Value), `REUSE` for two already-effective terms (Observation Input
Manifest, Provenance), and carries forward one `REJECT` (Calculation
Temporal Claim) without reopening it.

No candidate is canonical. No `GLOSSARY.md` entry is created or modified. No
Decision Log entry is added. No Graphify refresh is performed. No
implementation, runtime, provider, persistence, or API authority is created.
M41-WP1's own Definition, Method Version, and Applicability contract
specification does not begin here — it begins only after this register
completes stage 4 (Independent Confirmation), which has not yet occurred.
Independent confirmation is always required before downstream reliance; it
is not conditional on whether corrections were needed. M41-WP2 is not
begun.
