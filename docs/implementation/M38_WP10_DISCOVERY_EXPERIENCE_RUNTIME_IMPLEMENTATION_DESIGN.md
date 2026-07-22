# M38-WP10 — Discovery Experience Runtime Implementation Design

**Status:** Complete — implementation authority frozen

**Milestone:** M38 — Product Workspace Foundation

**Canonical authority:** [M38-WP1 Boundary Contracts and Conformance Specification](M38_WP1_BOUNDARY_CONTRACT_SPECIFICATION.md)

**Closeout:** [M38 Epic Closeout](M38_EPIC_CLOSEOUT.md)

## 1. Objective

WP10 implements the Experience-owned runtime for opening and observing a
transient Discovery Experience around one unmodified M37 Discovery Candidate.
It realizes the `DiscoveryExperienceContext` contract and the `OPEN` to
`CLOSED` lifecycle defined by WP1 without creating an Asset Workspace,
canonical Asset identity, or durable state.

WP10 is the only implementation authority for this runtime. It composes with
the frozen WP2 Workspace Context prerequisite and consumes M37 result data as
public contract values. It does not modify any WP1–WP9 runtime or authority.

## 2. Scope

WP10 implements:

- exact structural validation of the public M37 Discovery Candidate shape;
- exact structural validation and preservation of optional M37 Search
  degradation entries;
- `DiscoveryExperienceContext` construction in a resolved current workspace;
- structural absence before opening and after closing;
- `OPEN` to `CLOSED` transitions for close, replacement, and expiry;
- zero-or-one current Discovery Experience association;
- replacement, stale-handle suppression, and synchronous lifecycle
  observation;
- fail-closed validation and synchronous re-entrancy handling; and
- process-local, non-durable runtime correlation.

## 3. Out of scope

WP10 does not implement or invoke:

- Universal Search execution or Search internals;
- Registry reads, writes, or internal adjudication;
- Resolver behavior or Discovery handoff;
- provider adapters, SDKs, URLs, or direct provider calls;
- Asset Focus, canonical asset navigation, or asset routes;
- workspace lifecycle, workspace switching, membership, RBAC, or authority;
- Portfolio state or Current Selection mutation;
- contribution, projection, Experience Composition, observation, or query
  behavior owned by WP3–WP9;
- Market Intelligence, Intelligence, Intent, or Actions; or
- persistence, replay, durable command storage, or an asynchronous command
  queue.

## 4. Runtime architecture

```text
M37 public Discovery Candidate + optional degradation
                         |
                         v
WP2 public resolved-workspace prerequisite
                         |
                         v
          DiscoveryExperienceCoordinator
            |       |       |       |
            |       |       |       +-- observer notifications
            |       |       +---------- expiry
            |       +------------------ close / replacement
            +-------------------------- validation and current association
                         |
                         v
          zero or one transient OPEN context
```

The coordinator is an Experience-owned, process-local holder. A new
coordinator starts with structural absence and replays nothing. Its only
upstream runtime dependency is the frozen WP2 public prerequisite reader.
Candidate and degradation values enter as public M37 contract data supplied by
the caller; WP10 never calls Search.

## 5. Runtime contracts

### 5.1 Workspace prerequisite

`WorkspacePrerequisiteReader.readResolvedWorkspace()` returns either one
resolved public workspace prerequisite containing an opaque `workspace_id` or
structural absence. WP10 copies the identity exactly and never coerces,
selects, or switches it.

An absent or invalid prerequisite rejects an open command with
`WORKSPACE_NOT_RESOLVED`. An existing current context remains unchanged.

### 5.2 Discovery Candidate

The accepted value is exactly the frozen public M37 Discovery Candidate wire
shape:

| Field | Required value |
|---|---|
| `kind` | `DISCOVERY` |
| `claim_id` | non-empty string |
| `provider_name` | non-empty string |
| `reported_symbol` | string or null |
| `reported_name` | string or null |
| `reported_identifiers` | string-to-string record |
| `market` | string or null |
| `currency` | string or null |
| `match_field` | string |

