# M33.1 - Execution Intent Snapshot and Lifecycle Foundation

**Date:** 2026-07-16

**Status:** Design complete; implementation deferred to a bounded follow-up

**Milestone decision:** Design-only. No ORM model, migration, endpoint, writer,
backfill, or production behavior is introduced by M33.1.

## 1. Authoritative boundary

`docs/implementation/M32_EPIC_CLOSEOUT.md` is the governing predecessor for
this milestone.

- M32 is closed as foundation/shadow complete.
- Authoritative canonical execution planning remains NO-GO.
- No M32 reopen trigger is satisfied by this work.
- M31/M32 contracts remain at their existing adoption status.
- M32 shadow inputs, trade legs, policy results, and diagnostics are not
  executable evidence and are not persisted as an execution plan.
- Approval must not mutate the user portfolio or write a transaction.
- Broker integration, order routing, live execution, and transaction
  admission/requote are outside M33.1.

Graphify was used only to locate relevant code and documents. Every finding
below was verified against the actual source, migrations, architecture
documents, and focused tests.

## 2. Executive conclusion

The current system has recommendation evidence, human-response records,
paper portfolios, actual transactions, and derived portfolio state. It does
not have an immutable record of the exact action terms a human intended, nor
an enforced lifecycle connecting those terms to later ledger evidence.

`UserExecutionDecision` currently spans four meanings that must be separated:

1. a human verdict on a recommendation;
2. a system-authored expiry marker;
3. an implied statement of execution intent; and
4. an evaluation label that sometimes describes an outcome.

M33.1 defines the missing middle record without adopting a canonical plan:

```text
RecommendationSnapshot       advisory evidence
          |
          v
UserExecutionDecision        human/system response fact
          |
          v
ExecutionIntent              stable identity for one engaged objective
          |
          v
ExecutionIntentSnapshot      immutable, human-reviewed terms revision
          |
          v
append-only lifecycle        what became of those exact terms
          |
          +----> shadow diagnostics / simulated outcomes (non-authoritative)
          |
          +----> transaction links / fulfillment assessment (future, read-only)
                         |
                         v
                    Transaction ledger
                         |
                         v
                    portfolio replay/state
```

This document makes concrete architectural decisions, but implementation is
deferred. The legacy data does not support an honest automatic mapping for
partial execution, incomplete overrides, conflicting duplicate decisions, or
heterogeneous shadow sources. Adding persistence before resolving those cases
would create false authority rather than a safe additive foundation.

## 3. Evidence reviewed and verification

### 3.1 Source and schema

- `backend/models/database.py`
  - `OptimizerHistory`
  - `Transaction`
  - `RecommendationSnapshot`
  - `UserExecutionDecision`
  - `ShadowPortfolio`
  - `ShadowPortfolioSnapshot`
- `backend/services/decision_memory/snapshot_writer.py`
- `backend/services/evaluation/expired_writer.py`
- `backend/services/decision_memory/shadow_tracker.py`
- `backend/services/evaluation/execution_ledger.py`
- `backend/services/portfolio_transactions.py`
- `backend/main.py`
  - optimizer completion and recommendation snapshot creation
  - decision endpoints
  - shadow endpoints
  - transaction endpoints
- decision-memory and evaluation migrations

### 3.2 Architecture and predecessor documents

- `docs/implementation/M32_EPIC_CLOSEOUT.md`
- `docs/implementation/M32_cost_aware_execution_planning_design.md`
- `docs/architecture/EXECUTION_DOMAIN.md`
- `docs/architecture/TRANSACTION_DOMAIN_MODEL.md`
- `docs/architecture/PORTFOLIO_DOMAIN_MODEL.md`
- `docs/investment/OPTIMIZER_PHILOSOPHY.md`
- `docs/engineering/ENGINEERING_PRINCIPLES.md`

The conceptual architecture is directional authority, but current-runtime
claims in this document come from source. In particular, the current schema's
`Transaction.execution_decision_id` points from transaction to decision even
though the target architecture prefers decision-owned outcome linkage.

### 3.3 Focused tests

The following suites passed together: **57 passed**.

- `backend/tests/test_horizon_grader.py`
- `backend/tests/test_shadow_tracker_cash_accounting.py`
- `backend/tests/test_shadow_regeneration.py`
- `backend/tests/test_execution_decision_linkage.py`
- `backend/tests/test_execution_ledger.py`

