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
Negotiated, bilateral transfer.

The mechanism, never the venue — venues are instance facts.


## Settlement Semantics

When an agreed change of hands becomes real.

Instant. Cycle-based. Negotiated closing.

A negotiated closing carries no standard cycle length — the date is
itself an agreed term of the transaction, not a fixed number of days
after trade.


## Valuation Semantics

What question, if any, establishes a kind's worth.

Identity. Continuous quotation. Periodic NAV. Appraisal-on-event.

No definition ever states the arithmetic — only that the question exists.

An appraisal-on-event question is triggered by a sale, a refinancing, or
a holder-chosen revaluation date — never a continuous market, never a
fixed recurring schedule.

The declaration Market Intelligence answers, never derives.


## Flow Type

One kind of holding-generated flow a definition may grant.

Dividend. Coupon. Interest. Rent. Staking. Distribution.

Each carries its income character.

Rent is income from a counterparty's occupancy or use of a physical
asset — not a coupon's yield against a held instrument's principal.

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


## Portfolio Identity

The stable identifier of one portfolio container.

Owned by Ledger & Accounting.

It establishes accounting identity. It does not own strategy, goals,
decision policy, analytics, or UI selection.

Governed by `M34-D-0002`.


## Accounting Scope

The accounting boundary to which a portfolio's holdings, transactions, cash,
and balances belong.

Owned by Ledger & Accounting.

Every semantic projection of one portfolio refers to the same Accounting
Scope. No downstream domain may redefine it.

Governed by `M34-D-0002`.


## Portfolio Strategy Metadata

Metadata describing a portfolio as an investment-strategy container.

Owned by Portfolio Intelligence.

It excludes Goal Target, Decision Policy, and accounting truth.

Governed by `M34-D-0002` and `M34-D-0007`.


## Goal Target

The desired investment objective, financial objective, or intended outcome.

Owned by Wealth Intelligence.

Strategy and policy may reference it but do not own it.

Governed by `M34-D-0002` and `M34-D-0007`.


## Current Selection

The current Experience interaction state naming which portfolio a person is
viewing.

Owned by Experience Platform.

It has no business meaning and never establishes or changes Portfolio
Identity or Accounting Scope.

Governed by `M34-D-0002`.


## Portfolio Membership

The Ledger fact that a holding or instrument belongs to one or more Portfolio
Accounting Scopes.

Owned by Ledger & Accounting.

It is not an investment interpretation or cross-portfolio exposure measure.

Governed by `M34-D-0003`.


## Cross-Portfolio Aggregation

A mathematical aggregation of holdings across multiple Ledger-owned
Accounting Scopes.

Owned by Ledger & Accounting.

It adds no investment meaning and retains every contributing scope.

Governed by `M34-D-0003`.


## Cross-Portfolio Exposure

The interpretation of Cross-Portfolio Aggregation as overall investment
exposure.

Owned by Wealth Intelligence.

It consumes Ledger facts, Market Intelligence observations, and Asset
Foundation classifications without owning them. Provenance to every
contributing Accounting Scope is mandatory.

Governed by `M34-D-0003`.


## Asset Classification

The canonical classification assigned to an Asset.

Owned by Asset Foundation.

Provider metadata, cached or persisted copies, transports, and UI projections
never become canonical by being stored or displayed.

Governed by `M34-D-0004`.


## Market Classification Evidence

Provider-supplied classification metadata used as evidence for Asset
Classification.

Owned by Market Intelligence as evidence.

It informs Asset Foundation but never establishes canonical classification
authority.

Governed by `M34-D-0004`.


## Analytical Grouping

A context-specific grouping used for portfolio analysis, allocation, factor
analysis, attribution, reporting, or visualization.

Owned by Portfolio Intelligence for the M34 portfolio-analysis contexts.

It is distinct from Asset Classification even when both are presented with a
similar label. Experience may visualize it but cannot define it.

Governed by `M34-D-0001` and `M34-D-0004`.


## Canonical Temporal Claim

An authoritative statement of when a material event occurred and what its
availability means.

It contains exactly:

- Event Type;
- Producing Domain;
- authoritative timestamp; and
- Degraded State.

Governed by `M34-D-0005`.


## Event Type

The material event dated by a Canonical Temporal Claim.

