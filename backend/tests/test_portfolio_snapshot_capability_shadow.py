"""Stage R1 (M30.2 brief): portfolio_snapshots.py's shadow consultation of
the Asset Definition Runtime via _consult_runtime_for_snapshot(), plus the
wiring into generate_daily_snapshot() itself.

Third Stage R1 consumer, after ledger_validator (M11) and asset_registry
(M12). Mirrors both: read-only, never raises, never gates, never changes any
computed value — this suite proves that property at both layers:

  1. _consult_runtime_for_snapshot() in isolation — agreement / mismatch /
     missing-binding / registry-boot-failure outcomes for both questions
     this module shadows (quantity valuation, dividend flow).
  2. generate_daily_snapshot() end-to-end — the returned dict and the
     PortfolioSnapshot row are byte-identical whether the consultation
     agrees, disagrees, fails to resolve, or raises outright.
"""
import os
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base, Portfolio, PortfolioItem, PortfolioSnapshot, Transaction, Workspace
import models.asset  # noqa: F401 — registers Asset* tables (portfolio_items.asset_id FK target)
import models.registry_finding  # noqa: F401 — registers RegistryFinding table

from services import asset_registry as registry
from services import capability_lookup_service as lookup_service
from services import registry_lookup
from services.asset_domain import AssetClaim, AssetType, IdentifierRecord, IdentifierType
from services.runtime_consultation import RuntimeFindingCategory
from services.transaction_canonicalizer import CanonicalTransaction
import services.portfolio_snapshots as snap_module
from services.portfolio_snapshots import _consult_runtime_for_snapshot, generate_daily_snapshot


# ── Fixtures / helpers ────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _reset_cache():
    """registry_lookup's TTL cache is process-global — every test in this
    file must start and end with it empty, matching the established
    convention in test_registry_lookup.py / test_capability_lookup_service.py's
    sibling suites."""
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


def _holding(symbol: str) -> SimpleNamespace:
    """A stand-in for PortfolioItem — _consult_runtime_for_snapshot() only
    ever reads `.symbol` off each item."""
    return SimpleNamespace(symbol=symbol)


def _dividend_ctx(id_: int, symbol: str) -> CanonicalTransaction:
    return CanonicalTransaction(
        id=id_, transaction_type="DIVIDEND", raw_symbol=symbol, canonical_symbol=symbol,
        shares=Decimal("0"), price_per_share=Decimal("0"), total_amount=Decimal("100"),
        fees=Decimal("0"), taxes=Decimal("0"), transaction_date=datetime.utcnow().date(),
        created_at=datetime.utcnow(), sector=None, notes=None,
        qty_correction_delta=None, realized_pnl=None,
    )


# ── 1. Quantity valuation: agreement / mismatch / missing binding ─────────

def test_quantity_valuation_agrees_for_equity():
    db = make_session()
    _mint_with_symbol(db, "SHADOW_EQ", AssetType.EQUITY)

    log = _consult_runtime_for_snapshot(db, [_holding("SHADOW_EQ")], {"SHADOW_EQ": 10.0}, [])

    assert log.consulted == 1
    assert log.agreements == 1
    assert log.findings == ()


def test_quantity_valuation_mismatches_for_cash():
    """CASH declares quantity_equals_value=True, so permits_quantity_valuation()
    is False — but this module computes market_value = shares × price for any
    holding with a live price unconditionally, so this is a real disagreement."""
    db = make_session()
    _mint_with_symbol(db, "SHADOW_CASH", AssetType.CASH)

    log = _consult_runtime_for_snapshot(db, [_holding("SHADOW_CASH")], {"SHADOW_CASH": 1.0}, [])

    assert log.consulted == 1
    assert log.agreements == 0
    assert len(log.findings) == 1
    finding = log.findings[0]
    assert finding.category == RuntimeFindingCategory.RUNTIME_MISMATCH.value
    assert finding.check_id == "RUNTIME_SNAPSHOT_QUANTITY_VALUATION"
    assert finding.binding == "SHADOW_CASH"
    assert finding.legacy_result is True
    assert finding.runtime_result is False


def test_quantity_valuation_skipped_when_price_missing():
    """A holding with no live price never reaches the shares×price line in
    the legacy code, so there is no legacy decision to shadow."""
    db = make_session()
    _mint_with_symbol(db, "SHADOW_EQ", AssetType.EQUITY)

    log = _consult_runtime_for_snapshot(db, [_holding("SHADOW_EQ")], {}, [])

    assert log.consulted == 0
    assert log.findings == ()


def test_quantity_valuation_missing_binding_for_undefined_asset_type():
    db = make_session()
    _mint_with_symbol(db, "SHADOW_CRYPTO", AssetType.CRYPTO)

    log = _consult_runtime_for_snapshot(db, [_holding("SHADOW_CRYPTO")], {"SHADOW_CRYPTO": 5.0}, [])

    assert len(log.findings) == 1
    finding = log.findings[0]
    assert finding.category == RuntimeFindingCategory.MISSING_BINDING.value
    assert finding.detail == lookup_service._REASON_NO_DEFINITION
    assert finding.runtime_result is None