They verify expiry and supersession behavior, recommendation-shadow
idempotency, shadow NAV/cash behavior, deterministic regeneration,
metadata-only transaction linkage, and execution-ledger comparison. There is
no focused backend endpoint suite proving duplicate-decision rejection or
portfolio/snapshot/link consistency; the endpoint currently implements no such
guards.

## 4. Current domain inventory

| Record | Current identity | Current source | Mutation model | Authority |
|---|---|---|---|---|
| `OptimizerHistory` | integer primary key | one successful optimizer run | inserted per run | persisted run/history payload; not execution authority |
| `RecommendationSnapshot` | integer primary key; `optimizer_history_id` is unique | selected optimizer-run context and projected allocations | inserted; no normal update path, but deletable by cascade | advisory/evaluation evidence; not a canonical execution plan |
| `UserExecutionDecision` | integer primary key | decision endpoint or expiry writer | new row per write; no update endpoint | response/evaluation record; not proof of intent terms or execution |
| `ShadowPortfolio` | integer primary key | recommendation, decision, or portfolio fallback depending factory | mutable paper projection | diagnostic/counterfactual only |
| `ShadowPortfolioSnapshot` | integer primary key; unique `(shadow_portfolio_id, snapshot_date)` | paper valuation | upserted and regenerable | simulated outcome only |
| `Transaction` | integer primary key | explicit transaction service | inserted while holdings/cash projection is mutated | current economic ledger fact |
| `PortfolioItem` / `Portfolio` | integer identity | transaction mutation and rebuild paths | updated in place / rebuildable | current materialized portfolio state; ledger remains replay authority |

## 5. Verified current-state behavior

### 5.1 RecommendationSnapshot identity

`write_recommendation_snapshot()` runs after `OptimizerHistory` is committed.
It first looks up by `optimizer_history_id`, and the database also enforces a
unique constraint on that field. The result is one recommendation snapshot per
optimizer-history row.

Its `id` is the durable local reference used by decisions, shadows, and
grades. It has no semantic content hash, schema version, external idempotency
key, revision chain, or correction/supersession link. Workspace and portfolio
consistency with the referenced `OptimizerHistory` are conventional rather
than enforced by a composite foreign key.

The snapshot freezes optimizer evidence and `projected_allocations_json`. It
does not freeze a canonical cost-aware execution plan, executable price,
order, or admission decision.

### 5.2 UserExecutionDecision relationship and statuses

Each decision has a required FK to one `RecommendationSnapshot`, plus repeated
workspace and portfolio ids. The endpoint validates the snapshot's workspace,
but it does not require `body.portfolio_id == snapshot.portfolio_id`.

The complete runtime vocabulary is:

| Value | Writer | Current meaning |
|---|---|---|
| `APPROVED` | human endpoint | accepts the recommendation at decision level; does not execute it |
| `REJECTED` | human endpoint | declines the recommendation |
| `PARTIAL_EXECUTION` | human endpoint | evaluation label for partial following/execution; exact accepted terms are not structurally required |
| `MANUAL_OVERRIDE` | human endpoint | records divergence and optional structured override fields; complete replacement terms are not required |
| `EXPIRED` | scheduler | system marker for an undecided recommendation that aged out or was superseded |

There is no persisted `PENDING` decision. Absence of any decision row means
undecided.

### 5.3 Append-only behavior

The normal decision and expiry paths only insert. They do not update an
existing decision. This is append-only behavior by convention, not a schema
invariant:

- there is no unique constraint on recommendation snapshot id;
- the decision endpoint does not check for an existing row;
- duplicate or conflicting decisions can be appended through the API;
- the UI merely hides decision controls after it finds one row;
- recommendation/portfolio deletion can cascade-delete decision rows; and
- no transition sequence or supersedes link explains multiple rows.

Consequently, “latest decision wins” is not a defined domain rule even though
some readers order decisions by `executed_at`.

### 5.4 Expiry and recommendation supersession

`write_expired_decisions()` groups recommendation snapshots by workspace and
portfolio, then walks newest to oldest.

An undecided snapshot receives a new
`UserExecutionDecision(decision="EXPIRED", is_system_generated=True)` when:

1. its age in calendar dates is at least the configured `expiry_days`
   (default 14); or
2. a newer snapshot for the same portfolio has any decision, including an
   `EXPIRED` row written earlier in the same pass.

Any existing decision makes the snapshot decided and untouched. The writer's
pre-read set makes repeat serial passes operationally idempotent, and the
newest-to-oldest walk intentionally cascades supersession in one pass. A
concurrent writer is not protected by a database uniqueness constraint. Age
is calculated from `date.today()` and a naive `created_at.date()`, not from a
timezone-aware expiry instant.

