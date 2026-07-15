# M32.3E2 — Live Evidence Readiness Audit and Shadow Integration Design

**Audit date:** 2026-07-15

**Decision:** **GO for a narrow, non-authoritative live-evidence shadow
implementation.  NO-GO for canonical execution planning or execution-price
sizing.**

**Scope:** Audit and design only.  No provider, Registry, plan, optimizer,
transaction, API, frontend, persistence, policy, or financial-calculation
behavior was changed.

## 1. Executive summary

M32.3E1 has the necessary pure contracts to produce a complete
`NormalizedTradeInput`, but it intentionally receives fixture-backed evidence.
The runtime already contains most *source* data, but not the evidence-preserving
adapters and orchestration that join it safely:

- Yahoo Chart's raw response has a `meta` object and timestamped history bars,
  but `YahooChartProvider.get_quote()` publishes only `current_price`,
  `previous_close`, and a locally generated `last_updated` receipt time.
- The M32.3C Yahoo adapters already know how to preserve an explicitly supplied
  observation time, session, currency, cache time, and provider identity.  No
  live boundary supplies that complete DTO to them.
- Registry resolution already exposes immutable facts, eligibility, listing
  currency, `lot_size`, and `fractional_support`; current Registry data cannot
  be assumed to have a positive lot size for a given live symbol.
- The execution-plan boundary owns a database session, requested allocation
  values, holdings, and the existing M31/M32 post-result shadow hook.  It is
  the correct initial integration point, but its legacy plan is intentionally
  cost-basis/gross based and its shadow runs after the plan is complete.
- Facts-backed `FeeQuote` is ready once a final quantity, selected price, and
  explicit quote/assessment instant are supplied.  It must be invoked only
  after constrained sizing; the transaction write path remains compatibility
  fee quoting and is not the M32.3E2 owner.

The minimum M32.3E2 should add a Market Data-owned immutable live quote
envelope/adapter, a read-only batch orchestration adapter, and a private
post-result execution-plan shadow that creates observations, assessments,
facts-backed quotes, policy-produced normalized inputs, and policy-input legs
only as diagnostics.  It must report typed incompleteness rather than fill a
missing timestamp, session, currency, lot size, or holding evidence.

That limited implementation is safe because it is additive, exception
contained, log-only, and can be disabled without data migration.  It is not
safe to make policy-produced inputs authoritative today.

## 2. Current runtime evidence graph

```text
Current runtime

Yahoo Chart raw response ──> YahooChartProvider.get_quote()
                             └─> {current_price, previous_close, last_updated}
                                     └─> data_fetcher/cache ──> presentation/optimizer

Yahoo/Yahoo Chart history ──> timestamped DataFrame
                                     └─> analytics/timing (not an execution quote)

Registry DB ──> AssetView ──> ExecutionInstrumentFacts ──> ExecutionEligibility
Portfolio DB ──> PortfolioItem(shares, avg_cost), Portfolio(cash_balance)
Position sizing ──> suggested_pct ──> ExecutionPlan BuyAction(estimated_amount)

Existing M32 plan shadow (after legacy result)
 facts + eligibility + avg-cost/amount-only evidence
    └─> PriceObservation (incomplete/reference)
    └─> NormalizedTradeInput (incomplete)
    └─> M32.2 TradeLeg diagnostic
```

The target **live shadow** graph is:

```text
Market Data canonical quote envelope (missing)
  -> ExecutionPriceObservation (adapter exists; live call missing)
  -> PriceFreshnessAssessment (assessor exists; explicit assessment instant missing)
  -> ExecutionPolicyBundle (exists; supplied by orchestration)
  -> constrained quantity from allocation/holding evidence (pure helper exists)
  -> facts-backed FeeQuote after final quantity (exists; orchestration missing)
  -> policy-produced NormalizedTradeInput (exists)
  -> ExecutionTradeLeg.build_from_policy_input() (exists)
  -> private Shadow Canonical Plan diagnostic (missing)
```

### Missing edges

1. **Provider → canonical quote envelope:** the provider interface and cache
   facade discard exchange observation time, session, currency, provider
   version, delay, and cache-write time.
