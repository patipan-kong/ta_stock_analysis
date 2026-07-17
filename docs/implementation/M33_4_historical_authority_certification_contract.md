# M33.4 - Historical Authority Certification and Reconfirmation Contract

**Date:** 2026-07-17

**Status:** Design complete. Authority and reconfirmation contracts only. No
pure implementation, persistence, legacy adaptation, or runtime adoption.

**Milestone decision:** Historical approval may be recreated only when a
trusted, unrevoked, versioned `AuthorityCertificate` proves the exact reviewed
and approved payloads, historical human actor and authority, immutable scope,
unambiguous lineage, UTC event time, and a binding to the predetermined M33.2
`snapshot_id` and `content_hash`. Every lesser case either produces a visibly
non-authoritative pre-snapshot proposal requiring fresh human reconfirmation,
is quarantined, or is out of scope. Certification determines eligibility; it
does not construct a snapshot, append a transition, or perform adaptation.

## 1. Authoritative boundary

The governing inputs are:

- `docs/implementation/M33_1_execution_intent_snapshot_lifecycle_foundation.md`;
- `docs/implementation/M33_2_pure_execution_intent_contracts.md`;
- `docs/implementation/M33_3_legacy_adapter_feasibility.md`; and
- `docs/implementation/M32_EPIC_CLOSEOUT.md`.

All existing boundaries remain in force:

- M32 remains closed and canonical execution planning remains NO-GO.
- M33.3's conclusion remains unchanged: persisted legacy rows alone contain
  zero safely `EXACT_ADAPTABLE` cases.
- Approval is a human authorization of one exact snapshot id and content hash;
  it is not execution, transaction admission, fulfillment, or portfolio
  mutation.
- Recommendation, optimizer history, legacy decision, intent, shadow,
  transaction, and replay authority remain separate.
- A certificate cannot promote M32 shadow evidence, recommendation defaults,
  transaction linkage, or portfolio state into accepted terms.
- This milestone adds no code, ORM model, migration, repository, API,
  background job, writer, legacy conversion, persistence, or production import.
- Existing recommendation, decision, shadow, transaction, portfolio, ledger,
  expiry, and replay behavior remains unchanged.

M33.4 defines what a future pure verifier must require. It does not assert that
any certificate, audit archive, trusted issuer, signing key, or complete
historical evidence currently exists.

“Quarantine” in this document is a verification/classification disposition.
It does not construct an `ExecutionIntentSnapshot` or append a lifecycle
`QUARANTINED` event.

## 2. Authority invariants

The authority model is governed by these invariants:

1. Authority is proved by evidence; it is never inferred from a label, row
   order, timestamp proximity, matching symbols, or downstream activity.
2. A certificate is an immutable claim envelope, not self-authenticating
   truth. Issuer trust, signature verification, and revocation status are
   caller-supplied verification inputs under a versioned trust policy.
3. Exact adaptation requires exact bytes under a named canonical payload
   schema. A digest of an unspecified or heuristically normalized payload is
   not exact evidence.
4. Historical approval requires a verified human actor and verified authority
   for the exact workspace and portfolio at the historical event time.
5. Historical approval recreation additionally requires a certificate binding
   to the new snapshot's predetermined identity and M33.2 content hash. Terms
   equivalence without that target binding is proposal-only.
6. A certificate never calls `build_execution_intent_snapshot()` or
   `validate_transition()`. It returns eligibility data only.
7. Missing evidence remains missing. Combining several insufficient sources
   does not make them authoritative unless a trusted evidence source actually
   proves the missing fact.
8. Conflicts fail closed. No latest-wins, majority, source-priority, or manual
   override heuristic resolves competing historical authority.
9. Revocation is append-only status evidence. It never edits a certificate or
   silently deletes an already-recorded lifecycle fact.
10. Fresh reconfirmation creates new identity, content, actor, and timeline
    facts. It never impersonates or repairs historical approval.

## 3. Versioned authority model

The names below specify future frozen, ORM-free data contracts. M33.4 does not
implement them.

### 3.1 `AuthorityCertificate`

`AuthorityCertificate` is the immutable signed envelope evaluated by a future
pure verifier.

| Field | Required? | Semantics |
| --- | --- | --- |
| `contract_version` | yes | Authority-certificate grammar version. Unknown versions fail closed. |
| `certificate_id` | yes | Caller-supplied opaque identity in the issuer namespace; never derived from mutable row ids or content. |
| `issuer` | yes | One `AuthorityIssuer`. |
| `issued_at` | yes | Timezone-aware UTC knowledge time at which the certificate was issued. |
| `evidence` | yes | Non-empty immutable collection of `AuthorityEvidence`. |
| `binding` | yes | One `AuthorityBinding` describing the claim being certified. |
| `scope` | yes | One exact `AuthorityScope`. |
| `completeness_claim` | yes | Issuer's `AuthorityCompleteness` claim; verification may downgrade but never upgrade it without evidence. |
| `supersedes_certificate_id` | no | Prior certificate replaced by this one; it does not erase or implicitly revoke the prior certificate. |
| `certificate_digest` | yes | Deterministic digest of the versioned canonical signed content, excluding this field and the signature bytes. |
| `signature` | yes | Signature bytes plus declared algorithm/key reference; cryptographic verification is an input to the pure verifier. |

