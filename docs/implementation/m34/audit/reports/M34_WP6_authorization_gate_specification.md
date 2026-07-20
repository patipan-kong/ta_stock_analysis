# M34-WP6 - Authorization Gate Specification

**Date:** 2026-07-20

**Status:** Complete as a procedural specification for a future Architecture
Review Board authorization gate. The gate has not been convened.

**Current authorization:** None. WP6 remains `WP6_BLOCKED`. M34.1 remains
`NO-GO`. Runtime adoption and implementation remain unauthorized.

## 1. Gate question

The gate answers exactly one question:

> Is sufficient implementation-readiness evidence available to authorize
> WP6?

The gate evaluates evidence and records an authorization decision. This
specification does not answer the question, authorize work, or prejudge the
future Board decision.

## 2. Purpose

The purpose of the gate is to establish a controlled boundary between three
independent states:

```text
Frozen governance
  establishes eligible meaning and scope
                |
                v
Future authorization gate
  evaluates implementation-readiness evidence and decides whether work may begin
                |
                v
Implementation
  begins only if, and only within the scope that, the gate expressly authorizes
```

The gate prevents governance completion from being mistaken for permission to
implement. It also prevents repository preparation, planning activity, meeting
discussion, package completeness, or absence of objection from becoming
implicit authorization.

## 3. Authority

The Architecture Review Board is the decision authority for this gate. The
Board acts under the existing M34 decision and checkpoint framework and the
authority already recorded by `M34-D-0012`.

The frozen governance corpus is a binding input, not a subject of this gate.
In particular, the Board shall consume without reopening:

- DQ-01 through DQ-12 and `M34-D-0001` through `M34-D-0012`;
- the canonical Glossary and approved semantic mappings;
- the corrected admission manifest containing 18 `WP6_INCLUDED` candidates
  and 22 `WP6_EXCLUDED` families;
- the final independent architectural approval in `M34-R-0021`;
- the `M34-CP2` readiness checkpoint and `M34-R-0022`; and
- the M34-WP6A governance closeout and `M34-R-0023`.

The Board may verify the identity, completeness, currency, and integrity of
these inputs. It shall not reconsider their substance during this gate.

## 4. Scope

The gate evaluates whether the submitted WP6 work boundary is ready to begin.
Its scope is limited to:

- the exact `WP6_INCLUDED` claim families, decomposed concepts, and permitted
  verification boundaries submitted for authorization;
- the repository revision and affected repository areas named by the
  submission;
- technical dependencies and integration assumptions needed to start the
  submitted work safely;
- verification and acceptance evidence sufficient to determine whether the
  authorized work can be evaluated objectively;
- operational containment, rollback, observability, and production-control
  readiness applicable to the submitted work;
- accountable roles and required approvals for executing and verifying the
  submitted work; and
- preservation of all frozen exclusions, especially M32, M33,
  `STOPPED_AUTHORITY`, the 22 `WP6_EXCLUDED` families, M34.1, and runtime
  adoption.

The submission may request authorization for all or a bounded subset of the
18 eligible families. A smaller submitted scope is an authorization boundary,
not a change to the admission manifest. Every family not expressly named in
an approved gate result remains blocked.

## 5. Explicit non-scope

The gate shall not:

- review, amend, reinterpret, supersede, or improve frozen governance;
- reopen DQ-01 through DQ-12, M32, M33, or M34-WP6A;
- appoint an owner, define a term, change a semantic boundary, or alter the
  18/22 admission partition;
- redesign architecture, domains, product surfaces, contracts, persistence,
  or runtime behavior;
- select implementation techniques or produce an implementation plan;
- evaluate the correctness of portfolio calculations or current product
  behavior;
- perform code changes, migrations, deployments, runtime mutations, provider
  calls, or production experiments;
- authorize a `WP6_EXCLUDED` family by implication;
- authorize Portfolio Home or M34.1;
- restore execution, planning, intent, approval, authorization, or actor
  attribution prohibited by M32, M33, or `STOPPED_AUTHORITY`; or
- treat gate-package preparation as an authorization decision.

## 6. Evidence standard

