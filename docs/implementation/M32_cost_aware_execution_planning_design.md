# M32 — Cost-aware Execution Planning Audit and Technical Design

**Audit date:** 2026-07-14

**Decision:** **GO for staged foundation and shadow implementation; NO-GO for canonical cutover today**

**Scope:** Audit and technical design only. No production code, migration, API behavior, frontend behavior, database data, execution-eligibility mode, fee, allocation, funding result, or ledger rule was changed.

M31 remains in `LEGACY_FALLBACK`. M32 does not require `FACTS_ONLY_SHADOW` or `ENFORCE` and must not activate either mode.

## 1. Executive summary

The repository has one sound low-level fee formula and one shared funding-selection algorithm, but it does not have one canonical execution plan.

The actual BUY/SELL write path is already net-of-fees: `portfolio_transactions.py` uses `broker_fees.calc_fees()` and stores BUY `total_amount = gross + costs` and SELL `total_amount = gross - costs`. Planning does not use that implementation. All planning surfaces work in gross monetary approximations, omit commissions and VAT, have no executable quantities, do not apply lot/fractional constraints, and do not expose price freshness or currency conversion evidence.

There are four plan projections in active use:

1. the optimizer response's `execution_optimization` projection;
2. the optimizer frontend's independently derived `ExecutionPlan` and cash totals;
3. the Decision Workspace's backend `ExecutionPlanResult`/`FundingSourceResult`;
4. AI Evaluation's reconstructed day-0 plan.

They share some inputs and delegate discretionary funding selection to `resolve_funding_gap()`, but they are not the same object. The optimizer path uses target-allocation deltas based on current prices with an average-cost fallback. The Decision Workspace uses client-supplied sizing percentages and values every holding at average cost. The frontend re-sums the optimizer's gross amounts. Evaluation reconstructs the response-time projection from stored target allocations under the current code version.

The principal correctness risks are:

- buy requirements omit all estimated costs;
- sell funding treats gross position value as spendable proceeds;
- the plan can report non-negative remaining cash and the posted trades can still drive cash negative;
- currency and `exchange_rate` are stored on transactions but ignored by cash mutation and replay;
- the portfolio schema has no base-currency field even though architecture documents require one;
- no plan carries quantities, price timestamps, quote versions, fee schedule versions, or FX evidence;
- automatic fee-profile selection uses a DR regex and defaults every other symbol—including unknown and foreign instruments—to SET;
- `register_profile()` changes the name registry but does not change what `resolve_fee_profile()` returns for built-in profiles;
- the administrative recalculation endpoint can rewrite historical transaction fees using today's unversioned schedule;
- execution evaluation compares planned gross-like amounts with ledger net amounts, so fees can be misreported as size deviation.

The target architecture is one backend-owned, immutable projection:

```text
Investment belief / target allocation (unchanged)
                    |
                    v
Execution assessment (necessity, risk, eligibility metadata)
                    |
                    v
Trade-leg sizing (price + FX + lot/fractional constraints)
                    |
                    v
FeeQuote for every active leg
                    |
                    v
Net-of-cost funding resolution
                    |
                    v
Canonical ExecutionPlan projection
```

The frontend renders this projection and performs no trade or cash arithmetic. The transaction writer and planner share one pure fee calculator, but a planning quote remains an estimate and is never rewritten when a later fill produces different ledger facts.

Implementation should begin with the FeeQuote foundation and parity adapters. Canonical plan cutover must wait for explicit currency ownership, price-freshness policy, Registry-backed schedule coverage, and shadow comparison evidence.

## 2. Current-state dependency and data-flow map

### 2.1 Optimizer path

```text
main.py:2049-2083
  fetch_price_info(symbol) -> current_price (last_updated is discarded)
  scores_map
      |
      +-> execution_instrument_facts.resolve_execution_instruments()
      |      -> execution_penalty.py risk/slippage metadata
      |
      v
agents/optimizer.py:1498-1504
  holding value = shares * (current_price or avg_cost)
  total_value = equity + cash
  estimated_amount = allocation_delta_pct * total_value
      |
      v
main.py:2567-2588
  build_action_summary()
  optimize_execution()
      |
      +-> execution_optimizer.resolve_funding_gap()
      |      gross buy deployment and gross sell release
      |
      v
Optimizer response: target_allocations + execution_optimization
      |
      +-> frontend/lib/executionPlan.ts::deriveExecutionPlan()
      |      re-joins and re-sums trade cash impacts
      |
      +-> evaluation/plan_grader.py::derive_full_plan()
             later reconstructs the projection from stored inputs
```

Exact orchestration call sites:

- `backend/main.py:2110-2120` batch-resolves M31 facts and computes execution-risk context.
- `backend/main.py:2568-2571` creates the response-time action summary.
- `backend/main.py:2579-2586` creates `execution_optimization`.
- `backend/main.py:2696-2705` re-creates missing history projections with current code.
- `frontend/components/optimizer/ExecutionPlanCard.tsx:209-222` derives the UI plan and locally calculates remaining cash.
- `backend/services/evaluation/plan_grader.py:184-211` reconstructs the day-0 plan for grading.
- `backend/services/evaluation/execution_analyzer.py:85-102` reconstructs it again through the grader's shared helper for plan-versus-actual analysis.

### 2.2 Decision Workspace path

