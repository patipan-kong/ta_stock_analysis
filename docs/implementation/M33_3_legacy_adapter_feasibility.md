# M33.3 - Legacy Adapter Feasibility Study

**Date:** 2026-07-17

**Status:** Complete. Design and feasibility findings only. No adapter,
runtime adoption, persistence, or legacy conversion is implemented.

**Milestone decision:** Persisted legacy rows alone provide **zero safely
`EXACT_ADAPTABLE` cases**. No `ExecutionIntentSnapshot` may be minted from a
legacy row without additional authoritative certification of the exact terms
reviewed, the approving human actor, and the applicable scope. Missing facts
must not be inferred from recommendations, shadows, transaction linkage, or
other defaults.

## 1. Authoritative boundary

`docs/implementation/M33_1_execution_intent_snapshot_lifecycle_foundation.md`
governs the execution-intent design and
`docs/implementation/M33_2_pure_execution_intent_contracts.md` governs the
implemented pure contracts. `docs/implementation/M32_EPIC_CLOSEOUT.md` remains
the governing predecessor and is unchanged.

- M32 remains closed. Canonical execution planning remains NO-GO.
- This study does not treat M32 planning or shadow evidence as executable or
  as evidence of human acceptance.
- Approval remains non-executing. A legacy approval label does not establish
  execution, transaction admission, or fulfillment.
- This milestone adds no code and does not import or adopt the M33.2 modules
  anywhere in the running application.
- No ORM model, migration, endpoint, repository, background writer,
  dual-write, backfill, replay change, or production conversion is introduced.

The word **quarantine** in this document describes an adapter-classification
disposition. It does not mean that a lifecycle `QUARANTINED` event may be
created when no valid `ExecutionIntentSnapshot` exists.

## 2. Legacy facts verified

The feasibility review covered the persisted row shapes and the paths that
write or consume them, including `RecommendationSnapshot`,
`UserExecutionDecision`, `ShadowPortfolio`, `Transaction`, optimizer UI/API
submission, expiry writing, shadow construction/regeneration, and execution
ledger evaluation.

The relevant legacy facts are:

1. `UserExecutionDecision.decision` can contain human-submitted `APPROVED`,
   `REJECTED`, `PARTIAL_EXECUTION`, or `MANUAL_OVERRIDE`; the expiry writer can
   also create `EXPIRED` rows marked as system-generated.
2. `approved_allocations_json` is nullable text containing an unversioned list
   of dictionaries. The API does not validate a typed inner allocation schema,
   and a missing payload and an empty list are both stored as `NULL`.
3. The production optimizer UI does not submit `approved_allocations` when it
   records an approval or manual override. It submits the decision, notes, and
   any structured override labels/symbols.
4. The legacy field comment describes `approved_allocations_json` as what the
   user actually executed. Neither the row nor its writer certifies that it is
   the exact immutable set of terms displayed to and accepted by a human.
5. A decision row has no persisted human actor identity. Authentication is not
   converted into an actor reference stored with the decision.
6. `executed_at` is assigned when the decision is recorded; it is not evidence
   of execution. Its legacy timestamp has no persisted timezone contract.
7. The decision endpoint checks that the recommendation belongs to the active
   workspace, but it does not prove that the request's portfolio id equals the
   recommendation's portfolio id before storing the decision.
8. There is no uniqueness or correction-lineage constraint for decisions on a
   recommendation. Duplicate and conflicting rows can therefore coexist.
9. `RecommendationSnapshot.projected_allocations_json` represents recommended
   output, not necessarily accepted terms. Some historical rows were written
   with this field `NULL` and could later be backfilled from optimizer history,
   so current contents do not prove what a human reviewed at decision time.
10. Shadow construction can fall back from decision allocations to
    recommendation allocations and then to portfolio holdings. A shadow's
    resulting holdings therefore cannot prove which source, if any, was
    accepted by a human.
11. A transaction may store `execution_decision_id`, but the write path does
    not establish that the linked decision was approved, in the same scope, or
    authoritative for the transaction's symbol and amount. The link is
    metadata, not accepted-term or fulfillment evidence.
12. Legacy allocation actions include `BUY`, `ACCUMULATE`, `REDUCE`, `SELL`,
    `HOLD`, and `WATCH`. M33.2 terms have only `BUY` and `SELL`, require a
    positive target weight or value, and intentionally contain no executable
    quantity. In particular, `HOLD`/`WATCH` and a full-sale target weight of
    zero do not have a lossless, already-approved mapping.
13. Legacy target weights are represented as percentage-like values, while no
    approved adapter contract defines their normalization into M33.2 terms.