Unknown fields are rejected. A Registered Candidate, any candidate carrying
`asset_id`, or any malformed field is rejected with
`INVALID_DISCOVERY_CANDIDATE`. WP10 retains the accepted candidate reference
unchanged; `claim_id` remains transient correlation and never becomes
canonical identity.

### 5.3 Search degradation

`search_degradation`, when present, is an array of exact public M37 entries:

| Field | Required value |
|---|---|
| `source` | string |
| `reason` | string |
| `message` | string |
| `candidate_kind_uncertain` | boolean |

Unknown or malformed fields reject the open command with
`INVALID_SEARCH_DEGRADATION`. Accepted degradation is retained and exposed
without rewriting or concealment.

### 5.4 Discovery Experience Context

The runtime representation exactly realizes WP1 §3.4:

| Field | Presence | Owner |
|---|---|---|
| `workspace_id` | required | Experience Platform |
| `candidate` | required | Universal Search |
| `search_degradation` | conditional | Universal Search |
| `experience_state` | required: `OPEN` or `CLOSED` | Experience Platform |

The context carries no `asset_id`, durable route, Resolver verdict, Portfolio
state, or provider behavior. Its public values are immutable after
construction.

### 5.5 Runtime handle

The coordinator returns an opaque process-local handle with a successful open.
The handle is private operational correlation outside
`DiscoveryExperienceContext`. It is not serializable into a route or DTO and
does not create identity or public correlation state.

### 5.6 Public coordinator interface

The public runtime operations are:

- `open(input)`: validate the prerequisite and public values, then open a new
  instance or replace the current instance;
- `readCurrent()`: return the current handle and context, or structural
  absence;
- `close(handle)`: close the matching current instance;
- `expire(handle)`: expire the matching current instance; and
- `observe(observer)`: register a synchronous lifecycle observer and return an
  unsubscribe operation.

No HTTP endpoint is introduced by WP10.

## 6. Lifecycle and transition rules

| From | Command | To | Result |
|---|---|---|---|
| structurally absent | valid `open` | `OPEN` | one new current instance |
| `OPEN(A)` | valid `open(B)` | `CLOSED(A)`, then `OPEN(B)` | B is the only current instance |
| `OPEN(A)` | `close(handle A)` | structurally absent after terminal `CLOSED(A)` | success |
| `OPEN(A)` | `expire(handle A)` | structurally absent after terminal `CLOSED(A)` | success |
| any | invalid `open` | unchanged | rejected, no notification |
| absent or `OPEN(B)` | `close/expire(stale handle A)` | unchanged | false, no notification |

`CLOSED` is terminal for one context instance. Reopening always creates a new
instance and handle. Structural absence is not a third context state.

Replacement installs the successor as current before it emits the predecessor
`CLOSED / REPLACEMENT` notification. Observers therefore never read an
intermediate current-state gap. The notification order for normal replacement
is predecessor `CLOSED / REPLACEMENT`, then successor `OPEN`.

## 7. Concurrency and re-entrancy

All mutating lifecycle commands and their synchronous notification phase are
covered by one private, ephemeral transition guard.

If an observer synchronously invokes a lifecycle command while another
lifecycle transition is in progress:

- nested `open` rejects with `REENTRANT_LIFECYCLE_COMMAND`;
- nested `close` or `expire` returns false;
- the nested command performs no mutation and emits no notification; and
- the outer transition, its returned context, and the current association
  remain internally consistent.

The guard is released in `finally`, including when an observer throws.
Observer exceptions remain isolated and cannot change a lifecycle result,
suppress other observers, or permanently lock the coordinator. This mechanism
adds no public state, lifecycle state, queue, replay, or persistence.

## 8. Fail-closed behavior

The coordinator fails closed for:

- an unresolved or invalid workspace prerequisite;
- a non-Discovery or structurally invalid candidate;
- any candidate carrying additional identity or unknown fields;
- malformed or structurally extended degradation data;
- a stale close or expiry handle; and
- a synchronous re-entrant lifecycle command.

