M38-WP8 — Experience Observation Runtime Implementation Design

1. Executive summary

WP8 implements the Experience Observation Runtime: the coordinator that
lets external consumers observe the published Experience Snapshot WP7
produces, without granting them any authority over it. WP8 owns
observation, subscription, notification, and delivery behavior only. It
creates no new domain facts and composes nothing.

The canonical relationship is:

```
Experience Composition Runtime (WP7)
  Published Experience Snapshot
  Read-only Experience Observation Interface (WP7 §4.9)
                │
                │ read-only consumption, one direction only
                ▼
      Experience Observation Runtime (WP8)
                │
                ▼
          Registered Observers
```

WP8 sits strictly downstream of WP7 and has no upstream effect on it: it
never mutates Experience state, never triggers composition, and never
feeds anything back into WP7's Coordinator. Every fact an observer
receives is a reference to what WP7 already published; WP8 adds only
subscription identity, delivery ordering, and duplicate/staleness
bookkeeping.

WP8 neither owns nor infers any upstream fact:

- WP2 owns Workspace Context and its lifecycle.
- WP3 owns the Asset Focus relationship and its transitions.
- WP4 owns Navigation and canonical route composition.
- WP5 owns Contribution descriptors, availability, and attachment.
- WP6 owns Projection Composition and `ProjectionEnvelope` availability.
- WP7 owns the Unified Experience Snapshot, its publication ordering, and
  its replacement/retirement lifecycle, including the
  `recomposition_pending` signal.
- WP8 owns only observer subscriptions, notification sequencing, and
  delivery guarantees over what WP7 already publishes.

2. Scope boundary

WP8 implements:

- the Experience Observation Coordinator;
- the Subscription Registry and subscription lifecycle;
- the Notification model and its sequencing rules;
- replacement notification delivery;
- retirement notification delivery;
- `recomposition_pending` signal-change delivery;
- concurrency and stale/duplicate notification suppression;
- fail-closed rules for delivery under unstable or absent upstream state.

WP8 does not implement:

- Experience composition, sequencing, settlement, or publication (WP7);
- Workspace Context, Asset Focus, Navigation, Contribution, or Projection
  Composition behavior (WP2–WP6);
- Registry, Search, Resolver, provider, Portfolio, Intelligence, Intent,
  or Action behavior;
- any mutation endpoint; WP8 exposes subscribe/unsubscribe and
  observation delivery only, never a write path into Experience state;
- any new Experience Snapshot field, business meaning, or reinterpretation
  of `composition_state` or `recomposition_pending`.

3. Runtime architecture

```
Frozen WP7 Experience Observation Interface (§4.9)
  - last published Experience Snapshot, if any
  - replacement notification
  - retirement notification
  - recomposition_pending signal
                │
                │ read-only, one direction
                ▼
      Experience Observation Coordinator
        ├── Subscription Registry
        ├── Notification Sequencer
        ├── Delivery Channel
        └── Duplicate and Subscription-State Notification Suppressor
                │
                ▼
          Registered Observers
```

WP8 attaches to WP7 only through WP7's frozen public Experience
Observation Interface. It performs no direct database, HTTP, Search,
Registry, Resolver, provider, Portfolio, or WP2–WP6 access of its own;
every notification WP8 delivers is derived from a fact WP7 already
published or signaled.

4. Runtime components

4.1 Subscription Registry

Holds the set of currently registered observers and their subscription
state (§5). It:

- assigns each subscription a stable, opaque `subscription_id` at
  registration time;
- records no observer-supplied business data beyond a delivery target;
- removes a subscription's entry immediately on unsubscribe, after which
  no further notification is delivered to it.

4.2 Experience Observation Coordinator

The single entry point through which WP8 consumes WP7's Experience
Observation Interface. It:

- reads the last published Experience Snapshot and the current
  `recomposition_pending` value from WP7, and nothing else;
- hands every WP7 replacement, retirement, and signal-change event to the
  Notification Sequencer;
- performs no interpretation, aggregation, or recomputation of any
  Experience Snapshot field.

