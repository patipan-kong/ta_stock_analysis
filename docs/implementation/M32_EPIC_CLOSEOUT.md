# M32 — Cost-aware Execution Planning Epic Closeout and Adoption-Gate Review

**Closeout date:** 2026-07-15

**Decision:** **M32 foundation complete.** Its immutable contracts, pure
policy, evidence ownership, read-only capability governance, and default-off
live shadow are complete. **Authoritative canonical execution planning is
deferred and remains NO-GO.**

This is a governance closeout, not a declaration that the legacy execution
plan is cost-aware or that the M32 shadow is executable. M32 must not be
reopened merely to add another milestone or improve a completeness metric by
weakening evidence requirements.

## 1. Executive summary

M32 completed the execution-domain foundations needed to describe, validate,
and observe a future cost-aware plan without changing today's plan, posting,
or public response behavior. The architecture is complete for its intended
foundation/shadow scope.

- The current `ExecutionPlanResult` remains the public, gross, legacy plan.
- Current transaction admission uses the isolated raw-symbol compatibility fee
  path and does not consume a planning `FeeQuote`.
- `M32_LIVE_EVIDENCE_SHADOW` remains default-off. When enabled, it is
  post-result, bounded, exception-contained, log-only, and removable.
- No canonical plan, trade order, transaction admission decision, API field,
  frontend view, persistence/history record, or ledger fact is produced by
  M32.

The measured blockers are intentional typed evidence/domain gates, not missing
M32 abstractions. The development Registry has 21 assets with **0/21**
positive governed lots and **0/21** governed fractional-capability records.
The current Yahoo Chart/SET path is `LAST_PRICE_ONLY`: it has no timestamped
bid/ask, quote timestamp, or payload delay coverage, and its SET data is
known to be delayed. The live shadow observed **0 complete policy legs**.

## 2. Final M32 scope

M32 delivered versioned fee schedules/quotes, immutable normalized input,
price/session/market-price/policy/trade-leg evidence, pure constrained sizing,
separate price/book/receipt/cache/delay clocks, non-authoritative lot evidence
preflight, a default-off post-result shadow, and readiness audits.

It did not promise a broker-ready planner. Provider selection, side-aware
price selection, calendar acceptance, portfolio currency/FX, cash-floor/net
funding, transaction requoting, canonical plan lifecycle, and product adoption
remain separately approved domain work.

## 3. Milestone chronology

| Milestone | Result | Closeout interpretation |
| --- | --- | --- |
| M32 design, M32.3A, M32.3D | Architecture and policy designs | Decisions retained as references; no canonical plan activated. |
| M32.1 | `FeeSchedule`/`FeeQuote`, facts-backed selector, ledger parity | Active accounting calculator plus isolated transaction compatibility path. |
| M32.2 | `ExecutionTradeLeg` | Shadow-only leg representation. |
| M32.3B | `NormalizedTradeInput` and quantity intent | Shadow-only normalization boundary. |
| M32.3C | price observation and freshness contracts | Shadow-only evidence/freshness boundary. |
| M32.3E1 | pure policy and constrained sizing | Fixture-backed policy foundation; no live authority. |
| M32.3E2/E3 | live-evidence shadow and observation audit | Safe optional shadow; observed zero complete live legs. |
| M32.3E3R1/R2 | lot governance audit and read-only preflight | No Registry capability write path enabled. |
| M32.3E3S1/S2 | session evidence audit and adapter | Provider observation-session evidence only; no calendar. |
| M32.3E3F1/F2 | price semantics audit and evidence/capability foundation | Last-price evidence only; no execution quote selection. |

Historical documents remain accurate records of their milestone decisions.
This closeout is the final readiness reference; it does not rewrite them.

## 4. Final architecture and data flow

