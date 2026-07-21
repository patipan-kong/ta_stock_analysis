"""Feature-flag mount tests for the Universal Asset Search route
(Milestone M37.2, WP5 remediation — Observation 1).

The frozen design (§17/§20's WP5 entries) requires the route to ship
"mounted behind a feature flag" but never states a default state for that
flag anywhere in §15/§20. Per the remediation directive, the flag
therefore defaults OFF (the safer rollout posture), matching this repo's
existing env-var-boolean convention (`services.core.runtime_env`'s
`APP_ENV` pattern: `os.environ.get(NAME, default).strip().lower()`).

Verifies all three states:
  - FEATURE_ASSET_SEARCH absent -> route not mounted
  - FEATURE_ASSET_SEARCH=false  -> route not mounted
  - FEATURE_ASSET_SEARCH=true   -> route mounted

`main.py` is reloaded (not merely re-imported) for each case since the
router-mount decision runs once at module-import time — a plain `import
main` after the first test would return the cached module object and
never re-evaluate the env var. Each test restores the environment and
reloads `main` back to its default (flag absent) state on exit so test
order never leaks mount state into other test modules that `import main`
directly (test_watchlist_registry.py, test_main_get_sector_registry.py).
"""
import importlib
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _has_asset_search_route(app) -> bool:
    """`app.routes` on this FastAPI version stores included routers as a
    lazy wrapper object (no flattened `.path` string until resolved), so
    checking route presence must go through the resolved OpenAPI schema
    instead of walking `app.routes` directly."""
    return "/asset-search" in app.openapi()["paths"]


def _reload_main_with_env(value):
    if "main" in sys.modules:
        del sys.modules["main"]
    if value is None:
        os.environ.pop("FEATURE_ASSET_SEARCH", None)
    else:
        os.environ["FEATURE_ASSET_SEARCH"] = value
    import main  # noqa: F401
    return importlib.reload(main)


def _restore_default():
    os.environ.pop("FEATURE_ASSET_SEARCH", None)
    if "main" in sys.modules:
        del sys.modules["main"]


def test_route_not_mounted_when_flag_absent():
    try:
        main = _reload_main_with_env(None)
        assert not _has_asset_search_route(main.app)
    finally:
        _restore_default()


def test_route_not_mounted_when_flag_false():
    try:
        main = _reload_main_with_env("false")
        assert not _has_asset_search_route(main.app)
    finally:
        _restore_default()


def test_route_mounted_when_flag_true():
    try:
        main = _reload_main_with_env("true")
        assert _has_asset_search_route(main.app)
    finally:
        _restore_default()


def test_route_not_mounted_for_arbitrary_non_true_value():
    """Only the literal "true" (case/whitespace-insensitive) enables the
    route — no other truthy-looking string is silently accepted."""
    try:
        main = _reload_main_with_env("yes")
        assert not _has_asset_search_route(main.app)
    finally:
        _restore_default()
