# M32.3E2 — Live Evidence Shadow Integration

**Date:** 2026-07-15

**Status:** Implemented as a default-off, post-result, non-authoritative execution-plan shadow. Canonical execution planning remains **NO-GO**.

## Scope and decision

M32.3E2 wires existing M31/M32 contracts to live Market Data evidence without changing any returned `ExecutionPlanResult`, funding arithmetic, optimizer result, transaction, ledger entry, API, persistence model, Registry record, or frontend payload. The shadow is enabled only when `M32_LIVE_EVIDENCE_SHADOW=ON`; absent or invalid values safely leave it off. Disabling it restores the previous behavior without a schema or data change.

## Quote envelope and evidence ownership

`services.market_data.execution_quote.ExecutionQuoteEnvelope` is an immutable, versioned Market Data contract. It carries the requested/provider symbol, provider identity/version, candidate price and kind, provider currency, exchange observation time, provider receipt time, cache time, session, timezone, delay, warnings, and provenance.

Pure envelope adapters never read a clock, fetch a provider, inspect Registry data, access a cache/database, or evaluate policy. Missing evidence remains missing. Receipt/cache time never becomes observation time and Registry currency is never substituted for a missing provider payload currency.

`YahooChartProvider.get_execution_quote_envelope(s)` is an additive path that preserves `regularMarketPrice`, `regularMarketTime`, market state, currency, timezone, and delay from the already-loaded Chart `meta` payload. It captures receipt time at the provider I/O boundary. Existing `get_quote()` and `fetch_price_info()` dictionaries are unchanged. The legacy yfinance path is adapted only as `MARKET_CLOSE` with missing exchange observation evidence; it is never promoted to `MARKET_LAST`.

`adapt_cached_execution_quote()` accepts a supplied `MarketDataCache.fetched_at` value only as `cached_at` provenance. Cache expiry/TTL is not a freshness rule, and M32.3E2 adds no cache read/write behavior or schema change.

## Bounded orchestration

`services.execution_live_evidence_shadow.collect_live_execution_quote_evidence` deduplicates active plan symbols and makes at most one evidence attempt per symbol. A provider exposing `get_execution_quote_envelopes()` is called once for the complete bounded set. Providers without that method use a fixed-size five-worker executor and are capped at 25 symbols. Provider exceptions, empty responses, bound overflow, and malformed evidence become per-symbol typed missing evidence and cannot escape the shadow.

Registry facts and eligibility are supplied by the existing M31 one-batch plan shadow resolution; the E2 service never performs a second Registry lookup. One caller-owned `assessed_at` instant is passed to every freshness assessment and fee quote in the run.

## Holding and intent adapters

The pure plan adapters preserve only already-loaded evidence:

- BUY actions retain `BuyAction.estimated_amount` as amount intent. Units are derived only by the existing M32.3E1 policy after accepted live evidence.
- SELL/REDUCE actions retain their explicit `release_pct` and use either the full-holding or holding-fraction source. They never reconstruct an unstated reduction policy.
- `HoldingQuantitySnapshot` is built from the plan's loaded `PortfolioItem` with a caller-supplied capture instant. `avg_cost` is not price evidence.

The transitional planning context is explicitly THB for this private shadow; this does not establish a Portfolio base/valuation-currency model.

## Shadow sequence and diagnostic

After `build_execution_plan()` has finalized the legacy result, its existing exception-contained block may opt into this sequence:

1. Reuse the one-batch facts/eligibility map and deduplicate active actions.
2. Collect Market Data quote envelopes.
3. Adapt each envelope to `ExecutionPriceObservation` and assess freshness.
4. Report Registry lot/fraction/currency capability readiness.
5. Run the existing E1 price, session, sizing, lot, and residual helpers.
6. Only after constrained quantity exists, use `quote_fee_for_instrument()`.
7. Build a policy-produced `NormalizedTradeInput`.
8. Build an `ExecutionTradeLeg` only for a complete input.

`ShadowCanonicalPlanDiagnostic` is frozen and private. Its per-symbol records retain evidence/contract references, policy and normalization state, residuals, and an explicit `COMPLETE`, `DEFERRED`, `INCOMPLETE`, `EXCLUDED`, or `ERROR` outcome. Its log payload contains aggregate counts only; no symbol or asset ID is used as a low-cardinality metric label. The diagnostic is neither returned nor persisted.

## Registry capability readiness

The read-only readiness helper requires resolved/eligible facts, a positive integer `lot_size`, `fractional_support is False`, and THB listing currency for the v1 shadow bundle. Missing lot size never becomes one. True or unspecified fractional support, missing capabilities, Registry failure, and non-THB facts produce incomplete diagnostics; M32.3E2 does not remediate Registry data.

## Failure containment and observed limitations

The entire plan shadow remains within the pre-existing post-result try/except boundary and each symbol is independently exception-contained. A provider, cache, facts, quote, policy, or diagnostic failure therefore leaves the legacy plan byte-for-byte unchanged.

Completeness depends on Yahoo Chart supplying a market-last price, observation timestamp, `REGULAR` session, and currency, as well as Registry lot/capability coverage. yfinance Close, average cost, cache TTL, previous close, local receipt time, and Registry currency cannot fill a missing live-evidence field. Such cases remain useful incomplete diagnostics, not fallback execution inputs.

## M32.3E3 prerequisites

M32.3E3 must not adopt this shadow as a canonical plan until it has approved provider/caching operational coverage, Registry lot and fractional evidence, Portfolio base/valuation currency and FX ownership, net-of-cost funding and cash-floor semantics, canonical plan/API/history behavior, transaction re-quote/admission, and an observation-window review. Those decisions remain outside M32.3E2.

## Explicit non-goals

No provider replacement/ranking, legacy quote contract change, cache migration, Registry remediation, FX, portfolio currency model, funding/cash change, canonical plan/API, optimizer change, transaction guard/requote, ledger/replay change, frontend, persistence, M31 enforcement, compatibility removal, or ExecutionIntent work is included.

## Verification

Focused tests cover immutable Chart/cache envelopes, absent evidence, yfinance classification, pure adapter boundaries, provider call deduplication/bounds, complete BUY leg projection, Registry capability incompleteness, and holding intent preservation. Broader M31/M32, market-data, execution-plan, optimizer, transaction, and replay verification is recorded with the implementation run.