```text
Active production path

recommendations / position sizing
        -> legacy build_execution_plan()
        -> ExecutionPlanResult (gross, legacy public response)
        -> Decision Workspace UI

user-entered quantity + price
        -> portfolio_transactions
        -> broker_fees_compat.quote_transaction_fee_compat()
        -> ledger / Portfolio state

Optional M32 observation path (M32_LIVE_EVIDENCE_SHADOW=ON only)

legacy result + one Registry facts batch + bounded Market Data evidence
        -> Price / session / market-price evidence contracts
        -> freshness + pure ExecutionPolicyBundle evaluation
        -> facts-backed FeeQuote only after constrained quantity
        -> NormalizedTradeInput / ExecutionTradeLeg when complete
        -> private aggregate diagnostic
        -> no return value, mutation, API, frontend, persistence, or order

Deferred authoritative path

governed Registry capabilities + approved quote provider + calendar
+ portfolio currency/cash snapshot + net-funding policy + admission/requote
        -> future canonical plan decision (not implemented by M32)
```

## 5. Contract and subsystem status matrix

| Contract or subsystem | Final classification | Final status / authority |
| --- | --- | --- |
| `FeeSchedule` | `COMPLETE_AND_ACTIVE` | Immutable schedule/calculator is active; transaction selection remains compatibility-based. |
| `FeeQuote` | `COMPLETE_AND_ACTIVE` | Exact calculator supports active ledger parity; planning quotes are not admission authority. |
| Facts-backed fee-selection boundary | `COMPLETE_SHADOW_ONLY` | Implemented for policy/shadow; transactions retain compatibility until Registry-backed admission is approved. |
| Transaction ledger parity | `COMPLETE_AND_ACTIVE` | BUY/SELL posting preserves existing fee, tax, cash, cost-basis, and P&L behavior. |
| `ExecutionTradeLeg` | `COMPLETE_SHADOW_ONLY` | Immutable projection; never an order, response, or persistence record. |
| `NormalizedTradeInput` | `COMPLETE_SHADOW_ONLY` | Pure evidence boundary; amount-only evidence remains incomplete. |
| `ExecutionPriceObservation` | `COMPLETE_SHADOW_ONLY` | Scalar observation evidence, not an execution quote. |
| `PriceFreshnessAssessment` | `COMPLETE_SHADOW_ONLY` | Caller-timed diagnostic; thresholds are not execution approval. |
| `MarketSessionEvidence` | `COMPLETE_SHADOW_ONLY` | Provider observation claim is distinct from state/calendar. |
| `LastPriceEvidence` | `COMPLETE_SHADOW_ONLY` | Provider regular-last, not authoritative last trade/executable price. |
| `TopOfBookEvidence` | `COMPLETE_SHADOW_ONLY` | Contract/fixtures exist; no current usable live book source. |
| `DeclaredProviderDelayEvidence` | `COMPLETE_SHADOW_ONLY` | Governed container; no inferred/zero delay or active binding. |
| `MarketPriceEvidenceSet` | `COMPLETE_SHADOW_ONLY` | Retains independent components/clocks; does not choose a price. |
| `ProviderMarketPriceCapability` | `COMPLETE_READ_ONLY_GOVERNANCE` | Static/sanitized capability assessment; no routing/suitability decision. |
| `ExecutionPolicyBundle` | `COMPLETE_SHADOW_ONLY` | Pure constrained-sizing/lifecycle policy, fixture-backed only. |
| Lot-capability evidence/preflight | `COMPLETE_READ_ONLY_GOVERNANCE` | Strict parser/preflight exists; commit is refused and no projection update exists. |
| Authoritative Registry capability projection | `DEFERRED_EXTERNAL_DEPENDENCY` | Requires reviewed external per-listing evidence before a separately approved write/lifecycle milestone. |
| Authoritative provider execution-quote path | `DEFERRED_EXTERNAL_DEPENDENCY` | Requires a reviewed provider offering usable side-aware, timestamped quote evidence. |
| Live-evidence shadow | `COMPLETE_SHADOW_ONLY` | Default-off, post-result, bounded, deduplicated, exception-contained. |
| Private diagnostics | `COMPLETE_SHADOW_ONLY` | Aggregate low-cardinality logging; detailed objects are discarded. |
| Canonical execution plan | `DESIGNED_NOT_IMPLEMENTED` | No canonical projection, cost-aware funding aggregation, response, or rollout. |
| Frontend adoption | `EXPLICITLY_OUT_OF_SCOPE` | UI consumes only legacy `ExecutionPlanResult`. |
| Transaction admission/requote | `DESIGNED_NOT_IMPLEMENTED` | E1 requires future revalidation/requote; writes do not consume policy legs/quotes. |
| Persistence/history/lifecycle | `DEFERRED_DOMAIN_DEPENDENCY` | Needs canonical plan/intent lifecycle and product history decision. |

