# M33.9 - Identity Authority Provider Selection and Integration Feasibility Study

**Date:** 2026-07-17

**Status:** Complete. Provider-selection, authorization-ownership, and
integration-feasibility study only. No identity provider, account, session,
grant, API, frontend, runtime, or M33 persistence is implemented.

**Milestone decision:** Select a **hybrid identity/authorization ownership
model**. A managed identity provider should own individual human accounts,
authentication, sessions, disablement, and recovery. An application-owned
Identity and Authorization domain should own workspace membership, direct
portfolio grants, explicit workspace-to-portfolio inheritance, resource
status, authorization policy, and point-in-time authority facts. M33 consumes
only the M33.8 facts and hashes produced at that boundary. Clerk is the
smallest first proof-of-concept target; Supabase Auth is the managed alternate;
Keycloak is appropriate only if a confirmed self-hosting or control
requirement justifies its operational cost. Readiness is
**`PROVIDER_PROOF_OF_CONCEPT_REQUIRED`**. No production provider is adopted by
this document.

## 1. Authoritative boundary

The governing inputs are:

- `docs/implementation/M33_1_execution_intent_snapshot_lifecycle_foundation.md`;
- `docs/implementation/M33_2_pure_execution_intent_contracts.md`;
- `docs/implementation/M33_3_legacy_adapter_feasibility.md`;
- `docs/implementation/M33_4_historical_authority_certification_contract.md`;
- `docs/implementation/M33_5_pure_authority_verification_contracts.md`;
- `docs/implementation/M33_6_authority_evidence_availability_and_issuer_governance.md`;
- `docs/implementation/M33_7_prospective_human_authority_and_direct_approval_capture_design.md`;
- `docs/implementation/M33_8_stable_human_identity_and_scoped_authorization_foundation.md`;
- `docs/implementation/M32_EPIC_CLOSEOUT.md`; and
- the M33 entries in `docs/engineering/DECISION_LOG.md`.

All predecessor boundaries remain in force:

- M32 remains closed and canonical execution planning remains NO-GO.
- M33.8 is not weakened to fit a provider. A username, email, display name,
  bearer token, provider organization role, current workspace owner, or shared
  credential is not by itself M33 human authority.
- The current shared credential cannot be upgraded in place into an
  individual actor. Its historical requests remain unattributed.
- Identity facts do not construct an `ExecutionIntentSnapshot`, append a
  lifecycle event, approve an intent, admit a transaction, establish
  fulfillment, or mutate a portfolio.
- Portfolio authorization is evaluated outside M33. M33 receives the frozen
  result and validates it through `validate_human_authority()`.
- This study adds no ORM model, migration, provider tenant, account, login or
  token change, session/grant store, endpoint, frontend, runtime wiring,
  approval path, M33 persistence, certificate, adapter, snapshot,
  transition, Graphify output, or production behavior.

Provider selection here means selecting an ownership direction and a bounded
proof-of-concept target. It does not approve a vendor contract, production
tenant, personal-data transfer, secret, SDK, database schema, or rollout.

## 2. Verified repository and deployment facts

The study inspected the current authentication implementation and middleware,
frontend login/token/API path, workspace and portfolio models, deployment and
environment configuration, M33.8 contracts/tests, and predecessor studies.

### 2.1 Current authentication and trust boundary

- `backend/auth.py` compares one environment username/password pair and issues
  a 30-day HS256 JWT using a source-code signing secret.
- The JWT contains `sub=username` and `exp`, but the middleware reduces token
  verification to a boolean. It retains no actor, issuer, session,
  authentication event, assurance, or credential status.
- `frontend/lib/auth.ts` stores the bearer token in `localStorage`.
- `frontend/lib/api.ts` sends the token from the browser to a separately
  addressed backend in the `Authorization` header.
- CORS allows localhost and Vercel origins. The frontend and backend therefore
  form a cross-origin browser/API trust boundary in normal deployment.
- A token-validity check is not a current session/actor-status check. There is
  no way to disable one person or revoke one person's authority independently.

### 2.2 Workspace, deployment, and operations

- `Workspace` is documented as the top-level tenant boundary in single-user
  mode; `_ws_id()` always returns the default workspace.
- `Portfolio` belongs to one workspace, but no account, membership, role,
  permission, or grant model relates a human to either resource.
- The configured-development inspection recorded by M33.6 found one
  workspace. That is current data, not a product commitment to one human.
