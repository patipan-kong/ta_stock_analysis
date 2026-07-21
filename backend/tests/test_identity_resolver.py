"""Tests for the Identity Resolution Engine (Milestone M3).

Validates:
  1. Current-identifier match resolves decisively (RESOLVED)
  2. Unique historical-only match still resolves decisively (RESOLVED) —
     ASSET_REGISTRY.md Section 2's "ticker retired, statement imported
     years later" requirement
  3. A current mapping preempts an asset's own stale history for the same
     value (no false ambiguity against oneself)
  4. Strong identifier matching nothing anywhere -> CANDIDATE, never mints
  5. Weak identifier / no identifiers matching nothing -> UNKNOWN
  6. A single weak-identifier match is AMBIGUOUS, not silently resolved
  7. Two different identifiers with current mappings to two different
     assets -> CONFLICT (live contradiction)
  8. A recycled identifier value with two historical owners and no current
     claimant -> AMBIGUOUS, not CONFLICT
  9. AMBIGUOUS/CONFLICT verdicts create a durable RegistryFinding;
     RESOLVED/CANDIDATE/UNKNOWN do not
  10. adjudicate(CONFIRM_MATCH) records the mapping and a later resolve()
      of the same claim now resolves decisively
  11. adjudicate(CONFIRM_NEW) and adjudicate(NOT_A_MATCH) close the finding
      without attaching or minting anything
  12. resolve() never mints or merges under any verdict

All tests use an in-memory SQLite database; no network calls.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base
import models.asset  # noqa: F401 — registers Asset* tables on Base.metadata
import models.registry_finding  # noqa: F401 — registers RegistryFinding table
from services import identity_resolver as resolver
from services import registry_service as svc
from services.asset_domain import AssetClaim, AssetType, IdentifierRecord, IdentifierType
from services.registry_domain import FindingStatus
from services.resolver_domain import AdjudicationDecision, ResolutionClaim, ResolutionVerdict


def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _claim(**overrides):
    defaults = dict(
        canonical_symbol="KBANK",
        asset_type=AssetType.EQUITY,
        market="TH",
        exchange="SET",
        currency="THB",
    )
    defaults.update(overrides)
    return AssetClaim(**defaults)


def _asset_count(db) -> int:
    from models.asset import Asset
    return db.query(Asset).count()


def _finding_count(db) -> int:
    from models.registry_finding import RegistryFinding
    return db.query(RegistryFinding).count()


# ── RESOLVED ─────────────────────────────────────────────────────────────

def test_resolve_current_identifier_match_resolves():
    db = make_session()
    asset = svc.mint_asset(db, _claim())
    svc.attach_identifier(db, asset.id, IdentifierRecord(IdentifierType.ISIN, "TH0001010006", source="manual"))

    result = resolver.resolve(
        db, ResolutionClaim(identifiers=(IdentifierRecord(IdentifierType.ISIN, "TH0001010006", source="claim"),)),
    )

    assert result.verdict == ResolutionVerdict.RESOLVED
    assert result.resolved_asset_id == asset.id
    assert result.finding is None
    assert len(result.candidates) == 1
    assert result.candidates[0].asset_id == asset.id


def test_resolve_unique_historical_match_still_resolves():
    db = make_session()
    asset = svc.mint_asset(db, _claim())
    svc.attach_identifier(db, asset.id, IdentifierRecord(IdentifierType.ISIN, "TH0001010006", source="yfinance"))
    # supersede with a different ISIN value — the old value becomes historical
    svc.attach_identifier(db, asset.id, IdentifierRecord(IdentifierType.ISIN, "TH0001010999", source="yfinance"))

    result = resolver.resolve(
        db, ResolutionClaim(identifiers=(IdentifierRecord(IdentifierType.ISIN, "TH0001010006", source="claim"),)),
    )

    assert result.verdict == ResolutionVerdict.RESOLVED
    assert result.resolved_asset_id == asset.id
    assert result.candidates[0].contributions[0].is_current is False


def test_current_mapping_preempts_own_stale_history():
    """An asset's superseded identifier value must not make a fresh claim
    against its *current* value look ambiguous against itself."""
    db = make_session()
    asset = svc.mint_asset(db, _claim())
    svc.attach_identifier(db, asset.id, IdentifierRecord(IdentifierType.PROVIDER_SYMBOL, "KBANK.BK", source="yfinance"))
    svc.attach_identifier(db, asset.id, IdentifierRecord(IdentifierType.ISIN, "TH0001010006", source="manual"))

    result = resolver.resolve(
        db,
        ResolutionClaim(identifiers=(
            IdentifierRecord(IdentifierType.ISIN, "TH0001010006", source="claim"),
            IdentifierRecord(IdentifierType.PROVIDER_SYMBOL, "KBANK.BK", source="claim"),
        )),
    )

    assert result.verdict == ResolutionVerdict.RESOLVED
    assert result.resolved_asset_id == asset.id


# ── CANDIDATE / UNKNOWN ──────────────────────────────────────────────────

def test_strong_identifier_matching_nothing_is_candidate():
    db = make_session()

    result = resolver.resolve(
        db, ResolutionClaim(identifiers=(IdentifierRecord(IdentifierType.ISIN, "US0000000001", source="claim"),)),
    )

    assert result.verdict == ResolutionVerdict.CANDIDATE
    assert result.resolved_asset_id is None
    assert result.finding is None
    assert _asset_count(db) == 0  # never auto-created


def test_weak_identifier_matching_nothing_is_unknown():
    db = make_session()

    result = resolver.resolve(
        db, ResolutionClaim(identifiers=(IdentifierRecord(IdentifierType.BROKER_CODE, "XYZ1", source="claim"),)),
    )

    assert result.verdict == ResolutionVerdict.UNKNOWN
    assert result.resolved_asset_id is None
    assert result.finding is None


def test_empty_claim_is_unknown():
    db = make_session()

    result = resolver.resolve(db, ResolutionClaim(identifiers=()))

    assert result.verdict == ResolutionVerdict.UNKNOWN
    assert result.candidates == ()


# ── AMBIGUOUS ────────────────────────────────────────────────────────────

def test_single_weak_match_is_ambiguous_not_resolved():
    db = make_session()
    asset = svc.mint_asset(db, _claim())
    svc.attach_identifier(db, asset.id, IdentifierRecord(IdentifierType.BROKER_CODE, "BR1", source="broker"))

    result = resolver.resolve(
        db, ResolutionClaim(identifiers=(IdentifierRecord(IdentifierType.BROKER_CODE, "BR1", source="claim"),)),
    )

    assert result.verdict == ResolutionVerdict.AMBIGUOUS
    assert result.resolved_asset_id is None
    assert result.finding is not None
    assert result.finding.status == FindingStatus.OPEN.value


def test_recycled_identifier_no_current_claimant_is_ambiguous_not_conflict():
    db = make_session()
    asset_a = svc.mint_asset(db, _claim(canonical_symbol="AAA"))
    asset_d = svc.mint_asset(db, _claim(canonical_symbol="DDD"))

    svc.attach_identifier(db, asset_a.id, IdentifierRecord(IdentifierType.CUSIP, "C1", source="manual"))
    svc.attach_identifier(db, asset_a.id, IdentifierRecord(IdentifierType.CUSIP, "C2", source="manual"))  # C1 -> historical on A

    svc.attach_identifier(db, asset_d.id, IdentifierRecord(IdentifierType.CUSIP, "C1", source="manual"))  # legal: C1 no longer current on A
    svc.attach_identifier(db, asset_d.id, IdentifierRecord(IdentifierType.CUSIP, "C3", source="manual"))  # C1 -> historical on D too

    result = resolver.resolve(
        db, ResolutionClaim(identifiers=(IdentifierRecord(IdentifierType.CUSIP, "C1", source="claim"),)),
    )

    assert result.verdict == ResolutionVerdict.AMBIGUOUS
    assert result.resolved_asset_id is None
    assert {c.asset_id for c in result.candidates} == {asset_a.id, asset_d.id}
    assert result.finding is not None
    assert result.finding.related_asset_id is not None


# ── CONFLICT ─────────────────────────────────────────────────────────────

def test_two_current_identifiers_different_assets_is_conflict():
    db = make_session()
    asset_a = svc.mint_asset(db, _claim(canonical_symbol="AAA"))
    asset_b = svc.mint_asset(db, _claim(canonical_symbol="BBB"))

    svc.attach_identifier(db, asset_a.id, IdentifierRecord(IdentifierType.ISIN, "US1111111111", source="manual"))
    svc.attach_identifier(db, asset_b.id, IdentifierRecord(IdentifierType.PROVIDER_SYMBOL, "BBB.BK", source="yfinance"))

    result = resolver.resolve(
        db,
        ResolutionClaim(identifiers=(
            IdentifierRecord(IdentifierType.ISIN, "US1111111111", source="claim"),
            IdentifierRecord(IdentifierType.PROVIDER_SYMBOL, "BBB.BK", source="claim"),
        )),
    )

    assert result.verdict == ResolutionVerdict.CONFLICT
    assert result.resolved_asset_id is None
    assert {c.asset_id for c in result.candidates} == {asset_a.id, asset_b.id}
    assert result.finding is not None
    assert result.finding.status == FindingStatus.OPEN.value


# ── Adjudication ─────────────────────────────────────────────────────────

def test_adjudicate_confirm_match_closes_finding():
    db = make_session()
    asset = svc.mint_asset(db, _claim())
    svc.attach_identifier(db, asset.id, IdentifierRecord(IdentifierType.BROKER_CODE, "BR1", source="broker"))

    claim = ResolutionClaim(identifiers=(IdentifierRecord(IdentifierType.BROKER_CODE, "BR1", source="claim"),))
    first = resolver.resolve(db, claim)
    assert first.verdict == ResolutionVerdict.AMBIGUOUS

    finding = resolver.adjudicate(
        db, first.finding.id, AdjudicationDecision.CONFIRM_MATCH,
        asset_id=asset.id, resolution_note="confirmed by ops", resolved_by="tester",
    )
    assert finding.status == FindingStatus.RESOLVED.value
    assert finding.resolution == AdjudicationDecision.CONFIRM_MATCH.value


def test_adjudicate_confirm_match_resolves_decisively_next_time():
    """A provider symbol that is only historical (its original holder has
    since moved on) scores below the resolved threshold — AMBIGUOUS. A
    human researches and confirms the symbol was recycled onto a different,
    currently-listed asset; adjudicate() records that as the new current
    mapping. A later resolve() of the identical claim is then decisive —
    the same question is never asked twice."""
    db = make_session()
    old_asset = svc.mint_asset(db, _claim(canonical_symbol="OLDCO"))
    new_asset = svc.mint_asset(db, _claim(canonical_symbol="NEWCO"))

    svc.attach_identifier(db, old_asset.id, IdentifierRecord(IdentifierType.PROVIDER_SYMBOL, "RECYCLED.BK", source="yfinance"))
    svc.attach_identifier(db, old_asset.id, IdentifierRecord(IdentifierType.PROVIDER_SYMBOL, "OLDCO2.BK", source="yfinance"))  # supersedes -> historical

    claim = ResolutionClaim(identifiers=(IdentifierRecord(IdentifierType.PROVIDER_SYMBOL, "RECYCLED.BK", source="claim"),))
    first = resolver.resolve(db, claim)
    assert first.verdict == ResolutionVerdict.AMBIGUOUS
    assert first.candidates[0].asset_id == old_asset.id

    resolver.adjudicate(
        db, first.finding.id, AdjudicationDecision.CONFIRM_MATCH,
        asset_id=new_asset.id, resolution_note="RECYCLED.BK was reassigned to NEWCO by the exchange", resolved_by="tester",
    )

    second = resolver.resolve(db, claim)
    assert second.verdict == ResolutionVerdict.RESOLVED
    assert second.resolved_asset_id == new_asset.id


def test_adjudicate_confirm_new_closes_finding_without_minting():
    db = make_session()
    asset = svc.mint_asset(db, _claim())
    svc.attach_identifier(db, asset.id, IdentifierRecord(IdentifierType.BROKER_CODE, "BR1", source="broker"))

    claim = ResolutionClaim(identifiers=(IdentifierRecord(IdentifierType.BROKER_CODE, "BR1", source="claim"),))
    result = resolver.resolve(db, claim)
    count_before = _asset_count(db)

    finding = resolver.adjudicate(
        db, result.finding.id, AdjudicationDecision.CONFIRM_NEW,
        resolution_note="genuinely a different instrument", resolved_by="tester",
    )

    assert finding.status == FindingStatus.RESOLVED.value
    assert finding.resolution == AdjudicationDecision.CONFIRM_NEW.value
    assert _asset_count(db) == count_before  # never auto-created


def test_adjudicate_not_a_match_dismisses_finding():
    db = make_session()
    asset = svc.mint_asset(db, _claim())
    svc.attach_identifier(db, asset.id, IdentifierRecord(IdentifierType.BROKER_CODE, "BR1", source="broker"))

    claim = ResolutionClaim(identifiers=(IdentifierRecord(IdentifierType.BROKER_CODE, "BR1", source="claim"),))
    result = resolver.resolve(db, claim)

    finding = resolver.adjudicate(
        db, result.finding.id, AdjudicationDecision.NOT_A_MATCH,
        resolution_note="not actually related", resolved_by="tester",
    )

    assert finding.status == FindingStatus.DISMISSED.value
    assert finding.resolution == AdjudicationDecision.NOT_A_MATCH.value


def test_adjudicate_confirm_match_requires_asset_id():
    db = make_session()
    asset = svc.mint_asset(db, _claim())
    svc.attach_identifier(db, asset.id, IdentifierRecord(IdentifierType.BROKER_CODE, "BR1", source="broker"))
    claim = ResolutionClaim(identifiers=(IdentifierRecord(IdentifierType.BROKER_CODE, "BR1", source="claim"),))
    result = resolver.resolve(db, claim)

    with pytest.raises(svc.AssetRegistryError):
        resolver.adjudicate(
            db, result.finding.id, AdjudicationDecision.CONFIRM_MATCH, resolution_note="missing asset_id",
        )


# ── Never auto-create / never auto-merge invariant ──────────────────────

@pytest.mark.parametrize(
    "identifiers",
    [
        (),  # UNKNOWN
        (IdentifierRecord(IdentifierType.BROKER_CODE, "NOPE", source="claim"),),  # UNKNOWN
        (IdentifierRecord(IdentifierType.ISIN, "US9999999999", source="claim"),),  # CANDIDATE
    ],
)
def test_resolve_never_mutates_assets_table(identifiers):
    db = make_session()
    before = _asset_count(db)

    resolver.resolve(db, ResolutionClaim(identifiers=identifiers))

    assert _asset_count(db) == before


# ── record_finding=False (M37.1 WP2a) ───────────────────────────────────
# Universal Asset Search reuses resolve()'s matching/scoring logic to
# preview a claim without writing to the Registry's findings audit trail.
# Every case below is run twice — default (True) and explicit False — to
# prove the two calls differ *only* in whether a RegistryFinding row is
# written, never in the returned ResolutionResult's verdict/candidates.

def test_default_record_finding_still_records_ambiguous():
    """Calling resolve() with no record_finding argument at all — the
    exact call shape every pre-existing caller uses — must keep writing
    findings. This is the backward-compatibility guarantee itself."""
    db = make_session()
    asset = svc.mint_asset(db, _claim())
    svc.attach_identifier(db, asset.id, IdentifierRecord(IdentifierType.BROKER_CODE, "BR1", source="broker"))

    result = resolver.resolve(
        db, ResolutionClaim(identifiers=(IdentifierRecord(IdentifierType.BROKER_CODE, "BR1", source="claim"),)),
    )

    assert result.verdict == ResolutionVerdict.AMBIGUOUS
    assert result.finding is not None
    assert _finding_count(db) == 1


def test_record_finding_false_never_records_ambiguous():
    """Two calls against the same DB state — one with record_finding=True,
    one with False — must return an identical verdict/candidates/score, and
    differ only in whether a RegistryFinding was written."""
    db = make_session()
    asset = svc.mint_asset(db, _claim())
    svc.attach_identifier(db, asset.id, IdentifierRecord(IdentifierType.BROKER_CODE, "BR1", source="broker"))
    claim = ResolutionClaim(identifiers=(IdentifierRecord(IdentifierType.BROKER_CODE, "BR1", source="claim"),))

    recorded = resolver.resolve(db, claim, record_finding=True)
    non_recorded = resolver.resolve(db, claim, record_finding=False)

    assert non_recorded.verdict == recorded.verdict == ResolutionVerdict.AMBIGUOUS
    assert non_recorded.finding is None
    assert non_recorded.resolved_asset_id == recorded.resolved_asset_id
    assert [c.asset_id for c in non_recorded.candidates] == [c.asset_id for c in recorded.candidates]
    assert [c.score for c in non_recorded.candidates] == [c.score for c in recorded.candidates]
    # exactly one finding exists — from the record_finding=True call only
    assert _finding_count(db) == 1


def test_record_finding_false_never_records_conflict():
    db = make_session()
    asset_a = svc.mint_asset(db, _claim(canonical_symbol="AAA"))
    asset_b = svc.mint_asset(db, _claim(canonical_symbol="BBB"))
    svc.attach_identifier(db, asset_a.id, IdentifierRecord(IdentifierType.ISIN, "US1111111111", source="manual"))
    svc.attach_identifier(db, asset_b.id, IdentifierRecord(IdentifierType.PROVIDER_SYMBOL, "BBB.BK", source="yfinance"))
    claim = ResolutionClaim(identifiers=(
        IdentifierRecord(IdentifierType.ISIN, "US1111111111", source="claim"),
        IdentifierRecord(IdentifierType.PROVIDER_SYMBOL, "BBB.BK", source="claim"),
    ))

    result = resolver.resolve(db, claim, record_finding=False)

    assert result.verdict == ResolutionVerdict.CONFLICT
    assert result.resolved_asset_id is None
    assert {c.asset_id for c in result.candidates} == {asset_a.id, asset_b.id}
    assert result.finding is None
    assert _finding_count(db) == 0


@pytest.mark.parametrize("record_finding", [True, False])
def test_record_finding_flag_does_not_change_resolved_verdict(record_finding):
    """RESOLVED never wrote a finding either way — record_finding must not
    change that, and must not change the resolved asset."""
    db = make_session()
    asset = svc.mint_asset(db, _claim())
    svc.attach_identifier(db, asset.id, IdentifierRecord(IdentifierType.ISIN, "TH0001010006", source="manual"))

    result = resolver.resolve(
        db,
        ResolutionClaim(identifiers=(IdentifierRecord(IdentifierType.ISIN, "TH0001010006", source="claim"),)),
        record_finding=record_finding,
    )

    assert result.verdict == ResolutionVerdict.RESOLVED
    assert result.resolved_asset_id == asset.id
    assert result.finding is None
    assert _finding_count(db) == 0


@pytest.mark.parametrize("record_finding", [True, False])
def test_record_finding_flag_does_not_change_unknown_verdict(record_finding):
    db = make_session()

    result = resolver.resolve(
        db,
        ResolutionClaim(identifiers=(IdentifierRecord(IdentifierType.BROKER_CODE, "XYZ1", source="claim"),)),
        record_finding=record_finding,
    )

    assert result.verdict == ResolutionVerdict.UNKNOWN
    assert result.finding is None
    assert _finding_count(db) == 0


def test_record_finding_false_leaves_adjudicate_unaffected():
    """A record_finding=False preview call must not interfere with the
    normal finding lifecycle for a subsequent, normally-recorded claim —
    there is exactly one resolver, one code path, no second implementation
    silently diverging in adjudicate()'s reach."""
    db = make_session()
    asset = svc.mint_asset(db, _claim())
    svc.attach_identifier(db, asset.id, IdentifierRecord(IdentifierType.BROKER_CODE, "BR1", source="broker"))
    claim = ResolutionClaim(identifiers=(IdentifierRecord(IdentifierType.BROKER_CODE, "BR1", source="claim"),))

    preview = resolver.resolve(db, claim, record_finding=False)
    assert preview.finding is None
    assert _finding_count(db) == 0

    recorded = resolver.resolve(db, claim)
    assert recorded.finding is not None
    assert _finding_count(db) == 1

    finding = resolver.adjudicate(
        db, recorded.finding.id, AdjudicationDecision.CONFIRM_MATCH,
        asset_id=asset.id, resolution_note="confirmed by ops", resolved_by="tester",
    )
    assert finding.status == FindingStatus.RESOLVED.value
