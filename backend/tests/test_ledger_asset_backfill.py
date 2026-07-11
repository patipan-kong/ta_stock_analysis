"""Tests for the Ledger Asset ID Backfill (M5 Track B, Stage 2).

Mirrors test_migration_executor.py's fixture idiom exactly (in-memory
SQLite, real mint_asset()/attach_identifier()/plan_migration() rather than
mocks) since ledger_asset_backfill.py is architecturally a sibling of
migration_executor.py — same "commit an already-decided verdict" shape,
different target tables.

Validates:
  1. A RESOLVED claim shape backfills asset_id onto Transaction and
     PortfolioItem rows sharing its symbol, and is checkpointed COMPLETED
     with the exact row ids it touched.
  2. Watchlist rows are backfilled by symbol match alone (no portfolio
     linkage exists for Watchlist).
  3. dry_run=True (the default) leaves zero persisted rows of any kind.
  4. Re-running with the same run_id skips an already-COMPLETED shape.
  5. Idempotency independent of run_id: a second live run (fresh run_id)
     against already-backfilled rows reports zero additional writes.
  6. Every non-RESOLVED verdict is always reported as unresolved, in full,
     never silently dropped — and still_unresolved_transaction_count
     matches an independently-recomputed plan_migration() count.
  7. Duplicate alias symbols (two raw_symbols, one resolved asset) both
     backfill to the same asset_id without conflict.
  8. portfolio_ids scoping never touches another portfolio's rows.
  9. rollback_backfill() resets exactly the rows one run touched, is a
     no-op in dry_run, and never clobbers a value a later run legitimately
     wrote.
  10. Asset / AssetIdentifier / RegistryFinding are never touched — this
      module only ever reads Registry state, never writes it.
"""
import json
import os
import sys
from datetime import date, datetime, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from models.database import Base, PortfolioItem, Portfolio, Transaction, Watchlist, Workspace
import models.asset  # noqa: F401 — registers Asset* tables on Base.metadata
import models.registry_finding  # noqa: F401 — registers RegistryFinding table
import models.migration_execution  # noqa: F401 — registers MigrationExecutionCheckpoint table
import models.ledger_asset_backfill  # noqa: F401 — registers LedgerAssetBackfillCheckpoint table
from models.asset import Asset, AssetIdentifier
from models.ledger_asset_backfill import LedgerAssetBackfillCheckpoint
from models.registry_finding import RegistryFinding
from services import ledger_asset_backfill as backfill
from services import migration_planner as planner
from services import registry_service as svc
from services.asset_domain import AssetClaim, AssetType, IdentifierRecord, IdentifierType
from services.ledger_asset_backfill import BackfillOutcome
from services.replay_key import replay_key
from services.transaction_canonicalizer import CanonicalTransaction, canonicalize_transactions


def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _seed_portfolio(db, *, name="P1") -> Portfolio:
    ws = db.query(Workspace).first()
    if ws is None:
        ws = Workspace(name="default")
        db.add(ws)
        db.flush()
    p = Portfolio(workspace_id=ws.id, name=name, cash_balance=0.0)
    db.add(p)
    db.flush()
    return p


def _tx(db, portfolio, *, symbol, transaction_type="BUY", currency="THB") -> Transaction:
    tx = Transaction(
        workspace_id=portfolio.workspace_id,
        portfolio_id=portfolio.id,
        symbol=symbol,
        transaction_type=transaction_type,
        shares=100,
        price_per_share=10,
        total_amount=1000,
        fees=0,
        taxes=0,
        currency=currency,
        transaction_date=datetime.combine(date(2024, 1, 15), datetime.min.time()),
        created_at=datetime(2024, 1, 15, 9, 30, tzinfo=timezone.utc),
    )
    db.add(tx)
    db.flush()
    return tx


def _item(db, portfolio, *, symbol, shares=100, avg_cost=10.0) -> PortfolioItem:
    item = PortfolioItem(
        workspace_id=portfolio.workspace_id, portfolio_id=portfolio.id,
        symbol=symbol, shares=shares, avg_cost=avg_cost,
    )
    db.add(item)
    db.flush()
    return item


def _watchlist(db, workspace_id, *, symbol) -> Watchlist:
    wl = Watchlist(workspace_id=workspace_id, symbol=symbol)
    db.add(wl)
    db.flush()
    return wl


def _mint(db, canonical_symbol, *, currency="THB") -> Asset:
    return svc.mint_asset(
        db,
        AssetClaim(canonical_symbol=canonical_symbol, asset_type=AssetType.EQUITY, market="TH", exchange="SET", currency=currency),
    )


def _attach(db, asset, value) -> None:
    svc.attach_identifier(db, asset.id, IdentifierRecord(identifier_type=IdentifierType.PROVIDER_SYMBOL, value=value, source="seed"))


