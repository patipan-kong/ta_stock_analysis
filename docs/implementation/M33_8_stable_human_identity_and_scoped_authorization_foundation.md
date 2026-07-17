# M33.8 - Stable Human Identity and Scoped Authorization Foundation

**Date:** 2026-07-17

**Status:** Implemented as frozen, ORM-free contracts and one pure validator.
No identity provider, account/session/grant persistence, login change, M33
persistence, approval runtime, or production adoption is introduced.

**Milestone decision:** M33 consumes, but does not own, stable actor,
authentication, current-status, and scoped-authorization facts. One human may
cross the M33.7 approval boundary only when caller-supplied facts prove an
individually authenticated, active actor with an active session/credential and
one current `ALLOW` for `EXECUTION_INTENT_REVIEW` on the exact workspace and
portfolio. Shared credentials, system actors, delegation, impersonation,
unknown status, revoked or expired facts, implicit workspace inheritance, and
scope mismatch fail closed. Identity persistence remains an external
prerequisite.

## 1. Authoritative boundary

The governing inputs are:

- `docs/implementation/M33_1_execution_intent_snapshot_lifecycle_foundation.md`;
- `docs/implementation/M33_2_pure_execution_intent_contracts.md`;
- `docs/implementation/M33_3_legacy_adapter_feasibility.md`;
- `docs/implementation/M33_4_historical_authority_certification_contract.md`;
- `docs/implementation/M33_5_pure_authority_verification_contracts.md`;
- `docs/implementation/M33_6_authority_evidence_availability_and_issuer_governance.md`;
- `docs/implementation/M33_7_prospective_human_authority_and_direct_approval_capture_design.md`;
- `docs/implementation/M32_EPIC_CLOSEOUT.md`; and
- the M33 entries in `docs/engineering/DECISION_LOG.md`.

All predecessor boundaries remain in force:

- M32 remains closed and canonical execution planning remains NO-GO.
- M33.2 content hashing, actor types, lifecycle transitions, approval hash
  binding, and expected-prior-state/sequence validation are unchanged.
- M33.7 still requires a frozen snapshot, canonical review digest, display
  receipt, exact scope, stable actor, current authority, and atomic command/
  event/audit boundary before prospective approval.
- Authentication and authorization facts do not construct a snapshot, append
  a transition, approve an intent, admit a transaction, prove fulfillment, or
  mutate a portfolio.
- Historical rows, recommendations, optimizer output, shadows, transactions,
  holdings, current owner, and default workspace cannot supply identity or
  authority.
- This milestone adds no ORM, migration, repository, endpoint, frontend,
  writer, session store, role/grant store, identity provider, runtime import,
  certificate, key, adapter, or Graphify change.

The implementation is `backend/services/execution_intent_identity.py`. It has
no ORM, framework, environment, database, networking, token, credential, or
clock dependency.

## 2. Current-state limitation

The repository audit remains the one recorded in M33.6 and M33.7:

- `backend/auth.py` authenticates one environment username/password and issues
  a long-lived HS256 JWT signed by a source-code constant;
- `verify_token()` returns a boolean and the middleware in `backend/main.py`
  discards the token subject and all authentication context;
- the browser retains the bearer token in `localStorage`;
- `_ws_id()` resolves one default workspace, not an actor-scoped grant;
- `Workspace` and `Portfolio` have no user, membership, role, permission, or
  historical grant relationship;
- no user/account/session/membership/role/permission ORM model exists;
- the legacy decision endpoint retains no actor, authentication event, current
  status, grant, or point-in-time authorization fact; and
- the accepted request portfolio is not proved equal to the recommendation's
  portfolio before the legacy decision row is written.

Token possession therefore cannot prove which human acted or whether that
human had portfolio permission at an event time. The shared credential is not
eligible to produce a valid M33.8 human-authority result.

## 3. Identity ownership decision

### 3.1 Authentication/Authorization domain

A separate Application Identity and Access domain owns:

- account and stable-provider identity creation;
- usernames, email addresses, display names, credentials, password hashes,
  MFA, token issuance, cookies, login, recovery, and credential rotation;
- session creation, expiry, revocation, and authentication assurance;
- actor disablement, deletion, merge/replacement, and current status;
- workspace membership, roles, grants, portfolio permission, and policy
  evaluation;
