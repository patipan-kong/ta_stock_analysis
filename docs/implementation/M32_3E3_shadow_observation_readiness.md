# M32.3E3 — Live Shadow Observation and Canonical Plan Readiness Audit

**Audit date:** 2026-07-15

**Decision:** **NO-GO for an M32.3E4 canonical net-cost plan shadow.** The
M32.3E2 shadow itself is safe to continue in controlled development runs, but
the observation produced zero complete live legs and the current logs cannot
support an observation window.

**Scope:** Audit, measurement, and design only. No production code, public
response, frontend, funding arithmetic, transaction, ledger, Registry data,
provider behavior, persistence model, or policy was changed. No commit or push
was performed.

## 1. Executive summary

M32.3E2 behaved safely under controlled development use. Two calls through the
real `build_execution_plan()` boundary remained byte-for-byte identical with
the shadow off and on. Provider work was bounded and deduplicated once per
plan, Registry facts were reused from the existing batch, exceptions remained
contained, and `RegistryFinding` was zero after the run.

The live evidence is not ready for a canonical plan projection:

1. All 8 observed active symbol occurrences were `INCOMPLETE`; there were no
   complete `NormalizedTradeInput` values or `ExecutionTradeLeg` values.
2. The development Registry contains 21 assets and all 21 have
   `lot_size=None`. In the observation corpus, 6/8 occurrences resolved and
   were eligible, but 0/8 had a positive integer lot size.
3. Yahoo Chart returned `MARKET_LAST`, observation time, receipt time, and THB
   currency for 7/8 occurrences, but all seven had session `UNKNOWN`.
   Consequently freshness was never `CURRENT` under the approved E2 policy.
4. The remaining two occurrences were unresolved Registry identities. One of
   them (`M32E3-NOT-A-SYMBOL`) also produced the intentional provider-incomplete
   case (HTTP 404/no envelope); this is an invalid-input response, not evidence
   of a provider infrastructure outage.
5. Because no live input reached constrained quantity, the FeeQuote,
   normalized-input, and policy-leg stages all had 0% live coverage. Live
   net-cost funding comparisons therefore cannot be claimed.
6. The current structured E2 log records only outcome counts plus plan/time/
   policy references. It omits evidence coverage, root causes, provider calls,
   latency, monetary comparisons, and bounded diagnostic samples. Repository
   configuration does not establish log retention.

Fixture-backed arithmetic proves that fees and lot constraints can make a
gross-balanced plan net-insufficient and can invalidate exact monetary partial
scaling. That is design evidence, not a live coverage result.

M32.3E4 should not begin as a canonical net-cost plan implementation. The next
work should be Registry lot governance, explicit provider session evidence,
and observation instrumentation/artifact generation. After those gates pass,
the conditional private diagnostic design in §13 is the narrowest appropriate
E4 scope.

## 2. Test environment and methodology

### Environment

- Repository working tree on Windows, Python from `backend/venv-test`.
- Configured non-production PostgreSQL development database
  `_ta_stock_analysis` at the configured development host.
- Default Market Data provider: `YahooChartProvider`.
- Controlled flag use: `M32_LIVE_EVIDENCE_SHADOW=ON` only for the measured
  processes; it was reset to `OFF` afterward.
- Development Registry at measurement time: 21 assets, all active SET/THB
  equities, all `fractional_support=False`, all `lot_size=None`.
- Database sessions were rolled back. No Registry or portfolio row was edited
  to improve coverage, and `RegistryFinding` was 0 after measurement.

### Observation corpus

Two scenarios ran through the real `build_execution_plan()` boundary:

| Scenario | Input | Legacy result |
| --- | --- | --- |
| BUY, sufficient cash | Portfolio 4, `KBANK.BK`, 0.1% allocation | `NO_SELLS_NEEDED`; 1 BUY; cash remained positive |
| BUY, funding gap | Portfolio 4, `KBANK.BK` at 20% plus `GOOGL01.BK` at 5% | `INSUFFICIENT`; 2 BUYs; no active funding source |

