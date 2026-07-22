"""Tests for Market Intelligence's Ranking Engine (Milestone M37.2, WP4).

Validates docs/implementation/M37_1_Universal_Asset_Search_Technical_Design.md
Section 12's ranking model against `services/asset_search/ranking.py`:

  1.  Registered ordering established by WP2 is preserved
  2.  Discovery ordering follows the approved tier/tie-break rules
  3.  Mixed candidate ordering (registered before discovery within a tier)
  4.  Deterministic repeated execution (same input -> same output, every time)
  5.  Stable ordering under identical input (ties keep input order)
  6.  No mutation of input candidate objects
  7.  Ranking is a pure function (no side effects, no db/network access)
  8.  Empty input
  9.  Single candidate
  10. Registered-only input
  11. Discovery-only input
  12. Mixed candidate lists (symbol tier vs. identifier tier vs. unranked)
  13. Already-ranked input stays stable
  14. Duplicate candidate references (the same object appearing twice)
  15. No database imports
  16. No provider imports
  17. No resolver imports
  18. No write behavior
  19. No hidden randomness (no `random`/`hash`-based ordering)
  20. Conformance with the approved §12 ranking tiers

This module ranks only. It never searches, merges, calls providers, calls
identity_resolver, or writes Registry state. All tests are pure in-process
dataclass construction; no database, no network calls.
"""
import ast
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.asset_search.catalog_search import RegisteredCandidate
from services.asset_search.ranking import rank


@dataclass(frozen=True)
class DiscoveryCandidate:
    """Test-local double matching §6's DiscoveryCandidate field shape.
    `ranking.py` is duck-typed and does not define or import this class —
    per the WP4 conformance review (B2), the production contract belongs to
    WP6's `discovery_search.py`. This double exists only so
    WP4's tests can exercise mixed registered/discovery ranking without
    creating a premature ownership dependency."""

    kind: str = field(default="DISCOVERY", init=False)
    claim_id: str = ""
    provider_name: str = ""
    reported_symbol: Optional[str] = None
    reported_name: Optional[str] = None
    reported_identifiers: Dict[str, str] = field(default_factory=dict)
    market: Optional[str] = None
    currency: Optional[str] = None
    match_field: str = ""


def _registered(**overrides):
    defaults = dict(
        asset_id=1,
        canonical_symbol="AAA",
        display_symbol=None,
        asset_type="EQUITY",
        market="TH",
        exchange="SET",
        currency="THB",
        classifications={},
        status="ACTIVE",
        match_field="canonical_symbol",
    )
    defaults.update(overrides)
    return RegisteredCandidate(**defaults)


def _discovery(**overrides):
    defaults = dict(
        claim_id="claim-1",
        provider_name="test-provider",
        reported_symbol="AAA",
        reported_name=None,
        reported_identifiers={},
        market="TH",
        currency="THB",
        match_field="canonical_symbol",
    )
    defaults.update(overrides)
    return DiscoveryCandidate(**defaults)


# -- 1. Registered ordering preserved ----------------------------------------

def test_registered_ordering_established_by_wp2_is_preserved():
    a = _registered(asset_id=1, canonical_symbol="AAA", match_field="canonical_symbol")
    b = _registered(asset_id=2, canonical_symbol="BBB", match_field="canonical_symbol")
    c = _registered(asset_id=3, canonical_symbol="CCC", match_field="identifier:ISIN")
    result = rank([c, a, b])
    assert result == [a, b, c]


# -- 2. Discovery ordering follows approved ranking --------------------------

def test_discovery_ordering_follows_approved_tiers():
    d1 = _discovery(claim_id="c1", reported_symbol="ZZZ", match_field="canonical_symbol")
    d2 = _discovery(claim_id="c2", reported_symbol="AAA", match_field="identifier:ISIN")
    result = rank([d2, d1])
    assert result == [d1, d2]


# -- 3. Mixed candidate ordering: registered before discovery within a tier --

def test_registered_before_discovery_within_same_tier():
    registered = _registered(asset_id=1, canonical_symbol="ZZZ", match_field="canonical_symbol")
    discovery = _discovery(claim_id="c1", reported_symbol="AAA", match_field="canonical_symbol")
    result = rank([discovery, registered])
    assert result == [registered, discovery]