```text
DecisionWorkspace.tsx:1308-1362
  review -> client timing gate -> allocation -> sizing -> risk budget
      |
      v
POST /portfolios/{id}/execution-plan
  client supplies buy_symbols, sizing_suggestions, timing_scores
      |
      v
execution_plan.py
  portfolio value = cash + sum(shares * avg_cost)
  buys = suggested_pct * portfolio value
  funding candidates = SELL full avg-cost value / REDUCE 25%
      |
      v
funding_source_analysis.py
  -> execution_optimizer.resolve_funding_gap()
      |
      v
ExecutionPlanResult + duplicate FundingSourceResult/CashSummary views
      |
      v
DecisionWorkspace FundingFlowCard
```

Exact call sites:

- `backend/main.py:6371-6405` defines the open request and response boundary.
- `backend/services/execution_plan.py:122-128` values holdings at average cost.
- `backend/services/execution_plan.py:160-175` calculates gross buy deployment.
- `backend/services/execution_plan.py:181-223` delegates funding selection and recomputes cash totals.
- `backend/services/funding_source_analysis.py:96-116` builds gross monetary candidates.
- `frontend/components/operations-center/decision-workspace/DecisionWorkspace.tsx:1353-1362` requests the plan.
- `DecisionWorkspace.tsx:680-887` renders the funding flow using backend totals.
- `DecisionWorkspace.tsx:893-935` retains a legacy cash-summary fallback.

### 2.3 Ledger path

```text
BUY/SELL API -> portfolio_transactions.py
  gross = Decimal(quantity) * Decimal(fill price)
  profile = explicit override or resolve_fee_profile(symbol)
  FeeBreakdown = calc_fees(gross, profile)
  BUY cash delta  = -(gross + fees + VAT)
  SELL cash delta = +(gross - fees - VAT)
  Transaction.total_amount stores the absolute net cash effect
  Transaction.fees stores pre-VAT costs
  Transaction.taxes stores VAT
      |
      v
portfolio_rebuilder.py replay consumes total_amount directly
```

Exact call sites:

- `backend/services/portfolio_transactions.py:269-346` BUY quote, cash mutation, and persistence.
- `backend/services/portfolio_transactions.py:397-467` SELL quote, cash mutation, and persistence.
- `backend/services/portfolio_rebuilder.py:373-405` replays net BUY/SELL `total_amount` without recalculating fees.
- `backend/main.py:4792-4803` independently reconciles ledger cash from the same net `total_amount` convention.
- `backend/main.py:4546-4692` is a privileged historical fee/cost-basis recalculation path.

## 3. Complete fee-calculation inventory

### 3.1 Authoritative implementation today

`backend/services/broker_fees.py` contains the only production fee formula:

```text
gross          = quantity * unit_price
commission     = round_4(gross * commission_rate)
trading_fee    = round_4(gross * trading_fee_rate)
clearing_fee   = round_4(gross * clearing_fee_rate)
pre_vat_cost   = commission + trading_fee + clearing_fee
VAT            = round_4(pre_vat_cost * vat_rate)
total_cost     = pre_vat_cost + VAT
BUY cash out   = gross + total_cost
SELL cash in   = gross - total_cost
```

For a gross amount of 10,000, the current runtime produces commission 15.0000, trading fee 0.6000, clearing fee 0.1000, VAT 1.0990, and total cost 16.7990.

`SET_STANDARD` and `DR_STANDARD` both use:

- commission: 0.15%;
- trading fee: 0.006%;
- clearing fee: 0.001%;
- VAT: 7% of the three-component subtotal.

`FREE` sets every rate to zero. There is no minimum commission, maximum commission, tier, side-specific rate, stamp duty, withholding rule, account override, effective-date lookup, or version field.

Each component is rounded to four decimal places with `ROUND_HALF_UP`; transaction helpers then round stored floats to six decimal places. Plan monetary values are rounded differently—whole units in the optimizer and two decimals in the Decision Workspace.

### 3.2 Call-site inventory

| Function / call site | Purpose | Profile selection | Persists? |
|---|---|---|---|
| `broker_fees.calc_fees()` at `broker_fees.py:139-175` | Pure component arithmetic | Explicit profile or default SET | No |
| `portfolio_transactions.execute_buy()` at `:273-321` | Posting-time BUY costs, cash, and cost basis | Explicit service argument or automatic symbol resolver | Yes |
| `portfolio_transactions.execute_sell()` at `:407-444` | Posting-time SELL costs, proceeds, and P&L | Explicit service argument or automatic symbol resolver | Yes |
| `main.admin_recalculate_cost_basis()` at `:4599-4664` | Re-split historical fees and rebuild cost basis/P&L | Automatic symbol resolver using current process state | Yes unless dry-run |
| Tests and one-off probes | Formula/parity validation | Explicit and automatic | Test-only |

No planning module calls `calc_fees()` today.

### 3.3 Profile-selection audit

`resolve_fee_profile(symbol)` at `broker_fees.py:125-136` uses exactly one classifier:

- regex `^[A-Z]+\d{2}\.BK$` -> `DR_STANDARD`;
- everything else -> `SET_STANDARD`.

The comments describe `.BK` and non-Thai handling, but the implementation has no venue, market, or currency branch. Unknown symbols, US symbols, ETFs, ambiguous identities, and Registry failures all optimistically receive SET fees. Side is ignored. Broker and account do not exist in the operational schema. `ExecutionInstrumentFacts` is not consumed.

`register_profile()` and automatic resolution are behaviorally inconsistent. Registration writes `_PROFILES[profile.name]`, and `get_profile()` sees the replacement. Automatic resolution returns the module constants `DR_STANDARD`/`SET_STANDARD`, not `_PROFILES[name]`. A runtime probe replacing `DR_STANDARD` confirmed `get_profile("DR_STANDARD")` returned the replacement while `resolve_fee_profile("NVDA01.BK")` did not. Registering a new profile also provides no mapping that could make automatic resolution select it.

