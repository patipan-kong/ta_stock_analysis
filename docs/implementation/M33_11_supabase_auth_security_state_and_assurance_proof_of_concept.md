# M33.11 - Supabase Auth Security-State and Assurance Proof of Concept

**Date:** 2026-07-17

**Status:** Complete. Final bounded provider-feasibility assessment and
prerequisite audit only. No Supabase project, user, credential, session, key,
SDK, adapter, evidence store, identity persistence, or runtime adoption was
created.

**Milestone decision:** **`STOP_M33_RUNTIME`**. The environment contains no
approved non-production Supabase configuration and no Supabase CLI, Docker, or
Podman capability with which to create an isolated local project. Consequently
none of the mandatory provider properties could be proved empirically. Current
official documentation establishes useful candidate primitives, but it cannot
substitute for the required account mutation, authentication, revocation,
propagation, outage, key-rotation, recovery, and deterministic security-state
fixtures. A mandatory unproved property prevents
`IMPLEMENTATION_DESIGN_READY`.

M33.1-M33.8 remain pure foundations. Prospective M33 human-approval runtime is
stopped. This decision does not reject Supabase as a general authentication
product; it records that Supabase was not proved sufficient for this unusually
strict approval-authority boundary within the final approved provider
feasibility milestone.

## 1. Authoritative boundary

The governing inputs are:

- `docs/implementation/M32_EPIC_CLOSEOUT.md`;
- `docs/implementation/M33_1_execution_intent_snapshot_lifecycle_foundation.md`;
- `docs/implementation/M33_2_pure_execution_intent_contracts.md`;
- `docs/implementation/M33_3_legacy_adapter_feasibility.md`;
- `docs/implementation/M33_4_historical_authority_certification_contract.md`;
- `docs/implementation/M33_5_pure_authority_verification_contracts.md`;
- `docs/implementation/M33_6_authority_evidence_availability_and_issuer_governance.md`;
- `docs/implementation/M33_7_prospective_human_authority_and_direct_approval_capture_design.md`;
- `docs/implementation/M33_8_stable_human_identity_and_scoped_authorization_foundation.md`;
- `docs/implementation/M33_9_identity_authority_provider_selection_and_integration_feasibility.md`;
- `docs/implementation/M33_10_managed_identity_claim_current_status_and_revocation_proof_of_concept.md`;
- the M33 entries in `docs/engineering/DECISION_LOG.md`.

All predecessor boundaries remain in force:

- M32 remains closed and canonical execution planning remains NO-GO.
- M33.8 contracts and `validate_human_authority()` are unchanged. Missing
  provider evidence is not repaired by weakening actor, assurance, status,
  scope, time, freshness, or fail-closed rules.
- `ActorRef.actor_id` remains an application-owned, permanent, opaque,
  non-reassignable id. Supabase issuer and subject could only identify a
  replaceable provider binding.
- JWT signature/expiry, cached state, webhooks, `aal`, `amr`, a user row, or a
  session row cannot alone establish current M33 approval authority.
- Supabase roles, RLS claims, email, username, display name, current owner, and
  the legacy shared credential cannot become application workspace/portfolio
  authority.
- Identity facts do not create an execution-intent snapshot, lifecycle event,
  approval, transaction, ledger fact, fulfillment fact, or portfolio mutation.
- No Supabase-specific object or enum may enter M33.8, M33.7, M33.2, or an
  execution-intent contract.

The milestone's success criterion is an honest terminal decision, not provider
adoption. Because the empirical prerequisite was absent, the specified final
rule requires `STOP_M33_RUNTIME`; it does not permit another provider or
another documentary provider study.

## 2. Evidence classification and method

Findings use exactly these classifications:

