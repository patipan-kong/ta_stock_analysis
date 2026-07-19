# M34-WP1 - Charter and Audit Protocol

**Date:** 2026-07-17

**Status:** Complete. Canonical audit protocol for M34. Framework and corpus
definition only. No repository findings, semantic judgments, implementation,
or runtime changes.

**Governing milestone:** M34 - Portfolio Semantic Integrity and Product
Readiness Baseline.

**WP1 decision:** Every later M34 work package must use this protocol to select
evidence, classify findings, assign ownership, record dispositions, and decide
whether M34 may exit `READY_FOR_PORTFOLIO_HOME_SLICE`. This protocol does not
prejudge that exit. M34.1 remains NO-GO.

## 1. Audit charter

### 1.1 Objective

The audit will determine whether existing portfolio capabilities are
semantically correct, sufficiently explained, transparently degraded, and
supported by a credible product case before any Portfolio Home implementation
is approved.

The audit answers four bounded questions:

1. What portfolio facts and analytical claims does the repository currently
   define, transport, transform, render, document, and test?
2. Which domain owns the meaning and correctness of each claim?
3. Can a user understand what a displayed value means, when it applies, where
   it came from, and when it is incomplete or unavailable?
4. Is there enough verified product value and semantic integrity to authorize
   the smallest Portfolio Home slice?

The audit records evidence and decisions. It does not repair defects or design
the future implementation.

### 1.2 Scope

The audit includes repository artifacts that define or materially affect the
five approved portfolio questions:

1. What do I own?
2. What is it worth?
3. What changed?
4. Can I trust the displayed values?
5. Where should I investigate further?

An artifact is in scope when it performs at least one of these functions for
one of those questions:

- establishes portfolio, ledger, price, valuation, performance, attribution,
  risk, freshness, completeness, or explanatory semantics;
- stores or reconstructs a fact used by a portfolio read surface;
- exposes, transports, transforms, labels, formats, or renders such a fact;
- handles absence, staleness, partial coverage, fallback, or failure for such
  a fact;
- tests or documents the corresponding rule;
- governs the concept's owner, canonical vocabulary, roadmap status, or
  product readiness; or
- supplies evidence for the product case or navigation compatibility of a
  possible Portfolio Home.

Mixed-purpose files are included only for the symbols, routes, models,
contracts, configuration, tests, and documentation sections that satisfy this
rule. Inclusion does not transfer ownership to M34.

### 1.3 Exclusions

The audit excludes:

- implementation, repair, refactoring, migration, or runtime adoption;
- frontend, backend, database, API, schema, provider, configuration, or
  deployment changes;
- execution runtime, execution intent, approval authority, certificates,
  identity, RBAC, and all stopped M33 runtime work;
- reopening M32, canonical execution planning, order routing, broker, fill,
  fulfillment, or reconciliation behavior;
- market-provider adoption or selection;
- portfolio schema, registry, analytics, AI, or optimizer redesign;
- creation of a new Workspace, Trust, Read Model, or Portfolio Home domain;
- speculative target architecture not needed to classify current evidence;
- production data mutation, production traffic generation, external account
  creation, secrets, credentials, or personal-data collection;
- treating generated knowledge-graph output, screenshots, comments, names, or
  UI appearance as sufficient proof of business semantics; and
- auditing unrelated capabilities merely because they share a file, service,
  table, route module, component library, or deployment process with an
  in-scope capability.

Historical M32 and M33 artifacts may be read only to enforce their closed
boundaries. They are not candidates for runtime adoption or product reuse.

### 1.4 Evidence rules

Every material audit statement must obey these rules:

1. **Evidence before conclusion.** A finding cannot be verified from memory,
   naming, proximity, convention, or reviewer expectation.
2. **Traceability.** Evidence must identify a stable repository path and,
   when available, symbol, route, test, section, command, fixture, or captured
   observation. Line numbers may assist review but are not stable identities.
3. **Exactness.** Evidence records what an artifact actually states or does;
   it must not silently normalize terminology or repair meaning.
4. **Separation of fact and interpretation.** Source observations and
   reasoned conclusions are recorded separately. Derived evidence cites every
   material premise.
