"""Tests for Asset Foundation's Catalog Search (Milestone M37.2, WP2).

Validates docs/implementation/M37_1_Universal_Asset_Search_Technical_Design.md
Section 9's catalog-search design against
`services/asset_search/catalog_search.py`:

  1.  Exact canonical symbol match
  2.  Exact display symbol match
  3.  Partial/prefix symbol text does not match (no unapproved prefix tier)
  4.  Identifier match
  5.  Case-insensitive matching
  6.  NFC normalization
  7.  Whitespace normalization
  8.  Empty query rejection
  9.  Raw query over 200 code points rejected
  10. Literal `%` handling
  11. Literal `_` handling
  12. Literal escape-character handling
  13. Wildcard-only query does not scan/match the catalog
  14. Supported classification filters
  15. Invalid filter key
  16. Invalid filter value
  17. Conflicting filters
  18. Deterministic ordering (exact-symbol vs. exact-identifier tiers)
  19. Stable tie-breaking
  20. No classification-only fallback (F5 - no non-matching-query browse mode)
  21. No result for an unrelated query
  22. Result contains the real Registry asset_id
  23. Zero permanent writes across Asset/AssetIdentifier/AssetClassification/RegistryFinding
  24. No resolver/provider/adjudication imports
  25. Name search explicitly absent or gated until WP1
  26. Current identifier evidence wins over historical identifier evidence
  27. Historical-only classification evidence does not satisfy a filter
  28. An asset matching multiple approved exact tiers appears once, at its best tier

Symbol-prefix matching is NOT part of WP2. The frozen M37.1 §12 tier
enumeration authorizes only: (1) exact canonical/display symbol match,
(2) exact current identifier match, (3) name prefix match and (4) name
substring match — both gated on WP1's descriptive-name schema. Canonical/
display-symbol prefix matching is not in that list, so a query that is only
a prefix of a symbol must return zero results unless it also happens to be
an exact current identifier value.

All tests use an in-memory SQLite database; no network calls.
"""
import ast
import os
import sys
import unicodedata

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
from services.asset_domain import AssetClaim, AssetType, ClassificationDimension, IdentifierRecord, IdentifierType
from services.asset_search import catalog_search


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


def _asset_row_count(db) -> int:
    return db.query(Asset).count()


def _all_row_counts(db) -> dict:
    return {
        "Asset": db.query(Asset).count(),
        "AssetIdentifier": db.query(AssetIdentifier).count(),
        "AssetClassification": db.query(AssetClassification).count(),
        "RegistryFinding": db.query(RegistryFinding).count(),
    }


def _match_fields(result: catalog_search.CatalogSearchResult):
    return {c.asset_id: c.match_field for c in result.candidates}


# -- Exact matches ----------------------------------------------------------

def test_exact_canonical_symbol_match():
    db = make_session()
    asset = _mint(db)

    result = catalog_search.search(db, "KBANK")

    assert [c.asset_id for c in result.candidates] == [asset.id]
    assert result.candidates[0].match_field == "canonical_symbol"


def test_exact_display_symbol_match():
    db = make_session()
    asset = _mint(db, canonical_symbol="KBANK-INTERNAL")
    asset.display_symbol = "KBANK"
    db.commit()

    result = catalog_search.search(db, "KBANK")

    assert [c.asset_id for c in result.candidates] == [asset.id]
    assert result.candidates[0].match_field == "display_symbol"


def test_partial_symbol_text_does_not_match():
    """Symbol-prefix matching is not an approved WP2 tier (M37.1 §12's
    closed tier list authorizes only exact canonical/display symbol and
    exact current identifier matching). A query that is only a prefix of
    a stored symbol must return zero results unless it also happens to be
    an exact current identifier value."""
    db = make_session()
    _mint(db, canonical_symbol="KBANK")

    result = catalog_search.search(db, "KBA")

    assert result.candidates == ()


def test_partial_display_symbol_text_does_not_match():
    db = make_session()
    asset = _mint(db, canonical_symbol="KBANK-INTERNAL")
    asset.display_symbol = "KBANKDISPLAY"
    db.commit()

    result = catalog_search.search(db, "KBANKDIS")

    assert result.candidates == ()