- delegation and impersonation policy and evidence; and
- availability of current, point-in-time facts to relying domains.

M33.8 does not select a vendor, create a user store, or design a full IAM
platform. No current component is declared to be this owner merely because it
can parse a JWT or query a workspace.

### 3.2 M33 approval domain

M33 owns only:

- immutable opaque references supplied by the identity owner;
- the exact human-review permission required by approval;
- pure fail-closed validation of supplied facts against exact scope/time;
- domain-separated hashes used to bind those facts to a future M33.7 command
  receipt; and
- retention requirements for the references and point-in-time facts that
  supported an approval.

M33 never receives or retains credentials, password hashes, bearer tokens,
cookies, signing secrets, recovery material, mutable names, or a permission
query capability. It does not call an identity provider. Runtime orchestration
must obtain the facts before calling this pure module.

## 4. Implemented frozen contracts

All ids are caller-supplied opaque values. No contract generates an id, reads
time, or performs lookup.

| Contract | Purpose |
| --- | --- |
| `ActorRef` | Stable namespaced `HUMAN` or `SYSTEM` identity plus exact provider reference. |
| `AuthenticationEventRef` | One immutable authentication event, actor/provider binding, UTC validity interval, assurance, credential-state version, individual/shared binding, and direct/delegated/impersonated mode. |
| `ActorStatusFact` | Caller-supplied current actor, credential, and session state for the exact authentication event, with check and expiry times. |
| `AuthorizationScope` | Exact authority namespace, workspace id, and portfolio id. |
| `Permission` | `EXECUTION_INTENT_REVIEW` for approval/rejection; `EXECUTION_INTENT_PREPARE` is a typed non-approval value so permission mismatch can fail as data. |
| `GrantSourceRef` | Exact direct-portfolio or workspace-inherited grant source. |
| `ActorAuthorityFact` | Point-in-time `ALLOW`/`DENY`, exact actor/auth event/scope/permission, policy, grant/status, resource status, and UTC validity. |
| `IdentityValidationPolicy` | Named pure validation policy, supported fact/policy versions, assurance set, freshness limits, and explicit inheritance flag. |
| `IdentityValidationInput` | Complete caller-owned inputs for one validation. |
| `IdentityValidationResult` | `ACCEPTED` binding or one typed refusal, with no side effects. |
| `IdentityRefusalCode` | Stable fail-closed refusal taxonomy. |

All structures are frozen dataclasses. Unordered policy sets are `frozenset`s
and serialize in lexical order.

## 5. Stable actor semantics

### 5.1 Identity

`ActorRef` contains exactly:

- `contract_version`;
- M33.2 `ActorType` (`HUMAN` or `SYSTEM`);
- opaque `actor_id`;
- `authority_namespace`; and
- `identity_provider_ref`.

Stable identity is the pair of namespace/provider context and opaque actor id,
not username, email, display name, IP address, token subject without namespace,
session id, workspace owner, or administrator assertion. Mutable display data
does not exist in the contract or its hash.

Namespaces are compared as exact strings. An id from another deployment,
tenant, or provider namespace is not equivalent even when its text matches.

### 5.2 Human/system separation

`validate_human_authority()` is deliberately human-only. A `SYSTEM` actor is
representable for other domain references but receives
`SYSTEM_ACTOR_CANNOT_REVIEW` from this entry point. A system actor cannot carry
or borrow a human authentication event. M33.2 remains the final authority on
which lifecycle command types permit each actor type.

### 5.3 Shared credentials, delegation, and impersonation

- `CredentialBinding.SHARED` always produces
  `SHARED_CREDENTIAL_PROHIBITED`.
- `AuthenticationSubjectMode.DELEGATED` produces
  `DELEGATION_UNSUPPORTED`.
- `AuthenticationSubjectMode.IMPERSONATED` produces
  `IMPERSONATION_UNSUPPORTED`.
- Only `INDIVIDUAL` plus `DIRECT` is eligible in the MVP.

This makes the current shared application credential structurally
ineligible. No operator or deployment administrator can be recorded silently
as the approving human.

### 5.4 Disablement, deletion, merge, and replacement