5. **Authority is contextual.** A constitution may govern what is allowed,
   source may show what is implemented, runtime evidence may show what
   occurred in one environment, and tests may show an asserted contract.
   None automatically substitutes for another.
6. **No evidence by aggregation.** Several incomplete sources do not prove a
   missing semantic rule, owner, timestamp, basis, or lineage.
7. **Conflict visibility.** Conflicting artifacts remain conflicting until
   the appropriate owner or Architecture Review Board resolves them. No
   latest-file, majority, test-wins, code-wins, or document-wins heuristic is
   permitted outside the governance hierarchy.
8. **Negative claims need bounded searches.** “Absent” or “unused” claims must
   state the searched corpus, patterns, tools, and limitations.
9. **Reproducibility.** Runtime and test observations must record the command,
   relevant environment identity, fixture/data boundary, result, and date.
   Secrets and personal data are never retained.
10. **No mutation for proof.** Evidence collection is read-only unless a later
    work package separately authorizes isolated non-production execution.
    Even then, repository and runtime state must not be changed as part of
    M34.
11. **Uncertainty is explicit.** Missing, inaccessible, stale, ambiguous, or
    contradictory evidence is classified `UNKNOWN`; it is not converted into
    a favorable assumption.
12. **Assumptions cannot authorize readiness.** An assumption may guide the
    next verification step but cannot close a finding or support
    `READY_FOR_PORTFOLIO_HOME_SLICE`.

Evidence excerpts must be minimal and must not reproduce secrets, tokens,
credentials, personal information, proprietary external payloads, or large
generated files.

### 1.5 Ownership model

The audit recognizes existing domain ownership; it creates none.

| Responsibility | Owner rule |
| --- | --- |
| Portfolio identity, holdings interpretation, valuation composition, and portfolio-level read semantics | Portfolio domain, except where a more specific source domain owns the underlying fact |
| Transactions, cash movements, quantities, costs, and other ledger facts | Ledger domain |
| Prices, market observation times, provider/source state, and market-data availability | Market Data domain |
| Return, risk, benchmark, attribution, contribution, and statistical semantics | Analytics domain |
| Portfolio-intelligence claim meaning and investigation recommendations | Portfolio Intelligence domain, using source-domain facts without redefining them |
| AI-produced explanation or evaluation semantics | AI Evaluation owner, with explicit provenance and without becoming portfolio truth |
| Labels, layout, navigation, accessibility, and visible degraded-state rendering | Experience layer |
| Meaning of a degraded state and the facts that cause it | Domain that owns the affected truth; Experience only renders the supplied state |
| Canonical vocabulary | Glossary and the owning domain constitution under the governance hierarchy |
| Cross-domain architectural disputes and milestone readiness | Architecture Review Board |
| Evidence capture and finding-register integrity | M34 audit lead; this is stewardship, not business-rule ownership |

The governing ownership invariant is: **one concept, one owner; Experience
renders and explains truth but owns none.** A transport, cache, page,
aggregator, or test does not become the owner merely because it contains a
copy or projection.

When ownership is unclear, the audit records `UNKNOWN_OWNERSHIP`; it does not
appoint a convenient owner. When two domains implement the same business
meaning, the audit records potential duplication rather than choosing a
winner.

### 1.6 Review process and independence

The M34 audit lead maintains the corpus, evidence register, and finding
register. Domain owners verify factual interpretations for their concepts.
Experience reviewers verify presentation and navigation observations without
claiming source-domain semantics. The Architecture Review Board decides
constitutional disputes, cross-domain ownership, scope changes, and M34 exit.

No person may close a disputed finding solely because they authored the
artifact under review. Author feedback is evidence, not unilateral approval.
Every blocking finding requires an independent architectural review and a
recorded disposition.

## 2. Repository audit corpus

### 2.1 Corpus inclusion rule

The paths below are corpus anchors, not a claim that every file beneath them
is relevant. Later work packages must follow imports, calls, schemas,
configuration, data lineage, and documentation references from an anchor only
when the followed artifact meets section 1.2. Conversely, an in-scope artifact
is not excluded merely because it was not named individually in WP1.

