# M32.3A — Normalized Trade Input Audit and Technical Design

**Date:** 2026-07-14

**Decision:** **GO for a shadow-only M32.3B contract and quantity-source
foundation; NO-GO for authoritative executable quantity or canonical planning**

**Scope:** Audit and technical design only. No production code, migration,
optimizer behavior, funding arithmetic, API, frontend, persistence, M31 mode,
broker routing, or ledger behavior was changed.

## 1. Executive summary

The repository does not currently have one normalized trade input. It has
three different kinds of upstream intent and one downstream accounting fact:

1. the optimizer produces target-weight deltas and gross monetary
   `estimated_amount` values;
2. Decision Workspace position sizing produces gross allocation percentages,
   which `execution_plan.py` converts to gross monetary amounts using an
   average-cost portfolio value;
3. manual transaction entry supplies explicit shares and an entered price;
4. the transaction ledger records the shares and price that the user says
   actually executed.

Only the manual transaction boundary has both quantity and price today. The
optimizer and Decision Workspace know allocation value but not executable
quantity. SELL/REDUCE planning knows current holding shares, a gross monetary
release, and a release percentage, but does not own a canonical sell quantity.
M32.2 derives `current_shares × release_pct` and a balancing price only inside
a post-result diagnostic. That derivation is deliberately non-authoritative
and has no price timestamp.

Current price evidence is also insufficient for authoritative planning.
Optimizer price fetches carry `last_updated`, but `main.py` discards it before
calling the optimizer. The provider's `last_updated` is fetch time rather than
an exchange observation timestamp. The quote cache has a five-minute TTL and
may serve expired data on provider failure, while callers commonly receive
only the source fields and do not evaluate staleness. Decision Workspace uses
`avg_cost`, which may be arbitrarily old and is not a market observation.
Manual transaction UI pre-fills a price but passes neither its source time nor
market session to admission.

One backend-owned immutable `NormalizedTradeInput` can serve optimizer,
Decision Workspace, manual admission, fee quoting, trade-leg construction,
and later evaluation, provided it preserves the difference between:

- the source's requested value or quantity;
- the deterministic requested quantity derived from that source;
- the constraint-valid executable quantity;
- the later ledger-recorded fill quantity.

The normalized input must retain the existing `ExecutionInstrumentFacts`,
`ExecutionEligibility`, and `FeeQuote` objects rather than copying their
fields or recalculating them. It must also carry a normalized price observation
with explicit source, observation/receipt times, session, freshness decision,
and currency. `ExecutionTradeLeg` should eventually accept this input instead
of `LegacyExecutionTradeRequest` and must never derive quantity itself.

The repository is ready for M32.3B only as a shadow foundation: introduce the
contract, explicit quantity-source vocabulary, pure validation, and adapters
that can report incomplete normalization without changing current outputs.
Authoritative quantity normalization remains blocked by price-observation
semantics, freshness/session policy, portfolio currency authority, and
lot/fractional residual policy. Canonical net funding remains further blocked
by cash-floor ownership and the absence of a frozen canonical plan.

## 2. Current quantity and price flow

### 2.1 Optimizer recommendation path

```text
main.py
  fetch_price_info(symbol)
    -> current_price, previous_close, last_updated
    -> main.py retains current_price but drops last_updated from planning
  holdings -> shares + avg_cost + current_price
        |
        v
agents/optimizer.py
  holding market value = shares × (current_price or avg_cost or 0)
  total value = equity value + cash
  L2 produces target weights
  Python recomputes:
    allocation_change_percent = target_weight - current_weight
    estimated_amount = allocation_change_percent × total_value
        |
        v
execution_optimizer.py
  BUY/ACCUMULATE deployment = abs(estimated_amount)
  SELL/REDUCE candidate = abs(estimated_amount)
  selected/scaled/deferred amounts remain currency values, not quantities
        |
        +-> frontend/lib/executionPlan.ts re-joins and re-sums amounts
        |
        +-> evaluation/plan_grader.py reconstructs the same gross plan later
```

Exact ownership points:

- `backend/main.py:2049-2083` fetches per-symbol prices. The returned
  `last_updated` does not enter `scores_map`.
- `backend/agents/optimizer.py:90-105` values holdings with
  `current_price or avg_cost`.
- `backend/agents/optimizer.py:1501-1504` creates NAV from those values and
  cash.
- `backend/agents/optimizer.py:1743-1774` accepts target weights from L2 and
  deterministically overwrites monetary `estimated_amount`.
- `backend/agents/optimizer.py:1776-1927` repeatedly recomputes the same
  amount after policy, cash, sector, and execution-risk caps.
- `backend/services/optimizer/execution_optimizer.py:272-316` consumes only
  gross amounts. It does not receive holdings, quantities, prices, timestamps,
  currencies, facts, eligibility, or fee quotes.

Therefore BUY quantity does not come from the optimizer today. It does not
exist. The optimizer owns a constrained allocation value, not a trade size in
units.

### 2.2 Decision Workspace path