This is recommendation non-response expiry. It must not be copied unchanged
as execution-intent expiry. A newer recommendation currently expires only an
older *undecided recommendation*; it does not revoke a prior human approval.

### 5.5 Approval, rejection, partial, and manual handling

The decision endpoint always commits the `UserExecutionDecision` before it
performs shadow work.

- `APPROVED` creates a decision-keyed `STATIC_FROZEN` shadow, creates or
  rebalances the portfolio's `ACTIVE_MODEL` shadow, values both, and starts
  background attribution.
- A non-approved decision creates a decision-keyed `STATIC_FROZEN` shadow when
  `create_static_shadow=true`. The current optimizer UI sets that flag for
  rejected, partial, and manual-override decisions.
- No decision branch calls `execute_buy()`, `execute_sell()`, or another
  transaction writer.
- Shadow failure is caught after the decision commit; it does not roll back the
  decision.

Approval therefore means “human response recorded and paper diagnostics
started,” not “portfolio changed,” “transaction admitted,” “order requested,”
or “execution completed.”

### 5.6 Shadow creation and regeneration sources

There are three materially different shadow paths:

| Path | Type | Source of terms | Identity/idempotency |
|---|---|---|---|
| recommendation counterfactual | `STATIC_FROZEN`, `execution_decision_id=NULL` | `RecommendationSnapshot.projected_allocations_json` | application lookup returns existing row; no matching DB unique constraint |
| decision-time frozen shadow | `STATIC_FROZEN`, decision linked | decision approved allocations, else linked recommendation, else actual current holdings | always inserts; no one-per-decision constraint |
| model-following shadow | `ACTIVE_MODEL` | latest recommendation projected allocations | reuses the latest active row found for a portfolio, otherwise inserts; no one-active-row DB constraint |

The optimizer completion path creates/refreshes the active model shadow and
creates the recommendation-keyed frozen shadow before any human decision. An
approval repeats the active-model create/rebalance call and adds the
decision-keyed frozen shadow.

The shadow factories load referenced decision/snapshot rows by id without a
workspace predicate and trust separately supplied workspace/portfolio values.
Normal call sites supply related values, but cross-field scope consistency is
not enforced by the factories or composite database constraints.

`ShadowPortfolio` is mutable. An `ACTIVE_MODEL` row overwrites its current
recommendation link, holdings JSON, and paper cash on rebalance while retaining
its original inception. Daily shadow snapshots are one-per-day upserts.
Regeneration rewrites derived paper cash, holdings, current values, and daily
snapshot data while preserving shadow identity and inception facts.

Static regeneration uses the shadow's stored holdings/weights. Active-model
regeneration replays historical recommendation snapshots. Neither path writes
actual transactions, portfolio items, user decisions, or recommendations.

### 5.7 Transactions and actual portfolio state

The actual BUY/SELL endpoints are separate user-entered workflows. They accept
quantity and price, call transaction services, insert `Transaction`, and
mutate `PortfolioItem` plus portfolio cash in the same service commit.

An optional `execution_decision_id` is copied verbatim onto BUY/SELL
transactions. The FK proves only that a decision row exists. The endpoint does
not prove that the decision:

- is `APPROVED` or `PARTIAL_EXECUTION`;
- belongs to the same workspace or portfolio;
- refers to the same symbols or amounts; or
- has not expired or been contradicted.

The execution ledger is read-only. It reconstructs the legacy plan from the
recommendation snapshot and compares it with transactions carrying the
metadata link. It correctly reports unavailable/partial analysis; it is not
transaction admission and does not turn the decision into ledger truth.

No current decision automatically mutates the user portfolio or writes a
canonical transaction. Actual state changes only through transaction paths;
portfolio replay remains independent of decision and shadow objects.

### 5.8 Existing idempotency and uniqueness protections

| Boundary | Protection | Limitation |
|---|---|---|
| recommendation per optimizer run | unique `RecommendationSnapshot.optimizer_history_id` plus lookup | no content hash/revision; writer swallows failure |
| user decision per recommendation | none | duplicates/conflicts possible |
| expiry writer | pre-read decided-id set | race can duplicate; no unique constraint |
| recommendation frozen shadow | lookup by snapshot/type/null decision | race can duplicate; no unique constraint |
| decision frozen shadow | none | repeated calls create new rows |
| active model shadow | lookup for latest active row | race can create multiple active rows |
| daily shadow valuation | unique `(shadow_portfolio_id, snapshot_date)` | row is intentionally updated/regenerated, not immutable |
| transaction creation | database primary key | no request idempotency key/content identity in this path |
| transaction-decision link | nullable FK | no semantic scope/status validation |