4.3 Notification Sequencer

Establishes a strict, per-subscription delivery order for notifications
originating from WP7 events. It:

- assigns each outbound notification a WP8-owned, opaque, monotonically
  increasing `delivery_sequence` value, distinct from and never derived
  from any WP7-internal generation marker (WP7 §4.9 exposes no internal
  generation identifier, so WP8 mints its own delivery-ordering value
  for its own bookkeeping only);
- orders notifications for one subscription in the order WP7's events
  were observed by the Coordinator, never reordered, never batched out
  of order;
- does not reorder across subscriptions relative to one another; ordering
  is a per-subscription guarantee, not a global one.

4.4 Delivery Channel

Performs the actual hand-off of a notification to a registered observer.
It:

- delivers to `ACTIVE` subscriptions only (§5);
- treats delivery failure to one observer as isolated: it never blocks,
  delays, or drops delivery to any other observer;
- performs no retry logic that could reorder or duplicate a notification
  already accepted by the Sequencer; retry, if any, is the observer's own
  responsibility using the delivered `delivery_sequence` for
  deduplication.

4.5 Duplicate and Subscription-State Notification Suppressor

Shared logic consumed by the Sequencer and the Coordinator, scoped
strictly to WP8-local bookkeeping. It never determines whether a WP7
generation is stale or superseded — that is entirely WP7's concern (see
§10). It:

- suppresses an exact duplicate `PUBLISHED` observation for the same
  `experience_id`, and an exact duplicate `RETIRED` observation for the
  same retired `experience_id`, to at most one delivery per subscription;
- suppresses a repeated observation of an unchanged `recomposition_pending`
  boolean for the same `experience_id`, using transition-based tracking
  (§6, §10) rather than a permanent `(kind, experience_id)` key;
- discards any notification for a subscription that has already
  transitioned to `UNSUBSCRIBED`, and discards any queued delivery that a
  subscription's unsubscribe invalidates before hand-off.

This component never: infers WP7 generation ordering; determines whether
a generation has been superseded; repairs or second-guesses WP7 event
ordering; or suppresses a notification on the basis of an inferred
upstream generation validity. It acts only on facts WP8 itself already
observed for that subscription (an exact repeated `PUBLISHED`/`RETIRED`
identity, an unchanged pending boolean, or subscription lifecycle state).

5. Subscription lifecycle

| State | Meaning | Owner |
|---|---|---|
| `ACTIVE` | The subscription is registered and receiving notifications | Experience Platform (WP8) |
| `UNSUBSCRIBED` | The subscription has ended; no further notification is delivered | Experience Platform (WP8) |

| Transition | Canonical owner | Preconditions and effect |
|---|---|---|
| (none) → `ACTIVE` | Experience Platform (WP8) | Observer registers; the Coordinator immediately delivers one `PUBLISHED` notification for the last published Experience Snapshot and its current `recomposition_pending` value, if a snapshot currently exists; no notification is delivered if none exists yet |
| `ACTIVE` → `UNSUBSCRIBED` | Experience Platform (WP8) | Observer explicitly unsubscribes |

`UNSUBSCRIBED` is terminal for that subscription instance. Re-observing
requires a new subscription, which receives a new `subscription_id` and,
per its registration effect, a fresh initial delivery — it never inherits
notifications missed by a prior subscription instance. WP8 does not
retain or replay a notification history: it forwards only the current
state at registration time and events observed thereafter, matching
WP7's own "last published snapshot" contract (§4.9) rather than an
event log WP7 does not provide.

6. The Notification model

The Notification is the only new runtime contract WP8 introduces. Every
field it carries beyond delivery bookkeeping is a reference to what WP7
already published or signaled.