def test_mixed_candidates_tier_precedence_beats_source_precedence():
    """A discovery candidate in a higher tier still outranks a registered
    candidate in a lower tier - registered-before-discovery only applies
    as the within-tier tie-break, never across tiers."""
    registered_identifier_tier = _registered(asset_id=1, canonical_symbol="AAA", match_field="identifier:ISIN")
    discovery_symbol_tier = _discovery(claim_id="c1", reported_symbol="ZZZ", match_field="canonical_symbol")
    result = rank([registered_identifier_tier, discovery_symbol_tier])
    assert result == [discovery_symbol_tier, registered_identifier_tier]


# -- 4. Deterministic repeated execution -------------------------------------

def test_deterministic_repeated_execution():
    candidates = [
        _registered(asset_id=1, canonical_symbol="BBB"),
        _discovery(claim_id="c1", reported_symbol="AAA"),
        _registered(asset_id=2, canonical_symbol="AAA", match_field="identifier:ISIN"),
    ]
    first = rank(candidates)
    second = rank(candidates)
    third = rank(list(reversed(candidates)))
    assert first == second == third


# -- 5. Stable ordering under identical input --------------------------------

def test_stable_ordering_preserves_input_order_for_true_ties():
    a = _registered(asset_id=1, canonical_symbol="SHARED")
    b = _registered(asset_id=2, canonical_symbol="SHARED")
    result = rank([a, b])
    assert result == [a, b]
    result_reversed = rank([b, a])
    assert result_reversed == [b, a]


def test_provider_name_does_not_affect_canonical_ranking():
    first = _discovery(
        claim_id="c1",
        provider_name="z-provider",
        reported_symbol="SHARED",
        match_field="identifier:PROVIDER_SYMBOL",
    )
    second = _discovery(
        claim_id="c2",
        provider_name="a-provider",
        reported_symbol="SHARED",
        match_field="identifier:PROVIDER_SYMBOL",
    )

    assert rank([first, second]) == [first, second]
    assert rank([second, first]) == [second, first]


# -- B1 regression: missing tie-break symbol sorts LAST, never first --------

def test_candidate_missing_tie_break_symbol_sorts_last_within_tier():
    """§8 stage 8: 'a candidate missing a rankable field sorts last within
    its tier, never excluded.' A DiscoveryCandidate with reported_symbol=
    None is a real, §6-legal shape (the field is Optional) - it must never
    outrank a symbol-bearing peer in the same tier."""
    symbol_less = _discovery(claim_id="c1", reported_symbol=None, match_field="canonical_symbol")
    with_symbol = _discovery(claim_id="c2", reported_symbol="AAA", match_field="canonical_symbol")
    result = rank([symbol_less, with_symbol])
    assert result == [with_symbol, symbol_less]


def test_candidate_missing_tie_break_symbol_still_outranks_a_lower_tier():
    """A missing tie-break symbol only demotes a candidate within its own
    tier - it must not fall out of its tier entirely (that would be
    exclusion by another name)."""
    symbol_less_top_tier = _discovery(claim_id="c1", reported_symbol=None, match_field="canonical_symbol")
    lower_tier_with_symbol = _registered(asset_id=1, canonical_symbol="AAA", match_field="identifier:ISIN")
    result = rank([lower_tier_with_symbol, symbol_less_top_tier])
    assert result == [symbol_less_top_tier, lower_tier_with_symbol]


# -- 6. No mutation of input candidate objects -------------------------------

def test_rank_does_not_mutate_candidate_objects():
    a = _registered(asset_id=1, canonical_symbol="BBB")
    b = _discovery(claim_id="c1", reported_symbol="AAA")
    before_a, before_b = a, b
    rank([a, b])
    assert a == before_a
    assert b == before_b
    # frozen dataclasses: any attempted mutation would raise, so their mere
    # existence post-call is itself evidence rank() cannot have mutated them
    assert a.canonical_symbol == "BBB"
    assert b.reported_symbol == "AAA"


# -- 7. Ranking is pure -------------------------------------------------------

