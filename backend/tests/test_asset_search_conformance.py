"""Structural conformance tests for the Universal Asset Search WP6 delivery.

Validates docs/implementation/M37_1_Universal_Asset_Search_Technical_Design.md
Section 3's module-placement table and Section 21's WP6 dependency row
against `services/asset_search/search_service.py` and
`routers/asset_search.py`, via `ast` inspection rather than brittle
substring search:

  - Search orchestration imports discovery and merge, but never imports a
    concrete provider or the identity resolver directly.
  - Provider-specific code remains in provider_adapter.py; discovery_search
    performs capability-gated fan-out without Registry or ranking ownership.
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
DISCOVERY_PATH = os.path.join(
    os.path.dirname(__file__), "..", "services", "asset_search", "discovery_search.py"
)
CACHE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "services", "asset_search", "cache.py"
)

_FORBIDDEN_WRITE_CALLS = {"add", "flush", "commit", "delete", "merge", "mint_asset", "attach_identifier", "record_classification"}
_ORCHESTRATION_FORBIDDEN_IMPORTS = (
    "identity_resolver", "adjudicate", "provider_adapter", "yahoo", "yfinance"
)
_DISCOVERY_FORBIDDEN_IMPORTS = (
    "identity_resolver", "adjudicate", "registry_service", "ranking", "merge"
)


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


def _check_module_forbidden_imports(tree: ast.Module, forbidden_names):
    imported = _imported_names(tree)
    for name in imported:
        lowered = name.lower()
        for forbidden in forbidden_names:
            assert forbidden not in lowered, f"forbidden import found: {name}"


def test_search_service_does_not_bypass_discovery_or_merge_boundaries():
    _check_module_forbidden_imports(
        _tree(SEARCH_SERVICE_PATH), _ORCHESTRATION_FORBIDDEN_IMPORTS
    )


def test_router_imports_no_identity_resolver_no_merge_no_adjudicate_no_provider():
    _check_module_forbidden_imports(
        _tree(ROUTER_PATH), _ORCHESTRATION_FORBIDDEN_IMPORTS + ("merge",)
    )


def test_discovery_owns_provider_fanout_but_not_registry_merge_or_ranking():
    tree = _tree(DISCOVERY_PATH)
    _check_module_forbidden_imports(tree, _DISCOVERY_FORBIDDEN_IMPORTS)
    imported = _imported_names(tree)
    assert any("provider_adapter" in name for name in imported)


def test_search_service_contains_no_write_shaped_calls():
    called = _called_function_names(_tree(SEARCH_SERVICE_PATH))
    forbidden_hit = called & _FORBIDDEN_WRITE_CALLS
    assert not forbidden_hit, f"forbidden write-shaped call(s) found: {forbidden_hit}"


def test_router_contains_no_write_shaped_calls():
    called = _called_function_names(_tree(ROUTER_PATH))
    forbidden_hit = called & _FORBIDDEN_WRITE_CALLS
    assert not forbidden_hit, f"forbidden write-shaped call(s) found: {forbidden_hit}"


def test_discovery_and_cache_contain_no_registry_write_shaped_calls():
    for path in (DISCOVERY_PATH, CACHE_PATH):
        called = _called_function_names(_tree(path))
        forbidden_hit = called & _FORBIDDEN_WRITE_CALLS
        assert not forbidden_hit, f"forbidden write-shaped call(s) found in {path}: {forbidden_hit}"


def test_search_service_positively_imports_catalog_search_and_ranking():
    imported = _imported_names(_tree(SEARCH_SERVICE_PATH))
    assert any("catalog_search" in name for name in imported)
    assert any("ranking" in name for name in imported)
    assert any("discovery_search" in name for name in imported)
    assert any("asset_search.merge" in name for name in imported)


def test_router_imports_only_search_service_and_catalog_search_error_types():
    """WP6 changes orchestration, not transport ownership. Router imports
    be limited to `search_service` (orchestration) and the catalog-search
    the search service and catalog exception types it maps (§13), never `ranking` or
    `catalog_search.search` directly (that composition belongs to
    `search_service.py`, not the transport layer)."""
    tree = _tree(ROUTER_PATH)
    imported = _imported_names(tree)
    assert any("search_service" in name for name in imported)
    assert not any(name.endswith(".rank") for name in imported)
    assert not any(name == "services.asset_search.catalog_search.search" for name in imported)
