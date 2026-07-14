# M31.6 — Registry Remediation Wave 1

**Date:** 2026-07-14

**Result:** Wave 1 evidence review complete; **0 applied, 5 deferred**

**Cutover status:** `LEGACY_FALLBACK`; `FACTS_ONLY_SHADOW` and `ENFORCE`
remain inert. Blocking cutover remains **NO-GO**.

## 1. Scope and decision

Wave 1 investigated only `GOOGL01.BK`, `GULF.BK`, `ASML01.BK`,
`PLANB.BK`, and `STECON.BK`. It did not inspect the wider unresolved
watchlist for remediation and did not register any ETF, DR relationship, or
benchmark reference.

The governing decision is to quarantine all five pending human adjudication.
The configured development Registry contains no exact Asset candidate,
current or historical identifier, bootstrap checkpoint, migration checkpoint,
or Registry finding for any of them. Operational use proves that a spelling
exists in current workflows; it does not prove the instrument's Registry
identity, structural `AssetType`, market, or exchange. Minting any of the five
would therefore require a guess or fallback-to-EQUITY, both prohibited by the
milestone.

The reviewed manifest is
`docs/implementation/M31_6_registry_remediation_wave1_manifest.json`. It has
five evidence reviews and an empty `instructions` list. The before/after
preflight summary is
`docs/implementation/M31_6_registry_remediation_wave1_preflight.json`.

## 2. Evidence method

The investigation used only repository and configured development database
evidence:

- exact `Asset.canonical_symbol` and `Asset.display_symbol` values;
- exact current and historical `AssetIdentifier.value` records;
- Registry relationships, classifications, and findings;
- Registry bootstrap and migration execution checkpoints;
- current holdings and watchlist rows;
- executable transaction ledger rows;
- latest persisted actionable optimizer allocations;
- exact repository references and explicit provider-map membership.

Candidate matching is exact and case-normalized. It does not strip or append
`.BK`, remove numeric suffixes, inspect a caret prefix, call a provider, use a
DR regex, consult the ETF compatibility list, or use sector membership as an
identity/type verdict. `symbol_normalization.py` and `symbol_resolver.py` can
derive provider tickers from spelling, but those legacy/provider heuristics
were explicitly rejected as Registry authority.

The evidence collector has a hard-coded five-symbol milestone scope. Passing
an additional symbol is rejected. This is a remediation worklist boundary,
not an execution taxonomy or supported-universe list.

## 3. Symbol-by-symbol findings

| Requested symbol | Existing Registry candidates / identifiers | Stored operational evidence | Existing `asset_type` | Proposed operation | Confidence | Decision and unresolved risk |
|---|---|---|---|---|---|---|
| `GOOGL01.BK` | 0 candidates; 0 identifiers; 0 relationships/classifications/findings/checkpoints | Holding 107, watchlist 34; BUY transactions 47/48/57/59 and SELL 73, all stored as `GOOGL01.BK`, currency THB where populated | None | Mint or attach only after authoritative adjudication | Insufficient | Deferred. Ledger usage and THB currency do not establish whether this is an EQUITY, ETF, DR, or OTHER listing, nor its market/exchange. Numeric-suffix provider normalization is heuristic and cannot supply identity or a DR relationship. |
| `GULF.BK` | 0 candidates; 0 identifiers; 0 relationships/classifications/findings/checkpoints | Holding 105, watchlist 7; INITIAL_POSITION 24 and BUY 69, stored as `GULF.BK`, currency THB; repair-plan prose identifies transaction 24 as the authoritative ledger record | None | Mint or attach only after authoritative adjudication | Insufficient | Deferred. The ledger and repair record establish historical position spelling and amount evidence, not Registry `AssetType`, market, or exchange. `sector_taxonomy.py` labels Utilities but sector is not identity/type authority. |
| `ASML01.BK` | 0 candidates; 0 identifiers; 0 relationships/classifications/findings/checkpoints | Watchlist 46; latest actionable optimizer history 118 (`ACCUMULATE`); repeated analysis/cache use | None | Mint or attach only after authoritative adjudication | Insufficient | Deferred. No transaction/holding identity evidence and no explicit repository provider mapping exists. A symbol-shape inference would be prohibited. |
| `PLANB.BK` | 0 candidates; 0 identifiers; 0 relationships/classifications/findings/checkpoints | Watchlist 78; latest actionable optimizer history 118 (`ACCUMULATE`); repeated analysis/cache use | None | Mint or attach only after authoritative adjudication | Insufficient | Deferred. `sector_taxonomy.py` labels Consumer but that cannot establish an Asset identity, structural type, market, or exchange. |
| `STECON.BK` | 0 candidates; 0 identifiers; 0 relationships/classifications/findings/checkpoints | Watchlist 80; latest actionable optimizer history 118 (`ACCUMULATE`); repeated analysis/cache use | None | Mint or attach only after authoritative adjudication | Insufficient | Deferred. `sector_taxonomy.py` labels Industrial but that cannot establish an Asset identity, structural type, market, or exchange. |