- The frontend is Next.js 14/React with Vercel configuration.
- The backend is FastAPI/SQLAlchemy with PostgreSQL in deployment; PM2 runs
  four Uvicorn processes on a VPS bound to `127.0.0.1:8000`.
- The README names VPS, PM2, and Nginx. No proxy configuration or its
  authentication/log-retention policy is retained in the repository.
- Environment files contain application credentials, database configuration,
  provider keys, and frontend/backend URLs. This study inspected variable
  names only and did not expose or reuse values.
- No user/account/session/membership/role/permission/grant ORM concept exists.
  `UserExecutionDecision` and unrelated `UserUsage` are not identity models.
- No repository evidence names a security operations owner, recovery SLA,
  privacy/data-residency policy, external auditor, or regulated approval
  retention requirement.

## 3. Product and deployment constraints

| Constraint | Verified repository fact | Assumption used for this recommendation | Required confirmation |
| --- | --- | --- | --- |
| Human-user count | One shared credential and one development workspace exist; neither proves one human. | Initially a small number of named humans. | Current users, 12/24-month count, and external-user roadmap. |
| User model | Models say single-user mode; M33.7 requires stable per-human authority. | Independently revocable owner/operator accounts are needed even if only one person uses the product. | Whether shared workspace review will exist. |
| Workspace ownership | One default workspace, no actor owner. | One initial owner/admin will be bootstrapped explicitly. | Owner, administrator, reviewer, and transfer semantics. |
| Portfolio grants | No grants exist. | Small grant volume; inheritance allowed only by explicit policy. | Whether reviewers see all or selected portfolios. |
| Topology | Next.js/Vercel frontend; cross-origin FastAPI/PostgreSQL VPS backend. | Split architecture remains. | Production domains, TLS/proxy owner, and same-origin plans. |
| Internet exposure | Vercel and deployed API imply an internet-facing path; proxy config is absent. | Provider and backend can communicate over the internet. | Private ingress, WAF, and egress constraints. |
| Operational owner | Deployment files exist; accountable identity/security owner is unnamed. | One product operator can own bootstrap/recovery. | Named primary/backup owner and incident contact. |
| Security/recovery | No individual recovery, disablement, session inventory, or key history. | Individual recovery and immediate approval blocking on revocation are required. | MFA/passkey, recovery assurance, and break-glass policy. |
| Approval volume | No M33 runtime exists. | Low volume; synchronous status/grant checks per approval are affordable. | Peak volume and latency/outage targets. |
| Audit/regulation | No external relying party or regulated evidence requirement is documented. | Internal durable audit is initially sufficient. | Jurisdiction, retention, legal hold, and evidence export. |
| Budget | No identity budget is recorded. | Modest managed-service cost is acceptable to avoid credential operations. | Procurement and plan-tier constraints. |
| Maintenance | Current operations cover Vercel, VPS/PM2, PostgreSQL, and providers. | A self-hosted identity control plane is undesirable. | On-call, patch, backup, HA, and recovery tolerance. |
| Data residency | No policy is recorded. | Managed identity is acceptable only after explicit review. | Region, DPA, subprocessors, export, deletion, and pseudonymization. |

If managed identity cost, internet dependency, or residency is unacceptable,
the fallback is a separately approved local/self-hosted design or stopping M33,
never the shared credential.

## 4. Candidate ownership models

