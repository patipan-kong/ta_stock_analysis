# M34 Decision Register

**Status:** Active. Contains the approved post-WP5 Architecture Review Board
governance rulings. WP6 remains NO-GO under `M34-D-0012`.

**Governing protocol:**
`../../../M34_WP1_charter_and_audit_protocol.md`

**Working-artifact rules:** `../README.md`

## Use

This register records approved audit decisions without replacing the project
Decision Log. The project Decision Log is synchronized only at the governance
point required by the approved M34 execution plan.

Allowed decision kinds are `FINDING_DISPOSITION`, `OWNERSHIP_RULING`,
`CORPUS_AMENDMENT`, `ARB_ESCALATION_RESULT`, `CHECKPOINT_RESULT`,
`M34_EXIT_RESULT`, and `M34_1_GATE_RESULT`.

Allowed statuses are `PROPOSED`, `UNDER_REVIEW`, `APPROVED`, `REJECTED`,
`RETURNED_TO_ARB`, and `SUPERSEDED`.

## Record template

```markdown
## M34-D-NNNN - <decision title>

- Status: PROPOSED
- Decision kind: <allowed kind>
- Proposed at UTC: <YYYY-MM-DDTHH:MM:SSZ>
- Decided at UTC: <timestamp | PENDING>
- Proposed by: <identity or approved role>
- Decision authority: <domain owner | architectural reviewer | ARB | governance owner>
- Work package: <M34-WP#>
- Checkpoint: <M34-CP# | NONE>
- Subject ids: <sorted M34-C/F/D-NNNN ids>
- Evidence ids: <sorted verified M34-E-NNNN ids | NONE>
- Review ids: <sorted M34-R-NNNN ids | PENDING>
- Supersedes: <M34-D-NNNN | NONE>
- Superseded by: <M34-D-NNNN | NONE>
- Decision Log reference: <stable reference | PENDING | NONE>

### Question

<Exact bounded question requiring a decision.>

### Options considered

<Options and their consequences. Do not add implementation designs.>

### Decision

<Approved choice, or PENDING.>

### Rationale and evidence

<Why the evidence and governing authority support the decision.>

### Constitutional basis

<Exact governing principles and references.>

### Readiness and blocking effect

<Effect on findings, checkpoint, M34 outcome, and M34.1 GO/NO-GO.>

### Conditions and closure

<Required evidence, synchronization, expiry, or NONE.>
```

## Records

## M34-D-0001 - Govern the M34 audit-domain namespace

- Status: `APPROVED`
- Decision kind: `ARB_ESCALATION_RESULT`
- Proposed at UTC: `2026-07-19T13:21:40Z`
- Decided at UTC: `2026-07-19T13:21:40Z`
- Proposed by: `Architecture Review Board`
- Decision authority: `ARB`
- Work package: `M34-WP6A`
- Checkpoint: `NONE`
- Subject ids: `M34-C-0049`, `M34-C-0050`, `M34-C-0054`, `M34-C-0055`, `M34-C-0056`, `M34-C-0058`
- Evidence ids: `M34-E-0039`, `M34-E-0040`, `M34-E-0043`, `M34-E-0044`, `M34-E-0045`, `M34-E-0048`, `M34-E-0049`, `M34-E-0050`
- Review ids: `M34-R-0014`, `M34-R-0015`
- Supersedes: `NONE`
- Superseded by: `NONE`
- Decision Log reference: `docs/engineering/DECISION_LOG.md::M34-WP6A - Post-ARB Semantic Governance Production`

### Context

WP1 audit labels overlap with but do not equal the reserved constitutional
domain names. WP5 could not treat those labels as implicit aliases without
violating the one-concept/one-owner rule.

### Question

How may frozen WP1 audit labels be interpreted when assigning constitutional
semantic authority?

### Options considered

The Board considered a claim-specific mapping, a WP1 addendum, exclusive use
of constitutional names in later work, exclusion of all provisional families,
and a constitutional amendment.

### Decision

Approve Option A. WP1 labels remain frozen historical audit classifications,
are not constitutional domain names, and are never universal aliases. Every
affected claim family must map explicitly and context-sensitively to exactly
one constitutional semantic owner. Frozen WP1-WP5A artifacts remain
unchanged.

### Rationale

Claim-specific mapping preserves the existing Constitution and resolves the
verified namespace ambiguity without concealing concept-level ownership
differences.

### Consequences

Later M34 artifacts must use an explicit mapping and may not infer ownership
from a WP1 label. No Platform Architecture or Constitution amendment, code,
runtime change, or M32/M33 reopening follows.

### Required follow-up