| Classification | Meaning in this study |
| --- | --- |
| `EMPIRICALLY_PASSED` | A behavior was exercised against a real isolated Supabase environment and retained as sanitized evidence. No provider fixture has this classification. |
| `EMPIRICALLY_FAILED` | An attempted empirical prerequisite or behavior did not pass. Environment availability failed: no approved configuration or usable local stack existed. |
| `DOCUMENTARY_ONLY` | Current official Supabase documentation describes a candidate behavior, but no local observation proved it. |
| `SIMULATED_AT_ADAPTER_BOUNDARY` | A provider-neutral failure/result was injected into an isolated adapter. No provider adapter was added, so no provider fixture has this classification. Existing M33.8 unit fixtures are pure contract tests, not Supabase simulations. |
| `NOT_EXECUTED` | The provider fixture was not run. Every live Supabase fixture is in this class. |
| `MANDATORY_BLOCKER` | The missing empirical result is required for `IMPLEMENTATION_DESIGN_READY`; its absence contributes to the stop decision. |

The study performed:

1. complete predecessor-boundary review;
2. read-only repository and deployment inspection;
3. environment-variable **name-only** inspection for approved provider
   configuration;
4. tool/runtime availability checks for Supabase CLI, Docker, and Podman;
5. current official Supabase documentation review;
6. unchanged M33.8 source/test inspection and execution; and
7. repository-scope, dependency, secret, personal-data, and document-quality
   validation.

It did not create an external resource, install a tool, make a provider API
request, create a synthetic user, issue a token, query `auth.users` or
`auth.sessions`, enroll a factor, or perform a mutation. No raw provider data
exists to sanitize, so no `docs/implementation/evidence/m33_11/` directory was
created. An empty or simulated evidence directory would falsely suggest an
empirical POC.

## 3. Environment and synthetic-fixture result

### 3.1 Repository/configuration discovery

The prerequisite audit found:

- no `SUPABASE_*`, `NEXT_PUBLIC_SUPABASE_*`, Clerk, or other provider identity
  configuration among repository environment-variable names;
- no Supabase URL, project reference, SDK import, client construction, or
  provider adapter outside the M33.9/M33.10 documentation;
- no Supabase dependency in the inspected Python or frontend dependency paths;
- no approved project identifier, non-production API key, synthetic account,
  test fixture, or provider owner; and
- no retained evidence that an external non-production project was approved
  for this workspace.

Secret values were not printed or inspected. The absence conclusion is about
configuration names and references available to this workspace, not about
resources that might exist in an undocumented external account.

### 3.2 Local isolated-stack capability

The tool check returned:

| Capability | Result | Classification |
| --- | --- | --- |
| Supabase CLI | Absent | `EMPIRICALLY_FAILED` prerequisite |
| Docker CLI/daemon | Absent | `EMPIRICALLY_FAILED` prerequisite |
| Podman CLI/daemon | Absent | `EMPIRICALLY_FAILED` prerequisite |
| Approved hosted project/configuration | Not present | `EMPIRICALLY_FAILED` prerequisite |

Creating a hosted project would require an external account, provider
credentials, project ownership, region/privacy choices, and retained secrets
that were not available. Installing a new local container/CLI stack would
expand the approved environment and dependency surface rather than use an
already approved resource. Neither path could be performed honestly within
the available environment.

### 3.3 Synthetic-fixture conclusion

There was no environment in which to create synthetic passwords, factors,
sessions, recovery events, signing keys, or provider mutations. Therefore:

- provider fixture count executed: **0**;
- provider fixtures empirically passed: **0**;
- raw tokens/secrets/personal data retained: **0**;
- sanitized provider evidence artifacts created: **0**; and
- mandatory provider properties empirically proved: **0**.

This is not silently converted into a documentary POC. The explicit brief rule
states that absent configuration plus inability to create an isolated project
must produce a blocker and `STOP_M33_RUNTIME`.

## 4. Repository and architecture consistency

The current repository remains consistent with M33.6-M33.10:

- `backend/auth.py` compares one environment username/password, issues a
  30-day HS256 JWT using a source-code constant, and returns only boolean token
  validity.
- `backend/main.py` authentication middleware discards subject, issuer,
  session, method, actor, and current-status context.
- `_ws_id()` selects the default workspace rather than evaluating an
  actor-scoped grant.
- `frontend/lib/auth.ts` retains the bearer token in `localStorage`, and
  `frontend/lib/api.ts` sends it to the FastAPI backend.
- `Workspace`, `Portfolio`, and `UserExecutionDecision` have no account,
  membership, role, permission, session, or grant relationship.
- no production identity/provider adapter, status reader, receipt boundary,
  or application-owned authorization domain exists.
