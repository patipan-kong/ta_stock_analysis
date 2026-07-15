# M32.3E3F1 — Execution Price Freshness and Quote Semantics Audit

**Audit date:** 2026-07-15

**Decision:** **NO-GO for treating Yahoo Chart `regularMarketPrice` as an
execution-sizing quote or for changing the current freshness thresholds. GO
for an additive Market Data price-evidence foundation and a separate shadow
provider-capability assessment.**

**Scope:** Audit, bounded measurement, and design only. No provider request,
freshness threshold, execution policy, execution plan, Registry record, fee,
transaction, ledger, API, frontend, persistence model, or production behavior
was changed. No commit or push was performed.

## 1. Executive summary

The current M32 shadow is measuring one real but narrowly defined phenomenon:

```text
freshness age = caller assessment time - Yahoo regularMarketTime
```

That is the age of Yahoo's provider-labelled regular-market last-price event.
It is not quote age, provider receipt age, cache age, declared feed delay, or a
liquidity judgment. The calculation is truthful, but the current
`MARKET_LAST` label and the M32.3E1 sizing assumption are broader than the
runtime evidence can support.

The audit found:

1. Yahoo does not publish a formal field contract proving that
   `regularMarketTime` is an exchange last-trade timestamp. Field pairing,
   Yahoo presentation, intraday-bar alignment, and yfinance's treatment all
   support the narrower interpretation **provider regular-market last-price
   event time**. It is definitely not this application's receipt time or a
   provider refresh time, and it is not a bid/ask quote timestamp.
2. Yahoo's official market-coverage table states that Stock Exchange of
   Thailand `.BK` data is delayed by **15 minutes** and supplied by ICE Data
   Services. The Chart payload nevertheless omitted `exchangeDataDelayedBy`
   in all 21 controlled responses. Absence in the payload is not zero delay.
3. Seven symbols were fetched through three Chart shapes each:
   `5d/1d`, `1d/1m`, and `1d/5m`. All 21 responses had the same per-symbol
   `regularMarketPrice` and `regularMarketTime`. Request interval changes the
   chart bars, not this `meta` pair.
4. In the post-close sample, last-price age ranged from **15.03 to 59.01
   minutes**, median **30.23 minutes**. All seven observations were `EXPIRED`
   under the unchanged five-/fifteen-minute shadow policy.
5. The liquid-equity timestamps clustered near 30 minutes old: approximately
   the official 15-minute feed delay plus the 15 minutes elapsed after Yahoo's
   reported regular period ended. The index was 15.03 minutes old. PIS and
   AAPL01 were 58–59 minutes old and their last intraday bars stopped at the
   same time, consistent with sparse trading or price-event inactivity layered
   on top of the delayed feed.
6. Chart supplied no bid, ask, bid size, ask size, or quote timestamp in any
   controlled response. Its indicator arrays contained only OHLCV.
7. Yahoo's quote pages and yfinance's quote vocabulary show that Yahoo can
   carry bid/ask values through other paths. The repository's unauthenticated
   v7 quote requests returned HTTP 401, the existing yfinance `.info` path is
   owned and cached as 24-hour fundamental data, and none of those values has
   a trustworthy independent quote timestamp in the current runtime.
8. A last trade can remain unchanged while the order book changes. A fresh
   last trade also does not guarantee a usable spread; an old last trade can
   coexist with a fresh top of book. They require separate evidence and
   separate age assessments.

The narrowest truthful future v1 is therefore side-aware and quote-based:
BUY uses a timestamped ask, SELL uses a timestamped bid, and missing or delayed
top-of-book evidence produces `UNAVAILABLE`. Midpoint and last trade may remain
reference/sensitivity evidence; neither silently replaces the executable-side
quote. This is a design recommendation, not an approved or implemented policy.

Registry governed lot coverage remains 0/21 and independently prevents a
complete live leg even if price evidence is repaired.

## 2. Current price evidence flow

```text
Yahoo Chart GET range=5d interval=1d
  -> chart.result[0].meta.regularMarketPrice
  -> chart.result[0].meta.regularMarketTime
  -> ExecutionQuoteEnvelope(price_kind=MARKET_LAST)
  -> MarketSessionEvidence(observation claim REGULAR)
  -> ExecutionPriceObservation
  -> PriceFreshnessAssessment(assessed_at - regularMarketTime)
  -> ExecutionPolicy requires MARKET_LAST + CURRENT + REGULAR
  -> quantity / FeeQuote / NormalizedTradeInput / ExecutionTradeLeg
```

