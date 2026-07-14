# M31.4 — Execution Eligibility Cutover Readiness Audit and Design

**Audit date:** 2026-07-14

**Decision:** **NO-GO for blocking cutover**

**Scope:** Audit and design only. No production behavior, compatibility path, API, persistence model, or financial calculation was changed.

This audit evaluates the working tree containing M31.1, M31.2, and the uncommitted M31.3 implementation. Live coverage measurements used the configured development PostgreSQL database in read-only sessions. Resolver calls ran inside rolled-back savepoints, the outer sessions were rolled back, and `RegistryFinding` remained at zero before and after measurement.

## 1. Executive summary

The architecture is ready for a controlled cutover only in shape, not in data or operational evidence. `ExecutionInstrumentFacts` and the pure `ExecutionEligibility` predicate provide the right authoritative contracts, and all three selected M31.3 application paths consult eligibility. Blocking must not be enabled now.

The concrete blockers are:

1. Registry coverage is far below the required threshold. Current holdings resolve at 19/21 (90.5%), the workspace watchlist resolves at 18/87 (20.7%), and actual optimizer input coverage is only 20.7–21.6% per portfolio.
2. The latest persisted optimizer allocations contain 13 actionable rows, of which 3 are unresolved (`ASML01.BK`, `PLANB.BK`, and `STECON.BK`). Across distinct symbols that is 9/12 eligible (75.0%).
3. The Registry contains 21 assets, all typed `EQUITY`. It contains zero `ETF` assets, zero `DEPOSITARY_RECEIPT_OF` relationships, zero non-tradable assets, and zero current `ASSET_CLASS=INDEX` classifications.
4. All 10 tickers in the legacy ETF compatibility allow-list are unresolved. None of the 18 base/`.BK` spellings derived from the configured DR provider map resolves as a DR; only `MICRON01.BK` resolves at all, and it resolves as `EQUITY`.
5. The M31.3 observation points are too late to enforce: optimizer history is persisted before consultation, execution-plan funding arithmetic is complete before consultation, and transactions are committed before consultation.
6. Manual transaction and execution-plan inputs accept an open-ended symbol universe. Historical coverage can be measured, but 100% coverage of future accepted input is impossible unless admission is defined as “Registry-resolved and tradable.”
7. Shadow telemetry is emitted only to process logs. No durable aggregate or accessible review artifact proves an observation window, disagreement rate, or Registry-failure rate.
8. Failure and rejection contracts are not implemented. In particular, the current eligibility vocabulary represents Registry infrastructure failure as `UNKNOWN_IDENTITY` plus a boolean, which is insufficiently explicit for an authoritative admission API.

`execution_penalty_compat.py` can be mechanically isolated, but it cannot safely be retired yet. It still controls risk scoring for unresolved facts, supplies all `legacy_asset_type` comparison values, and covers symbols that are valid in current workflows but absent from the Registry. Blocking cutover now would suppress current recommendations, produce partial or incorrect plans, and reject currently held or historically traded instruments.

Preparatory work may proceed now: Registry remediation, durable telemetry/metrics, typed error contracts, facts-only shadow mode, and a default-off feature flag. Authoritative blocking must wait until the preconditions in §11 are met.

## 2. Remaining legacy dependency inventory

### 2.1 Exact `execution_penalty_compat.py` dependency

| Call site | Current behavior | Cutover significance |
|---|---|---|
| `backend/services/optimizer/execution_penalty.py:31-34` | Imports `LEGACY_COMPATIBILITY_FALLBACK` and `classify_legacy_compatibility`. | The judgment layer still has a direct production dependency on the deletable module. |
| `backend/services/optimizer/execution_penalty.py:133-202` | Calls the legacy classifier for **every** symbol. For `RESOLVED`/`NOT_TRADABLE` facts it supplies comparison metadata; for `UNKNOWN`/`AMBIGUOUS` or absent facts it selects the actual risk profile. | Compatibility is shadow-only for resolved facts but authoritative for unresolved risk scoring. |
| `backend/services/optimizer/execution_penalty.py:205-318` | `classify_execution(symbol, is_dr, ..., facts=...)` consumes the compatibility decision and publishes `asset_type`, penalties, warnings, caps, slippage, `legacy_asset_type`, and agreement metadata. | Removing compatibility without a facts-only unresolved policy changes optimizer scores and metadata. |
| `backend/services/optimizer/execution_penalty.py:321-391` | Reads `scores_map[symbol]["is_dr"]`, calls `classify_execution`, creates `dr_symbols`, and exposes the legacy-compatible response shape. | The legacy boolean remains connected to execution-risk behavior only through compatibility. |
| `backend/main.py:2052-2078` → `backend/main.py:2115-2120` | `is_dr_symbol()` populates `scores_map.is_dr`; the optimizer batch-resolves facts and computes penalties. | This is the sole production data path feeding `is_dr` into the compatibility classifier. |

