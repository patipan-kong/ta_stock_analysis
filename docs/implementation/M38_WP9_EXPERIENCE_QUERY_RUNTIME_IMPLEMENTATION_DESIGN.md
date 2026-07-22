M38-WP9 — Experience Query Runtime Implementation Design

1. Executive summary

WP9 implements the Experience Query Runtime: a read-only query facade
that lets callers ask deterministic, synchronous questions about the
currently observable Experience state, without granting them — or WP9
itself — any authority over that state. WP9 introduces no new business
fact, no new ownership, and no new business lifecycle. It answers
queries only from what WP8 has already delivered.

WP8 exposes no synchronous "read the current snapshot" call; its frozen
public interface (WP8 §5, §6) is subscription- and notification-based
only: `PUBLISHED`, `RETIRED`, `PENDING_TRUE`, and `PENDING_FALSE`
notifications delivered to a registered subscription. WP9 therefore
consumes that interface the only way it is exposed: WP9 itself is a
single WP8 subscriber, one subscription for the lifetime of one WP9
runtime instance (§5). It maintains a **Mechanical Observation
Projection** — a precisely defined record (§4.1) that maps explicit
WP8-delivered facts into a query-readable form — and answers queries by
reading that record, never by calling anything on WP7, and never by
opening a second, parallel channel into Experience state.

The canonical relationship is:

```
Experience Observation Runtime (WP8)
  Subscribe / Unsubscribe (WP8 §5)
  Notification stream: PUBLISHED / RETIRED / PENDING_TRUE / PENDING_FALSE (WP8 §6)
                │
                │ exactly one WP8 subscription per WP9 runtime instance
                ▼
      Experience Query Runtime (WP9)
        Observed State Holder (Mechanical Observation Projection, §4.1)
                │
                ▼
          Query Coordinator → Query Callers
```

WP9 sits strictly downstream of WP8 and has no upstream effect on it: it
never unsubscribes-and-resubscribes to influence delivery, never issues
a mutation, and never feeds anything back into WP8's Coordinator or
WP7's Composition Runtime. Every fact a query result carries is a
reference to what WP8 already delivered; WP9 adds only query
validation, filtering, projection, and result construction over that
held record.

WP9 neither owns nor infers any upstream fact:

- WP2 owns Workspace Context and its lifecycle.
- WP3 owns the Asset Focus relationship and its transitions.
- WP4 owns Navigation and canonical route composition.
- WP5 owns Contribution descriptors, availability, and attachment.
- WP6 owns Projection Composition and `ProjectionEnvelope` availability.
- WP7 owns the Unified Experience Snapshot, its identity (`experience_id`),
  its publication ordering, and its replacement/retirement lifecycle,
  including the `recomposition_pending` signal.
- WP8 owns observer subscriptions, notification sequencing, and delivery
  guarantees over what WP7 publishes.
- WP9 owns only query validation, query execution, filtering,
  projection-container construction, and result construction over what
  WP8 already delivered. WP9 owns none of the values carried inside a
  result — those retain their upstream owners (§6, §14 Finding 5).

2. Scope boundary

WP9 implements:

- the Experience Query Coordinator;
- the Observed State Holder (a Mechanical Observation Projection backed
  by exactly one WP8 subscription per WP9 runtime instance, §4.1, §5);
- query request validation;
- query execution;
- query filtering (§8, canonical grammar);
- query projection (§4.5b, field selection only);
- query result construction, including the `NO_MATCH` outcome (§6);
- fail-closed query behavior, including operational-unavailable
  behavior while the Holder is not `READY` (§5, §11);
- query consistency guarantees, including exactly-one-Holder-capture
  execution (§7, §10).

WP9 does not implement:

- Experience composition, sequencing, settlement, or publication (WP7);
- observer subscription lifecycle, notification sequencing, or delivery
  guarantees as a service offered to others (WP8) — WP9 consumes exactly
  one WP8 subscription for its own internal use and exposes no
  subscription capability of its own;
- Workspace Context, Asset Focus, Navigation, Contribution, or Projection
  Composition behavior (WP2–WP6);
- Registry, Search, Resolver, provider, Portfolio persistence,
  Intelligence, Intent, Action, recommendation, analytics, or reporting
  behavior;
- any mutation endpoint; WP9 exposes query execution only, never a write
  path into Experience state;
- any new Experience Snapshot field, business meaning, or reinterpretation
  of `composition_state` or `recomposition_pending`;
- caching or reconstruction of business state independent of what WP8
  has delivered;
- persistence, replay, reconnect, retry, durable delivery, event logs,
  timers, health-check orchestration, or background reconciliation of
  any kind (§5).

3. Runtime architecture

```
Frozen WP8 public interface (WP8 §5 Subscription lifecycle, §6 Notification model)
  - subscribe / unsubscribe
  - initial-state delivery completion signal
  - PUBLISHED  (experience_id, snapshot)
  - RETIRED    (experience_id)
  - PENDING_TRUE / PENDING_FALSE (experience_id)
                │
                │ exactly one WP8 subscription for this WP9 runtime instance
                ▼
          Observed State Holder
          (Mechanical Observation Projection: availability +
           observation_status + experience_id + snapshot +
           recomposition_pending + subscription_id — §4.1)
                │
                ▼
      Experience Query Coordinator
        ├── Query Validator            (reads the Holder zero times)
        ├── one Holder capture         (exactly once per query, §7, §10)
        ├── Filtering Model            (reads only the captured value)
        ├── Projection                 (reads only the captured value)
        └── Result Constructor         (reads only the captured value)
                │
                ▼
          Query Callers
```

WP9 attaches to WP8 only through WP8's frozen public Subscription and
Notification interface (WP8 §5, §6). It performs no direct database,
HTTP, Search, Registry, Resolver, provider, Portfolio, or WP2–WP7 access
of its own; every query result WP9 constructs is derived from the one
Holder record populated by facts WP8 already delivered to WP9's own
subscription.

4. Runtime components

4.1 Observed State Holder — Mechanical Observation Projection

The only stateful component WP9 introduces. "Mechanical Observation
Projection" means: WP9 maps explicit WP8-delivered facts into a
query-readable record; it does not reconstruct Experience state, and it
does not invent a transition absent from WP8's contract. It is the
target of exactly one WP8 subscription for the lifetime of exactly one
WP9 runtime instance (§5).