| Capability / cost | A. Application-local | B. Managed provider | C. Self-hosted provider | D. Shared credential | E. Stop M33 runtime |
| --- | --- | --- | --- | --- | --- |
| Stable opaque actors | Feasible with new non-reassignable ids | Provider subject + issuer; export/non-reuse must be proven | Realm subject + issuer; operator governs lifecycle | No individual actor | Not applicable |
| Individual credentials | Application must securely implement | Provider-owned | Locally operated provider | No | None |
| Authentication event | Must build login/session/reauth event store | Provider session/token facts + application receipt; POC required | OIDC session/event + application receipt | No individual event | None |
| Revocation/disablement | Fully application-owned | Provider current state + synchronous approval check/events | Local provider API/introspection/events | Token expiry only | Approval absent |
| Assurance/reauth | Must implement | Claims/step-up must be proven | Configurable; mapping must be proven | Unavailable | Not applicable |
| Workspace membership | New application model | Application model; provider org is not final authority | Application model; realm group is not final authority | No individual member | None |
| Workspace/portfolio grants | Application database | Application database | Application database | No actor to grant | None |
| Point-in-time fact | Application generates | App generates after provider + local checks | App generates after provider + local checks | Cannot | None |
| Policy versioning | Entirely application-owned | Application authorization/integration versions | Application authorization/integration versions | Absent | None |
| Outage | Own availability burden | Identity outage blocks approval | Identity outage blocks approval; local ops recover | Invalid authority may persist | No approval |
| Auditability | Potentially strong, entirely local work | Strong source if configured; app retains approval facts | Strong if events are retained/operated | Cannot attribute human | Not applicable |
| Retention/pseudonymization | Entirely application-owned | Provider contract/export plus local opaque audit binding | Entirely operator-owned | Shared mutable username is insufficient | Not applicable |
| Complexity | High security surface | Lowest identity operations | Highest deployment/security operations | Low direct cost, fails authority | Lowest; capability stops |
| Migration | High | Medium | High | None, but invalid | None |
| Cost | Engineering/security operations | Vendor cost + integration | Infrastructure + specialist operations | Low direct cost | Opportunity cost |
| Vendor/deployment dependency | Bespoke application security | Provider availability/API/claim/SDK dependency | Identity cluster/database/operator dependency | Current bespoke secret | None |
| React/FastAPI fit | Feasible, substantial work | Good OIDC/JWT/browser/API fit | Standards-compatible, heavier | Existing but ineligible | No integration |
| M33.8 fit | Feasible after full design | Feasible with app authorization and proven receipt | Feasible with same boundary and operations | **Not feasible** | Preserves pure foundation |

- **A is credible, not smallest.** It would own credential storage, recovery,
  MFA/step-up, sessions, disablement, abuse controls, rotation, and incidents.
  The current `auth.py` is not a safe base for that work.
- **B is selected.** It supplies the credential/session control plane while
  the application retains business authorization and M33 audit bindings.
- **C is conditional** on residency, offline, customization, or control needs.
- **D is rejected** because a shared username/credential is not a person.
- **E remains the safe fallback** if individual identity will not be funded.

## 5. Provider shortlist

Claims below use current official documentation reviewed on 2026-07-17.
Pricing, contractual retention, residency, SLAs, and production-plan features
remain product/procurement inputs.

### 5.1 Clerk - first managed proof-of-concept target