Tests import the compatibility constant and exercise the fallback in `backend/tests/test_execution_penalty_m31_2.py`; those are verification dependencies, not additional production callers.

### 2.2 Legacy execution metadata consumers

| Call site | Fields consumed or emitted | Dependency |
|---|---|---|
| `backend/agents/optimizer.py:850-852`, `980-982` | `execution_context` via `build_execution_prompt_block`. | `dr_symbols`, risk warnings, and caps affect optimizer prompts. |
| `backend/agents/optimizer.py:1907-1927` | `position_cap_pct`. | Mutates final BUY/ACCUMULATE weights when a risk cap exists. |
| `backend/agents/optimizer.py:1929-1938` | `execution_risk`, warnings, `asset_type`, and slippage. | Copies legacy-shaped metadata into target allocations. Line 1937 still contains a defensive default to `"EQUITY"` if an existing per-symbol metadata record lacks `asset_type`. |
| `backend/main.py:2258` | Adds `execution_context` to the optimizer response. | Public API exposure. |
| `frontend/lib/api.ts:586-608` | `AssetType = EQUITY | DR | ETF | INDEX`; `ExecutionSymbolMetadata.asset_type`; DR context fields. | The type still includes legacy `INDEX`, omits the M31.2 `OTHER` value, and does not declare the new facts/provenance fields returned by the backend. |
| `frontend/lib/api.ts:611-623` | Optional target-allocation `asset_type` and execution badges. | Backward-compatible field must remain during cutover. |
| `frontend/app/optimizer/page.tsx:430-435` | Renders execution warnings/risk/slippage/cap, not `asset_type` directly. | The current UI does not branch on EQUITY/DR/ETF/INDEX, but external API consumers may. |

The `ExecutionRole` at `frontend/lib/api.ts:1074-1083` and `backend/services/optimizer/execution_optimizer.py` is a different concept: it describes a trade’s job (`STANDALONE`, `FUNDING_SOURCE`, `NOT_NEEDED_TODAY`), not the Registry-backed instrument execution role (`TRADABLE`, `REFERENCE`, `UNKNOWN`). Cutover work must not merge these vocabularies.

### 2.3 Other symbol heuristics touching execution

These do not call `execution_penalty_compat.py`, but they are remaining execution-adjacent heuristic dependencies and prevent a blanket claim that execution has no symbol-shape authority.

| Call site | Heuristic | Current effect | Ownership |
|---|---|---|---|
| `backend/services/broker_fees.py:111-136` | DR regex. | Selects `DR_STANDARD` vs `SET_STANDARD` for BUY/SELL at `portfolio_transactions.py:171` and `:305`. Rates are currently identical, so arithmetic is unchanged, but the public `fee_profile` label differs. | M32 fee quoting/funding scope; it must consume facts or receive a documented temporary exception before “zero heuristic execution classification” can be claimed. |
| `backend/services/registry_symbol_matching.py:56-68`, `:145-153` | Bare/`.BK` suffix fallback. | `execution_plan.py:145` may use an unresolved spelling heuristic to join a holding to a cached SELL/REDUCE signal, which can create a funding action. | Identity compatibility, not instrument taxonomy; final eligibility must gate the resulting action, and the plan path should become facts/canonical-ID based before cutover. |
| `backend/main.py:145-161` | `THAI_SECTOR_MAP` membership appends `.BK`. | Normalizes symbols accepted by BUY/SELL/INITIAL_POSITION routes before the transaction service. | API identity compatibility. It is not an eligibility verdict, but service-level admission must resolve the resulting identity and direct service callers must not bypass it. |
| `backend/services/symbol_resolver.py:51-54`, `:92-157` | Explicit provider map plus DR regex. | Supplies provider symbols and the `is_dr` value used by optimizer compatibility. | Provider/data access may retain provider mapping, but it must no longer make an execution taxonomy or eligibility decision. |
| `backend/services/symbol_normalization.py:24-62` | DR pattern and alpha-to-`.BK` convention. | Used by analytics, timing, canonicalization, and rebuilding, not by the M31 eligibility predicate. | Provider/legacy symbol adapter; out of M31 eligibility policy unless its output is later admitted as a trade. |

Other `is_dr` uses in `fundamental.py`, watchlist/stock response enrichment in `main.py`, `factor_engine.py`, `portfolio_rebuilder.py`, Registry bootstrap helpers, sector lookup, and listing equivalence are provider, analytics, bootstrap, or presentation concerns. They are not transaction-admission decisions. They should be migrated independently where appropriate, but they are not direct M31 blocking gates.

### 2.4 Boundary trace and bypass assessment