The current development data has no active SELL/REDUCE signal matching a held
symbol (the only cached REDUCE was `BGRIM.BK`, which was not held). Therefore
SELL-only, REDUCE, and mixed coverage could not be obtained naturally without
changing portfolio/analysis data. Four additional runs called the private E2
projection directly with constructed plan actions while retaining live Yahoo,
live Registry, and already-loaded development holding evidence:

| Scenario | Evidence status |
| --- | --- |
| SELL-only `AOT.BK`, full 5,000-share holding | Hybrid live: action fixture; live provider/Registry/holding |
| REDUCE `KBANK.BK` by the explicit 0.4 fraction | Hybrid live: action fixture; live provider/Registry/holding |
| Mixed BUY `AAPL01.BK` plus full SELL `AOT.BK` | Hybrid live: action fixture; live provider/Registry/holding |
| BUY `M32E3-NOT-A-SYMBOL` | Hybrid live: action fixture; intentional provider/Registry incomplete case |

This yields 6 runs, 8 active symbol occurrences, and 5 unique symbols:
`KBANK.BK`, `GOOGL01.BK`, `AOT.BK`, `AAPL01.BK`, and
`M32E3-NOT-A-SYMBOL`.

### Evidence classes

- **Measured live:** development Registry, holdings, Yahoo envelopes, timing,
  call counts, E2 outcome counts, and two real-plan parity checks.
- **Hybrid live:** constructed SELL/REDUCE/mixed action records joined to real
  development Registry, holding, and Yahoo evidence.
- **Fixture evidence:** exact fee, lot residual, and net-funding arithmetic
  where complete facts are required but development Registry lots are absent.
- **Static finding:** source-level ownership, logging/retention capability, and
  canonical-plan dependency analysis.

The corpus is a one-shot readiness sample, not an observation window. It does
not establish daily provider reliability, percentile latency, or production
traffic distributions.

## 3. Live coverage metrics

Coverage below uses the 8 active symbol occurrences as the denominator. A
repeated symbol in a different plan remains a separate execution-evidence
observation.

| Metric | Count | Rate |
| --- | ---: | ---: |
| Total active symbols observed | 8 | — |
| Unique symbols | 5 | — |
| `COMPLETE` | 0/8 | 0.0% |
| `DEFERRED` | 0/8 | 0.0% |
| `INCOMPLETE` | 8/8 | 100.0% |
| `EXCLUDED` | 0/8 | 0.0% |
| `ERROR` | 0/8 | 0.0% |
| Registry resolved | 6/8 | 75.0% |
| Eligible | 6/8 | 75.0% |
| Positive integer `lot_size` | 0/8 | 0.0% |
| `fractional_support=False` | 6/8 | 75.0% overall; 100% of resolved occurrences |
| THB Registry listing currency | 6/8 | 75.0% overall; 100% of resolved occurrences |
| Provider `MARKET_LAST` | 7/8 | 87.5% |
| Provider observation time | 7/8 | 87.5% |
| Provider receipt time | 7/8 | 87.5% |
| `REGULAR` session | 0/8 | 0.0% |
| Provider currency | 7/8 | 87.5% |
| `CURRENT` freshness | 0/8 | 0.0% |
| FeeQuote produced | 0/8 | 0.0% |
| Complete `NormalizedTradeInput` | 0/8 | 0.0% |
| Policy `ExecutionTradeLeg` | 0/8 | 0.0% |
| Provider no-envelope responses | 1/8 | 12.5% |
| Provider infrastructure failures | 0/8 | 0.0% |
| Provider timeouts | 0/8 | 0.0% |
| Registry infrastructure failures | 0/8 | 0.0% |

All seven available provider envelopes carried `MARKET_LAST`, observation
time, receipt time, and THB. They also all carried `UNKNOWN` session with the
warning `Yahoo Chart payload has no recognized market session`. Freshness
assessment therefore stopped at `SESSION_UNKNOWN`; no stale/expired status is
reported even when observation age would otherwise exceed a threshold.

The real sufficient-cash plan contained one resolved/eligible symbol and still
produced one `INCOMPLETE` result because `lot_size` was absent. The real
funding-gap plan produced two `INCOMPLETE` results: missing lot for the resolved
`KBANK.BK`, and unresolved Registry identity for `GOOGL01.BK`.