- deployment remains Next.js/Vercel plus FastAPI/PostgreSQL under PM2 on a VPS.

The current shared credential remains ineligible for M33.8. Nothing in M33.11
attributes old requests or legacy decisions to a future actor.

## 5. Documentary Supabase capability baseline

The following official sources were current when reviewed on 2026-07-17:

- [JWT Claims Reference](https://supabase.com/docs/guides/auth/jwt-fields)
  documents required issuer, audience, expiry, issue time, subject, role, AAL,
  and session id claims plus optional timestamped AMR entries.
- [User sessions](https://supabase.com/docs/guides/auth/sessions) documents the
  `session_id` relationship to `auth.sessions`, refresh behavior, termination
  conditions, delayed cleanup, and the stronger sensitive-action check that a
  session row still exists.
- [Retrieve a user](https://supabase.com/docs/reference/python/auth-getuser)
  documents a database-backed server user lookup with `deleted_at` and
  `banned_until` fields.
- [Signing out](https://supabase.com/docs/guides/auth/signout) documents local,
  global, and other-session scopes and states that revoked-session access JWTs
  remain valid until expiry.
- [User management](https://supabase.com/docs/guides/auth/managing-user-data)
  documents managed `auth.users`, deletion/export, immutable primary keys, and
  the fact that deletion does not itself invalidate an already issued JWT.
- [Multi-Factor Authentication](https://supabase.com/docs/guides/auth/auth-mfa)
  documents `aal1`/`aal2`, factor listing, challenge/verification, and stale
  AAL behavior after factor removal.
- [JWT Signing Keys](https://supabase.com/docs/guides/auth/signing-keys)
  documents current/standby/previous/revoked keys and multi-level JWKS caching.
- [Passkey authentication](https://supabase.com/docs/guides/auth/passkeys)
  identifies passkeys as experimental and explicitly opt-in.
- [Migrating Auth Users Between Supabase Projects](https://supabase.com/docs/guides/troubleshooting/migrating-auth-users-between-projects)
  documents auth-schema export/import and signing-trust consequences.

These sources establish plausible inputs, not POC passes. In particular:

- an AMR entry describes a token claim; it does not prove the application
  retained a unique authentication receipt under the intended policy;
- an AAL describes assurance in a session token; it does not prove recovery
  exclusion, freshness, downgrade behavior, or current credential state;
- a database-backed user response does not by itself prove propagation bounds,
  outage classification, or all security-relevant revisions;
- a session row check is promising but was not tested for cleanup, expiry,
  concurrent revocation, project access, or transactional race behavior; and
- documented JWKS caches make key-state testing more important, not optional.

## 6. Permanent application actor and provider binding

The provider-neutral rule from M33.10 remains the only acceptable design:

```text
ApplicationActor
  actor_id: permanent opaque application id

ProviderActorBinding
  actor_id
  provider_configuration_id
  canonical_issuer
  provider_subject
  binding_revision
  binding_status
```

Documentary evidence says the JWT `sub` is the provider user UUID and that
managed `auth.users` primary keys do not change in place. It does not prove the
complete application behavior required by this milestone:

- initial binding and tombstone creation;
- deletion followed by recreation using the same synthetic address;
- absence of email/name identity joining;
- explicit merge and migration handling;
- stable application actor lineage across project/provider movement; and
- `UNKNOWN` for unresolved migration or recreation.

No application actor/binding persistence was authorized or implemented, and no
provider subject was observed. The relationship is therefore
`DOCUMENTARY_ONLY`, `NOT_EXECUTED`, and a `MANDATORY_BLOCKER`.

## 7. Claim and session mapping

### 7.1 Documentary candidate projection

If a later externally imposed requirement reopened this work, a provider
adapter could consider this sanitized projection; it is not approved here:

| Neutral fact | Documentary Supabase source | M33.11 result |
| --- | --- | --- |
| Canonical issuer | JWT `iss` | `DOCUMENTARY_ONLY` |
| Provider subject | JWT `sub` plus server user id | `DOCUMENTARY_ONLY` |
| Exact session id | JWT `session_id` plus `auth.sessions.id` | `DOCUMENTARY_ONLY` |
| Token times | JWT `iat`, `nbf`, `exp` | `DOCUMENTARY_ONLY`; transport only |
| Authentication methods | timestamped JWT `amr` entries | `DOCUMENTARY_ONLY`; exact flows untested |
| Assurance | JWT `aal` plus current/next AAL and verified factor inventory | `DOCUMENTARY_ONLY`; stale/downgrade paths untested |
| Token kind | exact issuer/audience/role/anonymous fields under local policy | `DOCUMENTARY_ONLY` |
| Signing trust | header `kid`/`alg` plus configured JWKS trust | `DOCUMENTARY_ONLY` |
| Current user | server `get_user(jwt)` and managed user state | `DOCUMENTARY_ONLY` |
| Exact session status | privileged exact `auth.sessions` lookup | `DOCUMENTARY_ONLY`; access/race semantics untested |

Email, phone, names, user metadata, application metadata, and raw tokens are
excluded from the neutral projection. Supabase `role` or custom claims cannot
become portfolio authorization.

### 7.2 Refresh rule

Official session documentation says an access/refresh-token pair is renewed as
the session continues, and the claims grammar includes `amr` timestamps. That
supports, but does not empirically prove, these required rules:

- refresh changes transport-token identity and expiry;
- refresh does not create a human authentication receipt;
- refresh does not reset original authentication occurrence; and
- refresh does not increase assurance without a new qualifying ceremony.

No before/after token projection was observed. The refresh fixture is
`NOT_EXECUTED` and mandatory.

## 8. Authentication-event semantics and assurance

`AuthenticationEventRef.authentication_event_id` would remain an
application-created opaque receipt, never the Supabase user, session, token,
or AMR id. No receipt may be created unless the provider adapter proves exact
direct-human method, occurrence time, freshness, assurance, current user,
exact current session, provider binding, and non-recovery status.

| Path | Candidate M33.8 class | Evidence | Result |
| --- | --- | --- | --- |
| Direct password authentication | `PASSWORD` only if exact recent `password` AMR is bound to the exact session | Official claim grammar only | `NOT_EXECUTED`; mandatory blocker |
| Password plus verified TOTP | `MULTI_FACTOR` only with exact `password` + `totp`, `aal2`, freshness, factor state, and no recovery | Official AAL/AMR/MFA docs only | `NOT_EXECUTED`; mandatory blocker |
| Federated sign-in | `FEDERATED_HIGH` only under a separate approved issuer/ACR/AMR policy | Generic OAuth/SSO support is insufficient | Unsupported for this POC |
| Passkey | At most a class proven by stable server evidence; never inferred as `HARDWARE_BOUND` | Feature is experimental | Not a permitted readiness path |
| Remembered session or refresh | None | Session continuation only | Must never create a receipt; not empirically proved |
| Recovery/backup/reset | None | Recovery method must be excluded | Must never create approval-eligible receipt; not empirically proved |
| Unknown, duplicate, or ambiguous AMR | None | Fail closed | Not empirically proved |

No honest M33.8 assurance mapping was empirically established for even one
direct-human, non-recovery path. This alone prevents
`IMPLEMENTATION_DESIGN_READY`.

## 9. Current user status

The intended fail-closed mapping remains:

| Observed provider result | M33.8 mapping | Evidence status |
| --- | --- | --- |
| Exact user exists, binding active, `deleted_at` absent, ban expired/absent | `ActorLifecycleStatus.ACTIVE` candidate | Documentary only; not executed |
| Current ban/disable under approved policy | `DISABLED` | Documentary field exists; not executed |
| Authoritative deletion plus application binding tombstone | `DELETED` | Documentary field/delete behavior only; not executed |
| Timeout, rate limit, outage, malformed/partial/unknown version, ambiguous absence, stale projection | `UNKNOWN` | Required local rule; not simulated against an adapter |

A locally valid JWT must never override `DISABLED`, `DELETED`, or `UNKNOWN`.
No administrative mutation was made, so mutation-to-observation latency has no
observed range. No provider propagation bound is claimed.

## 10. Exact session status and revocation

Official documentation provides the strongest Supabase candidate: JWT
`session_id` correlates to `auth.sessions`, and for sensitive actions the
application may check that the row still exists after sign-out. It also states
that access JWTs can remain valid until expiry and that expired sessions may be
cleaned up progressively later.

Those facts do not empirically establish:

- exact privileged lookup availability to the intended backend;
- active versus expired versus revoked versus cleanup-delayed semantics;
- single-session and global-sign-out timing;
- another-device session isolation;
- deleted-user/session behavior while a JWT still verifies;
- missing-row authoritative classification versus query failure;
- concurrent revocation/approval ordering; or
- the transaction-time recheck needed before an approval commit.

No sign-out, revoke, expiry, delete, or concurrent mutation was executed.
Observed revocation propagation range: **not available**. Maximum accepted
application grace remains **zero**; inability to confirm the exact session at
the approval boundary maps to `SessionStatus.UNKNOWN` and refusal.

## 11. Credential-security state and deterministic revision

### 11.1 Candidate grammar, not an approved version

The required form remains a provider-neutral, domain-separated hash:

```text
credential_status_version =
  "identity-status-v1:sha256:" + lowercase_hex(
    SHA-256(
      "M33.11:identity-security-state:1\n" + canonical_utf8_payload
    )
  )
```

Candidate canonical fields, only when authoritative and complete, would be:

- adapter/provider/schema/policy versions;
- application authority namespace, permanent actor id, provider-binding id,
  binding revision, and binding status;
- canonical issuer and provider subject;
- exact current user security timestamps/status, excluding profile data;
- complete verified MFA factor ids/types/statuses/creation-update instants;
- explicit recovery/security state when the selected path requires it;
- exact session id, authoritative current status, and relevant expiry;
- canonical current AAL and ordered AMR method/timestamp projection;
- application assurance-policy version; and
- explicit `PRESENT`, `ABSENT`, or `UNKNOWN` markers.

Excluded inputs are access/refresh tokens, cookies, passwords, MFA secrets or
codes, recovery codes, provider keys, email, phone, names, display/profile
metadata, IP, user agent, and frontend state.

### 11.2 Sensitivity result

| Required sensitivity | Empirical result |
| --- | --- |
| Identical facts produce identical version | Not executed |
| Password change alters/invalidate version | Not executed |
| MFA enrollment alters version | Not executed |
| MFA removal alters version | Not executed |
| Recovery alters/invalidate version | Not executed |
| Session revocation changes acceptance | Not executed |
| Non-security profile edit behavior is explicit | Not executed |
| Refresh does not create a new authentication event | Not executed |
| Field order does not alter hash | Not executed |
| Missing input produces `UNKNOWN`, never a partial hash | No adapter implemented; pure rule only |

The repository contains no isolated transformer to hash these fields, because
without real provider projections such code would test only a self-invented
schema. More importantly, the study did not prove that the provider exposes a
complete authoritative basis for detecting every security-relevant change in
the permitted approval path. This mandatory gap independently requires
`STOP_M33_RUNTIME`.

## 12. JWT signing keys and trust

Official documentation establishes a JWKS endpoint, key lifecycle, issuer/
audience/time claims, and layered cache behavior. It states that edge and
client caches can create roughly 20 minutes or more of application-side key
visibility depending on custom caching, and recommends explicit cache control
for urgent revocation.

No key was observed and none of these mandatory cases was exercised:

- current key verification;
- standby/current overlap and rotation;
- unknown `kid`;
- known-key and unknown-key JWKS outage;
- stale JWKS cache;
- emergency key revocation;
- issuer/audience/algorithm mismatch;
- expired/not-yet-valid token; and
- allowed/excessive clock skew.

Unknown trust always blocks approval. Cryptographic token acceptance remains
separate from current user, current session, credential-security, and local
authorization checks.

## 13. Webhook and cache behavior

No Supabase webhook or local provider-status cache existed to delay, drop,
duplicate, reorder, or invalidate. The intended invariant remains:

- webhook/cache input may deny early or trigger a synchronous refresh;
- neither may establish positive current authority;
- cached `ACTIVE` never extends approval authority;
- synchronous user, exact-session, provider-binding, and application-grant
  facts govern; and
- any ambiguity maps to `UNKNOWN`.

These rules are architecture consistency, not empirical Supabase proof.

## 14. Outage and failure matrix

No adapter was implemented, so the table records required normalized behavior
rather than simulated passes:

| Failure | Required neutral outcome | M33.8 consequence | Evidence |
| --- | --- | --- | --- |
| Provider/network/DNS/TLS outage | `UNKNOWN` | Refuse; zero events | Not executed |
| Current-user endpoint outage | `UNKNOWN` | Actor/credential status unavailable; refuse | Not executed |
| Exact-session query/store outage | `UNKNOWN` | Session status unavailable; refuse | Not executed |
| Provider database unavailable | `UNKNOWN` | Refuse | Not executed |
| JWKS outage with approved cached known key | Token gate only may pass under policy | Still require all current facts | Not executed |
| JWKS outage with unknown key | `UNKNOWN` trust | Refuse | Not executed |
| Rate limit | `UNKNOWN`; retry metadata only | Refuse | Not executed |
| Malformed, partial, unknown schema/version | `UNKNOWN` | Refuse | Not executed |
| Clock disagreement beyond policy | `UNKNOWN` | Refuse | Not executed |
| Local authorization-store outage | No `ActorAuthorityFact` | M33.8 refuses | Pure missing-fact behavior covered by unchanged tests, not provider proof |
| Concurrent grant revocation | Stale/mismatched authority fact | Refuse under future CAS/recheck | Pure fixtures only; no runtime race executed |

Every case would append zero approval/lifecycle events because M33.11 contains
no approval runtime. That structural absence is not evidence that a future
adapter correctly implements the mapping.

## 15. Provider-neutral adapter proof

The intended dependency boundary remains:

```text
Supabase token/API/auth-schema evidence
                  |
                  v
Supabase-specific verifier/status reader
                  |
                  v
provider-neutral identity source result
                  |
                  v
ActorRef + AuthenticationEventRef + ActorStatusFact
                  |
                  v
unchanged validate_human_authority()
```

No provider adapter or transformer was added because there was no real evidence
schema to transform. A fake adapter would prove only that code written to its
own fixtures can pass its own assumptions.

Repository inspection confirms that Supabase SDK types, `auth.users`,
`auth.sessions`, `aal`, `amr`, project ids, provider exceptions, and provider
dependencies do not appear in production M33 modules. The isolation/leakage
check therefore passes as a **structural negative finding**, not as an adapter
implementation pass.

## 16. Unchanged M33.8 validation and authorization fixtures

The isolated unchanged suite
`backend/tests/test_execution_intent_identity_m33_8.py` passes in full:
**106 passed**. It covers direct and inherited authority, shared/system actor
refusal, delegation/impersonation refusal, disabled/deleted/unknown actor,
revoked/unknown credential/session, status-version mismatch, time/freshness,
assurance, exact scope, deny/revoked/expired/unknown grant, deleted/unknown
resources, policy versions, canonical hashes, and deterministic precedence.

That suite proves the M33.8 consuming contract remains deterministic and
fail-closed. It does **not** prove that Supabase can produce the complete facts
accepted by the contract. Specifically:

| Authorization fixture | M33.8 status | Supabase relevance |
| --- | --- | --- |
| Direct portfolio grant | Pure fixture passes | Application-owned; not supplied by Supabase |
| Explicit workspace inheritance | Pure fixture passes | Application-owned named policy |
| Denied/revoked/expired grant | Pure refusals pass | Application-owned |
| Disabled workspace/deleted portfolio | Pure refusals pass | Application resource state |
| Policy/scope/actor/status-version mismatch | Pure refusals pass | Provider adapter must supply exact neutral facts |
| Stale status | Pure refusal passes | Provider freshness unmeasured |
| Missing authority fact/store outage | Pure refusal behavior passes | Runtime store not implemented |
| Concurrent grant revocation | Contract can refuse stale input | Runtime transaction/recheck not implemented |

Supabase role or JWT custom claims are not used as grants.

## 17. Mandatory fixture catalogue and readiness impact

No official source substitutes for a mandatory empirical fixture unless the
row says otherwise. All rows required to establish current behavior remain
blocking.

| Fixture | Execution | Documentary substitute? | Mandatory? | Readiness impact |
| --- | --- | --- | --- | --- |
| Individual password login | Not executed: no project/user | Claims describe candidate result only | Yes | Blocker |
| Password reauthentication | Not executed | AMR grammar does not prove configured ceremony | Yes | Blocker |
| Password plus TOTP | Not executed | AAL/MFA docs are insufficient | Yes for proposed MFA path | Blocker |
| Remembered-session refresh | Not executed | Session docs support intended rule only | Yes | Blocker |
| Token refresh | Not executed | Documentary only | Yes | Blocker |
| Recovery and recovery-code exclusion | Not executed | AMR includes recovery concepts but path unobserved | Yes | Blocker |
| Password reset | Not executed | No exact retained event evidence | Yes | Blocker |
| MFA enrollment/removal/challenge | Not executed | APIs/stale-AAL behavior documented | Yes | Blocker |
| Passkey | Not executed; feature experimental | No; not required if another direct path passes | No for initial path | Deferred/unsupported |
| Disable/ban | Not executed | `banned_until` documented | Yes | Blocker |
| Soft delete | Not executed | `deleted_at` documented | Yes if selected status grammar uses it | Blocker |
| Hard delete and valid JWT | Not executed | JWT persistence after deletion documented | Yes | Blocker |
| Logout | Not executed | Sign-out scopes documented | Yes | Blocker |
| Single-session revoke | Not executed | Session relationship documented | Yes | Blocker |
| Global/all-session revoke | Not executed | Scope documented | Yes | Blocker |
| Natural session expiry/cleanup | Not executed | Delayed cleanup documented | Yes | Blocker |
| Revoked session with valid JWT | Not executed | Behavior documented, exact lookup unproved | Yes | Blocker |
| Missing/replaced/concurrent session | Not executed | Partial session docs only | Yes | Blocker |
| Password/credential change | Not executed | Session termination candidate only | Yes | Blocker |
| Deterministic status version sensitivity | Not executed; no real projection | No | Yes | Blocker |
| Account recreation with same email | Not executed | No; email must never join | Yes | Blocker |
| Binding tombstone | Not executed; app domain absent | No | Yes | Blocker |
| Export/project migration | Not executed | Procedure documented, identity/race result unproved | Yes for migration readiness | Blocker |
| Key rotation overlap | Not executed | Key lifecycle documented | Yes | Blocker |
| Unknown key/JWKS outage | Not executed | Cache rules documented | Yes | Blocker |
| Emergency key revocation | Not executed | Cache caveat documented | Yes | Blocker |
| Provider/status endpoint outage | Not executed | No | Yes | Blocker |
| Webhook delay/drop/duplicate/reorder | Not executed | No configured webhook | Yes | Blocker |
| Rate limit | Not executed | No | Yes | Blocker |
| Clock skew | Not executed | No | Yes | Blocker |
| Concurrent revocation and approval | Not executed | No | Yes | Blocker |
| Unknown provider schema/version | Not executed | Fail-closed rule only | Yes | Blocker |
| Rollback/export rehearsal | Not executed | No | Yes | Blocker |

The fixture catalogue is not partially satisfied by the 106 M33.8 tests:
those tests consume caller-supplied facts and intentionally make no claim about
the provider's ability to produce them.

## 18. Unresolved gaps

Every empirical gap listed below remains unresolved:

1. exact direct password authentication occurrence and freshness;
2. exact password-plus-TOTP method and non-recovery classification;
3. refresh/continuation preserving original authentication age;
4. server-current active, banned, deleted, and unknown user mapping;
5. exact session-row current/revoked/expired/missing semantics;
6. current JWT surviving logout/deletion while current checks refuse;
7. complete security-relevant user/factor/session projection;
8. deterministic status-version sensitivity to password, factor, recovery,
   and session changes;
9. provider mutation propagation and revocation/approval race bounds;
10. key rotation, emergency revocation, cache, and outage behavior;
11. webhook/cache negative-only behavior;
12. account deletion/recreation, tombstone, export, and migration behavior;
13. provider-neutral adapter mapping with unknown-schema refusal;
14. named identity/security/operations/retention/privacy owners; and
15. acceptance of the operational outage and propagation model.

Any one mandatory gap is sufficient to stop. Collectively they leave no basis
for implementation design.

## 19. Readiness decision

**Decision: `STOP_M33_RUNTIME`.**

`IMPLEMENTATION_DESIGN_READY` is false because:

1. no approved non-production Supabase configuration existed;
2. no local Supabase/container runtime existed;
3. zero mandatory provider fixtures were executed;
4. no direct-human non-recovery path was mapped empirically to an existing
   M33.8 assurance class;
5. current user and exact session status were not observed synchronously;
6. disabled/deleted/revoked behavior against still-valid JWTs was not proved;
7. no complete deterministic credential-security revision was proved;
8. propagation, race, key, schema, outage, cache, and webhook behavior remain
   unmeasured;
9. no provider-neutral adapter output was exercised against M33.8; and
10. operational/privacy/retention owners have not accepted the boundary.

The stop decision has these exact effects:

- retain M33.1-M33.8 as pure, non-adopted foundations;
- do not implement prospective M33 human approval runtime;
- do not add identity, authorization, review, intent, lifecycle, or approval
  persistence for this path;
- do not investigate or recommend a third provider absent a new externally
  imposed requirement that creates a new architecture decision;
- do not attribute legacy activity to future or synthetic actors;
- keep current product behavior outside M33 approval authority;
- do not weaken M33.8 to accept provider facts that were not proved; and
- keep M32 closed and canonical execution planning NO-GO.

This is terminal for the currently approved M33 runtime-discovery sequence.
There is no recommended M33.12 provider milestone. A future external
regulatory, contractual, or relying-party requirement could authorize a new
program with an actual owned test environment, but it would not retroactively
change this result.

## 20. Validation performed

Validation for this documentation-only stop decision includes:

- unchanged M33.8 suite: **106 passed**;
- provider POC tests: **0 executed**, correctly reported as blocked rather
  than passed;
- negative provider fixtures: **not executed**; mandatory blocker;
- deterministic provider-status hash fixtures: **not executed**; mandatory
  blocker;
- provider dependency/import leakage scan: no Supabase dependency or type in
  production M33 code;
- repository secret scan over changed content and provider-key patterns;
- personal-data scan over changed content;
- `git diff --check`;
- trailing-whitespace and tab checks;
- Markdown heading hierarchy and balanced fence checks;
- required-section checklist;
- readiness-decision consistency check; and
- changed-file scope review.

The M33.8 test run emitted one pytest cache warning because the sandbox could
not create `.pytest_cache`; it did not affect the 106 passing tests.

## 21. Decision Log rationale

A Decision Log entry is required because `STOP_M33_RUNTIME` is the final
readiness decision for the bounded provider-feasibility sequence and governs
whether the pure M33 foundation may proceed to adoption. No additional
provider-specific architecture is adopted.

## 22. Explicit non-production and non-adoption statement

M33.11 does not:

- create a Supabase organization, project, branch, database, user, session,
  identity, password, factor, recovery flow, key, webhook, or API request;
- install a Supabase SDK, CLI, Docker image, container, dependency, or local
  service;
- create or retain an access token, refresh token, cookie, password, MFA
  secret/code, recovery code, service key, private key, email, phone, or
  personal name;
- add an empirical evidence directory containing simulated provider data;
- modify Python, TypeScript, tests, dependencies, environment values,
  `backend/auth.py`, login, token issuance/storage, middleware, CORS, or
  frontend behavior;
- add an ORM model, migration, repository, identity/session/grant store, API,
  endpoint, frontend, writer, scheduler, or runtime adapter;
- design or implement production `auth.users`/`auth.sessions` integration,
  application actors, provider bindings, workspace membership, portfolio
  grants, or authorization facts;
- modify M33.2, M33.5, M33.7, or M33.8 contracts or tests;
- create an execution intent, snapshot, display receipt, approval command,
  lifecycle event, audit receipt, certificate, proposal, or quarantine row;
- attribute, adapt, backfill, dual-write, repair, rank, or mutate historical
  data;
- change recommendation, optimizer, decision, expiry, shadow, transaction,
  portfolio, ledger, evaluation, or replay behavior;
- change Graphify output;
- compare or recommend a third identity provider;
- reopen M32 or adopt canonical execution planning; or
- change any production behavior.
