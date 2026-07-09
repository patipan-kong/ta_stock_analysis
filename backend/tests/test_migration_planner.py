"""Tests for the Migration Planner & Dry Run Engine (Milestone M5.1).

Validates:
  1. Transactions sharing a claim shape (raw_symbol, canonical_symbol,
     currency) resolve exactly once — not once per transaction, not once
     per portfolio.
  2. Currency is part of the claim shape key: the same symbol pair under
     two different transaction currencies is two distinct claim shapes.
  3. Cash-only transactions never build a claim and are never counted as
     UNKNOWN — they land in their own bucket.
  4. A RESOLVED claim shape carries the resolved asset's true
     market/exchange/currency, read via registry_service.get_asset().
  5. UNKNOWN passes through untouched when nothing in the Registry matches.
  6. CONFLICT is reachable from ledger evidence via the bundled
     venue-suffix case (KBANK/KBANK.BK each currently, wrongly, attached
     to a different asset).
  7. AMBIGUOUS is reachable via a single historical-only match (DR symbol,
     never bundled, superseded identifier).
  8. portfolio_ids scoping restricts which transactions are scanned.
  9. The dry run guarantee: identity_resolver.resolve() does write
     RegistryFinding rows internally for AMBIGUOUS/CONFLICT verdicts, but
     plan_migration() leaves zero net new rows in assets, asset_identifiers,
     or registry_findings — the write happens, and is then rolled back.
"""
import os
import sys
from datetime import date, datetime, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from models.database import Base, Portfolio, Transaction, Workspace
import models.asset  # noqa: F401 — registers Asset* tables on Base.metadata
import models.registry_finding  # noqa: F401 — registers RegistryFinding table
from models.asset import Asset, AssetIdentifier
from models.registry_finding import RegistryFinding
from services import migration_planner as planner
from services import registry_service as svc
from services.asset_domain import AssetClaim, AssetType, IdentifierRecord, IdentifierType
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


def _tx(
    db,
    portfolio,
    *,
    symbol,
    transaction_type="BUY",
    currency="THB",
    tx_date=date(2024, 1, 15),
    created_at=None,
) -> Transaction:
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
        transaction_date=datetime.combine(tx_date, datetime.min.time()),
        created_at=created_at or datetime(2024, 1, 15, 9, 30, tzinfo=timezone.utc),
    )
    db.add(tx)
    db.flush()
    return tx


def _row_counts(db) -> tuple:
    return (
        db.query(func.count(Asset.id)).scalar(),
        db.query(func.count(AssetIdentifier.id)).scalar(),
        db.query(func.count(RegistryFinding.id)).scalar(),
    )


# ── Grouping ─────────────────────────────────────────────────────────────

def test_transactions_sharing_a_claim_shape_resolve_once():
    db = make_session()
    p = _seed_portfolio(db)
    _tx(db, p, symbol="TESTCO")
    _tx(db, p, symbol="TESTCO")
    _tx(db, p, symbol="TESTCO")
    db.commit()

    plan = planner.plan_migration(db, portfolio_ids=[p.id])

    assert len(plan.resolutions) == 1
    assert len(plan.resolutions[0].transaction_ids) == 3
    assert plan.total_transactions == 3


def test_same_claim_shape_across_two_portfolios_resolves_once_globally():
    db = make_session()
    p1 = _seed_portfolio(db, name="P1")
    p2 = Portfolio(workspace_id=p1.workspace_id, name="P2", cash_balance=0.0)
    db.add(p2)
    db.flush()
    _tx(db, p1, symbol="TESTCO")
    _tx(db, p2, symbol="TESTCO")
    db.commit()

    plan = planner.plan_migration(db, portfolio_ids=[p1.id, p2.id])

    assert len(plan.resolutions) == 1
    resolution = plan.resolutions[0]
    assert set(resolution.portfolio_ids) == {p1.id, p2.id}
    assert len(resolution.transaction_ids) == 2


def test_different_currency_is_a_different_claim_shape():
    db = make_session()
    p = _seed_portfolio(db)
    _tx(db, p, symbol="AAPL", currency="USD")
    _tx(db, p, symbol="AAPL", currency="THB")
    db.commit()

    plan = planner.plan_migration(db, portfolio_ids=[p.id])

    assert len(plan.resolutions) == 2


# ── Cash-only handling ───────────────────────────────────────────────────