`certificate_id` is immutable. Reuse of the same id with a different
`certificate_digest` is `CONFLICTING`; a verifier must not choose one copy.
Different ids that make incompatible claims about the same historical act are
also conflicting unless an independently verified supersession and revocation
chain makes exactly one claim effective.

### 3.2 `AuthorityEvidence`

`AuthorityEvidence` describes one immutable evidence item without claiming
that its kind is sufficient.

| Field | Required? | Semantics |
| --- | --- | --- |
| `evidence_id` | yes | Stable opaque identity within its source/issuer namespace. |
| `evidence_kind` | yes | Typed source kind from the catalogue in section 5. |
| `evidence_roles` | yes | Non-empty set such as `REVIEWED_PAYLOAD`, `APPROVED_PAYLOAD`, `ACTOR_IDENTITY`, `ACTOR_AUTHORITY`, `SCOPE`, `EVENT_TIME`, `RECOMMENDATION_LINK`, or `DECISION_LINK`. |
| `source_local_id` | yes | Exact source reference; it may be an opaque external id. |
| `source_contract_version` | yes | Schema/canonicalization version used to interpret the evidence bytes. |
| `canonical_payload` | role-dependent | Exact canonical payload bytes or an equivalent frozen typed value. Required for `REVIEWED_PAYLOAD` and `APPROVED_PAYLOAD`; a digest or locator alone is insufficient. |
| `source_digest_algorithm` | yes | Approved digest algorithm identifier. M33.4 specifies SHA-256 for version 1. |
| `source_digest` | yes | Lowercase digest of the exact canonical source bytes. |
| `occurred_at` | role-dependent | UTC event time. Required when the evidence proves review, approval, authority, or another historical event. |
| `recorded_at` | yes | UTC knowledge time when the evidence item was captured by its source. |
| `source_timezone` | role-dependent | Named IANA timezone and conversion rule for a legacy local time. Required when a non-UTC source time is interpreted. |
| `source_local_time_text` | no | Original local timestamp text retained for audit; never used without the named conversion rule. |
| `locator` | no | Human/audit retrieval hint. A locator is not included as proof that the target still exists. |

Detached canonical payload bytes may be supplied alongside the certificate,
but they are part of the verification input and must match the evidence digest
exactly. Evidence roles are claims checked by verification; merely labeling a
legacy row `APPROVED_PAYLOAD` does not make it one.

### 3.3 `AuthorityIssuer`

`AuthorityIssuer` identifies who made and signed the certificate claim.

| Field | Required? | Semantics |
| --- | --- | --- |
| `issuer_id` | yes | Stable opaque issuer identity. |
| `issuer_kind` | yes | `TRUSTED_AUDIT_SYSTEM`, `EXTERNAL_SIGNED_ARCHIVE`, `FUTURE_CERTIFICATION_SERVICE`, or `HUMAN_OPERATOR`. |
| `authority_namespace` | yes | Deployment/organization namespace in which issuer identity is meaningful. |
| `trust_policy_version` | yes | Versioned external policy under which the issuer/key may be trusted. |
| `signing_key_id` | yes | Stable key reference used for verification and revocation checks. |
| `signature_algorithm` | yes | Approved algorithm identifier. |

Issuer kind is not trust. The verifier receives the trusted issuer/key set and
signature-verification facts from the caller. A `HUMAN_OPERATOR` statement may
record a proposal origin or warning disposition, but it cannot by itself prove
historical exact terms, historical actor identity, or historical authority.

### 3.4 `AuthorityBinding`

`AuthorityBinding` is the non-heuristic relationship between historical
evidence and the target M33.2 artifact.

