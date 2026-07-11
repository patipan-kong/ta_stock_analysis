# M5 Track B — Stage 2 Runbook: Ledger Asset ID Backfill

Operational companion to [M5_TRACK_B_NATIVE_INTEGRATION_TDD.md](M5_TRACK_B_NATIVE_INTEGRATION_TDD.md) §7 Stage 2. Covers how to run, verify, and if necessary reverse the Stage 2 backfill. Not a design document — see the TDD for rationale.

**Scope reminder:** Stage 2 only adds nullable `asset_id` columns and writes already-decided Registry verdicts onto them. Nothing reads `asset_id` yet (that's Stage 5). Every operation below is either fully reversible or provably inert with respect to production behavior.

---

## 1. Migration procedure

Two chained, purely-additive Alembic migrations, both nullable and indexed, no existing constraint touched:

| Revision | Adds |
|---|---|
| `b4d6f8a0c2e4` | `transactions.asset_id`, `portfolio_items.asset_id`, `watchlist.asset_id` (all nullable FK → `assets.id`) |
| `e6f8b0d2a4c6` | `ledger_asset_backfill_checkpoints` table (backfill's append-only attempt log) |

**Apply:**
```bash
cd backend
alembic upgrade head
```

Both migrations are additive and safe to run against a live database with no downtime — `ADD COLUMN ... NULL` and `CREATE TABLE` only, no data rewrite, no lock beyond what those DDL statements normally take on the target Postgres instance.

**Then, separately, run the backfill** (not part of the migration — a distinct, reviewable step):
```bash
# 1. Dry run first — always. Review the report before committing anything.
python manage.py backfill_asset_ids --all

# 2. Check the unresolved backlog specifically.
python manage.py backfill_asset_ids --all --unresolved-report

# 3. Commit, once the dry-run report looks right.
python manage.py backfill_asset_ids --all --commit
```

Per-portfolio is also supported (`--portfolio ID` instead of `--all`) — recommended for the first live run, to keep the blast radius small and the output easy to review, per Migration Principle 3 ("no flag days, per-portfolio, reversible").

## 2. Verification (required before treating a backfill run as done)

1. **Backfill report** — confirm `still_unresolved_transaction_count` matches what you expect (Track A's known adjudication backlog; not a new number). Every unresolved claim shape is printed by name, never silently dropped.
2. **Golden Baseline parity** — Stage 2 doesn't require a fresh baseline capture (nothing it does can change replay output — see §4 below), but as a belt-and-braces check:
   ```bash
   python manage.py golden_baseline --portfolio ID --compare-stored
   ```
   Must report `is_bit_identical=True` (exit code 0) exactly as it did before the backfill ran.
3. **Regression suite** — `pytest tests/test_ledger_asset_backfill.py tests/test_transaction_canonicalizer.py tests/test_portfolio_rebuilder.py tests/test_ledger_validator.py` should be unaffected (see §5 of the Stage 2 report for the full before/after count).

## 3. Rollback procedure

Two independent layers — use the one that matches what actually needs undoing.

**Data rollback (a specific backfill run):**
```bash
# Dry run first.
python manage.py backfill_asset_ids --rollback RUN_ID

# Commit.
python manage.py backfill_asset_ids --rollback RUN_ID --commit
```
Resets `asset_id` back to `NULL` for exactly the rows that run wrote — never a different run's rows, and never a row a later process has since legitimately changed (`rollback_backfill()` only resets a row if its current `asset_id` still equals what this run set it to). Low-risk by construction: nothing reads `asset_id` yet, so a rollback is invisible to every other part of the platform.

**Schema rollback (remove the columns/table entirely):**
```bash
cd backend
alembic downgrade c6e8a0f2d4b6
```
Verified round-trip (upgrade → downgrade → upgrade again, throwaway SQLite DB) as part of Stage 2's own testing — see the Stage 2 deliverables report. Only needed if the columns themselves need to disappear (e.g. abandoning M5 Track B entirely); ordinary operational mistakes are better fixed with the data-level rollback above, which doesn't require a second migration cycle.

## 4. Why this is low-risk (the invariant this runbook leans on)

`CanonicalTransaction` (`services/transaction_canonicalizer.py`) has no `asset_id` field, and `_canonicalize_one()` never reads `tx.asset_id` — so `canonicalize_transactions()`, `replay_key()`, `portfolio_rebuilder.py`, and `ledger_validator.py` are structurally incapable of observing whatever value the `asset_id` column holds. Verified by `tests/test_ledger_asset_backfill.py::test_canonicalization_and_replay_key_are_unaffected_by_backfilled_asset_id`, which backfills a real transaction and asserts its `CanonicalTransaction`/`replay_key()` output is byte-identical before and after. This is why backfill (and its rollback) can be run against production with no replay-parity risk, no maintenance window, and no coordination with any other consumer.

## 5. Operational checklist

- [ ] `alembic upgrade head` applied (`alembic current` shows `e6f8b0d2a4c6`)
- [ ] `backfill_asset_ids --all` (dry run) reviewed — counts and unresolved backlog make sense
- [ ] `backfill_asset_ids --all --unresolved-report` reviewed — no unexpectedly-unresolved symbol
- [ ] `backfill_asset_ids --all --commit` run (per-portfolio first, for the first live run)
- [ ] `golden_baseline --compare-stored` still reports `is_bit_identical=True` for spot-checked portfolios
- [ ] Regression suite (§2.3 above) green
- [ ] Run ID recorded somewhere retrievable (needed for `--rollback` if ever required)

## 6. Expected runtime

Backfill cost is proportional to claim-shape count, not row count — one Registry-read pass per distinct `(raw_symbol, canonical_symbol, currency)` shape (via `plan_migration()`, reused unmodified from M5.1), then one bounded query per table per shape. At M5 Track A's own bootstrap scale (52 transactions, 25 claim shapes, 2 duplicate clusters — `ASSET_REGISTRY_RETROSPECTIVE.md`'s reference numbers), a full-workspace `--all` run completes in low single-digit seconds. No network I/O, no price fetching — the backfill never touches `yfinance` or any external provider. Runtime scales roughly linearly with the number of distinct claim shapes across the scanned portfolios; per-portfolio runs targeting a single portfolio are correspondingly faster and are the recommended unit for the first live run.

## 7. Failure handling

- **Unresolved claim shape** (AMBIGUOUS/CANDIDATE/CONFLICT/UNKNOWN verdict): never blocks the run. Reported as `SKIPPED_NOT_RESOLVED` with full detail (symbol, canonical symbol, currency, transaction count) in every report — dry-run, live, and `--unresolved-report`. Resolve it via the existing Track A tools (`plan_migration` → `execute_migration` / `bootstrap_registry`), then re-run backfill; already-resolved shapes are untouched (idempotent).
- **Unexpected exception mid-run** (infra failure, not an identity question): caught per-shape, logged with `_log.exception`, the session is rolled back, and the shape is reported as `SKIPPED_NOT_RESOLVED` with the exception detail in the report — the run continues to the next shape rather than aborting entirely. Nothing partial is left committed for that one shape (SQLAlchemy session rollback discards any in-progress row mutations for it).
- **Interrupted live run** (process killed mid-run): safe to resume. Re-invoke with the same `--run-id` printed at the start of the interrupted run — already-`COMPLETED` shapes are skipped (checkpoint lookup), and processing continues from where it left off. Recompute is cheap (`plan_migration()` re-reads current ledger/Registry state fresh, so a resumed run always sees up-to-date state rather than a stale plan).
- **Portfolio scoping mistake** (`--portfolio` targeting the wrong id, or forgetting `--all`): no special recovery needed — re-run with the correct scope. `portfolio_ids` scoping never touches a portfolio outside the requested set (tested: `test_portfolio_scoping_never_touches_other_portfolio`), so a narrowly-scoped run is always safe to broaden later with a fresh run.
- **Migration applied but backfill never run**: harmless indefinitely. `asset_id IS NULL` on every row is the same "not yet adjudicated" state the platform already treats as legitimate everywhere else (`Unresolved`, per `ASSET_REGISTRY.md` §7) — there is no time-boxed window in which this is considered a problem.
