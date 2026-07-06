# Decision Log
_Why decisions were made. Useful context when revisiting constraints or architecture choices._
_See [ARCH_SPEC.md](ARCH_SPEC.md) for current specs. See [ROADMAP.md](ROADMAP.md) for phase history._

---

## Yahoo Finance Price Lag — Thai SET Stocks

**Date:** 2026-05 (discovered during snapshot integrity work)  
**Problem:** Yahoo Finance has ~15–20 minute delay for `.BK` symbols after SET closes at 16:30 ICT. Prices pulled at 16:35 may still reflect the last automated auction price, not final ATC.  
**Decision:** APScheduler `daily_portfolio_snapshot` fires at **17:45 ICT** (Mon–Fri), giving yfinance time to publish settled ATC prices.  
**Reasoning:** `KBANK.BK` pulled at 16:35 showed 196.5; ATC settled at 197.0 — 0.25% error compounding across a portfolio.  
**Impact:** Snapshot timing must not be moved earlier. Applies to automated job, manual Analyze All, optimizer runs, and backfill scripts.  
**Long-term backlog:** Replace yfinance `.BK` close prices with a direct SET data feed guaranteeing ATC settlement.

---

## Fee Decomposition (Phase 3B.10 + hardening)

**Date:** 2026-05-27  
**Problem:** Brokerage fees were stored as a single total in `Transaction.fees` with `taxes=0`. No visibility into components; DR instruments could not have different structures.  
**Decision:** Decompose into `fees = pre-VAT subtotal` (commission + trading + clearing) and `taxes = VAT`. Total is identical (`0.157% × 1.07`), so cash balances don't change.  
**Reasoning:** Decomposition enables per-component transparency, configurable fee profiles per symbol class, and correct DR handling without rewriting accounting logic.  
**Impact:** Old rows have `taxes=0` so `fees + taxes = fees` (unchanged). New rows sum to same total. `period_fees_paid` formula uses `(tx.fees or 0) + (tx.taxes or 0)` for backward compat.

---

## Fee-Inclusive Cost Basis

**Date:** 2026-05-27 (hardening sprint)  
**Problem:** `avg_cost` was computed as `price_per_share` only, excluding brokerage fees. This understated cost basis and overstated realized P/L.  
**Decision:** `avg_cost = net_buy_amount / shares` where `net_buy_amount = gross + all_fees_incl_vat`. Weighted average on additions uses `net_buy_amount`, not raw price.  
**Reasoning:** Institutional-grade accounting convention. Fees are a real cost of acquiring the position; excluding them understates true acquisition cost.  
**Impact:** `avg_cost` values increase by ~0.168%. Historical P/L slightly lower. `POST /admin/recalculate-cost-basis` endpoint repairs historical data.

---

## Position Import Accounting Fix (Phase 3B.9)

**Date:** 2026-05-25  
**Problem:** `INITIAL_POSITION` transactions injected equity into the portfolio without a cash outflow. The snapshot engine treated the full market value as investment gain, distorting return %.  
**Decision:** Classify `INITIAL_POSITION` as a NON-PERFORMANCE CAPITAL INFLOW. Store `imported_asset_value` at current market price in the snapshot. Subtract from the performance formula.  
**Reasoning:** A user who imports an existing holding they've had for years should not see a 100% return on the import date. The value existed before the portfolio was tracked.  
**Impact:** `add_holding` endpoint now calls `execute_initial_position()` to create a transaction trace. All return, alpha, Sharpe, and attribution calculations exclude imported assets.

---

## Backdated Import Detection (Phase 3B.9 Hotfix)

**Date:** 2026-05-25  
**Problem:** The import-stripping logic used `Transaction.transaction_date` to find INITIAL_POSITION events in the snapshot window. Backdated imports (user supplies original purchase date years ago) escaped the filter.  
**Decision:** All non-performance transaction queries filter by `Transaction.created_at` (physical DB insert time), not `transaction_date`.  
**Reasoning:** `created_at` is always `datetime.utcnow()` at insert time regardless of user-supplied `transaction_date`. It is the authoritative indicator of "when this event was recorded in the system."  
**Impact:** Applies to all queries in `portfolio_snapshots.py`. `transaction_date` remains accurate as the user's reported trade date.

---

## DR Symbol Handling

**Date:** 2026-05 (early architecture)  
**Problem:** DR stocks (e.g. `NVDA01.BK`) are Thai Depository Receipts trading on SET, but yfinance only knows the base ticker (`NVDA`).  
**Decision:** `normalize_dr_symbol()` strips the two-digit suffix for yfinance calls. Original symbol kept in DB for display. Pattern `^[A-Z]+\d{2}\.BK$` identifies DRs.  
**Reasoning:** Keeps all Thai SET symbols consistent with `.BK` suffix for UI while enabling correct yfinance data retrieval.  
**Impact:** Must call `normalize_dr_symbol(symbol)` before any `ticker.info` or `fetch_info` call in agents. Sector resolution for DRs uses FA cache (base ticker data).

---

## Authorized Exception Semantics (Phase 3B.6)

**Date:** 2026-05-25  
**Problem:** L2/L3 AI agents and the Consensus Engine were treating "Turnover Relaxation Active" as a failure condition and escalating to REVIEW even when the relaxation was intentional and authorized.  
**Decision:** Inject explicit "AUTHORIZED EXCEPTION SEMANTICS" into `_t1_note` (shared across all 3 layer prompts) classifying authorized states vs dangerous failure states. Add governance penalty exemption for turnover flags when Tier 1 relaxation is active.  
**Reasoning:** AI agents lack the context to distinguish an intentional policy relaxation from a genuine violation. The classification must be injected explicitly.  
**Impact:** `TURNOVER_BREACH` in UI displays as blue/informational rather than red/error. Governance score not penalized for authorized expansions.

---

## Constraint Resolution Hierarchy (Phase 3B.5)

**Date:** 2026-05-25  
**Problem:** Multiple overlapping constraint sources (user settings, regime policy, emergency limits, system safety) could contradict each other with no deterministic resolution.  
**Decision:** 4-source merge with `effective = min(A, B, C, D)` for upper bounds. Resolver runs before policy engine; policy engine applies confidence discount on top.  
**Reasoning:** Clean separation: resolver produces "pre-discount" constraints; policy engine handles dynamic adjustment. Audit trail per-constraint shows binding source.  
**Impact:** `emergency_limit` stored as `float | None` (not `float("inf")`) for JSON serializability. `_norm_sector()` duplicated in `policy_engine.py` to avoid circular import.

---

## Policy Engine Confidence Discount (Phase 3B.4)

**Date:** 2026-05-24  
**Problem:** The optimizer was equally aggressive regardless of regime confidence or consensus strength.  
**Decision:** Dynamic confidence discount (0–1) based on regime confidence (50%), stability (35%), consensus strength (15%). Discount tightens constraints proportionally.  
**Reasoning:** Low-confidence regime readings should yield more conservative portfolios. The discount gives a continuous rather than binary risk adjustment.  
**Impact:** At low confidence: cash floor +8%, max position −15%, turnover ceiling reduced, aggressiveness reduced.

---

## Persona Per-Portfolio Design (Phase 3B.2)

**Date:** 2026-05-23  
**Problem:** A user may want different investment philosophies for different portfolios (e.g. aggressive growth in one, dividend income in another).  
**Decision:** `Portfolio.strategy_persona` column (TEXT, default BALANCED) — one persona per portfolio, not workspace-level.  
**Reasoning:** Per-portfolio is more flexible and requires no breaking schema change for existing portfolios (default BALANCED is neutral).  
**Impact:** DNA computation lightweight — uses `ta_score`, `fa_score`, `pe_ratio`, `roe`, `revenue_growth` already in `scores_map`; no extra yfinance calls.