| Field | Required for exact? | Semantics |
| --- | --- | --- |
| `reviewed_payload_schema_version` | yes | Canonical schema for the complete payload displayed to the human. |
| `reviewed_payload_digest` | yes | Digest of the complete reviewed payload. |
| `approved_payload_schema_version` | yes | Canonical schema for the complete payload accepted by the human. |
| `approved_payload_digest` | yes | Digest of the complete approved payload. |
| `payload_relationship` | yes | `IDENTICAL` or a separately versioned, evidence-backed lossless transformation. No inferred transformation is allowed. |
| `historical_actor_id` | yes | Stable identity of the human who approved. Shared/session-only identities are insufficient. |
| `historical_actor_authority_ref` | yes | Evidence reference proving authority for the certified scope at approval time. |
| `recommendation_ref` | yes for legacy recommendation cases | Exact legacy recommendation identity and digest. |
| `decision_ref` | yes for legacy decision cases | Exact legacy decision identity and digest. |
| `approval_event_id` | yes | Stable identity of the historical approval act. |
| `approval_occurred_at` | yes | Exact timezone-aware UTC event time. |
| `source_timezone_semantics` | yes when converted | Named timezone, ambiguity rule, and conversion version. |
| `target_intent_id` | yes | Predetermined new opaque intent identity. |
| `target_snapshot_id` | yes | Predetermined new opaque snapshot identity to which approval would bind. |
| `target_content_hash` | yes | Exact M33.2 content hash of the predetermined target snapshot. |

For `IDENTICAL`, the reviewed and approved payload digests must match. A
different digest is accepted only when a named transformation contract proves
lossless equivalence and both original payloads are retained. Version 1
approves no legacy allocation transformation, action mapping, target-unit
normalization, or timezone guess; those remain separately governed inputs.

A certificate missing `target_snapshot_id` or `target_content_hash` may still
prove candidate integrity, but it can never recreate historical approval.

### 3.5 `AuthorityScope`

| Field | Required? | Semantics |
| --- | --- | --- |
| `workspace_id` | yes | Exact immutable workspace scope. |
| `portfolio_id` | yes | Exact immutable portfolio scope. |
| `authority_namespace` | yes | Namespace matching the issuer and actor authority evidence. |
| `environment_id` | no | Deployment/tenant boundary when ids are not globally unique. If supplied anywhere in the evidence chain, it must match everywhere. |

Scope comparison is exact string identity after the source contract's declared
canonicalization. There is no fuzzy id, name, or current-owner matching.

### 3.6 `AuthorityCompleteness`

`AuthorityCompleteness` describes the evidence package, not the issuer's trust:

- `EXACT` - every exact-certification field and evidence role is present;
- `PROPOSAL_ONLY` - candidate origin/content may be verified, but one or more
  historical approval requirements are deliberately absent;
- `INCOMPLETE` - required evidence is missing or invalid;
- `CONFLICTING` - two or more claims cannot simultaneously be true;
- `OUT_OF_SCOPE` - the source act is not accepted intent, including legacy
  `REJECTED` and `EXPIRED` decisions.

An issuer's completeness claim cannot force the verification result. For
example, an `EXACT` claim with a missing actor is verified as `UNVERIFIABLE`.

### 3.7 `AuthorityVerificationResult`

The pure verifier's immutable result contains:

| Field | Semantics |
| --- | --- |
| `verification_contract_version` | Version of deterministic verification rules. |
| `certificate_id`, `certificate_digest` | Exact certificate evaluated, or null when the result records that no certificate was supplied. |
| `authority_level` | One tier from section 4. |
| `reason_codes` | Canonically ordered, non-empty for every non-exact result. |
| `verified_evidence_ids` | Evidence items whose integrity and role were established. |
| `rejected_evidence_ids` | Items ignored/refused, with reasons. |
| `verified_scope` | Exact scope or null. |
| `verified_historical_actor_id` | Exact human actor or null. |
| `verified_approval_occurred_at` | Exact UTC event time or null. |
| `verified_target_snapshot_id` | Exact target identity or null. |
| `verified_target_content_hash` | Exact M33.2 hash or null. |
| `revocation_status` | `NOT_REVOKED`, `REVOKED`, `UNKNOWN`, or `CONFLICTING`. |
| `provenance_completeness` | Required M33.2 provenance classification if a later workflow creates a snapshot. |
| `may_build_exact_snapshot` | Derived capability; true only for `CERTIFIED_EXACT`. |
| `may_build_proposal` | Derived capability subject to proposal eligibility. |
| `requires_reconfirmation` | True for every proposal path. |
| `may_recreate_historical_approval` | True only for `CERTIFIED_EXACT`. |

The result is data, never an exception-based or side-effecting decision. It
does not allocate ids, persist a certificate, build a proposal, construct a
snapshot, or append lifecycle history.

### 3.8 Canonical digest and signature rules

Version 1 uses these deterministic rules:

1. Each payload schema defines its own canonical byte representation. Raw
   legacy JSON cannot be reserialized under guessed semantics and called exact.
2. Authority structures serialize from explicit field lists with sorted keys
   and compact separators; generic dataclass reflection is prohibited.
3. Evidence is sorted by `(evidence_kind, source_local_id, source_digest)`;
   role sets and reason-code sets are lexically sorted.
4. Time values serialize as canonical UTC ISO-8601. Naive values are refused.
   Original local text and named timezone semantics are separately retained.
5. Decimal values use finite, schema-defined fixed-point rendering. Unit
   conversion is not part of serialization.
