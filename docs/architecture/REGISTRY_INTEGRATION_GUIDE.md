# Registry Integration Guide

Companion documents: [ASSET_REGISTRY.md](ASSET_REGISTRY.md) (frozen architecture), [ASSET_REGISTRY_IMPLEMENTATION_PLAN.md](../implementation/ASSET_REGISTRY_IMPLEMENTATION_PLAN.md) (M0–M7 milestone plan), [M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md](../implementation/M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md) (the audit and refactoring order this module implements Phase 1 of).

**Status (2026-07-10): `services/registry_lookup.py` exists, is tested, and now has real callers.** `basket_simulation.py`, `execution_plan.py`, `position_sizing.py`, `allocation_engine.py`, `idea_review.py`, and `portfolio_construction.py` all resolve symbols through it now, via the shared `services/registry_symbol_matching.py` adapter described in §"Matching two spellings of one instrument" below. The Recommendation write path (`main.py`'s `POST /analyze/optimizer` → `RecommendationSnapshot.scores_map_json`) is also wired, via `services/registry_recommendation_context.py`, described in §"Recommendation write-path metadata" below. AI Evaluation's plan-vs-live-Transaction join is wired as of Phase 4 (2026-07-10) — see §"AI Evaluation read-path (Phase 4)" below. A fresh completion audit of the remaining Execution and Evaluation surface (Phase 5, also 2026-07-10) found nothing further that qualifies for migration — see §"Execution & Evaluation Completion Review (Phase 5)" below.

---

## When writing new code

**DO**

```python
from services import registry_lookup

result = registry_lookup.resolve_asset(db, symbol)
if isinstance(result, registry_lookup.AssetView):
    ...  # result.asset_id, .display_symbol, .classification, etc.
else:
    ...  # registry_lookup.Unresolved — fall back to today's symbol-string behavior
```

**DON'T**

```python
symbol.endswith(".BK")
```

**DON'T**

```python
if symbol == other_symbol:
    ...
```

**DON'T**

```python
db.query(PortfolioItem).filter_by(symbol=symbol)  # lookup by ticker directly, when identity is what you actually need
```

The pattern above (`.BK`-suffix checks, direct symbol equality, ticker-keyed lookups) is exactly what `resolve_asset()` replaces — see [M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md](../implementation/M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md) §2.3 for the three concrete correctness bugs this class of code has already produced elsewhere in this codebase.

---

## `resolve_asset(db, query)`

```python
def resolve_asset(db: Session, query: Union[str, AssetId, int]) -> Union[AssetView, Unresolved]
```

- `db` is always the first argument, matching every other Registry-facing function in this codebase (`registry_service.*`, `identity_resolver.*`). There is no ambient session anywhere in this platform; this module does not introduce one.
- `query` is either a platform symbol string (`"AOT.BK"`, `"NVDA01"`) or an `AssetId`/plain `int`. The function dispatches on the argument's type rather than exposing two separately-named functions — see the module's own docstring for the full rationale.
- The return value is always one of two types. **Check with `isinstance`, never with a try/except** — `resolve_asset()` does not raise for an ordinary not-found or ambiguous result (a `TypeError` is raised only if `query` is neither a `str` nor an `int`, which is a caller bug, not a lookup outcome).

### `AssetView` — what you get back on a resolved lookup

| Field | Type | Notes |
|---|---|---|
| `asset_id` | `AssetId` | Permanent, opaque. Never reused. |
| `canonical_symbol` | `str` | Assigned once at minting. **Never** render this to a user. |
| `display_symbol` | `str` | The current-facing symbol. Use this for display. |
| `market` | `str` | e.g. `"Thailand"` |
| `exchange` | `str` | e.g. `"SET"` |
| `currency` | `str` | e.g. `"THB"` |
| `asset_type` | `AssetType` | Structural enum (`EQUITY`, `ETF`, ...) |
| `classification` | `Mapping[str, str]` | Current classification facts, keyed by dimension (`"SECTOR"`, `"REGION"`, ...). Empty dict if none recorded yet. |

`AssetView` is a frozen dataclass of plain values — never `models.asset.Asset` itself. It carries no session or identity-map lifetime coupling; holding one after the `db` session that produced it has closed is safe.

### `Unresolved` — what you get back otherwise

```python
@dataclass(frozen=True)
class Unresolved:
    query: str
    reason: str
```

`reason` is a short human-readable string (`"no matching asset"`, `"ambiguous — ..."`, `"conflicting evidence — ..."`). It is for logs/debugging, not for branching logic — every `Unresolved` should be handled identically by callers: **fall back to today's symbol-string behavior.** That fallback is what makes wiring this module into a consumer risk-free even while the Registry's own coverage is partial (as of the 2026-07-09 M5.3 bootstrap run: 41/52 ledger transactions resolved, 11 not).

An `AMBIGUOUS` or `CONFLICT` verdict additionally records an `OPEN` `RegistryFinding` — this is `identity_resolver.resolve()`'s existing, unmodified behavior (M3), not something this module adds. It means a genuinely ambiguous symbol surfaces for human adjudication rather than being silently guessed, per [ASSET_REGISTRY.md](ASSET_REGISTRY.md) §4 ("resolve decisively or ask — never guess").

### `resolve_many(db, queries)`

Resolves several queries in one call, returning a dict keyed by the original query values, reusing the shared cache so a symbol repeated within or across calls is never re-resolved twice.

---

## Caching

Every result — positive and negative — is cached in-process, thread-safe, with a configurable TTL (default 300s) and max size (default 2048, LRU-evicted). A cache hit performs no database work and does not call `identity_resolver.resolve()` again.

```python
registry_lookup.configure_cache(ttl_seconds=60, max_size=4096)
registry_lookup.invalidate_cache()            # clear everything
registry_lookup.invalidate_cache("AOT.BK")    # clear one symbol
```

Mirrors the existing 30-minute TTL cache pattern already used by `services/analytics/regime_detector.py` in this codebase (same `invalidate_cache()` naming convention).

---

## Matching two spellings of one instrument

Don't call `resolve_asset()` directly to answer "is this bare ticker the same instrument as that `.BK`-suffixed one?" — that question comes up constantly (a portfolio holding stored as `"BH.BK"`, a user-submitted idea spelled `"BH"`, an `AnalysisCache` row that might be under either spelling) and answering it correctly needs more than one `resolve_asset()` call plus a fallback for symbols the Registry hasn't resolved yet. Use the shared adapter instead:

```python
from services.registry_symbol_matching import match_known_symbols

# symbols: the spellings you're querying with (e.g. user-submitted ideas)
# known:   the spellings already on file (e.g. portfolio holding symbols)
matches = match_known_symbols(db, symbols=["BH"], known=["BH.BK"])
# -> {"BH": "BH.BK"}
```

It tries `resolve_asset()` on both sides first — a genuine Registry match (same `asset_id`) always wins, and a genuine Registry **conflict** (both sides resolve, to *different* asset_ids) is never overridden by string-guessing, since that would silently paper over exactly the kind of "these are different instruments" verdict ASSET_REGISTRY.md §5 exists to protect (a DR and its underlying, for instance). Only for symbols the Registry has not resolved does it fall back to the legacy bare/`.BK` suffix heuristic — this is what keeps every currently-working `.BK`-variant match unchanged for the (currently large) population of symbols the Registry hasn't adjudicated yet.

`basket_simulation.py`, `execution_plan.py`, `position_sizing.py`, `allocation_engine.py`, `idea_review.py`, and `portfolio_construction.py` all call this instead of hand-rolling their own suffix matching — see `docs/implementation/M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md` §2.3 item 3 for the correctness risk this replaced (five independent, silently-diverging implementations of the same question).

---

## Recommendation write-path metadata

The Recommendation record (`RecommendationSnapshot`, one row per optimizer run) is the highest-leverage single place to attach Registry identity, because every downstream evaluation consumer reads it. `services/registry_recommendation_context.py` resolves every symbol in a run's `scores_map` and returns an *additive-only* enriched copy, never mutating the input:

```python
from services.registry_recommendation_context import enrich_scores_map_for_snapshot

# scores_map: {symbol: {...existing fields...}}, unchanged by this call
enriched = enrich_scores_map_for_snapshot(db, scores_map)
# enriched[symbol] == {**scores_map[symbol], "registry": {...}}
# enriched[symbol]["registry"] is either
#   {"resolved": True, "asset_id": ..., "canonical_symbol": ..., "market": ..., "exchange": ...}
# or
#   {"resolved": False, "reason": "..."}
```

`main.py`'s `POST /analyze/optimizer` calls this exactly once, immediately before `services.decision_memory.snapshot_writer.write_recommendation_snapshot()`, and only for the copy that gets persisted into `RecommendationSnapshot.scores_map_json` — the live `scores_map` that feeds the AI prompt, `portfolio_data`/`watchlist_data`, timing enrichment, and `execution_penalty` is never touched, so this integration cannot change AI behavior or any existing API response (OPTIMIZER_PHILOSOPHY.md §6's judgment/arithmetic boundary: identity resolution never reaches the AI's input). `SignalHistory` (the other per-run record written alongside `RecommendationSnapshot`) has no free-form JSON column and so cannot carry this metadata without a schema change — out of scope until one is authorized; see `docs/implementation/M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md`'s Phase 3 Migration Report and Technical Debt Register.

---

## AI Evaluation read-path (Phase 4)

The M6 Compatibility-Layer Phase 4 brief named `plan_grader.py`, `optimizer_action_summary.py`, `execution_analyzer.py`, `execution_report.py`, and "AI evaluation helpers" as candidates. Auditing every file in `backend/services/evaluation/` (full read, not a grep pass) found only one genuine identity-matching risk among them, plus one pre-existing hidden consumer the M6 read-path report's own audit had missed:

**Fixed:** `services/evaluation/execution_ledger.py::_linked_transactions(db, decision_id, known_symbols=None)` — this is the plan-vs-live-`Transaction.symbol` join [M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md](../implementation/M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md) §2.3 item 1 already named as the highest correctness risk in the evaluation domain. `services/evaluation/execution_analyzer.py::compute_execution_analysis` is a deliberately pure function (no DB access, its own docstring says so) and was **not** touched — the fix lives entirely in the caller that assembles its `linked_transactions` argument. When `known_symbols` (the decision's own plan symbols) is passed, each transaction symbol that doesn't already match one exactly is resolved via `registry_symbol_matching.match_known_symbols()`; a Registry (or legacy `.BK`) match rewrites the transaction's symbol to the plan's spelling before it reaches `compute_execution_analysis`. Symbols the Registry can't decide are left untouched — identical behavior to before this change.

Three call sites now pass `known_symbols`: `execution_ledger.py`'s own `_decision_analysis`/`list_execution_ledger`; `recommendation_ledger.py::get_report_card`, which previously duplicated the `linked_transactions`/`recommendation_prices` construction inline instead of reusing `execution_ledger.py`'s helpers (a Reuse-Before-Create gap, now fixed alongside the Registry wiring — both call sites use the same `_linked_transactions`/`_recommendation_prices`); and `services/analytics/attribution_engine.py::_timing_and_fee_effects`, a previously-undocumented fourth consumer of the same helpers discovered during this audit — the M6 read-path report's own classification of `attribution_engine.py` as "confirmed symbol-agnostic" was incomplete (true for the attribution/BHB math, not true for this one timing/fee-effect function).

**Audited, no change needed:**
- `plan_grader.py`'s `_derive_action_summary_and_buys` only indexes a dict built from `target_allocations` by symbols drawn from that same list — no cross-source join, nothing a wrong symbol could corrupt.
- `optimizer_action_summary.py::build_action_summary` is documented and enforced as pure ("No AI calls, no DB access, no side effects"); Registry calls require a `db` session and do not belong inside it.
- `services/evaluation/ideal_series.py` keys live yfinance price fetches by symbol from a single frozen allocation list — an external-API boundary (like `timing_intelligence.py`), not a cross-source identity join.
- `services/evaluation/opportunity_cost.py` never joins by symbol (decision-level aggregate only).

**Intentionally deferred:** `services/evaluation/horizon_grader.py::score_directional_calls` joins `inception_holdings` against a shadow's later `horizon_holdings_json` by symbol — a real cross-source join, but both sides are the *same shadow's own* frozen, machine-written output, not independently-sourced spellings the way the plan-vs-live-Transaction join is. Lower risk, and it's a documented pure function. Deferred; revisit only if a real divergence is observed in production.

**Naming mismatch found:** `execution_report.py`, named in the Phase 4 brief, does not exist anywhere in this codebase. The only match is `_print_execution_report()` in `manage.py`, which is CLI output for the M5 ledger-migration executor — unrelated to AI Evaluation.

---

## Execution & Evaluation Completion Review (Phase 5)

The Phase 5 brief asked for a fresh audit of `backend/services/evaluation/` and `backend/services/execution/` — explicitly warning not to assume the Phase 4 scoping still holds — and to implement only what genuinely needs it. **`backend/services/execution/` does not exist**, the same kind of naming mismatch as the `execution_report.py` finding above; the "Execution" domain's real files are `services/execution_plan.py`, `services/funding_source_analysis.py`, `services/optimizer/execution_optimizer.py`, `services/optimizer/execution_penalty.py`, and `services/optimizer/stabilization.py` (the same set [M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md](../implementation/M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md) §1.3 groups as "Execution sizing/planning").

Every remaining candidate was read in full and classified. **Result: zero migrations.** Nothing left in either domain satisfies all four required conditions (genuine cross-source identity join; Registry materially improves correctness; no schema change; no business-logic redesign) at the same time:

- **Already Registry-aware, no further work:** `execution_ledger.py`, `recommendation_ledger.py`, `attribution_engine.py::_timing_and_fee_effects` (Phase 4); `basket_simulation.py`, `execution_plan.py`, `position_sizing.py`, `allocation_engine.py`, `idea_review.py`, `portfolio_construction.py` (Phase 2).
- **No identity join to fix:** `plan_grader.py`, `optimizer_action_summary.py`, `ideal_series.py`, `opportunity_cost.py` (re-confirmed from Phase 4); `evaluation/scorecard.py`, `trust_report.py`, `verdict_composer.py`, `expired_writer.py` (re-grepped this session, zero `symbol` occurrences); `funding_source_analysis.py::build_funding_sources` (pure function, single-source dicts built by one caller — no second symbol source to join against); `override_classifier.py::build_override_record` (normalizes symbol strings for storage, never compares against a second source — also outside this brief's literal directory scope).
- **Pure functions, deliberately Registry-free:** `execution_analyzer.py::compute_execution_analysis` (unchanged since Phase 4 — its join is already fixed at the caller boundary); `funding_source_analysis.py` (see above).
- **Genuine joins, deliberately deferred (unchanged conclusion):** `horizon_grader.py::score_directional_calls` — same-shadow frozen-vs-frozen data, lower risk than the plan-vs-live-Transaction join; revisit only on an observed divergence.
- **Technical debt, blocked on business-logic redesign (out of this phase's scope by the brief's own rules):**
  - `execution_optimizer.py::classify_reason` — recovers a structured fact via `symbol in v` substring search against free-text violation strings `policy_engine.py` builds. A real fix means giving `policy_engine.py` a structured `subject_asset_id` field instead of prose — that's [M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md](../implementation/M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md)'s own §5 Phase 5 "structural fix," not a caller-boundary read-path change. Also a documented pure function (no DB access).
  - `execution_penalty.py::classify_execution` — infers `asset_type` from ticker shape (regex + hardcoded ETF list) only when the caller hasn't already supplied `is_dr=True`. `AssetView.asset_type` could answer this in principle, but the only call site (`main.py`'s `POST /analyze/optimizer`, synchronous prompt-building block) has no `db` session threaded to it — wiring Registry resolution in means changing this `agents/optimizer.py`-adjacent function's call signature and control flow, not a boundary-only fix.
  - `stabilization.py::diagnose_duplicate_tickers` — diagnostic-only, scans one pipeline run's own L1/L2/L3 output dicts for same-symbol duplicates; not a join against an independently-sourced second symbol list. Becomes structurally unnecessary once `agents/optimizer.py`'s internal dict-keys migrate to `asset_id` (a separate, later phase, out of `evaluation/`+`execution*` scope entirely).

**Execution & Evaluation integration is complete as of Phase 5.** The two legitimate remaining tracks in [M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md](../implementation/M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md) §5 are Phase 1 step 2 (pilot `resolve_asset()` on `GET /watchlist`, already-scoped, not started) and Phase 7 (classification consolidation — `THAI_SECTOR_MAP`/`_get_sector` becoming Registry-backed). Both are outside this brief's Execution/Evaluation scope and are named here as candidates, not started.

## Where NOT to call this from

Never from `services/portfolio_rebuilder.py`'s replay loop or `services/ledger_validator.py`'s CHECK functions. Those are the accounting-critical, deterministic-replay paths the M5 Track B milestone owns — introducing a Registry lookup there before Track B's replay-parity gate exists would be exactly the "silent behavior change during coexistence" Migration Principle 3 forbids. This module is for analytics, optimizer internals, evaluation, and CRUD/display paths only.

---

## Current status

`services/registry_lookup.py` and its 18-test suite (`backend/tests/test_registry_lookup.py`) shipped 2026-07-09 as Phase 1, step 1 of the M6 Compatibility-Layer Integration track. `services/registry_symbol_matching.py` and its two test suites (`backend/tests/test_registry_symbol_matching.py`, `backend/tests/test_registry_symbol_matching_integration.py`) shipped the same day as Phase 2, retiring the five duplicated `.BK`-variant shims. `services/registry_recommendation_context.py` and its test suite (`backend/tests/test_registry_recommendation_context.py`) shipped the same day as Phase 3 step 7, wiring the Recommendation write path (see [ASSET_REGISTRY_IMPLEMENTATION_PLAN.md](../implementation/ASSET_REGISTRY_IMPLEMENTATION_PLAN.md) §13 Changelog for all three). `resolve_asset()` now has real callers across symbol matching and recommendation persistence.

**Phase 4 (2026-07-10)** wired the plan-vs-live-Transaction join in AI Evaluation's read path — `execution_ledger.py`, `recommendation_ledger.py`, and `attribution_engine.py` — through `match_known_symbols()`, per §"AI Evaluation read-path (Phase 4)" above. `plan_grader.py`/`optimizer_action_summary.py` were audited and found not to need wiring; `horizon_grader.py`'s lower-risk shadow-vs-shadow join was deliberately deferred; `execution_report.py` does not exist in this codebase.

**Phase 5 (2026-07-10)** re-audited everything left in `services/evaluation/` and the "Execution" domain (`services/execution_plan.py`, `services/funding_source_analysis.py`, `services/optimizer/execution_optimizer.py`, `services/optimizer/execution_penalty.py`, `services/optimizer/stabilization.py` — `services/execution/` itself does not exist) and found no remaining module that is both a genuine cross-source identity join and fixable without a schema change or a business-logic redesign. See §"Execution & Evaluation Completion Review (Phase 5)" above for the full classification. **Execution & Evaluation integration is declared complete.**

Still open: Phase 1 step 2 (piloting `resolve_asset()` directly on `GET /watchlist`), and Phases 5–7 of [M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md](../implementation/M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md) §5's own numbering (the policy/execution structural fix, shadow portfolios/factor engine/calibration, and classification consolidation) — this guide's "Phase 5" heading above refers to the completion-review brief that requested it, not §5's own phase numbering, same numbering caveat as Phase 4's. Phase 4 of §5 (optimizer internals + consensus scoring, §5 steps 9-10) also remains open — out of scope for both this guide's Phase 4 and Phase 5 sections, which cover read-path business logic and its completion audit, not optimizer internals.