2. **Quote envelope → observation:** M32.3C adapters exist but are not invoked
   from a live execution orchestration boundary with Registry identity.
3. **Observation → assessment:** no execution-plan caller supplies one explicit
   assessment instant and an approved shadow freshness policy for live quotes.
4. **Plan intent/holding → policy:** allocation values and holdings exist, but
   their immutable per-run source/snapshot/currency evidence is not assembled.
5. **Constrained quantity → FeeQuote:** no plan orchestration quotes the final
   quantity through `quote_fee_for_instrument()`.
6. **Complete inputs → plan diagnostic:** no private container aggregates
   policy results, legs, exclusions, residuals, and plan-level non-authoritative
   evidence.

## 3. Execution evidence inventory

`READY` means the field/contract is usable at its current owner boundary, not
that it is sufficient for canonical planning.

| Input | Current owner and runtime availability | Immutable contract already exists | Missing work | Classification |
| --- | --- | --- | --- | --- |
| Price | Yahoo Chart raw `meta.regularMarketPrice`; public quote DTO exposes `current_price`; yfinance public quote is latest history `Close` | `ExecutionPriceObservation` | Preserve a canonical Chart market-last payload through provider/facade; do not treat yfinance close as `MARKET_LAST` | ADAPTER_REQUIRED |
| Observation timestamp | Chart raw `meta.regularMarketTime`; history DataFrame index supplies bar time; quote DTO drops both for current quote | Observation `observed_at` | Carry raw exchange time in a canonical quote envelope; a history-bar adapter cannot make a daily close a market-last quote | ADAPTER_REQUIRED |
| Receipt timestamp | Both quote providers create `last_updated` after fetch; public DTO/cache payload retains it | Observation `received_at` | Name it explicitly as receipt time in the envelope; never promote it to observed time | ADAPTER_REQUIRED |
| Cache timestamp | `MarketDataCache.fetched_at` exists; `fetch_price_info()` returns payload only | Observation `cached_at` | Return cache provenance/fetched time with a cache read or expose a read-only envelope adapter | ORCHESTRATION_REQUIRED |
| Session | Chart `meta` can contain market state, but public DTO discards it; current adapters map supplied values | `MarketSession` | Preserve raw state and define provider-field translation at Market Data boundary; unknown remains incomplete | ADAPTER_REQUIRED |
| Currency | Asset Registry has listing currency; current Yahoo quote DTO normally omits payload currency | Observation and planning context fields | Preserve provider-reported currency; Registry currency may validate, never substitute for payload currency | ADAPTER_REQUIRED |
| Delay | Chart metadata may expose delay; public DTO omits it; no policy consumes it in v1 | Observation `delay` | Preserve when provider supplies it; no execution decision uses it in E2 | OUT_OF_SCOPE |
| Provider identity/version | Provider selection exists (`PRICE_PROVIDER`), provider class is known; no quote payload retains selected name/version | Observation provider fields | Emit provider ID/version in the canonical quote envelope | ADAPTER_REQUIRED |
| Registry identity/tradability | Batch Registry facts resolver at session-owning boundaries; shadow wrapper uses rollback savepoint | `ExecutionInstrumentFacts`, `ExecutionEligibility` | Reuse one batch result in E2; no resolver inside pure policy helpers | READY |
| Lot size | `Asset.lot_size` → `AssetView` → facts | Facts field | Read-only readiness check and governed data remediation where null/invalid; no default lot of one | REGISTRY_REQUIRED |
| Fractional capability | `Asset.fractional_support` → facts | Facts field | Read-only readiness check; v1 accepts exactly `False`, not missing/default assumptions | REGISTRY_REQUIRED |
| Holding quantity | `PortfolioItem.shares` is loaded by execution plan; current shadow makes a snapshot with no timestamp | `HoldingQuantitySnapshot` | Build an immutable snapshot at the plan boundary with loaded-row identity, explicit capture time, source, and currency context; do not query from pure adapters | ORCHESTRATION_REQUIRED |
| Requested allocation | Position sizing returns `suggested_pct`; execution plan derives `estimated_amount` from legacy total value | `NormalizedTradeInput.requested_value` and source vocabulary | Bind value to a frozen recommendation/plan reference and explicit currency; do not alter legacy gross amount | ORCHESTRATION_REQUIRED |
| Portfolio cash / NAV | `Portfolio.cash_balance` and cost-basis `avg_cost × shares` are available; no base-currency column | transitional `PlanningCurrencyContext` only | A private THB transitional context can be supplied for shadow; authoritative portfolio-currency ownership is still absent | ORCHESTRATION_REQUIRED |
| Portfolio currency | Transaction defaults and Registry/fee schedule often use THB; `Portfolio` has no base/valuation currency | `PlanningCurrencyContext` | Do not infer from transaction default or exchange rate; later Portfolio-domain ownership required for canonical plan | POLICY_REQUIRED |
| Fee quote | `quote_fee_for_instrument()` is pure and facts-backed; legacy writes use `quote_transaction_fee_compat()` | `FeeQuote` | Create only after final quantity/price, using explicit quote/effective instants; no compatibility quote reuse | ORCHESTRATION_REQUIRED |
| Assessment timing | M32.3C assessor accepts caller-supplied `assessed_at`; current execution-plan shadow creates one local `datetime.now()` only for descriptive diagnostics | `PriceFreshnessAssessment` | Capture one orchestration instant per live-shadow run and pass it to pure assessment/quote assembly | ORCHESTRATION_REQUIRED |
| Execution policy | M32.3E1 bundle and pure sizing/lifecycle rules exist | `ExecutionPolicyBundle` and results | Supply a reviewed shadow bundle explicitly; no new price/session/FX/lot policy is needed in E2 | READY |
| Policy input / leg | Normalizer and `build_from_policy_input()` exist | `NormalizedTradeInput`, `ExecutionTradeLeg` | Aggregate outcomes privately without replacing `ExecutionPlanResult` | ORCHESTRATION_REQUIRED |

