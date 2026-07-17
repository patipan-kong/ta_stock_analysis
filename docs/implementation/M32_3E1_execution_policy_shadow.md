# M32.3E1 — Execution Policy Contracts and Pure Constrained Sizing Shadow

**Date:** 2026-07-15

**Status:** Implemented as a pure, fixture-backed shadow foundation. No
canonical execution plan, transaction admission, or existing execution-plan
behavior is enabled or changed.

## Scope

M32.3E1 adds one deliberately pure policy boundary at
`backend/services/execution_policy.py`. It consumes only preloaded immutable
facts, eligibility, price observations, caller-assessed freshness, holdings,
currency context, and an already-produced `FeeQuote`. It performs no Registry
lookup, ORM/database query, provider/network call, fee selection/calculation,
clock/environment read, or hidden fallback.

The policy module is fixture-backed in this milestone. The current legacy
execution-plan BUY actions supply only a gross amount, while funding actions'
balancing value is an `AVG_COST_REFERENCE`. Neither is accepted as M32.3E1
market-price evidence. Wiring them into a READY diagnostic would imply a live
capability that the inputs do not establish, so existing post-result plan
diagnostics remain unchanged.

## Frozen contracts

`ExecutionPolicyBundle` is frozen, versioned, deterministically referenced,
and aggregates these six frozen, versioned contracts:

| Contract | Approved v1 responsibility |
| --- | --- |
| `ExecutionPricingPolicy` | Accept exactly one identity-matching `MARKET_LAST`, positive THB observation. |
| `ExecutionFreshnessPolicy` | Require caller-assessed `CURRENT` freshness, `REGULAR` session, and an explicit `current_for` threshold. |
| `ExecutionSizingPolicy` | Derive requested units from source intent under the THB-only transitional context. |
| `ExecutionQuantityPolicy` | Require explicit non-fractional capability and positive integer lot size; floor only approved derived quantities. |
| `ExecutionResidualPolicy` | Retain exact per-leg quantity/value residuals without redistribution. |
| `ExecutionQuoteLifecycle` | Bind a quote to final constrained evidence and require future admission requoting. |

`PlanningCurrencyContext` is also frozen/versioned. Its only supported M32.3E1
constructor produces explicit `THB` context labelled as transitional. It is
not a portfolio base-currency field and does not perform FX conversion.

Focused fixtures use:

```text
pricing-v1: MARKET_LAST, THB
freshness-v1: CURRENT, REGULAR, current_for=5 minutes
sizing-v1: THB-only, no manual canonical sizing
quantity-v1: non-fractional, FLOOR_TO_LOT, no partial scaling
residual-v1: no redistribution
quote-v1: no independent TTL; re-quote required at admission
```

The five-minute threshold is a test/shadow parameter supplied through the
bundle. It is not inherited from cache TTL or `m32.3c-shadow-v1`, and it is
not production execution policy.

## Pure helpers and outcomes

Every helper returns a frozen typed result with a deterministic reference.
The common outcomes are `READY`, `DEFERRED`,
`DEFERRED_BELOW_EXECUTABLE_LOT`, `INCOMPLETE`, `EXCLUDED`, and `ERROR`.
Reasons include unsupported price kind, identity/currency mismatch,
non-current freshness, unsupported/unknown session, missing or invalid lot,
unsupported fractional capability, full-sell odd lot, oversell, conflicting
intent, zero constrained quantity, and unavailable/invalidated/expired quote.

1. `select_execution_price()` accepts exactly one `MARKET_LAST` observation
   with a positive explicit THB price whose requested symbol, asset ID, and
   canonical symbol exactly match `ExecutionInstrumentFacts`. It neither
   ranks nor chooses among multiple observations. `MARKET_CLOSE`, user terms,
   average cost, estimates, unknown prices, and currency/identity mismatches
   are incomplete.
2. `accept_freshness_and_session()` uses a supplied assessment and its supplied
   `assessed_at`; it never reads a clock. Only `CURRENT` / `REGULAR` within
   the bundle's threshold is ready. Pre/post/closed session and stale/expired
   evidence defer; unknown session is incomplete.
3. `derive_requested_quantity()` handles `ALLOCATION_VALUE_AT_PRICE` BUY,
   `REDUCTION_VALUE_AT_PRICE` SELL capped by the supplied holding snapshot,
   exact `FULL_HOLDING_QUANTITY` SELL, and `HOLDING_FRACTION` SELL. An explicit
   manual quantity remains manual evidence, not canonical recommendation
   sizing. A competing REDUCE value/fraction source is an error unless a
   caller names one primary source.