| Field | Presence | Meaning | Owner |
|---|---|---|---|
| `subscription_id` | Required | The subscription this notification is delivered to | Experience Platform (WP8) |
| `delivery_sequence` | Required | WP8-owned, opaque, monotonically increasing per-subscription ordering value | Experience Platform (WP8) |
| `kind` | Required | `PUBLISHED`, `RETIRED`, `PENDING_TRUE`, or `PENDING_FALSE` | Experience Platform (WP8) |
| `experience_id` | Required | Identifies the referenced Experience Snapshot instance (WP7 §5). For `PUBLISHED`, `PENDING_TRUE`, and `PENDING_FALSE`, the currently referenced instance. For `RETIRED`, the exact instance WP7 has retired, derived only from the previously WP7-published Snapshot reference WP8 already observed for that subscription | Experience Platform (WP7) |
| `snapshot` | Conditional | Present only for `PUBLISHED`; the referenced Unified Experience Snapshot (WP7 §5), passed through unchanged | Experience Platform (WP7) |

The Notification field named `snapshot` is a reference field, and that
reference field is owned by WP7 alone: the value is the exact immutable
Unified Experience Snapshot instance WP7 published, and WP8 does not own,
construct, modify, enrich, or reinterpret it. This is distinct from
ownership of the fields nested *inside* the referenced Snapshot, which
retain their own existing canonical owners exactly as declared by WP7 and
the upstream frozen WPs (WP7 §5; WP2–WP6) — WP8 asserts ownership only
over the Notification envelope field that carries the reference, never
over the Snapshot's internal fields.

**Invariants.** `delivery_sequence` is strictly increasing per
subscription and carries no business meaning; `kind` is exactly one of
the four values above; `experience_id` is present on every notification,
including `RETIRED`; `snapshot`, when present, is the same immutable
instance WP7 currently publishes — WP8 does not construct, rewrite, or
enrich it; a `PENDING_TRUE`/`PENDING_FALSE` notification never carries a
`snapshot` field of its own — it references the already-delivered
`experience_id` and changes no fact about that snapshot.

Pending notifications (`PENDING_TRUE`/`PENDING_FALSE`) are not
deduplicated by a permanent `(kind, experience_id)` key. WP8 tracks, per
active subscription and referenced `experience_id`, only the last
delivered pending boolean observation, and suppresses a repeat only when
the newly observed boolean equals that last delivered value (§10). A
`false → true → false → true` sequence of observations therefore produces
two distinct `PENDING_TRUE` deliveries, one for each genuine transition.

**Prohibited states.** A notification fabricating or defaulting a
`snapshot` field WP7 has not published; a `RETIRED` notification whose
`experience_id` is fabricated, inferred, defaulted, or synthesized rather
than derived from the previously WP7-published Snapshot reference WP8
already observed; a notification asserting a `RETIRED` snapshot as
current; a `PENDING_TRUE` notification reinterpreted by WP8 as a
snapshot mutation rather than a pass-through of WP7's
`recomposition_pending` signal (WP7 §4.9); a notification delivered out
of `delivery_sequence` order for the same subscription; a notification
delivered to an `UNSUBSCRIBED` subscription; a pending notification
permanently suppressed by `(kind, experience_id)` in a way that discards
a genuine later transition.

If a retirement event cannot be safely associated with the exact
previously published `experience_id` WP8 already observed for that
subscription, WP8 fails closed: it delivers no `RETIRED` notification
rather than fabricate one.

7. Notification sequencing and ordering

For one subscription, WP8 delivers notifications in the exact order it
observed the corresponding WP7 events:

1. On subscription, if a snapshot is currently published, deliver one
   `PUBLISHED` notification carrying it, and — if `recomposition_pending`
   is already true at that moment — follow immediately with one
   `PENDING_TRUE` notification for the same `experience_id`. This
   `PENDING_TRUE` is current-state qualification delivered at
   subscription time, not replay and not event-history backfill: it does
   not claim the subscriber observed the start of the recomposition
   attempt, only that WP7 currently reports the last published snapshot
   as pending confirmation. An observer must never receive the last
   published Snapshot without this qualification when WP7 currently
   reports `recomposition_pending = true`.
2. On a WP7 replacement (WP7 §8), when `recomposition_pending` becomes
   true for the currently published snapshot, deliver one `PENDING_TRUE`
   notification for that snapshot's `experience_id`.