## 4. Provider ownership

### Yahoo Chart (preferred live-evidence source)

`services/market_data/yahoo_chart.py` owns raw Chart retrieval.  Its raw
response already contains the provider metadata from which an execution quote
envelope can be built.  Its existing `get_quote()` implementation reduces that
response to a presentation DTO at the provider boundary.  M32.3E2 should add a
new additive method or adapter owned by Market Data, not change the semantics
of `get_quote()` or teach Execution Planning to inspect Yahoo JSON.

Required envelope fields, each copied only when Yahoo supplies it:

- requested/provider symbol and provider ID/version;
- `regularMarketPrice` as the candidate market-last value;
- `regularMarketTime` as exchange observation time;
- market-state/session and provider currency;
- provider delay and exchange timezone where present; and
- receipt time captured by Market Data at the fetch boundary.

The envelope must represent absence explicitly.  It must not manufacture an
exchange time from local receipt time, cache-write time, price-bar index, or
`datetime.now()` in a pure adapter.

### Yahoo Finance / history

The yfinance-backed provider returns the latest `Close` and a locally created
receipt timestamp.  It is useful analysis evidence but does not satisfy the
M32.3E1 exact `MARKET_LAST` policy.  Timestamped history bars can be adapted
through `adapt_yahoo_history_bar()` for diagnostics, but bar selection and
`MARKET_CLOSE` are not a substitute for the required live market-last path.

No provider fallback/ranking belongs in execution policy.  M32.3E2 should
record the configured provider and produce typed incomplete evidence when the
selected Market Data owner cannot supply a complete Chart quote.

### Cache

`MarketDataCache` owns only cache-write/fetch and expiry metadata.  Its five
minute quote TTL is not price freshness and must not become a policy threshold.
The E2 read adapter may expose `fetched_at` as `cached_at` provenance, but it
must preserve provider observation/receipt fields independently and never
turn cache freshness into `PriceFreshnessAssessment.CURRENT`.

## 5. Registry ownership

The Registry is already the exclusive owner of execution identity and listing
capabilities:

```text
Asset / AssetIdentifier / AssetRelationship / AssetClassification
  -> registry_lookup.AssetView
  -> ExecutionInstrumentFacts
  -> ExecutionEligibility
```

`Asset.currency`, `Asset.tradable`, `Asset.fractional_support`, and
`Asset.lot_size` are projected by `registry_lookup.AssetView` and then facts.
M32.3E2 must resolve the union of BUY and active funding symbols once through
the existing batch/shadow facts adapter and retain that exact facts object
through observation, eligibility, fee quote, normalized input, and leg.

Registry is not the owner of provider-payload currency, price timestamp,
session, price, quote time, or portfolio holding amount.  It may validate
currency/identity; it must not backfill them.

**Readiness gate:** a symbol with `lot_size=None`, non-positive/non-integral
lot evidence, or non-false fractional capability becomes a typed incomplete
policy result.  This is a Registry coverage issue, not a runtime heuristic or
an E2 Registry-remediation task.

## 6. Policy ownership

M32.3E1 already owns the approved v1 *evaluation* rules.  E2 must call, not
extend, them:

- `select_execution_price()` accepts one identity/currency-matched
  `MARKET_LAST` observation;
- `accept_freshness_and_session()` accepts only the supplied policy's
  `CURRENT` and `REGULAR` outcome;
- `derive_requested_quantity()`, `constrain_executable_quantity()`, and
  `calculate_execution_residual()` own pure sizing/lot/residual mechanics;
- `validate_fee_quote_lifecycle()` binds the post-constraint quote to the
  selected evidence; and
- `normalize_policy_trade_input()` assembles the typed result.

E2 must not add a provider preference, a cache TTL rule, price fallback,
currency conversion, broker capability inference, cash-reserve policy,
fractional increment, or partial-funding policy.  A reviewed immutable
`ExecutionPolicyBundle` and transitional THB planning context are inputs to
the orchestration adapter, not configuration reads inside pure helpers.

## 7. Provider adapter inventory

| Adapter | Input → output | Owner / purity | Rollback risk |
| --- | --- | --- | --- |
| `YahooChartExecutionQuoteAdapter` | Already-loaded Chart result + Market Data receipt instant → immutable provider quote envelope | Market Data; translation-only, no Registry/DB/policy/clock reads | Low: new consumer only; legacy `get_quote()` stays unchanged |
| `CachedExecutionQuoteAdapter` | Cache row/payload plus cache `fetched_at` → same envelope with `cached_at` | Market Data/cache orchestration; DB read occurs outside the pure envelope builder | Low: diagnostic provenance only; expiry is not used as freshness |
| `ExecutionQuoteObservationAdapter` | One envelope + already-resolved facts → `ExecutionPriceObservation` via existing M32.3C adapter | Execution evidence boundary; pure transformation | Low: typed incomplete output on missing data |
| `ExecutionFreshnessAdapter` | Observation + explicit per-run assessment instant + supplied policy → `PriceFreshnessAssessment` | Execution-plan orchestration calls existing pure assessor | Low: isolated shadow outcome only |
| `PortfolioHoldingSnapshotAdapter` | Already-loaded `PortfolioItem` + explicit capture instant/currency/source → `HoldingQuantitySnapshot` | Portfolio/execution-plan orchestration; no DB access inside adapter | Low: diagnostic-only; legacy `FundingAction` remains unchanged |
| `ExecutionPlanIntentAdapter` | Legacy `BuyAction.estimated_amount` / active funding action plus frozen plan/recommendation reference → quantity-source inputs | Execution-plan orchestration; pure after rows/actions are loaded | Low: preserves values; no legacy plan rewrite |
| `FactsBackedQuoteAdapter` | Facts + final constrained quantity + selected observation + explicit quote/effective instant → `quote_fee_for_instrument()` result | Fee-domain call at orchestration boundary; pure fee selection/calculation | Low: unavailable quote leaves diagnostic incomplete, never free |
| `ShadowCanonicalPlanAdapter` | Per-symbol policy results/legs/residuals → private structured log diagnostic | Execution Plan; no response/persistence mutation | Low: whole block exception-contained and removable |