Create the approved claim-family mapping, semantic mapping, required Glossary
entries, and final WP6 admission records.

### Constitutional basis

Platform Architecture sections 6, 11 G2-G4/G6, and 12 V1/V3; WP1 sections
1.4-1.5 and stop conditions 1, 5, and 11.

### Readiness and blocking effect

The ruling closes DQ-01 but does not authorize WP6. M34.1 remains NO-GO.

### Traceability

ARB question `M34-WP5A-DQ-01`; escalation reviews `M34-R-0014` and
`M34-R-0015`; verified authority evidence listed above.

### Conditions and closure

DQ-01 is closed. The mapping must be effective before any affected claim
family enters WP6.

## M34-D-0002 - Decompose portfolio identity and strategy-container semantics

- Status: `APPROVED`
- Decision kind: `ARB_ESCALATION_RESULT`
- Proposed at UTC: `2026-07-19T13:21:40Z`
- Decided at UTC: `2026-07-19T13:21:40Z`
- Proposed by: `Architecture Review Board`
- Decision authority: `ARB`
- Work package: `M34-WP6A`
- Checkpoint: `NONE`
- Subject ids: `M34-C-0049`, `M34-C-0050`, `M34-C-0051`, `M34-C-0052`, `M34-C-0054`, `M34-C-0055`, `M34-C-0058`
- Evidence ids: `M34-E-0041`, `M34-E-0043`, `M34-E-0044`, `M34-E-0048`, `M34-E-0049`
- Review ids: `M34-R-0014`, `M34-R-0015`
- Supersedes: `NONE`
- Superseded by: `NONE`
- Decision Log reference: `docs/engineering/DECISION_LOG.md::M34-WP6A - Post-ARB Semantic Governance Production`

### Context

`SA01` grouped portfolio identity, accounting scope, strategy metadata, goal,
and UI selection even though those meanings cross constitutional boundaries.

### Question

Which existing domains own the distinct concepts grouped by `SA01`?

### Options considered

The Board considered one existing owner, explicit decomposition, exclusion
from WP6, and escalation to a constitutional amendment.

### Decision

Approve Option B. Portfolio Identity and Accounting Scope belong to Ledger &
Accounting. Portfolio Strategy Metadata belongs to Portfolio Intelligence and
excludes goals, decision policy, and accounting truth. Goal Target belongs to
Wealth Intelligence. Current Selection belongs to Experience Platform as UI
interaction state with no business meaning.

### Rationale

Portfolio is a bounded product container, not one semantic concept. A single
owner would create a hidden Portfolio domain and violate one-concept/one-owner.

### Consequences

All decomposed concepts refer to the same Ledger-owned accounting scope. The
decomposition changes semantic ownership only and does not split accounting
identity or authorize implementation changes.

### Required follow-up

Record the decomposition in the semantic mapping and define each concept
independently in the canonical Glossary.

### Constitutional basis

Platform Architecture sections 6, 6.9, 7.1, and 11 G3-G4; WP1 section 1.5
and stop condition 5; `M34-D-0001`.

### Readiness and blocking effect

`SA01` becomes owner-verifiable only through this decomposition and effective
vocabulary. WP6 remains NO-GO; M34.1 remains NO-GO.

### Traceability

ARB question `M34-WP5A-DQ-02`; WP5 `SA01`; `M34-D-0001`; evidence and
review ids listed above.

### Conditions and closure

DQ-02 is closed. No component may redefine the Ledger-owned accounting
boundary.

## M34-D-0003 - Decompose cross-portfolio membership, aggregation, and exposure

- Status: `APPROVED`
- Decision kind: `ARB_ESCALATION_RESULT`
- Proposed at UTC: `2026-07-19T13:21:40Z`
- Decided at UTC: `2026-07-19T13:21:40Z`
- Proposed by: `Architecture Review Board`
- Decision authority: `ARB`
- Work package: `M34-WP6A`
- Checkpoint: `NONE`
- Subject ids: `M34-C-0049`, `M34-C-0050`, `M34-C-0051`, `M34-C-0052`, `M34-C-0054`, `M34-C-0058`
- Evidence ids: `M34-E-0041`, `M34-E-0043`, `M34-E-0048`, `M34-E-0049`
- Review ids: `M34-R-0014`, `M34-R-0015`
- Supersedes: `NONE`
- Superseded by: `NONE`
- Decision Log reference: `docs/engineering/DECISION_LOG.md::M34-WP6A - Post-ARB Semantic Governance Production`

### Context

`SA02` combined accounting-scope membership, aggregation across scopes, and
investment exposure on one presentation surface.

### Question

How must the three meanings in `SA02` be separated and owned?

### Options considered