```text
DecisionWorkspace
  suggestPositionSizes() -> suggested_pct only
  POST /execution-plan with client-supplied symbols/suggestions/timing
        |
        v
execution_plan.py
  holding value = PortfolioItem.shares × PortfolioItem.avg_cost
  total value = cash + holding values
  BUY amount = suggested_pct × total value
        |
        v
funding_source_analysis.py
  SELL full value = avg-cost holding value
  REDUCE full value = holding value × 25% unless override
        |
        v
execution_optimizer.py
  chooses gross monetary releases
        |
        v
FundingAction
  current_shares + release_pct + estimated_cash_release
  but no canonical quantity or price
```

Exact ownership points:

- `backend/services/position_sizing.py:86-102` publishes `suggested_pct`, not
  value, quantity, or price.
- `backend/services/position_sizing.py:278-285` calculates deployable
  percentages from average-cost portfolio value.
- `backend/main.py:6371-6405` accepts open client-supplied sizing dictionaries.
- `backend/services/execution_plan.py:125-131` again calculates average-cost
  portfolio value.
- `backend/services/execution_plan.py:159-178` converts percentage to gross
  buy amount.
- `backend/services/funding_source_analysis.py:105-114` creates gross SELL and
  REDUCE candidates; REDUCE defaults to 25%.
- `backend/services/funding_source_analysis.py:122-128` converts selected
  gross amount back to a release percentage.
- `backend/services/execution_plan.py:194-221` joins that percentage with
  current held shares, but still returns no sell quantity.

Decision Workspace therefore knows only buy allocation amount. On the sell
side it exposes enough operands to derive a quantity, but no module before
M32.2 accepts authority for that derivation.

### 2.3 M32.2 shadow trade-leg path

`backend/services/execution_trade_leg.py:243-315` is the only planner-adjacent
code that currently derives a trade quantity:

```text
shadow SELL quantity = current_shares × release_pct
shadow unit price = estimated_cash_release / shadow quantity
```

This is explicitly post-result, log-only, and exception-contained. It uses
`price_timestamp=None`. BUY actions are recorded as unprojectable because
they contain only `estimated_amount`. `ExecutionTradeLegBuilder` then copies
the requested quantity into `executable_quantity`; its lot and fractional
summaries are deliberate no-ops.

This shadow derivation proves that the existing SELL shape can be adapted, but
it is not an acceptable source of authoritative price evidence: both its
gross amount and its inferred price originate from average cost.

### 2.4 Manual transaction and ledger path

```text
TransactionModal
  optional current-price prefill
  user enters shares and price
  browser computes display-only fee/total
        |
        v
BUY/SELL API body
  shares + price_per_share + currency + exchange_rate + transaction_date
        |
        v
portfolio_transactions.py
  Decimal shares × Decimal entered price
  compatibility FeeQuote
  net cash mutation and Transaction write
        |
        v
transaction_canonicalizer.py / portfolio_rebuilder.py
  ledger shares, price_per_share, total_amount
  deterministic replay; no planning reconstruction
```

Exact ownership points:

- `frontend/components/TransactionModal.tsx:61-103` accepts/edit shares and
  price and independently estimates fees and total.
- `frontend/components/TransactionModal.tsx:129-145` sends explicit shares and
  price. No source timestamp, session, stale flag, or quote reference is sent.
- `backend/main.py:3656-3678` declares explicit BUY/SELL quantities and prices.
- `backend/main.py:3751-3831` validates positive numbers and delegates them
  unchanged.
- `backend/services/portfolio_transactions.py:247-378` and `:380-511` treat
  these values as posting inputs, quote fees, mutate cash/holdings, and persist
  them as ledger facts.
- `backend/services/transaction_canonicalizer.py:174-229` preserves ledger
  shares, price, total, event date, and record time as immutable Decimal
  inputs for replay.
- `backend/services/portfolio_rebuilder.py:362-458` consumes ledger quantity
  and net amount. Replay never creates planning quantity.

The entered transaction price is treated as the actual execution price, even
when the modal pre-filled it from a market quote. The repository does not
record whether it was a fill, a limit, a quote, a close, or a manual estimate.
`transaction_date` is event ordering at calendar-date precision; `created_at`
is knowledge/insert time. Neither is the price-observation timestamp.

### 2.5 Frontend and evaluation projections

The optimizer frontend has a separate amount-only plan in
`frontend/lib/executionPlan.ts:84-151`. It joins action buckets to allocations,
substitutes optimized sell amounts, and calculates `cashRequired` and
`cashReleased`. It never sees a quantity or a price.

Decision Workspace renders backend gross amounts and explicitly states that
they use `avg cost × shares` and no live prices
(`DecisionWorkspace.tsx:679-982`). It does not currently calculate quantity.

Evaluation reconstructs gross amounts from persisted target allocations in
`backend/services/evaluation/plan_grader.py:97-124` and `:184-211`.
`execution_analyzer.py:88-169` later compares those gross-like planned amounts
with ledger net `total_amount` and calculates a share-weighted fill price from
transactions. This is a consumer of plan and ledger facts, not a valid source
of planning quantity.