Clerk session-token V2 claims include issuer (`iss`), token id (`jti`),
session id (`sid`), subject (`sub`), issued/expiry times, factor-verification
age (`fva`), session status, and an actor claim for impersonation. Its docs
also recommend keeping larger application data outside token claims. See
[Clerk session-token claims](https://clerk.com/docs/guides/sessions/session-tokens).
Clerk documents backend public-key/JWKS verification and authorized-party
checks, including networkless signature verification, in
[backend token verification](https://clerk.com/docs/reference/backend/verify-token)
and [manual JWT verification](https://clerk.com/docs/guides/sessions/manual-jwt-verification).
It documents signed asynchronous user-lifecycle notifications in
[Clerk webhooks](https://clerk.com/docs/guides/development/webhooks/overview).

| Question | Feasibility conclusion |
| --- | --- |
| Stable actor/namespace | `iss` + `sub` is the candidate; export and non-reassignment expectations require POC confirmation. |
| Authentication event | `sid` is a session and `jti` one token. The M33 event is an application receipt binding both plus recent-auth evidence. |
| Revocation/disablement | Token `exp` is locally verifiable; approval still requires synchronous session/user status. Exact API/error behavior must be proven. |
| Assurance | `fva` can contribute recent-factor evidence; exact rounding, factor policy, and step-up receipt require proof. |
| Backend/events | Signed JWT/JWKS fits the split app. Webhooks can invalidate a projection but cannot prove current state alone. |
| Historical status | Provider APIs/events can contribute current and change facts; durable approval-grade history and ordered revisions remain application-owned. |
| Roles/grants | Organization claims may aid navigation; portfolio grants remain application-owned. |
| Residency/operations | Managed; region/DPA/subprocessor/retention/export terms require review. |
| Exit | Keep provider-neutral issuer/subject/session adapters and preserve old namespaced actor ids. |

Clerk is the first POC target because its documented claims are closest to the
M33.8 primitives and its browser/backend model fits this architecture. It is
not selected for production by this study.

### 5.2 Supabase Auth - managed alternate

Supabase documents a UUID `session_id` claim correlated to `auth.sessions` and
configurable session termination in
[Supabase Auth sessions](https://supabase.com/docs/guides/auth/sessions).
Its server-side `get_user(jwt)` validates the access token against the auth
server and exposes deleted/banned state; see
[Supabase Python `get_user`](https://supabase.com/docs/reference/python/auth-getuser).
It also documents asymmetric signing keys, JWKS discovery, rotation, and
revocation cache caveats in
[Supabase JWT signing keys](https://supabase.com/docs/guides/auth/signing-keys).

| Question | Feasibility conclusion |
| --- | --- |
| Stable actor/event | Project issuer + `sub` is the actor candidate; `session_id` is a session, still requiring an application reauth receipt. |
| Revocation/disablement | Current server user/session checks are candidates; locally valid JWT alone is insufficient. |
| Assurance | Reviewed sources do not establish an M33-ready assurance/step-up claim; material POC gap. |
| Backend/keys | Bearer JWT and Python verification fit; asymmetric keys and current user/session checks are required. |
| Historical status | Session/user sources can contribute; immutable status history needed by M33 must be retained by the application integration. |
| Grants | Stay in application PostgreSQL, not JWT custom claims. |
| Residency/exit | Managed-project region/contracts and user/session export require review; existing PostgreSQL does not imply adoption. |

Supabase is credible, especially if its wider platform is later chosen, but
Clerk has the clearer documented recent-factor primitive for the first POC.

### 5.3 Keycloak - conditional self-hosted option

Keycloak exposes OIDC discovery/JWK endpoints and confidential-client token
introspection; see
[Keycloak OIDC endpoints](https://www.keycloak.org/securing-apps/oidc-layers).
Its [Server Administration Guide](https://www.keycloak.org/docs/latest/server_admin/)
documents session inventory/timeouts, revocation, user/admin events, and
back-channel logout, while noting that outstanding access tokens can remain
valid unless the appropriate revocation mechanism reaches the client.

| Question | Feasibility conclusion |
| --- | --- |
| Stable actor/event | Realm issuer + OIDC subject is the actor candidate; session/login event can seed an application receipt if retention is configured. |
| Revocation/disablement | Introspection, admin state, revocation policy, and back-channel logout exist; configuration and synchronous status remain mandatory. |
| Assurance | Flow/ACR mapping is configurable but must be proven for M33 reauth. |
| Backend/events | Standards fit Next.js/FastAPI; durable event export is operator-owned. |
| Historical status | User/admin events can be configured, but complete durable retention and gap monitoring are operator responsibilities. |
| Grants | Remain application-owned; realm roles may bootstrap coarse roles only. |
| Residency/operations | Operator controls location and also owns upgrades, DB, backup, HA, monitoring, keys, and incidents. |

Keycloak is justified only by a confirmed self-hosting/control requirement.

## 6. Authorization ownership decision

Workspace/portfolio grants belong in an **application-owned Identity and
Authorization domain backed by the application database**, not M33 and not
primarily the identity provider.

The provider owns who authenticated and whether that account/session is
current. The application owns what the actor may do to application resources.
This supports exact portfolio scope, direct grants, versioned inheritance,
immediate grant revocation, resource deletion status, and reproducible policy
facts without high-cardinality token claims. A dedicated authorization service
is not justified at current scale but could later sit behind the same facts.

No schema is approved here. A future owner must provide provider actor
binding; workspace membership; direct portfolio grant; explicit inherited
grant policy; grant id/status/expiry/revocation; workspace/portfolio status;
authorization policy version; and an immutable evaluation receipt for exact
actor, authentication receipt, scope, permission, and time.

## 7. Mapping viable candidates to M33.8

| Candidate | `ActorRef` | `AuthenticationEventRef` | `ActorStatusFact` | Scope/grant/authority | Required proof |
| --- | --- | --- | --- | --- | --- |
| Application-local | New local opaque actor + namespace | Local login/step-up event + session | Local account/credential/session store | Local application grants/facts | Complete credential, recovery, MFA, session, and incident design |
| Clerk hybrid | `iss` + `sub`; local provider config | Application receipt bound to `sid`, `jti`, verified claims, and reauth evidence | Synchronous user/session check + governed status version | Local exact resources/grants/policy/fact | Exact reauth time, disable/session behavior, version grammar, webhook/outage behavior |
| Supabase hybrid | Project issuer + `sub` | Receipt bound to `session_id` and verified JWT/current user | Current user/session + governed status version | Local exact resources/grants/policy/fact | Assurance/step-up and prompt session-revocation mapping |
| Keycloak hybrid | Realm issuer + subject | Receipt bound to OIDC session/login event | Introspection/admin status + local revision | Local exact resources/grants/policy/fact | Event retention, ACR/reauth, revocation, HA, operator readiness |

No candidate currently supplies a complete M33.8 package to this repository.
The selected hybrid mapping is specified field by field next.

## 8. M33.8 field mapping for the selected direction

“Current” means queried/evaluated for the approval attempt; “immutable” means
retained as an audit fact after creation.

| Contract / fields | Exact source and owner | Mutability/freshness | Outage, retention, verification, missing behavior |
| --- | --- | --- | --- |
| `ActorRef.contract_version` | M33.8 adapter constant | Immutable | Retain; unsupported refuses. |
| `actor_type` | Integration policy maps an interactive provider user to `HUMAN` | Immutable per fact | Verify token/client type; machine/ambiguous refuses. |
| `actor_id` | Provider `sub`, retained opaque | Stable candidate; non-reassignment/export must be proven | Signed token + current response; retain namespaced id; missing/change refuses. |
| `authority_namespace` | Canonical environment + provider issuer/tenant | Immutable | Exact compare; migration creates new namespace; mismatch refuses. |
| `identity_provider_ref` | Versioned local provider-configuration id | Immutable reference, supersedable config | Retain issuer/JWKS history; unknown refuses; never a secret. |
| `AuthenticationEventRef.contract_version` | Adapter constant | Immutable | Retain; unsupported refuses. |
| `authentication_event_id` | Caller-generated application receipt id for one governed login/reauth | Immutable; one per qualifying act | Retain with command; no receipt refuses. |
| `actor_ref`, `provider_ref` | Verified exact actor + provider config | Immutable | Cross-check issuer/subject; mismatch refuses. |
| `authenticated_at` | Authority-server UTC completion of qualifying login/step-up/reauth | Immutable | POC must bind exact ceremony; approximate factor age alone is insufficient. |
| `valid_until` | Earliest provider session/token, reauth-policy, and receipt TTL | Immutable bound | Current status still rechecked; missing/unbounded refuses. |
| `assurance_class` | Versioned mapping from verified provider authentication facts | Immutable; allowed set by M33 policy | Retain mapping/source; unknown refuses. |
| `credential_status_version` | Deterministic version/hash of synchronous provider user/session status under integration grammar | Immutable in event | Must be reproducible without token bytes; no honest version fails POC. |
| `credential_binding` | Only individually enrolled provider user maps to `INDIVIDUAL` | Immutable | Provider/client/bootstrap evidence; shared/unknown refuses. |
| `subject_mode` | Provider impersonation/actor claims + policy; MVP `DIRECT` only | Immutable | Retain result, not token; delegated/impersonated/unknown refuses. |
| `ActorStatusFact.contract_version`, `status_fact_id` | Adapter constant + caller-generated status-check id | Immutable result | Retain; missing refuses. |
| `actor_ref`, `authentication_event_id` | Selected actor and exact receipt | Immutable | Exact equality; mismatch refuses. |
| `actor_status` | Synchronous provider user lookup + local binding tombstone/merge state | Current, short TTL | Provider outage/ambiguity blocks; disabled/deleted/unknown refuses. |
| `credential_status` | Provider security state supported by proved adapter | Current, short TTL | Never infer from JWT validity; revoked/unknown refuses. |
| `credential_status_version` | Fresh deterministic version/hash under same grammar | Current; must match event policy | Retain versions/source refs; missing/mismatch refuses. |
| `session_status` | Synchronous lookup/introspection for exact provider session | Current, short TTL | Webhooks may invalidate early, never prove active; revoked/unknown refuses. |
| `checked_at`, `valid_until` | Authority-server UTC and earliest status/policy expiry | Immutable fact | Server clock; stale/naive/missing refuses. |
| `AuthorizationScope.contract_version` | Adapter constant | Immutable | Unsupported refuses. |
| namespace/workspace/portfolio | Namespace above plus exact ids from frozen target, verified against app resources | Immutable target; current resource status | App DB authoritative; mismatch/missing/store outage refuses. |
| `GrantSourceRef.contract_version` | Adapter constant | Immutable | Unsupported refuses. |
| `grant_source_id` | Immutable local direct or workspace grant id | Source may revoke; id never reused | Retain tombstone/history; missing/ambiguous refuses. |
| `grant_kind` | Local source: `DIRECT_PORTFOLIO` or explicit `WORKSPACE_INHERITED` | Immutable source fact | Verify named policy; implicit/unknown refuses. |
| grant namespace | Application environment/authorization namespace | Immutable | Exact compare; mismatch refuses. |
| `ActorAuthorityFact.contract_version`, `authority_fact_id` | Adapter constant + caller-generated evaluation id | Immutable result | Retain with command/refusal audit; missing refuses. |
| actor/auth event/scope/permission | Exact actor, receipt, target scope, and `EXECUTION_INTENT_REVIEW` | Immutable input | Exact equality; provider role cannot substitute; mismatch refuses. |
| `authorization_policy_version` | Versioned application policy deployed for evaluation | Immutable in fact | Retain reproducible policy/fixtures; unsupported refuses. |
| `grant_source` | Unique local source selected deterministically | Immutable reference | Retain history; no unique effective source refuses. |
| `checked_at`, `valid_until` | App authorization UTC check + minimum grant/policy/status validity | Immutable short-lived fact | Store outage/expiry/staleness refuses. |
| `decision` | Deterministic application evaluation | Immutable | Retain `ALLOW`/`DENY`; unknown produces no usable fact. |
| `grant_status` | Current local grant status | Immutable in fact | Retain source revision; revoked/expired/unknown refuses. |
| workspace/portfolio status | Current application resource rows/tombstones | Immutable in fact | DB authoritative; deleted/unknown refuses. |
| `IdentityValidationPolicy` versions/sets | M33 identity-policy owner | Immutable named policy | Retain in validation hash; unsupported refuses. |
| allowed assurance + freshness durations | Product/security-approved after POC; authority-server UTC | Immutable per policy | No provider-default inference; invalid/unknown refuses. |
| workspace-inheritance flag | Explicit application policy, false by default | Immutable per version | Implicit inheritance refuses. |

Provider token/cookie/refresh token, password, secret, private key, email,
username, and display name are never M33.8 fields or M33 audit inputs.

## 9. Authentication-event strategy

### 9.1 Selected meaning

`AuthenticationEventRef.authentication_event_id` identifies an
**application-created recent-authentication receipt**, not a provider user id,
session id, access-token id, or API request id.

The receipt is created only after the backend:

1. verifies signature, issuer, audience/authorized party, expiry, and token
   type;
2. binds the exact provider subject and session;
3. proves a direct, individually authenticated human rather than a machine,
   shared, delegated, or impersonated subject;
4. verifies a qualifying recent login/step-up/reauth event under an approved
   assurance mapping;
5. synchronously checks current actor/account/credential and session status;
6. computes the governed credential/session status version; and
7. assigns authority-server UTC receipt identity, event time, and expiry.

The provider session id is a source reference. Token `jti` or equivalent is
diagnostic correlation. A refreshed token does not create new human
authentication by itself.

### 9.2 Refresh, reauthentication, and current state

- Token refresh may change token id/expiry while retaining the provider
  session. It does not reset M33 authentication age.
- Once recent-authentication TTL expires, approval requires a new qualifying
  provider step-up/reauth and a new application receipt.
- A changed actor/credential/session status version invalidates the prior
  receipt under the selected policy and may require new authentication.
- Every approval requires a fresh `ActorStatusFact` and
  `ActorAuthorityFact`, even while the authentication receipt is valid.
- Retain receipt/provider references, assurance/version mapping, source-event
  reference, UTC times, status version/hash, and response classification.
- Never retain password, bearer/refresh token, cookie, recovery secret, or
  provider private key in the receipt or M33.

The POC fails if it cannot prove exact recent authentication or a reproducible
status version without retaining credentials/secrets. The response is another
provider or stopping M33, not a weaker M33.8 contract.

## 10. Minimum future integration and migration sequence

This ordering authorizes no implementation.

1. Confirm user roadmap, identity operator, residency/privacy, MFA/recovery,
   budget, outage tolerance, and workspace/portfolio role policy.
2. Run an isolated non-production provider POC with synthetic users for
   subject/session stability, backend verification, recent auth, disablement,
   session revocation, key rotation, webhook gaps, export, and outage.
3. Freeze provider-neutral provider-config, actor-binding, authentication-
   receipt, current-status-revision, and error contracts outside M33.
4. Design application authorization persistence separately: actor binding,
   membership, grant, policy, resource tombstone, authority fact, and
   retention. This is not M33 intent persistence.
5. Bootstrap the first individual administrator through a documented one-time
   operator ceremony. Knowing the shared password proves nothing.
6. Assign the existing workspace explicitly to that actor through a new grant.
7. Create direct portfolio grants or one named inheritance policy and record
   every affected portfolio.
8. In a separately approved milestone, replace browser login with the
   provider-maintained flow. Do not copy provider secrets to the browser or
   preserve `localStorage` bearer storage by default.
9. Replace boolean backend authentication with a typed context containing
   verified issuer, audience/authorized party, subject, session, token type,
   and impersonation/delegation state.
10. Generate recent-authentication receipts only after a governed ceremony and
    current provider status check.
11. Generate exact authorization facts from the application grant owner.
12. Exercise the unchanged M33.8 validator with fixtures before runtime.
13. Retire shared login for authoritative use. During bounded coexistence it
    may support explicitly legacy/read-only functions only, never M33.
14. Begin any M33 persistence/runtime work only under a later approval.

No legacy `UserExecutionDecision`, recommendation, transaction, shadow, or
request is attributed to a newly created actor. Bootstrap creates prospective
authority only.

### 10.1 Rollback and recovery

- Before M33 rollout, rollback disables the new identity/approval feature; no
  M33 authority is created.
- During migration, provider failure may restore old login only for explicitly
  non-authoritative/read-only functions.
- After individual accounts become authoritative, rollback preserves actor
  bindings, grants, facts, and audit references.
- Recovery administrators may restore access but cannot impersonate approval.
- Tenant compromise or provider migration creates a new provider namespace
  and explicit migration binding. Historical `ActorRef`s are not rewritten.

## 11. Security, revocation, and outage model

| Scenario | Approval behavior | Other product behavior |
| --- | --- | --- |
| Provider unavailable | Block receipts and approval; cached success is not extended. | Read-only access may continue under a separate short-lived local-JWT policy. |
| Authorization store unavailable | Block: exact grant, policy, and resource state are unknown. | Separately governed read-only access may continue. |
| Status cache stale | Block after M33.8 freshness limit. | Webhooks can shorten, never extend, validity. |
| Webhook delay/missing/order conflict | Synchronous check governs; ambiguity blocks. | Reconcile later without rewriting facts. |
| JWT valid, actor disabled/deleted | Current status refuses; token signature cannot override it. | End/restrict other access under identity policy. |
| Session revoked after issuance | Current session check/revocation invalidates status; refuse. | Locally valid token may be rejected before cryptographic expiry. |
| Grant revoked during review | Approval-time evaluation sees changed/revoked grant; refuse. | Prior display cannot preserve permission. |
| Approval during outage | Typed unavailable/unknown refusal; append zero lifecycle events. | Retry after recovery with fresh facts/display as required. |
| Clock disagreement | Authority server/database UTC owns time; beyond configured skew block and alert. | Client time is never authority. |
| Signing-key rotation | Verify `kid`/issuer/audience; refresh JWKS once for unknown key; unknown trust blocks. | Read-only may use valid cached keys within separate policy. |
| Account merge | Old/new actor ids remain distinct; no heuristic winner. | External lineage may correlate; audit stays on old ids. |
| Provider migration | New provider config/namespace and explicit actor binding; bounded audited dual verification. | Export and rollback proven before cutover. |
| Provider active, local binding disabled | Local fail-closed binding prevents application authority. | Access follows local policy. |
| Grant changes before commit | Future approval must recheck/lock or compare grant/policy revision; stale fact refuses. | No timestamp winner. |

Local JWT verification is an availability optimization, not current revocation
proof. Read-only portfolio access may continue during an identity outage if a
separate bounded policy allows it; approval cannot.

## 12. Recommendation, cost, and blockers

### 12.1 Direction

**`HYBRID_IDENTITY_AUTHORIZATION_SELECTED`**:

- managed provider: account, authentication, credential, session,
  disablement, recovery, and provider-side events;
- application Identity/Authorization domain: provider binding, status
  receipt/revision, workspace membership, portfolio grant, resource status,
  policy, point-in-time fact, and audit retention; and
- M33: pure validation and immutable binding only.

Clerk is the first POC target, Supabase Auth the managed alternate, and
Keycloak conditional on self-hosting/control input. No production provider is
approved yet.

### 12.2 Cost and dependency position

- Managed identity introduces recurring cost and internet/vendor dependency.
- Application authorization still needs persistence, policy, audit,
  migration, and operations.
- Provider outage blocks approval by design.
- A provider-neutral adapter, local grants, exact issuer namespace, export
  test, and migration plan constrain lock-in.
- Self-hosting trades vendor dependency for patching, infrastructure, backup,
  HA, key, monitoring, and incident cost.
- If product input rejects both cost profiles, stop M33 runtime adoption.

Application-local identity is not selected because a user table is only a
small portion of the required credential, recovery, MFA, session, abuse,
rotation, notification, and incident-control surface.

### 12.3 Current blockers

1. User roadmap, operator, residency, MFA/recovery, budget, and availability
   expectations are unconfirmed.
2. No provider tenant/configuration exists in the repository.
3. No provider has proven exact recent-authentication/assurance mapping here.
4. No adapter has proven synchronous disabled-user/session-revoked behavior
   and deterministic outage classification.
5. M33.8 credential/session status-version grammar is not proven against a
   real provider.
6. Application workspace/portfolio grants and policy persistence do not exist.
7. Retention/pseudonymization ownership is unnamed.

## 13. Readiness and prerequisite exit evidence

**Readiness: `PROVIDER_PROOF_OF_CONCEPT_REQUIRED`.**

`READY_FOR_IDENTITY_IMPLEMENTATION_DESIGN` is premature because provider
status, recent-authentication, and status-version mapping remain unproven.
`AUTHORIZATION_MODEL_DESIGN_REQUIRED` is not selected because this study
decides its owner/semantics. Product input is required but does not replace
the technical proof. `STOP_M33_AFTER_PURE_FOUNDATION` remains the fallback.

Exit requires all of:

1. named product/security/operations owners and resolved section 3 inputs;
2. non-production provider configuration with exact issuer, audience,
   subject, session, token id, and key behavior;
3. subject export/non-reassignment evidence or approved stable local binding;
4. individual login plus refusal of shared/machine/delegated/impersonated use;
5. exact recent login/step-up/reauth UTC event and assurance mapping;
6. active, disabled/deleted, revoked-session, expired, and unknown fixtures;
7. reproducible credential/session status version without token storage;
8. key rotation, outage, webhook-delay, skew, and recovery fixtures;
9. region/DPA/subprocessor/retention/export/deletion review;
10. authorization fixtures for direct/inherited grant, deny, revoke, expiry,
    resource deletion, policy change, scope mismatch, outage, and grant race;
11. field-complete adapter output passing unchanged M33.8 validation;
12. synthetic bootstrap/rollback rehearsal without legacy attribution; and
13. explicit proceed, alternate-provider POC, or stop decision.

JWT signature verification alone is not exit evidence.

## 14. Recommended next milestone

**M33.10 - Managed Identity Claim, Current-Status, and Revocation Proof of
Concept (isolated, non-production).**

M33.10 should jointly with the Authentication/Authorization domain:

1. resolve the product inputs;
2. exercise Clerk first using synthetic users/non-production tenant;
3. prove issuer/subject/session/token, reauth/assurance, disablement,
   revocation, key rotation, webhook delay, outage, and export behavior;
4. specify/test the provider-neutral receipt and status-version grammar;
5. specify application direct/inherited authorization facts using fixtures;
6. map fixtures into unchanged M33.8 contracts and validator;
7. compare Supabase only if Clerk fails a mandatory requirement; and
8. end with implementation readiness, alternate POC, or stop.

It should add no production account/session/grant table, migration, login/token
change, API, frontend, production secret, middleware, approval endpoint, M33
persistence, certificate, adapter/backfill, snapshot, lifecycle transition,
Graphify change, or M32 change. Any POC artifact must be isolated, synthetic,
non-production, and separately approved.

## 15. Decision Log and non-adoption statement

A `DECISION_LOG` entry is added because M33.9 makes a concrete new ownership
and product-direction decision: managed identity plus application-owned
workspace/portfolio authorization, with Clerk as the first POC target.

M33.9 does not:

- modify Python/TypeScript code or tests;
- install an SDK, create/configure a provider tenant, or move a secret;
- add ORM, migration, repository, account/session/grant store, API, frontend,
  middleware, writer, or runtime wiring;
- change login, token issuance, local storage, CORS, workspace, or portfolio
  behavior;
- retain a credential, token, cookie, password hash, secret, or private key;
- create an actor, receipt, status fact, grant, authority fact, intent,
  snapshot, display receipt, command, transition, or audit receipt;
- add identity, intent, lifecycle, approval, or certificate persistence;
- construct a snapshot or call lifecycle validation;
- attribute/adapt/backfill any legacy decision;
- change recommendation, optimizer, expiry, shadow, transaction, portfolio,
  ledger, evaluation, or replay behavior;
- change Graphify output; or
- reopen M32 or adopt canonical execution planning.
