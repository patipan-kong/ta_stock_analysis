# M33.2 - Pure Execution Intent Contract and Transition Validator

**Date:** 2026-07-16

**Status:** Implemented. Pure, ORM-free contracts and a pure transition
validator only. No runtime adoption.

**Milestone decision:** Add frozen domain types for the M33.1 Execution
Intent design and a pure lifecycle transition validator, with deterministic
canonical serialization/hashing and pure idempotency resolution. No ORM
model, migration, endpoint, repository, background writer, dual-write from
`UserExecutionDecision`, or change to `RecommendationSnapshot`,
`ShadowPortfolio`, `Transaction`, `Portfolio`, or replay behavior is
introduced.

## 1. Authoritative boundary

`docs/implementation/M33_1_execution_intent_snapshot_lifecycle_foundation.md`
is the governing design for this milestone; `docs/implementation/M32_EPIC_CLOSEOUT.md`
remains the governing predecessor. Both are preserved unchanged:

- M32 remains closed; canonical execution planning remains NO-GO.
- Nothing in this milestone reopens M32 or claims M32 shadow evidence is
  executable.
- Approval remains non-executing: this module has no transaction, order, or
  portfolio-mutation path at all — it is pure data-in/data-out.
- Existing `RecommendationSnapshot`, `UserExecutionDecision`,
  `ShadowPortfolio`, `Transaction`, and replay behavior are untouched; the new
  modules are not imported anywhere in `main.py`, a router, or a service that
  the running application executes.

## 2. Implemented contracts

### `backend/services/execution_intent_contracts.py`

| Type | Purpose |
| --- | --- |
| `ActorType`, `Actor` | HUMAN vs SYSTEM authority identity |
| `SourceKind` | `LEGACY_RECOMMENDATION_SNAPSHOT`, `LEGACY_USER_EXECUTION_DECISION`, `MANUAL_HUMAN_INPUT`, and reserved `FUTURE_CANONICAL_EXECUTION_PLAN` — no shadow/diagnostic member exists |
| `ProvenanceCompleteness` | `EXACT_FROZEN` / `LEGACY_RECONSTRUCTED` / `INCOMPLETE` |
| `SourceProvenance` | typed source reference: kind, local id, contract version, source time, digest, completeness |
| `IntentKind` | `FOLLOW_RECOMMENDATION` / `PARTIAL_FOLLOW` / `MANUAL_OVERRIDE` / `MANUAL_INDEPENDENT` |
| `TermSide`, `ExecutionIntentAllocationTerm`, `ExecutionIntentTerms` | the exact reviewed allocation terms (symbol, side, target weight **or** value — never an executable quantity/price/order) |
| `LifecycleState`, `TERMINAL_LIFECYCLE_STATES` | the eleven M33.1 §8.7 states |
| `ExecutionIntentSnapshot` | one immutable terms revision, built only via `build_execution_intent_snapshot()` |
| `build_execution_intent_terms()` | validates non-empty, unique (symbol, side), exactly-one-of weight/value, positive values |
| `compute_snapshot_content_hash()` / `build_execution_intent_snapshot()` | canonical hashing and the sole snapshot constructor |

`snapshot_id` and `intent_id` are caller-supplied opaque strings. This module
never calls a random id generator, so identical inputs always produce
byte-equivalent output — a future persistence milestone owns id-generation
policy (e.g. `uuid4()` at write time).

`build_execution_intent_snapshot()` refuses to build if any
`SourceProvenance.source_kind == FUTURE_CANONICAL_EXECUTION_PLAN`: canonical
execution planning is NO-GO, so this milestone refuses even to let a snapshot
cite it as provenance.

### `backend/services/execution_intent_transitions.py`

