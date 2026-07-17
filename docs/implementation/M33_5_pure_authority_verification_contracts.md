# M33.5 - Pure Authority Verification and Reconfirmation Contracts

**Date:** 2026-07-17

**Status:** Implemented. Frozen ORM-free authority/proposal contracts, explicit
canonical hashing, pure eligibility verification, and pure reconfirmation
preparation only. No runtime adoption.

**Milestone decision:** Implement the M33.4 authority and reconfirmation model
as pure data-in/data-out contracts. Authority verification can report exact,
proposal-only, unverifiable, conflicting, or out-of-scope eligibility, but it
never constructs an `ExecutionIntentSnapshot`, appends a lifecycle event, or
recreates approval. Proposal finalization returns preparation data only; new
caller-owned ids, `PENDING_REVIEW`, and fresh M33.2 approval remain later acts.

## 1. Authoritative boundary

The governing inputs remain:

- `docs/implementation/M33_1_execution_intent_snapshot_lifecycle_foundation.md`;
- `docs/implementation/M33_2_pure_execution_intent_contracts.md`;
- `docs/implementation/M33_3_legacy_adapter_feasibility.md`;
- `docs/implementation/M33_4_historical_authority_certification_contract.md`;
  and
- `docs/implementation/M32_EPIC_CLOSEOUT.md`.

All predecessor boundaries remain unchanged:

- M32 is closed and canonical execution planning remains NO-GO.
- Persisted legacy rows alone still contain zero safely `EXACT_ADAPTABLE`
  cases.
- Certificates determine eligibility only. They are not snapshots, approvals,
  execution evidence, orders, transactions, or portfolio facts.
- Proposals are pre-snapshot review inputs. `FINALIZE_FOR_REVIEW` is not
  approval.
- M33.2 content hashing and transition validation are unchanged.
- No certificate audit data enters M33.2 hashed `source_provenance`.
- No ORM, migration, repository, database access, endpoint, scheduler, writer,
  cryptographic key retrieval, certificate persistence, legacy-row extraction,
  legacy conversion, runtime import, frontend, or Graphify change is included.

## 2. Implemented files

### `backend/services/execution_intent_authority.py`

The authority module contains only frozen values, enums, explicit serializers,
SHA-256 helpers, and one pure verifier.

Core contract groups:

| Group | Public contracts |
| --- | --- |
| Issuer and algorithms | `AuthorityIssuerKind`, `DigestAlgorithm`, `SignatureAlgorithm`, `AuthorityIssuer` |
| Evidence | `AuthorityEvidenceKind`, `AuthorityEvidenceRole`, `AuthoritySourceReference`, `AuthorityEvidence`, `DetachedEvidenceFact` |
| Binding and scope | `HistoricalSourceAct`, `PayloadRelationship`, `AuthorityBinding`, `AuthorityScope`, `TargetSnapshotFact` |
| Certificate and levels | `AuthorityCompleteness`, `AuthorityLevel`, `AuthorityCertificate`, `AuthorityReasonCode`, `AuthorityVerificationResult` |
| Caller-established facts | `SignatureVerificationFact`, `IssuerTrustFact`, `RevocationEvidence`, `RevocationVerificationFact`, `AuthorityConflictFact`, `VerificationPolicy` |
| Pure functions | `canonicalize_authority_evidence()`, `compute_authority_evidence_digest()`, `canonicalize_authority_certificate()`, `compute_authority_certificate_digest()`, `verify_authority()` |

No contract generates an id. Every certificate, evidence, source, proposal,
and target identity is caller-supplied.

### `backend/services/execution_intent_reconfirmation.py`

| Group | Public contracts |
| --- | --- |
| Proposal vocabulary | `ProposalOrigin`, `ProposalWarningCode`, `ProposalWarningSeverity`, `ProposalCompleteness`, `ProposalReviewRequirement` |
| Decision and refusal vocabulary | `ProposalDecisionKind`, `ProposalOutcome`, `ProposalRefusalReason` |
| Frozen values | `ProposalWarning`, `ProposalCandidate`, `ProposalDecision`, `ReconfirmationPreparation`, `ProposalRefusal`, `ProposalValidationResult` |
| Pure functions | `validate_proposal_eligibility()`, `build_proposal_candidate()`, `compute_proposal_candidate_digest()`, `finalize_proposal_for_review()` |

