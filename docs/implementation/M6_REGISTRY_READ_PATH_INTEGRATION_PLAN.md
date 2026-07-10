# M6 — Registry-backed Read Path: Migration Report

_Engineering implementation plan for replacing symbol-based identity reads with Asset-Registry-backed lookups across the platform. This is a plan, not code — no source file in this repository was modified to produce it._

_Companion documents: [ASSET_REGISTRY.md](../architecture/ASSET_REGISTRY.md) (frozen architecture), [ASSET_REGISTRY_IMPLEMENTATION_PLAN.md](ASSET_REGISTRY_IMPLEMENTATION_PLAN.md) (the M0–M7 migration plan this report is a child of), [OPTIMIZER_PHILOSOPHY.md](../investment/OPTIMIZER_PHILOSOPHY.md) (Design Invariant 1 — recorded recommendations are immutable), [PORTFOLIO_CALCULATION_RULES.md](../investment/PORTFOLIO_CALCULATION_RULES.md) (Design Principle 1 — the Transaction table is the single source of truth)._

---

## 0. Scope Note — read this before anything else below

The requesting brief calls this "Milestone M6." **It is important to be precise about what that means before proceeding**, because the frozen [ASSET_REGISTRY_IMPLEMENTATION_PLAN.md](ASSET_REGISTRY_IMPLEMENTATION_PLAN.md) already defines an M0–M7 sequence, and its own M6 ("Analytics & Intelligence Integration") is explicitly gated:

> **M5 — Portfolio Migration** ("the ledger gets its identity"). Depends on: M3, M4. **Hard gate for: M6.**
> Definition of Done: *100% ledger coverage; replay parity bit-identical for every portfolio against golden baselines; `verify_snapshots` and `validate_ledger` clean on the id-keyed path; accounting engines running id-keyed in production for a probation period.*

**M5, as defined, has not been done.** What has shipped so far (M5.0 Ledger Evidence Builder, M5.1 Migration Planner, M5.2 Migration Executor, M5.3 Registry Bootstrap) built the *tooling* that can resolve a symbol to an `asset_id` and populate the Registry — it deliberately, and by design, never touched `Transaction`, `PortfolioItem`, `PortfolioSnapshot`, or `Watchlist`. Confirmed directly against the schema in this session:

```
PortfolioItem      — symbol: String, NOT NULL  (no asset_id column)
Watchlist          — symbol: String, NOT NULL  (no asset_id column)
Transaction        — symbol: String, nullable  (no asset_id column)
PortfolioSnapshot  — holdings_json / sector_breakdown_json Text blobs (symbol-keyed, no asset_id anywhere)
```

And the bootstrap validation numbers supplied with this task confirm the Registry's own coverage is partial, not total: **21/25 claim shapes resolved, 41/52 transactions resolved, 2 duplicate clusters unresolved.** 11 transactions (21%) currently have no path to an `asset_id` at all.

This matters because it changes what "Registry-backed read path" can honestly mean *right now*:

- A **schema-changing, accounting-critical cutover** (adding `asset_id` to the ledger tables, replaying, gating on bit-identical parity, flipping engines over) is exactly M5's job, is **not done**, and this brief's own constraint — *"Do NOT modify database schema unless absolutely necessary"* — is inconsistent with attempting it now.
- A **read-time compatibility layer** that resolves `symbol → Asset` on demand (reusing the already-built `identity_resolver`/`registry_service`, ADR-004) can start immediately, touches no ledger schema, breaks nothing, and gives every read path in this report a path to becoming Registry-informed for *descriptive* facts (canonical identity, `display_symbol`, classification) without waiting on M5.

**This report proceeds on that second track.** Section 4 specifies it. Every module in Sections 1–3 is classified by whether it can adopt the compatibility layer today or is genuinely blocked on the M5 ledger backfill — that classification is the single most important column in this report, because it is the difference between work that can start this sprint and work that would be re-done once M5 lands.

---

## 1. Registry Read Map

### 1.1 How to read this section

Four discovery passes were run against the backend (`services/`, `agents/`, `main.py`, `models/database.py`), covering: **Portfolio/Transactions/Snapshots/Watchlist**, **Optimizer/Execution**, **Analytics/Shadow Portfolio**, **Recommendations/AI Evaluation**. The Asset Registry's own files (`asset.py`, `asset_registry.py`, `registry_service.py`, `identity_resolver.py`, `migration_*.py`, `registry_bootstrap.py`, `symbol_resolver.py`, `symbol_normalization.py`) were excluded from the search — they are the producer side; this report is about the consumer side.

Every finding below is one of:

| Kind | Meaning |
|---|---|
| **IDK** | True identity/lookup key — a dict key, DB filter, join, or set-membership test that assumes the symbol string uniquely denotes one instrument |
| **DISP** | Display-only — a label rendered to a human or written into a response payload, not used to look anything up |
| **BM** | Benchmark/index symbol (`^GSPC`, `^SET.BK`, `QQQ`, `^VIX`) — never a portfolio holding, never an Asset Registry citizen |
| **FROZEN** | Identity baked into an already-persisted, append-only historical record (per OPTIMIZER_PHILOSOPHY.md Design Invariant 1 / ARCH_SPEC.md immutability) — must never be rewritten |

### 1.2 Canonical read-map shape

```
Ledger write path                    Ledger read path
(BUY/SELL/INITIAL_POSITION/          (holdings, transactions, snapshots)
 QUANTITY_CORRECTION)
        │                                     │
        ▼                                     ▼
  Transaction.symbol ───────────────►  PortfolioItem.symbol
  (String, no asset_id)                (String, no asset_id)
        │                                     │
        └──────────────┬──────────────────────┘
                        ▼
         [ NEW, proposed ] Registry Lookup Adapter (§4)
         resolve_asset(symbol) → AssetView | UNRESOLVED
                        │
        ┌───────────────┼────────────────────────────────┐
        ▼               ▼                                ▼
  Optimizer/Exec   Analytics/Shadow                AI Evaluation
  (agents/optimizer,  (factor_engine,              (evaluation/*,
   execution_*,        shadow_tracker,              decision_memory/*)
   position_sizing,    calibration)
   basket_simulation)
```

Symbols enter the platform at exactly the same two doors the Registry architecture already names (ASSET_REGISTRY.md §10): **the boundary** (ledger writes: `POST .../transactions/*`, `POST .../holdings`, `POST /watchlist`) and **the presentation surface** (API response `"symbol"` fields, frontend display). Everything in between — optimizer allocation maps, shadow valuations, evaluation grading — is today re-deriving identity from the same raw string at every hop, which is the condition ASSET_REGISTRY.md §10 calls "a symbol in business logic... smuggled below the waterline."

### 1.3 Read Map by domain (condensed — full file:line inventory is in the appendix tables §1.4–1.7)