The Board considered Wealth ownership of the whole claim, a distinct
portfolio-collection projection, decomposition, and exclusion.

### Decision

Approve Option C. Portfolio Membership is the Ledger & Accounting fact that a
holding or instrument belongs to one or more portfolio accounting scopes.
Cross-Portfolio Aggregation is a Ledger & Accounting mathematical projection
over those facts with no investment meaning. Cross-Portfolio Exposure is a
Wealth Intelligence interpretation of the aggregate.

### Rationale

Membership, aggregation, and exposure are separate concepts. Route placement
and UI composition cannot assign them one owner.

### Consequences

Cross-Portfolio Exposure consumes Ledger facts, Market Intelligence
observations, and Asset Foundation classifications without owning them. It
must retain provenance to every contributing Ledger accounting scope.

### Required follow-up

Add the decomposition and provenance rule to the semantic mapping and define
the three concepts separately in the Glossary.

### Constitutional basis

Platform Architecture sections 6.3, 6.8, 6.9, and 7.1;
`PORTFOLIO_DOMAIN_MODEL.md` sections 7 and 10; `M34-D-0002`.

### Readiness and blocking effect

`SA02` becomes owner-verifiable only after its mapping and vocabulary are
effective. WP6 and M34.1 remain NO-GO.

### Traceability

ARB question `M34-WP5A-DQ-03`; WP5 `SA02` and `AV02`; `M34-D-0002`;
evidence and review ids listed above.

### Conditions and closure

DQ-03 is closed. Neither Portfolio Intelligence nor Experience Platform owns
Cross-Portfolio Exposure.

## M34-D-0004 - Distinguish asset classification evidence and analytical grouping

- Status: `APPROVED`
- Decision kind: `ARB_ESCALATION_RESULT`
- Proposed at UTC: `2026-07-19T13:21:40Z`
- Decided at UTC: `2026-07-19T13:21:40Z`
- Proposed by: `Architecture Review Board`
- Decision authority: `ARB`
- Work package: `M34-WP6A`
- Checkpoint: `NONE`
- Subject ids: `M34-C-0049`, `M34-C-0050`, `M34-C-0052`, `M34-C-0053`, `M34-C-0054`, `M34-C-0058`
- Evidence ids: `M34-E-0039`, `M34-E-0042`, `M34-E-0043`, `M34-E-0048`, `M34-E-0049`
- Review ids: `M34-R-0014`, `M34-R-0015`
- Supersedes: `NONE`
- Superseded by: `NONE`
- Decision Log reference: `docs/engineering/DECISION_LOG.md::M34-WP6A - Post-ARB Semantic Governance Production`

### Context

Current `sector` fields can represent canonical classification, provider
evidence, copied projections, or analytical grouping.

### Question

How must those distinct sector-related concepts be governed?

### Options considered

The Board considered one canonical classification with projections, a formal
classification/grouping distinction, an unknown classification, and exclusion
of all sector-dependent claims.

### Decision

Approve Option B. Canonical Asset Classification is Asset Foundation truth.
Market Classification Evidence is Market Intelligence evidence only.
Persisted, transported, cached, or displayed sector values are projections
with no independent authority. Analytical Grouping is a distinct,
context-specific portfolio-analysis, allocation, factor, attribution,
reporting, or visualization concept and is never canonical classification by
label similarity.

### Rationale

One unqualified `sector` term obscures provenance and violates
one-concept/one-owner.

### Consequences

Every sector-related value must identify whether it is canonical
classification, Market evidence, a copied projection, or Analytical Grouping.
Storage and display cannot promote authority.

### Required follow-up

Define Asset Classification, Market Classification Evidence, and Analytical
Grouping in the Glossary and preserve the distinction in semantic mappings.

### Constitutional basis

Platform Architecture sections 6.1, 6.2, 7.4, 11 G2/G4/G6, and 12 V1;
Market Data authority evidence in `M34-E-0042`.

### Readiness and blocking effect

Sector-dependent claims may enter WP6 only after their provenance is mapped
to this distinction. WP6 and M34.1 remain NO-GO.

### Traceability

ARB question `M34-WP5A-DQ-04`; WP5 `SA11` and `AV03`; evidence and review
ids listed above.

### Conditions and closure

DQ-04 is closed. No provider, cache, persistence layer, or presentation
becomes canonical merely by holding a value.

## M34-D-0005 - Adopt the canonical temporal and degraded-state grammar