def test_rank_does_not_mutate_input_sequence():
    candidates = [_registered(asset_id=2, canonical_symbol="BBB"), _registered(asset_id=1, canonical_symbol="AAA")]
    original_order = list(candidates)
    rank(candidates)
    assert candidates == original_order  # rank() must not sort in place


def test_rank_accepts_a_tuple_and_returns_a_new_list():
    a = _registered(asset_id=1, canonical_symbol="AAA")
    result = rank((a,))
    assert isinstance(result, list)


# -- 8. Empty input -----------------------------------------------------------

def test_empty_input_returns_empty_list():
    assert rank([]) == []


# -- 9. Single candidate ------------------------------------------------------

def test_single_candidate_returned_unchanged():
    a = _registered(asset_id=1, canonical_symbol="AAA")
    assert rank([a]) == [a]


# -- 10. Registered-only input ------------------------------------------------

def test_registered_only_input():
    a = _registered(asset_id=1, canonical_symbol="BBB")
    b = _registered(asset_id=2, canonical_symbol="AAA")
    assert rank([a, b]) == [b, a]


# -- 11. Discovery-only input -------------------------------------------------

def test_discovery_only_input():
    a = _discovery(claim_id="c1", reported_symbol="BBB")
    b = _discovery(claim_id="c2", reported_symbol="AAA")
    assert rank([a, b]) == [b, a]


# -- 12. Mixed candidate lists across tiers ----------------------------------

def test_mixed_candidate_list_across_all_currently_available_tiers():
    symbol = _registered(asset_id=1, canonical_symbol="AAA", match_field="canonical_symbol")
    identifier = _discovery(claim_id="c1", reported_symbol="BBB", match_field="identifier:ISIN")
    unranked = _registered(asset_id=2, canonical_symbol="CCC", match_field="")
    result = rank([unranked, identifier, symbol])
    assert result == [symbol, identifier, unranked]


# -- 13. Already-ranked input stays stable -----------------------------------

def test_already_ranked_input_is_unchanged():
    a = _registered(asset_id=1, canonical_symbol="AAA", match_field="canonical_symbol")
    b = _registered(asset_id=2, canonical_symbol="BBB", match_field="identifier:ISIN")
    assert rank([a, b]) == [a, b]


# -- 14. Duplicate candidate references ---------------------------------------

def test_duplicate_candidate_references_do_not_crash_or_vanish():
    a = _registered(asset_id=1, canonical_symbol="AAA")
    result = rank([a, a, a])
    assert result == [a, a, a]
    assert len(result) == 3


# -- 15/16/17. Structural import conformance ---------------------------------

def _ranking_module_tree():
    module_path = os.path.join(
        os.path.dirname(__file__), "..", "services", "asset_search", "ranking.py",
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


def test_ranking_module_imports_no_database_module():
    imported_names = _imported_names(_ranking_module_tree())
    forbidden = {"sqlalchemy", "models.database", "Session", "sessionmaker", "create_engine"}
    found = imported_names & forbidden
    assert not found, f"ranking.py must not import database machinery; found: {found}"


def test_ranking_module_imports_no_provider_adapter():
    imported_names = _imported_names(_ranking_module_tree())
    forbidden = {"provider_adapter", "provider_domain"}
    found = imported_names & forbidden
    assert not found, f"ranking.py must not import provider code; found: {found}"


def test_ranking_module_imports_no_resolver_or_adjudication():
    imported_names = _imported_names(_ranking_module_tree())
    forbidden = {"identity_resolver", "registry_findings_repository", "asset_registry"}
    found = imported_names & forbidden
    assert not found, f"ranking.py must not import Registry-mutating code; found: {found}"


# -- 18. No write behavior (structural) --------------------------------------

def test_ranking_module_contains_no_write_calls():
    """Structural guard: ranking.py must never call db.add/flush/commit/
    delete/merge anywhere - it takes no Session at all, verified both by
    the import check above and by inspecting the AST for the call shapes
    a write would need."""
    tree = _ranking_module_tree()
    forbidden_calls = {"add", "flush", "commit", "delete"}
    found = {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and node.attr in forbidden_calls
    }
    assert not found, f"ranking.py must remain read-only/writeless; found calls to: {found}"


def test_rank_signature_takes_no_session_or_db_parameter():
    """§3: ranking.py's allowed deps are 'pure functions of candidate
    fields' only - `rank()` must not accept anything resembling a db/session
    argument, which would let a future edit slip in a query."""
    import inspect

    from services.asset_search import ranking

    params = inspect.signature(ranking.rank).parameters
    forbidden_param_names = {"db", "session", "conn", "connection"}
    found = set(params) & forbidden_param_names
    assert not found, f"rank() must not accept a db/session parameter; found: {found}"


# -- 19. No hidden randomness --------------------------------------------------

def test_ranking_module_does_not_import_random_or_use_object_hash_for_ordering():
    imported_names = _imported_names(_ranking_module_tree())
    assert "random" not in imported_names
    # id()/hash()-based ordering would make output non-deterministic across
    # runs (different object addresses) - confirm no such builtin call exists
    tree = _ranking_module_tree()
    forbidden_builtins = {"hash", "id"}
    found_calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in forbidden_builtins
    }
    assert not found_calls, f"ranking.py must not order by hash()/id(); found calls to: {found_calls}"


