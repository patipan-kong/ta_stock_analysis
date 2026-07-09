"""Tests for the Migration Execution Framework (Milestone M5.2).

Validates:
  1. A RESOLVED claim shape attaches its identifier(s) to the correct asset
     and is checkpointed COMPLETED.
  2. Re-running with the same run_id skips an already-COMPLETED shape
     (idempotent resume) without touching the Registry again.
  3. dry_run=True (the default) leaves zero persisted rows of any kind.
  4. Every non-RESOLVED verdict (CANDIDATE/AMBIGUOUS/CONFLICT/UNKNOWN) is
     always skipped, never acted on — zero Registry writes.
  5. An execute-time identifier conflict blocks only the offending shape;
     the conflict finding survives (not rolled back), and every other shape
     in the same run still executes normally (isolation proof).
  6. Resume proof: re-running with the same run_id against a plan that now
     includes one additional RESOLVED shape only executes the new shape.
  7. Transaction / PortfolioItem / PortfolioSnapshot are never touched, even
     by a live (non-dry-run) execution.
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
import models.migration_execution  # noqa: F401 — registers MigrationExecutionCheckpoint table
from models.asset import Asset, AssetIdentifier
from models.migration_execution import MigrationExecutionCheckpoint
from models.registry_finding import RegistryFinding
from services import migration_executor as executor
from services import migration_planner as planner
from services import registry_service as svc
from services.asset_domain import AssetClaim, AssetType, IdentifierRecord, IdentifierType
from services.migration_executor import ExecutionOutcome
from services.migration_planner import CashOnlyGroup, ClaimShape, ClaimShapeResolution, MigrationPlan
from services.resolver_domain import ResolutionCandidate, ResolutionResult, ResolutionVerdict


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
        db.query(func.count(MigrationExecutionCheckpoint.id)).scalar(),
    )


def _ledger_row_counts(db) -> tuple:
    return (
        db.query(func.count(Transaction.id)).scalar(),
        db.query(func.count(PortfolioItem.id)).scalar(),
        db.query(func.count(PortfolioSnapshot.id)).scalar(),
    )


def _shape(raw, canonical=None, currency="THB") -> ClaimShape:
    return ClaimShape(raw_symbol=raw, canonical_symbol=canonical, currency=currency)


def _resolved_result(asset_id) -> ResolutionResult:
    return ResolutionResult(
        verdict=ResolutionVerdict.RESOLVED,
        resolved_asset_id=asset_id,
        candidates=(ResolutionCandidate(asset_id=asset_id, score=100.0, contributions=()),),
        claim_evaluations=(),
    )


def _non_resolved_result(verdict, candidates=()) -> ResolutionResult:
    return ResolutionResult(verdict=verdict, resolved_asset_id=None, candidates=tuple(candidates), claim_evaluations=())


def _resolution(shape, result, tx_ids=(1,)) -> ClaimShapeResolution:
    return ClaimShapeResolution(shape=shape, result=result, transaction_ids=tuple(tx_ids), portfolio_ids=(1,))


def _plan(resolutions) -> MigrationPlan:
    from datetime import datetime, timezone
    total = sum(len(r.transaction_ids) for r in resolutions)
    return MigrationPlan(
        resolutions=tuple(resolutions),
        cash_only=CashOnlyGroup(transaction_ids=(), portfolio_ids=()),
        total_transactions=total,
        portfolios_scanned=(1,),
        generated_at=datetime(2026, 7, 9, tzinfo=timezone.utc),
    )


# ── RESOLVED execution ───────────────────────────────────────────────────

def test_resolved_shape_attaches_identifier_and_checkpoints_completed():
    db = make_session()
    p = _seed_portfolio(db)
    asset = _mint(db, "TESTCO")
    _attach(db, asset, "TESTCO")
    _tx(db, p, symbol="TESTCO")
    db.commit()

    plan = planner.plan_migration(db, portfolio_ids=[p.id])
    report = executor.execute_migration(db, plan, run_id="run-1", dry_run=False)

    assert report.summary.completed == 1
    assert report.summary.blocked == 0
    assert report.steps[0].outcome == ExecutionOutcome.COMPLETED

    # build_claim bundles raw_symbol "TESTCO" with its listing-equivalent
    # canonical_symbol "TESTCO.BK" (same_listing venue-suffix rule): both get
    # attached, and per core.attach_identifier's single-current-per-type
    # model, attaching "TESTCO.BK" second supersedes "TESTCO" as current —
    # "TESTCO" is retained historically, never deleted.
    assert report.steps[0].identifiers_attached == 2
    all_identifiers = {i.value for i in svc.get_identifiers(db, asset.id, current_only=False)}
    assert {"TESTCO", "TESTCO.BK"} <= all_identifiers
    current_identifiers = {i.value for i in svc.get_identifiers(db, asset.id, current_only=True)}
    assert current_identifiers == {"TESTCO.BK"}

    checkpoints = db.query(MigrationExecutionCheckpoint).filter_by(run_id="run-1").all()
    assert len(checkpoints) == 1
    assert checkpoints[0].status == "COMPLETED"
    assert checkpoints[0].resolved_asset_id == asset.id


def test_rerun_same_run_id_skips_already_completed_shape():
    db = make_session()
    p = _seed_portfolio(db)
    asset = _mint(db, "TESTCO")
    _attach(db, asset, "TESTCO")
    _tx(db, p, symbol="TESTCO")
    db.commit()

    plan = planner.plan_migration(db, portfolio_ids=[p.id])
    executor.execute_migration(db, plan, run_id="run-1", dry_run=False)

    before = _registry_row_counts(db)
    report2 = executor.execute_migration(db, plan, run_id="run-1", dry_run=False)
    after = _registry_row_counts(db)

    assert before == after
    assert report2.summary.skipped_already_done == 1
    assert report2.summary.completed == 0
    assert report2.steps[0].outcome == ExecutionOutcome.SKIPPED_ALREADY_DONE

    checkpoints = db.query(MigrationExecutionCheckpoint).filter_by(run_id="run-1").all()
    assert len(checkpoints) == 1  # no duplicate checkpoint row written


def test_dry_run_leaves_zero_persisted_rows():
    db = make_session()
    p = _seed_portfolio(db)
    asset = _mint(db, "TESTCO")
    _attach(db, asset, "TESTCO")
    _tx(db, p, symbol="TESTCO")
    db.commit()

    plan = planner.plan_migration(db, portfolio_ids=[p.id])

    before = _registry_row_counts(db)
    report = executor.execute_migration(db, plan)  # dry_run=True default
    after = _registry_row_counts(db)

    assert before == after
    assert report.dry_run is True
    assert report.summary.completed == 1  # reported as what WOULD happen


# ── Non-RESOLVED verdicts are always skipped ────────────────────────────

def test_ambiguous_and_conflict_and_unknown_are_never_executed():
    db = make_session()
    p = _seed_portfolio(db)

    # AMBIGUOUS setup (mirrors test_migration_planner.py's own scenario)
    asset_amb = _mint(db, "NVDA01")
    _attach(db, asset_amb, "NVDA01")
    _attach(db, asset_amb, "NVDA01-RENAMED")

    # CONFLICT setup
    asset_a = _mint(db, "KBANK-A")
    asset_b = _mint(db, "KBANK-B")
    _attach(db, asset_a, "KBANK")
    _attach(db, asset_b, "KBANK.BK")

    _tx(db, p, symbol="NVDA01", currency="USD")
    _tx(db, p, symbol="KBANK")
    _tx(db, p, symbol="NEWCO")  # UNKNOWN
    db.commit()

    plan = planner.plan_migration(db, portfolio_ids=[p.id])
    verdicts = {r.shape.raw_symbol: r.result.verdict for r in plan.resolutions}
    assert verdicts["NVDA01"] == ResolutionVerdict.AMBIGUOUS
    assert verdicts["KBANK"] == ResolutionVerdict.CONFLICT
    assert verdicts["NEWCO"] == ResolutionVerdict.UNKNOWN

    before = _registry_row_counts(db)
    report = executor.execute_migration(db, plan, dry_run=False)
    after = _registry_row_counts(db)

    assert before == after  # zero Registry writes despite dry_run=False
    assert report.summary.skipped_not_resolved == 3
    assert report.summary.completed == 0
    assert all(s.outcome == ExecutionOutcome.SKIPPED_NOT_RESOLVED for s in report.steps)


def test_candidate_verdict_is_skipped_via_hand_built_fixture():
    # CANDIDATE is structurally unreachable from real ledger evidence (see
    # migration_planner.py / test_migration_report.py) — hand-built fixture,
    # same pattern test_migration_report.py already uses for this verdict.
    db = make_session()
    plan = _plan([_resolution(_shape("NEWISSUE"), _non_resolved_result(ResolutionVerdict.CANDIDATE))])

    report = executor.execute_migration(db, plan, dry_run=False)

    assert report.summary.skipped_not_resolved == 1
    assert report.steps[0].outcome == ExecutionOutcome.SKIPPED_NOT_RESOLVED
    assert db.query(func.count(MigrationExecutionCheckpoint.id)).scalar() == 0


# ── Execute-time conflict isolation ─────────────────────────────────────

def test_execute_time_conflict_blocks_only_that_shape_and_preserves_finding():
    # Simulates a stale plan: the plan claims "KBANK" resolves to asset_b,
    # but asset_a is actually the current holder in the Registry (as if the
    # plan were computed before, and the Registry changed after). Also
    # includes a second, cleanly-resolvable shape sorted AFTER "KBANK"
    # alphabetically, to prove one blocked shape never stops the next one.
    db = make_session()
    asset_a = _mint(db, "ASSETA")
    asset_b = _mint(db, "ASSETB")
    _attach(db, asset_a, "KBANK")  # KBANK is genuinely current on asset_a
    db.commit()

    stale_plan = _plan([
        _resolution(_shape("KBANK"), _resolved_result(asset_b.id), tx_ids=[1]),   # wrong — will conflict
        _resolution(_shape("NEWCO"), _resolved_result(asset_b.id), tx_ids=[2]),   # clean
    ])

    report = executor.execute_migration(db, stale_plan, run_id="run-1", dry_run=False)

    by_symbol = {s.shape.raw_symbol: s for s in report.steps}
    assert by_symbol["KBANK"].outcome == ExecutionOutcome.BLOCKED
    assert by_symbol["NEWCO"].outcome == ExecutionOutcome.COMPLETED

    # NEWCO's identifier really did attach despite KBANK's earlier failure.
    newco_identifiers = svc.get_identifiers(db, asset_b.id, current_only=True)
    assert any(i.value == "NEWCO" for i in newco_identifiers)

    # The conflict finding survived — not rolled back.
    findings = db.query(RegistryFinding).filter_by(finding_type="IDENTIFIER_CONFLICT").all()
    assert len(findings) == 1

    checkpoints = {c.raw_symbol: c for c in db.query(MigrationExecutionCheckpoint).filter_by(run_id="run-1").all()}
    assert checkpoints["KBANK"].status == "BLOCKED"
    assert checkpoints["NEWCO"].status == "COMPLETED"


# ── Resume ───────────────────────────────────────────────────────────────

def test_resume_only_executes_newly_added_shape():
    db = make_session()
    p = _seed_portfolio(db)
    asset1 = _mint(db, "TESTCO")
    _attach(db, asset1, "TESTCO")
    _tx(db, p, symbol="TESTCO")
    db.commit()

    plan1 = planner.plan_migration(db, portfolio_ids=[p.id])
    report1 = executor.execute_migration(db, plan1, run_id="run-1", dry_run=False)
    assert report1.summary.completed == 1

    asset2 = _mint(db, "NEWCO2")
    _attach(db, asset2, "NEWCO2")
    _tx(db, p, symbol="NEWCO2")
    db.commit()

    plan2 = planner.plan_migration(db, portfolio_ids=[p.id])
    assert len(plan2.resolutions) == 2  # TESTCO + NEWCO2

    report2 = executor.execute_migration(db, plan2, run_id="run-1", dry_run=False)
    by_symbol = {s.shape.raw_symbol: s for s in report2.steps}
    assert by_symbol["TESTCO"].outcome == ExecutionOutcome.SKIPPED_ALREADY_DONE
    assert by_symbol["NEWCO2"].outcome == ExecutionOutcome.COMPLETED

    testco_checkpoints = db.query(MigrationExecutionCheckpoint).filter_by(run_id="run-1", raw_symbol="TESTCO").all()
    assert len(testco_checkpoints) == 1  # not duplicated across the two invocations


# ── Ledger/Portfolio isolation ───────────────────────────────────────────

def test_live_execution_never_touches_ledger_or_portfolio_tables():
    db = make_session()
    p = _seed_portfolio(db)
    asset = _mint(db, "TESTCO")
    _attach(db, asset, "TESTCO")
    _tx(db, p, symbol="TESTCO")
    db.commit()

    plan = planner.plan_migration(db, portfolio_ids=[p.id])

    before = _ledger_row_counts(db)
    executor.execute_migration(db, plan, dry_run=False)
    after = _ledger_row_counts(db)

    assert before == after