## 6. Semantic boundaries M33 must preserve

| Concept | Meaning | Authoritative owner | Must not be treated as |
|---|---|---|---|
| Recommendation evidence | What the optimizer advised, with its then-known context | `RecommendationSnapshot` / intelligence history | human consent, intent, order, fill, or portfolio fact |
| Human decision | The person's response to advice: approve, reject, defer, modify, override | decision record | exact execution terms unless they were separately frozen |
| Execution intent | The exact, versioned terms the human chose to pursue | M33 Execution Domain | plan calculation, order, transaction, or proof of completion |
| Execution-plan/shadow diagnostic | A deterministic or simulated view of possible actions and feasibility | legacy planning/M32 shadow/evaluation owners | canonical intent, admission authority, or ledger fact |
| Simulated shadow outcome | Paper performance under stated counterfactual rules | shadow/evaluation subsystem | actual return, actual holding, or execution evidence |
| Actual transaction | An admitted economic fact at actual terms | transaction ledger | recommendation, intent, or evaluation label |
| Actual portfolio state | Deterministic replay/materialized projection of transactions | Portfolio/Replay | something intent or shadow may update directly |

The safe direction of influence is one-way:

```text
evidence -> decision -> intent -> optional attribution link -> transaction
                                                        transaction -> replay

shadow diagnostics may read evidence/decision/intent
shadow diagnostics may never create transaction or portfolio truth
```

## 7. Current semantic overload and missing boundaries

### 7.1 UserExecutionDecision overload

- The model name says user-authored while `EXPIRED` is system-authored.
- `decision` mixes verdict (`APPROVED`, `REJECTED`), divergence
  (`MANUAL_OVERRIDE`), and outcome (`PARTIAL_EXECUTION`).
- `executed_at` is populated when the decision is recorded, without execution.
- `approved_allocations_json` is described as what was actually executed, but
  no transaction is required and the UI commonly sends no allocations.
- A snapshot can have multiple decisions with no correction/revision semantics.

### 7.2 Recommendation/plan overload

`RecommendationSnapshot` freezes target allocations and optimizer outputs. It
is useful advisory evidence, but it has neither a versioned executable-plan
contract nor the M32 evidence required for a canonical cost-aware plan. M33
must reference it as provenance without promoting it.

### 7.3 Shadow overload

`STATIC_FROZEN` can mean recommendation counterfactual, decision baseline, or
actual-holdings fallback. `ACTIVE_MODEL` is a continuing simulated strategy
whose source recommendation changes over time. A shadow row therefore cannot
serve as the immutable terms of a human intent.

### 7.4 Outcome/linkage overload

The transaction's nullable decision FK is evaluation metadata, but consumers
may be tempted to read it as proof that the planned action was approved and
fulfilled. It proves neither. Conversely, marking a decision `APPROVED` or
`PARTIAL_EXECUTION` supplies no admitted transaction evidence.

### 7.5 Missing boundaries

The current runtime lacks:

- stable execution-intent identity;
- immutable terms revisions and content identity;
- append-only lifecycle transitions;
- an explicit human actor and two-timeline audit record;
- enforced terminal-state and supersession rules;
- intent-specific expiry policy/provenance;
- idempotent command handling;
- decision-to-intent cardinality and consistency rules;
- append-only intent-to-transaction attribution owned outside replay; and
- ledger-derived fulfillment status.

## 8. Proposed M33 execution-intent foundation

### 8.1 Design goals

1. Preserve the exact terms a human reviewed and chose without calling them an
   order or transaction.
2. Keep recommendation, decision, intent, diagnostics, simulated outcome, and
   actual outcome as separate records.
3. Make terms and lifecycle audit history append-only.
4. Let actual fulfillment be derived only from canonical transaction evidence.
5. Permit future canonical-plan provenance without adopting M32 planning now.
6. Make retries boring and conflicts loud.

### 8.2 Aggregate shape

The future aggregate should contain three core records and one later linkage:

```text
ExecutionIntent                     stable identity and portfolio scope
  1 ---- N ExecutionIntentSnapshot  immutable terms revisions
              1 ---- N ExecutionIntentTransition
                                     append-only state history

ExecutionIntentSnapshot
  1 ---- N ExecutionIntentTransactionLink   future, append-only attribution
                         N ---- 1 Transaction
```