---

## Shadow Portfolio Design (Phase 3B.7A)

**Date:** 2026-05-25  
**Problem:** No way to measure whether following AI recommendations actually outperforms the user's actual decisions.  
**Decision:** Two shadow types: `STATIC_FROZEN` (frozen at decision time, tracks "what would have happened") and `ACTIVE_MODEL` (refreshed each run, hypothetical 100%-compliant portfolio). Only one ACTIVE_MODEL shadow per portfolio.  
**Reasoning:** STATIC_FROZEN answers "did that recommendation have merit?"; ACTIVE_MODEL answers "what would a fully AI-compliant portfolio look like today?".  
**Impact:** Attribution and calibration depend on accumulated history. BHB sector decomposition is a structural stub awaiting per-sector benchmark data.

---

## Concurrent Watchlist Analysis

**Date:** 2026-05 (optimization sprint)  
**Problem:** Sequential analysis with sleep delays: ~4 minutes for 68 stocks.  
**Decision:** `asyncio.gather()` with `Semaphore(10)` concurrency cap and 10s per-stock timeout.  
**Reasoning:** AI provider rate limits require concurrency cap; 10s timeout prevents one slow AI call from blocking the entire batch.  
**Impact:** ~32 seconds for 68 stocks. Timed-out stocks fall back to deterministic signal; `AnalysisCache` not written for fallbacks (retry on next run).

---

## `datetime.utcnow()` Convention

**Date:** Throughout project  
**Problem:** `datetime.now(timezone.utc)` appends `+00:00Z` which is invalid ISO format.  
**Decision:** Use `datetime.utcnow().isoformat() + "Z"` for all ISO strings.  
**Impact:** All timestamp fields in API responses are consistent ISO-8601.

---

## PostgreSQL GroupBy Fix

**Date:** 2026-05  
**Problem:** PostgreSQL requires `ORDER BY` to use `func.sum()` not bare column in aggregation queries.  
**Decision:** Use `func.sum()` in ORDER BY clause for model cost report query.  
**Impact:** Production PostgreSQL deployment works correctly; SQLite dev environment was unaffected.

---

## Portfolio Metrics Engine Consolidation

**Date:** 2026-06-30  
**Problem:** `portfolio_rebuilder.py`, `portfolio_snapshots.py`, and `snapshot_return_recovery.py` each independently implemented the same nine period-return fields, with subtle, undocumented divergences (window field, cash-flow formula, signed-vs-absolute quantity correction, duplicate-import handling). `docs/PORTFOLIO_CALCULATION_RULES.md` documented these divergences and recommended canonical answers but made no code changes.  
**Decision:** Extract one pure function, `services/portfolio_metrics.py::compute_period_metrics()`, and migrate all three engines (plus `snapshot_repair.py`, which inherits the fix via delegation) to call it instead of duplicating the formulas. ADR-001 (Transaction ledger is the single source of truth), ADR-002 (Metrics never compensate for ledger corruption), ADR-003 (`transaction_date` governs replay-order; `created_at` governs window-membership in incrementally-built engines only — see below), ADR-004 (exactly one implementation) were ratified to guide this.  
**Reasoning:** ADR-004 directly states the goal — one formula, three engines, identical output for any given ledger and window. Per-engine duplication was the root cause of every divergence found during the architecture review.  
**Impact:** `portfolio_rebuilder.py` and `portfolio_snapshots.py` were mechanically migrated with zero behavior change (verified by their full existing test suites passing unchanged). `snapshot_return_recovery.py`'s migration intentionally changed two formulas — see the next two entries. New regression suite: `test_portfolio_metrics.py` (pure unit tests) and `test_portfolio_metrics_parity.py` (cross-engine parity + the ADR-003 backdated-transaction case).

---

## External Cash Flow Formula Confirmed Canonical (Implementation A)

**Date:** 2026-06-30  
**Problem:** `portfolio_rebuilder.py`/`portfolio_snapshots.py` summed ledger DEPOSIT/WITHDRAW/INITIAL_CASH events directly ("Implementation A"); `snapshot_return_recovery.py` instead derived the figure from the change in `Portfolio.cash_balance` minus BUY/SELL cash movement ("Implementation B"). `PORTFOLIO_CALCULATION_RULES.md` Section 4 originally recommended B as "self-validating against the authority column."  
**Decision:** Implementation A (ledger-derived) is canonical, reversing the original recommendation.  
**Reasoning:** A follow-up architecture review found B's "self-validation" property inverts Design Principle 1 — it treats `Portfolio.cash_balance` (a derived, disposable column per the ledger-is-truth principle) as authoritative input to the return formula, rather than as something checked against the ledger (which is exactly what `ledger_validator.py` CHECK 8, `CASH_MISMATCH`, already does). Worked examples showed A fails loud on `cash_balance` drift (an obviously-wrong return number, easy to catch) while B fails quiet (silently absorbs the drift into a plausible-looking "clean" return, hiding the underlying bug). A real production case — phantom DEPOSIT + duplicate INITIAL_POSITION on a specific portfolio/date — confirmed this concretely and became the regression test for the fix.  
**Impact:** `snapshot_return_recovery.py` migrated from B to A. Only affects portfolios whose ledger and `cash_balance` have ever drifted apart; forward-only (no backfill of already-persisted snapshots). Test: `test_phantom_deposit_and_initial_position_surface_as_anomalous_return` in `test_snapshot_return_recovery.py`.

---

## Signed Manual Adjustment Value Fix

**Date:** 2026-06-30  
**Problem:** `manual_adjustment_value` (the QUANTITY_CORRECTION strip in the return formula) used `abs(qty_correction_delta)` in `portfolio_rebuilder.py` and `portfolio_snapshots.py`, but the correct, signed formula in `snapshot_return_recovery.py`. A downward correction therefore double-subtracted in two of the three engines: once for the real NAV drop, once again for a wrongly-positive strip in the same direction, fabricating a loss of roughly 2× the correction's market value.  
**Decision:** `manual_adjustment_value = qty_correction_delta × price` (signed), matching `snapshot_return_recovery.py`'s original formula, in the shared `compute_period_metrics()`.  
**Reasoning:** This is a correctness bug, not a policy choice — an unsigned strip cannot make a pure data-entry correction net to zero effect on return, which Design Principle 2/3 require.  
**Impact:** Changes historical numbers only for a portfolio with a downward `QUANTITY_CORRECTION` that is rebuilt/recomputed after this fix; forward-only, no backfill. Test: `test_quantity_correction_downward_strips_negative_amount` in `test_portfolio_metrics.py`.

---

## INITIAL_POSITION Dedup Removed from Snapshot Engines

**Date:** 2026-06-30  
**Problem:** `snapshot_return_recovery.py` skipped an `INITIAL_POSITION` transaction's contribution to `imported_asset_value` when the symbol already appeared in the previous snapshot's holdings with equal-or-more shares (a defensive heuristic against duplicate imports). `portfolio_rebuilder.py` and `portfolio_snapshots.py` had no such dedup, creating a three-way inconsistency.  
**Decision:** Remove the dedup heuristic. `compute_period_metrics()` strips every `INITIAL_POSITION` transaction in the window at face value, unconditionally.  
**Reasoning:** Duplicate-import detection and correction is a ledger-quality concern with a dedicated owner — `ledger_validator.py` (detection) and `ledger_repair_plan.py` (Phase 6.7E, already shipped, auto-detects and repairs `DUP_INITIAL_POSITION`). Per ADR-002, the metrics layer should not silently compensate for ledger defects that a purpose-built repair pipeline already exists to fix upstream.  
**Impact:** A portfolio with an un-repaired duplicate `INITIAL_POSITION` will show an inflated `imported_asset_value` (and distorted `investment_return_pct`) after this change, where previously the dedup heuristic masked it. Run `validate_ledger` / `generate_repair_plan` on any portfolio that predates this change before trusting recomputed numbers.