def _registry_row_counts(db) -> tuple:
    return (
        db.query(func.count(Asset.id)).scalar(),
        db.query(func.count(AssetIdentifier.id)).scalar(),
        db.query(func.count(RegistryFinding.id)).scalar(),
    )


# ── RESOLVED shape backfills ledger rows ────────────────────────────────

def test_resolved_shape_backfills_transaction_and_portfolio_item():
    db = make_session()
    p = _seed_portfolio(db)
    asset = _mint(db, "TESTCO")
    _attach(db, asset, "TESTCO")
    tx = _tx(db, p, symbol="TESTCO")
    item = _item(db, p, symbol="TESTCO")
    db.commit()

    plan = planner.plan_migration(db, portfolio_ids=[p.id])
    report = backfill.backfill_ledger_asset_ids(db, plan, run_id="run-1", dry_run=False)

    assert report.transactions_updated == 1
    assert report.portfolio_items_updated == 1
    assert report.steps[0].outcome == BackfillOutcome.COMPLETED

    db.refresh(tx)
    db.refresh(item)
    assert tx.asset_id == asset.id
    assert item.asset_id == asset.id

    checkpoints = db.query(LedgerAssetBackfillCheckpoint).filter_by(run_id="run-1").all()
    assert len(checkpoints) == 1
    cp = checkpoints[0]
    assert cp.status == "COMPLETED"
    assert cp.resolved_asset_id == asset.id
    assert json.loads(cp.transaction_ids_json) == [tx.id]
    assert json.loads(cp.portfolio_item_ids_json) == [item.id]


def test_watchlist_row_backfilled_by_symbol_match_alone():
    db = make_session()
    p = _seed_portfolio(db)
    asset = _mint(db, "TESTCO")
    _attach(db, asset, "TESTCO")
    _tx(db, p, symbol="TESTCO")
    wl = _watchlist(db, p.workspace_id, symbol="TESTCO")
    db.commit()

    plan = planner.plan_migration(db, portfolio_ids=[p.id])
    report = backfill.backfill_ledger_asset_ids(db, plan, run_id="run-1", dry_run=False)

    assert report.watchlist_rows_updated == 1
    db.refresh(wl)
    assert wl.asset_id == asset.id


def test_dry_run_leaves_zero_persisted_rows():
    db = make_session()
    p = _seed_portfolio(db)
    asset = _mint(db, "TESTCO")
    _attach(db, asset, "TESTCO")
    tx = _tx(db, p, symbol="TESTCO")
    item = _item(db, p, symbol="TESTCO")
    db.commit()

    plan = planner.plan_migration(db, portfolio_ids=[p.id])
    report = backfill.backfill_ledger_asset_ids(db, plan)  # dry_run=True default

    assert report.dry_run is True
    assert report.transactions_updated == 1  # reported as what WOULD happen
    assert report.portfolio_items_updated == 1
    assert db.query(func.count(LedgerAssetBackfillCheckpoint.id)).scalar() == 0

    db.refresh(tx)
    db.refresh(item)
    assert tx.asset_id is None
    assert item.asset_id is None


# ── Resumability & idempotency ──────────────────────────────────────────

def test_rerun_same_run_id_skips_already_completed_shape():
    db = make_session()
    p = _seed_portfolio(db)
    asset = _mint(db, "TESTCO")
    _attach(db, asset, "TESTCO")
    _tx(db, p, symbol="TESTCO")
    db.commit()

    plan = planner.plan_migration(db, portfolio_ids=[p.id])
    backfill.backfill_ledger_asset_ids(db, plan, run_id="run-1", dry_run=False)

    report2 = backfill.backfill_ledger_asset_ids(db, plan, run_id="run-1", dry_run=False)

    assert report2.transactions_updated == 0
    assert report2.steps[0].outcome == BackfillOutcome.SKIPPED_ALREADY_DONE
    checkpoints = db.query(LedgerAssetBackfillCheckpoint).filter_by(run_id="run-1").all()
    assert len(checkpoints) == 1  # no duplicate checkpoint row written


def test_idempotent_across_fresh_runs_with_no_shared_run_id():
    """Running backfill_ledger_asset_ids() twice against the same portfolio,
    under two DIFFERENT run_ids, produces zero additional writes the second
    time — idempotency does not depend on run_id resumption (§10.4)."""
    db = make_session()
    p = _seed_portfolio(db)
    asset = _mint(db, "TESTCO")
    _attach(db, asset, "TESTCO")
    _tx(db, p, symbol="TESTCO")
    db.commit()

    plan = planner.plan_migration(db, portfolio_ids=[p.id])
    report1 = backfill.backfill_ledger_asset_ids(db, plan, dry_run=False)
    assert report1.transactions_updated == 1

    plan2 = planner.plan_migration(db, portfolio_ids=[p.id])
    report2 = backfill.backfill_ledger_asset_ids(db, plan2, dry_run=False)  # fresh run_id
    assert report2.run_id != report1.run_id
    assert report2.transactions_updated == 0
    assert report2.portfolio_items_updated == 0
    assert report2.watchlist_rows_updated == 0


