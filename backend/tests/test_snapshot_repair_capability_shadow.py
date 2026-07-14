"""Stage R1 (M30.3 brief): snapshot_repair.py's shadow consultation of the
Asset Definition Runtime via _consult_runtime_for_repair(), plus the wiring
into _repair_one() (called by repair_snapshot_by_date() / repair_snapshot()).

Fourth portfolio-domain Stage R1 consumer, after portfolio_snapshots (M30.2),
portfolio_rebuilder, and portfolio_transactions. Mirrors them exactly:
read-only, never raises, never gates, never changes any computed value.

Only the quantity-valuation question is shadowed here — this module never
touches DIVIDEND transactions directly (return-series fields, including
period_dividend_income, are delegated to
snapshot_return_recovery._compute_return_fields() ->
portfolio_metrics.compute_period_metrics(), which is pure by construction
per ADR-004 and therefore out of scope for this DB-backed pattern).

Coverage:
  1. _consult_runtime_for_repair() in isolation — agreement / mismatch /
     missing-binding outcomes, plus the "symbol has no retrievable price"
     short-circuit (mirrors the M30.2 "price missing" test).
  2. repair_snapshot_by_date() end-to-end (real sqlite session, historical
     price fetch mocked) — RepairResult and the persisted PortfolioSnapshot
     row are unaffected whether the consultation agrees, disagrees, or
     raises outright.
"""
import asyncio
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base, Portfolio, PortfolioSnapshot, Workspace
import models.asset  # noqa: F401 — registers Asset* tables
import models.registry_finding  # noqa: F401 — registers RegistryFinding table