Approved event types are Observation, Retrieval, Calculation, Analysis
Generation, Snapshot Creation, Batch Evaluation, and Synchronization.

The Producing Domain owns the event's meaning.

Governed by `M34-D-0005`.


## Producing Domain

The constitutional domain that owns the material event or source status in a
Canonical Temporal Claim.

It owns the event, timestamp meaning, and Degraded State. Experience Platform
only renders them.

Governed by `M34-D-0005`.


## Degraded State

The producing domain's canonical qualification that a fact or result is not
fully available as ordinary current truth.

Approved states are `UNKNOWN`, `UNAVAILABLE`, `DELAYED`, `STALE`, `PARTIAL`,
and `CONFLICTING`.

Experience Platform may render a Degraded State but never derives or
reinterprets it.

Governed by `M34-D-0005`.


## Presentation Label

Non-normative Experience language such as `Updated`, `As Of`, `Current`, or
`Fresh`.

Owned by Experience Platform as presentation vocabulary only.

It has no canonical temporal meaning unless accompanied by the complete
Canonical Temporal Claim. Client refresh, cache refresh, polling, rendering,
and interaction do not redefine source freshness.

Governed by `M34-D-0005`.


## Decision Policy

Policy envelopes, optimization rules, decision constraints, execution
preferences, and optimizer behavior.

Owned by Decision Intelligence.

It may reference Goal Target and Portfolio Strategy Metadata but owns
neither.

Governed by `M34-D-0007`.


## Portfolio Limits

Constraints on portfolio composition and optimization.

Owned by Decision Intelligence.

They govern decision behavior, not Portfolio Identity or Accounting Scope.

Governed by `M34-D-0007`.


## Sector Limits

Decision constraints that reference Asset Classification.

Owned by Decision Intelligence.

They do not redefine Asset Foundation classification or Market
Classification Evidence.

Governed by `M34-D-0004` and `M34-D-0007`.


## Persona

A bounded reference preset over independently owned settings.

Persona has no independent business-rule authority.

It never becomes Portfolio Strategy Metadata, Goal Target, Decision Policy,
or a new domain. Every referenced setting retains its constitutional owner.

Governed by `M34-D-0007`.


## Model Selection

Selection of an analytical or decision model used for a specific governed
behavior.

Owned by the one producing constitutional domain responsible for that
behavior.

It never creates platform-wide configuration authority. The concrete owner
must be named before the setting can support WP6.

Governed by `M34-D-0007`.


## Analysis Source Selection

Selection of data or analytical sources for one consuming constitutional
domain.

Owned by that one consuming constitutional domain.

It configures consumption behavior and never establishes ownership of the
underlying data or source.

Governed by `M34-D-0007`.


## Optimizer Configuration

Configuration of optimizer-layer orchestration and fallback behavior.

Owned by Decision Intelligence.

It governs optimizer behavior only and grants no execution or approval
authority.

Governed by `M34-D-0007` and constrained by `M34-D-0008`.


## Execution Plan Projection

A historical projection presented by the legacy execution workflow.

It is a `STOPPED_AUTHORITY` artifact.

It is not a canonical execution plan, approved execution intent, authorized
trading instruction, or execution authorization.

Governed by `M34-D-0008`.


## Legacy Decision Record

A historical application record showing only that the legacy system stored a
decision-related record.

It is a `STOPPED_AUTHORITY` artifact.

It proves no human approval, decision authority, authenticated actor,
constitutional authorization, or actor attribution.

Governed by `M34-D-0008`.


## STOPPED_AUTHORITY

A governance classification for a retained historical artifact whose
unqualified label could imply authority denied by a closed predecessor
decision.

It permits verification of non-authority and other approved negative
guarantees only.

It never grants execution planning, approval, authorization, human intent,
decision authority, or actor attribution.

Governed by `M34-D-0008`; M32 and M33 remain closed.


## Execution Detail

Historical execution-related presentation derived from legacy records.

It is a `STOPPED_AUTHORITY` artifact and is not proof of canonical planning,
approval, authorization, or actor attribution.

Governed by `M34-D-0008`.


## Plan-versus-Actual Comparison

An analytical comparison between a legacy projection and observed outcomes.

Owned by Trust & Evaluation as a comparison.

It evaluates the legacy projection only and never makes that projection a
canonical plan or authorized instruction.

Governed by `M34-D-0008`.


## Decision Memory