## 4. Root-cause breakdown

### Primary cause assigning every incomplete occurrence once

| Primary cause | Count | Evidence |
| --- | ---: | --- |
| Missing Registry `lot_size` | 6 | Every resolved/eligible occurrence stopped at capability readiness before sizing |
| Unresolved Registry identity | 2 | `GOOGL01.BK` had provider evidence; `M32E3-NOT-A-SYMBOL` also returned the intentional provider no-envelope case |
| **Total** | **8** | Every `INCOMPLETE` occurrence classified |

### Non-exclusive evidence gaps

| Requested root-cause class | Count / disposition |
| --- | --- |
| Unresolved Registry identity | 2 occurrences |
| Ineligible/non-tradable/reference | 0; the two non-eligible occurrences were ordinary unresolved identities |
| Missing `lot_size` | 6 resolved occurrences; all 21 development Registry assets have the same gap |
| Unsupported fractional capability | 0 among resolved facts; capability was unknowable for 2 unresolved identities |
| Non-THB listing | 0 among resolved facts; listing currency was unknowable for 2 unresolved identities |
| Missing `MARKET_LAST` | 1, the no-envelope case |
| Missing observation time | 1, the no-envelope case |
| Missing receipt time | 1, the no-envelope case |
| Unknown/non-regular session | 7 available envelopes; all were `UNKNOWN` |
| Missing provider currency | 1, the no-envelope case |
| Stale/expired price | 0 explicit assessments; session validation precedes age classification and returned `SESSION_UNKNOWN` |
| Missing holding evidence | 0 in measured SELL/REDUCE inputs; both used already-loaded positive holdings |
| Missing value intent | 0 in observed BUY inputs |
| Fee schedule unavailable | 0 observed; quote creation was not reached because earlier gates failed |
| FeeQuote mismatch/expiry | 0 observed; quote lifecycle was not reached |
| Policy contract error | 0 |
| Provider infrastructure failure | 0; the single no-envelope/HTTP 404 case was an intentionally invalid symbol, not an outage; 0 timeouts |
| Registry infrastructure failure | 0 |

`DEFERRED_BELOW_EXECUTABLE_LOT` was not observed because a valid Registry lot
is required before the quantity policy can decide that an amount is below one
lot. Likewise, FeeQuote coverage of 0% means “not reached,” not “free” or
“schedule unavailable.”

## 5. Provider and Registry readiness

### Provider

Yahoo Chart preserved the core market evidence well for valid symbols:
7/7 available envelopes had a market-last value, exchange observation time,
provider receipt time, and currency. A dedicated deduplication probe requested
8 entries containing 7 unique symbols; the provider boundary made 1 logical
batch call and 7 per-symbol HTTP attempts.

Session evidence is the provider blocker. The actual payload path did not
produce a recognized `REGULAR` value for any successful symbol. M32.3E2
correctly left session unknown; it did not infer session from Bangkok time,
exchange, observation timestamp, or a calendar. A future fix must establish an
authoritative Market Data-owned session source or explicitly approved calendar
assessment. It must not weaken the E1 policy or treat an absent provider field
as regular.

The intentional invalid symbol produced a fast HTTP 404 and typed missing
evidence. This proves failure containment but is not classified as provider
infrastructure failure. There were no timeouts or escaping exceptions. A
one-shot sample cannot establish provider reliability or timeout rates.

### Registry

Identity, eligibility, fractional capability, and currency were coherent for
the 6 resolved occurrences. Lot coverage is the absolute blocker:

| Registry population | Result |
| --- | ---: |
| Assets | 21 |
| Positive integer lot size | 0/21 (0.0%) |
| `fractional_support=False` | 21/21 (100.0%) |
| THB listing currency | 21/21 (100.0%) |

No runtime default to one is permitted. Lot values require governed Registry
evidence and remediation outside this milestone. `GOOGL01.BK` remains a
current-held but unresolved symbol and independently prevents supported-
universe cutover readiness.

## 6. Performance and call-count measurements

The exact E2 projection was timed for each of the six controlled scenarios:

| Scenario | Shadow latency | Logical provider batches | Per-symbol calls |
| --- | ---: | ---: | ---: |
| Real BUY, sufficient cash | 0.337 s | 1 | 1 |
| Real BUY, funding gap | 0.257 s | 1 | 2 |
| Hybrid-live SELL-only | 0.278 s | 1 | 1 |
| Hybrid-live REDUCE | 0.099 s | 1 | 1 |
| Hybrid-live mixed BUY/SELL | 0.289 s | 1 | 2 |
| Hybrid-live provider-incomplete | 0.043 s | 1 | 1 |
| **Average / maximum** | **0.217 s / 0.337 s** | **6 total** | **8 total** |

Within each plan, active symbols were deduplicated: 8 active occurrences led
to exactly 8 per-symbol attempts, with no duplicate call inside a plan. Symbols
repeated across separate plans were fetched again, as expected; there is no
cross-plan execution-evidence cache in M32.3E2.

A separate seven-unique-symbol provider batch took 0.522 s wall time. The five
valid equities completed in approximately 0.474–0.503 s each under concurrent
execution. `^SET.BK` succeeded in approximately 0.037 s, while the intentional
invalid symbol returned HTTP 404 in approximately 0.042 s. These are
development one-shot values, not service-level latency percentiles.

The two real execution-plan responses were byte-identical with the shadow off
and on: **2/2 parity (100%)**. A cold/warm baseline timing subtraction was
discarded because query/provider cache ordering made it noisy; the direct
projection timings above are the relevant shadow measurements.

## 7. Legacy versus policy cost comparison

There were no complete live legs, so no live legacy-versus-policy monetary
comparison exists. The following exact values are fixture evidence using the
production `SET_STANDARD` version-1 FeeQuote calculator and approved E1 lot
policy (`lot_size=100`, non-fractional, THB):

The measured real plans exposed legacy gross BUY totals of ฿783.33 for the
sufficient-cash case and ฿195,833.06 for the funding-gap case. Policy gross,
cost, and net values were unavailable because neither plan reached a complete
leg. The hybrid-live action fixtures likewise exposed legacy/reference values
(including ฿280,450 for the full AOT sell and ฿53,236.40 for the 40% KBANK
reduction), but no policy monetary projection. These amounts are not promoted
to live comparisons.

| Diagnostic | Legacy gross | Policy gross | Estimated cost | Policy net cash | Residual |
| --- | ---: | ---: | ---: | ---: | ---: |
| BUY value ฿1,050 at ฿10 | ฿1,050.0000 | ฿1,000.0000 (100 shares) | ฿1.6799 | ฿1,001.6799 required | 5 shares / ฿50.0000 |
| SELL 200 shares at ฿10 | ฿2,000.0000 release | ฿2,000.0000 | ฿3.3598 | ฿1,996.6402 proceeds | 0 shares |

The BUY fixture demonstrates a 4.76% value residual after flooring 105
requested shares to one 100-share lot. This is materially large in the
fixture, but no production materiality threshold has been approved.

The SELL fixture shows that gross release systematically overstates available
cash by fees (฿3.3598 here, 0.16799%). Whether that is “material” at plan level
requires an approved tolerance and a representative live sample.

## 8. Net-funding correctness findings

Fixture-backed net funding demonstrates a correctness gap that the legacy
gross arithmetic cannot represent:

```text
Cash before                         ฿1,000.0000
BUY: 200 × ฿10 gross               ฿2,000.0000
BUY fees / net requirement              ฿3.3598 / ฿2,003.3598
SELL: 100 × ฿10 gross              ฿1,000.0000
SELL fees / net proceeds                ฿1.6799 /   ฿998.3201

Legacy gross funding gap           ฿1,000.0000
Legacy gross sell closes gap       ฿1,000.0000
Net-cost funding gap                    ฿5.0397
Difference                              ฿5.0397
```

Therefore current cash can appear exactly sufficient while net-cost cash is
insufficient. Gross sell proceeds also overstate funding by the sell quote's
cost, and BUY cash requirements understate funding by the buy quote's cost.