Newly discovered artifacts are added to the corpus register with the reason
for inclusion. This is corpus completion, not scope expansion, when the
artifact already satisfies section 1.2. Changing the five user questions,
adding a domain, or examining an excluded capability requires Architecture
Review Board approval.

Generated `graphify-out/` material may be used for navigation and coverage
checks, but it is not authoritative evidence of runtime behavior or business
meaning. Claims must resolve to the underlying repository artifact.

### 2.2 Experience

In scope:

- portfolio-facing routes under `frontend/app/portfolio/`,
  `frontend/app/performance/`, `frontend/app/analytics/`, and
  `frontend/app/portfolio-intelligence/`;
- portfolio and analytics presentation components under
  `frontend/components/portfolio/` and `frontend/components/analytics/`;
- shared navigation used by those surfaces, including
  `frontend/components/PortfolioTabs.tsx` and
  `frontend/components/Navbar.tsx`;
- `frontend/lib/api.ts`, `frontend/lib/PortfolioContext.tsx`, and
  `frontend/lib/analytics-transformers.ts` for portfolio-facing contracts,
  transformations, status propagation, and freshness presentation only; and
- page-local types, selectors, formatters, empty/error/loading states,
  accessibility semantics, and navigation compatibility that materially
  affect the five user questions.

Shared visual infrastructure is included only where it changes portfolio
meaning, visibility, failure transparency, or navigation. General styling and
unrelated application navigation are excluded.

### 2.3 Portfolio

In scope:

- `backend/services/portfolio_metrics.py`;
- `backend/services/portfolio_snapshots.py`;
- `backend/services/portfolio_rebuilder.py`;
- portfolio-facing portions of `backend/main.py`;
- portfolio, holding/item, workspace-scope, snapshot, valuation, and related
  read-contract portions of `backend/models/database.py`;
- API request/response contracts used by the in-scope portfolio surfaces;
- persistence schema and migration history only where needed to establish the
  meaning, lineage, optionality, time, or deletion behavior of current
  portfolio reads; and
- configuration that materially affects portfolio read correctness,
  temporal meaning, completeness, or failure handling.

Schema redesign and tenant/identity redesign are excluded. The existing
`Workspace` tenant concept may be observed only to preserve terminology and
scope correctness; it is not the proposed product surface.

### 2.4 Analytics

In scope:

- `backend/services/analytics/`, including quantitative, attribution,
  contribution, performance, risk, and data-quality semantics used by an
  in-scope surface;
- `backend/services/benchmark_service.py`;
- analytics- and performance-facing portions of `backend/main.py`;
- analytics response contracts and transformations consumed by in-scope
  pages; and
- benchmark, period, basis, return, risk, contribution, attribution,
  completeness, and failure semantics visible to users.

Optimizer design, canonical execution planning, and unrelated research
analytics are excluded.

### 2.5 Market Data

In scope:

- `backend/services/data_fetcher.py`;
- `backend/services/market_data/`;
- price and market-observation portions of backend routes and contracts used
  by the in-scope surfaces;
- market-price persistence or cache schema relevant to displayed value;
- source/provider identifiers, observation timestamps, retrieval timestamps,
  staleness, fallback, coverage, and unavailability semantics; and
- tests and configuration that define those current behaviors.

Provider evaluation, provider adoption, and market-data infrastructure
redesign are excluded.

### 2.6 Ledger

In scope:

- transaction, cash, position quantity, cost basis, and portfolio-item facts
  that feed the in-scope portfolio reads;
- the relevant portions of models, repositories, services, routes, imports,
  and reconstruction paths;
- lineage from ledger facts into holdings, valuation, change, or performance
  views; and
- correction, deletion, duplication, and temporal rules that can affect the
  displayed portfolio truth.

Order execution, execution-intent linkage, broker integration, fills as a new
runtime capability, and reconciliation redesign are excluded. Existing
transaction facts may be inspected only as current ledger inputs.

### 2.7 Portfolio Intelligence

In scope:

- `frontend/app/portfolio-intelligence/` and its directly supporting
  presentation and API contracts;
- backend routes and services that produce portfolio-investigation claims,
  rankings, alerts, explanations, or follow-up cues displayed by that
  surface; and
- provenance, owner, calculation source, failure, freshness, and explanation
  boundaries for those claims.

New intelligence capability, AI redesign, recommendation redesign,
optimization, and execution adoption are excluded.

### 2.8 AI Evaluation

In scope:

- repository AI/evaluation prompts, services, contracts, fixtures, and tests
  only when their output is presented as an explanation, assessment, ranking,
  or investigation cue on an in-scope portfolio surface;
- the boundary between deterministic portfolio/analytics facts and generated
  interpretation; and
- provenance, model/provider disclosure already represented in the
  repository, failure transparency, and evaluation evidence for such output.

General AI infrastructure, model/provider selection, optimizer AI, prompt
redesign, and new evaluation systems are excluded.

### 2.9 Documentation

In scope:

- the Platform Constitution and applicable domain constitutions;
- Portfolio Calculation Rules and other canonical semantic definitions;
- Engineering Principles and architectural documentation;
- the canonical glossary and terminology rules;
- API/read-contract documentation for the in-scope surfaces;
- relevant implementation and closeout documents needed to establish current
  claims and closed boundaries;
- the approved M34 Architecture Decision, Execution Plan, and this protocol;
  and
- roadmap statements that describe portfolio capabilities or Portfolio Home
  readiness.

Documentation about M32 and M33 is included only to preserve their CLOSED and
NO-GO/STOP boundaries.

### 2.10 Tests

In scope:

- backend tests for portfolio metrics, valuation, snapshots, reconstruction,
  price matrices, market prices, benchmarks, performance, quantitative
  analytics, attribution, contribution, data quality, and portfolio-facing
  failure behavior;
- frontend tests for the in-scope routes, components, API transformations,
  labels, empty/error/degraded states, freshness, and navigation, when
  present;
- integration or contract tests that cross an in-scope domain boundary; and
- fixtures, golden outputs, and test utilities that encode a business
  meaning used in those tests.

Tests are evidence of an asserted or executable contract, not automatic proof
that the asserted semantics are correct.

### 2.11 Governance

In scope:

- `docs/engineering/DECISION_LOG.md`;
- the authoritative roadmap and milestone-status artifacts;
- applicable ADRs, governance indexes, and closeout records;
- the hierarchy and ownership statements used to resolve conflicts; and
- M34 exit-decision and M34.1 GO/NO-GO records.

Governance artifacts are reviewed for authority, consistency, terminology,
scope, and synchronization. M34 does not rewrite predecessor decisions.

### 2.12 Tooling and generated artifacts

Build tools, deployment files, dependency manifests, generated clients, and
knowledge-graph artifacts enter the corpus only when they materially affect
or provide bounded discovery for an in-scope contract. They do not receive a
new domain classification and cannot independently establish business truth.

## 3. Evidence classification

Every evidence item receives exactly one primary class. Related evidence may
be cross-referenced, but classes are not blended to inflate confidence.

| Class | Exact definition | Permitted use | Limitation |
| --- | --- | --- | --- |
| `DIRECT` | A read-only observation of a repository source artifact or persisted schema/configuration artifact in the frozen audit revision, recorded without inferential transformation | Establish what code, schema, contract, configuration, or static artifact explicitly contains | Does not prove runtime reachability, product correctness, or governing authority |
| `DERIVED` | A reproducible conclusion computed or reasoned from identified evidence items using an explicit method | Establish lineage, comparison, inconsistency, or calculated audit conclusion | Must cite all material premises and method; cannot replace a missing premise |
| `RUNTIME` | A captured observation from executing or querying an identified non-production/runtime environment under recorded conditions | Establish observed behavior, output, failure, timing, or data shape in that environment | Does not establish universal behavior, production state, or semantic correctness by itself |
| `DOCUMENTATION` | A statement in a constitution, decision, ADR, glossary, specification, guide, comment, or other repository documentation | Establish normative authority, declared intent, vocabulary, or descriptive claim according to governance rank | Descriptive documentation may drift; comments do not outrank governing documents or verified behavior |
| `TEST` | A test definition, fixture, expected value, test result, coverage result, or reproducible test command | Establish an asserted invariant and whether the observed implementation satisfies it under the fixture | A passing test can encode the wrong rule; an unexecuted test is not a runtime result |
| `UNKNOWN` | A recorded state in which required evidence is absent, inaccessible, ambiguous, contradictory, stale, or insufficient to support a conclusion | Preserve uncertainty and trigger verification, disposition, or a readiness block | Must not be rewritten as absence, correctness, or non-applicability |
| `ASSUMPTION` | A clearly labeled provisional statement introduced to organize investigation when evidence has not yet established it | Guide discovery questions and identify evidence still required | Cannot verify a finding, assign semantic truth, close a gap, or support readiness |

