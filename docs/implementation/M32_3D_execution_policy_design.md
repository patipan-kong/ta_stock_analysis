# M32.3D — Quantity Constraint, Price Selection, and Execution Policy Design

**Audit date:** 2026-07-15

**Decision:** **GO for policy approval and a split shadow implementation; NO-GO
for authoritative canonical execution planning**

**Scope:** Audit and design only. No production code, migration, API, frontend,
optimizer, funding, transaction, ledger, Registry data, provider behavior, M31
mode, or persistence behavior was changed.

## 1. Executive summary

M31 and M32.1–M32.3C now provide the evidence objects needed to discuss an
execution policy without guessing: authoritative identity and eligibility,
versioned fee quotes, quantity/value intent, trade-leg projection, market-price
observations, and reproducible freshness assessments. They do **not** yet
decide which price may size a trade, which session is executable, how a value
becomes units, how units are constrained, how residual cash is handled, or
when a fee quote stops being usable.

The smallest repository-supported executable policy is deliberately narrow:

- one explicitly supplied THB planning-currency context;
- Registry `RESOLVED + TRADABLE` instruments only;
- one Market Data-owned, identity-bound `MARKET_LAST` observation;
- `CURRENT` freshness under an approved versioned age threshold;
- `REGULAR` session only;
- observation, Registry, planning, and FeeQuote currency all equal THB;
- no FX, user-entered execution price, close-price fallback, average-cost
  fallback, partial fill, broker routing, or slippage-adjusted price;
- non-fractional instruments with an explicit positive Registry `lot_size`;
- floor-to-lot for value-derived BUY/REDUCE quantities, exact lot-aligned
  holding quantity for full SELL;
- one FeeQuote created after quantity constraint, for the exact constrained
  quantity and selected price;
- net-of-fee cash validation against the already-resolved portfolio cash-floor
  policy; and
- explicit residuals, never redistributed, rounded up, or hidden.

This is a policy proposal, not current behavior. It is compatible with the
repository's architecture, but live inputs cannot satisfy it today. Current
quote DTOs normally omit exchange observation time, session, and currency.
`Portfolio` has no operational base-currency field. Registry bootstrap claims
default `fractional_support=False` and `lot_size=None`, while current preflight
artifacts do not certify lot coverage. The current funding algorithm is gross,
may scale one monetary funding candidate, and does not consume constrained
quantities or FeeQuotes.

M32.3E should therefore be split. A first slice may implement the six frozen
policy contracts and pure shadow sizing after the decisions in §14 are
approved. Evidence plumbing, capability remediation, and canonical net-cost
planning must be separate reviewable slices. Authoritative cutover remains a
later decision.

## 2. Current execution evidence graph

```text
Asset Registry
  -> ExecutionInstrumentFacts
  -> ExecutionEligibility
                         \
Market Data               \
  -> ExecutionPriceObservation -> PriceFreshnessAssessment
                           \       /
Recommendation/value intent -> NormalizedTradeInput (validation only)
Holding/cash snapshot       /       \
                                  FeeQuote
                                     \
                              ExecutionTradeLeg
```

The graph has evidence contracts but no policy node between evidence and
`NormalizedTradeInput`. Today:

- `ExecutionPriceObservation` records evidence and explicitly does not select
  an execution price.
- `PriceFreshnessAssessment` reports a status under a supplied policy; the
  included five-minute shadow policy is not approved execution policy.
- `NormalizedTradeInput` validates supplied quantity, price, facts,
  eligibility, and FeeQuote. It does not calculate quantity or select price.
- `ExecutionTradeLegBuilder` still consumes `LegacyExecutionTradeRequest`,
  copies requested quantity to executable quantity, and applies no lot or
  fractional rule.
- `FeeQuote` binds side, quantity, unit price, currency, schedule version, and
  effective time, but has no expiry or lifecycle assessment.
- `execution_plan.py` completes gross average-cost funding arithmetic before
  the M31/M32 shadow block. BUY actions contain value but no units or price.
- `funding_source_analysis.py` and `execution_optimizer.py` size funding in
  currency amounts. One discretionary candidate may be scaled to close an
  exact gross funding gap.
- optimizer target allocations and Decision Workspace sizing are allocation
  evidence, not executable quantities.