| Boundary | Current facts/eligibility use | Why it is not cutover-ready |
|---|---|---|
| Optimizer | Batch facts resolution at `main.py:2115`; risk scoring consumes facts; final shadow consultation at `main.py:2590-2618`. | The result is persisted at `main.py:2351-2372`, and signal/snapshot side effects begin afterward, before eligibility consultation. `get_optimizer_history_detail()` also reconstructs execution optimization at `main.py:2679-2702` without rechecking eligibility. |
| Execution plan | Final buy and active funding actions are batch-resolved and observed at `execution_plan.py:263-289`. | The plan, funding selection, cash release, deployment arithmetic, warnings, and status are already complete. Filtering after line 261 would make the arithmetic inconsistent. |
| BUY/SELL/INITIAL_POSITION | All normal API callers converge on `execute_buy`, `execute_sell`, or `execute_initial_position`; each observes facts after building its response. | Commits occur at `portfolio_transactions.py:229`, `:351`, and `:631`; shadow calls occur at `:254`, `:376`, and `:650`. Admission must move before fee calculation and mutation, while keeping resolution batch/pure boundaries intact. |
| Add holding | `main.py:868-894` calls `execute_initial_position`. | Covered by the service shadow but would be blocked only by service-level pre-admission. |
| Direct ORM/scripts/replay | Some scripts, migrations, replay, and repair code write or reconstruct holdings/transactions directly. | These are not live executable trade admission and should not be retroactively blocked. They must be explicitly excluded from the enforcement adapter so historical replay remains deterministic. |

All normal live paths selected in M31.3 consult eligibility, so there is no missing shadow hook among those three paths. The stricter cutover criterion—no executable action can be produced, persisted, planned, or committed without an authoritative eligibility decision—is **not met** because every current hook is intentionally post-decision.

## 3. Registry coverage assessment

### 3.1 Method

The audit queried current `PortfolioItem`, workspace `Watchlist`, executable `Transaction` (`BUY`, `SELL`, `INITIAL_POSITION`), and `OptimizerHistory` rows. Symbols were batch-adapted through `resolve_execution_instruments()` and evaluated through `evaluate_execution_eligibility()`. No facts were synthesized from compatibility classifiers.

Coverage means `RESOLVED + TRADABLE + non-UNKNOWN instrument form`, which currently maps to `ExecutionEligibilityOutcome.ELIGIBLE`.

### 3.2 Measured coverage

| Population | Rows / distinct symbols | Eligible | UNKNOWN | Coverage |
|---|---:|---:|---:|---:|
| Current portfolio holdings | 21 rows / 21 | 19 | 2 | 90.5% |
| Current workspace watchlist | 87 rows / 87 | 18 | 69 | 20.7% |
| Portfolio 2 actual optimizer input (holdings ∪ workspace watchlist) | 87 distinct | 18 | 69 | 20.7% |
| Portfolio 3 actual optimizer input | 88 distinct | 19 | 69 | 21.6% |
| Portfolio 4 actual optimizer input | 87 distinct | 18 | 69 | 20.7% |
| Latest persisted actionable allocations | 13 action rows / 12 distinct | 10 rows / 9 distinct | 3 rows / 3 distinct | 76.9% rows / 75.0% distinct |
| All historical actionable allocation symbols | 40 distinct | 18 | 22 | 45.0% |
| Historical executable transaction symbols | 52 rows / 25 distinct | 21 distinct | 4 distinct | 84.0% distinct |
| Union of all measured populations | 92 distinct | 21 | 71 | 22.8% |

The two unresolved current holdings are `GOOGL01.BK` and `GULF.BK`. The three unresolved symbols in latest actionable allocations are `ASML01.BK`, `PLANB.BK`, and `STECON.BK`.

The latest per-portfolio evidence is:

- Portfolio 2, history 118 (2026-07-09): 8/11 actionable rows eligible; the three symbols above are unresolved.
- Portfolio 4, history 121 (2026-07-14): 2/2 actionable rows eligible (`KBANK.BK`, `META01.BK`).

### 3.3 Registry content and integrity

| Check | Result |
|---|---:|
| Assets | 21 |
| Asset types | 21 EQUITY; 0 ETF; 0 OTHER |
| Current provider identifiers | 21 |
| `DEPOSITARY_RECEIPT_OF` relationships | 0 |
| Current `ASSET_CLASS=INDEX` classifications | 0 |
| Non-tradable assets | 0 |
| Invalid asset types | 0 |
| Blank required canonical symbol/type/market/exchange/currency fields | 0 |
| Null `tradable` fields | 0 |
| Duplicate current identifier values resolving to multiple assets | 0 |

Native `asset_id` materialization is also absent in the operational tables: 0/21 holding rows, 0/87 watchlist rows, and 0/52 executable transaction rows carry `asset_id`. Dynamic Registry resolution still works for 21 symbols, but the lack of native IDs increases lookup dependence and leaves no row-level proof that current records were adjudicated.

### 3.4 Compatibility universe checks