14. `PARTIAL_EXECUTION` is accepted as a legacy decision label even though it
    describes an outcome-like condition. A label and notes do not identify the
    exact terms that were accepted or the admitted ledger evidence required by
    the M33.2 transition contract.

These are structural limitations, not merely dirty-data exceptions. They
prevent a row-only adapter from proving the M33.1 approval-binding invariant.

## 3. Verified legacy shape matrix

“Buildable” below means safe to construct an `ExecutionIntentSnapshot` and
claim that it represents the historically reviewed intent. Every current
row-only shape is non-buildable.

| Legacy row shape | What the rows establish | Classification | Required disposition | Row-only buildable? |
| --- | --- | --- | --- | --- |
| `APPROVED`, allocations `NULL`/empty | Approval label, notes, recommendation link, record time | `INCOMPLETE` — `APPROVED_TERMS_MISSING`, `HUMAN_ACTOR_UNAVAILABLE` | Quarantine; do not substitute recommendation or shadow terms | No |
| `APPROVED`, malformed or invalid allocations | Approval label plus uninterpretable/unrepresentable payload | `INCOMPLETE` — allocation parse/shape reason plus `HUMAN_ACTOR_UNAVAILABLE` | Quarantine; do not repair heuristically | No |
| `APPROVED`, well-formed and M33.2-representable allocations | Candidate terms exist, but the row does not certify that they are the exact reviewed terms or identify the approving human | `INCOMPLETE` — `TERMS_NOT_CERTIFIED_REVIEWED`, `HUMAN_ACTOR_UNAVAILABLE` | Quarantine pending external authority certification | No |
| `MANUAL_OVERRIDE`, allocations `NULL`/empty | Override label, optional notes/type/symbols, but no complete accepted allocation terms | `INCOMPLETE` — `OVERRIDE_TERMS_MISSING`, `HUMAN_ACTOR_UNAVAILABLE` | Quarantine; labels and prose must not be converted into terms | No |
| `MANUAL_OVERRIDE`, allocations present | Candidate allocations and override metadata without exact-review or actor certification | `INCOMPLETE` — `TERMS_NOT_CERTIFIED_REVIEWED`, `HUMAN_ACTOR_UNAVAILABLE` | Quarantine pending external authority certification | No |
| `PARTIAL_EXECUTION`, allocations `NULL`/empty | Outcome-like label without accepted terms or admitted ledger evidence | `UNSUPPORTED` — `PARTIAL_TERMS_MISSING`, `PARTIAL_EXECUTION_NOT_INTENT_AUTHORITY` | Quarantine; do not infer intent or fulfillment | No |
| `PARTIAL_EXECUTION`, allocations present | Candidate payload combined with an outcome-like label, but no historical approval binding, actor, or admitted evidence | `UNSUPPORTED` — `PARTIAL_EXECUTION_NOT_INTENT_AUTHORITY`, `TERMS_NOT_CERTIFIED_REVIEWED` | Quarantine pending a separately approved interpretation and authority contract | No |
| `REJECTED` | Explicit non-acceptance | `OUT_OF_SCOPE` — `REJECTED_NO_INTENT` | Create no intent and no proposal | No |
| `EXPIRED` | System-created absence/expiry of a usable decision | `OUT_OF_SCOPE` — `EXPIRED_NO_INTENT` | Create no intent and no proposal | No |
| Unknown decision value | No approved semantic mapping | `UNSUPPORTED` — `UNSUPPORTED_DECISION_VALUE` | Quarantine for inspection | No |
| Any candidate with duplicate decision rows | More than one legacy fact claims the same recommendation; there is no authoritative correction lineage | `CONFLICTING` — `DUPLICATE_DECISIONS` | Quarantine all involved rows, including byte-equivalent duplicates | No |
| Any candidate with materially different decision rows | Competing decisions without an authoritative winner | `CONFLICTING` — `MULTIPLE_DECISIONS_CONFLICT` | Quarantine all involved rows | No |
| Human-looking decision plus system expiry for the same recommendation | Conflicting human/system legacy facts without atomic ordering guarantees | `CONFLICTING` — `SYSTEM_EXPIRY_HUMAN_CONFLICT` | Quarantine; do not choose by timestamp alone | No |
| Decision/recommendation workspace or portfolio mismatch | Scope cannot be proven immutable | `CONFLICTING` — `WORKSPACE_SCOPE_MISMATCH` or `PORTFOLIO_SCOPE_MISMATCH` | Quarantine | No |
| Referenced recommendation or required source row missing | Provenance cannot be reconstructed or checked | `INCOMPLETE` — `SOURCE_UNAVAILABLE` | Quarantine | No |
| Actor cannot be identified and verified as the approving human | Approval authority is absent even if candidate terms are complete | `INCOMPLETE` — `HUMAN_ACTOR_UNAVAILABLE` | Quarantine | No |