- `portfolio_transactions.py` accepts explicit shares and a user-entered
  price, calculates posting fees, and may let BUY cash become negative. It is
  ledger admission, not a planning-price or sizing authority.

### Contract readiness

| Contract | Complete for its current purpose | Missing for canonical execution |
| --- | --- | --- |
| `ExecutionInstrumentFacts` | Yes: identity, listing currency, tradability, lot/fraction fields | Capability data coverage and positive-lot governance |
| `ExecutionEligibility` | Yes: pure typed eligibility | M31 blocking policy remains separate and disabled |
| `ExecutionPriceObservation` | Yes: immutable evidence | An orchestration path that supplies observation time, session, and currency |
| `PriceFreshnessAssessment` | Yes: pure assessment | Approved execution threshold and accepted statuses |
| `NormalizedTradeInput` | Yes: immutable validation result | Policy-produced constrained quantity and quote-lifecycle evidence |
| `FeeQuote` | Yes: exact fee arithmetic and schedule identity | Lifecycle/expiry binding to the selected observation and plan |
| `ExecutionTradeLeg` | Yes for M32.2 shadow | Builder migration from legacy request to complete normalized input |
| Canonical execution plan | No | Net funding, cash floor, residuals, readiness, rollout, and history contract |

## 3. Price-selection policy

### Proposed `ExecutionPricingPolicy`

| Field | Decision for executable v1 |
| --- | --- |
| Owner | Execution Planning selects; Market Data owns the observation and canonical provider choice |
| Accepted price kind | `MARKET_LAST` only |
| Provider preference | None inside Execution Planning. The Market Data boundary must supply exactly one canonical observation |
| Identity | Observation `asset_id` and canonical symbol must agree with `ExecutionInstrumentFacts` |
| Currency | Observation currency must equal Registry listing currency and planning currency |
| User term | Never a market sizing price in v1 |
| Close/open/high/low | Not accepted in v1 |
| Average cost / estimated | Reference-only; never accepted |
| Output | Typed `ExecutionPriceSelection` retaining the exact observation and policy version |

The planner must not rank Yahoo Chart versus yfinance, inspect a raw provider
payload, or fall back from `MARKET_LAST` to `MARKET_CLOSE`. Provider selection
already belongs to the Market Data Platform (`get_provider()`), and moving a
second provider preference into execution would create two authorities.

If orchestration supplies zero or more than one purported canonical
observation, price selection is `INCOMPLETE`; it does not choose the newest,
largest, or first value. Slippage from `execution_penalty.py` remains a risk
estimate/sensitivity field and does not alter the selected price in v1.

**Inputs:** one preselected observation, facts, policy version, assessment
instant. **Dependencies:** M31 facts and M32.3C evidence only. **Failure modes:**
missing/multiple observation, unsupported kind, identity mismatch, missing or
mismatched currency. **Rollback:** disable the shadow policy consumer; legacy
planning continues unchanged because no existing price path is replaced.

## 4. Freshness policy

### Proposed `ExecutionFreshnessPolicy`

| Concern | Decision for executable v1 |
| --- | --- |
| Owner | Execution Planning policy over Market Data evidence |
| Accepted result | `CURRENT` only |
| Assessment time | Caller-supplied plan assessment instant; never a clock read inside pure code |
| Age threshold | Required versioned parameter with no implicit default |
| Stale / expired | Defer the leg; retain the recommendation |
| Missing timestamp/currency/session | Incomplete evidence |
| Shadow policy reuse | Prohibited unless its five-minute threshold is explicitly approved as execution policy under a new policy version |

The repository's five-minute cache TTL is not observation freshness. The
M32.3C `m32.3c-shadow-v1` five-minute threshold is a repeatable diagnostic, not
authority. M32.3E must require an explicitly approved `current_for` value and
must not silently import either number.

`PriceFreshnessPolicy.stale_for` may remain useful for diagnostics, but v1
accepts neither `STALE` nor `EXPIRED`. `SESSION_CLOSED`, `SESSION_UNKNOWN`,
`PRICE_TIMESTAMP_MISSING`, `CURRENCY_UNKNOWN`, and `UNKNOWN` are also
non-executable.

