# ADR-006: M34 External Governance as an Intentional Dependency

**Date:** 2026-07-20
**Resolves:** The post-arbitration architectural disposition of governance
dependencies referenced by the M34 Authorization Framework but not completely
governed by repository artifacts.

---

## Context

The M34 semantic-governance work is complete and frozen. The Authorization
Framework is internally complete, but the Authorization Gate has not been
convened and no WP6 implementation or runtime authority exists.

The constitutional investigation considered two conflicting positions. The
initial review treated the missing governance foundation as requiring a new
repository constitutional initiative. The independent challenge argued that
existing constitutional silence and the current M34 corpus already supplied
sufficient authority. Arbitration found that neither position was fully
established: the repository evidence did not resolve every dependency, but it
also did not establish that no authoritative source exists outside the
repository.

Subsequent evidence discovery established that the repository contains:

- a complete frozen semantic-governance corpus;
- an explicit M34 gate decision role for the Architecture Review Board;
- named holders for the Submission Owner, Repository Custodian, Project
  Maintainer, Gate Secretary, and one person acting as the Board; and
- an internally complete Authorization Framework that repeatedly requires
  existing project governance or existing authority.

The architectural direction decision selected external governance as an
intentional dependency rather than repository self-constitution or gate
simplification. The final consistency review confirmed that this direction
preserves the frozen framework while retaining the unratified and blocked
states.

The same discovery established that no complete repository artifact supplies
the constituting authority needed for every referenced dependency. The role
record names holders but does not identify the authority that issued those
appointments or delegate appointment power. Applicable Board constitution,
participation, quorum, voting or decision, role-compatibility, recusal,
replacement, bounded-environment, security/data approval, and external-
escalation authority remain unresolved.

The investigation therefore distinguishes two governance objects:

1. the completed and frozen M34 semantic-governance corpus; and
2. the unratified external authority needed to constitute and operate the
   Authorization Gate.

The governing repository evidence includes:

- [Platform Architecture section 11](../architecture/platform_architecture.md),
  which defines the written-artifact hierarchy;
- [M34-WP1 Charter and Audit Protocol](../implementation/M34_WP1_charter_and_audit_protocol.md),
  which freezes the audit evidence, ownership, and independence rules;
- [Authorization Gate Specification](../implementation/m34/audit/reports/M34_WP6_authorization_gate_specification.md)
  and [Operating Procedure](../implementation/m34/audit/reports/M34_WP6_authorization_gate_operating_procedure.md),
  which require existing authority without creating it;
- [M34 Role Appointments](../implementation/m34/audit/reports/M34_ROLE_APPOINTMENTS.md),
  which records existing role holders;
- [Phase 2 Administrative Validation](../implementation/m34/audit/reports/M34_WP6_administrative_validation_ASP_0006.md),
  which returned the package;
- [Administrative Return Closure Plan](../implementation/m34/audit/reports/M34_WP6_administrative_return_closure_plan.md)
  and [Controlled Successor Transition Report](../implementation/m34/audit/reports/M34_WP6_controlled_successor_transition_report.md),
  which preserve the remaining blockers; and
- [Scoped Participant and Reviewer Appointment Record](../implementation/m34/audit/reports/M34_WP6_participant_and_reviewer_appointments.md),
  which records that the appointment action remained blocked.

## Problem

The repository must preserve the completed investigation without claiming
that the missing authority exists, manufacturing that authority inside M34,
or weakening the frozen gate to avoid its prerequisites.

Without a durable decision, a future session could incorrectly conflate
semantic-governance completion with constituting-authority completion, treat
role labels as proof of appointment authority, create repository-local
authority through self-assertion, or remove safeguards merely to advance the
blocked package.

## Decision

**Treat the governance authority referenced by the M34 Authorization
Framework as an intentional external dependency.**

The selected architectural posture is:

```text
INTERNALLY COMPLETE
EXTERNALLY UNRATIFIED
AUTHORIZATION BLOCKED
```

This decision records the dependency boundary. It does not assert that an
external authority has been identified, supplied, validated, or granted.
Constitutional silence permits this dependency to be recorded at the decision
level; it does not permit M34 to fabricate or self-issue the missing authority.

## Status Matrix

| Status field | Decision state |
| --- | --- |
| Constitutional investigation | `CONSTITUTIONAL_INVESTIGATION_COMPLETE` |
| M34 internal governance | `M34_INTERNAL_GOVERNANCE_COMPLETE` |
| External governance | `EXTERNAL_GOVERNANCE_UNRATIFIED` |
| Authorization Gate | `AUTHORIZATION_GATE_NOT_CONVENED` |
| WP6 | `WP6_BLOCKED` |
| M34.1 | `M34_1_NO_GO` |
| Runtime authority | `RUNTIME_AUTHORITY_NONE` |
| Implementation authority | `IMPLEMENTATION_AUTHORITY_NONE` |

