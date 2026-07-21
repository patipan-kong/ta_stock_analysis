"""Tests for Market Intelligence's Registry Merge (Milestone M37.2, WP3).

Validates docs/implementation/M37_1_Universal_Asset_Search_Technical_Design.md
Section 3/§8 stage 7's merge design against
`services/asset_search/merge.py`:

  1.  Empty registered and discovery inputs
  2.  Registered-only input is preserved
  3.  Unknown discovery candidate remains discovery
  4.  Discovery candidate lacking sufficient identity evidence remains discovery
  5.  RESOLVED discovery collapses to an existing registered candidate
  6.  RESOLVED discovery projects a registered candidate when catalog input
      does not already contain that asset
  7.  Multiple discovery candidates resolving to the same asset produce one
      registered result
  8.  Existing registered candidate is not duplicated by resolved discovery
  9.  AMBIGUOUS discovery remains discovery
  10. CONFLICT discovery remains discovery
  11. UNKNOWN discovery remains discovery
  12. AMBIGUOUS creates zero RegistryFinding rows
  13. CONFLICT creates zero RegistryFinding rows
  14. Resolver is called with record_finding=False
  15. Matching/scoring logic is not duplicated (no registry_query import)
  16. No adjudicate call
  17. No asset minting
  18. No provider calls
  19. No permanent writes across all relevant Registry tables
  20. Original input sequences are not mutated
  21. Candidate objects are not mutated
  22. Deterministic repeated execution
  23. Duplicate registered asset_id inputs are handled per the approved contract
  24. Same raw symbol without resolver proof does not cause collapse
  25. Provider-reported fields do not overwrite Registry facts
  26. Real Registry asset_id is used after resolution
  27. Ranking is not invoked by merge.py (delegated to search_service.py per §8)
  28. Missing resolved Asset row produces the approved internal failure behavior
  29. Historical/current identifier behavior is inherited from the resolver
  30. Structural AST checks for forbidden imports/calls

A CANDIDATE verdict (strong identifier, zero hits) is also verified to
preserve the discovery candidate, even though §12's four-verdict merge
narrative does not name it explicitly - CANDIDATE carries
`resolved_asset_id=None` exactly like AMBIGUOUS/CONFLICT/UNKNOWN, so the
same "collapse only on RESOLVED" branch already covers it correctly.

All tests use an in-memory SQLite database; no network calls.
"""
import ast
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, Optional
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base
import models.asset  # noqa: F401 - registers Asset* tables on Base.metadata
import models.registry_finding  # noqa: F401 - registers RegistryFinding table
from models.asset import Asset, AssetClassification, AssetIdentifier
from models.registry_finding import RegistryFinding
from services import registry_service as svc
from services.asset_domain import AssetClaim, AssetId, AssetType, IdentifierRecord, IdentifierType
from services.asset_search import merge
from services.asset_search.catalog_search import RegisteredCandidate
from services.resolver_domain import ResolutionResult, ResolutionVerdict


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


def _mint(db, **overrides):
    return svc.mint_asset(db, _claim(**overrides))


def _all_row_counts(db) -> dict:
    return {
        "Asset": db.query(Asset).count(),
        "AssetIdentifier": db.query(AssetIdentifier).count(),
        "AssetClassification": db.query(AssetClassification).count(),
        "RegistryFinding": db.query(RegistryFinding).count(),
    }


@dataclass(frozen=True)
class DiscoveryCandidate:
    """Test-local double matching §6's DiscoveryCandidate field shape.
    `merge.py` is duck-typed and does not define or import this class -
    the real contract belongs to WP6's `discovery_search.py`, not yet
    built."""

    kind: str = field(default="DISCOVERY", init=False)
    claim_id: str = ""
    provider_name: str = ""
    reported_symbol: Optional[str] = None
    reported_name: Optional[str] = None
    reported_identifiers: Dict[str, str] = field(default_factory=dict)
    market: Optional[str] = None
    currency: Optional[str] = None
    match_field: str = ""


