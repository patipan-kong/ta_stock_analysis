# M32.3E3S2 — Market Session Evidence Contract and Yahoo Chart Shadow Adapter

**Date:** 2026-07-15

**Status:** Implemented as a default-off, post-result, private evidence
enhancement. Canonical execution planning remains **NO-GO**.

## Scope and outcome

M32.3E3S2 adds one immutable Market Data-owned `MarketSessionEvidence`
contract. It improves the truthfulness of the M32 live-evidence shadow without
changing a provider request, legacy quote DTO, `ExecutionPlanResult`, funding
calculation, execution policy, Registry record, transaction, ledger, API,
frontend payload, persistence model, or M31 behavior.

Yahoo Chart commonly omits `meta.marketState`, but it can supply an explicit
`regularMarketPrice` and `regularMarketTime` pair. S2 records that pair as a
provider-labelled price-observation claim of `REGULAR`. It does **not** invent
a response-time venue state, a canonical calendar judgment, zero provider
delay, or a tradable instrument identity.

`M32_LIVE_EVIDENCE_SHADOW` remains default-off. When it is on, all work stays
inside the existing exception-contained post-result plan shadow. Disabling it
restores the prior behavior without a schema, Registry, or data change.

## Contract and semantic separation

`services.market_data.session_evidence.MarketSessionEvidence` is frozen,
versioned, and deterministic. It contains:

- envelope/requested/provider identity references and symbols;
- observation-session claim, basis, and observation time;
- raw and normalized provider response state, separately from the claim;
- the receipt instant associated with a supplied response state, but no
  fabricated provider state time;
- exact provider `pre`, `regular`, and `post` schedule intervals;
- provider timezone, GMT offset, and delay when supplied; and
- confidence, warnings, and provenance.

All retained datetimes are timezone-aware. Missing evidence remains `None` or
`UNKNOWN`; a missing delay is not zero.

```text
regularMarketPrice + regularMarketTime
    -> observation-session claim REGULAR

marketState (when present)
    -> separately retained provider response/venue state

currentTradingPeriod / timezone / GMT offset / delay
    -> provider schedule and source-quality context only

future governed calendar at observed_at
    -> not implemented; status remains NOT_AVAILABLE
```

The reused `MarketSession` vocabulary represents the observation claim and
normalized provider state. `ObservationSessionBasis` explicitly identifies
`PROVIDER_REGULAR_MARKET_FIELDS`,
`PROVIDER_EXPLICIT_OBSERVATION_SESSION`, `PROVIDER_STATE_ONLY`, or `NONE`.
Confidence is one of `EXPLICIT_PROVIDER_FIELD`, `PROVIDER_SEMANTIC_PAIR`,
`PARTIAL`, or `UNKNOWN`.

## Yahoo Chart mapping

The pure adapter consumes only the already-loaded allow-listed Chart metadata.
It does not fetch the network, read a clock, query Registry/database/cache,
consult a calendar, or infer from symbol spelling, exchange, local time, or
timezone.

| Yahoo evidence | Observation claim | Provider response state |
| --- | --- | --- |
| Positive `regularMarketPrice` + valid `regularMarketTime` | `REGULAR`, basis `PROVIDER_REGULAR_MARKET_FIELDS`, confidence `PROVIDER_SEMANTIC_PAIR` | Unchanged / separately mapped |
| `marketState=REGULAR` without a complete pair | `UNKNOWN` | `REGULAR` |
| Complete regular pair + `marketState=CLOSED` | `REGULAR` | `CLOSED`; not a conflict |
| `PRE` / `PREPRE` | No automatic claim | `PRE_MARKET`; raw spelling retained |
| `POST` / `POSTPOST` | No automatic claim | `AFTER_HOURS`; raw spelling retained |
| Missing or unrecognized `marketState` | No fallback | `UNKNOWN` |

`currentTradingPeriod` intervals are normalized and retained exactly, but
membership in one never creates a session claim. `exchangeTimezoneName`,
`gmtoffset`, and `exchangeDataDelayedBy` are similarly evidence only. Yahoo's
actual live shape from S1—regular pair present, state/delay absent, timezone
and schedule present—is represented directly by the sanitized S2 fixtures.

## Compatibility projections

`ExecutionQuoteEnvelope` now retains the exact session-evidence object. Its
existing scalar `market_session` remains for compatibility, but projects only
`session_evidence.observation_session_claim`. Provider response state can
never populate that scalar.