The M32.3E2 path calls `YahooChartProvider` directly. It does not use
`fetch_price_info()` or `MarketDataCache`, so the controlled M32 evidence was
not five-minute-cached legacy quote data.

The other price paths remain separate:

| Path | Price meaning | Timestamp retained for execution | Current use |
| --- | --- | --- | --- |
| Yahoo Chart `get_quote()` | `regularMarketPrice` | No; `last_updated` is locally generated receipt time | Presentation, optimizer valuation input |
| Yahoo Chart execution envelope | Provider regular-market last price | Yes, `regularMarketTime`, plus receipt time | Default-off M32 shadow |
| yfinance `get_quote()` | Latest `Ticker.history()` Close | No exchange observation time in DTO | Legacy rollback provider |
| `fetch_price_info()` cache | Legacy three-field quote payload | Provider DTO receipt string only; cache `fetched_at` is not returned | UI, analytics, optimizer |
| Intraday history | OHLCV bar selected by caller | Bar timestamp | Analytics; not current execution pricing |
| Execution plan | BUY amount; SELL funding derived from `avg_cost` | None | Legacy gross plan only |
| Position sizing / Decision Workspace | Allocation values over cost-basis portfolio value | None | Recommendation and amount intent |
| Portfolio transactions | User-entered execution term | Transaction time is not market-observation time | Ledger posting |

The optimizer copies `current_price` into `scores_map` after discarding the
legacy DTO's `last_updated`. It uses the value for valuation, upside, and
average-daily-traded-value judgment. `execution_penalty.py` derives liquidity,
spread, and slippage estimates from structural baselines plus volume and
price; it does not observe a live spread and does not own price selection.

## 3. Yahoo field semantics

### 3.1 `regularMarketPrice` and `regularMarketTime`

The defensible contract today is:

> Yahoo's latest supplied regular-market price value and the provider timestamp
> paired with that value.

The evidence supports, but does not formally prove, that this normally tracks
the last regular-session trade or last regular-price event:

- the price/time pair was invariant across daily, one-minute, and five-minute
  Chart requests;
- the time fell within the last populated intraday bar or immediately after
  its bucket start;
- sparse instruments had both an old `regularMarketTime` and an old final
  intraday bar;
- Yahoo quote pages present the regular price with an “as of” time; and
- yfinance internally calls `regularMarketPrice` its last price.

It must not yet be renamed to authoritative `LAST_TRADE`: no Yahoo field
contract inspected in this audit says whether every update is a trade,
auction print, calculated index event, correction, or another regular-market
price event. An index makes “trade” particularly inappropriate.

The pair is not:

- provider receipt or refresh time—the same old time was returned by new HTTP
  requests and receipt was recorded separately;
- cache time—the controlled path bypassed the application cache;
- bid/ask quote time—Chart supplied no book fields or quote clock; or
- proof of an executable price—the source is delayed and a last price says
  nothing about current spread or depth.

### 3.2 Can price remain unchanged while bid/ask changes?

Yes. Last-price and order-book events have different triggers. Orders can be
added, cancelled, or repriced without a trade. The best bid and ask can move
while the last traded price remains constant. Conversely, one trade can occur
without proving that the displayed book remains available afterward.

Yahoo's own quote pages display price, bid, and ask as separate values. The
installed yfinance streaming schema likewise has separate `price`, `bid`,
`ask`, sizes, and one message time. This is structural evidence of distinct
fields, not proof that the current repository receives a timestamped top of
book.

### 3.3 Daily request effect

For each of the seven controlled symbols, `regularMarketPrice` and
`regularMarketTime` were identical under:

- `range=5d`, `interval=1d`;
- `range=1d`, `interval=1m`; and
- `range=1d`, `interval=5m`.

Only `meta.dataGranularity`, the timestamp arrays, and aggregated OHLCV bars
changed. The production `5d/1d` request does not appear to make
`regularMarketTime` a daily-bar timestamp. Switching interval would therefore
not repair the execution evidence; it would only fetch different history.

