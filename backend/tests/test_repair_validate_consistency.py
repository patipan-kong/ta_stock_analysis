"""Single-source-of-truth regression test — apply_repair vs validate_ledger.

Both `manage.py apply_repair` and `manage.py validate_ledger --effective` /
`--compare` must derive their findings from the exact same code path:
services.ledger_validator.validate_portfolio_ledger(mode="effective").

repair_plan_executor.py has no private replay logic of its own — it only
calls validate_portfolio_ledger() (imported, never reimplemented). This test
proves that invariant end-to-end against a real database: a repair plan
applied for real (committed, not dry-run) produces an effective_after report
that is byte-for-byte identical (by finding key + severity) to a report
computed independently afterwards, in a fresh session, via
compare_ledger_validation() — the same call validate_ledger --compare uses.

Uses a real in-memory SQLite database (not mocks) so the comparison is
meaningful: mocked validate_portfolio_ledger (as in
test_ledger_repair_executor.py) cannot detect a divergence between the two
call sites.
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base, LedgerRepair, Portfolio, Transaction, Workspace
from services.ledger_repair import load_active_repairs
from services.ledger_validator import _finding_key, compare_ledger_validation
from services.repair_plan_executor import RepairPlan, RepairPlanOperation, apply_repair_plan


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def seeded_portfolio(db_session):
    """One portfolio with a duplicate INITIAL_POSITION (triggers DUP_INITIAL_POSITION CRITICAL)."""
    ws = Workspace(id=1, name="Default")
    db_session.add(ws)

    created_at = datetime(2026, 1, 1)
    portfolio = Portfolio(
        id=1, workspace_id=1, name="Test Portfolio",
        cash_balance=0.0, created_at=created_at,
    )
    db_session.add(portfolio)

    tx_date = datetime(2026, 2, 1)
    tx1 = Transaction(
        id=10, workspace_id=1, portfolio_id=1, symbol="GULF.BK",
        transaction_type="INITIAL_POSITION", shares=100, price_per_share=10,
        total_amount=1000, fees=0, taxes=0, transaction_date=tx_date,
        created_at=tx_date,
    )
    tx2 = Transaction(
        id=11, workspace_id=1, portfolio_id=1, symbol="GULF.BK",
        transaction_type="INITIAL_POSITION", shares=100, price_per_share=10,
        total_amount=1000, fees=0, taxes=0, transaction_date=tx_date,
        created_at=tx_date,
    )
    db_session.add_all([tx1, tx2])
    db_session.commit()
    return db_session


def test_apply_repair_commit_matches_independent_compare(seeded_portfolio):
    """After a real (non-dry-run) apply, a fresh compare_ledger_validation() call
    must report the exact same effective findings apply_repair_plan returned.
    """
    db = seeded_portfolio

    plan = RepairPlan(
        schema_version="1.0",
        portfolio_id=1,
        repair_plan_id="plan-consistency-001",
        generated_at="2026-02-02T00:00:00Z",
        operations=[RepairPlanOperation(
            repair_type="EXCLUDE",
            transaction_id=11,
            reason="Duplicate INITIAL_POSITION, keep tx10",
            reason_code="DUP_INITIAL_POSITION",
        )],
    )

    with patch("services.repair_plan_executor._backup_repairs", return_value="/tmp/fake-backup.json"):
        result = asyncio.run(apply_repair_plan(
            db=db, plan=plan, portfolio_id=1, workspace_id=1,
            dry_run=False, force=True,
        ))

    assert result.error is None
    assert result.rollback is False
    assert result.operations_inserted == 1
    assert result.effective_after is not None

    # Independently re-derive the effective report the same way
    # `manage.py validate_ledger --compare --effective` does: load the
    # now-committed repairs in a fresh query and run compare_ledger_validation().
    repairs = load_active_repairs(db, 1)
    assert len(repairs) == 1
    assert isinstance(repairs[0], LedgerRepair)

    comparison = asyncio.run(compare_ledger_validation(
        db=db, portfolio_id=1, workspace_id=1, repairs=repairs,
    ))

    apply_keys = {_finding_key(f) for f in result.effective_after.findings}
    compare_keys = {_finding_key(f) for f in comparison.effective_report.findings}
    assert apply_keys == compare_keys

    apply_sev = {_finding_key(f): f.severity for f in result.effective_after.findings}
    compare_sev = {_finding_key(f): f.severity for f in comparison.effective_report.findings}
    assert apply_sev == compare_sev

    # The duplicate INITIAL_POSITION finding must be resolved in both views.
    dup_key_prefix = "DUP_INITIAL_POSITION:"
    assert not any(k.startswith(dup_key_prefix) for k in apply_keys)
    assert not any(k.startswith(dup_key_prefix) for k in compare_keys)
    assert any(k.startswith(dup_key_prefix) for k in comparison.resolved_findings)
