# M33.7 - Prospective Human Authority and Direct Approval Capture Design

**Date:** 2026-07-17

**Status:** Design complete. Prospective identity, review, direct-approval,
time, concurrency, audit, and persistence-boundary design only. No runtime or
persistence adoption.

**Milestone decision:** A prospective approval must be a fresh act by one
stable, currently authorized human over one immutable M33.2
`ExecutionIntentSnapshot`. The act binds the exact `snapshot_id`,
`content_hash`, canonical review-payload digest, display receipt, scope, actor,
authentication event, grant fact, and expected lifecycle sequence. The
current shared-credential authentication path cannot supply that authority.
Readiness is therefore **`IDENTITY_PREREQUISITE_REQUIRED`**. The smallest
future MVP is manual-independent, target-weight intent review with approve,
reject, explicit expiry, and a durable audit receipt; optimizer conversion,
historical proposals, target-value terms, supersession, certificates, and all
execution behavior remain deferred.

## 1. Authoritative boundary

The governing inputs are:

- `docs/implementation/M33_1_execution_intent_snapshot_lifecycle_foundation.md`;
- `docs/implementation/M33_2_pure_execution_intent_contracts.md`;
- `docs/implementation/M33_3_legacy_adapter_feasibility.md`;
- `docs/implementation/M33_4_historical_authority_certification_contract.md`;
- `docs/implementation/M33_5_pure_authority_verification_contracts.md`;
- `docs/implementation/M33_6_authority_evidence_availability_and_issuer_governance.md`;
- `docs/implementation/M32_EPIC_CLOSEOUT.md`; and
- the M33 entries in `docs/engineering/DECISION_LOG.md`.

All predecessor boundaries remain in force:

- M32 remains closed and canonical execution planning remains NO-GO.
- M33.2 contracts, content hashing, human-only approval, expected-prior-state
  validation, and transition semantics are unchanged.
- Historical rows provide no exact approval authority. This design is for new
  current-human acts, not historical certificate reconstruction.
- Recommendations, optimizer results, shadows, transactions, holdings, and
  current UI state cannot supply or modify approved terms at approval time.
- Approval is non-executing. It creates no order, transaction, fill, ledger
  admission, fulfillment fact, cash change, or portfolio mutation.
- No certificate is needed for direct in-system approval. A certificate may
  be considered later only for a separately named relying party.
- This milestone adds no model, migration, repository, API, frontend, writer,
  identity provider, runtime wiring, snapshot, transition, backfill, adapter,
  certificate, key, signature operation, or Graphify change.

The future persistence entities described here are proposals, not approval to
create tables. Names are conceptual and do not reserve ORM class names.

## 2. Verified current-state identity and approval audit

The review inspected `backend/auth.py`, the authentication middleware and
default-workspace resolver in `backend/main.py`, workspace/portfolio and
decision models, optimizer and recommendation-snapshot writers, the decision
endpoint, the frontend login/token/API path, the optimizer result display,
`ExecutionPlanCard`, and the M33.2 pure contracts and transition tests.

### 2.1 Authentication

The current authentication model has one username/password pair supplied by
environment variables. Login creates a 30-day HS256 JWT containing `sub` and
`exp`. The signing secret is a source-code constant. The browser stores the
token in `localStorage` and sends it as a bearer token.

Middleware calls `verify_token()` and retains only a boolean. It does not put
the token subject, authentication event, session, authentication method, or
credential state into request context. There is no user table, stable actor
namespace, session table, key id, role, grant, disabled-user check, credential
rotation history, or authentication-event retention.

Consequences:

- token possession proves only knowledge of a shared application credential;
- two people using that credential are indistinguishable;
- a valid token cannot be tied to a unique approval actor;
- disabling a person cannot invalidate that person's authority separately;
- a request cannot retain which authentication event supported the act; and
- a later database row cannot reconstruct the missing actor.

### 2.2 Workspace and portfolio authorization

`_ws_id()` always returns the default workspace. Portfolio endpoints commonly
check that a portfolio belongs to that workspace, but this is tenant
filtering, not actor-scoped authorization. No record states that a specific
human had an approval permission for a specific workspace and portfolio at a
specific instant.

The legacy decision endpoint checks the recommendation snapshot's workspace
but accepts `body.portfolio_id` without proving equality to the snapshot's
portfolio. It records neither the authentication subject nor an authorization
fact.

### 2.3 Review and decision capture