# ── Unresolved reporting ────────────────────────────────────────────────

def test_unresolved_shapes_are_always_reported_never_dropped():
    db = make_session()
    p = _seed_portfolio(db)

    # AMBIGUOUS setup (mirrors test_migration_planner.py's own scenario)
    asset_amb = _mint(db, "NVDA01")
    _attach(db, asset_amb, "NVDA01")
    _attach(db, asset_amb, "NVDA01-RENAMED")

    _tx(db, p, symbol="NVDA01", currency="USD")
    db.commit()

    plan = planner.plan_migration(db, portfolio_ids=[p.id])
    report = backfill.backfill_ledger_asset_ids(db, plan, dry_run=True)

    unresolved = backfill.unresolved_steps(report)
    assert len(unresolved) == 1
    assert unresolved[0].shape.raw_symbol == "NVDA01"
    assert report.still_unresolved_transaction_count == 1

    # Independently recomputed via a fresh plan_migration() — the same
    # number reported two different ways must agree (§10.4).
    fresh_plan = planner.plan_migration(db, portfolio_ids=[p.id])
    independent_unresolved = sum(
        len(r.transaction_ids) for r in fresh_plan.resolutions
        if r.result.verdict.value != "RESOLVED"
    )
    assert independent_unresolved == report.still_unresolved_transaction_count


# ── Duplicate aliases ────────────────────────────────────────────────────

def test_duplicate_alias_symbols_backfill_to_same_asset_id():
    db = make_session()
    p = _seed_portfolio(db)
    asset = _mint(db, "KBANK")
    _attach(db, asset, "KBANK")
    _attach(db, asset, "KBANK.BK")

    tx_a = _tx(db, p, symbol="KBANK")
    tx_b = _tx(db, p, symbol="KBANK.BK")
    item_a = _item(db, p, symbol="KBANK")
    item_b = _item(db, p, symbol="KBANK.BK")
    db.commit()

    plan = planner.plan_migration(db, portfolio_ids=[p.id])
    report = backfill.backfill_ledger_asset_ids(db, plan, dry_run=False)

    assert report.transactions_updated == 2
    assert report.portfolio_items_updated == 2

    for row in (tx_a, tx_b, item_a, item_b):
        db.refresh(row)
        assert row.asset_id == asset.id


# ── portfolio_ids scoping ───────────────────────────────────────────────

def test_portfolio_scoping_never_touches_other_portfolio():
    db = make_session()
    p1 = _seed_portfolio(db, name="P1")
    p2 = _seed_portfolio(db, name="P2")
    asset = _mint(db, "TESTCO")
    _attach(db, asset, "TESTCO")
    tx1 = _tx(db, p1, symbol="TESTCO")
    tx2 = _tx(db, p2, symbol="TESTCO")
    item1 = _item(db, p1, symbol="TESTCO")
    item2 = _item(db, p2, symbol="TESTCO")
    db.commit()

    plan = planner.plan_migration(db, portfolio_ids=[p1.id, p2.id])
    report = backfill.backfill_ledger_asset_ids(db, plan, portfolio_ids=[p1.id], dry_run=False)

    assert report.transactions_updated == 1
    assert report.portfolio_items_updated == 1

    db.refresh(tx1); db.refresh(tx2); db.refresh(item1); db.refresh(item2)
    assert tx1.asset_id == asset.id
    assert item1.asset_id == asset.id
    assert tx2.asset_id is None
    assert item2.asset_id is None


# ── Rollback ─────────────────────────────────────────────────────────────

def test_rollback_resets_exactly_the_rows_this_run_touched():
    db = make_session()
    p = _seed_portfolio(db)
    asset = _mint(db, "TESTCO")
    _attach(db, asset, "TESTCO")
    tx = _tx(db, p, symbol="TESTCO")
    item = _item(db, p, symbol="TESTCO")
    db.commit()

    plan = planner.plan_migration(db, portfolio_ids=[p.id])
    fwd = backfill.backfill_ledger_asset_ids(db, plan, run_id="run-1", dry_run=False)
    assert fwd.transactions_updated == 1

    rb = backfill.rollback_backfill(db, "run-1", dry_run=False)
    assert rb.transactions_reset == 1
    assert rb.portfolio_items_reset == 1

    db.refresh(tx)
    db.refresh(item)
    assert tx.asset_id is None
    assert item.asset_id is None