def test_identifier_match():
    db = make_session()
    asset = _mint(db)
    svc.attach_identifier(db, asset.id, IdentifierRecord(IdentifierType.ISIN, "TH0001010006", source="manual"))

    result = catalog_search.search(db, "TH0001010006")

    assert [c.asset_id for c in result.candidates] == [asset.id]
    assert result.candidates[0].match_field == "identifier:ISIN"


def test_current_identifier_wins_over_historical_identifier():
    """When the same identifier value exists as historical evidence on one
    asset and current evidence on another, only the current-holding asset
    is returned — the historical asset must be excluded entirely, not
    merely ranked lower."""
    db = make_session()
    historical_owner = _mint(db, canonical_symbol="OLDCO")
    db.add(AssetIdentifier(
        asset_id=historical_owner.id, identifier_type=IdentifierType.ISIN.value,
        value="SHAREDID", source="test", is_current=False,
    ))
    current_owner = _mint(db, canonical_symbol="NEWCO")
    svc.attach_identifier(db, current_owner.id, IdentifierRecord(IdentifierType.ISIN, "SHAREDID", source="manual"))
    db.commit()

    result = catalog_search.search(db, "SHAREDID")

    assert [c.asset_id for c in result.candidates] == [current_owner.id]


def test_historical_only_identifier_still_matches_when_no_current_claimant_exists():
    """A purely historical identifier (no asset currently holds this value)
    still matches. This mirrors identity_resolver.resolve()'s own doctrine
    (identity_resolver.py's _match_candidates): 'historical rows only
    compete with each other when nothing currently claims the value' — a
    recycled identifier with no live claimant is surfaced, not silently
    hidden. Suppression only applies when a CURRENT row for the same value
    exists elsewhere (see test_current_identifier_wins_over_historical_identifier)."""
    db = make_session()
    asset = _mint(db, canonical_symbol="OLDCO")
    db.add(AssetIdentifier(
        asset_id=asset.id, identifier_type=IdentifierType.ISIN.value,
        value="STALEID", source="test", is_current=False,
    ))
    db.commit()

    result = catalog_search.search(db, "STALEID")

    assert [c.asset_id for c in result.candidates] == [asset.id]
    assert result.candidates[0].match_field == "identifier:ISIN"


def test_case_insensitive_matching():
    db = make_session()
    asset = _mint(db, canonical_symbol="KBANK")

    result = catalog_search.search(db, "kbank")

    assert [c.asset_id for c in result.candidates] == [asset.id]


# -- Normalization ------------------------------------------------------------

def test_nfc_normalization():
    """A query in decomposed (NFD) Unicode form must still match a symbol
    stored in precomposed (NFC) form - both forms are built at runtime via
    unicodedata rather than embedding an accented literal in this source
    file, so the test is independent of the file's own text encoding."""
    db = make_session()
    base_char = chr(0x00E9)  # LATIN SMALL LETTER E WITH ACUTE, precomposed
    nfc_symbol = unicodedata.normalize("NFC", base_char)
    nfd_query_char = unicodedata.normalize("NFD", base_char)  # "e" + combining acute
    assert nfc_symbol != nfd_query_char  # sanity: byte-for-byte forms differ

    asset = _mint(db, canonical_symbol="CAF" + nfc_symbol.upper())

    result = catalog_search.search(db, "CAF" + nfd_query_char.upper())

    assert [c.asset_id for c in result.candidates] == [asset.id]


def test_whitespace_normalization():
    db = make_session()
    asset = _mint(db, canonical_symbol="KBANK")

    result = catalog_search.search(db, "  KBANK   ")

    assert [c.asset_id for c in result.candidates] == [asset.id]


def test_empty_query_rejection():
    db = make_session()

    with pytest.raises(catalog_search.EmptyQueryError):
        catalog_search.search(db, "   ")


def test_raw_query_over_200_codepoints_rejected():
    db = make_session()

    with pytest.raises(catalog_search.QueryTooLongError):
        catalog_search.search(db, "A" * 201)


def test_query_at_200_codepoints_is_accepted():
    db = make_session()
    # boundary check: exactly 200 must not raise QueryTooLongError, even
    # though it will not match anything (a separate concern from
    # EmptyQueryError/matching).
    result = catalog_search.search(db, "A" * 200)
    assert result.candidates == ()