The matrix intentionally does not include a row shape whose missing terms are
filled from `RecommendationSnapshot`, `ShadowPortfolio`, portfolio holdings,
optimizer history, or transaction linkage. Such a composite is still not
proof of accepted terms and remains non-buildable.

## 4. Classification taxonomy

The future adapter taxonomy should use these mutually exclusive top-level
classifications:

| Classification | Meaning | Permitted result |
| --- | --- | --- |
| `EXACT_ADAPTABLE` | An approved authority contract proves exact reviewed terms, exact approving actor identity/authority, source time, scope, and unambiguous lineage. | May be eligible for exact conversion under a later approved milestone. There are zero current row-only cases. |
| `LEGACY_RECONSTRUCTED` | Candidate terms can be reconstructed, but historical approval against those exact terms and actor cannot be proved. | At most a pending proposal requiring explicit human review and reconfirmation; never import historical `APPROVED` state by inference. |
| `INCOMPLETE` | A required term, source, actor, timestamp interpretation, or provenance fact is missing or invalid. | Quarantine; create no intent from the incomplete historical claim. |
| `CONFLICTING` | Multiple facts disagree, duplicate authority is ambiguous, or immutable scope does not agree. | Quarantine all implicated rows; no heuristic winner. |
| `UNSUPPORTED` | The legacy value or shape has no approved lossless interpretation in the M33.2 contract. | Quarantine pending an explicit policy decision. |
| `OUT_OF_SCOPE` | The row explicitly does not represent accepted intent. | Create no intent or proposal. |

A future `LEGACY_RECONSTRUCTED` path may use recommendation output only as a
clearly labelled proposal input. It may produce no more than a pending proposal
that receives a new snapshot id, new human review, and a fresh approval bound
to the proposal's exact content hash. Whether that proposal is itself an M33.2
snapshot or a pre-snapshot candidate is an unresolved authority decision in
this study.

The only exception to fresh reconfirmation would be a separately approved,
versioned authority contract that proves the historical human approval against
the exact terms and the exact actor identity. Existing rows do not provide that
proof.

## 5. Reason-code catalogue

Reason codes should be stable machine-readable values. A future classifier may
return more than one code while retaining exactly one top-level classification.

### 5.1 Decision semantics

| Reason code | Meaning |
| --- | --- |
| `REJECTED_NO_INTENT` | A rejected recommendation is explicit non-acceptance. |
| `EXPIRED_NO_INTENT` | An expired legacy decision does not create accepted intent. |
| `UNSUPPORTED_DECISION_VALUE` | The decision label has no approved adapter meaning. |
| `SYSTEM_DECISION_CANNOT_AUTHORIZE` | A system-generated row cannot stand in for human approval. |
| `PARTIAL_EXECUTION_NOT_INTENT_AUTHORITY` | The outcome-like label does not prove accepted terms or ledger admission. |

### 5.2 Terms and payload

| Reason code | Meaning |
| --- | --- |
| `APPROVED_TERMS_MISSING` | An approval-labelled row has no decision-owned allocation payload. |
| `PARTIAL_TERMS_MISSING` | A partial-execution row has no complete accepted-term candidate. |
| `OVERRIDE_TERMS_MISSING` | Override labels/notes exist without complete allocation terms. |
| `TERMS_MALFORMED_JSON` | The allocation payload cannot be parsed as JSON. |
| `TERMS_INVALID_SHAPE` | The parsed payload does not have the required list/object structure. |
| `TERMS_NOT_CERTIFIED_REVIEWED` | Candidate terms exist but no authority proves they were exactly what the human reviewed and accepted. |

### 5.3 Allocation representation

| Reason code | Meaning |
| --- | --- |
| `SYMBOL_MISSING` | An allocation has no valid symbol. |
| `ACTION_MISSING` | An allocation has no action from which an approved side mapping can be applied. |
| `ACTION_UNSUPPORTED` | The action has no approved lossless M33.2 `TermSide` mapping. |
| `TARGET_MISSING` | Neither an approved target weight nor target value is present. |
| `TARGET_NON_FINITE` | A numeric target is NaN or infinite. |
| `TARGET_NON_POSITIVE` | A numeric target violates the M33.2 positive-value invariant. |
| `DUPLICATE_SYMBOL_SIDE` | Candidate terms contain duplicate `(symbol, side)` pairs. |
| `ZERO_TARGET_SELL_UNREPRESENTABLE` | A legacy full-sale target of zero cannot be represented as a positive M33.2 target without changing meaning. |
| `TARGET_UNIT_UNSPECIFIED` | Percentage-versus-fraction or value currency/units are not authoritatively defined. |

