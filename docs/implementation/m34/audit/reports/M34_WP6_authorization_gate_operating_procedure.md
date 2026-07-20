# M34-WP6 - Authorization Gate Operating Procedure

**Date:** 2026-07-20

**Status:** Complete as the administrative operating procedure for a future
M34-WP6 Authorization Gate. No gate has been convened by this document.

**Normative gate specification:**
`M34_WP6_authorization_gate_specification.md`

**Current authorization:** None. WP6 remains `WP6_BLOCKED`. M34.1 remains
`NO-GO`. Runtime adoption and implementation remain unauthorized.

## 1. Purpose

This procedure defines how the Architecture Review Board convenes, conducts,
records, and closes a future M34-WP6 Authorization Gate.

The procedure is administrative and decision-oriented. It implements the
process required to answer the normative gate question:

> Is sufficient implementation-readiness evidence available to authorize
> WP6?

The substantive scope, evidence requirements, evaluation categories,
decision criteria, outcomes, and authorization-record requirements are
defined exclusively by the normative Authorization Gate Specification. This
procedure does not alter them.

This document does not evaluate a submission, convene a gate, create an
authorization, or authorize implementation.

## 2. Operating principles

The gate operates under these procedural principles:

1. **Governance is a frozen input.** Participants verify input identity and
   integrity but do not review or reinterpret governance.
2. **Submission precedes review.** No evidence is evaluated until it is
   registered against an exact request and repository baseline.
3. **Evidence is visible.** Accepted, rejected, withdrawn, replaced,
   conflicting, and stale evidence remains traceable.
4. **Oral statements are not evidence.** A material assertion must resolve to
   a frozen evidence item before it can affect a category assessment.
5. **Unknown remains unknown.** Discussion, confidence, seniority, or vote
   count cannot repair missing or contradictory evidence.
6. **Scope cannot expand during deliberation.** Only a frozen and assessed
   scope may receive a decision.
7. **One canonical outcome is recorded.** Drafts, minutes, reviewer opinions,
   and administrative validation are not gate decisions.
8. **Authorization is effective only through the canonical record.** A Board
   discussion or announced intention does not permit work to begin.

## 3. Preconditions for convening the gate

The Gate Secretary shall not open a gate review until all of the following
are objectively established:

- the normative Authorization Gate Specification is approved, frozen, and
  identified by repository path and revision;
- M34-WP6A is closed and its frozen governance inputs are available;
- `M34-R-0021`, `M34-CP2`, `M34-R-0022`, the M34-WP6A governance closeout,
  and `M34-R-0023` are present and mutually traceable;
- the canonical admission partition remains 18 `WP6_INCLUDED` candidates and
  22 `WP6_EXCLUDED` families, with none unaccounted or duplicated;
- WP6 is still `WP6_BLOCKED` and neither implementation nor runtime authority
  has already been inferred from readiness evidence;
- a Submission Owner has filed one bounded gate request;
- the requested scope is stated as an exact subset of `WP6_INCLUDED`;
- the applicable ARB authority, participation, quorum, and decision rules are
  identified from existing project governance;
- a Gate Secretary and the required independent reviewers are identified;
- a reviewable repository baseline and evidence index exist; and
- no known material repository drift or unresolved submission-identity issue
  prevents the package from being frozen.

Failure of a precondition returns the request for administrative correction or
records it as invalid, as applicable. It does not create a gate outcome unless
the Board has formally convened and applies the normative outcome rules.

## 4. Participants and responsibilities

One person may hold more than one role only when existing project governance
permits it and the role combination does not defeat required independence.
Every role assignment and any declared conflict of interest is recorded before
the evidence freeze.

### 4.1 Architecture Review Board

The Architecture Review Board is the sole gate decision authority. It:

- confirms that it is properly constituted under existing authority;
- considers the frozen submission and recorded reviewer assessments;
- determines the final assessment of each evaluation category;
- decides whether material risks are acceptable within its authority;
- applies the decision criteria without changing them;
- selects exactly one normative gate outcome;
- approves the exact authorization boundary when the outcome is
  `WP6_AUTHORIZED`; and
- approves the canonical decision record.

The Board does not repair the submission, design implementation, amend frozen
governance, or create evidence through deliberation.

### 4.2 Gate Secretary

The Gate Secretary is the custodian of procedure and records. The Secretary:

- registers the request and assigns or records the gate identifier through
  the existing identifier process;
- validates administrative completeness without judging substantive
  readiness;
- maintains the submission manifest, evidence index, revision history, and
  participant list;
- records evidence status and preserves replaced, rejected, withdrawn, and
  stale items;
- declares the administrative evidence freeze after all freeze conditions are
  met;
- schedules reviews and distributes the identical frozen package;
- records reviewer assessments, conflicts, questions, responses, and Board
  deliberation;
- performs the admission-boundary reconciliation mechanically and records any
  unresolved semantic-containment question for Board determination;
- drafts the canonical outcome record exactly as decided by the Board;
- appends or coordinates the required Review Log event after the decision;
  and
- completes gate closeout and repository cross-reference validation.

The Secretary role carries no decision authority. If the Secretary is also a
voting Board member under existing rules, that separate role must be declared
and recorded.

### 4.3 Submission Owner

The Submission Owner is accountable for the accuracy and completeness of the
gate request. The Submission Owner:

- defines the exact requested authorization boundary;
- supplies the required evidence and stable locators;
- identifies known gaps, conflicts, assumptions, exclusions, dependencies,
  risks, and evidence limitations;
- answers reviewer questions by referencing existing evidence or submitting a
  controlled evidence revision;
- declares material repository or environment changes promptly;
- confirms the final frozen package represents the request; and
- accepts return, withdrawal, or a non-authorizing outcome without treating
  further preparation as authorization.

The Submission Owner may explain the package but may not self-approve evidence
or the gate outcome.

### 4.4 Reviewers

Reviewers perform independent category assessments. Collectively, the assigned
reviewers must cover every evaluation category in the normative specification.
Each reviewer:

- declares independence, role, scope, and conflicts of interest;
- uses only the frozen evidence package;
- assesses assigned categories as `PASS`, `FAIL`, `UNKNOWN`, or
  `NOT_APPLICABLE`;
- cites the exact evidence supporting every assessment;
- records contradictions, limitations, residual risks, and questions;
- distinguishes evidence rejection from an unfavorable assessment of accepted
  evidence;
- does not repair evidence, redesign the submission, or negotiate an outcome;
  and
- signs or otherwise confirms the final assessment attributed to that
  reviewer.

A reviewer opinion is advisory evidence for Board deliberation. It is not the
canonical gate decision.

### 4.5 Observers

Observers are optional. Their identity, role, and reason for attendance are
recorded. Observers:

- have no gate decision authority by virtue of observer status;
- do not vote or participate in category assessment;
- may answer a factual question only when invited by the presiding Board
  member;
- may not introduce unindexed evidence or privately brief decision-makers;
- comply with the same confidentiality and boundary rules as other
  participants; and
- are not treated as approval, consultation, or sign-off unless separately
  assigned an authorized role.

## 5. Submission requirements

The gate request must be a single controlled submission containing, or
indexing, all content required by the normative specification. At minimum it
must state:

- the proposed gate identifier, request date, Submission Owner, and decision
  authority;
- the exact repository revision and relevant environment boundary;
- the exact requested `WP6_INCLUDED` families and decomposed concepts;
- the permitted repository, interface, data, and environment boundaries;
- the complete set of retained exclusions and non-authorizations;
- a mapping from every requested item to the admission manifest, canonical
  vocabulary, semantic mapping, and constitutional owner;
- an evidence index organized by every required-evidence section and
  evaluation category in the normative specification;