### 3.4 Estimate versus actual today

The system has no separate estimate and actual cost concepts:

- planning carries no fee estimate;
- manual BUY/SELL input does not accept actual fee components;
- the writer calculates fees from entered quantity/price and persists them as ledger facts;
- `Transaction.fees` and `Transaction.taxes` carry neither schedule/version nor whether the values came from a broker confirmation or a platform calculation;
- the transaction result exposes `fee_profile` and `fee_breakdown`, but frontend `TransactionResult` does not type those fields and the modal displays only `fees`, not `taxes`.

The administrative recalculation endpoint is especially risky: it rewrites historical immutable ledger rows with the current unversioned schedule. It predates the current ADR language, but a versioned M32 design must not extend this pattern.

## 4. Complete funding-arithmetic inventory

### 4.1 Optimizer execution projection

`agents/optimizer.py` values each holding as:

```text
holding_value = shares * (current_price or avg_cost or 0)
total_value   = sum(holding_value) + cash_balance
trade_amount  = round((target_weight - current_weight) / 100 * total_value)
```

`execution_optimizer.optimize_execution()` then calculates:

```text
gross_buy_deployment = sum(abs(estimated_amount) for actionable BUY/ACCUMULATE)
candidate_release    = abs(estimated_amount) for actionable SELL/REDUCE
initial_gap          = max(0, gross_buy_deployment - cash_available)
idle_cash_after      = cash_available + selected_gross_releases - gross_buy_deployment
```

Necessary SELL and policy REDUCE trades execute in full. Discretionary candidates are sorted by full monetary amount, then REDUCE-before-SELL, then symbol. Full candidates are consumed until the first overshoot, which is scaled to the exact remaining monetary gap. Later candidates are deferred. This guarantees deterministic gross arithmetic and at most one scaled monetary candidate; it does not guarantee an executable share quantity.

The full `cash_balance` is available. The target cash weight/cash floor is not subtracted here despite the philosophy's “available above the required cash floor” wording.

### 4.2 Decision Workspace plan

`execution_plan.py` uses a different basis:

```text
holding_value = shares * avg_cost
total_value   = cash_balance + sum(holding_value)
buy_amount    = round(suggested_pct / 100 * total_value, 2)
SELL release  = full holding_value
REDUCE release = holding_value * 25% unless an override is supplied
```

`execution_plan.py` never passes a REDUCE override, so 25% is the active rule. It delegates selection to the same `resolve_funding_gap()` implementation, then computes:

```text
cash_released    = selected gross monetary releases
total_deployable = cash_before + cash_released
cash_remaining   = total_deployable - gross buy deployment
```

Negative cash is surfaced as `INSUFFICIENT`, not prevented. A scaled funding action has a monetary release percentage but no rounded sell quantity. Buy actions contain no quantity or price.

### 4.3 Partial funding, lot, rounding, and price assumptions

- Partial funding is monetary: the selected source is cut to an exact currency amount.
- BUY quantities are absent.
- SELL quantities are not calculated from release amount; only current shares and a percentage are displayed.
- Registry `fractional_support` and `lot_size` are available in `ExecutionInstrumentFacts` but unused.
- The optimizer rounds allocation amounts to whole currency units; execution optimization and Decision Workspace round to two decimals; transaction storage rounds to six decimals.
- Optimizer valuation prefers a fetched current price but falls back silently to average cost.
- `main.py` discards the price result's `last_updated` before the optimizer receives it.
- Decision Workspace uses average cost for both NAV proxy and funding value and explicitly displays “no live prices.”
- `execution_penalty.py` produces a slippage percentage, but no planner applies it to a price or cash total.

### 4.4 Currency and FX

Current planning implicitly treats every number as one currency. The execution-plan UI formats every amount as Thai baht.

Transactions accept `currency` and `exchange_rate`, but BUY/SELL cash mutation uses the unconverted numeric `total_amount`; replay also ignores both fields. `_tx_row()` defaults missing currency/rate to THB/1.0. There is no `Portfolio.base_currency` column, despite `PORTFOLIO_DOMAIN_MODEL.md` declaring that every portfolio owns a base currency. Consequently, a foreign-currency amount can be mixed into the scalar cash balance without conversion.

M32 must expose this instead of attempting to repair ledger accounting inside planning. Until base-currency and canonical FX ownership are implemented, a canonical plan may be READY only when every active leg and cash bucket share the explicitly supplied planning currency. A different currency or missing FX must produce an explicit incomplete status, never a 1.0 default.

## 5. Duplicate execution-plan surface comparison

| Surface | Producer | Inputs / price basis | Output | Fee-aware? | Current authority |
|---|---|---|---|---|---|
| Optimizer target allocation | `agents/optimizer.py` | Target delta x NAV; current price with avg-cost fallback | `TargetAllocation.estimated_amount` | No | Belief/constrained-allocation amount, not an executable plan |
| Optimizer funding projection | `execution_optimizer.py` via `main.py` | Action summary, target amounts, full cash balance | `ExecutionOptimizationResult` | No | Funding-selection logic for optimizer response |
| Optimizer UI plan | `frontend/lib/executionPlan.ts` | Action summary + allocations + optimizer projection | Local `ExecutionPlan`, local cash totals | No | What optimizer users see today |
| Decision Workspace plan | `execution_plan.py` + `funding_source_analysis.py` | Client sizing percentages; average-cost NAV/holdings | `ExecutionPlanResult`, `FundingSourceResult`, `CashSummary` | No | What Decision Workspace users see today |
| Evaluation day-0 plan | `evaluation/plan_grader.py` | Stored allocations and cash, reconstructed with current code | `derive_full_plan()` dict | No | What plan grading and execution analytics call “the plan” |
| Ledger cash effect | `portfolio_transactions.py` | Entered fill quantity/price | Transaction net amount and fee/tax components | Yes | Accounting truth after write |