No adapter may resolve Registry identity, perform a provider request, use a
symbol regex, select a history bar, read system time, or calculate an
alternative fee.  Network and database work belong in named orchestration
steps; all evidence translation and policy evaluation remains pure.

## 8. Missing orchestration

### Recommended integration point: `execution_plan.py`

Use the existing post-result M31/M32 shadow block in
`build_execution_plan()` as the only E2 live-shadow caller.  It already has:

- a legitimate database session;
- the target portfolio, its cash, and loaded `PortfolioItem` rows;
- requested BUY values (`BuyAction.estimated_amount`);
- active funding actions and their quantities/fractions;
- one batch Registry facts resolution and eligibility map; and
- an exception-contained diagnostic convention that does not change the
  returned `ExecutionPlanResult`.

The new shadow must occur after the legacy result is created in E2.  This is
not the final canonical insertion point; it is intentionally too late to
affect gross funding arithmetic, response status, persistence, or action
selection.

### Why not optimizer

The optimizer obtains current-price presentation values through
`fetch_price_info()` and has a facts batch at its main orchestration boundary,
but it creates investment recommendations and target allocations, not a
complete holding/funding trade set.  It is the wrong first owner for a
plan-level canonical shadow and must not gain a second market-data execution
adapter.

### Why not Decision Workspace

Decision Workspace/position-sizing outputs allocation percentages and values,
not a complete executable side/price/quantity/fee/holding set.  It remains a
source of amount intent.  It should consume E2 diagnostics only in a later,
explicit API/frontend milestone, not create execution evidence itself.

### Why not `portfolio_transactions.py`

Transaction services receive explicit user shares and price and commit ledger
effects.  They currently use `quote_transaction_fee_compat()` at admission
time.  Adding a live canonical planner there would mix plan evidence with
write semantics and would violate the E2 shadow-only scope.  A later
transaction-admission milestone can re-quote/revalidate a selected policy leg
using the lifecycle contract.

## 9. Shadow execution sequence

1. Build the unchanged legacy `ExecutionPlanResult` and its existing funding
   arithmetic.
2. Build one deduplicated symbol set from active BUY and active funding actions.
3. Reuse the existing rollback-safe one-batch Registry facts resolver and
   derive eligibility once.
4. At a Market Data orchestration boundary, fetch or read one canonical quote
   envelope per symbol in a bounded batch.  Capture one explicit receipt time
   per provider response and one explicit `assessed_at` for the shadow run.
5. Adapt each envelope with its exact facts object into
   `ExecutionPriceObservation`; retain `cached_at` only as cache provenance.
6. Assess freshness with the supplied E2 shadow policy.  Missing observed time,
   session, or provider currency produces typed incompleteness.
7. Convert each BUY amount into a policy request and each active funding action
   into a holding snapshot/fraction or full-holding request.  Preserve source
   references and all original values.
8. Run the E1 pure price/sizing/lot helpers.  Only when a final constrained
   quantity exists, call `quote_fee_for_instrument()` with explicit
   `quoted_at`/`effective_at` equal to the relevant orchestration instant.
9. Call `normalize_policy_trade_input()` and, only when complete, call
   `ExecutionTradeLegBuilder.build_from_policy_input()`.
10. Emit one structured private `ShadowCanonicalPlan` diagnostic containing
    complete legs, typed exclusions/deferred/incomplete results, fee quote
    references, residuals, and evidence provenance.  Do not return, persist,
    fund, execute, or use it to alter the legacy plan.
11. Catch failures around the whole shadow path and return the untouched legacy
    result.

The live shadow must batch market-data requests.  It must not use the current
per-symbol `fetch_price_info()` presentation loop, cache-miss N+1 lookups, or
the optimizer's provider-normalization heuristics as an execution identity
source.

## 10. Canonical readiness matrix