Paper/shadow portfolio code derives hypothetical shares from weights and
prices. Those quantities belong to counterfactual evaluation and must remain
outside execution normalization; they are not orders, intents, or fills.

## 3. Existing ownership map

### Quantity ownership today

| Quantity/value | Current producer | Current consumers | Authority today |
|---|---|---|---|
| Holding shares | Transaction replay / `PortfolioItem.shares` cache | Optimizer valuation, plan funding, admission oversell check | Portfolio/ledger truth about currently held units |
| Target weight and delta | Optimizer belief/constraint pipeline | `estimated_amount`, UI, evaluation | Constrained investment allocation, not execution quantity |
| Position-sizing percentage | `position_sizing.py` | Decision Workspace execution request | Allocation advice, not execution quantity |
| Full recommended amount | `execution_optimizer.py` input | Funding selection and display | Gross monetary recommendation |
| Executed amount | `execution_optimizer.py` | Funding display and evaluation | Gross monetary amount selected for today; name is not a fill quantity |
| Release percentage | `funding_source_analysis.py` | `FundingAction`, M32.2 shadow | Ratio of selected gross amount to recommended gross amount |
| M32.2 requested quantity | `execution_trade_leg.py` shadow adapter | `FeeQuote`, shadow leg | Diagnostic only: held shares × release percentage |
| M32.2 executable quantity | `ExecutionTradeLegBuilder` | Shadow comparison | Equal to requested quantity; no constraint policy exists |
| Manual shares | Human through API/UI | Transaction writer | Requested/claimed fill quantity at admission |
| Ledger shares | `Transaction` fact | Replay, holdings, evaluation | Actual recorded executed quantity |
| Remaining shares | Transaction writer/replay | Response and next-state holdings | Derived post-event position, not order remainder |
| Quantity-correction delta | Human correction / canonicalizer | Replay | Non-trade ledger adjustment |

### Price ownership today

| Price/value | Current producer | Timestamp evidence | Authority today |
|---|---|---|---|
| `current_price` | Market-data provider/cache | Provider `last_updated`, currently fetch time | Market observation used for analysis; not normalized for execution |
| `avg_cost` | Ledger accounting | No price-observation time | Fee-inclusive historical cost basis, never a market price |
| Optimizer valuation price | `current_price or avg_cost` | Timestamp discarded | Portfolio valuation approximation |
| Decision plan price basis | `avg_cost` | None | Display/planning proxy only |
| M32.2 inferred unit price | gross release ÷ derived quantity | `None` | Shadow balancing value only |
| Modal prefill | Portfolio/watchlist current price | Source timestamp not passed to modal/admission | User convenience only |
| Entered `price_per_share` | Human/API caller | Transaction date + insert time, not observation time | Claimed actual execution term at ledger admission |
| Ledger `price_per_share` | Canonical transaction | Event date and record time | Actual historical execution term |
| FeeQuote unit price | Caller | Quote/effective times only | Exact copy of caller price; FeeQuote never sources price |
| Fee-inclusive effective price | Transaction/replay accounting | Transaction timelines | Cost-basis derivation, not a market or fill price |
| Recommendation price | Frozen scores snapshot | Recommendation time indirectly | Evaluation reference, not current planning price |
| Average fill price | Evaluation from ledger fills | Transaction timelines | Evaluation result, never a planning input |

### Timestamp inventory

The relevant repository timestamps have different meanings and cannot be
substituted for each other:

| Timestamp | Meaning | Gap |
|---|---|---|
| Provider `last_updated` | Time the provider adapter completed/fetched the quote | Not guaranteed to be exchange observation time |
| `MarketDataCache.fetched_at` | Cache write time | Not returned as a first-class price-observation field |
| `MarketDataCache.expires_at` | Cache TTL boundary | Expired data can be served as fallback; staleness metadata is stripped at common call sites |
| Optimizer `analyzed_at` / recommendation time | When analysis/recommendation was recorded | Does not prove when its price was observed |
| `FeeQuote.quoted_at` | When fee quote was assembled | Does not prove price age |
| `FeeQuote.effective_at` | Schedule applicability time | Fee-schedule time, not market-price time |
| `LegacyExecutionTradeRequest.price_timestamp` | Optional caller evidence | M32.2 passes `None` |
| Transaction `transaction_date` | Event/replay date | Date-level execution timing; not quote observation time |
| Transaction `created_at` | Platform knowledge/insert time | Never price time and must not alter replay magnitude |
| Frontend `priceRefreshAt` | Browser receipt time | Presentation timer only; not sent to transaction admission |

No current execution input carries market session. Market-data providers
normalize neither `REGULAR`, `PRE`, `POST`, `CLOSED`, nor `UNKNOWN`, and no
trading-calendar result is attached to a quote.

## 4. Duplicate quantity concepts

There are **nine execution-relevant semantic quantity concepts** represented
across at least twelve fields today:

1. currently held quantity;
2. source-requested trade quantity (manual input; absent for amount-only plans);
3. derived requested quantity (M32.2 shadow SELL only);
4. requested leg quantity;
5. executable/constraint-valid leg quantity;
6. FeeQuote quantity, which must mirror the quantity being quoted;
7. ledger-recorded executed/fill quantity;
8. post-trade remaining holding quantity;
9. signed non-trade correction quantity.