There is no single current plan authority. `resolve_funding_gap()` is the shared authority for which gross SELL/REDUCE candidates execute, but its callers supply different candidate and purchase amounts. The Decision Workspace backend object is more structured than the optimizer object, but its average-cost pricing and client-supplied sizing make it unsuitable as the canonical base without redesign.

The portfolio-construction simulation in `DecisionWorkspace.tsx` is a belief/allocation preview, not an execution plan. It should remain visibly labeled as such and must not become another source of executable cash totals.

The canonical future surface should be a backend `ExecutionPlanProjection` produced from a normalized source recommendation/target-allocation input. Both optimizer and Decision Workspace should call it. Evaluation should read the frozen projection when present. The frontend should render it, not derive it.

## 6. Identified correctness risks

| Risk | Evidence | Consequence |
|---|---|---|
| Gross buys treated as total cash required | All three planners sum `estimated_amount`; none calls `calc_fees()` | Posted BUY can consume more cash than planned |
| Gross sells treated as released cash | Funding candidates use target/avg-cost amounts | Available funding is overstated by sell costs |
| Optimistic default fee jurisdiction | `resolve_fee_profile()` returns SET for every non-regex match | Unknown/foreign instruments receive invented cost assumptions |
| Registry-bypassing DR heuristic | `broker_fees.py:111-135` | M31 authoritative DR identity is ignored |
| Profile registry does not control resolver | Resolver returns constants | Runtime replacement appears successful but is not selected automatically |
| No schedule version/effective date | `FeeProfile` is rate-only | Historical quotes cannot be reproduced safely |
| Historical fee rewrite | `main.py:4546-4692` | Current schedules can overwrite immutable historical facts |
| Competing plan objects | Section 5 | Surfaces can disagree while each looks internally plausible |
| Different valuation bases | Optimizer current/avg-cost fallback vs Decision avg cost | The same portfolio produces different deployment/funding numbers |
| No quantity/lot rounding | Plans carry money only | “Ready” plans may not map to valid orders |
| No price timestamp | `last_updated` discarded; Decision uses avg cost | Stale estimates look current |
| Slippage metadata disconnected | `execution_penalty.py` only annotates | Displayed execution risk does not affect expected fill/cash |
| Currency fields are metadata-only | Transaction cash/replay ignore rate | Numeric amounts in different currencies can be silently mixed |
| No portfolio base currency in schema | `Portfolio` has only scalar cash | Canonical translation frame is absent |
| Full cash balance used | Funding ignores cash target/floor | Plan can spend policy-reserved cash |
| Evaluation compares unlike amounts | `execution_analyzer.py:148-163` compares ledger net `total_amount` to gross-like plan amount | Fees appear as execution-size error |
| History reconstruction is code-version dependent | `main.py:2684-2707`, `plan_grader.py:127-205` | A historical “day-0 plan” can change when algorithms change |
| Open client plan inputs | `ExecutionPlanRequest` accepts raw suggestions | No durable linkage proves which recommendation was planned |
| Float boundary | Models/API use float although fee core uses Decimal | Cross-surface rounding drift is possible |

## 7. Proposed `FeeQuote` contract

### 7.1 Value object

Use an immutable backend value object and decimal-string JSON serialization for monetary fields. `quote_ref` is a deterministic hash of normalized quote inputs and schedule version; it is not a database identity.

```text
FeeQuote
  contract_version: "fee-quote.v1"
  quote_ref: string
  status: QUOTED | UNAVAILABLE

  account_context:
    broker_account_id: optional opaque id
    broker_code: optional
  listing:
    asset_id
    canonical_symbol
    market
    exchange
    instrument_form
    settlement_currency
  side: BUY | SELL
  quantity: Decimal
  unit_price: Money
  gross_amount: Money

  costs:
    commission: Money
    venue_fees: Money
    clearing_fees: Money
    taxes: Money
    other_costs: Money
    total_cost: Money
  net_cash_effect: Money   # signed: BUY negative, SELL positive

  schedule:
    schedule_id
    schedule_version
    effective_from
  quoted_at
  price_observed_at
  confidence: HIGH | MEDIUM | LOW
  warnings[]
  provenance[]
```

For `UNAVAILABLE`, monetary outputs are absent—not zero—and the result carries a typed reason such as `IDENTITY_UNKNOWN`, `IDENTITY_AMBIGUOUS`, `NOT_TRADABLE`, `REGISTRY_FAILURE`, `MISSING_FEE_SCHEDULE`, or `MISSING_ACCOUNT_CONTEXT`.

### 7.2 Selection and calculation ownership

Split two responsibilities:

1. `FeeScheduleSelector` selects an immutable schedule from account context plus Registry facts, side, and effective time.
2. `quote_fees(schedule, quantity, unit_price, ...)` is the one pure arithmetic implementation used by planning and transaction posting.

Selection precedence should be explicit data, not code branches:

```text
account-specific schedule
  -> broker + venue + currency + form + side schedule
  -> venue + currency + form + side schedule
  -> no quote
```

There is no fallback by symbol. A resolved Registry DR may select a DR schedule only because its `ExecutionInstrumentFacts.instrument_form` came from `DEPOSITARY_RECEIPT_OF`. A schedule may intentionally share rates with another schedule while retaining its own ID/version.