### 5.4 Conflict and scope

| Reason code | Meaning |
| --- | --- |
| `DUPLICATE_DECISIONS` | Multiple rows exist where one authoritative decision lineage is required, even if their payloads look identical. |
| `MULTIPLE_DECISIONS_CONFLICT` | Decision values, payloads, or metadata materially disagree. |
| `SYSTEM_EXPIRY_HUMAN_CONFLICT` | A system expiry and a human-looking decision coexist without authoritative ordering. |
| `WORKSPACE_SCOPE_MISMATCH` | Decision and source do not prove the same workspace. |
| `PORTFOLIO_SCOPE_MISMATCH` | Decision and source do not prove the same portfolio. |
| `OPTIMIZER_HISTORY_MISMATCH` | A recommendation and optimizer-history candidate do not agree or cannot be bound to the same reviewed artifact. |

### 5.5 Provenance and authority

| Reason code | Meaning |
| --- | --- |
| `SOURCE_UNAVAILABLE` | A referenced source needed to interpret or authenticate the legacy fact is missing. |
| `HUMAN_ACTOR_UNAVAILABLE` | The approving human's stable identity and authority cannot be proved. |
| `SOURCE_TIMEZONE_UNSPECIFIED` | The legacy time cannot be converted to an exact UTC instant under an approved contract. |
| `RECOMMENDATION_DEFAULT_NOT_ACCEPTED_TERMS` | Recommended allocations cannot fill missing human-accepted terms. |
| `SHADOW_SOURCE_PROHIBITED` | Shadow or diagnostic output is prohibited as intent or acceptance evidence. |
| `TRANSACTION_LINK_NOT_FULFILLMENT` | A legacy decision link on a transaction is not admitted fulfillment evidence and does not prove accepted terms. |
| `CANONICAL_PLAN_PROVENANCE_PROHIBITED` | M32 canonical planning remains NO-GO and cannot supply provenance. |

## 6. Exact adaptable and non-adaptable policy

### 6.1 Current policy

There are **zero safely `EXACT_ADAPTABLE` cases from persisted legacy rows
alone**. Consequently:

- no legacy row or row join may directly mint an `ExecutionIntentSnapshot`;
- no legacy approval label may be replayed as lifecycle `APPROVED`;
- no content hash may be presented as the hash historically approved by a
  human unless an authority contract proves that binding;
- no fallback chain may fill a missing decision-owned payload;
- duplicate, conflicting, scope-mismatched, malformed, source-missing, or
  actor-unverifiable cases must be quarantined rather than repaired or ranked;
- `REJECTED` and `EXPIRED` remain `OUT_OF_SCOPE` and create no intent; and
- `PARTIAL_EXECUTION` cannot create intent or execution evidence from its label
  or notes.

### 6.2 Sources that cannot fill missing accepted terms

- `RecommendationSnapshot` records recommended output. It may be cited as a
  legacy source or, under a later contract, seed a clearly labelled proposal;
  it cannot prove acceptance of its allocations.
- `ShadowPortfolio`, shadow holdings, shadow legs, prices, fees, and diagnostic
  output are counterfactual/evaluation artifacts and must never become intent
  evidence or accepted terms.
- `Transaction.execution_decision_id` is legacy linkage only. It cannot supply
  missing terms, validate historical approval, or establish M33.2 ledger
  fulfillment.
- Portfolio holdings and optimizer history cannot be used as silent fallbacks
  for accepted terms. A later proposal policy may name an allowed candidate
  source explicitly, but the resulting proposal still requires reconfirmation.

### 6.3 Conditions for a future exact path

A case may be considered for `EXACT_ADAPTABLE` only when additional
authoritative certification, outside the currently persisted legacy rows,
proves all of the following:

1. the complete, immutable allocation payload shown to the human;
2. the complete, immutable allocation payload the human accepted, with an
   exact digest or equivalent binding showing it is the same payload;
3. a stable human actor identity and the actor's authority for the workspace
   and portfolio at the decision time;
4. the exact recommendation/source identity and an immutable source version;
5. the workspace and portfolio scope, with no mismatch across sources;
6. an unambiguous decision lineage, including duplicate, correction, and
   supersession semantics;
7. a timezone-aware decision/source time and its approved interpretation;
8. a lossless mapping of every legacy action and target into M33.2 term
   semantics, including target units and currency where relevant;