from services import asset_registry as registry
from services import capability_lookup_service as lookup_service
from services import registry_lookup
from services.asset_domain import AssetClaim, AssetType, IdentifierRecord, IdentifierType
from services.runtime_consultation import RuntimeFindingCategory
import services.snapshot_repair as repair_module
from services.snapshot_repair import (
    RepairStatus,
    _consult_runtime_for_repair,
    repair_snapshot_by_date,
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


def _mock_hist_prices(price_map: dict):
    async def _fake(symbols, date_str):
        return {sym: price_map.get(sym) for sym in symbols}
    return _fake


def _date(offset_days: int) -> str:
    return (datetime.utcnow() - timedelta(days=offset_days)).strftime("%Y-%m-%d")


def _make_snap(db, portfolio_id, workspace_id, snapshot_date, symbol, shares, avg_cost):
    import json
    holdings = [{
        "symbol": symbol, "shares": shares, "avg_cost": avg_cost,
        "current_price": avg_cost, "market_value": shares * avg_cost,
        "unrealized_pnl": 0.0, "unrealized_pnl_pct": 0.0, "sector": "Test",
    }]
    snap = PortfolioSnapshot(
        workspace_id=workspace_id, portfolio_id=portfolio_id, snapshot_date=snapshot_date,
        total_value=shares * avg_cost, cash_balance=0.0, total_invested=shares * avg_cost,
        holdings_json=json.dumps(holdings), holdings_count=1,
    )
    db.add(snap)
    db.commit()
    return snap


# ── 1. Quantity valuation: agreement / mismatch / missing binding ─────────

def test_quantity_valuation_agrees_for_equity():
    db = make_session()
    _mint_with_symbol(db, "SHADOW_EQ", AssetType.EQUITY)

    log = _consult_runtime_for_repair(db, ["SHADOW_EQ"], {"SHADOW_EQ": 10.0})

    assert log.consulted == 1
    assert log.agreements == 1
    assert log.findings == ()


def test_quantity_valuation_mismatches_for_cash():
    db = make_session()
    _mint_with_symbol(db, "SHADOW_CASH", AssetType.CASH)

    log = _consult_runtime_for_repair(db, ["SHADOW_CASH"], {"SHADOW_CASH": 1.0})

    assert log.consulted == 1
    assert log.agreements == 0
    assert len(log.findings) == 1
    finding = log.findings[0]
    assert finding.category == RuntimeFindingCategory.RUNTIME_MISMATCH.value
    assert finding.check_id == "RUNTIME_REPAIR_QUANTITY_VALUATION"
    assert finding.binding == "SHADOW_CASH"
    assert finding.legacy_result is True
    assert finding.runtime_result is False


def test_quantity_valuation_skipped_when_price_missing():
    """A symbol whose historical price could not be fetched never reaches
    the shares×price line in the legacy code, so there is no legacy
    decision to shadow."""
    db = make_session()
    _mint_with_symbol(db, "SHADOW_EQ", AssetType.EQUITY)

    log = _consult_runtime_for_repair(db, ["SHADOW_EQ"], {"SHADOW_EQ": None})

    assert log.consulted == 0
    assert log.findings == ()


def test_quantity_valuation_missing_binding_for_never_minted_symbol():
    db = make_session()

    log = _consult_runtime_for_repair(db, ["NEVER_MINTED"], {"NEVER_MINTED": 5.0})

    assert len(log.findings) == 1
    finding = log.findings[0]
    assert finding.category == RuntimeFindingCategory.MISSING_BINDING.value
    assert finding.detail == lookup_service._REASON_UNKNOWN_ASSET


def test_no_symbols_returns_empty_log():
    db = make_session()
    log = _consult_runtime_for_repair(db, [], {})
    assert log.consulted == 0
    assert log.findings == ()


# ── 2. Registry boot failure ───────────────────────────────────────────────

def test_registry_boot_failure_yields_missing_binding_never_raises():
    import services.asset_definitions.library as library

    db = make_session()
    _mint_with_symbol(db, "SHADOW_EQ", AssetType.EQUITY)

    original = dict(library.PINNED_FINGERPRINTS)
    try:
        library.PINNED_FINGERPRINTS[(AssetType.CASH.value, "v1")] = "0" * 64
        log = _consult_runtime_for_repair(db, ["SHADOW_EQ"], {"SHADOW_EQ": 10.0})
    finally:
        library.PINNED_FINGERPRINTS.clear()
        library.PINNED_FINGERPRINTS.update(original)

    assert len(log.findings) == 1
    assert log.findings[0].category == RuntimeFindingCategory.MISSING_BINDING.value
    assert log.findings[0].detail == lookup_service._REASON_REGISTRY_BOOT_FAILED


# ── 3. Integration: repair_snapshot_by_date() is unaffected end-to-end ────

def test_repair_unaffected_by_capability_mismatch(caplog):
    """A CASH-typed symbol (guaranteed quantity-valuation mismatch) must
    still repair to the true market value exactly as before — the shadow
    finding is logged, but never changes the repaired total_value."""
    db = make_session()
    _mint_with_symbol(db, "SHADOW_CASH", AssetType.CASH)
    ws, p = _seed(db, cash=0.0)
    snap = _make_snap(db, p.id, ws.id, _date(3), "SHADOW_CASH", shares=1000, avg_cost=50.0)

    with patch(
        "services.snapshot_repair.fetch_historical_prices",
        side_effect=_mock_hist_prices({"SHADOW_CASH": 80.0}),
    ):
        with caplog.at_level("WARNING", logger="services.snapshot_repair"):
            result = asyncio.run(repair_snapshot_by_date(db, p.id, ws.id, snap.snapshot_date))

    assert result.status == RepairStatus.REPAIRED
    assert result.new_total_value == pytest.approx(80_000.0, abs=1)
    assert any("RUNTIME_REPAIR_QUANTITY_VALUATION" in r.message for r in caplog.records)

    updated = db.query(PortfolioSnapshot).filter_by(id=snap.id).first()
    assert updated.total_value == pytest.approx(80_000.0, abs=1)


def test_repair_succeeds_even_when_capability_consultation_raises(monkeypatch):
    """Mirrors the same never-raises-out-of-caller proof used by every other
    Stage R1 consumer: even if the consultation itself raised unexpectedly,
    _repair_one() must swallow it and still complete successfully."""
    def _boom(db, unique_symbols, price_map):
        raise RuntimeError("simulated unexpected failure")

    monkeypatch.setattr(repair_module, "_consult_runtime_for_repair", _boom)

    db = make_session()
    ws, p = _seed(db, cash=0.0)
    snap = _make_snap(db, p.id, ws.id, _date(1), "BOOM.BK", shares=100, avg_cost=10.0)

    with patch(
        "services.snapshot_repair.fetch_historical_prices",
        side_effect=_mock_hist_prices({"BOOM.BK": 15.0}),
    ):
        result = asyncio.run(repair_snapshot_by_date(db, p.id, ws.id, snap.snapshot_date))

    assert result.status == RepairStatus.REPAIRED
    assert result.new_total_value == pytest.approx(1_500.0, abs=1)
