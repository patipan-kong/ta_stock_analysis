M38-WP7 — Experience Composition Runtime Implementation Design

1. Executive summary

WP7 implements the Experience Composition Runtime: the coordinator that
assembles the frozen outputs of WP2–WP6 into one consistent, publishable
Experience view after Projection Composition has settled. WP7 owns
orchestration and publication only. It creates no new domain facts.

The canonical composition chain is:

```
Workspace Context (WP2)
        ↓
Asset Focus (WP3)
        ↓
Navigation (WP4)
        ↓
Contribution (WP5)
        ↓
Projection Composition (WP6)
        ↓
Experience Composition (WP7)
        ↓
Published Experience Snapshot
```

Each upstream link is a frozen, public-only dependency. WP7 reads the
current state each link publishes; it does not re-derive, reinterpret, or
mutate it. The only new artifact WP7 introduces is the Experience
Snapshot — an Experience-owned, read-only aggregate of references to the
upstream state, plus WP7's own composition-lifecycle metadata
(`composition_state`, sequencing, and settlement bookkeeping).

WP7 neither owns nor infers any upstream fact:

- WP2 owns Workspace Context and its lifecycle.
- WP3 owns the Asset Focus relationship and its transitions.
- WP4 owns Navigation and canonical route composition.
- WP5 owns Contribution descriptors, availability, and attachment.
- WP6 owns Projection Composition and `ProjectionEnvelope` availability.
- WP7 owns only the assembled Experience Snapshot, its publication
  ordering, and its replacement/retirement lifecycle.

2. Scope boundary

WP7 implements:

- the Experience Composition Coordinator;
- the Unified Experience Snapshot representation;
- composition sequencing across WP2–WP6;
- settlement detection (the point at which a snapshot may publish);
- publication, replacement, and retirement orchestration;
- runtime observation interfaces for Experience consumers;
- concurrency and stale-result suppression across the whole chain;
- fail-closed rules for partial or unsettled upstream state.

WP7 does not implement:

- Workspace Context resolution, bootstrap, or Current Selection (WP2);
- Asset Focus requests, Registry reads, or focus transitions (WP3);
- canonical navigation composition or route validation (WP4);
- Contribution descriptor validation or attachment (WP5);
- Projection Envelope fetch, degradation, or availability evaluation (WP6);
- Registry, Search, Resolver, provider, Portfolio, Intelligence, Intent, or
  Action behavior;
- any new HTTP mutation endpoint; WP7 exposes read/observe interfaces only.

3. Runtime architecture

```
Frozen WP2 Workspace Context
Frozen WP3 Asset Focus
Frozen WP4 Navigation
Frozen WP5 Contribution
Frozen WP6 Projection Composition
                │
                │ current published state of each (read-only)
                ▼
      Experience Composition Coordinator
        ├── Upstream Observation Adapters (one per WP2–WP6)
        ├── Composition Sequencer
        ├── Settlement Detector
        ├── Experience Snapshot Builder
        ├── Publication Gate
        ├── Replacement Orchestrator
        ├── Retirement Orchestrator
        └── Stale-Result Suppressor
                │
                ▼
      Published Experience Snapshot
                │
                ▼
      Read-only Experience Observation Interface
```

WP7 attaches to each upstream runtime only through its frozen public
observation interface. It performs no direct database, HTTP, Search,
Registry, Resolver, provider, or Portfolio access of its own; every fact
in a published Experience Snapshot is a reference to state already
published by WP2–WP6.

4. Runtime components

4.1 Upstream Observation Adapters

One adapter per frozen runtime (WP2–WP6). Each adapter:

- subscribes to its runtime's public observation interface only;
- normalizes "current state" and "state replaced/retired" notifications
  into a single internal shape the Sequencer consumes;
- performs no interpretation of the underlying domain facts;
- performs no writes back into the upstream runtime.

An adapter must not:

- reach past its runtime's public interface into internals;
- read a second runtime through the first (for example, reading Asset
  Focus through the Contribution adapter);
- fabricate a state when its runtime has not published one.

4.2 Composition Sequencer

The Sequencer enforces the canonical composition chain's read order:
Workspace Context, then Asset Focus, then Navigation, then Contribution,
then Projection Composition. It:

- requires a `RESOLVED` Workspace Context before consuming any
  downstream state, matching WP2's composition gate;
- reads each subsequent link only after the prior link has produced a
  stable (non-transitional) result for the current interaction;