`DIRECT` means direct observation of an artifact, not “authoritative truth.”
Normative authority is recorded separately using the governance hierarchy.
Runtime and test results are kept distinct from source observations so an
auditor cannot claim execution merely from reading code or tests.

Each evidence record contains:

- evidence id in the form `M34-E-####`;
- primary class;
- repository revision and observation date;
- path plus symbol, route, section, schema object, command, or fixture;
- minimal factual observation;
- capture method and environment, if applicable;
- authority level, when the item is normative;
- limitations and redactions;
- reviewer; and
- linked finding ids.

## 4. Finding classification

Each finding receives exactly one primary type and any necessary secondary
types. A finding is not a task or implementation proposal.

| Type | Definition |
| --- | --- |
| `SEMANTIC_DEFECT` | A term, value, state, or claim means something materially different from what its contract, owner, label, or user context asserts |
| `TERMINOLOGY_DEFECT` | One term has competing meanings, multiple terms claim one meaning, or language conflicts with the canonical glossary/domain vocabulary |
| `OWNERSHIP_DEFECT` | A concept is defined, calculated, or governed outside its owning domain, or an experience/transport layer becomes a source of truth |
| `TEMPORAL_DEFECT` | Observation, effective, event, period, retrieval, refresh, recording, or freshness time is absent, conflated, misleading, or incorrectly ordered |
| `CALCULATION_DEFECT` | A formula, unit, basis, aggregation, sign, period, benchmark, precision, or input rule is incorrect or inconsistent with its authoritative definition |
| `PRESENTATION_DEFECT` | Rendering, labeling, ordering, accessibility, or context causes a correct source fact to be hidden, distorted, or reasonably misunderstood |
| `FAILURE_TRANSPARENCY_DEFECT` | Missing, partial, stale, fallback, degraded, or failed data is hidden or presented as complete/current success |
| `EXPLAINABILITY_DEFECT` | A material value or claim lacks the provenance, basis, period, unit, method, or limitations needed for a user or reviewer to understand it |
| `READ_CONTRACT_DEFECT` | A producer/consumer contract loses, renames, overloads, or ambiguously represents an in-scope fact or status across a boundary |
| `LINEAGE_DEFECT` | The path from source fact through calculation, transport, transformation, or display cannot be established or is incorrectly attributed |
| `GOVERNANCE_DEFECT` | An artifact or decision violates governing authority, reopens a closed boundary, bypasses review, or records incompatible milestone status |
| `DOCUMENTATION_DRIFT` | Descriptive documentation and the verified implementation, test contract, or governing decision disagree |
| `DUPLICATE_CONCEPT` | More than one implementation, label, model, or owner claims the same business rule or truth without an approved projection boundary |
| `UNKNOWN_OWNERSHIP` | The governing owner of a material concept cannot be established from authoritative evidence |
| `MISSING_EVIDENCE` | A material correctness, product, lineage, ownership, freshness, or readiness claim lacks sufficient evidence |

Classification does not infer remediation. For example, a presentation defect
may be disposed by relabeling, excluding a claim, correcting a source
contract, or returning to the Architecture Review Board; the audit records the
decision without implementing it.

## 5. Severity and blocking model