| Requirement | Readiness | Evidence / blocker |
| --- | --- | --- |
| Registry facts and eligibility | Partial | Contract/path ready; supported-universe resolution and capability coverage remain an M31 Registry gate |
| Live canonical `MARKET_LAST` | No | Raw Yahoo Chart data is reduced before it reaches execution; yfinance exposes close rather than market last |
| Observation and receipt time | No | Receipt can be retained; observation time is currently dropped from public quote DTO |
| Session and provider currency | No | Possible raw provider metadata but not retained in runtime quote DTO/cache payload |
| Cache provenance separation | No | `fetched_at` exists but the cache facade returns payload only; TTL must remain non-policy |
| Facts-backed FeeQuote | Conditional | Ready once final quantity/price/time evidence is complete; no plan orchestration creates it |
| Holding quantity | Partial | Shares are available; immutable snapshot time/currency/source are not assembled |
| Value intent | Partial | Allocation value exists after legacy plan; no frozen currency/recommendation identity contract at that boundary |
| Lot/fraction capability | No proof | Fields exist but current data coverage is not established and no defaults are allowed |
| Portfolio/base currency | No | `Portfolio` lacks a base/valuation currency; only transitional THB context can support a diagnostic |
| Net funding/reserve | No | Current execution plan is gross/cost-basis; E2 cannot alter funding or cash arithmetic |
| Plan-level canonical projection | No | No response/persistence/history contract, exclusion semantics, or rollout policy |
| Transaction re-quote/admission | No | Writes use compatibility quote path; M31 enforcement and transaction policy are separate work |

**Can policy-generated `NormalizedTradeInput` become live today?** No.  A
fixture can make it complete, but the normal production path cannot supply all
required identity-bound `MARKET_LAST`, exchange observation time, known regular
session, provider payload currency, final lot-ready quantity, facts-backed
quote, and typed portfolio-currency evidence without the E2 plumbing and
coverage gates.

## 11. Remaining blockers

1. Additive Market Data quote-envelope API that preserves raw Chart metadata
   without changing the legacy DTO contract.
2. Explicit canonical-provider selection at the Market Data boundary; neither
   execution policy nor plan code may select between Chart and yfinance.
3. Cache read provenance (`fetched_at`) must accompany, not overwrite, provider
   observation/receipt evidence.
4. Read-only Registry capability preflight must demonstrate valid positive
   lots and v1 fractional support for each candidate shadow symbol.
5. A Portfolio Runtime adapter must produce timestamped, currency-scoped
   holding/cash evidence from already-loaded rows.
6. A frozen amount-intent reference/currency must be carried from position
   sizing/plan request into the diagnostic.
7. E2 must batch provider evidence and facts and define bounded timeout/error
   handling that yields typed incomplete evidence rather than an execution
   fallback.
8. Shadow diagnostic schema/log retention must be reviewed before relying on
   coverage metrics; it may not introduce persistence in this milestone.
9. Canonical plan remains blocked by net-of-cost funding, cash floor, base
   currency/FX, plan projection/API/history, M31 enforcement, and transaction
   re-quote/admission work.  None belongs in E2.

## 12. Recommended Terra implementation scope

Implement only the following named, independently testable slice:

1. **Market Data evidence envelope:** an additive typed DTO and Chart adapter
   for already-loaded raw result plus explicit receipt/cache provenance.  Keep
   all legacy `get_quote()` and `fetch_price_info()` shapes unchanged.
2. **Read-only batch evidence orchestrator:** fetch/obtain the envelope once
   per active plan symbol set, adapt it to M32.3C observations with existing
   facts, and assess freshness from one caller-owned instant.
3. **Plan intent/snapshot adapter:** translate already-loaded BUY values and
   active funding holdings into immutable policy inputs; do not alter legacy
   amount, funding, or cash calculations.
4. **Private policy/quote/leg shadow:** run E1 helpers and
   `quote_fee_for_instrument()` only after final constrained quantity; collect
   typed results in an exception-contained structured diagnostic.
5. **Read-only readiness and tests:** prove no N+1 Registry/provider calls,
   no provider/clock/database access in pure adapters, no fallback from missing
   evidence, and byte-equivalent legacy plan output when every new component
   fails.