Several example concepts do **not** exist yet:

- there is no canonical rounded quantity;
- there is no lot-adjusted quantity produced by policy;
- there is no funded quantity—only a funded gross amount and release ratio;
- there is no order-level filled quantity versus remaining order quantity;
- there is no partial-fill aggregation contract;
- there is no canonical planned quantity for BUY.

`execution_optimizer.OptimizedTrade.executed_amount` is especially hazardous
terminology: it is a planned gross currency amount, not executed quantity and
not ledger evidence. The normalized contract must not reuse this name for
units.

## 5. Duplicate price concepts and stale-price exposure

The current code has at least eight materially different price meanings:
market quote, previous close, target price, average cost, optimizer valuation
fallback, inferred shadow price, user-entered execution price, and
fee-inclusive effective cost. Only some are valid inputs to execution sizing.

Stale or misleading prices can occur at these boundaries:

1. `fetch_price_info()` accepts a five-minute cache entry without exposing
   cache age to the optimizer.
2. On fetch prohibition/failure it may serve an expired cache value. The
   `_stale_data` and `_cache_age_minutes` annotations are removed from common
   returned payloads, leaving only the old source `last_updated`.
3. Provider adapters stamp `last_updated` with `datetime.now()` after fetching,
   so it is receipt time, not necessarily the venue's trade/quote time.
4. `main.py` drops `last_updated` when building optimizer score input.
5. Optimizer valuation silently falls back to `avg_cost` when price is absent.
6. Decision Workspace intentionally uses `avg_cost` for all plan values.
7. M32.2 constructs a balancing price and sets `price_timestamp=None`.
8. Portfolio UI passes `current_price` into the transaction modal without
   `last_updated`; a modal may remain open while its prefill ages.
9. Manual API clients may submit any positive price and current admission
   records no source, session, or freshness assessment.
10. `FeeQuote.quoted_at` can be current even when `unit_price` is stale, because
    quoting owns fee time, not price time.

The normalized contract must therefore distinguish `observed_at`,
`received_at`, `freshness_assessed_at`, and fee `quoted_at`. A single
`timestamp` field is insufficient.

## 6. Required normalized contract

### 6.1 Contract purpose

`NormalizedTradeInput` is the immutable handoff from source-specific
recommendation/admission adapters to constraint-aware trade-leg construction.
It is neither an order nor a ledger transaction. It preserves what the source
wanted, identifies how units were derived, binds one normalized price, and
retains the established facts/eligibility/fee contracts.

The normalizer returns either a complete `NormalizedTradeInput` or a typed
`TradeNormalizationFailure`. It must never manufacture zero quantity, a free
fee quote, an average-cost market price, or an eligible Registry identity to
avoid failure.

### 6.2 Proposed immutable shape

```text
NormalizedTradeInput (frozen, contract version 1)
  contract_version
  normalization_ref                  deterministic from immutable inputs
  recommendation_reference           optimizer/sizing/decision reference
  requested_symbol
  side                               existing TradeSide

  quantity
    requested_quantity               Decimal; source intent before constraints
    executable_quantity              Decimal; constraint-valid planning units
    requested_value                  optional Decimal; original monetary intent
    quantity_source                  enum
    quantity_confidence              EXACT | DERIVED | ESTIMATED
    lot_adjustment                   reuse/evolve LotAdjustmentSummary
    fractional_adjustment            reuse/evolve FractionalAdjustmentSummary

  price
    unit_price                       Decimal
    price_kind                       MARKET_REFERENCE | USER_EXECUTION_TERM
                                     | RECOMMENDATION_SNAPSHOT
    price_source                     stable provider/adapter identifier
    observed_at                      timezone-aware instant or explicit UNKNOWN
    received_at                      timezone-aware instant
    market_session                   REGULAR | PRE | POST | CLOSED | UNKNOWN
    freshness_assessed_at            caller-supplied deterministic instant
    freshness_limit                  policy identifier/duration
    stale                            boolean
    currency                         listing/price currency

  execution_instrument_facts         existing object, retained by identity
  execution_eligibility              existing object, retained by identity
  fee_quote                          existing FeeQuote, retained by identity

  allocation_source                  enum identifying upstream belief/value source
  portfolio_currency                 portfolio reporting/funding currency
  valuation_currency                 currency of requested_value
  assumptions                        immutable tuple of named assumptions
  warnings                           immutable tuple from established sources/policies
  provenance                         immutable tuple of source evidence
```

Identity and canonical symbol are not copied into independent authoritative
fields. They are read from the retained `ExecutionInstrumentFacts` object.
Convenience properties may expose them, as M32.2 does, but validation must
prove they match facts and no caller may override them.

`FeeQuote.quantity` must equal `quantity.executable_quantity`, and
`FeeQuote.unit_price` must equal `price.unit_price`. This removes the current
possibility that a fee quote describes different units or price than the leg.
If lot/fractional policy changes quantity, the old quote is not reused; a new
quote is obtained for the adjusted quantity before the normalized input is
complete.