def test_quantity_valuation_missing_binding_for_never_minted_symbol():
    db = make_session()

    log = _consult_runtime_for_snapshot(db, [_holding("NEVER_MINTED")], {"NEVER_MINTED": 5.0}, [])

    assert len(log.findings) == 1
    assert log.findings[0].detail == lookup_service._REASON_UNKNOWN_ASSET


# ── 2. Dividend flow: agreement / mismatch ─────────────────────────────────

def test_dividend_flow_agrees_for_equity():
    db = make_session()
    _mint_with_symbol(db, "SHADOW_EQ", AssetType.EQUITY)

    log = _consult_runtime_for_snapshot(db, [], {}, [_dividend_ctx(1, "SHADOW_EQ")])

    assert log.consulted == 1
    assert log.agreements == 1
    assert log.findings == ()


def test_dividend_flow_mismatches_for_bond():
    """BOND grants FlowType.COUPON, not DIVIDEND — but this module folds any
    DIVIDEND transaction into period_dividend_income unconditionally."""
    db = make_session()
    _mint_with_symbol(db, "SHADOW_BOND", AssetType.BOND)

    log = _consult_runtime_for_snapshot(db, [], {}, [_dividend_ctx(7, "SHADOW_BOND")])

    assert log.consulted == 1
    assert log.agreements == 0
    assert len(log.findings) == 1
    finding = log.findings[0]
    assert finding.category == RuntimeFindingCategory.RUNTIME_MISMATCH.value
    assert finding.check_id == "RUNTIME_SNAPSHOT_DIVIDEND_FLOW"
    assert finding.transaction_ids == (7,)
    assert finding.runtime_result is False


# ── 3. Registry boot failure ───────────────────────────────────────────────

def test_registry_boot_failure_yields_missing_binding_never_raises():
    import services.asset_definitions.library as library

    db = make_session()
    _mint_with_symbol(db, "SHADOW_EQ", AssetType.EQUITY)

    original = dict(library.PINNED_FINGERPRINTS)
    try:
        library.PINNED_FINGERPRINTS[(AssetType.CASH.value, "v1")] = "0" * 64
        log = _consult_runtime_for_snapshot(db, [_holding("SHADOW_EQ")], {"SHADOW_EQ": 10.0}, [])
    finally:
        library.PINNED_FINGERPRINTS.clear()
        library.PINNED_FINGERPRINTS.update(original)

    assert len(log.findings) == 1
    assert log.findings[0].category == RuntimeFindingCategory.MISSING_BINDING.value
    assert log.findings[0].detail == lookup_service._REASON_REGISTRY_BOOT_FAILED


def test_no_holdings_no_dividends_returns_empty_log():
    db = make_session()
    log = _consult_runtime_for_snapshot(db, [], {}, [])
    assert log.consulted == 0
    assert log.agreements == 0
    assert log.findings == ()


# ── 4. Integration: generate_daily_snapshot() is unaffected end-to-end ────

def _run_snapshot(db, portfolio_id, workspace_id, today_str, price_map):
    import asyncio
    from unittest.mock import patch

    async def _go():
        with patch(
            "services.portfolio_snapshots.fetch_price_info",
            side_effect=lambda sym: {"current_price": price_map.get(sym)},
        ):
            return await generate_daily_snapshot(db, portfolio_id, workspace_id, today_str)

    # asyncio.run() (not get_event_loop().run_until_complete(), which
    # test_snapshot_coverage.py's sibling helper uses) so this file's tests
    # stay independent of whichever thread-local event loop state an
    # earlier-run test file in the full suite happened to leave behind.
    return asyncio.run(_go())


def test_snapshot_values_unaffected_by_capability_mismatch(caplog):
    """A CASH-typed holding (guaranteed quantity-valuation mismatch) must
    still be valued exactly as shares × price — the shadow finding is
    logged, but never changes the computed market_value or total_value."""
    db = make_session()
    _mint_with_symbol(db, "SHADOW_CASH", AssetType.CASH)
    ws, p = _seed(db, cash=1_000.0)
    db.add(PortfolioItem(workspace_id=ws.id, portfolio_id=p.id, symbol="SHADOW_CASH", shares=100, avg_cost=1.0, sector="Test"))
    db.commit()

    with caplog.at_level("WARNING", logger="services.portfolio_snapshots"):
        result = _run_snapshot(db, p.id, ws.id, datetime.utcnow().strftime("%Y-%m-%d"), {"SHADOW_CASH": 2.5})

    holding = result["holdings"][0]
    assert holding["market_value"] == pytest.approx(250.0)
    assert result["total_value"] == pytest.approx(1_000.0 + 250.0)
    assert any("RUNTIME_SNAPSHOT_QUANTITY_VALUATION" in r.message for r in caplog.records)


