# M33.10 - Managed Identity Claim, Current-Status, and Revocation Proof of Concept

**Date:** 2026-07-17

**Status:** Complete. Isolated documentary proof-of-concept and provider
capability assessment only. No provider tenant, synthetic account, SDK,
secret, login change, runtime adapter, authorization store, or M33 persistence
is created.

**Milestone decision:** Clerk's documented identity, session, reverification,
user-status, and JWKS primitives can seed a provider-neutral adapter, but they
do **not** prove every fact required by M33.8. In particular, Clerk does not
document a forever-stable subject across deletion or tenant/provider
migration, an approval-grade monotonic credential-security revision, or an
unambiguous server-verifiable authentication-method record for every password,
MFA, passkey, recovery, and step-up path. The prohibition on creating a tenant,
accounts, or secrets also prevents empirical closure of those gaps. Supabase
Auth exposes richer authentication-method timestamps and inspectable session
identity, but it likewise requires a separate empirical proof and does not
close every gap on documentary evidence alone. Readiness is therefore
**`ALTERNATE_PROVIDER_REQUIRED`**, not `IMPLEMENTATION_DESIGN_READY`.

M33 actor identity is refined to an application-owned, non-reassignable opaque
id. Provider `(configuration, issuer, subject)` is a replaceable identity
binding to that actor, not the permanent `ActorRef.actor_id`. A deleted,
merged, or migrated provider account never causes historical actor identity to
be rewritten or inferred by email.

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
- the M33 entries in `docs/engineering/DECISION_LOG.md`.

All predecessor boundaries remain in force:

- M32 remains closed and canonical execution planning remains NO-GO.
- M33.8 contracts and `validate_human_authority()` are unchanged. Provider
  limitations are not repaired by weakening actor, current-status, scope,
  time, assurance, or fail-closed semantics.
- A signed JWT proves only the claims and validity interval in that JWT. It
  does not prove current user, credential, session, or application-grant state.
- Identity and authorization facts do not create an execution-intent snapshot,
  approval, lifecycle event, transaction, fulfillment fact, or portfolio
  mutation.
- Provider organization roles, email, username, display name, request IP,
  current owner, and the legacy shared credential are never human authority.
- Application workspace and portfolio authorization remains outside Clerk,
  Supabase, and M33.
- No provider-specific type may enter M33.8, M33.7, M33.2, an execution intent,
  or a future approval command.

The word **proof** in this report is bounded by the milestone's prohibitions.
Official contract documentation and repository inspection were available;
live provider behavior was not. Any claim requiring a configured tenant,
synthetic user, secret, network trace, timing measurement, account mutation,
or provider support commitment remains explicitly unproven.

## 2. Method and evidence limits

The study used three evidence classes:

1. repository source and configuration names, inspected read-only;
2. frozen M33.8 source contracts and tests; and
3. current official Clerk and Supabase documentation reviewed on 2026-07-17.

It did not create or access a provider tenant, account, session, key, secret,
webhook, passkey, MFA enrollment, or support ticket. It did not run an SDK or
send a provider request. Consequently:

- documented fields may be used to design candidate mappings;
- undocumented lifetime, ordering, propagation, and non-reuse properties are
  `UNKNOWN`, never assumed;
- provider marketing or client UI behavior is not server authority;
- an empirical pass criterion is not marked passed from documentation alone;
  and
- inability to observe current truth always becomes an M33.8 refusal.

This is the strongest honest outcome possible under the requested non-mutating
scope. It is sufficient to reject implementation readiness and specify exact
exit evidence, but not to certify a provider.

## 3. Repository and deployment consistency

The read-only inspection reconfirmed M33.9's repository findings:

- `backend/auth.py` compares one environment username/password pair, issues a
  30-day HS256 JWT under a source-code secret, and exposes only boolean
  `verify_token()` output.
- `backend/main.py` middleware discards subject/session context and uses
  `_ws_id()` to select one default workspace.
- `frontend/lib/auth.ts` retains the bearer token in `localStorage`;
  `frontend/lib/api.ts` sends it to the separately addressed FastAPI backend.
- `Workspace` and `Portfolio` have no account, membership, role, permission,
  session, or grant relationship.
- the repository has no identity/security dependency-injection boundary or
  provider adapter.
- the deployment remains a Next.js/Vercel frontend and a FastAPI/PostgreSQL
  backend run under PM2 on a VPS, with the backend bound to
  `127.0.0.1:8000`; no reverse-proxy identity policy is retained in source.
- environment configuration names include current application credentials
  and URLs, but no Clerk or Supabase production identity configuration was
  found or inspected by value.

Nothing in the current runtime can populate an accepted M33.8 result. The
shared credential remains structurally ineligible and no historical request
may be attributed to a future actor.

## 4. Official provider evidence used

### 4.1 Clerk

The assessment relies on these official sources:

- [Session-token claims](https://clerk.com/docs/guides/sessions/session-tokens)
  document V2 `iss`, `sub`, `sid`, `jti`, `fva`, `iat`, `nbf`, `exp`, `azp`,
  and session-status claims.
- [Manual JWT verification](https://clerk.com/docs/guides/sessions/manual-jwt-verification)
  requires signature, algorithm, time, and authorized-party validation and
  documents JWKS/public-key verification.
- [Backend User object](https://clerk.com/docs/reference/backend/types/backend-user)
  exposes a unique user id, `banned`, `locked`, factor-presence flags,
  creation/update times, and optional external id.
- [Backend Session object](https://clerk.com/docs/reference/backend/types/backend-session)
  exposes unique session id, user id, state, actor/impersonation data,
  creation/update/activity times, and explicit expiry/abandon times.
- [Session status](https://clerk.com/docs/reference/types/session-status)
  defines active and inactive states including ended, expired, removed,
  replaced, and revoked.
- [Reverification](https://clerk.com/docs/guides/secure/reverification)
  documents factor age, a unique optional `reverification_id`, supported
  factors, server freshness checks, and graceful downgrade behavior.
- [Sign-in options](https://clerk.com/docs/guides/configure/auth-strategies/sign-up-sign-in-options)
  documents passkey and MFA behavior.
- [Session revocation](https://clerk.com/docs/reference/backend/sessions/revoke-session)
  documents explicit session revocation.
- [Webhooks](https://clerk.com/docs/guides/development/webhooks/overview)
  state that delivery is asynchronous and not guaranteed to be immediate or
  delivered at all.
- [Migration](https://clerk.com/docs/guides/development/migrating/overview)
  documents import/export and use of an external id, while also stating that
  development instances cannot be migrated to production instances.
- [How Clerk works](https://clerk.com/docs/guides/how-clerk-works/overview)
  explains short-lived session tokens and automatic refresh.
- [Backend API limits](https://clerk.com/docs/guides/how-clerk-works/system-limits)
  document rate limiting of Backend API calls.

### 4.2 Supabase comparison

Because Clerk failed mandatory proof, the requested Supabase comparison was
triggered. It uses:

- [JWT claims](https://supabase.com/docs/guides/auth/jwt-fields), including
  issuer, UUID subject, session id, AAL, and timestamped AMR entries;
- [User sessions](https://supabase.com/docs/guides/auth/sessions), including
  the session-row relationship and termination behavior;
- [Server user retrieval](https://supabase.com/docs/reference/python/auth-getuser),
  including database-backed retrieval and banned/deleted fields;
- [Sign out](https://supabase.com/docs/guides/auth/signout), which documents
  that revoked-session access tokens remain cryptographically valid until
  expiry;
- [User management](https://supabase.com/docs/guides/auth/managing-user-data),
  which documents export and the fact that user deletion alone does not
  immediately invalidate an issued JWT;
- [MFA](https://supabase.com/docs/guides/auth/auth-mfa), which exposes
  authenticator-assurance state and factor listing;
- [Passkeys](https://supabase.com/docs/guides/auth/passkeys), currently marked
  experimental;
- [Signing keys](https://supabase.com/docs/guides/auth/signing-keys), including
  rotation and multi-layer JWKS-cache caveats; and
- [Auth-schema migration](https://supabase.com/docs/guides/troubleshooting/migrating-auth-users-between-supabase-projects),
  which can preserve database users but changes token trust unless signing
  material and migration are coordinated.

## 5. Stable identity result

### 5.1 What Clerk proves

For one configured Clerk instance and an extant user, a verified V2 session
token supplies exact `iss` and `sub`; the Backend User response supplies the
same unique user id. That pair is suitable for a **provider binding key**:

```text
(provider_configuration_id, canonical_issuer, provider_subject)
```

The token also supplies `sid`, allowing the binding to be checked against the
exact Backend Session user id. Email, username, external account, and display
attributes are unnecessary and must not be identity keys.

### 5.2 What Clerk does not prove

The reviewed documentation does not promise that a Clerk user id:

- is globally unique outside its instance namespace;
- is never reused forever after hard deletion;
- survives development-to-production movement (which Clerk says is not a user
  migration path);
- remains the same after export/import to a new Clerk instance;
- remains the same after migration to another provider;
- can be selected as the surviving id when two actual Clerk users are merged;
  or
- constitutes a durable tombstone after provider deletion.

Account linking may attach additional external accounts to one Clerk user, but
email-based linking is not proof that two application actors are the same.
Hard deletion removes the provider user; a later lookup failure proves current
absence, not permanent non-reuse.

### 5.3 Permanent `ActorRef` decision

`ActorRef.actor_id` must therefore be an application-owned, caller-supplied,
non-reassignable opaque id created by the Application Identity/Authorization
domain. Clerk supplies a binding, not that id:

```text
ActorRef.actor_id                 = application stable actor id
ActorRef.authority_namespace      = application environment/tenant namespace
ActorRef.identity_provider_ref    = versioned provider-configuration reference

ProviderActorBinding
  application_actor_id
  provider_configuration_id
  canonical_issuer
  provider_subject
  binding_revision
  status: ACTIVE | DISABLED | DELETED | SUPERSEDED | UNKNOWN
```

The conceptual `ProviderActorBinding` remains outside M33.8 and is not
implemented here. Its effects are:

- provider deletion tombstones the binding and marks the application actor
  ineligible; it never deletes or reuses the actor id;
- a new provider account receives a new binding and is never joined by email;
- an approved account merge requires explicit identity-owner evidence and
  preserves both old bindings; it does not merge historical `ActorRef`s;
- tenant/provider migration creates a new binding under a new provider
  configuration and retains the old binding as historical evidence;
- unresolved merge/migration state is `UNKNOWN` and blocks approval; and
- existing shared-credential history remains unattributed.

This keeps M33.8 provider-neutral and makes actor identity stable for the audit
retention period even when the provider is replaced.

## 6. Authentication receipt semantics

### 6.1 Required provider-neutral receipt

`AuthenticationEventRef.authentication_event_id` remains an
application-created opaque receipt id. A receipt is eligible only after one
server-side adapter evaluation proves:

1. supported token/provider/API contract versions;
2. signature, algorithm, issuer, authorized party/audience, `nbf`, and `exp`;
3. human session-token type rather than machine/API-key type;
4. exact provider binding from verified `iss` and `sub`;
5. exact `sid` whose Backend Session is active, belongs to `sub`, and carries
   no actor/impersonation claim;
6. an allowed, recent authentication ceremony with authoritative occurrence
   time and sufficient assurance;
7. current Backend User and Session status;
8. the deterministic status version in section 9;
9. application-owned UTC receipt time and explicit expiry; and
10. no shared, delegated, impersonated, recovery, ambiguous, or unknown path.

The receipt retains only ids, canonical classifications, UTC times, source
object revisions, and hashes. It never retains a token, cookie, password,
passkey assertion, MFA code, recovery code, secret key, or refresh token.

### 6.2 Event matrix

| Provider/user event | New `AuthenticationEventRef`? | Rule |
| --- | --- | --- |
| Initial login | Conditional | Yes only when exact factor/assurance and UTC occurrence can be proved and current status passes. A session alone is insufficient. |
| Password login | Unproven for Clerk | `fva` proves recent first-factor verification but not, by itself, that the factor was password. No `PASSWORD` mapping without exact server proof. |
| Password plus MFA login | Unproven for Clerk | Both factor ages can show freshness, but graceful downgrade and recovery-factor ambiguity must be excluded. |
| Passkey login | Unproven for Clerk | Clerk describes passkey MFA semantics, but reviewed server facts do not establish an approval-grade exact ceremony/method binding. Never map a synced passkey to `HARDWARE_BOUND`. |
| Explicit step-up/reverification | Candidate yes | Requires a new unique `reverification_id`, acceptable factor evidence, freshness, exact target binding policy, and successful current-status checks. Reused id is refused. |
| Session-token refresh | No | New `jti`/`iat`/`exp` is transport renewal, not a human ceremony. Authentication age does not reset. |
| Session continuation/touch | No | Activity or a remembered session is not authentication. |
| Browser/device reload | No | It may require a new display receipt later, not a new identity event. |
| MFA/passkey enrollment | No | Credential configuration changes invalidate the prior status version and require a later qualifying authentication act. |
| Password reset/account recovery | No | Recovery is not approval assurance. Invalidate prior receipt and require a distinct non-recovery authentication. |
| Session switch | No automatic event | The new session must independently satisfy the complete receipt boundary. |
| Account link/merge/migration | No | Resolve provider binding first, then require fresh direct authentication. |

### 6.3 Why Clerk is not proved

Clerk's reverification documentation provides a useful unique
`reverification_id` and factor ages, but also documents:

- supported reverification factors do not include every configured login
  method in one stable server grammar;
- a requested second/multi-factor level can downgrade when no second factor
  is available;
- backup code is a supported second-factor/recovery route;
- passkey behavior and generic reverification behavior are not documented as
  one immutable backend receipt; and
- factor age is minute-granularity relative evidence, not the exact original
  ceremony record retained by this application.

An isolated tenant could potentially prove a safe subset, such as a unique
strict reverification with an allowed non-recovery factor. This milestone was
not authorized to run that test, so the mapping remains `UNKNOWN`.

## 7. Current actor, credential, and session status

### 7.1 Required acceptance query

JWT verification is only the first gate. Every approval attempt must also
obtain, synchronously and for the exact `sub`/`sid`:

- the provider user or an authoritative not-found/deleted result;
- user `banned` and `locked` state;
- relevant credential/factor configuration under the approved grammar;
- the exact Backend Session or an authoritative not-found result;
- session `status`, user id, actor/impersonation data, expiry, and abandon
  time; and
- the active application provider binding and its revision.

The adapter maps to M33.8 only as follows:

| Source conclusion | M33.8 field |
| --- | --- |
| User exists, binding active, not banned/locked | `ActorLifecycleStatus.ACTIVE` |
| User banned, binding disabled, or locked under approval policy | `DISABLED` |
| Authoritative user deletion/tombstone | `DELETED` |
| Timeout, rate limit, server error, malformed response, conflict, or ambiguous not-found | `UNKNOWN` |
| Exact session state `active`, unexpired, direct subject | `SessionStatus.ACTIVE` |
| Ended/expired/removed/replaced/revoked/absent session | `SessionStatus.REVOKED` only when authoritative; otherwise `UNKNOWN` |
| Complete approved security projection unchanged | `CredentialStatus.ACTIVE` |
| Explicit credential/security revocation under the grammar | `CredentialStatus.REVOKED` |
| Missing factor inventory/version, unsupported state, or provider outage | `CredentialStatus.UNKNOWN` |

### 7.2 Credential gap

Clerk's Backend User exposes useful booleans and `updatedAt`, but the reviewed
contract does not provide one documented monotonic credential-security
revision, one list/version covering every password, passkey, recovery, OAuth,
MFA, and compromise state, or one event sequence that proves no relevant
credential change was omitted. `updatedAt` may be used as a conservative
invalidator, but the documentation does not guarantee that it is a complete
security revision or that every security change changes it exactly once.

Therefore `CredentialStatus.ACTIVE` and a matching
`credential_status_version` cannot yet be produced honestly for approval.
Returning `UNKNOWN` is required until the exit fixtures prove the projection.

## 8. Revocation and maximum-failure window

### 8.1 Revocation paths

| Path | Cryptographic/JWT effect | Required approval behavior |
| --- | --- | --- |
| Administrator bans/disables user | A previously issued token may still verify locally until expiry; provider behavior must be measured | Synchronous user/status query must refuse on observed ban/disable. Outage or ambiguity is `UNKNOWN`. |
| User is locked | Locking blocks sign-in; active-session effect is not assumed | Approval policy treats `locked=true` as disabled regardless of local JWT validity. |
| User logs out | Session becomes inactive/ended/removed; an already issued token may remain parseable | Exact session query must return non-active/absent and refuse. |
| Session explicitly revoked | Clerk exposes a revoke operation and revoked session state | Exact session query must refuse. Webhook/cache is not authority. |
| Session expires/abandons | Provider supplies expiry/abandon instants | Authority-server UTC comparison refuses at the boundary even before provider cleanup. |
| Token expires | `exp` invalidates that token | Reject before current-status construction. A refreshed token is not new authentication. |
| Password/credential changed | Session impact depends on provider operation/configuration | Status-version mismatch or unknown credential projection refuses. No assumption from password presence. |
| MFA/passkey removed/reset | May not invalidate every active session automatically | Status-version mismatch must refuse; if the provider cannot expose it, status is `UNKNOWN`. |
| User hard-deleted | Provider user lookup becomes absent; existing token behavior is not trusted | Tombstone application binding; refuse as `DELETED` or `UNKNOWN` until authoritative. |
| Signing key rotated normally | Old and new trust may overlap intentionally | Verify exact `kid` under configured trust. Rotation alone is not user revocation. |
| Signing key compromised/revoked | Cached keys can outlive control-plane change | Approval requires current trusted-key policy and synchronous provider status. Unknown key/trust state refuses. |
| Provider unavailable/rate-limited | Local JWT may still verify | `UNKNOWN`; no approval. |
| Webhook delayed/missing/reordered | Local projection may be stale | Webhook only shortens validity or triggers invalidation; it never proves active/current state. |

### 8.2 Maximum permitted window

M33 permits **zero application-granted revocation grace for approval**. The
first approval attempt after a revocation must perform current checks; a
cached JWT or webhook projection cannot extend authority.

That does not prove zero end-to-end provider propagation latency. The actual
upper bound is:

```text
provider control-plane propagation
+ synchronous user/session read latency
+ local authority transaction duration
```

Clerk's reviewed documentation does not specify a maximum for the first term.
Consequently no numerical maximum is claimed. Implementation readiness
requires a measured and contractually acceptable bound. Until then, any state
that cannot be confirmed at the approval boundary is `UNKNOWN` and refuses.

A future policy may use a very short M33.8 `ActorStatusFact.valid_until`, but
that TTL cannot convert stale provider truth into current truth. It only limits
reuse between the successful check and command commit.

## 9. Deterministic `credential_status_version` grammar

### 9.1 Purpose

The version binds an authentication receipt to the security-relevant provider
and application facts observed at that receipt. Recomputing the same grammar
at approval must yield the identical value. A difference forces
`CREDENTIAL_STATUS_VERSION_MISMATCH`; missing or incomplete input produces
`CREDENTIAL_STATUS_UNKNOWN`, not a best-effort version.

### 9.2 Candidate Clerk grammar

The provider-neutral envelope is:

```text
credential_status_version =
  "identity-status-v1:sha256:" + lowercase_hex(
    SHA-256(
      "M33.10:identity-security-state:1\n" + canonical_utf8_payload
    )
  )
```

The explicit canonical payload contains:

- adapter contract version and provider API/claims versions;
- application authority namespace and provider-configuration id;
- application actor id and actor-binding revision/status;
- canonical issuer and provider subject;
- provider user id, creation time, provider `updatedAt`, `banned`, `locked`,
  password-enabled, TOTP-enabled, two-factor-enabled, and backup-code-enabled;
- a complete provider-supported credential/factor inventory digest when such
  an authoritative inventory is available;
- exact provider session id/user id, normalized security status, creation,
  expiry, and abandon times;
- normalized direct/delegated/impersonated classification, without raw actor
  payload;
- assurance-policy version and provider security-configuration version; and
- explicit `PRESENT`, `ABSENT`, or `UNKNOWN` markers for every optional
  security field.

Rules:

- explicit dictionaries and field lists only;
- sorted JSON keys, compact separators, canonical UTC instants, and lowercase
  SHA-256 output;
- no generic object reflection;
- no volatile `lastActiveAt`, access-token `jti`, token `iat`/`exp`, request
  time, profile text, email, username, display name, IP, or user agent;
- no password, token, cookie, code, passkey assertion, refresh token, provider
  secret, or private key; and
- no version when a required field is unavailable or semantically unknown.

The exact token/session expiry remains in `AuthenticationEventRef.valid_until`
and the current session query. Excluding token renewal data prevents a routine
refresh from impersonating a new human authentication.

### 9.3 Why the grammar is not approved for Clerk

The syntax is deterministic, but its input completeness is unproved. Clerk's
documented Backend User does not expose a complete passkey/credential revision
inside the reviewed object, and `updatedAt` is not documented as a monotonic
security-only revision. A deterministic hash of incomplete facts would be
precisely repeatable and still dishonest. The grammar therefore remains an
exit-test candidate, not an implemented or approved adapter contract.

## 10. Assurance mapping

M33.8 currently recognizes `PASSWORD`, `MULTI_FACTOR`, `FEDERATED_HIGH`, and
`HARDWARE_BOUND`. Provider labels map only after server-verifiable evidence,
not from UI selection or client assertions.

| Authentication path | Candidate M33.8 class | M33.10 result |
| --- | --- | --- |
| Password login/reauth | `PASSWORD` | Unproved: recent first-factor age does not identify password by itself. |
| Password + TOTP/phone second factor | `MULTI_FACTOR` | Unproved: both factor ages help, but exact methods, downgrade, and recovery exclusion need proof. |
| Passkey | At most `MULTI_FACTOR`; never automatically `HARDWARE_BOUND` | Unproved: synced passkeys are not necessarily hardware-bound and approval-grade server ceremony evidence is not established. |
| Strict step-up | Class of exact completed factors | Candidate only with unique unused reverification id, exact non-downgraded level, allowed factors, and current status. |
| Remembered session/token refresh | None | Never a new event or assurance upgrade. |
| Recovery/backup code/password reset | None | Explicitly ineligible for approval receipt; require later non-recovery authentication. |
| Federated sign-in | `FEDERATED_HIGH` only under a separately approved issuer/ACR/AMR policy | No current mapping; generic OAuth is insufficient. |

No assurance class is accepted from Clerk on documentary evidence alone. This
does not mean the provider can never qualify; it means the exact supported
subset must be demonstrated with server evidence and downgrade/recovery
negative fixtures.

## 11. Outage and uncertainty matrix

`ALLOW` below means only that the identity-status gate may proceed to M33.8
and application authorization. It never means approval itself is accepted.

| Condition | Identity gate | Reason |
| --- | --- | --- |
| Token valid; user/session/status calls succeed; all exact facts pass | `ALLOW` candidate | Only complete current facts may reach M33.8. This case is not yet proved for Clerk. |
| Provider unavailable | `UNKNOWN` -> deny approval | Current actor/credential/session truth is unavailable. |
| Network unavailable/timeout/TLS failure | `UNKNOWN` -> deny approval | A local JWT cannot replace current status. |
| JWKS unavailable, known cached/pinned key and status APIs available | Conditional token verification only | May authenticate transport under a bounded key policy; still requires current status. |
| JWKS unavailable and token has unknown `kid` | `UNKNOWN` -> deny approval | Trust cannot be established. |
| Current-status user endpoint unavailable | `UNKNOWN` -> deny approval | Ban/delete/credential state cannot be known. |
| Exact session endpoint unavailable | `UNKNOWN` -> deny approval | Revocation/expiry/current session cannot be known. |
| Backend API rate limited | `UNKNOWN` -> deny approval | `Retry-After` is operational metadata, not authority. |
| Webhook current and status APIs succeed | Use synchronous facts | Webhook may correlate/invalidate but does not upgrade truth. |
| Webhook delayed, missing, duplicated, or reordered | Ignore for positive authority | Official docs describe asynchronous, non-guaranteed delivery. |
| Local status cache inside freshness window | Insufficient for approval | Cache may only deny early; it cannot assert current `ACTIVE`. |
| Token expired/not-yet-valid/issuer/azp mismatch | `DENY` | Cryptographic/request binding failed before status evaluation. |
| Provider and authority clocks within approved skew | Continue | Times remain server-owned UTC and are checked explicitly. |
| Clock skew exceeds policy or provider times are inconsistent | `UNKNOWN` -> deny approval | Expiry, freshness, and ordering cannot be trusted. |
| User or session response malformed/unknown version | `UNKNOWN` -> deny approval | Fail closed on schema/semantic change. |
| Provider says active but application binding/grant is disabled | `DENY` | Provider identity cannot override application authority. |

Read-only product behavior may have a separate bounded local-JWT policy, as
M33.9 allowed. It must never be reused for M33 approval.

## 12. Provider-neutral adapter boundary

All provider objects terminate inside an Authentication/Authorization-domain
adapter:

```text
Clerk/Supabase token + provider API responses
                  |
                  v
provider-specific verifier and status adapter
                  |
                  +--> provider binding/status audit (outside M33)
                  |
                  v
provider-neutral identity source result
                  |
                  v
ActorRef + AuthenticationEventRef + ActorStatusFact
                  |
                  v
unchanged M33.8 validate_human_authority()
                  |
                  v
later M33.7 command boundary
```

The neutral source result must contain only:

- application actor/provider-binding references;
- exact source namespace and source ids;
- direct/shared/delegated/impersonated classification;
- normalized user, credential, and session status;
- exact UTC event/check/expiry times;
- normalized assurance class and source evidence reference;
- status-version string and adapter/policy versions; and
- typed `ACTIVE`, `REVOKED`, `DELETED`, `DENIED`, or `UNKNOWN` outcomes.

Clerk `User`, `Session`, token claims, SDK errors, webhook payloads, and ids do
not appear in M33 modules. Supabase `User`, `Session`, `AAL`, `AMR`, auth-schema
rows, SDK errors, and project ids receive the same treatment.

## 13. Supabase comparison

Clerk fails three mandatory proof areas: permanent provider-subject identity,
complete credential-status version, and unambiguous assurance evidence.
Supabase was assessed only against those gaps.

| Requirement | Clerk documentary result | Supabase documentary result | Conclusion |
| --- | --- | --- | --- |
| Stable subject | Unique instance user id, no forever non-reuse/migration promise | UUID subject; auth-schema export/import may preserve ids | Supabase is stronger for controlled migration, but application actor id is still required. |
| Recent authentication | `fva` plus optional unique reverification id | timestamped `amr` entries and `aal` | Supabase is semantically richer for method/time, but exact reauth/event uniqueness still needs proof. |
| Assurance | Factor ages; downgrade/recovery/passkey ambiguity | explicit AAL/AMR including `password`, `totp`, and `recovery` | Supabase better distinguishes recovery; passkey is experimental and exact M33 mapping remains unproved. |
| Current user status | Backend user with banned/locked/update state | database-backed `getUser()` with banned/deleted fields | Both can contribute, neither replaces an empirical propagation/outage test. |
| Current session status | Backend Session with explicit state | JWT `session_id` can be checked against `auth.sessions`; missing row indicates logout | Supabase offers an inspectable row, but hosted access/cleanup/race behavior needs proof. |
| Credential revision | No documented complete security revision | User/session database revisions may be projected | Supabase may support a stronger grammar, but no reviewed contract guarantees complete credential change coverage. |
| Revoked JWT | Short-lived token limits exposure; current session still must be queried | Docs explicitly say revoked-session/deleted-user JWTs can remain valid until expiry | Both require a current server/database check for approval. |
| Key rotation | JWKS/public-key verification; exact emergency-cache behavior needs test | Documented overlapping keys and up-to-20-minute multi-level cache caveat | Supabase is more explicit, not automatically stricter. |
| Operational fit | Managed identity separate from application PostgreSQL | Managed Auth is coupled to a Supabase project/auth schema | Both add external operations; Supabase may enlarge platform coupling. |

Supabase is a credible alternate POC target because its AMR timestamps and
session-row semantics directly address Clerk's weakest areas. It is not
selected for implementation. Its passkey feature is experimental, deletion
does not itself invalidate issued JWTs, and the actual current-status/status-
revision boundary remains untested.

## 14. Exact exit-evidence catalogue

Every fixture uses synthetic identities in a separately approved
non-production environment. Pass requires retained, sanitized evidence of
provider request/response classifications, server UTC times, adapter output,
and unchanged M33.8 validation. Secrets and raw tokens must not be retained.

| Fixture | Pass criteria | Fail criteria | Required retained evidence |
| --- | --- | --- | --- |
| Synthetic individual login | One stable application actor binding; exact provider subject/session; direct individual mode; eligible receipt | Shared/machine/ambiguous subject or client-only assertion | Sanitized claim projection, provider user/session projections, binding and M33.8 result |
| Password reauthentication | Server proves password method, exact occurrence/freshness, unique event | Only generic first-factor age or client-selected method | Method/event reference, UTC time, assurance mapping, negative altered-token fixture |
| Password + MFA | Exact two allowed factors, no downgrade/recovery, unique step-up | Downgrade, backup/recovery ambiguity, or missing method | Factor methods/times, unique event id, strict-level result, negative downgrade/recovery traces |
| Passkey authentication | Exact WebAuthn/passkey ceremony; safe `MULTI_FACTOR` mapping; no hardware-bound overclaim | Method unavailable, synced credential called hardware-bound, or beta instability | Provider server event/method, RP config/version, assurance result |
| Remembered-session refresh | No new authentication event and original auth age retained | Refresh resets age or creates receipt | Before/after token projections and unchanged receipt id/time |
| Synthetic disable/ban | Next approval status query refuses despite locally valid token | Cached JWT or delayed webhook permits approval | Admin mutation time, provider observation time, sanitized query result, refusal |
| Synthetic lock | Locked actor is refused for approval | Active session bypasses lock policy | User state and refusal |
| Synthetic logout | Exact session becomes non-active/absent and approval refuses | Token validity permits approval | Logout time, session query result, refusal |
| Synthetic session revoke | Exact session query observes revoke and refuses | Another session or cache is substituted | Session id/status transition and refusal |
| Synthetic session expiry | Server UTC refuses at `expireAt`/`abandonAt`, independent of cleanup | Provider row cleanup delay extends authority | Boundary times and before/at/after results |
| Synthetic credential change | Status version changes and old receipt refuses | Security change leaves version equal | Before/after canonical security projections and hashes |
| Synthetic MFA/passkey removal | Old receipt invalidated or status becomes unknown/revoked | Removed factor remains approval-authoritative | Factor inventory/revision evidence and mismatch refusal |
| Synthetic account recovery | Recovery path cannot create eligible approval receipt | Recovery/backup factor maps to allowed approval assurance | AMR/method evidence and refusal; later clean reauth acceptance |
| Synthetic account deletion | Binding tombstoned; old actor retained audit-only; token cannot approve | Actor id deleted/reused or email-based recreation inherits authority | Provider delete result, tombstone, old/new binding results |
| Synthetic account recreation | New provider subject does not inherit old actor/grants automatically | Email match restores authority | Old/new provider ids, separate binding decision, refusal |
| Synthetic account merge | No heuristic merge; explicit owner evidence preserves lineage | Provider/email survivor silently rewrites actor | Both source bindings, approved lineage record, historical-id invariance |
| Synthetic tenant migration | New provider binding maps explicitly to same application actor; old binding retained | Provider subject assumed stable or history rewritten | Export/import mapping, namespaces, dual proof, rollback result |
| Synthetic provider migration | New provider-specific objects stay inside new adapter | Clerk/Supabase type leaks into M33 | Neutral adapter snapshots and import/dependency scan |
| Synthetic key rotation | Old/new expected keys verify in intended overlap; unknown `kid` fail-closed; trust history retained | JWKS outage accepts unknown key or old trust outlives policy | Key ids, trust states, cache behavior, verification outcomes |
| Synthetic emergency key revoke | Measured cache purge meets approved bound; approval blocks during ambiguity | Cached compromised key plus status ambiguity permits approval | Revocation/observation times, cache purge evidence, refusal interval |
| Synthetic provider outage | Status calls yield `UNKNOWN`; zero approval events | Cached user/session/JWT yields `ACTIVE` | Injected outage, typed result, event-count proof |
| Synthetic status-endpoint outage | Only affected identity gate blocks; no partial active fact | User succeeds while session fails but adapter accepts | Per-call classifications and refusal precedence |
| Synthetic JWKS outage | Known-key policy behaves exactly; unknown key refuses | Any unknown trust is accepted | Cache state, `kid`, outage, verification result |
| Synthetic webhook delay/drop/reorder | Synchronous truth governs; webhook only invalidates early | Webhook cache supplies positive current status | Delivery schedule and synchronous comparison |
| Synthetic rate limit | `429` becomes `UNKNOWN` and approval refuses | Retry metadata treated as authority | Sanitized response classification and refusal |
| Synthetic clock skew | Within-policy behavior deterministic; beyond threshold refuses | Client time or unchecked provider time controls | Authority/provider clock readings and boundary fixtures |
| Synthetic concurrent revocation/approval | Defined transaction check detects stale fact or measured residual window is accepted by owner | Unbounded race or latest-timestamp heuristic | Ordered server/provider times, status revision, command outcome |
| Status-version determinism | Same security facts produce same version; every security-relevant change alters it; non-security profile change policy is explicit | Missing credential change, secret/token input, or nondeterministic output | Canonical fixtures, hashes, sensitivity matrix, secret scan |
| Unknown schema/version | Adapter returns `UNKNOWN` and M33.8 refuses | Permissive parsing/defaults | Future-field/unknown-version fixture and refusal |
| Export/rollback | Actor bindings/grants/audit references export and restore without provider secrets | Lost actor lineage or forced historical rewrite | Sanitized export manifest, restore comparison, rollback drill |

### 14.1 Exit decision rule

- **Implementation design ready:** every mandatory fixture passes for one
  selected provider; all M33.8 fields are populated without inference; the
  provider/current-status propagation bound and ownership are approved.
- **Alternate provider required:** a mandatory provider property is absent,
  undocumented, untestable, or fails, but the provider-neutral architecture
  remains viable with another provider.
- **Stop M33 runtime:** no acceptable provider/owner can produce stable
  individual actors, current status, assurance, and exact scoped authority
  without weakening M33.8.

Documentation examples, SDK type declarations, and successful JWT signature
verification are not fixture passes.

## 15. Readiness decision

**Decision: `ALTERNATE_PROVIDER_REQUIRED`.**

`IMPLEMENTATION_DESIGN_READY` is false because:

1. no authorized live synthetic Clerk environment was exercised;
2. Clerk subject permanence/non-reuse across deletion and migration is not
   documented strongly enough for permanent `ActorRef` identity;
3. a complete monotonic Clerk credential-security revision is unavailable;
4. exact password/MFA/passkey/recovery assurance mapping is unproved;
5. revocation/control-plane propagation has no measured upper bound here;
6. webhook/JWKS/outage/rate-limit behavior has not been exercised; and
7. application actor-binding and grant owners remain conceptual.

The result is not `STOP_M33_RUNTIME` because M33.8 remains provider-neutral,
an application-owned permanent actor id resolves the provider-lifetime issue,
and Supabase exposes candidate AMR/session primitives that justify one bounded
alternate proof. If the alternate cannot pass the same fixture catalogue,
the next result must be `STOP_M33_RUNTIME`, not a third round of weakened
requirements or indefinite provider shopping.

## 16. Relationship to M33.8 and predecessor decisions

M33.10 changes no M33.8 source contract or validator:

- `ActorRef` already accepts an opaque caller-supplied id and provider ref;
- `AuthenticationEventRef` already models caller-owned event identity, UTC
  validity, assurance, credential binding, and subject mode;
- `ActorStatusFact` already separates actor, credential, and session state;
- unknown, revoked, expired, mismatched, shared, delegated, and impersonated
  facts already fail closed;
- `credential_status_version` already accepts an external version string and
  checks exact equality; and
- no Clerk/Supabase value needs to be added to M33 enums.

The application-owned actor-id refinement supersedes only M33.9's candidate
field mapping that used provider `sub` directly as `ActorRef.actor_id`. It does
not weaken M33.8 and is recorded in the Decision Log because it is a concrete
identity-ownership decision.

M33.6-M33.7's direct prospective approval policy is unchanged. Historical
rows remain unattributed and non-authoritative. M32 remains closed.

## 17. Recommended next milestone

**M33.11 - Supabase Auth Security-State and Assurance Proof of Concept
(isolated, synthetic, non-production).**

M33.11 should be separately approved to create only the minimum non-production
tenant/test fixtures necessary to exercise Supabase's UUID subject, AMR/AAL,
session row, current user status, soft/hard deletion, revocation, key cache,
outage, migration, and deterministic security-revision behavior against the
section 14 catalogue.

It should end with exactly `IMPLEMENTATION_DESIGN_READY` or
`STOP_M33_RUNTIME`. It should not compare a third provider unless a concrete
external requirement names one. It should add no production account, secret,
login/token change, ORM, migration, application grant table, API, frontend,
runtime middleware, M33 persistence, approval endpoint, snapshot, transition,
certificate, legacy adapter, backfill, or Graphify change.

If creating even an isolated synthetic identity environment is not approved,
the correct next result is `STOP_M33_RUNTIME`; documentary research cannot
substitute indefinitely for required current-status evidence.

## 18. Explicit non-adoption statement

M33.10 does not:

- install Clerk, Supabase, or any SDK;
- create a provider account, application, tenant, project, user, session,
  passkey, MFA factor, key, secret, webhook, or network integration;
- modify Python, TypeScript, tests, dependencies, environment values, login,
  token issuance/storage, middleware, CORS, or dependency injection;
- add an ORM model, migration, repository, account/session/grant store, API,
  frontend, writer, scheduler, or runtime adapter;
- implement workspace membership, portfolio grants, authorization, identity
  receipts, current-status facts, or status-version code;
- modify M33.2, M33.5, M33.7, or M33.8 contracts or tests;
- create an intent, snapshot, display receipt, command, transition, audit
  receipt, certificate, proposal, or quarantine row;
- attribute, adapt, backfill, dual-write, repair, rank, or mutate historical
  rows;
- change recommendation, optimizer, decision, expiry, shadow, transaction,
  portfolio, ledger, evaluation, or replay behavior;
- change Graphify output;
- retain or expose a token, cookie, credential, password hash, secret, private
  key, recovery code, or personal display identity; or
- reopen M32 or adopt canonical execution planning.