Evidence submitted to the gate must be repository-backed or identify a stable
approved external record, traceable to the exact submitted scope, and current
for the repository revision and environment boundary it claims to describe.
Intent, expectation, naming, meeting notes, and unrecorded assurances are not
sufficient evidence.

Each evidence item receives one gate assessment:

| Assessment | Meaning |
| --- | --- |
| `PASS` | The mandatory readiness assertion is directly and sufficiently supported for the submitted scope. |
| `FAIL` | Evidence establishes that the readiness assertion is not satisfied. |
| `UNKNOWN` | Evidence is missing, stale, contradictory, inaccessible, or insufficient. |
| `NOT_APPLICABLE` | The category demonstrably does not apply to the submitted scope, with a recorded rationale. |

`UNKNOWN` is not a favorable assumption. `NOT_APPLICABLE` requires evidence of
non-applicability and cannot be used merely because evidence is inconvenient
to obtain.

The gate does not itself authorize new runtime evidence collection. Existing
read-only, test, or runtime evidence may be considered when it was collected
under valid authority and its environment, command, fixture, result, and date
are reproducible. If decisive evidence requires activity that is not already
authorized, the gate remains blocked until that evidence can lawfully be
supplied.

## 7. Required evidence

Every submission must contain the following evidence. The evidence may be
organized in existing repository artifacts; the gate requires the content and
traceability, not a particular document layout.

### 7.1 Gate identity and immutable baseline

- the proposed gate identifier and decision authority;
- the exact repository revision and submission timestamp;
- references to `M34-R-0021`, `M34-CP2`, `M34-R-0022`, the governance
  closeout, and `M34-R-0023`;
- proof that the frozen governance inputs and the 18/22 admission partition
  have not been silently replaced or modified; and
- the current status statement showing WP6 blocked before the gate decision.

### 7.2 Exact authorization boundary

- the exact submitted `WP6_INCLUDED` families and, for decomposed families,
  the exact concepts and permitted verification scope;
- the repository areas, interfaces, data boundaries, and environments that
  the requested authorization would permit work to affect;
- every excluded family, concept, operation, environment, and authority that
  remains outside the request;
- a trace from each submitted item to its admission-manifest row, owner,
  canonical vocabulary, and semantic mapping; and
- proof that no excluded concept is indirectly required as a semantic input,
  verification target, or inferred authority.

### 7.3 Repository and dependency readiness

- a reproducible repository baseline and evidence that the proposed work can
  be isolated from unrelated or unreviewed changes;
- the relevant build, dependency, schema, contract, configuration, and
  integration assumptions for the submitted boundary;
- the availability and ownership of required dependencies;
- identified incompatibilities, unresolved dependency states, or assumptions
  that could prevent safe commencement; and
- evidence that generated, cached, copied, or implementation-local material
  will not substitute for canonical semantics.

### 7.4 Technical change containment

- a bounded description of the intended change surface and its architectural
  constraints, without prescribing implementation steps;
- the invariants that must remain true across source domains, transports,
  presentation, persistence, and failure states;
- backward-compatibility and coexistence boundaries where existing consumers
  remain in use;
- data ownership, provenance, temporal, and degraded-state obligations for
  every affected claim; and
- evidence that the submitted boundary does not depend on architecture or
  governance changes that have not been approved.

### 7.5 Verification and acceptance readiness

- objective acceptance criteria for every submitted claim or decomposed
  concept;
- a traceable verification approach covering semantic conformance, contract
  conformance, provenance, failure transparency, and applicable negative
  guarantees;
- identified fixtures, datasets, environments, or observation boundaries
  needed for verification, together with their availability and authority;
- a method for recording pass, fail, unknown, and partial results without
  converting uncertainty into readiness; and
- independent review responsibility for the resulting evidence.

The gate evaluates whether this verification basis is executable and
objective. It does not execute the verification or decide the future WP6
results.

### 7.6 Data, security, and boundary controls

- the data classifications and access boundaries applicable to the submitted
  scope;
- required identity, authorization, secrets, privacy, and audit controls;
- evidence that no stopped M33 identity, approval, or execution authority is
  assumed;