**Inputs:** selected observation, approved `PriceFreshnessPolicy`, explicit
`assessed_at`. **Output:** the existing immutable assessment plus an
accept/reject policy result. **Dependencies:** `assess_price_freshness()`;
there is no market-data lookup. **Failure modes:** every non-`CURRENT` status
is typed and non-executable. **Rollback:** remove policy consultation from the
shadow path; the observation and assessment contracts remain useful evidence.

## 5. Session policy

V1 accepts `REGULAR` only.

| Session | V1 result | Reason |
| --- | --- | --- |
| `REGULAR` | Continue when freshness is `CURRENT` | Repository's current fee and quantity models assume ordinary venue trading |
| `PRE_MARKET` | `DEFERRED` | No spread, liquidity, venue, or fee behavior is modeled for this session |
| `AFTER_HOURS` | `DEFERRED` | Same limitation; do not treat a known session as automatically supported |
| `CLOSED` | `DEFERRED` | A close may remain useful analysis evidence but is not a current executable quote |
| `UNKNOWN` | `INCOMPLETE` | Missing evidence is not a session policy |

Market Data owns session determination. Execution policy consumes the enum and
never consults a calendar or infers a session from local time, exchange,
symbol suffix, or provider name. The current providers usually emit
`UNKNOWN`, so the live path remains incomplete until their already-loaded
payload/DTO boundary preserves session evidence.

## 6. Currency ownership

| Currency concept | Authoritative owner | V1 treatment |
| --- | --- | --- |
| Listing/native currency | Asset Registry through `ExecutionInstrumentFacts.currency` | Must be `THB` |
| Price currency | Market Data through `ExecutionPriceObservation.currency` | Must equal listing currency |
| FeeQuote currency | Fee Domain | Must equal selected price currency |
| Portfolio base currency | Portfolio Domain | Operational field is absent; architecture says every portfolio should own one |
| Portfolio cash currency | Portfolio Domain / Ledger | Current scalar cash is operationally treated as THB but is not typed on `Portfolio` |
| Recommendation valuation currency | Upstream allocation/Portfolio Domain | Current amount fields omit it |
| FX observation | Market Data Platform | Absent and out of v1 |
| FX application | Execution Planning for estimates; Portfolio/Ledger for accounting | Prohibited in v1 |

The long-term rule is unchanged: Portfolio owns base currency. M32 must not
add a second owner. Until that field exists, v1 may run only with an explicit
transitional `PlanningCurrencyContext(currency="THB", source="single-currency-v1")`
supplied at orchestration. It is a scope gate, not evidence that a particular
portfolio row declares THB.

Every active leg must satisfy:

```text
facts.currency
  == observation.currency
  == FeeQuote.currency
  == requested_value currency
  == planning currency
  == cash snapshot currency
  == "THB"
```

Any missing value or mismatch is `INCOMPLETE`; no `exchange_rate=1.0` fallback
is permitted. The transaction table's existing `exchange_rate` cannot supply
planning FX because current cash mutation and replay ignore it.

## 7. Quantity conversion policy

### Proposed `ExecutionSizingPolicy`

Execution Planning owns deterministic value-to-requested-quantity conversion.
The normalizer validates its result; the trade-leg builder projects it. Neither
may perform the calculation independently.

| Quantity source | V1 requested quantity before lot constraint |
| --- | --- |
| `ALLOCATION_VALUE_AT_PRICE` BUY | `requested_value / selected_market_last` |
| `REDUCTION_VALUE_AT_PRICE` SELL | `min(requested_value / selected_market_last, held_quantity)` |
| `FULL_HOLDING_QUANTITY` SELL | exact quantity from one immutable Portfolio Runtime snapshot |
| `HOLDING_FRACTION` SELL | `held_quantity * explicitly supplied upstream fraction` |
| `EXPLICIT_USER_QUANTITY` | Preserved as manual intent, but not promoted by the canonical recommendation planner in v1 |
| `BROKER_ORDER_QUANTITY` | Out of scope; no broker routing exists |

The source recommendation's `requested_value` remains the belief/constrained
allocation's gross target value. It is never overwritten with
`quantity × price`. After quantity constraint, `FeeQuote.gross_amount` records
the achievable gross value and the difference is a residual.