- Legacy ETF allow-list: 0/10 resolve. `ARKK`, `EEM`, `GLD`, `IVV`, `QQQ`, `SPY`, `TLT`, `VTI`, `XLF`, and `XLK` are all `UNKNOWN`.
- Configured DR provider map, measured as base and `.BK` spellings: 1/18 resolves (`MICRON01.BK`), but 0/18 have form `DEPOSITARY_RECEIPT`; the resolved spelling is Registry `EQUITY`.
- Several current Registry-resolved symbols that the current provider/legacy layer treats as DR—`AAPL01.BK`, `AMZN01.BK`, `META01.BK`, `MICRON01.BK`, and `NVDA01.BK`—are authoritative `EQUITY` facts because the Registry has no DR relationships. This is a Registry data gap, not permission to infer DR from spelling.
- The Registry cannot currently identify a market-index reference because it has no index classification or non-tradable asset. Default analysis references such as `^SET.BK` therefore cannot satisfy the non-tradable-reference criterion.

### 3.5 Measurement limitations

1. Execution plans are not persisted. Their buy symbols are supplied by each request, so there is no historical plan-symbol population to query. Active funding symbols are derived from holdings and are partially covered by holding measurements.
2. BUY/SELL/INITIAL_POSITION request schemas accept arbitrary strings (including strings outside all known watchlists). Historical transaction symbols are only a lower-bound proxy for future admission coverage.
3. `UNKNOWN: no matching asset` does not distinguish a genuine typo/new instrument from a Registry coverage gap. That distinction requires an explicit supported-universe/adjudication process; it must never be inferred from symbol shape.
4. M31.3 telemetry is process-log-only. No repository artifact or database table contains a reviewable observation window, so disagreement and failure rates cannot be measured retrospectively from the application.
5. This audit measured the configured development database, not every deployment environment. Each environment requires the same preflight report immediately before enabling enforcement.

## 4. Unresolved-case classification

| Class | Measured evidence | Required disposition |
|---|---|---|
| Genuinely unknown symbol | None can be proven from current Registry output alone. | Define “supported executable instrument” through Registry governance. Inputs outside it remain typed UNKNOWN and are rejected at execution boundaries; never auto-mint or guess. |
| Registry coverage gap | 69 watchlist symbols, 2 current holdings, 3 latest actionable symbols, and 4 historical transaction symbols are unresolved. | Register and adjudicate every supported current symbol and alias before cutover. Current workflow presence makes these coverage gaps until explicitly declared unsupported. |
| Ambiguous alias | Zero AMBIGUOUS outcomes and zero duplicate current identifier values in this measurement. `GOOGL01`/`GOOGL01.BK`, `GULF`/`GULF.BK`, and `MICRON01`/`MICRON01.BK` show alias-coverage inconsistencies, but the resolver returns UNKNOWN, not AMBIGUOUS. | Add/repair Registry identifiers or record an actual ambiguity. Do not classify these pairs heuristically. |
| Missing classification metadata | Zero incomplete-metadata outcomes among resolved assets; raw required fields are populated. | Retain the M31.1 incomplete-metadata outcome and add a preflight integrity query. |
| Missing DR relationship | Registry has zero DR relationships; every configured/current DR-like instrument has either UNKNOWN or EQUITY facts. | Backfill authoritative `DEPOSITARY_RECEIPT_OF` relationships with one outgoing relationship per DR and verify underlying identities. No regex backfill at runtime. |
| Reference/non-tradable instrument | Registry has zero such assets. | Register supported benchmarks/index references as `OTHER`, current `ASSET_CLASS=INDEX`, `tradable=false`; prove they resolve to `REFERENCE + NOT_TRADABLE`. |
| Registry infrastructure failure | None occurred during the successful audit. The M31.1 batch adapter can carry `resolution_error`. | Promote this to an explicit eligibility outcome and implement boundary-specific policy. Do not conflate it with an ordinary unknown identity. |

Compatibility fallback is still required to preserve current observable behavior for valid current inputs. Removing it today changes unresolved symbols from legacy EQUITY/DR/ETF/INDEX risk assumptions to an as-yet undefined facts-only risk profile, changes penalties/caps/warnings, and removes legacy response diagnostics. It is also the only current ETF classifier, while the Registry resolves none of the compatibility ETF universe.

## 5. Boundary-by-boundary enforcement policy

### 5.1 Authoritative predicate

Future admission must consume a pre-resolved `ExecutionInstrumentFacts` object and produce a typed result without database access:

- `RESOLVED + TRADABLE + form in {EQUITY, ETF, DEPOSITARY_RECEIPT, OTHER}` → `ELIGIBLE`.
- `UNKNOWN` without infrastructure error → `UNKNOWN_IDENTITY`.
- `AMBIGUOUS` → `AMBIGUOUS_IDENTITY`.
- `NOT_TRADABLE` with role `REFERENCE` → `REFERENCE_ONLY`.
- Other `NOT_TRADABLE` → `NOT_TRADABLE`.
- Any resolver/adaptation infrastructure error → new explicit `REGISTRY_FAILURE`, not `UNKNOWN_IDENTITY` with only a side boolean.

`OTHER` is eligible only when Registry identity is resolved, `tradable=true`, and role is `TRADABLE`. It must never mean “fallback equity.”