| Domain | Owning service(s) | Ledger-critical? | Registry-adoptable today (no schema change)? |
|---|---|---|---|
| Portfolio holdings CRUD | `main.py` (add/delete/swap-permission), `services/portfolio_transactions.py` | Yes — `filter_by(symbol=...)` is the create/update/delete key | Partial — creation is the natural insertion point for `identity_resolver`; read/update stays symbol-keyed until M5 |
| Transaction ledger | `services/portfolio_transactions.py`, `main.py` `/transactions/*` | Yes — every execute_* function | Blocked on M5 for the ledger row itself; compatibility layer can annotate reads only |
| Replay / rebuild | `services/portfolio_rebuilder.py`, `services/ledger_validator.py` | Yes — **the most identity-critical code in the platform** | Blocked on M5 entirely — this is M5's actual job |
| Snapshots | `services/portfolio_snapshots.py`, `services/snapshot_repair.py`, `services/portfolio_metrics.py` | Yes — price-join keys, frozen `holdings_json` | Blocked on M5 for the join; `holdings_json` shape can gain an additive `asset_id` field going forward |
| Watchlist | `main.py` `/watchlist*` | No accounting impact, but same CRUD pattern | Yes — lowest-risk pilot for the compatibility layer (§5 Phase 1) |
| Optimizer (3-layer) | `agents/optimizer.py`, `services/optimizer/*` | Indirect — allocation math, not the ledger itself | Partial — internal dict-keys can switch to `asset_id` without a schema change, since these are in-memory structures rebuilt every run; the AI prompt/response contract stays symbol-shaped (§3.2) |
| Execution sizing/planning | `services/execution_plan.py`, `position_sizing.py`, `portfolio_construction.py`, `basket_simulation.py`, `funding_source_analysis.py`, `allocation_engine.py` | Indirect | Yes, high value — the `.BK`-variant matching shim duplicated across 4 files is exactly what the compatibility layer replaces (§4.3) |
| Regime detection | `services/analytics/regime_detector.py` | No | N/A — 100% benchmark symbols, out of Registry scope entirely |
| Factor exposure | `services/analytics/factor_engine.py` | No (analytics, not accounting) | Yes — `market_values[item.symbol]` dict-keying is a live recompute every call, safe to switch |
| Shadow portfolios | `services/decision_memory/shadow_tracker.py` | No (paper trading, not real ledger) but **large migration surface** | Yes for new shadows going forward; old `inception_holdings_json` rows are FROZEN |
| Calibration/Attribution | `services/decision_memory/calibration.py`, `attribution.py`; `services/analytics/attribution_engine.py`, `human_vs_ai.py`, `regime_attribution.py` | No | Mostly N/A — attribution math is symbol-agnostic by construction (reads only aggregate NAV/return columns); `calibration.py` has one real symbol join |
| Recommendation/Decision record | `models/database.py` (`RecommendationSnapshot`, `SignalHistory`, `UserExecutionDecision`), `services/decision_memory/snapshot_writer.py` | No (not the ledger) but **FROZEN once written** — Design Invariant 1 | Additive only, new rows going forward; existing rows must never be touched |
| AI Evaluation | `services/evaluation/*` (`horizon_grader.py`, `plan_grader.py`, `execution_analyzer.py`, `ideal_series.py`, `opportunity_cost.py`, `recommendation_ledger.py`, `execution_ledger.py`), `services/optimizer_action_summary.py` | No, but reads FROZEN grades | `execution_analyzer.py`'s frozen-plan-vs-live-`Transaction.symbol` join is the highest correctness risk in this whole domain (§2.3) |
| Human idea intake | `services/idea_review.py` | No (stateless, read-only) | Yes, immediately — no persistence, no immutability constraint, already has a hand-rolled `.BK` matcher that duplicates registry logic |
| Ops Center dashboard | `services/operations_center.py`, `services/translations/muji_translator.py`, `services/run_progress.py` | N/A | N/A — confirmed zero symbol usage in all three files |

### 1.4 Appendix — Portfolio / Transactions / Snapshots / Watchlist (file:line)

| File:Line | What it does | Kind | Ledger-critical |
|---|---|---|---|
| `models/database.py:80-96` | `PortfolioItem.symbol`, `UniqueConstraint(portfolio_id, symbol)` | IDK | Yes |
| `models/database.py:98-109` | `Watchlist.symbol`, `UniqueConstraint(workspace_id, symbol)` | IDK | No |
| `models/database.py:199-232` | `Transaction.symbol` (nullable — null for cash-only rows) | IDK | Yes |
| `models/database.py:235-266` | `PortfolioSnapshot.holdings_json` / `.sector_breakdown_json` — symbols only inside frozen JSON | IDK (in blob) | Yes |
| `services/portfolio_snapshots.py:208-225,269` | `price_map[item.symbol]` — join key between DB holdings and fetched price | IDK | Yes — silent NAV understatement if mismatched |
| `services/portfolio_snapshots.py:358-377` | Re-normalizes casing (`sym.strip().upper()`) to bridge two independently-keyed maps — documented workaround | IDK | Yes |
| `services/portfolio_rebuilder.py:126,136,144` | `_HoldingState.symbol`; `_PortfolioState.holdings: dict[symbol, HoldingState]` — the entire replay engine's core data structure | IDK | **Critical** |
| `services/portfolio_rebuilder.py:699-719` | Reconcile diff: `{item.symbol: item}` vs replayed `final_state.holdings` — literally the accounting-drift detector | IDK | **Critical** |
| `services/portfolio_rebuilder.py:1059-1077,1259-1264` | Repair-plan generation and final write-back of replayed state, both symbol-keyed | IDK (write) | **Critical** |
| `services/portfolio_transactions.py:109,209-254,443-525,591-672` | `filter_by(portfolio_id=..., symbol=symbol)` lookup-or-create/fail on every BUY/SELL/INITIAL_POSITION/QUANTITY_CORRECTION/DIVIDEND execute path | IDK | **Critical** |
| `services/transaction_canonicalizer.py:96,171` | `raw_sym = tx.symbol.strip().upper()` — the single normalization choke point everything downstream depends on | IDK | **Critical — natural resolver insertion point** |
| `services/ledger_validator.py:191-524,619-810,882,1013-1104` | Every CHECK_* function keyed by `raw_symbol`/`canonical_symbol`; CHECK 2 (`_check_symbol_aliases`, L249-301) exists **specifically** to detect the symbol-collision problem the Registry is meant to solve upstream | IDK | **Critical** |
| `services/portfolio_metrics.py:111-155` | `price_lookup.get(ctx.raw_symbol)` — feeds `investment_return_pct` math directly | IDK | **Critical — accounting** |
| `services/snapshot_repair.py:18-41,384-404` | Reconstructs historical snapshots **only** from `holdings_json` (no live DB fallback, by design) | IDK (frozen) | Yes — cannot be retroactively fixed without a JSON schema version bump |
| `services/broker_fees.py:125-134` | `resolve_fee_profile(symbol)` — regex-classifies DR vs `.BK` vs standard to pick a fee schedule | IDK (classification, not lookup) | Medium — $ impact via wrong fee schedule, but no DB join |
| `main.py:778-928` (`/holdings`, `/prices`, `/sector-breakdown`) | Cross-table joins to `AnalysisCache`/`AgentCache` by symbol string | IDK | Medium |
| `main.py:980-1061` (`add_holding`, swap-permission, delete) | `symbol` is a **URL path parameter** — identity carried in the route contract itself | IDK | High — migrating changes the API contract, not just internals |
| `main.py:1116-1197` (`/watchlist*`) | Same CRUD pattern as holdings, lower stakes | IDK | No (no accounting) |
| `main.py:3773-4046` (`/transactions/*`) | `_normalize_transaction_symbol(body.symbol)` on every write endpoint | IDK | **Critical** |
| `main.py:2982-3130` (`/admin/backfill-sectors`, `/admin/fix-dr-sectors`, `/admin/fix-sectors`) | Batch jobs re-running symbol→sector classification | IDK (classification) | Medium |
| `main.py:366-533` (`THAI_SECTOR_MAP`, `_DR_SECTOR_MAP`, `_get_sector`, `_fetch_sector`) | Static/branchy sector classification by symbol shape (`.endswith(".BK")`, DR prefix) | IDK (classification) | Medium — this is exactly the "Registry owns Classification" concern (ASSET_REGISTRY.md §8) |

### 1.5 Appendix — Optimizer / Execution (file:line)