## 4. Controlled measurement methodology

### 4.1 F1 sample

Seven allow-listed symbols were selected to vary activity and form:

| Group | Symbols |
| --- | --- |
| Liquid SET equities | `KBANK.BK`, `AOT.BK`, `ADVANC.BK` |
| Lower-activity SET equities | `KGI.BK`, `PIS.BK` |
| DR-like listing | `AAPL01.BK` |
| Index/reference | `^SET.BK` |

Each symbol was requested three times from the Chart endpoint using the three
shapes in §3.3. The probe retained only an allow-list of metadata fields,
indicator key names, latest populated bar time/value/volume, counts, HTTP
status, and caller receipt time. It retained no unrestricted response,
headers, cookies, tokens, or credentials.

Two unauthenticated Yahoo quote endpoint hosts were tested once with the same
bounded symbol set. A bounded yfinance WebSocket probe subscribed to five SET
symbols after the market close and received no messages. This does not prove
the stream lacks fields; it proves no usable SET streaming evidence was
obtained in that window.

The sample was taken at approximately 16:44 ICT, after Yahoo's supplied
regular trading period ended at 16:30 ICT. It is a one-shot development
sample, not a reliability or market-microstructure study. Open, intermission,
and auction-period measurement could not all be performed in one audit turn.

### 4.2 Earlier controlled evidence

M32.3E3S1 sampled during the SET trading day near 15:10 ICT. Its successful
responses showed approximately:

- `KBANK.BK` and `AOT.BK`: regular time near 14:42, about 28 minutes old;
- `AAPL01.BK`: regular time near 12:27, over two hours old; and
- `^SET.BK`: regular time near 14:57, about 13 minutes old.

That earlier window proves that even visibly active SET equities can expose a
regular-market last-price event older than five minutes while the session is
regular. It does not prove that no recent exchange trade occurred; Yahoo's
official 15-minute feed delay is already enough to make the free source
unsuitable for a five-minute execution threshold.

### 4.3 Evidence classes

- **Measured live:** the bounded Chart, v7 quote-status, and WebSocket probes.
- **Prior measured live:** the S1/S2 controlled runs recorded in their
  implementation documents.
- **Static repository:** provider, cache, observation, policy, optimizer,
  Decision Workspace, and execution-plan code.
- **Provider-published:** Yahoo's market-coverage/data-delay Help page and
  Yahoo quote-page presentation.
- **Dependency static:** installed yfinance source/schema; not a current
  application capability declaration.

## 5. Last-trade age results

The table uses the `5d/1d` receipt for each symbol; the other intervals differed
only by sub-second request sequencing.

| Symbol | `regularMarketPrice` | Last-price age | Latest 1m bar age | Populated 1m bars | Daily volume in response | Current shadow result |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `KBANK.BK` | 230.00 | 30.09 min | 31.85 min | 266 | 10,392,284 | `EXPIRED` |
| `AOT.BK` | 63.75 | 30.08 min | 31.85 min | 282 | 24,972,552 | `EXPIRED` |
| `ADVANC.BK` | 376.00 | 30.23 min | 31.85 min | 287 | 9,233,987 | `EXPIRED` |
| `KGI.BK` | 4.74 | 30.67 min | 31.85 min | 249 | 12,841,301 | `EXPIRED` |
| `PIS.BK` | 4.84 | 58.27 min | 58.86 min | 81 | 1,690,081 | `EXPIRED` |
| `AAPL01.BK` | 31.50 | 59.01 min | 59.86 min | 13 | 265,981 | `EXPIRED` |
| `^SET.BK` | 1,631.92 | 15.03 min | 16.86 min | 305 | 0 | `EXPIRED` |

Summary:

| Metric | Result |
| --- | ---: |
| Valid Chart responses | 21/21 |
| Symbols with regular price/time pair | 7/7 |
| `regularMarketTime` identical across all three request shapes | 7/7 |
| Minimum / median / maximum last-price age | 15.03 / 30.23 / 59.01 min |
| `CURRENT` / `STALE` / `EXPIRED` under existing shadow policy | 0 / 0 / 7 |
| Observation-session claim | 7/7 `REGULAR` |
| Provider response state | 0/21 present |
| Payload provider delay | 0/21 present |

