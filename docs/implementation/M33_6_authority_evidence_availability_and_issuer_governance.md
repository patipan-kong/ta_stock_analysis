# M33.6 - Authority Evidence Availability and Issuer Governance Study

**Date:** 2026-07-17

**Status:** Complete. Repository, configured-development-database, deployment,
and operational-evidence study only. No persistence, issuer, capture path,
adapter, or runtime adoption is implemented.

**Milestone decision:** No evidence currently available to this system can
honestly produce `CERTIFIED_EXACT` or `CERTIFIED_PROPOSAL_ONLY` authority for a
historical legacy decision. Existing non-conflicting recommendation material
can seed at most an `UNVERIFIABLE` proposal under explicit policy and fresh
human reconfirmation. Historical exact certification is not supported. For new
decisions, the preferred product path is direct fresh M33.2 approval of a
predetermined frozen snapshot, not a certificate layer. M33 is therefore
`PROSPECTIVE_CAPTURE_DESIGN_REQUIRED` and is not ready for authority or
reconfirmation persistence.

## 1. Authoritative boundary

The governing inputs are:

- `docs/implementation/M33_1_execution_intent_snapshot_lifecycle_foundation.md`;
- `docs/implementation/M33_2_pure_execution_intent_contracts.md`;
- `docs/implementation/M33_3_legacy_adapter_feasibility.md`;
- `docs/implementation/M33_4_historical_authority_certification_contract.md`;
- `docs/implementation/M33_5_pure_authority_verification_contracts.md`;
- `docs/implementation/M32_EPIC_CLOSEOUT.md`; and
- the M33 entries in `docs/engineering/DECISION_LOG.md`.

All predecessor boundaries remain in force:

- M32 remains closed and canonical execution planning remains NO-GO.
- Persisted legacy rows alone still contain zero safely `EXACT_ADAPTABLE`
  cases.
- M33.5 authority levels and evidence requirements are not weakened to make a
  current source fit.
- Recommendation output, optimizer history, shadows, transactions, current
  holdings, and matching values do not become proof of human acceptance.
- Approval remains non-executing and does not create a transaction, order,
  fill, ledger fact, or portfolio mutation.
- This study adds no code, model, migration, repository, API, certificate,
  trust store, key, signature operation, writer, adapter, quarantine workflow,
  frontend, background job, snapshot, lifecycle transition, or Graphify
  change.

“Exists now” means evidenced by repository source/configuration, repository
artifacts, or an aggregate read-only inspection of the configured development
database on 2026-07-17. It does not claim that an undocumented external log,
backup, or operator artifact does not exist somewhere else. Such an artifact
has no authority until it is produced and verified under M33.5.

## 2. Verification scope and current database facts

The review traced the current optimizer response and snapshot writer, the
frontend display and decision-confirmation path, authentication middleware,
workspace/portfolio checks, ORM schema and live development schema, decision
and expiry writers, shadow and transaction linkage, API client, deployment
configuration, synchronization tooling, repository backups, and M33.5 pure
verification/reconfirmation contracts and tests.

Aggregate read-only inspection of the configured development PostgreSQL
database found:

| Fact | Verified count |
| --- | ---: |
| Workspaces | 1 |
| Optimizer-history rows | 94 |
| Recommendation snapshots | 77 |
| Recommendation snapshots with missing projected allocations | 0 |
| Legacy execution decisions | 77 |
| Decisions with non-null `approved_allocations_json` | **0** |
| Duplicate-decision snapshot groups currently present | 0 |
| `APPROVED` / `REJECTED` / `EXPIRED` / `MANUAL_OVERRIDE` decisions | 21 / 34 / 19 / 3 |
| Shadow portfolios | 68 |
| Transactions | 56 |
| Transactions with `execution_decision_id` | **0** |

The absence of a duplicate group today does not create a uniqueness or
lineage invariant: the schema and endpoint still allow duplicates. The live
schema has 33 tables. Searching table identities for audit, request, session,
authentication, certificate, archive, backup, log, or event concepts found
only `user_execution_decisions` and unrelated `user_usage`; there is no
authority-evidence or approval-event store.