def _registered_from(asset, match_field="canonical_symbol"):
    return RegisteredCandidate(
        asset_id=asset.id,
        canonical_symbol=asset.canonical_symbol,
        display_symbol=asset.display_symbol,
        asset_type=asset.asset_type,
        market=asset.market,
        exchange=asset.exchange,
        currency=asset.currency,
        classifications={},
        status=asset.status,
        match_field=match_field,
    )


# -- 1. Empty inputs -----------------------------------------------------------

def test_empty_registered_and_discovery_inputs():
    db = make_session()
    assert merge.merge(db, [], []) == []


# -- 2. Registered-only input preserved -----------------------------------------

def test_registered_only_input_is_preserved():
    db = make_session()
    a = _mint(db, canonical_symbol="AAA")
    b = _mint(db, canonical_symbol="BBB")
    rc_a, rc_b = _registered_from(a), _registered_from(b)
    result = merge.merge(db, [rc_a, rc_b], [])
    assert result == [rc_a, rc_b]


# -- 3/11. UNKNOWN discovery remains discovery ----------------------------------

def test_unknown_discovery_candidate_remains_discovery():
    db = make_session()
    discovery = DiscoveryCandidate(
        claim_id="c1", provider_name="p1",
        reported_identifiers={"PROVIDER_SYMBOL": "NOWHERE"},
        match_field="canonical_symbol",
    )
    result = merge.merge(db, [], [discovery])
    assert result == [discovery]


# -- 4. Insufficient identity evidence remains discovery, resolver not called --

def test_discovery_lacking_identity_evidence_remains_discovery_and_skips_resolver():
    db = make_session()
    discovery = DiscoveryCandidate(claim_id="c1", provider_name="p1", reported_identifiers={})
    with patch("services.asset_search.merge.resolve") as mock_resolve:
        result = merge.merge(db, [], [discovery])
    assert result == [discovery]
    mock_resolve.assert_not_called()


def test_discovery_with_only_unrecognized_identifier_keys_remains_discovery():
    db = make_session()
    discovery = DiscoveryCandidate(
        claim_id="c1", provider_name="p1",
        reported_identifiers={"NOT_A_REAL_SCHEME": "X"},
    )
    with patch("services.asset_search.merge.resolve") as mock_resolve:
        result = merge.merge(db, [], [discovery])
    assert result == [discovery]
    mock_resolve.assert_not_called()


# -- 5/8. RESOLVED reuses an existing registered candidate ----------------------

def test_resolved_discovery_reuses_existing_registered_candidate():
    db = make_session()
    asset = _mint(db, canonical_symbol="KBANK")
    svc.attach_identifier(db, asset.id, IdentifierRecord(IdentifierType.ISIN, "TH0001010006", source="manual"))
    db.commit()

    existing = _registered_from(asset)
    discovery = DiscoveryCandidate(
        claim_id="c1", provider_name="p1",
        reported_identifiers={"ISIN": "TH0001010006"},
        reported_symbol="KBANK-DISCOVERY",
    )
    result = merge.merge(db, [existing], [discovery])
    assert result == [existing]  # same object - reused, not re-projected
    assert len(result) == 1


# -- 6. RESOLVED projects a fresh registered candidate --------------------------

def test_resolved_discovery_projects_new_registered_candidate_when_absent_from_catalog_input():
    db = make_session()
    asset = _mint(db, canonical_symbol="KBANK")
    svc.attach_identifier(db, asset.id, IdentifierRecord(IdentifierType.ISIN, "TH0001010006", source="manual"))
    db.commit()

    discovery = DiscoveryCandidate(
        claim_id="c1", provider_name="p1",
        reported_identifiers={"ISIN": "TH0001010006"},
    )
    result = merge.merge(db, [], [discovery])
    assert len(result) == 1
    assert isinstance(result[0], RegisteredCandidate)
    assert result[0].asset_id == asset.id
    assert result[0].canonical_symbol == "KBANK"


# -- 7. Multiple discovery candidates resolving to same asset -> one result ----

