# Portfolio Calculation Rules
_Canonical business specification for Portfolio Performance Calculation. Source of truth for `portfolio_metrics.py` and every existing/future engine that touches NAV, return, or attribution math._

_Status: **Business rules frozen for documentation purposes only.** This document records what the current engines do today, evaluates where they disagree, and recommends canonical answers. It does **not** change any code. See [Section 12](#12-open-questions) for what still requires a human decision before implementation begins._

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

### Implementation B — cash-balance delta reconciliation (`snapshot_return_recovery.py`)

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

### Recommendation: **Implementation B (cash-balance delta) as the canonical rule, everywhere.**

Reasoning:
1. **B is strictly safer.** In a portfolio with a clean, fully-consistent ledger (the common case, and always true immediately after a full rebuild), A and B produce identical numbers — there is no case where switching to B changes a correct result.
2. **B is the only one of the two that is self-validating against the authority column.** `cash_balance` is the field NAV (`total_value = cash + equity_value`) actually depends on — see [Section 9](#9-nav-definition). A formula that can silently diverge from the column driving NAV is a latent source of phantom returns; B cannot diverge from it by construction.
3. **The "B needs a prior persisted `cash_balance`" objection does not apply to the full rebuild.** `portfolio_rebuilder.py` already derives `cash_balance` for every reconstructed day as part of Stage 1/2 replay (`_SnapshotDay.cash_balance`), and stores it as `PortfolioSnapshot.cash_balance` for both the `prev` and `curr` rows being compared in Stage 3. The data Implementation B needs is already present at the point `_populate_return_fields()` runs — switching the rebuilder to B requires no new data, only the formula change.
4. Adopting B everywhere directly satisfies Design Principle 5 — one formula, three engines, identical output.

This recommendation requires changing `portfolio_snapshots.py` and `portfolio_rebuilder.py` to compute `net_external_cash_flow` via the cash-delta formula instead of the event-sum formula. **No such change is made by this document** — it is a recommendation for the eventual `portfolio_metrics.py` implementation, flagged again in [Section 12](#12-open-questions).

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

This is **where the three engines currently disagree**, and it is the most consequential open gap in this section:

| Engine | Duplicate-import handling |
|---|---|
| `portfolio_snapshots.py` | **No dedup.** Every `INITIAL_POSITION` transaction in the window is stripped, unconditionally. |
| `portfolio_rebuilder.py` | **No dedup.** Same — sums `shares × price` for every `INITIAL_POSITION` row in the window. |
| `snapshot_return_recovery.py` | **Dedups.** Skips a re-import for a symbol already present in `prev_snap.holdings_json` with `shares >= tx_shares`, on the documented theory that it's "a retroactive documentation entry for equity already embedded in the previous NAV." |

### Recommendation

Duplicate `INITIAL_POSITION` rows are a **ledger-quality problem**, not a snapshot-math problem, and the codebase already has the right tool for it: `ledger_repair_plan.py`'s `generate_repair_plan()` already auto-detects and repairs `DUP_INITIAL_POSITION` (per [[project_phase6_7e]] memory — Phase 6.7E shipped 2026-06-30). The snapshot-level dedup heuristic in `snapshot_return_recovery.py` is a defensive workaround for exactly the condition the ledger repair tooling is meant to eliminate upstream.

Canonical rule: **`INITIAL_POSITION` snapshot stripping should assume a clean ledger (no duplicates) and apply no dedup heuristic at compute time.** Duplicate detection and correction belongs exclusively in `ledger_validator.py` (detection) and `ledger_repair_plan.py` / `repair_plan_executor.py` (correction), run *before* any snapshot engine touches the ledger. This both resolves the three-way inconsistency and avoids encoding ledger-cleanliness assumptions into three separate snapshot engines. Until the ledger repair step is mandatory/automatic ahead of every rebuild, `snapshot_return_recovery.py`'s defensive dedup remains a reasonable belt-and-suspenders check — but it should not be treated as "the canonical rule," only as a safety net.

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

### A correctness gap found while researching this document

Stripping must be **signed**, not magnitude-only, and two of the three engines currently get this wrong:

| Engine | Formula used |
|---|---|
| `portfolio_snapshots.py` | `manual_adjustment_value += tx.shares × live_price` — `tx.shares` is **always positive** (stored as `abs(delta)` in the DB) |
| `portfolio_rebuilder.py` | `manual_adj_value = sum(abs(qty_correction_delta) × price)` — **explicitly absolute value** |
| `snapshot_return_recovery.py` | `manual_adj_value = sum(qty_correction_delta × price_per_share)` — **signed** |

The formula subtracts `manual_adjustment_value` from `pure_market_gain` (`pure_gain = curr_nav − prev_nav − net_ecf − imported_asset_value − manual_adjustment_value`). Walking a downward correction of 10 shares at price 100 (no other activity that day) through both versions:

- **Signed** (recovery engine): `manual_adjustment_value = −1000`. `curr_nav − prev_nav = −1000` (equity dropped). `pure_gain = −1000 − 0 − 0 − (−1000) = 0`. **Correct** — a correction has zero effect on return.
- **Absolute value** (live engine, rebuilder): `manual_adjustment_value = +1000`. `pure_gain = −1000 − 1000 = −2000`. **Wrong** — a pure data-entry correction shows up as a fabricated −2000/prev_nav% loss, because the real NAV drop is counted once *and* the strip subtracts a second, wrongly-signed, equal-magnitude amount in the same direction instead of offsetting it.

An upward correction happens to net out correctly under the absolute-value formula only because the sign of the NAV change and the (always-positive) strip happen to point the same way in that one direction — the bug is specific to **downward** corrections, which is presumably why it has not been noticed in practice (most recorded corrections likely add missing shares rather than remove erroneous ones).

### Recommendation

Canonical rule: **`manual_adjustment_value` must be signed**, computed as `qty_correction_delta × price_per_share` (not `abs(qty_correction_delta)`), matching `snapshot_return_recovery.py`. This is flagged here as a found defect for awareness, not fixed in this document per the no-code-changes constraint — see [Section 12](#12-open-questions).

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
3. **`rebuild_portfolio()` and `recover_portfolio_snapshot_returns()` must produce identical return metrics for the same date range.** ⚠️ **Currently false** — see [Section 4](#4-external-cash-flow-definition) (cash-flow formula divergence) and [Section 7](#7-quantity-corrections) (signed-delta divergence). This is the most important invariant violation this document surfaces.
4. **Transaction insertion order must not affect historical performance**, *given identical `(transaction_date, id)` values*. Replay order is fully determined by the canonicalizer's `(transaction_date, id)` sort key, not by wall-clock insertion order.
5. **`created_at` must never influence the *magnitude* of any computed field** — share count, price, P/L, fee amount. It may only influence *which window a transaction is attributed to* (Section 2), and only in incrementally-built (non-from-scratch) contexts.
6. **`fees` and `taxes` always sum to the same total fee burden**, regardless of whether a row predates the Phase 3B.10 decomposition (`taxes=0` rows still sum correctly).
7. **`avg_cost` is always fee-inclusive** (`net_buy_amount / shares`) — never a bare price-per-share figure.
8. **Realized P&L (cumulative or period) is never a term in `investment_return_pct`** — it is fully transparency-only (Section 5).
9. **`imported_asset_value` and `manual_adjustment_value` always net to zero effect on `investment_return_pct`** for the period in which they occur, when correctly signed (Section 6, Section 7) — this currently holds for imports but is violated for downward quantity corrections in two of three engines.
10. **A snapshot is never written with `equity_value` computed from a holding's `avg_cost` as a price fallback.** (This was the historical corruption pattern `snapshot_repair.py` exists to fix — see its docstring.)
11. **The `(portfolio_id, snapshot_date)` pair is unique** — `generate_daily_snapshot()` upserts rather than duplicating, enforced by a DB unique constraint, not just application logic.
12. **`investment_return_pct` is `None` (not `0`) when there is no valid previous snapshot** (`prev is None` or `prev.total_value <= 0`) — `0` would falsely claim a measured flat return; `None` correctly states "no return is computable yet." All three engines respect this.

---

## 12. Open Questions

These require an explicit human decision before `portfolio_metrics.py` implementation begins. None are answered by this document — they are listed so the decision is made deliberately rather than inherited by accident from whichever engine happens to get ported first.

1. **Which cash-flow formula becomes canonical — A (event sum) or B (cash delta)?** Section 4 recommends B, but this changes `net_external_cash_flow` output for any portfolio whose ledger and `cash_balance` have ever drifted apart. Adopting B retroactively could change historical `investment_return_pct` values on past dates where drift existed. Decision needed: backfill historical snapshots with the new formula, or apply only going forward?

2. **Should the live engine and rebuilder be migrated to signed `manual_adjustment_value`** (Section 7)? This is closer to a bug fix than a policy choice, but it is listed here because (a) no code changes are permitted in this task, and (b) fixing it changes historical numbers for any portfolio with a downward `QUANTITY_CORRECTION` in its ledger — same backfill-vs-forward-only question as #1.

3. **Should duplicate-`INITIAL_POSITION` dedup live exclusively in ledger repair, or should snapshot engines keep a defensive check?** (Section 6.) Removing it from `snapshot_return_recovery.py` simplifies the formula but removes a safety net for ledgers that haven't been through repair yet.

4. **Should `daily_return_pct` be removed as a separate column** now that it is set to exactly `investment_return_pct` in all three engines with no documented case of divergence? Keeping both is harmless but is unexplained duplication that a new contributor reading `portfolio_metrics.py` would reasonably question.

5. **What should happen to `imported_asset_value`/`manual_adjustment_value` valuation when the live price is unavailable?** All three engines fall back to `tx.price_per_share` (the user-entered or historical transaction price) when no live/historical price is found for that symbol on that date. This means the stripped amount can differ from the "true" market value if the price moved between the transaction date and the snapshot date for genuinely backdated entries — is `price_per_share` fallback acceptable, or should such transactions block the snapshot entirely (similar to the coverage-threshold gate for holdings)?

6. **Is `transaction_date` always trustworthy as portfolio-state ordering, or should there be a validation gate (block negative-share states, etc.) before a rebuild trusts it blindly?** `ledger_validator.py` already has checks for some of this (date skew, missing symbols, non-positive shares/prices) — should `portfolio_metrics.py` require a clean `ledger_validator` pass (no CRITICAL/ERROR findings) as a precondition for any return calculation, live or rebuilt?

7. **Stray debug output found in `portfolio_rebuilder.py`** (`_populate_return_fields`, lines ~716-730): an unconditional `print()` block gated on a hardcoded date string (`if curr_date == '2026-05-27'`). This has no effect on correctness (it's pure stdout noise) but indicates the cash-flow formula was being actively debugged around that date — worth checking whether that debugging session left any other unresolved questions about that specific portfolio/date before treating the rebuilder's current formula as settled. Not fixed here per the no-code-changes constraint.

---

# Summary of Remaining Unresolved Business Decisions

1. Canonical external-cash-flow formula: Implementation A vs. B (recommended: B, but needs a backfill/forward-only decision).
2. Whether to fix the signed-vs-absolute `manual_adjustment_value` discrepancy now or treat it as a tracked defect for later (recommended: fix, signed; same backfill question applies).
3. Where duplicate-`INITIAL_POSITION` detection should live long-term: ledger repair only, or snapshot-level defense-in-depth too.
4. Whether `daily_return_pct` should be deprecated as a duplicate column.
5. Fallback pricing policy for stripped non-performance transactions when live/historical price lookup fails.
6. Whether a clean `ledger_validator` pass should be a hard precondition for trusting any return calculation.

# Recommendation: Is the system ready to implement `portfolio_metrics.py`?

**Not yet — close, but two of the six open questions (#1 and #2 above) are not stylistic, they are correctness questions that change historical numbers depending on the answer.** Implementing `portfolio_metrics.py` against whichever formula is ported first (most likely the live engine's, since it's the most-used) without first deciding #1 and #2 would silently canonize the less-robust cash-flow formula and a signed-delta bug into the new single source of truth — exactly the outcome this freeze exercise was meant to prevent.

Suggested sequence before implementation starts:
1. Resolve open questions #1 and #2 explicitly (a short decision-log entry each, same format as existing `DECISION_LOG.md` entries).
2. Decide the backfill question for both (apply retroactively to historical snapshots, or forward-only from a cutover date) — this is itself worth a `DECISION_LOG.md` entry, since it affects every existing portfolio's historical return chart.
3. Resolve #3–#6 (lower-stakes, but each changes the shape of `portfolio_metrics.py`'s public surface).
4. Only then begin implementation, against this document as the frozen spec — and update this document (not just `DECISION_LOG.md`) if any answer changes during implementation, since this is meant to remain the living source of truth referenced by every future engine (shadow snapshots, recommendation snapshots, benchmark analytics, performance analytics) per the original goal stated in the task.