6. Digests use lowercase `sha256:<64-hex>` form with a domain separator and
   contract version.
7. `certificate_digest` covers the full certificate content except the digest
   field itself and signature bytes. It includes issuer/key references,
   evidence, binding, scope, completeness claim, issue time, and supersession
   reference.
8. The signature covers the certificate domain separator, contract version,
   and `certificate_digest`.
9. M33.2 `content_hash` is computed unchanged by the existing M33.2 contract.
   The certificate copies that exact hash; it does not recompute it under a
   second grammar.

### 3.9 Revocation and certificate status

Revocation is separate immutable signed evidence containing certificate id and
digest, revoking issuer, effective UTC time, reason code, trust-policy version,
and signature-verification fact. A future verifier receives all effective
status evidence with the certificate.

- Effective verified revocation produces `UNVERIFIABLE` with
  `CERTIFICATE_REVOKED` and forbids new adaptation or proposal derivation from
  that certificate.
- Unknown revocation status produces `UNVERIFIABLE` with
  `REVOCATION_STATUS_UNKNOWN` and forbids `CERTIFIED_EXACT`.
- Conflicting status evidence produces `CONFLICTING`.
- Supersession does not imply revocation.
- Revocation does not delete a certificate or retroactively mutate lifecycle
  events. A future audit may flag an already-recorded historical import for
  review under separately approved correction policy.

## 4. Authority levels and capabilities

| Authority level | Exact snapshot? | Proposal? | Reconfirmation? | Recreate historical approval? | Required M33.2 provenance | Historical actor certainty |
| --- | --- | --- | --- | --- | --- | --- |
| `CERTIFIED_EXACT` | Yes, in a later adapter milestone | Optional, unnecessary for the certified target | No for exact import | Yes, only for the bound target snapshot id/hash | `EXACT_FROZEN` for certified sources | Exact verified human identity and authority |
| `CERTIFIED_PROPOSAL_ONLY` | No | Yes, if candidate terms/scope pass proposal validation | Always | No | `LEGACY_RECONSTRUCTED` plus fresh `MANUAL_HUMAN_INPUT` when later frozen | Historical actor may be partial/unknown; current reconfirming actor must be exact |
| `UNVERIFIABLE` | No | Conditional: only complete, non-conflicting, permitted candidate input | Always if a proposal is permitted | No | `INCOMPLETE` before reconfirmation; later legacy source remains `LEGACY_RECONSTRUCTED` | Historical actor unverified; current reconfirming actor must be exact |
| `CONFLICTING` | No | No automatic proposal from conflicting facts | Not applicable; start a separate manual-independent workflow if desired | No | `INCOMPLETE`/conflict finding only | Conflicting or indeterminate |
| `OUT_OF_SCOPE` | No | No | No | No | None | Not applicable |

Mapping to M33.3 is deterministic:

- `CERTIFIED_EXACT` is the only authority level eligible for
  `EXACT_ADAPTABLE`;
- a successful proposal path is `LEGACY_RECONSTRUCTED`;
- `UNVERIFIABLE`, `CONFLICTING`, and `OUT_OF_SCOPE` preserve their M33.3
  fail-closed dispositions; and
- no existing persisted row reaches `CERTIFIED_EXACT` without additional
  authoritative evidence.

## 5. Certification-source evaluation

The table evaluates each source by itself. “Conditional” means only a
tamper-evident, versioned form that explicitly captures the named fact can
contribute evidence; it does not mean the source is known to exist.

| Possible source | Exact reviewed terms | Approved terms | Human identity | Actor authority | Scope | Event time | Historical digest binding | Authority conclusion |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Legacy `UserExecutionDecision` row | No; payload semantics are uncertified | No; label/payload do not prove exact acceptance | No | No | Partial and mismatch-prone | Partial, naive semantics | Current-row digest only, not historical approval binding | Insufficient forever by itself |
| `RecommendationSnapshot` | Recommendation candidate only | No | No | No | Partial | Source time only | Current/source digest possible, not acceptance binding | Proposal origin only; never acceptance proof |
| `OptimizerHistory` | Upstream candidate only | No | No | No | Partial | Run time only | Source digest possible | Proposal origin only under explicit policy |
| `Transaction.execution_decision_id` or transaction row | No | No | No | No | Transaction scope may be known but link is unchecked | Transaction time only | Transaction digest does not bind intent | Metadata/ledger hint only; never intent authority or fulfillment by itself |
| `ShadowPortfolio` or shadow output | No | No | No | No | Heterogeneous supplied scope | Simulation time only | Digest proves only shadow bytes | Prohibited as intent/authority evidence |
| Audit log | Conditional: yes if full canonical payload was immutably captured | Conditional | Conditional | Conditional if grant evidence is captured | Conditional | Conditional with UTC/timezone semantics | Conditional | Can contribute up to exact only when trusted, complete, and independently verified |
| Archived API request payload | Conditional: submitted bytes, not necessarily displayed bytes | Conditional: request may record a decision act | Conditional if authenticated identity is immutable | Usually no without authorization evidence | Conditional | Conditional | Conditional if tamper-evident and versioned | Contributing evidence, never automatically sufficient alone |
| External signed archive | Conditional | Conditional | Conditional | Conditional | Conditional | Conditional | Conditional | May support exact certification if trusted and complete; existence is not assumed |
| Future `AuthorityCertificate` | It can bind proof; it cannot manufacture missing bytes | Same | Same | Same | Same | Same | Yes when canonical/signature rules pass | Exact only when all underlying evidence and target binding pass |
| Manual operator statement | No historical proof | No historical proof | Identifies current operator only | Current operator authority only | May assert current scope | Statement time only | Digest proves statement bytes only | Warning/proposal input only; never historical exact authority by itself |