---

## Time Attribution Scope (ADR-003 Resolution)

**Date:** 2026-06-30  
**Problem:** ADR-003 states "`transaction_date` governs investment performance attribution; `created_at` must never affect it." Taken literally, this would require switching `portfolio_snapshots.py` and `snapshot_return_recovery.py`'s window-membership logic from `created_at` to `transaction_date` — but `created_at`-windowing in those two engines is the documented fix for the Phase 3B.9 "Backdated Import Detection" bug (a backdated transaction would become invisible to every window check under `transaction_date`-only attribution in an incrementally-built snapshot series, leaking its value into NAV as an undetected phantom gain).  
**Decision:** ADR-003 is scoped to portfolio-state/replay-order questions (cost basis, holdings-as-of-date, chronological sort) — the only thing `compute_period_metrics()` itself ever uses a date for (it reads neither field; callers pre-filter). Window-membership logic is unchanged and remains each engine's own responsibility: `created_at` for the two incrementally-built engines, `transaction_date` for the full rebuild.  
**Reasoning:** Applying ADR-003 literally to window membership would reintroduce a previously-fixed, documented production bug, directly conflicting with this refactor's "business behaviour must remain unchanged" constraint. This decision was confirmed explicitly with the task requester before implementation began.  
**Impact:** No behavior change to window membership in any engine. Regression test: `test_backdated_transaction_attributed_per_engine_own_window_field` in `test_portfolio_metrics_parity.py`, demonstrating each engine correctly uses its own window field for the same backdated transaction.

---

## 2026-07-03

### Adaptive Policy Engine Silent Failure

Problem

During UX.2D/E/L refactor,
`pd_with_weights` was removed while `compute_policy()` still depended on it.

Impact

- Policy Engine disabled
- Persona ignored
- Confidence adjustment disabled
- Alignment scoring disabled

Lessons Learned

- Never silently swallow architectural failures.
- Critical subsystems must expose health status.
- Integration tests are mandatory for pipeline components.

---

## BH/CENTEL Funding Confusion — Optimizer Philosophy Introduced

**Date:** 2026-07-06
**Problem:** With 120k cash on hand, the optimizer recommended BUY CENTEL 30k and REDUCE BH 95k, leaving 186k cash idle. Every number was arithmetically correct, but the plan was not: BH was sold without necessity, fees were paid without purpose, and there was no answer available to "why did it sell BH?" Root cause was architectural, not a math bug — the system had no explicit distinction between a **Belief** ("BH should eventually be a smaller share of this portfolio") and an **Execution** decision ("this trade is worth making today"), so a slow-moving allocation preference was rendered as an urgent, unexplained trade. The optimizer also had no concept of **Execution Role** (e.g. Funding Source) separate from a trade's **Reason** (e.g. Portfolio Improvement), so a sale justified on its own merits was misread as cash-raising for a purchase that existing cash already covered three times over.
**Decision:** Adopt `docs/OPTIMIZER_PHILOSOPHY.md` as the constitutional design document for the optimizer, execution planning, and AI evaluation layers. It establishes the hierarchical objective (Capital Preservation → Policy Compliance → Recommendation Integrity → Execution Practicality → Expected Improvement → Turnover Efficiency → Idle-Cash Efficiency), the Belief/Execution Plan separation, the Reason/Execution Role distinction for every trade, and the "guilty until proven necessary" default for trading activity.
**Reasoning:** A weighted-score optimizer can produce this exact failure and still report a good score, because expected improvement and unexplainable turnover are fungible under a price list. A lexicographic hierarchy cannot make this mistake: the BH sale served no tier (not preservation, not compliance, not required for practicality) and its improvement value was marginal, so it should never have shipped. Writing this down as philosophy — not just fixing the one incident — was necessary because the underlying gap (conflating Belief with Execution, and Reason with Role) could otherwise resurface anywhere a future feature touches trade selection or funding logic.
**Impact:** `docs/OPTIMIZER_PHILOSOPHY.md` is now required reading before modifying optimizer, execution, policy, or AI evaluation logic (see `CLAUDE.md`). `services/execution_plan.py` and `services/funding_source_analysis.py` (Phase UX.2E/UX.2L) already implement the Reason/Execution Role split described here — this decision formalizes the philosophy retroactively for the design they follow, and binds all future optimizer work to it going forward.

---

## Execution Optimization Layer (§7 implemented)