- does not block a settled downstream link on an unrelated, independently
  degrading upstream optional field (for example, a `DEGRADED` projection
  does not hold back Navigation).

The Sequencer enforces read order only. It confers no transition
ownership: reading a fact never grants WP7 authority over that fact,
per WP1 §5 ("supplying an input does not confer transition ownership").

4.3 Settlement Detector

Projection Composition (WP6) resolves each attached `ProjectionEnvelope`
into one of the WP1 §5.5 availability states
(`AVAILABLE`/`DEGRADED`/`UNAVAILABLE`/`UNSUPPORTED`/`DETACHED`) or leaves
it `REQUESTED`. The Settlement Detector determines when the current
interaction's projection set has stopped changing for the purpose of one
publication:

- a projection set is **settled** when every currently attached envelope
  has left `REQUESTED` (reached `AVAILABLE`, `DEGRADED`, `UNAVAILABLE`,
  `UNSUPPORTED`, or `DETACHED`);
- settlement is evaluated per Experience Snapshot generation (§9), not
  globally; a later attachment restarts settlement for the new
  generation only;
- a permanently `UNSUPPORTED` envelope counts as settled for that
  envelope and remains in the published projection set with its
  `UNSUPPORTED` availability visible;
- a `DETACHED` envelope counts as settled for the purpose of removing
  it: per WP1 §3.5, detachment discards the envelope without changing
  source state, so the successor snapshot MUST omit that envelope
  entirely rather than carry it forward in any availability state. A
  `DETACHED` notification triggers recomposition of the projection set;
  it is never itself a published projection.

WP7 does not evaluate settlement for Workspace Context, Asset Focus,
Navigation, or Contribution: those runtimes' own terminal/stable states
(per their WP1 state machines) are read directly and are not
re-classified by WP7.

4.4 Experience Snapshot Builder

A pure function from "current stable state of WP2–WP6" to one immutable
Experience Snapshot (§5). It performs no I/O. It must:

- copy references, not payloads — the snapshot holds the same
  `ProjectionEnvelope`, `AssetFocusReference`, `ContributionAvailability`,
  and navigation/workspace objects already published upstream, not copies
  with rewritten fields;
- preserve every upstream degradation, availability, and provenance
  marker unchanged;
- never substitute a default, a cached prior value, or a synthesized
  "safe" value for an absent or unsettled field.

4.5 Publication Gate

The gate controls when a built snapshot becomes the current published
Experience Snapshot. A snapshot may publish only when:

- Workspace Context is `RESOLVED`;
- Asset Focus, if present, is in a stable state (`ACTIVE` or `REJECTED`,
  not `REQUESTED`) — or Asset Focus is `ABSENT`;
- Navigation composition (WP4) has produced a stable result for the
  current route, or Navigation is not applicable to the current
  interaction;
- the single active Contribution referenced by the Workspace Context's
  `active_contribution_id` (WP1 §3.1), if any, has reached a
  non-transitional `ContributionAvailability` state (`AVAILABLE`,
  `DEGRADED`, `UNAVAILABLE`, `UNSUPPORTED`, or `ABSENT`); WP7 composes
  only this one active association, never the wider declared
  Contribution catalog;
- the current projection set is settled per §4.3.

A gate that is not yet satisfied does not publish a partial snapshot; it
retains the previously published snapshot (if any) until the new one
settles, or publishes nothing if this is the first composition for the
interaction. WP7 never publishes a snapshot mid-transition.

4.6 Replacement Orchestrator

Owns exchanging one published Experience Snapshot for the next once the
Publication Gate is satisfied for a new generation (§8).

4.7 Retirement Orchestrator

Owns discarding the current Experience Snapshot when its Workspace
Context is discarded (§9).

4.8 Stale-Result Suppressor

Shared generation-validation logic (§9) consumed by the Sequencer,
Settlement Detector, and Publication Gate so that a late upstream
notification from a retired generation can never mutate a newer or
already-retired snapshot.

4.9 Experience Observation Interface

Read-only. Consumers may:

- read the last published Experience Snapshot, if one exists;
- observe replacement (new snapshot published) and retirement (snapshot
  removed, no successor yet).

It exposes no mutation authority, no Registry payload beyond what
upstream already published, and no internal generation identifier. It
additionally exposes a `recomposition_pending` observation signal
(operational metadata, not a snapshot field per §5) that is true whenever
a newer generation has begun composing (§8) but has not yet published.
While `recomposition_pending` is true, the Interface MUST NOT represent
the last published snapshot as confirmed-current business state: it is
the last published snapshot, pending confirmation by the settling
generation, and consumers MUST treat it accordingly. The signal never
carries business meaning of its own and never blocks a consumer from
reading the last published snapshot — it only qualifies the strength of
the claim "this is current."