9. successful validation under the M33.2 terms and snapshot constructors; and
10. a versioned authority-contract identifier retained in provenance/audit
    output so the conclusion is reproducible.

Failure of any requirement prevents exact adaptation. A recommendation digest
alone is insufficient because it does not prove which terms the human accepted
or who accepted them.

## 7. Prerequisites for any future adapter

Before implementing even a pure classifier/adapter, a separately approved
milestone must define:

- an authority-certificate schema and its trusted issuer or source;
- exact reviewed-payload and accepted-payload binding semantics;
- stable actor identity and authorization semantics;
- legacy timestamp and timezone interpretation;
- authoritative workspace/portfolio joins and mismatch handling;
- decision uniqueness, ordering, correction, and supersession rules;
- a versioned allocation mapping for actions, target units, values, zero-target
  sales, `HOLD`, and `WATCH`;
- the boundary between an untrusted candidate proposal and a valid M33.2
  snapshot;
- deterministic classification precedence and complete reason-code behavior;
- quarantine output that records findings without creating lifecycle events;
- how a freshly reconfirmed proposal receives new ids, provenance, content
  hash, and human approval rather than inheriting a legacy state; and
- fixture coverage for every matrix row, including duplicate/conflicting and
  source-missing cases.

Any later implementation should remain pure first: caller-supplied rows and
certificates in, classification/proposal data out, with no database reads,
writes, id generation, or runtime imports. Persistence and concurrency remain
separate adoption decisions.

## 8. Unresolved authority decisions

This study deliberately does not resolve the following questions because the
legacy rows do not contain the necessary evidence:

1. What external artifact, audit trail, or signed certificate is trusted to
   prove the exact terms displayed and accepted historically?
2. Can any existing deployment recover a stable human actor identity, and how
   is that identity authorized for the historical workspace and portfolio?
3. Does any historical producer give `approved_allocations_json` a stronger,
   versioned meaning than the current schema and writers establish? If so,
   which rows and versions are covered?
4. What timezone contract applies to legacy naive timestamps, and which time
   is the authoritative human-decision time?
5. What are the exact unit and normalization rules for target weights and
   target values?
6. How do `ACCUMULATE`, `REDUCE`, full `SELL` to zero, `HOLD`, and `WATCH` map
   without changing the reviewed meaning?
7. Which source, if any, is allowed to seed a `LEGACY_RECONSTRUCTED` proposal,
   and must that proposal exist before an M33.2 snapshot is minted?
8. What authoritative ordering or lineage resolves duplicate decisions,
   corrections, and human/system-expiry races? This study approves no
   timestamp-based or “latest row wins” rule.
9. If a historical approval certificate is available, does policy permit
   importing an approved state, or must every legacy case still receive fresh
   reconfirmation?
10. What durable quarantine record and operator workflow would exist in a
    persistence milestone without accidentally creating an intent?

Until these are explicitly decided, all apparently convertible rows remain
non-buildable.

## 9. No implementation or adoption in M33.3

M33.3 adds no pure adapter because a pure function cannot repair missing
authority. It also does not:

- modify the M33.2 contracts or transition validator;
- add an ORM model, Alembic migration, API, repository, writer, scheduler, or
  idempotency store;
- read, convert, backfill, dual-write, or quarantine production rows;
- change recommendation, decision, shadow, transaction, portfolio, ledger,
  replay, or expiry behavior;
- create a lifecycle event or `ExecutionIntentSnapshot` of any state;
- treat shadow, diagnostic, planning, or transaction-link data as intent
  evidence; or
- reopen M32 or change M31/M32/M33.1/M33.2 adoption status.

No `DECISION_LOG` entry is added. This document records a feasibility result
and applies the existing M33.1/M33.2 authority boundaries; it does not adopt a
new runtime architecture.

## 10. Recommended next milestone

**M33.4 — Historical Authority Certification and Reconfirmation Contract
(design/pure-contract only).**

M33.4 should be bounded to deciding and specifying the prerequisites in §7:
the trusted authority-certificate shape, exact terms/actor binding, scope and
time semantics, allocation normalization, duplicate/conflict authority, and
the boundary for a reconfirmation-only proposal. It should include a fixture
catalog demonstrating whether any externally certified legacy shape can
become `EXACT_ADAPTABLE` and how every other candidate is classified.

M33.4 should still add no legacy database reader, table, migration, endpoint,
writer, backfill, production quarantine workflow, or runtime adoption. A pure
adapter should be considered only after those authority decisions are approved
and testable; persistence should follow in a later milestone rather than being
combined with the authority decision.
