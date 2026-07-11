"""Tests for the M5 Track B Stage 4 controlled replay cutover
(services/replay_cutover.py, services/transaction_canonicalizer.py's
prefer_asset_id parameter, and the services/portfolio_rebuilder.py
report_symbol fix it depends on).

Reference: docs/implementation/M5_TRACK_B_NATIVE_INTEGRATION_TDD.md §7
Stage 4, §9 Rollout Plan.

Real in-memory SQLite throughout — real mint_asset(), real execute_buy()
(exercising Stage 3's own write path), real capture_golden_baseline() /
rebuild_portfolio() / attempt_cutover(), no mocked DB session. This is the
only way to genuinely prove the session commit/rollback semantics
attempt_cutover() depends on (ADR-004: no new diff/replay logic — this
module only orchestrates already-built pieces).

Coverage:
  1. Legacy mode — a freshly-created portfolio's flag defaults to
     off/unset; ordinary replay is unaffected.
  2. Native mode accepted AND committed — a fully-resolved portfolio's
     cutover is proven bit-identical and, with commit=True, the flag is
     actually persisted.
  3. Native mode proved but NOT persisted when commit=False (the default,
     dry-run-by-default like every other write path in this codebase).
  4. Mixed portfolios — cutting over portfolio A never touches portfolio B
     in the same workspace (no global flag day).
  5. Missing asset_id (never minted) — an entirely unresolved portfolio's
     cutover is trivially bit-identical (replay_key still falls through to
     the string tier) and is accepted.
  6. Partial backfill — one resolved + one unresolved symbol in the same
     portfolio; exercises the exact mixed int/str holdings-dict code path
     fixed in portfolio_rebuilder.py (_reconcile_portfolio_items,
     _generate_execution_plan, _commit_rebuild); must not raise, and must
     be accepted (bit-identical) since report_symbol carries the display
     string regardless of the internal merge key's type.
  7. Rollback to legacy mode — a committed cutover is reverted via
     rollback_cutover(); the flag persists back to False.
  8. Replay parity catches a genuine diff and rejects — two raw symbols
     that resolve (write-time, mocked per the established
     test_registry_symbol_matching.py precedent — see that file's own
     docstring for why a live, un-mocked two-alias fixture can't exercise
     this branch: this codebase's identity_resolver treats two live
     PROVIDER_SYMBOL identifiers on one asset as ambiguous) to the SAME
     asset_id merge under native keying but stay separate under legacy
     keying; attempt_cutover must reject, and the portfolio's flag must
     remain False (never committed) — "Abort cutover. Leave the portfolio
     in legacy mode."
  9. Golden Baseline acceptance plumbing — unresolved_transaction_count is
     reported accurately, and portfolio/baseline-mismatch guards return a
     clean error rather than raising.
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
from services.portfolio_rebuilder import rebuild_portfolio
from services.portfolio_transactions import execute_buy
from services.registry_replay_parity import capture_golden_baseline, compare_against_baseline
from services.replay_cutover import attempt_cutover, rollback_cutover, unresolved_transaction_count


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


def _claim(symbol, **overrides):
    defaults = dict(asset_type=AssetType.EQUITY, market="Thailand", exchange="SET", currency="THB")
    defaults.update(overrides)
    return AssetClaim(canonical_symbol=symbol, **defaults)


def _provider_symbol(value):
    return IdentifierRecord(identifier_type=IdentifierType.PROVIDER_SYMBOL, value=value, source="test")


def _mint(db, symbol):
    return svc.mint_asset(db, _claim(symbol), identifiers=[_provider_symbol(symbol)])


@pytest.fixture()
def db():
    session = make_session()
    yield session
    session.close()


@pytest.fixture()
def ws(db):
    w = Workspace(name="Test")
    db.add(w)
    db.commit()
    db.refresh(w)
    return w


def _make_portfolio(db, ws, *, name="P1", cash=1_000_000.0) -> Portfolio:
    p = Portfolio(workspace_id=ws.id, name=name, cash_balance=cash)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


async def _capture(db, portfolio, ws):
    return await capture_golden_baseline(db, portfolio_id=portfolio.id, workspace_id=ws.id, skip_snapshots=True)


# ── 1. Legacy mode is the default ────────────────────────────────────────

@pytest.mark.asyncio
async def test_legacy_mode_is_default_and_replay_unaffected(db, ws):
    portfolio = _make_portfolio(db, ws)
    execute_buy(db, ws.id, portfolio.id, "AOT", shares=100, price_per_share=30.0)
    assert not portfolio.replay_asset_id_native

    baseline = await _capture(db, portfolio, ws)
    rebuilt = await rebuild_portfolio(
        db, portfolio_id=portfolio.id, workspace_id=ws.id, dry_run=True, skip_snapshots=True, backup=False,
    )
    parity = compare_against_baseline(baseline, rebuilt)
    assert parity.is_bit_identical


# ── 2/3. Native mode: accepted+committed vs accepted-but-not-persisted ──

@pytest.mark.asyncio
async def test_native_mode_accepted_and_committed(db, ws):
    portfolio = _make_portfolio(db, ws)
    asset = _mint(db, "AOT")
    execute_buy(db, ws.id, portfolio.id, "AOT", shares=100, price_per_share=30.0)
    baseline = await _capture(db, portfolio, ws)

    result = await attempt_cutover(
        db, portfolio_id=portfolio.id, workspace_id=ws.id, baseline=baseline,
        commit=True, skip_snapshots=True,
    )

    assert result.accepted
    assert result.committed
    assert result.error is None
    assert result.parity.is_bit_identical
    assert portfolio.replay_asset_id_native is True


@pytest.mark.asyncio
async def test_native_mode_accepted_but_not_persisted_by_default(db, ws):
    portfolio = _make_portfolio(db, ws)
    _mint(db, "AOT")
    execute_buy(db, ws.id, portfolio.id, "AOT", shares=100, price_per_share=30.0)
    baseline = await _capture(db, portfolio, ws)

    result = await attempt_cutover(
        db, portfolio_id=portfolio.id, workspace_id=ws.id, baseline=baseline, skip_snapshots=True,
    )

    assert result.accepted
    assert not result.committed
    assert not portfolio.replay_asset_id_native   # rolled back, still legacy


# ── 4. Mixed portfolios — cutover never touches a sibling portfolio ─────

@pytest.mark.asyncio
async def test_cutover_never_touches_sibling_portfolio(db, ws):
    p1 = _make_portfolio(db, ws, name="P1")
    p2 = _make_portfolio(db, ws, name="P2")
    _mint(db, "AOT")
    execute_buy(db, ws.id, p1.id, "AOT", shares=100, price_per_share=30.0)
    execute_buy(db, ws.id, p2.id, "AOT", shares=50, price_per_share=30.0)

    baseline1 = await _capture(db, p1, ws)
    result = await attempt_cutover(
        db, portfolio_id=p1.id, workspace_id=ws.id, baseline=baseline1, commit=True, skip_snapshots=True,
    )

    assert result.accepted and result.committed
    assert p1.replay_asset_id_native is True
    assert not p2.replay_asset_id_native


# ── 5. Missing asset_id — trivially bit-identical, still accepted ───────

@pytest.mark.asyncio
async def test_fully_unresolved_portfolio_still_accepted(db, ws):
    portfolio = _make_portfolio(db, ws)
    execute_buy(db, ws.id, portfolio.id, "NEVERMINTED", shares=10, price_per_share=5.0)
    baseline = await _capture(db, portfolio, ws)

    result = await attempt_cutover(
        db, portfolio_id=portfolio.id, workspace_id=ws.id, baseline=baseline,
        commit=True, skip_snapshots=True,
    )

    assert result.accepted
    assert result.parity.is_bit_identical
    assert result.still_unresolved_transaction_count == 1


# ── 6. Partial backfill — mixed resolved/unresolved in one portfolio ────

@pytest.mark.asyncio
async def test_partial_backfill_mixed_keys_does_not_raise_and_is_accepted(db, ws):
    portfolio = _make_portfolio(db, ws)
    _mint(db, "AOT")
    execute_buy(db, ws.id, portfolio.id, "AOT", shares=100, price_per_share=30.0)          # resolved
    execute_buy(db, ws.id, portfolio.id, "NEVERMINTED", shares=10, price_per_share=5.0)    # unresolved
    baseline = await _capture(db, portfolio, ws)

    result = await attempt_cutover(
        db, portfolio_id=portfolio.id, workspace_id=ws.id, baseline=baseline,
        commit=True, skip_snapshots=True,
    )

    assert result.error is None
    assert result.accepted
    assert result.parity.is_bit_identical
    assert result.still_unresolved_transaction_count == 1


# ── 7. Rollback to legacy mode ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_rollback_cutover_reverts_flag_to_legacy(db, ws):
    portfolio = _make_portfolio(db, ws)
    _mint(db, "AOT")
    execute_buy(db, ws.id, portfolio.id, "AOT", shares=100, price_per_share=30.0)
    baseline = await _capture(db, portfolio, ws)
    await attempt_cutover(
        db, portfolio_id=portfolio.id, workspace_id=ws.id, baseline=baseline,
        commit=True, skip_snapshots=True,
    )
    assert portfolio.replay_asset_id_native is True

    ok = rollback_cutover(db, portfolio.id, ws.id)
    assert ok
    assert portfolio.replay_asset_id_native is False


def test_rollback_cutover_returns_false_for_missing_portfolio(db, ws):
    assert rollback_cutover(db, 999_999, ws.id) is False


# ── 8. A genuine parity diff is rejected, portfolio stays legacy ────────

@pytest.mark.asyncio
async def test_genuine_merge_diff_is_rejected_and_stays_legacy(db, ws):
    """Two raw symbols ("OLD"/"NEW") that Track A's Registry has adjudicated
    as the SAME asset (write-time resolution mocked — see module docstring)
    stay as two separate holdings under legacy canonical_symbol keying, but
    correctly merge into one holding under native asset_id keying. That is
    a genuine, real difference — attempt_cutover must reject it and must
    never persist the flag flip.
    """
    portfolio = _make_portfolio(db, ws)
    asset = _mint(db, "OLD")   # canonical identity; "NEW" is a simulated rename

    with patch(
        "services.portfolio_transactions.registry_lookup.resolve_asset",
        return_value=lookup.AssetView(
            asset_id=asset.id, canonical_symbol="OLD", display_symbol="OLD",
            market="Thailand", exchange="SET", currency="THB", asset_type=lookup.AssetType.EQUITY,
        ),
    ):
        execute_buy(db, ws.id, portfolio.id, "OLD", shares=50, price_per_share=10.0)
        execute_buy(db, ws.id, portfolio.id, "NEW", shares=50, price_per_share=20.0)

    tx_old = db.query(Transaction).filter_by(portfolio_id=portfolio.id, symbol="OLD").one()
    tx_new = db.query(Transaction).filter_by(portfolio_id=portfolio.id, symbol="NEW").one()
    assert tx_old.asset_id == asset.id
    assert tx_new.asset_id == asset.id   # both point at the same asset — the merge trigger

    # Legacy baseline: "OLD" and "NEW" don't share a canonical_symbol, so
    # they replay as two separate holdings.
    baseline = await _capture(db, portfolio, ws)
    baseline_symbols = {sym for sym, _f, _v in baseline.holdings_truth}
    assert len(baseline_symbols) == 2   # "OLD" and "NEW" replay as two separate holdings under legacy keying

    result = await attempt_cutover(
        db, portfolio_id=portfolio.id, workspace_id=ws.id, baseline=baseline,
        commit=True, skip_snapshots=True,
    )

    assert not result.accepted
    assert not result.committed
    assert result.parity is not None
    assert not result.parity.is_bit_identical
    assert not portfolio.replay_asset_id_native   # stayed legacy — never committed


# ── 9. Baseline/portfolio mismatch guard + unresolved-count accuracy ────

@pytest.mark.asyncio
async def test_baseline_for_wrong_portfolio_returns_clean_error(db, ws):
    p1 = _make_portfolio(db, ws, name="P1")
    p2 = _make_portfolio(db, ws, name="P2")
    execute_buy(db, ws.id, p1.id, "AOT", shares=10, price_per_share=5.0)
    execute_buy(db, ws.id, p2.id, "PTT", shares=10, price_per_share=5.0)
    baseline_for_p1 = await _capture(db, p1, ws)

    result = await attempt_cutover(
        db, portfolio_id=p2.id, workspace_id=ws.id, baseline=baseline_for_p1, skip_snapshots=True,
    )
    assert not result.accepted
    assert result.error is not None
    assert not p2.replay_asset_id_native


def test_unresolved_transaction_count_accurate(db, ws):
    portfolio = _make_portfolio(db, ws)
    _mint(db, "AOT")
    execute_buy(db, ws.id, portfolio.id, "AOT", shares=10, price_per_share=5.0)
    execute_buy(db, ws.id, portfolio.id, "NEVERMINTED", shares=10, price_per_share=5.0)
    assert unresolved_transaction_count(db, portfolio.id) == 1