## 6. Production behavior currently active

The public endpoint builds and returns only the legacy `ExecutionPlanResult`:
funding actions, BUY actions, gross cash summary, status, warnings, and legacy
funding breakdown. The Decision Workspace consumes that exact type. There is
no public M32 canonical-plan, leg, normalized-input, price-evidence, or
policy-result surface.

Transaction writes remain the ledger authority. They use
`quote_transaction_fee_compat()` before mutation to preserve raw-symbol
schedule behavior. The shared M32 fee calculation preserves ledger parity, but
a planning `FeeQuote` is not persisted, reused, or accepted at admission.

## 7. Shadow and read-only behavior available

The optional live shadow may continue in controlled development/observation
environments. It can reuse the plan facts batch; collect bounded/deduplicated
provider evidence; retain price/session/receipt/cache/delay evidence without
filling absences; run pure policy logic only when supplied evidence permits;
and emit aggregate low-cardinality diagnostics while preserving legacy parity.

The Registry lot-capability and Market Price capability CLIs may continue as
read-only governance tooling. They must not become inference tools, network
probes, automatic remediation, or commit modes without a new approved
milestone.

## 8. Measured evidence and readiness results

| Area | Measured/current result | Meaning |
| --- | --- | --- |
| Registry lot coverage | 0/21 positive governed lots | No resolved live instrument passes the v1 lot gate. |
| Fractional evidence | 0/21 governed records | Stored `False` values are bootstrap defaults, not capability evidence. |
| Live shadow outcomes | 0 complete policy legs in E3 corpus | No live fee/normalization/leg coverage claim is available. |
| Yahoo regular-last | Price/time/currency commonly available | Useful provider-last evidence only. |
| Yahoo session | Provider `REGULAR` observation claim can be retained | Not response-state or calendar validation. |
| Yahoo SET path | `LAST_PRICE_ONLY` | No timestamped bid/ask or book sizes/clock. |
| Provider delay | SET declared delayed; payload delay unavailable | Absence is unknown, never zero. |
| Legacy parity | Shadow off/on outputs matched in controlled tests | Safety property, not execution readiness. |

## 9. Explicit blockers

1. No approved per-listing lot/fraction evidence for the supported Registry
   wave.
2. No reviewed provider path with identity/currency/session-bound timestamped
   side-aware bid/ask and known delay behavior.
3. No governed, versioned listing/product-bound Market Calendar.
4. No Portfolio-owned base/valuation currency and immutable cash/NAV snapshot;
   no approved FX ownership for a non-THB scope.
5. No approved cash-floor, net-of-cost funding, residual/deferred-leg, or
   insufficient-net-cash semantics.
6. No transaction admission/requote contract binding chosen evidence to writes.
7. No canonical plan API/frontend/history/lifecycle/rollback product decision.
8. No retained queryable observation window proving coverage and rollback.

## 10. Adoption-gate matrix

