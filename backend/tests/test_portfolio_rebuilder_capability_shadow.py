"""Stage R1 (M30.3 brief): portfolio_rebuilder.py's shadow consultation of
the Asset Definition Runtime via _consult_runtime_for_rebuild(), plus the
wiring into rebuild_portfolio() itself.

Third portfolio-domain Stage R1 consumer, after portfolio_snapshots (M30.2).
Mirrors it exactly: read-only, never raises, never gates, never changes any
computed value. Batched (capability_lookup_service.resolve_capability_views),
consulted once per rebuild run rather than once per transaction/holding —
_apply_transaction() itself stays pure and untouched (it is called inside a
per-transaction, per-snapshot-date hot loop; a per-call DB consultation
there would be both a purity violation and a performance regression).

Coverage:
  1. _consult_runtime_for_rebuild() in isolation — agreement / mismatch /
     missing-binding outcomes for both questions this module shadows
     (quantity valuation, dividend flow), plus the skip_snapshots=True
     short-circuit (no valuation formula runs at all in that mode) and the
     no-holdings/no-dividends empty case.
  2. rebuild_portfolio() end-to-end (dry_run=True, skip_snapshots=True,
     real sqlite session) — RebuildResult is unaffected whether the
     consultation agrees, disagrees, or raises outright.
"""
import asyncio
import os
import sys
from datetime import date, datetime
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base, Portfolio, Transaction, Workspace
import models.asset  # noqa: F401 — registers Asset* tables
import models.registry_finding  # noqa: F401 — registers RegistryFinding table

from services import asset_registry as registry
from services import capability_lookup_service as lookup_service
from services import registry_lookup
from services.asset_domain import AssetClaim, AssetType, IdentifierRecord, IdentifierType
from services.runtime_consultation import RuntimeFindingCategory
from services.transaction_canonicalizer import CanonicalTransaction
import services.portfolio_rebuilder as rebuild_module
from services.portfolio_rebuilder import (
    _HoldingState,
    _PortfolioState,
    _consult_runtime_for_rebuild,
    rebuild_portfolio,
)


# ── Fixtures / helpers ────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _reset_cache():
    registry_lookup.invalidate_cache()
    yield
    registry_lookup.invalidate_cache()


def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _seed(db, cash: float = 0.0):
    ws = Workspace(name="Test")
    db.add(ws)
    db.flush()
    p = Portfolio(workspace_id=ws.id, name="Test", cash_balance=cash)
    db.add(p)
    db.commit()
    return ws, p


def _mint_with_symbol(db, symbol, asset_type):
    claim = AssetClaim(canonical_symbol=symbol, asset_type=asset_type, market="TH", exchange="SET", currency="THB")
    return registry.mint(
        db, claim,
        identifiers=(IdentifierRecord(identifier_type=IdentifierType.PROVIDER_SYMBOL, value=symbol, source="test"),),
    )


def _state_with_holding(symbol: str) -> _PortfolioState:
    return _PortfolioState(
        cash_balance=Decimal("0"),
        holdings={symbol: _HoldingState(
            symbol=symbol, report_symbol=symbol,
            shares=Decimal("10"), avg_cost=Decimal("1"),
        )},
        cumulative_realized_pnl=Decimal("0"),
    )


def _dividend_ctx(id_: int, symbol: str) -> CanonicalTransaction:
    return CanonicalTransaction(
        id=id_, transaction_type="DIVIDEND", raw_symbol=symbol, canonical_symbol=symbol,
        shares=Decimal("0"), price_per_share=Decimal("0"), total_amount=Decimal("100"),
        fees=Decimal("0"), taxes=Decimal("0"), transaction_date=date.today(),
        created_at=datetime.utcnow(), sector=None, notes=None,
        qty_correction_delta=None, realized_pnl=None,
    )


# ── 1. Quantity valuation: agreement / mismatch / missing binding ─────────

def test_quantity_valuation_agrees_for_equity():
    db = make_session()
    _mint_with_symbol(db, "SHADOW_EQ", AssetType.EQUITY)

    log = _consult_runtime_for_rebuild(db, _state_with_holding("SHADOW_EQ"), [], skip_snapshots=False)

    assert log.consulted == 1
    assert log.agreements == 1
    assert log.findings == ()


def test_quantity_valuation_mismatches_for_cash():
    db = make_session()
    _mint_with_symbol(db, "SHADOW_CASH", AssetType.CASH)

    log = _consult_runtime_for_rebuild(db, _state_with_holding("SHADOW_CASH"), [], skip_snapshots=False)

    assert log.consulted == 1
    assert log.agreements == 0
    assert len(log.findings) == 1
    finding = log.findings[0]
    assert finding.category == RuntimeFindingCategory.RUNTIME_MISMATCH.value
    assert finding.check_id == "RUNTIME_REBUILD_QUANTITY_VALUATION"
    assert finding.binding == "SHADOW_CASH"
    assert finding.legacy_result is True
    assert finding.runtime_result is False


def test_quantity_valuation_skipped_when_skip_snapshots_true():
    """No valuation formula runs at all when skip_snapshots=True (Stages 2-3
    never execute), so there is no legacy decision to shadow."""
    db = make_session()
    _mint_with_symbol(db, "SHADOW_EQ", AssetType.EQUITY)

    log = _consult_runtime_for_rebuild(db, _state_with_holding("SHADOW_EQ"), [], skip_snapshots=True)

    assert log.consulted == 0
    assert log.findings == ()


def test_quantity_valuation_missing_binding_for_never_minted_symbol():
    db = make_session()

    log = _consult_runtime_for_rebuild(db, _state_with_holding("NEVER_MINTED"), [], skip_snapshots=False)

    assert len(log.findings) == 1
    finding = log.findings[0]
    assert finding.category == RuntimeFindingCategory.MISSING_BINDING.value
    assert finding.detail == lookup_service._REASON_UNKNOWN_ASSET