Exact monetary partial scaling can conflict with lot-valid quantity. With a
100-share holding at ฿10 and a ฿500 funding gap, legacy scaling can request a
0.5 release fraction (50 shares). Under a 100-share lot policy, the executable
quantity floors to zero and is deferred below one lot; it cannot release the
exact requested ฿500. This conflict is fixture/static evidence because live
Registry lots are absent.

No cash-floor conclusion can be measured. There is no approved cash-floor
policy or immutable cash-floor snapshot contract in the live path, and there
are no complete live plans. The fixture above is net-insufficient even at a
zero floor; any positive supplied floor would increase the gap. E3 does not
invent a floor value.

## 9. Observability assessment

Current E2 logging is insufficient for an observation window.

### What is currently safe

- `ShadowCanonicalPlanDiagnostic.low_cardinality_labels()` contains only the
  five outcome counts (`COMPLETE`, `DEFERRED`, `INCOMPLETE`, `EXCLUDED`,
  `ERROR`).
- Symbol and asset ID are absent from those labels.
- The emitted structured record includes plan reference, assessment time,
  policy bundle reference, and aggregate outcome counts.
- The private per-symbol diagnostic is bounded by the existing 25-symbol
  provider limit and is discarded after logging the aggregate.

### What is missing

- No low-cardinality counters for facts resolution, eligibility, lot,
  fractional capability, currency, price kind, timestamps, session,
  freshness, FeeQuote, normalization, leg, or root cause.
- No latency, logical batch count, per-symbol attempt count, failure/timeout
  count, or deduplication field.
- No plan-level gross/net comparison or residual totals.
- No bounded symbol-level diagnostic sample is emitted by E2.
- E2 has no process-local counter snapshot. The separate M31 eligibility
  observability module does not collect E2 price/policy/cost evidence.
- Repository configuration does not define or prove structured-log retention,
  indexing, restart durability, or an approved query/dashboard.

A process restart discards the in-memory diagnostic immediately. Already
emitted records survive only if the deployment's external log sink retains
them; that retention could not be established from the repository. The current
records cannot reconstruct the required coverage or root-cause report even if
retained.

A persistence table is not justified. Prefer:

1. aggregate low-cardinality structured logs for every plan;
2. bounded diagnostic samples per root-cause key, following the existing M31
   observability pattern; and
3. a read-only controlled-run command that writes a reviewed JSON artifact
   containing per-symbol remediation evidence outside metric labels.

That artifact can generate symbol-level Registry/provider remediation reports
without high-cardinality metrics. It should record build/version, environment,
window, provider/policy references, and anonymized plan reference where
appropriate. A database migration should be reconsidered only if the approved
log sink cannot meet retention/audit requirements.

## 10. Remaining blockers

1. **Registry lots:** 0/21 development assets have positive lot evidence.
2. **Provider session:** 0/7 successful live envelopes produced `REGULAR`.
3. **Supported identity:** `GOOGL01.BK` remains unresolved despite being a
   current holding; the accepted executable universe is not fully covered.
4. **No live quote/leg sample:** FeeQuote, normalized input, and policy leg all
   have 0% live coverage because earlier gates stop evaluation.
5. **No observation window:** one-shot measurements cannot establish
   reliability, failure rate, latency percentiles, or market-state behavior.
6. **Insufficient telemetry:** current logs cannot produce the required
   evidence/root-cause/cost report and retention is unverified.
7. **Portfolio currency:** the E2 THB context remains transitional; Portfolio
   Runtime has no authoritative base/valuation currency ownership.
8. **Cash floor:** no approved policy or immutable snapshot input exists.
9. **Net funding semantics:** active/deferred/excluded leg aggregation,
   residual treatment, insufficient-cash status, and exact scaling behavior
   are not canonical contracts.
10. **No transaction revalidation:** quote expiry/requote and transaction
    admission remain outside planning.
11. **No canonical history/rollout contract:** even a private plan diagnostic
    needs versioned comparison and rollback evidence before later adoption.

## 11. Canonical shadow acceptance gates

These are readiness gates, not new execution policy:

### Per-plan hard gates

- 100% of active supported symbols resolve to eligible Registry facts.
- 100% have governed positive integer lot size, explicit fractional support,
  and listing currency matching the supplied planning currency.