- Status: `APPROVED`
- Decision kind: `ARB_ESCALATION_RESULT`
- Proposed at UTC: `2026-07-19T13:21:40Z`
- Decided at UTC: `2026-07-19T13:21:40Z`
- Proposed by: `Architecture Review Board`
- Decision authority: `ARB`
- Work package: `M34-WP6A`
- Checkpoint: `NONE`
- Subject ids: `M34-C-0049`, `M34-C-0050`, `M34-C-0053`, `M34-C-0054`, `M34-C-0056`, `M34-C-0058`
- Evidence ids: `M34-E-0042`, `M34-E-0045`, `M34-E-0047`, `M34-E-0048`, `M34-E-0049`
- Review ids: `M34-R-0014`, `M34-R-0015`
- Supersedes: `NONE`
- Superseded by: `NONE`
- Decision Log reference: `docs/engineering/DECISION_LOG.md::M34-WP6A - Post-ARB Semantic Governance Production`

### Context

The product uses `Updated`, `As Of`, `Current`, and `Fresh` for multiple
independent events and degraded states.

### Question

What canonical grammar governs authoritative temporal claims?

### Options considered

The Board considered unique terms for every event, a shared qualified
grammar, presentation labels paired with authoritative fields, and exclusion
of time-dependent claims.

### Decision

Approve Option B. Every authoritative temporal statement must identify its
Event Type, Producing Domain, authoritative Timestamp, and Degraded State.
Event types include Observation, Retrieval, Calculation, Analysis Generation,
Snapshot Creation, Batch Evaluation, and Synchronization. The producing
domain owns `UNKNOWN`, `UNAVAILABLE`, `DELAYED`, `STALE`, `PARTIAL`, and
`CONFLICTING`; Experience only renders them.

### Rationale

Qualified grammar preserves one concept/one owner while allowing consistent
presentation across independent clocks.

### Consequences

`Updated`, `As Of`, `Current`, and `Fresh` are non-normative presentation
language unless accompanied by authoritative event and source qualifiers. UI
refresh, cache refresh, polling, or rendering cannot redefine source
freshness.

### Required follow-up

Define the temporal grammar in the Glossary and classify every authoritative
timestamp in the semantic mapping.

### Constitutional basis

Platform Architecture sections 6.2, 6.9, 8, and 12 V1-V2; WP1 degraded-state
ownership rule.

### Readiness and blocking effect

Time-bearing claims may enter WP6 only when they preserve the complete
grammar. WP6 and M34.1 remain NO-GO.

### Traceability

ARB question `M34-WP5A-DQ-05`; WP5 `SA16` and `AV04`; evidence and review
ids listed above.

### Conditions and closure

DQ-05 is closed. No presentation or client event may redefine source
freshness.

## M34-D-0006 - Govern bounded canonical-vocabulary admission to WP6

- Status: `APPROVED`
- Decision kind: `ARB_ESCALATION_RESULT`
- Proposed at UTC: `2026-07-19T13:21:40Z`
- Decided at UTC: `2026-07-19T13:21:40Z`
- Proposed by: `Architecture Review Board`
- Decision authority: `ARB`
- Work package: `M34-WP6A`
- Checkpoint: `NONE`
- Subject ids: `M34-C-0049`, `M34-C-0050`, `M34-C-0058`
- Evidence ids: `M34-E-0039`, `M34-E-0047`, `M34-E-0048`, `M34-E-0049`, `M34-E-0050`
- Review ids: `M34-R-0014`, `M34-R-0015`
- Supersedes: `NONE`
- Superseded by: `NONE`
- Decision Log reference: `docs/engineering/DECISION_LOG.md::M34-WP6A - Post-ARB Semantic Governance Production`

### Context

Most WP5 claim families lacked exact canonical Glossary coverage even after
their semantic boundaries and owners were decided.

### Question

Which vocabulary conditions must a claim family satisfy before entering WP6?

### Options considered

The Board considered complete coverage for all uncovered families, a bounded
subset, an ordinary-language exception list, temporary lower-level authority,
and continued global blockage.

### Decision

Approve Option B. Admission is claim-family-specific. A concept may enter
WP6 only when its ARB-approved boundary and one constitutional owner are
recorded, every required Glossary entry is created and independently
approved, the vocabulary is effective, and it is traceably synchronized with
governing artifacts.

### Rationale

Semantic agreement does not make vocabulary canonical. Bounded admission
allows incremental governance without creating a second glossary.

### Consequences

Every claim family must appear in exactly one approved `WP6_INCLUDED` or
`WP6_EXCLUDED` set. Each exclusion names missing entries, owner, remaining
work, and readiness consequence. Ordinary language may carry no independent
business, authority, formula, status, temporal, or degraded-state meaning.

### Required follow-up

Complete and approve required Glossary entries, synchronize them, and create
the exact admission manifests before a new WP6 gate review.

### Constitutional basis

