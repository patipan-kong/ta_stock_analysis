# M32.3C — Canonical Price Observation and Freshness Foundation

**Date:** 2026-07-15

**Status:** Implemented as shadow-only evidence foundation. No execution-price
policy or canonical execution-plan behavior is enabled.

## Scope and outcome

M32.3C introduces one immutable `ExecutionPriceObservation` contract and a
separate immutable `PriceFreshnessAssessment`. The observation records what a
provider or caller supplied. It does not decide whether that value should be
used for sizing, fee quoting, funding, transaction admission, or execution.

The implementation changes no provider request, cache, optimizer result,
execution-plan result, transaction, ledger, API, frontend, persistence model,
M31 cutover mode, or M32 plan mode. Its only orchestration use is a private
post-result execution-plan diagnostic inside the existing exception-contained
shadow block.

## Contract

`backend/services/execution_price_observation.py` owns the versioned frozen
contract. It retains:

- deterministic `observation_ref` and contract version;
- requested symbol plus caller-supplied Registry asset/canonical identity;
- exact `Decimal` observed price and currency when present;
- semantic price kind and source;
- provider and provider version when supplied;
- distinct `observed_at`, `received_at`, and `cached_at` values;
- market session, exchange timezone, and reported delay when present;
- timestamp quality, overall evidence quality, warnings, and provenance.

The builder is pure and performs no Registry lookup. Asset identity values are
copied only from explicit caller inputs. Missing values stay `None`; no symbol,
venue, currency, session, or timestamp inference exists.

The canonical price-kind vocabulary is:

- `MARKET_LAST`
- `MARKET_CLOSE`
- `MARKET_OPEN`
- `MARKET_HIGH`
- `MARKET_LOW`
- `USER_EXECUTION_TERM`
- `AVG_COST_REFERENCE`
- `ESTIMATED`
- `UNKNOWN`

`MARKET_REFERENCE` remains only as an alias for `MARKET_LAST` so existing
M32.3B request construction continues to work; it is not another wire value.
No M32.3C adapter emits the alias name.

Only the market kinds are structurally capable of being market-price evidence.
`USER_EXECUTION_TERM`, `AVG_COST_REFERENCE`, `ESTIMATED`, and `UNKNOWN` are
reference-only or incomplete. In particular, a positive average cost with a
currency is still not a market observation and cannot make a normalized trade
input complete.

## Timestamp ownership audit

| Existing source | Timestamp actually available | M32.3C treatment |
| --- | --- | --- |
| `YahooChartProvider.get_quote()` | `last_updated` is generated with `datetime.now()` after the HTTP request. The raw Chart payload can contain `regularMarketTime`, but the current DTO drops it. | Current DTO `last_updated` is `received_at`; `observed_at` remains absent. A richer already-loaded payload may preserve an explicit `regularMarketTime`, but the adapter never creates one. |
| `YahooProvider.get_quote()` | Latest `Ticker.history()` row has an index, but the returned quote DTO drops it and generates `last_updated` after the fetch. | Current DTO `last_updated` is `received_at`; `observed_at` remains absent. The price is labeled `MARKET_CLOSE` because the provider reads `Close`. |
| Yahoo history DataFrames | UTC-capable DataFrame index from provider timestamps. | `adapt_yahoo_history_bar()` preserves a caller-selected bar time as `observed_at`. It does not select the row or price column. |
| `MarketDataCache.fetched_at` | DB cache-write/fetch time. | It may be supplied as `cached_at`; it never becomes observation or receipt time. M32.3C does not query the cache. |
| `MarketDataCache.expires_at` / stale annotations | Cache policy and fallback evidence. | Not a market observation timestamp. Existing cache behavior is unchanged. |
| `AgentCache.cached_at` | Analysis-result cache write time. | Not price observation evidence. |
| FeeQuote `quoted_at` / `effective_at` | Fee assembly and schedule-applicability times. | Never used as price time. FeeQuote is unchanged. |
| Transaction date / creation time | Ledger event date and platform knowledge time. | Never used as a market observation. |
| Portfolio `avg_cost` | Accounting cost basis with no market-observation time. | `AVG_COST_REFERENCE`, reference-only, with absent observation time. |