| Type | Purpose |
| --- | --- |
| `TransitionCommandType` | the 13 command verbs (`SUBMIT`, `APPROVE`, `DEFER`, `RESUME`, `REJECT`, `CANCEL`, `EXPIRE`, `QUARANTINE`, `RESOLVE_QUARANTINE`, `REQUEST_EXECUTION`, `RECORD_PARTIAL_EXECUTION`, `RECORD_COMPLETION`, `SUPERSEDE_WITH_REPLACEMENT`) |
| `LedgerEvidenceEntry`, `AdmittedLedgerEvidence` | typed admitted-transaction facts only (`transaction_ref`, `symbol`, `side`, `quantity`, `recorded_at`) — structurally cannot be built from a shadow/diagnostic object |
| `FulfillmentOutcome`, `assess_fulfillment()` | pure symbol/side coverage comparison between terms and ledger evidence |
| `TransitionCommand` | the command payload, including `idempotency_key`, `expected_prior_state`, `expected_prior_transition_sequence` |
| `SnapshotLifecycleContext` | the exact current snapshot/state/sequence a command is expected to apply to |
| `TransitionEvent` | one immutable, append-only lifecycle fact |
| `TransitionRefusalReason`, `TransitionRefusal` | typed refusal taxonomy (below) |
| `TransitionResult` | `ACCEPTED` (with one or more `TransitionEvent`s) or `REFUSED` (with exactly one `TransitionRefusal`, zero events) |
| `validate_transition()` | the one pure entry point |
| `IdempotencyRecord`, `IdempotencyOutcome`, `IdempotencyResolution`, `compute_command_content_hash()`, `resolve_idempotency()` | pure idempotency-key resolution over a caller-owned mapping |

## 3. Canonical serialization and content-hash rules

`content_hash` is computed by `compute_snapshot_content_hash()` from exactly:

- `terms_schema_version`, `intent_kind`
- `terms` — allocations canonically **sorted by `(symbol, side)`** so
  construction order never affects the hash
- `workspace_id`, `portfolio_id` (immutable scope)
- `effective_at`, `expires_at` (canonical UTC ISO-8601; naive datetimes raise)
- `source_provenance` — sorted by `(source_kind, source_local_id)`

Deliberately **excluded**: `snapshot_id`, `intent_id`, `revision`,
`supersedes_snapshot_id`, `created_by_actor`, `recorded_at`. These are
lineage/bookkeeping metadata, not "what a human reviewed." A resumed and
re-approved snapshot with unchanged terms therefore keeps the same content
hash across revisions — approval binding still uses the exact `snapshot_id`
in addition to the hash, so this does not weaken the approval-binding
invariant.

Serialization is `json.dumps(..., sort_keys=True, separators=(",", ":"))`
over a hand-built dict (not generic dataclass reflection), so only the listed
fields can ever affect the hash. `Decimal` values are rendered with
`format(value, "f")` and must be finite (`NaN`/`Infinity` raise `ValueError`).
Non-UTC-aware datetimes raise `ValueError` rather than being silently
assumed. Command idempotency uses a separate, similarly-canonical hash
(`compute_command_content_hash()`) over the command's own fields, including
`occurred_at` and reduced identity/hash-only projections of any
snapshot payloads it carries.

## 4. Transition validation behavior

`validate_transition(context, command, recorded_at=...)` implements the
M33.1 §8.8 table:

- **Terminal states** (`REJECTED`, `CANCELLED`, `EXPIRED`, `SUPERSEDED`,
  `COMPLETED`) accept nothing.
- **Prior-state/sequence check**: `command.expected_prior_state` and
  `command.expected_prior_transition_sequence` must match the context exactly,
  or the command is refused with no event appended (optimistic concurrency).
- **Actor authority**: `APPROVE`/`DEFER`/`RESUME`/`REJECT`/`CANCEL`/
  `RESOLVE_QUARANTINE` require a `HUMAN` actor; `EXPIRE`/`QUARANTINE`/
  `REQUEST_EXECUTION`/`RECORD_PARTIAL_EXECUTION`/`RECORD_COMPLETION` require a
  `SYSTEM` actor (policy- or ledger-derived only, never a human decision).
  `SUPERSEDE_WITH_REPLACEMENT` requires a `HUMAN` actor specifically when
  superseding an `APPROVED` snapshot; either actor may supersede
  `PENDING_REVIEW`/`DEFERRED`/`QUARANTINED`.