A rejected open never closes or replaces the current context. A stale or
re-entrant terminal command never closes the current context. No failure path
invokes Search, Registry, Resolver, providers, Portfolio, or a future-domain
runtime.

## 9. Dependency rules

WP10 may consume only:

- the frozen WP2 public resolved-workspace prerequisite; and
- frozen M37 public Discovery Candidate and Search degradation values.

WP10 must not depend on Search execution or internals, Registry, Resolver,
providers, Portfolio, Current Selection, WP3–WP9 internals, Market
Intelligence, Intelligence, Intent, Actions, persistence, routing, or ambient
identity reconstruction.

The implementation remains a pure TypeScript module and introduces no
framework, transport, database, storage, or provider abstraction.

## 10. Implementation constraints

- Reuse existing runtime infrastructure wherever possible.
- Avoid introducing new framework abstractions.
- Keep implementation cohesive with WP2–WP9 conventions.
- Minimize public surface area.
- Do not refactor unrelated modules.

## 11. Implementation record

| File | Role |
|---|---|
| `frontend/lib/discoveryExperience.ts` | runtime contracts, validation, coordinator, lifecycle, observation, and re-entrancy guard |
| `frontend/lib/discoveryExperience.test.ts` | focused WP10 contract, lifecycle, boundary, concurrency, and regression tests |
| `frontend/package.json` | includes the WP10 test in the existing pure-test command |

The confirmed synchronous observer re-entrancy defect was corrected with the
private guard defined in §7. The final independent re-review approved the
remediation with no blocking findings.

## 12. Conformance mapping

| Frozen requirement | WP10 realization |
|---|---|
| WP1 §3.4 | exact `DiscoveryExperienceContext` fields, owners, and prohibited states |
| WP1 §5.2 | `EMITTED` consumption into `OPEN`; terminal `CLOSED`; no route, persistence, or Asset Focus transition |
| `ID-03`, `ID-04` | exact shape excludes `asset_id`; `claim_id` is neither persisted nor routed |
| `RT-05` | no asset-route construction surface |
| `CO-02` | only declared public WP2 and M37 contract dependencies |
| `DG-04` | degradation retained and exposed unchanged |
| `DS-01` | Registered and Discovery Candidate shapes remain distinct |
| `DS-02`, `DS-03` | selection opens only a transient, non-persistent, non-routing Experience with no provider call |
| `DS-04` | no transition to Asset Focus; any future `asset_id` must enter through a separate request |
| `COMP-04` | no M35, M36, M37, or WP1–WP9 public contract is modified |

## 13. Acceptance evidence

The focused suite contains 20 tests covering:

- exact candidate, workspace identity, and degradation preservation;
- structural absence, normal open, replacement, close, and expiry;
- terminal-state notification order and zero-or-one current association;
- no intermediate current-state gap during replacement;
- stale handle suppression and failed-replacement isolation;
- rejection of Registered Candidates, `asset_id`, malformed fields, unknown
  fields, and malformed degradation;
- observer exception isolation and unsubscribe behavior;
- no replay across runtime instances;
- absence of durable route and canonical identity fields;
- exact, non-coerced workspace identity;
- the reproduced `A` / `B` / re-entrant `C` replacement regression;
- re-entrant close and expiry suppression; and
- transition-guard release after observer exceptions.

## 14. Completion criteria

WP10 is complete when:

- the runtime implements the exact WP1 Discovery Experience contract and
  lifecycle;
- only a structurally valid M37 Discovery Candidate can open in a resolved
  current workspace;
- candidate and degradation values remain unmodified;
- zero-or-one current association, replacement, close, expiry, and stale
  handle behavior are deterministic and fail closed;
- synchronous observer re-entrancy cannot cause nested mutation, nested
  notification, stale publication, or an inconsistent outer result;
- the runtime creates no Asset Focus, canonical identity, route, persistence,
  or forbidden dependency;
- all focused tests and repository validation pass; and
- frozen M35–M37 and WP1–WP9 artifacts remain unchanged.

All completion conditions are satisfied. WP10 is frozen as the implementation
authority for the Discovery Experience Runtime.