Platform Architecture sections 11 G2-G5 and 12 V1-V4; WP1 canonical-
vocabulary rule, evidence rule 7, and stop condition 11.

### Readiness and blocking effect

No claim family is admitted by this decision alone. WP6 and M34.1 remain
NO-GO.

### Traceability

ARB question `M34-WP5A-DQ-06`; WP5 sections 3, 6, 8, and 9; approved
`M34-D-0001` through `M34-D-0005` and `M34-D-0007` through `M34-D-0011`.

### Conditions and closure

DQ-06 is closed. Lower-level documents never become a second canonical
Glossary.

## M34-D-0007 - Decompose goals, policy, limits, persona, and configuration

- Status: `APPROVED`
- Decision kind: `ARB_ESCALATION_RESULT`
- Proposed at UTC: `2026-07-19T13:21:40Z`
- Decided at UTC: `2026-07-19T13:21:40Z`
- Proposed by: `Architecture Review Board`
- Decision authority: `ARB`
- Work package: `M34-WP6A`
- Checkpoint: `NONE`
- Subject ids: `M34-C-0049`, `M34-C-0050`, `M34-C-0051`, `M34-C-0053`, `M34-C-0054`, `M34-C-0055`, `M34-C-0058`
- Evidence ids: `M34-E-0039`, `M34-E-0042`, `M34-E-0043`, `M34-E-0044`, `M34-E-0047`, `M34-E-0048`, `M34-E-0049`
- Review ids: `M34-R-0014`, `M34-R-0015`
- Supersedes: `NONE`
- Superseded by: `NONE`
- Decision Log reference: `docs/engineering/DECISION_LOG.md::M34-WP6A - Post-ARB Semantic Governance Production`

### Context

Goal Wizard, Settings, Optimizer, and Operations Center group settings that
govern different constitutional behavior.

### Question

How must `SA25` and `SA39` be decomposed without creating a Configuration,
Goal, Persona, Settings, or Portfolio Workspace domain?

### Options considered

The Board considered exhaustive decomposition, a bounded composite policy,
separate strategy/goal/policy concepts, and exclusion.

### Decision

Approve Option A. Portfolio Strategy Metadata belongs to Portfolio
Intelligence. Goal Target belongs to Wealth Intelligence. Decision Policy,
Portfolio Limits, Sector Limits, and Optimizer Layer/Fallback Configuration
belong to Decision Intelligence. Sector Limits reference but do not redefine
Asset Foundation classification. Model Selection belongs to the producing
constitutional domain responsible for the governed behavior. Analysis Source
Selection belongs to its consuming constitutional domain and does not own the
source data. Persona is a reference-only preset that owns no business rule.

### Rationale

Common storage and presentation are implementation concerns and cannot create
one semantic owner.

### Consequences

Every configuration family must preserve one concept, one constitutional
owner, and explicit references to independently owned concepts. No grouped
object acquires ownership of referenced settings.

### Required follow-up

Record the exhaustive family mapping and define Portfolio Strategy Metadata,
Goal Target, Decision Policy, Portfolio Limits, Sector Limits, Persona, Model
Selection, Analysis Source Selection, and Optimizer Configuration.

### Constitutional basis

Platform Architecture sections 6.5, 6.6, 6.8, 6.9, 7.2, and 11-12;
`M34-D-0002` and `M34-D-0004`.

### Readiness and blocking effect

`SA25` and `SA39` become owner-verifiable only through the decomposition and
effective vocabulary. WP6 and M34.1 remain NO-GO.

### Traceability

ARB question `M34-WP5A-DQ-07`; WP5 `SA25`, `SA39`, and `AV11`; evidence and
review ids listed above.

### Conditions and closure

DQ-07 is closed. Persona remains reference composition only.

## M34-D-0008 - Constrain legacy execution and decision records as stopped authority

- Status: `APPROVED`
- Decision kind: `ARB_ESCALATION_RESULT`
- Proposed at UTC: `2026-07-19T13:21:40Z`
- Decided at UTC: `2026-07-19T13:21:40Z`
- Proposed by: `Architecture Review Board`
- Decision authority: `ARB`
- Work package: `M34-WP6A`
- Checkpoint: `NONE`
- Subject ids: `M34-C-0049`, `M34-C-0050`, `M34-C-0055`, `M34-C-0056`, `M34-C-0057`, `M34-C-0058`
- Evidence ids: `M34-E-0044`, `M34-E-0045`, `M34-E-0046`, `M34-E-0047`, `M34-E-0048`, `M34-E-0049`, `M34-E-0050`
- Review ids: `M34-R-0014`, `M34-R-0015`
- Supersedes: `NONE`
- Superseded by: `NONE`
- Decision Log reference: `docs/engineering/DECISION_LOG.md::M34-WP6A - Post-ARB Semantic Governance Production`