The optimizer frontend displays mutable result data and a display-only
`ExecutionPlanCard` derived from recommendation fields. It does not display a
frozen M33.2 snapshot, compute a canonical review digest, record a display
receipt, or bind the confirmation control to a snapshot content hash.

The decision request carries a legacy snapshot id, portfolio id, decision
label, notes, and optional override fields. The production UI does not send
`approved_allocations`. There is no command id, idempotency key, correlation
id, actor reference, authentication-event reference, grant reference,
expected content hash, review digest, prior lifecycle state/sequence, or
mandatory-warning acknowledgement.

The backend uses naive `datetime.utcnow()`, commits the legacy decision before
shadow work, and allows duplicate/conflicting rows. The UI hides controls
after finding one row, but that is not concurrency protection.

### 2.4 Current-state conclusion

Current authentication cannot support prospective M33 approval. Reusing it
would assign authority to a shared credential, not a verified human. The
optimizer decision path also lacks the frozen review and command boundaries
required by M33.2. These are prerequisite gaps; they must not be repaired by
adding actor text or a content hash to the existing decision row.

## 3. Target human actor and authority model

The model below is the minimum M33 authority boundary. It is not a full IAM
platform design.

### 3.1 `ActorRef`

An authoritative human actor reference contains:

| Field | Semantics |
| --- | --- |
| `actor_type` | Must be M33.2 `HUMAN` for approve/reject. Service identities use `SYSTEM`. |
| `actor_id` | Stable opaque identity; never username, display name, email, token subject without namespace, or session id. |
| `authority_namespace` | Tenant/deployment/identity namespace in which `actor_id` is unique. |
| `identity_provider_ref` | Versioned provider or local identity authority that resolved the actor. |

Display names are mutable presentation attributes and are not actor identity.
They may be copied into an audit view but never replace `actor_id`.

### 3.2 `AuthenticationEventRef`

Each approval command binds one successful authentication event:

| Field | Semantics |
| --- | --- |
| `authentication_event_id` | Unique opaque identity for the authentication/session event. |
| `actor_ref` | Exact actor authenticated. |
| `authenticated_at` | Authority-owned UTC event time. |
| `valid_until` | UTC maximum validity; null only under an explicit short-lived policy. |
| `authentication_method_class` | Versioned assurance category, not secret material. |
| `credential_status_version` | Identity-provider state/version checked for the event. |

Passwords, tokens, cookies, and signing secrets are never retained in an
approval record. The authentication event is evidence that the current actor
was authenticated; it is not by itself scope authorization.

### 3.3 `ActorAuthorityFact`

The point-in-time authorization result contains:

| Field | Semantics |
| --- | --- |
| `authority_fact_id` | Unique immutable fact identity. |
| `actor_ref` | Exact human actor. |
| `authentication_event_ref` | Authentication event used for this check. |
| `workspace_id`, `portfolio_id` | Exact scope. |
| `permission` | `EXECUTION_INTENT_REVIEW` for approve/reject in the MVP. |
| `authorization_policy_version` | Version of evaluated role/grant rules. |
| `grant_source_ref` | Stable role/grant record or external decision reference. |
| `checked_at` | Authority-owned UTC time immediately before command acceptance. |
| `valid_until` | Optional explicit authorization expiry. |
| `decision` | `ALLOW` or `DENY`; only an `ALLOW` supports transition validation. |
| `revocation_status` | `ACTIVE`, `REVOKED`, `DISABLED_ACTOR`, or `UNKNOWN`. |

Authority means that the exact actor was allowed to perform the exact
permission on both the workspace and portfolio at `checked_at`. Workspace
membership alone is insufficient. Portfolio scope may inherit from a
workspace role only when the named policy explicitly says so and records that
evaluation.

### 3.4 Roles, revocation, and boundaries

The MVP needs only one human permission: `EXECUTION_INTENT_REVIEW`. Role names
may exist upstream, but the retained fact records the evaluated permission.

- A disabled actor, revoked grant, expired authentication event, unknown
  authorization status, or mismatched actor must refuse the command.
- Approval already recorded under valid authority remains an immutable fact.
  Later disablement does not rewrite it; a separately authorized lifecycle
  action may respond prospectively.
- System actors may submit a complete proposal or expire a snapshot under a
  frozen policy. M33.2 continues to forbid system approval.
- System actors cannot use a human authentication event.
- Shared credentials are prohibited for authoritative human acts.
- Delegation and impersonation are not supported in the MVP. If later added,
  both principal and delegate, the delegation grant, purpose, and event time
  must be retained; an impersonating administrator may never appear as the
  principal human silently.