The index crossed the fifteen-minute boundary by approximately 1.6 seconds,
so `EXPIRED` is the correct result under the existing inclusive thresholds.
The assessment did not round age or promote the value based on session.

## 6. Bid/ask and quote evidence availability

### 6.1 Yahoo Chart

Bid/ask coverage in the controlled Chart sample was **0/21**. The relevant
`meta` fields were absent, and every `indicators.quote[0]` contained exactly:

```text
open, high, low, close, volume
```

There was no bid, ask, bid size, ask size, quote-observed time, book sequence,
or exchange quote time. One-minute OHLCV bars are trade/price aggregation and
cannot be reinterpreted as top of book.

### 6.2 Yahoo v7 quote and existing yfinance path

Direct unauthenticated requests to both `query1` and `query2` v7 quote hosts
returned HTTP 401. The repository's yfinance `.info` implementation internally
merges Yahoo quote-summary and v7 quote data, whose vocabulary can include
`bid`, `ask`, and sizes. The application exposes that call only through
`get_fundamentals()` / `fetch_info()` and caches it for 24 hours.

That path is unsuitable for execution even when fields happen to populate:

- it is owned as fundamental metadata, not a quote contract;
- it has no independently retained quote observation timestamp;
- its application cache lifetime is 24 hours;
- bid/ask population and size conventions are not validated for SET; and
- the controlled `.info` process produced no sanitized result in this Windows
  environment, so live coverage could not be established.

Yahoo quote pages visibly publish bid/ask for some SET listings and label the
market data “Thailand - Delayed Quote.” They do not provide this application
with a stable, timestamped, contract-backed quote envelope.

### 6.3 Installed streaming vocabulary

The installed yfinance package includes an unused Yahoo WebSocket client and a
schema with `price`, `time`, `last_size`, `bid`, `ask`, `bid_size`, and
`ask_size`. The production provider interface does not use it or declare a
streaming/top-of-book capability. A bounded post-close subscription returned
zero messages.

Before this could be considered evidence, a separate provider milestone would
need to establish:

- what the single message `time` timestamps;
- whether bid and ask are contemporaneous or independently updated;
- SET/DR coverage and delay;
- snapshot/bootstrap behavior before the first update;
- currency and identity binding;
- reconnect, sequence, crossed-market, and one-sided-book behavior; and
- licensing/operational suitability.

The existence of dependency fields is not runtime readiness.

## 7. Provider delay and cache findings

Yahoo's official [exchange and data-provider table](https://help.yahoo.com/kb/finance/article-exchanges-data-delays-sln2310.html)
lists Stock Exchange of Thailand `.BK` quotes as delayed by **15 minutes**, with
ICE Data Services as the provider. Yahoo also states that its displayed data
is informational and not intended for trading purposes.

This is authoritative provider-capability evidence, but it is not currently
carried into `ExecutionQuoteEnvelope`:

- `exchangeDataDelayedBy` was absent in 21/21 Chart responses;
- S2 correctly retained `delay=None` rather than zero;
- the static Yahoo market-level delay is not versioned or bound to an
  observation inside the repository; and
- policy must not infer it from `.BK` or exchange text.

A future Market Data capability record may attach the governed Yahoo/SET delay
claim to the evidence set by resolved market/provider capability. That is an
adapter/router governance task, not a price-policy fallback.

Cache findings:

- the F1 and M32 live-evidence probes called the provider directly; application
  quote-cache involvement was **zero**;
- the legacy quote cache has a five-minute TTL, but a new cache write can
  contain a 15-minute-delayed or older market observation;
- `MarketDataCache.fetched_at` measures cache ingestion time, not price time;
- cache `expires_at` measures platform reuse policy, not source freshness; and
- stale fallback metadata is stripped by some legacy callers and must never
  enter execution evidence as current.

The official 15-minute source delay alone means a five-minute observation-age
acceptance policy and Yahoo SET cannot both succeed truthfully. The correct
response is source-capability `UNAVAILABLE` for that policy, not subtraction of
15 minutes from age and not a wider threshold chosen to restore coverage.

## 8. Sparse trading versus stale-feed analysis

The old timestamps have more than one cause.