## 3. Verified evidence-source matrix

The matrix distinguishes facts that exist, facts that can be captured later,
and facts permanently absent from the currently persisted historical rows.
“Exact bytes” means the exact canonical payload displayed to or accepted by the
human, not a later JSON serialization of similar data.

| Evidence source | Exists now and production path | Storage / mutability / retention | Schema and evidence quality | M33.5 roles and maximum honest use |
| --- | --- | --- | --- | --- |
| `OptimizerHistory.result_json` | Yes. `POST /analyze/optimizer` inserts one row after optimizer completion. 94 configured-development rows exist. | Database row; no normal update endpoint, but no content digest, immutability enforcement, or documented retention/backup guarantee. Local-to-VPS sync may upsert it, with local winning. | Unversioned result JSON; naive `TIMESTAMP`; workspace and portfolio ids are present. No actor, approval act, displayed-byte capture, accepted-byte capture, tamper evidence, or independent verification. | Candidate origin and upstream recommendation context only. May contribute a proposal input under explicit policy; cannot satisfy `REVIEWED_PAYLOAD`, `APPROVED_PAYLOAD`, actor, or authority roles. |
| `RecommendationSnapshot` | Yes. Written from optimizer result after history commit. 77 rows exist and all currently contain projected allocations. | Database row linked one-to-one to optimizer history; cascade deletion remains possible; a maintenance endpoint can backfill missing allocations. Sync tooling may upsert it. No frozen digest or retention contract. | Selected unversioned JSON fields; writer uses ordinary `json.dumps(default=str)`. Scope is recorded but not cryptographically bound. `created_at` is naive `TIMESTAMP`. | `RECOMMENDATION_LINK`, candidate content, and partial scope only. `LEGACY_RECOMMENDATION_CANDIDATE` may seed an `UNVERIFIABLE` proposal with warnings. Never accepted terms. |
| Frontend-displayed optimizer terms | A React view displays `target_allocations` and derives a display-only execution plan from recommendation data. | Browser render state only. No displayed-payload record, canonical display schema, digest, screenshot, DOM archive, or retention. A historical rerender may differ with code/version or ancillary inputs. | The view joins and formats recommendation fields; it is not a frozen M33.2 snapshot. Actor and event time are absent. Exact historical display bytes are permanently absent from current persisted rows. | None as historical authority. Prospectively it could satisfy `REVIEWED_PAYLOAD` only if the exact frozen canonical payload and display receipt are captured before approval. |
| Submitted optimizer-decision request body | The frontend submits decision, notes, shadow flag, and optional override labels. It does **not** submit `approved_allocations`. | Transient HTTP body. The endpoint stores selected fields only; no request archive or immutable body capture exists. | Pydantic outer shape only; no canonical request version, digest, request id, actor identity, or accepted-payload binding. | Current requests can establish only that a decision label reached the endpoint. They cannot satisfy `APPROVED_PAYLOAD` or exact review binding. Prospectively a redesigned request could carry an expected frozen snapshot id/hash, not editable accepted terms. |
| JWT authentication/session | Yes. Login issues a 30-day HS256 token with `sub=username`; the browser stores the token in `localStorage`. | Token exists client-side; no session table, authentication-event record, key id, rotation record, or historical session retention. | Middleware verifies only validity and returns a boolean. It discards the subject and passes no actor to endpoints. One environment-configured credential is used; there is no stable user/role/grant model. | Cannot satisfy historical `ACTOR_IDENTITY` or `ACTOR_AUTHORITY`. Prospectively a stable user identity and authenticated event may contribute actor evidence after redesign. |
| Workspace and portfolio authorization | Requests resolve one default workspace. Many portfolio endpoints filter portfolio by that workspace. The decision endpoint filters the recommendation by workspace but accepts the request portfolio id without proving it equals the recommendation portfolio. | Workspace/portfolio rows in the database; authorization grants are not separately recorded or versioned. | Single-user convention, not actor-scoped authorization. Scope fields can be compared but do not prove the human's authority at event time. | Partial `SCOPE` candidate only. Cannot satisfy `ACTOR_AUTHORITY`. A future exact flow must authorize the actor against the exact scope at approval time and retain the grant fact. |
| `UserExecutionDecision` | Yes. 77 rows exist; all have null approved allocations. Expiry writer creates system `EXPIRED` rows. | Append-only by normal writer convention, but no uniqueness, correction lineage, content digest, or deletion-independent retention. Workspace/portfolio cascades can remove rows. | Decision label and optional notes/override metadata; no actor id. `executed_at` and `created_at` are naive `TIMESTAMP`s assigned at recording, not proof of execution or exact approval time. | `DECISION_LINK` and legacy classification only. Non-conflicting human-looking rows remain `UNVERIFIABLE`; `REJECTED`/`EXPIRED` are `OUT_OF_SCOPE`; duplicate/conflicting/scope-invalid groups are `CONFLICTING`. |
| Application logs | Ordinary Python logging calls exist for startup, optimizer, decision-shadow failures, and background work. Uvicorn/PM2 may emit process/access output. | No repository log sink, request-body logger, append-only store, retention policy, rotation policy, digest chain, or evidence export. No repository `.log` files were found. | Messages are free-form and code-version dependent. Decision success does not log exact request bytes, actor, displayed terms, accepted terms, or target snapshot hash. | Operational diagnostics only. Cannot currently satisfy an M33.5 authority role. A future trusted audit subsystem is a different source, not an upgrade of these logs by assertion. |
| Reverse-proxy / hosting access logs | The repository shows Vercel frontend configuration and a PM2 backend process bound to localhost. No reverse-proxy configuration is present. Hosting platforms may possess external access logs, but none was available or governed here. | External and unverified. Retention, mutability, request-body coverage, actor binding, timestamp semantics, and independent access are not specified in the repository. | At best ordinary method/path/status/client metadata. No evidence that exact request bodies or displayed payloads are retained. | No current M33.5 role. If an external archive is later produced, it must be assessed as new evidence; access logs alone still do not prove displayed/accepted terms. |
| Dedicated audit log | No audit/event table, append-only audit service, or signed event stream exists in source, configuration, or the configured database schema. | Absent. | Historical exact audit facts are not recoverable from current rows. | None now. Prospectively a trusted audit subsystem could supply all evidence roles it directly captures, subject to trust, signature, and revocation governance. |
| `Transaction` and `execution_decision_id` | 56 transactions exist; zero currently carry the optional decision link. | Economic ledger row; separate transaction workflow. Link is nullable metadata and not semantically checked for decision state/scope/terms. | Transaction amount/time/symbol fields do not encode reviewed intent. Timestamps are naive. | Prohibited authority/proposal origin under M33.5. Cannot fill terms, actor, approval, or fulfillment authority. |
| `ShadowPortfolio` and shadow snapshots | 68 shadow portfolios exist. Recommendation-, decision-, and holdings-fallback sources are heterogeneous; active shadows and daily values are mutable/regenerable. | Database projections; repository contains two shadow-regeneration backup exports. No immutable approval binding. | Simulated holdings and valuation dates; no actor, accepted terms, or independent evidence. | Prohibited authority and proposal origin. Must never satisfy any M33.5 approval role. |
| Request/correlation identity | No decision request id, idempotency key, correlation header, middleware-generated request identity, or persisted trace id exists on the path. | Absent. | Historical request-to-row/display binding cannot be reconstructed uniquely. | None now. A future approval event requires a unique request/command and audit correlation identity. |
| Time and timezone evidence | Writers use naive `datetime.utcnow()`; expiry also uses local `date.today()`. APIs commonly append `Z` when serializing stored naive values. PostgreSQL columns are `TIMESTAMP` without timezone. | Database timestamps exist but timezone semantics are not schema-bound and event versus knowledge time is not separated for approvals. | Insufficient for exact UTC authority. Later adding `Z` does not prove the original timezone contract. | Candidate ordering hint only; cannot satisfy exact `EVENT_TIME`. Existing rows remain timezone-unverifiable. |
| Repository backup exports | Six JSON exports were found: four portfolio-rebuild backups and two shadow-regeneration backups. | Manually produced local files; no documented global retention, signing, immutable archive, or independent custody. | Contain portfolio/items/snapshots/repairs or shadow/snapshot/attribution data. They do not contain decision requests, actors, displayed terms, or approval bindings. | No authority role. Shadow backup content remains prohibited evidence. |
| Local-to-VPS synchronization | Tooling syncs computed market/snapshot/analytics data and may upsert optimizer history and recommendation snapshots. It explicitly blocks `user_execution_decisions`, transactions, portfolios, and user-specific tables. | Mutable replication with source-wins upserts; not an immutable archive. | Preserves some candidate recommendation data, not decision or actor evidence. | Proposal-origin availability only. Cannot independently verify historical approval. |
| External AI/provider records | AI provider/model names and generated optimizer output may be stored; provider-side request records are not integrated as authority evidence. | External retention is not specified or verified. | They concern recommendation production, not human display, actor, authorization, or acceptance. | At most upstream recommendation provenance if later verified. Never approval authority. |
| Manual operational records | Repository documents and Decision Log entries record engineering decisions; no operator approval journal for user decisions was found. | Human-authored mutable repository text with code-review history, not a signed per-approval archive. | Can identify current engineering intent, not historical end-user approval facts. | `MANUAL_OPERATOR_STATEMENT` at most: warning/proposal context only. Cannot certify historical exactness. |