| File:Line | What it does | Kind | Risk |
|---|---|---|---|
| `agents/optimizer.py:154-325,1436-1514,1751-1973` | `score_map`, `pc_map`, `alloc_map`, `_all_sector_data` — nearly every dict in this 2133-line file is `dict[symbol, ...]`; this is the widest single blast radius in the codebase | IDK | **Critical** |
| `agents/optimizer.py:188-253,855-1225` | Symbol is embedded in and parsed back out of the **AI prompt/response contract** (L1/L2/L3 JSON schemas) | IDK + AI I/O contract | High, orthogonal — needs prompt/schema work, not just a Python rename |
| `agents/optimizer.py:566-571` (`_consensus_engine`) | `l1_sells & l2_buy_syms` — symbol **sets** used for Jaccard-style overlap scoring, not just lookup | IDK, math semantics | High — any replacement key must preserve set semantics exactly |
| `services/optimizer/policy_engine.py:344-401` | Symbol interpolated into free-text violation strings (`f"CONCENTRATION_BREACH: {sym}..."`) | IDK embedded in prose | High — downstream code does substring search against this text |
| `services/optimizer/execution_optimizer.py:106-125` (`classify_reason`) | `symbol in v` — substring search inside policy_engine's free-text violations to recover identity | **Fragile double-hop stringly-typed coupling** | Very high — two layers deep, breaks silently under partial migration |
| `services/optimizer/execution_penalty.py:36-205` (`classify_execution`) | Infers `asset_type` (DR/ETF/INDEX/EQUITY) **from the ticker's textual shape** via regex + hardcoded list | Identity used as a classification signal | Very high — this should be **replaced by a real `Asset.asset_type`/`is_dr` field**, not migrated key-for-key |
| `services/optimizer/stabilization.py:429,574` (`diagnose_duplicate_tickers`) | Exists specifically to catch symbol-string collisions across pipeline stages | Symptom of unreliable identity | This function becomes structurally unnecessary once `asset_id` is the join key |
| `services/execution_plan.py:123-138`, `services/position_sizing.py:279-352`, `services/portfolio_construction.py` (via `basket_simulation._resolve_symbol_sectors`), `services/allocation_engine.py:339-420` | **The same `.BK`-suffix variant-matching hack, duplicated independently in 4 files** (`bk_variants = {f"{s}.BK"...}`) | Identity-resolution shim | Very high effort saved — this is the single clearest, highest-value target for the compatibility layer |
| `services/basket_simulation.py:282-311` (`_resolve_symbol_sectors`) | The canonical version of the above shim, shared by 3 other files | Identity-resolution shim | First thing to replace |
| `services/execution_plan.py:183-198` | `next((i.shares for i in portfolio_items if i.symbol == src.symbol), 0.0)` — O(n) linear scan, silently wrong under any symbol collision | IDK | High — correctness-critical for funding math |
| `services/timing_intelligence.py:297-335`, `services/optimizer_timing.py` | Live external market-data fetch, necessarily stays symbol/ticker-shaped at the yfinance boundary | IDK, external-API boundary | Not migratable — needs asset_id→fetchable-symbol resolution, not a key swap |
| `services/optimizer/constraint_resolver.py`, `services/optimizer/strategy_profiles.py`, `services/scorer.py`, `services/timing_score.py` | **Zero symbol usage** — confirmed | N/A | No change needed |
| `main.py:2039-2650` (`POST /analyze/optimizer`) | `scores_map = {s["symbol"]: s ...}` — the literal root of the symbol-keyed dict that flows into every downstream optimizer structure and gets frozen into `RecommendationSnapshot` | IDK | **Critical — upstream root cause, best leverage point** |

### 1.6 Appendix — Analytics / Shadow Portfolio (file:line)

| File:Line | What it does | Kind | Risk |
|---|---|---|---|
| `services/analytics/regime_detector.py` (whole file) | `^GSPC`, `^SET.BK`, `QQQ`, `^VIX` — 100% benchmark symbols | **BM** | None — confirmed out of Registry scope entirely |
| `services/analytics/factor_engine.py:386,799-825,840-841` | `market_values[item.symbol]`; O(n²) self-join `r.symbol == s.symbol` | IDK | High — live recompute, safe to switch; also a latent silent-collision bug independent of the migration |
| `services/analytics/attribution_engine.py`, `human_vs_ai.py`, `regime_attribution.py` | Attribution/BHB math is symbol-agnostic (aggregate NAV/return columns only) — **but this classification was incomplete.** `attribution_engine.py::_timing_and_fee_effects` (found during the M6 Phase 4 audit, 2026-07-10) reuses `execution_ledger.py`'s `_recommendation_prices`/`_linked_transactions` for its per-symbol timing-delta dollar-weighting, i.e. the same plan-vs-live-Transaction join as §2.3 item 1. `human_vs_ai.py`/`regime_attribution.py` remain confirmed symbol-agnostic. | IDK (one function) | Fixed 2026-07-10 alongside §2.3 item 1 — see the Phase 4 note there. |
| `services/decision_memory/shadow_tracker.py` (~40 touch points, 1877 lines) | `_resolve_shares_from_weights` (L404-428) is the canonical shadow-holding shape `{"symbol":..., "shares":...}`, consumed by ~15 other functions in the same file (valuation, repair, regeneration) | IDK | **Highest migration surface in the two subsystems** — one additive JSON-shape change ripples everywhere |
| `services/decision_memory/shadow_tracker.py:1301-1332` | `repair_shadow_portfolios` — same shape dependency, backfill path | IDK (partly FROZEN) | High |
| `services/decision_memory/calibration.py:124-154` | `AgentCache.filter_by(symbol=sym, ...)` — real DB column join, one query per symbol (N+1, pre-existing) | IDK | Medium |
| `models/database.py:269-283` (`BenchmarkPrice.symbol`) | Intentional benchmark symbol column | **BM** | None |
| `models/database.py:286-309` (`SignalHistory.symbol`) | Real indexed column, no FK | IDK | Migration candidate |
| `models/database.py:427-476` (`ShadowPortfolio`, `ShadowPortfolioSnapshot`) | Numeric columns are already derived; only `holdings_json`/`inception_holdings_json`/`benchmark_symbol` are symbol-keyed | Mixed | See shadow_tracker row above |
| `main.py:4187-4240` (`/analytics/signals`) | `symbol` query param → `SignalHistory.symbol` filter | IDK | Direct passthrough |
| Every other `/analytics/*` endpoint | portfolio_id/shadow_id/decision_id-scoped at the HTTP layer; symbol only appears once you descend into the service layer | — | — |

### 1.7 Appendix — Recommendations / AI Evaluation (file:line)

| File:Line | What it does | Kind | Risk |
|---|---|---|---|
| `models/database.py:368-394` (`RecommendationSnapshot`) | `scores_map_json`, `layer1/2/3_output_json`, `projected_allocations_json` — all symbol-keyed blobs, **frozen at write** | **FROZEN** | Additive-only; `projected_allocations_json` is the highest-leverage single shim point since most evaluation code re-parses it |
| `models/database.py:397-424` (`UserExecutionDecision`) | `original_symbol`, `replacement_symbol` (plain String columns), `rejected_symbols_json` | **FROZEN** | Low effort to add `original_asset_id`/`replacement_asset_id` alongside for new rows |
| `models/database.py:512-544` (`RecommendationGrade.detail_json`) | Model docstring **explicitly states** "never UPDATEd... per OPTIMIZER_PHILOSOPHY.md Invariant 1" | **FROZEN** | Strongest textual confirmation of the immutability constraint anywhere in the codebase |
| `services/decision_memory/snapshot_writer.py:92` | The single write site for `scores_map_json` | FROZEN (write) | Any registry integration here must be additive on **new** rows only |
| `services/evaluation/horizon_grader.py:88-90,114-120` | `{h["symbol"]: h ...}` dict-keys a frozen blob; writes `per_symbol` breakdown into `RecommendationGrade.detail_json` | IDK on FROZEN data | Medium — read-side re-derivation of frozen history |
| `services/evaluation/plan_grader.py:107-127` (`read_snapshot_plan_inputs`) | Shared reconstruction point reused by `execution_ledger.py`, `execution_analyzer.py`, `opportunity_cost.py`, `recommendation_ledger.py` | IDK on FROZEN data | **Natural single choke point for a read-shim** — fix once, benefits 4 consumers |
| `services/evaluation/execution_analyzer.py:88-181` | Joins **frozen** plan allocations (symbol from JSON) against **live**, mutable `Transaction.symbol` | IDK, frozen-vs-live join | **Highest correctness risk in this domain** — a post-hoc symbol rename silently breaks this join today; this is the actual argument for why `asset_id` matters here, independent of any Registry preference |
| `services/evaluation/ideal_series.py:217-584` | Backtest/counterfactual engine, heavy symbol-keyed dict manipulation, computed live (not frozen) | IDK | High — largest evaluation file by symbol density after shadow_tracker; safe to switch since not persisted |
| `services/optimizer_action_summary.py:29-56` (`build_action_summary`) | Not in the original file list but is a **hidden shared hub** — `plan_grader`, `execution_analyzer`, `recommendation_ledger` all depend on its `"symbol"` key contract | IDK | Medium — single point of leverage |
| `services/idea_review.py:279-431` | Hand-rolled `.BK`-suffix fuzzy matcher (`_symbol_matches`) — a miniature, duplicate identity-resolution layer | IDK, duplicate logic | High value to delete and replace — stateless, no persistence, no immutability constraint |
| `services/override_classifier.py:44-56` | Pure function, called only at write time for new decisions | IDK | Low — easiest file to extend with `asset_id` params |
| `services/operations_center.py`, `services/translations/muji_translator.py`, `services/run_progress.py` | **Confirmed zero symbol usage** | N/A | No change needed |
| `models/asset.py:34-61` (Registry side, for reference only) | `display_symbol` column **already exists** on `Asset` | — | The target field consumers should eventually read is already built; nothing new to add on the Registry side |