| Candidate cause | Finding |
| --- | --- |
| Incorrect extraction | Rejected. The adapter reads the explicit `regularMarketTime`; all request shapes agree. |
| `5d/1d` request shape | Rejected for `meta`. One-minute and five-minute requests returned the exact same pair. |
| Application stale cache | Rejected for the controlled path. It bypassed `MarketDataCache`. |
| Provider delay | Confirmed at market capability level: Yahoo publishes 15 minutes for SET, though the payload omits it. |
| Post-close inactivity | Present in F1: receipt was roughly 15 minutes after Yahoo's reported regular period ended. |
| Sparse trading / price inactivity | Strong evidence for PIS and AAPL01: far fewer populated bars and final bars aligned with their old regular times. |
| Liquid-symbol inactivity | Not established. Liquid names had millions of shares and hundreds of populated bars; their common timestamp cluster is more consistent with provider delay/cutoff than with simultaneous lack of trading. |
| Provider field is a quote clock | Rejected. No quote fields or independent quote timestamp accompany it. |

For the liquid names, a one-shot sample cannot decompose every second between
exchange trade inactivity, Yahoo/ICE publication delay, and post-close elapsed
time. It can establish the operational fact that the received evidence was
30 minutes old and the source declares a 15-minute delay.

For PIS and AAPL01, the latest one-minute bar and regular-market time ended
together. That is consistent with no later provider-visible price event.
Whether the exchange itself had a later trade is unknowable from this delayed
single source.

An actively traded symbol can therefore report a last-price event older than
five minutes during a regular session. The earlier S1 KBANK/AOT observations
showed exactly that. “Active today” is not “a fresh executable quote now.”

## 9. Price-kind ownership

Market Data owns observation meaning and must distinguish evidence kinds
before policy sees them:

| Evidence kind | Meaning | Owner |
| --- | --- | --- |
| Provider regular-market last | Latest provider-supplied regular price event; trade semantics not yet guaranteed | Market Data adapter |
| Last trade | Explicit exchange/provider trade event with trade timestamp | Market Data adapter/provider capability |
| Bid / ask | Executable-side top-of-book observations with quote timestamp and sizes when available | Market Data adapter/provider capability |
| Midpoint | Pure derivation from one contemporaneous valid bid/ask pair | Market Data normalization; policy chooses whether usable |
| User limit | Caller instruction/term, not market evidence | Input/Execution domain |
| Close | Settled or provider close for valuation/history | Market Data |
| Selected execution price | Policy decision retaining exact source evidence and derivation | Execution Policy |
| Slippage sensitivity | Judgment around a selected price, never a rewritten observation | Execution risk/policy |

The current `PriceKind.MARKET_LAST` is adequate as a compatibility vocabulary
only if documented as provider last-price evidence. It is insufficient to tell
policy whether the event is a trade, an index update, a delayed value, or a
quote. Price selection must not inspect Yahoo field names or provider names.

## 10. Freshness-policy implications

### 10.1 What the current assessment measures

`PriceFreshnessAssessment` correctly measures **last-price event age** for the
current observation. It does not measure:

- top-of-book quote age;
- provider receipt age;
- cache age;
- declared feed delay;
- venue state or calendar validity;
- last-trade frequency/liquidity;
- spread/depth risk; or
- expected slippage.

The implementation is mathematically correct for its input. The policy gap is
using that one assessment as if it certified an execution quote.

### 10.2 Different evidence requires different assessment

| Evidence | Required clock | Freshness interpretation |
| --- | --- | --- |
| Last trade / provider last price | Explicit event time | Age since last price event; may reflect delay plus sparse trading |
| Bid/ask | Explicit quote/book observation time | Age of the top-of-book snapshot; must also validate pair consistency |
| Close | Session/date and settlement status | Current for valuation according to calendar, not intraday execution |
| Delayed feed | Observation clock plus versioned declared delay | Source may be unsuitable even when recently received; delay is not subtracted from age |
| User limit | User term time/expiry | Instruction lifecycle, not market freshness |

A single five-minute threshold is not defensible across these kinds or across
all SET listings. It is a repeatable shadow diagnostic, exactly as M32.3C
documents. No alternative numeric threshold is approved here.

Per-kind or liquidity-aware policies must not make old evidence “current” to
increase coverage. If liquidity affects policy, the safe direction is a
stricter quote requirement, wider sensitivity, smaller capacity, or explicit
unavailability—not a rewritten timestamp or automatically longer age limit.