3. When the replacement's successor snapshot is accepted by WP7's
   Publication Gate, deliver one `PUBLISHED` notification carrying the
   new snapshot. WP8 does not deliver a separate "old snapshot retired"
   notification for an ordinary replacement — per WP7 §8, replacement is
   a single atomic exchange, and WP8's `PUBLISHED` notification for the
   successor is the sole observable event, matching that atomicity rather
   than exposing an intermediate gap of its own. Acceptance of the
   successor also ends the pending observation state WP8 was tracking for
   the previous `experience_id` (§10).
4. On WP7 retirement with no successor (WP7 §9), deliver one `RETIRED`
   notification identifying exactly the `experience_id` of the Experience
   Snapshot WP7 has retired, derived only from the previously
   WP7-published Snapshot reference WP8 already observed for that
   subscription. If that identity cannot be safely determined, WP8 fails
   closed and delivers no `RETIRED` notification. Retirement also ends
   the pending observation state WP8 was tracking for that
   `experience_id` (§10).
5. If `recomposition_pending` reverts to false without a successor ever
   publishing (WP7 aborts a generation before it settles), deliver one
   `PENDING_FALSE` notification for the same `experience_id` that was
   previously marked pending, restoring it to unqualified "last
   published" status. A subsequent reversion back to true for the same
   `experience_id` produces a new, distinct `PENDING_TRUE` notification
   (§6, §10) — pending transitions are not permanently deduplicated.

WP8 never delivers a notification predicting a future state; every
notification describes a fact WP7 has already published or signaled at
the moment WP8 observed it.

8. Replacement notification handling

Replacement notifications (`PENDING_TRUE` followed eventually by
`PUBLISHED`) must preserve WP7's atomicity guarantee end to end:

- between the `PENDING_TRUE` notification and the eventual `PUBLISHED`
  notification, an observer may continue reading the last delivered
  snapshot, but WP8 never asserts through any notification that this
  snapshot is confirmed-current business state — the `PENDING_TRUE`
  notification exists precisely so the observer can apply the same
  "last published, pending confirmation" qualification WP7's Observation
  Interface itself requires (WP7 §4.9);
- WP8 never delivers a partial or intermediate snapshot; the `PUBLISHED`
  notification for a successor always carries a complete, settled
  snapshot exactly as WP7 published it;
- if WP7's replacement produces the same `experience_id` again (which
  WP7 never does — every generation is a new instance per WP7 §6 — but
  WP8 fails closed regardless), the Suppressor treats it as a duplicate
  and delivers nothing further;
- an observer that subscribes mid-replacement receives only the current
  state at subscription time (§5, §7 step 1): one `PUBLISHED` notification
  for the last published snapshot, immediately followed by one
  `PENDING_TRUE` notification for the same `experience_id` if
  `recomposition_pending` is already true at that moment. This initial
  `PENDING_TRUE` is current-state qualification, not replay — it does not
  assert that the observer witnessed the recomposition attempt begin, and
  it must never be omitted while WP7 currently reports
  `recomposition_pending = true` for the last published snapshot.

9. Retirement notification handling

Retirement notifications follow WP7 §9 exactly:

- a `RETIRED` notification is delivered only once WP7's Retirement
  Orchestrator has actually transitioned the snapshot to `RETIRED`; WP8
  never anticipates retirement from a `PENDING_TRUE` signal alone, since
  a pending replacement may resolve into a new `PUBLISHED` snapshot
  instead of a retirement;
- the `RETIRED` notification identifies exactly the Experience Snapshot
  WP7 has retired; WP8 derives this `experience_id` only from the
  previously WP7-published Snapshot reference it already observed for
  that subscription, and never fabricates, infers, defaults, or
  synthesizes a missing identity; if the retirement event cannot be
  safely associated with that exact previously observed `experience_id`,
  WP8 fails closed and delivers no `RETIRED` notification;
- retirement ends the pending observation state WP8 was tracking for that
  `experience_id` (§10); a `RETIRED` notification is deduplicated using
  `(RETIRED, experience_id)`;