- the requested category result supported by each evidence group, without
  presenting that request as a Board determination;
- known evidence conflicts, gaps, staleness concerns, and declared
  non-applicability;
- technical, operational, organizational, data, security, and milestone
  readiness risks within the submitted scope;
- accountable implementation, verification, semantic-review, and operational
  roles as applicable; and
- an attestation that the submission does not request governance change,
  excluded scope, M34.1, runtime adoption, or stopped M32/M33 authority.

References must use stable repository paths, canonical identifiers, or stable
approved external record locators. Proximity, naming, or undocumented meeting
context is not a reference.

## 6. Evidence submission workflow

Gate evidence follows this procedural lifecycle:

```text
PROPOSED
   |
   v
REGISTERED -----> REJECTED
   |
   v
ACCEPTED_FOR_REVIEW -----> WITHDRAWN
   |                 \
   v                  -> SUPERSEDED
FROZEN
   |
   +-----> STALE
   |
   v
ASSESSED
   |
   v
RETAINED_WITH_GATE_RECORD
```

These are gate-package custody states. They do not overwrite the lifecycle or
authority of any canonical M34 Evidence Register record.

### 6.1 Proposal and registration

The Submission Owner supplies an evidence item with a unique package locator,
source locator, purpose, applicable scope, collection or publication date,
repository or environment boundary, and known limitations. The Secretary
registers the item without treating registration as acceptance or proof.

### 6.2 Acceptance for review

An item is accepted for review when it is readable, traceable, within the gate
scope, sufficiently identified for independent examination, and lawfully
available to the reviewers. Acceptance means only that the item may be
evaluated. It does not mean the item is correct, sufficient, authoritative, or
supportive of authorization.

### 6.3 Rejection

An evidence item is rejected from the review set when it is out of scope,
untraceable, inaccessible, unlawfully obtained, materially unidentified, or
incapable of supporting the assertion for which it was submitted. The item,
reason, decision-maker, and date remain in the evidence index. Rejection may
create an evidence gap; it never silently removes the underlying requirement.

Administrative rejection may be made by the Secretary for missing mandatory
identity fields. Substantive rejection is recorded by the assigned reviewer
and confirmed by the Board when it affects a gate category or outcome.

### 6.4 Replacement and supersession

An item may be replaced before or after freeze only through a new registered
version that identifies the prior item and explains the change. The prior
version remains visible as `SUPERSEDED`. A post-freeze replacement is late
evidence and triggers the revision rules in section 8.3.

### 6.5 Withdrawal

The Submission Owner may withdraw an item or the entire submission before the
Board records its decision. The withdrawal, reason, time, and affected
requirements remain visible. Withdrawal of material evidence reopens the
affected category assessment and normally ends the freeze. A withdrawn item
cannot support the decision.

### 6.6 Staleness

Evidence is declared stale when a material change makes its claimed repository
revision, dependency state, environment, control, role, risk, or observation
boundary no longer current. The evidence remains visible with the staleness
reason and time. Stale evidence cannot support `PASS` unless a reviewer and the
Board establish, from frozen evidence, that the change is immaterial to the
assertion.

### 6.7 Retention

All evidence states and assessment links are retained with the gate record.
No item used in deliberation is deleted merely because it was rejected,
withdrawn, superseded, stale, or unfavorable.

## 7. Gate phases

The gate uses the following ordered phases:

```text
REQUESTED
   -> ADMINISTRATIVE_VALIDATION
   -> EVIDENCE_FREEZE
   -> INDIVIDUAL_REVIEW
   -> BOUNDARY_RECONCILIATION
   -> BOARD_DELIBERATION
   -> DECISION_RECORDING
   -> GATE_CLOSEOUT
```

A phase may return the package to an earlier phase. Such return is recorded
and never represented as uninterrupted progress.

### 7.1 Phase 1 - Gate request