An actor must have current status `ACTIVE`. `DISABLED`, `DELETED`, and
`UNKNOWN` each fail closed. Deletion does not authorize physical removal of a
stable id from historical approval audit; the old opaque id becomes audit-only
and cannot act again.

Actor ids are never merged or reused. If an identity owner merges accounts or
replaces a provider identity, it creates and records an explicit external
lineage/correlation; the old and new `ActorRef`s remain distinct. M33.8 does
not follow replacement automatically or rewrite prior facts.

Pseudonymization may replace externally displayed personal data, which M33
does not retain. Any transformation of the opaque audit id must remain stable,
non-reassignable, and referentially consistent for the full approval retention
period.

## 6. Authentication-event and current-status contracts

### 6.1 Authentication event

`AuthenticationEventRef` binds:

- version and opaque event id;
- exact `ActorRef` and matching provider;
- authority-owned UTC `authenticated_at` and `valid_until`;
- typed method-assurance class;
- credential-status version observed when authenticating;
- individual/shared credential binding; and
- direct/delegated/impersonated subject mode.

It contains no credential, token, JWT, cookie, secret, or client assertion.
Possessing a client token is not equivalent to providing this fact. The owning
domain must authenticate it and supply the reference.

### 6.2 Current actor/session fact

`ActorStatusFact` is distinct because an authentication event that was valid
when issued may later become unusable. It binds the exact actor and event to:

- actor lifecycle status;
- current credential status and version;
- current session status;
- authority-owned UTC `checked_at`; and
- explicit `valid_until`.

`REVOKED` credential or session status fails closed. Every `UNKNOWN` state
fails closed. The status version must equal the version referenced by the
authentication event. A valid event cannot override later disablement or
revocation.

### 6.3 Time and assurance

Authentication must not occur in the future, must be strictly unexpired at
validation, and must not exceed `max_authentication_age`. The actor-status fact
has equivalent not-future, explicit-expiry, and maximum-age checks.

Only assurance classes explicitly listed by the named validation policy are
accepted. The contract does not claim that one assurance class is universally
sufficient; the identity owner and product/security authority must approve the
set.

## 7. Scoped authorization and grant semantics

### 7.1 Exact scope

`AuthorizationScope` always contains both workspace and portfolio ids plus the
authority namespace. Validation compares exact ids. It performs no default-
workspace, current-owner, current-membership, fuzzy-id, or name inference.

The authority fact also carries `workspace_status` and `portfolio_status`.
Deleted or unknown resources fail closed. A portfolio from another workspace
cannot be rescued by matching the portfolio id alone.

### 7.2 Permission and decision

The approval/rejection boundary requires
`Permission.EXECUTION_INTENT_REVIEW`. A different permission returns
`PERMISSION_MISMATCH`. `AuthorityDecision.DENY` returns `AUTHORITY_DENIED`
regardless of the grant label.

### 7.3 Grant source and current status

`GrantSourceRef` identifies one source as:

- `DIRECT_PORTFOLIO`; or
- `WORKSPACE_INHERITED`.

A direct portfolio grant may support authority when every other fact passes.
A workspace-inherited grant supports a portfolio only when the exact
`IdentityValidationPolicy` explicitly enables inheritance. Merely belonging
to a workspace, resolving a default workspace, or being its current owner is
not inheritance evidence.

Grant status must be `ACTIVE`. `REVOKED`, `EXPIRED`, and `UNKNOWN` have
distinct refusals. The authority check must not be in the future, must be
strictly before its explicit expiry, and must be no older than
`max_authority_check_age`.

## 8. Pure validation entry point

```python
validate_human_authority(
    actor_ref,
    authentication_event,
    actor_status_fact,
    authority_fact,
    required_scope,
    required_permission,
    validation_time,
    policy,
) -> IdentityValidationResult
```

The function:

- receives every fact and the UTC validation instant from its caller;
- parses no token and queries no identity provider, database, grant service,
  environment variable, or clock;
- returns one deterministic refusal for an expected failure;
- appends no event and performs no mutation;
- returns no partial validated authority on refusal; and
- on success exposes the exact actor, authentication event, actor-status fact,
  authority fact, scope, permission, effective validity interval, component
  hashes, and successful-binding hash.