- **Approval hash binding**: `APPROVE` requires
  `approval_content_hash == snapshot.content_hash` exactly, and refuses if any
  `SourceProvenance` on the snapshot is `INCOMPLETE`.
- **Ledger-evidence gating**: `RECORD_PARTIAL_EXECUTION`/`RECORD_COMPLETION`
  require `AdmittedLedgerEvidence` with at least one entry; the computed
  `FulfillmentOutcome` must be exactly `PARTIAL` (for partial) or `COMPLETE`
  (for completion), and any entry referencing a symbol/side absent from the
  intent's terms refuses the whole command as `LEDGER_EVIDENCE_CONFLICT`.
  Fulfillment assessment is coverage-based (symbol/side presence), not
  quantity-based — M33 terms carry a target weight/value, not an admission
  quantity, so exact quantity reconciliation is explicitly out of scope here.
- **Supersession** (`SUPERSEDE_WITH_REPLACEMENT`) validates the replacement
  snapshot's `intent_id`, `supersedes_snapshot_id`, `revision` (must be
  exactly predecessor + 1), and immutable `workspace_id`/`portfolio_id` scope,
  then returns **one atomic `TransitionResult`** carrying two events
  (predecessor → `SUPERSEDED`, replacement `None` → `PENDING_REVIEW`) or,
  with `also_approve_replacement=True` and a matching
  `approval_content_hash`, three events (adding replacement `PENDING_REVIEW`
  → `APPROVED`). Any failure — including an atomic-approval hash mismatch —
  refuses the whole command with zero events; there is no partial-event
  output.
- **`SUBMIT`** requires an empty `SnapshotLifecycleContext`
  (`snapshot=None`, `current_state=None`) and a `submitted_snapshot` at
  revision 1 with no predecessor; it produces the single creation event
  `None → PENDING_REVIEW`.

## 5. Refusal taxonomy

`TransitionRefusalReason`: `INVALID_TRANSITION`, `TERMINAL_STATE`,
`PRIOR_STATE_MISMATCH`, `PRIOR_SEQUENCE_MISMATCH`, `ACTOR_NOT_AUTHORIZED`,
`SYSTEM_ACTOR_CANNOT_APPROVE`, `APPROVAL_HASH_REQUIRED`,
`APPROVAL_HASH_MISMATCH`, `INCOMPLETE_PROVENANCE_CANNOT_APPROVE`,
`POLICY_REFERENCE_REQUIRED`, `LEDGER_EVIDENCE_REQUIRED`,
`LEDGER_EVIDENCE_INSUFFICIENT`, `LEDGER_EVIDENCE_CONFLICT`,
`SUPERSESSION_REQUIRES_HUMAN_ACT`, `INVALID_REPLACEMENT_REVISION`,
`INVALID_REPLACEMENT_LINEAGE`, `SCOPE_IMMUTABLE`,
`MISSING_SUBMITTED_SNAPSHOT`, `MISSING_REPLACEMENT_SNAPSHOT`,
`UNEXPECTED_PAYLOAD`. Every refusal is data (a `TransitionRefusal(reason,
detail)`), never a raised generic exception, and always carries zero events.

## 6. Idempotency semantics

`resolve_idempotency(command, prior_records)` is a pure lookup over a
caller-owned `Mapping[str, IdempotencyRecord]`:

- unseen `idempotency_key` → `IdempotencyOutcome.NEW` (caller validates,
  stores the result, and inserts a record itself);
- same key + same `compute_command_content_hash()` → `REPLAYED`, returning the
  previously stored `TransitionResult` byte-for-byte without recomputation;
- same key + different content hash → `CONFLICT`, with `result=None`.