`ExecutionPriceObservation` retains the exact same evidence instance by
identity. Its compatibility `market_session` follows only the evidence claim;
thus an explicit provider `marketState=REGULAR` cannot satisfy the existing
`CURRENT + REGULAR` policy in the absence of an observation claim. Existing
callers that do not have session evidence retain their previous scalar-only
behavior.

No `MarketCalendarAssessment` exists in this milestone. Its future result must
be an independent, versioned, identity/calendar-bound assessment evaluated at
the price `observed_at`, not a response-state or provider schedule rewrite.

## Shadow integration and observability

The existing live shadow sequence is unchanged except for evidence retention:

1. collect the existing bounded Yahoo Chart quote envelope;
2. retain/build its `MarketSessionEvidence`;
3. build an observation retaining that object by identity;
4. run the unchanged freshness assessor and policy; and
5. emit private aggregate labels for observation claim/basis, response state,
   delay/timezone/trading-period availability, session-evidence completeness,
   and `calendar_assessment=NOT_AVAILABLE`.

Metric labels are low-cardinality and never include a raw symbol, Registry
asset ID, raw provider state, or provider payload. The private per-symbol
diagnostic may retain the bounded raw state and provenance for debugging, but
is neither returned nor persisted.

This can expose true freshness age once an explicit regular pair is present;
it does not guarantee `CURRENT`, pass the missing Registry lot gate, or create
a complete policy leg.

## Expected coverage and remaining blockers

The S1 controlled sample had a valid regular price/time pair for 4/4
allow-listed Yahoo Chart responses while all 4 omitted `marketState`. In the
M32.3E3 corpus, 7/8 active occurrences had that pair. S2 can therefore record
a `REGULAR` **observation-session claim** for such evidence; it makes no claim
about provider response-state coverage, freshness, delay, or canonical venue
phase.

Canonical planning remains blocked by, at minimum:

- governed positive Registry lot evidence remains 0/21 in the development
  Registry;
- no Market Calendar Foundation exists for SET/product-specific sessions,
  holidays, intermissions, auctions, or effective periods;
- provider delay remains unknown when absent;
- portfolio currency/cash-floor and net-funding contracts are not canonical;
- transaction re-quote/admission and canonical plan rollout remain separate
  work.

## Explicit non-goals

No calendar implementation or SET calendar ingestion, policy change,
`UNKNOWN => REGULAR` fallback, local-time/interval-membership inference,
provider request/legacy response change, provider ranking, Registry lot work,
canonical plan, funding/cash-floor, transaction/ledger/replay, API/frontend,
persistence/migration, M31 enforcement, compatibility retirement, commit, or
push is included.

## Verification

Focused S2 plus M32.3C/E1/E2 tests passed:

```text
56 passed
```

The suite covers frozen/deterministic and timezone-aware evidence, the actual
absent-state Yahoo shape, all named response-state spellings, raw-state
retention, complete-pair-versus-closed-state separation, schedule/timezone/
delay absence, object-identity retention through envelope and observation,
policy compatibility, low-cardinality diagnostics, Registry-capability
incompleteness, bounded provider behavior, and byte-identical legacy plan
output when shadow processing fails. Existing SQLAlchemy datetime/declarative
and pytest-cache permission warnings were non-failing.

The broader S2/C/E1/E2, stable Yahoo Chart provider, and M31 facts/eligibility
verification group passed **111 tests with 32 pre-existing skips**.

### Controlled development probe

The S2 adapter was also exercised with three allow-listed, read-only Yahoo
Chart requests: `KBANK.BK`, `AOT.BK`, and `^SET.BK`. This is measured live
provider evidence, distinct from the sanitized fixtures:

| Metric | Measured result |
| --- | ---: |
| Successful envelopes / regular price-time pairs / `REGULAR` claims | 3/3 / 3/3 / 3/3 |
| Provider response-state evidence | 0/3 (`UNKNOWN`, absent raw state) |
| Delay evidence | 0/3 |
| Timezone and trading-period evidence | 3/3 and 3/3 |
| Freshness under the existing five-/fifteen-minute shadow policy | 3/3 `EXPIRED` |

The index response demonstrates that session evidence is not execution
eligibility. Freshness results describe only the sampled provider observation
age at the caller-supplied assessment instant; they do not alter policy or plan
behavior.