# -- Wildcard / literal-text security (F6) -----------------------------------

def test_literal_percent_handling():
    db = make_session()
    _mint(db, canonical_symbol="KBANK")
    _mint(db, canonical_symbol="SCB", asset_type=AssetType.EQUITY)

    result = catalog_search.search(db, "%")

    assert result.candidates == ()  # a literal '%' matches nothing, never every row


def test_literal_underscore_handling():
    db = make_session()
    _mint(db, canonical_symbol="KBANK")

    result = catalog_search.search(db, "_")

    assert result.candidates == ()  # a literal '_' matches nothing, never a single-char wildcard


def test_literal_escape_character_handling():
    db = make_session()
    _mint(db, canonical_symbol="KBANK")

    result = catalog_search.search(db, "\\")

    assert result.candidates == ()  # a literal backslash must not corrupt the ESCAPE clause


def test_wildcard_only_query_does_not_scan_the_catalog():
    db = make_session()
    _mint(db, canonical_symbol="KBANK")
    _mint(db, canonical_symbol="SCB")
    _mint(db, canonical_symbol="PTT")

    result = catalog_search.search(db, "%%%")

    assert result.candidates == ()  # not a full-table wildcard scan


def test_symbol_containing_percent_is_matched_literally():
    db = make_session()
    asset = _mint(db, canonical_symbol="AB%CD")

    result = catalog_search.search(db, "AB%CD")

    assert [c.asset_id for c in result.candidates] == [asset.id]


# -- Classification filters ---------------------------------------------------

def test_supported_classification_filters():
    db = make_session()
    th_asset = _mint(db, canonical_symbol="KBANK", market="TH")
    us_asset = _mint(db, canonical_symbol="KBANKUS", market="United States")

    result = catalog_search.search(db, "KBANK", filters=(("market", "TH"),))

    assert [c.asset_id for c in result.candidates] == [th_asset.id]
    assert us_asset.id not in _match_fields(result)


def test_supported_classification_filter_on_asset_class_dimension():
    db = make_session()
    asset = _mint(db, canonical_symbol="KBANK")
    svc.record_classification(db, asset.id, ClassificationDimension.ASSET_CLASS, "equity", source="test")
    other = _mint(db, canonical_symbol="KBANKX")
    svc.record_classification(db, other.id, ClassificationDimension.ASSET_CLASS, "fund", source="test")

    result = catalog_search.search(db, "KBANK", filters=(("asset_class", "equity"),))

    assert [c.asset_id for c in result.candidates] == [asset.id]


def test_historical_only_classification_does_not_satisfy_filter():
    """An asset whose only asset_class/region evidence is historical
    (is_current=False) must not satisfy that filter — only current
    classification rows are stewarded evidence for filtering (§9)."""
    db = make_session()
    asset = _mint(db, canonical_symbol="KBANK")
    db.add(AssetClassification(
        asset_id=asset.id, dimension=ClassificationDimension.ASSET_CLASS.value,
        value="equity", source="test", is_current=False,
    ))
    db.commit()

    result = catalog_search.search(db, "KBANK", filters=(("asset_class", "equity"),))

    assert result.candidates == ()


def test_invalid_filter_key():
    db = make_session()
    _mint(db, canonical_symbol="KBANK")

    with pytest.raises(catalog_search.UnknownFilterDimensionError):
        catalog_search.search(db, "KBANK", filters=(("sector", "Financials"),))


def test_invalid_filter_value():
    db = make_session()
    _mint(db, canonical_symbol="KBANK")

    with pytest.raises(catalog_search.InvalidFilterValueError):
        catalog_search.search(db, "KBANK", filters=(("market", "   "),))


def test_conflicting_filters():
    db = make_session()
    _mint(db, canonical_symbol="KBANK")

    with pytest.raises(catalog_search.ConflictingFiltersError):
        catalog_search.search(db, "KBANK", filters=(("market", "TH"), ("market", "United States")))


def test_repeated_identical_filter_is_not_a_conflict():
    db = make_session()
    asset = _mint(db, canonical_symbol="KBANK", market="TH")

    result = catalog_search.search(db, "KBANK", filters=(("market", "TH"), ("market", "TH")))

    assert [c.asset_id for c in result.candidates] == [asset.id]