This distinction exposes an existing limitation rather than hiding it: current
quote DTOs generally have receipt time but no exchange observation time.

## Session, currency, delay, and quality ownership

Market session is provider evidence. Adapters translate explicit known values
such as regular, pre-market, after-hours, or closed. When the current DTO does
not carry session, it remains `UNKNOWN`. M32.3C does not consult a trading
calendar.

Currency is also observation-source evidence. Registry facts establish the
listing currency for identity and fee schedule selection, but they do not prove
the currency of a provider payload. The price adapters therefore retain only
an explicit payload/caller currency. Current quote DTOs normally omit it, so
their observation currency remains absent. Normalized input validates that the
observation currency matches FeeQuote currency when both are used.

Delay and exchange timezone remain absent unless the source supplies them.
No venue-based default is added.

Timestamp quality is one of `EXCHANGE_OBSERVED`, `PROVIDER_BAR`,
`RECEIPT_ONLY`, `MISSING`, or `UNKNOWN`. Overall observation quality is
`COMPLETE`, `PARTIAL`, `REFERENCE_ONLY`, or `UNKNOWN`. Quality reports evidence
completeness; it is not an execution-pricing decision.

## Provider adapters

The pure adapters are:

- `adapt_yahoo_chart_quote()`;
- `adapt_yahoo_finance_quote()`;
- `adapt_yahoo_history_bar()`;
- `adapt_user_execution_term()`; and
- `adapt_avg_cost_reference()`.

They translate already-loaded values only. They do not import the provider
implementations, perform HTTP requests, touch the cache or ORM, select a
history bar, resolve identity, read a clock, or change provider behavior.

For backward compatibility, current quote `last_updated` is parsed as receipt
time and receives a warning explicitly saying it is not observation time. If
neither explicit observation nor receipt time exists, all timestamp fields
remain absent.

## Freshness model

Freshness is not stored on `ExecutionPriceObservation`. The pure
`assess_price_freshness()` function accepts exactly:

1. an immutable observation;
2. an explicit immutable `PriceFreshnessPolicy`; and
3. a caller-supplied `assessed_at`.

It never reads the system clock. The result records a deterministic
`assessment_ref`, policy version, assessment time, status, computed age,
reason, and warnings.

Supported statuses are `UNKNOWN`, `CURRENT`, `STALE`, `EXPIRED`,
`SESSION_CLOSED`, `PRICE_TIMESTAMP_MISSING`, `SESSION_UNKNOWN`, and
`CURRENCY_UNKNOWN`. Non-market kinds receive `UNKNOWN`. Missing currency,
observation time, or session stays explicit. A future observation or
incomparable datetime also produces `UNKNOWN` rather than a corrected time.

The included `m32.3c-shadow-v1` policy uses five minutes for `CURRENT` and
fifteen minutes as the upper stale threshold. It exists only to make shadow
diagnostics repeatable. It is not an approved execution-price acceptance
policy and does not enable canonical planning.

## NormalizedTradeInput integration

`NormalizedTradeInput` now owns price evidence only through retained
`ExecutionPriceObservation` and `PriceFreshnessAssessment` objects. Both are
reused by object identity. Read-only `unit_price`, `price_kind`, `price_source`,
timestamp, session, stale, and currency properties preserve M32.3B caller/test
compatibility without creating duplicate authority.

`TradeInputNormalizationRequest` temporarily accepts the original M32.3B raw
fields. When no M32.3C observation is supplied, the normalizer projects those
exact fields into a compatibility observation and supplied freshness record;
it adds no data and labels that provenance. New callers supply the two M32.3C
contracts directly, which take precedence over raw compatibility inputs.

A normalized input remains incomplete unless its retained evidence establishes
a positive market-kind price, observation and receipt times, known session,
currency, a matching `CURRENT` freshness assessment, resolved facts,
eligibility, valid quantities, and a matching successful FeeQuote. Average
cost and user terms remain incomplete even when positive.

## Shadow integration

After the legacy `ExecutionPlanResult` and the existing M31/M32.2 diagnostics
already exist, M32.3C projects:

- a BUY action as `UNKNOWN`, because it contains amount but no unit price;
- an active SELL/REDUCE action's balancing price as `AVG_COST_REFERENCE`,
  because legacy funding arithmetic originates in `avg_cost × shares`.

The diagnostic records legacy/reference price, price kind, timestamp quality,
freshness status, and provider. The same observation/assessment objects are
passed into the M32.3B normalized-input shadow projection. Average-cost
observations therefore remain explicitly incomplete. The projection is logged
only, not returned or persisted, and any failure returns the unchanged legacy
plan.

`ExecutionTradeLegBuilder` still accepts only `LegacyExecutionTradeRequest`.
M32.3C does not change its behavior or make trade legs canonical.

## Observable invariants

- Provider network, retry, payload, and cache behavior is unchanged.
- No exchange timestamp, session, currency, timezone, or delay is invented.
- Provider fetch time remains distinct from observation time.
- Cache-write time remains distinct from both.
- Average cost never satisfies market/execution price evidence.
- FeeQuote timestamps never supply missing price timestamps.
- `NormalizedTradeInput` retains the exact observation and assessment objects.
- Execution-plan output is byte-equivalent when the M32.3C shadow fails.
- FeeQuote and ExecutionTradeLeg contracts/builders are unchanged.
- Optimizer, transactions, ledger/replay, APIs, frontend, persistence, M31
  enforcement, and canonical plan modes are unchanged.

## M32.3D dependencies and blockers

M32.3D cannot size or publish canonical legs until the following are approved
and supplied:

1. a market-data orchestration path that carries provider observation time,
   receipt time, cache time, currency, session, timezone, and delay without
   dropping them;
2. venue/session-specific freshness policies, including closed-market and
   delayed-quote treatment;
3. an explicit decision on whether any user execution term may be used for
   planning and, if so, under what non-market policy;
4. authoritative value-to-quantity conversion price selection;
5. portfolio/base currency ownership and FX observation/freshness contracts;
6. lot, fractional, residual, and cash-floor policies;
7. quote expiry/requote behavior binding FeeQuote to the selected price and
   executable quantity; and
8. a canonical execution-plan projection and rollout contract.

Until then, `CURRENT` describes freshness under a supplied policy; it does not
mean approved for execution.

## Explicit non-goals

M32.3C implements no quantity sizing, lot policy, FX, funding change,
canonical plan, optimizer change, transaction admission, ledger change,
frontend/API field, persistence model, migration, ExecutionIntent, M31
enforcement, compatibility retirement, provider behavior change, market-data
fetch, or authoritative execution price.

## Verification

Focused tests cover immutable/deterministic observations and assessments,
provider observation-versus-receipt preservation, absent timestamps, history
bar timestamps, average-cost reference behavior, all freshness outcomes,
missing currency, normalized object reuse, unchanged FeeQuote/TradeLeg/plan
behavior, and static dependency boundaries.

Results:

- focused M32.3C: **21 passed**;
- M32.1/M32.2/M32.3B/M32.3C: **77 passed**;
- stable market-data tests: **25 passed, 32 skipped**;
- combined M32, market-data, price-matrix, and position-sizing group:
  **114 passed, 32 skipped**;
- M31 facts/eligibility/Registry integration: **83 passed**;
- optimizer/execution group: **53 passed**. Four existing
  `test_optimizer_pipeline.py` tests still call `_consensus_engine(l2, l3)`
  without its required leading argument. Five optimizer-history tests still
  fail in isolated import order because the Registry Asset mapper is absent;
  all **5 passed** when `models.asset` was imported first;
- transaction/write/replay group: **214 passed**. Nine async replay-cutover
  tests cannot run because this environment lacks an async pytest plugin, and
  the existing capability-shadow BUY test still expects a baseline log event
  that production does not emit.

`tests/test_fetch_history.py` is an import-time live-network probe rather than
an isolated pytest test. Collection failed at `df.shape` when the external
fetch returned `None`; no M32.3C code is imported by that probe. The stable
Yahoo Chart unit tests passed.

Python syntax compilation and `git diff --check` pass. No commit or push was
performed.