Normative record:

```
ObservedStateHolder {
  availability:
    NOT_READY | READY | FAILED

  observation_status:
    NO_DATA | PUBLISHED | RETIRED

  experience_id:
    exact WP7-owned identifier delivered through WP8, or absent

  snapshot:
    exact WP7-published immutable Snapshot reference delivered through WP8,
    or absent

  recomposition_pending:
    boolean, applicable only when observation_status = PUBLISHED

  subscription_id:
    WP8 subscription identity for this WP9 runtime instance
}
```

An equivalent representation is acceptable if the semantics above are
exact. `availability` and `observation_status` are separate concepts:
`availability` describes whether WP9's own subscription is fit to serve
queries (§5); `observation_status` describes what WP8 has told WP9 about
Experience state. A `NOT_READY` or `FAILED` availability is never
reported to a caller as `NO_DATA` (§5, §11).

Event-update table. Every Holder change is caused by exactly one of the
following; no other cause is permitted. `INITIAL_DELIVERY_COMPLETE` is
the only event that transitions `availability` from `NOT_READY` to
`READY`; every other event applies only after that transition has
already occurred.

| # | Event | Holder effect |
|---|---|---|
| 1 | `INITIAL_DELIVERY_COMPLETE(NO_DATA)` — WP8 confirms completion of initial delivery with no Snapshot published | `availability → READY`; `observation_status = NO_DATA`; `experience_id`, `snapshot` absent; `recomposition_pending = false` |
| 2 | `INITIAL_DELIVERY_COMPLETE(PUBLISHED { experience_id, snapshot, recomposition_pending })` — WP8 confirms completion of initial delivery with a Snapshot and its complete initial pending qualification | `availability → READY`; `observation_status = PUBLISHED`; `experience_id`, `snapshot` set atomically to the delivered values; `recomposition_pending` set atomically to the complete initial qualification delivered by WP8 for that `experience_id` — the Snapshot and its pending qualification become query-visible as one completed Holder state, never as two separate steps |
| 3 | `PUBLISHED(experience_id, snapshot)` (post-initial-delivery) | `observation_status = PUBLISHED`; `experience_id`, `snapshot` replaced atomically with the delivered values; `recomposition_pending` reset to `false` until a `PENDING_TRUE` is delivered for this `experience_id` |
| 4 | `PENDING_TRUE(experience_id)` (post-initial-delivery) | if `experience_id` matches the currently held one, `recomposition_pending = true`; no other field changes |
| 5 | `PENDING_FALSE(experience_id)` (post-initial-delivery) | if `experience_id` matches the currently held one, `recomposition_pending = false`; no other field changes |
| 6 | `RETIRED(experience_id)` (post-initial-delivery) | `observation_status = RETIRED`; `experience_id` retained exactly as delivered (the retired identifier remains in the record); `snapshot` cleared to absent; `recomposition_pending` no longer applicable |
| 7 | Subscription registration failure | `availability = FAILED`; `observation_status`, `experience_id`, `snapshot`, `recomposition_pending` no longer authoritative and not served (§5, §11) |
| 8 | Subscription inactivity or delivery-integrity loss | `availability = FAILED`; same effect as row 7 |
| 9 | Orderly runtime shutdown | `availability = NOT_READY` (or the Holder is disposed); no further queries served |

Rows 3–6 (individual `PUBLISHED`/`PENDING_TRUE`/`PENDING_FALSE`/`RETIRED`
notifications) apply only after `INITIAL_DELIVERY_COMPLETE` (row 1 or 2)
has already installed the Holder's initial state. Before that point, WP9
MAY mechanically buffer the initial `PUBLISHED` and any initial
`PENDING_TRUE`/`PENDING_FALSE` notifications WP8 delivers as part of its
buffered initial state, solely so that row 2 can install them atomically
when WP8 signals completion. That buffer:

- is temporary startup assembly only, internal to the transition into
  row 1 or row 2 — it is not a second Holder;
- is not replay, and is not persistence;
- is never query-visible: no query may observe an intermediate
  initial-delivery tuple, an initial `PUBLISHED` without its required
  initial pending qualification, or `availability = READY` before the
  complete initial state (row 1 or row 2) has been applied;
- is discarded once the initial state is committed (row 1 or row 2), or
  discarded on startup failure (row 7 or row 8) without ever being
  installed.

The Holder MUST NOT introduce: autonomous transitions; timers; inferred
upstream state; recomposition generation tracking; replay state;
reconnect state; retry state; or any independently owned business
lifecycle state. Every field's value, when present, is copied unchanged
from what WP8 delivered; the Holder performs no interpretation,
aggregation, recomputation, or persistence of any field.

4.2 Experience Query Coordinator

The single entry point for query execution. It:

- validates the request (§4.3) without observing the Holder;
- on a valid request, captures the complete Holder record — including
  `availability` — exactly once (§7, §10); this one capture is the sole
  Holder observation for the query, whether the outcome is `UNAVAILABLE`
  or any other status; it passes only that immutable captured value to
  filtering, projection, and result construction, never a Holder handle,
  callback, provider, or registry capable of re-observation;
- performs no WP7 or WP8 call of its own beyond the one subscription
  owned by the Observed State Holder, and performs that zero times
  during query execution (the subscription is established once, outside
  query execution, at WP9 startup, §5);
- issues no mutation, no subscription registration on behalf of a
  caller, and no notification delivery — those remain exclusively WP8's
  responsibility.

4.3 Query Validator

Validates a query request against the Query Contract (§6) before any
Holder read:

- rejects a request with an unrecognized filter field, unsupported
  filter operator, or unrecognized projection field, per the canonical
  filter grammar (§8);
- rejects a request that asks for a field not present anywhere in the
  Unified Experience Snapshot and not one of the explicitly declared
  observation-metadata fields (`experience_id`, `recomposition_pending`,
  `observation_status`, §8); `QueryResult.status` is never a valid
  filter field (§8);
- never fabricates a default for a missing or malformed request field;
  an invalid request fails closed with no query executed and no Holder
  read (§7).

4.4 Filtering Model

Applies caller-specified filters (§8) to the one captured Holder value,
only when that captured value's `availability = READY` and
`observation_status = PUBLISHED` (§8 evaluation semantics):

- reads only fields already present on the captured Unified Experience
  Snapshot reference, or the captured `experience_id`,
  `recomposition_pending`, `observation_status` metadata fields;