Severity measures consequence if the finding remains unresolved. Confidence
and blocking status are recorded independently.

| Severity | Objective threshold | Default blocking rule |
| --- | --- | --- |
| `CRITICAL` | Contradicts a constitutional or closed-milestone boundary; materially fabricates portfolio/ledger truth; can cause a user to treat an invalid value as authoritative with significant financial consequence; or makes the audit itself constitutionally invalid | Immediately pauses dependent audit work and returns the issue to the Architecture Review Board. Blocks `READY_FOR_PORTFOLIO_HOME_SLICE` |
| `HIGH` | Materially misstates or obscures ownership, value, change, period, basis, freshness, completeness, contribution, attribution, risk, or provenance for a primary user question; duplicates a core rule across owners; or lacks evidence required to establish a primary displayed truth | Blocks `READY_FOR_PORTFOLIO_HOME_SLICE` until verified disposition. Does not automatically stop unrelated evidence collection |
| `MEDIUM` | Produces bounded ambiguity, inconsistency, or incomplete explanation that can mislead investigation but does not materially falsify a primary portfolio fact under ordinary use | Blocks the proposed slice when in its contract or surface; otherwise requires explicit exclusion, acceptance, or deferral before readiness |
| `LOW` | Localized clarity, consistency, navigation, or documentation issue with low risk of changing a reasonable user's financial interpretation | Non-blocking after owner and disposition are recorded |
| `INFORMATIONAL` | Verified observation, opportunity, or alignment note with no current defect or readiness consequence | Never blocks; cannot be used to hide an unresolved higher-severity concern |

The finding records one blocking status:

- `ARB_STOP`: audit work subject to the finding pauses under section 8;
- `M34_1_BLOCKER`: M34 may continue, but
  `READY_FOR_PORTFOLIO_HOME_SLICE` is prohibited;
- `CONDITIONAL_BLOCKER`: blocks only if the affected claim or surface remains
  in the proposed M34.1 slice;
- `NON_BLOCKING`: requires disposition but does not prevent readiness; or
- `PENDING_VERIFICATION`: blocking effect cannot yet be determined and the
  finding cannot close.

Severity cannot be lowered because remediation appears easy, a value is
popular, the UI is attractive, tests pass, or the affected code is legacy.
Reachability, affected users, financial consequence, visibility, recoverability,
and the five primary user questions must be evidenced, not assumed.

M34 may still complete with blocking findings by exiting
`SEMANTIC_REPAIR_REQUIRED` or `PRODUCT_CASE_NOT_PROVEN`. “Blocking” prevents a
READY exit; it does not force the audit to claim completion failed.

## 6. Decision recording format

### 6.1 Finding identifier and status

Finding ids are permanent and sequential: `M34-F-####`. An id is never reused
or renumbered. Closure does not delete history.

Permitted lifecycle states are:

```text
DRAFT -> VERIFIED -> CLASSIFIED -> IN_ARCHITECTURAL_REVIEW
      -> DISPOSITION_APPROVED -> CLOSED
```

A finding may move to `NEEDS_EVIDENCE`, `DISPUTED`, or `RETURNED_TO_ARB` from
any review state. Reopening a closed finding creates a recorded status change;
it does not rewrite the prior decision.

### 6.2 Standard finding template

```markdown
## M34-F-#### - <short factual title>

- Status:
- Primary type:
- Secondary types:
- Severity:
- Blocking status:
- Confidence: VERIFIED | PARTIAL | UNKNOWN
- Affected user questions:
- Affected surfaces/contracts:
- Owning domain:
- Evidence steward:

### Description

<What is observed, stated without proposed implementation.>

### Evidence

- M34-E-#### — <minimal observation and stable reference>
- M34-E-#### — <minimal observation and stable reference>

### Evidence limitations and conflicts

<Missing evidence, bounded searches, environment limitations, or competing
claims.>

### Owner and authority

<One concept owner, governing artifact, and any ownership dispute.>

### Constitutional concern

<Applicable law/principle: one concept/one owner, Experience renders truth,
correctness over capability, explainability, failure transparency, roadmap
governance, or another cited authority.>

### Proposed disposition

<One permitted disposition and why. No implementation design.>

### Readiness effect

<Exact effect on M34 outcome and M34.1 GO/NO-GO.>

### Review record

- Verified by / date:
- Domain-owner response / date:
- Architectural reviewer / date:
- Decision authority / date:
- Approved disposition:
- Closure evidence:
```