M32.1 should wrap the current `FeeProfile` rates as versioned in-memory schedules first, preserving current SET arithmetic exactly. Broker-account persistence does not exist yet, so account context is nullable and must not be fabricated.

### 7.3 Pure formula guarantees

- `gross_amount = quantity * unit_price` in the listing settlement currency.
- Every component and its rounding rule belongs to the selected schedule version.
- `total_cost = sum(all cost components)`.
- BUY `net_cash_effect = -(gross_amount + total_cost)`.
- SELL `net_cash_effect = gross_amount - total_cost`.
- No consumer reimplements these equations.
- Slippage/market impact is not a broker fee. It is represented by the leg's reference price versus estimated fill price; fees are quoted on the estimated fill gross.

## 8. Proposed `ExecutionTradeLeg` contract

```text
ExecutionTradeLeg
  leg_ref
  source_allocation_ref / source_symbol
  requested_symbol
  asset_id / canonical_symbol
  resolution_status / instrument_form / Registry execution_role

  recommendation_action: BUY | ACCUMULATE | REDUCE | SELL
  side: BUY | SELL
  reason
  necessity
  funding_role: STANDALONE | FUNDING_SOURCE | NOT_NEEDED_TODAY
  execution_state: FULL | SCALED | DEFERRED | EXCLUDED

  target_amount: Money              # unchanged belief-side delta/reference
  requested_quantity: optional Decimal
  planned_quantity: optional Decimal
  quantity_adjustment:
    fractional_support
    lot_size
    rounding_mode
    quantity_delta
    amount_delta

  price:
    reference_price: Money
    estimated_fill_price: Money
    basis: LIVE_QUOTE | RECOMMENDATION_SNAPSHOT | LIMIT_ASSUMPTION
    observed_at
    source
    freshness_status
  gross_amount: Money
  fee_quote: FeeQuote | UnavailableFeeQuote
  net_cash_effect: Money | null

  fx_quote: optional FxQuote
  base_currency_cash_effect: Money | null
  eligibility: typed M31 assessment metadata
  warnings[]
  provenance[]
```

`target_amount` records what the target allocation implied and is never changed. `planned_quantity` is the cost/lot-constrained execution projection. Their difference is implementation shortfall, not a mutation of belief.

BUY sizing must solve for the largest valid quantity whose net BUY cash requirement does not exceed the leg budget. The algorithm must quote after rounding and decrement by one lot/unit until the net amount fits; a proportional-rate shortcut is not safe once minimums or tiers exist.

SELL sizing must convert the independently justified target reduction into a valid quantity, cap it at holdings, quote its net proceeds, and then use net—not gross—proceeds in funding. A scaled funding leg may miss or overshoot the requested monetary gap by one valid lot. That rounding residual is explicit; the planner must never invent a fractional share to close the arithmetic exactly.

## 9. Proposed canonical `ExecutionPlan` projection

```text
ExecutionPlanProjection
  contract_version: "execution-plan.v1"
  calculator_version
  plan_ref
  source:
    source_kind
    recommendation_snapshot_id / optimizer_history_id / request_ref
    target_allocations_hash
  generated_at
  as_of
  base_currency

  trade_legs[]                 # active, deferred, excluded all in one typed list
  funding_actions[]            # references SELL legs; no duplicate money objects
  deferred_actions[]           # leg references
  excluded_actions[]           # leg references + reason

  totals_by_currency[]
  totals_base_currency:
    gross_buys
    gross_sells
    estimated_costs
    buy_cash_required
    sell_cash_released
    cash_before
    funding_gap_before_discretionary_sales
    net_cash_requirement_after_plan
    cash_after

  price_status
  fx_status
  eligibility_status
  plan_status
  warnings[]
  provenance[]
```

The projection is immutable plain data. M32 introduces no approval, order, fill, lifecycle, or `ExecutionIntent` model.

### 9.1 Arithmetic invariants

For active legs translated into the plan base currency:

```text
estimated_costs    = sum(active leg fee_quote.total_cost)
buy_cash_required  = sum(-BUY leg net_cash_effect)
sell_cash_released = sum( SELL leg net_cash_effect)
cash_after         = cash_before + sell_cash_released - buy_cash_required
net_cash_requirement_after_plan
                   = max(0, buy_cash_required - cash_before - sell_cash_released)
```

`funding_gap_before_discretionary_sales` is computed after active necessary/standalone sales, because those trades happen for their own reason and their net proceeds are a side effect. Funding-source selection then closes only that net gap.

Every displayed total is serialized from these backend fields. No frontend sum is authoritative. Plan construction asserts the identities above within the currency's declared minor-unit tolerance before returning.

### 9.2 Statuses

Use orthogonal axes rather than overloading funding status:

- `plan_status`: `NO_TRADES`, `READY`, `PARTIAL`, `INSUFFICIENT_CASH`, `INCOMPLETE`;
- `price_status`: `CURRENT`, `STALE`, `MISSING`;
- `fx_status`: `NOT_REQUIRED`, `COMPLETE`, `MISSING`;
- `eligibility_status`: `ELIGIBLE`, `MIXED`, `UNRESOLVED`.

A plan cannot be `READY` if an active leg lacks price, FX, a FeeQuote, valid quantity, or a resolved tradable listing. This is a truthfulness rule for the projection, not M31 transaction-admission enforcement.

## 10. Ownership and dependency boundaries