The Submission Owner submits the package. The Secretary records receipt,
request scope, baseline, participants, current authorization state, and the
version of the normative specification being applied.

Output: registered request and initial package manifest. No review has begun.

### 7.2 Phase 2 - Administrative validation

The Secretary checks preconditions, required sections, locators, participant
assignments, declarations, and package readability. The Secretary records each
item as present, absent, malformed, or awaiting correction without judging its
substantive adequacy.

Output: administrative validation record and either acceptance for freeze or
return to the Submission Owner.

### 7.3 Phase 3 - Evidence freeze

When the package is administratively complete, the Secretary records:

- the repository revision;
- the complete evidence index and content hashes or equivalent immutable
  locators where available;
- the exact submitted authorization boundary;
- the participant and reviewer assignments;
- known conflicts, gaps, assumptions, and non-applicability claims; and
- the freeze time.

All reviewers receive the same frozen package. Material changes after this
point require a recorded revision and re-freeze. The freeze is administrative;
it does not validate evidence.

Output: evidence-freeze record.

### 7.4 Phase 4 - Individual review

Reviewers independently assess their assigned categories. Questions are
routed through the Secretary and answered on the shared record. A response
that adds a material assertion or source is new evidence and follows the
revision process; it is not accepted through discussion alone.

Output: one signed or confirmed assessment per reviewer assignment, with no
uncovered evaluation category.

### 7.5 Phase 5 - Boundary reconciliation

The Secretary prepares a mechanical reconciliation between the frozen request
and the canonical admission manifest. Assigned reviewers evaluate substantive
containment where necessary. The reconciliation records:

- requested eligible families and decomposed concepts;
- owners, vocabulary, and permitted verification boundaries;
- unsubmitted eligible families;
- all excluded families and opaque concepts;
- repository, data, interface, environment, and operational boundaries; and
- any direct or indirect dependency that could import excluded meaning or
  authority.

Output: boundary-reconciliation record. Any unresolved material ambiguity is
`UNKNOWN` and proceeds as a blocker; it is not normalized by the Secretary.

### 7.6 Phase 6 - Board deliberation

The Board confirms authority and quorum under existing rules, reviews the
category assessments and boundary reconciliation, hears bounded explanations,
resolves evidence-weight questions where the record permits, and determines
one final result for each category.

The frozen submission cannot be expanded, repaired, or informally narrowed
during deliberation. If the Board wishes to consider a smaller scope, that
scope must already have an independently complete assessment or be returned
for a revised submission and re-freeze.

Output: recorded category determinations, risk-acceptance decisions, and one
selected normative outcome.

### 7.7 Phase 7 - Decision recording

The Secretary drafts the canonical `CHECKPOINT_RESULT` and Review Log event
from the Board's recorded decision. The Board verifies that the draft contains
the exact outcome, scope, evidence, rationale, retained exclusions, status
effects, and non-authorizations before approval.

No authorization is effective until the canonical decision record is approved
and repository synchronization is complete.

Output: approved decision record and append-only Review Log event.

### 7.8 Phase 8 - Gate closeout

The Secretary validates identifiers, reverse references, final package
retention, evidence state, project status, and the absence of contradictory
authorization statements. The closeout records the next permitted action
under the selected outcome and confirms that no broader authority was created.

Output: gate-closeout record and closed submission package.

## 8. Rules governing discussion

All gate discussion obeys these rules:

- discussion is limited to the frozen request, evidence, evaluation
  categories, risks, boundaries, and outcome;
- participants may clarify what an evidence item says but may not turn an oral
  explanation into evidence;
- factual corrections must be submitted through the evidence workflow;
- governance meaning, ownership, vocabulary, and admission are not debated;
- implementation alternatives, optimization, design selection, and task
  planning are out of order;
- excluded families and stopped authority cannot be justified into scope;
- participants disclose conflicts of interest and role changes immediately;
- reviewer independence and dissent are preserved in the record;
- private or unrecorded material communication cannot support a category
  result;