### 5.2 Outcome policy matrix

| Outcome | Recommendation generation | Final optimizer executable allocations | Execution plan | Manual BUY/SELL/INITIAL_POSITION |
|---|---|---|---|---|
| RESOLVED + TRADABLE | Proceed normally. | Preserve current action and calculations. | Include before funding arithmetic. | Admit before fees/mutation. |
| UNKNOWN | Continue investment analysis, but mark the proposal non-executable. | Remove/downgrade executable BUY/SELL/ACCUMULATE/REDUCE before action persistence; record an exclusion with requested symbol and reason. Do not relabel it EQUITY. | Exclude before buy sizing and funding arithmetic. Mixed requests return a partial plan; all-excluded requests return a blocked plan result. | Reject before fee selection or mutation with typed 422 error. |
| AMBIGUOUS | Continue analysis with an identity-review warning; never select a candidate silently. | Same exclusion as UNKNOWN, but preserve candidate IDs/finding reference in internal telemetry. | Exclude before arithmetic and return an ambiguity-specific exclusion. | Reject with typed 409 conflict; user must resolve identity, not retry the same spelling blindly. |
| NOT_TRADABLE | Analysis/reference use may continue. | Never expose an executable action. | Exclude before arithmetic. | Reject with typed 422 non-tradable error. |
| REFERENCE_ONLY | Continue benchmark/context use. | Never expose as EQUITY or INDEX trade action. | Exclude before arithmetic. | Reject with typed 422 reference-only error. |
| REGISTRY_FAILURE | **Fail open for analysis only:** return scores/narrative with `execution_eligibility_available=false`; do not claim any action is executable. | **Fail closed for executable projection:** suppress all executable actions or return an explicit unavailable projection while preserving analysis. | **Fail closed:** 503; no plan or funding arithmetic should be represented as ready. | **Fail closed:** 503 before any write. |

Recommendation generation and transaction admission intentionally use different failure policy. Investment belief can still be useful during a Registry outage; an irreversible ledger write cannot be admitted without identity/tradability evidence.

### 5.3 Optimizer design

1. Resolve the complete holdings/watchlist symbol set once at the existing session-owning boundary.
2. Keep investment scoring independent from eligibility.
3. Apply eligibility to proposed final actions before `OptimizerHistory`, signal history, recommendation snapshots, or response-time execution optimization is created.
4. Preserve belief evidence in additive fields such as `proposed_action`/`eligibility_exclusion`; do not turn an excluded symbol into a fabricated HOLD without preserving why.
5. Persist the filtered executable view and the exclusion evidence together so history detail cannot reconstruct an action that bypasses eligibility.
6. Historical rows remain immutable and are displayed as historical legacy output; do not retroactively rewrite them.

### 5.4 Execution-plan design

Resolve the union of requested buys and potential active funding symbols once. Filter ineligible symbols **before** `total_deployed`, funding-source selection, `cash_released`, cash remaining, warnings, and status are computed. Deferred funding actions are not executable today and may retain descriptive eligibility metadata without becoming admission candidates.

For a mixed request, return HTTP 200 with a plan computed only from eligible actions plus:

```json
{
  "eligibility_status": "PARTIAL",
  "eligibility_exclusions": [
    {
      "symbol": "ASML01.BK",
      "code": "EXECUTION_INSTRUMENT_UNKNOWN",
      "resolution_status": "UNKNOWN",
      "execution_role": "UNKNOWN",
      "instrument_form": "UNKNOWN",
      "retryable": false
    }
  ]
}
```

If every requested executable action is excluded, return HTTP 200 with empty active action lists, `eligibility_status="BLOCKED"`, unchanged descriptive/deferred content, and no claim that the plan is `READY`. Add a separate `eligibility_status` rather than overloading the existing capital-funding `status` axis.

### 5.5 Transaction admission and API error contract

Admission belongs inside `portfolio_transactions.py`, before fee profile selection, holding lookup/mutation, cash arithmetic, and commit. API-route checks alone are insufficient because services are called directly by tests and other backend code.

Recommended error envelope:

```json
{
  "detail": {
    "code": "EXECUTION_INSTRUMENT_AMBIGUOUS",
    "message": "Execution identity is ambiguous; resolve the Registry finding before trading.",
    "requested_symbol": "ABC",
    "canonical_symbol": null,
    "asset_id": null,
    "resolution_status": "AMBIGUOUS",
    "execution_role": "UNKNOWN",
    "instrument_form": "UNKNOWN",
    "retryable": false
  }
}
```

Status mapping:

- UNKNOWN → 422 `EXECUTION_INSTRUMENT_UNKNOWN`
- AMBIGUOUS → 409 `EXECUTION_INSTRUMENT_AMBIGUOUS`
- NOT_TRADABLE → 422 `EXECUTION_INSTRUMENT_NOT_TRADABLE`
- REFERENCE_ONLY → 422 `EXECUTION_REFERENCE_NOT_TRADABLE`
- REGISTRY_FAILURE → 503 `EXECUTION_REGISTRY_UNAVAILABLE`, `retryable=true`

