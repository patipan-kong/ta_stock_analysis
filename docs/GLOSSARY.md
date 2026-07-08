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