### Context

Existing reads display execution-plan projections, legacy decision records,
execution detail, plan-versus-actual comparisons, and decision memory even
though M32 and M33 denied canonical planning and approval authority.

### Question

What bounded semantics may WP6 verify without reopening M32 or M33?

### Options considered

The Board considered positive non-authoritative definitions, qualified terms,
total exclusion, and negative-only `STOPPED_AUTHORITY` verification.

### Decision

Approve Option D. Execution Plan Projection, Legacy Decision Record,
Execution Detail, Plan-versus-Actual Comparison, and Decision Memory are
`STOPPED_AUTHORITY` artifacts. They preserve historical context only. They do
not prove canonical execution planning, approval, authenticated actor,
authorization, human intent, or trading instruction.

### Rationale

M32 and M33 are immutable constraints. Negative verification preserves those
boundaries without assigning positive authority to legacy records.

### Consequences

WP6 may verify non-authority, absence of canonical planning/approval/actor
attribution, and preservation of the stop boundary. It may not verify
execution correctness, approval correctness, authorization, human intent, or
decision authority. Ledger transactions remain Ledger facts and prove none of
those authorities.

### Required follow-up

Define Execution Plan Projection, Legacy Decision Record,
`STOPPED_AUTHORITY`, Decision Memory, and Plan-versus-Actual Comparison and
map `SA27`-`SA30` to negative verification only.

### Constitutional basis

M32 Epic Closeout; M33.11 `STOP_M33_RUNTIME`; Platform Architecture sections
6.3, 6.6, 6.7, 7.2, 8, and 11 G2/G4/G6; WP1 stop condition 7.

### Readiness and blocking effect

Affected families may enter only a negative WP6 scope after vocabulary is
effective. WP6 and M34.1 remain NO-GO.

### Traceability

ARB question `M34-WP5A-DQ-08`; WP5 `SA27`-`SA30`, `AV07`, `AV08`, and
`AV09`; evidence and review ids listed above.

### Conditions and closure

DQ-08 is closed. No later M34 artifact may infer positive authority from a
legacy record or linked Ledger event.

## M34-D-0009 - Decompose Operations Center source-domain statuses

- Status: `APPROVED`
- Decision kind: `ARB_ESCALATION_RESULT`
- Proposed at UTC: `2026-07-19T13:21:40Z`
- Decided at UTC: `2026-07-19T13:21:40Z`
- Proposed by: `Architecture Review Board`
- Decision authority: `ARB`
- Work package: `M34-WP6A`
- Checkpoint: `NONE`
- Subject ids: `M34-C-0049`, `M34-C-0050`, `M34-C-0052`, `M34-C-0053`, `M34-C-0054`, `M34-C-0055`, `M34-C-0056`, `M34-C-0058`
- Evidence ids: `M34-E-0039`, `M34-E-0042`, `M34-E-0043`, `M34-E-0044`, `M34-E-0045`, `M34-E-0047`, `M34-E-0048`, `M34-E-0049`
- Review ids: `M34-R-0014`, `M34-R-0015`
- Supersedes: `NONE`
- Superseded by: `NONE`
- Decision Log reference: `docs/engineering/DECISION_LOG.md::M34-WP6A - Post-ARB Semantic Governance Production`

### Context

Operations Center composes portfolio, goal, market, optimizer, policy,
station, committee, translation, trust, and attention states.

### Question

Does the composition own an Operations truth, or must its statuses retain
their source-domain authority?

### Options considered

The Board considered source decomposition, a derived Operations concept,
Experience-only labels, and exclusion.

### Decision

Approve Option A. Operations Center is presentation composition only.
Portfolio Status belongs to Portfolio Intelligence; Goal Status to Wealth
Intelligence; Market Context Status to Market Intelligence; Optimizer and
Policy Status to Decision Intelligence. Station Health remains the status of
its responsible producing domain. Committee Status remains supplied by its
producing governance component and never implies approval. Translation Status
is operational status of its producing translation service. Action Required
is Experience presentation indicating source-domain attention and is not a
decision, approval, instruction, or authorization.

### Rationale

Composition cannot transfer authority upward or create a platform-wide
Operations truth.

### Consequences

Every status preserves producing domain, event qualifier, timestamp,
degraded-state qualifier, and provenance. Trust & Evaluation remains
independently evaluative. Legacy inputs retain `STOPPED_AUTHORITY`.

### Required follow-up

Define the approved status terms, record their source-domain mappings, and
keep the aggregate presentation-only.