The following remain insufficient regardless of how closely their values
match: a legacy approval label, recommendation allocations, optimizer output,
shadow holdings, portfolio holdings, transaction linkage, transaction symbols
or quantities, latest-row ordering, notes, and an unsupported manual claim.
Matching is correlation, not authority.

## 6. Reconfirmation contract

Reconfirmation is the only approved route for candidate terms that lack exact
historical authority but are complete enough for fresh review. It creates new
authority rather than reconstructing old authority.

### 6.1 `ProposalCandidate`

`ProposalCandidate` is a pure, immutable pre-snapshot object. It is not an
`ExecutionIntentSnapshot`, lifecycle state, approval, order, or transaction.

Mandatory fields are:

- `proposal_contract_version`;
- new caller-supplied opaque `proposal_candidate_id`;
- `proposal_origin` collection;
- candidate `intent_kind` and complete candidate allocation terms when known;
- exact proposed workspace and portfolio scope;
- `proposal_completeness`;
- canonically ordered `proposal_warnings`;
- legacy source references and digests, labelled with their actual authority;
- `candidate_digest` over exact displayed candidate content; and
- timezone-aware UTC `created_at` as proposal knowledge time.

An incomplete candidate may be displayed for manual editing, but it cannot be
submitted to the M33.2 snapshot constructor until all terms and scope are
complete and valid.

### 6.2 `ProposalOrigin`

Permitted typed origins are:

- `CERTIFIED_DECISION_PAYLOAD`;
- `LEGACY_DECISION_CANDIDATE`;
- `LEGACY_RECOMMENDATION_CANDIDATE`;
- `OPTIMIZER_HISTORY_CANDIDATE` under a separately named proposal policy;
- `EXTERNAL_ARCHIVE_CANDIDATE`; and
- `MANUAL_HUMAN_INPUT`.

`SHADOW_PORTFOLIO`, transaction linkage/rows, current portfolio holdings, and
`FUTURE_CANONICAL_EXECUTION_PLAN` are prohibited proposal origins. They may be
shown separately as diagnostics or current facts, but cannot seed accepted
terms or silently modify the proposal.

### 6.3 `ProposalWarning`

Every warning has a stable code, human-readable detail, severity, and related
origin/evidence ids. Required warning codes include:

- `HISTORICAL_APPROVAL_UNVERIFIED`;
- `HISTORICAL_ACTOR_UNVERIFIED`;
- `RECOMMENDATION_ONLY_NOT_ACCEPTED_TERMS`;
- `LEGACY_PAYLOAD_SEMANTICS_UNCERTIFIED`;
- `TIMEZONE_UNVERIFIED`;
- `TARGET_UNIT_REVIEW_REQUIRED`;
- `ACTION_MAPPING_REVIEW_REQUIRED`;
- `SOURCE_MISSING`;
- `SOURCE_CONFLICT`;
- `SCOPE_RECONFIRMATION_REQUIRED`; and
- `FRESH_APPROVAL_REQUIRED`.

Warnings cannot be acknowledged in bulk or hidden by defaults. Material
warnings affecting a term must be displayed adjacent to that term.

### 6.4 `ProposalCompleteness`

- `COMPLETE_REVIEWABLE` - candidate terms and scope are structurally valid,
  but they have no historical approval authority;
- `EDIT_REQUIRED` - a human must add or replace missing/unsupported terms
  before a snapshot can be built;
- `CONFLICTING` - competing sources prevent an automatic candidate; quarantine;
- `UNUSABLE` - no permissible structured candidate can be produced; and
- `OUT_OF_SCOPE` - the source is rejected/expired or otherwise no-intent.

### 6.5 `ProposalReviewRequirement`

Review requirements are an immutable set. Every proposal eligible for
reconfirmation includes:

- `DISPLAY_EXACT_CANDIDATE_TERMS`;
- `DISPLAY_ALL_ORIGINS_AND_WARNINGS`;
- `CONFIRM_WORKSPACE_AND_PORTFOLIO_SCOPE`;
- `CONFIRM_INTENT_KIND`;
- `CONFIRM_EFFECTIVE_AND_EXPIRY_TIMES`;
- `FREEZE_FINAL_TERMS_BEFORE_APPROVAL`;
- `USE_CURRENT_VERIFIED_HUMAN_ACTOR`; and
- `BIND_FRESH_APPROVAL_TO_NEW_SNAPSHOT_ID_AND_HASH`.

`EDIT_REQUIRED` adds explicit review requirements for every missing or
unsupported field. A proposal cannot claim that silence means acceptance.

### 6.6 `ProposalDecision`

`ProposalDecision` records a current human's response to a proposal candidate,
not a historical decision. Its decision kinds are:

- `FINALIZE_FOR_REVIEW` - accept or edit candidate terms into a complete
  immutable M33.2 snapshot in `PENDING_REVIEW`; this is not approval;
- `REJECT_PROPOSAL` - decline the proposal without creating an intent;
- `ABANDON_PROPOSAL` - close the proposal without a verdict on historical
  advice; and
- `DEFER_PROPOSAL` - retain only proposal workflow state, not M33.2 lifecycle
  state.

The decision binds the candidate id/digest, current verified human actor,
current UTC occurrence time, exact final terms or rejection reason, exact
scope, and acknowledged warning ids. A stale candidate digest is a conflict.

After `FINALIZE_FOR_REVIEW`, the workflow is deliberately two-stage:

1. caller-supplied new `intent_id` and `snapshot_id` plus the final terms,
   scope, provenance, effective time, and expiry produce a new M33.2 snapshot
   and `PENDING_REVIEW` submission; then
2. the exact frozen snapshot is shown for a fresh M33.2 `APPROVE` command by a
   verified current human actor using that snapshot's exact content hash.

An implementation may make storage of those two acts transactional in a later
milestone, but it must not collapse the semantic distinction or approve an
unfrozen proposal.

### 6.7 What is new and what survives

Fresh reconfirmation creates:

- new proposal candidate identity and digest;
- new execution intent and snapshot identities;
- new M33.2 content hash from final reviewed terms;
- new `PENDING_REVIEW` transition sequence;
- new current-human approval event and event/knowledge times; and
- new idempotency keys and audit correlation ids.

The following may survive only as typed provenance or warnings:

- legacy recommendation and decision ids/digests;
- optimizer-history reference;
- legacy notes and labels;
- legacy local timestamp text;
- certificate/evidence ids and verification result; and
- the fact that candidate terms were reconstructed.

Historical actor, historical approval status, execution status, lifecycle
state, transaction linkage, fulfillment, shadow output, ids, content hashes,
effective/expiry policy, and inferred target units must never be silently
inherited.

## 7. Deterministic certification rules

Rules are evaluated in the order below. Every refusal/downgrade returns typed
reason codes and no snapshot, proposal, transition, or mutation.

| Condition | Deterministic result |
| --- | --- |
| Source decision is `REJECTED` or `EXPIRED` | `OUT_OF_SCOPE`; no proposal or intent, regardless of a certificate claim. |
| Unsupported certificate/payload/verification version | `UNVERIFIABLE` with `UNSUPPORTED_CONTRACT_VERSION`. |
| Same certificate id has different digests | `CONFLICTING` with `CERTIFICATE_ID_REUSED`. |
| Certificate digest or evidence digest does not match canonical bytes | `UNVERIFIABLE` with the applicable `*_DIGEST_MISMATCH`. |
| Signature is invalid, issuer/key is untrusted, or trust policy is unavailable | `UNVERIFIABLE`; never exact. |
| Effective verified revocation exists | `UNVERIFIABLE` with `CERTIFICATE_REVOKED`; certificate-derived proposal is forbidden. |
| Revocation status is unknown | `UNVERIFIABLE` with `REVOCATION_STATUS_UNKNOWN`; never exact. |
| Revocation status evidence conflicts | `CONFLICTING`. |
| Certificates make incompatible claims about the same approval event | `CONFLICTING`; supersession alone does not choose a winner. |
| Workspace, portfolio, namespace, or environment differs anywhere | `CONFLICTING` with exact scope reason; no automatic proposal. |
| Recommendation or decision binding is missing for a claimed legacy exact case | Not exact; proposal-only only if candidate eligibility independently passes. |
| Exact reviewed payload or canonical digest is missing | Not exact; `REVIEWED_PAYLOAD_MISSING`. |
| Exact approved payload or canonical digest is missing | Not exact; `APPROVED_PAYLOAD_MISSING`. |
| Reviewed and approved digests differ without an approved lossless transformation | `CONFLICTING`; no best-effort normalization. |
| Historical actor identity is missing/shared/ambiguous | Not exact; proposal may require a new current actor. |
| Historical actor authority for exact scope/event time is absent | Not exact; a current operator statement cannot repair it. |
| Event time is naive, timezone is unknown, or local time is ambiguous without a named rule | Not exact; `TIMEZONE_AMBIGUOUS`. |
| Decision lineage is duplicated, incomplete, or ambiguous | `CONFLICTING`; no latest-wins rule. |
| Legacy terms need an unapproved action/unit/zero-target transformation | Not exact; proposal may expose the unresolved field for explicit editing. |
| Target snapshot id is missing or differs from the certificate | No historical approval recreation. |
| M33.2 target content hash is missing or differs from the certificate | No historical approval recreation; `TARGET_CONTENT_HASH_MISMATCH`. |
| All exact requirements pass and revocation status is `NOT_REVOKED` | `CERTIFIED_EXACT`. |
| Trusted evidence proves candidate bytes/scope but not all historical approval requirements | `CERTIFIED_PROPOSAL_ONLY`, with mandatory reconfirmation. |
| No trusted certificate exists but a permitted candidate is complete and non-conflicting | `UNVERIFIABLE`; a warning-rich proposal may be produced under the explicit proposal policy only. |