### 6.3 Permitted dispositions

The audit may propose and approve only these disposition categories:

- `ACCEPT_AS_CORRECT`;
- `SEMANTIC_REPAIR_REQUIRED`;
- `TERMINOLOGY_CORRECTION_REQUIRED`;
- `OWNERSHIP_CLARIFICATION_REQUIRED`;
- `DOCUMENTATION_CORRECTION_REQUIRED`;
- `EVIDENCE_REQUIRED`;
- `EXCLUDE_FROM_PORTFOLIO_HOME_SLICE`;
- `DEFER_WITH_EXPLICIT_RATIONALE`;
- `NO_ACTION_WITH_RATIONALE`; or
- `RETURN_TO_ARCHITECTURE_REVIEW_BOARD`.

The category records the decision, not a repair design. Any later
implementation requires its own authorized milestone or slice.

## 7. Review workflow

### 7.1 Discovery

- Select artifacts only from the section 2 corpus.
- Assign evidence ids and capture factual observations.
- Record negative-search bounds and unavailability.
- Create a `DRAFT` finding only when evidence indicates a potential issue;
  do not classify from naming alone.

**Exit:** relevant evidence references exist, or the absence of required
evidence is itself bounded and recorded.

### 7.2 Verification

- Reproduce the observation independently.
- Trace producer, transformation, contract, consumer, and governing
  documentation as applicable.
- Separate actual behavior from test expectation and written intent.
- Mark conflicts and limitations.

**Exit:** the factual description is `VERIFIED`, or the finding moves to
`NEEDS_EVIDENCE`/`UNKNOWN` without a positive conclusion.

### 7.3 Classification

- Assign primary/secondary type, severity, blocking status, confidence,
  affected user questions, and candidate owner.
- Apply the deterministic rules in sections 4 and 5.
- Do not propose code or reduce severity based on presumed repair cost.

**Exit:** classification is complete and internally reviewed.

### 7.4 Architectural review

- Confirm one concept/one owner and the governance hierarchy.
- Check cross-domain lineage, Experience boundaries, explainability,
  correctness, failure transparency, and closed M32/M33 boundaries.
- Resolve or escalate disputes; do not use majority or author preference.

**Exit:** ownership and constitutional consequences are agreed, or the
finding is `RETURNED_TO_ARB`.

### 7.5 Disposition

- Select exactly one section 6.3 disposition.
- State readiness impact and any evidence required for closure.
- Keep remediation design outside the finding.

**Exit:** an accountable decision authority accepts the disposition and its
blocking effect.

### 7.6 Approval

- Domain owner acknowledges factual accuracy.
- Architectural reviewer approves classification and constitutional handling.
- Architecture Review Board approves every `CRITICAL`, ownership dispute,
  scope dispute, and milestone-exit-affecting exception.

**Exit:** the review record names approvers, dates, and decision authority.

### 7.7 Closure

- Confirm closure evidence matches the approved disposition.
- Preserve the complete record and links.
- Recalculate the aggregate M34 readiness state without hiding excluded or
  deferred blockers.
- Synchronize governance only at the authorized M34 closure point.

**Exit:** finding is `CLOSED`, or remains visibly open with its blocking
effect. Closing the audit does not require closing every defect; it requires
an honest terminal M34 decision.

## 8. Stop conditions

The audit must pause the affected work and return to the Architecture Review
Board when:

1. governing constitutions, frozen M34 decisions, or closed M32/M33 decisions
   materially contradict one another;
2. completing the audit would require changing the five user questions,
   adding a domain, expanding exclusions, or redesigning M34;
3. a requested conclusion would weaken one-concept/one-owner, correctness,
   explainability, failure-transparency, or Experience ownership boundaries;