- after `RETIRED`, no further notification is delivered to that
  subscription until a new snapshot publishes, at which point an ordinary
  `PUBLISHED` notification is delivered per §7 step 3;
- a subscription registered while no snapshot is currently published (for
  example, immediately after retirement and before a new Workspace
  Context resolves) receives no initial notification; its first
  notification is the eventual `PUBLISHED` event, if and when one occurs.

10. Concurrency and duplicate/subscription-state notification suppression

WP8 introduces its own `delivery_sequence` (§4.3, §6) solely to order
notifications for a single subscription. WP8 never determines whether a
WP7 generation is stale or superseded, never reconstructs WP7 generation
ordering, and never repairs or second-guesses WP7 event ordering —
generation validity remains entirely WP7's concern. WP8 delivers only the
public facts WP7 exposes, in the order WP8 observes them, subject solely
to its own local duplicate and subscription-lifecycle rules below.

Duplicate suppression is not uniform across notification kinds:

- `PUBLISHED` is deduplicated by its exact published `experience_id`: an
  identical `PUBLISHED` observation for the same `experience_id` produces
  at most one delivery per subscription;
- `RETIRED` is deduplicated by its exact retired `experience_id`, using
  the key `(RETIRED, experience_id)`: an identical `RETIRED` observation
  for the same `experience_id` produces at most one delivery per
  subscription;
- pending notifications (`PENDING_TRUE`/`PENDING_FALSE`) are **not**
  deduplicated by a permanent `(kind, experience_id)` key. For each active
  subscription and referenced `experience_id`, WP8 maintains only the
  last delivered pending boolean observation:
  - a repeated `true` observation while the last delivered value is
    already `true` is suppressed;
  - a repeated `false` observation while the last delivered value is
    already `false` is suppressed;
  - a transition from `false` to `true` produces a new `PENDING_TRUE`
    delivery;
  - a transition from `true` to `false` produces a new `PENDING_FALSE`
    delivery;
  - a `true → false → true` sequence produces two distinct `PENDING_TRUE`
    deliveries, one for each genuine transition;
  - publication of a successor (§7 step 3) or retirement (§7 step 4) ends
    the pending observation state associated with the previous
    `experience_id`; no further pending notification is delivered for
    that `experience_id` afterward.

Required behavior:

- a WP7 event is delivered as whatever WP7's interface currently reports;
  WP8 does not attempt to detect, repair, or second-guess a stale or
  superseded event on WP7's behalf; it only guarantees it will never
  deliver its own notifications for the same observed fact out of order
  or more than once, per the duplicate rules above;
- delivery failure or slowness for one subscription never delays or
  reorders delivery for any other subscription;
- unsubscribing mid-delivery is race-safe: any notification already
  handed to the Delivery Channel for that subscription before
  unsubscribe completes MAY still be attempted once, but no new
  notification is queued for it afterward.

11. Fail-closed rules

| Condition | Required behavior |
|---|---|
| No Experience Snapshot currently published at subscription time | No initial notification delivered; subscription remains `ACTIVE`, awaiting the first future `PUBLISHED` event |
| WP7 reports `recomposition_pending = true` | Deliver `PENDING_TRUE`; never represent the referenced snapshot as confirmed-current business state in the notification |
| WP7 replacement completes | Deliver exactly one `PUBLISHED` notification for the successor; never deliver a partial or intermediate snapshot |
| WP7 retirement with no successor | Deliver exactly one `RETIRED` notification identifying the exact retired `experience_id`, derived only from the previously observed published Snapshot reference; no further delivery until a new `PUBLISHED` event |
| Retirement event cannot be safely associated with the exact previously published `experience_id` | Fail closed: deliver no `RETIRED` notification; never fabricate, infer, default, or synthesize an identity |
| Duplicate `PUBLISHED` or `RETIRED` observation for the same `experience_id` | Suppressed to at most one delivery per subscription |
| Repeated `recomposition_pending` observation equal to the last delivered pending value for that `experience_id` | Suppressed; a genuine transition (`false → true` or `true → false`) always produces a new delivery, even if a prior transition for the same `experience_id` was already delivered |
| Notification for an `UNSUBSCRIBED` subscription | Discarded; never delivered |
| Delivery failure to one observer | Isolated; no other subscription's delivery is affected |
| WP7 Observation Interface reports no internal generation identifier | WP8 never fabricates or infers one; `delivery_sequence` remains WP8-local ordering metadata only; WP8 never infers WP7 generation staleness or supersession |