## 4. Evidence availability classifications

### 4.1 Exists now

The system currently retains recommendation candidates, optimizer context,
legacy decision labels, partial scope fields, naive record times, shadow
diagnostics, and transaction facts. These are useful for evaluation and for
forming a visibly non-authoritative proposal. They do not collectively prove
an approval: combining multiple insufficient sources does not create the
missing displayed bytes, actor, authority, event time, or target binding.

### 4.2 Could be captured prospectively

The current application could be extended in a later approved milestone to
capture a stable actor, actor-scoped authorization, a frozen M33.2 snapshot,
canonical displayed content, snapshot id/hash acknowledgement, UTC event and
knowledge times, unique command/correlation identity, and an immutable approval
event. A trusted audit or certificate envelope could also be issued after the
fact from those captured facts, but the certificate is optional; it does not
make the underlying direct approval more authoritative.

### 4.3 Permanently absent for current historical rows

Absent an independently retained external artifact not evidenced by this
study, the following facts cannot be recovered from current rows:

- exact canonical bytes displayed to the human;
- a digest recorded at display time;
- exact accepted payload bytes or an acknowledgement of a frozen snapshot;
- stable approving-human identity;
- actor authority for the exact workspace/portfolio at the decision time;
- a timezone-aware approval occurrence time and separate knowledge time;
- request/idempotency/correlation identity joining display, act, and row;
- predetermined M33.2 intent id, snapshot id, and content hash; and
- immutable decision lineage and historical revocation/status evidence.

