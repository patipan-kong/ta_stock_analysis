# M32.3E3S1 — Provider Market Session Evidence Audit and Design

**Audit date:** 2026-07-15

**Decision:** **GO for a narrow Market Data-owned session-evidence contract and
Yahoo Chart adapter; NO-GO for weakening session acceptance or treating the
current provider response state as the price observation's session.**

**Scope:** Audit and design only. No provider behavior, execution policy,
execution plan, Registry data, transaction, ledger, API, frontend, persistence
model, or production calculation was changed. Controlled requests were
read-only and emitted only bounded, allow-listed metadata.

## 1. Executive summary

`MarketSession.UNKNOWN` is caused by **omitted provider data, not an incomplete
value mapping**. The current Yahoo Chart adapter reads only
`chart.result[0].meta.marketState`. Four controlled successful requests made
during the SET trading day returned no `marketState` key at all. The existing
mapper already recognizes every spelling named in the brief: `REGULAR`, `PRE`,
`POST`, `CLOSED`, `PREPRE`, and `POSTPOST` (plus compatibility spellings).

The same responses did provide a different and more relevant fact:
`regularMarketPrice` paired with `regularMarketTime`. That pair is a
provider-labelled claim that this value and timestamp belong to the regular
market. It can truthfully support a **provider observation-session claim** of
`REGULAR`; it cannot establish that the venue was currently regular when the
response was received. A response after close can legitimately carry the last
regular-session price and a response state of `CLOSED`.

Yahoo also returned `currentTradingPeriod`, `exchangeTimezoneName`,
`gmtoffset`, and `instrumentType`. These are schedule, timezone, and provider
classification evidence. They do not substitute for observation session. In
particular, the observed Yahoo regular period was one continuous
10:00–16:30 ICT interval for ordinary SET equities, a DR-like symbol, and the
SET index. The official SET schedule distinguishes product classes and, for
ordinary equities, morning and afternoon sessions separated by an
intermission. Interval membership is therefore not a sufficient execution
session rule.

The smallest truthful architecture is:

1. add an immutable `MarketSessionEvidence` owned by Market Data;
2. retain provider response state, provider-labelled observation session, and
   provider schedule/timezone evidence as separate fields;
3. later add an independent versioned `MarketCalendarAssessment` evaluated at
   `observed_at`; and
4. let Execution Policy decide which evidence combination is acceptable.

Provider-only evidence can improve live-shadow session recognition for the
exact Yahoo `regularMarketPrice`/`regularMarketTime` pair. It cannot replace a
canonical calendar, establish present venue state, prove data is undelayed, or
make the plan canonical. M32 remains blocked independently by 0/21 governed
lot coverage.

## 2. Raw Yahoo metadata inventory

### Controlled requests

Four allow-listed Chart requests used the production query shape
(`range=5d`, `interval=1d`) between approximately 15:10 and 15:12 ICT. No raw
response, cookie, token, header, or unrestricted payload was retained.

| Requested symbol | Result | Provider type | Price | `regularMarketTime` (ICT) | `marketState` | `currentTradingPeriod.regular` | Timezone / offset | Delay field | `quoteType` |
| --- | --- | --- | ---: | --- | --- | --- | --- | --- | --- |
| `KBANK.BK` | Success | `EQUITY` | 231.00 | 2026-07-15 14:41:53 | Absent | 10:00–16:30 ICT | `Asia/Bangkok` / +25200 | Absent | Absent |
| `AOT.BK` | Success | `EQUITY` | 63.75 | 2026-07-15 14:41:56 | Absent | 10:00–16:30 ICT | `Asia/Bangkok` / +25200 | Absent | Absent |
| `AAPL01.BK` | Success | `EQUITY` | 31.25 | 2026-07-15 12:26:47 | Absent | 10:00–16:30 ICT | `Asia/Bangkok` / +25200 | Absent | Absent |
| `^SET.BK` | Success | `INDEX` | 1,633.37 | 2026-07-15 14:56:48 | Absent | 10:00–16:30 ICT | `Asia/Bangkok` / +25200 | Absent | Absent |

All four returned `currency=THB`, `exchangeName=SET`,
`fullExchangeName=Thailand`, `hasPrePostMarketData=false`, and a
`currentTradingPeriod` object with `pre`, `regular`, and `post` members. The
`pre` and `post` members were zero-duration boundaries in this response shape.
`instrumentType` was present; `quoteType` was not.

A final `KBANK.BK` probe captured the provider receipt boundary explicitly:

```json
{
  "requested_at": "2026-07-15T08:12:46.019637+00:00",
  "regularMarketTime": 1784101364,
  "marketState_present": false,
  "exchangeTimezoneName": "Asia/Bangkok",
  "gmtoffset": 25200,
  "regular_period_start": 1784084400,
  "regular_period_end": 1784107800,
  "observed_within_reported_regular_period": true,
  "exchangeDataDelayedBy_present": false,
  "quoteType_present": false,
  "instrumentType": "EQUITY",
  "envelope_session": "UNKNOWN"
}
```

This sample is bounded metadata, not a stable provider guarantee. The
repository has one synthetic fixture with `marketState=REGULAR`; it has no
recorded fixture representing the successful live Chart shape where that key
is absent. A future implementation should check in sanitized fixtures for both
shapes.

## 3. Current mapping and failure analysis

The path is:

```text
YahooChartProvider._fetch_chart_result()
  -> chart.result[0]
  -> adapt_yahoo_chart_execution_quote()
       market_session = map(meta.marketState)
  -> ExecutionQuoteEnvelope.market_session
  -> ExecutionPriceObservation.market_session
  -> assess_price_freshness()
  -> SESSION_UNKNOWN
  -> Execution Policy INCOMPLETE / SESSION_UNKNOWN
```

`backend/services/market_data/execution_quote.py` and
`backend/services/execution_price_observation.py` contain equivalent mappings.
Both recognize the listed Yahoo spellings. The M32.3E2 test fixture supplies a
synthetic `marketState=REGULAR`, so it proves mapping behavior but not live
Chart field availability.

The failure is therefore twofold:

1. the Chart response omitted `marketState`; and
2. the current envelope uses a response-level state field as the sole source
   for the observation-level session, while discarding the distinct session
   claim implicit in the `regularMarketPrice`/`regularMarketTime` pair.

No value should be mapped from `UNKNOWN` to `REGULAR`. The correct repair is
to model the two meanings separately.

## 4. Semantics of relevant provider fields

| Field | Evidence supplied | What it must not mean |
| --- | --- | --- |
| `regularMarketPrice` | Provider-labelled regular-market price value | Current venue state, execution price, or undelayed price |
| `regularMarketTime` | Timestamp paired with the regular-market value | Provider receipt time, cache time, or application time |
| `marketState` | When present, a provider-reported response/venue state | Historical proof of the session at `regularMarketTime` |
| `currentTradingPeriod` | Provider schedule claim for the current trading period/date | Complete canonical calendar, instrument-specific eligibility, halt state, or exact observed-price session |
| `exchangeTimezoneName` | Provider timezone identifier (`Asia/Bangkok`) | Proof that a timestamp occurred in a tradable session |
| `timezone` / `gmtoffset` | Provider abbreviation and numeric conversion context | A calendar or a session verdict; fixed offsets also cannot encode all timezone history |
| `exchangeDataDelayedBy` | Provider delay claim when present | Freshness when absent; absence means delay is unknown, not zero |
| `hasPrePostMarketData` | Provider coverage claim for pre/post data | Exchange trading-hours authority |
| `instrumentType` | Provider classification (`EQUITY`, `INDEX`) | Registry identity, tradability, or execution role |
| `quoteType` | Not present in the observed Chart metadata | A field that may be assumed from `instrumentType` |
| provider receipt time | Platform-captured instant after the HTTP response | Exchange observation time or venue state time |
| local application time | Orchestration timing only | Session classification |

The name `regularMarketPrice` is meaningful provider evidence. It is enough to
say “Yahoo labels this price/time pair as regular-market evidence.” It is not
enough to say “the exchange was open when the platform received it,” nor does
it guarantee a recent trade or a real-time feed.

## 5. Provider state versus observation-session distinction

Three temporal questions must remain separate:

```text
observed_at:  When did the provider-labelled price observation occur?
state_at:     At what instant does a provider's reported venue state apply?
received_at:  When did this platform receive the provider response?
```

Yahoo did not supply `marketState` or a provider state timestamp in the
controlled Chart responses. If `marketState` appears, the only defensible
claim without a stronger provider contract is that the response carried that
state when received. `received_at` can anchor provenance (“state received at”)
but must not be rewritten as a provider-authored state timestamp.

A regular observation and a closed response state are not contradictory. The
last regular-market value commonly remains in a response after the venue
closes. Likewise, a delayed regular observation may arrive while the venue is
currently regular. Session and freshness/delay are orthogonal:

- session describes the market phase associated with evidence;
- freshness measures age under a supplied policy; and
- delay is a provider/source-quality fact, when known.