---

## 2. Read-Path Classification Summary

### 2.1 True identity/lookup keys (would change behavior if the key changed)

Every `filter_by(symbol=...)`, every `dict[symbol, ...]`, every set built from symbols for membership testing (`agents/optimizer.py`'s consensus engine), every join between two independently-populated symbol-keyed structures (`portfolio_snapshots.py` price_map ↔ PortfolioItem; `execution_analyzer.py` frozen plan ↔ live Transaction). These are the sites where a wrong or ambiguous symbol produces a wrong number, not just a wrong label — Sections 1.4–1.7 tag every one of them **IDK**.

### 2.2 Display-only (safe to leave as `symbol`/`display_symbol` indefinitely)

Every `"symbol": tx.symbol` in a response-serialization helper (`_tx_row`, `_snapshot_row`, `main.py`'s per-idea output dict), every log-line interpolation, every narrative string in `position_sizing.py::_build_reasoning`. These need a `display_symbol` field added to the payload eventually (the Registry already has one — `models/asset.py`), but changing them carries no accounting risk and can happen any time, independent of everything else in this report.

### 2.3 The three specific correctness risks worth calling out by name

1. **`execution_analyzer.py:88-181`** — joins a frozen recommendation's symbol against the *live*, mutable `Transaction.symbol`. If a ticker is ever renamed between recommendation time and execution time, this join silently produces a false "no linked transaction" negative. This is the strongest concrete argument in the whole codebase for why `asset_id` (permanent) beats `symbol` (impermanent) — not a hypothetical, a description of a real failure mode with today's code.

   **Partially fixed, 2026-07-10 (M6 Compatibility-Layer Phase 4).** `compute_execution_analysis` itself was not touched — it remains a deliberately pure function, unit-tested with synthetic data, no DB access. The fix lives at the DB-aware boundary that assembles its `linked_transactions` argument: `services/evaluation/execution_ledger.py::_linked_transactions(db, decision_id, known_symbols=None)` now resolves each transaction's symbol against the decision's own plan symbols via `services/registry_symbol_matching.py::match_known_symbols()` before handing the list to `compute_execution_analysis`. A Registry (or legacy `.BK`) match rewrites the transaction's symbol to the plan's spelling; the residual risk — a spelling difference the Registry itself hasn't resolved yet — is unchanged and still requires M5 Track B (native `asset_id` on `Transaction`) to close completely. `recommendation_ledger.py::get_report_card` and `services/analytics/attribution_engine.py::_timing_and_fee_effects` (a fourth consumer of this join discovered during the Phase 4 audit — see the correction to this document's own §3.1/§1.6 classification below) both reuse the same fixed helper, so the fix reaches all three read paths, not just one.
2. **`execution_optimizer.py:106-125` (`classify_reason`)** — recovers a structured fact (is this trade mandatory?) via `symbol in v` substring search against a free-text string built by `policy_engine.py`. Two-hop stringly-typed coupling; a partial migration (one side moves to asset_id, the other doesn't) breaks this silently rather than loudly.
3. **The `.BK`-variant matching shim**, independently hand-rolled in `basket_simulation.py`, `execution_plan.py`, `position_sizing.py`, `allocation_engine.py`, and `idea_review.py` — five separate implementations of "is this bare ticker the same instrument as that `.BK`-suffixed one?" This is precisely the question the Asset Registry's `identity_resolver` already answers once, correctly, per ADR-004 ("one implementation per rule"). It is the single highest-value, lowest-risk target in this entire report.

---

## 3. Integration Plan

Per Migration Principle 3 of the parent plan ("no flag days... every switchover is per-consumer, feature-flagged, reversible") and Principle 6 ("expand → verify → cut over → contract"), nothing below proposes a simultaneous cutover. Each row is independently shippable.

| Module group | Current | Target | Effort | Dependencies |
|---|---|---|---|---|
| **Watchlist CRUD** (`main.py` `/watchlist*`) | `Watchlist.symbol` string filter | Reads resolve `symbol → AssetView` via compatibility layer (§4) for display/classification only; writes unchanged | S | §4 compatibility layer only |
| **`.BK`-variant shims** (basket_simulation, execution_plan, position_sizing, allocation_engine, idea_review) | 5 independent hand-rolled suffix-matchers | Single call to `resolve_asset(symbol)` from §4, delete the local shims | M | §4 compatibility layer |
| **`execution_penalty.classify_execution`** | Regex/hardcoded-list inference of DR/ETF/INDEX/EQUITY from ticker shape | Read `Asset.asset_type`/DR-relationship from Registry via §4 lookup, falling back to today's heuristic only when unresolved | M | §4; Registry already models this (ASSET_REGISTRY.md §5, §8) |
| **Sector classification** (`main.py` `THAI_SECTOR_MAP`/`_get_sector`, `/admin/*-sectors`) | Static maps + live yfinance fallback, keyed by symbol string | Registry `AssetClassification` becomes the read source; existing maps become the seed data / fallback for unresolved symbols | M | §4; Registry classification model already exists (M1) but is not yet populated for classification dimensions beyond identity |
| **Optimizer internal dict-keys** (`agents/optimizer.py` score_map/pc_map/alloc_map) | `dict[symbol, ...]`, rebuilt every run, not persisted | Same shape, keyed by `asset_id` where resolvable, symbol retained as a display field on each entry | L | §4; **must not** touch the AI prompt/response JSON contract — AI still speaks symbols (§3.2) |
| **Consensus engine set-overlap scoring** | `l1_sells & l2_buy_syms` (symbol sets) | Same math, over `asset_id` sets, once optimizer internals carry asset_id | M | Optimizer internal dict-key migration above |
| **`policy_engine` violation strings + `execution_optimizer.classify_reason`** | Symbol interpolated into prose, recovered via substring search | Replace the free-text coupling with a structured `violation.subject_asset_id` (or symbol, whichever the optimizer migration lands on) field; keep the human-readable string for display only | M | Optimizer internal dict-key migration; this is the one place a **structural fix**, not just a rename, is warranted |
| **Factor engine** (`factor_engine.py`) | `market_values[item.symbol]`, O(n²) self-join by symbol | Same shape keyed by `asset_id`; self-join replaced by index-zip regardless (efficiency, not identity) | S | §4 |
| **Shadow portfolio holdings shape** (`shadow_tracker.py`) | `{"symbol": ..., "shares": ...}` in `inception_holdings_json` and every downstream valuation function | Add `asset_id` field **additively** to the dict shape for *new* shadows; existing frozen rows keep symbol-only forever | L | §4; must respect immutability of already-persisted `ShadowPortfolio.inception_holdings_json` rows |
| **Calibration** (`calibration.py`) | `AgentCache.filter_by(symbol=sym)` per-symbol query | Same query pattern; `SignalHistory` gains an additive `asset_id` column for rows written after the change | S | §4 |
| **Recommendation write path** (`snapshot_writer.py`, `main.py` `POST /analyze/optimizer`) | `scores_map = {s["symbol"]: s ...}` built once, frozen into 4+ JSON columns | The single upstream root: if this dict is built keyed (or co-keyed) by `asset_id` here, every downstream consumer of `RecommendationSnapshot`/`SignalHistory` inherits it **for free on new rows**, no per-consumer rewrite needed | M | §4; highest-leverage single change in the whole report |
| **AI Evaluation read-side** (`plan_grader.read_snapshot_plan_inputs`, `optimizer_action_summary.build_action_summary`) | Re-parses frozen `projected_allocations_json` by symbol | Single shared shim function reads `asset_id` when present (new rows), falls back to symbol-only parsing (old rows) — one change point, four consumers benefit | S | Recommendation write path change above (for new rows to have asset_id to read) |
| **`execution_analyzer.py` frozen-vs-live join** | `Transaction.symbol` (live, mutable) vs frozen plan symbol | **Blocked on M5** — cannot be made robust without `Transaction` itself carrying `asset_id`. Until then, this risk is *documented*, not fixed. | — | M5 (ledger backfill) — out of this report's deliverable scope |
| **Ledger tables** (`Transaction`, `PortfolioItem`, `PortfolioSnapshot`, `Watchlist` themselves) | symbol-only, no asset_id column | Additive `asset_id` column, backfilled, replay-parity-gated, engine cutover | XL | **This is M5, not M6.** Explicitly out of scope for "read path" work per this brief's own schema-change constraint. |

Effort key: S = days, M = 1-2 weeks, L = 2-4 weeks, XL = its own milestone (M5).

### 3.1 What does NOT need to change

Confirmed zero or near-zero symbol coupling, no work item needed:

- `services/optimizer/constraint_resolver.py`, `services/optimizer/strategy_profiles.py` — sector/portfolio-level aggregates only
- `services/scorer.py`, `services/timing_score.py` — pure math over pre-fetched dicts
- `services/analytics/regime_detector.py`, `attribution_engine.py`, `human_vs_ai.py`, `regime_attribution.py` — benchmark-only or aggregate-NAV-only
- `services/operations_center.py`, `services/translations/muji_translator.py`, `services/run_progress.py`, `services/evaluation/scorecard.py`, `trust_report.py`, `verdict_composer.py`, `expired_writer.py` — confirmed zero symbol usage

### 3.2 Explicit non-goal: the AI prompt/response contract

`agents/optimizer.py`'s L1/L2/L3 prompts instruct the LLM to read and return JSON with `"symbol"` fields. This report does **not** propose changing that contract. The AI layer is, and should remain, symbol-facing — it is human/AI-readable text, exactly the role `display_symbol` plays elsewhere in the architecture. `asset_id` resolution happens in the deterministic Python layer that wraps the AI call, before and after, never inside the prompt. This matches OPTIMIZER_PHILOSOPHY.md §6's judgment/arithmetic boundary: identity resolution is arithmetic (exact, deterministic), and does not belong inside the probabilistic layer.

---

## 4. Compatibility Layer

### 4.1 `resolve_asset()` — the one new function this report proposes

A single new, additive module, e.g. `services/registry_lookup.py`, wrapping the already-built M1–M3 Registry/Resolver (reuse per ADR-004 — no new identity logic, this module contains zero rules):

```
resolve_asset(symbol: str) -> AssetView | Unresolved
resolve_asset(asset_id: int) -> AssetView
```

`AssetView` is a read-only projection: `asset_id`, `canonical_symbol`, `display_symbol`, `market`, `exchange`, `currency`, `asset_type`, `classification` (sector/etc., once populated). Internally this is nothing more than `identity_resolver.resolve()` plus a `find_by_identifier()` call against already-minted assets (both exist today, M2/M3), wrapped in a short-TTL in-process cache (mirroring the existing `AgentCache`/regime-detection 30-minute cache pattern already used elsewhere in this codebase) so hot read paths (optimizer runs, watchlist loads) don't re-run adjudication on every request.

**`Unresolved` is a first-class return value, not an exception.** Per ASSET_REGISTRY.md §4 ("resolve decisively or ask — never guess"), a symbol with no minted Asset (the 11/52 unresolved transactions noted in §0) must not silently synthesize a fake identity. Callers get back an honest "don't know yet" and fall back to today's symbol-string behavior — this is precisely what makes the layer additive and risk-free: **every existing code path keeps working unchanged for any symbol the Registry hasn't resolved**, and only improves for symbols it has.

### 4.2 `legacy symbol adapter` — for the mechanical replacement of the five `.BK`-variant shims

A thin function, `resolve_symbol_variants(symbols: list[str], known: set[str]) -> dict[str, str]`, that replaces `basket_simulation._resolve_symbol_sectors`'s duplicated logic (and its 4 copies) with one call to `resolve_asset()` per symbol, matching by `canonical_symbol`/current identifiers instead of hand-rolled suffix arithmetic. This is a pure refactor of existing, already-tested behavior — the DR/`.BK` semantics don't change, only where the logic lives (one place instead of five).

### 4.3 Where NOT to put the compatibility layer

It must not be called from inside `services/portfolio_rebuilder.py`'s replay loop or `services/ledger_validator.py`'s CHECK functions. Those are the accounting-critical, deterministic-replay-must-be-bit-identical files that M5 owns; introducing a Registry lookup into replay before M5's parity gate exists would be exactly the kind of "silent behavior change during coexistence" Migration Principle 3 forbids. The compatibility layer is for **analytics, optimizer internals, evaluation, and CRUD/display paths only** — never inside the replay/validate loop.

### 4.4 What the compatibility layer explicitly does not solve

It does not give `Transaction`/`PortfolioItem`/`PortfolioSnapshot` an `asset_id` column, does not make replay id-keyed, and does not close the `execution_analyzer.py` frozen-vs-live join risk (§2.3 item 1). Those require M5. This report's contribution is bounded honestly: it makes every *downstream* read path Registry-informed for identity/classification facts, while the ledger itself remains the M5 gate's problem.

---

## 5. Refactoring Order

Ordered for minimum blast radius first, per Migration Principle 6 (expand → verify → cut over → contract) and this codebase's own testing discipline (regression suite green at every boundary).

**Phase 1 — Build the compatibility layer, prove it on the lowest-stakes consumer.**
1. `services/registry_lookup.py` (`resolve_asset()`, `Unresolved`, TTL cache) — new file, zero existing files touched. **Shipped 2026-07-09** — see [ASSET_REGISTRY_IMPLEMENTATION_PLAN.md](ASSET_REGISTRY_IMPLEMENTATION_PLAN.md) §13 Changelog for the full accounting. The shipped API differs from this section's sketch in one respect: `resolve_asset(db, query)` is a single function taking `db` explicitly and dispatching on `query`'s type (`str` vs `int`/`AssetId`), rather than two db-less overloaded signatures — documented in the module's own docstring, consistent with every other Registry-facing function in this codebase.
2. Wire it into Watchlist read paths only (`GET /watchlist`) as a display-enrichment addition (`display_symbol`, classification) — no behavior change to identity/dedup logic, purely additive response fields. **Not started** — the 2026-07-09 shipment was scoped to the module and its tests only; no call site was touched.
3. Regression: full existing test suite green, plus new unit tests for `resolve_asset()` mirroring the M1–M4 testing idiom already established (in-memory SQLite, `_shape`/`_result` fixture helpers). **Done for the module itself** — 18 new tests plus the full pre-existing Asset Registry test family (133 tests total) green. Step 2 has no regression surface yet since nothing calls the module.

**Phase 2 — Retire the duplicated `.BK`-variant shims. Shipped 2026-07-09** — see [ASSET_REGISTRY_IMPLEMENTATION_PLAN.md](ASSET_REGISTRY_IMPLEMENTATION_PLAN.md) §13 Changelog for the full accounting.
4. Replace `basket_simulation._resolve_symbol_sectors` with `resolve_asset()`-backed resolution; this is the canonical implementation the other 4 files should have been calling all along. **Done.** The shipped design differs slightly from this sketch: rather than inlining Registry calls directly into `_resolve_symbol_sectors`, a new shared adapter, `services/registry_symbol_matching.py::match_known_symbols(db, symbols, known)`, was introduced and is what all five files (plus a sixth, previously-undocumented consumer, `portfolio_construction.py`) call — this keeps the fallback-preserving logic in exactly one place rather than repeating "try Registry, then fall back to the heuristic" five times.
5. Repoint `execution_plan.py`, `position_sizing.py`, `allocation_engine.py`, `idea_review.py` at the single implementation; delete their local copies. **Done.** Each file's hand-rolled bare/`.BK` dual-indexing was replaced by a call to `match_known_symbols()`; `idea_review.py` had four separate instances of the pattern (`_get_sector`, the `AnalysisCache` lookup, the holdings lookup, and the `known_symbols`/`symbols_with_db_sector` yfinance-skip gate) and all four were retired.
6. Regression: existing execution/sizing/idea-review test suites green with identical outputs on the same fixtures (this phase is a pure refactor — output must not change for any already-resolved symbol). **Done, with one documented exception.** `test_basket_simulation.py` and `test_position_sizing.py` exercise only the pure `compute_*` functions, which this phase did not touch, so they were unaffected by construction; `test_risk_budget_allocation.py` and `test_portfolio_construction.py` passed unchanged. `execution_plan.py` and `idea_review.py` had no pre-existing test files, so new integration tests (`backend/tests/test_registry_symbol_matching_integration.py`) were written to cover their refactored DB-loading wrappers directly. The one documented output change: the shared fallback is symmetric where a few of the retired shims were asymmetric (see the changelog entry) — additive-only (can only add a match, never remove one), and no existing caller was found to depend on the asymmetry.

**Phase 3 — Recommendation write-path root fix (highest leverage). Step 7 shipped 2026-07-09; step 8 reconsidered and reshipped, 2026-07-10.**
7. `main.py`'s `POST /analyze/optimizer` scores_map construction and `snapshot_writer.py` gain additive `asset_id` alongside `symbol` for every entry, for rows written **after** this change ships. No backfill of existing `RecommendationSnapshot`/`SignalHistory` rows (Design Invariant 1). **Done.** New module `services/registry_recommendation_context.py` (`build_registry_context()`, `enrich_scores_map_for_snapshot()`) resolves every symbol in a run's `scores_map` through `registry_lookup.resolve_asset()` and returns a *new* dict — same keys/values, plus an additive `"registry": {resolved, asset_id, canonical_symbol, market, exchange}` (or `{resolved: false, reason}`) per entry — never mutating the live `scores_map` that feeds the AI prompt, `portfolio_data`/`watchlist_data`, timing enrichment, and `execution_penalty`. `main.py`'s single call site (`POST /analyze/optimizer`, immediately before `write_recommendation_snapshot()`) was changed from `scores_map=scores_map` to `scores_map=enrich_scores_map_for_snapshot(db, scores_map)` — a one-line change, already inside the existing failure-swallowing `try/except` around the snapshot write, so a total Registry failure degrades to writing the unenriched map exactly as before. `snapshot_writer.py` itself needed **zero code change** — `scores_map_json=_j(scores_map)` was already a generic passthrough serializer, so it carries the new `"registry"` key for free. `SignalHistory` (no free-form JSON column) is **not** enriched — see the Phase 3 note below and the Technical Debt Register.
8. `plan_grader.read_snapshot_plan_inputs` and `optimizer_action_summary.build_action_summary` gain an `asset_id`-aware read path with symbol-only fallback for pre-change rows. **Rescoped, 2026-07-10 (M6 Compatibility-Layer Phase 4 audit).** A full read of both functions found neither has a genuine cross-source identity join to fix: `read_snapshot_plan_inputs` only reconstructs `target_allocations`/`active_policy` from a single snapshot's own stored JSON (no symbol matching at all), and `build_action_summary` indexes a dict built from `target_allocations` by symbols drawn from that *same* list (internal, single-source indexing — nothing a wrong symbol could corrupt, since both sides are the identical list). `build_action_summary` is also documented and enforced as pure ("No AI calls, no DB access, no side effects"); Registry calls need a `db` session and don't belong inside it. Wiring "asset_id-awareness" into either function as originally worded would have been decorative, not corrective. The actual correctness-relevant read-path gap in this domain was the plan-vs-live-`Transaction.symbol` join documented at §2.3 item 1 — fixed instead at `execution_ledger.py::_linked_transactions`, `recommendation_ledger.py::get_report_card`, and `attribution_engine.py::_timing_and_fee_effects` (a fourth consumer found during this same audit). See [REGISTRY_INTEGRATION_GUIDE.md](../architecture/REGISTRY_INTEGRATION_GUIDE.md) §"AI Evaluation read-path (Phase 4)" for the full writeup, and the Phase 4 Migration Report below for the complete audit trail.

**Phase 4 — Optimizer internals + consensus scoring.**
9. `agents/optimizer.py` internal dict-keys (`score_map`, `pc_map`, `alloc_map`) migrate to `asset_id`-keyed where resolvable, retaining `symbol`/`display_symbol` as data fields, not keys. AI prompt/response contract untouched (§3.2).
10. Consensus engine set-overlap math re-verified numerically identical on `asset_id` sets vs symbol sets for every already-resolved symbol (regression test: same portfolios, same consensus scores, before/after).

**Phase 5 — Structural fix for the policy/execution string-coupling.**
11. `policy_engine.py` violations gain a structured `subject_asset_id` (or equivalent) field; `execution_optimizer.classify_reason` reads the structured field instead of substring-searching prose. Free-text message stays for human display only.

**Phase 6 — Shadow portfolios, factor engine, calibration (parallelizable with Phase 4/5, lower urgency).**
12. `shadow_tracker.py` new-shadow creation gains additive `asset_id` in the holdings shape; existing frozen `inception_holdings_json` rows untouched.
13. `factor_engine.py` and `calibration.py` switch their internal joins to `asset_id` where resolvable.

**Phase 7 — Classification consolidation (independent, can run any time after Phase 1).**
14. `main.py`'s `THAI_SECTOR_MAP`/`_get_sector`/`/admin/*-sectors` become Registry-classification-backed, with the existing static maps retained as seed data and as the fallback for unresolved symbols.

**Explicitly not scheduled in this report:** ledger table schema changes, replay engine changes, `ledger_validator.py` changes, `execution_analyzer.py`'s frozen-vs-live join fix. All four require M5.

---

### Phase 3 Migration Report (2026-07-09)

Per the requesting brief's own deliverable #4 ("migration report summarizing migrated entry points, unresolved paths, remaining work"):

**Every place a Recommendation is created, as audited this phase.** `RecommendationSnapshot` and `SignalHistory` are the only two models this codebase's architecture (`docs/architecture/ARCHITECTURE.md`) names as recommendation records, and both are written from exactly **one** call site: `main.py`'s `POST /analyze/optimizer` endpoint, after the 3-layer optimizer (`agents/optimizer.py`) returns and `OptimizerHistory` is committed. There is no second endpoint, background job, or script in production code that creates a Recommendation. (`backend/scripts/copy_portfolio.py` and `backend/scripts/seed_historical_analytics.py` also construct `RecommendationSnapshot`/`SignalHistory` rows, but as administrative data-copy/seeding tools operating on already-decided data, not as recommendation-generation logic — out of scope, unchanged.)

**Migrated entry points:**
- `main.py`'s `scores_map` → `RecommendationSnapshot.scores_map_json`, via `services/registry_recommendation_context.py`, as described in Phase 3 step 7 above. This is the recommendation-creation write path.

**Audited and explicitly excluded, with reasoning (per the brief's "do not assume the list is complete" instruction):**
- **`SignalHistory`** — same optimizer run, same `scores_map` data, but the model has fixed typed columns and no free-form JSON field. Attaching `asset_id` would require a schema migration, which this phase's own brief forbids ("No schema migration is permitted"). Registry resolution still runs once per optimizer run (shared via `scores_map`'s enrichment pass) and is logged, but is not persisted onto `SignalHistory` rows. Flagged in the Technical Debt Register below.
- **Shadow Portfolio recommendation generation** (`services/decision_memory/shadow_tracker.py`'s `create_recommendation_shadow()`, `create_active_model_shadow()`, `create_static_frozen_shadow()`) — audited and determined **not** to be a Recommendation-creation path: these functions consume an *already-written*, frozen `RecommendationSnapshot.projected_allocations_json` to build a paper-trading mirror for later grading; they do not independently generate a recommendation. This is exactly the read-path plan's own Phase 6 ("Shadow portfolios... Yes for new shadows going forward"), a distinct, later phase — not touched here, consistent with the brief's "No Analytics migration" / "No Execution... changes" constraints.
- **Strategy output** (L1/L2/L3 outputs, consensus, portfolio DNA, style drift) — all persisted through the same single `write_recommendation_snapshot()` call already covered above; there is no separate creation point for "strategy output" independent of the `RecommendationSnapshot` write.

**Unresolved paths / remaining work:**
- Step 8 (read-side `asset_id`-awareness in `plan_grader.py`/`optimizer_action_summary.py`) — not started, distinct phase (read path, not write path). *Superseded — see the Phase 4 Migration Report below.*
- `SignalHistory` asset_id association — blocked on a schema change (M5 Track B / a future, explicitly-authorized migration).
- `backend/scripts/copy_portfolio.py` / `seed_historical_analytics.py` — not updated; they copy/seed pre-existing `scores_map_json` blobs verbatim (copy) or construct synthetic ones for tests (seed), so nothing about this phase requires them to change, but a future full-coverage audit should confirm they don't need the same enrichment for their own data-quality purposes.

---

### Phase 4 Migration Report (2026-07-10) — AI Evaluation read-path business logic

Scope as requested: migrate `plan_grader.py`, `optimizer_action_summary.py`, `execution_analyzer.py`, `execution_report.py`, and "AI evaluation helpers" off direct symbol/ticker/alias matching, per this section's own instruction to audit first rather than assume the named list is exhaustive or all directly applicable.

**Audit method.** Every file in `backend/services/evaluation/` was read in full (not grepped): `plan_grader.py`, `optimizer_action_summary.py`, `execution_analyzer.py`, `execution_ledger.py`, `recommendation_ledger.py`, `opportunity_cost.py`, `horizon_grader.py`, `ideal_series.py`. Each direct symbol lookup/comparison found was classified as a genuine cross-source identity join (fixable) or internal single-source indexing (not a risk).

**Migrated:**
- `services/evaluation/execution_ledger.py::_linked_transactions` — the plan-vs-live-`Transaction.symbol` join (§2.3 item 1) now resolves through `registry_symbol_matching.match_known_symbols()` when the caller supplies the decision's own plan symbols as `known_symbols`. `compute_execution_analysis` (the pure function that actually scores the match) is unmodified.
- `services/evaluation/recommendation_ledger.py::get_report_card` — its inline duplicate of the `linked_transactions`/`recommendation_prices` construction was replaced by reusing `execution_ledger.py`'s now-fixed `_linked_transactions`/`_recommendation_prices`, removing the duplication (ENGINEERING_PRINCIPLES.md Single Source of Truth) and inheriting the Registry-aware matching for free.
- `services/analytics/attribution_engine.py::_timing_and_fee_effects` — a fourth, previously-undocumented consumer of the same join, found during this audit (see the §1.6/§3.1 correction above). Same one-line fix: pass `known_symbols` through to `_linked_transactions`.

**Audited and explicitly excluded, with reasoning:**
- `plan_grader.py` (`_derive_action_summary_and_buys`, `read_snapshot_plan_inputs`) — no cross-source join; internal single-list indexing only.
- `optimizer_action_summary.py::build_action_summary` — documented pure function (no DB access); Registry calls do not belong inside it.
- `services/evaluation/ideal_series.py` — live yfinance price fetches keyed by symbol from one frozen list; an external-API boundary, not an identity join (same category as `timing_intelligence.py`).
- `services/evaluation/opportunity_cost.py` — decision-level aggregate only, never joins by symbol.
- `services/evaluation/horizon_grader.py::score_directional_calls` — a genuine cross-source join (inception holdings vs. a shadow's later snapshot), but both sides are the same shadow's own frozen output, not independently-sourced spellings. Lower risk; **intentionally deferred**, not fixed this phase.

**Naming mismatch:** `execution_report.py`, named in the requesting brief, does not exist in this codebase. The only match is `_print_execution_report()` in `manage.py` (CLI output for the M5 migration executor) — unrelated to AI Evaluation. Recorded here rather than silently dropped, per this document's own audit standard.

**Tests:** `backend/tests/test_execution_ledger.py` gained three tests (legacy `.BK` fallback links a previously-unmatched transaction; a genuine Registry conflict is never silently unified; wholly unrelated symbols stay unmatched — regression safety). `backend/tests/test_recommendation_ledger.py` gained one test proving the same fix reaches `get_report_card`. Full existing `test_execution_analyzer.py` suite (the pure function) is unchanged and unaffected. Full backend suite run before/after via `git stash`: byte-identical 49-failure set in both runs (all pre-existing, none in evaluation/registry/attribution modules), 1040 passed baseline → 1044 passed with this phase's 4 new tests, zero regressions.

---

### Phase 5 Migration Report (2026-07-10) — Execution & Evaluation completion audit

The Phase 5 brief asked for a fresh audit of everything remaining in `backend/services/evaluation/` and `backend/services/execution/`, explicitly not assuming the Phase 4 scoping was still correct, with two possible outcomes: implement whatever genuinely qualifies, or declare the domain complete with rationale.

**Directory finding, recorded before anything else:** `backend/services/execution/` does not exist — the same class of naming mismatch as the Phase 4 report's `execution_report.py` finding. This report interprets "Execution" as the domain §1.3 already names "Execution sizing/planning": `services/execution_plan.py`, `services/funding_source_analysis.py`, `services/optimizer/execution_optimizer.py`, `services/optimizer/execution_penalty.py`, `services/optimizer/stabilization.py`.

**Audit method.** Every file in that Execution set was read in full, plus a re-check of every `services/evaluation/` file not already fully disposed of by the Phase 4 report (`scorecard.py`, `trust_report.py`, `verdict_composer.py`, `expired_writer.py` re-grepped for `symbol`; `execution_analyzer.py`'s pure-function status re-confirmed unchanged). `override_classifier.py` was also read in full as an evaluation-adjacent file, for completeness, though it sits outside both literal directories.

**Migrated:** none. Every already-migrated consumer (`execution_ledger.py`, `recommendation_ledger.py`, `attribution_engine.py::_timing_and_fee_effects` from Phase 4; `basket_simulation.py`, `execution_plan.py`, `position_sizing.py`, `allocation_engine.py`, `idea_review.py`, `portfolio_construction.py` from Phase 2) was reconfirmed still wired via `match_known_symbols`/`registry_symbol_matching` imports, no regressions.

**Audited and explicitly excluded, with reasoning:**
- `plan_grader.py`, `optimizer_action_summary.py`, `ideal_series.py`, `opportunity_cost.py` — unchanged from the Phase 4 audit (no cross-source join, or external-API boundary).
- `evaluation/scorecard.py`, `trust_report.py`, `verdict_composer.py`, `expired_writer.py` — confirmed zero `symbol` occurrences.
- `funding_source_analysis.py::build_funding_sources` — read in full this phase. Docstring: "Pure service — no AI calls, no DB mutations, no side effects." `item_values`, `signal_map`, and `buy_set` are all built by one caller (`main.py`'s execution-plan surface) from one holdings loop; there is no independently-sourced second symbol collection to join against. Not a genuine identity-join candidate.
- `override_classifier.py::build_override_record` — normalizes/uppercases `original_symbol`/`replacement_symbol` for storage; never compared against a second source. Outside this brief's literal directory scope regardless.
- `horizon_grader.py::score_directional_calls` — re-confirmed, unchanged conclusion from Phase 4: real join, but same-shadow frozen-vs-frozen data, deliberately deferred.

**Audited, real gaps, deliberately not implemented — blocked on business-logic redesign, not schema/M5:**
- `execution_optimizer.py::classify_reason` (already tracked in the Technical Debt Register below as the §5 Phase 5 structural fix) — this audit reached the identical conclusion: fixing it requires `policy_engine.py` to emit a structured `subject_asset_id` field instead of free text, which is a redesign of the policy/violations contract, not a caller-boundary read-path change. Not attempted.
- `execution_penalty.py::classify_execution` — new finding this phase. Infers `asset_type` from ticker shape (regex `.BK` pattern + hardcoded ETF list) when the caller hasn't already supplied `is_dr=True`. `AssetView.asset_type` (already a field on the Registry's read model, §"`resolve_asset(db, query)`" in the integration guide) could answer this correctly, but the only call site (`main.py:2177`, inside `POST /analyze/optimizer`'s synchronous execution-context step) has no `db` session threaded to `compute_portfolio_execution_context`/`classify_execution`. Wiring Registry resolution in means changing this `agents/optimizer.py`-adjacent function's signature and control flow — a business-logic change to the optimizer's execution-context step, not a read-path boundary fix. Not attempted; added to the Technical Debt Register.
- `stabilization.py::diagnose_duplicate_tickers` — new finding this phase. Diagnostic-only: scans one pipeline run's own L1/L2/L3 output dicts (`layer1_result`, `layer2_result`, `target_allocations`, `swap_suggestions`, `watchlist_ranking`) for same-symbol duplicates within that single run — not a join against an independently-sourced second symbol collection. Already implicitly covered by this document's existing Technical Debt Register row (becomes unnecessary once optimizer internals migrate to `asset_id` keys, §5 Phase 4's own numbering) — confirmed unchanged, not attempted, since `agents/optimizer.py`'s internal dict-key migration is a separate, later, out-of-scope phase.

**Tests:** none added — no source file was changed. The audit table above and the doc updates are the "prove no implementation is necessary" deliverable this phase's brief asked for in place of new tests.

**Outcome: B — Execution & Evaluation integration is complete.** The two legitimate remaining tracks in §5 are Phase 1 step 2 (Watchlist pilot) and Phase 7 (classification consolidation); both are outside this phase's Execution/Evaluation scope.

---

## 6. Technical Debt Register

Legacy lookups/logic that become removable — fully or partly — once the compatibility layer (and eventually M5) lands:

| Item | Location | Removable when |
|---|---|---|
| 5 independent `.BK`-variant matching shims | `basket_simulation.py`, `execution_plan.py`, `position_sizing.py`, `allocation_engine.py`, `idea_review.py` | **Removed 2026-07-09 (Phase 2).** Replaced by `services/registry_symbol_matching.py::match_known_symbols()`, called from all five files (the legacy bare/`.BK` string comparison itself is retained *inside* that one shared function, as the documented fallback for symbols the Registry hasn't resolved — it is gone from the five call sites, not deleted from existence). |
| `execution_penalty.classify_execution`'s regex/hardcoded-ETF-list asset-type inference | `services/optimizer/execution_penalty.py:36-205` | Once `Asset.asset_type`/DR-relationship is populated in the Registry for all resolved symbols — partial removal, heuristic stays as fallback for unresolved symbols |
| `diagnose_duplicate_tickers` | `services/optimizer/stabilization.py:429,574` | Fully removable once Phase 4 lands — the bug class it detects becomes structurally impossible with `asset_id` keys |
| `ledger_validator.py` CHECK 2 (`_check_symbol_aliases`) | `services/ledger_validator.py:249-301` | **Only after M5** — this check operates on the ledger itself, not the compatibility layer's scope. Left in place, unaffected by this report. |
| `services/portfolio_snapshots.py`'s casing-normalization workaround (L358-377, explicitly commented as a workaround) | `services/portfolio_snapshots.py:358-377` | Only after M5 |
| `THAI_SECTOR_MAP` / `_DR_SECTOR_MAP` as the *primary* classification source | `main.py:366+` | Phase 7 — demoted to seed/fallback data, not deleted (still correct data, just no longer the authority) |
| `idea_review.py`'s hand-rolled `_symbol_matches`/`bk_variants` block (~50 lines) | `services/idea_review.py:279-431` | **Removed 2026-07-09 (Phase 2).** Four separate instances of the pattern in this file alone were retired. |
| `execution_optimizer.classify_reason`'s substring search | `services/optimizer/execution_optimizer.py:106-125` | Phase 5 (§5's own numbering — the policy/execution structural fix). Re-confirmed by the 2026-07-10 Execution & Evaluation completion audit: still blocked on `policy_engine.py` gaining a structured `subject_asset_id` field, a business-logic redesign, not a read-path fix. |
| `execution_penalty.classify_execution`'s regex/hardcoded-ETF-list asset-type inference (see also the identical row above at `services/optimizer/execution_penalty.py:36-205`) | `services/optimizer/execution_penalty.py:94-206` | Found in the 2026-07-10 Execution & Evaluation completion audit: `AssetView.asset_type` could answer this today, but the only call site (`main.py:2177`, `POST /analyze/optimizer`'s synchronous execution-context step) has no `db` session threaded through `compute_portfolio_execution_context`/`classify_execution`. Removable only once that call chain is given a `db` session — a business-logic change to the optimizer's execution-context step, out of this phase's read-path-only scope. |
| `funding_source_analysis.py` confirmed to have no identity-join surface at all | `services/funding_source_analysis.py::build_funding_sources` | Not applicable — nothing to remove. Recorded so a future reader doesn't re-audit it looking for a migration candidate; `item_values`/`signal_map`/`buy_set` are single-source, pure-function inputs built by one caller. |
| `SignalHistory` has no `asset_id`/registry-metadata column — the same optimizer run's Registry resolution (computed once for `RecommendationSnapshot.scores_map_json`, Phase 3) is not persisted onto these rows | `models/database.py:286-310` (`SignalHistory`), write site `main.py:2448` | Only after a schema migration (M5 Track B or an explicitly-authorized additive column) — forbidden this phase by "No schema migration is permitted" |
| Plan-vs-live-`Transaction.symbol` join's residual risk: a spelling difference the Registry hasn't resolved yet (still ~21% of ledger symbols per the M5.3 bootstrap run) still fails to link | `services/evaluation/execution_ledger.py::_linked_transactions` | Only fully closed by M5 Track B (native `asset_id` on `Transaction`) — the Registry-aware matching added 2026-07-10 narrows this gap but cannot close it without the ledger itself carrying `asset_id` |
| `horizon_grader.py::score_directional_calls`'s inception-holdings-vs-shadow-snapshot symbol join | `services/evaluation/horizon_grader.py` (function body) | Intentionally deferred 2026-07-10 — lower risk than the plan-vs-Transaction join (both sides are the same shadow's own frozen output); revisit only if a real divergence is observed |
| `execution_report.py` named in the M6 Phase 4 brief does not exist in this codebase | N/A — naming mismatch, only `manage.py`'s unrelated `_print_execution_report()` CLI helper matches | Not applicable — nothing to remove; recorded so a future reader doesn't go looking for a missing module |

None of these are proposed for deletion in this report — they are flagged as the concrete payoff a future cleanup phase (M7-equivalent for this read-path work) can point to.

---

## 7. Testing Strategy

Following the parent plan's own testing tracks (§8 of ASSET_REGISTRY_IMPLEMENTATION_PLAN.md), scoped to what this report covers:

- **Regression.** Full existing suite green at every phase boundary in §5. Every phase 2–7 change is, by construction, a refactor of already-tested behavior for already-resolved symbols — output must be provably identical, not just "similar," on existing fixtures.
- **Unresolved-symbol behavior.** New tests asserting that `resolve_asset()` returning `Unresolved` causes every caller to fall back to today's exact behavior — this is the property that makes the whole layer safe to ship incrementally while 11/52 transactions remain unresolved.
- **Consensus-math parity.** Phase 4's set-overlap scoring must produce byte-identical `consensus_strength_score` values before/after, for every historical optimizer run in the dev DB.
- **Immutability audit.** A mechanical check (grep-based, like the ones already used in this session) confirming no Phase 3/6 change ever issues an `UPDATE` against `RecommendationSnapshot`, `SignalHistory`, `RecommendationGrade`, or `ShadowPortfolio.inception_holdings_json` rows that predate the change.
- **No accounting drift.** `verify_snapshots` / `validate_ledger` run clean before and after every phase — this report touches nothing in their scope, so a clean run is the expected (not aspirational) outcome, and any drift would indicate scope creep into ledger-adjacent code that should not have happened.

---

## 8. Summary for the reader in a hurry

- The ledger (`Transaction`/`PortfolioItem`/`PortfolioSnapshot`/`Watchlist`) has **no `asset_id` column today**. That's M5, gated, not done, and out of scope here given the "no schema change" constraint.
- What **can** ship now, with zero schema changes: a `resolve_asset()` compatibility layer (§4) that lets every non-ledger read path (optimizer internals, execution sizing, analytics, evaluation, watchlist, idea intake) become Registry-informed for identity and classification, falling back to today's symbol-string behavior for anything not yet resolved.
- The single highest-leverage change is fixing the recommendation write path (§3, §5 Phase 3) so every *future* `RecommendationSnapshot`/`SignalHistory` row carries `asset_id` — four downstream evaluation consumers inherit it for free, with zero rewrite of frozen history.
- The five duplicated `.BK`-variant shims (§2.3 item 3, §6) are the clearest, lowest-risk, highest-value single deletion this report identifies.
- Three concrete correctness risks already exist in production code today, independent of whether this migration ever happens: the frozen-vs-live symbol join in `execution_analyzer.py`, the substring-search coupling in `execution_optimizer.classify_reason`, and the silent-collision risk in every `dict[symbol, ...]` structure in `agents/optimizer.py` and `factor_engine.py`. This report is also, in effect, a bug report.