### 3.5 Identity prerequisite

The identity owner must provide stable actor ids, unique authentication-event
ids, actor status, scoped permission evaluation, grant references, and UTC
check times. M33 owns how those facts bind to an approval; it does not own
password policy, account recovery, MFA product design, enterprise directory
synchronization, or general application authorization.

## 4. Prospective direct-approval semantic sequence

The following actions remain semantically distinct even if a future runtime
uses a small number of database transactions.

1. **Prepare terms.** A human or permitted system proposal supplies complete
   M33.2 terms, intent kind, scope, provenance, effective time, and expiry.
   The MVP accepts only direct manual-independent target-weight input.
2. **Allocate identity.** The caller supplies new opaque `intent_id` and
   `snapshot_id`. Neither is derived from content or a legacy row.
3. **Build snapshot.** The unchanged M33.2 constructor validates terms,
   provenance, UTC times, lineage, and computes `content_hash`.
4. **Persist and submit.** One atomic foundation transaction inserts the
   intent identity and immutable snapshot and appends the M33.2 `SUBMIT`
   event from none to `PENDING_REVIEW`. Snapshot construction and submission
   remain separately named facts even inside that transaction.
5. **Derive review payload.** A versioned pure projection derives
   `ReviewPayloadV1` only from the stored frozen snapshot and its review
   contract. It reads no optimizer, recommendation, holdings, price, shadow,
   transaction, or mutable portfolio data.
6. **Display exact payload.** An authorized current human receives the exact
   canonical semantics through an accessible renderer. Localized decoration
   may vary without changing reviewed values.
7. **Record display receipt.** The server records which actor/authentication
   event received which snapshot id, content hash, review digest, warning set,
   renderer contract, and validity interval.
8. **Submit decision request.** The client sends identifiers and expected
   bindings only. It cannot submit or edit terms.
9. **Normalize approval command.** At server receipt, the authority boundary
   verifies identity and scope, assigns authoritative times, and freezes an
   `ApprovalCommand` with `APPROVE` or `REJECT`.
10. **Validate under compare-and-swap.** The command verifies the actor,
    authentication event, grant, exact scope, intent/snapshot identity,
    content hash, review digest/receipt, freshness, warning acknowledgement,
    and expected `PENDING_REVIEW` state/transition sequence.
11. **Append transition.** A successful command maps to the unchanged M33.2
    `APPROVE` or `REJECT` `TransitionCommand`; exactly one next event is
    appended atomically with the command result.
12. **Record and emit audit receipt.** A durable internal receipt is inserted
    in the same transaction. Delivery to an external sink, if any, uses a
    durable outbox/retry boundary and does not redefine lifecycle truth.

No step mutates snapshot content. A term edit abandons the displayed snapshot
for approval purposes and requires a new revision/snapshot, new hash, new
display payload, and new display receipt.

## 5. Canonical review and display contract

### 5.1 `ReviewPayloadV1`

The immutable payload includes exactly:

- `review_payload_contract_version` and `review_policy_version`;
- `intent_id`, `snapshot_id`, and `revision`;
- the unchanged M33.2 `content_hash`;
- `terms_schema_version` and `intent_kind`;
- terms sorted by `(symbol, side)`, each containing exact `symbol`, `side`,
  canonical finite Decimal `target_weight` or `target_value` (exactly one is
  non-null), and term `note`;
- top-level terms `notes`;
- exact `workspace_id` and `portfolio_id`;
- canonical UTC `effective_at` and `expires_at`;
- source provenance sorted by `(source_kind, source_local_id)`, including
  kind, local id, contract version, source time, digest, and completeness;
- the snapshot's `created_by_actor` as preparation provenance; and
- deterministically derived mandatory warning records, sorted by warning id,
  with stable code, severity, and related source reference.

For MVP target-weight terms, the canonical Decimal is a fractional portfolio
weight. A renderer may show `0.10` as `10%`, but it must also expose the exact
canonical value and unit and may not round to a different reviewed value.
`target_value` terms are deferred because M33.2 currently carries no currency
field; a future schema must make value currency explicit before review.

At minimum, V1 always includes the warning
`APPROVAL_IS_NOT_EXECUTION`. Provenance-driven warnings include
`LEGACY_RECONSTRUCTED_SOURCE`, `SOURCE_INCOMPLETE`, and
`SNAPSHOT_EXPIRY_APPLIES` when their exact snapshot facts require them.
`SOURCE_INCOMPLETE` remains approval-blocking under M33.2 rather than becoming
acknowledgeable permission to proceed.