### Constitutional basis

Platform Architecture sections 6.2, 6.5-6.7, 6.9, 7.1, and 8; downward-only
dependency law; `M34-D-0005`, `M34-D-0007`, and `M34-D-0008`.

### Readiness and blocking effect

`SA36` and the operational portion of `SA37` become owner-verifiable only by
decomposition. WP6 and M34.1 remain NO-GO.

### Traceability

ARB question `M34-WP5A-DQ-09`; WP5 `SA36`, `SA37`, and `AV10`; evidence and
review ids listed above.

### Conditions and closure

DQ-09 is closed. No aggregate Operations, Health, or Committee domain is
created.

## M34-D-0010 - Decompose the instrument-analysis product contract

- Status: `APPROVED`
- Decision kind: `ARB_ESCALATION_RESULT`
- Proposed at UTC: `2026-07-19T13:21:40Z`
- Decided at UTC: `2026-07-19T13:21:40Z`
- Proposed by: `Architecture Review Board`
- Decision authority: `ARB`
- Work package: `M34-WP6A`
- Checkpoint: `NONE`
- Subject ids: `M34-C-0049`, `M34-C-0050`, `M34-C-0053`, `M34-C-0054`, `M34-C-0055`, `M34-C-0056`, `M34-C-0058`
- Evidence ids: `M34-E-0039`, `M34-E-0042`, `M34-E-0043`, `M34-E-0044`, `M34-E-0047`, `M34-E-0048`, `M34-E-0049`
- Review ids: `M34-R-0014`, `M34-R-0015`
- Supersedes: `NONE`
- Superseded by: `NONE`
- Decision Log reference: `docs/engineering/DECISION_LOG.md::M34-WP6A - Post-ARB Semantic Governance Production`

### Context

Stock and Watchlist responses combine identity, classification, market facts,
judgment, risk, consensus, history, evaluation, and presentation.

### Question

How must the grouped instrument-analysis contract be decomposed across
existing constitutional domains?

### Options considered

The Board considered full decomposition, one bounded analysis judgment,
partial admission, and exclusion.

### Decision

Approve Option A. Asset Identity and Canonical Asset Classification belong to
Asset Foundation. Market Observations, including prices, technical
observations, market statistics, provider observations, and news references,
belong to Market Intelligence and are not judgments. Investment Judgment,
Instrument-Level Derived Risk, Consensus, and Analysis History belong to
Decision Intelligence. Evaluation belongs to Trust & Evaluation.
Presentation belongs to Experience Platform and owns no business truth.

### Rationale

The grouped output is a presentation composition of existing constitutional
concepts, not one owned contract.

### Consequences

Consensus is derived judgment, not evidence or source authority. Instrument
risk is distinct from portfolio risk. Analysis History preserves context but
does not prove correctness. Every field preserves semantic owner, source and
temporal provenance, and applicable degraded state.

### Required follow-up

Define Market Observation, Investment Judgment, Instrument-Level Risk,
Consensus, Analysis History, and Evaluation and record the decomposition.

### Constitutional basis

Platform Architecture sections 6.1, 6.2, 6.5-6.7, 6.9, 7.1, 7.4, and 12;
facts-versus-judgment law; `M34-D-0004` and `M34-D-0005`.

### Readiness and blocking effect

`SA20` and `SA21` become owner-verifiable only through the decomposition and
effective vocabulary. WP6 and M34.1 remain NO-GO.

### Traceability

ARB question `M34-WP5A-DQ-10`; WP5 `SA20`, `SA21`, and `AV13`; evidence and
review ids listed above.

### Conditions and closure

DQ-10 is closed. No Instrument Analysis domain or composite authority is
created.

## M34-D-0011 - Govern Watchlist membership as interaction preference

- Status: `APPROVED`
- Decision kind: `ARB_ESCALATION_RESULT`
- Proposed at UTC: `2026-07-19T13:21:40Z`
- Decided at UTC: `2026-07-19T13:21:40Z`
- Proposed by: `Architecture Review Board`
- Decision authority: `ARB`
- Work package: `M34-WP6A`
- Checkpoint: `NONE`
- Subject ids: `M34-C-0049`, `M34-C-0050`, `M34-C-0053`, `M34-C-0055`, `M34-C-0058`
- Evidence ids: `M34-E-0039`, `M34-E-0042`, `M34-E-0044`, `M34-E-0047`, `M34-E-0048`, `M34-E-0049`
- Review ids: `M34-R-0014`, `M34-R-0015`
- Supersedes: `NONE`
- Superseded by: `NONE`
- Decision Log reference: `docs/engineering/DECISION_LOG.md::M34-WP6A - Post-ARB Semantic Governance Production`

