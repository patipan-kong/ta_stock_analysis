# M40 — Response to Independent Constitutional Architecture Review

**Date:** 2026-07-23

**Document class:** Proposal review response

**Status:** `CORRECTIONS_RECONCILED_PENDING_INDEPENDENT_CONFIRMATION`

**M40 approval state:** `NOT_APPROVED`

**Canonical authority:** `NONE`

**Implementation authority:** `NONE`

**Runtime authority:** `NONE`

**Decision Log status:** `NOT_SUBMITTED`

**Closeout:** `NONE`

**Responding author role:** Original M40 proposal author

**Proposal:** [M40 — Canonical Asset Market Measure Foundation](M40_Canonical_Asset_Market_Measure_Foundation_Plan.md)

**Independent review:** [M40 — Independent Constitutional Architecture Review](M40_INDEPENDENT_CONSTITUTIONAL_ARCHITECTURE_REVIEW.md)

**Normative status:** This response records how the non-canonical M40 proposal
was reconciled with repository-governing review feedback. It does not approve
M40, admit vocabulary, authorize a work package, amend a frozen artifact, or
create implementation, runtime, provider, persistence, public-exposure, or
production-method authority.

---

## 1. Response Summary

All four required corrections are accepted. RC-1 and RC-2 are accepted with
clarification because the proposal's architectural direction was
constitutionally supportable but its proof and terminology were incomplete.
RC-3 and RC-4 are accepted as direct proposal omissions.

| Required correction | Disposition | Prior proposal authority | Result |
| --- | --- | --- | --- |
| RC-1 — Layer ownership reconciliation | `ACCEPTED WITH CLARIFICATION` | Direction present; constitutional proof insufficient | Explicit layer/domain proof and mechanical boundary added |
| RC-2 — Market Observation vs. Calculated Market Measure | `ACCEPTED WITH CLARIFICATION` | Intended event distinction present; frozen-vocabulary reconciliation insufficient | Witnessed Observation Event and platform Calculation refinement added |
| RC-3 — M34-D-0005 temporal/state integration | `ACCEPTED` | Insufficient | Canonical Temporal Claim adopted and `UNAVAILABLE` collision removed |
| RC-4 — WP2 criteria and governing authorities | `ACCEPTED` | Insufficient | Authorities, deliverables, validation, exit criteria, and Definition of Done updated |

No correction changes the milestone title, creates a domain, expands scope, or
authorizes implementation.

---

## 2. RC-1 — Layer Ownership Reconciliation

**Disposition:** `ACCEPTED WITH CLARIFICATION`

### Reviewer concern

The proposal assigned a platform-computed value to Market Intelligence without
expressly reconciling that assignment with the six-layer model, where meaning
derived from observation appears in the Knowledge layer and the layer-to-domain
table assigns Knowledge to Portfolio Intelligence and Wealth Intelligence.

### Constitutional analysis

The concern is valid. The proposal already excluded portfolio, household,
ledger, and judgment meaning and cited Market Intelligence's ownership of
market context, but exclusion alone did not prove layer placement.

Repository authority supports the original direction when the boundary is
stated precisely:

- Platform Architecture section 6.2 assigns valuation over time, regime,
  volatility, breadth, histories, and market context to Market Intelligence.
- Platform Architecture sections 5 and 6.5 assign performance, attribution,
  exposure, portfolio risk, and other portfolio-derived meaning to the
  Knowledge layer and Portfolio Intelligence.
- `M34-D-0010` assigns technical observations and market statistics to Market
  Intelligence while preserving portfolio risk and Investment Judgment under
  their existing owners.
- Law 9 requires one owner and prohibits creating a second implementation or
  overlapping authority.

The constitutional distinction is therefore based on subject, inputs, and
meaning—not merely on whether arithmetic occurred. A calculation describing an
Asset or market context from market evidence may remain Market
Intelligence-owned. A calculation that consumes or interprets holdings, ledger
events, portfolios, households, goals, or life context is outside M40.

### Repository authority cited