The exact historical spelling found for each symbol is the requested spelling
itself. No governed alternative spelling or symbol migration was found. None
of the five requested symbols or their unsuffixed base is an explicit key in
`YFINANCE_SYMBOL_MAP`; even if one were present, provider routing alone would
still not establish Registry asset form or tradability.

## 4. Manifest generation and remediation safety

`services/execution_registry_wave1.py` builds a deterministic dossier with no
timestamp and stable symbol/evidence ordering. Outcomes are:

- `ALREADY_RESOLVED` when the exact symbol is already the current Registry
  provider identifier;
- `ATTACH_IDENTIFIER_REVIEW_REQUIRED` only when exact stored
  canonical/display/identifier history yields exactly one candidate; the
  generated instruction remains `approved: false`;
- `QUARANTINE_PENDING_HUMAN_ADJUDICATION` for zero or multiple exact
  candidates.

The generator never creates a mint instruction from operational presence.
Minting remains an explicit reviewed-manifest operation requiring complete
canonical/display identity, `AssetType`, market, exchange, currency,
tradability, and identifier evidence. An attach instruction now carries the
candidate asset IDs and validation requires exactly `(asset_id,)`.

`services/execution_registry_remediation.py` now classifies repeat application
as `ALREADY_APPLIED` only when the complete current Registry state matches the
instruction. A canonical-symbol collision with different metadata, a missing
requested current identifier, or a missing required relationship/
classification raises instead of being treated as success. Existing Registry
identifier, relationship, and classification idempotency remains reused.

The CLI `scripts/execution_registry_wave1.py` generates the read-only dossier.
The existing `scripts/execution_registry_preflight.py` remains the only
dry-run/commit runner.

## 5. Dry-run and commit result

The generated manifest contained zero approved or unapproved write
instructions. Both the required dry-run and explicit commit invocation
completed with zero steps. The commit invocation was intentionally retained
as evidence that the reviewed artifact cannot mutate Registry state.

| Registry table | Before | After | Changed |
|---|---:|---:|---:|
| Assets | 21 | 21 | 0 |
| Identifiers | 21 | 21 | 0 |
| Relationships | 0 | 0 | 0 |
| Classifications | 0 | 0 | 0 |
| Findings | 0 | 0 | 0 |

No `RegistryFinding` was created by candidate collection, dry-run, commit, or
post-run preflight.

## 6. Coverage before and after

Because no evidenced write was possible, coverage correctly did not improve.
This is a safe Wave 1 outcome, not an invitation to relax evidence standards.

| Population | Before | After | Delta |
|---|---:|---:|---:|
| Current holdings | 19/21 (90.5%) | 19/21 (90.5%) | 0 |
| Workspace watchlist | 18/87 (20.7%) | 18/87 (20.7%) | 0 |
| Optimizer reachable, portfolio 2 | 18/87 (20.7%) | 18/87 (20.7%) | 0 |
| Optimizer reachable, portfolio 3 | 19/88 (21.6%) | 19/88 (21.6%) | 0 |
| Optimizer reachable, portfolio 4 | 18/87 (20.7%) | 18/87 (20.7%) | 0 |
| Latest actionable allocations | 9/12 distinct (75.0%) | 9/12 (75.0%) | 0 |
| Historical executable transactions | 21/25 distinct (84.0%) | 21/25 (84.0%) | 0 |