Do **not** include a provider replacement, cache schema/migration, Registry
remediation, portfolio currency model, fee-schedule redesign, net funding,
execution-plan API field, frontend display, transaction guard, persistence, or
canonical-plan cutover.

## 13. Implementation order

1. Define the additive Market Data quote envelope and tests using recorded raw
   Chart metadata, including every absent-field case.
2. Add read-only cache/provenance adaptation and tests proving cache TTL is not
   freshness policy.
3. Add a bounded batch execution-evidence orchestrator, with Registry facts
   supplied rather than resolved inside pure transformation helpers.
4. Add Portfolio Runtime holding/cash and plan-value intent adapters using
   preloaded data only.
5. Add the post-result `execution_plan.py` shadow, facts-backed quote step,
   and private aggregate diagnostic.
6. Add integration tests for complete evidence, each typed incomplete edge,
   quote invalidation, registry failure, provider failure, cache fallback,
   batch behavior, and unchanged legacy result serialization.
7. Run a non-production observation window and review completeness/deferral
   rates before considering any M32.3F canonical-plan design.

## 14. Go / No-Go

| Decision | Result | Basis |
| --- | --- | --- |
| M32.3E2 live-evidence shadow implementation | **GO, narrowly scoped** | Existing contracts isolate policy; execution plan offers a session-owning, post-result, exception-contained diagnostic boundary |
| Live policy-produced normalized inputs as private diagnostics | **GO after E2 adapters** | They can remain typed incomplete when runtime evidence is absent and cannot affect legacy results |
| Canonical execution-plan adoption | **NO-GO** | Required provider evidence, Registry capability coverage, currency ownership, net funding, and admission/rollout contracts are absent |
| Transaction write integration | **NO-GO** | It currently owns ledger writes and compatibility fees, not planning evidence or canonical re-quote policy |

M32.3E2 implementation can therefore proceed safely **only** as the specified
non-blocking, non-persistent, post-result shadow integration.  It must remain
removable behind the existing shadow-style diagnostic boundary and may not
promote any missing evidence to a fallback value.

## 15. Verification record

### Audited implementation files

- `backend/services/market_data/base.py`
- `backend/services/market_data/provider.py`
- `backend/services/market_data/yahoo_chart.py`
- `backend/services/market_data/yahoo.py`
- `backend/services/data_fetcher.py`
- `backend/models/database.py`
- `backend/models/asset.py`
- `backend/services/registry_lookup.py`
- `backend/services/execution_instrument_facts.py`
- `backend/services/execution_eligibility.py`
- `backend/services/execution_eligibility_shadow.py`
- `backend/services/execution_price_observation.py`
- `backend/services/execution_policy.py`
- `backend/services/normalized_trade_input.py`
- `backend/services/execution_trade_leg.py`
- `backend/services/broker_fees.py`
- `backend/services/broker_fees_compat.py`
- `backend/services/execution_plan.py`
- `backend/services/position_sizing.py`
- `backend/services/optimizer/execution_penalty.py`
- `backend/services/optimizer/execution_optimizer.py`
- `backend/services/portfolio_transactions.py`
- `backend/agents/optimizer.py`
- `backend/main.py`
- `docs/implementation/M32_3D_execution_policy_design.md`
- `docs/implementation/M32_3E1_execution_policy_shadow.md`

### Dependency conclusions checked

- M32.3C adapters accept already-loaded evidence and do not fetch provider or
  Registry data.
- M32.3E1 policy helpers accept explicit facts, eligibility, observations,
  assessment, planning currency, and quote; they do not read a clock or select
  a provider/schedule.
- The live execution-plan shadow currently resolves facts once after the
  immutable legacy result, then projects only incomplete amount/average-cost
  evidence.
- Fee quotes bind exact quantity, price, currency, schedule version, and
  explicit times, while transaction writes still use the deliberately isolated
  compatibility quote path.
- `PortfolioItem` supplies shares and cost basis, and `Portfolio` supplies
  scalar cash, but neither provides a canonical portfolio currency or live
  price evidence.

No production implementation was changed by this audit.  No commit or push
was performed.