- observers speak only when invited and never vote by observer status;
- absence of objection is not approval; and
- the presiding Board member may pause or end discussion when the record is
  insufficient, the scope becomes ambiguous, or the meeting leaves gate
  scope.

Questions that require new evidence are recorded as evidence requests. The
Board does not speculate about the likely answer.

## 9. Rules governing post-freeze changes

### 9.1 Non-material administrative correction

A typographical correction, repaired link, or metadata clarification that
does not change evidence meaning, scope, provenance, result, risk, or
assessment may be appended by the Secretary. The correction and
non-materiality rationale are recorded. The original remains visible.

### 9.2 Material evidence addition or change

Any change to evidence meaning, source, scope, baseline, dependency state,
control, risk, or requested authorization boundary is material. The Secretary
pauses review, registers the revision, preserves the prior freeze, obtains
updated affected assessments, and establishes a new freeze before
deliberation.

### 9.3 Late evidence during deliberation

The Board may not rely on late evidence immediately. It either:

- excludes the item and decides using the frozen record; or
- pauses deliberation, returns the package to the evidence workflow, and
  reconvenes after re-freeze and affected independent review.

### 9.4 Repository drift

Any repository change after freeze is declared and classified for its effect
on the submission. If the change could alter scope, dependency assumptions,
acceptance criteria, risk, controls, or evidence reproducibility, the freeze
is no longer sufficient and section 9.2 applies. An immaterial-drift decision
must be explicit and evidence-backed.

## 10. Handling conflicts and exceptions

| Condition | Required handling | Gate effect if unresolved |
| --- | --- | --- |
| Conflicting evidence | Preserve both items, identify the exact conflicting assertion and authority, and seek a frozen evidence resolution | Affected assertion is `UNKNOWN`; authorization is blocked when mandatory |
| Reviewer disagreement | Record each assessment and rationale; the Board evaluates the cited evidence under the same criteria | Unresolved material disagreement becomes `UNKNOWN`, not an averaged result |
| Insufficient evidence | Record the missing assertion, affected category, scope, and required evidence characteristic without designing a solution | `WP6_BLOCKED_NEEDS_EVIDENCE` when the submission is otherwise valid |
| Scope ambiguity | Stop boundary reconciliation and require an exact scope revision | No authorization; invalid if the ambiguity prevents a valid submission |
| Direct governance conflict | Stop substantive review, preserve the conflict evidence, and escalate under existing authority outside this gate | `GATE_SUBMISSION_INVALID`; governance is not reopened or resolved by the gate |
| Repository drift | Determine materiality from recorded evidence; re-freeze and reassess when material | No decision on a stale baseline |
| Evidence-source access loss | Record the inaccessible item and whether an independently retained copy remains valid | `UNKNOWN` if the evidence can no longer be examined as required |
| Participant conflict of interest | Record the conflict and apply existing recusal or replacement rules | Gate pauses if required independence or authority is not preserved |
| Quorum or authority failure | End deliberation without a merits decision | `GATE_SUBMISSION_INVALID` or administrative return, as procedurally applicable |
| Submission withdrawal | Preserve the package and withdrawal record; stop assessment and deliberation | No authorization; a future request is a new gate submission |

The Board may determine evidence weight, but it cannot resolve a missing
semantic owner, vocabulary term, governance authority, or excluded admission
inside the gate.

## 11. Decision protocol

### 11.1 Deliberation readiness

The Secretary presents a deliberation-readiness statement confirming:

- administrative completeness;
- one active evidence freeze;
- coverage of every evaluation category;
- a completed boundary reconciliation;
- all known conflicts, unknowns, stale items, and dissent;
- the requested exact scope; and
- current non-authorization status.

If any required procedural input is absent, deliberation does not proceed.

### 11.2 Category determination