5. The Unified Experience Snapshot

The Experience Snapshot is the only new runtime contract WP7 introduces.
It is Experience-owned in its own right (composition grammar, sequencing
metadata, publication identity) while every field it carries remains
owned by the runtime that produced it.

| Field | Presence | Meaning | Owner |
|---|---|---|---|
| `experience_id` | Required | Opaque identity of this published snapshot instance | Experience Platform (WP7) |
| `workspace` | Required | Current `WorkspaceDescriptor` reference | WP2 |
| `current_selection` | Optional | Current Selection relationship reference | WP2 |
| `asset_focus` | Optional | Current `AssetFocusReference`, if any | WP3 |
| `navigation_position` | Optional | Current navigation/route reference | WP4 |
| `active_contribution` | Optional | The `ContributionDescriptor` bound to the Workspace Context's `active_contribution_id`, paired with its current `ContributionAvailability`; absent when no contribution is attached | WP5 |
| `projections` | Required (may be empty) | Set of current, still-attached `ProjectionEnvelope` references; a `DETACHED` envelope is removed from this set, never carried forward | WP6 |
| `composition_state` | Required | `COMPOSING`, `PUBLISHED`, or `RETIRED` | Experience Platform (WP7) |

**Invariants.** Exactly one `workspace` reference, `RESOLVED` at
publication time; `asset_focus`, when present, is the same immutable
`AssetFocusReference` instance WP3 currently publishes — WP7 does not
construct or mutate one; `active_contribution` reflects only the single
association named by `active_contribution_id` (WP1 §3.1) — WP7 never
enumerates or evaluates other declared Contribution descriptors; every
entry in `projections` is a reference to the corresponding upstream
instance, not a rebuilt copy, and never includes a `DETACHED` envelope;
`composition_state` is Experience-owned and carries no business
semantics.

**Prohibited states.** A `PUBLISHED` snapshot containing a `REQUESTED`
Asset Focus, an unsettled projection, a `DETACHED` projection still
present in the set, or a transitional Contribution availability; a
snapshot representing more than the one active Contribution association;
a snapshot fabricating a field no upstream runtime currently publishes;
a snapshot surviving its Workspace Context's discard; a snapshot whose
generation has begun being superseded (§8) presented to a consumer as
confirmed-current business state rather than as the last published
snapshot pending confirmation, per the `recomposition_pending` signal
in §4.9.

6. Composition lifecycle

| State | Meaning | Owner |
|---|---|---|
| `COMPOSING` | The coordinator has begun building a snapshot for the current generation; not yet publishable | Experience Platform |
| `PUBLISHED` | The Publication Gate accepted this snapshot as the current Experience state | Experience Platform |
| `RETIRED` | This snapshot instance has been superseded or discarded | Experience Platform |

| Transition | Canonical owner | Preconditions and effect |
|---|---|---|
| (none) → `COMPOSING` | Experience Platform | A new generation begins when Workspace Context resolves or any upstream link changes for the current interaction |
| `COMPOSING` → `PUBLISHED` | Experience Platform | Publication Gate (§4.5) is satisfied |
| `PUBLISHED` → `RETIRED` | Experience Platform | Replacement (§8) or retirement (§9) occurs |
| `COMPOSING` → `RETIRED` | Experience Platform | The generation is superseded or its Workspace Context is discarded before ever publishing |

`RETIRED` is terminal for that snapshot instance. There is no
`PUBLISHED` → `COMPOSING` transition on the same instance: a change
starts a new generation and a new snapshot instance, per §8.

7. Composition sequencing

For one interaction, WP7 reads upstream state in canonical chain order
and builds the snapshot bottom-up from what has already settled:

1. Read Workspace Context (WP2). If not `RESOLVED`, remain `COMPOSING`
   with no downstream reads; no snapshot publishes.
2. Read Asset Focus (WP3), if applicable to the current route or
   selection. `REQUESTED` keeps the generation `COMPOSING`.
3. Read Navigation (WP4) for the current route. An unresolved or
   in-flight navigation result keeps the generation `COMPOSING`.
4. Read the single active Contribution named by the Workspace Context's
   `active_contribution_id`, if any, and its current
   `ContributionAvailability`. A transitional evaluation of that one
   association keeps the generation `COMPOSING`; WP7 does not read,
   enumerate, or wait on any other declared Contribution descriptor —
   only the one association WP2's context currently names.