| Owner | Owns | Must not own |
|---|---|---|
| Asset Registry / M31 facts | Identity, form, market, exchange, currency, tradability, lot/fractional facts | Fee rates, funding choices, investment reason |
| Fee quoting / M32 | Schedule selection and one pure cost calculation | Asset inference, ledger facts, price sourcing |
| Execution planning / M32 | Leg sizing, cost-aware cash effects, funding resolution, immutable projection | Target-weight mutation, approval, orders, fills |
| Belief/optimizer | Scores, reasons, ideal/constrained target allocations | Fee arithmetic, frontend cash reconstruction |
| Market Data Platform | Price and FX observations with timestamps/provenance | Trade sizing or fee schedules |
| Portfolio/ledger | Actual transaction facts, replayed cash/holdings, accounting rules | Planned estimates or execution intent |
| Execution Domain / M33 | Decision, approval, intent, lifecycle, ledger linkage | Accounting truth or plan calculation |
| Frontend | Rendering and user interaction | Independent plan, fee, funding, FX, or lot arithmetic |

The canonical planner is a pure domain service once orchestration has batch-loaded facts, prices, FX, cash/holdings, and schedule context. Pure sizing, quoting, and funding helpers perform no ORM or network calls.

## 11. M31 integration strategy

1. Batch-resolve the union of all candidate BUY/SELL symbols once at a session-owning orchestration boundary.
2. Pass `ExecutionInstrumentFacts` into schedule selection and leg construction; never resolve inside pure functions.
3. Use `asset_id`, market, exchange, currency, form, tradability, fractional support, and lot size directly.
4. Never consume `execution_penalty.py`'s legacy-shaped `asset_type` as fee identity. Its slippage/risk judgment may annotate a leg, but it cannot select a schedule.
5. `UNKNOWN`, `AMBIGUOUS`, `NOT_TRADABLE`, `REFERENCE`, and `REGISTRY_FAILURE` produce an unavailable quote and an incomplete/excluded leg with typed provenance. They never receive SET or zero fees.
6. Keep M31's global mode at `LEGACY_FALLBACK`. M32 quoteability does not block optimizer belief generation or transaction writes while canonical planning is shadowed.
7. When a legacy surface must remain visible during rollout, compute it independently as today and compare it with the canonical shadow result. Do not backfill M31 facts from the legacy fee regex.

This design is compatible with deferred M31 enforcement: unresolved instruments may continue through current legacy behavior while the new plan is shadow-only, but the new plan refuses to label an invented quote “estimated.” Canonical adoption for a workflow waits until its supported symbols have facts and schedules.

## 12. Ledger estimate-versus-actual boundary

Planning and ledger posting share calculation law, not an object identity:

```text
Planning time:
  reference/estimated fill inputs -> FeeQuote(estimate) -> immutable plan leg

Fill/entry time:
  actual quantity + actual price + effective schedule
      -> same pure fee calculator
      -> new posting-time breakdown
      -> Transaction.fees / Transaction.taxes / net total_amount
```

Rules:

1. A later fill never updates the original `FeeQuote` or plan totals.
2. Actual ledger facts never derive intent; they may be linked to it later by M33.
3. Planning never rewrites transactions, holdings, cash, snapshots, or cost basis.
4. Replay continues to consume persisted net transaction amounts, not plans or quotes.
5. If broker evidence supplies actual fees that differ from the calculated estimate, the admitted ledger fact wins. The estimate remains available for execution-quality comparison.
6. Cost variance is measured explicitly: estimated fee versus actual fee, reference price versus fill price, planned quantity versus fill quantity. These dimensions must not be collapsed into one “size delta.”

The current schema can continue storing actual pre-VAT fees and VAT without a migration. It cannot record schedule/version, calculation-versus-broker provenance, or the original plan quote. M32 should not invent those as ledger columns in this milestone. Owner approval is required on whether actual-fee provenance belongs in a future canonical transaction envelope, broker-import provenance, or M33 linkage.

`POST /admin/recalculate-cost-basis` must not become the mechanism for schedule changes. Before versioned schedules are used beyond parity, this endpoint needs a separate ledger-governance decision: disable historical fee rewrites, restrict it to a named legacy repair window with preserved evidence, or replace mutations with append-only repair semantics.

## 13. API compatibility impact

### Additive transition

- Add `execution_plan_projection` to live optimizer and history-detail payloads while retaining `target_allocations`, `action_summary`, and `execution_optimization` for one migration window.
- Store the frozen projection in the existing optimizer history JSON before commit, or store sufficient frozen inputs plus the exact calculator/schedule versions. The preferred option is the projection itself because evaluation must grade what the user actually saw. This is JSON payload evolution, not an ORM model or lifecycle object.
- Add a versioned canonical projection to the existing execution-plan response while retaining `funding_actions`, `buy_actions`, `cash_summary`, and `funding_breakdown` as legacy adapters.
- Successful transaction response shapes remain unchanged during M32.1 parity adoption. Add typed cost detail only additively.
- Use decimal strings for new monetary contracts. Existing numeric legacy fields remain numbers until retirement.

### Semantic clarifications

- `TargetAllocation.estimated_amount` remains a gross belief/allocation delta and must not be relabeled as executable cash.
- Canonical `net_cash_effect` has one signed convention; legacy `estimated_amount`, `estimated_release`, and `total_amount` conventions remain documented at adapters.
- `AssetType` frontend vocabulary is not a fee schedule key.
- Evaluation should compare canonical quantity/gross/cost fields to ledger fields separately. Historical payloads without a canonical plan continue through the existing reconstruction adapter and are marked `LEGACY_RECONSTRUCTED`.

## 14. Frontend migration plan