- evidence that Ledger facts are not promoted into proof of plan, approval,
  intent, actor identity, or execution authorization; and
- the containment rule for any legacy or opaque excluded artifact reachable
  from an included verification boundary.

### 7.7 Operational readiness

- the environments in which authorized work may occur and the controls that
  prevent unapproved production or runtime adoption;
- change isolation, deployment preconditions, rollback or disablement
  capability, and recovery ownership applicable to the requested scope;
- observability sufficient to detect boundary breaches, degraded states,
  data-quality failures, and unintended runtime effects;
- incident escalation and stop-work criteria; and
- evidence that operational controls exist before implementation begins or
  are explicitly outside the requested authorization because no runtime
  change is permitted.

### 7.8 Organizational readiness and risk acceptance

- one accountable implementation owner for the submitted work boundary;
- named semantic-owner reviewers for affected concepts without transferring
  implementation responsibility to them;
- named verification and operational approvers where applicable;
- an evidence-backed readiness risk register limited to the submitted scope,
  with owners and treatment state; and
- confirmation that the Board members deciding the gate have the authority
  and independence required by existing project governance.

## 8. Evaluation categories

The Board shall evaluate the package in the following categories. Each
category receives `PASS`, `FAIL`, `UNKNOWN`, or `NOT_APPLICABLE`.

| Category | Gate question within the category | Mandatory result |
| --- | --- | --- |
| Governance-input integrity | Are the frozen eligibility inputs present, unchanged, and traceable? | `PASS` |
| Authorization-scope integrity | Is the requested boundary exact, contained within `WP6_INCLUDED`, and free of implicit admission? | `PASS` |
| Repository integrity | Is the baseline reproducible and isolated from unrelated or unreviewed state? | `PASS` |
| Dependency readiness | Are required technical and organizational dependencies available and their assumptions explicit? | `PASS` or evidenced `NOT_APPLICABLE` |
| Architectural containment | Can the work begin without redesign, unapproved authority, or boundary transfer? | `PASS` |
| Verification readiness | Are acceptance criteria, evidence methods, fixtures, and reviewers objective and available? | `PASS` |
| Data and security readiness | Are applicable access, provenance, privacy, and stopped-authority controls established? | `PASS` or evidenced `NOT_APPLICABLE` |
| Operational readiness | Are isolation, rollback/disablement, observability, escalation, and production controls sufficient for the requested boundary? | `PASS` or evidenced `NOT_APPLICABLE` |
| Risk accountability | Are all material readiness risks explicit, bounded, owned, and acceptable to the decision authority? | `PASS` |
| Milestone containment | Do M32, M33, M34.1, runtime adoption, and every unsubmitted or excluded family remain blocked? | `PASS` |

No category average or majority vote can compensate for a mandatory `FAIL` or
`UNKNOWN`.

## 9. Evaluation process

### 9.1 Submission freeze

The gate secretary records the submission revision, evidence index, requested
scope, current status, and decision authority. Evidence added after the freeze
is treated as a revision and is explicitly logged.

### 9.2 Administrative completeness check

The secretary verifies that every required evidence category is present and
cross-referenced. This check does not assess substance and does not authorize
the gate to proceed when a mandatory item is missing.

### 9.3 Independent category assessment

Qualified reviewers assess each category against section 8. Reviewers record
the evidence used, result, rationale, conflicts, unknowns, and any declared
non-applicability. They do not redesign the submission or repair its evidence
during review.

### 9.4 Boundary reconciliation

Before deliberation, the secretary reconciles the submitted scope against the
canonical admission manifest and confirms that:

- every requested item is eligible;
- every decomposed concept retains its exact owner and vocabulary;
- every omitted or excluded item remains explicitly blocked; and
- no implementation or operational dependency indirectly imports an excluded
  semantic concept or stopped authority.

This is a containment check, not a governance review.

### 9.5 Board deliberation

The Board considers only the frozen submission and recorded assessments. It
may accept evidence, reject evidence, or determine that evidence is unknown.
It shall not fill an evidentiary gap with intent, amend governance, or invent
an implementation solution.