def test_filters_never_surface_unrelated_non_matching_assets():
    db = make_session()
    _mint(db, canonical_symbol="OTHERCO", market="TH")  # matches filter, not query

    result = catalog_search.search(db, "KBANK", filters=(("market", "TH"),))

    assert result.candidates == ()


# -- Ordering -----------------------------------------------------------------

def test_deterministic_ordering_exact_symbol_before_exact_identifier():
    """Tier order must win over alphabetical canonical_symbol order: the
    exact-identifier match's canonical_symbol ("AAA") sorts before the
    exact-symbol match's ("ZZZ") alphabetically, but the higher-precedence
    tier (exact symbol) must still be listed first."""
    db = make_session()
    identifier_match = _mint(db, canonical_symbol="AAA")
    svc.attach_identifier(db, identifier_match.id, IdentifierRecord(IdentifierType.ISIN, "MATCHME", source="manual"))
    symbol_match = _mint(db, canonical_symbol="MATCHME")

    result = catalog_search.search(db, "MATCHME")

    assert [c.asset_id for c in result.candidates] == [symbol_match.id, identifier_match.id]


def test_stable_tie_breaking_by_canonical_symbol_then_asset_id():
    """Two assets in the same exact-symbol tier (one via canonical_symbol,
    one via display_symbol) must be ordered by canonical_symbol, not by
    which field matched or insertion order."""
    db = make_session()
    via_display = _mint(db, canonical_symbol="ZZZTOP")
    via_display.display_symbol = "AAA"
    db.commit()
    via_canonical = _mint(db, canonical_symbol="AAA")

    result = catalog_search.search(db, "AAA")

    assert [c.asset_id for c in result.candidates] == [via_canonical.id, via_display.id]


def test_ordering_stable_across_repeated_identical_queries():
    db = make_session()
    a = _mint(db, canonical_symbol="AAA")
    a.display_symbol = "SHARED"
    b = _mint(db, canonical_symbol="BBB")
    b.display_symbol = "SHARED"
    db.commit()

    first = [c.asset_id for c in catalog_search.search(db, "SHARED").candidates]
    second = [c.asset_id for c in catalog_search.search(db, "SHARED").candidates]

    assert first == second == [a.id, b.id]


def test_asset_matching_multiple_approved_tiers_appears_once_at_best_tier():
    """An asset whose canonical_symbol, display_symbol, and a current
    identifier all equal the query must appear exactly once, at its
    highest-precedence approved tier (exact canonical/display symbol),
    not once per matching tier."""
    db = make_session()
    asset = _mint(db, canonical_symbol="MATCHALL")
    asset.display_symbol = "MATCHALL"
    db.commit()
    svc.attach_identifier(db, asset.id, IdentifierRecord(IdentifierType.ISIN, "MATCHALL", source="manual"))

    result = catalog_search.search(db, "MATCHALL")

    assert [c.asset_id for c in result.candidates] == [asset.id]
    assert result.candidates[0].match_field == "canonical_symbol"


# -- No classification-only fallback (F5) ------------------------------------

def test_no_classification_only_fallback_for_non_matching_query():
    """A query matching no text/identifier returns zero candidates, even
    though a classification filter would otherwise match rows - the
    removed tier-5 browse-mode behavior must not resurface here."""
    db = make_session()
    _mint(db, canonical_symbol="KBANK", market="TH")
    _mint(db, canonical_symbol="SCB", market="TH")

    result = catalog_search.search(db, "zzzznomatch", filters=(("market", "TH"),))

    assert result.candidates == ()


def test_no_result_for_unrelated_query():
    db = make_session()
    _mint(db, canonical_symbol="KBANK")

    result = catalog_search.search(db, "totallyunrelatedquery")

    assert result.candidates == ()


# -- Registry-owned identity --------------------------------------------------

def test_result_contains_real_registry_asset_id():
    db = make_session()
    asset = _mint(db, canonical_symbol="KBANK")

    result = catalog_search.search(db, "KBANK")

    candidate = result.candidates[0]
    assert candidate.asset_id == asset.id
    assert candidate.kind == "REGISTERED"
    # the asset_id is re-fetched from the authoritative row, not cached
    refetched = svc.get_asset(db, asset.id)
    assert candidate.canonical_symbol == refetched.canonical_symbol