### 10.3 Provider delay

Declared delay is source-quality evidence. It may cause a policy to reject a
provider for execution pricing before inspecting age. It must never:

- be assumed zero when absent;
- be subtracted from event age to make a value current;
- turn receipt time into observation time; or
- be hidden inside one stale boolean.

## 11. Candidate contract changes

`ExecutionPriceObservation` remains useful for one selected scalar observation
and one age assessment. It is not sufficient as the raw container for
last-price and two-sided quote evidence with different clocks.

The smallest additive model is a composed `MarketPriceEvidenceSet`:

```text
MarketPriceEvidenceSet
  contract_version / evidence_set_ref
  asset_id / canonical_symbol / provider identity
  currency

  last_price_evidence
    semantic_kind                  # PROVIDER_REGULAR_LAST / LAST_TRADE
    price
    observed_at
    event_id or sequence if supplied

  top_of_book_evidence
    bid / bid_size
    ask / ask_size
    quote_observed_at
    book sequence if supplied
    pair quality                   # TWO_SIDED / ONE_SIDED / LOCKED / CROSSED

  provider_received_at
  cached_at
  declared_provider_delay_evidence # value + authority/version/effective period
  MarketSessionEvidence ref
  future MarketCalendarAssessment ref
  source quality / warnings / provenance
```

Each component receives its own immutable freshness assessment. The set does
not select a price.

Policy selection can then return:

```text
ExecutionPriceSelection
  selection_kind = LAST_TRADE | BID | ASK | MIDPOINT | USER_LIMIT | UNAVAILABLE
  selected_price
  source evidence ref(s)
  side
  derivation
  accepted freshness assessment ref
  optional sensitivity range
  policy version / reasons / warnings
```

`USER_LIMIT` retains an Input/Execution-owned term rather than pretending it
is Market Data. `UNAVAILABLE` is a first-class successful policy result when
truthful live evidence is insufficient.

No contract should contain one ambiguous `timestamp`, one combined stale
boolean, or a price already adjusted by slippage.

## 12. BUY versus SELL price-selection options

### Candidate comparison

| Selection | BUY | SELL | Finding |
| --- | --- | --- | --- |
| Last trade | May understate or overstate current ask | May overstate or understate current bid | Reference/sensitivity only unless an explicit future policy proves adequacy |
| Bid | Optimistic/non-marketable BUY assumption | Conservative immediate-sale point | Candidate SELL v1 evidence |
| Ask | Conservative immediate-purchase point | Optimistic/non-marketable SELL assumption | Candidate BUY v1 evidence |
| Midpoint | Understates immediate BUY cost | Overstates immediate SELL proceeds | Fair-value diagnostic, not conservative executable point |
| User limit | Conditional maximum term | Conditional minimum term | Valid instruction assumption when explicitly entered, not a live quote |
| Previous close / avg cost | Not live | Not live | Never accepted |
| Unavailable | Correct when quote evidence is missing | Correct when quote evidence is missing | Required safe fallback |

### Narrowest truthful future v1

For BUY:

- require one identity/currency/session-bound positive ask;
- require its own quote-observation time and caller assessment;
- require an approved quote-age policy and acceptable declared-delay status;
- retain bid/spread when available for quality/sensitivity;
- if ask, quote time, currency, session/calendar, or delay evidence is
  insufficient, return `UNAVAILABLE`; and
- do not fall back to last trade, midpoint, previous close, average cost, or
  receipt time.

For SELL:

- apply the symmetric rule to the bid;
- require quantity/depth policy separately before claiming that the displayed
  bid supports the whole leg;
- preserve full-holding and lot rules independently; and
- return `UNAVAILABLE` for one-sided/missing/untimestamped evidence.

For both sides, the selected point should be paired with a sensitivity range,
not replaced by it. Spread, depth, quantity relative to volume, and the
existing slippage judgment can describe uncertainty. They cannot alter the
source bid/ask or make it fresher.

Whether last trade is ever sufficient remains a policy approval question. It
could support non-marketable valuation, very small diagnostic sizing, or a
sensitivity anchor under an explicit future rule. The present delayed Yahoo
SET evidence is not sufficient for authoritative execution sizing.