def test_multiple_discovery_candidates_resolving_to_same_asset_produce_one_result():
    db = make_session()
    asset = _mint(db, canonical_symbol="KBANK")
    svc.attach_identifier(db, asset.id, IdentifierRecord(IdentifierType.ISIN, "TH0001010006", source="manual"))
    db.commit()

    d1 = DiscoveryCandidate(claim_id="c1", provider_name="p1", reported_identifiers={"ISIN": "TH0001010006"})
    d2 = DiscoveryCandidate(claim_id="c2", provider_name="p2", reported_identifiers={"ISIN": "TH0001010006"})
    result = merge.merge(db, [], [d1, d2])
    assert len(result) == 1
    assert result[0].asset_id == asset.id


# -- 9. AMBIGUOUS discovery remains discovery -----------------------------------

def test_ambiguous_discovery_remains_discovery():
    db = make_session()
    asset = _mint(db, canonical_symbol="KBANK")
    svc.attach_identifier(db, asset.id, IdentifierRecord(IdentifierType.BROKER_CODE, "BK-1", source="manual"))
    db.commit()

    discovery = DiscoveryCandidate(
        claim_id="c1", provider_name="p1",
        reported_identifiers={"BROKER_CODE": "BK-1"},  # weight 20 < resolved_threshold 50
    )
    result = merge.merge(db, [], [discovery])
    assert result == [discovery]


# -- 10. CONFLICT discovery remains discovery -----------------------------------

def test_conflict_discovery_remains_discovery():
    db = make_session()
    asset1 = _mint(db, canonical_symbol="AAA")
    asset2 = _mint(db, canonical_symbol="BBB")
    svc.attach_identifier(db, asset1.id, IdentifierRecord(IdentifierType.ISIN, "ISINAAA", source="manual"))
    svc.attach_identifier(db, asset2.id, IdentifierRecord(IdentifierType.CUSIP, "CUSIPBBB", source="manual"))
    db.commit()

    discovery = DiscoveryCandidate(
        claim_id="c1", provider_name="p1",
        reported_identifiers={"ISIN": "ISINAAA", "CUSIP": "CUSIPBBB"},
    )
    result = merge.merge(db, [], [discovery])
    assert result == [discovery]


# -- CANDIDATE verdict also remains discovery (not explicitly named by §12) ----

def test_candidate_verdict_remains_discovery():
    db = make_session()
    discovery = DiscoveryCandidate(
        claim_id="c1", provider_name="p1",
        reported_identifiers={"ISIN": "NOWHERE-STRONG"},  # strong type, zero hits -> CANDIDATE
    )
    result = merge.merge(db, [], [discovery])
    assert result == [discovery]


# -- 12/13. AMBIGUOUS/CONFLICT create zero RegistryFinding rows -----------------

def test_ambiguous_creates_zero_registry_finding_rows():
    db = make_session()
    asset = _mint(db, canonical_symbol="KBANK")
    svc.attach_identifier(db, asset.id, IdentifierRecord(IdentifierType.BROKER_CODE, "BK-1", source="manual"))
    db.commit()
    before = db.query(RegistryFinding).count()

    discovery = DiscoveryCandidate(claim_id="c1", provider_name="p1", reported_identifiers={"BROKER_CODE": "BK-1"})
    merge.merge(db, [], [discovery])
    assert db.query(RegistryFinding).count() == before == 0


def test_conflict_creates_zero_registry_finding_rows():
    db = make_session()
    asset1 = _mint(db, canonical_symbol="AAA")
    asset2 = _mint(db, canonical_symbol="BBB")
    svc.attach_identifier(db, asset1.id, IdentifierRecord(IdentifierType.ISIN, "ISINAAA", source="manual"))
    svc.attach_identifier(db, asset2.id, IdentifierRecord(IdentifierType.CUSIP, "CUSIPBBB", source="manual"))
    db.commit()
    before = db.query(RegistryFinding).count()

    discovery = DiscoveryCandidate(
        claim_id="c1", provider_name="p1",
        reported_identifiers={"ISIN": "ISINAAA", "CUSIP": "CUSIPBBB"},
    )
    merge.merge(db, [], [discovery])
    assert db.query(RegistryFinding).count() == before == 0