No default liquidation exception is recommended. Such an exception would violate the approved invariant that unresolved instruments cannot enter executable paths. The two unresolved current holdings must be adjudicated before enforcement. Emergency rollback uses the feature flag in §7 and is operationally auditable; it is not a hidden per-symbol heuristic.

## 6. Compatibility retirement plan

### Phase A — data and observability remediation

1. Define the supported executable universe in Registry governance, not a ticker allow-list in execution code.
2. Register all current holdings, optimizer-reachable watchlist instruments, supported ETFs, and accepted aliases.
3. Add authoritative DR relationships and non-tradable index references.
4. Backfill native `asset_id` where the existing Registry adjudication process permits it.
5. Export low-cardinality counters by boundary/outcome and retain structured disagreement samples long enough for review.

### Phase B — facts-only shadow

Introduce `FACTS_ONLY_SHADOW` mode:

- `execution_penalty.py` no longer lets compatibility select a risk profile.
- For unresolved facts, emit explicit unresolved metadata and apply no taxonomy-specific penalty/cap. Do not project UNKNOWN to OTHER or EQUITY.
- Keep `execution_penalty_compat.py` loaded only to compare/log what legacy would have done.
- Remove `is_dr` from the authoritative scoring-helper signature. Provider/analysis code may still carry it for non-execution purposes.
- Preserve resolved EQUITY/ETF/DR risk calculations exactly.

This mode is safe only after valid current inputs reach complete facts coverage; otherwise it intentionally changes unresolved optimizer scores.

### Phase C — enforce with compatibility available for rollback

Enable `ENFORCE` per environment after criteria pass. Compatibility remains packaged but unreachable in authoritative code. Keep one release window in which the feature flag can restore `LEGACY_FALLBACK` without a schema/data migration.

Retain backward-compatible public fields:

- `asset_type` remains the execution-risk profile string for resolved forms (`EQUITY`, `ETF`, `DR`, `OTHER`).
- `legacy_asset_type` remains nullable/deprecated for one release and is never used for a decision.
- Facts fields (`resolution_status`, `instrument_form`, Registry `execution_role`, source/warning) remain additive.
- Frontend `AssetType` adds `OTHER` and treats `INDEX` as legacy-history-only.

### Phase D — delete compatibility

After the rollback window and reviewed telemetry:

1. Remove the import and call from `execution_penalty.py`.
2. Remove `ASSET_INDEX` baselines and the `is_dr` scoring input.
3. Remove compatibility-only fields or retain them as always-null deprecated API fields for the announced compatibility period.
4. Delete `execution_penalty_compat.py` and convert its behavior tests into structural negative tests.
5. Runtime rollback after deletion is an application-version rollback, not a data migration.

`broker_fees.py` must be addressed in M32 by accepting a fee quote/profile selected from authoritative facts. Until then, its regex is a documented fee-domain exception; because `DR_STANDARD` and `SET_STANDARD` rates are currently identical, this does not change numeric fees, but it still changes the response label and prevents a claim that every execution taxonomy is Registry-backed.

## 7. Feature flag / rollback design

Use one environment-level enum so invalid combinations cannot occur:

`EXECUTION_ELIGIBILITY_CUTOVER_MODE`:

- `LEGACY_FALLBACK` — current M31.2/M31.3 behavior: Registry facts when resolved, compatibility risk profile when unresolved, shadow eligibility only.
- `FACTS_ONLY_SHADOW` — compatibility may be consulted only for telemetry; facts-only risk behavior; no blocking.
- `ENFORCE` — facts-only risk behavior plus optimizer, plan, and transaction admission policy from §5.

Requirements:

1. Default to `LEGACY_FALLBACK` until each environment passes preflight.
2. Read the mode once through a small configuration adapter; do not scatter environment reads across pure helpers.
3. Emit mode and build/version with every eligibility telemetry record.
4. Permit an operational switch from `ENFORCE` to `LEGACY_FALLBACK` without restarting only if the project already has a safe runtime-settings mechanism; otherwise require controlled redeploy/restart.
5. The flag changes behavior only prospectively. It never rewrites Registry, optimizer history, transactions, holdings, or plans.
6. Keep the compatibility module in the deployable artifact through the rollback window. After deletion, rollback means deploying the previous version.

Suggested promotion gate: at least 14 consecutive days and a representative minimum sample at each boundary, with zero non-eligible outcomes for supported instruments, zero unexplained Registry failures, all disagreements reviewed, and a successful rollback drill in a non-production environment. Exact sample thresholds should be set from observed traffic; current log-only telemetry cannot establish them.

## 8. API compatibility impact

### Existing dependencies