For BUY, fees are not subtracted before value-to-quantity conversion because
the upstream allocation amount describes desired asset value, not an
all-inclusive cash budget. FeeQuote then establishes the larger net cash
requirement. The plan-level residual/cash policy decides whether that full leg
fits; it does not silently resize the leg a second time.

For REDUCE, v1 accepts an explicit reduction value from the authoritative
target-allocation delta or an explicitly named holding fraction. The Decision
Workspace's legacy default 25% heuristic is not authoritative input. When both
value and fraction are supplied, the adapter must reject the conflict unless
the source contract explicitly designates one as primary; it must not choose.

**Inputs:** source intent, selected price, holding snapshot where required,
facts identity, side, policy version. **Outputs:** exact `Decimal`
`requested_quantity`, source/confidence, and derivation evidence. **Dependencies:**
no DB, clock, provider, fee, or frontend. **Failure modes:** missing/invalid
value, unsupported source, missing or identity-mismatched holding, oversell,
conflicting intents. **Rollback:** shadow sizing is removed without touching
recommendations or legacy amounts.

## 8. Lot and fractional policy

### Proposed `ExecutionQuantityPolicy`

Registry facts are the only runtime capability source. Asset type, exchange,
ticker shape, broker convention, and frontend input precision are not evidence.

V1 supports only:

```text
facts.fractional_support is False
facts.lot_size is a positive integer
```

`fractional_support=True` is not enough to execute fractional quantities,
because the Registry has no fractional increment/precision and there is no
broker capability contract. `fractional_support=None`, `lot_size=None`, zero,
or negative is incomplete capability evidence. In particular, `lot_size=None`
must not become an implicit lot of one.

Quantity rules:

1. Value-derived BUY/REDUCE: floor to the greatest non-negative multiple of
   `lot_size` not exceeding requested quantity.
2. Full SELL: use the exact held quantity only if it is lot-aligned. Do not
   floor a liquidation and silently leave an odd-lot residual.
3. Explicit holding fraction: derive first, then floor to lot.
4. Never round to nearest or ceiling; those can overspend or oversell.
5. A zero constrained quantity is `DEFERRED_BELOW_EXECUTABLE_LOT`, not a zero
   trade and not an error.

The existing `QuantityAdjustmentSummary` can represent requested quantity,
executable quantity, residual quantity, policy reference, and reason. M32.3E
should converge the duplicate M32.2 lot/fraction summaries on that one shape
rather than adding another rule implementation.

**Inputs:** requested quantity and the exact facts object. **Outputs:**
executable quantity plus immutable adjustment/residual evidence. **Dependencies:**
Registry facts only. **Failure modes:** missing capability, unsupported
fractional capability, invalid lot, zero result, non-aligned full liquidation.
**Rollback:** no-op quantity behavior remains available only in legacy shadow;
policy-produced legs are disabled as a unit.

### Registry capability readiness

The persisted schema and M31 facts adapter expose `fractional_support` and
`lot_size`. However:

- `AssetClaim` defaults to `fractional_support=False`, `lot_size=None`;
- the production bootstrap planner constructs claims without overriding those
  defaults;
- M31.6 explicitly left lot/settlement metadata among the facts requiring
  authoritative adjudication for unresolved symbols; and
- the committed M31.6 preflight artifact reports coverage and Registry row
  counts, not per-asset lot/fraction capability values.

Therefore repository evidence does not prove any current executable symbol is
v1 quantity-ready. A read-only live query was attempted during this audit, but
the environment exposes only a Microsoft Store Python alias and no installed
interpreter, so capability counts could not be remeasured. M32.3E must add a
read-only capability preflight and require 100% positive-lot coverage for its
supported shadow universe before interpreting a quantity as executable.

## 9. Residual cash and cash-floor policy

### Proposed `ExecutionResidualPolicy`

Residuals are expected output of conservative lot rounding, not an error to be
hidden.

Per leg, record:

- `quantity_residual = requested_quantity - executable_quantity`;
- `gross_value_residual = requested_value - FeeQuote.gross_amount` when a
  value intent exists; and
- reason/policy version.

At plan level, record:

- cash before;
- net SELL proceeds from FeeQuotes;
- net BUY cash requirements from FeeQuotes;
- absolute required reserve;
- cash after active legs;
- surplus above reserve or shortfall; and
- sum of gross value residuals, separately from cash residual.

No residual is redistributed among other symbols, used to round a different
leg upward, or converted into a new recommendation. This preserves the belief
and avoids a second allocation engine inside execution.

### Cash-floor decision

Portfolio Policy owns `min_cash_pct`; Execution Planning enforces it against
net cash effects. The planner consumes one immutable policy/NAV/cash snapshot:

```text
required_cash_reserve = portfolio_nav * min_cash_pct / 100
cash_after = cash_before
             + sum(SELL FeeQuote.net_cash_effect)
             + sum(BUY FeeQuote.net_cash_effect)  # negative values

ready only if cash_after >= required_cash_reserve
```

The planner must not invent a fixed baht minimum. The minimum executable BUY
is the first positive Registry-valid lot whose quoted net cash requirement
fits above the reserve. If lot flooring produces zero or the full leg breaches
the reserve, it is deferred. Current policy sources already expose
`min_cash_pct` through `PolicyEnvelope`/`EffectiveEnvelope`; the canonical
planner must consume the frozen resolved value, not recompute policy.

V1 applies no automatic partial resizing to make cash fit. Necessary SELLs
remain full. A discretionary funding candidate is used in full only when its
already-recommended constrained leg does not exceed the remaining funding gap;
the current exact monetary `SCALED` behavior is not canonical v1 behavior.
Overshooting candidates remain deferred and the shortfall remains explicit.
This avoids enlarging or partially inventing a trade for funding reasons.

**Inputs:** constrained quoted legs, cash/NAV snapshot, resolved cash-floor
policy, planning currency. **Output:** plan residual/funding assessment.
**Dependencies:** FeeQuote signed cash effects and Portfolio Policy; no gross
amount reconstruction. **Failure modes:** missing/stale policy snapshot,
currency mismatch, shortfall, zero executable lot. **Rollback:** keep the
existing gross `resolve_funding_gap()` result as the public legacy projection
while the new assessment remains shadow-only.

## 10. FeeQuote lifecycle

### Proposed `ExecutionQuoteLifecycle`

`FeeQuote` remains immutable. A separate immutable lifecycle assessment binds
it to the selected price evidence and policy context.

| Concern | Decision |
| --- | --- |
| Quote timing | Quote only after final quantity constraint |
| Exact binding | Side, executable quantity, selected price, currency, schedule ID/version, effective time, observation ref, facts asset ID, and policy bundle version |
| Planning validity | Quote must be `QUOTED`, exact-match the normalized input, and its price assessment must still be `CURRENT + REGULAR` |
| Upper-bound expiry | No later than `observation.observed_at + approved current_for` |
| Admission reuse | Prohibited in v1; transaction admission must reassess price and obtain a new posting-time quote |
| Requote triggers | Any side/quantity/price/currency/identity/schedule/account-context change; price no longer current; session no longer regular; plan refresh |

There is no evidence for an independent arbitrary FeeQuote TTL. Percentage fee
arithmetic does not age by itself; the selected price and schedule applicability
do. V1 therefore bounds planning quote lifetime by the price's approved CURRENT
window and invalidates it on every binding change. A future broker quote may
add its own expiry, but that is not present here.

The lifecycle assessment should expose `CURRENT`, `EXPIRED`, `INVALIDATED`, or
`UNAVAILABLE`, an upper-bound `expires_at`, reason, and the refs it checked.
At transaction admission, the plan quote is estimate evidence only. A new
quote at the then-current effective time prevents a stale plan from becoming
ledger truth.

**Inputs:** FeeQuote, selected observation/freshness, exact normalized input,
facts, policy bundle, assessment time. **Outputs:** lifecycle assessment.
**Dependencies:** no recalculation; fee selection/calculation remains in
`broker_fees.py`. **Failure modes:** unavailable quote, mismatch, expiry,
policy/session change, schedule/account-context change. **Rollback:** ignore
the lifecycle assessment and retain current compatibility posting; no quote or
ledger row requires migration.

## 11. Failure behavior

Policy evaluation must return typed results. Missing evidence is not an
exception, and a recommendation is not deleted because it cannot currently be
executed.