# ── 2. Dividend flow: agreement / mismatch ─────────────────────────────────

def test_dividend_flow_agrees_for_equity():
    db = make_session()
    _mint_with_symbol(db, "SHADOW_EQ", AssetType.EQUITY)
    empty_state = _PortfolioState(cash_balance=Decimal("0"), holdings={}, cumulative_realized_pnl=Decimal("0"))

    log = _consult_runtime_for_rebuild(db, empty_state, [_dividend_ctx(1, "SHADOW_EQ")], skip_snapshots=True)

    assert log.consulted == 1
    assert log.agreements == 1
    assert log.findings == ()


def test_dividend_flow_mismatches_for_bond():
    """BOND grants FlowType.COUPON, not DIVIDEND — but _apply_transaction()
    credits cash_balance for any DIVIDEND transaction unconditionally.
    Consulted even when skip_snapshots=True (replay always runs)."""
    db = make_session()
    _mint_with_symbol(db, "SHADOW_BOND", AssetType.BOND)
    empty_state = _PortfolioState(cash_balance=Decimal("0"), holdings={}, cumulative_realized_pnl=Decimal("0"))

    log = _consult_runtime_for_rebuild(db, empty_state, [_dividend_ctx(7, "SHADOW_BOND")], skip_snapshots=True)

    assert log.consulted == 1
    assert log.agreements == 0
    assert len(log.findings) == 1
    finding = log.findings[0]
    assert finding.category == RuntimeFindingCategory.RUNTIME_MISMATCH.value
    assert finding.check_id == "RUNTIME_REBUILD_DIVIDEND_FLOW"
    assert finding.transaction_ids == (7,)
    assert finding.runtime_result is False


def test_no_holdings_no_dividends_returns_empty_log():
    db = make_session()
    empty_state = _PortfolioState(cash_balance=Decimal("0"), holdings={}, cumulative_realized_pnl=Decimal("0"))

    log = _consult_runtime_for_rebuild(db, empty_state, [], skip_snapshots=False)

    assert log.consulted == 0
    assert log.agreements == 0
    assert log.findings == ()


# ── 3. Registry boot failure ───────────────────────────────────────────────

def test_registry_boot_failure_yields_missing_binding_never_raises():
    import services.asset_definitions.library as library

    db = make_session()
    _mint_with_symbol(db, "SHADOW_EQ", AssetType.EQUITY)

    original = dict(library.PINNED_FINGERPRINTS)
    try:
        library.PINNED_FINGERPRINTS[(AssetType.CASH.value, "v1")] = "0" * 64
        log = _consult_runtime_for_rebuild(db, _state_with_holding("SHADOW_EQ"), [], skip_snapshots=False)
    finally:
        library.PINNED_FINGERPRINTS.clear()
        library.PINNED_FINGERPRINTS.update(original)

    assert len(log.findings) == 1
    assert log.findings[0].category == RuntimeFindingCategory.MISSING_BINDING.value
    assert log.findings[0].detail == lookup_service._REASON_REGISTRY_BOOT_FAILED


# ── 4. Integration: rebuild_portfolio() is unaffected end-to-end ──────────

def _run_rebuild(db, portfolio_id, workspace_id):
    return asyncio.run(rebuild_portfolio(
        db, portfolio_id, workspace_id,
        skip_snapshots=True, dry_run=True,
    ))


def test_rebuild_result_unaffected_by_capability_mismatch(caplog):
    """A CASH-typed symbol (guaranteed quantity-valuation mismatch is not
    reachable with skip_snapshots=True, but the DIVIDEND-flow mismatch is)
    must still replay exactly as before — the shadow finding is logged,
    never enforced, never changes RebuildResult."""
    db = make_session()
    _mint_with_symbol(db, "SHADOW_BOND", AssetType.BOND)
    ws, p = _seed(db, cash=0.0)
    db.add(Transaction(
        workspace_id=ws.id, portfolio_id=p.id, symbol="SHADOW_BOND",
        transaction_type="DIVIDEND", shares=0, price_per_share=0,
        total_amount=25.0, fees=0.0, taxes=0.0,
        transaction_date=datetime.utcnow(), created_at=datetime.utcnow(),
    ))
    db.commit()

    with caplog.at_level("WARNING", logger="services.portfolio_rebuilder"):
        result = _run_rebuild(db, p.id, ws.id)

    assert result.success is True
    assert result.reconstructed_cash == pytest.approx(25.0)
    assert any("RUNTIME_REBUILD_DIVIDEND_FLOW" in r.message for r in caplog.records)


def test_rebuild_succeeds_even_when_capability_consultation_raises(monkeypatch):
    """Mirrors the same never-raises-out-of-caller proof used by every other
    Stage R1 consumer: even if the consultation itself raised unexpectedly,
    rebuild_portfolio() must swallow it and still complete successfully."""
    def _boom(db, final_state, all_txs, skip_snapshots):
        raise RuntimeError("simulated unexpected failure")

    monkeypatch.setattr(rebuild_module, "_consult_runtime_for_rebuild", _boom)

    db = make_session()
    ws, p = _seed(db, cash=0.0)
    db.add(Transaction(
        workspace_id=ws.id, portfolio_id=p.id, symbol="BOOM.BK",
        transaction_type="BUY", shares=10, price_per_share=2.0,
        total_amount=20.0, fees=0.0, taxes=0.0,
        transaction_date=datetime.utcnow(), created_at=datetime.utcnow(),
    ))
    db.commit()

    result = _run_rebuild(db, p.id, ws.id)

    assert result.success is True
    assert result.reconstructed_holdings_count == 1