`requested_value` preserves the amount implied by belief/allocation. It is not
silently replaced by `quantity × price`. The latter is available from the
retained `FeeQuote.gross_amount`. Their difference is an explicit quantity/
lot implementation residual.

### 6.3 Quantity-source vocabulary

Minimum values:

| Source | Definition | Confidence |
|---|---|---|
| `EXPLICIT_USER_QUANTITY` | Manual BUY/SELL quantity supplied by user/API | `EXACT` as intent, not proof of fill |
| `FULL_HOLDING_QUANTITY` | Full SELL uses replayed held quantity | `EXACT` relative to replay snapshot |
| `ALLOCATION_VALUE_AT_PRICE` | BUY/ACCUMULATE value divided by normalized price | `DERIVED` |
| `REDUCTION_VALUE_AT_PRICE` | SELL/REDUCE value divided by normalized price, capped at held units | `DERIVED` |
| `HOLDING_FRACTION` | Explicit source policy requests a fraction of held units | `DERIVED` |
| `BROKER_ORDER_QUANTITY` | Future approved broker instruction | `EXACT` as instruction |

No source value may be inferred from symbol shape or frontend arithmetic.
`HOLDING_FRACTION` is allowed only when the percentage itself has a named
upstream source; M32.2's reconstructed release ratio remains legacy shadow
provenance until migrated.

### 6.4 Price contract requirements

The existing market-data dictionaries are not sufficient as the canonical
price section. M32.3C should introduce or adapt an immutable price observation
whose value, currency, `asset_id`, observed time, receipt time, provider, and
session are explicit. The normalizer may consume this object and project its
fields, but must not call a provider itself.

Freshness is a deterministic execution-policy judgment over an observation;
it is not a provider opinion. The caller supplies `freshness_assessed_at` and a
versioned policy keyed by venue/session. Pure normalization reads no clock.
`UNKNOWN` session or observation time produces a typed incomplete result for
authoritative planning unless a deliberately approved policy says otherwise.

`avg_cost` is prohibited as `MARKET_REFERENCE`. It may remain visible as an
allocation/legacy valuation assumption, but it cannot make a normalized input
complete or current.

### 6.5 Validation invariants

A complete normalized input must satisfy all of the following:

1. side is BUY or SELL and quantities/prices are positive Decimals;
2. facts and eligibility refer to the requested identity and eligibility is
   explicit;
3. `asset_id`, canonical symbol, listing currency, lot size, and fractional
   support come only from facts;
4. requested and executable quantities have named sources and any difference
   is fully explained by the adjustment summaries;
5. the price has source, currency, observed/received time, session, and a
   reproducible freshness assessment;
6. requested-value currency is explicit;
7. FeeQuote is for the exact side, executable quantity, unit price, currency,
   and effective time represented by the input;
8. an unavailable FeeQuote or non-eligible facts produces a typed incomplete
   normalization result, never a zero-cost complete input;
9. warnings and provenance are append-only source evidence, not inferred
   identity or financial values;
10. normalization is pure after orchestration has batch-loaded facts, prices,
    holdings, and schedule context.

### 6.6 Can one contract satisfy current consumers?

Yes for every **pre-execution** consumer, with source-specific adapters:

- optimizer adapter: target allocation amount + normalized market price;
- Decision Workspace adapter: position-sizing amount + normalized market
  price;
- funding adapter: justified reduction value or full-holding quantity + held
  quantity + normalized market price;
- manual admission adapter: explicit quantity + entered execution term;
- FeeQuote: consumes normalized executable quantity and price;
- ExecutionTradeLeg: consumes the completed normalized input and performs no
  quantity or price invention;
- evaluation: reads a frozen normalized input/plan when available and compares
  quantity, price, fees, and cash separately.

Replay is intentionally not a consumer. Replay consumes ledger facts only.
Likewise, the frontend may display or collect source input but may not construct
the normalized contract or calculate canonical quantities.

## 7. Ownership boundaries