| Condition | Leg result | Plan behavior |
| --- | --- | --- |
| Resolved/eligible, accepted price/freshness/session/currency, valid lot, quote current | `READY` | Include in net funding assessment |
| Stale/expired price, pre/after-hours/closed session | `DEFERRED` | Retain recommendation and reason; no executable leg |
| Cash-floor shortfall or zero lot-rounded quantity | `DEFERRED` | Report shortfall/residual; no automatic resize |
| Missing observation time/session/currency, missing lot, unavailable quote | `INCOMPLETE` | Report missing evidence; plan cannot be READY |
| Unknown/ambiguous/not-tradable/reference eligibility | `EXCLUDED` from canonical executable projection | Preserve belief evidence; M31 admission enforcement remains a separate milestone |
| Registry infrastructure failure | `INCOMPLETE_REGISTRY_FAILURE` | No executable projection; recommendation analysis may remain available |
| Identity/side/quantity/price/currency/quote mismatch, oversell, negative inputs | `ERROR` typed contract inconsistency | Fail the canonical projection deterministically; shadow path must not affect legacy result |

Minimal v1 has no partial-execution claim. A response may describe per-leg
results for diagnosis, but a plan is `READY` only when every active leg in its
declared execution set is `READY` and the net cash floor passes. There is no
partial fill, automatic one-leg scaling, or hidden omission.

## 12. Policy ownership and dependency graph

### Policy ownership map

| Policy contract | Owner | Inputs | Output | Direct dependencies |
| --- | --- | --- | --- | --- |
| `ExecutionPricingPolicy` | Execution Planning | One canonical observation, facts | Selected-price result | M31 facts, M32.3C observation |
| `ExecutionFreshnessPolicy` | Execution Planning | Observation, explicit assessment time, approved thresholds | Accepted freshness result | M32.3C assessor |
| `ExecutionSizingPolicy` | Execution Planning | Value/quantity intent, selected price, holding snapshot | Requested quantity derivation | M32.3B source vocabulary, Portfolio Runtime snapshot |
| `ExecutionQuantityPolicy` | Execution Planning consuming Registry capability | Requested quantity, facts lot/fraction fields | Constrained quantity and adjustment | Asset Registry facts only |
| `ExecutionResidualPolicy` | Execution Planning consuming Portfolio Policy | Quoted legs, cash/NAV/policy snapshot | Net funding, reserve, residual result | FeeQuote, Portfolio Runtime/Policy |
| `ExecutionQuoteLifecycle` | Execution Planning; fee arithmetic remains Fee Domain | Quote, normalized input, price/freshness, policy bundle | Quote lifecycle assessment | M32.1 and M32.3C contracts |

The six policies should be frozen, versioned, and aggregated into one
`ExecutionPolicyBundle`. Pure helpers receive the bundle explicitly. They do
not read environment variables, clocks, ORM sessions, providers, or global
configuration.

```text
Registry facts + eligibility            Market Data observation
          |                                      |
          |                             Pricing + Freshness Policy
          |                                      |
Source value/quantity + holding snapshot --------+
          |
          v
ExecutionSizingPolicy -> requested quantity
          |
          v
ExecutionQuantityPolicy -> constrained quantity + residual
          |
          v
Fee Domain -> FeeQuote exact to quantity/price/currency
          |
          v
NormalizedTradeInput validation
          |
          v
ExecutionQuoteLifecycle
          |
          v
ExecutionResidualPolicy + cash/NAV/min-cash snapshot
          |
          v
ExecutionTradeLeg -> future canonical plan projection
```

The orchestration boundary batch-loads facts, observations, holdings, cash,
and policy once. Every policy helper below that boundary remains pure.

## 13. Minimal executable v1

An M32 v1 leg is executable only when all of these are true:

1. Facts are `RESOLVED`, role `TRADABLE`, eligibility `ELIGIBLE`, and all
   identities agree.
2. Registry market/exchange has a facts-backed FeeSchedule; current support is
   SET/THB.
3. An explicit THB planning-currency context is present.
4. One canonical `MARKET_LAST` observation has positive Decimal price,
   observation and receipt time, THB currency, and `REGULAR` session.