# -- 14. Resolver called with record_finding=False ------------------------------

def test_resolver_called_with_record_finding_false():
    db = make_session()
    asset = _mint(db, canonical_symbol="KBANK")
    svc.attach_identifier(db, asset.id, IdentifierRecord(IdentifierType.ISIN, "TH0001010006", source="manual"))
    db.commit()

    discovery = DiscoveryCandidate(claim_id="c1", provider_name="p1", reported_identifiers={"ISIN": "TH0001010006"})
    with patch("services.asset_search.merge.resolve", wraps=merge.resolve) as mock_resolve:
        merge.merge(db, [], [discovery])
    mock_resolve.assert_called_once()
    _, kwargs = mock_resolve.call_args
    assert kwargs.get("record_finding") is False


# -- 19. Zero permanent writes across all relevant Registry tables -------------

def test_zero_permanent_writes_across_all_relevant_tables():
    db = make_session()
    resolved_asset = _mint(db, canonical_symbol="KBANK")
    svc.attach_identifier(db, resolved_asset.id, IdentifierRecord(IdentifierType.ISIN, "TH0001010006", source="manual"))
    conflict_a = _mint(db, canonical_symbol="AAA")
    conflict_b = _mint(db, canonical_symbol="BBB")
    svc.attach_identifier(db, conflict_a.id, IdentifierRecord(IdentifierType.ISIN, "ISINAAA", source="manual"))
    svc.attach_identifier(db, conflict_b.id, IdentifierRecord(IdentifierType.CUSIP, "CUSIPBBB", source="manual"))
    db.commit()

    before = _all_row_counts(db)

    resolved_discovery = DiscoveryCandidate(claim_id="c1", provider_name="p1", reported_identifiers={"ISIN": "TH0001010006"})
    ambiguous_discovery = DiscoveryCandidate(claim_id="c2", provider_name="p1", reported_identifiers={"BROKER_CODE": "BK-NOPE"})
    conflict_discovery = DiscoveryCandidate(
        claim_id="c3", provider_name="p1",
        reported_identifiers={"ISIN": "ISINAAA", "CUSIP": "CUSIPBBB"},
    )
    unknown_discovery = DiscoveryCandidate(claim_id="c4", provider_name="p1", reported_identifiers={"PROVIDER_SYMBOL": "NOWHERE"})
    insufficient_discovery = DiscoveryCandidate(claim_id="c5", provider_name="p1", reported_identifiers={})

    merge.merge(
        db, [],
        [resolved_discovery, ambiguous_discovery, conflict_discovery, unknown_discovery, insufficient_discovery],
    )

    assert _all_row_counts(db) == before


# -- 20. Original input sequences are not mutated -------------------------------

def test_merge_does_not_mutate_input_sequences():
    db = make_session()
    asset = _mint(db, canonical_symbol="KBANK")
    rc = _registered_from(asset)
    discovery = DiscoveryCandidate(claim_id="c1", provider_name="p1")

    registered_input = [rc]
    discovery_input = [discovery]
    registered_before = list(registered_input)
    discovery_before = list(discovery_input)

    merge.merge(db, registered_input, discovery_input)

    assert registered_input == registered_before
    assert discovery_input == discovery_before


# -- 21. Candidate objects are not mutated ---------------------------------------

def test_merge_does_not_mutate_candidate_objects():
    db = make_session()
    asset = _mint(db, canonical_symbol="KBANK")
    rc = _registered_from(asset)
    discovery = DiscoveryCandidate(claim_id="c1", provider_name="p1", reported_symbol="KBANK")

    merge.merge(db, [rc], [discovery])

    assert rc.canonical_symbol == "KBANK"
    assert discovery.reported_symbol == "KBANK"