Semantic-governance completion does not establish constituting-authority
completion. None of these states changes merely because this ADR is accepted.

## Findings Preserved

- No complete repository artifact supplies all external governance authority
  required by the Authorization Gate.
- Existing role records name holders but do not establish the authority that
  issued the appointments.
- Appointment-issuing authority, participant and reviewer appointments,
  Board constitution, applicable participation and quorum, voting or decision
  rules, role compatibility, independence, conflict handling, recusal,
  replacement, bounded environment execution, security/data approval, and
  external escalation remain unresolved to the extent identified by the
  completed evidence discovery.
- The unresolved items require external evidence. Their classification is
  `UNRESOLVED_EXTERNAL_DEPENDENCIES`.
- Completion of the frozen semantic-governance corpus is distinct from
  ratification of the authority required to constitute and operate the gate.
- M34 is neither constitutionally invalid nor authorized to proceed merely
  because its internal framework is complete.

## Rationale

- Treating the dependency as external preserves the frozen Authorization
  Framework and records its actual prerequisite without reinterpreting it.
- Creating repository-local authority inside M34 would risk
  self-authorization: the blocked process would be manufacturing the authority
  needed to unblock itself without evidence of a competent issuer.
- Simplifying the gate would remove its authority, independence, quorum,
  conflict, and environment safeguards and would reopen frozen governance to
  obtain a procedural outcome.
- A blocked state is the designed result when a required authority or
  procedural input is absent. Preserving `WP6_BLOCKED` is therefore a correct
  lifecycle state, not an implementation defect.
- The available evidence does not justify creating Program Governance,
  Repository Governance, `CG-01`, or another constitutional layer.

## External Ratification Requirement

The authorization process may resume only when a currently effective and
authoritative source expressly provides or validly delegates, as applicable:

- Board constitution;
- appointment-issuing authority;
- participant and reviewer appointments;
- applicable participation and quorum rules;
- an applicable voting or decision rule;
- role compatibility and independence requirements;
- conflict declarations and recusal;
- a replacement procedure;
- bounded non-production execution authority;
- environment, security, and data approval authority; and
- external escalation authority.

This ADR supplies none of those facts. It does not identify or fabricate a
source, issuer, appointee, reviewer, declaration, rule, environment, or
approval.

## Resume Condition

M34 may resume only after the applicable external authority is:

1. identified;
2. shown to be currently effective;
3. shown to apply to this repository and the M34-WP6 Authorization Gate;
4. cited in repository evidence;
5. independently verified; and
6. accepted through the existing authorization procedure.

External authority may authorize the process governed by the repository. It
must not silently rewrite repository law, M34 decisions, canonical vocabulary,
the frozen semantic-governance corpus, or the 18 `WP6_INCLUDED` / 22
`WP6_EXCLUDED` admission partition.

## Reopen Triggers

This decision is reopened only if:

- authoritative external governance evidence is supplied;
- the Platform Architecture is amended regarding governance
  self-containment;
- the project deliberately chooses repository-self-contained governance
  through a separately authorized initiative;
- a material contradiction is discovered between the frozen semantic corpus
  and external authority; or
- the Authorization Framework itself is formally reopened.

Absent one of these events, repeated absence of external evidence does not
reopen the investigation or change the blocked state.

## Consequences

- The constitutional investigation is closed at the repository decision
  level.
- M34 remains internally complete but externally unratified.
- The returned package is not repaired or resubmitted by this decision.
- The Authorization Gate remains not convened.
- WP6 remains blocked and M34.1 remains NO-GO.
- No implementation, runtime, evidence-execution, appointment, Board,
  environment, or external-escalation authority is created.
- Future gate progress depends on external ratification evidence satisfying
  the resume condition.

## Alternatives Considered

1. **Make the repository constitutionally self-contained.**
   Rejected for the present decision. The available evidence does not identify
   authority permitting M34 or this ADR to constitute the missing governance,
   and doing so would risk self-authorization.

2. **Simplify the Authorization Framework to remove the unresolved
   dependencies.**
   Rejected. This would remove safeguards, alter the frozen framework, and
   convert missing authority into apparent readiness.

3. **Declare that external governance already exists.**
   Rejected. No currently effective source applying to this repository and
   gate has been supplied or verified.

4. **Open a new constitutional initiative automatically.**
   Rejected. Arbitration found insufficient evidence that a new initiative is
   required, and evidence discovery classified the missing inputs as external
   dependencies.

## Status

**Accepted as a repository architectural dependency decision.**

Final disposition:

`M34_CONSTITUTIONAL_INVESTIGATION_CLOSED_EXTERNAL_RATIFICATION_REQUIRED`
