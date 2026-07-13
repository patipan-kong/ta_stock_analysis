## Asset

The canonical representation of an investable instrument.

Every asset receives a permanent internal `asset_id`.

Business logic never depends on provider symbols.

Examples

- Thai Stock
- US Stock
- ETF
- Mutual Fund
- Gold
- Bond
- Crypto


## Asset Registry

The single source of truth for asset identity.

Responsible for

- Canonical identity
- Validation
- Provider mapping
- Metadata

Portfolio Engine never talks directly to external providers.


## Replay Engine

The deterministic engine that reconstructs portfolio state
from transaction history.

Replay Engine is the accounting authority.

Every metric ultimately derives from replay.


## Portfolio Snapshot

A historical snapshot of the replayed portfolio.

Snapshots are immutable historical records.

Used by

- Performance
- Analytics
- Benchmark
- AI Evaluation


## Recommendation Snapshot

A frozen record of one optimizer recommendation.

Contains

- projected allocations
- signals
- confidence
- execution plan

Independent from user decisions.


## Shadow Portfolio

Recommendation Snapshot

↓

Shadow Portfolio

↓

Shadow Portfolio Snapshots


## Ideal Portfolio

A friction-free replay of recommendation history.

Assumes

- Immediate execution
- No fees
- No liquidity constraints
- Full compliance


## AI Portfolio

A replay of recommendations using the platform's execution model.

Unlike Ideal Portfolio,
it preserves execution ordering and practical constraints.


## Gap A

Gap A = Ideal Portfolio − AI Portfolio

Measures

Implementation Shortfall

"What practical execution cost."

Not

Human decision quality.


## Gap B

Gap B = AI Portfolio − You

Measures

Human deviation from AI recommendations.

Positive

Human outperformed AI.

Negative

AI outperformed Human.


## Opportunity Cost

The estimated return difference between
actual decisions
and alternative AI actions.

Counterfactual.

Not realized profit.


## Recommendation Grade

Independent evaluation of

Belief

Execution

Outcome

A recommendation can have

Good idea

Poor execution

Excellent outcome

simultaneously.


## Implementation Shortfall

Difference between

Ideal execution

and

Practical execution.

A subset of Gap A.


## Funding Efficiency

How efficiently capital was deployed
relative to the recommended execution plan.


## Necessity

Measures whether a trade was actually required
to reach the intended portfolio state.

Low necessity

=

avoidable trading.


## Canonical Symbol

Platform-owned symbol.

Stable.

Independent of providers.


## Business Logic

The deterministic investment logic.

Must never depend on

Yahoo

Polygon

Morningstar

Provider-specific identifiers.


## Ledger

The append-only record of financial events.

The single source of truth.

Every balance, holding, snapshot, and metric
is a derivation of ledger events.


## Canonical Ledger Event

The one form in which facts enter the platform.

Every input source — manual entry, file, broker API, document —
is translated into canonical events before reaching accounting.

"Many doors, one hallway."


## Derivation

Any state computed from the ledger.

Holdings. Cash balances. Snapshots. Metrics.

Disposable.

Rebuildable.

Never an independent source of truth.


## Provenance

Where a fact came from.

Every ingested event records its source, time, and adapter.

Preserved forever.


## Proposal

An automated input awaiting human confirmation.

Machines propose.

The human confirms truth.

Auto-acceptance exists only as explicit, revocable, per-source delegation.


## Witness

An external party that informs the platform.

Providers witness prices.

Brokers witness trades.

Witnesses inform; they never overwrite.

No witness is an authority.


## Gate

One of exactly three doorways through which recorded state changes.

1. Ingestion gate — facts become truth
2. Decision gate — intent becomes action
3. Configuration gate — learning becomes future behavior

Everything else is derivation and display.


## Observer Plane

Where Trust & Evaluation lives.

Beside the pipeline, not in it.

Reads records.

Writes only its own.

Nothing operational depends on it.


## Domain

A boundary of ownership and meaning.

Not a module.

Not a team.

Not a deployment unit.

Every concept has exactly one domain home.


## Platform Domains