| Gate | Current status | Owner | Required evidence / pass condition | Current blocker | Remediation milestone/domain |
| --- | --- | --- | --- | --- | --- |
| A. Registry capability | Blocked | Asset Registry + steward | All active supported symbols have approved per-listing/effective positive lot and explicit fractional fact; preflight is 100% governed/identity-matched | 0/21 governed lots/fractional records; writes unavailable | Registry capability governance / future E3R3 after external evidence |
| B. Market-price evidence | Blocked | Market Data + provider governance | Reviewed path provides side-aware bid/ask, quote clock, currency, identity, delay, sizes/depth, and bounded operation | Yahoo Chart/SET is delayed last-price-only | Provider capability and quote-evidence milestone |
| C. Session/calendar | Blocked | Market Data calendar domain | Versioned calendar evaluates observation time, sessions, intermissions, holidays, auctions, conflicts | Claim is not calendar; no calendar binding/service | Market Calendar Foundation |
| D. Currency/FX | Blocked | Portfolio Runtime + finance | Immutable portfolio currency/cash/NAV and approved FX evidence where needed | THB transitional context only | Portfolio currency and FX domain |
| E. Cash-floor/funding | Blocked | Execution policy + Portfolio Runtime | Approved floor and exact net-cost aggregation/deferred/residual/insufficiency semantics | Legacy plan is gross/cost-basis | Net-funding policy/domain |
| F. Admission/requote | Blocked | Transactions + execution domain | Write-time identity/eligibility/price/quote/quantity revalidation and recorded admitted evidence | Compatibility writes; no canonical leg intake | Transaction admission milestone |
| G. API/frontend/history | Blocked | Product/API + M33 lifecycle | Approved snapshot/intent/history, response, display, audit, rollout, rollback | No canonical product decision/persistence model | M33/product adoption design |
| H. Observation/rollback | Blocked | Platform observability + execution | Retained representative window, root-cause/cost metrics, parity, bounded calls, disable drill | Aggregate-only logs, unproven retention, no complete legs | Observability readiness milestone |

No gate substitutes for another: a regular observation claim is not a current
quote, and a positive lot does not create market-price evidence.

## 11. Explicit reopen triggers

M32 may reopen only when a concrete approved input or decision below exists.
Each opens the smallest required follow-up; none alone authorizes cutover.

1. Human-adjudicated authoritative lot/fraction evidence for named Registry
   assets, with source/version/effective period and approved projection update.
2. A reviewed provider path with timestamped side-aware bid/ask,
   identity/currency/session binding, declared delay behavior, and bounded
   operational coverage.
3. A governed Market Calendar foundation with versioned calendars and explicit
   listing/product bindings.
4. A Portfolio Runtime contract for base/valuation currency plus immutable
   cash/NAV/cash-floor input and approved FX evidence where needed.
5. An approved net-of-cost funding policy for complete/deferred/excluded
   aggregation, residuals, partial evidence, and insufficient cash.
6. An approved transaction admission/requote contract binding evidence to the
   ledger write boundary.
7. A product decision to publish a canonical plan through API/frontend/history
   with lifecycle, audit, rollout, and rollback semantics.
8. A retained observation window demonstrating relevant gates and a rollback
   drill proving disabling shadow leaves legacy behavior/data unchanged.

## 12. Compatibility and rollback position

The authoritative compatibility paths remain intentional:

- `build_execution_plan()` and its endpoint/frontend contract provide the
  current execution-plan response.
- `broker_fees_compat.quote_transaction_fee_compat()` remains the transaction
  posting selector while Registry-backed admission is unavailable.
- Existing ledger rows/replay use persisted transaction values; M32 rewrites
  neither.

The shadow stays default-off. Only `M32_LIVE_EVIDENCE_SHADOW=ON` enables it;
absent, malformed, or other values remain off. Disabling it removes optional
observation behavior without migration, data repair, or public-contract change.

## 13. Technical debt and test-environment findings