The effective `valid_from` is the latest of authentication, current-status,
and authorization check times. The effective `valid_until` is the earliest of
their explicit expiries and policy freshness ceilings. A later approval
command must be accepted inside that interval and must revalidate current
facts as required by M33.7; a stored successful result is not an indefinite
bearer capability.

Malformed construction primitives such as blank ids, invalid enum values,
nonpositive scope ids, inverted validity ranges, naive datetimes, and non-UTC
offsets raise `ValueError`. Actor disablement, expiry, revocation, mismatch,
and policy failure are business refusals returned as data.

## 9. Deterministic refusal precedence

The validator returns the first applicable reason in this order:

1. unsupported validation/fact contract or validation/authorization policy;
2. authority-namespace mismatch;
3. non-human/system actor at the human-review boundary;
4. missing authentication event, then shared credential, delegation, or
   impersonation;
5. authentication actor/provider mismatch, missing/mismatched actor-status
   fact, and missing/mismatched authority actor/authentication fact;
6. disabled/deleted/unknown actor, revoked/unknown credential, credential-
   status version mismatch, and revoked/unknown session;
7. future, expired, or stale authentication/status fact, then unsupported
   assurance;
8. workspace mismatch, portfolio mismatch, then deleted/unknown resource;
9. permission mismatch;
10. `DENY`, revoked/expired/unknown grant;
11. future, expired, or stale authority check, then prohibited workspace
    inheritance; and
12. success.

No latest-row, most-recent-timestamp, majority, current-owner, source-priority,
or permissive-default rule exists.

## 10. Canonical serialization and binding hashes

M33.8 requires hashes because M33.7's future command/audit receipt must bind
the exact facts validated, not mutable external records with the same ids.

Version 1 provides explicit serializers and domain-separated SHA-256 hashes:

| Hash | Included fields |
| --- | --- |
| `compute_actor_ref_hash()` | Every `ActorRef` field. |
| `compute_authentication_event_ref_hash()` | Every event field, including the explicit actor projection, provider, UTC times, assurance, credential-state version, credential binding, and subject mode. |
| `compute_actor_authority_fact_hash()` | Every authority field, including exact scope, grant source, policy, status, decision, and UTC interval. |
| `compute_identity_validation_binding_hash()` | Actor, authentication, actor-status and authority facts; required scope/permission; validation time; effective validity interval; and complete validation policy. |

Serialization rules are:

- hand-built explicit dictionaries only; no generic dataclass reflection;
- JSON with sorted keys and compact separators;
- canonical timezone-aware UTC ISO-8601;
- lexical ordering for policy sets;
- lowercase `sha256:<64-hex>` output; and
- domain separator `M33.8:<artifact>:<contract-version>\n`.

Excluded data includes password/password hash, credential bytes, token, JWT,
cookie, secret, signing key, username, email, display name, IP address, user
agent, localized presentation, and UI state. Those values are neither fields
nor hash inputs.

These hashes are separate from and do not change:

- M33.2 `ExecutionIntentSnapshot.content_hash`; or
- M33.7 `ReviewPayloadV1` digest.

A future M33.7 command receipt may retain the component and validation-binding
hashes beside immutable fact references. They are audit bindings, not
credentials, capability tokens, snapshot content, approval, or execution
evidence.

## 11. Test coverage

`backend/tests/test_execution_intent_identity_m33_8.py` covers:

- valid direct human authority and explicit workspace inheritance;
- immutable structures, deterministic output, and zero side effects;
- stable actor identity independent of display attributes;
- shared credentials, `HUMAN`/`SYSTEM` separation, delegation, and
  impersonation;
- missing/mismatched actor, provider, authentication, status, and authority
  facts;
- disabled/deleted/unknown actor; revoked/unknown credential/session; and
  credential-state version mismatch;
- future, expired, and stale authentication/status/authority facts;
- assurance-policy refusal;
- exact workspace/portfolio matching and deleted/unknown resources;
- permission mismatch, `DENY`, and revoked/expired/unknown grant;
- direct grant, explicitly allowed inheritance, and prohibited implicit
  inheritance;
- deterministic refusal precedence;
- strict UTC construction and malformed primitive rejection;
- canonical ordering, domain hash syntax/determinism, included-field
  sensitivity, and successful status/policy binding; and
- structural exclusion of secrets and mutable display identity.