- Optimizer consumers receive `execution_context.per_symbol[*].asset_type`, DR summary fields, and target-allocation execution metadata.
- The frontend renders warnings/risk/slippage/caps but does not currently render `asset_type`.
- Frontend type declarations still expect `INDEX`, omit `OTHER`, and omit M31.2 facts/provenance fields.
- Execution-plan `status` currently represents funding sufficiency, so eligibility must use a new orthogonal field.
- Transaction errors are currently mostly string `detail` values; typed object detail is an intentional API extension and client error parsing must accept both during rollout.

### Compatibility rules

1. Successful resolved transactions retain their exact current success response shape and status code.
2. Resolved optimizer and plan outputs remain calculation-compatible.
3. Add `eligibility_status` and `eligibility_exclusions` without removing existing plan fields.
4. Add optimizer exclusion evidence without reusing `execution_warnings`, which describes liquidity/spread judgment rather than admission.
5. Update frontend types before enforcement; keep rendering tolerant of absent fields in historical payloads.
6. Preserve legacy history exactly. `INDEX` may be accepted when reading old payloads but must never be emitted as a new executable instrument form.
7. Document 409/422/503 transaction failures and expose the same stable `code` values to all clients.

## 9. Required test matrix

### Facts and predicate

- Resolved tradable EQUITY, ETF, DR, and OTHER are eligible.
- DR requires exactly one outgoing `DEPOSITARY_RECEIPT_OF` relationship.
- UNKNOWN, AMBIGUOUS, NOT_TRADABLE, REFERENCE_ONLY, and REGISTRY_FAILURE remain distinct.
- Incomplete metadata is UNKNOWN, not EQUITY/OTHER.
- No regex, ticker list, prefix test, provider `is_dr`, or compatibility result can influence the authoritative predicate.

### Optimizer

- Complete facts are batch-resolved once per run; no scoring helper performs DB access.
- Resolved EQUITY/ETF/DR scores, warnings, caps, slippage, and allocations remain bit-compatible.
- Each ineligible outcome is excluded before optimizer history, signal history, snapshot, action summary, and execution optimization persistence/projection.
- Recommendation analysis remains available during REGISTRY_FAILURE, but no action is marked executable.
- History detail cannot recreate an excluded executable action.
- Existing immutable legacy history renders unchanged.

### Execution plan

- Resolve requested buys plus potential active funding symbols in one batch.
- Filter before funding and cash arithmetic.
- Mixed requests produce internally consistent partial plans and typed exclusions.
- All-excluded requests produce no READY plan.
- Deferred funding actions do not become executable through eligibility metadata.
- REGISTRY_FAILURE returns 503 and no misleading plan.

### Transactions

- Eligibility is checked before fees, cash/holding mutation, transaction construction, or commit.
- All five non-eligible outcomes return the specified status/code and leave transaction, holding, cash, fees, and native IDs unchanged.
- BUY, SELL, INITIAL_POSITION, and add-holding route converge on the same service guard.
- Direct service calls cannot bypass the guard.
- Replay, migration, repair, dividends, cash movements, and quantity correction retain their defined non-admission behavior.

### Compatibility and rollback

- `LEGACY_FALLBACK` reproduces current unresolved behavior.
- `FACTS_ONLY_SHADOW` never lets compatibility change output.
- `ENFORCE` blocks consistently at all boundaries.
- A mode switch restores legacy prospective behavior without schema/data migration.
- Static tests prove `execution_penalty.py`, eligibility, plan admission, and transaction admission contain no heuristic classifier or import from compatibility in final mode.
- After deletion, repository search finds no production import of `execution_penalty_compat`.

### API/frontend

- Resolved success payloads remain backward compatible.
- Typed 409/422/503 errors serialize exactly.
- Frontend accepts `OTHER`, facts fields, partial/blocked plans, and both old string and new object error detail during transition.
- Historical `INDEX` values render but cannot be submitted as new executable identity evidence.

### Coverage/preflight

- Environment report covers holdings, optimizer-reachable watchlist, latest actionable allocations, supported ETFs/DRs, plan inputs sampled from telemetry, and transaction admission attempts.
- 100% of the supported executable universe resolves eligible, or every exception is an explicit Registry-governed non-supported declaration—not a heuristic fallback.
- Every supported reference resolves `REFERENCE + NOT_TRADABLE`.
- No valid supported instrument requires compatibility to obtain its form.

## 10. Go / No-Go recommendation

**NO-GO. Do not implement or enable blocking cutover now.**