Historical context composed from legacy decision-related artifacts.

It is a `STOPPED_AUTHORITY` reference composition.

It establishes neither Decision Intelligence authority nor immutable
governance truth.

Governed by `M34-D-0008`.


## Portfolio Status

Status describing portfolio-derived information.

Owned by Portfolio Intelligence.

It is a source-domain status, not aggregate Operations truth.

Governed by `M34-D-0009`.


## Goal Status

Status describing the current state of a Goal Target.

Owned by Wealth Intelligence.

It retains Goal Target provenance and the canonical temporal grammar.

Governed by `M34-D-0005` and `M34-D-0009`.


## Market Context Status

Status describing market observations and context.

Owned by Market Intelligence.

It does not own portfolio, decision, or evaluation meaning.

Governed by `M34-D-0009`.


## Optimizer Status

Status describing optimizer lifecycle, readiness, and internal processing.

Owned by Decision Intelligence.

It is operational status only and grants no execution or approval authority.

Governed by `M34-D-0008` and `M34-D-0009`.


## Policy Status

Status describing Decision Policy evaluation and applicability.

Owned by Decision Intelligence.

It does not constitute approval, execution authorization, or human intent.

Governed by `M34-D-0009`.


## Station Health

Operational status supplied by one responsible producing constitutional
domain for a concrete station.

Owned by that producing domain.

There is no independent platform-wide Health concept. The concrete owner must
be named before the status can support WP6.

Governed by `M34-D-0009`.


## Committee Status

Status supplied by the one constitutional domain responsible for a concrete
governance component.

Owned by that producing domain.

It never implies human approval. Legacy inputs remain `STOPPED_AUTHORITY`, and
the concrete owner must be named before the status can support WP6.

Governed by `M34-D-0008` and `M34-D-0009`.


## Translation Status

Operational lifecycle status supplied by a translation service.

Owned by the one constitutional domain responsible for that service.

It carries no investment, approval, authorization, or execution meaning. The
concrete owner must be named before the status can support WP6.

Governed by `M34-D-0009`.


## Action Required

Experience presentation indicating that one or more source domains require
user attention.

Owned by Experience Platform as presentation meaning only.

It is not a decision, approval, execution instruction, authorization, or
source-domain status.

Governed by `M34-D-0009`.


## Market Observation

An observable market fact, including a price, technical observation, market
statistic, provider observation, or news reference.

Owned by Market Intelligence.

It is evidence, not Investment Judgment. Its source and Canonical Temporal
Claim are mandatory provenance.

Governed by `M34-D-0010`.


## Investment Judgment

Interpretation of observations into an analytical conclusion, outlook, or
expected direction.

Owned by Decision Intelligence.

It consumes Market Observations without owning or converting them into
source authority.

Governed by `M34-D-0010`.


## Instrument-Level Risk

A derived risk assessment for one instrument.

Owned by Decision Intelligence.

It is distinct from portfolio-level risk owned by Portfolio Intelligence.

Governed by `M34-D-0010`.


## Consensus

An aggregated Investment Judgment derived from one or more analytical
sources.

Owned by Decision Intelligence.

Consensus is judgment, not evidence and not source authority.

Governed by `M34-D-0010`.


## Analysis History

A historical record of analytical outputs.

Owned by Decision Intelligence.

It preserves analytical context and does not establish correctness.

Governed by `M34-D-0010`.


## Evaluation

Independent assessment of analytical quality or correctness.

Owned by Trust & Evaluation.

It remains independent of the observation or judgment being evaluated and
does not become operational authority.

Governed by `M34-D-0010`.


## Watchlist Membership

A user-maintained interaction state indicating that an Asset is intentionally
retained for future viewing or investigation.

Owned by Experience Platform.

It expresses preference only and implies no ownership, portfolio inclusion,
accounting identity, recommendation, investment decision, approval, execution
authorization, transaction intent, plan, policy, or human authorization.

Governed by `M34-D-0011`.


## User Preference State

An Experience-owned interaction preference with no independent financial,
investment, portfolio, analytical, recommendation, or execution truth.

Watchlist Membership is one approved User Preference State.

Governed by `M34-D-0011`.


## Interaction State

The state of a bounded user interaction owned by Experience Platform.

It owns no business truth and acquires no authority from adjacent content or
workflows.

Governed by `M34-D-0011`.