### 5.2 Excluded presentation-only data

The canonical payload excludes:

- portfolio/workspace display names;
- localized labels, translated prose, font, color, icon, layout, and sorting
  chosen only for presentation;
- rounded percentages, currency symbols, grouping separators, and relative
  dates;
- browser/device/user-agent details;
- live price, current holdings, cash, NAV, optimizer score, confidence,
  recommendation explanation, execution-plan projection, fees, and shadows;
- transaction, fulfillment, and performance data; and
- snapshot `recorded_at`, database keys, and audit delivery status.

Such fields may appear beside the review surface as clearly non-authoritative
context, but they may not be placed between a term and its meaning or alter
the approval control.

### 5.3 Canonical serialization and digest

V1 uses an explicit field-list serializer, sorted JSON keys, compact
separators, canonical UTC ISO-8601, finite Decimal `format(value, "f")`, and
the stated collection ordering. Generic dataclass reflection is prohibited.

The digest is:

```text
sha256("M33.7:review-payload:1\n" + canonical_utf8_payload)
```

The review digest is distinct from M33.2 `content_hash`:

- `content_hash` continues to identify reviewed domain content under M33.2;
- the review digest additionally binds snapshot identity, revision, review
  contract/policy, preparation actor, and mandatory warning set; and
- neither digest includes a display-receipt id or mutable UI metadata.

The review contract recomputes and verifies the stored M33.2 content hash
before display. It does not redefine that hash.

### 5.4 Display, locale, accessibility, and freshness

- A locale-specific renderer must be a pure view of the canonical payload.
- Symbols, side, target kind, exact value/unit, scope, intent kind,
  effective/expiry instants, provenance limitations, and warnings must be
  perceptible and programmatically associated.
- Accessibility variants, screen readers, zoom, and responsive/mobile layouts
  may change presentation but must expose the same semantic fields.
- Each browser tab/device/display act receives its own display receipt. The
  payload digest may be identical across receipts.
- Approval must reference one receipt issued to the same actor and
  authentication event, unless a policy explicitly permits a refreshed auth
  event for the same stable actor and records both.
- Receipt validity ends at the earliest of snapshot expiry, authentication
  expiry, authorization expiry, configured review TTL, snapshot
  supersession, or any lifecycle change from the expected sequence.
- Reloading or moving devices requires a new receipt. It never copies an
  unverified client assertion that the payload was displayed.

A display receipt proves that the server supplied the canonical payload to an
authenticated review surface. It does not prove attention, comprehension, or
execution; the explicit command is still required.

## 6. Approval and rejection command contract

### 6.1 `ApprovalCommand`

One immutable command envelope serves both decisions and includes:

| Field | Semantics |
| --- | --- |
| `command_contract_version` | Versioned grammar; unknown versions fail closed. |
| `command_id` | Globally unique opaque request identity. |
| `idempotency_key` | Globally unique retry identity within the authority namespace. |
| `correlation_id` | Joins snapshot, display, command, event, and audit facts. |
| `decision` | Exactly `APPROVE` or `REJECT`. |
| `actor_ref` | Stable current `HUMAN` actor. |
| `authentication_event_ref` | Exact successful authentication event. |
| `authority_fact_ref` | Exact fresh `ALLOW` result for the scope and permission. |
| `workspace_id`, `portfolio_id` | Exact scope. |
| `intent_id`, `snapshot_id` | Exact immutable target. |
| `expected_content_hash` | Exact M33.2 hash. |
| `display_receipt_id` | Exact display act being acknowledged. |
| `expected_review_payload_digest` | Exact V1 review digest. |
| `expected_prior_state` | Must be `PENDING_REVIEW` for MVP approve/reject. |
| `expected_prior_transition_sequence` | Exact current sequence. |
| `acknowledged_warning_ids` | Canonically sorted set; all mandatory warnings required for approval. |
| `occurred_at` | Authority-server UTC time assigned when the normalized command is accepted for evaluation. |
| `server_received_at` | Authority-server UTC first-receipt time. |
| `client_request_ref` | Opaque client-generated request identity for diagnostics. |
| `channel` | Versioned channel such as `WEB`; not actor proof. |
| `client_action_at` | Optional client UTC metadata; never authoritative. |