4. evidence indicates a `CRITICAL` constitutional or material portfolio-truth
   concern;
5. ownership of a primary portfolio truth cannot be resolved within existing
   authority, or two domains claim canonical ownership;
6. evidence collection would require production mutation, external account
   creation, credentials, secrets, personal data, destructive operations, or
   runtime authority not approved by M34;
7. a proposed disposition would reopen M32, M33, execution runtime, identity,
   provider adoption, or another explicit non-goal;
8. the audit cannot preserve independence, reproduce material evidence, or
   distinguish facts from assumptions;
9. an unknown or inaccessible source is necessary to support a readiness
   decision and no bounded alternative evidence exists;
10. the frozen exit choices no longer describe the evidence honestly; or
11. a governance artifact would need reinterpretation rather than ordinary
    synchronization.

Routine `HIGH`, `MEDIUM`, `LOW`, and `INFORMATIONAL` findings do not stop the
audit. They follow section 7 and affect readiness according to section 5.

## 9. WP1 deliverables

WP1 produces exactly these artifacts, all contained in this canonical
document:

1. the M34 audit charter and exclusions;
2. the repository audit corpus and corpus-maintenance rule;
3. the evidence classification taxonomy and evidence-record schema;
4. the finding classification taxonomy;
5. the severity and blocking model;
6. the standard finding and decision-record template;
7. the review workflow and approval responsibilities;
8. the Architecture Review Board stop conditions; and
9. the WP1 completion attestation below.

WP1 creates no evidence entries, finding register entries, semantic
dispositions, product-readiness result, M34.1 definition, roadmap change, or
Decision Log decision. Those belong to later authorized checkpoints.

## 10. Completion checklist

WP1 is complete only when every item below is true:

- [x] The audit objective is limited to the approved M34 purpose and five user
  questions.
- [x] Implementation, runtime change, M32/M33 reopening, provider adoption,
  identity/RBAC, and redesign are explicitly excluded.
- [x] Corpus inclusion and mixed-file scoping rules are deterministic.
- [x] Experience, Portfolio, Analytics, Market Data, Ledger, Portfolio
  Intelligence, AI Evaluation, Documentation, Tests, and Governance corpus
  areas are defined.
- [x] Direct, derived, runtime, documentation, test, unknown, and assumption
  evidence classes have non-interchangeable definitions.
- [x] Evidence traceability, bounded negative claims, conflicts, redaction,
  and reproducibility rules are defined.
- [x] Finding types cover semantic, terminology, ownership, time,
  calculation, presentation, governance, drift, duplication, unknown owner,
  and missing evidence concerns.
- [x] Severity is separated from confidence, disposition, and blocking status.
- [x] Objective blocking rules preserve all three permitted M34 exit results.
- [x] One concept/one owner and Experience-renders-truth ownership are
  explicit.
- [x] The standard finding record includes id, description, evidence, owner,
  constitutional concern, proposed disposition, and blocking status.
- [x] Discovery, verification, classification, architectural review,
  disposition, approval, and closure have entry/exit expectations.
- [x] Stop conditions identify when Architecture Review Board intervention is
  mandatory.
- [x] WP1 creates no findings and makes no product-readiness judgment.
- [x] M34.1 remains NO-GO.

**Completion attestation:** M34-WP1 freezes the audit method only. Later work
packages may populate evidence and findings under this protocol but may not
silently change its scope, classifications, blocking rules, ownership model,
or review authority. Any material amendment requires a versioned change and
Architecture Review Board approval.

## 11. Explicit non-adoption statement

M34-WP1 does not:

- inspect or judge application source behavior;
- create a repository finding or classify a known issue;
- run application, frontend, backend, database, analytics, provider, or
  runtime tests;
- modify Python, TypeScript, SQL, dependencies, configuration, generated
  artifacts, or runtime state;
- implement or design Portfolio Home;
- change any portfolio, analytics, market-data, ledger, intelligence, AI, or
  Experience behavior;
- create a Workspace, Trust, Read Model, or other domain;
- update the roadmap or Decision Log with a new architecture decision;
- authorize M34.1; or
- reopen M32 or M33.