- never reads or evaluates against `QueryResult.status`, which does not
  exist until result construction;
- never derives, infers, or computes a new field not already published
  by WP7 or signaled by WP8;
- is a pure function of (captured Holder value, validated request); it
  reads the Holder zero additional times and has no side effect on the
  Observed State Holder.

4.5 Result Constructor

Builds the Query Result (§6) from the one captured Holder value and the
filter outcome:

- when the captured value's `observation_status = PUBLISHED` and the
  filter matches, returns `status = OK` with the full Snapshot reference
  or its requested projection (§4.5b), plus `recomposition_pending`;
- when the captured value's `observation_status = PUBLISHED` and the
  filter does not match, returns `status = NO_MATCH` (§6);
- when the captured value's `observation_status = NO_DATA`, returns
  `status = NO_DATA` with no `experience_id` and no `snapshot`;
- when the captured value's `observation_status = RETIRED`, returns
  `status = RETIRED` identifying the retained retired `experience_id`,
  with no `snapshot` — retired state is never returned as if it were
  current;
- when the captured value's `availability` is `NOT_READY` or `FAILED`,
  returns the operational-unavailable outcome (§5, §11) — never
  `NO_DATA`, never a previously held snapshot;
- never fabricates, defaults, or synthesizes a field the captured value
  does not actually carry.

4.5b Projection

Two distinct result forms exist for a matched, `PUBLISHED` query:

1. **Full Snapshot result** — returns the exact immutable WP7 Snapshot
   reference delivered through WP8, unchanged; WP9 does not copy or
   reconstruct it.
2. **Projected result** — returns a WP9-owned projection container
   (§6) holding only the requested fields; every selected value is
   copied unchanged from the one captured Snapshot reference; selected
   fields retain their canonical upstream owners.

Projection is field selection only. Projection MUST NOT perform:
renaming; transformation; derivation; aggregation; normalization;
formatting; defaulting; recomputation; meaning-changing flattening; or
synthesis of a missing value. An empty projection (`projection: []`)
returns a projection container with no selected fields, never the full
Snapshot and never a fabricated field. A projection field absent from
the Unified Experience Snapshot is rejected by the Query Validator
(§4.3) before execution.

5. Query lifecycle and subscription lifecycle

WP9 queries are stateless per call. A query request carries no
subscription identity and creates no persistent server-side state; the
only persistent state in WP9 is the single Observed State Holder shared
across all queries (§4.1).

**Permanent subscription, defined.** "Permanent" means: exactly one WP8
subscription for the lifetime of exactly one WP9 runtime instance. It
does not mean indefinite reconnection or cross-instance continuity.

**Startup rules.**

1. On startup, WP9 creates exactly one WP8 subscription.
2. While registration and WP8's complete initial-state delivery are in
   progress, the Holder's `availability = NOT_READY`; WP9 serves no
   state query from the Holder during this window; any initial
   notifications WP8 delivers during this window are mechanically
   buffered only, per §4.1, and are not query-visible.