5. Read the current Projection Composition (WP6) set and evaluate
   settlement (§4.3).
6. When steps 1–5 all report stable/settled results for the same
   generation, build the snapshot (§4.4) and submit it to the
   Publication Gate.

Sequencing governs read order only. Ownership of every upstream fact and
transition remains with its originating work package regardless of when
WP7 reads it.

8. Replacement orchestration

Replacement occurs when any upstream link produces a new result for the
current interaction after a snapshot has already published (for example,
Asset Focus is replaced, a contribution is re-evaluated, or a projection
refreshes).

Replacement is atomic from the observer's perspective:

- a new generation begins (§9), and the `recomposition_pending` signal
  (§4.9) becomes true for the currently published snapshot;
- the previously `PUBLISHED` snapshot remains the only observable
  snapshot until the new one is ready to publish, but from the moment
  `recomposition_pending` becomes true it is exposed as the last
  published snapshot pending confirmation, not asserted as
  confirmed-current business state — its supersession is disclosed via
  `recomposition_pending` rather than left undetectable;
- the coordinator re-runs sequencing (§7) against the new generation;
- no field of the previously `PUBLISHED` snapshot is copied into or
  reused by the successor; the successor is built fresh from §4.4 over
  only the new generation's stable upstream state;
- when the Publication Gate accepts the new snapshot, the old instance
  transitions to `RETIRED` and the new instance transitions to
  `PUBLISHED` as a single observable exchange — consumers never observe
  a gap or a partially-updated snapshot;
- if the new generation fails to settle (for example, Asset Focus
  rejects), the coordinator publishes the new stable combination
  (including the `REJECTED` focus reference) once every other link is
  stable — a rejected upstream result is a valid, publishable stable
  state, distinct from an in-flight one.

WP7 does not retry, override, or reinterpret an upstream rejection. It
composes whatever stable state each runtime currently publishes,
including `REJECTED` and `UNAVAILABLE` outcomes.

9. Retirement orchestration

Retirement occurs when the Workspace Context itself is discarded (WP2
`RESOLVED` → `DISCARDED`), independent of any individual downstream
field change.

On Workspace Context discard, WP7:

- transitions the current snapshot instance (whether `COMPOSING` or
  `PUBLISHED`) to `RETIRED`;
- detaches all Upstream Observation Adapter subscriptions for that
  generation;
- invalidates any in-flight settlement evaluation for that generation;
  ignores later completions from it;
- publishes no successor snapshot until a new Workspace Context resolves
  and a new generation begins sequencing from step 1 of §7.

WP7 introduces no snapshot state beyond `RETIRED`; there is no
Experience-level "discarded-but-recoverable" state, matching WP2's and
WP3's precedent that discard is not reversible on the same instance.

10. Concurrency and stale-result suppression

Each Experience Snapshot generation carries an internal, opaque,
monotonically changing generation marker — operational metadata, not a
public contract field (consistent with the generation mechanisms in WP2
§5.5 and WP3 §9).

An upstream notification (from any of WP2–WP6) may affect the current
generation only when all hold:

- the coordinator's current generation is unchanged since the
  notification was issued;
- the originating Workspace Context instance is unchanged and still
  `RESOLVED`;
- the notification's source runtime instance is still the one currently
  attached (no intervening replacement of that specific upstream link);
- for a settlement-relevant notification, the referenced projection or
  contribution attachment is still part of the current generation's set.

Otherwise the notification is stale and is ignored without mutating
state. Required race behavior:

- a late Asset Focus activation for a since-replaced focus request
  cannot alter the published snapshot;
- a late projection settlement from a retired generation cannot trigger
  publication;
- duplicate settlement notifications produce at most one publication;
- out-of-order upstream completions cannot cause the coordinator to
  revert a newer stable state to an older one;
- cancellation of in-flight upstream work is an optimization only —
  correctness depends on generation validation, not on successful
  cancellation.

11. Fail-closed rules

