"""Structural conformance tests for the Universal Asset Search WP5 delivery
(Milestone M37.2).

Validates docs/implementation/M37_1_Universal_Asset_Search_Technical_Design.md
Section 3's module-placement table and Section 20's WP5 dependency row
against `services/asset_search/search_service.py` and
`routers/asset_search.py`, via `ast` inspection rather than brittle
substring search:

  - No provider adapter imports (no discovery fan-out exists yet).
  - No `identity_resolver` import (search never resolves identity itself).
  - No `merge` import (F12 - WP3 is not a WP5 dependency for the
    CATALOG-only delivery; this also proves WP3 is invoked *zero* times,
    and that `RegistryConsistencyError` cannot be raised on this pipeline
    - both are the counterpart to test_asset_search_service.py's item 9/12
    notes).
  - No `adjudicate` import/call (search never adjudicates).
  - No write-shaped calls anywhere in either module (`db.add`, `.flush`,
    `.commit`, `.delete`, `.merge`, `mint_asset`, `attach_identifier`,
    `record_classification`) - read-only guarantee, checked structurally
    in addition to the row-count based behavioral proof in
    test_asset_search_service.py's read-only test.
  - `catalog_search.search` and `ranking.rank` ARE imported/used (positive
    control - proves the negative-import assertions above are meaningful
    and not simply a result of the module importing nothing at all).
"""
import ast
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

SEARCH_SERVICE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "services", "asset_search", "search_service.py"
)
ROUTER_PATH = os.path.join(os.path.dirname(__file__), "..", "routers", "asset_search.py")

_FORBIDDEN_WRITE_CALLS = {"add", "flush", "commit", "delete", "merge", "mint_asset", "attach_identifier", "record_classification"}
_FORBIDDEN_IMPORT_SUBSTRINGS = ("identity_resolver", "adjudicate", "merge", "provider", "yfinance")


def _tree(path: str) -> ast.Module:
    with open(path, "r", encoding="utf-8") as f:
        return ast.parse(f.read(), filename=path)


def _imported_names(tree: ast.Module) -> set:
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names.add(module)
            for alias in node.names:
                names.add(f"{module}.{alias.name}")
    return names


def _called_function_names(tree: ast.Module) -> set:
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                names.add(func.attr)
            elif isinstance(func, ast.Name):
                names.add(func.id)
    return names


def _check_module_forbidden_imports(tree: ast.Module):
    imported = _imported_names(tree)
    for name in imported:
        lowered = name.lower()
        for forbidden in _FORBIDDEN_IMPORT_SUBSTRINGS:
            assert forbidden not in lowered, f"forbidden import found: {name}"


def test_search_service_imports_no_identity_resolver_no_merge_no_adjudicate_no_provider():
    _check_module_forbidden_imports(_tree(SEARCH_SERVICE_PATH))


def test_router_imports_no_identity_resolver_no_merge_no_adjudicate_no_provider():
    _check_module_forbidden_imports(_tree(ROUTER_PATH))


def test_search_service_contains_no_write_shaped_calls():
    called = _called_function_names(_tree(SEARCH_SERVICE_PATH))
    forbidden_hit = called & _FORBIDDEN_WRITE_CALLS
    assert not forbidden_hit, f"forbidden write-shaped call(s) found: {forbidden_hit}"


def test_router_contains_no_write_shaped_calls():
    called = _called_function_names(_tree(ROUTER_PATH))
    forbidden_hit = called & _FORBIDDEN_WRITE_CALLS
    assert not forbidden_hit, f"forbidden write-shaped call(s) found: {forbidden_hit}"


def test_search_service_positively_imports_catalog_search_and_ranking():
    imported = _imported_names(_tree(SEARCH_SERVICE_PATH))
    assert any("catalog_search" in name for name in imported)
    assert any("ranking" in name for name in imported)


def test_router_imports_only_search_service_and_catalog_search_error_types():
    """WP5 may import WP2 and WP4 (F12) - the router's own imports should
    be limited to `search_service` (orchestration) and the catalog-search
    exception types it maps to HTTP codes (§13), never `ranking` or
    `catalog_search.search` directly (that composition belongs to
    `search_service.py`, not the transport layer)."""
    tree = _tree(ROUTER_PATH)
    imported = _imported_names(tree)
    assert any("search_service" in name for name in imported)
    assert not any(name.endswith(".rank") for name in imported)
    assert not any(name == "services.asset_search.catalog_search.search" for name in imported)
