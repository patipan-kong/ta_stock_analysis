# Portfolio Calculation Rules
_Canonical business specification for Portfolio Performance Calculation. Source of truth for `portfolio_metrics.py` and every existing/future engine that touches NAV, return, or attribution math._

_Status: **Implemented.** `backend/services/portfolio_metrics.py` is the single shared implementation this document specifies, and `portfolio_rebuilder.py`, `portfolio_snapshots.py`, and `snapshot_return_recovery.py` all delegate to it (ADR-001 through ADR-004, ratified 2026-06-30). Sections 4, 6, and 7's recommendations are implemented as described below. See [Section 12](#12-open-questions) for what remains open (Open Questions #4-#6 — not addressed by this implementation)._

_Companion docs: [ARCH_SPEC.md](ARCH_SPEC.md) (schema + formula reference), [DECISION_LOG.md](DECISION_LOG.md) (why past decisions were made)._

---

## 1. Design Principles

These principles are extracted from the existing engine docstrings (`portfolio_snapshots.py`, `portfolio_rebuilder.py`) — they are not new policy, they are what the codebase already asserts as its philosophy.

1. **The Transaction table is the single source of truth.** Every other number — `Portfolio.cash_balance`, `PortfolioItem.shares/avg_cost`, every `PortfolioSnapshot` column — is a derived view that must be reproducible by replaying transactions. (`portfolio_rebuilder.py:3-4`)
2. **Portfolio performance must represent investment performance, not accounting noise.** A deposit is not a gain. An imported holding is not a windfall. A share-count typo fix is not a trade. If a transaction has no market-risk content, it must have zero effect on `investment_return_pct`.
3. **Accounting events must not become investment return.** Cash movements (`DEPOSIT`/`WITHDRAW`/`INITIAL_CASH`), equity injections (`INITIAL_POSITION`), and balance-sheet corrections (`QUANTITY_CORRECTION`) are capital events, not performance events, and must be excluded from the return numerator.
4. **Historical replay must be deterministic.** Given the same Transaction rows, `rebuild_portfolio()` run twice must produce byte-identical snapshots both times. No wall-clock dependency, no network-call dependency on values that affect arithmetic (only on *fetching* historical prices, which are themselves deterministic per date).
5. **Every engine must produce identical results from the same ledger.** The live incremental engine (`portfolio_snapshots.py`), the full reconstruction engine (`portfolio_rebuilder.py`), and the return-only recalculation engine (`snapshot_return_recovery.py`) are three independent implementations of the same formula. They must agree. **They currently do not** — see [Section 4](#4-external-cash-flow-definition) and [Section 7](#7-quantity-corrections).
6. **Fees are real costs, gains are real gains — neither is stripped.** Only *capital structure* events (money/equity entering or leaving without market risk) are stripped from return. Anything that happened *to* invested capital (price moves, dividends, trading costs, realized P/L) stays in.
7. **Transparency columns must never feed back into the return formula.** `period_realized_pnl`, `period_dividend_income`, and `period_fees_paid` exist so a user can see *why* a return looks the way it does. They are display-only derivatives of values already embedded in NAV — adding or subtracting them again would double-count.

---

## 2. Time Attribution Policy

### The two timestamps

| Field | Meaning | Set by |
|---|---|---|
| `Transaction.transaction_date` | The date the user asserts the trade/event happened. Can be backdated (e.g. importing a position bought years ago). | User input, defaults to `datetime.utcnow()` if omitted |
| `Transaction.created_at` | The moment the row was physically inserted into the database. Always `datetime.utcnow()` at insert time. | `default=datetime.utcnow` — never user-editable |

### Current split (as implemented)

| Concern | Field used | Engine(s) |
|---|---|---|
| Chronological replay order (what was held on day X, cost-basis evolution) | `transaction_date` | `portfolio_rebuilder.py` (Stage 1/2), `transaction_canonicalizer.py` sort key |
| Snapshot window membership for the **live, incrementally-built** snapshot series (which transactions belong in the `prev_snapshot → today` window) | `created_at` | `portfolio_snapshots.py`, `snapshot_return_recovery.py` |
| Snapshot window membership for a **from-scratch full rebuild** | `transaction_date` | `portfolio_rebuilder.py` Stage 3 (`_populate_return_fields`) |

This is **not** an oversight — it is two different questions that happen to look like the same question:

- **"What was the state of the portfolio on date X?"** must use `transaction_date`, because that's the date the user is asserting the event occurred. A full rebuild recomputes the entire snapshot series in one pass with no pre-existing state, so there is no ambiguity to resolve — `transaction_date` alone defines the timeline.
- **"Has this transaction's effect already been baked into a snapshot I've already written?"** must use `created_at`, because the live engine commits one snapshot row per day, incrementally, as time passes. A transaction backdated to a date *before* the last committed snapshot was never visible to that snapshot — it only becomes visible once it is actually inserted. If window membership used `transaction_date` here, a backdated import would fall *before* the window and be silently invisible to the stripping logic forever, while its market value still flows into `total_value` on whatever day a snapshot first picks it up — producing a phantom gain. This exact bug is documented in `DECISION_LOG.md` → "Backdated Import Detection (Phase 3B.9 Hotfix)".

### Worked example

User has live snapshots through 2026-06-14. On 2026-06-15 they import a 1,000-share `SCB.BK` holding bought IRL in 2024, backdating `transaction_date = 2024-01-10`.

- `created_at = 2026-06-15` (today, real insert time)
- `transaction_date = 2024-01-10` (backdated)

**Live engine** (window keyed on `created_at`): the transaction falls inside the `[2026-06-14 end, 2026-06-15 end)` window → correctly classified as `imported_asset_value` on the 2026-06-15 snapshot → zero effect on `investment_return_pct` that day. ✅

**If window were keyed on `transaction_date` in this context**: 2024-01-10 falls years before any window in the existing snapshot series → the transaction is invisible to every window check → the 1,000 shares appear in `equity_value` with no offsetting strip anywhere → the first snapshot after price data exists shows a large phantom `investment_return_pct`. ❌ (the bug Phase 3B.9 Hotfix fixed)

**Full rebuild** (window keyed on `transaction_date`, run from scratch): correctly slots the import into the `2024-01-09 → 2024-01-10` window in the *reconstructed* timeline, since the rebuild has no pre-existing committed snapshots to be blind to. ✅

### Existing detector for divergence

`ledger_validator.py` CHECK 7 (`_check_created_vs_transaction_date_skew`) already flags any transaction where `created_at` and `transaction_date` differ by more than `_DATE_SKEW_WARNING_DAYS = 90` (WARNING) or `_DATE_SKEW_ERROR_DAYS = 365` (ERROR) days, with a finding message explicitly noting "the live snapshot engine uses created_at; the rebuild engine uses transaction_date... A large skew causes these engines to disagree." This check is the canonical, already-implemented acknowledgment of this exact policy split.

### Canonical rule

> Use `transaction_date` for **all portfolio-state / replay-order** questions (cost basis, holdings-as-of-date, chronological sort).
> Use `created_at` for **window-membership** questions in any engine that operates incrementally against a pre-existing snapshot history (live snapshot generation, return recovery, repair).
> A from-scratch full rebuild may use `transaction_date` for both, because it has no pre-existing snapshot history to be blind to — but this is an optimization specific to "no prior state exists," not a different business rule.
> `created_at` must never influence the *amount* of any field (shares, price, P/L) — only whether a transaction is counted *in this window vs. a different one*.

**ADR-003 resolution (2026-06-30):** ADR-003 ("Portfolio performance uses `transaction_date`; `created_at` is audit metadata only and must never affect investment performance attribution") is scoped to exactly the rule above: `transaction_date` governs replay-order/portfolio-state questions, which is the only thing `services/portfolio_metrics.py`'s pure formulas ever read a date from (the module never reads `created_at` at all — see its docstring). Window membership remains each calling engine's own pre-existing responsibility, unchanged: `created_at` for `portfolio_snapshots.py` and `snapshot_return_recovery.py` (preserving the Phase 3B.9 backdated-import fix described above), `transaction_date` for `portfolio_rebuilder.py`. Applying ADR-003 literally to window membership in the two incrementally-built engines would reintroduce the exact bug Phase 3B.9 fixed; this was evaluated and rejected during the `portfolio_metrics.py` implementation. `test_portfolio_metrics_parity.py::test_backdated_transaction_attributed_per_engine_own_window_field` is the regression test for this resolution.

---

## 3. Snapshot Window Definition

```
prev_snapshot (date = D-1)              today's snapshot (date = D)
       │                                         │
       ▼                                         ▼
───────●─────────────────────────────────────────●──────────▶ time
       prev_day_end                          today_end
       = D-1 + 1 day (00:00 of D)            = D + 1 day (00:00 of D+1)
```

### Boundary definition (as implemented in `portfolio_snapshots.py` and `snapshot_return_recovery.py`)

```python
prev_day_end = strptime(prev.snapshot_date, "%Y-%m-%d") + timedelta(days=1)
today_end    = strptime(today,              "%Y-%m-%d") + timedelta(days=1)

window:  prev_day_end <= Transaction.created_at < today_end
```

This is a **half-open interval**: `[prev_day_end, today_end)`.

- **Inclusive lower bound**: a transaction inserted at exactly `00:00:00` on the day *after* the previous snapshot's date is the first moment counted in this window.
- **Exclusive upper bound**: a transaction inserted at exactly `00:00:00` on the day *after* today's date belongs to the **next** window, not this one.
- Equivalently in plain terms: a transaction belongs to "today's window" if it was inserted on any calendar day strictly after `prev.snapshot_date` and up to and including `today`'s calendar day (since `today_end` is midnight starting the *next* day, anything inserted anytime during `today` itself is `< today_end`).

### Rebuilder's boundary (different field, same shape)

```python
window:  prev_date < Transaction.transaction_date <= curr_date     # string date comparison
```

This is also a half-open interval, but on calendar dates rather than full timestamps, and on `transaction_date` not `created_at` (per [Section 2](#2-time-attribution-policy)).

### Worked examples

| Event | `created_at` | Falls in window for snapshot... |
|---|---|---|
| `prev` snapshot = 2026-06-14, `today` snapshot = 2026-06-15 | | |
| BUY inserted 2026-06-14 23:59:59 | 2026-06-14 23:59:59 | **2026-06-14's own window** (the day BEFORE today) — already reflected in `prev.total_value`, not re-counted today |
| BUY inserted 2026-06-15 00:00:01 | 2026-06-15 00:00:01 | **2026-06-15 (today)** — first moment after `prev_day_end` |
| BUY inserted 2026-06-15 23:00:00 | 2026-06-15 23:00:00 | **2026-06-15 (today)** — still before `today_end` |
| BUY inserted 2026-06-16 00:00:00 | 2026-06-16 00:00:00 | **2026-06-16's window**, not today's — equals `today_end` exactly, excluded by `<` |

### What happens to a day with no snapshot generated (gap)?

If a snapshot is skipped (e.g. `SnapshotCoverageError`, market closed, scheduler missed a day), `prev` for the *next successfully generated* snapshot is whatever the most recent **prior** row actually is — found via `ORDER BY snapshot_date DESC LIMIT 1` filtered to `< today`, not `= today - 1`. The window then silently spans multiple calendar days. All transactions inserted during the gap are correctly captured (the window is computed from the actual `prev.snapshot_date`, not an assumed "yesterday"), but the single resulting `investment_return_pct` represents the *cumulative* multi-day return, not a true daily figure. This is consistent across engines and is not a bug — Modified-Dietz-style stripping is path-independent for non-performance flows as long as window boundaries don't overlap or gap incorrectly, which they do not here.

---

## 4. External Cash Flow Definition

### Implementation A — direct transaction sum (`portfolio_snapshots.py`, `portfolio_rebuilder.py`)

```python
net_external_cash_flow = sum(DEPOSIT.total_amount) + sum(INITIAL_CASH.total_amount) - sum(WITHDRAW.total_amount)
```

### Implementation B — cash-balance delta reconciliation (formerly `snapshot_return_recovery.py`; superseded — see Canonical rule below)

```python
net_ecf = (curr_cash_balance - prev_cash_balance) + sum(BUY.total_amount) - sum(SELL.total_amount)
```

Algebraically, since `cash_balance` is maintained by every transaction type (`BUY` subtracts, `SELL`/`DEPOSIT`/`DIVIDEND` add, `WITHDRAW` subtracts), Implementation B reduces to Implementation A *exactly when `cash_balance` was correctly updated by every recorded transaction*. They diverge only when `cash_balance` drifted from what the transaction ledger implies — e.g. a `DEPOSIT` row inserted as a retroactive bookkeeping note without the underlying `cash_balance` ever actually moving, a manual DB edit, or a partial-write bug.

### Comparison

| Dimension | Implementation A (sum events) | Implementation B (cash delta) |
|---|---|---|
| **Accounting correctness** | Directly traceable to discrete recorded events — "what the user told the system happened." Simple, auditable. | Traceable to the authoritative state column (`cash_balance`), which is what NAV actually depends on. |
| **Investment performance correctness** | Correct *only if* every cash-affecting transaction was recorded and `cash_balance` was updated consistently with it. Cannot detect drift. | Self-validating: if `cash_balance` and the transaction ledger disagree, B reports the number that actually explains the NAV change, not the number the (possibly stale) ledger claims. |
| **Replay determinism** | Fully ledger-derived; needs no prior `cash_balance` value other than for the % denominator. | Needs `prev_snap.cash_balance` and `curr_snap.cash_balance` to already be correct and persisted — depends on a previously-written NAV state, not just the ledger. |
| **Robustness** | Vulnerable to "phantom" cash-flow entries (a `DEPOSIT` logged without a real balance change) — A still counts it as external inflow even though no actual cash moved, incorrectly stripping a same-size chunk of real investment gain. | Immune to phantom entries (the documented motivation in `snapshot_return_recovery.py`'s own docstring). Vulnerable instead to undetected `BUY`/`SELL` recording bugs masquerading as cash-flow stripping error, since A's two components (event sums) are isolated from each other while B's formula conflates them into one number. |
| **Historical imports / full rebuild** | Works standalone with no dependency on a previously-computed `cash_balance` — appropriate when reconstructing from nothing. | In a full rebuild, `cash_balance` is *itself* derived in the same replay pass by summing the very same transactions — so for a clean, from-scratch rebuild, B reduces to being numerically identical to A. No information is lost by using B here; it is just unnecessary indirection in that one context. |

### Canonical rule (implemented 2026-06-30): **Implementation A (ledger-derived event sum), everywhere.**

This reverses the recommendation that originally stood in this section. A follow-up architecture review (recorded in `docs/DECISION_LOG.md` → "External Cash Flow Formula Confirmed Canonical") found that Implementation B's apparent safety property — "self-validating against the authority column" — was based on treating `Portfolio.cash_balance` as authoritative. That inverts Design Principle 1: the Transaction ledger is the single source of truth, and `cash_balance` is a *derived, disposable* column that is allowed to drift and then be corrected by replay (this is exactly what `ledger_validator.py` CHECK 8, `CASH_MISMATCH`, already does — it replays the ledger to get the true cash figure and reports `Portfolio.cash_balance` as the thing that "has drifted from the transaction ledger," not the other way around).

The decisive finding: **A fails loud on `cash_balance` drift; B fails quiet.**
- If `cash_balance` is under-credited relative to a real DEPOSIT in the ledger, A reports a large, obviously-wrong negative return (impossible to miss). B silently treats the missing cash flow as "nothing happened" — a flat, unremarkable return that hides the bug.
- If `cash_balance` is corrupted upward with no ledger backing (e.g. a manual SQL edit), A reports a phantom gain (a real, visible anomaly the existing diagnostic logging is designed to catch). B silently absorbs the untracked cash as if it were a legitimate deposit, erasing all trace of it.

In both directions, B's "immunity to phantom entries" is actually blindness: a formula defined in terms of `cash_balance` cannot, by construction, ever disagree with `cash_balance`. A real production case surfaced this exact failure mode and became the regression test for the fix — see `test_phantom_deposit_and_initial_position_surface_as_anomalous_return` in `test_snapshot_return_recovery.py`.

This also aligns with ADR-002 ("Portfolio Metrics never compensate for ledger corruption; validation belongs to Ledger Validator; repair belongs to Ledger Repair; Metrics assume a valid replay") — Implementation B is, by definition, a compensation mechanism: it strips whatever actually happened to `cash_balance`, ledger-explained or not. Implementation A keeps Metrics strictly downstream of the ledger, with no second input path.

`net_external_cash_flow` is computed by `services/portfolio_metrics.py::compute_period_metrics()` for all three engines as of this implementation. `snapshot_return_recovery.py` (previously the only Implementation-B holdout) was migrated; `portfolio_rebuilder.py` and `portfolio_snapshots.py` already used Implementation A and required no formula change.

---

## 5. Realized P&L

### Two distinct quantities

| Quantity | Definition | Computed by | Scope |
|---|---|---|---|
| **Cumulative realized P&L** (`PortfolioSnapshot.realized_pnl`) | Sum of `(sell_price − avg_cost) × shares − total_sell_fees_incl_vat` across **every SELL transaction ever**, parsed from the `"Realized P&L: ±X"` substring embedded in `Transaction.notes` by `execute_sell()` | `portfolio_snapshots.py` (regex over all-time SELLs), `portfolio_rebuilder.py` (`state.cumulative_realized_pnl`, accumulated during replay) | All-time, monotonically accumulating (only resets if all SELLs are reversed/deleted) |
| **Period realized P&L** (`PortfolioSnapshot.period_realized_pnl`) | Same per-SELL formula, but summed only over SELLs whose window timestamp falls in `(prev_snapshot, today]` | All three engines, windowed per [Section 3](#3-snapshot-window-definition) | This period only — transparency metric |

### Does either affect `investment_return_pct`?

**No, by formula — but yes, by construction, already.** Neither `realized_pnl` nor `period_realized_pnl` is added or subtracted anywhere in the `investment_return_pct` formula (see [Section 9](#9-nav-definition) / [ARCH_SPEC.md](ARCH_SPEC.md) canonical formula). They are **transparency-only metrics**.

The reason this is correct, not an oversight: when a SELL executes, equity (shares) leaves the portfolio and cash enters by exactly the net proceeds. The net effect on `total_value` that day is:

```
delta_total_value_from_sell = net_proceeds − (prev_close_price × shares_sold)
                            = (sell_price − prev_close_price) × shares_sold − fees
```

This is exactly the *single-day* price appreciation/depreciation captured in the trade — which is already the correct performance contribution and is already embedded in `total_value` via the cash increase. The *cumulative* `realized_pnl` figure (`sell_price − avg_cost`, since the position was originally opened, possibly months/years ago) is a much larger number, because most of that gain was already recognized as `unrealized_pnl` in **previous** snapshots, day by day, as the price moved. Subtracting `period_realized_pnl` from today's return would double-strip gains that were already counted on earlier days.

**Worked example**: A position with `avg_cost = 100` is sold today at `150` for 10 shares (`period_realized_pnl = 500`, ignoring fees). If the stock closed at `148` yesterday, today's actual contribution to `investment_return_pct` is `(150 − 148) × 10 = 20`, not `500`. The other `480` was already captured across the days the price rose from 100 to 148. `portfolio_snapshots.py`'s own diagnostic logging explicitly checks for and logs this exact situation (`period_realized_pnl > abs(investment_return_amount) * 2`).

---

## 6. Imported Assets

### Current behavior

`INITIAL_POSITION` transactions are classified as a **non-performance capital inflow** (DECISION_LOG.md → "Position Import Accounting Fix, Phase 3B.9"). The market value of the imported shares — computed at **current/live market price at snapshot time**, not the user-supplied `avg_cost` — is stripped from the return formula via `imported_asset_value`.

### Answering the four questions

**Should imported holdings contribute to investment return?**
No. The position existed (was acquired) before the portfolio was tracked by this system. Crediting its full market value as a same-day gain would be wrong by construction — the user did not earn that gain *today*, or even necessarily *while using this tool*.

**Should appreciation before import be ignored?**
Yes — and this is *why* current market price (not `avg_cost`) is used to compute `imported_asset_value`. Stripping at `avg_cost` would leave `(current_price − avg_cost) × shares` of pre-existing unrealized appreciation flowing into `investment_return_pct` on the import date, which is exactly the bug Phase 3B.9 fixed. Stripping at current market price removes the entire position's value, leaving the import with **zero** effect on that day's return; all future appreciation (from the import date forward) is then correctly captured day-by-day in subsequent snapshots, the same as any other holding.

**Should market value or cost basis be used?**
Market value, at the snapshot's effective price (live price in the incremental engines; the day's fetched historical close in the rebuilder). See previous answer for why.

**Should duplicate imports be ignored?**

**Resolved, implemented 2026-06-30 — no.** This was previously where the three engines disagreed:

| Engine | Duplicate-import handling (historical, pre-implementation) |
|---|---|
| `portfolio_snapshots.py` | **No dedup.** Every `INITIAL_POSITION` transaction in the window is stripped, unconditionally. |
| `portfolio_rebuilder.py` | **No dedup.** Same — sums `shares × price` for every `INITIAL_POSITION` row in the window. |
| `snapshot_return_recovery.py` | **Dedupped.** Skipped a re-import for a symbol already present in `prev_snap.holdings_json` with `shares >= tx_shares`. Removed during the `portfolio_metrics.py` migration. |

### Canonical rule (implemented)

Duplicate `INITIAL_POSITION` rows are a **ledger-quality problem**, not a snapshot-math problem, and the codebase already has the right tool for it: `ledger_repair_plan.py`'s `generate_repair_plan()` already auto-detects and repairs `DUP_INITIAL_POSITION` (per [[project_phase6_7e]] memory — Phase 6.7E shipped 2026-06-30). The snapshot-level dedup heuristic that used to live in `snapshot_return_recovery.py` was a defensive workaround for exactly the condition the ledger repair tooling is meant to eliminate upstream.

`services/portfolio_metrics.py::compute_period_metrics()` applies **no dedup heuristic** — it strips every `INITIAL_POSITION` transaction in the window at face value, matching what `portfolio_snapshots.py` and `portfolio_rebuilder.py` always did. Duplicate detection and correction belongs exclusively in `ledger_validator.py` (detection) and `ledger_repair_plan.py` / `repair_plan_executor.py` (correction), run *before* any snapshot engine touches the ledger. A portfolio with an un-repaired duplicate `INITIAL_POSITION` will now show an inflated `imported_asset_value` and a correspondingly distorted `investment_return_pct` for that period — by design, per ADR-002 ("Metrics never compensate for ledger corruption"); run `validate_ledger` / `generate_repair_plan` on any portfolio that predates this change before trusting recomputed numbers.

---

## 7. Quantity Corrections

### What `QUANTITY_CORRECTION` represents

A manual fix to a position's share count that is **not a trade** — correcting a data-entry error, reconciling against a broker statement, etc. Per `execute_quantity_correction()`: "Does NOT affect cash_balance — purely a record-keeping correction." The signed delta (`shares_delta`, positive or negative) is stored as `abs(shares_delta)` in `Transaction.shares`, with the sign recoverable only from the `notes` text (`"Quantity correction: +5.0 shares"` / `"-3.0 shares"`) or from `CanonicalTransaction.qty_correction_delta` (which parses that note).

### Should it affect NAV?

Yes, unavoidably and correctly — `PortfolioItem.shares` changes, so `equity_value` and therefore `total_value` change on the day the correction is applied. This is real and correct: the system's recorded NAV must reflect the system's recorded share count.

### Should it affect external cash flow?

No. No cash moves (`execute_quantity_correction` explicitly does not touch `cash_balance`), so it has no place in `net_external_cash_flow`.

### Should it affect investment return?

No — it must be fully stripped from `investment_return_pct`, the same as `imported_asset_value`, via `manual_adjustment_value`. A correction is not a market event; the user did not buy or sell anything, so it cannot be a gain or loss.

### A correctness gap found while researching this document (fixed 2026-06-30)

Stripping must be **signed**, not magnitude-only, and two of the three engines previously got this wrong:

| Engine | Formula used |
|---|---|
| `portfolio_snapshots.py` | `manual_adjustment_value += tx.shares × live_price` — `tx.shares` is **always positive** (stored as `abs(delta)` in the DB) |
| `portfolio_rebuilder.py` | `manual_adj_value = sum(abs(qty_correction_delta) × price)` — **explicitly absolute value** |
| `snapshot_return_recovery.py` | `manual_adj_value = sum(qty_correction_delta × price_per_share)` — **signed** |

The formula subtracts `manual_adjustment_value` from `pure_market_gain` (`pure_gain = curr_nav − prev_nav − net_ecf − imported_asset_value − manual_adjustment_value`). Walking a downward correction of 10 shares at price 100 (no other activity that day) through both versions:

- **Signed** (recovery engine): `manual_adjustment_value = −1000`. `curr_nav − prev_nav = −1000` (equity dropped). `pure_gain = −1000 − 0 − 0 − (−1000) = 0`. **Correct** — a correction has zero effect on return.
- **Absolute value** (live engine, rebuilder): `manual_adjustment_value = +1000`. `pure_gain = −1000 − 1000 = −2000`. **Wrong** — a pure data-entry correction shows up as a fabricated −2000/prev_nav% loss, because the real NAV drop is counted once *and* the strip subtracts a second, wrongly-signed, equal-magnitude amount in the same direction instead of offsetting it.

An upward correction happens to net out correctly under the absolute-value formula only because the sign of the NAV change and the (always-positive) strip happen to point the same way in that one direction — the bug is specific to **downward** corrections, which is presumably why it has not been noticed in practice (most recorded corrections likely add missing shares rather than remove erroneous ones).

### Canonical rule (implemented 2026-06-30)

**`manual_adjustment_value` is signed**, computed as `qty_correction_delta × price_per_share` (not `abs(qty_correction_delta)`), in `services/portfolio_metrics.py::compute_period_metrics()` — matching what `snapshot_return_recovery.py` always did independently. All three engines now agree. This changes historical numbers only for a portfolio that is rebuilt/recomputed after this fix and has a downward `QUANTITY_CORRECTION` in its ledger; no automatic backfill of already-persisted snapshots was performed (forward-only, consistent with the project's existing `POST /admin/recalculate-cost-basis` pattern for formula changes). Regression test: `test_quantity_correction_downward_strips_negative_amount` in `test_portfolio_metrics.py`.

---

## 8. Fees and Taxes

### Definitions (already canonical per `DECISION_LOG.md` → "Fee Decomposition")

- `Transaction.fees` = pre-VAT subtotal (commission + trading fee + clearing fee)
- `Transaction.taxes` = VAT amount (7% of the pre-VAT subtotal, for `SET_STANDARD`/`DR_STANDARD` profiles)
- `fees + taxes` = total fee burden for that transaction leg
- Backward compatibility: pre-decomposition rows have `taxes = 0`, so `fees + taxes = fees` still equals the historical total — no data migration was required.

### Should they affect investment return?

**Yes, indirectly and only once — they are never stripped.** Fees reduce `total_value` through the same mechanism as any other cash movement on a trade: `execute_buy()` debits `cash_balance` by `net_buy_amount = gross + total_fees_incl_vat` (more than the gross trade value), and `execute_sell()` credits `cash_balance` by `net_sell_proceeds = gross − total_fees_incl_vat` (less than the gross trade value). Both effects flow straight into `total_value` and are **not** stripped anywhere in the cash-flow-adjustment logic — `BUY` and `SELL` are explicitly classified as "performance events" with "net cash-flow effect = 0" *at the trade level* (equity in, cash out is a wash for NAV), while the fee component is a genuine, permanent drag that survives into `investment_return_pct`. This is correct: brokerage costs are a real cost of investing and must reduce measured performance, exactly as a real-world brokerage statement would show.

### Should they be transparency metrics?

Yes, in addition to (not instead of) affecting return. `period_fees_paid` sums `(fees + taxes)` across all `BUY` and `SELL` transactions in the window, purely so the UI can show "fees cost you X this period" without requiring the user to derive it from the return delta themselves. It is **never added back** to `investment_return_pct` — it is already embedded there via the cash balance, per Design Principle 7.

### Fee-inclusive cost basis (relevant to P&L definitions in Section 5)

Per `DECISION_LOG.md` → "Fee-Inclusive Cost Basis": `avg_cost = net_buy_amount / shares` where `net_buy_amount` already includes all BUY-side fees and VAT. This means `realized_pnl = (sell_price − avg_cost) × shares − sell_side_fees_incl_vat` already nets out **both legs'** transaction costs (buy-side baked into `avg_cost`, sell-side subtracted explicitly) — a SELL's `realized_pnl` is true round-trip economic profit, not a gross trading gain.

---

## 9. NAV Definition

```
total_value  =  cash_balance  +  equity_value

equity_value =  Σ over holdings ( shares × current_price )
                 (holdings with no live price are excluded from equity_value
                  entirely — see coverage threshold note below)

cash_balance =  Portfolio.cash_balance column (live engine)
              =  replayed running cash balance (rebuilder, from Transaction ledger)
```

- **Cash**: a single scalar per portfolio, mutated by every cash-affecting transaction (`BUY` debits, `SELL`/`DEPOSIT`/`DIVIDEND`/`INITIAL_CASH` credit, `WITHDRAW` debits). `QUANTITY_CORRECTION` and `INITIAL_POSITION` never touch cash.
- **Equity value**: sum of `shares × current_price` across all holdings with a resolvable price. A holding whose price lookup failed is **excluded from `equity_value` entirely** for that snapshot (not valued at zero, not valued at stale price) — see the coverage threshold gate below.
- **Total value (NAV)**: the sum. This is the canonical portfolio size figure used as the denominator for `investment_return_pct` and the basis for all attribution math.

### Canonical return formula (already documented in `ARCH_SPEC.md`, restated here as the frozen rule)

```
investment_return_pct =
  (today_nav − prev_nav − net_external_cash_flow − imported_asset_value − manual_adjustment_value)
  / prev_nav × 100

daily_return_pct = investment_return_pct   (kept as a separate column for historical/legacy reasons;
                                             always set to the identical value in all three engines today)
```

`period_realized_pnl`, `period_dividend_income`, `period_fees_paid` are **not** terms in this formula — see Sections 5 and 8.

### Coverage threshold (data-quality gate, not a business-logic exclusion)

All three engines enforce a `_COVERAGE_THRESHOLD = 0.90`: if fewer than 90% of holdings have a resolvable price for the target date, the snapshot is either rejected (`SnapshotCoverageError`, live engine) or written with `price_coverage` flagged below threshold (rebuilder, caller decides whether to persist). This exists to prevent a partial-data NAV (e.g. yfinance outage for 3 of 20 holdings) from silently understating `equity_value` and corrupting the return series with a fake, large negative `investment_return_pct`. It is a **guard**, not a definition — the NAV formula itself does not change based on coverage; coverage only gates whether an incomplete-data snapshot is allowed to be written at all.

### NAV reconciliation invariant

`portfolio_snapshots.py` explicitly recomputes `equity_value + cash` and compares it against the `total_value` about to be persisted, logging `[NAV RECONCILIATION FAILED]` at ERROR level if they differ by more than `0.01`. By construction in the current code this can never actually fire (the same addition produces both numbers) — it exists as a tripwire for future refactors that might compute the two halves independently. This invariant should be preserved verbatim in `portfolio_metrics.py`.

---

## 10. Benchmark Compatibility

Benchmark and attribution math (`services/analytics/attribution_engine.py`, `services/decision_memory/shadow_tracker.py`, `services/decision_memory/attribution.py`) does **not** independently recompute portfolio return. It consumes `PortfolioSnapshot.investment_return_pct` (actual portfolio) and `ShadowPortfolioSnapshot.daily_return_pct` (shadow portfolios, which have no external cash flows to strip by construction, so their raw daily return is already "clean") and chains them via **Time-Weighted Return (TWR)** to produce cumulative/period figures for comparison against `BenchmarkPrice` series.

The explicit comment in `attribution_engine.py` (`"Actual portfolio uses TWR from investment_return_pct (adjusted). Shadow portfolios use TWR from daily_return_pct (already clean)."`) is the existing acknowledgment of this contract.

### Rule for `portfolio_metrics.py` and any future engine

**Never recompute return inside an analytics/attribution module.** Any module that needs a portfolio's return for a given period must read `PortfolioSnapshot.investment_return_pct` (or chain it via TWR across multiple snapshots) rather than re-deriving NAV deltas from `Transaction` or `PortfolioItem` rows directly. This is the only way to guarantee Design Principle 5 (single source of truth for return) extends to every downstream consumer, not just the three snapshot-generation engines audited in this document. If a future engine's needs cannot be met by reading existing snapshot columns, that is a signal the snapshot schema is incomplete — extend it (per the `CLAUDE.md` "Adding a new snapshot column" checklist), don't bypass it.

---

## 11. Invariants

These must hold for any conforming implementation, including the eventual `portfolio_metrics.py`:

1. **`total_value = cash_balance + equity_value`**, always, by construction — not just approximately, exactly (`portfolio_snapshots.py`'s reconciliation check formalizes this as a `0.01` tolerance, which exists only to catch floating-point drift, not legitimate divergence).
2. **Rebuilding twice produces identical snapshots.** Same Transaction rows in, same `PortfolioSnapshot` rows out, every time — no clock dependency, no ordering dependency beyond `(transaction_date, id)`.
3. **`rebuild_portfolio()` and `recover_portfolio_snapshot_returns()` must produce identical return metrics for the same date range, for windows where both engines agree on transaction attribution.** ✅ **Holds as of 2026-06-30** — both engines delegate to `services/portfolio_metrics.py::compute_period_metrics()` (see [Section 4](#4-external-cash-flow-definition), [Section 7](#7-quantity-corrections); regression test: `test_parity_full_transaction_mix` in `test_portfolio_metrics_parity.py`). The qualifier matters: a transaction with `transaction_date != created_at` (a backdated entry) is *correctly* attributed to a different window by each engine per Section 2 / ADR-003 — that is not a violation of this invariant, since the two engines are answering different questions for that one transaction (see `test_backdated_transaction_attributed_per_engine_own_window_field`).
4. **Transaction insertion order must not affect historical performance**, *given identical `(transaction_date, id)` values*. Replay order is fully determined by the canonicalizer's `(transaction_date, id)` sort key, not by wall-clock insertion order.
5. **`created_at` must never influence the *magnitude* of any computed field** — share count, price, P/L, fee amount. It may only influence *which window a transaction is attributed to* (Section 2), and only in incrementally-built (non-from-scratch) contexts. `services/portfolio_metrics.py` enforces this structurally: it never reads `created_at` at all, only `period_transactions` already filtered by the caller.
6. **`fees` and `taxes` always sum to the same total fee burden**, regardless of whether a row predates the Phase 3B.10 decomposition (`taxes=0` rows still sum correctly).
7. **`avg_cost` is always fee-inclusive** (`net_buy_amount / shares`) — never a bare price-per-share figure.
8. **Realized P&L (cumulative or period) is never a term in `investment_return_pct`** — it is fully transparency-only (Section 5).
9. **`imported_asset_value` and `manual_adjustment_value` always net to zero effect on `investment_return_pct`** for the period in which they occur, when correctly signed (Section 6, Section 7) and the ledger is clean (no un-repaired duplicate imports). ✅ **Holds as of 2026-06-30** for a clean ledger — `manual_adjustment_value` is now signed in all three engines. Note this is now a precondition, not an unconditional guarantee: per the Section 6 resolution, a portfolio with an un-repaired duplicate `INITIAL_POSITION` will *deliberately* show a non-zero net effect (fail loud, per ADR-002) until the ledger is repaired.
10. **A snapshot is never written with `equity_value` computed from a holding's `avg_cost` as a price fallback.** (This was the historical corruption pattern `snapshot_repair.py` exists to fix — see its docstring.)
11. **The `(portfolio_id, snapshot_date)` pair is unique** — `generate_daily_snapshot()` upserts rather than duplicating, enforced by a DB unique constraint, not just application logic.
12. **`investment_return_pct` is `None` (not `0`) when there is no valid previous snapshot** (`prev is None` or `prev.total_value <= 0`) — `0` would falsely claim a measured flat return; `None` correctly states "no return is computable yet." All three engines respect this.

---

## 12. Open Questions

Questions #1–#3 were resolved and implemented on 2026-06-30 (ADR-001 through ADR-004). Questions #4–#6 remain open — out of scope for the `portfolio_metrics.py` implementation and not addressed by it.

1. ~~Which cash-flow formula becomes canonical — A (event sum) or B (cash delta)?~~ **Resolved: Implementation A**, forward-only (no backfill of already-persisted snapshots). See [Section 4](#4-external-cash-flow-definition) and `docs/DECISION_LOG.md` → "External Cash Flow Formula Confirmed Canonical."

2. ~~Should the live engine and rebuilder be migrated to signed `manual_adjustment_value`?~~ **Resolved: yes**, forward-only. See [Section 7](#7-quantity-corrections) and `docs/DECISION_LOG.md` → "Signed Manual Adjustment Value Fix."

3. ~~Should duplicate-`INITIAL_POSITION` dedup live exclusively in ledger repair, or should snapshot engines keep a defensive check?~~ **Resolved: ledger repair only** — the snapshot-level dedup heuristic was removed from `snapshot_return_recovery.py`. See [Section 6](#6-imported-assets) and `docs/DECISION_LOG.md` → "INITIAL_POSITION Dedup Removed from Snapshot Engines."

4. **[Still open] Should `daily_return_pct` be removed as a separate column** now that it is set to exactly `investment_return_pct` in all three engines with no documented case of divergence? `services/portfolio_metrics.py::PeriodMetrics.daily_return_pct` preserves this duplication unchanged — not addressed by this implementation.

5. **[Still open] What should happen to `imported_asset_value`/`manual_adjustment_value` valuation when the live price is unavailable?** All three engines (now via the shared `price_lookup` fallback in `compute_period_metrics()`) still fall back to `tx.price_per_share` when no live/historical price is found. Not addressed by this implementation.

6. **[Still open] Is `transaction_date` always trustworthy as portfolio-state ordering, or should there be a validation gate before a rebuild trusts it blindly?** `services/portfolio_metrics.py` has no ledger-validity precondition built in — per ADR-002, it "assumes a valid replay," but nothing currently enforces a clean `ledger_validator` pass before any engine calls it. Not addressed by this implementation.

7. ~~Stray debug output found in `portfolio_rebuilder.py`~~ **Resolved** — the `if curr_date == '2026-05-27': print(...)` block was removed when `_populate_return_fields` was migrated to call `compute_period_metrics()`.

---

# Summary of Remaining Unresolved Business Decisions

1. Whether `daily_return_pct` should be deprecated as a duplicate column.
2. Fallback pricing policy for stripped non-performance transactions when live/historical price lookup fails.
3. Whether a clean `ledger_validator` pass should be a hard precondition for trusting any return calculation.

# Implementation status

**Implemented 2026-06-30.** `backend/services/portfolio_metrics.py` is the single shared implementation (ADR-001 through ADR-004); `portfolio_rebuilder.py`, `portfolio_snapshots.py`, and `snapshot_return_recovery.py` all delegate to it. Open Questions #1–#3 (cash-flow formula, signed manual_adjustment_value, dedup ownership) were resolved as part of this implementation — all forward-only, no backfill of already-persisted snapshots. Open Questions #4–#6 above remain genuinely open and are not addressed by this implementation; resolve them in a future change and update this document (not just `DECISION_LOG.md`) when they are.