No mutable status or terms JSON is authoritative on `ExecutionIntent`. Current
revision and state are projections derived from snapshots and transitions.
A cached pointer may be added only as a rebuildable optimization.

### 8.3 ExecutionIntent identity

`ExecutionIntent` represents one continuously recognizable human-engaged
economic objective inside one portfolio. Its identity is not derived from a
symbol, recommendation id, status, timestamp, or terms hash.

Proposed identity rules:

- application-generated opaque `intent_id` (UUID) is stable across revisions;
- workspace and portfolio scope are immutable;
- one initial intent may reference at most one originating legacy decision;
- one legacy decision may originate at most one intent aggregate;
- a later recommendation creates a new intent unless a human explicitly says
  it replaces the terms of an engaged intent;
- similarity of symbols, allocations, or dates never implies identity; and
- after the execution-request threshold, changed or corrective terms require a
  new intent rather than revision of the in-flight one.

The database may retain an integer surrogate key for local joins, but the
opaque intent id is the domain identity and idempotency reference.

### 8.4 Immutable ExecutionIntentSnapshot

Each snapshot freezes one exact revision of the terms placed before or chosen
by the human. It is a volitional contract, not an execution plan or order.

Minimum contract:

| Field | Semantics |
|---|---|
| `snapshot_id` | opaque immutable snapshot identity |
| `intent_id` | stable aggregate identity |
| `revision` | positive, gap-free sequence unique within the intent |
| `supersedes_snapshot_id` | prior terms revision, if any; linear chain only |
| `terms_schema_version` | version of the exact terms grammar |
| `intent_kind` | `FOLLOW_RECOMMENDATION`, `PARTIAL_FOLLOW`, `MANUAL_OVERRIDE`, or `MANUAL_INDEPENDENT` |
| `terms` | exact human-reviewed allocation/action terms; never silently reconstructed later |
| `workspace_id`, `portfolio_id` | immutable scope copied for integrity checks |
| `source_provenance` | typed source references, versions, hashes, and reconstruction status |
| `created_by_actor` | accountable human/system identity; system may propose but not approve |
| `effective_at` | event-time applicability |
| `recorded_at` | knowledge-time insertion |
| `expires_at` | explicit expiry instant or null; never inferred at read time |
| `content_hash` | deterministic hash of canonical immutable content |

For a legacy allocation-intent grammar, `terms` may freeze exactly the
human-reviewed target/action representation. It must not claim executable
quantity, side-aware price, fee, routing, order type, broker account,
admission, or fill certainty. A future canonical plan may be referenced as a
different source contract only after a separate adoption decision.

An approved snapshot must contain complete terms. A bare legacy
`MANUAL_OVERRIDE`, a partial label without accepted terms, or a duplicate set
of conflicting decisions is not sufficient to mint an approved intent.

### 8.5 Source provenance

Provenance must be typed, copied, and independently auditable. Proposed source
kinds are:

- `LEGACY_RECOMMENDATION_SNAPSHOT`;
- `LEGACY_USER_EXECUTION_DECISION`;
- `MANUAL_HUMAN_INPUT`; and
- `FUTURE_CANONICAL_EXECUTION_PLAN` (reserved, not adopted by M33.1).

`M32_SHADOW_DIAGNOSTIC` is explicitly prohibited as an intent source.

For each source, retain its local id when available, contract/schema version,
source creation time, deterministic digest, and one of:

- `EXACT_FROZEN` - the reviewed terms were captured exactly;
- `LEGACY_RECONSTRUCTED` - a compatibility adapter reconstructed terms and the
  limitation is visible; or
- `INCOMPLETE` - no approved intent may be minted.

Foreign keys to legacy recommendation/decision rows should use `SET NULL` or a
separate reference table, not cascade-delete intent history. The immutable
source reference and digest remain even when a legacy source is unavailable.
`OptimizerHistory` is upstream provenance through the recommendation; it is
not itself human intent.

### 8.6 Revision semantics

1. Lifecycle transitions never edit a snapshot.
2. Any terms change creates revision `N+1` with a new content hash.
3. Creating a replacement revision atomically appends `SUPERSEDED` for the old
   revision and `PENDING_REVIEW` for the new revision. An old approval does not
   authorize changed terms.
