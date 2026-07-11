"""Tests for the M5 Track B Stage 3 write path (services/portfolio_transactions.py
resolve-and-write, docs/implementation/M5_TRACK_B_NATIVE_INTEGRATION_TDD.md §2.3).

Coverage:
  1. Successful dual write — a Registry-known symbol gets asset_id on both
     the new Transaction and the (new or existing) PortfolioItem row; the
     legacy symbol column is written exactly as before.
  2. Unresolved Registry result — a symbol the Registry has never seen
     resolves to Unresolved; the write proceeds normally, asset_id stays
     NULL, nothing raises.
  3. NULL asset_id fallback never blocks the write — legacy symbol/shares/
     price fields persist identically whether or not resolution succeeds.
  4. Idempotent repeated writes — resolving the same symbol across multiple
     execute_buy calls never diverges: PortfolioItem.asset_id, once set,
     matches every subsequent Transaction.asset_id for that symbol.
  5. Replay parity — default (prefer_asset_id=False) canonicalization still
     yields CanonicalTransaction.asset_id=None and replay_key() is
     unaffected by a Stage 3 write (write-path only; replay untouched, per
     TDD §2.3's own scope boundary — mirrors the structural proof used in
     the Stage 2 tests). M5 Track B Stage 4 later added the asset_id field
     itself plus the prefer_asset_id gate — see test_replay_cutover.py.
  6. No Stage 3 flag exists in the ratified design (the only flag,
     Portfolio.replay_asset_id_native, is Stage-4-scoped per TDD §9) —
     write-path resolution is unconditional, verified with no flag/config
     set at all ("flag OFF" is simply today's default, always-on behavior).
  7. Registry lookup failure (an unexpected exception, not an ordinary
     Unresolved) never blocks or partially commits the write — asset_id
     falls back to NULL and every other column persists exactly as it
     would pre-Stage-3 ("write path rollback": nothing partial is left
     committed when resolution errors).
  8. execute_sell / execute_initial_position / execute_quantity_correction
     opportunistically backfill a still-NULL PortfolioItem.asset_id using
     the same resolve call they already need for their own Transaction row
     — no second resolution call, no new identity logic (ADR-004), and a
     later Unresolved/error result never regresses an already-set value.
"""
from __future__ import annotations

import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base, Portfolio, PortfolioItem, Transaction, Workspace
import models.asset  # noqa: F401 — registers Asset* tables on Base.metadata
import models.registry_finding  # noqa: F401 — registers RegistryFinding table

from services import registry_lookup as lookup
from services import registry_service as svc
from services.asset_domain import AssetClaim, AssetType, IdentifierRecord, IdentifierType
from services.portfolio_transactions import (
    execute_buy,
    execute_initial_position,
    execute_quantity_correction,
    execute_sell,
)
from services.replay_key import replay_key
from services.transaction_canonicalizer import CanonicalTransaction, canonicalize_transactions


def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


@pytest.fixture(autouse=True)
def _reset_cache():
    lookup.invalidate_cache()
    yield
    lookup.invalidate_cache()


def _claim(canonical_symbol, **overrides):
    defaults = dict(asset_type=AssetType.EQUITY, market="Thailand", exchange="SET", currency="THB")
    defaults.update(overrides)
    return AssetClaim(canonical_symbol=canonical_symbol, **defaults)


def _provider_symbol(value):
    return IdentifierRecord(identifier_type=IdentifierType.PROVIDER_SYMBOL, value=value, source="test")


@pytest.fixture()
def db():
    session = make_session()
    yield session
    session.close()


@pytest.fixture()
def ws_portfolio(db):
    ws = Workspace(name="Test")
    db.add(ws)
    db.commit()
    db.refresh(ws)

    portfolio = Portfolio(workspace_id=ws.id, name="P1", cash_balance=1_000_000.0)
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)

    return ws, portfolio


def _mint(db, symbol):
    return svc.mint_asset(db, _claim(symbol), identifiers=[_provider_symbol(symbol)])


# ── 1/3. Successful dual write, legacy fields unchanged ─────────────────

