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