| Condition | Required behavior |
|---|---|
| Workspace Context not `RESOLVED` | No composition attempt; no snapshot publishes |
| Asset Focus `REQUESTED` | Generation remains `COMPOSING`; last published snapshot (if any) stays the only observable snapshot |
| Navigation unresolved for current route | Generation remains `COMPOSING` |
| The active Contribution (if any) still evaluating | Generation remains `COMPOSING` |
| Any attached projection still `REQUESTED` | Generation remains `COMPOSING` |
| A projection reaches `DETACHED` | Envelope is removed from the published set; not carried forward in any availability state |
| Replacement begins for a `PUBLISHED` snapshot | `recomposition_pending` becomes true; the last published snapshot is exposed as pending confirmation, not asserted as confirmed-current business state, and is not itself mutated or hidden |
| Workspace Context discarded mid-composition | Generation transitions `COMPOSING` → `RETIRED`; no publication |
| Workspace Context discarded post-publication | Published snapshot transitions `PUBLISHED` → `RETIRED`; no successor until new context resolves |
| Stale upstream notification | Ignored; no state mutation |
| Upstream runtime reports an error/failure state | Composed as-is (e.g. `REJECTED` focus, `UNAVAILABLE` contribution, `UNAVAILABLE`/`UNSUPPORTED` projection) — never hidden, retried silently, or replaced with a default |
| Missing optional field upstream | Represented as absent in the snapshot; never defaulted, zeroed, or treated as current/safe/approved |

WP7 never fabricates a missing upstream fact to unblock publication.
Partial settlement blocks publication; it never produces a partial
snapshot.

12. Dependency boundaries

WP7 may depend on:

- the frozen WP2 public Workspace Context observation interface;
- the frozen WP3 public Asset Focus observation interface;
- the frozen WP4 public Navigation observation interface;
- the frozen WP5 public Contribution descriptor/availability interface;
- the frozen WP6 public Projection Composition/availability interface;
- Experience-owned composition-sequencing and generation logic introduced
  by WP7 itself.

WP7 must never depend on:

- Registry, Search, Resolver, or provider adapters, directly or by
  reaching through an upstream runtime's internals;
- Portfolio persistence, beyond the Current Selection reference WP2
  already publishes;
- Market Intelligence, Intelligence, Intent, or Action implementations;
- private/internal state of WP2–WP6 (only their public observation
  interfaces);
- undeclared ambient state of any kind.

Every dependency must be declared and public, consistent with WP1 §6 and
the conformance requirement `CO-02`.

13. Implementation sequence

1. Define the immutable Experience Snapshot representation and its
   strict structural validator.
2. Define the pure `composition_state` transition engine
   (`COMPOSING`/`PUBLISHED`/`RETIRED`).
3. Implement the five Upstream Observation Adapters, each bound only to
   its runtime's frozen public interface.
4. Implement the Composition Sequencer enforcing canonical chain read
   order.
5. Implement the Settlement Detector for the projection set.
6. Implement the Experience Snapshot Builder as a pure function over
   stable upstream state.
7. Implement the Publication Gate and its stable/unstable classification
   per link.
8. Implement generation-based stale-result suppression shared across
   the Sequencer, Settlement Detector, and Publication Gate.
9. Implement Replacement Orchestration (atomic exchange, no observable
   gap or partial state).
10. Implement Retirement Orchestration bound to WP2 Workspace Context
    discard notifications.
11. Implement the read-only Experience Observation Interface.
12. Add structural dependency, sequencing, settlement, concurrency, and
    end-to-end conformance gates; verify WP1–WP6 artifacts remain
    unchanged.

This order establishes pure sequencing and publication invariants before
wiring live upstream subscriptions, preventing partial or racy snapshots
from ever becoming observable.

14. Conformance mapping

| WP1 requirement | WP7 realization |
|---|---|
| OW-01, OW-02 | Every snapshot field maps to exactly one upstream or WP7-owned field; no shared ownership |
| OW-03 | Snapshot Builder copies references only; never rewrites source facts |
| CO-01 | Publication Gate requires `RESOLVED` Workspace Context before any publication |
| CO-02 | Dependency boundaries restrict WP7 to WP2–WP6 frozen public interfaces only |
| CO-03 | Contribution/projection failures compose independently; one `UNAVAILABLE` link does not block others |
| CO-04 | Snapshot is a reference aggregate, not a computed authoritative fact |
| CO-05 | WP7 composes only the single active Contribution named by WP2's `active_contribution_id`; its `ContributionAvailability` remains namespaced per WP5 and is never merged with or substituted for other declared descriptors |
| CO-06 | Current Selection reference passes through unchanged and independent of Asset Focus |
| DG-01, DG-02, DG-03 | Settlement Detector and Publication Gate preserve distinct available/degraded/unavailable/unsupported/absent states; a `DETACHED` projection is removed from the published set rather than represented in any availability state; never default missing data |
| RR-04, RT-04 | WP7 performs no Registry, Search, Resolver, or provider calls of its own |
| SM-WC-02 | Retirement Orchestrator ties snapshot retirement to Workspace Context discard; no composition on `REJECTED`/`DISCARDED` contexts |
| SM-AF-01 | Publication Gate never publishes a `REQUESTED` Asset Focus |
| SM-PA-01, SM-PA-02 | Settlement Detector requires every projection to leave `REQUESTED`; distinguishes terminal outcomes |
| CT-02 | Field-owner assertions across the full Experience Snapshot |
| CT-05 | Projection references preserve provenance, temporal, quality, and degradation context unchanged |
| CT-07 | Structural and runtime dependency evidence restricted to WP2–WP6 public interfaces |