# -- Read-only guarantee -------------------------------------------------------

def test_zero_permanent_writes():
    db = make_session()
    _mint(db, canonical_symbol="KBANK")
    before = _asset_row_count(db)

    catalog_search.search(db, "KBANK")
    catalog_search.search(db, "totallyunrelated")
    catalog_search.search(db, "%%%")

    assert _asset_row_count(db) == before


def test_zero_permanent_writes_across_all_relevant_tables():
    """Behavioral (not just structural/AST) read-only proof: row counts
    across every table catalog_search.py touches — Asset, AssetIdentifier,
    AssetClassification, RegistryFinding — must be identical before and
    after multiple searches, including filtered, wildcard-only, and
    non-matching queries."""
    db = make_session()
    asset = _mint(db, canonical_symbol="KBANK", market="TH")
    svc.attach_identifier(db, asset.id, IdentifierRecord(IdentifierType.ISIN, "TH0001010006", source="manual"))
    svc.record_classification(db, asset.id, ClassificationDimension.ASSET_CLASS, "equity", source="test")
    before = _all_row_counts(db)

    catalog_search.search(db, "KBANK")
    catalog_search.search(db, "TH0001010006")
    catalog_search.search(db, "totallyunrelated")
    catalog_search.search(db, "%%%")
    catalog_search.search(db, "KBANK", filters=(("asset_class", "equity"),))

    assert _all_row_counts(db) == before


def test_catalog_search_module_contains_no_write_calls():
    """Structural guard: catalog_search.py must never call db.add/flush/
    commit anywhere - verified by inspecting the module's own AST rather
    than trusting behavioral tests alone to catch a future regression."""
    module_path = os.path.join(
        os.path.dirname(__file__), "..", "services", "asset_search", "catalog_search.py",
    )
    with open(module_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())

    forbidden_calls = {"add", "flush", "commit", "delete", "merge"}
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in forbidden_calls:
            found.add(node.attr)

    assert not found, f"catalog_search.py must remain read-only; found calls to: {found}"


# -- No resolver/provider/adjudication imports (structural conformance) ------

def test_catalog_search_imports_no_resolver_provider_or_adjudication():
    """Import-graph inspection (§19's conformance-test style): checks
    actual `import`/`from ... import` statements via the AST, not raw
    substring search over the file — the module's own docstrings
    legitimately name identity_resolver/adjudicate in prose to explain the
    boundary it does not cross, which a naive substring check would
    misflag as a violation."""
    module_path = os.path.join(
        os.path.dirname(__file__), "..", "services", "asset_search", "catalog_search.py",
    )
    with open(module_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())

    imported_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_names.add(node.module)
            imported_names.update(alias.name for alias in node.names)

    forbidden_modules = {
        "identity_resolver",
        "provider_adapter",
        "provider_domain",
        "registry_findings_repository",
        "difflib",
        "rapidfuzz",
    }
    violations = imported_names & forbidden_modules
    assert not violations, f"catalog_search.py must not import: {violations}"

    # adjudicate is a function, not a module - confirm no Attribute/Name
    # access to it anywhere (it is never imported, so this is expected to
    # be trivially empty; kept as an explicit regression guard).
    adjudicate_refs = [
        node for node in ast.walk(tree)
        if (isinstance(node, ast.Attribute) and node.attr == "adjudicate")
        or (isinstance(node, ast.Name) and node.id == "adjudicate")
    ]
    assert not adjudicate_refs, "catalog_search.py must never call adjudicate()"


# -- Name search absence (F4 staged conformance) -----------------------------

def test_name_search_explicitly_absent_until_wp1():
    assert hasattr(Asset, "name") is False
    assert catalog_search.NAME_SEARCH_AVAILABLE is False

    db = make_session()
    asset = _mint(db, canonical_symbol="KBANK")
    # simulate what a future provider-reported "name" would be - since
    # there is no column to persist or match it against, searching for it
    # must not accidentally match via any other field.
    result = catalog_search.search(db, "Kasikornbank Public Company Limited")

    assert result.candidates == ()
    # the result honestly discloses that name search did not run
    empty_result_flag = catalog_search.search(db, "KBANK").name_search_available
    assert empty_result_flag is False
    assert asset.id  # sanity: asset did mint despite the unrelated name query