5. Freshness is `CURRENT` under an approved, non-shadow policy version.
6. Quantity source is value-based BUY/REDUCE, full-holding SELL, or explicitly
   supplied holding fraction.
7. Holding evidence is identity-bound and immutable for SELL.
8. Registry explicitly says non-fractional and supplies a positive integer lot.
9. Quantity is floored to lot, remains positive, and cannot oversell.
10. A facts-backed FeeQuote exists for the exact constrained quantity, selected
    price, THB currency, side, and effective time.
11. Quote lifecycle is current.
12. Net cash effects leave the approved cash reserve intact.
13. All residuals and failures are exposed; no active leg is silently dropped.

Excluded from v1: foreign currency, FX, fractional trading, null lot size,
premarket/after-hours/closed/unknown session, market close as a fallback,
average cost, user execution terms, delayed/stale prices, slippage price
adjustment, partial fill/scaling, broker routing/account tiers, order types,
quote reuse at transaction admission, persistence, and ExecutionIntent.

## 14. Open decisions and approval gates

The policy direction above is complete, but these parameters/transition
choices have no authoritative repository value and require explicit approval:

1. **CURRENT duration:** approve a numeric `current_for` threshold and policy
   version. Do not inherit the five-minute cache or shadow value implicitly.
2. **Transitional THB context:** approve fixed THB-only planning until Portfolio
   Domain supplies real base currency, or defer all authoritative work until
   that domain gap is closed.
3. **Lot governance:** approve `lot_size=None => incomplete` and remediate
   supported Registry assets. Do not approve `None => 1` without Registry
   evidence.
4. **Fractional v1 exclusion:** approve that `fractional_support=True` remains
   unsupported until Registry/broker precision exists.
5. **Full SELL odd lots:** approve explicit incompleteness instead of silently
   leaving a residual holding.
6. **REDUCE source conflict:** approve designated-source-only behavior when
   both target value and holding fraction are present.
7. **No partial scaling:** approve removing current exact monetary scaling from
   the canonical v1 path; legacy output remains unchanged during shadow.
8. **Plan readiness:** approve the rule that any non-ready active leg prevents
   the plan from being labeled READY, even though diagnostics may show ready
   sibling legs.
9. **Policy snapshot identity:** define the immutable NAV/cash/min-cash snapshot
   reference consumed by residual policy. Existing response dictionaries are
   not a frozen contract.
10. **Planning quote at admission:** approve mandatory reassessment/requote and
    prohibit using a plan estimate directly as ledger posting evidence.

## 15. Go / No-Go

### Policy approval

**GO**, subject to explicit approval of §14. The proposed decisions follow
existing domain ownership, use no symbol or asset-type heuristics, preserve
belief separately from execution, and reuse the one fee implementation.

### M32.3E pure shadow foundation

**GO after policy approval.** Pure frozen policy contracts, typed results,
quantity adjustment, quote lifecycle assessment, and fixture-backed shadow
tests can be implemented without changing a plan.

### Live shadow completeness

**NO-GO today.** Current provider DTOs normally cannot satisfy observation
time/session/currency requirements, and Registry lot coverage is not certified.

### Authoritative canonical planning

**NO-GO.** It additionally requires net-of-cost funding orchestration, a frozen
Portfolio policy/cash/NAV snapshot, batch evidence loading, plan contract and
rollout design, frontend/API adoption, and parity telemetry. M31 enforcement
also remains independently disabled.

## 16. Recommended M32.3E scope and sequence

M32.3E should **not** be one milestone. Split it as follows:

### M32.3E1 — Execution policy contracts and pure constrained sizing shadow

- add the six frozen/versioned policy contracts and one policy bundle;
- add typed price selection, freshness/session acceptance, quantity
  derivation, lot adjustment, residual, and quote-lifecycle results;
- require caller-supplied times and evidence;
- quote after constraint and bind the exact objects;
- evolve `ExecutionTradeLegBuilder` to accept only a complete policy-produced
  normalized input under a new shadow entry point;
- retain the M32.2 legacy builder during comparison;
- no provider, Registry data, planner, API, frontend, persistence, or ledger
  behavior change.

### M32.3E2 — Evidence plumbing and readiness

- preserve Yahoo observation timestamp, receipt time, session, currency,
  timezone, delay, and cache time through one canonical Market Data DTO;