The transport request supplies expected ids, bindings, decision, warning
acknowledgements, and client metadata. The trusted server creates the final
command by adding verified actor/auth/grant references and authoritative
times. No bearer credential or secret enters canonical command content.

`APPROVE` requires acknowledgement of every mandatory non-blocking warning.
`REJECT` may carry acknowledgements but does not require the human to accept
warnings in order to decline the snapshot.

### 6.2 Prohibited payload and deterministic refusals

An approval request and command must not contain allocations, symbols to add
or remove, target values, notes that alter terms, effective/expiry edits,
source replacements, or an alternate content hash. Any such payload is
`EDITABLE_TERMS_PROHIBITED`; the caller must create a new snapshot.

Required refusal codes include:

| Condition | Refusal |
| --- | --- |
| Snapshot id, intent id, hash, prior state, or sequence changed | `STALE_SNAPSHOT` or underlying M33.2 prior-state/sequence refusal |
| Display receipt missing, expired, wrong actor, wrong snapshot, or digest mismatch | `STALE_DISPLAY` / `DISPLAY_BINDING_MISMATCH` |
| Workspace or portfolio differs anywhere | `SCOPE_MISMATCH` |
| Actor differs across auth, grant, receipt, and command | `ACTOR_MISMATCH` |
| Authentication expired/disabled/unknown | `AUTHENTICATION_NOT_CURRENT` |
| Grant absent, expired, revoked, denied, or unknown | `AUTHORIZATION_NOT_CURRENT` |
| Required warning not acknowledged for approval | `WARNING_ACKNOWLEDGEMENT_REQUIRED` |
| Snapshot expiry is due | `SNAPSHOT_EXPIRED` and no approval event |
| Unknown contract/policy version | `UNSUPPORTED_CONTRACT_VERSION` |
| Terms appear in request | `EDITABLE_TERMS_PROHIBITED` |
| Key/id reused with different canonical content | `IDEMPOTENCY_CONFLICT` / `COMMAND_ID_CONFLICT` |

All refusals append zero lifecycle events. Refusal receipts may be retained for
security/idempotency audit but are not lifecycle transitions.

### 6.3 Mapping to M33.2

After all stronger capture checks pass, the authority boundary creates the
existing M33.2 `TransitionCommand`:

- command type `APPROVE` or `REJECT`;
- the same idempotency key, actor, occurred time, expected state/sequence, and
  correlation id;
- `approval_content_hash=expected_content_hash` for approval; and
- no terms, display, optimizer, shadow, or transaction payload.

M33.2 remains the final lifecycle validator. The outer command receipt retains
the authentication/grant/display evidence that M33.2 intentionally does not
model.

## 7. Time model

| Time | Owner and meaning | Authority |
| --- | --- | --- |
| `authenticated_at` | Identity authority; successful authentication event | Authoritative identity evidence |
| `snapshot.effective_at` / `expires_at` | Frozen M33.2 content | Authoritative applicability interval |
| `snapshot.recorded_at` | Persistence boundary knowledge time | Authoritative insertion time, not review time |
| `displayed_at` | Review server records payload availability to the client | Authoritative display-receipt event time |
| `server_received_at` | Approval boundary first receives request | Authoritative receipt time |
| `authorization_checked_at` | Authorization authority evaluates exact scope | Authoritative authority-check time |
| `occurred_at` | Approval boundary accepts normalized human command | Authoritative lifecycle event time supplied to M33.2 |
| transition `recorded_at` | Database transaction appends event | Authoritative knowledge time |
| `client_action_at` | Client observation of click/action | Metadata only |
| audit `emitted_at` | Internal receipt/outbox creation | Audit knowledge time |

All authoritative instants are timezone-aware UTC. Naive datetimes and
non-UTC offsets are refused at contract boundaries. User locale/timezone may
render effective and expiry times, but the UI must also expose the exact zone
and avoid date-only ambiguity.

The authority server owns `server_received_at`, `authorization_checked_at`,
and `occurred_at`. Client time never determines authority, expiry, ordering,
or conflict winners. V1 treats client skew as diagnostics only: an absolute
skew above five minutes records `CLIENT_CLOCK_SKEW_OBSERVED`, but neither
accepts nor rejects the command on that basis. Expiry and freshness still use
the server/database authority clock.