WP8 never fabricates a missing WP7 fact to produce a notification, and
never suppresses a genuine `RETIRED`, `PENDING_TRUE`, or `PENDING_FALSE`
transition to make a snapshot appear confirmed-current or to hide a
retirement.

12. Dependency boundaries

WP8 may depend on:

- the frozen WP7 public Experience Observation Interface (§4.9 of WP7)
  only;
- Experience-owned subscription and delivery-sequencing logic introduced
  by WP8 itself.

WP8 must never depend on:

- WP2–WP6 internals, directly or by reaching through WP7;
- Registry, Search, Resolver, or provider adapters;
- Portfolio persistence, Market Intelligence, Intelligence, Intent, or
  Action implementations;
- WP7's internal generation marker, Coordinator internals, or any state
  beyond its declared public Observation Interface;
- undeclared ambient state of any kind.

Every dependency must be declared and public, consistent with WP1 §6 and
conformance requirement `CO-02`.

13. Implementation sequence

1. Define the immutable Notification representation (§6) and its strict
   structural validator.
2. Define the Subscription lifecycle (§5) and its transition engine.
3. Implement the Subscription Registry, including opaque
   `subscription_id` assignment and terminal `UNSUBSCRIBED` handling.
4. Implement the Experience Observation Coordinator bound only to WP7's
   frozen public Experience Observation Interface.
5. Implement the Notification Sequencer, including the WP8-owned
   `delivery_sequence` and per-subscription ordering guarantee.
6. Implement the Duplicate and Subscription-State Notification
   Suppressor shared by the Coordinator and Sequencer, including
   transition-based pending tracking per subscription and referenced
   `experience_id`.
7. Implement the Delivery Channel with per-subscription failure
   isolation.
8. Implement initial-delivery behavior on subscription (§5, §7 step 1),
   including the pending-signal follow-up notification.
9. Implement replacement notification handling (§8) preserving WP7's
   atomicity guarantee.
10. Implement retirement notification handling (§9).
11. Add structural dependency, sequencing, concurrency, and end-to-end
    conformance gates; verify WP1–WP7 artifacts remain unchanged.

This order establishes pure subscription and notification-ordering
invariants before wiring live WP7 event consumption, preventing a
misordered, duplicated, or fabricated notification from ever reaching an
observer.

14. Conformance mapping

| WP1 requirement | WP8 realization |
|---|---|
| OW-01, OW-02 | Every Notification field maps to exactly one owner (WP8 or the referenced upstream runtime); no shared ownership |
| OW-03 | Notification delivery copies the WP7-published snapshot reference only; WP8 never rewrites a source fact |
| CO-02 | Dependency boundaries (§12) restrict WP8 to WP7's frozen public Observation Interface only |
| CO-03 | Delivery failure to one observer never blocks or delays another (§4.4, §10) |
| CO-04 | The Notification is a reference/event aggregate, not a computed authoritative fact |
| DG-01, DG-02, DG-03 | `PENDING_TRUE`/`PENDING_FALSE` preserve WP7's own qualification of "last published, pending confirmation" distinct from confirmed-current; WP8 never defaults or hides a `RETIRED` or pending state |
| RR-04, RT-04 | WP8 performs no Registry, Search, Resolver, or provider calls of its own |
| CT-02 | Field-owner assertions across the full Notification model (§6) |
| CT-05 | The `snapshot` reference field is owned by WP7 alone (§6); it preserves provenance, temporal, quality, and degradation context unchanged, since it is WP7's own instance, while fields nested inside it retain their existing canonical owners |
| CT-07 | Structural and runtime dependency evidence restricted to WP7's public Observation Interface |

WP8-owned conformance requirements (new, scoped to this document):