| Concern | Authoritative owner | Normalized-input responsibility | Current conflict/gap |
|---|---|---|---|
| Investment target/value | Belief optimizer or Position Sizing | Preserve requested value and allocation source | Two upstream allocation paths use different NAV bases |
| Explicit manual quantity | Human/API admission source | Preserve as requested quantity with provenance | Currently conflated with an actual fill at write time |
| Derived planning quantity | Execution normalization | Deterministically derive from value, price, holdings, and side | Currently absent for BUY and shadow-only for SELL |
| Current held quantity | Portfolio Runtime / replay | Consume one replay snapshot and timestamp/provenance | `PortfolioItem` is a cache; native `asset_id` coverage remains incomplete |
| Lot size/fractional capability | Asset Registry facts | Consume facts only | Facts exist; policy is absent |
| Lot/fractional policy | Execution Planning | Produce executable quantity and adjustment evidence | M32.2 summaries are no-ops; residual policy undecided |
| Market price observation | Market Data Platform | Consume immutable observation | Current dictionary timestamp is fetch time and session is absent |
| Price freshness | Execution policy over Market Data evidence | Record policy, assessment time, and stale result | No accepted age/session policy |
| Market session/calendar | Market Data Platform | Carry normalized session evidence | No current quote contract supplies it |
| Listing/settlement currency | Asset Registry | Read from facts | Current planners implicitly assume THB |
| Portfolio/base currency | Portfolio Domain | Carry as planning/funding frame | Operational `Portfolio` has no base-currency field |
| Valuation currency | Upstream allocation contract / Portfolio Domain | Preserve currency of requested value | Current allocation amounts have no currency field |
| FX observation | Market Data Platform | Later retain immutable FX evidence | No canonical FX input; out of M32.3A implementation scope |
| FX application | Execution Planning for estimates; Portfolio rules for reporting | Convert only with explicit evidence/policy | Current transaction cash/replay ignore `exchange_rate` |
| Fee schedule and calculation | M32 FeeQuote | Retain existing quote object | Compatibility posting remains for unresolved Registry inputs |
| Funding selection | Execution Planning | Consume normalized net cash effects only | Current selection uses gross monetary candidates |
| Actual fill quantity/price | Transaction ledger | Never source planning input from later fills | Current manual entry jumps directly from UI input to ledger fact |
| Intent lifecycle | M33 Execution Domain | Later reference normalized plan/decision | Not part of M32.3A/M32.3B |
| Frontend | Presentation and explicit human input | Render backend output; submit raw explicit intent | Optimizer derives cash totals and modal derives fees locally |

### Required conflict resolutions

1. A constrained allocation amount is owned upstream; its conversion to units
   is owned only by execution normalization.
2. `avg_cost` remains accounting cost basis and cannot serve as current
   execution price.
3. Market Data owns observations; Execution Planning owns whether an
   observation is fresh enough for a specific planning boundary.
4. Registry owns listing currency; Portfolio owns base currency; Market Data
   owns FX observations; the planner only applies explicit evidence.
5. Lot/fractional facts and lot/fractional policy are separate: Registry
   describes what the listing supports, Execution Planning decides how to
   adjust a requested trade.
6. Ledger fill quantity and price are outcomes. They may grade a plan but can
   never be used to retroactively define what the plan requested.

## 8. Dependency graph

```text
Belief Optimizer / Position Sizing / Manual Admission
        |
        | requested value or explicit requested quantity
        v
Source Adapter -----------------------------+
        |                                    |
        |                                    v
        |                         Portfolio Runtime snapshot
        |                         held quantity + cash evidence
        |                                    |
        v                                    |
Market Data orchestration                    |
price observation + session + times          |
        |                                    |
        +-------------------+----------------+
                            |
                            v
Asset Registry batch -> ExecutionInstrumentFacts
                            |
                            v
                    ExecutionEligibility
                            |
                            v
              Quantity / price normalization
              + lot/fractional policy
              + explicit currency checks
                            |
                            v
                  facts-backed FeeQuote
                            |
                            v
                 NormalizedTradeInput
                            |
                            v
                   ExecutionTradeLeg
                            |
                            v
              net-of-cost funding resolver
                            |
                            v
             canonical ExecutionPlanProjection
                            |
             +--------------+---------------+
             |                              |
             v                              v
        frontend renderer             M33 decision/intent
                                            |
                                            v
                                      broker/manual fill
                                            |
                                            v
                                  canonical Transaction ledger
                                            |
                              replay + evaluation (read only)
```

Database and provider access belongs above the normalization boundary. The
normalizer, FeeQuote arithmetic, trade-leg builder, and funding resolver are
pure. A complete symbol set, holdings snapshot, and price set are batch-loaded
once per run; no per-leg Registry or market-data lookup is permitted.

## 9. Rollout sequence

1. Approve the contract vocabulary and source precedence in this document.
2. Add frozen `NormalizedTradeInput`, price/quantity sub-values, and typed
   normalization failures. Keep every new output private/shadow.
3. Add pure validation proving supplied facts, eligibility, price, quantity,
   and FeeQuote describe the same leg.
4. Add source adapters for explicit manual quantity, full-holding SELL, and
   amount-only optimizer/Decision Workspace inputs. Incomplete price evidence
   must return a typed failure, not a fallback.
5. Add a canonical immutable market-price observation adapter with observed
   time, received time, currency, provider, and session.
6. Add versioned price-freshness policy and shadow telemetry by source,
   session, freshness result, quantity source, and normalization outcome.
7. Add lot/fractional policy and explicit residual behavior; bind a facts-backed
   FeeQuote to the adjusted quantity.
8. Make `ExecutionTradeLegBuilder` consume `NormalizedTradeInput`; retain the
   M32.2 legacy request adapter only for comparison, then retire it.
9. Shadow-project both BUY and SELL legs and compare requested value, gross,
   cost, net cash, and quantity residuals without changing legacy plans.
10. Only after parity and owner decisions, implement net-of-cost canonical
    funding and a frozen backend plan projection.