A later digest of current database values proves only the later values. It
cannot be backdated into proof that those bytes were displayed or approved.

### 4.4 Proposal/reconfirmation-only evidence

`RecommendationSnapshot.projected_allocations_json` and, under an explicit
policy, `OptimizerHistory.result_json` may seed a proposal. Their use must
retain `LEGACY_RECONSTRUCTED`/`INCOMPLETE` authority, display warnings, require
explicit term editing where legacy actions/units are not lossless, reconfirm
scope, mint new ids, and obtain a fresh approval against a newly frozen M33.2
snapshot. Legacy decision labels and notes may be shown as context only.

## 5. Authority-level feasibility matrix

| Realistic evidence combination | Maximum honest M33.5 result | Proposal? | Historical approval recreation? | Reason |
| --- | --- | --- | --- | --- |
| Current `APPROVED` decision + recommendation snapshot + optimizer history | `UNVERIFIABLE` | Conditional under explicit policy and only when candidate terms are complete/non-conflicting | No | No decision-owned terms, actor, authority, exact display, UTC event, immutable target id/hash, issuer, trust, signature, or revocation status. |
| Current `MANUAL_OVERRIDE` + notes/labels + recommendation | `UNVERIFIABLE`, often edit-required | Conditional warning-rich proposal | No | Override metadata is not complete accepted terms; action/unit interpretation requires current human editing. |
| Current `REJECTED` or `EXPIRED` decision with any repository evidence | `OUT_OF_SCOPE` | No | No | M33.5 deterministic precedence forbids intent/proposal creation for these acts. |
| Duplicate, conflicting, scope-mismatched, or ambiguous decision/source facts | `CONFLICTING` | No automatic proposal | No | No latest-row, timestamp, or source-priority heuristic is approved. |
| Recommendation snapshot alone | `UNVERIFIABLE` | Conditional recommendation-only proposal with mandatory warnings | No | Recommended output is not acceptance. |
| Transaction and/or shadow values matching recommendation | `UNVERIFIABLE` with prohibited evidence, or `CONFLICTING` when mixed into an authority claim | No from those origins | No | M33.5 structurally prohibits transaction/shadow authority and proposal origins. |
| Ordinary application/access logs, if later retrieved | `UNVERIFIABLE` | Only if an independently permissible complete candidate exists | No | No demonstrated body/display capture, stable actor, authorization, immutability, trust policy, or tamper evidence. |
| Current repository backup/sync artifacts | `UNVERIFIABLE` | Recommendation candidate only where present | No | They exclude decisions or contain prohibited shadow data and are neither signed nor independently governed. |
| Future trusted archive proving candidate bytes and scope but missing historical actor/approval binding | `CERTIFIED_PROPOSAL_ONLY` | Yes, fresh reconfirmation mandatory | No | This is the first realistic use of the certificate tier, but no such archive exists today. |
| Future complete prospective approval capture, then valid certificate/trust/revocation facts | `CERTIFIED_EXACT` | Optional | Technically yes for the exact bound target | Possible only for newly captured events after all M33.5 requirements and governance are active. |
| Future direct M33.2 approval of a frozen snapshot without certificate | Outside the historical-certificate classification; authoritative current M33.2 approval | No legacy proposal needed | Not a historical recreation | Preferred product path. The human directly approves the exact current snapshot rather than certifying a legacy act. |