### Context

Watchlist membership is user-maintained state displayed beside independently
owned identity, market, judgment, evaluation, and transaction concepts.

### Question

What bounded meaning and owner govern Watchlist Membership?

### Options considered

The Board considered Experience preference, Decision Intelligence intent,
another existing domain, and exclusion.

### Decision

Approve Option A. Watchlist Membership is Experience Platform interaction and
user-preference vocabulary only: a user-maintained state retaining an Asset
for future viewing or investigation.

### Rationale

Membership expresses presentation preference, not financial or investment
truth. Assigning broader meaning would overstate a convenience state.

### Consequences

Membership implies no ownership, portfolio inclusion, accounting identity,
recommendation, investment decision, approval, execution authorization,
transaction intent, execution plan, optimizer policy, or human authorization.
Launching a transaction workflow does not change membership meaning. The
record preserves only preference state, referenced Asset identity,
interaction provenance, and `M34-D-0005` temporal provenance.

### Required follow-up

Define Watchlist Membership, User Preference State, and Interaction State and
record the interaction-only mapping.

### Constitutional basis

Platform Architecture sections 6.1, 6.2, 6.6, 6.9, 7.1, and 12; Experience
intent-capture boundary; `M34-D-0010`.

### Readiness and blocking effect

`SA38` becomes owner-verifiable only after vocabulary is effective. WP6 and
M34.1 remain NO-GO.

### Traceability

ARB question `M34-WP5A-DQ-11`; WP5 `SA38` and `AV13`; evidence and review
ids listed above.

### Conditions and closure

DQ-11 is closed. Watchlist Membership never inherits authority from displayed
analysis or an adjacent workflow.

## M34-D-0012 - Keep WP6 closed pending effective governance artifacts

- Status: `APPROVED`
- Decision kind: `ARB_ESCALATION_RESULT`
- Proposed at UTC: `2026-07-19T13:21:40Z`
- Decided at UTC: `2026-07-19T13:21:40Z`
- Proposed by: `Architecture Review Board`
- Decision authority: `ARB`
- Work package: `M34-WP6A`
- Checkpoint: `NONE`
- Subject ids: `M34-C-0049`, `M34-C-0050`, `M34-C-0058`
- Evidence ids: `M34-E-0048`, `M34-E-0049`, `M34-E-0050`
- Review ids: `M34-R-0014`, `M34-R-0015`
- Supersedes: `NONE`
- Superseded by: `NONE`
- Decision Log reference: `docs/engineering/DECISION_LOG.md::M34-WP6A - Post-ARB Semantic Governance Production`

### Context

DQ-01 through DQ-11 resolved substantive semantic governance, but their
required records, mappings, Glossary entries, synchronization, admission
manifests, independent review, and checkpoint were not yet effective.

### Question

May WP6 begin before those governance artifacts are complete and effective?

### Options considered

The Board considered full entry, bounded entry, continued NO-GO, and return
to the existing M34 closure authority.

### Decision

Approve Option C. WP6 remains closed. No claim family is admitted and no
implied partial authorization exists. The gate may be reconsidered only after
every required governance artifact and vocabulary entry is effective, the
semantic mappings and admission manifests are approved, independent Review
Log approval is recorded, and a checkpoint is completed.

### Rationale

ARB decisions establish semantic governance but do not by themselves
establish readiness. Readiness requires effective, synchronized artifacts.

### Consequences

The post-ARB governance-production phase may create documentation only. It
does not authorize WP6, Portfolio Home, implementation, runtime work, M34.1,
or any M32/M33 reopening.

### Required follow-up

Complete the twelve Decision Records, DQ-01 mapping, semantic mapping,
Glossary entries and approval, vocabulary synchronization, exact
`WP6_INCLUDED` and `WP6_EXCLUDED` manifests, independent Review Log approval,
and a `CHECKPOINT_RESULT`; then submit a new WP6 gate review.

### Constitutional basis

WP1 evidence, ownership, review, and stop rules; Platform Architecture
sections 11-12; `M34-D-0001` through `M34-D-0011`; M32 and M33 closed
decisions.

### Readiness and blocking effect

Final governance state is `WP6_BLOCKED`. WP6 is unauthorized and M34.1
remains NO-GO.

### Traceability

ARB question `M34-WP5A-DQ-12`; `M34-R-0014`, `M34-R-0015`; `M34-E-0048`
through `M34-E-0050`; approved DQ-01 through DQ-11 records.

### Conditions and closure

DQ-12 is closed. Completion of follow-up artifacts does not automatically
authorize WP6; a new gate review is mandatory.