No storage, database, or locking is implemented here — a persistence
milestone owns the actual key-value store and its concurrency guarantees.

## 7. Test coverage

- `backend/tests/test_execution_intent_contracts_m33_2.py` (25 tests):
  immutability, terms validation, snapshot construction refusals (reserved
  source kind, revision/lineage rules, missing provenance, naive datetimes),
  and canonical hashing (determinism, insensitivity to identity/lineage/actor/
  recorded_at, sensitivity to terms/scope/effective/expiry/provenance/kind,
  allocation-order independence, non-finite Decimal rejection).
- `backend/tests/test_execution_intent_transitions_m33_2.py` (70 tests):
  every allowed transition (table-driven), a representative set of invalid
  transitions, all five terminal states, prior-state/sequence mismatches,
  approval hash binding (required/mismatch/exact/system-actor-refused/
  incomplete-provenance-refused), deferred/resume requiring fresh review,
  expiry/quarantine policy-reference and actor-authority gating, fulfillment
  assessment (no evidence/partial/complete/conflict), ledger-evidence gating
  for `RECORD_PARTIAL_EXECUTION`/`RECORD_COMPLETION` (including
  human-actor-refused and conflict-refused), supersession (two-event and
  atomic three-event forms, human-only-for-approved, lineage/revision/scope
  rejections, missing replacement), byte-equivalent output for identical
  inputs, and idempotency (new/replayed/conflict).

Both files pass in full: **95 passed** (25 + 70) on
`venv-test/Scripts/python.exe -m pytest`.

## 8. Explicit non-adoption statement

M33.2 does **not**:

- add an ORM model, Alembic migration, FastAPI endpoint, repository, or
  background writer;
- import or wire either new module into `main.py`, a router, a scheduler, or
  any existing service;
- dual-write from `UserExecutionDecision`, backfill legacy decisions/shadows,
  or change `RecommendationSnapshot`, `ShadowPortfolio`, `Transaction`,
  `Portfolio`, or replay behavior in any way;
- adopt M32 shadow legs, price evidence, fee quotes, or policy diagnostics as
  intent evidence (`SourceKind` has no such member);
- adopt a canonical execution plan (`FUTURE_CANONICAL_EXECUTION_PLAN` is
  refused at construction time);
- add broker, order, routing, placement, fill, cancellation, or
  reconciliation behavior;
- change M31/M32 adoption status or reopen M32.

Regression evidence: the previously-passing M33.1 current-state suite
(`test_horizon_grader.py`, `test_shadow_tracker_cash_accounting.py`,
`test_shadow_regeneration.py`, `test_execution_decision_linkage.py`,
`test_execution_ledger.py`) plus the directly-adjacent M32 pure-contract
suites (`test_execution_optimizer.py`, `test_execution_policy_m32_3e1.py`,
`test_execution_trade_leg_m32_2.py`, `test_execution_price_observation_m32_3c.py`)
all remain green: **112 passed** (pre-existing `datetime.utcnow()` deprecation
warnings only, unrelated to this change).

## 9. Recommended next milestone

**M33.3 — Legacy-Adapter Feasibility Study (still design/pure-contract only).**

Before any persistence milestone, a separate bounded piece of work should
take the M33.2 pure contracts and, without adding a table or writer,
enumerate concretely which existing `RecommendationSnapshot` +
`UserExecutionDecision` row shapes can honestly produce a complete
`ExecutionIntentSnapshot` (i.e. `APPROVED` decisions with fully structured
allocation terms) versus which must be classified `INCOMPLETE`/quarantined
(bare `MANUAL_OVERRIDE` labels, `PARTIAL_EXECUTION` without accepted terms,
duplicate/conflicting decisions on one snapshot). This produces the adapter
policy M33.1 explicitly deferred, still with no ORM/migration/endpoint, and
is the natural prerequisite for a later M33.4 persistence milestone that
would introduce tables, concurrency constraints, and a real idempotency
store.