### 5.1 Historical conclusion

There are **zero currently persisted historical cases that can reach
`CERTIFIED_EXACT`**. There are also zero current cases that reach
`CERTIFIED_PROPOSAL_ONLY`, because no certificate issuer, signature, trust
policy, verified payload archive, or revocation status exists. The current
counts do not create an exception: even the 21 `APPROVED` rows have no approved
allocation payload and no actor.

Historical approval recreation has little product value here. Legacy approval
was non-executing, historical recommendations may be stale, and downstream
transactions are not bound to them. Recreating an `APPROVED` state would add
complexity and perceived authority without changing economic truth. Evaluation
may continue to read the legacy decision as a legacy fact; any current action
should begin with fresh reconfirmation.

### 5.2 Prospective conclusion

A prospective flow **could** satisfy the factual requirements for exact
authority, but the current flow cannot. It would need new identity,
authorization, freezing, display, event, and audit capture before the first
qualifying approval. Even after that work, a certificate is not necessary for
ordinary in-system approval: M33.2 already binds a verified human act to an
exact snapshot id and content hash. A certificate adds value only when a
separate trust domain must verify or transport that fact.

## 6. Issuer-governance model

No issuer kind is trusted by name. Every issuer requires a stable namespace,
versioned trust policy, controlled signing identity, known revocation status,
and evidence showing that it directly observed the fact it certifies.