4. A changed approved revision therefore requires a new explicit approval.
5. A human-approved replacement may perform supersession and approval in one
   atomic command when the replacement terms themselves were the object of
   that approval.
6. Only a human act may supersede an approved snapshot. A newer optimizer run
   never silently revokes or rewrites human authorization.
7. After `EXECUTION_REQUESTED` or any linked actual transaction, terms do not
   revise. Cancel the unfulfilled remainder if appropriate and create a new
   intent for new terms.
8. Corrections append a new snapshot/transition with a reason and correlation
   id; they never edit historical content.

### 8.7 Lifecycle states

The lifecycle describes what happened to an exact intent snapshot. It does not
change the snapshot's terms.

| State | Meaning | Authority | Terminal? | M33.1 runtime availability |
|---|---|---|---|---|
| `PENDING_REVIEW` | concrete frozen terms await a human verdict | creation/submit event | no | design only |
| `DEFERRED` | human explicitly chose “not now”; approval is not implied | human transition | no | design only |
| `APPROVED` | human authorized this exact snapshot; no execution claim | human transition | no | design only |
| `QUARANTINED` | validation uncertainty blocks progress without guessing | future validation | no | reserved |
| `EXECUTION_REQUESTED` | the intent crossed the future instruction threshold | future admission/orchestration | no | reserved; no writer |
| `PARTIALLY_EXECUTED` | admitted ledger evidence fulfills some terms | ledger-derived assessment | no | reserved; not asserted |
| `COMPLETED` | admitted ledger evidence fully accounts for the terms | ledger-derived assessment | yes | reserved; not asserted |
| `REJECTED` | human declined the frozen terms | human transition | yes | design only |
| `CANCELLED` | human terminated the unfulfilled intent or remainder | human transition | yes | design only |
| `EXPIRED` | explicit time/policy rule invalidated unfulfilled terms | policy transition | yes | design only |
| `SUPERSEDED` | an explicit replacement revision took authority | atomic revision command | yes for that revision | design only |

`PARTIALLY_EXECUTED` and `COMPLETED` are lifecycle views derived from admitted
transactions and append-only links. A command must never set them merely
because an order was requested, an approval exists, or a shadow moved.

Cancellation after partial execution terminates only the remainder. Existing
transactions remain actual facts and the outcome view continues to expose the
partial fulfillment.

### 8.8 Allowed transitions

| From | Allowed next state | Required evidence |
|---|---|---|
| none | `PENDING_REVIEW` | immutable complete terms and source provenance |
| `PENDING_REVIEW` | `APPROVED` | explicit human approval of this snapshot hash |
| `PENDING_REVIEW` | `DEFERRED` | explicit human deferral |
| `PENDING_REVIEW` | `REJECTED`, `CANCELLED` | explicit human act |
| `PENDING_REVIEW` | `EXPIRED` | frozen expiry/policy rule and due instant |
| `PENDING_REVIEW` | `SUPERSEDED` | atomic replacement revision |
| `DEFERRED` | `PENDING_REVIEW` | explicit resume; requires fresh review |
| `DEFERRED` | `CANCELLED`, `EXPIRED`, `SUPERSEDED` | human act or explicit due rule |
| `APPROVED` | `DEFERRED` | human postponement; re-approval required on resume |
| `APPROVED` | `QUARANTINED` | typed validation failure/uncertainty |
| `APPROVED` | `EXECUTION_REQUESTED` | future admission contract; unavailable in M33.1 |
| `APPROVED` | `CANCELLED`, `EXPIRED` | human act or explicit pre-request expiry rule |
| `APPROVED` | `SUPERSEDED` | human-authorized replacement only |
| `QUARANTINED` | `PENDING_REVIEW` | issue resolved; human reconfirmation required |
| `QUARANTINED` | `CANCELLED`, `EXPIRED`, `SUPERSEDED` | explicit evidence |
| `EXECUTION_REQUESTED` | `PARTIALLY_EXECUTED`, `COMPLETED` | admitted ledger evidence only |
| `EXECUTION_REQUESTED` | `CANCELLED`, `QUARANTINED` | cancel/reconciliation or validation evidence |
| `PARTIALLY_EXECUTED` | `COMPLETED` | additional admitted ledger evidence |
| `PARTIALLY_EXECUTED` | `CANCELLED`, `QUARANTINED` | remainder termination or reconciliation evidence |
| terminal state | none | corrections create a new intent/revision event chain |

Invalid transitions must fail closed and append nothing. A transition carries
the prior-state expectation so concurrent commands cannot both advance the
same revision.