def test_no_personalization_or_analytics_parameters_exist():
    """§12: no user ID, history, provider relevance, or confidence score is
    a ranking input - enforced by rank() simply not accepting one."""
    import inspect

    from services.asset_search import ranking

    params = set(inspect.signature(ranking.rank).parameters)
    forbidden_param_names = {
        "user_id", "user", "history", "provider_score", "relevance",
        "confidence", "popularity", "click_count",
    }
    found = params & forbidden_param_names
    assert not found, f"rank() must not accept a personalization/analytics parameter; found: {found}"


# -- 20. Conformance with approved §12 tiers ----------------------------------

def test_all_four_approved_tiers_rank_in_order_when_all_present():
    exact_symbol = _registered(asset_id=1, canonical_symbol="AAA", match_field="canonical_symbol")
    exact_identifier = _registered(asset_id=2, canonical_symbol="BBB", match_field="identifier:ISIN")
    name_prefix = _registered(asset_id=3, canonical_symbol="CCC", match_field="name_prefix")
    name_substring = _registered(asset_id=4, canonical_symbol="DDD", match_field="name_substring")
    result = rank([name_substring, name_prefix, exact_identifier, exact_symbol])
    assert result == [exact_symbol, exact_identifier, name_prefix, name_substring]


def test_discovery_candidate_never_wins_symbol_tier_over_a_registered_identifier_match():
    """§12 tier 1 is registered-only by construction - a DiscoveryCandidate
    has no canonical_symbol field to match against, so it can only ever
    appear via match_field values reachable from its own shape; this test
    documents that even if a discovery candidate's match_field were somehow
    "canonical_symbol" (a producer bug elsewhere), ranking.py places it by
    match_field/tier only - identity of "who can legitimately claim this
    tier" is a producer-side (catalog_search.py/discovery_search.py)
    responsibility, not ranking.py's to police."""
    registered_identifier = _registered(asset_id=1, canonical_symbol="AAA", match_field="identifier:ISIN")
    discovery_symbol = _discovery(claim_id="c1", reported_symbol="ZZZ", match_field="canonical_symbol")
    result = rank([registered_identifier, discovery_symbol])
    assert result == [discovery_symbol, registered_identifier]


def test_candidate_with_unrecognized_match_field_sorts_last_never_excluded():
    """§8 stage 8: ranking never fails and never drops a candidate; a
    candidate missing/mismatching a rankable field sorts last within
    nothing (dead last overall), never excluded from the result."""
    known = _registered(asset_id=1, canonical_symbol="AAA", match_field="canonical_symbol")
    unknown = _registered(asset_id=2, canonical_symbol="BBB", match_field="something_unexpected")
    result = rank([unknown, known])
    assert result == [known, unknown]
    assert len(rank([unknown])) == 1


def test_discovery_candidate_has_no_asset_id_attribute():
    """§6/R5 schema guarantee this module relies on: a DiscoveryCandidate
    cannot masquerade as registered because asset_id is structurally
    absent, not merely null."""
    d = _discovery()
    assert not hasattr(d, "asset_id")
    assert d.kind == "DISCOVERY"