Visible, intentional debt includes unversioned historical fee-governance risk
in the legacy recalculation route; future append-only Registry capability
evidence/projection work; and provider/log-retention arrangements insufficient
for an authoritative observation window. Shadow values are diagnostic-only and
discarded after logging.

Focused M32 tests cover immutability, object identity, typed incompleteness,
default-off behavior, bounded calls, and legacy parity. Milestone records also
note pre-existing test-environment limits: missing async pytest support for
selected replay tests, stale optimizer helper call signatures, and Registry
metadata tests sensitive to import order. None proves M32 is incomplete or
safe to activate.

## 14. M33 boundary — Execution Intent Domain

**Recommended M33 start: snapshot/intent contract foundation, not canonical
plan adoption.** It can start now because it can model a decision lifecycle
without claiming that M32 shadow evidence is executable.

M33 may own immutable/persisted `ExecutionPlanSnapshot`, `ExecutionIntent`,
approval/rejection/lifecycle state, provenance/recommendation linkage,
ledger-linked execution evidence, and status derived from ledger/portfolio
facts.

M33 must not mark a M32 shadow leg/input as approved executable evidence;
persist incomplete live evidence as a canonical plan; duplicate M32
fee/funding/accounting rules; make Registry/provider evidence authoritative;
place broker orders; convert intent state into ledger truth; or bypass future
transaction admission/requote.

The first M33 milestone should be a narrowly scoped immutable snapshot/intent
contract foundation with lifecycle/provenance design and tests. It must retain
the legacy-versus-shadow distinction and make no M32 cutover decision.

## 15. Recommended next milestone

Proceed with **M33.1 — Execution Intent Snapshot and Lifecycle Foundation**:

1. design and implement immutable intent/snapshot contracts independent of M32
   shadow completeness;
2. define lifecycle transitions and ledger-derived status evidence; and
3. record recommendation/legacy-plan provenance without treating either as a
   broker instruction.

External owners may collect Registry and provider evidence through existing
read-only tools. That operational evidence work does not reopen M32 by itself.

## 16. What M32 does not currently provide

M32 does **not** provide a canonical executable net-cost plan; execution-ready
Yahoo prices, a timestamped bid/ask source, or an approved selection policy; a
Market Calendar or a claim that `REGULAR` means `CURRENT`; a default SET lot or
governed `fractional_support=False`; portfolio currency/FX, cash-floor, or
net-funding authority; a reusable planning quote at admission; order placement
or ledger truth; or a public plan/leg/price-evidence API, frontend, or
canonical persistence/history.

## 17. Final GO / NO-GO decisions

| Decision | Result |
| --- | --- |
| Close M32 foundation/shadow epic | **GO — complete** |
| Continue default-off live/read-only evidence tooling | **GO — non-authoritative only** |
| Further M32 work without explicit reopen trigger | **NO-GO** |
| Canonical execution-plan adoption | **NO-GO** |
| Treat Yahoo last-price as an execution quote | **NO-GO** |
| Treat Registry defaults/conventions as capability evidence | **NO-GO** |
| Start M33 intent/snapshot foundation | **GO — bounded, non-execution authority** |

## 18. Verification record

This closeout reviewed all M32 design/implementation records, claimed contract
modules, the shadow boundary, public execution-plan endpoint/frontend type,
transaction fee call sites, Registry capability model/preflight, Decision Log,
and repository project-status context. Static verification confirms:

- all documented M32 records and claimed contract modules exist;
- the shadow is default-off unless the environment is exactly `ON`;
- no public canonical M32 plan or frontend surface exists;
- no capability-evidence table/projection update path exists and read-only
  tooling refuses commit;
- transaction admission does not consume a policy planning quote; and
- legacy plan and compatibility fee paths remain present.

No project-context statement claimed that M32 canonical planning, Yahoo
execution pricing, default SET lots, governed bootstrap fractional values, or
quote reuse at admission was complete; no historical record needed rewriting.
No production behavior or data changed. No commit or push was performed.