- Every active leg has identity-bound `MARKET_LAST`, observation/receipt time,
  accepted session, provider currency, `CURRENT` assessment, facts-backed
  FeeQuote, complete normalized input, and policy leg.
- Any incomplete/excluded/error leg is kept out of net arithmetic and makes
  plan readiness explicitly partial or blocked; it is never treated as zero
  cost or zero quantity.
- All monetary totals use exact `Decimal` values from retained legs/quotes.

### Observation-window gates

- Registry preflight reports 100% coverage for the approved executable sample
  universe; exceptions are Registry-governed unsupported declarations.
- A representative window includes BUY, full SELL, REDUCE, mixed, sufficient-
  cash, funding-gap, and exact-scaling cases from real plan output.
- Provider evidence includes both open and closed market periods, and session
  mapping is reviewed against raw provider evidence.
- Zero unexplained `ERROR` outcomes, zero duplicate calls within a plan, and
  100% legacy response parity.
- Fee/normalization/leg coverage is high enough to compare net funding across
  a representative sample; the exact promotion threshold and window length
  require operational approval after instrumentation exists.
- Latency and provider failure thresholds are approved from a multi-run
  distribution, not this six-run sample.
- Structured logs/artifacts are retained and queryable across process restarts,
  and a rollback drill proves that disabling the shadow changes no data.

### Policy/domain gates

- Portfolio Runtime owns base/valuation currency and cash snapshot evidence.
- A cash-floor policy is approved and supplied by reference; E4 must not choose
  the floor.
- Residual, deferred-leg, exact-scaling, and insufficient-net-cash behavior is
  approved.
- No FX is needed for the supported E4 sample, or FX remains an explicit block.

## 12. Go / No-Go recommendation

| Decision | Result | Evidence |
| --- | --- | --- |
| Continue controlled M32.3E2 development shadow | **GO** | 2/2 byte parity; bounded calls; no escaping errors or writes |
| Use current logs for an observation window | **NO-GO** | Outcome counts alone cannot calculate requested coverage/root causes/costs; retention unproven |
| Treat policy inputs/legs as live-ready | **NO-GO** | 0/8 complete, 0/8 lots, 0/8 regular/current session |
| Implement M32.3E4 canonical net-cost shadow now | **NO-GO** | No complete live legs or live cost comparison; currency/cash-floor/net-funding contracts absent |
| Prepare an E3 follow-up for Registry/provider/observability readiness | **GO** | Additive, read-only preparation can create the evidence required for a later decision |

M32.3E4 may proceed only after the gates in §11 are demonstrated. The
conditional design below is suitable for review, not implementation approval.

## 13. Recommended M32.3E4 scope

If the gates pass, keep M32.3E4 private, post-result, default-off, and
non-persistent. It should calculate a canonical **diagnostic**, not activate a
canonical execution plan.

### Immutable diagnostic contract

`CanonicalNetCostPlanDiagnostic` should retain, by identity/reference:

- contract version, deterministic diagnostic reference, legacy plan reference,
  build/environment, assessment time, and policy bundle reference;
- immutable planning-currency context and caller-supplied
  `CashFloorSnapshot` (`cash_before`, currency, captured time, source,
  cash-floor amount, and approved policy reference);
- constrained complete active BUY and SELL/REDUCE legs;
- typed deferred, excluded, incomplete, and error entries, each retaining the
  originating recommendation/action and reason;
- per-leg observation, freshness, FeeQuote, normalized-input, policy-result,
  and trade-leg references;
- exact quantity/value residuals without redistribution;
- exact gross BUY, BUY cost, net BUY requirement, gross SELL, SELL cost, net
  SELL proceeds, cash before, supplied floor, cash after, and net funding gap;
- legacy gross totals/status and exact comparison deltas; and
- a readiness status and warnings/provenance.

The cash snapshot is an input. E4 must not define the floor or infer portfolio
currency.

### Net arithmetic

Only complete active legs enter totals:

```text
net_buy_requirement = sum(-BUY FeeQuote.net_cash_effect)
net_sell_proceeds   = sum( SELL FeeQuote.net_cash_effect)
cash_after          = cash_before + net_sell_proceeds - net_buy_requirement
net_funding_gap     = max(0, cash_floor - cash_after)
```

Incomplete, excluded, error, and deferred legs contribute no optimistic zero
value. Their presence changes readiness status and remains visible separately.
Residuals remain attached to their leg and are not redistributed in E4.

### Readiness statuses

- `READY_NET_COST`: every intended active leg is complete and
  `cash_after >= supplied cash_floor`.
- `INSUFFICIENT_NET_CASH`: evidence is complete but net cash is below the
  supplied floor.
- `PARTIAL_EVIDENCE`: at least one complete leg exists, but another intended
  leg is incomplete/excluded/error and totals are explicitly non-authoritative.
- `BLOCKED_EVIDENCE`: no complete executable projection or a required plan-
  level input is missing.
- `NO_ACTIVE_LEGS`: no active intent exists after typed classification.

Deferred and excluded are leg collections, not aliases for plan readiness.

### Rollback and comparison

- Keep the existing legacy `ExecutionPlanResult` as the only returned result.
- Enable E4 through a new explicit default-off shadow flag; do not overload the
  E2 evidence flag.
- Log aggregate low-cardinality readiness/cause/cost-band counters and emit
  bounded diagnostic artifacts; return/persist nothing.
- Disabling E4 restores E2-only behavior without schema/data migration.
- Compare exact legacy gross funding gap/status with net-cost gap/status and
  preserve both; never rewrite legacy arithmetic.

### Implementation boundary

Reuse the existing post-result `execution_plan.py` boundary and the same
facts/provider evidence batch. Do not add a second Registry/provider lookup.
E4 should aggregate already-complete E2 policy legs and caller-supplied cash
evidence; it should not select prices, schedules, lots, sessions, currencies,
or floor policy.

## 14. Explicit non-goals

- No canonical-plan activation or public response field.
- No frontend or optimizer behavior change.
- No legacy funding/cash arithmetic change.
- No transaction admission, requote, write, ledger, or replay change.
- No Registry remediation in this audit.
- No provider replacement or ranking.
- No FX or base-currency implementation.
- No persistence table or migration without a separately demonstrated
  retention need.
- No M31 enforcement, compatibility removal, or ExecutionIntent.
- No fixes to unrelated stale/environmental tests.
- No commit or push.

## Verification record

### Live/read-only verification

- Six controlled shadow scenarios, eight active occurrences, five unique
  symbols.
- Two real development execution-plan runs with the flag off/on: **2/2 exact
  serialized parity**.
- One dedicated provider deduplication probe: 8 requested entries, 7 unique,
  1 batch call, 7 per-symbol attempts.
- Development Registry capability query: 21 assets, 0 positive lots, all 21
  explicit non-fractional and THB.
- Post-run `RegistryFinding`: **0**.
- All database sessions rolled back; no data was remediated or committed.

### Tests

- Focused M32.3E2: **11 passed**.
- Remaining M31/M32 contract/provider group: **141 passed, 32 skipped**;
  combined with focused E2: **152 passed, 32 skipped**.
- Registry/preflight/symbol integration group: **65 passed**.
- Optimizer/transaction/replay-adjacent group: **183 passed, 5 failed**.
  The exact pre-existing failures were:
  - `tests/test_optimizer_pipeline.py::test_consensus_rebalance_high_confidence`
  - `tests/test_optimizer_pipeline.py::test_consensus_no_action_low_score`
  - `tests/test_optimizer_pipeline.py::test_consensus_l1_parse_failure_propagation`
  - `tests/test_optimizer_pipeline.py::test_consensus_critical_flag_forces_rebalance`
  - `tests/test_portfolio_transactions_capability_shadow.py::test_execute_buy_unaffected_by_capability_mismatch`

The four optimizer tests still call `_consensus_engine(l2, l3)` without its
required leading argument. The capability-shadow test still expects a baseline
transaction log event that production does not emit. Neither failure imports
or exercises M32.3E2/E3 changes.

`git diff --check` is included in final verification. No production behavior
was changed by this audit.