3. The Holder becomes `availability = READY` only through the single
   `INITIAL_DELIVERY_COMPLETE` event (§4.1, event #1 or #2) — never
   through any other event, and never through the arrival of an
   individual `PUBLISHED`/`PENDING_TRUE`/`PENDING_FALSE` notification
   before that event.
4. No query may read or return an intermediate initial state: when the
   initial state is `PUBLISHED`, the Snapshot and its required initial
   pending qualification are installed by the same `INITIAL_DELIVERY_
   COMPLETE(PUBLISHED{...})` event and become query-visible together,
   atomically, at the point WP9 declares readiness — never `PUBLISHED`
   alone with `recomposition_pending` unqualified, and never as two
   separate visible steps.
5. Query execution rejects with the operational-unavailable outcome
   (§11) while `availability != READY`.

**Failure rules.** If registration fails, the subscription becomes
inactive unexpectedly, delivery ordering or integrity can no longer be
trusted, or initial delivery cannot complete safely, then:

- `availability = FAILED`;
- WP9 stops answering state queries from the Holder;
- queries fail closed with the explicit operational-unavailable outcome
  (§11), never `NO_DATA`;
- WP9 MUST NOT return previously held state as current;
- WP9 MUST NOT reconnect;
- WP9 MUST NOT replay;
- WP9 MUST NOT create a replacement subscription within the same
  runtime instance;
- WP9 MUST NOT infer a missed notification's content.

**Shutdown rules.** Orderly shutdown terminates query serving before or
while disposing of the one subscription (event #9, §4.1); no query is
served once the Holder is no longer `READY`.

**Runtime restart rule.** A restart creates a new WP9 runtime instance,
which creates exactly one new WP8 subscription. This is a new
subscription, not a reconnection or continuation of the old one; no
state from the previous Holder carries forward.

No availability infrastructure beyond these fail-closed contract
semantics is introduced — no timers, no health-check orchestration, no
background reconciliation.

| Step | Behavior |
|---|---|
| Request received | Query Validator checks the request against the Query Contract (§6); invalid requests fail closed with no Holder read |
| Request valid | Query Coordinator captures the complete Holder record exactly once, including `availability` (§7, §10) — this single capture is the only Holder observation for the query, whether it ends in `UNAVAILABLE` or otherwise |
| Captured `availability != READY` | Result Constructor returns `UNAVAILABLE`; no further field of the captured record is consulted |
| Captured `availability = READY`, `observation_status = PUBLISHED`, filter matches | Result Constructor returns `OK` with snapshot (or projection) and `recomposition_pending` |
| Captured `availability = READY`, `observation_status = PUBLISHED`, filter does not match | Result Constructor returns `NO_MATCH` |
| Captured `availability = READY`, `observation_status = NO_DATA` | Result Constructor returns `NO_DATA` |
| Captured `availability = READY`, `observation_status = RETIRED` | Result Constructor returns `RETIRED` with the retained retired `experience_id` |
| Result returned | The call ends; WP9 retains no per-caller state after the response |

There is no query-side subscription lifecycle to manage: a caller issues
a query and receives a result; it never registers, and is never
unsubscribed, since it never subscribed to anything. Any need for
push-style delivery on change remains WP8's exclusive responsibility
(WP8 §2), not WP9's.

6. Query contract

**Query Request**

| Field | Presence | Meaning | Owner |
|---|---|---|---|
| `filters` | Optional | Zero or more conjunctive equality predicates over the canonical filter field set (§8: Snapshot fields, plus `experience_id`, `recomposition_pending`, and `observation_status` as observation metadata) | Query caller |
| `projection` | Optional | Zero or more field names, drawn only from the held Unified Experience Snapshot's fields, to include in a projected result (§4.5b); absent means the full Snapshot reference | Query caller |

**Query Result**

| Field | Presence | Meaning | Owner |
|---|---|---|---|
| `status` | Required | One of `OK`, `NO_DATA`, `RETIRED`, `NO_MATCH`, `UNAVAILABLE` (§5, §11) | WP9 |
| `experience_id` | Conditional | Present for `OK`, `RETIRED`, and `NO_MATCH`; absent for `NO_DATA` and `UNAVAILABLE`; identifies the referenced Experience Snapshot instance | WP7 (identity is WP7-owned; transported unchanged through WP8; WP9 references and returns it without mutation) |
| `snapshot` (full form) | Conditional | Present only for `status = OK` with no `projection` requested; the held Unified Experience Snapshot reference, passed through unchanged | WP7 (delivered via WP8; WP9 performs no copy or reconstruction) |
| `projection` (`QueryProjection`, projected form) | Conditional | Present only for `status = OK` with a `projection` requested; `QueryProjection { selected_fields: map<canonical_field_name, unchanged_selected_value> }` | Container: WP9. Each selected field/value: unchanged canonical upstream owner (WP2–WP7, per each field's own declared owner) |
| `recomposition_pending` | Conditional | Present only for `status = OK`; the current pending qualification, mirroring WP8's last delivered `PENDING_TRUE`/`PENDING_FALSE` | WP7 (delivered via WP8) |

**`NO_MATCH`, defined.** `NO_MATCH` is a WP9-owned query outcome: a
valid query was evaluated against currently observable Experience state
and the filter predicate did not match. It is distinct from `NO_DATA`
(no Snapshot has ever been observed), from `RETIRED` (the observed
Snapshot was retired), and from `UNAVAILABLE` (WP9's own subscription is
not fit to serve). `NO_MATCH` is not an upstream business-state
assertion. A `NO_MATCH` result carries the `experience_id` of the
Snapshot the filter was evaluated against (so the caller can distinguish
"this Snapshot exists but doesn't match" from "no Snapshot exists") and
no `snapshot` or `projection` field.

**`UNAVAILABLE`, defined.** `UNAVAILABLE` reports that the Holder's
`availability` is `NOT_READY` or `FAILED` (§5). It carries no
`experience_id`, `snapshot`, `projection`, or `recomposition_pending`.
It is never conflated with `NO_DATA`: `NO_DATA` means WP9's subscription
is `READY` and WP8 has confirmed no Snapshot has ever published;
`UNAVAILABLE` means WP9 cannot currently answer at all.

**Invariants.** `status` is exactly one of the five values above;
`snapshot` is present only when `status = OK` and no projection was
requested; `projection` is present only when `status = OK` and a
projection was requested; `snapshot` and `projection` are never both
present; `experience_id` is present if and only if `status` is `OK`,
`RETIRED`, or `NO_MATCH`; a projection never introduces a field absent
from the held Unified Experience Snapshot; `recomposition_pending`, when
present, is never omitted while WP8's last delivered pending state for
that `experience_id` is true.

**Prohibited states.** A `status = OK` result with neither `snapshot`
nor `projection`; a `status = NO_DATA`, `RETIRED`, `NO_MATCH`, or
`UNAVAILABLE` result carrying a `snapshot` or `projection`; a `RETIRED`
result with a fabricated, inferred, defaulted, or synthesized
`experience_id`; a projection field not present in the held Unified
Experience Snapshot; a query result that omits `recomposition_pending =
true` when WP8's most recently delivered pending state for the held
`experience_id` is true; an `UNAVAILABLE` result reported as `NO_DATA`
or vice versa; a projected field that is renamed, transformed, derived,
or defaulted.

7. Execution model

Query execution is synchronous, deterministic, and read-only, and
proceeds in exactly this order:

1. Validate the request against the Query Contract (§6) and the
   canonical filter grammar (§8) — this step reads the Holder zero
   times, and issues zero WP8 or WP7 calls.
2. Atomically capture the complete immutable Holder record exactly
   once, including `availability`, `observation_status`, `experience_id`,
   `snapshot`, and `recomposition_pending`. This is the one and only
   Holder observation performed for this query, regardless of outcome —
   there is no separate, earlier availability check.
3. Derive all subsequent behavior exclusively from that one captured
   record:
   a. if the captured `availability != READY`, return `UNAVAILABLE`;
      no further field of the captured record is consulted, no filter
      is evaluated, and no second Holder read occurs;
   b. if the captured `availability = READY`, derive `NO_DATA`,
      `RETIRED`, `NO_MATCH`, or `OK` solely from the same captured
      record and the validated request (§8, §9).
4. Pass only that immutable captured value — never a Holder handle,
   callback, provider, or registry — through filter evaluation,
   projection, and result construction. No component re-reads the
   Holder, and no component issues a WP8 or WP7 call.
5. Return the constructed, immutable result.

The same query request against the same captured Holder value always
produces the same result; no randomness, wall-clock dependence, or
external call is introduced. Query inputs (the request) and query
outputs (the result) are immutable once constructed. Executing a query
has no side effect on the Observed State Holder, on WP8, or on WP7 — it
never registers a subscription, never unsubscribes, and never triggers
composition or publication.

8. Filtering model — canonical grammar

The canonical filter field set is exactly the union of the following two
categories. No other implicit or section-specific filter field exists
anywhere in this document.

| Category | Field | Owner / source | Available when |
|---|---|---|---|
| Snapshot fields | any canonical field name present in the captured Unified Experience Snapshot | WP7 (delivered via WP8) | only when captured `observation_status = PUBLISHED` |
| Observation metadata | `experience_id` | WP7-owned identifier, delivered through WP8, captured in the Holder | when captured (present for `PUBLISHED` and `RETIRED`) |
| Observation metadata | `recomposition_pending` | WP7-owned operational qualification, delivered through WP8, captured in the Holder | only when captured `observation_status = PUBLISHED` |
| Observation metadata | `observation_status` | WP9-owned mechanical Holder classification: `NO_DATA \| PUBLISHED \| RETIRED` | always, once `availability = READY` |

`QueryResult.status` (§6: `OK`, `NO_MATCH`, `NO_DATA`, `RETIRED`,
`UNAVAILABLE`) is **not** a filterable field and MUST NOT appear in the
canonical filter field set: it is the final outcome of query execution,
produced only after filtering completes, so a filter could never be
evaluated against it without circularity. Filtering the Holder's
`observation_status` (a distinct, WP9-owned, pre-filtering
classification) is permitted; filtering `QueryResult.status` is not.

Grammar:

- filters combine only by conjunction;
- only the equality predicate is supported;
- every allowed field (per the table above) and the equality operator
  are the only enumerated grammar elements; no other operator is
  defined;
- a filter referencing an unknown field (including `status` as a
  standalone field name, or any name not in the table above), or using
  an unsupported operator, is rejected by the Query Validator (§4.3)
  before any Holder read — never silently ignored;
- multiple predicates on the same field are evaluated conjunctively
  (all must be true for a match); they are not rejected as duplicates.

Evaluation semantics, applied to the one Holder value captured at the
start of execution (§7):

- if the captured `availability != READY`, filtering is not executed;
  the query returns `UNAVAILABLE` (§7, §9);
- if the captured `observation_status = NO_DATA`, filtering is not
  executed; the query returns `NO_DATA` directly, since no observable
  Experience instance exists to filter (§7, §9);
- if the captured `observation_status = RETIRED`, filtering is not
  executed; the query returns `RETIRED` directly, preserving the
  retained retired `experience_id`; retirement is never turned into
  `NO_MATCH` (§7, §9);
- if the captured `observation_status = PUBLISHED`, every valid
  predicate is evaluated against the Snapshot fields and observation
  metadata (`experience_id`, `recomposition_pending`,
  `observation_status`) within that one captured value; any false
  predicate produces `NO_MATCH`; if all predicates are true (or no
  filter was given), execution proceeds to `OK` result construction.

`NO_MATCH` therefore applies only when: captured `availability = READY`;
captured `observation_status = PUBLISHED`; and a valid predicate
evaluates false. This is the only path to `NO_MATCH` — it is never
produced from a `NO_DATA` or `RETIRED` captured value, and never from an
`UNAVAILABLE` capture.

A filter is evaluated against exactly the Snapshot reference and
metadata within the one Holder value captured at the start of execution
(§7); it is never evaluated against a value a concurrent WP8
notification later replaces.

9. Result construction

Result construction is a pure mapping from (validated request, one
captured Holder value, filter outcome) to a Query Result (§6):

- for `status = UNAVAILABLE`, derived solely from the captured
  `availability` field of the one captured Holder value (§7 step 3a);
  no other field of that captured value is consulted, and no filter is
  evaluated;
- for `status = OK`, the `snapshot` field (full form) or `projection`
  field (projected form, §4.5b) is derived only from the captured
  Snapshot reference, never rebuilt or enriched by WP9;
  `recomposition_pending` is the exact boolean the captured value holds;
- for `status = NO_MATCH`, the captured `experience_id` is returned with
  no `snapshot` or `projection`;
- for `status = NO_DATA`, the captured value's `observation_status =
  NO_DATA`; the result carries no `experience_id`, `snapshot`, or
  `projection`;
- for `status = RETIRED`, the captured value's `observation_status =
  RETIRED`; the result carries the retained retired `experience_id`
  exactly and no `snapshot` or `projection` — retired state is never
  returned as if it were current.

The `UNAVAILABLE` case above carries none of `experience_id`,
`snapshot`, `projection`, or `recomposition_pending`.

10. Concurrency behavior

A query executes against a single, consistent point-in-time capture of
the Observed State Holder, taken exactly once (§7):

- the Query Coordinator captures one immutable read of the Holder's
  complete record — including `availability` — after validation and
  before any availability check, filtering, projection, or result
  construction (§7); a concurrent WP8 notification arriving during
  execution updates the Holder for future queries but never mutates the
  value already captured by an in-flight query;
- validation (§4.3) performs zero Holder reads; the availability check,
  filtering, projection, and result construction each receive only the
  one captured value and perform zero additional Holder reads;
- two queries executed concurrently may legitimately observe different
  captured values if a WP8 notification is delivered to the Holder
  between their respective captures; each individual query result is
  still internally consistent (§7);
- the Observed State Holder itself applies WP8 notifications in the
  exact order WP8's own per-subscription delivery guarantees them (WP8
  §7, §10), per the event-update table (§4.1): a `PUBLISHED` replaces
  the held reference atomically, a `RETIRED` clears the snapshot
  atomically while retaining the retired `experience_id`, and a pending
  notification updates only the pending boolean for the currently held
  `experience_id`;
- WP9 introduces no query-side subscription, so no query ever produces
  a duplicate or out-of-order delivery of its own; ordering guarantees
  for the underlying notification stream remain entirely WP8's
  responsibility (WP8 §4.3, §10).

11. Fail-closed rules

| Condition | Required behavior |
|---|---|
| Captured `availability = NOT_READY` or `FAILED` (read from the one atomic Holder capture, §7) | Return `UNAVAILABLE`; never `NO_DATA`; never a previously held snapshot as current; no second Holder read is performed to reach this outcome |
| Captured `observation_status = NO_DATA` (Holder `READY`, no Snapshot ever delivered) | Return `NO_DATA`; never fabricate a snapshot |
| Captured `observation_status = RETIRED` | Return `RETIRED` with the exact retained retired `experience_id`; never return the previously held snapshot as current |
| Captured `observation_status = PUBLISHED`, filter does not match | Return `NO_MATCH` with the captured `experience_id`; never conflate with `NO_DATA` or `RETIRED` |
| Captured pending state is `true` | Include `recomposition_pending = true` in an `OK` result; never omit it, never treat the snapshot as unqualified current |
| Query request references a field absent from the canonical filter/projection field set (§8) | Reject the request before execution and before any Holder capture; never silently ignore the unknown field or substitute a default |
| Query request is otherwise malformed | Fail closed with no query executed and no Holder capture; never execute a best-effort partial query |
| Concurrent WP8 notification arrives mid-execution | The in-flight query completes against its already-captured value (§10); it is never partially updated |
| WP8 subscription registration fails, becomes inactive, or loses delivery integrity | `availability = FAILED`; fail closed with `UNAVAILABLE`; never reconnect, replay, or infer the missed content (§5) |
| Query issued while initial WP8 delivery is buffered but not yet committed via `INITIAL_DELIVERY_COMPLETE` (§4.1) | `availability` remains `NOT_READY`; return `UNAVAILABLE`; never expose the buffered initial `PUBLISHED` without its paired pending qualification |
| Query request filters on `QueryResult.status` (as opposed to the Holder's `observation_status`) | Reject before execution and before any Holder capture; `QueryResult.status` is not a filterable field (§8) |

WP9 never fabricates a missing WP8-delivered fact to answer a query, and
never represents retired, unmatched, unavailable, or pending Experience
state as unqualified current state.

12. Dependency boundaries

WP9 may depend on:

- WP8's frozen public Subscription lifecycle and Notification model
  (WP8 §5, §6) only, consumed through exactly one WP8 subscription per
  WP9 runtime instance (§5);
- WP9-owned query validation, filtering, projection, and
  result-construction logic introduced by WP9 itself.

WP9 must never depend on:

- WP2–WP7 internals, directly or by reaching through WP8;
- WP7's Experience Observation Interface (WP7 §4.9) directly — WP9
  consumes Experience state exclusively through WP8, never in parallel
  with it;
- Registry, Search, Resolver, or provider adapters;
- Portfolio persistence, Market Intelligence, Intelligence, Intent,
  Action, recommendation, analytics, or reporting implementations;
- WP8's internal Notification Sequencer, Subscription Registry, or
  Suppressor internals beyond WP8's declared public Subscription and
  Notification interface;
- undeclared ambient state of any kind;
- any second, independent channel into Experience state that could
  diverge from what WP9's single WP8 subscription has delivered;
- persistence, replay, reconnect, retry, durable delivery, event logs,
  timers, or background reconciliation (§5).

Every dependency must be declared and public, consistent with WP1 §6 and
conformance requirement `CO-02`.

13. Implementation sequence

1. Define the immutable Query Request and Query Result representations
   (§6), including the `NO_MATCH`/`UNAVAILABLE` outcomes and the
   `QueryProjection` container, and their strict structural validators.
2. Implement the Observed State Holder as the Mechanical Observation
   Projection (§4.1) backed by exactly one WP8 subscription per WP9
   runtime instance, including the full event-update table and the
   startup/failure/shutdown/restart rules (§5).
3. Implement the Query Validator against the canonical filter grammar
   (§8), rejecting unrecognized fields or operators before any Holder
   read (§4.3).
4. Implement the Filtering Model as a pure function over one captured
   Holder value (§4.4, §8), including the `NO_MATCH` outcome.
5. Implement projection as field selection only (§4.5b), producing the
   `QueryProjection` container without renaming, transforming, or
   deriving values.
6. Implement the Result Constructor, including the `OK`/`NO_DATA`/
   `RETIRED`/`NO_MATCH`/`UNAVAILABLE` status mapping (§4.5, §9).
7. Implement the Experience Query Coordinator binding the above into the
   single synchronous execution order of §7: validate (zero Holder
   reads) → availability check → exactly one Holder capture → filter →
   project → construct result.
8. Implement the single-read concurrency guarantee so an in-flight query
   is never mutated by a concurrent Holder update (§10).
9. Implement fail-closed handling for unavailable, no-data, retired,
   unmatched, pending, and malformed-request conditions (§11).
10. Add structural dependency, execution-determinism, concurrency, and
    exactly-one-Holder-capture conformance gates (using runtime spies or
    equivalent evidence, §15); verify WP1–WP8 artifacts remain unchanged.

This order establishes the Observed State Holder and its precisely
defined transition behavior before any query-serving logic is wired,
preventing a fabricated, stale, partially initialized, or independently
reconstructed result from ever reaching a caller.

14. Conformance mapping

| WP1 requirement | WP9 realization |
|---|---|
| OW-01, OW-02 | Every Query Result field maps to exactly one owner (WP9, WP7, or transported-and-unmutated WP7 identity, §6); no shared ownership. `experience_id` is owned by WP7 and merely transported through WP8 and referenced by WP9 (Finding 5) |
| OW-03 | Query results copy the WP8-delivered snapshot reference or selected field values only; WP9 never rewrites a source fact |
| CO-02 | Dependency boundaries (§12) restrict WP9 to WP8's frozen public Subscription and Notification interface only |
| CO-03 | Query execution is isolated per call; one query's execution never blocks or affects another |
| CO-04 | The Query Result is a reference/projection aggregate, not a computed authoritative fact |
| DG-01, DG-02, DG-03 | `recomposition_pending`, `RETIRED`, and `NO_MATCH`/`UNAVAILABLE` statuses preserve WP7/WP8's own qualification of state and WP9's own operational state; WP9 never defaults or hides a retired, pending, unmatched, or unavailable condition |
| RR-04, RT-04 | WP9 performs no Registry, Search, Resolver, or provider calls of its own |
| CT-02 | Field-owner assertions across the full Query Contract (§6), including the `QueryProjection` container-vs-value ownership split |
| CT-05 | The `snapshot` reference or each projected field value preserves provenance, temporal, quality, and degradation context unchanged, since it is WP7's own instance or field value delivered via WP8 |
| CT-07 | Structural and runtime dependency evidence restricted to WP8's public Subscription and Notification interface |

WP9-owned conformance requirements (new, scoped to this document):

- **QR-01:** A query never returns Experience state that WP8 has not
  actually delivered to WP9's subscription; no fabricated, partial, or
  predicted snapshot is ever returned.
- **QR-02:** An unpublished Experience generation is never queryable;
  only the state of the most recently delivered `PUBLISHED` notification
  can produce `status = OK` or `status = NO_MATCH`.
- **QR-03:** Once the Observed State Holder has processed a `RETIRED`
  notification for the held `experience_id`, every subsequent query
  returns `status = RETIRED` with that exact `experience_id`, never the
  previously held snapshot as current, until a new `PUBLISHED`
  notification arrives.
- **QR-04:** Query execution is deterministic: the same request against
  the same captured Holder value always produces the same result.
- **QR-05:** Query inputs and outputs are immutable once constructed.
- **QR-06:** A query never has a side effect on the Observed State
  Holder, on WP8, or on WP7.
- **QR-07:** An `OK` result never omits `recomposition_pending = true`
  when WP8's last delivered pending state for that `experience_id` is
  true.
- **QR-08:** A malformed query request, or a request referencing a
  field absent from the canonical filter/projection field set (§8), is
  rejected before any Holder capture; no best-effort partial query is
  ever executed.
- **QR-09:** A query whose one atomic Holder capture (§7) shows
  `availability` as `NOT_READY` or `FAILED` returns `UNAVAILABLE`; it is
  never reported as `NO_DATA`, and no previously held state is returned
  as current; `READY` is reached only through the single
  `INITIAL_DELIVERY_COMPLETE` event (§4.1), and an initial `PUBLISHED`
  is never query-visible without its paired initial pending
  qualification.
- **QR-10:** A valid query evaluated against a currently observed,
  non-matching Snapshot returns `NO_MATCH`, distinct from `NO_DATA`,
  `RETIRED`, and `UNAVAILABLE`; `NO_MATCH` arises only when the one
  captured Holder value has `availability = READY` and
  `observation_status = PUBLISHED` (§8); `QueryResult.status` is never
  itself a filterable field.
- **QR-11:** A projected result contains exactly the requested fields,
  each copied unchanged from the one captured Snapshot reference, with
  no renaming, transformation, derivation, aggregation, or defaulting.
- **QR-12:** Each query execution captures the Observed State Holder
  exactly once — including `availability` — as a single atomic
  operation; there is no separate, earlier availability check; this
  holds whether the query's outcome is `UNAVAILABLE` or any other
  status. Validation performs zero Holder reads; the availability
  determination, filtering, projection, and result construction each
  operate only on that one captured value and perform zero additional
  Holder reads.

15. Mandatory acceptance tests

Contract and ownership

- The Query Request and Query Result each contain exactly the fields in
  §6; no additional fields.
- Every field resolves to exactly one owner; `experience_id` resolves to
  WP7 as owner and WP8 as transport, never to WP8 as owner.
- No result field is computed as a new authoritative business fact.
- `QueryProjection`'s container is WP9-owned; each selected field/value
  retains its own upstream owner.

Holder representation and transitions (Finding 1)

- Each of the nine events in the §4.1 event-update table produces
  exactly the specified Holder effect and no other field change.
- `INITIAL_DELIVERY_COMPLETE(NO_DATA)` (event #1) transitions
  `availability → READY` with `observation_status = NO_DATA` and no
  `experience_id`/`snapshot`.
- `INITIAL_DELIVERY_COMPLETE(PUBLISHED{...})` (event #2) transitions
  `availability → READY` with `observation_status = PUBLISHED`,
  `experience_id`, `snapshot`, and `recomposition_pending` all installed
  atomically as one completed Holder state.
- `availability` transitions from `NOT_READY` to `READY` only through
  event #1 or event #2; no other event, and no individual
  `PUBLISHED`/`PENDING_TRUE`/`PENDING_FALSE` notification prior to that
  event, ever sets `availability = READY`.
- `availability` and `observation_status` vary independently; a `FAILED`
  or `NOT_READY` availability never implies `observation_status =
  NO_DATA` in a served result.
- A `RETIRED` event retains the exact retired `experience_id` in the
  Holder record and clears `snapshot`.
- No autonomous transition, timer-driven change, replay, reconnect, or
  retry state is observable in the Holder.
- Any startup buffering of initial notifications prior to
  `INITIAL_DELIVERY_COMPLETE` is never query-visible and is not a second
  Holder, replay, or persistence mechanism.

Subscription lifecycle (Finding 2)

- A query issued before initial WP8 delivery completes (including while
  an initial `PUBLISHED` has been buffered but not yet committed)
  returns `UNAVAILABLE`, never `NO_DATA` and never a partial snapshot.
- Initial delivery completing with no Snapshot published
  (`INITIAL_DELIVERY_COMPLETE(NO_DATA)`) yields `availability = READY`,
  `observation_status = NO_DATA`, and subsequent queries return
  `NO_DATA`.
- Initial delivery completing with a Snapshot and `recomposition_pending
  = false` yields `availability = READY`, `observation_status =
  PUBLISHED`, and subsequent queries return `OK` with
  `recomposition_pending = false`.
- Initial delivery completing with a Snapshot and a required initial
  `PENDING_TRUE` qualification yields both the Snapshot and
  `recomposition_pending = true` visible together, atomically, at the
  point WP9 declares `READY`; no query observes `PUBLISHED` without its
  pending qualification, and no query observes `READY` before both are
  installed.
- Subscription registration failure sets `availability = FAILED` and all
  subsequent queries return `UNAVAILABLE` until process restart.
- Subscription inactivity or delivery-integrity loss sets `availability
  = FAILED` with the same effect; WP9 does not reconnect, replay, or
  infer missed content.
- Orderly shutdown stops serving queries before or during subscription
  disposal; no query is served once the Holder leaves `READY`.
- A new WP9 runtime instance after restart creates exactly one new WP8
  subscription and carries forward no state from the previous instance's
  Holder.

Query lifecycle

- A query issued before any Experience Snapshot has ever published
  (Holder `READY`, `observation_status = NO_DATA`) returns `NO_DATA`
  with no `experience_id` and no `snapshot` (`QR-02`).
- A query issued while a snapshot is held and the filter matches (or no
  filter is given) returns `status = OK` with the held `experience_id`
  and snapshot (or requested projection) (`QR-01`).
- A query issued while a snapshot is held and the filter does not match
  returns `status = NO_MATCH` with the held `experience_id` and no
  snapshot or projection (`QR-10`).
- A query issued after a `RETIRED` notification for the held
  `experience_id` returns `status = RETIRED` with that exact
  `experience_id` and no `snapshot`, and continues to do so for every
  subsequent query until a new `PUBLISHED` notification arrives (`QR-03`).

Pending qualification

- A query issued while WP8's last delivered pending state for the held
  `experience_id` is true returns `status = OK` with
  `recomposition_pending = true`; the result never represents the
  snapshot as unqualified current (`QR-07`).
- A query issued after a `PENDING_FALSE` notification for the held
  `experience_id` returns `recomposition_pending = false`.

Execution determinism and immutability

- Two executions of the same request against the same captured Holder
  value produce identical results (`QR-04`).
- A Query Request and Query Result, once constructed, are never mutated
  by subsequent execution or delivery (`QR-05`).
- Executing a query produces no observable change in the Observed State
  Holder, and issues no call to WP8 or WP7 during execution (`QR-06`).

Filtering, non-match, and projection (Findings 3 and 4)

- The canonical filter field table (§8) explicitly lists Snapshot
  fields, `experience_id`, `recomposition_pending`, and
  `observation_status`; no other field is accepted.
- A filter naming `status` as a standalone metadata field (as opposed to
  the Holder's `observation_status`) is rejected before execution.
- A filter referencing `QueryResult.status` is rejected before
  execution; `QueryResult.status` is never a filterable field.
- A filter referencing a field in the canonical filter field set (§8)
  is applied correctly against the captured Snapshot or metadata.
- A valid `experience_id` filter matches and does not match correctly
  against the captured value.
- A valid `recomposition_pending` filter matches and does not match
  correctly against the captured value.
- A valid `observation_status = PUBLISHED` filter matches when the
  captured value's `observation_status = PUBLISHED`.
- A filter or projection referencing a field outside the canonical
  field set is rejected before execution, with no Holder capture
  (`QR-08`).
- An unsupported filter operator is rejected before execution.
- A captured `observation_status = NO_DATA` value returns `NO_DATA`
  directly without evaluating any filter predicate.
- A captured `observation_status = RETIRED` value returns `RETIRED`
  directly without evaluating any filter predicate, and is never turned
  into `NO_MATCH`.
- A `NO_MATCH` result is never conflated with `NO_DATA`.
- A `NO_MATCH` result is never conflated with `RETIRED`.
- Full-Snapshot mode returns the exact Snapshot reference unchanged.
- Projected mode returns only the requested fields, each with an
  unchanged value (`QR-11`).
- No field rename, transformation, or derived value appears in a
  projected result.
- An empty projection (`projection: []`) returns a `QueryProjection`
  with no selected fields, never the full Snapshot.
- An unknown projection field is rejected before execution.

Concurrency and exactly-one-capture (Finding 6)

- A query in flight when a concurrent `PUBLISHED`, `RETIRED`,
  `PENDING_TRUE`, or `PENDING_FALSE` notification updates the Observed
  State Holder completes against its already-captured value, never a
  partially updated one.
- Two concurrent queries may observe different captured values only if
  a WP8 notification was delivered between their respective captures;
  each individual result remains internally consistent.
- Runtime-spy evidence proves: every query attempt that passes validation
  — including one that ends in `UNAVAILABLE` — performs exactly one
  complete Holder capture, and no separate, earlier availability check
  exists; validation reads the Holder zero times; the availability
  determination reads only the captured record; filtering receives only
  the captured value; projection receives only the captured value;
  result construction receives only the captured value; no component
  re-reads the Holder; query execution performs zero WP8 calls and zero
  direct WP7 calls during execution; no component receives a Holder
  handle, callback, provider, or registry capable of re-observation
  (`QR-12`).

Dependency enforcement

- Static checks reject any WP9 import of WP2–WP7 internals (including
  WP7's Experience Observation Interface directly), WP8 internals beyond
  its declared public Subscription and Notification interface, Registry,
  Search, Resolver, provider, Portfolio persistence, Intelligence,
  Intent, Action, recommendation, analytics, or reporting internals.
- Runtime spies prove WP9 calls only WP8's frozen public Subscription
  and Notification interface, through exactly one subscription per WP9
  runtime instance.
- No new public mutation HTTP endpoint is introduced by WP9.
- No persistence, replay, reconnect, retry, timer, or reconciliation
  mechanism is present anywhere in the implementation.
- WP1–WP8 artifacts remain unchanged.

16. Completion criteria

WP9 is complete only when:

- The Query Contract exactly matches §6, with every field owned by
  exactly one runtime, and `experience_id` correctly attributed to WP7
  as owner with WP8 as transport only.
- The Observed State Holder implements the Mechanical Observation
  Projection exactly as defined in §4.1, with no independent caching or
  reconstruction of Experience state and no autonomous, timer-driven,
  replay, reconnect, or retry behavior.
- The subscription lifecycle in §5 — startup, initial-delivery
  atomicity, failure, shutdown, and restart — is fully implemented and
  fail-closed, with `READY` reached only through the single
  `INITIAL_DELIVERY_COMPLETE` event (§4.1) covering both the `NO_DATA`
  and `PUBLISHED` initial-state cases.
- The canonical filter field set (§8) is unambiguous: Snapshot fields,
  `experience_id`, `recomposition_pending`, and `observation_status` are
  the only filterable fields, and `QueryResult.status` is never
  filterable.
- Queries never return an unpublished, partial, fabricated, or predicted
  snapshot.
- A query against retired Experience state always returns `RETIRED`
  identifying the exact retained retired `experience_id`, never the
  previously held snapshot as current.
- A query against pending Experience state always surfaces
  `recomposition_pending = true`, never asserting the snapshot as
  unqualified current.
- A query against a non-matching but currently observed Snapshot always
  returns `NO_MATCH`, distinct from `NO_DATA`, `RETIRED`, and
  `UNAVAILABLE`.
- A query while the Holder is not `READY` always returns `UNAVAILABLE`,
  never `NO_DATA` and never previously held state.
- Projection is provably field-selection-only, with no rename,
  transform, derivation, or defaulting, and with container ownership
  (WP9) kept distinct from selected-field ownership (unchanged upstream
  owners).
- Query execution is deterministic, side-effect-free, and immutable on
  both input and output, and captures the Observed State Holder exactly
  once per query — including `availability`, with no separate, earlier
  availability check — proven by runtime-spy evidence (§7, §10, `QR-12`).
- Concurrency guarantees in §10 hold under concurrent WP8 notification
  delivery.
- Structural and runtime evidence proves WP9 depends only on WP8's
  frozen public Subscription and Notification interface, through exactly
  one subscription per runtime instance, with no reconnect, replay,
  persistence, retry, timer, or reconciliation authority.
- All conformance mappings in §14 and acceptance tests in §15 pass.
- No frozen WP1–WP8 or M35–M37 artifact requires modification.

WP9 implementation design status: COMPLETE — READY FOR INDEPENDENT
CORRECTIVE VERIFICATION.
No repository files outside this document were modified.