Core reason codes include:

`UNSUPPORTED_CONTRACT_VERSION`, `CERTIFICATE_ID_REUSED`,
`CERTIFICATE_DIGEST_MISMATCH`, `EVIDENCE_DIGEST_MISMATCH`,
`SIGNATURE_INVALID`, `ISSUER_UNTRUSTED`, `TRUST_POLICY_UNAVAILABLE`,
`CERTIFICATE_REVOKED`, `REVOCATION_STATUS_UNKNOWN`,
`REVOCATION_STATUS_CONFLICT`,
`CONFLICTING_CERTIFICATES`, `REVIEWED_PAYLOAD_MISSING`,
`APPROVED_PAYLOAD_MISSING`, `REVIEWED_APPROVED_PAYLOAD_CONFLICT`,
`HISTORICAL_ACTOR_MISSING`, `HISTORICAL_ACTOR_AMBIGUOUS`,
`ACTOR_AUTHORITY_UNPROVEN`, `WORKSPACE_SCOPE_MISMATCH`,
`PORTFOLIO_SCOPE_MISMATCH`, `AUTHORITY_NAMESPACE_MISMATCH`,
`ENVIRONMENT_SCOPE_MISMATCH`, `RECOMMENDATION_BINDING_MISSING`,
`DECISION_BINDING_MISSING`, `LINEAGE_AMBIGUOUS`, `TIMEZONE_AMBIGUOUS`,
`LOSSLESS_MAPPING_UNPROVEN`, `TARGET_SNAPSHOT_BINDING_MISSING`,
`TARGET_SNAPSHOT_ID_MISMATCH`, `TARGET_CONTENT_HASH_MISMATCH`,
`PROPOSAL_ORIGIN_PROHIBITED`, `OUT_OF_SCOPE_DECISION`, and
`FRESH_RECONFIRMATION_REQUIRED`.

## 8. Fixture catalogue for a future pure implementation