def test_execute_buy_writes_asset_id_for_known_symbol(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    asset = _mint(db, "AOT")
    db.commit()

    result = execute_buy(db, ws.id, portfolio.id, "AOT", shares=100, price_per_share=30.0)

    tx = db.query(Transaction).filter_by(id=result["transaction_id"]).one()
    item = db.query(PortfolioItem).filter_by(portfolio_id=portfolio.id, symbol="AOT").one()
    assert tx.symbol == "AOT"
    assert tx.shares == 100.0
    assert tx.asset_id == asset.id
    assert item.symbol == "AOT"
    assert item.asset_id == asset.id


# ── 2/3. Unresolved Registry result never blocks the write ──────────────

def test_execute_buy_leaves_asset_id_null_for_unknown_symbol(db, ws_portfolio):
    ws, portfolio = ws_portfolio

    result = execute_buy(db, ws.id, portfolio.id, "NEVERMINTED", shares=10, price_per_share=5.0)

    tx = db.query(Transaction).filter_by(id=result["transaction_id"]).one()
    item = db.query(PortfolioItem).filter_by(portfolio_id=portfolio.id, symbol="NEVERMINTED").one()
    assert tx.symbol == "NEVERMINTED"
    assert tx.shares == 10.0
    assert tx.price_per_share == 5.0
    assert tx.asset_id is None
    assert item.asset_id is None


def test_execute_initial_position_unresolved_symbol_still_persists(db, ws_portfolio):
    ws, portfolio = ws_portfolio

    result = execute_initial_position(db, ws.id, portfolio.id, "UNKNOWNCO", shares=50, avg_cost=12.0)

    tx = db.query(Transaction).filter_by(id=result["transaction_id"]).one()
    assert tx.transaction_type == "INITIAL_POSITION"
    assert tx.asset_id is None


# ── 4. Idempotent repeated writes ────────────────────────────────────────

def test_repeated_buys_never_diverge_asset_id(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    asset = _mint(db, "AOT")
    db.commit()

    r1 = execute_buy(db, ws.id, portfolio.id, "AOT", shares=100, price_per_share=30.0)
    r2 = execute_buy(db, ws.id, portfolio.id, "AOT", shares=50, price_per_share=31.0)

    item = db.query(PortfolioItem).filter_by(portfolio_id=portfolio.id, symbol="AOT").one()
    tx1 = db.query(Transaction).filter_by(id=r1["transaction_id"]).one()
    tx2 = db.query(Transaction).filter_by(id=r2["transaction_id"]).one()

    assert item.asset_id == asset.id
    assert tx1.asset_id == asset.id
    assert tx2.asset_id == asset.id
    assert item.shares == 150.0


def test_write_time_resolution_opportunistically_upgrades_but_never_regresses(db, ws_portfolio):
    """A PortfolioItem created before its symbol was minted (asset_id NULL)
    opportunistically gains asset_id the next time it's written to — but a
    later Unresolved result must never null out an asset_id a previous write
    already set (identity is permanent, TDD §4.1)."""
    ws, portfolio = ws_portfolio

    execute_buy(db, ws.id, portfolio.id, "AOT", shares=100, price_per_share=30.0)
    item = db.query(PortfolioItem).filter_by(portfolio_id=portfolio.id, symbol="AOT").one()
    assert item.asset_id is None

    asset = _mint(db, "AOT")
    db.commit()
    lookup.invalidate_cache()

    execute_buy(db, ws.id, portfolio.id, "AOT", shares=10, price_per_share=31.0)
    db.refresh(item)
    assert item.asset_id == asset.id   # opportunistic upgrade

    with patch(
        "services.portfolio_transactions.registry_lookup.resolve_asset",
        return_value=lookup.Unresolved(query="AOT", reason="forced-for-test"),
    ):
        execute_buy(db, ws.id, portfolio.id, "AOT", shares=5, price_per_share=32.0)
    db.refresh(item)
    assert item.asset_id == asset.id   # never regressed to NULL


# ── 5. Replay parity — write path change is structurally invisible to replay ──

def test_canonicalization_unaffected_by_stage3_write(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    asset = _mint(db, "AOT")
    db.commit()

    result = execute_buy(db, ws.id, portfolio.id, "AOT", shares=100, price_per_share=30.0)
    tx = db.query(Transaction).filter_by(id=result["transaction_id"]).one()
    assert tx.asset_id == asset.id   # Stage 3 did write it onto the row

    # ...yet default (prefer_asset_id=False) canonicalization still yields
    # asset_id=None on the CanonicalTransaction, and replay_key() still
    # falls through to the string tier — replay remains untouched by a
    # Stage 3 write alone (Stage 4's prefer_asset_id gate is what actually
    # changes this, per-portfolio — see test_replay_cutover.py).
    canon = canonicalize_transactions([tx])
    assert canon[0].asset_id is None

    key = replay_key(canon[0])
    assert key == canon[0].canonical_symbol or key == canon[0].raw_symbol


def test_replay_key_never_reads_asset_id_even_when_populated(db, ws_portfolio):
    """Belt-and-braces: monkeypatching resolve_asset to raise proves replay
    performs no Registry call of its own (mirrors TDD §10.6's "Replay never
    re-resolves identity" invariant test)."""
    ws, portfolio = ws_portfolio
    asset = _mint(db, "AOT")
    db.commit()
    result = execute_buy(db, ws.id, portfolio.id, "AOT", shares=100, price_per_share=30.0)
    tx = db.query(Transaction).filter_by(id=result["transaction_id"]).one()
    assert tx.asset_id == asset.id

    with patch("services.registry_lookup.resolve_asset", side_effect=AssertionError("replay must not call this")):
        canon = canonicalize_transactions([tx])
        replay_key(canon[0])   # would raise if it ever touched resolve_asset


# ── 6. No Stage 3 flag exists — resolution is unconditional ─────────────

def test_resolve_and_write_is_unconditional_no_flag_required(db, ws_portfolio):
    """The ratified design's only rollout flag (Portfolio.replay_asset_id_
    native, TDD §9) gates Stage 4 replay cutover, not Stage 3 write-path
    resolution. This test documents that fact: write-path resolution
    happens unconditionally regardless of the flag's value (which, since
    M5 Track B Stage 4, defaults to None/False on every portfolio — see
    test_replay_cutover.py for that flag's own dedicated coverage)."""
    ws, portfolio = ws_portfolio
    assert not portfolio.replay_asset_id_native   # default OFF; Stage 3 doesn't touch it either way

    asset = _mint(db, "PTT")
    db.commit()
    result = execute_buy(db, ws.id, portfolio.id, "PTT", shares=20, price_per_share=35.0)
    tx = db.query(Transaction).filter_by(id=result["transaction_id"]).one()
    assert tx.asset_id == asset.id


# ── 7. Registry failure never blocks or partially commits the write ─────

def test_registry_exception_falls_back_to_null_without_blocking(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    _mint(db, "AOT")
    db.commit()

    with patch(
        "services.portfolio_transactions.registry_lookup.resolve_asset",
        side_effect=RuntimeError("simulated Registry outage"),
    ):
        result = execute_buy(db, ws.id, portfolio.id, "AOT", shares=100, price_per_share=30.0)

    tx = db.query(Transaction).filter_by(id=result["transaction_id"]).one()
    item = db.query(PortfolioItem).filter_by(portfolio_id=portfolio.id, symbol="AOT").one()
    assert tx.asset_id is None
    assert item.asset_id is None
    # Nothing partial: exactly one Transaction and one PortfolioItem exist,
    # and every non-identity field persisted exactly as a normal buy would.
    assert db.query(Transaction).filter_by(portfolio_id=portfolio.id).count() == 1
    assert db.query(PortfolioItem).filter_by(portfolio_id=portfolio.id).count() == 1
    assert tx.shares == 100.0
    assert tx.total_amount is not None
    assert portfolio.cash_balance < 1_000_000.0


# ── 8. Other execute_* functions opportunistically backfill PortfolioItem ──

def test_execute_sell_opportunistically_backfills_item_asset_id(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    execute_buy(db, ws.id, portfolio.id, "AOT", shares=100, price_per_share=30.0)
    item = db.query(PortfolioItem).filter_by(portfolio_id=portfolio.id, symbol="AOT").one()
    assert item.asset_id is None

    asset = _mint(db, "AOT")
    db.commit()
    lookup.invalidate_cache()

    result = execute_sell(db, ws.id, portfolio.id, "AOT", shares=40, price_per_share=32.0, remove_if_zero=False)
    tx = db.query(Transaction).filter_by(id=result["transaction_id"]).one()
    db.refresh(item)
    assert tx.asset_id == asset.id
    assert item.asset_id == asset.id


def test_execute_quantity_correction_opportunistically_backfills_item_asset_id(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    execute_buy(db, ws.id, portfolio.id, "AOT", shares=100, price_per_share=30.0)
    item = db.query(PortfolioItem).filter_by(portfolio_id=portfolio.id, symbol="AOT").one()
    assert item.asset_id is None

    asset = _mint(db, "AOT")
    db.commit()
    lookup.invalidate_cache()

    result = execute_quantity_correction(db, ws.id, portfolio.id, "AOT", shares_delta=5.0, price_per_share=30.0)
    tx = db.query(Transaction).filter_by(id=result["transaction_id"]).one()
    db.refresh(item)
    assert tx.asset_id == asset.id
    assert item.asset_id == asset.id


def test_execute_initial_position_writes_asset_id_for_known_symbol(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    asset = _mint(db, "PTT")
    db.commit()

    result = execute_initial_position(db, ws.id, portfolio.id, "PTT", shares=200, avg_cost=34.5)
    tx = db.query(Transaction).filter_by(id=result["transaction_id"]).one()
    item = db.query(PortfolioItem).filter_by(portfolio_id=portfolio.id, symbol="PTT").one()
    assert tx.asset_id == asset.id
    assert item.asset_id == asset.id