### 8.9 Supersession and expiry rules

Recommendation expiry and intent expiry are distinct policies.

1. Current legacy recommendation expiry remains unchanged.
2. No legacy `EXPIRED` decision is automatically converted into an intent.
3. An intent snapshot expires only from its own frozen `expires_at` and policy
   provenance.
4. Expiry is an append-once transition with a deterministic event key.
5. Expiry is permitted only before the execution-request threshold in the
   foundation. Future remainder-expiry semantics require a separate decision.
6. A newer recommendation may supersede a pending/deferred proposal only when
   an explicit orchestration rule creates a replacement revision.
7. A newer recommendation never automatically supersedes an approved intent.
8. Supersession and replacement creation are atomic; the system must not leave
   two active revisions or neither revision recorded.
9. `SUPERSEDED`, `EXPIRED`, and `REJECTED` mean different things and remain
   separately queryable for evaluation.

### 8.10 Relationship to RecommendationSnapshot and UserExecutionDecision

- `RecommendationSnapshot` remains immutable advisory evidence by convention
  and is referenced as source provenance, never as executable authority.
- `UserExecutionDecision` remains the legacy response record during
  compatibility. M33.1 does not rename it, constrain its values, add a unique
  key, or change downstream acceptance calculations.
- Rejected and expired decisions do not create execution intent.
- Approved legacy decisions may create an intent only when the exact approved
  terms are available and consistent.
- Partial and manual-override decisions require complete structured human
  terms. A label and notes alone are insufficient.
- No historical automatic backfill is approved. Legacy rows remain readable
  through their existing evaluation paths.
- Future decision recording should atomically append the human-decision fact,
  intent snapshot, and initial lifecycle transition, but only in a separately
  approved persistence/adoption milestone.

### 8.11 Relationship to ShadowPortfolio

Shadows remain projections outside the intent authority boundary.

- Recommendation-keyed shadows measure recommendation counterfactuals.
- Decision-keyed shadows currently approximate decision-time counterfactuals.
- Active-model shadows simulate continued model compliance.
- Shadow valuation and regeneration never advance intent lifecycle.
- Intent expiry/cancellation never deletes or rewrites shadow history.
- A future exact-intent shadow may reference `ExecutionIntentSnapshot`, but it
  must use a distinct source/type and may not overload current
  `STATIC_FROZEN` semantics silently.
- Existing shadows are not backfilled as intent snapshots because their source
  terms are heterogeneous and mutable in the active-model case.

### 8.12 Relationship to transactions, outcomes, and portfolio state

M33.1 adds no transaction write path.

A future `ExecutionIntentTransactionLink` should be an append-only attribution
record owned by the Execution Domain. It may reference an admitted transaction
and state why/how the transaction was matched. It must not edit transaction
amounts, identity, fees, dates, or replay behavior.

Proposed link invariants:

- unique `(intent_snapshot_id, transaction_id, link_role)`;
- link provenance and knowledge time are required;
- a metadata FK from a legacy transaction is a candidate hint, not sufficient
  proof of fulfillment;
- a transaction linked to multiple intents is surfaced as an attribution
  conflict unless an explicit allocation record explains the split; and
- unlink/correction is append-only, never destructive.

Execution outcome is a derived assessment over:

```text
immutable intent terms
  + admitted transactions
  + append-only attribution links
  + versioned matching/reconciliation rules
  = fulfillment view
```

The fulfillment view may report no evidence, partial, complete, excess, or
conflict. It does not create accounting truth. Transactions remain the only
economic facts, and actual portfolio state remains a replay/materialized view
of transactions alone.

## 9. Idempotency and audit invariants

The following are mandatory for any implementation milestone:

1. An intent id is opaque, stable, and never reused.
2. Workspace and portfolio scope never change.
3. Snapshot content is immutable after insert.
4. `(intent_id, revision)` is unique and revisions are gap-free.
5. A snapshot has at most one direct successor; the revision chain is linear.
6. Snapshot content hash is deterministic and verified on read/audit.
7. Every lifecycle transition is append-only, sequenced, actor-attributed, and
   carries event time plus knowledge time.
8. `(intent_snapshot_id, transition_sequence)` is unique.
9. Every command has an idempotency key. Same key plus same content returns the
   existing result; same key plus different content is a conflict.
10. Expected prior state/version is required for a transition.
11. Terminal states have no outbound transitions.
12. Replacement snapshot creation and predecessor supersession are atomic.
13. Approval binds the actor to the exact snapshot id and content hash.
14. System actors may expire/quarantine according to frozen policy; they may
    not manufacture human approval.