15. Mandatory acceptance tests

Contract and ownership

- The Experience Snapshot contains exactly the fields in §5; no
  additional fields.
- Every field resolves to exactly one owner (WP2–WP6 or WP7).
- No snapshot field is computed as a new authoritative business fact.

Composition lifecycle

- Every `composition_state` transition in §6 succeeds; every unlisted
  transition fails closed.
- A generation that never settles never reaches `PUBLISHED`.
- `RETIRED` is terminal for its instance.

Sequencing and settlement

- Composition does not proceed past Workspace Context until it is
  `RESOLVED`.
- A `REQUESTED` Asset Focus, an unresolved Navigation result, an
  evaluating active Contribution, or a `REQUESTED` projection each
  independently keep the generation `COMPOSING`.
- A `REJECTED` Asset Focus, an `UNAVAILABLE` active Contribution, or an
  `UNSUPPORTED`/`UNAVAILABLE` projection are each treated as settled and
  do not block publication of the other links.
- WP7 reads and composes only the single Contribution named by
  `active_contribution_id`; a declared-but-inactive Contribution
  descriptor is never read, evaluated, or allowed to block publication.
- A `DETACHED` projection is excluded from the published `projections`
  set in the next snapshot; it never appears with a `DETACHED`
  availability inside a published snapshot.

Publication and replacement

- The Publication Gate never publishes a partial snapshot.
- Replacement is observed as a single atomic exchange; no consumer
  observes an intermediate or missing snapshot.
- A superseded generation transitions to `RETIRED` without mutating the
  newly published snapshot.
- While a replacement is in flight, the last published snapshot exposes
  `recomposition_pending = true` and is exposed as pending confirmation,
  never as confirmed-current business state; no consumer can observe a
  snapshot whose generation is being superseded with no means of
  detecting that supersession.
- The successor snapshot never reuses a field value copied from the
  snapshot it replaces; every field is rebuilt from that generation's
  own stable upstream state.

Retirement

- Workspace Context discard retires the current snapshot regardless of
  its `composition_state`.
- No successor snapshot publishes until a new Workspace Context resolves.
- Retirement detaches all five Upstream Observation Adapters for that
  generation.

Concurrency

- A late notification from a retired generation cannot mutate the
  current or a newer snapshot.
- Duplicate settlement notifications produce at most one publication.
- Out-of-order upstream completions cannot revert newer state to older
  state.
- Cancellation failure of in-flight upstream work does not break
  correctness.

Dependency enforcement

- Static checks reject any WP7 import of Registry, Search, Resolver,
  provider, Portfolio persistence, Intelligence, Intent, or Action
  internals.
- Runtime spies prove WP7 calls only the five frozen public observation
  interfaces of WP2–WP6.
- No new public mutation HTTP endpoint is introduced by WP7.
- WP1–WP6 artifacts remain unchanged.

16. Completion criteria

WP7 is complete only when:

- The Experience Snapshot exactly matches §5, with every field owned by
  exactly one upstream work package or by WP7 itself.
- The `composition_state` lifecycle in §6 is fully enforced, with all
  other transitions failing closed.
- Publication never occurs before every applicable link (Workspace
  Context, Asset Focus, Navigation, Contribution, Projection Composition)
  has reached a stable or settled result for the same generation.
- Replacement and retirement are atomic and observable exactly as
  specified in §8 and §9.
- Stale results from any of the five upstream runtimes cannot mutate a
  current or newer snapshot.
- Structural and runtime evidence proves WP7 depends only on the frozen
  public interfaces of WP2–WP6.
- All conformance mappings in §14 and acceptance tests in §15 pass.
- No frozen WP1–WP6 or M35–M37 artifact requires modification.

WP7 implementation design status: COMPLETE — READY FOR IMPLEMENTATION.
No repository files outside this document were modified.