11. Migrate evaluation and frontend consumers to the frozen projection;
    historical amount-only payloads remain explicitly `LEGACY_RECONSTRUCTED`.

## 10. Risks

| Risk | Consequence | Required control |
|---|---|---|
| Calling gross monetary amount “quantity” | Unit/currency confusion and invalid orders | Typed Decimal quantity/value sections and source enums |
| Value-to-quantity conversion before price normalization | Stale or synthetic units look executable | Require complete normalized price evidence |
| Treating cache TTL as observation freshness | Recently fetched old market data appears current | Separate observed, received, and assessed times |
| Reusing `avg_cost` as price | Arbitrarily old accounting value drives trades | Prohibit it as an execution price kind |
| FeeQuote timestamp mistaken for price timestamp | Current quote time masks stale unit price | Validate separate price and fee times |
| Lot rounding before preserving requested value | Belief is silently mutated | Preserve requested value and adjustment residual |
| Exact monetary funding gap forces fractional units | Invalid quantity invented to close cash exactly | Explicit under/over-funding residual policy |
| Different adapter rules by surface | Competing plans persist | One normalizer and shared source vocabulary |
| Frontend computes canonical units/fees/cash | Backend and UI diverge | Backend-only normalization and static frontend tests |
| Manual input treated as broker-confirmed fill | Estimate becomes ledger fact without provenance | Distinguish user execution term, broker fill, and market quote |
| Float input before Decimal normalization | Avoidable quantity/price drift | Decimal strings at new API boundary; preserve legacy adapters |
| Registry or price lookup in pure helpers | N+1 behavior and nondeterminism | Batch orchestration before normalization |
| Historical evaluation re-derives with new rules | Past plan changes over time | Freeze future projections; label legacy reconstructions |

## 11. Open decisions

The following require owner approval before authoritative normalization:

1. **Portfolio currency scope:** add a real portfolio base currency or limit
   the first authoritative planner to Registry THB listings and THB cash.
2. **Price observation semantics:** identify the canonical market-data field
   for exchange observation time. Current provider `last_updated` is receipt
   time.
3. **Freshness by session:** define allowed age for regular, pre/post, closed,
   and unknown sessions, and whether stale evidence is `INCOMPLETE` or merely
   advisory.
4. **Reference price kind:** decide whether planning uses last trade, bid/ask
   midpoint, close, limit assumption, or a versioned hierarchy by venue.
5. **Slippage ownership:** decide whether execution-risk slippage changes the
   estimated fill price or remains a sensitivity range.
6. **BUY derivation:** approve value ÷ normalized price as requested quantity
   and specify whether estimated fees reduce the quantity budget before or
   after lot adjustment.
7. **REDUCE derivation:** approve target-reduction value ÷ normalized price or
   an explicit holding fraction as the authoritative source when both exist.
8. **Full SELL semantics:** confirm full held quantity is taken from one
   identified replay snapshot and define behavior if state changes before use.
9. **Lot/fractional residual:** choose floor/nearest/ceiling rules by side and
   whether any one-lot overfunding is permitted.
10. **Quantity confidence:** approve the proposed exact/derived/estimated
    vocabulary and client-facing meaning.
11. **Manual transaction semantics:** decide whether entered price is an
    actual fill, a user estimate, or selectable provenance, and whether fills
    need time-of-day.
12. **Cash availability:** choose raw cash, policy-reserved cash, or target-cash
    headroom as the canonical funding input.
13. **Normalization expiry:** decide when a complete normalized input must be
    refreshed/requoted due to price age, holdings change, or schedule change.

None of these decisions should be hidden inside `ExecutionTradeLegBuilder`, a
frontend component, or a compatibility adapter.

## 12. Go / No-Go recommendation

### M32.3B foundation

**GO, with a strict shadow-only scope.** The repository has sufficient
contracts and orchestration boundaries to implement:

- the immutable normalized-input and failure contracts;
- quantity-source/confidence vocabulary;
- pure consistency validation;
- explicit adapters for manual quantities and amount-only recommendation
  sources;
- batch reuse of M31 facts/eligibility and M32.1 FeeQuote;
- telemetry showing which inputs remain incomplete.

M32.3B must not label value-derived quantities executable when normalized
price evidence is absent, must not add a fallback price, and must not alter a
plan or transaction.

### Authoritative quantity or canonical plan

**NO-GO.** The current repository is not ready to make M32.3B quantities
authoritative or proceed directly to canonical cost-aware funding because:

1. BUY sources carry no quantity;
2. normalized price observation/session/freshness does not exist;
3. current price timestamps are discarded or mean receipt time;
4. Decision Workspace uses average cost;
5. portfolio/base and valuation currencies are not authoritative;
6. lot/fractional and residual rules are undecided;
7. cash-floor ownership is undecided;
8. manual input provenance does not distinguish estimate from fill;
9. plan persistence/evaluation still reconstructs amount-only history;
10. frontend and backend still contain competing amount/fee projections.

The additional decisions in §11 are required before any authoritative
implementation approval.

## 13. Suggested implementation split

### M32.3B — Normalized input and quantity-intent foundation

