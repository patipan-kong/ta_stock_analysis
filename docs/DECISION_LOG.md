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