- [Platform Architecture §5 and §6](../architecture/platform_architecture.md#5-platform-layers)
- [Platform Architecture §6.2 — Market Intelligence](../architecture/platform_architecture.md#62-market-intelligence)
- [Platform Architecture §6.5 — Portfolio Intelligence](../architecture/platform_architecture.md#65-portfolio-intelligence)
- [M34 Decision Register — M34-D-0010](m34/audit/registers/decision_register.md#m34-d-0010---decompose-the-instrument-analysis-product-contract)

### Proposal change

The proposal now:

- adds the explicit ownership reconciliation to section 2.4;
- adds section 2.6 with a five-part, mechanically testable boundary;
- distinguishes asset/market measures from portfolio and life measures by
  subject, permitted inputs, and output meaning;
- makes failure of that boundary inadmissible to M40; and
- requires WP2 and the Definition of Done to obtain independent approval of the
  layer-ownership proof.

### Rationale

This correction supplies the missing proof while preserving the original
Market Intelligence direction. It neither creates a new domain nor transfers
Portfolio Intelligence or Wealth Intelligence meaning into M40.

---

## 3. RC-2 — Market Observation vs. Calculated Market Measure

**Disposition:** `ACCEPTED WITH CLARIFICATION`

### Reviewer concern

The proposal said a platform-computed statistic is not an Observation Event,
while the frozen Market Observation Glossary entry and `M34-D-0010` include
technical observations and market statistics within Market Intelligence-owned
Market Observations. The proposal did not prove that the new term refined the
frozen boundary without reinterpreting it.

### Constitutional analysis

The proposal intended to distinguish an M39 source-reported Observation Event
from a platform computation. That artifact distinction remains necessary, but
the categorical wording was too broad because it could be read as excluding a
computed market statistic from the frozen Market Observation ownership
surface.

The corrected refinement is:

- a witnessed or provider-reported statistic remains a Market Observation
  represented by M39 Observation semantics and Event Type `Observation`;
- a platform-computed statistic remains Market Intelligence-owned market
  evidence but is represented as a Calculated Market Measure and Event Type
  `Calculation`; and
- neither becomes Investment Judgment.

This adds precision under Governance G2. It does not amend the frozen Glossary,
change `M34-D-0010`, or reclassify an M39 Observation Event.

### Repository authority cited

- [Canonical Glossary — Market Observation](../GLOSSARY.md#market-observation)
- [Canonical Glossary — Event Type](../GLOSSARY.md#event-type)
- [M34 Decision Register — M34-D-0010](m34/audit/registers/decision_register.md#m34-d-0010---decompose-the-instrument-analysis-product-contract)
- [Platform Architecture — Governance G2 and G4](../architecture/platform_architecture.md#11-architecture-governance)
- [Platform Architecture — Vocabulary V1 and V3](../architecture/platform_architecture.md#12-canonical-vocabulary)

### Proposal change

Section 2.2 now states the witnessed-observation/platform-calculation
refinement explicitly. Section 8.9 binds a Calculated Market Measure to Event
Type `Calculation`. WP2 must prove that the refinement preserves the frozen
Market Observation meaning before admitting any vocabulary.

### Rationale

The change removes an apparent vocabulary conflict without weakening M39 or
redesigning the M40 result. The distinction is now made by provenance and
canonical Event Type, not by silently narrowing the existing term.

---

## 4. RC-3 — M34-D-0005 Temporal and State Integration

**Disposition:** `ACCEPTED`

### Reviewer concern

The proposal did not cite or integrate `M34-D-0005`, even though every
authoritative dated result must carry Event Type, Producing Domain,
authoritative timestamp, and Degraded State. Its proposed Computation State also
reused `UNAVAILABLE`, already a canonical Degraded State.

### Constitutional analysis

The proposal lacked sufficient authority and contained a real terminology
collision. `M34-D-0005` is directly governing:

- Event Type is `Calculation`;
- Producing Domain is `Market Intelligence`;
- the producing domain owns timestamp meaning and Degraded State; and
- `UNAVAILABLE` belongs to the canonical Degraded State vocabulary.

Method execution outcome and temporal availability answer different questions
and must remain separate. The former says whether a method completed; the
latter qualifies the availability of the authoritative result and evidence.

### Repository authority cited

- [M34 Decision Register — M34-D-0005](m34/audit/registers/decision_register.md#m34-d-0005---adopt-the-canonical-temporal-and-degraded-state-grammar)
- [Canonical Glossary — Canonical Temporal Claim](../GLOSSARY.md#canonical-temporal-claim)
- [Canonical Glossary — Event Type](../GLOSSARY.md#event-type)
- [Canonical Glossary — Producing Domain](../GLOSSARY.md#producing-domain)
- [Canonical Glossary — Degraded State](../GLOSSARY.md#degraded-state)

### Proposal change

The proposal now:

- adds `M34-D-0005` to governing authority;
- replaces `Computation State` with the orthogonal `Computation Outcome`;
- replaces its `UNAVAILABLE` outcome with `DEPENDENCY_UNRESOLVED`;
- adds a Calculation Temporal Claim to every result;
- defines Event Type `Calculation` and Producing Domain `Market Intelligence`;
- requires an explicit, method-defined authoritative timestamp with no
  wall-clock lookup;
- reserves `UNAVAILABLE` for Degraded State; and
- requires WP5/WP6 to specify a deterministic outcome/degraded-state
  interaction matrix.

### Rationale

This correction adopts the repository's existing temporal grammar rather than
inventing a parallel one. It preserves deterministic replay by making the
authoritative timestamp an explicit invocation input and keeping any future
operational execution timestamp outside semantic result identity.

---

## 5. RC-4 — WP2 Admission Criteria and Governing Authority

**Disposition:** `ACCEPTED`

### Reviewer concern

The governing-authority list omitted `M34-D-0004` and `M34-D-0005`, and WP2 did
not make RC-1 through RC-3 explicit admission-blocking exit criteria. The
Definition of Done also did not require independent approval of the layer and
Observation/Measure reconciliations.

### Constitutional analysis

The concern is valid. Ownership, vocabulary, and temporal grammar must be
resolved at the first work package that could admit those concepts. Deferring
them would allow lower-level contracts to depend on unresolved terms, contrary
to Governance G3 and Vocabulary V2.

`M34-D-0004` is directly relevant because it demonstrates that provider
evidence, canonical classification, projection, and analytical grouping retain
distinct owners even when labels overlap. `M34-D-0005` governs every
authoritative temporal result. Both belong in the proposal's governing corpus.

### Repository authority cited

- [M34 Decision Register — M34-D-0004](m34/audit/registers/decision_register.md#m34-d-0004---distinguish-asset-classification-evidence-and-analytical-grouping)
- [M34 Decision Register — M34-D-0005](m34/audit/registers/decision_register.md#m34-d-0005---adopt-the-canonical-temporal-and-degraded-state-grammar)
- [Platform Architecture — Governance G3](../architecture/platform_architecture.md#11-architecture-governance)
- [Platform Architecture — Vocabulary V2](../architecture/platform_architecture.md#12-canonical-vocabulary)

### Proposal change

The governing-authority list now names `M34-D-0004`, `M34-D-0005`, and
`M34-D-0010`. WP2 deliverables, validation, and exit criteria now require:

1. the six-layer ownership proof;
2. the frozen Market Observation refinement;
3. complete `M34-D-0005` integration;
4. an asset-measure/portfolio-measure negative corpus; and
5. independent constitutional approval before vocabulary admission or
   downstream work.

The milestone Definition of Done repeats the independent-approval gate.

### Rationale

The correction places each decision at its proper governance level and blocks
downstream reliance until it is resolved. It adds no work package and no
implementation scope.

---

## 6. Scope and Authority Confirmation

This reconciliation:

- preserves the M40 title and architectural direction;
- introduces no domain;
- weakens no M40 boundary;
- expands no milestone scope;
- modifies no M31–M39 or other frozen milestone document;
- modifies neither the independent review nor the Decision Log;
- creates no production code or implementation authority;
- creates no runtime, provider, persistence, API, Workspace, execution, or
  production-method authority;
- triggers no Graphify output; and
- creates no closeout.

M40 remains a non-canonical proposal in `NOT_APPROVED` state, pending
independent confirmation that the required corrections are satisfied.