The Board assigns one canonical result to every normative evaluation category:
`PASS`, `FAIL`, `UNKNOWN`, or permitted `NOT_APPLICABLE`. Each determination
names the supporting evidence and rationale. Category results are not averaged
or traded against one another.

### 11.3 Outcome determination

The Board applies the normative decision criteria and selects exactly one:

- `WP6_AUTHORIZED`;
- `WP6_BLOCKED_NEEDS_EVIDENCE`;
- `WP6_NOT_AUTHORIZED`; or
- `GATE_SUBMISSION_INVALID`.

The Board follows the applicable existing quorum and decision rule. This
procedure does not create a new voting threshold. Silence, informal consensus,
conditional intent, or a majority of category passes is not a substitute for
the canonical outcome.

### 11.4 Exact-scope rule

An authorization outcome must enumerate every authorized family, decomposed
concept, repository boundary, environment, control, and validity condition.
Anything not enumerated remains unauthorized. There is no implied partial
authorization.

### 11.5 Conditions

A condition required before work can safely begin is missing readiness
evidence and prevents `WP6_AUTHORIZED`. The Board may record non-blocking
observations or controls that apply during authorized work only when every
pre-start criterion is already satisfied.

### 11.6 Decision finalization

The presiding Board member confirms the outcome on the record. The Secretary
reads back the exact scope, status effect, retained exclusions, and
non-authorizations. The Board approves the canonical written record through
the existing decision process. Until that approval is effective, WP6 remains
`WP6_BLOCKED`.

## 12. Recording requirements

The gate generates and retains the following mandatory records:

1. **Gate request record** — requester, purpose, exact scope, baseline, date,
   and current status.
2. **Submission manifest** — package revision, required sections, stable
   locators, and known limitations.
3. **Participant record** — Board authority, Secretary, Submission Owner,
   reviewers, observers, declarations, recusals, and replacements.
4. **Evidence index and custody history** — every evidence item and its
   registered, accepted, rejected, withdrawn, superseded, frozen, stale,
   assessed, and retained states as applicable.
5. **Evidence-freeze record** — exact scope, repository revision, evidence
   set, participant assignments, and freeze time.
6. **Individual review assessments** — assigned category, result, evidence,
   rationale, limitations, risk, conflict, and reviewer confirmation.
7. **Boundary-reconciliation record** — included, unsubmitted, excluded,
   opaque, indirect-dependency, repository, environment, and authority
   boundaries.
8. **Deliberation record** — authority and quorum confirmation, category
   determinations, dissent, accepted risks, excluded late evidence, and
   selected outcome.
9. **Canonical `CHECKPOINT_RESULT`** — every field required by the normative
   Authorization Gate Specification.
10. **Append-only Review Log event** — purpose, scope, evidence, outcome,
    status effect, related decision, and checkpoint.
11. **Gate-closeout record** — repository synchronization, final status,
    retained non-authorizations, next permitted action, and reconvening
    conditions.

These may be sections of a controlled package rather than eleven separate
files. Each semantic record has one canonical location, and cross-references
must not create parallel sources of truth.

## 13. Post-decision repository state

The Secretary records the repository and project state corresponding to the
selected outcome:

| Outcome | WP6 state | Repository state | Permitted next action |
| --- | --- | --- | --- |
| `WP6_AUTHORIZED` | Authorized only for the exact recorded scope after the decision becomes effective | Canonical `CHECKPOINT_RESULT`, Review Log event, frozen package, and closeout are synchronized; all non-authorizations remain explicit | Begin only the enumerated WP6 work under the recorded controls |
| `WP6_BLOCKED_NEEDS_EVIDENCE` | `WP6_BLOCKED` | Missing, stale, conflicting, or unknown evidence and affected categories are recorded; package closes without implementation authority | Prepare a new or revised submission; no work begins |
| `WP6_NOT_AUTHORIZED` | `WP6_BLOCKED` | Failed criteria, unaccepted risks, rationale, and retained scope are recorded | No work begins; a later request requires materially relevant new evidence or scope |
| `GATE_SUBMISSION_INVALID` | `WP6_BLOCKED` | Invalid authority, scope, baseline, or boundary is recorded without a merits authorization decision | Correct the submission under existing authority or complete external escalation before any new request |