def test_cash_only_transactions_never_enter_claim_shapes_or_count_as_unknown():
    db = make_session()
    p = _seed_portfolio(db)
    _tx(db, p, symbol=None, transaction_type="DEPOSIT")
    _tx(db, p, symbol="TESTCO")
    db.commit()

    plan = planner.plan_migration(db, portfolio_ids=[p.id])

    assert len(plan.cash_only.transaction_ids) == 1
    assert plan.cash_only.portfolio_ids == (p.id,)
    assert len(plan.resolutions) == 1
    assert plan.resolutions[0].shape.raw_symbol == "TESTCO"


# ── Verdicts against a seeded Registry ────────────────────────────────────

def test_resolved_claim_shape_carries_true_asset_market_exchange():
    db = make_session()
    p = _seed_portfolio(db)
    asset = svc.mint_asset(
        db,
        AssetClaim(canonical_symbol="KBANK", asset_type=AssetType.EQUITY, market="TH", exchange="SET", currency="THB"),
    )
    svc.attach_identifier(
        db, asset.id, IdentifierRecord(identifier_type=IdentifierType.PROVIDER_SYMBOL, value="KBANK.BK", source="seed"),
    )
    _tx(db, p, symbol="KBANK")
    db.commit()

    plan = planner.plan_migration(db, portfolio_ids=[p.id])

    assert len(plan.resolutions) == 1
    res = plan.resolutions[0]
    assert res.result.verdict == ResolutionVerdict.RESOLVED
    assert res.resolved_market == "TH"
    assert res.resolved_exchange == "SET"
    assert res.resolved_currency == "THB"


def test_unknown_when_nothing_in_registry_matches():
    db = make_session()
    p = _seed_portfolio(db)
    _tx(db, p, symbol="NEWCO")
    db.commit()

    plan = planner.plan_migration(db, portfolio_ids=[p.id])

    assert plan.resolutions[0].result.verdict == ResolutionVerdict.UNKNOWN
    assert plan.resolutions[0].resolved_market is None


def test_ambiguous_when_only_a_historical_weak_match_exists():
    # NVDA01 is a DR symbol (services.symbol_resolver.is_dr) — the Listing
    # Equivalence Rule never bundles a DR pair, so the claim carries
    # "NVDA01" alone. Superseding it on the same asset leaves it historical
    # only (weight 50 * historical_multiplier 0.95 = 47.5), which alone is
    # below resolved_threshold (50) -> AMBIGUOUS. The transaction's currency
    # is deliberately set to mismatch the asset's ("USD" vs "THB") so the
    # currency corroboration penalty doesn't accidentally offset that —
    # build_claim always passes the ledger transaction's own currency as a
    # corroboration hint, and a same-currency match would otherwise add
    # +10 and push this case over the RESOLVED threshold.
    db = make_session()
    p = _seed_portfolio(db)
    asset = svc.mint_asset(
        db,
        AssetClaim(canonical_symbol="NVDA01", asset_type=AssetType.EQUITY, market="TH", exchange="SET", currency="THB"),
    )
    svc.attach_identifier(
        db, asset.id, IdentifierRecord(identifier_type=IdentifierType.PROVIDER_SYMBOL, value="NVDA01", source="seed"),
    )
    svc.attach_identifier(
        db, asset.id, IdentifierRecord(identifier_type=IdentifierType.PROVIDER_SYMBOL, value="NVDA01-RENAMED", source="seed"),
    )
    _tx(db, p, symbol="NVDA01", currency="USD")
    db.commit()

    plan = planner.plan_migration(db, portfolio_ids=[p.id])

    assert len(plan.resolutions) == 1
    res = plan.resolutions[0]
    assert res.shape.canonical_symbol != "NVDA01"  # DR mapping, never bundled
    assert res.result.verdict == ResolutionVerdict.AMBIGUOUS
    assert res.result.finding is not None