- batch-load observations for all candidate legs;
- add a read-only lot/fraction capability preflight;
- remediate supported Registry capability facts through governance;
- supply the explicit THB planning context and a frozen policy/cash/NAV
  snapshot;
- record shadow outcome/residual/quote-expiry telemetry;
- still no canonical plan behavior change.

### M32.3E3 — Canonical net-cost plan shadow

- replace gross funding inputs in the new shadow only with constrained legs and
  signed FeeQuote cash effects;
- apply the resolved cash floor and no-partial-scaling rule;
- project one immutable canonical plan diagnostic for optimizer and Decision
  Workspace inputs;
- compare actions, quantities, gross/net cash, residuals, and readiness against
  both legacy projections;
- do not cut over until evidence coverage and parity gates are approved.

### Later adoption milestone

API/frontend/history adoption, transaction admission requote, persistence, and
retirement of duplicate legacy plan arithmetic require a separate cutover
milestone. They should not be hidden inside M32.3E.

## Verification and audited files

### Backend contracts and execution boundaries

- `backend/services/execution_price_observation.py`
- `backend/services/normalized_trade_input.py`
- `backend/services/execution_trade_leg.py`
- `backend/services/broker_fees.py`
- `backend/services/broker_fees_compat.py`
- `backend/services/execution_instrument_facts.py`
- `backend/services/execution_eligibility.py`
- `backend/services/execution_plan.py`
- `backend/services/funding_source_analysis.py`
- `backend/services/optimizer/execution_optimizer.py`
- `backend/services/optimizer/policy_engine.py`
- `backend/services/optimizer/constraint_resolver.py`
- `backend/services/position_sizing.py`
- `backend/agents/optimizer.py`
- `backend/services/portfolio_transactions.py`
- `backend/models/asset.py`
- `backend/models/database.py`
- `backend/services/asset_domain.py`
- `backend/services/bootstrap_planner.py`
- `backend/services/registry_lookup.py`
- `backend/services/asset_definitions/capability_view.py`
- `backend/services/asset_definitions/vocabulary.py`
- `backend/services/market_data/base.py`
- `backend/services/market_data/provider.py`
- `backend/services/market_data/yahoo_chart.py`
- `backend/services/market_data/yahoo.py`
- `backend/main.py`

### Frontend and Decision Workspace

- `frontend/lib/api.ts`
- `frontend/lib/executionPlan.ts`
- `frontend/components/optimizer/ExecutionPlanCard.tsx`
- `frontend/components/operations-center/decision-workspace/DecisionWorkspace.tsx`
- `frontend/components/TransactionModal.tsx`

### Architecture and prior milestones

- `docs/implementation/M32_cost_aware_execution_planning_design.md`
- `docs/implementation/M32_1_fee_quote_foundation.md`
- `docs/implementation/M32_2_trade_leg_foundation.md`
- `docs/implementation/M32_3A_normalized_trade_input_design.md`
- `docs/implementation/M32_3B_normalized_trade_input_foundation.md`
- `docs/implementation/M32_3C_price_observation_foundation.md`
- `docs/implementation/M31_4_execution_cutover_readiness.md`
- `docs/implementation/M31_5_registry_cutover_preparation.md`
- `docs/implementation/M31_6_registry_remediation_wave1.md`
- `docs/implementation/M31_6_registry_remediation_wave1_preflight.json`
- `docs/architecture/PORTFOLIO_DOMAIN_MODEL.md`
- `docs/architecture/asset_foundation.md`
- `docs/architecture/asset_definitions.md`
- `docs/definitions/asset_definition_cash.md`
- `docs/investment/OPTIMIZER_PHILOSOPHY.md`
- `docs/decisions/ADR-004_ONE_IMPLEMENTATION_PER_RULE.md`
- `docs/engineering/ENGINEERING_PRINCIPLES.md`
- `docs/engineering/DECISION_LOG.md`

Verification was read-only except for creation of this design document.
Repository searches traced every required contract and consumer. No production
test was necessary because no executable code changed. The attempted read-only
live Registry capability query could not run because this environment has no
installed Python interpreter; this limitation is reflected in the readiness
finding rather than replaced by an assumption. No commit or push was
performed.