The nine domains of the constitution:

- Asset Foundation — what things are
- Market Intelligence — what things are worth
- Ledger & Accounting — what happened
- Connectivity & Ingestion — how facts enter
- Portfolio Intelligence — what it means
- Decision Intelligence — what to do
- Trust & Evaluation — was it right
- Wealth Intelligence — the whole financial life
- Experience Platform — how a person meets it

Defined in `docs/architecture/platform_architecture.md`.


## Asset Definition

The declarative behavior contract of an asset class.

Unit semantics. Valuation cadence. Flow types. Lifecycle vocabulary.

Written in a closed, platform-owned vocabulary.

A definition can only say things engines already know how to hear.

Engines consume declarations through single implementations.

They never contain asset-class branches.

"Assets are plugins" — by description, never by code.


## Capability

One queryable behavior fact granted by an asset definition.

Supports NAV. Supports coupons. Supports corporate actions.

Independently combinable.

Engines branch on capabilities, never on types.


## Evidence File

Every external name an asset is known by.

ISINs, tickers, provider symbols, broker codes.

Externally owned. Mutable. Plural. Time-bounded.

Maps into identity; the arrow never reverses.

Survives every provider.


## Claim

Evidence that something exists, before identity does.

Discovery → Candidate → Verified.

Reversible until minting.

A claim never mints itself.


## Structural Event

An adjudicated fact about what the world did to an instrument.

Splits, mergers, spin-offs, renames, delistings, redemptions.

Classified into a closed family vocabulary before any consequence.

Moves lifecycle. Authors relationships.

Proposes ledger consequences — never performs them.


## Domain Constitution

A document that governs one domain's interior.

`OPTIMIZER_PHILOSOPHY.md` — Decision Intelligence.

`PORTFOLIO_CALCULATION_RULES.md` — accounting semantics.

Supreme inside the boundary.

Subordinate to the Platform Architecture at the boundary.

## Definition Vocabulary

The closed set of words asset definitions are written in.

Platform-owned. Extended only by governance, never by data.

Every word exists because some engine must behave differently on it.

Its size is a health metric of the whole abstraction.


## Axis

One of the seven questions a definition answers about a kind:

unit semantics, acquisition, settlement, valuation,
flow grants, event-family grants, existence pattern.

The axes are constitutional; the words on each axis are canonical.

Defined in `docs/architecture/asset_definitions.md` §5.1.


## Grant

A boolean declaration in an asset definition.

Supports coupons. Supports corporate actions.

Present or absent — and absence is itself a declaration.

An ungranted capability means "does not support," never "unknown."


## Unit Semantics

How a kind is counted.

What one unit is. Discrete or continuous. Sign. Conservation.

The declaration the Accounting Engine can never do without.


## Acquisition Semantics

How a kind changes hands.

Not transactable. Venue-traded. NAV-window subscription/redemption.

The mechanism, never the venue — venues are instance facts.


## Valuation Semantics

What question, if any, establishes a kind's worth.

Identity. Continuous quotation. Periodic NAV.

No definition ever states the arithmetic — only that the question exists.

The declaration Market Intelligence answers, never derives.


## Flow Type

One kind of holding-generated flow a definition may grant.

Dividend. Coupon. Interest. Rent. Staking. Distribution.

Each carries its income character.

An ungranted flow is a flow the ledger refuses.


## Event Family

One kind of structural event a definition may grant.

Split. Merger. Spin-off. Redemption. Expiry. Exercise.

Definitions grant the family; Lifecycle & Structural Events
interprets the actual event.


## Existence Pattern

The lifecycle shape a kind follows, until its story ends.

Open-ended. Scheduled-terminal.

A scheduled-terminal kind carries a known-in-advance terminal event —
a bond's maturity, an option's expiry.

The definition declares only that the event exists in the pattern —
never an instance's actual date, never whether it has already happened.

The declaration Lifecycle & Structural Events tracks against, never predicts.


## Definition Version

One immutable published state of an asset definition.

Additive within a version. New version to widen or narrow.

Recorded facts replay under the version that admitted them.

Definitions bind forward, never backward.