# -- 22. Deterministic repeated execution ----------------------------------------

def test_deterministic_repeated_execution():
    db = make_session()
    asset = _mint(db, canonical_symbol="KBANK")
    svc.attach_identifier(db, asset.id, IdentifierRecord(IdentifierType.ISIN, "TH0001010006", source="manual"))
    db.commit()

    discovery = DiscoveryCandidate(claim_id="c1", provider_name="p1", reported_identifiers={"ISIN": "TH0001010006"})
    first = merge.merge(db, [], [discovery])
    second = merge.merge(db, [], [discovery])
    assert first == second


# -- 23. Duplicate registered asset_id inputs handled per approved contract -----

def test_duplicate_registered_asset_id_inputs_are_preserved_not_deduplicated():
    """WP3 does not own catalog-level deduplication (that is WP2's
    responsibility) - its Deduplication section is scoped to discovery-vs-
    Registry collapsing only. A caller/test-supplied duplicate asset_id
    already present twice in registered_candidates is passed through
    unchanged; merge() must not invent a new dedup rule for that case."""
    db = make_session()
    asset = _mint(db, canonical_symbol="KBANK")
    svc.attach_identifier(db, asset.id, IdentifierRecord(IdentifierType.ISIN, "TH0001010006", source="manual"))
    db.commit()

    rc1 = _registered_from(asset)
    rc2 = _registered_from(asset)
    discovery = DiscoveryCandidate(claim_id="c1", provider_name="p1", reported_identifiers={"ISIN": "TH0001010006"})

    result = merge.merge(db, [rc1, rc2], [discovery])
    assert result == [rc1, rc2]  # both duplicates preserved, no third copy added for the resolved discovery


# -- 24. Same raw symbol without resolver proof does not collapse --------------

def test_same_raw_symbol_without_resolver_proof_does_not_collapse():
    db = make_session()
    d1 = DiscoveryCandidate(claim_id="c1", provider_name="p1", reported_symbol="SAME", reported_identifiers={})
    d2 = DiscoveryCandidate(claim_id="c2", provider_name="p2", reported_symbol="SAME", reported_identifiers={})
    result = merge.merge(db, [], [d1, d2])
    assert result == [d1, d2]
    assert len(result) == 2


# -- 25/26. Provider fields never overwrite Registry facts; real asset_id used --

def test_provider_reported_fields_do_not_overwrite_registry_facts():
    db = make_session()
    asset = _mint(db, canonical_symbol="KBANK", market="TH", exchange="SET", currency="THB")
    svc.attach_identifier(db, asset.id, IdentifierRecord(IdentifierType.ISIN, "TH0001010006", source="manual"))
    db.commit()

    discovery = DiscoveryCandidate(
        claim_id="c1", provider_name="p1",
        reported_symbol="WRONG-SYMBOL", reported_name="Wrong Name",
        market="US", currency="USD",
        reported_identifiers={"ISIN": "TH0001010006"},
    )
    result = merge.merge(db, [], [discovery])
    projected = result[0]
    assert projected.canonical_symbol == "KBANK"
    assert projected.market == "TH"
    assert projected.currency == "THB"
    assert projected.asset_id == asset.id  # 26: real Registry asset_id used


# -- 27. Ranking is not invoked by merge.py --------------------------------------

def _merge_module_tree():
    module_path = os.path.join(
        os.path.dirname(__file__), "..", "services", "asset_search", "merge.py",
    )
    with open(module_path, "r", encoding="utf-8") as f:
        return ast.parse(f.read())


def _imported_names(tree):
    imported_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_names.add(node.module)
            imported_names.update(alias.name for alias in node.names)
    return imported_names


def test_merge_module_does_not_import_ranking():
    imported_names = _imported_names(_merge_module_tree())
    forbidden = {"ranking", "services.asset_search.ranking", "rank"}
    found = imported_names & forbidden
    assert not found, f"merge.py must not import ranking.py; found: {found}"


