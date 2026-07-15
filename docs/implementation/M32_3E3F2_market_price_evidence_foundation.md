# M32.3E3F2 — Market Price Evidence Set and Provider Capability Shadow Foundation

**Date:** 2026-07-15

**Status:** Implemented as a default-off, evidence-only enhancement to the
private M32 live shadow. Canonical execution planning remains **NO-GO**.

## Scope and decision

M32.3E3F2 adds immutable contracts that retain independently timed market-price
evidence and provider capability facts. It does not select an execution price,
change a freshness threshold, change provider routing, or activate a canonical
plan. The only integration enriches the existing exception-contained,
post-result `M32_LIVE_EVIDENCE_SHADOW` diagnostic. Legacy plans, optimizer,
transactions, fees, ledger, API, frontend, Registry, and M31 behavior remain
unchanged.

## Evidence contracts

`LastPriceEvidence` represents one provider price event. The Yahoo Chart
`regularMarketPrice` / `regularMarketTime` pair maps to
`PROVIDER_REGULAR_LAST`, never `LAST_TRADE`. A Registry reference asset maps
to `INDEX_VALUE`, but eligibility remains Registry-owned. Receipt/cache time
and Registry currency never fill a missing event time/currency.

`TopOfBookEvidence` separately retains exact bid, ask, size, quote time,
receipt/cache time, pair quality, and evidence provenance. Pair quality is
`TWO_SIDED`, `BID_ONLY`, `ASK_ONLY`, `LOCKED`, `CROSSED`, `EMPTY`, or
`UNKNOWN`. The midpoint is available only for a valid two-sided book as a pure
reference convenience. It is not an execution price.

`DeclaredProviderDelayEvidence` is an optional governed provider/market claim
with authority, source/version, effective period, confidence, approval, and
provenance. Missing payload delay remains missing; declared delay is never
subtracted from observation age.

`MarketPriceEvidenceSet` retains supplied facts and all component objects by
identity. It cannot fetch data, resolve Registry facts, read a clock, select a
price, quote a fee, or derive a quantity.

## Separate clocks and ages

| Component | Clock measured | It is not |
| --- | --- | --- |
| Last price | Price-event `observed_at` | Quote/book age |
| Top of book | Book `quote_observed_at` | Receipt/cache age |
| Provider receipt | `provider_received_at` | Observation time |
| Cache | `cached_at` | Source freshness |
| Delay | Governed provider capability | Timestamp correction |

Pure component assessors accept the evidence object, a caller-supplied time,
and a versioned diagnostic policy. They never read a clock. The existing
five-/fifteen-minute values remain diagnostics only; F2 makes no new
execution-acceptance threshold and does not change M32.3E1 policy.

## Provider capability model

`ProviderMarketPriceCapability` documents one provider/market path without
ranking or routing providers. The current Yahoo Chart/SET path declares:

| Field | Capability |
| --- | --- |
| Provider regular-last | `SUPPORTED` |
| Explicit last trade | `UNAVAILABLE` |
| Timestamped bid/ask and sizes | `UNSUPPORTED` |
| Quote timestamp | `UNSUPPORTED` |
| Payload delay | `UNAVAILABLE` |
| Session, currency, bounded batch behavior | `SUPPORTED` |

The known Yahoo SET delay can only be attached through an explicitly supplied,
approved delay-evidence record. No pure adapter infers it from a symbol or
exchange. Capability is not a policy suitability field.

`python scripts/market_price_capability_audit.py` is read-only. It defaults to
the static current-path declaration and makes no network call. It can consume
reviewed sanitized field-availability samples, emits only aggregate coverage,
and refuses `--commit` and `--network-probe`. The supplied Yahoo fixture
reports `LAST_PRICE_ONLY`.

## Shadow diagnostics and compatibility

For each private shadow symbol, F2 reports last-price kind/age,
top-of-book/bid/ask/quote-clock availability, pair quality, provider-receipt
and cache age, declared-delay state, provider-capability readiness, session
evidence, and existing Registry eligibility/lot readiness. Low-cardinality
labels exclude symbols, asset IDs, prices, timestamps, and source locators.
The detailed diagnostic is neither returned nor persisted.

F2 does not construct a book-based observation for the existing M32.3E1 path,
does not select ASK for BUY or BID for SELL, and does not build a normalized
input or trade leg from top-of-book evidence. Existing Yahoo regular-last
policy behavior is unchanged.

## Fixtures and verification

Sanitized fixtures cover Yahoo regular-last, complete/timestamped two-sided
book, missing quote timestamp, approved delay, and current Yahoo capability
field availability. Focused tests also cover explicit last-trade vocabulary,
bid-only, ask-only, locked/crossed books, identity/currency absence,
receipt/cache separation, deterministic/frozen contracts, identity retention,
and absence of policy selection.

Focused F2 plus M32.3C/E1/E2/S2, stable Yahoo Chart provider, and M31
facts/eligibility tests:

```text
123 passed, 32 skipped
```

The skips are the existing stable Yahoo-provider set. Warnings are existing
SQLAlchemy declarative/datetime deprecations.

## Remaining blockers

No side-aware execution-price policy is approved. A future provider path must
provide identity/currency/session-bound timestamped bid and ask, known delay,
and operational/batch coverage. A later policy milestone must separately set
quote-age, delay, depth/capacity, and sensitivity rules.

Registry governed lot coverage remains 0/21. Market Calendar, portfolio
currency/cash-floor, net funding, transaction requote/admission, and canonical
plan rollout also remain unresolved. F2 changes none of these gates.

## Explicit non-goals

- No price-selection policy, threshold change, provider routing, streaming/top-of-book adapter, or authenticated endpoint.
- No Market Calendar, Registry remediation, canonical plan, funding/cash-floor, transaction/requote, API/frontend, persistence/migration, M31 enforcement, compatibility removal, or ExecutionIntent.
- No commit or push.