Approval is allowed only when the server-owned authorization check/occurrence
instant is strictly before `expires_at` and within the display/auth/grant
validity intervals. A command at or after expiry loses to expiry. A future
implementation must define a single database/authority clock source for the
transaction and may append the due `EXPIRE` event separately under M33.2; it
must never approve first based on client time.

Event ordering is transition sequence plus database commit order, not
timestamp sorting. Timestamps explain when facts occurred and were learned;
they never implement latest-wins.

## 8. Idempotency and concurrency matrix

Idempotency is resolved in two stages so server-owned time stays authoritative
without making a retry look different:

1. The transport request has a canonical `request_content_hash` over every
   client-supplied authority field, excluding credentials, client clock,
   presentation metadata, and server-assigned times. `command_id` and
   `idempotency_key` are looked up against this hash before normalization.
2. On the first unseen request, the server verifies identity/authority,
   assigns `server_received_at` and `occurred_at`, and stores one normalized
   command hash over section 6.1. A retry with the same request hash replays
   that stored normalized command/result; it never receives a new occurrence
   time.

This outer request lookup precedes M33.2 `resolve_idempotency()`. The persisted
normalized command then maps to one M33.2 command whose existing canonical
hash includes the single retained `occurred_at`. Replay still requires an
authenticated request resolving to the same stable actor/namespace; an
idempotency lookup must never disclose another actor's command result.

| Scenario | Deterministic result |
| --- | --- |
| Same `command_id`, same request-content hash | Replay the stored normalized command result and audit reference byte-for-byte. |
| Same `command_id`, different request-content hash | Conflict; append nothing. |
| Same `idempotency_key`, same request-content hash | Replay the stored result, even after network delay or client restart. |
| Same `idempotency_key`, different request-content hash | Conflict; append nothing. |
| Same semantic click with new command id/key after acceptance | Lifecycle CAS fails because state/sequence changed; do not create a second event. |
| Two humans approve the same snapshot | Both may validate initially; exactly one wins the atomic prior-sequence CAS. The other receives stale-prior refusal. |
| Approve versus reject race | Exactly one wins the same CAS. No decision priority or latest-wins rule. |
| Approval after supersession | Refused as terminal/stale target. New snapshot requires new display and command. |
| Approval at/after expiry | Refused; client time cannot rescue it. |
| Multiple browser tabs | Each has a receipt. First valid CAS may win; every stale receipt/sequence is refused. |
| Delayed mobile retry / duplicated delivery | Same key/hash replays; new key evaluates current state and normally refuses stale. |
| Offline request | No offline approval. It must reach the authority server while auth, grant, display, snapshot, and expiry are current. |
| Transaction rollback before commit | No event, command result, or audit receipt is authoritative. Retry may use the same key. |
| Event append failure | Roll back command acceptance, idempotency result, and audit receipt together. |
| Internal audit-receipt insert failure | Roll back approval transaction; lifecycle event must not commit without its internal receipt. |
| External audit delivery failure | Committed approval remains valid; durable outbox retries and exposes failure. No duplicate lifecycle event. |

Required database protections are:

- unique `intent_id` and `snapshot_id`;
- unique `(intent_id, revision)` and one direct successor per snapshot;
- unique `(snapshot_id, transition_sequence)`;
- compare-and-swap on exact current state and transition sequence;
- unique `(authority_namespace, command_id)` with stored command hash;
- unique `(authority_namespace, idempotency_key)` with stored command hash;
- unique `display_receipt_id`, `authority_fact_id`, and `audit_receipt_id`;
- at most one command result bound to one command id; and
- one audit receipt per committed command result/event correlation.

The approval transaction reads/locks or conditionally advances the lifecycle
projection, rechecks expiry and authorization time, inserts the command
receipt/idempotency result, appends the event, and inserts the audit receipt or
outbox fact. A cached current-state column may support CAS only if the
append-only event log remains rebuildable authority.

## 9. Persistence design boundaries