**Date:** 2026-07-06
**Problem:** §7 of `OPTIMIZER_PHILOSOPHY.md` described the Execution Optimization stage as the fix for the BH/CENTEL incident, but no code implemented it: both execution-plan surfaces — the optimizer page's `ExecutionPlanCard` (via `frontend/lib/executionPlan.ts::deriveExecutionPlan`) and the Decision Workspace's `build_execution_plan()` — summed every SELL/REDUCE-flagged holding's full release into "cash released" unconditionally, regardless of whether a buy actually needed the cash. The exact founding-example arithmetic (120k cash, 30k need, 95k REDUCE ships anyway, 186k idle) was live in both surfaces.
**Decision:** Added `backend/services/optimizer/execution_optimizer.py` as a new, pure, deterministic post-processing stage inserted between the existing action-summary/noise-filter response-time views and display. It assigns three independent axes to every candidate SELL/REDUCE trade — **Reason** (durable belief-side: Mandatory Risk Reduction / Policy Enforcement / Portfolio Improvement, derived from the already-chosen `action` plus `PolicyEnvelope.violations`, no new AI output), **Necessity** (a pure function of Reason: NECESSARY trades ship in full unconditionally; DISCRETIONARY trades are deferrable), and **Execution Role + Execution State** (STANDALONE/FUNDING_SOURCE/NOT_NEEDED_TODAY × FULL/SCALED/DEFERRED — what job a trade does in *today's* plan and how much of its own recommended size actually executes). The funding-gap algorithm sorts discretionary candidates ascending by their own full recommended size and walks them greedily, scaling at most one "boundary" candidate down to exactly close the gap — least-distortion-from-its-own-plan, not "SELL before REDUCE" or "largest first." Deterministic tie-break: full-release ascending → REDUCE preferred over SELL when scaling → symbol ascending.
**Reasoning:** Necessity must never be conflated with Execution Role (a trade can be necessary without serving a funding job, and only discretionary trades can ever be scaled — a Mandatory Risk exit is never partially executed just because today's cash need is small). Ordering candidates by raw category (SELL/REDUCE) or size-descending, as an early draft of this design did, would partially execute a large intended-full-exit position to cover a small gap — a bigger, less explainable distortion from the Belief's own plan than fully executing a small, already-well-fitting candidate instead. The gap between a trade's `full_recommended_amount` and its `executed_amount` is deliberately not routed through `UserExecutionDecision.PARTIAL_EXECUTION` (that field is reserved for a human's later action on top of the already-optimized plan) — it feeds Execution Quality metrics (§12: Trade Necessity, Funding Efficiency) and is invisible to Belief Quality grading, which continues to compare against the `ACTIVE_MODEL` shadow's full-compliance simulation, untouched.
**Impact:** `main.py`'s `/analyze/optimizer` and `/optimizer/history/{id}` responses gain an additive `execution_optimization` key (same response-time-view pattern as `action_summary`, backward compatible — absent on old unbackfilled rows). `services/funding_source_analysis.py::build_funding_sources()` now delegates its candidate selection to the shared `resolve_funding_gap()` instead of unconditionally including every flagged holding, and gained a `deferred_sources` field. `services/execution_plan.py::build_execution_plan()` now computes buy deployment before funding (the gap must be known first) and derives `funding_actions`/`deferred_funding_actions` from one shared resolution instead of two redundant computations. `RecommendationSnapshot` and `target_allocations` are never touched — see `test_execution_optimizer.py` for the founding-example regression test plus ordering/tie-break/edge-case coverage.

### Follow-up fix: position-level policy breach was not detected (2026-07-06)

**Problem:** A design review surfaced that `classify_reason()` only pattern-matched `PolicyEnvelope.violations` strings against the trade's **sector** (`SECTOR_BREACH: {sector}...`), never against its **symbol**. `policy_engine._detect_violations()` also emits a position-level shape, `CONCENTRATION_BREACH: {symbol} at {w}% exceeds {limit}% single-position policy limit`, which never matched. A REDUCE enforcing a live single-position breach was silently classified as discretionary `PORTFOLIO_IMPROVEMENT` instead of `POLICY_ENFORCEMENT` — meaning it could be deferred to "Not Executing Today" whenever no funding gap happened to exist, even though the position limit itself was actively being violated.
**Decision:** `classify_reason()` now takes the trade's `symbol` as an explicit parameter and matches a `BREACH` violation line against either the symbol or the sector. Minimal, additive change — no new inputs, no architectural change; still pure string-matching against an already-computed violations list (belief-free per §7).
**Reasoning:** Necessity is a pure function of Reason (§9); a Policy Enforcement trade must ship regardless of cash position. Missing one of the two breach shapes the policy engine actually emits meant a real Priority-2 constraint violation could be masked as a deferrable Priority-5 discretionary trade — the opposite of what §2's objective hierarchy requires.
**Impact:** `execution_optimizer.py::classify_reason(symbol, action, sector, violations)` — signature change, one call site (`resolve_funding_gap`) updated. Two new regression tests: a live `CONCENTRATION_BREACH` on the trade's own symbol now classifies as `POLICY_ENFORCEMENT`/`NECESSARY` and ships in full even with `funding_gap == 0`; an unrelated symbol's breach still does not.

---

## Strategist (L1) Explainability — "Stability Review" summary

**Date:** 2026-07-06
**Problem:** A quiet L1 (few or zero swaps — intended behavior per its "quality over quantity" conviction bar, see the L1/L2 architecture review the same day) reads to users as "the AI did very little," not "the AI actively reviewed the portfolio and found nothing worth disturbing." L1 had no field explaining its own reasoning — `Layer1Result.summary` existed in the schema but was never populated (only L2 wrote to its own `summary`, from `portfolio_assessment`).
**Decision:** Prompt-only change to `_layer1_prompt()` — added a required `summary` field: exactly 2 sentences, written in natural investment-strategist voice (what was evaluated, then what cleared the conviction bar and why the rest didn't), with an explicit instruction to vary phrasing run-to-run rather than reuse a fixed template. Also added the same output-budget priority-order fallback L2 already had (`_layer2_prompt`), so a token-constrained response drops `sector_flags`/`top_buys` before it drops `summary` or the actual `swaps`/`priority` decision. Token budget bumped 400→550 to fit the new field. Frontend: `Layer1Section`'s subtitle changed from `"Recommendations — priority: X"` to a static `"Stability Review"`, added a `"Recommendation"`/`"Recommendations"` label above the swap/allocation table, renamed the inline `"Top buys:"` label to a `"Top Watchlist"` section header, and the empty-state string changed from `"No swap proposals from Strategist."` to `"No changes met the conviction bar this cycle."`.
**Reasoning:** None of L1's decision surface changed — same conviction thresholds, same max-3-swaps/max-5-top_buys caps, same `no_action` gate, same consensus math (`_consensus_engine`'s `buy_overlap`/`strategist_alignment_score` are untouched). This is purely narrating a decision L1 was already making, in a render slot (`layer.summary` → orange callout) that already existed and was already wired through `RecommendationSnapshot` persistence — just never populated for L1. Mirrors §8's "confident silence" principle (a system that explains *why* it did nothing builds more trust than one that says nothing) applied one layer up, to the Strategist itself rather than the Execution Plan.
**Impact:** `agents/optimizer.py::_layer1_prompt()` prompt text only — no signature change, no new parameters. `frontend/app/optimizer/page.tsx`'s `Layer1Section`/`SwapTable` — copy and layout only, same props, same data. No changes to `_consensus_engine`, `execution_optimizer.py`, or any threshold/scoring logic.

---

## Alembic Migration Graph Corruption — Duplicate Revision ID + Unmerged Branch

**Date:** 2026-07-06
**Problem:** While implementing Milestone M0 of the AI Evaluation phase, `alembic current` failed immediately with `Cycle is detected in revisions` against the live dev Postgres DB. Root cause, found by inspecting the DB directly: `migrations/versions/a1b2c3d4e5f6_add_ledger_repairs.py` (Phase 6.7A, commit `cb3726a`) reused revision id `a1b2c3d4e5f6`, already taken by the much earlier `add_latency_columns.py` (commit `ea7e390`), and its `down_revision` pointed at `z0a1b2c3d4e5` in parallel with `a1b3c5d7e9f0_add_override_structured_fields.py` (UX.2D, commit `c45dc8a`) — an unmerged branch from the same parent. Alembic has been unable to load this script directory since Phase 6.7A shipped. The live DB's `alembic_version` was stamped at `a1b3c5d7e9f0`, and the `ledger_repairs` table already existed with all its columns but was missing 2 of its 6 intended indexes (`ix_ledger_repairs_portfolio_is_active` and the partial-unique `uq_ledger_repairs_active_per_tx_type`) plus one index (`ix_ledger_repairs_id`) the migration never defines — conclusive evidence the table was created via `Base.metadata.create_all()` (an ORM side effect of editing `models/database.py` on this always-live dev box), not via `alembic upgrade`, silently working around the broken graph instead of fixing it.
**Decision:** Renamed the colliding file's revision id to a unique `b4c6d8e0f2a4` and rebased its `down_revision` onto the true current head (`a1b3c5d7e9f0`), restoring a single linear chain. Added the two missing indexes to the live DB directly (plain `CREATE INDEX`, no `IF NOT EXISTS` — see next entry) to match what the migration would have produced, then `alembic stamp b4c6d8e0f2a4` to reconcile bookkeeping without re-running `create_table` against a table that already existed.
**Reasoning:** Building M0's own migration on top of a graph that cannot even be loaded was not possible, and silently routing around it (a third out-of-band `create_all()`) would have repeated the exact failure mode being fixed. Rebasing onto the true head rather than introducing an Alembic merge revision was preferred because it matches both chronological reality (ledger_repairs landed after UX.2D) and DB reality (UX.2D was the last revision actually applied through Alembic) with a plain, auditable chain — no new merge-commit-style node for future readers to puzzle over.
**Impact:** `migrations/versions/b4c6d8e0f2a4_add_ledger_repairs.py` (renamed from `a1b2c3d4e5f6_add_ledger_repairs.py`, content and table shape unchanged) is now the sole head prior to M0's own migration. `alembic heads`/`alembic current` resolve cleanly. No `Transaction`/ledger data was touched — only DDL (two `CREATE INDEX` statements) and the `alembic_version` bookkeeping row.

---

## Live Dev Postgres Is 9.2 (EOL, pre-9.5) — No `IF NOT EXISTS` on DDL

**Date:** 2026-07-06
**Problem:** While reconciling the migration graph above, `CREATE INDEX IF NOT EXISTS ...` raised a syntax error against the dev DB. `SELECT version()` confirmed the server is PostgreSQL 9.2.18 (released 2012, EOL since 2017); `IF NOT EXISTS` for indexes/columns was only added in 9.5.
**Decision:** No behavior change to the running system — this is a documentation-only entry. Any future migration or raw-SQL fix-up against this DB must avoid 9.5+-only syntax (`CREATE INDEX/ADD COLUMN IF NOT EXISTS`, etc.) and use existence checks in application code instead, exactly as the existing 30+ migrations already do (none of them use `IF NOT EXISTS`).
**Reasoning:** Recording this now (rather than letting the next migration author rediscover it the hard way) is the cheapest fix available — the alternative, upgrading the dev Postgres instance, is out of scope for the AI Evaluation phase and was not requested.
**Impact:** No code changed. Future Alembic authors and this repo's DECISION_LOG are now the record of this constraint; `docs/AI_EVALUATION_IMPLEMENTATION_PLAN.md`'s M0 migration was written 9.2-compatible from the start.

---

## AI Evaluation M0 — Groundwork: Schema, Config, Route Relocation

**Date:** 2026-07-06
**Problem:** `docs/AI_EVALUATION_IMPLEMENTATION_PLAN.md` §3 left three Planning Decisions (P1, P3, P5) to be confirmed at implementation time rather than re-litigated mid-build.
**Decision:**
- **P1 (route conflict):** The Evaluation hub takes the `/ai-analytics` root; the pre-existing AI operational telemetry page (cost/latency/tokens/reliability — not an evaluation concern) moved intact to `/ai-analytics/system`. The root is a minimal placeholder linking to System until Milestone M4 ships the real hub.
- **P3 (grade persistence):** Added `recommendation_grades` — append-only, unique on `(recommendation_snapshot_id, grade_kind)`, no ORM/service writes UPDATE it.
- **P5 (decision→transaction linkage):** Added nullable `transactions.execution_decision_id`, metadata-only. Verified by running the full ledger toolchain suites (`test_ledger_validator*`, `test_ledger_repair*`, `test_portfolio_rebuilder`, `test_verify_snapshots` — 293 tests) unchanged with the column present, and confirmed the canonicalizer/rebuilder/validators do not reference it.
- Also shipped: `user_execution_decisions.is_system_generated` (for P4's future EXPIRED writer, M1), the `evaluation_settings` config key (P7) via `GET/PATCH /settings/evaluation`, and the `services/evaluation/` package skeleton (no logic yet).
**Reasoning:** Per the plan's Working Agreement, resolving P1/P3/P5 now — rather than leaving them implicit — lets M1–M3 build against a stable schema and route without re-deciding foundational shape mid-milestone.
**Impact:** `models/database.py` (`RecommendationGrade` model + 2 columns), `migrations/versions/c5d7e9f1a3b5_add_recommendation_grades.py`, `main.py` (`/settings/evaluation`), `services/evaluation/__init__.py`, `frontend/app/ai-analytics/{page.tsx,system/page.tsx}`. Full backend suite run before/after (baseline via `git stash`): 49 failed/724 passed/32 skipped in both cases, identical failing tests — no regressions. Optimizer, policy, and execution-optimizer code untouched. M1 (horizon grading engine) is next.

---

## AI Evaluation M1 — Horizon Grading Engine

**Date:** 2026-07-06
**Problem:** `docs/AI_EVALUATION_IMPLEMENTATION_PLAN.md` §5 M1 needed three cooperating pieces built on M0's schema: a per-recommendation counterfactual (P2), the grading arithmetic that reads it (P3), and EXPIRED semantics for undecided snapshots (P4) — none of which exist yet.
**Decision:**
- **P2 (recommendation-level counterfactual):** `services/decision_memory/shadow_tracker.py::create_recommendation_shadow()` — a third use of `shadow_type="STATIC_FROZEN"`, keyed to the recommendation itself (`execution_decision_id=NULL`) rather than to a human decision, so every optimizer run gets a return series from day 0 regardless of what the user does. Wired into the existing post-optimizer background thread (`main.py`, beside the ACTIVE_MODEL shadow at line ~2501). Idempotent (one shadow per `recommendation_snapshot_id`); when called against a historical snapshot (backfill path) it also replays the shadow's full daily valuation from stored `PortfolioSnapshot` prices, reusing `repair_shadow_portfolios()`'s existing `_snapshot_price_history`/`_rebuild_shadow_snapshots` routine rather than re-deriving that math.
- **P3 (horizon grading):** `services/evaluation/horizon_grader.py::grade_due_recommendations()` — for every snapshot whose age has reached a configured horizon (7/30/90/180 days by default, `evaluation_settings`) and lacks that grade row, reads the recommendation shadow's already-persisted `ShadowPortfolioSnapshot` nearest the horizon date for `return_pct`/`benchmark_return_pct`/`alpha` (zero re-derivation), computes `max_drawdown_pct` via the existing `attribution_engine.compute_max_drawdown()`, and scores directional correctness of each BUY/ACCUMULATE/SELL/REDUCE call against the shadow's own persisted horizon-date prices. Deactivates the shadow once the largest configured horizon is graded, bounding the daily valuation job. Missing shadow / stale valuation (gap > 5 calendar days from the target date) / write failure all skip-with-reason and retry next run — never raise, never guess.
- **P4 (EXPIRED semantics):** `services/evaluation/expired_writer.py::write_expired_decisions()` — an undecided snapshot becomes an `is_system_generated=True` `UserExecutionDecision(decision="EXPIRED")` row when superseded (a newer sibling snapshot for the same portfolio has any decision, walked newest-to-oldest so same-run cascades work) or aged out (≥ `evaluation_settings.expiry_days`, default 14), superseded taking priority when both are true.
- Both scheduler jobs are appended to the 17:45 ICT daily chain (`snapshot_scheduler.py`), after `value_all_active_shadows`, EXPIRED writer first so a snapshot that ages out today is gradable as such starting today.
- **Backfill:** `python manage.py backfill_recommendation_grades --all|--portfolio ID` — one-shot CLI (mirrors `verify_snapshots` conventions) that creates missing recommendation shadows (with historical replay) and grades every now-mature horizon, so the Evaluation phase does not launch empty for existing users. Idempotent by construction (shadow creation and grading are both create-if-missing).
**Reasoning:** Reusing the shadow's own persisted daily valuation (rather than a fresh price lookup at grading time) keeps grading and shadow valuation from ever disagreeing about what a recommendation was "worth" on a given day — a second source of truth for the same number was the exact anti-pattern PLAN §4.6 rules out. Cascading EXPIRED newest-to-oldest in one pass avoids a multi-day lag for chains of ignored recommendations.
**Impact:** `services/decision_memory/shadow_tracker.py` (+`create_recommendation_shadow`), `services/evaluation/{horizon_grader,expired_writer}.py` (new), `snapshot_scheduler.py`, `manage.py` (+`backfill_recommendation_grades`), `models/database.py` (`is_system_generated`, used here for the first time). 17 new tests in `tests/test_horizon_grader.py`, all passing. M2 (plan grading + execution analysis) is next.

---

## AI Evaluation M2 — Plan Grading & Execution Analysis

**Date:** 2026-07-06
**Problem:** `docs/AI_EVALUATION_IMPLEMENTATION_PLAN.md` §5 M2 needed a day-0 plan-quality composite (G4) and a plan-vs-actual execution comparison (half of G5) — both scored deterministically off data the pipeline already produces, without touching the optimizer or execution_optimizer.py.
**Decision:**
- **Plan grade:** `services/evaluation/plan_grader.py::compute_plan_grade()` — a 0-100 composite over four documented, weighted sub-scores: **necessity** (30%, share of SELL/REDUCE candidates that are Required-tier or actively funding today), **funding efficiency** (30%, THE BH-INCIDENT METRIC — of the total amount discretionary candidates proposed to release, what fraction was actually needed to close the funding gap; a REDUCE proposing far more than the gap requires scores near the floor even though execution_optimizer.py already defers the excess), **turnover proportionality** (20%, reads the already-computed `TURNOVER_BREACH` violation_detail, no new turnover math), **explanation completeness** (20%, every candidate trade carries a non-empty reason/necessity/execution_role/execution_state/note, or the no-trade case carries a portfolio_assessment/no_action_summary). Re-derives the plan via the existing `optimize_execution()` on stored `target_allocations`/`cash_balance`/`active_policy.violations` — same inputs, same grade, always (asserted in tests). `grade_pending_plans()` persists `grade_kind="PLAN"` rows from the post-optimizer background thread (no maturity wait needed) and via the M1 backfill CLI (extended, not duplicated).
- **Execution analysis:** `services/evaluation/execution_analyzer.py::compute_execution_analysis()` — a pure function comparing the re-derived plan against `Transaction` rows linked via `execution_decision_id` (P5): **timing** delta (recommendation-date price vs. share-weighted fill price), **size** delta (planned vs. executed amount), **funding fidelity** (planned FUNDING_SOURCE trades vs. actual linked sells), **completeness** (fraction of the plan with a linked transaction). A decision with zero linked transactions returns `status="unavailable"`, `score=None` — never a fabricated number; partial matches renormalize the composite over only the measurable components and mark `status="partial"`. No DB writes — a read-only comparison, left for M3 to expose via `GET …/execution/{decision_id}`.
- **Linkage write-path (P5):** `execute_buy()`/`execute_sell()` (`services/portfolio_transactions.py`) gained an optional `execution_decision_id` param, threaded through `TransactionBuyBody`/`TransactionSellBody` in `main.py`. Metadata-only, defaults to `None`, omitted from every existing call site untouched.
**Reasoning:** Funding efficiency deliberately grades the RECOMMENDATION's own proportionality, not just whether execution_optimizer.py caught the excess — a plan that requires heavy correction is a worse plan even when the correction succeeds, which is what separates "plan quality" from "execution-optimization quality" as independent, addressable failure points (PLAN §12, three-lens independence). Execution analysis returning `None` rather than a fabricated composite when nothing is linked follows PLAN §4.7/§4.8 literally — an evaluation number must never imply confidence the data doesn't support.
**Impact:** `services/evaluation/{plan_grader,execution_analyzer}.py` (new), `services/portfolio_transactions.py`, `main.py` (buy/sell bodies + endpoints, `_tx_row`, post-optimizer background PLAN-grading thread), `manage.py` (`backfill_recommendation_grades` now also grades PLAN). No DB schema change — `recommendation_grades`/`transactions.execution_decision_id` already existed from M0. 43 new tests across `tests/test_plan_grader.py` (12), `tests/test_execution_analyzer.py` (8), `tests/test_execution_decision_linkage.py` (3), all passing; the BH-incident fixture (`test_bh_incident_scores_funding_efficiency_at_floor`) scores `funding_efficiency_score == 0.0` exactly as the philosophy predicts. Full ledger toolchain suites (293 tests) re-verified unchanged with the linkage column now actually being populated by real callers (not just present in schema): confirmed via `git stash` A/B comparison that the pre-existing 49-failure/asyncio-ordering baseline is byte-identical before and after this milestone — no regressions. `execution_optimizer.py`/`agents/optimizer.py` untouched. M3 (aggregation APIs + verdict composer) is next.
**Impact:** `services/decision_memory/shadow_tracker.py` (+`create_recommendation_shadow`), new `services/evaluation/horizon_grader.py` and `services/evaluation/expired_writer.py`, `main.py` (background-thread wiring only, no new endpoints), `services/snapshot_scheduler.py` (+2 calls in the existing daily chain), `manage.py` (+`backfill_recommendation_grades` subcommand). 17 new unit tests (`tests/test_horizon_grader.py`, in-memory SQLite against the real ORM models) covering maturity boundaries, append-only idempotency, skip-with-reason paths, deactivation, directional scoring, EXPIRED supersession/aging, and shadow-creation idempotency — all passing. Full ledger toolchain suite: 294/294 passing, untouched. Full backend suite before/after (baseline via `git stash`): identical 49 failed/32 skipped, passed count up by exactly the 17 new tests — no regressions. Optimizer, policy, and execution-optimizer code untouched. M2 (Plan Grading & Execution Analysis) is next.

---

## AI Evaluation M3 — Aggregation APIs & Verdict Composer

**Date:** 2026-07-06
**Problem:** `docs/AI_EVALUATION_IMPLEMENTATION_PLAN.md` §5 M3 needed the read layer the frontend (M4+) will consume: scorecard, recommendations ledger + Report Card, execution ledger + detail, and a deterministic verdict sentence builder (G8) — all computed server-side from M0/M1/M2 data, with server-side min-n gating and honest cold-start payloads (P8).
**Decision:**
- **New endpoints, all under `/analytics/evaluation/*`, portfolio-scoped, read + in-memory aggregation only** (no endpoint triggers grading — that stays in the scheduler): `GET …/scorecard`, `GET …/recommendations` (ledger) + `GET …/recommendations/{snapshot_id}` (Report Card), `GET …/execution` (ledger) + `GET …/execution/{decision_id}` (detail).
- **`services/evaluation/verdict_composer.py`** — the single deterministic TH/EN sentence builder (P6), used by both the scorecard verdict strip and the Report Card verdict. `letter_grade(score, n, min_n)` gates every letter-grade chip server-side (UX D10) — below `min_n_letter_grade` the chip reports `insufficient_evidence`, never a guessed letter. `compose_scorecard_verdict()` covers four branches (ai_ahead / human_ahead / tie / insufficient_evidence) against `evaluation_settings.tie_band_pct`; `compose_report_card_verdict()` degrades to a plan-only sentence when no horizon has matured (UX Rung 1).
- **`services/evaluation/scorecard.py`** — three-lens aggregate. Belief/Execution lenses read `RecommendationGrade` rows (M1/M2) directly — zero new grading math. Outcome lens reuses the existing `attribution_engine.compute_portfolio_attribution()` and `human_vs_ai.compare_human_vs_ai()` (both pre-existing, already-used analytics services) rather than re-deriving return/drawdown/win-rate formulas. Two fields — `implementation_shortfall` (needs `ideal_series.py`, explicitly scoped to M6) and `net_opportunity_cost` (explicitly "a placeholder until M5" per the plan's own M3 section) — ship as `status:"unavailable"` with a reason naming the future milestone, never a fabricated number.
- **`services/evaluation/recommendation_ledger.py`** — the S2 ledger and S3 Report Card. Extracted a shared `plan_grader.read_snapshot_plan_inputs()` helper (refactor, behavior-preserving — `grade_pending_plans()` now calls it too, verified by the unchanged M2 test suite) so the ledger, Report Card, and execution ledger all reconstruct "this snapshot's plan" exactly one way. `HorizonStrip` semantics (`graded` / `maturing` / `pending_grading`) are defined precisely in the module docstring since the UX wireframe's own legend was ambiguous about the maturing/not-due boundary. Rows are `is_counterfactual=True` whenever the recorded decision isn't APPROVED/PARTIAL_EXECUTION — the recommendation-keyed shadow (P2) always exists regardless of the human's decision.
- **`services/evaluation/execution_ledger.py`** — the S4 ledger and S4b detail, built on the existing `execution_analyzer.compute_execution_analysis()` (M2, unchanged). Class-segmented acceptance (UX D5) honestly segments across the three Reasons `execution_optimizer.py` actually assigns (Mandatory Risk Reduction / Policy Enforcement / Portfolio Improvement) — "Optional Rebalancing" never appears as a produced Reason (it's filtered out upstream by the drift-tolerance layer), so a fourth bucket is not fabricated. Acceptance is evaluated at the decision level (APPROVED/PARTIAL_EXECUTION vs not), a documented approximation since the data model doesn't record which individual trade within a PARTIAL_EXECUTION was kept — surfaced via an `acceptance_note` field, never hidden.
- **TypeScript contracts:** `frontend/lib/api.ts` gained full interfaces + typed fetch wrappers for all five new endpoints (no React components, no pages — those are M4).
**Reasoning:** Every M3 module is a read-only aggregator over already-persisted grades and already-existing analytics services (`Reuse Before Create`) — the milestone's entire job is presentation-ready shape, not new arithmetic. Where a genuinely new number would be needed (implementation shortfall, net opportunity cost), the plan itself schedules that work for M5/M6; shipping an honest `unavailable` now rather than a placeholder zero keeps PLAN §4.7/§4.8 intact and gives M4 a real degraded-state to render instead of a number it would have to later un-teach users to trust.
**Impact:** `services/evaluation/{verdict_composer,scorecard,recommendation_ledger,execution_ledger}.py` (new), `services/evaluation/plan_grader.py` (+`read_snapshot_plan_inputs`, extracted from `grade_pending_plans` — non-behavioral refactor), `main.py` (5 new endpoints under `/analytics/evaluation/*`), `frontend/lib/api.ts` (+types and fetch wrappers). No DB schema change. 30 new tests across `tests/test_verdict_composer.py` (11), `tests/test_scorecard.py` (4), `tests/test_recommendation_ledger.py` (7), `tests/test_execution_ledger.py` (6), all passing; combined with M1/M2's 38 (17+12+8+... — see those entries), the `services/evaluation/` suite is 68/68 green. Full backend suite before/after: identical 49 pre-existing failures (same asyncio-ordering fragility documented at M0/M2), 792 passed (up by the 30 new tests plus incidental collection) — no regressions. `tsc --noEmit` clean on the frontend. `execution_optimizer.py`/`agents/optimizer.py` untouched throughout. M4 (frontend hub shell + S1–S3 screens) is next.

## AI Evaluation M4 — Hub Shell, Component Kit, Screens S1–S3

**Date:** 2026-07-06
**Problem:** `docs/AI_EVALUATION_IMPLEMENTATION_PLAN.md` §5 M4 needed the Evaluation hub to become visible: the segmented sub-nav shell, the shared honesty component kit (tri-state HorizonStrip/MaturityChip/CounterfactualValue plus the rest of §6's kit), and the Scorecard/Recommendations-ledger/Report-Card screens consuming the M3 read APIs — with zero metric computation in React (§4.5) and the read-only Evaluation invariant preserved end-to-end.
**Decision:**
- **Route structure — Next.js route group, not a shared layout on `/ai-analytics` itself.** `app/ai-analytics/(hub)/` holds every Evaluation screen behind one `layout.tsx` rendering `EvaluationTabs`; `app/ai-analytics/system/page.tsx` (pre-existing AI ops telemetry, Planning Decision P1) sits as a sibling outside the group so it keeps its own page chrome instead of being force-wrapped in Evaluation's segmented nav. A layout.tsx directly on `app/ai-analytics/` would have wrapped System too, which UX §2.2 explicitly says is a header link, not a 7th segment.
- **Component kit** shipped at `frontend/components/evaluation/`: `VerdictSentence`, `LensGradeChip`, `HorizonStrip`, `MaturityChip`, `SampleSizeChip`, `CounterfactualValue`, `AsOfStamp`, `EvidenceLedger`, `DecisionStatusBadge`, `GapAnnotation`, plus `EvaluationColdStart` (Rung 0) and `ComingSoonScreen` (placeholder chrome only). Every component renders backend-delivered fields verbatim — none derives a letter grade, a gap, or a counterfactual value from other numbers already on the page.
- **S1 Scorecard hero row scope deviation (flagged, not silently absorbed):** the UX wireframe's Row 3 is an indexed Ideal/AI/You sparkline with Gap A and Gap B annotations. `ideal_series.py` (M6) doesn't exist yet, the scorecard API has no time-series field and no Gap B field, and `implementation_shortfall` ships explicitly `unavailable`. Building the literal chart would have required either fabricating a series or computing Gap B (`ai_model_return_pct − actual_return_pct`) client-side — both forbidden by this phase's invariants. M4 instead renders a point-return summary table sourced entirely from `outcome.*`, a `GapAnnotation` for Gap A wired to the real `implementation_shortfall` field (rendering its honest `unavailable` state), and a plain link to the Human vs AI tab for the Gap B question. No chart component was built for S1.
- **S2 filters are display-only.** Decision and Consensus dropdowns filter the already-fetched `rows` array client-side; no value is recomputed and no additional network call is made per filter change. The wireframe's Regime filter was dropped — `RecommendationLedgerRow` carries no regime field to filter on.
- **Placeholder routes for Execution/Human vs AI/Portfolios/Attribution** (`execution/`, `human-vs-ai/`, `portfolios/`, `attribution/` inside the same route group): static `ComingSoonScreen` text naming the milestone that ships each screen, no data fetching, no logic. Built only so the UX-mandated 6-segment sub-nav has no dead links — not an implementation of any deferred screen.
**Reasoning:** The milestone's job is presentation of already-computed M3 payloads, not new arithmetic — every deviation above was a choice between (a) rendering an honest `unavailable`/link-out for a number the backend doesn't yet produce, or (b) fabricating/computing that number in React, which Working Agreement #5 and Architecture Constraint §4.5 forbid regardless of how small the computation looks (e.g. a single subtraction for Gap B). Choosing (a) in every case keeps the "never fabricate" invariant intact through the frontend, not just the backend, and gives M5/M6 clean real estate to fill in rather than numbers the UI would have to un-teach users to trust later.
**Impact:** `frontend/components/evaluation/*.tsx` (12 new components), `frontend/app/ai-analytics/(hub)/{layout,page}.tsx` (S1), `.../recommendations/{page,[id]/page}.tsx` (S2/S3), `.../{execution,human-vs-ai,portfolios,attribution}/page.tsx` (placeholders, new), `frontend/app/ai-analytics/page.tsx` (deleted — superseded by the route group's `page.tsx`). No backend changes, no DB schema change — M3 APIs consumed exactly as shipped. `tsc --noEmit` clean; `next build` succeeds with all 9 new/changed routes resolving correctly (including the `(hub)` route group and the `recommendations/[id]` dynamic segment — no route conflicts). Verified against the live dev backend (portfolio_id=2 real data, portfolio_id=3 genuinely cold) via direct API calls: confirmed payload shapes and every branch (`cold_start`/`partial`/`ok` status, per-lens `cold_start`, `unavailable` execution analysis with populated-but-null symbol deltas, null plan grade, `maturing` horizon cells, REJECTED/EXPIRED/APPROVED decisions, `is_counterfactual` true/false) render as designed. **No interactive browser verification was performed — no browser-automation tool is available in this environment**; this is a gap against the usual "test the feature in a browser" expectation for UI changes, surfaced here rather than silently claimed. M5 (Human vs AI extension, Opportunity Cost engine, S4–S6 screens — replacing the `execution/` and `human-vs-ai/` placeholders) is next.

## AI Evaluation M5 — Human vs AI Scoreboard, Opportunity Cost, Execution/Human-vs-AI Screens (S4–S6)

**Date:** 2026-07-06
**Problem:** `docs/AI_EVALUATION_IMPLEMENTATION_PLAN.md` §5 M5 needed the comparison layer (G6): a grade-sourced Human vs AI scoreboard segmented by trade class and structured override type, a counterfactual Opportunity-Cost engine pricing every divergence from an AI recommendation (including the system's own deferrals), and the S4/S5/S6 screens — while leaving M0–M4 untouched.
**Decision:**
- **M4 polish first:** `/ai-analytics` was already reachable (it lived in the ⚙ ระบบ admin dropdown, correctly repointed to the new Evaluation hub by M0's route relocation) but not on primary navigation. Promoted it into `Navbar.tsx`'s flat `NAV_MAIN` row (label "ประเมินผล AI", prefix-matches the whole `/ai-analytics/*` tree including `/system`) and removed the now-redundant entry from `NAV_ADMIN`. No other nav item touched.
- **S4 Execution required zero new backend.** M3 already shipped `GET /analytics/evaluation/execution` (ledger) and `.../execution/{decision_id}` (detail) with matching TypeScript types — M5's S4/S4b work was purely the two frontend pages (`execution/page.tsx` ledger, `execution/[id]/page.tsx` detail) consuming them, replacing the M4 placeholder.
- **`services/analytics/human_vs_ai.py::compute_scoreboard()` — new function, additive, `compare_human_vs_ai()` untouched.** The plan asked to "extend human_vs_ai.py... verdicts sourced from grade rows (not ad-hoc valuation)" — rewriting the existing ad-hoc-valuation function in place would have risked its three existing consumers (`/analytics/human-vs-ai`, `/analytics/ai-vs-human-timeline`, the optimizer page's AttributionPanel), which Risk R5 explicitly flags. Instead, a new function in the same module reads `RecommendationGrade` H-rows (the same rows S2/S3/S6 already read) so every Evaluation-hub screen agrees on "what would the AI recommendation have returned" — additive, zero regression risk, same file. `is_system_generated` (EXPIRED) decisions are excluded from the scoreboard — S5 is deliberately about human judgment vs AI, not inaction, which belongs to S6 instead. Tie band, trade-class segmentation, and override-type segmentation (UX.2D columns) all apply; a shared `_nearest_graded_horizon()` helper (also used by opportunity_cost.py) is the single place "what's the AI's return for this recommendation" is looked up.
- **`services/evaluation/opportunity_cost.py` — new.** Prices every divergence (REJECTED, PARTIAL_EXECUTION, MANUAL_OVERRIDE, EXPIRED) as `actual_return_pct − recommendation_shadow_return_pct` over the same window, reusing the recommendation-keyed shadow's horizon grade (P2) — no new return math. This is a **decision-level approximation** (documented, same convention as `execution_ledger.py`'s `acceptance_by_class`): the data model doesn't record which individual trade inside a multi-trade recommendation drove the divergence, so pricing is per-decision, not per-symbol.
- **System's-own-deferrals honesty strip ships without a price.** UX S6 asks for a companion strip pricing the system's own `STATE_DEFERRED` trades the same way. This is **not implemented as a priced number** — both the recommendation shadow and the ACTIVE_MODEL shadow track the full *ideal* allocation (including whatever gets deferred today), so neither can isolate "what would have happened had this one deferred trade executed instead." Pricing a single deferred trade would require a per-symbol counterfactual price series that doesn't exist anywhere in the system. Rather than fabricate one, deferrals are reported structurally (symbol, reason, snapshot) with `counterfactual_pricing: "unavailable"` and an explicit reason string — flagged here as an open design question for M6, not silently shipped as a fake number.
- **S6's headline is a plain number, not the wireframe's generated prose sentence.** The UX mock shows "mostly one ignored BUY. Ignoring two SELL calls helped" — composing that requires ranking/narrating individual rows, which is frontend business logic no backend field produces. `net_opportunity_cost_pct` renders plainly; each waterfall row's own backend-authored `note` field carries the row-level explanation instead.
- **`/ai-analytics/opportunity-cost` is a linked sub-screen, not a 7th tab** — reached from within Human vs AI via an explicit link and a `BackBreadcrumb`, per UX §2.3; `EvaluationTabs`' six segments are unchanged.
- **New components:** `ClassSegmentBars` (S4 acceptance-by-class, S5 win-rate-by-class/override-type — the `ClassAcceptanceBars` of UX §6, generalized since both screens need the same "numerator/denominator segmented by label" shape) and `EffectWaterfall` (S6, the UX §6 component — signed horizontal bars, pinned net row, mandatory counterfactual `*` styling since nothing in it is realized money).
- **New endpoints** `GET /analytics/evaluation/human-vs-ai` and `GET /analytics/evaluation/opportunity-cost`, alongside the existing M3 `/analytics/evaluation/*` family, same `as_of`/status conventions.
**Reasoning:** Every new number here traces to an already-recorded `RecommendationGrade` row or an already-existing analytics helper (`_portfolio_return_since`) — no return math was re-derived, and the two places a literal reading of the UX mock would have required either fabricating data (a per-trade deferral price) or writing interpretive prose in React (S6's headline sentence) were resolved by shipping the honest partial instead, consistent with the pattern established at M3/M4.
**Impact:** `backend/services/evaluation/opportunity_cost.py` (new), `backend/services/analytics/human_vs_ai.py` (+`_nearest_graded_horizon`, +`compute_scoreboard`, existing `compare_human_vs_ai` untouched), `backend/main.py` (+2 endpoints), `frontend/lib/api.ts` (+types/fetch wrappers for both), `frontend/components/evaluation/{ClassSegmentBars,EffectWaterfall}.tsx` (new), `frontend/app/ai-analytics/(hub)/execution/{page,[id]/page}.tsx` (S4/S4b, new), `.../human-vs-ai/page.tsx` (S5, replaces M4 placeholder), `.../opportunity-cost/page.tsx` (S6, new), `frontend/components/Navbar.tsx` (nav promotion). No DB schema change. 11 new backend tests (`tests/test_opportunity_cost.py` 5, `tests/test_human_vs_ai_scoreboard.py` 6), all passing; full backend suite re-run with the same pre-existing 49 asyncio-ordering failures as M0–M4 (confirmed unchanged by running the suite with and without the new test files) plus a small number of environment-only crashes in unrelated scratch/network test scripts (`test_pandas.py`, `test_yf.py`, `tests/investigate/`) excluded from the run as out of scope. `tsc --noEmit` clean; `next build` succeeds, all new/changed routes resolve (`/ai-analytics/execution`, `/ai-analytics/execution/[id]`, `/ai-analytics/human-vs-ai`, `/ai-analytics/opportunity-cost`), `/ai-analytics/system` unaffected. Verified against the live dev backend (portfolio_id=2, real data with REJECTED/APPROVED/EXPIRED decisions; portfolio_id=3, genuinely cold): both new endpoints return correctly-shaped `ok`/`cold_start`/`maturing` payloads; no snapshot in this dev DB has yet crossed a graded horizon, so the "graded" branch of the scoreboard/opportunity-cost UI was verified via the new unit tests rather than live data. **No interactive browser verification was performed** (same environment limitation as M4). `execution_optimizer.py`/`agents/optimizer.py` untouched. M6 (Ideal series, attribution waterfall, S7–S8) is next — see open design questions in the completion report re: DecisionActionPanel↔execution_decision_id wiring and system-deferral pricing.