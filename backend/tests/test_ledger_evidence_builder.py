"""Tests for the Ledger Replay Evidence Builder (Milestone M5.0).

Validates:
  1. A venue-suffix pair (KBANK / KBANK.BK) bundles into one claim with
     two PROVIDER_SYMBOL identifiers
  2. An identical pair produces a single-identifier claim (no duplicate)
  3. A DR-mapped pair (CATL01 / 300750.SZ) produces a single-identifier
     claim built from raw_symbol alone — canonical_symbol is never
     admitted as identity evidence
  4. A cash-only transaction (no symbol) produces a claim with zero
     identifiers, never None — same contract as provider_adapter
  5. market/exchange/currency/requested_by/note pass through unchanged
  6. build_claim_from_transaction() extracts raw_symbol/canonical_symbol
     and created_at correctly from a CanonicalTransaction
  7. End-to-end: a claim built by this module resolves exactly like a
     hand-built one — proving the KBANK/KBANK.BK BLOCKER is actually
     fixed by identity_resolver.resolve(), unmodified
"""
import os
import sys
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base
import models.asset  # noqa: F401 — registers Asset* tables on Base.metadata
import models.registry_finding  # noqa: F401 — registers RegistryFinding table
from services import identity_resolver as resolver
from services import ledger_evidence_builder as builder
from services import registry_service as svc
from services.asset_domain import AssetClaim, AssetType, IdentifierRecord, IdentifierType
from services.resolver_domain import ResolutionVerdict
from services.transaction_canonicalizer import CanonicalTransaction


def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _transaction(**overrides) -> CanonicalTransaction:
    defaults = dict(
        id=1,
        transaction_type="BUY",
        raw_symbol="KBANK",
        canonical_symbol="KBANK.BK",
        shares=Decimal("100"),
        price_per_share=Decimal("150"),
        total_amount=Decimal("15000"),
        fees=Decimal("0"),
        taxes=Decimal("0"),
        transaction_date=date(2024, 1, 15),
        created_at=datetime(2024, 1, 15, 9, 30, tzinfo=timezone.utc),
        sector=None,
        notes=None,
        qty_correction_delta=None,
        realized_pnl=None,
    )
    defaults.update(overrides)
    return CanonicalTransaction(**defaults)


# ── build_claim() — bundling behavior ───────────────────────────────────

def test_venue_suffix_pair_bundles_into_one_claim_two_identifiers():
    claim = builder.build_claim("KBANK", "KBANK.BK")
    assert len(claim.identifiers) == 2
    values = {i.value for i in claim.identifiers}
    assert values == {"KBANK", "KBANK.BK"}
    assert all(i.identifier_type == IdentifierType.PROVIDER_SYMBOL for i in claim.identifiers)
    assert all(i.source == "ledger:historical" for i in claim.identifiers)


def test_identical_pair_produces_single_identifier():
    claim = builder.build_claim("AAPL", "AAPL")
    assert len(claim.identifiers) == 1
    assert claim.identifiers[0].value == "AAPL"


def test_dr_mapped_pair_uses_raw_symbol_only():
    claim = builder.build_claim("CATL01", "300750.SZ")
    assert len(claim.identifiers) == 1
    assert claim.identifiers[0].value == "CATL01"


def test_generic_dr_suffix_pair_uses_raw_symbol_only():
    claim = builder.build_claim("NVDA01", "NVDA")
    assert len(claim.identifiers) == 1
    assert claim.identifiers[0].value == "NVDA01"


def test_cash_only_transaction_produces_zero_identifiers_not_none():
    claim = builder.build_claim(None, None)
    assert claim is not None
    assert claim.identifiers == ()


def test_context_and_provenance_pass_through():
    claim = builder.build_claim(
        "KBANK",
        "KBANK.BK",
        market="TH",
        exchange="SET",
        currency="THB",
        requested_by="m5_backfill",
        note="portfolio 42 backfill",
    )
    assert claim.market == "TH"
    assert claim.exchange == "SET"
    assert claim.currency == "THB"
    assert claim.requested_by == "m5_backfill"
    assert claim.note == "portfolio 42 backfill"


# ── build_claim_from_transaction() ──────────────────────────────────────

def test_build_claim_from_transaction_extracts_fields():
    tx = _transaction()
    claim = builder.build_claim_from_transaction(tx, market="TH", exchange="SET", currency="THB")
    values = {i.value for i in claim.identifiers}
    assert values == {"KBANK", "KBANK.BK"}
    assert all(i.as_of == tx.created_at for i in claim.identifiers)


def test_build_claim_from_transaction_dr_pair_uses_raw_symbol_only():
    tx = _transaction(raw_symbol="CATL01", canonical_symbol="300750.SZ")
    claim = builder.build_claim_from_transaction(tx)
    assert len(claim.identifiers) == 1
    assert claim.identifiers[0].value == "CATL01"


def test_build_claim_from_transaction_cash_only():
    tx = _transaction(transaction_type="DEPOSIT", raw_symbol=None, canonical_symbol=None)
    claim = builder.build_claim_from_transaction(tx)
    assert claim.identifiers == ()


# ── End-to-end: this is the actual BLOCKER fix ──────────────────────────

def test_bundled_claim_resolves_decisively_to_the_registered_asset():
    """The KBANK/KBANK.BK case, end to end: an asset already carries
    KBANK.BK as its PROVIDER_SYMBOL. A ledger row recorded the raw
    spelling KBANK. Before this milestone, a claim built from KBANK
    alone could not bridge to the asset without a live provider lookup.
    With the bundle, the same historical pair resolves decisively — and
    identity_resolver.resolve() itself required zero changes to do it."""
    db = make_session()
    asset = svc.mint_asset(
        db,
        AssetClaim(
            canonical_symbol="KBANK",
            asset_type=AssetType.EQUITY,
            market="TH",
            exchange="SET",
            currency="THB",
        ),
    )
    svc.attach_identifier(
        db,
        asset.id,
        IdentifierRecord(
            identifier_type=IdentifierType.PROVIDER_SYMBOL,
            value="KBANK.BK",
            source="seed",
        ),
    )

    claim = builder.build_claim("KBANK", "KBANK.BK", market="TH", exchange="SET", currency="THB")
    result = resolver.resolve(db, claim)

    assert result.verdict == ResolutionVerdict.RESOLVED
    assert result.resolved_asset_id == asset.id


def test_dr_pair_never_silently_conflates_with_underlying():
    """A DR-mapped pair must never resolve against an asset registered
    under the underlying's ticker — that would be exactly the identity
    conflation ASSET_REGISTRY.md Section 5 forbids. Registering an asset
    under the underlying's symbol and then resolving a claim built from
    the DR's raw_symbol must NOT find it, because canonical_symbol
    (the underlying) was correctly excluded from the claim."""
    db = make_session()
    svc.mint_asset(
        db,
        AssetClaim(
            canonical_symbol="MU",
            asset_type=AssetType.EQUITY,
            market="US",
            exchange="NASDAQ",
            currency="USD",
        ),
    )

    claim = builder.build_claim("MICRON01", "MU")
    result = resolver.resolve(db, claim)

    assert result.verdict != ResolutionVerdict.RESOLVED