| Possible issuer | May certify | Must never certify | Independence / required governance | Historical exact suitability |
| --- | --- | --- | --- | --- |
| Current application backend | Prospectively observed frozen snapshot identity/hash, authenticated actor presented by a future identity layer, authorization result, server receipt time, and accepted command. | Historical display or approval facts inferred from mutable rows; actor identity discarded by current middleware; client display it did not observe; transaction/shadow evidence as intent. | Issuer namespace must include environment/deployment. Keys must not be embedded in source or app config; security owner controls custody/rotation, product/security jointly own trust policy, and an independent revocation publisher/auditor reviews issuance. Backend deployers must not unilaterally rewrite past claims. | **No** for existing history. Conditional for prospective facts only after capture redesign and governance. |
| Dedicated certification service | A complete evidence bundle received through an authenticated, idempotent, versioned protocol; certificate issuance time and target binding. | Missing facts, legacy-row interpretations, or assertions that source systems did not capture. | Separate service identity/namespace; isolated signing keys (prefer managed HSM/KMS), scheduled and incident-driven rotation, two-person policy changes, independent revocation channel, append-only issuance audit, reproducible verification, and disaster-recovery testing. | No unless a pre-existing independently authoritative archive supplies every historical fact. Strong prospective option if cross-system certification is justified. |
| Trusted audit subsystem | Events it directly and immutably captured: display receipt, frozen payload digest, actor/auth decision, scope, approval command, UTC times, and correlation. | Product semantics inferred after capture, mutable table snapshots presented as original events, or facts outside its instrumentation. | Operationally and logically separated write path; append-only/tamper-evident storage; restricted readers; independently owned verification keys; retention and export policy; continuous completeness/gap monitoring; revocation and compromise playbook. | No current subsystem exists. A future subsystem could support prospective exact certification. |
| External signed archive | Exact archived bytes, archive receipt time, signer identity, and integrity/retention facts within its contract. | Application actor authority or acceptance semantics unless explicitly captured and independently bound at the event. | External namespace and contract; verified key history, rotation, revocation and availability SLA; exportability; legal/operational ownership; independent evidence that the archive was active at the event. | Only if an archive predating the decision is produced and complete. None is evidenced here. |
| Human operator | Current manual input, current warning acknowledgement, current reconfirmation, or an observation that a case needs review. | Historical exact payload, historical actor, historical authority, or backdated approval based on inspection of current rows. | Stable current operator identity, least-privilege role, two-person review for exceptional claims, audit of every action, and no access to issuer signing keys. | **Never sufficient** for historical exact certification by itself. |
| Deployment administrator | Deployment/environment identity, code/config version, service availability, key activation/retirement action, or incident declaration. | End-user approval, reviewed terms, actor authority, or correctness of application-level evidence. | Separate from product approval and issuer-policy owners; break-glass controls; immutable admin audit; key access split from application/database administration; mandatory incident reporting. | **No.** Administrative control is not independent evidence of a user's historical act. |

### 6.1 Ownership and separation of duties

If certificates are ever introduced, governance must name at least these
separate responsibilities:

1. **Product authority owner** defines which event semantics may be certified.
2. **Identity/authorization owner** defines stable actor and historical grant
   evidence.
3. **Trust-policy owner** versions accepted issuer kinds, algorithms, keys,
   environments, and verification rules.
4. **Key custodian** provisions, rotates, suspends, and destroys signing keys
   without editing product evidence.
5. **Issuer operator** runs issuance but cannot change trust policy or grant
   itself historical facts.
6. **Revocation authority** publishes independently verifiable append-only
   status, including emergency suspension.
7. **Audit/review owner** reconciles source events, issued certificates,
   failures, gaps, and policy changes.
8. **Incident commander** can halt issuance and publish compromise status but
   cannot delete evidence or silently repair certificates.

Key rotation must preserve verification of earlier certificates through a
versioned key history. Compromise response must stop issuance, revoke or
suspend affected key/certificate ranges, preserve evidence, identify affected
consumers, and require explicit correction policy. Reissuing a certificate
does not erase the compromised claim.

### 6.2 Current issuer conclusion

No current application component is independent or complete enough to certify
historical exact claims. A service that reads `RecommendationSnapshot` and
`UserExecutionDecision` would merely sign mutable, incomplete legacy values;
its signature would prove who signed the later statement, not what the human
historically reviewed or approved.

## 7. Minimum prospective capture requirements

This section describes facts and ordering only. It does not design tables,
repositories, keys, or runtime wiring.

### 7.1 Before display

The system must establish:

- a stable current human actor identity from an approved identity provider;
- the actor's authorization for the exact workspace and portfolio;
- a unique request/session and correlation identity;
- exact environment and authority namespace;
- caller-supplied new intent and snapshot ids;
- complete M33.2 terms, intent kind, scope, provenance, effective time, and
  expiry inputs; and
- a successful M33.2 snapshot build producing the predetermined content hash.