- **OB-01:** An observer receives only Experience Snapshots WP7 has
  actually published; no fabricated, partial, or predicted snapshot is
  ever delivered.
- **OB-02:** An unpublished generation is never observable through any
  notification.
- **OB-03:** A `PUBLISHED` notification for a successor is delivered only
  after WP7's atomic exchange (WP7 §8) completes; no notification exposes
  an intermediate or missing state.
- **OB-04:** A `RETIRED` notification is delivered only after WP7's
  Retirement Orchestrator (WP7 §9) has actually retired the snapshot, and
  identifies exactly the retired `experience_id`, derived only from the
  previously observed published Snapshot reference; if that identity
  cannot be safely determined, no `RETIRED` notification is delivered.
- **OB-05:** Notification ordering is deterministic per subscription;
  `delivery_sequence` is strictly increasing and never reused.
- **OB-06:** Duplicate `PUBLISHED` observations for the same
  `experience_id`, and duplicate `RETIRED` observations for the same
  `experience_id`, are each suppressed to at most one delivery per
  subscription.
- **OB-07:** An `UNSUBSCRIBED` subscription can never mutate runtime
  state and never receives a further notification.
- **OB-08:** A `PENDING_TRUE` notification never represents its
  referenced snapshot as confirmed-current business state; a
  `PENDING_FALSE` notification restores unqualified "last published"
  status only when WP7 itself reports the pending replacement resolved
  without a new publication. A subscriber joining while a snapshot is
  published and `recomposition_pending` is already true always receives
  this qualification via an initial `PENDING_TRUE` following the initial
  `PUBLISHED`; this is current-state qualification, not replay.
- **OB-09:** WP8 never infers, reconstructs, or second-guesses WP7
  generation ordering or staleness; suppression decisions are based only
  on WP8's own observed duplicate and subscription-lifecycle facts (§10).
- **OB-10:** Pending notifications are suppressed only by transition:
  repeated observation of an unchanged pending boolean for the same
  `experience_id` is suppressed, but every genuine `false → true` or
  `true → false` transition produces a new delivery, even following a
  prior transition already delivered for the same `experience_id`.

15. Mandatory acceptance tests

Contract and ownership

- The Notification contains exactly the fields in §6; no additional
  fields.
- Every field resolves to exactly one owner, including `experience_id`
  (required on every `kind`, including `RETIRED`) and `snapshot` (owned
  by WP7 alone; nested Snapshot fields retain their own upstream owners).
- No notification field is computed as a new authoritative business
  fact.

Subscription lifecycle

- Every subscription transition in §5 succeeds; every unlisted transition
  fails closed.
- `UNSUBSCRIBED` is terminal for its subscription instance.
- Re-subscribing after `UNSUBSCRIBED` creates a new subscription with a
  new `subscription_id` and no inherited notification history.

Observation behavior

- An observer subscribed before any snapshot exists receives no initial
  notification and later receives the first `PUBLISHED` event once one
  occurs (`OB-01`, `OB-02`).
- An observer subscribed while a snapshot is currently published receives
  exactly one initial `PUBLISHED` notification, immediately followed by a
  `PENDING_TRUE` notification if `recomposition_pending` is already true
  (§7 step 1); this `PENDING_TRUE` is delivered as current-state
  qualification, never omitted, and never treated as replay or
  event-history backfill (`OB-08`).
- A replacement produces exactly one `PENDING_TRUE` notification followed
  later by exactly one `PUBLISHED` notification for the successor; no
  intermediate or partial snapshot is ever observed (`OB-03`).
- A retirement with no successor produces exactly one `RETIRED`
  notification identifying the exact retired `experience_id`, and no
  further delivery until the next `PUBLISHED` event (`OB-04`).
- A retirement event that cannot be safely associated with the exact
  previously observed published `experience_id` produces no `RETIRED`
  notification (`OB-04`).
- A `recomposition_pending` reversion without a successor publishing
  produces exactly one `PENDING_FALSE` notification for the previously
  pending `experience_id` (`OB-08`).