## 13. Risk and failure behavior

| Condition | Required behavior |
| --- | --- |
| Old last trade, fresh valid book | Keep trade-age warning; policy may use book under its own assessment |
| Fresh last trade, old/missing book | No executable-side quote; `UNAVAILABLE` |
| Missing bid for SELL or ask for BUY | `UNAVAILABLE`; no midpoint/last fallback |
| No quote timestamp | Incomplete quote evidence; receipt time cannot fill it |
| Declared delayed feed exceeds policy capability | Defer/unavailable even if HTTP response is new |
| Delay absent | `UNKNOWN`, never zero |
| Sparse trading | Preserve old trade age and warning; require stronger quote/depth evidence |
| Wide spread | Preserve bid/ask; add risk/sensitivity or policy block without rewriting either side |
| Locked/crossed book | Quarantine or typed conflict; do not select mechanically |
| Quote currency/identity mismatch | Incomplete/error; never normalize from Registry currency or symbol shape |
| Closed/intermission/calendar conflict | Session/calendar policy remains independently blocking |
| Cache hit | Preserve original event, receipt, and cache times; TTL does not certify freshness |
| Provider unavailable | Typed missing evidence; no previous close/avg-cost fallback |

The current optimizer liquidity/slippage metadata may contribute warnings,
evidence-quality context, a stricter policy tier, capacity limits, or a
sensitivity band. It may not:

- rewrite the observed price or timestamp;
- infer a spread when bid/ask is absent;
- make an expired observation current;
- select a provider or price kind; or
- convert a coarse liquidity score into quote evidence.

## 14. Go / No-Go recommendation

| Decision | Result | Basis |
| --- | --- | --- |
| Keep S2 semantic separation | **GO** | Session claim, state, delay, receipt, and observation time remain distinct |
| Treat `regularMarketTime` as provider refresh or quote time | **NO-GO** | New requests return the old event time; no book clock exists |
| Treat `regularMarketPrice` as authoritative last trade | **NO-GO** | Strongly last-price-like, but provider does not publish a sufficient field contract for every instrument kind |
| Use current Yahoo Chart value for execution sizing | **NO-GO** | Official SET delay is 15 min; no bid/ask/depth/quote timestamp |
| Change five-/fifteen-minute thresholds | **NO-GO** | Would optimize coverage around an unsuitable delayed source rather than approve policy |
| Use cache TTL or receipt time as freshness | **NO-GO** | Different clocks and owners |
| Use legacy yfinance fundamentals bid/ask | **NO-GO** | 24-hour cache, no quote clock, unproven SET coverage |
| Add a pure price-evidence-set contract and fixtures | **GO** | Additive and does not change provider/policy behavior |
| Implement a provider-capability probe/adapter in shadow | **Conditional GO** | Only if it preserves missing fields and remains default-off/non-authoritative |
| Begin canonical M32 plan work | **NO-GO** | Price, calendar, lots, currency/cash floor, funding, and admission gates remain unresolved |

The current freshness policy is measuring the intended **last-price age**, but
that is not sufficient to answer the intended **execution quote usability**
question. An implementation milestone can safely proceed only to evidence
contracts, provider-capability evaluation, fixtures, and default-off shadow
measurement. It must not activate a new price-selection policy.

## 15. Recommended implementation sequence

Proceed with a narrowly scoped **M32.3E3F2 — Market Price Evidence Set and
Provider Capability Shadow Foundation**:

1. Add immutable `LastPriceEvidence`, `TopOfBookEvidence`,
   `DeclaredProviderDelayEvidence`, and `MarketPriceEvidenceSet` contracts.
   Preserve exact clocks and absences; add no provider call yet.
2. Add sanitized fixtures for Chart last-price evidence, quote fields with and
   without timestamps, one-sided/locked/crossed books, missing delay, and
   sparse last trades.
3. Add separate pure freshness assessments for last-price and book evidence.
   Keep current numeric policies unchanged and label them diagnostic only.
4. Add a read-only provider capability audit for SET that establishes whether
   any approved source can supply timestamped bid/ask, size, currency, delay,
   session, identity, and bounded batch behavior. Do not route to it yet.
5. Model Yahoo's official SET delay as versioned provider-market capability
   evidence if governance approves the Help table as authority. Do not infer
   from `.BK` in pure adapters.