### 9.6 Decision and recording

The Board answers the gate question for the exact submitted scope and records
one outcome from section 11. No work begins until the canonical authorization
record is approved and effective.

## 10. Decision criteria

The answer to the gate question may be **Yes** only when all of the following
are true:

1. every mandatory category in section 8 is `PASS` or an expressly permitted,
   evidenced `NOT_APPLICABLE`;
2. no mandatory assertion is `FAIL` or `UNKNOWN`;
3. the requested scope is an explicit subset of `WP6_INCLUDED` and names each
   authorized family and decomposed concept;
4. the evidence is traceable to the frozen submission revision and is not
   materially stale or contradictory;
5. objective acceptance and verification criteria exist for the entire
   requested scope;
6. material readiness risks are visible, accountable, and accepted by the
   proper decision authority;
7. implementation can begin without a governance change, architectural
   redesign, excluded semantic dependency, or unauthorized runtime action;
8. M32, M33, `STOPPED_AUTHORITY`, all `WP6_EXCLUDED` concepts, unsubmitted
   eligible families, M34.1, and runtime adoption remain explicitly outside
   the authorization; and
9. the Board records an approved, effective authorization result rather than
   relying on package completion, meeting consensus, or absence of objection.

Non-blocking observations may be recorded only when they do not weaken a
mandatory criterion, defer a precondition needed to start work, or require an
unapproved change. A condition that must be satisfied before work can safely
begin is missing readiness evidence and therefore prevents authorization.

## 11. Possible gate outcomes

| Outcome | Answer to gate question | Effect |
| --- | --- | --- |
| `WP6_AUTHORIZED` | Yes, for the exact enumerated scope | Permits WP6 implementation work to begin only within the recorded boundary and controls. Everything else remains unauthorized. |
| `WP6_BLOCKED_NEEDS_EVIDENCE` | No, not yet | Records the exact missing, stale, contradictory, or unknown readiness evidence. No implementation authority is created. |
| `WP6_NOT_AUTHORIZED` | No | Records that the submitted evidence is sufficient to decide but one or more mandatory criteria fail or the residual readiness risk is not accepted. |
| `GATE_SUBMISSION_INVALID` | No valid gate decision is possible | Records an invalid authority, corrupted baseline, out-of-manifest scope, or inability to preserve the frozen governance boundary. The gate does not reopen governance. |

`WP6_AUTHORIZED` never authorizes more than the exact submitted and enumerated
scope. There is no implied partial authorization. A Board wishing to consider
a smaller scope must evaluate and record that smaller scope explicitly.

## 12. Authorization record

Every convened gate must produce one canonical M34 `CHECKPOINT_RESULT` in the
Decision Register and one append-only Review Log event. The record must
contain:

- the gate and decision identifiers;
- the exact gate question;
- the submission revision, date, and evidence index;
- the Board authority and participating reviewer roles;
- the exact requested scope and every retained exclusion;
- the assessment and rationale for every category in section 8;
- all blocking unknowns, failures, observations, and accepted risks;
- one outcome from section 11;
- for `WP6_AUTHORIZED`, the exact families, decomposed concepts, repository
  boundary, environments, controls, and validity conditions authorized;
- an explicit statement that M34.1 and runtime adoption remain unauthorized;
- confirmation that M32, M33, and `STOPPED_AUTHORITY` remain intact;
- the effective time and any evidence-staleness or material-change condition
  that requires a new gate; and
- traceability to `M34-D-0012`, `M34-R-0021`, `M34-CP2`, `M34-R-0022`, the
  governance closeout, and `M34-R-0023`.

The authorization record is the only evidence that WP6 may begin. Drafts,
minutes, review comments, package manifests, and this specification are not
authorization records.

## 13. Decision principles

The Board shall apply these principles:

1. **Authorization is explicit.** Silence, readiness, approval for review, or
   completion of governance does not authorize work.
2. **Evidence overrides intent.** A stated plan or expected outcome cannot
   replace missing readiness evidence.
3. **Scope is exact.** Authority attaches only to enumerated families,
   concepts, repository boundaries, environments, and controls.