The two unresolved holdings and three unresolved latest actions remain the
same five Wave 1 symbols.

## 7. Native `asset_id` readiness

No native row was updated. No additional operational row became exactly
resolvable because the Registry received no identity evidence.

| Table | Before proposals | After proposals | Delta | Remaining unresolved |
|---|---:|---:|---:|---:|
| `portfolio_items` | 19 | 19 | 0 | 2 |
| `watchlist` | 18 | 18 | 0 | 69 |
| executable `transactions` | 41 | 41 | 0 | 11 rows |

The 78 existing dry-run proposals remain reporting-only. No backfill was
performed.

## 8. Behavior invariants

- No optimizer score, allocation, history, or action was changed.
- No execution-plan filtering or funding arithmetic changed.
- No transaction admission, holding, cash, fee, tax, or ledger behavior
  changed.
- No frontend/API/schema/migration file changed.
- No ETF, DR relationship, or reference instrument was registered.
- `execution_penalty_compat.py` remains available and authoritative for the
  named unresolved compatibility path.
- Setting the typed mode to `ENFORCE` in focused tests still permits an
  unregistered initial position and plan action; no new runtime imports the
  Wave 1 tooling.

## 9. Verification

Focused M31.6 tests cover deterministic output, fixed scope, exact-only
candidate matching, attach candidate cardinality, complete mint evidence,
ambiguous quarantine, dry-run rollback, approved-only commit, repeat
idempotency, conflicting repeat refusal, finding control, inert cutover mode,
and runtime-boundary isolation.

Verification results:

- focused M31.6: **12 passed**;
- combined M31.1–M31.6: **70 passed**;
- Registry/bootstrap regressions: **207 passed**;
- portfolio transaction/accounting/write-boundary regressions: **103 passed**;
- broad optimizer/execution/timing regressions: **254 passed**, with nine
  pre-existing stale-test failures listed below;
- `git diff --check`: passed.

The four pre-existing `test_optimizer_pipeline.py` failures still call
`_consensus_engine(l2, l3)` without its required leading argument:

- `test_consensus_rebalance_high_confidence`;
- `test_consensus_no_action_low_score`;
- `test_consensus_l1_parse_failure_propagation`;
- `test_consensus_critical_flag_forces_rebalance`.

Five additional pre-existing `test_human_vs_ai_timing.py` fixtures construct
`OverrideAttribution` without its now-required `override_type` field:

- `test_win_rate_is_good_overrides_over_total`;
- `test_total_added_return_is_sum_of_deltas`;
- `test_total_saved_drawdown_is_sum_of_saved_drawdowns`;
- `test_mixed_outcomes_count_correctly`;
- `test_summary_fields_are_correct_for_realistic_scenario`.

None of the failed files or their production dependencies was modified by
M31.6.

## 10. Required human adjudication and remaining blockers

For each symbol, a Registry steward must supply a reviewed instrument-master
record (or another already approved repository mapping) that explicitly
answers:

1. Is this a new listing or an alias of an existing `asset_id`?
2. What are the permanent canonical symbol and current provider identifier?
3. What are the structural `AssetType`, market, exchange, and currency?
4. Is the listing tradable, and what lot/settlement metadata applies?
5. If it is a DR, what existing authoritative underlying `asset_id` is linked
   by exactly one `DEPOSITARY_RECEIPT_OF` relationship?

Until those answers exist, all five remain legitimate Registry coverage gaps.
`FACTS_ONLY_SHADOW` remains blocked by these five plus the broader unresolved
supported universe, ETF/DR/reference governance, alias policy, and an observed
telemetry window. `ENFORCE` additionally remains blocked by every M31.4
pre-admission, API contract, outage-policy, frontend, canary, and rollback
precondition.