1. Add TypeScript types mirroring `FeeQuote`, `ExecutionTradeLeg`, and `ExecutionPlanProjection`; use a decimal parser/formatter at the display boundary only.
2. Build one shared `CanonicalExecutionPlan` renderer used by optimizer and Decision Workspace.
3. In shadow mode, keep existing UI output and capture backend comparison telemetry; do not calculate canonical totals in the browser.
4. Switch the optimizer card from `deriveExecutionPlan()` to the backend projection. Retain `frontend/lib/executionPlan.ts` only as a legacy-history adapter, then delete its cash arithmetic.
5. Switch Decision Workspace from the duplicated `FundingSourceResult`/`CashSummary` display to canonical legs and totals. Retain `LegacyCashSummary` only for old responses, then retire it.
6. Label allocation-table `estimated_amount` as a gross target-allocation delta so it is not confused with the net plan.
7. Render price time/freshness, native/base currency, estimated costs, lot adjustments, excluded/deferred reasons, and plan status directly from backend fields.
8. Update `TransactionModal` to display taxes and total costs from backend response if supplied; never sum fee components client-side.
9. Keep Decision Workspace's portfolio-construction simulation separate and labeled as an allocation preview.
10. Add static/component tests proving neither frontend surface computes `cash_after`, fee totals, funding gaps, quantity rounding, or FX.

## 15. Rollout and rollback strategy

Use an M32-specific flag independent of M31:

`EXECUTION_PLAN_PROJECTION_MODE`:

- `LEGACY` — current surfaces only; default.
- `SHADOW` — compute legacy and canonical projections; return/render legacy; emit structured comparison metrics.
- `CANONICAL` — return/render canonical projection and retain legacy adapters for old clients.

Promotion sequence:

1. Adopt the versioned pure fee calculator in the transaction path under parity tests. Numeric ledger behavior must remain bit-compatible for current SET/DR schedules.
2. Shadow FeeQuotes and trade legs for Registry-resolved, same-currency cases.
3. Compare gross inputs, quote components, rounded quantities, net cash, statuses, and expected intentional differences from legacy gross math.
4. Enable canonical backend projection for one non-production environment/workspace.
5. Migrate evaluation consumers, then Decision Workspace, then optimizer frontend.
6. Retain legacy response fields and reconstruction for at least one release/observation window.
7. Remove frontend arithmetic and legacy backend projections only after all consumers and historical fallbacks are verified.

Rollback from `CANONICAL` to `LEGACY` changes prospective rendering/projection only. It does not rewrite target allocations, history, transactions, holdings, quotes, or Registry data. Frozen canonical projections already stored in history remain historical evidence and continue to render through their contract version.

## 16. Open decisions requiring owner approval

1. **Portfolio currency authority:** add/derive a real portfolio base currency, or explicitly limit M32 v1 to one currency. The current schema cannot support a truthful multi-currency READY plan.
2. **FX ownership and freshness:** choose the canonical Market Data FX API, accepted timestamp, market-closed behavior, and missing-rate policy.
3. **Price basis/freshness:** define acceptable live/snapshot age by venue/session and whether stale prices yield `PARTIAL` or `INCOMPLETE`.
4. **Cash floor:** decide the authoritative available-cash input—raw cash, target cash weight, or policy-reserved cash—and where it is calculated upstream.
5. **Fee schedule governance:** identify the owner/source of broker, account, venue, side, and effective-date schedules before adding non-SET profiles.
6. **Actual fee admission:** decide whether manual/broker inputs may supply actual components and how provenance is preserved without conflating estimate and fact.
7. **Market-impact treatment:** decide whether risk-layer slippage adjusts estimated fill price, remains a sensitivity range, or both. It must not be mislabeled as a broker fee.
8. **Lot residual policy:** define acceptable overfunding/underfunding after valid-quantity rounding and whether a one-lot overshoot is allowed.
9. **Discretionary funding order:** preserve the current smallest-amount deterministic order or introduce an upstream independent-merit ranking. M32 must not invent investment merit.
10. **Unknown/unquotable plan UX:** approve partial-plan versus all-or-nothing behavior. In all cases, an unquoted leg cannot contribute optimistic totals.
11. **Historical projection retention:** approve storing the canonical projection in existing history JSON versus reconstructing from frozen inputs and versioned catalogs.
12. **Legacy recalculation endpoint:** choose its retirement/restriction strategy before fee schedules become time-versioned.
13. **Plan request authority:** decide whether Decision Workspace may continue sending raw sizing suggestions or must reference a server-produced recommendation/sizing snapshot.

## 17. Suggested milestone decomposition

Repository evidence supports five milestones rather than four because evaluation is a separate backend consumer with historical semantics.

### M32.1 — Versioned FeeQuote foundation and ledger parity

- immutable schedule and quote contracts;
- facts/account-aware selector interface with no symbol heuristics;
- one pure Decimal calculator;
- adapters preserving current SET/DR numeric posting behavior;
- explicit unavailable quote outcomes;
- deprecate the automatic resolver/registration inconsistency;
- no plan or frontend cutover.

### M32.2 — Priced, constrained `ExecutionTradeLeg`

- batch price/facts inputs;
- price timestamps/freshness;
- quantity derivation;
- lot/fractional rounding;
- native-currency FeeQuotes;
- explicit FX/multi-currency incomplete states;
- shadow comparison only.

### M32.3 — Net-of-cost funding and canonical backend projection

- fund from net SELL proceeds;
- require gross BUY plus costs;
- iterative lot-valid scaling;
- canonical totals/invariants/statuses;
- source/version/provenance fields;
- additive optimizer and Decision Workspace response adapters;
- freeze live optimizer projection in existing history JSON.

### M32.4 — Backend consumer and evaluation adoption