15. A shadow row or diagnostic can never satisfy lifecycle evidence.
16. `PARTIALLY_EXECUTED` and `COMPLETED` require admitted transaction evidence.
17. Intent records never mutate a transaction or portfolio projection.
18. Replay never consumes intent, decision, lifecycle, shadow, or attribution
    metadata.
19. Source loss does not erase intent history; copied provenance remains.
20. Audit detects duplicate active revisions, sequence gaps, hash mismatch,
    invalid transitions, orphaned provenance, and ambiguous transaction links;
    it does not silently repair them.
21. All new lifecycle timestamps are timezone-aware UTC instants; display
    dates and policy calendars are derived explicitly from a named timezone.

## 10. Compatibility plan

M33.1 changes documentation and architectural decisions only.

- Existing tables, values, endpoints, responses, UI, scheduler, shadows,
  evaluation services, and transaction paths remain unchanged.
- `APPROVED` continues to create/value shadows and does not mutate the user
  portfolio.
- Existing recommendation expiry remains unchanged.
- Existing `Transaction.execution_decision_id` remains metadata-only.
- Existing M31 mode and M32 shadow/adoption states remain unchanged.
- No canonical plan, plan snapshot, order, fill, broker instruction, or live
  execution surface is introduced.
- No legacy data is rewritten or automatically backfilled.

## 11. Explicit non-goals

M33.1 does not:

- reopen M32 or satisfy an M32 adoption gate;
- adopt, publish, or persist a canonical cost-aware execution plan;
- treat legacy projected allocations as broker-ready instructions;
- treat M32 shadow legs, prices, fees, or policy results as approved evidence;
- change recommendation or decision adoption semantics;
- make approval change holdings, cash, or transactions;
- add transaction admission, requoting, broker accounts, orders, routing,
  placement, cancellation, fills, or reconciliation;
- implement execution-outcome matching or change the execution ledger;
- add ORM models, migrations, endpoints, background writers, or frontend;
- backfill legacy decisions or shadows into intents;
- repair current duplicate/idempotency limitations; or
- change portfolio replay, accounting, fee, tax, or cost-basis rules.

## 12. Next bounded milestone recommendation

Proceed with **M33.2 - Pure Execution Intent Contract and Transition
Validator**.

Scope:

1. Add frozen, ORM-free domain types for `ExecutionIntentSnapshot`, source
   provenance, lifecycle state, transition command, and transition event.
2. Add deterministic canonical serialization/content hashing.
3. Add a pure transition validator implementing the table in section 8.8.
4. Add unit/property tests for immutability, valid/invalid transitions,
   terminal states, revision chains, actor authority, expiry boundaries,
   supersession atomic-command output, and idempotency-key conflicts.
5. Keep all runtime writers, ORM, migrations, APIs, legacy adapters, shadows,
   transactions, and portfolio state untouched.

Exit criteria:

- same input contract and command produce byte-equivalent output;
- invalid transitions produce typed refusal and no event;
- approval binds to an exact content hash;
- system actors cannot approve;
- completion cannot be constructed without explicit ledger-evidence input;
- M31/M32 and legacy decision behavior remain byte-for-byte unchanged; and
- the focused current-state suite remains green.

Only after those pure contracts stabilize should a separate persistence
milestone propose tables, migration, concurrency constraints, and an explicit
legacy-adapter policy. Runtime dual-write or UI adoption requires another
separately approved milestone and evidence that ambiguous legacy cases are
quarantined rather than guessed.

## 13. M33.1 decision summary

| Question | Decision |
|---|---|
| Is a recommendation a pending execution intent? | No |
| Is `UserExecutionDecision` sufficient intent evidence? | Not without complete exact terms |
| Does approval execute or mutate the portfolio? | No |
| Can a shadow be the intent snapshot? | No |
| Can a transaction metadata link prove fulfillment? | No |
| What is the stable identity? | opaque `ExecutionIntent` id scoped to workspace/portfolio |
| What is immutable? | every `ExecutionIntentSnapshot` terms revision and every transition event |
| How does state change? | append-only transition history with expected prior state |
| How are actual outcomes known? | derived from admitted transactions plus audited attribution links |
| Does a new recommendation revoke approval? | Never automatically |
| Is M33.1 design-only? | Yes |
| What comes next? | pure immutable contracts and transition tests, no persistence/adoption |
