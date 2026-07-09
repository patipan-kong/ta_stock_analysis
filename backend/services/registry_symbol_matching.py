"""M6 Compatibility-Layer Integration, Phase 2 — Registry-backed replacement
for the five independently hand-rolled `.BK`-suffix variant matchers that
existed in basket_simulation.py, execution_plan.py, position_sizing.py,
allocation_engine.py, and idea_review.py.

See docs/implementation/M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md §2.3 item 3
(the correctness risk this replaces) and §4.2 (the "legacy symbol adapter"
this module implements).

This module holds zero identity rules of its own (ADR-004) — every match is
decided by services.registry_lookup.resolve_asset(), which in turn defers to
identity_resolver's existing current-preempts-historical adjudication. What
lives here is purely the fallback-preserving composition the five call sites
need: try the Registry first, and only when it cannot decide (Unresolved on
either side) fall back to the exact bare/`.BK`-suffix heuristic every one of
those files used before this change, so behavior for any symbol the Registry
hasn't resolved yet is unchanged (M6 plan §4.4 — "every existing code path
keeps working unchanged for any symbol the Registry hasn't resolved").

One deliberate normalization: the pre-existing heuristics were not all
identical — basket_simulation._resolve_symbol_sectors and idea_review's
known-symbol expansion only stripped a watchlist/holding symbol's `.BK`
suffix, never appended one to a bare symbol, while the portfolio-holding
side of the same functions did both. That asymmetry was incidental (nothing
depended on it), not a documented behavior; this module's fallback is
symmetric in every caller, which only ever adds matches the old asymmetric
code missed — it never removes one the old code found.

Public API
----------
match_known_symbols(db, symbols, known) -> dict[str, str]
"""
from __future__ import annotations

import logging
from typing import Iterable

from sqlalchemy.orm import Session

from services import registry_lookup

log = logging.getLogger(__name__)


def _legacy_bk_match(symbol: str, known_set: set[str]) -> str | None:
    """The bare/`.BK` suffix heuristic every target module used previously."""
    if symbol in known_set:
        return symbol
    if symbol.endswith(".BK"):
        bare = symbol[:-3]
        if bare in known_set:
            return bare
    else:
        suffixed = f"{symbol}.BK"
        if suffixed in known_set:
            return suffixed
    return None


def match_known_symbols(
    db: Session,
    symbols: Iterable[str],
    known: Iterable[str],
) -> dict[str, str]:
    """For each symbol in `symbols`, find which entry in `known` denotes the
    same instrument, if any. Symbols with no match are omitted from the
    result.

    Resolution order per symbol:
      1. Exact string match — trivial, always correct, checked before any
         lookup.
      2. Registry match — resolve_asset() on both sides; identical asset_id
         wins. This can only ever add a match the `.BK` heuristic would have
         missed (e.g. a spelling difference that isn't a `.BK` suffix at
         all), never remove one, since it is tried before the fallback.
      3. Legacy bare/`.BK` suffix heuristic — preserved so any symbol the
         Registry has not resolved yet keeps matching exactly as before
         (M6 plan §4.4). This fallback is only ever applied against `known`
         entries the Registry itself could not resolve: if the Registry
         decisively resolved a `known` entry to some asset_id, and `sym`
         resolves to a *different* one, that is the Registry affirmatively
         saying these are two distinct instruments (ASSET_REGISTRY.md §5 —
         e.g. a DR and its underlying are never the same identity even when
         their spellings are superficially similar), and the string
         heuristic must not override that verdict.
    """
    known_list = [k for k in dict.fromkeys(known) if k]
    known_set = set(known_list)

    known_asset_ids: dict[int, str] = {}
    known_unresolved: list[str] = []
    for k in known_list:
        resolved = registry_lookup.resolve_asset(db, k)
        if isinstance(resolved, registry_lookup.AssetView):
            known_asset_ids.setdefault(resolved.asset_id, k)
        else:
            known_unresolved.append(k)
    known_unresolved_set = set(known_unresolved)

    result: dict[str, str] = {}
    for sym in dict.fromkeys(s for s in symbols if s):
        if sym in known_set:
            result[sym] = sym
            continue

        resolved = registry_lookup.resolve_asset(db, sym)
        if isinstance(resolved, registry_lookup.AssetView):
            match = known_asset_ids.get(resolved.asset_id)
            if match is not None:
                log.debug(
                    "registry_symbol_matching: %s -> %s via Registry asset_id=%s",
                    sym, match, resolved.asset_id,
                )
                result[sym] = match
                continue
            # Registry resolved `sym` decisively but no known entry shares
            # its identity — only fall back to the heuristic against knowns
            # the Registry couldn't itself adjudicate.
            legacy = _legacy_bk_match(sym, known_unresolved_set)
            if legacy is not None:
                log.debug("registry_symbol_matching: %s -> %s via legacy .BK heuristic", sym, legacy)
                result[sym] = legacy
            continue

        legacy = _legacy_bk_match(sym, known_set)
        if legacy is not None:
            log.debug("registry_symbol_matching: %s -> %s via legacy .BK heuristic", sym, legacy)
            result[sym] = legacy

    return result