- optimizer response/history read the canonical projection;
- plan grader and execution analyzer consume the frozen plan;
- cost, price, and quantity variances are graded separately;
- legacy-history reconstruction remains typed and isolated;
- shadow telemetry and rollback drill.

### M32.5 — Frontend adoption and legacy retirement

- one shared renderer;
- optimizer and Decision Workspace cutover;
- remove independent frontend arithmetic;
- retire duplicated backend response objects after compatibility window;
- delete the DR regex fee selector only after all production callers use facts/schedules.

M32.1 and M32.2 may be reviewed and rolled back independently. M32.3 must not be promoted to canonical mode until currency, price, and schedule prerequisites pass.

## 18. Effort estimates

Estimates assume one engineer familiar with the repository, existing test infrastructure, and prompt owner decisions. They exclude Registry remediation, a new Broker Account model, a Market Data FX platform, and M31 enforcement work.

| Milestone | Estimate | Main uncertainty |
|---|---:|---|
| M32.1 FeeQuote + transaction parity | 4–6 engineering days | Schedule/version representation and admin recalculation boundary |
| M32.2 Trade legs + price/lot/FX states | 5–8 days | Price freshness and missing portfolio currency authority |
| M32.3 Canonical planner + net funding | 7–10 days | Iterative quantity/funding behavior and API compatibility |
| M32.4 Backend/evaluation adoption | 4–6 days | Frozen historical plan migration and grading semantics |
| M32.5 Frontend migration/retirement | 4–6 days | Shared rendering, old-history compatibility, UI tests |
| **Total** | **24–36 engineering days** | Owner decisions and missing currency/FX foundations can extend this |

Add 3–5 days if M32 must first implement a portfolio base-currency field and canonical FX observation adapter. That work crosses Portfolio and Market Data ownership and should be approved as an explicit dependency, not hidden inside the planner.

## 19. Explicit out-of-scope list

M32 does not implement or own:

- investment scores, signals, expected returns, or target-weight selection;
- mutation of ideal or constrained target allocations;
- M31 eligibility enforcement or Registry remediation;
- symbol regex/list/prefix classification;
- Registry identity/type/relationship governance;
- broker-account persistence unless separately approved;
- order routing, placement, cancellation, or broker integration;
- actual fill processing or reconciliation;
- plan approval, human decision lifecycle, `ExecutionIntent`, or M33 persistence;
- transaction-ledger accounting rule redesign;
- historical ledger mutation or migration;
- tax-lot selection or tax optimization;
- settlement simulation beyond carrying existing facts/warnings;
- frontend-authored fee, funding, FX, quantity, or cash arithmetic;
- automatic activation of `FACTS_ONLY_SHADOW` or `ENFORCE`.

## 20. Go / No-Go recommendation for implementation

**GO for M32.1 and the shadow-only portions of M32.2.** The repository has a stable fee formula, strong Decimal tests, a reusable deterministic funding selector, and the correct architectural separation between belief and execution.

**NO-GO for M32 canonical-plan cutover today.** The following are concrete blockers:

1. portfolio base currency is architecturally specified but absent from the operational schema;
2. transaction `currency`/`exchange_rate` are not applied to cash or replay;
3. price timestamps are discarded and Decision Workspace uses average cost;
4. Registry-backed fee schedule coverage does not exist;
5. automatic fee selection still uses a DR regex and optimistic SET fallback;
6. lot/fractional facts are not consumed and plans have no executable quantities;
7. current optimizer and Decision Workspace inputs do not identify one canonical source recommendation;
8. historical plans are reconstructed rather than frozen;
9. no shadow comparison/rollback evidence exists for cost-aware totals;
10. the ledger recalculation endpoint conflicts with immutable, versioned fee history.

Implementation may proceed incrementally with `EXECUTION_PLAN_PROJECTION_MODE=LEGACY`. Promotion to `CANONICAL` requires owner decisions in §16, complete same-currency facts/schedule coverage for the promoted workflow, price/freshness evidence, passing arithmetic invariants, evaluation migration, frontend adoption, and a rollback drill.

## Verification record

Read-only/static analysis performed:

- exhaustive call-site searches for fee calculation/profile selection, net cash effects, execution plans, funding, prices, currencies, FX, lot/fractional capabilities, transaction persistence, response types, and frontend arithmetic;
- inspection of all backend/frontend/docs named in the M32 brief plus evaluation plan consumers and replay/canonicalization boundaries;
- direct runtime fee probe confirming the 10,000 SET component formula, unknown-to-SET fallback, and `register_profile()`/automatic-resolution inconsistency;
- independent focused suites:

  ```text
  python -m pytest \
    tests/test_execution_optimizer.py \
    tests/test_plan_grader.py \
    tests/test_execution_analyzer.py \
    tests/test_execution_ledger.py \
    tests/test_registry_symbol_matching_integration.py -q

  53 passed, 169 warnings
  ```

- M31 facts contract:

  ```text
  python -m pytest tests/test_execution_instrument_facts.py -q

  15 passed, 41 warnings
  ```

Attempting the broader fee/M31 execution group found a pre-existing collection failure before any test ran:

```text
tests/test_fee_accounting.py
tests/test_execution_eligibility_m31_3.py
tests/test_execution_penalty_m31_2.py
  NameError: name 'RuntimeConsultationLog' is not defined
  at backend/services/portfolio_transactions.py:107
```

The working tree was clean before this document was added, so the missing annotation import is not an M32 regression. Existing warnings were SQLAlchemy/datetime deprecations and pytest cache-permission warnings.

No production code, migration, frontend file, database data, fee, transaction, allocation, plan behavior, or cutover mode was changed. No commit or push was performed.