| Fixture | Essential input | Expected result |
| --- | --- | --- |
| Fully certified exact case | Trusted issuer/signature, exact payloads/digests, actor/authority, scope, lineage, UTC time, unrevoked status, target id/hash | `CERTIFIED_EXACT`; exact eligible; historical approval recreation eligible |
| Missing actor | Otherwise complete trusted proposal evidence without stable historical actor | `CERTIFIED_PROPOSAL_ONLY`; no historical approval |
| Missing reviewed digest | Trusted approved candidate payload present but reviewed payload/digest absent | `CERTIFIED_PROPOSAL_ONLY`; `REVIEWED_PAYLOAD_MISSING` |
| Missing approved digest | Trusted reviewed candidate payload present but accepted payload/digest absent | `CERTIFIED_PROPOSAL_ONLY`; `APPROVED_PAYLOAD_MISSING` |
| Duplicate authority id, identical bytes | Duplicate delivery of same id/digest | Deterministic replay of same result, not two authorities |
| Duplicate authority id, different bytes | Same id with different digest | `CONFLICTING`; `CERTIFICATE_ID_REUSED` |
| Conflicting certificates | Two trusted certificates disagree on actor, terms, scope, time, or target | `CONFLICTING`; no selected winner |
| Legacy rows only | Current recommendation/decision rows with no certificate | Never exact; preserves M33.3 zero-row-only conclusion |
| Proposal-only certificate | Candidate bytes/scope certified, actor or historical approval binding absent | `CERTIFIED_PROPOSAL_ONLY`; fresh review required |
| Unverifiable but reviewable candidate | Complete permitted candidate, no trusted certificate, no conflict | Warning-rich pre-snapshot proposal only |
| Manual reconfirmation unchanged | Human finalizes exact candidate, then approves newly frozen snapshot id/hash | New ids/hash/current actor; legacy approval not inherited |
| Manual reconfirmation with edits | Human changes candidate before finalization | New final terms/hash; warnings/provenance retained; fresh approval required |
| Certificate revocation | Otherwise exact certificate plus effective trusted revocation | `UNVERIFIABLE`; no new adaptation/proposal from certificate |
| Conflicting revocation evidence | Trusted status sources disagree | `CONFLICTING` |
| Workspace mismatch | Certificate, evidence, or target scopes differ | `CONFLICTING`; no proposal derived automatically |
| Portfolio mismatch | Certificate, evidence, or target portfolios differ | `CONFLICTING`; no proposal derived automatically |
| Timezone ambiguity | Otherwise trusted proposal evidence with naive/local historical time and no named disambiguation rule | `CERTIFIED_PROPOSAL_ONLY`; `TIMEZONE_AMBIGUOUS` |
| Target hash mismatch | Certificate target hash differs from M33.2 computation | Not exact; no approval event |
| Recommendation-only candidate | Structured recommendation with no acceptance proof | Proposal only with visible warning and fresh review |
| Shadow-only evidence | Matching shadow holdings/terms | Refused as authority and proposal origin |
| Transaction-link-only evidence | Matching transaction link/symbol | Refused as intent authority or fulfillment proof |
| Rejected legacy decision | Any certificate/proposal claim over `REJECTED` | `OUT_OF_SCOPE`; no intent/proposal |
| Expired legacy decision | Any certificate/proposal claim over `EXPIRED` | `OUT_OF_SCOPE`; no intent/proposal |

Future tests must also prove frozen-data immutability, canonical ordering,
byte-equivalent output, unknown-version refusal, naive-time refusal, non-finite
number refusal, idempotent same-certificate verification, and zero side effects.

## 9. Relationship to M33.2 contracts

M33.4 changes no existing M33.2 type, hash rule, transition, or test.

- `ExecutionIntentSnapshot.content_hash` remains exactly as implemented.
- Approval still requires the exact snapshot id plus matching content hash and
  a human actor.
- `INCOMPLETE` source provenance remains unapprovable.
- `LEGACY_RECONSTRUCTED` provenance does not carry historical approval; a new
  current human approval is required.
- System actors still cannot approve.
- Authority evidence is not ledger evidence and cannot produce
  `PARTIALLY_EXECUTED` or `COMPLETED`.
- A certificate is not a new `SourceKind` in M33.4. A future pure contract may
  add a typed certificate audit reference outside or alongside current source
  provenance only through a separately reviewed additive change; it must not
  overload an existing source kind.

The certificate digest must not be inserted into hashed M33.2
`source_provenance` when that same certificate binds `target_content_hash`;
doing so would create a circular digest dependency. A future audit reference
must remain outside snapshot content or use a separately designed two-layer
binding approved before implementation.

The target snapshot id/hash requirement is deliberately stronger than term
similarity. It closes the gap between “these historical terms look equal” and
“this exact immutable M33.2 snapshot is the object of the certified approval.”

## 10. Explicit non-adoption statement

M33.4 does not:

- implement `AuthorityCertificate`, verification, proposal, or reconfirmation
  code;
- create or read a certificate, trust store, signing key, revocation list,
  legacy row, proposal, snapshot, transition, or quarantine record;
- add an ORM model, migration, repository, API, endpoint, writer, scheduler,
  background task, CLI, or frontend;
- perform cryptographic signing or verification;
- convert, backfill, dual-write, repair, rank, or delete legacy data;
- import M33 contracts into production code;
- change recommendation, decision, expiry, shadow, transaction, portfolio,
  ledger, evaluation, or replay behavior;
- treat approval as execution or certification as transaction evidence;
- adopt a canonical execution plan or reopen M32; or
- claim that any existing deployment possesses qualifying exact evidence.

## 11. Recommended next milestone

**M33.5 - Pure Authority Verification and Reconfirmation Contracts.**

M33.5 should implement only frozen ORM-free types, canonical serialization and
hashing, a pure verifier over caller-supplied certificate/trust/signature/
revocation facts, pure proposal eligibility/finalization validation, and the
fixture catalogue in section 8.

It should return typed results and reason codes with no id generation, storage,
database access, cryptographic key retrieval, legacy row reader, snapshot
construction, lifecycle transition, or production import. It should not yet
recreate historical approval or add a legacy adapter. Any additive M33.2 audit
reference required for a later adapter must be proposed explicitly rather than
smuggled into the pure verifier milestone.

Persistence, certificate issuance/key governance, legacy data access,
production quarantine, dual-write, runtime reconfirmation UI/API, and actual
adaptation remain later, separately approved milestones.