def test_merge_module_never_calls_a_function_named_rank():
    tree = _merge_module_tree()
    found = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "rank"
    }
    assert not found


# -- 28. Missing resolved Asset row -> internal consistency failure -----------

def test_missing_resolved_asset_row_raises_registry_consistency_error():
    db = make_session()
    discovery = DiscoveryCandidate(claim_id="c1", provider_name="p1", reported_identifiers={"ISIN": "DOES-NOT-MATTER"})

    fabricated_result = ResolutionResult(
        verdict=ResolutionVerdict.RESOLVED,
        resolved_asset_id=AssetId(999999),  # no Asset row with this id exists
        candidates=(),
        claim_evaluations=(),
    )
    with patch("services.asset_search.merge.resolve", return_value=fabricated_result):
        with pytest.raises(merge.RegistryConsistencyError):
            merge.merge(db, [], [discovery])


# -- 29. Historical/current identifier behavior inherited from resolver -------

def test_historical_only_identifier_still_resolves_via_inherited_resolver_doctrine():
    """Mirrors identity_resolver.py's own doctrine (see
    test_asset_search_catalog.py's equivalent test): a purely historical
    identifier with no live claimant elsewhere still resolves decisively
    when it is the only evidence - merge.py inherits this behavior for
    free by calling resolve(), never re-deciding it independently."""
    db = make_session()
    asset = _mint(db, canonical_symbol="OLDCO")
    db.add(AssetIdentifier(
        asset_id=asset.id, identifier_type=IdentifierType.ISIN.value,
        value="STALEID", source="test", is_current=False,
    ))
    db.commit()

    discovery = DiscoveryCandidate(claim_id="c1", provider_name="p1", reported_identifiers={"ISIN": "STALEID"})
    result = merge.merge(db, [], [discovery])
    assert len(result) == 1
    assert result[0].asset_id == asset.id


# -- 30. Structural AST checks: forbidden imports/calls -------------------------

def test_merge_module_imports_no_registry_query():
    """No copy of resolver-internal matching logic: merge.py must never
    import registry_query directly (that raw-row matching machinery is
    identity_resolver.py's alone to use)."""
    imported_names = _imported_names(_merge_module_tree())
    assert "registry_query" not in imported_names
    assert "services.registry_query" not in imported_names


def test_merge_module_imports_no_adjudicate():
    imported_names = _imported_names(_merge_module_tree())
    assert "adjudicate" not in imported_names


def test_merge_module_imports_no_findings_repository():
    imported_names = _imported_names(_merge_module_tree())
    forbidden = {"registry_findings_repository"}
    found = imported_names & forbidden
    assert not found, f"merge.py must not import finding-write repositories; found: {found}"


def test_merge_module_imports_no_provider_code():
    imported_names = _imported_names(_merge_module_tree())
    forbidden = {"provider_adapter", "provider_domain"}
    found = imported_names & forbidden
    assert not found, f"merge.py must not import provider code; found: {found}"


def test_merge_module_contains_no_mint_or_write_calls():
    """Structural guard: merge.py must never call db.add/flush/commit/
    delete/merge, and must never call mint_asset/attach_identifier/
    record_classification/adjudicate anywhere."""
    tree = _merge_module_tree()
    forbidden_attrs = {
        "add", "flush", "commit", "delete",
        "mint_asset", "attach_identifier", "record_classification", "adjudicate",
    }
    found = {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and node.attr in forbidden_attrs
    }
    assert not found, f"merge.py must remain read-only/non-minting; found calls to: {found}"


def test_merge_module_imports_identity_resolver_resolve_only():
    """Confirms merge.py imports resolve by name (not adjudicate, not the
    whole module wholesale in a way that would make adjudicate reachable
    as merge.identity_resolver.adjudicate)."""
    tree = _merge_module_tree()
    resolve_imported = any(
        isinstance(node, ast.ImportFrom)
        and node.module == "services.identity_resolver"
        and any(alias.name == "resolve" for alias in node.names)
        for node in ast.walk(tree)
    )
    assert resolve_imported