4. `constrain_executable_quantity()` requires
   `facts.fractional_support is False` and a positive integer
   `facts.lot_size`. Missing lot size never defaults to one. Value-derived
   BUY/REDUCE and holding-fraction quantities floor to the lot; full sells
   must already be lot aligned. The helper never rounds up, rounds nearest,
   partially scales, or oversells. A floor to zero yields
   `DEFERRED_BELOW_EXECUTABLE_LOT`.
5. `calculate_execution_residual()` retains
   `requested_quantity - executable_quantity`, plus
   `requested_value - executable_quantity * selected_price` where a requested
   value exists. It does not redistribute the residual to another leg.
6. `validate_fee_quote_lifecycle()` requires a quoted `FeeQuote` to match
   exact side, final constrained quantity, selected price, observation/planning
   currency, Registry asset identity, and non-null schedule version. Its
   validity ends no later than `observed_at + current_for`; it has no separate
   arbitrary fee-quote TTL. A future transaction boundary must reassess and
   requote instead of reusing this planning quote.

## Policy-produced normalized input and trade leg

`normalize_policy_trade_input()` joins the completed pure results into the
existing `TradeInputNormalizationRequest` only after the quote lifecycle check
has accepted the final constrained quantity. It sets additive
`execution_policy_bundle_ref` and `execution_policy_result_ref` fields on the
resulting `NormalizedTradeInput`. Existing raw/compatibility normalizer paths
leave both fields absent and have not changed.

The new `ExecutionTradeLegBuilder.build_from_policy_input()` accepts only a
`COMPLETE` normalized input carrying those two policy references. It retains
the exact facts, eligibility, price observation, freshness assessment, and
FeeQuote object instances. It does not derive a price/quantity, recalculate a
fee, or recalculate a residual. The old
`LegacyExecutionTradeRequest` builder is unchanged and remains the M32.2
comparison path.

Example complete fixture:

```text
BUY requested_value=1050 THB / MARKET_LAST=10 THB = requested 105 units
lot_size=100 => executable 100 units
quantity residual=5 units; gross-value residual=50 THB
FeeQuote(BUY, 100, 10 THB, matching asset/schedule) => COMPLETE policy input
```

Example incomplete fixture:

```text
BUY requested_value=1000 THB, no successful FeeQuote
=> INCOMPLETE / FEE_QUOTE_UNAVAILABLE
```

## Evidence limitations and M32.3E2 dependencies

M32.3E1 does not claim live readiness. Current provider DTOs generally lose
exchange observation time/session/currency, and current Registry facts do not
prove positive lot-size and explicit non-fractional capability coverage. The
legacy plan has amount-only BUY actions and average-cost funding values. M32.3E2
must supply real evidence plumbing and capability readiness before a live
post-result policy shadow is useful:

- provider/orchestration preservation of canonical `MARKET_LAST`, identity,
  THB currency, observation/receipt time, and regular-session evidence;
- Registry remediation/coverage for positive lot size and explicit
  `fractional_support=False` on the supported executable universe;
- adjudicated holding snapshots and explicit REDUCE primary-source ownership;
- facts-backed fee schedule/quote coverage following final constrained sizing;
- an approved operational freshness threshold and a real portfolio/base
  currency context before any canonical net-funding work.

## Explicit non-goals

No provider DTO or market-data orchestration change, Registry write/capability
backfill, FX, portfolio base-currency field, cash/NAV snapshot, net funding
planner, canonical plan, optimizer/transaction/ledger/replay behavior,
API/frontend/persistence/migration change, M31 enforcement, compatibility
retirement, ExecutionIntent, commit, or push is part of M32.3E1.

## Verification

Focused M32.3E1 plus M32.2/M32.3B/M32.3C compatibility contracts:
**56 passed**. The suite covers immutable/versioned bundle references, all
accepted/rejected price kinds, one-observation/identity/currency rules,
freshness/session behavior, value/full/fraction sizing, conflict handling,
lot/fraction/oversell rules, exact residuals, quote binding/expiry, complete
and incomplete policy normalization, object identity, and unchanged legacy
trade-leg construction.

The project `backend/.venv` lacks pytest; the supplied
`backend/venv-test` environment ran the suite. The run emitted only existing
SQLAlchemy deprecation and pytest-cache permission warnings.