def test_snapshot_result_identical_whether_or_not_symbol_is_minted():
    """Capability consultation is purely additive/observational — minting
    (or not minting) the Asset Registry entry for a symbol must not change
    a single computed value in the snapshot."""
    today = datetime.utcnow().strftime("%Y-%m-%d")

    db_unminted = make_session()
    ws1, p1 = _seed(db_unminted, cash=500.0)
    db_unminted.add(PortfolioItem(workspace_id=ws1.id, portfolio_id=p1.id, symbol="TWIN.BK", shares=10, avg_cost=3.0, sector="Test"))
    db_unminted.commit()
    unminted_result = _run_snapshot(db_unminted, p1.id, ws1.id, today, {"TWIN.BK": 4.0})

    registry_lookup.invalidate_cache()

    db_minted = make_session()
    _mint_with_symbol(db_minted, "TWIN.BK", AssetType.EQUITY)
    ws2, p2 = _seed(db_minted, cash=500.0)
    db_minted.add(PortfolioItem(workspace_id=ws2.id, portfolio_id=p2.id, symbol="TWIN.BK", shares=10, avg_cost=3.0, sector="Test"))
    db_minted.commit()
    minted_result = _run_snapshot(db_minted, p2.id, ws2.id, today, {"TWIN.BK": 4.0})

    for key in (
        "total_value", "cash_balance", "equity_value", "total_invested",
        "unrealized_pnl", "unrealized_pnl_pct", "realized_pnl", "holdings_count",
    ):
        assert unminted_result[key] == minted_result[key], key

    assert unminted_result["holdings"] == minted_result["holdings"]
    assert set(unminted_result.keys()) == set(minted_result.keys()), (
        "capability consultation must not add or remove any key from the returned dict"
    )


def test_snapshot_succeeds_even_when_capability_consultation_raises(monkeypatch):
    """Mirrors test_runtime_consultation_never_raises_out_of_mint (M12):
    even if _consult_runtime_for_snapshot() itself raised unexpectedly,
    generate_daily_snapshot() must swallow it and still complete."""
    def _boom(db, items, price_map, window_txs):
        raise RuntimeError("simulated unexpected failure")

    monkeypatch.setattr(snap_module, "_consult_runtime_for_snapshot", _boom)

    db = make_session()
    ws, p = _seed(db, cash=1_000.0)
    db.add(PortfolioItem(workspace_id=ws.id, portfolio_id=p.id, symbol="BOOM.BK", shares=10, avg_cost=1.0, sector="Test"))
    db.commit()

    result = _run_snapshot(db, p.id, ws.id, datetime.utcnow().strftime("%Y-%m-%d"), {"BOOM.BK": 2.0})

    assert result["total_value"] == pytest.approx(1_000.0 + 20.0)

    saved = db.query(PortfolioSnapshot).filter_by(portfolio_id=p.id).first()
    assert saved is not None
    assert saved.total_value == pytest.approx(1_020.0)


def test_dividend_window_transaction_does_not_change_period_dividend_income(caplog):
    """A DIVIDEND transaction on a BOND-typed symbol (guaranteed dividend-flow
    mismatch) must still be folded into period_dividend_income exactly as
    before — the mismatch is logged, never enforced."""
    db = make_session()
    _mint_with_symbol(db, "SHADOW_BOND", AssetType.BOND)
    ws, p = _seed(db, cash=0.0)
    db.add(PortfolioItem(workspace_id=ws.id, portfolio_id=p.id, symbol="SHADOW_BOND", shares=10, avg_cost=1.0, sector="Test"))
    db.commit()

    yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
    db.add(PortfolioSnapshot(
        workspace_id=ws.id, portfolio_id=p.id, snapshot_date=yesterday,
        total_value=10.0, cash_balance=0.0, total_invested=10.0,
    ))
    db.commit()

    db.add(Transaction(
        workspace_id=ws.id, portfolio_id=p.id, symbol="SHADOW_BOND",
        transaction_type="DIVIDEND", shares=0, price_per_share=0,
        total_amount=25.0, fees=0.0, taxes=0.0,
        transaction_date=datetime.utcnow(), created_at=datetime.utcnow(),
    ))
    db.commit()

    with caplog.at_level("WARNING", logger="services.portfolio_snapshots"):
        result = _run_snapshot(db, p.id, ws.id, datetime.utcnow().strftime("%Y-%m-%d"), {"SHADOW_BOND": 1.0})

    assert result["period_dividend_income"] == pytest.approx(25.0)
    assert any("RUNTIME_SNAPSHOT_DIVIDEND_FLOW" in r.message for r in caplog.records)