The isolated suite passes: **106 passed**.

## 12. Persistence-prerequisite exit criteria

M33 remains **`IDENTITY_OWNER_IMPLEMENTATION_REQUIRED`**. Persistence design
may begin only when an owning Authentication/Authorization domain can provide
evidence for all of the following in a representative non-production
integration or approved fixture package:

1. a named identity owner/provider and stable authority namespace;
2. unique, non-reassignable human actor ids distinct from usernames, emails,
   display names, and sessions;
3. individual rather than shared human credentials;
4. unique authentication-event ids, assurance, UTC event/expiry times, and
   credential-state version;
5. current active/disabled/deleted actor, credential, and session status with
   revocation semantics;
6. exact workspace and portfolio permission evaluation for
   `EXECUTION_INTENT_REVIEW`;
7. stable grant-source references, authorization-policy version, and explicit
   inheritance behavior;
8. deleted/unknown resource status and fail-closed availability behavior;
9. separation of human and service identities;
10. a caller adapter that constructs the M33.8 contracts without exposing
    credentials or performing inference inside M33;
11. passing fixtures for valid, disabled, revoked, expired, unknown, mismatch,
    shared-credential, and race/current-status cases; and
12. an approved retention/pseudonymization policy preserving historical audit
    references without retaining mutable personal display data in M33.

An account table alone, a JWT subject alone, a current workspace owner, or a
boolean permission response without a retained fact does not satisfy exit.
There is no user/account persistence approval in M33.8.

## 13. Relationship to M33.7 approval capture

M33.7's future authority boundary can refer without ambiguity to:

- `ActorRef` and its hash;
- `AuthenticationEventRef` and its hash;
- `ActorStatusFact` id and state included in the successful-binding hash;
- `ActorAuthorityFact` and its hash;
- exact `AuthorizationScope` and `EXECUTION_INTENT_REVIEW`;
- the validation time and effective validity interval; and
- the M33.8 successful validation-binding hash.

This satisfies the identity portion of the future `ApprovalCommand` grammar
without putting credentials or permission queries in the command. It does not
implement the M33.7 `ReviewPayloadV1`, display receipt, command normalization,
idempotency boundary, persistence transaction, audit receipt, or M33.2
transition mapping.

## 14. Explicit non-adoption statement

M33.8 does not:

- modify `backend/auth.py`, `backend/main.py`, ORM models, APIs, or frontend;
- add a user/account/membership/role/permission/session/grant model,
  migration, repository, or store;
- change login, JWT/token issuance, middleware, cookies, local storage,
  workspace resolution, or portfolio authorization;
- perform token parsing, database access, permission lookup, environment
  access, network access, id generation, or clock reads;
- create or persist an actor, authentication event, status fact, grant,
  authority fact, validation result, snapshot, display receipt, approval
  command, transition, audit receipt, or quarantine record;
- add M33 intent/lifecycle persistence or runtime authorization wiring;
- construct an `ExecutionIntentSnapshot` or call lifecycle validation;
- change M33.2 or M33.7 hashing;
- add certificate, signature, key, trust, or revocation infrastructure;
- adapt, backfill, dual-write, rank, repair, or mutate legacy data;
- change recommendation, optimizer, decision, expiry, shadow, transaction,
  portfolio, ledger, evaluation, or replay behavior;
- change Graphify output; or
- reopen M32 or adopt canonical execution planning.

## 15. Recommended next milestone

**M33.9 - Identity Authority Provider Selection and Integration Feasibility
Study (design-only, owned with the Authentication/Authorization domain).**

M33.9 should select and name the actual provider/owner capable of satisfying
section 12, map its stable actor/authentication/status/grant facts to the M33.8
contracts, define status freshness and outage behavior, establish retention
and pseudonymization ownership, and produce an integration fixture catalogue.
It should end with a concrete readiness decision for M33 persistence design.

M33.9 should not add account/session/grant tables, migrations, login/token
changes, APIs, frontend, approval endpoints, M33 persistence, runtime wiring,
certificates, legacy adaptation, snapshot construction, lifecycle transitions,
or Graphify changes. If no owner can supply stable per-human and scoped facts,
M33 runtime adoption must stop after the pure foundation rather than treating
the current shared credential as authority.