The module imports the M33.2 terms builder for final allocation validation. It
does not import or call `build_execution_intent_snapshot()` or
`validate_transition()`.

## 3. Primitive validation and immutability

- Domain records are frozen dataclasses.
- Collections retained by contracts are tuples or frozensets.
- Required ids and version strings must be non-empty.
- Digests use lowercase `sha256:<64-hex>` syntax.
- All authority/proposal datetimes must be timezone-aware with an exact UTC
  offset; naive and non-UTC-offset values raise `ValueError`.
- Proposal term Decimals must be finite. The M33.2 terms builder continues to
  own positive/exactly-one-of/duplicate validation.
- Unknown authority/proposal contract versions are typed fail-closed business
  outcomes when verification/finalization is attempted.
- Malformed primitive shapes raise `ValueError`; expected authority and review
  failures return typed result/refusal data.

## 4. Canonical serialization and hashing

All canonical serializers use explicit hand-built dictionaries, sorted JSON
keys, compact separators, and canonical UTC ISO-8601. Generic dataclass
reflection is not used.

### 4.1 Evidence source digest

`compute_authority_evidence_digest()` hashes the exact canonical UTF-8 payload
under the versioned domain separator:

```text
M33.5:authority-evidence:<source_contract_version>\n
```

The payload may be embedded in `AuthorityEvidence` or supplied through a
`DetachedEvidenceFact`. A detached caller assertion is checked and the digest
is independently recomputed. A locator is never payload evidence.

### 4.2 Certificate digest

The certificate digest includes exactly:

- certificate contract version and opaque certificate id;
- issuer id/kind/namespace, trust-policy version, signing-key id, and signature
  algorithm;
- issuance time;
- evidence envelopes sorted by `(evidence_kind, source_local_id,
  source_digest)`, with roles sorted;
- complete binding, scope, completeness claim, and supersession reference.

It excludes exactly:

- the stored `certificate_digest`; and
- signature bytes.

The signature is a caller-verified fact. This module performs no cryptographic
operation.

### 4.3 Proposal candidate digest

The proposal digest binds all candidate identity/display/review data:

- contract version and candidate id;
- authority level, certificate reference, and ordered authority reasons;
- ordered origins;
- intent kind and canonical candidate terms;
- exact scope and proposal completeness;
- ordered warnings and review requirements;
- ordered legacy provenance inputs; and
- candidate creation, effective, and expiry times.

Only the stored `candidate_digest` is excluded. Allocation order, origin order,
warning order, provenance order, and reason-code input order do not change the
digest.

### 4.4 M33.2 hash boundary

`TargetSnapshotFact.content_hash` is validated only as an opaque SHA-256 value
and compared byte-for-byte with `AuthorityBinding.target_content_hash`.
M33.5 does not import, call, or redefine M33.2 snapshot hashing.

Certificate audit data is not copied into M33.2 hashed provenance, avoiding
the circular dependency identified by M33.4.

## 5. Caller-supplied verification facts

`verify_authority()` receives all external conclusions explicitly:

- detached canonical payload plus caller digest-match fact;
- certificate signature validity;
- issuer/key trust under the named policy;
- verified revocation evidence and its signature/trust facts;
- verified conflicting-authority facts or related certificates;
- verification policy/version/evaluation time; and
- the target intent/snapshot identity, opaque content hash, and exact scope.

The verifier does not retrieve keys, call a crypto library, query a trust
store, fetch evidence, read environment variables, inspect a database, or use
the current clock.

## 6. Deterministic verification precedence

`verify_authority()` applies this fail-closed sequence:

1. legacy `REJECTED`/`EXPIRED` source act;
2. unsupported authority/policy, digest, or signature-algorithm version;
3. certificate-id reuse or verified conflicting claims;
4. certificate digest mismatch;
5. evidence/detached-payload mismatch or prohibited shadow/transaction/current-
   holdings evidence;