No approval button may refer to mutable optimizer result state. The frozen
snapshot is the display subject.

### 7.2 When terms are frozen and displayed

Capture:

- the exact canonical M33.2 snapshot content and content hash;
- the exact snapshot and intent ids;
- a versioned display-payload schema derived from that frozen snapshot;
- exact canonical displayed payload bytes and digest;
- all provenance and visible warnings;
- the workspace/portfolio and actor for which the display is authorized;
- UTC display occurrence and knowledge times; and
- an immutable display receipt joined by correlation identity.

Formatting-only UI state may remain outside authority, but every semantically
reviewed field must be in the canonical displayed payload. If a term changes,
the prior display receipt is stale and a new snapshot/display is required.

### 7.3 At human approval

Capture atomically or under one idempotent command boundary:

- exact actor identity and a fresh authorization decision for the scope;
- expected intent id, snapshot id, and M33.2 content hash;
- expected displayed-payload digest;
- accepted-payload digest, normally identical to the displayed digest;
- explicit human action, not silence or a system default;
- UTC occurrence time from the authority boundary and knowledge/recording
  time;
- command idempotency key and request/correlation identity;
- immutable approval event and deterministic transition result; and
- evidence that no stale snapshot/display was substituted.

Editing in the approval request is prohibited. An edit creates a new snapshot,
new content hash, new display receipt, and new approval opportunity.

### 7.4 After approval

The system may produce:

- a durable append-only audit receipt for the direct M33.2 approval;
- independent monitoring that detects missing, duplicate, conflicting, or
  out-of-order events;
- optional certificate issuance over the already complete evidence package;
- trust and revocation status under a named policy; and
- export/verification material for a separate relying system.

Certificate issuance must not be on the critical path unless a concrete
external relying party requires it. Issuance failure must not silently convert
or restate the direct approval.

### 7.5 Facts that must never be inferred later

- displayed or accepted bytes;
- actor identity or authorization;
- workspace/portfolio scope;
- approval occurrence time or timezone;
- intent/snapshot identity and content hash;
- payload relationship;
- request/correlation/idempotency identity;
- issuer trust or revocation status; and
- decision lineage.

Recommendation equality, a matching transaction, a shadow holding, a later
database digest, a current account owner, or an operator statement cannot fill
any of these facts.

## 8. Historical-versus-prospective product policy

The requested policy options are resolved differently by time horizon.

### 8.1 Historical records: choose B

**B. Support historical proposal/reconfirmation only.**

- Do not support historical exact certification from current sources.
- Do not search for value by importing a legacy `APPROVED` state.
- Permit an opt-in warning-rich proposal only for complete, non-conflicting,
  permitted recommendation candidates.
- Require explicit current-human editing/review, new ids, a new frozen M33.2
  snapshot, `PENDING_REVIEW`, and a separate fresh approval.
- Keep rejected and expired decisions out of scope.
- Keep conflicting or scope-ambiguous cases out of automatic proposal flows.

Fresh reconfirmation is the **exclusive authority path** for existing rows.
Legacy decisions remain useful evaluation facts, but they do not become M33
approval history.

### 8.2 Prospective records: choose D initially

**D. Do not introduce certificates and use fresh M33.2 approval directly.**

The direct flow already provides the product fact that matters: a verified
human approved one exact frozen snapshot id and hash. Building issuer keys,
trust policy, revocation, certificate retention, and incident operations adds
substantial security and governance cost without a current relying party.

Option C, prospective certification only, remains a later conditional choice
if a real need appears, such as cross-system verification, regulated evidence
export, offline third-party validation, or trust-domain separation. If chosen,
certificates must be derived from the direct prospective capture in section 7;
they must not replace it.

Option A, historical exact certification, is rejected for the evidence
currently available.

## 9. Persistence-readiness decision

**Decision: `PROSPECTIVE_CAPTURE_DESIGN_REQUIRED`.**

M33 must not proceed next to authority-certificate persistence or a general
legacy adapter. The evidence supporting this result is:

1. zero current decision rows contain approved allocations;
2. no decision row contains a human actor;
3. authentication identity and authorization are not propagated or retained;
4. the frontend does not freeze or submit the reviewed/accepted terms;
5. timestamps are naive and no approval event/correlation identity exists;
6. no audit/archive/certificate/trust/revocation infrastructure exists;
7. current backups, sync, transactions, and shadows cannot supply the missing
   authority; and
8. direct fresh M33.2 approval is likely sufficient for the product, leaving
   certificate persistence without a demonstrated consumer.

`READY_FOR_AUTHORITY_PERSISTENCE` is therefore false. A table would preserve
empty or manufactured authority, not solve evidence capture.

`READY_FOR_RECONFIRMATION_PERSISTENCE_ONLY` is also premature. The pure M33.5
proposal boundary is sound, but the current application still lacks the stable
actor/authorization and frozen display/approval boundary required to turn a
proposal into an authoritative current snapshot safely.

`NO_PERSISTENCE_JUSTIFIED` applies specifically to certificate persistence at
this time. It does not preclude later M33.2 intent/lifecycle persistence after
the prospective direct-approval design is approved.

## 10. Explicit stop conditions

Stop M33 authority/adaptation work and do not add persistence if any proposed
milestone would:

- weaken an M33.5 exact requirement or downgrade a missing fact to a warning
  merely to make legacy rows pass;
- sign current mutable rows and label the signature historical proof;
- infer displayed/accepted terms from recommendation, optimizer, shadow,
  transaction, holdings, notes, or current UI output;
- infer historical actor or authority from the current shared credential,
  current owner, deployment administrator, or operator statement;
- treat naive timestamps or appended `Z` text as certified UTC event time;
- select a winner among duplicate/conflicting facts by timestamp, row id,
  majority, or source priority;
- create a proposal from rejected, expired, shadow, transaction, holdings, or
  canonical-plan inputs;
- add certificate persistence without a named relying party, trust-policy
  owner, key custodian, revocation authority, and incident process;
- combine capture, persistence, adapter, legacy backfill, and runtime adoption
  into one approval; or
- reopen M32 or treat canonical execution planning as adopted.

If prospective product discovery shows no need for persisted intent lifecycle
beyond the existing legacy decision/evaluation workflow, stop M33 after the
pure foundation rather than adding tables for architectural completeness.

## 11. Recommended next milestone

**M33.7 - Prospective Human Authority and Direct Approval Capture Design
(design-only).**

M33.7 should design, but not implement:

1. stable human identity and workspace/portfolio authorization at event time;
2. the direct M33.2 flow from complete terms to predetermined ids/hash,
   canonical display, explicit approval, and append-only event;
3. event-time versus knowledge-time and UTC ownership;
4. request, idempotency, correlation, stale-display, and concurrency rules;
5. atomicity boundaries among snapshot persistence, `PENDING_REVIEW`, and
   approval without collapsing their semantics;
6. minimum audit receipt and retention needed for the application itself;
7. a product-value decision for opt-in historical proposal/reconfirmation;
8. explicit persistence entities and constraints only after those facts are
   settled; and
9. a documented trigger for revisiting prospective certificates, with a named
   external relying party or compliance requirement.

M33.7 should add no ORM model, migration, endpoint, frontend, writer, key,
certificate, adapter, backfill, production quarantine, snapshot construction,
lifecycle transition, or runtime integration. If stable actor/authorization
cannot be specified without a broader identity/workspace program, M33.7 should
stop and hand that prerequisite to its owning domain.

## 12. Explicit non-adoption statement

M33.6 changes no application behavior or data. It does not:

- add or modify Python/TypeScript code or tests;
- add an ORM model, migration, repository, API, frontend, writer, scheduler,
  background job, or persistence store;
- perform signing, signature verification, key retrieval, key storage,
  certificate issuance, or revocation publication;
- create a proposal, snapshot, lifecycle event, approval, or quarantine row;
- adapt, backfill, dual-write, repair, rank, delete, or mutate legacy data;
- change authentication, authorization, recommendation, decision, expiry,
  shadow, transaction, portfolio, ledger, evaluation, or replay behavior;
- introduce a historical authority claim;
- change Graphify output; or
- reopen M32 or adopt canonical execution planning.