The price observation should reference an observation-session claim. The
provider response should retain its current-state claim independently. A
calendar assessment should be a third object evaluated at `observed_at`.

## 6. Existing calendar and timezone capabilities

There is no canonical exchange-calendar contract, repository, or assessment
service in the current runtime. The architecture explicitly assigns trading
calendars to the Market Data Platform and the Provider Interface includes a
future “Get Exchange Calendar” capability, but the concrete provider base
class exposes only quote, history, fundamentals, and news.

`snapshot_scheduler.is_thai_trading_day()` is not an execution calendar. It
uses weekdays plus the generic `holidays.Thailand` public-holiday set and
falls back to weekends only when that dependency is unavailable. It has no
intraday sessions, random auction boundaries, exchange-specific closure
adjudication, half-days, product schedules, halts, or effective-versioned
provenance. It must remain scheduler-local.

Registry facts expose listing exchange and currency, but the Asset model does
not provide a governed calendar identifier or exchange timezone. Registry can
identify which listing needs a calendar; it cannot assert the phase at a
particular timestamp.

The official SET trading-hours page demonstrates why a calendar must be
instrument-aware. Ordinary equities have morning and afternoon sessions with
an intermission, while some foreign-underlying products and DRs have different
or extended schedules. See the [SET trading-hours specification](https://www.set.or.th/en/market/information/trading-procedure/trading-hours).
Yahoo's one 10:00–16:30 `regular` interval therefore cannot be promoted to the
canonical SET calendar for every returned symbol.

## 7. Candidate architecture comparison

| Option | Strength | Limitation | Decision |
| --- | --- | --- | --- |
| A. Provider-reported state only | Small; preserves explicit `marketState` values | Current Chart responses omit the field; response state is not observation session | Retain as evidence, but insufficient alone |
| B. Separate `MarketSessionEvidence` | Preserves raw state, observation-session claim, timing, timezone, delay, confidence, and provenance without conflation | Does not independently validate the provider claim | **Implement next** |
| C. Separate `MarketCalendarAssessment` | Deterministically evaluates `observed_at` against a versioned, instrument-aware calendar | Requires a governed calendar source, product/calendar binding, exceptions, and lifecycle | **Required before canonical acceptance** |
| D. Combined policy acceptance | Can require agreement or explicitly handle conflicts while keeping owners separate | Is a new execution-policy decision and must not be smuggled into an adapter milestone | Design target after B and C |

Option B is the smallest truthful next step. Option C is still required for a
canonical platform: it validates observations, handles fields without an
explicit session label, and represents holidays/intermissions/product-specific
hours. Option D belongs to Execution Policy after evidence coverage is known.

## 8. Recommended contract changes

### `MarketSessionEvidence`

Add a frozen, versioned Market Data contract containing:

```text
contract_version
session_evidence_ref
observation_ref / envelope_ref
provider_id / provider_version
observation_session_claim          # REGULAR for explicit regularMarket pair
observation_session_basis          # PROVIDER_REGULAR_MARKET_FIELDS
observation_at
provider_reported_state_raw
provider_reported_state_normalized
provider_state_received_at          # provenance anchor, not provider state time
provider_state_at                   # only if provider explicitly supplies it
current_trading_period              # exact supplied pre/regular/post intervals
exchange_timezone
gmt_offset
provider_delay
confidence                         # explicit bounded vocabulary
warnings
provenance
```

The Yahoo adapter may create `observation_session_claim=REGULAR` only when the
selected value and timestamp come from the explicit
`regularMarketPrice`/`regularMarketTime` pair. It must not derive that claim
from symbol suffix, exchange, current local time, timezone, or coarse interval
membership.

`provider_reported_state_normalized` stays `UNKNOWN` when `marketState` is
absent or unrecognized. The raw bounded value is retained for diagnosis.

### `MarketCalendarAssessment`

A later immutable contract should receive:

- exact `observed_at`;
- Registry-resolved listing identity and a governed calendar binding;
- a versioned calendar including holidays, intermissions, auctions, product
  schedules, and effective periods; and
- a caller-supplied assessment instant only for audit context.

It should return the assessed session, calendar/source version, matching
interval, outcome, warnings, and provenance. It must never read local time or
select a calendar from a suffix.

`ExecutionPriceObservation` should retain references to session evidence and
calendar assessment. Its existing scalar `market_session` may remain as a
temporary shadow compatibility projection, but it must be documented as the
observation-session claim—not provider response state.

Execution Policy remains the only owner of acceptance. No M32.3E3S1 change is
authorized to its `CURRENT` and `REGULAR` requirements.

## 9. Mapping table for known Yahoo values

These are accepted input spellings in current code; only `REGULAR` appears in
the synthetic fixture. None appeared in the four controlled Chart responses.

| Yahoo raw value | Normalized provider response state | Observation-session effect |
| --- | --- | --- |
| `REGULAR` | `REGULAR` | None automatically; retain separately from the observation claim |
| `REGULAR_MARKET` | `REGULAR` compatibility spelling | Same |
| `PRE`, `PREPRE`, `PRE_MARKET` | `PRE_MARKET` | Same; retain the exact raw value because coarse normalization loses phase detail |
| `POST`, `POSTPOST`, `AFTER_HOURS` | `AFTER_HOURS` | Same; retain exact raw value |
| `CLOSED` | `CLOSED` | Same; may coexist with a regular observation |
| missing, blank, or unrecognized | `UNKNOWN` | Never defaults to `REGULAR` |
| explicit `regularMarketPrice` + valid `regularMarketTime` | Response state unchanged | Separate provider observation-session claim `REGULAR` |

## 10. Conflict and missing-evidence behavior

| Condition | Required result |
| --- | --- |
| Regular-market pair present; `marketState` missing | Observation-session claim `REGULAR`; provider response state `UNKNOWN` |
| Regular-market pair present; `marketState=CLOSED` | No conflict: regular observation plus closed response state |
| `marketState=REGULAR`; observation timestamp/session source absent | Response state `REGULAR`; observation session remains `UNKNOWN` |
| Provider observation claim and canonical calendar agree | Preserve both; policy may accept under an approved rule |
| Provider claim and calendar assessment disagree | Explicit conflict/quarantine; neither silently overrides the other |
| `currentTradingPeriod` contains `observed_at`, but calendar says intermission/closed | Explicit conflict; provider interval is not promoted |
| Delay field absent | Delay `UNKNOWN`; never zero |
| Delayed regular evidence | Session may be `REGULAR`; freshness/delay policy may still defer or reject it |
| Timezone/offset absent or conflicting | Preserve missing/conflict; no local-time correction |
| Index/reference symbol | Session evidence may be recorded, but Registry eligibility remains authoritative and prevents executable use |

Thai SET symbols were structurally consistent in the controlled sample: all
four had the same omitted state and schedule/timezone shape. That consistency
does not imply identical executable calendars. The index had
`instrumentType=INDEX`, while the listings reported `EQUITY`; current Registry
facts—not Yahoo type or caret prefix—own execution eligibility.

## 11. Tests required

### Contract and mapping

- Frozen, deterministic `MarketSessionEvidence` with distinct observation,
  state, receipt, timezone, schedule, and delay fields.
- Sanitized fixtures for the actual Chart shape with absent `marketState`, and
  for every recognized raw state spelling.
- Exact regular-market pair produces only an observation-session claim; it
  does not manufacture provider response state.
- `marketState=CLOSED` plus a regular pair remains two non-conflicting facts.
- Missing/unrecognized states remain `UNKNOWN`; no `UNKNOWN => REGULAR` path.
- `PREPRE`/`POSTPOST` preserve raw values even when mapped to coarse vocabulary.
- Missing delay stays missing and cannot satisfy a delay policy implicitly.

### Temporal and calendar boundaries

- Receipt time, observation time, provider state time, cache time, and local
  application time are never substituted for one another.
- `currentTradingPeriod` is retained exactly but cannot by itself set the
  observation session.
- A versioned calendar assessment covers SET morning, intermission,
  afternoon, auction, close, holidays, and effective changes.
- Product-specific schedules are selected from governed identity/calendar
  binding, never `.BK`, provider type, or exchange string alone.
- Calendar/provider agreement and disagreement produce distinct outcomes.
- Future/incomparable timestamps stay unknown.

### Regression and shadow behavior

- Existing quote/history/provider response shapes remain unchanged.
- Existing M32 policy still accepts only `CURRENT + REGULAR`.
- Provider/session adapter failures remain per-symbol and exception-contained.
- Execution-plan output remains byte-identical with the shadow off/on.
- Index/reference and ineligible instruments never become executable because
  session evidence is present.
- Static tests prohibit clock reads, suffix rules, Registry lookup, policy
  decisions, or calendar inference in pure provider adapters.

## 12. Go / No-Go recommendation

| Decision | Result | Evidence |
| --- | --- | --- |
| Diagnose current UNKNOWN cause | **Complete** | 4/4 live Chart responses omitted `marketState`; mapping already covers named values |
| Map missing `marketState` to `REGULAR` | **NO-GO** | Would fabricate provider response state |
| Use local time, `.BK`, exchange, or timezone as session | **NO-GO** | These identify context, not the phase of one observation |
| Use `currentTradingPeriod` alone | **NO-GO** | Coarse continuous interval does not encode all SET intermissions/product schedules |
| Add separate provider session evidence | **GO** | Additive, truthful, Market Data-owned, and shadow-safe |
| Label the explicit regular-market price/time pair as a provider observation-session claim | **GO for shadow evidence** | The provider names both value and timestamp as regular-market fields; response state remains separate |
| Treat provider-only evidence as canonical session validation | **NO-GO** | No independent calendar, delay assurance, or provider contract validation |
| Implement canonical planning | **NO-GO** | Lots, calendar, currency/cash-floor, funding, and admission gates remain unresolved |

Provider-only evidence can truthfully improve `REGULAR` **observation-session
coverage** for the explicit field pair. A calendar contract is still required
for canonical validation, conflicts, arbitrary price kinds, holidays,
intermissions, and product-specific schedules.

## 13. Recommended implementation milestone

Proceed with **M32.3E3S2 — Market Session Evidence Contract and Yahoo Chart
Shadow Adapter**:

1. add immutable `MarketSessionEvidence` without changing provider I/O;
2. adapt sanitized Yahoo Chart fixtures, retaining regular-field semantics,
   raw state, schedule, timezone, offset, and delay separately;
3. attach the evidence to the private live shadow and preserve the existing
   scalar session only as an explicitly sourced observation-session
   projection;
4. add coverage/root-cause diagnostics showing observation claim, response
   state, delay availability, and eventual calendar state independently; and
5. keep policy, legacy plan output, and provider call behavior unchanged.

Then perform a separate **Market Calendar Foundation** design/implementation:
governed calendar sources, versioned canonical sessions, identity/calendar
bindings, product exceptions, and conflict assessment. Only after observation
evidence exists should Execution Policy review a combined acceptance rule.

## 14. Expected effect on M32 live-shadow coverage

In the M32.3E3 corpus, 7/8 occurrences had a successful
`regularMarketPrice`/`regularMarketTime` pair. Under the recommended evidence
contract, those seven could carry a provider observation-session claim of
`REGULAR`; the no-envelope case would remain unknown. This does **not** imply
7/8 `CURRENT` outcomes:

- freshness must still be computed from `assessed_at - observed_at`;
- sparse trading or provider lag may yield `STALE`/`EXPIRED`;
- missing delay remains explicit; and
- a future canonical calendar may disagree or be unavailable.

The current assessor checks session before age, so resolving the session claim
will expose the true age distribution rather than automatically improve it.
Complete live-leg coverage remains **0%** until governed positive lot evidence
exists; the development Registry still has 0/21 positive lots. Session work
alone cannot make canonical planning ready.

## 15. Explicit non-goals

- No execution-policy weakening or change to `CURRENT + REGULAR` acceptance.
- No `UNKNOWN => REGULAR` mapping.
- No local-time, suffix, exchange-name, timezone, or instrument-type session
  inference.
- No provider replacement, ranking, request-shape change, or cache change.
- No canonical calendar implementation in S1.
- No execution-plan, canonical-plan, funding, fee, FX, cash-floor, transaction,
  ledger, API, frontend, persistence, or migration change.
- No Registry lot remediation or M31 enforcement.
- No commit or push.

## Verification record

Repository audit covered:

- `backend/services/market_data/yahoo_chart.py`;
- `backend/services/market_data/execution_quote.py`;
- `backend/services/market_data/base.py` and `provider.py`;
- `backend/services/execution_price_observation.py`;
- `backend/services/execution_policy.py`;
- `backend/services/execution_live_evidence_shadow.py`;
- M32.3C/E1/E2 tests and fixtures;
- `backend/services/snapshot_scheduler.py` and dependency inventory;
- Asset/Registry execution facts for exchange/timezone ownership; and
- `MARKET_DATA_PLATFORM.md`, `PROVIDER_INTERFACE.md`, and the universal Asset
  architecture calendar boundary.

Controlled network evidence comprised four successful bounded Chart requests
plus one final single-symbol receipt-time probe. The result was 4/4 successful,
0/4 `marketState`, 4/4 regular price/time pairs, 4/4 timezone and
`currentTradingPeriod`, 0/4 delay fields, and 0/4 `quoteType`. The existing
adapter returned `UNKNOWN` exactly because `marketState` was absent.

No provider or production code was edited. No application database session was
required, no production data was changed, and no commit or push was performed.
