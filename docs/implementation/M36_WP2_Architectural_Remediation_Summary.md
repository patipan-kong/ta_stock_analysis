# M36-WP2 - Architectural Remediation Summary

**Date:** 2026-07-20

**Document class:** Architecture-review remediation trace

**Status:** `COMPLETE`

**Implementation authority:** `NONE`

**Runtime authority:** `NONE`

## 1. Purpose

This record maps the two findings from the independent architectural review of
`M36_WP1_Multiple_Portfolio_Foundation.md` to their bounded resolutions in the
revised M36-WP1. It records remediation only. It does not approve M36-WP1,
register a canonical Glossary term, amend M29-M35, define product behavior, or
create implementation or runtime authority.

The remediation preserves the original Multiple Portfolio Foundation: one
Product Workspace may reference zero or more Portfolio Identities while one
Workspace Context carries zero or one Current Selection. Portfolio identity,
accounting, lifecycle truth, Experience interaction, and M33 authority remain
separate.

## 2. Finding disposition matrix

| Finding | Original concern | Disposition | Exact architectural correction | Affected M36-WP1 sections | Retained boundaries | Why no redesign was required |
| --- | --- | --- | --- | --- | --- | --- |
| `M36-ARB-F01` | The load-bearing phrase “lifecycle qualification” had no canonical definition or exact owner; the vague “existing portfolio source” risked collision with the Portfolio Intelligence-owned Portfolio Status term. | `Resolved` | Section 3.3 determined that no frozen canonical term covered the Portfolio Domain Model's `active`/`archived`/`closed` lifecycle state. It proposed **Portfolio Lifecycle State** as a Ledger & Accounting-owned fact, established same-change Glossary registration as an acceptance condition now completed by the M36 approval change, preserved the existing Portfolio Status meaning, and separated lifecycle state from Portfolio Identity, Current Selection, availability, authority, and transition legitimacy. Vague lifecycle-owner phrases were removed. | 3.1, 3.3, 4, 5.1, 7, 8.4, 10, 11, 12, 14, 15, 16, 17 | Portfolio Identity and Accounting Scope remain Ledger-owned; Portfolio Status remains Portfolio Intelligence-owned; Current Selection remains Experience-owned; lifecycle behavior and workflows remain frozen or deferred. | The Portfolio Domain Model already supplies the lifecycle states and transitions. Remediation names and owns the previously unnamed state without changing its values or behavior. |
| `M36-ARB-F02` | Referenceability, source availability, Current Selection, and M33 action authority were partially collapsed, allowing generic authority to influence context resolution and selection loss. | `Resolved` | Referenceability now depends only on exact Portfolio Identity, its exact one-workspace relationship, and the M35 Context Resolver applying the Scope Reference contract. Current Selection uses the same source resolution without generic M33 authority. Unavailable, unauthorized, unknown, archived, closed, degraded, and relationship-mismatched are explicitly distinct. Selection clears without fallback only when exact identity or relationship no longer resolves. M33 is invoked only by an existing governed action boundary and remains exact and fail-closed there. Generic read and portfolio-view permissions are explicitly not invented. | 5.2-5.5, 6.1-6.4, 7, 8.4, 9.2-9.3, 10, 12, 13, 14, 15, 16, 17 | M33 contracts and permissions remain frozen; M35 context and selection contracts remain frozen; authorization never depends on UI; read-access policy and authorization implementation remain deferred. | M35 already separates context from authority and M33 already scopes authority to declared permissions. Remediation makes those inherited boundaries explicit without changing cardinality, contracts, or capability behavior. |

Both findings are `Resolved`. No finding is classified `Partially Resolved` or
`Deferred`. The second independent architectural review approved both
remediations. Its mandatory same-change condition was canonical Glossary
registration of Portfolio Lifecycle State; that registration is complete in
the M36 approval change. This historical remediation trace does not itself
perform the registration or grant architectural, implementation, or runtime
authority.

## 3. Lifecycle vocabulary resolution

The frozen evidence supports these exact conclusions:

- Portfolio Domain Model sections 3 and 8 use `active`, `archived`, and
  `closed` as the lifecycle state of a permanent Portfolio Identity.
- The canonical Glossary's existing **Portfolio Status** means status of
  portfolio-derived information, is owned by Portfolio Intelligence, and is
  governed by `M34-D-0009`.
- Portfolio Status therefore cannot lawfully be reused for portfolio identity
  lifecycle state.
- M36-WP1 proposed **Portfolio Lifecycle State** as the narrow missing term,
  owned by Ledger & Accounting because it qualifies the Ledger-owned Portfolio
  Identity and Accounting Scope; the M36 approval change has now registered
  that term in the canonical Glossary.
- M36-WP1 introduces no unnamed pre-activation state and no lifecycle command,
  workflow, persistence, or transition implementation.

Transition legitimacy remains a separate question that M36 does not allocate
or redesign. Portfolio Domain Model section 9 validation and the Platform
Architecture section 7.2 decision gate remain its exact governing boundaries
for a proposed action. Experience observes state and routes intent only.

## 4. Reference and authority resolution

The revised architecture applies this boundary:

```text
exact Portfolio Identity
  + exact one-workspace relationship
  + M35 Context Resolver applying Scope Reference
  = referenceable portfolio context

referenceable portfolio context
  + explicit human orientation
  = Current Selection

proposed governed action
  + exact M33 facts, only when its existing boundary invokes M33
  = action-boundary authority evaluation
```

The third step never establishes either of the first two. Authority does not
create or erase Portfolio Identity, rewrite the workspace relationship, decide
source availability, or clear Current Selection. Conversely, referenceability,
visibility, and selection grant no authority.

No frozen input defines a generic read-access or portfolio-view permission.
M36-WP1 explicitly defers that policy and does not repurpose M33's existing
execution-intent permissions.

## 5. Scope control

The remediation adds no:

- database, schema, persistence, API, event, frontend, backend, cache,
  synchronization, infrastructure, or deployment design;
- portfolio lifecycle implementation, creation workflow, closure workflow, or
  transition command;
- read-access policy, RBAC, membership, sharing, grant, or authorization
  runtime;
- analytics, AI, execution, trading, dashboard, or plugin behavior;
- new workspace or portfolio cardinality;
- amendment to M29-M35, M33 authority contracts, M34 decisions, or M35
  workspace contracts; or
- implementation or runtime authority.

## 6. Final disposition

The second independent architectural review returned `APPROVED` for the
revised M36-WP1 and confirmed both findings resolved. The required same-change
canonical Glossary registration is complete. M36-WP1 is approved and
canonical; this trace remains the historical record of remediation and grants
no authority by itself.

Retained state:

```text
M29-M35:                       CLOSED AND FROZEN
First independent M36 review: CHANGES REQUIRED
Second independent review:    APPROVED
M36:                           CLOSED AND CANONICAL
M36-WP2 remediation:           COMPLETE
M36-WP1 architectural status:  APPROVED
Portfolio Lifecycle State:     REGISTERED IN CANONICAL GLOSSARY
Implementation authority:      NONE
Runtime authority:             NONE
```

The recommended next architecture milestone is M37 - Universal Asset Search
Foundation. No M37 implementation or runtime work is authorized.