| Criterion | Current evidence | Result |
|---|---|---|
| 100% Registry resolution for supported executable instruments or documented exception policy | Holdings 90.5%; watchlist/optimizer input about 21%; accepted request universe undefined/open-ended. | Fail |
| Zero valid current instruments requiring heuristic classification | 10/10 compatibility ETFs unresolved; zero DR relationships; unresolved current/actionable symbols use compatibility. | Fail |
| No executable path bypassing eligibility | All paths observe, but persistence/plan arithmetic/commits precede observation; history can reconstruct execution optimization. | Fail |
| All non-tradable references consistently identified | Registry contains zero non-tradable/index-reference facts. | Fail |
| Ambiguity behavior defined and implemented | Proposed here; no admission contract exists. | Fail |
| Registry infrastructure failure behavior defined and implemented | Proposed here; current outcome is UNKNOWN plus boolean and boundary policy is non-blocking. | Fail |
| Transaction admission error contract | Proposed here, not implemented. | Fail |
| Optimizer and plan exclusion behavior | Proposed here, not implemented. | Fail |
| Compatibility telemetry observed and reviewed | Log emission exists; no durable review evidence or observation window. | Fail |
| Rollback switch/feature flag | Proposed here, not implemented. | Fail |
| Focused regression health | 128 relevant tests pass. | Pass, but insufficient |

M31.4 audit/design is complete. A cutover implementation milestone should not proceed to enforcement now. A preparation/remediation milestone may proceed with all behavior flags left in `LEGACY_FALLBACK`/shadow mode.

## 11. Preconditions for implementation

1. Approve a Registry-governed definition of the supported executable universe.
2. Reach 100% eligible resolution for all current holdings and optimizer-reachable watchlist symbols in every deployment environment.
3. Adjudicate `GOOGL01.BK`, `GULF.BK`, `ASML01.BK`, `PLANB.BK`, and `STECON.BK` before cutover.
4. Register all supported ETFs and remove the need for the 10-ticker compatibility allow-list.
5. Create authoritative DR assets/aliases and exactly one underlying relationship for every supported DR; review current Registry EQUITY records that the legacy/provider layer treats as DR.
6. Register supported indices/benchmarks as non-tradable references and prove reference behavior.
7. Decide whether native `asset_id` backfill is a cutover requirement; at minimum, produce a clean adjudication report for the 0%-materialized operational rows.
8. Add explicit `REGISTRY_FAILURE` to the eligibility contract.
9. Approve and document the optimizer exclusion, partial-plan, and transaction error contracts.
10. Move future guards to pre-persistence/pre-arithmetic/pre-commit locations while retaining batch resolution and pure scoring/admission predicates.
11. Add durable telemetry/metrics, complete the observation window, review every supported-instrument disagreement, and run a Registry-outage exercise.
12. Implement and drill the three-state feature flag with no data migration.
13. Update frontend types and error handling before server enforcement.
14. Coordinate the remaining broker-fee DR regex with M32 or approve it as an explicitly time-bounded fee-domain exception.

## 12. Suggested implementation sequence if approved

1. **Registry remediation only:** populate assets, aliases, ETF types, DR relationships, index/reference classifications, and run the preflight report until clean.
2. **Observability and contract preparation:** add explicit REGISTRY_FAILURE, counters/log retention, API schemas, and frontend parsing while behavior remains shadow-only.
3. **Feature flag foundation:** add the single cutover-mode enum defaulted to `LEGACY_FALLBACK`; prove rollback.
4. **Facts-only execution-risk shadow:** remove authoritative compatibility influence under `FACTS_ONLY_SHADOW`, retain comparison telemetry, and verify resolved-output parity.
5. **Optimizer pre-persistence guard:** filter executable projections while retaining belief/exclusion evidence; test history reconstruction.
6. **Execution-plan pre-arithmetic guard:** resolve once, filter, then recompute all funding/cash/status values from eligible actions only.
7. **Transaction pre-commit guard:** admit inside the service before fees/mutation and map typed errors at the API boundary.
8. **Enforcement canary:** enable `ENFORCE` in a non-production environment, then one low-risk environment/workspace if deployment scoping supports it; monitor and drill rollback.
9. **General enforcement:** promote only after thresholds remain clean across the observation window.
10. **Compatibility retirement:** keep one rollback release, then delete `execution_penalty_compat.py`; coordinate fee-taxonomy cleanup with M32.

## Verification record

Read-only/static work performed:

- Exhaustive `rg` traces for compatibility imports/calls, `asset_type`, `legacy_asset_type`, `is_dr`, execution facts/status/role/form, symbol classifiers, fee profile resolution, transaction service callers, plan builders, and frontend fields.
- Live development Registry/portfolio/watchlist/history/transaction coverage queries in rolled-back sessions and savepoints. `RegistryFinding` was 0 before and after resolver measurement.
- Focused tests:

  `python -m pytest tests/test_execution_instrument_facts.py tests/test_execution_penalty_m31_2.py tests/test_execution_eligibility_m31_3.py tests/test_registry_lookup.py tests/test_registry_symbol_matching.py tests/test_registry_symbol_matching_integration.py tests/test_fee_accounting.py tests/test_transaction_symbol_normalization.py tests/test_write_path_asset_id.py -q`

  Result: **128 passed**, 486 warnings. Warnings are existing SQLAlchemy, datetime, pandas, event-loop, and pytest-cache warnings; there were no test failures.

No production code, compatibility code, database data, migration, frontend behavior, or API behavior was changed. No commit or push was performed.