- No notification ever represents a snapshot whose generation is being
  superseded as confirmed-current business state (`OB-08`).
- WP8 never suppresses a notification on the basis of an inferred WP7
  generation staleness or supersession determination (`OB-09`).

Sequencing and ordering

- `delivery_sequence` values are strictly increasing per subscription and
  never repeat (`OB-05`).
- Notifications for one subscription are delivered in the exact order the
  corresponding WP7 events were observed.
- Ordering guarantees are per-subscription; no cross-subscription
  ordering claim is made or required.

Transition-based pending suppression (`OB-10`)

- `PENDING_TRUE` followed by a repeated `PENDING_TRUE` observation for the
  same `experience_id` delivers only the first; the repeat is suppressed.
- `PENDING_TRUE` followed by `PENDING_FALSE` for the same `experience_id`
  delivers both.
- `PENDING_TRUE` → `PENDING_FALSE` → `PENDING_TRUE` for the same
  `experience_id` delivers all three as distinct notifications.
- Publication of a successor snapshot resets pending tracking for the
  previous `experience_id`: no further pending notification is delivered
  for it afterward.
- Retirement resets pending tracking for the retired `experience_id`: no
  further pending notification is delivered for it afterward.

Concurrency

- Duplicate `PUBLISHED` observations for the same `experience_id`, and
  duplicate `RETIRED` observations for the same `experience_id`, each
  produce at most one delivered notification per subscription (`OB-06`).
- Delivery failure to one subscription does not delay, reorder, or drop
  delivery to any other subscription.
- A notification queued for a subscription that unsubscribes before
  delivery is discarded, not delivered (`OB-07`).

Dependency enforcement

- Static checks reject any WP8 import of WP2–WP6 internals, Registry,
  Search, Resolver, provider, Portfolio persistence, Intelligence,
  Intent, or Action internals.
- Runtime spies prove WP8 calls only WP7's frozen public Experience
  Observation Interface.
- No new public mutation HTTP endpoint is introduced by WP8.
- WP1–WP7 artifacts remain unchanged.

16. Completion criteria

WP8 is complete only when:

- The Notification model exactly matches §6, with every field owned by
  exactly one runtime, `experience_id` required on every `kind`
  including `RETIRED`, and the `snapshot` reference field owned by WP7
  alone.
- The subscription lifecycle in §5 is fully enforced, with all other
  transitions failing closed.
- Observers never receive an unpublished, partial, fabricated, or
  predicted snapshot.
- Replacement and retirement notifications are delivered exactly as
  specified in §8 and §9, preserving WP7's atomic no-gap guarantee; a
  `RETIRED` notification always identifies the exact retired
  `experience_id`, derived only from a previously observed published
  Snapshot reference, and is never delivered when that identity cannot
  be safely determined.
- A subscriber joining while a snapshot is published and
  `recomposition_pending` is already true always receives an initial
  `PUBLISHED` immediately followed by an initial `PENDING_TRUE`, as
  current-state qualification rather than replay.
- No notification ever asserts a snapshot undergoing replacement as
  confirmed-current business state; the `PENDING_TRUE`/`PENDING_FALSE`
  pass-through of WP7's `recomposition_pending` signal is the only
  mechanism used to qualify that claim.
- WP8 never infers, reconstructs, or second-guesses WP7 generation
  ordering or staleness; all suppression is based only on WP8's own
  observed duplicate and subscription-lifecycle facts.
- Pending notification suppression is transition-based, per subscription
  and referenced `experience_id`, never a permanent
  `(kind, experience_id)` key; `PUBLISHED` and `RETIRED` duplicate
  suppression each key on their own exact `experience_id`.
- Notification ordering and duplicate suppression hold per subscription
  under concurrent WP7 events.
- Structural and runtime evidence proves WP8 depends only on WP7's frozen
  public Experience Observation Interface.
- All conformance mappings in §14 and acceptance tests in §15 pass.
- No frozen WP1–WP7 or M35–M37 artifact requires modification.

WP8 implementation design status: COMPLETE — READY FOR IMPLEMENTATION.
No repository files outside this document were modified.