6. invalid/missing signature fact;
7. unavailable/mismatched trust policy or untrusted issuer/key;
8. conflicting, revoked, or unknown revocation status;
9. workspace, portfolio, namespace, or environment mismatch;
10. ambiguous lineage;
11. reviewed/approved payload conflict or unapproved transformation;
12. missing recommendation/decision/payload/actor/authority/time facts;
13. missing/mismatched target intent id, snapshot id, or content hash;
14. exact success, otherwise trusted proposal-only eligibility.

Uncertified evidence is `UNVERIFIABLE`. It may expose proposal capability only
when `VerificationPolicy.allow_unverifiable_proposals=True`, candidate payload
and scope are available, no prohibited/conflicting evidence exists, and fresh
reconfirmation remains mandatory.

Reason codes and evidence ids are returned in deterministic canonical order.

## 7. Authority capabilities

| Level | Exact snapshot eligible? | Proposal eligible? | Reconfirmation | Historical approval recreation eligible? | M33.2 provenance result |
| --- | --- | --- | --- | --- | --- |
| `CERTIFIED_EXACT` | Yes | Yes, optionally | Not required for exact eligibility | Yes | `EXACT_FROZEN` |
| `CERTIFIED_PROPOSAL_ONLY` | No | Yes | Required | No | `LEGACY_RECONSTRUCTED` |
| `UNVERIFIABLE` | No | Explicit-policy conditional | Required if permitted | No | `INCOMPLETE` |
| `CONFLICTING` | No | No | Not applicable | No | None/incomplete finding |
| `OUT_OF_SCOPE` | No | No | No | No | None |

Only `CERTIFIED_EXACT` can set both
`may_build_exact_snapshot=True` and
`may_recreate_historical_approval=True`. Even then, the verifier produces no
snapshot or approval event.

Effective revocation disables both exact adaptation and certificate-derived
proposal use. Unknown revocation is `UNVERIFIABLE`; an independently permitted
unverifiable proposal remains a separate policy decision.

## 8. Proposal and reconfirmation behavior

### 8.1 Eligibility and construction

- Exact authority may optionally enter the proposal path, but the proposal
  path still requires fresh approval.
- Proposal-only authority produces warnings for unverified historical
  approval/actor as applicable.
- Unverifiable authority requires explicit verifier policy capability.
- Conflicting and out-of-scope authority cannot create a proposal.
- Shadow portfolios, transaction linkage/rows, current holdings, and future
  canonical execution plans are prohibited origins.
- Non-exact authority cannot label legacy provenance `EXACT_FROZEN`.
- Structurally valid candidate terms produce `COMPLETE_REVIEWABLE`; missing or
  invalid candidate terms produce `EDIT_REQUIRED` with a blocking warning.

### 8.2 Candidate binding

Every candidate contains its authority reference/result, exact scope, origins,
warnings, review requirements, source provenance, and canonical digest. A
decision supplies `expected_candidate_digest`; stale or tampered content is a
typed refusal.

All candidate warnings must be explicitly acknowledged by code. Scope must be
confirmed exactly.

### 8.3 Finalization

`finalize_proposal_for_review()` requires:

- `FINALIZE_FOR_REVIEW` decision kind;
- unchanged candidate id/digest;
- current non-empty `HUMAN` actor;
- exact workspace/portfolio confirmation;
- acknowledgement of every warning;
- complete final terms validated by the M33.2 terms builder;
- finite Decimal targets;
- final intent kind and UTC effective/expiry facts; and
- no `INCOMPLETE` legacy source provenance in preparation output.

On success, `ReconfirmationPreparation` returns final terms, intent kind,
scope, legacy provenance inputs, current actor, effective/expiry values,
review requirements, and authority references.

It deliberately contains no `intent_id`, `snapshot_id`, M33.2 `content_hash`,
lifecycle state, transition, or approval event. Explicit flags state that new
caller-owned ids, a later `PENDING_REVIEW` submission, manual-human-input
provenance, and a separate fresh approval are still required. Historical
approval and lifecycle state are always marked as not inherited.