6. Extend the default-off shadow diagnostic to report last-price age, quote
   age, receipt age, cache age, declared delay, spread/depth availability, and
   distinct root causes. Keep symbols out of low-cardinality labels.
7. Observe open, intermission, auction, closed, liquid, sparse, DR-like, and
   reference samples across a retained review window.
8. Only after evidence exists, perform a separate policy-design approval for
   side-aware bid/ask selection, quote-age thresholds, delayed-feed behavior,
   depth/capacity, and sensitivity ranges.

Do not combine F2 with threshold changes, execution-plan integration beyond
the existing private shadow, provider routing changes, or canonical adoption.

## 16. Expected impact on M32 completeness

The expected immediate effect of honest price semantics is not higher complete
leg coverage:

- current Yahoo Chart top-of-book completeness remains **0%**;
- current Yahoo SET data is officially 15 minutes delayed;
- keeping a five-minute shadow requirement means Yahoo-sourced SET execution
  evidence remains non-current by design;
- last-price observations become better diagnosed as delay, inactivity, or
  unknown rather than one generic stale flag; and
- governed lot coverage remains **0/21**, independently holding complete live
  legs at zero.

Completeness can improve only when a provider capability supplies truthful
timestamped side-aware evidence under an approved policy and Registry lots are
governed. Loosening labels or thresholds would improve a metric while reducing
truth, which is explicitly rejected.

## 17. Explicit non-goals

- No freshness-threshold or execution-policy change.
- No provider request-shape, provider ranking, or routing change.
- No top-of-book, streaming, or quote adapter implementation.
- No Market Calendar implementation.
- No Registry lot remediation.
- No execution-plan, funding, cash-floor, fee, or canonical-plan change.
- No transaction admission/requote, ledger, or replay change.
- No API, frontend, persistence, or migration.
- No M31 enforcement or compatibility retirement.
- No commit or push.

## Verification record

### Repository audit

Audited:

- `backend/services/market_data/yahoo_chart.py`;
- `backend/services/market_data/yahoo.py`;
- `backend/services/market_data/execution_quote.py`;
- `backend/services/market_data/session_evidence.py`;
- `backend/services/market_data/base.py` and `provider.py`;
- `backend/services/data_fetcher.py` and `MarketDataCache`;
- `backend/services/execution_price_observation.py`;
- `backend/services/execution_policy.py`;
- `backend/services/execution_live_evidence_shadow.py`;
- `backend/services/execution_trade_leg.py` and `normalized_trade_input.py`;
- `backend/services/optimizer/execution_penalty.py` and optimizer price flow;
- `backend/services/position_sizing.py`, `execution_plan.py`, Decision
  Workspace orchestration, and transaction price ownership;
- installed yfinance quote and streaming schemas; and
- Market Data Platform, Provider Interface, M32.3C/D/E1/E2/E3/S1/S2 design
  and implementation records.

### Controlled network evidence

- 7 symbols × 3 Chart request shapes: **21/21 HTTP 200**, regular pair 21/21,
  bid/ask 0/21, quote timestamp 0/21, payload delay 0/21.
- Per-symbol `regularMarketTime` was identical across all three request shapes:
  **7/7**.
- Direct unauthenticated v7 quote endpoint: query1 **401**, query2 **401**.
- Bounded post-close Yahoo WebSocket subscription: **0 SET messages**; no
  coverage claim made.
- Application cache involvement: **0** for the controlled requests.
- No unrestricted payload, response header, cookie, token, or credential was
  retained.

### Provider-published evidence

Yahoo's official market-coverage table lists SET `.BK` data as 15-minute
delayed. Yahoo quote pages label Thai data delayed and may display bid/ask, but
the current application has no timestamped top-of-book contract for those
fields.

### Tests and repository checks

The stable Yahoo Chart, M32.3C price-observation, M32.3E1 policy, M32.3E2 live
evidence, and M32.3E3S2 session-evidence group completed with:

```text
81 passed, 32 skipped
```

The 32 skips are the existing stable Yahoo-provider skip set. Warnings were
existing SQLAlchemy declarative/datetime deprecations. Repository diff and
explicit whitespace checks are included in final verification.

No production code or data was changed by this audit.