| Proposed entity | Authority / mutability | Keys and constraints | Relationships and ownership | Retention, deletion, and hashing | MVP? |
| --- | --- | --- | --- | --- | --- |
| `execution_intent` | Authoritative stable aggregate identity and immutable scope; no mutable status authority | unique opaque `intent_id`; exact workspace/portfolio; immutable after insert | Parent of snapshots; Execution Domain owns identity | Retain with all descendants; no cascade deletion; not content-hashed | Yes |
| `execution_intent_snapshot` | Authoritative immutable terms revision | unique `snapshot_id`; unique `(intent_id, revision)`; unique successor/predecessor rules; verified `content_hash` | FK to intent; source refs must not cascade-delete history | Indefinite/audit retention; deletion restricted; M33.2 reviewed fields participate in existing hash only | Yes |
| `execution_intent_event` | Authoritative append-only lifecycle | event identity; unique `(snapshot_id, transition_sequence)`; exact from/to/command | FK to snapshot and command receipt; lifecycle owner | Never update/delete normally; M33.2 event data retained; not part of snapshot hash | Yes |
| `review_display_receipt` | Authoritative server fact that exact review payload was issued; not proof of comprehension | unique receipt id; snapshot id/hash; review version/digest; actor/auth ref; displayed/valid-until UTC | FK to snapshot; identity references may be opaque external refs | Immutable; retain with approval/refusal policy; review payload digest separate from M33.2 hash | Yes |
| `approval_command_receipt` | Authoritative immutable command intake, idempotency, and typed result | unique command id and idempotency key in namespace; stored command hash; correlation id | FK to snapshot, display receipt, authority fact, optional event/refusal | Immutable; no secret/token bytes; command hash is separate; never cascade-delete | Yes |
| `actor_authority_fact` | Authoritative retained result of a point-in-time identity/authorization check; not general IAM state | unique fact id; actor/auth/grant refs; exact scope/permission/policy/time/status | Identity/authorization owner supplies facts; M33 references them | Immutable pseudonymous id preferred; retain with dependent command; not in snapshot hash | Yes |
| `audit_receipt` | Authoritative internal audit correlation/proof of committed result; not lifecycle owner | unique receipt id; unique committed command/event correlation; optional receipt digest | FK to command/event; external delivery uses separate append-only attempts/projection | Immutable core receipt; retain at least as long as lifecycle; separate audit digest allowed | Yes |

No certificate table is proposed. Mutable delivery state, search indexes, and
current-lifecycle projections are rebuildable operational projections, not
authority. Physical deletion must not be permitted through workspace,
portfolio, recommendation, actor, or legacy-row cascades. Privacy erasure must
use an approved pseudonymization/retention policy that preserves referential
and audit integrity.

Snapshot creation plus `SUBMIT` should be one atomic foundation transaction.
Approval is a later transaction. Display receipt creation is a separate event.
This preserves the semantic distinctions required by section 4 even when
storage is optimized.

## 10. Historical proposal and reconfirmation boundary

An optional M33.5 proposal may enter only before snapshot construction:

```text
legacy candidate + authority result + warnings
    -> pre-snapshot ProposalCandidate
    -> current human edits/reviews complete terms and scope
    -> ReconfirmationPreparation
    -> new caller-supplied intent_id and snapshot_id
    -> fresh M33.2 snapshot/content_hash and PENDING_REVIEW
    -> same M33.7 review display and direct approval path
```

The path must:

- preserve every legacy warning and provenance limitation;
- require current-human editing/review rather than silent normalization;
- create new intent/snapshot ids, content hash, display receipt, command, and
  current actor/authority facts;
- never inherit historical `APPROVED`, actor, time, lifecycle state,
  transaction link, execution status, or fulfillment; and
- refuse rejected/expired sources and quarantine conflicting sources under the
  existing M33.3-M33.5 rules.

Historical proposals are **deferred from the initial MVP**. They add legacy
allocation mapping, warning UX, proposal retention, and product-value
questions before the direct prospective authority path exists. Deferral does
not change the pure M33.5 contracts or prohibit a later opt-in milestone.

## 11. Smallest valuable MVP

| Question | MVP decision |
| --- | --- |
| Intent kinds | `MANUAL_INDEPENDENT` only |
| Term form | Complete target-weight terms only; canonical fractional weights; target-value/currency deferred |
| Human source | Direct current verified human input only |
| Optimizer recommendation conversion | Deferred; mutable/unversioned recommendation actions and units are not approval terms |
| Historical reconfirmation proposal | Deferred |
| Approval | Included; exact snapshot/hash/review/actor/grant binding |
| Rejection | Included; exact snapshot rejection is useful and terminal |
| Expiry | Included as explicit frozen `expires_at` plus system policy transition; no date-only inference |
| Supersession/revision UI | Deferred; MVP may require abandoning/creating a separate new intent rather than editing an approved one |
| Defer/resume/cancel/quarantine | Deferred from product surface |
| Audit receipt | Required for every committed approve/reject result |
| Certificates | Excluded |
| Execution request, transaction linkage, fulfillment | Excluded |