def test_rollback_dry_run_does_not_persist():
    db = make_session()
    p = _seed_portfolio(db)
    asset = _mint(db, "TESTCO")
    _attach(db, asset, "TESTCO")
    tx = _tx(db, p, symbol="TESTCO")
    db.commit()

    plan = planner.plan_migration(db, portfolio_ids=[p.id])
    backfill.backfill_ledger_asset_ids(db, plan, run_id="run-1", dry_run=False)

    rb = backfill.rollback_backfill(db, "run-1", dry_run=True)
    assert rb.transactions_reset == 1  # reported as what WOULD happen

    db.refresh(tx)
    assert tx.asset_id == asset.id  # unchanged — dry run


def test_rollback_never_clobbers_a_later_runs_write():
    db = make_session()
    p = _seed_portfolio(db)
    asset = _mint(db, "TESTCO")
    _attach(db, asset, "TESTCO")
    tx = _tx(db, p, symbol="TESTCO")
    db.commit()

    plan = planner.plan_migration(db, portfolio_ids=[p.id])
    backfill.backfill_ledger_asset_ids(db, plan, run_id="run-1", dry_run=False)

    # Simulate a later, independent write to the same row (e.g. a re-resolution).
    other_asset = _mint(db, "TESTCO-REPLACEMENT")
    tx.asset_id = other_asset.id
    db.commit()

    rb = backfill.rollback_backfill(db, "run-1", dry_run=False)
    assert rb.transactions_reset == 0  # current value no longer matches run-1's write

    db.refresh(tx)
    assert tx.asset_id == other_asset.id  # untouched


# ── Registry isolation (§10.6 "Ledger remains the single source of truth") ──

def test_backfill_never_writes_to_registry_tables():
    db = make_session()
    p = _seed_portfolio(db)
    asset = _mint(db, "TESTCO")
    _attach(db, asset, "TESTCO")
    _tx(db, p, symbol="TESTCO")
    db.commit()

    before = _registry_row_counts(db)
    plan = planner.plan_migration(db, portfolio_ids=[p.id])
    backfill.backfill_ledger_asset_ids(db, plan, dry_run=False)
    after = _registry_row_counts(db)

    assert before == after


# ── Golden Baseline parity: replay is byte-identical before/after backfill ──
#
# Stage 2's own Definition of Done requires "Replay behavior must remain
# identical" after backfill. Structural proof, not a sampled comparison:
# CanonicalTransaction (services/transaction_canonicalizer.py) has no
# asset_id field at all yet (confirmed by field inspection below), and
# _canonicalize_one() never reads tx.asset_id — so canonicalize_transactions()
# and replay_key() are provably incapable of observing whatever value
# Transaction.asset_id holds. This is the mechanical version of "Replay
# never re-resolves identity" (§10.6), specialized to Stage 2: replay
# doesn't merely avoid re-resolving identity, it cannot see Stage 2's
# column at all yet. Full rebuild_portfolio()-level parity (via
# registry_replay_parity.compare_against_baseline) is exercised separately
# in test_registry_replay_parity.py against the mocked-DB rebuild harness;
# it adds no further coverage here since rebuild_portfolio's replay path is
# entirely downstream of canonicalize_transactions()/replay_key(), both
# proven column-blind below.

def test_canonical_transaction_asset_id_defaults_to_none():
    """M5 Track B Stage 4 added CanonicalTransaction.asset_id (superseding
    this test's original Stage-2-era name/assertion, which checked the field
    didn't exist at all — see test_write_path_asset_id.py and
    test_replay_cutover.py for Stage 4's own coverage of the field). What
    remains true, and is the actual invariant this backfill module's
    zero-replay-impact guarantee depends on: constructing a
    CanonicalTransaction without prefer_asset_id=True — exactly what every
    call site in this file does — always yields asset_id=None, regardless
    of what the underlying Transaction.asset_id column holds."""
    field_names = {f for f in CanonicalTransaction.__dataclass_fields__}
    assert "asset_id" in field_names
    assert CanonicalTransaction.__dataclass_fields__["asset_id"].default is None


def test_canonicalization_and_replay_key_are_unaffected_by_backfilled_asset_id():
    db = make_session()
    p = _seed_portfolio(db)
    asset = _mint(db, "TESTCO")
    _attach(db, asset, "TESTCO")
    tx = _tx(db, p, symbol="TESTCO")
    db.commit()

    before_ctx = canonicalize_transactions([tx])[0]
    before_key = replay_key(before_ctx)

    plan = planner.plan_migration(db, portfolio_ids=[p.id])
    report = backfill.backfill_ledger_asset_ids(db, plan, dry_run=False)
    assert report.transactions_updated == 1
    db.refresh(tx)
    assert tx.asset_id == asset.id  # backfill genuinely wrote a new value

    after_ctx = canonicalize_transactions([tx])[0]
    after_key = replay_key(after_ctx)

    assert after_ctx == before_ctx  # dataclass equality — every field, byte-identical
    assert after_key == before_key