For every outcome:

- M34.1 remains `NO-GO` unless a separate authorized gate expressly changes
  it;
- runtime adoption remains unauthorized;
- M32 and M33 remain closed;
- every `WP6_EXCLUDED` family and every unsubmitted eligible family remains
  outside the decision; and
- no broader authority is inferred from administrative completion.

## 14. Gate closeout procedure

Before closing the gate, the Secretary verifies:

- exactly one canonical outcome is recorded;
- the Decision Register, Review Log, and checkpoint references agree;
- the decided scope matches the frozen and assessed scope;
- all evidence and reviewer records are retained and reachable;
- rejected, withdrawn, superseded, stale, late, and conflicting evidence is
  still visible;
- category results and dissent are preserved;
- project status and next permitted action match section 13;
- all exclusions and non-authorizations are explicit; and
- no draft, minutes, package summary, or obsolete status statement conflicts
  with the canonical result.

Closeout is administrative. It does not expand, reduce, or reinterpret the
Board's decision.

## 15. Re-convening rules

A new Authorization Gate is required when any of the following applies:

- a prior outcome was `WP6_BLOCKED_NEEDS_EVIDENCE`, `WP6_NOT_AUTHORIZED`, or
  `GATE_SUBMISSION_INVALID` and a new decision is requested;
- the requested authorization scope changes, including addition of another
  eligible family, decomposed concept, repository area, interface, data
  boundary, or environment;
- a material repository, dependency, environment, control, role, or risk
  change occurs after evidence freeze and before an effective decision;
- an effective authorization record's stated validity or evidence-currency
  condition is no longer satisfied;
- work would need to proceed outside an authorized boundary or control;
- material evidence used for authorization is withdrawn, superseded,
  contradicted, or declared stale before commencement or under a recorded
  stop-work condition; or
- the applicable gate authority or required review independence can no longer
  be demonstrated.

If the Platform Constitution, an approved DQ, semantic ownership, canonical
vocabulary, or the admission manifest changes, the applicable governance
process must complete outside this procedure before a new gate may be
convened. The gate does not reopen or repair governance.

A new gate uses a new request, new freeze, new assessments, new reconciliation,
new Board deliberation, and new canonical outcome. A prior decision is never
silently edited into a new authorization.

## 16. Procedural stop conditions

The Secretary or presiding Board member pauses the process when:

- authority, quorum, independence, or required role coverage is absent;
- the active submission or repository baseline cannot be identified;
- material evidence changes after freeze;
- scope is ambiguous or appears outside `WP6_INCLUDED`;
- an excluded concept or stopped authority is imported directly or
  indirectly;
- a material question depends on unindexed or inaccessible evidence;
- discussion attempts to redesign governance or implementation;
- a direct governance conflict is discovered; or
- the record cannot support one canonical outcome.

A pause preserves every existing record. It is not an authorization, rejection,
or governance reopening.

## 17. Non-authorization statement

This operating procedure defines how a future gate is conducted. It does not
submit evidence, validate readiness, convene the Board, allocate a gate or
decision identifier, perform a review, select an outcome, authorize WP6,
authorize implementation, authorize M34.1, authorize runtime adoption, or
modify the normative Authorization Gate Specification.

Current state remains:

```text
Governance:                COMPLETE AND FROZEN
Gate specification:        APPROVED AND FROZEN
Authorization Gate:        NOT CONVENED
WP6:                       WP6_BLOCKED
M34.1:                     NO-GO
Runtime authority:         NONE
Implementation authority:  NONE
```
