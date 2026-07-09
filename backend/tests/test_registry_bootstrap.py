"""Tests for the Registry Bootstrap Executor (Milestone M5.3).

Validates:
  1. A mintable candidate mints a new asset, attaches its ledger-evidence
     identifier(s), and is checkpointed MINTED.
  2. Re-running with the same run_id skips an already-MINTED shape
     (idempotent resume) without touching the Registry again.
  3. dry_run=True (the default) leaves zero persisted rows of any kind.
  4. A mint-time identifier conflict (AssetRegistryError) blocks only the
     offending shape; the DUPLICATE_CLAIM finding survives (not rolled
     back), and every other candidate in the same run still mints normally
     (isolation proof) — mirrors test_migration_executor.py's own
     execute-time conflict test.
  5. Resume proof: re-running with the same run_id against a plan that now
     includes one additional mintable candidate only mints the new one.
  6. Transaction / PortfolioItem / PortfolioSnapshot are never touched,
     even by a live (non-dry-run) run.
  7. duplicate_blocked and quarantined shapes are carried through to the
     report unchanged, never minted.
  8. End-to-end validation (Q7 success criterion): bootstrapping a real
     ledger-derived UNKNOWN shape through the full plan_migration() ->
     build_bootstrap_plan() -> bootstrap_registry() pipeline makes a
     second plan_migration() run resolve that shape RESOLVED.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from models.database import Base, Portfolio, PortfolioItem, PortfolioSnapshot, Transaction, Workspace
import models.asset  # noqa: F401 — registers Asset* tables on Base.metadata
import models.registry_finding  # noqa: F401 — registers RegistryFinding table
import models.registry_bootstrap  # noqa: F401 — registers RegistryBootstrapCheckpoint table
from models.asset import Asset, AssetIdentifier
from models.registry_bootstrap import RegistryBootstrapCheckpoint
from models.registry_finding import RegistryFinding
from services import migration_planner as planner
from services import registry_bootstrap as bootstrap_executor
from services import registry_service as svc
from services.asset_domain import AssetClaim, AssetType, IdentifierRecord, IdentifierType
from services.bootstrap_planner import BootstrapPlan, MintCandidate, QuarantinedShape, build_bootstrap_plan
from services.migration_planner import ClaimShape
from services.migration_report import PotentialDuplicateCluster
from services.registry_bootstrap import BootstrapOutcome
from services.resolver_domain import ResolutionVerdict


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
    from datetime import date, datetime, timezone
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
        db.query(func.count(RegistryBootstrapCheckpoint.id)).scalar(),
    )


def _ledger_row_counts(db) -> tuple:
    return (
        db.query(func.count(Transaction.id)).scalar(),
        db.query(func.count(PortfolioItem.id)).scalar(),
        db.query(func.count(PortfolioSnapshot.id)).scalar(),
    )


def _shape(raw, canonical=None, currency="THB") -> ClaimShape:
    return ClaimShape(raw_symbol=raw, canonical_symbol=canonical, currency=currency)


def _candidate(raw_symbol, *, currency="THB", canonical_symbol=None, tx_ids=(1,)) -> MintCandidate:
    return MintCandidate(
        shape=_shape(raw_symbol, canonical=canonical_symbol, currency=currency),
        proposed_claim=AssetClaim(
            canonical_symbol=raw_symbol, asset_type=AssetType.EQUITY, market="Thailand", exchange="SET", currency=currency,
        ),
        transaction_ids=tuple(tx_ids),
    )


def _bplan(mintable=(), duplicate_blocked=(), quarantined=()) -> BootstrapPlan:
    from datetime import datetime, timezone
    return BootstrapPlan(
        mintable=tuple(mintable),
        duplicate_blocked=tuple(duplicate_blocked),
        quarantined=tuple(quarantined),
        generated_at=datetime(2026, 7, 9, tzinfo=timezone.utc),
    )


# ── Mintable execution ───────────────────────────────────────────────────

def test_mintable_candidate_mints_asset_and_checkpoints_minted():
    db = make_session()
    plan = _bplan(mintable=[_candidate("NEWCO.BK")])

    report = bootstrap_executor.bootstrap_registry(db, plan, run_id="run-1", dry_run=False)

    assert report.summary.minted == 1
    assert report.summary.blocked == 0
    assert report.steps[0].outcome == BootstrapOutcome.MINTED

    asset = db.query(Asset).filter_by(canonical_symbol="NEWCO.BK").first()
    assert asset is not None
    assert asset.market == "Thailand"
    assert asset.exchange == "SET"
    assert report.steps[0].minted_asset_id == asset.id

    identifiers = {i.value for i in svc.get_identifiers(db, asset.id, current_only=False)}
    assert "NEWCO.BK" in identifiers

    checkpoints = db.query(RegistryBootstrapCheckpoint).filter_by(run_id="run-1").all()
    assert len(checkpoints) == 1
    assert checkpoints[0].status == "MINTED"
    assert checkpoints[0].minted_asset_id == asset.id


def test_rerun_same_run_id_skips_already_minted_shape():
    db = make_session()
    plan = _bplan(mintable=[_candidate("NEWCO.BK")])
    bootstrap_executor.bootstrap_registry(db, plan, run_id="run-1", dry_run=False)

    before = _registry_row_counts(db)
    report2 = bootstrap_executor.bootstrap_registry(db, plan, run_id="run-1", dry_run=False)
    after = _registry_row_counts(db)

    assert before == after
    assert report2.summary.skipped_already_done == 1
    assert report2.summary.minted == 0
    assert report2.steps[0].outcome == BootstrapOutcome.SKIPPED_ALREADY_DONE

    checkpoints = db.query(RegistryBootstrapCheckpoint).filter_by(run_id="run-1").all()
    assert len(checkpoints) == 1  # no duplicate checkpoint row written


def test_dry_run_leaves_zero_persisted_rows():
    db = make_session()
    plan = _bplan(mintable=[_candidate("NEWCO.BK")])

    before = _registry_row_counts(db)
    report = bootstrap_executor.bootstrap_registry(db, plan)  # dry_run=True default
    after = _registry_row_counts(db)

    assert before == after
    assert report.dry_run is True
    assert report.summary.minted == 1  # reported as what WOULD happen


# ── Mint-time conflict isolation ────────────────────────────────────────

def test_mint_time_conflict_blocks_only_that_shape_and_preserves_finding():
    db = make_session()
    asset_a = _mint(db, "ASSETA")
    _attach(db, asset_a, "DUPCO")  # DUPCO already the current identifier on asset_a
    db.commit()

    plan = _bplan(mintable=[
        _candidate("DUPCO", tx_ids=(1,)),   # will conflict — DUPCO is live elsewhere
        _candidate("ZZZCO", tx_ids=(2,)),   # clean, sorted after DUPCO
    ])

    report = bootstrap_executor.bootstrap_registry(db, plan, run_id="run-1", dry_run=False)

    by_symbol = {s.shape.raw_symbol: s for s in report.steps}
    assert by_symbol["DUPCO"].outcome == BootstrapOutcome.BLOCKED
    assert by_symbol["DUPCO"].minted_asset_id is None
    assert by_symbol["ZZZCO"].outcome == BootstrapOutcome.MINTED

    # ZZZCO really did mint despite DUPCO's earlier failure.
    assert db.query(Asset).filter_by(canonical_symbol="ZZZCO").first() is not None

    # The duplicate-claim finding survived — not rolled back.
    findings = db.query(RegistryFinding).filter_by(finding_type="DUPLICATE_CLAIM").all()
    assert len(findings) == 1

    checkpoints = {c.raw_symbol: c for c in db.query(RegistryBootstrapCheckpoint).filter_by(run_id="run-1").all()}
    assert checkpoints["DUPCO"].status == "BLOCKED"
    assert checkpoints["DUPCO"].minted_asset_id is None
    assert checkpoints["ZZZCO"].status == "MINTED"


# ── Resume ───────────────────────────────────────────────────────────────

def test_resume_only_mints_newly_added_candidate():
    db = make_session()
    plan1 = _bplan(mintable=[_candidate("TESTCO.BK")])
    report1 = bootstrap_executor.bootstrap_registry(db, plan1, run_id="run-1", dry_run=False)
    assert report1.summary.minted == 1

    plan2 = _bplan(mintable=[_candidate("TESTCO.BK"), _candidate("NEWCO2.BK")])
    report2 = bootstrap_executor.bootstrap_registry(db, plan2, run_id="run-1", dry_run=False)

    by_symbol = {s.shape.raw_symbol: s for s in report2.steps}
    assert by_symbol["TESTCO.BK"].outcome == BootstrapOutcome.SKIPPED_ALREADY_DONE
    assert by_symbol["NEWCO2.BK"].outcome == BootstrapOutcome.MINTED

    testco_checkpoints = db.query(RegistryBootstrapCheckpoint).filter_by(run_id="run-1", raw_symbol="TESTCO.BK").all()
    assert len(testco_checkpoints) == 1  # not duplicated across the two invocations


# ── Ledger/Portfolio isolation ───────────────────────────────────────────

def test_live_bootstrap_never_touches_ledger_or_portfolio_tables():
    db = make_session()
    p = _seed_portfolio(db)
    _tx(db, p, symbol="NEWCO.BK")
    db.commit()

    plan = _bplan(mintable=[_candidate("NEWCO.BK")])

    before = _ledger_row_counts(db)
    bootstrap_executor.bootstrap_registry(db, plan, dry_run=False)
    after = _ledger_row_counts(db)

    assert before == after


# ── Duplicate-blocked / quarantined pass-through ────────────────────────

def test_duplicate_blocked_and_quarantined_are_reported_but_never_minted():
    db = make_session()
    cluster = PotentialDuplicateCluster(
        canonical_symbol="PTT.BK",
        raw_symbols=("PTTX", "PTTY"),
        claim_shapes=(_shape("PTTX", canonical="PTT.BK"), _shape("PTTY", canonical="PTT.BK")),
        transaction_ids=(1, 2),
    )
    quarantined_shape = QuarantinedShape(shape=_shape("GLIF"), reason="no known market/exchange convention", transaction_ids=(3,))
    plan = _bplan(mintable=[_candidate("AOT.BK", tx_ids=(4,))], duplicate_blocked=[cluster], quarantined=[quarantined_shape])

    report = bootstrap_executor.bootstrap_registry(db, plan, dry_run=False)

    assert report.summary.minted == 1
    assert report.summary.duplicate_blocked_clusters == 1
    assert report.summary.quarantined == 1
    assert report.duplicate_blocked == (cluster,)
    assert report.quarantined == (quarantined_shape,)
    assert db.query(Asset).filter_by(canonical_symbol="PTTX").first() is None
    assert db.query(Asset).filter_by(canonical_symbol="PTTY").first() is None
    assert db.query(Asset).filter_by(canonical_symbol="GLIF").first() is None


# ── End-to-end validation (Q7 success criterion) ─────────────────────────

def test_bootstrapped_symbol_resolves_on_next_plan_migration_run():
    db = make_session()
    p = _seed_portfolio(db)
    _tx(db, p, symbol="FRESHCO.BK")
    db.commit()

    plan1 = planner.plan_migration(db, portfolio_ids=[p.id])
    verdicts1 = {r.shape.raw_symbol: r.result.verdict for r in plan1.resolutions}
    assert verdicts1["FRESHCO.BK"] == ResolutionVerdict.UNKNOWN

    bootstrap_plan = build_bootstrap_plan(plan1)
    assert len(bootstrap_plan.mintable) == 1
    assert bootstrap_plan.mintable[0].shape.raw_symbol == "FRESHCO.BK"

    report = bootstrap_executor.bootstrap_registry(db, bootstrap_plan, dry_run=False)
    assert report.summary.minted == 1

    plan2 = planner.plan_migration(db, portfolio_ids=[p.id])
    verdicts2 = {r.shape.raw_symbol: r.result.verdict for r in plan2.resolutions}
    assert verdicts2["FRESHCO.BK"] == ResolutionVerdict.RESOLVED

    resolution2 = next(r for r in plan2.resolutions if r.shape.raw_symbol == "FRESHCO.BK")
    minted_asset_id = report.steps[0].minted_asset_id
    assert resolution2.result.resolved_asset_id == minted_asset_id