- add immutable contracts and typed failures;
- define quantity/value source and confidence vocabulary;
- add pure cross-contract validation;
- adapt explicit manual quantities, full-holding quantities, and amount-only
  recommendations in shadow;
- do not convert value to authoritative executable quantity without M32.3C
  price evidence;
- no public response or behavior change.

### M32.3C — Canonical price observation and freshness

- add/adapt immutable price evidence keyed by Registry identity;
- preserve observation and receipt times, provider, currency, and session;
- define versioned freshness policy with caller-supplied assessment time;
- remove average-cost and balancing-price eligibility for complete
  normalization;
- shadow-normalize both BUY and SELL.

### M32.3D — Constrained quantity and FeeQuote binding

- implement approved BUY/REDUCE/full-SELL quantity derivation;
- apply Registry-backed lot/fractional policy and holdings caps;
- expose residual value/quantity explicitly;
- obtain FeeQuote for the exact adjusted quantity and price;
- migrate `ExecutionTradeLegBuilder` to consume normalized input;
- remain shadow until parity/coverage thresholds pass.

### M32.3E — Canonical cost-aware execution plan

- resolve net-of-cost funding from normalized legs;
- freeze one backend plan projection;
- retain belief amounts separately from executable legs;
- define partial/incomplete outcomes, quote expiry, rollback, and history
  compatibility;
- migrate evaluation and frontend in later adoption steps.

This ordering puts price normalization before authoritative value-to-quantity
conversion. Implementing “quantity normalization” first as arithmetic would
force M32.3B to choose a price source it does not own.

## 14. Verification and audited files

This audit used read-only source/document tracing. No tests were required to
validate behavior because no executable code changed. The design was checked
against the currently implemented M31/M32 contracts and existing regression
documentation.

### Backend audited

- `backend/agents/optimizer.py`
- `backend/main.py`
- `backend/models/database.py`
- `backend/services/position_sizing.py`
- `backend/services/optimizer/execution_optimizer.py`
- `backend/services/optimizer_action_summary.py`
- `backend/services/execution_plan.py`
- `backend/services/funding_source_analysis.py`
- `backend/services/execution_trade_leg.py`
- `backend/services/broker_fees.py`
- `backend/services/broker_fees_compat.py`
- `backend/services/execution_instrument_facts.py`
- `backend/services/execution_eligibility.py`
- `backend/services/portfolio_transactions.py`
- `backend/services/data_fetcher.py`
- `backend/services/market_data/base.py`
- `backend/services/market_data/provider.py`
- `backend/services/market_data/yahoo.py`
- `backend/services/market_data/yahoo_chart.py`
- `backend/services/transaction_canonicalizer.py`
- `backend/services/portfolio_rebuilder.py`
- `backend/services/replay_key.py`
- `backend/services/replay_cutover.py`
- `backend/services/registry_replay_parity.py`
- `backend/services/evaluation/plan_grader.py`
- `backend/services/evaluation/execution_analyzer.py`
- `backend/services/evaluation/execution_ledger.py`
- `backend/services/decision_memory/shadow_tracker.py`

### Frontend audited

- `frontend/lib/api.ts`
- `frontend/lib/executionPlan.ts`
- `frontend/app/optimizer/page.tsx`
- `frontend/app/portfolio/page.tsx`
- `frontend/components/optimizer/ExecutionPlanCard.tsx`
- `frontend/components/operations-center/decision-workspace/DecisionWorkspace.tsx`
- `frontend/components/TransactionModal.tsx`

### Documentation audited

- `docs/implementation/M31_4_execution_cutover_readiness.md`
- `docs/implementation/M31_5_registry_cutover_preparation.md`
- `docs/implementation/M31_6_registry_remediation_wave1.md`
- `docs/implementation/M32_cost_aware_execution_planning_design.md`
- `docs/implementation/M32_1_fee_quote_foundation.md`
- `docs/implementation/M32_2_trade_leg_foundation.md`
- `docs/architecture/ASSET_REGISTRY.md`
- `docs/architecture/EXECUTION_DOMAIN.md`
- `docs/architecture/MARKET_DATA_PLATFORM.md`
- `docs/architecture/PORTFOLIO_DOMAIN_MODEL.md`
- `docs/architecture/TRANSACTION_DOMAIN_MODEL.md`
- `docs/investment/OPTIMIZER_PHILOSOPHY.md`
- `docs/investment/PORTFOLIO_CALCULATION_RULES.md`
- `docs/decisions/ADR-001_TRANSACTION_LEDGER_SINGLE_SOURCE_OF_TRUTH.md`
- `docs/decisions/ADR-003_TWO_TIMELINE_RULE.md`
- `docs/decisions/ADR-004_ONE_IMPLEMENTATION_PER_RULE.md`
- `docs/engineering/DECISION_LOG.md`

### Audit conclusion

The normalized-input boundary is implementable without changing belief,
funding, ledger, or frontend behavior. Its safe next step is contract-first and
shadow-only. The repository is not yet ready for authoritative unit sizing or
canonical planning; the concrete blockers and required owner decisions are
listed in §§10–12.