The MVP proves the authority boundary with the fewest semantic conversions.
It does not call a recommendation an intent, does not claim an execution plan,
and does not connect approval to portfolio mutation. A later milestone may add
`MANUAL_OVERRIDE` or `FOLLOW_RECOMMENDATION` only after a typed, frozen source-
to-terms contract and review semantics are separately approved.

## 12. Readiness decision

**Decision: `IDENTITY_PREREQUISITE_REQUIRED`.**

The review/display, command, time, idempotency, concurrency, and minimum
persistence boundaries are sufficiently defined for later implementation
planning. Persistence or runtime work must nevertheless stop because the
current system cannot produce these mandatory inputs:

1. stable namespaced human actor identity;
2. unique retained authentication-event identity;
3. actor-scoped workspace and portfolio permission;
4. a point-in-time authorization/grant fact;
5. disabled-user, expired-session, and revoked-grant evaluation; and
6. separation of human and system actor credentials.

`READY_FOR_PERSISTENCE_DESIGN` is false until an owning identity contract can
supply and retain those facts. `REVIEW_CAPTURE_PREREQUISITE_REQUIRED` is not
selected because this document defines the review-capture contract; it becomes
implementable after identity. `PRODUCT_SCOPE_DECISION_REQUIRED` is not
selected because the bounded MVP is decided. `STOP_M33_AFTER_DESIGN` is not
selected because direct prospective approval has a coherent non-executing
product boundary, subject to the identity gate.

The identity prerequisite must be resolved without weakening actor certainty
to a username string, shared token, current workspace owner, or operator
assertion. If the product will not adopt stable per-human identity and scoped
authorization, M33 runtime adoption must stop after design.

## 13. Recommended next milestone

**M33.8 - Stable Human Identity and Scoped Authorization Foundation
(design/pure-contract only).**

M33.8 should:

1. name the identity owner/provider and actor namespace;
2. define stable actor, authentication event, session expiry, disabled-user,
   and credential-rotation semantics;
3. define workspace/portfolio permission and grant-source ownership;
4. implement, if approved, frozen ORM-free `ActorRef`,
   `AuthenticationEventRef`, `ActorAuthorityFact`, and typed refusal contracts;
5. define caller-supplied current-status/authorization facts and pure
   validation against the M33.7 command boundary;
6. test shared-credential refusal, actor mismatch, expired authentication,
   revoked/unknown grant, scope mismatch, UTC enforcement, and deterministic
   output; and
7. decide the exact prerequisite exit evidence before any persistence design.

M33.8 should not add a user table, migration, login/API change, token/session
store, frontend, approval endpoint, M33 persistence, certificate/key system,
legacy adapter, backfill, snapshot construction, lifecycle transition, or
runtime authorization wiring. A later persistence-design milestone may begin
only after the identity owner and facts are approved and implementable.

## 14. Explicit stop and non-adoption statement

Stop future M33 adoption if a proposal would:

- retain shared credentials for human approval;
- infer an actor from a display name, current owner, request IP, operator, or
  deployment administrator;
- put editable terms in an approval command;
- derive review content from mutable optimizer/recommendation state;
- make client time authoritative;
- resolve races by latest timestamp, row id, UI hiding, or source priority;
- bypass M33.2 expected-prior-state/sequence or hash validation;
- approve incomplete provenance;
- commit a lifecycle event without the durable internal command/audit facts;
- treat an audit receipt or certificate as execution evidence;
- combine identity, persistence, frontend, legacy conversion, and runtime
  rollout into one approval;
- create a canonical execution plan or use M32 shadow evidence; or
- make approval mutate a transaction or portfolio.

M33.7 does not:

- modify Python, TypeScript, tests, or Graphify output;
- add an ORM model, migration, repository, API, frontend, writer, scheduler,
  job, or persistence store;
- create an actor, authentication event, authority fact, intent, snapshot,
  display receipt, command, transition, or audit receipt;
- change M33.2 hashing, transitions, or idempotency;
- add certificate infrastructure, signing, keys, trust, or revocation;
- read, adapt, backfill, dual-write, quarantine, repair, rank, or mutate legacy
  rows;
- change recommendation, optimizer, decision, shadow, transaction, portfolio,
  ledger, expiry, evaluation, or replay behavior;
- adopt target-value currency semantics or optimizer allocation conversion;
- introduce order, routing, broker, fill, or reconciliation behavior; or
- reopen M32 or adopt canonical execution planning.