## 9. Typed refusal behavior

Expected verifier outcomes are represented by `AuthorityVerificationResult`
plus stable `AuthorityReasonCode` values. Expected proposal failures are
`ProposalValidationResult(REFUSED)` with exactly one `ProposalRefusal` and no
candidate/preparation payload.

Malformed primitive inputs may raise `ValueError`, including naive/non-UTC
times, empty required ids, invalid digest syntax, invalid enum/collection
shapes, and non-finite final term values at direct canonicalization boundaries.

No expected authority or proposal business outcome raises a generic exception.

## 10. Tests and regression evidence

### New M33.5 tests

- `backend/tests/test_execution_intent_authority_m33_5.py`: **63 passed**.
- `backend/tests/test_execution_intent_reconfirmation_m33_5.py`: **46 passed**.

Coverage includes the complete M33.4 fixture catalogue, authority capability
invariants, same-id replay/conflict, certificate conflict, signature/trust/
revocation facts, exact scope components, actor/authority/time/lineage/target
requirements, prohibited evidence/origins, canonical ordering and sensitivity,
stale candidate protection, warning acknowledgement, final term validation,
fresh-human requirements, and preparation-only output.

### M33.2 regression

Both M33.2 files remain green with the new tests: **204 passed** total
(109 M33.5 + 95 M33.2).

### Focused current-state regression

The M33.1 current-state suites remain green: **57 passed**.

- `test_horizon_grader.py`
- `test_shadow_tracker_cash_accounting.py`
- `test_shadow_regeneration.py`
- `test_execution_decision_linkage.py`
- `test_execution_ledger.py`

### Relevant M31/M32 regression

Relevant pure/foundation suites remain green: **100 passed**.

- `test_execution_eligibility_m31_3.py`
- `test_execution_registry_preparation_m31_5.py`
- `test_execution_optimizer.py`
- `test_normalized_trade_input_m32_3b.py`
- `test_execution_price_observation_m32_3c.py`
- `test_execution_policy_m32_3e1.py`
- `test_execution_trade_leg_m32_2.py`

Warnings are pre-existing SQLAlchemy, `datetime.utcnow()`, pandas, and test
environment deprecations; no new test failure is hidden.

## 11. Explicit non-adoption statement

M33.5 does not:

- change M33.2 types, content hashing, transitions, or approval behavior;
- construct an `ExecutionIntentSnapshot` or lifecycle event;
- recreate historical approval;
- add an ORM model, migration, database access, repository, endpoint, writer,
  scheduler, background job, CLI, frontend, or Graphify output;
- retrieve keys, verify signatures cryptographically, consult a trust store,
  or fetch revocation/evidence data;
- persist a certificate, proposal, result, or quarantine finding;
- read or adapt a legacy recommendation/decision row;
- use recommendation, optimizer, shadow, transaction, current holdings, or
  replay data as silent accepted terms;
- mutate recommendation, decision, shadow, transaction, portfolio, ledger,
  expiry, evaluation, or replay behavior; or
- reopen M32 or adopt canonical execution planning.

No `DECISION_LOG` entry is added. The implementation realizes the concrete
authority and reconfirmation architecture already approved and recorded by
M33.4; it introduces no new runtime or ownership decision.

## 12. Recommended next milestone

**M33.6 - Authority Evidence Availability and Issuer Governance Study
(design-only).**

Before a legacy adapter or persistence milestone, M33.6 should determine
whether any real deployment possesses immutable reviewed/approved payloads,
stable historical actors, authorization evidence, reliable UTC/timezone
semantics, and a viable audit/archive issuer. It should define ownership of
trust-policy versions, signing keys, revocation publication, certificate
issuance, incident response, and retention without implementing them.

The study should run the M33.5 verifier against sanitized caller-supplied
fixtures only and report whether any evidence source can honestly reach
`CERTIFIED_EXACT`. It should add no database reader, certificate issuer,
crypto/key integration, persistence, adapter, backfill, API, or runtime path.