4. **Unknown blocks.** A material unknown cannot be accepted as a favorable
   assumption.
5. **Eligibility is not authorization.** `WP6_INCLUDED` means eligible for
   consideration, not permitted to implement.
6. **Dependency does not transfer ownership.** Implementation composition
   never changes constitutional semantic ownership.
7. **Presentation and storage own no supplied truth.** Routes, tables, APIs,
   caches, components, and aggregators cannot substitute for a semantic owner.
8. **Negative guarantees remain negative.** `STOPPED_AUTHORITY` cannot become
   execution, approval, planning, intent, authorization, or actor identity.
9. **Operational safety is part of readiness.** Work is not ready when its
   permitted environment, containment, recovery, or observation boundary is
   unknown.
10. **A gate decision is not implementation.** The Board may authorize work;
    it does not perform, design, validate, or adopt the resulting changes.

## 14. Relationship to governance

Governance answers what each concept means, who owns it, which vocabulary is
canonical, and which claim families are eligible. Those answers are complete,
approved, synchronized, frozen, and outside this gate.

The gate uses governance as a constraint on authorization. It may reject or
invalidate a submission that does not preserve the frozen boundary, but it
may not correct that boundary, reinterpret it, or create substitute authority.
Discovery of a direct conflict is recorded as an invalid or blocked
submission and escalated under existing authority; it is not resolved inside
the gate.

## 15. Relationship to implementation

Before an effective `WP6_AUTHORIZED` result, implementation authority is
`NONE` and WP6 remains `WP6_BLOCKED`.

After an effective `WP6_AUTHORIZED` result, implementation may begin only:

- for the exact recorded scope;
- within the recorded repository and environment boundaries;
- under the recorded controls and accountable roles; and
- while all retained exclusions and non-authorizations remain in force.

Authorization does not establish that implementation is correct, complete,
accepted, deployed, or adopted at runtime. Those states require their own
evidence and later decisions under the existing milestone process.

## 16. Success conditions

The gate is successfully completed when:

- the submitted baseline and scope are frozen and traceable;
- every required category has a recorded assessment;
- the Board applies the criteria without reopening governance or designing
  implementation;
- the gate question is answered for one exact scope;
- the canonical `CHECKPOINT_RESULT` and Review Log event are complete,
  approved where required, and mutually traceable;
- every retained exclusion and non-authorization is explicit; and
- the resulting project status is unambiguous.

Gate-process success does not require authorization. A well-evidenced
`WP6_BLOCKED_NEEDS_EVIDENCE`, `WP6_NOT_AUTHORIZED`, or
`GATE_SUBMISSION_INVALID` result is a successful gate process when it records
the decision and blockers correctly.

## 17. Failure conditions

The gate cannot authorize WP6 when any of the following is true:

- a mandatory evidence category is missing, failed, unknown, materially
  stale, contradictory, or unsupported;
- the requested scope is ambiguous, exceeds `WP6_INCLUDED`, or indirectly
  admits an excluded concept;
- the repository baseline or evidence set is not reproducible;
- acceptance criteria or verification responsibility are not objective and
  complete;
- a required dependency, data boundary, security control, operational
  control, rollback/disablement mechanism, or accountable role is absent;
- material risk lacks an owner or is not accepted by the proper authority;
- commencement depends on architectural redesign, new governance, semantic
  reinterpretation, or unauthorized runtime activity;
- M32, M33, `STOPPED_AUTHORITY`, M34.1, or runtime-adoption boundaries are
  weakened;
- the decision authority or required review independence is not established;
  or
- no approved canonical authorization record exists.

## 18. Non-authorization statement

This document defines the future gate only. It does not convene the gate,
evaluate a submission, create a gate finding, allocate a decision or review
identifier, approve evidence, authorize WP6, authorize M34.1, authorize
runtime adoption, or permit implementation.

Current state remains:

```text
Governance:              COMPLETE AND FROZEN
Future Gate Readiness:   APPROVED
Authorization Gate:      NOT CONVENED
WP6:                     WP6_BLOCKED
M34.1:                   NO-GO
Runtime authority:       NONE
Implementation authority: NONE
```