def test_conflict_when_bundled_pair_points_at_two_different_assets():
    # KBANK / KBANK.BK is a venue-suffix pair (bundles into one claim with
    # two identifiers). If, by data-quality accident, "KBANK" is currently
    # attached to one asset and "KBANK.BK" to a *different* asset, the
    # bundled claim's evidence contradicts itself right now -> CONFLICT.
    db = make_session()
    p = _seed_portfolio(db)
    asset_a = svc.mint_asset(
        db, AssetClaim(canonical_symbol="KBANK-A", asset_type=AssetType.EQUITY, market="TH", exchange="SET", currency="THB"),
    )
    asset_b = svc.mint_asset(
        db, AssetClaim(canonical_symbol="KBANK-B", asset_type=AssetType.EQUITY, market="TH", exchange="SET", currency="THB"),
    )
    svc.attach_identifier(db, asset_a.id, IdentifierRecord(identifier_type=IdentifierType.PROVIDER_SYMBOL, value="KBANK", source="seed"))
    svc.attach_identifier(db, asset_b.id, IdentifierRecord(identifier_type=IdentifierType.PROVIDER_SYMBOL, value="KBANK.BK", source="seed"))
    _tx(db, p, symbol="KBANK")
    db.commit()

    plan = planner.plan_migration(db, portfolio_ids=[p.id])

    assert len(plan.resolutions) == 1
    res = plan.resolutions[0]
    assert res.result.verdict == ResolutionVerdict.CONFLICT
    assert res.result.finding is not None
    assert {c.asset_id for c in res.result.candidates} == {asset_a.id, asset_b.id}


# ── Scoping ────────────────────────────────────────────────────────────────

def test_portfolio_ids_scoping_excludes_other_portfolios():
    db = make_session()
    p1 = _seed_portfolio(db, name="P1")
    p2 = Portfolio(workspace_id=p1.workspace_id, name="P2", cash_balance=0.0)
    db.add(p2)
    db.flush()
    _tx(db, p1, symbol="ONLYP1")
    _tx(db, p2, symbol="ONLYP2")
    db.commit()

    plan = planner.plan_migration(db, portfolio_ids=[p1.id])

    assert plan.total_transactions == 1
    assert plan.portfolios_scanned == (p1.id,)
    assert plan.resolutions[0].shape.raw_symbol == "ONLYP1"


# ── The dry run guarantee ────────────────────────────────────────────────

def test_plan_migration_leaves_zero_net_rows_despite_internal_finding_writes():
    db = make_session()
    p = _seed_portfolio(db)

    # AMBIGUOUS setup
    asset_amb = svc.mint_asset(
        db, AssetClaim(canonical_symbol="NVDA01", asset_type=AssetType.EQUITY, market="TH", exchange="SET", currency="THB"),
    )
    svc.attach_identifier(db, asset_amb.id, IdentifierRecord(identifier_type=IdentifierType.PROVIDER_SYMBOL, value="NVDA01", source="seed"))
    svc.attach_identifier(db, asset_amb.id, IdentifierRecord(identifier_type=IdentifierType.PROVIDER_SYMBOL, value="NVDA01-RENAMED", source="seed"))

    # CONFLICT setup
    asset_a = svc.mint_asset(
        db, AssetClaim(canonical_symbol="KBANK-A", asset_type=AssetType.EQUITY, market="TH", exchange="SET", currency="THB"),
    )
    asset_b = svc.mint_asset(
        db, AssetClaim(canonical_symbol="KBANK-B", asset_type=AssetType.EQUITY, market="TH", exchange="SET", currency="THB"),
    )
    svc.attach_identifier(db, asset_a.id, IdentifierRecord(identifier_type=IdentifierType.PROVIDER_SYMBOL, value="KBANK", source="seed"))
    svc.attach_identifier(db, asset_b.id, IdentifierRecord(identifier_type=IdentifierType.PROVIDER_SYMBOL, value="KBANK.BK", source="seed"))

    # NVDA01's currency deliberately mismatches its asset's THB (see
    # test_ambiguous_when_only_a_historical_weak_match_exists for why).
    _tx(db, p, symbol="NVDA01", currency="USD")
    _tx(db, p, symbol="KBANK")
    db.commit()

    before = _row_counts(db)
    plan = planner.plan_migration(db, portfolio_ids=[p.id])
    after = _row_counts(db)

    assert before == after

    verdicts = {res.shape.raw_symbol: res.result.verdict for res in plan.resolutions}
    assert verdicts["NVDA01"] == ResolutionVerdict.AMBIGUOUS
    assert verdicts["KBANK"] == ResolutionVerdict.CONFLICT

    # Confirm the findings really were created (and rolled back), not
    # silently skipped — resolve() is called completely unmodified.
    for res in plan.resolutions:
        assert res.result.finding is not None
