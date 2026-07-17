# M32.3B — Normalized Trade Input and Quantity-Intent Foundation

**Date:** 2026-07-14

**Status:** Implemented as shadow-only foundation. Authoritative unit sizing and
canonical execution-plan adoption remain deferred.

## Scope

M32.3B adds `backend/services/normalized_trade_input.py`: a pure boundary for
normalizing already-loaded pre-execution evidence. It neither creates an order
nor changes an optimizer recommendation, execution plan, transaction, ledger,
funding calculation, API response, frontend payload, persistence model, or
M31 cutover decision.

The only orchestration use is a private, post-result execution-plan diagnostic.
It reuses the existing M31.3 batch-resolved facts and eligibility values after
the legacy `ExecutionPlanResult` is already complete. The diagnostic is logged
only, exception-contained by the existing shadow block, and is neither
returned nor persisted.

## Contract

`NormalizedTradeInput` is frozen and versioned. It retains, by object identity:

- `ExecutionInstrumentFacts`, which remains the authority for identity;
- `ExecutionEligibility`, which remains the authority for eligibility; and
- an optional `FeeQuote`, which remains the authority for fee arithmetic.

It contains a deterministic `normalization_ref`, recommendation reference,
requested symbol, side, the following evidence sections, and a status of
`COMPLETE` or `INCOMPLETE`.

| Section | Values retained |
| --- | --- |
| Quantity/value intent | Requested/executable `Decimal` quantity, requested value, source, confidence, no-op lot/fraction adjustment summaries, and an optional caller-supplied holding snapshot. |
| Price evidence | Unit price, kind, source, observed/received timestamps, market session, freshness assessment/policy reference, stale state, and currency. |
| Planning context | Allocation source, portfolio/valuation currency, assumptions, warnings, and append-only provenance. |

Convenience `asset_id` and `canonical_symbol` properties project from facts;
they are not independent identity fields.

`QuantityAdjustmentSummary` permits absent quantities in amount-only inputs.
M32.3B adapters use no-op summaries only. Lot/fractional rounding and residual
policy remain M32.3D work.

## Quantity-source vocabulary

`QuantityIntentSource` explicitly distinguishes:

- `EXPLICIT_USER_QUANTITY`
- `FULL_HOLDING_QUANTITY`
- `ALLOCATION_VALUE_AT_PRICE`
- `REDUCTION_VALUE_AT_PRICE`
- `HOLDING_FRACTION`
- `BROKER_ORDER_QUANTITY`

`QuantityConfidence` is `EXACT`, `DERIVED`, or `ESTIMATED`. Value sources are
not silently converted into units. `ALLOCATION_VALUE_AT_PRICE` is BUY-only;
reduction, full-holding, and holding-fraction sources are SELL-only. An
unsupported/unspecified source or a source/side mismatch yields a typed
incomplete result.

## Typed incomplete results

`normalize_trade_input()` returns `NormalizationResult`, containing the frozen
input and zero or more `NormalizationFailure` values. Important reasons include
missing/invalid quantity or requested value, missing/invalid price, absent
price provenance/timestamp/session/freshness/currency, stale price, unresolved
or identity-mismatched facts, ineligibility, unavailable FeeQuote, and exact
side/quantity/price/currency quote mismatch. It also reports unexplained
requested/executable quantity differences.

Incomplete means evidence is absent or inconsistent; it never means:

- a zero quantity or price;
- an inferred `avg_cost` execution price;
- a created timestamp, session, currency, or fee quote;
- an assumed EQUITY identity; or
- a free trade.

A successful FeeQuote is necessary but not sufficient for `COMPLETE`: facts
must resolve eligible, values must be positive, complete price/freshness
evidence must be supplied, and quote side/quantity/price/currency must match
the normalized input exactly.

## Pure validation boundary

The normalizer and adapters accept only supplied contracts/data. They do not
perform Registry or market-data lookup, ORM/database access, network access,
fee selection/calculation, clock/environment reads, hidden price derivation,
or frontend arithmetic. Price evidence is only validated, never authored.

This also deliberately separates FeeQuote time from market-price evidence:
quote timestamps cannot supply absent observed/received price times.

## Source adapters

| Adapter | Result in M32.3B |
| --- | --- |
| Explicit manual quantity | Preserves requested/executable quantity exactly. An entered price is `USER_EXECUTION_TERM` / `USER_ENTERED`, never a market observation or broker-confirmed fill. |
| Full-holding SELL | Consumes a caller-supplied `HoldingQuantitySnapshot`; it does not query `PortfolioItem`. |
| Holding fraction | Derives quantity only as supplied held quantity × an explicitly named upstream fraction; confidence is `DERIVED`. No reconstructed percentage is used. |
| Optimizer amount-only | Preserves requested value and optimizer allocation source, with absent quantity/price and an explicit incomplete result. |
| Decision Workspace amount-only | Preserves requested value and Decision Workspace allocation source under the same incomplete rule. |

The execution-plan diagnostic demonstrates the last two cases: legacy BUY
`estimated_amount` becomes incomplete amount-only evidence. For active funding
actions it preserves legacy `current_shares` and `release_pct` as an explicit
holding-fraction quantity intent. Those SELL values remain incomplete without
canonical price, timestamp/session/freshness/currency, and FeeQuote evidence.

## Object reuse and future trade-leg integration

M32.2 `ExecutionTradeLegBuilder` is unchanged and continues to consume only
`LegacyExecutionTradeRequest`. M32.3B does not rebuild, resize, or replace a
leg and does not alter the existing M32.2 shadow output.

M32.3D’s future migration point is explicit: it may allow the builder to
consume only a `NormalizedTradeInput` with `status=COMPLETE`, retaining the
same facts, eligibility, and FeeQuote objects. M32.3B does not add that
authoritative builder path prematurely.

## Observable invariants

- Legacy execution-plan Pydantic output is byte-equivalent if the M32.3B
  diagnostic fails.
- Existing M32.2 legacy-request builder behavior remains unchanged.
- No new API/frontend/schema/migration field exists.
- No optimizer, transaction admission, ledger/replay, broker fee, funding,
  persistence, allocation, or M31 cutover behavior changes.
- Amount-only intent keeps value intact and never produces units or price.
- Facts, eligibility, and FeeQuote remain the exact input object instances.

## Dependencies and non-goals

M32.3C must provide an authoritative immutable price-observation contract with
observation/receipt time, source, currency, market session, and a versioned
freshness policy. It must decide whether a user term can ever satisfy market
price evidence and how stale/session state is assessed.

M32.3D additionally requires approved value-to-quantity, BUY/REDUCE/full-SELL,
lot/fractional/residual, cash-floor, base/valuation currency, FX, and quote
expiry/requote policies before constrained quantities or trade legs can become
authoritative.

M32.3B explicitly does not implement canonical price observations or
freshness, value-to-quantity conversion, lot/fractional policy, FX, funding,
canonical execution plans, optimizer/transaction/ledger/frontend changes,
persistence/migrations, execution intent, M31 enforcement, or compatibility
retirement.

## Verification

Focused M32.3B contract and shadow tests: **16 passed**. The suite covers
frozen/deterministic contracts, all required adapters, incomplete preservation,
absence of fallback quantity/price/timestamp/currency, Registry and
eligibility failure, unavailable/mismatched FeeQuote evidence, object identity,
pure-boundary static checks, unchanged M32.2 builder behavior, and
byte-equivalent execution-plan output when the new shadow fails.

Broader M31/M32, execution-plan, optimizer, transaction/write/replay, syntax,
and diff verification results are recorded with the implementation run.
